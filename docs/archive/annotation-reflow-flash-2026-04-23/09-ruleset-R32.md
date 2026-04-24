# R-32 — Annotation Stable Layout (proposed ruleset addition)

**Date:** 2026-04-24
**Status:** Proposed (blocks merge of reflow-flash fix)
**Target doc:** `docs/spec/ruleset.md`
**Related:** R-31 (annotation arrow stroke scope), smart-label R-SL-* (pill placement)
**Originating research:** `docs/archive/annotation-reflow-flash-2026-04-23/01-07`

---

## R-32 Annotation Stable Layout

> **Rule.** The rendered bounding box of any annotation-bearing primitive MUST be identical
> across all frames in a scene, regardless of which frames contain annotations targeting
> that primitive. Annotation headroom MUST be reserved at its per-scene maximum for the
> full scene duration, not only for frames in which annotations are active.

### Applies to

All primitives that accept `\annotate` targets: `Array`, `DPTable`, `Queue`, `Plane2D`,
`Tree`, `Graph`. Any future primitive that implements `set_annotations` inherits this
rule automatically.

### Invariants (normative)

**R-32.1 — Intra-primitive bbox stability.**
For any primitive `P` and any two frames `f_i`, `f_j` in the same scene, the rendered
bounding-box height of `P` when emitted into the SVG stage MUST satisfy
`height(P, f_i) == height(P, f_j)`. The width invariant is the same; implementations MAY
relax width when values (not annotations) drive the delta, provided the widened value is
pre-scanned upstream by the existing `_prescan_value_widths` path.

**R-32.2 — Inter-primitive y-cursor stability.**
For any pair of primitives `P_above`, `P_below` stacked in a scene and any two frames
`f_i`, `f_j`, the rendered y-offset of `P_below` MUST satisfy
`y(P_below, f_i) == y(P_below, f_j)`. This applies whether or not `f_i` or `f_j` contains
annotations on `P_above`, `P_below`, or any other primitive in the scene.

**R-32.3 — Max-envelope reservation.**
The reserved layout envelope for each primitive is the component-wise maximum of
`bounding_box(P, annotations=A_f)` over all frames `f` in the scene, where `A_f` is the
annotation list scoped to `P` in frame `f`. The envelope MUST be computed once at scene
build time and applied uniformly to every frame.

**R-32.4 — Annotation purity.**
For any primitive `P` and any annotation list `A`, the call sequence
`P.set_annotations(A); bbox_1 = P.bounding_box()` followed by
`P.set_annotations(A); bbox_2 = P.bounding_box()` MUST yield `bbox_1 == bbox_2`,
regardless of intervening calls `P.set_annotations(A')` with any other `A'`.
In other words, `bounding_box()` is a pure function of the current `_annotations` state.

**R-32.5 — Reduced-motion parity.**
When `prefers-reduced-motion: reduce` is active, the rendered output MUST still satisfy
R-32.1 and R-32.2. The reduced-motion code path MUST NOT bypass the reserved-envelope
machinery; it only disables the cosmetic tween layer (see §Interaction with animation
rules).

**R-32.6 — Determinism.**
The reserved-envelope computation MUST be deterministic: same scene input → same
envelope → byte-identical SVG emit. No floating-point accumulation differences, no
hash-map iteration-order dependence.

### Rationale

Violation of R-32.2 is the root cause of the annotation-induced reflow flash documented
in `01-mechanics-archaeology.md` and `02-cross-primitive-survey.md`. Eight distinct
displacement events were measured across 10 rendered files; the most severe are:

| file                    | step   | affected primitive | Δy     |
|-------------------------|--------|--------------------|--------|
| `dp_optimization`       | 2 → 3  | `nl`               | +56 px |
| `convex_hull_trick`     | 0 → 1  | `h`                | +52 px |
| `houses_schools`        | 1 → 2  | `cost_val`         | +49 px |
| `kruskal_mst`           | 4 → 5  | `queue`, `picked`  | +24 px |

Each event is a snap — no transition — because the frame switcher at
`_html_stitcher.py` swaps `stage.innerHTML` wholesale; the SVG attribute
`transform="translate(x,y)"` on the outer `<g>` at `_frame_renderer.py:479` changes with
no intermediate keyframe.

