// Promo Studio 網頁伺服器（無框架）
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { prepare, produce, timelineFor, normalizeUrl } = require('./src/pipeline');

const PORT = +process.env.PORT || 3000;
const JOBS_DIR = path.resolve(process.env.JOBS_DIR || path.join(__dirname, 'jobs'));
const PUBLIC = path.join(__dirname, 'public');
const ALLOW_PRIVATE = process.env.ALLOW_PRIVATE_URLS === '1';
const MAX_QUEUE = +process.env.MAX_QUEUE || 6;
fs.mkdirSync(JOBS_DIR, { recursive: true });

const jobs = new Map();
const queue = [];
let running = false;

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.ico': 'image/x-icon', '.mp4': 'video/mp4' };

function send(res, code, body, type = 'application/json') {
  res.writeHead(code, { 'Content-Type': type, 'Cache-Control': 'no-store' });
  res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
}

function serveFile(req, res, file, download) {
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) return send(res, 404, { error: 'not found' });
    const type = MIME[path.extname(file).toLowerCase()] || 'application/octet-stream';
    const headers = { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Cache-Control': 'no-cache' };
    if (download) headers['Content-Disposition'] = `attachment; filename="${download}"`;
    const range = req.headers.range && /bytes=(\d*)-(\d*)/.exec(req.headers.range);
    if (range) {
      const start = range[1] ? +range[1] : 0;
      const end = range[2] ? Math.min(+range[2], st.size - 1) : st.size - 1;
      if (start > end || start >= st.size) { res.writeHead(416, { 'Content-Range': `bytes */${st.size}` }); return res.end(); }
      res.writeHead(206, { ...headers, 'Content-Range': `bytes ${start}-${end}/${st.size}`, 'Content-Length': end - start + 1 });
      return fs.createReadStream(file, { start, end }).pipe(res);
    }
    res.writeHead(200, { ...headers, 'Content-Length': st.size });
    fs.createReadStream(file).pipe(res);
  });
}

function safeJoin(base, rel) {
  const p = path.resolve(base, '.' + path.sep + rel);
  return p.startsWith(base + path.sep) ? p : null;
}

function publicJob(j) {
  const copy = j.prep ? j.prep.copy : null;
  return {
    id: j.id, url: j.url, status: j.status, stage: j.stage, progress: j.progress, eta: j.eta, error: j.error, phase: j.phase,
    logs: j.logs.slice(-40), queuePos: j.status === 'queued' ? queue.indexOf(j) + 1 : 0,
    review: copy ? {
      source: copy.source, brand: copy.brand, tagline: copy.tagline, cta: copy.cta, outroLine: copy.outroLine, gridLine: copy.gridLine, hook: copy.hook,
      features: copy.features.map((f) => ({ sectionId: f.sectionId, on: f.on !== false, kicker: f.kicker, title: f.title, body: f.body, page: f.page, img: f.img, rect: f.rect })),
      icon: j.prep.site.iconFile, logo: j.prep.site.logoFile, palette: j.prep.palette,
    } : null,
    choices: j.choices || null,
    timeline: j.timeline || null, video: j.hasVideo ? `/jobs/${j.id}/promo.mp4?v=${j.videoVer}` : null,
    createdAt: j.createdAt,
  };
}

function sanitizeChoices(c = {}) {
  const out = {};
  if (['short', 'standard', 'full'].includes(c.length)) out.length = c.length;
  if (['auto', 'glass', 'bare', 'logo', 'mono', 'none'].includes(c.iconStyle)) out.iconStyle = c.iconStyle;
  for (const k of ['brand', 'tagline', 'cta', 'outroLine', 'gridLine']) if (typeof c[k] === 'string') out[k] = c[k].slice(0, 120);
  if (Array.isArray(c.hook)) out.hook = c.hook.slice(0, 3).map((x) => String(x).slice(0, 80));
  if (Array.isArray(c.features)) out.features = c.features.slice(0, 16).map((f) => ({
    sectionId: String(f.sectionId || ''), kicker: String(f.kicker ?? '').slice(0, 40), title: String(f.title ?? '').slice(0, 80), body: String(f.body ?? '').slice(0, 200),
  }));
  return out;
}

