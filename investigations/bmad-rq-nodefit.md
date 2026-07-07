# Investigation — Family C: Fixed-Container Node-Label Overflow (bmad-rq-nodefit)

**Status:** Concluded · **Discipline:** bmad-investigate · **Repo:** scriba @ `__version__` 0.27.0 / `SCRIBA_VERSION` 22
**Scope:** Graph / Tree / Forest / Hypercube node primitives paint labels into a fixed-radius circle whose
size and inter-node pitch never grow for the content.

---

## Hand-off Brief (15-second read)

Node primitives paint the label as a bare `<text text-anchor="middle">` centred on the node (`cx ± tw/2`,
uncapped, `clip_overflow=False`), but the node radius is a hard constant (`_NODE_RADIUS=20`, only ever scaled
**down** by node count) and the viewBox/`bounding_box` reserves just `_PADDING+r` per side while node pitch
(`graph min_sep=2r+12`, `tree _MIN_H_GAP=50`, `hypercube _H_PITCH=2r+16`) is entirely **label-blind**. So a wide
label overflows the circle by design (CSS halo keeps it readable) but then **clips the frame** (Graph, Hypercube)
and **collides with neighbour labels** (Graph, dense Tree, dense Hypercube). The fix is structural: feed the
cross-frame-max measured label width into the `bounding_box` and the node pitch — **do not** grow the circle,
ellipsize, or shrink the font. `SCRIBA_VERSION` must bump 22→23.

---

## Confirmed Findings (evidence-graded, primitive-level exact coords)

All numbers are **primitive-level**, using the emitter's own contract: circle `cx = positions[n]`, group
`transform="translate(r, …)"` (graph.py:1841, tree.py:913; Hypercube translate is `(left_pad, arrow_above)` =
`(0,0)`), frame = `[0, bounding_box().width]`, label width = `measure_value_text(label, font)` (the shipped
"Scriba Sans" per-glyph metric — "size what you paint"). Repro `.tex` + parser in scratch `bmad-nodefit/`.

> ⚠️ Method note: an early SVG-parser read raw `<circle cx>` **without** the parent `<g translate(r)>` and
> over-reported clips by ~r. All numbers below are the **corrected** primitive-level values (cross-checked: the
> raw-parser's graph seed-1 `L=−2.5` + translate 15 = `+12.5` = exact primitive `minL`).

### F1 — GRAPH `scriba/animation/primitives/graph.py` — **CONFIRMED (HIGH)**
- `_NODE_RADIUS=20` (graph.py:62) but `_node_radius = max(12, min(20, int(min(w,h)/(2·N))))` (graph.py:990-996):
  **radius shrinks with node count** — N=7→r=20, N=10→r=15, N≥20→r=12 (floor `_NODE_MIN_RADIUS=12`, _types.py:183).
  More nodes ⇒ smaller circle ⇒ **worse** overflow. This is a density measure, never a label measure.
- **Circle overflow (by design):** 10 long names (r=15, diam 30px): widest `component` tw=75 → **22.5 px/side**
  spill (label 2.5× the diameter). Wide DP-state labels (tw≈103) at r=20 → 31 px/side.
- **Frame clip (CONFIRMED, robust with realistic labels):** reserve per side = `_PADDING+r` = 35-40 px < label
  half-width. Wide DP labels (tw≈103): **3-4 of 7 nodes clip on _every_ seed** {0,1,2,3,42}. Short names
  (tw≤75, N=10): 0-1/10 clip, seed-dependent (seed 0 `component` R=432.5>430; seed 5 `component` L=−2.5).
- **Node-node label collision (CONFIRMED):** 10 names @ seed 1 → `component × boundary` overlap 16×14 px
  (coverage 0.20). Layout/seed-dependent; `min_sep=2r+12` (graph.py:651) ignores label width.

### F1 — TREE `scriba/animation/primitives/tree.py` (+ forest.py shares this model) — **PARTIALLY CONFIRMED**
- `_NODE_RADIUS=20`, `_MIN_H_GAP=50`, `_LAYER_GAP=60` (tree.py:47-49); `width = max(400, N·50+2·PAD)` (tree.py:198).
- **Circle overflow (CONFIRMED, severe):** DP labels tw 84-133 in a 40px circle = 2.1-3.3× diameter, 22-46 px/side.
- **Frame clip (WEAK / REFUTED):** Tree widens its canvas (`N·50`) and `_reingold_tilford` centres — even tw=133
  labels fit the 440-450px frame in sparse/chain trees (0 clip observed). Tree does **not** reliably strict-clip.
- **Sibling label collision (CONFIRMED for dense trees):** flat root+N children — pitch floors toward the
  label-blind `_MIN_H_GAP`: children 4→pitch 113 (0 collisions), 6→70 (**4**), 8→64 (**6**), 10→61 (**9**),
  12→59 (**11**). Any label wider than the pitch (tw 73-92 > 59-70) overprints its neighbour.

### F2 — HYPERCUBE `scriba/animation/primitives/hypercube.py` — **CONFIRMED (MED, opt-in)**
- `_NODE_RADIUS=20`, `_H_PITCH=2·20+16=56`, `_ROW_PITCH=2·20+30=70` (hypercube.py:57-64). Emit translate `(0,0)`
  → **zero side reserve** (unlike graph/tree).
- **Default labels FIT:** `show_bits=True` paints the binary mask (≤5 chars, tw=25) → −7.5 px (comfortably inside
  the 40px circle). No default overflow.
- **Overflow only via `\apply{L.subset[i]}{value=…}`** (hypercube.py:188-195 honours the value override): bits=3,
  values `dp=123456`/`dp=999999` (tw=75) → 17.5 px/side spill; **frame clip CONFIRMED** — `subset[3]` L=−1.5,
  `subset[6]` R=185.5 > W=168.
- **Lattice-row collision (CONFIRMED, dense):** bits=4 full popcount-2 row, six `dp=NNNN` values (tw=58) →
  **6/16 nodes collide** (coverage 0.38), overlap = `tw − _H_PITCH` (≈2 px here; 19 px for tw=75).

---

## Root Cause + the radius/pitch coupling

**Causal chain (Confirmed):**
1. **Paint site** — node label emitted as a plain, uncapped SVG `<text>` centred at `cx` with `clip_overflow=False`:
   graph.py:2271-2291, tree.py:1018-1041, hypercube.py:384-407 (all `_render_svg_text(..., fo_width=r*2,
   clip_overflow=False)`). `fo_width` bounds **only** the `$math$`/foreignObject path; plain text spills freely to
   `cx ± tw/2`. Overflow-past-circle is intentional (0.21.2 changelog "overflow like plain node text instead of
   clipping" + Wave 9 CSS halo). **The circle overflow is not itself the bug** — it is the upstream cause.
2. **Footprint is label-blind** — `bounding_box` computes `content_w = self.width + 2*r` (graph.py:1548, tree.py:869)
   or `widest·_H_PITCH` (hypercube `_compute_layout` :174). It folds **caption width** (`_caption_block_width`) and
   **position=left/right pill pads** (`_h_label_pad`) but **never the node-label width**.
3. **viewBox = max `bounding_box()` across frames** (`_frame_renderer.py:545/1749/1808`), so a label at
   `cx − tw/2 < 0` is clipped by the SVG viewport.
4. **Pitch is label-blind** — `min_sep = 2*node_radius + _NODE_OVERLAP_GAP` (graph.py:651), `_MIN_H_GAP=50`
   (tree_layout `_reingold_tilford`), `_H_PITCH=2*_NODE_RADIUS+_H_GAP` (hypercube.py:63). None reference label width
   ⇒ neighbours overprint once a label exceeds the pitch.

**Is the radius a hard constant or is there a measure?** Hard constant `_NODE_RADIUS=20`, only ever scaled **down**
by node count (`int(min(w,h)/(2N))`, graph.py:993 / tree.py:205). No layout solver measures label width — verified
`measure_value_text` is imported into graph.py **only** for edge-**weight** pills (graph.py:1617), never for node
size or node pitch.

**The coupling (why this is a layout-engine change, not a paint tweak):** node pitch **and** viewBox are both pure
functions of the fixed radius/gaps. Growing the radius to fit a label would ripple into **edge-endpoint math**
(`_shorten_line_to_circle` graph.py:1973/1984, tree.py:955/956), **arrow geometry** (`_arrow_shorten`/`_arrow_cell_height`
graph.py:997/999), **group-hull inflate** (`_node_radius + _GROUP_PAD` graph.py:1723) and **cursor/annotation anchoring**
(`resolve_annotation_box` graph.py:1522, `_annotation_cell_metrics` :1529) — plus every golden. Growing the pitch
spreads nodes, but the Graph canvas is fixed at 400×300, so FR just clamps them back tighter unless the canvas grows
too. And because a node's `value=` can widen per `\apply` frame, the reserved pitch/viewBox must key off the
**cross-frame-max** label (like `set_min_arrow_above` reserves the cross-frame arrow floor) or per-frame re-flow
would break R-32 node-pin stability.

---

## Fix Design (recommended: grow the LAYOUT, keep the circle)

**Recommendation: keep the fixed circle glyph + its intentional halo-overflow; feed the cross-frame-max measured
label width into (A) the footprint/viewBox and (B) the node pitch.** This is the option that keeps DP-state labels
**fully legible** (no truncation, no sub-7px text) while only growing spacing where labels are actually wide;
short-label scenes stay byte-identical. It is a direct extension of the mechanism the code **already** uses for
captions and left/right pills (`_h_label_pad`).

**Rejected alternatives**
- **(a) Grow node radius/box to fit** — a circle fits text of width only ~`r√2`; a tw=103 label needs r≈52
  (2.6× blow-up) and ripples into all radius-coupled geometry above + all goldens. *Variant worth noting:* switch the
  glyph to a **horizontally-growing capsule** (rounded rect, height 2r, width `max(2r, tw+2·pad)`, à la Graphviz/
  Mermaid) — grows width-only, avoids the radius ripple, but is a larger visual redesign than (A)/(B).
- **(b) Ellipsis + keep radius** — destroys the DP-state content editorials exist to show (`dp[0][7]=42` → `dp…`).
  Acceptable only as an opt-in escape hatch, never the default.
- **(c) Scale font down to fit** — tw=103 in a 40px circle ⇒ ~5px font, illegible. A mild floor-capped nudge
  (≥11px) is at best a secondary polish, not a fix.

**Exact edit sites**

| # | Concern | File:line | Change |
|---|---------|-----------|--------|
| A1 | viewBox honesty (Graph) | `graph.py:1548-1561` `bounding_box` | extend `_h_label_pad()` (or add a `_node_label_pad()`) to fold each node's painted extent `framecx ± tw/2` into `left_pad` / `content_w`; `framecx = positions[n][0]+r`, `tw = measure_value_text(cross_frame_max_label(n), 14)` |
| A2 | viewBox honesty (Tree) | `tree.py:862-882` `bounding_box` | same fold (defensive — outer leaves with very wide labels) |
| A3 | viewBox honesty (Hypercube) | `hypercube.py:166-183` `_compute_layout` + `bounding_box` | add per-row label overflow to `content_w`; add a `left_pad` (translate is `(0,0)` today ⇒ zero left reserve) |
| B1 | pitch (Graph) | `graph.py:651` (`_resolve_overlaps`/FR `min_sep`) | `min_sep = max(2*node_radius, max_label_width) + _NODE_OVERLAP_GAP` (uniform) or per-pair `(w_i+w_j)/2 + gap`; **couple with a canvas grow** (self.width/height) so the spread isn't clamped back |
| B2 | pitch (Tree) | `tree_layout.py:_reingold_tilford` (~:100-194, `subtree_width`) | leaf/column spacing `max(_MIN_H_GAP, (w_i+w_{i+1})/2 + gap)`; pass per-node label widths into the layout |
| B3 | pitch (Hypercube) | `hypercube.py:63,174,180-183` (`_H_PITCH`) | per-row pitch `max(2r, max_row_label_width) + _H_GAP` |
| C | single source of truth | new helper on `PrimitiveBase` | `cross_frame_max_label_width(node)` — max over all frames' `value=` for a node — so A* (measure) and B* (layout) agree and R-32 holds |

**Layout-engine note:** because A* grows `bounding_box` and B* grows node coordinates, the scene viewBox
(`_frame_renderer` max-extent) follows automatically **iff** `bounding_box` reflects the grown pitch. The label
width feeding pitch (layout, in `__init__`) and viewBox (measure) must be the identical cross-frame-max value.

---

## RED Tests (all FAIL on 0.27.0 — verified `4 failed`)

`scratchpad/bmad-nodefit/test_nodefit_RED.py` — asserts the FULL label fits the footprint OR neighbours don't collide:

- `test_graph_wide_labels_fit_frame` — 7 wide DP labels, seed 0 → **FAILS**: `4/7 labels spill the 440px frame`.
- `test_tree_dense_siblings_no_label_collision` — root+8 wide children → **FAILS**: `6 adjacent-sibling label
  collisions (pitch<label)`.
- `test_hypercube_wide_value_fits_frame` — bits=3 + wide `value=` → **FAILS**: `2 labels spill the 168px frame:
  [('dp=123456',−1.5,73.5),('dp=999999',110.5,185.5)]`.
- `test_graph_adjacent_labels_no_collision` — 10 names, seed 1 → **FAILS**: `component × boundary 16.0px`.

These pass once A*+B* reserve the measured label width. (Graph strict-frame-fit for short labels and Tree strict-
frame-fit are intentionally **not** asserted — those are not reliably violated; the failing set is the confirmed
surface.)

---

## Impact / Blast Radius + Byte Verdict

- **Every wide-label Graph/Tree/Hypercube render changes bytes** (viewBox + node coords). Byte-golden corpus:
  **97 Graph, 61 Tree, 3 Hypercube** documents — the subset whose labels exceed `2r`/pitch will re-bless.
  Short-label scenes (node ids `S`/`A`, binary masks `011`, weight-only edges) keep `tw ≤ 2r` ⇒ the fix's `max()`
  is inert ⇒ **byte-identical** (this is the "opt-in-inert for non-wide-label docs" property to verify with a
  zero-marker-leak pass, as prior bumps did).
- **Radius is NOT changed** in the recommended fix, so edge-endpoint math, arrow geometry, hull inflate and
  cursor/annotation anchoring are untouched — the circle stays the same size, only spacing/frame grow. (This is the
  main reason to prefer grow-layout over grow-radius.)
- **`SCRIBA_VERSION` verdict: MUST bump 22 → 23.** Any rendered-byte change forces it (project DNA-3 rule; every
  prior geometry bump in `_version.py` did the same). `__version__` 0.27.0 → **0.28.0** (SemVer MINOR: additive
  layout-geometry change, no author-facing API removed).
- Guard `tests/unit/test_layout_constant_sync.py` pins these constants — update alongside any pitch/reserve change.

**Confidence: HIGH** for Graph frame-clip (wide labels, all seeds), Graph node-node collision, Hypercube
wide-value frame-clip + dense-row collision, and dense-Tree sibling collision — all reproduced deterministically at
the primitive level with exact "size-what-you-paint" metrics. **Tree strict-frame-clip is REFUTED** (canvas growth +
centring absorb it); the tree's confirmed harm is circle-overflow + dense-sibling collision. The circle-overflow
itself is by-design (halo) and is treated as the upstream cause, not the defect.
