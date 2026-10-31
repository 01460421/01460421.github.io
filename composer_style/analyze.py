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
    "flatness":            ("噪音／失真感", "失真噪音質感強", "音色乾淨",         "{:.3f}"),
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


# 每個指標的計算方式與解讀（寫進報告的「指標說明」）
DEFINITIONS = {
    "bpm": ("讀取 master 譜面檔的 BPM 事件，取演奏時間最長的 BPM", "曲速。來自官方譜面，不是從音訊估計；慢速前奏或漸慢段落不會影響主 BPM"),
    "bpm_changes": ("譜面中實際使用到的不同 BPM 數量 − 1（算 z 分數時取 log(1+x)）", "0 表示全曲同速；越多表示變速段落越多。漸快、漸慢在譜面上是連續一串 BPM，所以可能高達上百"),
    "onset_rate": ("librosa onset 偵測到的音頭數 ÷ 歌曲秒數", "聽得出的「起音」密度。失真很重、壓縮成音牆的編曲，音頭會糊在一起，數值反而偏低"),
    "beat_strength": ("拍點上的 onset 強度 ÷ 全曲平均 onset 強度（拍點由 Essentia 偵測並自動對齊）", "越高代表重音越集中在拍點上（四拍踩踏、鼓點清楚）；低代表切分、律動柔和或拍點模糊"),
    "percussive_ratio": ("HPSS 分離後打擊成分能量 ÷ 總能量", "鼓組與打擊樂在混音中佔的比重"),
    "brightness": ("頻譜質心平均值（Hz）", "聲音的「亮度」。高頻樂器、合成器、明亮人聲會拉高"),
    "flatness": ("頻譜平坦度平均值", "越接近 1 越像白噪音。失真吉他、噪音合成器、大量鈸類會拉高"),
    "bass_ratio": ("150 Hz 以下的能量 ÷ 總能量", "低音（大鼓、貝斯、808）的厚重程度"),
    "high_ratio": ("4 kHz 以上的能量 ÷ 總能量", "高頻（鈸、齒音、閃亮合成器）的比重"),
    "dynamic_range_db": ("RMS 音量（dB）第 95 百分位 − 第 10 百分位", "全曲音量的落差。低代表壓縮重、始終很大聲"),
    "section_contrast_db": ("每 5 秒平均音量的標準差（dB）", "段落之間的起伏，例如安靜的 A 段接爆發的副歌"),
    "harmonic_entropy": ("和聲成分 chroma 分布的熵（bit），最大值 log2(12)=3.58", "同時響起的音高種類有多分散。高代表和聲厚、張力音多；低代表和聲單純"),
    "chord_change": ("逐拍 chroma 的餘弦距離平均", "每拍之間和聲變化的程度，近似「和弦轉換頻率」"),
    "is_minor": ("Essentia KeyExtractor（edma 調性模板）判定為小調 = 1", "作曲家平均值即小調曲的比例"),
    "key_strength": ("KeyExtractor 的調性強度（0–1）", "越高越像單純的大／小調；低代表轉調多、調式曖昧或大量借用和弦"),
    "happy": ("discogs-effnet + mood_happy 模型的機率", "聽感的歡快程度"),
    "sad": ("discogs-effnet + mood_sad 模型的機率", "聽感的哀傷程度"),
    "aggressive": ("discogs-effnet + mood_aggressive 模型的機率", "聽感的攻擊性（失真、重拍、咆哮感）"),
    "relaxed": ("discogs-effnet + mood_relaxed 模型的機率", "聽感的放鬆程度"),
    "danceability": ("discogs-effnet + danceability 模型的機率", "穩定律動、適合跳舞的程度"),
    "acoustic": ("discogs-effnet + mood_acoustic 模型的機率", "原聲樂器（鋼琴、木吉他、弦樂）主導的程度"),
    "electronic": ("discogs-effnet + mood_electronic 模型的機率", "電子音色主導的程度"),
}
GROUPS = {
    "節奏": ["bpm", "bpm_changes", "onset_rate", "beat_strength"],
    "音色": ["percussive_ratio", "brightness", "flatness", "bass_ratio", "high_ratio"],
    "動態": ["dynamic_range_db", "section_contrast_db"],
    "和聲": ["harmonic_entropy", "chord_change", "is_minor", "key_strength"],
    "情緒／質感": ["happy", "sad", "aggressive", "relaxed", "danceability", "acoustic", "electronic"],
}
NO_PCT = {"is_minor", "bpm_changes"}


