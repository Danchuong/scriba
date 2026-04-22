"""Unit tests for Plane2D.resolve_obstacle_segments (R-31, v0.12.0 W3-α).

Covers:
  - Empty plane → []
  - 3 lines + axes → correct count and kinds
  - state="current" → severity="MUST", state preserved
  - other states → severity="SHOULD"
  - Coordinate-space check: data coords → correct SVG pixel coords
  - Tombstoned and hidden lines are skipped
  - No axes → no axis_tick segments
"""
from __future__ import annotations

import pytest

from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives._obstacle_types import ObstacleSegment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plane(**kwargs) -> Plane2D:
    """Construct a Plane2D with common defaults; override via kwargs."""
    params: dict = {
        "xrange": [-5.0, 5.0],
        "yrange": [-5.0, 5.0],
        "width": 320,
        "axes": True,
        "grid": False,
    }
    params.update(kwargs)
    return Plane2D("p", params)


def _add_line(plane: Plane2D, slope: float, intercept: float, label: str = "") -> None:
    """Add a line via apply_command (label, slope, intercept tuple form)."""
    plane._add_line_internal([label, slope, intercept])


# ---------------------------------------------------------------------------
# Test: empty plane → []
# ---------------------------------------------------------------------------


def test_empty_plane_returns_empty_list() -> None:
    plane = _make_plane(axes=False)
    result = plane.resolve_obstacle_segments()
    assert result == []


# ---------------------------------------------------------------------------
# Test: no axes option → no axis_tick segments
# ---------------------------------------------------------------------------


def test_no_axes_produces_no_axis_tick_segments() -> None:
    plane = _make_plane(axes=False)
    _add_line(plane, 1.0, 0.0)
    result = plane.resolve_obstacle_segments()
    kinds = [seg.kind for seg in result]
    assert "axis_tick" not in kinds
    assert len(result) == 1  # only the one plot_line


# ---------------------------------------------------------------------------
# Test: 3 lines + axes → 3 plot_line + 2 axis_tick
# ---------------------------------------------------------------------------


def test_three_lines_plus_axes_segment_count() -> None:
    plane = _make_plane(axes=True)
    _add_line(plane, 1.0, 0.0)
    _add_line(plane, -1.0, 0.0)
    _add_line(plane, 0.0, 2.0)  # horizontal y=2

    result = plane.resolve_obstacle_segments()
    plot_lines = [s for s in result if s.kind == "plot_line"]
    axis_ticks = [s for s in result if s.kind == "axis_tick"]

    assert len(plot_lines) == 3, f"expected 3 plot_line, got {len(plot_lines)}"
    assert len(axis_ticks) == 2, f"expected 2 axis_tick (X+Y spine), got {len(axis_ticks)}"
    assert len(result) == 5


# ---------------------------------------------------------------------------
# Test: state="current" → severity="MUST" and state field correct
# ---------------------------------------------------------------------------


def test_current_state_becomes_must_severity() -> None:
    plane = _make_plane(axes=False)
    _add_line(plane, 1.0, 0.0)  # line[0]
    _add_line(plane, -1.0, 0.0)  # line[1]
    plane.set_state("line[1]", "current")

    result = plane.resolve_obstacle_segments()
    assert len(result) == 2

    seg0 = result[0]  # line[0] — default state
    seg1 = result[1]  # line[1] — current

    assert seg0.severity == "SHOULD"
    assert seg0.state == "default"

    assert seg1.severity == "MUST"
    assert seg1.state == "current"


# ---------------------------------------------------------------------------
# Test: dim / done states → severity="SHOULD"
# ---------------------------------------------------------------------------


def test_dim_state_produces_should_severity() -> None:
    plane = _make_plane(axes=False)
    _add_line(plane, 0.0, 1.0)  # line[0]: y=1
    plane.set_state("line[0]", "dim")
    result = plane.resolve_obstacle_segments()
    assert len(result) == 1
    assert result[0].severity == "SHOULD"
    assert result[0].state == "dim"


def test_done_state_produces_should_severity() -> None:
    plane = _make_plane(axes=False)
    _add_line(plane, 0.0, -1.0)  # line[0]: y=-1
    plane.set_state("line[0]", "done")
    result = plane.resolve_obstacle_segments()
    assert len(result) == 1
    assert result[0].severity == "SHOULD"
    assert result[0].state == "done"


