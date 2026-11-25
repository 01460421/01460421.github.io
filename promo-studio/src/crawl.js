// 爬取網站：截圖（桌機 hero、各段落特寫、整頁長圖、手機版）＋抽取文字結構與品牌色
const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');

const DESK = { width: 1440, height: 900 };
const MAX_FULL_H = 7000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function settle(page, timeout = 25000) {
  try { await page.waitForLoadState('networkidle', { timeout }); } catch {}
  await sleep(600);
}

async function dismissOverlays(page) {
  try {
    for (let round = 0; round < 3; round++) {
      const clicked = await page.evaluate(() => {
        const re = /^(accept|accept all|accept cookies|agree|i agree|got it|ok|okay|allow all|allow|close|skip|skip tour|dismiss|not now|no thanks|maybe later|later|×|✕|✖|x|同意|接受|全部接受|接受全部|我知道了|知道了|好|好的|關閉|关闭|略過|跳過|跳过|稍後|稍後再說|以後再說|不用了|同意並繼續|開始使用)$/i;
        let n = 0;
        for (const b of document.querySelectorAll('button,a,[role=button],[aria-label]')) {
          const t = (b.innerText || b.getAttribute('aria-label') || '').trim();
          const r = b.getBoundingClientRect();
          if (t && t.length < 24 && re.test(t) && r.width > 0 && r.height > 0) { try { b.click(); n++; } catch {} }
        }
        return n;
      });
      await page.keyboard.press('Escape').catch(() => {});
      await sleep(350);
      if (!clicked) break;
    }
    // 最後手段：移除仍覆蓋畫面的對話框／遮罩
    await page.evaluate(() => {
      const vw = innerWidth, vh = innerHeight;
      document.querySelectorAll('dialog[open],[role=dialog],[role=alertdialog],[aria-modal=true]').forEach((el) => el.remove());
      for (const el of document.querySelectorAll('body *')) {
        const s = getComputedStyle(el);
        if (s.position !== 'fixed') continue;
        const r = el.getBoundingClientRect();
        if (r.width * r.height > vw * vh * 0.3 && (parseInt(s.zIndex) || 0) > 0) el.remove();
      }
      for (const el of [document.documentElement, document.body]) {
        el.style.setProperty('overflow', 'auto', 'important');
        el.classList.remove('modal-open', 'no-scroll', 'overflow-hidden');
      }
      document.querySelectorAll('body > *').forEach((el) => {
        const s = getComputedStyle(el);
        if (s.filter && s.filter !== 'none') el.style.filter = 'none';
      });
    });
    await sleep(250);
  } catch {}
}

async function autoScroll(page) {
  try {
    await page.evaluate(async (maxH) => {
      const H = Math.min(document.documentElement.scrollHeight, maxH);
      for (let y = 0; y < H; y += Math.round(window.innerHeight * 0.6)) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 140));
      }
      window.scrollTo(0, 0);
      await new Promise((r) => setTimeout(r, 500));
    }, MAX_FULL_H);
  } catch {}
}

