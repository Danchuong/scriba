"""Unit tests for the Deque primitive (Queue generalised to both ends).

Deque is a subclass of :class:`Queue` registered under its own type name.
These tests pin:

* the double-ended op semantics (``push_front``/``push_back``/``pop_front``/
  ``pop_back``) and the FIFO aliases (``enqueue``/``dequeue``);
* count-based pop coercion (``true``/bare → 1, ``0``/``false`` → no-op);
* *loud* overflow (E1442) and underflow (E1443), unlike Queue's silent no-ops;
* the Queue-side guard that rejects deque-only verbs (E1444);
* **Queue byte-identity** — a plain Queue still emits exactly as before, with
  ``front``/``rear`` labels and no Deque markers;
* selectors (``cell[i]``/``front``/``back``/``all``) and the positional,
  front-relative ``cell[i]`` semantics (differs from Array slot-identity).
"""

from __future__ import annotations

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.primitives import get_primitive_registry
from scriba.animation.primitives.queue import Deque, Queue

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Registration & construction
# ---------------------------------------------------------------------------


class TestRegistrationAndConstruction:
    def test_registered_under_deque_name(self) -> None:
        assert get_primitive_registry().get("Deque") is Deque

    def test_is_queue_subclass(self) -> None:
        # The generalisation relationship: a Deque IS-A Queue (superset of ops).
        assert issubclass(Deque, Queue)

    def test_primitive_type_is_deque(self) -> None:
        assert Deque("d", {"capacity": 4}).primitive_type == "deque"

    def test_initial_items_from_data(self) -> None:
        d = Deque("d", {"capacity": 6, "data": [3, 1]})
        assert d.items == [3, 1]

    def test_empty_data_is_empty_deque(self) -> None:
        assert Deque("d", {"capacity": 4}).items == []

    def test_initial_data_truncated_to_capacity(self) -> None:
        # Matches Queue's silent initial-fill truncation (not a loud overflow).
        d = Deque("d", {"capacity": 2, "data": [1, 2, 3, 4]})
        assert d.items == [1, 2]

    def test_label_parameter(self) -> None:
        assert Deque("d", {"capacity": 3, "label": "My Deque"}).label == "My Deque"

    def test_capacity_validation_inherited(self) -> None:
        # E1440 (Queue capacity) still applies to a Deque.
        with pytest.raises(AnimationError) as exc:
            Deque("d", {"capacity": 0})
        assert exc.value.code == "E1440"


# ---------------------------------------------------------------------------
# Four-op semantics
# ---------------------------------------------------------------------------


class TestFourOps:
    def test_push_back(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2]})
        d.apply_command({"push_back": 3})
        assert d.items == [1, 2, 3]

    def test_push_front(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2]})
        d.apply_command({"push_front": 0})
        assert d.items == [0, 1, 2]

    def test_pop_back(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2, 3]})
        d.apply_command({"pop_back": 1})
        assert d.items == [1, 2]

    def test_pop_front(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2, 3]})
        d.apply_command({"pop_front": 1})
        assert d.items == [2, 3]

    def test_task_example_round_trip(self) -> None:
        """The exact sequence from the task brief round-trips to [3, 1]."""
        d = Deque("d", {"capacity": 6, "data": [3, 1]})
        d.apply_command({"push_back": 4})
        assert d.items == [3, 1, 4]
        d.apply_command({"push_front": 9})
        assert d.items == [9, 3, 1, 4]
        d.apply_command({"pop_back": 1})
        assert d.items == [9, 3, 1]
        d.apply_command({"pop_front": 1})
        assert d.items == [3, 1]

    def test_pushes_run_before_pops_in_one_command(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [2]})
        d.apply_command({"push_front": 1, "push_back": 3, "pop_front": 1})
        # push_front=1 -> [1,2]; push_back=3 -> [1,2,3]; pop_front -> [2,3]
        assert d.items == [2, 3]


# ---------------------------------------------------------------------------
# FIFO aliases: enqueue -> push_back, dequeue -> pop_front
# ---------------------------------------------------------------------------


class TestFifoAliases:
    def test_enqueue_aliases_push_back(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1]})
        d.apply_command({"enqueue": 2})
        assert d.items == [1, 2]

    def test_dequeue_aliases_pop_front(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2]})
        d.apply_command({"dequeue": True})
        assert d.items == [2]

    def test_deque_is_queue_superset(self) -> None:
        # A pure FIFO workload authored with enqueue/dequeue behaves identically
        # on a Deque as it would on a Queue.
        d = Deque("d", {"capacity": 4})
        d.apply_command({"enqueue": "A"})
        d.apply_command({"enqueue": "B"})
        d.apply_command({"dequeue": True})
        assert d.items == ["B"]


