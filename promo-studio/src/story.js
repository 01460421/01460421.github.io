// 由爬取結果產生「腳本＋分鏡時間軸」：有 ANTHROPIC_API_KEY 時用 Claude 看圖寫文案，否則用規則產生
const fs = require('fs');
const path = require('path');

const BAR = 2; // 120 BPM，一小節 2 秒；所有場景長度對齊小節，剪輯點落在拍子上

// ---------- 色彩 ----------
function parseColor(c) {
  if (!c) return null;
  let m = c.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?/);
  if (m) { if (m[4] !== undefined && +m[4] < 0.5) return null; return [+m[1], +m[2], +m[3]]; }
  m = c.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (m) { let h = m[1]; if (h.length === 3) h = h.split('').map((x) => x + x).join(''); return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)); }
  return null;
}
function rgb2hsl([r, g, b]) {
  r /= 255; g /= 255; b /= 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b); const l = (mx + mn) / 2;
  if (mx === mn) return [0, 0, l];
  const d = mx - mn; const s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
  let h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}
const hsl = (h, s, l) => `hsl(${Math.round(((h % 360) + 360) % 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%)`;

function pickPalette(pages) {
  const tally = {};
  for (const p of pages) for (const [c, w] of Object.entries(p.colors || {})) tally[c] = (tally[c] || 0) + w;
  let best = null;
  for (const [c, w] of Object.entries(tally)) {
    const rgb = parseColor(c); if (!rgb) continue;
    const [h, s, l] = rgb2hsl(rgb);
    if (s < 0.35 || l < 0.22 || l > 0.78) continue;
    const score = w * (0.5 + s);
    if (!best || score > best.score) best = { h, s, l, score };
  }
  const h = best ? best.h : 211;
  const s = best ? Math.min(1, Math.max(0.6, best.s)) : 1;
  // 在深色背景上要夠亮
  return { accent: hsl(h, s, 0.6), accent2: hsl(h + 48, s, 0.62), accent3: hsl(h - 40, s, 0.58), hue: h };
}

// ---------- 規則式文案（無 API 金鑰時） ----------
const T = {
  'zh-Hant': {
    intro: '隆重介紹', scroll: '每一處細節，\n都經過打磨。', pages: (n) => `${n} 個頁面。\n一氣呵成。`,
    mobile: '放進口袋，\n隨時出發。', cta: '立即體驗', kicker: (i) => `功能 ${String(i + 1).padStart(2, '0')}`,
    hook: ['為你而生。', '比你想得更多。'],
    grid: '重點功能，\n一次看齊。',
  },
  en: {
    intro: 'Introducing', scroll: 'Every detail.\nConsidered.', pages: (n) => `${n} pages.\nOne seamless flow.`,
    mobile: 'Fits in your pocket.\nGoes everywhere.', cta: 'Try it now', kicker: (i) => `Feature ${String(i + 1).padStart(2, '0')}`,
    hook: ['Made for you.', 'More than you expect.'],
    grid: 'Everything you need.\nIn one place.',
  },
};

