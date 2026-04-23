"""Phase 5 Auto-Expansion — GEP v2.0 (U-15).

Pure functions for computing the minimum scale factor that drives
all edge-weight pill placements out of the leader/origin-fallback
cascade stages.

Design doc: docs/plans/phase-5-auto-expansion-design.md
"""

from __future__ import annotations

import math
from typing import Any

from scriba.animation.primitives._svg_helpers import _LabelPlacement
from scriba.animation.primitives.graph import (
    PillPlacement,
    _nudge_pill_placement,
    _WEIGHT_EDGE_MIN_LEN,
    _WEIGHT_FONT,
    _WEIGHT_PILL_PAD_X,
    _WEIGHT_PILL_PAD_Y,
    _WEIGHT_PILL_PERP_BIAS,
    _WEIGHT_PILL_STROKE_PAD,
    _format_weight,
)

# Import estimate_text_width from base (re-exported there).
from scriba.animation.primitives.base import estimate_text_width


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _min_scale_analytic(
    edges: list[tuple[float, float, float, float, float, float]],
    node_r: float,
) -> float:
    """Closed-form per-edge lower bound on the scale factor.

    Parameters
    ----------
    edges:
        List of ``(x1, y1, x2, y2, pill_w, aabb_w)`` tuples.  ``pill_w``
        and ``aabb_w`` are the pill width and rotated-AABB width at scale 1.
    node_r:
        Node radius at scale 1.

    Returns
    -------
    float
        ``max(1.0, max over all edges of (pill_w + 2*node_r) / L)``.
        Edges with coincident endpoints (``L < 1e-9``) are skipped.
    """
    s_min = 1.0
    for x1, y1, x2, y2, pill_w, _aabb_w in edges:
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1e-9:
            continue
        s_edge = (pill_w + 2.0 * node_r) / L
        if s_edge > s_min:
            s_min = s_edge
    return s_min


