"""Shared arrow annotation SVG rendering infrastructure for animation primitives.

Extracted from base.py (Wave C1 split). Re-exported from base.py for
backward compatibility — all existing imports from base.py continue to work.

placed_labels contract
----------------------
Callers MUST initialize one ``placed_labels: list[_LabelPlacement] = []``
before all annotation loops for a given frame and pass the **same list** to
every call of both ``emit_plain_arrow_svg`` and ``emit_arrow_svg`` within
that frame.  Sharing the list is what lets the collision-avoidance nudge
account for labels placed by both helper functions.  Using a fresh list per
call defeats overlap detection across annotation types.
"""

from __future__ import annotations

import enum
import logging
import math
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterator, Literal, NamedTuple

from scriba.animation.primitives._text_render import _escape_xml, estimate_text_width
from scriba.animation.primitives._types import CELL_HEIGHT

# Match inline math delimited by single `$`. Non-greedy; rejects empty bodies.
_MATH_DELIM_RE = re.compile(r"\$[^$]+?\$")

# Gate debug annotation comments behind an env var so they never leak into
# production HTML.  Set SCRIBA_DEBUG_LABELS=1 to enable.
_DEBUG_LABELS: bool = os.getenv("SCRIBA_DEBUG_LABELS") == "1"

if TYPE_CHECKING:  # pragma: no cover - type checking only
    pass


__all__ = [
    # Label placement
    "_LABEL_MAX_WIDTH_CHARS",
    "_LABEL_PILL_PAD_X",
    "_LABEL_PILL_PAD_Y",
    "_LABEL_PILL_RADIUS",
    "_LABEL_BG_OPACITY",
    "_LABEL_HEADROOM",
    "_PLAIN_ARROW_STEM",
    "_LEADER_DISPLACEMENT_THRESHOLD",
    "_LabelPlacement",
    "_nudge_candidates",
    "_wrap_label_lines",
    "_place_pill",
    # Arrow styles and rendering
    "ARROW_STYLES",
    "emit_plain_arrow_svg",
    "emit_arrow_svg",
    "emit_position_label_svg",
    "arrow_height_above",
    "position_label_height_above",
    "position_label_height_below",
    "emit_arrow_marker_defs",
    # Cross-primitive segment helpers (W3-α+)
    "_translate_segment",
    # R-31 ext: prior-annotation arrow-stroke obstacle sampling
    "_sample_arrow_segments",
    "_BEZIER_SAMPLE_N",
    # Phase C (v0.13.0): grid-aware flow direction
    "CellMetrics",
    "FlowDirection",
    "classify_flow",
]


# ---------------------------------------------------------------------------
# Smart label placement constants & helpers
# ---------------------------------------------------------------------------

_LABEL_MAX_WIDTH_CHARS = 24
_LABEL_PILL_PAD_X = 6
_LABEL_PILL_PAD_Y = 3
_LABEL_PILL_RADIUS = 4
_LABEL_BG_OPACITY = 0.92
_LABEL_HEADROOM = 24
# Length of the straight stem for plain arrow=true annotations (no source arc).
_PLAIN_ARROW_STEM = 18
# R-07: Leader-line displacement threshold — scale-relative minimum.
# A leader is emitted when the label is nudged more than this many pixels from
# its natural anchor.  The threshold is computed per-call as max(pill_h, 20) so
# it scales with pill height rather than being a fixed constant.  The constant
# below is kept for backward compatibility with any callers that reference it
# directly; the per-call formula supersedes it in emit_arrow_svg.
# Unused in v0.15.0+; kept for import-stability.
_LEADER_DISPLACEMENT_THRESHOLD: float = 20.0

# R-01: Default label font size in pixels.  Referenced by both the full render
# path (l_font_px fallback) and the early pill-height estimator (_est_pill_h).
_DEFAULT_LABEL_FONT_PX: int = 11

_log = logging.getLogger(__name__)


@dataclass(slots=True)
class _LabelPlacement:
    """Tracks the bounding box of a placed annotation label for collision avoidance."""

    x: float
    y: float
    width: float
    height: float

    def overlaps(self, other: "_LabelPlacement") -> bool:
        """Return True if this placement overlaps *other*."""
        return not (
            self.x + self.width / 2 < other.x - other.width / 2
            or self.x - self.width / 2 > other.x + other.width / 2
            or self.y + self.height / 2 < other.y - other.height / 2
            or self.y - self.height / 2 > other.y + other.height / 2
        )


# ---------------------------------------------------------------------------
# v0.12.0 W1 — Unified obstacle type for scoring
# ---------------------------------------------------------------------------
# Internal type used by the scoring engine.  Not part of the public API.
# The public-facing W0-[A] Protocol types (ObstacleAABB, ObstacleSegment) in
# _obstacle_types.py remain unchanged — _Obstacle is the internal unified
# representation consumed by _score_candidate / _pick_best_candidate.

ObstacleKind = Literal[
    "pill", "target_cell", "axis_label", "source_cell", "grid",
    "segment", "edge_polyline",
]
Severity = Literal["MUST", "SHOULD"]


@dataclass(frozen=True)
class _Obstacle:
    """Unified internal obstacle geometry for smart-label scoring (W1).

    Covers both AABB obstacles (pill, target_cell, …) and segment obstacles
    (segment, edge_polyline) in a single type so the scoring function has one
    uniform interface.

    For AABB kinds:
        ``x``, ``y`` are the AABB centre; ``width``, ``height`` are full dims.
        ``x2``, ``y2`` are unused (default 0.0).

    For segment kinds:
        ``x``, ``y`` are the segment start point.
        ``x2``, ``y2`` are the segment end point.
        ``width``, ``height`` are unused (default 0.0).
    """

    kind: ObstacleKind
    x: float
    y: float
    width: float
    height: float
    x2: float = 0.0
    y2: float = 0.0
    severity: Severity = "SHOULD"


def _lp_to_obstacle(lp: _LabelPlacement) -> _Obstacle:
    """Convert a placed pill label to an internal _Obstacle (SHOULD severity).

    Used as the entry shim in _place_pill / emit_plain_arrow_svg /
    emit_arrow_svg so that existing placed-label registries can be converted
    into the obstacle tuple expected by _score_candidate.

    The kind is always ``"pill"`` (kind_weight 1.0) and severity is ``"SHOULD"``
    (pills do not trigger hard-block semantics — a new label overlapping an
    existing pill is penalised, not forbidden).
    """
    return _Obstacle(
        kind="pill",
        x=lp.x,
        y=lp.y,
        width=lp.width,
        height=lp.height,
    )


def _segment_to_obstacle(seg: "Any") -> _Obstacle:
    """Convert an ObstacleSegment (R-31) to an internal _Obstacle.

    Accepts any object with ``kind``, ``x0``, ``y0``, ``x1``, ``y1``,
    ``severity`` attributes — matching the ``ObstacleSegment`` frozen
    dataclass from ``_obstacle_types.py``.

    The ``_Obstacle`` kind is ``"segment"`` (handled by P7 edge-occlusion
    term in ``_score_candidate``).  Width and height are left at their
    zero defaults (unused for segment kind).
    """
    return _Obstacle(
        kind="segment",
        x=seg.x0,
        y=seg.y0,
        width=0.0,
        height=0.0,
        x2=seg.x1,
        y2=seg.y1,
        severity=seg.severity,
    )


def _translate_segment(seg: "Any", dx: float, dy: float) -> "Any":
    """Return a copy of *seg* (ObstacleSegment) with endpoints shifted by (dx, dy).

    Used by cross-primitive obstacle threading (W3-α+) to re-express a
    segment from one primitive's local SVG frame into another's local frame.

    Parameters
    ----------
    seg:
        An ``ObstacleSegment`` (or any object with ``kind``, ``x0``, ``y0``,
        ``x1``, ``y1``, ``state``, ``severity`` attributes).
    dx, dy:
        Translation deltas: ``(other_x_off - self_x_off, other_y_off - self_y_off)``.

    Returns
    -------
    ObstacleSegment
        A new frozen instance with translated endpoints and identical metadata.
    """
    # Import here to avoid a module-level circular reference.
    from scriba.animation.primitives._obstacle_types import ObstacleSegment

    return ObstacleSegment(
        kind=seg.kind,
        x0=seg.x0 + dx,
        y0=seg.y0 + dy,
        x1=seg.x1 + dx,
        y1=seg.y1 + dy,
        state=seg.state,
        severity=seg.severity,
    )


# ---------------------------------------------------------------------------
# v0.12.0 W1 — Scoring weights, constants, and functions
# ---------------------------------------------------------------------------
# Weights are frozen at import time.  Use SCRIBA_LABEL_WEIGHTS env var for
# debugging only; golden generation scripts must unset it.
# See docs/plans/smart-label-scoring-impl-2026-04-22.md §2.2 and §4.4.

def _parse_weight_override(name: str, default: float) -> float:
    """Parse a single weight from SCRIBA_LABEL_WEIGHTS at import time.

    Format: ``SCRIBA_LABEL_WEIGHTS="overlap=20,displace=0.5"``

    Returns *default* when the env var is absent or the key is not found.
    Malformed values (non-numeric) are silently ignored and the default is
    returned so that a misconfigured env var does not crash the process.
    """
    raw = os.environ.get("SCRIBA_LABEL_WEIGHTS", "")
    if not raw:
        return default
    for token in raw.split(","):
        token = token.strip()
        if "=" not in token:
            continue
        key, _, val = token.partition("=")
        if key.strip() == name:
            try:
                return float(val.strip())
            except ValueError:
                return default
    return default


# Kind-weight table (R-02, R-03, R-04).  Drives P1 (overlap area) term.
# "segment" and "edge_polyline" are handled by P7 (edge occlusion) instead.
# "annotation_arrow" (R-31 ext): prior-annotation arc segments are also handled
# by P7 (edge occlusion) at weight 40.0 — SHOULD severity only, no hard-block.
_KIND_WEIGHT: dict[str, float] = {
    "pill":        1.0,
    "target_cell": 3.0,   # R-02: highest priority blocker
    "axis_label":  2.0,   # R-03
    "source_cell": 0.5,   # R-04: SHOULD-level
    "grid":        0.2,
    # annotation_arrow is a segment kind handled by P7, not P1; entry is kept
    # here as documentation that its effective weight is _W_EDGE_OCCLUSION (40.0).
}

# Semantic rank table (R-05).  Higher rank → lower penalty.
_SEMANTIC_RANK: dict[str, int] = {
    "error": 5,
    "warn":  4,
    "good":  3,
    "path":  3,
    "info":  2,
    "muted": 1,
}
_SEMANTIC_RANK_DEFAULT: int = 2

# Frozen scoring weights — captured at import time (D-1, §4.4).
_W_OVERLAP: float       = _parse_weight_override("overlap",       10.0)
_W_DISPLACE: float      = _parse_weight_override("displace",       2.0)
_W_SIDE_HINT: float     = _parse_weight_override("side_hint",      5.0)
_W_SEMANTIC: float      = _parse_weight_override("semantic",       2.0)
_W_WHITESPACE: float    = _parse_weight_override("whitespace",     0.3)
_W_READING_FLOW: float  = _parse_weight_override("reading_flow",   0.8)
_W_EDGE_OCCLUSION: float = _parse_weight_override("edge_occlusion", 40.0)

# Score threshold above which R-19 degraded-placement warning fires.
# Raised from 50.0 → 200.0 when _W_DISPLACE was bumped 1.0→2.0 and the P1
# touch sentinel was bumped 1.0→3.0: the farthest clear nudge candidate can
# legitimately score up to ~135.6 pt (_W_DISPLACE×67px), so 200.0 keeps a
# comfortable gap above that while staying far below fully-blocked scores
# (≥ 10 000 pt when all candidates overlap).
_DEGRADED_SCORE_THRESHOLD: float = 200.0

# --- Arrow curve tuning constants (Phase A extraction) ---
# All numeric factors used by ``emit_arrow_svg`` for control-point and
# stagger geometry. Split out so Phase B can swap the control-point formula
# (port of perfect-arrows bow+stretch) without touching the caller.
_ARROW_CAP_FLOOR_FACTOR: float = 1.2
"""Cap floor: ``cell_height * 1.2`` — minimum visible bow height."""
_ARROW_CAP_EUCLID_SCALE: float = 0.18
"""Cap-per-euclid scale: long cross-grid arrows bow at 18% of euclidean."""
_ARROW_BASE_FLOOR_FACTOR: float = 0.5
"""Base-offset floor: ``cell_height * 0.5`` — prevents near-flat arrows."""
_ARROW_SQRT_SCALE: float = 2.5
"""Sqrt-scale multiplier for ``math.sqrt(euclid) * 2.5`` base-offset."""
_ARROW_STAGGER_FACTOR: float = 0.3
"""Per-index stagger step: ``cell_height * 0.3`` for same-target arrows."""
_ARROW_STAGGER_CAP: int = 4
"""``min(arrow_index, 4)`` — dense stacks capped so they don't fly off-canvas."""
_ARROW_LEADER_FAR_FACTOR: float = 1.0
"""R-27b leader-far gate: ``displacement >= pill_h * 1.0``. Unused in v0.15.0+; kept for import-stability."""
_LEADER_GAP_FACTOR: float = 1.0
"""v0.15.0 visual-gap gate tune surface: lower emits more leaders, higher emits fewer.

Replaces ``_ARROW_LEADER_FAR_FACTOR``; applies to the visual-gap metric
(``‖pill_centre − curve_mid‖``) rather than the legacy algorithmic displacement."""
_LEADER_ARC_CLEARANCE_PX: float = 4.0
"""Natural arc-clearance baseline (px) used by the v0.15.0 visual-gap gate.

Subtracted from the visual gap so an undisplaced pill sitting at its natural
``pill_h/2 + 4`` offset above the arc peak does not emit a spurious leader."""
_ARROW_VERT_ALIGN_H_SPAN: int = 4
"""Near-vertical column threshold (px) that triggers horizontal nudge."""
_ARROW_VERT_H_NUDGE_FACTOR: float = 0.6
"""Horizontal nudge magnitude: ``total_offset * 0.6`` for near-vertical arrows."""

# --- Perfect-arrows bow+stretch constants (Phase B, v0.12.2) ---
# Port of https://github.com/steveruizok/perfect-arrows. The curve amplitude
# is ``arc = bow + modulate(dist, [stretch_min, stretch_max], [1, 0]) * stretch``.
# At very short distances the arrow bows by ``bow + stretch``; at
# ``stretch_max`` and beyond it bows only by ``bow``. The perpendicular pixel
# offset of the quadratic control point from the midpoint equals
# ``arc * dist``. Tuned to approximate the old cap/sqrt formula at the
# mid-range (100–300 px) while straightening long cross-grid arrows.
_ARROW_BOW: float = 0.05
"""Constant-arc component. Keeps long cross-grid arrows visibly bowed."""
_ARROW_STRETCH: float = 0.20
"""Peak stretch component at ``dist <= stretch_min``."""
_ARROW_STRETCH_MIN: float = 0.0
"""Distance below which stretch saturates (1.0)."""
_ARROW_STRETCH_MAX: float = 1000.0
"""Distance above which stretch decays to 0 (raised from perfect-arrows
420 default so long DP-grid cross-cell arrows still bow)."""
_ARROW_PERP_FLOOR_FACTOR: float = 0.5
"""Minimum perpendicular offset = ``cell_height * 0.5``; keeps short
arrows visible even when ``arc * euclid`` is tiny."""


