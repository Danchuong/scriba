"""Regression tests for bare-shape selector validation in the emitter.

Before Wave 5.2 the emitter's selector validator would emit a warning
for any target key that did not contain a ``.`` (e.g. ``stk``, ``pq``,
``G``) because the suffix-stripping logic left the bare shape name as
the suffix, which never matches an addressable part.

Bare shape ids are legitimate whole-primitive targets (used e.g. by
``\\apply{stk}{push=X}`` or ``\\recolor{pq}{state=done}``) and must not
warn.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import pytest

from scriba.animation.emitter import _validate_expanded_selectors


@dataclass
class _FakePrim:
    """Minimal primitive that only supports a known set of suffixes."""

    parts: list[str] = field(default_factory=lambda: ["cell[0]", "cell[1]", "all"])

    def addressable_parts(self) -> list[str]:
        return list(self.parts)

    def validate_selector(self, suffix: str) -> bool:
        return suffix in self.parts


class TestBareShapeSelectorSkipGuard:
    """``_validate_expanded_selectors`` must not warn on bare shape ids."""

    @pytest.mark.parametrize("shape_name", ["stk", "pq", "G"])
    def test_bare_shape_id_emits_no_warning(self, shape_name: str) -> None:
        prim = _FakePrim()
        # The bare shape id is the full target key — no ``.field`` suffix.
        expanded = {shape_name: {"state": "current"}}

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            _validate_expanded_selectors(expanded, shape_name, prim)

        matching = [
            w
            for w in captured
            if "does not match any addressable part" in str(w.message)
        ]
        assert matching == [], (
            f"Expected no selector warnings for bare shape id {shape_name!r}, "
            f"got: {[str(w.message) for w in matching]}"
        )

    def test_valid_suffix_still_passes(self) -> None:
        prim = _FakePrim()
        expanded = {"arr.cell[0]": {"state": "current"}}

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            _validate_expanded_selectors(expanded, "arr", prim)

        matching = [
            w
            for w in captured
            if "does not match any addressable part" in str(w.message)
        ]
        assert matching == []

    def test_invalid_suffix_still_warns(self) -> None:
        """The skip guard must not mask real invalid selectors."""
        prim = _FakePrim()
        expanded = {"arr.cell[99]": {"state": "current"}}

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            _validate_expanded_selectors(expanded, "arr", prim)

        matching = [
            w
            for w in captured
            if "does not match any addressable part" in str(w.message)
        ]
        assert len(matching) == 1
        assert "arr.cell[99]" in str(matching[0].message)

    def test_all_meta_selector_not_warned(self) -> None:
        prim = _FakePrim()
        expanded = {"arr.all": {"state": "done"}}

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            _validate_expanded_selectors(expanded, "arr", prim)

        matching = [
            w
            for w in captured
            if "does not match any addressable part" in str(w.message)
        ]
        assert matching == []
