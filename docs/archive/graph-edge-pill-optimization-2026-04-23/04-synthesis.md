# Edge-Pill Placement — Synthesis & Adaptation Design

*Source: architect agent, 2026-04-23. Inputs: `01-current-audit.md`, `02-smart-label-study.md`, `03-external-survey.md`, `docs/archive/graph-edge-pill-logic-2026-04-23.md`.*

## TL;DR

- Keep the current 3-step loop as a **fast path** for the ~80% of non-degenerate edges.
- Fix the two CRITICAL bugs (F1 node-circle overlap, G1 missing check) in Phase 0 with a single AABB guard — no pipeline change.
- **Phase 0.5 (new, 2026-04-23 product decision)**: rotate pill + text to match edge angle, normalize to `[-π/2, π/2]` for text-upright. Improves pill→edge association on dense/diagonal graphs. See §*Rotation addendum* and `docs/plans/edge-pill-rotation-impl-plan.md`.
- Phase 1: introduce `EdgePillContext` (frozen dataclass mirroring `_ScoreContext`) and pre-build a segment obstacle set from all graph edges; reuse `_score_candidate` / `_pick_best_candidate` unchanged.
- Candidate generation follows yFiles' `(t, side, distance)` parameterisation — 3 t-values × 2 perp sides × 4 offsets = **24 candidates per edge**.
- Sort edges by `(state priority DESC, edge key ASC)` before the loop (fixes E4/E5 determinism).

## Decision — what to keep, what to add, what to reject

| Feature | From | Status | Rationale |
|---|---|---|---|
| `_LabelPlacement` AABB registry | Current | **Keep** | Works; only missing node-circle entries |
| `_LabelPlacement.overlaps()` | Current | **Keep** | Used by fast path; P1 engine calls `_aabb_intersect_area` semantically equivalent |
| `_pick_best_candidate` / `_score_candidate` | Smart-label (`_svg_helpers.py:683–837`) | **Keep / reuse** | 7-penalty engine already exists; no rewrite |
| `_nudge_candidates` (8 compass × 6) | Smart-label (`_svg_helpers.py:874`) | **Adopt-lite** | Replace with edge-parametric `(t, side, offset)` generator |
| `_Obstacle` frozen dataclass | Smart-label (`_svg_helpers.py:137`) | **Keep / extend** | Add `"node_circle"` to `ObstacleKind`; `"edge_line"` as `"segment"` sub-kind |
| `_ScoreContext` | Smart-label | **Adopt** | `EdgePillContext` structural parallel |
| P1–P7 weights | Smart-label | **Adopt with changes** | P3 re-parameterised; P4 re-keyed to edge state; P7 unchanged at 40.0 |
| R-27c leader line | Smart-label (`_svg_helpers.py:2252`) | **Adopt-lite** | Same threshold; target = edge midpoint, not Bézier control point |
| Greedy sequential + semantic sort | Smart-label | **Adopt** | Sort key changes to edge state priority |
| CellMetrics flow normalisation | Smart-label | **Reject** | `cell_metrics=None` for Graph; raw pixel atan2 |
| Stagger-flip for parallel arcs | Smart-label | **Adopt-lite** | Multi-edge `(u,v)` → alternating initial `side_hint` |
| R-tree spatial index | Graphviz `xlabel` | **Reject** | V=10 E=45 inside O(n²) budget; +200 LOC, no gain |
| Dummy-node structural reservation | Graphviz `dot` | **Reject** | Requires layout rerun; incompatible with stateless `emit_svg` |
| ePRISM relaxation | arXiv 0911.0626 | **Reject** | Non-deterministic, violates D-1 |
| Greedy MIS on conflict graph | Kakoulis & Tollis 2003 | **Reject** | O(E²) conflict graph; same quality as sequential for small E |
| Pill constants module-level | Audit E2 | **Adopt** | Promote `_WEIGHT_FONT`, `_PILL_PAD_X/Y`, `_PILL_R` |

## Proposed algorithm

**Pre-loop setup:**

