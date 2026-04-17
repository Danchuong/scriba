"""IPC lifecycle tests — Wave 7 audit findings.

Covers:
  W7-C2  SIGXCPU handler: soft RLIMIT_CPU fires SIGXCPU, worker responds E1152
  W7-H2  Instance-level budget: StarlarkHost._cumulative_elapsed is per-instance
  W7-M1  begin_render() resets budget so renders don't bleed into each other
  W7-L3  Empty-response crash raises WorkerError with code E1199
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time

import pytest

from scriba.core.errors import WorkerError
from scriba.core.workers import SubprocessWorkerPool

_WORKER_ARGV = [sys.executable, "-m", "scriba.animation.starlark_worker"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
# W7-C2 — SIGXCPU handler
# ---------------------------------------------------------------------------


_HAS_SIGXCPU = hasattr(signal, "SIGXCPU")


@pytest.mark.skipif(not _HAS_SIGXCPU, reason="SIGXCPU not available on this platform")
class TestSIGXCPULifecycle:
    """End-to-end SIGXCPU handling in the worker subprocess."""

    def test_sigxcpu_produces_e1152_json_line(self):
        """Delivering SIGXCPU to the worker must yield a JSON E1152 response."""
        proc = _spawn_worker()
        try:
            # Confirm alive.
            pong = _send(proc, {"op": "ping", "id": "pre-sigxcpu"})
            assert pong.get("ok") is True

            os.kill(proc.pid, signal.SIGXCPU)

            line = proc.stdout.readline()
            assert line, "worker produced no output after SIGXCPU"
            resp = json.loads(line)
            assert resp["ok"] is False, resp
            assert resp["code"] == "E1152", resp
            assert resp["message"]

            # Should exit cleanly (sys.exit(0) in handler).
            proc.wait(timeout=3)
            assert proc.returncode == 0
        finally:
            _close(proc)

    def test_sigxcpu_response_fields_valid(self):
        """E1152 response from SIGXCPU must include required JSON fields."""
        proc = _spawn_worker()
        try:
            os.kill(proc.pid, signal.SIGXCPU)
            line = proc.stdout.readline()
            assert line
            resp = json.loads(line)
            # Required fields per JSON-line protocol.
            assert "ok" in resp
            assert "code" in resp
            assert "message" in resp
            assert resp["ok"] is False
            assert resp["code"] == "E1152"
        finally:
            _close(proc)

    def test_sigxcpu_worker_does_not_linger(self):
        """After SIGXCPU the worker process must exit within 3 seconds."""
        proc = _spawn_worker()
        try:
            os.kill(proc.pid, signal.SIGXCPU)
            # Drain the E1152 line.
            proc.stdout.readline()
            proc.wait(timeout=3)
            assert proc.returncode is not None, "worker is still alive after 3 s"
        finally:
            _close(proc)


# ---------------------------------------------------------------------------
# W7-H2 / W7-M1 — Instance-level budget, begin_render isolation
# ---------------------------------------------------------------------------


class TestInstanceBudgetIsolation:
    """Budget is tracked per-StarlarkHost instance; begin_render() resets it."""

    def test_fresh_host_budget_is_zero(self):
        pool = SubprocessWorkerPool()
        from scriba.animation.starlark_host import StarlarkHost

        host = StarlarkHost(pool)
        try:
            assert host._cumulative_elapsed == 0.0
        finally:
            pool.close()

    def test_eval_increments_instance_budget(self):
        pool = SubprocessWorkerPool()
        from scriba.animation.starlark_host import StarlarkHost

        host = StarlarkHost(pool)
        try:
            host.eval({}, "x = 1")
            after_one = host._cumulative_elapsed
            assert after_one > 0.0

            host.eval({}, "y = 2")
            after_two = host._cumulative_elapsed
            assert after_two > after_one
        finally:
            pool.close()

    def test_begin_render_zeroes_instance_budget(self):
        pool = SubprocessWorkerPool()
        from scriba.animation.starlark_host import StarlarkHost

        host = StarlarkHost(pool)
        try:
            host.eval({}, "a = 1")
            assert host._cumulative_elapsed > 0.0

            host.begin_render()
            assert host._cumulative_elapsed == 0.0

            # Subsequent eval still works and re-accumulates from 0.
            host.eval({}, "b = 2")
            assert host._cumulative_elapsed > 0.0
        finally:
            pool.close()

    def test_two_hosts_budgets_are_independent(self):
        """begin_render() on host2 must not disturb host1's budget."""
        pool = SubprocessWorkerPool()
        from scriba.animation.starlark_host import StarlarkHost

        host1 = StarlarkHost(pool)
        host2 = StarlarkHost(pool)
        try:
            host1.eval({}, "a = 1")
            host2.eval({}, "b = 2")

            budget_before = host1._cumulative_elapsed
            host2.begin_render()  # resets host2, must not touch host1
            assert host1._cumulative_elapsed == pytest.approx(budget_before)
        finally:
            pool.close()

    def test_budget_overflow_raises_worker_error_e1152(self):
        """Manually pre-charge budget past limit; next eval raises E1152."""
        import scriba.animation.starlark_worker as sw
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            host.eval({}, "x = 1")
            # Force the instance accumulator past the cap.
            host._cumulative_elapsed = sw._CUMULATIVE_BUDGET_SECONDS + 1.0
            with pytest.raises(WorkerError) as exc_info:
                host.eval({}, "y = 2")
            err = exc_info.value
            assert getattr(err, "code", None) == "E1152"
            assert "cumulative" in str(err).lower()
        finally:
            pool.close()

    def test_begin_render_clears_overflow_state(self):
        """After overflow, begin_render() allows eval to succeed again."""
        import scriba.animation.starlark_worker as sw
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            host.eval({}, "x = 1")
            host._cumulative_elapsed = sw._CUMULATIVE_BUDGET_SECONDS + 1.0

            # Overflow state cleared by begin_render.
            host.begin_render()
            # Must succeed now.
            result = host.eval({}, "z = 42")
            assert result.get("z") == 42
        finally:
            pool.close()


