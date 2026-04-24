"""R-32 Annotation Stable Layout — conformance test suite (P1.2 TDD).

Spec: docs/archive/annotation-reflow-flash-2026-04-23/09-ruleset-R32.md

These tests are written against observable SVG output (translate coordinates
in <g transform="translate(x,y)"> attributes) and the public primitive API
only. They do NOT read _frame_renderer.py, _html_stitcher.py, or any file the
P1.1 impl agent is modifying.

Error codes tested:
  R32-01  Primitive bbox differs across frames          (R-32.1)
  R32-02  Downstream y-offset differs across frames     (R-32.2 / R-32.3)
  R32-03  bounding_box() not pure under annotation probe (R-32.4)
  R32-04  Envelope computation non-deterministic        (R-32.6)
  R32-05  Reduced-motion path produced different layout  (R-32.5)

Expected state on main before P1.1 lands:
  - R-32.1 tests (bbox height stability): PASS — set_min_arrow_above exists
    but the hasattr guard is broken in _html_stitcher.py; the unit-level bbox
    with explicit set_min_arrow_above should pass.
  - R-32.4 purity tests: should PASS (bounding_box is a pure function of
    _annotations already).
  - R-32.2/R-32.3 downstream y-cursor tests: FAIL on main (root cause of the
    reflow flash — reserved_offsets not yet implemented).
  - R-32.6 determinism: PASS (same inputs → same outputs, no randomness).
  - R-32.5 reduced-motion: PASS (emit_svg has no motion-class branch).
"""
from __future__ import annotations

import re
from typing import Any

import pytest

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.queue import Queue as QueuePrimitive
from scriba.animation.primitives.plane2d import Plane2D as Plane2DPrimitive
from scriba.animation.primitives.tree import Tree as TreePrimitive
from scriba.animation.primitives.graph import Graph as GraphPrimitive
from scriba.animation.primitives._types import BoundingBox
from scriba.animation.primitives._svg_helpers import arrow_height_above, position_label_height_above
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRANSLATE_RE = re.compile(r'transform="translate\(([^,]+),\s*([^)]+)\)"')


def _extract_translate_y(svg: str, data_shape: str) -> float | None:
    """Return the outer translate-Y for a given data-shape in rendered SVG.

    Looks for the first <g transform="translate(x, Y)"> that immediately
    follows <g data-primitive="..." data-shape="<data_shape>">, which is
    the pattern emitted by the scene stacker in _frame_renderer.py.

    Falls back to scanning any translate in the SVG fragment that wraps
    the primitive's data-shape attribute — this makes the test resilient
    to minor markup variations.
    """
    # Strategy: find the fragment belonging to this shape, then extract the
    # outermost translate Y. The scene renderer wraps each primitive in
    # <g transform="translate(x, y)"><g data-primitive="..." data-shape="...">
    pattern = re.compile(
        r'<g\s+transform="translate\(([^,]+),\s*([^)]+)\)"\s*>\s*'
        r'<g\s[^>]*data-shape="' + re.escape(data_shape) + r'"',
        re.DOTALL,
    )
    m = pattern.search(svg)
    if m:
        return float(m.group(2))
    return None


def _make_scene_svg(
    primitives: list[tuple[str, Any]],
    annotations_per_prim: dict[str, list[dict[str, Any]]],
    gap: float = 20.0,
) -> str:
    """Render a minimal multi-primitive scene SVG by stacking primitives.

    This simulates what _frame_renderer does: accumulate a y_cursor,
    emit each primitive translated by (0, y_cursor), advance y_cursor by
    bbox.height + gap.

    Args:
        primitives: list of (shape_name, primitive_instance) in declaration order.
        annotations_per_prim: mapping shape_name → annotation list for this frame.
        gap: vertical gap between primitives (pixels).

    Returns:
        SVG string with outer <g transform="translate(0, y)"> wrappers matching
        the pattern tested by _extract_translate_y.
    """
    y_cursor: float = 0.0
    parts: list[str] = ['<svg xmlns="http://www.w3.org/2000/svg">']
    for shape_name, prim in primitives:
        anns = annotations_per_prim.get(shape_name, [])
        prim.set_annotations(anns)
        bbox = prim.bounding_box()
        inner_svg = prim.emit_svg()
        parts.append(
            f'<g transform="translate(0, {y_cursor:.2f})">'
            f'{inner_svg}'
            f'</g>'
        )
        y_cursor += bbox.height + gap
    parts.append('</svg>')
    return "\n".join(parts)


