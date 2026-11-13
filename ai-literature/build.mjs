// 建置：content/*.txt → index.html（分頁網頁版）＋ ai-literature.pdf
// 用法：node build.mjs [--artifact <輸出路徑>]
// 需要 Node 22、Playwright（Chromium）、Python 的 fonttools 與 brotli，以及能連上 Google Fonts 的網路。
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, readdirSync, mkdtempSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const here = dirname(fileURLToPath(import.meta.url));
const TITLE = 'AI文學創作巔峰集';
const FONT_LINK = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;600&display=swap">';

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
// 標點擠壓：連續兩個全形標點之間，收掉半個字的空白
const squeeze = s => s
  .replace(/([」』）》])(?=[，。、；：？！「『（《」』）》])/g, '<span class="sq-r">$1</span>')
  .replace(/([，。、；：？！])([「『（《])/g, '$1<span class="sq-l">$2</span>');
const inline = s => squeeze(esc(s)).replace(/\*([^*]+)\*/g, '<em>$1</em>');

// ---------- 解析 ----------
// @part 卷次|卷名|文類|題句        整頁的卷首
// @piece 種類|篇名|副題            新的一篇，另起一頁（種類：prose poem verse play）
// @raw 類別 … @end                 整頁的原樣 HTML（書名頁、版權頁）
// @toc                             目錄的位置
// 篇內：@sec（分隔）@sec 一（小節）@sub（小標）@epi 引文|出處 @note @sig @center @break
function parse(text) {
  const items = [];
  let piece = null, para = [], display = '';
  const flush = () => {
    if (!piece || !para.length) { para = []; return; }
    const lines = para; para = [];
    const k = piece.kind;
    if (k === 'poem' || k === 'verse') {
      piece.blocks.push({ html: `<div class="st">${lines.map(l => `<span class="l">${inline(l)}</span>`).join('')}</div>` });
      return;
    }
    const t = lines.join('');
    if (k === 'play') {
      if (/^（.*）$/.test(t)) { piece.blocks.push({ html: `<p class="stage">${inline(t)}</p>`, split: true }); return; }
      const m = t.match(/^([^：（]{1,5})：(.*)$/);
      if (m) { piece.blocks.push({ html: `<p class="dl"><b>${esc(m[1])}</b>${inline(m[2])}</p>`, split: true }); return; }
    }
    piece.blocks.push({ html: `<p>${inline(t)}</p>`, split: true });
  };
  const src = text.split('\n');
  for (let i = 0; i < src.length; i++) {
    const line = src[i].replace(/\s+$/, '');
    if (!line.startsWith('@')) { if (line === '') flush(); else para.push(line); continue; }
    flush();
    const [, cmd, rest = ''] = line.match(/^@(\S+)\s*(.*)$/);
    const f = rest.split('|').map(s => s.trim());
    if (cmd === 'raw') {
      const buf = [];
      while (++i < src.length && src[i].trim() !== '@end') buf.push(src[i]);
      const html = buf.join('\n');
      items.push({ type: 'full', html: `<div class="full ${f[0]}">${html}</div>` });
      display += html.replace(/<[^>]+>/g, '');
      piece = null;
    } else if (cmd === 'toc') {
      items.push({ type: 'toc' }); piece = null;
    } else if (cmd === 'part') {
      const [no, name, genre, motto = ''] = f;
      items.push({ type: 'full', part: { no, name, genre },
        html: `<div class="full part"><div class="no">${esc(no)}</div><h2>${esc(name)}</h2><div class="genre">${esc(genre)}</div><div class="dia">◆</div><div class="line">${inline(motto)}</div></div>` });
      display += no + name; piece = null;
    } else if (cmd === 'piece') {
      const [kind, title, sub = ''] = f;
      piece = { type: 'piece', kind, title, blocks: [{ keep: true,
        html: `<div class="tb"><h2>${esc(title)}</h2>${sub ? `<div class="sub">${esc(sub)}</div>` : ''}</div>` }] };
      items.push(piece); display += title;
    } else if (!piece) {
      throw new Error(`第 ${i + 1} 行：@${cmd} 不在任何一篇裡面`);
    } else if (cmd === 'sec') {
      if (rest) { piece.blocks.push({ keep: true, html: `<div class="sech">${esc(rest)}</div>` }); display += rest; }
      else piece.blocks.push({ keep: true, html: '<div class="sec">◆◆◆</div>' });
    } else if (cmd === 'sub') {
      piece.blocks.push({ keep: true, html: `<div class="subh">${esc(rest)}</div>` }); display += rest;
    } else if (cmd === 'epi') {
      piece.blocks.push({ keep: true, html: `<div class="epi">${inline(f[0])}${f[1] ? `<cite>——${esc(f[1])}</cite>` : ''}</div>` });
    } else if (cmd === 'note') {
      piece.blocks.push({ html: `<div class="note">${inline(rest)}</div>` });
    } else if (cmd === 'sig') {
      piece.blocks.push({ html: `<p class="sig">${inline(rest)}</p>` });
    } else if (cmd === 'center') {
      piece.blocks.push({ html: `<p class="center">${inline(rest)}</p>` });
    } else if (cmd === 'break') {
      piece.blocks.push({ brk: true });
    } else throw new Error(`第 ${i + 1} 行：不認得 @${cmd}`);
  }
  flush();
  return { items, display };
}

