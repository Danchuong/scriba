"""Regression tests for arrow=true annotation support.

Covers:
  1. renderer serialization: AnnotationEntry.arrow=True survives
     _snapshot_to_frame_data → FrameData.annotations dict.
  2. SVG output: arrow=true produces a <polygon> arrowhead but NO <path>
     Bezier curve; arrow_from produces both.
  3. Both annotations can coexist in the same frame.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.base import emit_plain_arrow_svg
from scriba.animation.renderer import _snapshot_to_frame_data
from scriba.animation.scene import AnnotationEntry, FrameSnapshot, SceneState
from scriba import RenderContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={},
        render_inline_tex=None,
    )


def _make_snap(annotations: tuple[AnnotationEntry, ...]) -> FrameSnapshot:
    return FrameSnapshot(
        index=1,
        shape_states={},
        highlights=frozenset(),
        annotations=annotations,
        bindings={},
        narration=None,
    )


# ---------------------------------------------------------------------------
# 1. Renderer serialization boundary
# ---------------------------------------------------------------------------


class TestRendererSerialization:
    """_snapshot_to_frame_data must pass arrow=True through to the dict."""

    def test_arrow_true_present_in_frame_data(self) -> None:
        snap = _make_snap(
            (AnnotationEntry(target="a.cell[0]", text="X", arrow=True),)
        )
        ctx = _make_ctx()
        fd = _snapshot_to_frame_data(snap, total_frames=1, scene_id="s", ctx=ctx)

        assert len(fd.annotations) == 1
        ann = fd.annotations[0]
        assert ann.get("arrow") is True, (
            "arrow=True must survive renderer → FrameData serialization"
        )

    def test_arrow_false_omitted_from_frame_data(self) -> None:
        """arrow=False (default) must NOT add noise to the dict."""
        snap = _make_snap(
            (AnnotationEntry(target="a.cell[0]", text="X", arrow=False),)
        )
        ctx = _make_ctx()
        fd = _snapshot_to_frame_data(snap, total_frames=1, scene_id="s", ctx=ctx)

        ann = fd.annotations[0]
        assert "arrow" not in ann, (
            "arrow=False (default) must not add a key to the annotation dict"
        )

    def test_arrow_from_unaffected(self) -> None:
        """Existing arrow_from behaviour must not be changed by this fix."""
        snap = _make_snap(
            (
                AnnotationEntry(
                    target="a.cell[2]",
                    text="Y",
                    arrow_from="a.cell[0]",
                ),
            )
        )
        ctx = _make_ctx()
        fd = _snapshot_to_frame_data(snap, total_frames=1, scene_id="s", ctx=ctx)

        ann = fd.annotations[0]
        assert ann.get("arrow_from") == "a.cell[0]"
        assert "arrow" not in ann

    def test_both_annotations_in_same_frame(self) -> None:
        """arrow=true and arrow_from can coexist in the same FrameData."""
        snap = _make_snap(
            (
                AnnotationEntry(target="a.cell[0]", text="X", arrow=True),
                AnnotationEntry(
                    target="a.cell[2]",
                    text="Y",
                    arrow_from="a.cell[0]",
                ),
            )
        )
        ctx = _make_ctx()
        fd = _snapshot_to_frame_data(snap, total_frames=1, scene_id="s", ctx=ctx)

        assert len(fd.annotations) == 2
        plain_ann = fd.annotations[0]
        arc_ann = fd.annotations[1]
        assert plain_ann.get("arrow") is True
        assert "arrow" not in arc_ann
        assert arc_ann.get("arrow_from") == "a.cell[0]"


# ---------------------------------------------------------------------------
# 2. SVG output — Array primitive
# ---------------------------------------------------------------------------


class TestArraySvgOutput:
    """Arrow=true must produce a <polygon> arrowhead with no Bezier <path>."""

    def _make_array(self, annotations: list[dict]) -> ArrayPrimitive:
        inst = ArrayPrimitive("a", {"size": 4})
        inst.set_annotations(annotations)
        return inst

    def test_arrow_true_produces_polygon_no_bezier(self) -> None:
        inst = self._make_array(
            [{"target": "a.cell[0]", "label": "X", "arrow": True}]
        )
        svg = inst.emit_svg()
        assert "<polygon" in svg, "arrow=true must emit a <polygon> arrowhead"
        # A Bezier arc uses <path d="M...C..."> — must be absent for plain arrow
        assert 'C' not in svg or '<path' not in svg.split('<polygon')[0], (
            "arrow=true must not emit a Bezier <path> before the arrowhead"
        )

    def test_arrow_true_produces_line_stem(self) -> None:
        inst = self._make_array(
            [{"target": "a.cell[1]", "label": "X", "arrow": True}]
        )
        svg = inst.emit_svg()
        assert "<line" in svg, "arrow=true must emit a <line> stem"

    def test_arrow_true_has_annotation_group(self) -> None:
        inst = self._make_array(
            [{"target": "a.cell[0]", "label": "X", "arrow": True}]
        )
        svg = inst.emit_svg()
        assert 'class="scriba-annotation' in svg

    def test_arrow_from_produces_bezier_path_and_polygon(self) -> None:
        inst = self._make_array(
            [
                {
                    "target": "a.cell[2]",
                    "label": "Y",
                    "arrow_from": "a.cell[0]",
                }
            ]
        )
        svg = inst.emit_svg()
        assert "<polygon" in svg, "arrow_from must emit arrowhead polygon"
        assert "<path" in svg, "arrow_from must emit Bezier <path>"

    def test_both_annotations_distinct_visuals(self) -> None:
        """arrow=true and arrow_from coexist and produce distinct SVG."""
        inst = self._make_array(
            [
                {"target": "a.cell[0]", "label": "X", "arrow": True},
                {
                    "target": "a.cell[2]",
                    "label": "Y",
                    "arrow_from": "a.cell[0]",
                },
            ]
        )
        svg = inst.emit_svg()
        # Should have TWO annotation groups
        assert svg.count('class="scriba-annotation') == 2
        # arrow=true contributes a <line>; arrow_from contributes a <path>
        assert "<line" in svg
        assert "<path" in svg
        # Both have arrowhead polygons
        assert svg.count("<polygon") == 2

    def test_arrow_true_no_effect_without_flag(self) -> None:
        """Annotations without arrow=true or arrow_from emit no arrowhead."""
        inst = self._make_array(
            [{"target": "a.cell[0]", "label": "X"}]
        )
        svg = inst.emit_svg()
        assert "<polygon" not in svg
        assert "<line" not in svg

    def test_bounding_box_includes_stem_height(self) -> None:
        """arrow=true must reserve vertical space above the cells."""
        inst_plain = ArrayPrimitive("a", {"size": 3})
        inst_with_arrow = ArrayPrimitive("a", {"size": 3})
        inst_with_arrow.set_annotations(
            [{"target": "a.cell[1]", "label": "X", "arrow": True}]
        )
        _, _, _, h_plain = inst_plain.bounding_box()
        _, _, _, h_arrow = inst_with_arrow.bounding_box()
        assert h_arrow > h_plain, (
            "arrow=true must increase the bounding box height to accommodate "
            "the stem above the cells"
        )


# ---------------------------------------------------------------------------
# 3. emit_plain_arrow_svg unit test (base helper)
# ---------------------------------------------------------------------------


class TestEmitPlainArrowSvg:
    """Direct unit test of the shared emit_plain_arrow_svg helper."""

    def test_emits_line_polygon_and_annotation_group(self) -> None:
        lines: list[str] = []
        emit_plain_arrow_svg(
            lines,
            ann={"target": "a.cell[0]", "label": "hi", "color": "info"},
            dst_point=(30.0, 0.0),
        )
        svg = "\n".join(lines)
        assert 'class="scriba-annotation' in svg
        assert "<line" in svg
        assert "<polygon" in svg

    def test_emits_label_text_when_provided(self) -> None:
        lines: list[str] = []
        emit_plain_arrow_svg(
            lines,
            ann={"target": "a.cell[0]", "label": "myLabel", "color": "info"},
            dst_point=(30.0, 0.0),
        )
        svg = "\n".join(lines)
        assert "myLabel" in svg

    def test_no_label_skips_text_element(self) -> None:
        lines: list[str] = []
        emit_plain_arrow_svg(
            lines,
            ann={"target": "a.cell[0]", "color": "info"},
            dst_point=(30.0, 0.0),
        )
        svg = "\n".join(lines)
        assert "<text" not in svg

    def test_arrowhead_points_downward(self) -> None:
        """The arrowhead tip must equal the dst_point (pointing down)."""
        lines: list[str] = []
        emit_plain_arrow_svg(
            lines,
            ann={"target": "a.cell[0]", "color": "info"},
            dst_point=(50.0, 10.0),
        )
        svg = "\n".join(lines)
        # The polygon tip is at dst_point (rounded to int): "50,10"
        # It appears as the first pair in the points= attribute.
        assert "50.0,10.0" in svg, (
            "The arrowhead tip must be at the dst_point coordinates"
        )

    def test_uses_color_style(self) -> None:
        lines: list[str] = []
        emit_plain_arrow_svg(
            lines,
            ann={"target": "a.cell[0]", "color": "error"},
            dst_point=(30.0, 0.0),
        )
        svg = "\n".join(lines)
        # ARROW_STYLES["error"]["stroke"] == "#c6282d" (darkened from #dc2626
        # for WCAG AA: 5.61:1 on white pill, was 4.83:1 which failed AA)
        assert "#c6282d" in svg