# --- Phase C (v0.13.0): grid-aware flow direction ---
# Primitives that render on a regular cell grid (Array, DPTable, Queue,
# HashMap, LinkedList, …) pass CellMetrics to emit_arrow_svg so the
# curve-direction helper can reason about motion in cell-space rather than
# raw pixels. Non-grid primitives (Graph, Tree, Plane2D) pass None and
# the classifier degrades to pure atan2.


class CellMetrics(NamedTuple):
    """Grid context for a single primitive at render time.

    All values are in SVG pixels. ``origin_x``/``origin_y`` are the
    top-left corner of cell[0][0] in the primitive's local coordinate
    space (i.e. before any scene translate). For non-grid primitives,
    pass ``cell_metrics=None`` instead of constructing a degenerate
    instance.
    """

    cell_width: float
    cell_height: float
    # TODO(v0.15.0): grid_cols / grid_rows / origin_x / origin_y are unused
    # by the scoring + geometry hot paths (only cell_width/cell_height feed
    # classify_flow, and sentinel checks are identity-only). Kept on the
    # struct for now to preserve the field-value regression suite
    # (test_cell_metrics_regression.py) and downstream debug tooling.
    # Candidate for removal once a real consumer is decided.
    grid_cols: int
    grid_rows: int
    origin_x: float
    origin_y: float


class FlowDirection(enum.IntEnum):
    """8-way compass classification for a displacement vector.

    Values match ``round(atan2(dy, dx) / (pi/4)) % 8`` with +y pointing
    down (SVG convention). ``RIGHTWARD`` (0) is the safe default for
    degenerate zero vectors.
    """

    RIGHTWARD = 0
    SE = 1
    DOWNWARD = 2
    SW = 3
    LEFTWARD = 4
    NW = 5
    UPWARD = 6
    NE = 7


def classify_flow(
    dx: float,
    dy: float,
    cell_metrics: CellMetrics | None = None,
) -> FlowDirection:
    """Classify a displacement vector into one of 8 :class:`FlowDirection` sectors.

    Zero vectors return :attr:`FlowDirection.RIGHTWARD` as a safe default.

    When ``cell_metrics`` is supplied, the displacement is first normalised
    by cell dimensions so sub-cell diagonals classify correctly on non-square
    grids (e.g. DPTable 60×40). With ``cell_metrics=None``, pure pixel-space
    atan2 is used and the Phase B behaviour is preserved exactly.
    """
    # Tolerance-based zero guard: floating-point subtraction in the caller
    # (``x2 - x1`` after shortening) can leave residuals well below the
    # sub-pixel threshold.  Treat anything under 1e-9 as the degenerate case.
    if math.hypot(dx, dy) < 1e-9:
        return FlowDirection.RIGHTWARD
    if cell_metrics is not None:
        cw = cell_metrics.cell_width
        ch = cell_metrics.cell_height
        nx = dx / cw if cw else dx
        ny = dy / ch if ch else dy
    else:
        nx, ny = dx, dy
    angle = math.atan2(ny, nx)
    sector = round(angle / (math.pi / 4)) % 8
    return FlowDirection(sector)


def _modulate(
    value: float,
    from_range: tuple[float, float],
    to_range: tuple[float, float],
    clamp: bool = True,
) -> float:
    """Linear remap with optional clamping (perfect-arrows helper).

    Maps ``value`` from ``from_range`` to ``to_range`` linearly; if
    ``clamp`` is True, the result is clamped to the ``to_range`` bounds.
    """
    a_low, a_high = from_range
    b_low, b_high = to_range
    span = a_high - a_low
    if span == 0:
        return b_low
    t = (value - a_low) / span
    out = b_low + t * (b_high - b_low)
    if clamp:
        lo = min(b_low, b_high)
        hi = max(b_low, b_high)
        if out < lo:
            out = lo
        elif out > hi:
            out = hi
    return out


@dataclass(frozen=True)
class _ScoreContext:
    """Immutable context passed to every _score_candidate call.

    Carries all per-annotation data that is constant across the 32 candidates:
    natural (un-nudged) position, pill dimensions, placement hints, and
    viewbox bounds.
    """

    natural_x: float
    natural_y: float
    pill_w: float
    pill_h: float
    side_hint: Literal["left", "right", "above", "below"] | None
    arc_direction: tuple[float, float]   # unit vector (dx, dy) src→dst
    color_token: str
    viewbox_w: float
    viewbox_h: float
    # Phase D/4 (v0.14.0): grid-aware flow sector. Non-None when the caller
    # supplied ``cell_metrics`` (i.e. grid context available). Drives P7
    # annotation-arc scale-down; reserved for future P2 side_hint refinement.
    flow: "FlowDirection | None" = None


# ---------------------------------------------------------------------------
# Scoring helpers (closed-form, D-1 deterministic)
# ---------------------------------------------------------------------------


def _aabb_intersects_pill(
    obs: _Obstacle,
    cx: float,
    cy: float,
    pill_w: float,
    pill_h: float,
) -> bool:
    """Return True if *obs* AABB overlaps the candidate pill AABB.

    Both AABBs are described by their centres and full dimensions.
    Uses the same non-overlap test as ``_LabelPlacement.overlaps``.
    """
    half_pw = pill_w / 2.0
    half_ph = pill_h / 2.0
    half_ow = obs.width / 2.0
    half_oh = obs.height / 2.0
    return not (
        cx + half_pw < obs.x - half_ow
        or cx - half_pw > obs.x + half_ow
        or cy + half_ph < obs.y - half_oh
        or cy - half_ph > obs.y + half_oh
    )


def _aabb_intersect_area(
    obs: _Obstacle,
    cx: float,
    cy: float,
    pill_w: float,
    pill_h: float,
) -> float:
    """Return the overlap area (px²) between *obs* AABB and the candidate pill.

    Returns 0.0 when there is no intersection.

    Uses an inclusive boundary convention matching ``_LabelPlacement.overlaps``:
    two AABBs that share an edge (touching) are considered overlapping.  When
    the geometric overlap area is exactly 0.0 (touching) a minimum penalty of
    3.0 px² (the "touch sentinel") is returned so that
    ``_W_OVERLAP * 3.0 * kind_weight`` provides a penalty that exceeds the P2
    displacement cost for a 0.5×pill_h gap, preserving "clear > touch"
    preference (spec §5.2 pill-equivalence; sentinel raised 1.0→3.0 when
    _W_DISPLACE was raised from 1.0→2.0).
    """
    half_pw = pill_w / 2.0
    half_ph = pill_h / 2.0
    half_ow = obs.width / 2.0
    half_oh = obs.height / 2.0

    overlap_x = min(cx + half_pw, obs.x + half_ow) - max(cx - half_pw, obs.x - half_ow)
    overlap_y = min(cy + half_ph, obs.y + half_oh) - max(cy - half_ph, obs.y - half_oh)

    # Strictly disjoint — no overlap and not touching.
    if overlap_x < 0.0 or overlap_y < 0.0:
        return 0.0
    # Touching (overlap == 0 on one axis) or truly overlapping.
    # Return at least 3.0 (the "touch sentinel") so that
    # ``_W_OVERLAP (10) × 3.0 × kind_weight (1.0)`` = 30 pt for a
    # boundary-touching candidate, which exceeds the P2 displacement cost of
    # ``_W_DISPLACE (2.0) × 9.5 px`` ≈ 19 pt for a 0.5×pill_h gap.
    # This preserves the "clear > touch" preference after _W_DISPLACE was
    # raised from 1.0 → 2.0.  (spec §5.2 pill-equivalence; sentinel 1.0→3.0)
    true_area = overlap_x * overlap_y
    return true_area if true_area >= 3.0 else 3.0


def boundary_clearance(
    cx: float,
    cy: float,
    obstacles: tuple[_Obstacle, ...],
) -> float:
    """Return the minimum clearance (px) from pill centre to any obstacle edge.

    Used for the P5 (whitespace) term.  Considers only AABB obstacles (not
    segments).  When there are no AABB obstacles the clearance is infinite —
    callers clamp via ``max(0, min_clearance - boundary_clearance(...))``.

    The clearance to a single AABB obstacle is the minimum of the four gap
    distances (left gap, right gap, top gap, bottom gap) between the pill
    centre and the obstacle edges.  This is not the AABB–AABB separation
    distance; it is the distance from the *centre* to the nearest obstacle
    face, which captures how "hemmed in" the candidate position is.
    """
    min_clearance = float("inf")
    for obs in obstacles:
        if obs.kind in ("segment", "edge_polyline", "annotation_arrow"):
            continue
        half_ow = obs.width / 2.0
        half_oh = obs.height / 2.0
        gap_left  = cx - (obs.x - half_ow)
        gap_right = (obs.x + half_ow) - cx
        gap_top   = cy - (obs.y - half_oh)
        gap_bot   = (obs.y + half_oh) - cy
        nearest = min(abs(gap_left), abs(gap_right), abs(gap_top), abs(gap_bot))
        if nearest < min_clearance:
            min_clearance = nearest
    return min_clearance


def side_hint_violation(
    cx: float,
    cy: float,
    ctx: _ScoreContext,
) -> float:
    """Return 1.0 if the candidate is in the wrong half-plane, else 0.0.

    Implements the P3 (side_hint) binary term.  The half-plane check is
    relative to the natural position:

    - ``"above"``: candidate must have ``cy < ctx.natural_y``
    - ``"below"``: candidate must have ``cy > ctx.natural_y``
    - ``"left"``:  candidate must have ``cx < ctx.natural_x``
    - ``"right"``: candidate must have ``cx > ctx.natural_x``

    Returns 0.0 when *side_hint* is ``None`` (no preference).
    """
    hint = ctx.side_hint
    if hint is None:
        return 0.0
    if hint == "above":
        return 0.0 if cy < ctx.natural_y else 1.0
    if hint == "below":
        return 0.0 if cy > ctx.natural_y else 1.0
    if hint == "left":
        return 0.0 if cx < ctx.natural_x else 1.0
    if hint == "right":
        return 0.0 if cx > ctx.natural_x else 1.0
    return 0.0


def reading_flow_cost(
    cx: float,
    cy: float,
    ctx: _ScoreContext,
) -> float:
    """Return 0.0 if candidate is in the Hirsch-ladder preferred quadrant, else 1.0.

    Implements P6 (reading_flow) per R-06 (Hirsch 1982).  The preferred
    quadrant rotates with the arc direction:

    - Horizontal-ish arc (|dx| >= |dy|): prefer NE (cx > natural_x, cy < natural_y)
    - Vertical-ish arc   (|dy| >  |dx|): prefer NW (cx < natural_x, cy < natural_y)
    - Zero vector: no preference, return 0.0.

    The arc_direction is the (dx, dy) unit vector from source to destination.
    """
    adx, ady = ctx.arc_direction
    abs_adx = abs(adx)
    abs_ady = abs(ady)
    if abs_adx == 0.0 and abs_ady == 0.0:
        return 0.0
    # Determine preferred quadrant relative to natural position.
    if abs_adx >= abs_ady:
        # Horizontal-ish: prefer NE (right of and above natural).
        preferred = cx >= ctx.natural_x and cy <= ctx.natural_y
    else:
        # Vertical-ish: prefer NW (left of and above natural).
        preferred = cx <= ctx.natural_x and cy <= ctx.natural_y
    return 0.0 if preferred else 1.0


def semantic_rank(color_token: str) -> int:
    """Return the semantic priority rank for *color_token* (1–5).

    Higher rank → label is higher priority → lower P4 penalty (better positions).
    Unknown tokens return ``_SEMANTIC_RANK_DEFAULT`` (2).
    """
    return _SEMANTIC_RANK.get(color_token, _SEMANTIC_RANK_DEFAULT)


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------


def _score_candidate(
    cx: float,
    cy: float,
    obstacles: tuple[_Obstacle, ...],
    ctx: _ScoreContext,
) -> float:
    """Return composite penalty score for placing a pill at (cx, cy).

    Lower is better.  Returns ``float("inf")`` when a MUST-severity obstacle
    is violated (hard-block discipline, §2.3).

    Terms (spec §2.2):
        P1  _W_OVERLAP        — weighted AABB intersection area
        P2  _W_DISPLACE       — Euclidean distance from natural position
        P3  _W_SIDE_HINT      — binary half-plane violation
        P4  _W_SEMANTIC       — semantic priority cost (1 − rank/5)
        P5  _W_WHITESPACE     — clearance deficit below required minimum
        P6  _W_READING_FLOW   — Hirsch-ladder quadrant preference
        P7  _W_EDGE_OCCLUSION — normalised segment-in-pill length
    """
    pill_w = ctx.pill_w
    pill_h = ctx.pill_h

    # Hard-block pass (§2.3) — MUST-severity violations return inf immediately.
    for obs in obstacles:
        if obs.severity != "MUST":
            continue
        if obs.kind == "target_cell":
            if _aabb_intersects_pill(obs, cx, cy, pill_w, pill_h):
                return float("inf")
        elif obs.kind in ("segment", "edge_polyline"):
            if _segment_rect_clip_length(
                obs.x, obs.y, obs.x2, obs.y2, cx, cy, pill_w, pill_h
            ) > 0.0:
                return float("inf")

    # Segment-kind set: includes annotation_arrow (R-31 ext) which contributes
    # to P7 (SHOULD severity, no hard-block) and is excluded from P1 (AABB).
    _SEGMENT_KINDS = ("segment", "edge_polyline", "annotation_arrow")

    # P1 — weighted overlap area over AABB obstacles.
    p1 = sum(
        _aabb_intersect_area(obs, cx, cy, pill_w, pill_h)
        * _KIND_WEIGHT.get(obs.kind, 1.0)
        for obs in obstacles
        if obs.kind not in _SEGMENT_KINDS
    )

    # P2 — displacement from natural position.
    p2 = math.hypot(cx - ctx.natural_x, cy - ctx.natural_y)

    # P3 — side-hint half-plane violation (binary).
    p3 = side_hint_violation(cx, cy, ctx)

    # P4 — semantic priority cost.
    p4 = 1.0 - semantic_rank(ctx.color_token) / 5.0

    # P5 — whitespace / boundary clearance deficit.
    min_clearance_required = max(4.0, pill_h * 0.15)
    actual_clearance = boundary_clearance(cx, cy, obstacles)
    p5 = max(0.0, min_clearance_required - actual_clearance)

    # P6 — reading flow / Hirsch-ladder cost (binary).
    p6 = reading_flow_cost(cx, cy, ctx)

    # P7 — edge occlusion: saturating normalised clipped segment length.
    # Covers "segment", "edge_polyline", and "annotation_arrow" (R-31 ext).
    # Normalise against the short side of the pill so that any clip ≥ pill_h
    # saturates to 1.0 per segment, giving _W_EDGE_OCCLUSION penalty per
    # clipping segment.  Grazing clips (< pill_h) remain proportional.
    # This prevents a 20-px displacement (cost 20) from being cheaper than
    # staying on a clipping arrow (cost 40+), which was the root cause of
    # pills overlapping annotation-arrow strokes (R-31 ext, §P7-saturate).
    pill_short = min(pill_w, pill_h)
    # Phase D/4 (v0.14.0): when grid context is available (ctx.flow is not None),
    # scale the annotation_arrow P7 contribution by 0.75.  The stagger-flip in
    # _compute_control_points distributes alternating arcs to opposite perp
    # sides, reducing expected cross-occlusion on 2D stacks.  Non-arrow segment
    # kinds (edges, axes, …) stay at 1.0.
    _flow_p7_scale = 0.75 if ctx.flow is not None else 1.0
    if pill_short > 0.0:
        p7 = sum(
            min(1.0, _segment_rect_clip_length(
                obs.x, obs.y, obs.x2, obs.y2, cx, cy, pill_w, pill_h
            ) / pill_short)
            * (_flow_p7_scale if obs.kind == "annotation_arrow" else 1.0)
            for obs in obstacles
            if obs.kind in _SEGMENT_KINDS
        )
    else:
        p7 = 0.0

    return (
        _W_OVERLAP       * p1
        + _W_DISPLACE    * p2
        + _W_SIDE_HINT   * p3
        + _W_SEMANTIC    * p4
        + _W_WHITESPACE  * p5
        + _W_READING_FLOW * p6
        + _W_EDGE_OCCLUSION * p7
    )


