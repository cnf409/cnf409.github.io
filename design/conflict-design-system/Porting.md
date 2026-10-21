# Porting

How to move this system into the site: Python build script, Jinja2 templates, Tailwind CSS v4, one custom CSS file, vanilla JS. Nothing here needs React or a bundler.

## Files

| From this system | Into the site | Notes |
| --- | --- | --- |
| `tokens.json` → the block below | `static/css/app.css` (Tailwind entry) | colours per theme, then `@theme` |
| `components/bundle.css` | `static/css/conflict.css`, imported after the tokens | the one custom CSS file: screentones, masks, components, motion, view transitions, Pygments theme |
| `components/bundle.js` | `static/js/conflict.js`, `<script defer>` | exposes `window.Conflict`; auto-inits on DOMContentLoaded |
| `fonts/*.woff2` | `static/fonts/` | five files, ≈220 KB, Latin subset |
| `assets/Avatar/avatar.jpg` | `static/img/avatar.jpg` | greyscale, 640px |

## Tokens for Tailwind v4

Colours live as plain custom properties per theme and are mapped into Tailwind with `@theme inline`, so `bg-paper`, `text-ink`, `border-ink` and `text-red` follow `data-theme` without `dark:` variants.

```css
@import "tailwindcss";

@font-face { font-family: "Archivo Condensed"; src: url("/static/fonts/ArchivoCondensed-Variable.woff2") format("woff2"); font-weight: 100 900; font-style: normal; font-display: swap; }
@font-face { font-family: "Inter"; src: url("/static/fonts/Inter-Variable.woff2") format("woff2"); font-weight: 100 900; font-style: normal; font-display: swap; }
@font-face { font-family: "Inter"; src: url("/static/fonts/Inter-Italic-Variable.woff2") format("woff2"); font-weight: 100 900; font-style: italic; font-display: swap; }
@font-face { font-family: "JetBrains Mono"; src: url("/static/fonts/JetBrainsMono-Variable.woff2") format("woff2"); font-weight: 100 800; font-style: normal; font-display: swap; }
@font-face { font-family: "JetBrains Mono"; src: url("/static/fonts/JetBrainsMono-Italic-Variable.woff2") format("woff2"); font-weight: 100 800; font-style: italic; font-display: swap; }

:root, [data-theme="light"] {
  --paper: #fafaf7;
  --paper-2: #f1f1ec;
  --tone-1: #e2e2dc;
  --tone-2: #c4c4bd;
  --tone-3: #86867f;
  --ink-muted: #55554f;
  --ink: #121212;
  --red: #d12a1a;
  --on-red: var(--paper);
  --blue: #2a5cff;
  --focus: var(--blue);
  --term-bg: #121212;
  --term-ink: #f2f2ec;
  --term-muted: #adada6;
}
[data-theme="dark"] {
  --paper: #0f0f0e;
  --paper-2: #191917;
  --tone-1: #2a2a27;
  --tone-2: #46463f;
  --tone-3: #7e7e76;
  --ink-muted: #b0b0a8;
  --ink: #f2f2ec;
  --red: #ff5440;
  --blue: #7b98ff;
  --term-bg: #000000;
  --term-ink: #f2f2ec;
  --term-muted: #a3a39c;
}

@theme inline {
  --color-paper: var(--paper);
  --color-paper-2: var(--paper-2);
  --color-tone-1: var(--tone-1);
  --color-tone-2: var(--tone-2);
  --color-tone-3: var(--tone-3);
  --color-ink-muted: var(--ink-muted);
  --color-ink: var(--ink);
  --color-red: var(--red);
  --color-on-red: var(--on-red);
  --color-blue: var(--blue);
  --color-focus: var(--focus);
  --color-term-bg: var(--term-bg);
  --color-term-ink: var(--term-ink);
  --color-term-muted: var(--term-muted);
}

@theme {
  --font-display: "Archivo Condensed", "Arial Narrow", "Roboto Condensed", sans-serif;
  --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --text-display-xxl: 176px; --text-display-xxl--line-height: 0.82; --text-display-xxl--font-weight: 900; --text-display-xxl--letter-spacing: -0.02em;
  --text-display-xl: 84px; --text-display-xl--line-height: 0.9; --text-display-xl--font-weight: 900; --text-display-xl--letter-spacing: -0.01em;
  --text-display-l: 64px; --text-display-l--line-height: 0.94; --text-display-l--font-weight: 900; --text-display-l--letter-spacing: -0.005em;
  --text-display-m: 36px; --text-display-m--line-height: 1; --text-display-m--font-weight: 800;
  --text-display-s: 28px; --text-display-s--line-height: 1.05; --text-display-s--font-weight: 800;
  --text-display-xs: 22px; --text-display-xs--line-height: 1.1; --text-display-xs--font-weight: 800;
  --text-label: 12px; --text-label--line-height: 1; --text-label--font-weight: 800; --text-label--letter-spacing: 0.1em;
  --text-body-article: 18px; --text-body-article--line-height: 1.72; --text-body-article--font-weight: 400;
  --text-body: 16px; --text-body--line-height: 1.6; --text-body--font-weight: 400;
  --text-body-s: 14px; --text-body-s--line-height: 1.5; --text-body-s--font-weight: 400;
  --text-ui: 14px; --text-ui--line-height: 1.2; --text-ui--font-weight: 600;
  --text-caption: 12px; --text-caption--line-height: 1.4; --text-caption--font-weight: 500; --text-caption--letter-spacing: 0.01em;
  --text-code: 14px; --text-code--line-height: 1.7; --text-code--font-weight: 400;
  --text-code-inline: 0.86em; --text-code-inline--line-height: 1; --text-code-inline--font-weight: 500;
  --text-mono-s: 12px; --text-mono-s--line-height: 1.3; --text-mono-s--font-weight: 500;
  --text-flag: 20px; --text-flag--line-height: 1.45; --text-flag--font-weight: 700;
  --spacing: 4px; /* space-N = N × 4px → p-6, gap-4, mt-16 */
  --radius-0: 0;
  --radius-xs: 2px;
  --radius-round: 999px;
  --ease-ink: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-cut: cubic-bezier(0.83, 0, 0.17, 1);
  --ease-exit: cubic-bezier(0.5, 0, 0.75, 0);
}

/* plain custom properties, used by conflict.css */
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  --space-16: 64px;
  --space-24: 96px;
  --space-32: 128px;
  --stroke-hair: 1px;
  --stroke-thin: 2px;
  --stroke-panel: 3px;
  --stroke-heavy: 6px;
  --tone-pitch-fine: 4px;
  --tone-pitch: 6px;
  --tone-pitch-coarse: 10px;
  --size-header: 56px;
  --size-page: 1200px;
  --size-article: 720px;
  --size-toc: 232px;
  --z-header: 40;
  --z-menu: 50;
  --z-search: 80;
  --z-lightbox: 90;
  --dur-instant: 90ms;
  --dur-fast: 160ms;
  --dur-base: 260ms;
  --dur-slow: 440ms;
  --dur-page: 560ms;
  --dur-stagger: 45ms;
}
```

