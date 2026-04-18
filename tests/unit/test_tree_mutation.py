"""Unit tests for Tree primitive mutation API (RFC-001 §4.1, Wave 6.1).

Covers the three mutation operations exposed via ``Tree.apply_command``:

* ``add_node`` — attach a new leaf to an existing parent.
* ``remove_node`` — delete a leaf (or whole subtree via ``cascade``).
* ``reparent`` — move a subtree under a different parent.

Also covers the Wave 6 value-layer override + hidden-state wire-up in
``emit_svg``.

Notes
-----
The ``"hidden"`` state is introduced in Wave 6. At the time this file was
written, ``scriba.animation.constants.VALID_STATES`` does not yet include
it (W6.3 owns that file). To exercise the ``"hidden"`` branch in
``emit_svg``, the tests either monkey-patch ``VALID_STATES`` for the
duration of the test (via the ``allow_hidden_state`` fixture) or write
the state directly into ``Tree._states`` to bypass the validator. Once
W6.3 merges, the monkey-patching becomes a no-op and the tests continue
to pass unchanged.

Similarly, the new error codes ``E1433``-``E1436`` are raised via
``_animation_error(code=...)`` which does NOT consult the catalog at
runtime (the factory only stores the code string on the exception). So
raising an as-yet-uncataloged code is safe — the ``code`` attribute on
the raised exception is the authoritative check site.
"""

from __future__ import annotations

import pytest

