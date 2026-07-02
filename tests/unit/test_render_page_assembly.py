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
