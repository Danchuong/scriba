"""Tests for the Array primitive.

Covers declaration, selectors, SVG output, bounding box, and error handling.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.array import ArrayInstance, ArrayPrimitive
from scriba.core.errors import ValidationError


@pytest.fixture()
def factory() -> ArrayPrimitive:
    return ArrayPrimitive()


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_size_creates_cells(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 5})
        assert isinstance(inst, ArrayInstance)
        assert inst.size == 5
        assert inst.shape_name == "a"

    def test_n_alias(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("arr", {"n": 3, "data": [1, 2, 3]})
        assert inst.size == 3
        assert inst.data == [1, 2, 3]

    def test_missing_size_raises_e1103(self, factory: ArrayPrimitive) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            factory.declare("a", {})

    def test_labels_parameter(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 5, "labels": "0..4"})
        assert inst.labels == "0..4"

    def test_label_parameter(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 3, "label": "heights"})
        assert inst.label == "heights"


# ---------------------------------------------------------------------------
# Addressable parts
# ---------------------------------------------------------------------------


class TestAddressableParts:
    def test_returns_all_cells_and_all(
        self, factory: ArrayPrimitive
    ) -> None:
        inst = factory.declare("a", {"size": 3})
        parts = inst.addressable_parts()
        assert parts == ["a.cell[0]", "a.cell[1]", "a.cell[2]", "a.all"]

    def test_single_cell_array(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 1})
        assert inst.addressable_parts() == ["a.cell[0]", "a.all"]


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_cell_valid(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 5})
        assert inst.validate_selector("a.cell[0]") is True
        assert inst.validate_selector("a.cell[4]") is True

    def test_cell_out_of_range(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 5})
        assert inst.validate_selector("a.cell[5]") is False

    def test_range_valid(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 5})
        assert inst.validate_selector("a.range[1:3]") is True

    def test_range_invalid(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 5})
        assert inst.validate_selector("a.range[3:1]") is False
        assert inst.validate_selector("a.range[0:5]") is False

    def test_all_valid(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 3})
        assert inst.validate_selector("a.all") is True

    def test_wrong_name(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 3})
        assert inst.validate_selector("b.cell[0]") is False

    def test_garbage_selector(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 3})
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 2, "data": [10, 20]})
        svg = inst.emit_svg({})

        assert 'data-primitive="array"' in svg
        assert 'data-shape="a"' in svg
        assert 'data-target="a.cell[0]"' in svg
        assert 'data-target="a.cell[1]"' in svg
        assert ">10</text>" in svg
        assert ">20</text>" in svg

    def test_default_idle_class(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 1})
        svg = inst.emit_svg({})
        assert "scriba-state-idle" in svg

    def test_state_applied(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 2})
        svg = inst.emit_svg({"a.cell[0]": {"state": "current"}})
        assert "scriba-state-current" in svg

    def test_value_applied(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 2, "data": [0, 0]})
        svg = inst.emit_svg({"a.cell[1]": {"value": 42}})
        assert ">42</text>" in svg

    def test_label_rendered(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 2, "label": "my array"})
        svg = inst.emit_svg({})
        assert "scriba-primitive-label" in svg
        assert "my array" in svg

    def test_index_labels_rendered(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 3, "labels": "0..2"})
        svg = inst.emit_svg({})
        assert "scriba-index-label" in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_dimensions(self, factory: ArrayPrimitive) -> None:
        inst = factory.declare("a", {"size": 3})
        x, y, w, h = inst.bounding_box()
        assert x == 0
        assert y == 0
        # 3 cells * 60 + 2 gaps * 2 = 184
        assert w == 184.0
        assert h == 40.0  # just cell height, no labels
