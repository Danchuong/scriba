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
from scriba.animation.primitives.graph import Graph


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
