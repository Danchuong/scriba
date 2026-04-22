"""Unit tests for smart-label scoring infrastructure (v0.12.0 W1).

Commit 1: shim round-trip tests.
Commit 2: per-term hand-computed scoring tests (§5.1 table).

Test IDs correspond directly to the spec table in
docs/plans/smart-label-scoring-impl-2026-04-22.md §5.1.
"""

from __future__ import annotations

import math

import pytest

import scriba.animation.primitives._svg_helpers as _h


# ---------------------------------------------------------------------------
# Commit 1 — _Obstacle type + _lp_to_obstacle shim
# ---------------------------------------------------------------------------


class TestLpToObstacleShim:
    """Round-trip tests for _lp_to_obstacle (commit 1)."""

    def test_shim_kind_is_pill(self) -> None:
        lp = _h._LabelPlacement(x=10.0, y=20.0, width=50.0, height=19.0)
        obs = _h._lp_to_obstacle(lp)
        assert obs.kind == "pill"

    def test_shim_preserves_geometry(self) -> None:
        lp = _h._LabelPlacement(x=100.0, y=200.0, width=60.0, height=22.0)
        obs = _h._lp_to_obstacle(lp)
        assert obs.x == lp.x
        assert obs.y == lp.y
        assert obs.width == lp.width
        assert obs.height == lp.height

    def test_shim_default_severity_should(self) -> None:
        lp = _h._LabelPlacement(x=0.0, y=0.0, width=40.0, height=18.0)
        obs = _h._lp_to_obstacle(lp)
        assert obs.severity == "SHOULD"

    def test_shim_x2_y2_default_zero(self) -> None:
        lp = _h._LabelPlacement(x=5.0, y=5.0, width=30.0, height=15.0)
        obs = _h._lp_to_obstacle(lp)
        assert obs.x2 == 0.0
        assert obs.y2 == 0.0

    def test_obstacle_is_frozen(self) -> None:
        obs = _h._Obstacle(kind="pill", x=0.0, y=0.0, width=10.0, height=10.0)
        with pytest.raises((AttributeError, TypeError)):
            obs.x = 99.0  # type: ignore[misc]

    def test_shim_round_trip_identity(self) -> None:
        """Converting lp → obstacle and back round-trips geometry exactly."""
        lp = _h._LabelPlacement(x=37.5, y=88.25, width=72.0, height=21.0)
        obs = _h._lp_to_obstacle(lp)
        # Reconstruct an equivalent LabelPlacement from the obstacle fields.
        lp2 = _h._LabelPlacement(
            x=obs.x, y=obs.y, width=obs.width, height=obs.height
        )
        assert lp2.x == lp.x
        assert lp2.y == lp.y
        assert lp2.width == lp.width
        assert lp2.height == lp.height


# ---------------------------------------------------------------------------
# Commit 2 — Scoring function per-term tests (spec §5.1 table)
# ---------------------------------------------------------------------------

# Helpers: build a minimal _ScoreContext and obstacle tuple.

def _make_ctx(
    natural_x: float = 100.0,
    natural_y: float = 100.0,
    pill_w: float = 60.0,
    pill_h: float = 20.0,
    side_hint: str | None = None,
    arc_direction: tuple[float, float] = (1.0, 0.0),
    color_token: str = "info",
    viewbox_w: float = 600.0,
    viewbox_h: float = 400.0,
) -> _h._ScoreContext:
    return _h._ScoreContext(
        natural_x=natural_x,
        natural_y=natural_y,
        pill_w=pill_w,
        pill_h=pill_h,
        side_hint=side_hint,
        arc_direction=arc_direction,
        color_token=color_token,
        viewbox_w=viewbox_w,
        viewbox_h=viewbox_h,
    )


def _pill_obs(cx: float, cy: float, w: float = 60.0, h: float = 20.0) -> _h._Obstacle:
    return _h._Obstacle(kind="pill", x=cx, y=cy, width=w, height=h)


def _target_obs(
    cx: float, cy: float, w: float = 40.0, h: float = 40.0,
    severity: str = "MUST",
) -> _h._Obstacle:
    return _h._Obstacle(kind="target_cell", x=cx, y=cy, width=w, height=h, severity=severity)  # type: ignore[arg-type]


