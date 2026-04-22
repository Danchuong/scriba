"""Unit tests for scriba.animation.primitives._protocol.

Tests cover:
- PrimitiveProtocol structural interface.
- @register_primitive: silent registration when all 6 methods present.
- @register_primitive: warning (not exception) when methods missing.
- get_registered_primitives() returns expected list.
"""

from __future__ import annotations

import warnings
from typing import Callable

import pytest

from scriba.animation.primitives._protocol import (
    PrimitiveProtocol,
    _REQUIRED_PROTOCOL_METHODS,
    _find_missing_methods,
    get_registered_primitives,
    register_primitive,
)


# ---------------------------------------------------------------------------
# Fixtures: minimal compliant and non-compliant primitive stubs
# ---------------------------------------------------------------------------


def _make_full_primitive(name: str = "FullPrimitive") -> type:
    """Return a class that implements all required protocol methods.

    Includes the six original §5.1 methods plus the two obstacle-geometry
    accessors added in v0.12.0 prep (resolve_obstacle_boxes,
    resolve_obstacle_segments).
    """

    def resolve_annotation_point(self, selector: str):
        return (0.0, 0.0)

    def emit_svg(self, *, placed_labels=None, render_inline_tex=None):
        return ""

    def annotation_headroom_above(self) -> float:
        return 0.0

    def annotation_headroom_below(self) -> float:
        return 0.0

    def register_decorations(self, registry) -> None:
        pass

    def dispatch_annotations(self, placed_labels, *, render_inline_tex=None):
        return []

    def resolve_obstacle_boxes(self) -> list:
        return []

    def resolve_obstacle_segments(self) -> list:
        return []

    return type(name, (), {
        "resolve_annotation_point": resolve_annotation_point,
        "emit_svg": emit_svg,
        "annotation_headroom_above": annotation_headroom_above,
        "annotation_headroom_below": annotation_headroom_below,
        "register_decorations": register_decorations,
        "dispatch_annotations": dispatch_annotations,
        "resolve_obstacle_boxes": resolve_obstacle_boxes,
        "resolve_obstacle_segments": resolve_obstacle_segments,
    })


def _make_partial_primitive(name: str, missing: list[str]) -> type:
    """Return a class missing the specified methods from the full set."""
    cls = _make_full_primitive(name)
    for m in missing:
        if hasattr(cls, m):
            delattr(cls, m)
    return cls


# ---------------------------------------------------------------------------
# PrimitiveProtocol structural checks
# ---------------------------------------------------------------------------


class TestPrimitiveProtocol:
    def test_protocol_has_all_six_required_methods(self):
        """PrimitiveProtocol declares exactly the six required method names."""
        protocol_members = {
            name for name in dir(PrimitiveProtocol)
            if not name.startswith("_")
        }
        assert _REQUIRED_PROTOCOL_METHODS.issubset(protocol_members)

    def test_full_primitive_satisfies_protocol(self):
        """A class with all six methods is recognised as an instance of PrimitiveProtocol."""
        FullPrim = _make_full_primitive()
        instance = FullPrim()
        assert isinstance(instance, PrimitiveProtocol)

    def test_partial_primitive_fails_isinstance(self):
        """A class missing any method is not an isinstance of PrimitiveProtocol."""
        PartialPrim = _make_partial_primitive("Partial", ["dispatch_annotations"])
        instance = PartialPrim()
        assert not isinstance(instance, PrimitiveProtocol)


# ---------------------------------------------------------------------------
# _find_missing_methods helper
# ---------------------------------------------------------------------------


class TestFindMissingMethods:
    def test_no_missing_for_full_class(self):
        FullPrim = _make_full_primitive()
        assert _find_missing_methods(FullPrim) == set()

    def test_reports_single_missing_method(self):
        PartialPrim = _make_partial_primitive("P1", ["annotation_headroom_above"])
        missing = _find_missing_methods(PartialPrim)
        assert missing == {"annotation_headroom_above"}

    def test_reports_multiple_missing_methods(self):
        PartialPrim = _make_partial_primitive(
            "P2", ["register_decorations", "dispatch_annotations"]
        )
        missing = _find_missing_methods(PartialPrim)
        assert missing == {"register_decorations", "dispatch_annotations"}

    def test_inherited_methods_count_as_present(self):
        """Methods defined on a base class count as present via MRO."""
        Base = _make_full_primitive("Base")
        Child = type("Child", (Base,), {})
        assert _find_missing_methods(Child) == set()