def _pick_best_candidate(
    candidates: tuple[tuple[float, float], ...],
    obstacles: tuple[_Obstacle, ...],
    ctx: _ScoreContext,
) -> tuple[float, float, float]:
    """Score all candidates and return the best (cx, cy, score).

    Uses stable tie-break: primary key = score ascending, secondary key =
    candidate enumeration index.  Never uses ``min()`` over a generator
    (spec §4.2 D-1 requirement).

    If all candidates return ``float("inf")`` (every position hard-blocked),
    falls back to argmin over a fresh score pass treating MUST violations as
    finite (R-17 fallback semantics — best available position even if blocked).
    R-19 warning is the caller's responsibility.

    Parameters
    ----------
    candidates:
        Ordered tuple of ``(cx, cy)`` positions.  Enumeration index is used
        for tie-breaking, so the order is part of the contract.
    obstacles:
        Tuple of active obstacles for this frame (AABB + segment kinds).
    ctx:
        Immutable scoring context for this annotation.

    Returns
    -------
    tuple[float, float, float]
        ``(best_cx, best_cy, best_score)``
    """
    scored: list[tuple[float, int, float, float]] = [
        (_score_candidate(cx, cy, obstacles, ctx), i, cx, cy)
        for i, (cx, cy) in enumerate(candidates)
    ]
    scored.sort(key=lambda t: (t[0], t[1]))

    best_score, _, best_cx, best_cy = scored[0]

    # If all candidates are hard-blocked, fall back to finite-score argmin.
    if best_score == float("inf"):
        finite_scored: list[tuple[float, int, float, float]] = []
        for i, (cx, cy) in enumerate(candidates):
            # Re-score without hard-block returns by computing terms directly.
            # We reuse _score_candidate but strip inf: replace inf with a large
            # finite value so the argmin finds the "least bad" position.
            raw = _score_candidate(cx, cy, obstacles, ctx)
            finite_scored.append((raw if raw != float("inf") else 1e18, i, cx, cy))
        finite_scored.sort(key=lambda t: (t[0], t[1]))
        best_score, _, best_cx, best_cy = finite_scored[0]
        # Restore the actual score (inf) for the caller to detect degradation.
        best_score = float("inf")

    return best_cx, best_cy, best_score


def _label_has_math(text: str) -> bool:
    """True if *text* contains at least one ``$...$`` inline math fragment."""
    return bool(text) and bool(_MATH_DELIM_RE.search(text))


# Ordered 8-direction compass list used by _nudge_candidates.
# Tie-break priority: N, S, E, W, NE, NW, SE, SW.
# Each entry is (dx_sign, dy_sign) where values are -1, 0, or +1.
_COMPASS_8 = (
    (0, -1),    # 0: N
    (0, +1),    # 1: S
    (+1, 0),    # 2: E
    (-1, 0),    # 3: W
    (+1, -1),   # 4: NE
    (-1, -1),   # 5: NW
    (+1, +1),   # 6: SE
    (-1, +1),   # 7: SW
)

# Half-plane preferred direction indices for side hints.
# Only strictly-preferred half-plane directions (not neutral E/W or N/S) are
# listed here so that test_side_hint_above_upper_first can assert all first-4
# candidates have dy < 0.  Neutral directions (E/W for above/below, N/S for
# left/right) are included in the "other" group that comes second.
_SIDE_HINT_PREFERRED: dict[str, tuple[int, ...]] = {
    "above": (0, 4, 5),   # N, NE, NW  (all dy < 0)
    "below": (1, 6, 7),   # S, SE, SW  (all dy > 0)
    "left":  (3, 5, 7),   # W, NW, SW  (all dx < 0)
    "right": (2, 4, 6),   # E, NE, SE  (all dx > 0)
}


def _nudge_candidates(
    pill_w: float,
    pill_h: float,
    side_hint: str | None = None,
) -> Iterator[tuple[float, float]]:
    """Yield (dx, dy) nudge offsets in Manhattan-distance order for collision resolution.

    Generates 48 candidates = 8 compass directions x 6 step sizes.

    Step sizes are fractions of *pill_h*: 0.25, 0.5, 1.0, 1.5, 2.0, 2.5.
    Both horizontal and vertical steps use *pill_h*-based sizing so the grid
    is square in pixel space.

    Within the same Manhattan distance, candidates follow the fixed priority:
    N, S, E, W, NE, NW, SE, SW.

    When *side_hint* is one of ``"above"``, ``"below"``, ``"left"``, ``"right"``,
    the strictly-preferred half-plane candidates (e.g. N, NE, NW for "above")
    are emitted first across all step sizes (sorted by Manhattan distance),
    followed by the remaining candidates in Manhattan-distance order.

    When *side_hint* is ``None`` or unknown, all 48 candidates are sorted by
    Manhattan distance (smallest first) with the fixed tie-break direction
    priority.

    Parameters
    ----------
    pill_w:
        Pill width in pixels (unused for step sizing; retained for API
        symmetry in case callers want aspect-aware steps in the future).
    pill_h:
        Pill height in pixels.  Steps are multiples of this value.
    side_hint:
        Optional placement preference: ``"above"``, ``"below"``, ``"left"``,
        or ``"right"``.  When provided, candidates in the preferred half-plane
        are emitted before the rest.

    Yields
    ------
    tuple[float, float]
        ``(dx, dy)`` offset tuples, smallest Manhattan distance first.
        Within equal distance, order follows N, S, E, W, NE, NW, SE, SW.
    """
    steps = (pill_h * 0.25, pill_h * 0.5, pill_h * 1.0, pill_h * 1.5, pill_h * 2.0, pill_h * 2.5)

    # Build all 48 (dx, dy, priority_index) tuples.
    all_candidates: list[tuple[float, float, int]] = []
    for step in steps:
        for priority, (dx_sign, dy_sign) in enumerate(_COMPASS_8):
            dx = dx_sign * step
            dy = dy_sign * step
            all_candidates.append((dx, dy, priority))

    def _manhattan(c: tuple[float, float, int]) -> float:
        return abs(c[0]) + abs(c[1])

    hint_key = side_hint if side_hint in _SIDE_HINT_PREFERRED else None

    if hint_key is None:
        # No side hint: sort all 48 by (manhattan_distance, priority_index).
        sorted_candidates = sorted(all_candidates, key=lambda c: (_manhattan(c), c[2]))
        for dx, dy, _ in sorted_candidates:
            yield (dx, dy)
    else:
        preferred_set = set(_SIDE_HINT_PREFERRED[hint_key])

        preferred = [c for c in all_candidates if c[2] in preferred_set]
        other = [c for c in all_candidates if c[2] not in preferred_set]

        sorted_preferred = sorted(preferred, key=lambda c: (_manhattan(c), c[2]))
        sorted_other = sorted(other, key=lambda c: (_manhattan(c), c[2]))

        for dx, dy, _ in sorted_preferred:
            yield (dx, dy)
        for dx, dy, _ in sorted_other:
            yield (dx, dy)


# Regex to match LaTeX command tokens like \frac, \sum, \alpha, etc.
_LATEX_CMD_RE = re.compile(r"\\[a-zA-Z]+")

# ---------------------------------------------------------------------------
# R-11: LaTeX → speech helper
# ---------------------------------------------------------------------------

# Known LaTeX token → spoken-word replacements (R-11 required set).
_LATEX_SPEECH_MAP: dict[str, str] = {
    r"\alpha": "alpha",
    r"\beta": "beta",
    r"\gamma": "gamma",
    r"\delta": "delta",
    r"\epsilon": "epsilon",
    r"\theta": "theta",
    r"\lambda": "lambda",
    r"\mu": "mu",
    r"\pi": "pi",
    r"\sigma": "sigma",
    r"\phi": "phi",
    r"\omega": "omega",
    r"\sum": "sum",
    r"\infty": "infinity",
    r"\cdot": "times",
    r"\leq": "less than or equal",
    r"\geq": "greater than or equal",
    r"\neq": "not equal",
    r"\approx": "approximately",
    r"\in": "in",
    r"\notin": "not in",
    r"\times": "times",
    r"\div": "divided by",
    r"\pm": "plus or minus",
    r"\sqrt": "square root of",
    r"\frac": "",  # removed; sub/sup handles numerator/denominator context
    r"\left": "",
    r"\right": "",
}

# Regex for subscript: _{n}, _{ab}, _n (single char), _0 etc.
_SUBSCRIPT_RE = re.compile(r"_\{([^}]+)\}|_([A-Za-z0-9])")
# Regex for superscript: ^{n}, ^n (single char).
_SUPERSCRIPT_RE = re.compile(r"\^\{([^}]+)\}|\^([A-Za-z0-9])")


def _latex_to_speech(tex: str) -> str:
    r"""Convert a LaTeX-containing string to a screen-reader-friendly speech form.

    Algorithm (R-11):
    1. Strip ``$`` delimiters.
    2. Replace known ``\command`` tokens from ``_LATEX_SPEECH_MAP``.
    3. Replace ``_{n}`` / ``_n`` → `` subscript n``.
    4. Replace ``^{n}`` / ``^n`` → `` to the power n``.
    5. Remove remaining ``\`` prefix for unknown tokens.
    6. Strip brace characters ``{`` / ``}``.
    7. Collapse whitespace.
    """
    if not tex:
        return tex

    # Step 1: strip $ delimiters (both opening and closing).
    result = _MATH_DELIM_RE.sub(lambda m: m.group(0)[1:-1], tex)

    # Step 2: replace known LaTeX commands before generic stripping.
    for cmd, replacement in _LATEX_SPEECH_MAP.items():
        result = result.replace(cmd, f" {replacement} " if replacement else " ")

    # Step 3: subscripts.
    def _sub_repl(m: re.Match) -> str:
        content = m.group(1) if m.group(1) is not None else m.group(2)
        return f" subscript {content}"

    result = _SUBSCRIPT_RE.sub(_sub_repl, result)

    # Step 4: superscripts.
    def _sup_repl(m: re.Match) -> str:
        content = m.group(1) if m.group(1) is not None else m.group(2)
        return f" to the power {content}"

    result = _SUPERSCRIPT_RE.sub(_sup_repl, result)

    # Step 5: strip remaining \ prefix for unknown tokens.
    result = re.sub(r"\\([a-zA-Z]+)", r"\1", result)

    # Step 6: strip brace chars.
    result = result.replace("{", "").replace("}", "")

    # Step 7: collapse whitespace.
    result = " ".join(result.split())

    return result


def _point_in_rect(
    px: float, py: float, rx: float, ry: float, rw: float, rh: float
) -> bool:
    """Return True if *(px, py)* lies strictly inside the axis-aligned rect.

    The rect is defined by its centre *(rx, ry)* and dimensions *(rw, rh)*.
    Points exactly on the boundary are considered inside (inclusive test).
    """
    half_w = rw / 2.0
    half_h = rh / 2.0
    return (rx - half_w <= px <= rx + half_w) and (ry - half_h <= py <= ry + half_h)


def _line_rect_intersection(
    origin_x: float,
    origin_y: float,
    pill_cx: float,
    pill_cy: float,
    pill_w: float,
    pill_h: float,
) -> tuple[int, int] | None:
    """Return the point where the line from *origin* through *pill_cx/cy* first hits the pill AABB.

    The pill AABB is centred at *(pill_cx, pill_cy)* with half-dimensions
    *(pill_w/2, pill_h/2)*.  The function parametrises the ray from *origin*
    toward the centre, clips to each of the 4 half-planes, and returns the
    smallest positive *t* at which the ray exits the AABB.

    Returns:
        The intersection point as ``(x, y)`` integers, or ``None`` when the
        origin lies inside the pill AABB (signals "no leader needed" to the
        caller — the leader endpoint would be identical to the anchor point,
        producing a zero-length invisible line).

    Falls back to the pill centre when origin == centre (degenerate case:
    origin at exact centre is outside the AABB detection range so it is
    treated separately before the inside-rect check).

    Used by R-08: leader endpoint at pill perimeter (not pill centre).
    """
    half_w = pill_w / 2.0
    half_h = pill_h / 2.0

    ddx = pill_cx - origin_x
    ddy = pill_cy - origin_y

    if abs(ddx) < 1e-6 and abs(ddy) < 1e-6:
        # Degenerate: origin is at pill centre — return centre unchanged.
        return int(pill_cx), int(pill_cy)

    # HIGH-1: if origin is inside the pill AABB the ray travels outward in the
    # same direction it enters, so all t > 0 candidates land on the *far* side
    # of the rect, not the near edge.  A leader from inside the pill to the far
    # edge is visually meaningless (zero-length or backward).  Return None so
    # the caller can skip leader emission for this candidate.
    if _point_in_rect(origin_x, origin_y, pill_cx, pill_cy, pill_w, pill_h):
        return None

    # Compute t for each of the 4 AABB edges.
    # Ray: P(t) = origin + t * (dd).
    # We want the smallest t > 0 such that P(t) is ON an edge of the AABB.
    t_candidates: list[float] = []

    if abs(ddx) > 1e-9:
        # Left edge: pill_cx - half_w
        t_left = (pill_cx - half_w - origin_x) / ddx
        if t_left > 0:
            y_at_t = origin_y + t_left * ddy
            if pill_cy - half_h <= y_at_t <= pill_cy + half_h:
                t_candidates.append(t_left)
        # Right edge: pill_cx + half_w
        t_right = (pill_cx + half_w - origin_x) / ddx
        if t_right > 0:
            y_at_t = origin_y + t_right * ddy
            if pill_cy - half_h <= y_at_t <= pill_cy + half_h:
                t_candidates.append(t_right)

    if abs(ddy) > 1e-9:
        # Top edge: pill_cy - half_h
        t_top = (pill_cy - half_h - origin_y) / ddy
        if t_top > 0:
            x_at_t = origin_x + t_top * ddx
            if pill_cx - half_w <= x_at_t <= pill_cx + half_w:
                t_candidates.append(t_top)
        # Bottom edge: pill_cy + half_h
        t_bot = (pill_cy + half_h - origin_y) / ddy
        if t_bot > 0:
            x_at_t = origin_x + t_bot * ddx
            if pill_cx - half_w <= x_at_t <= pill_cx + half_w:
                t_candidates.append(t_bot)

    if not t_candidates:
        # No valid intersection found (unexpected geometry) — return None to
        # suppress leader emission rather than producing an invisible dot.
        return None

    t_hit = min(t_candidates)
    hit_x = origin_x + t_hit * ddx
    hit_y = origin_y + t_hit * ddy
    return int(hit_x), int(hit_y)


# ---------------------------------------------------------------------------
# R-31 geometry helpers — Liang–Barsky segment-vs-rect clipping
# ---------------------------------------------------------------------------
# Rect convention (matches _point_in_rect / _line_rect_intersection above):
#   centre (rx, ry), full dimensions (rw, rh) → corners at
#   (rx±rw/2, ry±rh/2).
#
# Both helpers are closed-form and D-1 deterministic: no iterative solvers,
# no numpy, no randomness.  NOT added to __all__ (internal, prefix _).
# ---------------------------------------------------------------------------


