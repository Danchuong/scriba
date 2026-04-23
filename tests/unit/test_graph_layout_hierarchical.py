"""Tests for hierarchical (Sugiyama-style) graph layout."""

from __future__ import annotations

import pytest

from scriba.animation.primitives.graph_layout_hierarchical import (
    _assign_coords,
    _assign_layers,
    _break_cycles,
    _minimize_crossings,
    compute_hierarchical_layout,
)
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Layer assignment
# ---------------------------------------------------------------------------


class TestAssignLayers:
    def test_linear_chain(self) -> None:
        nodes = ["a", "b", "c", "d"]
        edges = [("a", "b"), ("b", "c"), ("c", "d")]
        layers = _assign_layers(nodes, edges)
        assert layers == [["a"], ["b"], ["c"], ["d"]]

    def test_diamond(self) -> None:
        nodes = ["A", "B", "C", "D"]
        edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
        layers = _assign_layers(nodes, edges)
        assert layers[0] == ["A"]
        assert set(layers[1]) == {"B", "C"}
        assert layers[2] == ["D"]

    def test_maxflow_topology(self) -> None:
        """S→{A,B}, A→{B,C}, B→D, C→{D,T}, D→T."""
        nodes = ["S", "A", "B", "C", "D", "T"]
        edges = [
            ("S", "A"), ("S", "B"),
            ("A", "B"), ("A", "C"),
            ("B", "D"), ("C", "D"),
            ("C", "T"), ("D", "T"),
        ]
        layers = _assign_layers(nodes, edges)
        # S is only source
        assert layers[0] == ["S"]
        # T sinks last
        assert layers[-1] == ["T"]
        # A precedes B (A→B)
        layer_of = {n: i for i, layer in enumerate(layers) for n in layer}
        assert layer_of["A"] < layer_of["B"]
        assert layer_of["B"] < layer_of["D"]
        assert layer_of["D"] < layer_of["T"]

    def test_disconnected_components(self) -> None:
        nodes = ["a", "b", "c", "x", "y"]
        edges = [("a", "b"), ("b", "c"), ("x", "y")]
        layers = _assign_layers(nodes, edges)
        # Sources (a, x) at layer 0, both reachable independently
        assert "a" in layers[0] and "x" in layers[0]

    def test_singleton(self) -> None:
        layers = _assign_layers(["only"], [])
        assert layers == [["only"]]

    def test_empty(self) -> None:
        layers = _assign_layers([], [])
        assert layers == []


# ---------------------------------------------------------------------------
# Cycle breaking
# ---------------------------------------------------------------------------


class TestBreakCycles:
    def test_no_cycle_is_noop(self) -> None:
        nodes = ["a", "b", "c"]
        edges = [("a", "b"), ("b", "c")]
        dag, rev = _break_cycles(nodes, edges)
        assert set(dag) == {("a", "b"), ("b", "c")}
        assert rev == set()

    def test_simple_cycle_broken(self) -> None:
        nodes = ["a", "b", "c"]
        edges = [("a", "b"), ("b", "c"), ("c", "a")]
        dag, rev = _break_cycles(nodes, edges)
        assert len(rev) == 1  # exactly one back edge reversed
        # After reversal the graph is acyclic — _assign_layers should terminate
        layers = _assign_layers(nodes, dag)
        assert sum(len(l) for l in layers) == 3

    def test_self_loop_dropped(self) -> None:
        dag, rev = _break_cycles(["a"], [("a", "a")])
        assert dag == []
        assert rev == set()

    def test_two_isolated_cycles(self) -> None:
        nodes = ["1", "2", "3", "4", "5", "6"]
        edges = [
            ("1", "2"), ("2", "3"), ("3", "1"),
            ("4", "5"), ("5", "6"), ("6", "4"),
        ]
        dag, rev = _break_cycles(nodes, edges)
        assert len(rev) == 2  # one back edge per cycle
        layers = _assign_layers(nodes, dag)
        assert sum(len(l) for l in layers) == 6


# ---------------------------------------------------------------------------
# Crossing minimization
# ---------------------------------------------------------------------------


class TestMinimizeCrossings:
    def test_already_sorted_stays_stable(self) -> None:
        import random as _rnd
        layers = [["A"], ["B", "C"], ["D"]]
        edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
        out = _minimize_crossings(layers, edges, _rnd.Random(42))
        assert out[0] == ["A"]
        assert set(out[1]) == {"B", "C"}
        assert out[2] == ["D"]

    def test_determinism(self) -> None:
        import random as _rnd
        layers = [["A"], ["B", "C", "D"], ["E"]]
        edges = [("A", "B"), ("A", "C"), ("A", "D"), ("B", "E"), ("D", "E")]
        r1 = _minimize_crossings(layers, edges, _rnd.Random(7))
        r2 = _minimize_crossings(
            [list(layer) for layer in layers], edges, _rnd.Random(7)
        )
        assert r1 == r2


# ---------------------------------------------------------------------------
# Coordinate assignment
# ---------------------------------------------------------------------------


