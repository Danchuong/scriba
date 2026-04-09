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

import json
import math
import re
import signal
import sys
import traceback
from io import StringIO
from typing import Any

# ---------------------------------------------------------------------------
# Forbidden-keyword scanner
# ---------------------------------------------------------------------------

_FORBIDDEN_KEYWORDS: tuple[str, ...] = (
    "while",
    "import",
    "load",
    "class",
    "lambda",
    "try",
    "except",
    "with",
    "yield",
    "async",
    "await",
    "global",
    "nonlocal",
)

_FORBIDDEN_BUILTINS: frozenset[str] = frozenset(
    {
        "exec",
        "eval",
        "__import__",
        "open",
        "compile",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "type",
        "object",
        "super",
        "classmethod",
        "staticmethod",
        "property",
        "breakpoint",
        "exit",
        "quit",
        "help",
        "input",
        "memoryview",
        "bytearray",
        "bytes",
    }
)

# Build a single regex that matches any forbidden keyword at a word boundary.
_FORBIDDEN_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in _FORBIDDEN_KEYWORDS) + r")\b"
)


def _scan_forbidden(source: str) -> tuple[str, int | None, int | None] | None:
    """Return ``(keyword, line, col)`` of the first forbidden keyword, or *None*."""
    for i, line in enumerate(source.splitlines(), start=1):
        # Strip comments so that ``# while`` does not trigger.
        code_part = line.split("#", 1)[0]
        m = _FORBIDDEN_PATTERN.search(code_part)
        if m:
            return m.group(1), i, m.start() + 1
    return None

    # Also reject forbidden builtin names used as function calls.
    # (e.g., ``eval("code")``, ``__import__("os")``).


def _scan_forbidden_builtins(source: str) -> tuple[str, int | None, int | None] | None:
    """Return ``(name, line, col)`` if source calls a forbidden builtin."""
    for i, line in enumerate(source.splitlines(), start=1):
        code_part = line.split("#", 1)[0]
        for name in _FORBIDDEN_BUILTINS:
            pattern = re.compile(r"\b" + re.escape(name) + r"\b")
            m = pattern.search(code_part)
            if m:
                return name, i, m.start() + 1
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
    "range": range,
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
    "isinstance": isinstance,
    "hash": hash,
    "repr": repr,
    "round": round,
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


def _timeout_handler(signum: int, frame: Any) -> None:
    raise _TimeoutError("evaluation timed out")


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

_WALL_CLOCK_SECONDS = 5


def _evaluate(
    source: str,
    caller_globals: dict[str, Any],
    request_id: str | None,
) -> dict[str, Any]:
    """Evaluate *source* in a restricted namespace and return a response dict."""
    debug: list[str] = []
    print_capture: list[str] = []

    # --- pre-parse scan ---
    forbidden = _scan_forbidden(source)
    if forbidden:
        kw, line, col = forbidden
        return {
            "id": request_id,
            "ok": False,
            "code": "E1154",
            "message": f"forbidden keyword '{kw}' at line {line}",
            "line": line,
            "col": col,
        }

    forbidden_builtin = _scan_forbidden_builtins(source)
    if forbidden_builtin:
        name, line, col = forbidden_builtin
        return {
            "id": request_id,
            "ok": False,
            "code": "E1154",
            "message": f"forbidden builtin '{name}' at line {line}",
            "line": line,
            "col": col,
        }

    # --- build restricted namespace ---
    namespace: dict[str, Any] = {"__builtins__": dict(_ALLOWED_BUILTINS)}
    namespace["__builtins__"]["print"] = _make_print_fn(print_capture)

    # Merge caller-provided globals (reconstruct __fn__ wrappers).
    initial_keys: set[str] = set()
    for key, value in caller_globals.items():
        if isinstance(value, dict) and "__fn__" in value:
            # Re-evaluate the function source to reconstruct the callable.
            fn_source = value["__fn__"]
            try:
                exec(fn_source, namespace)  # noqa: S102
            except Exception as exc:
                debug.append(
                    f"warning: failed to reconstruct function from __fn__: {exc}"
                )
        else:
            namespace[key] = value
        initial_keys.add(key)

    # --- execute ---
    has_alarm = hasattr(signal, "SIGALRM")
    old_handler = None
    try:
        if has_alarm:
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(_WALL_CLOCK_SECONDS)

        exec(compile(source, "<compute>", "exec"), namespace)  # noqa: S102

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
            # Serialize function definitions as __fn__ wrappers.
            if callable(value) and hasattr(value, "__name__"):
                # Try to extract the function source from the original source.
                fn_name = value.__name__
                # Look for the def in the source text.
                fn_source = _extract_function_source(source, fn_name)
                if fn_source is not None:
                    bindings[key] = {"__fn__": fn_source, "name": fn_name}
            continue
        bindings[key] = _serialize_value(value, debug)

    return {
        "id": request_id,
        "ok": True,
        "bindings": bindings,
        "debug": print_capture,
    }


def _extract_function_source(source: str, fn_name: str) -> str | None:
    """Extract the source text of a function definition from *source*."""
    lines = source.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(f"def {fn_name}(") or stripped.startswith(f"def {fn_name} ("):
            start = i
            break
    if start is None:
        return None

    # Collect the function body (indented lines after the def).
    result_lines = [lines[start]]
    # Determine the indentation of the def line.
    def_indent = len(lines[start]) - len(lines[start].lstrip())
    for j in range(start + 1, len(lines)):
        line = lines[j]
        if line.strip() == "":
            result_lines.append(line)
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent > def_indent:
            result_lines.append(line)
        else:
            break
    return "".join(result_lines).rstrip("\n")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the starlark worker subprocess."""
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
