"""Obstacle geometry types for smart-label placement (v0.12.0 prep).

Defines frozen dataclasses used by the Protocol methods
``resolve_obstacle_boxes`` and ``resolve_obstacle_segments`` on every
primitive.  These types represent non-pill geometry that the
label-placement engine MUST treat as blocked regions.

R-02/R-03/R-04 (AABB obstacles) and R-31 (segment obstacles) are the
consumers.  See docs/spec/smart-label-ruleset.md and
docs/archive/smart-label-edge-avoidance-2026-04-22/R-31-plan.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ObstacleAABB:
    """Axis-aligned bounding box obstacle for smart-label placement.

    Used by ``resolve_obstacle_boxes`` to expose non-pill rectangular
    geometry (target cells, source cells, axis labels, grid lines) to
    the collision solver.

    Attributes
    ----------
    kind:
        Semantic category of the obstacle.  Drives severity escalation
        and candidate filtering in ``_nudge_candidates``.
    x:
        Left edge of the bounding box in SVG coordinates.
    y:
        Top edge of the bounding box in SVG coordinates.
    w:
        Width of the bounding box in pixels.
    h:
        Height of the bounding box in pixels.
    severity:
        ``"MUST"`` — hard block; no pill may overlap this obstacle.
        ``"SHOULD"`` — soft penalty; overlap is penalised but allowed
        when no MUST-free candidate exists.
    """

    kind: Literal["target_cell", "source_cell", "axis_label", "grid_line"]
    x: float
    y: float
    w: float
    h: float
    severity: Literal["MUST", "SHOULD"]


@dataclass(frozen=True)
class ObstacleSegment:
    """Line-segment obstacle for smart-label placement (R-31).

    Used by ``resolve_obstacle_segments`` to expose line geometry
    (graph edges, plot lines, axis ticks, tree edges) that pills must
    not occlude.

    Attributes
    ----------
    kind:
        Semantic category of the segment.
    x0, y0:
        Start point in SVG coordinates.
    x1, y1:
        End point in SVG coordinates.
    state:
        Rendering state of the line at the current frame — used for
        severity escalation (e.g. ``"current"`` lines are MUST-avoid).
    severity:
        ``"MUST"`` — hard block; no pill may cross this segment.
        ``"SHOULD"`` — soft penalty.
    """

    kind: Literal["plot_line", "edge", "axis_tick", "tree_edge"]
    x0: float
    y0: float
    x1: float
    y1: float
    state: Literal["current", "dim", "done", "default"]
    severity: Literal["MUST", "SHOULD"]
