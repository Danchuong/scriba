"""Exact annotation reservation: reserved == painted, no estimation.

``PrimitiveBase.annotation_height_above()`` must return exactly how far the
primitive's annotations paint above y=0 — measured from the same emit code
that renders them — replacing the ``arrow_height_above`` heuristic upper
bound (uncapped arc + fixed headroom + guessed nudge margin).

Tightness is asserted against the INDEPENDENT test-side extent parser
(tests/helpers/painted_extent.py, dense-sampled bezier) so the production
measurer and the test measurer double-check each other.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.grid import GridPrimitive

from tests.helpers.painted_extent import painted_extent

# int(ceil) on the production side vs float sampling on the test side.
_TOL = 1.5


def _painted_top(prim) -> float:
    """How far the emitted annotations paint above y=0 (test-side parser)."""
    parts: list[str] = []
    # Run the SAME hook production measures through (it threads the
    # primitive's cell_metrics — geometry diverges without it).
    prim._measure_emit(parts)
    ext = painted_extent("\n".join(parts))
    if ext is None:
        return 0.0
    return max(0.0, -ext.min_y)


def _annotate(prim, target: str, **kv) -> None:
    prim.set_annotations(prim._annotations + [{"target": target, **kv}])


CASES = []


def _case(fn):
    CASES.append(pytest.param(fn, id=fn.__name__))
    return fn


@_case
def kmp_self_loops():
    arr = ArrayPrimitive("F", {"size": 9, "data": [0] * 9, "labels": "0..8"})
    for i, lbl in [(3, "j=F[3]=2"), (1, "j=F[1]=0"), (2, "j=F[2]=1"), (0, "j=F[0]=0")]:
        _annotate(arr, f"F.cell[{i}]", label=lbl, arrow_from=f"F.cell[{i}]", color="warn")
    return arr


@_case
def long_2d_arrow_grid():
    g = GridPrimitive("g", {"rows": 5, "cols": 5})
    _annotate(
        g,
        "g.cell[3][1]",
        label="m chẵn: vào từ trên-phải, xuống rồi trái",
        arrow_from="g.cell[0][3]",
        color="good",
    )
    return g


@_case
def stacked_same_target():
    d = DPTablePrimitive("dp", {"n": 8})
    for src in (1, 2, 4, 5, 6):
        _annotate(d, "dp.cell[7]", label=f"from {src}", arrow_from=f"dp.cell[{src}]")
    return d


@_case
def plain_pointer():
    arr = ArrayPrimitive("a", {"size": 5, "data": [1, 2, 3, 4, 5]})
    _annotate(arr, "a.cell[1]", label="here", arrow=True)
    return arr


@_case
def position_above_pill():
    arr = ArrayPrimitive("a", {"size": 5, "data": [1, 2, 3, 4, 5]})
    _annotate(arr, "a.cell[2]", label="một nhãn khá dài", position="above")
    return arr


@_case
def math_arrow_label():
    arr = ArrayPrimitive("a", {"size": 6, "data": list(range(6))})
    _annotate(arr, "a.cell[4]", label="$\\frac{a}{b}$", arrow_from="a.cell[1]")
    return arr


@_case
def no_annotations():
    return ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})


class TestExactReservation:
    @pytest.mark.parametrize("factory", CASES)
    def test_reserved_equals_painted(self, factory) -> None:
        prim = factory()
        reserved = prim.annotation_height_above()
        painted = _painted_top(factory())  # fresh instance: emit untouched
        assert reserved >= painted - 0.01, (
            f"UNDER-reserved: {reserved} < painted {painted:.1f}"
        )
        assert reserved <= painted + _TOL, (
            f"OVER-reserved: {reserved} vs painted {painted:.1f} — estimation crept back in"
        )

    def test_no_annotations_reserves_zero(self) -> None:
        arr = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        assert arr.annotation_height_above() == 0

    def test_cache_invalidated_by_set_annotations(self) -> None:
        arr = ArrayPrimitive("a", {"size": 6, "data": list(range(6))})
        assert arr.annotation_height_above() == 0
        _annotate(arr, "a.cell[3]", label="x", arrow_from="a.cell[0]")
        h1 = arr.annotation_height_above()
        assert h1 > 0
        assert arr.annotation_height_above() == h1  # cached, stable
        arr.set_annotations([])
        assert arr.annotation_height_above() == 0
