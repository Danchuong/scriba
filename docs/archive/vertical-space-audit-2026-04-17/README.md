# Vertical-Space / Layout Aesthetic Audit — 2026-04-17

Triggered by user report: DPTable in `examples/tutorial_en.html` shows a large blank gap above the table on frames without annotations. Suspected affecting other primitives too.

## Reports

1. [01-vertical-reservations.md](01-vertical-reservations.md) — per-primitive code audit of `bounding_box`/`emit_svg` vertical-space reservation
2. [02-stage-layout-cross-frame.md](02-stage-layout-cross-frame.md) — emitter.py viewBox composition + cross-frame y-stability
3. [03-visual-sweep.md](03-visual-sweep.md) — rendered HTML inspection, per-primitive bug table

## Synthesis

Two distinct bug classes, both caused by the same `set_min_arrow_above` mechanism in `emitter.py:690-709`.

### Bug A — Locked top gap (DPTable; affects all DPTable frames without arrows)

The emitter pre-computes `max_ah = max(arrow_height_above for all frames)` and calls `prim.set_min_arrow_above(max_ah)` then `prim.set_annotations([])`. After this, `bounding_box()` and `emit_svg()` see `_min_arrow_above > 0` even on frames with zero current annotations.

`Array._arrow_height_above` and `DPTable._arrow_height_above` both do `return max(computed, _min_arrow_above)`. So in tutorial_en.html step 1 (no arrows), the primitive still reserves 73 px of headroom at top → blank gap.

### Bug B — Cross-frame jitter (Queue, Grid, NumberLine)

These primitives compute `arrow_above` per-frame inside `emit_svg` and `bounding_box` but do NOT consult `_min_arrow_above`. The viewBox is locked to max, but the inner `translate(0, arrow_above)` shifts per-frame:
- Queue: 0 ↔ 44 px jitter
- Grid: 0 ↔ 24 px
- NumberLine: 0 ↔ 43 px

Cells physically jump up/down between frames when annotations toggle.

### Other findings

- `_LABEL_HEADROOM = 24` (`base.py:152`) always added inside `arrow_height_above` even when no labels — inflates reserved height.
- `_PRIMITIVE_GAP = 50` (`emitter.py:51`) added between every pair unconditionally; trailing gap not subtracted from total height (~50 px wasted at bottom).
- 12 of 17 primitives are CORRECT (conditional reservations).

## Bug Matrix

| Primitive | Bug A (locked gap) | Bug B (jitter) | Other |
|---|---|---|---|
| DPTable | YES | — | — |
| Array | (only if used with arrows) | — | — |
| Queue | — | YES | — |
| Grid | — | YES | — |
| NumberLine | — | YES | — |
| HashMap, LinkedList, VariableWatch, Tree, Graph, Plane2D | — | — | safe (constant arrows or none) |
| CodePanel, Matrix, Stack, MetricPlot | — | — | no annotations |

## Fix Proposals (synthesized)

### Fix Bug B first (regressions, less debate)

Extend `set_min_arrow_above` / `_arrow_height_above` pattern to:
- `Queue` (`queue.py:233, 246`)
- `Grid` (`grid.py:197, 315`)
- `NumberLine` (`numberline.py:198, 327`)

Also need `emitter.py:690-709` to call `set_min_arrow_above` on those primitives — currently the loop only finds it on Array/DPTable because they are the only ones with the method.

### Fix Bug A (design tradeoff)

Two options:

**Option 1 — Decouple sizing from positioning**: keep `_min_arrow_above` for `translate()` stability, but DO NOT add it to `bounding_box().height`. The viewBox stays sized for the worst-frame, but primitives without current arrows render at the top of their slot. Side-effect: bottom blank space appears instead of top blank space — same total gap, different visual position. Marginal aesthetic win.

**Option 2 — Per-frame y-translate, fixed viewBox**: drop `_min_arrow_above` entirely. Each frame computes its own `arrow_above`. The outer viewBox max-height keeps the stage stable, but in frames without arrows the primitive renders at y=0 (top of slot). Re-introduces "jitter" but only as a vertical-fill behavior (table stays at top, then arrows appear above pushing down — but the cells stay where they are if anchored by their y-translate). Needs careful translate accounting.

**Option 3 — Tighter arc bounds**: investigate why `arrow_height_above` returns 73 px when arrows arc through control point y=−5. Likely `_LABEL_HEADROOM = 24` is over-conservative. Trim it conditionally (only add when an arrow has a label). Gain: ~24 px less locked gap.

### Quick wins

- Conditional `_LABEL_HEADROOM` in `arrow_height_above` (`base.py:1094-1095`): `if any(a.get("label") for a in arrow_anns): max_height += _LABEL_HEADROOM`
- Trailing `_PRIMITIVE_GAP` subtraction in `emitter.py:312-313` after stack loop.

## Suggested Fix Order

1. Quick wins (label headroom guard, trailing gap) — safe, tightens space across the board.
2. Bug B fixes — extend `_min_arrow_above` to Queue/Grid/NumberLine. Eliminates jitter.
3. Bug A — decide between Options 1/2/3. Recommend Option 3 first (tightest arc bounds), then revisit if still ugly.
