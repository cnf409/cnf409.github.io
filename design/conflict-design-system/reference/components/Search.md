Global search opens with `Ctrl/⌘ K` or the header button and drops in like a new panel; results are keyboard-navigable.

- States: closed (header button), open with an empty query (pinned posts), typing (`N results`, matches underlined in red), active result (ink row, `↵`), no results (message and a link to tags).
- Markup: `[data-search][hidden][role=dialog]` with `.search__scrim`, `.search__panel`, `.search__input`, `.search__label`, `.search__results`, `.search__empty`, `.search__foot`. Index: `<script type="application/json" id="search-index">` of `{title,type,event,date,tags,url,pinned}`.
- Keys: ↑ ↓ move (`aria-selected`), ↵ opens, Esc closes and returns focus.
- Motion: scrim `opacity` + panel `clip-path`/`transform` drop `dur-base` `ease-ink`; rows rise with `dur-stagger`; close `dur-fast` `ease-exit`.
