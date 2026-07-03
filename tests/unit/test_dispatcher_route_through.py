"""FP-6 route-through: every annotation kind flows through the dispatcher.

Three primitives kept bespoke arrow paths that predate the dispatcher's
current capabilities (prior-arrow-stroke avoidance, content obstacles,
scene segments). The bespoke paths also created a latent measure≠paint
asymmetry on NumberLine and Plane2D: ``_measure_emit`` runs ALL
annotations through ``emit_annotation_arrows`` while paint ran arrows
through the bespoke loop — so multi-arrow scenes reserved space the paint
never used.

- Behavior locks (green before AND after): every annotation kind renders.
- Tightness pins (red before route-through): the reserved lane equals the
  painted extent on multi-arrow scenes.
"""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "tests")
from helpers.painted_extent import painted_extent  # noqa: E402

from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives.queue import Queue


def _anns(prim, anns):
    prim.set_annotations([
        {**a, "target": f"{prim.name}.{a['target']}"} for a in anns
    ])


def _numberline() -> NumberLinePrimitive:
    return NumberLinePrimitive("nl", {"domain": [0, 10]})


def _queue() -> Queue:
    return Queue("q", {"capacity": 4})


def _plane() -> Plane2D:
    return Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10]})


class TestBehaviorLocks:
    """Every annotation kind renders a visible pill/label (green today)."""

    @pytest.mark.parametrize("ann", [
        {"target": "tick[3]", "label": "vị trí", "position": "above"},
        {"target": "tick[3]", "label": "vị trí", "position": "below"},
        {"target": "tick[3]", "label": "mũi tên", "arrow": True},
        {"target": "tick[5]", "label": "cung", "arrow_from": "nl.tick[1]"},
    ], ids=["above", "below", "arrow-bool", "arrow-from"])
    def test_numberline_kind_renders(self, ann) -> None:
        nl = _numberline()
        _anns(nl, [ann])
        svg = nl.emit_svg()
        assert ann["label"] in svg

    @pytest.mark.parametrize("ann", [
        {"target": "cell[1]", "label": "đầu hàng", "position": "above"},
        {"target": "cell[1]", "label": "đầu hàng", "position": "below"},
        {"target": "cell[1]", "label": "mũi tên", "arrow": True},
        {"target": "cell[2]", "label": "cung", "arrow_from": "q.cell[0]"},
    ], ids=["above", "below", "arrow-bool", "arrow-from"])
    def test_queue_kind_renders(self, ann) -> None:
        q = _queue()
        _anns(q, [ann])
        svg = q.emit_svg()
        assert ann["label"] in svg

    @pytest.mark.parametrize("ann", [
        {"target": "point[0]", "label": "điểm P", "position": "above"},
        {"target": "point[0]", "label": "mũi tên", "arrow": True},
        {"target": "point[1]", "label": "cung", "arrow_from": "p.point[0]"},
    ], ids=["position", "arrow-bool", "arrow-from"])
    def test_plane2d_kind_renders(self, ann) -> None:
        p = _plane()
        p.apply_command({"add_point": (2.0, 2.0)})
        p.apply_command({"add_point": (7.0, 7.0)})
        _anns(p, [ann])
        svg = p.emit_svg()
        assert ann["label"] in svg


class TestMeasurePaintTightness:
    """Reserved lane == painted extent, multi-arrow case (red pre-fix).

    Measure replays the dispatcher (prior-stroke avoidance shifts pills);
    the bespoke paint path did not — so the reservation was computed from
    placements the paint never produced.
    """

    def test_numberline_multi_arrow_reservation_is_painted(self) -> None:
        nl = _numberline()
        _anns(nl, [
            {"target": "tick[6]", "label": "cung một", "arrow_from": "nl.tick[1]"},
            {"target": "tick[6]", "label": "cung hai", "arrow_from": "nl.tick[2]"},
            {"target": "tick[7]", "label": "cung ba", "arrow_from": "nl.tick[0]"},
        ])
        svg = nl.emit_svg()
        ext = painted_extent(svg)
        bb = nl.bounding_box()
        # honesty (always) + tightness (the RED half): nothing painted
        # outside, and no reserved band the paint never uses
        assert ext.min_y >= -0.01 and ext.max_y <= bb.height + 0.01
        assert ext.min_y <= 1.0, f"top over-reservation: {ext.min_y:.1f}px unused"

    def test_plane2d_position_pills_reservation_is_painted(self) -> None:
        p = _plane()
        p.apply_command({"add_point": (1.0, 9.5)})
        p.apply_command({"add_point": (3.0, 9.5)})
        _anns(p, [
            {"target": "point[0]", "label": "nhãn thứ nhất", "position": "above"},
            {"target": "point[1]", "label": "nhãn thứ hai", "position": "above"},
        ])
        svg = p.emit_svg()
        ext = painted_extent(svg)
        bb = p.bounding_box()
        assert ext.min_y >= -0.01 and ext.max_y <= bb.height + 0.01
        assert ext.min_y <= 1.0, f"top over-reservation: {ext.min_y:.1f}px unused"
