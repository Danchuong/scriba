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


# -----------------------------------------------------------------------------
# Cluster 8 additions — coverage for uncovered error paths in workers.py.
# These tests extend the existing 17 tests above without modifying them.
# -----------------------------------------------------------------------------


def test_worker_name_property():
    w = PersistentSubprocessWorker("myname", _fake_argv())
    try:
        assert w.name == "myname"
    finally:
        w.close()


def test_worker_request_count_starts_at_zero():
    w = PersistentSubprocessWorker("fake", _fake_argv())
    try:
        assert w.request_count == 0
    finally:
        w.close()


def test_worker_request_count_increments():
    w = PersistentSubprocessWorker(
        "fake", _fake_argv(), ready_signal="fake-worker ready",
    )
    try:
        w.send({"echo": "a"})
        w.send({"echo": "b"})
        w.send({"echo": "c"})
        assert w.request_count == 3
    finally:
        w.close()


def test_worker_is_running_false_before_spawn():
    w = PersistentSubprocessWorker("fake", _fake_argv())
    try:
        assert w.is_running is False
    finally:
        w.close()


def test_worker_is_running_true_after_send():
    w = PersistentSubprocessWorker(
        "fake", _fake_argv(), ready_signal="fake-worker ready",
    )
    try:
        w.send({"echo": "hi"})
        assert w.is_running is True
    finally:
        w.close()


def test_worker_spawn_missing_binary_raises():
    """FileNotFoundError during spawn is re-raised as WorkerError."""
    w = PersistentSubprocessWorker(
        "ghost", ["/path/that/definitely/does/not/exist/xyz-scriba-test"],
    )
    try:
        with pytest.raises(WorkerError) as excinfo:
            w.send({"ping": 1})
        assert "failed to spawn" in str(excinfo.value)
    finally:
        w.close()


def test_worker_ready_signal_never_arrives_raises():
    """A worker whose binary exits immediately without the ready signal
    must surface a WorkerError from _spawn()."""
    argv = [sys.executable, "-c", "import sys; sys.exit(0)"]
    w = PersistentSubprocessWorker(
        "silent",
        argv,
        ready_signal="this-signal-never-comes",
    )
    try:
        with pytest.raises(WorkerError) as excinfo:
            w.send({"x": 1})
        assert "did not report ready" in str(excinfo.value)
    finally:
        w.close()


def test_worker_invalid_json_response_raises():
    """If the subprocess writes something that isn't valid JSON, the send
    must raise WorkerError pointing at JSONDecodeError."""
    argv = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "sys.stdin.readline(); "
            "sys.stdout.write('not-json-at-all\\n'); "
            "sys.stdout.flush()"
        ),
    ]
    w = PersistentSubprocessWorker("bad-json", argv)
    try:
        with pytest.raises(WorkerError) as excinfo:
            w.send({"x": 1})
        assert "invalid JSON response" in str(excinfo.value)
    finally:
        w.close()


def test_worker_empty_response_raises():
    """Subprocess that closes stdout without writing anything produces
    'closed unexpectedly (empty response)'."""
    argv = [
        sys.executable,
        "-c",
        "import sys; sys.stdin.readline(); sys.exit(0)",
    ]
    w = PersistentSubprocessWorker("quiet", argv)
    try:
        with pytest.raises(WorkerError) as excinfo:
            w.send({"x": 1})
        assert "closed unexpectedly" in str(excinfo.value)
    finally:
        w.close()


def test_worker_send_on_closed_raises():
    """Using a closed worker surfaces a WorkerError via _ensure_started."""
    w = PersistentSubprocessWorker(
        "fake", _fake_argv(), ready_signal="fake-worker ready",
    )
    w.close()
    with pytest.raises(WorkerError) as excinfo:
        w.send({"echo": "x"})
    assert "closed" in str(excinfo.value)


def test_worker_close_after_send_is_idempotent():
    w = PersistentSubprocessWorker(
        "fake", _fake_argv(), ready_signal="fake-worker ready",
    )
    w.send({"echo": "a"})
    w.close()
    w.close()  # second close must be a no-op
    # A third for good measure.
    w.close()


def test_worker_close_unused_worker_idempotent():
    """Closing a worker that was never spawned should be a no-op."""
    w = PersistentSubprocessWorker("never", _fake_argv())
    w.close()
    w.close()


def test_worker_context_manager_closes():
    """__enter__/__exit__ must release resources even when send() failed."""
    with PersistentSubprocessWorker(
        "fake", _fake_argv(), ready_signal="fake-worker ready"
    ) as w:
        r = w.send({"echo": "cm"})
        assert r.get("echo") == "cm"
    # After the with-block the worker is closed.
    with pytest.raises(WorkerError):
        w.send({"echo": "again"})


# ----- OneShotSubprocessWorker coverage extensions ----------------------------


