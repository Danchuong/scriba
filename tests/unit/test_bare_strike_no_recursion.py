"""hunt2-traceback-fuzz CRITICAL: bare-shape strike must never recurse.

d628b9b's bare-shape strike fallback called ``bounding_box()`` from inside
``emit_annotation_arrows``; ``bounding_box`` measures the exact annotation
extent by re-running the annotation emitters (base.py ``_measure_emit``),
re-entering the strike block — RecursionError on every primitive whose
``resolve_self_content_rects()`` is empty (13 of 22 types: Stack, Queue,
Deque, Tree, Forest, LinkedList, HashMap, NumberLine, Plane2D, CodePanel,
Bar, Equation, VariableWatch). The honest fallback is ``None`` → the
existing E1119 soft-drop warn (design-decorate.md's no-extent convention).
"""

from __future__ import annotations

import warnings

import pytest

from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.array import ArrayPrimitive


class TestBareStrikeNoRecursion:
    def test_stack_bare_strike_soft_drops_e1119(self) -> None:
        # The fuzz repro: Stack has no content rects -> must warn, not recurse.
        s = Stack("s", {"items": ["A", "B"], "max_visible": 2})
        s.set_annotations([{"target": "s", "strike": True}])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            svg = s.emit_svg()  # RecursionError before the fix
        assert svg
        assert "s-strike" not in svg
        assert any("E1119" in str(x.message) for x in w)

    def test_bounding_box_safe_with_bare_strike_annotation(self) -> None:
        # bounding_box() itself re-runs the emitters; it must also terminate.
        s = Stack("s", {"items": ["A"], "max_visible": 1})
        s.set_annotations([{"target": "s", "strike": True}])
        bb = s.bounding_box()
        assert bb.width > 0 and bb.height > 0

    def test_array_bare_strike_still_spans_content_box(self) -> None:
        # Regression guard: primitives WITH content rects keep the whole-shape
        # strike (the FIX 4 feature is unchanged where it worked).
        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        a.set_annotations([{"target": "a", "strike": True}])
        svg = a.emit_svg()
        assert "a-strike" in svg
