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
  // demo links: scroll the whole player into view, then autoplay
  var demoSec = document.getElementById('demo');
  var demoShell = demoSec && demoSec.querySelector('.video-shell');
  var demoVideo = demoSec && demoSec.querySelector('video');
  var NAV_H = 72, EDGE = 16;

  function absTop(el) { // layout position, ignores transforms (e.g. .reveal offset)
    var y = 0;
    while (el) { y += el.offsetTop; el = el.offsetParent; }
    return y;
  }
  function demoTarget() {
    var vh = window.innerHeight;
    var secPad = parseFloat(getComputedStyle(demoSec).paddingTop) || 0;
    var shellTop = absTop(demoShell), shellH = demoShell.offsetHeight;
    // preferred: section heading just under the nav (same as the other anchors)
    var y = absTop(demoSec) + secPad - NAV_H;
    // if the player's bottom edge would be cut off, scroll further down
    if (shellTop + shellH - y > vh - EDGE) y = shellTop + shellH - vh + EDGE;
    // but never hide the player's top edge behind the nav
    if (shellTop - y < NAV_H) y = shellTop - NAV_H;
    var max = document.documentElement.scrollHeight - vh;
    return Math.max(0, Math.min(y, max));
  }
  function whenScrollSettled(cb) {
    var last = -1, still = 0, t0 = Date.now();
    (function poll() {
      var y = window.pageYOffset;
      still = (y === last) ? still + 1 : 0;
      last = y;
      if (still >= 4 || Date.now() - t0 > 2500) cb(); else setTimeout(poll, 60);
    })();
  }
  function playDemo(unlocked) {
    if (!demoVideo) return;
    if (demoVideo.ended) demoVideo.currentTime = 0;
    unlocked.then(function () {
      var p = demoVideo.play();
      if (p && p.catch) p.catch(function () { // sound blocked -> start muted
        demoVideo.muted = true;
        demoVideo.play().catch(function () {});
      });
    });
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href="#demo"]');
    if (!a || !demoSec || !demoShell) return;
    e.preventDefault();
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: demoTarget(), behavior: reduce ? 'auto' : 'smooth' });
    if (history.replaceState) history.replaceState(null, '', '#demo');
    if (!demoVideo) return;
    // "unlock" the element inside this click (needed by Safari/iOS), then start once in view
    var unlocked = Promise.resolve();
    if (demoVideo.paused) {
      var wasMuted = demoVideo.muted, t = demoVideo.currentTime;
      demoVideo.muted = true; // silent unlock, no audio blip
      var u = demoVideo.play();
      var restore = function () { demoVideo.pause(); demoVideo.currentTime = t; demoVideo.muted = wasMuted; };
      unlocked = (u && u.then) ? u.then(restore).catch(function () { demoVideo.muted = wasMuted; }) : Promise.resolve();
    }
    whenScrollSettled(function () { playDemo(unlocked); });
  });
})();
