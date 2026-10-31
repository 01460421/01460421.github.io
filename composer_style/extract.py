"""PJSK 歌曲音訊特徵抽取。

對每首歌：
  1. 從 sekai.best 下載遊戲內音源（不保存音檔，只留下特徵）
  2. librosa：節奏、音色、能量、和聲等可解釋特徵
  3. Essentia：調性、Discogs 400 種風格機率、情緒／舞曲感模型、1280 維嵌入
  4. 從譜面 master.txt 讀出準確的 BPM 與變速次數

用法：
  python extract.py --models ./models --out ./out [--workers 3] [--limit 20]
輸出：
  out/features.csv   每首歌一列（含曲目資訊與可解釋特徵）
  out/genre400.npy   每首歌的 400 維風格機率（順序同 features.csv）
  out/embed.npy      每首歌的 1280 維 discogs-effnet 平均嵌入
"""
import argparse
import io
import json
import os
import re
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests

DB = "https://raw.githubusercontent.com/Sekai-World/sekai-master-db-diff/refs/heads/main/"
ASSET = "https://storage.sekai.best/sekai-jp-assets/music/"
VOCAL_PRIORITY = ["original_song", "virtual_singer", "sekai", "another_vocal",
                  "instrumental", "streaming_live", "april_fool_2022"]
UNIT_TAGS = {"vocaloid": "VIRTUAL SINGER", "light_music_club": "Leo/need",
             "idol": "MORE MORE JUMP!", "street": "Vivid BAD SQUAD",
             "theme_park": "ワンダーランズ×ショウタイム", "school_refusal": "25時、ナイトコードで。",
             "other": "其他"}
MOOD_HEADS = {  # 模型名稱 -> 正向類別的索引
    "mood_happy": 0, "mood_sad": 1, "mood_aggressive": 0, "mood_relaxed": 1,
    "danceability": 0, "mood_acoustic": 0, "mood_electronic": 0,
}


def get_json(name):
    r = requests.get(DB + name, timeout=60)
    r.raise_for_status()
    return r.json()


def build_song_table():
    musics = get_json("musics.json")
    vocals = get_json("musicVocals.json")
    tags = get_json("musicTags.json")
    now = time.time() * 1000

    unit_of = {}
    for t in tags:
        if t["musicTag"] in UNIT_TAGS:
            unit_of.setdefault(t["musicId"], []).append(UNIT_TAGS[t["musicTag"]])

    best_vocal = {}
    for v in vocals:
        if v["musicVocalType"] not in VOCAL_PRIORITY:
            continue
        rank = VOCAL_PRIORITY.index(v["musicVocalType"])
        cur = best_vocal.get(v["musicId"])
        if cur is None or rank < cur[0] or (rank == cur[0] and v["seq"] < cur[1]["seq"]):
            best_vocal[v["musicId"]] = (rank, v)

    rows = []
    for m in musics:
        if m["publishedAt"] > now or m["id"] not in best_vocal:
            continue
        v = best_vocal[m["id"]][1]
        rows.append({
            "music_id": m["id"], "title": m["title"], "composer": m["composer"],
            "arranger": m["arranger"], "lyricist": m["lyricist"],
            "unit": "/".join(unit_of.get(m["id"], [])),
            "newly_written": m.get("isNewlyWrittenMusic", False),
            "published": pd.to_datetime(m["publishedAt"], unit="ms").date().isoformat(),
            "vocal_type": v["musicVocalType"], "vocal_asset": v["assetbundleName"],
        })
    return pd.DataFrame(rows)


