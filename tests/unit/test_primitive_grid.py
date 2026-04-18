"""Tests for the Grid primitive.

Covers declaration, selectors, SVG output, bounding box, and error handling.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.grid import GridPrimitive
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_3x3_grid(self) -> None:
        inst = GridPrimitive("g", {"rows": 3, "cols": 3})
        assert isinstance(inst, GridPrimitive)
        assert inst.rows == 3
        assert inst.cols == 3
        assert inst.name == "g"

    def test_with_2d_data(self) -> None:
        data = [[0, 0, 0], [0, 1, 0], [0, 0, 0]]
        inst = GridPrimitive("g", {"rows": 3, "cols": 3, "data": data})
        assert inst.data == [0, 0, 0, 0, 1, 0, 0, 0, 0]

    def test_with_flat_data(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "data": [1, 2, 3, 4]})
        assert inst.data == [1, 2, 3, 4]

    def test_missing_rows_raises_e1410(self) -> None:
        with pytest.raises(ValidationError, match="E1410"):
            GridPrimitive("g", {"cols": 3})

    def test_missing_cols_raises_e1410(self) -> None:
        with pytest.raises(ValidationError, match="E1410"):
            GridPrimitive("g", {"rows": 3})

    def test_missing_both_raises_e1410(self) -> None:
        with pytest.raises(ValidationError, match="E1410"):
            GridPrimitive("g", {})

    def test_label_parameter(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "label": "board"})
        assert inst.label == "board"


# ---------------------------------------------------------------------------
# Addressable parts
# ---------------------------------------------------------------------------


class TestAddressableParts:
    def test_3x3_returns_all_cells_and_all(self) -> None:
        inst = GridPrimitive("g", {"rows": 3, "cols": 3})
        parts = inst.addressable_parts()
        assert len(parts) == 3 * 3 + 1  # 9 cells + all
        assert parts[0] == "cell[0][0]"
        assert parts[8] == "cell[2][2]"
        assert parts[-1] == "all"

    def test_1x1_grid(self) -> None:
        inst = GridPrimitive("g", {"rows": 1, "cols": 1})
        assert inst.addressable_parts() == ["cell[0][0]", "all"]


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_cell_valid(self) -> None:
        inst = GridPrimitive("g", {"rows": 3, "cols": 3})
        assert inst.validate_selector("cell[0][0]") is True
        assert inst.validate_selector("cell[1][2]") is True
        assert inst.validate_selector("cell[2][2]") is True

    def test_cell_out_of_range(self) -> None:
        inst = GridPrimitive("g", {"rows": 3, "cols": 3})
        assert inst.validate_selector("cell[3][0]") is False
        assert inst.validate_selector("cell[0][3]") is False

    def test_all_valid(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2})
        assert inst.validate_selector("all") is True

    def test_range_not_supported(self) -> None:
        """Grid does NOT support .range selectors."""
        inst = GridPrimitive("g", {"rows": 3, "cols": 3})
        assert inst.validate_selector("range[0:2]") is False

    def test_garbage_selector(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2})
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        data = [[1, 2], [3, 4]]
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "data": data})
        svg = inst.emit_svg()

        assert 'data-primitive="grid"' in svg
        assert 'data-shape="g"' in svg
        assert 'data-target="g.cell[0][0]"' in svg
        assert 'data-target="g.cell[0][1]"' in svg
        assert 'data-target="g.cell[1][0]"' in svg
        assert 'data-target="g.cell[1][1]"' in svg
        assert ">1</text>" in svg
        assert ">4</text>" in svg

    def test_default_idle_class(self) -> None:
        inst = GridPrimitive("g", {"rows": 1, "cols": 1})
        svg = inst.emit_svg()
        assert "scriba-state-idle" in svg

    def test_state_applied(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2})
        inst.set_state("cell[0][0]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_value_override(self) -> None:
        data = [[0, 0], [0, 0]]
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "data": data})
        inst.set_value("cell[1][1]", "42")
        svg = inst.emit_svg()
        assert ">42</text>" in svg

    def test_label_rendered(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "label": "board"})
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg
        assert "board" in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_dimensions_3x3(self) -> None:
        inst = GridPrimitive("g", {"rows": 3, "cols": 3})
        x, y, w, h = inst.bounding_box()
        assert x == 0
        assert y == 0
        # 3 cells * 60 + 2 gaps * 2 = 184
        assert w == 184.0
        # 3 cells * 40 + 2 gaps * 2 = 124
        assert h == 124.0

    def test_dimensions_with_label(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "label": "test"})
        _, _, _, h = inst.bounding_box()
        # 2*40 + 1*2 = 82 (grid) + 16 (label offset) = 98
        assert h == 98.0
