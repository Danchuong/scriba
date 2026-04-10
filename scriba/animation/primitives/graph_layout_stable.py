"""Simulated annealing layout optimizer for stable Graph positions.

Computes a single set of node positions valid across ALL animation frames,
so nodes do not jump between frames. Pure Python, no external dependencies.

Error codes:
    E1500 — Convergence warning (objective too high, positions still returned)
    E1501 — Too many nodes (N > 20), returns None for force-layout fallback
    E1502 — Too many frames (T > 50), returns None for force-layout fallback
    E1503 — Fallback triggered (accompanies E1501 or E1502)
    E1504 — lambda_weight out of [0.01, 10] range, clamped
    E1505 — Invalid seed (must be non-negative integer)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
from typing import Any

from scriba.core.errors import ValidationError

logger = logging.getLogger(__name__)

_MAX_NODES = 20
_MAX_FRAMES = 50
_LAMBDA_MIN = 0.01
_LAMBDA_MAX = 10.0


def _segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> bool:
    """Check if segments (p1,p2) and (p3,p4) cross (shared endpoints excluded)."""

    def cross(
        o: tuple[float, float],
        a: tuple[float, float],
        b: tuple[float, float],
    ) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1 = cross(p3, p4, p1)
    d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3)
    d4 = cross(p1, p2, p4)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True
    return False


def _count_edge_crossings(
    edges: list[tuple[str, str]],
    positions: dict[str, tuple[float, float]],
) -> int:
    """Count crossing edge pairs for a single frame's edge set."""
    count = 0
    for i in range(len(edges)):
        u1, v1 = edges[i]
        p1 = positions[u1]
        p2 = positions[v1]
        for j in range(i + 1, len(edges)):
            u2, v2 = edges[j]
            # Skip edges sharing an endpoint.
            if u1 == u2 or u1 == v2 or v1 == u2 or v1 == v2:
                continue
            p3 = positions[u2]
            p4 = positions[v2]
            if _segments_intersect(p1, p2, p3, p4):
                count += 1
    return count


def _distance_penalty(
    u_pos: tuple[float, float],
    v_pos: tuple[float, float],
) -> float:
    """Compute distance penalty for a pair of connected nodes.

    Penalizes edges that are too short (< 0.3) or too long (> 0.6).
    """
    dx = u_pos[0] - v_pos[0]
    dy = u_pos[1] - v_pos[1]
    d = math.sqrt(dx * dx + dy * dy)
    too_close = max(0.0, 0.3 - d)
    too_far = max(0.0, d - 0.6)
    return too_close * too_close + too_far * too_far


def _objective(
    positions: dict[str, tuple[float, float]],
    frame_edge_sets: list[list[tuple[str, str]]],
    lambda_weight: float,
) -> float:
    """Compute the joint objective across all frames.

    O = sum_t[edge_crossings(E_t, positions)] + lambda * sum_edges[distance_penalty]
    """
    total = 0.0
    all_edges: set[tuple[str, str]] = set()
    for edges in frame_edge_sets:
        total += _count_edge_crossings(edges, positions)
        for e in edges:
            all_edges.add(e)
    for u, v in all_edges:
        total += lambda_weight * _distance_penalty(positions[u], positions[v])
    return total


