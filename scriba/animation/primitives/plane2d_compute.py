"""Geometry helpers for Plane2D — exposed to Starlark as the ``plane2d`` namespace.

All functions operate in math-convention coordinates (Y up). No external
dependencies.

See ``docs/primitives/plane2d.md`` §6 for the authoritative specification.
"""

from __future__ import annotations

from typing import Sequence

from scriba.animation.primitives._types import _FLOAT_EPS

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Point2D = tuple[float, float]
LineSI = tuple[float, float]  # (slope, intercept) — slope-intercept form


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def intersect(line1: LineSI, line2: LineSI) -> Point2D | None:
    """Intersection of two lines in slope-intercept form.

    Returns ``None`` when lines are parallel (slopes equal within 1e-9).
    """
    s1, i1 = line1
    s2, i2 = line2
    if abs(s1 - s2) < _FLOAT_EPS:
        return None
    x = (i2 - i1) / (s1 - s2)
    y = s1 * x + i1
    return (x, y)


def cross(a: Point2D, b: Point2D, c: Point2D) -> float:
    """Signed 2D cross product of ``(b-a) x (c-a)``.

    Positive  → left turn (CCW).
    Negative  → right turn (CW).
    Zero      → collinear.
    """
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def hull(points: Sequence[Point2D]) -> list[Point2D]:
    """Andrew's monotone chain convex hull.  Returns CCW vertices.

    Collinear boundary points are excluded (strict inequality ``<= 0``).
    Degenerate inputs (< 2 distinct points) return the sorted input.
    """
    pts = sorted(points)
    if len(pts) <= 1:
        return list(pts)

    # Build lower hull
    lower: list[Point2D] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    # Build upper hull
    upper: list[Point2D] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    # Remove last point of each half because it is repeated
    return lower[:-1] + upper[:-1]


def half_plane(line: LineSI, point: Point2D) -> bool:
    """Return ``True`` if *point* is strictly above the line ``y = slope*x + intercept``."""
    slope, intercept_val = line
    return point[1] > slope * point[0] + intercept_val


# ---------------------------------------------------------------------------
# Line clipping (Liang-Barsky style)
# ---------------------------------------------------------------------------


def clip_line_to_viewport(
    slope: float,
    intercept_val: float,
    xrange: tuple[float, float],
    yrange: tuple[float, float],
) -> tuple[Point2D, Point2D] | None:
    """Clip an infinite line ``y = slope*x + intercept`` to a rectangular viewport.

    Returns two endpoint tuples ``((x1,y1),(x2,y2))`` in math coordinates,
    or ``None`` if the line does not intersect the viewport.
    """
    xmin, xmax = xrange
    ymin, ymax = yrange

    # Collect candidate intersection points with the four viewport edges
    candidates: list[Point2D] = []

    # Left edge x = xmin
    y_at_xmin = slope * xmin + intercept_val
    if ymin <= y_at_xmin <= ymax:
        candidates.append((xmin, y_at_xmin))

    # Right edge x = xmax
    y_at_xmax = slope * xmax + intercept_val
    if ymin <= y_at_xmax <= ymax:
        candidates.append((xmax, y_at_xmax))

    # Bottom edge y = ymin (avoid division by zero for horizontal lines)
    if abs(slope) > 1e-12:
        x_at_ymin = (ymin - intercept_val) / slope
        if xmin <= x_at_ymin <= xmax:
            candidates.append((x_at_ymin, ymin))

    # Top edge y = ymax
    if abs(slope) > 1e-12:
        x_at_ymax = (ymax - intercept_val) / slope
        if xmin <= x_at_ymax <= xmax:
            candidates.append((x_at_ymax, ymax))

    if len(candidates) < 2:
        return None

    # Deduplicate near-identical points
    unique: list[Point2D] = [candidates[0]]
    for pt in candidates[1:]:
        is_dup = any(
            abs(pt[0] - u[0]) < _FLOAT_EPS and abs(pt[1] - u[1]) < _FLOAT_EPS
            for u in unique
        )
        if not is_dup:
            unique.append(pt)

    if len(unique) < 2:
        # Line just touches a corner — treat as no visible segment
        return None

    # Sort by x then y to get consistent left-to-right ordering
    unique.sort()
    return (unique[0], unique[-1])


# ---------------------------------------------------------------------------
# Lower envelope (Convex Hull Trick)
# ---------------------------------------------------------------------------


def _intersect_x(l1: LineSI, l2: LineSI) -> float:
    """X-coordinate where two non-parallel lines intersect."""
    s1, i1 = l1
    s2, i2 = l2
    return (i2 - i1) / (s1 - s2)


def lower_envelope(
    lines: Sequence[LineSI],
) -> list[tuple[LineSI, float, float]]:
    """Compute the lower envelope of non-vertical lines via CHT.

    Returns ``[(line, x_start, x_end), ...]`` in left-to-right order.
    ``x_start`` of piece 0 is ``-inf``; ``x_end`` of the last piece is ``+inf``.
    Pieces are contiguous: ``x_end[k] == x_start[k+1]``.

    The lower envelope is the pointwise minimum over all lines.
    """
    if not lines:
        return []

    # Sort by slope DESCENDING so that the line with the largest slope
    # (which dominates at x → -∞) comes first, and pieces go left-to-right.
    sorted_lines = sorted(lines, key=lambda l: (-l[0], l[1]))

    # Remove dominated lines: among parallel lines, only keep lowest intercept
    deduped: list[LineSI] = []
    for line in sorted_lines:
        if deduped and abs(line[0] - deduped[-1][0]) < _FLOAT_EPS:
            # Same slope — keep the one with smaller intercept
            if line[1] < deduped[-1][1]:
                deduped[-1] = line
        else:
            deduped.append(line)

    if len(deduped) == 1:
        return [(deduped[0], float("-inf"), float("inf"))]

    # Build envelope: lines sorted by decreasing slope.
    # Each successive line has a smaller slope, so it takes over (achieves
    # minimum) to the RIGHT of the previous line.
    # Remove line B from the stack if, when adding C, the intersection of
    # A and C is at or to the LEFT of intersection of A and B.
    env: list[LineSI] = []
    for line in deduped:
        while len(env) >= 2:
            ix_prev = _intersect_x(env[-2], env[-1])
            ix_new = _intersect_x(env[-2], line)
            if ix_new <= ix_prev:
                env.pop()
            else:
                break
        env.append(line)

    # Build result tuples with x-intervals (left-to-right)
    result: list[tuple[LineSI, float, float]] = []
    for i, line in enumerate(env):
        x_start = float("-inf") if i == 0 else _intersect_x(env[i - 1], line)
        x_end = float("inf") if i == len(env) - 1 else _intersect_x(line, env[i + 1])
        result.append((line, x_start, x_end))

    return result
