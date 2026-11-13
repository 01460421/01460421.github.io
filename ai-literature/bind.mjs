// 線裝本：把已經分好頁的 index.html 重新拼成「筒子葉」（A4 橫向、單面印、對摺）
// 用法：先 node build.mjs，再 node bind.mjs
// 產生 binding/leaves.pdf（內頁）、binding/cover.pdf（封面、封底、題簽）、binding/guide.pdf（裝訂指南）
// 以及指南用的兩張圖 binding/mock.png、binding/leaf.png
import { createRequire } from 'node:module';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, 'binding');
const FONT_LINK = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;600&display=swap">';

// 打眼的位置（公釐）：離書背 12，離天地各 15，中間等分。指南裡的圖也用這組數字。
export const HOLES = { inset: 12, ys: [15, 75, 135, 195] };

const hanNum = n => {
  const d = '〇一二三四五六七八九';
  if (n < 10) return d[n];
  if (n < 20) return '十' + (n % 10 ? d[n % 10] : '');
  return d[Math.floor(n / 10)] + '十' + (n % 10 ? d[n % 10] : '');
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 }, javaScriptEnabled: false, colorScheme: 'light' });
const tab = await ctx.newPage();
await tab.goto(pathToFileURL(join(here, 'index.html')).href, { waitUntil: 'networkidle' });
const book = await tab.evaluate(() => ({
  css: [...document.querySelectorAll('style')].map(s => s.textContent).join('\n'),
  sheets: [...document.querySelectorAll('#book .sheet')].map(s => ({
    cls: s.className, html: s.innerHTML, part: s.querySelector('.part .no') ? s.querySelector('.part .no').textContent : null,
  })),
  rain: document.querySelector('.cover svg').outerHTML,
}));

// ---- 線裝本自己的幾頁 ----
// 第一頁換成內封（封面另外印）；書末加一葉牌記，留給訂書的人落款
const pages = book.sheets.map(s => ({ ...s }));
pages[0] = { cls: 'sheet bare odd', part: null, html:
  `<div class="full neifeng"><div class="nf-by">Claude　著</div><h1><span class="tcy">AI</span>文學創作巔峰集</h1><div class="nf-yr">丙午冬月　讀者手訂</div></div>` };
pages.push({ cls: 'sheet bare odd', part: '跋', html:
  `<div class="full paiji"><div class="pj">
<p>此書成於丙午冬月，凡一百頁，分八卷。</p>
<p>撰者無手，不能自訂，茲以散葉五十一付與讀者：對摺，理齊，打四眼，穿一線。</p>
<p>線過之日，方是書成之日。</p>
</div>
<div class="sign"><span>訂書者</span><i></i><span>時在</span><i class="s"></i><span>年</span><i class="s"></i><span>月</span></div>
<div class="sign"><span>此為第</span><i class="s"></i><span>冊</span></div></div>` });
pages.push({ cls: 'sheet bare even', part: null, html: '' });

let juan = '卷首';
const leaves = [];
for (let k = 0; k * 2 < pages.length; k++) {
  const a = pages[k * 2], b = pages[k * 2 + 1];
  if (a.part) juan = a.part;
  const label = juan;
  if (b && b.part) juan = b.part;
  const fish = '<svg class="fish" viewBox="0 0 12 5" preserveAspectRatio="none"><path d="M0 0H12V5L6 2.2 0 5Z"/></svg>';
  leaves.push(`<div class="leaf">
<div class="half r"><section class="${a.cls}">${a.html}</section></div>
<div class="half l">${b ? `<section class="${b.cls}">${b.html}</section>` : ''}</div>
<div class="frame"></div>
<div class="xin"><span class="nm">巔峰集</span>${fish}<span class="jn">${label}</span><span class="gap"></span><span class="ye">${hanNum(k + 1)}</span></div>
</div>`);
}