def distinctiveness(df, emb, split, min_songs=5):
    """風格辨識度：只用單一作曲者的歌，交叉驗證「聽聲音猜作曲家」。
    回傳每位作曲家的召回率、亂猜機率、以及被誤認對象的統計。"""
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    solo_label = [split[c][0] if len(split[c]) == 1 else None for c in df["composer"]]
    cnt = Counter(l for l in solo_label if l)
    keep = [i for i, l in enumerate(solo_label) if l and cnt[l] >= min_songs]
    if len(keep) < 20:
        return {}, np.nan, {}
    X = emb[keep]
    y = np.array([solo_label[i] for i in keep])
    clf = make_pipeline(StandardScaler(), PCA(48, random_state=0),
                        LogisticRegression(max_iter=3000, C=0.5))
    pred = cross_val_predict(clf, X, y, cv=StratifiedKFold(min_songs, shuffle=True, random_state=0))
    recall = {c: float(np.mean(pred[y == c] == c)) for c in np.unique(y)}
    confused = {c: Counter(p for p, t in zip(pred, y) if t == c and p != c) for c in recall}
    return recall, 1 / len(recall), confused


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


def level(z):
    if not np.isfinite(z):
        return "無資料"
    if z >= 1.0:
        return "非常高"
    if z >= 0.5:
        return "偏高"
    if z > -0.5:
        return "接近平均"
    if z > -1.0:
        return "偏低"
    return "非常低"


def zbar(z):
    """把 z 分數畫成文字長條：◀◀◀｜▶▶▶"""
    if not np.isfinite(z):
        return ""
    k = int(min(3, round(abs(z) / 0.5)))
    return ("◀" * k).rjust(3, "·") + "｜" + "···" if z < 0 else "···" + "｜" + ("▶" * k).ljust(3, "·")


def slug(text):
    """GitHub markdown 標題錨點"""
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def fmt(k, v):
    return TRAITS[k][3].format(v) if np.isfinite(v) else "—"


