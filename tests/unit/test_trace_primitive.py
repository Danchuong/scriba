"""P3 of the unified decoration plan: ``\\trace`` — an arrow that follows a
sequence of cells (R-37; investigations/feat-trace-primitive.md,
unified-{decoration-model,conflict-audit,spec}.md).

Emit contract: one ``<g data-annotation="{shape}.trace[{id}]-solo">``
containing a rounded-join ``<path>`` through the cell centers + a
``<polygon>`` arrowhead, painted BEFORE the cell loop (under the digits,
which keep their global paint-order halo). The shipped runtime's
``annotation_add`` handler draws it on via stroke-dashoffset with zero JS
changes — structure-driven."""

from __future__ import annotations

import re

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.grid import GridPrimitive


def _parse(body: str, shape: str = "Grid", args: str = "rows=3, cols=3, data=[[1,2,3],[4,5,6],[7,8,9]]"):
    return SceneParser().parse(
        f"\\shape{{g}}{{{shape}}}{{{args}}}\n\\step\n" + body
    )


class TestGrammar:
    def test_trace_parses(self) -> None:
        ir = _parse('\\trace{g}{cells=[[2,0],[2,1],[2,2],[1,2]], color=good, label="lớp lẻ"}\n')
        cmds = [c for f in ir.frames for c in f.commands
                if type(c).__name__ == "TraceCommand"]
        assert len(cmds) == 1
        assert cmds[0].cells == ((2, 0), (2, 1), (2, 2), (1, 2))
        assert cmds[0].color == "good"

    def test_trace_1d_cells(self) -> None:
        ir = _parse(
            "\\trace{a}{cells=[0,1,2]}\n",
        ).frames  # shape mismatch fine at parse level; scene validates
        cmds = [c for f in ir for c in f.commands
                if type(c).__name__ == "TraceCommand"]
        assert cmds[0].cells == (0, 1, 2)

    def test_trace_inside_foreach_parses(self) -> None:
        # audit C6: the SECOND dispatch site
        src = (
            "\\shape{g}{Grid}{rows=2, cols=2, data=[[1,2],[3,4]]}\n"
            "\\step\n"
            "\\foreach{i}{0,1}\n"
            "\\trace{g}{cells=[[0,0],[1,1]]}\n"
            "\\endforeach\n"
        )
        ir = SceneParser().parse(src)
        assert ir is not None

    def test_too_few_points_e1491(self) -> None:
        from scriba.core.errors import ScribaError

        with pytest.raises(ScribaError) as ei:
            _parse("\\trace{g}{cells=[[0,0]]}\n")
        assert "E1491" in str(ei.value)


class TestEmit:
    def _grid_traced(self, **kv) -> str:
        g = GridPrimitive(
            "g", {"rows": 3, "cols": 3, "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        )
        g.set_traces([{"id": "t0", "cells": [[2, 0], [2, 1], [2, 2], [1, 2]],
                       "color": "good", **kv}])
        return g.emit_svg()

    def test_structure_group_path_polygon(self) -> None:
        svg = self._grid_traced()
        m = re.search(
            r'<g class="scriba-annotation scriba-annotation-good"'
            r'[^>]*data-annotation="g\.trace\[t0\]-solo"[^>]*>(.*?)</g>',
            svg, re.S,
        )
        assert m, "trace group missing"
        body = m.group(1)
        assert re.search(r'<path [^>]*stroke-linejoin="round"', body)
        assert 'fill="none"' in body
        assert "<polygon" in body  # arrowhead

    def test_painted_above_cells_below_annotations(self) -> None:
        # a filled cell body would swallow an under-stroke, so traces sit
        # above the cells; digits stay legible via the global halo. Pills
        # and arrows still paint on top of traces.
        g = GridPrimitive(
            "g", {"rows": 3, "cols": 3, "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        )
        g.set_traces([{"id": "t0", "cells": [[2, 0], [2, 2]], "color": "good"}])
        g.set_annotations([{"target": "g.cell[0][0]", "label": "x"}])
        svg = g.emit_svg()
        assert svg.index("trace[t0]") > svg.index('data-target="g.cell[2][2]"')
        assert svg.index("trace[t0]") < svg.index("-position-above")

    def test_path_through_cell_centers_dynamic_pitch(self) -> None:
        g = GridPrimitive(
            "g", {"rows": 3, "cols": 3, "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        )
        g.set_traces([{"id": "t0", "cells": [[2, 0], [2, 2]], "color": "good"}])
        svg = g.emit_svg()
        c0 = g.resolve_annotation_point("g.cell[2][0]")
        m = re.search(r'data-annotation="g\.trace\[t0\]-solo".*?<path d="M([\d.]+),([\d.]+)', svg, re.S)
        assert m
        assert abs(float(m.group(1)) - c0[0]) < 0.6
        assert abs(float(m.group(2)) - c0[1]) < 0.6

    def test_oob_cell_soft_dropped(self) -> None:
        g = GridPrimitive("g", {"rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]})
        g.set_traces([{"id": "t0", "cells": [[0, 0], [5, 5]], "color": "good"}])
        svg = g.emit_svg()
        assert "trace[" not in svg  # unresolvable point -> whole trace dropped

    def test_dptable_1d_trace(self) -> None:
        dp = DPTablePrimitive("dp", {"n": 4, "data": ["1", "2", "3", "4"]})
        dp.set_traces([{"id": "t0", "cells": [0, 1, 2], "color": "info"}])
        assert "dp.trace[t0]-solo" in dp.emit_svg()


class TestDiffer:
    def test_new_trace_emits_annotation_add(self) -> None:
        from scriba.animation.differ import compute_transitions
        from scriba.animation.emitter import FrameData

        def _fd(traces):
            return FrameData(
                step_number=0, total_frames=2, narration_html="",
                shape_states={}, annotations=[], traces=traces,
            )

        prev = _fd([])
        curr = _fd([{"id": "t0", "target": "g",
                     "cells": [[0, 0], [1, 1]], "color": "good"}])
        trs = compute_transitions(prev, curr).transitions
        adds = [t for t in trs if t.kind == "annotation_add"
                and "trace[t0]" in t.target]
        assert len(adds) == 1
