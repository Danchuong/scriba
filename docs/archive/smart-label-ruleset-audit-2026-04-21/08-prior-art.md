# Prior-Art Comparison: Smart-Label Placement

**Date**: 2026-04-21  
**Scope**: Scriba smart-label system vs. ten external label-placement systems  
**Audience**: MW-2 through MW-4 implementers  
**Status**: reference document — update when new external art is found

---

## 0. Executive Summary

Scriba's current algorithm (32-candidate grid nudge, pill-only AABB registry) is a
**greedy fixed-grid search with no spatial index**. It is correct for the shipped scope
but misses conflict classes (cell text, leader paths, decorations) and has no fallback
when all 32 candidates are occupied. This document surveys ten external systems, extracts
portable ideas, and recommends three concrete ports aligned with MW-2, MW-3, and MW-4.

---

## 1. Scriba Current State (Baseline)

### 1.1 Candidate generation

`_nudge_candidates` yields 32 offsets: 8 compass directions × 4 step sizes
`(0.25, 0.5, 1.0, 1.5) × pill_h`. The grid is square in pixel space (both axes use
`pill_h`-based sizing). When a `side_hint` is present, candidates in the matching
half-plane are emitted first; the other half-plane follows as fallback. The generator is
lazy (`Iterator`) so early exit is O(1) after the first conflict-free slot is found.

### 1.2 Conflict detection

Pure AABB list scan: `O(n)` per candidate × 32 candidates = `O(32n)` per label where
`n` is the number of previously placed labels. The registry stores only pill AABBs
(`_LabelPlacement` dataclass). Cell text, leader paths, grid lines, value badges, and
pills from sibling primitives are all invisible to the registry (§2.3 of the ruleset).

### 1.3 Objective function

Implicit: **minimize displacement from the natural anchor**. The first conflict-free
candidate that appears in Manhattan-distance order is accepted. There is no explicit
score; the sort key is distance-then-compass-priority, not a readability or aesthetics
function.

### 1.4 Temporal coherence

None. Each `emit_svg` call constructs a fresh `placed_labels` list. Pill positions are
not carried forward across animation steps. A label can legally teleport between frames.

### 1.5 Interaction mode

Scriba is a **batch SVG generator**. There is no runtime re-layout and no user
interaction. This simplifies constraints significantly: no fade animations, no
draggable labels, no viewport-change callbacks.

---

## 2. External Systems

### 2.1 Manim — `Mobject.next_to`

**What it does**  
Manim is 3Blue1Brown's Python animation library. `Text` and `Tex` mobjects are
themselves `Mobject` instances. To position them, authors call `label.next_to(target,
direction, buff=0.25)`. The method computes the AABB of the reference mobject, then
places the label so that a specific edge of the label touches a specific edge of the
reference at the given `buff` offset [1].

**Algorithm**  
Pure geometric offset: pick a compass direction (`UP`, `DOWN`, `LEFT`, `RIGHT`,
`UL`, `UR`, `DL`, `DR`), compute the reference AABB extreme point in that direction,
add `buff * unit_vector(direction)`, and align the label's opposing edge to that point.
There is **no collision avoidance**: if two labels share the same `next_to` call sites,
the author is responsible for choosing distinct directions. `arrange` and
`arrange_in_grid` lay out a list of mobjects linearly with spacing but do not detect
pairwise overlaps.

**Source / Docs**  
- `manim/mobject/mobject.py` — `next_to`, `arrange`, `arrange_in_grid` [2]  
- https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html

**What scriba could port**  
The `buff`-parameterized edge-offset model is identical to the `gap = max(4.0,
cell_height * 0.1)` calculation already in `emit_position_label_svg`. No net gain here.

**What does NOT apply**  
Manim operates in a continuous coordinate space with full-precision floats and OpenGL
rendering. Its mobject system handles font shaping via LaTeX + dvisvgm, so real glyph
metrics are available. Neither condition holds for scriba's pixel-approximate approach.
Manim has no temporal label-persistence model — each scene is rebuilt from scratch, same
as scriba.

---

### 2.2 d3fc-label-layout

**What it does**  
`@d3fc/d3fc-label-layout` is a D3 add-on providing three placement strategies for
axis annotations, scatter plot labels, and map overlays [3]. It operates on an array of
`{x, y, width, height}` rectangles and re-positions or removes them to reduce overlap.

**Algorithm**

*Greedy strategy*: processes labels in input order. For each label, evaluates a fixed
set of candidate positions (typically N, NE, E, SE, S, SW, W, NW offsets from the
anchor) and selects the candidate with the lowest total overlap area against already-
placed labels. Unlike scriba's "first conflict-free slot wins", this is a
**minimum-overlap selection**: even if no candidate is fully free, it picks the least-
bad one. Runs in O(k × n) per label where k is the candidate count.

