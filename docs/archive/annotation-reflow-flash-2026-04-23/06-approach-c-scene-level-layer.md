# Approach C: Scene-Level Annotation Layer

**Date:** 2026-04-23
**Bug:** Layout flash in `convex_hull_trick.html` step 1 → 2. `\annotate` on `dp.cell[1]` enlarges that primitive's bbox, shifting `h` downward.
**Root cause file:line:** `scriba/animation/_frame_renderer.py:465-474` — `set_annotations(prim_anns)` is called before `bounding_box()` inside the emit loop. A second, earlier pre-scan loop at `_frame_renderer.py:444-449` calls `bounding_box()` without annotations set, so the two loops use inconsistent bbox values. The emit-loop bbox (line 474) is the one used for `y_cursor` accumulation; it is inflated by annotation headroom.

---

## 1. Architecture

### Current data flow

```
\annotate{dp.cell[1]}{...}
  → AnnotationEntry appended to SceneState.annotations    [scene.py:672-681]
  → FrameSnapshot.annotations tuple                        [scene.py:134]
  → _emit_frame_svg():
      for shape_name, prim in primitives:
          prim.set_annotations(prim_anns)                  [_frame_renderer.py:472]
          bbox = prim.bounding_box()   # INFLATED           [_frame_renderer.py:474]
          y_cursor += bh               # pushes h downward  [_frame_renderer.py:540]
          prim.emit_svg(...)
            → emit_annotation_arrows(...)                  [base.py:387-540]
              → emit_arrow_svg / emit_plain_arrow_svg
              → SVG lives inside <g transform="translate(x_off, y_cursor)">
```

Primitives store annotation headroom in `_min_arrow_above` (set via `set_min_arrow_above`). `bounding_box()` adds this to its height, causing the bbox expansion that drives the bug.

### Proposed data flow (Approach C)

```
\annotate{dp.cell[1]}{...}
  → AnnotationEntry in FrameSnapshot.annotations
  → _emit_frame_svg():
      # Phase 1: layout pass — NO set_annotations call
      for shape_name, prim in primitives:
          bbox = prim.bounding_box()   # intrinsic only, stable
          compute x_off, y_cursor
          _prim_offsets[shape_name] = (x_off, y_cursor)
          y_cursor += bh + _PRIMITIVE_GAP

      # Phase 2: primitive emit
      for shape_name, prim in primitives:
          svg_parts.append(f'<g transform="translate({x_off},{y_off})">')
          svg_parts.append(prim.emit_svg(...))   # no annotations
          svg_parts.append("</g>")

      # Phase 3: scene-level annotation emit (new)
      ann_svg = SceneAnnotationRenderer(
          annotations=frame.annotations,
          primitives=primitives,
          prim_offsets=_prim_offsets,
          scene_segments=scene_segments,
      ).emit()
      svg_parts.append(ann_svg)   # after all primitive <g>s

  → </svg>
```

### New module / class responsibilities

**`scriba/animation/_annotation_renderer.py`** (new module)

`SceneAnnotationRenderer` — owns the scene-level annotation emit pass.

Responsibilities:
- Accept `frame.annotations` (tuple of `AnnotationEntry`), the already-laid-out `_prim_offsets` dict, the `primitives` dict, and the pre-built `scene_segments` tuple.
- For each `AnnotationEntry`, resolve the absolute pixel position of the target by calling `prim.resolve_annotation_point(suffix)` and adding `(x_off, y_off)` from `_prim_offsets`.
- Delegate arrow SVG generation to the existing `emit_arrow_svg` / `emit_plain_arrow_svg` / `emit_position_label_svg` functions — no duplication of geometry logic.
- Return a single `<g data-layer="annotations">...</g>` string.

`PrimitiveBase.resolve_annotation_point` (`base.py:359-366`) is the existing coordinate hook; it already returns local-frame `(x, y)`. It requires no signature change — the caller adds the scene offset.

---

## 2. Coordinate Resolution

`resolve_annotation_point(selector)` lives on `PrimitiveBase` (base.py:359). It returns local-frame SVG coordinates for a selector such as `arr.cell[3]` or `G.node[A]`. Each concrete primitive that supports arrow annotations overrides it (Array, DPTable, Graph, etc.). The base class returns `None`.

In the scene-level renderer, the absolute coordinate is:

