"""Tests for the Stack primitive.

Covers declaration, push/pop, orientation, selectors, SVG output,
overflow, and bounding box.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.stack import Stack


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_empty_stack(self) -> None:
        s = Stack("s", {})
        assert len(s.items) == 0
        assert s.orientation == "vertical"

    def test_initial_items_strings(self) -> None:
        s = Stack("s", {"items": ["A", "B", "C"]})
        assert len(s.items) == 3
        assert s.items[0].label == "A"
        assert s.items[2].label == "C"

    def test_initial_items_dicts(self) -> None:
        s = Stack("s", {
            "items": [
                {"label": "X", "value": 1.0},
                {"label": "Y", "value": 2.0},
            ],
        })
        assert s.items[0].label == "X"
        assert s.items[0].value == 1.0

    def test_horizontal_orientation(self) -> None:
        s = Stack("s", {"orientation": "horizontal"})
        assert s.orientation == "horizontal"

    def test_max_visible(self) -> None:
        s = Stack("s", {"max_visible": 5})
        assert s.max_visible == 5

    def test_max_visible_zero_rejected(self) -> None:
        """max_visible must be >= 1 (v0.5.1: E1441)."""
        from scriba.core.errors import ValidationError

        with pytest.raises(ValidationError, match="E1441"):
            Stack("s", {"max_visible": 0})

    def test_unknown_kwargs_rejected(self) -> None:
        """Stack rejects unknown params via E1114.

        Stack previously lacked an ``ACCEPTED_PARAMS`` frozenset, which
        silently accepted any key. Docs-param audit 2026-04-23 flagged
        this as a structural bug — unknown keys now raise E1114 like
        every other primitive.
        """
        from scriba.core.errors import ValidationError

        with pytest.raises(ValidationError, match="E1114"):
            Stack("s", {
                "items": ["A"],
                "cell_width": 999,
            })


# ---------------------------------------------------------------------------
# Push / Pop
# ---------------------------------------------------------------------------


class TestPushPop:
    def test_push_string(self) -> None:
        s = Stack("s", {"items": ["A"]})
        s.apply_command({"push": "B"})
        assert len(s.items) == 2
        assert s.items[1].label == "B"

    def test_push_dict(self) -> None:
        s = Stack("s", {})
        s.apply_command({"push": {"label": "X", "value": 42}})
        assert len(s.items) == 1
        assert s.items[0].label == "X"
        assert s.items[0].value == 42

    def test_pop_one(self) -> None:
        s = Stack("s", {"items": ["A", "B", "C"]})
        s.apply_command({"pop": 1})
        assert len(s.items) == 2
        assert s.items[-1].label == "B"

    def test_pop_multiple(self) -> None:
        s = Stack("s", {"items": ["A", "B", "C"]})
        s.apply_command({"pop": 2})
        assert len(s.items) == 1
        assert s.items[0].label == "A"

    def test_pop_more_than_available(self) -> None:
        s = Stack("s", {"items": ["A"]})
        s.apply_command({"pop": 5})
        assert len(s.items) == 0

    def test_push_then_pop(self) -> None:
        s = Stack("s", {"items": ["A"]})
        s.apply_command({"push": "B"})
        assert len(s.items) == 2
        s.apply_command({"pop": 1})
        assert len(s.items) == 1
        assert s.items[0].label == "A"


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestSelectors:
    def test_addressable_parts(self) -> None:
        s = Stack("s", {"items": ["A", "B", "C"]})
        parts = s.addressable_parts()
        assert "item[0]" in parts
        assert "item[1]" in parts
        assert "item[2]" in parts
        assert "top" in parts
        assert "all" in parts

    def test_empty_stack_has_all_only(self) -> None:
        s = Stack("s", {})
        parts = s.addressable_parts()
        assert "all" in parts
        assert "top" not in parts

    def test_validate_item(self) -> None:
        s = Stack("s", {"items": ["A", "B"]})
        assert s.validate_selector("item[0]") is True
        assert s.validate_selector("item[1]") is True
        assert s.validate_selector("item[2]") is False

    def test_validate_top(self) -> None:
        s = Stack("s", {"items": ["A"]})
        assert s.validate_selector("top") is True

    def test_validate_top_empty(self) -> None:
        s = Stack("s", {})
        assert s.validate_selector("top") is False

    def test_validate_all(self) -> None:
        s = Stack("s", {})
        assert s.validate_selector("all") is True


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        s = Stack("s", {"items": ["A", "B"]})
        svg = s.emit_svg()
        assert 'data-primitive="stack"' in svg
        assert 'data-shape="s"' in svg
        assert ">A</text>" in svg
        assert ">B</text>" in svg

    def test_empty_placeholder(self) -> None:
        s = Stack("s", {})
        svg = s.emit_svg()
        assert "empty" in svg
        assert 'stroke-dasharray="4 2"' in svg

    def test_state_applied(self) -> None:
        s = Stack("s", {"items": ["A", "B"]})
        s.set_state("item[0]", "current")
        svg = s.emit_svg()
        assert "scriba-state-current" in svg

    def test_vertical_layout(self) -> None:
        s = Stack("s", {"items": ["A", "B", "C"]})
        svg = s.emit_svg()
        # All items should be present
        assert 's.item[0]' in svg
        assert 's.item[1]' in svg
        assert 's.item[2]' in svg

    def test_horizontal_layout(self) -> None:
        s = Stack("s", {"items": ["A", "B"], "orientation": "horizontal"})
        svg = s.emit_svg()
        assert ">A</text>" in svg
        assert ">B</text>" in svg


# ---------------------------------------------------------------------------
# Overflow
# ---------------------------------------------------------------------------


class TestOverflow:
    def test_overflow_indicator(self) -> None:
        items = [str(i) for i in range(15)]
        s = Stack("s", {"items": items, "max_visible": 10})
        svg = s.emit_svg()
        assert "+5 more" in svg

    def test_no_overflow_within_limit(self) -> None:
        s = Stack("s", {"items": ["A", "B", "C"], "max_visible": 10})
        svg = s.emit_svg()
        assert "more" not in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_vertical_dimensions(self) -> None:
        s = Stack("s", {"items": ["A", "B", "C"]})
        bbox = s.bounding_box()
        assert bbox.width == 80 + 2 * 8  # cell width + 2 * padding
        assert bbox.height == 3 * 36 + 2 * 4 + 2 * 8  # 3 cells + 2 gaps + 2 padding

    def test_horizontal_dimensions(self) -> None:
        s = Stack("s", {"items": ["A", "B"], "orientation": "horizontal"})
        bbox = s.bounding_box()
        assert bbox.width == 2 * 80 + 1 * 4 + 2 * 8  # 2 cells + 1 gap + 2 padding
        assert bbox.height == 36 + 2 * 8  # 1 cell + 2 padding

    def test_empty_stack_has_minimum_size(self) -> None:
        s = Stack("s", {})
        bbox = s.bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0
