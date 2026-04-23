# GEP v2.0 — Implementation Plan

**Date**: 2026-04-23
**Source research**: `docs/archive/graph-edge-pill-ultra-cascade-2026-04-23/`
**Baseline**: GEP v1.2 (commit `2c389bd`) — along-shift cascade, 50→80% on-stroke on K5
**Target**: 100% overlap-free, pedagogical clarity, tuân thủ U-01..U-15

> Ghi chú: phases ordered theo risk (low→high). Mỗi phase ship riêng, có roll-back path.
> User rules tham chiếu: [`docs/archive/graph-edge-pill-ultra-cascade-2026-04-23/user-rules.md`](../archive/graph-edge-pill-ultra-cascade-2026-04-23/user-rules.md)

---

## Phase 1 — Option 5 saturate probe (U-11) · 2 agents

**Goal**: Insert stage 1.5 vào cascade: thử pill tại `±budget` exact trước khi rơi xuống perp.

**Rules enforced**: U-04, U-08, U-09, U-11, U-14

**Agents**:

| Agent | Role | Deliverable |
|-------|------|-------------|
| 1. tdd-guide | Write failing tests first | 4 tests in `tests/unit/test_graph_mutation.py`: `test_saturate_resolves_hair_thin_collision`, `test_saturate_respects_budget_zero`, `test_saturate_on_stroke_invariant` (U-14), `test_saturate_deterministic` (U-06) |
| 2. general-purpose | Implement saturate stage | Edit `_nudge_pill_placement` in `scriba/animation/primitives/graph.py`: insert `_try_saturate()` helper between along-shift loop và perp loop. Update `docs/spec/graph-edge-pill-ruleset.md` với GEP-14 entry. |

**Files touched**: `graph.py`, `test_graph_mutation.py`, `graph-edge-pill-ruleset.md`

**Exit criteria**:
- All tests pass
- Golden regen cho `examples/maxflow.html` (D→T edge) shows pill on-stroke không fallback
- `gitnexus_impact` < MEDIUM risk

---

## Phase 2 — Option 2 side-preferred perp (U-10) · 2 agents

**Goal**: Reorder perp candidates từ `[+s,-s,+2s,-2s]` thành `[+s,+2s,-s,-2s]` — ưu tiên một bên trước khi đổi bên. Anti-flicker.

**Rules enforced**: U-06, U-10

**Agents**:

| Agent | Role | Deliverable |
|-------|------|-------------|
| 1. tdd-guide | Add determinism tests | `test_perp_side_preferred_order`, `test_perp_no_flicker_rerun` (run cascade 2× → same output) |
| 2. general-purpose | Reorder + deterministic choice of initial side | Edit perp loop ordering; tiebreak initial side theo global convention (e.g., right-hand side of edge direction) |

**Files touched**: `graph.py`, `test_graph_mutation.py`, `graph-edge-pill-ruleset.md` (GEP-15)

**Exit criteria**: S→B và S→C pills trên K5 same-side thay vì opposite-side.

---

## Phase 3 — U-14 enforcement (on-stroke invariant) · 3 agents

**Goal**: Add invariant check đảm bảo pill center nằm trên stroke (origin/along/sat stages) — chống drift do future refactor.

**Rules enforced**: U-04, U-14

**Agents**:

| Agent | Role | Deliverable |
|-------|------|-------------|
| 1. tdd-guide | Property-based test | `test_on_stroke_invariant_hypothesis` — cho 100 random graphs, tất cả pills stage ∈ {origin, along, sat} phải có `point_to_line_distance(pill_center, edge) < 0.5` |
| 2. general-purpose | Add runtime assert | Add `_assert_on_stroke(pill, edge, stage)` helper; call sau mỗi stage placement trong dev mode (via `SCRIBA_DEBUG=1` env) |
| 3. python-reviewer | Review for perf cost | Ensure assert chỉ chạy debug mode, không overhead production |

**Files touched**: `graph.py`, `_svg_helpers.py`, `test_graph_mutation.py`, `graph-edge-pill-ruleset.md` (GEP-16)

**Exit criteria**: Property test pass trên hypothesis 100 samples; golden tests unchanged.

---

## Phase 4 — Leader-line fallback (U-04 last resort) · 4 agents

**Goal**: Thay origin-fallback bằng leader line. Khi cascade exhaust → pill off-stroke với dashed leader back to midpoint.

**Rules enforced**: U-01, U-02, U-04

**Agents**:

| Agent | Role | Deliverable |
|-------|------|-------------|
| 1. architect | Design leader emission | Spec ra: leader SVG element structure, z-order (leader below node, pill above), offset direction (outward from graph centroid), min leader length |
| 2. tdd-guide | Write tests | `test_leader_emitted_on_exhaust`, `test_leader_direction_outward`, `test_leader_pill_rotation_preserved` (U-01 phải giữ) |
| 3. general-purpose | Impl leader emission | New `_emit_leader_line(pill, edge, graph_centroid)` trong `_svg_helpers.py`; update `_nudge_pill_placement` return type thêm `leader: bool` |
| 4. doc-updater | Update spec | GEP-17 trong `graph-edge-pill-ruleset.md`; visual example in `docs/spec/primitives.md` |

**Files touched**: `graph.py`, `_svg_helpers.py`, `test_graph_mutation.py`, `graph-edge-pill-ruleset.md`, `primitives.md`

**Exit criteria**: K5 A→C, B→T pills có leader line; `examples/maxflow.html` regen clean.

