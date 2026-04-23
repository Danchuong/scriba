# Smart-Label Algorithm — Study for Edge-Pill Port

*Source: Explore agent investigation, 2026-04-23. Target: `scriba/animation/primitives/_svg_helpers.py` plus `_obstacle_types.py`, ruleset doc `docs/spec/smart-label-ruleset.md`.*

## 1. Overview of smart-label placer

The smart-label placer is a **greedy, per-label, weighted-scoring placer** that processes annotations sequentially. Each annotation picks the lowest-penalty candidate from a fixed-size pool of 49 positions (1 natural + 48 nudges). Already-placed pills register in a shared mutable list (`placed_labels: list[_LabelPlacement]`) that accumulates across the annotation loop, so each new label avoids all prior ones.

Pipeline per label:
1. Compute natural position from arc geometry.
2. Auto-infer side hint from the arc direction vector.
3. Assemble obstacles tuple (prior pills + primitive segment obstacles).
4. Build 49-candidate tuple.
5. `_pick_best_candidate` → `_score_candidate` on every candidate → argmin.
6. Register winner in `placed_labels`.

A leader line is emitted when the rendered pill centre is visually separated from the arc midpoint by more than `pill_h/2 + 4 + pill_h × _LEADER_GAP_FACTOR`.

## 2. Candidate generation

**Source:** `_svg_helpers.py:874` (`_nudge_candidates`) and caller sites at lines 1789–1792, 2192–2195, 2864–2867.

- **1 natural candidate**: arc-geometry-derived `(label_ref_x, label_ref_y)`, placed at the quadratic control point offset 8 px perpendicular (`_compute_control_points` line 2000–2001).
- **48 nudge candidates**: 8 compass directions × 6 step sizes. Directions N, S, E, W, NE, NW, SE, SW (line 850–858). Step sizes `pill_h × {0.25, 0.5, 1.0, 1.5, 2.0, 2.5}` (line 917).
- **Side-hint ordering** (R-22, line 866–871): when `side_hint ∈ {above, below, left, right}`, the strictly-preferred half-plane directions are emitted first across all step sizes sorted by Manhattan distance, then the remaining 5 directions.
- **Total per label**: 49. `_pick_best_candidate` evaluates all; no short-circuit on first zero-score.

## 3. Scoring model

All penalty terms sum to a single float; lower is better. Source: `_score_candidate`, lines 683–783.

### 3.1 Penalty P1 — Weighted overlap area (weight `_W_OVERLAP = 10.0`)
- **Kind weights** (`_KIND_WEIGHT`, line 277): `pill=1.0, target_cell=3.0, axis_label=2.0, source_cell=0.5, grid=0.2`.
- **Formula**: sum of AABB intersection areas × kind weight.
- **Touch sentinel**: if geometric overlap = 0.0 (touching edges), a 3.0 px² sentinel is returned (line 570–571) so P1 = 30 pt, exceeding a 0.5×pill_h nudge cost (≈ 19 pt at P2 weight 2.0).
- **Hard-block**: `target_cell` and segment MUST obstacles return `inf` (lines 707–717).

### 3.2 Penalty P2 — Displacement from natural position (`_W_DISPLACE = 2.0`)
- Euclidean `‖(cx, cy) − (natural_x, natural_y)‖` in pixels (line 732). No saturation.

### 3.3 Penalty P3 — Side-hint half-plane violation (`_W_SIDE_HINT = 5.0`)
- Binary: 1.0 if candidate is on wrong side of natural per declared hint; else 0.

### 3.4 Penalty P4 — Semantic priority cost (`_W_SEMANTIC = 2.0`)
- `_SEMANTIC_RANK` (line 288): `error=5, warn=4, good=3, path=3, info=2, muted=1`.
- `1.0 − rank/5` per candidate. Constant across all candidates for a given label → effectively sorts labels, not positions.

### 3.5 Penalty P5 — Whitespace / clearance deficit (`_W_WHITESPACE = 0.3`)
- `min_clearance = max(4.0, pill_h × 0.15)`.
- Penalises `max(0, min_clearance − actual_clearance)` (line 741–743). Saturates at 0 when clearance sufficient.

### 3.6 Penalty P6 — Reading-flow (Hirsch) preference (`_W_READING_FLOW = 0.8`)
- Binary 1.0 if candidate is not in the Hirsch (1982) preferred quadrant: NE for horizontal arcs, NW for vertical arcs (line 638–666).