// 在頁面內執行：抽取結構
function extractInPage() {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 30 && r.height > 8 && s.visibility !== 'hidden' && s.display !== 'none' && parseFloat(s.opacity) > 0.05;
  };
  const meta = (n) => document.querySelector(`meta[name="${n}"],meta[property="${n}"]`)?.content || '';
  const sy = window.scrollY;

  // 標題候選：h1–h3，若太少則用「大字粗體」的元素補足（很多 SPA 不用語意標籤）
  let hEls = [...document.querySelectorAll('h1,h2,h3')].filter(visible);
  if (hEls.length < 5) {
    const extra = [];
    for (const el of document.querySelectorAll('h4,h5,div,span,p,strong,b,a,button,li')) {
      if (extra.length > 80) break;
      if (hEls.includes(el) || !visible(el)) continue;
      const direct = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join('').trim();
      if (direct.length < 2 || direct.length > 40) continue;
      const s = getComputedStyle(el);
      if (parseFloat(s.fontSize) >= 19 && parseInt(s.fontWeight) >= 600 && !el.closest('nav,header,footer')) extra.push(el);
    }
    hEls = hEls.concat(extra).sort((a, b) => (a.compareDocumentPosition(b) & 2 ? 1 : -1));
  }
  const heads = hEls.map((h, idx) => {
    h.setAttribute('data-pc-h', String(idx));
    const r = h.getBoundingClientRect();
    let desc = '';
    let n = h.nextElementSibling; let k = 0;
    while (n && k < 4 && !desc) {
      const t = clean(n.innerText);
      if (t.length > 12 && !/^H[1-3]$/.test(n.tagName)) desc = t;
      n = n.nextElementSibling; k++;
    }
    if (!desc) {
      const p = h.parentElement && h.parentElement.querySelector('p');
      if (p) desc = clean(p.innerText);
    }
    return { id: idx, tag: /^H[1-3]$/.test(h.tagName) ? h.tagName : 'H3', text: clean(h.innerText).slice(0, 140), desc: desc.slice(0, 280), y: r.top + sy, h: r.height };
  }).filter((h) => h.text.length >= 2 && h.y < 60000);

  const links = [...document.querySelectorAll('a[href]')].map((a) => ({
    href: a.href, text: clean(a.innerText).slice(0, 60), inNav: !!a.closest('nav,header,[role=navigation]'),
  }));

  // 品牌色：按鈕／連結的背景與文字顏色
  const colors = {};
  const add = (c, w) => { if (c && !/rgba\(0, 0, 0, 0\)|transparent/.test(c)) colors[c] = (colors[c] || 0) + w; };
  document.querySelectorAll('button,a,[class*=btn],[class*=button]').forEach((el, i) => {
    if (i > 400) return;
    const s = getComputedStyle(el);
    add(s.backgroundColor, 3); add(s.color, 1);
  });
  document.querySelectorAll('h1,h2,svg,[class*=logo]').forEach((el, i) => {
    if (i > 200) return;
    const s = getComputedStyle(el); add(s.color, 1); add(s.fill, 1);
  });
  const themeColor = meta('theme-color');
  if (themeColor) colors[themeColor] = (colors[themeColor] || 0) + 6;

  const icons = [...document.querySelectorAll('link[rel*=icon]')].map((l) => ({ href: l.href, sizes: l.getAttribute('sizes') || '', rel: l.rel }));
  let logo = null;
  const logoEl = [...document.querySelectorAll('header img, header svg, nav img, nav svg, a[href="/"] img, a[href="/"] svg, [class*=logo] img, [class*=logo] svg, img[alt*=logo i], [id*=logo] img')].find(visible);
  if (logoEl) { const r = logoEl.getBoundingClientRect(); logo = { x: r.left, y: r.top + sy, w: r.width, h: r.height }; }

  return {
    url: location.href,
    title: clean(document.title),
    description: meta('description') || meta('og:description'),
    siteName: meta('og:site_name') || meta('application-name') || meta('apple-mobile-web-app-title'),
    ogImage: meta('og:image'),
    lang: document.documentElement.lang || '',
    heads, links, colors, icons, logo,
    bg: getComputedStyle(document.body).backgroundColor,
    bodyText: clean(document.body.innerText).slice(0, 5000),
    docH: document.documentElement.scrollHeight,
  };
}

function pickSubpages(home, origin, max) {
  const seen = new Set([new URL(home.url).pathname.replace(/\/(index\.html?)?$/, '')]);
  const bad = /\.(pdf|zip|png|jpe?g|gif|svg|webp|mp4|mp3|dmg|exe)$|\/(login|signin|sign-in|signup|logout|cart|checkout|account)\b|^mailto:|^tel:|^javascript:/i;
  const scored = [];
  for (const l of home.links) {
    let u; try { u = new URL(l.href); } catch { continue; }
    if (u.origin !== origin || bad.test(u.pathname) || bad.test(l.href)) continue;
    const key = u.pathname.replace(/\/(index\.html?)?$/, '');
    if (seen.has(key)) continue;
    seen.add(key);
    const depth = key.split('/').filter(Boolean).length;
    scored.push({ url: u.origin + u.pathname + u.search, text: l.text, score: (l.inNav ? 10 : 0) + (l.text ? 2 : 0) - depth });
  }
  return scored.sort((a, b) => b.score - a.score).slice(0, max);
}

async function captureSections(page, info, dir, prefix, maxSections, log) {
  const out = [];
  // 選取有意義的標題，避免太接近的重複
  const cands = [];
  let lastY = -1e9;
  for (const h of info.heads) {
    if (h.y - lastY < 260) continue;
    if (h.text.length > 90) continue;
    cands.push(h); lastY = h.y;
  }
  // h1 優先保留，其餘依是否有描述排序，再按位置
  const chosen = cands
    .map((h, i) => ({ h, i, s: (h.desc ? 3 : 0) + (h.tag === 'H2' ? 2 : h.tag === 'H1' ? 1 : 0) }))
    .sort((a, b) => b.s - a.s || a.i - b.i)
    .slice(0, maxSections)
    .sort((a, b) => a.h.y - b.h.y)
    .map((x) => x.h);

  for (const h of chosen) {
    try {
      const targetY = Math.max(0, h.y - 140);
      await page.evaluate((y) => window.scrollTo(0, y), targetY);
      await sleep(450);
      // 捲動後重新量測（因為 sticky、動畫等）
      const rect = await page.evaluate((id) => {
        const el = document.querySelector(`[data-pc-h="${id}"]`);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const box = (el.closest('section,article,[class*=card],[class*=feature]') || el.parentElement).getBoundingClientRect();
        return { x: r.left, y: r.top, w: r.width, h: r.height, bx: box.left, by: box.top, bw: box.width, bh: box.height };
      }, h.id);
      const file = `${prefix}_s${out.length}.jpg`;
      await page.screenshot({ path: path.join(dir, file), type: 'jpeg', quality: 86 });
      out.push({ img: file, title: h.text, desc: h.desc, tag: h.tag, rect: rect || { x: 120, y: 140, w: 800, h: 80 } });
    } catch (e) { log && log(`  段落截圖略過：${e.message.split('\n')[0]}`); }
  }
  return out;
}

