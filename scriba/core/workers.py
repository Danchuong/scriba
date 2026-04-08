"""SubprocessWorker and SubprocessWorkerPool.

One persistent subprocess per worker speaking JSON-line over stdin/stdout.
See ``docs/scriba/01-architecture.md`` §SubprocessWorkerPool for the locked
protocol.
"""

from __future__ import annotations


class SubprocessWorker:
    """One persistent subprocess speaking JSON-line over stdin/stdout.

    Supports both Node scripts (KaTeX: ``node katex_worker.js``) and native
    binaries (D2). Thread-safe via an internal lock: concurrent callers
    serialize through send().
    """

    def __init__(
        self,
        name: str,
        argv: list[str],
        *,
        ready_signal: str | None = None,
        max_requests: int = 50_000,
        default_timeout: float = 10.0,
    ) -> None:
        """Configure one subprocess worker spec.

        Args:
            name: Stable identifier, e.g. "katex" or "d2".
            argv: Full process command line.
            ready_signal: If not None, worker startup waits for this exact
                line on stderr before the worker is considered ready.
            max_requests: Respawn threshold. Default 50_000.
            default_timeout: Per-request read timeout in seconds.
        """
        raise NotImplementedError

    def send(self, request: dict, *, timeout: float | None = None) -> dict:
        """Send one JSON request, read one JSON response line.

        On BrokenPipeError / empty response / JSON decode failure, the
        worker is killed and WorkerError is raised. The next call
        transparently respawns the worker.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Graceful shutdown. Idempotent."""
        raise NotImplementedError


class SubprocessWorkerPool:
    """Named registry of SubprocessWorker instances, lazily spawned.

    One pool per Pipeline. Workers are keyed by name, e.g. "katex", "d2".
    """

    def __init__(self) -> None:
        raise NotImplementedError

    def register(
        self,
        name: str,
        argv: list[str],
        *,
        ready_signal: str | None = None,
        max_requests: int = 50_000,
        default_timeout: float = 10.0,
    ) -> None:
        """Register a worker spec. Does not spawn the process."""
        raise NotImplementedError

    def get(self, name: str) -> SubprocessWorker:
        """Return the worker, spawning it on first access.

        Raises KeyError if name was not registered.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Close every spawned worker. Idempotent."""
        raise NotImplementedError

    def __enter__(self) -> "SubprocessWorkerPool":
        raise NotImplementedError

    def __exit__(self, exc_type, exc, tb) -> None:
        raise NotImplementedError
