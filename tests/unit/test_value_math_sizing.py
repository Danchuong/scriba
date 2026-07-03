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
