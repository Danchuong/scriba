"""Sugiyama-style layered layout for directed graphs.

Produces a top-down (or left-right) layered layout where:
  * layer(v) = longest path from any source to v (longest-path ranking)
  * nodes within a layer are ordered via barycenter heuristic to reduce
    edge crossings
  * coordinates are even-spread within each layer, centered in the viewport

Pure Python, O(V + E) layering + O(sweeps · E) crossing reduction.
Deterministic — same inputs always produce the same output. ``seed`` is
accepted for API parity with ``compute_stable_layout`` but only affects
tie-breaking when two nodes share the same barycenter.

Cycle handling: back edges are detected via iterative DFS and temporarily
reversed for the layering pass. Reversed edges are restored in the final
output so the caller's edge list is unchanged — only node coordinates
are produced here.

Error codes:
    E1506 — Empty node list (returns empty dict, not None)
"""

from __future__ import annotations

import logging
import random
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from scriba.core.context import RenderContext

from scriba.core.errors import ValidationError

logger = logging.getLogger(__name__)

# Fixed-point sweep count. 12 forward + 12 backward matches dagre's
# default and converges for N ≤ ~30 well before the cap.
_BARYCENTER_SWEEPS = 12

# Padding around viewport edge, matching graph.py's ``_PADDING``.
_PADDING = 20

# Minimum primary-axis distance between adjacent layers. Sized so that
# after subtracting 2 × node_radius, at least one edge-weight pill
# (~22 px tall) fits on the visible segment with margin. Falling below
# this gap forces the GEP v2.0 cascade to escape to perp/leader stages,
# which the caller perceives as "misaligned" labels.
_MIN_LAYER_GAP = 100


# ---------------------------------------------------------------------------
# Cycle breaking
# ---------------------------------------------------------------------------


def _break_cycles(
    nodes: list[str],
    edges: list[tuple[str, str]],
) -> tuple[list[tuple[str, str]], set[tuple[str, str]]]:
    """Return (dag_edges, reversed_set).

    Uses iterative DFS; any edge (u, v) where v is currently on the DFS
    stack is a back-edge and gets reversed. Self-loops are dropped.
    """
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    known = set(nodes)
    for u, v in edges:
        if u == v:
            continue
        if u not in known or v not in known:
            logger.warning(
                "hierarchical layout: edge (%r, %r) references unknown node; dropped",
                u, v,
            )
            continue
        adj[u].append(v)

    visited: set[str] = set()
    on_stack: set[str] = set()
    reversed_set: set[tuple[str, str]] = set()

    for root in nodes:
        if root in visited:
            continue
        # Iterative DFS. Stack entries: (node, iter_index).
        stack: list[tuple[str, int]] = [(root, 0)]
        on_stack.add(root)
        while stack:
            u, i = stack[-1]
            if i == 0:
                visited.add(u)
            neighbors = adj.get(u, [])
            if i < len(neighbors):
                stack[-1] = (u, i + 1)
                v = neighbors[i]
                if v in on_stack:
                    reversed_set.add((u, v))
                elif v not in visited:
                    stack.append((v, 0))
                    on_stack.add(v)
            else:
                on_stack.discard(u)
                stack.pop()

    dag_edges: list[tuple[str, str]] = []
    for u, v in edges:
        if u == v:
            continue
        if (u, v) in reversed_set:
            dag_edges.append((v, u))
        else:
            dag_edges.append((u, v))
    return dag_edges, reversed_set


# ---------------------------------------------------------------------------
# Layer assignment (longest-path ranking via Kahn's algorithm)
# ---------------------------------------------------------------------------


def _assign_layers(
    nodes: list[str],
    dag_edges: list[tuple[str, str]],
) -> list[list[str]]:
    """Return nodes grouped by layer index (layer 0 at top)."""
    pred: dict[str, list[str]] = {n: [] for n in nodes}
    succ: dict[str, list[str]] = {n: [] for n in nodes}
    for u, v in dag_edges:
        if u in succ and v in pred:
            succ[u].append(v)
            pred[v].append(u)

    indegree = {n: len(pred[n]) for n in nodes}
    # Kahn's: process sources first, always keeping input order for
    # determinism among ties. ``deque.popleft`` is O(1); a plain list
    # would degrade the whole pass to O(V²).
    queue: deque[str] = deque(n for n in nodes if indegree[n] == 0)
    layer: dict[str, int] = {}
    while queue:
        u = queue.popleft()
        layer[u] = max((layer[p] + 1 for p in pred[u] if p in layer), default=0)
        for v in succ[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)

    # Nodes still missing (shouldn't happen after cycle break, but guard):
    # assign layer 0.
    for n in nodes:
        layer.setdefault(n, 0)

    if not nodes:
        return []
    max_layer = max(layer.values(), default=0)
    layers: list[list[str]] = [[] for _ in range(max_layer + 1)]
    for n in nodes:  # preserve input order within layer
        layers[layer[n]].append(n)
    return layers


# ---------------------------------------------------------------------------
# Crossing minimization (barycenter heuristic)
# ---------------------------------------------------------------------------


def _barycenter_sort(
    fixed: list[str],
    free: list[str],
    neighbors_in_fixed: dict[str, list[str]],
    rng: random.Random,
) -> list[str]:
    pos = {n: i for i, n in enumerate(fixed)}

    def key(n: str) -> tuple[float, float]:
        nbrs = [pos[nb] for nb in neighbors_in_fixed.get(n, []) if nb in pos]
        bary = sum(nbrs) / len(nbrs) if nbrs else float(pos.get(n, 0))
        # Tiny jitter for ties only; seeded so determinism holds for identical
        # inputs.
        return (bary, rng.random())

    return sorted(free, key=key)


