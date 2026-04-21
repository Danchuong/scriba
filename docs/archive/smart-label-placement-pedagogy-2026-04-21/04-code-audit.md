# 04-code-audit.md — Smart-Label Placement: Deep Code Audit

**Repository:** `scriba`
**Date:** 2026-04-21
**HEAD commit:** `168cc4e` (fix: leader anchor at true cubic Bézier midpoint B(0.5))
**Scope:** label placement pipeline from annotation dict emission to final SVG bytes

---

## 1. Entry-Point Map

### 1.1 Call Graph

```
primitive.emit_svg()                     [array.py:183, dptable.py:210, grid.py:196,
                                          graph.py:674, tree.py:564, numberline.py:208,
                                          queue.py:261, linkedlist.py:240, hashmap.py:229,
                                          variablewatch.py:218, plane2d.py:622]
  │
  ├─ arrow_height_above(anns, resolver, ...) [_svg_helpers.py:1003]
  │    └─ _label_has_math()                 [_svg_helpers.py:96]
  │
  ├─ position_label_height_above(anns)      [_svg_helpers.py:1110]
  ├─ position_label_height_below(anns)      [_svg_helpers.py:1167]
  │
  ├─ translate(0, arrow_above)  ← SVG group shift for headroom
  │
  ├─ PrimitiveBase.emit_annotation_arrows(parts, anns) [base.py:358]
  │    │
  │    │  for ann in annotations:
  │    │
  │    ├─ [arrow=true, no arrow_from]
  │    │    resolve_annotation_point(target)   [per-primitive override]
  │    │    emit_plain_arrow_svg(...)          [_svg_helpers.py:409]
  │    │         _wrap_label_lines()           [_svg_helpers.py:310]
  │    │         _label_width_text()           [_svg_helpers.py:210]
  │    │         estimate_text_width()         [_text_render.py:45]
  │    │         _nudge_candidates()           [_svg_helpers.py:128]   ← collision avoidance
  │    │         _LabelPlacement.overlaps()    [_svg_helpers.py:86]
  │    │
  │    ├─ [arrow_from present]
  │    │    resolve_annotation_point(arrow_from)
  │    │    resolve_annotation_point(target)
  │    │    emit_arrow_svg(...)               [_svg_helpers.py:634]
  │    │         _wrap_label_lines()
  │    │         _label_width_text()
  │    │         estimate_text_width()
  │    │         _nudge_candidates()          ← collision avoidance
  │    │         _LabelPlacement.overlaps()
  │    │         [leader emit if displacement > 30]
  │    │         _emit_label_single_line()    [_svg_helpers.py:246]
  │    │
  │    └─ [label only, no arrow_from, no arrow=true]
  │         resolve_annotation_point(target)
  │         emit_position_label_svg(...)      [_svg_helpers.py:1337]
  │              [4-dir nudge loop — NOT _nudge_candidates]
  │
  └─ [plane2d only — text_anns routed separately, base.py:663–687]
       emit_position_label_svg(parts, ann, anchor, ..., placed_labels=text_placed)
```

**Key divergence:** `plane2d.py` uses a *separate* `placed_labels` list (`text_placed`) for its text annotations at line 674, independent from the `placed` list used by `emit_annotation_arrows`. Cross-annotation collision avoidance between text and arrow annotations does NOT occur in `plane2d.py`. All other primitives use a single `placed` list initialized inside `emit_annotation_arrows` (`base.py:383`).

**NumberLine divergence:** `numberline.py` does NOT call `emit_annotation_arrows`. Instead it has its own inline loop (`numberline.py:300–316`) that calls `emit_arrow_svg` directly with a locally-constructed `placed` list. The `emit_plain_arrow_svg` and `emit_position_label_svg` paths are entirely bypassed; only `arrow_from` annotations are handled.

---

## 2. Natural Position Calculation

For each primitive and annotation type, where is `(natural_x, natural_y)` computed:

| Primitive | Annotation type | `resolve_annotation_point` returns | natural_x | natural_y | File:line |
|---|---|---|---|---|---|
| **Array** | all | `(cx, 0)` — top-edge of cell | `label_ref_x` = mid of arc | `label_ref_y` = mid_y_val - 4 | `array.py:383`, `_svg_helpers.py:768` |
| **Array** | `arrow=true` | `(cx, 0)` | `float(ix1)` = same x as stem | `float(iy1) - pill_h/2 - 2` = above stem | `_svg_helpers.py:513–515` |
| **Array** | position-only | `(cx, 0)` | `ax` (cell center x) | `ay ± cell_h/2 ± pill_h/2 ± gap` | `_svg_helpers.py:1404–1419` |
| **DPTable 1D** | arc arrow | `(cx, CELL_H/2)` — cell center | arc peak x | arc peak y | `dptable.py:467`, `_svg_helpers.py:768` |
| **DPTable 2D** | arc arrow | `(cx, cy)` — cell center | arc peak x | arc peak y | `dptable.py:475` |
| **Grid** | arc arrow | `(cx, cy)` — cell center | arc or perp-offset | arc or perp-offset | `grid.py:180–193` |
| **Graph** | arc arrow | `(pos[node].x, pos[node].y)` | perp mid x + 8 | perp mid y + 8 | `graph.py:636`, `_svg_helpers.py:737` |
| **Tree** | arc arrow | `(pos[node].x, pos[node].y)` | perp mid x + 8 | perp mid y + 8 | `tree.py:525`, `_svg_helpers.py:737` |
| **NumberLine** | arc arrow | `(tick_x, NL_TICK_TOP=12)` — top of tick | mid of arc x | mid_y_val - 4 | `numberline.py:165–175`, `_svg_helpers.py:768` |
| **Queue** | arc arrow | `(cx, cell_y)` — top of cell | arc peak x | arc peak y | `queue.py:228–241` |
| **LinkedList** | arc arrow | `(nx + w/2, _PADDING=12)` — top of node | arc peak x | arc peak y | `linkedlist.py:205–218` |
| **HashMap** | arc arrow | `(cx, cy)` — bucket row center | arc peak x | arc peak y | `hashmap.py:197–210` |
| **VariableWatch** | arc arrow | `(cx, cy)` — row center | arc peak x | arc peak y | `variablewatch.py:184–198` |
| **Plane2D** | position-only | `math_to_svg(px, py)` for points; mid/centroid for lines/segments/polygons | `ax ± pill_w/2 ± gap` | `ay ± cell_h/2 ± pill_h/2 ± gap` | `plane2d.py:529–601` |

**Arc label natural position formulas (`emit_arrow_svg`):**

*Horizontal layout* (`layout != "2d"`, used by Array, DPTable 1D, NumberLine, Queue, LinkedList, HashMap, VariableWatch):
```
mid_x_f = (x1 + x2) / 2
total_offset = base_offset + arrow_index * stagger
mid_y_val = int(min(y1, y2) - total_offset)

# h_span < 4 (near-vertical):
label_ref_x = max(raw_lx, _est_pill_hw)   # _svg_helpers.py:761
label_ref_y = mid_y_val - 4

# h_span >= 4 (normal):
label_ref_x = int(mid_x_f)                # _svg_helpers.py:768
label_ref_y = mid_y_val - 4
```

*2D layout* (`layout == "2d"`, used by Grid, Graph, Tree, Plane2D):
```
mid_x_f = (x1 + x2) / 2
mid_y_f = (y1 + y2) / 2
perp_x = -dy / dist
perp_y = dx / dist
label_ref_x = int(mid_x_f + perp_x * (total_offset + 8))   # _svg_helpers.py:737
label_ref_y = int(mid_y_f + perp_y * (total_offset + 8))
```

`base_offset` formula (`_svg_helpers.py:720`):
```python
h_dist = abs(x2 - x1) + abs(y2 - y1)
base_offset = min(cell_height * 1.2, max(cell_height * 0.5, math.sqrt(h_dist) * 2.5))
stagger = cell_height * 0.3
total_offset = base_offset + arrow_index * stagger
```

---

## 3. Candidate Generation Algorithm

### 3.1 `_nudge_candidates` (used by `emit_arrow_svg` and `emit_plain_arrow_svg`)

**Location:** `_svg_helpers.py:128–203`

The algorithm generates exactly **32 candidates = 8 compass directions × 4 step sizes**.

**Step sizes** (relative to `pill_h`):
```
steps = (pill_h * 0.25, pill_h * 0.5, pill_h * 1.0, pill_h * 1.5)
```
Note: `pill_w` is accepted for API symmetry but not used for step sizing.

**8 compass directions** (`_COMPASS_8`, `_svg_helpers.py:104–113`):
```
(0, -1)   # 0: N
(0, +1)   # 1: S
(+1, 0)   # 2: E
(-1, 0)   # 3: W
(+1, -1)  # 4: NE
(-1, -1)  # 5: NW
(+1, +1)  # 6: SE
(-1, +1)  # 7: SW
```

**Candidate layout (ASCII spiral diagram):**