function brandFrom(home) {
  if (home.siteName) return home.siteName.trim();
  const parts = (home.title || '').split(/\s[|\-–—·:：]\s|\s?[|｜]\s?/).map((s) => s.trim()).filter(Boolean);
  if (!parts.length) return new URL(home.url).hostname.replace(/^www\./, '');
  return parts.sort((a, b) => a.length - b.length)[0];
}
function firstSentence(s, max) {
  if (!s) return '';
  s = String(s).replace(/[↗︎↗→›»]/g, '').trim();
  if (!/[\u2E80-\u9FFF]/.test(s)) max = Math.round(max * 2.4); // 拉丁文字較長
  const m = s.match(/^(.+?[。！？]|.+?[.!?](?=\s|$))/);
  let t = (m ? m[1] : s).trim();
  if (t.length > max) {
    const cut = t.slice(0, max);
    const dot = cut.lastIndexOf(' · ');
    if (dot > max * 0.4) return cut.slice(0, dot).trim();
    const at = Math.max(cut.lastIndexOf('，'), cut.lastIndexOf('、'), cut.lastIndexOf(','), cut.lastIndexOf('；'));
    t = at > max * 0.5 ? cut.slice(0, at) + (/[\u2E80-\u9FFF]/.test(cut) ? '。' : '.') : cut.replace(/\s+\S*$/, '').replace(/[\s.,，、。…:：-]+$/, '') + '…';
  }
  return t;
}
function shortTitle(s) {
  const t = String(s || '').replace(/[↗︎↗→›»]/g, '').split(/\s[|\-–—·:：]\s|[|｜]/)[0].trim();
  const max = /[\u2E80-\u9FFF]/.test(t) ? 16 : 28;
  return t.length > max ? t.slice(0, max - 1).replace(/\s+\S*$/, '').replace(/[\s.,，、。…:：-]+$/, '') + '…' : t;
}
function pageName(p, i) {
  if (i === 0) return null;
  return shortTitle(p.navText || p.heads?.[0]?.text || p.title);
}

// 段落 + 每個頁面／視圖本身（id: p{i}v）都是功能候選
function allSections(site) {
  const out = [];
  site.pages.forEach((p, pi) => {
    if (pi > 0 && p.hero) {
      const f = p.focus;
      out.push({ id: `p${pi}v`, pi, si: -1, page: p, view: true, img: p.hero, title: p.navText || (f && f.text) || p.title,
        desc: p.lead || (p.view ? '' : p.description) || '', rect: f ? { x: f.x, y: f.y, w: f.w, h: f.h } : { x: 360, y: 120, w: 720, h: 90 } });
    }
    p.sections.forEach((s, si) => out.push({ id: `p${pi}s${si}`, pi, si, page: p, ...s }));
  });
  return out;
}

// 所有段落 → 功能候選清單（規則式文案），依「有說明 > 頁面順序」排序並去重
function candidatesFor(site, lang) {
  const t = T[lang] || T['zh-Hant'];
  const out = [];
  const seen = new Set();
  const secs = allSections(site);
  // 頁面／視圖（導覽上的功能）優先，其次是有說明的段落
  const ranked = secs.slice().sort((a, b) => (b.view ? 2 : 0) + (b.desc ? 1 : 0) - ((a.view ? 2 : 0) + (a.desc ? 1 : 0)) || a.pi - b.pi || a.si - b.si);
  for (const s of ranked) {
    const title = shortTitle(s.title);
    const key = title.slice(0, 12).toLowerCase();
    if (!title || title.length < 2 || seen.has(key)) continue;
    if (/^[A-Za-z]+$/.test(title) && title.length < 10 && !s.desc) continue;
    // 數字、倒數、價格之類不是功能名稱
    if ((title.replace(/[^\p{L}]/gu, '').length < 2) || /^(還有|剩|剩餘|倒數)?\s*[\d,.:：\s]+\s*(天|小時|分|秒|%|days?|hours?)?$/i.test(title)) continue;
    seen.add(key);
    const words = (s.desc || '').split(/\s+/);
    const menuLike = words.length > 3 && !/[.。!?！？,，]/.test(s.desc) && words.filter((w) => /^[A-Z]/.test(w)).length / words.length > 0.5;
    const goodDesc = s.desc && s.desc.length > 8 && !/[·|｜]/.test(s.desc) && !menuLike;
    const body = firstSentence(goodDesc ? s.desc : s.page.description || s.desc || '', lang === 'en' ? 110 : 40);
    let kicker = s.view ? '' : pageName(s.page, s.pi) || '';
    if (!kicker || kicker === title) kicker = t.kicker(out.length);
    out.push({ sectionId: s.id, kicker, title, body, page: shortTitle(s.page.navText || s.page.title), img: s.img, rect: s.rect });
  }
  return out;
}