const bindCss = `
@page { size: 297mm 210mm; margin: 0 }
html, body { margin: 0; background: #fff }
.leaf { position: relative; width: 297mm; height: 209.8mm; overflow: hidden; break-after: page; break-inside: avoid; background: #fff }
.leaf:last-child { break-after: auto }
/* 版心靠書口（紙的中線），書背那一側留 20 公釐給線；天頭比地腳寬 */
.leaf .sheet { position: absolute; top: 6mm; width: 148mm; height: 210mm; overflow: visible; background: none; box-shadow: none; break-after: auto }
.leaf .half.r .sheet { left: 142mm }
.leaf .half.l .sheet { left: 7mm }
.leaf .rf { display: none }
.leaf .colophon { bottom: 112px }
.frame { position: absolute; left: 19mm; right: 19mm; top: 23mm; bottom: 16mm; border: 1.3pt solid #111 }
.frame::after { content: ""; position: absolute; inset: 1.1mm; border: .4pt solid #111 }
.xin { position: absolute; left: 142.5mm; width: 12mm; top: 24.1mm; bottom: 17.1mm; border-left: .4pt solid #111; border-right: .4pt solid #111;
  writing-mode: vertical-rl; display: flex; align-items: center; font: 400 12px/1 "Noto Serif TC", serif; letter-spacing: .3em; color: #111 }
.xin .nm { margin-block: 0; padding-block: 0; margin-inline: 26mm 3mm }
.xin .fish { inline-size: 5mm; block-size: 12mm; fill: #111; writing-mode: horizontal-tb; width: 12mm; height: 5mm }
.xin .jn { margin-inline-start: 4mm }
.xin .gap { flex: 1 }
.xin .ye { margin-inline-end: 9mm; letter-spacing: .1em }
.neifeng, .paiji { display: flex; flex-direction: column; justify-content: center; align-items: flex-start }
.neifeng { gap: 34px; padding-inline-start: 96px }
.neifeng h1 { font: 400 50px/1.1 var(--display); margin: 0; letter-spacing: .12em; white-space: nowrap }
.neifeng .nf-by { font: 400 19px/1 var(--display); letter-spacing: .3em; margin-inline-start: 250px; white-space: nowrap }
.neifeng .nf-yr { font-size: 14px; letter-spacing: .4em; margin-inline-start: 300px; color: var(--soft); white-space: nowrap }
.paiji { gap: 30px; padding-inline-start: 120px }
.paiji .pj { border: 1pt solid #111; padding: 16px 14px; line-height: 30px; letter-spacing: .1em; block-size: auto; inline-size: 25em }
.paiji .pj p { margin: 0; text-indent: 0; text-align: justify }
.paiji .sign { font-size: 14px; letter-spacing: .3em; color: var(--soft); display: flex; align-items: center; gap: 6px; margin-inline-start: 6em }
.paiji .sign i { inline-size: 8em; block-size: 1.6em; border-block-end: .5pt solid #777 }
.paiji .sign i.s { inline-size: 3.2em }
`;
const head = `<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">${FONT_LINK}<style>${book.css}</style>`;
const work = mkdtempSync(join(tmpdir(), 'bind-'));
const leavesHtml = join(work, 'leaves.html');
writeFileSync(leavesHtml, `${head}<style>${bindCss}</style></head><body>${leaves.join('\n')}</body></html>`);

const pg = await ctx.newPage();
await pg.setViewportSize({ width: 1300, height: 900 });
await pg.goto(pathToFileURL(leavesHtml).href, { waitUntil: 'networkidle' });
await pg.evaluate(() => document.fonts.ready);
await pg.waitForTimeout(600);
await pg.emulateMedia({ media: 'print', colorScheme: 'light' });
await pg.pdf({ path: join(out, 'leaves.pdf'), width: '297mm', height: '210mm', printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });

// ---- 封面、封底、題簽（A4 直向，附裁切線；裁成 148×210）----
// 裁切線：對齊成品邊（148×210，置中於 A4），畫在出血之外
const TX = 31, TY = 43.5, TW = 148, TH = 210;
const marks = `<svg class="marks" viewBox="0 0 210 297" aria-hidden="true">${[[TX, TY, -1, -1], [TX + TW, TY, 1, -1], [TX, TY + TH, -1, 1], [TX + TW, TY + TH, 1, 1]]
  .map(([x, y, dx, dy]) => `<path d="M${x + dx * 5} ${y}H${x + dx * 12}M${x} ${y + dy * 5}V${y + dy * 12}"/>`).join('')}</svg>`;
const stitches = `<svg class="thread" viewBox="0 0 148 210" aria-hidden="true">${
  [`M${148 - HOLES.inset} ${HOLES.ys[0]}V${HOLES.ys[3]}`, ...HOLES.ys.map(y => `M${148 - HOLES.inset} ${y}H148`), `M${148 - HOLES.inset} ${HOLES.ys[0]}V0`, `M${148 - HOLES.inset} ${HOLES.ys[3]}V210`]
    .map(d => `<path d="${d}"/>`).join('')}${HOLES.ys.map(y => `<circle cx="${148 - HOLES.inset}" cy="${y}" r="0.9"/>`).join('')}</svg>`;
