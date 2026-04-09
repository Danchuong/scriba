"""Starlark host wrapper — Python-side interface to the Starlark worker.

Wraps the persistent subprocess worker for use by AnimationRenderer and
DiagramRenderer.  Both renderers share a single ``"starlark"`` worker
registered in the Pipeline's ``SubprocessWorkerPool``.
"""

from __future__ import annotations

import sys
import uuid
from typing import Any

from scriba.core.errors import WorkerError
from scriba.core.workers import SubprocessWorkerPool


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
            raise WorkerError(f"[{code}] {message}")

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
