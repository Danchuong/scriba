"""Tests for the Queue primitive.

Covers declaration, selectors, addressable parts, state management,
SVG output, enqueue/dequeue operations, and front/rear pointers.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.queue import Queue


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_default_construction(self) -> None:
        inst = Queue("q", {"capacity": 4, "data": [10, 20]})
        assert inst.name == "q"
        assert inst.capacity == 4
        assert inst.cells[0] == 10
        assert inst.cells[1] == 20
        assert inst.cells[2] == ""
        assert inst.front_idx == 0
        assert inst.rear_idx == 2
        assert inst.primitive_type == "queue"

    def test_default_capacity(self) -> None:
        inst = Queue("q", {})
        assert inst.capacity == 8

    def test_label_parameter(self) -> None:
        inst = Queue("q", {"capacity": 4, "label": "FIFO Queue"})
        assert inst.label_text == "FIFO Queue"

    def test_empty_construction(self) -> None:
        inst = Queue("q", {"capacity": 3})
        assert inst.front_idx == 0
        assert inst.rear_idx == 0
        assert all(c == "" for c in inst.cells)


# ---------------------------------------------------------------------------
# Addressable parts
# ---------------------------------------------------------------------------


class TestAddressableParts:
    def test_returns_cells_front_rear_all(self) -> None:
        inst = Queue("q", {"capacity": 3})
        parts = inst.addressable_parts()
        assert parts == ["cell[0]", "cell[1]", "cell[2]", "front", "rear", "all"]


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_cell_valid(self) -> None:
        inst = Queue("q", {"capacity": 4})
        assert inst.validate_selector("cell[0]") is True
        assert inst.validate_selector("cell[3]") is True

    def test_cell_out_of_range(self) -> None:
        inst = Queue("q", {"capacity": 4})
        assert inst.validate_selector("cell[4]") is False

    def test_front_valid(self) -> None:
        inst = Queue("q", {"capacity": 2})
        assert inst.validate_selector("front") is True

    def test_rear_valid(self) -> None:
        inst = Queue("q", {"capacity": 2})
        assert inst.validate_selector("rear") is True

    def test_all_valid(self) -> None:
        inst = Queue("q", {"capacity": 2})
        assert inst.validate_selector("all") is True

    def test_unknown_selector(self) -> None:
        inst = Queue("q", {"capacity": 2})
        assert inst.validate_selector("bucket[0]") is False
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class TestState:
    def test_set_state_on_cell(self) -> None:
        inst = Queue("q", {"capacity": 3})
        inst.set_state("cell[0]", "current")
        assert inst.get_state("cell[0]") == "current"
        assert inst.get_state("cell[1]") == "idle"

    def test_set_state_on_front(self) -> None:
        inst = Queue("q", {"capacity": 2})
        inst.set_state("front", "done")
        assert inst.get_state("front") == "done"

    def test_set_state_on_rear(self) -> None:
        inst = Queue("q", {"capacity": 2})
        inst.set_state("rear", "done")
        assert inst.get_state("rear") == "done"


# ---------------------------------------------------------------------------
# Enqueue / Dequeue operations
# ---------------------------------------------------------------------------


class TestEnqueueDequeue:
    def test_enqueue(self) -> None:
        inst = Queue("q", {"capacity": 4})
        inst.apply_command({"enqueue": "A"})
        assert inst.cells[0] == "A"
        assert inst.rear_idx == 1

    def test_enqueue_multiple(self) -> None:
        inst = Queue("q", {"capacity": 4})
        inst.apply_command({"enqueue": "A"})
        inst.apply_command({"enqueue": "B"})
        assert inst.cells[0] == "A"
        assert inst.cells[1] == "B"
        assert inst.rear_idx == 2

    def test_enqueue_at_capacity_ignored(self) -> None:
        inst = Queue("q", {"capacity": 2, "data": [1, 2]})
        inst.apply_command({"enqueue": "X"})
        assert inst.rear_idx == 2  # unchanged

    def test_dequeue(self) -> None:
        inst = Queue("q", {"capacity": 4, "data": [10, 20]})
        inst.apply_command({"dequeue": True})
        assert inst.cells[0] == ""
        assert inst.front_idx == 1

    def test_dequeue_empty_ignored(self) -> None:
        inst = Queue("q", {"capacity": 4})
        inst.apply_command({"dequeue": True})
        assert inst.front_idx == 0  # unchanged

    def test_enqueue_then_dequeue(self) -> None:
        inst = Queue("q", {"capacity": 3})
        inst.apply_command({"enqueue": "A"})
        inst.apply_command({"enqueue": "B"})
        inst.apply_command({"dequeue": True})
        assert inst.front_idx == 1
        assert inst.rear_idx == 2
        assert inst.cells[1] == "B"

    def test_set_value(self) -> None:
        inst = Queue("q", {"capacity": 3})
        inst.set_value("cell[1]", "42")
        assert inst.cells[1] == "42"


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        inst = Queue("q", {"capacity": 3, "data": [10, 20]})
        svg = inst.emit_svg()
        assert 'data-primitive="queue"' in svg
        assert 'data-shape="q"' in svg
        assert 'data-target="q.cell[0]"' in svg
        assert 'data-target="q.cell[1]"' in svg

    def test_front_rear_pointers_rendered(self) -> None:
        inst = Queue("q", {"capacity": 3, "data": [10]})
        svg = inst.emit_svg()
        assert 'data-target="q.front"' in svg
        assert 'data-target="q.rear"' in svg

    def test_default_idle_class(self) -> None:
        inst = Queue("q", {"capacity": 2})
        svg = inst.emit_svg()
        assert "scriba-state-idle" in svg

    def test_state_applied_in_svg(self) -> None:
        inst = Queue("q", {"capacity": 2})
        inst.set_state("cell[0]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_label_rendered(self) -> None:
        inst = Queue("q", {"capacity": 2, "label": "My Queue"})
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg

    def test_index_labels_rendered(self) -> None:
        inst = Queue("q", {"capacity": 3})
        svg = inst.emit_svg()
        assert "scriba-index-label" in svg


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_bounding_box_positive(self) -> None:
        inst = Queue("q", {"capacity": 3})
        bbox = inst.bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0

    def test_front_rear_overlap_on_single_element(self) -> None:
        """When front and rear point to the same cell, both should render."""
        inst = Queue("q", {"capacity": 4, "data": [42]})
        svg = inst.emit_svg()
        assert "front" in svg
        assert "rear" in svg

    def test_all_state_propagates_to_cells(self) -> None:
        inst = Queue("q", {"capacity": 2})
        inst.set_state("all", "done")
        svg = inst.emit_svg()
        assert svg.count("scriba-state-done") >= 2
