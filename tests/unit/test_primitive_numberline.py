"""Tests for the NumberLine primitive.

Covers declaration, selectors, SVG output, bounding box, and error handling.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.numberline import NumberLineInstance, NumberLinePrimitive
from scriba.core.errors import ValidationError


@pytest.fixture()
def factory() -> NumberLinePrimitive:
    return NumberLinePrimitive()


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_domain_0_5_creates_6_ticks(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5]})
        assert isinstance(inst, NumberLineInstance)
        assert inst.tick_count == 6
        assert inst.shape_name == "nl"

    def test_domain_0_10_ticks_5(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 10], "ticks": 5})
        assert inst.tick_count == 5

    def test_custom_labels_list(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 3], "labels": ["a", "b", "c", "d"]})
        assert inst.tick_labels == ["a", "b", "c", "d"]

    def test_custom_labels_string(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5], "labels": "0..5"})
        assert inst.tick_labels == ["0", "1", "2", "3", "4", "5"]

    def test_label_caption(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5], "label": "My Axis"})
        assert inst.label == "My Axis"

    def test_missing_domain_raises_e1103(self, factory: NumberLinePrimitive) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            factory.declare("nl", {})

    def test_float_domain_defaults_to_11_ticks(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0.0, 1.5]})
        assert inst.tick_count == 11


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_tick_valid(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5]})
        assert inst.validate_selector("nl.tick[0]") is True
        assert inst.validate_selector("nl.tick[5]") is True

    def test_tick_out_of_range(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5]})
        assert inst.validate_selector("nl.tick[6]") is False

    def test_range_valid(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 10], "ticks": 11})
        assert inst.validate_selector("nl.range[1:3]") is True

    def test_range_invalid(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5]})
        assert inst.validate_selector("nl.range[5:3]") is False
        assert inst.validate_selector("nl.range[0:6]") is False

    def test_axis_valid(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5]})
        assert inst.validate_selector("nl.axis") is True

    def test_all_valid(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5]})
        assert inst.validate_selector("nl.all") is True

    def test_wrong_name(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5]})
        assert inst.validate_selector("other.tick[0]") is False

    def test_garbage_selector(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5]})
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 3]})
        svg = inst.emit_svg({})

        assert 'data-primitive="numberline"' in svg
        assert 'data-shape="nl"' in svg
        assert 'data-target="nl.axis"' in svg
        assert 'data-target="nl.tick[0]"' in svg
        assert 'data-target="nl.tick[3]"' in svg

    def test_tick_labels_in_output(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 2]})
        svg = inst.emit_svg({})
        assert ">0</text>" in svg
        assert ">1</text>" in svg
        assert ">2</text>" in svg

    def test_default_idle_class(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 1]})
        svg = inst.emit_svg({})
        assert "scriba-state-idle" in svg

    def test_state_recolor(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 3]})
        svg = inst.emit_svg({"nl.tick[1]": {"state": "current"}})
        assert "scriba-state-current" in svg

    def test_axis_uses_idle_stroke(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 3]})
        svg = inst.emit_svg({})
        assert 'stroke="#d0d7de"' in svg

    def test_caption_rendered(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5], "label": "Scale"})
        svg = inst.emit_svg({})
        assert "scriba-primitive-label" in svg
        assert "Scale" in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_dimensions_no_label(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5]})
        x, y, w, h = inst.bounding_box()
        assert x == 0.0
        assert y == 0.0
        assert w == 400.0
        assert h == 56.0

    def test_dimensions_with_label(self, factory: NumberLinePrimitive) -> None:
        inst = factory.declare("nl", {"domain": [0, 5], "label": "Axis"})
        x, y, w, h = inst.bounding_box()
        assert w == 400.0
        assert h == 72.0  # 56 + 16 for caption
