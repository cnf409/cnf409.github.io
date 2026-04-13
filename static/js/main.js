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

  // ── Init ──────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    initFilters();
    markActiveNav();
  });
})();
