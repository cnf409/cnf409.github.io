Post filters (All / CTF / Box / Post) are a segmented control; an ink block slides under the active one.

- Markup: `.filters[data-filters="#list"]` > `.filters__ink` + `button.filter[data-filter][aria-pressed]` with `.filter__label`. Items in the list carry `data-type`.
- Counts are optional `<small>` children. `[data-filter-count]` anywhere on the page shows the visible total.
- Motion: indicator `transform` translateX + scaleX, `dur-base` `ease-ink`. Shown items replay the cut reveal.
