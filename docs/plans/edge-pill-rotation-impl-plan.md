# Edge-Pill Rotation — Implementation Plan

**Date:** 2026-04-23
**Scope:** `scriba/animation/primitives/graph.py` edge-pill emitter (lines 735–841).
**Goal:** Fix F1/G1 CRITICAL bugs, then rotate pill + weight text along edge angle for visual edge→pill association.
**Research bundle:** `docs/archive/graph-edge-pill-optimization-2026-04-23/` (audit, smart-label study, external survey, synthesis).
**Demo (gitignored):** `examples/demos/edge_pill_rotated_demo.html`.

---

## TL;DR

Two small phases, ~130 LOC total, zero new dependencies.

| Phase | LOC | Risk | Fixes |
|-------|-----|------|-------|
| 0  | ~50  | Low | F1/G1 node-circle overlap, E2/E4/E5/G5/E3 |
| 0.5 | ~80  | Low-Med | Pill edge-aligned rotation + OBB-as-AABB collision |

Defer Phase 1+ (full 7-penalty scoring adoption) until both phases ship and regress no goldens.

---

## Phase 0 — Incremental fixes (~50 LOC, no pipeline change)

### Goal
Close the two CRITICAL bugs (F1 + G1) and the determinism issues (E4/E5) with the smallest viable diff. No scoring pipeline. No rotation yet.

### Changes (`scriba/animation/primitives/graph.py`)

**0.A. Promote pill constants to module level** (fixes E2)

Above class `Graph`, add:
```python
_WEIGHT_FONT: int = 11
_WEIGHT_PILL_PAD_X: int = 5
_WEIGHT_PILL_PAD_Y: int = 2
_WEIGHT_PILL_R: int = 3
```
Remove the re-declarations inside the `if display_weight is not None:` block (lines 775–778).

**0.B. Deterministic edge ordering** (fixes E4, E5)

Replace `for u, v, weight in self.edges:` (line 737) with:
```python
_STATE_PRIO: dict[str, int] = {
    "current": 0, "highlighted": 1, "active": 2, "idle": 3, "muted": 4
}
def _edge_sort_key(edge: tuple) -> tuple[int, str]:
    u, v, _ = edge
    state = self.get_state(self._edge_key(u, v))
    return (_STATE_PRIO.get(state, 99), self._edge_key(u, v))
for u, v, weight in sorted(self.edges, key=_edge_sort_key):
```

**0.C. Node-circle obstacle list** (fixes F1, G1)

Before the edge loop (after line 735):
```python
node_aabbs: list[_LabelPlacement] = [
    _LabelPlacement(
        x=self.positions[n][0],
        y=self.positions[n][1],
        width=2 * self._node_radius,
        height=2 * self._node_radius,
    )
    for n in self.nodes
    if n not in hidden_nodes
]
```
Update the nudge guard (line 803):
```python
if not any(candidate.overlaps(p) for p in placed_edge_labels) \
   and not any(candidate.overlaps(n) for n in node_aabbs):
    break
```

**0.D. Stage-boundary clamp** (fixes G5)

After the nudge loop, before `placed_edge_labels.append(candidate)` (line 811):
```python
lx = max(pill_w / 2, min(self._viewbox_width - pill_w / 2, lx))
ly = max(pill_h / 2, min(self._viewbox_height - pill_h / 2, ly))
candidate = _LabelPlacement(x=lx, y=ly, width=pill_w, height=pill_h)
```
(Requires verifying `_viewbox_width/_viewbox_height` exist on `Graph` — if not, derive from `self.width`, `self.height`.)

**0.E. Perp-derived y-bias** (fixes F3, E1)

Replace line 755:
```python
mid_x = (x1 + x2) / 2
mid_y = (y1 + y2) / 2
```
After computing `perp_x, perp_y` (around line 795) but before the nudge loop, set the initial candidate position using perp-offset:
```python
_bias = _WEIGHT_PILL_R + 2    # 5 px
lx = mid_x + perp_x * _bias
ly = mid_y + perp_y * _bias
candidate = _LabelPlacement(x=lx, y=ly, width=pill_w, height=pill_h)
```
Removes magic `-4`; offset now always perpendicular to the stroke.

**0.F. Stroke-width AABB inflation** (fixes E3)

In `_LabelPlacement` usages for pills, construct with `width=pill_w + 1.0, height=pill_h + 1.0` (0.5 stroke on each side). Do **not** inflate node AABB — node stroke already fits inside `2r`.

### Tests (`tests/unit/test_graph_mutation.py`)

Add four tests (fixes T1–T4):

1. `test_pill_does_not_overlap_node_circle` — 2-node directed, `d(u,v) = 2r`. Assert pill rect y+h/2 ≤ node cy − r **or** pill rect y − h/2 ≥ node cy + r.
2. `test_pill_stacking_resolved_on_star` — K1,4 star. Extract pill AABBs from SVG, assert pairwise non-overlap.
3. `test_pill_within_viewbox` — edge touching top. Assert pill rect `y ≥ 0`.
4. `test_edge_sort_determinism` — 3-node graph built with two different `add_edge` orders. Assert identical SVG output.

