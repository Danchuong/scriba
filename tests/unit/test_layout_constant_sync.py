"""Constant-parity registry — registered twins may never drift (FP-3).

Two live bugs shipped exactly this way (fp3-duplicated-constants.md):
- B-1: plane2d's hand-rolled ``len * 7`` char width vs the canonical
  ``estimate_text_width`` (6.2/char Latin at 10px) — under-sizes CJK pills.
- B-2: graph's ``_WEIGHT_PILL_* = 5/2/3`` vs the canonical
  ``_LABEL_PILL_* = 6/3/4`` — an earlier FP-3 pass reconciled the same
  lineage in plane2d and skipped graph.

Rows opt IN by being registered here, so the coincidental look-alikes
(the five distinct ``_PADDING`` values, stack-vs-grid cell sizes, the
axis-font 10s) can never false-positive. Registered-equal today = a
lock-in; registered-unequal = a reproduced bug.
"""

from __future__ import annotations

from scriba.animation.primitives import _svg_helpers as svg
from scriba.animation.primitives import _types as types_
from scriba.animation.primitives import array, base, dptable, graph, linkedlist
from scriba.animation.primitives._text_render import estimate_text_width, line_box_h


class TestPillMetricsParity:
    def test_weight_pill_matches_label_pill(self) -> None:
        # B-2 — RED until graph imports the canonical pill metrics
        assert graph._WEIGHT_PILL_PAD_X == svg._LABEL_PILL_PAD_X
        assert graph._WEIGHT_PILL_PAD_Y == svg._LABEL_PILL_PAD_Y
        assert graph._WEIGHT_PILL_R == svg._LABEL_PILL_RADIUS


class TestFontTokenParity:
    def test_caption_font_single_source(self) -> None:
        # C3 — one primitive-label token (CSS --scriba-label-font)
        assert base._CAPTION_FONT_PX == svg.LABEL_FONT_PX
        assert array._FONT_SIZE_CAPTION == svg.LABEL_FONT_PX
        assert dptable._FONT_SIZE_CAPTION == svg.LABEL_FONT_PX

    def test_annotation_font_single_source(self) -> None:
        # C4 — one annotation token (CSS --scriba-annotation-font);
        # deliberately a DIFFERENT symbol from LABEL_FONT_PX even though
        # both are 11 today — the two CSS vars may diverge
        assert graph._WEIGHT_FONT == svg._DEFAULT_LABEL_FONT_PX

    def test_index_font_single_source(self) -> None:
        # C5
        assert array._FONT_SIZE_INDEX == types_.INDEX_FONT_PX
        assert dptable._FONT_SIZE_INDEX == types_.INDEX_FONT_PX

    def test_index_offset_single_source(self) -> None:
        # C6
        assert linkedlist._INDEX_LABEL_OFFSET == types_.INDEX_LABEL_OFFSET


class TestDerivedMathExtras:
    def test_math_caption_line_derives_from_pill_extra(self) -> None:
        # C7 — 18 == (11+2) + 5, derived not restated
        assert base._MATH_CAPTION_LINE_H == (
            line_box_h(base._CAPTION_FONT_PX) + svg._MATH_PILL_LINE_EXTRA
        )

    def test_line_box_formula_is_the_helper(self) -> None:
        # C9 — the +2 line box lives in one helper
        assert line_box_h(11) == 13
        assert line_box_h(10) == 12


class TestCanonicalWidthEstimator:
    def test_plane2d_line_label_uses_canonical_estimator(self) -> None:
        # B-1 — RED until the hand-rolled len*7 dies: a CJK label must get
        # a pill at least as wide as the canonical estimate
        from scriba.animation.primitives.plane2d import Plane2D

        p = Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10]})
        p.apply_command({"add_line": ("斜率很大", 1.0, 0.0)})
        rec = p.register_decorations()[0]
        canonical = estimate_text_width("斜率很大", 10)
        assert rec["placement"].width >= canonical, (
            f"line-label width {rec['placement'].width} under-sizes the "
            f"canonical {canonical} (hand-rolled len*7 survives)"
        )