// ---------- 分頁（在瀏覽器裡執行）----------
function paginateInPage({ items, tocSheets, title }) {
  const book = document.getElementById('book');
  book.innerHTML = '';
  const sheets = [], entries = [], warn = [];
  let part = null;
  const newSheet = (cls) => {
    const s = document.createElement('section');
    s.className = 'sheet' + (cls ? ' ' + cls : '');
    s.innerHTML = '<header class="rh"></header><div class="body"></div><footer class="folio"></footer>';
    book.appendChild(s); sheets.push(s);
    return s;
  };
  const fits = (el, body) => el.getBoundingClientRect().bottom <= body.getBoundingClientRect().bottom + 0.6;

  // 把段落照實際的斷行位置拆成兩段；回傳 null 表示整段搬到下一頁
  const split = (el, body) => {
    const limit = body.getBoundingClientRect().bottom + 0.6;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    const lines = [];
    let lastTop = -1e9, node;
    while ((node = walker.nextNode())) {
      for (let i = 0; i < node.length; i++) {
        range.setStart(node, i); range.setEnd(node, i + 1);
        const r = range.getClientRects()[0];
        if (!r || r.width === 0) continue;
        if (r.top > lastTop + 6) { lines.push({ node, i, bottom: r.bottom }); lastTop = r.top; }
        else lines[lines.length - 1].bottom = Math.max(lines[lines.length - 1].bottom, r.bottom);
      }
    }
    let fit = lines.filter(l => l.bottom <= limit).length;
    const rest = lines.length - fit;
    if (rest === 1 && fit >= 3) fit -= 1;            // 不讓單獨一行落到下一頁
    else if (rest === 1) return null;
    if (fit < 2) return null;                        // 頁尾也不留單獨一行
    const at = lines[fit];
    range.setStart(at.node, at.i); range.setEndAfter(el.lastChild);
    const tail = el.cloneNode(false);
    tail.classList.add('cont');
    tail.appendChild(range.extractContents());
    el.classList.add('split-head');
    return tail;
  };

  const flow = (piece, blocks) => {
    let sheet = newSheet(piece.cls), body = sheet.querySelector('.body');
    const first = sheet;
    for (const b of blocks) {
      if (b.brk) { sheet = newSheet(piece.cls); body = sheet.querySelector('.body'); continue; }
      const holder = document.createElement('div');
      holder.innerHTML = b.html;
      let el = holder.firstElementChild;
      if (b.keep) el.dataset.keep = '1';
      body.appendChild(el);
      let guard = 0;
      while (!fits(el, body)) {
        if (++guard > 40) { warn.push('放不進一頁：' + piece.title); break; }
        const tail = b.split ? split(el, body) : null;
        const moving = [];
        if (tail) moving.push(tail);
        else {
          moving.push(el);
          while (el.previousElementSibling && el.previousElementSibling.dataset.keep) moving.unshift(el.previousElementSibling), moving[0].remove();
          el.remove();
          if (!body.children.length) {                // 整頁只有它也放不下
            moving.forEach(m => body.appendChild(m));
            warn.push('溢出：' + piece.title + '（第 ' + sheets.length + ' 頁）');
            break;
          }
        }
        sheet = newSheet(piece.cls); body = sheet.querySelector('.body');
        moving.forEach(m => body.appendChild(m));
        el = moving[moving.length - 1];
      }
    }
    return first;
  };

  let tocAt = -1;
  for (const it of items) {
    if (it.type === 'full') {
      const s = newSheet('bare');
      s.querySelector('.body').remove();
      s.insertAdjacentHTML('beforeend', it.html);
      if (it.part) { part = it.part; entries.push({ part: it.part, sheet: s }); }
    } else if (it.type === 'toc') {
      tocAt = sheets.length;
      for (let i = 0; i < tocSheets; i++) newSheet('toc');
    } else {
      const start = sheets.length;
      const first = flow({ title: it.title, cls: it.kind }, it.blocks);
      for (let i = start; i < sheets.length; i++) { sheets[i].dataset.piece = it.title; sheets[i].dataset.part = part ? part.no + '　' + part.name : title; }
      first.dataset.first = '1';
      entries.push({ title: it.title, sheet: first });
    }
  }

  // 目錄
  let tocUsed = 0;
  if (tocAt >= 0) {
    const pageOf = s => sheets.indexOf(s) + 1;
    const blocks = [{ keep: true, html: '<div class="tb"><h2>目錄</h2></div>' }];
    for (const e of entries) {
      if (e.part) blocks.push({ keep: true, html: `<div class="tp">${e.part.no}　${e.part.name}</div>` });
      else blocks.push({ html: `<div class="te"><a href="#p${pageOf(e.sheet)}"><span>${e.title}</span><i></i><b>${pageOf(e.sheet)}</b></a></div>` });
    }
    const before = sheets.length;
    flow({ title: '目錄', cls: 'toc' }, blocks);
    const made = sheets.splice(before);
    tocUsed = made.length;
    if (tocUsed === tocSheets) {
      made.forEach((m, i) => { sheets[tocAt + i].replaceWith(m); sheets[tocAt + i] = m; m.dataset.piece = '目錄'; m.dataset.part = title; });
      made[0].dataset.first = '1';
    } else made.forEach(m => m.remove());
  }

  sheets.forEach((s, i) => {
    const n = i + 1;
    s.id = 'p' + n; s.dataset.n = n;
    s.classList.add(n % 2 ? 'recto' : 'verso');
    if (s.classList.contains('bare')) return;
    s.querySelector('.folio').textContent = n;
    if (!s.dataset.first) s.querySelector('.rh').textContent = n % 2 ? s.dataset.piece : s.dataset.part;
  });

  const fill = s => {
    const body = s.querySelector('.body');
    if (!body || !body.lastElementChild) return 1;
    return (body.lastElementChild.getBoundingClientRect().bottom - body.getBoundingClientRect().top) / body.getBoundingClientRect().height;
  };
  const report = [];
  let lastPart = null;
  entries.forEach((e, i) => {
    const n = sheets.indexOf(e.sheet) + 1;
    if (e.part) { lastPart = e.part; report.push({ part: e.part.no + '　' + e.part.name, page: n }); return; }
    const next = entries[i + 1] ? sheets.indexOf(entries[i + 1].sheet) : sheets.length;
    report.push({ title: e.title, page: n, pages: next - n + 1, lastFill: +fill(sheets[next - 1]).toFixed(2) });
  });
  sheets.forEach(s => { delete s.dataset.piece; delete s.dataset.part; delete s.dataset.first; s.querySelectorAll('[data-keep]').forEach(k => delete k.dataset.keep); });
  return { html: book.innerHTML, total: sheets.length, tocUsed, report, warn };
}

