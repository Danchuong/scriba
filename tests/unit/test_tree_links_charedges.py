"""Unit tests for Tree char-edge labels + second link class (Wave-3 · B3).

Two additive extensions turn Tree into a substrate for trie / Aho-Corasick /
suffix-automaton (spine = suffix-link tree), per
``investigations/gap-new-substrates.md`` §6 and ``gap-dsu-forest-design.md`` §7:

- **Char-edge labels** — an edge may carry a *string* label, supplied either
  as a 3-tuple ``(parent, child, "a")`` in ``edges`` or via ``add_node`` with
  ``char="a"``. Unlike Graph's weighted 3-tuple, the third element is NOT
  coerced to ``float`` — it is a display glyph on the parent->child edge.
- **Second link class** — fail/suffix links declared with ``links=[(u,v)]``
  (plus ``add_link`` / ``remove_link`` ops). Links are a presentation overlay:
  they are excluded from ``children_map`` so Reingold-Tilford never sees them,
  addressed by ``T.link[(u,v)]``, and drawn as a dashed curved arrow.

All tests operate on Tree directly — no parser/emitter layers required — except
``TestSelectorCanonicalization`` which asserts the quoted-string authoring form
``T.link["(u,v)"]`` canonicalizes to the emitted ``T.link[(u,v)]`` key (the
addressing path that needs zero selector-parser change).
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.tree import Tree
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _std_tree(**extra) -> Tree:
    """A 4-node tree: root 0 with children 1, 2; 1 has child 3."""
    params = {
        "root": "0",
        "nodes": ["0", "1", "2", "3"],
        "edges": [("0", "1"), ("0", "2"), ("1", "3")],
    }
    params.update(extra)
    return Tree("T", params)


# ---------------------------------------------------------------------------
# 1. Char-edge labels
# ---------------------------------------------------------------------------


class TestCharEdgeLabels:
    def test_3tuple_edges_populate_labels(self) -> None:
        t = Tree(
            "T",
            {
                "root": "0",
                "nodes": ["0", "1", "2"],
                "edges": [("0", "1", "a"), ("0", "2", "b")],
            },
        )
        assert t.edge_labels == {("0", "1"): "a", ("0", "2"): "b"}
        # Structure is unchanged — the third element does not become an edge.
        assert t.edges == [("0", "1"), ("0", "2")]

    def test_label_is_string_not_float(self) -> None:
        # Graph coerces the 3rd tuple element to float; Tree must NOT — a
        # numeric-looking char label stays a display string.
        t = Tree(
            "T",
            {"root": "0", "nodes": ["0", "1"], "edges": [("0", "1", "5")]},
        )
        assert t.edge_labels[("0", "1")] == "5"
        assert isinstance(t.edge_labels[("0", "1")], str)

    def test_2tuple_edges_have_no_labels(self) -> None:
        t = _std_tree()
        assert t.edge_labels == {}

    def test_mixed_2_and_3_tuple_edges(self) -> None:
        # Tree labels are per-edge optional (Graph forbids the mix; Tree allows).
        t = Tree(
            "T",
            {
                "root": "0",
                "nodes": ["0", "1", "2"],
                "edges": [("0", "1", "a"), ("0", "2")],
            },
        )
        assert t.edge_labels == {("0", "1"): "a"}

    def test_emit_renders_label_text(self) -> None:
        t = Tree(
            "T",
            {"root": "0", "nodes": ["0", "1"], "edges": [("0", "1", "a")]},
        )
        svg = t.emit_svg()
        assert "scriba-tree-edge-label" in svg
        assert ">a<" in svg

    def test_numeric_node_ids_label_lookup(self) -> None:
        # Node ids given as ints are str-normalized; labels key on the same.
        t = Tree(
            "T",
            {"root": 0, "nodes": [0, 1], "edges": [(0, 1, "x")]},
        )
        assert t.edge_labels == {("0", "1"): "x"}


class TestAddNodeChar:
    def test_add_node_char_sets_label(self) -> None:
        t = _std_tree()
        t.apply_command({"add_node": {"id": "4", "parent": "1", "char": "c"}})
        assert t.edge_labels[("1", "4")] == "c"
        assert ">c<" in t.emit_svg()

    def test_add_node_without_char_has_no_label(self) -> None:
        t = _std_tree()
        t.apply_command({"add_node": {"id": "4", "parent": "1"}})
        assert ("1", "4") not in t.edge_labels

    def test_add_node_char_still_requires_id_parent(self) -> None:
        t = _std_tree()
        with pytest.raises(ValidationError, match="E1436"):
            t.apply_command({"add_node": {"char": "c"}})


# ---------------------------------------------------------------------------
# 2. Links prelude
# ---------------------------------------------------------------------------


class TestLinksPrelude:
    def test_links_param_populates(self) -> None:
        t = _std_tree(links=[("1", "2")])
        assert t.links == [("1", "2")]
        assert "link[(1,2)]" in t.addressable_parts()

    def test_links_str_normalized(self) -> None:
        t = _std_tree(links=[(1, 2)])
        assert t.links == [("1", "2")]

    def test_no_links_param_empty(self) -> None:
        t = _std_tree()
        assert t.links == []

    def test_links_excluded_from_children_map(self) -> None:
        t = _std_tree(links=[("1", "2")])
        # A fail-link between siblings must NOT become a parent->child edge.
        assert "2" not in t.children_map["1"]
        assert ("1", "2") not in t.edges

    def test_link_to_unknown_node_raises_e1436(self) -> None:
        with pytest.raises(ValidationError, match="E1436"):
            _std_tree(links=[("1", "99")])

    def test_emit_link_overlay(self) -> None:
        t = _std_tree(links=[("1", "2")])
        svg = t.emit_svg()
        assert "scriba-tree-link" in svg
        assert 'data-target="T.link[(1,2)]"' in svg

    def test_link_overlay_is_dashed_with_arrowhead(self) -> None:
        # R-13: fail-links need a NON-colour differentiator (dash). The
        # arrowhead is a self-contained <polygon> (no directed-graph marker
        # dependency).
        t = _std_tree(links=[("1", "2")])
        svg = t.emit_svg()
        assert "stroke-dasharray" in svg
        assert "<polygon" in svg


# ---------------------------------------------------------------------------
# 3. Link mutations
# ---------------------------------------------------------------------------


class TestLinkMutations:
    def test_add_link(self) -> None:
        t = _std_tree()
        t.apply_command({"add_link": {"from": "1", "to": "2"}})
        assert ("1", "2") in t.links
        assert 'data-target="T.link[(1,2)]"' in t.emit_svg()

    def test_add_link_str_normalized(self) -> None:
        t = _std_tree()
        t.apply_command({"add_link": {"from": 1, "to": 2}})
        assert ("1", "2") in t.links

    def test_add_link_unknown_node_raises_e1436(self) -> None:
        t = _std_tree()
        with pytest.raises(ValidationError, match="E1436"):
            t.apply_command({"add_link": {"from": "1", "to": "99"}})

    def test_add_link_duplicate_is_idempotent(self) -> None:
        t = _std_tree(links=[("1", "2")])
        t.apply_command({"add_link": {"from": "1", "to": "2"}})
        assert t.links.count(("1", "2")) == 1

    def test_add_link_malformed_raises_e1436(self) -> None:
        t = _std_tree()
        with pytest.raises(ValidationError, match="E1436"):
            t.apply_command({"add_link": {"from": "1"}})
        with pytest.raises(ValidationError, match="E1436"):
            t.apply_command({"add_link": "nope"})

    def test_remove_link(self) -> None:
        t = _std_tree(links=[("1", "2")])
        t.apply_command({"remove_link": {"from": "1", "to": "2"}})
        assert t.links == []
        assert "scriba-tree-link" not in t.emit_svg()

    def test_remove_link_nonexistent_raises_e1436(self) -> None:
        t = _std_tree()
        with pytest.raises(ValidationError, match="E1436"):
            t.apply_command({"remove_link": {"from": "1", "to": "2"}})

    def test_remove_node_prunes_touching_links(self) -> None:
        t = _std_tree(links=[("1", "2")])
        # Removing node 2 must drop any link that touches it (no dangling
        # overlay to a vanished node).
        t.apply_command({"remove_node": "2"})
        assert t.links == []
        assert "scriba-tree-link" not in t.emit_svg()


# ---------------------------------------------------------------------------
# 4. Links do not touch layout
# ---------------------------------------------------------------------------


class TestLinksDoNotAffectLayout:
    def test_positions_identical_with_and_without_links(self) -> None:
        base = _std_tree()
        linked = _std_tree(links=[("1", "2"), ("3", "0")])
        assert base.get_node_positions() == linked.get_node_positions()

    def test_bounding_box_identical(self) -> None:
        base = _std_tree()
        linked = _std_tree(links=[("1", "2")])
        assert base.bounding_box() == linked.bounding_box()

    def test_char_labels_do_not_move_nodes(self) -> None:
        plain = _std_tree()
        labelled = Tree(
            "T",
            {
                "root": "0",
                "nodes": ["0", "1", "2", "3"],
                "edges": [("0", "1", "a"), ("0", "2", "b"), ("1", "3", "c")],
            },
        )
        assert plain.get_node_positions() == labelled.get_node_positions()


# ---------------------------------------------------------------------------
# 5. Link selector addressability
# ---------------------------------------------------------------------------


class TestLinkSelector:
    def test_link_in_addressable_parts(self) -> None:
        t = _std_tree(links=[("1", "2")])
        assert "link[(1,2)]" in t.addressable_parts()
        # Nodes and tree edges remain addressable too.
        assert "node[1]" in t.addressable_parts()
        assert "edge[(0,1)]" in t.addressable_parts()

    def test_validate_link_selector(self) -> None:
        t = _std_tree(links=[("1", "2")])
        assert t.validate_selector("link[(1,2)]") is True
        assert t.validate_selector("link[(9,9)]") is False

    def test_resolve_annotation_point_link_midpoint(self) -> None:
        t = _std_tree(links=[("1", "2")])
        p1 = t.positions["1"]
        p2 = t.positions["2"]
        expected = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
        assert t.resolve_annotation_point("T.link[(1,2)]") == pytest.approx(expected)

    def test_resolve_annotation_point_unknown_link_is_none(self) -> None:
        t = _std_tree(links=[("1", "2")])
        assert t.resolve_annotation_point("T.link[(9,9)]") is None

    def test_recolor_link_changes_state(self) -> None:
        t = _std_tree(links=[("1", "2")])
        t.set_state("link[(1,2)]", "current")
        svg = t.emit_svg()
        assert "scriba-state-current" in svg
        assert 'data-target="T.link[(1,2)]"' in svg


class TestSelectorCanonicalization:
    """The quoted-string authoring form parses on the existing selector grammar
    and canonicalizes to the emitted link key — no ``_parse_link`` handler."""

    def test_quoted_link_selector_canonicalizes(self) -> None:
        from scriba.animation.parser.selectors import parse_selector
        from scriba.animation.scene import _selector_to_str

        sel = parse_selector('T.link["(1,2)"]')
        assert _selector_to_str(sel) == "T.link[(1,2)]"


# ---------------------------------------------------------------------------
# 6. Regression — plain / segtree / heap emit is byte-stable (additive only)
# ---------------------------------------------------------------------------


class TestRegressionByteStable:
    def test_plain_tree_has_no_link_or_label_markers(self) -> None:
        svg = _std_tree().emit_svg()
        assert "scriba-tree-link" not in svg
        assert "scriba-tree-edge-label" not in svg
        assert "stroke-dasharray" not in svg

    def test_segtree_unaffected(self) -> None:
        t = Tree("T", {"kind": "segtree", "data": [1, 2, 3, 4]})
        svg = t.emit_svg()
        assert t.edge_labels == {}
        assert t.links == []
        assert "scriba-tree-link" not in svg

    def test_heap_unaffected(self) -> None:
        t = Tree("T", {"kind": "heap", "data": [9, 7, 8, 3, 5]})
        svg = t.emit_svg()
        assert t.links == []
        assert "scriba-tree-link" not in svg

    def test_empty_tree_still_empty_group(self) -> None:
        t = Tree("T", {"root": "0", "nodes": ["0"], "edges": []})
        t.apply_command({"remove_node": {"id": "0", "cascade": True}})
        svg = t.emit_svg()
        assert "scriba-tree-link" not in svg
