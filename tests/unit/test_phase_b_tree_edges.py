"""Phase B edge-case tests for the Tree primitive.

Exercises single-node, linear, wide trees, segtree variants,
string/integer node IDs, state application, Reingold-Tilford layout,
and error handling.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.tree import Tree, build_segtree, reingold_tilford
from scriba.animation.primitives.base import STATE_COLORS
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# 1. Single-node tree (root only, no edges)
# ---------------------------------------------------------------------------


class TestSingleNodeTree:
    def test_root_only(self) -> None:
        t = Tree("T", {"root": 1, "nodes": [1], "edges": []})
        assert t.root == 1
        assert len(t.nodes) == 1
        assert len(t.edges) == 0

    def test_root_only_svg_renders(self) -> None:
        t = Tree("T", {"root": 1, "nodes": [1], "edges": []})
        svg = t.emit_svg()
        assert 'data-primitive="tree"' in svg
        assert "T.node[1]" in svg

    def test_root_only_no_edge_elements(self) -> None:
        t = Tree("T", {"root": 1, "nodes": [1], "edges": []})
        svg = t.emit_svg()
        assert "<line" not in svg


# ---------------------------------------------------------------------------
# 2. Linear tree (1->2->3->4, degenerate case)
# ---------------------------------------------------------------------------


class TestLinearTree:
    def test_linear_tree_structure(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2, 3, 4],
            "edges": [(1, 2), (2, 3), (3, 4)],
        })
        assert len(t.nodes) == 4
        assert len(t.edges) == 3

    def test_linear_tree_depth(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2, 3, 4],
            "edges": [(1, 2), (2, 3), (3, 4)],
        })
        # Max depth should be 3 (node 4 at depth 3)
        assert t._compute_max_depth() == 3

    def test_linear_tree_positions_unique_y(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2, 3, 4],
            "edges": [(1, 2), (2, 3), (3, 4)],
        })
        ys = [t.positions[n][1] for n in t.nodes]
        # All y values should be unique (each node at different depth)
        assert len(set(ys)) == 4


# ---------------------------------------------------------------------------
# 3. Wide tree (root with 10 children)
# ---------------------------------------------------------------------------


class TestWideTree:
    def test_wide_tree_10_children(self) -> None:
        nodes = list(range(11))
        edges = [(0, i) for i in range(1, 11)]
        t = Tree("T", {"root": 0, "nodes": nodes, "edges": edges})
        assert len(t.nodes) == 11
        assert len(t.edges) == 10

    def test_wide_tree_children_same_y(self) -> None:
        nodes = list(range(11))
        edges = [(0, i) for i in range(1, 11)]
        t = Tree("T", {"root": 0, "nodes": nodes, "edges": edges})
        child_ys = {t.positions[i][1] for i in range(1, 11)}
        # All children should be at the same depth (same y)
        assert len(child_ys) == 1

    def test_wide_tree_svg_renders_all_nodes(self) -> None:
        nodes = list(range(11))
        edges = [(0, i) for i in range(1, 11)]
        t = Tree("T", {"root": 0, "nodes": nodes, "edges": edges})
        svg = t.emit_svg()
        for i in range(11):
            assert f"T.node[{i}]" in svg


# ---------------------------------------------------------------------------
# 4. Segtree from data=[1] (single element)
# ---------------------------------------------------------------------------


class TestSegtreeSingleElement:
    def test_segtree_single_element(self) -> None:
        root, nodes, edges, sums = build_segtree([1])
        assert root == "[0,0]"
        assert nodes == ["[0,0]"]
        assert edges == []
        assert sums["[0,0]"] == 1

    def test_segtree_single_element_tree(self) -> None:
        t = Tree("st", {"kind": "segtree", "data": [1]})
        assert t.root == "[0,0]"
        assert len(t.nodes) == 1
        assert len(t.edges) == 0


# ---------------------------------------------------------------------------
# 5. Segtree from data=[1,2,3,4,5,6,7,8] -- verify [lo,hi] nodes
# ---------------------------------------------------------------------------


class TestSegtree8Elements:
    def test_segtree_8_elements_root(self) -> None:
        root, nodes, edges, sums = build_segtree([1, 2, 3, 4, 5, 6, 7, 8])
        assert root == "[0,7]"

    def test_segtree_8_elements_leaf_nodes(self) -> None:
        root, nodes, edges, sums = build_segtree([1, 2, 3, 4, 5, 6, 7, 8])
        for i in range(8):
            assert f"[{i},{i}]" in nodes

    def test_segtree_8_elements_internal_nodes(self) -> None:
        root, nodes, edges, sums = build_segtree([1, 2, 3, 4, 5, 6, 7, 8])
        assert "[0,3]" in nodes
        assert "[4,7]" in nodes
        assert "[0,1]" in nodes
        assert "[2,3]" in nodes

    def test_segtree_8_elements_sum(self) -> None:
        root, nodes, edges, sums = build_segtree([1, 2, 3, 4, 5, 6, 7, 8])
        assert sums["[0,7]"] == 36


# ---------------------------------------------------------------------------
# 6. Segtree node count: power of 2 -> 2N-1 nodes
# ---------------------------------------------------------------------------


class TestSegtreeNodeCount:
    def test_power_of_2_node_count(self) -> None:
        for n in [1, 2, 4, 8, 16]:
            data = list(range(n))
            root, nodes, edges, sums = build_segtree(data)
            assert len(nodes) == 2 * n - 1, f"Failed for n={n}"

    def test_non_power_of_2_still_builds(self) -> None:
        root, nodes, edges, sums = build_segtree([1, 2, 3, 4, 5])
        assert root == "[0,4]"
        assert "[0,4]" in nodes
        # 5 elements: 2*5-1 = 9 nodes
        assert len(nodes) == 9


# ---------------------------------------------------------------------------
# 7. Sparse segtree: verify root node exists
# ---------------------------------------------------------------------------


class TestSparseSegtree:
    def test_sparse_root_exists(self) -> None:
        t = Tree("st", {
            "kind": "sparse_segtree",
            "range_lo": 0,
            "range_hi": 1000000,
        })
        assert t.root == "[0,1000000]"
        assert "[0,1000000]" in t.nodes

    def test_sparse_starts_with_one_node(self) -> None:
        t = Tree("st", {
            "kind": "sparse_segtree",
            "range_lo": 0,
            "range_hi": 100,
        })
        assert len(t.nodes) == 1

    def test_sparse_missing_range_hi_raises(self) -> None:
        with pytest.raises(Exception, match="E1432"):
            Tree("st", {"kind": "sparse_segtree", "range_lo": 0})

    def test_sparse_missing_range_lo_raises(self) -> None:
        with pytest.raises(Exception, match="E1432"):
            Tree("st", {"kind": "sparse_segtree", "range_hi": 100})


# ---------------------------------------------------------------------------
# 8. Tree with string node IDs
# ---------------------------------------------------------------------------


class TestTreeStringNodeIds:
    def test_string_node_ids(self) -> None:
        t = Tree("T", {
            "root": "A",
            "nodes": ["A", "B", "C"],
            "edges": [("A", "B"), ("A", "C")],
        })
        assert t.root == "A"
        assert "A" in t.nodes
        assert "B" in t.nodes
        assert "C" in t.nodes

    def test_string_node_ids_in_svg(self) -> None:
        t = Tree("T", {
            "root": "A",
            "nodes": ["A", "B", "C"],
            "edges": [("A", "B"), ("A", "C")],
        })
        svg = t.emit_svg()
        assert "T.node[A]" in svg
        assert "T.node[B]" in svg


# ---------------------------------------------------------------------------
# 9. Tree with integer node IDs starting from 0
# ---------------------------------------------------------------------------


class TestTreeIntegerNodeIds:
    def test_integer_node_ids_from_zero(self) -> None:
        t = Tree("T", {
            "root": 0,
            "nodes": [0, 1, 2, 3],
            "edges": [(0, 1), (0, 2), (1, 3)],
        })
        assert t.root == 0
        assert 0 in t.nodes

    def test_integer_node_ids_svg(self) -> None:
        t = Tree("T", {
            "root": 0,
            "nodes": [0, 1, 2, 3],
            "edges": [(0, 1), (0, 2), (1, 3)],
        })
        svg = t.emit_svg()
        assert "T.node[0]" in svg
        assert "T.node[3]" in svg


# ---------------------------------------------------------------------------
# 10. Recolor tree edge -- verify inline fill changes
# ---------------------------------------------------------------------------


class TestTreeEdgeRecolor:
    def test_edge_recolor_changes_stroke(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2],
            "edges": [(1, 2)],
        })
        t.set_state("edge[(1,2)]", "current")
        svg = t.emit_svg()
        # current state stroke is #0072B2
        assert "#0072B2" in svg

    def test_edge_recolor_class(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2],
            "edges": [(1, 2)],
        })
        t.set_state("edge[(1,2)]", "done")
        svg = t.emit_svg()
        assert "scriba-state-done" in svg


# ---------------------------------------------------------------------------
# 11. Highlight tree node -- gold dashed overlay
# ---------------------------------------------------------------------------


class TestTreeNodeHighlight:
    def test_node_highlight_state(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2],
            "edges": [(1, 2)],
        })
        t.set_state("node[1]", "highlight")
        svg = t.emit_svg()
        assert "scriba-state-highlight" in svg
        # highlight fill color is #F0E442
        assert "#F0E442" in svg


# ---------------------------------------------------------------------------
# 12. Tree with show_sum=true: verify sum labels present
# ---------------------------------------------------------------------------


class TestTreeShowSum:
    def test_show_sum_labels(self) -> None:
        t = Tree("st", {
            "kind": "segtree",
            "data": [1, 2, 3, 4],
            "show_sum": True,
        })
        svg = t.emit_svg()
        assert "[0,3]=10" in svg
        assert "[0,0]=1" in svg

    def test_show_sum_false_no_sum_labels(self) -> None:
        t = Tree("st", {
            "kind": "segtree",
            "data": [1, 2, 3, 4],
            "show_sum": False,
        })
        svg = t.emit_svg()
        assert "=10" not in svg


# ---------------------------------------------------------------------------
# 13. Reingold-Tilford: no two nodes share same (x,y)
# ---------------------------------------------------------------------------


class TestReingoldTilfordNoOverlap:
    def test_no_position_collision(self) -> None:
        children = {
            1: [2, 3],
            2: [4, 5],
            3: [6, 7],
            4: [], 5: [], 6: [], 7: [],
        }
        positions = reingold_tilford(1, children)
        coords = list(positions.values())
        assert len(coords) == len(set(coords)), "Two nodes share the same position"

    def test_large_tree_no_overlap(self) -> None:
        """15-node complete binary tree -- no position collisions."""
        children = {}
        for i in range(1, 8):
            children[i] = [2 * i, 2 * i + 1]
        for i in range(8, 16):
            children[i] = []
        positions = reingold_tilford(1, children)
        coords = list(positions.values())
        assert len(coords) == len(set(coords))


# ---------------------------------------------------------------------------
# 14. Reingold-Tilford: parent centered above children
# ---------------------------------------------------------------------------


class TestReingoldTilfordCentered:
    def test_parent_x_between_children(self) -> None:
        children = {1: [2, 3], 2: [], 3: []}
        positions = reingold_tilford(1, children, width=400, height=300)
        px = positions[1][0]
        left_x = positions[2][0]
        right_x = positions[3][0]
        assert left_x <= px <= right_x

    def test_parent_above_children(self) -> None:
        children = {1: [2, 3], 2: [], 3: []}
        positions = reingold_tilford(1, children)
        parent_y = positions[1][1]
        child_y = positions[2][1]
        assert parent_y < child_y  # Parent is above (lower y value)


# ---------------------------------------------------------------------------
# 15. Missing root param without segtree kind -> E1430
# ---------------------------------------------------------------------------


class TestTreeMissingRoot:
    def test_missing_root_raises_e1430(self) -> None:
        with pytest.raises(Exception, match="E1430"):
            Tree("T", {"nodes": [1, 2], "edges": [(1, 2)]})

    def test_missing_root_with_edges_only(self) -> None:
        with pytest.raises(Exception, match="E1430"):
            Tree("T", {"edges": [(1, 2)]})


# ---------------------------------------------------------------------------
# 16. Empty children_map for reingold_tilford
# ---------------------------------------------------------------------------


class TestReingoldTilfordEmpty:
    def test_empty_children_map_single_node(self) -> None:
        positions = reingold_tilford("root", {})
        assert "root" in positions

    def test_single_node_centered_in_viewport(self) -> None:
        positions = reingold_tilford("root", {}, width=400, height=300)
        x, y = positions["root"]
        assert x == 200  # width // 2


# ---------------------------------------------------------------------------
# 17. Segtree with non-numeric data
# ---------------------------------------------------------------------------


class TestSegtreeNonNumeric:
    def test_string_data_sums_to_zero(self) -> None:
        """Segment tree with string data: sums should default to 0."""
        root, nodes, edges, sums = build_segtree(["a", "b", "c", "d"])
        # Leaf sums are the strings themselves
        assert sums["[0,0]"] == "a"
        # Internal sums fall back to 0 because strings aren't (int, float)
        assert sums["[0,1]"] == 0
        assert sums["[0,3]"] == 0


# ---------------------------------------------------------------------------
# 18. Tree label in SVG
# ---------------------------------------------------------------------------


class TestTreeLabelInSvg:
    def test_label_present(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1],
            "edges": [],
            "label": "My BST",
        })
        svg = t.emit_svg()
        assert "My BST" in svg
        assert "scriba-primitive-label" in svg

    def test_no_label_no_text(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1],
            "edges": [],
        })
        svg = t.emit_svg()
        assert "scriba-primitive-label" not in svg


# ---------------------------------------------------------------------------
# 19. Default state is idle
# ---------------------------------------------------------------------------


class TestTreeDefaultState:
    def test_default_node_state_idle(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2],
            "edges": [(1, 2)],
        })
        assert t.get_state("node[1]") == "idle"
        assert t.get_state("node[2]") == "idle"

    def test_default_edge_state_idle(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [1, 2],
            "edges": [(1, 2)],
        })
        assert t.get_state("edge[(1,2)]") == "idle"


# ---------------------------------------------------------------------------
# 20. Root auto-inserted into nodes
# ---------------------------------------------------------------------------


class TestTreeRootAutoInsert:
    def test_root_added_if_not_in_nodes(self) -> None:
        t = Tree("T", {
            "root": 1,
            "nodes": [2, 3],
            "edges": [(1, 2), (1, 3)],
        })
        assert 1 in t.nodes
