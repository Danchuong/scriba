"""Tests for Graph mutation + warm-start layout (Wave 6.2).

Covers RFC-001 §4.2:
    - 2-tuple and 3-tuple edge syntax
    - show_weights rendering
    - apply_command dispatcher (add_edge, remove_edge, set_weight)
    - E1471 / E1472 / E1473 / E1474 error codes
    - Warm-start relayout keeps positions close to their pre-mutation values
"""

from __future__ import annotations

import math

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.primitives.graph import Graph, _nudge_pill_placement
from scriba.animation.primitives._svg_helpers import _LabelPlacement


# ---------------------------------------------------------------------------
# Edge syntax
# ---------------------------------------------------------------------------


class TestEdgeSyntax:
    """Parsing 2-tuple (unweighted) and 3-tuple (weighted) edges."""

    def test_two_tuple_edges_unweighted(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B", "C"], "edges": [("A", "B"), ("B", "C")]},
        )
        assert g.edges == [("A", "B", None), ("B", "C", None)]

    def test_three_tuple_edges_weighted(self) -> None:
        g = Graph(
            "G",
            {
                "nodes": ["A", "B", "C"],
                "edges": [("A", "B", 1.5), ("B", "C", 2.0)],
            },
        )
        assert g.edges == [("A", "B", 1.5), ("B", "C", 2.0)]

    def test_three_tuple_edges_integer_weight_coerced_to_float(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B"], "edges": [("A", "B", 3)]},
        )
        assert g.edges == [("A", "B", 3.0)]
        assert isinstance(g.edges[0][2], float)

    def test_mixed_weighted_and_unweighted_raises_e1474(self) -> None:
        with pytest.raises(AnimationError) as exc:
            Graph(
                "G",
                {
                    "nodes": ["A", "B", "C"],
                    "edges": [("A", "B", 1.0), ("B", "C")],
                },
            )
        assert exc.value.code == "E1474"

    def test_one_tuple_edge_raises_e1474(self) -> None:
        with pytest.raises(AnimationError) as exc:
            Graph("G", {"nodes": ["A"], "edges": [("A",)]})
        assert exc.value.code == "E1474"

    def test_four_tuple_edge_raises_e1474(self) -> None:
        with pytest.raises(AnimationError) as exc:
            Graph(
                "G",
                {
                    "nodes": ["A", "B"],
                    "edges": [("A", "B", 1.0, "extra")],
                },
            )
        assert exc.value.code == "E1474"

    def test_empty_edges_accepted(self) -> None:
        g = Graph("G", {"nodes": ["A"], "edges": []})
        assert g.edges == []


# ---------------------------------------------------------------------------
# show_weights rendering
# ---------------------------------------------------------------------------


class TestShowWeights:
    """show_weights flag renders per-edge midpoint text in emit_svg."""

    def test_show_weights_default_off(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B"], "edges": [("A", "B", 5.0)]},
        )
        assert g.show_weights is False
        svg = g.emit_svg()
        assert "scriba-graph-weight" not in svg

    def test_show_weights_renders_text(self) -> None:
        g = Graph(
            "G",
            {
                "nodes": ["A", "B"],
                "edges": [("A", "B", 5.0)],
                "show_weights": True,
            },
        )
        svg = g.emit_svg()
        assert "scriba-graph-weight" in svg
        # Integer weights render without decimal tail.
        assert ">5<" in svg

    def test_show_weights_renders_float_trimmed(self) -> None:
        g = Graph(
            "G",
            {
                "nodes": ["A", "B"],
                "edges": [("A", "B", 1.5)],
                "show_weights": True,
            },
        )
        svg = g.emit_svg()
        assert ">1.5<" in svg

    def test_show_weights_skipped_for_unweighted(self) -> None:
        """No weight text when weight is None (purely unweighted graph)."""
        g = Graph(
            "G",
            {
                "nodes": ["A", "B"],
                "edges": [("A", "B")],
                "show_weights": True,
            },
        )
        svg = g.emit_svg()
        assert "scriba-graph-weight" not in svg

    def test_show_weights_for_directed(self) -> None:
        """Directed graphs show midpoint weight labels (flow networks)."""
        g = Graph(
            "G",
            {
                "nodes": ["A", "B"],
                "edges": [("A", "B", 2.0)],
                "directed": True,
                "show_weights": True,
            },
        )
        svg = g.emit_svg()
        assert "scriba-graph-weight" in svg

    def test_show_weights_multiple_edges(self) -> None:
        g = Graph(
            "G",
            {
                "nodes": ["A", "B", "C"],
                "edges": [("A", "B", 1.0), ("B", "C", 2.0)],
                "show_weights": True,
            },
        )
        svg = g.emit_svg()
        # Both weights should appear.
        assert svg.count("scriba-graph-weight") == 2


# ---------------------------------------------------------------------------
# apply_command dispatcher
# ---------------------------------------------------------------------------


