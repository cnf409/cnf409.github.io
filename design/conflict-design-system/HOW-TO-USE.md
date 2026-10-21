# conflict design system — files for the cnf409.me repo

Read in this order:
1. `README.md`: the brand book (colour, type, panels, texture, motion, states, iconography). The rules to follow.
2. `Porting.md`: Tailwind v4 `@theme` block, `<head>`, Pygments setup, Jinja partials, and the JS behaviour hooks.
3. `Motion.md`: every interaction with its trigger, properties, duration and easing tokens.
4. `tokens.json`: source of truth for every token value.

Code:
- `css/tokens.css`: compiled tokens (light/dark themes, `@font-face`, type classes).
- `css/conflict.css`: all component styles, screentones, motion, view transitions and the Pygments theme.
- `js/conflict.js`: vanilla behaviours (search, filters, copy/share, dropdown, TOC, lightbox, reveals). Exposes `window.Conflict`.
- `fonts/`: self-hosted woff2. `img/avatar.jpg`: the avatar.

Reference markup: `reference/components/*.html` and `reference/pages/*.html` open directly in a browser. Each has a `.md` beside it with usage rules. Copy markup from these when building Jinja templates.
