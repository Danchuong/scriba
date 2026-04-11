"""Tests for the Starlark wall-clock and cumulative budget helpers.

Covers Wave 6.4 red-team hardening:

* Per-block wall-clock limit reduced from 3 s to 1 s
  (:data:`scriba.animation.starlark_worker._WALL_CLOCK_SECONDS`).
* Cumulative budget tracking across blocks via
  :func:`reset_cumulative_budget` / :func:`consume_cumulative_budget`.

The wall-clock reduction test spawns the worker subprocess and verifies
that a compute block which would have fit inside the old 3 s window
now trips the timeout (or step counter, on Windows). The cumulative
budget tests exercise the helpers directly — the worker subprocess
does not share module state across requests so cumulative tracking
lives in the host-facing layer.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.starlark_worker import (
    _CUMULATIVE_BUDGET_SECONDS,
    _WALL_CLOCK_SECONDS,
    consume_cumulative_budget,
    get_cumulative_elapsed,
    reset_cumulative_budget,
)


# ---------------------------------------------------------------------------
# Fixtures — ensure every test starts from a clean cumulative counter.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_budget_state() -> None:
    reset_cumulative_budget()
    yield
    reset_cumulative_budget()


# ---------------------------------------------------------------------------
# Wall-clock constant
# ---------------------------------------------------------------------------


class TestWallClockConstant:
    def test_wall_clock_is_one_second(self) -> None:
        """Per-block wall-clock limit must be 1 s after W6.4 reduction."""
        assert _WALL_CLOCK_SECONDS == 1

    def test_cumulative_budget_is_five_seconds(self) -> None:
        """Cumulative budget default is 5 s (matches fix plan)."""
        assert _CUMULATIVE_BUDGET_SECONDS == 5.0


# ---------------------------------------------------------------------------
# Cumulative budget helpers
# ---------------------------------------------------------------------------


class TestCumulativeBudget:
    def test_reset_clears_state(self) -> None:
        consume_cumulative_budget(0.5)
        assert get_cumulative_elapsed() == pytest.approx(0.5)
        reset_cumulative_budget()
        assert get_cumulative_elapsed() == 0.0

    def test_single_consume_under_limit_ok(self) -> None:
        consume_cumulative_budget(1.0)
        assert get_cumulative_elapsed() == pytest.approx(1.0)

    def test_multiple_consumes_accumulate(self) -> None:
        consume_cumulative_budget(1.0)
        consume_cumulative_budget(1.5)
        consume_cumulative_budget(0.5)
        assert get_cumulative_elapsed() == pytest.approx(3.0)

    def test_three_blocks_of_two_seconds_trip_on_third(self) -> None:
        """Three 2 s blocks consume 6 s total; third should fail."""
        consume_cumulative_budget(2.0)  # 2 s total — ok
        consume_cumulative_budget(2.0)  # 4 s total — ok
        with pytest.raises(AnimationError) as exc_info:
            consume_cumulative_budget(2.0)  # 6 s total — over
        exc = exc_info.value
        assert exc.code == "E1152"
        assert "cumulative" in str(exc).lower()

    def test_single_over_budget_trips_immediately(self) -> None:
        with pytest.raises(AnimationError) as exc_info:
            consume_cumulative_budget(6.0)
        assert exc_info.value.code == "E1152"

    def test_exact_budget_is_not_over(self) -> None:
        # Exactly at the limit is allowed; only >limit trips.
        consume_cumulative_budget(_CUMULATIVE_BUDGET_SECONDS)
        # Next tiny increment pushes us over.
        with pytest.raises(AnimationError):
            consume_cumulative_budget(0.01)

    def test_negative_elapsed_clamped_to_zero(self) -> None:
        # Clock skew or buggy caller must not gift extra budget.
        consume_cumulative_budget(-1.0)
        assert get_cumulative_elapsed() == 0.0
        consume_cumulative_budget(2.0)
        assert get_cumulative_elapsed() == pytest.approx(2.0)

    def test_reset_after_overflow_allows_fresh_budget(self) -> None:
        # Force an overflow, then verify reset restores usable state.
        with pytest.raises(AnimationError):
            consume_cumulative_budget(100.0)
        reset_cumulative_budget()
        # Fresh budget — should succeed.
        consume_cumulative_budget(1.0)
        assert get_cumulative_elapsed() == pytest.approx(1.0)

    def test_hint_is_actionable(self) -> None:
        with pytest.raises(AnimationError) as exc_info:
            consume_cumulative_budget(10.0)
        hint = exc_info.value.hint or ""
        # The hint should point the author at something they can change.
        assert "compute" in hint.lower() or "animation" in hint.lower()


# ---------------------------------------------------------------------------
# Per-block wall-clock (subprocess integration)
# ---------------------------------------------------------------------------


def _spawn_worker() -> subprocess.Popen:
    """Spawn the Starlark worker subprocess."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "scriba.animation.starlark_worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    # Consume the ready signal from stderr.
    assert proc.stderr is not None
    ready = proc.stderr.readline()
    assert "ready" in ready, f"worker did not signal ready: {ready!r}"
    return proc


def _send(proc: subprocess.Popen, request: dict) -> dict:
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    return json.loads(line)


def _close(proc: subprocess.Popen) -> None:
    try:
        if proc.stdin is not None:
            proc.stdin.close()
    except Exception:  # noqa: BLE001 — cleanup best-effort
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


class TestWallClockIntegration:
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="SIGALRM not available on Windows",
    )
    def test_compute_block_trips_one_second_wall_clock(self) -> None:
        """A tight loop that used to fit in 3 s should now trip the 1 s alarm.

        We use the largest allowed ``range()`` (1e6) inside a nested
        loop so the worker spends at least a couple of seconds executing
        under the old limit. The test accepts any of the expected
        defence responses (``E1152`` timeout, ``E1153`` step limit,
        ``E1173`` iterable validation) because on fast machines the
        step counter may fire before the wall-clock alarm.
        """
        proc = _spawn_worker()
        try:
            start = time.monotonic()
            resp = _send(proc, {
                "op": "eval",
                "id": "wall-clock-1",
                "globals": {},
                "source": (
                    "x = 0\n"
                    "for i in range(1000000):\n"
                    "    for j in range(1000000):\n"
                    "        x += 1\n"
                ),
            })
            elapsed = time.monotonic() - start
            assert resp["ok"] is False
            assert resp["code"] in ("E1152", "E1153", "E1173")
            # Under the 1 s wall-clock, any real timeout should return
            # well under the old 3 s ceiling.
            assert elapsed < 3.0, (
                f"wall-clock alarm did not fire in time: elapsed={elapsed:.2f}s"
            )
        finally:
            _close(proc)