async function crawl(startUrl, opts = {}) {
  const { outDir, maxPages = 5, log = () => {}, progress = () => {} } = opts;
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ args: ['--hide-scrollbars'] });
  const result = { pages: [], mobile: null, iconFile: null, logoFile: null };
  try {
    const ctx = await browser.newContext({ viewport: DESK, deviceScaleFactor: 2, locale: 'zh-TW', ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    page.setDefaultTimeout(30000);

    const visit = async (url, idx, maxSections) => {
      log(`開啟 ${url}`);
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await settle(page);
      await dismissOverlays(page);
      await autoScroll(page);
      await settle(page, 6000);
      await dismissOverlays(page);
      const info = await page.evaluate(extractInPage);
      const prefix = `p${idx}`;
      const hero = `${prefix}_hero.jpg`;
      await page.evaluate(() => window.scrollTo(0, 0)); await sleep(500);
      await page.screenshot({ path: path.join(outDir, hero), type: 'jpeg', quality: 88 });
      // 整頁長圖（1x 以節省記憶體）
      const fullH = Math.min(info.docH, MAX_FULL_H);
      const full = `${prefix}_full.jpg`;
      try {
        await page.screenshot({ path: path.join(outDir, full), type: 'jpeg', quality: 82, scale: 'css', fullPage: true, clip: { x: 0, y: 0, width: DESK.width, height: fullH } });
      } catch (e) { log(`  長圖失敗：${e.message.split('\n')[0]}`); }
      const sections = await captureSections(page, info, outDir, prefix, maxSections, log);
      return { ...info, hero, full, fullH, sections, links: idx === 0 ? info.links : undefined };
    };

    const home = await visit(startUrl, 0, 6);
    result.pages.push(home);
    progress(0.3);

    // logo 特寫
    if (home.logo && home.logo.w > 10) {
      try {
        await page.evaluate(() => window.scrollTo(0, 0)); await sleep(300);
        const pad = 10;
        const clip = { x: Math.max(0, home.logo.x - pad), y: Math.max(0, home.logo.y - pad), width: Math.min(600, home.logo.w + pad * 2), height: Math.min(200, home.logo.h + pad * 2) };
        await page.screenshot({ path: path.join(outDir, 'logo.png'), clip, omitBackground: true });
        result.logoFile = 'logo.png';
      } catch {}
    }
    // icon：優先 apple-touch-icon / 大尺寸
    const icons = (home.icons || []).sort((a, b) => {
      const sz = (x) => (/apple/.test(x.rel) ? 1000 : 0) + (parseInt(x.sizes) || (x.href.endsWith('.svg') ? 500 : 16));
      return sz(b) - sz(a);
    });
    for (const ic of icons.concat([{ href: new URL('/apple-touch-icon.png', home.url).href }])) {
      try {
        const res = await page.request.get(ic.href, { timeout: 10000 });
        const ct = res.headers()['content-type'] || '';
        if (!res.ok() || !/image/.test(ct)) continue;
        const ext = /svg/.test(ct) ? 'svg' : /png/.test(ct) ? 'png' : /jpe?g/.test(ct) ? 'jpg' : /webp/.test(ct) ? 'webp' : /icon/.test(ct) ? 'ico' : 'png';
        const body = await res.body();
        if (body.length < 200) continue;
        fs.writeFileSync(path.join(outDir, `icon.${ext}`), body);
        result.iconFile = `icon.${ext}`;
        break;
      } catch {}
    }

    const origin = new URL(home.url).origin;
    const subs = pickSubpages(home, origin, Math.max(0, maxPages - 1));
    for (let i = 0; i < subs.length; i++) {
      try {
        const p = await visit(subs[i].url, i + 1, 3);
        p.navText = subs[i].text;
        result.pages.push(p);
      } catch (e) { log(`  略過 ${subs[i].url}：${e.message.split('\n')[0]}`); }
      progress(0.3 + 0.55 * ((i + 1) / Math.max(1, subs.length)));
    }
    await ctx.close();

    // 手機版
    try {
      log('擷取手機版畫面');
      const d = devices['iPhone 15'];
      const mctx = await browser.newContext({ ...d, viewport: { width: 393, height: 852 }, deviceScaleFactor: 2, locale: 'zh-TW', ignoreHTTPSErrors: true });
      const mp = await mctx.newPage();
      await mp.goto(startUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await settle(mp);
      await dismissOverlays(mp);
      await autoScroll(mp);
      await mp.evaluate(() => window.scrollTo(0, 0)); await sleep(500);
      const mh = await mp.evaluate(() => document.documentElement.scrollHeight);
      const h = Math.min(mh, 4200);
      await mp.screenshot({ path: path.join(outDir, 'mobile_full.jpg'), type: 'jpeg', quality: 85, scale: 'css', fullPage: true, clip: { x: 0, y: 0, width: 393, height: h } });
      result.mobile = { full: 'mobile_full.jpg', h, w: 393 };
      await mctx.close();
    } catch (e) { log(`  手機版失敗：${e.message.split('\n')[0]}`); }
    progress(1);
  } finally {
    await browser.close();
  }
  return result;
}

module.exports = { crawl };
