"""Unit tests for scriba.animation._minify.

Covers _minify_html (and indirectly _minify_css / _minify_js).
"""

from __future__ import annotations

import pytest

from scriba.animation._minify import _minify_css, _minify_html, _minify_js


# ---------------------------------------------------------------------------
# _minify_html — blank-line collapsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_html_collapses_multiple_blank_lines() -> None:
    """Multiple consecutive blank lines between tags are collapsed."""
    html = "<div>\n\n\n\n<p>hello</p>\n\n\n</div>"
    result = _minify_html(html)
    # The result must not contain more than one consecutive blank line
    assert "\n\n\n" not in result
    # Content must be preserved
    assert "hello" in result


@pytest.mark.unit
def test_html_collapses_whitespace_between_tags() -> None:
    """Whitespace-only text between adjacent tags is collapsed."""
    html = "<div>   \n   <span>text</span>   \n   </div>"
    result = _minify_html(html)
    assert "text" in result
    # No multi-space runs between > and <
    assert ">   <" not in result


# ---------------------------------------------------------------------------
# _minify_html — <pre> preservation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pre_content_preserved_verbatim() -> None:
    """Content inside <pre> is NOT minified."""
    html = "<div>\n\n<pre>  indented\n    code  </pre>\n\n</div>"
    result = _minify_html(html)
    assert "  indented\n    code  " in result


@pytest.mark.unit
def test_pre_with_attributes_preserved() -> None:
    """<pre> with attributes is also preserved verbatim."""
    html = '<pre class="code">   spaces   </pre>'
    result = _minify_html(html)
    assert "   spaces   " in result


# ---------------------------------------------------------------------------
# _minify_html — <style> block protection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_style_block_css_is_minified_not_stripped() -> None:
    """CSS inside <style> is minified but the block itself is kept."""
    html = "<style>\n.foo {\n  color: red;\n}\n</style>"
    result = _minify_html(html)
    assert "<style>" in result or "<style " in result.lower()
    assert "</style>" in result
    assert "color" in result


@pytest.mark.unit
def test_style_block_content_stays_inside_style_tags() -> None:
    """CSS content does not escape the <style> element."""
    css_body = ".a { margin: 0; }"
    html = f"<style>{css_body}</style><p>after</p>"
    result = _minify_html(html)
    # The CSS selector must appear before </style>
    style_end = result.index("</style>")
    css_pos = result.index(".a")
    assert css_pos < style_end


# ---------------------------------------------------------------------------
# _minify_html — <script> block protection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_script_block_js_is_kept() -> None:
    """JS inside <script> is preserved (not stripped entirely)."""
    html = "<script>\nvar x = 1; // comment\n</script>"
    result = _minify_html(html)
    assert "<script>" in result or "<script " in result.lower()
    assert "</script>" in result
    assert "var x = 1" in result


@pytest.mark.unit
def test_script_block_js_comments_stripped() -> None:
    """Single-line JS comments are stripped from inside <script>."""
    html = "<script>\nvar x = 1; // this is a comment\n</script>"
    result = _minify_html(html)
    # The comment text should not appear (conservative JS strip)
    assert "this is a comment" not in result


@pytest.mark.unit
def test_script_block_stays_inside_script_tags() -> None:
    """JS content does not escape the <script> element."""
    html = "<script>\nconsole.log(1);\n</script><p>after</p>"
    result = _minify_html(html)
    script_end = result.index("</script>")
    js_pos = result.index("console")
    assert js_pos < script_end


# ---------------------------------------------------------------------------
# _minify_html — idempotence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_minify_html_idempotent_on_simple_html() -> None:
    """Minifying already-minified HTML produces the same string."""
    html = "<div><p>hello world</p></div>"
    first = _minify_html(html)
    second = _minify_html(first)
    assert first == second


@pytest.mark.unit
def test_minify_html_idempotent_with_style_and_script() -> None:
    """Idempotence holds when <style> and <script> blocks are present."""
    html = (
        "<style>.a{color:red}</style>"
        "<script>var x=1;</script>"
        "<div><p>text</p></div>"
    )
    first = _minify_html(html)
    second = _minify_html(first)
    assert first == second


# ---------------------------------------------------------------------------
# _minify_html — edge: empty input
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_minify_html_empty_string_returns_empty() -> None:
    """Empty string input returns empty string."""
    assert _minify_html("") == ""


@pytest.mark.unit
def test_minify_html_whitespace_only_returns_empty() -> None:
    """Whitespace-only input returns empty string (stripped)."""
    result = _minify_html("   \n\n   ")
    assert result == ""


# ---------------------------------------------------------------------------
# _minify_css — direct unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_minify_css_removes_comments() -> None:
    """CSS block comments are removed."""
    css = "/* header */\n.a { color: red; }"
    result = _minify_css(css)
    assert "header" not in result
    assert "color:red" in result


@pytest.mark.unit
def test_minify_css_empty_returns_empty() -> None:
    """Empty CSS returns empty string."""
    assert _minify_css("") == ""


# ---------------------------------------------------------------------------
# _minify_js — direct unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_minify_js_strips_line_comments() -> None:
    """Single-line // comments are stripped."""
    js = "var x = 1; // remove me\nvar y = 2;"
    result = _minify_js(js)
    assert "remove me" not in result
    assert "var y = 2" in result


@pytest.mark.unit
def test_minify_js_preserves_url_in_strings() -> None:
    """URLs containing :// are not mangled."""
    js = 'var u = "https://example.com";'
    result = _minify_js(js)
    assert "https://example.com" in result


@pytest.mark.unit
def test_minify_js_empty_returns_empty() -> None:
    """Empty JS returns empty string."""
    assert _minify_js("") == ""
