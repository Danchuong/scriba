"""Unit tests for scriba.animation.primitives.tree."""

from __future__ import annotations

import pytest

from scriba.animation.primitives.tree import Tree, _build_segtree as build_segtree, _reingold_tilford as reingold_tilford


# ---------------------------------------------------------------
# Layout tests
# ---------------------------------------------------------------


class TestReingoldTilford:
    def test_single_node_centered(self) -> None:
        positions = reingold_tilford(1, {1: []})
        assert len(positions) == 1
        assert 1 in positions

    def test_positions_are_integers(self) -> None:
        children = {1: [2, 3], 2: [4, 5], 3: [], 4: [], 5: []}
        positions = reingold_tilford(1, children)
        for x, y in positions.values():
            assert isinstance(x, int)
            assert isinstance(y, int)

    def test_deterministic(self) -> None:
        children = {1: [2, 3], 2: [], 3: []}
        pos1 = reingold_tilford(1, children)
        pos2 = reingold_tilford(1, children)
        assert pos1 == pos2

    def test_no_node_overlap(self) -> None:
        """Nodes at the same depth should not overlap."""
        children = {
            1: [2, 3],
            2: [4, 5],
            3: [6, 7],
            4: [],
            5: [],
            6: [],
            7: [],
        }
        positions = reingold_tilford(1, children)
        # Group by y-coordinate (depth level)
        by_y: dict[int, list[int]] = {}
        for node, (x, y) in positions.items():
            by_y.setdefault(y, []).append(x)
        # At each level, no two nodes should share the same x
        for y, xs in by_y.items():
            assert len(xs) == len(set(xs)), f"Overlapping nodes at y={y}"

    def test_parent_centered_over_children(self) -> None:
        children = {1: [2, 3], 2: [], 3: []}
        positions = reingold_tilford(1, children, width=400, height=300)
        px = positions[1][0]
        left_x = positions[2][0]
        right_x = positions[3][0]
        # Parent should be centered between children (with integer rounding)
        expected_center = (left_x + right_x) / 2
        assert abs(px - expected_center) <= 1


# ---------------------------------------------------------------
# build_segtree tests
# ---------------------------------------------------------------


class TestBuildSegtree:
    def test_data_4_elements(self) -> None:
        root, nodes, edges, sums = build_segtree([1, 2, 3, 4])
        assert root == "[0,3]"
        assert "[0,3]" in nodes
        assert "[0,1]" in nodes
        assert "[2,3]" in nodes
        assert "[0,0]" in nodes
        assert "[1,1]" in nodes
        assert "[2,2]" in nodes
        assert "[3,3]" in nodes
        assert len(nodes) == 7

    def test_edges_correct(self) -> None:
        root, nodes, edges, sums = build_segtree([1, 2, 3, 4])
        assert ("[0,3]", "[0,1]") in edges
        assert ("[0,3]", "[2,3]") in edges
        assert ("[0,1]", "[0,0]") in edges
        assert ("[0,1]", "[1,1]") in edges

    def test_sums_correct(self) -> None:
        root, nodes, edges, sums = build_segtree([1, 2, 3, 4])
        assert sums["[0,0]"] == 1
        assert sums["[1,1]"] == 2
        assert sums["[0,1]"] == 3
        assert sums["[2,3]"] == 7
        assert sums["[0,3]"] == 10

    def test_single_element(self) -> None:
        root, nodes, edges, sums = build_segtree([42])
        assert root == "[0,0]"
        assert nodes == ["[0,0]"]
        assert edges == []
        assert sums["[0,0]"] == 42

    def test_empty_data(self) -> None:
        root, nodes, edges, sums = build_segtree([])
        assert root == "[0,0]"
        assert len(nodes) == 1


# ---------------------------------------------------------------
# Tree construction tests
# ---------------------------------------------------------------


class TestTreeConstruction:
    def test_standard_tree_5_nodes(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2, 3, 4, 5],
            "edges": [(1, 2), (1, 3), (2, 4), (2, 5)],
        })
        assert t.name == "T"
        assert t.root == 1
        assert len(t.nodes) == 5
        assert len(t.edges) == 4
        assert t.kind is None

    def test_segtree_from_data(self) -> None:
        t = Tree("st", {
            "kind": "segtree",
            "data": [1, 2, 3, 4],
        })
        assert t.root == "[0,3]"
        assert len(t.nodes) == 7
        assert t.kind == "segtree"

    def test_sparse_segtree(self) -> None:
        t = Tree("st", {
            "kind": "sparse_segtree",
            "range_lo": 0,
            "range_hi": 7,
        })
        assert t.root == "[0,7]"
        assert "[0,7]" in t.nodes
        assert t.kind == "sparse_segtree"

    def test_missing_root_raises_e1430(self) -> None:
        # v0.5.1: E1430 (Tree missing root)
        with pytest.raises(Exception, match="E1430"):
            Tree("T", {"nodes": [1, 2], "edges": [(1, 2)]})

    def test_segtree_missing_data_raises_e1431(self) -> None:
        with pytest.raises(Exception, match="E1431"):
            Tree("st", {"kind": "segtree"})

    def test_sparse_segtree_missing_range_raises_e1432(self) -> None:
        with pytest.raises(Exception, match="E1432"):
            Tree("st", {"kind": "sparse_segtree", "range_lo": 0})

    def test_label_parameter(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1],
            "edges": [],
            "label": "My Tree",
        })
        assert t.label == "My Tree"