def _minimize_crossings(
    layers: list[list[str]],
    dag_edges: list[tuple[str, str]],
    rng: random.Random,
) -> list[list[str]]:
    if len(layers) < 2:
        return layers

    fwd: dict[str, list[str]] = {n: [] for layer in layers for n in layer}
    bwd: dict[str, list[str]] = {n: [] for layer in layers for n in layer}
    for u, v in dag_edges:
        if u in fwd and v in bwd:
            fwd[u].append(v)
            bwd[v].append(u)

    working = [list(layer) for layer in layers]
    for _ in range(_BARYCENTER_SWEEPS):
        # Forward sweep — sort layer i by barycenter of predecessors in i-1.
        for i in range(1, len(working)):
            working[i] = _barycenter_sort(working[i - 1], working[i], bwd, rng)
        # Backward sweep — sort layer i by barycenter of successors in i+1.
        for i in range(len(working) - 2, -1, -1):
            working[i] = _barycenter_sort(working[i + 1], working[i], fwd, rng)
    return working


# ---------------------------------------------------------------------------
# Coordinate assignment
# ---------------------------------------------------------------------------


def _assign_coords(
    layers: list[list[str]],
    *,
    width: int,
    height: int,
    node_radius: int,
    orientation: str,
) -> dict[str, tuple[float, float]]:
    pad = node_radius + _PADDING // 2
    positions: dict[str, tuple[float, float]] = {}

    if orientation == "LR":
        primary, secondary = width, height
    else:  # "TB" default
        primary, secondary = height, width

    n_layers = len(layers)
    if n_layers == 0:
        return positions

    # Spread layers along the primary axis (top-down by default).
    if n_layers == 1:
        primary_coords = [primary / 2.0]
    else:
        # Enforce a minimum layer gap so edge pills fit on the visible
        # segment. If the caller's viewport is too small, positions
        # overflow — the caller is expected to expand width/height to
        # encompass the returned bounding box.
        span_min = (n_layers - 1) * _MIN_LAYER_GAP
        span = max(primary - 2 * pad, span_min)
        primary_coords = [pad + i * span / (n_layers - 1) for i in range(n_layers)]

    for layer_idx, layer in enumerate(layers):
        n = len(layer)
        if n == 0:
            continue
        if n == 1:
            sec_coords = [secondary / 2.0]
        else:
            span = secondary - 2 * pad
            sec_coords = [pad + j * span / (n - 1) for j in range(n)]
        for node, sec in zip(layer, sec_coords, strict=True):
            if orientation == "LR":
                positions[node] = (primary_coords[layer_idx], sec)
            else:
                positions[node] = (sec, primary_coords[layer_idx])
    return positions


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compute_hierarchical_layout(
    nodes: list[str],
    frame_edge_sets: list[list[tuple[str, str]]],
    seed: int = 42,
    width: int = 400,
    height: int = 300,
    node_radius: int = 16,
    orientation: str = "TB",
    *,
    ctx: "RenderContext | None" = None,
) -> dict[str, tuple[float, float]] | None:
    """Compute layered node positions for a directed graph.

    Mirrors the signature of ``compute_stable_layout`` so the caller
    (``Graph.__init__``) can treat the two as interchangeable dispatch
    targets. Returns a dict of node_id → (svg_x, svg_y), or None only on
    invalid orientation (caller falls back to force layout).

    Args:
        nodes: List of node identifiers.
        frame_edge_sets: Per-frame edge lists. All frames' edges are
            unioned before layering so the layout is stable across the
            animation.
        seed: Deterministic tie-break seed. Non-negative integer.
        width: SVG canvas width in pixels.
        height: SVG canvas height in pixels.
        node_radius: Node circle radius for padding computation.
        orientation: ``"TB"`` (default, top→bottom) or ``"LR"`` (left→right).
        ctx: Reserved for future warning emission. Unused today.

    Raises:
        ValidationError: If seed is invalid (E1505).

    Returns:
        Mapping of node_id to (svg_x, svg_y) floats in SVG coordinates,
        or None when orientation is unrecognized.

    Note:
        When the layer count requires more primary-axis space than
        the passed ``height`` (TB) or ``width`` (LR) provides —
        enforced via ``_MIN_LAYER_GAP`` so edge-weight pills fit on
        visible segments — returned coordinates legally exceed the
        caller's viewport. The caller (see ``graph.py`` hierarchical
        dispatch) must expand its canvas to encompass the bounding
        box of the returned positions.
    """
    del ctx  # reserved

    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValidationError(
            f"layout_seed must be a non-negative integer, got {seed!r}",
            code="E1505",
        )

    if orientation not in ("TB", "LR"):
        return None

    if not nodes:
        return {}

    # Union edges across all frames so the layout is stable.
    edge_set: set[tuple[str, str]] = set()
    for frame in frame_edge_sets:
        for pair in frame:
            edge_set.add((pair[0], pair[1]))
    edges = sorted(edge_set)  # deterministic iteration

    dag_edges, _reversed = _break_cycles(nodes, edges)
    layers = _assign_layers(nodes, dag_edges)
    rng = random.Random(seed)
    layers = _minimize_crossings(layers, dag_edges, rng)

    return _assign_coords(
        layers,
        width=width,
        height=height,
        node_radius=node_radius,
        orientation=orientation,
    )