*Simulated annealing strategy*: iterates `ceil(temperature / cooling)` times. Each
iteration picks a random label and moves it to a random candidate position. Accepts the
move if it improves total overlap; accepts it probabilistically (∝ exp(−ΔE / T))
otherwise. Temperature decreases each iteration. Finds globally better solutions than
greedy at the cost of non-determinism and longer runtime.

*Remove-overlaps strategy*: does not reposition; removes labels with the highest
overlap area iteratively until no overlaps remain. Useful when label density makes
placement impossible.

**Source / Docs**  
- https://github.com/d3fc/d3fc/blob/master/packages/d3fc-label-layout/README.md [3]  
- ColinEberhardt's original: https://github.com/ColinEberhardt/d3fc-label-layout

**What scriba could port**  
The **minimum-overlap greedy** selection (MW-4 fallback): when all 32 grid candidates
are occupied, rather than keeping the last candidate, score each by total overlap area
with the registry and accept the minimum. This costs O(32 × n) but eliminates the
"all-exhausted" failure mode gracefully. No randomness, fully deterministic.

**What does NOT apply**  
The simulated annealing strategy produces non-deterministic output, which violates
scriba's batch-rendering guarantee that the same input always yields the same SVG.
The remove-overlaps strategy would silently drop annotation pills — unacceptable for a
math/CS pedagogy tool where every annotation is semantically meaningful.

---

### 2.3 matplotlib adjustText

**What it does**  
`adjustText` (https://github.com/Phlya/adjustText) is a Python library that post-
processes matplotlib label positions by iteratively applying virtual forces until labels
stop overlapping or a maximum iteration count is reached [4]. It is inspired by the
R `ggrepel` package.

**Algorithm**  
The main loop runs up to `max_iter` iterations. Each iteration:

1. For every text-to-text pair that overlaps (AABB intersection), apply a repulsion
   force `force_text` proportional to the overlap area vector, moving each text away
   from the other.
2. For every text-to-static-object pair (data points, line segments) that overlaps,
   apply `force_static` repulsion.
3. Apply `force_pull` attraction toward the original anchor position to prevent labels
   from drifting arbitrarily far.
4. Apply `force_explode` for extreme overlaps (large area fraction).
5. After movement, re-check bounding boxes. If total overlap is zero (or below
   tolerance), converge early.

Forces are 2D vectors accumulated per label; the label position is updated once per
iteration by the net force vector. After convergence, leader lines are drawn from
each label to its original anchor.

**Source / Docs**  
- https://github.com/Phlya/adjustText  
- https://adjusttext.readthedocs.io/

**What scriba could port**  
The **force-pull-toward-anchor** term (MW-4): scriba's current fallback when 32
candidates are exhausted keeps the last candidate regardless of how bad it is. Adding
an attraction term (after a grid-based initial placement) would allow the solver to
escape the 32-candidate grid while still gravitating toward the natural anchor,
avoiding arbitrary drift. The `force_text` repulsion from every registry AABB is
directly analogous to what §6 MW-4 calls "spring repulsion from every registry AABB".

The **convergence-early-on-zero-overlap** criterion is directly portable as the
termination condition for the MW-4 bounded solver.

**What does NOT apply**  
adjustText uses matplotlib's true glyph metrics for bounding box calculations.
Scriba uses an approximate character-count estimator (`estimate_text_width`). The force
magnitudes in adjustText are calibrated to matplotlib's coordinate system (data units,
not pixels), so the specific parameter values (`force_text=0.1`, etc.) cannot be
imported directly — scriba would need to re-tune in pixel space. The leader-line
rendering in adjustText is a matplotlib post-process; scriba already renders leaders as
SVG polylines (the `displacement > 30` branch in `emit_arrow_svg`).

---

### 2.4 Observable Plot — `Plot.dodge`

**What it does**  
Observable Plot's `dodgeX`/`dodgeY` transforms produce beeswarm-style layouts by
placing marks sequentially along one axis while preserving the other [5]. `Plot.text`
with a dodge transform can be used for de-cluttered scatter labels.

**Algorithm**  
Sequential greedy placement using a **1D interval tree** (Mikola Lysenko's
`interval-tree-1d`) for O(log n + k) intersection queries. Each dot/label is placed at
the minimum displacement from the baseline that avoids all previously-placed items.
Because the dodge dimension is constrained to one axis, the search is 1D: find the
lowest free slot above (or below) the current stack. Order-dependent: input sort order
controls visual density.

**Source / Docs**  
- https://observablehq.com/plot/transforms/dodge  
- GitHub: https://github.com/observablehq/plot (src/transforms/dodge.js)

