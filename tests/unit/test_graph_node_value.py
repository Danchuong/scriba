r"""Graph renders a PER-NODE ``value=`` (Option-A of the value-flipback design).

``\apply{g.node[X]}{value=...}`` was E1105-rejected since 0.26.3 ("value= is
edge-scoped on Graph"). Six flagship graph examples (Dijkstra, BFS, Tarjan,
DSU, ...) hand-build a side Array/DPTable to carry a per-node number the graph
node could not hold. This closes that gap: the Graph node now renders the
applied value the way Tree/Forest already do — the value **overrides** the node
id text (``tree.py:1004`` / ``forest.py:577``), riding the existing
``value_change`` transition with no new motion kind.

The A1 **override** model: the value REPLACES the node id (compose ``"A:7"`` to
keep the name visible). Edges keep their documented weight-label ``value=``.
Stack ``item[i]`` / NumberLine ``tick[i]`` / CodePanel ``line[i]`` STILL reject
``value=`` with E1105 — this change touches only Graph nodes.

See ``investigations/research-graph-node-value.md`` and
``investigations/design-value-flipback.md``.
"""
from __future__ import annotations

import re

import pytest

from scriba.animation.differ import compute_transitions
from scriba.animation.emitter import FrameData
from scriba.animation.errors import AnimationError
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.codepanel import CodePanel
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.animation.primitives.stack import Stack
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext


# ---------------------------------------------------------------------------
# Helpers (mirrors test_value_flipback_guard / test_value_change_value_node)
# ---------------------------------------------------------------------------


def _ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        metadata={"output_mode": "interactive"},
        warnings_collector=None,
    )


def _render(body: str) -> str:
    """Drive the full animation pipeline (scene -> prescan -> diff -> emit)."""
    renderer = AnimationRenderer()
    source = '\\begin{animation}[id="graph-node-value"]\n' + body + "\n\\end{animation}"
    blocks = renderer.detect(source)
    assert len(blocks) == 1
    return renderer.render_block(blocks[0], _ctx()).html


def _group_at(svg: str, target: str, i: int) -> str:
    """Extract the balanced ``<g …> … </g>`` subtree containing offset *i*."""
    start = svg.rfind("<g", 0, i)
    depth, j, n = 0, start, len(svg)
    while j < n:
        if svg.startswith("<g", j):
            depth += 1
            j += 2
        elif svg.startswith("</g>", j):
            depth -= 1
            j += 4
            if depth == 0:
                return svg[start:j]
        else:
            j += 1
    return svg[start:]


def _group(svg: str, target: str) -> str:
    """The FIRST ``<g data-target="target"> … </g>`` subtree (first frame)."""
    needle = f'data-target="{target}"'
    i = svg.find(needle)
    assert i != -1, f"no data-target={target!r} in svg"
    return _group_at(svg, target, i)


def _group_last(svg: str, target: str) -> str:
    """The LAST ``<g data-target="target"> … </g>`` subtree (final frame).

    Each ``\\step`` emits its own fs-snap SVG, so a persisted node value must be
    read from the last frame — that snapshot is what the flip-back reverted.
    """
    needle = f'data-target="{target}"'
    i = svg.rfind(needle)
    assert i != -1, f"no data-target={target!r} in svg"
    return _group_at(svg, target, i)


def _texts(group: str) -> list[str]:
    """All ``<text>`` inner strings in document order (tspans stripped)."""
    return [
        re.sub(r"<[^>]+>", "", m.group(1))
        for m in re.finditer(r"<text\b[^>]*>(.*?)</text>", group, re.DOTALL)
    ]


def _frame(shape_states: dict) -> FrameData:
    return FrameData(
        step_number=1,
        total_frames=2,
        narration_html="",
        shape_states=shape_states,
        annotations=[],
    )


def _graph() -> Graph:
    return Graph("G", {"nodes": ["A", "B", "C"], "edges": [("A", "B"), ("B", "C")]})


# ---------------------------------------------------------------------------
# renders_value capability — Graph node now honors value= (like the edge)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGraphRendersNodeValue:
    def test_node_and_edge_both_render_value(self) -> None:
        g = _graph()
        # Node flips reject -> render (this feature); edge stays rendering.
        assert g.renders_value("node[A]") is True
        assert g.renders_value("edge[(A,B)]") is True

    def test_non_node_non_edge_suffix_does_not_render(self) -> None:
        # The gate stays tight: only node[/edge[ carry a value slot on Graph.
        g = _graph()
        assert g.renders_value("all") is False
        assert g.renders_value("cell[0]") is False