def _positions_close(
    a: dict[str | int, tuple[int, int]],
    b: dict[str | int, tuple[int, int]],
    tolerance: float,
) -> bool:
    for k in a:
        if k not in b:
            return False
        dx = a[k][0] - b[k][0]
        dy = a[k][1] - b[k][1]
        if math.sqrt(dx * dx + dy * dy) > tolerance:
            return False
    return True


class TestApplyCommand:
    """apply_command dispatches to add_edge/remove_edge/set_weight."""

    def test_add_edge_unweighted(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B", "C"], "edges": [("A", "B")]},
        )
        g.apply_command({"add_edge": {"from": "B", "to": "C"}})
        assert ("B", "C", None) in g.edges

    def test_add_edge_weighted(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B", "C"], "edges": [("A", "B", 1.0)]},
        )
        g.apply_command({"add_edge": {"from": "B", "to": "C", "weight": 3.5}})
        assert ("B", "C", 3.5) in g.edges

    def test_add_edge_unknown_source_raises_e1471(self) -> None:
        g = Graph("G", {"nodes": ["A", "B"], "edges": [("A", "B")]})
        with pytest.raises(AnimationError) as exc:
            g.apply_command({"add_edge": {"from": "Z", "to": "A"}})
        assert exc.value.code == "E1471"

    def test_add_edge_unknown_target_raises_e1471(self) -> None:
        g = Graph("G", {"nodes": ["A", "B"], "edges": [("A", "B")]})
        with pytest.raises(AnimationError) as exc:
            g.apply_command({"add_edge": {"from": "A", "to": "Z"}})
        assert exc.value.code == "E1471"

    def test_add_edge_missing_to_raises_e1471(self) -> None:
        g = Graph("G", {"nodes": ["A", "B"], "edges": []})
        with pytest.raises(AnimationError) as exc:
            g.apply_command({"add_edge": {"from": "A"}})
        assert exc.value.code == "E1471"

    def test_add_edge_bad_spec_raises_e1471(self) -> None:
        g = Graph("G", {"nodes": ["A", "B"], "edges": []})
        with pytest.raises(AnimationError) as exc:
            g.apply_command({"add_edge": "not-a-dict"})
        assert exc.value.code == "E1471"

    def test_remove_edge_undirected_matches_either_order(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B"], "edges": [("A", "B")]},
        )
        g.apply_command({"remove_edge": {"from": "B", "to": "A"}})
        assert g.edges == []

    def test_remove_edge_directed_requires_exact_order(self) -> None:
        g = Graph(
            "G",
            {
                "nodes": ["A", "B"],
                "edges": [("A", "B")],
                "directed": True,
            },
        )
        with pytest.raises(AnimationError) as exc:
            g.apply_command({"remove_edge": {"from": "B", "to": "A"}})
        assert exc.value.code == "E1472"
        # Forward direction works.
        g.apply_command({"remove_edge": {"from": "A", "to": "B"}})
        assert g.edges == []

    def test_remove_edge_missing_raises_e1472(self) -> None:
        g = Graph("G", {"nodes": ["A", "B"], "edges": [("A", "B")]})
        with pytest.raises(AnimationError) as exc:
            g.apply_command({"remove_edge": {"from": "A", "to": "Z"}})
        assert exc.value.code == "E1472"

    def test_remove_edge_bad_spec_raises_e1472(self) -> None:
        g = Graph("G", {"nodes": ["A"], "edges": []})
        with pytest.raises(AnimationError) as exc:
            g.apply_command({"remove_edge": ["A", "B"]})
        assert exc.value.code == "E1472"

    def test_set_weight_updates_value(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B"], "edges": [("A", "B", 1.0)]},
        )
        g.apply_command({"set_weight": {"from": "A", "to": "B", "value": 9.0}})
        assert g.edges == [("A", "B", 9.0)]

    def test_set_weight_undirected_matches_either_order(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B"], "edges": [("A", "B", 1.0)]},
        )
        g.apply_command({"set_weight": {"from": "B", "to": "A", "value": 4.5}})
        assert g.edges == [("A", "B", 4.5)]

    def test_set_weight_missing_edge_raises_e1473(self) -> None:
        g = Graph("G", {"nodes": ["A", "B"], "edges": []})
        with pytest.raises(AnimationError) as exc:
            g.apply_command(
                {"set_weight": {"from": "A", "to": "B", "value": 2.0}}
            )
        assert exc.value.code == "E1473"

    def test_set_weight_missing_value_raises_e1473(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B"], "edges": [("A", "B", 1.0)]},
        )
        with pytest.raises(AnimationError) as exc:
            g.apply_command({"set_weight": {"from": "A", "to": "B"}})
        assert exc.value.code == "E1473"

    def test_set_weight_bad_spec_raises_e1473(self) -> None:
        g = Graph("G", {"nodes": ["A"], "edges": []})
        with pytest.raises(AnimationError) as exc:
            g.apply_command({"set_weight": "not-a-dict"})
        assert exc.value.code == "E1473"

    def test_apply_command_no_op_without_known_key(self) -> None:
        g = Graph("G", {"nodes": ["A"], "edges": []})
        # Unknown op silently no-ops (future hooks may extend).
        g.apply_command({"unknown_op": {}})
        assert g.edges == []


