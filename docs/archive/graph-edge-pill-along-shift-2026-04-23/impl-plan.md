# GEP v1.2 — Along-Edge Shift Impl Plan

**Date:** 2026-04-23
**Author:** Edge-pill placement task (iter 3)
**Supersedes:** GEP v1.1 nudge logic (commit `b80e77c`)
**Status:** Planned — not yet implemented
**Related spec:** `docs/spec/graph-edge-pill-ruleset.md` (will bump to v1.2)
**Related archive:** `docs/archive/graph-edge-pill-optimization-2026-04-23/`

---

## TL;DR

v1.1 solved **wrong-side commits** but couldn't avoid **pill detachment** on
crossing edges (B→D in `mcmf.html` ended up 19 px off its stroke).

v1.2 replaces the 1-dimensional perpendicular nudge with a **2-stage shift**:

1. **Along-edge shift first** — pill slides DOWN the stroke (still ON the
   edge) to escape a neighbouring pill. Preserves GEP-10 edge binding.
2. **Perp nudge as fallback** — only when along-shift is blocked by a node
   AABB or by running out of visible segment.

Result: pills stay centered on edges whenever geometrically possible, which
is the original user intent behind the rotation decision.

---

## Motivation — what v1.1 left broken

After commit `b80e77c` (v1.1), re-measuring `examples/mcmf.html`:

| Edge | Mid        | Pill        | Δalong | Δperp  | Reason                    |
|------|------------|-------------|--------|--------|---------------------------|
| A→C  | (199.0, 131.5) | (199.0, 131.5) | 0      | 0      | on-edge, no collision     |
| B→D  | (194.5, 144.0) | (201.6, 164.3) | −10.08 | **−19.00** | nudged: on-edge collided with A→C pill |

Why A→C and B→D collided on-edge:

- A→C edge mid = (199.0, 131.5)
- B→D edge mid = (194.5, 144.0)
- Screen distance between midpoints = **13.3 px**
- Pill AABB = 17 × 17
- AABB overlap area = 77 px² ≈ **19 % of pill area**

v1.1 fired the nudge on any non-zero overlap. B→D got pushed perpendicular
by `-nudge_step = -19`, landing 19 px below its visible stroke. User: "B→D
vẫn bị lệch."

**Root cause:** crossing edges in dense graphs naturally produce near-coincident
midpoints. Perp nudge resolves the overlap but detaches the pill.

---

## Design — along-edge shift

Every edge provides two axes to maneuver on:

- **Perp axis** — v1.1 used this; breaks GEP-10 binding
- **Along axis** — pill slides along stroke; preserves GEP-10 binding and
  reads like Graphviz/dot

Shifting pill by `Δ` along the edge unit vector:
```
lx = mid_x + ux * Δ
ly = mid_y + uy * Δ
```
Pill remains on the edge stroke. Rotation angle is unchanged (still aligned
with edge direction). The user's perceptual mapping (pill → edge) is
preserved.

### Why this works for B→D

B→D edge from B=(293, 159) to D=(96, 129), `u = (−0.89, −0.136)`.
Shifting by `Δ = +15` along `u`:
```
new_center = (194.5 - 0.89*15, 144.0 - 0.136*15) = (181.2, 142.0)
```
Screen distance to A→C pill (199, 131.5):
```
|Δx|=17.8 > pill_w=17 → AABB overlap = 0 on X axis → CLEAR
```
Pill now on stroke, 13 px along-edge away from the crossing.

### Shift budget

Pill must not:

1. Pass the visible-segment endpoint (would overlap node AABB).
2. Escape the canvas.

Budget: half the visible segment minus half-pill-width.
```
max_shift = max(0, (edge_len_visible / 2) - (pill_w / 2) - _NODE_RADIUS)
```
For B→D: `(199 / 2) - (17 / 2) - 20 = 99.5 - 8.5 - 20 = 71 px`. Plenty.
For short edges (e.g. 50 px total, node_r=20): `25 - 8.5 - 20 = -3.5 → 0`
→ along-shift disabled, falls through to perp nudge. That's the correct
degradation.

---

## Updated nudge protocol (GEP-07 v1.2)

