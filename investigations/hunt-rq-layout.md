# Hunt: Render-Quality — Scene Layout (multi-shape, viewBox, spacing, transitions)

**Hunter slice:** SCENE LAYOUT quality — multi-shape composition, viewBox sizing,
spacing/density, animation-transition visual integrity, dark-mode contrast.
**Method:** read-only source study + a rendered-geometry probe that drives the
*production* emit path (`_prescan_value_widths` → `_apply_min_arrow_above` →
`measure_scene_layout` → `_emit_frame_svg`) and measures each frame's viewBox,
per-shape `<g translate>`, and `painted_extent` (rects/circles/paths, stroke-aware).
Every number below is from that probe or the real `render.py`; grading is
Confirmed-cite + rendered-geometry.
**Probe harness:** `scratchpad/rq-layout/{probe.py,probe2.py,tprobe.py}` + `*.tex`.

---

## Hand-off Brief

- **1 HIGH bug** found, with a **same-root-cause family of 5 more primitives** (MEDIUM).
- The board/stack **geometry engine itself is robust**: reserve-max + growth
  envelopes hold, R-32 translate-stability is byte-exact, zoom crops+restores,
  annotation lanes reserve, transition manifests carry no NaN/off-canvas.
- The single defect class is **value-width reservation**: 6 of 15 value-rendering
  primitives use `base.set_value` (which only stores the value) instead of
  overriding it to grow their content box. A mid-timeline
  `\apply{shape.part}{value=…}` on one of those 6 → the box stays its original
  width → the value **text overflows into neighbours and/or clips the viewBox**,
  and the viewBox never grows to compensate.
- This is a **known, documented gap**: `investigations/fixedbox-content-sizing.md:145`
  literally records `Array … APPLIED value=1000000 via prescan: 60 -> 60 (Array
  does NOT grow on \apply)` — the DPTable/Grid/Matrix fix in that doc never got
  ported back to Array (or to Stack/Tree/Graph/NumberLine).

---

## Defect table

| # | Scene / trigger | Defect | Numbers (rendered geometry) | Severity |
|---|---|---|---|---|
| 1 | `Array size=3 data=[1,2,3]` then `\apply{a.cell[1]}{value="1234567890123"}` | Cell does **not** widen on value-change; 13-char value (118px) rendered in a fixed **58px** cell, centered at x=92 → text spans x=33..151 | Intrudes **26.0px into cell[0]** (rect x1..59) **and 26.0px into cell[2]** (rect x125..183); viewBox stays **208** (no growth) | **HIGH** |
| 1b | Same, on the **edge** cell: `\apply{a.cell[0]}{value="1234567890123"}` | Half the overrun falls off the board's left edge | Value text absolute span x=**−17.0**..101; viewBox left edge = 0 → **hard clip of 17.0px** off-canvas | **HIGH** |
| 2 | Same root cause, `Matrix show_values=true` then `\apply{m.cell[0][0]}{value=100}` | `cell_size` stays **24→24** on applied value; 3-digit "100" ≈ 21px vs 22px cell rect | ~marginal overflow at 3 digits; grows unbounded for 4+ digit / string values; viewBox stays **73** | MEDIUM |
| 3 | Same root cause: `Stack`, `Tree`, `Graph`(edge), `NumberLine` applied value | Base `set_value`, no box growth (measured: Stack `_cell_width` 80→80, Tree bboxW 440→440, Graph 440→440, NumberLine 400→400) | Box dimension unchanged after `set_value("…","1234567890123")` | MEDIUM |

### Root cause (Confirmed cites)

- `scriba/animation/primitives/base.py:393-402` — `set_value` just does
  `self._values[suffix] = value`; **no width growth**.
- `scriba/animation/primitives/array.py:312` — `_grow_cell_width(value)` is called
  **only from `_apply_insert`** (structural `insert=`), never from the
  value-change channel. `array.py:337-344` defines it; grep confirms `_apply_insert`
  is its sole call site.
- Array does **not** override `set_value` (proved: `Array.set_value is
  PrimitiveBase.set_value → True`; `Queue.set_value is base → False`). Direct
  probe: `Array._cell_width 60 → 60` after `set_value('cell[1]','1000000')`,
  vs `Queue 60 → 74`.
- `scriba/animation/_frame_renderer.py:326-389` (`_prescan_value_widths`) **relies**
  on `set_value` growing a width field so the envelope reaches its timeline max
  before `measure_scene_layout`. For the 6 base-`set_value` primitives this pass
  is a silent no-op → no reservation → overflow/clip.
- **9 immune primitives override `set_value`** and grow: Bar, HashMap, DPTable,
  Grid, LinkedList, VariableWatch, Queue, TraceTable (+ Deque via Queue). Verified:
  Queue/Deque/DPTable/Grid all go `_cell_width 60 → 130` on `set_value(long)`.
