"""Worker Protocol and subprocess-backed implementations.

Two concrete ``Worker`` implementations are provided:

* ``PersistentSubprocessWorker`` — one long-lived subprocess speaking
  JSON-line over stdin/stdout. Lazy-spawned, thread-safe, auto-recovers
  from crashes, restarted after ``max_requests`` successful sends.
* ``OneShotSubprocessWorker`` — spawns a fresh subprocess for every
  request. Useful for engines that cannot (or should not) be kept alive
  between calls. ``close()`` is a no-op.

``SubprocessWorker`` remains as a deprecated alias of
``PersistentSubprocessWorker`` for one release.

See ``docs/scriba/01-architecture.md`` §SubprocessWorkerPool for the
locked protocol.
"""

from __future__ import annotations

import json
import logging
import select
import subprocess
import sys
import threading
from typing import Callable, Literal, Optional, Protocol, runtime_checkable

from scriba.core.errors import WorkerError

logger = logging.getLogger(__name__)


@runtime_checkable
class Worker(Protocol):
    """Protocol every worker implementation satisfies."""

    name: str

    def send(
        self, request: dict, *, timeout: float | None = None
    ) -> dict: ...

    def close(self) -> None: ...


class PersistentSubprocessWorker:
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
        preexec_fn: Callable[[], None] | None = None,
    ) -> None:
        self._name = name
        self._argv = list(argv)
        self._ready_signal = ready_signal
        self._max_requests = max_requests
        self._default_timeout = default_timeout
        # preexec_fn is called in the child process before exec on Unix.
        # On Windows (where preexec_fn is not supported), pass None.
        self._preexec_fn = preexec_fn if sys.platform != "win32" else None
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
                preexec_fn=self._preexec_fn,
            )
        except FileNotFoundError as e:
            self._process = None
            raise WorkerError(
                f"failed to spawn worker {self._name!r}: {e}"
            ) from e

        self._request_count = 0

        if self._ready_signal is not None:
            assert self._process.stderr is not None
            import os
            fd = self._process.stderr.fileno()
            buf = b""
            deadline_iters = 0
            ready = False
            while deadline_iters < 200:  # ~10s with 0.05s slices
                if sys.platform == "win32":
                    line = self._process.stderr.readline()
                    if not line:
                        break
                    if self._ready_signal in line:
                        ready = True
                        break
                else:
                    # Use raw fd reads to avoid TextIOWrapper
                    # buffering that can make select() miss data.
                    r, _, _ = select.select([fd], [], [], 0.05)
                    if r:
                        chunk = os.read(fd, 4096)
                        if not chunk:
                            break
                        buf += chunk
                        if self._ready_signal.encode() in buf:
                            ready = True
                            break
                deadline_iters += 1
                if self._process.poll() is not None:
                    # Process exited; drain any remaining output.
                    try:
                        chunk = os.read(fd, 4096)
                        if chunk:
                            buf += chunk
                            if self._ready_signal.encode() in buf:
                                ready = True
                    except OSError:
                        pass
                    break

            if not ready:
                stderr_capture = self._drain_stderr()
                self._kill()
                raise WorkerError(
                    f"worker {self._name!r} did not report ready",
                    stderr=stderr_capture,
                )

    def _ensure_started(self) -> None:
        if self._closed:
            raise WorkerError(f"worker {self._name!r} is closed")

        if self._process is not None and self._process.poll() is None:
            if self._request_count < self._max_requests:
                return
            self._kill()

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
                except subprocess.TimeoutExpired as e:
                    logger.debug("worker cleanup: wait after kill: %s", e)
        except (OSError, ProcessLookupError) as e:
            logger.debug("worker cleanup: terminate failed: %s", e)
            try:
                proc.kill()
            except (OSError, ProcessLookupError) as e2:
                logger.debug("worker cleanup: kill failed: %s", e2)
        finally:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError as e:
                        logger.debug("worker cleanup: stream close: %s", e)
            self._process = None

    def _drain_stderr(self) -> str | None:
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
        except (OSError, ValueError) as e:
            logger.debug("worker drain_stderr: %s", e)
        return "".join(chunks) if chunks else None

    def close(self) -> None:
        """Graceful shutdown. Idempotent."""
        with self._lock:
            self._kill()
            self._closed = True

    # ----- send -----

    def send(self, request: dict, *, timeout: float | None = None) -> dict:
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

            if sys.platform != "win32":
                try:
                    r, _, _ = select.select(
                        [proc.stdout], [], [], effective_timeout
                    )
                except (OSError, ValueError) as e:
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

    def __enter__(self) -> "PersistentSubprocessWorker":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


