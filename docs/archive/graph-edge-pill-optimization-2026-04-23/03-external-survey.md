# External Edge-Label Algorithms — Survey

Date: 2026-04-23
Scope: Research for adapting smart-label-style placement to graph edge pills.

---

## 1. Graphviz

### Core algorithm

Graphviz uses two strategies for edge labels.

**Standard `label` (dummy-node, `dot`):** Each label is promoted to a *virtual node* inserted along the edge chain during rank assignment. Normal coordinate assignment reserves space before splines are routed. After routing, `place_vnlabel()` (`lib/dotgen/dotsplines.c:524`) reads the virtual node's coordinate and shifts the label right by half its width. No post-hoc collision pass is needed; space is reserved structurally.

**`xlabel` (post-hoc):** After full layout, a second pass (`lib/label/xlabels.c`) places external labels using a spatial index: a splay tree keyed on Hilbert codes combined with an R-tree for overlap queries. Candidates are scored by an area metric (`BestPos_t`); the lowest-cost non-overlapping position wins. If no slot is found the label is omitted (override with `forcelabels=true`).

**`headlabel` / `taillabel`:** Placed at a polar offset from the endpoint. `labelangle` (default −25°) sets radial direction; `labeldistance` scales distance. No overlap resolution.

### Candidate positions

- **`label`:** one position, determined by virtual-node coordinate — no search.
- **`xlabel`:** continuous search around the label's natural point; candidates ranked by BestPos area metric; R-tree prunes collisions efficiently.
- **`headlabel`/`taillabel`:** single position from (angle, distance) parameters.

### Collision handling

`xlabel` is the only mode with explicit collision avoidance (label vs. node, label vs. label). Standard `label` prevents collisions structurally by widening ranks; `headlabel`/`taillabel` have none.

### Ordering / greediness

`xlabel` placement is greedy per-label in undefined order; a label not placed in the first pass is omitted or forced.

### Trade-offs

| | `label` | `xlabel` |
|---|---|---|
| Quality | Guaranteed space | Best-effort |
| Cost | Distorts layout (widens ranks) | Post-hoc, cheap |
| Overlap | Never (structural) | Usually avoided |

Code: `lib/dotgen/dotsplines.c`, `lib/label/xlabels.c`, `lib/label/xlabels.h`
DOI/paper: Gansner et al., "A Technique for Drawing Directed Graphs," IEEE TSE 19(3):214–230, 1993.

---

## 2. Mermaid.js

### Core algorithm

Mermaid delegates layout to Dagre (default) or ELK. Label position is stored as `labelpos: 'c'` (center), hardcoded in `flowDb.ts`. The screen coordinate comes from `calcLabelPosition(path)` in `dagre-wrapper/edges.js`, which samples the path for a midpoint (x, y) and adds a vertical margin (`subGraphTitleTotalMargin / 2`). For start/end labels, `calcTerminalLabelPosition()` offsets 10 px from the arrowhead.

### Candidate positions

One: the parametric midpoint of the rendered path (t ≈ 0.5). No search across alternatives.

### Collision handling

