Screentone is the texture system: CSS dot screens plus four SVG masks (focus lines, speed lines, mottle, burst), each with one job.

- `.tone` + modifier (`--light`, `--dense`, `--coarse`, `--ink`) paints a 45° dot screen. Set `--tone-c`, `--tone-p`, `--tone-r` to tune ink, pitch and dot size.
- Masks are custom properties (`--mask-focus-lines`, `--mask-speed-lines`, `--mask-mottle`, `--mask-burst`, `--mask-brush`) used with `mask:` on an element filled with `ink` or `tone-2`.
- Only `ink` text may sit on `tone-2` dots. Put any other text in a `.knockout` (paper, ink border).
- Don't: put screentone behind body copy or code, or use focus lines anywhere except climax panels.
