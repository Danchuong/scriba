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


@pytest.fixture()
def factory() -> MatrixPrimitive:
    return MatrixPrimitive()


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_basic_declaration(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 3, "cols": 4,
            "data": [float(i) for i in range(12)],
        })
        assert isinstance(inst, MatrixInstance)
        assert inst.rows == 3
        assert inst.cols == 4
        assert inst.shape_name == "m"
        assert inst.primitive_type == "matrix"

    def test_2d_data(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [[0.1, 0.2], [0.3, 0.4]],
        })
        assert inst.data == [[0.1, 0.2], [0.3, 0.4]]

    def test_flat_data_reshaping(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 3,
            "data": [1, 2, 3, 4, 5, 6],
        })
        assert inst.data == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]

    def test_missing_rows_raises(self, factory: MatrixPrimitive) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            factory.declare("m", {"cols": 3, "data": [1, 2, 3]})

    def test_missing_cols_raises(self, factory: MatrixPrimitive) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            factory.declare("m", {"rows": 3, "data": [1, 2, 3]})

    def test_data_length_mismatch(self, factory: MatrixPrimitive) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            factory.declare("m", {"rows": 2, "cols": 2, "data": [1, 2, 3]})

    def test_empty_data_fills_zeros(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 2, "cols": 2})
        assert inst.data == [[0.0, 0.0], [0.0, 0.0]]

    def test_default_colorscale(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 1, "cols": 1})
        assert inst.colorscale == "viridis"

    def test_show_values_default_false(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 1, "cols": 1})
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
    def test_cell_valid(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 3, "cols": 4})
        assert inst.validate_selector("m.cell[0][0]") is True
        assert inst.validate_selector("m.cell[2][3]") is True

    def test_cell_out_of_range(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 3, "cols": 4})
        assert inst.validate_selector("m.cell[3][0]") is False
        assert inst.validate_selector("m.cell[0][4]") is False

    def test_all_valid(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 2, "cols": 2})
        assert inst.validate_selector("m.all") is True

    def test_wrong_name(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 2, "cols": 2})
        assert inst.validate_selector("x.cell[0][0]") is False

    def test_addressable_parts(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 2, "cols": 2})
        parts = inst.addressable_parts()
        assert "m.cell[0][0]" in parts
        assert "m.cell[0][1]" in parts
        assert "m.cell[1][0]" in parts
        assert "m.cell[1][1]" in parts
        assert "m.all" in parts
        assert len(parts) == 5  # 4 cells + all


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [0.0, 0.5, 0.5, 1.0],
        })
        svg = inst.emit_svg({})
        assert 'data-primitive="matrix"' in svg
        assert 'data-shape="m"' in svg
        assert 'data-target="m.cell[0][0]"' in svg
        assert 'data-target="m.cell[1][1]"' in svg

    def test_colorscale_applied(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 1, "cols": 2,
            "data": [0.0, 1.0],
        })
        svg = inst.emit_svg({})
        # Should contain rgb fill colors from viridis
        assert "rgb(" in svg

    def test_show_values(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 1, "cols": 2,
            "data": [0.5, 1.0],
            "show_values": True,
        })
        svg = inst.emit_svg({})
        assert ">0.5</text>" in svg
        assert ">1</text>" in svg

    def test_state_applied_via_stroke(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [0, 0.5, 0.5, 1],
        })
        svg = inst.emit_svg({"m.cell[0][0]": {"state": "current"}})
        assert "scriba-state-current" in svg
        # State should affect stroke, not fill
        assert '#005a8e' in svg  # current state stroke color

    def test_vmin_vmax(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 1, "cols": 2,
            "data": [5, 10],
            "vmin": 0, "vmax": 20,
        })
        svg = inst.emit_svg({})
        # t for value 5 with vmin=0, vmax=20 -> 0.25, should be blue-ish
        assert "rgb(" in svg

    def test_label_rendered(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 1, "cols": 1,
            "label": "My Matrix",
        })
        svg = inst.emit_svg({})
        assert "scriba-primitive-label" in svg
        assert "My Matrix" in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_basic_dimensions(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
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
        heatmap = HeatmapPrimitive()
        inst = heatmap.declare("h", {
            "rows": 2, "cols": 2,
            "data": [0.1, 0.2, 0.3, 0.4],
        })
        assert isinstance(inst, MatrixInstance)
        assert inst.primitive_type == "matrix"
