"""Unit tests for cross-primitive segment obstacle threading (v0.12.0 W3-α+).

Spec: when Plane2D is stacked above Array in a scene, pills on Array
annotations must see Plane2D's segment obstacles (translated into Array's
local coordinate frame) so they can avoid them.

Tests:
  1. pill SHIFTS when Plane2D MUST segment is in the default pill position.
  2. Two runs produce identical pill positions (determinism).
  3. A primitive's own segments are NOT double-counted when passed as
     cross-primitive segments targeting itself.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.primitives._obstacle_types import ObstacleSegment
from scriba.animation.primitives._svg_helpers import (
    _Obstacle,
    _segment_to_obstacle,
    _translate_segment,
)
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.plane2d import Plane2D


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plane(x0: float = -5.0, x1: float = 5.0,
                y0: float = -5.0, y1: float = 5.0,
                width: int = 320) -> Plane2D:
    return Plane2D("p", {
        "xrange": [x0, x1],
        "yrange": [y0, y1],
        "width": width,
        "axes": False,
        "grid": False,
    })


def _make_array(size: int = 5) -> ArrayPrimitive:
    return ArrayPrimitive("dp", {"size": size, "data": list(range(size))})


def _extract_pill_xy(svg: str) -> list[tuple[float, float]]:
    """Extract (x, y) from every pill rect inside a scriba-annotation group.

    Looks for ``<rect x="..." y="..." .../>`` elements that appear inside
    ``<g class="scriba-annotation ...">`` groups.
    """
    results: list[tuple[float, float]] = []
    # Find all scriba-annotation blocks and extract their first rect's x,y.
    for block in re.findall(
        r'<g[^>]*scriba-annotation[^>]*>(.*?)</g>', svg, re.S
    ):
        m = re.search(r'<rect[^>]*\bx="([^"]+)"[^>]*\by="([^"]+)"', block)
        if m:
            results.append((float(m.group(1)), float(m.group(2))))
    return results


# Scene-level offsets used throughout:
# Plane2D stacked at (x_off=82, y_off=16, height=320) → y_cursor_after = 386
# Array stacked below: y_off=386+50=436 (gap=50), x_off=82

_PLANE_X_OFF = 82.0
_PLANE_Y_OFF = 16.0
_ARRAY_X_OFF = 82.0
_ARRAY_Y_OFF = 436.0


def _build_scene_segments_for_array(
    plane: Plane2D,
    plane_x_off: float,
    plane_y_off: float,
    array: ArrayPrimitive,
    array_x_off: float,
    array_y_off: float,
) -> tuple:
    """Build scene_segments from plane's obstacle segments as seen by array.

    Returns the scene_segments tuple that _emit_frame_svg would pass to
    array.emit_svg(scene_segments=..., self_offset=...).
    """
    segs = plane.resolve_obstacle_segments()
    prim_id = id(plane)
    return tuple((seg, plane_x_off, plane_y_off, prim_id) for seg in segs)


# ---------------------------------------------------------------------------
# Test 1: pill shifts away from Plane2D MUST segment
# ---------------------------------------------------------------------------


class TestPillShiftsAwayFromCrossPrimitiveSegment:
    """Array pills must shift when a Plane2D MUST segment occupies the
    natural pill position in scene coordinates."""

    def _make_scene(self) -> tuple[Plane2D, ArrayPrimitive]:
        """Build Plane2D + Array stacked at the canonical offsets."""
        plane = _make_plane(width=320)
        arr = _make_array(size=5)
        return plane, arr

    def _annotate_cell2_above(self, arr: ArrayPrimitive) -> None:
        """Set a position=above annotation on cell[2]."""
        arr.set_annotations([{
            "target": "dp.cell[2]",
            "label": "$L_0(3)=0$",
            "position": "above",
        }])

    def _emit_without_cross_segs(
        self, arr: ArrayPrimitive
    ) -> str:
        """Emit Array SVG with NO cross-primitive segments (baseline)."""
        return arr.emit_svg(scene_segments=None, self_offset=None)

    def _emit_with_cross_segs(
        self,
        plane: Plane2D,
        arr: ArrayPrimitive,
        plane_x_off: float = _PLANE_X_OFF,
        plane_y_off: float = _PLANE_Y_OFF,
        array_x_off: float = _ARRAY_X_OFF,
        array_y_off: float = _ARRAY_Y_OFF,
    ) -> str:
        """Emit Array SVG WITH cross-primitive segments from plane."""
        scene_segs = _build_scene_segments_for_array(
            plane, plane_x_off, plane_y_off, arr, array_x_off, array_y_off
        )
        return arr.emit_svg(
            scene_segments=scene_segs,
            self_offset=(array_x_off, array_y_off),
        )

    def test_no_segments_no_shift(self) -> None:
        """Baseline: without any segments the pill stays at natural position."""
        plane, arr = self._make_scene()
        self._annotate_cell2_above(arr)
        svg = self._emit_without_cross_segs(arr)
        pills = _extract_pill_xy(svg)
        assert len(pills) >= 1, "expected at least one pill in SVG"

    def test_must_segment_in_pill_path_shifts_pill(self) -> None:
        """A Plane2D MUST segment at the natural pill y must cause a shift."""
        plane, arr = self._make_scene()

        # Add a line to plane2d that, when translated to Array's frame, lands
        # exactly where the pill would be placed by default (above cell[2]).
        # Array cell[2] center in Array-local coords:
        from scriba.animation.primitives._types import CELL_WIDTH, CELL_GAP, CELL_HEIGHT
        cell_cx = (CELL_WIDTH + CELL_GAP) * 2 + CELL_WIDTH / 2
        # Natural pill y for position=above is approx cell_cx_y - some offset above 0
        # In Array's local frame with arrow_above, default pill y is negative
        # (above y=0 of the translate group).  We construct a horizontal MUST
        # segment that covers the entire width of the array at that y level in
        # scene coordinates, which translates to the pill's natural local y.

        # A simpler approach: inject a synthetic MUST obstacle segment directly
        # into Array's local coordinate frame via scene_segments translation.
        # We want a horizontal segment at Array-local y = -40 (typical pill y),
        # which means in scene coords it's at y = array_y_off + (-40) = 396.
        # We place the Plane2D line at scene y = array_y_off - 40 = 396.
        # Since plane_y_off=16, Plane2D-local y for the segment = 396 - 16 = 380.
        # We create an ObstacleSegment directly.

        target_scene_y = _ARRAY_Y_OFF - 40.0   # = 396 in scene coords
        plane_local_y = target_scene_y - _PLANE_Y_OFF  # = 380 in Plane2D-local

        must_seg = ObstacleSegment(
            kind="plot_line",
            x0=0.0,
            y0=plane_local_y,
            x1=500.0,
            y1=plane_local_y,
            state="current",
            severity="MUST",
        )

        # Manually patch plane's segments so resolve_obstacle_segments returns
        # our crafted segment without needing a real math-space line.
        original_resolve = plane.resolve_obstacle_segments
        plane.resolve_obstacle_segments = lambda: [must_seg]  # type: ignore[method-assign]

        self._annotate_cell2_above(arr)

        svg_baseline = self._emit_without_cross_segs(arr)
        svg_with = self._emit_with_cross_segs(plane, arr)

        pills_baseline = _extract_pill_xy(svg_baseline)
        pills_with = _extract_pill_xy(svg_with)

        assert len(pills_baseline) >= 1, "baseline must have at least 1 pill"
        assert len(pills_with) >= 1, "with-segments must have at least 1 pill"

        # The pill y should have shifted — the MUST segment forces avoidance.
        baseline_y = pills_baseline[0][1]
        with_y = pills_with[0][1]
        assert baseline_y != with_y, (
            f"pill y did not shift: baseline_y={baseline_y}, with_y={with_y}. "
            "The MUST segment should have forced the pill to move."
        )

        # Restore
        plane.resolve_obstacle_segments = original_resolve  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# Test 2: determinism — two runs produce identical output
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Cross-primitive segment threading must be deterministic."""

    def test_two_runs_identical(self) -> None:
        """emit_svg with scene_segments returns byte-identical output twice."""
        plane = _make_plane(width=320)
        arr = _make_array(size=5)

        # Add a line to plane so resolve_obstacle_segments returns something.
        plane._add_line_internal(["", 0.5, 1.0])  # y = 0.5x + 1

        arr.set_annotations([{
            "target": "dp.cell[2]",
            "label": "$L_0(3)=0$",
            "position": "above",
        }])

        scene_segs = _build_scene_segments_for_array(
            plane, _PLANE_X_OFF, _PLANE_Y_OFF, arr, _ARRAY_X_OFF, _ARRAY_Y_OFF
        )

        svg_run1 = arr.emit_svg(
            scene_segments=scene_segs,
            self_offset=(_ARRAY_X_OFF, _ARRAY_Y_OFF),
        )
        svg_run2 = arr.emit_svg(
            scene_segments=scene_segs,
            self_offset=(_ARRAY_X_OFF, _ARRAY_Y_OFF),
        )

        assert svg_run1 == svg_run2, (
            "emit_svg is not deterministic with scene_segments. "
            "Two identical calls produced different output."
        )


