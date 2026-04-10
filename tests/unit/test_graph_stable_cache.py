"""Tests for the stable layout cache key computation.

Covers: determinism, node sensitivity, frame-order sensitivity,
lambda sensitivity, seed sensitivity.
"""

from __future__ import annotations

from scriba.animation.primitives.graph_layout_stable import compute_cache_key


class TestCacheKeyDeterminism:
    """Same input produces same cache key."""

    def test_same_input_same_key(self) -> None:
        nodes = ["A", "B", "C"]
        frames = [[("A", "B"), ("B", "C")]]
        k1 = compute_cache_key(nodes, frames, lambda_weight=0.3, seed=42)
        k2 = compute_cache_key(nodes, frames, lambda_weight=0.3, seed=42)
        assert k1 == k2

    def test_node_order_irrelevant(self) -> None:
        """Node list order does not affect cache key (sorted internally)."""
        frames = [[("A", "B")]]
        k1 = compute_cache_key(["A", "B"], frames, lambda_weight=0.3, seed=42)
        k2 = compute_cache_key(["B", "A"], frames, lambda_weight=0.3, seed=42)
        assert k1 == k2


class TestCacheKeySensitivity:
    """Different inputs produce different cache keys."""

    def test_different_nodes_different_key(self) -> None:
        frames = [[("A", "B")]]
        k1 = compute_cache_key(["A", "B"], frames, lambda_weight=0.3, seed=42)
        k2 = compute_cache_key(
            ["A", "B", "C"], frames, lambda_weight=0.3, seed=42
        )
        assert k1 != k2

    def test_same_union_different_frame_order_different_key(self) -> None:
        """Same edge union but different frame ordering must differ."""
        nodes = ["A", "B", "C"]
        frames_v1 = [[("A", "B")], [("B", "C")]]
        frames_v2 = [[("B", "C")], [("A", "B")]]
        k1 = compute_cache_key(nodes, frames_v1, lambda_weight=0.3, seed=42)
        k2 = compute_cache_key(nodes, frames_v2, lambda_weight=0.3, seed=42)
        assert k1 != k2

    def test_different_lambda_different_key(self) -> None:
        nodes = ["A", "B"]
        frames = [[("A", "B")]]
        k1 = compute_cache_key(nodes, frames, lambda_weight=0.3, seed=42)
        k2 = compute_cache_key(nodes, frames, lambda_weight=0.5, seed=42)
        assert k1 != k2

    def test_different_seed_different_key(self) -> None:
        nodes = ["A", "B"]
        frames = [[("A", "B")]]
        k1 = compute_cache_key(nodes, frames, lambda_weight=0.3, seed=42)
        k2 = compute_cache_key(nodes, frames, lambda_weight=0.3, seed=99)
        assert k1 != k2
