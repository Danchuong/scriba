# Approach A: Reserve Gutter — Design Document

**Date:** 2026-04-23
**Branch:** feat/smart-label-v2.0.0

---

## Background

The layout flash occurs because `_emit_frame_svg` (`_frame_renderer.py:464-540`) calls `prim.set_annotations(prim_anns)` then `prim.bounding_box()` in the per-frame vertical-stacking loop. When `dp`'s annotation appears in step 2, its height grows, and `y_cursor` advances further before `h` is placed, snapping it downward with no transition.

A partial fix already exists: `emit_animation_html` (`_html_stitcher.py:151-170`) pre-scans all frames and calls `prim.set_min_arrow_above(max_ah)` so that `arrow_height_above` is floor-clamped. However, this only stabilises the **within-primitive** translate offset (`arrow_above`). It does **not** stabilise the `y_cursor` accumulation in `_emit_frame_svg`, because `bounding_box()` is called after `set_annotations()` there with only the current frame's annotations (`_frame_renderer.py:466-475`). The floor-clamping already landed for the `_arrow_height_above` / `set_min_arrow_above` path (Queue, Array), but the `y_cursor` accumulation in the main stacking loop does not yet use these stabilised heights consistently for all primitives.

---

## 1. Algorithm Specification

### Pre-scan Phase

```
function _prescan_annotation_heights(frames, primitives):
    # Data structures
    max_bbox: dict[shape_name, BoundingBox] = {}   # per-primitive max envelope

    for frame in frames:
        for shape_name, prim in primitives.items():
            # Collect this frame's annotations for this primitive
            prim_anns = [a for a in frame.annotations
                         if a.get("target", "").startswith(shape_name + ".")]

            # Probe bounding box under this frame's annotation load
            if hasattr(prim, "set_annotations"):
                prim.set_annotations(prim_anns)
            bbox = prim.bounding_box()

            # Accumulate max per dimension
            prev = max_bbox.get(shape_name)
            if prev is None:
                max_bbox[shape_name] = bbox
            else:
                max_bbox[shape_name] = BoundingBox(
                    x=prev.x,
                    y=prev.y,
                    width=max(prev.width, bbox.width),
                    height=max(prev.height, bbox.height),
                )

    # Reset annotation state to empty before rendering begins
    for shape_name, prim in primitives.items():
        if hasattr(prim, "set_annotations"):
            prim.set_annotations([])

    return max_bbox   # shape_name -> max BoundingBox across all frames
```

### Frame-level `reserved_offsets`

```
function _build_reserved_offsets(max_bbox, primitives, vb_width):
    reserved_offsets: dict[shape_name, (x_off, y_cursor)] = {}
    y_cursor = _PADDING
    for shape_name, prim in primitives.items():
        bbox = max_bbox[shape_name]
        bw, bh = bbox.width, bbox.height
        x_off = (vb_width - bw) // 2
        reserved_offsets[shape_name] = (x_off, y_cursor)
        y_cursor += bh + _PRIMITIVE_GAP
    return reserved_offsets
```

### Where it slots into the pipeline

The call graph is:

```
emit_animation_html  (_html_stitcher.py:101)
  └── _prescan_value_widths(frames, primitives)       # already exists
  └── [NEW] max_bbox = _prescan_annotation_heights(frames, primitives)
  └── viewbox = computed from max_bbox heights
  └── _emit_frame_svg(frame, primitives, ..., reserved_offsets=...)
        └── [MODIFIED] use reserved_offsets for y_cursor stacking
```

The same pattern applies in `emit_interactive_html` (which mirrors the same pre-scan pattern).

### Is the per-frame `y_cursor` loop replaced or wrapped?