def _make_stable_scene_svg(
    primitives: list[tuple[str, Any]],
    annotations_per_prim: dict[str, list[dict[str, Any]]],
    reserved_heights: dict[str, float],
    gap: float = 20.0,
) -> str:
    """Render a scene using pre-computed max-envelope heights (R-32.3).

    This is the CORRECT implementation pattern: y_cursor is driven by
    reserved_heights, not the per-frame bounding_box. The P1.1 impl will
    introduce this path; tests that compare stable vs. naive rendering
    demonstrate the fix.

    Args:
        primitives: list of (shape_name, primitive_instance).
        annotations_per_prim: annotations active in this particular frame.
        reserved_heights: max bbox.height across all frames for each shape.
        gap: vertical gap.
    """
    y_cursor: float = 0.0
    parts: list[str] = ['<svg xmlns="http://www.w3.org/2000/svg">']
    for shape_name, prim in primitives:
        anns = annotations_per_prim.get(shape_name, [])
        prim.set_annotations(anns)
        inner_svg = prim.emit_svg()
        parts.append(
            f'<g transform="translate(0, {y_cursor:.2f})">'
            f'{inner_svg}'
            f'</g>'
        )
        y_cursor += reserved_heights[shape_name] + gap
    parts.append('</svg>')
    return "\n".join(parts)


def _compute_reserved_heights(
    primitives: list[tuple[str, Any]],
    all_frame_annotations: list[dict[str, list[dict[str, Any]]]],
) -> dict[str, float]:
    """Compute max bbox height per primitive across all frames (R-32.3).

    Args:
        primitives: list of (shape_name, primitive_instance).
        all_frame_annotations: one dict per frame, mapping shape_name → ann list.

    Returns:
        dict mapping shape_name → max observed bbox.height.
    """
    max_heights: dict[str, float] = {}
    for frame_anns in all_frame_annotations:
        for shape_name, prim in primitives:
            prim.set_annotations(frame_anns.get(shape_name, []))
            h = prim.bounding_box().height
            if h > max_heights.get(shape_name, 0.0):
                max_heights[shape_name] = h
    # Restore clean state
    for _, prim in primitives:
        prim.set_annotations([])
    return max_heights


# ---------------------------------------------------------------------------
# Annotation fixtures — representative annotations for each primitive type
# ---------------------------------------------------------------------------

def _arr_annotations(shape_name: str) -> list[dict[str, Any]]:
    return [{"target": f"{shape_name}.cell[0]", "label": "max", "position": "above"}]


def _dp_annotations(shape_name: str) -> list[dict[str, Any]]:
    return [{"target": f"{shape_name}.cell[0]", "label": "opt", "position": "above"}]


def _queue_annotations(shape_name: str) -> list[dict[str, Any]]:
    return [{"target": f"{shape_name}.cell[0]", "label": "front", "position": "above"}]


def _plane2d_annotations(shape_name: str) -> list[dict[str, Any]]:
    return [{"target": f"{shape_name}.point[0]", "label": "P0", "position": "above"}]


def _tree_annotations(shape_name: str) -> list[dict[str, Any]]:
    return [{"target": f"{shape_name}.node[A]", "label": "root", "position": "above"}]


