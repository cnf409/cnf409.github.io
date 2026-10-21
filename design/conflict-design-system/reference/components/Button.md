Buttons are square, ink-bordered and lowercase; on hover an ink fill sweeps in from the left and the label inverts with it.

- Markup: `<button class="btn"><span class="btn__label">share</span></button>`. The label must be an element, because the inversion uses `mix-blend-mode: difference` on children.
- Variants: default outline; `.btn--solid` (ink fill, arrow, speed lines on hover) for the one main way forward on a view; `.btn--sm` (28px) inside bars; `.btn--icon` square, which needs an `aria-label`.
- States: `:hover`/`:focus-visible` sweep, `aria-pressed="true"` filled, `disabled`/`aria-disabled` gray border and no sweep, press = impact frame (`dur-instant`).
- Motion: sweep `clip-path` `dur-base` `ease-ink`. Impact squash + burst under 150ms.
