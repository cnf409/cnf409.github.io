Copy and share buttons swap their label to `copied` with an ink fill and a stamp, then revert after 1.6s.

- `data-copy` copies the nearest code block, terminal (commands only) or flag. `data-copy="#id"` targets an element.
- `data-share` copies the page URL, or the URL given as its value.
- State: `data-state="copied"`. Motion: label stamp `transform`/`opacity` `dur-slow` `ease-ink`; with reduced motion, the label swaps only.
