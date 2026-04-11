"""Starlark worker subprocess — restricted Python evaluator.

Speaks JSON-line protocol over stdin/stdout.  Emits ready signal on stderr.

Usage::

    python -m scriba.animation.starlark_worker

Request format (``eval``)::

    {"op": "eval", "id": "req-1", "globals": {"h": [2,9,4]}, "source": "n = len(h)"}

Response (success)::

    {"id": "req-1", "ok": true, "bindings": {"n": 3, "h": [2,9,4]}, "debug": []}

Response (error)::

    {"id": "req-1", "ok": false, "code": "E1150", "message": "...", "line": null, "col": null}
"""

from __future__ import annotations

import ast
import json
import math
import signal
import sys
import threading
import traceback
import tracemalloc
from io import StringIO
from typing import Any

from scriba.animation.constants import BLOCKED_ATTRIBUTES, FORBIDDEN_BUILTINS

# ---------------------------------------------------------------------------
# AST literal limits (defence-in-depth against C-level bombs)
# ---------------------------------------------------------------------------

_MAX_INT_LITERAL = 10**7  # 10 million
_MAX_STR_LITERAL_LEN = 10_000  # characters

# ---------------------------------------------------------------------------
# Runtime range() limit
# ---------------------------------------------------------------------------

_MAX_RANGE_LEN = 10**6  # 1 million elements

# ---------------------------------------------------------------------------
# Security sets (imported from constants.py for centralization)
# ---------------------------------------------------------------------------

_BLOCKED_ATTRIBUTES = BLOCKED_ATTRIBUTES

# Forbidden AST node types (not plain strings, so kept here)
_FORBIDDEN_NODE_TYPES: tuple[type, ...] = (
    ast.Import,
    ast.ImportFrom,
    ast.While,
    ast.Try,
    ast.ClassDef,
    ast.Lambda,
)

_FORBIDDEN_BUILTINS = FORBIDDEN_BUILTINS

# Friendly names for forbidden AST nodes
_FORBIDDEN_NODE_NAMES: dict[type, str] = {
    ast.Import: "import",
    ast.ImportFrom: "import",
    ast.While: "while",
    ast.Try: "try",
    ast.ClassDef: "class",
    ast.Lambda: "lambda",
}


def _scan_ast(source: str) -> tuple[str, int | None, int | None] | None:
    """Walk the AST and reject forbidden node types and blocked attribute access.

    Returns ``(reason, line, col)`` on first violation, or *None* if clean.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Let the actual exec handle syntax errors with better messages.
        return None

    for node in ast.walk(tree):
        # Reject forbidden statement/expression types
        if isinstance(node, _FORBIDDEN_NODE_TYPES):
            name = _FORBIDDEN_NODE_NAMES.get(type(node), type(node).__name__)
            line = getattr(node, "lineno", None)
            col = getattr(node, "col_offset", None)
            if col is not None:
                col += 1  # 1-based
            return name, line, col

        # Reject access to blocked dunder attributes
        if isinstance(node, ast.Attribute) and node.attr in _BLOCKED_ATTRIBUTES:
            line = getattr(node, "lineno", None)
            col = getattr(node, "col_offset", None)
            if col is not None:
                col += 1
            return node.attr, line, col

        # Reject forbidden builtin names used as function calls
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_BUILTINS:
            line = getattr(node, "lineno", None)
            col = getattr(node, "col_offset", None)
            if col is not None:
                col += 1
            return node.id, line, col

        # Cap integer literals to prevent memory/CPU bombs like "x" * 10**8
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            if abs(node.value) > _MAX_INT_LITERAL:
                line = getattr(node, "lineno", None)
                col = getattr(node, "col_offset", None)
                if col is not None:
                    col += 1
                return (
                    f"integer literal too large (max {_MAX_INT_LITERAL})",
                    line,
                    col,
                )

        # Cap string literal length
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if len(node.value) > _MAX_STR_LITERAL_LEN:
                line = getattr(node, "lineno", None)
                col = getattr(node, "col_offset", None)
                if col is not None:
                    col += 1
                return (
                    f"string literal too long (max {_MAX_STR_LITERAL_LEN} chars)",
                    line,
                    col,
                )

    return None


# ---------------------------------------------------------------------------
# Allowed builtins for the restricted namespace
# ---------------------------------------------------------------------------

_CAPTURED_PRINTS: list[str] = []


def _make_print_fn(capture_list: list[str]):
    """Return a ``print()`` replacement that captures output."""

    def _print(*args: Any, **kwargs: Any) -> None:
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        buf = StringIO()
        buf.write(sep.join(str(a) for a in args))
        buf.write(end)
        capture_list.append(buf.getvalue().rstrip("\n"))

    return _print


def _safe_range(*args: int) -> range:
    """Wrapper around built-in ``range()`` that caps length to _MAX_RANGE_LEN."""
    for a in args:
        if abs(a) > _MAX_RANGE_LEN:
            raise ValueError(
                f"range() argument too large (max {_MAX_RANGE_LEN})"
            )
    r = range(*args)
    if len(r) > _MAX_RANGE_LEN:
        raise ValueError(
            f"range() would produce {len(r)} elements (max {_MAX_RANGE_LEN})"
        )
    return r


_ALLOWED_BUILTINS: dict[str, Any] = {
    # Types / constructors
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    # Constants
    "True": True,
    "False": False,
    "None": None,
    # Built-in functions
    "len": len,
    "range": _safe_range,
    "min": min,
    "max": max,
    "abs": abs,
    "sorted": sorted,
    "enumerate": enumerate,
    "zip": zip,
    "reversed": reversed,
    "any": any,
    "all": all,
    "sum": sum,
    "divmod": divmod,
    "repr": repr,
    "round": round,
    "chr": chr,
    "ord": ord,
    "pow": pow,
    "map": map,
    "filter": filter,
    # print is injected per-request with a fresh capture list
}


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize_value(value: Any, debug: list[str]) -> Any:
    """Convert a Python value to a JSON-compatible representation."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            debug.append(f"warning: {value!r} serialized as null")
            return None
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v, debug) for v in value]
    if isinstance(value, set):
        return [_serialize_value(v, debug) for v in sorted(value, key=str)]
    if isinstance(value, dict):
        return {
            str(k): _serialize_value(v, debug) for k, v in value.items()
        }
    if callable(value):
        # Functions cannot be JSON-serialized; skip them.
        return None
    debug.append(f"warning: value of type {type(value).__name__} serialized as null")
    return None