**What scriba could port**  
The **1D interval-tree search** for `emit_position_label_svg` on arrays/DPTables:
when all labels for a horizontal array are being placed (all above or all below),
the problem collapses to 1D bin-packing along the x-axis. An interval tree would
reduce the per-label conflict check from O(n) list scan to O(log n + k) where k is
the number of actual conflicts. At the typical annotation count of 3–8 labels per
frame, the O(n) scan is adequate, but this becomes relevant for dense Plane2D scenes
(bug-E, 20+ annotation points).

**What does NOT apply**  
The dodge transform is strictly 1D — it cannot handle the 2D placement problem that
arises when labels sit on curves (bezier arrows) or have mixed above/below/left/right
placement. For scriba's general case, a 2D solution is required. The dodge transform
also assumes uniform item sizes; scriba pills have variable widths (math vs. plain text)
and heights (multi-line wrapping).

---

### 2.5 Vega-label — Bitmap Occupancy (FLP)

**What it does**  
`vega-label` (now at `vega/packages/vega-label`) implements the algorithm described in
"Legible Label Layout for Data Visualization" (arXiv 2405.10953) [6] and the earlier
"Fast and Flexible Overlap Detection for Chart Labeling with Occupancy Bitmap" (IEEE
VIS 2021) [7]. The core innovation is replacing per-element AABB comparisons with a
**rasterized occupancy bitmap**.

**Algorithm**

1. *Rasterize marks*: Before any label is placed, render all chart marks (points, lines,
   areas, axes) onto a 2D boolean bitmap at screen resolution. Each pixel that
   belongs to a mark is set to 1.
2. *Candidate positions*: For each mark to be labeled, generate up to 8 candidate
   positions (NW, N, NE, E, SE, S, SW, W) at a configurable offset radius. For
   stacked-area labels, search the area interior for the largest rectangle matching
   the label's aspect ratio.
3. *Conflict check*: For each candidate, compute the label's AABB in pixel space,
   extract the corresponding bitmap subregion, and perform a bitwise AND against 0.
   If the AND is zero, the position is free. This is O(w×h/word_size) ≈ O(1) for
   practical label sizes, independent of mark count.
4. *Mark used*: On placement, OR the label's footprint into the bitmap.
5. *Greedy first-fit*: Candidates are tried in a fixed priority order; the first free
   one wins.

**Performance**: The bitmap approach was reported as 22% faster than the prior particle-
based labeling on a 3,320-airport map while placing a similar number of labels.

**Source / Docs**  
- Paper: https://arxiv.org/abs/2405.10953  
- Source: https://github.com/vega/vega/tree/main/packages/vega-label  
- LabelPlacer.js: uses `bm0` (exterior) and `bm1` (interior) bitmaps with
  `searchOutOfBound` and `markInRangeScaled` primitives  
- Earlier paper: https://idl.cs.washington.edu/files/2021-FastLabels-VIS.pdf

**What scriba could port**  
The **bitmap occupancy model** is the single most impactful upgrade available for MW-2.
Instead of registering only pill AABBs, scriba could rasterize cell text, grid lines,
axis tick labels, value badges, and leader paths onto a shared bitmap before any pill is
placed. Each `_nudge_candidates` check becomes a bitmap AND rather than a list scan.
This would close bug-A (pill landing on "15" cell value) in a single unified mechanism
without needing separate registry kinds.

A minimal MVP: encode the bitmap as a Python `bytearray` with 1 bit per pixel. At a
typical scriba SVG width of 640 px and height of 480 px, the bitmap is 640×480/8 =
38,400 bytes — well within memory budget. Bitwise AND over a 24×18-px pill region
operates on roughly 54 bytes with 64-bit words.

**What does NOT apply**  
The full vega-label implementation rasterizes SVG/Canvas marks at runtime using the
browser's 2D canvas API. Scriba generates SVG server-side in Python without a rendering
context, so it cannot rasterize marks directly. It would need to approximate mark AABBs
geometrically (e.g., cell bounding boxes from known grid geometry, leader bezier
bounding boxes computed analytically) and paint those approximations onto the bitmap.
This is achievable but requires each primitive to expose its mark footprints.

---

### 2.6 Graphviz — `xlabel` External Label Routing

**What it does**  
Graphviz's `xlabel` attribute places an external label for a node or edge after all
nodes and edges are laid out. The placer attempts to find a position that does not
overlap existing nodes or edge routes [8].

**Algorithm**  
Post-layout scan: after `dot`/`neato` assigns node and edge coordinates, a second pass
iterates over all xlabels. For each, it tests a small set of candidate positions (by
default top-left of the node bounding box) and moves the label if it collides with a
node. The implementation is heuristic: `forcelabels=true` disables the collision check
entirely and always places at the default position. The `xlp` attribute allows manual
override of the final position in points.

There is no formal scoring function. Collision detection uses node bounding boxes only —
it does not avoid overlapping edge paths. As the Graphviz documentation notes: "It may
not be possible to place all of them." [8]

