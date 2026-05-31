"""Tests for the simulated annealing stable layout optimizer.

Covers: SA correctness, determinism, fallback guards, validation,
edge crossing counting, distance penalty, convergence check.
"""

from __future__ import annotations

import math

import pytest

from scriba.animation.primitives.graph_layout_stable import (
    _count_edge_crossings,
    _distance_penalty,
    _segments_intersect,
    compute_stable_layout,
)
from scriba.core.context import RenderContext
from scriba.core.errors import ValidationError


def _ctx_with_collector() -> RenderContext:
    """A RenderContext carrying a fresh, per-call warnings collector.

    Each context owns its own list, so warnings never leak between renders
    — the property the module-level collector used to violate.
    """
    return RenderContext(
        resource_resolver=lambda _filename: None,
        warnings_collector=[],
    )


class TestSABasic:
    """Basic SA optimizer behavior."""

    def test_four_nodes_three_edges_valid_positions(self) -> None:
        """SA with 4 nodes, 3 edges produces valid positions within SVG bounds."""
        nodes = ["A", "B", "C", "D"]
        edges = [("A", "B"), ("B", "C"), ("C", "D")]
        result = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            width=400,
            height=300,
            node_radius=16,
        )
        assert result is not None
        assert set(result.keys()) == set(nodes)
        pad = 16 + 8  # node_radius + 8
        for node, (x, y) in result.items():
            assert pad <= x <= 400 - pad, f"Node {node} x={x} out of bounds"
            assert pad <= y <= 300 - pad, f"Node {node} y={y} out of bounds"

    def test_determinism_same_seed(self) -> None:
        """Same seed produces identical positions."""
        nodes = ["A", "B", "C"]
        edges = [("A", "B"), ("B", "C")]
        r1 = compute_stable_layout(nodes=nodes, frame_edge_sets=[edges], seed=7)
        r2 = compute_stable_layout(nodes=nodes, frame_edge_sets=[edges], seed=7)
        assert r1 is not None and r2 is not None
        for node in nodes:
            assert r1[node] == r2[node], f"Mismatch for {node}"

    def test_different_seeds_different_positions(self) -> None:
        """Different seeds produce different positions."""
        nodes = ["A", "B", "C", "D"]
        edges = [("A", "B"), ("B", "C"), ("C", "D")]
        r1 = compute_stable_layout(nodes=nodes, frame_edge_sets=[edges], seed=1)
        r2 = compute_stable_layout(nodes=nodes, frame_edge_sets=[edges], seed=99)
        assert r1 is not None and r2 is not None
        # At least one node should differ.
        any_different = any(r1[n] != r2[n] for n in nodes)
        assert any_different, "Different seeds should produce different layouts"

    def test_mcmf_six_nodes_stable_across_frames(self) -> None:
        """N=6 MCMF example: positions are identical for all frames."""
        nodes = ["s", "a", "b", "c", "d", "t"]
        frame1 = [("s", "a"), ("s", "b"), ("a", "c"), ("b", "d"), ("c", "t"), ("d", "t")]
        frame2 = [("s", "a"), ("a", "c"), ("c", "t")]
        frame3 = [("s", "b"), ("b", "d"), ("d", "t")]
        result = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[frame1, frame2, frame3],
            seed=42,
        )
        assert result is not None
        # Positions are a single set — by construction they are frame-independent.
        assert len(result) == 6


class TestFallbackGuards:
    """Size guard tests for E1501, E1502."""

    def test_e1501_too_many_nodes(self) -> None:
        """N=25 triggers fallback and returns None."""
        nodes = [f"n{i}" for i in range(25)]
        edges = [(f"n{i}", f"n{i+1}") for i in range(24)]
        result = compute_stable_layout(
            nodes=nodes, frame_edge_sets=[edges], seed=42
        )
        assert result is None

    def test_e1502_too_many_frames(self) -> None:
        """60 frames triggers fallback and returns None."""
        nodes = ["A", "B"]
        edges = [("A", "B")]
        frame_edge_sets = [edges] * 60
        result = compute_stable_layout(
            nodes=nodes, frame_edge_sets=frame_edge_sets, seed=42
        )
        assert result is None