### 3.7 Penalty P7 — Edge / segment occlusion (`_W_EDGE_OCCLUSION = 40.0`)
- For each segment obstacle (kind `"segment"`, `"edge_polyline"`, `"annotation_arrow"`): `min(1.0, clipped_length / pill_short)` where `pill_short = min(pill_w, pill_h)` (lines 756–773). Saturates at 1.0 per segment.
- **Grid-aware scale-down**: when `ctx.flow is not None`, the `annotation_arrow` sub-kind is scaled by 0.75 (line 762).
- **Rationale**: a 20 px displacement costs 40 pt (`P2×20` with `_W_DISPLACE=2`), equal to full occlusion = one `_W_EDGE_OCCLUSION` = 40 pt. Comment at line 753–755.

### Summary

| Term | Weight | Penalises | Saturates |
|------|--------|-----------|-----------|
| P1 | 10.0 | AABB overlap × kind weight | Touch sentinel = 3 px² min |
| P2 | 2.0 | Euclidean displacement | No |
| P3 | 5.0 | Wrong half-plane | Binary |
| P4 | 2.0 | Low semantic rank (constant/label) | [0, 0.8] |
| P5 | 0.3 | Clearance deficit below `max(4, 0.15×pill_h)` | Clamps at sufficient |
| P6 | 0.8 | Outside Hirsch quadrant | Binary |
| P7 | 40.0 | Normalised segment-clipped length per segment | 1.0 per segment |

## 4. Obstacles

**Source:** `_obstacle_types.py`, `_svg_helpers.py:120–230` (internal `_Obstacle`).

Two shape classes:
1. **AABB** (`ObstacleAABB`, `_Obstacle` with `x2=y2=0`): centre + dims. Kinds `pill, target_cell, axis_label, source_cell, grid`. `target_cell` MUST (hard-block); others SHOULD.
2. **Segment** (`ObstacleSegment`, `_Obstacle` with `width=height=0`, `x2/y2` = endpoint). Kinds `plot_line, edge, axis_tick, tree_edge, annotation_arrow`. Mostly SHOULD; `"current"` state can escalate to MUST. Contribute to P7.

Obstacles tuple assembled at call sites (lines 1770–1772, 2162–2164) by `_lp_to_obstacle` (always `"pill"`/SHOULD) + concatenating `primitive_obstacles` from protocol methods `resolve_obstacle_boxes` / `resolve_obstacle_segments`.

**Prior annotation arcs** are sampled by `_sample_arrow_segments` (line 2553–2558): 8 points → 7 segments kind `"annotation_arrow"`, fed back for subsequent labels.

## 5. Ordering strategy

Greedy sequential, not global. Annotations processed in definition order (R-05 specifies semantic-sort `error > warn > good > path > info > muted`, pending v0.12.0 per line 585 comment). Each label placed once; placed pills accumulate for downstream labels.

`_pick_best_candidate` (line 786) uses **stable tie-break**: primary = score ascending, secondary = enumeration index. Explicitly avoids `min()` over generator to satisfy D-1 determinism (spec §4.2, line 795).

**All-blocked fallback** (R-17): if all 49 return `inf`, strip hard-block in a second pass and return argmin over finite-scored positions, then restore `inf` for caller to fire R-19 warning (lines 826–837).

## 6. CellMetrics context

**Source:** `_svg_helpers.py:378–399`.

`CellMetrics` NamedTuple: `cell_width, cell_height, grid_cols, grid_rows, origin_x, origin_y`. Only `cell_width`/`cell_height` actively consumed.

Consumers:
- `classify_flow` (line 420): normalises displacement by cell dims before atan2 classification → sub-cell diagonals on non-square grids (DPTable 60×40) classify correctly.
- `_compute_control_points` (line 1975): `cell_metrics is not None` sentinel enables stagger-flip for odd-indexed 2D stacked arrows.
- `_emit_label_and_pill` (line 2173): propagates `classify_flow` result into `_ScoreContext.flow`, which gates P7 `annotation_arrow` 0.75 scale-down.

Non-grid primitives (Graph, Tree, Plane2D) pass `cell_metrics=None` → pure pixel-space atan2, no stagger-flip.

## 7. Flow classification

**Source:** `classify_flow` (lines 420–448), `FlowDirection` enum (lines 402–417).

`classify_flow(dx, dy, cell_metrics)` → 8 compass `FlowDirection` values via `round(atan2(ny, nx) / (π/4)) % 8` where `(nx, ny)` is cell-normalised if `cell_metrics` provided.

Uses:
1. P7 scale-down (line 762): `ctx.flow is not None` → annotation_arrow × 0.75.
2. Auto side-hint (lines 2144–2150): raw `(dx, dy)` → `|dx| ≥ |dy|` → "above"; else "right".
3. Stagger-flip (`_compute_control_points` line 1975–1985): odd-indexed 2D arrows bow opposite perp side when cell_metrics + layout==2d.

## 8. Leader lines (R-27c)

**Source:** `_svg_helpers.py:2252–2288`; ruleset R-27c (lines 524–557).

