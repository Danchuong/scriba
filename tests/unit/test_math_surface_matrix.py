"""Every user-facing text surface renders ``$...$`` — pinned per surface.

The engine has supported math in cell values, watch names/values, tick
labels etc. all along, but the docs' canonical list omitted most of them
and none had a test — so the capability was undiscoverable and unguarded.
The one genuine gap was graph SPLIT edge labels (capacity/flow), whose
tspan styling path escaped ``$`` raw while the single-value path rendered
KaTeX; math weights now fall back to the single-value KaTeX path.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.codepanel import CodePanel
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.hashmap import HashMap
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.variablewatch import VariableWatch


def _fake_tex(fragment: str) -> str:
    return f'<span class="fake-katex">{fragment.strip("$")}</span>'


def _array_value():
    a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
    a.set_value("cell[1]", "$n^2$")
    return a


def _dptable_value():
    d = DPTablePrimitive("dp", {"n": 3})
    d.set_value("cell[1]", "$f(i)$")
    return d


def _watch_name_value():
    w = VariableWatch("w", {"names": ["$\\alpha$", "b"]})
    w.set_value("var[b]", "$b^2 - 4ac$")
    return w


def _matrix_row_col_labels():
    return MatrixPrimitive(
        "m",
        {"rows": 2, "cols": 2, "row_labels": ["$r_0$", "r1"], "col_labels": ["$c_0$", "c1"]},
    )


def _stack_item():
    return Stack("s", {"items": ["$x_1$", "y"]})


def _hashmap_entries():
    h = HashMap("h", {"capacity": 2})
    h.set_value("bucket[0]", "$k$: $v$")
    return h


def _plane2d_point_and_line():
    return Plane2D(
        "p",
        {
            "xrange": [-2, 2],
            "yrange": [-2, 2],
            "points": [{"x": 1, "y": 1, "label": "$P_1$"}],
            "lines": [{"slope": 1, "intercept": 0, "label": "$y=x$"}],
        },
    )


def _codepanel_caption():
    return CodePanel("c", {"source": "x = 1", "label": "$O(n)$ scan"})


def _graph_single_math_weight():
    # static weights are numeric; math arrives via \apply on the edge
    g = Graph("G", {"nodes": ["A", "B"], "edges": [("A", "B")]})
    g.set_value("edge[(A,B)]", "$w_1$")
    return g


def _graph_split_math_weight():
    # split_labels styling must yield to KaTeX when the weight carries math
    g = Graph(
        "G",
        {"nodes": ["A", "B"], "edges": [("A", "B")], "split_labels": True},
    )
    g.set_value("edge[(A,B)]", "$c$/$f$")
    return g


SURFACES = {
    "array_cell_value": _array_value,
    "dptable_cell_value": _dptable_value,
    "watch_name_and_value": _watch_name_value,
    "matrix_row_col_labels": _matrix_row_col_labels,
    "stack_item": _stack_item,
    "hashmap_entries": _hashmap_entries,
    "plane2d_point_and_line_labels": _plane2d_point_and_line,
    "codepanel_caption": _codepanel_caption,
    "graph_single_math_weight": _graph_single_math_weight,
    "graph_split_math_weight": _graph_split_math_weight,
}


@pytest.mark.parametrize("surface", SURFACES, ids=list(SURFACES))
def test_surface_renders_math(surface: str) -> None:
    prim = SURFACES[surface]()
    svg = prim.emit_svg(render_inline_tex=_fake_tex)
    assert "fake-katex" in svg, f"{surface}: $...$ did not reach KaTeX"


def test_codepanel_code_lines_stay_verbatim() -> None:
    cp = CodePanel("c", {"source": 'price = "$100"'})
    svg = cp.emit_svg(render_inline_tex=_fake_tex)
    assert "fake-katex" not in svg  # code is verbatim by design
    assert "$100" in svg