# ---------- 譜面 BPM ----------
def chart_bpm(music_id):
    url = f"{ASSET}music_score/{music_id:04d}_01/master.txt"
    try:
        txt = requests.get(url, timeout=30).text
    except Exception:
        return np.nan, np.nan
    defs = {k: float(v) for k, v in re.findall(r"#BPM(\w\w):\s*([\d.]+)", txt)}
    if not defs:
        return np.nan, np.nan
    # 小節 08 通道引用 BPM 編號；第一個出現的視為主 BPM，統計實際用到幾種
    used = []
    for meas, data in re.findall(r"#(\d{3})08:\s*(\w+)", txt):
        for i in range(0, len(data) - 1, 2):
            code = data[i:i + 2]
            if code != "00" and code in defs:
                used.append((int(meas), defs[code]))
    used.sort()
    main = used[0][1] if used else list(defs.values())[0]
    distinct = len({b for _, b in used}) if used else 1
    return main, distinct - 1


# ---------- 每個 worker 載入一次模型 ----------
_M = {}


def _init_models(model_dir):
    import essentia
    essentia.log.infoActive = False
    essentia.log.warningActive = False
    import essentia.standard as es
    _M["es"] = es
    _M["effnet"] = es.TensorflowPredictEffnetDiscogs(
        graphFilename=os.path.join(model_dir, "discogs-effnet-bs64-1.pb"),
        output="PartitionedCall:1")
    _M["genre"] = es.TensorflowPredict2D(
        graphFilename=os.path.join(model_dir, "genre_discogs400-discogs-effnet-1.pb"),
        input="serving_default_model_Placeholder", output="PartitionedCall:0")
    _M["heads"] = {
        h: es.TensorflowPredict2D(
            graphFilename=os.path.join(model_dir, f"{h}-discogs-effnet-1.pb"),
            output="model/Softmax")
        for h in MOOD_HEADS}
    _M["key"] = es.KeyExtractor(profileType="edma", sampleRate=22050)
    _M["rhythm"] = es.RhythmExtractor2013(method="degara")


def analyse(row, model_dir):
    import librosa
    if not _M:
        _init_models(model_dir)
    es = _M["es"]

    url = f"{ASSET}long/{row['vocal_asset']}/{row['vocal_asset']}.mp3"
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
        f.write(r.content)
        f.flush()
        y, sr = librosa.load(f.name, sr=22050, mono=True)
        y16 = es.MonoLoader(filename=f.name, sampleRate=16000, resampleQuality=4)()
        y44 = es.MonoLoader(filename=f.name, sampleRate=44100)()

    y, (t0, _) = librosa.effects.trim(y, top_db=50)  # 去掉頭尾靜音（遊戲音源開頭有空白）
    lead = t0 / sr  # 之後 Essentia 的節拍時間要扣掉這段
    out = {}
    # --- 節奏 ---
    bpm, bpm_changes = chart_bpm(row["music_id"])
    out["bpm"], out["bpm_changes"] = bpm, bpm_changes
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    dur = len(y) / sr
    out["duration"] = dur
    out["onset_rate"] = len(onsets) / dur
    # 節拍：用 Essentia（librosa.beat 在部分 numba 版本會 segfault）
    est_bpm, ticks, *_ = _M["rhythm"](y44)
    if not np.isfinite(bpm):
        out["bpm"] = bpm = float(est_bpm)
    beats = librosa.time_to_frames(np.asarray(ticks) - lead, sr=sr, hop_length=512)
    beats = beats[(beats >= 0) & (beats < len(onset_env) - 6)]
    # 兩套解碼器有數十毫秒的時間差：在 ±6 個 frame 內找讓拍點對齊音頭的整體偏移
    if len(beats):
        shift = max(range(-5, 6), key=lambda d: onset_env[np.clip(beats + d, 0, None)].mean())
        beats = np.clip(beats + shift, 0, None)
    out["beat_strength"] = (float(onset_env[beats].mean() / (onset_env.mean() + 1e-9))
                            if len(beats) else np.nan)

    # --- 音色 / 頻譜 ---
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    power = S ** 2
    total = power.sum() + 1e-12
    out["brightness"] = float(librosa.feature.spectral_centroid(S=S, sr=sr).mean())
    out["flatness"] = float(librosa.feature.spectral_flatness(S=S).mean())
    out["bass_ratio"] = float(power[freqs < 150].sum() / total)
    out["high_ratio"] = float(power[freqs > 4000].sum() / total)
    H, P = librosa.decompose.hpss(S)
    out["percussive_ratio"] = float((P ** 2).sum() / ((H ** 2).sum() + (P ** 2).sum() + 1e-12))
    mfcc = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=power, sr=sr)), n_mfcc=20)

    # --- 能量 / 動態 ---
    rms = librosa.feature.rms(S=S)[0]
    rms_db = librosa.amplitude_to_db(rms + 1e-9)
    out["loudness_db"] = float(np.mean(rms_db))
    out["dynamic_range_db"] = float(np.percentile(rms_db, 95) - np.percentile(rms_db, 10))
    win = int(5 * sr / 512)  # 5 秒一段
    seg = [rms_db[i:i + win].mean() for i in range(0, len(rms_db) - win, win)]
    out["section_contrast_db"] = float(np.std(seg)) if len(seg) > 1 else np.nan

    # --- 和聲 ---
    chroma = librosa.feature.chroma_stft(S=H ** 2, sr=sr)  # 只用和聲成分，避免鼓聲干擾
    c = chroma / (chroma.sum(0, keepdims=True) + 1e-9)
    out["harmonic_entropy"] = float(np.mean(-(c * np.log2(c + 1e-9)).sum(0)))
    if len(beats) > 2:
        bc = librosa.util.sync(chroma, beats, aggregate=np.median)
        bc = bc / (np.linalg.norm(bc, axis=0, keepdims=True) + 1e-9)
        out["chord_change"] = float(np.mean(1 - (bc[:, 1:] * bc[:, :-1]).sum(0)))
    else:
        out["chord_change"] = np.nan
    key, scale, strength = _M["key"](y.astype(np.float32))
    out["key"], out["scale"], out["key_strength"] = key, scale, float(strength)
    out["is_minor"] = int(scale == "minor")

    # --- 深度模型 ---
    emb = _M["effnet"](y16)
    genre = _M["genre"](emb).mean(0)
    for h, idx in MOOD_HEADS.items():
        out[h.replace("mood_", "")] = float(_M["heads"][h](emb).mean(0)[idx])

    for i in range(20):
        out[f"mfcc{i}_mean"] = float(mfcc[i].mean())
        out[f"mfcc{i}_std"] = float(mfcc[i].std())
    return out, genre.astype(np.float32), emb.mean(0).astype(np.float32)