The existing `y_cursor` loop in `_emit_frame_svg` (`_frame_renderer.py:463-540`) is **replaced** for the stacking coordinate lookup. The loop still iterates over primitives to emit SVG, but instead of computing `y_cursor += bh + _PRIMITIVE_GAP` from the per-frame `bounding_box()`, it reads its `y_offset` from the pre-computed `reserved_offsets` dict. The `set_annotations` call before `bounding_box` can still run — it is needed for correct rendering of arrows within the primitive — but `y_cursor` no longer derives from the result.

The `_pre_y` accumulation at `_frame_renderer.py:442-449` (which builds `_prim_offsets` for cross-primitive obstacle avoidance) should also switch to the reserved heights, otherwise scene-segment coordinates will jitter.

---

## 2. Per-Primitive Implementation

### Which primitives use `bounding_box()` with annotation-dependent height?

From reading the primitives:

| Primitive | File | `bounding_box` annotation-sensitive? |
|---|---|---|
| ArrayPrimitive | `array.py:355-399` | Yes — adds `arrow_above` from `_annotations` |
| Queue | `queue.py:253-259` | Yes — `_arrow_height_above(self._annotations)` |
| Plane2D | `plane2d.py:597-609` | Yes — `arrow_height_above(self._annotations, ...)` |
| Tree | `tree.py:549-563` | Yes — `arrow_height_above(self._annotations, ...)` |
| Graph | `graph.py:1056-1069` | Yes — `arrow_height_above(self._annotations, ...)` |
| DPTable | not found in primitives/ | Assumed yes (same pattern) |

All five annotation-supporting primitives already own the `_annotations` list via `PrimitiveBase.set_annotations` (`base.py:304-306`). Their `bounding_box()` reads `self._annotations` directly.

### Option 1: `max_bounding_box(all_frames_annotations)` new method

Add a method that accepts the full union of annotation lists across all frames:

```python
def max_bounding_box(self, all_frames_annotations: list[list[dict]]) -> BoundingBox:
    max_h = 0.0
    max_w = 0.0
    for anns in all_frames_annotations:
        self.set_annotations(anns)
        bbox = self.bounding_box()
        max_h = max(max_h, bbox.height)
        max_w = max(max_w, bbox.width)
    self.set_annotations([])
    return BoundingBox(x=0, y=0, width=max_w, height=max_h)
```

**Pros:** Explicit API surface; can be overridden per-primitive if needed; no mutation side-effects visible to callers.

**Cons:** Must be added to every annotation-aware primitive (5 classes + base). Requires a new abstract method or a default in `PrimitiveBase`. Increases the interface contract.

### Option 2: Repeated `set_annotations` + `bounding_box()` in the pre-scan (no new method)

The pre-scan function calls `set_annotations(prim_anns)` + `bounding_box()` in a loop over frames, exactly as shown in §1 above. This is what the existing `_prescan_value_widths` pattern does for `set_value`.

**Pros:** Zero per-primitive changes. Works today for any primitive that already implements `set_annotations` (which all annotation-bearing ones do). The pattern is already established in the codebase.

**Cons:** `bounding_box()` is called once per (frame, primitive) pair during pre-scan — O(F × P) calls where F is frame count and P is primitive count. Primitives that cache internal geometry must tolerate repeated `set_annotations` calls without side effects.

**Decision: Option 2.** It aligns with the existing `_prescan_value_widths` approach, requires no interface changes, and the cost is bounded (see §3). The `set_annotations` + `bounding_box()` call pair is already side-effect-free: it reads `_annotations` and computes `arrow_height_above` statelessly.

---

## 3. Cost Analysis

### Whitespace cost

For frames with no annotation on a given primitive, the gutter reserves the max-frame height. The extra gap appears at the top of the primitive (inside the `<g transform="translate(0, arrow_above)">` group). The percentage overhead depends on how many frames lack annotations relative to those that have them.