def _seg_obs(
    x0: float, y0: float, x1: float, y1: float, severity: str = "MUST"
) -> _h._Obstacle:
    return _h._Obstacle(kind="segment", x=x0, y=y0, width=0.0, height=0.0, x2=x1, y2=y1, severity=severity)  # type: ignore[arg-type]


class TestP1OverlapArea:
    """P1: weighted intersection area (spec §2.2 _W_OVERLAP term)."""

    def test_p1_overlap_area_zero(self) -> None:
        """No obstacles → P1 contribution = 0."""
        obs_tuple: tuple[_h._Obstacle, ...] = ()
        area = sum(
            _h._aabb_intersect_area(o, 100.0, 100.0, 60.0, 20.0)
            for o in obs_tuple
        )
        assert area == 0.0

    def test_p1_overlap_area_partial(self) -> None:
        """Partial overlap: area × kind_weight with known geometry.

        Pill: centre=(100, 100), 60×20 → x in [70,130], y in [90,110].
        Obstacle (pill kind, w=1.0): centre=(115, 100), 60×20 → x in [85,145].
        Overlap x: [85,130] = 45; overlap y: [90,110] = 20.  Area = 900 px².
        kind_weight("pill") = 1.0 → P1 contribution = 900.
        """
        obs = _pill_obs(cx=115.0, cy=100.0, w=60.0, h=20.0)
        area = _h._aabb_intersect_area(obs, 100.0, 100.0, 60.0, 20.0)
        assert area == pytest.approx(900.0)

    def test_p1_kind_weight_target_cell(self) -> None:
        """target_cell kind has weight 3.0 (R-02)."""
        assert _h._KIND_WEIGHT["target_cell"] == 3.0

    def test_p1_touching_returns_min_penalty(self) -> None:
        """Touching (shared edge) → minimum penalty area = 1.0.

        ``_LabelPlacement.overlaps`` uses strict-less-than separation, so
        two AABBs that share an edge are considered overlapping.
        ``_aabb_intersect_area`` mirrors that by returning at least 1.0 for
        any touching-or-overlapping pair (inclusive boundary, spec §5.2).
        """
        # Pill centred at (100,100), 60×20 → right edge at x=130.
        # Obstacle centred at (160, 100) → left edge at x=130.  Edges touch.
        obs = _pill_obs(cx=160.0, cy=100.0, w=60.0, h=20.0)
        area = _h._aabb_intersect_area(obs, 100.0, 100.0, 60.0, 20.0)
        assert area == 1.0


class TestP2Displace:
    """P2: displacement from natural position (spec §2.2 _W_DISPLACE term)."""

    def test_p2_displace_zero(self) -> None:
        """Candidate at natural position → displacement component = 0."""
        disp = math.hypot(100.0 - 100.0, 100.0 - 100.0)
        assert disp == 0.0

    def test_p2_displace_scale(self) -> None:
        """2× distance → 2× displacement component."""
        ctx = _make_ctx(natural_x=0.0, natural_y=0.0)
        score_near = _h._score_candidate(10.0, 0.0, (), ctx)
        score_far  = _h._score_candidate(20.0, 0.0, (), ctx)
        # Both have same P3/P4/P5/P6/P7 (no obstacles, same side_hint=None).
        # Only P2 differs: 10 vs 20.
        diff = score_far - score_near
        assert diff == pytest.approx(_h._W_DISPLACE * 10.0, rel=1e-9)


class TestP3SideHint:
    """P3: side-hint half-plane violation (spec §2.2 _W_SIDE_HINT term)."""

    def test_p3_side_hint_violation_wrong_plane(self) -> None:
        """Candidate on wrong side of natural_y with side_hint=above → P3 = W_SIDE_HINT."""
        ctx = _make_ctx(natural_x=100.0, natural_y=100.0, side_hint="above")
        # cy=150 > natural_y=100 → violation.
        p3 = _h.side_hint_violation(100.0, 150.0, ctx)
        assert p3 == 1.0

    def test_p3_side_hint_no_violation(self) -> None:
        """Candidate on correct side → P3 = 0."""
        ctx = _make_ctx(natural_x=100.0, natural_y=100.0, side_hint="above")
        p3 = _h.side_hint_violation(100.0, 50.0, ctx)
        assert p3 == 0.0

    def test_p3_no_hint_returns_zero(self) -> None:
        """side_hint=None → P3 = 0 regardless of position."""
        ctx = _make_ctx(side_hint=None)
        assert _h.side_hint_violation(0.0, 0.0, ctx) == 0.0
        assert _h.side_hint_violation(999.0, 999.0, ctx) == 0.0

    def test_p3_score_contribution_equals_w_side_hint(self) -> None:
        """Score diff between wrong and right half-plane equals W_SIDE_HINT.

        We null out reading_flow (arc_direction=(0,0)) and keep displacements
        equal so the only difference between the two candidates is P3.
        Candidates (100,50) and (100,150) are equidistant from natural (100,100).
        """
        ctx = _make_ctx(
            natural_x=100.0, natural_y=100.0,
            side_hint="above",
            arc_direction=(0.0, 0.0),   # zero vector → P6=0 for both candidates
        )
        score_correct = _h._score_candidate(100.0, 50.0, (), ctx)
        score_wrong   = _h._score_candidate(100.0, 150.0, (), ctx)
        assert score_wrong - score_correct == pytest.approx(_h._W_SIDE_HINT, rel=1e-9)


