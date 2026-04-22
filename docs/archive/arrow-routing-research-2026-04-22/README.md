# Arrow Routing Research — 2026-04-22

**Branch:** `feat/smart-label-v2.0.0`
**Trigger:** Deep research into `emit_arrow_svg` after v0.12.0 arc-fix (Manhattan→Euclidean, cap expand).
**Method:** 3 parallel sub-agents (industry survey, architect review, planner roadmap) synthesized into merged recommendation.

---

## 1. Problem Statement

`scriba/animation/primitives/_svg_helpers.py:1713 emit_arrow_svg` renders cubic Bezier annotation arrows between primitive cells, with a floating pill label anchored on the curve. The function has grown to ~480 lines, is called by 12 primitives (CRITICAL blast radius per gitnexus_impact), and has accumulated 10 identified issues during v0.12.0 tuning:

| # | Issue | Severity |
|---|-------|----------|
| 1 | ~~Flat cap `1.2 × cell_height`~~ | **DONE v0.12.0** |
| 2 | ~~Stagger no cap~~ | **DONE v0.12.0** (capped at `arrow_index=4`) |
| 3 | `h_nudge` always nudges LEFT; should pick side with more free space | MED |
| 4 | `h_span < 4` threshold hard-coded, not scale-aware | LOW |
| 5 | ~~Manhattan distance~~ | **DONE v0.12.0** (→ Euclidean) |
| 6 | Always curves UP; should detect flow direction | MED |
| 7 | Zero obstacle avoidance — Bezier can pass through intermediate cells | HIGH |
| 8 | Pill leader always targets `B(0.5)`, not closest-point-on-Bezier | LOW |
| 9 | Assumes scalar `cell_height` — Tree/Graph don't have uniform cell_h | MED |
| 10 | No memoization — potentially called many times during placement scoring | LOW |

---

## 2. Industry Survey (sub-agent: general-purpose)

### Tool-by-Tool Summary

| Tool | Shape strategy | Obstacle avoidance | Label placement | Multi-edge handling |
|------|---------------|-------------------|-----------------|---------------------|
| **Mermaid.js** | Cubic Bezier (D3 curve families: `basis`, `cardinal`, `catmullRom`); orthogonal step also available | None (delegated to Dagre/ELK for node layout) | Dummy-node reservation in Dagre; `xlabels` floated post-route | Dagre assigns lanes; ELK bundles parallel edges |
| **Graphviz dot** | Cubic Bezier polyspline (3n+1 control pts) for `splines=spline/curved`; axis-aligned polyline for `splines=ortho` | Visibility-graph O(N³) → shortest polyline → spline fitted inside obstacle-free corridor (2-phase Spline-o-Matic) | Edge labels modelled as dummy nodes during layout; `lp` attr = midpoint of spline; `xlabel` avoids dummy-node distortion | Dot stacks parallel edges in same ranked slot; ortho mode does not support port labels |
| **D3.js** | `d3.linkHorizontal/Vertical` = cubic Bezier S-curve; `d3.lineRadial` = arc; d3-annotation connectors = straight line, elbow, or curved (user-chosen) | None built-in | d3-annotation: label is a freely positioned `<text>` box offset from an anchor point on the connector; anchor defaults to subject center, not curve midpoint | No built-in multi-edge stagger; manual `x`/`y` offset per annotation |
| **d3-annotation** (Susie Lu) | Three connector modes: `line` (straight), `elbow` (two-segment orthogonal), `curve` (cubic Bezier with user-controlled handle). Connector is separate from edge — it's a leader line from a `subject` marker to an offset `note` box. | None | Note box positioned at explicit pixel offset from the subject; user drags it; no auto-placement | No collision avoidance; annotations overlap if too close |
| **Excalidraw** | Curved arrows: quadratic Bezier (single handle, user-draggable midpoint). Elbow arrows: fully orthogonal (90° only). | Elbow arrows: **A\* pathfinding** on a non-uniform grid (nodes only at shape corners + heading intersection points + halfway between obstacles). Curved arrows: none. | No pill labels; text label is a separate shape | Elbow router constrained to ≤2 bounding boxes; no explicit stagger for shared endpoints |
| **React Flow / xyflow** | `bezier` = cubic Bezier; `smoothstep` = orthogonal polyline with rounded corners (quadratic Bézier at bends); `step` = sharp orthogonal; `straight` = line | **None** — no obstacle avoidance in any built-in edge type | Label placed at centroid of the path (`labelX`/`labelY` = mid of bounding box); `getSmoothStepPath` returns offset coords | No auto-stagger; caller must supply different `sourcePosition`/`targetPosition` or custom `centerX`/`centerY` |
| **tldraw** | `kind:'arc'` = quadratic Bezier (one control point, user-draggable handle); `kind:'elbow'` = orthogonal routing. Previously shipped `perfect-arrows` (now internalized). | Elbow: shape-bounding-box aware with gap/overlap detection; simplified heuristic (not A\*, unlike Excalidraw) | Floating label on `arc` arrow; no auto-placement algorithm documented | `ElbowArrowInfo` computes midline between two connected shapes; `arc` has manual handle |
| **perfect-arrows** (Ruiz) | **Quadratic Bezier** (one control point). Returns `[sx,sy, cx,cy, ex,ey, endAngle, startAngle, controlAngle]`. | None | Not in scope (library returns geometry only) | `getBoxToBoxArrow` adds box-edge intersection logic; no stagger |
| **Dagre** | Spline-fit cubic Bezier through waypoints computed by layered layout | Implicit: layout assigns node rows/cols, edges are routed in inter-rank channels | `labelpos` attr; default = midpoint of edge spline | Parallel edges ranked in adjacent virtual nodes |
| **ELK** | Configurable: `POLYLINE`, `ORTHOGONAL`, `SPLINES`. Orthogonal is most common in practice. | Orthogonal routing enforces port constraints + segment separation | Label embedded in ELK edge object; rendered at midpoint of longest segment | Bundling of parallel edges; `mergeEdges` option |

