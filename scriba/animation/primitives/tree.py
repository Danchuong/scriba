"""Tree primitive with Reingold-Tilford layout and segment tree variants.

Implements ``\\shape{name}{Tree}{root=..., nodes=..., edges=...}`` for BSTs,
segment trees, recursive DP, and tree traversal visualizations.

See ``docs/spec/primitives.md`` section 7 for the authoritative specification.
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives._params import coerce_list, scalar_node_ids
from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    _render_svg_text,
    _trace_arrowhead,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._svg_helpers import CellMetrics
from scriba.animation.primitives._types import (
    _NODE_MIN_RADIUS,
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
# nodefit B2: breathing room between adjacent painted node labels when the
# pitch is label-driven (labels wider than _MIN_H_GAP - this gap).
_LABEL_PITCH_GAP = 6

# Regex to parse annotation selectors like "T.node[5]" or "T.node[[0,3]]"
_TREE_NODE_SEL_RE = re.compile(r"^(?P<name>\w+)\.node\[(?P<id>.+)\]$")

# Regex for the second-class link selector "T.link[(u,v)]". Authors reach it on
# the existing selector grammar via the quoted-string form ``T.link["(u,v)"]``,
# which canonicalizes back to this exact key (see scene._selector_to_str), so
# no ``_parse_link`` handler is needed.
_TREE_LINK_SEL_RE = re.compile(
    r"^(?P<name>\w+)\.link\[\((?P<u>[^,]+),(?P<v>[^)]+)\)\]$"
)


def _link_geometry(
    x1: float, y1: float, x2: float, y2: float, radius: float
) -> tuple[str, str]:
    """Curved-arc path + arrowhead polygon points for a second-class link.

    Fail/suffix links are drawn as a dashed quadratic arc bowed off the
    straight ``u->v`` line so they read as a distinct overlay from the tree
    edges beneath them. Returns ``(path_d, arrowhead_points)`` where the tip
    sits on ``v``'s circle boundary, oriented along the arc's end tangent.
    """
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    dx, dy = x2 - x1, y2 - y1
    dist = math.hypot(dx, dy) or 1.0
    # Left-hand perpendicular unit; bow scales with span but has a floor so
    # short links still arc visibly.
    perp_x, perp_y = -dy / dist, dx / dist
    bow = max(20.0, dist * 0.22)
    cx, cy = mx + perp_x * bow, my + perp_y * bow
    # Pull both ends back to the node-circle boundary along the control tangent.
    sdx, sdy = cx - x1, cy - y1
    sd = math.hypot(sdx, sdy) or 1.0
    sx, sy = x1 + radius * sdx / sd, y1 + radius * sdy / sd
    edx, edy = cx - x2, cy - y2
    ed = math.hypot(edx, edy) or 1.0
    ex, ey = x2 + radius * edx / ed, y2 + radius * edy / ed
    path_d = f"M{sx:.1f},{sy:.1f} Q{cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}"
    head = _trace_arrowhead((cx, cy), (ex, ey))
    return path_d, head


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
    # \apply structural verbs (per-node value= — incl. segtree lazy tags —
    # is handled generically via set_value, not here).
    APPLY_KEYS: ClassVar[frozenset[str]] = frozenset(
        {"add_node", "remove_node", "reparent", "add_link", "remove_link"}
    )

    # DECORATE v4: a \trace threads a polyline through node centres — in a
    # hierarchical layout the straight segment between adjacent node centres IS
    # the edge, so this is the "follow the path down the tree" gesture.
    # resolve_annotation_point already returns the node centre.
    supports_trace: ClassVar[bool] = True

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "node[{id}]": "node by id",
        "edge[({u},{v})]": "edge by endpoints",
        "link[({u},{v})]": "second-class (fail/suffix) link by endpoints",
        "all": "all nodes and edges",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "root",
        "nodes",
        "edges",
        "links",
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

        # Char-edge labels: a string glyph shown on the parent->child edge
        # (trie / automaton transitions). Populated from 3-tuple ``edges`` by
        # ``_init_standard``; the derived kinds (segtree/heap/…) leave it empty.
        self.edge_labels: dict[tuple[str | int, str | int], str] = {}

        # Build tree structure depending on kind
        if self.kind == "segtree":
            self._init_segtree(params)
        elif self.kind == "sparse_segtree":
            self._init_sparse_segtree(params)
        elif self.kind == "heap":
            self._init_heap(params)
        else:
            self._init_standard(params)

        # Build children map from edges
        self.children_map: dict[str | int, list[str | int]] = {
            n: [] for n in self.nodes
        }
        for parent, child in self.edges:
            if parent in self.children_map:
                self.children_map[parent].append(child)

        # Second-class links (fail/suffix links). These are a presentation
        # overlay only: they are deliberately kept OUT of ``children_map`` so
        # Reingold-Tilford never sees them and node layout is identical whether
        # or not links are present (gap-new-substrates §6.1).
        self.links: list[tuple[str | int, str | int]] = []
        for lk in params.get("links", []):
            u, v = str(lk[0]), str(lk[1])
            if u not in self.children_map or v not in self.children_map:
                raise _animation_error(
                    "E1436",
                    detail=(
                        f"link ({u!r}, {v!r}) references a node that is not "
                        "in the tree"
                    ),
                    hint="both link endpoints must be existing node ids",
                )
            if (u, v) not in self.links:
                self.links.append((u, v))

        # nodefit: seed the cross-frame-max label map with the static display
        # labels (segtree "[l,r]=v", ids); per-frame value= overrides grow it
        # via set_value during the prescan.
        for _n in self.nodes:
            self.note_node_label(
                self._node_key(_n), self.node_labels.get(_n, str(_n))
            )

        # Compute viewport dimensions based on tree size
        node_count = len(self.nodes)
        depth = self._compute_max_depth()
        self.width: int = self._layout_width()
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

        # Node ids are normalized to ``str`` so numeric literals
        # (``nodes=[8,3,10]``) and string refs (``parent="3"``) match — the
        # id ``3`` and ``"3"`` are the same node.  Labels still display the
        # original text via ``str``.
        self.root: str | int = str(root)
        # nodes= takes scalar ids. A pairs/list entry (nodes=[["r","5"]]) would
        # be str()-mangled into a bogus single id, silently dropping the real
        # node — reject it (E1104) and point at the per-node value recipe.
        self.nodes: list[str | int] = scalar_node_ids(
            params.get("nodes", []),
            "E1104",
            detail=(
                "Tree 'nodes' entries must be scalar ids, got a list/tuple "
                "(the pairs form 'nodes=[[id, value], ...]' is not supported)"
            ),
            hint=(
                'nodes= takes scalar ids (nodes=["r", "c"]); set a per-node '
                'display value with \\apply{T.node["c"]}{value="..."}'
            ),
        )
        # Edges stay 2-tuples ``(parent, child)`` so every existing code path
        # (children_map, layout, emit) is untouched. A 3-tuple ``(p, c, "a")``
        # peels its third element off into ``edge_labels`` as a *string* — no
        # ``float()`` coercion, unlike Graph's weighted edges.
        raw_edges = params.get("edges", [])
        self.edges: list[tuple[str | int, str | int]] = []
        for e in raw_edges:
            parent, child = str(e[0]), str(e[1])
            self.edges.append((parent, child))
            if len(e) >= 3 and e[2] is not None:
                self.edge_labels[(parent, child)] = str(e[2])
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

    def _init_heap(self, params: dict[str, Any]) -> None:
        """Initialize a binary heap laid out as a complete binary tree.

        The heap is defined entirely by its backing array ``data``: index
        ``i`` (0-based) is the parent of ``2i+1`` and ``2i+2``, with the root
        at index ``0``. Node *ids* are the array indices — so selectors read
        ``h.node[i]`` — while each node's *label* shows the stored value. A
        sift/swap step therefore relabels two nodes via
        ``\\apply{h.node[i]}{value=...}`` (the value-layer override read in
        :meth:`emit_svg`) without moving them; Reingold-Tilford positions
        stay put.

        Like ``kind=segtree``, the structure is derived from ``data`` alone;
        any author-supplied ``nodes``/``edges`` are ignored because the
        complete-binary-tree shape is fully implied by the array.
        """
        data = params.get("data")
        if not data:
            raise _animation_error(
                "E1438",
                detail="Tree (kind=heap) requires a non-empty 'data' parameter",
                hint="example: Tree{h}{kind=\"heap\", data=[9, 7, 8, 3, 5, 6, 4]}",
            )

        data = coerce_list(
            data,
            "E1438",
            detail=f"Tree (kind=heap) 'data' must be a list, got {data!r}",
            hint="example: Tree{h}{kind=\"heap\", data=[9, 7, 8, 3, 5, 6, 4]}",
        )
        n = len(data)
        # Node ids are the array indices (str-normalized to match the other
        # kinds), so ``h.node[i]`` addresses the value at array slot i.
        self.root = "0"
        self.nodes = [str(i) for i in range(n)]
        self.edges = []
        for i in range(n):
            for child in (2 * i + 1, 2 * i + 2):
                if child < n:
                    self.edges.append((str(i), str(child)))
        self.node_labels: dict[str | int, str] = {
            str(i): str(data[i]) for i in range(n)
        }

    # ----- apply commands --------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Process mutation commands from ``\\apply``.

        Supported keys (checked in order): ``add_node``, ``remove_node``,
        ``reparent``, ``add_link``, ``remove_link``. See RFC-001 §4.1 for spec
        details; ``add_link``/``remove_link`` manage the second-class
        (fail/suffix) link overlay.
        """
        if "add_node" in params:
            spec = params["add_node"]
            if not isinstance(spec, dict) or "id" not in spec or "parent" not in spec:
                raise _animation_error(
                    "E1436",
                    detail="add_node requires {id, parent}",
                )
            self._add_node_internal(spec["id"], spec["parent"], spec.get("char"))
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
            self._reparent_internal(
                spec["node"], spec["parent"], index=spec.get("index")
            )
            return

        if "add_link" in params:
            spec = params["add_link"]
            if not isinstance(spec, dict) or "from" not in spec or "to" not in spec:
                raise _animation_error(
                    "E1436",
                    detail="add_link requires {from, to}",
                )
            self._add_link_internal(spec["from"], spec["to"])
            return

        if "remove_link" in params:
            spec = params["remove_link"]
            if not isinstance(spec, dict) or "from" not in spec or "to" not in spec:
                raise _animation_error(
                    "E1436",
                    detail="remove_link requires {from, to}",
                )
            self._remove_link_internal(spec["from"], spec["to"])
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
        self, node_id: str | int, parent_id: str | int,
        char: str | int | None = None,
    ) -> None:
        # Match the str-normalized node ids set up at construction.
        node_id = str(node_id)
        parent_id = str(parent_id)
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
        # ``char`` labels the new parent->child edge (trie / automaton growth).
        if char is not None:
            self.edge_labels[(parent_id, node_id)] = str(char)
        self._relayout()

    def _add_link_internal(
        self, u: str | int, v: str | int
    ) -> None:
        u, v = str(u), str(v)
        if u not in self.children_map or v not in self.children_map:
            raise _animation_error(
                "E1436",
                detail=(
                    f"add_link ({u!r}, {v!r}) references a node that is not "
                    "in the tree"
                ),
                hint="both link endpoints must be existing node ids",
            )
        # Idempotent: a link is an unordered-of-meaning but directed-of-draw
        # overlay keyed by (from, to); re-adding the same pair is a no-op.
        if (u, v) not in self.links:
            self.links.append((u, v))
        # No relayout — links never enter children_map or affect geometry.

    def _remove_link_internal(
        self, u: str | int, v: str | int
    ) -> None:
        u, v = str(u), str(v)
        if (u, v) not in self.links:
            raise _animation_error(
                "E1436",
                detail=f"remove_link: no link between {u!r} and {v!r}",
            )
        self.links = [lk for lk in self.links if lk != (u, v)]

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
        node_id = str(node_id)
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

        # Drop char-labels for edges that no longer exist, and any link that
        # touches a removed node (no dangling overlay to a vanished node).
        self.edge_labels = {
            (p, c): lbl
            for (p, c), lbl in self.edge_labels.items()
            if p not in doomed and c not in doomed
        }
        self.links = [
            (p, c) for (p, c) in self.links if p not in doomed and c not in doomed
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
        self,
        node_id: str | int,
        new_parent_id: str | int,
        index: int | None = None,
    ) -> None:
        node_id = str(node_id)
        new_parent_id = str(new_parent_id)
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
            # The root is an ancestor of every other node, so attaching it
            # under any node would close a cycle.
            raise _animation_error(
                "E1433",
                detail="reparent would create a cycle (root node)",
            )
        if node_id == new_parent_id:
            raise _animation_error(
                "E1433",
                detail="reparent would create a cycle (self-parent)",
            )

        # Cycle check: new_parent_id must not be a descendant of node_id.
        if self._is_ancestor(node_id, new_parent_id):
            raise _animation_error(
                "E1433",
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
        # The old parent->child edge label no longer applies.
        self.edge_labels.pop((old_parent, node_id), None)
        # Attach to new parent. ``index`` places the node among the new
        # parent's children so a BST rotation can put it on the LEFT
        # (index=0) instead of always rightmost; omit for append.
        siblings = list(self.children_map[new_parent_id])
        if index is None:
            siblings.append(node_id)
        else:
            siblings.insert(max(0, min(int(index), len(siblings))), node_id)
        self.children_map[new_parent_id] = siblings
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

    @staticmethod
    def _link_key(u: str | int, v: str | int) -> str:
        return f"link[({u},{v})]"

    def _node_pitch(self) -> int:
        """Horizontal leaf pitch (nodefit B2): the historic ``_MIN_H_GAP``
        floor, grown to the widest painted node label plus a small gap —
        uniform, because Reingold-Tilford gives every leaf one unit of the
        usable width. max() keeps the pitch (and every byte) unchanged when
        labels fit."""
        widest = max(
            (
                self.cross_frame_max_label_width(self._node_key(n))
                for n in self.nodes
            ),
            default=0,
        )
        return max(_MIN_H_GAP, widest + _LABEL_PITCH_GAP)

    def _layout_width(self) -> int:
        """Canvas width: the historic node-count formula, widened (nodefit
        B2) only when the widest painted label needs more LEAF pitch than
        the historic width already provides — RT spreads the usable width
        across leaves, so a node-count canvas usually carries slack and
        must not churn when labels already fit it."""
        base = len(self.nodes) * _MIN_H_GAP + 2 * _PADDING
        leaves = sum(1 for n in self.nodes if not self.children_map.get(n))
        need = max(1, leaves) * self._node_pitch() + 2 * _PADDING
        return max(_DEFAULT_WIDTH, base, need)

    def _nodefit_regrow(self) -> None:
        """Widen the canvas to the grown label map and re-run RT.

        Called from ``set_value`` only when a node's cross-frame max grew;
        the prescan replays every frame BEFORE the first viewbox read, so
        the geometry settles pre-measure and stays frame-stable (R-32).
        Only the LABEL-driven need may exceed the current width — the
        node-count base stays frozen at its __init__ value (add_node has
        never re-derived the canvas; re-deriving it here would move the
        tree mid-scene). Radius frozen too — glyph stability."""
        leaves = sum(1 for n in self.nodes if not self.children_map.get(n))
        need = max(1, leaves) * self._node_pitch() + 2 * _PADDING
        if need > self.width:
            self.width = need
            self._relayout()

    def set_value(self, suffix: str, value: str) -> None:
        super().set_value(suffix, value)
        # nodefit: a node's value= paints centered in the circle at 14 px —
        # grow the cross-frame-max map only when the set actually landed
        # (the base soft-drops invalid selectors with E1115).
        if suffix.startswith("node[") and self.get_value(suffix) == value:
            before = self.cross_frame_max_label_width(suffix)
            self.note_node_label(suffix, value)
            if self.cross_frame_max_label_width(suffix) > before:
                self._nodefit_regrow()

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
        for u, v in self.links:
            parts.append(self._link_key(u, v))
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True
        return suffix in set(self.addressable_parts())

    def _trace_cell_suffix(self, cell) -> str:
        """Map a ``\\trace`` ``cells=`` entry to a node selector suffix.

        Tree traces address nodes by id (string) or index, so the entry becomes
        ``node[{id}]`` verbatim — ``resolve_annotation_point`` then handles the
        str-then-int id lookup."""
        return f"node[{cell}]"

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

        # A ``T.link[(u,v)]`` anchor sits at the midpoint of the two node
        # centres (annotation pills/arrows attach there, not on the bowed arc).
        lm = _TREE_LINK_SEL_RE.match(selector)
        if lm and lm.group("name") == self.name:
            pu = self._node_center(lm.group("u"))
            pv = self._node_center(lm.group("v"))
            if pu is not None and pv is not None:
                return ((pu[0] + pv[0]) / 2.0, (pu[1] + pv[1]) / 2.0)
        return None

    def _node_center(self, raw_id: str) -> tuple[float, float] | None:
        """Resolve a raw node-id string to its ``(x, y)`` centre, trying the
        str key first then an int fallback (mirrors the node-selector path)."""
        node_id: str | int = raw_id
        if node_id not in self.positions:
            try:
                node_id = int(raw_id)
            except ValueError:
                return None
        if node_id in self.positions:
            cx, cy = self.positions[node_id]
            return (float(cx), float(cy))
        return None

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit in a callout lane below the whole tree
        (clear of the lowest node), with a leader line back to the node. The
        baseline is the content height; every node's ``cy + radius`` stays at or
        above it (Reingold-Tilford keeps nodes inside ``height``)."""
        return float(self.height)

    def resolve_annotation_box(self, selector: str) -> "BoundingBox | None":
        """Annotated node's circle AABB (Layer C) so a ``position=below`` pill
        gets a leader line and the placer treats the node as a MUST blocker.
        Coords are content-local (pre-frame-translate), matching
        ``resolve_annotation_point``.

        Scoped to selectors that actually carry a below pill: base.py feeds the
        returned width to *every* position pill as ``cell_width`` (which drives
        the R-07/R-08 spanning-leader), and a node's diameter is narrow enough
        that an above/left/right pill would spuriously trip that leader. Gating
        on an actual below pill keeps the box's effect limited to the below lane,
        so existing above/left/right corpus pills stay byte-stable."""
        if not self._target_has_below_pill(selector):
            return None
        pt = self.resolve_annotation_point(selector)
        if pt is None:
            return None
        cx, cy = pt
        r = self._node_radius
        return BoundingBox(
            x=int(cx - r), y=int(cy - r), width=int(2 * r), height=int(2 * r)
        )

    def _annotation_cell_metrics(self) -> "CellMetrics":
        """Phase D/2 CellMetrics proxy — node diameter stands in as the local
        "cell" scale (activates 2D stagger-flip). Single source for render
        AND measurement."""
        _diam = float(self._node_radius * 2)
        return CellMetrics(
            cell_width=_diam,
            cell_height=_diam,
            grid_cols=len(self.nodes) or 1,
            grid_rows=1,
            origin_x=0.0,
            origin_y=0.0,
        )

    def _h_label_pad(self) -> "tuple[int, int]":
        """Base pads plus the painted node-label overhang (nodefit A2).

        Defensive for Tree — the canvas already widens with node count — but
        a very wide value=/label on an outer leaf can still overhang the
        frame. Same fold as Graph: ``(r + left_pad + cx) ± tw/2`` must stay
        inside ``[0, width]``; both folds are int 0 when every label fits.
        """
        left_pad, right_reach = super()._h_label_pad()
        r = self._node_radius
        content_w = self.width + 2 * r
        lbl_l = 0
        lbl_r = 0
        for node_id, (cx, _cy) in self.positions.items():
            tw = self.cross_frame_max_label_width(self._node_key(node_id))
            if tw <= 2 * r:
                continue  # fits inside the circle -> inside the frame
            half = tw / 2.0
            lbl_l = max(lbl_l, int(math.ceil(half - (r + cx))))
            lbl_r = max(lbl_r, int(math.ceil(r + cx + half - content_w)))
        if lbl_l > 0:
            left_pad = max(left_pad, lbl_l)
        if lbl_r > 0:
            right_reach = max(right_reach, content_w + lbl_r)
        return left_pad, right_reach

    def bounding_box(self) -> BoundingBox:
        r = self._node_radius
        arrow_above = self._reserved_arrow_above()
        # Defect 6 — the caption width participates in the footprint so a
        # caption wider than the tree is folded into the box, not clipped.
        # Keep the int footprint when no widening is needed so the downstream
        # transform stays byte-stable (only a genuinely wider caption grows it).
        content_w = float(self.width + 2 * r)
        core_w = max(self.width + 2 * r, self._caption_block_width(content_w))
        label_h = self._top_caption_band(content_w)
        # #1: reserve horizontal room for position=left/right pills. Both pads
        # are 0 (int) without left/right pills, so the box stays byte-stable.
        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)
        # #2: position=below pills occupy a callout lane below the content; the
        # lane is 0 px without below pills, so this stays byte-stable too.
        return BoundingBox(
            x=0,
            y=0,
            width=w,
            height=self.height + 2 * r + arrow_above + self._below_lane_height() + label_h,
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
        arrow_above = self._reserved_arrow_above()
        # #1: shift content right by left_pad so position=left pills clear the
        # viewBox. left_pad is 0 (int) without left pills, so the transform is
        # byte-identical to the pre-#1 "translate({r},{ty})".
        left_pad, _right = self._h_label_pad()

        parts: list[str] = []
        # Offset by node radius so nodes at edge positions don't clip.
        # When annotations with arrows exist, shift content down by
        # arrow_above so curves have room above the tree.
        ty = r + arrow_above
        parts.append(
            f'<g data-primitive="tree" data-shape="{_escape_xml(self.name)}"'
            f' transform="translate({r + left_pad},{ty})">'
        )

        # Optional label / caption
        label_offset = 0
        if self.label is not None:
            content_w = float(self.width + 2 * r)
            label_offset = self._top_caption_band(content_w)
            self._emit_top_caption(
                parts,
                content_width=content_w,
                footprint_width=int(self.bounding_box().width),
                frame_radius=r,
                render_inline_tex=render_inline_tex,
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
                # Char-edge label (trie / automaton transition glyph), nudged
                # off the stroke so the line does not strike through it.
                label = self.edge_labels.get((parent, child))
                if label is not None:
                    dxl, dyl = (x2 - x1), (y2 - y1)
                    dl = math.hypot(dxl, dyl) or 1.0
                    nx, ny = -dyl / dl, dxl / dl
                    lmx = (x1 + x2) / 2.0 + nx * 7.0
                    lmy = (y1 + y2) / 2.0 + ny * 7.0
                    parts.append(
                        f'<text class="scriba-tree-edge-label" '
                        f'x="{lmx:.1f}" y="{lmy:.1f}" text-anchor="middle" '
                        f'dominant-baseline="central" font-size="11" '
                        f'fill="{edge_colors["text"]}">'
                        f"{_escape_xml(str(label))}</text>"
                    )
        parts.append("</g>")

        # DECORATE v4: \trace polylines thread node centres, painted between the
        # edges and the nodes so the circles sit on top of the swept path. Same
        # coordinate frame as the annotation arrows below.
        self.emit_traces_under(parts)

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
                font_size="14",
                fo_width=self._node_radius * 2,
                fo_height=self._node_radius * 2,
                render_inline_tex=render_inline_tex,
                clip_overflow=False,
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

        # --- Second-class link overlay (fail/suffix links) ---
        # Rendered above nodes but below annotation arrows. Gated on non-empty
        # ``links`` so link-free trees (and every derived kind) stay
        # byte-identical to the pre-feature output.
        if self.links:
            parts.append('<g class="scriba-tree-links">')
            for u, v in self.links:
                link_state = self.get_state(self._link_key(u, v))
                if link_state == "hidden":
                    continue
                if (
                    self.get_state(self._node_key(u)) == "hidden"
                    or self.get_state(self._node_key(v)) == "hidden"
                ):
                    continue
                if u not in self.positions or v not in self.positions:
                    continue
                link_target = f"{self.name}.{self._link_key(u, v)}"
                link_colors = svg_style_attrs(link_state)
                link_stroke = link_colors["stroke"]
                ux, uy = self.positions[u]
                vx, vy = self.positions[v]
                path_d, head = _link_geometry(ux, uy, vx, vy, self._node_radius)
                parts.append(
                    f'<g data-target="{_escape_xml(link_target)}" '
                    f'class="scriba-tree-link {state_class(link_state)}">'
                    f'<path d="{path_d}" fill="none" stroke="{link_stroke}" '
                    f'stroke-width="1.5" stroke-dasharray="5,4"/>'
                    f'<polygon points="{head}" fill="{link_stroke}"/>'
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
                cell_metrics=self._annotation_cell_metrics(),
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
