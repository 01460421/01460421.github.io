// 合成器：把錄到的畫面放進有陰影的視窗，依聚焦事件推近鏡頭，加上排版字幕
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const { pathToFileURL } = require('url');

const PUB = path.join(__dirname, '..', '..', 'public');

async function composeSegments(list, { fps = 30, log = () => {}, page: pageName = 'compose.html' } = {}) {
  const PAGE = path.join(PUB, pageName);
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files', '--force-color-profile=srgb'] });
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    for (const { data, outFile } of list) {
      await page.goto(pathToFileURL(PAGE).href, { waitUntil: 'load' });
      const base = pathToFileURL(path.dirname(data.frames[0].file)).href + '/';
      await page.evaluate(([d, b]) => window.__init(d, b), [data, base]);
      const total = Math.round(data.duration * fps);
      const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(fps), '-an', outFile], { stdio: ['pipe', 'ignore', 'pipe'] });
      let err = ''; ff.stderr.on('data', (x) => (err += x));
      const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg: ' + err.slice(-300))))));
      const t0 = Date.now();
      for (let i = 0; i < total; i++) {
        await page.evaluate((t) => window.__seek(t), i / fps);
        const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
        if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      }
      ff.stdin.end(); await done;
      log(`  合成 ${data.id}：${(total / fps).toFixed(1)} 秒，耗時 ${((Date.now() - t0) / 1000).toFixed(0)} 秒`);
    }
  } finally { await browser.close(); }
}

module.exports = { composeSegments };