```
Step sizes are multiples of pill_h: 0.25h, 0.5h, 1.0h, 1.5h

At each step s, the 8 candidates form a square ring:
         NW(5)  N(0)  NE(4)
          W(3)  [●]   E(2)
         SW(7)  S(1)  SE(6)

Full 32-candidate traversal order (no side_hint, Manhattan-sorted):
  Ring 0 (s=0.25h): dist=0.25h  → N(0), S(1), E(2), W(3)
                    dist=0.35h  → NE(4), NW(5), SE(6), SW(7)
  Ring 1 (s=0.5h):  dist=0.5h  → N(0), S(1), E(2), W(3)
                    dist=0.71h  → NE(4), NW(5), SE(6), SW(7)
  Ring 2 (s=1.0h):  dist=1.0h  → N(0), S(1), E(2), W(3)
                    dist=1.41h  → NE(4), NW(5), SE(6), SW(7)
  Ring 3 (s=1.5h):  dist=1.5h  → N(0), S(1), E(2), W(3)
                    dist=2.12h  → NE(4), NW(5), SE(6), SW(7)

Tie-break priority at equal Manhattan distance: N < S < E < W < NE < NW < SE < SW
```

**Side-hint reordering** (`_svg_helpers.py:184–203`):
When `side_hint` ∈ `{"above", "below", "left", "right"}`, the preferred half-plane indices are:
```
"above": {0, 4, 5}  → N, NE, NW  (all dy < 0)
"below": {1, 6, 7}  → S, SE, SW  (all dy > 0)
"left":  {3, 5, 7}  → W, NW, SW  (all dx < 0)
"right": {2, 4, 6}  → E, NE, SE  (all dx > 0)
```
Preferred candidates (12 total = 3 dirs × 4 steps) are emitted first, sorted by Manhattan distance. The remaining 20 candidates follow, also sorted by Manhattan distance.

**Selection:** First candidate for which `not any(candidate.overlaps(p) for p in placed_labels)` wins. If all 32 exhausted, last candidate is returned with `fits_cleanly=False` (`_place_pill:1324`, or `collision_unresolved=True` in `emit_arrow_svg`/`emit_plain_arrow_svg`).

### 3.2 `emit_position_label_svg` — DIFFERENT algorithm

**Location:** `_svg_helpers.py:1421–1453`

This function does NOT use `_nudge_candidates`. It uses an older **4-direction × up-to-4-pass** scheme:
```python
nudge_dirs = [
    (0, -nudge_step),   # up
    (-nudge_step, 0),   # left
    (nudge_step, 0),    # right
    (0, nudge_step),    # down
]
nudge_step = pill_h + 2

for _ in range(4):    # at most 4 rounds
    if no collision: break
    try each of 4 dirs, take first free, break
    if none free: collision_unresolved=True; break
```
Maximum candidate count: 4 × 4 = **16 candidates** (much less than the 32 used by arc/pointer arrows). No diagonal directions. No side_hint support.

### 3.3 `_place_pill` — MW-3 dedicated helper

**Location:** `_svg_helpers.py:1213–1334`

Used **only by `plane2d.py`** (via the `text_anns` path at `plane2d.py:680`). Uses `_nudge_candidates` (32 candidates), does per-candidate clamp before collision check (AC-3), and returns `(placement, fits_cleanly)`. Does not append to `placed_labels` itself — the caller (`plane2d.py`) is responsible.

**Observation:** `_place_pill` is the most correct implementation; `emit_position_label_svg` uses the legacy 4-dir/4-pass scheme. They coexist on the same code path for different callsites.

---

## 4. Scoring Function

There is no scoring function. The algorithm is **first-fit**, not ranked-choice. The selection criterion is binary: `not any(candidate.overlaps(p) for p in placed_labels)` (`_svg_helpers.py:549`, `891`, `1314`).

**Overlap test** (`_svg_helpers.py:86–93`):
```python
def overlaps(self, other: "_LabelPlacement") -> bool:
    return not (
        self.x + self.width / 2 < other.x - other.width / 2
        or self.x - self.width / 2 > other.x + other.width / 2
        or self.y + self.height / 2 < other.y - other.height / 2
        or self.y - self.height / 2 > other.y + other.height / 2
    )
```
Pure AABB intersection. No distance-based scoring, no proximity bonus, no "closest to natural position" tiebreaker beyond the implicit Manhattan-distance ordering of candidates.

**Tie-break order** is encoded in `_COMPASS_8` ordering: among candidates with equal Manhattan distance to the natural position, N wins over S wins over E wins over W wins over diagonals. This is hard-wired in `_svg_helpers.py:104–113`. There is no user-controllable scoring parameter.

---

## 5. Clamping Logic

