// 操作教學錄製器：在真實網站上自動操作，疊加游標／點擊光圈／聚焦框／字幕，逐格擷取並輸出分段影片
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 注入頁面的疊加層（每次換頁都會重新注入）
const OVERLAY = () => {
  if (window.__pc) return;
  const boot = () => {
    if (window.__pc || !document.documentElement) return;
    const root = document.createElement('div');
    root.id = '__pc_root';
    root.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147483647;font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif';
    root.innerHTML = `
      <div id="__pc_hl" style="position:fixed;border:3px solid #39c5bb;border-radius:14px;box-shadow:0 0 0 9999px rgba(0,0,0,.28),0 0 30px rgba(57,197,187,.8);opacity:0;transition:all .45s cubic-bezier(.2,.8,.2,1)"></div>
      <div id="__pc_rip" style="position:fixed;width:20px;height:20px;margin:-10px 0 0 -10px;border-radius:50%;border:3px solid #39c5bb;opacity:0"></div>
      <svg id="__pc_cur" width="30" height="34" viewBox="0 0 30 34" style="position:fixed;left:0;top:0;filter:drop-shadow(0 3px 6px rgba(0,0,0,.45));transform:translate(-100px,-100px)">
        <path d="M3 2 L3 26 L9.5 20 L14 31 L18.5 29 L14 18.5 L23 18.5 Z" fill="#fff" stroke="#111" stroke-width="2" stroke-linejoin="round"/></svg>
      <div id="__pc_badge" style="position:fixed;left:22px;top:18px;padding:8px 16px;border-radius:999px;background:rgba(20,20,24,.78);color:#fff;font-size:15px;font-weight:700;letter-spacing:.04em;backdrop-filter:blur(12px);opacity:0;transition:opacity .4s;box-shadow:0 6px 20px rgba(0,0,0,.25)"></div>
      <div id="__pc_cap" style="position:fixed;left:50%;bottom:34px;transform:translateX(-50%) translateY(12px);max-width:1180px;padding:16px 30px;border-radius:18px;background:rgba(16,16,20,.82);color:#fff;font-size:26px;font-weight:600;line-height:1.45;text-align:center;letter-spacing:.01em;backdrop-filter:blur(14px);box-shadow:0 12px 40px rgba(0,0,0,.35);opacity:0;transition:opacity .35s,transform .35s"></div>`;
    document.documentElement.appendChild(root);
    const cur = root.querySelector('#__pc_cur'), cap = root.querySelector('#__pc_cap'), hl = root.querySelector('#__pc_hl'), rip = root.querySelector('#__pc_rip'), badge = root.querySelector('#__pc_badge');
    const st = { x: innerWidth * 0.62, y: innerHeight * 0.55 };
    const place = () => { cur.style.transform = `translate(${st.x - 3}px,${st.y - 2}px)`; };
    place();
    window.__pc = {
      pos: () => ({ x: st.x, y: st.y }),
      setPos(x, y) { st.x = x; st.y = y; place(); },
      move(x, y, ms) {
        const x0 = st.x, y0 = st.y, t0 = performance.now();
        // 微弧線，像真人移動
        const cx = (x0 + x) / 2 + (y - y0) * 0.12, cy = (y0 + y) / 2 - (x - x0) * 0.12;
        return new Promise((res) => {
          const f = (now) => {
            let p = Math.min(1, (now - t0) / ms); const e = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
            st.x = (1 - e) * (1 - e) * x0 + 2 * (1 - e) * e * cx + e * e * x; st.y = (1 - e) * (1 - e) * y0 + 2 * (1 - e) * e * cy + e * e * y; place();
            if (p < 1) requestAnimationFrame(f); else res();
          };
          requestAnimationFrame(f);
        });
      },
      click() {
        rip.animate([{ opacity: 0.95, transform: 'scale(.4)' }, { opacity: 0, transform: 'scale(3.2)' }], { duration: 520, easing: 'cubic-bezier(.2,.8,.2,1)' });
        rip.style.left = st.x + 'px'; rip.style.top = st.y + 'px';
        cur.animate([{ transform: cur.style.transform + ' scale(1)' }, { transform: cur.style.transform + ' scale(.82)' }, { transform: cur.style.transform + ' scale(1)' }], { duration: 220 });
      },
      say(t) {
        if (!t) { cap.style.opacity = 0; cap.style.transform = 'translateX(-50%) translateY(12px)'; return; }
        cap.textContent = t; cap.style.opacity = 1; cap.style.transform = 'translateX(-50%) translateY(0)';
      },
      hl(r) {
        if (!r) { hl.style.opacity = 0; return; }
        const pad = 8;
        Object.assign(hl.style, { left: r.x - pad + 'px', top: r.y - pad + 'px', width: r.w + pad * 2 + 'px', height: r.h + pad * 2 + 'px', opacity: 1 });
      },
      badge(t) { badge.textContent = t || ''; badge.style.opacity = t ? 1 : 0; },
    };
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  new MutationObserver(() => { if (!document.getElementById('__pc_root') && document.documentElement) { window.__pc = null; boot(); } }).observe(document, { childList: true, subtree: false });
};

class Recorder {
  constructor({ outDir, viewport = { width: 1600, height: 900 }, scale = 1.2, log = console.log, storage = {} }) {
    this.outDir = outDir; this.viewport = viewport; this.scale = scale; this.log = log; this.storage = storage;
    this.frames = []; this.segments = []; this.cur = null; this.badgeText = '';
    fs.mkdirSync(path.join(outDir, 'frames'), { recursive: true });
  }

  async start(url) {
    this.browser = await chromium.launch({ args: ['--hide-scrollbars', '--force-color-profile=srgb'] });
    this.ctx = await this.browser.newContext({ viewport: this.viewport, deviceScaleFactor: this.scale, locale: 'zh-TW' });
    await this.ctx.addInitScript(OVERLAY);
    // 預先寫入 localStorage（例如關掉新手導覽、提示泡泡）
    await this.ctx.addInitScript((kv) => { try { for (const [k, v] of Object.entries(kv)) if (localStorage.getItem(k) == null) localStorage.setItem(k, v); } catch (e) {} }, this.storage);
    this.page = await this.ctx.newPage();
    this.page.setDefaultTimeout(15000);
    if (url) await this.goto(url);
    await this._startCast();
  }

  async _startCast() {
    this.cdp = await this.ctx.newCDPSession(this.page);
    let n = this.frames.length;
    this.cdp.on('Page.screencastFrame', async (f) => {
      const file = path.join(this.outDir, 'frames', `f${String(n++).padStart(6, '0')}.jpg`);
      fs.writeFile(file, Buffer.from(f.data, 'base64'), () => {});
      this.frames.push({ file, ts: f.metadata.timestamp });
      try { await this.cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }); } catch {}
    });
    await this.cdp.send('Page.startScreencast', { format: 'jpeg', quality: 88, maxWidth: Math.round(this.viewport.width * this.scale), maxHeight: Math.round(this.viewport.height * this.scale), everyNthFrame: 1 });
  }

  async goto(url) {
    await this.page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    try { await this.page.waitForLoadState('networkidle', { timeout: 15000 }); } catch {}
    await sleep(500);
    if (this.badgeText) await this.page.evaluate((t) => window.__pc && window.__pc.badge(t), this.badgeText).catch(() => {});
  }

  // ---- 分段（每章一段） ----
  begin(id, badge) {
    this.cur = { id, start: Date.now() / 1000 };
    this.badgeText = badge || '';
    return this.page.evaluate((t) => window.__pc && window.__pc.badge(t), this.badgeText).catch(() => {});
  }
  async end() {
    await this.say('');
    await this.hl(null);
    await sleep(300);
    this.cur.end = Date.now() / 1000;
    this.segments.push(this.cur);
    this.log(`  段落 ${this.cur.id}：${(this.cur.end - this.cur.start).toFixed(1)} 秒`);
    this.cur = null;
  }

  // ---- 動作 ----
  async _el(target) {
    if (typeof target !== 'string') return target;
    const loc = this.page.locator(target).first();
    await loc.waitFor({ state: 'visible', timeout: 8000 });
    return loc;
  }
  async _rect(loc) {
    // 只有不在畫面內時才捲動（太高的元素不捲，避免跳動）
    const moved = await loc.evaluate((el) => {
      const r = el.getBoundingClientRect();
      const inView = r.top >= 40 && r.bottom <= innerHeight - 140;
      if (inView || r.height > innerHeight * 0.8) return false;
      el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' }); return true;
    });
    if (moved) await sleep(700);
    const b = await loc.boundingBox();
    return b && { x: b.x, y: b.y, w: b.width, h: b.height };
  }
  async say(text, ms = 0) {
    await this.page.evaluate((t) => window.__pc && window.__pc.say(t), text || '').catch(() => {});
    if (ms) await sleep(ms);
  }
  async hl(target, ms = 0) {
    if (!target) { await this.page.evaluate(() => window.__pc && window.__pc.hl(null)).catch(() => {}); return; }
    try {
      const r = await this._rect(await this._el(target));
      await this.page.evaluate((rr) => window.__pc && window.__pc.hl(rr), r);
      if (ms) { await sleep(ms); await this.hl(null); }
    } catch (e) { this.log(`  （聚焦略過：${target}）`); if (ms) await sleep(ms); }
  }
  async move(target, ms = 700) {
    const loc = await this._el(target);
    const r = await this._rect(loc);
    if (!r) return null;
    const x = r.x + Math.min(r.w / 2, 60), y = r.y + r.h / 2;
    await this.page.evaluate(([x, y, ms]) => window.__pc && window.__pc.move(x, y, ms), [x, y, ms]);
    await sleep(80);
    return loc;
  }
  async click(target, caption, { wait = 900, hl = false } = {}) {
    try {
      if (caption) await this.say(caption);
      const loc = await this.move(target);
      if (hl) await this.hl(loc);
      await this.page.evaluate(() => window.__pc && window.__pc.click());
      await sleep(140);
      await loc.click({ timeout: 5000 });
      await sleep(wait);
      if (hl) await this.hl(null);
      return true;
    } catch (e) { this.log(`  （點擊略過：${target} — ${e.message.split('\n')[0]}）`); await sleep(wait); return false; }
  }
  async type(target, text, caption, { wait = 900, enter = false, clear = true } = {}) {
    try {
      if (caption) await this.say(caption);
      const loc = await this.move(target);
      await this.page.evaluate(() => window.__pc && window.__pc.click());
      await loc.click({ timeout: 5000 });
      if (clear) await loc.fill('');
      await loc.pressSequentially(text, { delay: 110 });
      if (enter) await loc.press('Enter');
      await sleep(wait);
      return true;
    } catch (e) { this.log(`  （輸入略過：${target} — ${e.message.split('\n')[0]}）`); await sleep(wait); return false; }
  }
  async select(target, value, caption, { wait = 1000 } = {}) {
    try {
      if (caption) await this.say(caption);
      const loc = await this.move(target);
      await this.page.evaluate(() => window.__pc && window.__pc.click());
      await loc.selectOption(value);
      await sleep(wait);
      return true;
    } catch (e) { this.log(`  （選單略過：${target} — ${e.message.split('\n')[0]}）`); await sleep(wait); return false; }
  }
  async scroll(by, ms = 1200) {
    await this.page.evaluate((by) => window.scrollBy({ top: by, behavior: 'smooth' }), by);
    await sleep(ms);
  }
  async top(ms = 700) { await this.page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' })); await sleep(ms); }
  async keys(text, caption, wait = 900) {
    if (caption) await this.say(caption);
    await this.page.keyboard.type(text, { delay: 120 });
    await sleep(wait);
  }
  async key(k, wait = 600) { await this.page.keyboard.press(k); await sleep(wait); }
  wait(ms) { return sleep(ms); }

  async stop() {
    try { await this.cdp.send('Page.stopScreencast'); } catch {}
    await sleep(400);
    await this.browser.close();
  }

  // ---- 輸出：每段依時間戳組成固定 30fps 影片 ----
  encodeSegment(seg, outFile, fps = 30) {
    const fr = this.frames;
    const W = Math.round(this.viewport.width * this.scale), H = Math.round(this.viewport.height * this.scale);
    let i0 = fr.findIndex((f) => f.ts >= seg.start);
    if (i0 < 0) i0 = fr.length - 1;
    const startIdx = Math.max(0, i0 - 1);
    const list = [];
    for (let i = startIdx; i < fr.length && fr[i].ts < seg.end; i++) {
      const t0 = Math.max(fr[i].ts, seg.start);
      const t1 = Math.min(i + 1 < fr.length ? fr[i + 1].ts : seg.end, seg.end);
      if (t1 > t0) list.push(`file '${fr[i].file}'\nduration ${(t1 - t0).toFixed(4)}`);
    }
    if (!list.length) throw new Error('段落沒有畫面：' + seg.id);
    const last = list[list.length - 1].split('\n')[0];
    const txt = path.join(this.outDir, `${seg.id}.txt`);
    fs.writeFileSync(txt, list.join('\n') + '\n' + last + '\n');
    const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', txt,
      '-vf', `scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,fps=${fps},format=yuv420p`,
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-r', String(fps), '-an', outFile]);
    if (r.status !== 0) throw new Error('ffmpeg 失敗：' + r.stderr.toString().slice(-400));
    return outFile;
  }
}

module.exports = { Recorder };
