"""Tree primitive with Reingold-Tilford layout and segment tree variants.

Implements ``\\shape{name}{Tree}{root=..., nodes=..., edges=...}`` for BSTs,
segment trees, recursive DP, and tree traversal visualizations.

See ``docs/spec/primitives.md`` section 7 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    THEME,
    _escape_xml,
    _render_svg_text,
    arrow_height_above,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._types import (
    _NODE_MIN_RADIUS,
    _PRIMITIVE_LABEL_Y,
)
from scriba.animation.primitives.tree_layout import *  # noqa: F401, F403
from scriba.animation.primitives.tree_layout import (
    _build_segtree,
    _reingold_tilford,
    _shorten_line_to_circle,
)

__all__ = ["Tree"]

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
_LABEL_HEIGHT = 28  # vertical space reserved for the caption when label is set

# Regex to parse annotation selectors like "T.node[5]" or "T.node[[0,3]]"
_TREE_NODE_SEL_RE = re.compile(r"^(?P<name>\w+)\.node\[(?P<id>.+)\]$")


# ---------------------------------------------------------------------------
# Tree primitive
# ---------------------------------------------------------------------------


@register_primitive("Tree")
@_protocol_register
class Tree(PrimitiveBase):
    """Rooted tree primitive with Reingold-Tilford layout.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``T``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
    """

    primitive_type = "tree"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "node[{id}]": "node by id",
        "edge[({u},{v})]": "edge by endpoints",
        "all": "all nodes and edges",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "root",
        "nodes",
        "edges",
        "kind",
        "data",
        "range_lo",
        "range_hi",
        "show_sum",
        "label",
    })

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
            _NODE_MIN_RADIUS,
            min(
                _NODE_RADIUS,
                int(min(self.width, self.height) / (2 * max(len(self.nodes), 1))),
            ),
        )
        self._arrow_cell_height = float(self._node_radius * 2)
        self._arrow_layout = "2d"
        self._arrow_shorten = float(self._node_radius)

        # Compute positions
        if self.nodes:
            self.positions: dict[str | int, tuple[int, int]] = _reingold_tilford(
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
        root = params.get("root")
        if root is None:
            raise _animation_error(
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
        data = params.get("data")
        if data is None:
            raise _animation_error(
                "E1431",
                detail="Tree (kind=segtree) requires 'data' parameter",
                hint="example: Tree{t}{kind=\"segtree\", data=[1, 2, 3, 4]}",
            )

        data = list(data)
        root_id, nodes, edges, sums = _build_segtree(data)
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
        range_lo = params.get("range_lo")
        range_hi = params.get("range_hi")
        if range_lo is None or range_hi is None:
            raise _animation_error(
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
        if "add_node" in params:
            spec = params["add_node"]
            if not isinstance(spec, dict) or "id" not in spec or "parent" not in spec:
                raise _animation_error(
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
                raise _animation_error(
                    "E1436",
                    detail="remove_node requires id or {id, cascade?}",
                )
            return

        if "reparent" in params:
            spec = params["reparent"]
            if not isinstance(spec, dict) or "node" not in spec or "parent" not in spec:
                raise _animation_error(
                    "E1435",
                    detail="reparent requires {node, parent}",
                )
            self._reparent_internal(spec["node"], spec["parent"])
            return

    # ----- internal mutation helpers --------------------------------------

    def _relayout(self) -> None:
        """Recompute Reingold-Tilford positions after a mutation."""
        if self.nodes:
            self.positions = _reingold_tilford(
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
        if parent_id not in self.children_map:
            raise _animation_error(
                "E1436",
                detail=(
                    f"add_node parent {parent_id!r} is not in the tree"
                ),
                hint="parent must be an existing node id",
            )
        if node_id in self.children_map:
            raise _animation_error(
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
        if node_id not in self.children_map:
            raise _animation_error(
                "E1436",
                detail=f"remove_node target {node_id!r} is not in the tree",
            )

        is_root = node_id == self.root
        kids = list(self.children_map.get(node_id, []))

        if is_root and not cascade:
            raise _animation_error(
                "E1434",
                detail="cannot remove root without cascade",
                hint="pass cascade=true to drop the whole tree",
            )

        if kids and not cascade:
            raise _animation_error(
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
        if node_id not in self.children_map:
            raise _animation_error(
                "E1436",
                detail=f"reparent node {node_id!r} is not in the tree",
            )
        if new_parent_id not in self.children_map:
            raise _animation_error(
                "E1436",
                detail=f"reparent parent {new_parent_id!r} is not in the tree",
            )
        if node_id == self.root:
            raise _animation_error(
                "E1435",
                detail="cannot reparent the root node",
            )
        if node_id == new_parent_id:
            raise _animation_error(
                "E1435",
                detail="reparent would create a cycle (self-parent)",
            )

        # Cycle check: new_parent_id must not be a descendant of node_id.
        if self._is_ancestor(node_id, new_parent_id):
            raise _animation_error(
                "E1435",
                detail="reparent would create a cycle",
                hint=(
                    f"{new_parent_id!r} is a descendant of {node_id!r}"
                ),
            )

        old_parent = self._find_parent(node_id)
        if old_parent is None:
            raise _animation_error(
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

    # ----- Position tracking ------------------------------------------------

    def get_node_positions(self) -> dict[str, tuple[int, int]]:
        """Return a mapping of fully-qualified node targets to ``(x, y)`` positions.

        Keys use the form ``"{name}.node[{id}]"`` so they align with the
        ``data-target`` attributes emitted by :meth:`emit_svg`.
        """
        result: dict[str, tuple[int, int]] = {}
        for node_id, pos in self.positions.items():
            target = f"{self.name}.{self._node_key(node_id)}"
            result[target] = pos
        return result

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

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Map ``"T.node[5]"`` to the SVG ``(x, y)`` center of that node.

        Coordinates include the ``translate(r, r)`` offset applied by
        :meth:`emit_svg` so arrow endpoints line up with rendered nodes.
        """
        m = _TREE_NODE_SEL_RE.match(selector)
        if m and m.group("name") == self.name:
            raw_id = m.group("id")
            # Try to match as-is first (string node ids), then as int
            node_id: str | int = raw_id
            if node_id not in self.positions:
                try:
                    node_id = int(raw_id)
                except ValueError:
                    return None
            if node_id in self.positions:
                cx, cy = self.positions[node_id]
                # Coordinates are in the local space of the translated
                # group emitted by emit_svg; no extra offset needed.
                return (float(cx), float(cy))
        return None

    def bounding_box(self) -> BoundingBox:
        r = self._node_radius
        arrow_above = arrow_height_above(
            self._annotations,
            self.resolve_annotation_point,
            cell_height=float(self._node_radius * 2),
            layout="2d",
        )
        label_h = _LABEL_HEIGHT if self.label is not None else 0
        return BoundingBox(
            x=0,
            y=0,
            width=self.width + 2 * r,
            height=self.height + 2 * r + arrow_above + label_h,
        )

    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        if not self.nodes:
            return (
                f'<g data-primitive="tree" data-shape="{_escape_xml(self.name)}">'
                "</g>"
            )

        r = self._node_radius
        effective_anns = self._annotations
        arrow_above = arrow_height_above(
            effective_anns,
            self.resolve_annotation_point,
            cell_height=float(self._node_radius * 2),
            layout="2d",
        )

        parts: list[str] = []
        # Offset by node radius so nodes at edge positions don't clip.
        # When annotations with arrows exist, shift content down by
        # arrow_above so curves have room above the tree.
        ty = r + arrow_above
        parts.append(
            f'<g data-primitive="tree" data-shape="{_escape_xml(self.name)}"'
            f' transform="translate({r},{ty})">'
        )

        # Optional label / caption
        label_offset = 0
        if self.label is not None:
            label_offset = _LABEL_HEIGHT
            parts.append(
                _render_svg_text(
                    str(self.label),
                    self.width // 2,
                    _PRIMITIVE_LABEL_Y,
                    fill=THEME["fg_muted"],
                    css_class="scriba-primitive-label",
                    text_anchor="middle",
                    fo_width=self.width,
                    fo_height=24,
                    render_inline_tex=render_inline_tex,
                )
            )

        # Shift edges + nodes below the label when present
        if label_offset:
            parts.append(f'<g transform="translate(0,{label_offset})">')

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
                    f'<g data-target="{_escape_xml(edge_target)}" '
                    f'class="{state_class(state)}">'
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
            # Wave 9 — the text halo that keeps overflowing node labels
            # readable (e.g. "[0,3]=11" inside a 22-pixel-radius circle)
            # is now handled by the CSS cascade in
            # scriba-scene-primitives.css. The old inline ``text_outline=``
            # parameter burned a hex color into the SVG stroke attribute
            # that didn't flip in dark mode; the CSS approach uses
            # ``var(--scriba-state-*-fill)`` so the halo follows the
            # theme and the per-state fill changes automatically.
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
            )
            parts.append(
                f'<g data-target="{_escape_xml(node_target)}" '
                f'data-node-x="{cx}" data-node-y="{cy}" '
                f'class="{state_class(state)}">'
                f'<circle cx="{cx}" cy="{cy}" r="{self._node_radius}" '
                f'fill="{node_colors["fill"]}" '
                f'stroke="{node_colors["stroke"]}" '
                f'stroke-width="{node_sw}"/>'
                f"{node_text}"
                f"</g>"
            )
        parts.append("</g>")

        # --- Annotation arrows (rendered on top of everything) ---
        if effective_anns:
            arrow_lines: list[str] = []
            self.emit_annotation_arrows(
                arrow_lines,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
            )
            parts.extend(arrow_lines)

        # Close the label-offset group if present
        if label_offset:
            parts.append("</g>")

        parts.append("</g>")
        return "".join(parts)

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []
