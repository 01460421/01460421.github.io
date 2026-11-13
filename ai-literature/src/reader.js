(function () {
  document.documentElement.classList.add('js');
  var book = document.getElementById('book'), where = document.getElementById('where');
  var panel = document.getElementById('panel'), pristine = book.innerHTML;
  var narrow = window.matchMedia('screen and (max-width: 639px)');
  var total = book.querySelectorAll('.sheet').length, current = 1, io;

  function layout() {
    book.innerHTML = pristine;
    if (narrow.matches) {
      // phone: rejoin paragraphs that the paper edition split across two sheets
      book.querySelectorAll('.split-head').forEach(function (head) {
        var next = head.closest('.sheet').nextElementSibling;
        var cont = next && next.querySelector('.body > .cont');
        if (!cont) return;
        while (cont.firstChild) head.appendChild(cont.firstChild);
        cont.remove(); head.classList.remove('split-head');
      });
    }
    arm();
    watch();
  }
  // ---- 對話：讀者點「人」的話把它送出，回答才逐字出現 ----
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)');
  function arm() {
    var first = {};
    book.querySelectorAll('.q').forEach(function (q) {
      q.setAttribute('role', 'button'); q.tabIndex = 0;
      var p = q.dataset.p;
      if (!first[p]) first[p] = q.dataset.t;
      if (q.hasAttribute('data-free') || first[p] === q.dataset.t) q.classList.add('ready');
    });
  }
  function type(el, done) {
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), nodes = [], n;
    while ((n = walker.nextNode())) if (n.data) nodes.push(n);
    var rest = nodes.map(function (t) {
      var s = document.createElement('span');
      s.style.visibility = 'hidden'; s.textContent = t.data; t.data = '';
      t.parentNode.insertBefore(s, t.nextSibling);
      return { t: t, s: s };
    });
    el.classList.add('on');
    var k = 0, timer = setInterval(function () {
      for (var i = 0; i < 2; i++) {
        while (k < rest.length && !rest[k].s.textContent) { rest[k].s.remove(); k++; }
        if (k >= rest.length) { clearInterval(timer); done(); return; }
        var d = rest[k].s.textContent;
        rest[k].t.data += d.charAt(0); rest[k].s.textContent = d.slice(1);
      }
    }, 22);
  }
  function send(q) {
    var t = q.dataset.t, p = q.dataset.p;
    book.querySelectorAll('.q[data-t="' + t + '"]').forEach(function (e) { e.classList.remove('ready'); e.classList.add('sent'); e.removeAttribute('tabindex'); });
    var answers = Array.prototype.slice.call(book.querySelectorAll('[data-w="' + t + '"]')), i = 0;
    (function next() {
      if (i < answers.length) {
        var el = answers[i++];
        if (calm.matches) { el.classList.add('on'); next(); } else type(el, next);
        return;
      }
      book.querySelectorAll('.q[data-p="' + p + '"][data-t="' + (+t + 1) + '"]').forEach(function (e) { e.classList.add('ready'); });
    })();
  }
  book.addEventListener('click', function (e) { var q = e.target.closest('.q.ready'); if (q) send(q); });
  book.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var q = e.target.closest('.q.ready'); if (q) { e.preventDefault(); send(q); }
  });
  var allBtn = document.getElementById('all');
  allBtn.addEventListener('click', function () {
    var on = book.classList.toggle('all');
    allBtn.setAttribute('aria-pressed', on); allBtn.textContent = on ? '對話收起' : '對話全開';
  });
  function watch() {
    if (io) io.disconnect();
    if (!('IntersectionObserver' in window)) return;
    io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { current = +e.target.dataset.n; where.textContent = current + ' / ' + total; } });
    }, { rootMargin: '-45% 0px -45% 0px' });
    book.querySelectorAll('.sheet').forEach(function (s) { io.observe(s); });
  }
  function go(n) {
    n = Math.max(1, Math.min(total, n));
    var el = document.getElementById('p' + n);
    if (el) el.scrollIntoView();
  }
  var wide = window.matchMedia('screen and (min-width: 1200px)');
  function step(d) { go(current + d * (wide.matches ? 2 : 1)); }
  document.getElementById('prev').addEventListener('click', function () { step(-1); });
  document.getElementById('next').addEventListener('click', function () { step(1); });
  document.addEventListener('keydown', function (e) {
    if (e.target.closest('input, textarea') || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'Escape' && !panel.hidden) { shut(); return; }
    if (!panel.hidden || narrow.matches) return;
    // 直排書由右往左翻：左鍵是下一頁
    if (e.key === 'ArrowLeft') step(1); else if (e.key === 'ArrowRight') step(-1);
  });
  var opener = document.getElementById('open-toc');
  function shut() { panel.hidden = true; opener.focus(); }
  opener.addEventListener('click', function () { panel.hidden = false; document.getElementById('shut-toc').focus(); });
  document.getElementById('shut-toc').addEventListener('click', shut);
  panel.addEventListener('click', function (e) { if (e.target.closest('a')) panel.hidden = true; });
  (narrow.addEventListener ? narrow.addEventListener.bind(narrow, 'change') : narrow.addListener.bind(narrow))(layout);
  layout();
  where.textContent = current + ' / ' + total;
  if (/^#p\d+$/.test(location.hash)) go(+location.hash.slice(2));
})();
