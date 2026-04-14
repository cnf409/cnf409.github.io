/* main.js — conflict blog */

(function () {
  'use strict';

  // ── Post type filter ──────────────────────────────────────
  function initFilters() {
    const buttons = document.querySelectorAll('[data-filter]');
    const cards   = document.querySelectorAll('#post-list [data-type]');

    if (!buttons.length || !cards.length) return;

    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const filter = btn.dataset.filter;

        // active state
        buttons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');

        // show / hide
        cards.forEach((card) => {
          const match = filter === 'all' || card.dataset.type === filter;
          card.style.display = match ? '' : 'none';
        });
      });
    });
  }

  // ── Active nav link ───────────────────────────────────────
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

  // ── Copy buttons on code blocks ──────────────────────────
  function initCodeCopy() {
    const blocks = document.querySelectorAll('.highlight, .terminal-block');
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

  // ── Init ──────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    initFilters();
    markActiveNav();
    initCodeCopy();
  });
})();
