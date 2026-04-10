"""Starlark host wrapper — Python-side interface to the Starlark worker.

Wraps the persistent subprocess worker for use by AnimationRenderer and
DiagramRenderer.  Both renderers share a single ``"starlark"`` worker
registered in the Pipeline's ``SubprocessWorkerPool``.
"""

from __future__ import annotations

import logging
import sys
import uuid
from typing import Any

from scriba.core.errors import WorkerError
from scriba.core.workers import SubprocessWorkerPool

logger = logging.getLogger(__name__)

# Resource limits applied to the starlark worker child process.
_MEMORY_LIMIT_BYTES = 256 * 1024 * 1024  # 256 MB
_CPU_LIMIT_SECONDS = 5


def _starlark_preexec() -> None:
    """Set OS-level resource limits in the child process before exec.

    Called via ``preexec_fn`` on Unix only (skipped on Windows).

    * **Linux**: ``RLIMIT_AS`` caps virtual address space.
    * **macOS/Darwin**: ``RLIMIT_AS`` silently fails, so we use
      ``RLIMIT_DATA`` instead to cap heap allocation.
    * **Both**: ``RLIMIT_CPU`` enforces a hard CPU-time ceiling
      independent of the wall-clock SIGALRM inside the worker.
    """
    import resource  # import here — only needed in the child

    # Memory limit
    if sys.platform == "linux":
        try:
            resource.setrlimit(
                resource.RLIMIT_AS,
                (_MEMORY_LIMIT_BYTES, _MEMORY_LIMIT_BYTES),
            )
        except (ValueError, OSError):
            logger.debug("RLIMIT_AS not supported; memory limit not enforced")
    elif sys.platform == "darwin":
        try:
            resource.setrlimit(
                resource.RLIMIT_DATA,
                (_MEMORY_LIMIT_BYTES, _MEMORY_LIMIT_BYTES),
            )
        except (ValueError, OSError):
            logger.debug("RLIMIT_DATA not supported; memory limit not enforced")

    # CPU time limit (works on both Linux and macOS)
    try:
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (_CPU_LIMIT_SECONDS, _CPU_LIMIT_SECONDS),
        )
    except (ValueError, OSError):
        logger.debug("RLIMIT_CPU not supported; CPU time limit not enforced")


class StarlarkHost:
    """High-level interface to the Starlark evaluation worker.

    Usage::

        pool = SubprocessWorkerPool()
        host = StarlarkHost(pool)
        bindings = host.eval({"h": [2, 9, 4]}, "n = len(h)")
        # bindings == {"n": 3, "h": [2, 9, 4]}
        host.close()
    """

    def __init__(self, worker_pool: SubprocessWorkerPool) -> None:
        worker_pool.register(
            name="starlark",
            argv=[sys.executable, "-m", "scriba.animation.starlark_worker"],
            mode="persistent",
            ready_signal="starlark-worker ready",
            max_requests=50_000,
            default_timeout=10.0,
            preexec_fn=_starlark_preexec,
        )
        self._pool = worker_pool

    def eval(
        self,
        globals: dict[str, Any],
        source: str,
        *,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """Execute Starlark *source* with *globals* and return new bindings.

        Parameters
        ----------
        globals:
            Key-value map of bindings to pre-populate before execution.
        source:
            The Starlark source code to evaluate.
        timeout:
            Transport-level timeout in seconds (default 5.0).  The worker
            also enforces a 5 s wall-clock alarm internally.

        Returns
        -------
        dict
            The ``bindings`` dict from the worker response.

        Raises
        ------
        WorkerError
            On transport failure, timeout, or if the worker returns an
            error response.
        """
        request_id = uuid.uuid4().hex[:10]
        request = {
            "op": "eval",
            "id": request_id,
            "globals": globals,
            "source": source,
        }

        worker = self._pool.get("starlark")
        response = worker.send(request, timeout=timeout)

        if not response.get("ok", False):
            code = response.get("code", "E1151")
            message = response.get("message", "unknown starlark error")
            raise WorkerError(message, code=code)

        return response.get("bindings", {})

    def eval_raw(
        self,
        globals: dict[str, Any],
        source: str,
        *,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """Like :meth:`eval` but returns the full worker response dict.

        Useful when the caller needs access to ``debug`` output or wants
        to inspect the ``ok`` field without catching exceptions.
        """
        request_id = uuid.uuid4().hex[:10]
        request = {
            "op": "eval",
            "id": request_id,
            "globals": globals,
            "source": source,
        }

        worker = self._pool.get("starlark")
        return worker.send(request, timeout=timeout)

    def ping(self, *, timeout: float = 5.0) -> bool:
        """Send a health-check ping. Returns True if the worker is healthy."""
        worker = self._pool.get("starlark")
        try:
            response = worker.send({"op": "ping"}, timeout=timeout)
            return response.get("ok", False)
        except WorkerError:
            return False

    def close(self) -> None:
        """Shut down the starlark worker via the pool."""
        try:
            worker = self._pool.get("starlark")
            worker.close()
        except KeyError:
            pass

    def __enter__(self) -> StarlarkHost:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