# ---------------------------------------------------------------------------
# Test 3: self-exclusion — own segments not double-counted
# ---------------------------------------------------------------------------


class TestSelfExclusion:
    """A primitive's own segments must not appear twice in obstacle scoring."""

    def test_plane2d_own_segments_not_double_counted(self) -> None:
        """Passing Plane2D's own segments as scene_segments must not change its
        SVG output vs. calling without scene_segments (since those segments are
        already included via resolve_obstacle_segments())."""
        plane = _make_plane(width=320)
        # Add a line so there are actual segments.
        plane._add_line_internal(["", 1.0, 0.0])  # y = x
        plane.set_state("line[0]", "current")

        plane.set_annotations([{
            "target": "p.line[0]",
            "label": "test label",
            "arrow_from": "p.line[0]",
        }])

        # Build scene_segments from plane's own segments, with itself as source.
        segs = plane.resolve_obstacle_segments()
        prim_id = id(plane)
        scene_segs = tuple(
            (seg, _PLANE_X_OFF, _PLANE_Y_OFF, prim_id) for seg in segs
        )

        # With self_offset == the offset used in scene_segs, self segments
        # should be excluded (prim_id matches).
        svg_no_cross = plane.emit_svg(
            scene_segments=None,
            self_offset=None,
        )
        svg_with_self = plane.emit_svg(
            scene_segments=scene_segs,
            self_offset=(_PLANE_X_OFF, _PLANE_Y_OFF),
        )

        # Both should be identical — self-segments excluded means no change.
        assert svg_no_cross == svg_with_self, (
            "Plane2D SVG changed when passed its own segments as cross-primitive "
            "obstacles. Self-segments must be excluded to avoid double-counting."
        )


