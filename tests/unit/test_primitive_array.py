"""Tests for the Array primitive.

Covers declaration, selectors, SVG output, bounding box, and error handling.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.array import ArrayInstance, ArrayPrimitive
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_size_creates_cells(self) -> None:
        inst = ArrayPrimitive("a", {"size": 5})
        assert isinstance(inst, ArrayInstance)
        assert inst.size == 5
        assert inst.name == "a"

    def test_n_alias(self) -> None:
        inst = ArrayPrimitive("arr", {"n": 3, "data": [1, 2, 3]})
        assert inst.size == 3
        assert inst.data == [1, 2, 3]

    def test_missing_size_raises_e1400(self) -> None:
        # v0.5.1 split E1103 into per-primitive codes.
        with pytest.raises(ValidationError, match="E1400"):
            ArrayPrimitive("a", {})

    def test_labels_parameter(self) -> None:
        inst = ArrayPrimitive("a", {"size": 5, "labels": "0..4"})
        assert inst.labels == "0..4"

    def test_label_parameter(self) -> None:
        inst = ArrayPrimitive("a", {"size": 3, "label": "heights"})
        assert inst.label == "heights"


# ---------------------------------------------------------------------------
# Addressable parts
# ---------------------------------------------------------------------------


class TestAddressableParts:
    def test_returns_all_cells_and_all(self) -> None:
        inst = ArrayPrimitive("a", {"size": 3})
        parts = inst.addressable_parts()
        assert parts == ["cell[0]", "cell[1]", "cell[2]", "all"]

    def test_single_cell_array(self) -> None:
        inst = ArrayPrimitive("a", {"size": 1})
        assert inst.addressable_parts() == ["cell[0]", "all"]


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_cell_valid(self) -> None:
        inst = ArrayPrimitive("a", {"size": 5})
        assert inst.validate_selector("cell[0]") is True
        assert inst.validate_selector("cell[4]") is True

    def test_cell_out_of_range(self) -> None:
        inst = ArrayPrimitive("a", {"size": 5})
        assert inst.validate_selector("cell[5]") is False

    def test_range_valid(self) -> None:
        inst = ArrayPrimitive("a", {"size": 5})
        assert inst.validate_selector("range[1:3]") is True

    def test_range_invalid(self) -> None:
        inst = ArrayPrimitive("a", {"size": 5})
        assert inst.validate_selector("range[3:1]") is False
        assert inst.validate_selector("range[0:5]") is False

    def test_all_valid(self) -> None:
        inst = ArrayPrimitive("a", {"size": 3})
        assert inst.validate_selector("all") is True

    def test_unknown_selector(self) -> None:
        inst = ArrayPrimitive("a", {"size": 3})
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        inst = ArrayPrimitive("a", {"size": 2, "data": [10, 20]})
        svg = inst.emit_svg()

        assert 'data-primitive="array"' in svg
        assert 'data-shape="a"' in svg
        assert 'data-target="a.cell[0]"' in svg
        assert 'data-target="a.cell[1]"' in svg
        assert ">10</text>" in svg
        assert ">20</text>" in svg

    def test_default_idle_class(self) -> None:
        inst = ArrayPrimitive("a", {"size": 1})
        svg = inst.emit_svg()
        assert "scriba-state-idle" in svg

    def test_state_applied(self) -> None:
        inst = ArrayPrimitive("a", {"size": 2})
        inst.set_state("cell[0]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_value_applied(self) -> None:
        inst = ArrayPrimitive("a", {"size": 2, "data": [0, 0]})
        inst.set_value("cell[1]", "42")
        svg = inst.emit_svg()
        assert ">42</text>" in svg

    def test_label_rendered(self) -> None:
        inst = ArrayPrimitive("a", {"size": 2, "label": "my array"})
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg
        assert "my array" in svg

    def test_index_labels_rendered(self) -> None:
        inst = ArrayPrimitive("a", {"size": 3, "labels": "0..2"})
        svg = inst.emit_svg()
        assert "scriba-index-label" in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_dimensions(self) -> None:
        inst = ArrayPrimitive("a", {"size": 3})
        x, y, w, h = inst.bounding_box()
        assert x == 0
        assert y == 0
        # 3 cells * 60 + 2 gaps * 2 = 184
        assert w == 184.0
        assert h == 40.0  # just cell height, no labels