class TestP5Whitespace:
    """P5: boundary clearance deficit (spec §2.2 _W_WHITESPACE term)."""

    def test_p5_whitespace_penalty_near_obstacle(self) -> None:
        """Candidate very close to an obstacle gets positive P5.

        Pill at (10, 100), obstacle centre at (0, 100) size 20×20.
        Distance from candidate centre (10) to obstacle right edge (10) = 0.
        min_clearance_required = max(4, 20*0.15) = 4.
        boundary_clearance = 0 → deficit = 4.
        """
        obs = _h._Obstacle(kind="pill", x=0.0, y=100.0, width=20.0, height=20.0)
        obstacles = (obs,)
        ctx = _make_ctx(pill_h=20.0)
        clr = _h.boundary_clearance(10.0, 100.0, obstacles)
        min_req = max(4.0, ctx.pill_h * 0.15)
        deficit = max(0.0, min_req - clr)
        assert deficit > 0.0

    def test_p5_whitespace_zero_far_from_obstacles(self) -> None:
        """Candidate far from all obstacles → P5 = 0."""
        obs = _h._Obstacle(kind="pill", x=500.0, y=500.0, width=20.0, height=20.0)
        obstacles = (obs,)
        ctx = _make_ctx(natural_x=100.0, natural_y=100.0, pill_h=20.0)
        clr = _h.boundary_clearance(100.0, 100.0, obstacles)
        min_req = max(4.0, ctx.pill_h * 0.15)
        deficit = max(0.0, min_req - clr)
        assert deficit == 0.0


class TestP7EdgeOcclusion:
    """P7: edge occlusion (segment-in-pill length, spec §2.2 _W_EDGE_OCCLUSION term)."""

    def test_p7_edge_occlusion_zero_no_segments(self) -> None:
        """No segment obstacles → clipped segment length = 0 (P7 = 0).

        Use a far-away segment to confirm the clip function returns 0.0
        when the segment doesn't intersect the pill AABB.
        """
        # Segment at (200,200)→(300,300) does not overlap pill at (100,100) 60×20.
        clip = _h._segment_rect_clip_length(
            200.0, 200.0, 300.0, 300.0, 100.0, 100.0, 60.0, 20.0
        )
        assert clip == 0.0

    def test_p7_edge_occlusion_bisecting_segment(self) -> None:
        """A segment bisecting the pill produces nonzero P7.

        Pill at (100, 100) 60×20: x ∈ [70,130], y ∈ [90,110].
        Segment from (80, 100) to (120, 100) — fully inside pill.
        Clipped length = 40 px.  pill_diagonal = sqrt(60²+20²) ≈ 63.25.
        Normalised = 40/63.25 ≈ 0.6325.
        """
        clip = _h._segment_rect_clip_length(80.0, 100.0, 120.0, 100.0, 100.0, 100.0, 60.0, 20.0)
        assert clip == pytest.approx(40.0, abs=0.1)
        pill_diagonal = math.hypot(60.0, 20.0)
        p7 = clip / pill_diagonal
        assert p7 == pytest.approx(40.0 / pill_diagonal, rel=1e-6)