### Key findings

1. **Cubic Bezier is standard** for graph edges and annotation arrows in Mermaid, D3, React Flow, Dagre, Graphviz. Only orthogonal routing (Excalidraw, tldraw elbow, React Flow smoothstep) is comparably common, and requires A*/grid infrastructure that does not fit a static SVG pipeline.
2. **No production tool does full obstacle avoidance for annotations.** Excalidraw elbow + Graphviz ortho are the exceptions — both are interactive editors with arbitrary shape placement, not cell-aligned grids.
3. **Battle-tested library to port:** `perfect-arrows` (Ruiz, MIT, ~200 lines JS). Quadratic Bezier, distance-adaptive `bow + stretch` formula. Portable to ~100 lines Python.
4. **Annotation vs data edge visual distinction:** tools consistently use a **leader-line pattern** — thin, often dashed, terminates at label box rather than node boundary. Scriba's colored pill + thin Bezier stem already follows this pattern correctly.
5. **Label anchor t=0.4 not t=0.5** — both perfect-arrows and d3-annotation place the annotation note slightly toward the source end (t=0.35–0.45) for LTR reading direction.
6. **Nudge direction heuristic** (informal, not formalized in any reviewed tool): compute perpendicular bisector of src→dst, choose half-plane with more free area (fewest obstacle bounding boxes intersecting a test arc). O(k) over `primitive_obstacles`.

### Academic references

- Wybrow, Marriott, Stuckey (2009) — "Orthogonal Connector Routing"
- Marriott et al. (2014) — "Seeing Around Corners"

No short-range callout routing paper distinct from full A* — practitioners default to fixed-direction arcs (convex up, perpendicular offset) for predictability and speed.

---

## 3. Architecture Review (sub-agent: architect)

### Verdict

> The current architecture is functional and has grown organically with each rule (R-01 through R-31) but `emit_arrow_svg` has accumulated enough responsibilities that it will become a genuine maintenance liability before the v0.12.0 planned features land. A targeted refactor is warranted, but it does not need to be large.

### Architectural issues

1. **Single Responsibility violated** — `emit_arrow_svg` does all of: endpoint shortening, Bezier CP calc, arrowhead tip-direction math, curve midpoint for leader anchor, label-size estimation, `_nudge_candidates` search, `_pick_best_candidate` scoring, leader emission, pill rect emission, single-line vs multi-line text emission, ARIA attribute construction, dash-array derivation, `_sample_arrow_segments` return. ~480 lines.
2. **Open/Closed will not scale** — `if layout == "2d" ... else ...` fork handles 2 shapes today. Obstacle avoidance + flow-direction curves + orthogonal/S-curve will grow this to 4+ arms each duplicating common control-point preamble.
3. **Testability blocked by output coupling** — no way to unit-test "does the arc for a diagonal 2d arrow produce right control points and tip direction?" without invoking full SVG emit.
4. **Duplication** — `emit_arrow_svg` and `emit_plain_arrow_svg` share 60–70% of label-placement/text-emission block verbatim. Future R-02/R-05 changes must be applied twice.
5. **Stringly-typed protocol** — `PrimitiveBase.emit_annotation_arrows` translates `_arrow_layout == "2d"` to `kwargs["layout"] = "2d"`. No enforcement; a new primitive that forgets the string gets horizontal layout silently.

### Proposal options