function heuristicCopy(site, lang) {
  const t = T[lang] || T['zh-Hant'];
  const home = site.pages[0];
  const brand = brandFrom(home);
  const tagline = firstSentence(home.description || home.heads[0]?.text || '', lang === 'en' ? 80 : 30) || brand;
  const features = candidatesFor(site, lang).map((f, i) => ({ ...f, on: i < 10 }));
  return {
    brand, tagline, intro: t.intro, hook: [tagline, ...t.hook].slice(0, 3),
    features, gridLine: t.grid, scrollLine: t.scroll, pagesLine: t.pages(site.pages.length), mobileLine: t.mobile,
    outroLine: tagline, cta: t.cta, source: 'heuristic',
  };
}

// ---------- Claude 文案 ----------
async function claudeCopy(site, lang, jobDir, log) {
  const Anthropic = require('@anthropic-ai/sdk');
  const { z } = require('zod');
  const { zodOutputFormat } = require('@anthropic-ai/sdk/helpers/zod');
  const client = new Anthropic();
  const secs = allSections(site);
  const Schema = z.object({
    brand: z.string(),
    intro: z.string(),
    tagline: z.string(),
    hook: z.array(z.string()),
    features: z.array(z.object({ sectionId: z.string(), kicker: z.string(), title: z.string(), body: z.string() })),
    gridLine: z.string(),
    scrollLine: z.string(),
    pagesLine: z.string(),
    mobileLine: z.string(),
    outroLine: z.string(),
    cta: z.string(),
  });
  const digest = {
    pages: site.pages.map((p, i) => ({
      index: i, url: p.url, title: p.title, description: p.description,
      text: p.bodyText.slice(0, i === 0 ? 3000 : 1200),
    })),
    sections: secs.map((s) => ({ id: s.id, page: s.pi, heading: s.title, text: s.desc })),
  };
  const langName = lang === 'en' ? 'English' : '繁體中文（台灣用語）';
  const prompt = `你是 Apple 發表會影片與「影視颶風」等級的廣告文案總監。根據下面這個網站的真實內容與截圖，替一支產品宣傳片寫字幕文案。

規則：
- 輸出語言：${langName}。
- 風格：極短、有力、有節奏、自信；像 Apple 廣告。一句一個想法，常用句號收尾。可用換行 \\n 斷句製造節奏（每段最多兩行）。
- 只寫網站真的有的功能，不可捏造數字或功能。
- brand：品牌／網站名稱（簡短）。intro：開場小字（如「隆重介紹」或「Introducing」）。
- tagline：一句總結價值的主標（中文 ≤ 14 字，英文 ≤ 7 個字）。
- hook：2–3 句開場鋪陳，每句 ≤ 12 字（英文 ≤ 6 words），層層推進。
- features：把這個網站「所有重點功能」都列出來，6–12 個，依重要性排序（最重要的放前面）。每個必須對應 sections 裡的一個 id（sectionId，不可重複，挑畫面最能代表該功能的段落）。不要漏掉主要功能；行銷口號、頁尾、登入等不算功能。kicker 是小標（≤ 6 字），title 是大標（≤ 12 字，英文 ≤ 6 words），body 是一句說明（≤ 28 字，英文 ≤ 16 words），要具體說出這個功能能幫使用者做什麼。
- gridLine：配合「所有功能一次排開」鏡頭的一句話。scrollLine：配合整頁滑動鏡頭。pagesLine：配合「多個頁面拼牆」鏡頭（共 ${site.pages.length} 頁）。mobileLine：配合手機畫面。
- outroLine：結尾標語。cta：行動呼籲（≤ 6 字）。

網站資料（JSON）：
${JSON.stringify(digest)}`;

  const content = [];
  const imgs = [site.pages[0].hero, ...site.pages.slice(1).map((p) => p.hero), ...secs.slice(0, 6).map((s) => s.img)].slice(0, 10);
  for (const f of imgs) {
    try {
      content.push({ type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: fs.readFileSync(path.join(jobDir, f)).toString('base64') } });
    } catch {}
  }
  content.push({ type: 'text', text: prompt });
  log && log('Claude 正在看截圖、整理所有重點功能…');
  const res = await client.messages.parse({
    model: process.env.PROMO_MODEL || 'claude-opus-5-5',
    max_tokens: 16000,
    output_config: { effort: 'medium', format: zodOutputFormat(Schema) },
    messages: [{ role: 'user', content }],
  });
  if (res.stop_reason === 'refusal' || !res.parsed_output) throw new Error(`Claude 未回傳文案（${res.stop_reason}）`);
  const out = res.parsed_output;
  const byId = Object.fromEntries(secs.map((s) => [s.id, s]));
  const used = new Set();
  const ai = out.features.filter((f) => byId[f.sectionId] && !used.has(f.sectionId) && used.add(f.sectionId)).slice(0, 12)
    .map((f) => ({ ...f, on: true, page: shortTitle(byId[f.sectionId].page.navText || byId[f.sectionId].page.title), img: byId[f.sectionId].img, rect: byId[f.sectionId].rect }));
  if (ai.length < 2) throw new Error('Claude 選的段落無效');
  // AI 沒選到的段落也留著，讓使用者自己勾
  const rest = candidatesFor(site, lang).filter((c) => !used.has(c.sectionId)).map((c) => ({ ...c, on: false }));
  out.features = ai.concat(rest);
  out.hook = out.hook.slice(0, 3);
  out.source = 'claude';
  return out;
}