---

## Phase 5 — U-15 auto-expansion · 5 agents (biggest phase)

**Goal**: Layout-level change. Trước khi render, compute min-scale và expand node positions nếu cần.

**Rules enforced**: U-05 (dataset-preserving — chỉ scale, không relocate), U-15

**Agents**:

| Agent | Role | Deliverable |
|-------|------|-------------|
| 1. architect | Design pre-layout phase | Scope: scale area là Scene hay Graph primitive? Bao giờ trigger (opt-in flag vs auto)? Clamp max scale để không blow canvas? |
| 2. general-purpose | Impl per-edge analytic bound | `_min_scale_per_edge(edges, node_r)` trả về `s_min_analytic`. Pure function, test riêng. |
| 3. general-purpose | Impl binary search wrapper | `_find_min_scale(graph)` chạy cascade trial ở mid scale, iterate đến fallback=0. Bound iterations 8. |
| 4. tdd-guide | Tests | `test_min_scale_per_edge_formula`, `test_binary_search_converges`, `test_auto_expand_opt_in_flag`, `test_canvas_bound_clamp`, `test_dataset_topology_preserved` (U-05: chỉ positions scale, edges không đổi) |
| 5. python-reviewer + doc-updater | Review + docs | Perf audit (expansion có tăng SVG bytes bao nhiêu); GEP-18 spec entry; migration note cho callers |

**Files touched**: `scriba/animation/primitives/graph.py`, `scriba/animation/scene.py` (possibly), new `scriba/animation/primitives/_layout_expand.py`, tests, spec

**Exit criteria**:
- Opt-in flag `auto_expand=True` làm K5 đạt 100% on-stroke
- Opt-out giữ behavior hiện tại
- SVG bytes increase < 15% worst case

---

## Phase 6 — Typography + color tint (visual polish) · 2 agents

**Goal**: Bold primary / dim secondary split trên "X/Y" labels; pill bg tint theo source node color.

**Rules enforced**: U-03 (clarity)

**Agents**:

| Agent | Role | Deliverable |
|-------|------|-------------|
| 1. general-purpose | Impl tspan split + tint | `_render_split_label(label)` parse "X/Y" → emit `<tspan>` hierarchy; add `src_color` param tới `_emit_label_and_pill` |
| 2. tdd-guide | Visual regression goldens | Regen + sign off `examples/*.svg`; snapshot test for tspan structure |

**Files touched**: `_svg_helpers.py`, golden SVGs, tests

**Exit criteria**: Maxflow/mcmf/dinic examples render với hierarchy; goldens updated.

---

## Phase 7 — Global SA pass (optional, gated) · 3 agents

**Goal**: Post-cascade simulated annealing cho dense graphs. Opt-in via `global_optimize=True`.

**Rules enforced**: U-01 (θ locked), U-06 (seeded), U-14 (on-stroke lock)

**Agents**:

| Agent | Role | Deliverable |
|-------|------|-------------|
| 1. architect | Decide scope | Justify SA vs cheaper alternatives. Pin budget (iterations × cost). Decide: per-Scene opt-in hay Scene-level heuristic auto-enable? |
| 2. general-purpose | Impl SA + energy + on-stroke lock | `_simulated_annealing_refine(pills, edges, nodes, seed=42)`. Energy: `Σ overlap² + dist_from_origin·w`. Lock `perp_delta=0` cho on-stroke pills. |
| 3. python-reviewer | Perf + determinism audit | Benchmark 50-edge graph <200ms; same seed → bit-identical output |

**Files touched**: new `scriba/animation/primitives/_pill_refine.py`, tests, spec (GEP-19)

**Exit criteria**: Opt-in gated; off by default; when on reduces residual perp count by ≥50% vs cascade-only.

---

## Summary

| Phase | Agents | Rules | Risk | Ship order |
|-------|-------:|-------|------|-----------|
| 1 | 2 | U-11 | LOW | First |
| 2 | 2 | U-10 | LOW | Second |
| 3 | 3 | U-14 | LOW | Third |
| 4 | 4 | U-04 leader | MEDIUM | Fourth |
| 5 | 5 | U-15 expand | HIGH | Fifth |
| 6 | 2 | U-03 typo | LOW | Parallel with 4–5 |
| 7 | 3 | SA | MEDIUM | Optional / last |

**Total**: 21 agent-slots across 7 phases.
**Parallelizable pairs**: (1,2), (3,6), (4,6). Không parallel (5) vì layout-level.
**Version bumps**:
- Phase 1–3 → GEP v1.3 (minor, backward-compat)
- Phase 4 → GEP v1.4 (new SVG output)
- Phase 5 → GEP v2.0 (breaking: auto_expand default behavior TBD)
- Phase 6 → GEP v2.0-ux (with 5) or v1.3-ux (standalone)
- Phase 7 → GEP v2.1 (opt-in)

## Acceptance criteria (end state, all phases merged)

- [ ] K5 hard case 100% on-stroke hoặc leader (0 silent fallback)
- [ ] Deterministic: same input → byte-identical SVG
- [ ] U-01..U-15 all enforced
- [ ] Existing examples (`maxflow.html`, `mcmf.html`, `dinic.html`) visual diff reviewed + accepted
- [ ] No regression trên non-graph primitives (smart-label / Plane2D / Queue)
- [ ] SVG byte increase < 15% worst case
- [ ] Docs: `graph-edge-pill-ruleset.md` v2.0, README plans linked