## `<head>`

```html
<html lang="{{ lang }}" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#fafaf7" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0f0f0e" media="(prefers-color-scheme: dark)">
  <link rel="preload" href="/static/fonts/ArchivoCondensed-Variable.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/static/fonts/Inter-Variable.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/static/css/app.css">
  <script defer src="/static/js/conflict.js"></script>
</head>
```

If you add the optional Ink toggle, set `data-theme` on `<html>` from `localStorage` in a tiny inline script before the stylesheet so there is no flash, and update both `theme-color` metas.

## Page transitions

Nothing to template: `@view-transition { navigation: auto; }` in `conflict.css` turns them on for same-origin navigations in supporting browsers. The header carries `view-transition-name: site-header`, so keep exactly one `.site-header` per page. Other browsers navigate normally.

## Pygments

Render with the HTML formatter and **no** Pygments stylesheet: `conflict.css` styles the short class names.

```python
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

def code_block(src, lang, filename=None, hl_lines=()):
    body = highlight(src, get_lexer_by_name(lang), HtmlFormatter(cssclass="highlight", hl_lines=hl_lines))
    return render("partials/codeblock.html", lang=lang, filename=filename, body=body)

def terminal_block(src):  # shell sessions: prompts become .gp, output .go
    body = highlight(src, get_lexer_by_name("console"), HtmlFormatter(nowrap=True))
    return render("partials/terminal.html", body=body)

# source viewer: HtmlFormatter(cssclass="highlight", linenos="inline")
```

```html
{# partials/codeblock.html #}
<figure class="codeblock">
  <figcaption class="codeblock__bar">
    <span class="codeblock__lang">{{ lang }}</span>
    {% if filename %}<span class="codeblock__file">{{ filename }}</span>{% endif %}
    <button class="btn btn--sm" data-copy><svg class="icon"><use href="#i-copy"/></svg><span class="btn__label">copy</span></button>
  </figcaption>
  {{ body | safe }}
</figure>
```

## Behaviour hooks

`conflict.js` only toggles these. Your existing JS can keep its own logic and set the same attributes instead.

| Behaviour | Markup the CSS expects | State |
| --- | --- | --- |
| Entrances | `data-reveal="ink"`, `"cut"`, `"flag"` or `"impact"`; optional `data-reveal-group` on the parent | `.is-in`; `html.js` must be set (the script adds it) |
| Search | `[data-search]` dialog with `.search__input`, `.search__results`, `.search__empty`, `.search__label`; triggers `[data-search-open]`; index in `<script type="application/json" id="search-index">` | `hidden`, `.is-opening`, `.is-closing`, `.is-results`; rows `aria-selected` |
| Dropdown, phone menu | button `data-toggle aria-controls="id" aria-expanded` → panel `id` | `hidden`, `.is-opening`, `.is-closing` |
| Filters | `.filters[data-filters="#list"]` with `.filters__ink` and `button.filter[data-filter]`; items `[data-type]` | `aria-pressed`, items `hidden`, `.filters.is-ready` |
| Copy / share | `[data-copy]` (optional selector) or `[data-share]` (optional URL); text in `.btn__label` | `data-state="copied"` for 1.6s |
| Tag search | `input[data-tag-search="#area"]`, items `[data-tag]`, groups `[data-letter-group]`, `[data-empty]` | `hidden` |
| TOC | `nav[data-toc]` with `.toc__rail`, links to heading ids, `.toc__marker` | link `aria-current="true"`; marker `--y`, `--s` |
| Lightbox | any `.article img` or `img[data-zoom]` | built on first use; `.is-opening`, `.is-closing`; frame `--fx --fy --fs` |
| Impact frame | `.btn`, `.filter`, `[data-impact]` | `.is-impact` + a temporary `.impact-burst` child |
| Back transition | — | adds the `back` view-transition type on history traversal |

## Template rules

- Button text always sits in `<span class="btn__label">` (the hover inversion blends child elements).
- Cards are `<article class="card …">` with the title link as `.card__link` (it stretches over the card); tags inside cards are `<span class="tag">`, not links.
- Use `aria-current="page"` on the current nav link; red marks only that.
- Difficulty: `<span class="diff" data-level="easy|medium|hard|insane">` with four `<i>` pips. Stars: `<span class="stars" role="img" aria-label="2 of 3 stars"><i></i><i></i><i class="off"></i></span>`.
- The flag: wrap braces in `<span class="brace">` so they print red.