def compute_cache_key(
    nodes: list[str],
    frame_edge_sets: list[list[tuple[str, str]]],
    lambda_weight: float,
    seed: int,
) -> str:
    """Compute a SHA-256 cache key for the layout parameters.

    The cache key uses the ordered list of per-frame edge sets, NOT the union.
    Two scenes with the same edge union but different frame orderings produce
    different cache keys.
    """
    payload = json.dumps(
        {
            "nodes": sorted(nodes),
            "frames": [sorted(edges) for edges in frame_edge_sets],
            "layout_lambda": lambda_weight,
            "layout_seed": seed,
            "version": 1,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def compute_stable_layout(
    nodes: list[str],
    frame_edge_sets: list[list[tuple[str, str]]],
    seed: int = 42,
    lambda_weight: float = 0.3,
    width: int = 400,
    height: int = 300,
    node_radius: int = 16,
) -> dict[str, tuple[float, float]] | None:
    """Compute stable node positions across all frames via simulated annealing.

    Returns dict mapping node_id to (svg_x, svg_y), or None if the problem
    exceeds size guards (caller should fall back to force layout).

    Args:
        nodes: List of node identifiers.
        frame_edge_sets: Per-frame edge lists. Each entry is a list of
            (source, target) tuples for that frame.
        seed: Random seed for reproducibility. Must be non-negative.
        lambda_weight: Weight for distance penalty term. Clamped to [0.01, 10].
        width: SVG canvas width in pixels.
        height: SVG canvas height in pixels.
        node_radius: Node circle radius for padding computation.

    Returns:
        Mapping of node_id to (svg_x, svg_y), or None on fallback.

    Raises:
        ValidationError: If seed is negative (E1505).
    """
    # --- Validate seed ---
    if not isinstance(seed, int) or seed < 0:
        raise ValidationError(
            f"E1505: layout_seed must be a non-negative integer, got {seed!r}"
        )

    # --- Validate and clamp lambda ---
    if lambda_weight < _LAMBDA_MIN or lambda_weight > _LAMBDA_MAX:
        logger.warning(
            "E1504: layout_lambda=%.4f outside [%.2f, %.2f], clamping",
            lambda_weight,
            _LAMBDA_MIN,
            _LAMBDA_MAX,
        )
        lambda_weight = max(_LAMBDA_MIN, min(_LAMBDA_MAX, lambda_weight))

    # --- Guard: too many nodes ---
    if len(nodes) > _MAX_NODES:
        logger.warning(
            "E1501: %d nodes exceeds limit of %d", len(nodes), _MAX_NODES
        )
        logger.warning("E1503: falling back to force layout")
        return None

    # --- Guard: too many frames ---
    if len(frame_edge_sets) > _MAX_FRAMES:
        logger.warning(
            "E1502: %d frames exceeds limit of %d",
            len(frame_edge_sets),
            _MAX_FRAMES,
        )
        logger.warning("E1503: falling back to force layout")
        return None

    # --- Initialize positions randomly in [0,1]^2 ---
    rng = random.Random(seed)
    positions: dict[str, tuple[float, float]] = {
        node: (rng.random(), rng.random()) for node in nodes
    }

    # --- SA parameters ---
    t0 = 10.0
    alpha = 0.97
    num_iterations = 200
    step_size_initial = 0.2
    temperature = t0

    initial_obj = _objective(positions, frame_edge_sets, lambda_weight)
    current_obj = initial_obj

    for _ in range(num_iterations):
        # Pick a random node.
        node = rng.choice(nodes)
        old_pos = positions[node]

        # Propose displacement scaled by temperature.
        magnitude = (temperature / t0) * step_size_initial
        angle = rng.uniform(0, 2 * math.pi)
        dx = magnitude * math.cos(angle)
        dy = magnitude * math.sin(angle)
        new_x = max(0.0, min(1.0, old_pos[0] + dx))
        new_y = max(0.0, min(1.0, old_pos[1] + dy))

        # Apply and evaluate.
        positions[node] = (new_x, new_y)
        new_obj = _objective(positions, frame_edge_sets, lambda_weight)
        delta = new_obj - current_obj

        if delta <= 0:
            # Accept improvement.
            current_obj = new_obj
        else:
            # Accept worse solution with SA probability.
            if temperature > 0 and rng.random() < math.exp(-delta / temperature):
                current_obj = new_obj
            else:
                # Reject: revert.
                positions[node] = old_pos

        temperature *= alpha

    # --- Convergence check ---
    if initial_obj > 0 and current_obj > 10 * initial_obj:
        logger.warning(
            "E1500: final objective (%.4f) exceeds 10x initial (%.4f)",
            current_obj,
            initial_obj,
        )

    # --- Denormalize to SVG coordinates ---
    pad = node_radius + 8
    result: dict[str, tuple[float, float]] = {}
    for node, (nx, ny) in positions.items():
        svg_x = pad + nx * (width - 2 * pad)
        svg_y = pad + ny * (height - 2 * pad)
        result[node] = (svg_x, svg_y)

    return result