def _segment_intersects_rect(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    rx: float,
    ry: float,
    rw: float,
    rh: float,
) -> bool:
    """Return True if the segment (x0,y0)→(x1,y1) intersects the axis-aligned rect.

    "Intersects" means any overlap: the segment may cross an edge, lie fully
    inside the rect, or have exactly one endpoint on the boundary.

    The rect is defined by centre *(rx, ry)* and full dimensions *(rw, rh)*,
    matching the convention used by :func:`_point_in_rect` and
    :func:`_line_rect_intersection`.

    Uses Liang–Barsky parametric clipping (closed-form, D-1 deterministic).

    Args:
        x0: Start x of segment.
        y0: Start y of segment.
        x1: End x of segment.
        y1: End y of segment.
        rx: Rect centre x.
        ry: Rect centre y.
        rw: Rect full width  (>= 0).
        rh: Rect full height (>= 0).

    Returns:
        True if the segment has any point in common with the closed rect.
    """
    half_w = rw / 2.0
    half_h = rh / 2.0
    xmin = rx - half_w
    xmax = rx + half_w
    ymin = ry - half_h
    ymax = ry + half_h

    dx = x1 - x0
    dy = y1 - y0

    t0 = 0.0
    t1 = 1.0

    # Four Liang–Barsky half-planes: p*t <= q  →  t >= q/p (lower) or t <= q/p (upper).
    # p < 0  →  lower bound update; p > 0  →  upper bound update; p == 0  →  reject if q < 0.
    for p, q in (
        (-dx, x0 - xmin),   # left   edge
        ( dx, xmax - x0),   # right  edge
        (-dy, y0 - ymin),   # bottom edge
        ( dy, ymax - y0),   # top    edge
    ):
        if abs(p) < 1e-12:
            # Segment is parallel to this pair of edges.
            if q < 0.0:
                return False  # outside this slab entirely
            # Otherwise fully inside this slab; continue to next edges.
        elif p < 0.0:
            t0 = max(t0, q / p)
        else:
            t1 = min(t1, q / p)

        if t0 > t1:
            return False

    return True


def _segment_rect_clip_length(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    rx: float,
    ry: float,
    rw: float,
    rh: float,
) -> float:
    """Return the length of the portion of the segment (x0,y0)→(x1,y1) inside the rect.

    Returns ``0.0`` when there is no intersection.

    The rect is defined by centre *(rx, ry)* and full dimensions *(rw, rh)*,
    matching the convention used by :func:`_point_in_rect` and
    :func:`_line_rect_intersection`.

    Uses Liang–Barsky parametric clipping.  The clipped length is:

    .. code-block:: text

        length = sqrt(dx**2 + dy**2) * (t1 - t0)

    where *t0*, *t1* ∈ [0, 1] are the entry/exit parameters.

    For a zero-length segment (x0==x1 and y0==y1) this returns ``0.0``
    regardless of position (the "length" of a point is zero).

    Args:
        x0: Start x of segment.
        y0: Start y of segment.
        x1: End x of segment.
        y1: End y of segment.
        rx: Rect centre x.
        ry: Rect centre y.
        rw: Rect full width  (>= 0).
        rh: Rect full height (>= 0).

    Returns:
        Euclidean length of the clipped portion (>= 0.0).
    """
    half_w = rw / 2.0
    half_h = rh / 2.0
    xmin = rx - half_w
    xmax = rx + half_w
    ymin = ry - half_h
    ymax = ry + half_h

    dx = x1 - x0
    dy = y1 - y0

    t0 = 0.0
    t1 = 1.0

    for p, q in (
        (-dx, x0 - xmin),
        ( dx, xmax - x0),
        (-dy, y0 - ymin),
        ( dy, ymax - y0),
    ):
        if abs(p) < 1e-12:
            if q < 0.0:
                return 0.0
        elif p < 0.0:
            t0 = max(t0, q / p)
        else:
            t1 = min(t1, q / p)

        if t0 > t1:
            return 0.0

    seg_len = (dx * dx + dy * dy) ** 0.5
    return seg_len * (t1 - t0)


def _label_width_text(text: str) -> str:
    r"""Return a width-estimation string derived from *text*.

    For plain text: returned unchanged.
    For math labels (containing ``$...$``):

    1. Strip ``$`` delimiters.
    2. Strip ``\\command`` tokens (``\\frac``, ``\\sum``, ``\\alpha``, etc.).
    3. Strip brace characters ``{`` and ``}``.
    4. Repeat the remaining characters by 1.15× (by appending a scaled
       suffix) so that ``estimate_text_width`` accounts for the structural
       overhead of rendered math, which KaTeX renders ~15 % wider than a
       naive character count suggests.

    The 1.15× factor is applied by returning a string whose estimated
    width, when passed to ``estimate_text_width``, equals the corrected
    estimate.  Because ``estimate_text_width`` is linear in character count
    for ASCII, repeating characters achieves the scale accurately.
    """
    if not text:
        return ""
    has_math = _label_has_math(text)
    # Strip $ delimiters from math spans.
    result = _MATH_DELIM_RE.sub(lambda m: m.group(0)[1:-1], text)
    if has_math:
        # Strip LaTeX command tokens and braces.
        result = _LATEX_CMD_RE.sub("", result)
        result = result.replace("{", "").replace("}", "")
        # Apply 1.15x scale by appending 15% extra characters.
        # We append a scaled copy of the stripped string so that
        # estimate_text_width(result_scaled) ≈ estimate_text_width(result) * 1.15.
        extra_len = max(1, int(len(result) * 0.15))
        result = result + result[:extra_len]
    return result


def _emit_label_single_line(
    *,
    label_text: str,
    fi_x: int,
    fi_y: int,
    pill_rx: int,
    pill_ry: int,
    pill_w: int,
    pill_h: int,
    l_fill: str,
    l_weight: str,
    l_size: str,
    render_inline_tex: "Callable[[str], str] | None",
) -> str:
    """Emit an annotation label as either ``<text>`` or KaTeX foreignObject.

    When *label_text* contains ``$...$`` math and a ``render_inline_tex``
    callback is available, the label is emitted as an SVG
    ``<foreignObject>`` hosting the KaTeX-rendered HTML centered inside the
    pill rectangle.  Falls back to plain SVG ``<text>`` otherwise.
    """
    if render_inline_tex is not None and _label_has_math(label_text):
        try:
            html = render_inline_tex(label_text)
        except Exception:
            html = None
        if html:
            weight_css = f"font-weight:{l_weight};" if l_weight else ""
            size_css = f"font-size:{l_size};" if l_size else ""
            return (
                f'    <foreignObject x="{pill_rx}" y="{pill_ry}"'
                f' width="{pill_w}" height="{pill_h}"'
                f' class="scriba-annot-fobj">'
                f'<div xmlns="http://www.w3.org/1999/xhtml"'
                f' class="scriba-annot-label"'
                f' style="width:100%;height:100%;display:flex;'
                f'align-items:center;justify-content:center;'
                f'text-align:center;line-height:1;'
                f'white-space:pre-wrap;gap:0.25em;'
                f'color:{l_fill};{weight_css}{size_css}'
                f'text-shadow:0 0 2px #fff,0 0 2px #fff;">'
                f'{html}</div></foreignObject>'
            )

    # Fallback: plain SVG <text> with halo.
    style_parts: list[str] = []
    if l_weight:
        style_parts.append(f"font-weight:{l_weight}")
    if l_size:
        style_parts.append(f"font-size:{l_size}")
    style_parts.append("text-anchor:middle")
    style_parts.append("dominant-baseline:auto")
    style_str = ";".join(style_parts)
    text_attrs = (
        f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
        f' stroke="white" stroke-width="3"'
        f' stroke-linejoin="round" paint-order="stroke fill"'
    )
    return (
        f'    <text {text_attrs} style="{style_str}">'
        f'{_escape_xml(label_text)}</text>'
    )


def _wrap_label_lines(text: str, max_chars: int = _LABEL_MAX_WIDTH_CHARS) -> list[str]:
    """Split label text into lines at natural break points if it exceeds *max_chars*.

    Split characters: space, comma, ``+``, ``=``.  The ``-`` character is
    intentionally excluded from splitting to avoid breaking LaTeX math
    expressions like ``$f(x)=-4$`` across lines.  Inside ``$...$`` delimiters
    no splitting occurs at all (``in_math`` guard).
    """
    if len(text) <= max_chars:
        return [text]
    # Split at spaces, operators, commas — but NOT inside $...$ math regions.
    tokens: list[str] = []
    current = ""
    in_math = False
    for ch in text:
        if ch == "$":
            in_math = not in_math
        current += ch
        if not in_math and ch in (" ", ",", "+", "="):
            tokens.append(current)
            current = ""
    if current:
        tokens.append(current)

    lines: list[str] = []
    line = ""
    for tok in tokens:
        if line and len(line) + len(tok) > max_chars:
            lines.append(line.rstrip())
            line = tok
        else:
            line += tok
    if line:
        lines.append(line.rstrip())
    return lines if lines else [text]


# ---------------------------------------------------------------------------
# R-31 ext: Prior-annotation arrow-stroke obstacle sampling
# ---------------------------------------------------------------------------

# Number of evenly-spaced t-values used to sample a cubic Bezier arc.
# N=8 yields N-1=7 line segments, providing ~7x oversampling vs a single chord.
# Closed-form, D-1 deterministic (no iterative solver, no randomness).
_BEZIER_SAMPLE_N: int = 8


def _sample_arrow_segments(
    arrow_path_points: "tuple[float, float, float, float, float, float, float, float]",
    *,
    state: "str" = "default",
    is_straight: bool = False,
) -> "list[Any]":
    """Sample an arrow geometry into a list of ObstacleSegment instances.

    For cubic Bezier arcs (``is_straight=False``):
        Evaluates the Bezier at N=8 evenly-spaced t values and returns N-1=7
        line segments connecting consecutive sample points.  Closed-form
        (no iterative solver).

    For straight lines (``is_straight=True``):
        Returns a single segment from start to end.

    All returned segments carry ``kind="annotation_arrow"`` and
    ``severity="SHOULD"`` (never MUST — annotation arrows are soft-penalty
    obstacles per R-31 ext; they penalise pill placement but do not hard-block
    when no MUST-free position is available).

    Parameters
    ----------
    arrow_path_points:
        ``(x1, y1, cx1, cy1, cx2, cy2, x2, y2)`` — start point, two cubic
        Bezier control points, and end point, all in SVG coordinates.
        For straight lines only ``x1, y1, x2, y2`` are used.
    state:
        Rendering state of the arrow (propagated to the obstacle ``state``
        field).  Defaults to ``"default"``.
    is_straight:
        ``True`` for straight-line arrows (``emit_plain_arrow_svg`` stem).
        ``False`` (default) for cubic Bezier arcs.

    Returns
    -------
    list[ObstacleSegment]
        Sampled line-segment obstacles.  Empty list when N < 2 (degenerate).
    """
    from scriba.animation.primitives._obstacle_types import ObstacleSegment

    x1, y1, cx1, cy1, cx2, cy2, x2, y2 = arrow_path_points

    if is_straight:
        # Single segment from stem start to stem end.
        return [
            ObstacleSegment(
                kind="annotation_arrow",
                x0=x1,
                y0=y1,
                x1=x2,
                y1=y2,
                state=state,
                severity="SHOULD",
            )
        ]

    # Cubic Bezier: sample at N evenly-spaced t ∈ [0, 1] and produce N-1 segments.
    n = _BEZIER_SAMPLE_N
    segments: list[ObstacleSegment] = []

    # Pre-compute sample points.  B(t) = (1-t)³P0 + 3(1-t)²tP1 + 3(1-t)t²P2 + t³P3
    def _bezier_point(t: float) -> tuple[float, float]:
        mt = 1.0 - t
        bx = mt**3 * x1 + 3 * mt**2 * t * cx1 + 3 * mt * t**2 * cx2 + t**3 * x2
        by = mt**3 * y1 + 3 * mt**2 * t * cy1 + 3 * mt * t**2 * cy2 + t**3 * y2
        return bx, by

    pts: list[tuple[float, float]] = [
        _bezier_point(i / (n - 1)) for i in range(n)
    ]

    for i in range(len(pts) - 1):
        px0, py0 = pts[i]
        px1, py1 = pts[i + 1]
        segments.append(
            ObstacleSegment(
                kind="annotation_arrow",
                x0=px0,
                y0=py0,
                x1=px1,
                y1=py1,
                state=state,
                severity="SHOULD",
            )
        )

    return segments


# ---------------------------------------------------------------------------
# Shared arrow annotation infrastructure
# ---------------------------------------------------------------------------

# Annotation pill labels (ARROW_STYLES "label_fill") are rendered on a white
# semi-opaque pill background (fill="white" fill-opacity="0.92").  All label_fill
# values below have been verified ≥ 4.5:1 against white (WCAG AA, 2026-04-17):
#   good  #027a55 → 5.36:1   info   #506882 → 5.76:1
#   warn  #92600a → 5.38:1   error  #c6282d → 5.61:1
#   muted #526070 → 6.43:1   path   #2563eb → 5.17:1
ARROW_STYLES: dict[str, dict[str, str]] = {
    "good": {
        "stroke": "#027a55",      # darkened from #059669 (3.77:1 ✗) → 5.36:1 ✓
        "stroke_width": "2.2",
        "opacity": "1.0",
        "label_fill": "#027a55",
        "label_weight": "700",
        "label_size": "12px",
    },
    "info": {
        "stroke": "#506882",      # darkened from #94a3b8 (2.56:1 ✗) → 5.76:1 ✓
        "stroke_width": "1.5",
        "opacity": "0.7",         # R-12: floor raised from 0.45 → 0.7 (WCAG 1.4.11)
        "label_fill": "#506882",
        "label_weight": "500",
        "label_size": "11px",
    },
    "warn": {
        "stroke": "#92600a",      # darkened from #d97706 (3.19:1 ✗) → 5.38:1 ✓
        "stroke_width": "2.0",
        "opacity": "0.8",
        "label_fill": "#92600a",
        "label_weight": "600",
        "label_size": "11px",
    },
    "error": {
        "stroke": "#c6282d",      # darkened from #dc2626 (4.83:1 ✗) → 5.61:1 ✓
        "stroke_width": "2.0",
        "opacity": "0.8",
        "label_fill": "#c6282d",
        "label_weight": "600",
        "label_size": "11px",
    },
    "muted": {
        "stroke": "#526070",      # darkened from #cbd5e1 (1.48:1 ✗) → 6.43:1 ✓
        "stroke_width": "1.2",
        "opacity": "0.7",         # R-12: floor raised from 0.30 → 0.7 (WCAG 1.4.11, 3.24:1)
        "label_fill": "#526070",
        "label_weight": "500",
        "label_size": "11px",
    },
    "path": {
        "stroke": "#2563eb",      # unchanged — 5.17:1 ✓ on white
        "stroke_width": "2.5",
        "opacity": "1.0",
        "label_fill": "#2563eb",
        "label_weight": "700",
        "label_size": "12px",
    },
}


