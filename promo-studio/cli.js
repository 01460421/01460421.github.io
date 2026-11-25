#!/usr/bin/env node
// 用法：node cli.js <網址> [--lang zh-Hant|en] [--pages 5] [--out promo.mp4] [--no-ai]
const path = require('path');
const fs = require('fs');
const { runPipeline } = require('./src/pipeline');

const args = process.argv.slice(2);
const url = args.find((a) => !a.startsWith('--'));
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
if (!url) { console.log('用法：node cli.js <網址> [--lang zh-Hant|en] [--pages 5] [--out promo.mp4] [--no-ai]'); process.exit(1); }

const jobDir = path.resolve(opt('dir', path.join('jobs', 'cli-' + Date.now())));
const out = path.resolve(opt('out', 'promo.mp4'));
let last = '';
runPipeline({
  url, jobDir, lang: opt('lang', 'zh-Hant'), maxPages: +opt('pages', 5), useAI: !args.includes('--no-ai'),
  log: (m) => console.log('  ' + m),
  onStatus: (s) => {
    const line = `[${s.stage}] ${(s.progress * 100).toFixed(0)}%${s.eta != null ? `  剩約 ${s.eta}s` : ''}`;
    if (line !== last) { process.stdout.write('\r' + line.padEnd(40)); last = line; }
    if (s.stage !== 'render') process.stdout.write('\n');
  },
}).then((r) => {
  fs.copyFileSync(r.out, out);
  console.log(`\n完成 → ${out}`);
}).catch((e) => { console.error('\n失敗：', e.message); process.exit(1); });
