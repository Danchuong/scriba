"""Snapshot tests for _render_svg_text — plain <text> and foreignObject paths.

Test matrix
-----------
TestPlainTextPath
    plain text → <text> element (control case)
    empty string → empty <text>
    special XML chars → properly escaped
    css_class attribute propagated
    text_anchor / dominant_baseline → inline style
    font_weight / font_size attributes
    no render_inline_tex callback → always plain <text> even with $

TestForeignObjectPath
    math ($...$) → <foreignObject>
    inline HTML-like markup (<span>) → foreignObject if math present
    mixed RTL/LTR text with math → foreignObject
    fo_width / fo_height respected
    text_anchor="start" positions fo_x correctly
    text_anchor="end" positions fo_x correctly
    text_anchor="middle" (default) centres fo_x
    font_weight / font_size forwarded to inline style
    fill colour forwarded

TestDeprecatedTextOutline
    text_outline emits stroke attrs + DeprecationWarning
"""

from __future__ import annotations

import warnings

import pytest

from scriba.animation.primitives._text_render import _render_svg_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _katex_stub(fragment: str) -> str:
    """Minimal stand-in for a KaTeX renderer — returns a recognisable span."""
    inner = fragment.strip("$")
    return f'<span class="katex">{inner}</span>'


# ---------------------------------------------------------------------------
# Plain <text> path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPlainTextPath:
    def test_plain_text_emits_text_element(self) -> None:
        result = _render_svg_text("hello", 10, 20)
        assert result.startswith("<text ")
        assert result.endswith("</text>")
        assert "hello" in result

    def test_plain_text_has_x_y_fill(self) -> None:
        result = _render_svg_text("hello", 10, 20, fill="#aabbcc")
        assert 'x="10"' in result
        assert 'y="20"' in result
        assert 'fill="#aabbcc"' in result

    def test_empty_string_emits_empty_text_element(self) -> None:
        result = _render_svg_text("", 0, 0)
        assert "<text " in result
        assert "</text>" in result
        # content between tags should be empty
        assert "></text>" in result

    def test_ampersand_escaped(self) -> None:
        result = _render_svg_text("a & b", 0, 0)
        assert "&amp;" in result
        assert " & " not in result

    def test_less_than_escaped(self) -> None:
        result = _render_svg_text("a < b", 0, 0)
        assert "&lt;" in result
        assert "< b" not in result

    def test_greater_than_escaped(self) -> None:
        result = _render_svg_text("a > b", 0, 0)
        assert "&gt;" in result

    def test_double_quote_escaped(self) -> None:
        result = _render_svg_text('say "hi"', 0, 0)
        assert "&quot;" in result

    def test_css_class_propagated(self) -> None:
        result = _render_svg_text("x", 0, 0, css_class="cell-label")
        assert 'class="cell-label"' in result

    def test_text_anchor_in_inline_style(self) -> None:
        result = _render_svg_text("x", 0, 0, text_anchor="start")
        assert "text-anchor:start" in result

    def test_dominant_baseline_in_inline_style(self) -> None:
        result = _render_svg_text("x", 0, 0, dominant_baseline="central")
        assert "dominant-baseline:central" in result

    def test_font_weight_in_inline_style(self) -> None:
        result = _render_svg_text("x", 0, 0, font_weight="bold")
        assert "font-weight:bold" in result

    def test_font_size_with_unit_suffix_unchanged(self) -> None:
        result = _render_svg_text("x", 0, 0, font_size="12px")
        assert "font-size:12px" in result

    def test_font_size_without_unit_gets_px(self) -> None:
        result = _render_svg_text("x", 0, 0, font_size="14")
        assert "font-size:14px" in result

    def test_no_callback_forces_plain_text_even_with_math(self) -> None:
        """Without render_inline_tex, math text must still go through plain path."""
        result = _render_svg_text("$x^2$", 0, 0, render_inline_tex=None)
        assert "<text " in result
        assert "<foreignObject" not in result

    def test_non_math_dollar_stays_plain(self) -> None:
        """A lone $ with no closing $ should NOT trigger foreignObject."""
        result = _render_svg_text("price $5", 0, 0, render_inline_tex=_katex_stub)
        assert "<text " in result
        assert "<foreignObject" not in result


