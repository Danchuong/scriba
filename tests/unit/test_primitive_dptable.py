"""Tests for the DPTable primitive.

Covers 1D and 2D modes, selectors, SVG output, arrows, and error handling.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.dptable import DPTableInstance, DPTablePrimitive
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_1d_with_n(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 5})
        assert isinstance(inst, DPTableInstance)
        assert inst.cols == 5
        assert inst.is_2d is False

    def test_2d_with_rows_cols(self) -> None:
        inst = DPTablePrimitive("dp", {"rows": 3, "cols": 3})
        assert inst.rows == 3
        assert inst.cols == 3
        assert inst.is_2d is True

    def test_missing_n_and_rows_cols_raises_e1103(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            DPTablePrimitive("dp", {})

    def test_missing_cols_raises_e1103(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            DPTablePrimitive("dp", {"rows": 3})


# ---------------------------------------------------------------------------
# Addressable parts
# ---------------------------------------------------------------------------


class TestAddressableParts:
    def test_1d_parts(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 3})
        parts = inst.addressable_parts()
        assert "cell[0]" in parts
        assert "cell[1]" in parts
        assert "cell[2]" in parts
        assert "all" in parts

    def test_2d_parts(self) -> None:
        inst = DPTablePrimitive("dp", {"rows": 2, "cols": 2})
        parts = inst.addressable_parts()
        assert "cell[0][0]" in parts
        assert "cell[0][1]" in parts
        assert "cell[1][0]" in parts
        assert "cell[1][1]" in parts
        assert "all" in parts


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_cell_1d_valid(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 5})
        assert inst.validate_selector("cell[0]") is True
        assert inst.validate_selector("cell[4]") is True

    def test_cell_1d_out_of_range(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 5})
        assert inst.validate_selector("cell[5]") is False

    def test_cell_2d_valid(self) -> None:
        inst = DPTablePrimitive("dp", {"rows": 3, "cols": 3})
        assert inst.validate_selector("cell[0][0]") is True
        assert inst.validate_selector("cell[2][2]") is True

    def test_cell_2d_out_of_range(self) -> None:
        inst = DPTablePrimitive("dp", {"rows": 3, "cols": 3})
        assert inst.validate_selector("cell[3][0]") is False

    def test_range_1d_valid(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 5})
        assert inst.validate_selector("range[1:3]") is True

    def test_all_valid(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 3})
        assert inst.validate_selector("all") is True


# ---------------------------------------------------------------------------
# SVG output -- 1D
# ---------------------------------------------------------------------------


class TestEmitSvg1D:
    def test_basic_structure(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 3, "data": [0, 1, 2]})
        svg = inst.emit_svg()

        assert 'data-primitive="dptable"' in svg
        assert 'data-target="dp.cell[0]"' in svg
        assert 'data-target="dp.cell[2]"' in svg
        assert ">0</text>" in svg

    def test_state_applied(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 2})
        inst.set_state("cell[0]", "done")
        svg = inst.emit_svg()
        assert "scriba-state-done" in svg

    def test_value_applied(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 2})
        inst.set_value("cell[1]", "99")
        svg = inst.emit_svg()
        assert ">99</text>" in svg


# ---------------------------------------------------------------------------
# SVG output -- 2D
# ---------------------------------------------------------------------------


class TestEmitSvg2D:
    def test_grid_layout(self) -> None:
        inst = DPTablePrimitive(
            "dp", {"rows": 2, "cols": 2, "data": [1, 2, 3, 4]}
        )
        svg = inst.emit_svg()

        assert 'data-target="dp.cell[0][0]"' in svg
        assert 'data-target="dp.cell[1][1]"' in svg
        assert ">1</text>" in svg
        assert ">4</text>" in svg

    def test_2d_state(self) -> None:
        inst = DPTablePrimitive("dp", {"rows": 2, "cols": 2})
        inst.set_state("cell[1][0]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg


# ---------------------------------------------------------------------------
# Arrow annotations
# ---------------------------------------------------------------------------


class TestArrowAnnotation:
    def test_bezier_path_generated(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 5})
        inst.set_annotations([
            {
                "target": "dp.cell[3]",
                "arrow_from": "dp.cell[1]",
                "label": "30",
                "color": "good",
            }
        ])
        svg = inst.emit_svg()

        assert "scriba-annotation" in svg
        assert "scriba-annotation-good" in svg
        assert "<path" in svg
        assert "scriba-arrow-good" in svg
        assert ">30</text>" in svg

    def test_2d_arrow(self) -> None:
        inst = DPTablePrimitive("dp", {"rows": 3, "cols": 3})
        inst.set_annotations([
            {
                "target": "dp.cell[0][1]",
                "arrow_from": "dp.cell[1][1]",
                "label": "",
                "color": "info",
            }
        ])
        svg = inst.emit_svg()
        assert "<path" in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_1d_dimensions(self) -> None:
        inst = DPTablePrimitive("dp", {"n": 5})
        x, y, w, h = inst.bounding_box()
        assert x == 0
        assert y == 0
        # 5 cells * 60 + 4 gaps * 2 = 308
        assert w == 308.0
        assert h == 40.0

    def test_2d_dimensions(self) -> None:
        inst = DPTablePrimitive("dp", {"rows": 3, "cols": 3})
        x, y, w, h = inst.bounding_box()
        assert x == 0
        assert y == 0
        # 3*60 + 2*2 = 184 wide, 3*40 + 2*2 = 124 tall
        assert w == 184.0
        assert h == 124.0