def emit_plain_arrow_svg(
    lines: list[str],
    ann: dict[str, Any],
    dst_point: tuple[float, float],
    render_inline_tex: "Callable[[str], str] | None" = None,
    placed_labels: "list[_LabelPlacement] | None" = None,
    _debug_capture: "dict[str, Any] | None" = None,
    primitive_obstacles: "tuple[_Obstacle, ...] | None" = None,
) -> "list[Any]":
    """Emit a short straight pointer arrow for ``arrow=true`` annotations.

    ``arrow=true`` means "draw an arrowhead pointing at the target with no
    source arc".  A short vertical stem originates from
    ``_PLAIN_ARROW_STEM`` pixels above the target cell top edge, and an
    inline arrowhead polygon points downward into the target.

    Parameters
    ----------
    lines:
        Output buffer — SVG markup is appended in-place.
    ann:
        Annotation dict with keys ``target``, optional ``color``, and
        optional ``label``.
    dst_point:
        ``(x, y)`` SVG coordinates of the target cell center (top edge).
    render_inline_tex:
        Optional callback for rendering ``$...$`` math in labels.
    placed_labels:
        Shared mutable list of already-placed label bounding boxes used for
        collision avoidance.  Callers MUST pass the **same** list to every
        ``emit_plain_arrow_svg`` and ``emit_arrow_svg`` call within a single
        frame so that cross-annotation overlap detection works correctly.
        When provided, the final placement is appended to this list.

    Returns
    -------
    list[ObstacleSegment]
        Sampled arrow-stroke segments for use as prior-annotation obstacles
        (R-31 ext).  Callers accumulate these across the annotation loop and
        pass them to subsequent calls via ``primitive_obstacles``.
    """
    color = ann.get("color", "info")
    label_text = ann.get("label", "")
    target = ann.get("target", "")

    x2, y2 = float(dst_point[0]), float(dst_point[1])
    x1, y1 = x2, y2 - _PLAIN_ARROW_STEM

    # Resolve inline style for this color
    style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
    s_stroke = style["stroke"]
    s_width = style["stroke_width"]
    s_opacity = style["opacity"]

    # R-11: build aria-label using speech-friendly form; keep raw TeX for aria-description.
    raw_ann_desc = f"Pointer to {_escape_xml(str(target))}"
    if label_text:
        raw_ann_desc += f": {_escape_xml(label_text)}"
    speech_label_text = _latex_to_speech(label_text) if label_text else ""
    speech_ann_desc = f"Pointer to {_escape_xml(str(target))}"
    if speech_label_text:
        speech_ann_desc += f": {_escape_xml(speech_label_text)}"
    aria_description_attr = ""
    if label_text and _label_has_math(label_text):
        aria_description_attr = f' aria-description="{_escape_xml(label_text)}"'

    # Inline arrowhead polygon pointing straight down into the target.
    arrow_size = 10
    # Direction: straight down (unit vector = (0, 1))
    aux, auy = 0.0, 1.0
    apx, apy = -auy, aux  # perpendicular = (-1, 0)
    hw = arrow_size * 0.5
    ix2, iy2 = int(x2), int(y2)
    p1x, p1y = float(ix2), float(iy2)
    p2x = p1x - aux * arrow_size + apx * hw
    p2y = p1y - auy * arrow_size + apy * hw
    p3x = p1x - aux * arrow_size - apx * hw
    p3y = p1y - auy * arrow_size - apy * hw
    arrow_points = (
        f"{p1x:.1f},{p1y:.1f} {p2x:.1f},{p2y:.1f} {p3x:.1f},{p3y:.1f}"
    )

    ix1, iy1 = int(x1), int(y1)

    # R-13: dash-array for warn/muted on the stem line.
    path_dasharray = ""
    pill_dasharray = ""
    if color == "warn":
        path_dasharray = ' stroke-dasharray="3,2"'
        pill_dasharray = ' stroke-dasharray="3,2"'
    elif color == "muted":
        path_dasharray = ' stroke-dasharray="1,3"'
        pill_dasharray = ' stroke-dasharray="1,3"'

    ann_key = f"{target}-plain-arrow"
    lines.append(
        f'  <g class="scriba-annotation scriba-annotation-{color}"'
        f' data-annotation="{_escape_xml(ann_key)}"'
        f' opacity="{s_opacity}"'
        f' role="graphics-symbol"'
        f' aria-roledescription="annotation"'  # R-14
        f' aria-label="{speech_ann_desc}"'      # R-11: speech form
        f'{aria_description_attr}>'             # R-11: raw TeX in aria-description
    )
    lines.append(
        f'    <line x1="{ix1}" y1="{iy1}" x2="{ix2}" y2="{iy2}"'
        f' stroke="{s_stroke}" stroke-width="{s_width}"{path_dasharray}/>'
    )
    lines.append(
        f'    <polygon points="{arrow_points}" fill="{s_stroke}"/>'
    )

    if label_text:
        l_fill = style["label_fill"]
        l_weight = style["label_weight"]
        l_size = style["label_size"]
        l_font_px = int(l_size.replace("px", "")) if l_size.endswith("px") else _DEFAULT_LABEL_FONT_PX

        # Do not wrap when math is present — would split inside $...$.
        if _label_has_math(label_text):
            label_lines = [label_text]
        else:
            label_lines = _wrap_label_lines(label_text)
        line_height = l_font_px + 2
        num_lines = len(label_lines)

        max_line_w = max(
            estimate_text_width(_label_width_text(ln), l_font_px)
            for ln in label_lines
        )
        pill_w = max_line_w + _LABEL_PILL_PAD_X * 2
        pill_h = num_lines * line_height + _LABEL_PILL_PAD_Y * 2

        # Label sits above the stem start
        natural_x = float(ix1)
        natural_y = float(iy1) - pill_h / 2 - 2
        final_x = natural_x
        final_y = natural_y

        # Populate debug capture dict for testing (zero overhead when None).
        if _debug_capture is not None:
            _debug_capture["final_y"] = final_y
            _debug_capture["l_font_px"] = l_font_px
            _debug_capture["pill_w"] = pill_w
            _debug_capture["pill_h"] = pill_h

        # MW-1: Extract side hint from annotation for half-plane preference.
        anchor_side = ann.get("side") or ann.get("position") or None

        # v0.12.0 W1: Replace boolean overlaps() first-fit with _pick_best_candidate
        # argmin (spec §1.3 commit 4).
        collision_unresolved = False
        if placed_labels is not None:
            # HIGH #2: candidate_y carries the -0.3 centre-correction so the
            # registered geometry matches the rendered pill position.
            candidate_y = final_y - l_font_px * 0.3

            # Entry shim: convert placed labels to obstacle tuple (§1.3).
            # R-31: merge primitive segment obstacles (e.g. Plane2D lines/axes).
            _obstacles: tuple[_Obstacle, ...] = tuple(
                _lp_to_obstacle(p) for p in placed_labels
            ) + (primitive_obstacles if primitive_obstacles is not None else ())

            # Build ScoreContext.  Plain-arrow has no src→dst arc vector.
            _ctx = _ScoreContext(
                natural_x=final_x,
                natural_y=candidate_y,
                pill_w=float(pill_w),
                pill_h=float(pill_h),
                side_hint=anchor_side if anchor_side in ("left", "right", "above", "below") else None,
                arc_direction=(0.0, 0.0),
                color_token=color,
                viewbox_w=float(ix2) * 4 + float(pill_w),   # generous bound; no viewbox param here
                viewbox_h=float(iy2) * 4 + float(pill_h),
            )

            # Build candidate list: natural + 32 nudges (no clamp — emit functions
            # do not have viewbox bounds; use post-scoring clamped_x for registration).
            _nat_candidates: list[tuple[float, float]] = [(final_x, candidate_y)]
            for _ndx, _ndy in _nudge_candidates(float(pill_w), float(pill_h), side_hint=anchor_side):
                _nat_candidates.append((final_x + _ndx, candidate_y + _ndy))
            _cands = tuple(_nat_candidates)

            _best_cx, _best_cy, _best_score = _pick_best_candidate(_cands, _obstacles, _ctx)
            candidate_obj = _LabelPlacement(
                x=_best_cx, y=_best_cy, width=float(pill_w), height=float(pill_h),
            )
            collision_unresolved = (
                _best_score == float("inf") or _best_score > _DEGRADED_SCORE_THRESHOLD
            )

            final_x = candidate_obj.x
            # Reconstruct render y from candidate y (which carries the -0.3 correction).
            final_y = candidate_obj.y + l_font_px * 0.3
            # QW-3: register clamped x so collision avoidance for subsequent
            # labels uses the same coordinate as rendering.
            clamped_x = max(final_x, pill_w / 2)
            # QW-1: register y = candidate_obj.y (= final_y - l_font_px*0.3).
            placed_labels.append(_LabelPlacement(
                x=clamped_x,
                y=candidate_obj.y,
                width=float(pill_w),
                height=float(pill_h),
            ))

        fi_x = int(final_x)
        fi_y = int(final_y)

        # QW-2: emit collision debug comment when all directions were exhausted.
        # HIGH #1: gated behind _DEBUG_LABELS so it never leaks into production.
        if collision_unresolved and _DEBUG_LABELS:
            target_id = ann.get("target", "unknown")
            lines.append(f"  <!-- scriba:label-collision id={target_id} -->")

        # R-19: unconditional stderr warning when placement is degraded.
        if collision_unresolved:
            _target_id = ann.get("target", "unknown")
            _disp = int(math.sqrt((float(fi_x) - natural_x) ** 2 + (float(fi_y) - natural_y) ** 2))
            _log.warning(
                "scriba:label-placement-degraded annotation=%s displacement=%dpx",
                _target_id,
                _disp,
            )

        pill_rx = max(0, int(fi_x - pill_w / 2))
        pill_ry = int(fi_y - pill_h / 2 - l_font_px * 0.3)
        fi_x = max(fi_x, pill_w // 2)
        lines.append(
            f'    <rect x="{pill_rx}" y="{pill_ry}"'
            f' width="{pill_w}" height="{pill_h}"'
            f' rx="{_LABEL_PILL_RADIUS}" ry="{_LABEL_PILL_RADIUS}"'
            f' fill="white" fill-opacity="{_LABEL_BG_OPACITY}"'
            f' stroke="{s_stroke}" stroke-width="0.5" stroke-opacity="0.3"'
            f'{pill_dasharray}/>'  # R-13: mirror dash to pill border
        )

        if num_lines == 1:
            lines.append(
                _emit_label_single_line(
                    label_text=label_text,
                    fi_x=fi_x,
                    fi_y=fi_y,
                    pill_rx=pill_rx,
                    pill_ry=pill_ry,
                    pill_w=int(pill_w),
                    pill_h=int(pill_h),
                    l_fill=l_fill,
                    l_weight=l_weight,
                    l_size=l_size,
                    render_inline_tex=render_inline_tex,
                )
            )
        else:
            text_attrs = (
                f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
                f' stroke="white" stroke-width="3"'
                f' stroke-linejoin="round" paint-order="stroke fill"'
            )
            style_parts = []
            if l_weight:
                style_parts.append(f"font-weight:{l_weight}")
            if l_size:
                style_parts.append(f"font-size:{l_size}")
            style_parts.append("text-anchor:middle")
            style_parts.append("dominant-baseline:auto")
            style_str = ";".join(style_parts)
            tspans = ""
            for li, ln_text in enumerate(label_lines):
                dy_val = f"{line_height}" if li > 0 else "0"
                tspans += (
                    f'<tspan x="{fi_x}" dy="{dy_val}">'
                    f"{_escape_xml(ln_text)}</tspan>"
                )
            lines.append(
                f'    <text {text_attrs} style="{style_str}">{tspans}</text>'
            )

    lines.append("  </g>")

    # R-31 ext: return sampled stem segments for prior-annotation obstacle threading.
    # Straight stem: one segment from stem start to destination point.
    return _sample_arrow_segments(
        (x1, y1, x1, y1, x2, y2, x2, y2),  # control points unused for straight
        state=ann.get("color", "default"),
        is_straight=True,
    )


class ArrowGeometry(NamedTuple):
    """Pure geometry result for ``_compute_control_points``.

    All integer fields are pre-cast for direct SVG coordinate use.
    ``euclid``, ``base_offset``, and ``total_offset`` are kept as floats
    for downstream scoring / headroom math. Phase B will swap the
    control-point formula (port of perfect-arrows bow+stretch) without
    changing this struct.
    """

    src_x: float
    src_y: float
    dst_x: float
    dst_y: float
    cp1_x: int
    cp1_y: int
    cp2_x: int
    cp2_y: int
    euclid: float
    base_offset: float
    total_offset: float
    label_ref_x: int
    label_ref_y: int
    curve_mid_x: int
    curve_mid_y: int


def _compute_control_points(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    dx: float,
    dy: float,
    dist: float,
    arrow_index: int,
    cell_height: float,
    layout: str,
    label_text: str,
    *,
    cell_metrics: CellMetrics | None = None,
) -> ArrowGeometry:
    """Pure geometry: cubic Bézier control points + label anchor.

    Endpoints are post-shortening; ``dx``/``dy``/``dist`` are derived
    from them and passed in to avoid recomputation. No side effects.

    See ``docs/plans/phase-a-v0.12.1-extraction-plan.md`` §3 and
    Phase B notes (v0.12.2): the curve amplitude is a port of
    perfect-arrows' ``bow + modulate(dist, [smin, smax], [1, 0]) * stretch``.
    The cubic control points are derived from the single quadratic control
    point via the standard quad→cubic identity
    ``cp1 = P0 + 2/3*(Q - P0); cp2 = P1 + 2/3*(Q - P1)``.

    Phase D (v0.14.0): ``cell_metrics`` presence is the sentinel for
    grid-aware flow context. When provided and ``layout == "2d"``,
    odd-indexed stacked arrows flip the perpendicular direction so dense
    stacks distribute symmetrically instead of forming a one-sided fan.
    """
    euclid = math.hypot(x2 - x1, y2 - y1)

    # Perfect-arrows bow+stretch arc amplitude (scalar, unitless).
    _bow_factor = _modulate(
        euclid, (_ARROW_STRETCH_MIN, _ARROW_STRETCH_MAX), (1.0, 0.0)
    )
    arc = _ARROW_BOW + _bow_factor * _ARROW_STRETCH

    # Perpendicular offset from midpoint to quadratic control point.
    # Floor against cell_height so short arrows stay visibly bowed.
    base_offset = max(arc * euclid, cell_height * _ARROW_PERP_FLOOR_FACTOR)
    stagger = cell_height * _ARROW_STAGGER_FACTOR
    total_offset = base_offset + min(arrow_index, _ARROW_STAGGER_CAP) * stagger

    # Phase D stagger-flip: odd-indexed 2D stacks bow to opposite side.
    # Gate on cell_metrics presence — its non-None value is the grid-aware
    # context sentinel that authorises the flip.
    _perp_flip = (
        cell_metrics is not None and layout == "2d" and (arrow_index % 2 == 1)
    )

    if layout == "2d":
        # Perpendicular to the connecting line (rotated 90° toward +perp).
        perp_x = -dy / dist if dist else 0.0
        perp_y = dx / dist if dist else 0.0
        if _perp_flip:
            perp_x = -perp_x
            perp_y = -perp_y

        mid_x_f = (x1 + x2) / 2
        mid_y_f = (y1 + y2) / 2

        # Quadratic control point = midpoint pushed along the perpendicular.
        qx = mid_x_f + perp_x * total_offset
        qy = mid_y_f + perp_y * total_offset

        # Quadratic → cubic conversion.
        cx1 = int(x1 + 2.0 / 3.0 * (qx - x1))
        cy1 = int(y1 + 2.0 / 3.0 * (qy - y1))
        cx2 = int(x2 + 2.0 / 3.0 * (qx - x2))
        cy2 = int(y2 + 2.0 / 3.0 * (qy - y2))

        label_ref_x = int(qx + perp_x * 8)
        label_ref_y = int(qy + perp_y * 8)
    else:
        # Horizontal layout: curve upward (negative y).
        mid_x_f = (x1 + x2) / 2
        mid_y_f = (y1 + y2) / 2

        # R-01: estimate pill_h early so the natural anchor clears the arc.
        _est_l_font_px = _DEFAULT_LABEL_FONT_PX
        _est_pill_h = (_est_l_font_px + 2) + _LABEL_PILL_PAD_Y * 2  # 19 px typical

        h_span = abs(x2 - x1)
        if h_span < _ARROW_VERT_ALIGN_H_SPAN:
            # Near-vertical / self-loop: bow up-and-sideways so the arc is
            # visible even when src and dst share the same column (or point).
            h_nudge = total_offset * _ARROW_VERT_H_NUDGE_FACTOR
            qx = mid_x_f - h_nudge
            qy = min(y1, y2) - total_offset

            cx1 = max(0, int(x1 + 2.0 / 3.0 * (qx - x1)))
            cy1 = int(y1 + 2.0 / 3.0 * (qy - y1))
            cx2 = max(0, int(x2 + 2.0 / 3.0 * (qx - x2)))
            cy2 = int(y2 + 2.0 / 3.0 * (qy - y2))

            _est_pill_hw = (
                estimate_text_width(label_text, _DEFAULT_LABEL_FONT_PX) // 2 + _LABEL_PILL_PAD_X
                if label_text else 20
            )
            raw_lx = int(qx - 8)
            label_ref_x = max(raw_lx, _est_pill_hw)
            label_ref_y = int(qy) - _est_pill_h // 2 - 4  # R-01: arc clearance
        else:
            # Standard horizontal bow upward.
            qx = mid_x_f
            qy = min(y1, y2) - total_offset

            cx1 = int(x1 + 2.0 / 3.0 * (qx - x1))
            cy1 = int(y1 + 2.0 / 3.0 * (qy - y1))
            cx2 = int(x2 + 2.0 / 3.0 * (qx - x2))
            cy2 = int(y2 + 2.0 / 3.0 * (qy - y2))

            label_ref_x = int(mid_x_f)
            # Peak of the cubic at t=0.5 for cp1.y = cp2.y = qy:
            # B(0.5).y = 0.125*y1 + 0.375*qy + 0.375*qy + 0.125*y2
            #         = 0.25*(y1+y2)/2 ... but we use qy directly for clearance.
            label_ref_y = int(qy) - _est_pill_h // 2 - 4  # R-01: arc clearance

    # Curve midpoint B(0.5) for leader anchoring — evaluated from the actual
    # control points so the anchor dot sits ON the rendered curve.
    curve_mid_x = int(0.125 * x1 + 0.375 * cx1 + 0.375 * cx2 + 0.125 * x2)
    curve_mid_y = int(0.125 * y1 + 0.375 * cy1 + 0.375 * cy2 + 0.125 * y2)

    return ArrowGeometry(
        src_x=x1, src_y=y1,
        dst_x=x2, dst_y=y2,
        cp1_x=cx1, cp1_y=cy1,
        cp2_x=cx2, cp2_y=cy2,
        euclid=euclid,
        base_offset=base_offset,
        total_offset=total_offset,
        label_ref_x=label_ref_x,
        label_ref_y=label_ref_y,
        curve_mid_x=curve_mid_x,
        curve_mid_y=curve_mid_y,
    )


def _emit_label_and_pill(
    lines: list[str],
    label_text: str,
    style: dict[str, Any],
    geom: ArrowGeometry,
    ix1: int,
    iy1: int,
    ix2: int,
    iy2: int,
    dx: float,
    dy: float,
    dist: float,
    color: str,
    s_stroke: str,
    pill_dasharray_emit: str,
    ann: dict[str, Any],
    render_inline_tex: "Callable[[str], str] | None",
    placed_labels: "list[_LabelPlacement] | None",
    primitive_obstacles: "tuple[_Obstacle, ...] | None",
    _debug_capture: "dict[str, Any] | None",
    *,
    cell_metrics: "CellMetrics | None" = None,
) -> None:
    """Emit pill background, leader line (when needed), and label text.

    Mutates ``lines`` in place (append), and when provided also mutates
    ``placed_labels`` (append final placement) and ``_debug_capture``
    (populate final_y / l_font_px / pill_w / pill_h keys).

    Extracted from ``emit_arrow_svg`` in Phase A/3. Zero behavior change.
    See ``docs/plans/phase-a-v0.12.1-extraction-plan.md`` §4.
    """
    l_fill = style["label_fill"]
    l_weight = style["label_weight"]
    l_size = style["label_size"]
    l_font_px = int(l_size.replace("px", "")) if l_size.endswith("px") else _DEFAULT_LABEL_FONT_PX

    # Multi-line wrap (skip when math is present — would split inside $...$).
    if _label_has_math(label_text):
        label_lines = [label_text]
    else:
        label_lines = _wrap_label_lines(label_text)
    line_height = l_font_px + 2
    num_lines = len(label_lines)

    # Measure pill dimensions (strip $ delimiters for math labels)
    max_line_w = max(
        estimate_text_width(_label_width_text(ln), l_font_px)
        for ln in label_lines
    )
    pill_w = max_line_w + _LABEL_PILL_PAD_X * 2
    pill_h = num_lines * line_height + _LABEL_PILL_PAD_Y * 2

    # Natural label position
    natural_x = float(geom.label_ref_x)
    natural_y = float(geom.label_ref_y)
    final_x = natural_x
    final_y = natural_y

    # Populate debug capture dict for testing (zero overhead when None).
    if _debug_capture is not None:
        _debug_capture["final_y"] = final_y
        _debug_capture["l_font_px"] = l_font_px
        _debug_capture["pill_w"] = pill_w
        _debug_capture["pill_h"] = pill_h

    # MW-1: Extract explicit side hint from annotation for half-plane preference.
    # R-22: auto-infer side_hint from arrow vector when no explicit hint given.
    anchor_side = ann.get("side") or ann.get("position") or None
    if anchor_side is None:
        # Infer from the (dx, dy) vector between src and dst (post-shortening).
        _abs_dx = abs(dx)
        _abs_dy = abs(dy)
        # HIGH-3: zero-vector guard — src == dst produces abs_dx == abs_dy == 0.
        # No directional hint can be inferred; leave anchor_side as None so the
        # 32-candidate symmetric search handles placement without a half-plane bias.
        if _abs_dx == 0 and _abs_dy == 0:
            anchor_side = None  # degenerate: no hint, use symmetric search
        elif _abs_dx >= _abs_dy:
            # Horizontal-ish arc: prefer ABOVE (cog P-DIR-1).
            anchor_side = "above"
        else:
            # Vertical-ish arc: prefer RIGHT.
            anchor_side = "right"

    # v0.12.0 W1: Replace boolean overlaps() first-fit with _pick_best_candidate
    # argmin (spec §1.3 commit 4).
    collision_unresolved = False
    if placed_labels is not None:
        # HIGH #2: candidate_y carries the -0.3 centre-correction so the
        # registered geometry matches the rendered pill position.
        candidate_y = final_y - l_font_px * 0.3

        # Entry shim: convert placed labels to obstacle tuple (§1.3).
        # R-31: merge primitive segment obstacles (e.g. Plane2D lines/axes).
        _obstacles: tuple[_Obstacle, ...] = tuple(
            _lp_to_obstacle(p) for p in placed_labels
        ) + (primitive_obstacles if primitive_obstacles is not None else ())

        # Arc direction unit vector for P6 (reading_flow) term.
        _arc_dist = dist  # already computed as sqrt(dx²+dy²) above; ≥1.0
        _arc_dir: tuple[float, float] = (dx / _arc_dist, dy / _arc_dist)

        # Phase D/4 (v0.14.0): classify grid-aware flow when cell_metrics
        # is available.  Non-None value enables the P7 annotation_arrow
        # scale-down (× 0.75) in _score_candidate.
        _flow_hint = (
            classify_flow(dx, dy, cell_metrics)
            if cell_metrics is not None else None
        )

        _ctx = _ScoreContext(
            natural_x=final_x,
            natural_y=candidate_y,
            pill_w=float(pill_w),
            pill_h=float(pill_h),
            side_hint=anchor_side if anchor_side in ("left", "right", "above", "below") else None,
            arc_direction=_arc_dir,
            color_token=color,
            viewbox_w=max(float(ix2), float(ix1)) * 4 + float(pill_w),
            viewbox_h=max(float(iy2), float(iy1)) * 4 + float(pill_h),
            flow=_flow_hint,
        )

        # Build candidate list: natural + 32 nudges.
        _ea_candidates: list[tuple[float, float]] = [(final_x, candidate_y)]
        for _ndx, _ndy in _nudge_candidates(float(pill_w), float(pill_h), side_hint=anchor_side):
            _ea_candidates.append((final_x + _ndx, candidate_y + _ndy))
        _cands = tuple(_ea_candidates)

        _best_cx, _best_cy, _best_score = _pick_best_candidate(_cands, _obstacles, _ctx)
        candidate_obj = _LabelPlacement(
            x=_best_cx, y=_best_cy, width=float(pill_w), height=float(pill_h),
        )
        collision_unresolved = (
            _best_score == float("inf") or _best_score > _DEGRADED_SCORE_THRESHOLD
        )

        final_x = candidate_obj.x
        # Reconstruct render y from candidate y (which carries the -0.3 correction).
        final_y = candidate_obj.y + l_font_px * 0.3
        # QW-3: register clamped x so subsequent labels check the right coord.
        clamped_x = max(final_x, pill_w / 2)
        # QW-1: register y = candidate_obj.y (= final_y - l_font_px*0.3).
        placed_labels.append(_LabelPlacement(
            x=clamped_x,
            y=candidate_obj.y,
            width=float(pill_w),
            height=float(pill_h),
        ))

    fi_x = int(final_x)
    fi_y = int(final_y)

    # QW-2: emit collision debug comment when all directions were exhausted.
    # HIGH #1: gated behind _DEBUG_LABELS so it never leaks into production.
    if collision_unresolved and _DEBUG_LABELS:
        target_id = ann.get("target", "unknown")
        lines.append(f"  <!-- scriba:label-collision id={target_id} -->")

    # R-19: unconditional stderr warning when placement is degraded.
    if collision_unresolved:
        _target_id = ann.get("target", "unknown")
        _disp = int(math.sqrt((float(fi_x) - natural_x) ** 2 + (float(fi_y) - natural_y) ** 2))
        _log.warning(
            "scriba:label-placement-degraded annotation=%s displacement=%dpx",
            _target_id,
            _disp,
        )

    # Background pill: white rect with rounded corners, before text
    # Clamp so pill doesn't extend outside the viewBox (x/y >= 0).
    pill_rx = max(0, int(fi_x - pill_w / 2))
    pill_ry = int(fi_y - pill_h / 2 - l_font_px * 0.3)
    # If pill was clamped, shift label text to stay centered in pill
    fi_x = max(fi_x, pill_w // 2)
    lines.append(
        f'    <rect x="{pill_rx}" y="{pill_ry}"'
        f' width="{pill_w}" height="{pill_h}"'
        f' rx="{_LABEL_PILL_RADIUS}" ry="{_LABEL_PILL_RADIUS}"'
        f' fill="white" fill-opacity="{_LABEL_BG_OPACITY}"'
        f' stroke="{s_stroke}" stroke-width="0.5" stroke-opacity="0.3"'
        f'{pill_dasharray_emit}/>'  # R-13: mirror dash to pill border
    )

    # Leader line: v0.15.0 visual-gap gate.
    # Pill centre derived from the rendered <rect>, NOT from fi_x which was
    # mutated on line 2228 for the left-edge clamp. For a clamped pill
    # fi_x != pill_rx + pill_w/2 — only the rect origin is reliable.
    _pill_cx = float(pill_rx) + float(pill_w) / 2.0
    _pill_cy = float(pill_ry) + float(pill_h) / 2.0
    # v0.15.0 visual-gap gate: distance from the rendered pill centre to the
    # curve-mid anchor on the arrow, minus the natural arc-clearance baseline.
    # Fires for every colour once the pill is clearly offset from the curve —
    # replaces R-27 (colour-gate) + R-27b (algorithmic far-gate).
    _visual_gap = math.hypot(
        float(geom.curve_mid_x) - _pill_cx,
        float(geom.curve_mid_y) - _pill_cy,
    )
    _natural_gap = float(pill_h) / 2.0 + _LEADER_ARC_CLEARANCE_PX
    if _visual_gap >= _natural_gap + float(pill_h) * _LEADER_GAP_FACTOR:
        # R-08: leader endpoint at pill perimeter, not pill centre.
        _leader_ep = _line_rect_intersection(
            float(geom.curve_mid_x), float(geom.curve_mid_y),
            _pill_cx, _pill_cy,
            float(pill_w), float(pill_h),
        )
        # HIGH-1: skip leader when origin is inside the pill (None return).
        if _leader_ep is not None:
            _leader_ep_x, _leader_ep_y = _leader_ep
            leader_dasharray = ' stroke-dasharray="3,2"' if color == "warn" else ""
            lines.append(
                f'    <circle cx="{geom.curve_mid_x}" cy="{geom.curve_mid_y}" r="2"'
                f' fill="{s_stroke}" opacity="0.6"/>'
            )
            lines.append(
                f'    <polyline points="{geom.curve_mid_x},{geom.curve_mid_y}'
                f' {_leader_ep_x},{_leader_ep_y}"'
                f' fill="none" stroke="{s_stroke}"'
                f' stroke-width="0.75"{leader_dasharray}'
                f' opacity="0.6"/>'
            )

    # Render label text with paint-order halo (single-line dispatches
    # to KaTeX foreignObject when math is present).
    if num_lines == 1:
        lines.append(
            _emit_label_single_line(
                label_text=label_text,
                fi_x=fi_x,
                fi_y=fi_y,
                pill_rx=pill_rx,
                pill_ry=pill_ry,
                pill_w=int(pill_w),
                pill_h=int(pill_h),
                l_fill=l_fill,
                l_weight=l_weight,
                l_size=l_size,
                render_inline_tex=render_inline_tex,
            )
        )
    else:
        # Multi-line — use tspan elements
        text_attrs = (
            f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
            f' stroke="white" stroke-width="3"'
            f' stroke-linejoin="round" paint-order="stroke fill"'
        )
        style_parts = []
        if l_weight:
            style_parts.append(f"font-weight:{l_weight}")
        if l_size:
            style_parts.append(f"font-size:{l_size}")
        style_parts.append("text-anchor:middle")
        style_parts.append("dominant-baseline:auto")
        style_str = ";".join(style_parts)
        tspans = ""
        for li, ln_text in enumerate(label_lines):
            dy_val = f'{line_height}' if li > 0 else "0"
            tspans += (
                f'<tspan x="{fi_x}" dy="{dy_val}">'
                f'{_escape_xml(ln_text)}</tspan>'
            )
        lines.append(
            f'    <text {text_attrs} style="{style_str}">{tspans}</text>'
        )


def emit_arrow_svg(
    lines: list[str],
    ann: dict[str, Any],
    src_point: tuple[float, float],
    dst_point: tuple[float, float],
    arrow_index: int,
    cell_height: float,
    render_inline_tex: "Callable[[str], str] | None" = None,
    *,
    layout: str = "horizontal",
    shorten_src: float = 0.0,
    shorten_dst: float = 0.0,
    placed_labels: "list[_LabelPlacement] | None" = None,
    _debug_capture: "dict[str, Any] | None" = None,
    primitive_obstacles: "tuple[_Obstacle, ...] | None" = None,
    cell_metrics: "CellMetrics | None" = None,
) -> "list[Any]":
    """Emit a cubic Bezier arrow annotation into *lines*.

    This is the shared arrow rendering used by Array, DPTable, and any
    future primitive that supports annotation arrows.  Each primitive is
    responsible for resolving selectors to SVG coordinates (via its own
    ``_cell_center`` / ``resolve_annotation_point``) and passing the
    results here.

    Parameters
    ----------
    lines:
        Output buffer -- SVG markup is appended in-place.
    ann:
        Annotation dict with keys ``target``, ``arrow_from``, and
        optional ``color`` and ``label``.
    src_point:
        ``(x, y)`` SVG coordinates of the arrow source.
    dst_point:
        ``(x, y)`` SVG coordinates of the arrow destination.
    arrow_index:
        Stagger index for multiple arrows targeting the same cell.
    cell_height:
        Cell height used for curve offset calculation.
    render_inline_tex:
        Optional callback for rendering ``$...$`` math in labels.
    layout:
        ``"horizontal"`` (default) curves upward for Array/DPTable etc.
        ``"2d"`` curves perpendicular to the source-destination line,
        suitable for Graph, Tree, Grid, and Plane2D.
    shorten_src:
        Pull the path start point toward the destination by this many
        pixels.  Useful for circular nodes so the arrow starts at the
        circle edge rather than the center.
    shorten_dst:
        Pull the path end point toward the source by this many pixels.
        Useful for circular nodes so the arrowhead stops at the circle
        edge rather than piercing into the node.
    placed_labels:
        Shared mutable list of already-placed label bounding boxes used for
        collision avoidance.  Callers MUST pass the **same** list to every
        ``emit_plain_arrow_svg`` and ``emit_arrow_svg`` call within a single
        frame so that cross-annotation overlap detection works correctly.
        When provided, the final placement is appended to this list.

    Returns
    -------
    list[ObstacleSegment]
        Sampled arrow-stroke segments for use as prior-annotation obstacles
        (R-31 ext).  Callers accumulate these across the annotation loop and
        pass them to subsequent calls via ``primitive_obstacles``.
    """
    color = ann.get("color", "info")
    label_text = ann.get("label", "")
    target = ann.get("target", "")
    arrow_from = ann.get("arrow_from", "")

    x1, y1 = float(src_point[0]), float(src_point[1])
    x2, y2 = float(dst_point[0]), float(dst_point[1])

    # Shorten endpoints toward each other (for circle-edge arrows)
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy) or 1.0

    if shorten_src > 0 and dist > 0:
        x1 = x1 + (dx / dist) * shorten_src
        y1 = y1 + (dy / dist) * shorten_src
    if shorten_dst > 0 and dist > 0:
        x2 = x2 - (dx / dist) * shorten_dst
        y2 = y2 - (dy / dist) * shorten_dst

    # Recompute after shortening
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy) or 1.0

    # Phase A/2: geometry extracted to _compute_control_points.
    # Returns ArrowGeometry NamedTuple; locals below are unpacked for the
    # existing SVG emit code. Phase B will swap the control-point formula
    # (port of perfect-arrows bow+stretch) inside the helper with zero
    # churn here.
    # Phase D (v0.14.0): cell_metrics presence alone gates stagger-flip;
    # the helper no longer accepts a pre-classified flow kwarg.
    _geom = _compute_control_points(
        x1, y1, x2, y2, dx, dy, dist,
        arrow_index, cell_height, layout, label_text,
        cell_metrics=cell_metrics,
    )
    cx1, cy1 = _geom.cp1_x, _geom.cp1_y
    cx2, cy2 = _geom.cp2_x, _geom.cp2_y
    label_ref_x, label_ref_y = _geom.label_ref_x, _geom.label_ref_y
    curve_mid_x, curve_mid_y = _geom.curve_mid_x, _geom.curve_mid_y

    ix1, iy1 = int(x1), int(y1)
    ix2, iy2 = int(x2), int(y2)

    # Resolve inline style for this color
    style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
    s_stroke = style["stroke"]
    s_width = style["stroke_width"]
    s_opacity = style["opacity"]

    # R-11: build speech-friendly aria-label; keep raw TeX in aria-description.
    _speech_label = _latex_to_speech(label_text) if label_text else ""
    speech_ann_desc = (
        f"Arrow from {_escape_xml(str(arrow_from))} "
        f"to {_escape_xml(str(target))}"
    )
    if _speech_label:
        speech_ann_desc += f": {_escape_xml(_speech_label)}"
    ann_aria_description_attr = ""
    if label_text and _label_has_math(label_text):
        ann_aria_description_attr = f' aria-description="{_escape_xml(label_text)}"'

    # Keep raw desc for use in path <title> (no need to speechify title).
    raw_ann_desc = (
        f"Arrow from {_escape_xml(str(arrow_from))} "
        f"to {_escape_xml(str(target))}"
    )
    if label_text:
        raw_ann_desc += f": {_escape_xml(label_text)}"

    # Compute inline arrowhead polygon at the path endpoint.
    # This replaces SVG <marker> defs which have cross-browser issues
    # (Safari file://, innerHTML replacement, etc.).
    arrow_size = 10
    # Direction vector at the curve tip: approximate via last control
    # point → endpoint.
    adx = float(ix2 - cx2)
    ady = float(iy2 - cy2)
    ad = math.sqrt(adx * adx + ady * ady) or 1.0
    aux, auy = adx / ad, ady / ad       # unit vector toward tip
    apx, apy = -auy, aux                 # perpendicular
    hw = arrow_size * 0.5
    # Three vertices: tip, and two base corners
    p1x, p1y = ix2, iy2
    p2x = p1x - aux * arrow_size + apx * hw
    p2y = p1y - auy * arrow_size + apy * hw
    p3x = p1x - aux * arrow_size - apx * hw
    p3y = p1y - auy * arrow_size - apy * hw
    arrow_points = (
        f"{p1x:.1f},{p1y:.1f} {p2x:.1f},{p2y:.1f} {p3x:.1f},{p3y:.1f}"
    )

    # R-13: dash-array for warn/muted on arrow path and pill border.
    path_dasharray = ""
    pill_dasharray_emit = ""
    if color == "warn":
        path_dasharray = ' stroke-dasharray="3,2"'
        pill_dasharray_emit = ' stroke-dasharray="3,2"'
    elif color == "muted":
        path_dasharray = ' stroke-dasharray="1,3"'
        pill_dasharray_emit = ' stroke-dasharray="1,3"'

    ann_key = f"{target}-{arrow_from}" if arrow_from else f"{target}-solo"
    lines.append(
        f'  <g class="scriba-annotation scriba-annotation-{color}"'
        f' data-annotation="{_escape_xml(ann_key)}"'
        f' opacity="{s_opacity}"'
        f' role="graphics-symbol"'
        f' aria-roledescription="annotation"'       # R-14
        f' aria-label="{speech_ann_desc}"'           # R-11: speech form
        f'{ann_aria_description_attr}>'              # R-11: raw TeX in aria-description
    )
    lines.append(
        f'    <path d="M{ix1},{iy1} C{cx1},{cy1} {cx2},{cy2} {ix2},{iy2}" '
        f'stroke="{s_stroke}" stroke-width="{s_width}" fill="none"{path_dasharray}>'  # R-13
        f'<title>{raw_ann_desc}</title>'
        f'</path>'
    )
    lines.append(
        f'    <polygon points="{arrow_points}" fill="{s_stroke}"/>'
    )
    if label_text:
        # Phase A/3: pill + leader + label text extracted to _emit_label_and_pill.
        _emit_label_and_pill(
            lines=lines,
            label_text=label_text,
            style=style,
            geom=_geom,
            ix1=ix1, iy1=iy1, ix2=ix2, iy2=iy2,
            dx=dx, dy=dy, dist=dist,
            color=color,
            s_stroke=s_stroke,
            pill_dasharray_emit=pill_dasharray_emit,
            ann=ann,
            render_inline_tex=render_inline_tex,
            placed_labels=placed_labels,
            primitive_obstacles=primitive_obstacles,
            _debug_capture=_debug_capture,
            cell_metrics=cell_metrics,
        )

    lines.append("  </g>")

    # R-31 ext: return sampled arc segments for prior-annotation obstacle threading.
    # Bezier: sample N=8 points → 7 segments covering the arc stroke geometry.
    return _sample_arrow_segments(
        (float(ix1), float(iy1), float(cx1), float(cy1),
         float(cx2), float(cy2), float(ix2), float(iy2)),
        state=ann.get("color", "default"),
        is_straight=False,
    )


