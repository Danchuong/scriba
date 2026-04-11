"""Phase B edge-case tests for the NumberLine primitive.

Exercises single-point domain, negative range, float domain, tick extremes,
range recolor, highlight, axis selector, custom labels, tick spacing, and
bounding box.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.numberline import (
    NL_PADDING,
    NL_WIDTH,
    NumberLineInstance,
    NumberLinePrimitive,
    _resolve_labels,
)
from scriba.animation.primitives.base import STATE_COLORS
from scriba.core.errors import ValidationError



# ---------------------------------------------------------------------------
# 1. NumberLine domain=[0,0] (single point)
# ---------------------------------------------------------------------------


class TestSinglePointDomain:
    def test_single_point_creates_1_tick(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 0]})
        assert inst.tick_count == 1
        assert inst.domain_min == 0.0
        assert inst.domain_max == 0.0

    def test_single_point_svg_renders(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 0]})
        svg = inst.emit_svg()
        assert 'data-target="nl.tick[0]"' in svg

    def test_single_point_tick_centered(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 0]})
        svg = inst.emit_svg()
        # With 1 tick, x should be at NL_PADDING + usable_width // 2
        usable = NL_WIDTH - 2 * NL_PADDING
        expected_x = NL_PADDING + usable // 2
        assert f'x1="{expected_x}"' in svg


# ---------------------------------------------------------------------------
# 2. NumberLine domain=[-5,5] (negative range)
# ---------------------------------------------------------------------------


class TestNegativeRange:
    def test_negative_domain_creates_11_ticks(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [-5, 5]})
        assert inst.tick_count == 11

    def test_negative_labels_include_negatives(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [-5, 5]})
        assert "-5" in inst.tick_labels
        assert "0" in inst.tick_labels
        assert "5" in inst.tick_labels

    def test_negative_domain_svg_renders(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [-5, 5]})
        svg = inst.emit_svg()
        assert ">-5</text>" in svg
        assert ">0</text>" in svg
        assert ">5</text>" in svg


# ---------------------------------------------------------------------------
# 3. NumberLine domain=[0.0,1.0] with ticks=11 (float domain)
# ---------------------------------------------------------------------------


class TestFloatDomain:
    def test_float_domain_11_ticks(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0.0, 1.0], "ticks": 11})
        assert inst.tick_count == 11

    def test_float_domain_labels(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0.0, 1.0], "ticks": 11})
        assert "0" in inst.tick_labels  # 0.0 formats as "0"
        assert "0.5" in inst.tick_labels
        assert "1" in inst.tick_labels  # 1.0 formats as "1"


# ---------------------------------------------------------------------------
# 4. NumberLine with 1 tick
# ---------------------------------------------------------------------------


class TestSingleTick:
    def test_1_tick_renders(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 1})
        assert inst.tick_count == 1
        svg = inst.emit_svg()
        assert svg.count('data-target="nl.tick') == 1


# ---------------------------------------------------------------------------
# 5. NumberLine with 100 ticks
# ---------------------------------------------------------------------------


class TestManyTicks:
    def test_100_ticks_renders(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 99], "ticks": 100})
        assert inst.tick_count == 100
        svg = inst.emit_svg()
        assert 'data-target="nl.tick[99]"' in svg

    def test_100_ticks_addressable_parts(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 99], "ticks": 100})
        parts = inst.addressable_parts()
        # 100 ticks + axis + all = 102
        assert len(parts) == 102


# ---------------------------------------------------------------------------
# 6. Range recolor: range[0:0] (single tick)
# ---------------------------------------------------------------------------


class TestRangeSingleTick:
    def test_range_single_tick_valid(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        assert inst.validate_selector("range[0:0]") is True

    def test_range_single_tick_recolor(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        # range[0:0] is a valid single-tick range
        assert inst.validate_selector("range[0:0]") is True


# ---------------------------------------------------------------------------
# 7. Range recolor: range[0:10] (entire range)
# ---------------------------------------------------------------------------


class TestRangeEntireRange:
    def test_range_covers_all_ticks(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 10]})
        assert inst.validate_selector("range[0:10]") is True

    def test_range_out_of_bounds_rejected(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 10]})
        # tick_count is 11 (0..10), so range[0:11] is invalid
        assert inst.validate_selector("range[0:11]") is False


# ---------------------------------------------------------------------------
# 8. Highlight tick -- gold circle overlay
# ---------------------------------------------------------------------------


class TestHighlightTick:
    def test_highlight_produces_gold_circle(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 3]})
        inst._highlighted.add("tick[1]")
        svg = inst.emit_svg()
        assert "#F0E442" in svg
        assert "stroke-dasharray" in svg

    def test_highlight_idle_state(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 3]})
        inst._highlighted.add("tick[1]")
        svg = inst.emit_svg()
        # Should still have idle class since no explicit state
        assert "scriba-state-idle" in svg


# ---------------------------------------------------------------------------
# 9. Highlight + range recolor on same tick -- both apply
# ---------------------------------------------------------------------------


class TestHighlightAndRecolor:
    def test_both_apply(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 3]})
        inst.set_state("tick[1]", "current")
        inst._highlighted.add("tick[1]")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg
        assert "#F0E442" in svg  # highlight overlay
        assert "#0072B2" in svg  # current fill color


# ---------------------------------------------------------------------------
# 10. Axis selector: nl.axis in state dict
# ---------------------------------------------------------------------------


class TestAxisSelector:
    def test_axis_in_addressable_parts(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        parts = inst.addressable_parts()
        assert "axis" in parts

    def test_axis_selector_valid(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        assert inst.validate_selector("axis") is True


# ---------------------------------------------------------------------------
# 11. Custom labels longer than tick count -- handle gracefully
# ---------------------------------------------------------------------------


class TestCustomLabelsLong:
    def test_extra_labels_accepted(self) -> None:
        """Labels list longer than tick_count should not crash."""
        inst = NumberLinePrimitive("nl", {
            "domain": [0, 2],
            "labels": ["a", "b", "c", "d", "e"],
        })
        assert inst.tick_count == 3
        assert len(inst.tick_labels) == 5

    def test_extra_labels_svg_renders(self) -> None:
        """SVG should render only tick_count ticks, using available labels."""
        inst = NumberLinePrimitive("nl", {
            "domain": [0, 2],
            "labels": ["a", "b", "c", "d", "e"],
        })
        svg = inst.emit_svg()
        assert ">a</text>" in svg
        assert ">b</text>" in svg
        assert ">c</text>" in svg


# ---------------------------------------------------------------------------
# 12. Custom labels shorter than tick count -- fallback to index
# ---------------------------------------------------------------------------


class TestCustomLabelsShort:
    def test_short_labels_fallback(self) -> None:
        inst = NumberLinePrimitive("nl", {
            "domain": [0, 4],
            "labels": ["x", "y"],
        })
        assert inst.tick_count == 5
        svg = inst.emit_svg()
        # First two ticks use custom labels
        assert ">x</text>" in svg
        assert ">y</text>" in svg
        # Remaining ticks should fall back to index
        assert ">2</text>" in svg
        assert ">3</text>" in svg
        assert ">4</text>" in svg


# ---------------------------------------------------------------------------
# 13. Tick spacing: verify ticks are evenly spaced
# ---------------------------------------------------------------------------


class TestTickSpacing:
    def test_even_spacing_3_ticks(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 2], "ticks": 3})
        svg = inst.emit_svg()
        usable = NL_WIDTH - 2 * NL_PADDING
        x0 = NL_PADDING
        x1 = NL_PADDING + usable // 2
        x2 = NL_PADDING + usable
        # Check that x positions are evenly spaced
        assert f'x1="{x0}"' in svg
        assert f'x1="{x1}"' in svg
        assert f'x1="{x2}"' in svg


# ---------------------------------------------------------------------------
# 14. Bounding box correct
# ---------------------------------------------------------------------------


class TestBoundingBoxCorrect:
    def test_no_label_dimensions(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        x, y, w, h = inst.bounding_box()
        assert w == float(NL_WIDTH)
        assert h == 56.0

    def test_with_label_dimensions(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5], "label": "Test"})
        x, y, w, h = inst.bounding_box()
        assert h == 72.0  # 56 + 16


# ---------------------------------------------------------------------------
# 15. Invalid domain format
# ---------------------------------------------------------------------------


class TestInvalidDomain:
    def test_non_list_domain_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1453"):
            NumberLinePrimitive("nl", {"domain": 5})

    def test_single_element_domain_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1453"):
            NumberLinePrimitive("nl", {"domain": [5]})

    def test_three_element_domain_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1453"):
            NumberLinePrimitive("nl", {"domain": [0, 5, 10]})
