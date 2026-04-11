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


# ---------------------------------------------------------------------------
# Fruchterman-Reingold layout
# ---------------------------------------------------------------------------


def fruchterman_reingold(
    nodes: list[str | int],
    edges: list[tuple[str | int, str | int]],
    *,
    width: int = _DEFAULT_WIDTH,
    height: int = _DEFAULT_HEIGHT,
    seed: int = _DEFAULT_SEED,
    iterations: int = _DEFAULT_ITERATIONS,
) -> dict[str | int, tuple[int, int]]:
    """Compute force-directed node positions.

    Returns a dict mapping each node identifier to an ``(x, y)`` integer
    coordinate pair.  Layout is deterministic for a given *seed*.
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
                "E1103",
                detail=(
                    f"Graph '{name}' requires a non-empty 'nodes' list; "
                    f"got an empty or missing 'nodes' parameter"
                ),
            )
        raw_edges = params.get("edges", [])
        self.edges: list[tuple[str | int, str | int]] = [
            (e[0], e[1]) for e in raw_edges
        ]
        self.directed: bool = bool(params.get("directed", False))
        self.layout: str = str(params.get("layout", "force"))
        self.layout_seed: int = int(params.get("layout_seed", _DEFAULT_SEED))
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
                self.edges,
                width=self.width,
                height=self.height,
                seed=self.layout_seed,
            )
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
                    css_class="scriba-label",
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
        parts.append('<g class="scriba-graph-edges">')
        for u, v in self.edges:
            edge_target = f"{self.name}.{self._edge_key(u, v)}"
            state = self.get_state(self._edge_key(u, v))
            x1, y1 = self.positions[u]
            x2, y2 = self.positions[v]

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
            parts.append(
                f'<g data-target="{html_escape(edge_target)}" '
                f'class="scriba-state-{state}" '
                f'role="graphics-symbol" aria-label="{edge_label}">'
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{edge_stroke}" stroke-width="{edge_sw}"'
                f'{marker}>'
                f'<title>{edge_label}</title>'
                f'</line>'
                f'</g>'
            )
        parts.append('</g>')

        # --- Node layer (rendered on top) ---
        parts.append('<g class="scriba-graph-nodes">')
        for node_id in self.nodes:
            node_target = f"{self.name}.{self._node_key(node_id)}"
            state = self.get_state(self._node_key(node_id))
            node_colors = svg_style_attrs(state)
            cx, cy = self.positions[node_id]
            node_sw = "1.5" if state == "idle" else "2"
            hl_suffixes = getattr(self, "_highlighted", set())
            is_hl = self._node_key(node_id) in hl_suffixes
            hl_overlay = ""
            if is_hl:
                hl_overlay = (
                    f'<circle cx="{cx}" cy="{cy}" r="{self._node_radius}" '
                    f'fill="none" stroke="#F0E442" stroke-width="3" '
                    f'stroke-dasharray="6 3"/>'
                )
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
                text_outline=node_colors["fill"],
            )
            parts.append(
                f'<g data-target="{html_escape(node_target)}" '
                f'class="scriba-state-{state}">'
                f'<circle cx="{cx}" cy="{cy}" r="{self._node_radius}" '
                f'fill="{node_colors["fill"]}" '
                f'stroke="{node_colors["stroke"]}" '
                f'stroke-width="{node_sw}"/>'
                f'{node_text}'
                f'{hl_overlay}'
                f'</g>'
            )
        parts.append('</g>')

        parts.append('</g>')
        return ''.join(parts)