None in Mermaid itself. Dagre may adjust edge routing, but edge-label vs. edge-label or edge-label vs. node collisions are not detected or resolved. This is a known open issue (mermaid-js/mermaid#490).

### Ordering / greediness

N/A — single fixed position.

### Trade-offs

Simple and fast; visually clean for sparse graphs. Dense graphs produce overlapping labels with no recourse. The architecture makes it easy to swap in a better `calcLabelPosition` without touching layout.

Code: `packages/mermaid/src/dagre-wrapper/edges.js` (`positionEdgeLabel`, `calcLabelPosition`), `src/diagrams/flowchart/flowDb.ts` (`labelpos: 'c'`).

---

## 3. D3-graphviz / Cytoscape.js

### D3-graphviz

D3-graphviz is a thin bridge: it feeds a DOT string into Graphviz (compiled to WASM), receives back SVG with pre-computed label coordinates, and animates between states using D3 transitions. It adds no label placement logic of its own. Label positions are whatever Graphviz emitted.

### Cytoscape.js

Cytoscape.js supports `text-rotation: autorotate` to align label text to the edge slope. Label position is controlled by `edge-text-rotation`, `source-text-offset`, `target-text-offset`, and `text-margin-x/y` CSS-like style properties. The midpoint is the default anchor.

There is no built-in edge-label collision avoidance. Layout engines (`cola`, `dagre`, `elk` via adapters) expose `avoidOverlap: true` but this flag applies to *node* bounding boxes only — edge labels are excluded. This is an acknowledged gap (cytoscape/cytoscape.js#2872, #1013). Community extensions (`cytoscape-no-overlap`) address node overlap only.

### Trade-offs

Both libraries trade placement quality for simplicity/speed. They suit interactive graphs where users can pan/zoom past label collisions; they are insufficient for print-quality diagrams.

---

## 4. Commercial (yEd, Tom Sawyer, JGraphX/mxGraph)

### yFiles (yEd's engine)

yFiles introduces a formal *label model* abstraction. An `EdgePathLabelModel` or `SmartEdgeLabelModel` discretises an edge into a set of *candidate positions* — each a (t, side, distance) triple where t ∈ [0,1] parameterises arc length along the edge, side ∈ {left, right, on-edge}, and distance is a perpendicular offset in pixels. `GenericLabeling` iterates over all labels, evaluates each candidate against a cost function that penalises overlap with nodes, other edges, and other labels, then assigns the cheapest non-conflicting position. For *integrated labeling*, the routing step itself avoids generating edge paths that cross label bounding boxes. This is substantially more principled than any open-source equivalent.

Code pointer: `docs.yworks.com/yfiles-html/dguide/layout/label_placement.html`

### Tom Sawyer Perspectives

Three configurable association points per edge (source, center, target) plus a "label region" (above/below/left/right/over the edge). Placement is reported as automatic and layout-aware ("does not overlap nodes, edges, or other labels, and does not overlap crossing locations") but no algorithmic details are public. Commercially licensed.

### JGraphX / mxGraph (draw.io upstream)

Edge label geometry is stored as a relative coordinate `(x, y)` where `x ∈ [−1, 1]` is arc-length fraction from the edge midpoint and `y` is an absolute perpendicular offset in pixels, plus an absolute `offset` vector. Default is `(0, 0)` — the midpoint. There is no automatic placement or collision avoidance; developers must set coordinates manually or implement their own pass. Known issue: mxHierarchicalLayout does not respect label bounding boxes (jgraph/mxgraph#113).

### Trade-offs

yFiles is the most complete: the (t, side, distance) candidate parameterisation plus cost-function assignment is the right mental model for a constrained placement problem. Tom Sawyer is high-quality but opaque. mxGraph/JGraphX provides geometry primitives but no solver.

---

## 5. Academic

### Kakoulis & Tollis — Edge Label Placement complexity (2001) and unified approach (2003)

The Edge Label Placement (ELP) problem asks: given a set of edges each with a fixed-size label and k candidate positions per edge, select one position per label to maximise the number of non-overlapping placements. Kakoulis & Tollis proved ELP NP-hard even for k = 2 candidates per edge, reducing from Independent Set on the *conflict graph* (where nodes are (edge, candidate) pairs and edges connect geometrically overlapping candidates). Their 2003 unified framework represents all graphical features — nodes, edges, areas — with a common label model, so that node and edge label placement can be solved in one pass. The heuristic they propose is a greedy maximum-independent-set scan on the conflict graph: pick the vertex (candidate) with highest degree, eliminate it and all its neighbours, repeat. This runs in O(n²) and empirically assigns ≥50% of labels their best candidate.

DOI: Computational Geometry 18(1):1–17 (2001); IJCGA 13(1):23–60 (2003).

### Wagner & Wolff — "Three Rules Suffice for Good Label Placement" (2001) and orthogonal labeling (2005)

The "three rules" paper (Wagner, Wolff, Kreveld, Strijk) formalises a point-feature labeling model but includes edge labeling as a special case. The key insight is that three geometric rules applied in priority order — (1) label must not overlap its own feature, (2) label must not overlap other features, (3) label must not overlap other labels — combined with a fixed candidate set produce near-optimal results with a simple greedy sweep. The orthogonal labeling paper (Eiglsperger, Kaufmann, Wagner; GD 2003/JGAA 2005) extends this to orthogonal graph drawings: candidates are placed at corners of edge segments, and the Sugiyama-style layered algorithm is modified to reserve label space by widening segments — similar to Graphviz's dummy-node approach but for rectilinear layouts.

DOI/URL: `www1.pub.informatik.uni-wuerzburg.de/pub/wolff/pub/wwks-3rsgl-01.pdf`; ScienceDirect Computational Geometry 32(1):1–27 (2005).

### vPRISM / ePRISM — force-directed label placement (arXiv 0911.0626)

A more recent approach avoids the candidate enumeration entirely. Edge labels become virtual nodes in the graph and a penalised stress model is minimised: the penalty term `‖x_k − (x_i + x_j)/2‖²` pulls label k toward the midpoint of its edge while the PRISM overlap-removal algorithm repels all bounding boxes. The proximity graph (Delaunay triangulation) drives the sparse linear system. This finds globally smooth placements at the cost of potentially moving labels far from the midpoint on crowded graphs.

arXiv: 0911.0626 (Nachmanson et al., 2009).

### Key take-away from literature

ELP is NP-hard; all practical systems use either (a) structural reservation (dummy-node / widen-segment), (b) greedy conflict-graph search over a discrete candidate set, or (c) force/penalty relaxation. The discrete-candidate approach (b) maps most cleanly to a pill-placement problem where candidates can be enumerated geometrically.

---

## 6. Pattern catalog

| Technique | Used by | Maps to edge-pill problem? | Cost |
|---|---|---|---|
| Dummy-node structural reservation | Graphviz `dot`, ELK hierarchical | Partial — requires layout rerun | High (layout distortion) |
| R-tree + Hilbert-code spatial index for xlabel | Graphviz `xlabel` | Yes — fast overlap query for pills | Low–medium |
| Hardcoded midpoint, no collision | Mermaid.js, Cytoscape.js | No — insufficient for dense graphs | O(1), trivial |
| (t, side, distance) candidate model + cost function | yFiles GenericLabeling | Yes — directly models pill placement | Medium |
| Greedy max-independent-set on conflict graph | Kakoulis & Tollis 2003 | Yes — maps pill candidates to conflict graph | O(n²) |
| Structural widening of edge segments | Wagner & Wolff orthogonal 2005 | Partial — only rectilinear layouts | High |
| Penalised stress + virtual label node (ePRISM) | arXiv 0911.0626 | Partially — smooth but imprecise anchor | Medium–high |
| Polar offset from endpoint (labelangle/labeldistance) | Graphviz head/taillabel | No — single position, no search | O(1) |
| (x, y) relative geometry, manual | JGraphX / mxGraph | No — requires external solver | O(1) per label |

---

## 7. Recommendations to consider

- Adopt the **(t, side, distance) candidate parameterisation** from yFiles: enumerate candidates at t ∈ {0.25, 0.5, 0.75} × side ∈ {left, right} × distance ∈ {small, large} for 12 candidates per edge; this fits naturally onto a pill-shaped label geometry.
- Build a **conflict graph** over (edge, candidate) pairs as in Kakoulis & Tollis and run a greedy independent-set sweep: cheap, well-understood, proven to assign ≥50% best positions.
- Use an **R-tree** (or axis-aligned bounding box grid) for O(log n) overlap queries rather than O(n²) pairwise checks, analogous to Graphviz's xlabel spatial index.
- Consider the **ePRISM midpoint penalty** as a secondary objective when a greedy pass leaves a label with all candidates blocked: pull it toward the midpoint under a soft constraint rather than dropping it.
- Do not replicate the dummy-node approach — it requires layout re-runs and distorts the graph; it is only sensible when the layout engine is designed around it from the start.
- Mermaid's `calcLabelPosition` midpoint baseline is a reasonable default anchor before any collision pass — it is the cheapest thing that looks correct on sparse graphs.
