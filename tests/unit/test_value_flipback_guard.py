r"""E1105 gate for ``value=`` on primitives with no per-part value display.

Three primitives accept the universally-generic ``value=`` ``\apply`` key but
their ``emit_svg`` renders no value on the targeted part: **Stack** ``item[i]``,
**NumberLine** ``tick[i]``, **CodePanel** ``line[i]``. The scene layer recorded
the value unconditionally, the differ turned the delta into a real
``value_change`` transition, and the runtime stamped it into a ``<text>`` —
then the fs-snap frame (which never rendered it) reverted it: a flip-back
flash, and a silent no-op on the author's intent.

The fix rejects ``value=`` on those parts at build time (**E1105**) via the
``renders_value(suffix)`` primitive capability, checked in the pre-differ value
pass. Honoring primitives (Array, Tree, LinkedList, Graph *nodes* and *edges*,
...) keep ``value=`` working because they render it. Graph *nodes* joined the
honoring set via the per-node value override (see
``tests/unit/test_graph_node_value.py`` and
``investigations/research-graph-node-value.md``).

See ``investigations/design-value-flipback.md``.
"""
from __future__ import annotations

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.codepanel import CodePanel
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.animation.primitives.stack import Stack
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext


def _ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        metadata={"output_mode": "interactive"},
        warnings_collector=None,
    )


def _render(body: str) -> str:
    """Drive the full animation pipeline (scene -> prescan -> diff -> emit)."""
    renderer = AnimationRenderer()
    source = '\\begin{animation}[id="flipback-test"]\n' + body + "\n\\end{animation}"
    blocks = renderer.detect(source)
    assert len(blocks) == 1
    return renderer.render_block(blocks[0], _ctx()).html


# ---------------------------------------------------------------------------
# Unit — the ``renders_value(suffix)`` capability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRendersValueCapability:
    def test_base_default_true(self) -> None:
        # A value-honoring primitive (Array) inherits the base default True.
        arr = ArrayPrimitive("a", {"values": [1, 2, 3]})
        assert arr.renders_value("cell[0]") is True

    def test_stack_item_false(self) -> None:
        s = Stack("s", {"items": ["A", "B"]})
        assert s.renders_value("item[0]") is False

    def test_numberline_tick_false(self) -> None:
        nl = NumberLinePrimitive("nl", {"domain": [0, 6], "ticks": 7})
        assert nl.renders_value("tick[2]") is False

    def test_codepanel_line_false(self) -> None:
        c = CodePanel("c", {"lines": ["alpha", "beta"]})
        assert c.renders_value("line[1]") is False

    def test_graph_node_and_edge_true(self) -> None:
        # value= renders on BOTH Graph nodes (per-node override) and edges
        # (weight label) — see tests/unit/test_graph_node_value.py.
        g = Graph("g", {"nodes": ["A", "B"], "edges": [("A", "B")]})
        assert g.renders_value("node[A]") is True
        assert g.renders_value("edge[(A,B)]") is True


# ---------------------------------------------------------------------------
# Integration — flip-back parts now raise E1105 at build (was: silent no-op)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValueFlipbackRaisesE1105:
    def test_stack_item_value_raises(self) -> None:
        body = (
            '\\shape{s}{Stack}{items=["A","B"]}\n'
            "\\step\n"
            '\\apply{s.item[0]}{value="ZZZ"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1105"
        assert "Stack" in str(ei.value)

    def test_numberline_tick_value_raises(self) -> None:
        body = (
            "\\shape{nl}{NumberLine}{domain=[0,6], ticks=7}\n"
            "\\step\n"
            '\\apply{nl.tick[2]}{value="9"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1105"

    def test_codepanel_line_value_raises(self) -> None:
        body = (
            '\\shape{c}{CodePanel}{lines=["alpha","beta"]}\n'
            "\\step\n"
            '\\apply{c.line[1]}{value="ZZZ"}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1105"

    def test_flipback_repro_errors_across_two_steps(self) -> None:
        # The literal flip-back repro: value applied to a Stack item, carried
        # across a second step. Pre-fix this rendered a dishonest value_change
        # that stamped then reverted; post-fix it errors at author time.
        body = (
            '\\shape{s}{Stack}{items=["A","B"]}\n'
            "\\step\n"
            '\\apply{s.item[0]}{value="X"}\n'
            "\\step\n"
            '\\highlight{s.item[1]}\n'
        )
        with pytest.raises(AnimationError) as ei:
            _render(body)
        assert ei.value.code == "E1105"


# ---------------------------------------------------------------------------
# Non-regression — honoring primitives still render value= (the fence)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHonoringPrimitivesUnaffected:
    def test_graph_edge_value_renders(self) -> None:
        body = (
            '\\shape{g}{Graph}{nodes=["A","B"], edges=[("A","B")], '
            "show_weights=true}\n"
            "\\step\n"
            '\\apply{g.edge[(A,B)]}{value="3/10"}\n'
        )
        html = _render(body)  # must NOT raise
        assert "3/10" in html

    def test_graph_node_value_renders(self) -> None:
        # Graph node value= moved from the reject set to the render set: it
        # overrides the node id text (per-node value, mirrors Tree/Forest).
        body = (
            '\\shape{g}{Graph}{nodes=["A","B"], edges=[("A","B")]}\n'
            "\\step\n"
            '\\apply{g.node[A]}{value="7"}\n'
        )
        html = _render(body)  # must NOT raise (was E1105 pre-feature)
        assert "7" in html

    def test_array_cell_value_renders(self) -> None:
        body = (
            "\\shape{a}{Array}{values=[1,2,3,4]}\n"
            "\\step\n"
            '\\apply{a.cell[0]}{value="ZZZ"}\n'
        )
        html = _render(body)
        assert "ZZZ" in html

    def test_linkedlist_node_value_renders(self) -> None:
        body = (
            "\\shape{ll}{LinkedList}{data=[1,2,3]}\n"
            "\\step\n"
            '\\apply{ll.node[0]}{value="ZZZ"}\n'
        )
        html = _render(body)
        assert "ZZZ" in html