**Source / Docs**  
- https://graphviz.org/docs/attrs/xlabel/  
- Community hack for custom placement: https://petercorke.com/general/hacking-graphviz-dot-to-place-labels/

**What scriba could port**  
The **post-layout placement pass** concept is directly analogous to what scriba already
does: annotation pills are placed after the primitive geometry is fully computed. No
algorithmic port is needed; the architecture is already aligned. The lesson from
Graphviz is cautionary: without a richer conflict model (edges, not just nodes), xlabel
placement remains incomplete. Scriba's §2.3 blind spots are the same failure mode.

**What does NOT apply**  
Graphviz's `xlabel` operates on a global graph coordinate space with physical units
(inches/points). Scriba operates on per-primitive SVG pixel space. The Graphviz
placement code is in C and requires recompilation to modify. None of the source is
portable.

---

### 2.7 Cytoscape.js — Layout-Integrated Label Avoidance

**What it does**  
Cytoscape.js is a JavaScript graph visualization library. Label collision avoidance is
not a first-class feature of the core library; it is delegated to layout algorithms
(ELK, Klay, Cola) via the `nodeDimensionsIncludeLabels` boolean option [9].

**Algorithm**  
When `nodeDimensionsIncludeLabels: true`, each layout algorithm inflates the node
bounding box to include the label text extent before running its overlap-avoidance
pass. This is the **label-inflate-then-layout** model: labels never have independent
placement; they are treated as part of the node. Edge label collisions are not handled:
there is no built-in avoidance for labels on edges or for label-to-label conflicts when
multiple nodes are close.

**Source / Docs**  
- https://js.cytoscape.org  
- ELK adapter: https://github.com/cytoscape/cytoscape.js-elk  
- Issue #1626 (nodeDimensionsIncludeLabels discussion): https://github.com/cytoscape/cytoscape.js/issues/1626

**What scriba could port**  
The **node-inflate model** is implicitly what scriba does for its `arrow_height_above`
and `position_label_height_above/below` helpers: the viewBox is expanded to accommodate
labels before layout. This is the correct approach for primitives where the label is
anchored above/below the data structure and the data structure geometry is fixed. No
additional port needed — scriba already applies this pattern.

**What does NOT apply**  
Cytoscape.js graph layouts are iterative force-directed or constraint solvers that
can reposition nodes. Scriba's primitive geometry is immutable once computed (cell
positions are fixed by data values and grid geometry). Edge labels (bezier annotation
leaders) are the harder problem, and Cytoscape.js does not solve it either.

---

### 2.8 Mapbox GL — Priority-Based Cartographic Culling

**What it does**  
Mapbox GL's symbol layout engine processes hundreds of place name labels and icons at
runtime across multiple zoom levels and rotation states [10]. It uses a priority-based
culling model: labels are tried in importance order; a label that cannot be placed is
hidden (opacity animated to zero), not repositioned.

**Algorithm**

1. Assign a `sort-key` to each symbol feature; lower values have higher priority.
2. Process features in ascending sort-key order.
3. For each symbol, compute its bounding geometry: a rectangle for point labels
   (viewport-aligned), collision circles for line-following labels (rotation-invariant).
4. Query a `GridIndex` (a 30-px-cell 2D spatial hash) for existing occupied regions.
5. If the query returns no conflicts, insert the bounding geometry and mark visible;
   otherwise, mark collided (hidden). No repositioning.
6. The `CrossTileSymbolIndex` assigns stable identifiers to symbols across tile
   boundaries so fade transitions are smooth across zoom changes.

**Source / Docs**  
- https://github.com/mapbox/mapbox-gl-native/wiki/Collision-Detection  
- text-variable-anchor layout property (variable placement): https://docs.mapbox.com/style-spec/reference/layers/

**What scriba could port**  
The **GridIndex spatial hash** for conflict detection (MW-3/MW-4): at typical scriba
label counts (≤ 10 per frame) a 30-px-cell grid offers no advantage over the current
O(n) list scan. However, for dense Plane2D frames with 20–40 labeled points (bug-E),
a GridIndex would reduce per-candidate conflict checks from O(n) to O(1) amortized.
A Python implementation: divide the SVG canvas into a dict keyed by `(cell_x, cell_y)`
tuples; each placed AABB is recorded in all cells it touches; lookup returns only
nearby candidates.

The **variable-anchor list** concept from Mapbox's `text-variable-anchor` property
is directly applicable to MW-3's planned `_place_pill` helper: instead of a fixed
8-direction nudge grid, the helper could accept a priority-ordered list of explicit
anchor positions (e.g., `["above", "right", "below", "left"]`) per annotation, letting
primitive authors control the preferred half-plane declaratively.

