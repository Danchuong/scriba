# Leader-Line Logic

**Version**: v0.15.0
**Scope**: annotation-arrow leader-line emission in `emit_arrow_svg`
**Source**: `scriba/animation/primitives/_svg_helpers.py` (`_emit_label_and_pill`, `_line_rect_intersection`)
**Related rules**: R-07, R-08, R-27c (see `docs/spec/smart-label-ruleset.md`); R-27 and R-27b superseded in v0.15.0

---

## Purpose

A **leader line** is a thin dashed/solid polyline connecting the arrow curve to the annotation pill when the pill has been nudged away from its natural anchor by the collision-avoidance pipeline. It restores the visual binding between pill and arrow after placement.

Visual anatomy:

```
           ┌──────────────┐
           │  +cost       │  ← pill (AABB, rounded rect)
           └──────▲───────┘
                  │  polyline (R-08: perimeter endpoint)
                  │
              ●─ curve_mid = B(0.5)   ← dot anchor on the arrow curve
             /
          ╭─╯
    arrow path  →  dst
```

---

## Pipeline

```
1. Compute curve_mid       (arc B(0.5), NamedTuple ArrowGeometry)
2. Pick pill position      (_pick_best_candidate over natural + 32 nudges)
3. Measure visual_gap      (‖pill_center − curve_mid‖)
4. Gate                    (single visual-gap threshold)
5. Clip endpoint to pill   (_line_rect_intersection)
6. Emit <circle> + <polyline>
```

Each stage below.

---

## 1. Curve anchor — `curve_mid`

Leader dot sits **on the rendered Bézier curve**, not at the chord midpoint.

```python
# scriba/animation/primitives/_svg_helpers.py ≈ :2030
curve_mid_x = int(0.125*x1 + 0.375*cx1 + 0.375*cx2 + 0.125*x2)
curve_mid_y = int(0.125*y1 + 0.375*cy1 + 0.375*cy2 + 0.125*y2)
```

This is the standard cubic-Bézier evaluation `B(0.5)` where `P0 = src`, `P3 = dst`, `P1 = cp1`, `P2 = cp2`. Using control points (not chord mid) guarantees the dot lands on the visible arc even when the bow is large.

Stored on `ArrowGeometry`:

```python
ArrowGeometry(..., curve_mid_x=..., curve_mid_y=...)
```

---

## 2. Visual gap — `visual_gap`

**`visual_gap`** is the Euclidean distance from the **rendered pill centre** to the **arc midpoint anchor** (`curve_mid`). This is a purely visual measurement: it reflects exactly how far the pill appears from its arrow in the rendered output, regardless of how the placement algorithm arrived there.

```python
visual_gap = sqrt((pill_cx − curve_mid_x)² + (pill_cy − curve_mid_y)²)
```

`pill_cx` and `pill_cy` are the centre coordinates of the placed pill after `_pick_best_candidate` and viewBox clamping have resolved the final position. `curve_mid_{x,y}` are taken from `ArrowGeometry` (see §1).

This replaces the previous **algorithmic displacement** metric (`‖final − natural‖`), which measured movement within the placement algorithm rather than visual separation in the output. The old metric could produce a small displacement value even when the pill sat 100+ px from the arrow (e.g. when the natural anchor itself was far from `curve_mid`). The visual-gap metric is immune to this failure mode. See `docs/archive/dp-optimization-leader-analysis-2026-04-23/README.md` case #6 for the motivating audit.

---

## 3. Gate — when to emit

Single gate (R-27c, introduced in v0.15.0):

| Gate | Formula | Rule | Intent |
|------|---------|------|--------|
| **visual-gap gate** | `visual_gap >= pill_h/2 + 4 + pill_h × _LEADER_GAP_FACTOR` | R-27c | Any color emits a leader when the pill is visually offset from its arrow. |

Constants:

```python
_LEADER_GAP_FACTOR: float = 1.0                  # visual-gap multiplier (v0.15.0)
_LEADER_ARC_CLEARANCE_PX: float = 4.0            # natural arc clearance (v0.15.0)

# Deprecated in v0.15.0, retained for import-stability — unused by the gate:
_LEADER_DISPLACEMENT_THRESHOLD: float = 20.0
_ARROW_LEADER_FAR_FACTOR: float = 1.0
```

The threshold `pill_h/2 + _LEADER_ARC_CLEARANCE_PX + pill_h × _LEADER_GAP_FACTOR` equals `1.5 × pill_h + 4` at defaults. At `pill_h ≈ 20 px` this is 34 px. The `pill_h/2` term accounts for the half-height of the pill (so the gap is measured from the pill edge, not centre); `_LEADER_ARC_CLEARANCE_PX` is the baseline offset for the natural "above the arc peak" placement; `pill_h × _LEADER_GAP_FACTOR` is the scale-relative offset allowance.

Code:

```python
# :2238-2251 (approx)
_pill_cx = float(pill_rx) + float(pill_w) / 2.0   # rect centre, not mutated fi_x
_pill_cy = float(pill_ry) + float(pill_h) / 2.0
_visual_gap = math.hypot(
    float(geom.curve_mid_x) - _pill_cx,
    float(geom.curve_mid_y) - _pill_cy,
)
_natural_gap = float(pill_h) / 2.0 + _LEADER_ARC_CLEARANCE_PX
if _visual_gap >= _natural_gap + float(pill_h) * _LEADER_GAP_FACTOR:
    # emit leader
```

The color-gate restriction (leaders only for `warn`/`error`) is gone. Any color token emits a leader when the visual gap exceeds the threshold.

