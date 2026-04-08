"""5 XSS hardening tests per docs/scriba/02-tex-plugin.md §9.

Assertions are made on the *raw* renderer output (not bleach-cleaned)
because the spec mandates Scriba's belt-and-suspenders hardening must
produce safe HTML before any sanitizer runs. See PHASE2_DECISIONS.md D-09.
"""

from __future__ import annotations

import pytest


def test_xss_script_tag_in_text(pipeline, ctx):
    tex = r"\textbf{<script>alert(1)</script>}"
    doc = pipeline.render(tex, ctx)
    html = doc.html.lower()
    assert "<script" not in html
    assert "&lt;script&gt;" in html or "&lt;script" in html


def test_xss_javascript_url_in_href(pipeline, ctx):
    tex = r"\href{javascript:alert(1)}{click}"
    doc = pipeline.render(tex, ctx)
    html = doc.html
    assert "javascript:" not in html.lower()
    assert "scriba-tex-link-disabled" in html


def test_xss_filename_with_quotes_in_includegraphics(pipeline, ctx):
    tex = r'\includegraphics{"><script>.png}'
    doc = pipeline.render(tex, ctx)
    html = doc.html
    # No raw <script> tag, no unescaped quote breaking out of an attribute.
    assert "<script" not in html.lower()
    # Quote inside attribute must be entity-escaped.
    assert '"><script' not in html


def test_xss_malformed_brace_img_onerror(pipeline, ctx):
    tex = r"\textbf{<img src=x onerror=alert(1)>}"
    doc = pipeline.render(tex, ctx)
    html = doc.html.lower()
    assert "onerror" not in html or "&lt;img" in html
    assert "<img src=x onerror" not in html.lower()


@pytest.mark.skip(reason="implemented in sub-phase 2d")
def test_xss_data_code_breakout(pipeline, ctx):
    tex = (
        r"\begin{lstlisting}[language=cpp]"
        r'" onload="alert(1)'
        r"\end{lstlisting}"
    )
    doc = pipeline.render(tex, ctx)
    html = doc.html
    # The data-code attribute value must be entity-escaped so the literal
    # quote cannot break out of the attribute.
    assert 'onload="alert(1)' not in html
    assert "&quot;" in html or "&#34;" in html
