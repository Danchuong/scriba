# Comparative Landscape: Label Placement in Educational Algorithm-Visualization Tools

**Date**: 2026-04-21  
**Scope**: How nine external tools handle label placement, disambiguation, leader lines,
colorblind cues, and hierarchy emphasis — benchmarked against scriba's unified smart-label
engine (v0.10.0, `_svg_helpers.py`).  
**Audience**: Scriba maintainers planning MW-3 / MW-4 / accessibility hardening.  
**Status**: Research snapshot — update when new external art is found.

---

## 1. Methodology

### 1.1 Systems reviewed (in depth)

| # | System | Version / Commit | Depth |
|---|--------|-----------------|-------|
| 1 | **Manim Community** (`next_to`, `Brace`, `Arrow`) | `main` branch, April 2026 | Source + docs |
| 2 | **3Blue1Brown visual style** | `3b1b/videos` repo + YouTube survey | Source + observation |
| 3 | **VisuAlgo** (Halim, NUS) | Live site + `jonathanirvings/VisuAlgo` mirror | Source HTML/JS |
| 4 | **algorithm-visualizer** (github.com/algorithm-visualizer) | `main` branch, April 2026 | Source + tracer docs |
| 5 | **D3-Labeler / d3-force collision** | `tinker10/D3-Labeler` + d3.js v7 docs | Source + docs |
| 6 | **Gephi Label Adjust** | Gephi 0.10 + blog post | Plugin source + blog |
| 7 | **matplotlib / adjustText** | `Phlya/adjustText` + matplotlib 3.10 docs | Full source |
| 8 | **CLRS textbook figures** | 4th ed. (2022) visual survey | Static observation |
| 9 | **Vega-label FLP** | arXiv 2405.10953 + `vega/vega-label` | Paper + source |

### 1.2 Supplementary references

The following were examined at lighter depth and appear in the comparison matrix but not
as full sections: TikZ `\node[label=...]` grammar (tikz.dev docs), Observable Plot `dodge`
transform (`observablehq/plot` source), Mapbox GL symbol layout (mapbox-gl-native wiki),
Graphviz `xlabel` (`lib/common/postproc.c` hack by Peter Corke),
Cytoscape.js `nodeDimensionsIncludeLabels` (issues #1626, #1374, #2170),
d3fc-label-layout greedy/annealing/remove-overlaps strategies.

### 1.3 Questions answered for each system

For every system reviewed we sought answers to:

1. **Placement algorithm** — natural position → conflict detection → displacement / removal
2. **Displacement threshold** — when does a leader / callout appear?
3. **Leader styling** — dashed vs. solid, directional arrowhead, anchor dot?
4. **Colorblind disambiguation** — what non-color cues are provided?
5. **Hierarchy emphasis** — how are "important" edges / labels distinguished?
6. **Target occlusion** — do labels avoid the focal node/cell?
7. **Directional bias** — above > below > right > left preference ordering?

### 1.4 What is excluded

- Map-labeling systems with no pedagogy use (Mapbox GL, HERE Maps) — included only in
  comparison matrix where algorithms are portable.
- Commercial screencasting tools (Camtasia, Loom) — no algorithmic label placement.
- AI-generated diagram tools (Napkin.ai, Eraser.io) — insufficient source access.
- Scriba internal test data and benchmark numbers — cited from existing audit docs rather
  than re-measured here.

### 1.5 Scriba baseline

Scriba v0.10.0 (commit `539bb5e`) uses a **32-candidate grid nudge** with 8 compass
directions × 4 step sizes `(0.25, 0.5, 1.0, 1.5) × pill_h`. Conflict detection is an
O(n) AABB list scan over previously placed pill bounding boxes only. Source:
`scriba/animation/primitives/_svg_helpers.py` — `_nudge_candidates`, `_LabelPlacement`,
`emit_arrow_svg`, `emit_plain_arrow_svg`.

---

## 2. System-by-System Deep-Dive

### 2.1 Manim Community — `Mobject.next_to` / `Brace` / `Arrow`

#### Placement algorithm

`Mobject.next_to(reference, direction, buff=0.25)` is the primary label-placement
primitive. It computes the AABB of the reference object, takes the extreme point in
the given compass `direction`, and shifts the label's opposing edge to that point plus
`buff` world-units of clearance. Source: `manim/mobject/mobject.py`, `next_to` method
(GitHub: `ManimCommunity/manim`, `main` branch).

`Brace.get_text()` / `Brace.put_at_tip()` position labels at the brace tip using either
(a) `next_to(tip, direction, buff=DEFAULT_MOBJECT_TO_MOBJECT_BUFFER)` or (b) a direct
`shift` by `mob.width / 2 + buff` along the brace direction vector. Source:
`manim/mobject/svg/brace.py`.

**No collision avoidance exists in the Manim engine.** When two labels share
a `next_to` call site, the author must manually choose distinct directions.
`arrange` and `arrange_in_grid` lay out a list linearly but do not detect pairwise
overlap. This is a fully manual system — the engine provides geometric primitives;
pedagogy authors are responsible for disambiguation.

```
ASCII: Manim next_to model

    ┌───────┐  buff
    │ label │←──── placed here
    └───────┘
        │
    direction=UP
        ↓
    ┌───────────┐
    │  target   │
    └───────────┘
```

#### Code / doc reference

- `ManimCommunity/manim` → `manim/mobject/mobject.py` — `next_to`, `arrange`,
  `arrange_in_grid`  
  https://github.com/ManimCommunity/manim/blob/main/manim/mobject/mobject.py
- `ManimCommunity/manim` → `manim/mobject/svg/brace.py` — `put_at_tip`, `get_text`  
  https://github.com/ManimCommunity/manim/blob/main/manim/mobject/svg/brace.py
- Docs: https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html

#### Pros for pedagogy

- Explicit directional control. Authors can express "put this label above and to the
  right of this arrow, 0.3 units out" in a single readable call — highly readable
  source code.
- `buff` parameter is pedagogically meaningful: it communicates that the label is
  *about* a specific object, not floating freely.
- 3Blue1Brown's videos demonstrate that purely manual placement, when done well, produces
  consistently clean visuals because the author is always aware of every object's position.

#### Cons for pedagogy

- Zero automation. A 10-node graph with edge labels requires 10 manual `next_to`
  calls and careful direction choices. This does not scale to a batch system like scriba
  where annotations are data-driven.
- No leader lines. When a label must be displaced far from its anchor (dense scene),
  the visual connection to the target is severed silently.
- Crash-on-overlap: Manim does not warn when two labels overlap. The rendered frame
  is silently wrong.

---

### 2.2 3Blue1Brown Video Style — Visual Conventions

#### Placement algorithm

3Blue1Brown videos (source: `3b1b/videos` repository, https://github.com/3b1b/videos)
use fully manual label placement via Manim's `next_to` / `shift` primitives. The style
conventions observed across 2019–2025 videos are:

- **Labels above formulas** with `UP` direction (never below when avoidable)
- **Color-matched labels** — a label referring to a red variable is rendered in the same
  red; the color *is* the connection between label and referent
- **"Indicate" animations** — `Indicate`, `Circumscribe`, `FocusOn` draw the eye before
  the label appears; label placement follows attention, not collision avoidance
- **Arrow annotations** use `CurvedArrow` or `Arrow` with `tip_length` and `max_stroke_width_to_length_ratio` tuned per scene; the arrow body is styled to match the label color
- **Background rectangles** (`BackgroundRectangle`) are sometimes placed behind multi-word
  labels that overlap a busy background, serving the same role as scriba's pill background

#### Color hierarchy for emphasis

From video observation and the `3b1b/videos` color convention, the de facto palette:

| Role | Typical Color |
|------|--------------|
| Primary concept | Yellow (`YELLOW`, `#FFFF00`) |
| Secondary / related | Blue (`BLUE`, `#58C4DD`) |
| Contrast emphasis | Red (`RED`, `#FC6255`) |
| Background / muted | Gray |
| Positive / correct | Green (`GREEN`, `#83C167`) |

The color *carries* the semantic weight; no shape or stroke-width difference is required
because the animations build the mental model before the label appears.

#### Code / doc reference

- `3b1b/videos` repo: https://github.com/3b1b/videos
- Manim original: `3b1b/manim` https://github.com/3b1b/manim
- `manimlib/mobject/mobject.py` — `next_to`, `shift` in 3b1b's fork

#### Pros for pedagogy

- Color-semantic labeling is extremely learnable: "red = the thing we're tracking"
  works without any text at all.
- Animations build context so dense frames are rarely needed — the video paces
  information delivery to match placement capacity.
- `BackgroundRectangle` is a simple but effective halo pattern that generalizes to
  any rendering system.

#### Cons for pedagogy

- Relies entirely on animated sequencing; static frames (e.g., textbook exports or
  scriba's step-by-step SVGs) break the color-context assumption because the prior
  animation is not visible.
- No colorblind accommodation — the primary differentiation mechanism *is* color.
  3Blue1Brown has acknowledged accessibility gaps but has not changed the core convention.
- Not portable to interactive/generative tools without author-time editorial judgment.

---

### 2.3 VisuAlgo — Halim's Graph / DP Visualizer

#### Placement algorithm

VisuAlgo (https://visualgo.net, mirror: `jonathanirvings/VisuAlgo` on GitHub) renders
graph nodes as SVG circles of fixed radius 16 px. Node labels (the integer id) are
placed **at the node center** using `<text x="{cx}" y="{cy+baseline_offset}">`. No
displacement from center; the label is inside the circle.

Edge weight labels are placed at the parametric midpoint of the edge (straight line
between nodes), horizontally offset by a small fixed amount (estimated 5–8 px from
source HTML). There is **no collision avoidance** for edge labels. When two edges
are close and both weighted, their labels overlap.

DP table cells are rendered as `<rect>` + `<text>` at cell center. Cell indices (row/col
headers) are placed outside the table boundary at fixed offsets above/left. No collision
avoidance.

#### Code / doc reference

- `jonathanirvings/VisuAlgo` → `graphds.html` + linked `visual_final.js`  
  https://github.com/jonathanirvings/VisuAlgo/blob/master/graphds.html
- Live site: https://visualgo.net/en/graphds

```
ASCII: VisuAlgo node label model

    ╭───────╮
    │   0   │  ← label at node center (inside circle)
    ╰───────╯
         |
      edge mid: "12"  ← label at parametric t=0.5, fixed offset
```

#### Pros for pedagogy

- Inside-node labeling is compact and unambiguous — the label is indisputably about
  the node it lives in.
- Students see the integer id immediately without scanning nearby space.

#### Cons for pedagogy

- Edge labels have zero displacement budget — dense graphs produce overlapping weights
  with no fallback.
- Cell-text labels in DP tables cannot grow without resizing cells; long values truncate.
- No non-color disambiguation. Directed edges use arrowheads; otherwise no shape/texture
  differentiation. Colorblind students must infer direction purely from arrowhead shape.
- No hierarchy emphasis for "current step" beyond a color highlight — the highlighted
  node/edge changes color but does not change shape, stroke-width, or label weight.

---

### 2.4 algorithm-visualizer — Tracer-Based Annotation

#### Placement algorithm

algorithm-visualizer (https://algorithm-visualizer.org, GitHub:
`algorithm-visualizer/algorithm-visualizer`) uses a tracer model: algorithm authors
call tracer methods (e.g., `Array1DTracer`, `GraphTracer`, `LogTracer`) that emit
visualization commands. The React web app interprets commands and renders them.

Graph nodes are laid out using force-directed simulation. Node labels are placed at
node center (same model as VisuAlgo). Edge labels use a midpoint offset with fixed
perpendicular displacement (approximately half the edge stroke width × 4 px). No
collision detection for edge labels; the tracer specification has no `label_side` or
`label_offset` parameter.

Log output (`LogTracer`) renders algorithm state as text lines, which acts as a
supplementary label panel rather than inline annotations — a fundamentally different
model (labels are beside the visualization, not on top of it).

#### Code / doc reference

- Main repo: https://github.com/algorithm-visualizer/algorithm-visualizer
- Tracers JS: `algorithm-visualizer/tracers.js`  
  https://github.com/algorithm-visualizer/tracers.js

#### Pros for pedagogy

- Separation of algorithm logic and visualization label is clean. The `LogTracer`
  side panel avoids the label-over-data clash entirely by spatially separating state
  from the data structure.
- Force-directed node layout automatically avoids node-node occlusion; labels
  benefit indirectly.

#### Cons for pedagogy

- No annotation *on* edges or *between* cells. Inline annotation (e.g., "this is
  the minimum cut") is not a first-class feature.
- `LogTracer` text is generic; it has no semantic styling (no `warn`/`error`/`good`
  color tokens, no weighted font for emphasis).
- The tracer API surface area is small — authors cannot express "highlight this
  specific edge label in red and point to it with an arrow" without patching the
  renderer.

---

### 2.5 D3.js — forceCollide / D3-Labeler

#### Placement algorithm: d3-force with forceCollide

`d3.forceCollide(radius)` (`d3-force` module, https://d3js.org/d3-force/collide)
treats each element as a circle of configurable radius. On each tick:

1. For each node, compute anticipated position `(x + vx, y + vy)`.
2. Find all nodes whose circles overlap based on anticipated positions.
3. For each overlapping pair, modify velocity to push nodes apart.
4. Dampen velocity changes by `strength` (default 1.0) to blend simultaneous
   resolutions.

For **rectangular labels**, the community workaround (popularized by
`chrissardegna.com/blog/lessons-in-d3-labeling/`) uses:
- A force simulation with `forceCollide(labelHeight / 2)` (approximates rect as circle)
- Fixed `fx` property to lock horizontal position to the data point
- A `forceY(targetY)` attraction to prevent label from drifting arbitrarily far
- 300 ticks to reach stable placement

No directional bias: labels move wherever the velocity field pushes them. The `fx`
lock provides implicit x-axis stability but not a preferred half-plane.

#### Placement algorithm: D3-Labeler (simulated annealing)

`tinker10/D3-Labeler` (https://github.com/tinker10/D3-Labeler) uses simulated annealing.
The energy function penalizes: label-label overlap, label-anchor overlap, label-anchor
distance, leader line intersections, and poor orientation. Monte Carlo sweeps move or
rotate each label; the acceptance probability follows the Boltzmann criterion
`exp(-ΔE / T)`. Temperature decreases linearly. Users can inject custom energy functions.

```
ASCII: D3 forceCollide label model

  Data point •            • Data point
              ↘          ↗
           [label A]  [label B]  ← pushed apart by velocity fields
               ↕ attraction to targetY prevents runaway drift
```

#### Code / doc reference

- `d3-force` docs: https://d3js.org/d3-force/collide
- D3-Labeler: https://github.com/tinker10/D3-Labeler
- d3-bboxCollide (rect AABB): https://github.com/emeeks/d3-bboxCollide
- D3 labeling blog: https://chrissardegna.com/blog/lessons-in-d3-labeling/

#### Pros for pedagogy

- `forceCollide` is continuous and reactive — adding a new data point re-runs the
  simulation and all labels re-settle. Excellent for interactive tools.
- D3-Labeler's energy function explicitly penalizes **leader-line crossings** —
  a constraint scriba does not currently enforce.
- Energy-function extensibility allows domain-specific constraints (e.g., "labels
  must stay above the data point" for CS pedagogy tools).

#### Cons for pedagogy

- Non-deterministic in the annealing variant. The same input can produce different
  label layouts across renders — unsuitable for scriba's batch SVG guarantee.
- `forceCollide` approximates rectangles as circles; pill-shaped labels with variable
  aspect ratios accumulate systematic error.
- 300 ticks means real-time cost; for a batch SVG generator this is acceptable but
  disproportionate to the problem size.
- No built-in leader-line rendering — the library repositions labels; connecting lines
  must be drawn separately.

---

### 2.6 Gephi — Label Adjust

#### Placement algorithm

Gephi's **Label Adjust** plugin (`gephi.wordpress.com/2008/11/15/label-adjust/`) moves
*nodes* rather than labels to resolve label overlaps. The model:

1. After ForceAtlas2 (or any layout) stabilizes, run Label Adjust.
2. For each pair of nodes whose rendered label bounding boxes overlap, apply a
   small repulsive displacement to both nodes.
3. Repeat until no label AABB pairs overlap, or user stops manually.

Because nodes are moved, the entire graph topology shifts to accommodate legible labels.
This is a **label-inflate-then-relax** model: label legibility is treated as a first-class
layout constraint, not an afterthought.

#### Code / doc reference

- Gephi blog: https://gephi.wordpress.com/2008/11/15/label-adjust/
- ForceAtlas2 paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC4051631/
- Gephi GitHub: https://github.com/gephi/gephi

```
ASCII: Gephi Label Adjust

  Before:           After Label Adjust:
  [A][B]            [A]   [B]
  nodes overlap     nodes pushed apart to
  label bboxes      make room for labels
```

#### Pros for pedagogy

- Handles any label length. Long labels for named nodes (e.g., algorithm step names)
  get the space they need by moving nodes.
- Self-terminating: stops automatically when no overlaps remain.
- Works at graph scale (hundreds of nodes). Scriba rarely needs this but the model is
  proven correct.

#### Cons for pedagogy

- Moving nodes changes the graph's spatial semantics. For algorithm-step visualizations
  (where node position encodes algorithmic meaning, e.g., tree depth), moving nodes to
  accommodate labels is unacceptable.
- No directional bias. Labels can end up in any orientation relative to their nodes.
- No leader lines — the node itself moves, so the label is always adjacent.
- Not applicable to scriba: cell positions in array/DPTable primitives are fixed by
  data values and cannot be relocated.

---

### 2.7 matplotlib + adjustText — Force-Based Label Repulsion

#### Placement algorithm

`adjustText` (`github.com/Phlya/adjustText`) post-processes matplotlib label positions:

1. Initialize labels at their natural positions (data point coordinates).
2. Iterate until convergence or `max_iter` reached:
   a. **Text-text repulsion** (`force_text`): for each overlapping AABB pair, compute
      the minimum-axis shift vector and accumulate it as velocity.
   b. **Text-static-object repulsion** (`force_static`): same against fixed mark AABBs.
   c. **Anchor pull** (`force_pull`): attract each label back toward its original anchor.
      A `pull_threshold` (default 10 display units) suppresses pull when already close.
   d. **Explosion** (`force_explode`): large proportional repulsion for severe overlaps.
   e. Apply net force vector; update position.
3. Convergence: when accumulated `|shift|` across all labels drops to zero.
4. Draw leader lines (`FancyArrowPatch`) from adjusted text center to target point
   when distance exceeds `min_arrow_len` (default 5 display units).

The `only_move` parameter restricts axes: `{'x': 'x+', 'texts': 'y+'}` confines
labels to move right and up only.

Source: `adjustText/__init__.py` — `get_shifts_texts`, `pull_back`,
`iterate_to_convergence`.

```
ASCII: adjustText force model

   anchor •         anchor •
   ↑ pull_back      ↑ pull_back
   [label A] ←——→ [label B]
       force_text repulsion
```

#### Code / doc reference

- GitHub: https://github.com/Phlya/adjustText
- Docs: https://adjusttext.readthedocs.io/

#### Pros for pedagogy

- Pull-toward-anchor prevents labels from drifting far from their data points —
  the reader never loses the label-to-data correspondence.
- Static-object repulsion allows pre-registering chart elements (axes, titles) that
  labels should avoid — equivalent to what scriba needs for cell-text avoidance.
- `only_move` directional constraints enable half-plane enforcement (all labels above
  the data line).
- Leader lines are drawn automatically at a configurable distance threshold.

#### Cons for pedagogy

- Force parameters (`force_text`, `force_pull`, `force_static`) must be hand-tuned
  per figure — no universal defaults. Batch systems like scriba would need robust
  defaults or per-primitive tuning.
- Convergence is not guaranteed: cycles are possible if forces are balanced.
  `max_iter` acts as a hard cap with no quality guarantee at termination.
- Uses matplotlib's true glyph metrics. Scriba uses `estimate_text_width`, a
  character-count heuristic — force magnitudes calibrated for matplotlib would
  need re-derivation in pixel space.
- Leader lines terminate at label center, not label perimeter — same as scriba's
  known defect (§2.3 of the existing placement-algorithm audit).

---

### 2.8 CLRS Textbook Figures — Static Pedagogical Conventions

#### Placement algorithm

CLRS (*Introduction to Algorithms*, 4th ed., 2022) uses hand-crafted figures produced
with a combination of TikZ/LaTeX and pre-press illustration. There is no runtime
label-placement algorithm — every position is an editorial decision. The figures
establish a well-studied pedagogical convention set:

- **Array indices above cells, values inside**: index labels sit above cell boundaries
  as subscript-style superscripts, never inside or below.
- **Pointer arrows with explicit arrowheads** drawn at 45° or 90° angles; no curved
  bezier arrows unless the semantics require (BST rotation figures use curved arrows).
- **Shaded / colored cells** to indicate "active" elements; shading is combined with
  **bordered outline** so the figure reads in grayscale.
- **Step subfigures (a)–(f)** for multi-step algorithms; each subfigure is self-contained
  with its own labels, eliminating the "which frame does this label belong to?" ambiguity
  present in animated tools.
- **Bold / heavy-weight arrows** for the "critical path" or "current comparison"; normal
  arrows for structural edges. Stroke-width hierarchy is consistent throughout the book.
- **Captions carry semantic weight**: figures have descriptive captions that serve as
  the primary explanation; labels on the figure are *pointers*, not explanations.

#### Code / doc reference

No public source code. Published in MIT Press, 2022.  
Observation sources: Chapters 2 (sorting), 6 (heaps), 12 (BST), 22–24 (graphs),
15 (DP) — the DP chapter uses both matrix tables and recursion DAGs with edge labels.

```
ASCII: CLRS-style array annotation (Chapter 2, insertion sort)

    ↓ current
  ┌──┬──┬──┬──┬──┐
  │1 │3 │2 │5 │4 │   ← values inside
  └──┴──┴──┴──┴──┘
  [0] [1] [2] [3] [4]  ← indices above (superscript style)
   ↑
  shaded = sorted prefix
```

#### Pros for pedagogy

- Grayscale-safe by design. CLRS figures use shading patterns (diagonal lines, dots,
  solid gray) rather than color alone to distinguish element states. This is the gold
  standard for colorblind accessibility among algorithm textbooks.
- Stroke-width hierarchy (bold = important, normal = structural) is a non-color cue
  that survives photocopy and print.
- Subfigure decomposition eliminates temporal ambiguity in static media.
- Captions as primary carriers prevents the label-density problem — figures stay clean
  because textual explanation lives elsewhere.

#### Cons for pedagogy

- Static — no progressive disclosure, no animation.
- Every figure requires hours of editorial judgment. Not automatable.
- No leader lines in most figures — labels are placed close enough to their referents
  that lines are unnecessary, which is only possible because positions are hand-tuned.

---

### 2.9 Vega-label — Occupancy Bitmap FLP

#### Placement algorithm

`vega-label` (GitHub: `vega/vega-label`, https://github.com/vega/vega-label) implements
the algorithm from arXiv 2405.10953 ("Legible Label Layout for Data Visualization").

1. **Rasterize marks**: render all chart marks (data points, lines, areas, axis ticks)
   onto a 1D array of 32-bit integers representing an `(width × height)`-pixel bitmap.
   Each pixel belonging to any mark is set to 1.
2. **Candidate positions**: for each mark to label, generate 8 candidate positions
   (corners: NW, NE, SE, SW; midpoints: N, E, S, W) at a configurable `padding` offset
   from the mark's bounding box.
3. **Conflict check per candidate**: extract the label's AABB footprint from the bitmap
   using bitwise AND. The check operates on fully-covered 32-bit words (whole-row
   coverage) and applies bit-masks for partial-word boundary rows. Cost is O(w×h /
   32) ≈ O(1) for practical label sizes.
4. **Greedy first-fit**: first conflict-free candidate in fixed priority order wins.
5. **Mark used**: on placement, OR the label's footprint into the bitmap.
6. **No placement when all 8 collide**: that label is simply omitted.

Performance: 22% faster than prior art on a 3,320-airport map dataset (paper, §5.3).

```
ASCII: Vega-label bitmap model

  Bitmap:           Candidate NW check:
  ░░░░████░░░░      Extract subregion from bitmap
  ░░░░████░░░░   →  Bitwise AND with label footprint
  ░░░░████░░░░      Result=0: PLACE HERE
  ░░░░░░░░░░░░      Result≠0: try NE, N, E, ...
```

#### Code / doc reference

- Paper: https://arxiv.org/html/2405.10953  
- Source: https://github.com/vega/vega-label  
- Prior bitmap paper: https://idl.cs.washington.edu/files/2021-FastLabels-VIS.pdf

#### Pros for pedagogy

- Conflict resolution accounts for *all* marks (data points, lines, axes), not just
  previously placed labels. Scriba's current registry sees only pills; vega-label sees
  everything.
- O(1) conflict check independent of mark count — scales to dense Plane2D frames.
- Bitmap model is medium-independent: it would work equally well for scriba's SVG
  server-side generation if mark footprints are approximated analytically.

#### Cons for pedagogy

- **Labels are silently omitted** when all 8 candidates fail. In a CS pedagogy context,
  every `\annotate` call is author-intent — silent omission is unacceptable.
- No directional bias. The 8 fixed positions are tried in a fixed order with no half-
  plane preference; the paper reports no evidence that this order was evaluated against
  Imhof's cartographic preference ranking.
- No leader lines — the paper and source make no provision for callout connectors.
- Requires a rendering context to rasterize marks. Scriba generates SVG server-side;
  mark footprints would need to be approximated geometrically, not by actual rendering.

---

## 3. Cross-System Comparison Matrix

Rows = systems. Columns = seven key dimensions plus three scriba-specific angles.

| System | Directional bias | Leader threshold | Leader style | Colorblind cue | Occlusion rule | Hierarchy cue | Displacement fallback | Temporal coherence | Batch/interactive |
|--------|-----------------|-----------------|--------------|---------------|---------------|---------------|----------------------|-------------------|-------------------|
| **Scriba v0.10** | N > NE > NW first (side_hint); else Manhattan-distance order | `displacement > 30 px` (arrow only) | Dashed polyline; dot at arc anchor; terminates at pill center | WCAG AA contrast (all 6 tokens ≥ 4.5:1 at full opacity); font-weight hierarchy; no shape/pattern | Not enforced for plain arrow; bezier pill allowed over curve midpoint | `color` token (stroke-width, opacity, font-weight, font-size vary by token) | Keep last of 32 candidates regardless of overlap | None — fresh list per frame | Batch |
| **Manim** | Author-chosen direction arg to `next_to`; no default ordering | Never — no leader concept | None | None (color-only) | Not enforced | Stroke color; `Indicate` animation | None — overlaps silently | None — scene rebuilt | Batch (rendered) |
| **3Blue1Brown style** | Author judgment, strongly above-preferred | Explicit arrow MObject when needed | Solid `CurvedArrow` with tip; color-matched | None (color-only) | Author decides | Color-semantic (yellow = primary); `Indicate` / `Circumscribe` animation | Author resolves manually | None | Batch (video) |
| **VisuAlgo** | Node: center; Edge: `t=0.5` + fixed offset | Never | None | Node: grayscale fill; arrowheads for direction | N/A (inside node) | Color highlight only | None — overlap left in place | None | Interactive |
| **algorithm-visualizer** | Node: center; Edge: midpoint | Never (uses LogTracer side panel) | None | None | N/A (inside node) | Color highlight + animation timing | None — overlap left in place | None | Interactive |
| **D3 forceCollide** | No bias; fx locks x-axis | None (position only) | None built-in | None | Not applicable | None | Physics-stable last position | None (re-simulates) | Interactive |
| **D3-Labeler** | None (annealing random) | None explicit | None built-in | None | Not applicable | Energy-function extensible | Probabilistic last accepted position | None | Interactive |
| **Gephi Label Adjust** | None (node repositioned) | N/A (node moves to label) | None (no displacement) | Node shapes optional | N/A | ForceAtlas2 gravity (implicit) | Nodes moved until no overlaps | None | Interactive |
| **matplotlib / adjustText** | `only_move` param (e.g., `y+` for above-only) | `min_arrow_len = 5 units` | `FancyArrowPatch`; terminates at label center | None (matplotlib color) | Not enforced | matplotlib styling (line-width, color, alpha) | Bounded iteration fallback (last position at `max_iter`) | None | Batch |
| **CLRS textbook** | Above > beside > below (editorial preference) | None needed (hand-placed) | Solid line with arrowhead; terminates at glyph edge | Shading patterns + stroke-weight; no color reliance | Not applicable (hand-placed) | Stroke-weight: bold = critical, normal = structural | N/A (manual) | N/A | Static |
| **Vega-label FLP** | None (fixed 8-position order) | None | None | None | Bitmap occupancy = universal occlusion rule | Not addressed | Label omitted silently | None | Batch |
| **Graphviz xlabel** | Top-left of node bbox (default); hack to lower-left | N/A | None | None | No guarantee | Edge: `xlabel` vs `label` visual weight | Unchecked overlap acknowledged | None | Batch |
| **TikZ node[label=]** | Author-chosen cardinal/diagonal direction; `label distance` param | None | None | None | Not enforced | Font size, weight per `every label/.style` | Manual | N/A | Static |
| **Mapbox GL** | `text-variable-anchor` ordered list | N/A (cull, not move) | None | None | Bitmap spatial hash (30-px cells) | `sort-key` priority (higher = cull first) | Label culled (hidden) | `CrossTileSymbolIndex` fade | Interactive |
| **Observable Plot dodge** | 1D: minimum displacement from baseline | None | None | None | 1D interval-tree | Not applicable | Stack above/below (1D only) | None | Batch |

---

## 4. Patterns Observed — Recurring Best Practices

### Pattern 1: The "anchor pull" principle (adjustText, d3fc, Imhof cartography)

**Observation**: Every system that achieves readable dense layouts includes an explicit
force or constraint that pulls displaced labels *back toward* their natural anchor.
adjustText's `pull_back()`, d3fc's greedy minimum-overlap scoring, and Imhof's
"labels should be close to their point" rule all express the same invariant: displacement
is costly and must be bounded.

**Implication**: scriba's 32-candidate grid implicitly applies this by ordering candidates
by Manhattan distance, but has no fallback when all 32 are occupied. The "keep last
candidate" fallback violates this principle by accepting unbounded displacement.

### Pattern 2: Multi-channel encoding for colorblind accessibility (CLRS, WCAG 2.2)

**Observation**: Systems designed for print or export (CLRS, TikZ-based academic figures)
universally use **at least two independent visual channels** to distinguish element states.
CLRS uses shading pattern + border presence. TikZ academic diagrams use stroke-weight +
dash pattern. WCAG 2.2 SC 1.4.1 codifies this as a legal requirement: "color cannot be
the sole means of conveying information."

**Implication**: scriba's 6 color tokens (info, warn, good, error, muted, path) differ
primarily in color. Font-weight (`700` vs `500`) is the only secondary channel, and the
audit (`10-accessibility.md`) shows that `info` at 0.45 group opacity fails WCAG AA even
on the nominal contrast pass.

### Pattern 3: Stroke-weight hierarchy for important edges (CLRS, Manim, scriba)

**Observation**: CLRS uses bold strokes for the "current" comparison arrow and normal
strokes for structural edges. Manim uses `stroke_width` parameter variation. Scriba uses
`stroke_width` values of 2.5 (`path`), 2.2 (`good`), 1.2 (`muted`) — a 2:1 range is
present but not maximally exploited.

**Implication**: the stroke-weight channel is available and partially used. The gap
is that scriba does not allow author-specified stroke-weight overrides; it is locked
to the color-token table.

### Pattern 4: Parametric midpoint as the canonical edge-label anchor (CLRS, draw.io, scriba)

**Observation**: Across every system that places labels on edges — CLRS manual figures,
draw.io's `t=0.5` geometry, scriba's `label_ref_x/y` at the bezier midpoint — the
midpoint of the edge geometry is the universal default anchor. This is confirmed by
Imhof's principle: "labels should be adjacent to their features."

**Implication**: scriba is already aligned. The remaining gap is the leader-line endpoint
(currently pill center rather than pill perimeter), which all reviewed systems that have
leader lines implement differently.

### Pattern 5: Leader-line threshold as an explicit policy (adjustText, scriba)

**Observation**: Only two systems in the survey expose a configurable displacement
threshold for triggering a leader line: adjustText (`min_arrow_len=5`) and scriba
(`displacement > 30 px` hardcoded). All other systems either never draw leaders (Manim,
VisuAlgo) or always draw them (3Blue1Brown explicit-arrow style).

**Implication**: the threshold mechanism is rare and valuable. scriba's 30 px threshold
is reasonable but is a magic constant — it should be derived from `cell_height` or
`pill_h` to remain stable across different primitive scales.

### Pattern 6: First-fit greedy with distance ordering converges faster than annealing for low-density problems (PFLP survey, vega-label)

**Observation**: The canonical academic survey (Christensen et al., ACM ToG 1995)
established that greedy first-fit is adequate for ≤ 10 labels per frame and that
simulated annealing shows meaningful gains only above ~30 simultaneous labels. Vega-label
uses greedy first-fit. D3-Labeler's annealing provides non-deterministic output.

**Implication**: scriba's greedy 32-candidate search is algorithmically appropriate
for its typical workload (3–8 annotations per step). Annealing is not warranted unless
Plane2D scenes regularly exceed 30 simultaneous annotations.

### Pattern 7: Bitmap occupancy enables unified conflict detection across mark types (vega-label FLP)

**Observation**: The single largest qualitative gap between scriba and the state-of-
the-art (vega-label) is that vega-label treats *all marks* as occupancy — data points,
lines, axes, previously placed labels all occupy the same bitmap. Scriba's AABB registry
only registers pills. Cell text, grid lines, and value badges are invisible to the
registry.

**Implication**: even a partial bitmap (approximating cell text boxes and grid lines
as thin AABBs on a `bytearray` bitmap) would close bug-A and related issues in a single
mechanism without enumerating special cases per primitive.

---

## 5. Anti-Patterns Seen in the Wild

### Anti-pattern 1: Silent label omission when no candidate is free (vega-label, Graphviz xlabel)

Both vega-label and Graphviz's `xlabel` default to silently dropping labels that cannot
be placed. For a cartographic map, a missing city name is acceptable. For a CS pedagogy
tool, every `\annotate` call is author-intent — a missing label breaks the explanation.
Scriba correctly avoids this by always registering a placement, but at the cost of
accepting collision when all candidates are exhausted.

**Lesson**: choose between "always show, possibly overlapping" (scriba) and "sometimes
hide, never overlapping" (vega-label). Document the choice; do not make it silently.

### Anti-pattern 2: Color as the sole differentiator (VisuAlgo, algorithm-visualizer, 3Blue1Brown)

Three of the nine surveyed systems use color as the exclusive mechanism for
distinguishing element states (highlighted vs. normal, current vs. visited). None of
these systems pass simulated deuteranopia (red-green colorblindness, affecting ~8% of
males). CLRS — the only system designed for print — explicitly avoids this.

**Lesson**: every state distinction must be redundantly encoded in at least one
non-color channel (stroke-weight, dash pattern, shape, font-weight).

### Anti-pattern 3: Leader line terminating at label center, not label perimeter (adjustText, scriba)

Both adjustText (via `FancyArrowPatch` default) and scriba's `emit_arrow_svg` terminate
the leader line at the pill center (`fi_x, fi_y`), not the pill perimeter. This means
the leader visually pierces the label background, creating an ambiguous endpoint.
TikZ's arrow-clipping (`shorten_src`, `shorten_dst` via `shrinkA/shrinkB` in matplotlib)
and CLRS hand-placed arrows always terminate at the glyph edge.

**Lesson**: leader lines should be drawn from the curve anchor to the nearest point
on the pill perimeter, not to pill center. This requires computing the intersection of
the leader line direction with the pill rectangle before rendering.

### Anti-pattern 4: Magic-constant displacement thresholds (scriba, adjustText)

Scriba's `displacement > 30 px` and adjustText's `min_arrow_len = 5 units` are
absolute values calibrated at the time of writing. As viewport dimensions, font sizes,
and cell geometry change, these constants drift out of calibration. Mapbox GL's
`text-variable-anchor` list and TikZ's `label distance` parameter are both
scale-relative (expressed as fractions of the mark size or em-units).

**Lesson**: displacement thresholds should be expressed as multiples of `pill_h`,
`cell_height`, or `font_size`, not as fixed pixel values.

### Anti-pattern 5: No feedback when placement fails (scriba, Graphviz, VisuAlgo)

When scriba's 32 candidates are exhausted, it falls back silently to the last
candidate's position (an overlapping label) and emits only an HTML comment
`<!-- scriba:label-collision id=X -->` when `SCRIBA_DEBUG_LABELS=1`. No visible
warning is surfaced to the scriba author. Graphviz's documentation acknowledges
"It may not be possible to place all of them" but provides no runtime warning.

**Lesson**: when a label is placed in a degraded position (overlap unresolved), the
authoring tool should surface a visible warning — either in terminal output (a log
message) or in the rendered SVG itself (e.g., a red pill border).

---

## 6. Scriba Positioning — Strengths, Weaknesses, and Gaps

### 6.1 Where scriba is strong

| Strength | Evidence |
|----------|----------|
| WCAG AA contrast on all 6 tokens at full opacity | `10-accessibility.md` §1.2 |
| 32-candidate grid with distance-ordered nudge | `_svg_helpers.py` `_nudge_candidates` |
| Side-hint half-plane preference (N, NE, NW for `above`) | `_SIDE_HINT_PREFERRED` dict |
| Leader line at configurable displacement threshold | `displacement > 30 px` branch in `emit_arrow_svg` |
| Multi-line label wrapping with math-safe splitting | `_wrap_label_lines` + `$...$` guard |
| KaTeX inline math rendering in labels | `_emit_label_single_line` foreignObject path |
| Semantic color tokens with font-weight hierarchy | `ARROW_STYLES` dict + CSS custom props |
| Per-frame cross-annotation AABB registry | `placed_labels: list[_LabelPlacement]` |
| Debug label-collision comments (gated behind env var) | `SCRIBA_DEBUG_LABELS=1` |

### 6.2 Where scriba is weak (compared to peers)

| Weakness | Best-in-class peer | Gap |
|---------|--------------------|-----|
| Registry sees only pills — not cell text, grid lines, value badges | vega-label (bitmap sees all marks) | All non-pill marks are invisible to collision detection |
| Fallback when all 32 candidates fail is "keep last (overlapping)" | d3fc greedy (minimum-overlap scoring as fallback) | No graceful degradation path |
| Leader line terminates at pill center, not perimeter | CLRS hand-placed arrows, TikZ `shrinkB` | Visual ambiguity at leader endpoint |
| `displacement > 30 px` threshold is a magic pixel constant | TikZ `label distance` (em-based) | Drifts when cell height or font size changes |
| info token at 0.45 opacity fails WCAG AA (2.01:1 rendered) | No peer has this opacity-compositing bug | Active accessibility defect |
| No non-color cue for colorblind disambiguation of 6 tokens | CLRS (shading patterns + stroke-weight) | Color is currently the sole differentiator |
| No author-visible warning when placement degrades | None of the peers do this well | Silence fails fast authoring feedback |
| No anti-overlap constraint for leader paths crossing each other | D3-Labeler energy function penalizes leader crossings | Leader lines can cross in multi-annotation frames |

### 6.3 Gaps with no direct peer coverage

| Gap | Nature |
|----|--------|
| Temporal coherence across animation steps | All batch systems rebuild fresh — no peer covers this |
| Pill-on-dark-background opacity compositing WCAG compliance | None of the surveyed systems have opacity compositing with dark themes |
| Inline KaTeX label math — width estimation accuracy (1.15× heuristic) | No peer with equivalent constraint |

---

## 7. Recommendation: Adopt Patterns

The following six patterns are recommended for porting into scriba, ordered by estimated
implementation cost (ascending). Each entry covers: pattern name, source system,
rationale, and estimated cost.

### P1 — Relative displacement threshold

**Pattern**: express `displacement > 30 px` threshold as `displacement > 2.5 * pill_h`  
**Source**: TikZ `label distance` (em-based), adjustText (can be tuned per figure scale)  
**Rationale**: scriba's 30 px is calibrated for current default cell sizes (~24 px height,
~12 px font). If a primitive changes cell height (e.g., a larger DPTable cell), the 30 px
threshold becomes either too aggressive (leaders appear too early) or too passive (leaders
appear too late). A pill_h-relative threshold self-calibrates.  
**Files affected**: `emit_arrow_svg` in `_svg_helpers.py`, one constant change.  
**Estimated cost**: 1 hour (constant swap + parametric test update).

---

### P2 — Leader-line endpoint at pill perimeter, not pill center

**Pattern**: when drawing a leader (dashed polyline), compute the intersection of the
leader direction vector with the pill rectangle and terminate there, not at `(fi_x, fi_y)`.  
**Source**: CLRS hand-placed figures (all arrows terminate at glyph edge); TikZ
`shorten_dst` / `shrinkB` in `arrowprops`.  
**Rationale**: a leader terminating at pill center visually pierces the label text,
creating an ambiguous endpoint. Terminating at perimeter makes the leader a clear
"pointing at" visual signal.  
**Files affected**: `emit_arrow_svg` leader-line branch (approximately 8 lines).  
**Estimated cost**: 2 hours (geometry: line-rect intersection + test case).

---

### P3 — Minimum-overlap fallback when all 32 candidates are exhausted

**Pattern**: when `_nudge_candidates` exhausts all 32 slots with no conflict-free
position found, score each of the 32 candidates by total overlap area with the registry
and accept the one with minimum overlap rather than the "keep last" fallback.  
**Source**: d3fc-label-layout greedy strategy (minimum overlap area over placed labels).  
**Rationale**: the "keep last" fallback in scriba places the label in the last-tested
position regardless of how much it overlaps — typically at `1.5 × pill_h` in the SW
direction from natural, which may be worse than the initial natural position. The
minimum-overlap candidate is always at least as good as "keep last" and is often
significantly better.  
**Files affected**: `_nudge_candidates` (add scoring pass), `emit_arrow_svg` and
`emit_plain_arrow_svg` (pass scored fallback to _place_pill).  
**Estimated cost**: 4–6 hours (algorithm change + comprehensive test for overlapping
frames).

---

### P4 — Non-color secondary cue: dash pattern on leader lines per token

**Pattern**: differentiate annotation *leaders* (the dashed polyline) by dash pattern
per semantic token: `info` → `4 4` (short dashes), `warn` → `6 2` (long-short),
`error` → `2 2` (dotted), `good` → solid, `muted` → `8 4` (long dashes).  
**Source**: CLRS stroke-weight hierarchy; WCAG 2.2 SC 1.4.1 (color not sole means of
conveying information).  
**Rationale**: scriba's 6 tokens currently differ in color, stroke-width, font-weight,
and opacity — but *not* in a way that survives grayscale or colorblind simulation.
A dash-pattern channel is the lowest-overhead non-color differentiator that works in SVG
(`stroke-dasharray`). It does not require pixel-resolution changes.  
**Files affected**: `ARROW_STYLES` dict (add `leader_dasharray` key), `emit_arrow_svg`
leader-line `<line>` emission (~3 lines).  
**Estimated cost**: 4 hours (design 5 distinct patterns + verify they read differently
at scriba's typical scale + visual regression test).

---

### P5 — Pre-register non-pill mark AABBs (cell text + grid lines) before annotation loops

**Pattern**: before any annotation emission loop in each primitive's `emit_svg`, register
all cell-text bounding boxes and all grid-line segments as thin `_LabelPlacement` AABB
entries in the shared `placed_labels` list. Assign a `kind` field to distinguish
pill-AABB entries from pre-registered mark entries (so future code can filter them).  
**Source**: vega-label FLP (rasterizes all marks before placing any label); Mapbox GL
bitmap occupancy.  
**Rationale**: scriba's collision registry currently sees only pills. Bug-A ("pill lands
on a cell value"), bug-E ("dense Plane2D pills overlap value annotations"), and
related issues all stem from this blind spot. Pre-registering known-geometry marks
requires no algorithm change — `_nudge_candidates` already checks the full registry —
only callers need to populate it more fully.  
**Files affected**: `_LabelPlacement` dataclass (add `kind` field), each primitive's
`emit_svg` entry point (add pre-registration loop). Affected primitives: `array.py`,
`dptable.py`, `matrix.py`, `graph.py`, `tree.py`, `hashmap.py` (one method each).  
**Estimated cost**: 8–12 hours (dataclass field + 6 primitive emission entry points +
test coverage for each primitive).

---

### P6 — Author-visible degraded-placement warning

**Pattern**: when the collision registry exhausts all candidates for a label placement,
emit a `scriba:label-placement-degraded` warning to stderr (similar to existing
`E1199`-family IPC warnings) with the target identifier and the number of candidates
tried. This is independent of `SCRIBA_DEBUG_LABELS` and fires unconditionally.  
**Source**: No peer does this well — this pattern fills a gap across all surveyed systems.
Closest analogy: adjustText's convergence warning (`max_iter` reached) and matplotlib's
`UserWarning` mechanism.  
**Rationale**: silent degraded placement is the dominant failure mode for dense frames
in scriba. Authors currently have no feedback path unless they set `SCRIBA_DEBUG_LABELS=1`
and inspect HTML comments. A stderr warning surfaces the issue at build time, enabling
authors to reduce annotation density or override placement.  
**Files affected**: `_svg_helpers.py` collision-unresolved branch, scriba's warning
infrastructure (`animation/warnings.py`), `animation/errors.py` (new warning code).  
**Estimated cost**: 3–5 hours (warning infrastructure + test that warning fires on
forced-collision frame).

---

## Sources

- Manim Community `next_to` source: https://github.com/ManimCommunity/manim/blob/main/manim/mobject/mobject.py
- Manim `brace.py`: https://github.com/ManimCommunity/manim/blob/main/manim/mobject/svg/brace.py
- Manim Community docs: https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html
- 3Blue1Brown videos repo: https://github.com/3b1b/videos
- VisuAlgo graphds.html: https://github.com/jonathanirvings/VisuAlgo/blob/master/graphds.html
- algorithm-visualizer main: https://github.com/algorithm-visualizer/algorithm-visualizer
- tracers.js: https://github.com/algorithm-visualizer/tracers.js
- d3-force collide: https://d3js.org/d3-force/collide
- D3-Labeler: https://github.com/tinker10/D3-Labeler
- d3-bboxCollide: https://github.com/emeeks/d3-bboxCollide
- D3 labeling blog: https://chrissardegna.com/blog/lessons-in-d3-labeling/
- Gephi Label Adjust blog: https://gephi.wordpress.com/2008/11/15/label-adjust/
- ForceAtlas2 paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC4051631/
- adjustText source: https://github.com/Phlya/adjustText
- adjustText docs: https://adjusttext.readthedocs.io/
- Vega-label: https://github.com/vega/vega-label
- Vega-label paper arXiv 2405.10953: https://arxiv.org/html/2405.10953
- IEEE VIS 2021 bitmap paper: https://idl.cs.washington.edu/files/2021-FastLabels-VIS.pdf
- Graphviz xlabel docs: https://graphviz.org/docs/attrs/xlabel/
- Graphviz xlabel hack: https://petercorke.com/general/hacking-graphviz-dot-to-place-labels/
- TikZ shapes manual: https://tikz.dev/tikz-shapes
- Imhof 1975 (cartographic labeling): https://www.tandfonline.com/doi/abs/10.1559/152304075784313304
- Christensen et al. 1995 PFLP survey: https://dl.acm.org/doi/10.1145/212332.212334
- Perceptual label preference 2024: https://arxiv.org/html/2407.11996
- Wikipedia: automatic label placement: https://en.wikipedia.org/wiki/Label_placement
- Cytoscape.js issue #1626: https://github.com/cytoscape/cytoscape.js/issues/1626
- Observable Plot repo: https://github.com/observablehq/plot
- Accessible color sequences: https://arxiv.org/pdf/2107.02270
- WCAG SC 1.4.1: https://www.w3.org/WAI/WCAG21/Understanding/use-of-color.html
- Scriba placement algorithm audit: `docs/archive/smart-label-audit-2026-04-21/02-placement-algorithm.md`
- Scriba prior-art doc: `docs/archive/smart-label-ruleset-audit-2026-04-21/08-prior-art.md`
- Scriba accessibility audit: `docs/archive/smart-label-ruleset-audit-2026-04-21/10-accessibility.md`