For `convex_hull_trick`: the `dp` Array is annotated from step 2 onward. `arrow_above` for a single annotation on a 1D array is approximately 40–60 px (one arc above CELL_HEIGHT=32). Total scene height is roughly `2 × CELL_HEIGHT + annotations_above + gaps + padding` ≈ 250 px. The reserved gutter adds ~50 px to frames 0–1 where no annotation exists — **~20% height increase for those frames' `dp` primitive**, but since the scene `viewbox` was already set to the max, no visible frame-to-frame size change occurs. The blank vertical slot appears as whitespace above the cells in early frames, which is acceptable and less jarring than the snap.

For `maxflow`, `dinic`, `mcmf`: these use Graph primitives. Graph `arrow_above` depends on the annotation arc curvature, typically 50–80 px above node centers. Graph height is ~300 px so the overhead is 15–25% of that primitive's height in non-annotated frames, but again the SVG `viewBox` is already fixed.

**In all cases the whitespace cost is confined to the pre-annotation frames and is invisible as frame-size change.** That is the entire point of the design.

### SVG byte cost

Reserved space does not add SVG elements. The only change is a larger `transform="translate(0, N)"` value in the inner `<g>` for frames without annotations. This is a constant-size string change. **No measurable byte impact.**

### Pre-scan performance cost

The pre-scan iterates over all frames once (on top of the existing `_prescan_value_widths` pass). For a 50-frame animation with 3 primitives, this is 150 `set_annotations` + `bounding_box()` calls. `arrow_height_above` is O(A) where A is annotation count, and `bounding_box()` in all primitives is O(1) arithmetic after that. Total cost is O(F × P × A) ≈ negligible for any realistic editorial.

The existing pre-scan loop at `_html_stitcher.py:152-170` already does a similar O(F × P) pass for `set_min_arrow_above`. The new pre-scan merges naturally with it.

### Determinism

The pre-scan reads frames in the order given by `frames` (a `list[FrameData]`), which is always the document order — deterministic. `dict.items()` iteration on `primitives` is insertion-order-stable in Python 3.7+. `bounding_box()` is a pure function of `_annotations` and primitive geometry. No randomness is introduced. **Replay contract is preserved.**

---

## 4. Edge Cases

### Arrow position depends on rendered content (target pixel coords)

`arrow_height_above` (`_svg_helpers.py`) calls `resolve_annotation_point(selector)` to get the target's (x, y). For Array, this is cell center arithmetic — purely structural, no pixel-dependency on prior rendering. For Graph/Tree, node positions are computed once at construction and stored in `self.positions` — they do not change per-frame unless `apply_command` mutations run. The pre-scan sees the correct positions because it runs after primitives are constructed but before rendering. **No recompute needed per-frame for layout purposes.**

The subtle exception: if `apply_command` (add_node, reparent) runs during a frame and changes Graph/Tree positions, the pre-scan positions are stale by the time that frame renders. However, `add_node`/`reparent` also changes the primitive height independently of annotations. This is a pre-existing problem unrelated to gutter reservation, and is handled separately by the viewbox max-scan that already exists.

### Ephemeral annotations (`ephemeral=true`)

Ephemeral annotations are cleared at each step (`scene.py:208`). They still appear in the frame's `annotations` list for the frame in which they are active. The pre-scan iterates all frames' annotation lists, so ephemeral annotations on step N do contribute to the max bounding box computation. This is correct — a frame with an ephemeral annotation would otherwise snap if its slot is not reserved.

Whether to include ephemeral annotations in max-bbox is a **policy decision**. The safer default is to include them: the reserved gutter never exceeds what was actually rendered at any point in the animation. Excluding ephemeral annotations would require a flag on `AnnotationEntry.ephemeral` and complicates the scan loop with marginal benefit.

### Concurrent / pulsing ephemeral annotations

If step 3 has a persistent annotation and step 4 has an additional ephemeral one, the max height includes step 4's taller bbox, and every other frame is padded to that height. This is correct: the gutter is the global maximum across all frames, and it never exceeds what was actually needed.

### Annotations added then removed

