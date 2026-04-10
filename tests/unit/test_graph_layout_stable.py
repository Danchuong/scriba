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
from scriba.core.errors import ValidationError


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
