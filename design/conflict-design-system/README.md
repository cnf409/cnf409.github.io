conflict is a black-and-white manga page: paper, heavy ink, screentone, hard panel borders, and two spot inks used the way an editor uses red pencil. The feel comes from line weight, panel framing, type and texture. Nothing is decorative for its own sake.

## Voice and content

- Write in lowercase for UI chrome (nav, buttons, filters: `posts`, `share`, `copy`, `browse all →`). Titles keep the author's own casing ("Secure Mood Notes", "No thanks, I use AI").
- First person, direct, a little irreverent where the author already is ("hacking sh*t", "in rami malek we trust"). No marketing tone, no exclamation marks in UI.
- Emoji appear only where the author typed them in markdown (the about bio). Never as icons or decoration.
- Dates are `Apr 11, 2026` in `mono-s`. Counts and sizes are mono: `12 solves`, `4.2 KB`, `1 / 3`. Unknown values print `???` in `ink-muted` mono, never a dash.
- Language is a marker (`EN` / `FR`), never a flag.

## Colour

- Default theme is **Paper** (`light`); **Ink** (`dark`) is the same tokens inverted. Theme switches with `data-theme` on `<html>`.
- Grounds: `paper` for the page and every panel; `paper-2` for quiet fills (code body bar, inputs, table head). There is no "card background": a card is paper with an ink border.
- Text: `ink` for everything that matters, `ink-muted` for meta and comments. `tone-3` is for marks (empty stars, the TOC rail), never words.
- Screentone colours are `tone-1` (light dots, hover sweeps) and `tone-2` (dense dots, hairlines). Only `ink` text may sit directly on `tone-2` dots. Muted, red or blue text over tone goes in a paper knockout box.
- **Spot inks — sparingly, on states only.**
  - `red` (vermilion): the active state (current nav item's brush stroke), the one key highlight of a page, the flag stamp, `insane` difficulty, the terminal prompt, the `0` of the 404. Text on red is `on-red`. At most one red thing per viewport at rest.
  - `blue`: links in body copy, string literals in code, the focus ring (`focus`). Never a fill.
  - Each accent is one token: change `red` or `blue` and everything follows (the terminal prompt is derived from `red` with `color-mix`).
- `red` was deepened from the proposed `#E63322` (4.1:1 on paper) to `#d12a1a` (4.95:1) so it can carry small text. If you swap it back, keep red to fills and type ≥24px.
- `<meta name="theme-color">` is `#fafaf7` in light and `#0f0f0e` in dark (replaces `#ff0080`).

## Type

- **Display — Archivo Condensed** (Archivo variable, width pinned at 66, weights 100–900). Use `display-*` styles for titles and headings, `label` (uppercase, tracked) for eyebrows, panel tabs and badges. Heavy and condensed like an editorial headline or a manga sound effect, but it stays a real text face.
- **Body — Inter** (variable, with italics). `body-article` (18/1.72, 68ch measure) for writeups and the about bio; `body`, `body-s`, `ui`, `caption` elsewhere.
- **Code — JetBrains Mono** (variable, with italics). Ligatures off everywhere (`!=`, `=>`, `->` must read literally in exploit code). `code` for blocks, `code-inline` inside text, `mono-s` for dates, sizes, kbd, markers.
- Titles use `text-wrap: balance`. Display sizes step down on phones (see `bundle.css` `:root` media block): `display-l` 64 → 40, `display-xl` 84 → 48, body 18 → 17.
- All five files are self-hosted woff2 in `fonts/`, Latin subset, ≈220 KB total. Preload `ArchivoCondensed-Variable.woff2` and `Inter-Variable.woff2`.

## Panels, lines and texture

- Every container is drawn: `stroke-hair` for rows inside a panel, `stroke-thin` for cards, buttons, tags and code, `stroke-panel` for major panels (info card, search, header rule, avatar), `stroke-heavy` only for climax panels (flag, 404).
- No shadows and no rounded corners (`radius-0`). Depth comes from a **tone drop**: a screentone copy offset 8px behind a panel (`.tone-drop`). `radius-xs` is only for kbd and inline code.
- Panel tabs (`.panel__tab`) sit on the top border like a caption box: `INFO`, `BOX`, `EVENT`, `CONNECT`, `NOTE`.
- Gutters between panels are white: `space-4` (`space-3` on phones), like a manga page.
- **The cut**: one diagonal panel edge (`.cut`) per page at most: the home avatar. The page transition uses the same diagonal.
- Texture vocabulary, each with one job:
  - screentone dots (`.tone`, `--tone-light/-dense/-ink`): fills, hover sweeps, section marks before article h2;
  - mottled tone (`.mottle`): the cloudy patches from the reference panel, for art areas only (pinned card header);
  - speed lines: direction (post nav, solid button hover);
  - focus lines: climax only (flag panel, 404);
  - burst: the impact frame on press.

## Layout

- Page max width `size-page` (1200) inside `space-8` side margins (`space-4` on phones). Writeup body is `size-article` (720) with the TOC in `size-toc` (232) on the right from 1100px up; below that the TOC becomes a `<details>` panel above the body.
- Header is sticky and slim: `size-header` 56px (52 on phones), paper with a `stroke-panel` ink rule. Under 760px the nav moves into a menu panel; search becomes an icon button.
- Anchor scrolling is CSS (`scroll-behavior: smooth`, off under reduced motion) with `scroll-padding-top: size-header + space-6`.
- Section rhythm: `space-16` between page sections, `space-24` before the flag panel and the footer.

## Motion

Motion lives on navigation, hover, entrances and overlays. Nothing moves inside the article body, code or terminal blocks while someone reads.

- Animate only `transform`, `opacity`, `clip-path`, `filter`. No layout shift, no scroll-jacking, no JS animation library.
- Durations: `dur-instant` 90ms (impact), `dur-fast` 160ms (hover, exits), `dur-base` 260ms (sweeps, drops, slides), `dur-slow` 440ms (reveals, lightbox, flag), `dur-page` 560ms (page cut), `dur-stagger` 45ms per sibling, max 8.
- Easings: `ease-ink` for entrances and settles, `ease-cut` for panel cuts (page transition, lightbox, flag box), `ease-exit` for things leaving.
- Entrances are opt-in attributes, run once when they enter the viewport and only with JS: `data-reveal="ink"` (titles), `data-reveal="cut"` (cards and panels; siblings stagger inside `data-reveal-group`), `data-reveal="flag"`, `data-reveal="impact"` (404).
- `prefers-reduced-motion: reduce` turns every animation into a `dur-fast` crossfade or nothing. The full per-interaction table is in the Motion section.

## Interaction states

- Focus: solid 2px `focus` ring, 2px offset. Visible on every interactive element, including cards (`:has(.card__link:focus-visible)`), search results and the lightbox close button.
- Hover on outline buttons, menu rows and the connect list: an ink fill sweeps in from the left. Labels are white with `mix-blend-mode: difference`, so they read correctly at every frame. Wrap button text in `.btn__label`.
- Hover on cards: a `tone-1` screentone sweeps in; arrows nudge 4px. Hover on tags: dense tone. Hover on UI links: a brush stroke is drawn under them.
- Active/current: `aria-current` (nav, TOC, tag) and `aria-pressed` (filters) carry state; red is reserved for the current nav item's stroke.
- Copy/share: label becomes `copied` with an ink fill and a stamp, then reverts after 1.6s.

## Code, terminal, flag

- Code blocks are paper with a `stroke-thin` frame and a bar holding an inverted language tab, the file name and `copy`. The Pygments theme carries structure by **weight**: keywords bold, functions semibold, punctuation muted. Strings are `blue`. Numbers, constants, decorators, escapes and interpolation are `red`. Comments are `ink-muted` italic. Highlighted lines are `paper-2` with a red edge.
- Terminal blocks are inverted panels (`term-bg`, `term-ink`, `term-muted`): the prompt is red, output is muted. In Ink mode their bar flips to light so they never read as source code. Copy takes commands only.
- The flag panel is the climax of a writeup: `stroke-heavy` frame, focus lines, a paper knockout box, a red `FLAG` stamp, and the flag in `flag` mono with red braces.

## Iconography

- Monoline 16px SVG icons, `stroke: currentColor`, 1.8 stroke, square caps (`.icon`). The set in the previews covers search, clock, refresh, share, copy, download, pin, cap, chevron, window (Windows), terminal (Linux), menu, globe, arrow.
- OS labels use a generic window glyph and a terminal glyph, never vendor logos.
- Social and platform links (LinkedIn, Twitter, GitHub, Discord, HackTheBox, Root-Me) are text links with `↗`. Drop in your existing brand SVGs if you want marks: single ink, 18px, `currentColor`.
- Arrows are text glyphs in mono: `→ ← ↗ ↵`.

## Imagery

- The avatar is your picture (`assets/Avatar/avatar.jpg`, greyscale) in a `stroke-panel` frame. A halftone dot layer sits over it and shifts half a pitch on hover.
- Article images get a `stroke-thin` frame and open in the lightbox. Captions start with an ink `▲`.
- Favicons in related-link cards are shown greyscale in a hairline square.