- **Documented-known:** `investigations/fixedbox-content-sizing.md:145` (`Array does
  NOT grow on \apply`) and `:152` ("Array is a *partial* precedent … does **not**
  override `set_value`"). The fix that gave DPTable/Grid/Matrix an init-seed **and**
  a `set_value` growth was never applied to Array's applied path.

**End-to-end reproduction** (real `render.py`, not just probe): rendering the
scene #1 tex emits all three cell rects at `width="58.0"` (x=1, x=63, x=125) with
the 13-char value present and `viewBox="0 0 208 124"` — the shipped renderer
overflows.

**Fix shape (for the fixer):** override `Array.set_value` to call
`_grow_cell_width` (mirror Queue `queue.py:195-205`); do the same for Matrix's
applied path and, if in scope, Stack/Tree/Graph/NumberLine. Low-risk: the prescan
already replays `set_value` across the whole timeline, so a monotonic grow is
frame-stable by construction.

---

## viewBox / spacing findings (all PASS — engine is robust)

- **Board `at=[row,col]` packing** (`_frame_renderer.py:646 _pack_board`): correct.
  - 2×2 disparate sizes (A1): 4 shapes, **zero pairwise overlap**
    (arr 13–505, s 557–635, t 68–450, b 534–658). Right/left board margins are
    20 vs 13 — that is column-centering slack (rightmost shape narrower than its
    column), **not** a bug.
  - Sparse indices `at=[0,0]`+`at=[5,7]` (A4) **compact** to adjacent cells
    (reserved a=(12,12), b=(216,72)) — no canvas balloon. Matches spec §5.1.
- **Growth inside a board cell** keeps neighbours off it:
  - Horizontal grow — `LinkedList` in cell[0,0] grows f0→f3 right edge 324→654;
    Array in cell[0,1] fixed at 687–869. Board reserved the LL's **max envelope**;
    final gap **33px, no overlap**.
  - Vertical grow — `TraceTable` in row 0 grows bottom 93→261; Array in row 1
    fixed 283–321. Gap **22px, no overlap**.
- **R-32 translate stability** (per-frame `<g translate>`, must be constant):
  - Auto-stack, growing TraceTable below Array: `a`=(12,12) on **all 4 frames**.
  - Board, growing LinkedList beside Array: `a`=(686,12) on **all 4 frames**.
  - Board, growing TraceTable beside Array: `a`=(154,12) on **all 4 frames**.
  - The growing shape's **own** translate is also constant (envelope reserves max),
    so nothing jitters.
- **viewBox = max-extent across the timeline**: growing TraceTable / LinkedList /
  Bar / Queue all reserve their widest/tallest state; **no clip on the biggest
  frame** (e.g. B1 TraceTable f3 paint bottom 279 vs viewBox 292). Cost is large
  *empty* margin on early frames (Bar f0 top-margin 125px; TraceTable f0
  bottom-margin 139px) — the deliberate R-32 stability trade-off, LOW/by-design.
- **Zoom crop + restore** (`_frame_renderer.py:1561 _zoom_viewbox`): `\zoom{b.cell[2]}`
  cropped viewBox to `(128,64,76,56)` centred on the cell, then **restored to the
  full `(0,0,270,124)`** on the next step. Correct.
- **Annotation lanes**: shape with `position=above` + `position=below` on `a`,
  and `above` on `b` stacked below → a paints y13..97, b paints y119..183;
  **no clip, 22px inter-shape gap, no overlap**. Lanes reserved correctly.

### LOW / cosmetic observations (not bugs)
- Board row top-alignment aligns **bounding boxes**, so a Tree (which reserves
  internal headroom above its root) sits with content-top at y=41 while a short
  Array in the same row starts at y=13 — a 28px visual "float". By-design
  (bbox-based), minor.

---

## Transition-integrity findings (PASS)

- Dumped `compute_transitions` (`differ.py:557`) manifests across movement scenes:
  Array `reorder`, LinkedList `insert`×2, Tree `add_node`, Queue `enqueue`×N.
- `position_move` from/to and `value_change` values are **all finite and inside
  the scene viewBox** — **no NaN, no non-finite, no off-canvas mid-glide** in any
  probed transition. Each per-frame server SVG (the fs-snap frame) stands alone
  with a valid tight/max viewBox.

---

## Dark-mode / theme (PASS for layout scope)

- Cell value text emits inline `fill="#11181c"` (`array.py:575` ← `_types.py`
  state colours). That inline colour is a **no-CSS fallback**: the shipped CSS
  `.scriba-state-idle > text:not(.scriba-graph-weight){fill:var(--scriba-state-idle-text)}`
  (`scriba-scene-primitives.css:209-211`) overrides it, and `[data-theme="dark"]`
  flips `--scriba-state-idle-text` to `#ecedee` (`:718-732`). The value text is a
  direct child of the state `<g>` (`array.py:559,570`), so the selector matches →
  **dark mode is themed, not invisible.** No same-colour-on-same defect here.

---

## Conclusion + Confidence

The multi-shape layout **engine** (board packing, auto-stack, growth envelopes,
R-32 stability, zoom, annotation lanes, transition manifests) is **solid** — I
could not break it with disparate sizes, in-cell growth, sparse indices, or
movement transitions; every number matched the reserve-max contract.

The one real render-quality defect is **value-width reservation on applied
value-changes**: `Array` (HIGH — measured 26px neighbour intrusion + 17px viewBox
clip on edge cells) and the same-root family `Matrix / Stack / Tree / Graph /
NumberLine` (MEDIUM). It is a Confirmed, **documented-but-unfixed** inconsistency:
9 sibling primitives grow on `\apply{…}{value=…}`, these 6 do not.

**Confidence: HIGH.** Root cause traced to exact lines, reproduced through the
real `render.py`, corroborated by the project's own investigation note, and
quantified with rendered geometry from the production emit path.