# ---------------------------------------------------------------------------
# Test: idle / good / error / info → state="default", severity="SHOULD"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw_state", ["idle", "good", "error", "highlight", "path"])
def test_non_special_states_map_to_default(raw_state: str) -> None:
    """States that are not current/dim/done map to obs_state="default", SHOULD."""
    plane = _make_plane(axes=False)
    _add_line(plane, 0.0, 0.0)  # line[0]
    if raw_state != "idle":
        plane.set_state("line[0]", raw_state)
    result = plane.resolve_obstacle_segments()
    assert len(result) == 1
    assert result[0].state == "default"
    assert result[0].severity == "SHOULD"


# ---------------------------------------------------------------------------
# Test: hidden lines are skipped
# ---------------------------------------------------------------------------


def test_hidden_lines_are_skipped() -> None:
    plane = _make_plane(axes=False)
    _add_line(plane, 1.0, 0.0)   # line[0] — visible
    _add_line(plane, -1.0, 0.0)  # line[1] — will be hidden
    plane.set_state("line[1]", "hidden")

    result = plane.resolve_obstacle_segments()
    assert len(result) == 1
    assert result[0].kind == "plot_line"


# ---------------------------------------------------------------------------
# Test: tombstoned lines are skipped
# ---------------------------------------------------------------------------


def test_tombstoned_lines_are_skipped() -> None:
    plane = _make_plane(axes=False)
    _add_line(plane, 1.0, 0.0)   # line[0]
    _add_line(plane, -1.0, 0.0)  # line[1]
    plane._remove_line_internal(0)

    result = plane.resolve_obstacle_segments()
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Test: return type is list[ObstacleSegment]
# ---------------------------------------------------------------------------


def test_return_type_is_list_of_obstacle_segment() -> None:
    plane = _make_plane(axes=True)
    _add_line(plane, 0.5, 1.0)
    result = plane.resolve_obstacle_segments()
    assert isinstance(result, list)
    for seg in result:
        assert isinstance(seg, ObstacleSegment)


# ---------------------------------------------------------------------------
# Test: coordinate-space check
#
# Plane setup:
#   xrange=[0, 10], yrange=[0, 10], width=200
#   aspect="equal" → height = 200 * 10/10 = 200
#   _PAD = 32
#   sx = (200 - 2*32) / 10 = 136/10 = 13.6
#   sy = -(200 - 2*32) / 10 = -13.6
#   tx = 32 + 0 * 13.6 = 32
#   ty = (200 - 32) + 0 * (200 - 64)/10 = 168 + 0 = 168
#
# A line y=x has slope=1, intercept=0.
# clip_line_to_viewport(1, 0, [0,10], [0,10]):
#   at x=0: y=0 (in range), at x=10: y=10 (in range).
#   So endpoints are (0,0) and (10,10) in math-space.
#
# math_to_svg(0, 0) = (32 + 0*13.6, 168 + 0*(-13.6)) = (32.0, 168.0)
# math_to_svg(10, 10) = (32 + 10*13.6, 168 + 10*(-13.6)) = (168.0, 32.0)
# ---------------------------------------------------------------------------

_COORD_PLANE_PARAMS = {
    "xrange": [0.0, 10.0],
    "yrange": [0.0, 10.0],
    "width": 200,
    "axes": False,
    "grid": False,
    "aspect": "equal",
}

# Expected transform constants for _COORD_PLANE_PARAMS:
_PAD = 32
_SX = (200 - 2 * _PAD) / 10.0   # 13.6
_SY = -(200 - 2 * _PAD) / 10.0  # -13.6
_TX = _PAD + 0.0 * _SX           # 32.0
_TY = (200 - _PAD) + 0.0 * (200 - 2 * _PAD) / 10.0  # 168.0


def _expected_svg(mx: float, my: float) -> tuple[float, float]:
    """Hand-compute expected SVG coord for _COORD_PLANE_PARAMS."""
    return _TX + mx * _SX, _TY + my * _SY


def test_coordinate_space_diagonal_line() -> None:
    """Line y=x maps from math (0,0)→(10,10) to correct SVG pixels."""
    plane = Plane2D("p", _COORD_PLANE_PARAMS)
    plane._add_line_internal(["", 1.0, 0.0])  # y = 1*x + 0

    result = plane.resolve_obstacle_segments()
    assert len(result) == 1
    seg = result[0]

    exp_x0, exp_y0 = _expected_svg(0.0, 0.0)
    exp_x1, exp_y1 = _expected_svg(10.0, 10.0)

    assert abs(seg.x0 - exp_x0) < 1e-4, f"x0: {seg.x0} != {exp_x0}"
    assert abs(seg.y0 - exp_y0) < 1e-4, f"y0: {seg.y0} != {exp_y0}"
    assert abs(seg.x1 - exp_x1) < 1e-4, f"x1: {seg.x1} != {exp_x1}"
    assert abs(seg.y1 - exp_y1) < 1e-4, f"y1: {seg.y1} != {exp_y1}"


