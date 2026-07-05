"""Unit tests for Plane2D in-place rotate ops (angular motion, census gap #2).

Design: investigations/completeness-census-post-0.24.md gap #2 +
investigations/tierD-combinatorics-game.md §5.3 (Burnside ring / rotating
calipers). ``rotate_*`` computes a rotated destination via the standard CCW
rotation matrix about a pivot, then mutates the element in place keeping its
index — so it rides the shipped ``position_move`` glide exactly like ``move_*``
(0 new motion kinds). The glide is a straight chord of the anchor's rotation
arc; with small per-step angles chord ≈ arc and reads as rotation.

Verified here:

- ``rotate_point`` / ``rotate_segment`` / ``rotate_line`` land the analytic
  rotation-matrix coordinates about ``about`` (default origin), keeping the
  slot index (identity) fixed.
- Rotating 90° four times returns to the start (idempotent full turn).
- ``get_node_positions`` moves for a rotated element, so the real differ emits
  ``position_move`` with the rotated anchor.
- Out-of-range / tombstoned targets → ``E1437`` (same as move).
- Missing ``i`` / missing or non-numeric ``by`` / malformed ``about`` → ``E1467``.
- ``move_*`` ops still behave (rotate dispatch does not shadow them).

All tests operate on Plane2D directly — no parser/emitter layers required.
"""

from __future__ import annotations

import math

import pytest

from scriba.animation.differ import _diff_shape_states
from scriba.animation.primitives.plane2d import Plane2D
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _make_plane(**extra) -> Plane2D:
    params = {"xrange": [-10, 10], "yrange": [-10, 10], "width": 320}
    params.update(extra)
    return Plane2D("p", params)


def _inject(prim: Plane2D) -> dict:
    """Mirror emitter._inject_tree_positions for one primitive → shape_states."""
    return {
        prim.name: {
            target: {"state": "idle", "x": x, "y": y}
            for target, (x, y) in prim.get_node_positions().items()
        }
    }


def _rotate_ref(x: float, y: float, cx: float, cy: float, deg: float) -> tuple[float, float]:
    """Independent reference implementation of CCW rotation about (cx, cy)."""
    r = math.radians(deg)
    dx, dy = x - cx, y - cy
    return (
        cx + dx * math.cos(r) - dy * math.sin(r),
        cy + dx * math.sin(r) + dy * math.cos(r),
    )


# ---------------------------------------------------------------
# 1. rotate_point
# ---------------------------------------------------------------


class TestRotatePoint:
    def test_rotate_90_about_origin(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        p.apply_command({"rotate_point": {"i": 0, "by": 90}})
        assert (p.points[0]["x"], p.points[0]["y"]) == pytest.approx((0.0, 2.0), abs=1e-9)

    def test_rotate_about_named_center(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (3, 1)})
        p.apply_command({"rotate_point": {"i": 0, "by": 180, "about": (1, 1)}})
        # 180° about (1,1): (3,1) → (-1,1)
        assert (p.points[0]["x"], p.points[0]["y"]) == pytest.approx((-1.0, 1.0), abs=1e-9)

    def test_matches_rotation_matrix_reference(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2.5, -1.5)})
        p.apply_command({"rotate_point": {"i": 0, "by": 37, "about": (0.5, 0.5)}})
        expect = _rotate_ref(2.5, -1.5, 0.5, 0.5, 37)
        assert (p.points[0]["x"], p.points[0]["y"]) == pytest.approx(expect, abs=1e-12)

    def test_four_quarter_turns_return_to_start(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (3, 1)})
        for _ in range(4):
            p.apply_command({"rotate_point": {"i": 0, "by": 90, "about": (0, 0)}})
        assert (p.points[0]["x"], p.points[0]["y"]) == pytest.approx((3.0, 1.0), abs=1e-9)

    def test_keeps_index_and_metadata(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": {"x": 2, "y": 0, "label": "A"}})
        p.apply_command({"rotate_point": {"i": 0, "by": 90}})
        assert p.points[0]["label"] == "A"
        assert "point[0]" in p.addressable_parts()

    def test_replaces_dict_immutably(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        original = p.points[0]
        p.apply_command({"rotate_point": {"i": 0, "by": 90}})
        assert p.points[0] is not original
        assert original["x"] == 2.0 and original["y"] == 0.0

    def test_out_of_range_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"rotate_point": {"i": 5, "by": 90}})

    def test_tombstoned_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        p.apply_command({"remove_point": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"rotate_point": {"i": 0, "by": 90}})

    def test_missing_index_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"rotate_point": {"by": 90}})

    def test_missing_by_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"rotate_point": {"i": 0}})

    def test_non_numeric_by_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"rotate_point": {"i": 0, "by": "oops"}})

    def test_malformed_about_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"rotate_point": {"i": 0, "by": 90, "about": (1,)}})

    def test_non_numeric_about_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"rotate_point": {"i": 0, "by": 90, "about": ("x", "y")}})

    def test_non_dict_spec_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"rotate_point": [0, 90]})


# ---------------------------------------------------------------
# 2. rotate_segment
# ---------------------------------------------------------------