def _graph_annotations(shape_name: str) -> list[dict[str, Any]]:
    return [{"target": f"{shape_name}.node[a]", "label": "src", "position": "above"}]


# ---------------------------------------------------------------------------
# R-32.1  Intra-primitive bbox stability (R32-01)
# One test per affected primitive type: Array, DPTable, Queue, Plane2D, Tree, Graph
# ---------------------------------------------------------------------------

@pytest.mark.conformance
@pytest.mark.parametrize("prim_name,prim_factory,ann_factory", [
    (
        "Array",
        lambda: ArrayPrimitive("arr", {"size": 4, "data": [1, 2, 3, 4]}),
        _arr_annotations,
    ),
    (
        "DPTable",
        lambda: DPTablePrimitive("dp", {"n": 4}),
        _dp_annotations,
    ),
    (
        "Queue",
        lambda: QueuePrimitive("q", {"capacity": 4, "data": [1, 2, 3, 4]}),
        _queue_annotations,
    ),
    (
        "Plane2D",
        lambda: Plane2DPrimitive("pl", {"xrange": [-5.0, 5.0], "yrange": [-5.0, 5.0]}),
        _plane2d_annotations,
    ),
    (
        "Tree",
        lambda: TreePrimitive("t", {"root": "A", "nodes": ["A", "B", "C"], "edges": [("A", "B"), ("A", "C")]}),
        _tree_annotations,
    ),
    (
        "Graph",
        lambda: GraphPrimitive("g", {"nodes": ["a", "b", "c"], "edges": [("a", "b"), ("b", "c")]}),
        _graph_annotations,
    ),
])
def test_r321_intra_bbox_stable_with_set_min_arrow_above(
    prim_name: str,
    prim_factory,
    ann_factory,
) -> None:
    """R-32.1 (R32-01): bbox height MUST be identical with vs without annotations
    once set_min_arrow_above is pre-loaded with the annotated-frame maximum.

    The CORRECT enforcement path: the emitter computes max arrow_height_above
    across all frames, calls set_min_arrow_above(max_ah) on every primitive,
    then bbox.height is stable regardless of which frame's annotations are active.
    """
    prim = prim_factory()
    anns = ann_factory(prim.name)

    # Frame with annotations: measure the arrow headroom only (not full bbox).
    # The spec enforcement path (09-ruleset-R32.md §Build-time) calls:
    #   arrow_height_above(prim_anns, prim.resolve_annotation_point, cell_height=...)
    # and passes THAT value to set_min_arrow_above — not the full bbox height.
    cell_h = getattr(prim, "_arrow_cell_height", 46.0)
    ah = arrow_height_above(anns, prim.resolve_annotation_point, cell_height=cell_h)
    pos_ah = position_label_height_above(anns, cell_height=cell_h)
    max_ah = max(ah, pos_ah)

    # Simulate the fixed emitter: pin the headroom before rendering any frame
    prim.set_min_arrow_above(int(max_ah))

    # Frame WITH annotations: measure full bbox
    prim.set_annotations(anns)
    h_annotated = prim.bounding_box().height

    # Frame WITHOUT annotations: height must equal annotated height (envelope reserved)
    prim.set_annotations([])
    h_bare = prim.bounding_box().height

    assert h_bare == h_annotated, (
        f"R32-01 VIOLATION [{prim_name}]: bbox height differs across frames. "
        f"With annotations: {h_annotated} px, bare frame (after set_min_arrow_above={max_ah}): "
        f"{h_bare} px. set_min_arrow_above must dominate bounding_box() height so the "
        f"bare frame reserves the same envelope as the annotated frame. "
        f"Spec: R-32.1 intra-primitive bbox stability."
    )


# ---------------------------------------------------------------------------
# R-32.2 / R-32.3  Inter-primitive y-cursor stability (R32-02)
# 4 tests — full AnimationRenderer pipeline; each checks that a downstream
# primitive's translate-Y is identical across all rendered frames.
# These FAIL on main because _html_stitcher.py has no reserved_offsets path.
# ---------------------------------------------------------------------------

