"""Regression tests for three Starlark sandbox security fixes.

C1 — Cumulative budget wired into StarlarkHost.eval()
H2 — Bulk-allocation builtins capped to prevent C-level SIGALRM bypass
M3 — RecursionError no longer leaks starlark_worker.py internal paths
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.starlark_worker import (
    _MAX_LIST_SIZE,
    _safe_bytes,
    _safe_list,
    _safe_set,
    _safe_tuple,
    consume_cumulative_budget,
    format_compute_traceback,
    reset_cumulative_budget,
)
from scriba.core.errors import WorkerError
from scriba.core.workers import SubprocessWorkerPool

_WORKER_ARGV = [sys.executable, "-m", "scriba.animation.starlark_worker"]


def _spawn_worker() -> subprocess.Popen:
    proc = subprocess.Popen(
        _WORKER_ARGV,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=str(__import__("pathlib").Path(__file__).resolve().parents[2]),
    )
    ready = proc.stderr.readline()
    assert "starlark-worker ready" in ready
    return proc


def _send(proc: subprocess.Popen, request: dict) -> dict:
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    assert line, "worker produced no output"
    return json.loads(line)


def _close(proc: subprocess.Popen) -> None:
    try:
        if proc.stdin:
            proc.stdin.close()
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# C1 — Cumulative budget wired into StarlarkHost.eval()
# ---------------------------------------------------------------------------


class TestCumulativeBudgetWiring:
    """C1: StarlarkHost.eval() must reset and consume the cumulative budget."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_cumulative_budget()
        yield
        reset_cumulative_budget()

    def test_host_eval_resets_budget_on_first_call(self):
        """A fresh StarlarkHost resets the module-level counter on first eval."""
        from scriba.animation import starlark_worker as sw

        # Pre-charge the counter so we can detect the reset.
        consume_cumulative_budget(4.9)
        assert sw.get_cumulative_elapsed() == pytest.approx(4.9)

        pool = SubprocessWorkerPool()
        from scriba.animation.starlark_host import StarlarkHost

        host = StarlarkHost(pool)
        try:
            # First eval() must reset the counter first.
            host.eval({}, "x = 1")
            # Counter is now the elapsed time of this single fast call —
            # much less than the pre-charged 4.9 s.
            assert sw.get_cumulative_elapsed() < 4.0
        finally:
            pool.close()

    def test_host_eval_charges_elapsed_after_success(self):
        """Each successful eval() charges its wall-clock time to the budget."""
        from scriba.animation import starlark_worker as sw
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            host.eval({}, "x = 1")
            first_elapsed = sw.get_cumulative_elapsed()
            assert first_elapsed > 0.0

            host.eval({}, "y = 2")
            second_elapsed = sw.get_cumulative_elapsed()
            assert second_elapsed > first_elapsed
        finally:
            pool.close()

    def test_host_eval_raises_worker_error_on_cumulative_overflow(self):
        """After budget exhaustion the next eval() raises WorkerError(E1152)."""
        from scriba.animation import starlark_worker as sw
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            # Make one cheap call to trigger the initial reset.
            host.eval({}, "x = 1")
            # Set the counter well past the limit; the next consume_cumulative_budget
            # call inside eval() will detect the overflow even if elapsed is tiny.
            sw._cumulative_elapsed = sw._CUMULATIVE_BUDGET_SECONDS + 1.0
            # The next eval() must detect the overflow via consume_cumulative_budget.
            with pytest.raises(WorkerError) as exc_info:
                host.eval({}, "y = 2")
            err = exc_info.value
            # WorkerError carries the code as an attribute or in its message.
            assert "E1152" in str(err) or getattr(err, "code", "") == "E1152"
            assert "cumulative" in str(err).lower()
        finally:
            pool.close()

    def test_second_host_instance_resets_budget(self):
        """Each new StarlarkHost resets the budget on its first eval(), so
        budgets from a previous host do not bleed into a new render."""
        from scriba.animation import starlark_worker as sw
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host1 = StarlarkHost(pool)
        try:
            host1.eval({}, "a = 1")
            after_host1 = sw.get_cumulative_elapsed()
            assert after_host1 > 0

            # Second host on same pool — must reset counter.
            host2 = StarlarkHost(pool)
            host2.eval({}, "b = 2")
            after_host2 = sw.get_cumulative_elapsed()
            # After reset, elapsed is only the time of host2's single call.
            assert after_host2 < after_host1 + 0.5  # sanity: not accumulating
        finally:
            pool.close()


# ---------------------------------------------------------------------------
# H2 — Bulk-allocation builtins capped
# ---------------------------------------------------------------------------


class TestSafeListUnit:
    """Unit tests for _safe_list — no subprocess needed."""

    def test_small_list_from_range_ok(self):
        result = _safe_list(range(10))
        assert result == list(range(10))

    def test_empty_list_ok(self):
        assert _safe_list() == []

    def test_list_at_max_size_ok(self):
        result = _safe_list(range(_MAX_LIST_SIZE))
        assert len(result) == _MAX_LIST_SIZE

    def test_list_over_max_size_raises(self):
        with pytest.raises(AnimationError) as exc_info:
            _safe_list(range(_MAX_LIST_SIZE + 1))
        err = exc_info.value
        assert err.code == "E1154"
        assert str(_MAX_LIST_SIZE + 1) in str(err) or "large" in str(err).lower()

    def test_list_repeat_over_limit_raises(self):
        """[0] * 9_000_000 is the PoC; safe_list intercepts via len check."""
        with pytest.raises(AnimationError) as exc_info:
            _safe_list([0] * (_MAX_LIST_SIZE + 1))
        assert exc_info.value.code == "E1154"

    def test_list_without_len_passes_through(self):
        """Generators have no __len__; they pass the pre-check and are
        allowed (tracemalloc / RLIMIT remain as backstops)."""
        gen = (x for x in range(5))
        result = _safe_list(gen)
        assert result == [0, 1, 2, 3, 4]


