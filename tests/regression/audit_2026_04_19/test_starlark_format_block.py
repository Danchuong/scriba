"""Regression tests for audit finding F-04 — Starlark format-bypass.

Audit finding: ``_scan_format_call`` in ``starlark_worker.py`` only
intercepted ``.format()`` calls on *string-literal* receivers.  A
variable-receiver form — ``fmt = "{0.__class__}"; fmt.format([])`` —
bypassed the check because the receiver is an ``ast.Name`` node, not an
``ast.Constant``.

Fix: ``_scan_format_call`` now rejects any ``.format()`` call whose
receiver is not a string literal.  This closes the variable-receiver
bypass while leaving safe literal-receiver calls (e.g.
``"{0}-{1}".format(a, b)``) untouched.

These tests call ``_scan_ast`` and ``_evaluate`` directly (in-process)
to verify the AST scanner catches the new pattern and that the evaluator
returns an E1154 sandbox error.
"""

from __future__ import annotations

import pytest

from scriba.animation.starlark_worker import _evaluate, _scan_ast


# ---------------------------------------------------------------------------
# F-04 — variable-receiver format bypass
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestStarlarkFormatVariableReceiverBlocked:
    """_scan_format_call must reject .format() on non-literal receivers.

    Audit finding F-04: ``fmt = "{0.__class__}"; fmt.format([])`` bypassed
    the literal-receiver guard and leaked class introspection at runtime.
    """

    def test_variable_receiver_format_rejected_by_scan_ast(self) -> None:
        """``fmt.format([])`` with a variable receiver must be caught by the AST scanner.

        The receiver is an ``ast.Name`` node — not a string literal — so the
        template cannot be inspected at parse time.  The scanner must reject
        the call regardless of what the variable might contain.
        """
        source = 'fmt = "{0.__class__}"; result = fmt.format([])'
        hit = _scan_ast(source)
        assert hit is not None, (
            "F-04: _scan_ast allowed .format() on a variable receiver. "
            "The AST scanner must reject non-literal receivers unconditionally."
        )
        reason, _line, _col = hit
        assert "format" in reason, (
            f"F-04: expected a 'format' related reason, got {reason!r}"
        )

    def test_variable_receiver_format_evaluate_returns_e1154(self) -> None:
        """The evaluator must return E1154 for the variable-receiver format call.

        Even if _scan_ast is bypassed, _evaluate wraps the AST scan so
        the same rejection must surface as a structured error response.
        """
        source = 'fmt = "{0.__class__}"; result = fmt.format([])'
        resp = _evaluate(source, {}, "f04-var-receiver")
        assert resp["ok"] is False, (
            "F-04: _evaluate returned ok=True for a variable-receiver "
            ".format() call.  Expected a sandbox rejection."
        )
        assert resp["code"] == "E1154", (
            f"F-04: expected error code E1154, got {resp['code']!r}"
        )

    def test_two_step_variable_receiver_blocked(self) -> None:
        """Multi-statement bypass where format string is built in a prior step."""
        source = (
            "template = '{0.__class__.__mro__}'\n"
            "result = template.format([])\n"
        )
        hit = _scan_ast(source)
        assert hit is not None, (
            "F-04: two-step variable-receiver bypass not caught by _scan_ast."
        )

    def test_variable_receiver_via_subscript_blocked(self) -> None:
        """``templates[0].format(x)`` — subscript receiver — must be blocked."""
        source = (
            "templates = ['{0.__class__}']\n"
            "result = templates[0].format([])\n"
        )
        hit = _scan_ast(source)
        assert hit is not None, (
            "F-04: subscript receiver .format() call not caught by _scan_ast."
        )

    # ------------------------------------------------------------------
    # Negative: safe literal-receiver calls must remain allowed.
    # ------------------------------------------------------------------

    def test_literal_receiver_without_attr_field_still_allowed(self) -> None:
        """``"{0}-{1}".format(a, b)`` has no attribute field — must be allowed.

        This is the non-regression guard: the F-04 fix must not block
        legitimate use of .format() with a safe string literal receiver.
        """
        source = "s = '{0}-{1}'.format('a', 'b')"
        hit = _scan_ast(source)
        assert hit is None, (
            f"F-04 regression: safe literal .format() call was blocked. "
            f"_scan_ast returned {hit!r}"
        )

    def test_literal_receiver_with_index_field_still_allowed(self) -> None:
        """``"{0[0]}".format([1,2])`` uses index access only — must be allowed."""
        source = "s = '{0[0]}'.format([1, 2])"
        hit = _scan_ast(source)
        assert hit is None, (
            f"F-04 regression: index-only literal .format() was blocked: {hit!r}"
        )

    def test_literal_receiver_with_attr_field_still_blocked(self) -> None:
        """``"{0.__class__}".format([])`` — literal receiver with attr field — blocked.

        This was already blocked before F-04.  Confirm it remains blocked
        after the fix (no regression on the original literal-receiver path).
        """
        source = "leaked = '{0.__class__}'.format([])"
        hit = _scan_ast(source)
        assert hit is not None, (
            "Pre-F-04 literal-receiver-with-attr check regressed: "
            "_scan_ast no longer catches it."
        )
        reason, _line, _col = hit
        assert "format" in reason