def test_oneshot_send_on_closed_raises():
    argv = [sys.executable, "-c", "import sys; sys.stdin.readline()"]
    w = OneShotSubprocessWorker("o", argv)
    w.close()
    with pytest.raises(WorkerError) as excinfo:
        w.send({"x": 1})
    assert "closed" in str(excinfo.value)


def test_oneshot_spawn_missing_binary_raises():
    w = OneShotSubprocessWorker(
        "ghost", ["/definitely/not/a/real/binary/zzz-scriba-test"]
    )
    try:
        with pytest.raises(WorkerError) as excinfo:
            w.send({"a": 1})
        assert "failed to spawn" in str(excinfo.value)
    finally:
        w.close()


def test_oneshot_timeout_raises():
    """If the subprocess blocks past the timeout, WorkerError is raised."""
    argv = [sys.executable, "-c", "import time; time.sleep(5)"]
    w = OneShotSubprocessWorker("slow", argv, default_timeout=0.25)
    try:
        with pytest.raises(WorkerError) as excinfo:
            w.send({"x": 1})
        assert "timeout" in str(excinfo.value)
    finally:
        w.close()


def test_oneshot_empty_output_raises():
    argv = [sys.executable, "-c", "import sys; sys.stdin.readline()"]
    w = OneShotSubprocessWorker("empty", argv)
    try:
        with pytest.raises(WorkerError) as excinfo:
            w.send({"x": 1})
        assert "no output" in str(excinfo.value)
    finally:
        w.close()


def test_oneshot_invalid_json_raises():
    argv = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "sys.stdin.readline(); "
            "sys.stdout.write('definitely not json\\n'); "
            "sys.stdout.flush()"
        ),
    ]
    w = OneShotSubprocessWorker("bad-json", argv)
    try:
        with pytest.raises(WorkerError) as excinfo:
            w.send({"x": 1})
        assert "invalid JSON" in str(excinfo.value)
    finally:
        w.close()


def test_oneshot_name_property():
    w = OneShotSubprocessWorker("oneshot-name", _fake_argv())
    try:
        assert w.name == "oneshot-name"
    finally:
        w.close()


def test_oneshot_close_idempotent():
    w = OneShotSubprocessWorker("o", _fake_argv())
    w.close()
    w.close()


# ----- SubprocessWorkerPool coverage extensions -------------------------------


def test_pool_register_idempotent():
    """Re-registering the same name is a silent no-op."""
    with SubprocessWorkerPool() as pool:
        pool.register("fake", _fake_argv(), ready_signal="fake-worker ready")
        first = pool.get("fake")
        # Second registration with different argv is ignored.
        pool.register(
            "fake",
            [sys.executable, "-c", "print('nope')"],
            ready_signal="other",
        )
        second = pool.get("fake")
        assert first is second


def test_pool_register_requires_argv_or_worker():
    with SubprocessWorkerPool() as pool:
        with pytest.raises(ValueError) as excinfo:
            pool.register("bare")  # no argv, no worker
        assert "argv" in str(excinfo.value) or "worker" in str(excinfo.value)


def test_pool_register_after_close_raises():
    pool = SubprocessWorkerPool()
    pool.close()
    with pytest.raises(WorkerError) as excinfo:
        pool.register("x", _fake_argv())
    assert "closed" in str(excinfo.value)


def test_pool_register_prebuilt_worker():
    """Passing an already-built worker instance is a valid register path."""
    pre = PersistentSubprocessWorker(
        "pre", _fake_argv(), ready_signal="fake-worker ready",
    )
    with SubprocessWorkerPool() as pool:
        pool.register("pre", worker=pre)
        assert pool.get("pre") is pre


def test_pool_close_swallows_worker_close_errors():
    """Pool.close() must never propagate errors from individual worker.close()
    calls — they're logged and cleanup continues."""

    class BoomWorker:
        name = "boom"

        def send(self, request, *, timeout=None):
            return {}

        def close(self):
            raise RuntimeError("boom")

    pool = SubprocessWorkerPool()
    pool.register("boom", worker=BoomWorker())
    # Must not raise despite worker.close() blowing up.
    pool.close()
    # Subsequent close still idempotent.
    pool.close()


def test_pool_close_clears_workers():
    pool = SubprocessWorkerPool()
    pool.register("fake", _fake_argv(), ready_signal="fake-worker ready")
    pool.close()
    with pytest.raises(KeyError):
        pool.get("fake")


# ----- Lazy alias identity (Cluster 9 symbol re-export) -----------------------


def test_alias_identity_twice():
    """SubprocessWorker alias resolves to the same class every access."""
    from scriba.core.workers import SubprocessWorker as A
    from scriba.core.workers import SubprocessWorker as B
    assert A is B
    assert A is PersistentSubprocessWorker


def test_alias_via_top_level_scriba_module():
    import scriba
    assert scriba.SubprocessWorker is PersistentSubprocessWorker
    # Access twice.
    assert scriba.SubprocessWorker is scriba.SubprocessWorker