### 5.1 `emit_arrow_svg` and `emit_plain_arrow_svg` — post-selection clamp only

Both functions apply a **left-edge-only** post-selection clamp at the registration step:

```python
# _svg_helpers.py:559–568 (emit_plain_arrow_svg), 903–910 (emit_arrow_svg)
clamped_x = max(final_x, pill_w / 2)    # left-edge clamp
placed_labels.append(_LabelPlacement(
    x=clamped_x,
    y=candidate.y,
    width=float(pill_w),
    height=float(pill_h),
))
```

And the render step also applies:
```python
# _svg_helpers.py:579–581 (emit_plain_arrow_svg), 923–926 (emit_arrow_svg)
pill_rx = max(0, int(fi_x - pill_w / 2))
fi_x = max(fi_x, pill_w // 2)
```

**No right-edge, top-edge, or bottom-edge clamp** is applied. The candidate is selected without any viewbox awareness; only the left edge is clamped, and only after selection. This means a label near the right edge can extend beyond the viewbox without triggering re-selection.

The `y` coordinate is not clamped at all in `emit_arrow_svg` or `emit_plain_arrow_svg`. A label whose natural position is off the top of the canvas can be emitted at a negative y, with only the top-of-frame `translate(0, arrow_above)` shift as an indirect safeguard.

**This is MW-3 / ISSUE-A3 (clamp-race):** The nudge candidates in `emit_arrow_svg`/`emit_plain_arrow_svg` are generated from `final_x + ndx, candidate_y + ndy` without clamping each candidate before the collision check. A candidate that lands at x < 0 is tested as-is, and if it passes the (unpopulated) collision check, it becomes the winner before clamping. After clamping moves it right, the rendered pill collides with something that the test would have flagged. This is the bug `_place_pill` was built to fix (per `AC-3` comment at `_svg_helpers.py:1273`), but `_place_pill` is only used by `plane2d.py`.

### 5.2 `_place_pill` — per-candidate clamp (correct)

```python
# _svg_helpers.py:1282–1285
def _clamp(cx, cy):
    cx = max(half_w, min(cx, viewbox_w - half_w))
    cy = max(half_h, min(cy, viewbox_h - half_h))
    return cx, cy
```

Every candidate is clamped to `[half_w, viewbox_w - half_w] × [half_h, viewbox_h - half_h]` **before** the collision check (`_svg_helpers.py:1307–1322`). This prevents post-selection drift. Natural position also clamped before initial check (`_svg_helpers.py:1288–1295`).

### 5.3 `emit_position_label_svg` — no clamp at all

The 4-dir nudge loop in `emit_position_label_svg` (`_svg_helpers.py:1429–1453`) applies zero clamping during candidate selection. The only clamp is `clamped_x = max(final_x, pill_w / 2)` at registration (`_svg_helpers.py:1457`), identical to the `emit_arrow_svg` left-only clamp.

---

## 6. Leader Emit Trigger

**Location:** `emit_arrow_svg`, `_svg_helpers.py:939–954`

```python
displacement = math.sqrt(
    (final_x - natural_x) ** 2 + (final_y - natural_y) ** 2
)
if displacement > 30:
    leader_dasharray = ' stroke-dasharray="3,2"' if color == "warn" else ""
    lines.append(
        f'    <circle cx="{curve_mid_x}" cy="{curve_mid_y}" r="2"'
        f' fill="{s_stroke}" opacity="0.6"/>'
    )
    lines.append(
        f'    <polyline points="{curve_mid_x},{curve_mid_y}'
        f' {fi_x},{fi_y}"'
        f' fill="none" stroke="{s_stroke}"'
        f' stroke-width="0.75"{leader_dasharray}'
        f' opacity="0.6"/>'
    )
```

**Threshold:** Hard-coded `30` pixels (no constant, no config). `_svg_helpers.py:942`.

**Trigger condition:** Any `displacement > 30` regardless of color token.

**Leader endpoint:** Anchor dot at `(curve_mid_x, curve_mid_y)` — the true B(0.5) cubic Bézier midpoint, computed at `_svg_helpers.py:775–776`:
```python
curve_mid_x = int(0.125 * x1 + 0.375 * cx1 + 0.375 * cx2 + 0.125 * x2)
curve_mid_y = int(0.125 * y1 + 0.375 * cy1 + 0.375 * cy2 + 0.125 * y2)
```
This is the **B(0.5) fix** at HEAD commit `168cc4e`. Before this commit, the 2d branch used `mid_x_f + perp_x * total_offset * 0.75` (the control-point plateau, ~25% above the true midpoint), and the horizontal branch used `(mid_x_f, mid_y_val)` (the control-point y-coordinate, not the curve itself).