### Golden regen

Regenerate `examples/demos/dinic.html`, `examples/demos/mcmf.html` via `build.sh`. Manually verify in browser that pill no longer overlaps any node circle. Commit the new SHAs.

### Acceptance

- [ ] All Phase 0 tests pass.
- [ ] `pytest tests/unit/test_graph_mutation.py tests/unit/test_scoring_regression.py -q` green.
- [ ] `dinic.html` + `mcmf.html` visually clean (no pill-on-circle in any frame).
- [ ] SVG output byte-stable across two runs on same fixture.

---

## Phase 0.5 — Edge-aligned rotation (~80 LOC)

### Goal
Pill rectangle + weight text rotate to match edge angle, making pill→edge association obvious on diagonal/dense graphs. Text remains upright (never upside-down).

### Prerequisite
Phase 0 merged.

### Design decisions

1. **Rotation pivot = visible-segment midpoint.** Same `(mid_x, mid_y)` used for pill centre. Rotation around pivot leaves pill centered on the stroke centerline (pre-perp-offset).

2. **Text upright rule.** Normalise `θ = atan2(dy_visible, dx_visible)` into `[-π/2, π/2]`:
   ```python
   θ = math.atan2(dy, dx)
   if θ > math.pi / 2:
       θ -= math.pi
   elif θ < -math.pi / 2:
       θ += math.pi
   ```
   Vertical edges (`θ = ±π/2`) stay at `π/2` → text reads top-to-bottom on the left side. Acceptable — follows Imhof cartography convention.

3. **Apply rotation to the pill group, not individual elements.**
   ```xml
   <g transform="rotate(θ_deg, mid_x, mid_y)">
     <rect x=… y=… width=… height=… …/>
     <text x=mid_x+perp_off_x y=mid_y+perp_off_y …>12</text>
   </g>
   ```
   Perp offset is applied **before** rotation — in local frame, perp becomes pure y-offset after rotation.

4. **Simplification:** when pill is centered with perp offset already applied, rotation around `(mid_x, mid_y)` moves both rect and text coherently. No need for per-element transforms.

5. **Collision obstacle becomes OBB.** Minimum-viable approach: expand rotated-rect AABB:
   ```python
   abs_cos = abs(math.cos(θ))
   abs_sin = abs(math.sin(θ))
   aabb_w = pill_w * abs_cos + pill_h * abs_sin
   aabb_h = pill_w * abs_sin + pill_h * abs_cos
   candidate = _LabelPlacement(x=lx, y=ly, width=aabb_w, height=aabb_h)
   ```
   Overestimates true footprint by up to √2 on 45° edges — acceptable false-positive rate at E ≤ 50. True OBB-OBB test deferred to Phase 1.

6. **KaTeX `<foreignObject>` path.** `_render_svg_text` falls back to `<foreignObject>` for inline-TeX. The rotate transform must sit on the **outer `<g>`**, not the `<foreignObject>` itself — Safari has a known `<foreignObject>` + `transform` rendering bug. Confirm via `render_inline_tex` branch.

### Changes (`scriba/animation/primitives/graph.py`)

**0.5.A. Compute rotation angle** — right after computing `dx_edge`, `dy_edge`, `edge_len` (line 792):
```python
_raw_theta = math.atan2(dy_edge, dx_edge)
if _raw_theta > math.pi / 2:
    theta = _raw_theta - math.pi
elif _raw_theta < -math.pi / 2:
    theta = _raw_theta + math.pi
else:
    theta = _raw_theta
theta_deg = math.degrees(theta)
```

**0.5.B. Rotate collision AABB**
Replace AABB construction:
```python
abs_cos = abs(math.cos(theta))
abs_sin = abs(math.sin(theta))
aabb_w = pill_w * abs_cos + pill_h * abs_sin + 1.0   # +1 stroke
aabb_h = pill_w * abs_sin + pill_h * abs_cos + 1.0
candidate = _LabelPlacement(x=lx, y=ly, width=aabb_w, height=aabb_h)
```
Nudge loop reuses this expanded AABB.

**0.5.C. Emit rotated pill group**
Replace current pill + text emission (lines 814–828) with:
```python
pill_rx = lx - pill_w / 2
pill_ry = ly - pill_h / 2
weight_text = (
    f'<g transform="rotate({theta_deg:.2f} {lx:.1f} {ly:.1f})">'
    f'<rect x="{pill_rx:.1f}" y="{pill_ry:.1f}" '
    f'width="{pill_w}" height="{pill_h}" '
    f'rx="{_WEIGHT_PILL_R}" fill="white" fill-opacity="0.85" '
    f'stroke="{THEME["border"]}" stroke-width="0.5"/>'
    + _render_svg_text(
        display_weight, lx, ly,
        fill=THEME["fg_muted"],
        text_anchor="middle",
        dominant_baseline="central",
        css_class="scriba-graph-weight",
        render_inline_tex=render_inline_tex,
    )
    + "</g>"
)
```
Text `(x, y) = (lx, ly)` pre-rotation coincides with pill centre — after rotate, both rotate as a unit.

