"""Unit tests for the Tree ``kind=heap`` variant (Wave 1).

A heap is a complete binary tree derived from a backing array: node ``i``
(0-based array index) is the parent of ``2i+1`` and ``2i+2``, with the root at
index ``0``. Node *ids* are the array indices (addressed as ``h.node[i]``),
while node *labels* show the stored values. The structure is derived from
``data`` alone, mirroring ``kind=segtree``.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.tree import Tree

_SAMPLE = [9, 7, 8, 3, 5, 6, 4]


def _make_heap(data: list | None = None) -> Tree:
    return Tree("h", {"kind": "heap", "data": _SAMPLE if data is None else data})


class TestHeapConstruction:
    def test_kind_recorded(self) -> None:
        assert _make_heap().kind == "heap"

    def test_root_is_index_zero(self) -> None:
        assert _make_heap().root == "0"

    def test_nodes_are_array_indices(self) -> None:
        h = _make_heap(_SAMPLE)
        assert h.nodes == ["0", "1", "2", "3", "4", "5", "6"]

    def test_node_count_matches_data(self) -> None:
        assert len(_make_heap([10, 20, 30]).nodes) == 3

    def test_edges_follow_2i_plus_1_and_2(self) -> None:
        h = _make_heap(_SAMPLE)
        assert ("0", "1") in h.edges
        assert ("0", "2") in h.edges
        assert ("1", "3") in h.edges
        assert ("1", "4") in h.edges
        assert ("2", "5") in h.edges
        assert ("2", "6") in h.edges
        assert len(h.edges) == 6

    def test_partial_last_level(self) -> None:
        # n=5: node 1 -> (3, 4); node 2 has no children (5, 6 out of range).
        h = _make_heap([5, 4, 3, 2, 1])
        assert ("1", "3") in h.edges
        assert ("1", "4") in h.edges
        assert ("2", "5") not in h.edges
        assert ("2", "6") not in h.edges
        assert len(h.edges) == 4

    def test_single_element_heap(self) -> None:
        h = _make_heap([42])
        assert h.nodes == ["0"]
        assert h.edges == []

    def test_labels_are_values_not_indices(self) -> None:
        h = _make_heap(_SAMPLE)
        assert h.node_labels["0"] == "9"
        assert h.node_labels["1"] == "7"
        assert h.node_labels["6"] == "4"

    def test_ignores_author_nodes_and_edges(self) -> None:
        # Decision (a): kind=heap is data-driven like segtree — the
        # complete-binary-tree shape is implied by the array, so any
        # author-supplied nodes/edges are ignored (not merged).
        h = Tree(
            "h",
            {
                "kind": "heap",
                "data": [1, 2, 3],
                "nodes": ["x", "y"],
                "edges": [("x", "y")],
            },
        )
        assert h.nodes == ["0", "1", "2"]
        assert ("0", "1") in h.edges
        assert "x" not in h.nodes


class TestHeapErrors:
    def test_missing_data_raises_e1438(self) -> None:
        with pytest.raises(Exception, match="E1438"):
            Tree("h", {"kind": "heap"})

    def test_empty_data_raises_e1438(self) -> None:
        with pytest.raises(Exception, match="E1438"):
            Tree("h", {"kind": "heap", "data": []})


class TestHeapAddressing:
    def test_addressable_parts_contains_index_nodes(self) -> None:
        parts = _make_heap(_SAMPLE).addressable_parts()
        assert "node[0]" in parts
        assert "node[6]" in parts

    def test_validate_selector_index_node(self) -> None:
        h = _make_heap()
        assert h.validate_selector("node[0]") is True
        assert h.validate_selector("node[3]") is True

    def test_validate_selector_out_of_range(self) -> None:
        assert _make_heap([1, 2, 3]).validate_selector("node[9]") is False

    def test_resolve_annotation_point_by_index(self) -> None:
        pt = _make_heap(_SAMPLE).resolve_annotation_point("h.node[0]")
        assert pt is not None
        assert len(pt) == 2

    def test_positions_cover_all_nodes(self) -> None:
        h = _make_heap(_SAMPLE)
        for node_id in h.nodes:
            assert node_id in h.positions


class TestHeapValueRelabel:
    def test_apply_value_overrides_label_in_svg(self) -> None:
        h = _make_heap(_SAMPLE)
        # "99" is not among the sample values, so its presence proves the
        # value-layer override replaced node 0's original "9" label.
        h.set_value("node[0]", "99")
        assert "99" in h.emit_svg()

    def test_sift_swap_two_applies_exchange_values(self) -> None:
        # A sift/swap step = two \apply value commands exchanging the labels
        # of two nodes; positions (Reingold-Tilford layout) stay put.
        h = _make_heap(_SAMPLE)
        before = dict(h.positions)
        h.set_value("node[0]", "7")
        h.set_value("node[1]", "9")
        assert h.get_value("node[0]") == "7"
        assert h.get_value("node[1]") == "9"
        assert h.positions == before
        assert 'data-primitive="tree"' in h.emit_svg()


class TestOtherKindsUnaffected:
    """Regression: adding kind=heap must not change the existing kinds."""

    def test_segtree_still_builds(self) -> None:
        t = Tree("st", {"kind": "segtree", "data": [1, 2, 3, 4]})
        assert t.root == "[0,3]"
        assert len(t.nodes) == 7
        assert t.kind == "segtree"

    def test_sparse_segtree_still_builds(self) -> None:
        t = Tree("st", {"kind": "sparse_segtree", "range_lo": 0, "range_hi": 7})
        assert t.root == "[0,7]"
        assert t.kind == "sparse_segtree"

    def test_standard_tree_still_builds(self) -> None:
        t = Tree("T", {"root": 1, "nodes": [1, 2, 3], "edges": [(1, 2), (1, 3)]})
        assert t.root == "1"
        assert t.kind is None
        assert len(t.nodes) == 3

    def test_segtree_missing_data_still_e1431(self) -> None:
        with pytest.raises(Exception, match="E1431"):
            Tree("st", {"kind": "segtree"})

    def test_standard_missing_root_still_e1430(self) -> None:
        with pytest.raises(Exception, match="E1430"):
            Tree("T", {"nodes": [1, 2], "edges": [(1, 2)]})
