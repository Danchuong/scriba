# Smart-Label Placement Algorithm Audit — 2026-04-21

## 1. Current Algorithm Walk-Through

### 1.1 Shared data structure: `_LabelPlacement`

**File:** `scriba/animation/primitives/_svg_helpers.py` lines 58–74

```python
@dataclass(slots=True)
class _LabelPlacement:
    x: float   # CENTER of the pill
    y: float   # CENTER of the pill
    width: float
    height: float

    def overlaps(self, other) -> bool:
        return not (
            self.x + self.width  / 2 < other.x - other.width  / 2
            or self.x - self.width  / 2 > other.x + other.width  / 2
            or self.y + self.height / 2 < other.y - other.height / 2
            or self.y - self.height / 2 > other.y + other.height / 2
        )
```

`x` and `y` are **center** coordinates. The AABB overlap test expands each box by half its dimension in each direction before comparing edges. The math is internally consistent.

### 1.2 `emit_plain_arrow_svg` (lines 247–445) — `arrow=true` pointer

1. **Stem geometry.** The arrowhead tip is `dst_point`; the stem base is 18 px directly above it (`_PLAIN_ARROW_STEM = 18`).
2. **Pill sizing.** `_wrap_label_lines` splits the label text at ≤ 24 chars. `estimate_text_width` measures each line (strip-`$` heuristic via `_label_width_text`). `pill_w = max_line_w + 12`, `pill_h = num_lines * (font_px + 2) + 6`.
3. **Natural position.** `natural_x = stem_base_x`, `natural_y = stem_base_y - pill_h/2 - 2`. The label sits centred horizontally above the stem base, with 2 px gap.
4. **Nudge loop** (lines 353–388):
   - `nudge_step = pill_h + 2` (just enough to clear a same-size pill)
   - Direction priority: UP, LEFT, RIGHT, DOWN
   - Four outer iterations. Each iteration: if no overlap → break. Otherwise scan 4 directions; take the first collision-free one (break). If no direction resolved, forced-apply UP regardless.
5. **Post-nudge rendering.** `fi_x = int(final_x)`, `fi_y = int(final_y)`. `pill_rx = max(0, int(fi_x - pill_w/2))` clamps left edge. `fi_x = max(fi_x, pill_w // 2)` adjusts the text anchor if the pill was clamped.
6. **No leader line.** `emit_plain_arrow_svg` never draws a leader line regardless of displacement. The stem is the only visual connection and it never moves.
7. **Registration.** `placed_labels.append(candidate)` appends the final (possibly nudged) position.

### 1.3 `emit_arrow_svg` (lines 448–790) — cubic Bezier `arrow_from`

1. **Endpoint shortening.** Optional `shorten_src`/`shorten_dst` pulls endpoints toward each other along the chord, used by circular graph nodes.
2. **Curve geometry.**
   - *Horizontal layout:* curve peaks above the lower endpoint. `total_offset = base_offset + arrow_index * stagger` where `base_offset = clamp(sqrt(h_dist)*2.5, cell_h*0.5, cell_h*1.2)` and `stagger = cell_h * 0.3`.
   - *2D layout:* curve bows perpendicular to the source–destination line using the left-hand normal.
   - *Near-vertical special case* (horizontal only, `h_span < 4`): control points are nudged horizontally by `total_offset * 0.6` to prevent the arc from collapsing.
3. **`label_ref_x/y`** is the candidate natural position: curve midpoint + small upward offset (`-4 px`) for horizontal, or curve midpoint displaced along the perpendicular for 2D.
4. **Pill sizing.** Same as plain: wrap, measure, pad.
5. **Nudge loop** (lines 671–710): identical structure to plain — `nudge_step = pill_h + 2`, same 4-direction priority, same 4-iteration cap, same forced-UP fallback when unresolved.
6. **Leader line** (lines 729–744): if `displacement > 30` px after nudging, a dashed polyline is drawn from `curve_mid_x/y` (≈ curve midpoint) to `fi_x/fi_y` (pill center). A 2 px dot marks the curve anchor. Note: the leader terminates at pill **center**, not the pill perimeter.
7. **Post-nudge clamping.** Same `pill_rx = max(0, ...)` / `fi_x = max(fi_x, pill_w // 2)` pattern as plain.
8. **Registration.** `placed_labels.append(candidate)`.

