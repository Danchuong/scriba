"""DECORATE design, verb 4 — lift the ``\\trace`` restriction for Graph/Tree.

``\\trace`` was ``supports_trace``-gated to Array/Grid/DPTable/NumberLine;
Graph and Tree raised E1118 (investigations/teaching-marker-verbs.md GAP-2).
Both already expose ``resolve_annotation_point`` at the node centre, so the
same ``emit_traces_under`` decoration threads a polyline through the nodes —
"follow the edges". ``cells=`` now accepts node ids (strings) or indices. The
gate stays intact for genuinely non-trace primitives (Stack, Queue, ...).
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.scene import SceneState
from scriba.core.errors import ScribaError

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


def _run(src: str) -> None:
    ir = SceneParser().parse(src)
    sc = SceneState()
    sc.apply_prelude(ir.shapes, ir.prelude_commands, ir.prelude_compute)
    for f in ir.frames:
        sc.apply_frame(f)


def _render(source: str, tmp_path: Path) -> str:
    tex_path = tmp_path / "in.tex"
    tex_path.write_text(source, encoding="utf-8")
    out_path = tmp_path / "out.html"
    render_file(tex_path, out_path)
    return out_path.read_text(encoding="utf-8")


class TestGrammarStringNodes:
    def test_string_node_cells_parse(self) -> None:
        ir = SceneParser().parse(
            '\\shape{g}{Graph}{nodes=["A","B","C"], edges=[("A","B"),("B","C")]}\n'
            "\\step\n"
            '\\trace{g}{cells=["A","B","C"], color=good}\n'
        )
        cmds = [
            c
            for f in ir.frames
            for c in f.commands
            if type(c).__name__ == "TraceCommand"
        ]
        assert cmds and cmds[0].cells == ("A", "B", "C")

    def test_int_node_cells_still_parse(self) -> None:
        # The existing int branch must be untouched (grid traces unaffected).
        ir = SceneParser().parse(
            "\\shape{t}{Tree}{root=0, nodes=[0,1,2], edges=[(0,1),(0,2)]}\n"
            "\\step\n"
            "\\trace{t}{cells=[0, 1], color=path}\n"
        )
        cmds = [
            c
            for f in ir.frames
            for c in f.commands
            if type(c).__name__ == "TraceCommand"
        ]
        assert cmds and cmds[0].cells == (0, 1)


class TestLiftE1118:
    def test_trace_on_graph_no_e1118(self) -> None:
        _run(
            '\\shape{g}{Graph}{nodes=["A","B","C"], edges=[("A","B"),("B","C")]}\n'
            "\\step\n"
            '\\trace{g}{cells=["A","B","C"], color=good}\n'
        )  # must not raise E1118

    def test_trace_on_tree_no_e1118(self) -> None:
        _run(
            "\\shape{t}{Tree}{root=1, nodes=[1,2,3], edges=[(1,2),(1,3)]}\n"
            "\\step\n"
            "\\trace{t}{cells=[1, 2], color=path}\n"
        )  # must not raise E1118

    def test_trace_on_stack_still_e1118(self) -> None:
        with pytest.raises(ScribaError) as ei:
            _run(
                '\\shape{s}{Stack}{items=["a","b"]}\n'
                "\\step\n"
                "\\trace{s}{cells=[0,1], color=good}\n"
            )
        assert "E1118" in str(ei.value)


class TestGraphTraceEmit:
    def test_graph_trace_draws_polyline(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="graph trace"]\n'
            '\\shape{g}{Graph}{nodes=["A","B","C"], edges=[("A","B"),("B","C")]}\n'
            "\\step\n"
            '\\trace{g}{cells=["A","B","C"], color=good, label="BFS"}\n'
            "\\end{animation}\n"
        )
        html_out = _render(source, tmp_path)
        # The trace rides the shipped trace annotation key + a polyline path.
        assert 'data-annotation="g.trace[t1]-solo"' in html_out
        assert "<path" in html_out

    def test_tree_trace_draws_polyline(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="tree trace"]\n'
            "\\shape{t}{Tree}{root=1, nodes=[1,2,3], edges=[(1,2),(1,3)]}\n"
            "\\step\n"
            "\\trace{t}{cells=[1, 2], color=path}\n"
            "\\end{animation}\n"
        )
        html_out = _render(source, tmp_path)
        assert 'data-annotation="t.trace[t1]-solo"' in html_out

    def test_graph_trace_unknown_node_soft_drops(self) -> None:
        from scriba.animation.primitives.graph import Graph

        g = Graph(
            "g",
            {"nodes": ["A", "B", "C"], "edges": [("A", "B"), ("B", "C")]},
        )
        g.set_traces(
            [{"id": "t1", "cells": ["A", "ZZ"], "color": "good"}]
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            svg = g.emit_svg()
        assert svg  # render did not blank
        # Unknown node soft-drops the whole trace (E1115), no polyline.
        assert "g.trace[t1]-solo" not in svg
        assert any("E1115" in str(x.message) for x in w)