class TestRotateSegment:
    def test_rotate_90_about_origin(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((1, 0), (2, 0))})
        p.apply_command({"rotate_segment": {"i": 0, "by": 90}})
        seg = p.segments[0]
        assert (seg["x1"], seg["y1"]) == pytest.approx((0.0, 1.0), abs=1e-9)
        assert (seg["x2"], seg["y2"]) == pytest.approx((0.0, 2.0), abs=1e-9)

    def test_matches_rotation_matrix_reference(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((1, -2), (4, 3))})
        p.apply_command({"rotate_segment": {"i": 0, "by": 50, "about": (2, 1)}})
        e1 = _rotate_ref(1, -2, 2, 1, 50)
        e2 = _rotate_ref(4, 3, 2, 1, 50)
        seg = p.segments[0]
        assert (seg["x1"], seg["y1"]) == pytest.approx(e1, abs=1e-12)
        assert (seg["x2"], seg["y2"]) == pytest.approx(e2, abs=1e-12)

    def test_length_preserved(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((1, 1), (4, 5))})
        p.apply_command({"rotate_segment": {"i": 0, "by": 73, "about": (0, 0)}})
        seg = p.segments[0]
        length = math.hypot(seg["x2"] - seg["x1"], seg["y2"] - seg["y1"])
        assert length == pytest.approx(5.0, abs=1e-9)  # 3-4-5

    def test_tombstoned_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        p.apply_command({"remove_segment": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"rotate_segment": {"i": 0, "by": 45}})

    def test_missing_by_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"rotate_segment": {"i": 0}})


# ---------------------------------------------------------------
# 3. rotate_line (refit slope/intercept, vertical handling)
# ---------------------------------------------------------------


class TestRotateLine:
    def test_horizontal_to_vertical(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("y=1", 0.0, 1.0)})  # y = 1
        p.apply_command({"rotate_line": {"i": 0, "by": 90}})  # about origin
        ln = p.lines[0]
        assert math.isinf(ln["slope"])  # now vertical
        assert ln["intercept"] == pytest.approx(-1.0, abs=1e-9)  # x = -1

    def test_vertical_to_horizontal(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("x=2", {"a": 1, "b": 0, "c": 2})})  # x = 2
        assert math.isinf(p.lines[0]["slope"])
        p.apply_command({"rotate_line": {"i": 0, "by": 90}})  # about origin
        ln = p.lines[0]
        assert ln["slope"] == pytest.approx(0.0, abs=1e-9)  # horizontal
        assert ln["intercept"] == pytest.approx(2.0, abs=1e-9)  # y = 2

    def test_slope_rotates_by_angle(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("h", 0.0, 0.0)})  # y = 0, angle 0
        p.apply_command({"rotate_line": {"i": 0, "by": 30}})
        # A line through the origin rotated 30° has slope tan(30°).
        assert p.lines[0]["slope"] == pytest.approx(math.tan(math.radians(30)), abs=1e-9)

    def test_keeps_index_and_label(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("L", 0.0, 1.0)})
        p.apply_command({"rotate_line": {"i": 0, "by": 45}})
        assert p.lines[0]["label"] == "L"
        assert "line[0]" in p.addressable_parts()

    def test_tombstoned_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("L", 0.0, 1.0)})
        p.apply_command({"remove_line": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"rotate_line": {"i": 0, "by": 45}})

    def test_missing_by_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("L", 0.0, 1.0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"rotate_line": {"i": 0}})


# ---------------------------------------------------------------
# 4. Differ integration — a rotate drives position_move
# ---------------------------------------------------------------


class TestRotateDrivesPositionMove:
    def test_rotated_point_yields_position_move(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        prev = _inject(p)
        p.apply_command({"rotate_point": {"i": 0, "by": 90}})
        curr = _inject(p)

        moves = [t for t in _diff_shape_states(prev, curr) if t.kind == "position_move"]
        assert len(moves) == 1
        move = moves[0]
        assert move.target == "p.point[0]"
        fx, fy = (float(v) for v in move.from_val.split(","))
        tx, ty = (float(v) for v in move.to_val.split(","))
        assert (fx, fy) == pytest.approx((2.0, 0.0), abs=1e-9)
        assert (tx, ty) == pytest.approx((0.0, 2.0), abs=1e-9)

    def test_rotated_segment_yields_position_move(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((1, 0), (3, 0))})  # midpoint (2, 0)
        prev = _inject(p)
        p.apply_command({"rotate_segment": {"i": 0, "by": 90}})
        curr = _inject(p)

        moves = [t for t in _diff_shape_states(prev, curr) if t.kind == "position_move"]
        assert len(moves) == 1
        assert moves[0].target == "p.segment[0]"
        tx, ty = (float(v) for v in moves[0].to_val.split(","))
        assert (tx, ty) == pytest.approx((0.0, 2.0), abs=1e-9)  # midpoint rotates

    def test_rotated_line_yields_position_move(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("y=1", 0.0, 1.0)})
        prev = _inject(p)
        p.apply_command({"rotate_line": {"i": 0, "by": 90}})
        curr = _inject(p)

        moves = [t for t in _diff_shape_states(prev, curr) if t.kind == "position_move"]
        assert len(moves) == 1
        assert moves[0].target == "p.line[0]"


# ---------------------------------------------------------------
# 5. Regression — move ops still work alongside rotate dispatch
# ---------------------------------------------------------------


class TestMoveStillWorks:
    def test_move_point_after_adding_rotate(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"move_point": {"i": 0, "x": 5, "y": -3}})
        assert (p.points[0]["x"], p.points[0]["y"]) == (5.0, -3.0)

    def test_rotate_then_move_compose(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (2, 0)})
        p.apply_command({"rotate_point": {"i": 0, "by": 90}})  # → (0, 2)
        p.apply_command({"move_point": {"i": 0, "x": 7}})  # partial: x only
        assert p.points[0]["x"] == 7.0
        assert p.points[0]["y"] == pytest.approx(2.0, abs=1e-9)
