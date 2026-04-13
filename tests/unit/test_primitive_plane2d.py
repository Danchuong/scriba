"""Unit tests for scriba.animation.primitives.plane2d."""

from __future__ import annotations

import pytest

from scriba.animation.primitives.plane2d import Plane2D
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------


class TestPlane2DConstructor:
    def test_default_params(self) -> None:
        p = Plane2D("p", {})
        assert p.xrange == (-5.0, 5.0)
        assert p.yrange == (-5.0, 5.0)
        assert p.grid is True
        assert p.axes is True
        assert p.aspect == "equal"
        assert p.width == 320

    def test_explicit_ranges(self) -> None:
        p = Plane2D("p", {"xrange": [0, 10], "yrange": [-2, 2]})
        assert p.xrange == (0, 10)
        assert p.yrange == (-2, 2)

    def test_degenerate_xrange_raises_e1460(self) -> None:
        with pytest.raises(ValidationError, match="E1460"):
            Plane2D("p", {"xrange": [5, 5]})

    def test_degenerate_yrange_raises_e1460(self) -> None:
        with pytest.raises(ValidationError, match="E1460"):
            Plane2D("p", {"yrange": [0, 0]})

    def test_invalid_aspect_raises_e1465(self) -> None:
        with pytest.raises(ValidationError, match="E1465"):
            Plane2D("p", {"aspect": "stretch"})

    def test_aspect_equal_computes_height(self) -> None:
        p = Plane2D("p", {
            "xrange": [-2, 2],
            "yrange": [-1, 1],
            "width": 200,
            "aspect": "equal",
        })
        # width=200, xspan=4, yspan=2 → height = 200 * 2/4 = 100
        assert p.height == 100

    def test_aspect_auto_uses_explicit_height(self) -> None:
        p = Plane2D("p", {
            "xrange": [-5, 5],
            "yrange": [-5, 5],
            "width": 400,
            "height": 200,
            "aspect": "auto",
        })
        assert p.height == 200
        assert p.width == 400


# ---------------------------------------------------------------
# Math→SVG transform tests
# ---------------------------------------------------------------


class TestMathToSvgTransform:
    def test_worked_example_center(self) -> None:
        """Verify the worked example from the spec: xrange=[-2,2], yrange=[-2,2], 200x200."""
        p = Plane2D("p", {
            "xrange": [-2, 2],
            "yrange": [-2, 2],
            "width": 200,
            "aspect": "equal",
        })
        # Math (0,0) should map to center (100, 100)
        sx, sy = p.math_to_svg(0, 0)
        assert abs(sx - 100) < 1
        assert abs(sy - 100) < 1

    def test_worked_example_corner(self) -> None:
        p = Plane2D("p", {
            "xrange": [-2, 2],
            "yrange": [-2, 2],
            "width": 200,
            "aspect": "equal",
        })
        # Math (2,2) → SVG (168, 32) approximately
        sx, sy = p.math_to_svg(2, 2)
        assert abs(sx - 168) < 1
        assert abs(sy - 32) < 1

    def test_origin_at_bottom_left(self) -> None:
        p = Plane2D("p", {
            "xrange": [0, 10],
            "yrange": [0, 10],
            "width": 320,
            "aspect": "equal",
        })
        # Math (0,0) should map to bottom-left (pad, height-pad)
        sx, sy = p.math_to_svg(0, 0)
        assert abs(sx - 32) < 1
        assert abs(sy - (p.height - 32)) < 1


# ---------------------------------------------------------------
# Add element tests
# ---------------------------------------------------------------