**`warn` dasharray rule (A-5 non-colour cue, commit `b1a4ff1`):** Only the `"warn"` color token gets `stroke-dasharray="3,2"`. All other tokens (`good`, `info`, `error`, `muted`, `path`) emit a solid leader.

**`emit_plain_arrow_svg`:** No leader logic at all. Plain pointer arrows do not emit leader lines regardless of displacement, because the stem is always short and fixed at `_PLAIN_ARROW_STEM = 18` px. `_svg_helpers.py:513–515`.

**`emit_position_label_svg`:** No leader logic. Position-only labels never emit leader lines. `_svg_helpers.py:1337–1531`.

---

## 7. Z-order / Emit Order

Z-order is entirely determined by **insertion order into the `parts`/`lines` list**, which becomes the final SVG string. SVG renders elements in document order; later elements appear on top.

**Within `emit_annotation_arrows` (`base.py:383–449`):**

Annotations are processed in `annotations` list order — the order they were provided to `set_annotations()`. For each annotation:
1. Marker defs (`emit_arrow_marker_defs` — now a no-op, `_svg_helpers.py:1534–1554`)
2. The annotation `<g>` element itself (arrow path + arrowhead polygon + pill rect + label text)

All annotations are appended into the same `parts`/`lines` list inside a single flat loop. There is no sorting by priority, color, or semantic importance.

**Cross-primitive z-order:**

The `placed` list in `emit_annotation_arrows` is local to that call (`base.py:383`). When the scene assembles multiple primitives' SVG fragments, each fragment is self-contained. Annotations of one primitive are fully below or above annotations of another depending on which primitive's `emit_svg` runs first.

**Plane2D z-order:**

`plane2d.py:663–687` emits `arrow_anns` first (via `emit_annotation_arrows`), then `text_anns` (via the `text_placed` loop). Arrow annotation `<g>` elements appear before text annotation `<g>` elements, meaning text labels render on top of arrow curves.

---

## 8. Known Weaknesses

### W-1: No directional priority on arc labels (angle-uniform ring)

**Evidence:** `_nudge_candidates` generates candidates at all 8 compass directions symmetrically. For a label sitting above a horizontal arrow, N-nudge candidates (`dy < 0`) push the label further into empty white space above the arrow; S-nudge candidates push it back toward the target cell. The algorithm has no concept of "which direction is safe given the arrow geometry."

The `side_hint` mitigation (`_svg_helpers.py:184–203`, added in MW-1) partially addresses this for the caller-specified `ann["side"]` or `ann["position"]` key. However, these keys are authored manually; no key is auto-computed from the arrow direction. Most annotations omit `side`, so `anchor_side = None` (`_svg_helpers.py:867`), triggering the symmetric 32-candidate search.

**File:line:** `_svg_helpers.py:867–868`, `_svg_helpers.py:128–203`.

### W-2: No target-occlusion guard

**Evidence:** The collision registry (`placed_labels`) contains only placed pill labels. It does not include the source/destination cell rectangles, node circles, or the arrow curve path itself. A nudged label can land directly over the destination cell it annotates, or over the arrow arc body.

**File:line:** `_LabelPlacement` dataclass `_svg_helpers.py:77–93`; no obstacle registration anywhere in `emit_annotation_arrows` (`base.py:383–449`).

### W-3: Hard-coded displacement threshold = 30 px

**Evidence:** `_svg_helpers.py:942`:
```python
if displacement > 30:
```
No named constant. The value 30 was chosen arbitrarily and applies identically to all primitives regardless of their scale. A 30 px displacement is meaningful at `CELL_HEIGHT=40` but nearly invisible for Graph nodes at `width=400`.

### W-4: Leader emitted for all color tokens (not just warn/error)

**Evidence:** `_svg_helpers.py:939–954`. The `if displacement > 30:` block fires for `good`, `info`, `muted`, and `path` labels just as it does for `warn` and `error`. A nudged `muted` annotation emits a faint leader at `opacity="0.6"`, which adds visual noise for annotations that are intentionally low-prominence.

### W-5: Emit order = insertion order, not semantic importance

**Evidence:** `base.py:383`; all annotations processed in `annotations` list order. `error` annotations do not render on top of `muted` annotations; z-order reflects the author's list order, not the urgency level of the color token. An `error` annotation appended after a `good` one will render on top, but if declared before it will appear under.

### W-6: `emit_position_label_svg` uses legacy 4-dir × 4-pass nudge (not `_nudge_candidates`)

