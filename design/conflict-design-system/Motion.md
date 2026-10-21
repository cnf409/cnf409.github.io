# Motion

Every interaction, its trigger, the properties it touches and its tokens. "Reduced" is the behaviour under `prefers-reduced-motion: reduce`.

| Interaction | Trigger | Properties | Duration | Easing | Reduced |
| --- | --- | --- | --- | --- | --- |
| Page transition: panel cut | cross-document navigation (`@view-transition { navigation: auto }`) | new page `clip-path` diagonal wipe; old page `clip-path` + `transform` −3%; ink gutter is the `::view-transition` background; header is its own group and stays still | `dur-page` | `ease-cut` | `dur-fast` crossfade |
| Back navigation | `pageswap` / `pagereveal` with a traverse to a lower history index adds the `back` type | the same cut, mirrored | `dur-page` | `ease-cut` | crossfade |
| Unsupported browser | no cross-document View Transitions | plain navigation; entrances below still run | — | — | — |
| Heading ink reveal | `[data-reveal="ink"]` enters view, once | `clip-path` left→right, `filter` blur 5→0, `transform` −6px→0 | `dur-slow` | `ease-ink` | shown at once |
| Card / panel cut reveal | `[data-reveal="cut"]` enters view, once | diagonal `clip-path` wipe + `transform` 10px | `dur-slow`, +`dur-stagger` per sibling (max 8) | `ease-ink` | shown at once |
| Card hover | `:hover`, `:focus-within` | `tone-1` screentone layer `clip-path` sweep; arrow `transform` 4px | `dur-base` / `dur-fast` | `ease-ink` | instant |
| Brush underline | UI link `:hover`, `:focus-visible` | brush-shaped mask revealed by `clip-path` | `dur-base` | `ease-ink` | instant |
| Button hover | `.btn:hover` | ink fill `clip-path` sweep; label inverts by blend | `dur-base` | `ease-ink` | instant |
| Solid button hover | `.btn--solid:hover` | speed lines `opacity` + `transform`; arrow `transform` 5px | `dur-fast` / `dur-base` | `ease-ink` | instant |
| Impact frame | `pointerdown` / Enter / Space on `.btn`, `.filter`, `[data-impact]` | squash `transform` .94; burst `opacity` + `transform` | `dur-instant` (burst ×1.6, under 150ms) | `ease-ink` | none |
| Copy / share stamp | click → `data-state="copied"` | label `transform` scale 1.6→1 + rotate, `opacity` | `dur-slow` | `ease-ink` | label swap only |
| Tag hover | `a.tag:hover` | dense screentone `clip-path` sweep | `dur-base` | `ease-ink` | instant |
| Filter indicator | filter click | ink block `transform` translateX + scaleX; shown items replay the cut reveal | `dur-base` | `ease-ink` | jumps |
| Nav dropdown open | button click | panel `clip-path` top→down + `transform` −14px | `dur-base` | `ease-ink` | `dur-fast` fade |
| Nav dropdown close | Esc, outside click, button | `transform` −8px + `opacity` | `dur-fast` | `ease-exit` | fade |
| Menu row hover | `.menu-item:hover`, keyboard focus | ink fill `clip-path` sweep | `dur-fast` | `ease-ink` | instant |
| Phone menu | menu button | panel drop, same as dropdown | `dur-base` | `ease-ink` | fade |
| Search open | `Ctrl/⌘ K`, search button | scrim `opacity`; panel `clip-path` + `transform` drop | `dur-base` | `ease-ink` | `dur-fast` fade |
| Search results | each render (typing) | rows `transform` 6px + `opacity`, +`dur-stagger` each | `dur-base` | `ease-ink` | none |
| Active result | ↑ ↓, mouse | ink fill `clip-path` sweep | `dur-fast` | `ease-ink` | instant |
| Search close | Esc, scrim click, `esc` button | scrim `opacity`; panel `transform` + `opacity` | `dur-fast` | `ease-exit` | fade |
| Lightbox open | click / Enter on an article image | frame FLIP `transform` from the thumbnail; gutter revealed by `clip-path`; scrim `opacity` | `dur-slow` (scrim `dur-base`) | `ease-cut` | `dur-fast` fade |
| Lightbox zoom / pan | wheel, drag | image `transform` (direct, untimed) | — | — | same |
| Lightbox close | Esc, scrim, close | `transform` .96 + `opacity` | `dur-fast` | `ease-exit` | fade |
| TOC marker | active section changes (IntersectionObserver) | marker `transform` translateY + scaleY | `dur-base` | `ease-ink` | jumps |
| Mobile TOC | `<details>` open | list `clip-path` drop; chevron `transform` rotate | `dur-base` / `dur-fast` | `ease-ink` | fade |
| Avatar halftone | `.avatar:hover` | dot layer `transform` half a pitch + `opacity`; image `filter` contrast | `dur-base` | `ease-ink` | dot layer hidden |
| Flag reveal | `[data-reveal="flag"]` enters view, once | panel `filter` invert flash → focus lines `transform` + `opacity` → box `clip-path` → stamp `transform` | `dur-instant` → `dur-slow` → `dur-base` → `dur-base` (chained delays) | `ease-ink`, box `ease-cut` | shown at once |
| 404 impact | page load | focus lines `transform` + `opacity`; box `transform` + `filter` blur → 0 | `dur-slow` / `dur-base` | `ease-ink` | shown at once |
| Post nav hover | `:hover` | speed lines `opacity` + `transform`; arrow `transform` | `dur-fast` / `dur-base` | `ease-ink` | instant |
| Anchor jump | in-page link | CSS `scroll-behavior: smooth`, offset by `scroll-padding-top` | browser | browser | instant jump |

**Never animated:** anything inside `.article`, `.codeblock`, `.terminal` or the source viewer, colour or size of text, layout properties (`width`, `height`, `top`, `margin`…), and scrolling.
