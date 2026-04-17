# Report 3 — Visual Aesthetic Sweep

## Per-Primitive Bug Table

| Primitive | File | Top gap? | Bottom gap? | Cross-frame jitter? | Other |
|---|---|---|---|---|---|
| **DPTable** | `dptable.html` | YES — 56 px locked on frames 0, 1, 8, 9 (no arrows) | No | No | `set_min_arrow_above` works; gap is correct fix's side-effect |
| **DPTable** | `tutorial_en.html` | YES — 73 px locked on frames 0, 1, 5, 6 (no arrows) | No | No | Larger than standalone because arcs dip to control-y = −5 |
| **Queue** | `queue.html` | No | No | YES — inner y-translate flips 0 ↔ 44 px across frames | Frames 0 and 6 have no arrow annotations; missing `set_min_arrow_above` |
| **Grid** | `grid.html` | No | No | YES — inner y-translate flips 0 ↔ 24 px | Frames 0 and 3 have no arrow annotations; missing `set_min_arrow_above` |
| **NumberLine** | `numberline.html` | No | No | YES — inner y-translate flips 0 ↔ 43 px | Frames 0 and 2 have no arrow annotations; missing `set_min_arrow_above` |
| Array | `array.html` | No | No | No | No arrow annotations in example; stable |
| CodePanel | `codepanel.html` | No | No | No | No annotations |
| HashMap | `hashmap.html` | No | No | No | Arrow height constant across frames |
| LinkedList | `linkedlist.html` | No | No | No | Arrow height constant across frames |
| Matrix | `matrix.html` | No | No | No | No arrows |
| MetricPlot | `metricplot.html` | No | No | No | No arrows |
| Plane2D | `plane2d.html` | No | No | No | Arrow height constant across frames |
| Stack | `stack.html` | No | No | No | No arrows |
| Tree | `tree.html` | No | No | No | Arrow height constant across frames |
| VariableWatch | `variablewatch.html` | No | No | No | Arrow height constant across frames |

## DPTable in `tutorial_en.html` — Exact Source of the Gap

SVG coordinates (all 10 frames identical layout):
- Outer container: `translate(69.0, 16)` — centres the table horizontally, top padding = 16 px
- Inner translate: `translate(0, 73)` — pushes the cell grid down 73 px to make room above for arrow arcs
- First cell rect: `y="1.0"` within inner group → absolute SVG y = 16 + 73 + 1 = **90 px from top of viewBox**

In frames 0, 1, 5, 6 (no `\annotate` arrows) the 73 px block above the cell grid is completely empty. Visible top gap = those 73 px.

**Why 73?** `set_min_arrow_above` locks the maximum `arrow_height_above` computed across all frames. Frame 2 has an annotation whose cubic-bezier arc passes through control point `y = −5` (relative to cell grid), requiring 73 px headroom. Emitter correctly locks for cross-frame stability; visual cost is 73 px dead space on frames without annotations.

## Root Cause Summary

**Bug A — Locked top gap (DPTable only):** `set_min_arrow_above` implemented for Array and DPTable. Both lock stable `arrow_above` across frames to prevent jitter. Visual cost: every frame reserves max headroom needed by any frame.

**Bug B — Cross-frame jitter (Queue, Grid, NumberLine):** Compute `arrow_above` per frame inside `emit_svg`, include in `bounding_box()`, but do NOT implement `set_min_arrow_above`. Outer viewBox is stable (locked to max); inner `translate(0, arrow_above)` group moves frame-to-frame. Cells physically jump 44/24/43 px when annotations toggle.

**Fix direction:** Extend `set_min_arrow_above` / `_min_arrow_above` to Queue, Grid, NumberLine — matching pattern in Array/DPTable. Top-gap cosmetic issue (Bug A) is separate design tradeoff: the gap is the price of jitter-free rendering. Shrinking requires per-frame viewBox crop (re-introducing canvas jitter) or tighter arc bounds.

## Key Files

- `scriba/animation/primitives/base.py` — `set_min_arrow_above`, `arrow_height_above`
- `scriba/animation/primitives/dptable.py` — has `_min_arrow_above`; Bug A source
- `scriba/animation/primitives/queue.py` — Bug B: missing `_min_arrow_above`
- `scriba/animation/primitives/grid.py` — Bug B: missing `_min_arrow_above`
- `scriba/animation/primitives/numberline.py` — Bug B: missing `_min_arrow_above`
- `scriba/animation/emitter.py` — `emit_animation_html` ~line 690 calls `set_min_arrow_above` only on primitives implementing it
