"""Graph primitive with Fruchterman-Reingold force-directed layout.

Implements ``\\shape{name}{Graph}{nodes=..., edges=..., ...}`` for BFS/DFS,
flow networks, and general graph algorithm visualizations.

See ``docs/spec/primitives.md`` section 6 for the authoritative specification.
"""

from __future__ import annotations

import math
import random
import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives.base import (
    _LabelPlacement,
    BoundingBox,
    PrimitiveBase,
    THEME,
    _escape_xml,
    _render_svg_text,
    arrow_height_above,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._svg_helpers import CellMetrics
from scriba.animation.primitives._types import (
    _NODE_MIN_RADIUS,
    _PRIMITIVE_LABEL_Y,
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

# Edge weight pill — see docs/spec/graph-edge-pill-ruleset.md (GEP-02/03/04).
_WEIGHT_FONT: int = 11
_WEIGHT_PILL_PAD_X: int = 5
_WEIGHT_PILL_PAD_Y: int = 2
_WEIGHT_PILL_R: int = 3
# Perpendicular offset from stroke centerline to pill centre (GEP-06 v1.1).
# v1.1: pill sits ON the edge stroke (Graphviz/Mermaid convention) rather than
# floating alongside — rotated pill already binds to edge direction visually,
# so an extra perp gap reads as detachment. Nudge only kicks in on collision.
# v1.2 (GEP-07): along-edge shift is the primary collision resolution; perp
# nudge is a fallback only when the visible segment is too short to slide.
_WEIGHT_PILL_PERP_BIAS: float = 0.0
# Stroke-width expansion of the pill AABB for collision (GEP-09).
_WEIGHT_PILL_STROKE_PAD: float = 1.0
# Coincident-edge early-exit threshold (GEP-11).
_WEIGHT_EDGE_MIN_LEN: float = 4.0

# Edge-placement ordering priority for D-1 determinism (GEP-05).
_EDGE_STATE_PRIO: dict[str, int] = {
    "current": 0,
    "highlighted": 1,
    "active": 2,
    "idle": 3,
    "muted": 4,
}

# Regex to parse annotation selectors like "G.node[A]" or "G.node[myNode]"
_GRAPH_NODE_SEL_RE = re.compile(r"^(?P<name>\w+)\.node\[(?P<id>.+)\]$")


# ---------------------------------------------------------------------------
# GEP-07 v1.2 — pill nudge helper (pure, testable without SVG)
# ---------------------------------------------------------------------------


def _nudge_pill_placement(
    mid_x: float,
    mid_y: float,
    ux: float,
    uy: float,
    perp_x: float,
    perp_y: float,
    pill_w: float,
    pill_h: float,
    aabb_w: float,
    aabb_h: float,
    max_shift_along: float,
    node_aabbs: list[_LabelPlacement],
    placed_pills: list[_LabelPlacement],
) -> tuple[float, float]:
    """Return the final pill centre (lx, ly) after GEP-07 v1.2 nudge.

    Stage 1 — along-edge shift: slides pill on the stroke, preserving
    GEP-10 edge binding.  Skipped when max_shift_along == 0 (short edges).
    Stage 2 — perp nudge fallback: v1.1 behaviour, used only when along-
    shift is exhausted or budget is zero.
    Stage 3 — origin fallback: a touching pill beats a detached pill.

    All obstacle lists are consulted as-is; caller must not mutate them
    between construction and this call.
    """
    def _collides(c: _LabelPlacement) -> bool:
        return any(c.overlaps(p) for p in placed_pills) or any(
            c.overlaps(n) for n in node_aabbs
        )

    origin_lx, origin_ly = mid_x, mid_y
    candidate = _LabelPlacement(x=origin_lx, y=origin_ly, width=aabb_w, height=aabb_h)

    if not _collides(candidate):
        return origin_lx, origin_ly

    # Step against the rotated AABB, not the un-rotated pill box: on angled
    # edges aabb_w / aabb_h swell to ~pill·√2, so step=pill_w+2 would leave
    # residual overlap between neighbouring rotated pills. Using aabb_* + 2
    # guarantees the first probe clears the previous pill's footprint.
    nudge_step_along = aabb_w + 2
    nudge_step_perp = aabb_h + 2

    # Stage 1 — along-edge shift (preserves GEP-10 binding).
    for offset in (
        nudge_step_along,
        -nudge_step_along,
        2 * nudge_step_along,
        -2 * nudge_step_along,
    ):
        if abs(offset) > max_shift_along:
            continue
        trial_lx = origin_lx + ux * offset
        trial_ly = origin_ly + uy * offset
        trial = _LabelPlacement(x=trial_lx, y=trial_ly, width=aabb_w, height=aabb_h)
        if not _collides(trial):
            return trial_lx, trial_ly

    # Stage 2 — perp nudge fallback (v1.1 behaviour).
    for offset in (
        nudge_step_perp,
        -nudge_step_perp,
        2 * nudge_step_perp,
        -2 * nudge_step_perp,
    ):
        trial_lx = origin_lx + perp_x * offset
        trial_ly = origin_ly + perp_y * offset
        trial = _LabelPlacement(x=trial_lx, y=trial_ly, width=aabb_w, height=aabb_h)
        if not _collides(trial):
            return trial_lx, trial_ly

    # Stage 3 — origin fallback: touching beats detached.
    return origin_lx, origin_ly


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
    """Return an SVG ``<defs>`` block with the shared arrowhead markers.

    Two markers are emitted for SVG 1.1 compatibility (Firefox ESR ≤ 88
    does not support ``orient="auto-start-reverse"``):

    * ``scriba-arrow-fwd`` — forward arrowhead, ``orient="auto"``.
    * ``scriba-arrow-rev`` — reverse arrowhead, path rotated 180°,
      ``orient="auto"``.
    """
    return (
        '<defs>'
        '<marker id="scriba-arrow-fwd" viewBox="0 0 10 10" refX="10" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        '<title>Arrowhead (forward)</title>'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/>'
        '</marker>'
        '<marker id="scriba-arrow-rev" viewBox="0 0 10 10" refX="0" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        '<title>Arrowhead (reverse)</title>'
        '<path d="M 10 0 L 0 5 L 10 10 z" fill="currentColor"/>'
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
@_protocol_register
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

    primitive_type = "graph"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "node[{id}]": "node by id",
        "edge[({u},{v})]": "edge by endpoints",
        "all": "all nodes and edges",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "nodes",
        "edges",
        "directed",
        "layout",
        "layout_seed",
        "layout_lambda",
        "seed",
        "show_weights",
        "label",
    })

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        self.nodes: list[str | int] = list(params.get("nodes", []))
        if not self.nodes:
            raise _animation_error(
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
            raise _animation_error(
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
                raise _animation_error(
                    "E1474",
                    detail=f"edge must be 2-tuple or 3-tuple, got {e!r}",
                )
        if has_weighted and has_unweighted:
            raise _animation_error(
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
            raise _animation_error(
                "E1505",
                f"Graph layout_seed must be a non-negative integer, "
                f"got {type(raw_seed).__name__} {raw_seed!r}",
            )
        if raw_seed < 0:
            raise _animation_error(
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
        if "add_edge" in params:
            spec = params["add_edge"]
            if not isinstance(spec, dict):
                raise _animation_error(
                    "E1471",
                    detail=f"add_edge requires a dict {{from, to}}, got {type(spec).__name__}",
                )
            u = spec.get("from")
            v = spec.get("to")
            weight = spec.get("weight")
            if u is None or v is None:
                raise _animation_error(
                    "E1471",
                    detail="add_edge requires {from, to}",
                )
            self._add_edge_internal(u, v, weight)
            return
        if "remove_edge" in params:
            spec = params["remove_edge"]
            if not isinstance(spec, dict):
                raise _animation_error(
                    "E1472",
                    detail=f"remove_edge requires a dict {{from, to}}, got {type(spec).__name__}",
                )
            self._remove_edge_internal(spec.get("from"), spec.get("to"))
            return
        if "set_weight" in params:
            spec = params["set_weight"]
            if not isinstance(spec, dict):
                raise _animation_error(
                    "E1473",
                    detail=f"set_weight requires a dict {{from, to, value}}, got {type(spec).__name__}",
                )
            self._set_weight_internal(
                spec.get("from"), spec.get("to"), spec.get("value")
            )
            return

    def _invalidate_addressable_cache(self) -> None:
        """Discard the cached addressable_parts and validate_selector results.

        Called by any mutation that changes graph topology (add_edge,
        remove_edge).  The cache is lazily rebuilt on the next call.
        """
        self.__dict__.pop("_cached_addressable_parts", None)
        self.__dict__.pop("_cached_addressable_set", None)

    def _add_edge_internal(
        self,
        u: str | int,
        v: str | int,
        weight: float | int | None,
    ) -> None:
        if u not in self.nodes:
            raise _animation_error(
                "E1471",
                detail=f"add_edge source node {u!r} is not in graph",
            )
        if v not in self.nodes:
            raise _animation_error(
                "E1471",
                detail=f"add_edge target node {v!r} is not in graph",
            )
        w: float | None = float(weight) if weight is not None else None
        self.edges.append((u, v, w))
        self._invalidate_addressable_cache()  # Opt-4: topology changed
        self._relayout_with_warm_start()

    def _remove_edge_internal(self, u: str | int, v: str | int) -> None:
        idx = self._find_edge_index(u, v)
        if idx is None:
            raise _animation_error(
                "E1472",
                detail=f"remove_edge: no edge between {u!r} and {v!r}",
            )
        self.edges.pop(idx)
        self._invalidate_addressable_cache()  # Opt-4: topology changed
        self._relayout_with_warm_start()

    def _set_weight_internal(
        self,
        u: str | int,
        v: str | int,
        value: float | int | None,
    ) -> None:
        if value is None:
            raise _animation_error(
                "E1473",
                detail="set_weight requires a numeric 'value'",
            )
        idx = self._find_edge_index(u, v)
        if idx is None:
            raise _animation_error(
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
        """Return all valid selector suffixes for this Graph instance.

        Opt-4: result is memoized on the instance after the first call.
        Graph topology is fixed at construction — no mutation path exists —
        so the cache is valid for the lifetime of the primitive.
        """
        cached = self.__dict__.get("_cached_addressable_parts")
        if cached is None:
            parts: list[str] = []
            for node_id in self.nodes:
                parts.append(self._node_key(node_id))
            for u, v, _w in self.edges:
                parts.append(self._edge_key(u, v))
            self.__dict__["_cached_addressable_parts"] = parts
            cached = parts
        return cached

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True
        # Opt-4: reuse the cached frozenset built from the cached parts list.
        cached_set = self.__dict__.get("_cached_addressable_set")
        if cached_set is None:
            cached_set = frozenset(self.addressable_parts())
            self.__dict__["_cached_addressable_set"] = cached_set
        return suffix in cached_set

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Map ``"G.node[A]"`` to the SVG ``(x, y)`` center of that node.

        Coordinates include the ``translate(r, r)`` offset applied by
        :meth:`emit_svg` so arrow endpoints line up with rendered nodes.
        """
        m = _GRAPH_NODE_SEL_RE.match(selector)
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
        return BoundingBox(
            x=0,
            y=0,
            width=self.width + 2 * r,
            height=self.height + 2 * r + arrow_above,
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
                f'<g data-primitive="graph" data-shape="{_escape_xml(self.name)}">'
                '</g>'
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
        # arrow_above so curves have room above the graph.
        ty = r + arrow_above
        parts.append(
            f'<g data-primitive="graph" data-shape="{_escape_xml(self.name)}"'
            f' transform="translate({r},{ty})">'
        )

        # Optional label / caption
        if self.label is not None:
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
        placed_edge_labels: list[_LabelPlacement] = []
        # GEP-03: visible node circles act as MUST-avoid AABB obstacles for
        # edge weight pills. Prevents F1/G1 (pill overlaps node circle on
        # short edges — confirmed in dinic.html / mcmf.html pre-fix).
        node_aabbs: list[_LabelPlacement] = [
            _LabelPlacement(
                x=float(self.positions[n][0]),
                y=float(self.positions[n][1]),
                width=float(2 * self._node_radius),
                height=float(2 * self._node_radius),
            )
            for n in self.nodes
            if n not in hidden_nodes
        ]
        # GEP-05: stable edge order — (state priority ASC, canonical edge key
        # ASC) — so identical graphs placed in different add_edge orders
        # produce byte-identical SVG output (D-1 determinism).
        def _edge_sort_key(
            edge: tuple[Any, Any, Any],
        ) -> tuple[int, str]:
            u_, v_, _w = edge
            state_ = self.get_state(self._edge_key(u_, v_))
            return (
                _EDGE_STATE_PRIO.get(state_, 99),
                self._edge_key(u_, v_),
            )
        parts.append('<g class="scriba-graph-edges">')
        for u, v, weight in sorted(self.edges, key=_edge_sort_key):
            edge_target = f"{self.name}.{self._edge_key(u, v)}"
            state = self.get_state(self._edge_key(u, v))
            # RFC-001 §4.4 — hidden edges are not rendered at all. Also
            # skip edges whose endpoints are hidden (would otherwise
            # render as a line going into empty space).
            if state == "hidden" or u in hidden_nodes or v in hidden_nodes:
                continue
            x1, y1 = self.positions[u]
            x2, y2 = self.positions[v]

            if self.directed:
                # Shorten line so arrowhead stops at circle boundary
                x2, y2 = _shorten_line_to_circle(x1, y1, x2, y2, self._node_radius)

            # GEP-01: pill sits on the visible segment — midpoint computed
            # from post-shortening endpoints. Perp-bias (GEP-06) replaces
            # the earlier magic `-4`; applied below once perp is known.
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            marker = ' marker-end="url(#scriba-arrow-fwd)"' if self.directed else ""
            edge_colors = svg_style_attrs(state)
            edge_stroke = edge_colors["stroke"]
            edge_sw = "1.5" if state == "idle" else "2"
            edge_label = (
                f"Edge from node {_escape_xml(str(u))} "
                f"to node {_escape_xml(str(v))}"
            )
            weight_text = ""
            # Dynamic value from \apply overrides the static weight.
            edge_suffix = self._edge_key(u, v)
            dynamic_val = self.get_value(edge_suffix)
            display_weight: str | None = None
            if dynamic_val is not None:
                display_weight = str(dynamic_val)
            elif self.show_weights and weight is not None:
                display_weight = _format_weight(weight)
            if display_weight is not None:
                # GEP-02: pill dimensions from module-level constants so the
                # constants survive ruff/style churn and share one source.
                tw = estimate_text_width(display_weight, _WEIGHT_FONT)
                th = _WEIGHT_FONT + 2
                pill_w = tw + _WEIGHT_PILL_PAD_X * 2
                pill_h = th + _WEIGHT_PILL_PAD_Y * 2

                # Edge direction + unit perpendicular (left-hand of flow).
                dx_edge = x2 - x1
                dy_edge = y2 - y1
                edge_len = math.hypot(dx_edge, dy_edge) or 1.0
                perp_x = -dy_edge / edge_len
                perp_y = dx_edge / edge_len

                # GEP-10: rotate pill + text along the visible stroke so
                # users can map a pill to its edge instantly on dense /
                # diagonal graphs. Normalize θ into [-π/2, π/2] so text
                # never renders upside-down (GEP-10 upright rule).
                # GEP-11: fall back to horizontal pill on degenerate edges
                # (coincident nodes) — perp vector is zero there.
                if edge_len < _WEIGHT_EDGE_MIN_LEN:
                    theta_rad = 0.0
                else:
                    _raw_theta = math.atan2(dy_edge, dx_edge)
                    if _raw_theta > math.pi / 2:
                        theta_rad = _raw_theta - math.pi
                    elif _raw_theta < -math.pi / 2:
                        theta_rad = _raw_theta + math.pi
                    else:
                        theta_rad = _raw_theta
                theta_deg = math.degrees(theta_rad)

                # GEP-06: initial placement = midpoint + perp-bias so the pill
                # sits perpendicular to the stroke, not an unconditional -4
                # y-offset. Correct for any edge angle including vertical.
                lx = mid_x + perp_x * _WEIGHT_PILL_PERP_BIAS
                ly = mid_y + perp_y * _WEIGHT_PILL_PERP_BIAS

                # GEP-09 / GEP-12: collision AABB = axis-aligned bounding
                # box of the rotated pill rect plus stroke-width pad. Over-
                # estimates the true OBB footprint by up to √2 on diagonals;
                # acceptable at E ≤ 50 (Phase 1 may upgrade to SAT OBB test).
                abs_cos = abs(math.cos(theta_rad))
                abs_sin = abs(math.sin(theta_rad))
                aabb_w = pill_w * abs_cos + pill_h * abs_sin + _WEIGHT_PILL_STROKE_PAD
                aabb_h = pill_w * abs_sin + pill_h * abs_cos + _WEIGHT_PILL_STROKE_PAD
                candidate = _LabelPlacement(
                    x=lx, y=ly, width=aabb_w, height=aabb_h
                )

                # GEP-07 v1.2: along-edge shift first (preserves GEP-10
                # binding), perp nudge as fallback, origin as last resort.
                # See _nudge_pill_placement for the three-stage protocol.
                ux = dx_edge / edge_len
                uy = dy_edge / edge_len
                max_shift_along = max(
                    0.0,
                    edge_len / 2 - pill_w / 2 - self._node_radius,
                )
                lx, ly = _nudge_pill_placement(
                    mid_x=lx,
                    mid_y=ly,
                    ux=ux,
                    uy=uy,
                    perp_x=perp_x,
                    perp_y=perp_y,
                    pill_w=pill_w,
                    pill_h=pill_h,
                    aabb_w=aabb_w,
                    aabb_h=aabb_h,
                    max_shift_along=max_shift_along,
                    node_aabbs=node_aabbs,
                    placed_pills=placed_edge_labels,
                )
                candidate = _LabelPlacement(
                    x=lx, y=ly, width=aabb_w, height=aabb_h
                )

                # GEP-08: clamp pill centre into the viewbox so a pill near
                # the canvas boundary never spills outside.
                lx = max(
                    pill_w / 2,
                    min(float(self.width) - pill_w / 2, lx),
                )
                ly = max(
                    pill_h / 2,
                    min(float(self.height) - pill_h / 2, ly),
                )
                candidate = _LabelPlacement(
                    x=lx, y=ly, width=aabb_w, height=aabb_h
                )
                placed_edge_labels.append(candidate)

                # GEP-10: pill rect + text wrapped in a <g transform="rotate">
                # so the pill rotates as a unit around its own centre. Text
                # remains centred in the pill's local frame regardless of
                # edge angle. GEP-13: rotate the outer <g>, NEVER the inner
                # <foreignObject> (KaTeX path) — Safari has a known sub-pixel
                # rendering bug for transforms on <foreignObject>.
                pill_rx = lx - pill_w / 2
                pill_ry = ly - pill_h / 2
                _pill_svg = (
                    f'<rect x="{pill_rx:.1f}" y="{pill_ry:.1f}" '
                    f'width="{pill_w}" height="{pill_h}" '
                    f'rx="{_WEIGHT_PILL_R}" fill="white" fill-opacity="0.85" '
                    f'stroke="{THEME["border"]}" stroke-width="0.5"/>'
                ) + _render_svg_text(
                    display_weight, lx, ly,
                    fill=THEME["fg_muted"],
                    text_anchor="middle",
                    dominant_baseline="central",
                    css_class="scriba-graph-weight",
                    render_inline_tex=render_inline_tex,
                )
                if abs(theta_deg) < 0.05:
                    weight_text = _pill_svg
                else:
                    weight_text = (
                        f'<g transform="rotate({theta_deg:.2f} '
                        f'{lx:.1f} {ly:.1f})">'
                        f'{_pill_svg}'
                        f'</g>'
                    )
            parts.append(
                f'<g data-target="{_escape_xml(edge_target)}" '
                f'class="{state_class(state)}" '
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
                f'<g data-target="{_escape_xml(node_target)}" '
                f'class="{state_class(effective_state)}">'
                f'<circle cx="{cx}" cy="{cy}" r="{self._node_radius}"/>'
                f'{node_text}'
                f'</g>'
            )
        parts.append('</g>')

        # --- Annotation arrows (rendered on top of everything) ---
        if effective_anns:
            arrow_lines: list[str] = []
            # Phase D/2 (v0.14.0): CellMetrics proxy for 2D graph → activates
            # stagger-flip in _compute_control_points. Graph has no grid;
            # node-diameter stands in as the local "cell" scale.
            _diam = float(self._node_radius * 2)
            graph_cm = CellMetrics(
                cell_width=_diam,
                cell_height=_diam,
                grid_cols=len(self.nodes) or 1,
                grid_rows=1,
                origin_x=0.0,
                origin_y=0.0,
            )
            self.emit_annotation_arrows(
                arrow_lines,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
                cell_metrics=graph_cm,
            )
            parts.extend(arrow_lines)

        parts.append('</g>')
        return ''.join(parts)

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []
