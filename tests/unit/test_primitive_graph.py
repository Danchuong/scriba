"""Unit tests for scriba.animation.primitives.graph."""

from __future__ import annotations

import pytest

from scriba.animation.primitives.graph import Graph, fruchterman_reingold
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------
# Layout tests
# ---------------------------------------------------------------


class TestFruchtermanReingold:
    def test_empty_nodes(self) -> None:
        result = fruchterman_reingold([], [])
        assert result == {}

    def test_single_node_centered(self) -> None:
        result = fruchterman_reingold(["A"], [])
        assert result == {"A": (200, 150)}

    def test_deterministic_same_seed(self) -> None:
        nodes = ["A", "B", "C"]
        edges = [("A", "B"), ("B", "C")]
        pos1 = fruchterman_reingold(nodes, edges, seed=42)
        pos2 = fruchterman_reingold(nodes, edges, seed=42)
        assert pos1 == pos2

    def test_different_seed_different_positions(self) -> None:
        nodes = ["A", "B", "C"]
        edges = [("A", "B"), ("B", "C")]
        pos1 = fruchterman_reingold(nodes, edges, seed=42)
        pos2 = fruchterman_reingold(nodes, edges, seed=99)
        assert pos1 != pos2

    def test_positions_are_integers(self) -> None:
        nodes = ["A", "B", "C", "D"]
        edges = [("A", "B"), ("B", "C"), ("C", "D")]
        positions = fruchterman_reingold(nodes, edges)
        for x, y in positions.values():
            assert isinstance(x, int)
            assert isinstance(y, int)

    def test_positions_within_bounds(self) -> None:
        nodes = list(range(10))
        edges = [(i, i + 1) for i in range(9)]
        positions = fruchterman_reingold(nodes, edges, width=400, height=300)
        for x, y in positions.values():
            assert 20 <= x <= 380
            assert 20 <= y <= 280


# ---------------------------------------------------------------
# Graph construction tests
# ---------------------------------------------------------------


class TestGraphConstruction:
    def test_basic_construction(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B", "C"],
            "edges": [("A", "B"), ("A", "C")],
        })
        assert g.name == "G"
        assert g.nodes == ["A", "B", "C"]
        # Wave 6.2: edges are stored as 3-tuples (u, v, weight).
        # Unweighted edges have weight=None.
        assert g.edges == [("A", "B", None), ("A", "C", None)]
        assert g.directed is False
        assert g.layout == "force"
        assert g.layout_seed == 42

    def test_directed_graph(self) -> None:
        g = Graph("DG", {
            "nodes": [1, 2],
            "edges": [(1, 2)],
            "directed": True,
        })
        assert g.directed is True

    def test_layout_computed_on_init(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
        })
        assert "A" in g.positions
        assert "B" in g.positions
        assert len(g.positions["A"]) == 2
        assert len(g.positions["B"]) == 2

    def test_label_parameter(self) -> None:
        g = Graph("G", {
            "nodes": ["A"],
            "edges": [],
            "label": "My Graph",
        })
        assert g.label == "My Graph"

    def test_empty_nodes_list_raises(self) -> None:
        """Graph with empty nodes must raise E1470 (not silently render)."""
        from scriba.core.errors import ValidationError

        with pytest.raises(ValidationError, match="E1470"):
            Graph("G", {"nodes": [], "edges": []})

    def test_missing_nodes_raises(self) -> None:
        from scriba.core.errors import ValidationError

        with pytest.raises(ValidationError, match="E1470"):
            Graph("G", {})


# ---------------------------------------------------------------
# Selector tests
# ---------------------------------------------------------------


