"""Tree layout algorithms extracted from tree.py (Wave D2).

Contains:
- ``_shorten_line_to_circle`` — edge geometry helper.
- ``_build_segtree``          — builds nodes/edges for a segment tree.
- ``_reingold_tilford``       — Reingold-Tilford layout (iterative).
"""

from __future__ import annotations

import math
from typing import Any

__all__ = [
    "_build_segtree",
    "_reingold_tilford",
    "_shorten_line_to_circle",
]

# ---------------------------------------------------------------------------
# Constants shared with tree.py (duplicated to avoid circular import)
# ---------------------------------------------------------------------------

_DEFAULT_WIDTH = 400
_DEFAULT_HEIGHT = 300
_PADDING = 30


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------


def _shorten_line_to_circle(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    radius: int,
) -> tuple[int, int]:
    """Move ``(x2, y2)`` back along the line by *radius* pixels.

    Used so edges stop at the circle boundary rather than at the centre.
    """
    dx = x2 - x1
    dy = y2 - y1
    d = max(math.sqrt(dx * dx + dy * dy), 0.01)
    return (round(x2 - radius * dx / d), round(y2 - radius * dy / d))


# ---------------------------------------------------------------------------
# Segment tree builder
# ---------------------------------------------------------------------------


def _build_segtree(
    data: list[Any],
) -> tuple[str, list[str], list[tuple[str, str]], dict[str, Any]]:
    """Build segment tree nodes and edges from leaf data.

    Returns ``(root_id, nodes, edges, sums)`` where *sums* maps each node ID
    to its aggregate value.
    """
    n = len(data)
    if n == 0:
        return "[0,0]", ["[0,0]"], [], {"[0,0]": 0}

    nodes: list[str] = []
    edges: list[tuple[str, str]] = []
    sums: dict[str, Any] = {}

    def build(lo: int, hi: int) -> str:
        node_id = f"[{lo},{hi}]"
        nodes.append(node_id)
        if lo == hi:
            sums[node_id] = data[lo]
        else:
            mid = (lo + hi) // 2
            left = build(lo, mid)
            right = build(mid + 1, hi)
            edges.append((node_id, left))
            edges.append((node_id, right))
            sums[node_id] = (
                (sums[left] + sums[right])
                if isinstance(sums[left], (int, float))
                and isinstance(sums[right], (int, float))
                else 0
            )
        return node_id

    root = build(0, n - 1)
    return root, nodes, edges, sums


# ---------------------------------------------------------------------------
# Reingold-Tilford layout
# ---------------------------------------------------------------------------


def _reingold_tilford(
    root: str | int,
    children_map: dict[str | int, list[str | int]],
    *,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
) -> dict[str | int, tuple[int, int]]:
    """Compute Reingold-Tilford tree layout positions.

    Returns a dict mapping each node_id to an ``(x, y)`` integer pair.
    Layout is fully deterministic.

    Algorithm:
    1. Compute depth of each node via iterative DFS.
    2. Iterative bottom-up: assign each subtree a contiguous x range.
       Leaves take width 1; internal nodes center over children.
    3. Normalize all positions into the viewport.

    Implemented without recursion so deep trees do not hit Python's
    default recursion limit (Wave 4B Cluster 1 DoS fix).
    """
    if not children_map:
        return {root: (width // 2, _PADDING)}

    # 1. Compute depth via iterative DFS.
    #
    # An explicit stack is used instead of recursion so deeply nested
    # trees (e.g., a 1000-level linear tree) cannot trigger Python's
    # default recursion limit and raise ``RecursionError``. See the
    # Wave 4B Cluster 1 recursion-DoS fix for context.
    depth: dict[str | int, int] = {}
    max_depth = 0
    depth_stack: list[tuple[str | int, int]] = [(root, 0)]
    while depth_stack:
        node, d = depth_stack.pop()
        depth[node] = d
        if d > max_depth:
            max_depth = d
        for child in children_map.get(node, []):
            depth_stack.append((child, d + 1))

    # 2. Assign x positions via two iterative passes.
    #
    # A recursive implementation would blow the Python stack for very
    # deep trees (e.g., 1000-level linear trees). The two-pass
    # approach below is purely iterative:
    #
    #   Pass A — post-order walk computes ``subtree_width`` for every
    #   node. Leaves take width 1.0; internal nodes take the sum of
    #   their children's widths.
    #
    #   Pass B — pre-order walk assigns the left-edge offset of each
    #   subtree, then sets ``prelim_x`` for each node as the midpoint
    #   between its first and last child's ``prelim_x`` (computed on
    #   pop, once children have been finalised).
    prelim_x: dict[str | int, float] = {}
    subtree_width: dict[str | int, float] = {}

    # --- Pass A: post-order width computation (iterative) ----------
    # Stack frames: (node, visited_flag).
    width_stack: list[tuple[str | int, bool]] = [(root, False)]
    while width_stack:
        node, visited = width_stack.pop()
        kids = children_map.get(node, [])
        if not kids:
            subtree_width[node] = 1.0
            continue
        if not visited:
            width_stack.append((node, True))
            for child in kids:
                width_stack.append((child, False))
        else:
            subtree_width[node] = sum(subtree_width[c] for c in kids)

    # --- Pass B: pre-order offset assignment + post-order midpoint -
    # Stack frames: (node, offset, visited_flag).
    pos_stack: list[tuple[str | int, float, bool]] = [(root, 0.0, False)]
    while pos_stack:
        node, offset, visited = pos_stack.pop()
        kids = children_map.get(node, [])
        if not kids:
            prelim_x[node] = offset
            continue
        if not visited:
            # Re-push self as visited so we can compute midpoint
            # after children are finalised.
            pos_stack.append((node, offset, True))
            # Push children in reverse so leftmost is processed first
            # (LIFO). Each child starts at the running cursor based
            # on its left siblings' widths.
            cursor = offset
            child_offsets: list[tuple[str | int, float]] = []
            for child in kids:
                child_offsets.append((child, cursor))
                cursor += subtree_width[child]
            for child, child_offset in reversed(child_offsets):
                pos_stack.append((child, child_offset, False))
        else:
            first_child_x = prelim_x[kids[0]]
            last_child_x = prelim_x[kids[-1]]
            prelim_x[node] = (first_child_x + last_child_x) / 2.0

    # 3. Normalize to viewport
    all_nodes = list(prelim_x.keys())
    if not all_nodes:
        return {}

    min_px = min(prelim_x[n] for n in all_nodes)
    max_px = max(prelim_x[n] for n in all_nodes)

    usable_width = width - 2 * _PADDING
    usable_height = height - 2 * _PADDING

    x_range = max_px - min_px
    x_scale = usable_width / x_range if x_range > 0 else 0.0
    y_scale = usable_height / max_depth if max_depth > 0 else 0.0

    positions: dict[str | int, tuple[int, int]] = {}
    for node in all_nodes:
        if x_range == 0:
            x = width // 2
        else:
            x = round(_PADDING + (prelim_x[node] - min_px) * x_scale)
        y = round(_PADDING + depth[node] * y_scale)
        positions[node] = (x, y)

    return positions
