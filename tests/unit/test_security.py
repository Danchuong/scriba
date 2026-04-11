"""Security regression tests for hardened sandbox and primitive limits."""

from __future__ import annotations

import resource
import sys

import pytest

from scriba.animation.emitter import _escape_js
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.animation.starlark_worker import _scan_ast, _evaluate
from scriba.core.errors import ValidationError


# -----------------------------------------------------------------------
# CRITICAL-1: AST-based sandbox hardening
# -----------------------------------------------------------------------


class TestSandboxAST:
    """Verify AST scanner rejects sandbox escape vectors."""

    def test_rejects_dunder_class_chain(self) -> None:
        result = _scan_ast("x = ''.__class__.__mro__[1].__subclasses__()")
        assert result is not None
        reason, _, _ = result
        # AST walker may hit any blocked attr first; all are in the chain
        assert reason in ("__class__", "__mro__", "__subclasses__")

    def test_rejects_dunder_globals(self) -> None:
        result = _scan_ast("f.__globals__['os']")
        assert result is not None
        assert "__globals__" in result[0]

    def test_rejects_dunder_builtins(self) -> None:
        result = _scan_ast("x.__builtins__")
        assert result is not None
        assert "__builtins__" in result[0]

    def test_rejects_import_statement(self) -> None:
        result = _scan_ast("import os")
        assert result is not None
        assert "import" in result[0]

    def test_rejects_from_import(self) -> None:
        result = _scan_ast("from os import path")
        assert result is not None
        assert "import" in result[0]

    def test_rejects_while_loop(self) -> None:
        result = _scan_ast("while True: pass")
        assert result is not None
        assert "while" in result[0]

    def test_rejects_lambda(self) -> None:
        result = _scan_ast("f = lambda x: x + 1")
        assert result is not None
        assert "lambda" in result[0]

    def test_rejects_class_def(self) -> None:
        result = _scan_ast("class Foo: pass")
        assert result is not None
        assert "class" in result[0]

    def test_rejects_try_except(self) -> None:
        result = _scan_ast("try:\n  x=1\nexcept:\n  pass")
        assert result is not None
        assert "try" in result[0]

    def test_rejects_eval_builtin(self) -> None:
        result = _scan_ast("eval('1+1')")
        assert result is not None
        assert "eval" in result[0]

    def test_allows_safe_code(self) -> None:
        result = _scan_ast("x = [1, 2, 3]\ny = len(x)")
        assert result is None

    def test_evaluate_rejects_class_chain(self) -> None:
        resp = _evaluate(
            "x = ''.__class__.__mro__[1].__subclasses__()", {}, "t1"
        )
        assert resp["ok"] is False
        assert resp["code"] == "E1154"


# -----------------------------------------------------------------------
# CRITICAL-2: Memory / ops limits
# -----------------------------------------------------------------------


class TestResourceLimits:
    """Verify memory and step-count limits are enforceable."""

    @pytest.mark.skipif(
        not hasattr(resource, "RLIMIT_AS"),
        reason="RLIMIT_AS not available on this platform",
    )
    def test_memory_limit_is_settable(self) -> None:
        """Verify RLIMIT_AS can be read (not necessarily set in test env)."""
        # Just confirm the constant exists and is callable
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        assert isinstance(soft, int)
        assert isinstance(hard, int)

    def test_step_counter_rejects_long_computation(self) -> None:
        """Verify the step counter mechanism works via _evaluate."""
        import scriba.animation.starlark_worker as sw

        # Temporarily lower the step limit to make the test fast
        original_limit = sw._STEP_LIMIT
        sw._STEP_LIMIT = 50
        try:
            resp = _evaluate("for i in range(10000): pass", {}, "step-test")
            # Should fail with step count exceeded (RuntimeError -> E1151)
            assert resp["ok"] is False
            assert "step count exceeded" in resp["message"] or "E1153" in resp["message"]
        finally:
            sw._STEP_LIMIT = original_limit


# -----------------------------------------------------------------------
# HIGH-1: innerHTML XSS via </script>
# -----------------------------------------------------------------------


class TestEscapeJS:
    """Verify _escape_js prevents script injection."""

    def test_escapes_closing_script_tag(self) -> None:
        assert "<\\/script>" in _escape_js("</script>")

    def test_escapes_closing_style_tag(self) -> None:
        assert "<\\/style>" in _escape_js("</style>")

    def test_escapes_backtick(self) -> None:
        assert "\\`" in _escape_js("`")

    def test_escapes_template_literal(self) -> None:
        assert "\\${" in _escape_js("${foo}")


# -----------------------------------------------------------------------
# HIGH-2: Primitive dimension caps
# -----------------------------------------------------------------------


