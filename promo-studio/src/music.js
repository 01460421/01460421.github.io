// 程序化配樂：120 BPM 電影感電子樂。墊底和弦 + 低頻 + 鼓 + 上升音效 + 轉場重擊，全部對齊分鏡剪輯點。
const fs = require('fs');

function makeMusic(timeline, outFile) {
  const SR = 44100;
  const dur = timeline.duration + 0.5;
  const N = Math.ceil(dur * SR);
  const L = new Float32Array(N), R = new Float32Array(N);
  const beat = 60 / timeline.bpm;
  const bar = beat * 4;
  const drop = timeline.dropAt;
  const outro = timeline.outroAt;
  const midi = (m) => 440 * Math.pow(2, (m - 69) / 12);
  let seed = 1234567;
  const rnd = () => ((seed = (seed * 1103515245 + 12345) >>> 0) / 4294967296) * 2 - 1;

  // 和弦進行（小調，史詩感）：Am – F – C – G，每小節換一次
  const prog = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]];
  const roots = [45, 41, 48, 43];

  // ---- 1. Pad：每個和弦音 3 個微失諧鋸齒波 + 單極低通 ----
  const detune = [-0.11, 0, 0.12];
  const phases = [];
  for (let v = 0; v < 4; v++) for (let d = 0; d < 3; d++) phases.push(Math.random());
  let lpL = 0, lpR = 0;
  for (let i = 0; i < N; i++) {
    const t = i / SR;
    const ci = Math.floor(t / bar) % 4;
    const pos = (t % bar) / bar;
    const nextCi = (ci + 1) % 4;
    const xf = pos > 0.92 ? (pos - 0.92) / 0.08 : 0; // 和弦交叉淡化
    let sl = 0, sr = 0, k = 0;
    for (let v = 0; v < 4; v++) {
      const f = midi(prog[ci][v]) * (1 - xf) + midi(prog[nextCi][v]) * xf;
      for (let d = 0; d < 3; d++, k++) {
        phases[k] += (f * Math.pow(2, detune[d] / 12)) / SR;
        phases[k] -= Math.floor(phases[k]);
        const saw = phases[k] * 2 - 1;
        if (d === 0) sl += saw; else if (d === 2) sr += saw; else { sl += saw * 0.6; sr += saw * 0.6; }
      }
    }
    // 濾波器隨段落打開
    const open = t < drop ? 0.02 + 0.03 * (t / drop) : t < outro ? 0.07 + 0.02 * Math.sin(t * 0.7) : 0.05;
    lpL += (sl - lpL) * open; lpR += (sr - lpR) * open;
    let amp = 0.055;
    if (t < 1.2) amp *= t / 1.2;
    // 側鏈抽吸（drop 後）
    if (t >= drop && t < outro + bar) { const ph = ((t - drop) % beat) / beat; amp *= 0.55 + 0.45 * Math.min(1, ph * 3.2); }
    L[i] += lpL * amp; R[i] += lpR * amp;
  }

  // ---- 2. 低頻 Sub（drop 後）----
  let sp = 0;
  for (let i = Math.floor(drop * SR); i < Math.min(N, Math.floor((outro + bar) * SR)); i++) {
    const t = i / SR;
    const ci = Math.floor(t / bar) % 4;
    const ph = ((t - drop) % beat) / beat;
    sp += midi(roots[ci] - 12) / SR;
    const env = Math.min(1, ph * 6) * (0.6 + 0.4 * (1 - ph));
    const v = Math.sin(2 * Math.PI * sp) * 0.22 * env;
    L[i] += v; R[i] += v;
  }

  const addAt = (t0, len, fn, gain = 1, pan = 0) => {
    const s0 = Math.floor(t0 * SR), n = Math.floor(len * SR);
    for (let j = 0; j < n && s0 + j < N; j++) {
      if (s0 + j < 0) continue;
      const v = fn(j / SR) * gain;
      L[s0 + j] += v * (1 - Math.max(0, pan)); R[s0 + j] += v * (1 + Math.min(0, pan));
    }
  };

  // ---- 3. 鼓 ----
  const kick = (t) => { const f = 45 + 110 * Math.exp(-t * 28); return Math.sin(2 * Math.PI * (45 * t + (110 / 28) * (1 - Math.exp(-t * 28)))) * Math.exp(-t * 7) * (f > 0 ? 1 : 0); };
  const hat = () => { let hp = 0, prev = 0; return (t) => { const n = rnd(); hp = 0.6 * (hp + n - prev); prev = n; return hp * Math.exp(-t * 60); }; };
  const clap = () => { let lp = 0; return (t) => { lp += (rnd() - lp) * 0.35; return lp * (Math.exp(-t * 18) + 0.6 * Math.exp(-Math.max(0, t - 0.012) * 30)); }; };
  for (let t = drop; t < outro + bar - 0.01; t += beat) {
    addAt(t, 0.45, kick, 0.75);
    const bi = Math.round((t - drop) / beat);
    if (t > drop + bar) addAt(t + beat / 2, 0.08, hat(), 0.09, bi % 2 ? 0.3 : -0.3);
    if (bi % 4 === 1 || bi % 4 === 3) if (t > drop + bar * 2) addAt(t, 0.3, clap(), 0.16);
  }
  // 快剪段落：16 分音符 hat
  for (const c of timeline.scenes.filter((s) => s.type === 'cuts')) {
    for (let t = c.start; t < c.start + c.dur; t += beat / 4) addAt(t, 0.06, hat(), 0.06, Math.sin(t * 9) * 0.4);
  }

  // ---- 4. 上升音（drop 與結尾前）----
  const riser = (len) => { let lp = 0, ph = 0; return (t) => { const p = t / len; lp += (rnd() - lp) * (0.02 + 0.5 * p * p); ph += (200 + 900 * p * p) / SR; return (lp * 0.8 + Math.sin(2 * Math.PI * ph) * 0.25) * p * p; }; };
  for (const at of [drop, outro]) addAt(at - 2, 2, riser(2), 0.35);

  // ---- 5. 轉場重擊（每個剪輯點）----
  const boom = (big) => { let lp = 0; return (t) => { lp += (rnd() - lp) * 0.08; return Math.sin(2 * Math.PI * (38 * t + 25 * (1 - Math.exp(-t * 9)) / 9)) * Math.exp(-t * (big ? 1.6 : 3.5)) + lp * Math.exp(-t * 10) * 0.7; }; };
  timeline.cuts.forEach((c, i) => {
    if (i === 0) return;
    const big = c.type === 'hero' || c.type === 'outro';
    addAt(c.t, big ? 2.5 : 1.2, boom(big), big ? 0.55 : 0.22);
  });
  // 開場鐘聲（亮音）
  const bell = (f) => (t) => (Math.sin(2 * Math.PI * f * t) + 0.4 * Math.sin(2 * Math.PI * f * 2.76 * t) * Math.exp(-t * 3)) * Math.exp(-t * 1.4);
  addAt(0.9, 3, bell(midi(81)), 0.07, -0.2);
  addAt(0.9, 3, bell(midi(88)), 0.05, 0.2);
  addAt(outro + 0.05, 4, bell(midi(76)), 0.08, 0);
  addAt(outro + 0.05, 4, bell(midi(81)), 0.06, 0.2);

  // ---- 6. 迴聲延遲（附點八分）+ 簡易殘響 ----
  const dl = Math.floor(beat * 0.75 * SR);
  for (let i = dl; i < N; i++) { L[i] += R[i - dl] * 0.22; R[i] += L[i - dl] * 0.22; }
  const combs = [1557, 1617, 1491, 1422].map((d) => ({ d, buf: new Float32Array(d), i: 0 }));
  for (let i = 0; i < N; i++) {
    const x = (L[i] + R[i]) * 0.5; let y = 0;
    for (const c of combs) { const o = c.buf[c.i]; c.buf[c.i] = x + o * 0.78; c.i = (c.i + 1) % c.d; y += o; }
    L[i] += y * 0.045; R[i] += y * 0.045;
  }

  // ---- 7. 母帶：淡入淡出、軟削波、正規化 ----
  let peak = 0;
  for (let i = 0; i < N; i++) {
    const t = i / SR;
    let g = 1;
    if (t > timeline.duration - 1.8) g = Math.max(0, (timeline.duration - t) / 1.8);
    L[i] = Math.tanh(L[i] * 1.3 * g); R[i] = Math.tanh(R[i] * 1.3 * g);
    peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
  }
  const norm = peak > 0 ? 0.89 / peak : 1;
  const buf = Buffer.alloc(44 + N * 4);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + N * 4, 4); buf.write('WAVE', 8);
  buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22);
  buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 4, 28); buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34);
  buf.write('data', 36); buf.writeUInt32LE(N * 4, 40);
  for (let i = 0; i < N; i++) {
    buf.writeInt16LE(Math.round(Math.max(-1, Math.min(1, L[i] * norm)) * 32767), 44 + i * 4);
    buf.writeInt16LE(Math.round(Math.max(-1, Math.min(1, R[i] * norm)) * 32767), 46 + i * 4);
  }
  fs.writeFileSync(outFile, buf);
}

module.exports = { makeMusic };