An earlier partial fix (`set_min_arrow_above` at `_html_stitcher.py:151-170`) attempted
to enforce R-32.1 for `Array` and `DPTable` but is non-functional: the guard
`hasattr(prim, "_arrow_height_above")` returns `False` because `arrow_height_above` is a
module-level import, not an instance method. R-32 is the fully-specified form of that
latent contract, extended to cover inter-primitive stacking (R-32.2) which
`_min_arrow_above` never addressed.

### Non-requirements (explicitly out of scope)

- **Annotation opacity / draw-in animation.** Governed by existing `annotation_add` path
  in `_script_builder.py:209-280`. R-32 is concerned with layout only.
- **Pill placement deltas inside the reserved envelope.** Governed by smart-label R-SL-*.
  R-32 provides the stable container; R-SL-* decides where inside it the pill lands.
- **Cross-primitive arrows.** Out of scope — see R-31 for arrow stroke emission. If
  future work introduces scene-level arrows, they must not inflate per-primitive
  envelopes; they live in a scene-level overlay (see approach C roadmap).
- **Ephemeral / conditional annotations.** If an annotation appears in frame `f_k` but
  not elsewhere, R-32.3 still applies: `f_k`'s annotation set participates in the max
  envelope. "Ephemeral" is not an escape hatch.

---

## Enforcement

### Build-time (Python pipeline)

**R-32.1 + R-32.3 enforcement:** the intra-primitive part of the contract is satisfied
by extending the existing `set_min_arrow_above` pass in `_html_stitcher.py`:

```python
from scriba.animation.primitives._svg_helpers import arrow_height_above

max_ah: float = 0.0
for frame in frames:
    for shape_name, prim in primitives.items():
        prim_anns = [
            a for a in frame.annotations
            if a.get("target", "").startswith(shape_name + ".")
        ]
        ah = arrow_height_above(
            prim_anns,
            prim.resolve_annotation_point,
            cell_height=getattr(prim, "_cell_height", 46),
        )
        max_ah = max(max_ah, ah)
for prim in primitives.values():
    if hasattr(prim, "set_min_arrow_above"):
        prim.set_min_arrow_above(max_ah)
```

No `hasattr(prim, "_arrow_height_above")` guard. The module-level function handles every
primitive type uniformly.

**R-32.2 + R-32.3 enforcement:** the inter-primitive part is satisfied by a new
`max_bbox` pre-scan, also in `_html_stitcher.py`, run after the `set_min_arrow_above`
loop above:

```python
max_bbox: dict[str, BoundingBox] = {}
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
        max_bbox[shape_name] = (
            bbox if prev is None
            else BoundingBox(
                x=prev.x, y=prev.y,
                width=max(prev.width, bbox.width),
                height=max(prev.height, bbox.height),
            )
        )
# clear annotation state after probe — restore purity
for prim in primitives.values():
    if hasattr(prim, "set_annotations"):
        prim.set_annotations([])

reserved_offsets: dict[str, tuple[float, float]] = {}
y_cursor: float = 0.0
for shape_name in primitives:  # preserve scene.tex declaration order
    bb = max_bbox[shape_name]
    reserved_offsets[shape_name] = (bb.x, y_cursor)
    y_cursor += bb.height + _PRIMITIVE_GAP
```

`reserved_offsets` is threaded into `_emit_frame_svg`; the per-frame `y_cursor`
accumulation at `_frame_renderer.py:540` is replaced by a lookup.

**R-32.4 enforcement:** conformance test. For each primitive type, assert:

```python
def test_bounding_box_purity(prim_factory, ann_set_a, ann_set_b):
    prim = prim_factory()
    prim.set_annotations(ann_set_a)
    bbox_1 = prim.bounding_box()
    prim.set_annotations(ann_set_b)
    _ = prim.bounding_box()
    prim.set_annotations(ann_set_a)
    bbox_2 = prim.bounding_box()
    assert bbox_1 == bbox_2
```

Failure indicates hidden state (e.g., a lazily-mutated cache keyed on call count, not on
annotation content). Such state is forbidden by R-32.4.