**Evidence:** `_svg_helpers.py:1421–1453`. The function has 16 candidates maximum, no diagonal directions, no side-hint support. `emit_arrow_svg` / `emit_plain_arrow_svg` have 32 candidates with diagonal and side-hint. The two code paths provide unequal collision resolution quality for the same type of label pill.

**File:line:** `_svg_helpers.py:1428–1453` vs `_svg_helpers.py:541–554`.

### W-7: Clamp-race (AC-3) in `emit_arrow_svg` / `emit_plain_arrow_svg`

**Evidence:** As detailed in §5.1, nudge candidates are not clamped before the collision test in these two functions. `_place_pill` (`_svg_helpers.py:1305–1311`) was built to fix this but is only wired to `plane2d.py`. The `emit_arrow_svg` path (`_svg_helpers.py:883–898`) and `emit_plain_arrow_svg` path (`_svg_helpers.py:542–555`) generate candidates with `final_x + ndx` and `candidate_y + ndy` without clamping, then clamp only after selection. A candidate in negative-x territory may be selected over a valid positive-x candidate if the negative-x one happens to be collision-free.

### W-8: `placed_labels=None` bypasses all collision avoidance silently

**Evidence:** All three emit functions guard with `if placed_labels is not None:` (`_svg_helpers.py:530`, `872`, `1421`). If a caller forgets to pass a registry, the annotation is emitted at its natural position with no overlap checking, no registration, and no warning. `NumberLine.emit_svg` does pass `placed_labels=placed` (`numberline.py:312`), but does not go through `emit_annotation_arrows`, meaning if the path were refactored to skip `placed_labels`, there would be no loud failure.

### W-9: `_place_pill` is unused by 10 of 12 primitives

**Evidence:** `_place_pill` is imported in `plane2d.py:38` and used at `plane2d.py:680`. It is not called by Array, DPTable, Grid, Graph, Tree, NumberLine, Queue, LinkedList, HashMap, or VariableWatch. These primitives use the older `emit_position_label_svg` (4-dir nudge) or `emit_arrow_svg`/`emit_plain_arrow_svg` (32-dir but no per-candidate clamp). The fully-correct implementation exists but is not propagated.

### W-10: No viewbox dimensions passed to the arrow/pointer emitters

**Evidence:** `emit_arrow_svg` and `emit_plain_arrow_svg` do not accept `viewbox_w` / `viewbox_h` parameters. `_place_pill` does (`_svg_helpers.py:1219–1220`). Without viewbox dimensions, right-edge, top-edge, and bottom-edge clamping is impossible. Only left-edge is clamped (as `max(x, pill_w/2)`).

### W-11: `curve_mid` used as leader anchor even when label was not displaced by nudge

**Evidence:** `_svg_helpers.py:939–954`. The displacement check uses `natural_x / natural_y` vs `final_x / final_y`. When `displacement > 30`, a leader is drawn from `(curve_mid_x, curve_mid_y)` — the B(0.5) midpoint of the arrow — to `(fi_x, fi_y)` — the label center. If the label happens to be near the arc's B(0.5) point naturally (not because it was nudged far), the leader still fires. The condition `displacement > 30` is a proxy for "the label is visually separate from the annotation target," but it triggers even for geometrically normal large-canvas layouts.

---

## 9. Refactor Cost Estimates

