"""Graph primitive with Fruchterman-Reingold force-directed layout.

Implements ``\\shape{name}{Graph}{nodes=..., edges=..., ...}`` for BFS/DFS,
flow networks, and general graph algorithm visualizations.

See ``docs/spec/primitives.md`` section 6 for the authoritative specification.
"""

from __future__ import annotations

import math
import random
from html import escape as html_escape
from typing import Any, Callable, ClassVar

from scriba.animation.errors import animation_error
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
_EDGE_STROKE_WIDTH = 2
_PADDING = 20
_DEFAULT_SEED = 42
_DEFAULT_ITERATIONS = 50

# Maximum node count for force-directed Graph layout.
#
# The Fruchterman-Reingold implementation below is O(N^2) per
# iteration, so constructing a 1000-node graph takes ~10 seconds and
# blocks the renderer (a DoS vector for a malicious editorial).
#
# 100 is a generous upper bound for visualisations — viewers cannot
# meaningfully distinguish more than ~100 nodes in a single frame
# anyway. Scenes needing more nodes should use ``layout="stable"``
# (itself capped at 20 nodes) or split the graph across frames.
#
# See Wave 4B Cluster 1 DoS fix for the original finding.
_MAX_NODES = 100

# Minimum gap (in px) between the outer edges of two node circles after
# the collision-resolution post-pass.  The actual minimum center-to-center
# distance is ``2 * _NODE_RADIUS + _NODE_OVERLAP_GAP``.
_NODE_OVERLAP_GAP = 12


# ---------------------------------------------------------------------------
# Fruchterman-Reingold layout
# ---------------------------------------------------------------------------


def _resolve_overlaps(
    pos: dict[str | int, tuple[float, float]],
    nodes: list[str | int],
    min_sep: float,
    width: int,
    height: int,
    passes: int = 10,
) -> None:
    """Push apart any node pair closer than *min_sep* (in-place).

    A simple iterative collision-resolution post-pass.  For each pair
    within *min_sep*, both nodes are displaced by half the deficit along
    the line connecting them.  Multiple passes handle cascades where
    resolving one collision creates another.

    Clamped to ``[_PADDING, width/height - _PADDING]`` so nodes stay
    inside the canvas.
    """
    for _ in range(passes):
        moved = False
        for i, u in enumerate(nodes):
            for v in nodes[i + 1:]:
                dx = pos[u][0] - pos[v][0]
                dy = pos[u][1] - pos[v][1]
                d = math.sqrt(dx * dx + dy * dy)
                if d < min_sep:
                    moved = True
                    # Push apart along the connecting line (or along x
                    # if they're at the exact same position).
                    if d < 0.01:
                        dx, dy, d = 1.0, 0.0, 1.0
                    deficit = (min_sep - d) / 2.0 + 0.5
                    shift_x = deficit * dx / d
                    shift_y = deficit * dy / d
                    pos[u] = (
                        max(_PADDING, min(width - _PADDING, pos[u][0] + shift_x)),
                        max(_PADDING, min(height - _PADDING, pos[u][1] + shift_y)),
                    )
                    pos[v] = (
                        max(_PADDING, min(width - _PADDING, pos[v][0] - shift_x)),
                        max(_PADDING, min(height - _PADDING, pos[v][1] - shift_y)),
                    )
        if not moved:
            break


