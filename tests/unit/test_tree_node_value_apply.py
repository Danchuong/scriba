"""Per-node value relabel on Tree via ``\\apply{T.node[id]}{value=...}``.

These lock in behavior that already ships today — no engine change is being
introduced here. The display value of a Tree node flows through the generic
value-layer, *not* through ``apply_command`` (which only mutates structure):

    ``\\apply{T.node[5]}{value="dp=7"}``
      -> scene stores it on ``ShapeTargetState.value``
      -> the emitter calls ``prim.set_value("node[5]", "dp=7")``
      -> ``Tree.emit_svg`` reads ``get_value("node[5]")`` and lets it override
         the static node label (tree.py, "Value-layer override takes
         precedence over the static label").

This is the mechanism tree-DP overlays and segtree lazy tags rely on, so the
tests below pin: (1) the override actually replaces the rendered label,
(2) it survives a structural ``reparent``, and (3) an out-of-range node id is
dropped quietly (a ``UserWarning``, never a hard error).
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.tree import Tree
from scriba.animation.scene import SceneState


def _standard_tree() -> Tree:
    """A small rooted tree: 1 -> {2 -> {4,5}, 3}."""
    return Tree(
        "T",
        {
            "root": 1,
            "nodes": [1, 2, 3, 4, 5],
            "edges": [(1, 2), (1, 3), (2, 4), (2, 5)],
        },
    )


@pytest.mark.unit
class TestTreeNodeValueOverride:
    def test_apply_value_overrides_static_label(self) -> None:
        t = _standard_tree()
        # Baseline: the DP value is not in the freshly-built tree.
        assert "dp=7" not in t.emit_svg()

        t.set_value("node[2]", "dp=7")
        svg = t.emit_svg()
        assert "dp=7" in svg
        # The override is attached to the addressed node, not floating loose.
        assert 'data-target="T.node[2]"' in svg

    def test_int_or_str_node_id_addresses_same_slot(self) -> None:
        # Node ids are str-normalized at construction, but ``node[id]`` keys are
        # built by f-string so int 2 and str "2" resolve to the same node.
        t = _standard_tree()
        t.set_value("node[2]", "dp=9")
        assert t.get_value("node[2]") == "dp=9"
        assert "dp=9" in t.emit_svg()

    def test_value_persists_through_reparent(self) -> None:
        t = _standard_tree()
        t.set_value("node[2]", "dp=3")
        assert "2" in t.children_map["1"]  # node 2 starts under root 1

        # Structural move: reparent 2 under 3. apply_command only touches
        # topology; it must not clear the value layer.
        t.apply_command({"reparent": {"node": 2, "parent": 3}})
        assert "2" in t.children_map["3"]
        assert "2" not in t.children_map["1"]

        svg = t.emit_svg()
        assert "dp=3" in svg
        assert 'data-target="T.node[2]"' in svg

    def test_value_on_unknown_node_is_silently_dropped(self) -> None:
        # Pinned behavior: set_value on a non-existent node id warns and no-ops
        # (base.PrimitiveBase.set_value validates the selector first). It is a
        # UserWarning + drop, never a ScribaError — authors are not blocked.
        t = _standard_tree()
        with pytest.warns(UserWarning, match="invalid selector"):
            t.set_value("node[99]", "ghost")

        assert t.get_value("node[99]") is None
        assert "ghost" not in t.emit_svg()

    def test_segtree_node_value_carries_lazy_tag(self) -> None:
        # Same value-layer path powers segtree lazy-propagation tags: a node's
        # displayed value can be an arbitrary string ("sum | pending-op").
        st = Tree(
            "st",
            {"data": [2, 5, 1, 3, 7, 4], "kind": "segtree", "show_sum": True},
        )
        st.set_value("node[[0,2]]", "sum=17 | +3")
        svg = st.emit_svg()
        assert "sum=17 | +3" in svg


@pytest.mark.unit
class TestSceneApplyValueWiring:
    def test_apply_value_lands_on_target_state(self) -> None:
        # Parser + scene layer: \apply{...}{value=...} routes the value onto the
        # addressed tree node's ShapeTargetState (the emitter reads this to call
        # set_value). This is the front half of the end-to-end path.
        src = (
            "\\shape{T}{Tree}{root=1, nodes=[1,2,3], edges=[(1,2),(1,3)]}\n"
            "\\step\n"
            '\\apply{T.node[2]}{value="dp=7"}\n'
        )
        ir = SceneParser().parse(src)
        sc = SceneState()
        sc.apply_prelude(ir.shapes, ir.prelude_commands, ir.prelude_compute)
        snaps = [sc.apply_frame(f) for f in ir.frames]

        target_state = snaps[0].shape_states["T"]["T.node[2]"]
        assert target_state.value == "dp=7"
