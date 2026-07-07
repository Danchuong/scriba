"""Graph primitive with Fruchterman-Reingold force-directed layout.

Implements ``\\shape{name}{Graph}{nodes=..., edges=..., ...}`` for BFS/DFS,
flow networks, and general graph algorithm visualizations.

See ``docs/spec/primitives.md`` section 6 for the authoritative specification.
"""

from __future__ import annotations

import math
import os
import random
import re
from typing import Any, Callable, ClassVar, NamedTuple

from scriba.animation.errors import _animation_error
from scriba.animation.primitives._params import coerce_list
from scriba.animation.primitives._text_metrics import measure_value_text
from scriba.animation.primitives.base import (
    line_box_h,
    _label_has_math,
    _LabelPlacement,
    BoundingBox,
    PrimitiveBase,
    THEME,
    _escape_xml,
    _render_split_label_svg,
    _render_svg_text,
    allow_forbidden_pattern,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._svg_helpers import (
    CellMetrics,
    _DEFAULT_LABEL_FONT_PX,
    _LABEL_PILL_PAD_X,
    _LABEL_PILL_PAD_Y,
    _LABEL_PILL_RADIUS,
    ARROW_STYLES,
    annotation_color_class,
    LABEL_FONT_PX,
    measure_label_line,
    strip_math_markup,
)
from scriba.animation.primitives.plane2d_compute import hull as _convex_hull
from scriba.animation.primitives._types import (
    _NODE_MIN_RADIUS,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_WIDTH = 400
_DEFAULT_HEIGHT = 300
_NODE_RADIUS = 20
_EDGE_STROKE_WIDTH = 2
_PADDING = 20
_DEFAULT_SEED = 42
_DEFAULT_ITERATIONS = 50

# \group overlay hull (investigations/gap-dsu-forest-design.md §6 Phase 1) — a
# presentation-only decoration wrapping a named node cluster. The hull clears
# each node centre by node_radius + _GROUP_PAD so circles sit inside; corners
# round by _GROUP_CORNER_R. Fill/stroke opacities + dash mirror the R-35 block
# bracket (base.py) so the whole decoration family reads alike. These never
# touch bounding_box — the node-set (and viewBox) is untouched.
_GROUP_PAD = 14
_GROUP_CORNER_R = 12
_GROUP_FILL_OPACITY = "0.12"
_GROUP_STROKE_OPACITY = "0.55"
_GROUP_STROKE_DASH = "4,3"


def _rounded_polygon_path(pts: "list[tuple[float, float]]", r: float) -> str:
    """Closed SVG path through *pts* (a simple polygon, len>=3) with every corner
    rounded by radius ~*r* via a quadratic-Bézier corner-cut. The straight edge
    portions are preserved, so the path never bulges past the vertices' bbox."""
    n = len(pts)

    def _cut(i: int, toward: int) -> "tuple[float, float]":
        x0, y0 = pts[i]
        x1, y1 = pts[toward]
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy) or 1.0
        t = min(r, d / 2.0)
        return (x0 + dx / d * t, y0 + dy / d * t)

    segs: "list[str]" = []
    for i in range(n):
        prev_pt = _cut(i, (i - 1) % n)
        next_pt = _cut(i, (i + 1) % n)
        vx, vy = pts[i]
        segs.append(
            f"{'M' if i == 0 else 'L'}{prev_pt[0]:.1f},{prev_pt[1]:.1f}"
        )
        segs.append(f"Q{vx:.1f},{vy:.1f} {next_pt[0]:.1f},{next_pt[1]:.1f}")
    segs.append("Z")
    return " ".join(segs)


def _rounded_rect_path(x: float, y: float, w: float, h: float, r: float) -> str:
    """Closed SVG path for an axis-aligned rounded rectangle — the <=2-node
    fallback for a degenerate hull (case §6: `style=bbox`)."""
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    return (
        f"M{x + r:.1f},{y:.1f} "
        f"L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} "
        f"L{x + w:.1f},{y + h - r:.1f} Q{x + w:.1f},{y + h:.1f} "
        f"{x + w - r:.1f},{y + h:.1f} "
        f"L{x + r:.1f},{y + h:.1f} Q{x:.1f},{y + h:.1f} {x:.1f},{y + h - r:.1f} "
        f"L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} Z"
    )

# Auto-seed sweep (Phase 3): when the author does NOT pin a seed, a force
# layout tries this many candidate seeds, scores each with score_layout, and
# keeps the lowest-scoring (most readable) result. Candidates are the first
# _AUTO_SEED_COUNT integers (0..N-1), a deterministic set; ties break toward
# the smallest seed. Kept small because each candidate is a full O(N^2) FR
# solve and _MAX_NODES already bounds N.
_AUTO_SEED_COUNT = 8

# Maximum node count for force-directed Graph layout.
#
# The Fruchterman-Reingold implementation below is O(N^2) per
# iteration, so constructing a 1000-node graph takes ~10 seconds and
# blocks the renderer (a DoS vector for a malicious editorial).
#
# 100 is a generous upper bound for visualisations — viewers cannot
# meaningfully distinguish more than ~100 nodes in a single frame
# anyway. Scenes needing more nodes should use ``layout="stable"``
# (itself capped at 20 nodes) or split the graph across frames.
#
# See Wave 4B Cluster 1 DoS fix for the original finding.
_MAX_NODES = 100

# Minimum gap (in px) between the outer edges of two node circles after
# the collision-resolution post-pass.  The actual minimum center-to-center
# distance is ``2 * _NODE_RADIUS + _NODE_OVERLAP_GAP``.
_NODE_OVERLAP_GAP = 12

# Height (in px) of the band along the bottom reserved for the isolated-node
# lane when a force layout has degree-0 nodes.  Connected nodes are clamped to
# ``[_PADDING, height - _PADDING - _ISOLATED_LANE_BAND]`` and the lane sits at
# ``height - _PADDING - _NODE_RADIUS``.  Sized so the lane's y is at least the
# min center-to-center separation (``2*_NODE_RADIUS + _NODE_OVERLAP_GAP``)
# below the lowest possible connected node, making isolated-vs-connected
# overlap impossible regardless of x.
_ISOLATED_LANE_BAND = 3 * _NODE_RADIUS + _NODE_OVERLAP_GAP

# Edge weight pill — see docs/spec/graph-edge-pill-ruleset.md (GEP-02/03/04).
_WEIGHT_FONT: int = _DEFAULT_LABEL_FONT_PX  # annotation-font token (C4)
# B-2 reconciliation: the earlier FP-3 pass aliased plane2d's pill metrics
# to the canonical _LABEL_PILL_* but skipped graph — the copies had drifted
# to 5/2/3 vs 6/3/4. One pill token now (guarded by test_layout_constant_sync);
# if design ever wants tighter weight pills, pin them apart explicitly there.
_WEIGHT_PILL_PAD_X: int = _LABEL_PILL_PAD_X
_WEIGHT_PILL_PAD_Y: int = _LABEL_PILL_PAD_Y
_WEIGHT_PILL_R: int = _LABEL_PILL_RADIUS
# Perpendicular offset from stroke centerline to pill centre (GEP-06 v1.1).
# v1.1: pill sits ON the edge stroke (Graphviz/Mermaid convention) rather than
# floating alongside — rotated pill already binds to edge direction visually,
# so an extra perp gap reads as detachment. Nudge only kicks in on collision.
# v1.2 (GEP-07): along-edge shift is the primary collision resolution; perp
# nudge is a fallback only when the visible segment is too short to slide.
_WEIGHT_PILL_PERP_BIAS: float = 0.0
# Stroke-width expansion of the pill AABB for collision (GEP-09).
_WEIGHT_PILL_STROKE_PAD: float = 1.0
# Coincident-edge early-exit threshold (GEP-11).
_WEIGHT_EDGE_MIN_LEN: float = 4.0

# C2 antiparallel curved edges. When a *directed* graph holds both (u,v) and
# (v,u) (forward + residual in flow editorials), each edge bows onto its own
# side by this many px at the curve midpoint (apex), so the two arrows and
# their f/c pills separate into readable arcs instead of overlapping on one
# straight line. The quadratic control point sits at TWICE this distance,
# because a quadratic Bézier's apex deviation is half its control offset.
_ANTIPARALLEL_CURVE_OFFSET: float = 12.0

# Minimum leader-line length gate (GEP-17).  When the computed perpendicular
# offset is smaller than this value the leader is suppressed and the function
# falls back to the silent origin (leader=False, stage="origin").
_GEP17_MIN_LEADER_PX: float = 4.0

# Phase 6 (U-03) — pill background tint map keyed by source-node state.
# Light hues that stay legible over edge strokes and preserve pill/text
# contrast.  Returned from _pill_tint_for_state for ``tint_by_source=True``.
#
# NOTE: these tints are a presentation-only companion to the state colours
# in scriba.animation.primitives.base.THEME / svg_style_attrs. They are NOT
# derived programmatically — Phase 6 treats the tint palette as an
# independent design surface so callers can adjust pill contrast without
# touching node strokes / fills. Keep in sync manually when the primary
# state palette changes; see GEP-19 in docs/spec/graph-edge-pill-ruleset.md.
#
# Dark-mode caveat: the palette is light-mode-only. Rendering these tints
# on a dark scene background will drop contrast against edge strokes. A
# dark-mode companion palette is scheduled as a fast-follow once GEP-19
# lands visual regression coverage; until then callers wanting dark-mode
# pills should leave tint_by_source=False.
_PILL_TINT_BY_STATE: dict[str, str] = {
    "idle": "#eff6ff",      # subtle blue tint
    "active": "#dbeafe",    # stronger blue for active traversal
    "visited": "#ecfdf5",   # pale green for already-visited
    "complete": "#ecfdf5",
    "highlight": "#fef3c7", # amber highlight
    "error": "#fee2e2",     # red error
}


def _pill_tint_for_state(state: str) -> str:
    """Return the pill background tint for a given source-node state (GEP-19)."""
    return _PILL_TINT_BY_STATE.get(state, "#eff6ff")


# Phase 7 (smart-label v2.0) — pill background tint map keyed by edge state.
# Harmonises with the edge stroke palette so pill fill tracks edge colour
# when tint_by_edge=True.  Light hues (~90 %+ lightness) keep text legible.
_PILL_TINT_BY_EDGE_STATE: dict[str, str] = {
    "idle":        "#ffffff",  # neutral — no visual noise on resting edges
    "current":     "#dbeafe",  # light blue (matches current stroke hue)
    "good":        "#d1fae5",  # light green
    "bad":         "#fee2e2",  # light red
    "done":        "#f3f4f6",  # light gray
    "dim":         "#f9fafb",  # very light gray
    "active":      "#dbeafe",  # same hue family as current
    "highlighted": "#fef3c7",  # amber
    "muted":       "#f3f4f6",  # light gray
}


def _pill_tint_for_edge_state(state: str) -> str:
    """Return the pill background tint for a given edge state (smart-label v2.0)."""
    return _PILL_TINT_BY_EDGE_STATE.get(state, "#ffffff")


# ---------------------------------------------------------------------------
# GEP-17 — PillPlacement return type (NamedTuple for positional back-compat)
# ---------------------------------------------------------------------------

class PillPlacement(NamedTuple):
    """Return type for _nudge_pill_placement (GEP-17 v1.4.0).

    Fields 0 and 1 are x/y so existing ``lx, ly = _nudge_pill_placement(...)``
    callers continue to work without modification (NamedTuple positional
    unpacking).
    """

    x: float
    y: float
    leader: bool
    anchor_x: float
    anchor_y: float
    stage: str  # "origin" | "along" | "saturate" | "perp" | "leader"


# Regex to parse annotation selectors like "G.node[A]" or "G.node[myNode]"
_GRAPH_NODE_SEL_RE = re.compile(r"^(?P<name>\w+)\.node\[(?P<id>.+)\]$")


# ---------------------------------------------------------------------------
# GEP-16 v1.3.2 — on-stroke runtime invariant check (debug mode)
# ---------------------------------------------------------------------------


def _assert_on_stroke(
    cx: float,
    cy: float,
    mid_x: float,
    mid_y: float,
    ux: float,
    uy: float,
    stage: str,
) -> None:
    """U-14 runtime check. No-op unless SCRIBA_DEBUG=1.

    Raises AssertionError if pill center distance to infinite edge line > 0.5 px.
    """
    if os.environ.get("SCRIBA_DEBUG") != "1":
        return
    perp_dist = abs((cx - mid_x) * (-uy) + (cy - mid_y) * ux)
    assert perp_dist <= 0.5, (
        f"U-14 on-stroke violated at stage {stage!r}: "
        f"pill centre ({cx:.4f}, {cy:.4f}) is {perp_dist:.4f} px off stroke"
    )


# ---------------------------------------------------------------------------
# GEP-07 v1.2 — pill nudge helper (pure, testable without SVG)
# ---------------------------------------------------------------------------


def _nudge_pill_placement(
    mid_x: float,
    mid_y: float,
    ux: float,
    uy: float,
    perp_x: float,
    perp_y: float,
    pill_w: float,
    pill_h: float,
    aabb_w: float,
    aabb_h: float,
    max_shift_along: float,
    node_aabbs: list[_LabelPlacement],
    placed_pills: list[_LabelPlacement],
    graph_centroid: tuple[float, float] | None = None,
) -> PillPlacement:
    """Return a PillPlacement after GEP-07 v1.2 / GEP-17 v1.4 nudge.

    Stage 1 — along-edge shift: slides pill on the stroke, preserving
    GEP-10 edge binding.  Skipped when max_shift_along == 0 (short edges).
    Stage 1.5 — saturate probe: try ±max_shift_along exact (GEP-14).
    Stage 2 — perp nudge fallback: v1.1 behaviour, used only when along-
    shift is exhausted or budget is zero.
    Stage 3 / leader — when graph_centroid is provided and all prior stages
    are blocked, a leader line is emitted and the pill is placed on the far
    side of the midpoint from the centroid (GEP-17 v1.4.0).  When
    graph_centroid is None the legacy silent-origin fallback fires.

    The returned NamedTuple's fields [0] and [1] are x/y respectively, so
    existing ``lx, ly = _nudge_pill_placement(...)`` callers continue to work.

    All obstacle lists are consulted as-is; caller must not mutate them
    between construction and this call.
    """
    def _collides(c: _LabelPlacement) -> bool:
        return any(c.overlaps(p) for p in placed_pills) or any(
            c.overlaps(n) for n in node_aabbs
        )

    origin_lx, origin_ly = mid_x, mid_y
    candidate = _LabelPlacement(x=origin_lx, y=origin_ly, width=aabb_w, height=aabb_h)

    if not _collides(candidate):
        _assert_on_stroke(origin_lx, origin_ly, mid_x, mid_y, ux, uy, "origin")
        return PillPlacement(origin_lx, origin_ly, False, mid_x, mid_y, "origin")

    # Step against the rotated AABB, not the un-rotated pill box: on angled
    # edges aabb_w / aabb_h swell to ~pill·√2, so step=pill_w+2 would leave
    # residual overlap between neighbouring rotated pills. Using aabb_* + 2
    # guarantees the first probe clears the previous pill's footprint.
    nudge_step_along = aabb_w + 2
    nudge_step_perp = aabb_h + 2

    # Stage 1 — along-edge shift (preserves GEP-10 binding).
    for offset in (
        nudge_step_along,
        -nudge_step_along,
        2 * nudge_step_along,
        -2 * nudge_step_along,
    ):
        if abs(offset) > max_shift_along:
            continue
        trial_lx = origin_lx + ux * offset
        trial_ly = origin_ly + uy * offset
        trial = _LabelPlacement(x=trial_lx, y=trial_ly, width=aabb_w, height=aabb_h)
        if not _collides(trial):
            _assert_on_stroke(trial_lx, trial_ly, mid_x, mid_y, ux, uy, "along")
            return PillPlacement(trial_lx, trial_ly, False, mid_x, mid_y, "along")

    # Stage 1.5 — saturate probe (GEP-14 v1.3): try pill at exactly
    # ±max_shift_along before falling through to perp.  Preserves U-14
    # on-stroke invariant because displacement is purely along (ux, uy).
    if max_shift_along > 0:
        for sign in (1, -1):
            sat_lx = origin_lx + sign * max_shift_along * ux
            sat_ly = origin_ly + sign * max_shift_along * uy
            sat = _LabelPlacement(x=sat_lx, y=sat_ly, width=aabb_w, height=aabb_h)
            if not _collides(sat):
                _assert_on_stroke(sat_lx, sat_ly, mid_x, mid_y, ux, uy, "saturate")
                return PillPlacement(sat_lx, sat_ly, False, mid_x, mid_y, "saturate")

    # Stage 2 — perp nudge fallback (v1.3 behaviour, GEP-15).
    # Candidate order [+s, +2s, -s, -2s]: exhaust the right-hand side (initial
    # + direction = right-hand of edge via perp_x/perp_y) before switching
    # sides.  Prevents pill flicker when two near-identical scenes produce
    # different orderings under the old [+s, -s, +2s, -2s] sequence (U-10).
    for offset in (
        nudge_step_perp,
        2 * nudge_step_perp,
        -nudge_step_perp,
        -2 * nudge_step_perp,
    ):
        trial_lx = origin_lx + perp_x * offset
        trial_ly = origin_ly + perp_y * offset
        trial = _LabelPlacement(x=trial_lx, y=trial_ly, width=aabb_w, height=aabb_h)
        if not _collides(trial):
            return PillPlacement(trial_lx, trial_ly, False, mid_x, mid_y, "perp")

    # Stage 3 / GEP-17 leader fallback.
    # When graph_centroid is None → legacy silent-origin fallback (leader=False).
    # When graph_centroid is provided → attempt a leader-line placement on the
    # far side of the midpoint from the centroid.
    if graph_centroid is not None:
        leader_offset = 2.0 * aabb_h + _WEIGHT_PILL_PAD_Y
        if leader_offset >= _GEP17_MIN_LEADER_PX:
            cx, cy = graph_centroid
            # Place the pill away from the centroid: use the unit vector from
            # centroid toward midpoint as the push direction.
            vec_x = mid_x - cx
            vec_y = mid_y - cy
            vec_len = math.hypot(vec_x, vec_y)
            if vec_len < 1e-9:
                # Centroid coincides with midpoint: default to (perp_x, perp_y).
                dir_x, dir_y = perp_x, perp_y
            else:
                dir_x = vec_x / vec_len
                dir_y = vec_y / vec_len
            pill_x = mid_x + dir_x * leader_offset
            pill_y = mid_y + dir_y * leader_offset
            return PillPlacement(pill_x, pill_y, True, mid_x, mid_y, "leader")

    # Origin fallback: touching beats detached (legacy stage 3 + min-gate path).
    return PillPlacement(origin_lx, origin_ly, False, mid_x, mid_y, "origin")


# ---------------------------------------------------------------------------
# GEP-17 — leader-line SVG helper
# ---------------------------------------------------------------------------


def _emit_leader_line(
    x1: float, y1: float, x2: float, y2: float, stroke_color: str
) -> str:
    """Return an SVG <line> string for a GEP-17 leader line.

    Emitted BEFORE the pill rect so the pill renders on top.
    stroke-dasharray="3,2" distinguishes the leader from edge strokes.
    """
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"'
        f' stroke="{stroke_color}" stroke-width="0.8" stroke-dasharray="3,2"/>'
    )