# ---------------------------------------------------------------------------
# Warm-start relayout
# ---------------------------------------------------------------------------


class TestWarmStartRelayout:
    """Positions before and after a mutation should stay close."""

    def test_add_edge_warm_start_keeps_positions_close(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B", "C", "D"], "edges": [("A", "B"), ("C", "D")]},
        )
        before = dict(g.positions)
        g.apply_command({"add_edge": {"from": "B", "to": "C"}})
        after = dict(g.positions)
        # Both should exist with same keys.
        assert set(before.keys()) == set(after.keys())
        # Warm-start layout should stay within ~75% of the canvas
        # diagonal — looser than zero because SA re-anneals from
        # high temperature, but still much tighter than the ~full
        # canvas excursion a cold init would permit.
        tolerance = 0.75 * math.sqrt(g.width ** 2 + g.height ** 2)
        assert _positions_close(before, after, tolerance)

    def test_remove_edge_warm_start_keeps_positions_close(self) -> None:
        g = Graph(
            "G",
            {
                "nodes": ["A", "B", "C", "D"],
                "edges": [("A", "B"), ("B", "C"), ("C", "D")],
            },
        )
        before = dict(g.positions)
        g.apply_command({"remove_edge": {"from": "A", "to": "B"}})
        after = dict(g.positions)
        tolerance = 0.75 * math.sqrt(g.width ** 2 + g.height ** 2)
        assert _positions_close(before, after, tolerance)

    def test_set_weight_does_not_relayout(self) -> None:
        """Weight changes must not disturb geometry."""
        g = Graph(
            "G",
            {"nodes": ["A", "B"], "edges": [("A", "B", 1.0)]},
        )
        before = dict(g.positions)
        g.apply_command(
            {"set_weight": {"from": "A", "to": "B", "value": 99.0}}
        )
        after = dict(g.positions)
        assert before == after

    def test_large_graph_fallback_to_force_layout(self) -> None:
        """Stable layout caps at 20 nodes; 21+ falls back via force layout."""
        # Graph primitive itself caps at 100; pick 21 to bypass SA.
        nodes = [f"n{i}" for i in range(21)]
        edges = [(f"n{i}", f"n{i+1}") for i in range(20)]
        g = Graph("G", {"nodes": nodes, "edges": edges})
        before = dict(g.positions)
        g.apply_command({"add_edge": {"from": "n0", "to": "n5"}})
        after = dict(g.positions)
        # Force layout is deterministic on seed so positions should
        # still be valid tuples of ints.
        assert set(before.keys()) == set(after.keys())
        for _, (x, y) in after.items():
            assert isinstance(x, int)
            assert isinstance(y, int)

    def test_svg_after_mutation_is_valid(self) -> None:
        """emit_svg still works after mutation sequence."""
        g = Graph(
            "G",
            {"nodes": ["A", "B", "C"], "edges": [("A", "B")]},
        )
        g.apply_command({"add_edge": {"from": "B", "to": "C", "weight": 2.0}})
        g.apply_command({"set_weight": {"from": "A", "to": "B", "value": 1.0}})
        svg = g.emit_svg()
        assert '<g data-primitive="graph"' in svg
        assert "</g>" in svg

    def test_addressable_parts_reflect_mutation(self) -> None:
        g = Graph("G", {"nodes": ["A", "B", "C"], "edges": [("A", "B")]})
        assert "edge[(A,B)]" in g.addressable_parts()
        assert "edge[(B,C)]" not in g.addressable_parts()
        g.apply_command({"add_edge": {"from": "B", "to": "C"}})
        assert "edge[(B,C)]" in g.addressable_parts()
        g.apply_command({"remove_edge": {"from": "A", "to": "B"}})
        assert "edge[(A,B)]" not in g.addressable_parts()


# ---------------------------------------------------------------------------
# RFC-001 §4.4 — hidden state on Graph
# ---------------------------------------------------------------------------


class TestHiddenState:
    """Hidden nodes and edges must be omitted from emit_svg entirely.

    W7.1 (cookbook Dijkstra/Kruskal) flagged that Graph.emit_svg did not
    honor the 'hidden' state at v0.6.0-alpha1 time. Fixed in the v0.6.0
    GA release commit — this test class is the regression sentinel.
    """

    def _make_triangle(self) -> Graph:
        return Graph(
            "G",
            {
                "nodes": ["A", "B", "C"],
                "edges": [("A", "B"), ("B", "C"), ("A", "C")],
            },
        )

    def test_hidden_node_omitted_from_svg(self) -> None:
        g = self._make_triangle()
        g.set_state("node[B]", "hidden")
        svg = g.emit_svg()
        assert 'data-target="G.node[B]"' not in svg
        assert 'data-target="G.node[A]"' in svg
        assert 'data-target="G.node[C]"' in svg

    def test_hidden_edge_omitted_from_svg(self) -> None:
        g = self._make_triangle()
        g.set_state("edge[(A,B)]", "hidden")
        svg = g.emit_svg()
        assert 'data-target="G.edge[(A,B)]"' not in svg
        assert 'data-target="G.edge[(B,C)]"' in svg

    def test_hidden_node_also_hides_incident_edges(self) -> None:
        """Edges incident on a hidden node are also skipped to avoid
        dangling lines into empty space (matches Tree.emit_svg)."""
        g = self._make_triangle()
        g.set_state("node[B]", "hidden")
        svg = g.emit_svg()
        # B is hidden, so A-B and B-C both vanish; A-C remains
        assert 'data-target="G.edge[(A,B)]"' not in svg
        assert 'data-target="G.edge[(B,C)]"' not in svg
        assert 'data-target="G.edge[(A,C)]"' in svg

    def test_hidden_state_is_reversible(self) -> None:
        """Toggling hidden -> idle restores rendering."""
        g = self._make_triangle()
        g.set_state("node[B]", "hidden")
        assert 'data-target="G.node[B]"' not in g.emit_svg()
        g.set_state("node[B]", "idle")
        assert 'data-target="G.node[B]"' in g.emit_svg()