```
prim_local = prim.resolve_annotation_point(full_selector)
# e.g. resolve_annotation_point("dp.cell[1]") → (cx_local, cy_local)

scene_x = prim_local[0] + prim_offsets[shape_name][0]
scene_y = prim_local[1] + prim_offsets[shape_name][1]
```

The `full_selector` string is already stored in `AnnotationEntry.target` (e.g. `"dp.cell[1]"`). The shape name is extracted by splitting on `"."`.

For `arrow_from` selectors (`AnnotationEntry.arrow_from`), the same lookup applies: split on `"."`, find the source primitive, call `resolve_annotation_point`, add offset. Both source and destination may live in different primitives — this is already a resolved concern because `resolve_annotation_point` is per-primitive and the renderer holds `_prim_offsets` for all of them.

One gap: `resolve_annotation_point` is called with the full selector including the shape name prefix (e.g. `"dp.cell[1]"`). Existing primitive implementations vary in whether they strip the prefix before cell lookup. This should be audited per-primitive during migration (Phase 2) rather than assumed uniform.

---

## 3. Obstacle Avoidance Coupling

The obstacle machinery (`_svg_helpers.py:208-238`, `base.py:419-443`) operates in each primitive's local coordinate frame. The `scene_segments` tuple passed into `emit_annotation_arrows` uses the `_translate_segment` helper (`_svg_helpers.py:208`) to re-express foreign-primitive segments into the consuming primitive's local frame.

Under Approach C, the annotation renderer operates in absolute scene coordinates. The translation logic inverts: rather than translating foreign segments into a primitive's local frame, the scene renderer already works in scene coordinates so all segments must be translated from their primitive-local frames into scene space.

Proposal:

- The scene-level annotation renderer builds a flat `scene_obs` tuple of `_Obstacle` entries by iterating `scene_segments` and applying the **forward** translation: `(seg.x0 + src_x_off, seg.y0 + src_y_off)` (the inverse of the existing `dx = src_x - self_x` pattern in `base.py:432-438`).
- `emit_arrow_svg` / `emit_plain_arrow_svg` accept `primitive_obstacles` as a flat tuple of `_Obstacle`; the scene renderer passes the translated `scene_obs` directly. No change to `_svg_helpers.py` is needed.
- Annotation SVG coordinates are expressed in scene space (after adding `prim_offsets`), so obstacle coordinates must also be in scene space. This is consistent.

**Callers that would break:** `emit_annotation_arrows` in `base.py:387` takes `scene_segments` and `self_offset` and performs the translation internally. After migration, that method is no longer called from the scene renderer — it becomes dead for the migrated path. Tests that call `emit_annotation_arrows` directly on a primitive instance (there are none in the unit test corpus based on reading `test_scoring_unit.py` and `test_scoring_regression.py`) would be unaffected. Any integration tests that invoke `_emit_frame_svg` end-to-end would exercise the new path.

Annotations do not contribute to `resolve_obstacle_segments()`. That contract is unchanged: primitives register their structural segments (edges, cell borders) via `resolve_obstacle_segments`; annotation arrows are only ever consumers of the obstacle set, not contributors to it at layout time.

---

## 4. SVG Z-Order

Currently, annotation SVG is emitted inside each primitive's `<g transform="translate(...)">` block. Its z-order relative to the primitive body depends on where `emit_annotation_arrows` is called within `emit_svg` — typically at the end, so annotations render above cells. There is no known case where annotations intentionally render below the primitive body; the existing behavior is correct-by-convention.

Under Approach C, the annotation `<g data-layer="annotations">` is appended after all primitive `<g>` elements and before `</svg>`. Z-order is now explicit and structurally guaranteed: all annotations are above all primitive bodies. This is strictly better than the current convention-based ordering.

The only edge case to verify: marker `<defs>` for arrowheads are currently emitted via `emit_arrow_marker_defs(parts, annotations)` inside `emit_annotation_arrows`. Under Approach C, marker defs must be emitted either into the top-level `<defs>` block (via `emit_shared_defs` at `_frame_renderer.py:427`) or into a `<defs>` inside the annotation `<g>`. The cleaner option is to add a pass in `SceneAnnotationRenderer.emit()` that pre-collects all needed marker ids and emits one `<defs>` block at the start of the annotation group.

---

## 5. Breaking Changes

### Golden byte-changes

Every frame that contains at least one `\annotate` will produce a different SVG byte string because:
1. The annotation SVG elements move from inside `<g transform="translate(x, y)">` (primitive group) to a top-level `<g data-layer="annotations">`.
2. Coordinates shift from primitive-local to scene-absolute.
3. Marker `<defs>` relocate.

