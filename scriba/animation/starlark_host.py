"""Starlark host wrapper — Python-side interface to the Starlark worker.

Wraps the persistent subprocess worker for use by AnimationRenderer and
DiagramRenderer.  Both renderers share a single ``"starlark"`` worker
registered in the Pipeline's ``SubprocessWorkerPool``.
"""

from __future__ import annotations

import logging
import platform
import sys
import time
import uuid
import warnings
from typing import Any

from scriba.core.errors import WorkerError
from scriba.core.workers import SubprocessWorkerPool
from scriba.animation import starlark_worker as _starlark_worker_module

logger = logging.getLogger(__name__)

# Module-level sentinel: ensures the Windows backstop-unavailable warning
# fires at most once per process, regardless of how many StarlarkHost
# instances are created.  Reset in tests via ``_reset_windows_warning()``.
_WINDOWS_WARNING_EMITTED = False


def _reset_windows_warning() -> None:
    """Test hook: clear the once-per-process Windows warning sentinel.

    Production code never calls this; it exists solely so the unit tests
    that assert the warning fires can run in any order without leaking
    state between cases.
    """
    global _WINDOWS_WARNING_EMITTED
    _WINDOWS_WARNING_EMITTED = False


def _maybe_emit_windows_warning() -> None:
    """Emit a one-shot ``RuntimeWarning`` on Windows about the missing
    wall-clock ``SIGALRM`` backstop.

    On Windows the Starlark sandbox cannot install a ``SIGALRM`` handler
    (the signal does not exist), so the only in-process runaway-loop
    defence is the step counter inside ``starlark_worker._step_trace``.
    A runaway C-extension builtin that does not tick the trace hook
    could in theory evade the step counter, in which case the host's
    10-second transport-level timeout remains as the outermost safety
    net.  See ``docs/spec/starlark-worker.md`` SS6.1.

    Threading.Timer fallback was deliberately not implemented because
    interrupting the main Python thread from a timer callback requires
    ``PyErr_SetInterrupt`` and introduces race conditions that are worse
    than the missing backstop itself.
    """
    global _WINDOWS_WARNING_EMITTED
    if _WINDOWS_WARNING_EMITTED:
        return
    if platform.system() != "Windows":
        return
    _WINDOWS_WARNING_EMITTED = True
    warnings.warn(
        "Scriba Starlark sandbox on Windows relies on step-counter only; "
        "wall-clock SIGALRM backstop unavailable. "
        "See `docs/spec/starlark-worker.md` SS6.1.",
        RuntimeWarning,
        stacklevel=3,
    )

# Resource limits applied to the starlark worker child process.
#
# Aligned with ``docs/spec/starlark-worker.md`` SS6 which promises a 64 MB
# memory cap. A prior drift allowed 256 MB at the RLIMIT level and 128 MB at
# the tracemalloc level, undermining the DoS guarantee the spec advertises.
_MEMORY_LIMIT_BYTES = 64 * 1024 * 1024  # 64 MB
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
        # One-shot platform warning: on Windows the wall-clock SIGALRM
        # backstop inside the worker is unavailable (the signal does not
        # exist), so only the step counter protects against runaway loops.
        # See ``docs/spec/starlark-worker.md`` SS6.1.
        _maybe_emit_windows_warning()
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
        # Track whether the cumulative budget has been reset for this
        # render session. Reset happens lazily on the first eval() call.
        self._budget_reset_done: bool = False

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
        # C1 fix: reset the cumulative budget on the first eval() call of
        # each StarlarkHost session so that budgets from a previous render
        # (sharing the same module-level state) do not bleed through.
        if not self._budget_reset_done:
            _starlark_worker_module.reset_cumulative_budget()
            self._budget_reset_done = True

        request_id = uuid.uuid4().hex[:10]
        request = {
            "op": "eval",
            "id": request_id,
            "globals": globals,
            "source": source,
        }

        worker = self._pool.get("starlark")
        t_start = time.monotonic()
        response = worker.send(request, timeout=timeout)
        elapsed = time.monotonic() - t_start

        if not response.get("ok", False):
            code = response.get("code", "E1151")
            message = response.get("message", "unknown starlark error")
            raise WorkerError(message, code=code)

        # C1 fix: charge the wall-clock time of this block against the
        # cumulative budget.  consume_cumulative_budget() raises an
        # AnimationError(E1152) when the total exceeds _CUMULATIVE_BUDGET_SECONDS.
        # Convert to WorkerError so callers get the same error type as other
        # sandbox violations.
        from scriba.core.errors import ScribaError  # avoid circular at module level
        try:
            _starlark_worker_module.consume_cumulative_budget(elapsed)
        except ScribaError as exc:
            raise WorkerError(
                exc._raw_message,
                code=getattr(exc, "code", "E1152") or "E1152",
            ) from exc

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

        .. deprecated::
            ``eval_raw`` has no internal callers and is not part of the
            stable Scriba public API.  It is scheduled for removal in a
            future release.  Use :meth:`eval` instead; if you need the
            raw worker response, file an issue describing your use-case.
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