class TestAddElements:
    def test_add_point(self) -> None:
        p = Plane2D("p", {})
        p.apply_command({"add_point": (1, 2)})
        assert len(p.points) == 1
        assert p.points[0]["x"] == 1.0
        assert p.points[0]["y"] == 2.0

    def test_add_line(self) -> None:
        p = Plane2D("p", {})
        p.apply_command({"add_line": ("L1", 2, 3)})
        assert len(p.lines) == 1
        assert p.lines[0]["slope"] == 2.0
        assert p.lines[0]["intercept"] == 3.0

    def test_add_segment(self) -> None:
        p = Plane2D("p", {})
        p.apply_command({"add_segment": ((0, 0), (3, 4))})
        assert len(p.segments) == 1
        assert p.segments[0]["x1"] == 0.0
        assert p.segments[0]["y2"] == 4.0

    def test_add_polygon(self) -> None:
        p = Plane2D("p", {})
        p.apply_command({"add_polygon": [(0, 0), (3, 0), (3, 3), (0, 3)]})
        assert len(p.polygons) == 1
        # RFC-002 / SF-1: auto-close now explicitly appends the first
        # point so the internal list matches the rendered SVG path. A
        # 4-vertex polygon becomes a 5-element list (closing copy).
        assert len(p.polygons[0]["points"]) == 5
        assert p.polygons[0]["points"][0] == p.polygons[0]["points"][-1]

    def test_add_region(self) -> None:
        p = Plane2D("p", {})
        p.apply_command({"add_region": {"polygon": [(0, 0), (5, 0), (5, 5)], "fill": "rgba(0,0,255,0.3)"}})
        assert len(p.regions) == 1
        assert p.regions[0]["fill"] == "rgba(0,0,255,0.3)"


# ---------------------------------------------------------------
# Element cap tests (hard-limit E1466)
# ---------------------------------------------------------------


class TestElementCap:
    def test_e1466_raises_on_incremental_apply(self) -> None:
        """501st ``add_point`` via apply_command must raise E1466."""
        p = Plane2D("p", {})
        for _ in range(500):
            p.apply_command({"add_point": (0, 0)})
        assert len(p.points) == 500
        with pytest.raises(ValidationError) as excinfo:
            p.apply_command({"add_point": (1, 1)})
        assert "E1466" in str(excinfo.value)
        assert "501" in str(excinfo.value)
        assert "500" in str(excinfo.value)
        # State is unchanged (hard limit: no silent growth).
        assert len(p.points) == 500

    # NOTE: Pre-Wave-4A HEAD had two tests asserting SOFT-DROP behavior
    # (logger.error + silent keep-first-500). Wave 4A Cluster 4 converted
    # Plane2D cap enforcement from soft-drop to hard-raise per audit
    # finding 06-H3. The old tests have been replaced with the new
    # hard-raise assertions below.

    def test_e1466_raises_at_construction(self) -> None:
        """Supplying 501 points via ``\\shape`` params must raise E1466."""
        too_many = [(0.0, 0.0)] * 501
        with pytest.raises(ValidationError) as excinfo:
            Plane2D("p", {"points": too_many})
        assert "E1466" in str(excinfo.value)

    def test_e1466_cap_is_per_frame_across_element_types(self) -> None:
        """Cap is shared across points/lines/segments/polygons/regions."""
        p = Plane2D("p", {})
        # 499 points + 1 segment = 500 total — still OK.
        for _ in range(499):
            p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_segment": ((0.0, 0.0), (1.0, 1.0))})
        assert len(p.points) + len(p.segments) == 500
        # One more of ANY kind should raise.
        with pytest.raises(ValidationError) as excinfo:
            p.apply_command({"add_line": ("L", 1.0, 0.0)})
        assert "E1466" in str(excinfo.value)

    def test_e1466_message_format(self) -> None:
        """Error message should identify offender and valid range."""
        p = Plane2D("p", {})
        for _ in range(500):
            p.apply_command({"add_point": (0, 0)})
        with pytest.raises(ValidationError) as excinfo:
            p.apply_command({"add_point": (1, 1)})
        msg = str(excinfo.value)
        # Concrete offender (501) + valid range (500) + guidance.
        assert "Plane2D element count 501" in msg
        assert "maximum 500" in msg
        assert "per frame" in msg


# ---------------------------------------------------------------
# Addressable parts / selectors
# ---------------------------------------------------------------


class TestAddressableParts:
    def test_returns_correct_selectors(self) -> None:
        p = Plane2D("p", {
            "points": [(0, 0), (1, 1)],
            "lines": [("L", 1, 0)],
            "segments": [((0, 0), (1, 1))],
        })
        parts = p.addressable_parts()
        assert "point[0]" in parts
        assert "point[1]" in parts
        assert "line[0]" in parts
        assert "segment[0]" in parts
        assert "all" in parts

    def test_validate_selector_valid(self) -> None:
        p = Plane2D("p", {"points": [(0, 0)]})
        assert p.validate_selector("point[0]") is True
        assert p.validate_selector("all") is True

    def test_validate_selector_invalid_index(self) -> None:
        p = Plane2D("p", {"points": [(0, 0)]})
        assert p.validate_selector("point[5]") is False

    def test_validate_selector_unknown(self) -> None:
        p = Plane2D("p", {})
        assert p.validate_selector("foo[0]") is False