**0.5.D. Guard for short edges**
If `edge_len < 4.0`, skip rotation (fall back to horizontal pill):
```python
if edge_len < 4.0:
    theta_deg = 0.0
    aabb_w, aabb_h = pill_w + 1.0, pill_h + 1.0
```

### Tests

Add to `tests/unit/test_graph_mutation.py`:

1. `test_pill_rotation_angle_horizontal_edge` — B(0,0)→C(100,0) directed. Parse SVG, extract `transform="rotate(θ …)"`. Assert `θ == 0`.
2. `test_pill_rotation_angle_45deg` — B(0,0)→C(100,100). Assert `θ == 45.0` (±0.01).
3. `test_pill_rotation_normalized_uphill` — B(100,100)→C(0,0). Raw `atan2` would be 135°; assert rotated `θ == -45.0` (normalized into upright range).
4. `test_pill_rotation_vertical_edge` — B(50,0)→C(50,100). Assert `θ == 90.0` (boundary case; stays at 90).
5. `test_rotated_pill_aabb_diagonal_no_node_overlap` — short 45° edge. Assert rotated AABB still excludes node circles.
6. `test_rotated_pill_with_katex` — weight = `"$\\sqrt{2}$"`, directed 30° edge. Parse SVG, assert `<foreignObject>` is inside a `<g transform="rotate(...)">`, NOT wrapping it.

### Golden regen

Regenerate `examples/demos/dinic.html`, `examples/demos/mcmf.html`, `examples/demos/maxflow.html`. SVG hash WILL change (rotation transform on every pill). Update golden SHAs in CHANGELOG.

### Acceptance

- [ ] Phase 0.5 tests pass.
- [ ] Opening `dinic.html` in browser: pills visibly tilted along their edges.
- [ ] No pill text appears upside-down in any of the three example files.
- [ ] No regression in `pytest` suite.

---

## Phase 1+ deferral

Phase 1 (24-candidate scoring, `EdgePillContext`, P1–P7) and Phase 2/3 (leader lines, cross-primitive obstacles) remain as planned in `04-synthesis.md`. Revisit only if rotated-AABB overestimation causes visible over-nudging on real scenes. Expected: K8 graphs with many crossing edges might show false-positive collisions → trigger nudge when true OBB would clear. Measure first before escalating.

---

## Risks

1. **AABB overestimation at 45°**: expanded width = `pill_w · √2/2 + pill_h · √2/2 ≈ 0.707·(pill_w + pill_h)`. For typical `pill_w = 30, pill_h = 18`: AABB ≈ 34×34 vs true OBB ≈ 30×18. ~47% area overestimate on diagonals. At E≤10 (typical scenes), collision rate stays low. Mitigation: if regressions observed, upgrade to OBB-OBB check via separating-axis theorem in Phase 1.

2. **`<foreignObject>` + rotate rendering**: Safari `<foreignObject>` inside a rotated `<g>` historically had sub-pixel snap issues. Test on Safari before shipping. Fallback: disable rotation when `render_inline_tex` path is active AND contains `$…$` tokens.

3. **SVG byte stability across browsers**: `rotate(θ 0 0)` rendering identical on Chrome/Firefox/Safari. Verified by E2E screenshot diff during Phase 0.5 acceptance.

4. **Goldens**: every existing `*.html` with an edge-pill regenerates. Plan to land Phase 0 + Phase 0.5 in two separate commits so goldens diff is reviewable.

---

## Rollout sequence

1. Land Phase 0 (one commit) → regen goldens → merge.
2. Land Phase 0.5 (one commit) → regen goldens → merge.
3. Document final state in `docs/archive/graph-edge-pill-logic-<date>.md` (supersedes 2026-04-23 file).
4. Update `AGENTS.md` / primitives spec if public shape changes (it should not — rotation is purely visual).

---

## File checklist

| File | Phase 0 | Phase 0.5 |
|------|---------|-----------|
| `scriba/animation/primitives/graph.py` | edit (~50 LOC) | edit (~80 LOC) |
| `tests/unit/test_graph_mutation.py` | +4 tests | +6 tests |
| `examples/demos/dinic.html` | regen | regen |
| `examples/demos/mcmf.html` | regen | regen |
| `examples/demos/maxflow.html` | regen | regen |
| `CHANGELOG.md` | entry | entry |
| `docs/archive/graph-edge-pill-logic-<date>.md` | — | new file supersedes 2026-04-23 |

---

## Symbols touched (for `gitnexus_impact`)

Run before each phase:
```
gitnexus_impact target: "Graph.emit_svg" direction: "upstream"
gitnexus_impact target: "_LabelPlacement" direction: "upstream"
```
Expected blast radius: scene renderer + golden tests. No upstream API change.
