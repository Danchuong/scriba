# JZ-17 residual — the composition's constant viewBox shortfall (slot-sum honesty)

**Date:** 2026-07-13 · **Fixed in:** SCRIBA_VERSION 33→34 · **Status:** CONFIRMED + FIXED

## The report (0.38.0 status block)

Finding A fixed on every isolated repro (+14…+18px reserve), but the shipped
cses-1192 composition still under-reserved its stack column by a CONSTANT:
deepest frame gap −10px (2-line caption) / −6px (1-line) / −3px (no caption —
the bottom stack ITEM clips), invariant under `max_visible` 3/7/8. Author-side
dodge: declaring the Stack before the Grid moved the growing column off the
bottom edge.

## Reproduction

The report's composition description ("Grid 4×5 … + VariableWatch column") did
not reproduce — synthetic three-shape builds gave +11…+21px clearance on every
frame. The REAL pre-dodge file (`ojcloud` @ `ee68f9fe7`,
`…/cses-1192-counting-rooms/tutorial_vi.tex`) is Grid 5×8 + Stack + \invariant,
and reproduced immediately on main/0.38.0: **frame 4 (and its print twin)
overflow −13px, viewBox height 655 — the report's exact number** (their −10 was
glyph-measured; ours adds the descender estimate).

## Ablation

| variant | deepest-frame gap |
|---|---|
| full pre-dodge file | **−13** |
| − `\invariant` | −13 |
| − `\trace{grid…}` | −13 |
| − grid `label=` | −13 |
| − `\recolor` states | −13 |
| − `\annotate{grid…}{position=above}` pills | **+11** |

Trigger: the grid's `position=above` pills. Frame translates told the story:
with pills the grid's inner content shifts +24 (arrow headroom) and its bbox
peaks at +48 **on the last frame** (two pill rows), while the stack peaks on
frame 4 (grid only +24 there). The stack's painted y moved +48; the viewBox
grew +24.

## Root cause

`measure_scene_layout` (`scriba/animation/_frame_renderer.py`) returned two
numbers derived from DIFFERENT aggregations of the same replay:

- **reserved y-offsets** — cumulative slot cursor over each primitive's
  **timeline-max** bbox (`max_bbox`), i.e. fixed slots;
- **viewBox height** — max over frames of the **simultaneous** per-frame
  stacked totals (`max_h`).

The emit loop always paints into the fixed slots, whose total is
Σ per-shape maxima + gaps + padding. A per-frame-total max equals that only
when every shape peaks on the same frame. In cses-1192 the grid peaked on
frame 6 (274px) and the stack on frame 4 (grid at 250px there), so the slot
layout was 24px taller than any single frame's total → the bottom shape's
below-content clipped by 24 − 11px padding slack = 13px. Constant per
composition, invariant under `max_visible`, and reorder-dodgeable — all three
reported signatures. The isolated repros never triggered it because a single
mutating shape (or monotonic growth everywhere) peaks simultaneously by
construction. `_pack_board` (the `at=` grid path) already summed `max_bbox`
and was never affected.

## Fix

viewBox height now derives from the SAME slot cursor as the offsets
(`total_h = y_cursor − gap + padding`). Width was already
aggregation-independent (max of per-shape maxima). `max_h` bookkeeping
removed. Σ slots ≥ every per-frame total, so the height only ever grows, and
only for documents whose shapes peak on different frames.

## Verification

- `tests/unit/test_scene_slot_viewbox.py` — two RED→GREEN mechanism tests
  (rect ink and wrapped-caption glyphs inside the viewBox on every frame when
  maxima disagree) + one stability guard (co-occurring maxima keep the exact
  pre-fix slot-sum height, asserted from real primitive bboxes).
- Real pre-dodge cses-1192: deepest frame −13 → **+11** (viewBox 655 → 679,
  exactly the diagnosed +24). All ablation variants: zero overflow.
- Full tree green (6053 passed; `test_recursive_dos` 100-self-loops timing
  failure reproduces on clean main — pre-existing, unrelated).
- Golden corpus: 110 passed, **zero re-blesses** — every corpus scene grows
  monotonically, so maxima co-occur and bytes are identical.
