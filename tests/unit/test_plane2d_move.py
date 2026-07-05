"""Unit tests for Plane2D in-place move ops (A4 — element glides).

Design: investigations/gap-motion-identity-reorder.md §5.1-5.3. A ``move_*``
mutation changes an element's coordinates while keeping its index — and thus
its ``data-target`` — stable, so the differ emits ``position_move`` (a glide)
instead of the add+remove pair a re-add would produce.

Verified here:

- ``move_point`` / ``move_line`` / ``move_segment`` mutate coordinates but keep
  the slot index (identity) fixed; partial specs touch only the given fields.
- ``move_line`` slides a vertical sweep line via ``to_x``; a sloped line is
  ``E1467`` (no single x to set).
- Out-of-range / tombstoned targets raise ``E1437`` (same as remove).
- Malformed specs raise ``E1467``.
- ``get_node_positions`` returns math-space anchors keyed ``{name}.<part>[i]``
  for every living point/line/segment/circle, and its coordinates satisfy
  ``math_to_svg(anchor) == resolve_annotation_point(target)``.
- Injected positions drive a ``position_move`` through the real differ with
  correct from/to, and add/remove behaviour is unchanged (regression).

All tests operate on Plane2D directly — no parser/emitter layers required.
"""

from __future__ import annotations

import math

import pytest

from scriba.animation.differ import _diff_shape_states
from scriba.animation.primitives.plane2d import Plane2D, _TOMBSTONE
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _make_plane(**extra) -> Plane2D:
    params = {"xrange": [-10, 10], "yrange": [-10, 10], "width": 320}
    params.update(extra)
    return Plane2D("p", params)


def _vertical_line_plane(x: float = -2.0) -> Plane2D:
    """Plane holding a single vertical sweep line at ``x`` (slope=inf)."""
    p = _make_plane()
    p.apply_command({"add_line": ("sweep", {"a": 1, "b": 0, "c": x})})
    assert math.isinf(p.lines[0]["slope"])  # stored as a vertical line
    return p


def _inject(prim: Plane2D) -> dict:
    """Mirror emitter._inject_tree_positions for one primitive → shape_states."""
    return {
        prim.name: {
            target: {"state": "idle", "x": x, "y": y}
            for target, (x, y) in prim.get_node_positions().items()
        }
    }


# ---------------------------------------------------------------
# 1. move_point
# ---------------------------------------------------------------


class TestMovePoint:
    def test_move_changes_coords_keeps_index(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"move_point": {"i": 1, "x": 5, "y": -3}})
        # Index 1 still addresses the (now moved) point; index 0 untouched.
        assert p.points[0] == {"x": 0.0, "y": 0.0, "label": None, "radius": 4}
        assert p.points[1]["x"] == 5.0
        assert p.points[1]["y"] == -3.0
        assert "point[1]" in p.addressable_parts()

    def test_partial_move_only_touches_given_field(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": {"x": 2, "y": 4, "label": "A"}})
        p.apply_command({"move_point": {"i": 0, "y": 9}})
        assert p.points[0]["x"] == 2.0  # unchanged
        assert p.points[0]["y"] == 9.0  # moved
        assert p.points[0]["label"] == "A"  # metadata preserved

    def test_move_replaces_dict_immutably(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        original = p.points[0]
        p.apply_command({"move_point": {"i": 0, "x": 1}})
        assert p.points[0] is not original  # fresh dict, not in-place mutation
        assert original["x"] == 0.0  # old object untouched

    def test_out_of_range_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"move_point": {"i": 5, "x": 1}})

    def test_tombstoned_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"remove_point": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"move_point": {"i": 0, "x": 1}})

    def test_missing_index_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"move_point": {"x": 1}})

    def test_non_dict_spec_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"move_point": [0, 1, 2]})

    def test_non_integer_index_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"move_point": {"i": "oops", "x": 1}})

    def test_empty_move_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"move_point": {"i": 0}})


# ---------------------------------------------------------------
# 2. move_line (vertical sweep)
# ---------------------------------------------------------------


