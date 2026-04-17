"""Regression tests for Starlark sandbox security fixes.

C1 — Cumulative budget tracked on StarlarkHost instance (W7-H2/W7-M1)
H2 — Bulk-allocation builtins capped to prevent C-level SIGALRM bypass
M3 — RecursionError no longer leaks starlark_worker.py internal paths
W7-C2 — SIGXCPU handler flushes graceful E1152 response
W7-L3 — Empty-response WorkerError carries E1199 code
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
    """W7-H2/W7-M1: Budget tracked on StarlarkHost instance, not module-level."""

    def test_host_starts_with_zero_budget(self):
        """A fresh StarlarkHost starts with _cumulative_elapsed == 0.0."""
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            assert host._cumulative_elapsed == 0.0
        finally:
            pool.close()

    def test_host_eval_charges_elapsed_after_success(self):
        """Each successful eval() charges its wall-clock time to the instance budget."""
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            host.eval({}, "x = 1")
            first_elapsed = host._cumulative_elapsed
            assert first_elapsed > 0.0

            host.eval({}, "y = 2")
            second_elapsed = host._cumulative_elapsed
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
            # Make one cheap call to populate _cumulative_elapsed.
            host.eval({}, "x = 1")
            # Directly set the instance counter past the limit so the next
            # eval() detects overflow regardless of its own tiny elapsed.
            host._cumulative_elapsed = sw._CUMULATIVE_BUDGET_SECONDS + 1.0
            with pytest.raises(WorkerError) as exc_info:
                host.eval({}, "y = 2")
            err = exc_info.value
            assert "E1152" in str(err) or getattr(err, "code", "") == "E1152"
            assert "cumulative" in str(err).lower()
        finally:
            pool.close()

    def test_begin_render_resets_instance_budget(self):
        """begin_render() zeroes _cumulative_elapsed so renders don't bleed."""
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            host.eval({}, "a = 1")
            assert host._cumulative_elapsed > 0.0

            host.begin_render()
            assert host._cumulative_elapsed == 0.0

            # Ensure eval() still works and starts accumulating from zero.
            host.eval({}, "b = 2")
            assert host._cumulative_elapsed > 0.0
        finally:
            pool.close()

    def test_two_hosts_have_independent_budgets(self):
        """Two StarlarkHost instances on the same pool track budgets independently."""
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host1 = StarlarkHost(pool)
        host2 = StarlarkHost(pool)
        try:
            host1.eval({}, "a = 1")
            host2.eval({}, "b = 2")
            # Both accumulate independently; neither resets the other.
            assert host1._cumulative_elapsed > 0.0
            assert host2._cumulative_elapsed > 0.0
            # They should be roughly equal (both did one fast eval).
            # The key invariant: one host's eval doesn't zero the other.
            before = host1._cumulative_elapsed
            host2.begin_render()
            # host1 budget must be untouched after host2 reset.
            assert host1._cumulative_elapsed == pytest.approx(before)
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


# ---------------------------------------------------------------------------
# W7-C2 — SIGXCPU handler writes graceful E1152
# ---------------------------------------------------------------------------


class TestSIGXCPUHandler:
    """W7-C2: SIGXCPU handler must flush a structured E1152 response."""

    @pytest.mark.skipif(
        not hasattr(__import__("signal"), "SIGXCPU"),
        reason="SIGXCPU not available on this platform",
    )
    def test_sigxcpu_handler_writes_e1152_and_exits_cleanly(self):
        """Send SIGXCPU to a live worker; it should return E1152 and exit 0."""
        import os
        import signal as _signal

        proc = _spawn_worker()
        try:
            # Confirm the worker is alive via ping.
            pong = _send(proc, {"op": "ping", "id": "ping-1"})
            assert pong.get("ok") is True

            # Deliver SIGXCPU directly to the worker process.
            os.kill(proc.pid, _signal.SIGXCPU)

            # The handler should write an E1152 line to stdout before exiting.
            line = proc.stdout.readline()
            assert line, "worker produced no output after SIGXCPU"
            resp = json.loads(line)
            assert resp["ok"] is False
            assert resp["code"] == "E1152"
            assert (
                "cpu" in resp["message"].lower()
                or "limit" in resp["message"].lower()
            )

            # Worker must have exited cleanly (exit code 0 from sys.exit(0)).
            proc.wait(timeout=3)
            assert proc.returncode == 0, (
                f"expected returncode 0, got {proc.returncode}"
            )
        finally:
            _close(proc)


# ---------------------------------------------------------------------------
# W7-L3 — Empty-response WorkerError carries E1199
# ---------------------------------------------------------------------------


class TestEmptyResponseErrorCode:
    """W7-L3: a worker crash (empty response) must raise WorkerError(code='E1199')."""

    def test_empty_response_worker_error_has_e1199_code(self):
        """Kill the worker subprocess; the host must raise WorkerError E1199."""
        import os
        import signal as _signal

        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            # First request confirms the worker is alive.
            host.eval({}, "x = 1")

            # Retrieve the underlying PersistentSubprocessWorker and kill the
            # subprocess so the next send() gets an empty response.
            worker = pool.get("starlark")
            if worker._process is not None:
                os.kill(worker._process.pid, _signal.SIGKILL)

            # The next eval() must raise WorkerError with code E1199.
            with pytest.raises(WorkerError) as exc_info:
                host.eval({}, "y = 2")
            err = exc_info.value
            assert getattr(err, "code", None) == "E1199", (
                f"expected E1199, got code={getattr(err, 'code', None)!r} "
                f"message={str(err)!r}"
            )
        finally:
            pool.close()
