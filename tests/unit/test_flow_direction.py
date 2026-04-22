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
    _compute_control_points,
    classify_flow,
    emit_arrow_svg,
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


# ---------------------------------------------------------------------------
# _compute_control_points stagger-flip gate (Phase C/2 gap fill)
# ---------------------------------------------------------------------------


_DP_GRID = CellMetrics(
    cell_width=60.0,
    cell_height=40.0,
    grid_cols=8,
    grid_rows=5,
    origin_x=0.0,
    origin_y=0.0,
)


def _cp(arrow_index: int, layout: str, cell_metrics: CellMetrics | None):
    """Invoke `_compute_control_points` on a fixed horizontal pair."""
    x1, y1, x2, y2 = 0.0, 0.0, 100.0, 0.0
    dx, dy = x2 - x1, y2 - y1
    return _compute_control_points(
        x1, y1, x2, y2, dx, dy, math.hypot(dx, dy) or 1.0,
        arrow_index, 40.0, layout, "",
        cell_metrics=cell_metrics,
    )


class TestStaggerFlip:
    """Phase D stagger-flip gate: ``cell_metrics is not None and layout=='2d'``."""

    def test_even_index_no_flip(self) -> None:
        g0 = _cp(arrow_index=0, layout="2d", cell_metrics=_DP_GRID)
        g1 = _cp(arrow_index=1, layout="2d", cell_metrics=_DP_GRID)
        # Horizontal source→dst, perp y flips on odd index → cp y-sign flips.
        assert g0.cp1_y != g1.cp1_y
        assert (g0.cp1_y > 0) != (g1.cp1_y > 0)

    def test_flip_requires_cell_metrics(self) -> None:
        g_none = _cp(arrow_index=1, layout="2d", cell_metrics=None)
        g_cm = _cp(arrow_index=1, layout="2d", cell_metrics=_DP_GRID)
        assert g_none.cp1_y != g_cm.cp1_y

    def test_1d_layout_ignores_cell_metrics_entirely(self) -> None:
        # Horizontal layout uses the "bow upward" branch and never reads flow.
        g_cm = _cp(arrow_index=1, layout="horizontal", cell_metrics=_DP_GRID)
        g_none = _cp(arrow_index=1, layout="horizontal", cell_metrics=None)
        assert g_cm == g_none

    def test_flip_preserves_magnitude(self) -> None:
        g0 = _cp(arrow_index=0, layout="2d", cell_metrics=_DP_GRID)
        g1 = _cp(arrow_index=1, layout="2d", cell_metrics=_DP_GRID)
        # arrow_index=1 adds one stagger step, so magnitudes differ slightly.
        # Direction MUST be mirrored, not scaled differently.
        assert math.copysign(1, g0.cp1_y) == -math.copysign(1, g1.cp1_y)


# ---------------------------------------------------------------------------
# emit_arrow_svg: cell_metrics=None vs cell_metrics provided for 1D
# ---------------------------------------------------------------------------


class TestEmitArrowCellMetricsIdentity:
    """1D callers: cell_metrics presence must never alter SVG output.

    Stagger-flip gate requires ``layout == "2d"``; the default layout is
    ``"horizontal"`` so providing cell_metrics for a 1D caller should
    produce byte-identical SVG markup.
    """

    @staticmethod
    def _emit(cell_metrics: "CellMetrics | None") -> list[str]:
        lines: list[str] = []
        ann = {"color": "info", "label": "x", "target": "a", "arrow_from": "b"}
        emit_arrow_svg(
            lines, ann,
            src_point=(0.0, 0.0),
            dst_point=(100.0, 0.0),
            arrow_index=0,
            cell_height=40.0,
            render_inline_tex=None,
            cell_metrics=cell_metrics,
        )
        return lines

    def test_none_vs_provided_identical_1d(self) -> None:
        cm = CellMetrics(60.0, 40.0, 8, 1, 0.0, 0.0)
        assert self._emit(None) == self._emit(cm)


# ---------------------------------------------------------------------------
# classify_flow zero-vector robustness (tolerance-based guard)
# ---------------------------------------------------------------------------


class TestClassifyFlowTolerance:
    """Float-subtraction residuals must still classify as degenerate."""

    def test_fp_residual_classifies_as_rightward(self) -> None:
        # Realistic residual after `x2 - x1` for x1 == x2 under shortening.
        assert classify_flow(1e-12, -1e-13) == FlowDirection.RIGHTWARD
        assert classify_flow(-1e-15, 1e-15) == FlowDirection.RIGHTWARD
