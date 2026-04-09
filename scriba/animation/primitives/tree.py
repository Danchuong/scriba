"""Tree primitive with Reingold-Tilford layout and segment tree variants.

Implements ``\\shape{name}{Tree}{root=..., nodes=..., edges=...}`` for BSTs,
segment trees, recursive DP, and tree traversal visualizations.

See ``docs/06-primitives.md`` section 7 for the authoritative specification.
"""

from __future__ import annotations

from html import escape as html_escape
from typing import Any

from scriba.animation.primitives.base import BoundingBox, PrimitiveBase, svg_style_attrs

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_WIDTH = 400
_DEFAULT_HEIGHT = 300
_NODE_RADIUS = 20
_LAYER_GAP = 60
_MIN_H_GAP = 50
_EDGE_STROKE_WIDTH = 1.5
_PADDING = 30


# ---------------------------------------------------------------------------
# Segment tree builder
# ---------------------------------------------------------------------------


def build_segtree(
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


def reingold_tilford(
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
    1. Compute depth of each node via DFS.
    2. Recursive bottom-up: assign each subtree a contiguous x range.
       Leaves take width 1; internal nodes center over children.
    3. Normalize all positions into the viewport.
    """
    if not children_map:
        return {root: (width // 2, _PADDING)}

    # 1. Compute depth via DFS
    depth: dict[str | int, int] = {}
    max_depth = 0

    def _compute_depth(node: str | int, d: int) -> None:
        nonlocal max_depth
        depth[node] = d
        max_depth = max(max_depth, d)
        for child in children_map.get(node, []):
            _compute_depth(child, d + 1)

    _compute_depth(root, 0)

    # 2. Bottom-up: assign x positions
    #    Each subtree occupies a contiguous range starting at `offset`.
    #    Returns the width consumed by the subtree.
    prelim_x: dict[str | int, float] = {}

    def _layout(node: str | int, offset: float) -> float:
        kids = children_map.get(node, [])
        if not kids:
            prelim_x[node] = offset
            return 1.0

        # Layout children left-to-right
        cursor = offset
        for child in kids:
            child_width = _layout(child, cursor)
            cursor += child_width

        total_width = cursor - offset
        # Center parent over children
        first_child_x = prelim_x[kids[0]]
        last_child_x = prelim_x[kids[-1]]
        prelim_x[node] = (first_child_x + last_child_x) / 2.0
        return total_width

    _layout(root, 0.0)

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


# ---------------------------------------------------------------------------
# Tree primitive
# ---------------------------------------------------------------------------


class Tree(PrimitiveBase):
    """Rooted tree primitive with Reingold-Tilford layout.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``T``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
    """

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        self.kind: str | None = params.get("kind")
        self.label: str | None = params.get("label")
        self.show_sum: bool = bool(params.get("show_sum", False))

        # Build tree structure depending on kind
        if self.kind == "segtree":
            self._init_segtree(params)
        elif self.kind == "sparse_segtree":
            self._init_sparse_segtree(params)
        else:
            self._init_standard(params)

        # Build children map from edges
        self.children_map: dict[str | int, list[str | int]] = {
            n: [] for n in self.nodes
        }
        for parent, child in self.edges:
            if parent in self.children_map:
                self.children_map[parent].append(child)

        # Compute viewport dimensions based on tree size
        node_count = len(self.nodes)
        depth = self._compute_max_depth()
        self.width: int = max(_DEFAULT_WIDTH, node_count * _MIN_H_GAP + 2 * _PADDING)
        self.height: int = max(_DEFAULT_HEIGHT, (depth + 1) * _LAYER_GAP + 2 * _PADDING)

        # Compute positions
        if self.nodes:
            self.positions: dict[str | int, tuple[int, int]] = reingold_tilford(
                self.root,
                self.children_map,
                width=self.width,
                height=self.height,
            )
        else:
            self.positions = {}

    # ----- initialization helpers -----------------------------------------

    def _init_standard(self, params: dict[str, Any]) -> None:
        """Initialize a standard tree from explicit root/nodes/edges."""
        from scriba.animation.errors import animation_error

        root = params.get("root")
        if root is None:
            raise animation_error("E1103", "Tree requires 'root' parameter")

        self.root: str | int = root
        self.nodes: list[str | int] = list(params.get("nodes", []))
        raw_edges = params.get("edges", [])
        self.edges: list[tuple[str | int, str | int]] = [
            (e[0], e[1]) for e in raw_edges
        ]
        self.node_labels: dict[str | int, str] = {
            n: str(n) for n in self.nodes
        }

        # Ensure root is in nodes list
        if self.root not in self.nodes:
            self.nodes.insert(0, self.root)

        # Infer nodes from edges if not provided
        if not self.nodes:
            node_set: set[str | int] = {self.root}
            for p, c in self.edges:
                node_set.add(p)
                node_set.add(c)
            self.nodes = sorted(node_set, key=str)
            self.node_labels = {n: str(n) for n in self.nodes}

    def _init_segtree(self, params: dict[str, Any]) -> None:
        """Initialize a segment tree from leaf data."""
        from scriba.animation.errors import animation_error

        data = params.get("data")
        if data is None:
            raise animation_error("E1103", "segtree requires 'data' parameter")

        data = list(data)
        root_id, nodes, edges, sums = build_segtree(data)
        self.root = root_id
        self.nodes = nodes
        self.edges = edges
        self._sums: dict[str, Any] = sums

        self.node_labels: dict[str | int, str] = {}
        for node_id in nodes:
            label = str(node_id)
            if self.show_sum and node_id in sums:
                label = f"{node_id}={sums[node_id]}"
            self.node_labels[node_id] = label

    def _init_sparse_segtree(self, params: dict[str, Any]) -> None:
        """Initialize a sparse segment tree with range bounds."""
        from scriba.animation.errors import animation_error

        range_lo = params.get("range_lo")
        range_hi = params.get("range_hi")
        if range_lo is None or range_hi is None:
            raise animation_error(
                "E1103",
                "sparse_segtree requires 'range_lo' and 'range_hi' parameters",
            )

        self.range_lo: int = int(range_lo)
        self.range_hi: int = int(range_hi)
        self.root = f"[{self.range_lo},{self.range_hi}]"

        # Start with just the root node; others appear dynamically
        self.nodes = [self.root]
        self.edges = []
        self.node_labels = {self.root: str(self.root)}

    # ----- depth computation -----------------------------------------------

    def _compute_max_depth(self) -> int:
        """Compute the maximum depth of the tree."""
        if not self.nodes:
            return 0
        depth: dict[str | int, int] = {self.root: 0}
        queue = [self.root]
        max_d = 0
        while queue:
            node = queue.pop(0)
            for child in self.children_map.get(node, []):
                depth[child] = depth[node] + 1
                max_d = max(max_d, depth[child])
                queue.append(child)
        return max_d

    # ----- selector helpers ------------------------------------------------

    @staticmethod
    def _node_key(node_id: str | int) -> str:
        return f"node[{node_id}]"

    @staticmethod
    def _edge_key(u: str | int, v: str | int) -> str:
        return f"edge[({u},{v})]"

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for node_id in self.nodes:
            parts.append(self._node_key(node_id))
        for u, v in self.edges:
            parts.append(self._edge_key(u, v))
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True
        return suffix in set(self.addressable_parts())

    def bounding_box(self) -> BoundingBox:
        return BoundingBox(x=0, y=0, width=self.width, height=self.height)

    def emit_svg(self) -> str:
        if not self.nodes:
            return (
                f'<g data-primitive="tree" data-shape="{html_escape(self.name)}">'
                "</g>"
            )

        parts: list[str] = []
        parts.append(
            f'<g data-primitive="tree" data-shape="{html_escape(self.name)}">'
        )

        # Optional label / caption
        if self.label is not None:
            parts.append(
                f'<text x="{self.width // 2}" y="14" '
                f'text-anchor="middle" class="scriba-label" fill="#6c757d">'
                f"{html_escape(str(self.label))}</text>"
            )

        # --- Edge layer (rendered first, below nodes) ---
        parts.append('<g class="scriba-tree-edges">')
        for parent, child in self.edges:
            edge_target = f"{self.name}.{self._edge_key(parent, child)}"
            state = self.get_state(self._edge_key(parent, child))
            edge_colors = svg_style_attrs(state)
            edge_stroke = edge_colors["stroke"]
            edge_sw = "1.5" if state == "idle" else "2"

            if parent in self.positions and child in self.positions:
                x1, y1 = self.positions[parent]
                x2, y2 = self.positions[child]
                parts.append(
                    f'<g data-target="{html_escape(edge_target)}" '
                    f'class="scriba-state-{state}">'
                    f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                    f'fill="none" stroke="{edge_stroke}" '
                    f'stroke-width="{edge_sw}"/>'
                    f"</g>"
                )
        parts.append("</g>")

        # --- Node layer (rendered on top) ---
        parts.append('<g class="scriba-tree-nodes">')
        for node_id in self.nodes:
            if node_id not in self.positions:
                continue
            node_target = f"{self.name}.{self._node_key(node_id)}"
            state = self.get_state(self._node_key(node_id))
            node_colors = svg_style_attrs(state)
            cx, cy = self.positions[node_id]
            node_sw = "1.5" if state == "idle" else "2"
            display_label = self.node_labels.get(node_id, str(node_id))
            parts.append(
                f'<g data-target="{html_escape(node_target)}" '
                f'class="scriba-state-{state}">'
                f'<circle cx="{cx}" cy="{cy}" r="{_NODE_RADIUS}" '
                f'fill="{node_colors["fill"]}" '
                f'stroke="{node_colors["stroke"]}" '
                f'stroke-width="{node_sw}"/>'
                f'<text x="{cx}" y="{cy}" text-anchor="middle" '
                f'dominant-baseline="central" '
                f'fill="{node_colors["text"]}">'
                f"{html_escape(str(display_label))}</text>"
                f"</g>"
            )
        parts.append("</g>")

        parts.append("</g>")
        return "".join(parts)