### 1.4 `_wrap_label_lines` (lines 157–182)

Breaks tokens at `" "`, `","`, `"+"`, `"="`, `"-"`. After splitting, greedily packs tokens into lines until adding the next token would exceed `max_chars=24`. The delimiter character is **included at the end of the preceding token**, not the start of the next one.

---

## 2. Known Weaknesses

### W1 — Forced-UP nudge when all 4 directions collide (critical)

**Lines:** `_svg_helpers.py` 379–385 (plain), 699–706 (Bezier)

```python
if not resolved:
    candidate = _LabelPlacement(
        x=candidate.x + nudge_dirs[0][0],   # nudge_dirs[0] = (0, -nudge_step) = UP
        y=candidate.y + nudge_dirs[0][1],
        ...
    )
```

When all 4 nudge directions still collide, the algorithm applies the UP nudge unconditionally, **without checking for collision**. The outer `for _ in range(4)` then retries, but "retry" means: check current position → still collides → scan 4 dirs → all collide again → force UP again. The candidate moves UP by `nudge_step` every iteration until the 4 iterations exhaust. The result is a label displaced `4 * (pill_h + 2)` pixels straight up from its natural position regardless of what is above it, and still overlapping the original blockers. There is no recovery path after 4 forced-UP moves; the label is registered as placed and future labels treat it as a blocker at this wrong position.

### W2 — Nudge loop is NOT iterative refinement; it is a greedy single-step scanner

Each outer iteration tries to escape from the **current** candidate position, not from the original natural position. When iteration 1 picks LEFT (moves left), iteration 2 checks the LEFT position and may then pick UP — the final position is UP+LEFT from natural, not straight UP. This is unintentional chain-drift: the label can wander far from its anchor across the 4 iterations even when the first escape direction resolved overlap with all existing labels.

The 30 px leader threshold has to pick up the slack for all this drift, but see W5.

### W3 — Leader line threshold is hardcoded at 30 px and applies only to `emit_arrow_svg`

**Line:** `_svg_helpers.py` 733

`emit_plain_arrow_svg` **never** draws a leader line. When a plain-pointer label is nudged far from the stem top — possible with a dense plain-arrow cluster — the user sees a floating pill with no visual connection to the stem.

For `emit_arrow_svg`, the threshold of 30 px is small relative to `nudge_step = pill_h + 2`. A single UP nudge for an 11 px font gives `nudge_step = (11+2) + 2 = 15 px`, so two nudge steps = 30 px, exactly at the threshold. A label nudged two steps up (common) will draw no leader. The threshold should arguably be one nudge_step or zero.

### W4 — Leader line anchors to pill CENTER, not pill perimeter

**Lines:** `_svg_helpers.py` 739–743

```python
f'    <polyline points="{curve_mid_x},{curve_mid_y} {fi_x},{fi_y}"'
```

`fi_x`, `fi_y` is the pill center (the text x/y coordinate). The line pierces visually through the pill background rectangle, obscuring the text. The abandoned Phase 7 branch introduced `intersect_pill_edge` specifically to fix this (see Section 4).

### W5 — AABB overlap is measured against pill CENTER, but the pill is clamped at render time

**Lines:** `_svg_helpers.py` 393–395 (plain) and 717–720 (Bezier)

```python
pill_rx = max(0, int(fi_x - pill_w / 2))   # clamp left edge to 0
fi_x    = max(fi_x, pill_w // 2)            # shift text right if clamped
```

The `_LabelPlacement` stored in `placed_labels` uses `final_x` before this clamp. If the pill is clamped (e.g. near the left edge of the viewBox), the registered bounding box center differs from the rendered pill center. Future pills checking overlap against this registration will compute incorrect distances.

### W6 — `estimate_text_width` strip-`$` heuristic underestimates math labels

**File:** `_svg_helpers.py` lines 82–90; `_text_render.py` lines 45–85