1. Promote `_WEIGHT_FONT = 11`, `_PILL_PAD_X = 5`, `_PILL_PAD_Y = 2`, `_PILL_R = 3` to module-level constants in `graph.py` (fixes E2).

2. Before iterating edges, sort edge list by `(_state_priority(state), edge_key_str)` ascending — state priority: `current=0, highlighted=1, active=2, idle=3, muted=4`. Freeze order for this `emit_svg` call (fixes E4, E5; D-1 stable tie-break).

3. Build `edge_segments: tuple[_Obstacle, ...]` from every non-hidden edge's visible segment `(x1, y1) → (x2', y2')`, kind `"edge_line"` (treated as `"segment"` for P7), severity `SHOULD`. Immutable for the loop.

4. Build `node_circle_obstacles: tuple[_Obstacle, ...]` — one `_Obstacle(kind="node_circle", x=cx, y=cy, width=2r, height=2r, severity="MUST")` per visible node. Fixes G1/F1 — MUST hard-block prevents pill landing inside any node circle.

5. Initialise `placed_pills: list[_LabelPlacement] = []`.

**Per-edge loop:**

6. Compute visible segment endpoints after directed shortening (unchanged from `graph.py:748–750`).

7. `mid_x = (x1 + x2') / 2`, `mid_y = (y1 + y2') / 2` — no `−4` y-bias (fixes E1; the perp offset in step 8 replaces it with a geometrically justified value).

8. Compute edge unit perpendicular `(perp_x, perp_y)` with `edge_len or 1.0` clamp (unchanged). For `edge_len < 4.0` (coincident), emit fallback pill at `(mid_x, mid_y − pill_h)` and log warning (fixes F4).

9. **Candidate generation**: enumerate 24 `(t, sign, offset_factor)` triples. Convert each to `(cx, cy)`. Prepend two "natural" candidates `(t=0.5, sign=±1, offset=pill_h/2 + 2)` — strongly weighted toward midpoint-above/below.

10. **Fast path**: if best natural candidate (Hirsch-preferred perp) does not overlap `placed_pills + node_circle_obstacles`, accept directly without full scoring. Preserves O(1) for clean cases.

11. **Full scoring path**: assemble `obstacles = (*node_circle_obstacles, *edge_segments_minus_own, *[_lp_to_obstacle(p) for p in placed_pills])`. Build `EdgePillContext`. Call `_pick_best_candidate(candidates, obstacles, ctx)`. Accept winner; if score ≥ `_DEGRADED_SCORE_THRESHOLD = 200.0`, log R-19 warning.

12. Clamp `cx ∈ [pill_w/2, viewbox_w − pill_w/2]`, `cy ∈ [pill_h/2, viewbox_h − pill_h/2]` (fixes G5).

13. Append winner to `placed_pills`. Emit SVG.

14. **Leader line** (Phase 3): if `hypot(cx − mid_x, cy − mid_y) ≥ pill_h * 1.5 + 4`, emit leader polyline from `(mid_x, mid_y)` to nearest pill perimeter point (R-27c, `_svg_helpers.py:2252`).

## Candidate generation for edges

Parameterisation: `t ∈ {0.25, 0.5, 0.75}`, `sign ∈ {+1, −1}`, `offset_factor ∈ {0.5, 1.0, 1.5, 2.5}` × `pill_h`. Total: 3 × 2 × 4 = **24**.

Screen coord from `(t, sign, offset_factor)`:
- `bx = x1 + t * dx`, `by = y1 + t * dy`
- `cx = bx + sign * perp_x * offset_factor * pill_h`
- `cy = by + sign * perp_y * offset_factor * pill_h`

**Natural candidates** (prepended, indices 0 and 1): `t=0.5, sign = Hirsch-preferred, offset_factor = (pill_h/2 + 2) / pill_h`. These should cost P2=0 displacement.