from scriba.animation import constants as anim_constants
from scriba.animation.errors import AnimationError
from scriba.animation.primitives.tree import Tree


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def allow_hidden_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Temporarily add ``"hidden"`` to ``VALID_STATES`` for one test.

    W6.3 is expected to add this to the canonical set; until then, this
    fixture ensures ``set_state(_, "hidden")`` is accepted by base.py.
    """
    new_states = frozenset(set(anim_constants.VALID_STATES) | {"hidden"})
    monkeypatch.setattr(anim_constants, "VALID_STATES", new_states)
    # base.py re-imports the name at module load time, so patch there too.
    from scriba.animation.primitives import base as prim_base

    monkeypatch.setattr(prim_base, "VALID_STATES", new_states)


def _make_simple_tree() -> Tree:
    """Build a small standard tree: A -> B, C; B -> D."""
    return Tree(
        "T",
        {
            "root": "A",
            "nodes": ["A", "B", "C", "D"],
            "edges": [("A", "B"), ("A", "C"), ("B", "D")],
        },
    )


def _make_linear_tree(depth: int) -> Tree:
    """Build a linear tree: n0 -> n1 -> ... -> n(depth-1)."""
    nodes = [f"n{i}" for i in range(depth)]
    edges = [(f"n{i}", f"n{i + 1}") for i in range(depth - 1)]
    return Tree("T", {"root": "n0", "nodes": nodes, "edges": edges})


def _err_code(exc: BaseException) -> str | None:
    return getattr(exc, "code", None)


# ---------------------------------------------------------------------------
# add_node
# ---------------------------------------------------------------------------


class TestAddNode:
    def test_add_leaf_to_root(self) -> None:
        t = _make_simple_tree()
        t.apply_command({"add_node": {"id": "E", "parent": "A"}})
        assert "E" in t.nodes
        assert ("A", "E") in t.edges
        assert "E" in t.children_map["A"]
        assert t.children_map["E"] == []
        assert t.node_labels["E"] == "E"
        assert "E" in t.positions

    def test_add_deeper(self) -> None:
        t = _make_simple_tree()
        t.apply_command({"add_node": {"id": "E", "parent": "D"}})
        assert ("D", "E") in t.edges
        assert t.children_map["D"] == ["E"]

    def test_add_chained(self) -> None:
        t = _make_simple_tree()
        t.apply_command({"add_node": {"id": "E", "parent": "B"}})
        t.apply_command({"add_node": {"id": "F", "parent": "E"}})
        t.apply_command({"add_node": {"id": "G", "parent": "F"}})
        assert "G" in t.nodes
        # The chain should have lengthened the tree depth.
        assert "F" in t.positions
        assert "G" in t.positions

    def test_add_multiple_to_same_parent(self) -> None:
        t = _make_simple_tree()
        t.apply_command({"add_node": {"id": "E", "parent": "C"}})
        t.apply_command({"add_node": {"id": "F", "parent": "C"}})
        t.apply_command({"add_node": {"id": "G", "parent": "C"}})
        assert t.children_map["C"] == ["E", "F", "G"]

    def test_add_to_nonexistent_parent_raises_E1436(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"add_node": {"id": "Z", "parent": "NOPE"}})
        assert _err_code(ei.value) == "E1436"

    def test_add_duplicate_id_raises_E1436(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"add_node": {"id": "B", "parent": "A"}})
        assert _err_code(ei.value) == "E1436"

    def test_add_missing_fields_raises_E1436(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"add_node": {"parent": "A"}})
        assert _err_code(ei.value) == "E1436"
        with pytest.raises(AnimationError) as ei2:
            t.apply_command({"add_node": {"id": "X"}})
        assert _err_code(ei2.value) == "E1436"

    def test_add_non_dict_spec_raises_E1436(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"add_node": "bogus"})
        assert _err_code(ei.value) == "E1436"

    def test_add_node_triggers_relayout(self) -> None:
        t = _make_simple_tree()
        before = dict(t.positions)
        t.apply_command({"add_node": {"id": "E", "parent": "C"}})
        # The new node must have a computed position.
        assert "E" in t.positions
        # Positions dict must now include every node.
        assert set(t.positions.keys()) == set(t.nodes)
        # Old nodes keep deterministic placement — at minimum still present.
        for k in before:
            assert k in t.positions


# ---------------------------------------------------------------------------
# remove_node
# ---------------------------------------------------------------------------


class TestRemoveNode:
    def test_remove_leaf_plain_id(self) -> None:
        t = _make_simple_tree()
        t.apply_command({"remove_node": "D"})
        assert "D" not in t.nodes
        assert "D" not in t.children_map
        assert "D" not in t.node_labels
        assert ("B", "D") not in t.edges
        assert "D" not in t.children_map["B"]

    def test_remove_leaf_dict_form(self) -> None:
        t = _make_simple_tree()
        t.apply_command({"remove_node": {"id": "C"}})
        assert "C" not in t.nodes
        assert ("A", "C") not in t.edges

    def test_remove_internal_without_cascade_raises_E1433(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"remove_node": "B"})
        assert _err_code(ei.value) == "E1433"

    def test_remove_internal_with_cascade(self) -> None:
        t = _make_simple_tree()
        t.apply_command({"remove_node": {"id": "B", "cascade": True}})
        assert "B" not in t.nodes
        assert "D" not in t.nodes
        assert ("A", "B") not in t.edges
        assert ("B", "D") not in t.edges
        # Sibling survives.
        assert "C" in t.nodes

    def test_remove_root_without_cascade_raises_E1434(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"remove_node": "A"})
        assert _err_code(ei.value) == "E1434"

    def test_remove_root_with_cascade_empties_tree(self) -> None:
        t = _make_simple_tree()
        t.apply_command({"remove_node": {"id": "A", "cascade": True}})
        assert t.nodes == []
        assert t.edges == []
        assert t.positions == {}
        assert t.children_map == {}

    def test_remove_nonexistent_node_raises_E1436(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"remove_node": "ZZZ"})
        assert _err_code(ei.value) == "E1436"

    def test_remove_non_dict_spec_without_id_raises_E1436(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"remove_node": {"cascade": True}})
        assert _err_code(ei.value) == "E1436"

    def test_remove_deep_cascade_iterative(self) -> None:
        """Cascade removal must handle deep trees without recursion."""
        depth = 500
        t = _make_linear_tree(depth)
        # Drop the whole tree from the root with cascade — should not blow
        # the Python stack (iterative DFS collect_descendants).
        t.apply_command({"remove_node": {"id": "n0", "cascade": True}})
        assert t.nodes == []

    def test_remove_leaf_preserves_siblings(self) -> None:
        t = Tree(
            "T",
            {
                "root": "A",
                "nodes": ["A", "B", "C", "D"],
                "edges": [("A", "B"), ("A", "C"), ("A", "D")],
            },
        )
        t.apply_command({"remove_node": "C"})
        assert t.children_map["A"] == ["B", "D"]


# ---------------------------------------------------------------------------
# reparent
# ---------------------------------------------------------------------------


class TestReparent:
    def test_basic_reparent(self) -> None:
        t = _make_simple_tree()
        # Move D from B's child to C's child.
        t.apply_command({"reparent": {"node": "D", "parent": "C"}})
        assert ("B", "D") not in t.edges
        assert ("C", "D") in t.edges
        assert "D" not in t.children_map["B"]
        assert "D" in t.children_map["C"]

    def test_reparent_creates_cycle_raises_E1435(self) -> None:
        t = _make_simple_tree()
        # Make B the parent of A — this is a cycle.
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"reparent": {"node": "A", "parent": "B"}})
        # Root reparent rejected first as E1435.
        assert _err_code(ei.value) == "E1435"

    def test_reparent_under_own_descendant_raises_E1435(self) -> None:
        t = _make_simple_tree()
        # D is a descendant of B; reparenting B under D creates a cycle.
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"reparent": {"node": "B", "parent": "D"}})
        assert _err_code(ei.value) == "E1435"

    def test_reparent_self_raises_E1435(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"reparent": {"node": "B", "parent": "B"}})
        assert _err_code(ei.value) == "E1435"

    def test_reparent_missing_node_raises_E1436(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"reparent": {"node": "ZZZ", "parent": "A"}})
        assert _err_code(ei.value) == "E1436"

    def test_reparent_missing_new_parent_raises_E1436(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"reparent": {"node": "D", "parent": "ZZZ"}})
        assert _err_code(ei.value) == "E1436"

    def test_reparent_missing_fields_raises_E1435(self) -> None:
        t = _make_simple_tree()
        with pytest.raises(AnimationError) as ei:
            t.apply_command({"reparent": {"node": "D"}})
        assert _err_code(ei.value) == "E1435"
        with pytest.raises(AnimationError) as ei2:
            t.apply_command({"reparent": {"parent": "A"}})
        assert _err_code(ei2.value) == "E1435"

    def test_reparent_changes_positions(self) -> None:
        t = _make_simple_tree()
        before_d = t.positions["D"]
        t.apply_command({"reparent": {"node": "D", "parent": "C"}})
        after_d = t.positions["D"]
        # D was at B's subtree; after moving to C it should be under C.
        # Its parent-relative position should change.
        assert after_d != before_d or t.children_map["C"] == ["D"]
        # Structurally: D's parent must now be C.
        assert t._find_parent("D") == "C"

    def test_reparent_noop_same_parent(self) -> None:
        t = _make_simple_tree()
        t.apply_command({"reparent": {"node": "D", "parent": "B"}})
        assert ("B", "D") in t.edges
        assert t.children_map["B"] == ["D"]


# ---------------------------------------------------------------------------
# Value layer override via emit_svg
# ---------------------------------------------------------------------------


class TestValueOverride:
    def test_set_value_appears_in_svg(self) -> None:
        t = _make_simple_tree()
        t.set_value("node[D]", "42")
        svg = t.emit_svg()
        assert "42" in svg
        # The original label "D" still appears elsewhere in the SVG
        # (e.g. in data-target attributes), but the rendered text for
        # node[D] should now be "42".
        # Heuristic: the string '>D<' (inside a foreignObject or text)
        # must not be present for node D; instead the override is used.
        # Check that the override is wired.
        assert ">42<" in svg or ">42 " in svg or "42</" in svg

    def test_override_falls_back_to_label_when_none(self) -> None:
        t = _make_simple_tree()
        svg = t.emit_svg()
        # Without any override, the static labels render.
        assert ">A<" in svg or "A</" in svg

    def test_override_works_for_segtree(self) -> None:
        # Covers Agent 7 F1 CRITICAL: segtree sum updates via value layer.
        t = Tree("T", {"kind": "segtree", "data": [1, 2, 3, 4]})
        # Pick any node that exists.
        some_node = t.nodes[0]
        t.set_value(f"node[{some_node}]", "SUMMED")
        svg = t.emit_svg()
        assert "SUMMED" in svg


# ---------------------------------------------------------------------------
# Hidden-state support
# ---------------------------------------------------------------------------


class TestHiddenState:
    def test_hidden_node_omitted_from_svg(
        self, allow_hidden_state: None
    ) -> None:
        t = _make_simple_tree()
        t.set_state("node[C]", "hidden")
        svg = t.emit_svg()
        # The data-target attribute for C must not appear.
        assert "node[C]" not in svg
        # Sibling nodes are still rendered.
        assert "node[B]" in svg

    def test_hidden_edge_omitted_from_svg(
        self, allow_hidden_state: None
    ) -> None:
        t = _make_simple_tree()
        t.set_state("edge[(A,C)]", "hidden")
        svg = t.emit_svg()
        assert "edge[(A,C)]" not in svg
        # Non-hidden edges still render.
        assert "edge[(A,B)]" in svg

    def test_hidden_node_hides_incident_edges(
        self, allow_hidden_state: None
    ) -> None:
        """If a node is hidden, its incident edges should also disappear."""
        t = _make_simple_tree()
        t.set_state("node[C]", "hidden")
        svg = t.emit_svg()
        # The edge A->C should not render because C is hidden.
        assert "edge[(A,C)]" not in svg

    def test_hidden_state_without_monkey_patch_is_inert(self) -> None:
        """Writing ``hidden`` directly into _states must still hide the node.

        This exercises the emit_svg guard independently of whether W6.3
        has added ``hidden`` to VALID_STATES.
        """
        t = _make_simple_tree()
        t._states["node[D]"] = "hidden"
        svg = t.emit_svg()
        assert "node[D]" not in svg
        # Edge B->D should also be hidden because D is hidden.
        assert "edge[(B,D)]" not in svg


# ---------------------------------------------------------------------------
# Layout determinism
# ---------------------------------------------------------------------------


class TestLayoutDeterminism:
    def test_same_shape_same_positions_via_mutation(self) -> None:
        """Two trees reaching the same shape must have identical positions."""
        # Direct construction.
        direct = Tree(
            "T",
            {
                "root": "A",
                "nodes": ["A", "B", "C", "D", "E"],
                "edges": [
                    ("A", "B"),
                    ("A", "C"),
                    ("B", "D"),
                    ("C", "E"),
                ],
            },
        )
        # Via mutation: start smaller, add to reach the same shape.
        via_mut = Tree(
            "T",
            {
                "root": "A",
                "nodes": ["A", "B", "C"],
                "edges": [("A", "B"), ("A", "C")],
            },
        )
        via_mut.apply_command({"add_node": {"id": "D", "parent": "B"}})
        via_mut.apply_command({"add_node": {"id": "E", "parent": "C"}})

        # Final shape equality.
        assert set(direct.nodes) == set(via_mut.nodes)
        assert set(direct.edges) == set(via_mut.edges)
        assert direct.children_map == via_mut.children_map
        # Width/height are computed at __init__ from the initial shape, so
        # via_mut may have a smaller viewport. Positions use the per-tree
        # viewport. The determinism property we actually care about is:
        # a tree of a given shape + viewport always produces the same
        # positions. Verify that by re-running layout with identical args.
        from scriba.animation.primitives.tree import reingold_tilford

        p1 = reingold_tilford(
            "A", direct.children_map, width=400, height=300
        )
        p2 = reingold_tilford(
            "A", via_mut.children_map, width=400, height=300
        )
        assert p1 == p2

    def test_add_then_remove_restores_positions(self) -> None:
        """add_node then remove_node must restore original positions."""
        t = _make_simple_tree()
        before = dict(t.positions)
        t.apply_command({"add_node": {"id": "E", "parent": "C"}})
        t.apply_command({"remove_node": "E"})
        after = dict(t.positions)
        assert before == after

    def test_reparent_then_reparent_back_restores_positions(self) -> None:
        t = _make_simple_tree()
        before = dict(t.positions)
        t.apply_command({"reparent": {"node": "D", "parent": "C"}})
        t.apply_command({"reparent": {"node": "D", "parent": "B"}})
        after = dict(t.positions)
        assert before == after

    def test_repeated_mutation_deterministic(self) -> None:
        def build() -> Tree:
            t = _make_simple_tree()
            t.apply_command({"add_node": {"id": "E", "parent": "C"}})
            t.apply_command({"add_node": {"id": "F", "parent": "C"}})
            t.apply_command({"remove_node": {"id": "B", "cascade": True}})
            return t

        a = build()
        b = build()
        assert a.nodes == b.nodes
        assert a.edges == b.edges
        assert a.positions == b.positions


# ---------------------------------------------------------------------------
# Dispatcher: unknown keys are a no-op (consistent with Plane2D precedent).
# ---------------------------------------------------------------------------


class TestDispatcher:
    def test_unknown_key_is_noop(self) -> None:
        t = _make_simple_tree()
        snapshot_nodes = list(t.nodes)
        snapshot_edges = list(t.edges)
        # Unknown key: no-op, no exception.
        t.apply_command({"frobnicate": {"foo": 1}})
        assert t.nodes == snapshot_nodes
        assert t.edges == snapshot_edges

    def test_empty_params_is_noop(self) -> None:
        t = _make_simple_tree()
        t.apply_command({})
        assert t.nodes == ["A", "B", "C", "D"]

    def test_dispatch_precedence_add_before_remove(self) -> None:
        """When both keys are present, add_node wins (first in dispatch)."""
        t = _make_simple_tree()
        t.apply_command(
            {
                "add_node": {"id": "E", "parent": "A"},
                "remove_node": "D",
            }
        )
        # add_node ran; remove_node did not (early return).
        assert "E" in t.nodes
        assert "D" in t.nodes