# ---------------------------------------------------------------------------
# GEP-07 v1.2 — _nudge_pill_placement unit tests
# ---------------------------------------------------------------------------

# Shared pill geometry (single-digit weight, font=11, pad_x=5, pad_y=2).
_TW = 7          # text width of a 1-char label
_PILL_W = _TW + 5 * 2   # = 17
_PILL_H = 11 + 2 + 2 * 2  # = 17
# AABB for a near-horizontal B→D-like edge (theta ~9°).
_AABB_W = 20.37
_AABB_H = 20.37


def _lp(x: float, y: float, w: float = _AABB_W, h: float = _AABB_H) -> _LabelPlacement:
    return _LabelPlacement(x=x, y=y, width=w, height=h)


@pytest.mark.unit
def test_crossing_edges_resolved_by_along_shift() -> None:
    """B→D pill slides along stroke to escape A→C pill collision.

    Geometry mirrors the mcmf A→C / B→D crossing from the impl plan.
    Step = aabb_w + 2 = 22.37 (rotated-AABB stepping, GEP-07 v1.2).
    Expected: B→D pill lands at (172.38, 140.63) ±0.05 — on the stroke
    (delta_perp ≈ 0), shifted along edge by one step.
    """
    # B→D edge: B=(293,159), D=(96,129)
    bx, by = 293.0, 159.0
    dx2, dy2 = 96.0, 129.0
    edge_len = math.hypot(dx2 - bx, dy2 - by)
    dxe = dx2 - bx
    dye = dy2 - by
    ux = dxe / edge_len
    uy = dye / edge_len
    perp_x = -dye / edge_len
    perp_y = dxe / edge_len
    mid_x = (bx + dx2) / 2   # 194.5
    mid_y = (by + dy2) / 2   # 144.0
    max_shift_along = max(0.0, edge_len / 2 - _PILL_W / 2 - 20)

    # A→C pill (already placed) at the on-edge midpoint, blocks B→D origin.
    placed = [_lp(199.0, 131.5)]

    lx, ly = _nudge_pill_placement(
        mid_x=mid_x,
        mid_y=mid_y,
        ux=ux,
        uy=uy,
        perp_x=perp_x,
        perp_y=perp_y,
        pill_w=_PILL_W,
        pill_h=_PILL_H,
        aabb_w=_AABB_W,
        aabb_h=_AABB_H,
        max_shift_along=max_shift_along,
        node_aabbs=[],
        placed_pills=placed,
    )

    assert abs(lx - 172.38) < 0.05, f"lx={lx:.4f}, expected ~172.38"
    assert abs(ly - 140.63) < 0.05, f"ly={ly:.4f}, expected ~140.63"

    # Pill must remain on stroke: perp displacement ≈ 0.
    # delta_perp = (lx - mid_x)*perp_x + (ly - mid_y)*perp_y
    delta_perp = (lx - mid_x) * perp_x + (ly - mid_y) * perp_y
    assert abs(delta_perp) < 0.1, f"delta_perp={delta_perp:.4f}, expected ≈0"


