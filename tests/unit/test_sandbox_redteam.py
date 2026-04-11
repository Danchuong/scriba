"""Red-team regression tests for the Starlark sandbox.

These tests encode the three critical and three high escape vectors
surfaced by the 2026-04-11 production audit (reports 08 and 13), plus the
related hardening directives (memory-limit alignment, explicit recursion
cap, determinism-preserving set ordering, ``hash()`` builtin removal,
walrus/match node rejection, and range-overflow E-code wrapping).

Every test exercises :func:`scriba.animation.starlark_worker._evaluate`
or :func:`_scan_ast` in-process rather than spawning a subprocess — we
care about the behaviour of the evaluator, not the JSON wire.
"""

from __future__ import annotations

import pytest

import scriba.animation.starlark_worker as sw
from scriba.animation.constants import (
    BLOCKED_ATTRIBUTES,
    FORBIDDEN_BUILTINS,
)
from scriba.animation.starlark_worker import _evaluate, _scan_ast


# ---------------------------------------------------------------------------
# 08-C1 / 08-C2 — memory + determinism hardening
# ---------------------------------------------------------------------------


class TestMemoryLimitAlignment:
    """Finding 08-C1: tracemalloc cap must match spec SS6 (64 MB)."""

    def test_tracemalloc_limit_is_64mb(self) -> None:
        assert sw._TRACEMALLOC_PEAK_LIMIT == 64 * 1024 * 1024

    def test_tracemalloc_limit_not_greater_than_host_rlimit(self) -> None:
        # If the tracemalloc cap ever exceeded the OS-level cap, the
        # soft check would be unreachable.
        from scriba.animation import starlark_host

        assert sw._TRACEMALLOC_PEAK_LIMIT <= starlark_host._MEMORY_LIMIT_BYTES


class TestHashBuiltinForbidden:
    """Finding 08-C2: ``hash()`` must be in FORBIDDEN_BUILTINS."""

    def test_hash_listed_in_forbidden_builtins(self) -> None:
        assert "hash" in FORBIDDEN_BUILTINS

    def test_hash_call_rejected_at_ast_scan(self) -> None:
        result = _scan_ast("x = hash('abc')")
        assert result is not None
        reason, _line, _col = result
        assert reason == "hash"

    def test_evaluate_rejects_hash(self) -> None:
        resp = _evaluate("x = hash(1)", {}, "hash-test")
        assert resp["ok"] is False
        assert resp["code"] == "E1154"
        assert "hash" in resp["message"]


# ---------------------------------------------------------------------------
# 13-C1 — .format() string-based attribute access bypass
# ---------------------------------------------------------------------------


class TestFormatAttributeBypass:
    """Finding 13-C1: ``'{0.attr}'.format(x)`` must be rejected."""

    def test_format_with_positional_attribute_rejected(self) -> None:
        source = "leaked = '{0.append.__self__.__class__}'.format([])"
        result = _scan_ast(source)
        assert result is not None
        assert result[0] == "format-with-attribute"

    def test_format_with_named_attribute_rejected(self) -> None:
        source = "leaked = '{x.append}'.format(x=[])"
        result = _scan_ast(source)
        assert result is not None
        assert result[0] == "format-with-attribute"

    def test_format_without_attribute_allowed(self) -> None:
        # Plain ``.format(...)`` without a ``.attr`` field is fine.
        source = "s = '{0}-{1}'.format('a', 'b')"
        assert _scan_ast(source) is None

    def test_format_with_index_only_allowed(self) -> None:
        source = "s = '{0[0]}'.format([1, 2, 3])"
        assert _scan_ast(source) is None

    def test_evaluate_rejects_format_attribute(self) -> None:
        resp = _evaluate(
            "leaked = '{0.__class__}'.format([])", {}, "fmt-test"
        )
        assert resp["ok"] is False
        assert resp["code"] == "E1154"
        assert "format-with-attribute" in resp["message"]


# ---------------------------------------------------------------------------
# 13-C2 — recursive dunder scan in attribute chains
# ---------------------------------------------------------------------------


class TestRecursiveAttributeChainScan:
    """Finding 13-C2: attribute chains must be walked for dunder names."""

    def test_rejects_chain_ending_in_class(self) -> None:
        result = _scan_ast("x = [].append.__self__.__class__")
        assert result is not None
        reason, _line, _col = result
        assert reason == "__class__"

    def test_rejects_fstring_attribute_chain(self) -> None:
        # The audit-reported vector: f-string that builds an attribute
        # chain ending in __class__.
        result = _scan_ast('s = f"{[].append.__self__.__class__}"')
        assert result is not None
        assert result[0] == "__class__"

    def test_rejects_deeply_nested_dunder(self) -> None:
        source = "y = obj.a.b.c.d.__globals__"
        result = _scan_ast(source)
        assert result is not None
        assert result[0] == "__globals__"

    def test_rejects_intermediate_dunder_in_chain(self) -> None:
        # ``__dict__`` in the middle of a chain still blocks.
        source = "z = obj.foo.__dict__.bar"
        result = _scan_ast(source)
        assert result is not None
        assert result[0] == "__dict__"

    def test_allows_safe_attribute_chain(self) -> None:
        # Plain method chain with no dunder is fine.
        source = "x = 'a'.upper().lower()"
        assert _scan_ast(source) is None


# ---------------------------------------------------------------------------
# 13-C3 — generator / coroutine / async-generator frame introspection
# ---------------------------------------------------------------------------