If `\annotate` is persistent (the default), once set it stays in all subsequent frames. If an ephemeral annotation appears only in step 7, the pre-scan includes step 7's bbox and all other frames inherit that height. The gutter stays reserved for the whole animation duration. This is by design: a stable `viewBox` requires the globally tallest state to be the envelope.

---

## 5. Goldens and Test Impact

### Which golden SVGs will byte-change?

Any golden that uses `\annotate` on a primitive that appears as a non-top-level primitive (i.e., has other primitives stacked below it) will have changed `transform` values for downstream primitives in frames that previously had a smaller annotation load.

The most certain candidates are in `tests/` (search for files referencing `annotate` in their source `.tex` / input fixtures, then check their corresponding `_expected*.svg` or inline golden strings). The pre-scan already partially does this stabilisation via `set_min_arrow_above`, so goldens that were re-pinned after that fix may only change for the `y_cursor` delta portion.

**Primitives without annotations:** their `transform` values will also change if any primitive above them grows. Every golden for multi-primitive scenes with `\annotate` is affected.

### Migration plan

1. Run `pytest tests/ -k golden` with `--update-goldens` flag (or the project's equivalent regen script).
2. Visually diff SVGs before/after with a browser to confirm whitespace is the only change.
3. Re-pin all changed goldens in a single commit with message `test: regen goldens for reserve-gutter stable y_cursor`.
4. Add a `pytest.mark` test (e.g. `test_annotation_reflow_no_shift`) that renders `convex_hull_trick` step 1 and step 2, extracts the `transform` of the `h` Array group, and asserts the `y` value is identical across both steps.

---

## 6. Opt-in vs Default

**Recommendation: on by default.**

The existing `set_min_arrow_above` stabilisation is already on by default in `emit_animation_html`. Reserve Gutter is the logical completion of that stabilisation: `set_min_arrow_above` stabilises the within-primitive translate, while reserve gutter stabilises the inter-primitive stacking offset. Applying one without the other is an incomplete fix.

An opt-out scene flag (`reserve_gutter=false`) should be provided only if a concrete use case requires the old snap behavior (e.g. an animation that deliberately shrinks after annotations clear). There is no such use case documented in the codebase.

**Anti-argument:** Extra whitespace in early frames may look odd for scenes with many annotations that appear late. Counter: the blank slot is exactly where the annotation will appear, so it reads as intentional reserved space rather than a layout defect. The snap was the actual visual defect.

---

## 7. Implementation Sketch

The change in `_html_stitcher.py` is an extension of the existing pre-scan loop:

```python
# In emit_animation_html (and emit_interactive_html), after _prescan_value_widths:

# NEW: pre-scan annotation-driven bounding boxes
max_bbox: dict[str, Any] = {}
for frame in frames:
    for shape_name, prim in primitives.items():
        prim_anns = [
            a for a in frame.annotations
            if a.get("target", "").startswith(shape_name + ".")
        ]
        if hasattr(prim, "set_annotations"):
            prim.set_annotations(prim_anns)
        bbox = prim.bounding_box()
        prev = max_bbox.get(shape_name)
        if prev is None:
            max_bbox[shape_name] = bbox
        else:
            from scriba.animation.primitives.base import BoundingBox
            max_bbox[shape_name] = BoundingBox(
                x=prev.x, y=prev.y,
                width=max(prev.width, bbox.width),
                height=max(prev.height, bbox.height),
            )
# Reset annotation state
for shape_name, prim in primitives.items():
    if hasattr(prim, "set_annotations"):
        prim.set_annotations([])

# Build reserved_offsets (replaces per-frame y_cursor stacking)
reserved_offsets: dict[str, tuple[float, float]] = {}
_ry: float = _PADDING
for shape_name, prim in primitives.items():
    bbox = max_bbox.get(shape_name) or prim.bounding_box()
    bw, bh = float(bbox.width), float(bbox.height)
    reserved_offsets[shape_name] = (0.0, _ry)  # x_off resolved in _emit_frame_svg
    _ry += bh + _PRIMITIVE_GAP

# Pass reserved_offsets into _emit_frame_svg
```

In `_emit_frame_svg` (`_frame_renderer.py`):

```python
# Existing _pre_y loop (lines 442-449): replace with reserved_offsets when provided
# New signature addition:
#   reserved_offsets: dict[str, tuple[float, float]] | None = None,

# In the emit loop (lines 463-540):
# BEFORE: y_cursor += bh + _PRIMITIVE_GAP (line 540)
# AFTER:
if reserved_offsets is not None:
    _, y_cursor_next = reserved_offsets.get(shape_name, (0.0, y_cursor))
    # x_off uses reserved width for centering:
    _, _, max_bw, _ = _normalize_bbox(max_bbox[shape_name])
    x_offset = (vb_width - max_bw) // 2
else:
    y_cursor += bh + _PRIMITIVE_GAP  # original path preserved
```

The original y_cursor accumulation at line 540 is retained as a fallback when `reserved_offsets` is `None` (backward-compatible for direct `_emit_frame_svg` callers such as tests).

---

## 8. Risks

### Silent breakage risks

1. **`_prim_offsets` in the pre-scan at `_frame_renderer.py:442-449`** is computed from per-frame `bounding_box()` *before* `set_annotations` is called (it uses bare `prim.bounding_box()` with whatever annotations are currently set from the previous frame's render). This stale-annotations issue means cross-primitive obstacle coordinates jitter even today. Switching `_prim_offsets` to use `reserved_offsets` fixes this too, but requires passing `reserved_offsets` through to `_emit_frame_svg`. Missing this change would leave cross-primitive label placement subtly unstable.

2. **`compute_viewbox` still called in tests directly** (`_frame_renderer.py:114-155`) — it calls `prim.set_annotations(prim_anns)` from a passed annotation list. Tests that call `compute_viewbox` in isolation are unaffected by this change since they don't go through `_html_stitcher`. They will not catch regressions in the reserved-offsets path.

3. **`emit_interactive_html` is a separate code path** (`_html_stitcher.py`) and mirrors the same pre-scan pattern as `emit_animation_html`. If reserve gutter is implemented in `emit_animation_html` only and forgotten in `emit_interactive_html`, the flash persists in the interactive widget. Both must be patched.

### Tests that would catch it

- Any test that renders a multi-primitive scene across frames and compares `transform="translate(x,y)"` of downstream primitives. This does not currently exist as an explicit test — it would need to be added as part of the migration (see §5).
- The `test_min_arrow_above` family of tests (if any exist) would catch regressions to the within-primitive stabilisation, but not to the y_cursor inter-primitive drift.
- Full golden re-pins catch structural SVG changes, but only when re-run. A golden test that was pinned *before* the fix captures the broken layout, not the corrected one.

### Tests that would miss it

- Unit tests against individual primitives (`test_array.py`, etc.) that call `bounding_box()` and `emit_svg()` in isolation: they see a single frame's annotations and never exercise inter-primitive stacking.
- Tests that only assert on pixel dimensions of a single primitive, not on the `translate` of primitives below it.

---

## Key File References

- `scriba/animation/_frame_renderer.py:442-449` — `_prim_offsets` pre-scan (uses stale bbox)
- `scriba/animation/_frame_renderer.py:463-540` — per-frame stacking loop
- `scriba/animation/_html_stitcher.py:129-170` — pre-scan entry point; existing `set_min_arrow_above` loop
- `scriba/animation/primitives/base.py:304-315` — `set_annotations` and `set_min_arrow_above`
- `scriba/animation/primitives/array.py:355-399` — annotation-sensitive `bounding_box()`
- `scriba/animation/primitives/plane2d.py:597-609`, `graph.py:1056-1069`, `tree.py:549-563`, `queue.py:253-259` — same pattern in other primitives