def _job(row, model_dir, cache_dir):
    path = os.path.join(cache_dir, f"{row['music_id']}.npz")
    if os.path.exists(path):
        return row["music_id"], "cached"
    try:
        feats, genre, emb = analyse(row, model_dir)
    except Exception as e:  # 音源不存在等
        return row["music_id"], f"error: {e}"
    np.savez(path, feats=json.dumps(feats), genre=genre, emb=emb)
    return row["music_id"], "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    cache = os.path.join(a.out, "cache")
    os.makedirs(cache, exist_ok=True)
    songs = build_song_table()
    if a.limit:
        songs = songs.head(a.limit)
    print(f"{len(songs)} 首歌待分析", flush=True)

    rows = songs.to_dict("records")
    done = 0
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(_job, r, a.models, cache) for r in rows]
        for f in as_completed(futs):
            mid, status = f.result()
            done += 1
            if status != "cached":
                print(f"[{done}/{len(rows)}] {mid} {status}", flush=True)

    feats, genres, embs, keep = [], [], [], []
    for r in rows:
        p = os.path.join(cache, f"{r['music_id']}.npz")
        if not os.path.exists(p):
            continue
        z = np.load(p)
        feats.append({**r, **json.loads(str(z["feats"]))})
        genres.append(z["genre"])
        embs.append(z["emb"])
    pd.DataFrame(feats).to_csv(os.path.join(a.out, "features.csv"), index=False)
    np.save(os.path.join(a.out, "genre400.npy"), np.stack(genres))
    np.save(os.path.join(a.out, "embed.npy"), np.stack(embs))
    print(f"完成：{len(feats)} 首", flush=True)


if __name__ == "__main__":
    main()