def test_coordinate_space_horizontal_line() -> None:
    """Horizontal line y=5 maps to a horizontal SVG segment at correct y."""
    plane = Plane2D("p", _COORD_PLANE_PARAMS)
    plane._add_line_internal(["", 0.0, 5.0])  # y = 5

    result = plane.resolve_obstacle_segments()
    assert len(result) == 1
    seg = result[0]

    # y=5 in math-space → SVG y = 168 + 5*(-13.6) = 168 - 68 = 100.0
    exp_svg_y = _TY + 5.0 * _SY
    assert abs(seg.y0 - exp_svg_y) < 1e-4, f"y0: {seg.y0} != {exp_svg_y}"
    assert abs(seg.y1 - exp_svg_y) < 1e-4, f"y1: {seg.y1} != {exp_svg_y}"
    # x range should span full viewport width in SVG
    exp_x0, _ = _expected_svg(0.0, 5.0)
    exp_x1, _ = _expected_svg(10.0, 5.0)
    assert abs(seg.x0 - exp_x0) < 1e-4
    assert abs(seg.x1 - exp_x1) < 1e-4


def test_coordinate_space_vertical_line() -> None:
    """Vertical line x=3 maps to a vertical SVG segment at correct x."""
    plane = Plane2D("p", _COORD_PLANE_PARAMS)
    plane._add_line_internal(["", float("inf"), 3.0])  # vertical x=3

    result = plane.resolve_obstacle_segments()
    assert len(result) == 1
    seg = result[0]

    exp_svg_x = _TX + 3.0 * _SX
    assert abs(seg.x0 - exp_svg_x) < 1e-4, f"x0: {seg.x0} != {exp_svg_x}"
    assert abs(seg.x1 - exp_svg_x) < 1e-4, f"x1: {seg.x1} != {exp_svg_x}"
    # y spans full height
    exp_y0 = _TY + 0.0 * _SY
    exp_y1 = _TY + 10.0 * _SY
    assert abs(seg.y0 - exp_y0) < 1e-4
    assert abs(seg.y1 - exp_y1) < 1e-4


# ---------------------------------------------------------------------------
# Test: axis spines are in correct SVG positions
# ---------------------------------------------------------------------------


def test_axis_spines_position() -> None:
    """With xrange/yrange crossing zero, axis spines cross at (0,0) in math."""
    plane = Plane2D("p", {
        "xrange": [-5.0, 5.0],
        "yrange": [-5.0, 5.0],
        "width": 320,
        "axes": True,
        "grid": False,
        "aspect": "equal",
    })
    result = plane.resolve_obstacle_segments()
    axis_ticks = [s for s in result if s.kind == "axis_tick"]
    assert len(axis_ticks) == 2

    # Both must be SHOULD severity
    for seg in axis_ticks:
        assert seg.severity == "SHOULD"
        assert seg.state == "default"

    # X-spine is horizontal (same y0 and y1)
    x_spine = axis_ticks[0]
    assert abs(x_spine.y0 - x_spine.y1) < 1e-4, "X-spine should be horizontal"

    # Y-spine is vertical (same x0 and x1)
    y_spine = axis_ticks[1]
    assert abs(y_spine.x0 - y_spine.x1) < 1e-4, "Y-spine should be vertical"


# ---------------------------------------------------------------------------
# Test: stable ordering — line[0] before line[1] before axis ticks
# ---------------------------------------------------------------------------


def test_ordering_is_stable() -> None:
    """plot_line segments come before axis_tick segments in strict index order."""
    plane = _make_plane(axes=True)
    _add_line(plane, 2.0, 0.0)   # line[0]
    _add_line(plane, -2.0, 1.0)  # line[1]

    result = plane.resolve_obstacle_segments()
    plot_lines = [s for s in result if s.kind == "plot_line"]
    axis_ticks = [s for s in result if s.kind == "axis_tick"]

    # All plot_lines appear before all axis_ticks in the returned list
    if plot_lines and axis_ticks:
        last_plot_idx = max(i for i, s in enumerate(result) if s.kind == "plot_line")
        first_axis_idx = min(i for i, s in enumerate(result) if s.kind == "axis_tick")
        assert last_plot_idx < first_axis_idx, (
            "plot_line segments must precede axis_tick segments"
        )

    assert len(plot_lines) == 2
    assert len(axis_ticks) == 2