| Option | Description | Pros | Cons | Effort |
|--------|-------------|------|------|--------|
| **A** Strategy pattern | `ArrowShape` protocol with `ConvexArchShape`, `VerticalNudgeShape`, `OrthogonalShape`, `PerpendicularShape` | Adding shape = new file, not branch. Testable isolated. | Indirection for 15–20 lines of arithmetic. | M |
| **B** Pipeline | `(geometry) → (obstacle avoidance) → (label placement) → (serialization)` pure functions | Each stage independently testable. Dedup with `emit_plain_arrow_svg`. | Changes mutation contract to return-value; touches all 12 callers. | L |
| **C** Extract dataclass | Pull CP math (lines 1787–1868) into pure `compute_arrow_geometry(...) -> ArrowGeometry` frozen dataclass. Extract `_emit_label_and_pill` shared helper. | Geometry unit-testable without SVG machinery. Dedup eliminated. **No caller changes.** Unblocks obstacle-avoidance because control points become explicit value. | Still has `if layout == "2d"` inside `compute_arrow_geometry` (doesn't give Strategy yet). | **S** |
| **D** Do nothing | Self-consistent; all planned features can be force-fit | Zero churn. | Each planned feature adds state to already-large function; duplication diverges. | — |

### Architect's recommendation

**Option C**. Extract `compute_arrow_geometry` as `@dataclass(frozen=True)` returning `(ix1, iy1, cx1, cy1, cx2, cy2, ix2, iy2, label_ref_x, label_ref_y, curve_mid_x, curve_mid_y, tip_direction)`. Extract `_emit_label_and_pill` as shared helper. No behavior change, no caller changes, **migration effort S**. Clears testability blocker + eliminates duplication in one commit — prerequisite for v0.12.0 features.

---

## 4. Phased Roadmap (sub-agent: planner)

### Sequencing recommendation

> Ship the current uncommitted v0.12.0 cluster first, without touching any curve geometry — all eight open issues are post-v0.12.0 work. Sequence by blast radius: #4 + #3 are low-blast quick wins; #6 is medium-blast formula change that must land before #7 (obstacle avoidance) because avoidance sampling depends on curve geometry being correct.

### Phased table

| Phase | Version | Issues | Effort | Risk |
|-------|---------|--------|--------|------|
| A | v0.12.1 | #4 (threshold), #10 (memo) | S | Low |
| B | v0.12.2 | #3 (side nudge), #8 (closest-point leader) | M | Medium |
| C | v0.13.0 | #6 (flow direction), #9 (cell_h scalar) | M | Medium-High |
| D | v0.13.1 | #7 (obstacle avoidance) | L | High — depends Task #16 |

### Phase A — v0.12.1 (zero-blast quick wins)

- Extract `h_span < 4` to `_H_SPAN_VERTICAL_THRESHOLD = max(4.0, cell_height * 0.05)`. Lines 1845–1851. At cell_h=80 px → 4 px (no visible change) but formula tracks cell size.
- Extract `_compute_bezier_geometry(x1, y1, x2, y2, cell_height, arrow_index, layout)` → frozen dataclass. Wrap with `@functools.lru_cache(maxsize=256)`. Requires `cell_height` be hashable scalar (#9 dependency; Phase C must remove scalar assumption before widening cache).
- Test: parametric unit test on new constant. No golden re-pin.
- Risk: Low.

### Phase B — v0.12.2 (side-aware nudge + closest-point leader)

- **#3**: replace `mid_x_f - h_nudge` with side-selection via `left_space = x1`, `right_space = viewbox_w - x2`. `side_sign = -1 if left_space >= right_space else +1`. Apply `cx1 = cx2 = max(0, int(mid_x_f + side_sign * h_nudge))`. `viewbox_w` available on `_ScoreContext` or approximated as `max(x1, x2) * 2 + pill_w` (same as line 2036).
- **#8**: replace `curve_mid_x/curve_mid_y` (B(0.5)) in leader origin with closest-point search. Sample Bezier at N=8 t-values (already implemented as `_BEZIER_SAMPLE_N`), pick closest sample to `(fi_x, fi_y)`. Reuses R-31 ext infrastructure.
- Test: assert `cx1 >= mid_x_f` when `x1 > viewbox_w - x2` (right nudge). For #8, synthetic non-symmetric CP case. Re-pin 2 golden fixtures (DPTable column-to-column).
- Risk: Medium. Right-nudge may shift pixels on DPTable column annotations.

### Phase C — v0.13.0 (flow direction + cell_h)

- **#9** first: replace `cell_height: float` with `cell_height: float | tuple[float, float]` (or `_CellMetrics` namedtuple). Scalar callers unchanged. Tree/Graph (Task #16 scope) can pass non-uniform metrics.
- **#6** second: after `total_offset` computation, detect flow. `y1 > y2` (source below target, arrow upward) → keep `min(y1, y2) - total_offset`. `y1 < y2` (source above, arrow downward) → flip to `max(y1, y2) + total_offset`. `y1 == y2` → current formula.
- Test: parametric on 3 sign cases. Re-pin 3–5 DPTable goldens with downward arrows.
- Risk: Medium-High. Curve direction flip visible on any scene with source row > target row. Align with Task #16.

### Phase D — v0.13.1 (obstacle avoidance, **lightweight**)

- Dependency: Task #16 (Graph/Tree AABBs) must ship first to provide `resolve_obstacle_boxes` infrastructure.
- Do **not** implement full A*/visibility-graph — industry survey confirms overkill for cell-aligned grids.
- **Greedy upward push**: sample proposed Bezier at N=8 points, check against intermediate cell AABBs. If any sample inside a cell, `total_offset += cell_height * 0.3`, re-check. Max 3 iterations.
- Gate behind `primitive_obstacles` non-empty — primitives not yet passing obstacles get identical output.
- Test: synthetic src (0,0) → dst (3,0) with occupied cell (1,0) — assert all 8 sample `y < cell_top`. Golden fixture for multi-hop DPTable annotation. Expect most existing goldens unaffected.
- Risk: High. Coordinate with Task #16 completion.

### Parking lot

- **#10 (memoization full form)**: Phase A `lru_cache` covers hot path. Full memoization (entire SVG string) unsafe due to `lines.append` / `placed_labels.append` side effects.
- **#8 closest-point refinement beyond 8 samples**: N=8 sub-pixel accurate at typical curve magnitudes. Newton's method is over-engineering.

---

## 5. Merged Recommendation

Combining industry + architect + planner:

| Phase | Version | Content | Source |
|-------|---------|---------|--------|
| **0** | v0.12.0 | **SHIP NOW** — R-27b leader gate + scoring tweaks + CSS rect fix + arc-fix (Euclidean + cap expand) | Current cluster |
| **A** | v0.12.1 | **Architect Option C** (extract `ArrowGeometry` dataclass + shared `_emit_label_and_pill`) + **Planner Phase A** (threshold #4 + lru_cache #10). Zero behavior change. | Architect + Planner merged |
| **B** | v0.12.2 | Planner Phase B (#3 perpendicular-half-plane side-nudge, #8 closest-point leader) **+ port `perfect-arrows` `bow+stretch` formula** (replace cap-based offset) **+ anchor t=0.4** (LTR reading) | Planner + Industry |
| **C** | v0.13.0 | Planner Phase C (#6 flow-direction, #9 `cell_height` → `CellMetrics`) | Planner |
| **D** | v0.13.1 | Planner Phase D **lightweight greedy push** (not A*) — after Task #16 | Planner + Industry validation |

### Critical decisions

1. **Don't overengineer** — industry data: A*/visibility-graph not used for annotations in any major tool. Greedy nudge + perpendicular-half-plane test covers realistic cases.
2. **Architect Option C before any other phase** — extracting geometry is prerequisite. Zero blast radius, effort S, unblocks testability.
3. **Port `perfect-arrows` `bow+stretch`** — ~200 line JS → ~100 line Python, MIT licence, proven in tldraw/Excalidraw ecosystem. Replaces current `sqrt(euclid) * 2.5` + hard cap formula with distance-adaptive curvature.
4. **Label anchor t=0.4** — bonus tuning from d3-annotation + perfect-arrows. Minor but validated by convention.

### Immediate actions

1. **Commit v0.12.0 cluster** (R-27b leader + `_W_DISPLACE=2.0` + P1 sentinel=3.0 + `_DEGRADED_SCORE_THRESHOLD=200.0` + CSS rect fix + arc-fix Euclidean/cap).
2. **Next branch `feat/arrow-refactor-v0.12.1`** — extract `ArrowGeometry` dataclass + shared helper + threshold constant + `lru_cache`.
3. **Research spike** — port `perfect-arrows` `bow+stretch` to Python (standalone test, compare curve shapes with current formula, visual diff before merge Phase B).

---

## 6. Provenance

| Agent | Duration | Tokens | Output file |
|-------|----------|--------|-------------|
| general-purpose (industry survey) | 269 s | 62,100 | `/tmp/claude-501/.../ac12c59f0505e85a9.output` |
| architect (redesign review) | 73 s | 55,851 | `/tmp/claude-501/.../a46477abdf44415a9.output` |
| planner (phased roadmap) | 89 s | 62,947 | `/tmp/claude-501/.../a41e5d7d477f85716.output` |

Transcripts ephemeral (tmp). Key findings captured above.

### Related documents

- `docs/spec/smart-label-ruleset.md` — R-01 through R-31 ruleset
- `docs/archive/smart-label-audit-2026-04-21/` — prior audits
- `docs/archive/smart-label-edge-avoidance-2026-04-22/` — earlier edge-avoidance work
- Task #16 — v0.12.0 W2-β Graph/Tree AABBs + R-20/21/28/29 (**blocks Phase D**)