@pytest.mark.unit
def test_along_shift_respects_node_budget() -> None:
    """Short edge disables along-shift; perp nudge or origin fallback used.

    edge_len=48, node_r=20: max_shift_along = max(0, 24 - 8.5 - 20) = 0.
    Along-shift must be skipped; result must not be inside any node AABB.
    """
    # Horizontal short edge: A=(100,100), B=(148,100)
    ax, ay = 100.0, 100.0
    bx, by = 148.0, 100.0
    edge_len = math.hypot(bx - ax, by - ay)  # = 48.0
    ux, uy = (bx - ax) / edge_len, 0.0
    perp_x, perp_y = 0.0, 1.0  # left-hand perp for horizontal edge
    mid_x = (ax + bx) / 2  # = 124.0
    mid_y = ay              # = 100.0
    node_r = 20
    max_shift_along = max(0.0, edge_len / 2 - _PILL_W / 2 - node_r)
    assert max_shift_along == 0.0, "precondition: short edge disables along-shift"

    # Place a blocker at the origin so nudge is forced.
    placed = [_lp(mid_x, mid_y)]
    # Node AABBs at both endpoints.
    node_aabbs = [
        _lp(ax, ay, w=2 * node_r, h=2 * node_r),
        _lp(bx, by, w=2 * node_r, h=2 * node_r),
    ]

    lx, ly = _nudge_pill_placement(
        mid_x=mid_x,
        mid_y=mid_y,
        ux=ux,
        uy=uy,
        perp_x=perp_x,
        perp_y=perp_y,
        pill_w=_PILL_W,
        pill_h=_PILL_H,
        aabb_w=_AABB_W,
        aabb_h=_AABB_H,
        max_shift_along=max_shift_along,
        node_aabbs=node_aabbs,
        placed_pills=placed,
    )

    # Result must not overlap either node AABB.
    result = _lp(lx, ly)
    for n in node_aabbs:
        assert not result.overlaps(n), f"pill at ({lx:.1f},{ly:.1f}) overlaps node AABB"

    # Stage-pinning (GEP-07 v1.2): Stage 1 skipped (budget=0); Stage 2 perp
    # nudge lands at +2·step_perp (±1x collides nodes). Origin fallback must
    # NOT be used here — that would leave the pill overlapping the blocker.
    assert (lx, ly) != (mid_x, mid_y), "must not return origin (blocker unresolved)"
    step_perp = _AABB_H + 2
    assert abs(lx - mid_x) < 1e-9, f"lx={lx:.4f}, expected mid_x={mid_x} (pure perp)"
    assert abs(ly - (mid_y + 2 * step_perp)) < 1e-9, (
        f"ly={ly:.4f}, expected {mid_y + 2 * step_perp:.4f} (+2·step_perp)"
    )


@pytest.mark.unit
def test_along_shift_never_overlaps_node_circle() -> None:
    """K4 graph: every placed pill must clear all node AABBs.

    Nodes at (100,80),(300,80),(300,220),(100,220).  All 6 undirected edges
    are processed sequentially; verify no final pill overlaps a node AABB.
    """
    nodes = [(100.0, 80.0), (300.0, 80.0), (300.0, 220.0), (100.0, 220.0)]
    node_r = 20
    node_aabbs = [_lp(nx, ny, w=2 * node_r, h=2 * node_r) for nx, ny in nodes]

    placed: list[_LabelPlacement] = []

    # Enumerate all 6 undirected K4 edges (deterministic order).
    edges = [
        (nodes[i], nodes[j])
        for i in range(len(nodes))
        for j in range(i + 1, len(nodes))
    ]

    for (x1, y1), (x2, y2) in edges:
        edge_len = math.hypot(x2 - x1, y2 - y1) or 1.0
        dxe = x2 - x1
        dye = y2 - y1
        ux = dxe / edge_len
        uy = dye / edge_len
        perp_x = -dye / edge_len
        perp_y = dxe / edge_len
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        max_shift_along = max(0.0, edge_len / 2 - _PILL_W / 2 - node_r)

        raw_theta = math.atan2(dye, dxe)
        if raw_theta > math.pi / 2:
            theta = raw_theta - math.pi
        elif raw_theta < -math.pi / 2:
            theta = raw_theta + math.pi
        else:
            theta = raw_theta
        abs_cos = abs(math.cos(theta))
        abs_sin = abs(math.sin(theta))
        aabb_w = _PILL_W * abs_cos + _PILL_H * abs_sin + 1.0
        aabb_h = _PILL_W * abs_sin + _PILL_H * abs_cos + 1.0

        lx, ly = _nudge_pill_placement(
            mid_x=mid_x,
            mid_y=mid_y,
            ux=ux,
            uy=uy,
            perp_x=perp_x,
            perp_y=perp_y,
            pill_w=_PILL_W,
            pill_h=_PILL_H,
            aabb_w=aabb_w,
            aabb_h=aabb_h,
            max_shift_along=max_shift_along,
            node_aabbs=node_aabbs,
            placed_pills=placed,
        )
        result = _LabelPlacement(x=lx, y=ly, width=aabb_w, height=aabb_h)
        for n in node_aabbs:
            assert not result.overlaps(n), (
                f"edge ({x1},{y1})->({x2},{y2}): pill at ({lx:.1f},{ly:.1f}) "
                f"overlaps node AABB at ({n.x},{n.y})"
            )
        placed.append(result)