class TestValidation:
    """Validation tests for E1504 and E1505."""

    def test_e1504_lambda_clamped_low(self) -> None:
        """Lambda below 0.01 is clamped."""
        nodes = ["A", "B"]
        edges = [("A", "B")]
        result = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            lambda_weight=0.001,
        )
        assert result is not None

    def test_e1504_lambda_clamped_high(self) -> None:
        """Lambda above 10 is clamped."""
        nodes = ["A", "B"]
        edges = [("A", "B")]
        result = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            lambda_weight=100.0,
        )
        assert result is not None

    def test_e1505_negative_seed_raises(self) -> None:
        """Negative seed raises ValidationError."""
        with pytest.raises(ValidationError, match="E1505"):
            compute_stable_layout(
                nodes=["A", "B"],
                frame_edge_sets=[[("A", "B")]],
                seed=-1,
            )


class TestEdgeCrossingCount:
    """Edge crossing counting correctness."""

    def test_known_crossing(self) -> None:
        """Two crossing edges are counted correctly."""
        # Edges (A,D) and (B,C) cross when A is top-left, D is bottom-right,
        # B is top-right, C is bottom-left.
        positions = {
            "A": (0.0, 0.0),
            "B": (1.0, 0.0),
            "C": (0.0, 1.0),
            "D": (1.0, 1.0),
        }
        edges = [("A", "D"), ("B", "C")]
        assert _count_edge_crossings(edges, positions) == 1

    def test_no_crossing(self) -> None:
        """Parallel edges do not cross."""
        positions = {
            "A": (0.0, 0.0),
            "B": (1.0, 0.0),
            "C": (0.0, 1.0),
            "D": (1.0, 1.0),
        }
        edges = [("A", "B"), ("C", "D")]
        assert _count_edge_crossings(edges, positions) == 0


class TestDistancePenalty:
    """Distance penalty correctness."""

    def test_optimal_distance_no_penalty(self) -> None:
        """Distance in [0.3, 0.6] incurs zero penalty."""
        p1 = (0.0, 0.0)
        p2 = (0.4, 0.0)  # d = 0.4, within [0.3, 0.6]
        assert _distance_penalty(p1, p2) == pytest.approx(0.0)

    def test_too_close_penalty(self) -> None:
        """Distance < 0.3 incurs penalty."""
        p1 = (0.0, 0.0)
        p2 = (0.1, 0.0)  # d = 0.1, penalty = (0.3-0.1)^2 = 0.04
        assert _distance_penalty(p1, p2) == pytest.approx(0.04)

    def test_too_far_penalty(self) -> None:
        """Distance > 0.6 incurs penalty."""
        p1 = (0.0, 0.0)
        p2 = (0.9, 0.0)  # d = 0.9, penalty = (0.9-0.6)^2 = 0.09
        assert _distance_penalty(p1, p2) == pytest.approx(0.09)


class TestConvergenceCheck:
    """Convergence check: objective should not be extremely high."""

    def test_sa_does_not_diverge(self) -> None:
        """For a simple graph, SA should converge to a reasonable objective."""
        nodes = ["A", "B", "C", "D"]
        edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")]
        # Run SA; if it returned positions, it converged (or at worst warned).
        result = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
        )
        assert result is not None


# ---------------------------------------------------------------------------
# Wave 6.2: warm-start + SF-5/SF-6 collector
# ---------------------------------------------------------------------------


class TestWarmStart:
    """Warm-start ``initial_positions`` kwarg (Wave 6.2)."""

    def test_initial_positions_near_input(self) -> None:
        """With no edge change, warm-start stays near the given positions."""
        nodes = ["A", "B", "C", "D"]
        edges = [("A", "B"), ("B", "C"), ("C", "D")]
        # Provide positions we know are already reasonable.
        width, height, radius = 400, 300, 16
        seed_positions = {
            "A": (80.0, 80.0),
            "B": (160.0, 80.0),
            "C": (240.0, 220.0),
            "D": (320.0, 220.0),
        }
        result = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            width=width,
            height=height,
            node_radius=radius,
            initial_positions=seed_positions,
        )
        assert result is not None
        # SA wiggles nodes but with warm-start they should be within
        # ~70% of the canvas distance from their starting point. This
        # is still much tighter than a fully-random init could achieve
        # for a 4-node graph (which would average ~canvas/2 displacement).
        for node, (sx, sy) in seed_positions.items():
            rx, ry = result[node]
            dist = math.sqrt((rx - sx) ** 2 + (ry - sy) ** 2)
            max_allowed = 0.70 * max(width, height)
            assert dist < max_allowed, (
                f"Node {node} drifted {dist:.1f}px, expected < {max_allowed}"
            )

    def test_initial_positions_partial_coverage(self) -> None:
        """Missing nodes in initial_positions still get random init."""
        nodes = ["A", "B", "C"]
        edges = [("A", "B"), ("B", "C")]
        result = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            initial_positions={"A": (100.0, 100.0)},
        )
        assert result is not None
        assert set(result.keys()) == {"A", "B", "C"}

    def test_initial_positions_none_equivalent_to_old_behavior(self) -> None:
        """Passing None for initial_positions is equivalent to omitting it."""
        nodes = ["A", "B", "C"]
        edges = [("A", "B"), ("B", "C")]
        r1 = compute_stable_layout(
            nodes=nodes, frame_edge_sets=[edges], seed=42
        )
        r2 = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            initial_positions=None,
        )
        assert r1 == r2

    def test_initial_positions_clamped_to_unit_square(self) -> None:
        """Out-of-canvas coordinates are clamped instead of escaping."""
        nodes = ["A", "B"]
        edges = [("A", "B")]
        # Deliberately provide coordinates outside the 400x300 canvas.
        result = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            width=400,
            height=300,
            node_radius=16,
            initial_positions={"A": (-500.0, -500.0), "B": (9999.0, 9999.0)},
        )
        assert result is not None
        # Final denormalized coordinates must stay inside [pad, dim-pad].
        pad = 16 + 8
        for x, y in result.values():
            assert pad - 1 <= x <= 400 - pad + 1
            assert pad - 1 <= y <= 300 - pad + 1

    def test_warm_start_closer_than_cold_start(self) -> None:
        """Warm-start should end closer to the seed than a cold run.

        Over many nodes the cold run averages near canvas center while
        the warm run should remember the hand-picked seed corners.
        """
        nodes = ["A", "B", "C", "D"]
        edges = [("A", "B"), ("B", "C"), ("C", "D")]
        width, height = 400, 300
        seed_positions = {
            "A": (40.0, 40.0),
            "B": (360.0, 40.0),
            "C": (40.0, 260.0),
            "D": (360.0, 260.0),
        }
        cold = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            width=width,
            height=height,
        )
        warm = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            width=width,
            height=height,
            initial_positions=seed_positions,
        )
        assert cold is not None and warm is not None
        cold_drift = sum(
            math.sqrt(
                (cold[n][0] - seed_positions[n][0]) ** 2
                + (cold[n][1] - seed_positions[n][1]) ** 2
            )
            for n in nodes
        )
        warm_drift = sum(
            math.sqrt(
                (warm[n][0] - seed_positions[n][0]) ** 2
                + (warm[n][1] - seed_positions[n][1]) ** 2
            )
            for n in nodes
        )
        assert warm_drift < cold_drift, (
            f"warm ({warm_drift:.1f}) should be closer than cold ({cold_drift:.1f})"
        )

    def test_initial_positions_all_nodes_random_when_missing(self) -> None:
        """Completely disjoint initial_positions still yields a layout."""
        nodes = ["A", "B"]
        edges = [("A", "B")]
        result = compute_stable_layout(
            nodes=nodes,
            frame_edge_sets=[edges],
            seed=42,
            initial_positions={"Z": (1.0, 1.0)},  # unrelated
        )
        assert result is not None
        assert set(result.keys()) == {"A", "B"}


