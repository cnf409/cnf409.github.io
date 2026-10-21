/* conflict — vanilla behaviours (bundle.js). One classic script, no dependencies, no network.
   It only toggles attributes and classes; every visual and every timing lives in bundle.css.
   Port: drop into the site as /static/conflict.js with <script defer>. Exposes window.Conflict. */
(function () {
  'use strict';
  var d = document, root = d.documentElement;
  root.classList.add('js');
  var reduce = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };

  function $(sel, scope) { return (scope || d).querySelector(sel); }
  function $$(sel, scope) { return Array.prototype.slice.call((scope || d).querySelectorAll(sel)); }
  function once(el, key) { if (el.dataset['w' + key]) return false; el.dataset['w' + key] = '1'; return true; }
  function ms(name) {
    var v = getComputedStyle(root).getPropertyValue(name).trim();
    if (!v) return 0;
    return /ms$/.test(v) ? parseFloat(v) : parseFloat(v) * 1000;
  }
  /* run `done` when el's animation ends (or after a safety timeout) */
  function afterAnim(el, done, fallback) {
    var called = false;
    function fin(e) { if (e && e.target !== el && !el.contains(e.target)) return; if (called) return; called = true; el.removeEventListener('animationend', fin); done(); }
    el.addEventListener('animationend', fin);
    setTimeout(fin, (fallback || 400) + 60);
  }
  function restart(el, cls) { el.classList.remove(cls); void el.offsetWidth; el.classList.add(cls); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  /* ── entrances ─────────────────────────────────────────── */
  var io = 'IntersectionObserver' in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); } });
  }, { threshold: 0.15, rootMargin: '0px 0px -6% 0px' }) : null;
  function reveals(scope) {
    $$('[data-reveal-group]', scope).forEach(function (g) {
      $$(':scope > [data-reveal], :scope > * > [data-reveal]', g).forEach(function (el, i) { el.style.setProperty('--i', i); });
    });
    $$('[data-reveal]', scope).forEach(function (el) {
      if (!once(el, 'reveal')) return;
      if (!io || reduce.matches) { el.classList.add('is-in'); return; }
      io.observe(el);
    });
  }
  function replay(el) { el.classList.remove('is-in'); void el.offsetWidth; el.classList.add('is-in'); }

  /* ── impact frame (< 150ms) ────────────────────────────── */
  function impact(el) {
    if (reduce.matches || !el) return;
    restart(el, 'is-impact');
    var b = d.createElement('span'); b.className = 'impact-burst'; b.setAttribute('aria-hidden', 'true');
    el.appendChild(b);
    setTimeout(function () { b.remove(); el.classList.remove('is-impact'); }, ms('--dur-instant') * 1.6 + 40);
  }
  function wireImpact(scope) {
    $$('.btn, .filter, [data-impact]', scope).forEach(function (el) {
      if (!once(el, 'impact')) return;
      el.addEventListener('pointerdown', function () { impact(el); });
      el.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') impact(el); });
    });
  }

  /* ── copy / share: "copy" → "copied" ───────────────────── */
  function setCopied(btn) {
    var label = $('.btn__label', btn) || btn;
    if (!btn.dataset.label) btn.dataset.label = label.textContent;
    label.textContent = btn.dataset.copied || 'copied';
    btn.setAttribute('data-state', 'copied');
    clearTimeout(btn._t);
    btn._t = setTimeout(function () { label.textContent = btn.dataset.label; btn.removeAttribute('data-state'); }, 1600);
  }
  function writeClip(text) {
    try { if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text).catch(function () {}); } catch (e) {}
    var ta = d.createElement('textarea'); ta.value = text; ta.setAttribute('readonly', ''); ta.style.position = 'fixed'; ta.style.opacity = '0';
    d.body.appendChild(ta); ta.select(); try { d.execCommand('copy'); } catch (e) {} ta.remove();
    return Promise.resolve();
  }
  function wireCopy(scope) {
    $$('[data-copy]', scope).forEach(function (btn) {
      if (!once(btn, 'copy')) return;
      btn.addEventListener('click', function () {
        var sel = btn.getAttribute('data-copy'), src = sel ? $(sel) : null;
        if (!src) { var box = btn.closest('.codeblock, .terminal, .flag-panel, .source'); src = box && $('pre, .flag-panel__value', box); }
        var text = src ? src.innerText : '';
        if (src && src.closest('.terminal')) { /* copy commands only, without prompts or output */
          var cmds = $$('.gp', src).map(function (p) { var t = ''; for (var n = p.nextSibling; n && !(n.nodeType === 1 && (n.classList.contains('go') || n.classList.contains('gp'))); n = n.nextSibling) t += n.textContent; return t.trim(); }).filter(Boolean);
          if (cmds.length) text = cmds.join('\n');
        }
        writeClip(text).then(function () { setCopied(btn); });
      });
    });
    $$('[data-share]', scope).forEach(function (btn) {
      if (!once(btn, 'share')) return;
      btn.addEventListener('click', function () { writeClip(btn.getAttribute('data-share') || location.href).then(function () { setCopied(btn); }); });
    });
  }

  /* ── disclosure panels: nav dropdown, phone menu ───────── */
  function openPanel(btn, panel) {
    panel.hidden = false; btn.setAttribute('aria-expanded', 'true');
    panel.classList.remove('is-closing'); restart(panel, 'is-opening');
  }
  function closePanel(btn, panel, focusBack) {
    if (panel.hidden) return;
    btn.setAttribute('aria-expanded', 'false');
    panel.classList.remove('is-opening'); panel.classList.add('is-closing');
    afterAnim(panel, function () { panel.hidden = true; panel.classList.remove('is-closing'); }, ms('--dur-fast'));
    if (focusBack) btn.focus();
  }
  function wireDisclosure(scope) {
    $$('[aria-controls][data-toggle]', scope).forEach(function (btn) {
      if (!once(btn, 'toggle')) return;
      var panel = d.getElementById(btn.getAttribute('aria-controls')); if (!panel) return;
      btn.addEventListener('click', function (e) { e.stopPropagation(); panel.hidden ? openPanel(btn, panel) : closePanel(btn, panel); });
      d.addEventListener('click', function (e) { if (!panel.hidden && !panel.contains(e.target)) closePanel(btn, panel); });
      d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) closePanel(btn, panel, true); });
      panel.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
        var items = $$('a, button', panel), i = items.indexOf(d.activeElement);
        e.preventDefault(); items[(i + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length].focus();
      });
    });
  }

  /* ── global search (Ctrl/⌘ K) ──────────────────────────── */
  function wireSearch(scope) {
    var box = $('[data-search]', scope); if (!box || !once(box, 'search')) return;
    var input = $('.search__input', box), list = $('.search__results', box), empty = $('.search__empty', box), label = $('.search__label', box);
    var idxEl = d.getElementById('search-index'), index = [];
    try { index = idxEl ? JSON.parse(idxEl.textContent) : (window.CONFLICT_SEARCH || []); } catch (e) {}
    var active = -1, lastFocus = null;
    function open() {
      if (!box.hidden) return;
      lastFocus = d.activeElement; box.hidden = false; box.classList.remove('is-closing'); restart(box, 'is-opening');
      $$('[data-search-open]').forEach(function (b) { b.setAttribute('aria-expanded', 'true'); });
      render(input.value); setTimeout(function () { input.focus(); input.select(); }, 0);
    }
    function close() {
      if (box.hidden) return;
      box.classList.remove('is-opening'); box.classList.add('is-closing');
      $$('[data-search-open]').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
      afterAnim(box, function () { box.hidden = true; box.classList.remove('is-closing'); }, ms('--dur-fast'));
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    function hi(text, q) {
      if (!q) return esc(text);
      var i = text.toLowerCase().indexOf(q.toLowerCase());
      return i < 0 ? esc(text) : esc(text.slice(0, i)) + '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' + esc(text.slice(i + q.length));
    }
    function select(i) {
      var items = $$('.result', list); if (!items.length) { active = -1; input.removeAttribute('aria-activedescendant'); return; }
      active = (i + items.length) % items.length;
      items.forEach(function (it, n) { it.setAttribute('aria-selected', n === active ? 'true' : 'false'); });
      input.setAttribute('aria-activedescendant', items[active].id);
      items[active].scrollIntoView({ block: 'nearest' });
    }
    function render(q) {
      q = (q || '').trim();
      var hits = !q ? index.filter(function (p) { return p.pinned; }).slice(0, 6) : index.filter(function (p) {
        return (p.title + ' ' + (p.event || '') + ' ' + (p.tags || []).join(' ')).toLowerCase().indexOf(q.toLowerCase()) > -1;
      }).slice(0, 8);
      label.textContent = q ? (hits.length + (hits.length === 1 ? ' result' : ' results')) : 'Pinned';
      label.hidden = q && !hits.length;
      list.innerHTML = hits.map(function (p, n) {
        return '<li><a class="result" role="option" id="sr-' + n + '" href="' + esc(p.url || '#') + '" style="--i:' + n + '" aria-selected="false">' +
          '<span class="badge badge--' + esc(p.type) + '">' + esc(p.type) + '</span>' +
          '<span class="result__title">' + hi(p.title, q) + '</span>' +
          '<span class="result__enter" aria-hidden="true">↵</span>' +
          '<span class="result__meta">' + esc([p.event, p.date].filter(Boolean).join(' · ')) + (p.tags ? ' · ' + p.tags.slice(0, 3).map(function (t) { return hi('#' + t, q); }).join(' ') : '') + '</span></a></li>';
      }).join('');
      empty.hidden = !(q && !hits.length);
      if (!empty.hidden) $('b', empty).textContent = '“' + q + '”';
      restart(box, 'is-results');
      select(hits.length ? 0 : -1);
    }
    $$('[data-search-open]').forEach(function (b) { if (once(b, 'sopen')) b.addEventListener('click', open); });
    $$('[data-search-close]', box).forEach(function (b) { b.addEventListener('click', close); });
    input.addEventListener('input', function () { render(input.value); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); select(active + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); select(active - 1); }
      else if (e.key === 'Enter') { var a = $$('.result', list)[active]; if (a) { e.preventDefault(); impact(a); a.click(); } }
    });
    list.addEventListener('mousemove', function (e) { var a = e.target.closest('.result'); if (a) select($$('.result', list).indexOf(a)); });
    d.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); box.hidden ? open() : close(); }
      else if (e.key === 'Escape' && !box.hidden) close();
    });
    box.Conflict = { open: open, close: close, render: render, select: select, input: input };
  }

  /* ── post filters: All / CTF / Box / Post ──────────────── */
  function wireFilters(scope) {
    $$('[data-filters]', scope).forEach(function (bar) {
      if (!once(bar, 'filters')) return;
      var ink = $('.filters__ink', bar), btns = $$('[data-filter]', bar);
      var list = d.querySelector(bar.getAttribute('data-filters')) || d;
      function place(btn, instant) {
        if (!ink) return;
        if (instant) ink.style.transition = 'none';
        ink.style.transform = 'translateX(' + btn.offsetLeft + 'px) scaleX(' + (btn.offsetWidth / 100) + ')';
        if (instant) { void ink.offsetWidth; ink.style.transition = ''; }
      }
      function apply(btn, instant) {
        btns.forEach(function (b) { b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'); });
        place(btn, instant);
        var f = btn.getAttribute('data-filter'), shown = 0;
        $$('[data-type]', list).forEach(function (it) { var on = f === 'all' || it.getAttribute('data-type') === f; it.hidden = !on; if (on) { shown++; if (!instant) replay(it); } });
        var c = $('[data-filter-count]'); if (c) c.textContent = shown;
      }
      btns.forEach(function (b) { b.addEventListener('click', function () { apply(b); }); });
      apply($('[aria-pressed="true"]', bar) || btns[0], true);
      bar.classList.add('is-ready');
      window.addEventListener('resize', function () { place($('[aria-pressed="true"]', bar), true); });
      if (d.fonts && d.fonts.ready) d.fonts.ready.then(function () { place($('[aria-pressed="true"]', bar), true); });
    });
  }

  /* ── tag search: filters pills live ────────────────────── */
  function wireTagSearch(scope) {
    $$('[data-tag-search]', scope).forEach(function (input) {
      if (!once(input, 'tags')) return;
      var area = d.querySelector(input.getAttribute('data-tag-search')) || d, empty = $('[data-empty]', area.parentNode || d);
      input.addEventListener('input', function () {
        var q = input.value.trim().toLowerCase().replace(/^#/, ''), any = false;
        $$('[data-tag]', area).forEach(function (t) { var on = !q || t.getAttribute('data-tag').indexOf(q) > -1; t.hidden = !on; any = any || on; });
        $$('[data-letter-group]', area).forEach(function (g) { g.hidden = !$$('[data-tag]', g).some(function (t) { return !t.hidden; }); });
        if (empty) { empty.hidden = any; var b = $('b', empty); if (b) b.textContent = '“' + input.value.trim() + '”'; }
      });
    });
  }

  /* ── TOC: ink marker follows the active section ────────── */
  function wireToc(scope) {
    $$('[data-toc]', scope).forEach(function (toc) {
      if (!once(toc, 'toc')) return;
      var rail = $('.toc__rail', toc), marker = $('.toc__marker', toc);
      var links = $$('a[href^="#"]', rail);
      var heads = links.map(function (a) { return d.getElementById(decodeURIComponent(a.hash.slice(1))); });
      function set(i) {
        links.forEach(function (a, n) { if (n === i) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
        var a = links[i]; if (!a || !marker) return;
        var r = rail.getBoundingClientRect(), b = a.getBoundingClientRect();
        marker.style.setProperty('--y', (b.top - r.top) + 'px');
        marker.style.setProperty('--s', (b.height / 100).toFixed(3));
      }
      toc.Conflict = { set: set };
      var initial = links.findIndex ? links.findIndex(function (a) { return a.getAttribute('aria-current') === 'true'; }) : 0;
      set(initial > -1 ? initial : 0);
      if (d.fonts && d.fonts.ready) d.fonts.ready.then(function () { set(Math.max(0, links.findIndex(function (a) { return a.getAttribute('aria-current') === 'true'; }))); });
      if (!('IntersectionObserver' in window) || heads.some(function (h) { return !h; })) return;
      var vis = new Map();
      var obs = new IntersectionObserver(function (es) {
        es.forEach(function (e) { vis.set(e.target, e.isIntersecting); });
        for (var i = 0; i < heads.length; i++) if (vis.get(heads[i])) { set(i); return; }
      }, { rootMargin: '-' + (ms('--size-header') || 56) + 'px 0px -65% 0px' });
      heads.forEach(function (h) { obs.observe(h); });
    });
  }

  /* ── image lightbox: click, scroll-zoom, drag-pan, Esc ─── */
  var lb = null;
  function buildLightbox() {
    lb = d.createElement('div'); lb.className = 'lightbox'; lb.hidden = true; lb.setAttribute('role', 'dialog'); lb.setAttribute('aria-modal', 'true'); lb.setAttribute('aria-label', 'Image viewer');
    lb.innerHTML = '<div class="lightbox__scrim" data-lb-close></div><div class="lightbox__frame"><img alt=""></div>' +
      '<button class="btn btn--sm lightbox__close" data-lb-close><span class="btn__label">close</span><kbd>Esc</kbd></button>' +
      '<div class="lightbox__bar"><span class="lightbox__zoom">100%</span><span>scroll to zoom · drag to pan · esc to close</span></div>';
    d.body.appendChild(lb);
    var frame = $('.lightbox__frame', lb), img = $('img', lb), z = $('.lightbox__zoom', lb);
    var s = 1, x = 0, y = 0, drag = null;
    function paint() { img.style.transform = 'translate(' + x + 'px,' + y + 'px) scale(' + s + ')'; z.textContent = Math.round(s * 100) + '%'; }
    lb._reset = function () { s = 1; x = 0; y = 0; paint(); };
    frame.addEventListener('wheel', function (e) {
      e.preventDefault();
      var r = frame.getBoundingClientRect(), px = e.clientX - r.left, py = e.clientY - r.top;
      var ns = Math.min(6, Math.max(1, s * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
      x = px - (px - x) * (ns / s); y = py - (py - y) * (ns / s); s = ns;
      if (s === 1) { x = 0; y = 0; }
      paint();
    }, { passive: false });
    frame.addEventListener('pointerdown', function (e) { drag = { x: e.clientX - x, y: e.clientY - y }; frame.setPointerCapture(e.pointerId); });
    frame.addEventListener('pointermove', function (e) { if (!drag || s === 1) return; x = e.clientX - drag.x; y = e.clientY - drag.y; paint(); });
    frame.addEventListener('pointerup', function () { drag = null; });
    $$('[data-lb-close]', lb).forEach(function (b) { b.addEventListener('click', closeLightbox); });
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !lb.hidden) closeLightbox(); });
  }
  function openLightbox(src, alt, from) {
    if (!lb) buildLightbox();
    var img = $('img', lb), frame = $('.lightbox__frame', lb);
    img.src = src; img.alt = alt || ''; lb._reset(); lb._from = from || null;
    lb.hidden = false; lb.classList.remove('is-closing');
    function go() {
      if (from) { /* FLIP from the thumbnail */
        var a = from.getBoundingClientRect(), b = frame.getBoundingClientRect();
        frame.style.setProperty('--fx', (a.left - b.left) + 'px'); frame.style.setProperty('--fy', (a.top - b.top) + 'px');
        frame.style.setProperty('--fs', Math.max(0.2, a.width / b.width).toFixed(3));
        frame.style.transformOrigin = '0 0';
      }
      restart(lb, 'is-opening');
      $('.lightbox__close', lb).focus({ preventScroll: true });
    }
    img.complete ? go() : img.addEventListener('load', go, { once: true });
  }
  function closeLightbox() {
    if (!lb || lb.hidden) return;
    lb.classList.remove('is-opening'); lb.classList.add('is-closing');
    afterAnim(lb, function () { lb.hidden = true; lb.classList.remove('is-closing'); if (lb._from) lb._from.focus && lb._from.focus({ preventScroll: true }); }, ms('--dur-fast'));
  }
  function wireLightbox(scope) {
    $$('.article img, img[data-zoom]', scope).forEach(function (img) {
      if (!once(img, 'zoom')) return;
      img.tabIndex = 0; img.setAttribute('role', 'button'); img.setAttribute('aria-label', 'Open image: ' + (img.alt || 'figure'));
      function go() { openLightbox(img.currentSrc || img.src, img.alt, img); }
      img.addEventListener('click', go);
      img.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    });
  }

  /* ── cross-document transitions: reverse the cut on Back ── */
  function isBack(act) {
    try { return act && act.navigationType === 'traverse' && act.entry && act.from && act.entry.index < act.from.index; } catch (e) { return false; }
  }
  window.addEventListener('pageswap', function (e) {
    if (!e.viewTransition || !e.activation) return;
    try { if (e.activation.navigationType === 'traverse' && e.activation.entry.index < navigation.currentEntry.index) e.viewTransition.types.add('back'); } catch (err) {}
  });
  window.addEventListener('pagereveal', function (e) {
    if (!e.viewTransition || !window.navigation) return;
    if (isBack(navigation.activation)) e.viewTransition.types.add('back');
  });

  function init(scope) {
    scope = scope || d;
    reveals(scope); wireImpact(scope); wireCopy(scope); wireDisclosure(scope); wireSearch(scope);
    wireFilters(scope); wireTagSearch(scope); wireToc(scope); wireLightbox(scope);
  }
  window.Conflict = { init: init, impact: impact, replay: replay, openLightbox: openLightbox, closeLightbox: closeLightbox, version: '1.0.0' };
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', function () { init(d); }); else init(d);
})();