async function pump() {
  if (running || !queue.length) return;
  running = true;
  const job = queue.shift();
  job.status = 'running';
  const log = (m) => { job.logs.push({ t: Date.now(), m }); };
  const onStatus = (st) => { job.stage = st.stage; job.progress = st.progress; job.eta = st.eta; if (st.timeline) job.timeline = st.timeline; };
  try {
    if (job.phase === 'prepare') {
      job.prep = await prepare({ url: job.url, jobDir: job.dir, lang: job.lang, maxPages: job.pages, useAI: job.useAI, allowPrivate: ALLOW_PRIVATE, log, onStatus });
      job.timeline = job.prep.timeline;
      job.status = 'review'; job.stage = 'review'; job.progress = 0.4;
    } else {
      await produce(job.prep, job.choices || {}, { jobDir: job.dir, log, onStatus });
      job.hasVideo = true; job.videoVer = Date.now();
      job.status = 'done';
    }
  } catch (e) {
    job.status = 'error'; job.error = e.message;
    log('錯誤：' + e.message);
  } finally {
    running = false;
    pump();
  }
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let b = '';
    req.on('data', (d) => { b += d; if (b.length > 1e5) req.destroy(); });
    req.on('end', () => { try { resolve(b ? JSON.parse(b) : {}); } catch (e) { reject(e); } });
  });
}

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  const p = decodeURIComponent(u.pathname);
  try {
    if (req.method === 'GET' && (p === '/' || p === '/index.html')) return serveFile(req, res, path.join(PUBLIC, 'index.html'));
    if (req.method === 'GET' && p === '/stage.html') return serveFile(req, res, path.join(PUBLIC, 'stage.html'));
    if (req.method === 'GET' && p === '/api/config') return send(res, 200, { ai: !!(process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN), queue: queue.length, busy: running });

    if (req.method === 'POST' && p === '/api/jobs') {
      const body = await readBody(req);
      if (queue.length >= MAX_QUEUE) return send(res, 429, { error: '排隊的人太多了，請稍後再試' });
      let url;
      try { url = await normalizeUrl(body.url, { allowPrivate: ALLOW_PRIVATE }); } catch (e) { return send(res, 400, { error: '網址無效：' + e.message }); }
      const id = crypto.randomBytes(6).toString('hex');
      const job = {
        id, url, dir: path.join(JOBS_DIR, id), lang: body.lang === 'en' ? 'en' : 'zh-Hant',
        pages: Math.max(1, Math.min(16, +body.pages || 8)), useAI: body.ai !== false, phase: 'prepare',
        status: 'queued', stage: 'queued', progress: 0, logs: [], createdAt: Date.now(),
      };
      jobs.set(id, job); queue.push(job); pump();
      return send(res, 201, publicJob(job));
    }

    let m;
    if (req.method === 'POST' && (m = p.match(/^\/api\/jobs\/([a-f0-9]{12})\/(preview|render)$/))) {
      const j = jobs.get(m[1]);
      if (!j) return send(res, 404, { error: '找不到這個任務' });
      if (!j.prep) return send(res, 409, { error: '網站還在分析中' });
      if (j.status === 'queued' || j.status === 'running') return send(res, 409, { error: '正在處理中' });
      const choices = sanitizeChoices(await readBody(req));
      if (m[2] === 'preview') return send(res, 200, timelineFor(j.prep, choices));
      if (queue.length >= MAX_QUEUE) return send(res, 429, { error: '排隊的人太多了，請稍後再試' });
      j.choices = choices; j.phase = 'produce'; j.status = 'queued'; j.stage = 'queued'; j.error = null; j.progress = 0.4;
      queue.push(j); pump();
      return send(res, 202, publicJob(j));
    }
    if (req.method === 'GET' && (m = p.match(/^\/api\/jobs\/([a-f0-9]{12})$/))) {
      const j = jobs.get(m[1]);
      return j ? send(res, 200, publicJob(j)) : send(res, 404, { error: '找不到這個任務' });
    }
    if (req.method === 'GET' && (m = p.match(/^\/jobs\/([a-f0-9]{12})\/(.+)$/))) {
      const j = jobs.get(m[1]);
      if (!j) return send(res, 404, { error: 'not found' });
      const rel = m[2];
      if (!/^(promo\.mp4|preview\.jpg|assets\/[\w.-]+)$/.test(rel)) return send(res, 404, { error: 'not found' });
      const f = safeJoin(j.dir, rel);
      if (!f) return send(res, 400, { error: 'bad path' });
      const host = (() => { try { return new URL(j.url).hostname.replace(/^www\./, ''); } catch { return 'promo'; } })();
      return serveFile(req, res, f, u.searchParams.has('dl') ? `${host}-promo.mp4` : null);
    }
    send(res, 404, { error: 'not found' });
  } catch (e) {
    send(res, 500, { error: e.message });
  }
});

server.listen(PORT, () => console.log(`Promo Studio → http://localhost:${PORT}`));