# ---------------------------------------------------------------------------
# Override render (primitive level) — mirrors Tree/Forest exactly
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGraphNodeValueOverride:
    def test_value_overrides_node_id_text(self) -> None:
        # A1 model: the applied value REPLACES the "A" id text inside the circle.
        g = _graph()
        g.set_value("node[A]", "7")
        grp = _group(g.emit_svg(), "G.node[A]")
        assert _texts(grp) == ["7"], "node value= must render as the node's text"

    def test_untouched_node_keeps_id_text(self) -> None:
        # Byte-identity guard: a node with NO value renders str(node_id) as before
        # (get_value unset -> the id fallback path is unchanged).
        g = _graph()
        g.set_value("node[A]", "7")  # value on A must not bleed onto B
        grp_b = _group(g.emit_svg(), "G.node[B]")
        assert _texts(grp_b) == ["B"]

    def test_compose_name_and_value(self) -> None:
        # Where the letter must stay, the author composes it (documented idiom).
        g = _graph()
        g.set_value("node[A]", "A:7")
        grp = _group(g.emit_svg(), "G.node[A]")
        assert _texts(grp) == ["A:7"]

    def test_plain_graph_svg_unchanged_without_any_value(self) -> None:
        # No value applied anywhere -> emit is byte-identical to a fresh render
        # of the same graph (the override read is a pure no-op when unset).
        assert _graph().emit_svg() == _graph().emit_svg()
        grp = _group(_graph().emit_svg(), "G.node[A]")
        assert _texts(grp) == ["A"]


# ---------------------------------------------------------------------------
# Pipeline — \apply{g.node[X]}{value=} renders instead of raising E1105
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGraphNodeValuePipeline:
    def test_apply_node_value_renders_not_e1105(self) -> None:
        body = (
            '\\shape{g}{Graph}{nodes=["A","B"], edges=[("A","B")]}\n'
            "\\step\n"
            '\\apply{g.node[A]}{value="7"}\n'
        )
        html = _render(body)  # must NOT raise E1105
        grp = _group(html, "g.node[A]")
        assert _texts(grp) == ["7"]

    def test_flipback_repro_node_value_across_two_steps(self) -> None:
        # The Dijkstra-style repro that caused the 0.26.5 flip-back: a node value
        # applied in one step and carried into the next. Server SVG now renders
        # it (agrees with the runtime stamp) so there is no revert.
        body = (
            '\\shape{g}{Graph}{nodes=["A","B","C"], '
            'edges=[("A","B"),("B","C")]}\n'
            "\\step\n"
            '\\apply{g.node[A]}{value="0"}\n'
            "\\step\n"
            '\\apply{g.node[B]}{value="4"}\n'
            '\\recolor{g.node[A]}{state=good}\n'
        )
        html = _render(body)  # must NOT raise
        # The final fs-snap frame (what the flip-back reverted) renders both
        # distances co-located on their nodes: A's value persisted from step 1,
        # B's applied in step 2. Server SVG now agrees with the runtime stamp.
        assert _texts(_group_last(html, "g.node[A]")) == ["0"]
        assert _texts(_group_last(html, "g.node[B]")) == ["4"]

    def test_graph_edge_value_still_renders(self) -> None:
        # Regression: the documented edge weight-label value= is untouched.
        body = (
            '\\shape{g}{Graph}{nodes=["A","B"], edges=[("A","B")], '
            "show_weights=true}\n"
            "\\step\n"
            '\\apply{g.edge[(A,B)]}{value="3/10"}\n'
        )
        html = _render(body)
        assert "3/10" in html


# ---------------------------------------------------------------------------
# Manifest honesty — the value_change for a node is now backed by a render
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGraphNodeValueManifestHonest:
    def test_value_change_emitted_and_server_renders_it(self) -> None:
        prev = _frame({"G": {"G.node[A]": {"state": "idle"}}})
        curr = _frame({"G": {"G.node[A]": {"state": "idle", "value": "7"}}})
        manifest = compute_transitions(prev, curr)
        vc = [
            t
            for t in manifest.transitions
            if t.kind == "value_change" and t.target == "G.node[A]"
        ]
        assert len(vc) == 1, "differ must emit a value_change for the node"
        assert vc[0].to_val == "7"
        # And the server actually renders that value (honest, not a flip-back):
        g = _graph()
        g.set_value("node[A]", "7")
        assert _texts(_group(g.emit_svg(), "G.node[A]")) == ["7"]


# ---------------------------------------------------------------------------
# The fence stays intact — the OTHER value-less parts still reject (E1105)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOtherValueLessPartsStillReject:
    def test_base_default_still_true(self) -> None:
        # Did not loosen (or tighten) the base default: value-honoring majority.
        arr = ArrayPrimitive("a", {"values": [1, 2, 3]})
        assert arr.renders_value("cell[0]") is True

    def test_stack_item_still_false_and_raises(self) -> None:
        s = Stack("s", {"items": ["A", "B"]})
        assert s.renders_value("item[0]") is False
        body = (
            '\\shape{s}{Stack}{items=["A","B"]}\n'
            "\\step\n"
            '\\apply{s.item[0]}{value="ZZZ"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1105"

    def test_numberline_tick_still_false_and_raises(self) -> None:
        nl = NumberLinePrimitive("nl", {"domain": [0, 6], "ticks": 7})
        assert nl.renders_value("tick[2]") is False
        body = (
            "\\shape{nl}{NumberLine}{domain=[0,6], ticks=7}\n"
            "\\step\n"
            '\\apply{nl.tick[2]}{value="9"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1105"

    def test_codepanel_line_still_false_and_raises(self) -> None:
        c = CodePanel("c", {"lines": ["alpha", "beta"]})
        assert c.renders_value("line[1]") is False
        body = (
            '\\shape{c}{CodePanel}{lines=["alpha","beta"]}\n'
            "\\step\n"
            '\\apply{c.line[1]}{value="ZZZ"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1105"
