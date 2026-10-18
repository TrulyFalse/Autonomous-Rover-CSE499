(function () {
  'use strict';

  // scroll progress
  var bar = document.getElementById('progress');
  function onScroll() {
    var h = document.documentElement;
    var p = h.scrollTop / (h.scrollHeight - h.clientHeight || 1);
    bar.style.width = (p * 100).toFixed(1) + '%';
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // mobile menu
  var links = document.getElementById('navLinks');
  document.getElementById('menuBtn').addEventListener('click', function () {
    links.classList.toggle('open');
  });
  links.addEventListener('click', function (e) {
    if (e.target.tagName === 'A') links.classList.remove('open');
  });

  // reveal on scroll + bars + counters
  function countUp(el) {
    var target = parseFloat(el.dataset.count);
    var dec = parseInt(el.dataset.dec || '0', 10);
    var suffix = el.dataset.suffix || '';
    var start = null, dur = 1400;
    function tick(t) {
      if (!start) start = t;
      var k = Math.min((t - start) / dur, 1);
      var eased = 1 - Math.pow(1 - k, 3);
      el.textContent = (target * eased).toFixed(dec) + (k === 1 ? suffix : '');
      if (k < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      var el = en.target;
      el.classList.add('in');
      el.querySelectorAll('[data-count]').forEach(countUp);
      io.unobserve(el);
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal, #bars').forEach(function (el) { io.observe(el); });

  // nav highlight
  var secs = ['demo', 'hardware', 'pipeline', 'results', 'impact', 'team'];
  var navA = {};
  links.querySelectorAll('a').forEach(function (a) { navA[a.getAttribute('href').slice(1)] = a; });
  var so = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (en.isIntersecting) {
        Object.keys(navA).forEach(function (k) { navA[k].classList.toggle('on', k === en.target.id); });
      }
    });
  }, { rootMargin: '-45% 0px -50% 0px' });
  secs.forEach(function (id) { var s = document.getElementById(id); if (s) so.observe(s); });

  // pipeline steps: one image per step, autoplay every 3s
  var steps = Array.prototype.slice.call(document.querySelectorAll('#steps li'));
  var stepsEl = document.getElementById('steps');
  var imgs = Array.prototype.slice.call(document.querySelectorAll('#stage .stage-imgs img'));
  var cap = document.getElementById('stageCap');
  var cur = 0, timer = null, visible = false;
  function setStep(i) {
    cur = i;
    steps.forEach(function (s, idx) { s.classList.toggle('active', idx === i); });
    imgs.forEach(function (im, idx) { im.classList.toggle('on', idx === i); });
    var active = steps[i];
    // restart the progress-fill animation
    active.classList.remove('active'); void active.offsetWidth; active.classList.add('active');
    cap.textContent = 'Step ' + (i + 1) + ' / ' + steps.length + ' — ' + active.querySelector('h3').textContent;
  }
  function restart() {
    clearInterval(timer);
    if (visible) timer = setInterval(function () { setStep((cur + 1) % steps.length); }, 3000);
  }
  steps.forEach(function (s, i) {
    s.addEventListener('click', function () { setStep(i); restart(); });
  });
  new IntersectionObserver(function (e) {
    visible = e[0].isIntersecting;
    restart();
  }, { threshold: 0.3 }).observe(stepsEl);

  // tabs
  var tabBtns = document.querySelectorAll('#tabs [data-tab]');
  var panels = document.querySelectorAll('#tabs [data-panel]');
  tabBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      var n = b.dataset.tab;
      tabBtns.forEach(function (x) { x.classList.toggle('on', x === b); });
      panels.forEach(function (p) { p.classList.toggle('on', p.dataset.panel === n); });
    });
  });

  // lightbox
  var lb = document.getElementById('lightbox');
  var lbImg = lb.querySelector('img');
  document.querySelectorAll('img[data-zoom]').forEach(function (img) {
    img.addEventListener('click', function () {
      lbImg.src = img.src; lbImg.alt = img.alt;
      lb.classList.add('open'); lb.setAttribute('aria-hidden', 'false');
    });
  });
  function closeLb() { lb.classList.remove('open'); lb.setAttribute('aria-hidden', 'true'); }
  lb.addEventListener('click', closeLb);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeLb(); });
})();
