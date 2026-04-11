"""Regression tests for Queue.apply_command dequeue flag handling.

Previously ``dequeue=false`` still triggered a dequeue because the code
only checked ``dequeue_val is not None`` — turning the explicit opt-out
into a silent footgun.  See Wave 5.2 emitter/primitive quick wins.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.queue import Queue


def _make_queue() -> Queue:
    return Queue("q", {"capacity": 4, "data": [10, 20, 30]})


class TestDequeueFlagTruthiness:
    """``dequeue`` must only pop when the flag is explicitly truthy."""

    def test_dequeue_false_python_bool_does_not_pop(self) -> None:
        q = _make_queue()
        q.apply_command({"dequeue": False})
        assert q.front_idx == 0
        assert q.cells[0] == 10  # front cell untouched

    def test_dequeue_false_string_does_not_pop(self) -> None:
        q = _make_queue()
        q.apply_command({"dequeue": "false"})
        assert q.front_idx == 0
        assert q.cells[0] == 10

    def test_dequeue_zero_does_not_pop(self) -> None:
        q = _make_queue()
        q.apply_command({"dequeue": 0})
        assert q.front_idx == 0
        assert q.cells[0] == 10

    def test_dequeue_none_does_not_pop(self) -> None:
        q = _make_queue()
        q.apply_command({"dequeue": None})
        assert q.front_idx == 0
        assert q.cells[0] == 10

    def test_dequeue_empty_string_does_not_pop(self) -> None:
        q = _make_queue()
        q.apply_command({"dequeue": ""})
        assert q.front_idx == 0
        assert q.cells[0] == 10

    def test_dequeue_true_python_bool_pops(self) -> None:
        q = _make_queue()
        q.apply_command({"dequeue": True})
        assert q.front_idx == 1
        assert q.cells[0] == ""

    def test_dequeue_true_string_pops(self) -> None:
        q = _make_queue()
        q.apply_command({"dequeue": "true"})
        assert q.front_idx == 1
        assert q.cells[0] == ""

    def test_dequeue_true_case_insensitive(self) -> None:
        q = _make_queue()
        q.apply_command({"dequeue": "TRUE"})
        assert q.front_idx == 1

    @pytest.mark.parametrize(
        "falsy_value",
        [False, "false", "False", "FALSE", 0, None, ""],
    )
    def test_parametrised_falsy_values_all_ignored(
        self, falsy_value: object
    ) -> None:
        q = _make_queue()
        q.apply_command({"dequeue": falsy_value})
        assert q.front_idx == 0, (
            f"dequeue={falsy_value!r} should NOT have popped, but front_idx "
            f"advanced to {q.front_idx}"
        )
