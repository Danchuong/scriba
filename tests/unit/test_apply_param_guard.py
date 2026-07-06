r"""Silent-swallow hardening for ``\apply`` and node-construction params.

Three failure modes in the "accepted, dropped, no signal" family are pinned
here (the same class 0.25.0 hardened for \trace E1159 / soft-drop E1115):

1. **E1105** — an unknown ``\apply`` param used to be stashed into
   ``apply_params`` and silently ignored by every primitive's
   ``apply_command`` (a segtree ``\apply{st.node[..]}{lazy="+3"}`` rendered
   clean, the ``+3`` appearing nowhere).  Now the pipeline validates the
   spec against the primitive's declared ``APPLY_KEYS`` and raises.
2. **E1104** — a Tree/Forest ``nodes=`` entry that is a list/tuple was
   ``str()``-mangled into a bogus scalar id.  Now it raises with a hint.
3. **E1115** — the invalid-selector ``set_value``/``set_state`` soft-drop
   warnings now carry the ``[E1115]`` machine-readable prefix so E-code
   render gates see them.
"""

from __future__ import annotations

import pytest

from scriba.animation._frame_renderer import _validate_apply_spec
from scriba.animation.errors import AnimationError
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.bar import Bar
from scriba.animation.primitives.equation import Equation
from scriba.animation.primitives.forest import Forest
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.hashmap import HashMap
from scriba.animation.primitives.hypercube import Hypercube
from scriba.animation.primitives.linkedlist import LinkedList
from scriba.animation.primitives.metricplot import MetricPlot
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives.queue import Deque, Queue
from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.tracetable import TraceTable
from scriba.animation.primitives.tree import Tree
from scriba.animation.primitives.variablewatch import VariableWatch
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext


def _segtree() -> Tree:
    return Tree("st", {"data": [1, 2, 3, 4], "kind": "segtree", "show_sum": True})


def _standard_tree() -> Tree:
    return Tree(
        "T",
        {"root": 1, "nodes": [1, 2, 3, 4, 5], "edges": [(1, 2), (1, 3), (2, 4), (2, 5)]},
    )


def _ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        metadata={"output_mode": "interactive"},
        warnings_collector=None,
    )


def _render(body: str) -> str:
    """Drive the full animation pipeline (scene -> measure -> emit)."""
    renderer = AnimationRenderer()
    source = '\\begin{animation}[id="guard-test"]\n' + body + "\n\\end{animation}"
    blocks = renderer.detect(source)
    assert len(blocks) == 1
    return renderer.render_block(blocks[0], _ctx()).html


# ---------------------------------------------------------------------------
# HAZARD 1 — E1105: unknown \apply param is rejected, not swallowed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestApplyParamGuardE1105:
    def test_unknown_key_on_segtree_raises_e1105(self) -> None:
        with pytest.raises(AnimationError) as ei:
            _validate_apply_spec(_segtree(), {"lazy": "+3"})
        assert ei.value.code == "E1105"
        msg = str(ei.value)
        assert "lazy" in msg
        assert "Tree" in msg  # names the primitive type
        # The supported structural keys are named, and the generic value=
        # channel (the real segtree lazy-tag recipe) is surfaced.
        assert "reparent" in msg
        assert "value" in msg

    def test_typo_key_on_array_raises_e1105(self) -> None:
        arr = ArrayPrimitive("a", {"values": [1, 2, 3, 4]})
        with pytest.raises(AnimationError) as ei:
            _validate_apply_spec(arr, {"vlaue": 7})
        assert ei.value.code == "E1105"
        assert "vlaue" in str(ei.value)

    def test_generic_value_label_never_flagged(self) -> None:
        # value=/label= are the generic ShapeTargetState display channels; they
        # must pass the guard on any primitive (here a Tree that has no such
        # structural op of its own).
        _validate_apply_spec(_standard_tree(), {"value": "dp=7"})
        _validate_apply_spec(_standard_tree(), {"label": "root"})

    def test_apply_state_raises_e1105_steering_to_recolor(self) -> None:
        # state= is NOT a generic \apply channel: it was silently swallowed
        # (nobody reads apply_params["state"] — the cell stayed idle), so the
        # guard now rejects it and steers to \recolor, the documented
        # state-setter (§5.7). hunt-param-guard.md A3.
        arr = ArrayPrimitive("a", {"values": [1, 2, 3]})
        with pytest.raises(AnimationError) as ei:
            _validate_apply_spec(arr, {"state": "current"})
        assert ei.value.code == "E1105"
        assert "recolor" in str(ei.value).lower()

    def test_unknown_series_on_metricplot_raises_e1105(self) -> None:
        # MetricPlot's valid keys are its series names (dynamic per instance).
        mp = MetricPlot("plot", {"series": ["phi", "cost"]})
        with pytest.raises(AnimationError) as ei:
            _validate_apply_spec(mp, {"fee": 3.0})
        assert ei.value.code == "E1105"

    def test_unknown_var_on_variablewatch_raises_e1105(self) -> None:
        vw = VariableWatch("w", {"names": ["i", "j"]})
        with pytest.raises(AnimationError) as ei:
            _validate_apply_spec(vw, {"k": 1})
        assert ei.value.code == "E1105"


