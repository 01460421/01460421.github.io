// Promo Studio 網頁伺服器（無框架）
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { runPipeline, normalizeUrl } = require('./src/pipeline');

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
  return {
    id: j.id, url: j.url, status: j.status, stage: j.stage, progress: j.progress, eta: j.eta, error: j.error,
    logs: j.logs.slice(-40), queuePos: j.status === 'queued' ? queue.indexOf(j) + 1 : 0,
    copy: j.copy, timeline: j.timeline, video: j.status === 'done' ? `/jobs/${j.id}/promo.mp4` : null,
    createdAt: j.createdAt,
  };
}

async function pump() {
  if (running || !queue.length) return;
  running = true;
  const job = queue.shift();
  job.status = 'running';
  try {
    await runPipeline({
      url: job.url, jobDir: job.dir, lang: job.lang, maxPages: job.pages, useAI: job.useAI, allowPrivate: ALLOW_PRIVATE,
      log: (m) => { job.logs.push({ t: Date.now(), m }); },
      onStatus: (s) => {
        job.stage = s.stage; job.progress = s.progress; job.eta = s.eta;
        if (s.copy) { job.copy = s.copy; job.timeline = s.timeline; }
      },
    });
    job.status = 'done';
  } catch (e) {
    job.status = 'error'; job.error = e.message;
    job.logs.push({ t: Date.now(), m: '錯誤：' + e.message });
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
        pages: Math.max(1, Math.min(8, +body.pages || 5)), useAI: body.ai !== false,
        status: 'queued', stage: 'queued', progress: 0, logs: [], createdAt: Date.now(),
      };
      jobs.set(id, job); queue.push(job); pump();
      return send(res, 201, publicJob(job));
    }

    let m;
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