class TestGraphSelectors:
    @pytest.fixture()
    def graph(self) -> Graph:
        return Graph("G", {
            "nodes": ["A", "B", "C"],
            "edges": [("A", "B"), ("B", "C")],
        })

    def test_addressable_parts_contains_nodes(self, graph: Graph) -> None:
        parts = graph.addressable_parts()
        assert "node[A]" in parts
        assert "node[B]" in parts
        assert "node[C]" in parts

    def test_addressable_parts_contains_edges(self, graph: Graph) -> None:
        parts = graph.addressable_parts()
        assert "edge[(A,B)]" in parts
        assert "edge[(B,C)]" in parts

    def test_validate_selector_valid_node(self, graph: Graph) -> None:
        assert graph.validate_selector("node[A]") is True

    def test_validate_selector_valid_edge(self, graph: Graph) -> None:
        assert graph.validate_selector("edge[(A,B)]") is True

    def test_validate_selector_all(self, graph: Graph) -> None:
        assert graph.validate_selector("all") is True

    def test_validate_selector_invalid_node(self, graph: Graph) -> None:
        assert graph.validate_selector("node[Z]") is False

    def test_validate_selector_invalid_edge(self, graph: Graph) -> None:
        assert graph.validate_selector("edge[(X,Y)]") is False


# ---------------------------------------------------------------
# Bounding box test
# ---------------------------------------------------------------


class TestGraphBoundingBox:
    def test_bounding_box_default_dimensions(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
        })
        bb = g.bounding_box()
        assert bb.x == 0
        assert bb.y == 0
        assert bb.width == 440   # 400 + 2 * node_radius(20)
        assert bb.height == 340  # 300 + 2 * node_radius(20)


# ---------------------------------------------------------------
# SVG emission tests
# ---------------------------------------------------------------


class TestGraphEmitSvg:
    def test_single_node_graph_svg(self) -> None:
        """A minimal graph with a single node still emits the wrapper."""
        g = Graph("G", {"nodes": ["A"], "edges": []})
        svg = g.emit_svg()
        assert 'data-primitive="graph"' in svg
        assert 'data-shape="G"' in svg

    def test_svg_structure_edges_before_nodes(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
        })
        svg = g.emit_svg()
        edges_pos = svg.find("scriba-graph-edges")
        nodes_pos = svg.find("scriba-graph-nodes")
        assert edges_pos < nodes_pos

    def test_svg_data_target_node(self) -> None:
        g = Graph("G", {
            "nodes": ["A"],
            "edges": [],
        })
        svg = g.emit_svg()
        assert 'data-target="G.node[A]"' in svg

    def test_svg_data_target_edge(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
        })
        svg = g.emit_svg()
        assert 'data-target="G.edge[(A,B)]"' in svg

    def test_undirected_no_arrowheads(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
            "directed": False,
        })
        svg = g.emit_svg()
        assert "scriba-arrow" not in svg
        assert "marker-end" not in svg

    def test_directed_has_arrowheads(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
            "directed": True,
        })
        svg = g.emit_svg()
        assert "scriba-arrow-fwd" in svg
        assert 'marker-end="url(#scriba-arrow-fwd)"' in svg

    def test_node_circle_radius(self) -> None:
        g = Graph("G", {
            "nodes": ["A"],
            "edges": [],
        })
        svg = g.emit_svg()
        assert 'r="20"' in svg

    def test_edge_stroke_width(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
        })
        svg = g.emit_svg()
        # Idle edges have stroke-width="1.5", active states have "2"
        assert 'stroke-width="1.5"' in svg

    def test_node_label_rendered(self) -> None:
        g = Graph("G", {
            "nodes": ["X"],
            "edges": [],
        })
        svg = g.emit_svg()
        assert ">X</text>" in svg

    def test_label_caption_rendered(self) -> None:
        g = Graph("G", {
            "nodes": ["A"],
            "edges": [],
            "label": "BFS Demo",
        })
        svg = g.emit_svg()
        assert "BFS Demo" in svg
        assert "scriba-primitive-label" in svg


# ---------------------------------------------------------------
# State application tests
# ---------------------------------------------------------------