// ---------- 標題字型：把「逆雨」裁成只含用到的字 ----------
function subsetDisplayFont(chars) {
  const dir = mkdtempSync(join(tmpdir(), 'niyu-'));
  const out = join(dir, 'sub.woff2');
  const py = `
import sys
from fontTools.ttLib import TTFont
from fontTools import subset
src, out, text = sys.argv[1], sys.argv[2], sys.argv[3]
cmap = TTFont(src, lazy=True).getBestCmap()
missing = sorted({c for c in text if ord(c) not in cmap and not c.isspace()})
opts = subset.Options(); opts.flavor = 'woff2'; opts.layout_features = ['kern', 'liga', 'onum', 'pnum']
f = TTFont(src); s = subset.Subsetter(opts); s.populate(text=text); s.subset(f)
f.flavor = 'woff2'; f.save(out)
print(''.join(missing))
`;
  const missing = execFileSync('python3', ['-c', py, join(here, '..', 'fonts', 'NiYu-Regular.ttf'), out, chars], { encoding: 'utf8' }).trim();
  return { b64: readFileSync(out).toString('base64'), missing };
}

// ---------- 組頁 ----------
function chrome(report, { pdf }) {
  let toc = '';
  for (const r of report) {
    toc += r.part ? `<div class="tp">${esc(r.part)}</div>`
      : `<div class="te"><a href="#p${r.page}"><span>${esc(r.title)}</span><b>${r.page}</b></a></div>`;
  }
  return `<div class="bar"><div class="bar-in">
<a class="bar-title" href="#p1">${TITLE}</a>
<span class="where" id="where" aria-live="off"></span>
<button class="nav" id="prev" type="button" aria-label="上一頁">←</button>
<button class="nav" id="next" type="button" aria-label="下一頁">→</button>
<button id="open-toc" type="button">目錄</button>
${pdf ? '<a class="btn" href="ai-literature.pdf">PDF</a>' : ''}
</div></div>
<div class="panel" id="panel" hidden><div class="panel-in">
<div class="panel-head"><h2>目錄</h2><button id="shut-toc" type="button">關閉</button></div>
${toc}
</div></div>`;
}