class TestAssignCoords:
    def test_top_down_y_monotone(self) -> None:
        layers = [["A"], ["B", "C"], ["D"]]
        pos = _assign_coords(
            layers, width=400, height=300, node_radius=16, orientation="TB"
        )
        assert pos["A"][1] < pos["B"][1] == pos["C"][1] < pos["D"][1]

    def test_left_right_x_monotone(self) -> None:
        layers = [["A"], ["B", "C"], ["D"]]
        pos = _assign_coords(
            layers, width=400, height=300, node_radius=16, orientation="LR"
        )
        assert pos["A"][0] < pos["B"][0] == pos["C"][0] < pos["D"][0]

    def test_centered_single_node_per_layer(self) -> None:
        layers = [["A"], ["B"], ["C"]]
        pos = _assign_coords(
            layers, width=400, height=300, node_radius=16, orientation="TB"
        )
        for node in ("A", "B", "C"):
            assert pos[node][0] == pytest.approx(200.0)  # centered x

    def test_within_bounds(self) -> None:
        layers = [["A", "B"], ["C", "D", "E"], ["F"]]
        pos = _assign_coords(
            layers, width=400, height=300, node_radius=16, orientation="TB"
        )
        pad = 16 + 10  # node_radius + _PADDING // 2
        for x, y in pos.values():
            assert pad <= x <= 400 - pad + 0.001
            assert pad <= y <= 300 - pad + 0.001


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


class TestComputeHierarchicalLayout:
    def test_maxflow_returns_all_nodes(self) -> None:
        nodes = ["S", "A", "B", "C", "D", "T"]
        edges = [[
            ("S", "A"), ("S", "B"),
            ("A", "B"), ("A", "C"),
            ("B", "D"), ("C", "D"),
            ("C", "T"), ("D", "T"),
        ]]
        pos = compute_hierarchical_layout(nodes, edges)
        assert pos is not None
        assert set(pos.keys()) == set(nodes)
        # S at top (smallest y), T at bottom
        ys = {n: pos[n][1] for n in nodes}
        assert ys["S"] == min(ys.values())
        assert ys["T"] == max(ys.values())

    def test_diamond_returns_all_nodes(self) -> None:
        nodes = ["A", "B", "C", "D"]
        edges = [[("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]]
        pos = compute_hierarchical_layout(nodes, edges)
        assert pos is not None
        assert pos["A"][1] < pos["B"][1] == pos["C"][1] < pos["D"][1]

    def test_linear_chain(self) -> None:
        nodes = ["a", "b", "c", "d"]
        edges = [[("a", "b"), ("b", "c"), ("c", "d")]]
        pos = compute_hierarchical_layout(nodes, edges)
        assert pos is not None
        ys = [pos[n][1] for n in nodes]
        assert ys == sorted(ys)

    def test_cycles_do_not_hang(self) -> None:
        nodes = ["1", "2", "3"]
        edges = [[("1", "2"), ("2", "3"), ("3", "1")]]
        pos = compute_hierarchical_layout(nodes, edges)
        assert pos is not None
        assert set(pos.keys()) == {"1", "2", "3"}

    def test_empty_nodes_returns_empty_dict(self) -> None:
        pos = compute_hierarchical_layout([], [])
        assert pos == {}

    def test_singleton(self) -> None:
        pos = compute_hierarchical_layout(["only"], [[]])
        assert pos is not None
        assert "only" in pos

    def test_invalid_orientation_returns_none(self) -> None:
        pos = compute_hierarchical_layout(
            ["a"], [[]], orientation="diagonal"
        )
        assert pos is None

    def test_negative_seed_raises_e1505(self) -> None:
        with pytest.raises(ValidationError, match="E1505"):
            compute_hierarchical_layout(["a"], [[]], seed=-1)

    def test_bool_seed_raises_e1505(self) -> None:
        with pytest.raises(ValidationError, match="E1505"):
            compute_hierarchical_layout(["a"], [[]], seed=True)  # type: ignore[arg-type]

    def test_determinism_same_seed(self) -> None:
        nodes = ["A", "B", "C", "D", "E"]
        edges = [[("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E")]]
        p1 = compute_hierarchical_layout(nodes, edges, seed=17)
        p2 = compute_hierarchical_layout(nodes, edges, seed=17)
        assert p1 == p2

    def test_within_viewport_bounds(self) -> None:
        """Small flat graphs (layer_gap ≥ _MIN_LAYER_GAP) stay inside."""
        nodes = ["a", "b", "c"]
        edges = [[("a", "b"), ("b", "c")]]
        pos = compute_hierarchical_layout(
            nodes, edges, width=400, height=400, node_radius=16
        )
        assert pos is not None
        for x, y in pos.values():
            assert 0 <= x <= 400
            assert 0 <= y <= 400

    def test_overflows_when_min_gap_required(self) -> None:
        """Many-layer DAGs overflow the passed height — caller must
        expand viewport to fit the returned bounding box (see
        graph.py's hierarchical dispatch branch)."""
        nodes = ["S", "A", "B", "C", "D", "T"]
        edges = [[
            ("S", "A"), ("S", "B"),
            ("A", "C"), ("B", "D"),
            ("C", "T"), ("D", "T"),
        ]]
        pos = compute_hierarchical_layout(
            nodes, edges, width=400, height=300, node_radius=16
        )
        assert pos is not None
        # 4 layers × min_gap=100 = 300, plus 2×pad(24) = 348 primary-axis
        ys = [y for _, y in pos.values()]
        assert max(ys) - min(ys) >= 100 * (4 - 1) - 1  # 3 layer gaps

    def test_frame_union(self) -> None:
        """Edges from multiple frames are unioned for layering."""
        nodes = ["a", "b", "c"]
        # Frame 0 has a→b; frame 1 adds b→c. Final layering honors both.
        edges = [[("a", "b")], [("b", "c")]]
        pos = compute_hierarchical_layout(nodes, edges)
        assert pos is not None
        assert pos["a"][1] < pos["b"][1] < pos["c"][1]

    def test_lr_orientation(self) -> None:
        nodes = ["a", "b", "c"]
        edges = [[("a", "b"), ("b", "c")]]
        pos = compute_hierarchical_layout(nodes, edges, orientation="LR")
        assert pos is not None
        # Layers spread along x now
        assert pos["a"][0] < pos["b"][0] < pos["c"][0]