def narrative(c, sub, zr, pct_mean, gm, lift_items, classes, self_arr, arrangers, keys):
    """自動產生一段描述文字。"""
    n = len(sub)
    p = lambda k: f"第 {pct_mean[k] * 100:.0f} 百分位"  # noqa: E731
    s = []
    bc = int((sub["bpm_changes"] > 0).sum())
    s.append(f"**節奏**：平均 {sub.bpm.mean():.0f} BPM（{level(zr.bpm)}，約{p('bpm')}），"
             f"範圍 {sub.bpm.min():.0f}–{sub.bpm.max():.0f} BPM"
             + (f"，{n} 首中有 {bc} 首含變速" if bc else "，全部為單一速度")
             + f"。可辨識音頭密度{level(zr.onset_rate)}，拍點清晰度{level(zr.beat_strength)}。")
    s.append(f"**音色**：亮度{level(zr.brightness)}（平均 {sub.brightness.mean():.0f} Hz），"
             f"低音比重{level(zr.bass_ratio)}，高頻比重{level(zr.high_ratio)}，"
             f"噪音／失真感{level(zr.flatness)}，鼓組比重{level(zr.percussive_ratio)}。"
             f"動態範圍{level(zr.dynamic_range_db)}，段落對比{level(zr.section_contrast_db)}。")
    minor = int(sub.is_minor.sum())
    s.append(f"**和聲**：{n} 首中 {minor} 首判定為小調（{minor / n:.0%}），"
             f"最常見的調是 {'、'.join(k for k, _ in keys.most_common(2))}。"
             f"和聲複雜度{level(zr.harmonic_entropy)}，和弦變化率{level(zr.chord_change)}，"
             f"調性明確度{level(zr.key_strength)}。")
    moods = sorted(["happy", "sad", "aggressive", "relaxed"], key=lambda k: -zr[k])
    top_mood = [TRAITS[k][0] for k in moods if zr[k] > 0.3][:2]
    low_mood = [TRAITS[k][0] for k in moods[::-1] if zr[k] < -0.3][:2]
    texture = ("偏電子" if zr.electronic - zr.acoustic > 0.6 else
               "偏原聲" if zr.acoustic - zr.electronic > 0.6 else "電子與原聲比例接近 PJSK 平均")
    s.append(f"**情緒與質感**：情緒模型上"
             + (f"相對突出的是{'、'.join(top_mood)}" if top_mood else "沒有特別突出的情緒")
             + (f"，較少{'、'.join(low_mood)}" if low_mood else "")
             + f"；舞曲感{level(zr.danceability)}，整體{texture}"
             f"（電子感 {sub.electronic.mean():.2f}，原聲感 {sub.acoustic.mean():.2f}）。")
    top = [genre_name(classes[i]) for i in np.argsort(-gm) if not classes[i].endswith("J-pop")][:3]
    g = f"**曲風**：除了 J-pop 以外，模型最常給出 {'、'.join(top)}"
    if lift_items:
        g += f"；和其他作曲家相比特別突出的是 {'、'.join(f'{genre_name(classes[i])}（×{l:.1f}）' for i, l in lift_items[:3])}"
    s.append(g + "。")
    others = [a for a, _ in arrangers.most_common() if c not in a and a.strip() not in ("-", "")][:3]
    s.append(f"**編曲**：{n} 首中 {round(self_arr * n)} 首自己參與編曲（{self_arr:.0%}）"
             + (f"；其他編曲者有 {'、'.join(others)}" if others else "") + "。"
             + (" 自編曲比例低時，上面的聲音特徵很大一部分反映的是編曲者的風格。" if self_arr < 0.5 else ""))
    return "\n\n".join(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--min-songs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(a.report, exist_ok=True)

    df, genre, emb, classes = load(a.data, a.models)
    df["unit"] = df["unit"].fillna("").str.replace("/", "|", regex=False).str.replace("Leo|need", "Leo/need", regex=False)
    feats = list(TRAITS)
    mu, sd = df[feats].mean(), df[feats].std()
    # 變速次數極度偏斜（漸慢段落可達上百個 BPM 值），z 分數改用 log(1+x)
    zsrc = df[feats].copy()
    zsrc["bpm_changes"] = np.log1p(zsrc["bpm_changes"])
    Z = (zsrc - zsrc.mean()) / zsrc.std()
    pct = df[feats].rank(pct=True)
    members, split = composer_index(df)
    composers = sorted((c for c, ix in members.items() if len(ix) >= a.min_songs),
                       key=lambda c: (-len(members[c]), c))
    pairs_only = sorted((c for c, ix in members.items() if len(ix) == 2), key=str)

    # 嵌入：先扣掉全體平均，否則 PJSK 歌曲彼此都很像，相似度會全部接近 1
    E = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    E = E - E.mean(0)
    En = E / np.linalg.norm(E, axis=1, keepdims=True)
    cent = {c: E[members[c]].mean(0) for c in members}
    cn = {c: v / (np.linalg.norm(v) + 1e-9) for c, v in cent.items()}
    recall, chance, confused = distinctiveness(df, emb, split)
    g_mean = genre.mean(0)

    def lift_of(ix):
        gm = genre[ix].mean(0)
        lift = np.where(gm >= 0.04, gm / (g_mean + 1e-9), 0)
        return gm, [(i, float(lift[i])) for i in np.argsort(-lift)[:8] if lift[i] > 1.3]

    def top_style(i):
        order = [j for j in np.argsort(-genre[i]) if not classes[j].endswith("J-pop")]
        return genre_name(classes[order[0]]).split("（")[0]

    prof_rows, sections, index_rows = [], [], []
    profile_files = {}
    fname, used = {}, set()
    for c in composers:
        base = re.sub(r"[^\w\-]", "", unicodedata.normalize("NFKC", c)) or "composer"
        name, k = base, 2
        while name.lower() in used:
            name, k = f"{base}_{k}", k + 1
        used.add(name.lower())
        fname[c] = name
    for c in composers:
        ix = members[c]
        n = len(ix)
        sub = df.iloc[ix]
        zr = Z.iloc[ix].mean()
        pm = pct.iloc[ix].mean()
        words = describe(zr.to_dict(), n)
        gm, lift_items = lift_of(ix)
        sims = En[ix] @ cn[c]
        order = np.argsort(-sims)
        near = sorted(((float(cn[c] @ cn[o]), o) for o in composers if o != c), reverse=True)[:5]
        units = Counter(u for us in sub["unit"] for u in us.split("|") if u)
        keys = Counter(f"{k} {'小調' if s == 'minor' else '大調'}" for k, s in zip(sub["key"], sub["scale"]))
        self_flags = [c in unicodedata.normalize("NFKC", str(ar)) for ar in sub["arranger"]]
        self_arr = float(np.mean(self_flags))
        arrangers = Counter(unicodedata.normalize("NFKC", str(ar)) for ar in sub["arranger"])
        prof_rows.append({"composer": c, "songs": n, **zr.to_dict(),
                          "distinctiveness": recall.get(c, np.nan), "self_arranged": self_arr})
        index_rows.append((c, n, words, recall.get(c)))

        head = [f"> 歌曲數 **{n}**　｜　風格關鍵字：**{'、'.join(words) if words else '接近 PJSK 平均'}**", ""]
        if c in recall:
            conf = confused[c].most_common(3)
            head += [f"**風格辨識度**：{recall[c]:.0%}（亂猜為 {chance:.0%}）"
                     + (f"。認錯時最常被當成：{'、'.join(f'{o}（{k} 次）' for o, k in conf)}" if conf else "。每首都被正確認出"), ""]
        head += [narrative(c, sub, zr, pm, gm, lift_items, classes, self_arr, arrangers, keys), ""]
        lift_line = ("**相對 PJSK 全體特別突出的曲風**：" + "、".join(f"{genre_name(classes[i])} ×{l:.1f}" for i, l in lift_items[:5])) if lift_items else ""
        rep_line = (f"**最具代表性**：{'、'.join(sub.iloc[order[:3]].title)}　｜　"
                    f"**最不像平常的自己**：{'、'.join(sub.iloc[order[::-1][:min(2, max(0, n - 3))]].title) or '—'}")

        # 主報告：摘要版
        B = [f"### {c}", ""] + head
        B += [f"**聲音最相近**：{'、'.join(f'[{o}](#{slug(o)}) {s:.2f}' for s, o in near)}", "", rep_line, "",
              f"→ [完整指標表與曲目明細](profiles/{fname[c]}.md)", ""]
        sections.append("\n".join(B))

        # 個別檔案：完整版
        F = [f"# {c}：作曲家風格輪廓", "", "[← 回到總報告](../composer_profiles.md)", ""] + head
        F += ["## 完整指標", "", "| 類別 | 指標 | 平均 | 最小–最大 | 百分位 | z | 判讀 | |", "|---|---|---|---|---|---|---|---|"]
        for gname, ks in GROUPS.items():
            for k in ks:
                rng = f"{fmt(k, sub[k].min())}–{fmt(k, sub[k].max())}" if k not in NO_PCT else "—"
                pc = "—" if k in NO_PCT else f"{pm[k]:.0%}"
                F.append(f"| {gname} | {TRAITS[k][0]} | {fmt(k, sub[k].mean())} | {rng} | {pc} | "
                         f"{zr[k]:+.2f} | {level(zr[k])} | `{zbar(zr[k])}` |")
        F += ["", "z 分數以全部 PJSK 歌曲為基準；長條每個 ▶／◀ 約 0.5 個標準差。指標定義見總報告「二、方法」。", ""]
        F += ["## 曲風與調性", "",
              "**Discogs 曲風機率（前 8）**：" + "、".join(f"{genre_name(classes[i])} {gm[i]:.2f}" for i in np.argsort(-gm)[:8]), ""]
        if lift_line:
            F += [lift_line, ""]
        F += [f"**調性分布**：{'、'.join(f'{k}×{v}' for k, v in keys.most_common())}", ""]
        F += ["## 關係", "",
              "**聲音最相近的作曲家**（嵌入餘弦相似度）：" + "、".join(
                  (f"[{o}]({fname[o]}.md)" if o in fname else o) + f" {s:.2f}" for s, o in near), "",
              f"**為哪些團體寫歌**：{'、'.join(f'{u}×{v}' for u, v in units.most_common()) or '—'}", "",
              f"**編曲者**：{'、'.join(f'{ar}×{v}' for ar, v in arrangers.most_common())}", "",
              rep_line, ""]
        F += ["## 曲目明細", "",
              "| 歌名 | 編曲 | 團體 | BPM | 調性 | 歡快 | 哀傷 | 攻擊 | 放鬆 | 舞曲 | 電子 | 原聲 | 亮度 | 主要曲風（J-pop 以外） | 代表性 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for j in order:
            r = sub.iloc[j]
            bpm_s = f"{r.bpm:.0f}" + ("*" if r.bpm_changes > 0 else "")
            F.append(f"| {r.title} | {r.arranger} | {r.unit.replace('|', '、') or '—'} | {bpm_s} | "
                     f"{r.key}{'m' if r.scale == 'minor' else ''} | {r.happy:.2f} | {r.sad:.2f} | {r.aggressive:.2f} | "
                     f"{r.relaxed:.2f} | {r.danceability:.2f} | {r.electronic:.2f} | {r.acoustic:.2f} | "
                     f"{r.brightness:.0f} | {top_style(ix[j])} | {sims[j]:+.2f} |")
        F += ["", "BPM 後的 * 表示有變速；調性後的 m 表示小調。代表性是這首歌與作曲家平均聲音的相似度，越高越典型。", ""]
        profile_files[fname[c]] = "\n".join(F)

    prof = pd.DataFrame(prof_rows)
    prof.to_csv(os.path.join(a.report, "composer_profiles.csv"), index=False, float_format="%.3f")
    cols = ["music_id", "title", "composer", "arranger", "unit", "vocal_type", "published", "key", "scale"] + feats
    df[cols].to_csv(os.path.join(a.report, "song_features.csv"), index=False, float_format="%.4f")
    make_figures(prof, feats, a.report)

    out = []
    w = out.append
    w("# PJSK 作曲家風格量化報告\n")
    w(f"用遊戲內 {len(df)} 首歌的音訊，把「作曲家風格」拆成 22 項可量化指標、400 種曲風機率和 1280 維聲音嵌入，"
      f"整理出 {len(composers)} 位作曲家（至少 {a.min_songs} 首）的風格輪廓。\n")
    w("## 目錄\n")
    toc = ["一、資料概覽", "二、方法", "三、PJSK 全體基準", "四、團體風格比較", "五、風格地圖與熱圖",
           "六、風格辨識度", "七、各指標排行", "八、聲音最相近的作曲家組合", "九、作曲家索引",
           "十、作曲家個別輪廓", "十一、只有 2 首歌的作曲家", "十二、限制與注意事項"]
    for t in toc:
        w(f"- [{t}](#{slug(t)})")
    w("")

    # 一、資料概覽
    vt = df.vocal_type.value_counts()
    vt_name = {"original_song": "原曲", "virtual_singer": "バーチャル・シンガー ver.", "sekai": "セカイ ver.",
               "another_vocal": "アナザーボーカル", "instrumental": "伴奏", "streaming_live": "直播版",
               "april_fool_2022": "愚人節版"}
    unit_cnt = Counter(u for us in df.unit for u in us.split("|") if u)
    w("## 一、資料概覽\n")
    w("| 項目 | 數值 |\n|---|---|")
    w(f"| 分析歌曲 | {len(df)} 首 |")
    w(f"| 不同作曲者（拆開合作曲後） | {len(members)} 位 |")
    w(f"| 至少 {a.min_songs} 首（有完整輪廓） | {len(composers)} 位 |")
    w(f"| 只有 2 首（簡表） | {len(pairs_only)} 位 |")
    w(f"| 歌曲總長 | {df.duration.sum() / 3600:.1f} 小時（平均 {df.duration.mean():.0f} 秒／首） |")
    w(f"| 遊戲收錄期間 | {df.published.min()} ～ {df.published.max()} |")
    w("| 使用的音源版本 | " + "、".join(f"{vt_name.get(k, k)} {v}" for k, v in vt.items()) + " |")
    w("| 團體分布 | " + "、".join(f"{u} {v}" for u, v in unit_cnt.most_common()) + " |")
    w("")
    w("每首歌只取一個版本，優先順序：原曲 > バーチャル・シンガー ver. > セカイ ver. > アナザーボーカル。"
      "原曲最接近作曲家本人的編曲，所以排在最前面。\n")

    # 二、方法
    w("## 二、方法\n")
    w("### 流程\n")
    w("1. **取得音源**：從 sekai.best 下載遊戲內的 game size 音源，每首約 2 分鐘。音檔只在記憶體中處理，不會保存。")
    w("2. **去除頭尾靜音**：遊戲音源開頭有約 9 秒空白，先裁掉，避免動態類指標失真。")
    w("3. **可解釋特徵**：librosa 負責頻譜、能量、和聲；Essentia 負責調性和節拍；BPM 直接讀譜面檔。")
    w("4. **深度模型**：Essentia 的 `discogs-effnet` 先把音訊轉成 1280 維嵌入，再接分類頭：")
    w("   - Discogs 400 種曲風機率（例如 Electronic---Drum n Bass）")
    w("   - 7 個情緒／質感模型（歡快、哀傷、攻擊性、放鬆、舞曲感、原聲感、電子感）")
    w("5. **標準化**：每項指標以全部 PJSK 歌曲換算成 z 分數，0 是平均，±1 是一個標準差。")
    w("6. **作曲家彙整**：作曲家的值就是他們歌曲的平均。合作曲會同時算進每位作曲者。")
    w("")
    w("### 指標說明\n")
    w("| 類別 | 指標 | 計算方式 | 怎麼解讀 |\n|---|---|---|---|")
    for gname, ks in GROUPS.items():
        for k in ks:
            w(f"| {gname} | {TRAITS[k][0]} | {DEFINITIONS[k][0]} | {DEFINITIONS[k][1]} |")
    w("")
    w("### 衍生指標\n")
    w("- **風格關鍵字**：作曲家平均 z 分數最極端的幾項，轉成文字。門檻是 max(0.45, 1.6/√歌曲數)，"
      "所以歌越少的作曲家，特徵要越極端才會列出，避免一兩首歌就下結論。")
    w("- **判讀等級**：z ≥ 1 為「非常高」，0.5 到 1 為「偏高」，−0.5 到 0.5 為「接近平均」，"
      "−1 到 −0.5 為「偏低」，z ≤ −1 為「非常低」。")
    w("- **百分位**：作曲家每首歌在全部 PJSK 歌曲中排第幾百分位，再取平均。")
    w("- **突出曲風（lift）**：作曲家的平均曲風機率 ÷ PJSK 全體平均，只看本身機率 ≥ 0.04 的曲風。×3 代表這種曲風在該作曲家身上出現的程度是平均的 3 倍。")
    w("- **聲音相似度**：每首歌的嵌入先扣掉 PJSK 全體平均（否則所有歌都很像），作曲家取平均向量，再算餘弦相似度。1 是完全同方向，0 是無關。")
    w("- **代表性**：單曲嵌入與作曲家平均向量的相似度。")
    w(f"- **風格辨識度**：只用「單獨作曲且至少 5 首」的 {len(recall)} 位作曲家。用嵌入訓練邏輯回歸"
      "（先標準化並 PCA 降到 48 維），做 5-fold 交叉驗證，算每位作曲家的歌被正確認出的比例。"
      "這代表聲音有多少「個人簽名」。")
    w("- **作曲者名稱整理**：先做 NFKC 正規化（例如 cosMo＠暴走P → cosMo@暴走P）。"
      "合作曲按 `/ × & 、 ,` 拆開。`・` 只在其中一邊單獨出現過時才拆（所以「ユリイ・カノン」不會被拆）。"
      "「名字（別名）」若「名字」單獨出現過，就併到該名字。另外合併 ギガ→Giga、堀江晶太→kemu。"
      "作曲者為「-」或「ロシア民謡」的歌不列入作曲家統計。\n")

    # 三、全體基準
    w("## 三、PJSK 全體基準\n")
    w("作曲家的「高／低」都是相對下表而言。\n")
    w("| 類別 | 指標 | 平均 | 標準差 | 第 10 百分位 | 中位數 | 第 90 百分位 |\n|---|---|---|---|---|---|---|")
    for gname, ks in GROUPS.items():
        for k in ks:
            q = df[k].quantile([.1, .5, .9])
            sdv = TRAITS[k][3].format(sd[k]).replace(" BPM", "").replace(" Hz", "")
            if k == "is_minor":
                w(f"| {gname} | {TRAITS[k][0]} | {fmt(k, mu[k])} | — | — | — | — |")
            elif k == "bpm_changes":
                w(f"| {gname} | {TRAITS[k][0]} | {fmt(k, mu[k])}（{(df[k] > 0).mean():.0%} 的歌有變速） | 偏斜，z 分數改用 log(1+x) | "
                  f"{fmt(k, q[.1])} | {fmt(k, q[.5])} | {fmt(k, df[k].max())}（最大） |")
            else:
                w(f"| {gname} | {TRAITS[k][0]} | {fmt(k, mu[k])} | {sdv} | {fmt(k, q[.1])} | {fmt(k, q[.5])} | {fmt(k, q[.9])} |")
    w("")
    keys_all = Counter(f"{k} {'小調' if s == 'minor' else '大調'}" for k, s in zip(df.key, df.scale))
    w(f"**大小調**：大調 {int((df.scale == 'major').sum())} 首、小調 {int((df.scale == 'minor').sum())} 首。")
    w("")
    w("**最常見的調**：" + "、".join(f"{k} {v}" for k, v in keys_all.most_common(10)))
    w("")
    w(f"**有變速的歌**：{int((df.bpm_changes > 0).sum())} 首（{(df.bpm_changes > 0).mean():.0%}）。"
      f"最快 {df.bpm.max():.0f} BPM（{'、'.join(df[df.bpm == df.bpm.max()].title.head(3))}），"
      f"最慢 {df.bpm.min():.0f} BPM（{'、'.join(df[df.bpm == df.bpm.min()].title.head(3))}）。")
    w("")
    w("**PJSK 全體最常見的曲風**（平均機率）：" + "、".join(f"{genre_name(classes[i])} {g_mean[i]:.3f}" for i in np.argsort(-g_mean)[:12]))
    w("")

    # 四、團體
    w("## 四、團體風格比較\n")
    w("以團體標籤分組（同一首歌若有多個標籤，會同時計入）。數值為平均 z 分數。\n")
    unit_names = [u for u, _ in unit_cnt.most_common()]
    uidx = {u: [i for i, us in enumerate(df.unit) if u in us.split("|")] for u in unit_names}
    w("| 指標 | " + " | ".join(f"{u}（{len(uidx[u])}）" for u in unit_names) + " |")
    w("|---|" + "---|" * len(unit_names))
    for k in feats:
        w(f"| {TRAITS[k][0]} | " + " | ".join(f"{Z.iloc[uidx[u]][k].mean():+.2f}" for u in unit_names) + " |")
    w("")
    for u in unit_names:
        ix = uidx[u]
        if len(ix) < 5:
            continue
        zr = Z.iloc[ix].mean()
        _, li = lift_of(ix)
        comp = Counter(p for i in ix for p in split[df.composer.iloc[i]]).most_common(5)
        w(f"- **{u}**（{len(ix)} 首）：{'、'.join(describe(zr.to_dict(), len(ix))) or '接近平均'}。"
          f"平均 {df.bpm.iloc[ix].mean():.0f} BPM，小調 {df.is_minor.iloc[ix].mean():.0%}。"
          f"突出曲風：{'、'.join(f'{genre_name(classes[i])} ×{l:.1f}' for i, l in li[:3]) or '—'}。"
          f"最常合作的作曲家：{'、'.join(f'{c} {k}' for c, k in comp)}。")
    w("")

    # 五、圖
    w("## 五、風格地圖與熱圖\n")
    w("**風格地圖**：把至少 4 首歌的作曲家，用 22 項 z 分數做 PCA 投影到平面。"
      "距離越近，風格越像。灰色箭頭是影響最大的指標方向，點的大小代表歌曲數，顏色代表電子感。\n")
    w("![風格地圖](fig_style_map.png)\n")
    w("**熱圖**：紅色代表高於 PJSK 平均，藍色代表低於平均。\n")
    w("![特徵熱圖](fig_heatmap.png)\n")

    # 六、辨識度
    w("## 六、風格辨識度\n")
    w(f"共 {len(recall)} 位作曲家參與分類，亂猜的命中率是 {chance:.1%}。\n")
    w("| 排名 | 作曲家 | 歌曲數 | 辨識度 | 認錯時最常被當成 |\n|---|---|---|---|---|")
    dist = sorted(recall.items(), key=lambda kv: -kv[1])
    for r, (c, v) in enumerate(dist, 1):
        conf = confused[c].most_common(2)
        w(f"| {r} | [{c}](#{slug(c)}) | {len(members[c])} | {v:.0%} | {'、'.join(f'{o}（{k}）' for o, k in conf) or '—'} |")
    w("")
    w("辨識度低不代表沒有風格，而是聲音容易和別人重疊。常見原因有："
      "（1）作品橫跨很多曲風；（2）由不同編曲者經手；（3）屬於 PJSK 中很常見的主流 J-pop／J-rock 聲音。\n")

    # 七、排行
    w("## 七、各指標排行\n")
    w("只計算至少 4 首歌的作曲家。括號內為平均值。\n")
    big = prof[prof.songs >= 4].set_index("composer")
    raw = {c: df.iloc[members[c]][feats].mean() for c in big.index}
    w("| 指標 | 最高 5 位 | 最低 5 位 |\n|---|---|---|")
    for k in feats:
        hi = big[k].sort_values(ascending=False).head(5).index
        lo = big[k].sort_values().head(5).index
        w(f"| {TRAITS[k][0]} | {'、'.join(f'{c}（{fmt(k, raw[c][k])}）' for c in hi)} | "
          f"{'、'.join(f'{c}（{fmt(k, raw[c][k])}）' for c in lo)} |")
    w("")

    # 八、相似組合
    w("## 八、聲音最相近的作曲家組合\n")
    w("至少 4 首歌的作曲家之間，嵌入相似度最高的 25 組。\n")
    bl = list(big.index)
    pairs = sorted(((float(cn[x] @ cn[y]), x, y) for i, x in enumerate(bl) for y in bl[i + 1:]), reverse=True)[:25]
    w("| # | 作曲家 A | 作曲家 B | 相似度 |\n|---|---|---|---|")
    for r, (s, x, y) in enumerate(pairs, 1):
        w(f"| {r} | {x} | {y} | {s:.2f} |")
    w("")
    far = sorted(((float(cn[x] @ cn[y]), x, y) for i, x in enumerate(bl) for y in bl[i + 1:]))[:10]
    w("**聲音差異最大的 10 組**：" + "、".join(f"{x} ↔ {y}（{s:.2f}）" for s, x, y in far))
    w("")

    # 九、索引
    w("## 九、作曲家索引\n")
    w("| 作曲家 | 歌曲數 | 辨識度 | 風格關鍵字 | 詳細 |\n|---|---|---|---|---|")
    for c, n, words, rc in index_rows:
        w(f"| [{c}](#{slug(c)}) | {n} | {'' if rc is None else f'{rc:.0%}'} | {'、'.join(words) or '接近平均'} | [完整](profiles/{fname[c]}.md) |")
    w("")

    # 十、個別輪廓
    w("## 十、作曲家個別輪廓\n")
    w("依歌曲數排序。這裡是每位作曲家的摘要；22 項完整指標、曲風、調性、編曲者和逐曲明細，"
      "請點各段最後的連結，進入 `profiles/` 底下的個別檔案。\n")
    w("\n\n".join(sections))
    w("")

    # 十一、2 首
    w("## 十一、只有 2 首歌的作曲家\n")
    w("樣本太少，只列出最極端的特徵（|z| ≥ 1.13）和突出曲風，僅供參考。\n")
    w("| 作曲家 | 歌曲 | 特徵 | 突出曲風 | 平均 BPM |\n|---|---|---|---|---|")
    for c in pairs_only:
        ix = members[c]
        zr = Z.iloc[ix].mean()
        _, li = lift_of(ix)
        w(f"| {c} | {'、'.join(df.title.iloc[ix])} | {'、'.join(describe(zr.to_dict(), 2)) or '—'} | "
          f"{'、'.join(genre_name(classes[i]).split('（')[0] for i, _ in li[:2]) or '—'} | {df.bpm.iloc[ix].mean():.0f} |")
    w("")

    # 十二、限制
    w("## 十二、限制與注意事項\n")
    w("1. **分析的是編曲後的成品**。作曲者和編曲者不同時（例如 DECO\\*27、Eve 多半由他人編曲），"
      "結果會混入編曲者的風格。每位作曲家都附有自編曲比例，可以拿來判斷。")
    w("2. **game size 版本約 2 分鐘**，通常是前奏、A 段、副歌加結尾，不一定包含完整曲的所有段落。")
    w("3. **音符密度是「可辨識的音頭數」**。失真重、壓縮成音牆的編曲（如部分搖滾或金屬曲），音頭會糊在一起，"
      "所以快歌也可能分數偏低。")
    w("4. **調性判定可能錯一個五度**，或把關係大小調搞混，轉調多的歌尤其容易出錯。看整體比例比看單首可靠。")
    w("5. **情緒和曲風模型是用 Discogs 上的西方音樂訓練的**。J-pop、Vocaloid 的分類較粗，"
      "所以重點應該放在「相對 PJSK 平均的差異」，不是絕對機率。")
    w("6. **只有 3 到 5 首的作曲家，結論容易被單首特例左右。**")
    w("7. **所有數字都是相對 PJSK 收錄曲而言。**「慢」「暗」「不歡快」都是跟 PJSK 其他歌比較。")
    w("")
    w("---\n")
    w("產生方式：`python extract.py` 抽特徵 → `python analyze.py` 產生本報告。原始數據見 "
      "`song_features.csv`、`composer_profiles.csv`；Colab 版本見 `pjsk_composer_style.ipynb`。")

    pdir = os.path.join(a.report, "profiles")
    os.makedirs(pdir, exist_ok=True)
    for old_file in os.listdir(pdir):
        if old_file.endswith(".md"):
            os.remove(os.path.join(pdir, old_file))
    for name, text in profile_files.items():
        with open(os.path.join(pdir, f"{name}.md"), "w") as f:
            f.write(text + "\n")
    with open(os.path.join(a.report, "composer_profiles.md"), "w") as f:
        f.write("\n".join(out) + "\n")
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
