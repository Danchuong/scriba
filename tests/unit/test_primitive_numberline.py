"""Tests for the NumberLine primitive.

Covers declaration, selectors, SVG output, bounding box, and error handling.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_domain_0_5_creates_6_ticks(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        assert isinstance(inst, NumberLinePrimitive)
        assert inst.tick_count == 6
        assert inst.name == "nl"

    def test_domain_0_10_ticks_5(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 5})
        assert inst.tick_count == 5

    def test_custom_labels_list(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 3], "labels": ["a", "b", "c", "d"]})
        assert inst.tick_labels == ["a", "b", "c", "d"]

    def test_custom_labels_string(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5], "labels": "0..5"})
        assert inst.tick_labels == ["0", "1", "2", "3", "4", "5"]

    def test_label_caption(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5], "label": "My Axis"})
        assert inst.label == "My Axis"

    def test_missing_domain_raises_e1452(self) -> None:
        # v0.5.1: E1452 (NumberLine missing domain)
        with pytest.raises(ValidationError, match="E1452"):
            NumberLinePrimitive("nl", {})

    def test_float_domain_defaults_to_11_ticks(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0.0, 1.5]})
        assert inst.tick_count == 11

    def test_ticks_zero_raises_e1103(self) -> None:
        """ticks=0 is a validation error, not a degenerate primitive."""
        with pytest.raises(ValidationError, match="E1103"):
            NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 0})

    def test_ticks_negative_raises_e1103(self) -> None:
        """Negative ticks are rejected as out-of-range."""
        with pytest.raises(ValidationError, match="E1103"):
            NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": -5})

    def test_ticks_one_is_boundary_accepted(self) -> None:
        """ticks=1 is the minimum accepted value (single-point number line)."""
        inst = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 1})
        assert inst.tick_count == 1


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_tick_valid(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        assert inst.validate_selector("tick[0]") is True
        assert inst.validate_selector("tick[5]") is True

    def test_tick_out_of_range(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        assert inst.validate_selector("tick[6]") is False

    def test_range_valid(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 11})
        assert inst.validate_selector("range[1:3]") is True

    def test_range_invalid(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        assert inst.validate_selector("range[5:3]") is False
        assert inst.validate_selector("range[0:6]") is False

    def test_axis_valid(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        assert inst.validate_selector("axis") is True

    def test_all_valid(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        assert inst.validate_selector("all") is True

    def test_garbage_selector(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 3]})
        svg = inst.emit_svg()

        assert 'data-primitive="numberline"' in svg
        assert 'data-shape="nl"' in svg
        assert 'data-target="nl.axis"' in svg
        assert 'data-target="nl.tick[0]"' in svg
        assert 'data-target="nl.tick[3]"' in svg

    def test_tick_labels_in_output(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 2]})
        svg = inst.emit_svg()
        assert ">0</text>" in svg
        assert ">1</text>" in svg
        assert ">2</text>" in svg

    def test_default_idle_class(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 1]})
        svg = inst.emit_svg()
        assert "scriba-state-idle" in svg

    def test_state_recolor(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 3]})
        inst.set_state("tick[1]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_axis_uses_idle_stroke(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 3]})
        svg = inst.emit_svg()
        # β slate-6 idle border
        assert 'stroke="#dfe3e6"' in svg

    def test_caption_rendered(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5], "label": "Scale"})
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg
        assert "Scale" in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_dimensions_no_label(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5]})
        x, y, w, h = inst.bounding_box()
        assert x == 0.0
        assert y == 0.0
        assert w == 400.0
        assert h == 56.0

    def test_dimensions_with_label(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 5], "label": "Axis"})
        x, y, w, h = inst.bounding_box()
        assert w == 400.0
        assert h == 69.0  # 56 + 13 (one wrapped caption line, font 11 + 2)


# ---------------------------------------------------------------------------
# Layer B/C — position pills + 1D range annotations
#
# Regression: numberline only rendered `arrow_from` annotations; a
# `position=above/below` pill (and any `range[lo:hi]` target) was silently
# dropped even though bounding_box() reserved space for it. Route non-arrow
# annotations through the shared annotation engine so pills and ranges render.
# ---------------------------------------------------------------------------


class TestPositionAndRangeAnnotation:
    def test_position_pill_renders(self) -> None:
        nl = NumberLinePrimitive("nl", {"domain": [0, 15], "ticks": 16})
        nl.set_annotations(
            [{"target": "nl.tick[10]", "label": "Found!", "position": "above"}]
        )
        svg = nl.emit_svg()
        assert "Found!" in svg  # was silently dropped
        assert "scriba-annotation" in svg  # rendered as a pill

    def test_range_anchor_not_none(self) -> None:
        nl = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 11})
        assert nl.resolve_annotation_point("nl.range[1:3]") is not None

    def test_range_anchor_is_span_midpoint(self) -> None:
        nl = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 11})
        pt = nl.resolve_annotation_point("nl.range[1:3]")
        ticks = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 11})
        mid = (ticks._tick_x(1) + ticks._tick_x(3)) / 2.0
        assert pt is not None and abs(pt[0] - mid) < 0.5

    def test_range_position_pill_renders(self) -> None:
        nl = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 11})
        nl.set_annotations(
            [{"target": "nl.range[1:3]", "label": "RNG", "position": "above"}]
        )
        assert "RNG" in nl.emit_svg()

    def test_arrow_annotation_still_renders(self) -> None:
        """Regression: existing arrow annotations keep working."""
        nl = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 11})
        nl.set_annotations(
            [{"target": "nl.tick[3]", "arrow_from": "nl.tick[1]", "label": "mv"}]
        )
        assert "mv" in nl.emit_svg()


# ---------------------------------------------------------------------------
# Layer C — position=below pill clears the tick labels (caption-below-lane)
# ---------------------------------------------------------------------------


class TestBelowPillLane:
    def test_below_pill_clears_tick_labels(self) -> None:
        """A position=below pill sits below the tick labels (NL_LABEL_Y), not
        in the label band where it used to land."""
        import re
        from scriba.animation.primitives.numberline import NL_LABEL_Y

        nl = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 11})
        nl.set_annotations(
            [{"target": "nl.tick[5]", "label": "BELOW", "position": "below"}]
        )
        svg = nl.emit_svg()
        m = re.search(
            r'scriba-annotation.*?<rect x="[\d.]+" y="([\d.]+)"', svg, re.S
        )
        assert m is not None, "below pill not rendered"
        assert float(m.group(1)) > NL_LABEL_Y

    def test_below_pill_and_caption_coexist(self) -> None:
        """With both a below pill and a caption, both render and the caption
        sits below the below-pill lane."""
        nl = NumberLinePrimitive("nl", {"domain": [0, 5], "label": "Scale"})
        nl.set_annotations(
            [{"target": "nl.tick[2]", "label": "HERE", "position": "below"}]
        )
        svg = nl.emit_svg()
        assert "HERE" in svg and "Scale" in svg

    def test_caption_only_bbox_unchanged(self) -> None:
        """No below pills -> lane is 0 -> caption stays at NL_HEIGHT (byte-stable)."""
        nl = NumberLinePrimitive("nl", {"domain": [0, 5], "label": "Axis"})
        assert nl.bounding_box().height == 69.0  # 56 + 13, unchanged
