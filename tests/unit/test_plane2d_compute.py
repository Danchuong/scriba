"""Unit tests for scriba.animation.primitives.plane2d_compute."""

from __future__ import annotations

import math

import pytest

from scriba.animation.primitives.plane2d_compute import (
    clip_line_to_viewport,
    cross,
    half_plane,
    hull,
    intersect,
    lower_envelope,
)


# ---------------------------------------------------------------
# intersect
# ---------------------------------------------------------------


class TestIntersect:
    def test_two_lines_crossing(self) -> None:
        # y = 2x + 1 and y = x + 3 → x = 2, y = 5
        pt = intersect((2, 1), (1, 3))
        assert pt is not None
        assert abs(pt[0] - 2.0) < 1e-9
        assert abs(pt[1] - 5.0) < 1e-9

    def test_parallel_lines_return_none(self) -> None:
        # y = 2x + 1 and y = 2x + 5 → parallel
        assert intersect((2, 1), (2, 5)) is None

    def test_nearly_parallel_within_epsilon(self) -> None:
        # slopes differ by less than 1e-9 → treated as parallel
        assert intersect((1.0, 0), (1.0 + 5e-10, 0)) is None

    def test_negative_slopes(self) -> None:
        # y = -x + 4 and y = x → x = 2, y = 2
        pt = intersect((-1, 4), (1, 0))
        assert pt is not None
        assert abs(pt[0] - 2.0) < 1e-9
        assert abs(pt[1] - 2.0) < 1e-9


# ---------------------------------------------------------------
# cross
# ---------------------------------------------------------------


class TestCross:
    def test_left_turn_positive(self) -> None:
        # (0,0) → (1,0) → (0,1) is a left turn
        assert cross((0, 0), (1, 0), (0, 1)) > 0

    def test_right_turn_negative(self) -> None:
        # (0,0) → (1,0) → (0,-1) is a right turn
        assert cross((0, 0), (1, 0), (0, -1)) < 0

    def test_collinear_zero(self) -> None:
        assert cross((0, 0), (1, 1), (2, 2)) == pytest.approx(0.0)


# ---------------------------------------------------------------
# hull
# ---------------------------------------------------------------


class TestHull:
    def test_simple_convex_set(self) -> None:
        pts = [(0, 0), (4, 0), (4, 4), (0, 4), (2, 2)]
        h = hull(pts)
        # Interior point (2,2) should be excluded
        assert (2, 2) not in h
        assert len(h) == 4

    def test_collinear_points_excluded(self) -> None:
        # Three collinear points: only endpoints should be on hull
        pts = [(0, 0), (1, 1), (2, 2), (0, 2), (2, 0)]
        h = hull(pts)
        assert (1, 1) not in h

    def test_degenerate_single_point(self) -> None:
        assert hull([(1, 2)]) == [(1, 2)]

    def test_degenerate_two_points(self) -> None:
        h = hull([(0, 0), (1, 1)])
        assert len(h) == 2

    def test_returns_ccw(self) -> None:
        pts = [(0, 0), (3, 0), (3, 3), (0, 3), (1.5, 1.5)]
        h = hull(pts)
        # Check CCW: every consecutive triple should have positive cross
        n = len(h)
        for i in range(n):
            c = cross(h[i], h[(i + 1) % n], h[(i + 2) % n])
            assert c > 0 or abs(c) < 1e-9

    def test_empty_input(self) -> None:
        assert hull([]) == []


# ---------------------------------------------------------------
# half_plane
# ---------------------------------------------------------------


class TestHalfPlane:
    def test_above_line(self) -> None:
        # y = x + 0, point (0, 2) → 2 > 0 → True
        assert half_plane((1, 0), (0, 2)) is True

    def test_below_line(self) -> None:
        assert half_plane((1, 0), (0, -1)) is False

    def test_on_line(self) -> None:
        # On the line: not strictly above
        assert half_plane((1, 0), (1, 1)) is False


# ---------------------------------------------------------------
# clip_line_to_viewport
# ---------------------------------------------------------------


class TestClipLineToViewport:
    def test_line_crossing_viewport(self) -> None:
        # y = x through [-5,5] x [-5,5]
        result = clip_line_to_viewport(1.0, 0.0, (-5, 5), (-5, 5))
        assert result is not None
        (x1, y1), (x2, y2) = result
        assert abs(x1 - (-5)) < 1e-6
        assert abs(y1 - (-5)) < 1e-6
        assert abs(x2 - 5) < 1e-6
        assert abs(y2 - 5) < 1e-6

    def test_line_entirely_outside(self) -> None:
        # y = x + 100 — way above viewport [0,10] x [0,10]
        assert clip_line_to_viewport(1.0, 100.0, (0, 10), (0, 10)) is None

    def test_horizontal_line(self) -> None:
        # y = 3
        result = clip_line_to_viewport(0.0, 3.0, (-5, 5), (-5, 5))
        assert result is not None
        (x1, y1), (x2, y2) = result
        assert abs(y1 - 3) < 1e-6
        assert abs(y2 - 3) < 1e-6

    def test_steep_line_clipped_by_top_bottom(self) -> None:
        # y = 10x through [0,1] x [0,5] → clipped by y boundaries
        result = clip_line_to_viewport(10.0, 0.0, (0, 1), (0, 5))
        assert result is not None
        (x1, y1), (x2, y2) = result
        assert y1 >= 0 - 1e-6
        assert y2 <= 5 + 1e-6


# ---------------------------------------------------------------
# lower_envelope
# ---------------------------------------------------------------


class TestLowerEnvelope:
    def test_four_lines_known_intersections(self) -> None:
        # y=2x+1, y=x+3, y=-x+9, y=-2x+11
        lines = [(2, 1), (1, 3), (-1, 9), (-2, 11)]
        env = lower_envelope(lines)

        # Should have 3 pieces
        assert len(env) == 3

        # First piece starts at -inf, last ends at +inf
        assert env[0][1] == float("-inf")
        assert env[-1][2] == float("inf")

        # Pieces are contiguous
        for i in range(len(env) - 1):
            assert abs(env[i][2] - env[i + 1][1]) < 1e-9

        # Verify each piece achieves minimum at a test query point
        for line, x_start, x_end in env:
            if math.isinf(x_start):
                test_x = x_end - 1
            elif math.isinf(x_end):
                test_x = x_start + 1
            else:
                test_x = (x_start + x_end) / 2
            y_env = line[0] * test_x + line[1]
            for s, i_val in lines:
                y_other = s * test_x + i_val
                assert y_env <= y_other + 1e-9

    def test_parallel_lines(self) -> None:
        # Among parallel lines, only the lowest intercept survives
        lines = [(1, 5), (1, 3), (1, 7)]
        env = lower_envelope(lines)
        assert len(env) == 1
        assert env[0][0] == (1, 3)

    def test_empty_input(self) -> None:
        assert lower_envelope([]) == []

    def test_single_line(self) -> None:
        env = lower_envelope([(2, 1)])
        assert len(env) == 1
        assert env[0][0] == (2, 1)
        assert env[0][1] == float("-inf")
        assert env[0][2] == float("inf")
