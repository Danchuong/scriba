# ok-simple

## What this fixture guards

Happy-path: a single position-only annotation on a 3-cell array renders
correctly. Specifically:

- Exactly one `<rect>` pill appears above `cell[1]`.
- No `<polyline>` leader is emitted (position-only, not arc-arrow).
- The pill bounding box is within the SVG `viewBox` (0 0 200 100).
- `aria-label` equals the annotation label text (`ptr`).
- Color token `info` maps to stroke `#506882`.

## Invariants exercised

AC-1, AC-3, G-3

## Rebase trigger notes

Rebase this fixture when any of the following change:

- Pill geometry constants (`_LABEL_PILL_PAD_X`, `_LABEL_PILL_PAD_Y`,
  `_LABEL_PILL_RADIUS`, `_LABEL_HEADROOM`) — PATCH rebase.
- Color token mapping for `info` — PATCH rebase.
- Font size or `emit_position_label_svg` coordinate logic — PATCH rebase.
- SVG attribute order or element structure changes — may require rebase
  or normalizer update first.

KaTeX version bumps and Python minor-version float jitter do NOT require
a rebase (the normalizer handles both).
