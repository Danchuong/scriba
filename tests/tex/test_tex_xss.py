"""5 XSS hardening tests per docs/scriba/02-tex-plugin.md §9.

Assertions are made on the *raw* renderer output (not bleach-cleaned)
because the spec mandates Scriba's belt-and-suspenders hardening must
produce safe HTML before any sanitizer runs. See PHASE2_DECISIONS.md D-09.
"""

from __future__ import annotations

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


def test_xss_href_newline_smuggle(pipeline, ctx):
    tex = "\\href{http://evil.com\x0Ajavascript:alert(1)}{x}"
    doc = pipeline.render(tex, ctx)
    html = doc.html.lower()
    assert "javascript:" not in html


def test_xss_href_unicode_line_separator(pipeline, ctx):
    tex = "\\href{java\u2028script:alert(1)}{x}"
    doc = pipeline.render(tex, ctx)
    html = doc.html.lower()
    assert "javascript:" not in html
    assert "scriba-tex-link-disabled" in doc.html


def test_xss_href_tab_smuggle(pipeline, ctx):
    tex = "\\href{\tjavascript:alert(1)}{x}"
    doc = pipeline.render(tex, ctx)
    assert "javascript:" not in doc.html.lower()
    assert "scriba-tex-link-disabled" in doc.html


def test_xss_href_uppercase_javascript(pipeline, ctx):
    tex = r"\href{JAVASCRIPT:alert(1)}{x}"
    doc = pipeline.render(tex, ctx)
    assert "javascript:" not in doc.html.lower()
    assert "scriba-tex-link-disabled" in doc.html


def test_xss_image_resolver_returns_javascript_url(pipeline):
    """Resource resolver returning a javascript: URL must be treated as
    a missing image, not embedded as src."""
    from scriba import RenderContext

    bad_ctx = RenderContext(
        resource_resolver=lambda name: "javascript:alert(1)",
    )
    doc = pipeline.render(r"\includegraphics{evil.png}", bad_ctx)
    assert "javascript:" not in doc.html.lower()
    assert "<img" not in doc.html.lower()
    assert "scriba-tex-image-missing" in doc.html


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
