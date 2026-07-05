"""``\\trace`` on a primitive that cannot draw traces must be LOUD (E1118),
not a silent no-op.

hunt-selectors BUG 2: \\trace is only wired into Array/Grid/DPTable/
NumberLine (they call emit_traces_under). On every other primitive —
Deque, Forest, Matrix, Stack, HashMap, Plane2D, LinkedList, Graph, Tree —
\\trace rendered "success" with zero output and zero warning, so an author
could not tell it did nothing.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.scene import SceneState
from scriba.core.errors import ScribaError


def _run(src: str) -> None:
    ir = SceneParser().parse(src)
    sc = SceneState()
    sc.apply_prelude(ir.shapes, ir.prelude_commands, ir.prelude_compute)
    for f in ir.frames:
        sc.apply_frame(f)


class TestTraceLoudOnUnsupported:
    @pytest.mark.parametrize("shape_decl,shape", [
        ("\\shape{d}{Deque}{capacity=6, data=[3,1,4]}", "d"),
        ("\\shape{f}{Forest}{nodes=[0,1,2,3], edges=[(0,1)]}", "f"),
        ("\\shape{m}{Matrix}{rows=2, cols=2, data=[[1,2],[3,4]]}", "m"),
        ("\\shape{s}{Stack}{items=[\"a\",\"b\"]}", "s"),
    ])
    def test_trace_unsupported_raises_e1118(self, shape_decl, shape) -> None:
        src = (
            f"{shape_decl}\n\\step\n"
            f"\\trace{{{shape}}}{{cells=[0,1], color=good}}\n"
        )
        with pytest.raises(ScribaError) as ei:
            _run(src)
        assert "E1118" in str(ei.value), str(ei.value)

    def test_trace_still_works_on_grid(self) -> None:
        # the supported path must not regress
        src = (
            "\\shape{g}{Grid}{rows=2, cols=3, data=[[1,2,3],[4,5,6]]}\n"
            "\\step\n"
            "\\trace{g}{cells=[[0,0],[0,1]], color=good}\n"
        )
        _run(src)  # no raise
