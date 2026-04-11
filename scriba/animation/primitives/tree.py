"""Tree primitive with Reingold-Tilford layout and segment tree variants.

Implements ``\\shape{name}{Tree}{root=..., nodes=..., edges=...}`` for BSTs,
segment trees, recursive DP, and tree traversal visualizations.

See ``docs/spec/primitives.md`` section 7 for the authoritative specification.
"""

from __future__ import annotations

import math
from html import escape as html_escape
from typing import Any, Callable, ClassVar

from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    THEME,
    _render_svg_text,
    register_primitive,
    svg_style_attrs,
)

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


# ---------------------------------------------------------------------------
# Tree primitive
# ---------------------------------------------------------------------------


@register_primitive("Tree")
class Tree(PrimitiveBase):
    """Rooted tree primitive with Reingold-Tilford layout.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``T``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
    """

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "node[{id}]": "node by id",
        "edge[({u},{v})]": "edge by endpoints",
        "all": "all nodes and edges",
    }

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

        # Scale node radius with density so dense trees don't overlap
        self._node_radius: int = max(
            12,
            min(
                _NODE_RADIUS,
                int(min(self.width, self.height) / (2 * max(len(self.nodes), 1))),
            ),
        )

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
            raise animation_error(
                "E1430",
                detail="Tree requires 'root' parameter",
                hint="example: Tree{t}{root=\"A\", nodes=[...], edges=[...]}",
            )

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
            raise animation_error(
                "E1431",
                detail="Tree (kind=segtree) requires 'data' parameter",
                hint="example: Tree{t}{kind=\"segtree\", data=[1, 2, 3, 4]}",
            )

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
                "E1432",
                detail=(
                    "Tree (kind=sparse_segtree) requires 'range_lo' and "
                    "'range_hi' parameters"
                ),
                hint="example: Tree{t}{kind=\"sparse_segtree\", range_lo=0, range_hi=1000}",
            )

        self.range_lo: int = int(range_lo)
        self.range_hi: int = int(range_hi)
        self.root = f"[{self.range_lo},{self.range_hi}]"

        # Start with just the root node; others appear dynamically
        self.nodes = [self.root]
        self.edges = []
        self.node_labels = {self.root: str(self.root)}

    # ----- apply commands --------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Process mutation commands from ``\\apply``.

        Supported keys (checked in order): ``add_node``, ``remove_node``,
        ``reparent``. See RFC-001 §4.1 for spec details.
        """
        from scriba.animation.errors import animation_error

        if "add_node" in params:
            spec = params["add_node"]
            if not isinstance(spec, dict) or "id" not in spec or "parent" not in spec:
                raise animation_error(
                    "E1436",
                    detail="add_node requires {id, parent}",
                )
            self._add_node_internal(spec["id"], spec["parent"])
            return

        if "remove_node" in params:
            spec = params["remove_node"]
            if isinstance(spec, (str, int)):
                self._remove_node_internal(spec, cascade=False)
            elif isinstance(spec, dict) and "id" in spec:
                self._remove_node_internal(
                    spec["id"], cascade=bool(spec.get("cascade", False))
                )
            else:
                raise animation_error(
                    "E1436",
                    detail="remove_node requires id or {id, cascade?}",
                )
            return

        if "reparent" in params:
            spec = params["reparent"]
            if not isinstance(spec, dict) or "node" not in spec or "parent" not in spec:
                raise animation_error(
                    "E1435",
                    detail="reparent requires {node, parent}",
                )
            self._reparent_internal(spec["node"], spec["parent"])
            return

    # ----- internal mutation helpers --------------------------------------

    def _relayout(self) -> None:
        """Recompute Reingold-Tilford positions after a mutation."""
        if self.nodes:
            self.positions = reingold_tilford(
                self.root,
                self.children_map,
                width=self.width,
                height=self.height,
            )
        else:
            self.positions = {}

    def _find_parent(self, node_id: str | int) -> str | int | None:
        """Reverse-scan ``children_map`` to find *node_id*'s parent."""
        for parent, kids in self.children_map.items():
            if node_id in kids:
                return parent
        return None

    def _add_node_internal(
        self, node_id: str | int, parent_id: str | int
    ) -> None:
        from scriba.animation.errors import animation_error

        if parent_id not in self.children_map:
            raise animation_error(
                "E1436",
                detail=(
                    f"add_node parent {parent_id!r} is not in the tree"
                ),
                hint="parent must be an existing node id",
            )
        if node_id in self.children_map:
            raise animation_error(
                "E1436",
                detail=f"add_node id {node_id!r} already exists",
                hint="node ids must be unique",
            )

        self.nodes.append(node_id)
        self.edges.append((parent_id, node_id))
        self.children_map[parent_id] = self.children_map[parent_id] + [node_id]
        self.children_map[node_id] = []
        self.node_labels[node_id] = str(node_id)
        self._relayout()

    def _collect_descendants(self, node_id: str | int) -> list[str | int]:
        """Iterative DFS returning *node_id* and all descendants.

        Recursion-free to honor the Wave 4B recursion-DoS lockdown.
        """
        collected: list[str | int] = []
        stack: list[str | int] = [node_id]
        while stack:
            n = stack.pop()
            collected.append(n)
            for child in self.children_map.get(n, []):
                stack.append(child)
        return collected

    def _remove_node_internal(
        self, node_id: str | int, *, cascade: bool
    ) -> None:
        from scriba.animation.errors import animation_error

        if node_id not in self.children_map:
            raise animation_error(
                "E1436",
                detail=f"remove_node target {node_id!r} is not in the tree",
            )

        is_root = node_id == self.root
        kids = list(self.children_map.get(node_id, []))

        if is_root and not cascade:
            raise animation_error(
                "E1434",
                detail="cannot remove root without cascade",
                hint="pass cascade=true to drop the whole tree",
            )

        if kids and not cascade:
            raise animation_error(
                "E1433",
                detail=(
                    f"remove_node {node_id!r} has {len(kids)} child(ren)"
                ),
                hint="pass cascade=true to drop descendants",
            )

        if cascade:
            doomed = set(self._collect_descendants(node_id))
        else:
            doomed = {node_id}

        # Remove doomed nodes from nodes/children_map/node_labels.
        self.nodes = [n for n in self.nodes if n not in doomed]
        for n in list(self.children_map.keys()):
            if n in doomed:
                del self.children_map[n]
        for n in list(self.node_labels.keys()):
            if n in doomed:
                del self.node_labels[n]

        # Remove any edge touching a doomed node.
        self.edges = [
            (p, c) for (p, c) in self.edges if p not in doomed and c not in doomed
        ]

        # Detach node_id from its parent's children list (if any remains).
        for parent, kids_list in self.children_map.items():
            if node_id in kids_list:
                self.children_map[parent] = [
                    k for k in kids_list if k != node_id
                ]

        if is_root and cascade:
            # Tree is fully emptied; leave structures empty.
            self.positions = {}
            return

        self._relayout()

    def _is_ancestor(
        self, ancestor: str | int, descendant: str | int
    ) -> bool:
        """Return True if *ancestor* is on the path from root to *descendant*."""
        current: str | int | None = descendant
        seen: set[str | int] = set()
        while current is not None and current not in seen:
            seen.add(current)
            if current == ancestor:
                return True
            current = self._find_parent(current)
        return False

    def _reparent_internal(
        self, node_id: str | int, new_parent_id: str | int
    ) -> None:
        from scriba.animation.errors import animation_error

        if node_id not in self.children_map:
            raise animation_error(
                "E1436",
                detail=f"reparent node {node_id!r} is not in the tree",
            )
        if new_parent_id not in self.children_map:
            raise animation_error(
                "E1436",
                detail=f"reparent parent {new_parent_id!r} is not in the tree",
            )
        if node_id == self.root:
            raise animation_error(
                "E1435",
                detail="cannot reparent the root node",
            )
        if node_id == new_parent_id:
            raise animation_error(
                "E1435",
                detail="reparent would create a cycle (self-parent)",
            )

        # Cycle check: new_parent_id must not be a descendant of node_id.
        if self._is_ancestor(node_id, new_parent_id):
            raise animation_error(
                "E1435",
                detail="reparent would create a cycle",
                hint=(
                    f"{new_parent_id!r} is a descendant of {node_id!r}"
                ),
            )

        old_parent = self._find_parent(node_id)
        if old_parent is None:
            raise animation_error(
                "E1436",
                detail=f"reparent node {node_id!r} has no parent in the tree",
            )
        if old_parent == new_parent_id:
            # No-op: still relayout to be safe (stable positions expected).
            self._relayout()
            return

        # Detach from old parent.
        self.children_map[old_parent] = [
            k for k in self.children_map[old_parent] if k != node_id
        ]
        # Drop the old edge.
        self.edges = [
            (p, c)
            for (p, c) in self.edges
            if not (p == old_parent and c == node_id)
        ]
        # Attach to new parent.
        self.children_map[new_parent_id] = (
            self.children_map[new_parent_id] + [node_id]
        )
        self.edges.append((new_parent_id, node_id))

        self._relayout()

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
        r = self._node_radius
        return BoundingBox(
            x=0,
            y=0,
            width=self.width + 2 * r,
            height=self.height + 2 * r,
        )

    def emit_svg(self, *, render_inline_tex: Callable[[str], str] | None = None) -> str:
        if not self.nodes:
            return (
                f'<g data-primitive="tree" data-shape="{html_escape(self.name)}">'
                "</g>"
            )

        r = self._node_radius
        parts: list[str] = []
        # Offset by node radius so nodes at edge positions don't clip
        parts.append(
            f'<g data-primitive="tree" data-shape="{html_escape(self.name)}"'
            f' transform="translate({r},{r})">'
        )

        # Optional label / caption
        if self.label is not None:
            parts.append(
                _render_svg_text(
                    str(self.label),
                    self.width // 2,
                    14,
                    fill=THEME["fg_muted"],
                    css_class="scriba-label",
                    text_anchor="middle",
                    fo_width=self.width,
                    fo_height=24,
                    render_inline_tex=render_inline_tex,
                )
            )

        # --- Edge layer (rendered first, below nodes) ---
        parts.append('<g class="scriba-tree-edges">')
        for parent, child in self.edges:
            edge_target = f"{self.name}.{self._edge_key(parent, child)}"
            state = self.get_state(self._edge_key(parent, child))
            # Hidden edges are skipped entirely (Wave 6).
            if state == "hidden":
                continue
            # Also skip edges whose endpoint nodes are hidden.
            if (
                self.get_state(self._node_key(parent)) == "hidden"
                or self.get_state(self._node_key(child)) == "hidden"
            ):
                continue
            edge_colors = svg_style_attrs(state)
            edge_stroke = edge_colors["stroke"]
            edge_sw = "1.5" if state == "idle" else "2"

            if parent in self.positions and child in self.positions:
                px, py = self.positions[parent]
                cx, cy = self.positions[child]
                # Shorten both ends so lines stop at circle boundaries
                x1, y1 = _shorten_line_to_circle(cx, cy, px, py, self._node_radius)
                x2, y2 = _shorten_line_to_circle(px, py, cx, cy, self._node_radius)
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
            # Hidden nodes are omitted entirely (Wave 6).
            if state == "hidden":
                continue
            node_colors = svg_style_attrs(state)
            cx, cy = self.positions[node_id]
            node_sw = "1.5" if state == "idle" else "2"
            # Value-layer override takes precedence over the static label
            # (Wave 6 Agent 7 F1 CRITICAL fix — enables segtree sum updates
            # via ``\apply{T.node["X"]}{value="..."}``).
            override = self.get_value(self._node_key(node_id))
            display_label = (
                override
                if override is not None
                else self.node_labels.get(node_id, str(node_id))
            )
            node_text = _render_svg_text(
                str(display_label),
                cx,
                cy,
                fill=node_colors["text"],
                text_anchor="middle",
                dominant_baseline="central",
                fo_width=self._node_radius * 2,
                fo_height=self._node_radius * 2,
                render_inline_tex=render_inline_tex,
                text_outline=node_colors["fill"],
            )
            parts.append(
                f'<g data-target="{html_escape(node_target)}" '
                f'class="scriba-state-{state}">'
                f'<circle cx="{cx}" cy="{cy}" r="{self._node_radius}" '
                f'fill="{node_colors["fill"]}" '
                f'stroke="{node_colors["stroke"]}" '
                f'stroke-width="{node_sw}"/>'
                f"{node_text}"
                f"</g>"
            )
        parts.append("</g>")

        parts.append("</g>")
        return "".join(parts)