# ---------------------------------------------------------------------------
# Fruchterman-Reingold layout
# ---------------------------------------------------------------------------


def _resolve_overlaps(
    pos: dict[str | int, tuple[float, float]],
    nodes: list[str | int],
    min_sep: float,
    width: int,
    height: int,
    passes: int = 10,
    max_y: float | None = None,
) -> None:
    """Push apart any node pair closer than *min_sep* (in-place).

    A simple iterative collision-resolution post-pass.  For each pair
    within *min_sep*, both nodes are displaced by half the deficit along
    the line connecting them.  Multiple passes handle cascades where
    resolving one collision creates another.

    Clamped to ``[_PADDING, width - _PADDING]`` in x and
    ``[_PADDING, max_y]`` in y so nodes stay inside the canvas.  *max_y*
    defaults to ``height - _PADDING``; pass a smaller value to reserve a
    band along the bottom (e.g. for an isolated-node lane).
    """
    if max_y is None:
        max_y = height - _PADDING
    for _ in range(passes):
        moved = False
        for i, u in enumerate(nodes):
            for v in nodes[i + 1:]:
                dx = pos[u][0] - pos[v][0]
                dy = pos[u][1] - pos[v][1]
                d = math.sqrt(dx * dx + dy * dy)
                if d < min_sep:
                    moved = True
                    # Push apart along the connecting line (or along x
                    # if they're at the exact same position).
                    if d < 0.01:
                        dx, dy, d = 1.0, 0.0, 1.0
                    deficit = (min_sep - d) / 2.0 + 0.5
                    shift_x = deficit * dx / d
                    shift_y = deficit * dy / d
                    pos[u] = (
                        max(_PADDING, min(width - _PADDING, pos[u][0] + shift_x)),
                        max(_PADDING, min(max_y, pos[u][1] + shift_y)),
                    )
                    pos[v] = (
                        max(_PADDING, min(width - _PADDING, pos[v][0] - shift_x)),
                        max(_PADDING, min(max_y, pos[v][1] - shift_y)),
                    )
        if not moved:
            break


def _place_isolated_lane(
    connected_pos: dict[str | int, tuple[float, float]],
    isolated: list[str | int],
    width: int,
    height: int,
) -> dict[str | int, tuple[int, int]]:
    """Round connected positions and append *isolated* nodes in a tidy lane.

    Isolated (degree-0) nodes are placed in a deterministic reserved lane: a
    single evenly-spaced row inside the reserved bottom band at
    ``height - _PADDING - _NODE_RADIUS`` (strictly inside the canvas, not on
    the bottom border), spanning ``[_PADDING, width - _PADDING]`` in
    node-declaration order.  This keeps them inside the canvas instead of
    being flung to a corner by repulsion.
    """
    result: dict[str | int, tuple[int, int]] = {
        node: (round(x), round(y)) for node, (x, y) in connected_pos.items()
    }
    if not isolated:
        return result

    lane_y = height - _PADDING - _NODE_RADIUS
    count = len(isolated)
    if count == 1:
        xs = [width / 2.0]
    else:
        span = (width - 2 * _PADDING) / (count - 1)
        xs = [_PADDING + i * span for i in range(count)]
    for node, x in zip(isolated, xs):
        result[node] = (round(x), round(lane_y))
    return result


