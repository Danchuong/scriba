"""Tests for the CodePanel primitive.

Covers declaration, selectors, addressable parts, state management,
SVG output, and edge cases (1-based indexing).
"""

from __future__ import annotations

import re

from scriba.animation.primitives.codepanel import CodePanel


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_default_construction_with_source(self) -> None:
        inst = CodePanel("code", {"source": "x = 1\ny = 2"})
        assert inst.name == "code"
        assert inst.lines == ["x = 1", "y = 2"]
        assert inst.primitive_type == "codepanel"

    def test_construction_with_lines_list(self) -> None:
        inst = CodePanel("code", {"lines": ["def foo():", "    pass"]})
        assert inst.lines == ["def foo():", "    pass"]

    def test_construction_with_lines_single_string(self) -> None:
        inst = CodePanel("code", {"lines": "single line"})
        assert inst.lines == ["single line"]

    def test_empty_construction(self) -> None:
        inst = CodePanel("code", {})
        assert inst.lines == []

    def test_label_parameter(self) -> None:
        inst = CodePanel("code", {"source": "x = 1", "label": "Algorithm"})
        assert inst.label == "Algorithm"

    def test_source_strips_leading_trailing_newlines(self) -> None:
        inst = CodePanel("code", {"source": "\nline1\nline2\n"})
        assert inst.lines == ["line1", "line2"]


# ---------------------------------------------------------------------------
# Addressable parts
# ---------------------------------------------------------------------------


