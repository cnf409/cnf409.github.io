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

      button.addEventListener('click', async () => {
        const text = code.innerText;
        try {
          if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
          } else {
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

          button.textContent = 'copied';
          button.classList.add('is-copied');
          window.setTimeout(() => {
            button.textContent = 'copy';
            button.classList.remove('is-copied');
          }, 1400);
        } catch (_) {
          button.textContent = 'failed';
          window.setTimeout(() => {
            button.textContent = 'copy';
          }, 1400);
        }
      });

      block.appendChild(button);
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
        overlay.classList.remove('is-closing');
        document.body.style.overflow = '';
        imgEl.src = '';
      }
      imgEl.addEventListener('animationend', onEnd, { once: true });
      imgEl.addEventListener('webkitAnimationEnd', onEnd, { once: true });
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

  document.addEventListener('DOMContentLoaded', () => {
    initFilters();
    markActiveNav();
    initCodeCopy();
    initLightbox();
  });
})();