@pytest.mark.unit
def test_origin_fallback_on_all_collisions() -> None:
    """When all along-shift, saturate, and perp-nudge probes collide, return origin.

    Plant blockers covering every cascade stage (stage 1 stepped probes,
    stage 1.5 saturate probes at ±max_shift_along, stage 2 perp probes).
    The helper must revert to (mid_x, mid_y).
    """
    mid_x, mid_y = 200.0, 150.0
    ux, uy = 1.0, 0.0        # horizontal edge
    perp_x, perp_y = 0.0, 1.0

    step_along = _PILL_W + 2   # = 19
    step_perp = _PILL_H + 2    # = 19

    max_shift_along = 200.0   # plenty of budget so stage 1 runs fully

    blockers: list[_LabelPlacement] = [
        # Origin itself
        _lp(mid_x, mid_y),
        # Along-shift probes ×4
        _lp(mid_x + ux * step_along,      mid_y + uy * step_along),
        _lp(mid_x - ux * step_along,      mid_y - uy * step_along),
        _lp(mid_x + ux * 2 * step_along,  mid_y + uy * 2 * step_along),
        _lp(mid_x - ux * 2 * step_along,  mid_y - uy * 2 * step_along),
        # Stage 1.5 saturate probes at ±budget (GEP-14).
        _lp(mid_x + ux * max_shift_along,  mid_y + uy * max_shift_along),
        _lp(mid_x - ux * max_shift_along,  mid_y - uy * max_shift_along),
        # Perp probes ×4
        _lp(mid_x + perp_x * step_perp,   mid_y + perp_y * step_perp),
        _lp(mid_x - perp_x * step_perp,   mid_y - perp_y * step_perp),
        _lp(mid_x + perp_x * 2*step_perp, mid_y + perp_y * 2*step_perp),
        _lp(mid_x - perp_x * 2*step_perp, mid_y - perp_y * 2*step_perp),
    ]

    lx, ly = _nudge_pill_placement(
        mid_x=mid_x,
        mid_y=mid_y,
        ux=ux,
        uy=uy,
        perp_x=perp_x,
        perp_y=perp_y,
        pill_w=_PILL_W,
        pill_h=_PILL_H,
        aabb_w=_AABB_W,
        aabb_h=_AABB_H,
        max_shift_along=max_shift_along,
        node_aabbs=[],
        placed_pills=blockers,
    )

    assert lx == mid_x, f"expected origin lx={mid_x}, got {lx}"
    assert ly == mid_y, f"expected origin ly={mid_y}, got {ly}"


# ---------------------------------------------------------------------------
# GEP v2.0 — saturate probe (stage 1.5 / rule U-11) — RED tests
#
# These 4 tests describe the NEW cascade stage that does NOT yet exist.
# They MUST fail against the current _nudge_pill_placement (no saturate).
# ---------------------------------------------------------------------------

# Shared geometry for the saturate tests: a clean horizontal edge so all
# directions reduce to simple arithmetic.
_S_MID_X: float = 500.0
_S_MID_Y: float = 300.0
_S_UX: float = 1.0   # unit vector along stroke (horizontal)
_S_UY: float = 0.0
_S_PERP_X: float = 0.0   # perpendicular (vertical)
_S_PERP_Y: float = 1.0
_S_PILL_W: float = 17.0
_S_PILL_H: float = 17.0
_S_AABB_W: float = 20.0  # rotated AABB for a horizontal edge = pill dimensions
_S_AABB_H: float = 20.0
_S_STEP_ALONG: float = _S_AABB_W + 2   # = 22.0  (matches nudge_step_along inside impl)
_S_STEP_PERP: float = _S_AABB_H + 2    # = 22.0


def _slp(x: float, y: float) -> _LabelPlacement:
    """Convenience: saturate-test placement using shared AABB dimensions."""
    return _LabelPlacement(x=x, y=y, width=_S_AABB_W, height=_S_AABB_H)


@pytest.mark.unit
def test_saturate_resolves_hair_thin_collision() -> None:
    """Stage 1.5 saturate probe at +budget rescues a hair-thin collision.

    Scenario:
      - Origin collides (blocker planted at origin).
      - Stage-1 stepped probes (±step_along, ±2·step_along) all collide.
      - All four perp probes collide (so stage 2 is exhausted too).
      - Saturate probe at +max_shift_along is clear.

    Expected (U-11): function returns (mid_x + max_shift_along, mid_y).
    Current code: no saturate stage → falls through to origin → FAIL.
    """
    max_shift_along = 75.0  # budget sits between 2·step (44) and ±3·step (66)

    # The exact positions stage 1 probes (all must be blocked).
    s1_offsets = [
        _S_STEP_ALONG,
        -_S_STEP_ALONG,
        2 * _S_STEP_ALONG,
        -2 * _S_STEP_ALONG,
    ]

    blockers: list[_LabelPlacement] = [
        # Origin itself
        _slp(_S_MID_X, _S_MID_Y),
    ]
    for off in s1_offsets:
        if abs(off) <= max_shift_along:
            blockers.append(_slp(_S_MID_X + _S_UX * off, _S_MID_Y + _S_UY * off))
    # Block all four perp probes so stage 2 is fully exhausted.
    for off in [_S_STEP_PERP, -_S_STEP_PERP, 2 * _S_STEP_PERP, -2 * _S_STEP_PERP]:
        blockers.append(_slp(_S_MID_X + _S_PERP_X * off, _S_MID_Y + _S_PERP_Y * off))

    # Saturate probe at +max_shift_along must be clear (no blocker there).
    sat_x = _S_MID_X + _S_UX * max_shift_along  # = 575.0
    sat_y = _S_MID_Y + _S_UY * max_shift_along  # = 300.0

    lx, ly = _nudge_pill_placement(
        mid_x=_S_MID_X,
        mid_y=_S_MID_Y,
        ux=_S_UX,
        uy=_S_UY,
        perp_x=_S_PERP_X,
        perp_y=_S_PERP_Y,
        pill_w=_S_PILL_W,
        pill_h=_S_PILL_H,
        aabb_w=_S_AABB_W,
        aabb_h=_S_AABB_H,
        max_shift_along=max_shift_along,
        node_aabbs=[],
        placed_pills=blockers,
    )

    assert abs(lx - sat_x) < 1e-9, (
        f"saturate probe: expected lx={sat_x}, got {lx} — "
        f"stage 1.5 saturate probe not implemented yet"
    )
    assert abs(ly - sat_y) < 1e-9, (
        f"saturate probe: expected ly={sat_y}, got {ly}"
    )