**R-32.6 enforcement:** existing golden-SVG byte-equality tests carry this invariant. A
replay test (same seed, same SVG bytes) is already enforced by the smart-label
regression suite and is re-used here.

### Runtime (JS)

R-32 has no JS runtime obligation. The animation layer (Approach B / WAAPI tween) is
governed by a separate contract; it is permitted to assume R-32.2 holds and to optimise
(e.g., skip tween when `|Δy| < 0.5 px`, which will be the case whenever R-32 is honoured).

---

## Conformance tests

Proposed additions to `tests/unit/` and `tests/integration/`:

| Test                                         | Rule covered | Location |
|----------------------------------------------|--------------|----------|
| `test_bounding_box_purity[Array]`            | R-32.4       | `tests/unit/primitives/test_array.py`       |
| `test_bounding_box_purity[DPTable]`          | R-32.4       | `tests/unit/primitives/test_dptable.py`     |
| `test_bounding_box_purity[Queue]`            | R-32.4       | `tests/unit/primitives/test_queue.py`       |
| `test_bounding_box_purity[Plane2D]`          | R-32.4       | `tests/unit/primitives/test_plane2d.py`     |
| `test_bounding_box_purity[Tree]`             | R-32.4       | `tests/unit/primitives/test_tree.py`        |
| `test_bounding_box_purity[Graph]`            | R-32.4       | `tests/unit/primitives/test_graph.py`       |
| `test_frame_height_invariant[convex_hull]`   | R-32.1       | `tests/integration/test_layout_stability.py` |
| `test_downstream_y_invariant[convex_hull]`   | R-32.2       | `tests/integration/test_layout_stability.py` |
| `test_downstream_y_invariant[dp_optimization]` | R-32.2     | `tests/integration/test_layout_stability.py` |
| `test_downstream_y_invariant[houses_schools]` | R-32.2      | `tests/integration/test_layout_stability.py` |
| `test_downstream_y_invariant[kruskal_mst]`   | R-32.2       | `tests/integration/test_layout_stability.py` |
| `test_envelope_determinism[every_example]`   | R-32.6       | `tests/integration/test_layout_stability.py` |
| `test_reduced_motion_layout_parity`          | R-32.5       | `tests/integration/test_layout_stability.py` |

**Shape of the integration test.** For each subject example:

```python
def test_downstream_y_invariant(example_path: Path) -> None:
    html = render(example_path)
    frames = parse_frames(html)  # returns list[dict[shape_name, translate_y]]
    for shape_name in frames[0]:
        ys = {frame[shape_name] for frame in frames}
        assert len(ys) == 1, (
            f"R-32.2 violated: {example_path.name} / {shape_name} "
            f"sees {len(ys)} distinct y-offsets across {len(frames)} frames: {sorted(ys)}"
        )
```

This test fails loudly today against at least 10 of the rendered examples. Passing it is
the merge gate for the Phase 1 fix.

---

## Error codes

Proposed entries for `docs/spec/error-codes.md`:

| Code      | Meaning                                                               | Severity |
|-----------|-----------------------------------------------------------------------|----------|
| `R32-01`  | Primitive bbox differs across frames (R-32.1 violation)               | error    |
| `R32-02`  | Downstream y-offset differs across frames (R-32.2 violation)          | error    |
| `R32-03`  | `bounding_box()` not pure under annotation probe (R-32.4 violation)   | error    |
| `R32-04`  | Max-envelope computation non-deterministic across replays             | error    |
| `R32-05`  | Reduced-motion path produced different layout than motion path        | error    |

Errors surface from the conformance test suite, not from a runtime check in the emitter
itself — R-32 is a build-time contract.

---

## Interaction with existing rules

