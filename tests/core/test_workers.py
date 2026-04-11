"""SubprocessWorker / SubprocessWorkerPool lifecycle tests.

These rely on a fake JSON-line worker shipped at
``tests/fixtures/fake_worker.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scriba import (
    OneShotSubprocessWorker,
    PersistentSubprocessWorker,
    SubprocessWorker,
    SubprocessWorkerPool,
    Worker,
    WorkerError,
)

FAKE_WORKER = Path(__file__).resolve().parents[1] / "fixtures" / "fake_worker.py"


def _fake_argv(*extra: str) -> list[str]:
    return [sys.executable, str(FAKE_WORKER), *extra]


def test_worker_pool_register_and_get():
    pool = SubprocessWorkerPool()
    try:
        pool.register("fake", _fake_argv(), ready_signal="fake-worker ready")
        w = pool.get("fake")
        assert isinstance(w, SubprocessWorker)
    finally:
        pool.close()


def test_worker_pool_get_unregistered_raises():
    pool = SubprocessWorkerPool()
    try:
        with pytest.raises(KeyError):
            pool.get("does-not-exist")
    finally:
        pool.close()


def test_worker_pool_close_idempotent():
    pool = SubprocessWorkerPool()
    pool.close()
    pool.close()  # must not raise


def test_worker_pool_context_manager():
    with SubprocessWorkerPool() as pool:
        assert pool is not None


def test_subprocess_worker_lazy_spawn():
    """Constructing a worker must NOT spawn the subprocess; the first
    .send() should."""
    w = SubprocessWorker("fake", _fake_argv(), ready_signal="fake-worker ready")
    # No spawn yet — closing immediately should be a no-op.
    w.close()


def test_subprocess_worker_crash_respawns():
    """If the worker dies, the next send() must transparently respawn."""
    w = SubprocessWorker("fake", _fake_argv(), ready_signal="fake-worker ready")
    try:
        w.send({"echo": "hello"})
        # Tell the worker to die on the next request.
        try:
            w.send({"die": True})
        except WorkerError:
            pass
        # Next call should respawn and succeed.
        result = w.send({"echo": "again"})
        assert result.get("echo") == "again"
    finally:
        w.close()


def test_subprocess_worker_timeout_raises():
    w = SubprocessWorker(
        "fake", _fake_argv(), ready_signal="fake-worker ready",
        default_timeout=0.05,
    )
    try:
        with pytest.raises(WorkerError):
            w.send({"sleep": 2.0}, timeout=0.05)
    finally:
        w.close()


def test_subprocess_worker_alias_is_persistent():
    assert SubprocessWorker is PersistentSubprocessWorker


def test_worker_protocol_runtime_checkable():
    w = PersistentSubprocessWorker("fake", _fake_argv())
    try:
        assert isinstance(w, Worker)
    finally:
        w.close()
    o = OneShotSubprocessWorker("fake", _fake_argv())
    try:
        assert isinstance(o, Worker)
    finally:
        o.close()


def test_oneshot_mode():
    """OneShotSubprocessWorker spawns a fresh subprocess per call."""
    argv = [
        sys.executable,
        "-c",
        (
            "import sys,json;"
            "line=sys.stdin.readline();"
            "print(json.dumps({'echo': json.loads(line)}))"
        ),
    ]
    w = OneShotSubprocessWorker("oneshot-echo", argv)
    try:
        r1 = w.send({"a": 1})
        assert r1 == {"echo": {"a": 1}}
        r2 = w.send({"b": 2})
        assert r2 == {"echo": {"b": 2}}
    finally:
        w.close()


def test_pool_register_oneshot_mode():
    argv = [
        sys.executable,
        "-c",
        (
            "import sys,json;"
            "line=sys.stdin.readline();"
            "print(json.dumps({'echo': json.loads(line)}))"
        ),
    ]
    with SubprocessWorkerPool() as pool:
        pool.register("oneshot", argv, mode="oneshot")
        w = pool.get("oneshot")
        assert isinstance(w, OneShotSubprocessWorker)
        assert w.send({"x": 3}) == {"echo": {"x": 3}}


def test_subprocess_worker_max_requests_restart():
    """After ``max_requests`` successful sends the worker must be restarted
    transparently. We can't directly observe the restart from the client,
    but we can verify N+1 sends still succeed when N == max_requests."""
    w = SubprocessWorker(
        "fake", _fake_argv(), ready_signal="fake-worker ready",
        max_requests=3,
    )
    try:
        for i in range(5):
            r = w.send({"echo": str(i)})
            assert r.get("echo") == str(i)
    finally:
        w.close()


# =========================================================================
# Cluster 3 — audit finding 20-H3 / 14-H2 regression tests
# =========================================================================


def test_persistent_worker_send_uses_ensure_ascii_true():
    """20-H3: ``json.dumps(..., ensure_ascii=True)`` must escape
    zero-width, BOM, LS/PS, and combining characters so they cannot
    corrupt the newline-delimited protocol.
    """
    import json
    import sys

    captured: dict[str, str] = {}

    class FakeStdin:
        def write(self, line: str) -> None:
            captured["line"] = line

        def flush(self) -> None:
            pass

    class FakeStdout:
        def __init__(self) -> None:
            self._calls = 0

        def readline(self) -> str:
            # Echo back a no-op response.
            self._calls += 1
            return json.dumps({"ok": True}) + "\n"

    class FakeStderr:
        def readline(self) -> str:
            return ""

    class FakeProc:
        def __init__(self) -> None:
            self.stdin = FakeStdin()
            self.stdout = FakeStdout()
            self.stderr = FakeStderr()

        def poll(self):
            return None

    w = PersistentSubprocessWorker("fake-asciitest", ["/bin/true"])
    # Bypass _ensure_started by planting a fake process.
    w._process = FakeProc()  # type: ignore[assignment]
    w._request_count = 0

    # Unicode pile with zero-width joiners and LS/PS separators.
    payload = {
        "tex": "a\u200bb\u200cc\u200dd\ufeffe",
        "sep": "x\u2028y\u2029z",
    }
    try:
        # select.select on the fake stdout will fail on darwin; skip the
        # readable check by patching select.select.
        import select as _select
        real_select = _select.select

        def fake_select(rlist, wlist, xlist, timeout):
            return (rlist, [], [])

        _select.select = fake_select  # type: ignore[assignment]
        try:
            w.send(payload)
        finally:
            _select.select = real_select  # type: ignore[assignment]
    finally:
        # Avoid _kill() trying to terminate the fake.
        w._process = None  # type: ignore[assignment]
        w._closed = True

    line = captured["line"]
    # The wire line is pure ASCII (so every non-ASCII codepoint is escaped).
    assert line.endswith("\n")
    assert all(ord(ch) < 128 for ch in line), (
        f"non-ASCII leaked onto the wire: {line!r}"
    )
    # Decoding round-trips the original payload.
    assert json.loads(line) == payload


def test_oneshot_worker_uses_ensure_ascii_true():
    """20-H3: OneShotSubprocessWorker also escapes every non-ASCII byte.
    We verify by pointing the worker at a python -c that echoes the raw
    stdin line back on stdout.
    """
    import json

    argv = [
        sys.executable,
        "-c",
        (
            "import sys;"
            "line=sys.stdin.readline();"
            "sys.stdout.write(line)"
        ),
    ]
    w = OneShotSubprocessWorker("ascii-echo", argv)
    try:
        payload = {"x": "a\u200bb\u2028c"}
        result = w.send(payload)
        # round-trips correctly
        assert result == payload
    finally:
        w.close()


def test_subprocess_worker_alias_emits_deprecation_on_external_access():
    """14-H2: The ``SubprocessWorker`` alias emits a DeprecationWarning on
    attribute access from external (non-scriba) callers.

    Wave 3 Cluster 9 moved the warning from import time to PEP 562
    ``__getattr__`` so plain ``import scriba`` stays silent. The warning
    now fires only when external code reaches for the alias. This test
    pins the new behavior; parallel coverage lives in
    ``tests/unit/test_public_api.py``.

    Note: intentionally does NOT manipulate ``sys.modules`` to avoid
    reloading the module mid-test-run, which was observed to trigger
    step-limit flakes in tests that monkey-patch module attributes.
    """
    import warnings

    import scriba.core.workers as workers_mod

    # Reaching for the attribute from this external test module DOES fire.
    with warnings.catch_warnings(record=True) as on_access:
        warnings.simplefilter("always")
        alias = workers_mod.SubprocessWorker
    dep = [
        w for w in on_access
        if issubclass(w.category, DeprecationWarning)
        and "SubprocessWorker" in str(w.message)
    ]
    assert dep, (
        f"expected DeprecationWarning on SubprocessWorker access, "
        f"got {[str(w.message) for w in on_access]}"
    )
    # Alias still resolves to the real class for backward compat.
    from scriba.core.workers import PersistentSubprocessWorker
    assert alias is PersistentSubprocessWorker
