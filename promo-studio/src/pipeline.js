// 完整流程：爬取 → 腳本 → 配樂 → 渲染
const fs = require('fs');
const path = require('path');
const dns = require('dns').promises;
const net = require('net');
const { crawl } = require('./crawl');
const { makeStory } = require('./story');
const { makeMusic } = require('./music');
const { render } = require('./render');

function isPrivate(ip) {
  if (net.isIPv4(ip)) {
    const [a, b] = ip.split('.').map(Number);
    return a === 10 || a === 127 || a === 0 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 100 && b >= 64 && b <= 127) || a >= 224;
  }
  const v = ip.toLowerCase();
  return v === '::1' || v === '::' || v.startsWith('fc') || v.startsWith('fd') || v.startsWith('fe80') || v.startsWith('::ffff:') && isPrivate(v.slice(7));
}

async function normalizeUrl(input, { allowPrivate = false } = {}) {
  let s = String(input || '').trim();
  if (/^[a-z][a-z0-9+.-]*:/i.test(s) && !/^https?:\/\//i.test(s)) throw new Error('只支援 http / https 網址');
  if (!/^https?:\/\//i.test(s)) s = 'https://' + s;
  const u = new URL(s);
  if (!/^https?:$/.test(u.protocol)) throw new Error('只支援 http / https 網址');
  if (!allowPrivate) {
    const addrs = await dns.lookup(u.hostname, { all: true });
    if (!addrs.length || addrs.some((a) => isPrivate(a.address))) throw new Error('不允許內部網路位址');
  }
  return u.href;
}

async function runPipeline({ url, jobDir, lang = 'zh-Hant', maxPages = 5, useAI = true, allowPrivate = true, onStatus = () => {}, log = () => {} }) {
  const assets = path.join(jobDir, 'assets');
  fs.mkdirSync(assets, { recursive: true });
  const status = (stage, p, extra = {}) => onStatus({ stage, progress: p, ...extra });

  const target = await normalizeUrl(url, { allowPrivate });
  status('crawl', 0.01);
  const site = await crawl(target, { outDir: assets, maxPages, log, progress: (p) => status('crawl', 0.02 + p * 0.33) });
  if (!site.pages.length) throw new Error('抓不到任何頁面');
  fs.writeFileSync(path.join(jobDir, 'site.json'), JSON.stringify(site));

  status('script', 0.36);
  const { copy, timeline } = await makeStory(site, assets, { lang, useAI, log });
  fs.writeFileSync(path.join(jobDir, 'story.json'), JSON.stringify({ copy, timeline }, null, 1));
  log(`腳本完成（${copy.source === 'claude' ? 'Claude AI 文案' : '規則式文案'}），共 ${timeline.scenes.length} 個鏡頭、${timeline.duration} 秒`);
  status('music', 0.4, { copy, timeline });

  const wav = path.join(jobDir, 'music.wav');
  makeMusic(timeline, wav);
  log('配樂完成');

  status('render', 0.42);
  const out = path.join(jobDir, 'promo.mp4');
  await render({
    timeline, assetsDir: assets, audioFile: wav, outFile: out, log,
    onProgress: (p, eta) => status('render', 0.42 + p * 0.58, { eta: Math.round(eta) }),
    previewEvery: 45, onPreview: (buf) => fs.writeFile(path.join(jobDir, 'preview.jpg'), buf, () => {}),
  });
  status('done', 1);
  return { out, copy, timeline };
}

module.exports = { runPipeline, normalizeUrl };