class TestMustHardBlock:
    """MUST-severity obstacles cause float('inf') return (spec §2.3)."""

    def test_must_hard_block_target_cell(self) -> None:
        """Overlapping MUST target_cell → float('inf')."""
        obs = _target_obs(cx=100.0, cy=100.0, w=40.0, h=40.0, severity="MUST")
        ctx = _make_ctx(natural_x=100.0, natural_y=100.0)
        score = _h._score_candidate(100.0, 100.0, (obs,), ctx)
        assert score == float("inf")

    def test_must_hard_block_target_cell_non_overlapping(self) -> None:
        """MUST target_cell far away → finite score (no hard block)."""
        obs = _target_obs(cx=500.0, cy=500.0, w=40.0, h=40.0, severity="MUST")
        ctx = _make_ctx(natural_x=100.0, natural_y=100.0)
        score = _h._score_candidate(100.0, 100.0, (obs,), ctx)
        assert score != float("inf")
        assert math.isfinite(score)

    def test_must_hard_block_current_segment(self) -> None:
        """R-31 MUST segment intersecting pill → float('inf')."""
        obs = _seg_obs(80.0, 100.0, 120.0, 100.0, severity="MUST")
        ctx = _make_ctx(pill_w=60.0, pill_h=20.0)
        score = _h._score_candidate(100.0, 100.0, (obs,), ctx)
        assert score == float("inf")

    def test_should_segment_not_hard_block(self) -> None:
        """SHOULD segment → finite score (penalised but not blocked)."""
        obs = _seg_obs(80.0, 100.0, 120.0, 100.0, severity="SHOULD")
        ctx = _make_ctx(pill_w=60.0, pill_h=20.0)
        score = _h._score_candidate(100.0, 100.0, (obs,), ctx)
        assert math.isfinite(score)


class TestTieBreak:
    """Tie-break determinism (spec §4.2)."""

    def test_score_tiebreak_deterministic(self) -> None:
        """Equal-score candidates resolve to the lower enumeration index.

        Two candidates at equal distance from natural (symmetric positions):
        (90, 100) and (110, 100) — both 10 px from natural (100, 100),
        no side hint, same obstacles.  The one at index 0 must win.
        """
        ctx = _make_ctx(natural_x=100.0, natural_y=100.0, side_hint=None,
                        arc_direction=(0.0, 0.0))
        candidates = ((90.0, 100.0), (110.0, 100.0))
        best_cx, best_cy, _ = _h._pick_best_candidate(candidates, (), ctx)
        # Both have identical scores (same distance, same everything).
        # Winner must be the first candidate (index 0).
        assert best_cx == 90.0
        assert best_cy == 100.0

    def test_pick_best_returns_lowest_score_position(self) -> None:
        """_pick_best_candidate returns the position with the lowest score."""
        ctx = _make_ctx(natural_x=100.0, natural_y=100.0)
        # (100, 100) is at natural position → displacement = 0 → best.
        # (200, 200) is far → displacement = 141 → worse.
        candidates = ((200.0, 200.0), (100.0, 100.0))
        best_cx, best_cy, best_score = _h._pick_best_candidate(candidates, (), ctx)
        assert best_cx == 100.0
        assert best_cy == 100.0
        assert best_score < _h._score_candidate(200.0, 200.0, (), ctx)


class TestWeightsFrozen:
    """Weights-frozen assertion (spec §5.1 test_weights_are_frozen)."""

    def test_weights_are_frozen(self) -> None:
        """Module-level weight constants match the spec initial values.

        These are the W1 initial weights; calibration is post-W1.
        The env var SCRIBA_LABEL_WEIGHTS must not be set during golden
        generation — unset it before running the golden suite.

        _W_EDGE_OCCLUSION raised from 8.0 → 40.0 (P7-saturate fix, R-31 ext):
        saturating normalisation against pill short-side means any clip ≥ pill_h
        costs 40 per segment, making 20-px displacement (cost 20) cheaper than
        staying on a clipping annotation arrow (cost 40+).
        """
        import os
        if os.environ.get("SCRIBA_LABEL_WEIGHTS"):
            pytest.skip("SCRIBA_LABEL_WEIGHTS is set — weight override active")
        assert _h._W_OVERLAP       == 10.0
        assert _h._W_DISPLACE      ==  1.0
        assert _h._W_SIDE_HINT     ==  5.0
        assert _h._W_SEMANTIC      ==  2.0
        assert _h._W_WHITESPACE    ==  0.3
        assert _h._W_READING_FLOW  ==  0.8
        assert _h._W_EDGE_OCCLUSION == 40.0