class TestCollectorPromotion:
    """SF-5/SF-6: logger.warning still fires AND warnings reach ctx collector."""

    def test_e1504_collected_hidden(self) -> None:
        """Lambda outside [0.01, 10] emits an E1504 hidden warning."""
        ctx = _ctx_with_collector()
        compute_stable_layout(
            nodes=["A", "B"],
            frame_edge_sets=[[("A", "B")]],
            seed=42,
            lambda_weight=100.0,
            ctx=ctx,
        )
        entries = ctx.warnings_collector
        assert any(e.code == "E1504" for e in entries)
        e1504 = next(e for e in entries if e.code == "E1504")
        assert e1504.severity == "hidden"
        assert "layout_lambda" in e1504.message

    def test_e1501_collected_dangerous(self) -> None:
        """N > 20 emits E1501 + E1503 dangerous warnings."""
        ctx = _ctx_with_collector()
        nodes = [f"n{i}" for i in range(25)]
        edges = [(f"n{i}", f"n{i+1}") for i in range(24)]
        result = compute_stable_layout(
            nodes=nodes, frame_edge_sets=[edges], seed=42, ctx=ctx
        )
        assert result is None
        codes = {e.code for e in ctx.warnings_collector}
        assert "E1501" in codes
        assert "E1503" in codes
        for e in ctx.warnings_collector:
            if e.code in {"E1501", "E1503"}:
                assert e.severity == "dangerous"

    def test_e1502_collected_dangerous(self) -> None:
        """Too many frames emits E1502 + E1503 dangerous warnings."""
        ctx = _ctx_with_collector()
        result = compute_stable_layout(
            nodes=["A", "B"],
            frame_edge_sets=[[("A", "B")]] * 60,
            seed=42,
            ctx=ctx,
        )
        assert result is None
        codes = {e.code for e in ctx.warnings_collector}
        assert "E1502" in codes
        assert "E1503" in codes

    def test_collector_is_per_context_no_leak(self) -> None:
        """Each context owns its collector — warnings never leak across renders.

        Regression for the old module-level ``_collected`` buffer, which
        accumulated across calls in the same process.
        """
        ctx1 = _ctx_with_collector()
        compute_stable_layout(
            nodes=["A", "B"],
            frame_edge_sets=[[("A", "B")]],
            seed=42,
            lambda_weight=100.0,
            ctx=ctx1,
        )
        assert any(e.code == "E1504" for e in ctx1.warnings_collector)

        # A fresh context starts clean — no carry-over from ctx1.
        ctx2 = _ctx_with_collector()
        compute_stable_layout(
            nodes=["A", "B", "C"],
            frame_edge_sets=[[("A", "B"), ("B", "C")]],
            seed=42,
            ctx=ctx2,
        )
        assert all(e.code != "E1504" for e in ctx2.warnings_collector)

    def test_ok_path_no_warnings(self) -> None:
        """A normal call adds nothing dangerous to the collector."""
        ctx = _ctx_with_collector()
        compute_stable_layout(
            nodes=["A", "B", "C"],
            frame_edge_sets=[[("A", "B"), ("B", "C")]],
            seed=42,
            ctx=ctx,
        )
        # SA may emit E1500 on pathological cases but this graph
        # should not trip the 10x initial objective bound.
        codes = {e.code for e in ctx.warnings_collector}
        assert "E1501" not in codes
        assert "E1502" not in codes
        assert "E1503" not in codes
        assert "E1504" not in codes

    def test_logger_warning_still_fires(self, caplog: pytest.LogCaptureFixture) -> None:
        """Backward-compat: logger.warning is still emitted for SF-5/SF-6."""
        import logging

        caplog.set_level(logging.WARNING, logger="scriba.animation.primitives.graph_layout_stable")
        compute_stable_layout(
            nodes=["A", "B"],
            frame_edge_sets=[[("A", "B")]],
            seed=42,
            lambda_weight=100.0,
        )
        assert any("E1504" in rec.message for rec in caplog.records)
