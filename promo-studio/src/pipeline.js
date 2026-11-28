// 完整流程：爬取 → 腳本 → 配樂 → 渲染
const fs = require('fs');
const path = require('path');
const dns = require('dns').promises;
const net = require('net');
const { crawl } = require('./crawl');
const { makeStory, buildTimeline, applyChoices } = require('./story');
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

// 第一階段：爬取＋寫腳本（之後讓使用者挑選）
async function prepare({ url, jobDir, lang = 'zh-Hant', maxPages = 8, useAI = true, allowPrivate = true, viewsOnly = false, extraUrls = [], brief = '', onStatus = () => {}, log = () => {} }) {
  const assets = path.join(jobDir, 'assets');
  fs.mkdirSync(assets, { recursive: true });
  const status = (stage, p, extra = {}) => onStatus({ stage, progress: p, ...extra });
  const target = await normalizeUrl(url, { allowPrivate });
  status('crawl', 0.01);
  // 額外頁面只允許同網域（避免被拿來抓別的站／內網）
  const origin = new URL(target).origin;
  const extras = (extraUrls || []).map((u) => { try { return new URL(String(u).trim(), target); } catch { return null; } })
    .filter((u) => u && u.origin === origin).map((u) => u.href).slice(0, 6);
  const site = await crawl(target, { outDir: assets, maxPages, viewsOnly, extraUrls: extras, log, progress: (p) => status('crawl', 0.02 + p * 0.33) });
  if (!site.pages.length) throw new Error('抓不到任何頁面');
  fs.writeFileSync(path.join(jobDir, 'site.json'), JSON.stringify(site));
  status('script', 0.36);
  const { copy, palette, timeline } = await makeStory(site, assets, { lang, useAI, log, brief });
  fs.writeFileSync(path.join(jobDir, 'story.json'), JSON.stringify({ copy, palette }, null, 1));
  const n = copy.features.filter((f) => f.on !== false).length;
  log(`腳本完成（${copy.source === 'claude' ? 'Claude AI 文案' : '規則式文案'}）：找到 ${copy.features.length} 個功能候選，預選 ${n} 個`);
  return { site, copy, palette, timeline, lang };
}

// 依使用者選擇產生時間軸（不渲染，可用來預覽）
function timelineFor(prep, choices = {}) {
  const copy = applyChoices(prep.copy, choices);
  return { copy, timeline: buildTimeline(prep.site, copy, prep.palette, { lang: prep.lang, length: choices.length, iconStyle: choices.iconStyle, spot: choices.spot }) };
}

// 第二階段：配樂＋渲染
async function produce(prep, choices, { jobDir, onStatus = () => {}, log = () => {} }) {
  const assets = path.join(jobDir, 'assets');
  const { copy, timeline } = timelineFor(prep, choices);
  fs.writeFileSync(path.join(jobDir, 'final.json'), JSON.stringify({ choices, copy, timeline }, null, 1));
  const status = (stage, p, extra = {}) => onStatus({ stage, progress: p, ...extra });
  status('music', 0.4, { copy, timeline });
  const wav = path.join(jobDir, 'music.wav');
  makeMusic(timeline, wav);
  log(`配樂完成；${timeline.scenes.length} 個鏡頭、${timeline.duration} 秒`);
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

// 一次跑完（CLI 用）
async function runPipeline(opts) {
  const prep = await prepare(opts);
  return produce(prep, opts.choices || {}, opts);
}

module.exports = { runPipeline, prepare, produce, timelineFor, normalizeUrl };
