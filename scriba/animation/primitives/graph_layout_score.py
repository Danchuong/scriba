"""Pure layout-quality scorer for force-directed Graph layouts.

Phase 3 of ``docs/plans/layout-seed-fix-plan-2026-06-03.md``.

``score_layout`` rates a candidate node placement for *readability* — lower
is better.  It is a pure, deterministic function: no RNG, no rendering, no
side effects.  The auto-seed sweep in ``graph.py`` calls it once per candidate
seed and keeps the lowest-scoring layout.

The score combines three readability penalties, each documented as a named
constant below:

1. **Edge crossings** (primary) — count intersecting edge pairs, normalised by
   edge count.  Crossings are the single most legibility-damaging defect.
2. **Border-hugging** — penalise connected nodes that sit within ~1 node-radius
   of any canvas border (force layouts shove nodes to the edge when repulsion
   dominates).
3. **Spread** — reward filling the canvas; penalise clustering via low
   bounding-box fill.

Conventions (``_PADDING`` / ``_NODE_RADIUS``) mirror ``graph.py`` but are kept
as local constants so this module has no import-time dependency on it.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Layout conventions — mirror scriba.animation.primitives.graph
# ---------------------------------------------------------------------------

_PADDING = 20
_NODE_RADIUS = 20

# ---------------------------------------------------------------------------
# Penalty weights.  Tuned so edge crossings dominate (the worst readability
# defect), border-hugging is a clear secondary signal, and spread is a gentle
# tie-breaker that nudges toward canvas-filling layouts without overriding the
# topological signals above.
# ---------------------------------------------------------------------------

# Per normalised crossing (crossings / edge-count).  Highest weight: a single
# crossing is worse than several border-hugging nodes.
_W_CROSSINGS = 10.0

# Per fraction of connected nodes hugging a border.
_W_BORDER = 3.0

# Applied to (1 - bounding-box fill ratio): a tightly clustered layout that
# uses little of the canvas is penalised most.
_W_SPREAD = 1.0


def _segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> bool:
    """Return True if segment ``p1->p2`` properly crosses ``p3->p4``.

    Uses the standard orientation (signed-area) test.  Collinear/touching
    cases return False — we only count genuine X-shaped crossings, not edges
    that merely share an endpoint or graze each other, since shared endpoints
    are expected and not a readability defect.
    """

    def _orient(
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
    ) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1 = _orient(p3, p4, p1)
    d2 = _orient(p3, p4, p2)
    d3 = _orient(p1, p2, p3)
    d4 = _orient(p1, p2, p4)
    # Strict opposite orientations on both segments => proper crossing.
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def score_layout(
    positions: dict,
    edges: list,
    width: int,
    height: int,
) -> float:
    """Score a candidate layout for readability.  LOWER is better.

    Parameters
    ----------
    positions:
        Mapping ``node -> (x, y)`` for every node in the layout.
    edges:
        List of ``(u, v)`` 2-tuples or ``(u, v, weight)`` 3-tuples.  The weight
        is ignored.  Edges whose endpoint is missing from *positions* are
        skipped.
    width, height:
        Canvas dimensions (used for border and spread normalisation).

    Pure and deterministic: identical inputs always yield an identical score.
    """
    # --- Normalise edges to endpoint pairs, dropping unknown endpoints. ---
    edge_pairs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for e in edges:
        u, v = e[0], e[1]  # ignore weight on 3-tuples
        if u in positions and v in positions:
            edge_pairs.append((positions[u], positions[v]))

    # --- 1. Edge crossings (primary). ---
    # Count intersecting edge pairs that do not share an endpoint, normalised
    # by edge count so dense and sparse graphs are comparable.
    crossings = 0
    for i in range(len(edge_pairs)):
        a1, a2 = edge_pairs[i]
        for j in range(i + 1, len(edge_pairs)):
            b1, b2 = edge_pairs[j]
            # Skip pairs sharing an endpoint (coords identical) — they meet at
            # a node, which is not a crossing.
            if a1 in (b1, b2) or a2 in (b1, b2):
                continue
            if _segments_intersect(a1, a2, b1, b2):
                crossings += 1
    crossing_score = crossings / len(edge_pairs) if edge_pairs else 0.0

    # --- Connected nodes only (endpoints of at least one kept edge). ---
    # Isolated nodes are lane-fixed by graph.py, so they carry no readability
    # signal here — exclude them from border and spread terms.
    connected: set = set()
    for e in edges:
        u, v = e[0], e[1]
        if u in positions and v in positions:
            connected.add(u)
            connected.add(v)
    conn_pts = [positions[n] for n in connected]

    # --- 2. Border-hugging. ---
    # Fraction of connected nodes within ~1 node-radius of any border.
    border_margin = _PADDING + _NODE_RADIUS
    if conn_pts:
        hugging = sum(
            1
            for (x, y) in conn_pts
            if x <= border_margin
            or x >= width - border_margin
            or y <= border_margin
            or y >= height - border_margin
        )
        border_score = hugging / len(conn_pts)
    else:
        border_score = 0.0

    # --- 3. Spread. ---
    # Reward filling the canvas: 1 - (bbox area / canvas area).  A cluster in
    # one corner has a tiny bbox => high penalty.  A single connected node has
    # no spread to measure => no penalty.
    if len(conn_pts) >= 2:
        xs = [p[0] for p in conn_pts]
        ys = [p[1] for p in conn_pts]
        bbox_w = max(xs) - min(xs)
        bbox_h = max(ys) - min(ys)
        canvas_area = float(width * height) or 1.0
        fill_ratio = (bbox_w * bbox_h) / canvas_area
        spread_score = max(0.0, 1.0 - fill_ratio)
    else:
        spread_score = 0.0

    return (
        _W_CROSSINGS * crossing_score
        + _W_BORDER * border_score
        + _W_SPREAD * spread_score
    )