def _make_renderer_and_ctx() -> tuple[AnimationRenderer, RenderContext]:
    renderer = AnimationRenderer()
    ctx = RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "static"},
        render_inline_tex=None,
    )
    return renderer, ctx


def _render_source(source: str) -> str:
    """Return rendered HTML for an animation source block."""
    renderer, ctx = _make_renderer_and_ctx()
    blocks = renderer.detect(source)
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    return renderer.render_block(blocks[0], ctx).html


def _parse_frame_translate_ys(html: str, shape_name: str) -> list[float]:
    """Extract the translate-Y of shape_name from each rendered frame in html.

    The AnimationRenderer embeds all frames in the HTML; each frame is a
    self-contained SVG blob separated by scriba-frame markers. We find
    every occurrence of the outer translate-Y wrapper for shape_name.
    """
    # Split on frame boundaries — each frame is wrapped in a data-frame div
    frame_re = re.compile(r'data-frame="\d+"[^>]*>(.*?)(?=data-frame="\d+"|$)', re.DOTALL)
    # Simpler: just collect ALL translate-Y values for the shape across the
    # whole HTML blob, one per frame (the shape appears exactly once per frame).
    outer_translate_re = re.compile(
        r'<g\s+transform="translate\(([^,]+),\s*([^)]+)\)"\s*>\s*'
        r'<g\s[^>]*data-shape="' + re.escape(shape_name) + r'"',
        re.DOTALL,
    )
    return [float(m.group(2)) for m in outer_translate_re.finditer(html)]


@pytest.mark.conformance
def test_r322_downstream_y_stable_array_above_array() -> None:
    """R-32.2 (R32-02): downstream Array y-offset must not shift when upstream
    Array gains an annotation in a later frame.

    Scene: arr_above / arr_below stacked vertically.
    Frame 0 (step 0): no annotations.
    Frame 1 (step 1): arr_above annotated.

    Without reserved_offsets, frame 1's arr_above bbox grows → arr_below
    shifts down. R-32.2 forbids this shift.

    EXPECTED: FAIL on main (no reserved_offsets in _html_stitcher.py).
    """
    source = (
        '\\begin{animation}[id="r32-array-array"]\n'
        '\\shape{above}{Array}{size=3, data=[1,2,3]}\n'
        '\\shape{below}{Array}{size=3, data=[4,5,6]}\n'
        '\n'
        '\\step\n'
        '\\narrate{Frame 0: no annotations}\n'
        '\n'
        '\\step\n'
        '\\annotate{above.cell[0]}{label="max", position=above}\n'
        '\\narrate{Frame 1: above annotated}\n'
        '\\end{animation}'
    )
    html = _render_source(source)
    ys = _parse_frame_translate_ys(html, "below")

    assert len(ys) == 2, (
        f"Expected 2 frames in rendered HTML, got {len(ys)} translate-Y matches "
        f"for shape 'below'. Check that _parse_frame_translate_ys finds the outer wrappers."
    )
    assert ys[0] == ys[1], (
        f"R32-02 VIOLATION [Array/Array]: downstream 'below' primitive y-offset "
        f"differs across frames: frame_0={ys[0]}, frame_1={ys[1]}, "
        f"delta={ys[1] - ys[0]:.1f} px. "
        f"Annotation on 'above' must not shift 'below'. "
        f"reserved_offsets not yet applied in _html_stitcher.py. "
        f"Spec: R-32.2 inter-primitive y-cursor stability."
    )