# Backward-compatible alias for ``PersistentSubprocessWorker``. Access via
# ``from scriba.core.workers import SubprocessWorker`` emits a
# :class:`DeprecationWarning` when invoked from outside scriba's own
# package — scriba-internal imports are silenced so first-party code does
# not spam end users. See ``STABILITY.md`` §Deprecation policy.
def __getattr__(name: str):  # PEP 562 module-level attribute access hook
    if name == "SubprocessWorker":
        import sys
        import warnings

        caller_module = ""
        try:
            caller_module = sys._getframe(1).f_globals.get("__name__", "")
        except ValueError:  # pragma: no cover - defensive
            caller_module = ""

        is_internal = caller_module == "scriba" or caller_module.startswith(
            "scriba."
        )
        if not is_internal:
            warnings.warn(
                "SubprocessWorker is a deprecated alias for "
                "PersistentSubprocessWorker and will be removed in 0.2.0. "
                "Import PersistentSubprocessWorker instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return PersistentSubprocessWorker
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


class OneShotSubprocessWorker:
    """Spawn a fresh subprocess for each request.

    The request is written as a single JSON line on stdin, then stdin is
    closed. The response is read as a single JSON line from stdout. The
    subprocess is expected to exit on its own.
    """

    def __init__(
        self,
        name: str,
        argv: list[str],
        *,
        default_timeout: float = 10.0,
    ) -> None:
        self._name = name
        self._argv = list(argv)
        self._default_timeout = default_timeout
        self._closed = False

    @property
    def name(self) -> str:
        return self._name

    def send(self, request: dict, *, timeout: float | None = None) -> dict:
        if self._closed:
            raise WorkerError(f"worker {self._name!r} is closed")
        effective_timeout = (
            timeout if timeout is not None else self._default_timeout
        )
        line = json.dumps(request, ensure_ascii=False) + "\n"
        try:
            proc = subprocess.Popen(
                self._argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as e:
            raise WorkerError(
                f"failed to spawn worker {self._name!r}: {e}"
            ) from e

        try:
            stdout_data, stderr_data = proc.communicate(
                input=line, timeout=effective_timeout
            )
        except subprocess.TimeoutExpired as e:
            try:
                proc.kill()
            except (OSError, ProcessLookupError) as ke:
                logger.debug("oneshot worker cleanup: %s", ke)
            raise WorkerError(
                f"worker {self._name!r} timeout after "
                f"{effective_timeout:.3f}s"
            ) from e

        first = (stdout_data or "").strip().splitlines()
        if not first:
            raise WorkerError(
                f"worker {self._name!r} produced no output",
                stderr=stderr_data or None,
            )
        try:
            return json.loads(first[0])
        except json.JSONDecodeError as e:
            raise WorkerError(
                f"worker {self._name!r} invalid JSON response: {e}",
                stderr=stderr_data or None,
            ) from e

    def close(self) -> None:
        self._closed = True


class SubprocessWorkerPool:
    """Named registry of ``Worker`` instances, lazily spawned.

    One pool per Pipeline. Workers are keyed by name, e.g. "katex", "d2".
    Workers may be registered either by spec (``register(name, argv, ...)``)
    or directly via the convenience overload accepting a pre-built worker.
    """

    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}
        self._lock = threading.Lock()
        self._closed = False

    def register(
        self,
        name: str,
        argv: list[str] | None = None,
        *,
        mode: Literal["persistent", "oneshot"] = "persistent",
        ready_signal: str | None = None,
        max_requests: int = 50_000,
        default_timeout: float = 10.0,
        preexec_fn: Callable[[], None] | None = None,
        worker: Worker | None = None,
    ) -> None:
        """Register a worker.

        Either pass ``argv`` (and optional kwargs) so the pool builds the
        worker, or pass a pre-built ``worker``. ``mode`` selects the
        subprocess strategy when building from ``argv``.

        If a worker with the same name is already registered, this is a
        no-op (idempotent). See PHASE2_DECISIONS.md D-16.
        """
        with self._lock:
            if self._closed:
                raise WorkerError("pool is closed")
            if name in self._workers:
                return
            if worker is not None:
                self._workers[name] = worker
                return
            if argv is None:
                raise ValueError(
                    "register() requires either argv or worker"
                )
            if mode == "persistent":
                self._workers[name] = PersistentSubprocessWorker(
                    name,
                    argv,
                    ready_signal=ready_signal,
                    max_requests=max_requests,
                    default_timeout=default_timeout,
                    preexec_fn=preexec_fn,
                )
            elif mode == "oneshot":
                self._workers[name] = OneShotSubprocessWorker(
                    name, argv, default_timeout=default_timeout
                )
            else:  # pragma: no cover - defensive
                raise ValueError(f"unknown worker mode: {mode!r}")

    def get(self, name: str) -> Worker:
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
                except Exception as e:  # noqa: BLE001 - defensive cleanup
                    logger.debug("pool close: %s", e)
            self._workers.clear()
            self._closed = True

    def __enter__(self) -> "SubprocessWorkerPool":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