@pytest.mark.unit
def test_saturate_respects_budget_zero() -> None:
    """When max_shift_along == 0, saturate MUST be skipped (U-11 guard).

    Scenario:
      - max_shift_along = 0 (short edge — no along budget at all).
      - Origin collides.
      - Stage-1 is skipped (budget = 0).
      - A naive saturate implementation might probe at ±0, which would
        land on origin (still collides) and then either return origin or
        silently fall through.  The correct implementation MUST skip the
        saturate stage entirely when budget is zero and proceed directly
        to the perp fallback.
      - Perp step 1 (+step_perp) is clear.

    Red condition: we additionally block the perp step-1 probe but leave
    perp step-2 clear.  A buggy saturate impl that probes at +0 (=origin,
    collides) and then ALSO probes at -0 (same, collides) would exit the
    saturate loop having failed, then fall into the perp stage — which is
    correct.  To create an observable difference we assert the EXACT perp
    step-2 position and simultaneously assert that the result is NOT the
    along-stroke saturate position (mid_x + 0, mid_y + 0 = origin).

    This is partly a regression guard: it locks in the correct behavior
    for budget=0 so that when the saturate stage is added it cannot
    accidentally short-circuit the perp fallback.  The test PASSES on
    current code (which also falls through to perp) and MUST CONTINUE
    TO PASS after the saturate stage is added with a correct budget guard.
    Any implementation that probes at offset=0 and introduces a bug
    (e.g. infinite loop, incorrect short-circuit) will be caught here.

    Because the current code already satisfies the assertion this test is
    a GREEN guard (regression sentinel) rather than a strict RED test.
    The three other saturate tests (test_saturate_resolves_hair_thin_collision,
    test_saturate_preserves_on_stroke_invariant, test_saturate_deterministic_same_input)
    are the primary RED tests that drive the implementation.
    """
    max_shift_along = 0.0

    blockers: list[_LabelPlacement] = [
        _slp(_S_MID_X, _S_MID_Y),                                # origin collides
        _slp(_S_MID_X + _S_PERP_X * _S_STEP_PERP,               # perp step +1 blocked
             _S_MID_Y + _S_PERP_Y * _S_STEP_PERP),
    ]

    lx, ly = _nudge_pill_placement(
        mid_x=_S_MID_X,
        mid_y=_S_MID_Y,
        ux=_S_UX,
        uy=_S_UY,
        perp_x=_S_PERP_X,
        perp_y=_S_PERP_Y,
        pill_w=_S_PILL_W,
        pill_h=_S_PILL_H,
        aabb_w=_S_AABB_W,
        aabb_h=_S_AABB_H,
        max_shift_along=max_shift_along,
        node_aabbs=[],
        placed_pills=blockers,
    )

    # Must NOT return origin (blocker unresolved).
    assert (lx, ly) != (_S_MID_X, _S_MID_Y), (
        "budget=0: must not return origin when origin collides"
    )
    # No along-stroke displacement — saturate at 0 must be a no-op.
    assert abs(lx - _S_MID_X) < 1e-9, (
        f"budget=0: expected no along-stroke displacement, got lx={lx}"
    )
    # Perp step 1 is blocked; perp step -1 must be the result.
    expected_ly = _S_MID_Y - _S_STEP_PERP
    assert abs(ly - expected_ly) < 1e-9, (
        f"budget=0: expected ly={expected_ly} (perp step -1, since step +1 is blocked), "
        f"got {ly} — saturate must be skipped so perp fallback fires"
    )