// ---------- 使用者選擇 ----------
const LENGTHS = {
  short: { spot: 3, cuts: false, scroll: false, wall: false },
  standard: { spot: 5, cuts: true, scroll: true, wall: true },
  full: { spot: 12, cuts: true, scroll: true, wall: true },
};
const ICON_STYLES = ['auto', 'glass', 'bare', 'logo', 'mono', 'none'];

// choices：{ features:[{sectionId,kicker,title,body}]（依此順序、全部視為選取）, brand, tagline, cta, outroLine, hook }
function applyChoices(copy, choices = {}) {
  const c = { ...copy };
  for (const k of ['brand', 'tagline', 'cta', 'outroLine', 'gridLine']) if (typeof choices[k] === 'string' && choices[k].trim()) c[k] = choices[k].trim().slice(0, 120);
  if (Array.isArray(choices.hook)) c.hook = choices.hook.map((x) => String(x).trim()).filter(Boolean).slice(0, 3);
  if (!c.hook || !c.hook.length) c.hook = [c.tagline];
  if (Array.isArray(choices.features)) {
    const byId = Object.fromEntries(copy.features.map((f) => [f.sectionId, f]));
    const picked = [];
    for (const f of choices.features) {
      const base = byId[f.sectionId]; if (!base || picked.some((p) => p.sectionId === f.sectionId)) continue;
      picked.push({ ...base, on: true, kicker: String(f.kicker ?? base.kicker).slice(0, 40), title: String(f.title ?? base.title).slice(0, 80), body: String(f.body ?? base.body).slice(0, 200) });
    }
    // 預設編號的小標依新順序重新編號
    picked.forEach((f, i) => { const m = f.kicker.match(/^(功能|Feature)\s*\d+$/); if (m) f.kicker = `${m[1]} ${String(i + 1).padStart(2, '0')}`; });
    const rest = copy.features.filter((f) => !picked.some((p) => p.sectionId === f.sectionId)).map((f) => ({ ...f, on: false }));
    c.features = picked.concat(rest);
  }
  return c;
}