Frames without annotations are unaffected (no `set_annotations` call was made; `bounding_box()` is identical).

### Tests that would catch it

`test_scoring_unit.py` and `test_scoring_regression.py` test the scoring math only (`_score_candidate`, `_nudge_candidates`, `_place_pill`). They do not exercise the SVG emit path and will not catch golden changes.

Annotation-related tests are likely end-to-end golden comparison tests. A scan of `tests/` for `annotate` should be done with the shell; based on reading the test files available, none of the unit test files exercise `_emit_frame_svg` with annotations directly. Golden tests are the primary regression surface.

### Golden scope estimate

To estimate the number of affected goldens, one would check `tests/goldens/` for `*.svg` files and `*.html` files that contain annotation SVG patterns (e.g. `data-annotation`, `emit_arrow_marker_defs`-generated `<marker` elements, or `scriba-annotation` class). Without shell access, a conservative estimate based on the codebase's known example count (several DP, graph, and array examples) is **20-60 golden SVGs** would require re-pinning. All are regenerated in a single pass with `pytest --update-goldens` (or the project's equivalent).

---

## 6. Migration Path

### Phase 1 — Parallel path, flag-gated (1 agent-phase)

Introduce `SceneAnnotationRenderer` in `scriba/animation/_annotation_renderer.py`. In `_emit_frame_svg`, add a boolean flag `_USE_SCENE_ANNOTATION_LAYER` (default `False`). When `True`:
- Skip `set_annotations` calls in the emit loop.
- Remove annotation headroom from `bounding_box()` by not calling `set_annotations` before the pre-scan loop either.
- Append `SceneAnnotationRenderer(...).emit()` after all primitive `<g>` blocks.

When `False`, behavior is identical to today. This allows A/B testing without touching goldens.

### Phase 2 — Migrate primitives one at a time (2-3 agent-phases)

For each primitive (Array, DPTable, Plane2D, Graph, Tree, Queue, etc.):
1. Verify `resolve_annotation_point` handles full-selector strings correctly (e.g. `"dp.cell[1]"` vs `"cell[1]"`).
2. Enable `_USE_SCENE_ANNOTATION_LAYER = True` in CI.
3. Regenerate and re-pin goldens for that primitive's test suite.
4. Delete `set_annotations` dispatch from that primitive's emit path (it becomes dead code for this primitive).

### Phase 3 — Remove primitive-internal path (1 agent-phase)

- Remove `set_annotations` from `PrimitiveBase` and all subclasses.
- Remove `prim._annotations` storage.
- Remove the `set_annotations` dispatch block at `_frame_renderer.py:465-472`.
- Remove the `_USE_SCENE_ANNOTATION_LAYER` flag; the scene-level path is unconditional.
- Regenerate remaining goldens.

Total: approximately 4-5 focused agent-phases.

---

## 7. Selector Semantics

`AnnotationEntry.target` stores the full selector string, e.g. `"dp.cell[1]"` (`scene.py:113`). The shape name is extracted by `split(".", 1)[0]`. This contract is unchanged: targets are declared on primitives; only rendering moves.

`_apply_annotate` in `scene.py:646-681` validates that the shape name exists in `shape_states` at IR time. No parser or IR change is needed. The `Selector` → string conversion in `_selector_to_str` (`scene.py:50-92`) is also unaffected.

The one semantic question: `resolve_annotation_point` is currently called with the full selector including shape prefix. Some primitives call `self.name` to strip it; others may assume the suffix form. This is a per-primitive implementation detail to audit during Phase 2, not a design-level change.

---

## 8. Replay Contract

Frame immutability is unchanged: `FrameSnapshot` is a frozen dataclass (`scene.py:123-135`). The annotations tuple is still derived purely from `FrameSnapshot.annotations`.

The emit order for annotation SVG must be deterministic. `SceneAnnotationRenderer` iterates `frame.annotations` in tuple order (which is insertion order from `SceneState.annotations`, a plain list). This is the same order annotations were previously processed within each primitive. As long as the scene-level renderer iterates `frame.annotations` in a single linear pass — same order, no set operations — SVG output is byte-identical across re-runs for the same input.

