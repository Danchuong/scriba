"""Math foreignObject boxes: match neighbouring plain-text sizing.

The CSS that sizes plain SVG ``<text>`` uses ``> text`` child selectors,
which never reach a ``<foreignObject>``'s XHTML div — so a math cell value
rendered at the browser default (~16px) sat next to 14px plain values.
Every FO call site now passes the explicit ``font_size`` its plain twin
gets from CSS, node labels get overflow parity with plain node text, and
axis/point labels get real measured boxes instead of the 80x30 default.
"""

from __future__ import annotations

import re

from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.metricplot import MetricPlot
from scriba.animation.primitives.numberline import NumberLinePrimitive


def _fake_tex(fragment: str) -> str:
    return f'<span class="fake-katex">{fragment.strip("$")}</span>'


def _fo_styles(svg: str) -> list[str]:
    return re.findall(r"<foreignObject[^>]*>\s*<div[^>]*style=\"([^\"]*)\"", svg)


class TestFontSizeParity:
    def test_grid_cell_math_value_is_14px(self) -> None:
        g = GridPrimitive("g", {"rows": 2, "cols": 2, "data": [["$x$", 1], [2, 3]]})
        svg = g.emit_svg(render_inline_tex=_fake_tex)
        styles = [st for st in _fo_styles(svg) if "fake-katex" not in st]
        assert styles, "expected a math cell foreignObject"
        assert any("font-size:14px" in st for st in styles), styles

    def test_numberline_math_tick_is_10px(self) -> None:
        nl = NumberLinePrimitive(
            "n", {"domain": [0, 4], "ticks": 3, "labels": ["0", "$k$", "4"]}
        )
        svg = nl.emit_svg(render_inline_tex=_fake_tex)
        assert any("font-size:10px" in st for st in _fo_styles(svg)), _fo_styles(svg)


class TestNodeOverflowParity:
    def test_graph_math_node_label_overflows_like_plain(self) -> None:
        g = Graph(
            "G", {"nodes": ["$x^{2}+y$", "B"], "edges": [("$x^{2}+y$", "B")]}
        )
        svg = g.emit_svg(render_inline_tex=_fake_tex)
        m = re.search(r'<foreignObject[^>]*class="[^"]*"[^>]*>', svg) or re.search(
            r"<foreignObject[^>]*>", svg
        )
        assert m, "expected node foreignObject"
        styles = _fo_styles(svg)
        assert styles and all("overflow:hidden" not in st for st in styles), styles
        assert any("overflow:visible" in st for st in styles), styles


class TestRealAxisBoxes:
    def test_metricplot_long_math_xlabel_gets_measured_box(self) -> None:
        mp = MetricPlot(
            "m",
            {
                "series": ["cost"],
                "xlabel": "$t_{elapsed}$ theo giây trong toàn phiên",
            },
        )
        svg = mp.emit_svg(render_inline_tex=_fake_tex)
        widths = [
            float(w)
            for w in re.findall(r'<foreignObject[^>]*width="([\d.]+)"', svg)
        ]
        assert widths and max(widths) > 80, widths


class TestCaptionAnchorInline:
    def test_single_line_plain_caption_carries_inline_anchor(self) -> None:
        g = GridPrimitive("g", {"rows": 2, "cols": 2, "label": "nhãn ngắn"})
        svg = g.emit_svg()
        m = re.search(r'<text class="scriba-primitive-label"[^>]*>', svg)
        assert m and "text-anchor:middle" in m.group(0), m and m.group(0)


class TestCopyPasteSpaces:
    def test_wrapped_caption_lines_keep_trailing_space(self) -> None:
        g = GridPrimitive(
            "g",
            {"rows": 2, "cols": 2,
             "label": "một chú thích thuần văn bản rất dài buộc phải xuống dòng nhiều lần cho chắc"},
        )
        svg = g.emit_svg()
        spans = re.findall(r"<tspan[^>]*>(.*?)</tspan>", svg)
        assert len(spans) >= 2
        assert all(sp.endswith(" ") for sp in spans[:-1]), spans
        assert not spans[-1].endswith(" ")
