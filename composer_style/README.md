# PJSK 作曲家風格量化

- 總報告：[composer_profiles.md](composer_profiles.md)（方法、全體基準、團體比較、辨識度、排行、95 位作曲家摘要）
- 個別作曲家完整輪廓：[profiles/](profiles/)（22 項指標表、曲風、調性、編曲者、逐曲明細）
- Colab：[pjsk_composer_style.ipynb](pjsk_composer_style.ipynb)

| 檔案 | 說明 |
|---|---|
| `extract.py` | 下載遊戲音源，抽取 librosa／Essentia 特徵（不保存音檔） |
| `analyze.py` | 整理作曲家輪廓，產生報告與圖表 |
| `data/` | 已算好的特徵：`features.csv`、`genre400.npy`（Discogs 400 曲風機率）、`embed.npy`（1280 維嵌入） |
| `song_features.csv` | 每首歌的可解釋特徵 |
| `composer_profiles.csv` | 作曲家 × 特徵的平均 z 分數 |
| `fig_style_map.png`、`fig_heatmap.png` | 風格地圖、作曲家 × 指標熱圖 |

本機執行：

```bash
pip install librosa essentia-tensorflow matplotlib scikit-learn pandas
# 依 notebook 第 2 步下載模型到 ./models
python extract.py --models models --out data --workers 4   # 約 1 小時（--refresh-bpm 只重讀譜面 BPM）
python analyze.py --data data --models models --report .
```
