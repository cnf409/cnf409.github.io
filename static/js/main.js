(function () {
  'use strict';

  function initFilters() {
    const buttons = document.querySelectorAll('[data-filter]');
    const cards   = document.querySelectorAll('#post-list [data-type]');

    if (!buttons.length || !cards.length) return;

    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const filter = btn.dataset.filter;
        buttons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        cards.forEach((card) => {
          const match = filter === 'all' || card.dataset.type === filter;
          card.style.display = match ? '' : 'none';
        });
      });
    });
  }

  function markActiveNav() {
    const path  = window.location.pathname;
    const links = document.querySelectorAll('.nav-link');
    links.forEach((link) => {
      const href = link.getAttribute('href');
      if (href && href !== '/' && path.startsWith(href)) {
        link.style.color = 'var(--cyan)';
      }
    });
  }

  function escapeHtml(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function normalizeUnicode(value) {
    const text = String(value || '');

    if (typeof text.normalize !== 'function') return text;

    try {
      return text.normalize('NFD');
    } catch (_) {
      return text;
    }
  }

  function matchesSelector(node, selector) {
    if (!node) return false;

    const matcher = node.matches || node.msMatchesSelector || node.webkitMatchesSelector;
    return Boolean(matcher && matcher.call(node, selector));
  }

  function closestElement(node, selector) {
    if (!node) return null;
    if (typeof node.closest === 'function') return node.closest(selector);

    let current = node;
    while (current && current.nodeType === 1) {
      if (matchesSelector(current, selector)) return current;
      current = current.parentElement;
    }

    return null;
  }

  function requestAnimationFrameSafe(callback) {
    if (typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(callback);
      return;
    }

    window.setTimeout(callback, 16);
  }

  function requestText(url) {
    if (typeof window.fetch === 'function') {
      return window.fetch(url, { credentials: 'same-origin' })
        .then((response) => {
          if (!response.ok) throw new Error(`request ${response.status}`);
          return response.text();
        });
    }

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('GET', url, true);
      xhr.withCredentials = true;

      xhr.onreadystatechange = () => {
        if (xhr.readyState !== 4) return;
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.responseText);
          return;
        }
        reject(new Error(`request ${xhr.status}`));
      };

      xhr.onerror = () => reject(new Error('network error'));
      xhr.send();
    });
  }

  function requestJson(url) {
    return requestText(url).then((text) => JSON.parse(text));
  }

  function setClassState(node, className, enabled) {
    if (!node) return;
    if (enabled) node.classList.add(className);
    else node.classList.remove(className);
  }

  function scrollWindowTo(top, behavior) {
    const supportsSmoothScroll = 'scrollBehavior' in document.documentElement.style;

    if (behavior === 'smooth' && supportsSmoothScroll) {
      try {
        window.scrollTo({ top, behavior: 'smooth' });
        return;
      } catch (_) {
      }
    }

    window.scrollTo(0, top);
  }

  function normalizeSearchValue(value) {
    return String(value || '')
      .toLowerCase()
      .replace(/\s+/g, ' ')
      .trim();
  }

  function normalizeSearchText(value) {
    return normalizeSearchValue(
      normalizeUnicode(value)
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^\w#+.-]+/g, ' ')
    );
  }

  function initGlobalSearch() {
    const root = document.querySelector('[data-site-search]');
    if (!root) return;

    const trigger = root.querySelector('[data-search-trigger]');
    const panel = root.querySelector('[data-search-panel]');
    const input = root.querySelector('[data-search-input]');
    const results = root.querySelector('[data-search-results]');
    const indexUrl = root.dataset.searchIndexUrl || '/search-index.json';
    if (!trigger || !panel || !input || !results) return;

    let items = [];
    let activeIndex = -1;
    let fetchPromise = null;
    let isOpen = false;
    let visibleMatches = [];

    function compareByPriorityDate(a, b) {
      const priorityA = Number(a.priority || 0);
      const priorityB = Number(b.priority || 0);
      if (priorityA !== priorityB) return priorityB - priorityA;

      const dateA = a.date_iso || '';
      const dateB = b.date_iso || '';
      if (dateA !== dateB) return dateB.localeCompare(dateA);

      return String(a.title || '').localeCompare(String(b.title || ''));
    }

    function ensureIndex() {
      if (fetchPromise) return fetchPromise;

      fetchPromise = requestJson(indexUrl)
        .then((payload) => {
          const rawItems = Array.isArray(payload)
            ? payload
            : (payload && Array.isArray(payload.items) ? payload.items : []);
          items = Array.isArray(rawItems) ? rawItems : [];
          return items;
        })
        .catch(() => {
          items = [];
          return items;
        });

      return fetchPromise;
    }

    function scoreItem(item, query) {
      const normalizedQuery = normalizeSearchText(query);
      const title = normalizeSearchText(item.title);
      const subtitle = normalizeSearchText(item.subtitle);
      const description = normalizeSearchText(item.description);
      const haystack = normalizeSearchText(item.search_text || `${item.title} ${item.subtitle} ${item.description}`);
      const priority = Number(item.priority || 0);

      if (!normalizedQuery) return priority;

      let score = priority;
      const terms = normalizedQuery.split(/\s+/).filter(Boolean);

      if (title === normalizedQuery) score += 1200;
      else if (title.startsWith(normalizedQuery)) score += 900;
      else if (title.includes(normalizedQuery)) score += 640;

      terms.forEach((term) => {
        if (title.startsWith(term)) score += 220;
        else if (title.includes(term)) score += 150;

        if (subtitle.includes(term)) score += 60;
        if (description.includes(term)) score += 45;
        if (haystack.includes(term)) score += 25;
      });

      return score;
    }

    function getMatches(query) {
      const normalizedQuery = normalizeSearchText(query);
      const scored = items
        .map((item) => ({ item, score: scoreItem(item, normalizedQuery) }))
        .filter(({ item, score }) => !normalizedQuery || score > Number(item.priority || 0))
        .sort((a, b) => {
          if (b.score !== a.score) return b.score - a.score;
          return compareByPriorityDate(a.item, b.item);
        })
        .map(({ item }) => item);

      return scored.slice(0, 8);
    }

    function renderResults(matches, query) {
      visibleMatches = matches;

      if (!matches.length) {
        results.innerHTML = `
          <div class="site-search__empty">
            <strong>No result</strong>
            <span>Try another title, tag, event, or CVE.</span>
          </div>
        `;
        activeIndex = -1;
        return;
      }

      results.innerHTML = matches.map((item, index) => `
        <a
          href="${escapeHtml(item.url)}"
          class="site-search__result${index === activeIndex ? ' is-active' : ''}"
          data-search-result
          data-search-index="${index}">
          <span class="site-search__result-top">
            <span class="site-search__result-kind">${escapeHtml(item.kind_label || item.kind || 'Result')}</span>
            <span class="site-search__result-title">${escapeHtml(item.title)}</span>
          </span>
          ${item.subtitle ? `<span class="site-search__result-subtitle">${escapeHtml(item.subtitle)}</span>` : ''}
          ${item.description ? `<span class="site-search__result-copy">${escapeHtml(item.description)}</span>` : ''}
        </a>
      `).join('');

      const hint = document.createElement('div');
      hint.className = 'site-search__hint';
      hint.textContent = query
        ? 'Enter to open the selected result'
        : 'Suggestions from recent posts, tags, and events';
      results.appendChild(hint);

      syncActiveResultScroll();
    }

    function syncActiveResultScroll() {
      if (activeIndex < 0) return;

      const active = results.querySelector(`[data-search-index="${activeIndex}"]`);
      if (!active) return;

      const pad = 8;
      const activeTop = active.offsetTop;
      const activeBottom = activeTop + active.offsetHeight;
      const viewTop = results.scrollTop;
      const viewBottom = viewTop + results.clientHeight;

      if (activeTop < viewTop + pad) {
        results.scrollTop = Math.max(0, activeTop - pad);
      } else if (activeBottom > viewBottom - pad) {
        results.scrollTop = activeBottom - results.clientHeight + pad;
      }
    }

    function updateActiveResult() {
      const links = results.querySelectorAll('[data-search-result]');
      links.forEach((link) => {
        const index = Number(link.dataset.searchIndex || -1);
        setClassState(link, 'is-active', index === activeIndex);
      });

      syncActiveResultScroll();
    }

    function refreshResults() {
      visibleMatches = getMatches(input.value);
      if (visibleMatches.length) {
        activeIndex = Math.min(activeIndex, visibleMatches.length - 1);
        if (activeIndex < 0) activeIndex = 0;
      } else {
        activeIndex = -1;
      }
      renderResults(visibleMatches, input.value);
    }

    function openPanel() {
      if (isOpen) return;
      isOpen = true;
      root.classList.add('is-open');
      panel.hidden = false;
      trigger.setAttribute('aria-expanded', 'true');
      ensureIndex().then(() => refreshResults());
    }

    function closePanel() {
      if (!isOpen) return;
      isOpen = false;
      root.classList.remove('is-open');
      panel.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      activeIndex = -1;
    }

    function focusSearch() {
      openPanel();
      requestAnimationFrameSafe(() => {
        input.focus();
        input.select();
      });
    }

    trigger.addEventListener('click', () => {
      if (isOpen) {
        input.focus();
        return;
      }
      focusSearch();
    });

    input.addEventListener('focus', openPanel);
    input.addEventListener('input', () => {
      activeIndex = 0;
      refreshResults();
    });

    input.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        closePanel();
        trigger.focus();
        return;
      }

      if (!visibleMatches.length) return;

      if (event.key === 'ArrowDown') {
        event.preventDefault();
        activeIndex = (activeIndex + 1) % visibleMatches.length;
        updateActiveResult();
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        activeIndex = (activeIndex - 1 + visibleMatches.length) % visibleMatches.length;
        updateActiveResult();
      } else if (event.key === 'Enter' && activeIndex >= 0) {
        event.preventDefault();
        const active = results.querySelector(`[data-search-index="${activeIndex}"]`);
        if (active) window.location.href = active.getAttribute('href');
      }
    });

    results.addEventListener('mouseover', (event) => {
      const link = closestElement(event.target, '[data-search-result]');
      if (!link) return;
      const nextIndex = Number(link.dataset.searchIndex || 0);
      if (nextIndex === activeIndex) return;
      activeIndex = nextIndex;
      updateActiveResult();
    });

    results.addEventListener('click', (event) => {
      if (closestElement(event.target, '[data-search-result]')) closePanel();
    });

    document.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        focusSearch();
      }

      if (event.key === 'Escape' && isOpen && document.activeElement !== input) {
        closePanel();
      }
    });

    document.addEventListener('click', (event) => {
      if (!isOpen) return;
      if (!root.contains(event.target)) closePanel();
    });
  }

  async function writeTextToClipboard(text) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      await navigator.clipboard.writeText(text);
      return;
    }

    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    textarea.remove();
  }

  function flashCopyState(button, label, copied) {
    const defaultLabel = button.dataset.defaultLabel || 'copy';
    const labelNode = button.querySelector('[data-button-label]');

    if (labelNode) labelNode.textContent = label;
    else button.textContent = label;

    button.setAttribute('aria-label', label);
    setClassState(button, 'is-copied', Boolean(copied));

    window.setTimeout(() => {
      if (labelNode) labelNode.textContent = defaultLabel;
      else button.textContent = defaultLabel;

      button.setAttribute('aria-label', defaultLabel);
      button.classList.remove('is-copied');
    }, 1400);
  }

  function initCodeCopy() {
    const blocks = document.querySelectorAll('.highlight');
    if (!blocks.length) return;

    blocks.forEach((block) => {
      if (block.querySelector('.code-copy-btn')) return;
      const code = block.querySelector('code');
      if (!code) return;

      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'code-copy-btn';
      button.textContent = 'copy';
      button.dataset.defaultLabel = 'copy';

      button.addEventListener('click', async () => {
        const text = code.innerText;
        try {
          await writeTextToClipboard(text);
          flashCopyState(button, 'copied', true);
        } catch (_) {
          flashCopyState(button, 'failed', false);
        }
      });

      block.appendChild(button);
    });
  }

  function initSourceCopy() {
    const buttons = document.querySelectorAll('[data-copy-source]');
    if (!buttons.length) return;

    buttons.forEach((button) => {
      button.addEventListener('click', async () => {
        let text = '';
        const url = button.dataset.copyUrl;
        const fallbackSelector = button.dataset.copyTarget;

        if (url) {
          try {
            text = await requestText(url);
          } catch (_) {
          }
        }

        if (!text && fallbackSelector) {
          const sourceEl = document.querySelector(fallbackSelector);
          if (sourceEl) text = sourceEl.innerText;
        }

        if (!text) {
          flashCopyState(button, 'failed', false);
          return;
        }

        try {
          await writeTextToClipboard(text);
          flashCopyState(button, 'copied', true);
        } catch (_) {
          flashCopyState(button, 'failed', false);
        }
      });
    });
  }

  function initShareButtons() {
    const buttons = document.querySelectorAll('[data-share-post]');
    if (!buttons.length) return;

    buttons.forEach((button) => {
      button.addEventListener('click', async () => {
        const url = window.location.href;
        const title = button.dataset.shareTitle || document.title;

        if (navigator.share) {
          try {
            await navigator.share({ title, url });
            flashCopyState(button, 'shared', true);
            return;
          } catch (error) {
            if (error && error.name === 'AbortError') return;
          }
        }

        try {
          await writeTextToClipboard(url);
          flashCopyState(button, 'link copied', true);
        } catch (_) {
          flashCopyState(button, 'failed', false);
        }
      });
    });
  }

  function initLightbox() {
    const content = document.querySelector('.post-content');
    if (!content) return;

    const imgs = content.querySelectorAll('img');
    if (!imgs.length) return;

    const overlay = document.createElement('div');
    overlay.className = 'lightbox-overlay';
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('role', 'dialog');

    const imgEl = document.createElement('img');
    imgEl.className = 'lightbox-img';
    imgEl.alt = '';

    overlay.appendChild(imgEl);
    document.body.appendChild(overlay);

    let isZoomed = false;
    let tx = 0, ty = 0;
    let isDragging = false;
    let hasMoved = false;
    let dragStartX, dragStartY, dragOriginTx, dragOriginTy;

    function applyTransform() {
      imgEl.style.transform = `translate(${tx}px, ${ty}px) scale(2)`;
    }

    function resetZoom() {
      isZoomed = false;
      tx = 0; ty = 0;
      overlay.classList.remove('is-zoomed');
      imgEl.style.transform = '';
      imgEl.style.cursor = 'zoom-in';
    }

    function open(src, alt) {
      imgEl.src = src;
      imgEl.alt = alt || '';
      resetZoom();
      overlay.classList.remove('is-open', 'is-closing');
      void overlay.offsetWidth; // force reflow so the animation replays
      overlay.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }

    function close() {
      resetZoom();
      overlay.classList.remove('is-open');
      overlay.classList.add('is-closing');
      let done = false;
      function onEnd() {
        if (done) return;
        done = true;
        imgEl.removeEventListener('animationend', onEnd);
        imgEl.removeEventListener('webkitAnimationEnd', onEnd);
        overlay.classList.remove('is-closing');
        document.body.style.overflow = '';
        imgEl.src = '';
      }
      imgEl.addEventListener('animationend', onEnd);
      imgEl.addEventListener('webkitAnimationEnd', onEnd);
    }

    function hitsImage(e) {
      const r = imgEl.getBoundingClientRect();
      const cx = e.clientX - r.left;
      const cy = e.clientY - r.top;
      const ir = imgEl.naturalWidth / imgEl.naturalHeight;
      const br = r.width / r.height;
      let iw, ih, ox, oy;
      if (ir > br) { iw = r.width;  ih = r.width / ir;  ox = 0;                    oy = (r.height - ih) / 2; }
      else          { ih = r.height; iw = r.height * ir; ox = (r.width - iw) / 2;  oy = 0; }
      return cx >= ox && cx <= ox + iw && cy >= oy && cy <= oy + ih;
    }

    imgEl.addEventListener('click', (e) => {
      if (hasMoved) { hasMoved = false; return; }
      if (!hitsImage(e)) { close(); return; }
      e.stopPropagation();
      if (!isZoomed) {
        isZoomed = true;
        overlay.classList.add('is-zoomed');
        imgEl.style.cursor = 'grab';
        applyTransform();
      } else {
        resetZoom();
      }
    });

    imgEl.addEventListener('mousedown', (e) => {
      if (!isZoomed) return;
      e.preventDefault();
      isDragging = true;
      hasMoved = false;
      dragStartX = e.clientX;
      dragStartY = e.clientY;
      dragOriginTx = tx;
      dragOriginTy = ty;
      imgEl.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - dragStartX;
      const dy = e.clientY - dragStartY;
      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) hasMoved = true;
      tx = dragOriginTx + dx;
      ty = dragOriginTy + dy;
      applyTransform();
    });

    window.addEventListener('mouseup', () => {
      if (!isDragging) return;
      isDragging = false;
      if (isZoomed) imgEl.style.cursor = 'grab';
    });

    imgs.forEach((img) => {
      img.style.cursor = 'zoom-in';
      img.addEventListener('click', () => open(img.src, img.alt));
    });

    overlay.addEventListener('click', (e) => {
      if (e.target !== imgEl) close();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && overlay.classList.contains('is-open')) close();
    });
  }

  function getHashTarget(hash) {
    if (!hash || hash === '#') return null;

    let id = String(hash).replace(/^#/, '');
    try {
      id = decodeURIComponent(id);
    } catch (_) {
    }
    return id ? document.getElementById(id) : null;
  }

  function getAnchorOffset() {
    const header = document.querySelector('.site-header');
    return ((header && header.offsetHeight) || 0) + 16;
  }

  function scrollToHashTarget(hash, behavior = 'smooth') {
    const target = getHashTarget(hash);
    if (!target) return false;

    const top = Math.max(
      0,
      window.scrollY + target.getBoundingClientRect().top - getAnchorOffset()
    );

    scrollWindowTo(top, behavior);
    return true;
  }

  function initAnchoredScroll() {
    const tocLinks = document.querySelectorAll('.post-toc a[href^="#"]');
    if (!tocLinks.length) return;

    let correctionTimer = 0;
    let lateCorrectionTimer = 0;

    function scheduleCorrection(hash) {
      window.clearTimeout(correctionTimer);
      window.clearTimeout(lateCorrectionTimer);

      correctionTimer = window.setTimeout(() => {
        scrollToHashTarget(hash, 'auto');
      }, 220);

      lateCorrectionTimer = window.setTimeout(() => {
        scrollToHashTarget(hash, 'auto');
      }, 800);
    }

    tocLinks.forEach((link) => {
      link.addEventListener('click', (event) => {
        const hash = link.getAttribute('href');
        if (!hash || !scrollToHashTarget(hash, 'smooth')) return;

        event.preventDefault();
        if (window.history && typeof window.history.pushState === 'function') {
          window.history.pushState(null, '', hash);
        } else {
          window.location.hash = hash;
        }
        scheduleCorrection(hash);
      });
    });

    if (window.location.hash) {
      const onLoad = () => {
        if (scrollToHashTarget(window.location.hash, 'auto')) {
          scheduleCorrection(window.location.hash);
        }
        window.removeEventListener('load', onLoad);
      };

      window.addEventListener('load', onLoad);
    }

    window.addEventListener('hashchange', () => {
      if (scrollToHashTarget(window.location.hash, 'auto')) {
        scheduleCorrection(window.location.hash);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initFilters();
    markActiveNav();
    initGlobalSearch();
    initCodeCopy();
    initSourceCopy();
    initShareButtons();
    initLightbox();
    initAnchoredScroll();
  });
})();