class TestGraphStateApplication:
    def test_node_recolor(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [],
        })
        g.set_state("node[A]", "current")
        svg = g.emit_svg()
        assert 'class="scriba-state-current"' in svg

    def test_edge_highlight(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
        })
        g.set_state("edge[(A,B)]", "highlight")
        svg = g.emit_svg()
        assert 'class="scriba-state-highlight"' in svg

    def test_default_state_is_idle(self) -> None:
        g = Graph("G", {
            "nodes": ["A"],
            "edges": [],
        })
        assert g.get_state("node[A]") == "idle"
        svg = g.emit_svg()
        assert 'class="scriba-state-idle"' in svg


# ---------------------------------------------------------------
# Seed validation (E1505)
# ---------------------------------------------------------------


class TestGraphSeedValidation:
    def test_valid_positive_seed(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
            "layout_seed": 123,
        })
        assert g.layout_seed == 123

    def test_valid_zero_seed(self) -> None:
        g = Graph("G", {
            "nodes": ["A"],
            "edges": [],
            "layout_seed": 0,
        })
        assert g.layout_seed == 0

    def test_negative_seed_raises_e1505(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            Graph("G", {
                "nodes": ["A", "B"],
                "edges": [("A", "B")],
                "layout_seed": -1,
            })
        assert "E1505" in str(excinfo.value)
        assert "-1" in str(excinfo.value)

    def test_string_seed_raises_e1505(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            Graph("G", {
                "nodes": ["A"],
                "edges": [],
                "layout_seed": "abc",
            })
        assert "E1505" in str(excinfo.value)

    def test_float_seed_raises_e1505(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            Graph("G", {
                "nodes": ["A"],
                "edges": [],
                "layout_seed": 3.14,
            })
        assert "E1505" in str(excinfo.value)

    def test_bool_seed_rejected(self) -> None:
        """``True`` is technically an ``int`` subclass but should be rejected."""
        with pytest.raises(ValidationError) as excinfo:
            Graph("G", {
                "nodes": ["A"],
                "edges": [],
                "layout_seed": True,
            })
        assert "E1505" in str(excinfo.value)

    def test_seed_alias_accepted(self) -> None:
        """Bare ``seed`` key is accepted as an alias for ``layout_seed``."""
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
            "seed": 7,
        })
        assert g.layout_seed == 7

    def test_seed_alias_also_validated(self) -> None:
        """Invalid ``seed`` alias is rejected with E1505 too."""
        with pytest.raises(ValidationError) as excinfo:
            Graph("G", {
                "nodes": ["A"],
                "edges": [],
                "seed": -5,
            })
        assert "E1505" in str(excinfo.value)

    def test_layout_seed_wins_over_seed_alias(self) -> None:
        """When both keys present, ``layout_seed`` is canonical and wins."""
        g = Graph("G", {
            "nodes": ["A"],
            "edges": [],
            "layout_seed": 111,
            "seed": 222,
        })
        assert g.layout_seed == 111

    def test_default_seed_when_omitted(self) -> None:
        g = Graph("G", {"nodes": ["A"], "edges": []})
        # _DEFAULT_SEED is 42 per the module.
        assert g.layout_seed == 42


# ---------------------------------------------------------------
# Layout dispatch (layout="auto", stable-directed warning)
# ---------------------------------------------------------------


class TestLayoutAutoDispatch:
    """``layout="auto"`` routes directed DAGs to Sugiyama, else FR."""

    def test_directed_dag_uses_hierarchical(self) -> None:
        g = Graph("G", {
            "nodes": ["a", "b", "c", "d"],
            "edges": [("a", "b"), ("b", "c"), ("c", "d")],
            "directed": True,
            "layout": "auto",
        })
        # Auto resolves to "hierarchical" when the graph is a DAG.
        assert g.layout == "hierarchical"
        # Chain → strictly increasing y in TB orientation.
        ys = [g.positions[n][1] for n in ["a", "b", "c", "d"]]
        assert ys == sorted(ys)

    def test_directed_cyclic_falls_back_to_fr(self) -> None:
        g = Graph("G", {
            "nodes": ["a", "b", "c"],
            "edges": [("a", "b"), ("b", "c"), ("c", "a")],
            "directed": True,
            "layout": "auto",
        })
        # Cycle detected → auto stays "auto" (not rewritten to hierarchical),
        # positions produced by FR fallback.
        assert g.layout == "auto"
        assert set(g.positions.keys()) == {"a", "b", "c"}

    def test_undirected_falls_back_to_fr(self) -> None:
        g = Graph("G", {
            "nodes": ["a", "b", "c"],
            "edges": [("a", "b"), ("b", "c")],
            "directed": False,
            "layout": "auto",
        })
        # Undirected graphs skip the DAG probe → FR.
        assert g.layout == "auto"
        assert set(g.positions.keys()) == {"a", "b", "c"}

    def test_directed_dag_diamond(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B", "C", "D"],
            "edges": [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")],
            "directed": True,
            "layout": "auto",
        })
        assert g.layout == "hierarchical"
        # A top, D bottom, B & C same layer.
        assert g.positions["A"][1] < g.positions["B"][1]
        assert g.positions["B"][1] == g.positions["C"][1]
        assert g.positions["C"][1] < g.positions["D"][1]


class TestStableDirectedWarning:
    """Stable-SA + directed graph emits a UserWarning."""

    def test_warns_when_stable_and_directed(self) -> None:
        with pytest.warns(UserWarning, match="does not respect edge direction"):
            Graph("G", {
                "nodes": ["a", "b"],
                "edges": [("a", "b")],
                "directed": True,
                "layout": "stable",
            })

    def test_no_warning_when_stable_undirected(self) -> None:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # any warning becomes an error
            Graph("G", {
                "nodes": ["a", "b"],
                "edges": [("a", "b")],
                "directed": False,
                "layout": "stable",
            })

    def test_no_warning_when_hierarchical_directed(self) -> None:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Graph("G", {
                "nodes": ["a", "b"],
                "edges": [("a", "b")],
                "directed": True,
                "layout": "hierarchical",
            })


class TestHierarchicalOrientation:
    """``orientation`` param plumbs TB/LR into hierarchical layout."""

    def test_default_is_tb(self) -> None:
        # Chain S→A→T: TB means ys strictly increasing, xs clustered.
        g = Graph("G", {
            "nodes": ["S", "A", "T"],
            "edges": [("S", "A"), ("A", "T")],
            "directed": True,
            "layout": "hierarchical",
        })
        assert g.orientation == "TB"
        ys = [g.positions[n][1] for n in ("S", "A", "T")]
        assert ys[0] < ys[1] < ys[2]

    def test_lr_orients_left_to_right(self) -> None:
        # Same chain LR: xs strictly increasing, ys clustered.
        g = Graph("G", {
            "nodes": ["S", "A", "T"],
            "edges": [("S", "A"), ("A", "T")],
            "directed": True,
            "layout": "hierarchical",
            "orientation": "LR",
        })
        xs = [g.positions[n][0] for n in ("S", "A", "T")]
        assert xs[0] < xs[1] < xs[2]

    def test_lr_mcmf_topology(self) -> None:
        # MCMF-shaped DAG: S leftmost, T rightmost.
        g = Graph("G", {
            "nodes": ["S", "A", "B", "C", "D", "T"],
            "edges": [
                ("S", "A"), ("S", "B"),
                ("A", "C"), ("A", "D"),
                ("B", "C"), ("B", "D"),
                ("C", "T"), ("D", "T"),
            ],
            "directed": True,
            "layout": "hierarchical",
            "orientation": "LR",
        })
        xs = {n: g.positions[n][0] for n in g.nodes}
        # S leftmost of all, T rightmost of all.
        assert xs["S"] == min(xs.values())
        assert xs["T"] == max(xs.values())
        # Middle layers strictly between S and T.
        for mid in ("A", "B", "C", "D"):
            assert xs["S"] < xs[mid] < xs["T"]

    def test_invalid_orientation_falls_back_to_fr(self) -> None:
        # compute_hierarchical_layout returns None for unknown orientation
        # → caller falls through to Fruchterman-Reingold.
        g = Graph("G", {
            "nodes": ["a", "b"],
            "edges": [("a", "b")],
            "directed": True,
            "layout": "hierarchical",
            "orientation": "DIAGONAL",
        })
        # Positions still computed (FR fallback), just not layered.
        assert set(g.positions.keys()) == {"a", "b"}


class TestPillPlacementFrameStable:
    """Edge-pill geometry must NOT depend on per-frame edge state.

    Regression for the mcmf.html step 8→9 pill swap: prior versions sorted
    edges by state priority, so a current→good transition in one edge
    could reorder the placement cascade and shift pills on unrelated
    edges. Placement should now be purely a function of topology.
    """

    def _extract_pill_rects(self, svg: str) -> list[tuple[str, float, float]]:
        """Return (edge_target, pill_x, pill_y) tuples from an emitted SVG.

        Each edge <g data-target="G.edge_u_v"> with a weight pill contains
        a `<rect x=… y=…>` for the pill. Parse them in document order.
        """
        import re as _re
        out: list[tuple[str, float, float]] = []
        # Match each edge group, then the first rect (the pill rect) inside it.
        for m in _re.finditer(
            r'<g data-target="(?P<tgt>G\.edge[^"]+)"[^>]*>'
            r'[^<]*<line[^/]*/>'  # the stroke line
            r'(?P<rest>.*?)</g>',
            svg,
            flags=_re.DOTALL,
        ):
            tgt = m.group("tgt")
            rest = m.group("rest")
            rect_m = _re.search(
                r'<rect\s+x="(?P<x>[-\d.]+)"\s+y="(?P<y>[-\d.]+)"',
                rest,
            )
            if rect_m:
                out.append((tgt, float(rect_m.group("x")), float(rect_m.group("y"))))
        return out

    def test_mcmf_pill_positions_frame_stable_across_state_changes(self) -> None:
        """MCMF topology: pill positions must match frame-to-frame despite state churn."""
        common = {
            "nodes": ["S", "A", "B", "C", "D", "T"],
            "edges": [
                ("S", "A", 4), ("S", "B", 3),
                ("A", "C", 2), ("A", "D", 3),
                ("B", "C", 5), ("B", "D", 1),
                ("C", "T", 4), ("D", "T", 3),
            ],
            "directed": True,
            "show_weights": True,
            "layout": "hierarchical",
            "orientation": "LR",
        }

        g1 = Graph("G", common)
        svg1 = g1.emit_svg()
        rects1 = {t: (x, y) for t, x, y in self._extract_pill_rects(svg1)}

        # Frame "step 8" state: mix of good/dim (all fall to prio-99 pre-fix).
        g2 = Graph("G", common)
        for edge, state in [
            (("S", "A"), "good"), (("A", "D"), "good"), (("D", "T"), "good"),
            (("S", "B"), "dim"), (("B", "C"), "dim"), (("A", "C"), "dim"),
            (("C", "T"), "dim"),
        ]:
            g2.set_state(f"edge[({edge[0]},{edge[1]})]", state)
        rects2 = {t: (x, y) for t, x, y in self._extract_pill_rects(g2.emit_svg())}

        # Frame "step 9" state: path edges done, rest idle (prio-3 pre-fix).
        g3 = Graph("G", common)
        for edge, state in [
            (("S", "A"), "done"), (("A", "D"), "done"), (("D", "T"), "done"),
            (("S", "B"), "idle"), (("B", "C"), "idle"), (("A", "C"), "idle"),
            (("C", "T"), "dim"),
        ]:
            g3.set_state(f"edge[({edge[0]},{edge[1]})]", state)
        rects3 = {t: (x, y) for t, x, y in self._extract_pill_rects(g3.emit_svg())}

        # All three frames must produce identical pill positions per edge.
        assert rects1.keys() == rects2.keys() == rects3.keys()
        for tgt in rects1:
            assert rects1[tgt] == rects2[tgt] == rects3[tgt], (
                f"pill for {tgt} moved across frames: "
                f"{rects1[tgt]} vs {rects2[tgt]} vs {rects3[tgt]}"
            )