const css = readFileSync(join(here, 'src/reader.css'), 'utf8');
const js = readFileSync(join(here, 'src/reader.js'), 'utf8');
const files = readdirSync(join(here, 'content')).filter(f => f.endsWith('.txt')).sort();
const { items, display } = parse(files.map(f => readFileSync(join(here, 'content', f), 'utf8')).join('\n\n'));
const font = subsetDisplayFont([...new Set(display + TITLE + '目錄卷一二三四五六七八九十0123456789　◆')].join(''));
if (font.missing) console.log('⚠ 逆雨字型缺字（會退回思源宋體）：' + font.missing);
const fontFace = `@font-face{font-family:"NiYuBook";src:url(data:font/woff2;base64,${font.b64}) format("woff2");font-display:block}`;
const head = `<title>${TITLE}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="一本由 AI 寫成的一百頁文學作品集：詩、小說、散文、極短篇、擬古、寓言與獨幕劇。">
${FONT_LINK}
<style>
${fontFace}
${css}</style>`;
const doc = (inner, opt) => `<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
${head}
</head>
<body>
${inner}
</body>
</html>
`;
const page = (bookHtml, report, opt) => `${chrome(report, opt)}
<main class="desk"><div class="book" id="book">${bookHtml}</div></main>
<script>
${js}</script>`;

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 900, height: 1000 }, colorScheme: 'light' });
const tab = await ctx.newPage();
const work = join(mkdtempSync(join(tmpdir(), 'book-')), 'work.html');
// 先把全文灌進去一次，讓瀏覽器把用得到的字型子集都載完，量出來的行才會準
const allText = items.map(it => it.html || (it.blocks || []).map(b => b.html || '').join('')).join('');
writeFileSync(work, doc(`<main class="desk"><div class="book" id="book"><section class="sheet"><div class="body">${allText}<b style="font-weight:600">${esc(display)}</b></div></section></div></main>`));
await tab.goto(pathToFileURL(work).href, { waitUntil: 'networkidle' });
await tab.evaluate(() => document.fonts.ready);
await tab.waitForTimeout(800);
await tab.evaluate(() => document.fonts.ready);

let result, tocSheets = 2;
for (let tries = 0; tries < 4; tries++) {
  result = await tab.evaluate(paginateInPage, { items, tocSheets, title: TITLE });
  if (result.tocUsed === tocSheets || result.tocUsed === 0) break;
  tocSheets = result.tocUsed;
}

const out = join(here, 'index.html');
writeFileSync(out, doc(page(result.html, result.report, { pdf: true })));
const art = process.argv.indexOf('--artifact');
if (art > 0) writeFileSync(process.argv[art + 1], head + '\n' + page(result.html, result.report, { pdf: false }) + '\n');

await tab.setViewportSize({ width: 1000, height: 1000 });
await tab.goto(pathToFileURL(out).href, { waitUntil: 'networkidle' });
await tab.evaluate(() => document.fonts.ready);
await tab.emulateMedia({ media: 'print', colorScheme: 'light' });
await tab.pdf({ path: join(here, 'ai-literature.pdf'), width: '148mm', height: '210mm', printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
await browser.close();

for (const r of result.report) {
  console.log(r.part ? `\n${String(r.page).padStart(3)}  ── ${r.part}` : `${String(r.page).padStart(3)}  ${r.title}  （${r.pages} 頁，末頁 ${Math.round(r.lastFill * 100)}%）`);
}
result.warn.forEach(w => console.log('⚠ ' + w));
const chars = items.reduce((n, it) => n + (it.html || (it.blocks || []).map(b => b.html || '').join('')).replace(/<[^>]+>/g, '').replace(/\s/g, '').length, 0);
console.log(`\n共 ${result.total} 頁，約 ${chars} 字`);
