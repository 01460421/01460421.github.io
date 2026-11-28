# Promo Studio 🎬

**輸入一個網址，自動產生整站功能介紹宣傳片。**目標是 Apple 發表會／影視颶風那種節奏：3D 浮動視窗、鏡頭推近聚焦、逐字模糊浮現、對拍快剪、原創配樂。

## 它怎麼做

| 階段 | 做什麼 |
|---|---|
| 1. 深度瀏覽 `src/crawl.js` | Playwright 打開首頁，展開導覽群組，逐一點開導覽列／側欄的每個項目（包含單頁應用的按鈕式路由），預設 8 頁；自動關彈窗、觸發延遲載入；擷取每頁／每個視圖的畫面、功能段落特寫（記錄標題位置供鏡頭聚焦）、整頁長圖、手機版、icon、Logo 字標（自動裁白邊）、品牌色。 |
| 2. 腳本 `src/story.js` | 有 `ANTHROPIC_API_KEY` 時，Claude 會看截圖與內容，列出所有重點功能（6–12 個，依重要性排序）並寫 Apple 式短句；沒有金鑰則用規則產生。 |
| 3. 你來挑選（網頁版） | 勾選要放的功能、改文案、調順序，選收尾圖示樣式與影片長度，先看即時分鏡預覽再渲染；渲染完還能修改後重新渲染。 |
| 4. 配樂 `src/music.js` | 程序化合成：墊底和弦、低頻、鼓組、上升音、轉場重擊，全部對齊剪輯點。 |
| 5. 渲染 `src/render.js` + `public/stage.html` | 動態引擎完全由時間 t 決定每一格畫面，Playwright 逐格截圖 → ffmpeg 編成 1080p30 H.264 + AAC。 |

分鏡：開場品牌字 → 鋪陳金句 → 3D 主視覺 → 功能特寫 ×N（左右分割／全幅推鏡交替）→ **重點功能總覽牆**（所有勾選的功能都在這裡）→ 快剪 → 整頁滑動 → 頁面牆 → 手機展示 → 收尾 CTA。

### 選項

| 選項 | 值 |
|---|---|
| 影片長度 | `short` 精簡（3 個特寫）、`standard` 標準（5 個）、`full` 完整（全部特寫） |
| 收尾圖示 | `glass` 玻璃磚、`bare` 裸圖＋倒影、`logo` 網站字標、`mono` 首字母、`none` 純文字（`auto`：有圖示用玻璃，沒有用首字母） |

## 使用

需要 Node 20+、ffmpeg、Playwright Chromium。

```bash
cd promo-studio
npm install
npx playwright install chromium   # 若尚未安裝
export ANTHROPIC_API_KEY=sk-ant-...  # 選用：AI 文案

# 網頁版
npm start            # → http://localhost:3000

# 命令列
node cli.js https://example.com --pages 8 --length standard --icon glass --out promo.mp4
#   --lang en      英文文案
#   --no-ai        不呼叫 Claude
#   --main-only    只抓主站的視圖（不含另開的獨立頁面）
#   --extra /ep-calc,/foo   一定要包含的同網域頁面，頁內分頁（role=tab）會逐一拍攝
#   命令列會直接用推薦的功能渲染；要挑選請用網頁版
```

### Docker（建議部署方式）

```bash
docker build -t promo-studio .
docker run -p 3000:3000 -e ANTHROPIC_API_KEY=sk-ant-... promo-studio
```

可部署到任何能跑 Docker 的主機（Render、Fly.io、Railway、自己的 VPS）。渲染很吃 CPU，建議至少 2 vCPU / 2 GB RAM。Vercel / GitHub Pages 這類靜態或 serverless 平台跑不了（需要長時間執行的瀏覽器＋ffmpeg）。

### 環境變數

| 變數 | 用途 |
|---|---|
| `ANTHROPIC_API_KEY` | 啟用 Claude AI 文案（預設模型 `claude-opus-5-5`，可用 `PROMO_MODEL` 改） |
| `PORT` | 預設 3000 |
| `ALLOW_PRIVATE_URLS=1` | 允許內網網址（預設封鎖，避免公開部署被用來掃內網） |
| `MAX_QUEUE` | 排隊上限，預設 6 |
| `X264_PRESET` | 編碼速度，預設 `medium`；`veryfast` 較快、檔案較大 |

## 時間

一支約 50–60 秒的片：爬取 30–60 秒，渲染約 1,500–1,800 格，視 CPU 而定約 3–8 分鐘。網頁版在渲染時就會先播放「分鏡即時預覽」。
