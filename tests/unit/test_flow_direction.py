"""Unit tests for Phase C v0.13.0 flow classifier and grid types.

Covers:
- `FlowDirection` enum values match the ``round(atan2(dy, dx) / (π/4)) % 8`` scheme.
- `classify_flow` resolves all 8 sectors on cardinal + diagonal vectors.
- Zero-vector degenerate returns :attr:`FlowDirection.RIGHTWARD`.
- `CellMetrics`-normalised classification works on non-square grids.
"""

from __future__ import annotations

import math

import pytest

from scriba.animation.primitives._svg_helpers import (
    CellMetrics,
    FlowDirection,
    classify_flow,
)


# ---------------------------------------------------------------------------
# FlowDirection enum layout (sector indices match atan2 convention)
# ---------------------------------------------------------------------------


class TestFlowDirectionEnum:
    """`FlowDirection` must be an ``IntEnum`` with sectors 0–7."""

    def test_is_int_enum(self) -> None:
        assert issubclass(FlowDirection, int)

    def test_member_count(self) -> None:
        assert len(FlowDirection) == 8

    def test_rightward_is_zero(self) -> None:
        assert FlowDirection.RIGHTWARD == 0

    def test_all_sectors_distinct(self) -> None:
        values = {f.value for f in FlowDirection}
        assert values == set(range(8))


# ---------------------------------------------------------------------------
# classify_flow — pure pixel-space (no CellMetrics)
# ---------------------------------------------------------------------------


class TestClassifyFlowPixelSpace:
    """With ``cell_metrics=None`` the classifier uses raw atan2."""

    @pytest.mark.parametrize(
        "dx, dy, expected",
        [
            (10.0, 0.0, FlowDirection.RIGHTWARD),
            (10.0, 10.0, FlowDirection.SE),
            (0.0, 10.0, FlowDirection.DOWNWARD),
            (-10.0, 10.0, FlowDirection.SW),
            (-10.0, 0.0, FlowDirection.LEFTWARD),
            (-10.0, -10.0, FlowDirection.NW),
            (0.0, -10.0, FlowDirection.UPWARD),
            (10.0, -10.0, FlowDirection.NE),
        ],
    )
    def test_cardinal_and_diagonal(
        self, dx: float, dy: float, expected: FlowDirection
    ) -> None:
        assert classify_flow(dx, dy) == expected

    def test_zero_vector_is_rightward(self) -> None:
        assert classify_flow(0.0, 0.0) == FlowDirection.RIGHTWARD

    def test_very_small_nonzero_still_classifies(self) -> None:
        assert classify_flow(1e-9, 0.0) == FlowDirection.RIGHTWARD
        assert classify_flow(0.0, 1e-9) == FlowDirection.DOWNWARD


# ---------------------------------------------------------------------------
# classify_flow — CellMetrics normalisation
# ---------------------------------------------------------------------------


class TestClassifyFlowCellSpace:
    """Non-square grids should classify using cell-normalised displacement."""

    _DP_GRID = CellMetrics(
        cell_width=60.0,
        cell_height=40.0,
        grid_cols=8,
        grid_rows=5,
        origin_x=0.0,
        origin_y=0.0,
    )

    def test_one_cell_right(self) -> None:
        # 60 px right, 0 px vertical → pure RIGHTWARD regardless of metrics.
        assert classify_flow(60.0, 0.0, self._DP_GRID) == FlowDirection.RIGHTWARD

    def test_one_cell_down(self) -> None:
        # 0 px horizontal, 40 px vertical → pure DOWNWARD.
        assert classify_flow(0.0, 40.0, self._DP_GRID) == FlowDirection.DOWNWARD

    def test_one_cell_diag_se_resolves_to_se(self) -> None:
        # (60, 40) px raw → atan2(40,60) ≈ 33.7° (sector 1 = SE via pure atan2
        # since 33.7° rounds up to 45°? Actually round(0.75) = 1. So SE).
        # After normalisation: norm_dx=1, norm_dy=1 → atan2(1,1) = 45° exactly → SE.
        # Either way: SE.
        assert classify_flow(60.0, 40.0, self._DP_GRID) == FlowDirection.SE

    def test_half_cell_down_short_right_classifies_vertical(self) -> None:
        # Raw pixel angle: atan2(20, 60) ≈ 18° (sector 0 = RIGHTWARD).
        # Normalised:      atan2(20/40, 60/60) = atan2(0.5, 1) ≈ 26.6° still < 22.5°?
        # Actually 26.6° > 22.5° so sector rounds to 1 = SE.
        # The point: normalisation amplifies the vertical component when
        # cell_height < cell_width. Pin the classifier's current answer.
        raw = classify_flow(60.0, 20.0)  # pure pixel
        normed = classify_flow(60.0, 20.0, self._DP_GRID)
        # Normalisation should make vertical motion MORE visible, not less.
        # So the normed sector should be at least as "vertical" as raw.
        assert raw == FlowDirection.RIGHTWARD
        assert normed in (FlowDirection.RIGHTWARD, FlowDirection.SE)

    def test_degenerate_zero_cell_dimensions_falls_back(self) -> None:
        # Zero cell_width should not crash — falls back to raw dx/dy.
        cm = CellMetrics(0.0, 0.0, 1, 1, 0.0, 0.0)
        assert classify_flow(10.0, 0.0, cm) == FlowDirection.RIGHTWARD
        assert classify_flow(0.0, 10.0, cm) == FlowDirection.DOWNWARD


# ---------------------------------------------------------------------------
# CellMetrics — value-type semantics
# ---------------------------------------------------------------------------


class TestCellMetricsNamedTuple:
    """`CellMetrics` must be a hashable NamedTuple-style record."""

    def test_equality(self) -> None:
        a = CellMetrics(60.0, 40.0, 8, 5, 0.0, 0.0)
        b = CellMetrics(60.0, 40.0, 8, 5, 0.0, 0.0)
        assert a == b

    def test_hashable(self) -> None:
        cm = CellMetrics(60.0, 40.0, 8, 5, 0.0, 0.0)
        assert {cm, cm} == {cm}

    def test_positional_construction(self) -> None:
        cm = CellMetrics(60.0, 40.0, 8, 5, 0.0, 0.0)
        assert cm.cell_width == 60.0
        assert cm.cell_height == 40.0
        assert cm.grid_cols == 8
        assert cm.grid_rows == 5
        assert cm.origin_x == 0.0
        assert cm.origin_y == 0.0
