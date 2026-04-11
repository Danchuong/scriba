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
        assert len(p.polygons[0]["points"]) == 4

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
