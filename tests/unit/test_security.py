"""Security regression tests for hardened sandbox and primitive limits."""

from __future__ import annotations

import resource
import sys

import pytest

from scriba.animation.emitter import _escape_js
from scriba.animation.primitives.array import ArrayPrimitive
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
            MatrixPrimitive("m", {"rows": 101, "cols": 100})

    def test_matrix_accepts_max(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 100, "cols": 100})
        assert inst.rows == 100

    def test_numberline_rejects_oversized(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            NumberLinePrimitive("nl", {"domain": [0, 100], "ticks": 1001})

    def test_numberline_accepts_max(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 100], "ticks": 1000})
        assert inst.tick_count == 1000