class TestGeneratorCoroutineIntrospection:
    """Finding 13-C3: gi_*/cr_*/ag_* must be in BLOCKED_ATTRIBUTES."""

    @pytest.mark.parametrize(
        "name",
        [
            "gi_frame",
            "gi_code",
            "gi_yieldfrom",
            "gi_running",
            "cr_frame",
            "cr_code",
            "cr_running",
            "cr_await",
            "ag_frame",
            "ag_code",
        ],
    )
    def test_attribute_is_blocked(self, name: str) -> None:
        assert name in BLOCKED_ATTRIBUTES

    def test_gi_frame_access_rejected(self) -> None:
        source = (
            "def g():\n"
            "    yield 1\n"
            "gen = g()\n"
            "frame = gen.gi_frame"
        )
        resp = _evaluate(source, {}, "gi-test")
        assert resp["ok"] is False
        assert resp["code"] == "E1154"
        assert "gi_frame" in resp["message"]

    def test_gi_code_chain_rejected(self) -> None:
        source = "x = obj.gi_code"
        result = _scan_ast(source)
        assert result is not None
        assert result[0] == "gi_code"


# ---------------------------------------------------------------------------
# 08-M1 — additional dunder getter/setter blocks
# ---------------------------------------------------------------------------


class TestDunderGetterSetterBlocks:
    """Finding 08-M1: operator-overloading dunders must be blocked."""

    @pytest.mark.parametrize(
        "name",
        [
            "__class_getitem__",
            "__format__",
            "__getattr__",
            "__getattribute__",
            "__set_name__",
            "__init_subclass__",
        ],
    )
    def test_attribute_is_blocked(self, name: str) -> None:
        assert name in BLOCKED_ATTRIBUTES

    def test_format_dunder_rejected(self) -> None:
        resp = _evaluate("x = ''.__format__('')", {}, "fmt-dunder")
        assert resp["ok"] is False
        assert resp["code"] == "E1154"

    def test_getattribute_rejected(self) -> None:
        resp = _evaluate("x = [].__getattribute__('append')", {}, "ga")
        assert resp["ok"] is False
        assert resp["code"] == "E1154"


# ---------------------------------------------------------------------------
# 13-H1 / 13-H3 — walrus + match node rejection
# ---------------------------------------------------------------------------


class TestWalrusAndMatchForbidden:
    """Findings 13-H1 (match) and 13-H3 (walrus): rejected at AST scan."""

    def test_walrus_rejected(self) -> None:
        result = _scan_ast("x = [1, 2]\nif (n := len(x)):\n    pass")
        assert result is not None
        assert "walrus" in result[0]

    def test_walrus_in_comprehension_rejected(self) -> None:
        result = _scan_ast("xs = [y for y in [1, 2, 3] if (y2 := y * 2)]")
        assert result is not None
        assert "walrus" in result[0]

    def test_match_rejected(self) -> None:
        source = "match x:\n    case 1:\n        y = 'one'\n    case _:\n        y = 'other'"
        result = _scan_ast(source)
        assert result is not None
        assert "match" in result[0]

    def test_evaluate_rejects_walrus(self) -> None:
        resp = _evaluate("if (z := 5):\n    y = z", {}, "walrus-test")
        assert resp["ok"] is False
        assert resp["code"] == "E1154"
        assert "walrus" in resp["message"]


# ---------------------------------------------------------------------------
# 08-M3 — set serialization tie-break
# ---------------------------------------------------------------------------


class TestSetSerializationDeterminism:
    """Finding 08-M3: set elements with equal ``str()`` must still be stable."""

    def test_set_with_duplicate_str_is_stable(self) -> None:
        # Pick values whose ``str()`` may collide across types.  Using
        # ``(str, repr)`` as key makes ordering fully deterministic.
        debug: list[str] = []
        result = sw._serialize_value({1, True, 0, False}, debug)
        # Python treats ``1 == True`` and ``0 == False`` at set level, so
        # the actual set has two members.  We just assert the output
        # order is stable on successive calls.
        second = sw._serialize_value({1, True, 0, False}, debug)
        assert result == second


# ---------------------------------------------------------------------------
# 08-M2 — explicit recursion-limit constant surfaced
# ---------------------------------------------------------------------------


class TestRecursionLimitConstant:
    """Finding 08-M2: spec promise of 1000 frames is locked in a constant."""

    def test_recursion_limit_constant_matches_spec(self) -> None:
        assert sw._RECURSION_DEPTH_LIMIT == 1000


# ---------------------------------------------------------------------------
# 05-C2 — ``_safe_range`` must surface an E-code, not bare ValueError
# ---------------------------------------------------------------------------


class TestSafeRangeErrorCode:
    """Finding 05-C2: range overflows must emit E1173, not bare ValueError."""

    def test_range_arg_too_large_raises_animation_error(self) -> None:
        from scriba.animation.errors import AnimationError

        with pytest.raises(AnimationError) as exc_info:
            sw._safe_range(10**7)
        assert exc_info.value.code == "E1173"

    def test_evaluate_range_overflow_returns_e1173(self) -> None:
        resp = _evaluate("xs = list(range(10**7))", {}, "range-test")
        assert resp["ok"] is False
        assert resp["code"] == "E1173"
        assert "range" in resp["message"]


# ---------------------------------------------------------------------------
# 13-M1 / 13-M3 — intentional allowances (smoke tests for spec drift)
# ---------------------------------------------------------------------------


class TestIntentionallyAllowed:
    """Findings 13-M1 (isinstance) and 13-M3 (.send()): intentionally allowed.

    These tests guard against over-zealous future hardening that would
    silently break compute ergonomics.  If they fail, update the spec
    first and only then change the sandbox.
    """

    def test_isinstance_allowed(self) -> None:
        resp = _evaluate("x = isinstance(42, int)", {}, "ii")
        assert resp["ok"] is True
        assert resp["bindings"]["x"] is True
