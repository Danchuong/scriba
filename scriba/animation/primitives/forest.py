"""Forest primitive — a multi-root forest for Disjoint Set Union (DSU).

Renders ``\\shape{name}{Forest}{nodes=[...]}`` as N independent
Reingold-Tilford trees packed side by side. ``\\apply{name}{union={a, b}}``
attaches the root of ``b``'s tree under the root of ``a``'s tree, growing one
tree and dropping the number of roots by one.

Design stake (gap-motion-identity §9(ii), gap-dsu-forest §6 Phase 2)
-------------------------------------------------------------------
A node's identity key is its **intrinsic id alone** — ``{name}.node[{id}]`` —
and never encodes parent / root / DSU-set. A ``union`` re-parents a whole
subtree but leaves every node's ``data-target`` untouched, so the differ sees
the same identities in a new position and emits ``position_move`` (a glide),
not element_add/remove (a pop). Keying by root would change the key of every
node in a merged subtree on each union and destroy that identity. This is the
one load-bearing design decision of the primitive.

Envelope (R-32 / R-42 / LinkedList lesson)
------------------------------------------
Node positions are recomputed each frame from the parent array, but the
reported ``bounding_box`` follows a **monotonic envelope** (``_envelope_width``
/ ``_envelope_height``) grown by ``apply_command`` and by the structural
prescan (``_structural_prescan = True``). A union deepens a tree (height
grows) while the total horizontal footprint only shrinks (leaf columns are
non-increasing under union), so the prescan replays every union before frame 0
and the envelope reaches its timeline maximum before the first frame is
measured — the box never jumps mid-animation.

The mutable structural state lives in ``self.values`` (a DSU parent array) so
the structural prescan's snapshot/restore in ``_prescan_value_widths`` returns
the forest to its declared state after replaying unions, exactly as it does for
LinkedList's ``values`` list.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives._params import coerce_list
from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    _render_svg_text,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives.tree_layout import (
    _reingold_tilford,
    _shorten_line_to_circle,
)

__all__ = ["Forest"]

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_NODE_RADIUS = 18
_LAYER_GAP = 60  # vertical distance between tree depths
_H_GAP = 56  # horizontal distance between sibling columns within a tree
_TREE_GAP = 56  # horizontal gap between adjacent trees
_PADDING = 30  # must match tree_layout._PADDING so wT/hT map to fixed gaps
_EDGE_STROKE_WIDTH = 1.5

# Selector regexes (matched against the full ``name.suffix`` string).
_FOREST_NODE_SEL_RE = re.compile(r"^(?P<name>\w+)\.node\[(?P<id>.+)\]$")
_FOREST_EDGE_SEL_RE = re.compile(
    r"^(?P<name>\w+)\.edge\[\((?P<u>[^,]+),(?P<v>[^)]+)\)\]$"
)


# ---------------------------------------------------------------------------
# Forest primitive
# ---------------------------------------------------------------------------


@register_primitive("Forest")
@_protocol_register
class Forest(PrimitiveBase):
    """Multi-root forest primitive for DSU / union-find visualisations.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``f``).
    params:
        ``nodes`` (required, >=1) — each node starts as its own single-node
        tree. ``edges`` (optional) — ``[(parent, child), ...]`` initial forest
        structure (validated acyclic, at most one parent per node). ``label``
        — optional caption.
    """

    primitive_type = "forest"

    # opt-in: _prescan_value_widths replays union apply_params so the envelope
    # (_envelope_height) reaches its timeline max before frame 0 is measured.
    # Safe because the structural state lives in self.values (a list), which
    # the prescan snapshots and restores like LinkedList's values.
    _structural_prescan: bool = True

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "node[{id}]": "node by id",
        "edge[({u},{v})]": "parent->child edge by endpoints",
        "all": "all nodes and edges",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "nodes",
        "edges",
        "label",
    })

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        raw_nodes = params.get("nodes")
        if not raw_nodes:
            raise _animation_error(
                "E1508",
                detail="Forest requires a non-empty 'nodes' list",
                hint="example: Forest{f}{nodes=[0, 1, 2, 3]}",
            )
        raw_nodes = coerce_list(
            raw_nodes,
            "E1508",
            detail=f"Forest 'nodes' must be a list, got {raw_nodes!r}",
            hint="example: Forest{f}{nodes=[0, 1, 2, 3]}",
        )

        # Node ids are normalized to str so numeric literals (nodes=[0,1,2])
        # and string refs (union={a="1"}) address the same node. Order is the
        # declared order and never changes — Forest grows edges via union, not
        # nodes.
        self.node_ids: list[str] = [str(n) for n in raw_nodes]
        seen: set[str] = set()
        for nid in self.node_ids:
            if nid in seen:
                raise _animation_error(
                    "E1508",
                    detail=f"Forest node id {nid!r} is declared more than once",
                    hint="node ids must be unique",
                )
            seen.add(nid)
        self._index: dict[str, int] = {
            nid: i for i, nid in enumerate(self.node_ids)
        }
        self.node_labels: dict[str, str] = {nid: nid for nid in self.node_ids}

        # DSU parent array: values[i] is the parent id of node_ids[i]; a node
        # is a root iff it is its own parent. This is the single mutable
        # structural state, and the ONLY thing a union touches — the prescan
        # snapshots and restores it (mirror LinkedList.values).
        self.values: list[str] = list(self.node_ids)

        # Optional initial forest structure.
        self._build_from_edges(params.get("edges", []))

        self.label: str | None = params.get("label")
        self._node_radius: int = _NODE_RADIUS

        # Annotation geometry (mirror Tree: 2-D arc offsets off a node circle).
        self._arrow_cell_height = float(self._node_radius * 2)
        self._arrow_layout = "2d"
        self._arrow_shorten = float(self._node_radius)

        # Position cache keyed on the parent-array signature so emit_svg,
        # get_node_positions and resolve_annotation_point share one layout per
        # state AND recompute correctly after the prescan restores self.values.
        self._pos_cache: dict[str, tuple[int, int]] | None = None
        self._pos_cache_sig: tuple[str, ...] | None = None

        # Monotonic envelope — seeded from the initial (all-singleton) layout,
        # grown by every union. bounding_box reads these, never the live layout.
        self._envelope_width: int = 2 * _PADDING
        self._envelope_height: int = 2 * _PADDING
        self._grow_envelope()

    # ----- construction helpers -------------------------------------------

    def _build_from_edges(self, raw_edges: Any) -> None:
        """Populate the parent array from an optional initial ``edges`` list.

        Each ``(parent, child)`` sets ``child``'s parent. Rejects unknown
        endpoints, a node handed two parents, and any cycle (all E1509).
        """
        assigned: set[str] = set()
        edge_list = coerce_list(
            raw_edges if raw_edges is not None else [],
            "E1509",
            detail=f"Forest 'edges' must be a list of (parent, child), got {raw_edges!r}",
            hint="example: edges=[(0, 1), (0, 2)]",
        )
        for e in edge_list:
            if isinstance(e, (str, bytes)) or not hasattr(e, "__getitem__") or len(e) < 2:
                raise _animation_error(
                    "E1509",
                    detail=f"Forest edge {e!r} must be a (parent, child) pair",
                    hint="example: edges=[(0, 1), (0, 2)]",
                )
            parent, child = str(e[0]), str(e[1])
            if parent not in self._index:
                raise _animation_error(
                    "E1509",
                    detail=f"Forest edge parent {parent!r} is not a declared node",
                    hint="both edge endpoints must appear in 'nodes'",
                )
            if child not in self._index:
                raise _animation_error(
                    "E1509",
                    detail=f"Forest edge child {child!r} is not a declared node",
                    hint="both edge endpoints must appear in 'nodes'",
                )
            if child in assigned or self.values[self._index[child]] != child:
                raise _animation_error(
                    "E1509",
                    detail=f"Forest node {child!r} is given more than one parent",
                    hint="each node may have at most one parent",
                )
            self.values[self._index[child]] = parent
            assigned.add(child)
        # Reject cycles introduced by the edge list (e.g. a->b, b->a).
        for nid in self.node_ids:
            if self._walk_to_root(nid) is None:
                raise _animation_error(
                    "E1509",
                    detail=f"Forest 'edges' form a cycle through node {nid!r}",
                    hint="the initial forest must be acyclic",
                )

    # ----- DSU helpers -----------------------------------------------------

    def _walk_to_root(self, node_id: str) -> str | None:
        """Follow parent pointers to the root, or ``None`` if a cycle is hit."""
        current = node_id
        for _ in range(len(self.node_ids) + 1):
            parent = self.values[self._index[current]]
            if parent == current:
                return current
            current = parent
        return None

    def _root_of(self, node_id: str) -> str:
        root = self._walk_to_root(node_id)
        # A cycle is impossible post-construction: union never creates one
        # (root(b) attaches under root(a), and a==b's root is a no-op).
        return root if root is not None else node_id

    def _build_children_map(self) -> dict[str, list[str]]:
        """Derive parent->children adjacency from the parent array."""
        children: dict[str, list[str]] = {nid: [] for nid in self.node_ids}
        for nid in self.node_ids:
            parent = self.values[self._index[nid]]
            if parent != nid:
                children[parent].append(nid)
        return children

    def _current_edges(self) -> list[tuple[str, str]]:
        """Current ``(parent, child)`` edges — one per non-root node."""
        return [
            (self.values[self._index[nid]], nid)
            for nid in self.node_ids
            if self.values[self._index[nid]] != nid
        ]

    @staticmethod
    def _sort_key(node_id: str) -> tuple[int, int, str]:
        """Order ids numerically when possible, else lexically (numbers first)."""
        try:
            return (0, int(node_id), "")
        except ValueError:
            return (1, 0, node_id)

    # ----- apply commands --------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Process ``union`` mutations from ``\\apply``.

        ``union={a, b}`` attaches ``root(b)`` **under** ``root(a)`` — the
        author controls the merge direction through the ``a``/``b`` order
        (there is deliberately no union-by-rank/size). When ``a`` and ``b``
        already share a root the union is a no-op. Both endpoints must be
        declared nodes (E1509).
        """
        if "union" not in params:
            return
        spec = params["union"]
        if not isinstance(spec, dict) or "a" not in spec or "b" not in spec:
            raise _animation_error(
                "E1509",
                detail="union requires {a, b}",
                hint="example: \\apply{f}{union={a=3, b=5}}",
            )
        a, b = str(spec["a"]), str(spec["b"])
        if a not in self._index:
            raise _animation_error(
                "E1509",
                detail=f"union references node {a!r} which is not in the forest",
                hint="both union endpoints must be declared nodes",
            )
        if b not in self._index:
            raise _animation_error(
                "E1509",
                detail=f"union references node {b!r} which is not in the forest",
                hint="both union endpoints must be declared nodes",
            )
        ra, rb = self._root_of(a), self._root_of(b)
        if ra == rb:
            # Already the same set — nothing to merge.
            return
        # root(b) becomes a child of root(a); rb's whole subtree rides along.
        self.values[self._index[rb]] = ra
        self._grow_envelope()

    # ----- layout ----------------------------------------------------------

    def _compute_positions(self) -> dict[str, tuple[int, int]]:
        """Pack each tree with Reingold-Tilford, left-to-right by min member id.

        Each tree is laid out independently in a per-tree viewport sized to
        yield a fixed ``_H_GAP`` column gap and ``_LAYER_GAP`` layer gap, then
        translated by a running horizontal cursor. The whole forest is
        re-anchored so the top-left-most node edge sits at ``(_PADDING,
        _PADDING)`` — a constant offset every frame (roots stay at depth 0 and
        the first tree stays leftmost), so the anchoring adds no spurious
        motion.
        """
        if not self.node_ids:
            return {}

        children = self._build_children_map()
        members_by_root: dict[str, list[str]] = {}
        for nid in self.node_ids:
            members_by_root.setdefault(self._root_of(nid), []).append(nid)

        roots = sorted(
            members_by_root,
            key=lambda r: min(self._sort_key(m) for m in members_by_root[r]),
        )

        r = self._node_radius
        positions: dict[str, tuple[int, int]] = {}
        x_cursor = float(_PADDING + r)
        for root in roots:
            members = members_by_root[root]
            depth_t = self._tree_depth(root, children)
            leaves_t = sum(1 for m in members if not children[m])
            w_t = max(2 * _PADDING, (leaves_t - 1) * _H_GAP + 2 * _PADDING)
            h_t = depth_t * _LAYER_GAP + 2 * _PADDING
            sub_children = {m: children[m] for m in members}
            rt = _reingold_tilford(root, sub_children, width=w_t, height=h_t)
            min_local_x = min(x for x, _ in rt.values())
            offset = x_cursor - min_local_x
            for m, (x, y) in rt.items():
                positions[m] = (round(x + offset), y)
            tree_w = max(x for x, _ in rt.values()) - min_local_x
            x_cursor += tree_w + _TREE_GAP

        # Re-anchor top-left node edge to (_PADDING, _PADDING).
        min_cx = min(x for x, _ in positions.values())
        min_cy = min(y for _, y in positions.values())
        shift_x = (_PADDING + r) - min_cx
        shift_y = (_PADDING + r) - min_cy
        if shift_x or shift_y:
            positions = {
                m: (x + shift_x, y + shift_y) for m, (x, y) in positions.items()
            }
        return positions

    @staticmethod
    def _tree_depth(root: str, children: dict[str, list[str]]) -> int:
        """Max depth of one tree (0 for a single node). Iterative (recursion
        is banned by the Wave 4B DoS lockdown)."""
        max_d = 0
        stack: list[tuple[str, int]] = [(root, 0)]
        while stack:
            node, d = stack.pop()
            if d > max_d:
                max_d = d
            for child in children.get(node, []):
                stack.append((child, d + 1))
        return max_d

    def _current_positions(self) -> dict[str, tuple[int, int]]:
        """Layout for the current parent-array state, cached on its signature."""
        sig = tuple(self.values)
        if self._pos_cache_sig != sig or self._pos_cache is None:
            self._pos_cache = self._compute_positions()
            self._pos_cache_sig = sig
        return self._pos_cache

    def _measure_content(self, positions: dict[str, tuple[int, int]]) -> tuple[int, int]:
        """Content ``(width, height)`` of a layout, with a ``_PADDING`` margin."""
        if not positions:
            return (2 * _PADDING, 2 * _PADDING)
        r = self._node_radius
        max_x = max(x for x, _ in positions.values())
        max_y = max(y for _, y in positions.values())
        return (max_x + r + _PADDING, max_y + r + _PADDING)

    def _grow_envelope(self) -> None:
        """Grow the monotonic envelope to cover the current layout."""
        w, h = self._measure_content(self._current_positions())
        self._envelope_width = max(self._envelope_width, w)
        self._envelope_height = max(self._envelope_height, h)

    # ----- selector helpers ------------------------------------------------

    @staticmethod
    def _node_key(node_id: str) -> str:
        return f"node[{node_id}]"

    @staticmethod
    def _edge_key(u: str, v: str) -> str:
        return f"edge[({u},{v})]"

    # ----- position tracking (glide substrate) -----------------------------

    def get_node_positions(self) -> dict[str, tuple[int, int]]:
        """Map ``"{name}.node[{id}]"`` to ``(x, y)`` for every node.

        Consumed by ``_inject_tree_positions`` so the differ emits
        ``position_move`` when a union re-lays out the forest — the free glide.
        """
        return {
            f"{self.name}.{self._node_key(nid)}": pos
            for nid, pos in self._current_positions().items()
        }

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = [self._node_key(nid) for nid in self.node_ids]
        for u, v in self._current_edges():
            parts.append(self._edge_key(u, v))
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True
        return suffix in set(self.addressable_parts())

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Center of a node, or the midpoint of an edge's two node centers."""
        positions = self._current_positions()
        m = _FOREST_NODE_SEL_RE.match(selector)
        if m and m.group("name") == self.name:
            node_id = m.group("id")
            if node_id in positions:
                cx, cy = positions[node_id]
                return (float(cx), float(cy))
            return None

        em = _FOREST_EDGE_SEL_RE.match(selector)
        if em and em.group("name") == self.name:
            u, v = em.group("u"), em.group("v")
            if u in positions and v in positions:
                ux, uy = positions[u]
                vx, vy = positions[v]
                return ((ux + vx) / 2.0, (uy + vy) / 2.0)
        return None

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit below the reserved forest envelope."""
        return float(self._envelope_height)

    def bounding_box(self) -> BoundingBox:
        content_w = float(self._envelope_width)
        core_w = max(self._envelope_width, self._caption_block_width(content_w))
        label_h = self._top_caption_band(content_w)
        arrow_above = self._reserved_arrow_above()
        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)
        h = self._envelope_height + arrow_above + self._below_lane_height() + label_h
        return BoundingBox(x=0, y=0, width=int(w), height=int(h))

    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        if not self.node_ids:
            return (
                f'<g data-primitive="forest" data-shape="{_escape_xml(self.name)}">'
                "</g>"
            )

        positions = self._current_positions()
        r = self._node_radius
        effective_anns = self._annotations
        arrow_above = self._reserved_arrow_above()
        left_pad, _right = self._h_label_pad()

        parts: list[str] = []
        parts.append(
            f'<g data-primitive="forest" data-shape="{_escape_xml(self.name)}"'
            f' transform="translate({left_pad},{arrow_above})">'
        )

        # Optional top-band caption (mirror Tree; content is shifted by
        # left_pad only, so frame_radius == left_pad centres it on the box).
        label_offset = 0
        if self.label is not None:
            content_w = float(self._envelope_width)
            label_offset = self._top_caption_band(content_w)
            self._emit_top_caption(
                parts,
                content_width=content_w,
                footprint_width=int(self.bounding_box().width),
                frame_radius=float(left_pad),
                render_inline_tex=render_inline_tex,
            )
        if label_offset:
            parts.append(f'<g transform="translate(0,{label_offset})">')

        # --- Edge layer (below nodes) ---
        parts.append('<g class="scriba-forest-edges">')
        for parent, child in self._current_edges():
            edge_key = self._edge_key(parent, child)
            edge_target = f"{self.name}.{edge_key}"
            state = self.get_state(edge_key)
            if state == "hidden":
                continue
            if (
                self.get_state(self._node_key(parent)) == "hidden"
                or self.get_state(self._node_key(child)) == "hidden"
            ):
                continue
            if parent not in positions or child not in positions:
                continue
            edge_colors = svg_style_attrs(state)
            edge_sw = "1.5" if state == "idle" else "2"
            px, py = positions[parent]
            cx, cy = positions[child]
            x1, y1 = _shorten_line_to_circle(cx, cy, px, py, r)
            x2, y2 = _shorten_line_to_circle(px, py, cx, cy, r)
            parts.append(
                f'<g data-target="{_escape_xml(edge_target)}" '
                f'class="{state_class(state)}">'
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'fill="none" stroke="{edge_colors["stroke"]}" '
                f'stroke-width="{edge_sw}"/>'
                f"</g>"
            )
        parts.append("</g>")

        # --- Node layer (on top) ---
        parts.append('<g class="scriba-forest-nodes">')
        for node_id in self.node_ids:
            if node_id not in positions:
                continue
            node_key = self._node_key(node_id)
            node_target = f"{self.name}.{node_key}"
            state = self.get_state(node_key)
            if state == "hidden":
                continue
            node_colors = svg_style_attrs(state)
            cx, cy = positions[node_id]
            node_sw = "1.5" if state == "idle" else "2"
            override = self.get_value(node_key)
            display_label = (
                override if override is not None
                else self.node_labels.get(node_id, node_id)
            )
            node_text = _render_svg_text(
                str(display_label),
                cx,
                cy,
                fill=node_colors["text"],
                text_anchor="middle",
                dominant_baseline="central",
                font_size="14",
                fo_width=r * 2,
                fo_height=r * 2,
                render_inline_tex=render_inline_tex,
                clip_overflow=False,
            )
            parts.append(
                f'<g data-target="{_escape_xml(node_target)}" '
                f'data-node-x="{cx}" data-node-y="{cy}" '
                f'class="{state_class(state)}">'
                f'<circle cx="{cx}" cy="{cy}" r="{r}" '
                f'fill="{node_colors["fill"]}" '
                f'stroke="{node_colors["stroke"]}" '
                f'stroke-width="{node_sw}"/>'
                f"{node_text}"
                f"</g>"
            )
        parts.append("</g>")

        # --- Annotation arrows (on top of everything) ---
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

        if label_offset:
            parts.append("</g>")
        parts.append("</g>")
        return "".join(parts)

    def _annotation_cell_metrics(self) -> Any:
        """Node diameter stands in as the local cell scale (2-D arc stagger)."""
        from scriba.animation.primitives._svg_helpers import CellMetrics

        diam = float(self._node_radius * 2)
        return CellMetrics(
            cell_width=diam,
            cell_height=diam,
            grid_cols=len(self.node_ids) or 1,
            grid_rows=1,
            origin_x=0.0,
            origin_y=0.0,
        )

    # -- obstacle protocol stubs --------------------------------------------

    def resolve_obstacle_boxes(self) -> list:
        return []

    def resolve_obstacle_segments(self) -> list:
        return []
