"""Residual #3 of report #6 (audit-node-targeting-class.md finding 3): a MATH
value renders as ``<foreignObject data-role="value">``, so a text-only throb
selector (``text[data-role="value"]``) missed it and the 100ms scale-bounce
animated the NAME node instead. The runtime now resolves the throb node
element-agnostically (``[data-role="value"]``, any element), and the renderer
tags the math foreignObject too.
"""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

from render import render_file


def _widget_js() -> str:
    return (files("scriba.animation.static") / "scriba.js").read_text()


class TestMathValueThrobNode:
    def test_math_value_foreignObject_carries_value_role(self, tmp_path: Path) -> None:
        # a math value renders as a KaTeX foreignObject — this needs the full
        # render pipeline (render_inline_tex), not a bare emit_svg().
        src = tmp_path / "m.tex"
        src.write_text(
            '\\begin{animation}[id="t", label="x"]\n'
            '\\shape{w}{VariableWatch}{names=["s"]}\n'
            '\\apply{w.var[s]}{value="$x^2$"}\n'
            "\\step\n\\narrate{m.}\n"
            "\\end{animation}\n"
        )
        out = tmp_path / "m.html"
        render_file(src, out)
        h = out.read_text()
        g = re.search(r'data-target="w\.var\[s\]".{0,700}', h, re.S)
        assert g, "var group missing"
        # the math value is a foreignObject, tagged data-role=value (the throb
        # node the element-agnostic selector must resolve).
        assert re.search(r'<foreignObject[^>]*data-role="value"', g.group(0))
        # the name is a plain text, tagged data-role=name (never the throb node).
        assert re.search(r'<text[^>]*data-role="name"', g.group(0))

    def test_runtime_throb_node_is_element_agnostic(self) -> None:
        js = _widget_js()
        # the value node is selected without a `text` prefix (matches <text> AND
        # <foreignObject>), and the throb node (vt) rides that tagged node.
        assert "querySelector('[data-role=\"value\"]')" in js
        assert "vt=vnode" in js
        # the old text-only value selector is gone.
        assert 'querySelector(\'text[data-role="value"]\')' not in js