def _cascade_fallback_count(
    positions: dict[Any, tuple[float, float]],
    edges_data: list[Any],
    node_r: float,
    directed: bool,
    canvas_w: float | None = None,
    canvas_h: float | None = None,
) -> int:
    """Dry-run the pill placement cascade and return the fallback count.

    A "fallback" is any pill whose final placement stage is ``"leader"``
    (GEP-17 leader line) or ``"origin"`` reached only because all cascade
    stages were blocked (detected by checking if the origin candidate
    collided at entry).

    Parameters
    ----------
    positions:
        Node positions **already scaled** to the target scale.
    edges_data:
        Raw edge list in Graph-internal format:
        ``list[tuple[node_id, node_id, float | None]]``.
    node_r:
        Node radius (at scale 1 — not rescaled; the caller rescales
        positions instead).
    directed:
        Whether to shorten lines for arrowheads (mirrors Graph.emit_svg).

    Returns
    -------
    int
        Number of pills that fell back to leader or forced-origin stage.
    """
    # Build visible node AABBs (no hidden-node tracking — dry-run assumes
    # all nodes visible, matching the default emit_svg path).
    node_aabbs: list[_LabelPlacement] = [
        _LabelPlacement(
            x=float(positions[n][0]),
            y=float(positions[n][1]),
            width=float(2 * node_r),
            height=float(2 * node_r),
        )
        for n in positions
    ]

    # Graph centroid (mirrors emit_svg computation).
    if positions:
        graph_centroid: tuple[float, float] | None = (
            sum(float(positions[n][0]) for n in positions) / len(positions),
            sum(float(positions[n][1]) for n in positions) / len(positions),
        )
    else:
        graph_centroid = None

    placed_pills: list[_LabelPlacement] = []
    fallback_count = 0

    for edge in edges_data:
        u, v, weight = edge[0], edge[1], edge[2]
        if weight is None:
            continue  # unweighted edge — no pill

        # Compute pill dimensions (mirrors emit_svg).
        display_weight = _format_weight(float(weight))
        tw = estimate_text_width(display_weight, _WEIGHT_FONT)
        th = _WEIGHT_FONT + 2
        pill_w = tw + _WEIGHT_PILL_PAD_X * 2
        pill_h = th + _WEIGHT_PILL_PAD_Y * 2

        # Positions (already scaled by caller).
        if u not in positions or v not in positions:
            continue
        x1, y1 = float(positions[u][0]), float(positions[u][1])
        x2, y2 = float(positions[v][0]), float(positions[v][1])

        if directed:
            # Shorten line so arrowhead stops at circle boundary.
            dx_s = x2 - x1
            dy_s = y2 - y1
            d_s = math.hypot(dx_s, dy_s) or 1.0
            x2 = x2 - node_r * dx_s / d_s
            y2 = y2 - node_r * dy_s / d_s

        dx_edge = x2 - x1
        dy_edge = y2 - y1
        edge_len = math.hypot(dx_edge, dy_edge) or 1.0

        mid_x = (x1 + x2) / 2.0
        mid_y = (y1 + y2) / 2.0

        perp_x = -dy_edge / edge_len
        perp_y = dx_edge / edge_len

        # Theta for AABB computation (mirrors emit_svg).
        if edge_len < _WEIGHT_EDGE_MIN_LEN:
            theta_rad = 0.0
        else:
            _raw_theta = math.atan2(dy_edge, dx_edge)
            if _raw_theta > math.pi / 2:
                theta_rad = _raw_theta - math.pi
            elif _raw_theta < -math.pi / 2:
                theta_rad = _raw_theta + math.pi
            else:
                theta_rad = _raw_theta

        abs_cos = abs(math.cos(theta_rad))
        abs_sin = abs(math.sin(theta_rad))
        aabb_w = pill_w * abs_cos + pill_h * abs_sin + _WEIGHT_PILL_STROKE_PAD
        aabb_h = pill_w * abs_sin + pill_h * abs_cos + _WEIGHT_PILL_STROKE_PAD

        # Initial placement with perp-bias (mirrors emit_svg).
        lx = mid_x + perp_x * _WEIGHT_PILL_PERP_BIAS
        ly = mid_y + perp_y * _WEIGHT_PILL_PERP_BIAS

        ux = dx_edge / edge_len
        uy = dy_edge / edge_len
        max_shift_along = max(
            0.0,
            edge_len / 2.0 - pill_w / 2.0 - node_r,
        )

        # Check whether the origin candidate already collides — needed to
        # distinguish a "clean origin" from a "forced origin fallback".
        origin_candidate = _LabelPlacement(x=lx, y=ly, width=aabb_w, height=aabb_h)
        origin_collides = any(
            origin_candidate.overlaps(p) for p in placed_pills
        ) or any(
            origin_candidate.overlaps(n) for n in node_aabbs
        )

        pp: PillPlacement = _nudge_pill_placement(
            mid_x=lx,
            mid_y=ly,
            ux=ux,
            uy=uy,
            perp_x=perp_x,
            perp_y=perp_y,
            pill_w=pill_w,
            pill_h=pill_h,
            aabb_w=aabb_w,
            aabb_h=aabb_h,
            max_shift_along=max_shift_along,
            node_aabbs=node_aabbs,
            placed_pills=placed_pills,
            graph_centroid=graph_centroid,
        )

        # Count fallbacks:
        # - stage "leader": GEP-17 leader-line was emitted.
        # - stage "origin" AND origin collided at entry: all stages exhausted,
        #   fell back to origin as last resort.
        if pp.stage == "leader" or (pp.stage == "origin" and origin_collides):
            fallback_count += 1

        # Mirror emit_svg's GEP-08 canvas clamp before recording the obstacle,
        # so dry-run and live-run obstacle sets stay aligned near the viewbox
        # edge.
        rec_x = pp.x
        rec_y = pp.y
        if canvas_w is not None:
            rec_x = max(pill_w / 2, min(canvas_w - pill_w / 2, rec_x))
        if canvas_h is not None:
            rec_y = max(pill_h / 2, min(canvas_h - pill_h / 2, rec_y))
        placed_pills.append(
            _LabelPlacement(x=rec_x, y=rec_y, width=aabb_w, height=aabb_h)
        )

    return fallback_count