# ---------------------------------------------------------------------------
# @register_primitive decorator — advisory (warn-on-register) mode
# ---------------------------------------------------------------------------


class TestRegisterPrimitive:
    def _fresh_module_state(self):
        """Return a fresh reference to _REGISTERED_PRIMITIVES for isolation."""
        from scriba.animation.primitives import _protocol as proto_mod
        # Snapshot the list length before the test so we can check relative additions.
        return len(proto_mod._REGISTERED_PRIMITIVES)

    def test_full_primitive_registers_silently(self):
        """All six methods present → no warning, class added to registry."""
        FullPrim = _make_full_primitive("SilentPrim")
        before = self._fresh_module_state()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = register_primitive(FullPrim)

        assert result is FullPrim, "Decorator must return the class unchanged"
        assert not any("PrimitiveProtocol" in str(warning.message) for warning in w), (
            "No warning expected for a fully conformant class"
        )
        after = self._fresh_module_state()
        assert after == before + 1

    def test_partial_primitive_warns_but_registers(self):
        """Missing method → warning emitted, but class is still registered."""
        PartialPrim = _make_partial_primitive(
            "PartialPrimWarn", ["annotation_headroom_above"]
        )
        before = self._fresh_module_state()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = register_primitive(PartialPrim)

        assert result is PartialPrim, "Decorator must return the class unchanged"
        # Check warning was emitted
        protocol_warnings = [
            x for x in w if "PrimitiveProtocol" in str(x.message)
        ]
        assert len(protocol_warnings) >= 1, (
            "Expected at least one PrimitiveProtocol warning for partial class"
        )
        # Check the missing method name appears in the warning text
        warning_text = str(protocol_warnings[0].message)
        assert "annotation_headroom_above" in warning_text

        # Still registered despite missing method
        after = self._fresh_module_state()
        assert after == before + 1

    def test_multiple_missing_methods_all_listed_in_warning(self):
        """Warning text includes all missing method names."""
        PartialPrim = _make_partial_primitive(
            "MultiMissingPrim",
            ["annotation_headroom_above", "annotation_headroom_below", "dispatch_annotations"],
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            register_primitive(PartialPrim)

        protocol_warnings = [
            x for x in w if "PrimitiveProtocol" in str(x.message)
        ]
        assert protocol_warnings, "Expected at least one warning"
        warning_text = str(protocol_warnings[0].message)
        assert "annotation_headroom_above" in warning_text
        assert "annotation_headroom_below" in warning_text
        assert "dispatch_annotations" in warning_text

    def test_decorator_does_not_raise(self):
        """register_primitive MUST NOT raise even for fully non-conformant class."""
        EmptyPrim = type("EmptyPrim", (), {})
        try:
            register_primitive(EmptyPrim)
        except Exception as exc:
            pytest.fail(
                f"register_primitive raised {type(exc).__name__} in advisory mode: {exc}"
            )


# ---------------------------------------------------------------------------
# get_registered_primitives()
# ---------------------------------------------------------------------------


class TestGetRegisteredPrimitives:
    def test_returns_list(self):
        result = get_registered_primitives()
        assert isinstance(result, list)

    def test_registered_class_appears_in_list(self):
        UniquePrim = _make_full_primitive("UniquePrimForListTest")
        register_primitive(UniquePrim)
        result = get_registered_primitives()
        assert UniquePrim in result

    def test_returns_snapshot_copy(self):
        """Mutating the returned list must not affect the internal registry."""
        result1 = get_registered_primitives()
        result1.clear()
        result2 = get_registered_primitives()
        assert len(result2) > 0, (
            "Internal registry should be unaffected by clearing the returned copy"
        )

    def test_partial_class_also_appears_in_list(self):
        """Advisory mode means even non-conformant classes are registered."""
        PartialPrim = _make_partial_primitive("PartialInListPrim", ["dispatch_annotations"])
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            register_primitive(PartialPrim)
        result = get_registered_primitives()
        assert PartialPrim in result
