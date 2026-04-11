"""Tests for the Starlark worker subprocess.

Each test spawns the worker as a subprocess and communicates via
stdin/stdout JSON-line protocol.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

import pytest

_WORKER_ARGV = [sys.executable, "-m", "scriba.animation.starlark_worker"]


def _spawn_worker() -> subprocess.Popen:
    proc = subprocess.Popen(
        _WORKER_ARGV,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=str(
            __import__("pathlib").Path(__file__).resolve().parents[2]
        ),
    )
    # Wait for ready signal on stderr.
    ready_line = proc.stderr.readline()
    assert "starlark-worker ready" in ready_line
    return proc


def _send(proc: subprocess.Popen, request: dict[str, Any]) -> dict[str, Any]:
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    assert line, "worker produced no output"
    return json.loads(line)


def _close(proc: subprocess.Popen) -> None:
    proc.stdin.close()
    proc.wait(timeout=5)


# ---- Tests ----


class TestBasicEval:
    def test_len_builtin(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t1",
                "globals": {"h": [1, 2, 3]},
                "source": "n = len(h)",
            })
            assert resp["ok"] is True
            assert resp["bindings"]["n"] == 3
            assert resp["bindings"]["h"] == [1, 2, 3]
        finally:
            _close(proc)

    def test_arithmetic(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t2",
                "globals": {"a": 10, "b": 3},
                "source": "c = a + b\nd = a * b",
            })
            assert resp["ok"] is True
            assert resp["bindings"]["c"] == 13
            assert resp["bindings"]["d"] == 30
        finally:
            _close(proc)


class TestFunctionDef:
    def test_function_def_skipped_in_bindings(self):
        """Functions are serialized as __fn__ wrappers, not as values."""
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t3",
                "globals": {},
                "source": "def f(x):\n    return x * 2\nresult = f(5)",
            })
            assert resp["ok"] is True
            assert resp["bindings"]["result"] == 10
            # Functions are no longer serialized (__fn__ removed for security)
            assert "f" not in resp["bindings"]
        finally:
            _close(proc)


class TestRecursion:
    def test_recursive_function(self):
        proc = _spawn_worker()
        try:
            source = (
                "def fib(n):\n"
                "    if n <= 1:\n"
                "        return n\n"
                "    return fib(n - 1) + fib(n - 2)\n"
                "result = fib(10)"
            )
            resp = _send(proc, {
                "op": "eval",
                "id": "t4",
                "globals": {},
                "source": source,
            })
            assert resp["ok"] is True
            assert resp["bindings"]["result"] == 55
        finally:
            _close(proc)


class TestTimeout:
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="SIGALRM not available on Windows",
    )
    def test_long_running_code_times_out(self):
        proc = _spawn_worker()
        try:
            # Use nested loops within safe range limits to trigger timeout/step limit.
            resp = _send(proc, {
                "op": "eval",
                "id": "t5",
                "globals": {"n": 10**9},
                "source": "x = 0\nfor i in range(n):\n    x += 1",
            })
            assert resp["ok"] is False
            # May hit range iterable validation (E1173 — ``_safe_range``
            # now wraps its ValueError in an ``animation_error``),
            # timeout (E1152), or step limit (E1153).
            assert resp["code"] in ("E1152", "E1153", "E1173")
        finally:
            _close(proc)


class TestForbiddenKeywords:
    def test_while_forbidden(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t6",
                "globals": {},
                "source": "while True:\n    pass",
            })
            assert resp["ok"] is False
            assert resp["code"] == "E1154"
            assert "while" in resp["message"]
        finally:
            _close(proc)

    def test_import_forbidden(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t7",
                "globals": {},
                "source": "import os",
            })
            assert resp["ok"] is False
            assert resp["code"] == "E1154"
            assert "import" in resp["message"]
        finally:
            _close(proc)

    def test_class_forbidden(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t8",
                "globals": {},
                "source": "class Foo:\n    pass",
            })
            assert resp["ok"] is False
            assert resp["code"] == "E1154"
            assert "class" in resp["message"]
        finally:
            _close(proc)

    def test_lambda_forbidden(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t9",
                "globals": {},
                "source": "f = lambda x: x + 1",
            })
            assert resp["ok"] is False
            assert resp["code"] == "E1154"
            assert "lambda" in resp["message"]
        finally:
            _close(proc)

    def test_substring_not_flagged(self):
        """Keywords as substrings of identifiers should NOT be flagged."""
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t10",
                "globals": {},
                "source": "meanwhile = 3\nclassifier = 5",
            })
            assert resp["ok"] is True
            assert resp["bindings"]["meanwhile"] == 3
            assert resp["bindings"]["classifier"] == 5
        finally:
            _close(proc)


class TestListComprehension:
    def test_list_comprehension(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t11",
                "globals": {},
                "source": "result = [x * 2 for x in range(5)]",
            })
            assert resp["ok"] is True
            assert resp["bindings"]["result"] == [0, 2, 4, 6, 8]
        finally:
            _close(proc)


class TestDictOperations:
    def test_dict_mutation(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t12",
                "globals": {},
                "source": 'd = {"a": 1}\nd["b"] = 2',
            })
            assert resp["ok"] is True
            assert resp["bindings"]["d"] == {"a": 1, "b": 2}
        finally:
            _close(proc)


class TestPrintCapture:
    def test_print_captured_in_debug(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {
                "op": "eval",
                "id": "t13",
                "globals": {},
                "source": 'print("hello")\nprint("world")\nx = 42',
            })
            assert resp["ok"] is True
            assert resp["bindings"]["x"] == 42
            assert resp["debug"] == ["hello", "world"]
        finally:
            _close(proc)


class TestPing:
    def test_ping_response(self):
        proc = _spawn_worker()
        try:
            resp = _send(proc, {"op": "ping"})
            assert resp["ok"] is True
            assert resp["status"] == "healthy"
        finally:
            _close(proc)


class TestMalformedInput:
    def test_malformed_json(self):
        proc = _spawn_worker()
        try:
            assert proc.stdin is not None
            assert proc.stdout is not None
            proc.stdin.write("not valid json\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            resp = json.loads(line)
            assert resp["ok"] is False
            assert resp["code"] == "E1150"
        finally:
            _close(proc)


class TestMultipleRequests:
    def test_sequential_requests(self):
        """Worker handles multiple sequential requests correctly."""
        proc = _spawn_worker()
        try:
            resp1 = _send(proc, {
                "op": "eval",
                "id": "seq-1",
                "globals": {},
                "source": "a = 1",
            })
            resp2 = _send(proc, {
                "op": "eval",
                "id": "seq-2",
                "globals": {},
                "source": "b = 2",
            })
            assert resp1["ok"] is True
            assert resp1["bindings"]["a"] == 1
            assert resp2["ok"] is True
            assert resp2["bindings"]["b"] == 2
            # Verify statelessness: resp2 should NOT have 'a'
            assert "a" not in resp2["bindings"]
        finally:
            _close(proc)