def arrow_height_above(
    annotations: list[dict[str, Any]],
    cell_center_resolver: "Callable[[str], tuple[float, float] | None]",
    cell_height: float = CELL_HEIGHT,
    layout: str = "horizontal",
) -> int:
    """Compute the max vertical extent above y=0 that arrows need.

    Parameters
    ----------
    annotations:
        Full list of annotations for the primitive.
    cell_center_resolver:
        Callable that maps a selector string (e.g. ``"arr.cell[3]"``)
        to ``(x, y)`` SVG coordinates, or ``None`` if unresolvable.
    cell_height:
        Cell height used for curve offset calculation.
    layout:
        ``"horizontal"`` (default) assumes upward-curving arrows.
        ``"2d"`` computes based on perpendicular offset from the
        source-destination line.
    """
    if not annotations:
        return 0
    # Include both arc-style (arrow_from) and pointer-style (arrow=True) annotations
    arrow_anns = [a for a in annotations if a.get("arrow_from")]
    plain_anns = [a for a in annotations if a.get("arrow") and not a.get("arrow_from")]
    if not arrow_anns and not plain_anns:
        return 0

    # Plain arrow=true annotations need a fixed height above the target for the
    # short pointer stem (stem length + label headroom).
    plain_height = 0
    if plain_anns:
        plain_height = _PLAIN_ARROW_STEM + (
            _LABEL_HEADROOM if any(a.get("label") for a in plain_anns) else 0
        )

    if not arrow_anns:
        return plain_height

    has_label = any(a.get("label") for a in arrow_anns)
    max_height = 0
    for idx, ann in enumerate(arrow_anns):
        src = cell_center_resolver(ann.get("arrow_from", ""))
        dst = cell_center_resolver(ann.get("target", ""))
        if src is None or dst is None:
            continue
        x1, y1 = src
        x2, y2 = dst
        # Count arrows targeting same cell before this one
        target = ann.get("target", "")
        arrow_index = sum(
            1
            for j, a in enumerate(arrow_anns)
            if a.get("target") == target
            and j < idx
        )
        # NOTE: uses Manhattan distance (h_dist) as a deliberately conservative
        # upper bound for headroom estimation. Do NOT unify with the Euclidean
        # formula in emit_arrow_svg without re-verifying all headroom callers.
        # Also: no stagger cap here (pre-v0.12.0 behavior preserved intentionally).
        h_dist = abs(x2 - x1) + abs(y2 - y1)
        base_offset = min(
            cell_height * _ARROW_CAP_FLOOR_FACTOR,
            max(cell_height * _ARROW_BASE_FLOOR_FACTOR, math.sqrt(h_dist) * _ARROW_SQRT_SCALE),
        )
        stagger = cell_height * _ARROW_STAGGER_FACTOR
        total_offset = base_offset + arrow_index * stagger

        if layout == "2d":
            # For 2D layouts the curve bows perpendicular to the line
            # between source and destination.  The vertical component
            # above the topmost endpoint depends on the perpendicular
            # direction.
            dx = x2 - x1
            dy = y2 - y1
            dist = math.sqrt(dx * dx + dy * dy) or 1.0
            perp_y = dx / dist  # perpendicular y-component
            # The control points sit at roughly mid_y + perp_y * offset.
            # The worst-case vertical extent above the topmost point is
            # how far above min(y1, y2) the curve can reach.
            mid_y = (y1 + y2) / 2
            ctrl_y = mid_y + perp_y * total_offset
            extent_above = max(0, min(y1, y2) - ctrl_y)
            max_height = max(max_height, int(extent_above))
        else:
            # Horizontal: the curve peaks at min(y1, y2) - total_offset
            max_height = max(max_height, int(total_offset))

    if has_label:
        # QW-7: use 32 px headroom when any arrow label contains math
        # (fractions, large operators overflow the 24 px default).
        has_math = any(_label_has_math(a.get("label", "")) for a in arrow_anns)
        headroom_extra = 32 if has_math else _LABEL_HEADROOM
        max_height += headroom_extra

    return max(max_height, plain_height)


