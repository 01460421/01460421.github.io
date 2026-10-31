"""由 extract.py 的輸出，計算每位作曲家的風格輪廓並產生報告。

用法：
  python analyze.py --data ./out --models ./models --report ./ [--min-songs 3]
輸出：
  composer_profiles.md    中文報告（每位作曲家的風格描述）
  composer_profiles.csv   作曲家 × 特徵（平均 z 分數）
  song_features.csv       每首歌的可解釋特徵
  fig_style_map.png       作曲家風格地圖（PCA）
  fig_heatmap.png         作曲家 × 特徵熱圖
"""
import argparse
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

# 特徵: (中文名稱, 高時描述, 低時描述, 顯示格式)
TRAITS = {
    "bpm":                 ("速度 BPM",     "快節奏",         "慢節奏",           "{:.0f} BPM"),
    "bpm_changes":         ("變速次數",     "常有變速",       None,              "{:.1f} 次"),
    "onset_rate":          ("音符密度",     "音符密集",       "音符疏朗",          "{:.2f} 個/秒"),
    "beat_strength":       ("拍點清晰度",   "拍點鮮明",       "律動柔和",          "{:.2f}"),
    "percussive_ratio":    ("打擊樂比重",   "鼓組厚重",       "鼓組輕",            "{:.0%}"),
    "brightness":          ("音色亮度",     "音色明亮",       "音色溫暖偏暗",      "{:.0f} Hz"),
    "flatness":            ("噪音／失真感", "失真、噪音質感強", "音色乾淨",         "{:.3f}"),
    "bass_ratio":          ("低音比重",     "低音厚重",       "低音輕薄",          "{:.0%}"),
    "high_ratio":          ("高頻比重",     "高頻閃亮",       "高頻收斂",          "{:.1%}"),
    "dynamic_range_db":    ("動態範圍",     "動態起伏大",     "壓縮感強、音量平均", "{:.1f} dB"),
    "section_contrast_db": ("段落對比",     "段落落差大",     "段落起伏小",        "{:.1f} dB"),
    "harmonic_entropy":    ("和聲複雜度",   "和聲豐富",       "和聲簡潔",          "{:.2f} bit"),
    "chord_change":        ("和弦變化率",   "和弦轉換頻繁",   "和弦變化少",        "{:.3f}"),
    "is_minor":            ("小調比例",     "偏好小調",       "偏好大調",          "{:.0%}"),
    "key_strength":        ("調性明確度",   "調性明確",       "調性曖昧",          "{:.2f}"),
    "happy":               ("歡快",         "明亮歡快",       "少走歡快路線",      "{:.2f}"),
    "sad":                 ("哀傷",         "哀傷感重",       "少哀傷",            "{:.2f}"),
    "aggressive":          ("攻擊性",       "攻擊性強",       "溫和",              "{:.2f}"),
    "relaxed":             ("放鬆",         "放鬆",           "緊繃",              "{:.2f}"),
    "danceability":        ("舞曲感",       "舞曲感強",       "舞曲感弱",          "{:.2f}"),
    "acoustic":            ("原聲感",       "原聲樂器感重",   "原聲感低",          "{:.2f}"),
    "electronic":          ("電子感",       "電子感強",       "電子感弱",          "{:.2f}"),
}
ALIASES = {"堀江晶太(kemu)": "kemu", "堀江晶太": "kemu", "ギガ": "Giga"}
EXCLUDE = {"-", "ロシア民謡"}  # 作曲者不明／民謡
SPLIT_RE = re.compile(r"\s*(?:/|×|&|、|,|\sx\s|\sX\s)\s*")
PAREN_RE = re.compile(r"\s*\(.*\)$")


def split_composers(names):
    """把作曲者欄位拆成個人並統一寫法。
    - NFKC 正規化（cosMo＠暴走P → cosMo@暴走P）
    - 合作曲拆開；'・' 只在其中一邊單獨出現過時才拆（避免拆掉「ユリイ・カノン」）
    - 「名字(別名)」若「名字」單獨出現過，就併到「名字」（如 TOKOTOKO(西沢さんP)）
    """
    norm = {n: unicodedata.normalize("NFKC", n).strip() for n in names}
    solo = {v for v in norm.values() if not SPLIT_RE.search(v)}
    out = {}
    for n, v in norm.items():
        res = []
        for p in (p for p in SPLIT_RE.split(v) if p):
            sub = p.split("・")
            res += sub if len(sub) > 1 and any(x in solo for x in sub) else [p]
        clean = []
        for p in res:
            p = ALIASES.get(p, p)
            base = PAREN_RE.sub("", p)
            if base != p and base in solo:
                p = base
            if p not in EXCLUDE:
                clean.append(p)
        out[n] = clean
    return out


def genre_name(c):
    """'Electronic---Drum n Bass' -> 'Drum n Bass（Electronic）'"""
    parent, _, style = c.partition("---")
    return f"{style}（{parent}）" if style else c


def load(data_dir, models_dir):
    df = pd.read_csv(os.path.join(data_dir, "features.csv"))
    genre = np.load(os.path.join(data_dir, "genre400.npy"))
    emb = np.load(os.path.join(data_dir, "embed.npy"))
    with open(os.path.join(models_dir, "genre_discogs400-discogs-effnet-1.json")) as f:
        classes = json.load(f)["classes"]
    return df, genre, emb, classes


def composer_index(df):
    split = split_composers(df["composer"].unique())
    members = defaultdict(list)
    for i, c in enumerate(df["composer"]):
        for p in split[c]:
            members[p].append(i)
    return members, split


def distinctiveness(df, emb, members, split, min_songs=5):
    """風格辨識度：只用單一作曲者的歌，交叉驗證「聽音色猜作曲家」的召回率。"""
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    solo_label = [split[c][0] if len(split[c]) == 1 else None for c in df["composer"]]
    cnt = Counter(l for l in solo_label if l)
    keep = [i for i, l in enumerate(solo_label) if l and cnt[l] >= min_songs]
    if len(keep) < 20:
        return {}, np.nan
    X = emb[keep]
    y = np.array([solo_label[i] for i in keep])
    clf = make_pipeline(StandardScaler(), PCA(48, random_state=0),
                        LogisticRegression(max_iter=3000, C=0.5))
    pred = cross_val_predict(clf, X, y, cv=StratifiedKFold(min_songs, shuffle=True, random_state=0))
    recall = {c: float(np.mean(pred[y == c] == c)) for c in np.unique(y)}
    return recall, 1 / len(recall)


def describe(z_row, n):
    """把平均 z 分數轉成文字。門檻隨歌曲數調整：歌越少，要越極端才算數。"""
    thr = max(0.45, 1.6 / np.sqrt(n))
    items = sorted(((abs(v), k, v) for k, v in z_row.items() if np.isfinite(v)), reverse=True)
    words = []
    for _, k, v in items:
        if abs(v) < thr:
            break
        w = TRAITS[k][1] if v > 0 else TRAITS[k][2]
        if w:
            words.append(w)
        if len(words) >= 6:
            break
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--min-songs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(a.report, exist_ok=True)

    df, genre, emb, classes = load(a.data, a.models)
    feats = list(TRAITS)
    Z = (df[feats] - df[feats].mean()) / df[feats].std()
    members, split = composer_index(df)
    composers = sorted((c for c, ix in members.items() if len(ix) >= a.min_songs),
                       key=lambda c: (-len(members[c]), c))

    # 嵌入：先扣掉全體平均，否則 PJSK 歌曲彼此都很像，相似度會全部接近 1
    E = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    E = E - E.mean(0)
    cent = {c: E[members[c]].mean(0) for c in composers}
    cn = {c: v / (np.linalg.norm(v) + 1e-9) for c, v in cent.items()}
    recall, chance = distinctiveness(df, emb, members, split)

    g_mean = genre.mean(0)
    pct = df[feats].rank(pct=True)

    prof_rows, sections = [], []
    for c in composers:
        ix = members[c]
        n = len(ix)
        zr = Z.iloc[ix].mean()
        prof_rows.append({"composer": c, "songs": n, **zr.to_dict(),
                          "distinctiveness": recall.get(c, np.nan)})

        words = describe(zr.to_dict(), n)
        sub = df.iloc[ix]
        # 風格標籤：作曲家的平均機率 ÷ 全體平均（lift），只看本身機率夠高的
        gm = genre[ix].mean(0)
        top_abs = np.argsort(-gm)[:4]
        mask = gm >= 0.04
        lift = np.where(mask, gm / (g_mean + 1e-9), 0)
        top_lift = [i for i in np.argsort(-lift)[:6] if lift[i] > 1.3][:4]
        # 代表曲：最接近作曲家重心的歌
        sims = E[ix] @ cn[c]
        rep = sub.iloc[np.argsort(-sims)[:3]]["title"].tolist()
        # 最相近的作曲家
        near = sorted(((float(cn[c] @ cn[o]), o) for o in composers if o != c), reverse=True)[:3]
        units = Counter(u for us in sub["unit"].fillna("") for u in us.split("/") if u)
        keys = Counter(f"{k} {'小調' if s == 'minor' else '大調'}" for k, s in zip(sub["key"], sub["scale"]))
        self_arr = np.mean([c in str(ar) for ar in sub["arranger"]])

        lines = [f"### {c}（{n} 首）", ""]
        lines.append("**風格關鍵字**：" + ("、".join(words) if words else "整體接近 PJSK 平均值，沒有特別突出的面向"))
        lines.append("")
        if c in recall:
            lines.append(f"**風格辨識度**：{recall[c]:.0%}（只聽音色就猜中作曲家的比例；隨機猜為 {chance:.0%}）")
            lines.append("")
        lines.append("| 指標 | 平均值 | 在全體歌曲中的百分位 | z 分數 |")
        lines.append("|---|---|---|---|")
        for k in sorted(feats, key=lambda k: -abs(zr[k]))[:8]:
            name, _, _, fmt = TRAITS[k]
            p = "—" if k in ("is_minor", "bpm_changes") else f"{pct[k].iloc[ix].mean():.0%}"
            lines.append(f"| {name} | {fmt.format(sub[k].mean())} | {p} | {zr[k]:+.2f} |")
        lines.append("")
        lines.append("**Discogs 風格標籤**（最常見）：" + "、".join(f"{genre_name(classes[i])} ({gm[i]:.2f})" for i in top_abs))
        lines.append("")
        if top_lift:
            lines.append("**相對其他作曲家特別突出的曲風**：" + "、".join(f"{genre_name(classes[i])} ×{lift[i]:.1f}" for i in top_lift))
            lines.append("")
        lines.append(f"**常用調性**：{'、'.join(f'{k}（{v}）' for k, v in keys.most_common(3))}")
        lines.append("")
        lines.append(f"**最具代表性的歌**：{'、'.join(rep)}")
        lines.append("")
        lines.append(f"**聲音最相近的作曲家**：{'、'.join(f'{o} ({s:.2f})' for s, o in near)}")
        lines.append("")
        lines.append(f"**為哪些團體寫歌**：{'、'.join(f'{u} {v}' for u, v in units.most_common())}；"
                     f"自己編曲的比例 {self_arr:.0%}")
        lines.append("")
        sections.append("\n".join(lines))

    prof = pd.DataFrame(prof_rows)
    prof.to_csv(os.path.join(a.report, "composer_profiles.csv"), index=False, float_format="%.3f")
    cols = ["music_id", "title", "composer", "arranger", "unit", "vocal_type", "published", "key", "scale"] + feats
    df[cols].to_csv(os.path.join(a.report, "song_features.csv"), index=False, float_format="%.4f")
    make_figures(prof, feats, a.report)

    # 排行榜
    def top(k, asc=False, m=5):
        p = prof[prof.songs >= 4].sort_values(k, ascending=asc).head(m)
        return "、".join(f"{r.composer}" for r in p.itertuples())

    rank_lines = ["| 指標 | 最高 | 最低 |", "|---|---|---|"]
    for k in feats:
        rank_lines.append(f"| {TRAITS[k][0]} | {top(k)} | {top(k, True)} |")
    dist = prof.dropna(subset=["distinctiveness"]).sort_values("distinctiveness", ascending=False)

    header = f"""# PJSK 作曲家風格量化報告

分析了 **{len(df)} 首**遊戲內歌曲（每首取一個版本，優先順序：原曲 > バーチャル・シンガー ver. > セカイ ver.），
列出其中至少有 {a.min_songs} 首歌的 **{len(composers)} 位作曲家**。合作曲目會同時算進每位作曲者。

## 方法

- **音訊來源**：遊戲內的 game size 音源，所以反映的是「編曲完成後的聲音」，
  不只是旋律。若作曲和編曲是不同人，結果會混入編曲者的風格（每位作曲家都附上自編曲比例）。
- **可解釋特徵**（librosa + Essentia）：BPM（直接讀譜面，最準確）、音符密度、鼓組比重、
  音色亮度、低音比重、動態、和聲複雜度、和弦變化率、調性等。
- **深度模型**（Essentia discogs-effnet）：Discogs 400 種曲風機率，以及歡快、哀傷、攻擊性、
  舞曲感、電子感等情緒模型；1280 維嵌入用於「相似作曲家」與「風格辨識度」。
- **z 分數**：以全部 PJSK 歌曲為基準，0 代表平均，+1 代表高一個標準差。
  所以這裡的「快」是指「在 PJSK 裡算快」。
- **風格關鍵字的門檻**會隨歌曲數調整：歌越少的作曲家，特徵要越極端才會列出。
- **風格辨識度**：只用單獨作曲且至少 5 首歌的作曲家，用嵌入訓練分類器做 5-fold 交叉驗證，
  看每位作曲家的歌被正確認出的比例。數字越高，代表聲音越有個人簽名。

![風格地圖](fig_style_map.png)

![特徵熱圖](fig_heatmap.png)

## 風格辨識度排行

隨機猜中的機率為 {chance:.1%}。

| 作曲家 | 歌曲數 | 辨識度 |
|---|---|---|
""" + "\n".join(f"| {r.composer} | {r.songs} | {r.distinctiveness:.0%} |" for r in dist.itertuples()) + """

## 各指標排行（至少 4 首歌）

""" + "\n".join(rank_lines) + "\n\n## 作曲家個別輪廓\n\n"

    with open(os.path.join(a.report, "composer_profiles.md"), "w") as f:
        f.write(header + "\n".join(sections))
    print(f"報告完成：{len(composers)} 位作曲家")


def make_figures(prof, feats, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from sklearn.decomposition import PCA

    for name in ["Noto Sans CJK JP", "Noto Sans CJK TC", "IPAGothic", "IPAexGothic", "TakaoGothic"]:
        if any(f.name == name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False
    labels = [TRAITS[k][0] for k in feats]

    big = prof[prof.songs >= 4].reset_index(drop=True)
    if len(big) < 3:
        big = prof.reset_index(drop=True)
    X = big[feats].fillna(0).values
    pca = PCA(2).fit(X)
    P = pca.transform(X)
    fig, ax = plt.subplots(figsize=(13, 10))
    sc = ax.scatter(P[:, 0], P[:, 1], s=big.songs * 18, c=big["electronic"], cmap="coolwarm", alpha=.75)
    for (x, y), name in zip(P, big.composer):
        ax.annotate(name, (x, y), fontsize=8, xytext=(4, 3), textcoords="offset points")
    # 用箭頭標出主要特徵的方向
    load = pca.components_.T
    strongest = np.argsort(-np.linalg.norm(load, axis=1))[:8]
    scale = np.abs(P).max() * .9 / np.abs(load[strongest]).max()
    for i in strongest:
        ax.arrow(0, 0, load[i, 0] * scale, load[i, 1] * scale, color="gray", alpha=.5, width=.005)
        ax.text(load[i, 0] * scale * 1.08, load[i, 1] * scale * 1.08, labels[i], color="dimgray", fontsize=9)
    ax.axhline(0, color="lightgray", lw=.5)
    ax.axvline(0, color="lightgray", lw=.5)
    ev = pca.explained_variance_ratio_
    ax.set_xlabel(f"PC1（{ev[0]:.0%}）")
    ax.set_ylabel(f"PC2（{ev[1]:.0%}）")
    ax.set_title("PJSK 作曲家風格地圖（點大小＝歌曲數，顏色＝電子感）")
    fig.colorbar(sc, ax=ax, label="電子感 z 分數")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig_style_map.png"), dpi=130)
    plt.close(fig)

    order = big.sort_values("songs", ascending=False)
    M = order[feats].values
    fig, ax = plt.subplots(figsize=(14, max(6, .32 * len(order))))
    im = ax.imshow(M, cmap="RdBu_r", vmin=-1.5, vmax=1.5, aspect="auto")
    ax.set_xticks(range(len(feats)), labels, rotation=60, ha="right", fontsize=9)
    ax.set_yticks(range(len(order)), [f"{c}（{n}）" for c, n in zip(order.composer, order.songs)], fontsize=8)
    fig.colorbar(im, ax=ax, label="平均 z 分數（相對 PJSK 全體）")
    ax.set_title("作曲家 × 風格指標")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "fig_heatmap.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
