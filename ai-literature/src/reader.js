(function () {
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
    watch();
  }
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
    if (!panel.hidden) return;
    if (e.key === 'ArrowRight') step(1); else if (e.key === 'ArrowLeft') step(-1);
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