# ---------------------------------------------------------------------------
# HAZARD 1 — false-positive guard: real structural keys must NOT raise
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestApplyParamFalsePositiveGuard:
    """Every representative structural op a primitive documents must survive
    the guard (the full golden suite is the exhaustive proof; this samples
    broadly for a fast signal)."""

    @pytest.mark.parametrize(
        "factory, spec",
        [
            (_standard_tree, {"reparent": {"node": 2, "parent": 3}}),
            (_standard_tree, {"add_node": {"id": "x", "parent": "1"}}),
            (_standard_tree, {"remove_node": 5}),
            (_standard_tree, {"add_link": {"from": "2", "to": "3"}}),
            (_standard_tree, {"remove_link": {"from": "2", "to": "3"}}),
            (lambda: ArrayPrimitive("a", {"values": [1, 2, 3, 4]}), {"insert": {"at": 0, "value": 9}}),
            (lambda: ArrayPrimitive("a", {"values": [1, 2, 3, 4]}), {"remove": 1}),
            (lambda: ArrayPrimitive("a", {"values": [1, 2, 3, 4]}), {"reorder": [3, 0, 1, 2]}),
            (lambda: Graph("g", {"nodes": ["a", "b"], "edges": [("a", "b")]}), {"add_edge": {"from": "a", "to": "b"}}),
            (lambda: Graph("g", {"nodes": ["a", "b"], "edges": [("a", "b")]}), {"remove_edge": {"from": "a", "to": "b"}}),
            (lambda: Graph("g", {"nodes": ["a", "b"], "edges": [("a", "b")]}), {"set_weight": {"from": "a", "to": "b", "value": 3}}),
            (lambda: Bar("h", {"data": [1, 2, 3]}), {"value": 5}),
            (lambda: TraceTable("t", {"columns": ["i", "j"]}), {"row": [1, 2]}),
            (lambda: Equation("E", {"tex": "x^2"}), {"tex": "y=1"}),
            (lambda: Equation("E", {"tex": "x^2"}), {"lines": ["a", "b"]}),
            (lambda: Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10]}), {"rotate_point": {"index": 0, "angle": 15}}),
            (lambda: Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10]}), {"add_point": {"x": 1, "y": 2}}),
            (lambda: Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10]}), {"move_segment": {"index": 0}}),
            (lambda: Forest("f", {"nodes": [0, 1, 2, 3]}), {"union": {"a": 0, "b": 1}}),
            (lambda: Stack("s", {}), {"push": "x"}),
            (lambda: Stack("s", {}), {"pop": 1}),
            (lambda: Queue("q", {"capacity": 4}), {"enqueue": 5}),
            (lambda: Queue("q", {"capacity": 4}), {"dequeue": True}),
            # Deque-only verbs are ACCEPTED by the guard on a plain Queue so
            # apply_command can raise the specific E1444 (not E1105).
            (lambda: Queue("q", {"capacity": 4}), {"push_front": 1}),
            (lambda: Deque("d", {"capacity": 4}), {"push_front": 1}),
            (lambda: Deque("d", {"capacity": 4}), {"pop_back": 1}),
            (lambda: LinkedList("l", {"data": [1, 2, 3]}), {"insert": {"index": 0, "value": 9}}),
            (lambda: LinkedList("l", {"data": [1, 2, 3]}), {"remove": 1}),
            (lambda: MetricPlot("plot", {"series": ["phi", "cost"]}), {"phi": 3.2}),
            (lambda: VariableWatch("w", {"names": ["i", "j"]}), {"i": 0}),
            (lambda: HashMap("hm", {"capacity": 4}), {"value": "v"}),
            (lambda: Hypercube("L", {"bits": 3}), {"value": "v"}),
        ],
    )
    def test_structural_key_does_not_raise(self, factory, spec) -> None:
        _validate_apply_spec(factory(), spec)  # must not raise