def fruchterman_reingold(
    nodes: list[str | int],
    edges: list[tuple[str | int, str | int]],
    *,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    seed: int = _DEFAULT_SEED,
    iterations: int = _DEFAULT_ITERATIONS,
    node_radius: int = _NODE_RADIUS,
) -> dict[str | int, tuple[int, int]]:
    """Compute force-directed node positions.

    Returns a dict mapping each node identifier to an ``(x, y)`` integer
    coordinate pair.  Layout is deterministic for a given *seed*.

    After force-directed convergence, a collision-resolution post-pass
    guarantees no two nodes overlap (minimum separation =
    ``2 * node_radius + _NODE_OVERLAP_GAP``).
    """
    n = len(nodes)
    if n == 0:
        return {}
    if n == 1:
        return {nodes[0]: (width // 2, height // 2)}

    area = width * height
    k = math.sqrt(area / n)  # optimal inter-node distance

    rng = random.Random(seed)
    pos: dict[str | int, tuple[float, float]] = {
        node: (rng.uniform(_PADDING, width - _PADDING),
               rng.uniform(_PADDING, height - _PADDING))
        for node in nodes
    }

    t = width / 10.0  # initial temperature
    dt = t / (iterations + 1)

    for _ in range(iterations):
        disp: dict[str | int, list[float]] = {node: [0.0, 0.0] for node in nodes}

        # Repulsive forces between all node pairs
        for i, u in enumerate(nodes):
            for v in nodes[i + 1:]:
                dx = pos[u][0] - pos[v][0]
                dy = pos[u][1] - pos[v][1]
                d = max(math.sqrt(dx * dx + dy * dy), 0.01)
                force = k * k / d
                fx = force * dx / d
                fy = force * dy / d
                disp[u][0] += fx
                disp[u][1] += fy
                disp[v][0] -= fx
                disp[v][1] -= fy

        # Attractive forces along edges
        for u, v in edges:
            dx = pos[u][0] - pos[v][0]
            dy = pos[u][1] - pos[v][1]
            d = max(math.sqrt(dx * dx + dy * dy), 0.01)
            force = d * d / k
            fx = force * dx / d
            fy = force * dy / d
            disp[u][0] -= fx
            disp[u][1] -= fy
            disp[v][0] += fx
            disp[v][1] += fy

        # Apply displacement with temperature limit
        for node in nodes:
            ndx, ndy = disp[node]
            d = max(math.sqrt(ndx * ndx + ndy * ndy), 0.01)
            move_x = ndx / d * min(abs(ndx), t)
            move_y = ndy / d * min(abs(ndy), t)
            new_x = max(_PADDING, min(width - _PADDING, pos[node][0] + move_x))
            new_y = max(_PADDING, min(height - _PADDING, pos[node][1] + move_y))
            pos[node] = (new_x, new_y)

        t -= dt

    # Post-pass: guarantee no two nodes overlap.  The force-directed
    # algorithm converges to an equilibrium that can leave nodes within
    # 2*radius of each other when repulsion is balanced by attractive
    # edge forces or boundary constraints.
    min_sep = 2.0 * node_radius + _NODE_OVERLAP_GAP
    _resolve_overlaps(pos, nodes, min_sep, width, height)

    return {node: (round(x), round(y)) for node, (x, y) in pos.items()}


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------


def _arrow_marker_defs() -> str:
    """Return an SVG ``<defs>`` block with the shared arrowhead marker."""
    return (
        '<defs>'
        '<marker id="scriba-arrow" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<title>Arrowhead</title>'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/>'
        '</marker>'
        '</defs>'
    )


def _format_weight(weight: float) -> str:
    """Format an edge weight for SVG display.

    Integers render without a decimal (``"3"``); floats keep up to
    three significant digits and trim trailing zeros (``"1.5"``).
    """
    if weight == int(weight):
        return str(int(weight))
    formatted = f"{weight:.3g}"
    return formatted


def _shorten_line_to_circle(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    radius: int,
) -> tuple[int, int]:
    """Move ``(x2, y2)`` back along the line by *radius* pixels.

    Used for directed edges so the arrowhead sits at the circle boundary
    rather than at the centre.
    """
    dx = x2 - x1
    dy = y2 - y1
    d = max(math.sqrt(dx * dx + dy * dy), 0.01)
    return (round(x2 - radius * dx / d), round(y2 - radius * dy / d))


# ---------------------------------------------------------------------------
# Graph primitive
# ---------------------------------------------------------------------------


@register_primitive("Graph")
class Graph(PrimitiveBase):
    """Force-directed graph primitive.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``G``).
    params:
        Dictionary of parameters from the ``\\shape`` command.  Required keys
        are ``nodes`` and ``edges``.  Optional keys: ``directed``,
        ``layout``, ``layout_seed``, ``label``.

    Seed canonicalization
    ---------------------
    The spec canonical key is ``layout_seed`` (see ``docs/spec/primitives.md``
    §6).  A bare ``seed`` key is accepted as a convenience alias when
    ``layout_seed`` is absent.  The value must be a non-negative ``int``;
    anything else raises ``E1505``.
    """

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "node[{id}]": "node by id",
        "edge[({u},{v})]": "edge by endpoints",
        "all": "all nodes and edges",
    }

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        from scriba.animation.errors import animation_error

        self.nodes: list[str | int] = list(params.get("nodes", []))
        if not self.nodes:
            raise animation_error(
                "E1470",
                detail=(
                    f"Graph '{name}' requires a non-empty 'nodes' list; "
                    "got an empty or missing 'nodes' parameter"
                ),
                hint="example: Graph{g}{nodes=[\"a\", \"b\"], edges=[(\"a\", \"b\")]}",
            )
        if len(self.nodes) > _MAX_NODES:
            # Force-directed layout is O(N^2) per iteration; reject
            # oversized graphs up front rather than letting a
            # malicious editorial burn seconds of renderer time.
            from scriba.animation.errors import animation_error

            raise animation_error(
                "E1501",
                detail=(
                    f"Graph '{name}' node count {len(self.nodes)} "
                    f"exceeds maximum {_MAX_NODES}; use layout=stable "
                    f"for larger graphs or split the visualization"
                ),
            )
        raw_edges = params.get("edges", [])
        parsed_edges: list[tuple[str | int, str | int, float | None]] = []
        has_weighted = False
        has_unweighted = False
        for e in raw_edges:
            if len(e) == 3:
                parsed_edges.append((e[0], e[1], float(e[2])))
                has_weighted = True
            elif len(e) == 2:
                parsed_edges.append((e[0], e[1], None))
                has_unweighted = True
            else:
                raise animation_error(
                    "E1474",
                    detail=f"edge must be 2-tuple or 3-tuple, got {e!r}",
                )
        if has_weighted and has_unweighted:
            raise animation_error(
                "E1474",
                detail="edges list mixes weighted and unweighted entries",
            )
        self.edges: list[tuple[str | int, str | int, float | None]] = parsed_edges
        self.directed: bool = bool(params.get("directed", False))
        self.layout: str = str(params.get("layout", "force"))
        self.show_weights: bool = bool(params.get("show_weights", False))

        # --- layout_seed validation (E1505) ---
        #
        # The spec canonical name is ``layout_seed``.  We also accept a bare
        # ``seed`` as an alias if ``layout_seed`` was not supplied (for
        # convenience and because ``fruchterman_reingold`` itself uses
        # ``seed=``).  If both are present, ``layout_seed`` wins.
        if "layout_seed" in params:
            raw_seed: Any = params["layout_seed"]
        elif "seed" in params:
            raw_seed = params["seed"]
        else:
            raw_seed = _DEFAULT_SEED

        # Reject ``bool`` explicitly: in Python ``bool`` is a subclass of
        # ``int`` but ``True``/``False`` as a seed is almost certainly a
        # programming mistake.
        if isinstance(raw_seed, bool) or not isinstance(raw_seed, int):
            raise animation_error(
                "E1505",
                f"Graph layout_seed must be a non-negative integer, "
                f"got {type(raw_seed).__name__} {raw_seed!r}",
            )
        if raw_seed < 0:
            raise animation_error(
                "E1505",
                f"Graph layout_seed must be a non-negative integer, "
                f"got {raw_seed}",
            )
        self.layout_seed: int = raw_seed

        self.label: str | None = params.get("label")

        self.width: int = _DEFAULT_WIDTH
        self.height: int = _DEFAULT_HEIGHT

        # Scale node radius with density so dense graphs don't overlap
        self._node_radius: int = max(
            12,
            min(
                _NODE_RADIUS,
                int(min(self.width, self.height) / (2 * max(len(self.nodes), 1))),
            ),
        )

        # Compute positions
        self.positions: dict[str | int, tuple[int, int]] = (
            fruchterman_reingold(
                self.nodes,
                [(u, v) for u, v, _w in self.edges],
                width=self.width,
                height=self.height,
                seed=self.layout_seed,
            )
        )

    # ----- mutation API ----------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Apply a mutation command from the animation pipeline.

        Supported ops (one per call):
            - ``add_edge``: {"from": u, "to": v, "weight": w?}
            - ``remove_edge``: {"from": u, "to": v}
            - ``set_weight``: {"from": u, "to": v, "value": w}

        Raises
        ------
        AnimationError
            - ``E1471`` if ``add_edge`` references an unknown endpoint or
              the spec dict is missing required keys.
            - ``E1472`` if ``remove_edge`` targets a non-existent edge.
            - ``E1473`` if ``set_weight`` targets a non-existent edge.
        """
        from scriba.animation.errors import animation_error

        if "add_edge" in params:
            spec = params["add_edge"]
            if not isinstance(spec, dict):
                raise animation_error(
                    "E1471",
                    detail=f"add_edge requires a dict {{from, to}}, got {type(spec).__name__}",
                )
            u = spec.get("from")
            v = spec.get("to")
            weight = spec.get("weight")
            if u is None or v is None:
                raise animation_error(
                    "E1471",
                    detail="add_edge requires {from, to}",
                )
            self._add_edge_internal(u, v, weight)
            return
        if "remove_edge" in params:
            spec = params["remove_edge"]
            if not isinstance(spec, dict):
                raise animation_error(
                    "E1472",
                    detail=f"remove_edge requires a dict {{from, to}}, got {type(spec).__name__}",
                )
            self._remove_edge_internal(spec.get("from"), spec.get("to"))
            return
        if "set_weight" in params:
            spec = params["set_weight"]
            if not isinstance(spec, dict):
                raise animation_error(
                    "E1473",
                    detail=f"set_weight requires a dict {{from, to, value}}, got {type(spec).__name__}",
                )
            self._set_weight_internal(
                spec.get("from"), spec.get("to"), spec.get("value")
            )
            return

    def _add_edge_internal(
        self,
        u: str | int,
        v: str | int,
        weight: float | int | None,
    ) -> None:
        from scriba.animation.errors import animation_error

        if u not in self.nodes:
            raise animation_error(
                "E1471",
                detail=f"add_edge source node {u!r} is not in graph",
            )
        if v not in self.nodes:
            raise animation_error(
                "E1471",
                detail=f"add_edge target node {v!r} is not in graph",
            )
        w: float | None = float(weight) if weight is not None else None
        self.edges.append((u, v, w))
        self._relayout_with_warm_start()

    def _remove_edge_internal(self, u: str | int, v: str | int) -> None:
        from scriba.animation.errors import animation_error

        idx = self._find_edge_index(u, v)
        if idx is None:
            raise animation_error(
                "E1472",
                detail=f"remove_edge: no edge between {u!r} and {v!r}",
            )
        self.edges.pop(idx)
        self._relayout_with_warm_start()

    def _set_weight_internal(
        self,
        u: str | int,
        v: str | int,
        value: float | int | None,
    ) -> None:
        from scriba.animation.errors import animation_error

        if value is None:
            raise animation_error(
                "E1473",
                detail="set_weight requires a numeric 'value'",
            )
        idx = self._find_edge_index(u, v)
        if idx is None:
            raise animation_error(
                "E1473",
                detail=f"set_weight: no edge between {u!r} and {v!r}",
            )
        eu, ev, _old = self.edges[idx]
        self.edges[idx] = (eu, ev, float(value))
        # No relayout: weight does not affect geometry.

    def _find_edge_index(
        self,
        u: str | int,
        v: str | int,
    ) -> int | None:
        """Return the index of the edge (u,v); treat undirected as unordered."""
        for i, (eu, ev, _w) in enumerate(self.edges):
            if eu == u and ev == v:
                return i
            if not self.directed and eu == v and ev == u:
                return i
        return None

    def _relayout_with_warm_start(self) -> None:
        """Recompute positions after a mutation using warm-start layout."""
        from scriba.animation.primitives.graph_layout_stable import (
            compute_stable_layout,
        )

        old_positions: dict[str, tuple[float, float]] = {
            str(n): (float(self.positions[n][0]), float(self.positions[n][1]))
            for n in self.nodes
            if n in self.positions
        }
        frame_edges = [[(str(u), str(v)) for u, v, _w in self.edges]]
        result = compute_stable_layout(
            [str(n) for n in self.nodes],
            frame_edges,
            seed=self.layout_seed,
            initial_positions=old_positions,
            width=self.width,
            height=self.height,
            node_radius=self._node_radius,
        )
        if result is not None:
            self.positions = {
                n: (round(result[str(n)][0]), round(result[str(n)][1]))
                for n in self.nodes
            }
        else:
            # Size guard tripped — fall back to force layout.
            self.positions = fruchterman_reingold(
                self.nodes,
                [(u, v) for u, v, _w in self.edges],
                width=self.width,
                height=self.height,
                seed=self.layout_seed,
            )

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
        for u, v, _w in self.edges:
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
                f'<g data-primitive="graph" data-shape="{html_escape(self.name)}">'
                '</g>'
            )

        r = self._node_radius
        parts: list[str] = []
        # Offset by node radius so nodes at edge positions don't clip
        parts.append(
            f'<g data-primitive="graph" data-shape="{html_escape(self.name)}"'
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
                    css_class="scriba-primitive-label",
                    text_anchor="middle",
                    fo_width=self.width,
                    fo_height=24,
                    render_inline_tex=render_inline_tex,
                )
            )

        # Arrowhead defs for directed graphs
        if self.directed:
            parts.append(_arrow_marker_defs())

        # --- Edge layer (rendered first, below nodes) ---
        # Pre-compute the set of hidden node keys so edges incident on a
        # hidden node are also skipped (avoids orphan edges dangling into
        # empty space, matches Tree.emit_svg behavior — RFC-001 §4.4).
        hidden_nodes: set[str | int] = {
            n for n in self.nodes
            if self.get_state(self._node_key(n)) == "hidden"
        }
        parts.append('<g class="scriba-graph-edges">')
        for u, v, weight in self.edges:
            edge_target = f"{self.name}.{self._edge_key(u, v)}"
            state = self.get_state(self._edge_key(u, v))
            # RFC-001 §4.4 — hidden edges are not rendered at all. Also
            # skip edges whose endpoints are hidden (would otherwise
            # render as a line going into empty space).
            if state == "hidden" or u in hidden_nodes or v in hidden_nodes:
                continue
            x1, y1 = self.positions[u]
            x2, y2 = self.positions[v]
            # Capture midpoint before any directed shortening so the
            # weight label stays centered on the visible segment.
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2 - 4

            if self.directed:
                # Shorten line so arrowhead stops at circle boundary
                x2, y2 = _shorten_line_to_circle(x1, y1, x2, y2, self._node_radius)

            marker = ' marker-end="url(#scriba-arrow)"' if self.directed else ""
            edge_colors = svg_style_attrs(state)
            edge_stroke = edge_colors["stroke"]
            edge_sw = "1.5" if state == "idle" else "2"
            edge_label = (
                f"Edge from node {html_escape(str(u))} "
                f"to node {html_escape(str(v))}"
            )
            weight_text = ""
            if (
                self.show_weights
                and not self.directed
                and weight is not None
            ):
                weight_text = _render_svg_text(
                    _format_weight(weight), mid_x, mid_y,
                    fill=THEME["fg_muted"],
                    text_anchor="middle",
                    css_class="scriba-graph-weight",
                    render_inline_tex=render_inline_tex,
                )
            parts.append(
                f'<g data-target="{html_escape(edge_target)}" '
                f'class="scriba-state-{state}" '
                f'role="graphics-symbol" aria-label="{edge_label}">'
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{edge_stroke}" stroke-width="{edge_sw}"'
                f'{marker}>'
                f'<title>{edge_label}</title>'
                f'</line>'
                f'{weight_text}'
                f'</g>'
            )
        parts.append('</g>')

        # --- Node layer (rendered on top) ---
        parts.append('<g class="scriba-graph-nodes">')
        for node_id in self.nodes:
            node_target = f"{self.name}.{self._node_key(node_id)}"
            state = self.get_state(self._node_key(node_id))
            # RFC-001 §4.4 — hidden nodes are not rendered at all.
            if state == "hidden":
                continue
            cx, cy = self.positions[node_id]
            hl_suffixes = getattr(self, "_highlighted", set())
            is_hl = self._node_key(node_id) in hl_suffixes
            # β: highlight is a state, not a dashed overlay. Promote only
            # when the node is otherwise idle; keep current/error/good alive.
            effective_state = "highlight" if (is_hl and state == "idle") else state
            node_colors = svg_style_attrs(effective_state)
            node_text = _render_svg_text(
                str(node_id),
                cx,
                cy,
                fill=node_colors["text"],
                text_anchor="middle",
                dominant_baseline="central",
                fo_width=self._node_radius * 2,
                fo_height=self._node_radius * 2,
                render_inline_tex=render_inline_tex,
                # Wave 9: no inline text_outline — CSS halo cascade owns it.
            )
            parts.append(
                f'<g data-target="{html_escape(node_target)}" '
                f'class="scriba-state-{effective_state}">'
                f'<circle cx="{cx}" cy="{cy}" r="{self._node_radius}"/>'
                f'{node_text}'
                f'</g>'
            )
        parts.append('</g>')

        parts.append('</g>')
        return ''.join(parts)
