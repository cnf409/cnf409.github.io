Redesign the front-end of my personal cybersecurity blog, **cnf409.me** ("conflict"). It hosts CTF writeups, box writeups, CVE research, CTF event pages and an about page. I'm attaching my new profile picture, which is the mood reference for the whole site.

## Direction

- **Minimal manga.** The look comes from a black-and-white manga page: heavy ink lines, paper white, halftone / screentone dot textures, hard panel borders, high contrast. Treat the attached picture as a reference for ink weight, screentone texture and panel edges. Don't treat it as an illustration to copy.
- **Minimalist first.** Lots of white space and few elements. The manga feel should come from line weight, panel framing, typography and texture, not from decoration. No stickers, no fake-Japanese fonts, no kawaii clutter.
- **Palette:** ink black, paper white, two or three grays (rendered as flat grays or screentone dot patterns), plus **two spot colors used like red ink in a manga**: sparingly, on hover, active and highlight states only.
  - Proposed accent 1: vermilion red (~`#E63322`). Used for active states, the key highlight on a page, the flag reveal and "insane" difficulty.
  - Proposed accent 2: electric blue (~`#2A5CFF`). Used for links and focus rings.
  - Each accent must be a single token so I can swap it.
- **Moving away from** the current neon-cyberpunk look: cyan/magenta neon, glitch and flicker effects, the `▌` blinking-cursor logo and `~/path` terminal-style headings. None of that should survive. If I attach screenshots of the current site, use them for structure only, not style.
- **Light "paper" mode is the default.** Optionally add an inverted "ink" dark mode (white lines on black) through the same tokens.

## Motion: really smooth and nice, everywhere, but never in the way of reading

I want the site to feel alive, with polished, smooth animations on every interaction. Manga-inspired motion ideas you can use or improve on:
- **Page transitions** like turning to the next panel: a panel-wipe or diagonal cut.
- **Reveals:** ink-bleed or clip-path reveals on headings and cards as they enter the viewport.
- **Hover:** speed lines or a screentone fill sweeping in on cards; on links, an underline drawn like a brush stroke.
- **Impact frames:** a very short (<150ms) frame on clicks or button presses.
- **Avatar:** a subtle halftone shift on hover.
- **Search panel:** drops in like a new panel.
- **Lightbox:** zoom with a panel frame.
- **TOC:** an ink marker that slides to the active section.

Hard rules:
- Animate only `transform`, `opacity`, `clip-path` and `filter`. No layout shift and no scroll-jacking.
- Define a motion token scale: named durations (e.g. instant / fast / base / slow / page) and 2–3 named easings. Use them everywhere.
- Full `prefers-reduced-motion` fallback: crossfades or no motion.
- Nothing animates inside code blocks, terminal blocks or the article body while the reader is reading. Motion lives on navigation, hover, entrances and overlays.
- It must stay fast: no heavy JS animation library unless it's tiny and justified.

## Tech constraints (so I can port it)

It's a **static multi-page site**: a Python build script renders Jinja2 templates; styling is Tailwind CSS v4 (`@theme` tokens) plus one custom CSS file; behavior is vanilla JS. Please deliver:
- Plain **HTML + CSS + small vanilla JS**: no React, no SPA routing, no build-time framework.
- **Design tokens as CSS custom properties** (color, type scale, spacing, borders/ink weights, screentone patterns, motion) that I can drop into a Tailwind v4 `@theme` block.
- Page transitions that work **across separate HTML pages**, using cross-document View Transitions (`@view-transition { navigation: auto; }`), with a graceful fallback when unsupported.
- **Self-hostable fonts only** (woff2). Today I use Inter for body and a system mono for code. Propose a display face for headings that fits the manga look (heavy / condensed / editorial) while keeping body text very readable for long technical writeups. Keep a good monospace for code.
- Screentone / halftone textures in CSS (radial-gradient dot patterns) or tiny inline SVG, not big images.
- Visible keyboard focus states, WCAG AA contrast (including text over screentone), responsive down to phone width.
- Update `<meta name="theme-color">` (currently `#ff0080`) to match.

## Existing behaviors to design states for (they already exist in JS, keep them)

- **Global search:** a "search" button in the header with a `Ctrl K` hint opens a panel with an input and a results list (keyboard-navigable, active result highlighted). Design closed, open, typing, results, active result and no-results states.
- **Post filters** on the posts list: `All / CTF / Box / Post`, with an active state.
- **Copy buttons** on code blocks and source files ("copy" → "copied").
- **Share button** on posts ("share" → "copied").
- **Tag search** input that filters tag pills live, with an empty state.
- **Image lightbox:** click an image to open, scroll to zoom, drag to pan, Esc to close.
- **Nav dropdown** under "cves" listing CVE IDs.
- **Smooth anchor scrolling** with an offset for the sticky header.