# ---------------------------------------------------------------------------
# HAZARD 2 — E1104: Tree/Forest pairs-form nodes= is rejected, not mangled
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPairsNodesE1104:
    def test_tree_pairs_form_nodes_raises_e1104(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Tree(
                "t",
                {"root": "r", "nodes": [["r", "5"], ["c", "3"]], "edges": [["r", "c"]]},
            )
        assert ei.value.code == "E1104"
        msg = str(ei.value)
        # The hint steers to scalar ids + the per-node value recipe.
        assert "scalar" in msg.lower()
        assert "value=" in msg

    def test_tree_scalar_nodes_unchanged(self) -> None:
        # The ordinary scalar-ids form still builds fine.
        t = Tree("t", {"root": "r", "nodes": ["r", "c"], "edges": [("r", "c")]})
        assert "c" in t.nodes

    def test_forest_pairs_form_nodes_raises_e1104(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Forest("f", {"nodes": [["a", "1"], ["b", "2"]]})
        assert ei.value.code == "E1104"

    def test_forest_scalar_nodes_unchanged(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2, 3]})
        assert f.node_ids == ["0", "1", "2", "3"]


# ---------------------------------------------------------------------------
# HAZARD 3 — E1115 prefix on invalid-selector set_value/set_state soft-drops
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInvalidSelectorE1115Prefix:
    def test_set_value_invalid_selector_warns_with_e1115(self) -> None:
        t = _standard_tree()
        with pytest.warns(UserWarning, match=r"\[E1115\]"):
            t.set_value("node[99]", "ghost")

    def test_set_state_invalid_selector_warns_with_e1115(self) -> None:
        t = _standard_tree()
        with pytest.warns(UserWarning, match=r"\[E1115\]"):
            t.set_state("node[99]", "current")

    def test_set_label_invalid_selector_warns_with_e1115(self) -> None:
        t = _standard_tree()
        with pytest.warns(UserWarning, match=r"\[E1115\]"):
            t.set_label("node[99]", "ghost")


# ---------------------------------------------------------------------------
# JudgeZone repros — verbatim, now loud at build
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJudgeZoneRepros:
    def test_repro1_tree_pairs_nodes_raises_at_build(self) -> None:
        # \shape{t}{Tree}{root="r", nodes=[["r","5"],["c","3"]], edges=[["r","c"]]}
        with pytest.raises(AnimationError) as ei:
            Tree(
                "t",
                {"root": "r", "nodes": [["r", "5"], ["c", "3"]], "edges": [["r", "c"]]},
            )
        assert ei.value.code == "E1104"

    def test_repro2_segtree_lazy_apply_raises_e1105(self) -> None:
        # A segtree \apply with an unknown structural key renders loud, not clean.
        body = (
            '\\shape{st}{Tree}{kind=segtree, data=[1,2,3,4]}\n'
            "\\step\n"
            '\\apply{st.node["[0,3]"]}{lazy="+3"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1105"