`_label_width_text` strips only the `$` delimiters, leaving the raw TeX source (e.g. `\frac{n(n+1)}{2}`) for width estimation. `estimate_text_width` then runs the character-based 0.62 em/char heuristic over the TeX source string. KaTeX renders `\frac{n(n+1)}{2}` much wider than the raw ASCII characters suggest (fraction stacks vertically, numerals in sub/superscripts have different metrics). The result is `pill_w` computed too small, so the rendered KaTeX foreignObject overflows the pill rect visually and the registered `_LabelPlacement.width` is smaller than the true rendered width, causing collision misses for adjacent labels.

### W7 — `_wrap_label_lines` will never split math labels, silently

**Lines:** `_svg_helpers.py` 332–336, 649–652

```python
if _label_has_math(label_text):
    label_lines = [label_text]
else:
    label_lines = _wrap_label_lines(label_text)
```

Math labels are never wrapped. A long label like `"$O(n^2)$ where n is the array length"` (mixed math + prose, > 24 chars) is treated as a single line and the pill width grows unboundedly.

### W8 — `_wrap_label_lines` token boundary: delimiter stays with the preceding line

**Lines:** `_svg_helpers.py` 162–170

When the text is `"foo+bar"` and the break falls at `+`, the token list is `["foo+", "bar"]`. Line 1 becomes `"foo+"` (with trailing `+`), line 2 becomes `"bar"`. This is correct for spaces and commas but looks wrong for `+`, `=`, `-` which conventionally begin the next line in mathematical notation.

---

## 3. Determinism

### 3.1 Annotation iteration order

Annotations are processed in the order they appear in the `placed` list. In `base.py` (lines 379–428), the `placed: list[_LabelPlacement] = []` list is allocated fresh per call to `_emit_annotations`, and annotations are iterated in dict-definition order (Python 3.7+ insertion order). No sorting is applied before placement.

Since the nudge algorithm is greedy and order-dependent (earlier labels are registered as blockers for later ones, but not vice versa), **rearranging annotation definitions changes placement**. The first annotation always lands at its natural position; subsequent annotations are displaced. No stable canonical ordering.

### 3.2 `placed` list scope: per-primitive, not global

Each primitive (`base.py`, `numberline.py`, `queue.py`, `plane2d.py`) allocates its own `placed: list[_LabelPlacement] = []` immediately before its annotation loop. The list is **not** shared across primitives on the same frame. If a frame has two primitives whose SVG viewboxes overlap, their labels do not see each other as blockers.

In `renderer.py`, annotations are converted to plain dicts and passed into the primitive's `render()` method. The renderer does not maintain a cross-primitive collision state. There is no global `placed_labels` registry at the frame level.

### 3.3 The `arrow_index` stagger counter is computed independently in two places

In `base.py` (lines 404–409) and in `arrow_height_above` in `_svg_helpers.py` (lines 845–850), the stagger index is computed by scanning `annotations` before the current annotation. Both scans use the same `target` key match. If `annotations` is modified between the two calls, the stagger in `arrow_height_above` and the stagger in `emit_arrow_svg` can diverge, producing a curve offset that doesn't match the reserved headroom.

---

## 4. What the Abandoned Phase 7 Branch Was Trying to Solve

The `backup/pre-reset-20260421-151848` branch (tip `4a4477d`) represents a complete replacement of the per-primitive nudge loop with a unified, multi-pass placement engine. It was structured in three phases (A, B, C) plus a Phase 7 flip.

### Phase A — Unified engine scaffold and primitive migration

- `scriba/animation/labels/types.py`: `Label`, `Anchor`, `Leader`, `Flexibility` (FIXED / NUDGEABLE / FLEXIBLE), `Direction` (8-way), `LayerHint` (AXIS/GEOMETRY/EDGE_WEIGHT/ANNOTATION/TOP), `LabelStyle`.
- `scriba/animation/layout/engine.py`: `LayoutEngine` with a multi-pass solver operating across all labels in a frame, not per-primitive.
- `scriba/animation/labels/_orchestrator.py`: `LabelOrchestrator` that collects `LabelSource` registrations from primitives, runs the engine, and injects a rendered label layer before `</svg>`.
- `scriba/animation/labels/_feature_flag.py`: `SCRIBA_LABEL_ENGINE` env var (`legacy` / `unified`) gating the new path.
- Each primitive was migrated to register `LabelSource` objects instead of calling `emit_plain_arrow_svg`/`emit_arrow_svg` directly.

