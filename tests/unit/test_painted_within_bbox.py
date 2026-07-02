"""Bbox honesty: everything a primitive paints must fit its declared bbox.

Guard for the reservation redesign (exact painted-extent reservation).
Today ``arrow_height_above`` is a heuristic upper bound that can UNDER-reserve
(kmp corpus: self-loop arrows paint ~4px above the reserved lane) and
over-reserve (grid 2D: 114px reserved, 0px used). This test pins the safety
half of the contract — painted ⊆ declared — measured from the emitted SVG
itself (dense-sampled bezier arcs, stroke-padded), so it stays true no matter
how the reservation is computed.

The tightness half (reserved ≈ painted) is asserted separately once the exact
measurer lands.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.grid import GridPrimitive

from tests.helpers.painted_extent import painted_extent

# Painted pixels may legally exceed the geometric bbox by nothing.
# (Stroke halves are already folded into the measurement.)
_EPS = 0.01
# Horizontal reservation now consumes the same painted-extent measurement
# as the vertical lane, so it gets the same strict budget.
_EPS_X = 0.01


def _assert_painted_within_bbox(prim) -> None:
    svg = prim.emit_svg()
    ext = painted_extent(svg)
    assert ext is not None, "nothing painted?"
    bb = prim.bounding_box()
    problems = []
    if ext.min_y < -_EPS:
        problems.append(f"paints {-ext.min_y:.1f}px ABOVE the bbox top")
    if ext.max_y > bb.height + _EPS:
        problems.append(
            f"paints {ext.max_y - bb.height:.1f}px BELOW the bbox bottom"
        )
    if ext.min_x < -_EPS_X:
        problems.append(f"paints {-ext.min_x:.1f}px LEFT of the bbox")
    if ext.max_x > bb.width + _EPS_X:
        problems.append(
            f"paints {ext.max_x - bb.width:.1f}px RIGHT of the bbox"
        )
    assert not problems, (
        f"{type(prim).__name__} bbox {bb.width:.0f}x{bb.height:.0f}, painted "
        f"[{ext.min_x:.1f},{ext.min_y:.1f}..{ext.max_x:.1f},{ext.max_y:.1f}]: "
        + "; ".join(problems)
    )


def _annotate(prim, target: str, **kv) -> None:
    prim.set_annotations(prim._annotations + [{"target": target, **kv}])


class TestSelfLoopArrows:
    """kmp regression: arrow_from == target (self-loop) under-reserved."""

    def test_single_self_loop_with_label(self) -> None:
        arr = ArrayPrimitive("F", {"size": 9, "data": [0] * 9, "labels": "0..8"})
        _annotate(
            arr, "F.cell[3]", label="j=F[3]=2", arrow_from="F.cell[3]", color="warn"
        )
        _assert_painted_within_bbox(arr)

    def test_kmp_shape_four_self_loops(self) -> None:
        arr = ArrayPrimitive("F", {"size": 9, "data": [0] * 9, "labels": "0..8"})
        for i, lbl in [(3, "j=F[3]=2"), (1, "j=F[1]=0"), (2, "j=F[2]=1"), (0, "j=F[0]=0")]:
            _annotate(
                arr,
                f"F.cell[{i}]",
                label=lbl,
                arrow_from=f"F.cell[{i}]",
                color="warn",
            )
        _assert_painted_within_bbox(arr)


class TestArcArrows:
    def test_long_diagonal_arrow_on_grid(self) -> None:
        g = GridPrimitive("g", {"rows": 5, "cols": 5})
        _annotate(
            g,
            "g.cell[3][1]",
            label="m chẵn: vào từ trên-phải, xuống rồi trái",
            arrow_from="g.cell[0][3]",
            color="good",
        )
        _assert_painted_within_bbox(g)

    def test_adjacent_cells_short_arrow(self) -> None:
        arr = ArrayPrimitive("a", {"size": 6, "data": list(range(6))})
        _annotate(arr, "a.cell[3]", label="swap", arrow_from="a.cell[2]")
        _assert_painted_within_bbox(arr)

    def test_stacked_arrows_same_target(self) -> None:
        d = DPTablePrimitive("dp", {"n": 8})
        for src in (1, 2, 4, 5, 6):
            _annotate(d, "dp.cell[7]", label=f"from {src}", arrow_from=f"dp.cell[{src}]")
        _assert_painted_within_bbox(d)

    def test_extreme_span_arrow(self) -> None:
        arr = ArrayPrimitive("a", {"size": 19, "data": [0] * 19})
        _annotate(arr, "a.cell[18]", label="wrap", arrow_from="a.cell[0]")
        _assert_painted_within_bbox(arr)


class TestPositionPills:
    @pytest.mark.parametrize("position", ["above", "below", "left", "right"])
    def test_position_pill(self, position: str) -> None:
        arr = ArrayPrimitive("a", {"size": 5, "data": [1, 2, 3, 4, 5]})
        _annotate(arr, "a.cell[2]", label="một nhãn khá dài", position=position)
        _assert_painted_within_bbox(arr)

    def test_math_label_above(self) -> None:
        arr = ArrayPrimitive("a", {"size": 5, "data": [1, 2, 3, 4, 5]})
        _annotate(arr, "a.cell[2]", label="$\\frac{a}{b}$ tổng", position="above")
        _assert_painted_within_bbox(arr)


class TestPlainPointer:
    def test_plain_arrow_with_label(self) -> None:
        arr = ArrayPrimitive("a", {"size": 5, "data": [1, 2, 3, 4, 5]})
        _annotate(arr, "a.cell[1]", label="here", arrow=True)
        _assert_painted_within_bbox(arr)

class TestHorizontalAndBelowExact:
    """Multi-pill collision nudges relocate pills; the reservation must
    contain the RELOCATED pill, which the legacy formula never modelled."""

    def test_three_right_pills_nudged_stay_inside(self) -> None:
        arr = ArrayPrimitive("a", {"size": 4, "data": [1, 2, 3, 4]})
        for i in (1, 2, 3):
            _annotate(arr, f"a.cell[{i}]", label=f"nhãn phải {i}", position="right")
        _assert_painted_within_bbox(arr)

    def test_three_left_pills_nudged_stay_inside(self) -> None:
        arr = ArrayPrimitive("a", {"size": 4, "data": [1, 2, 3, 4]})
        for i in (0, 1, 2):
            _annotate(arr, f"a.cell[{i}]", label=f"nhãn trái dài {i}", position="left")
        _assert_painted_within_bbox(arr)

    def test_stacked_below_pills_stay_inside(self) -> None:
        arr = ArrayPrimitive("a", {"size": 5, "data": [1, 2, 3, 4, 5]})
        for i in (1, 2, 3):
            _annotate(arr, f"a.cell[{i}]", label=f"ghi chú dưới {i}", position="below")
        _assert_painted_within_bbox(arr)

    def test_wide_math_arc_pill_horizontal(self) -> None:
        g = GridPrimitive("g", {"rows": 3, "cols": 3})
        _annotate(
            g, "g.cell[0][2]",
            label="$dp[i][j] = \\min(dp[i-1][j], dp[i][j-1]) + c$",
            arrow_from="g.cell[2][0]",
        )
        _assert_painted_within_bbox(g)

    def test_12px_color_below_pill(self) -> None:
        # ARROW_STYLES has 12px label colors; the legacy array estimator
        # hardcoded 11px and under-reserved these.
        arr = ArrayPrimitive("a", {"size": 4, "data": [1, 2, 3, 4]})
        _annotate(arr, "a.cell[0]", label="một nhãn khá dài rõ ràng", position="below", color="bad")
        _assert_painted_within_bbox(arr)


class TestPillsDoNotOverlapEachOther:
    """Placement must resolve pill-pill collisions through the scoring
    engine — the retired 4-direction first-fit loop gave up after one
    round and left pills stacked on top of each other."""

    @staticmethod
    def _pill_rects(svg: str):
        import re as _re

        rects = []
        for m in _re.finditer(
            r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"'
            r'[^>]*fill="white"',
            svg,
        ):
            x, y, w, h = map(float, m.groups())
            rects.append((x, y, w, h))
        return rects

    def test_four_above_pills_same_cell_do_not_stack(self) -> None:
        arr = ArrayPrimitive("a", {"size": 6, "data": list(range(6))})
        for i in range(4):
            _annotate(arr, "a.cell[2]", label=f"chú thích {i}", position="above")
        svg = arr.emit_svg()
        rects = self._pill_rects(svg)
        assert len(rects) == 4
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                ax, ay, aw, ah = rects[i]
                bx, by, bw, bh = rects[j]
                ix = min(ax + aw, bx + bw) - max(ax, bx)
                iy = min(ay + ah, by + bh) - max(ay, by)
                overlap = max(0.0, ix) * max(0.0, iy)
                assert overlap <= 0.25 * min(aw * ah, bw * bh), (
                    f"pills {i} and {j} overlap heavily: {rects[i]} vs {rects[j]}"
                )
        _assert_painted_within_bbox(arr)