class TestMoveLine:
    def test_slides_vertical_line_keeps_identity(self) -> None:
        p = _vertical_line_plane(-2.0)
        p.apply_command({"move_line": {"i": 0, "to_x": 3.5}})
        assert p.lines[0]["intercept"] == 3.5  # x = 3.5 now
        assert math.isinf(p.lines[0]["slope"])  # still vertical
        assert p.lines[0]["label"] == "sweep"  # metadata preserved
        assert "line[0]" in p.addressable_parts()

    def test_sloped_line_rejects_to_x_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("y=x", 1.0, 0.0)})  # slope=1, finite
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"move_line": {"i": 0, "to_x": 4.0}})

    def test_missing_to_x_raises_e1467(self) -> None:
        p = _vertical_line_plane(-2.0)
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"move_line": {"i": 0}})

    def test_out_of_range_raises_e1437(self) -> None:
        p = _vertical_line_plane(-2.0)
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"move_line": {"i": 9, "to_x": 1.0}})

    def test_tombstoned_raises_e1437(self) -> None:
        p = _vertical_line_plane(-2.0)
        p.apply_command({"remove_line": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"move_line": {"i": 0, "to_x": 1.0}})


# ---------------------------------------------------------------
# 3. move_segment (partial endpoints)
# ---------------------------------------------------------------


class TestMoveSegment:
    def test_full_move_keeps_index(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        p.apply_command(
            {"move_segment": {"i": 0, "x1": 2, "y1": 2, "x2": 4, "y2": 5}}
        )
        seg = p.segments[0]
        assert (seg["x1"], seg["y1"], seg["x2"], seg["y2"]) == (2.0, 2.0, 4.0, 5.0)

    def test_partial_move_only_one_endpoint(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        p.apply_command({"move_segment": {"i": 0, "x1": -3, "y1": -3}})
        seg = p.segments[0]
        assert (seg["x1"], seg["y1"]) == (-3.0, -3.0)  # moved end
        assert (seg["x2"], seg["y2"]) == (1.0, 1.0)  # other end fixed

    def test_tombstoned_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        p.apply_command({"remove_segment": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"move_segment": {"i": 0, "x1": 2}})

    def test_empty_move_raises_e1467(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"move_segment": {"i": 0}})


# ---------------------------------------------------------------
# 4. get_node_positions — keys, math anchors, resolve/emit parity
# ---------------------------------------------------------------


class TestGetNodePositions:
    def test_keys_use_data_target_format(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (1, 2)})
        p.apply_command({"add_segment": ((0, 0), (2, 2))})
        p.apply_command({"add_circle": (0, 0, 3)})
        p.apply_command({"add_line": ("s", {"a": 1, "b": 0, "c": 1})})
        keys = set(p.get_node_positions())
        assert keys == {
            "p.point[0]",
            "p.segment[0]",
            "p.circle[0]",
            "p.line[0]",
        }

    def test_point_anchor_is_math_coords(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (3, -4)})
        assert p.get_node_positions()["p.point[0]"] == (3.0, -4.0)

    def test_line_anchor_is_midpoint_math(self) -> None:
        p = _vertical_line_plane(-2.0)
        # Vertical line spans the full yrange [-10, 10] → mid-y = 0.
        assert p.get_node_positions()["p.line[0]"] == (-2.0, 0.0)

    def test_segment_anchor_is_midpoint_math(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((0, 0), (4, 6))})
        assert p.get_node_positions()["p.segment[0]"] == (2.0, 3.0)

    @pytest.mark.parametrize(
        "add",
        [
            {"add_point": (2, -3)},
            {"add_segment": ((1, 1), (5, 3))},
            {"add_circle": (-1, 2, 2)},
            {"add_line": ("s", {"a": 1, "b": 0, "c": 4})},
        ],
    )
    def test_math_to_svg_of_anchor_matches_resolve(self, add) -> None:
        # The invariant that ties injection to the established annotation path:
        # feeding the injected math anchor through math_to_svg reproduces
        # resolve_annotation_point exactly, so a moved element's glide target is
        # the same point the annotation scorer would resolve.
        p = _make_plane()
        p.apply_command(add)
        for target, anchor in p.get_node_positions().items():
            svg = p.math_to_svg(*anchor)
            resolved = p.resolve_annotation_point(target)
            assert resolved == pytest.approx(svg)

    def test_tombstoned_element_omitted(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"remove_point": 0})
        pos = p.get_node_positions()
        assert "p.point[0]" not in pos  # tombstoned
        assert "p.point[1]" in pos  # survivor keeps its index

    def test_offscreen_vertical_line_omitted(self) -> None:
        p = _make_plane()  # xrange [-10, 10]
        p.apply_command({"add_line": ("s", {"a": 1, "b": 0, "c": 99})})
        assert "p.line[0]" not in p.get_node_positions()

    def test_empty_plane_returns_empty(self) -> None:
        assert _make_plane().get_node_positions() == {}

    def test_unsupported_families_not_injected(self) -> None:
        # Only point/line/segment/circle carry a move op → only they are injected.
        p = _make_plane()
        p.apply_command({"add_polygon": [(0, 0), (1, 0), (0, 1), (0, 0)]})
        p.apply_command({"add_wedge": (0, 0, 3, 0, 90)})
        assert p.get_node_positions() == {}


# ---------------------------------------------------------------
# 5. Differ integration — a move drives position_move end to end
# ---------------------------------------------------------------


class TestPositionMoveIntegration:
    def test_moved_line_yields_position_move(self) -> None:
        p = _vertical_line_plane(-2.0)
        prev = _inject(p)
        p.apply_command({"move_line": {"i": 0, "to_x": 0.0}})
        curr = _inject(p)

        transitions = _diff_shape_states(prev, curr)
        moves = [t for t in transitions if t.kind == "position_move"]
        assert len(moves) == 1
        move = moves[0]
        assert move.target == "p.line[0]"
        assert move.from_val == "-2.0,0.0"
        assert move.to_val == "0.0,0.0"

    def test_moved_point_yields_position_move(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (1, 1)})
        prev = _inject(p)
        p.apply_command({"move_point": {"i": 0, "x": 4, "y": -2}})
        curr = _inject(p)

        moves = [
            t for t in _diff_shape_states(prev, curr) if t.kind == "position_move"
        ]
        assert [(m.target, m.from_val, m.to_val) for m in moves] == [
            ("p.point[0]", "1.0,1.0", "4.0,-2.0")
        ]

    def test_static_element_yields_no_transition(self) -> None:
        # An element that does not move must not emit a spurious position_move
        # (this is what keeps existing multi-step plane goldens unchanged).
        p = _make_plane()
        p.apply_command({"add_point": (1, 1)})
        prev = _inject(p)
        curr = _inject(p)  # nothing moved
        assert _diff_shape_states(prev, curr) == []

    def test_add_does_not_emit_position_move(self) -> None:
        # Adding a second point is a new identity, not a move of the first.
        p = _make_plane()
        p.apply_command({"add_point": (1, 1)})
        prev = _inject(p)
        p.apply_command({"add_point": (2, 2)})
        curr = _inject(p)
        moves = [
            t for t in _diff_shape_states(prev, curr) if t.kind == "position_move"
        ]
        assert moves == []


# ---------------------------------------------------------------
# 6. Regression — add/remove semantics unchanged by the new method
# ---------------------------------------------------------------


class TestAddRemoveRegression:
    def test_add_then_position_reflects_new_element(self) -> None:
        p = _make_plane()
        assert p.get_node_positions() == {}
        p.apply_command({"add_point": (3, 3)})
        assert p.get_node_positions() == {"p.point[0]": (3.0, 3.0)}

    def test_remove_keeps_index_stable_for_survivors(self) -> None:
        # The motivating tombstone invariant still holds: removing point[1]
        # leaves point[2] addressable at index 2 (not renumbered to 1).
        p = _make_plane()
        for xy in [(0, 0), (1, 1), (2, 2)]:
            p.apply_command({"add_point": xy})
        p.apply_command({"remove_point": 1})
        assert p.points[1] is _TOMBSTONE
        pos = p.get_node_positions()
        assert "p.point[1]" not in pos
        assert pos["p.point[2]"] == (2.0, 2.0)