The engine replaced W1 (forced-UP stacking) with a **48-candidate nudge grid** using 7 multipliers (`-2, -1, -0.5, 0, 0.5, 1, 2`) in both axes per direction, drawn from side-hint priorities rather than hardcoded UP/LEFT/RIGHT/DOWN.

### Phase B — Advanced placement features

- **Typed side-priority tuples** per `LayerHint` — annotation labels try UP first, edge-weight labels try the 4 diagonal sides first.
- **viewBox grow**: the engine reports a `LayoutIssue` when no candidate fits, and the orchestrator can expand the SVG viewBox to accommodate.
- **`intersect_pill_edge`** — the ray-vs-AABB intersection that computes where a leader line should terminate at the **pill perimeter** rather than the pill center (fixing W4).
- **`_perp_sides_for_edge`** for graph/tree edge-weight labels — slope-aware side hints.
- **`_repulsion.py`** — a force-directed particle solver as a last-resort fallback when the 48-candidate nudge grid is fully exhausted.

### Phase C — Browser-side measure-and-fix pipeline

Phase C introduced `measure_and_fix.js` (versions 0.1–0.7), a self-contained IIFE injected into the HTML output:
- **C.0**: added `data-scriba-label`, `data-scriba-source`, etc. breadcrumbs.
- **C.2**: drift measurement via `getBBox()` vs Python estimate.
- **C.3**: `applyCorrection()` — `transform="translate(dx dy)"` to move drifted labels.
- **C.4**: `redrawLeader()` — recomputes leader Bezier after C.3.
- **C.5**: `growViewBoxIfNeeded()` — rAF-animated viewBox expansion.
- **C.7+C.8**: re-runs pipeline on `scriba:framechanged` event.

### Phase 7 — Flip default and regression baseline

Commit `244cc79` flipped `_DEFAULT_MODE` from `legacy` to `unified`. Commit `539bb5e` added a visual regression baseline: 8/12 scenes clean, 4 scenes on watchlist (`test_label_overlap_1d`: 6 overlaps, `test_label_overlap_2d`: 12, `convex_hull_trick`: 22, `elevator_rides`: 52) — these required the C.3–C.5 browser pipeline to fully resolve.

### Summary of what Phase 7 was solving vs the current `main`

| Problem | Current `main` | Phase 7 branch |
|---|---|---|
| W1 forced-UP stacking | Forced UP, up to 4×nudge_step drift | 48-candidate grid; repulsion solver fallback; LayoutIssue |
| W4 leader to pill center | Leader draws into pill background | `intersect_pill_edge` terminates at pill perimeter |
| W5 clamped-pill blocker mismatch | Registered bbox vs rendered bbox diverge | C.2 drift logging; C.3 transform correction |
| W6 KaTeX width underestimate | No correction | C.2 `getBBox` measures actual rendered width; C.3 corrects |
| Cross-primitive isolation | Per-primitive `placed` list, no global state | Global `LabelOrchestrator` across all primitives in a frame |
| Leader re-anchor after correction | n/a | C.4 redraws leader Bezier after C.3 translate |
| ViewBox overflow | Labels can go off-canvas silently | C.5 grows viewBox with animated transition |
| Frame-change stale layout | n/a | C.7 re-runs pipeline on `scriba:framechanged` |
| Edge-label side bias | UP always first | B.4 slope-aware perpendicular sides per edge |

The branch was reset from `main` on 2026-04-21 rather than merged, most likely because the regression watchlist (`elevator_rides` with 52 overlaps, etc.) was not yet fully resolved server-side and because the C.3–C.5 browser pipeline required a Playwright E2E contract that added CI infrastructure complexity.