| Weakness | Description | Estimate | Rationale |
|---|---|---|---|
| W-1 | Directional priority (auto-compute `side_hint` from arrow direction) | **S = 4h** | Add a helper that computes preferred half-plane from `(src_point, dst_point)` vector; wire into `emit_arrow_svg` before `_nudge_candidates` call. Pure logic, no schema change. |
| W-2 | Target-occlusion guard (add cell/node geometry to registry) | **M = 1d** | Need to define how each primitive registers its cell bounding boxes before annotation emission; requires API extension on `resolve_annotation_point` or a separate `resolve_obstacle_boxes` method; test coverage for each primitive. |
| W-3 | Named constant + scale-relative threshold | **XS = 1h** | Extract `30` to `_LEADER_DISPLACEMENT_THRESHOLD: int = 30`; optionally pass as parameter. No behavior change. |
| W-4 | Leader gated to warn/error only | **XS = 1h** | Add `if color in ("warn", "error"):` guard; update tests. Byte-breaking for `good`/`info`/`muted`/`path` displaced labels. |
| W-5 | Emit order by semantic importance | **S = 4h** | Sort annotations by `ARROW_STYLES` priority before the loop in `emit_annotation_arrows`; define color priority ordering. Byte-breaking for all scenes with mixed-color annotations. |
| W-6 | Migrate `emit_position_label_svg` to `_nudge_candidates` | **S = 4h** | Replace the 4-dir × 4-pass loop with the 32-candidate `_nudge_candidates` loop. Requires viewbox params to be threaded through. Byte-breaking for any scene where nudge fires. |
| W-7 | Per-candidate clamp in `emit_arrow_svg` / `emit_plain_arrow_svg` | **S = 4h** | Thread `viewbox_w / viewbox_h` params to both functions (new optional params); wrap candidate generation in same `_clamp()` as `_place_pill`. Byte-breaking. |
| W-8 | Warn on `placed_labels=None` | **XS = 1h** | Add runtime warning when `placed_labels is None`; or make the parameter required. No SVG change. |
| W-9 | Propagate `_place_pill` to all primitives | **L = 3d** | Requires threading `viewbox_w / viewbox_h` through all 10 primitives' `emit_svg` paths; refactoring `emit_annotation_arrows` to accept or compute viewport dimensions; golden corpus re-pin for all affected primitives. |
| W-10 | Add `viewbox_w / viewbox_h` to arrow emitters | **M = 1d** | API surface change; update 10 primitive callsites + all tests that call `emit_arrow_svg` directly. |
| W-11 | Conditionalize leader on semantic displacement | **S = 4h** | Replace `displacement > 30` with a smarter test (e.g. `displacement > threshold AND label_center not near curve`). May require geometry helper. Byte-breaking for edge cases. |

---

## 10. Test Coverage Gaps

### 10.1 Not covered by current tests

**T-1: Right-edge, top-edge, bottom-edge overflow** — `test_smart_label_phase0.py` tests only left-edge clamp (`TestQW3ClampedRegistration`). There is no test asserting that a label near `x=viewbox_width` or `y=0`/`y=viewbox_height` is clamped. `_place_pill` tests in `test_g1_anchor.py` cover right-edge for `_place_pill` only.

**T-2: `emit_arrow_svg` clamp-race scenario** — No test exercises the case where a nudge candidate lands at negative x, passes collision check, then is clamped to positive x before rendering. The clamped position could overlap an already-registered label.

**T-3: `emit_position_label_svg` with 32-candidate overflow** — `TestQW2NoBlindUpNudge` tests all-32-collision only for `emit_plain_arrow_svg` and `emit_arrow_svg`. No analogous test exercises all-16-candidate exhaustion in `emit_position_label_svg`.

**T-4: Plane2D cross-annotation collision (text vs arrow)** — `plane2d.py` uses separate `placed` and `text_placed` lists. No test verifies that text annotations and arrow annotations do not overlap each other in Plane2D renders.

**T-5: Arrow index stagger with N > 2 arrows on same target** — `arrow_index` stagger (`cell_height * 0.3` per index) is tested implicitly through rendering, but there is no unit test asserting that labels for 3+ arrows on the same target are mutually non-overlapping.

**T-6: `side_hint` propagation from `ann["side"]` key** — `_nudge_candidates` side_hint tests exist (`TestMW1EightDirectionGrid`), but no test verifies that an annotation with `{"side": "above"}` or `{"position": "above"}` in the dict actually causes `_nudge_candidates` to be called with `side_hint="above"` in `emit_arrow_svg` and `emit_plain_arrow_svg`.

**T-7: Multi-primitive scene collision across primitive boundaries** — The entire test suite operates on single-primitive scenes. When two ArrayPrimitive instances are placed side-by-side in the same scene, their `placed` registries are entirely independent (`base.py:383`). No test exercises label collision between annotations from different primitive instances.

**T-8: Graph/Tree `_arrow_layout="2d"` + `_arrow_shorten` edge case with `shorten_src ≈ dist`** — When `shorten_src` is close to or exceeds `dist` (very short edges), the endpoints `x1, y1, x2, y2` can collapse nearly to the same point, making `label_ref_x / label_ref_y` undefined. No test covers this.

**T-9: `_wrap_label_lines` with mixed math and long plain text** — The `in_math` guard prevents splitting inside `$...$` but there is no test for a label where a math fragment occurs after 24+ plain-text characters (the split would fire, then the math segment would be on a new line).

**T-10: `emit_position_label_svg` with `position="left"` or `position="right"` near edge** — Tests cover `above` and `below` positions. The horizontal positions `left` and `right` calculate `final_x = ax ± pill_w/2 ± gap`; for a cell near the canvas left edge, `position="left"` would produce a negative `final_x`. No test covers this.

