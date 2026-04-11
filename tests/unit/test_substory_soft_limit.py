"""Substory boundary / soft-limit regression tests.

Covers audit finding 16-L1 — behaviour at the edges of the
``\\substory`` feature: depth boundaries, empty substories, missing
closers, and interaction with ``\\foreach``.

Written Wave 4A Cluster 9 to cover 16-L1 + 17-M3 residuals.  Update
when:

* ``_MAX_SUBSTORY_DEPTH`` in ``scriba/animation/parser/grammar.py``
  changes.
* The forbidden-inside-foreach rule is relaxed.

The existing ``tests/unit/test_substory.py`` covers the happy paths
and the headline E1360..E1368 error codes.  This file fills in the
soft-limit / boundary gaps.
"""

from __future__ import annotations

import warnings

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.core.errors import ValidationError


def _parse(source: str):
    return SceneParser().parse(source)


class TestSubstoryDepthBoundary:
    """\\substory depth at, under, and over the limit."""

    def test_depth_1_works(self) -> None:
        """One level of substory is allowed."""
        ir = _parse(
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\narrate{one level}\n"
            "\\endsubstory\n"
        )
        sub = ir.frames[0].substories[0]
        assert len(sub.frames) == 1

    def test_depth_3_works_at_limit(self) -> None:
        """Three levels (the documented maximum) parse without error."""
        ir = _parse(
            "\\step\n"
            "\\substory\n"  # depth 1
            "\\step\n"
            "\\substory\n"  # depth 2
            "\\step\n"
            "\\substory\n"  # depth 3
            "\\step\n"
            "\\narrate{deepest}\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
        )
        outer = ir.frames[0].substories[0]
        middle = outer.frames[0].substories[0]
        inner = middle.frames[0].substories[0]
        assert inner.frames[0].narrate_body == "deepest"

    def test_depth_4_rejected_with_e1360(self) -> None:
        """Four levels exceed the limit and must raise E1360 (not E1170
        which is the foreach depth code)."""
        src = (
            "\\step\n"
            "\\substory\n"  # 1
            "\\step\n"
            "\\substory\n"  # 2
            "\\step\n"
            "\\substory\n"  # 3
            "\\step\n"
            "\\substory\n"  # 4 → error
            "\\step\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1360"):
            _parse(src)


class TestSubstoryClosers:
    """Missing or misplaced \\endsubstory."""

    def test_unclosed_substory_raises_e1361(self) -> None:
        src = (
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\narrate{body}\n"
        )
        with pytest.raises(ValidationError, match="E1361"):
            _parse(src)

    def test_unclosed_inner_substory_raises_e1361(self) -> None:
        """Outer substory is closed but inner is not."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\substory\n"  # inner — never closed
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1361"):
            _parse(src)


class TestSubstoryZeroFrames:
    """Substory with no inner \\step is a warning, not an error."""

    def test_empty_substory_warns_e1366(self) -> None:
        """A substory with zero inner frames emits the E1366 warning
        (Agent 05 flagged this — the code exists and IS raised)."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\endsubstory\n"
        )
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            ir = _parse(src)
            messages = [str(w.message) for w in captured]
        assert any("E1366" in m for m in messages), (
            f"expected E1366 warning, got: {messages}"
        )
        sub = ir.frames[0].substories[0]
        assert len(sub.frames) == 0


class TestSubstoryInsideForeach:
    """\\substory is forbidden inside \\foreach (E1172)."""

    def test_substory_inside_foreach_raises_e1172(self) -> None:
        src = (
            "\\step\n"
            "\\foreach{i}{0..2}\n"
            "\\substory\n"
            "\\step\n"
            "\\endsubstory\n"
            "\\endforeach\n"
        )
        with pytest.raises(ValidationError, match="E1172"):
            _parse(src)

    def test_foreach_inside_substory_is_allowed(self) -> None:
        """The reverse direction (foreach inside substory) must work
        because foreach is a per-frame mutation expander and the
        substory just hosts frames."""
        src = (
            "\\shape{a}{Array}{size=5}\n"
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\foreach{i}{0..2}\n"
            "\\highlight{a.cell[0]}\n"
            "\\endforeach\n"
            "\\endsubstory\n"
        )
        ir = _parse(src)
        assert ir.frames[0].substories[0].frames