class TestAddressableParts:
    def test_returns_1_based_lines_and_all(self) -> None:
        inst = CodePanel("code", {"lines": ["a", "b", "c"]})
        parts = inst.addressable_parts()
        assert parts == ["line[1]", "line[2]", "line[3]", "all"]

    def test_empty_source_only_all(self) -> None:
        inst = CodePanel("code", {})
        assert inst.addressable_parts() == ["all"]

    def test_single_line(self) -> None:
        inst = CodePanel("code", {"lines": ["only"]})
        assert inst.addressable_parts() == ["line[1]", "all"]


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_line_1_based_valid(self) -> None:
        inst = CodePanel("code", {"lines": ["a", "b", "c"]})
        assert inst.validate_selector("line[1]") is True
        assert inst.validate_selector("line[3]") is True

    def test_line_0_is_invalid(self) -> None:
        """CodePanel uses 1-based indexing; line[0] must be invalid."""
        inst = CodePanel("code", {"lines": ["a", "b"]})
        assert inst.validate_selector("line[0]") is False

    def test_line_1_is_first_line_not_second(self) -> None:
        """line[1] addresses the first source line (not the second)."""
        inst = CodePanel("code", {"lines": ["first", "second", "third"]})
        # 1-based boundaries: line[1], line[2], line[3] all valid.
        assert inst.validate_selector("line[1]") is True
        assert inst.validate_selector("line[2]") is True
        assert inst.validate_selector("line[3]") is True
        # line[0] and line[4] both rejected.
        assert inst.validate_selector("line[0]") is False
        assert inst.validate_selector("line[4]") is False

    def test_line_out_of_range(self) -> None:
        inst = CodePanel("code", {"lines": ["a", "b"]})
        assert inst.validate_selector("line[3]") is False

    def test_all_valid(self) -> None:
        inst = CodePanel("code", {"lines": ["a"]})
        assert inst.validate_selector("all") is True

    def test_unknown_selector(self) -> None:
        inst = CodePanel("code", {"lines": ["a"]})
        assert inst.validate_selector("cell[0]") is False
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class TestState:
    def test_set_state_on_line(self) -> None:
        inst = CodePanel("code", {"lines": ["a", "b"]})
        inst.set_state("line[1]", "current")
        assert inst.get_state("line[1]") == "current"
        assert inst.get_state("line[2]") == "idle"

    def test_set_state_all(self) -> None:
        inst = CodePanel("code", {"lines": ["a", "b"]})
        inst.set_state("all", "done")
        assert inst.get_state("all") == "done"


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        inst = CodePanel("code", {"lines": ["x = 1", "y = 2"]})
        svg = inst.emit_svg()
        assert 'data-primitive="codepanel"' in svg
        assert 'data-shape="code"' in svg
        assert 'data-target="code.line[1]"' in svg
        assert 'data-target="code.line[2]"' in svg

    def test_default_idle_class(self) -> None:
        inst = CodePanel("code", {"lines": ["hello"]})
        svg = inst.emit_svg()
        assert "scriba-state-idle" in svg

    def test_state_applied_in_svg(self) -> None:
        inst = CodePanel("code", {"lines": ["a", "b"]})
        inst.set_state("line[1]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_label_rendered(self) -> None:
        inst = CodePanel("code", {"source": "x = 1", "label": "My Code"})
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg
        assert "My Code" in svg

    def test_empty_source_renders_placeholder(self) -> None:
        inst = CodePanel("code", {})
        svg = inst.emit_svg()
        assert "no code" in svg

    def test_code_text_appears_in_svg(self) -> None:
        inst = CodePanel("code", {"lines": ["print('hi')"]})
        svg = inst.emit_svg()
        assert "print(" in svg

    def test_line_numbers_rendered(self) -> None:
        inst = CodePanel("code", {"lines": ["a", "b", "c"]})
        svg = inst.emit_svg()
        assert ">1</text>" in svg
        assert ">2</text>" in svg
        assert ">3</text>" in svg


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_1_based_indexing_first_line_is_line1(self) -> None:
        """line[1] is the first line, NOT line[0]."""
        inst = CodePanel("code", {"lines": ["first", "second"]})
        parts = inst.addressable_parts()
        assert "line[1]" in parts
        assert "line[0]" not in parts

    def test_bounding_box_positive(self) -> None:
        inst = CodePanel("code", {"lines": ["a", "b"]})
        bbox = inst.bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0

    def test_bounding_box_empty(self) -> None:
        inst = CodePanel("code", {})
        bbox = inst.bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0

    def test_all_state_propagates_to_lines(self) -> None:
        """When 'all' state is set, lines without specific state inherit it."""
        inst = CodePanel("code", {"lines": ["a", "b"]})
        inst.set_state("all", "done")
        svg = inst.emit_svg()
        # Both lines should reflect done state (not idle)
        assert svg.count("scriba-state-done") >= 2


# ---------------------------------------------------------------------------
# Annotations — line anchors + position pills (Layer B/C)
#
# Regression: CodePanel had no annotation resolver, so a line annotation was
# silently dropped (accepted by validate_selector, stored, never rendered).
# Lines are 1-based; the anchor is the line's vertical center.
# ---------------------------------------------------------------------------


class TestAnnotations:
    def test_line_anchor_resolves(self) -> None:
        c = CodePanel("c", {"source": "a = 1\nb = 2\nc = 3"})
        assert c.resolve_annotation_point("c.line[1]") is not None
        assert c.resolve_annotation_point("c.line[3]") is not None

    def test_line_anchor_centers_descend(self) -> None:
        """Later lines anchor lower than earlier ones."""
        c = CodePanel("c", {"source": "a = 1\nb = 2\nc = 3"})
        y1 = c.resolve_annotation_point("c.line[1]")[1]
        y3 = c.resolve_annotation_point("c.line[3]")[1]
        assert y3 > y1

    def test_invalid_line_no_anchor(self) -> None:
        c = CodePanel("c", {"source": "a = 1\nb = 2"})
        assert c.resolve_annotation_point("c.line[0]") is None  # 1-based
        assert c.resolve_annotation_point("c.line[5]") is None

    def test_position_pill_renders(self) -> None:
        c = CodePanel("c", {"source": "a = 1\nb = 2\nc = 3"})
        c.set_annotations(
            [{"target": "c.line[2]", "label": "O(n)", "position": "above"}]
        )
        svg = c.emit_svg()
        assert "O(n)" in svg  # was silently dropped
        assert "scriba-annotation" in svg

    def test_unannotated_bbox_unchanged(self) -> None:
        c = CodePanel("c", {"source": "a = 1\nb = 2"})
        assert c.bounding_box().height == float(c._panel_height())


# ---------------------------------------------------------------------------
# Annotation layout — #1 horizontal pill reservation + #2 below-pill lane
#
# A position=right pill must fit inside bounding_box().width (it was clipped
# when the box reserved only vertical space). A position=below pill is placed
# in a callout lane BELOW the panel (panel bottom = _panel_height). CodePanel
# gets lane mode but NO leader line (no resolve_annotation_box per spec). With
# no left/right or below pills the box stays byte-stable.
# ---------------------------------------------------------------------------


def _pill_rects(svg: str) -> list[tuple[float, float, float, float]]:
    """(x, y, width, height) of every annotation pill ``<rect>`` in *svg*."""
    out: list[tuple[float, float, float, float]] = []
    for block in re.findall(r'<g class="scriba-annotation[^"]*".*?</g>', svg, re.S):
        for m in re.finditer(
            r'<rect x="([\-\d.]+)" y="([\-\d.]+)" '
            r'width="([\-\d.]+)" height="([\-\d.]+)"',
            block,
        ):
            out.append(
                (
                    float(m.group(1)),
                    float(m.group(2)),
                    float(m.group(3)),
                    float(m.group(4)),
                )
            )
    return out


class TestAnnotationLayout:
    def test_right_pill_fits_bbox(self) -> None:
        c = CodePanel("c", {"source": "a = 1\nb = 2\nc = 3"})
        c.set_annotations(
            [{"target": "c.line[2]", "label": "a fairly long side note",
              "position": "right"}]
        )
        rects = _pill_rects(c.emit_svg())
        assert rects, "right pill not rendered"
        bbox_w = float(c.bounding_box().width)
        for x, _y, w, _h in rects:
            assert x >= -1.0
            assert x + w <= bbox_w + 1.0

    def test_below_pill_in_lane(self) -> None:
        c = CodePanel("c", {"source": "a = 1\nb = 2\nc = 3"})
        c.set_annotations(
            [{"target": "c.line[2]", "label": "note", "position": "below"}]
        )
        rects = _pill_rects(c.emit_svg())
        assert rects, "below pill not rendered"
        content_bottom = c.resolve_below_baseline()
        bbox_h = float(c.bounding_box().height)
        for _x, y, _w, h in rects:
            assert y >= content_bottom  # below the panel
            assert y + h <= bbox_h + 1.0  # lane fits inside the bbox

    def test_below_pill_has_no_leader_line(self) -> None:
        """Spec: CodePanel gets lane mode but NO leader (no resolve_annotation_box)."""
        c = CodePanel("c", {"source": "a = 1\nb = 2\nc = 3"})
        c.set_annotations(
            [{"target": "c.line[2]", "label": "note", "position": "below"}]
        )
        blocks = re.findall(
            r'<g class="scriba-annotation[^"]*".*?</g>', c.emit_svg(), re.S
        )
        assert blocks, "below pill not rendered"
        assert all("<line" not in b for b in blocks)

    def test_unannotated_bbox_width_unchanged(self) -> None:
        c = CodePanel("c", {"source": "a = 1\nb = 2"})
        bbox = c.bounding_box()
        assert bbox.width == c._panel_width()
        assert bbox.height == float(c._panel_height())