@pytest.mark.unit
def test_saturate_preserves_on_stroke_invariant() -> None:
    """U-14: when saturate succeeds, returned center must lie on the stroke.

    Perpendicular distance from (lx, ly) to the stroke line (defined by
    mid-point and unit direction (ux, uy)) must be < 0.5 px.

    Current code: no saturate stage → falls through to either perp (off-
    stroke) or origin.  The test blocks origin AND perp so the function
    returns origin, which happens to be on-stroke — but that is the WRONG
    reason (it's the fallback, not a resolved placement).  To create a
    genuine RED condition the test asserts (a) the returned position is NOT
    origin AND (b) the perpendicular distance is < 0.5.  Condition (a) makes
    the test fail against current code because current code returns origin
    (stage-3 fallback) when both stage-1 and perp are exhausted.
    """
    max_shift_along = 80.0

    s1_offsets = [
        _S_STEP_ALONG,
        -_S_STEP_ALONG,
        2 * _S_STEP_ALONG,
        -2 * _S_STEP_ALONG,
    ]

    blockers: list[_LabelPlacement] = [
        _slp(_S_MID_X, _S_MID_Y),  # origin
    ]
    for off in s1_offsets:
        if abs(off) <= max_shift_along:
            blockers.append(_slp(_S_MID_X + _S_UX * off, _S_MID_Y + _S_UY * off))
    # Block all four perp probes.
    for off in [_S_STEP_PERP, -_S_STEP_PERP, 2 * _S_STEP_PERP, -2 * _S_STEP_PERP]:
        blockers.append(_slp(_S_MID_X + _S_PERP_X * off, _S_MID_Y + _S_PERP_Y * off))

    # Saturate probe at +max_shift_along is clear (no blocker near 580, 300).

    lx, ly = _nudge_pill_placement(
        mid_x=_S_MID_X,
        mid_y=_S_MID_Y,
        ux=_S_UX,
        uy=_S_UY,
        perp_x=_S_PERP_X,
        perp_y=_S_PERP_Y,
        pill_w=_S_PILL_W,
        pill_h=_S_PILL_H,
        aabb_w=_S_AABB_W,
        aabb_h=_S_AABB_H,
        max_shift_along=max_shift_along,
        node_aabbs=[],
        placed_pills=blockers,
    )

    # (a) Must NOT be origin (stage-3 fallback) — saturate must have resolved it.
    assert (lx, ly) != (_S_MID_X, _S_MID_Y), (
        "U-14: saturate probe should have resolved the collision — "
        "not falling back to origin; stage 1.5 not implemented yet"
    )

    # (b) U-14: returned center must be on the stroke line.
    # Perpendicular distance = |dot((lx-mid_x, ly-mid_y), (perp_x, perp_y))|
    delta_x = lx - _S_MID_X
    delta_y = ly - _S_MID_Y
    perp_dist = abs(delta_x * _S_PERP_X + delta_y * _S_PERP_Y)
    assert perp_dist < 0.5, (
        f"U-14 on-stroke invariant violated: perp_dist={perp_dist:.4f} >= 0.5"
    )


@pytest.mark.unit
def test_saturate_deterministic_same_input() -> None:
    """U-06: two calls with identical inputs produce byte-identical output.

    Saturate must not introduce any non-determinism (no random probing,
    no mutable shared state).  This test exercises the full cascade including
    the saturate probe path (origin + stage-1 blocked, saturate fires).

    Current code: returns origin for both calls (no saturate) — both calls
    return the same origin tuple, so determinism holds trivially.  The test
    additionally asserts the result is NOT origin (saturate must have resolved
    it), which makes the test RED against current code.
    """
    max_shift_along = 75.0

    s1_offsets = [
        _S_STEP_ALONG,
        -_S_STEP_ALONG,
        2 * _S_STEP_ALONG,
        -2 * _S_STEP_ALONG,
    ]

    blockers: list[_LabelPlacement] = [
        _slp(_S_MID_X, _S_MID_Y),
    ]
    for off in s1_offsets:
        if abs(off) <= max_shift_along:
            blockers.append(_slp(_S_MID_X + _S_UX * off, _S_MID_Y + _S_UY * off))
    for off in [_S_STEP_PERP, -_S_STEP_PERP, 2 * _S_STEP_PERP, -2 * _S_STEP_PERP]:
        blockers.append(_slp(_S_MID_X + _S_PERP_X * off, _S_MID_Y + _S_PERP_Y * off))

    kwargs: dict[str, object] = dict(
        mid_x=_S_MID_X,
        mid_y=_S_MID_Y,
        ux=_S_UX,
        uy=_S_UY,
        perp_x=_S_PERP_X,
        perp_y=_S_PERP_Y,
        pill_w=_S_PILL_W,
        pill_h=_S_PILL_H,
        aabb_w=_S_AABB_W,
        aabb_h=_S_AABB_H,
        max_shift_along=max_shift_along,
        node_aabbs=[],
        placed_pills=blockers,
    )

    result_a = _nudge_pill_placement(**kwargs)  # type: ignore[arg-type]
    result_b = _nudge_pill_placement(**kwargs)  # type: ignore[arg-type]

    assert result_a == result_b, (
        f"U-06 determinism violated: first={result_a}, second={result_b}"
    )

    # Saturate must have resolved the collision — not origin fallback.
    expected = (_S_MID_X + _S_UX * max_shift_along, _S_MID_Y + _S_UY * max_shift_along)
    assert result_a == expected, (
        f"U-06 + U-11: expected saturate result {expected}, got {result_a} — "
        f"stage 1.5 saturate probe not implemented yet"
    )
