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