**Ordering**: Hirsch-preferred sign first across all `t`, then anti-preferred. Within each sign, `t ∈ {0.5, 0.25, 0.75}`. Within each `(t, sign)`, offsets ascending. Matches `_pick_best_candidate`'s stable tie-break (`_svg_helpers.py:795`): enumeration index is secondary key, so midpoint-perp candidates win ties.

**Determinism**: deterministic generator, no randomness. Index 0 = natural Hirsch candidate always. D-1 safe.

## Scoring model for edges

`EdgePillContext` passes `pill_w`, `pill_h`, `natural_x`, `natural_y`, `color_token` (from edge state), `side_hint`, `flow=None`. `_score_candidate` called unchanged.

| Penalty | Weight | Change | Obstacle kinds | Notes |
|---|---|---|---|---|
| P1 overlap × kind | 10.0 | Unchanged | `node_circle = 3.0` (target_cell semantic); `pill = 1.0`; `axis_label` dropped | MUST on `node_circle` returns `inf` before P1 evaluated |
| P2 displacement | 2.0 | Unchanged | Natural = `(mid, ± pill_h/2 + 2)` at `t=0.5` | Anchors pills near midpoint |
| P3 side-hint | 5.0 | Unchanged | Auto-inferred: `cross(edge_dir, up_screen) > 0 → "above"` else `"below"`; directed = left-of-flow | Replaces fixed `−4` with geometric preference |
| P4 semantic rank | 2.0 | **Re-keyed** | `current=5, highlighted=4, active=3, idle=2, muted=1` | Per-edge constant; sorts edges, not candidates |
| P5 clearance deficit | 0.3 | Unchanged | `min_clearance = max(4.0, pill_h × 0.15)` | Already correct |
| P6 Hirsch reading-flow | 0.8 | Unchanged | NE for L→R, NW for R→L/vertical; raw pixel atan2 | `flow=None` path already handled |
| P7 edge occlusion | 40.0 | Unchanged | `"edge_line"` sub-kind (treated as `"segment"`); **own edge excluded** | Forces pill off crossing edges (G2 fix) |

**Node-circle hard-block**: `node_circle` carries `severity="MUST"`. Caught at `_svg_helpers.py:706–717` → returns `inf`. Minimal correct fix for F1/G1.

**Own-edge exclusion**: omit current edge's segment when building obstacles. Otherwise P7 penalises natural position (pill on own edge midpoint).

## Obstacles schema for Graph context

| Obstacle | Kind | Severity | Source | Shape |
|---|---|---|---|---|
| Node circle | `"node_circle"` | `MUST` | `self.positions[n]`, `self._node_radius` | AABB centre `(cx, cy)`, dims `(2r, 2r)` |
| Other edge lines | `"segment"` (`"edge_line"`) | `SHOULD` | `edge_segments` tuple | Segment `(x1, y1) → (x2', y2')` |
| Placed pills | `"pill"` | `SHOULD` | `placed_pills` via `_lp_to_obstacle` | AABB |
| Stage boundary | — | — | `viewbox_w / viewbox_h` | Hard clamp post-scoring |

Cross-primitive obstacles (G4) → Phase 3: requires threading shared `placed_labels` from `emit_svg` into `Graph.emit_svg`.

`ObstacleKind` at `_svg_helpers.py:130` needs `"node_circle"` added; `_KIND_WEIGHT` needs `"node_circle": 3.0`. Only changes to `_svg_helpers.py` in Phase 1.

## Ordering — edge placement order

Sort copy of `self.edges` by:
1. `_state_priority(self.get_state(edge_key))` ascending.
2. Canonical edge key `self._edge_key(u, v)` lexicographic.

D-1 determinism: identical logical graphs with different declaration order → identical placements (fixes E4, E5). O(E log E) — negligible.

## Leader line reuse

R-27c gate transfers directly. Threshold `pill_h * 1.5 + 4` = 29.5 px at `pill_h=17`. With max `offset_factor = 2.5 × pill_h = 42.5 px`, leaders fire at 2.5× tier. Target = geometric midpoint of visible segment (analogue of `curve_mid`). Thin wrapper in `graph.py`, not shared with annotation emitter (no arrow — just 0.75 px stroke circle + polyline). Phase 3.

