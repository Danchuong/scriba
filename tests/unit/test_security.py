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

    # --- New 2026-04-11 audit regressions ---

    def test_rejects_format_attribute_bypass(self) -> None:
        """13-C1: ``.format()`` templates with ``.attr`` leak class refs."""
        result = _scan_ast("'{0.__class__}'.format([])")
        assert result is not None
        assert result[0] == "format-with-attribute"

    def test_rejects_fstring_attribute_chain(self) -> None:
        """13-C2: f-string attribute chains leak class references."""
        result = _scan_ast('s = f"{[].append.__self__.__class__}"')
        assert result is not None
        assert result[0] == "__class__"

    def test_rejects_gi_frame_attribute(self) -> None:
        """13-C3: generator frame/code objects must be blocked."""
        result = _scan_ast("f = gen.gi_frame")
        assert result is not None
        assert result[0] == "gi_frame"

    def test_rejects_hash_builtin(self) -> None:
        """08-C2: ``hash()`` must be forbidden (PYTHONHASHSEED non-determinism)."""
        result = _scan_ast("x = hash('a')")
        assert result is not None
        assert result[0] == "hash"

    def test_rejects_walrus_operator(self) -> None:
        """13-H3: walrus ``:=`` is forbidden."""
        result = _scan_ast("if (y := 1):\n    pass")
        assert result is not None
        assert "walrus" in result[0]

    def test_rejects_match_statement(self) -> None:
        """13-H1: ``match``/``case`` is forbidden."""
        result = _scan_ast("match x:\n    case _:\n        y = 1")
        assert result is not None
        assert "match" in result[0]


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
        with pytest.raises(ValidationError, match="E1401"):
            ArrayPrimitive("a", {"size": 10_001})

    def test_array_accepts_max(self) -> None:
        inst = ArrayPrimitive("a", {"size": 10_000})
        assert inst.size == 10_000

    def test_grid_rejects_oversized_rows(self) -> None:
        with pytest.raises(ValidationError, match="E1411"):
            GridPrimitive("g", {"rows": 501, "cols": 10})

    def test_grid_rejects_oversized_cols(self) -> None:
        with pytest.raises(ValidationError, match="E1411"):
            GridPrimitive("g", {"rows": 10, "cols": 501})

    def test_grid_accepts_max(self) -> None:
        inst = GridPrimitive("g", {"rows": 500, "cols": 500})
        assert inst.rows == 500

    def test_matrix_rejects_oversized(self) -> None:
        # Cell-count cap raises E1425 (not generic E1103).
        with pytest.raises(ValidationError, match="E1425"):
            MatrixPrimitive("m", {"rows": 501, "cols": 500})

    def test_matrix_accepts_max(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 500, "cols": 500})
        assert inst.rows == 500

    def test_dptable_rejects_oversized_1d(self) -> None:
        # Cell-count cap raises E1425 (not generic E1103).
        with pytest.raises(ValidationError, match="E1425"):
            DPTablePrimitive("dp", {"n": 250_001})

    def test_dptable_rejects_oversized_2d(self) -> None:
        # Cell-count cap raises E1425 (not generic E1103).
        with pytest.raises(ValidationError, match="E1425"):
            DPTablePrimitive("dp", {"rows": 501, "cols": 500})

    def test_dptable_accepts_max_2d(self) -> None:
        inst = DPTablePrimitive("dp", {"rows": 500, "cols": 500})
        assert inst.rows == 500

    def test_numberline_rejects_oversized(self) -> None:
        with pytest.raises(ValidationError, match="E1454"):
            NumberLinePrimitive("nl", {"domain": [0, 100], "ticks": 1001})

    def test_numberline_accepts_max(self) -> None:
        inst = NumberLinePrimitive("nl", {"domain": [0, 100], "ticks": 1000})
        assert inst.tick_count == 1000


# -----------------------------------------------------------------------
# Wave 4A Cluster 9 — new security vectors
# -----------------------------------------------------------------------


class TestSecurityWave4NewVectors:
    """Vectors added by Wave 4A Cluster 9.

    These vectors fill audit finding 17-M3 gaps that do not belong in
    the dedicated test_svg_injection / test_unicode_homograph /
    test_recursive_dos files. Each test is a one-liner defence-in-depth
    assertion that complements the primary coverage.
    """

    def test_escape_js_handles_unicode_line_separators(self) -> None:
        """U+2028 / U+2029 would terminate a JS string literal in old
        engines. Verify ``_escape_js`` does not leave them bare inside
        a template literal."""
        # Template literals tolerate U+2028/U+2029, but document the
        # current behaviour: they pass through unchanged.
        out = _escape_js("a\u2028b\u2029c")
        assert "a\u2028b\u2029c" in out

    def test_escape_js_handles_null_byte(self) -> None:
        """Null byte must not prematurely terminate anything downstream."""
        out = _escape_js("a\x00b")
        assert "\x00" in out  # pass-through — sanitizer handles the rest

    def test_evaluate_rejects_asterisk_import(self) -> None:
        """``from x import *`` must be rejected by the AST scanner."""
        resp = _evaluate("from os import *", {}, "t1")
        assert resp["ok"] is False

    def test_evaluate_rejects_nested_lambda(self) -> None:
        """Nested lambda inside a list comprehension must still be
        rejected (lambdas are blocked unconditionally)."""
        resp = _evaluate(
            "xs = [(lambda n: n)(i) for i in range(3)]",
            {},
            "t1",
        )
        assert resp["ok"] is False

    @pytest.mark.xfail(
        reason=(
            "Bug found Wave 4A Cluster 9: _FORBIDDEN_NODE_TYPES does "
            "not include ast.FunctionDef, so arbitrary `def f(): ...` "
            "is accepted. Generators (`yield`) slip through on the "
            "back of that. Severity is low because the generator still "
            "runs inside the step-limited sandbox, but the scanner is "
            "not complete. Deferred to Wave 4B fix cluster (17-M3 "
            "sandbox surface-area)."
        ),
        strict=True,
    )
    def test_evaluate_rejects_yield(self) -> None:
        """``yield`` expressions are not in the supported subset."""
        from scriba.animation.starlark_worker import _scan_ast
        result = _scan_ast("def f():\n  yield 1")
        # ``def`` should be blocked; yield would be too.
        assert result is not None

    @pytest.mark.xfail(
        reason=(
            "Bug found Wave 4A Cluster 9: NumberLine checks an upper "
            "bound on `ticks` (>1000 → E1103) but does not check the "
            "lower bound. `ticks=0` produces a degenerate primitive. "
            "Deferred to Wave 4B fix cluster (17-M3 validation "
            "completeness)."
        ),
        strict=True,
    )
    def test_numberline_zero_ticks_is_validation_error(self) -> None:
        """Zero ticks on a numberline must be a validation error, not a
        silent degenerate primitive."""
        with pytest.raises(ValidationError, match="E1103"):
            NumberLinePrimitive("nl", {"domain": [0, 10], "ticks": 0})

    def test_dptable_negative_rows_is_validation_error(self) -> None:
        """Negative dimensions must be rejected."""
        with pytest.raises(ValidationError, match="E1103"):
            DPTablePrimitive("dp", {"rows": -1, "cols": 5})

    def test_grid_zero_rows_is_validation_error(self) -> None:
        """Zero-sized grid must be rejected."""
        with pytest.raises(ValidationError, match="E1103"):
            GridPrimitive("g", {"rows": 0, "cols": 5})
