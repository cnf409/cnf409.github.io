The writeup's sticky contents column: a rail with an ink marker that slides to the active section; on narrow screens it becomes a `<details>` panel.

- `nav.toc[data-toc]` > `.toc__rail` > `ol.toc__list` (h3 nested) + `.toc__marker`, then a `back to top` link.
- Active link: `aria-current="true"`, ink bold. Others `ink-muted`.
- Motion: marker `transform` `dur-base` `ease-ink`; reduced motion jumps.