class TestSafeTupleUnit:
    def test_small_tuple_ok(self):
        assert _safe_tuple((1, 2, 3)) == (1, 2, 3)

    def test_over_limit_raises(self):
        with pytest.raises(AnimationError) as exc_info:
            _safe_tuple(range(_MAX_LIST_SIZE + 1))
        assert exc_info.value.code == "E1154"


class TestSafeSetUnit:
    def test_small_set_ok(self):
        assert _safe_set([1, 2, 3]) == {1, 2, 3}

    def test_over_limit_raises(self):
        with pytest.raises(AnimationError) as exc_info:
            _safe_set(range(_MAX_LIST_SIZE + 1))
        assert exc_info.value.code == "E1154"


class TestSafeBytesUnit:
    def test_small_bytes_ok(self):
        assert _safe_bytes(b"hello") == b"hello"

    def test_bytes_int_form_over_limit_raises(self):
        with pytest.raises(AnimationError) as exc_info:
            _safe_bytes(_MAX_LIST_SIZE + 1)
        assert exc_info.value.code == "E1154"

    def test_bytes_int_form_at_limit_ok(self):
        result = _safe_bytes(_MAX_LIST_SIZE)
        assert len(result) == _MAX_LIST_SIZE

    def test_bytes_zero_ok(self):
        assert _safe_bytes(0) == b""


class TestH2WorkerIntegration:
    """Verify the sandbox rejects large list constructions end-to-end."""

    def test_list_repeat_bomb_rejected(self):
        """list(range(9_000_000)) must fail with E1154 or E1173, not succeed."""
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "h2-list",
                "globals": {},
                "source": "big = list(range(9000000))",
            })
            assert resp["ok"] is False
            # E1173 from _safe_range (range cap), E1154 from _safe_list (size cap).
            assert resp["code"] in ("E1154", "E1173"), resp
        finally:
            _close(proc)

    def test_normal_list_construction_unaffected(self):
        """list(range(100)) must still work."""
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "h2-small",
                "globals": {},
                "source": "result = list(range(100))",
            })
            assert resp["ok"] is True
            assert len(resp["bindings"]["result"]) == 100
        finally:
            _close(proc)

    def test_tuple_bomb_rejected(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "h2-tuple",
                "globals": {},
                "source": "big = tuple(range(200001))",
            })
            assert resp["ok"] is False
            assert resp["code"] in ("E1154", "E1173"), resp
        finally:
            _close(proc)

    def test_set_bomb_rejected(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "h2-set",
                "globals": {},
                "source": "big = set(range(200001))",
            })
            assert resp["ok"] is False
            assert resp["code"] in ("E1154", "E1173"), resp
        finally:
            _close(proc)

    def test_bytes_bomb_rejected(self):
        """bytes(10**7) would allocate 10 MB in a single C call."""
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "h2-bytes",
                "globals": {},
                # Use integer literal within _MAX_INT_LITERAL (10**7).
                "source": "big = bytes(10000001)",
            })
            assert resp["ok"] is False
            # Rejected either by AST literal check (E1154) or _safe_bytes (E1154).
            assert resp["code"] in ("E1154",), resp
        finally:
            _close(proc)


# ---------------------------------------------------------------------------
# M3 — RecursionError does not leak internal paths
# ---------------------------------------------------------------------------


class TestRecursionErrorNoPathLeak:
    """M3: RecursionError from compile() must not expose starlark_worker.py."""

    def test_format_compute_traceback_sanitises_recursion_error(self):
        """format_compute_traceback detects RecursionError text and returns
        a safe, path-free message."""
        fake_tb = (
            "Traceback (most recent call last):\n"
            '  File "/Users/user/scriba/scriba/animation/starlark_worker.py", '
            "line 527, in _evaluate\n"
            "    exec(compile(source, '<compute>', 'exec'), namespace)\n"
            "RecursionError: maximum recursion depth exceeded\n"
        )
        result = format_compute_traceback(fake_tb)
        assert "starlark_worker.py" not in result
        assert "RecursionError" in result or "nested" in result.lower()

    def test_format_compute_traceback_strips_internal_frames_in_fallback(self):
        """When no <compute> frames exist, internal File lines are stripped."""
        fake_tb = (
            "Traceback (most recent call last):\n"
            '  File "/path/to/starlark_worker.py", line 100, in foo\n'
            "    some_call()\n"
            "ValueError: something\n"
        )
        result = format_compute_traceback(fake_tb)
        assert "starlark_worker.py" not in result
        assert "ValueError" in result

    def test_deeply_nested_expression_no_path_leak_via_worker(self):
        """End-to-end: a 5000-token expression must return an E1151 message
        with no starlark_worker.py reference."""
        expr = "+".join(["1"] * 5000)
        source = f"x = {expr}"
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "m3-recursion",
                "globals": {},
                "source": source,
            })
            assert resp["ok"] is False
            message = resp.get("message", "")
            assert "starlark_worker.py" not in message, (
                f"internal path leaked: {message!r}"
            )
            assert "starlark_host.py" not in message, (
                f"internal path leaked: {message!r}"
            )
        finally:
            _close(proc)

    def test_normal_division_error_still_shows_compute_frame(self):
        """Sanity: a ZeroDivisionError still shows the <compute> frame."""
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "m3-zerodiv",
                "globals": {},
                "source": "x = 1 / 0",
            })
            assert resp["ok"] is False
            assert resp["code"] == "E1151"
            assert "<compute>" in resp["message"]
            assert "starlark_worker.py" not in resp["message"]
        finally:
            _close(proc)
