The sticky header: `conflict` logo, `posts · events · cves ▾ · tags · about`, and a search button with its `Ctrl K` hint.

- 56px tall, paper with a `stroke-panel` ink rule, `view-transition-name: site-header` so it stays still during page cuts.
- The current section's link has `aria-current="page"`, which keeps the brush stroke on in red.
- `cves ▾` is a disclosure: `button[data-toggle][aria-controls]` → `ul.dropdown__menu` of `.menu-item` rows (CVE ID + short label). Esc / outside click close it; ↑↓ move.
- Motion: menu drop `dur-base` `ease-ink`; close `dur-fast` `ease-exit`; rows ink-sweep `dur-fast`.
