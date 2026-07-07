"""Graph force-layout canvas scaling (research-graph-scaling.md).

The force layout solved and clamped every graph into a hard-coded 400x300
canvas; Fruchterman-Reingold's ideal spacing ``k = sqrt(area/n)`` collapses
as N grows (k=34.6 < min_sep=36 at N=100), so ``_resolve_overlaps`` just
oscillated against the clamp — overlapping nodes from N~40, coincident
nodes from N~75.

The fix under test: ``_grow_force_canvas(n)`` sizes the canvas by AREA per
node (``max(400*300, 6300*n)``, 4:3 aspect preserved, floored at the
default so N <= 19 stays byte-identical — mirroring Tree's max()-floored
grow), plus an overlap post-pass relaxed to ``max(10, N)`` passes gated on
the canvas actually growing. Positions and canvas are computed once in
``__init__`` and no mutation re-solves, so R-32 pin-stability holds by
construction.
"""

from __future__ import annotations

import math

import pytest

from scriba.animation.primitives.graph import (
    _DEFAULT_HEIGHT,
    _DEFAULT_WIDTH,
    Graph,
)


def _ring_chords(n: int) -> list[tuple[int, int]]:
    """Deterministic ring + long chords — the probe topology."""
    edges = [(i, (i + 1) % n) for i in range(n)]
    edges += [(i, (i + n // 3) % n) for i in range(0, n, 5)]
    return edges


def _min_pairwise_dist(points: list[tuple[float, float]]) -> float:
    best = float("inf")
    for i, (x1, y1) in enumerate(points):
        for x2, y2 in points[i + 1:]:
            d = math.hypot(x1 - x2, y1 - y2)
            if d < best:
                best = d
    return best


class TestForceCanvasScaling:
    @pytest.mark.unit
    @pytest.mark.parametrize("n", [40, 100])
    def test_force_no_overlap_at_scale(self, n: int) -> None:
        """No circle intersection and no coincident nodes at scale."""
        g = Graph("G", {"nodes": list(range(n)), "edges": _ring_chords(n)})
        pts = [tuple(map(float, p)) for p in g.positions.values()]
        d = _min_pairwise_dist(pts)
        assert d > 0.0, "coincident nodes"
        assert d >= 2 * g._node_radius, (
            f"node circles intersect at N={n}: min center distance "
            f"{d:.1f} < {2 * g._node_radius}"
        )

    @pytest.mark.unit
    def test_small_graph_canvas_inert(self) -> None:
        """N <= 16 keeps the default canvas — the byte-identity floor."""
        for n in (2, 6, 9, 16):
            g = Graph(
                "G",
                {"nodes": list(range(n)), "edges": [(i, (i + 1) % n) for i in range(n)]},
            )
            assert g.width == _DEFAULT_WIDTH, f"N={n} canvas width grew"
            assert g.height == _DEFAULT_HEIGHT, f"N={n} canvas height grew"

    @pytest.mark.unit
    def test_positions_stable_across_edge_mutation(self) -> None:
        """R-32: add_edge/remove_edge never move a node (grow is __init__-only)."""
        g = Graph(
            "G",
            {"nodes": list(range(24)), "edges": _ring_chords(24)},
        )
        before = dict(g.positions)
        g.apply_command({"add_edge": {"from": 0, "to": 7}})
        g.apply_command({"remove_edge": {"from": 0, "to": 7}})
        assert g.positions == before

    @pytest.mark.unit
    @pytest.mark.parametrize("n", [40, 100])
    def test_grown_canvas_viewbox_contains_nodes(self, n: int) -> None:
        """Painted node circles stay inside the (grown) viewBox — the
        painted-extent honesty invariant at any canvas size."""
        g = Graph("G", {"nodes": list(range(n)), "edges": _ring_chords(n)})
        r = g._node_radius
        left_pad, _right = g._h_label_pad()
        bb = g.bounding_box()
        for node_id, (cx, cy) in g.positions.items():
            px = r + left_pad + cx
            py = r + cy
            assert px - r >= 0 and px + r <= bb.width, f"node {node_id} x-clip"
            assert py - r >= 0 and py + r <= bb.height, f"node {node_id} y-clip"

    @pytest.mark.unit
    def test_grow_threshold(self) -> None:
        """Pins the byte threshold: inert through N=16, grows at N=17."""
        from scriba.animation.primitives.graph import _grow_force_canvas

        assert _grow_force_canvas(16) == (_DEFAULT_WIDTH, _DEFAULT_HEIGHT)
        w17, h17 = _grow_force_canvas(17)
        assert w17 > _DEFAULT_WIDTH and h17 > _DEFAULT_HEIGHT
        # aspect preserved (4:3) within rounding
        assert abs(w17 / h17 - _DEFAULT_WIDTH / _DEFAULT_HEIGHT) < 0.02