---

## 4. Endpoint clipping — `_line_rect_intersection`

The polyline MUST end on the pill **perimeter**, not the pill centre (R-08). Otherwise the leader visually pierces the pill and creates a disconnected dot.

Algorithm (`_svg_helpers.py:1044-1133`):

```
ray:   P(t) = origin + t × (pill_center − origin),  t ≥ 0
pill:  AABB at (pill_cx, pill_cy) with half-sizes (pill_w/2, pill_h/2)

for each of the 4 AABB edges:
    solve t where ray crosses that edge's x or y plane
    if t > 0 AND the other-axis coord at t is within the edge's span:
        add t to candidates
t_hit = min(candidates)
return origin + t_hit × direction
```

Edge cases:
- **origin inside pill AABB** → return `None` (leader is zero-length / meaningless).
- **origin == pill centre** → return `(pill_cx, pill_cy)` unchanged (degenerate; pre-checked).
- **no valid t** (ray parallel and off-edge, numeric) → return `None`, skip emit.

Caller honours `None`:

```python
_leader_ep = _line_rect_intersection(
    float(curve_mid_x), float(curve_mid_y),
    pill_cx, pill_cy, pill_w, pill_h,
)
if _leader_ep is not None:
    # emit circle + polyline
```

---

## 5. Emit — SVG shape

```xml
<circle cx="{curve_mid_x}" cy="{curve_mid_y}" r="2"
        fill="{arrow_stroke}" opacity="0.6"/>
<polyline points="{curve_mid_x},{curve_mid_y} {ep_x},{ep_y}"
          fill="none" stroke="{arrow_stroke}"
          stroke-width="0.75"{dasharray}
          opacity="0.6"/>
```

**Styling**:
- `r="2"` dot and `stroke-width="0.75"` are constants; opacity `0.6` mutes the leader so it doesn't compete with the arrow `<path>`.
- Stroke colour matches the arrow stroke (`s_stroke`), not the label fill.
- Dash: `stroke-dasharray="3,2"` **only** when `color == "warn"`. Error / info / success stay solid.

```python
# :2260
leader_dasharray = ' stroke-dasharray="3,2"' if color == "warn" else ""
```

Paired with R-13 which applies the dash to the arrow `<path>` too on `warn`/`muted` — leader dash mirrors that.

---

## Rule cross-reference

| Rule | Stage | What it controls |
|------|-------|------------------|
| **R-07** | gate threshold | `_LEADER_GAP_FACTOR` constant — scale-relative multiplier in the visual-gap formula (§3). |
| **R-08** | endpoint | Perimeter endpoint, not pill centre. |
| **R-13** | style | Dash on arrow `<path>` for warn/muted (mirrored on leader when warn). |
| **R-27** | (superseded) | Superseded in v0.15.0 by R-27c (visual-gap gate, §3). Color-gate restriction removed. |
| **R-27b** | (superseded) | Superseded in v0.15.0 by R-27c (visual-gap gate, §3). |
| **R-27c** | gate | Single visual-gap gate: `visual_gap >= pill_h/2 + 4 + pill_h × _LEADER_GAP_FACTOR`. Any color. |
| **HIGH-1** | safety | `_line_rect_intersection` returns `None` when origin ∈ pill AABB. |

---

## Test references

| Test | File | What it asserts |
|------|------|-----------------|
| `test_visual_gap_formula_applied` | `tests/unit/test_w3_batch1.py` | Visual-gap gate positive case (renamed from `test_scale_relative_formula_applied`). |
| `test_leader_emitted_when_visual_gap_exceeds_threshold` | `tests/unit/test_w3_batch1.py` | Visual-gap gate positive case (renamed from `test_leader_emitted_when_displacement_exceeds_scale_threshold`). |
| `test_no_leader_when_not_displaced` | `tests/unit/test_w3_batch1.py` | Gate negative case. |
| leader endpoint perimeter assertions | `tests/unit/test_smart_label_phase0.py` | R-08 endpoint clipping. |

---

## Known limitations

None outstanding for the leader-line gate as of v0.15.0. The prior limitation (algorithmic displacement under-reporting visual separation) was resolved by the visual-gap metric introduced in v0.15.0. The motivating case — DP-optimization audit annotation #6 (`dp.cell[0][6]-dp.cell[4][6]`, `final merge`, 103 px visual gap, no leader) — now correctly emits a leader. See `docs/archive/dp-optimization-leader-analysis-2026-04-23/README.md`.

---

## File map

| Symbol | Location |
|--------|----------|
| `_emit_label_and_pill` | `scriba/animation/primitives/_svg_helpers.py:2050` |
| `_line_rect_intersection` | `scriba/animation/primitives/_svg_helpers.py:1044` |
| `_compute_control_points` (emits `ArrowGeometry` with `curve_mid_{x,y}`) | `scriba/animation/primitives/_svg_helpers.py` (Phase A/2) |
| `_LEADER_GAP_FACTOR` (v0.15.0) | `≈:330` |
| `_LEADER_DISPLACEMENT_THRESHOLD` (deprecated v0.15.0, import-stability only) | `≈:93` |
| `_ARROW_LEADER_FAR_FACTOR` (deprecated v0.15.0, import-stability only) | `≈:330` |
| Gate block (`_visual_gap` / `_natural_gap` / `_LEADER_GAP_FACTOR`) | `≈:2238-2251` |
| Emit block (`<circle>` + `<polyline>`) | `≈:2261-2271` |
