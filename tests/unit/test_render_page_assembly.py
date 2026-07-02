"""render.py page assembly: TeX regions get their wrapper and their CSS.

Found by a 375px-viewport sweep: the page template dropped ``{body}``
straight into ``<body>`` with no ``.scriba-tex-content`` wrapper, and the
CSS bundle was hardcoded — ignoring the ``css_assets`` each RenderArtifact
declares. Net effect: all 71 rules in scriba-tex-content.css were never
shipped, and the 53 shipped pygments rules (scoped under
``.scriba-tex-content .highlight``) could never match. Typography ran on
browser defaults and a long code line stretched the whole page (no
``overflow-x: auto``) instead of scrolling inside its block.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from render import render_file

_DOC = r"""Đoạn văn có $x^2$ toán.

\begin{lstlisting}[language=C++]
ll f(ll y, ll x) { return max(y, x); } // một dòng dài đủ để tràn viewport hẹp khi thiếu overflow
\end{lstlisting}

\begin{animation}[id="demo"]
\shape{a}{Array}{size=3}
\step
\end{animation}

Đoạn kết.
"""


@pytest.fixture(scope="module")
def page(tmp_path_factory) -> str:
    d = tmp_path_factory.mktemp("assembly")
    src = d / "doc.tex"
    src.write_text(_DOC, encoding="utf-8")
    out = d / "doc.html"
    render_file(src, out)
    return out.read_text(encoding="utf-8")


class TestTexContentWrapper:
    def test_tex_regions_are_wrapped(self, page: str) -> None:
        assert page.count('<div class="scriba-tex-content">') == 2  # gap + trailing

    def test_code_block_sits_inside_wrapper(self, page: str) -> None:
        w = page.find('<div class="scriba-tex-content">')
        code = page.find('<div class="scriba-tex-code-block"')
        assert -1 < w < code

    def test_animation_widget_stays_outside_wrapper(self, page: str) -> None:
        # the widget must not inherit tex-content typography
        for m in re.finditer(
            r'<div class="scriba-tex-content">(.*?)</div>\n*(?=<)', page, re.S
        ):
            assert "scriba-widget" not in m.group(1)
        assert 'class="scriba-widget"' in page


class TestDeclaredCssShipped:
    def test_content_css_is_bundled(self, page: str) -> None:
        # a signature rule from scriba-tex-content.css
        assert ".scriba-tex-content .scriba-tex-code-block pre" in page

    def test_pygments_css_still_bundled(self, page: str) -> None:
        assert ".scriba-tex-content .highlight" in page

    def test_pygments_dark_variant_ships_for_the_theme_toggle(self, page: str) -> None:
        # the dark file is entirely [data-theme="dark"]-guarded, so it must
        # ship ALONGSIDE light — the page has a runtime theme toggle and
        # token colors must follow it
        assert '[data-theme="dark"] .scriba-tex-content .highlight' in page


_WIDGET_DOC = r"""Đồ thị và mặt phẳng.

\begin{animation}[id="mp"]
\shape{plot}{MetricPlot}{series=["n"], xlabel="step", ylabel="value"}
\step
\end{animation}

\begin{diagram}[id="pl"]
\shape{p}{Plane2D}{xrange=[-2,2], yrange=[-2,2]}
\apply{p}{add_point=(1.0, 1.0)}
\end{diagram}
"""


def _count_in_sheet(name: str, needle: str) -> int:
    from importlib.resources import files

    return (files("scriba.animation") / "static" / name).read_text(
        "utf-8"
    ).count(needle)


@pytest.fixture(scope="module")
def widget_page(tmp_path_factory) -> str:
    d = tmp_path_factory.mktemp("widgetcss")
    src = d / "doc.tex"
    src.write_text(_WIDGET_DOC, encoding="utf-8")
    out = d / "doc.html"
    render_file(src, out)
    return out.read_text(encoding="utf-8")


class TestArtifactDeclaredWidgetCss:
    """render.py must ship the css_assets animation/diagram artifacts declare.

    Browser-measured bug: MetricPlot gridlines rendered stroke:none because
    scriba-metricplot.css was never bundled — render.py collected artifact
    css_assets only for TeX gaps and shipped a hardcoded 4-sheet list for
    everything else. Companion bug: DiagramRenderer never declared primitive
    CSS at all, so diagram+Plane2D docs stayed broken even with render.py
    fixed.
    """

    def test_metricplot_sheet_ships(self, widget_page: str) -> None:
        assert ".scriba-metricplot-gridline-h" in widget_page

    def test_plane2d_sheet_ships_for_diagram(self, widget_page: str) -> None:
        assert ".scriba-plane" in widget_page

    def test_base_sheets_not_duplicated(self, widget_page: str) -> None:
        # animation artifacts also declare the two base sheets; the union
        # must subtract the base or they concatenate twice. Source-relative
        # counts: each shipped sheet appears exactly once.
        assert widget_page.count(".scriba-metricplot-gridline-h") == 2  # as in source
        # unique to scriba-animation.css (a base sheet every widget artifact
        # also declares) — page count must equal the single-sheet count
        assert widget_page.count("scriba-frame:target .scriba-hl") == \
            _count_in_sheet("scriba-animation.css", "scriba-frame:target .scriba-hl")

    def test_diagram_renderer_declares_primitive_css(self) -> None:
        from scriba.animation.detector import detect_diagram_blocks
        from scriba.animation.renderer import DiagramRenderer
        from scriba.core.context import RenderContext

        blocks = detect_diagram_blocks(_WIDGET_DOC)
        assert blocks
        art = DiagramRenderer().render_block(
            blocks[0], RenderContext(resource_resolver=lambda n: n)
        )
        assert "scriba-plane2d.css" in art.css_assets


class TestRendererDeclaresThemePair:
    def test_artifact_declares_light_and_dark(self) -> None:
        from scriba.core.artifact import Block
        from scriba.core.context import RenderContext
        from scriba.core.workers import SubprocessWorkerPool
        from scriba.tex.renderer import TexRenderer

        pool = SubprocessWorkerPool()
        try:
            r = TexRenderer(worker_pool=pool)
            art = r.render_block(
                Block(start=0, end=4, kind="tex", raw="text"),
                RenderContext(resource_resolver=lambda name: name),
            )
        finally:
            pool.close()
        assert "scriba-tex-pygments-light.css" in art.css_assets
        assert "scriba-tex-pygments-dark.css" in art.css_assets