# ---------------------------------------------------------------------------
# Count-based pop coercion (mirrors Stack's pop; True -> 1)
# ---------------------------------------------------------------------------


class TestPopCountCoercion:
    def test_pop_true_removes_one(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2, 3]})
        d.apply_command({"pop_back": True})
        assert d.items == [1, 2]

    def test_pop_int_count(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2, 3, 4]})
        d.apply_command({"pop_front": 2})
        assert d.items == [3, 4]

    @pytest.mark.parametrize("noop_value", [0, False, "false", "", None])
    def test_pop_zero_or_falsy_is_noop(self, noop_value: object) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2, 3]})
        d.apply_command({"pop_back": noop_value})
        assert d.items == [1, 2, 3]

    def test_pop_string_true_removes_one(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2]})
        d.apply_command({"pop_front": "true"})
        assert d.items == [2]


# ---------------------------------------------------------------------------
# Loud overflow / underflow (E1442 / E1443)
# ---------------------------------------------------------------------------


class TestOverflowUnderflow:
    def test_push_back_overflow_raises_e1442(self) -> None:
        d = Deque("d", {"capacity": 2, "data": [1, 2]})
        with pytest.raises(AnimationError) as exc:
            d.apply_command({"push_back": 3})
        assert exc.value.code == "E1442"

    def test_push_front_overflow_raises_e1442(self) -> None:
        d = Deque("d", {"capacity": 2, "data": [1, 2]})
        with pytest.raises(AnimationError) as exc:
            d.apply_command({"push_front": 0})
        assert exc.value.code == "E1442"

    def test_pop_front_empty_raises_e1443(self) -> None:
        d = Deque("d", {"capacity": 3})
        with pytest.raises(AnimationError) as exc:
            d.apply_command({"pop_front": 1})
        assert exc.value.code == "E1443"

    def test_pop_back_empty_raises_e1443(self) -> None:
        d = Deque("d", {"capacity": 3})
        with pytest.raises(AnimationError) as exc:
            d.apply_command({"pop_back": True})
        assert exc.value.code == "E1443"

    def test_pop_more_than_present_raises_e1443(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2]})
        with pytest.raises(AnimationError) as exc:
            d.apply_command({"pop_back": 3})
        assert exc.value.code == "E1443"

    def test_overflow_leaves_state_unchanged(self) -> None:
        d = Deque("d", {"capacity": 2, "data": [1, 2]})
        with pytest.raises(AnimationError):
            d.apply_command({"push_back": 3})
        assert d.items == [1, 2]


# ---------------------------------------------------------------------------
# Queue-mode rejects deque-only verbs (E1444)
# ---------------------------------------------------------------------------


class TestQueueRejectsDequeVerbs:
    @pytest.mark.parametrize(
        "verb", ["push_front", "push_back", "pop_front", "pop_back"]
    )
    def test_queue_rejects_deque_verb(self, verb: str) -> None:
        q = Queue("q", {"capacity": 4, "data": [1]})
        with pytest.raises(AnimationError) as exc:
            q.apply_command({verb: 9})
        assert exc.value.code == "E1444"

    def test_queue_enqueue_dequeue_still_work(self) -> None:
        # The guard must not disturb the legitimate FIFO verbs.
        q = Queue("q", {"capacity": 4})
        q.apply_command({"enqueue": 7})
        assert q.cells[0] == 7
        assert q.rear_idx == 1
        q.apply_command({"dequeue": True})
        assert q.front_idx == 1


# ---------------------------------------------------------------------------
# Queue byte-identity regression
# ---------------------------------------------------------------------------