# ---------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------


class TestBoundingBox:
    def test_matches_width_height(self) -> None:
        p = Plane2D("p", {"width": 400, "aspect": "auto", "height": 300})
        bb = p.bounding_box()
        assert bb.width == 400
        assert bb.height == 300


# ---------------------------------------------------------------
# SVG emission
# ---------------------------------------------------------------


class TestEmitSvg:
    def test_produces_three_layer_structure(self) -> None:
        p = Plane2D("p", {"points": [(0, 0)]})
        svg = p.emit_svg()
        assert 'class="scriba-plane-grid"' in svg
        assert 'class="scriba-plane-axes"' in svg
        assert 'class="scriba-plane-content"' in svg
        assert 'class="scriba-plane-labels"' in svg

    def test_grid_lines_at_integer_positions(self) -> None:
        p = Plane2D("p", {"xrange": [-2, 2], "yrange": [-2, 2]})
        svg = p.emit_svg()
        # Should have grid lines (check for grid group content)
        assert "scriba-plane-grid" in svg
        assert "<line" in svg

    def test_axes_through_origin(self) -> None:
        p = Plane2D("p", {"xrange": [-5, 5], "yrange": [-5, 5]})
        svg = p.emit_svg()
        assert "scriba-plane-axes" in svg
        # Arrowheads present
        assert "<path" in svg

    def test_no_grid_when_disabled(self) -> None:
        p = Plane2D("p", {"grid": False})
        svg = p.emit_svg()
        # The grid group should be empty
        assert 'class="scriba-plane-grid"' not in svg

    def test_no_axes_when_disabled(self) -> None:
        p = Plane2D("p", {"axes": False})
        svg = p.emit_svg()
        assert 'class="scriba-plane-axes"' not in svg

    def test_point_rendered_as_circle(self) -> None:
        p = Plane2D("p", {"points": [(1, 2)]})
        svg = p.emit_svg()
        assert "scriba-plane-point" in svg
        assert "<circle" in svg

    def test_polygon_auto_close_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Non-closed polygon emits E1462 warning."""
        import logging
        with caplog.at_level(logging.WARNING):
            p = Plane2D("p", {"polygons": [[(0, 0), (1, 0), (1, 1)]]})
        assert any("E1462" in r.message for r in caplog.records)

    def test_point_outside_viewport_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Point outside viewport emits E1463 warning."""
        import logging
        with caplog.at_level(logging.WARNING):
            p = Plane2D("p", {"xrange": [0, 5], "yrange": [0, 5], "points": [(-10, -10)]})
        assert any("E1463" in r.message for r in caplog.records)

    def test_wrapper_has_data_attributes(self) -> None:
        p = Plane2D("p", {"width": 400, "aspect": "auto", "height": 300})
        svg = p.emit_svg()
        assert 'data-primitive="plane2d"' in svg
        assert 'data-shape="p"' in svg

    def test_line_clipping_to_viewport(self) -> None:
        p = Plane2D("p", {"xrange": [-5, 5], "yrange": [-5, 5], "lines": [("L", 1, 0)]})
        svg = p.emit_svg()
        assert "scriba-plane-line" in svg

    def test_data_attributes(self) -> None:
        p = Plane2D("p", {"xrange": [-3, 3], "yrange": [-3, 3]})
        svg = p.emit_svg()
        assert 'data-scriba-xrange="-3 3"' in svg
        assert 'data-scriba-yrange="-3 3"' in svg


# ---------------------------------------------------------------
# Line label collision avoidance and clamping tests
# ---------------------------------------------------------------