# ---------------------------------------------------------------------------
# Test 4: _translate_segment helper correctness
# ---------------------------------------------------------------------------


class TestTranslateSegment:
    """_translate_segment must shift endpoints by (dx, dy) without mutation."""

    def test_translate_shifts_endpoints(self) -> None:
        seg = ObstacleSegment(
            kind="plot_line",
            x0=10.0, y0=20.0,
            x1=30.0, y1=40.0,
            state="current",
            severity="MUST",
        )
        translated = _translate_segment(seg, dx=5.0, dy=-3.0)

        assert translated.x0 == pytest.approx(15.0)
        assert translated.y0 == pytest.approx(17.0)
        assert translated.x1 == pytest.approx(35.0)
        assert translated.y1 == pytest.approx(37.0)

    def test_translate_preserves_metadata(self) -> None:
        seg = ObstacleSegment(
            kind="axis_tick",
            x0=0.0, y0=0.0,
            x1=100.0, y1=50.0,
            state="dim",
            severity="SHOULD",
        )
        translated = _translate_segment(seg, dx=0.0, dy=0.0)

        assert translated.kind == "axis_tick"
        assert translated.state == "dim"
        assert translated.severity == "SHOULD"

    def test_translate_does_not_mutate_original(self) -> None:
        seg = ObstacleSegment(
            kind="plot_line",
            x0=1.0, y0=2.0,
            x1=3.0, y1=4.0,
            state="default",
            severity="SHOULD",
        )
        _ = _translate_segment(seg, dx=100.0, dy=200.0)

        # Original unchanged (frozen dataclass).
        assert seg.x0 == pytest.approx(1.0)
        assert seg.y0 == pytest.approx(2.0)
