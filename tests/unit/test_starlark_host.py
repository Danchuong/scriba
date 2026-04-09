"""Tests for StarlarkHost — the Python-side wrapper around the worker."""

from __future__ import annotations

import pytest

from scriba.core.errors import WorkerError
from scriba.core.workers import SubprocessWorkerPool
from scriba.animation.starlark_host import StarlarkHost


class TestHostRegistration:
    def test_registers_worker_in_pool(self):
        pool = SubprocessWorkerPool()
        try:
            _host = StarlarkHost(pool)
            worker = pool.get("starlark")
            assert worker.name == "starlark"
        finally:
            pool.close()

    def test_idempotent_registration(self):
        """Creating two StarlarkHost instances with the same pool should
        not raise (register is idempotent)."""
        pool = SubprocessWorkerPool()
        try:
            _host1 = StarlarkHost(pool)
            _host2 = StarlarkHost(pool)
            worker = pool.get("starlark")
            assert worker.name == "starlark"
        finally:
            pool.close()


class TestHostEval:
    def test_eval_returns_bindings(self):
        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            result = host.eval({"h": [1, 2, 3]}, "n = len(h)")
            assert result["n"] == 3
            assert result["h"] == [1, 2, 3]
        finally:
            pool.close()

    def test_eval_raises_on_forbidden_keyword(self):
        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            with pytest.raises(WorkerError, match="E1154"):
                host.eval({}, "while True: pass")
        finally:
            pool.close()

    def test_eval_raises_on_syntax_error(self):
        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            with pytest.raises(WorkerError, match="E1150"):
                host.eval({}, "def (invalid")
        finally:
            pool.close()


class TestHostPing:
    def test_ping_healthy(self):
        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        try:
            assert host.ping() is True
        finally:
            pool.close()


class TestHostClose:
    def test_close_shuts_down_worker(self):
        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        # Force the worker to spawn by sending a request.
        host.eval({}, "x = 1")
        host.close()
        # After close, the worker should not be running (but pool still has it).
        worker = pool.get("starlark")
        # The worker's is_running should be False after close.
        assert not getattr(worker, "is_running", True)
        pool.close()

    def test_context_manager(self):
        pool = SubprocessWorkerPool()
        with StarlarkHost(pool) as host:
            result = host.eval({}, "x = 42")
            assert result["x"] == 42
        pool.close()