def _find_min_scale(
    positions: dict[Any, tuple[float, float]],
    edges_data: list[Any],
    node_r: float,
    directed: bool,
    canvas_w: float,
    canvas_h: float,
) -> float:
    """Binary-search for the minimum scale that eliminates all fallbacks.

    Parameters
    ----------
    positions:
        Node positions at scale 1.
    edges_data:
        Raw edge list: ``list[tuple[node_id, node_id, float | None]]``.
    node_r:
        Node radius.
    directed:
        Whether the graph is directed.
    canvas_w, canvas_h:
        Canvas dimensions (used to compute the canvas-bound scale cap).

    Returns
    -------
    float
        Minimum scale ``s >= 1.0`` such that ``_cascade_fallback_count``
        returns 0 at the returned scale, clamped to
        ``min(3.0, canvas_bound_scale)``.
    """
    # --- analytic lower bound ---
    edge_tuples: list[tuple[float, float, float, float, float, float]] = []
    for edge in edges_data:
        u, v, weight = edge[0], edge[1], edge[2]
        if weight is None:
            continue
        if u not in positions or v not in positions:
            continue
        x1, y1 = float(positions[u][0]), float(positions[u][1])
        x2, y2 = float(positions[v][0]), float(positions[v][1])
        # Mirror emit_svg's directed-edge shortening so the analytic L matches
        # the effective collision length used by _nudge_pill_placement.
        if directed:
            dxs = x2 - x1
            dys = y2 - y1
            ds = math.hypot(dxs, dys) or 1.0
            x2 = x2 - node_r * dxs / ds
            y2 = y2 - node_r * dys / ds
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1e-9:
            continue
        display_weight = _format_weight(float(weight))
        tw = estimate_text_width(display_weight, _WEIGHT_FONT)
        th = _WEIGHT_FONT + 2
        pill_w = tw + _WEIGHT_PILL_PAD_X * 2
        pill_h = th + _WEIGHT_PILL_PAD_Y * 2
        if L < _WEIGHT_EDGE_MIN_LEN:
            theta_rad = 0.0
        else:
            _raw_theta = math.atan2(y2 - y1, x2 - x1)
            if _raw_theta > math.pi / 2:
                theta_rad = _raw_theta - math.pi
            elif _raw_theta < -math.pi / 2:
                theta_rad = _raw_theta + math.pi
            else:
                theta_rad = _raw_theta
        abs_cos = abs(math.cos(theta_rad))
        abs_sin = abs(math.sin(theta_rad))
        aabb_w = (
            pill_w * abs_cos + pill_h * abs_sin + _WEIGHT_PILL_STROKE_PAD
        )
        edge_tuples.append((x1, y1, x2, y2, pill_w, aabb_w))

    lo = _min_scale_analytic(edge_tuples, node_r)

    # --- canvas-bound scale cap ---
    # Largest s such that all scaled positions remain within canvas.  Axes are
    # independent: x coord scales against canvas_w, y against canvas_h.
    max_x = max(
        (float(v[0]) for v in positions.values()),
        default=0.0,
    )
    max_y = max(
        (float(v[1]) for v in positions.values()),
        default=0.0,
    )
    cap_x = canvas_w / max_x if max_x > 1e-9 else 3.0
    cap_y = canvas_h / max_y if max_y > 1e-9 else 3.0
    canvas_bound_scale = min(cap_x, cap_y)

    effective_cap = min(3.0, canvas_bound_scale)

    if lo >= effective_cap:
        return effective_cap

    # Probe the full feasible range; binary search will tighten from both ends.
    hi = effective_cap

    # Binary search: up to 8 iterations, eps=0.02.
    eps = 0.02
    max_iter = 8
    for _ in range(max_iter):
        if hi - lo <= eps:
            break
        mid = (lo + hi) / 2.0
        scaled = {k: (float(v[0]) * mid, float(v[1]) * mid) for k, v in positions.items()}
        if _cascade_fallback_count(
            scaled,
            edges_data,
            node_r,
            directed,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
        ) == 0:
            hi = mid
        else:
            lo = mid

    return hi
