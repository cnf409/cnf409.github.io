Links: UI links get a brush stroke drawn under them on hover; links in body copy are blue, always underlined and never animated.

- UI: add `.brush` to nav, footer and section links. `aria-current="page"` keeps the stroke on, in `red`.
- `.link-arrow` + `.arr` nudges a trailing arrow 4px on hover.
- Article: `.article a` is `blue`, 1px underline, 2px on hover.
- Motion: brush `clip-path` reveal `dur-base` `ease-ink`.