Pin: `SceneAnnotationRenderer.emit()` iterates `annotations` in index order (0, 1, 2, …). No sorting, no grouping by primitive until coordinate lookup. The resulting `<g data-layer="annotations">` contains elements in the same relative order as the current per-primitive output, just with all primitives' annotations interleaved in their declaration order rather than clustered by primitive. This interleaving is a byte-change vs. current (where array annotations all precede dp annotations), but is deterministic and stable.

---

## 9. Interaction with Approaches A and B

**Approach C vs A (gutter reservation):** Approach A reserves a stable vertical gutter above each primitive so `bounding_box()` returns the same height regardless of whether annotations are present in a given frame. Once Approach C is in place, `bounding_box()` is annotation-unaware by construction — no gutter is needed because annotations never affect bbox. Approach C makes Approach A unnecessary. Implementing both would be redundant; C is strictly a superset of A's layout-stability benefit.

**Approach C + B (opacity transitions):** Approach B adds per-annotation CSS opacity transitions. With annotations in a scene-level `<g>`, the transition can be applied to the entire `<g data-layer="annotations">` or to individual annotation child elements. Fade-in/out is trivially independent of primitive `<g>` transitions. C makes B easier to implement cleanly because the annotation layer has a single, stable DOM anchor.

**Cost comparison:** Approach A is a targeted two-line fix (pre-reserve gutter; skip `set_annotations` before pre-scan). Approach C is a 4-5 phase refactor with golden regeneration. Approach C eliminates the entire class of annotation-layout coupling, not just the specific flash. If future features (e.g. cross-primitive arrows, annotation z-ordering, CSS transitions on annotations) are planned, C pays off. If only the immediate flash matters, A is sufficient and lower risk.

---

## 10. Implementation Sketch

```python
# scriba/animation/_annotation_renderer.py

from __future__ import annotations
from typing import Any
from scriba.animation.primitives._svg_helpers import (
    emit_arrow_svg, emit_plain_arrow_svg, emit_position_label_svg,
    emit_arrow_marker_defs, _segment_to_obstacle, _translate_segment,
    _LabelPlacement,
)


class SceneAnnotationRenderer:
    def __init__(
        self,
        annotations: tuple[Any, ...],           # AnnotationEntry tuple
        primitives: dict[str, Any],             # shape_name -> PrimitiveBase
        prim_offsets: dict[str, tuple[float, float]],
        scene_segments: tuple[Any, ...],        # (ObstacleSegment, x, y, prim_id)
        render_inline_tex: Any | None = None,
    ) -> None:
        self._annotations = annotations
        self._primitives = primitives
        self._offsets = prim_offsets
        self._scene_segs = scene_segments
        self._render_tex = render_inline_tex

    def _abs_point(self, selector: str) -> tuple[float, float] | None:
        shape_name = selector.split(".", 1)[0]
        prim = self._primitives.get(shape_name)
        if prim is None:
            return None
        local_pt = prim.resolve_annotation_point(selector)
        if local_pt is None:
            return None
        x_off, y_off = self._offsets[shape_name]
        return (local_pt[0] + x_off, local_pt[1] + y_off)

    def _build_scene_obstacles(self) -> tuple[Any, ...]:
        obs = []
        for seg, sx, sy, _ in self._scene_segs:
            # Translate segment from primitive-local to scene-absolute.
            translated = _translate_segment(seg, sx, sy)
            obs.append(_segment_to_obstacle(translated))
        return tuple(obs)

    def emit(self) -> str:
        if not self._annotations:
            return ""
        parts: list[str] = []
        parts.append('<g data-layer="annotations">')

        ann_dicts = [
            {
                "target": a.target,
                "label": a.text,
                "arrow_from": a.arrow_from or "",
                "color": a.color,
                "position": a.position,
                "arrow": a.arrow,
            }
            for a in self._annotations
        ]
        emit_arrow_marker_defs(parts, ann_dicts)

        scene_obs = self._build_scene_obstacles()
        placed: list[_LabelPlacement] = []
        prior_arrow_segs: list[Any] = []

        for ann, ann_dict in zip(self._annotations, ann_dicts):
            dst_abs = self._abs_point(ann.target)
            if dst_abs is None:
                continue

            # Translate ann_dict coordinates to scene-absolute before passing
            # to emit helpers (helpers work in whatever coordinate space the
            # caller supplies; scene-absolute is consistent here).
            if ann.arrow_from:
                src_abs = self._abs_point(ann.arrow_from)
                if src_abs is None:
                    continue
                new_segs = emit_arrow_svg(
                    parts, ann_dict,
                    src_point=src_abs,
                    dst_point=dst_abs,
                    arrow_index=0,          # recompute per-target if needed
                    cell_height=40,         # TODO: derive from target primitive
                    render_inline_tex=self._render_tex,
                    placed_labels=placed,
                    primitive_obstacles=scene_obs or None,
                )
                if new_segs:
                    prior_arrow_segs.extend(new_segs)
            elif ann_dict.get("arrow"):
                emit_plain_arrow_svg(
                    parts, ann_dict,
                    dst_point=dst_abs,
                    render_inline_tex=self._render_tex,
                    placed_labels=placed,
                    primitive_obstacles=scene_obs or None,
                )
            elif ann.text:
                emit_position_label_svg(
                    parts, ann_dict,
                    anchor_point=dst_abs,
                    cell_height=40,
                    render_inline_tex=self._render_tex,
                    placed_labels=placed,
                    primitive_obstacles=scene_obs or None,
                )

        parts.append("</g>")
        return "\n".join(parts)
```