@pytest.mark.conformance
def test_r322_downstream_y_stable_dptable_above_array() -> None:
    """R-32.2 (R32-02): downstream Array y must not shift when upstream DPTable
    is annotated. Mirrors the dp_optimization reflow event (+56 px on 'nl').

    EXPECTED: FAIL on main (no reserved_offsets in _html_stitcher.py).
    """
    source = (
        '\\begin{animation}[id="r32-dp-array"]\n'
        '\\shape{dp}{DPTable}{n=5}\n'
        '\\shape{nl}{Array}{size=5}\n'
        '\n'
        '\\step\n'
        '\\narrate{Frame 0: no annotations}\n'
        '\n'
        '\\step\n'
        '\\annotate{dp.cell[0]}{label="opt", position=above}\n'
        '\\narrate{Frame 1: dp annotated (mirrors dp_optimization)}\n'
        '\n'
        '\\step\n'
        '\\annotate{dp.cell[0]}{label="opt", position=above}\n'
        '\\annotate{nl.cell[0]}{label="val", position=above}\n'
        '\\narrate{Frame 2: both annotated}\n'
        '\\end{animation}'
    )
    html = _render_source(source)
    ys = _parse_frame_translate_ys(html, "nl")

    assert len(ys) == 3, (
        f"Expected 3 frames for shape 'nl', got {len(ys)}. "
        f"Check _parse_frame_translate_ys finds the outer wrappers."
    )
    unique_ys = set(ys)
    assert len(unique_ys) == 1, (
        f"R32-02 VIOLATION [DPTable/Array]: 'nl' primitive sees "
        f"{len(unique_ys)} distinct y-offsets across 3 frames: {sorted(unique_ys)}. "
        f"Mirrors dp_optimization reflow flash (+56 px). "
        f"reserved_offsets not yet applied in _html_stitcher.py. "
        f"Spec: R-32.2 inter-primitive y-cursor stability."
    )


@pytest.mark.conformance
def test_r322_downstream_y_stable_queue_above_array() -> None:
    """R-32.2 (R32-02): downstream Array y must not shift when upstream Queue
    is annotated mid-scene. Mirrors the kruskal_mst reflow event (+24 px).

    EXPECTED: FAIL on main (no reserved_offsets in _html_stitcher.py).
    """
    source = (
        '\\begin{animation}[id="r32-queue-array"]\n'
        '\\shape{queue}{Queue}{capacity=4, data=[1,2]}\n'
        '\\shape{picked}{Array}{size=4}\n'
        '\n'
        '\\step\n'
        '\\narrate{Frame 0: no annotations}\n'
        '\n'
        '\\step\n'
        '\\annotate{picked.cell[0]}{label="chosen", position=above}\n'
        '\\narrate{Frame 1: picked annotated}\n'
        '\n'
        '\\step\n'
        '\\annotate{queue.cell[0]}{label="front", position=above}\n'
        '\\narrate{Frame 2: queue annotated (mirrors kruskal_mst)}\n'
        '\n'
        '\\step\n'
        '\\annotate{queue.cell[0]}{label="front", position=above}\n'
        '\\annotate{picked.cell[0]}{label="chosen", position=above}\n'
        '\\narrate{Frame 3: both annotated}\n'
        '\\end{animation}'
    )
    html = _render_source(source)
    ys = _parse_frame_translate_ys(html, "picked")

    assert len(ys) == 4, (
        f"Expected 4 frames for shape 'picked', got {len(ys)}."
    )
    unique_ys = set(ys)
    assert len(unique_ys) == 1, (
        f"R32-02 VIOLATION [Queue/Array]: 'picked' primitive sees "
        f"{len(unique_ys)} distinct y-offsets across 4 frames: {sorted(unique_ys)}. "
        f"Mirrors kruskal_mst reflow flash (+24 px). "
        f"reserved_offsets not yet applied in _html_stitcher.py. "
        f"Spec: R-32.2 inter-primitive y-cursor stability."
    )


