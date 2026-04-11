"""Tests for StarlarkHost — the Python-side wrapper around the worker."""

from __future__ import annotations

import warnings
from unittest.mock import patch

import pytest

from scriba.core.errors import WorkerError
from scriba.core.workers import SubprocessWorkerPool
from scriba.animation import starlark_host as starlark_host_module
from scriba.animation.starlark_host import StarlarkHost, _reset_windows_warning


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


class TestWindowsWarning:
    """Verify the one-shot Windows backstop-unavailable warning.

    The warning fires when a ``StarlarkHost`` is constructed on Windows
    because ``signal.SIGALRM`` does not exist there, so the worker's
    wall-clock timeout cannot be installed.  Only the step counter
    protects against runaway loops.  The warning must:

    * fire on Windows
    * fire at most once per process
    * NOT fire on Linux / macOS
    """

    def setup_method(self) -> None:
        _reset_windows_warning()

    def teardown_method(self) -> None:
        _reset_windows_warning()

    def test_warning_fires_on_windows(self) -> None:
        pool = SubprocessWorkerPool()
        try:
            with patch.object(
                starlark_host_module.platform, "system", return_value="Windows"
            ):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    _host = StarlarkHost(pool)
                messages = [
                    str(w.message)
                    for w in caught
                    if issubclass(w.category, RuntimeWarning)
                ]
                assert any(
                    "SIGALRM backstop unavailable" in m for m in messages
                ), f"expected Windows warning, got: {messages!r}"
        finally:
            pool.close()

    def test_warning_fires_at_most_once_per_process(self) -> None:
        pool = SubprocessWorkerPool()
        try:
            with patch.object(
                starlark_host_module.platform, "system", return_value="Windows"
            ):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    _host1 = StarlarkHost(pool)
                    _host2 = StarlarkHost(pool)
                    _host3 = StarlarkHost(pool)
                windows_warnings = [
                    w
                    for w in caught
                    if issubclass(w.category, RuntimeWarning)
                    and "SIGALRM backstop unavailable" in str(w.message)
                ]
                assert len(windows_warnings) == 1, (
                    f"expected exactly one warning, got {len(windows_warnings)}"
                )
        finally:
            pool.close()

    def test_warning_does_not_fire_on_linux(self) -> None:
        pool = SubprocessWorkerPool()
        try:
            with patch.object(
                starlark_host_module.platform, "system", return_value="Linux"
            ):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    _host = StarlarkHost(pool)
                windows_warnings = [
                    w
                    for w in caught
                    if issubclass(w.category, RuntimeWarning)
                    and "SIGALRM backstop unavailable" in str(w.message)
                ]
                assert windows_warnings == [], (
                    f"warning unexpectedly fired on Linux: {windows_warnings!r}"
                )
        finally:
            pool.close()

    def test_warning_does_not_fire_on_darwin(self) -> None:
        pool = SubprocessWorkerPool()
        try:
            with patch.object(
                starlark_host_module.platform, "system", return_value="Darwin"
            ):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    _host = StarlarkHost(pool)
                windows_warnings = [
                    w
                    for w in caught
                    if issubclass(w.category, RuntimeWarning)
                    and "SIGALRM backstop unavailable" in str(w.message)
                ]
                assert windows_warnings == [], (
                    f"warning unexpectedly fired on Darwin: {windows_warnings!r}"
                )
        finally:
            pool.close()