// ---------- 分鏡時間軸 ----------
function buildTimeline(site, copy, palette, opts = {}) {
  const secs = Object.fromEntries(allSections(site).map((s) => [s.id, s]));
  const home = site.pages[0];
  const domain = new URL(home.url).hostname.replace(/^www\./, '');
  const L = LENGTHS[opts.length] || LENGTHS.standard;
  const iconStyle = ICON_STYLES.includes(opts.iconStyle) ? opts.iconStyle : 'auto';
  const selected = copy.features.filter((f) => f.on !== false && secs[f.sectionId]);
  const scenes = [];
  const push = (type, bars, data = {}) => scenes.push({ type, dur: bars * BAR, ...data });

  push('intro', 2, { small: copy.intro, brand: copy.brand });
  push('hook', Math.max(1, Math.min(3, copy.hook.length)), { lines: copy.hook.slice(0, 3) });
  push('hero', 3, { img: home.hero, domain, title: copy.brand, tagline: copy.tagline });
  selected.slice(0, L.spot).forEach((f, i) => {
    const s = secs[f.sectionId];
    push('feature', 2, {
      variant: i % 2 === 0 ? (i % 4 === 0 ? 'left' : 'right') : 'bleed',
      img: s.img, rect: s.rect, kicker: f.kicker, title: f.title, body: f.body, domain: new URL(s.page.url).hostname.replace(/^www\./, ''),
      path: new URL(s.page.url).pathname,
    });
  });
  // 功能總覽牆：所有勾選的重點功能都會出現在這裡
  if (selected.length >= 3) {
    const items = selected.slice(0, 16).map((f) => ({ img: secs[f.sectionId].img, rect: secs[f.sectionId].rect, kicker: f.kicker, title: f.title }));
    push('grid', items.length > 8 ? 3 : 2, { line: copy.gridLine || (T[opts.lang] || T['zh-Hant']).grid, items });
  }
  if (L.cuts) {
    const usedIds = new Set(selected.map((f) => f.sectionId));
    const pool = Object.values(secs).sort((a, b) => (usedIds.has(a.id) ? 0 : 1) - (usedIds.has(b.id) ? 0 : 1));
    const heroes = site.pages.map((p) => ({ img: p.hero, rect: null, title: p.navText || p.title }));
    const cutsSrc = pool.map((s) => ({ img: s.img, rect: s.rect, title: (selected.find((f) => f.sectionId === s.id) || {}).title || s.title })).concat(heroes);
    if (cutsSrc.length >= 4) {
      const cuts = [];
      for (let i = 0; i < 8; i++) { const c = cutsSrc[i % cutsSrc.length]; cuts.push({ ...c, word: shortTitle(c.title) || copy.brand }); }
      push('cuts', 2, { cuts });
    }
  }
  const longest = site.pages.slice().sort((a, b) => (b.fullH || 0) - (a.fullH || 0))[0];
  if (L.scroll && longest && longest.full && longest.fullH > 1800) push('scroll', 3, { img: longest.full, h: longest.fullH, line: copy.scrollLine, domain });
  if (L.wall && site.pages.length >= 3) push('wall', 2, { imgs: site.pages.map((p) => p.hero), line: copy.pagesLine });
  if (site.mobile) push('mobile', 2, { img: site.mobile.full, h: site.mobile.h, w: site.mobile.w, line: copy.mobileLine });
  push('outro', 3, { brand: copy.brand, line: copy.outroLine, cta: copy.cta, domain, icon: site.iconFile, logo: site.logoFile, iconStyle });

  let t = 0;
  for (const s of scenes) { s.start = t; t += s.dur; }
  const dropAt = scenes.find((s) => s.type === 'hero').start;
  const outroAt = scenes[scenes.length - 1].start;
  return {
    width: opts.width || 1920, height: opts.height || 1080, fps: opts.fps || 30,
    duration: t, bpm: 120, dropAt, outroAt, palette, lang: opts.lang, scenes,
    cuts: scenes.map((s) => ({ t: s.start, type: s.type })),
  };
}

async function makeStory(site, jobDir, opts = {}) {
  const { lang = 'zh-Hant', useAI = true, log = () => {} } = opts;
  let copy = null;
  if (useAI && (process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN)) {
    try { copy = await claudeCopy(site, lang, jobDir, log); }
    catch (e) { log(`AI 文案失敗，改用規則產生：${e.message}`); }
  }
  if (!copy) copy = heuristicCopy(site, lang);
  const palette = pickPalette(site.pages);
  return { copy, palette, timeline: buildTimeline(site, copy, palette, opts) };
}

module.exports = { makeStory, heuristicCopy, pickPalette, buildTimeline, applyChoices, LENGTHS, ICON_STYLES };