class TestLineLabelCollision:
    def test_line_labels_no_overlap(self) -> None:
        """Two lines with labels near the same endpoint have distinct y positions."""
        import re as _re

        p = Plane2D("p", {
            "xrange": [-5, 5],
            "yrange": [-5, 5],
            "lines": [("y=-x", -1, 0), ("y=-0.5x-2", -0.5, -2)],
        })
        svg = p.emit_svg()
        # Both labels should be rendered
        assert "y=-x" in svg
        assert "y=-0.5x-2" in svg
        # Extract y positions of the background pills (rect elements in label section)
        pills = _re.findall(r'<rect x="[^"]*" y="([^"]*)"', svg)
        # Should have at least 2 pills for the two line labels
        assert len(pills) >= 2
        y_positions = [float(y) for y in pills[-2:]]
        assert abs(y_positions[0] - y_positions[1]) >= 12

    def test_line_label_clamped(self) -> None:
        """Line label near the right edge stays within viewBox bounds."""
        import re as _re

        p = Plane2D("p", {
            "xrange": [-5, 5],
            "yrange": [-5, 5],
            "width": 320,
            "lines": [("RightEdge", 1, 0)],
        })
        svg = p.emit_svg()
        assert "RightEdge" in svg
        # The text-anchor="middle" text x should be within viewBox width
        # Find text elements with "RightEdge"
        text_matches = _re.findall(
            r'<text[^>]*x="(\d+)"[^>]*>.*?RightEdge', svg,
        )
        if not text_matches:
            # Try alternate attribute order
            text_matches = _re.findall(
                r'<text[^>]*>.*?RightEdge', svg,
            )
        # The label should be present and not exceed viewBox
        assert "RightEdge" in svg
        # Verify pill rect x + width stays within viewBox
        pill_matches = _re.findall(
            r'<rect x="([^"]*)" y="[^"]*" width="([^"]*)"', svg,
        )
        for rx, rw in pill_matches:
            right_edge = float(rx) + float(rw)
            assert right_edge <= p.width + 1  # 1px tolerance


# ---------------------------------------------------------------
# Point coordinate label tests
# ---------------------------------------------------------------


class TestPointShowCoords:
    def test_point_show_coords_default_off(self) -> None:
        """Without show_coords, points have no coordinate text."""
        p = Plane2D("p", {"points": [(3, 4)]})
        svg = p.emit_svg()
        assert "(3, 4)" not in svg

    def test_point_show_coords_on(self) -> None:
        """With show_coords=True, point at (3,4) gets coordinate label."""
        p = Plane2D("p", {"points": [(3, 4)], "show_coords": True})
        svg = p.emit_svg()
        assert "(3, 4)" in svg

    def test_point_explicit_label_overrides_coords(self) -> None:
        """Explicit label takes priority over show_coords."""
        p = Plane2D("p", {
            "points": [{"x": 3, "y": 4, "label": "P"}],
            "show_coords": True,
        })
        svg = p.emit_svg()
        assert "P" in svg
        # Should NOT also show coordinates
        assert "(3, 4)" not in svg


# ---------------------------------------------------------------
# Text-only annotation tests
# ---------------------------------------------------------------


class TestTextAnnotation:
    def test_text_annotation_produces_svg(self) -> None:
        """Annotating a point with label only (no arrow_from) emits text."""
        p = Plane2D("p", {"points": [(1, 2)]})
        p.set_annotations([
            {"target": "p.point[0]", "label": "A", "position": "above", "color": "good"},
        ])
        svg = p.emit_svg()
        assert "<text" in svg
        assert "A" in svg

    def test_text_annotation_all_positions(self) -> None:
        """Each position (above/below/left/right) produces text at different y offsets."""
        positions = ["above", "below", "left", "right"]
        results: dict[str, str] = {}
        for pos in positions:
            p = Plane2D("p", {"points": [(0, 0)]})
            p.set_annotations([
                {"target": "p.point[0]", "label": "X", "position": pos, "color": "info"},
            ])
            results[pos] = p.emit_svg()
            assert "<text" in results[pos], f"position={pos} should produce <text>"

        # above and below should differ in their y coordinate
        assert results["above"] != results["below"]
        # left and right should differ in text-anchor
        assert "text-anchor:end" in results["left"]
        assert "text-anchor:start" in results["right"]

    def test_text_annotation_missing_target(self) -> None:
        """Annotating a nonexistent point produces no crash and no text output."""
        p = Plane2D("p", {"points": [(1, 2)]})
        p.set_annotations([
            {"target": "p.point[99]", "label": "MISSING", "position": "above", "color": "good"},
        ])
        svg = p.emit_svg()
        # Should not crash; label text should not appear
        assert "MISSING" not in svg

    def test_text_annotation_no_label(self) -> None:
        """Annotation with empty label produces no text output."""
        p = Plane2D("p", {"points": [(1, 2)]})
        p.set_annotations([
            {"target": "p.point[0]", "label": "", "position": "above", "color": "info"},
        ])
        svg = p.emit_svg()
        # The pill background should not appear either
        assert svg.count("opacity=\"0.85\"") == 0

    def test_text_annotation_has_background_pill(self) -> None:
        """Text annotation renders a white background pill for readability."""
        p = Plane2D("p", {"points": [(1, 2)]})
        p.set_annotations([
            {"target": "p.point[0]", "label": "B", "position": "above", "color": "good"},
        ])
        svg = p.emit_svg()
        assert 'fill="white"' in svg
        assert 'opacity="0.85"' in svg