const coverCss = `
@page { size: 210mm 297mm; margin: 0 }
html, body { margin: 0; background: #fff }
.pp { position: relative; width: 210mm; height: 296.8mm; break-after: page; overflow: hidden }
.pp:last-child { break-after: auto }
.bleed { position: absolute; left: 28mm; top: 40.5mm; width: 154mm; height: 216mm; overflow: hidden }
.bleed .cover { position: absolute; inset: 0 }
.bleed.back .cover svg { transform: scaleX(-1) }
.bleed .dia { position: absolute; left: 0; right: 0; bottom: 13%; text-align: center; color: #C9A45C; font-size: 9px }
.marks { position: absolute; inset: 0; width: 100%; height: 100% } .marks path { stroke: #000; stroke-width: .12; fill: none }
.cap { position: absolute; left: 0; right: 0; top: 14mm; text-align: center; font: 400 11px/1.8 "Noto Serif TC", serif; color: #555; letter-spacing: .1em }
.slips { position: absolute; left: 0; right: 0; top: 52mm; display: flex; justify-content: center; gap: 30mm }
.slip { width: 30mm; height: 150mm; border: .3pt dashed #999; display: flex; align-items: center; justify-content: center; background: #FBF7EC }
.slip div { width: 24mm; height: 144mm; border: 1pt solid #111; outline: .4pt solid #111; outline-offset: -1.6mm; display: flex; align-items: center; justify-content: center;
  writing-mode: vertical-rl; font: 400 30px/1 "NiYuBook", "Noto Serif TC", serif; letter-spacing: .14em; color: #111 }
`;
const coverInner = book.sheets[0].html;   // 網頁版第一頁就是封面
const coverHtml = join(work, 'cover.html');
writeFileSync(coverHtml, `${head}<style>${coverCss}</style></head><body>
<div class="pp"><div class="cap">封面　印在兩百磅上下的厚紙，沿裁切線裁成 148 × 210 公釐　書背在右</div><div class="bleed">${coverInner}</div>${marks}</div>
<div class="pp"><div class="cap">封底　同樣裁成 148 × 210 公釐　書背在左</div><div class="bleed back"><div class="full cover">${book.rain}<div class="dia">◆</div></div></div>${marks}</div>
<div class="pp"><div class="cap">題簽　封面若改用素色的紙或布，把這一條沿虛線裁下，貼在封面左上角（多印一條備用）</div>
<div class="slips"><div class="slip"><div><span><span class="tcy">AI</span>文學創作巔峰集</span></div></div><div class="slip"><div><span><span class="tcy">AI</span>文學創作巔峰集</span></div></div></div></div>
</body></html>`);
await pg.goto(pathToFileURL(coverHtml).href, { waitUntil: 'networkidle' });
await pg.evaluate(() => document.fonts.ready);
await pg.pdf({ path: join(out, 'cover.pdf'), width: '210mm', height: '297mm', printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });

// ---- 指南用的圖：訂好的樣子、一張攤開的葉子 ----
const shot = await browser.newContext({ viewport: { width: 900, height: 1000 }, deviceScaleFactor: 2, colorScheme: 'light' });
const sp = await shot.newPage();
const mockHtml = join(work, 'mock.html');
writeFileSync(mockHtml, `${head}<style>
body { margin: 0; background: transparent }
.stage { width: 760px; height: 900px; display: flex; align-items: center; justify-content: center }
.bk { position: relative; width: 148mm; height: 210mm; box-shadow: -10px 14px 34px rgba(0,0,0,.35), -3px 2px 0 #1b2c33, -6px 4px 0 #EDE6D4, -9px 6px 0 #E3DBC6 }
.bk .cover { position: absolute; inset: 0 }
.thread { position: absolute; inset: 0; width: 100%; height: 100% }
.thread path { stroke: #D9B872; stroke-width: .9; fill: none; stroke-linecap: round }
.thread circle { fill: #071318 }
</style></head><body><div class="stage"><div class="bk">${coverInner}${stitches}</div></div></body></html>`);
await sp.goto(pathToFileURL(mockHtml).href, { waitUntil: 'networkidle' });
await sp.evaluate(() => document.fonts.ready);
await sp.locator('.stage').screenshot({ path: join(out, 'mock.png'), omitBackground: true });
await sp.setViewportSize({ width: 1200, height: 900 });
await sp.goto(pathToFileURL(leavesHtml).href, { waitUntil: 'networkidle' });
await sp.evaluate(() => document.fonts.ready);
await sp.emulateMedia({ media: 'print' });
await sp.locator('.leaf').nth(15).screenshot({ path: join(out, 'leaf.png') });

// ---- 指南 ----
await pg.goto(pathToFileURL(join(out, 'index.html')).href, { waitUntil: 'networkidle' }).catch(() => null);
if (await pg.title().catch(() => '')) {
  await pg.evaluate(() => document.fonts.ready);
  await pg.pdf({ path: join(out, 'guide.pdf'), format: 'A4', printBackground: true, margin: { top: '14mm', right: '14mm', bottom: '14mm', left: '14mm' } });
}
await browser.close();
console.log(`線裝本：${leaves.length} 葉（A4 橫向單面），封面三頁`);