# ---------------------------------------------------------------
# Selector tests
# ---------------------------------------------------------------


class TestTreeSelectors:
    @pytest.fixture()
    def tree(self) -> Tree:
        return Tree("T", {
            "root": 1,
            "nodes": [1, 2, 3, 4, 5],
            "edges": [(1, 2), (1, 3), (2, 4), (2, 5)],
        })

    def test_addressable_parts_contains_nodes(self, tree: Tree) -> None:
        parts = tree.addressable_parts()
        assert "node[1]" in parts
        assert "node[2]" in parts
        assert "node[5]" in parts

    def test_addressable_parts_contains_edges(self, tree: Tree) -> None:
        parts = tree.addressable_parts()
        assert "edge[(1,2)]" in parts
        assert "edge[(2,4)]" in parts

    def test_validate_selector_valid_node(self, tree: Tree) -> None:
        assert tree.validate_selector("node[1]") is True

    def test_validate_selector_valid_edge(self, tree: Tree) -> None:
        assert tree.validate_selector("edge[(1,2)]") is True

    def test_validate_selector_all(self, tree: Tree) -> None:
        assert tree.validate_selector("all") is True

    def test_validate_selector_invalid_node(self, tree: Tree) -> None:
        assert tree.validate_selector("node[99]") is False

    def test_validate_selector_invalid_edge(self, tree: Tree) -> None:
        assert tree.validate_selector("edge[(99,100)]") is False

    def test_segtree_selectors(self) -> None:
        t = Tree("st", {"kind": "segtree", "data": [1, 2, 3, 4]})
        parts = t.addressable_parts()
        assert "node[[0,3]]" in parts
        assert "node[[0,0]]" in parts


# ---------------------------------------------------------------
# Bounding box test
# ---------------------------------------------------------------


class TestTreeBoundingBox:
    def test_bounding_box_correct(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2, 3],
            "edges": [(1, 2), (1, 3)],
        })
        bb = t.bounding_box()
        assert bb.x == 0
        assert bb.y == 0
        assert bb.width >= 400
        assert bb.height >= 300


# ---------------------------------------------------------------
# SVG emission tests
# ---------------------------------------------------------------


class TestTreeEmitSvg:
    def test_svg_structure(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2, 3],
            "edges": [(1, 2), (1, 3)],
        })
        svg = t.emit_svg()
        assert 'data-primitive="tree"' in svg
        assert 'data-shape="T"' in svg

    def test_edges_before_nodes(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2, 3],
            "edges": [(1, 2), (1, 3)],
        })
        svg = t.emit_svg()
        edges_pos = svg.find("scriba-tree-edges")
        nodes_pos = svg.find("scriba-tree-nodes")
        assert edges_pos < nodes_pos

    def test_node_circle_radius(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1],
            "edges": [],
        })
        svg = t.emit_svg()
        assert 'r="20"' in svg

    def test_idle_node_uses_state_class(self) -> None:
        """β palette: a tree node with no explicit state carries the
        'idle' CSS state class on its wrapping <g>; fill and stroke are
        owned by the stylesheet, not inline."""
        t = Tree("T", {
            "root": 1,
            "nodes": [1],
            "edges": [],
        })
        svg = t.emit_svg()
        assert "scriba-state-idle" in svg

    def test_label_caption_rendered(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1],
            "edges": [],
            "label": "BST Demo",
        })
        svg = t.emit_svg()
        assert "BST Demo" in svg
        assert "scriba-primitive-label" in svg

    def test_empty_tree_svg(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [],
            "edges": [],
        })
        svg = t.emit_svg()
        assert 'data-primitive="tree"' in svg

    def test_show_sum_in_segtree(self) -> None:
        t = Tree("st", {
            "kind": "segtree",
            "data": [1, 2, 3, 4],
            "show_sum": True,
        })
        svg = t.emit_svg()
        assert "[0,3]=10" in svg
        assert "[0,1]=3" in svg


# ---------------------------------------------------------------
# State application tests
# ---------------------------------------------------------------


class TestTreeStateApplication:
    def test_node_recolor(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2],
            "edges": [(1, 2)],
        })
        t.set_state("node[1]", "current")
        svg = t.emit_svg()
        assert 'class="scriba-state-current"' in svg

    def test_edge_highlight(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2],
            "edges": [(1, 2)],
        })
        t.set_state("edge[(1,2)]", "highlight")
        svg = t.emit_svg()
        assert 'class="scriba-state-highlight"' in svg

    def test_default_state_is_idle(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1],
            "edges": [],
        })
        assert t.get_state("node[1]") == "idle"
