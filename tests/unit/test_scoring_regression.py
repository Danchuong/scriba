"""Score distribution snapshot tests for v0.12.0 W1 (spec §5.3).

These tests catch silent weight regressions faster than full golden re-pin.
Each snapshot records: min_score (exact), winner_index (exact), max_score
(±5 % drift allowed per spec §5.3).

Snapshots computed with initial W1 weights:
  _W_OVERLAP=10, _W_DISPLACE=1, _W_SIDE_HINT=5, _W_SEMANTIC=2,
  _W_WHITESPACE=0.3, _W_READING_FLOW=0.8, _W_EDGE_OCCLUSION=8

Scenes:
  "no-collision"   — single label, no placed obstacles; wins at natural pos (index 0).
  "one-collision"  — second label placed at natural pos; scorer must nudge away.
"""

from __future__ import annotations

import math

import pytest

import scriba.animation.primitives._svg_helpers as _h


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_scene(
    nat_x: float,
    nat_y: float,
    pill_w: float,
    pill_h: float,
    placed_labels: list[_h._LabelPlacement],
    viewbox_w: float = 200.0,
    viewbox_h: float = 100.0,
    side_hint: str | None = None,
    color_token: str = "info",
) -> tuple[tuple[tuple[float, float], ...], tuple[_h._Obstacle, ...], _h._ScoreContext]:
    """Build candidates, obstacles, and context for a _place_pill-equivalent scene."""
    half_w = pill_w / 2.0
    half_h = pill_h / 2.0

    def _clamp(cx: float, cy: float) -> tuple[float, float]:
        cx = max(half_w, min(cx, viewbox_w - half_w))
        cy = max(half_h, min(cy, viewbox_h - half_h))
        return cx, cy

    candidates: list[tuple[float, float]] = [_clamp(nat_x, nat_y)]
    for ndx, ndy in _h._nudge_candidates(pill_w, pill_h, side_hint=side_hint):
        candidates.append(_clamp(nat_x + ndx, nat_y + ndy))

    obstacles = tuple(_h._lp_to_obstacle(p) for p in placed_labels)

    ctx = _h._ScoreContext(
        natural_x=nat_x,
        natural_y=nat_y,
        pill_w=pill_w,
        pill_h=pill_h,
        side_hint=side_hint if side_hint in ("left", "right", "above", "below") else None,
        arc_direction=(0.0, 0.0),
        color_token=color_token,
        viewbox_w=viewbox_w,
        viewbox_h=viewbox_h,
    )

    return tuple(candidates), obstacles, ctx


def _score_scene(
    candidates: tuple[tuple[float, float], ...],
    obstacles: tuple[_h._Obstacle, ...],
    ctx: _h._ScoreContext,
) -> dict[str, object]:
    """Return score distribution dict for a scene."""
    scores = [
        _h._score_candidate(cx, cy, obstacles, ctx) for cx, cy in candidates
    ]
    finite_scores = [s for s in scores if s != float("inf")]
    min_score = min(scores)
    max_score = max(finite_scores) if finite_scores else float("inf")
    winner_index = min(range(len(scores)), key=lambda i: (scores[i], i))
    return {
        "min_score": min_score,
        "max_score": max_score,
        "winner_index": winner_index,
    }


# ---------------------------------------------------------------------------
# Snapshot table (spec §5.3)
# min_score and winner_index: exact match
# max_score: ±5 % drift allowed
# ---------------------------------------------------------------------------

SCORE_SNAPSHOTS: dict[str, dict[str, object]] = {
    # Single label above cell centre; no placed labels; natural position wins.
    "no-collision": {
        "min_score": 1.2,          # W_SEMANTIC*(1-2/5) = 2*0.6 = 1.2; P2=0, P3=0, P5=0, P6=0, P7=0
        "max_score": 41.5,         # approximate; ±5% tolerance applied in assertion
        "winner_index": 0,         # natural position (index 0) is best
    },
    # Two labels at the same natural position; second must be nudged away.
    "one-collision": {
        "min_score": 20.2,         # best non-overlapping candidate score
        "max_score": 7601.2,       # worst (fully overlapping); ±5% tolerance
        "winner_index": 14,        # first nudge direction that clears the obstacle
    },
}


class TestScoreDistributionSnapshots:
    """Verify score distribution snapshots match initial W1 weights (spec §5.3)."""

    @pytest.fixture(autouse=True)
    def _skip_if_weights_overridden(self) -> None:
        import os
        if os.environ.get("SCRIBA_LABEL_WEIGHTS"):
            pytest.skip("SCRIBA_LABEL_WEIGHTS override active — snapshot comparison invalid")

    def test_no_collision_snapshot(self) -> None:
        """Single label; no obstacles; winner at natural position (index 0)."""
        pill_w, pill_h = 40.0, 19.0
        candidates, obstacles, ctx = _build_scene(
            nat_x=100.0, nat_y=18.0,
            pill_w=pill_w, pill_h=pill_h,
            placed_labels=[],
        )
        actual = _score_scene(candidates, obstacles, ctx)
        snap = SCORE_SNAPSHOTS["no-collision"]

        assert actual["winner_index"] == snap["winner_index"], (
            f"winner_index changed: expected {snap['winner_index']}, got {actual['winner_index']}"
        )
        assert actual["min_score"] == pytest.approx(snap["min_score"], rel=1e-9), (
            f"min_score changed: expected {snap['min_score']}, got {actual['min_score']}"
        )
        assert actual["max_score"] == pytest.approx(snap["max_score"], rel=0.05), (
            f"max_score drifted >5%%: expected ~{snap['max_score']}, got {actual['max_score']}"
        )

    def test_one_collision_snapshot(self) -> None:
        """Two labels at same natural position; second nudged by scorer."""
        pill_w, pill_h = 40.0, 19.0
        existing = _h._LabelPlacement(x=100.0, y=18.0, width=pill_w, height=pill_h)
        candidates, obstacles, ctx = _build_scene(
            nat_x=100.0, nat_y=18.0,
            pill_w=pill_w, pill_h=pill_h,
            placed_labels=[existing],
        )
        actual = _score_scene(candidates, obstacles, ctx)
        snap = SCORE_SNAPSHOTS["one-collision"]

        assert actual["winner_index"] == snap["winner_index"], (
            f"winner_index changed: expected {snap['winner_index']}, got {actual['winner_index']}"
        )
        assert actual["min_score"] == pytest.approx(snap["min_score"], rel=0.01), (
            f"min_score changed: expected {snap['min_score']}, got {actual['min_score']}"
        )
        assert actual["max_score"] == pytest.approx(snap["max_score"], rel=0.05), (
            f"max_score drifted >5%%: expected ~{snap['max_score']}, got {actual['max_score']}"
        )

    def test_winner_is_finite_when_obstacle_is_should(self) -> None:
        """SHOULD obstacle → winner has finite score even when directly overlapping."""
        pill_w, pill_h = 40.0, 19.0
        # Place an obstacle right at natural position.
        existing = _h._LabelPlacement(x=100.0, y=18.0, width=pill_w, height=pill_h)
        candidates, obstacles, ctx = _build_scene(
            nat_x=100.0, nat_y=18.0,
            pill_w=pill_w, pill_h=pill_h,
            placed_labels=[existing],
        )
        _, _, best_score = _h._pick_best_candidate(candidates, obstacles, ctx)
        assert math.isfinite(best_score), "SHOULD obstacle must not produce inf best_score"

    def test_score_monotone_with_displacement(self) -> None:
        """All else equal, score increases with displacement (P2 term verification)."""
        pill_w, pill_h = 40.0, 19.0
        candidates, obstacles, ctx = _build_scene(
            nat_x=100.0, nat_y=18.0,
            pill_w=pill_w, pill_h=pill_h,
            placed_labels=[],
        )
        # Natural position (index 0) should have the lowest displacement cost.
        nat_cx, nat_cy = candidates[0]
        score_nat = _h._score_candidate(nat_cx, nat_cy, obstacles, ctx)
        score_far = _h._score_candidate(nat_cx + 50.0, nat_cy, obstacles, ctx)
        assert score_far > score_nat, "Farther candidate must score worse than natural position"