## Migration plan

### Phase 0 — Incremental fixes (~50 LOC, no pipeline change)

- **F1/G1** (`graph.py:784`): build `node_aabbs = [_LabelPlacement(cx, cy, 2r, 2r) for each visible node]`. Test against in nudge loop: `candidate.overlaps(p) for p in placed_edge_labels + node_aabbs`. +3 lines.
- **E2** (`graph.py:775`): promote constants to module-level.
- **E5/E4** (`graph.py:737`): `sorted(self.edges, key=lambda e: (state_prio(e), edge_key(e)))`.
- **G5** (`graph.py:806`): `lx = max(pill_w/2, min(viewbox_w − pill_w/2, lx))`.
- **F3/E1** (`graph.py:755`): replace `−4` with perp-derived offset `(−perp_y * (pill_h/2 + 2), +perp_x * (pill_h/2 + 2))`.
- **E3** (`graph.py:787`): expand `_LabelPlacement` dims by `+1.0` (stroke width both sides).

### Phase 0.5 — Edge-aligned rotation (~80 LOC, product decision 2026-04-23)

- Compute `θ = atan2(dy_visible, dx_visible)`; normalize to `[-π/2, π/2]` so text never renders upside-down.
- Emit pill group as `<g transform="rotate(θ_deg, mid_x, mid_y)"> <rect…> <text…> </g>` — rect + text rotate together, text remains centred in rect local frame.
- Collision: rotated AABB becomes OBB. Minimum-viable fix: expand AABB to axis-aligned bounding box of rotated rectangle (`w' = |w·cos θ| + |h·sin θ|`, `h' = |w·sin θ| + |h·cos θ|`). Overestimates but deterministic, O(1).
- KaTeX `<foreignObject>` pill path (`_render_svg_text` inline-TeX) requires separate handling — rotate the outer `<g>`, not `<foreignObject>` itself (Safari bug workaround).
- Demo: `examples/fixes/edge_pill_rotated_demo.html` (gitignored) — 3 case visual comparison.
- See `docs/plans/edge-pill-rotation-impl-plan.md` for step-by-step.

### Phase 1 — Foundation (~150 LOC in `graph.py` + ~20 in `_svg_helpers.py`)

- Add `"node_circle"` to `ObstacleKind`, `_KIND_WEIGHT` (`_svg_helpers.py:130,277`).
- `EdgePillContext` frozen dataclass in `graph.py` mirroring `_ScoreContext`.
- Pre-build `node_circle_obstacles` and `edge_segments` tuples.
- On fast-path overlap, invoke `_pick_best_candidate` over 24 candidates.
- Wire P1, P2, P7 at this stage (P3, P6 can land in Phase 2).

### Phase 2 — Full 7-penalty + candidate grid (~100 LOC)

- P3 side-hint auto-inference (cross-product).
- P6 Hirsch preference for edges.
- Expand to full 24 candidates (Phase 1 used slim 12).
- F2 silent-stacking guard: score ≥ 200.0 → R-19 warning in SVG comment.
- F4 coincident-node guard (`edge_len < 4.0` early exit).

### Phase 3 — Leader lines + cross-primitive (~80 LOC)

- R-27c leader line emitter in `graph.py`.
- Thread `placed_labels` from outer `emit_svg` for G4 (interface change with Scene layer).

## Risks & open questions

1. **`_score_candidate` coupling**: requires importing `_ScoreContext` from `_svg_helpers.py` into `graph.py`. New cross-layer dependency — document as explicit design decision.

2. **`"node_circle"` vs `"target_cell"` hard-block path**: `_svg_helpers.py:706` currently only checks `kind == "target_cell"`. Add branch for `"node_circle"` (3 LOC, clean) rather than aliasing.

3. **Parallel edges (multigraph)**: share geometry. Stagger-flip idea (force opposite `side_hint` on second parallel edge) added as O(E) pre-processing with `Counter` over `frozenset({u, v})`. Phase 2.