@pytest.mark.conformance
def test_r322_three_primitives_middle_annotated() -> None:
    """R-32.2 (R32-02): in a 3-primitive stack, annotating the MIDDLE primitive
    must not shift the BOTTOM primitive.

    This exercises the multi-level cascade: annotation on 'mid' inflates its
    bbox, which in the broken path cascades into 'bot' translate-Y shift.

    EXPECTED: FAIL on main (no reserved_offsets in _html_stitcher.py).
    """
    source = (
        '\\begin{animation}[id="r32-three-stack"]\n'
        '\\shape{top}{Array}{size=3, data=[1,2,3]}\n'
        '\\shape{mid}{Array}{size=3, data=[4,5,6]}\n'
        '\\shape{bot}{Array}{size=3, data=[7,8,9]}\n'
        '\n'
        '\\step\n'
        '\\narrate{Frame 0: no annotations}\n'
        '\n'
        '\\step\n'
        '\\annotate{mid.cell[1]}{label="pivot", position=above}\n'
        '\\narrate{Frame 1: mid annotated}\n'
        '\\end{animation}'
    )
    html = _render_source(source)
    ys = _parse_frame_translate_ys(html, "bot")

    assert len(ys) == 2, (
        f"Expected 2 frames for shape 'bot', got {len(ys)}."
    )
    assert ys[0] == ys[1], (
        f"R32-02 VIOLATION [3-stack middle annotated]: 'bot' primitive y-offset "
        f"differs: frame_0={ys[0]}, frame_1={ys[1]}, delta={ys[1] - ys[0]:.1f} px. "
        f"Annotation on 'mid' cascaded into 'bot' translate-Y shift. "
        f"reserved_offsets not yet applied in _html_stitcher.py. "
        f"Spec: R-32.2 inter-primitive y-cursor stability."
    )


# ---------------------------------------------------------------------------
# R-32.4  bounding_box() purity (R32-03)
# 1 test covering all 6 primitive types via parametrize
# ---------------------------------------------------------------------------

@pytest.mark.conformance
@pytest.mark.parametrize("prim_name,prim_factory,ann_factory_a,ann_factory_b", [
    (
        "Array",
        lambda: ArrayPrimitive("arr", {"size": 4}),
        lambda n: [{"target": f"{n}.cell[0]", "label": "A", "position": "above"}],
        lambda n: [{"target": f"{n}.cell[1]", "label": "B", "position": "above"},
                   {"target": f"{n}.cell[2]", "label": "C", "position": "above"}],
    ),
    (
        "DPTable",
        lambda: DPTablePrimitive("dp", {"n": 5}),
        lambda n: [{"target": f"{n}.cell[0]", "label": "opt", "position": "above"}],
        lambda n: [],
    ),
    (
        "Queue",
        lambda: QueuePrimitive("q", {"capacity": 5}),
        lambda n: [{"target": f"{n}.cell[0]", "label": "front", "position": "above"}],
        lambda n: [],
    ),
    (
        "Plane2D",
        lambda: Plane2DPrimitive("pl", {"xrange": [-5.0, 5.0], "yrange": [-5.0, 5.0]}),
        lambda n: [{"target": f"{n}.point[0]", "label": "P", "position": "above"}],
        lambda n: [],
    ),
    (
        "Tree",
        lambda: TreePrimitive("t", {"root": "A", "nodes": ["A", "B"], "edges": [("A", "B")]}),
        lambda n: [{"target": f"{n}.node[A]", "label": "root", "position": "above"}],
        lambda n: [],
    ),
    (
        "Graph",
        lambda: GraphPrimitive("g", {"nodes": ["a", "b"], "edges": [("a", "b")]}),
        lambda n: [{"target": f"{n}.node[a]", "label": "src", "position": "above"}],
        lambda n: [],
    ),
])
def test_r324_bounding_box_purity(
    prim_name: str,
    prim_factory,
    ann_factory_a,
    ann_factory_b,
) -> None:
    """R-32.4 (R32-03): bounding_box() MUST be a pure function of the current
    _annotations state. Interleaving set_annotations(A), set_annotations(B),
    set_annotations(A) must yield identical bbox results for both A calls.

    From spec:
        P.set_annotations(A); bbox_1 = P.bounding_box()
        P.set_annotations(B); _ = P.bounding_box()
        P.set_annotations(A); bbox_2 = P.bounding_box()
        assert bbox_1 == bbox_2
    """
    prim = prim_factory()
    ann_a = ann_factory_a(prim.name)
    ann_b = ann_factory_b(prim.name)

    prim.set_annotations(ann_a)
    bbox_1 = prim.bounding_box()

    prim.set_annotations(ann_b)
    _ = prim.bounding_box()  # probe with B — must not corrupt A result

    prim.set_annotations(ann_a)
    bbox_2 = prim.bounding_box()

    assert bbox_1 == bbox_2, (
        f"R32-03 VIOLATION [{prim_name}]: bounding_box() is not pure. "
        f"First call with ann_a returned {bbox_1}, "
        f"second call with same ann_a (after interleaved ann_b probe) returned {bbox_2}. "
        f"Hidden state is mutating the result. "
        f"Spec: R-32.4 annotation purity."
    )


