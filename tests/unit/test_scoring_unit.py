"""Unit tests for smart-label scoring infrastructure (v0.12.0 W1).

Commit 1: shim round-trip tests.
Commit 2: per-term hand-computed scoring tests (§5.1 table).

Test IDs correspond directly to the spec table in
docs/plans/smart-label-scoring-impl-2026-04-22.md §5.1.
"""

from __future__ import annotations

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
