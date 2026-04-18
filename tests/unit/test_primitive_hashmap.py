"""Tests for the HashMap primitive.

Covers declaration, capacity validation, selectors, addressable parts,
state management, SVG output, and value operations.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.hashmap import HashMap
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_default_construction(self) -> None:
        inst = HashMap("hm", {"capacity": 4})
        assert inst.name == "hm"
        assert inst.capacity == 4
        assert inst.primitive_type == "hashmap"

    def test_capacity_as_string(self) -> None:
        inst = HashMap("hm", {"capacity": "3"})
        assert inst.capacity == 3

    def test_label_parameter(self) -> None:
        inst = HashMap("hm", {"capacity": 2, "label": "Hash Table"})
        assert inst.label == "Hash Table"

    def test_missing_capacity_raises_error(self) -> None:
        # v0.5.1: E1450 (HashMap missing capacity)
        with pytest.raises(ValidationError, match="E1450"):
            HashMap("hm", {})

    def test_zero_capacity_raises_error(self) -> None:
        # v0.5.1: E1451 (HashMap capacity out of range)
        with pytest.raises(ValidationError, match="E1451"):
            HashMap("hm", {"capacity": 0})

    def test_negative_capacity_raises_error(self) -> None:
        with pytest.raises(ValidationError, match="E1451"):
            HashMap("hm", {"capacity": -1})


# ---------------------------------------------------------------------------
# Addressable parts
# ---------------------------------------------------------------------------


class TestAddressableParts:
    def test_returns_all_buckets_and_all(self) -> None:
        inst = HashMap("hm", {"capacity": 3})
        parts = inst.addressable_parts()
        assert parts == ["bucket[0]", "bucket[1]", "bucket[2]", "all"]

    def test_single_bucket(self) -> None:
        inst = HashMap("hm", {"capacity": 1})
        assert inst.addressable_parts() == ["bucket[0]", "all"]


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_bucket_valid(self) -> None:
        inst = HashMap("hm", {"capacity": 4})
        assert inst.validate_selector("bucket[0]") is True
        assert inst.validate_selector("bucket[3]") is True

    def test_bucket_out_of_range(self) -> None:
        inst = HashMap("hm", {"capacity": 4})
        assert inst.validate_selector("bucket[4]") is False

    def test_all_valid(self) -> None:
        inst = HashMap("hm", {"capacity": 2})
        assert inst.validate_selector("all") is True

    def test_unknown_selector(self) -> None:
        inst = HashMap("hm", {"capacity": 2})
        assert inst.validate_selector("cell[0]") is False
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class TestState:
    def test_set_state_on_bucket(self) -> None:
        inst = HashMap("hm", {"capacity": 3})
        inst.set_state("bucket[0]", "current")
        assert inst.get_state("bucket[0]") == "current"
        assert inst.get_state("bucket[1]") == "idle"

    def test_set_state_all(self) -> None:
        inst = HashMap("hm", {"capacity": 2})
        inst.set_state("all", "done")
        assert inst.get_state("all") == "done"


# ---------------------------------------------------------------------------
# Value operations
# ---------------------------------------------------------------------------


class TestValues:
    def test_set_value(self) -> None:
        inst = HashMap("hm", {"capacity": 3})
        inst.set_value("bucket[0]", "cat:3  car:7")
        assert inst._bucket_values[0] == "cat:3  car:7"

    def test_set_value_out_of_range_ignored(self) -> None:
        inst = HashMap("hm", {"capacity": 2})
        inst.set_value("bucket[5]", "nope")
        assert all(v == "" for v in inst._bucket_values.values())

    def test_apply_command_sets_value(self) -> None:
        inst = HashMap("hm", {"capacity": 3})
        inst.apply_command({"value": "dog:1"}, target_suffix="bucket[1]")
        assert inst._bucket_values[1] == "dog:1"


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        inst = HashMap("hm", {"capacity": 2})
        svg = inst.emit_svg()
        assert 'data-primitive="hashmap"' in svg
        assert 'data-shape="hm"' in svg
        assert 'data-target="hm.bucket[0]"' in svg
        assert 'data-target="hm.bucket[1]"' in svg

    def test_default_idle_class(self) -> None:
        inst = HashMap("hm", {"capacity": 1})
        svg = inst.emit_svg()
        assert "scriba-state-idle" in svg

    def test_state_applied_in_svg(self) -> None:
        inst = HashMap("hm", {"capacity": 2})
        inst.set_state("bucket[0]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_label_rendered(self) -> None:
        inst = HashMap("hm", {"capacity": 2, "label": "My Map"})
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg

    def test_bucket_value_appears_in_svg(self) -> None:
        inst = HashMap("hm", {"capacity": 2})
        inst.set_value("bucket[0]", "key:val")
        svg = inst.emit_svg()
        assert "key:val" in svg


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_capacity_one_works(self) -> None:
        inst = HashMap("hm", {"capacity": 1})
        assert inst.capacity == 1
        assert inst.addressable_parts() == ["bucket[0]", "all"]
        svg = inst.emit_svg()
        assert 'data-primitive="hashmap"' in svg

    def test_bounding_box_positive(self) -> None:
        inst = HashMap("hm", {"capacity": 3})
        bbox = inst.bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0

    def test_all_state_propagates_to_buckets(self) -> None:
        inst = HashMap("hm", {"capacity": 2})
        inst.set_state("all", "done")
        svg = inst.emit_svg()
        assert svg.count("scriba-state-done") >= 2
