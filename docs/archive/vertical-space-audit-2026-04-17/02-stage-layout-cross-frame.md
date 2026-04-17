# Report 2 — Stage Layout & Cross-Frame Y-Stability

## 1. `compute_viewbox` — viewBox Union Logic

**File:** `scriba/animation/emitter.py:274-315`

`compute_viewbox` never reads `bbox.x` or `bbox.y`. It only accumulates `w` and `h` from `_normalize_bbox`, then returns `"0 0 {W} {H}"` always — origin hard-coded to `(0, 0)`.

The caller in `emit_animation_html` (lines 677-688) takes `max(width)` and `max(height)` across all frames plus a baseline no-annotation pass.

Consequence:
- If frame N has annotations pushing height to 200 px and frame N+1 has none (height 120 px), viewBox is locked to 200 px every frame → 80 px dead space in N+1.
- `bbox.y` is always 0 in every primitive, so no negative-y leakage bug — origin is never consulted.

**Root cause of blank top space:** the max-height union (emitter.py:680-687) is intentional jitter prevention but over-reserves for frames without annotations.

## 2. Per-Frame Primitive Arrangement

**File:** `scriba/animation/emitter.py:50-51`

```python
_PADDING = 16        # emitter.py:50
_PRIMITIVE_GAP = 50  # emitter.py:51
```

Both **unconditional module-level constants**. Stacking loop (emitter.py:545-610):
- Starts `y_cursor = _PADDING` (16 px top margin always present)
- After each primitive: `y_cursor += bh + _PRIMITIVE_GAP` (line 610)

`_PRIMITIVE_GAP` (50 px) applied between every pair regardless of annotations. No conditional shrink. **Trailing gap is included in total** — last primitive contributes one extra 50 px at bottom.

## 3. Cross-Frame Y Stability — `set_min_arrow_above`

**Files:** `emitter.py:690-709`, `base.py:378-385`, `array.py:413-422`, `dptable.py:507-512`

Emitter pre-computes `max_ah = max(arrow_height_above(...) for all frames)` and calls `prim.set_min_arrow_above(max_ah)` before rendering frames (emitter.py:690-709, repeated at 889-907 for substories).

`Array._arrow_height_above` (array.py:413-422) and `DPTable._arrow_height_above` (dptable.py:507-512):
```python
return max(computed, getattr(self, "_min_arrow_above", 0))
```

This **locks** `arrow_above` to cross-frame max. In frames with no annotations, `computed = 0`, `_min_arrow_above > 0` → primitive pads `arrow_above` px above cells = blank space. Intentional stability fix; also causes permanent top space.

### Primitives lacking this pattern (cross-frame jitter)

`hashmap.py:229-244`, `numberline.py:198-210`, `queue.py:233-258`, `grid.py:197-208`, `linkedlist.py:221-251`, `variablewatch.py:203-227` — call `arrow_height_above(self._annotations, ...)` directly without consulting `_min_arrow_above`. Their height and translate jitter between frames.

## 4. `arrow_height_above` Callers

| Primitive | Mode | Annotation source |
|---|---|---|
| `array.py:419` | via `_arrow_height_above(annotations)` | per-frame arg |
| `dptable.py:509` | via `_arrow_height_above(annotations)` | per-frame arg |
| `hashmap.py:213, 230` | direct call | current `self._annotations` |
| `numberline.py:198, 327` | direct call | current `self._annotations` |
| `queue.py:233, 246` | direct call | current `self._annotations` |
| `grid.py:197, 315` | direct call | current `self._annotations` |
| `graph.py:868`, `tree.py:942`, `plane2d.py:804` | `_arrow_height_above()` no arg | current `self._annotations` |
| `linkedlist.py:221, 238` | direct call | current frame |
| `variablewatch.py:203, 214` | direct call | current frame |

Only Array and DPTable respect `_min_arrow_above`.

## 5. Unconditional Padding Constants

| Constant | Value | File:Line | Conditional? |
|---|---|---|---|
| `_PADDING` | 16 px | emitter.py:50 | No |
| `_PRIMITIVE_GAP` | 50 px | emitter.py:51 | No |
| `_LABEL_HEADROOM` | 24 px | base.py:152 | No (added inside `arrow_height_above` always) |
| `_STACK_GAP` | 9 px | array.py:51, dptable.py:43 | No |
| `CELL_GAP` | 2 px | base.py:104 | No |

## 6. Concrete Proposals

**A. Decouple viewBox sizing from translate stability.** Track two values: max-height-with-annotations and max-height-without. Use the without-annotations max for frames that have none. Or: keep `_min_arrow_above` for `translate()` only; do not add it to `bounding_box()` height.

**B. Conditional `_LABEL_HEADROOM`** (base.py:1094-1095):
```python
if any(a.get("label") for a in arrow_anns):
    max_height += _LABEL_HEADROOM
```

**C. Extend `_min_arrow_above` to jitter-prone primitives.** Replace direct `arrow_height_above(...)` calls in `hashmap.py:213`, `numberline.py:198`, `queue.py:233`, `grid.py:197`, `linkedlist.py:221`, `variablewatch.py:203` with a `_arrow_height_above()` method respecting `_min_arrow_above`.

**D. Trim trailing `_PRIMITIVE_GAP`.** After the stack loop in viewBox-height summation (emitter.py:312-313):
```python
total_height -= _PRIMITIVE_GAP
total_height += 2 * _PADDING
```
Reclaims 50 px of dead bottom space.
