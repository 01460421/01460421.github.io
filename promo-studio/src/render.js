// 逐格渲染：Playwright 打開 stage.html，每一格 seek(t) → 截圖 → 送進 ffmpeg 編碼 H.264 + AAC
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const { pathToFileURL } = require('url');

const STAGE = path.join(__dirname, '..', 'public', 'stage.html');

async function render({ timeline, assetsDir, audioFile, outFile, onProgress = () => {}, log = () => {}, previewEvery = 0, onPreview }) {
  const { fps, duration, width, height } = timeline;
  const browser = await chromium.launch({ args: ['--hide-scrollbars', '--force-color-profile=srgb', '--allow-file-access-from-files'] });
  let ff;
  try {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    page.on('pageerror', (e) => log(`stage 錯誤：${e.message}`));
    await page.goto(pathToFileURL(STAGE).href, { waitUntil: 'load', timeout: 60000 });
    const base = pathToFileURL(assetsDir).href + '/';
    const info = await page.evaluate(([s, b]) => window.__init(s, b), [timeline, base]);
    log(`舞台就緒：${info.images} 張素材，${duration.toFixed(1)} 秒`);

    const total = Math.round(duration * fps);
    const args = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-'];
    if (audioFile) args.push('-i', audioFile);
    args.push('-c:v', 'libx264', '-preset', process.env.X264_PRESET || 'medium', '-crf', process.env.X264_CRF || '20', '-pix_fmt', 'yuv420p', '-r', String(fps));
    if (audioFile) args.push('-c:a', 'aac', '-b:a', '192k', '-shortest');
    args.push('-movflags', '+faststart', outFile);
    ff = spawn('ffmpeg', args, { stdio: ['pipe', 'ignore', 'pipe'] });
    let ffErr = '';
    ff.stderr.on('data', (d) => (ffErr += d));
    const ffDone = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg 失敗：' + ffErr.slice(-500))))));

    const t0 = Date.now();
    for (let i = 0; i < total; i++) {
      await page.evaluate((t) => window.__seek(t), i / fps);
      const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      if (previewEvery && onPreview && i % previewEvery === 0) onPreview(buf, i / fps);
      if (i % 15 === 0) {
        const el = (Date.now() - t0) / 1000;
        onProgress((i + 1) / total, el / (i + 1) * (total - i - 1));
      }
    }
    ff.stdin.end();
    await ffDone;
    onProgress(1, 0);
  } finally {
    await browser.close();
    if (ff && ff.exitCode === null && !ff.stdin.writableEnded) try { ff.kill('SIGKILL'); } catch {}
  }
}

// 單張預覽（除錯／縮圖用）
async function stills({ timeline, assetsDir, times, outPattern }) {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  try {
    const page = await browser.newPage({ viewport: { width: timeline.width, height: timeline.height } });
    page.on('pageerror', (e) => console.error('stage error', e.message));
    await page.goto(pathToFileURL(STAGE).href);
    await page.evaluate(([s, b]) => window.__init(s, b), [timeline, pathToFileURL(assetsDir).href + '/']);
    const files = [];
    for (const t of times) {
      await page.evaluate((x) => window.__seek(x), t);
      const f = outPattern.replace('%t', t.toFixed(2));
      await page.screenshot({ path: f, type: 'jpeg', quality: 85 });
      files.push(f);
    }
    return files;
  } finally { await browser.close(); }
}

module.exports = { render, stills };