Current gate (v0.15.0, visual-gap metric):
```
_visual_gap  = ‖pill_centre − curve_mid‖
_natural_gap = pill_h / 2 + _LEADER_ARC_CLEARANCE_PX          (pill_h/2 + 4)
threshold    = _natural_gap + pill_h × _LEADER_GAP_FACTOR     (_LEADER_GAP_FACTOR = 1.0)
```
Leader emitted when `_visual_gap ≥ threshold` (i.e. pill centre > `pill_h × 1.5 + 4` px from curve midpoint). Applies to all color tokens.

Visual: small circle at `curve_mid` (r=2, 60% opacity) + `<polyline>` to nearest point on pill perimeter (`_line_rect_intersection`, line 2269). Stroke-width 0.75; `warn` gets dashed.

## 9. Transfer analysis — what maps to graph edges

| Smart-label concept | Graph-edge analogue | Transferable? | Notes |
|---|---|---|---|
| Natural position from arc quadratic control point | Parametric midpoint (t=0.5) of edge, ±perp offset `pill_h/2 + clearance` | **Yes, directly** | Two natural candidates (both perp sides) replace single arc-above candidate |
| 49 nudge candidates (8 compass × 6 steps) | Parametric-along (t ∈ {0.25, 0.5, 0.75}) × perp offset (± {0.5, 1.0, 1.5} × pill_h) ≈ 18–24 candidates | **Partially** | Along-line parametrisation more natural for edges than compass |
| P1 AABB overlap + kind weights | Pill vs node circles (→ AABB `2r × 2r`), pill vs other pills | **Yes** | Kind weights: `node=3.0` (target_cell-like), `other_pill=1.0` |
| P2 Euclidean displacement from natural | Displacement from `(midpoint, perp_offset=0)` natural | **Yes** | Keeps pills near edge midpoint |
| P3 Side-hint half-plane | Prefer one perp side; directed edges prefer left-of-flow (Hirsch) | **Yes** | Directed edge has a natural "above flow" side |
| P4 Semantic rank | Edge weight severity (highlighted/current edge = higher rank) | **Yes** | Current/highlighted edges claim best positions first |
| P5 Clearance deficit | Clearance from pill to node perimeter | **Yes** | `min_clearance = max(4, pill_h × 0.15)` unchanged |
| P6 Hirsch reading-flow | Prefer above-right of midpoint for L→R edges | **Yes** | Hirsch NE maps directly |
| **P7 Segment occlusion (W=40)** | Pill must not cross other graph edge lines | **Yes, CORE** | Most critical transfer. Every edge is a segment obstacle for every other edge's pill |
| Greedy sequential, R-05 semantic sort | Sort edges by weight magnitude descending (heaviest first) | **Yes** | Identical mechanism, different sort key |
| Shared `placed_labels` registry | Accumulate across edge loop | **Yes** | Identical |
| Prior annotation arcs as segment obstacles | All other edge line segments (pre-sampled 1–3 segments/edge) | **Yes, new input** | V=10, E=45: 45 segments × 49 candidates ≈ cheap |
| Hard-block (MUST) on target cell | MUST-block pill vs its own endpoint nodes (u and v) | **Yes** | Pill must never cover a node it labels |
| R-27c leader line (visual-gap gate) | Same threshold, polyline from edge midpoint to pill | **Yes** | Formula unchanged: `pill_h × 1.5 + 4` |
| CellMetrics (grid flow normalisation) | N/A — graph has no cells | **No** | `cell_metrics=None`; raw pixel atan2 |
| Stagger-flip for parallel arrows | Alternate left/right perp for parallel edges between same nodes | **Partially** | Natural analogue to stagger-flip idea |
| `_ScoreContext` immutable | `EdgePillContext` frozen dataclass with natural pos, pill dims, edge unit vector, endpoints, viewbox | **Yes** | Same pattern |
| Touch sentinel (3 px² min) | Same when pill touches node AABB | **Yes** | Preserves "clear > touch" |
| `_DEGRADED_SCORE_THRESHOLD = 200.0` | Same (fires R-19 warning) | **Yes** | 67+ px displacement reasoning unchanged |

**Key differences to address:**
1. Natural candidate parameterised as `(t=0.5, perp=±pill_h/2)` rather than Bézier control point.
2. P7 obstacle segments include **all graph edges**, not just prior annotation arcs. Pre-build full segment obstacle set before placement loop.
3. Side-hint auto-inference simplifies to a single cross-product rule: prefer perp side "upward relative to edge direction".

**Complexity** at V=10, E=45: 45 edges × 49 candidates × 45 segment obstacles ≈ 99 225 segment-rect-clip calls. ~1 µs each → <100 ms. Cheap.