| Rule            | Interaction |
|-----------------|-------------|
| **R-31** (annotation arrow strokes) | R-31 decides what the arrow SVG looks like; R-32 decides where the owning primitive is placed. Orthogonal; no conflict. |
| **R-SL-*** (smart-label pill placement) | R-32 provides a stable primitive envelope. R-SL-* operates inside that envelope. R-32 is a prerequisite: smart-label scoring is only meaningful if candidates are evaluated against a layout that will not shift mid-animation. |
| **U-05** (dataset-preserving) | R-32.4 is a direct analog. U-05 forbids mutations to intrinsic data driven by annotation presence; R-32.4 forbids mutations to the bbox result driven by annotation-probe call order. Both invariants are "annotation must not leak into primary state." |
| **Reduced-motion accessibility contract** | R-32.5 codifies the existing practice. No new obligation on the animation layer. |
| **Determinism contract** (replay SVG byte-equality) | R-32.6 is a restatement of the existing contract at the envelope layer. Existing golden-SVG tests already enforce it end-to-end; R-32.6 requires it to be maintained as the stitcher changes. |

---

## Migration / golden impact

Adoption of R-32 requires re-pinning goldens for scenes whose previous output violated
R-32.1 or R-32.2. The affected set, per `02-cross-primitive-survey.md`, is bounded at
10 rendered examples with a total of 8 displacement events. The re-pin is a one-shot
operation gated on visual review:

1. Run the full example build with the Phase 0 + Phase 1 fix applied.
2. For each affected example, visually diff `step_N.svg` vs. the previous golden at the
   same step. The diff must be: (a) identical within each primitive's local coord space,
   (b) translated downward in outer `<g transform>` for primitives whose
   `reserved_offsets` changed.
3. If the diff shape matches (a) + (b), the golden is re-pinned. If anything else
   differs, R-32 has interacted with another part of the pipeline and the diff is a bug.

Expected golden churn: 8-20 files. No other example is affected.

---

## Out-of-scope — recorded for future work

- **Approach C** (scene-level annotation overlay) makes R-32.1 vacuous for most
  primitives by removing annotation SVG from inside the primitive `<g>`. R-32.2 remains
  necessary even under C. R-32 is written to survive the C migration unchanged.
- **Dynamic scene composition** (primitives added/removed mid-scene) is not currently
  supported by the pipeline. If it is added, R-32.3's "all frames" quantifier needs a
  precise definition of the primitive lifetime; the current formulation assumes a
  primitive exists for the full scene duration.
- **Multi-scene batching** (replay across scene boundaries) is not covered. R-32 is
  per-scene.

---

## Checklist for the implementer

Before claiming R-32 compliance on a branch:

- [ ] `set_min_arrow_above` guard at `_html_stitcher.py:163` uses `arrow_height_above`
      directly — no `hasattr(prim, "_arrow_height_above")`.
- [ ] `max_bbox` pre-scan exists in both `emit_animation_html` and
      `emit_interactive_html`.
- [ ] `_emit_frame_svg` accepts `reserved_offsets` and falls back to the accumulation
      path when `None`.
- [ ] `_prim_offsets` at `_frame_renderer.py:442` uses `reserved_offsets` when provided
      (fixes L2 landmine from `01-mechanics-archaeology.md:§7`).
- [ ] Every annotation-bearing primitive has a `test_bounding_box_purity` unit test.
- [ ] `test_downstream_y_invariant` passes for `convex_hull_trick`, `dp_optimization`,
      `houses_schools`, `kruskal_mst`.
- [ ] `test_envelope_determinism` passes across all rendered examples.
- [ ] `test_reduced_motion_layout_parity` passes — reduced-motion snap reaches the same
      layout as the animated path, within 0.5 px.
- [ ] Goldens re-pinned only for the 8-20 files in the affected set; visual diff matches
      the expected shape (§Migration above).
- [ ] `docs/spec/ruleset.md` updated with R-32 verbatim from this file.
- [ ] `docs/spec/error-codes.md` updated with R32-01 through R32-05.
- [ ] `docs/spec/svg-emitter.md` updated with the `reserved_offsets` parameter
      contract on `_emit_frame_svg`.
- [ ] `docs/spec/primitives.md` updated with the `bounding_box()` purity contract
      (R-32.4).

---

## One-line summary

> **R-32:** a primitive's rendered bbox is per-scene constant, its stacking offset is
> per-scene constant, and `bounding_box()` is a pure function of `_annotations` state.
> Violations cause reflow flash; enforcement is a max-bbox pre-scan at scene build time.