def _position_only_anns(annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to annotations that go through emit_position_label_svg.

    These are annotations with a ``label`` and (optionally) a ``position`` key
    but with neither ``arrow_from`` nor ``arrow=true``.
    """
    return [
        a for a in annotations
        if a.get("label")
        and not a.get("arrow_from")
        and not a.get("arrow")
    ]


def position_label_height_above(
    annotations: list[dict[str, Any]],
    *,
    l_font_px: int = 11,
    cell_height: float = CELL_HEIGHT,
) -> int:
    """Compute the max vertical headroom needed above y=0 for position=above labels.

    Parameters
    ----------
    annotations:
        Full annotation list for the primitive (any entries without
        ``arrow_from`` / ``arrow=true`` that have a ``label`` are considered).
    l_font_px:
        Label font size in pixels used to compute pill height.
    cell_height:
        Cell height used to match the offset calculation in
        ``emit_position_label_svg``.

    Returns
    -------
    int
        Pixel headroom required above the cell top-edge (y=0) to fit all
        ``position=above`` pill labels, or 0 when there are none.
    """
    pos_anns = [
        a for a in _position_only_anns(annotations)
        if a.get("position", "above") == "above"
    ]
    if not pos_anns:
        return 0

    line_height = l_font_px + 2
    pill_h_base = line_height + _LABEL_PILL_PAD_Y * 2  # single-line pill height
    gap = max(4.0, cell_height * 0.1)

    # The label center sits at:
    #   final_y = ay - cell_height/2 - pill_h/2 - gap
    # where ay = 0 (cell center-y for the top row, which is the closest to y=0).
    # The topmost pixel of the pill rect is at:
    #   pill_ry = final_y - pill_h/2 - l_font_px*0.3
    # Headroom = max(0, -pill_ry) so the translate shifts content down enough.
    has_math = any(_label_has_math(a.get("label", "")) for a in pos_anns)
    headroom_extra = 32 if has_math else _LABEL_HEADROOM

    # Worst-case pill_h is pill_h_base (single line); multi-line makes it taller
    # but also pushes its center further — here we use pill_h_base as the
    # conservative minimum (taller pills need more room, but we match the
    # same conservative estimate used for arrow_height_above).
    pill_h = pill_h_base
    final_y = -cell_height / 2 - pill_h / 2 - gap
    pill_ry = final_y - pill_h / 2 - l_font_px * 0.3
    # headroom = how much above y=0 the pill extends, plus label readability buffer
    raw_headroom = int(math.ceil(-pill_ry)) + headroom_extra
    return max(0, raw_headroom)


def position_label_height_below(
    annotations: list[dict[str, Any]],
    *,
    l_font_px: int = 11,
    cell_height: float = CELL_HEIGHT,
) -> int:
    """Compute extra height needed BELOW the cell bottom for position=below labels.

    Parameters
    ----------
    annotations:
        Full annotation list for the primitive.
    l_font_px:
        Label font size in pixels.
    cell_height:
        Cell height used to match offset calculation in
        ``emit_position_label_svg``.

    Returns
    -------
    int
        Extra pixels needed below the nominal cell bottom, or 0 when none.
    """
    pos_anns = [
        a for a in _position_only_anns(annotations)
        if a.get("position") == "below"
    ]
    if not pos_anns:
        return 0

    line_height = l_font_px + 2
    pill_h = line_height + _LABEL_PILL_PAD_Y * 2
    gap = max(4.0, cell_height * 0.1)

    # AC-6: mirror the math-headroom branch from position_label_height_above.
    # When any below-label contains $…$, add 8 px extra (32 − 24 delta).
    has_math = any(_label_has_math(a.get("label", "")) for a in pos_anns)
    math_extra = 8 if has_math else 0  # _LABEL_MATH_HEADROOM_EXTRA

    # final_y for below = ay + cell_height/2 + pill_h/2 + gap
    # pill bottom = final_y + pill_h/2 + l_font_px*0.3
    # extra = pill_bottom - cell_height
    pill_bottom = cell_height / 2 + pill_h + gap + l_font_px * 0.3 + math_extra
    return max(0, int(math.ceil(pill_bottom - cell_height)))


def _place_pill(
    *,
    natural_x: float,
    natural_y: float,
    pill_w: float,
    pill_h: float,
    placed_labels: "list[_LabelPlacement]",
    viewbox_w: float,
    viewbox_h: float,
    side_hint: "str | None" = None,
    overlap_pad: float = 0.0,
    _debug_capture: "dict[str, Any] | None" = None,
) -> "tuple[_LabelPlacement, bool]":
    """Place a pill label using weighted scoring argmin (v0.12.0 W1).

    Replaces the boolean overlaps() first-fit loops with
    ``_pick_best_candidate`` argmin selection (spec §1.3 commit 3).
    Sole placement primitive for MW-3.  Closes ISSUE-A3 (clamp-race) by
    clamping each candidate to the viewport *before* scoring, so a candidate
    that would shift after clamping is evaluated at its actual rendered position.

    Parameters
    ----------
    natural_x, natural_y:
        Natural pill center (cx, cy) before any nudge.  The caller is
        responsible for supplying the geometry-rule-derived center
        (e.g. arc mid-point, stem tip, or position-offset anchor).
    pill_w, pill_h:
        Pill dimensions in SVG user units.  MUST be > 0.
    placed_labels:
        Registry of already-placed pills in this frame.  The returned
        placement is NOT appended — the caller does that to maintain C-3
        (append-only registry).
    viewbox_w, viewbox_h:
        Declared viewBox dimensions for clamping (G-3).
    side_hint:
        Half-plane preference passed to ``_nudge_candidates`` (C-5) and
        encoded in ``_ScoreContext`` for P3 (side-hint violation) term.
    overlap_pad:
        Retained for API compatibility; not used by the scoring path.
    _debug_capture:
        When provided, receives diagnostic keys ``natural_x``,
        ``natural_y``, ``final_x``, ``final_y``, ``collision_unresolved``,
        ``candidates_tried``.  Enabled by ``SCRIBA_DEBUG_LABELS=1``.

    Returns
    -------
    tuple[_LabelPlacement, bool]
        ``(placement, fits_cleanly)`` where *fits_cleanly* is ``True``
        when the best candidate has a finite score (no hard-block violation).
        When all candidates are hard-blocked, the least-bad candidate is
        returned with ``fits_cleanly=False`` (E-1 / R-17 fallback).
    """
    half_w = pill_w / 2.0
    half_h = pill_h / 2.0

    def _clamp(cx: float, cy: float) -> tuple[float, float]:
        """Translate center so the AABB stays within [0, viewbox_w] × [0, viewbox_h]."""
        cx = max(half_w, min(cx, viewbox_w - half_w))
        cy = max(half_h, min(cy, viewbox_h - half_h))
        return cx, cy

    # Build obstacles tuple from the placed-label registry (entry shim, §1.3).
    obstacles: tuple[_Obstacle, ...] = tuple(
        _lp_to_obstacle(p) for p in placed_labels
    )

    # Build scoring context.  W1 callers don't supply arc_direction or
    # color_token, so we use neutral defaults (P6=0, P4=constant).
    ctx = _ScoreContext(
        natural_x=natural_x,
        natural_y=natural_y,
        pill_w=pill_w,
        pill_h=pill_h,
        side_hint=side_hint if side_hint in ("left", "right", "above", "below") else None,
        arc_direction=(0.0, 0.0),   # no arc info available at this call site
        color_token="info",         # neutral P4 constant across all candidates
        viewbox_w=viewbox_w,
        viewbox_h=viewbox_h,
    )

    # Build candidate list: natural (clamped) + 32 nudges (clamped).
    # Clamp BEFORE scoring so the score reflects the actual rendered position.
    nat_cx, nat_cy = _clamp(natural_x, natural_y)
    all_candidates: list[tuple[float, float]] = [(nat_cx, nat_cy)]
    for ndx, ndy in _nudge_candidates(pill_w, pill_h, side_hint=side_hint):
        cx, cy = _clamp(natural_x + ndx, natural_y + ndy)
        all_candidates.append((cx, cy))
    candidates_tuple = tuple(all_candidates)

    # Score all candidates and pick the best.
    best_cx, best_cy, best_score = _pick_best_candidate(candidates_tuple, obstacles, ctx)

    fits_cleanly = best_score != float("inf")
    placement = _LabelPlacement(x=best_cx, y=best_cy, width=pill_w, height=pill_h)

    if _debug_capture is not None:
        _debug_capture.update({
            "natural_x": natural_x,
            "natural_y": natural_y,
            "final_x": best_cx,
            "final_y": best_cy,
            "collision_unresolved": not fits_cleanly,
            "candidates_tried": len(candidates_tuple),
        })

    return placement, fits_cleanly


def emit_position_label_svg(
    lines: list[str],
    ann: dict[str, Any],
    anchor_point: tuple[float, float],
    cell_height: float = CELL_HEIGHT,
    render_inline_tex: "Callable[[str], str] | None" = None,
    placed_labels: "list[_LabelPlacement] | None" = None,
    primitive_obstacles: "tuple[_Obstacle, ...] | None" = None,
) -> None:
    """Emit a pill-only label for position-only annotations (no arrow, no arc).

    Called when an annotation has a ``label`` and a ``position`` key but
    neither ``arrow_from`` nor ``arrow=true``.  Emits just the rounded pill
    rectangle and the label text, offset from *anchor_point* according to
    *position* (``"above"``, ``"below"``, ``"left"``, ``"right"``).

    Parameters
    ----------
    lines:
        Output buffer — SVG markup is appended in-place.
    ann:
        Annotation dict.  Keys ``label``, ``color``, ``position``,
        ``target`` are consulted.
    anchor_point:
        ``(x, y)`` SVG coordinates of the annotated cell center.
    cell_height:
        Cell height used to compute the vertical offset from the anchor.
    render_inline_tex:
        Optional callback for rendering ``$...$`` math in labels.
    placed_labels:
        Shared mutable list of already-placed label bounding boxes.
        Callers MUST pass the **same** list to every label-emitting call
        within a single frame so that cross-annotation overlap detection
        works correctly.
    primitive_obstacles:
        Optional tuple of ``_Obstacle`` entries (W3-α+) representing
        cross-primitive segments (e.g. Plane2D lines) that pills MUST or
        SHOULD avoid.  When provided, ``_place_pill`` is used instead of
        the simple nudge loop so that MUST-severity segments are treated
        as hard blocks.
    """
    label_text = ann.get("label", "")
    if not label_text:
        return

    color = ann.get("color", "info")
    target = ann.get("target", "")
    position = ann.get("position", "above")

    style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
    s_stroke = style["stroke"]
    s_opacity = style["opacity"]
    l_fill = style["label_fill"]
    l_weight = style["label_weight"]
    l_size = style["label_size"]
    l_font_px = int(l_size.replace("px", "")) if l_size.endswith("px") else _DEFAULT_LABEL_FONT_PX

    if _label_has_math(label_text):
        label_lines = [label_text]
    else:
        label_lines = _wrap_label_lines(label_text)
    line_height = l_font_px + 2
    num_lines = len(label_lines)

    max_line_w = max(
        estimate_text_width(_label_width_text(ln), l_font_px)
        for ln in label_lines
    )
    pill_w = max_line_w + _LABEL_PILL_PAD_X * 2
    pill_h = num_lines * line_height + _LABEL_PILL_PAD_Y * 2

    ax, ay = float(anchor_point[0]), float(anchor_point[1])
    gap = max(4.0, cell_height * 0.1)

    if position == "above":
        final_x = ax
        final_y = ay - cell_height / 2 - pill_h / 2 - gap
    elif position == "below":
        final_x = ax
        final_y = ay + cell_height / 2 + pill_h / 2 + gap
    elif position == "left":
        final_x = ax - pill_w / 2 - gap
        final_y = ay
    elif position == "right":
        final_x = ax + pill_w / 2 + gap
        final_y = ay
    else:
        # Default: above
        final_x = ax
        final_y = ay - cell_height / 2 - pill_h / 2 - gap

    if placed_labels is not None:
        if primitive_obstacles:
            # W3-α+: use _place_pill so MUST-severity segment obstacles (e.g.
            # cross-primitive Plane2D lines) are treated as hard blocks.
            # Merge placed-label AABBs with segment obstacles into one tuple.
            all_obs: tuple[_Obstacle, ...] = tuple(
                _lp_to_obstacle(p) for p in placed_labels
            ) + primitive_obstacles
            # Use a very large viewbox so clamping does not interfere; the
            # caller's viewbox is not available here, so use a safe sentinel.
            _vb = 8192.0
            placement, _fits = _place_pill(
                natural_x=final_x,
                natural_y=final_y - l_font_px * 0.3,
                pill_w=float(pill_w),
                pill_h=float(pill_h),
                placed_labels=[],  # already baked into all_obs above
                viewbox_w=_vb,
                viewbox_h=_vb,
                side_hint=position if position in ("above", "below", "left", "right") else None,
            )
            # _place_pill returns placement at candidate_y (already -0.3 corrected)
            final_x = placement.x
            final_y = placement.y + l_font_px * 0.3
            clamped_x = max(final_x, pill_w / 2)
            placed_labels.append(_LabelPlacement(
                x=clamped_x,
                y=placement.y,
                width=float(pill_w),
                height=float(pill_h),
            ))
        else:
            # Legacy simple-nudge loop (no segment obstacles present).
            # HIGH #2: initial candidate uses center-corrected y so overlap
            # geometry during nudge matches the registered placement geometry.
            candidate_y = final_y - l_font_px * 0.3
            candidate = _LabelPlacement(
                x=final_x, y=candidate_y, width=float(pill_w), height=float(pill_h),
            )
            nudge_step = pill_h + 2
            nudge_dirs = [
                (0, -nudge_step),
                (-nudge_step, 0),
                (nudge_step, 0),
                (0, nudge_step),
            ]
            collision_unresolved = False
            for _ in range(4):
                if not any(candidate.overlaps(p) for p in placed_labels):
                    break
                resolved = False
                for ndx, ndy in nudge_dirs:
                    test = _LabelPlacement(
                        x=candidate.x + ndx,
                        y=candidate.y + ndy,
                        width=candidate.width,
                        height=candidate.height,
                    )
                    if not any(test.overlaps(p) for p in placed_labels):
                        candidate = test
                        resolved = True
                        break
                if not resolved:
                    collision_unresolved = True
                    break
            final_x = candidate.x
            # Reconstruct render y from candidate y (which carries the -0.3 correction).
            final_y = candidate.y + l_font_px * 0.3
            clamped_x = max(final_x, pill_w / 2)
            # QW-1: register y = candidate.y (already = final_y - l_font_px*0.3).
            placed_labels.append(_LabelPlacement(
                x=clamped_x,
                y=candidate.y,
                width=float(pill_w),
                height=float(pill_h),
            ))
            # HIGH #1: gated behind _DEBUG_LABELS so it never leaks into production.
            if collision_unresolved and _DEBUG_LABELS:
                lines.append(f"  <!-- scriba:label-collision id={target} -->")

    fi_x = int(final_x)
    fi_y = int(final_y)

    pill_rx = max(0, int(fi_x - pill_w / 2))
    pill_ry = int(fi_y - pill_h / 2 - l_font_px * 0.3)
    fi_x = max(fi_x, pill_w // 2)

    # R-11: speech form for aria-label; raw TeX in aria-description when math.
    speech_pos_label = _latex_to_speech(label_text)
    pos_aria_description_attr = ""
    if _label_has_math(label_text):
        pos_aria_description_attr = f' aria-description="{_escape_xml(label_text)}"'

    # R-13: dash-array for warn/muted colors on pill border.
    pos_pill_dasharray = ""
    if color == "warn":
        pos_pill_dasharray = ' stroke-dasharray="3,2"'
    elif color == "muted":
        pos_pill_dasharray = ' stroke-dasharray="1,3"'

    ann_key = f"{target}-position-{position}"
    lines.append(
        f'  <g class="scriba-annotation scriba-annotation-{color}"'
        f' data-annotation="{_escape_xml(ann_key)}"'
        f' opacity="{s_opacity}"'
        f' role="graphics-symbol"'
        f' aria-roledescription="annotation"'                      # R-14
        f' aria-label="{_escape_xml(speech_pos_label)}"'           # R-11: speech form
        f'{pos_aria_description_attr}>'                            # R-11: raw TeX
    )
    lines.append(
        f'    <rect x="{pill_rx}" y="{pill_ry}"'
        f' width="{pill_w}" height="{pill_h}"'
        f' rx="{_LABEL_PILL_RADIUS}" ry="{_LABEL_PILL_RADIUS}"'
        f' fill="white" fill-opacity="{_LABEL_BG_OPACITY}"'
        f' stroke="{s_stroke}" stroke-width="0.5" stroke-opacity="0.3"'
        f'{pos_pill_dasharray}/>'  # R-13: dash on pill border
    )
    if num_lines == 1:
        lines.append(
            _emit_label_single_line(
                label_text=label_text,
                fi_x=fi_x,
                fi_y=fi_y,
                pill_rx=pill_rx,
                pill_ry=pill_ry,
                pill_w=int(pill_w),
                pill_h=int(pill_h),
                l_fill=l_fill,
                l_weight=l_weight,
                l_size=l_size,
                render_inline_tex=render_inline_tex,
            )
        )
    else:
        text_attrs = (
            f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
            f' stroke="white" stroke-width="3"'
            f' stroke-linejoin="round" paint-order="stroke fill"'
        )
        style_parts: list[str] = []
        if l_weight:
            style_parts.append(f"font-weight:{l_weight}")
        if l_size:
            style_parts.append(f"font-size:{l_size}")
        style_parts.append("text-anchor:middle")
        style_parts.append("dominant-baseline:auto")
        style_str = ";".join(style_parts)
        tspans = ""
        for li, ln_text in enumerate(label_lines):
            dy_val = f"{line_height}" if li > 0 else "0"
            tspans += (
                f'<tspan x="{fi_x}" dy="{dy_val}">'
                f"{_escape_xml(ln_text)}</tspan>"
            )
        lines.append(
            f'    <text {text_attrs} style="{style_str}">{tspans}</text>'
        )
    lines.append("  </g>")


def emit_arrow_marker_defs(
    lines: list[str],
    annotations: list[dict[str, Any]],
) -> None:
    """Emit ``<defs>`` with ``<marker>`` elements for arrow colors.

    Only emits markers for colors actually used in *annotations*.
    Does nothing when no arrow annotations are present.

    Parameters
    ----------
    lines:
        Output buffer -- SVG markup is appended in-place.
    annotations:
        Full list of annotations; only those with ``arrow_from`` are
        considered.
    """
    # Arrowheads are now rendered as inline <polygon> elements inside
    # each annotation group by emit_arrow_svg().  No <marker> <defs>
    # needed.  This function is kept as a no-op for call-site compat.
    pass