# ---------------------------------------------------------------
# _nice_ticks tests
# ---------------------------------------------------------------


class TestNiceTicks:
    def test_nice_ticks_fractional(self) -> None:
        """Range [0, 1] should produce ~5-10 tick values between 0 and 1."""
        ticks = Plane2D._nice_ticks(0, 1)
        assert 3 <= len(ticks) <= 12
        assert all(0 <= t <= 1.01 for t in ticks)

    def test_nice_ticks_large(self) -> None:
        """Range [-100, 100] should produce ~5-10 tick values."""
        ticks = Plane2D._nice_ticks(-100, 100)
        assert 3 <= len(ticks) <= 12
        assert all(-100.1 <= t <= 100.1 for t in ticks)

    def test_nice_ticks_standard(self) -> None:
        """Range [-5, 5] should produce integer ticks."""
        ticks = Plane2D._nice_ticks(-5, 5)
        assert len(ticks) >= 3
        for t in ticks:
            assert t == int(t), f"Expected integer tick, got {t}"

    def test_nice_ticks_zero_span(self) -> None:
        """Edge case: vmin == vmax should return [vmin]."""
        ticks = Plane2D._nice_ticks(3.0, 3.0)
        assert ticks == [3.0]


# ---------------------------------------------------------------
# Adaptive tick label tests
# ---------------------------------------------------------------


class TestAdaptiveTickLabels:
    def test_tick_labels_fractional_range(self) -> None:
        """Plane2D with xrange=[0,1] should render tick <text> elements."""
        p = Plane2D("p", {"xrange": [0, 1], "yrange": [0, 1], "width": 320, "aspect": "auto", "height": 320})
        svg = p.emit_svg()
        assert "<text" in svg, "Expected tick labels in fractional range SVG"

    def test_tick_labels_large_range(self) -> None:
        """Plane2D with xrange=[-100,100] should render tick labels, not blank."""
        p = Plane2D("p", {"xrange": [-100, 100], "yrange": [-100, 100], "width": 600, "aspect": "auto", "height": 600})
        svg = p.emit_svg()
        # Should have at least some tick <text> elements
        assert svg.count("<text") >= 2, "Expected tick labels for large range"

    def test_origin_at_boundary(self) -> None:
        """When xrange starts at 0, the '0' tick should be rendered."""
        p = Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10], "width": 320, "aspect": "equal"})
        svg = p.emit_svg()
        # Find tick text elements containing "0"
        # The origin "0" should appear as a tick label since xmin == 0
        import re
        tick_texts = re.findall(r'<text[^>]*>([^<]+)</text>', svg)
        assert "0" in tick_texts, f"Expected '0' tick label when range starts at 0, got: {tick_texts}"

    def test_origin_interior_suppressed(self) -> None:
        """When 0 is strictly interior to xrange, '0' should NOT appear on x-axis ticks."""
        p = Plane2D("p", {"xrange": [-5, 5], "yrange": [-5, 5], "width": 320, "aspect": "equal"})
        svg = p.emit_svg()
        import re
        # Extract x-axis tick labels (those near the x-axis y position)
        # We check that "0" does not appear as a standalone tick label
        # by looking at text elements anchored "middle" (x-axis style)
        x_tick_texts = re.findall(r'<text[^>]*text-anchor="middle"[^>]*>([^<]+)</text>', svg)
        assert "0" not in x_tick_texts, f"Origin '0' should be suppressed on x-axis when interior, got: {x_tick_texts}"
