# Phase 5 Auto-Expansion Design — GEP v2.0 (U-15)

Date: 2026-04-23
Status: Approved — implementing

## Decisions

### 1. Scope — `Graph` primitive, not `Scene`
Graph owns `positions`, `width`, `height`, `fruchterman_reingold`, node radius, and pill constants. Scene would need to reach into internals. Multi-Graph-per-Scene collision documented as known limitation.

### 2. Opt-in flag
```python
class Graph(PrimitiveBase):
    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        ...,
        "auto_expand",
    })
    def __init__(self, name: str, params: dict[str, Any]) -> None:
        ...
        self.auto_expand: bool = bool(params.get("auto_expand", False))
```
Default `False` preserves backward compat.

### 3. Trigger — inside `emit_svg`, before edge loop
Runs only when `auto_expand=True` AND at least one visible edge has a display weight. Uses an immutable `working_positions` copy — `self.positions` is never mutated across frames.

### 4. Per-edge analytic bound (closed form)
For each edge length `L`, node radius `r`, pill width `pill_w`, rotated AABB width `aabb_w`:

- **Origin fit (k=0):** `s_min_edge = (pill_w + 2r) / L`
- **Along-shift k:** `s_min_edge = (2k·(aabb_w + 2) + pill_w + 4r) / L`

`aabb_w` depends only on edge angle `θ`; scaling preserves angles → formula stable.

`s_min_analytic = max(1.0, max over edges of s_min_edge(k=0))`

Binary search handles pill-pill inter-edge collisions (no closed form).

### 5. Binary search
```
lo = s_min_analytic
hi = min(lo * 1.8, effective_cap)
eps = 0.02
max_iter = 8
while hi - lo > eps and iter < max_iter:
    mid = (lo + hi) / 2
    if _cascade_fallback_count(scale=mid) == 0: hi = mid
    else: lo = mid
return hi  # conservative
```

`_cascade_fallback_count`: pure dry-run of `_nudge_pill_placement` for all visible weighted edges; counts placements with `stage in ("leader", "origin")` reached after cascade exhaustion.

### 6. Canvas clamp
`effective_cap = min(3.0, canvas_bound_scale)` where `canvas_bound_scale` prevents nodes being pushed off-canvas. Hard cap 3.0 protects against degenerate inputs.

### 7. SVG byte impact
Only coordinate digit growth — no structural elements added. Realistic ~2–5%, worst case <15% (meets spec).

### 8. Rollback — no raise
If `s_min > effective_cap`, expand to cap and accept remaining fallbacks. Debug-level log only. GEP-17 leader lines remain correctness floor.

## Module layout

| Path | Purpose |
|------|---------|
| `scriba/animation/primitives/_layout_expand.py` | New. Pure functions: `_min_scale_analytic`, `_cascade_fallback_count`, `_find_min_scale`. |
| `scriba/animation/primitives/graph.py` | Add `auto_expand` param; compute `working_positions` in `emit_svg`. |
| `tests/unit/test_layout_expand.py` | New. 5 tests. |

`_layout_expand.py` imports `_nudge_pill_placement` + `_LabelPlacement` from `graph.py`. Must NOT import `Graph` class (circular risk) — takes primitive data as args.

## API sketches

```python
# _layout_expand.py
def _min_scale_analytic(
    edges: list[tuple[float, float, float, float, float, float]],  # (x1,y1,x2,y2,pill_w,aabb_w)
    node_r: float,
) -> float: ...

def _cascade_fallback_count(
    positions: dict[Any, tuple[float, float]],  # already scaled
    edges_data: list[Any],                       # raw edges w/ weights
    node_r: float,
    directed: bool,
) -> int: ...

def _find_min_scale(
    positions: dict[Any, tuple[float, float]],
    edges_data: list[Any],
    node_r: float,
    directed: bool,
    canvas_w: float,
    canvas_h: float,
) -> float: ...
```

```python
# graph.py helper
def _scaled_positions(
    positions: dict[Any, tuple[float, float]],
    scale: float,
) -> dict[Any, tuple[float, float]]: ...
```

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Per-frame probe cost | 8 iterations × O(E) = fast (<1ms @ E=50). |
| Scale accumulation across frames | Immutable copy; `self.positions` never written. |
| Duplication between `emit_svg` and `_cascade_fallback_count` | Extract `_edge_pill_geometry(edge, node_r)` shared helper. |
| Binary search non-termination | `max_iter=8` + `eps=0.02` hard guard. |
| Multi-Graph scenes | Document in GEP-18; `auto_expand=False` default. |

## Test scope (5 tests)

1. `test_min_scale_per_edge_formula` — hand-computed horizontal + 45° cases.
2. `test_binary_search_converges` — K5 that forces leader at s=1.0; assert s>1.0 and `fallback_count==0` at returned s.
3. `test_auto_expand_opt_in_flag` — default `False` unchanged SVG; `True` on crowded graph removes leader pills.
4. `test_canvas_bound_clamp` — analytic > 3.0 → returns `effective_cap` exactly.
5. `test_dataset_topology_preserved` (U-05) — after `emit_svg(auto_expand=True)`, `graph.edges`, `graph.nodes`, `graph.positions` byte-identical to pre-call.

## GEP-18 spec summary

Normative SHOULD. `Graph(..., auto_expand=True)` triggers pre-emit scale search. Minimum `s ≥ 1.0` such that full cascade resolves without leader/origin fallback. Working-copy scaling; `self.positions` immutable. Cap `min(3.0, canvas_bound)`. GEP-17 remains correctness floor on cap overflow.