## Elements that currently carry color and must be redesigned for the new palette

- Difficulty labels: `easy / medium / hard / insane` (currently green/yellow/orange/red). Make them work in B&W, e.g. screentone density or ink-stamp weight, with "insane" in the red accent.
- Star ratings (1–3 stars, currently yellow) and the personal rating `9.5 / 10`.
- Type badges: `CTF`, `BOX`, `POST`.
- OS icons for boxes (Windows / Linux, currently colored).
- Language markers `EN` / `FR` (currently small flag SVGs).
- The **flag block** at the end of writeups (currently neon green): it reveals the captured flag like `FCSC{5c3fa80e…}`. It should feel like the climax panel.
- **Syntax highlighting (Pygments):** design a code theme in ink + grays + the two accents that stays fully legible for long PHP / Python / JS / bash snippets. This is the hardest legibility problem on the site, so take it seriously.
- **Terminal blocks** (shell sessions with prompt + output): visually distinct from code blocks.

## Screens, in priority order

**0. Design system page:** tokens, type scale, buttons, tags, badges, cards, code/terminal/flag blocks, motion specimens.

**1. Writeup page (the core of the site).** Use this real content:
- Header: badge `CTF`, event name `FCSC 2026` (links to the event page), title **"Secure Mood Notes"**, language `EN`, author `conflict`, date `Apr 11, 2026`, pills "⏱ 25 min read" and "↻ updated Apr 20, 2026", share button.
- Info card: Event FCSC 2026 · Category web · Difficulty ★★★ · Solves 12 (sometimes shown as `???`) · Author Worty (link) · My rating 9.5/10. Box writeups swap this for Platform / OS / Difficulty / Personal rating.
- Optional cover image.
- Long article body: h1–h3, paragraphs, inline code, lists, blockquotes, tables, images, fenced code blocks with language label + copy button, terminal blocks.
- Flag block.
- "Files" section: downloadable solve scripts and challenge sources (file name, extension, size).
- "Related articles": external link cards with favicon + host.
- Newer / older post navigation cards.
- **Sticky TOC sidebar** on desktop with a "back to top" link; collapses on mobile.
- Tags: up to 9, e.g. `#web #web-server #php #apache #flask #ld_preload #pop_chain #snuffleupagus #rce`.

**2. Home:** avatar hero (my picture), small label `cnf409`, title "CTF Writeups & Cybersecurity Research", tagline "hacking sh*t - CTF Player, CS student based in Bordeaux", links "all posts" / "about", social icons (LinkedIn, Twitter, GitHub, Discord), then a **"Pinned"** grid of 4 featured post cards (eyebrow event name, title + language, up to 4 tags, type, date) with a "browse all →" link.

**3. Posts list:** title, count, filter buttons, list of post cards (title + language, category · difficulty · solves, up to 7 tags, date on the right), prev / next pagination with "1 / 3". Titles can be long, e.g. "No thanks, I use AI", "Thank you JavaScript", "10 Fast Fishers".

**4. Header + footer:** logo "conflict"; nav `posts · events · cves ▾ · tags · about`; search button. Footer: "conflict © 2026", linkedin / twitter / github, and the small easter-egg line "in rami malek we trust". The header is sticky and must stay slim.

**5. About:** avatar, name "conflict / cnf409", tagline, 📍 Bordeaux, France, 🎓 Ynov Campus (B2 Cyber), a markdown bio (bold, italics, emoji), and a sidebar of connection links (LinkedIn, Twitter, GitHub, HackTheBox, Root-Me, Discord).

**6. 404:** a big "404" treated as a manga impact panel, "This page doesn't exist or has been moved.", and links "home" / "all posts".

**7. Reuse the same components for:**
- Events list: event cards with title, writeup count, date range, organizers, country.
- Event page: summary grid (organizers / country / dates), markdown description, writeup cards.
- CVEs list: CVE ID, date, title, description, tags.
- Tags index: alphabetical letter groups of tag pills with counts, plus the search input.
- Single tag page.
- Source-file viewer: file name, "from <post>" · size, copy / download / back buttons, highlighted code.

## Output

A cohesive design system plus the screens above, desktop and mobile, light (and optional dark). Annotate the motion for each interaction with its duration and easing tokens.