class TestPrimitiveDimensionCaps:
    """Verify oversized primitives are rejected."""

    def test_array_rejects_oversized(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            ArrayPrimitive("a", {"size": 10_001})

    def test_array_accepts_max(self) -> None:
        inst = ArrayPrimitive("a", {"size": 10_000})
        assert inst.size == 10_000

    def test_grid_rejects_oversized_rows(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            GridPrimitive("g", {"rows": 501, "cols": 10})

    def test_grid_rejects_oversized_cols(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            GridPrimitive("g", {"rows": 10, "cols": 501})

    def test_grid_accepts_max(self) -> None:
        inst = GridPrimitive("g", {"rows": 500, "cols": 500})
        assert inst.rows == 500

    def test_matrix_rejects_oversized(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            MatrixPrimitive("m", {"rows": 501, "cols": 500})

    def test_matrix_accepts_max(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 500, "cols": 500})
        assert inst.rows == 500

    def test_dptable_rejects_oversized_1d(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            DPTablePrimitive("dp", {"n": 250_001})

    def test_dptable_rejects_oversized_2d(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            DPTablePrimitive("dp", {"rows": 501, "cols": 500})

    def test_dptable_accepts_max_2d(self) -> None:
        inst = DPTablePrimitive("dp", {"rows": 500, "cols": 500})
        assert inst.rows == 500

    def test_numberline_rejects_oversized(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            NumberLinePrimitive("nl", {"domain": [0, 100], "ticks": 1001})

    def test_numberline_accepts_max(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 100], "ticks": 1000})
        assert inst.tick_count == 1000


# -----------------------------------------------------------------------
# Wave 4B Cluster 2: Sandbox FunctionDef/Yield block + NumberLine ticks<1
# -----------------------------------------------------------------------


class TestSecurityWave4NewVectors:
    """Wave 4B C2 regression tests for sandbox yield/async and NumberLine ticks<1.

    Historical context: Wave 4A Cluster 9 flagged these as strict xfails. Wave 4B
    Cluster 2 closes them by (a) adding ``ast.Yield``/``ast.YieldFrom``/
    ``ast.AsyncFunctionDef``/``ast.Await`` to the sandbox forbidden-node set
    (``ast.walk`` recursion catches ``yield`` inside regular ``def``s without
    forbidding ``FunctionDef`` outright), and (b) adding a ``ticks < 1``
    validation check to ``NumberLinePrimitive``.
    """

    def test_evaluate_rejects_yield(self) -> None:
        """A ``def f(): yield 1`` payload must raise E1154 forbidden construct.

        Before Wave 4B C2, ``yield`` inside a ``def`` slipped the AST scanner
        because ``FunctionDef`` was allowed and ``Yield`` was not in the
        forbidden tuple.  Now ``ast.walk`` visits the nested ``Yield`` node
        during the pre-exec scan.
        """
        resp = _evaluate("def f():\n    yield 1\nresult = 0", {}, "yield-test")
        assert resp["ok"] is False
        assert resp["code"] == "E1154"
        assert "yield" in resp["message"]

    def test_numberline_zero_ticks_is_validation_error(self) -> None:
        """``ticks=0`` must raise E1103 rather than produce a degenerate primitive.

        Before Wave 4B C2, ``NumberLinePrimitive`` only clamped the upper bound
        (``ticks > 1000``) and silently accepted ``ticks=0``, producing a
        primitive with zero tick marks.
        """
        with pytest.raises(ValidationError, match="E1103"):
            NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 0})

    def test_numberline_negative_ticks_is_validation_error(self) -> None:
        """``ticks=-1`` is also caught by the lower-bound guard."""
        with pytest.raises(ValidationError, match="E1103"):
            NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": -1})

    def test_numberline_one_tick_boundary_accepted(self) -> None:
        """``ticks=1`` is the minimum accepted value — boundary regression."""
        inst = NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 1})
        assert inst.tick_count == 1

    def test_evaluate_rejects_yield_from(self) -> None:
        """``yield from`` inside a ``def`` must also be blocked."""
        resp = _evaluate(
            "def g():\n    yield from [1, 2, 3]\nresult = 0",
            {},
            "yield-from-test",
        )
        assert resp["ok"] is False
        assert resp["code"] == "E1154"
        assert "yield from" in resp["message"]

    def test_evaluate_rejects_async_def(self) -> None:
        """``async def`` must be rejected outright (no legitimate use)."""
        resp = _evaluate(
            "async def f():\n    pass\nresult = 0",
            {},
            "async-def-test",
        )
        assert resp["ok"] is False
        assert resp["code"] == "E1154"
        assert "async def" in resp["message"]

    def test_evaluate_rejects_bare_await(self) -> None:
        """``await`` is only syntactically legal inside an ``async`` scope,
        but the scanner still blocks it as a defence-in-depth measure."""
        # Wrap in async def since `await` is a syntax error at module scope.
        # Both forbidden nodes (AsyncFunctionDef and Await) will be caught;
        # whichever is visited first wins.
        resp = _evaluate(
            "async def f():\n    await f()\nresult = 0",
            {},
            "await-test",
        )
        assert resp["ok"] is False
        assert resp["code"] == "E1154"
        assert resp["message"] and (
            "await" in resp["message"] or "async def" in resp["message"]
        )

    def test_regular_def_still_allowed(self) -> None:
        """Sanity: plain ``def`` helper functions remain legal (cookbook 05/07/08
        and TestFunctionDef/TestRecursion rely on this)."""
        resp = _evaluate(
            "def double(x):\n    return x * 2\nresult = double(21)",
            {},
            "def-ok-test",
        )
        assert resp["ok"] is True
        assert resp["bindings"]["result"] == 42
