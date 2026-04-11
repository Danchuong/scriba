"""Tests for the Matrix / Heatmap primitive.

Covers declaration, colorscale, selectors, SVG output, value display,
vmin/vmax, bounding box, and the Heatmap alias.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.matrix import (
    MatrixInstance,
    MatrixPrimitive,
    HeatmapPrimitive,
    interpolate_color,
    VIRIDIS,
)
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_basic_declaration(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 3, "cols": 4,
            "data": [float(i) for i in range(12)],
        })
        assert isinstance(inst, MatrixInstance)
        assert inst.rows == 3
        assert inst.cols == 4
        assert inst.shape_name == "m"
        assert inst.primitive_type == "matrix"

    def test_2d_data(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 2, "cols": 2,
            "data": [[0.1, 0.2], [0.3, 0.4]],
        })
        assert inst.data == [[0.1, 0.2], [0.3, 0.4]]

    def test_flat_data_reshaping(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 2, "cols": 3,
            "data": [1, 2, 3, 4, 5, 6],
        })
        assert inst.data == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]

    def test_missing_rows_raises(self) -> None:
        # v0.5.1: E1420 (Matrix missing rows/cols)
        with pytest.raises(ValidationError, match="E1420"):
            MatrixPrimitive("m", {"cols": 3, "data": [1, 2, 3]})

    def test_missing_cols_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1420"):
            MatrixPrimitive("m", {"rows": 3, "data": [1, 2, 3]})

    def test_data_length_mismatch(self) -> None:
        # v0.5.1: E1422 (Matrix data length mismatch)
        with pytest.raises(ValidationError, match="E1422"):
            MatrixPrimitive("m", {"rows": 2, "cols": 2, "data": [1, 2, 3]})

    def test_zero_rows_raises_e1421(self) -> None:
        with pytest.raises(ValidationError, match="E1421"):
            MatrixPrimitive("m", {"rows": 0, "cols": 4})

    def test_zero_cols_raises_e1421(self) -> None:
        with pytest.raises(ValidationError, match="E1421"):
            MatrixPrimitive("m", {"rows": 4, "cols": 0})

    def test_cell_count_limit_raises_e1425(self) -> None:
        """A 251x1000 matrix (251,000 cells) exceeds the 250,000 limit."""
        with pytest.raises(ValidationError, match="E1425") as exc_info:
            MatrixPrimitive("m", {"rows": 251, "cols": 1000})
        # Error message must name the actual count and the 250000 limit.
        msg = str(exc_info.value)
        assert "251000" in msg
        assert "250000" in msg

    def test_cell_count_at_limit_ok(self) -> None:
        """Exactly 250,000 cells is still permitted."""
        inst = MatrixPrimitive("m", {"rows": 500, "cols": 500})
        assert inst.rows == 500 and inst.cols == 500

    def test_empty_data_fills_zeros(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 2, "cols": 2})
        assert inst.data == [[0.0, 0.0], [0.0, 0.0]]

    def test_default_colorscale(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 1, "cols": 1})
        assert inst.colorscale == "viridis"

    def test_show_values_default_false(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 1, "cols": 1})
        assert inst.show_values is False


# ---------------------------------------------------------------------------
# Colorscale interpolation
# ---------------------------------------------------------------------------


class TestColorscale:
    def test_t_zero_gives_first_stop(self) -> None:
        color = interpolate_color(0.0, VIRIDIS)
        assert color == "rgb(68,1,84)"

    def test_t_one_gives_last_stop(self) -> None:
        color = interpolate_color(1.0, VIRIDIS)
        assert color == "rgb(253,231,37)"

    def test_t_half_gives_teal(self) -> None:
        color = interpolate_color(0.5, VIRIDIS)
        assert color == "rgb(33,145,140)"

    def test_clamp_below_zero(self) -> None:
        color = interpolate_color(-0.5, VIRIDIS)
        assert color == "rgb(68,1,84)"

    def test_clamp_above_one(self) -> None:
        color = interpolate_color(1.5, VIRIDIS)
        assert color == "rgb(253,231,37)"

    def test_midpoint_interpolation(self) -> None:
        # t=0.125 is midpoint between stop 0 (0.0) and stop 1 (0.25)
        color = interpolate_color(0.125, VIRIDIS)
        assert color.startswith("rgb(")


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestSelectors:
    def test_cell_valid(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 3, "cols": 4})
        assert inst.validate_selector("cell[0][0]") is True
        assert inst.validate_selector("cell[2][3]") is True

    def test_cell_out_of_range(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 3, "cols": 4})
        assert inst.validate_selector("cell[3][0]") is False
        assert inst.validate_selector("cell[0][4]") is False

    def test_all_valid(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 2, "cols": 2})
        assert inst.validate_selector("all") is True

    def test_unknown_selector(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 2, "cols": 2})
        assert inst.validate_selector("nonsense") is False

    def test_addressable_parts(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 2, "cols": 2})
        parts = inst.addressable_parts()
        assert "cell[0][0]" in parts
        assert "cell[0][1]" in parts
        assert "cell[1][0]" in parts
        assert "cell[1][1]" in parts
        assert "all" in parts
        assert len(parts) == 5  # 4 cells + all


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 2, "cols": 2,
            "data": [0.0, 0.5, 0.5, 1.0],
        })
        svg = inst.emit_svg()
        assert 'data-primitive="matrix"' in svg
        assert 'data-shape="m"' in svg
        assert 'data-target="m.cell[0][0]"' in svg
        assert 'data-target="m.cell[1][1]"' in svg

    def test_colorscale_applied(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 1, "cols": 2,
            "data": [0.0, 1.0],
        })
        svg = inst.emit_svg()
        # Should contain rgb fill colors from viridis
        assert "rgb(" in svg

    def test_show_values(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 1, "cols": 2,
            "data": [0.5, 1.0],
            "show_values": True,
        })
        svg = inst.emit_svg()
        assert ">0.5</text>" in svg
        assert ">1</text>" in svg

    def test_state_applied_via_stroke(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 2, "cols": 2,
            "data": [0, 0.5, 0.5, 1],
        })
        inst.set_state("cell[0][0]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_vmin_vmax(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 1, "cols": 2,
            "data": [5, 10],
            "vmin": 0, "vmax": 20,
        })
        svg = inst.emit_svg()
        # t for value 5 with vmin=0, vmax=20 -> 0.25, should be blue-ish
        assert "rgb(" in svg

    def test_label_rendered(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 1, "cols": 1,
            "label": "My Matrix",
        })
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg
        assert "My Matrix" in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_basic_dimensions(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 3, "cols": 4,
            "cell_size": 24,
        })
        x, y, w, h = inst.bounding_box()
        assert x == 0
        assert y == 0
        # 4 cells * 24 + 3 gaps * 1 = 99
        assert w == 99.0
        # 3 cells * 24 + 2 gaps * 1 = 74
        assert h == 74.0


# ---------------------------------------------------------------------------
# Heatmap alias
# ---------------------------------------------------------------------------


class TestHeatmapAlias:
    def test_heatmap_is_matrix(self) -> None:
        inst = HeatmapPrimitive("h", {
            "rows": 2, "cols": 2,
            "data": [0.1, 0.2, 0.3, 0.4],
        })
        assert isinstance(inst, MatrixInstance)
        assert inst.primitive_type == "matrix"