def _is_serializable_binding(key: str, value: Any) -> bool:
    """Return True if the binding should be included in the response."""
    if key.startswith("_"):
        return False
    if callable(value) and not isinstance(value, type):
        return False
    return True


# ---------------------------------------------------------------------------
# Timeout handler
# ---------------------------------------------------------------------------


class _TimeoutError(Exception):
    """Raised when a Starlark evaluation exceeds the wall-clock limit."""


class _StepCountExceededError(Exception):
    """E1153: Raised when Starlark execution exceeds the step count limit."""


def _timeout_handler(signum: int, frame: Any) -> None:
    raise _TimeoutError("evaluation timed out")


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

_WALL_CLOCK_SECONDS = 3


def _evaluate(
    source: str,
    caller_globals: dict[str, Any],
    request_id: str | None,
) -> dict[str, Any]:
    """Evaluate *source* in a restricted namespace and return a response dict."""
    debug: list[str] = []
    print_capture: list[str] = []

    # --- AST-based pre-parse scan ---
    forbidden = _scan_ast(source)
    if forbidden:
        reason, line, col = forbidden
        return {
            "id": request_id,
            "ok": False,
            "code": "E1154",
            "message": f"forbidden construct '{reason}' at line {line}",
            "line": line,
            "col": col,
        }

    # --- build restricted namespace ---
    namespace: dict[str, Any] = {"__builtins__": dict(_ALLOWED_BUILTINS)}
    namespace["__builtins__"]["print"] = _make_print_fn(print_capture)

    # Merge caller-provided globals (skip callable reconstructions).
    initial_keys: set[str] = set()
    for key, value in caller_globals.items():
        namespace[key] = value
        initial_keys.add(key)

    # --- execute ---
    has_alarm = hasattr(signal, "SIGALRM")
    old_handler = None

    # Set up step counter
    _step_local.count = 0
    _step_local.limit = _STEP_LIMIT

    try:
        if has_alarm:
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(_WALL_CLOCK_SECONDS)

        # Start tracemalloc for runtime memory checking
        _tracemalloc_was_tracing = tracemalloc.is_tracing()
        if not _tracemalloc_was_tracing:
            tracemalloc.start()

        old_trace = sys.gettrace()
        sys.settrace(_step_trace)
        try:
            exec(compile(source, "<compute>", "exec"), namespace)  # noqa: S102
        finally:
            sys.settrace(old_trace)
            if not _tracemalloc_was_tracing and tracemalloc.is_tracing():
                tracemalloc.stop()

        if has_alarm:
            signal.alarm(0)
    except _TimeoutError:
        return {
            "id": request_id,
            "ok": False,
            "code": "E1152",
            "message": f"evaluation timed out after {_WALL_CLOCK_SECONDS}s",
            "line": None,
            "col": None,
        }
    except SyntaxError as exc:
        if has_alarm:
            signal.alarm(0)
        return {
            "id": request_id,
            "ok": False,
            "code": "E1150",
            "message": f"parse error: {exc.msg}",
            "line": exc.lineno,
            "col": exc.offset,
        }
    except _StepCountExceededError:
        if has_alarm:
            signal.alarm(0)
        return {
            "id": request_id,
            "ok": False,
            "code": "E1153",
            "message": "step count exceeded",
            "line": None,
            "col": None,
        }
    except MemoryError as exc:
        if has_alarm:
            signal.alarm(0)
        msg = str(exc) if str(exc) else "memory limit exceeded"
        return {
            "id": request_id,
            "ok": False,
            "code": "E1155",
            "message": msg,
            "line": None,
            "col": None,
        }
    except Exception as exc:
        if has_alarm:
            signal.alarm(0)
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        # Filter traceback to only show lines from <compute>
        filtered = [
            line for line in tb_lines
            if "<compute>" in line or not line.startswith("  File")
        ]
        return {
            "id": request_id,
            "ok": False,
            "code": "E1151",
            "message": "".join(filtered).strip(),
            "line": None,
            "col": None,
        }
    finally:
        if has_alarm and old_handler is not None:
            signal.signal(signal.SIGALRM, old_handler)

    # --- extract bindings ---
    bindings: dict[str, Any] = {}
    for key, value in namespace.items():
        if key == "__builtins__":
            continue
        if not _is_serializable_binding(key, value):
            continue
        bindings[key] = _serialize_value(value, debug)

    return {
        "id": request_id,
        "ok": True,
        "bindings": bindings,
        "debug": print_capture,
    }


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


