"""B-sweep: cells/values with $math$ — tighten to what is painted.

Two paint modes exist (KaTeX FO with a callback, stripped plain text
without), so the deterministic reservation is max(katex_model,
painted_fallback) — callback-independent, covers both, and drops the
raw-$-and-backslash overhead the old raw measure charged (129px cells
for a 16px glyph — folabel-sweep-katex-cells).
"""

from __future__ import annotations

from scriba.animation.primitives._text_metrics import (
    measure_label_line,
    measure_text,
    measure_value_text,
)
from scriba.animation.primitives._text_render import (
    estimate_text_width,
    strip_math_markup,
)


class TestStripMathMarkup:
    def test_strips_dollars_commands_braces(self) -> None:
        assert strip_math_markup(r"$\max(y,x)$") == "max(y,x)"
        assert strip_math_markup("v = $x_{i}$") == "v = x_i"
        assert strip_math_markup("$dp[i][j]$") == "dp[i][j]"
        assert strip_math_markup(r"$2^{n-1}$") == "2^n-1"

    def test_plain_text_untouched(self) -> None:
        assert strip_math_markup("gia tri 42") == "gia tri 42"

    def test_escaped_dollar_survives(self) -> None:
        assert strip_math_markup(r"cost \$5") == r"cost \$5"


class TestMeasureValueText:
    def test_plain_uses_base_measurer(self) -> None:
        assert measure_value_text("1000000", 14) == measure_text("1000000", 14)
        assert measure_value_text("abc", 13, mono=True) == estimate_text_width(
            "abc", 13
        )

    def test_math_is_max_of_model_and_painted_fallback(self) -> None:
        s = r"$\max(y,x)$"
        got = measure_value_text(s, 13)
        assert got == max(
            measure_label_line(s, 13), measure_text(strip_math_markup(s), 13)
        )
        # tighter than the old raw measure (which charged $ + backslash)
        assert got < measure_text(s, 13)

    def test_math_never_below_either_paint_mode(self) -> None:
        for s in (r"$x_i$", r"$\infty$", r"$\Leftrightarrow$", "$dp[i][j]$"):
            got = measure_value_text(s, 14)
            assert got >= measure_label_line(s, 14)
            assert got >= measure_text(strip_math_markup(s), 14)


class TestFallbackPaintsStripped:
    def test_render_svg_text_no_callback_strips_math(self) -> None:
        from scriba.animation.primitives._text_render import _render_svg_text

        out = _render_svg_text(r"$\max(y,x)$", 50, 20)
        assert "<text" in out and "foreignObject" not in out
        assert "max(y,x)" in out
        assert "$" not in out and "\\max" not in out


class TestValueChannelOneInterpretation:
    """JZ-13 sweep (wave 2): the value= channel (``measure_value_text`` /
    ``measure_label_line`` / ``_render_svg_text`` / ``_render_mixed_html``)
    must share the SAME "one interpretation" contract as the annotation
    pill channel (``tests/unit/test_label_one_interpretation.py``): text
    outside ``$...$`` is literal (``\\_`` unescapes, bare ``_`` stays
    literal), ``\\texttt{...}`` unwraps unconditionally, math transforms
    apply only inside ``$...$``. Covers all four (measure x paint) x
    (callback x no-callback) combinations that share the underlying
    ``strip_math_markup`` helper.
    """

    VARIANTS = [
        "upper_bound",
        r"upper\_bound",
        r"\texttt{upper\_bound}",
    ]

    @staticmethod
    def _fake_katex(frag: str) -> str:
        return f"<katex>{frag}</katex>"

    def test_measure_value_text_converges_across_variants(self) -> None:
        widths = {v: measure_value_text(v, 14) for v in self.VARIANTS}
        assert len(set(widths.values())) == 1, widths

    def test_measure_label_line_converges_across_variants(self) -> None:
        widths = {v: measure_label_line(v, 14) for v in self.VARIANTS}
        assert len(set(widths.values())) == 1, widths

    def test_measure_label_line_mixed_segment_literal_converges(self) -> None:
        # the has-$ branch's text_seg/tail (not just the no-$ early
        # return) must ALSO get the literal pass, mirroring the split
        # _render_mixed_html renders with.
        widths = {
            v: measure_label_line(f"{v} is $x_i$ now", 14) for v in self.VARIANTS
        }
        assert len(set(widths.values())) == 1, widths

    def test_render_svg_text_no_callback_converges(self) -> None:
        from scriba.animation.primitives._text_render import _render_svg_text

        outs = {_render_svg_text(v, 0, 0) for v in self.VARIANTS}
        assert len(outs) == 1, outs
        assert ">upper_bound<" in outs.pop()

    def test_render_svg_text_with_callback_no_math_converges(self) -> None:
        # Dominant real-world case: Pipeline/TexRenderer always registers a
        # working KaTeX callback. A value with no $...$ must still paint
        # its literal interpretation, not raw \_ / \texttt{...} markup —
        # previously only the no-callback path was fixed here.
        from scriba.animation.primitives._text_render import _render_svg_text

        outs = {
            _render_svg_text(v, 0, 0, render_inline_tex=self._fake_katex)
            for v in self.VARIANTS
        }
        assert len(outs) == 1, outs
        assert ">upper_bound<" in outs.pop()

    def test_render_mixed_html_converges(self) -> None:
        from scriba.animation.primitives._text_render import _render_mixed_html

        outs = {_render_mixed_html(v, self._fake_katex) for v in self.VARIANTS}
        assert outs == {"upper_bound"}

    def test_texttt_inside_math_stays_untouched_for_katex(self) -> None:
        # The one sanctioned exception: \texttt{} INSIDE $...$ with a real
        # callback is KaTeX's job (renders natively as monospace math) —
        # scriba's own unwrap must not touch it (wave-1 contract, verified
        # here for the value channel too).
        from scriba.animation.primitives._text_render import _render_mixed_html

        out = _render_mixed_html(r"$\texttt{upper\_bound}$", self._fake_katex)
        assert out == r"<katex>$\texttt{upper\_bound}$</katex>"

    def test_mixed_literal_and_math_segment_scoping(self) -> None:
        # One interpretation WITHIN a single string: the literal segment
        # unescapes; the math segment is handed verbatim to the callback.
        from scriba.animation.primitives._text_render import _render_mixed_html

        out = _render_mixed_html(r"upper\_bound is $x_i$ now", self._fake_katex)
        assert out == "upper_bound is <katex>$x_i$</katex> now"

    def test_adjacent_escaped_dollars_do_not_phantom_pair(self) -> None:
        # Two independent \$ escapes around literal text must not misread
        # as a math span now that non-math segments route through
        # strip_math_markup (sentinel-restore-order safety).
        from scriba.animation.primitives._text_render import _render_mixed_html

        out = _render_mixed_html(r"cost \$5 and \$10 only", self._fake_katex)
        assert out == "cost $5 and $10 only"
        assert "<katex>" not in out
