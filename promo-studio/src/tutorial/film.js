// 電影式宣傳片：錄製鏡頭 → 電影版面合成 → 交叉溶接 → 配樂
// 用法：node src/tutorial/film.js tutorials/reverse1999.js --out jobs/r1999 --music path/to/music.m4a
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { Recorder } = require('./recorder');
const { composeSegments } = require('./compose');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const ff = (a) => { const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', ...a]); if (r.status !== 0) throw new Error(r.stderr.toString().slice(-800)); };
const dur = (f) => parseFloat(spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).stdout.toString());

(async () => {
  const script = require(path.resolve(args[0]));
  const OUT = path.resolve(opt('out', 'jobs/film'));
  const XF = 0.7;
  fs.mkdirSync(path.join(OUT, 'seg'), { recursive: true });
  if (!args.includes('--skip-record')) {
    const rec = new Recorder({ outDir: path.join(OUT, 'rec'), storage: script.storage || {} });
    await rec.start(script.site);
    await rec.cursor(false);
    for (const s of script.shots) {
      console.log('鏡頭', s.id);
      await rec.begin(s.id, '');
      try { await s.run(rec); } catch (e) { console.log('  錯誤：', e.message.split('\n')[0]); }
      await rec.say('');
      rec.cur.end = Date.now() / 1000; rec.segments.push(rec.cur); rec.cur = null;
    }
    await rec.stop();
    const list = rec.segments.map((s) => { const data = rec.segmentData(s); fs.writeFileSync(path.join(OUT, 'rec', s.id + '.json'), JSON.stringify(data)); return { data, outFile: path.join(OUT, 'seg', s.id + '.mp4') }; });
    await composeSegments(list, { page: 'cinema.html', log: console.log });
  } else if (args.includes('--recompose')) {
    const dir = path.join(OUT, 'rec');
    const list = fs.readdirSync(dir).filter((f) => /^s\d+\.json$/.test(f)).sort().map((f) => ({ data: JSON.parse(fs.readFileSync(path.join(dir, f))), outFile: path.join(OUT, 'seg', f.replace('.json', '.mp4')) }));
    await composeSegments(list, { page: 'cinema.html', log: console.log });
  }
  // 交叉溶接
  const clips = script.shots.map((s) => path.join(OUT, 'seg', s.id + '.mp4')).filter((f) => fs.existsSync(f));
  const ds = clips.map(dur);
  let fg = '', prev = '[0:v]', off = 0;
  for (let i = 1; i < clips.length; i++) {
    off += ds[i - 1] - XF;
    const o = i === clips.length - 1 ? '[vx]' : `[x${i}]`;
    fg += `${prev}[${i}:v]xfade=transition=fade:duration=${XF}:offset=${off.toFixed(3)}${o};`;
    prev = o;
  }
  const total = ds.reduce((a, b) => a + b, 0) - XF * (clips.length - 1);
  fg += `[vx]fade=t=in:st=0:d=0.8,fade=t=out:st=${(total - 1.2).toFixed(2)}:d=1.2,format=yuv420p[v]`;
  const video = path.join(OUT, 'video.mp4');
  ff([...clips.flatMap((c) => ['-i', c]), '-filter_complex', fg, '-map', '[v]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-r', '30', video]);
  const final = path.join(OUT, 'promo.mp4');
  const music = opt('music', '');
  if (music) {
    const st = script.music && script.music.start || 0;
    ff(['-i', video, '-ss', String(st), '-i', music, '-filter_complex', `[1:a]atrim=0:${total.toFixed(2)},asetpts=PTS-STARTPTS,afade=t=in:d=1.2,afade=t=out:st=${(total - 3).toFixed(2)}:d=3,volume=0.9[a]`, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', final]);
  } else fs.copyFileSync(video, final);
  console.log(`完成：${final}（${total.toFixed(1)} 秒）`);
})().catch((e) => { console.error(e); process.exit(1); });