**What does NOT apply**  
Mapbox GL culls rather than repositions. This is optimal for cartographic labels
where a missing city name is acceptable, but scriba annotation pills must appear
(every `\annotate` call is author-intent). The fade-animation model requires a
runtime DOM; scriba produces static SVG. The CrossTileSymbolIndex is irrelevant
(scriba has no tiles or zoom levels).

---

### 2.9 draw.io / tldraw — Connector Label Floating

**What it does**  
draw.io places labels on connectors at three parametric positions: source end, midpoint,
and destination end. Labels are attached to a connector's arc via a `geometry.offset`
relative to the parametric midpoint [11]. tldraw uses a similar model: edge labels live
at a normalized `t` parameter along the edge path.

**Algorithm**  
No collision avoidance algorithm. Labels are positioned deterministically at
`t = 0, 0.5, 1.0` unless the user drags the "yellow diamond" handle to reposition them.
Moving the connector moves all attached labels rigidly. There is no automatic avoidance
of node overlap or label-to-label conflicts.

**Source / Docs**  
- https://www.drawio.com/doc/faq/position-labels  
- draw.io connector label drag: https://drawio-app.com/blog/add-and-rotate-connector-labels/

**What scriba could port**  
The **parametric midpoint anchor** model (already in scriba): `label_ref_x / label_ref_y`
in `emit_arrow_svg` is computed as the Bezier midpoint + perpendicular offset, which is
precisely the draw.io `t=0.5` model. No port needed. The lesson from draw.io: the
midpoint anchor is the right default; users who need different positions must configure
it (scriba's `side` hint). The draw.io architecture confirms scriba's choice.

**What does NOT apply**  
draw.io and tldraw are interactive editors. Their label positioning relies on user
drag-to-resolve for collisions. Scriba is a batch generator with no user interaction;
automatic avoidance is mandatory.

---

### 2.10 Academic: Cartographic and Graph Label Placement

#### 2.10.1 Imhof's Cartographic Rules (1962 / 1975)

Eduard Imhof established the foundational rules for point-feature label placement in
cartography [12]. His 5-position model for left-to-right languages ranked positions:

| Priority | Position | Rationale |
|----------|----------|-----------|
| 1 (best) | Top-Right (TR) | Latin ascenders more common than descenders; right preserves left-to-right reading flow |
| 2 | Right (R) | Close to point, clear of the symbol |
| 3 | Top (T) | Above the point |
| 4 | Bottom (B) | Below the point |
| 5 (worst) | Left (L) | Reads against Western text direction |

A 2024 perceptual study (arXiv 2407.11996) found that modern users actually prefer
Top > Bottom > Right, with Top-Right ranking only fourth — suggesting Imhof's
typographic rationale does not fully predict perceived readability [13]. Both studies
agree that diagonal positions (NW, SW) are lowest priority.

**Scriba mapping**: scriba's `_SIDE_HINT_PREFERRED["above"] = (0, 4, 5)` (N, NE, NW)
aligns with Imhof's observation that upward positions are preferred. The tie-break order
N > NE > NW is consistent with the perceptual-study finding that pure Top outranks
diagonal Top-Right in user preference. The current compass priority already embeds
Imhof's insight without explicitly citing it.

#### 2.10.2 Point-Feature Label Placement (PFLP) Survey

The canonical empirical survey (Christensen et al., 1995, ACM ToG) compared six
algorithms including exhaustive search, gradient descent, and simulated annealing on
the 4-position and 8-position candidate models [14]. Key findings:

- **Simulated annealing** consistently outperformed greedy across high-density problems
  (more labels placed without overlap).
- **Greedy fixed-order** is adequate for low-density cases (≤ 10 labels per frame),
  which covers scriba's typical workload.
- The **8-position model** (N, NE, E, SE, S, SW, W, NW) is the consensus standard;
  4-position is faster but misses solutions the 8-position finds.
- **Step size matters**: candidates at multiples of the label height (the "Hirsch
  ladder") work better than fixed-pixel offsets because label sizes vary.

**Scriba mapping**: scriba's 32-candidate grid (8 directions × 4 steps) is the PFLP
8-position model with 4 step sizes, which matches the literature recommendation. The
step sizes `(0.25, 0.5, 1.0, 1.5) × pill_h` implement the "Hirsch ladder" principle.
The algorithm is well-calibrated for the density it faces.

**Source / Docs**  
- Imhof 1975: https://www.tandfonline.com/doi/abs/10.1559/152304075784313304  
- Christensen et al. 1995: https://dl.acm.org/doi/10.1145/212332.212334  
- Perceptual study 2024: https://arxiv.org/html/2407.11996  
- Wikipedia survey: https://en.wikipedia.org/wiki/Automatic_label_placement

#### 2.10.3 Sugiyama Algorithm — Layered Graph Label Placement

The Sugiyama method for hierarchical graph drawing assigns nodes to horizontal layers,
minimizes edge crossings, then assigns coordinates [15]. Edge labels are placed at
parametric positions (source, center, or target) along the routed edge, with the label
treated as a pseudo-node occupying space in the layout.

**Scriba mapping**: scriba's `arrow_index` stagger (`total_offset + arrow_index *
cell_height * 0.3`) is a simplified version of the Sugiyama pseudo-node approach:
multiple arrows targeting the same cell are vertically staggered so their bezier peaks
do not overlap. The Sugiyama insight — treat labels as layout constraints, not
afterthoughts — is already implicit in scriba's design but incompletely implemented
(the label AABB is registered after placement, not fed back into the bezier geometry).

---

## 3. Comparative Analysis

### 3.1 Candidate Generation

| System | Method | Count / Cost |
|--------|--------|--------------|
| Scriba (current) | 8-compass × 4 steps fixed grid | 32 candidates, O(1) to generate |
| d3fc-label-layout greedy | N/NE/E/SE/S/SW/W/NW offsets | 8 positions, user-configurable |
| d3fc-label-layout annealing | Random candidate per iteration | O(T/cooling) iterations |
| vega-label FLP | 8 positions around anchor AABB | 8 candidates (+ area interior search) |
| Observable Plot dodge | 1D greedy stack | 1 dimension only |
| Mapbox GL variable-anchor | Explicit ordered anchor list | User-defined, ≤ 10 positions |
| Imhof/PFLP academic | 4-position or 8-position model | 4 or 8 positions |

Scriba's 32-candidate count is higher than the 8-position academic standard. The extra
coverage (4 step sizes) is warranted given that scriba labels have variable pill heights
and the 1.5× step is the critical escape distance for a dense frame.

### 3.2 Conflict Detection

| System | Method | Complexity per query |
|--------|--------|---------------------|
| Scriba (current) | AABB list scan, pill-only | O(n) |
| d3fc-label-layout | AABB overlap area accumulation | O(n) |
| adjustText | Bounding box intersection per pair | O(n²) per iteration |
| vega-label FLP | Bitmap AND over label footprint | O(w×h / word_size) ≈ O(1) |
| Observable Plot dodge | 1D interval tree | O(log n + k) |
| Mapbox GL | 2D spatial hash (30-px cells) | O(1) amortized |

Scriba's O(n) list scan is adequate for n ≤ 10. At n ≈ 20–40 (dense Plane2D),
the bitmap model (vega-label) or spatial hash (Mapbox) would reduce total conflict-
detection time from O(32 × 40) = 1280 comparisons to near-constant.

### 3.3 Objective Function

| System | Objective |
|--------|-----------|
| Scriba (current) | Implicit: minimize displacement (first conflict-free in distance order) |
| d3fc greedy | Minimize total overlap area over already-placed labels |
| d3fc annealing | Minimize global total overlap (simulated annealing energy) |
| adjustText | Minimize per-label overlap area + maximize proximity to anchor |
| vega-label FLP | First-fit greedy in fixed priority order |
| Mapbox GL | Priority: higher-importance labels always win; no score for second-choice positions |
| Imhof | Maximize aesthetic quality (preference-ordered positions) |

Scriba's implicit objective (minimize displacement) aligns with vega-label's greedy
first-fit but lacks the overlap-area scoring of d3fc greedy. When all 32 candidates are
occupied, scriba has no scoring fallback — it keeps the last candidate regardless of
how badly it overlaps. Adding a minimum-overlap selection as the 33rd candidate (the
d3fc greedy model) would close this gap.

### 3.4 Temporal Coherence

| System | Temporal model |
|--------|---------------|
| Scriba (current) | None — fresh list per emit_svg call |
| Manim | None — scene rebuilt per frame (same as scriba) |
| adjustText | None — stateless per plot render |
| Mapbox GL | CrossTileSymbolIndex for fade transitions across zoom changes |
| d3fc-label-layout | None — stateless |

Scriba is batch, not real-time. Temporal coherence is listed as out-of-scope in §6.
No external system provides a portable model for this because scriba's step-by-step
animation model is unique: each step is a standalone SVG, not a frame in a video.
If temporal coherence is ever desired, the approach would be: after placing labels in
step N, serialize their positions as a bias map; in step N+1, score candidates by
proximity to the step-N position and apply a stability reward before the distance
sort. This is novel work, not borrowed from existing systems.

### 3.5 Interactive vs. Batch

All surveyed systems except Mapbox GL and Cytoscape.js are batch in practice (plot
re-rendered from scratch). Scriba's batch nature is not a limitation relative to peers;
it is a simplification that removes the need for incremental updates, animation
callbacks, and viewport-change handlers.

---

## 4. Recommended Ports

### Port 1 (MW-2): Extend the registry to a typed occupancy list with cell-text and leader-path entries

**Based on**: vega-label FLP (§2.5) — specifically the concept of rasterizing all
marks before placing any label.

**What to implement**:

1. Introduce a `kind` field on `_LabelPlacement`:
   ```python
   @dataclass(slots=True)
   class _LabelPlacement:
       x: float; y: float; width: float; height: float
       kind: str = "pill"  # "pill" | "cell_text" | "leader_path" | "decoration"
   ```
2. Before any annotation loop in a primitive's `emit_svg`, register all cell-text
   AABBs (DPTable: every `(col, row)` value badge; Array: every value text box) and
   all grid-line segments as thin AABBs (height = stroke_width + 2 px padding).
3. `_nudge_candidates` already ignores `kind`; the change is purely in what callers
   pre-register. No algorithm change needed.
4. Add `placed_labels: list[_LabelPlacement]` initialization with pre-populated
   non-pill entries to the primitive's `emit_svg` entry point.

**Expected outcome**: closes bug-A (pill landing on "15" cell value) and bug-E/F
(Plane2D labels missing or truncated). The typed `kind` field enables future
filtering (e.g., pill-to-pill repulsion heavier than pill-to-cell repulsion).

**Effort**: 2–3 hours per primitive. Requires updating DPTable, Array, and Plane2D.
No change to the nudge algorithm.

**Does NOT require**: a full bitmap rasterizer. Simple geometric AABB approximations
for cell text are sufficient for the scriba use case (cell geometry is known exactly
from grid parameters).

---

### Port 2 (MW-3): Unify pill placement into a single `_place_pill` function with variable-anchor list support

**Based on**: Mapbox GL `text-variable-anchor` (§2.8) + d3fc-label-layout's strategy
interface (§2.2).

**What to implement**:

Refactor the duplicated placement logic in `emit_arrow_svg`, `emit_plain_arrow_svg`,
and `emit_position_label_svg` into a single function:

```python
def _place_pill(
    natural_x: float,
    natural_y: float,
    pill_w: float,
    pill_h: float,
    l_font_px: float,
    placed_labels: list[_LabelPlacement],
    anchor_order: list[str] | None = None,  # NEW: e.g. ["above","right","below","left"]
) -> _LabelPlacement:
    ...
```

`anchor_order` maps to the existing `_SIDE_HINT_PREFERRED` table but as an ordered
preference list rather than a single hint. The function tries `_nudge_candidates` with
each anchor's preferred half-plane in the declared order before falling back to
omnidirectional search.

This is the Mapbox `text-variable-anchor` concept: the caller declares a priority-
ordered list of acceptable anchor positions; the placer tries them in order, committing
to the first conflict-free one.

**Expected outcome**: eliminates the ~90-line placement block duplicated across three
emit functions. Makes adding Plane2D support in MW-2 a one-line call to `_place_pill`
rather than another copy of the block. Prerequisite for MW-4 solver hook.

**Effort**: 1–2 hours refactor + test update. No behavior change; pure deduplication
with the variable-anchor-list extension as additive surface.

---

### Port 3 (MW-4): Add a minimum-overlap fallback for the all-candidates-exhausted case

**Based on**: d3fc-label-layout greedy minimum-overlap selection (§2.2) + adjustText
anchor-attraction term (§2.3).

**What to implement**:

When all 32 `_nudge_candidates` are occupied (the `collision_unresolved = True` path),
instead of keeping the last candidate:

1. Score each of the 32 candidates by `total_overlap_area(candidate, placed_labels)`.
   For each candidate, sum `overlap_rect_area(candidate, p)` for all `p` in
   `placed_labels`.
2. Accept the candidate with the minimum total overlap (ties broken by Manhattan
   distance to natural anchor — the adjustText attraction term).
3. Emit the debug comment as today, but include the winning overlap score for
   diagnostic visibility.

No simulated annealing, no force iteration — just a deterministic argmin over the
existing 32 candidates. This is O(32 × n) worst-case which at n ≤ 40 is 1,280
comparisons — negligible.

**Expected outcome**: eliminates the "all-exhausted" silent failure for dense scenes.
The least-bad position is always selected and logged; the debug comment reports its
overlap score so authors can identify when a scene genuinely needs a manual `side`
hint.

**Effort**: ~1 hour. Add `_overlap_area(a, b)` helper. Replace `collision_unresolved`
keep-last with argmin selection inside `_place_pill` (after Port 2 refactor).

**Does NOT require**: a force-directed solver. The bounded force-based solver
described in §6 MW-4 of the ruleset can still be added later, but the minimum-overlap
argmin is a standalone improvement that closes the worst failure mode immediately.

---

## 5. What Scriba Should Not Port

| Feature | Source | Why Not |
|---------|--------|---------|
| Simulated annealing | d3fc, PFLP | Non-deterministic; violates batch-render idempotency requirement |
| Remove-overlaps strategy | d3fc | Silently drops annotation pills; every `\annotate` must render |
| Runtime bitmap rasterization | vega-label FLP | Requires canvas/rendering context; scriba generates SVG in Python without one |
| Fade/transition animation | Mapbox GL | Static SVG output; no DOM runtime |
| Cross-tile label persistence | Mapbox GL | No tile boundaries; single-SVG-per-step model |
| Node-inflate-then-layout | Cytoscape.js | Primitive geometry is immutable post-computation; label positions cannot influence grid layout |
| Force-directed full solver | adjustText | Unnecessary for n ≤ 40; over-engineering relative to the quality improvement. Reserve for MW-4 if argmin fallback proves insufficient. |
| Real glyph metrics | Manim, adjustText | Requires font shaping (dvisvgm or HarfBuzz); scriba uses approximate estimator by design |
| User-drag resolution | draw.io, tldraw | Batch generator; no interactive session |

---

## 6. Citations

[1] Manim Community. "Mobject.next_to." Manim Community Documentation, v0.20.1.
    https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html

[2] Manim Community. Source code: `manim/mobject/mobject.py`.
    https://github.com/ManimCommunity/manim/blob/main/manim/mobject/mobject.py

[3] Eberhardt, Colin; d3fc contributors. "d3fc-label-layout README."
    https://github.com/d3fc/d3fc/blob/master/packages/d3fc-label-layout/README.md

[4] Flyamer, Ilya M. "adjustText: A small library for automatical adjustment of text
    position in matplotlib plots to minimize overlaps." GitHub.
    https://github.com/Phlya/adjustText
    Documentation: https://adjusttext.readthedocs.io/

[5] Observable Plot. "Dodge Transform." Observable HQ.
    https://observablehq.com/plot/transforms/dodge

[6] Borik, Chanwut; Hu, Kanit; Vo, Dominik; Heer, Jeffrey. "Legible Label Layout for
    Data Visualization, Algorithm and Integration into Vega-Lite." arXiv:2405.10953.
    https://arxiv.org/abs/2405.10953

[7] Borik, Chanwut; Heer, Jeffrey. "Fast and Flexible Overlap Detection for Chart
    Labeling with Occupancy Bitmap." IEEE VIS 2021.
    https://idl.cs.washington.edu/files/2021-FastLabels-VIS.pdf
    Source: https://github.com/vega/vega/tree/main/packages/vega-label

[8] Graphviz Documentation. "xlabel attribute."
    https://graphviz.org/docs/attrs/xlabel/
    Forum discussion: https://forum.graphviz.org/t/customized-xlabel-placement/2597

[9] Cytoscape.js. "nodeDimensionsIncludeLabels option; Issue #1626."
    https://github.com/cytoscape/cytoscape.js/issues/1626
    Main docs: https://js.cytoscape.org

[10] Mapbox. "Collision Detection." mapbox-gl-native Wiki.
     https://github.com/mapbox/mapbox-gl-native/wiki/Collision-Detection
     Label placement help: https://docs.mapbox.com/help/troubleshooting/optimize-map-label-placement/

[11] draw.io. "Position labels inside and outside shapes."
     https://www.drawio.com/doc/faq/position-labels
     Connector label blog: https://drawio-app.com/blog/add-and-rotate-connector-labels/

[12] Imhof, Eduard. "Positioning Names on Maps." *The American Cartographer* 2(2):
     128–144, 1975. (Original German: "Die Anordnung der Namen in der Karte,"
     *International Yearbook Cartography* 2, 93–129, 1962.)
     https://www.tandfonline.com/doi/abs/10.1559/152304075784313304

[13] Heijer, Martijn den; van Garderen, Mereke; Westenberg, Michel A. "From Top-Right
     to User-Right: Perceptual Prioritization of Point-Feature Label Positions."
     arXiv:2407.11996, 2024.
     https://arxiv.org/html/2407.11996

[14] Christensen, Jon; Marks, Joe; Shieber, Stuart. "An Empirical Study of Algorithms
     for Point-Feature Label Placement." *ACM Transactions on Graphics* 14(3): 203–232,
     1995.
     https://dl.acm.org/doi/10.1145/212332.212334
     Pre-print: https://www.eecs.harvard.edu/shieber/Biblio/Papers/tog-final.pdf

[15] Sugiyama, Kozo; Tagawa, Shojiro; Toda, Mitsuhiko. "Methods for Visual
     Understanding of Hierarchical System Structures." *IEEE Transactions on Systems,
     Man, and Cybernetics* 11(2): 109–125, 1981.
     Survey: https://en.wikipedia.org/wiki/Layered_graph_drawing

---

*End of document. Next: 09-mw2-registry-design.md*
