"""Phase B edge-case tests for the Matrix / Heatmap primitive.

Exercises 1x1, uniform values, colorscale, show_values, vmin/vmax,
negative values, state via stroke, selectors, Heatmap alias,
row/col labels, large matrix, and missing params.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.matrix import (
    HeatmapPrimitive,
    MatrixInstance,
    MatrixPrimitive,
    VIRIDIS,
    interpolate_color,
    _text_color_for_background,
)
from scriba.core.errors import ValidationError


@pytest.fixture()
def factory() -> MatrixPrimitive:
    return MatrixPrimitive()


# ---------------------------------------------------------------------------
# 1. Matrix 1x1
# ---------------------------------------------------------------------------


class TestMatrix1x1:
    def test_1x1_declaration(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 1, "cols": 1, "data": [0.5]})
        assert inst.rows == 1
        assert inst.cols == 1
        assert inst.data == [[0.5]]

    def test_1x1_svg_single_cell(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 1, "cols": 1, "data": [0.5]})
        svg = inst.emit_svg({})
        assert svg.count('data-target="m.cell') == 1

    def test_1x1_addressable_parts(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 1, "cols": 1})
        parts = inst.addressable_parts()
        assert len(parts) == 2  # 1 cell + .all


# ---------------------------------------------------------------------------
# 2. Matrix with all same values -- uniform color
# ---------------------------------------------------------------------------


class TestMatrixUniformValues:
    def test_uniform_values_same_color(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [5.0, 5.0, 5.0, 5.0],
        })
        svg = inst.emit_svg({})
        # When all values are same, t = 0.5 for each cell
        expected_color = interpolate_color(0.5, VIRIDIS)
        assert expected_color in svg


# ---------------------------------------------------------------------------
# 3. Viridis maps 0.0 to dark, 1.0 to yellow
# ---------------------------------------------------------------------------


class TestColorscaleMapping:
    def test_zero_maps_to_dark_purple(self) -> None:
        color = interpolate_color(0.0, VIRIDIS)
        assert color == "rgb(68,1,84)"

    def test_one_maps_to_yellow(self) -> None:
        color = interpolate_color(1.0, VIRIDIS)
        assert color == "rgb(253,231,37)"

    def test_text_color_dark_for_bright_bg(self) -> None:
        text_color = _text_color_for_background(1.0, VIRIDIS)
        assert text_color == "#212529"  # dark text for yellow bg

    def test_text_color_white_for_dark_bg(self) -> None:
        text_color = _text_color_for_background(0.0, VIRIDIS)
        assert text_color == "#ffffff"  # white text for dark purple bg


# ---------------------------------------------------------------------------
# 4. show_values=true: text elements present
# ---------------------------------------------------------------------------


class TestShowValues:
    def test_show_values_true(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [1.0, 2.0, 3.0, 4.0],
            "show_values": True,
        })
        svg = inst.emit_svg({})
        assert ">1</text>" in svg
        assert ">2</text>" in svg
        assert ">3</text>" in svg
        assert ">4</text>" in svg

    def test_show_values_formatting(self, factory: MatrixPrimitive) -> None:
        """Verify trailing zeros are stripped."""
        inst = factory.declare("m", {
            "rows": 1, "cols": 1,
            "data": [0.50],
            "show_values": True,
        })
        svg = inst.emit_svg({})
        assert ">0.5</text>" in svg


# ---------------------------------------------------------------------------
# 5. show_values=false (default): no value text
# ---------------------------------------------------------------------------


class TestShowValuesDefault:
    def test_show_values_default_false(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [1.0, 2.0, 3.0, 4.0],
        })
        svg = inst.emit_svg({})
        # No value text elements (only rect elements, no mid-cell text)
        assert ">1</text>" not in svg
        assert ">2</text>" not in svg


# ---------------------------------------------------------------------------
# 6. vmin/vmax explicit: check color mapping
# ---------------------------------------------------------------------------


class TestExplicitVminVmax:
    def test_explicit_vmin_vmax(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 1, "cols": 2,
            "data": [25, 75],
            "vmin": 0, "vmax": 100,
        })
        svg = inst.emit_svg({})
        # t for 25 is 0.25 (blue), t for 75 is 0.75 (green)
        blue_color = interpolate_color(0.25, VIRIDIS)
        green_color = interpolate_color(0.75, VIRIDIS)
        assert blue_color in svg
        assert green_color in svg

    def test_partial_vmin_only(self, factory: MatrixPrimitive) -> None:
        """Only vmin set, vmax from data."""
        inst = factory.declare("m", {
            "rows": 1, "cols": 2,
            "data": [5, 10],
            "vmin": 0,
        })
        # vmax should come from data max (10)
        svg = inst.emit_svg({})
        assert "rgb(" in svg


# ---------------------------------------------------------------------------
# 7. Matrix with negative values
# ---------------------------------------------------------------------------


class TestNegativeValues:
    def test_negative_values_accepted(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [-5, -1, 0, 5],
        })
        svg = inst.emit_svg({})
        assert "rgb(" in svg
        # vmin=-5, vmax=5, t for 0 should be 0.5
        teal_color = interpolate_color(0.5, VIRIDIS)
        assert teal_color in svg


# ---------------------------------------------------------------------------
# 8. Matrix state via border stroke (not fill)
# ---------------------------------------------------------------------------


class TestMatrixStateStroke:
    def test_state_uses_stroke_not_fill(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [0.0, 0.5, 0.5, 1.0],
        })
        svg = inst.emit_svg({"m.cell[0][0]": {"state": "current"}})
        # current stroke color #005a8e should be in the SVG
        assert "#005a8e" in svg
        # The fill should still be the colorscale color, not the state color
        # (the state color only affects stroke)
        colorscale_fill = interpolate_color(0.0, VIRIDIS)
        assert colorscale_fill in svg


# ---------------------------------------------------------------------------
# 9. Matrix cell selector: m.cell[0][0]
# ---------------------------------------------------------------------------


class TestMatrixCellSelector:
    def test_cell_selector_valid(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 3, "cols": 3})
        assert inst.validate_selector("m.cell[0][0]") is True
        assert inst.validate_selector("m.cell[2][2]") is True

    def test_cell_selector_out_of_bounds(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 3, "cols": 3})
        assert inst.validate_selector("m.cell[3][0]") is False
        assert inst.validate_selector("m.cell[0][3]") is False


# ---------------------------------------------------------------------------
# 10. Matrix Heatmap alias -- same behavior
# ---------------------------------------------------------------------------


class TestHeatmapAlias:
    def test_heatmap_produces_matrix_instance(self) -> None:
        h = HeatmapPrimitive()
        inst = h.declare("h", {
            "rows": 2, "cols": 2,
            "data": [0.1, 0.2, 0.3, 0.4],
        })
        assert isinstance(inst, MatrixInstance)
        assert inst.primitive_type == "matrix"

    def test_heatmap_svg_same_as_matrix(self) -> None:
        h = HeatmapPrimitive()
        m = MatrixPrimitive()
        data = [0.1, 0.2, 0.3, 0.4]
        params = {"rows": 2, "cols": 2, "data": data}
        inst_h = h.declare("x", params)
        inst_m = m.declare("x", params)
        # Both should produce identical SVG
        assert inst_h.emit_svg({}) == inst_m.emit_svg({})


# ---------------------------------------------------------------------------
# 11. Matrix with row_labels/col_labels
# ---------------------------------------------------------------------------


class TestMatrixLabels:
    def test_row_labels_rendered(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "row_labels": ["R0", "R1"],
        })
        svg = inst.emit_svg({})
        assert "R0" in svg
        assert "R1" in svg

    def test_col_labels_rendered(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "col_labels": ["C0", "C1"],
        })
        svg = inst.emit_svg({})
        assert "C0" in svg
        assert "C1" in svg

    def test_labels_add_offset(self, factory: MatrixPrimitive) -> None:
        inst_no_labels = factory.declare("m", {"rows": 2, "cols": 2})
        inst_with_labels = factory.declare("m", {
            "rows": 2, "cols": 2,
            "row_labels": ["A", "B"],
            "col_labels": ["X", "Y"],
        })
        _, _, w1, h1 = inst_no_labels.bounding_box()
        _, _, w2, h2 = inst_with_labels.bounding_box()
        assert w2 > w1  # row labels add width
        assert h2 > h1  # col labels add height


# ---------------------------------------------------------------------------
# 12. Large matrix (20x20) -- should not crash
# ---------------------------------------------------------------------------


class TestLargeMatrix:
    def test_20x20_renders(self, factory: MatrixPrimitive) -> None:
        data = [float(i) for i in range(400)]
        inst = factory.declare("m", {"rows": 20, "cols": 20, "data": data})
        svg = inst.emit_svg({})
        assert 'data-target="m.cell[19][19]"' in svg
        assert 'data-target="m.cell[0][0]"' in svg

    def test_20x20_addressable_parts(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {"rows": 20, "cols": 20})
        parts = inst.addressable_parts()
        assert len(parts) == 401  # 400 cells + .all


# ---------------------------------------------------------------------------
# 13. Missing rows/cols -- E1103
# ---------------------------------------------------------------------------


class TestMatrixMissingParams:
    def test_missing_rows_raises(self, factory: MatrixPrimitive) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            factory.declare("m", {"cols": 3})

    def test_missing_cols_raises(self, factory: MatrixPrimitive) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            factory.declare("m", {"rows": 3})

    def test_missing_both_raises(self, factory: MatrixPrimitive) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            factory.declare("m", {})


# ---------------------------------------------------------------------------
# 14. Highlight overlay
# ---------------------------------------------------------------------------


class TestMatrixHighlight:
    def test_highlight_produces_dashed_rect(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [0, 0.5, 0.5, 1],
        })
        svg = inst.emit_svg({"m.cell[0][0]": {"highlighted": True}})
        assert "#F0E442" in svg
        assert "stroke-dasharray" in svg

    def test_highlight_and_state_both_apply(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 2, "cols": 2,
            "data": [0, 0.5, 0.5, 1],
        })
        svg = inst.emit_svg({
            "m.cell[0][0]": {"state": "current", "highlighted": True},
        })
        assert "#F0E442" in svg  # highlight
        assert "#005a8e" in svg  # current stroke


# ---------------------------------------------------------------------------
# 15. Caption label
# ---------------------------------------------------------------------------


class TestMatrixCaption:
    def test_label_rendered(self, factory: MatrixPrimitive) -> None:
        inst = factory.declare("m", {
            "rows": 1, "cols": 1,
            "label": "Confusion Matrix",
        })
        svg = inst.emit_svg({})
        assert "Confusion Matrix" in svg
        assert "scriba-primitive-label" in svg
