"""Tier-B advance-sum vs Chromium truth (bench pins).

Expected px are getBoundingClientRect() measurements of scriba's own
vendored KaTeX rendering at 11px container (investigations/
folabel-measure.md §4). The old heuristic missed these by p50 43%
(and measured pure-command fragments like $\\to$ as 0 px).
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives._math_metrics import (
    is_linear_math,
    measure_inline_math,
)

# (fragment, browser px @ 11px container) — Chromium truth from the bench.
_BROWSER_PINS = [
    ("dp", 13.62),
    ("map", 25.44),
    ("parent[]", 46.19),
    ("dp[i][j]", 39.27),
    ("a_i", 10.92),
    ("A_{ij}", 18.23),
    ("m^2", 17.00),
    ("O(n^2)", 34.20),
    ("2^{n-1}", 24.81),
    (r"\pi r^2", 19.75),
    (r"a \to b", 33.45),
    (r"dp[3] \times dp[4]", 71.64),
    ("x = y", 32.36),
    (r"a \ne b", 30.50),
    ("i+1", 27.52),
    (r"O(\log n)", 48.30),
    ("f(x)", 25.95),
    (r"\sum_{k=0}^{4} dp[k]", 62.36),
    ("n!", 11.70),
    (r"\to", 13.31),
    (r"\alpha", 8.58),
    (r"\le k", 21.39),
    ("|S|", 16.34),
]


class TestBrowserPins:
    @pytest.mark.parametrize("frag,browser_px", _BROWSER_PINS)
    def test_within_one_percent_of_chromium(self, frag: str, browser_px: float) -> None:
        got = measure_inline_math(frag, 11)
        assert abs(got - browser_px) / browser_px <= 0.011, (
            f"${frag}$: predicted {got:.2f}px vs browser {browser_px:.2f}px"
        )

    def test_scales_linearly_with_font_px(self) -> None:
        assert measure_inline_math("dp", 22) == pytest.approx(
            2 * measure_inline_math("dp", 11), rel=0.01
        )


class TestLinearGuard:
    def test_corpus_fragments_are_linear(self) -> None:
        for frag, _ in _BROWSER_PINS:
            assert is_linear_math(frag), frag

    @pytest.mark.parametrize(
        "frag",
        [r"\frac{1}{2}", r"\sqrt{x}", r"\binom{n}{k}", r"\begin{matrix}a\end{matrix}",
         r"a \\ b", r"\unknowncmd x"],
    )
    def test_two_dimensional_or_unknown_falls_back(self, frag: str) -> None:
        assert not is_linear_math(frag)
        # fallback must still return a positive finite width, never crash
        assert measure_inline_math(frag, 11) > 0


class TestFallbackNeverZero:
    def test_pure_command_fragment_nonzero(self) -> None:
        # the old heuristic stripped \to to nothing -> 0 px -> clipped pill
        assert measure_inline_math(r"\to", 11) > 8


class TestMixedLineComposer:
    # browser truth from mixed_bench.py (§5): additive composition is exact;
    # our text term keeps the 0.62 em/char safe-over (+~3%) vs measured 0.60
    _MIXED = [
        ("pattern $P$", 63.20),
        ("failure $F[i]$", 75.22),
        ("nen $(m-1)^2$", 76.70),
        ("value $= 9$", 60.31),
    ]

    def test_mixed_lines_never_under_and_bounded_over(self) -> None:
        from scriba.animation.primitives._text_metrics import measure_label_line

        for line, browser in self._MIXED:
            got = measure_label_line(line, 11)
            assert got >= browser * 0.99, (line, got, browser)
            assert got <= browser * 1.07, (line, got, browser)

    def test_plain_text_line_unchanged(self) -> None:
        from scriba.animation.primitives._text_metrics import measure_label_line
        from scriba.animation.primitives._text_render import estimate_text_width

        assert measure_label_line("shortest path", 11) == estimate_text_width(
            "shortest path", 11
        )

    def test_pure_math_line(self) -> None:
        from scriba.animation.primitives._text_metrics import measure_label_line

        assert abs(measure_label_line("$dp$", 11) - 13.62) <= 1.0