The `_emit_frame_svg` changes are minimal: remove the `set_annotations` block at lines 465-472, and append `SceneAnnotationRenderer(...).emit()` after line 539 (`svg_parts.append("</g>")`).

---

## 11. Risks and Tech Debt

**`_arrow_cell_height` coupling.** The `emit_arrow_svg` bow geometry uses `cell_height` (a per-primitive setting at `base.py:220`). In the scene-level renderer, this must be sourced from the target primitive: `prim._arrow_cell_height`. This is an internal attribute (`_` prefix), not a stable API. Either promote it to a public property or accept reading the private attribute in `SceneAnnotationRenderer`.

**`arrow_index` stagger.** `emit_arrow_svg` takes `arrow_index` to stagger multiple arrows landing on the same target (`_svg_helpers.py:329`). Currently computed in `emit_annotation_arrows` at `base.py:511-517` by counting preceding annotations to the same target. The scene-level renderer must replicate this count across all annotations in the tuple, grouping by `(target, arrow_from is not None)`.

**`_arrow_layout` and `_arrow_shorten`.** The `layout="2d"` and `shorten_src/dst` kwargs passed to `emit_arrow_svg` in `base.py:519-527` are sourced from per-primitive attributes (`_arrow_layout`, `_arrow_shorten`). The scene renderer must look these up from the target primitive.

**`resolve_annotation_point` full-selector inconsistency.** Some primitives may strip the shape-name prefix internally; others may not. This is a latent bug in the current code masked by the fact that `emit_annotation_arrows` passes the full `ann.get("target")` string. A systematic audit is needed during Phase 2.

**`emit_arrow_marker_defs` duplication.** This is currently called once per primitive that has annotations. In the scene-level renderer it is called once globally. If two primitives use the same marker id (e.g. `scriba-arrow-info`), the current per-primitive `<defs>` inside separate `<g>` scopes are technically redundant but harmless. The scene-level single call is cleaner.

**`set_min_arrow_above`.** The emitter calls `set_min_arrow_above` on primitives to stabilize the translate offset across frames (preventing vertical jitter when some frames have arrows and others don't). Once Approach C is in place, `bounding_box()` no longer includes annotation headroom, so `set_min_arrow_above` becomes irrelevant. It can be removed in Phase 3.

**Existing feature: `\annotate` position-label without arrow.** `emit_position_label_svg` computes a pill offset from the anchor point using `_LABEL_HEADROOM` and the `position` hint (`above`/`below`/`left`/`right`). This is fully coordinate-independent — it only needs the anchor point, which is provided by `resolve_annotation_point` + offset. No special handling needed.

---

**Relevant source anchors:**
- `scriba/animation/_frame_renderer.py:442-479` — bug site (pre-scan + emit loop)
- `scriba/animation/_frame_renderer.py:540` — `y_cursor` advance
- `scriba/animation/scene.py:111-120` — `AnnotationEntry`
- `scriba/animation/scene.py:646-681` — `_apply_annotate`
- `scriba/animation/primitives/base.py:304-306` — `set_annotations`
- `scriba/animation/primitives/base.py:359-366` — `resolve_annotation_point`
- `scriba/animation/primitives/base.py:387-540` — `emit_annotation_arrows`
- `scriba/animation/primitives/_svg_helpers.py:208-238` — `_translate_segment`
