The image lightbox: click an article image and it zooms out of its own position into a framed panel; scroll to zoom, drag to pan, Esc to close.

- Built by the script on first use. Open: FLIP `transform` from the thumbnail, gutter and frame revealed by `clip-path`, `dur-slow` `ease-cut`. Close: `dur-fast` `ease-exit`.
- Zoom is clamped to 100–600% around the cursor, and the percentage shows in the bar. Focus returns to the image on close.