```python
# Pseudocode — see §Implementation for actual diff
step_along = pill_w + 2
step_perp  = pill_h + 2
max_shift  = max(0, edge_len_visible / 2 - pill_w / 2 - _NODE_RADIUS)

# 0. On-edge origin
candidate = on_edge_midpoint()
if not collides(candidate):
    commit(candidate); return

# 1. Along-edge shifts (bounded by visible-segment budget)
for delta in (+step_along, -step_along, +2*step_along, -2*step_along):
    if abs(delta) > max_shift: continue
    candidate = shift_along(delta)
    if not collides(candidate):
        commit(candidate); return

# 2. Perp nudge fallback (v1.1 logic)
for delta in (+step_perp, -step_perp, +2*step_perp, -2*step_perp):
    candidate = shift_perp(delta)
    if not collides(candidate):
        commit(candidate); return

# 3. Origin fallback — touching beats detached
commit(on_edge_midpoint())
```

### Why along-first, perp-fallback?

- Along-shift preserves GEP-10 binding (pill rotates with edge, stays on
  stroke).
- Perp nudge is a last-resort for edges too short to maneuver (coincident
  or near-coincident midpoints with no along-budget).
- On a degenerate edge (`edge_len < _WEIGHT_EDGE_MIN_LEN`), GEP-11 already
  forces `theta=0` and `max_shift=0` → perp nudge kicks in, same as v1.1.

---

## Implementation (~30 LOC)

**File:** `scriba/animation/primitives/graph.py` (~line 860 region,
inside `Graph.emit_svg`, post-perp-vector computation).

**Diff sketch:**

```python
# GEP-07 v1.2: along-edge shift first, perp nudge as fallback.
# Preserves GEP-10 edge binding: pill stays on stroke when along-budget
# allows. Falls through to perpendicular only when the visible segment is
# too short to slide.
nudge_step_along = pill_w + 2
nudge_step_perp  = pill_h + 2
max_shift_along  = max(
    0.0,
    edge_len / 2 - pill_w / 2 - self._node_radius,
)
origin_lx, origin_ly = lx, ly

def _collides(c: _LabelPlacement) -> bool:
    return any(c.overlaps(p) for p in placed_edge_labels) or any(
        c.overlaps(n) for n in node_aabbs
    )

if _collides(candidate):
    resolved = False

    # Stage 1 — along-edge shift (preserves GEP-10 binding).
    along_offsets = (
        nudge_step_along,
        -nudge_step_along,
        2 * nudge_step_along,
        -2 * nudge_step_along,
    )
    ux = dx_edge / edge_len
    uy = dy_edge / edge_len
    for offset in along_offsets:
        if abs(offset) > max_shift_along:
            continue
        trial_lx = origin_lx + ux * offset
        trial_ly = origin_ly + uy * offset
        trial = _LabelPlacement(
            x=trial_lx, y=trial_ly, width=aabb_w, height=aabb_h
        )
        if not _collides(trial):
            lx, ly, candidate = trial_lx, trial_ly, trial
            resolved = True
            break

    # Stage 2 — perp nudge fallback (v1.1 behaviour).
    if not resolved:
        perp_offsets = (
            nudge_step_perp,
            -nudge_step_perp,
            2 * nudge_step_perp,
            -2 * nudge_step_perp,
        )
        for offset in perp_offsets:
            trial_lx = origin_lx + perp_x * offset
            trial_ly = origin_ly + perp_y * offset
            trial = _LabelPlacement(
                x=trial_lx, y=trial_ly, width=aabb_w, height=aabb_h
            )
            if not _collides(trial):
                lx, ly, candidate = trial_lx, trial_ly, trial
                resolved = True
                break

    # Stage 3 — origin fallback.
    if not resolved:
        lx, ly = origin_lx, origin_ly
        candidate = _LabelPlacement(
            x=lx, y=ly, width=aabb_w, height=aabb_h
        )
```

**Touched symbols:** `Graph.emit_svg` — pill placement block only. No
constants added/removed. No API surface change.

---

## Tests

### Unit

`tests/unit/test_graph_mutation.py` (extend):

1. `test_crossing_edges_resolved_by_along_shift`
   - Set up 2 edges whose midpoints are within `pill_w` on screen
     (B→D / A→C mcmf-like geometry).
   - Assert both pills have `Δperp < 1.0` (on stroke) and
     `|Δalong| >= step_along` (shifted apart).

