// 教學長片組裝：錄製每章操作 → 章節卡／開場／收尾（動態引擎）→ BGM 串接 → 輸出
// 用法：node src/tutorial/build.js tutorials/sekai.js --out jobs/tutorial --assets jobs/sekai-main/assets --bgm dir/with/mp3s [--only 3,5]
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { Recorder } = require('./recorder');
const { composeSegments } = require('./compose');
const { render } = require('../render');
const { pickPalette } = require('../story');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const ff = (a) => { const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', ...a]); if (r.status !== 0) throw new Error(r.stderr.toString().slice(-600)); };
const dur = (f) => parseFloat(spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).stdout.toString());

async function main() {
  const script = require(path.resolve(args[0]));
  const OUT = path.resolve(opt('out', 'jobs/tutorial'));
  const ASSETS = path.resolve(opt('assets', path.join(OUT, 'assets')));
  const BGM = opt('bgm', '');
  const only = opt('only', '') ? opt('only').split(',').map(Number) : null;
  fs.mkdirSync(path.join(OUT, 'seg'), { recursive: true });
  const N = script.chapters.length;
  const log = (m) => console.log(m);

  // ---------- 1. 錄製 ----------
  if (!args.includes('--skip-record')) {
    const rec = new Recorder({ outDir: path.join(OUT, 'rec'), storage: script.storage || {}, log });
    await rec.start(script.site);
    for (let i = 0; i < N; i++) {
      if (only && !only.includes(i + 1)) continue;
      const ch = script.chapters[i];
      log(`第 ${i + 1} 章：${ch.title}`);
      await rec.begin(`c${String(i + 1).padStart(2, '0')}`, `${String(i + 1).padStart(2, '0')} · ${ch.title}`);
      try { await ch.run(rec); } catch (e) { log(`  章節錯誤：${e.message.split('\n')[0]}`); }
      await rec.end();
      // 每章結束回到首頁頂端，避免狀態殘留
      try { await rec.page.keyboard.press('Escape'); await rec.page.evaluate(() => window.scrollTo(0, 0)); } catch {}
    }
    await rec.stop();
    const list = rec.segments.map((s) => {
      const data = rec.segmentData(s);
      fs.writeFileSync(path.join(OUT, 'rec', s.id + '.json'), JSON.stringify(data));
      return { data, outFile: path.join(OUT, 'seg', s.id + '.mp4') };
    });
    log('合成畫面（視窗、鏡頭推近、字幕）…');
    await composeSegments(list, { log });
  }

  if (args.includes('--recompose')) {
    const recDir = path.join(OUT, 'rec');
    const list = fs.readdirSync(recDir).filter((f) => /^c\d+\.json$/.test(f)).filter((f) => !only || only.includes(parseInt(f.slice(1)))).sort()
      .map((f) => ({ data: JSON.parse(fs.readFileSync(path.join(recDir, f))), outFile: path.join(OUT, 'seg', f.replace('.json', '.mp4')) }));
    await composeSegments(list, { log });
  }

  // ---------- 2. 章節卡、開場、收尾 ----------
  const site = fs.existsSync(path.join(ASSETS, '..', 'site.json')) ? JSON.parse(fs.readFileSync(path.join(ASSETS, '..', 'site.json'))) : { pages: [] };
  const palette = site.pages.length ? pickPalette(site.pages) : { accent: 'hsl(176 70% 55%)', accent2: 'hsl(224 80% 62%)', accent3: 'hsl(136 70% 55%)' };
  const domain = new URL(script.site).hostname.replace(/^www\./, '');
  const base = { width: 1920, height: 1080, fps: 30, bpm: 120, palette, lang: 'zh-Hant', calm: true };
  const mk = (scenes) => {
    let t = 0; for (const s of scenes) { s.start = t; t += s.dur; }
    return { ...base, scenes, duration: t, dropAt: 0, outroAt: t, cuts: scenes.map((s) => ({ t: s.start, type: s.type })) };
  };
  const hero = fs.existsSync(path.join(ASSETS, 'p0_hero.jpg')) ? 'p0_hero.jpg' : null;
  const icon = ['icon.png', 'icon.svg', 'icon.jpg'].find((f) => fs.existsSync(path.join(ASSETS, f)));
  const introScenes = [
    { type: 'intro', dur: 4, small: '完整教學', brand: script.title },
    { type: 'hook', dur: 2 * script.intro.hook.length, lines: script.intro.hook },
  ];
  if (hero) introScenes.push({ type: 'hero', dur: 6, img: hero, domain, title: script.title, tagline: script.intro.tagline });
  const jobs = [
    ['intro', mk(introScenes)],
    ['cards', mk(script.chapters.map((c, i) => ({ type: 'chapter', dur: 3, n: i + 1, total: N, title: c.title, sub: c.sub })))],
    ['outro', mk([{ type: 'outro', dur: 6, brand: script.title, line: script.outro.line, cta: script.outro.cta, domain, icon, iconStyle: 'glass' }])],
  ];
  for (const [name, tl] of jobs) {
    const f = path.join(OUT, name + '.mp4');
    if (fs.existsSync(f) && args.includes('--reuse-stage')) continue;
    log(`渲染 ${name}（${tl.duration} 秒）`);
    await render({ timeline: tl, assetsDir: ASSETS, outFile: f, log: () => {} });
  }
  for (let i = 0; i < N; i++) ff(['-ss', String(i * 3), '-i', path.join(OUT, 'cards.mp4'), '-t', '3', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', '30', '-an', path.join(OUT, 'seg', `card${String(i + 1).padStart(2, '0')}.mp4`)]);

  // ---------- 3. 串接畫面 ----------
  const parts = [path.join(OUT, 'intro.mp4')];
  for (let i = 0; i < N; i++) {
    const id = String(i + 1).padStart(2, '0');
    const seg = path.join(OUT, 'seg', `c${id}.mp4`);
    if (!fs.existsSync(seg)) continue;
    parts.push(path.join(OUT, 'seg', `card${id}.mp4`), seg);
  }
  parts.push(path.join(OUT, 'outro.mp4'));
  // 統一重新編碼一次，確保所有片段參數一致
  const listFile = path.join(OUT, 'parts.txt');
  fs.writeFileSync(listFile, parts.map((p) => `file '${p}'`).join('\n'));
  const video = path.join(OUT, 'video.mp4');
  log('串接畫面…');
  ff(['-f', 'concat', '-safe', '0', '-i', listFile, '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', '30', '-an', video]);
  const total = dur(video);

  // ---------- 4. 配樂：BGM 交叉淡入串接 ----------
  const final = path.join(OUT, 'tutorial.mp4');
  let tracks = BGM ? fs.readdirSync(BGM).filter((f) => /\.(mp3|m4a|ogg|wav)$/i.test(f)).sort((a, b) => parseInt(a) - parseInt(b)).map((f) => path.join(BGM, f)) : [];
  if (tracks.length) {
    const XF = 3;
    let sum = 0, list = [];
    while (sum < total + 5) { for (const t of tracks) { list.push(t); sum += dur(t) - XF; if (sum >= total + 5) break; } }
    const inputs = list.flatMap((t) => ['-i', t]);
    let fg = '', prev = '[0:a]';
    for (let i = 1; i < list.length; i++) { const o = i === list.length - 1 ? '[mix]' : `[a${i}]`; fg += `${prev}[${i}:a]acrossfade=d=${XF}:c1=tri:c2=tri${o};`; prev = o; }
    if (list.length === 1) fg = '[0:a]anull[mix];';
    fg += `[mix]atrim=0:${total.toFixed(2)},volume=0.32,afade=t=in:d=1.5,afade=t=out:st=${(total - 4).toFixed(2)}:d=4[out]`;
    const bgm = path.join(OUT, 'bgm.m4a');
    log(`配樂：${list.length} 段 BGM`);
    ff([...inputs, '-filter_complex', fg, '-map', '[out]', '-c:a', 'aac', '-b:a', '192k', bgm]);
    ff(['-i', video, '-i', bgm, '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', final]);
  } else {
    fs.copyFileSync(video, final);
  }
  log(`完成：${final}（${(total / 60).toFixed(1)} 分鐘）`);
}

main().catch((e) => { console.error(e); process.exit(1); });