class TestQueueByteIdentity:
    def _queue_emit(self) -> str:
        q = Queue("q", {"capacity": 4, "data": [10, 20]})
        q.apply_command({"enqueue": 30})
        q.apply_command({"dequeue": True})
        return q.emit_svg()

    def test_queue_emit_keeps_queue_primitive_marker(self) -> None:
        assert 'data-primitive="queue"' in self._queue_emit()

    def test_queue_emit_keeps_front_and_rear_labels(self) -> None:
        svg = self._queue_emit()
        assert 'data-target="q.front"' in svg
        assert 'data-target="q.rear"' in svg

    def test_queue_emit_has_no_deque_markers(self) -> None:
        svg = self._queue_emit()
        assert 'data-primitive="deque"' not in svg
        assert 'data-target="q.back"' not in svg
        # Queue draws every slot solid — no dashed reserved-capacity cells.
        assert "stroke-dasharray" not in svg

    def test_queue_emit_deterministic(self) -> None:
        # Same construction + ops must produce byte-identical SVG.
        assert self._queue_emit() == self._queue_emit()


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestSelectors:
    def test_addressable_parts(self) -> None:
        d = Deque("d", {"capacity": 3})
        assert d.addressable_parts() == [
            "cell[0]",
            "cell[1]",
            "cell[2]",
            "front",
            "back",
            "all",
        ]

    def test_addressable_parts_has_no_rear(self) -> None:
        # Deque's back pointer is "back", not Queue's "rear".
        assert "rear" not in Deque("d", {"capacity": 3}).addressable_parts()

    def test_validate_front_back_all(self) -> None:
        d = Deque("d", {"capacity": 3})
        assert d.validate_selector("front") is True
        assert d.validate_selector("back") is True
        assert d.validate_selector("all") is True

    def test_validate_rear_is_rejected(self) -> None:
        assert Deque("d", {"capacity": 3}).validate_selector("rear") is False

    def test_validate_cell_bounds(self) -> None:
        d = Deque("d", {"capacity": 3})
        assert d.validate_selector("cell[0]") is True
        assert d.validate_selector("cell[2]") is True
        assert d.validate_selector("cell[3]") is False


# ---------------------------------------------------------------------------
# Positional (front-relative) cell semantics — differs from Array (R-42)
# ---------------------------------------------------------------------------


class TestPositionalCellSemantics:
    def test_cell_index_is_front_relative_after_pop_front(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2, 3]})
        assert d.items[0] == 1
        d.apply_command({"pop_front": 1})
        # cell[0] now addresses a DIFFERENT element — the front shifted.
        assert d.items[0] == 2

    def test_cell_index_is_front_relative_after_push_front(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2]})
        d.apply_command({"push_front": 9})
        # Every existing element shifted one position to the right.
        assert d.items[0] == 9
        assert d.items[1] == 1

    def test_set_value_on_occupied_cell(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1, 2, 3]})
        d.set_value("cell[1]", "42")
        assert d.items[1] == "42"

    def test_set_value_on_empty_cell_is_noop(self) -> None:
        d = Deque("d", {"capacity": 5, "data": [1]})
        d.set_value("cell[3]", "X")
        assert d.items == [1]


# ---------------------------------------------------------------------------
# SVG emit
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_deque_primitive_marker(self) -> None:
        assert 'data-primitive="deque"' in Deque("d", {"capacity": 3}).emit_svg()

    def test_front_and_back_targets_rendered(self) -> None:
        svg = Deque("d", {"capacity": 3, "data": [1]}).emit_svg()
        assert 'data-target="d.front"' in svg
        assert 'data-target="d.back"' in svg

    def test_no_rear_label(self) -> None:
        svg = Deque("d", {"capacity": 3, "data": [1]}).emit_svg()
        assert 'data-target="d.rear"' not in svg

    def test_empty_slots_are_dashed(self) -> None:
        # capacity 4, only 1 occupied -> 3 dashed reserved cells.
        svg = Deque("d", {"capacity": 4, "data": [1]}).emit_svg()
        assert svg.count("stroke-dasharray") == 3

    def test_occupied_cells_not_dashed(self) -> None:
        svg = Deque("d", {"capacity": 3, "data": [1, 2, 3]}).emit_svg()
        assert "stroke-dasharray" not in svg

    def test_cell_targets_rendered(self) -> None:
        svg = Deque("d", {"capacity": 3, "data": [1, 2]}).emit_svg()
        assert 'data-target="d.cell[0]"' in svg
        assert 'data-target="d.cell[1]"' in svg

    def test_all_state_propagates_to_cells(self) -> None:
        d = Deque("d", {"capacity": 3, "data": [1, 2]})
        d.set_state("all", "done")
        svg = d.emit_svg()
        assert svg.count("scriba-state-done") >= 2

    def test_bounding_box_positive(self) -> None:
        bbox = Deque("d", {"capacity": 3, "data": [1]}).bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0