2. `test_along_shift_respects_node_budget`
   - Short edge (`edge_len < 2 * node_r + pill_w`).
   - Force collision via a neighbouring pill.
   - Assert pill falls through to perp nudge (not jammed into node AABB).

3. `test_along_shift_never_overlaps_node_circle`
   - K5 layout (dense). Assert no pill AABB overlaps any `node_aabbs`.

4. `test_origin_fallback_on_all_collisions`
   - Contrived scene where every along + perp probe collides.
   - Assert pill lands at origin (on-edge midpoint), not at last-tried.

### Integration

- `examples/mcmf.html` regeneration: re-measure B→D and A→C. Both should
  be at `Δperp ≈ 0`, with `|Δalong|` non-zero for the nudged pill.
- `examples/dinic.html`, `examples/maxflow.html`: no regressions on
  currently-on-edge pills.

### Property (deferred)

A hypothesis test generating random graphs with controlled midpoint
spacing would strengthen GEP-07.4 (origin-fallback invariant). Not
required for v1.2 acceptance — can ship in Phase 1.

---

## Risks

1. **Shift picks the "wrong" endpoint side** — pill might slide toward
   source when toward target reads better (e.g. if the target side has
   more whitespace). Mitigation: the alternating order `(+, −, +2, −2)`
   tries both sides with equal priority; scoring would be Phase 1.

2. **Two pills on parallel short edges both want to shift toward same
   spot** — GEP-05 determinism ensures deterministic resolution order, so
   the outcome is stable, but not necessarily optimal. Measure on K5 /
   K6. Phase 1 scoring fixes this; not blocking for v1.2.

3. **Edge length jitter across frames** — if `edge_len` changes between
   animation frames (nodes move), `max_shift_along` changes, and the
   pill may re-select a different stage. Mitigation: in `scriba` all
   graph layouts are stable across frames (verified by
   `test_mcmf_six_nodes_stable_across_frames`), so `edge_len` is
   per-frame-constant within a stable layout. Jitter risk is bounded.

4. **Tests that assert exact perp=0 on placed pills** — none currently
   exist because v1.0/v1.1 never produced that invariant. Safe.

---

## Rollout sequence

1. Implement diff in `graph.py`.
2. Add 4 unit tests above.
3. Run full `pytest tests/unit` → expect 2443 + 4 passing.
4. Regenerate `examples/{mcmf,dinic,maxflow}.html`.
5. Measure B→D: assert `Δperp < 1.0` post-shift.
6. Bump spec to v1.2 (GEP-07 rewrite, new §Version entry).
7. Commit:
   `fix(graph-edge-pill): GEP v1.2 — along-edge shift preserves on-stroke placement`

---

## File checklist

| File | Change |
|------|--------|
| `scriba/animation/primitives/graph.py` | edit ~30 LOC (nudge protocol) |
| `tests/unit/test_graph_mutation.py` | +4 tests |
| `docs/spec/graph-edge-pill-ruleset.md` | GEP-07 rewrite, v1.2 history entry |
| `examples/mcmf.html` | regen |
| `examples/dinic.html` | regen |
| `examples/maxflow.html` | regen |
| `docs/archive/graph-edge-pill-along-shift-2026-04-23/impl-plan.md` | this file |

---

## Open questions

- Should along-shift probe order be `(+, −, +2, −2)` (current plan) or
  `(+, +2, −, −2)` (prefer one side)? Alternation gives both sides equal
  chance; prefer-one-side gives visual consistency. **Decision: keep
  alternating** — simpler, no bias.

- Should perp-fallback step size be `pill_h + 2` (v1.1 value) or larger?
  v1.1 value is fine — fallback is rare (only short-edge cases), and
  perp already guarantees no overlap at that distance.

---

## Version mapping

| GEP spec | Nudge behavior                                          | Commit       |
|----------|---------------------------------------------------------|--------------|
| v1.0     | perp-only, 2 attempts, commits last candidate           | `4dda2a0`    |
| v1.1     | perp-only, 4 probes, origin fallback, no failed commit  | `b80e77c`    |
| v1.2     | **along-shift first, perp fallback, origin fallback**   | _(this plan)_ |