4. **Performance at K50**: V=50, E=1225. Worst case 1225 × 24 × 1225 = 35M clip calls = 35s. Fast-path short-circuits most. If K50 needed, cull segment obstacles to 3×pill_h spatial neighbourhood (Phase 3 gate). Real scenes cap E≈50.

5. **`_LabelPlacement` stroke inflation (E3)**: expand `width`, `height` by `+1.0` at construction. 1-line fix, Phase 0.

## Test strategy

### Phase 0 (coordinate assertions — fixes T1/T2)

- `test_pill_does_not_overlap_node_circle`: 2-node directed, `d(u,v) = 2r`. Assert `ly − pill_h/2 > cy_node − r` for both endpoints.
- `test_pill_stacking_resolved`: star K1,4. Assert pairwise non-overlapping.
- `test_pill_within_viewbox`: edge near top. Assert `ly − pill_h/2 ≥ 0`.
- `test_sort_order_determinism`: same graph, 2 different edge-add orders. Assert identical SVG strings.

### Phase 1

- `test_node_circle_must_block`: pill natural lands in node AABB → scoring returns `inf` → fallback picks closest non-blocked → coordinate assert.
- `test_edge_line_p7_penalty`: X-shape crossing. Assert pill not centred on crossing (P7 forces off).

### Golden scenes (Phase 2)

- Pin `dinic.html` and `mcmf.html` post-Phase-0. Assert no `scriba-graph-weight` rect AABB intersects any `<circle>` AABB.
- Seed determinism: `random.seed(42)` graph, call `emit_svg` twice, assert identical SVG strings.

### Degenerate (fixes T3)

- `test_coincident_nodes`: `positions[u] == positions[v]`. No crash, finite `x/y`.
- `test_self_loop`: `(u, u)` edge. Pill omitted OR placed at defined offset.

---

## Rotation addendum (2026-04-23)

**Decision:** Keep pill (not plain Graphviz-style text). Add edge-aligned rotation.

**Rationale:** Scriba animates weight values across frames (`\apply` override). Plain-text labels lose readability when edges cross or when weight changes mid-animation. Pill background preserves contrast. Rotating the pill along the edge:
- Binds pill visually to its stroke → easier user mapping on dense/diagonal graphs.
- Pill always parallel to edge → never "cuts across" adjacent edges like a horizontal pill can.
- Solves F3 (vertical-edge `−4` bias wrong) automatically: perp offset now always perpendicular to the stroke in screen space.

**Cost:**
- Collision obstacle: AABB → expanded AABB of rotated rect (OBB). Overestimates occupied area ~30% on diagonal edges; acceptable at E ≤ 50.
- Readability: cartography research (Imhof 1975, Yoeli 1972) shows rotated text is 5–10% slower to read but strongly preferred for association. Acceptable trade.
- KaTeX fallback (`<foreignObject>`): rotate via parent `<g>` only, never on `<foreignObject>` itself (Safari rendering bug).

**Angle normalization rule:**
```
θ_raw = atan2(y2 − y1, x2 − x1)   # in [-π, π]
if θ_raw >  π/2: θ = θ_raw − π
elif θ_raw < -π/2: θ = θ_raw + π
else: θ = θ_raw                    # in [-π/2, π/2]
```

**Scope:** Phase 0.5, after Phase 0 lands. Implementation plan: `docs/plans/edge-pill-rotation-impl-plan.md`.

---

**Key file references for implementation:**
- `scriba/animation/primitives/graph.py` lines 735–838 — placement loop
- `scriba/animation/primitives/_svg_helpers.py`:
  - 103–119 (`_LabelPlacement`)
  - 130–162 (`_Obstacle` / `ObstacleKind`)
  - 277 (`_KIND_WEIGHT`)
  - 683–837 (`_score_candidate` / `_pick_best_candidate`)
  - 874–939 (`_nudge_candidates`)
- `tests/unit/test_graph_mutation.py` 91–167 — augment with coordinate assertions in Phase 0