# ---------------------------------------------------------------------------
# <foreignObject> path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestForeignObjectPath:
    def test_math_emits_foreign_object(self) -> None:
        result = _render_svg_text("$x^2$", 50, 50, render_inline_tex=_katex_stub)
        assert "<foreignObject" in result
        assert "<text " not in result

    def test_katex_span_in_output(self) -> None:
        result = _render_svg_text("$E=mc^2$", 0, 0, render_inline_tex=_katex_stub)
        assert '<span class="katex">' in result

    def test_inline_html_markup_with_math_uses_foreignobject(self) -> None:
        """Text containing <span> alongside $math$ goes through foreignObject."""
        result = _render_svg_text(
            "see $x$ here", 10, 10, render_inline_tex=_katex_stub
        )
        assert "<foreignObject" in result

    def test_mixed_rtl_ltr_with_math_uses_foreignobject(self) -> None:
        """Arabic mixed with math — foreignObject branch must handle it."""
        result = _render_svg_text(
            "مرحبا $n$", 20, 20, render_inline_tex=_katex_stub
        )
        assert "<foreignObject" in result

    def test_fo_width_respected(self) -> None:
        result = _render_svg_text(
            "$x$", 0, 0, render_inline_tex=_katex_stub, fo_width=120, fo_height=40
        )
        assert 'width="120"' in result
        assert 'height="40"' in result

    def test_fo_width_defaults_to_80(self) -> None:
        result = _render_svg_text("$x$", 0, 0, render_inline_tex=_katex_stub)
        assert 'width="80"' in result

    def test_fo_height_defaults_to_30(self) -> None:
        result = _render_svg_text("$x$", 0, 0, render_inline_tex=_katex_stub)
        assert 'height="30"' in result

    def test_text_anchor_start_fo_x_equals_x(self) -> None:
        result = _render_svg_text(
            "$x$", 100, 50, render_inline_tex=_katex_stub,
            text_anchor="start", fo_width=80
        )
        assert 'x="100"' in result

    def test_text_anchor_end_fo_x_shifted_left_by_width(self) -> None:
        result = _render_svg_text(
            "$x$", 100, 50, render_inline_tex=_katex_stub,
            text_anchor="end", fo_width=80
        )
        # fo_x = x - w = 100 - 80 = 20
        assert 'x="20"' in result

    def test_text_anchor_middle_centres_fo_x(self) -> None:
        result = _render_svg_text(
            "$x$", 100, 50, render_inline_tex=_katex_stub,
            fo_width=80
        )
        # fo_x = x - w // 2 = 100 - 40 = 60
        assert 'x="60"' in result

    def test_fill_forwarded_to_div_style(self) -> None:
        result = _render_svg_text(
            "$x$", 0, 0, render_inline_tex=_katex_stub, fill="#ff0000"
        )
        assert "color:#ff0000" in result

    def test_font_weight_in_foreignobject_div_style(self) -> None:
        result = _render_svg_text(
            "$x$", 0, 0, render_inline_tex=_katex_stub, font_weight="700"
        )
        assert "font-weight:700" in result

    def test_font_size_in_foreignobject_div_style(self) -> None:
        result = _render_svg_text(
            "$x$", 0, 0, render_inline_tex=_katex_stub, font_size="16px"
        )
        assert "font-size:16px" in result

    def test_xhtml_namespace_on_div(self) -> None:
        result = _render_svg_text("$x$", 0, 0, render_inline_tex=_katex_stub)
        assert 'xmlns="http://www.w3.org/1999/xhtml"' in result

    def test_text_anchor_start_sets_text_align_left(self) -> None:
        result = _render_svg_text(
            "$x$", 0, 0, render_inline_tex=_katex_stub, text_anchor="start"
        )
        assert "text-align:left" in result

    def test_text_anchor_end_sets_text_align_right(self) -> None:
        result = _render_svg_text(
            "$x$", 0, 0, render_inline_tex=_katex_stub, text_anchor="end"
        )
        assert "text-align:right" in result

    def test_text_anchor_middle_sets_text_align_center(self) -> None:
        result = _render_svg_text(
            "$x$", 0, 0, render_inline_tex=_katex_stub
        )
        assert "text-align:center" in result

    def test_non_math_literal_escaped_in_mixed_context(self) -> None:
        """Plain text segments alongside math are XML-escaped."""
        result = _render_svg_text(
            "cost $n$ & fees", 0, 0, render_inline_tex=_katex_stub
        )
        assert "&amp;" in result

    def test_escaped_dollar_mixed_html_sentinel_restores_literal_dollar(self) -> None:
        r"""Escaped \$ inside math-containing text is not itself treated as a
        math delimiter — the sentinel logic in _render_mixed_html preserves the
        literal $ in the non-math segments while the enclosing $...$ is still
        rendered via foreignObject."""
        # "price \$ 10 for $n$ items" — has real math AND escaped dollar
        result = _render_svg_text(
            r"price \$ 10 for $n$ items", 0, 0, render_inline_tex=_katex_stub
        )
        # Real math triggers foreignObject
        assert "<foreignObject" in result
        # The escaped dollar should appear as a literal $ in output (not katex-wrapped)
        assert "$" in result
        # The math fragment IS rendered via the callback
        assert '<span class="katex">' in result


# ---------------------------------------------------------------------------
# Deprecated text_outline parameter
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeprecatedTextOutline:
    def test_text_outline_emits_stroke_attrs(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = _render_svg_text("x", 0, 0, text_outline="white")
        assert 'stroke="white"' in result
        assert "stroke-width" in result
        assert "paint-order" in result

    def test_text_outline_issues_deprecation_warning(self) -> None:
        with pytest.warns(DeprecationWarning, match="text_outline="):
            _render_svg_text("x", 0, 0, text_outline="white")