def fruchterman_reingold(
    nodes: list[str | int],
    edges: list[tuple[str | int, str | int]],
    *,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    seed: int = _DEFAULT_SEED,
    iterations: int = _DEFAULT_ITERATIONS,
    node_radius: int = _NODE_RADIUS,
) -> dict[str | int, tuple[int, int]]:
    """Compute force-directed node positions.

    Returns a dict mapping each node identifier to an ``(x, y)`` integer
    coordinate pair.  Layout is deterministic for a given *seed*.

    After force-directed convergence, a collision-resolution post-pass
    guarantees no two nodes overlap (minimum separation =
    ``2 * node_radius + _NODE_OVERLAP_GAP``).
    """
    n = len(nodes)
    if n == 0:
        return {}
    if n == 1:
        return {nodes[0]: (width // 2, height // 2)}

    # Isolated nodes (degree 0) feel only repulsion, so the force solve flings
    # them to a corner.  Exclude them from the solve and place them
    # deterministically in a reserved lane afterwards.  When there are no
    # isolated nodes, ``connected`` == ``nodes`` and the solve below is
    # byte-identical to running on ``nodes`` directly.
    incident: set[str | int] = set()
    for u, v in edges:
        incident.add(u)
        incident.add(v)
    connected = [node for node in nodes if node in incident]
    isolated = [node for node in nodes if node not in incident]

    if not connected:
        # Every node is isolated (no edges at all): lay them out in a tidy
        # even row instead of leaving them random-cornered.
        return _place_isolated_lane({}, isolated, width, height)

    n = len(connected)
    if n == 1:
        pos_single = {connected[0]: (width / 2.0, height / 2.0)}
        return _place_isolated_lane(pos_single, isolated, width, height)

    # When isolated nodes exist, reserve a band along the bottom for their
    # lane and keep the connected solve in the upper region so the two regions
    # are disjoint in y (no isolated-vs-connected overlap is possible).  With
    # no isolated nodes the clamp stays ``height - _PADDING`` so the solve is
    # byte-identical to the pre-fix behaviour.
    solve_max_y = height - _PADDING
    if isolated:
        solve_max_y = height - _PADDING - _ISOLATED_LANE_BAND

    area = width * height
    k = math.sqrt(area / n)  # optimal inter-node distance

    rng = random.Random(seed)
    pos: dict[str | int, tuple[float, float]] = {
        node: (rng.uniform(_PADDING, width - _PADDING),
               rng.uniform(_PADDING, solve_max_y))
        for node in connected
    }

    t = width / 10.0  # initial temperature
    dt = t / (iterations + 1)

    for _ in range(iterations):
        disp: dict[str | int, list[float]] = {node: [0.0, 0.0] for node in connected}

        # Repulsive forces between all node pairs
        for i, u in enumerate(connected):
            for v in connected[i + 1:]:
                dx = pos[u][0] - pos[v][0]
                dy = pos[u][1] - pos[v][1]
                d = max(math.sqrt(dx * dx + dy * dy), 0.01)
                force = k * k / d
                fx = force * dx / d
                fy = force * dy / d
                disp[u][0] += fx
                disp[u][1] += fy
                disp[v][0] -= fx
                disp[v][1] -= fy

        # Attractive forces along edges
        for u, v in edges:
            dx = pos[u][0] - pos[v][0]
            dy = pos[u][1] - pos[v][1]
            d = max(math.sqrt(dx * dx + dy * dy), 0.01)
            force = d * d / k
            fx = force * dx / d
            fy = force * dy / d
            disp[u][0] -= fx
            disp[u][1] -= fy
            disp[v][0] += fx
            disp[v][1] += fy

        # Apply displacement with temperature limit
        for node in connected:
            ndx, ndy = disp[node]
            d = max(math.sqrt(ndx * ndx + ndy * ndy), 0.01)
            move_x = ndx / d * min(abs(ndx), t)
            move_y = ndy / d * min(abs(ndy), t)
            new_x = max(_PADDING, min(width - _PADDING, pos[node][0] + move_x))
            new_y = max(_PADDING, min(solve_max_y, pos[node][1] + move_y))
            pos[node] = (new_x, new_y)

        t -= dt

    # Post-pass: guarantee no two nodes overlap.  The force-directed
    # algorithm converges to an equilibrium that can leave nodes within
    # 2*radius of each other when repulsion is balanced by attractive
    # edge forces or boundary constraints.
    min_sep = 2.0 * node_radius + _NODE_OVERLAP_GAP
    _resolve_overlaps(pos, connected, min_sep, width, height, max_y=solve_max_y)

    return _place_isolated_lane(pos, isolated, width, height)


def map_manual_positions(
    coords: dict[str | int, tuple[float, float]],
    *,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
) -> dict[str | int, tuple[int, int]]:
    """Map author-supplied abstract coordinates into canvas pixel space.

    *coords* maps every node id to an ``(x, y)`` pair in an arbitrary author
    coordinate system (e.g. an FFT butterfly's ``(column, row)`` lattice). The
    author frame is scaled **uniformly** — aspect ratio preserved, so geometric
    and planar graphs keep their true proportions — and centred inside the
    drawable region ``[_PADDING, width - _PADDING] x [_PADDING, height -
    _PADDING]`` (the same bounds ``fruchterman_reingold`` clamps to).

    Screen convention: x grows right, y grows **down** — identical to the force
    and hierarchical solves, so the node with the smallest author y sits at the
    top. Returns integer pixel coordinates like every other layout, so the emit
    path is byte-for-byte the same shape regardless of how positions were
    decided.
    """
    if not coords:
        return {}
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x
    span_y = max_y - min_y
    avail_w = width - 2 * _PADDING
    avail_h = height - 2 * _PADDING
    # Uniform scale: the tighter axis governs so nothing spills the canvas. A
    # zero span on an axis means every node shares that coordinate — it is then
    # centred by the offset below (scale on that axis is irrelevant).
    if span_x > 0 and span_y > 0:
        scale = min(avail_w / span_x, avail_h / span_y)
    elif span_x > 0:
        scale = avail_w / span_x
    elif span_y > 0:
        scale = avail_h / span_y
    else:
        scale = 1.0  # single node or all-coincident: centre everything
    off_x = _PADDING + (avail_w - span_x * scale) / 2.0
    off_y = _PADDING + (avail_h - span_y * scale) / 2.0
    return {
        node: (
            round(off_x + (ax - min_x) * scale),
            round(off_y + (ay - min_y) * scale),
        )
        for node, (ax, ay) in coords.items()
    }


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------


def _format_weight(weight: float) -> str:
    """Format an edge weight for SVG display.

    Integers render without a decimal (``"3"``); floats keep up to
    three significant digits and trim trailing zeros (``"1.5"``).
    """
    if weight == int(weight):
        return str(int(weight))
    formatted = f"{weight:.3g}"
    return formatted


def _shorten_line_to_circle(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    radius: int,
) -> tuple[int, int]:
    """Move ``(x2, y2)`` back along the line by *radius* pixels.

    Used for directed edges so the arrowhead sits at the circle boundary
    rather than at the centre.
    """
    dx = x2 - x1
    dy = y2 - y1
    d = max(math.sqrt(dx * dx + dy * dy), 0.01)
    return (round(x2 - radius * dx / d), round(y2 - radius * dy / d))


# ---------------------------------------------------------------------------
# Graph primitive
# ---------------------------------------------------------------------------


@register_primitive("Graph")
@_protocol_register
class Graph(PrimitiveBase):
    """Force-directed graph primitive.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``G``).
    params:
        Dictionary of parameters from the ``\\shape`` command.  Required keys
        are ``nodes`` and ``edges``.  Optional keys: ``directed``,
        ``layout``, ``layout_seed``, ``label``.

    Seed canonicalization
    ---------------------
    The spec canonical key is ``layout_seed`` (see ``docs/spec/primitives.md``
    §6).  A bare ``seed`` key is accepted as a convenience alias when
    ``layout_seed`` is absent.  The value must be a non-negative ``int``;
    anything else raises ``E1505``.
    """

    primitive_type = "graph"
    # \apply edge-mutation verbs (node value= handled generically).
    APPLY_KEYS: ClassVar[frozenset[str]] = frozenset(
        {"add_edge", "remove_edge", "set_weight"}
    )

    # DECORATE v4: a \trace threads a polyline through node centres ("follow the
    # edges"). resolve_annotation_point already returns the node centre, so the
    # shipped emit_traces_under decoration draws the sweep with no new machinery.
    supports_trace: ClassVar[bool] = True

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "node[{id}]": "node by id",
        "edge[({u},{v})]": "edge by endpoints",
        "all": "all nodes and edges",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "nodes",
        "edges",
        "directed",
        "layout",
        "positions",
        "layout_seed",
        "seed",
        "show_weights",
        "label",
        "auto_expand",
        "split_labels",
        "tint_by_source",
        "tint_by_edge",
        "global_optimize",
        "orientation",
    })

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        self.nodes: list[str | int] = coerce_list(
            params.get("nodes", []),
            "E1470",
            detail=(
                f"Graph '{name}' 'nodes' must be a list, got "
                f"{params.get('nodes')!r}"
            ),
            hint="example: Graph{g}{nodes=[\"a\", \"b\"], edges=[(\"a\", \"b\")]}",
        )
        if not self.nodes:
            raise _animation_error(
                "E1470",
                detail=(
                    f"Graph '{name}' requires a non-empty 'nodes' list; "
                    "got an empty or missing 'nodes' parameter"
                ),
                hint="example: Graph{g}{nodes=[\"a\", \"b\"], edges=[(\"a\", \"b\")]}",
            )
        if len(self.nodes) > _MAX_NODES:
            # Force-directed layout is O(N^2) per iteration; reject
            # oversized graphs up front rather than letting a
            # malicious editorial burn seconds of renderer time.
            raise _animation_error(
                "E1501",
                detail=(
                    f"Graph '{name}' node count {len(self.nodes)} "
                    f"exceeds maximum {_MAX_NODES}; use layout=stable "
                    f"for larger graphs or split the visualization"
                ),
            )
        raw_edges = params.get("edges", [])
        parsed_edges: list[tuple[str | int, str | int, float | None]] = []
        has_weighted = False
        has_unweighted = False
        for e in raw_edges:
            if len(e) == 3:
                parsed_edges.append((e[0], e[1], float(e[2])))
                has_weighted = True
            elif len(e) == 2:
                parsed_edges.append((e[0], e[1], None))
                has_unweighted = True
            else:
                raise _animation_error(
                    "E1474",
                    detail=f"edge must be 2-tuple or 3-tuple, got {e!r}",
                )
        if has_weighted and has_unweighted:
            raise _animation_error(
                "E1474",
                detail="edges list mixes weighted and unweighted entries",
            )
        self.edges: list[tuple[str | int, str | int, float | None]] = parsed_edges
        # Author guidance (Phase 4): a partially-connected graph that leaves
        # some node with no edge places that node in the isolated-node lane.
        # That is usually an oversight, so surface a soft, one-time note
        # pointing to the fix. Only warn when the graph DOES have edges (a
        # pure node-set with no edges is an intentional display, not a slip).
        # Suppressed under manual `positions`: a pinned node is placed exactly
        # where the author put it (isolated vertices are then intentional, e.g.
        # a lone point in a geometric graph), so the "flung to a lane" remedy
        # would be false.
        if self.edges and params.get("positions") is None:
            _incident: set[str | int] = set()
            for _u, _v, _w in self.edges:
                _incident.add(_u)
                _incident.add(_v)
            _isolated = [n for n in self.nodes if n not in _incident]
            if _isolated:
                import warnings as _w
                _w.warn(
                    f"Graph '{name}' has node(s) with no edges "
                    f"({', '.join(str(n) for n in _isolated)}); they are "
                    "placed in a separate lane. If this is unintended, declare "
                    "their edges up front, or use layout='stable' for a small "
                    "graph. See docs/SCRIBA-TEX-REFERENCE.md §7.4 best practices.",
                    UserWarning,
                    stacklevel=2,
                )
        self.directed: bool = bool(params.get("directed", False))
        self.layout: str = str(params.get("layout", "force"))
        # Hierarchical-only axis: "TB" (top→bottom, default) or "LR"
        # (left→right). Silently ignored for non-hierarchical layouts;
        # compute_hierarchical_layout returns None for unknown values,
        # which makes the caller fall back to FR.
        self.orientation: str = str(params.get("orientation", "TB"))
        # Emit a UserWarning when editorials pair layout="stable" with a
        # directed graph. The stable SA optimizer is topology-blind (no
        # edge-direction term), so DAGs frequently render upside-down or
        # sideways. See docs/archive/stable-layout-chaos-analysis-2026-04-23.
        if self.layout == "stable" and self.directed:
            import warnings as _w
            _w.warn(
                "Graph(layout='stable', directed=True) — the stable layout "
                "does not respect edge direction and often produces "
                "upside-down or sideways DAGs. Use layout='hierarchical' or "
                "layout='auto' for directed graphs.",
                UserWarning,
                stacklevel=2,
            )
        self.show_weights: bool = bool(params.get("show_weights", False))
        self.auto_expand: bool = bool(params.get("auto_expand", False))
        # Phase 6 (U-03) — typography + tint opt-ins. Default False keeps
        # byte-stable SVG for existing goldens.
        self.split_labels: bool = bool(params.get("split_labels", False))
        self.tint_by_source: bool = bool(params.get("tint_by_source", False))
        self.tint_by_edge: bool = bool(params.get("tint_by_edge", False))
        # Phase 7 (GEP-20) — opt-in simulated-annealing post-cascade refine.
        # Default False keeps byte-stable output. The emit_svg wiring lands
        # in v2.1; the flag is accepted here so editorials can opt in
        # without raising E1474 once wiring ships. When the caller opts in
        # today, surface a UserWarning so the no-op is explicit rather than
        # silent — otherwise a misconfigured editorial could believe SA is
        # running when in fact the cascade alone produced the output.
        self.global_optimize: bool = bool(params.get("global_optimize", False))
        if self.global_optimize:
            import warnings as _w
            _w.warn(
                "Graph(global_optimize=True) is accepted as a v2.1 forward-"
                "compat flag but has no runtime effect yet — the simulated-"
                "annealing refine (GEP-20) is currently only available as a "
                "pure primitive in scriba.animation.primitives._pill_refine. "
                "emit_svg wiring ships in GEP v2.1.",
                UserWarning,
                stacklevel=2,
            )

        # --- layout_seed validation (E1505) ---
        #
        # The spec canonical name is ``layout_seed``.  We also accept a bare
        # ``seed`` as an alias if ``layout_seed`` was not supplied (for
        # convenience and because ``fruchterman_reingold`` itself uses
        # ``seed=``).  If both are present, ``layout_seed`` wins.
        # Track whether the author explicitly pinned a seed. An explicit seed
        # (even one equal to the default 42) must always win for
        # reproducibility — no auto-seed sweep. Absent seed -> auto-seed
        # selection for layout="force" (Phase 3).
        self._seed_pinned: bool = "layout_seed" in params or "seed" in params
        if "layout_seed" in params:
            raw_seed: Any = params["layout_seed"]
        elif "seed" in params:
            raw_seed = params["seed"]
        else:
            raw_seed = _DEFAULT_SEED

        # Reject ``bool`` explicitly: in Python ``bool`` is a subclass of
        # ``int`` but ``True``/``False`` as a seed is almost certainly a
        # programming mistake.
        if isinstance(raw_seed, bool) or not isinstance(raw_seed, int):
            raise _animation_error(
                "E1505",
                f"Graph layout_seed must be a non-negative integer, "
                f"got {type(raw_seed).__name__} {raw_seed!r}",
            )
        if raw_seed < 0:
            raise _animation_error(
                "E1505",
                f"Graph layout_seed must be a non-negative integer, "
                f"got {raw_seed}",
            )
        self.layout_seed: int = raw_seed

        self.label: str | None = params.get("label")

        # Manual node placement (census gap #3). When the author supplies
        # ``positions``, every node is PINNED to the mapped author coordinate
        # and the force / hierarchical / stable solvers are bypassed — this is
        # what lets FFT-butterfly, planar, and geometric graphs draw at true
        # coordinates. Parsed to author-space coords here (needs the node set);
        # the pixel mapping happens once in the layout block below. Absent
        # ``positions`` leaves this None so the existing code path is untouched.
        self._manual_positions: dict[str | int, tuple[float, float]] | None = (
            self._parse_manual_positions(params["positions"])
            if params.get("positions") is not None
            else None
        )

        self.width: int = _DEFAULT_WIDTH
        self.height: int = _DEFAULT_HEIGHT

        # Scale node radius with density so dense graphs don't overlap
        self._node_radius: int = max(
            _NODE_MIN_RADIUS,
            min(
                _NODE_RADIUS,
                int(min(self.width, self.height) / (2 * max(len(self.nodes), 1))),
            ),
        )
        self._arrow_cell_height = float(self._node_radius * 2)
        self._arrow_layout = "2d"
        self._arrow_shorten = float(self._node_radius)

        # Manual placement wins over every solver: pin each node to its mapped
        # author coordinate and stop. Positions are computed once and never
        # move between frames (the node set is fixed, so edge mutations keep
        # these coordinates — R-32 pin-stability by construction).
        if self._manual_positions is not None:
            self.positions = map_manual_positions(
                self._manual_positions, width=self.width, height=self.height
            )
            return

        # Compute positions. layout="stable" routes to the stable-layout
        # primitive so the documented flag actually takes effect on the
        # first frame (previously it only engaged after a mutation).
        if self.layout == "stable":
            from scriba.animation.primitives.graph_layout_stable import (
                compute_stable_layout,
            )
            frame_edges = [[(str(u), str(v)) for u, v, _w in self.edges]]
            stable = compute_stable_layout(
                [str(n) for n in self.nodes],
                frame_edges,
                seed=self.layout_seed,
                width=self.width,
                height=self.height,
                node_radius=self._node_radius,
            )
            if stable is not None:
                self.positions = {
                    n: (round(stable[str(n)][0]), round(stable[str(n)][1]))
                    for n in self.nodes
                }
                return
            # Size guard tripped — fall through to FR default.
        elif self.layout == "auto":
            # Smart dispatch: route directed DAGs to the Sugiyama layout
            # (visible hierarchy); everything else to Fruchterman-Reingold.
            # "Is it a DAG?" is probed by _break_cycles — an empty
            # reversed-edge set means no back-edges were found.
            _is_dag = False
            if self.directed:
                from scriba.animation.primitives.graph_layout_hierarchical import (
                    _break_cycles,
                )
                _dag_edges, _rev = _break_cycles(
                    [str(n) for n in self.nodes],
                    [(str(u), str(v)) for u, v, _w in self.edges],
                )
                _is_dag = (len(_rev) == 0)
            if _is_dag:
                # Resolved to hierarchical — rewrite self.layout so the
                # dispatch below + downstream code (e.g. mutation warm-start)
                # see the concrete choice, not "auto".
                self.layout = "hierarchical"
        if self.layout == "hierarchical":
            from scriba.animation.primitives.graph_layout_hierarchical import (
                compute_hierarchical_layout,
            )
            frame_edges = [[(str(u), str(v)) for u, v, _w in self.edges]]
            hier = compute_hierarchical_layout(
                [str(n) for n in self.nodes],
                frame_edges,
                seed=self.layout_seed,
                width=self.width,
                height=self.height,
                node_radius=self._node_radius,
                orientation=self.orientation,
            )
            if hier is not None:
                self.positions = {
                    n: (round(hier[str(n)][0]), round(hier[str(n)][1]))
                    for n in self.nodes
                }
                # Expand viewport to encompass layered positions — the
                # hierarchical layout enforces a minimum layer gap so
                # edge pills fit, which may push coords past the
                # default width/height. Pad by node_radius + _PADDING//2
                # to match the layout's own interior padding.
                if hier:
                    pad = self._node_radius + _PADDING // 2
                    max_x = max(pos[0] for pos in hier.values())
                    max_y = max(pos[1] for pos in hier.values())
                    self.width = max(self.width, int(max_x + pad))
                    self.height = max(self.height, int(max_y + pad))
                return
            # Invalid orientation or empty — fall through to FR default.

        fr_edges = [(u, v) for u, v, _w in self.edges]
        if self._seed_pinned:
            # Author pinned a seed (or alias): use it directly, no sweep.
            # Byte-identical to the pre-Phase-3 behaviour.
            self.positions: dict[str | int, tuple[int, int]] = (
                fruchterman_reingold(
                    self.nodes,
                    fr_edges,
                    width=self.width,
                    height=self.height,
                    seed=self.layout_seed,
                )
            )
        else:
            # No pinned seed: sweep candidate seeds, score each layout, keep
            # the best (lowest score). Tie-break toward the smallest seed via
            # the (score, seed) key so the choice is fully deterministic.
            from scriba.animation.primitives.graph_layout_score import (
                score_layout,
            )
            best_positions: dict[str | int, tuple[int, int]] | None = None
            best_key: tuple[float, int] | None = None
            for cand in range(_AUTO_SEED_COUNT):
                cand_pos = fruchterman_reingold(
                    self.nodes,
                    fr_edges,
                    width=self.width,
                    height=self.height,
                    seed=cand,
                )
                cand_score = score_layout(
                    cand_pos, fr_edges, self.width, self.height
                )
                cand_key = (cand_score, cand)
                if best_key is None or cand_key < best_key:
                    best_key = cand_key
                    best_positions = cand_pos
            assert best_positions is not None  # _AUTO_SEED_COUNT >= 1
            self.positions = best_positions
            # Record the auto-selected seed for introspection / debugging
            # WITHOUT clobbering self.layout_seed (which keeps reporting the
            # resolved default for backward compatibility — see
            # test_default_seed_when_omitted).
            self._auto_seed: int = best_key[1]

    def _parse_manual_positions(
        self, raw: Any
    ) -> dict[str | int, tuple[float, float]]:
        """Validate the ``positions`` param into ``{node: (x, y)}`` author coords.

        v1 requires one ``(node_id, x, y)`` entry for **every** declared node —
        there is no partial-pin mode. Anything malformed (not a list, wrong
        arity, unknown / duplicated / missing node, non-numeric coordinate) is a
        loud ``E1475`` rather than a silent fall-back to force layout, so a
        hand-placed diagram never half-pins without the author noticing.
        """
        hint = (
            'positions=[("A", 0, 0), ("B", 2, 1)] — one (node, x, y) per '
            "declared node; x/y are numbers in any author units (scaled and "
            "centred to fit the canvas)."
        )
        entries = coerce_list(
            raw,
            "E1475",
            detail=(
                f"Graph '{self.name}' 'positions' must be a list of "
                f"(node, x, y) entries, got {raw!r}"
            ),
            hint=hint,
        )
        coords: dict[str | int, tuple[float, float]] = {}
        for entry in entries:
            if isinstance(entry, (str, bytes)) or not hasattr(entry, "__iter__"):
                raise _animation_error(
                    "E1475",
                    detail=(
                        f"Graph '{self.name}' positions entry must be "
                        f"(node, x, y), got {entry!r}"
                    ),
                    hint=hint,
                )
            parts = list(entry)
            if len(parts) != 3:
                raise _animation_error(
                    "E1475",
                    detail=(
                        f"Graph '{self.name}' positions entry must have exactly "
                        f"3 items (node, x, y), got {entry!r}"
                    ),
                    hint=hint,
                )
            node, ax, ay = parts
            if node not in self.nodes:
                raise _animation_error(
                    "E1475",
                    detail=(
                        f"Graph '{self.name}' positions references unknown node "
                        f"{node!r}; declared nodes: "
                        f"{', '.join(repr(n) for n in self.nodes)}"
                    ),
                    hint=hint,
                )
            if node in coords:
                raise _animation_error(
                    "E1475",
                    detail=(
                        f"Graph '{self.name}' pins node {node!r} more than once"
                    ),
                    hint=hint,
                )
            for axis, val in (("x", ax), ("y", ay)):
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise _animation_error(
                        "E1475",
                        detail=(
                            f"Graph '{self.name}' position {axis} for node "
                            f"{node!r} must be a number, got {val!r}"
                        ),
                        hint=hint,
                    )
            coords[node] = (float(ax), float(ay))
        missing = [n for n in self.nodes if n not in coords]
        if missing:
            raise _animation_error(
                "E1475",
                detail=(
                    f"Graph '{self.name}' positions must cover every node; "
                    f"missing: {', '.join(repr(n) for n in missing)}"
                ),
                hint=hint,
            )
        return coords

    # ----- mutation API ----------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Apply a mutation command from the animation pipeline.

        Supported ops (one per call):
            - ``add_edge``: {"from": u, "to": v, "weight": w?}
            - ``remove_edge``: {"from": u, "to": v}
            - ``set_weight``: {"from": u, "to": v, "value": w}

        Raises
        ------
        AnimationError
            - ``E1471`` if ``add_edge`` references an unknown endpoint or
              the spec dict is missing required keys.
            - ``E1472`` if ``remove_edge`` targets a non-existent edge.
            - ``E1473`` if ``set_weight`` targets a non-existent edge.
        """
        if "add_edge" in params:
            spec = params["add_edge"]
            if not isinstance(spec, dict):
                raise _animation_error(
                    "E1471",
                    detail=f"add_edge requires a dict {{from, to}}, got {type(spec).__name__}",
                )
            u = spec.get("from")
            v = spec.get("to")
            weight = spec.get("weight")
            if u is None or v is None:
                raise _animation_error(
                    "E1471",
                    detail="add_edge requires {from, to}",
                )
            self._add_edge_internal(u, v, weight)
            return
        if "remove_edge" in params:
            spec = params["remove_edge"]
            if not isinstance(spec, dict):
                raise _animation_error(
                    "E1472",
                    detail=f"remove_edge requires a dict {{from, to}}, got {type(spec).__name__}",
                )
            self._remove_edge_internal(spec.get("from"), spec.get("to"))
            return
        if "set_weight" in params:
            spec = params["set_weight"]
            if not isinstance(spec, dict):
                raise _animation_error(
                    "E1473",
                    detail=f"set_weight requires a dict {{from, to, value}}, got {type(spec).__name__}",
                )
            self._set_weight_internal(
                spec.get("from"), spec.get("to"), spec.get("value")
            )
            return

    def _invalidate_addressable_cache(self) -> None:
        """Discard the cached addressable_parts and validate_selector results.

        Called by any mutation that changes graph topology (add_edge,
        remove_edge).  The cache is lazily rebuilt on the next call.
        """
        self.__dict__.pop("_cached_addressable_parts", None)
        self.__dict__.pop("_cached_addressable_set", None)

    def _add_edge_internal(
        self,
        u: str | int,
        v: str | int,
        weight: float | int | None,
    ) -> None:
        if u not in self.nodes:
            raise _animation_error(
                "E1471",
                detail=f"add_edge source node {u!r} is not in graph",
            )
        if v not in self.nodes:
            raise _animation_error(
                "E1471",
                detail=f"add_edge target node {v!r} is not in graph",
            )
        w: float | None = float(weight) if weight is not None else None
        self.edges.append((u, v, w))
        self._invalidate_addressable_cache()  # Opt-4: topology changed
        # A1 position-pinning: the node set never changes for a Graph
        # (no add_node/remove_node), so an edge mutation must NOT move any
        # node — nodes keep their construction-time coordinates and the new
        # edge is simply drawn between them. This keeps multi-step edge
        # mutations visually stable instead of re-solving the whole layout
        # each frame. See docs/plans/graph-position-pinning-analysis-2026-06-03.md.

    def _remove_edge_internal(self, u: str | int, v: str | int) -> None:
        idx = self._find_edge_index(u, v)
        if idx is None:
            raise _animation_error(
                "E1472",
                detail=f"remove_edge: no edge between {u!r} and {v!r}",
            )
        self.edges.pop(idx)
        self._invalidate_addressable_cache()  # Opt-4: topology changed
        # A1 position-pinning: removing an edge leaves every node in place
        # (the node set is unchanged); only the edge line disappears.

    def _set_weight_internal(
        self,
        u: str | int,
        v: str | int,
        value: float | int | None,
    ) -> None:
        if value is None:
            raise _animation_error(
                "E1473",
                detail="set_weight requires a numeric 'value'",
            )
        idx = self._find_edge_index(u, v)
        if idx is None:
            raise _animation_error(
                "E1473",
                detail=f"set_weight: no edge between {u!r} and {v!r}",
            )
        eu, ev, _old = self.edges[idx]
        self.edges[idx] = (eu, ev, float(value))
        # No relayout: weight does not affect geometry.

    def _find_edge_index(
        self,
        u: str | int,
        v: str | int,
    ) -> int | None:
        """Return the index of the edge (u,v); treat undirected as unordered."""
        for i, (eu, ev, _w) in enumerate(self.edges):
            if eu == u and ev == v:
                return i
            if not self.directed and eu == v and ev == u:
                return i
        return None

    # ----- selector helpers ------------------------------------------------

    @staticmethod
    def _node_key(node_id: str | int) -> str:
        return f"node[{node_id}]"

    @staticmethod
    def _edge_key(u: str | int, v: str | int) -> str:
        return f"edge[({u},{v})]"

    def _antiparallel_edges(
        self, hidden_nodes: "set[str | int]"
    ) -> "set[tuple[Any, Any]]":
        """Directed (u,v) whose reverse (v,u) is also drawn this frame.

        C2: forward + residual edges overlap on one straight ``<line>``; a
        directed edge curves iff its reverse partner exists AND both are
        actually drawable (endpoints visible, edge state not ``hidden``) — a
        lone visible edge never bows on its own, and a mid-animation
        ``add_edge`` that births the reverse activates the curve from that
        frame. Undirected graphs return the empty set: antiparallel is
        meaningless without direction, so those edges stay byte-identical.
        """
        if not self.directed:
            return set()
        drawable = {
            (u, v)
            for u, v, _w in self.edges
            if u not in hidden_nodes
            and v not in hidden_nodes
            and self.get_state(self._edge_key(u, v)) != "hidden"
        }
        return {
            (u, v) for (u, v) in drawable if u != v and (v, u) in drawable
        }

    @staticmethod
    def _antiparallel_curve(
        cx1: float, cy1: float, cx2: float, cy2: float, radius: int
    ) -> "tuple[float, float, int, int, int, int, float, float]":
        """Quadratic geometry for one bowed antiparallel edge.

        Returns ``(qx, qy, sx1, sy1, sx2, sy2, apex_x, apex_y)`` where ``q`` is
        the control point offset onto the edge's left-hand normal (the reverse
        edge's normal is the negation, so a pair bows to opposite sides),
        ``s`` are the endpoints pulled back to each node-circle boundary along
        the curve tangent, and ``apex`` is the on-curve midpoint B(0.5) — the
        pill anchor, already shifted onto the bow side.
        """
        dxc = cx2 - cx1
        dyc = cy2 - cy1
        clen = math.hypot(dxc, dyc) or 1.0
        nperp_x = -dyc / clen
        nperp_y = dxc / clen
        ctrl_off = 2.0 * _ANTIPARALLEL_CURVE_OFFSET
        qx = (cx1 + cx2) / 2 + nperp_x * ctrl_off
        qy = (cy1 + cy2) / 2 + nperp_y * ctrl_off
        sx1, sy1 = _shorten_line_to_circle(qx, qy, cx1, cy1, radius)
        sx2, sy2 = _shorten_line_to_circle(qx, qy, cx2, cy2, radius)
        apex_x = 0.25 * sx1 + 0.5 * qx + 0.25 * sx2
        apex_y = 0.25 * sy1 + 0.5 * qy + 0.25 * sy2
        return qx, qy, sx1, sy1, sx2, sy2, apex_x, apex_y

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector suffixes for this Graph instance.

        Opt-4: result is memoized on the instance after the first call.
        Graph topology is fixed at construction — no mutation path exists —
        so the cache is valid for the lifetime of the primitive.
        """
        cached = self.__dict__.get("_cached_addressable_parts")
        if cached is None:
            parts: list[str] = []
            for node_id in self.nodes:
                parts.append(self._node_key(node_id))
            for u, v, _w in self.edges:
                parts.append(self._edge_key(u, v))
            self.__dict__["_cached_addressable_parts"] = parts
            cached = parts
        return cached

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True
        # Opt-4: reuse the cached frozenset built from the cached parts list.
        cached_set = self.__dict__.get("_cached_addressable_set")
        if cached_set is None:
            cached_set = frozenset(self.addressable_parts())
            self.__dict__["_cached_addressable_set"] = cached_set
        return suffix in cached_set

    def renders_value(self, suffix: str) -> bool:
        """``value=`` is edge-scoped on Graph (docs:1125).

        An edge renders its ``value=`` as a dynamic weight label
        (:meth:`emit_svg` reads it back via ``get_value``), so edges honor the
        key. Nodes are name-keyed identities with no value slot — a ``value=``
        there would vanish from the render (flip-back), so reject it. Per-node
        computed-value display (e.g. Dijkstra distances) is a separate future
        feature, not this key.
        """
        return suffix.startswith("edge[")

    def _trace_cell_suffix(self, cell) -> str:
        """Map a ``\\trace`` ``cells=`` entry to a node selector suffix.

        Graph traces address nodes by id (string) or index, not grid cells, so
        the entry becomes ``node[{id}]`` verbatim — ``resolve_annotation_point``
        then handles the str-then-int id lookup."""
        return f"node[{cell}]"

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Map ``"G.node[A]"`` to the SVG ``(x, y)`` center of that node.

        Coordinates include the ``translate(r, r)`` offset applied by
        :meth:`emit_svg` so arrow endpoints line up with rendered nodes.
        """
        m = _GRAPH_NODE_SEL_RE.match(selector)
        if m and m.group("name") == self.name:
            raw_id = m.group("id")
            # Try to match as-is first (string node ids), then as int
            node_id: str | int = raw_id
            if node_id not in self.positions:
                try:
                    node_id = int(raw_id)
                except ValueError:
                    return None
            if node_id in self.positions:
                cx, cy = self.positions[node_id]
                # Coordinates are in the local space of the translated
                # group emitted by emit_svg; no extra offset needed.
                return (float(cx), float(cy))
        return None

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit in a callout lane below the whole graph
        (clear of the lowest node), with a leader line back to the node. The
        baseline is the content height; every node's ``cy + radius`` stays at or
        above it (the force/lane/hierarchical solves keep nodes inside
        ``height``)."""
        return float(self.height)

    def resolve_annotation_box(self, selector: str) -> "BoundingBox | None":
        """Annotated node's circle AABB (Layer C) so a ``position=below`` pill
        gets a leader line and the placer treats the node as a MUST blocker.
        Coords are content-local (pre-frame-translate), matching
        ``resolve_annotation_point``.

        Scoped to selectors that actually carry a below pill: base.py feeds the
        returned width to *every* position pill as ``cell_width`` (which drives
        the R-07/R-08 spanning-leader), and a node's diameter is narrow enough
        that an above/left/right pill would spuriously trip that leader. Gating
        on an actual below pill keeps the box's effect limited to the below lane,
        so existing above/left/right corpus pills stay byte-stable."""
        if not self._target_has_below_pill(selector):
            return None
        pt = self.resolve_annotation_point(selector)
        if pt is None:
            return None
        cx, cy = pt
        r = self._node_radius
        return BoundingBox(
            x=int(cx - r), y=int(cy - r), width=int(2 * r), height=int(2 * r)
        )

    def _annotation_cell_metrics(self) -> "CellMetrics":
        """Phase D/2 CellMetrics proxy — node diameter stands in as the local
        "cell" scale (activates 2D stagger-flip). Single source for render
        AND measurement."""
        _diam = float(self._node_radius * 2)
        return CellMetrics(
            cell_width=_diam,
            cell_height=_diam,
            grid_cols=len(self.nodes) or 1,
            grid_rows=1,
            origin_x=0.0,
            origin_y=0.0,
        )

    def bounding_box(self) -> BoundingBox:
        r = self._node_radius
        arrow_above = self._reserved_arrow_above()
        # Reserve a top band for the caption and shift content below it, so the
        # caption never overlaps the top nodes (mirrors Tree). Defect 6 — the
        # caption width participates in the footprint so a wide caption is folded
        # into the box rather than clipped.
        # Keep the int footprint when no widening is needed so the downstream
        # transform stays byte-stable (only a genuinely wider caption grows it).
        content_w = float(self.width + 2 * r)
        core_w = max(self.width + 2 * r, self._caption_block_width(content_w))
        label_h = self._top_caption_band(content_w)
        # #1: reserve horizontal room for position=left/right pills. Both pads
        # are 0 (int) without left/right pills, so the box stays byte-stable.
        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)
        # #2: position=below pills occupy a callout lane below the content; the
        # lane is 0 px without below pills, so this stays byte-stable too.
        return BoundingBox(
            x=0,
            y=0,
            width=w,
            height=self.height + 2 * r + arrow_above + self._below_lane_height() + label_h,
        )

    def resolve_self_content_rects(self) -> "list[BoundingBox]":
        """Node circles + edge-weight pill boxes as scorer obstacles (FP-2).

        Weight pills are approximated at their GEP-06 natural anchor (the
        visible-segment midpoint) — the collision cascade may slide the
        painted pill, but a SHOULD obstacle only needs the neighbourhood.
        Pure function of primitive state, consulted identically on the emit
        and measure paths; auto_expand scaling is intentionally not replayed
        (the approximation stays on the unscaled frame the anchors use).
        """
        hidden = {
            n for n in self.nodes
            if self.get_state(self._node_key(n)) == "hidden"
        }
        pos = {
            k: (float(v[0]), float(v[1])) for k, v in self.positions.items()
        }
        r = float(self._node_radius)
        antiparallel = self._antiparallel_edges(hidden)
        rects: list[BoundingBox] = []
        for n in self.nodes:
            if n in hidden or n not in pos:
                continue
            x, y = pos[n]
            rects.append(
                BoundingBox(x=x - r, y=y - r, width=2 * r, height=2 * r)
            )
        for u, v, w in self.edges:
            if u in hidden or v in hidden or u not in pos or v not in pos:
                continue
            if self.get_state(self._edge_key(u, v)) == "hidden":
                continue
            dyn = self.get_value(self._edge_key(u, v))
            if dyn is not None:
                display = str(dyn)
            elif self.show_weights and w is not None:
                display = _format_weight(w)
            else:
                continue
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            if self.directed:
                x2, y2 = _shorten_line_to_circle(x1, y1, x2, y2, r)
            vx1, vy1 = _shorten_line_to_circle(x2, y2, x1, y1, r)
            mid_x = (vx1 + x2) / 2
            mid_y = (vy1 + y2) / 2
            if (u, v) in antiparallel:
                # Mirror emit_svg: the pill obstacle rides the bowed apex, not
                # the straight midpoint (FP-2 measure/emit parity).
                *_c, mid_x, mid_y = self._antiparallel_curve(
                    pos[u][0], pos[u][1], pos[v][0], pos[v][1],
                    self._node_radius,
                )
            tw = measure_value_text(display, _WEIGHT_FONT, mono=True)
            pw = float(tw + _WEIGHT_PILL_PAD_X * 2)
            ph = float(line_box_h(_WEIGHT_FONT) + _WEIGHT_PILL_PAD_Y * 2)
            rects.append(
                BoundingBox(
                    x=mid_x - pw / 2, y=mid_y - ph / 2, width=pw, height=ph
                )
            )
        return rects

    def set_groups(self, groups: "list[dict]") -> None:
        """Attach this frame's ``\\group`` overlay hulls (case §6 Phase 1)."""
        self._groups = list(groups)

    @staticmethod
    def _group_hull_path(
        centers: "list[tuple[float, float]]",
        inflate: float,
        corner_r: float,
    ) -> "tuple[str, tuple[float, float, float, float]]":
        """Closed rounded path enclosing *centers* with ~*inflate* clearance.

        >=3 centres with a non-degenerate hull → convex hull
        (``plane2d_compute.hull``) expanded radially from its centroid by
        *inflate*, corners rounded. <=2 centres (or a collinear/degenerate
        hull) → an inflated rounded rectangle around the centres' bbox. Returns
        ``(path_d, (minx, miny, maxx, maxy))`` — the path's extent, used for
        label placement and the painted⊆bbox honesty test. Every input centre
        lies inside the returned bbox by construction (the hull is only ever
        pushed outward)."""
        verts = _convex_hull(centers)
        if len(verts) >= 3:
            cx = sum(p[0] for p in verts) / len(verts)
            cy = sum(p[1] for p in verts) / len(verts)
            expanded: "list[tuple[float, float]]" = []
            for x, y in verts:
                dx, dy = x - cx, y - cy
                d = math.hypot(dx, dy) or 1.0
                expanded.append((x + dx / d * inflate, y + dy / d * inflate))
            xs = [p[0] for p in expanded]
            ys = [p[1] for p in expanded]
            return (
                _rounded_polygon_path(expanded, corner_r),
                (min(xs), min(ys), max(xs), max(ys)),
            )
        xs = [p[0] for p in centers]
        ys = [p[1] for p in centers]
        minx, maxx = min(xs) - inflate, max(xs) + inflate
        miny, maxy = min(ys) - inflate, max(ys) + inflate
        return (
            _rounded_rect_path(minx, miny, maxx - minx, maxy - miny, corner_r),
            (minx, miny, maxx, maxy),
        )

    def _emit_group_hulls(
        self,
        parts: "list[str]",
        working_positions: "dict[Any, tuple[float, float]]",
    ) -> None:
        """Paint each ``\\group`` hull UNDER the edges/nodes (call before the
        edge layer). The hull wraps the cluster's node CENTRES with
        ``_GROUP_PAD`` clearance; the Graph node-set is never touched, so the
        viewBox is unchanged and this stays a pure decoration keyed
        ``{shape}.group[{id}]-solo``. Appear/disappear/recolour ride the shipped
        ``annotation_add / annotation_remove / annotation_recolor`` handlers —
        zero new motion kinds, no JS. A node not present in this frame's
        positions (hidden/unknown) is skipped; an empty cluster soft-drops the
        whole hull (mirrors trace selector semantics)."""
        self._pending_group_labels: list[str] = []
        groups = getattr(self, "_groups", None)
        if not groups:
            return
        pos_by_str = {
            str(k): (float(v[0]), float(v[1]))
            for k, v in working_positions.items()
        }
        inflate = float(self._node_radius) + _GROUP_PAD
        for g in groups:
            centers = [
                pos_by_str[str(n)]
                for n in g.get("nodes", [])
                if str(n) in pos_by_str
            ]
            if not centers:
                continue
            color = g.get("color", "info")
            style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
            stroke = style["stroke"]
            gid = g.get("id", "g")
            key = f"{self.name}.group[{gid}]-solo"
            d_str, (minx, miny, _maxx, _maxy) = self._group_hull_path(
                centers, inflate, _GROUP_CORNER_R
            )
            cls = annotation_color_class(color)
            label = g.get("label")
            inner = (
                f'<path d="{d_str}" fill="{stroke}"'
                f' fill-opacity="{_GROUP_FILL_OPACITY}" stroke="{stroke}"'
                f' stroke-width="1.5" stroke-opacity="{_GROUP_STROKE_OPACITY}"'
                f' stroke-dasharray="{_GROUP_STROKE_DASH}"'
                f' stroke-linejoin="round"/>'
            )
            parts.append(
                f'  <g class="scriba-annotation scriba-annotation-{cls}'
                f' scriba-group" data-annotation="{_escape_xml(key)}"'
                f' role="graphics-symbol" aria-roledescription="group"'
                f' aria-label='
                f'"{_escape_xml(strip_math_markup(str(label or gid)))}">'
                f"{inner}</g>"
            )
            if label:
                # The hull FILL stays under the nodes (tints the cluster), but
                # the label pill must paint OVER nodes or a node standing at the
                # hull corner overdraws it into ":1" (hunt-visual BUG 1). Stash
                # it for the top layer, emitted after the node group.
                pw = measure_label_line(str(label), LABEL_FONT_PX) + 12
                ph = LABEL_FONT_PX + 8
                prx = minx
                pry = miny - ph - 4
                if pry < 0:
                    pry = miny + 4
                tx = prx + pw / 2.0
                self._pending_group_labels.append(
                    f'<g class="scriba-group-label" data-annotation='
                    f'"{_escape_xml(key)}-label">'
                    f'<rect x="{prx:.1f}" y="{pry:.1f}" width="{pw}"'
                    f' height="{ph}" rx="4" fill="white" fill-opacity="0.92"'
                    f' stroke="{stroke}" stroke-width="0.5"'
                    f' stroke-opacity="0.4"/>'
                    f'<text x="{tx:.1f}" y="{pry + ph / 2.0:.1f}"'
                    f' fill="{style["label_fill"]}"'
                    f' style="text-anchor:middle;dominant-baseline:central">'
                    f"{_escape_xml(strip_math_markup(str(label)))}</text></g>"
                )

    @allow_forbidden_pattern(
        "FP-2",
        reason=(
            "placed_edge_labels is the content layer's internal weight-vs-"
            "weight avoidance; content→annotation sharing goes through "
            "resolve_self_content_rects (the measure-parity channel), which "
            "is what FP-2 actually demands"
        ),
        issue="investigations/fp2-isolated-registries.md",
    )
    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        if not self.nodes:
            return (
                f'<g data-primitive="graph" data-shape="{_escape_xml(self.name)}">'
                '</g>'
            )

        r = self._node_radius
        effective_anns = self._annotations
        arrow_above = self._reserved_arrow_above()
        # #1: shift content right by left_pad so position=left pills clear the
        # viewBox. left_pad is 0 (int) without left pills, so the transform is
        # byte-identical to the pre-#1 "translate({r},{ty})".
        left_pad, _right = self._h_label_pad()

        parts: list[str] = []
        # Offset by node radius so nodes at edge positions don't clip.
        # When annotations with arrows exist, shift content down by
        # arrow_above so curves have room above the graph.
        ty = r + arrow_above
        parts.append(
            f'<g data-primitive="graph" data-shape="{_escape_xml(self.name)}"'
            f' transform="translate({r + left_pad},{ty})">'
        )

        # Optional label / caption (in the reserved top band)
        label_offset = 0
        if self.label is not None:
            content_w = float(self.width + 2 * r)
            label_offset = self._top_caption_band(content_w)
            self._emit_top_caption(
                parts,
                content_width=content_w,
                footprint_width=int(self.bounding_box().width),
                frame_radius=r,
                render_inline_tex=render_inline_tex,
            )
        # Shift all edges/nodes/annotations below the caption band (mirrors
        # Tree) so the caption no longer overlaps the top nodes.
        if label_offset:
            parts.append(f'<g transform="translate(0,{label_offset})">')

        # NOTE: arrowhead marker <defs> are emitted once per SVG at the stage
        # root by `emit_shared_defs` (driven by `_has_directed_graph`).  The
        # primitive must NOT emit its own copy — doing so produced a duplicate
        # `id="scriba-arrow-fwd"` (invalid SVG).  Edges reference the shared
        # marker via `marker-end="url(#scriba-arrow-fwd)"`.

        # --- Edge layer (rendered first, below nodes) ---
        # Pre-compute the set of hidden node keys so edges incident on a
        # hidden node are also skipped (avoids orphan edges dangling into
        # empty space, matches Tree.emit_svg behavior — RFC-001 §4.4).
        hidden_nodes: set[str | int] = {
            n for n in self.nodes
            if self.get_state(self._node_key(n)) == "hidden"
        }
        placed_edge_labels: list[_LabelPlacement] = []

        # Phase 5 / GEP v2.0 (U-15): auto-expand working positions so that
        # no edge-weight pill falls back to leader/origin stage.
        # self.positions is NEVER mutated — working_positions is a local copy.
        # Opt-in via auto_expand=True; default False preserves legacy behaviour.
        has_display_weight = any(
            (
                self.get_value(self._edge_key(u_, v_)) is not None
                or (self.show_weights and w_ is not None)
            )
            for u_, v_, w_ in self.edges
        )
        working_positions: dict[Any, tuple[float, float]]
        if self.auto_expand and has_display_weight:
            from scriba.animation.primitives._layout_expand import _find_min_scale  # noqa: PLC0415
            s = _find_min_scale(
                {k: (float(v[0]), float(v[1])) for k, v in self.positions.items()},
                self.edges,
                float(self._node_radius),
                self.directed,
                float(self.width),
                float(self.height),
            )
            if s > 1.0:
                working_positions = {
                    k: (float(v[0]) * s, float(v[1]) * s)
                    for k, v in self.positions.items()
                }
            else:
                working_positions = {
                    k: (float(v[0]), float(v[1])) for k, v in self.positions.items()
                }
        else:
            working_positions = {
                k: (float(v[0]), float(v[1])) for k, v in self.positions.items()
            }

        # GEP-03: visible node circles act as MUST-avoid AABB obstacles for
        # edge weight pills. Built from working_positions so auto-expand
        # scaling propagates into the collision set.
        node_aabbs: list[_LabelPlacement] = [
            _LabelPlacement(
                x=float(working_positions[n][0]),
                y=float(working_positions[n][1]),
                width=float(2 * self._node_radius),
                height=float(2 * self._node_radius),
            )
            for n in self.nodes
            if n not in hidden_nodes
        ]
        # GEP-17: centroid of visible node positions — used as the repulsion
        # origin for leader-line placement when all cascade stages are blocked.
        _visible_nodes = [n for n in self.nodes if n not in hidden_nodes]
        if _visible_nodes:
            graph_centroid: tuple[float, float] | None = (
                sum(float(working_positions[n][0]) for n in _visible_nodes) / len(_visible_nodes),
                sum(float(working_positions[n][1]) for n in _visible_nodes) / len(_visible_nodes),
            )
        else:
            graph_centroid = None

        # Frame-stable placement order: sort by canonical edge key only.
        # Prior versions (≤v0.15) prepended an _EDGE_STATE_PRIO bucket so
        # current/highlighted edges claimed the best slots — but the prio
        # map omitted good/done/dim/bad, which collapsed to 99 and sorted
        # inconsistently as edges crossed state-group boundaries (e.g. a
        # current→good transition would flip edge ordering, moving pills
        # to different slots in the very next frame). The resulting
        # "pill swap" across frames was disorienting and outweighed the
        # pedagogical win of priority slotting. D-1 determinism is still
        # satisfied because _edge_key is a canonical ASCII string key.
        def _edge_sort_key(
            edge: tuple[Any, Any, Any],
        ) -> str:
            u_, v_, _w = edge
            return self._edge_key(u_, v_)
        # \group overlay hulls sit UNDER edges/nodes (above the background) so
        # they tint the cluster interior without occluding node labels. Uses the
        # same working_positions space as edges/nodes; never widens the viewBox.
        self._emit_group_hulls(parts, working_positions)
        # C2: directed (u,v) whose reverse (v,u) is also drawn bows onto a
        # quadratic <path>; every other edge keeps its byte-identical <line>.
        antiparallel = self._antiparallel_edges(hidden_nodes)
        parts.append('<g class="scriba-graph-edges">')
        for u, v, weight in sorted(self.edges, key=_edge_sort_key):
            edge_target = f"{self.name}.{self._edge_key(u, v)}"
            state = self.get_state(self._edge_key(u, v))
            # RFC-001 §4.4 — hidden edges are not rendered at all. Also
            # skip edges whose endpoints are hidden (would otherwise
            # render as a line going into empty space).
            if state == "hidden" or u in hidden_nodes or v in hidden_nodes:
                continue
            x1, y1 = working_positions[u]
            x2, y2 = working_positions[v]

            if self.directed:
                # Shorten line so arrowhead stops at circle boundary
                x2, y2 = _shorten_line_to_circle(x1, y1, x2, y2, self._node_radius)

            # GEP-01: pill sits on the *visible* segment. Both endpoints
            # are shortened to the node-circle boundary for the midpoint
            # calculation — the stroke is drawn from node centers, but
            # the source-side half is occluded by the source circle, so
            # the raw-center midpoint is biased toward the source by
            # `node_radius / 2`. Mirroring the target-side shortening
            # gives the true visual midpoint and prevents wide pills
            # from overlapping the source node AABB on short vertical
            # edges (e.g. hierarchical 5-layer DAGs with layer_gap≈100).
            vx1, vy1 = _shorten_line_to_circle(x2, y2, x1, y1, self._node_radius)
            mid_x = (vx1 + x2) / 2
            mid_y = (vy1 + y2) / 2

            # C2 antiparallel: bow this edge onto its own side. The forward and
            # residual edges of a pair take opposite left-hand normals, so they
            # separate into two arcs. curve_ctrl feeds the <path> emit below;
            # x1/y1/x2/y2 become the on-curve endpoints (so the pill's edge
            # direction = the curve's midpoint tangent) and mid_x/mid_y ride the
            # apex, dragging the weight pill off the shared centre line.
            curve_ctrl: "tuple[float, float] | None" = None
            if (u, v) in antiparallel:
                cx1, cy1 = working_positions[u]
                cx2, cy2 = working_positions[v]
                qx, qy, x1, y1, x2, y2, mid_x, mid_y = self._antiparallel_curve(
                    float(cx1), float(cy1), float(cx2), float(cy2),
                    self._node_radius,
                )
                curve_ctrl = (qx, qy)

            marker = ' marker-end="url(#scriba-arrow-fwd)"' if self.directed else ""
            edge_colors = svg_style_attrs(state)
            edge_stroke = edge_colors["stroke"]
            edge_sw = "1.5" if state == "idle" else "2"
            edge_label = (
                f"Edge from node {_escape_xml(str(u))} "
                f"to node {_escape_xml(str(v))}"
            )
            weight_text = ""
            # Dynamic value from \apply overrides the static weight.
            edge_suffix = self._edge_key(u, v)
            dynamic_val = self.get_value(edge_suffix)
            display_weight: str | None = None
            if dynamic_val is not None:
                display_weight = str(dynamic_val)
            elif self.show_weights and weight is not None:
                display_weight = _format_weight(weight)
            if display_weight is not None:
                # GEP-02: pill dimensions from module-level constants so the
                # constants survive ruff/style churn and share one source.
                tw = measure_value_text(display_weight, _WEIGHT_FONT, mono=True)
                th = line_box_h(_WEIGHT_FONT)
                pill_w = tw + _WEIGHT_PILL_PAD_X * 2
                pill_h = th + _WEIGHT_PILL_PAD_Y * 2

                # Edge direction + unit perpendicular (left-hand of flow).
                dx_edge = x2 - x1
                dy_edge = y2 - y1
                edge_len = math.hypot(dx_edge, dy_edge) or 1.0
                perp_x = -dy_edge / edge_len
                perp_y = dx_edge / edge_len

                # GEP-10: rotate pill + text along the visible stroke so
                # users can map a pill to its edge instantly on dense /
                # diagonal graphs. Normalize θ into [-π/2, π/2] so text
                # never renders upside-down (GEP-10 upright rule).
                # GEP-11: fall back to horizontal pill on degenerate edges
                # (coincident nodes) — perp vector is zero there.
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
                theta_deg = math.degrees(theta_rad)

                # GEP-06: initial placement = midpoint + perp-bias so the pill
                # sits perpendicular to the stroke, not an unconditional -4
                # y-offset. Correct for any edge angle including vertical.
                lx = mid_x + perp_x * _WEIGHT_PILL_PERP_BIAS
                ly = mid_y + perp_y * _WEIGHT_PILL_PERP_BIAS

                # GEP-09 / GEP-12: collision AABB = axis-aligned bounding
                # box of the rotated pill rect plus stroke-width pad. Over-
                # estimates the true OBB footprint by up to √2 on diagonals;
                # acceptable at E ≤ 50 (Phase 1 may upgrade to SAT OBB test).
                abs_cos = abs(math.cos(theta_rad))
                abs_sin = abs(math.sin(theta_rad))
                aabb_w = pill_w * abs_cos + pill_h * abs_sin + _WEIGHT_PILL_STROKE_PAD
                aabb_h = pill_w * abs_sin + pill_h * abs_cos + _WEIGHT_PILL_STROKE_PAD
                candidate = _LabelPlacement(
                    x=lx, y=ly, width=aabb_w, height=aabb_h
                )

                # GEP-07 v1.2 / GEP-17 v1.4: along-edge shift first (preserves
                # GEP-10 binding), perp nudge as fallback, leader line as last
                # resort when graph_centroid is available.
                # See _nudge_pill_placement for the full stage protocol.
                ux = dx_edge / edge_len
                uy = dy_edge / edge_len
                max_shift_along = max(
                    0.0,
                    edge_len / 2 - pill_w / 2 - self._node_radius,
                )
                pp = _nudge_pill_placement(
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
                    placed_pills=placed_edge_labels,
                    graph_centroid=graph_centroid,
                )
                lx, ly = pp.x, pp.y
                candidate = _LabelPlacement(
                    x=lx, y=ly, width=aabb_w, height=aabb_h
                )

                # GEP-08: clamp pill centre into the viewbox so a pill near
                # the canvas boundary never spills outside.
                lx = max(
                    pill_w / 2,
                    min(float(self.width) - pill_w / 2, lx),
                )
                ly = max(
                    pill_h / 2,
                    min(float(self.height) - pill_h / 2, ly),
                )
                candidate = _LabelPlacement(
                    x=lx, y=ly, width=aabb_w, height=aabb_h
                )
                placed_edge_labels.append(candidate)

                # GEP-17: leader line emitted BEFORE the pill (so pill renders
                # on top).  Anchor point is the edge midpoint (pp.anchor_x/y).
                leader_svg = ""
                if pp.leader:
                    leader_svg = _emit_leader_line(
                        pp.anchor_x, pp.anchor_y, lx, ly, edge_stroke
                    )

                # GEP-10: pill rect + text wrapped in a <g transform="rotate">
                # so the pill rotates as a unit around its own centre. Text
                # remains centred in the pill's local frame regardless of
                # edge angle. GEP-13: rotate the outer <g>, NEVER the inner
                # <foreignObject> (KaTeX path) — Safari has a known sub-pixel
                # rendering bug for transforms on <foreignObject>.
                pill_rx = lx - pill_w / 2
                pill_ry = ly - pill_h / 2

                # Phase 6 (U-03) — tint_by_source: derive pill fill from the
                # source node's state colour instead of the default white.
                # Phase 7 (smart-label v2.0) — tint_by_edge takes priority:
                # derive pill fill from the edge's own state palette.
                # Uses a desaturated / alpha-blended tint so the pill stays
                # legible over edge strokes.
                if self.tint_by_edge:
                    pill_fill = _pill_tint_for_edge_state(state)
                elif self.tint_by_source:
                    src_state = self.get_state(self._node_key(u))
                    pill_fill = _pill_tint_for_state(src_state)
                else:
                    pill_fill = "white"

                # Phase 6 (U-03) — split_labels: when enabled AND the label
                # contains a "/" separator with non-empty both sides, split
                # into bold primary + dim secondary tspans; otherwise fall
                # through to the single _render_svg_text path. Degenerate
                # inputs ("/", "5/", "/3") skip the split to avoid emitting
                # an empty <tspan>. Multi-slash labels ("5/3/7") split on
                # the first "/" only, leaving the rest dim as the secondary.
                _split_head, _split_sep, _split_tail = (
                    display_weight.partition("/") if self.split_labels else ("", "", "")
                )
                if (
                    self.split_labels
                    and _split_sep == "/"
                    and _split_head
                    and _split_tail
                    # A math weight yields to the single-value KaTeX path:
                    # the split styling emits escaped tspans, which would
                    # show the raw $...$ (inconsistent with every other
                    # edge-weight render).
                    and not _label_has_math(display_weight)
                ):
                    _text_svg = _render_split_label_svg(
                        _split_head, _split_sep, _split_tail, lx, ly,
                        fill=THEME["fg_muted"],
                        text_anchor="middle",
                        dominant_baseline="central",
                        css_class="scriba-graph-weight",
                    )
                else:
                    # size the KaTeX FO to the weight pill instead of the
                    # 80x30 default box (which silently clipped tall/wide
                    # math weights — folabel-sweep-fo-surface GAP)
                    _text_svg = _render_svg_text(
                        display_weight, lx, ly,
                        fill=THEME["fg_muted"],
                        text_anchor="middle",
                        dominant_baseline="central",
                        css_class="scriba-graph-weight",
                        fo_width=max(int(pill_w), 8),
                        fo_height=max(int(pill_h), 8),
                        render_inline_tex=render_inline_tex,
                        clip_overflow=False,
                    )
                # class="scriba-graph-pill" scopes state CSS away from the
                # pill rect (see scriba-scene-primitives.css :not() exclusion
                # on .scriba-state-X > rect rules). Without this, horizontal
                # edges (pill rect = direct child of state-classed edge <g>)
                # get CSS fill override while rotated edges (pill rect wrapped
                # in <g transform="rotate">) escape it — producing visible
                # inter-edge color drift even when all edges share one state.
                _pill_svg = (
                    f'<rect class="scriba-graph-pill" '
                    f'x="{pill_rx:.1f}" y="{pill_ry:.1f}" '
                    f'width="{pill_w}" height="{pill_h}" '
                    f'rx="{_WEIGHT_PILL_R}" fill="{pill_fill}" fill-opacity="0.85" '
                    f'stroke="{edge_stroke}" stroke-width="0.5"/>'
                ) + _text_svg
                if abs(theta_deg) < 0.05:
                    weight_text = leader_svg + _pill_svg
                else:
                    weight_text = (
                        leader_svg
                        + f'<g transform="rotate({theta_deg:.2f} '
                        f'{lx:.1f} {ly:.1f})">'
                        f'{_pill_svg}'
                        f'</g>'
                    )
            if curve_ctrl is None:
                edge_geom = (
                    f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                    f'stroke="{edge_stroke}" stroke-width="{edge_sw}"'
                    f'{marker}>'
                    f'<title>{edge_label}</title>'
                    f'</line>'
                )
            else:
                qx, qy = curve_ctrl
                edge_geom = (
                    f'<path d="M {x1} {y1} Q {qx:.1f} {qy:.1f} {x2} {y2}" '
                    f'fill="none" '
                    f'stroke="{edge_stroke}" stroke-width="{edge_sw}"'
                    f'{marker}>'
                    f'<title>{edge_label}</title>'
                    f'</path>'
                )
            parts.append(
                f'<g data-target="{_escape_xml(edge_target)}" '
                f'class="{state_class(state)}" '
                f'role="graphics-symbol" aria-label="{edge_label}">'
                f'{edge_geom}'
                f'{weight_text}'
                f'</g>'
            )
        parts.append('</g>')

        # DECORATE v4: \trace polylines thread node centres, painted between the
        # edges and the nodes ("follow the edges", nodes sitting on top). Same
        # coordinate frame as the annotation arrows below, which already resolve
        # through resolve_annotation_point.
        self.emit_traces_under(parts)

        # --- Node layer (rendered on top) ---
        parts.append('<g class="scriba-graph-nodes">')
        for node_id in self.nodes:
            node_target = f"{self.name}.{self._node_key(node_id)}"
            state = self.get_state(self._node_key(node_id))
            # RFC-001 §4.4 — hidden nodes are not rendered at all.
            if state == "hidden":
                continue
            cx, cy = working_positions[node_id]
            hl_suffixes = getattr(self, "_highlighted", set())
            is_hl = self._node_key(node_id) in hl_suffixes
            # β: highlight is a state, not a dashed overlay. Promote only
            # when the node is otherwise idle; keep current/error/good alive.
            effective_state = "highlight" if (is_hl and state == "idle") else state
            node_colors = svg_style_attrs(effective_state)
            node_text = _render_svg_text(
                str(node_id),
                cx,
                cy,
                fill=node_colors["text"],
                text_anchor="middle",
                dominant_baseline="central",
                font_size="14",
                fo_width=self._node_radius * 2,
                fo_height=self._node_radius * 2,
                render_inline_tex=render_inline_tex,
                clip_overflow=False,
                # Wave 9: no inline text_outline — CSS halo cascade owns it.
            )
            parts.append(
                f'<g data-target="{_escape_xml(node_target)}" '
                f'class="{state_class(effective_state)}">'
                f'<circle cx="{cx}" cy="{cy}" r="{self._node_radius}"/>'
                f'{node_text}'
                f'</g>'
            )
        parts.append('</g>')

        # \group labels paint OVER the nodes (the hull fill stayed under) so a
        # node at the hull corner can't overdraw the pill (hunt-visual BUG 1).
        pending_labels = getattr(self, "_pending_group_labels", None)
        if pending_labels:
            parts.append('<g class="scriba-group-labels">')
            parts.extend(pending_labels)
            parts.append('</g>')

        # --- Annotation arrows (rendered on top of everything) ---
        if effective_anns:
            arrow_lines: list[str] = []
            self.emit_annotation_arrows(
                arrow_lines,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
                cell_metrics=self._annotation_cell_metrics(),
            )
            parts.extend(arrow_lines)

        if label_offset:
            parts.append('</g>')  # close the caption-band content shift
        parts.append('</g>')
        return ''.join(parts)

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []
