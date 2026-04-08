"""SubprocessWorker and SubprocessWorkerPool.

One persistent subprocess per worker speaking JSON-line over stdin/stdout.
See ``docs/scriba/01-architecture.md`` §SubprocessWorkerPool for the locked
protocol.
"""

from __future__ import annotations

import json
import select
import subprocess
import sys
import threading
from typing import Optional

from scriba.core.errors import WorkerError


class SubprocessWorker:
    """One persistent subprocess speaking JSON-line over stdin/stdout.

    Lazy-spawn: subprocess is not created until the first ``send()`` call.
    Thread-safe via an internal lock. Crashes between calls are recovered
    transparently on the next ``send()``. After ``max_requests`` successful
    sends, the worker is restarted to bound memory.
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
        self._name = name
        self._argv = list(argv)
        self._ready_signal = ready_signal
        self._max_requests = max_requests
        self._default_timeout = default_timeout
        self._process: Optional[subprocess.Popen] = None
        self._request_count = 0
        self._lock = threading.Lock()
        self._closed = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def request_count(self) -> int:
        return self._request_count

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    # ----- lifecycle -----

    def _spawn(self) -> None:
        """Spawn the subprocess and wait for ready signal if configured."""
        try:
            self._process = subprocess.Popen(
                self._argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as e:
            self._process = None
            raise WorkerError(
                f"failed to spawn worker {self._name!r}: {e}"
            ) from e

        self._request_count = 0

        if self._ready_signal is not None:
            assert self._process.stderr is not None
            deadline_iters = 0
            ready = False
            # Read stderr lines until we see the ready signal or timeout.
            while deadline_iters < 200:  # ~10s with 0.05s slices
                if sys.platform == "win32":
                    line = self._process.stderr.readline()
                    if not line:
                        break
                    if self._ready_signal in line:
                        ready = True
                        break
                else:
                    r, _, _ = select.select(
                        [self._process.stderr], [], [], 0.05
                    )
                    if r:
                        line = self._process.stderr.readline()
                        if not line:
                            break
                        if self._ready_signal in line:
                            ready = True
                            break
                deadline_iters += 1
                if self._process.poll() is not None:
                    break

            if not ready:
                stderr_capture = self._drain_stderr()
                self._kill()
                raise WorkerError(
                    f"worker {self._name!r} did not report ready",
                    stderr=stderr_capture,
                )

    def _ensure_started(self) -> None:
        """Spawn the worker if needed (lazy/restart/recover)."""
        if self._closed:
            raise WorkerError(f"worker {self._name!r} is closed")

        if self._process is not None and self._process.poll() is None:
            if self._request_count < self._max_requests:
                return
            # Restart due to max requests reached.
            self._kill()

        # Either never started, died, or just killed for max-requests.
        self._spawn()

    def _kill(self) -> None:
        """Kill the worker process. Idempotent."""
        proc = self._process
        if proc is None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        finally:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
            self._process = None

    def _drain_stderr(self) -> str | None:
        """Best-effort non-blocking stderr capture for error reporting."""
        proc = self._process
        if proc is None or proc.stderr is None:
            return None
        chunks: list[str] = []
        try:
            if sys.platform == "win32":
                return None
            while True:
                r, _, _ = select.select([proc.stderr], [], [], 0.0)
                if not r:
                    break
                line = proc.stderr.readline()
                if not line:
                    break
                chunks.append(line)
        except Exception:
            pass
        return "".join(chunks) if chunks else None

    def close(self) -> None:
        """Graceful shutdown. Idempotent."""
        with self._lock:
            self._kill()
            self._closed = True

    # ----- send -----

    def send(self, request: dict, *, timeout: float | None = None) -> dict:
        """Send one JSON request, read one JSON response line.

        On crash/timeout/decode error the worker is killed and ``WorkerError``
        is raised; the next call respawns transparently.
        """
        with self._lock:
            self._ensure_started()
            assert self._process is not None
            proc = self._process
            assert proc.stdin is not None and proc.stdout is not None

            effective_timeout = (
                timeout if timeout is not None else self._default_timeout
            )

            try:
                line = json.dumps(request, ensure_ascii=False) + "\n"
                proc.stdin.write(line)
                proc.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                stderr = self._drain_stderr()
                self._kill()
                raise WorkerError(
                    f"worker {self._name!r} pipe error on write: {e}",
                    stderr=stderr,
                ) from e

            # Read response with timeout (Unix only via select).
            if sys.platform != "win32":
                try:
                    r, _, _ = select.select(
                        [proc.stdout], [], [], effective_timeout
                    )
                except Exception as e:
                    self._kill()
                    raise WorkerError(
                        f"worker {self._name!r} select failed: {e}"
                    ) from e
                if not r:
                    stderr = self._drain_stderr()
                    self._kill()
                    raise WorkerError(
                        f"worker {self._name!r} timeout after "
                        f"{effective_timeout:.3f}s",
                        stderr=stderr,
                    )

            try:
                response_line = proc.stdout.readline()
            except (OSError, ValueError) as e:
                stderr = self._drain_stderr()
                self._kill()
                raise WorkerError(
                    f"worker {self._name!r} read error: {e}",
                    stderr=stderr,
                ) from e

            if not response_line:
                stderr = self._drain_stderr()
                self._kill()
                raise WorkerError(
                    f"worker {self._name!r} closed unexpectedly "
                    "(empty response)",
                    stderr=stderr,
                )

            try:
                response = json.loads(response_line)
            except json.JSONDecodeError as e:
                stderr = self._drain_stderr()
                self._kill()
                raise WorkerError(
                    f"worker {self._name!r} invalid JSON response: {e}",
                    stderr=stderr,
                ) from e

            self._request_count += 1
            return response

    def __enter__(self) -> "SubprocessWorker":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class SubprocessWorkerPool:
    """Named registry of SubprocessWorker instances, lazily spawned.

    One pool per Pipeline. Workers are keyed by name, e.g. "katex", "d2".
    Workers may be registered either by spec (``register(name, argv, ...)``)
    or directly via the convenience overload accepting a pre-built worker.
    """

    def __init__(self) -> None:
        self._workers: dict[str, SubprocessWorker] = {}
        self._lock = threading.Lock()
        self._closed = False

    def register(
        self,
        name: str,
        argv: list[str] | None = None,
        *,
        ready_signal: str | None = None,
        max_requests: int = 50_000,
        default_timeout: float = 10.0,
        worker: SubprocessWorker | None = None,
    ) -> None:
        """Register a worker. Either pass ``argv`` (and optional kwargs) so
        the pool builds the worker, or pass a pre-built ``worker``.

        If a worker with the same name is already registered, this is a
        no-op (idempotent) when the new spec is functionally compatible.
        See PHASE2_DECISIONS.md D-16.
        """
        with self._lock:
            if self._closed:
                raise WorkerError("pool is closed")
            if name in self._workers:
                # Idempotent: silently ignore duplicate registration.
                return
            if worker is not None:
                self._workers[name] = worker
            else:
                if argv is None:
                    raise ValueError(
                        "register() requires either argv or worker"
                    )
                self._workers[name] = SubprocessWorker(
                    name,
                    argv,
                    ready_signal=ready_signal,
                    max_requests=max_requests,
                    default_timeout=default_timeout,
                )

    def get(self, name: str) -> SubprocessWorker:
        """Return the registered worker. Raises KeyError if missing."""
        with self._lock:
            if name not in self._workers:
                raise KeyError(name)
            return self._workers[name]

    def close(self) -> None:
        """Close every registered worker. Idempotent."""
        with self._lock:
            for w in self._workers.values():
                try:
                    w.close()
                except Exception:
                    pass
            self._workers.clear()
            self._closed = True

    def __enter__(self) -> "SubprocessWorkerPool":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