**T-11: `numberline.py` bypasses `emit_annotation_arrows`** — `numberline.py:300–316` has its own arrow emission loop that does not call `emit_annotation_arrows`. It handles only `arrow_from` annotations and drops all `arrow=true` and position-only annotations silently. No test exercises `arrow=true` or `position` annotations on a NumberLine.

### 10.2 Partial coverage

**P-1: Golden corpus** — Three golden fixtures exist (`tests/golden/smart_label/ok-simple`, `critical-2-null-byte`, `bug-B`). They cover basic rendering correctness but do not systematically exercise all 12 primitives or the full annotation type matrix (arc × pointer × position-only × each color).

**P-2: Hypothesis D-3 permutation independence** — Tested for `emit_position_label_svg` with non-overlapping annotations. Not tested for `emit_arrow_svg` (which has a dependency on `arrow_index` based on insertion order, making D-3 fundamentally NOT invariant to permutation for arrow annotations sharing a target).

---

## 11. Safety Analysis

Changes are classified as **byte-breaking** (existing golden corpus SVGs change) or **non-byte-breaking** (no SVG output change).

### 11.1 Byte-breaking changes

These changes would alter SVG output and require golden corpus re-pin:

| Change | Why breaking |
|---|---|
| Migrate `emit_position_label_svg` to `_nudge_candidates` (W-6) | Nudge direction priority changes from 4-dir to 8-dir; any scene where collision fires gets different pill coordinates |
| Add per-candidate clamp to `emit_arrow_svg` / `emit_plain_arrow_svg` (W-7, W-9) | Candidate selection changes for labels near viewport edges; different winning candidate → different `(fi_x, fi_y)` → different pill rect and text coordinates |
| Gate leader to warn/error only (W-4) | Removes leader `<circle>` and `<polyline>` elements from displaced `good`/`info`/`muted`/`path` labels |
| Sort annotations by semantic importance (W-5) | Reorders `<g>` elements within the SVG for mixed-color annotation sets |
| Auto-compute `side_hint` from arrow direction (W-1) | Changes candidate priority order for arc arrows without explicit `side`/`position` key |
| Change displacement threshold constant (W-3) | Any change to the `30` value changes which leaders are emitted |
| Conditionalize leader trigger (W-11) | Changes when leaders appear |
| Propagate `_place_pill` full-clamping to all primitives (W-9) | Changes all near-edge placements |

### 11.2 Non-byte-breaking changes

These changes would not alter SVG output for any currently-passing scene:

| Change | Why safe |
|---|---|
| Extract `30` to named constant without value change (W-3 partial) | Behavior identical |
| Add `placed_labels=None` warning or deprecation (W-8) | No SVG change; only developer-visible warning |
| Add `viewbox_w / viewbox_h` as optional parameters with `None` default, falling back to current no-clamp behavior (W-10 partial) | When `None`, identical to current behavior |
| Fix `_DEBUG_LABELS` gating (already correct at HEAD) | Gated behind env var; production SVG unaffected |
| Add `side_hint` auto-computation as opt-in via new annotation key (not auto-applied) | Existing annotations without the new key unaffected |
| Documentation, type annotations, constant extraction (no logic change) | Safe |

### 11.3 Partial-breaking changes

| Change | Breaking scope |
|---|---|
| Per-candidate clamp in emitters with `viewbox_w / viewbox_h` optional (no clamp when `None`) | Only byte-breaking when viewbox is actually supplied and a candidate near an edge would have been differently selected |
| Migrate position-only nudge to `_nudge_candidates` only when `placed_labels` is non-empty and a collision actually fires | Only byte-breaking for frames that currently trigger position nudging |

---

## Summary

The smart-label placement system operates through three distinct code paths — `emit_arrow_svg` (32-candidate 8-direction nudge), `emit_plain_arrow_svg` (same), and `emit_position_label_svg` (older 16-candidate 4-direction nudge) — none of which apply per-candidate viewport clamping, a problem already solved in the newer `_place_pill` helper (`_svg_helpers.py:1213–1334`) but wired only to `plane2d.py`. The candidate search is purely first-fit with Manhattan-distance ordering and no knowledge of arrow geometry, cell boundaries, or semantic priority; the `side_hint` directional preference helps when explicitly authored but is never auto-inferred from the arc direction. The leader line trigger fires at a hard-coded 30 px threshold for all color tokens (including low-prominence `muted`/`info`), the B(0.5) anchor was corrected in HEAD commit `168cc4e` to use true cubic Bézier midpoint evaluation, and z-order is insertion order with no semantic sorting. Primary test gaps are right/top/bottom edge overflow, cross-primitive collision, and the `numberline.py` bypass of the shared annotation dispatch that silently drops `arrow=true` and position-only annotations.