# ---------------------------------------------------------------------------
# W7-L3 — Empty-response crash → E1199
# ---------------------------------------------------------------------------


class TestEmptyResponseE1199:
    """A crashed worker (empty response) must raise WorkerError with E1199."""

    def test_killed_worker_raises_e1199(self):
        """SIGKILL the worker subprocess; host must receive WorkerError E1199."""
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            # Prime the worker so the subprocess is alive.
            host.eval({}, "x = 1")

            # Hard-kill the subprocess.
            worker = pool.get("starlark")
            if worker._process is not None:
                os.kill(worker._process.pid, signal.SIGKILL)

            with pytest.raises(WorkerError) as exc_info:
                host.eval({}, "y = 2")
            err = exc_info.value
            assert getattr(err, "code", None) == "E1199", (
                f"expected E1199, got code={getattr(err, 'code', None)!r} "
                f"message={str(err)!r}"
            )
        finally:
            pool.close()

    def test_worker_recovers_after_e1199(self):
        """After an E1199 crash, the pool auto-respawns and the next call succeeds."""
        from scriba.animation.starlark_host import StarlarkHost

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            host.eval({}, "x = 1")

            worker = pool.get("starlark")
            if worker._process is not None:
                os.kill(worker._process.pid, signal.SIGKILL)

            # This call raises E1199 (crash).
            with pytest.raises(WorkerError) as exc_info:
                host.eval({}, "y = 2")
            assert getattr(exc_info.value, "code", None) == "E1199"

            # The next call must succeed (worker auto-respawned).
            host.begin_render()
            result = host.eval({}, "recovered = 99")
            assert result.get("recovered") == 99
        finally:
            pool.close()