_STEP_LIMIT = 10**8
_STEP_LIMIT_FASTFORWARD = 10**9
_TRACEMALLOC_PEAK_LIMIT = 128 * 1024 * 1024  # 128 MB
_MEMORY_CHECK_INTERVAL = 1000  # check every N steps

# Thread-local step counter for sys.settrace
_step_local = threading.local()


def _step_trace(frame: Any, event: str, arg: Any) -> Any:
    """Trace function that counts execution steps and raises on overflow."""
    _step_local.count += 1
    if _step_local.count > _step_local.limit:
        raise _StepCountExceededError("step count exceeded")
    # Periodic memory check via tracemalloc (catches string multiplication etc.)
    if (
        _step_local.count % _MEMORY_CHECK_INTERVAL == 0
        and tracemalloc.is_tracing()
    ):
        _, peak = tracemalloc.get_traced_memory()
        if peak > _TRACEMALLOC_PEAK_LIMIT:
            raise MemoryError(
                f"E1155: peak memory {peak // (1024 * 1024)}MB "
                f"exceeds {_TRACEMALLOC_PEAK_LIMIT // (1024 * 1024)}MB limit"
            )
    return _step_trace


def main() -> None:
    """Entry point for the starlark worker subprocess.

    Resource limits (RLIMIT_AS/RLIMIT_DATA, RLIMIT_CPU) are set by the
    parent process via ``preexec_fn`` before this code runs.  See
    ``starlark_host._starlark_preexec``.
    """
    sys.stderr.flush()  # flush any logging output before ready signal

    sys.stderr.write("starlark-worker ready\n")
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = {
                "id": None,
                "ok": False,
                "code": "E1150",
                "message": f"malformed JSON request: {exc}",
                "line": None,
                "col": None,
            }
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        op = request.get("op", "eval")
        request_id = request.get("id")

        if op == "ping":
            response = {"ok": True, "status": "healthy"}
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        if op == "eval":
            caller_globals = request.get("globals", {})
            source = request.get("source", "")
            response = _evaluate(source, caller_globals, request_id)
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        # Unknown op
        response = {
            "id": request_id,
            "ok": False,
            "code": "E1150",
            "message": f"unknown op: {op!r}",
            "line": None,
            "col": None,
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
