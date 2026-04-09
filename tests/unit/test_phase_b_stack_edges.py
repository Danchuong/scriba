"""Phase B edge-case tests for the Stack primitive.

Exercises empty stack, single item, orientation, push/pop,
pop from empty, selectors, max_visible overflow, state, and highlight.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.stack import Stack, StackItem
from scriba.animation.primitives.base import BoundingBox, STATE_COLORS


# ---------------------------------------------------------------------------
# 1. Stack with empty items (no initial items)
# ---------------------------------------------------------------------------


class TestEmptyStack:
    def test_empty_stack_creation(self) -> None:
        s = Stack("s", {})
        assert len(s.items) == 0

    def test_empty_stack_svg_placeholder(self) -> None:
        s = Stack("s", {})
        svg = s.emit_svg()
        assert "empty" in svg
        assert "stroke-dasharray" in svg

    def test_empty_stack_addressable_parts(self) -> None:
        s = Stack("s", {})
        parts = s.addressable_parts()
        # Only "all" when empty (no items, no "top")
        assert parts == ["all"]

    def test_empty_stack_bounding_box(self) -> None:
        s = Stack("s", {})
        bb = s.bounding_box()
        assert isinstance(bb, BoundingBox)
        assert bb.width > 0
        assert bb.height > 0


# ---------------------------------------------------------------------------
# 2. Stack with 1 item
# ---------------------------------------------------------------------------


class TestSingleItemStack:
    def test_single_item_from_string(self) -> None:
        s = Stack("s", {"items": ["hello"]})
        assert len(s.items) == 1
        assert s.items[0].label == "hello"

    def test_single_item_from_dict(self) -> None:
        s = Stack("s", {"items": [{"label": "x", "value": 42}]})
        assert s.items[0].label == "x"
        assert s.items[0].value == 42

    def test_single_item_svg_renders(self) -> None:
        s = Stack("s", {"items": ["hello"]})
        svg = s.emit_svg()
        assert "hello" in svg
        assert 'data-target="s.item[0]"' in svg

    def test_single_item_addressable_parts(self) -> None:
        s = Stack("s", {"items": ["hello"]})
        parts = s.addressable_parts()
        assert "item[0]" in parts
        assert "top" in parts
        assert "all" in parts


# ---------------------------------------------------------------------------
# 3. Stack orientation="horizontal" -- different layout
# ---------------------------------------------------------------------------


class TestHorizontalStack:
    def test_horizontal_orientation(self) -> None:
        s = Stack("s", {"items": ["a", "b", "c"], "orientation": "horizontal"})
        assert s.orientation == "horizontal"

    def test_horizontal_bounding_box_wider(self) -> None:
        s_h = Stack("s", {"items": ["a", "b", "c"], "orientation": "horizontal"})
        s_v = Stack("s", {"items": ["a", "b", "c"], "orientation": "vertical"})
        bb_h = s_h.bounding_box()
        bb_v = s_v.bounding_box()
        # Horizontal should be wider than vertical
        assert bb_h.width > bb_v.width
        # Vertical should be taller than horizontal
        assert bb_v.height > bb_h.height

    def test_horizontal_svg_renders(self) -> None:
        s = Stack("s", {"items": ["a", "b"], "orientation": "horizontal"})
        svg = s.emit_svg()
        assert "a" in svg
        assert "b" in svg


# ---------------------------------------------------------------------------
# 4. Stack push -- adds item
# ---------------------------------------------------------------------------


class TestStackPush:
    def test_push_string(self) -> None:
        s = Stack("s", {"items": ["a"]})
        s.apply_command({"push": "b"})
        assert len(s.items) == 2
        assert s.items[-1].label == "b"

    def test_push_dict(self) -> None:
        s = Stack("s", {"items": []})
        s.apply_command({"push": {"label": "x", "value": 10}})
        assert len(s.items) == 1
        assert s.items[0].label == "x"
        assert s.items[0].value == 10

    def test_push_multiple(self) -> None:
        s = Stack("s", {"items": []})
        s.apply_command({"push": "a"})
        s.apply_command({"push": "b"})
        s.apply_command({"push": "c"})
        assert len(s.items) == 3
        assert s.items[-1].label == "c"


# ---------------------------------------------------------------------------
# 5. Stack pop -- removes top
# ---------------------------------------------------------------------------


class TestStackPop:
    def test_pop_removes_top(self) -> None:
        s = Stack("s", {"items": ["a", "b", "c"]})
        s.apply_command({"pop": 1})
        assert len(s.items) == 2
        assert s.items[-1].label == "b"

    def test_pop_multiple(self) -> None:
        s = Stack("s", {"items": ["a", "b", "c"]})
        s.apply_command({"pop": 2})
        assert len(s.items) == 1
        assert s.items[0].label == "a"


# ---------------------------------------------------------------------------
# 6. Stack pop from empty -- handle gracefully
# ---------------------------------------------------------------------------


class TestStackPopEmpty:
    def test_pop_from_empty_no_crash(self) -> None:
        s = Stack("s", {"items": []})
        s.apply_command({"pop": 1})
        assert len(s.items) == 0

    def test_pop_more_than_available(self) -> None:
        s = Stack("s", {"items": ["a"]})
        s.apply_command({"pop": 5})
        assert len(s.items) == 0


# ---------------------------------------------------------------------------
# 7. Stack item[0] selector (bottom)
# ---------------------------------------------------------------------------


class TestStackItemSelector:
    def test_item_0_valid(self) -> None:
        s = Stack("s", {"items": ["a", "b", "c"]})
        assert s.validate_selector("item[0]") is True

    def test_item_out_of_range_invalid(self) -> None:
        s = Stack("s", {"items": ["a", "b"]})
        assert s.validate_selector("item[2]") is False

    def test_item_negative_invalid(self) -> None:
        """Negative indices are not supported in the regex."""
        s = Stack("s", {"items": ["a", "b"]})
        assert s.validate_selector("item[-1]") is False


# ---------------------------------------------------------------------------
# 8. Stack s.top selector
# ---------------------------------------------------------------------------


class TestStackTopSelector:
    def test_top_valid_when_items_exist(self) -> None:
        s = Stack("s", {"items": ["a", "b"]})
        assert s.validate_selector("top") is True

    def test_top_invalid_when_empty(self) -> None:
        s = Stack("s", {"items": []})
        assert s.validate_selector("top") is False

    def test_top_in_addressable_parts(self) -> None:
        s = Stack("s", {"items": ["a"]})
        parts = s.addressable_parts()
        assert "top" in parts


# ---------------------------------------------------------------------------
# 9. Stack with max_visible=3, items=5 -- overflow
# ---------------------------------------------------------------------------


class TestStackOverflow:
    def test_overflow_indicator(self) -> None:
        s = Stack("s", {"items": ["a", "b", "c", "d", "e"], "max_visible": 3})
        svg = s.emit_svg()
        assert "+2 more" in svg

    def test_overflow_shows_top_items(self) -> None:
        s = Stack("s", {"items": ["a", "b", "c", "d", "e"], "max_visible": 3})
        svg = s.emit_svg()
        # Should show the top 3 items (c, d, e)
        assert "e" in svg
        assert "d" in svg
        assert "c" in svg


# ---------------------------------------------------------------------------
# 10. Stack state: recolor item
# ---------------------------------------------------------------------------


class TestStackRecolor:
    def test_recolor_item(self) -> None:
        s = Stack("s", {"items": ["a", "b", "c"]})
        s.set_state("item[0]", "current")
        svg = s.emit_svg()
        assert "scriba-state-current" in svg

    def test_recolor_top(self) -> None:
        s = Stack("s", {"items": ["a", "b", "c"]})
        s.set_state("top", "done")
        svg = s.emit_svg()
        assert "scriba-state-done" in svg


# ---------------------------------------------------------------------------
# 11. Stack highlight item -- overlay
# ---------------------------------------------------------------------------


class TestStackHighlight:
    def test_highlight_produces_dashed_rect(self) -> None:
        s = Stack("s", {"items": ["a", "b"]})
        s._highlighted = {"item[1]"}
        svg = s.emit_svg()
        assert "#F0E442" in svg
        assert "stroke-dasharray" in svg

    def test_highlight_top_produces_overlay(self) -> None:
        s = Stack("s", {"items": ["a", "b"]})
        s._highlighted = {"top"}
        svg = s.emit_svg()
        assert "#F0E442" in svg


# ---------------------------------------------------------------------------
# 12. Stack label caption
# ---------------------------------------------------------------------------


class TestStackLabel:
    def test_label_rendered(self) -> None:
        s = Stack("s", {"items": ["a"], "label": "Call Stack"})
        svg = s.emit_svg()
        assert "Call Stack" in svg
        assert "scriba-primitive-label" in svg

    def test_no_label_no_caption(self) -> None:
        s = Stack("s", {"items": ["a"]})
        svg = s.emit_svg()
        assert "scriba-primitive-label" not in svg