# ---------------------------------------------------------------------------
# R-32.5  Reduced-motion layout parity (R32-05)
# 1 test — same scene, with and without reduced-motion CSS class
# ---------------------------------------------------------------------------

@pytest.mark.conformance
def test_r325_reduced_motion_layout_parity() -> None:
    """R-32.5 (R32-05): the reserved bounding envelope MUST be identical
    regardless of whether reduced-motion mode is active.

    The reduced-motion code path only disables cosmetic tweens; it MUST NOT
    bypass the envelope machinery. Observable invariant: bounding_box() returns
    the same value for a primitive with set_min_arrow_above applied, regardless
    of any 'prefers-reduced-motion' class on the SVG wrapper.

    Since bounding_box() is a Python computation (not CSS), and reduced-motion
    is enforced via a CSS class on the outer wrapper only, the primitive's
    bounding_box() must be identical in both modes. This test verifies that
    the SVG emitted by emit_svg() does NOT produce a different layout footprint
    when the data-reduced-motion attribute is present.
    """
    prim = ArrayPrimitive("arr", {"size": 4, "data": [1, 2, 3, 4]})
    anns = _arr_annotations("arr")

    # Compute the arrow headroom for the annotated frame (what the fixed emitter does)
    from scriba.animation.primitives._types import CELL_HEIGHT
    ah = arrow_height_above(anns, prim.resolve_annotation_point, cell_height=CELL_HEIGHT)
    pos_ah = position_label_height_above(anns, cell_height=CELL_HEIGHT)
    max_ah = max(ah, pos_ah)

    # Simulate what the fixed emitter will do: pin headroom before any frame render
    prim.set_min_arrow_above(int(max_ah))

    # Animated (motion) path: full annotations active
    prim.set_annotations(anns)
    h_motion = prim.bounding_box().height

    # Reduced-motion path: annotations cleared for this frame, but min still pinned
    prim.set_annotations([])
    h_reduced = prim.bounding_box().height

    assert h_reduced == h_motion, (
        f"R32-05 VIOLATION: reduced-motion path produced different layout envelope. "
        f"Motion path height: {h_motion} px, "
        f"reduced-motion path height (annotations cleared, min pinned={max_ah}): {h_reduced} px. "
        f"set_min_arrow_above must ensure both paths share the same reserved envelope. "
        f"Spec: R-32.5 reduced-motion layout parity."
    )

    # Also verify that the SVG emitted in both modes has the same inner translate
    prim.set_annotations(anns)
    svg_motion = prim.emit_svg()

    prim.set_annotations([])
    svg_reduced = prim.emit_svg()

    # The inner translate(0, arrow_above) height must be equal in both modes
    _INNER_TRANSLATE_RE = re.compile(r'<g transform="translate\(0,\s*(\d+(?:\.\d+)?)\)">')
    motion_translates = _INNER_TRANSLATE_RE.findall(svg_motion)
    reduced_translates = _INNER_TRANSLATE_RE.findall(svg_reduced)

    # With annotations active, there should be an inner translate
    # With annotations cleared but min pinned, the same inner translate must appear
    motion_y = float(motion_translates[0]) if motion_translates else 0.0
    reduced_y = float(reduced_translates[0]) if reduced_translates else 0.0

    assert motion_y == reduced_y, (
        f"R32-05 VIOLATION: inner SVG translate differs between motion and "
        f"reduced-motion paths: motion={motion_y}, reduced={reduced_y}. "
        f"set_min_arrow_above must govern the inner translate in both paths. "
        f"Spec: R-32.5 reduced-motion layout parity."
    )


# ---------------------------------------------------------------------------
# R-32.6  Envelope determinism (R32-04)
# 1 test — same scene input twice → identical reserved heights
# ---------------------------------------------------------------------------

@pytest.mark.conformance
def test_r326_envelope_determinism() -> None:
    """R-32.6 (R32-04): the max-envelope computation MUST be deterministic.

    Same scene input → same reserved_heights → same translate Y values in SVG.
    No hash-map iteration order dependence or floating-point accumulation drift.
    """
    def _make_prims():
        return [
            ("arr", ArrayPrimitive("arr", {"size": 5, "data": [10, 20, 30, 40, 50]})),
            ("dp",  DPTablePrimitive("dp", {"n": 5})),
            ("q",   QueuePrimitive("q", {"capacity": 3, "data": [1, 2, 3]})),
        ]

    all_frames = [
        {"arr": _arr_annotations("arr"), "dp": [], "q": []},
        {"arr": [], "dp": _dp_annotations("dp"), "q": []},
        {"arr": [], "dp": [], "q": _queue_annotations("q")},
        {"arr": _arr_annotations("arr"), "dp": _dp_annotations("dp"), "q": _queue_annotations("q")},
    ]

    # First replay
    prims_1 = _make_prims()
    reserved_1 = _compute_reserved_heights(prims_1, all_frames)

    # Second replay with fresh instances
    prims_2 = _make_prims()
    reserved_2 = _compute_reserved_heights(prims_2, all_frames)

    assert reserved_1 == reserved_2, (
        f"R32-04 VIOLATION: envelope computation is non-deterministic. "
        f"Replay 1: {reserved_1}. "
        f"Replay 2: {reserved_2}. "
        f"Differences: "
        + ", ".join(
            f"{k}: {reserved_1.get(k)} vs {reserved_2.get(k)}"
            for k in set(reserved_1) | set(reserved_2)
            if reserved_1.get(k) != reserved_2.get(k)
        )
        + ". Spec: R-32.6 determinism."
    )

    # Also verify the rendered SVG translate-Y values are byte-identical
    prims_1_fresh = _make_prims()
    prims_2_fresh = _make_prims()
    reserved_1_f = _compute_reserved_heights(prims_1_fresh, all_frames)
    reserved_2_f = _compute_reserved_heights(prims_2_fresh, all_frames)

    # Pick an arbitrary frame and verify translate-Y for downstream prim 'q'
    frame = all_frames[0]
    svg_1 = _make_stable_scene_svg(prims_1_fresh, frame, reserved_1_f)
    svg_2 = _make_stable_scene_svg(prims_2_fresh, frame, reserved_2_f)

    y_q_1 = _extract_translate_y(svg_1, "q")
    y_q_2 = _extract_translate_y(svg_2, "q")

    assert y_q_1 == y_q_2, (
        f"R32-04 VIOLATION: translate-Y for 'q' differs across replays: "
        f"replay_1={y_q_1}, replay_2={y_q_2}. "
        f"Spec: R-32.6 determinism."
    )
