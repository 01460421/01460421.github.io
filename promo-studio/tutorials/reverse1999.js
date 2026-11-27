// 逆雨檔案館（reverse-1999-art.vercel.app）宣傳片：安靜、電影式的鏡頭腳本
const SITE = 'https://reverse-1999-art.vercel.app/';
const go = async (r, hash) => { await r.page.evaluate((h) => { location.hash = h; }, hash); await r.wait(1600); await r.page.evaluate(() => window.scrollTo(0, 0)); };
const scrollTo = (r, sel, off = 80) => r.page.evaluate(([s, o]) => { const el = document.querySelector(s); if (el) window.scrollTo({ top: el.getBoundingClientRect().top + scrollY - o, behavior: 'instant' }); }, [sel, off]);
const glide = (r, by, ms) => r.page.evaluate(([b, m]) => new Promise((res) => { const y0 = scrollY, t0 = performance.now(); const f = (n) => { const p = Math.min(1, (n - t0) / m); window.scrollTo(0, y0 + b * (p < .5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2)); p < 1 ? requestAnimationFrame(f) : res(); }; requestAnimationFrame(f); }), [by, ms]);

module.exports = {
  site: SITE,
  music: { file: 'theme-suitcase.m4a', start: 0 },
  shots: [
    // 開場：入館的雨夜（網站自己的標題，不另加字）
    { id: 's01', async run(r) { await r.cursor(false); await r.wait(6500); } },
    { id: 's02', async run(r) {
      await r.page.locator('.gd-intro button:has-text("進館")').first().click({ timeout: 2500 }).catch(() => {});
      await r.wait(4600);
    } },
    // 大廳：慢慢往下滑
    { id: 's03', async run(r) {
      await r.page.evaluate(() => document.querySelectorAll('.gd-intro').forEach((e) => e.remove()));
      await go(r, '#hall'); await r.wait(1800);
      await glide(r, 420, 4200); await r.wait(500);
    } },
    { id: 's04', async run(r) {
      await go(r, '#rain'); await scrollTo(r, '#r-rain', 30); await r.wait(500);
      const box = await r.page.locator('#r-rain canvas').first().boundingBox({ timeout: 2500 }).catch(() => null) || { x: 120, y: 300, width: 900, height: 520 };
      await r.cursor(true);
      const pts = [[.12, .55], [.32, .38], [.52, .62], [.72, .42], [.88, .58]].map(([a, b]) => [box.x + box.width * a, box.y + box.height * b]);
      await r.sweep(pts, 6200);
      await r.cursor(false);
    } },
    { id: 's05', async run(r) { await go(r, '#chronicle'); await scrollTo(r, '#r-chronicle', 30); await r.wait(700); await glide(r, 360, 4800); await r.wait(400); } },
    { id: 's06', async run(r) {
      await go(r, '#chapters'); await scrollTo(r, '#r-chapters', 30); await r.wait(1600);
      for (let i = 0; i < 2; i++) { await r.page.locator('#r-chapters button:has-text("›")').first().click({ timeout: 2500 }).catch(() => {}); await r.wait(1800); }
      await r.wait(800);
    } },
    { id: 's07', async run(r) {
      await go(r, '#film'); await scrollTo(r, '#r-film', 0); await r.wait(1400);
      await r.page.locator('#r-film button.film-big').first().click({ timeout: 2500 }).catch(() => {});
      await r.wait(7600);
    } },
    { id: 's08', async run(r) {
      await r.page.keyboard.press('Escape').catch(() => {});
      await r.page.locator('button:has-text("離開")').first().click({ timeout: 1500 }).catch(() => {});
      await go(r, '#choices'); await scrollTo(r, '#r-choices', 30); await r.wait(2000);
      await r.page.locator('#r-choices button.opt').first().click({ timeout: 2500 }).catch(() => {});
      await r.wait(3800);
    } },
    { id: 's09', async run(r) {
      await go(r, '#index'); await scrollTo(r, '#r-index', 30); await r.wait(1200);
      const inp = r.page.locator('#r-index input').first();
      await inp.click({ timeout: 2500 }).catch(() => {}); await inp.pressSequentially('手提箱', { delay: 240, timeout: 4000 }).catch(() => {});
      await r.wait(3000);
    } },
    { id: 's10', async run(r) { await go(r, '#quiz'); await scrollTo(r, '#r-quiz', 30); await r.wait(5200); } },
    { id: 's11', async run(r) { await go(r, '#play'); await scrollTo(r, '#r-play', 30); await r.wait(1200); await glide(r, 300, 3600); await r.wait(300); } },
    // 片尾：回到大廳的雨夜主視覺，只在底部加網址
    { id: 's12', async run(r) {
      await go(r, '#hall'); await r.page.evaluate(() => window.scrollTo(0, 0));
      await r.say('@||reverse-1999-art.vercel.app');
      await r.wait(8000);
    } },
  ],
};
