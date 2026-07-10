"""JZ-13 defects #2/#3/#4: ONE interpretation of a label string shared by
paint (``strip_math_markup``) and speech (``_latex_to_speech``).

Contract: text outside ``$...$`` is literal — a bare ``_`` stays literal,
``\\_`` unescapes to ``_``, no TeX-speech transform runs. Math transforms
(command words, subscript, superscript) and speech rules apply ONLY
inside ``$...$`` segments. ``\\texttt{...}`` is a literal-text-island
command unwrapped unconditionally, independent of ``$...$``.
"""

from __future__ import annotations

from scriba.animation.primitives._svg_helpers import _latex_to_speech
from scriba.animation.primitives._text_render import strip_math_markup


class TestPaintOneInterpretation:
    def test_bare_underscore_outside_math_stays_literal(self) -> None:
        assert strip_math_markup("upper_bound") == "upper_bound"

    def test_escaped_underscore_outside_math_unescapes(self) -> None:
        assert strip_math_markup(r"upper\_bound") == "upper_bound"

    def test_bare_texttt_unwraps_and_unescapes(self) -> None:
        assert strip_math_markup(r"\texttt{upper\_bound}") == "upper_bound"

    def test_math_wrapped_texttt_unwraps_and_unescapes(self) -> None:
        assert strip_math_markup(r"$\texttt{upper\_bound}$") == "upper_bound"

    def test_math_subscript_still_strips_normally(self) -> None:
        # \command -> command and brace-strip only; a bare underscore with
        # no backslash/braces is untouched (matches the pre-existing
        # precedent in test_pill_dimensions_raw_mode_measures_painted_string).
        assert strip_math_markup("$dp_i$") == "dp_i"

    def test_all_four_variants_converge(self) -> None:
        expected = "upper_bound = begin(): nothing ≤ 3"
        assert strip_math_markup("upper_bound = begin(): nothing ≤ 3") == expected
        assert strip_math_markup(r"upper\_bound = begin(): nothing ≤ 3") == expected
        assert (
            strip_math_markup(r"\texttt{upper\_bound} = begin(): nothing ≤ 3")
            == expected
        )
        assert (
            strip_math_markup(r"$\texttt{upper\_bound}$ = begin(): nothing ≤ 3")
            == expected
        )


class TestSpeechOneInterpretation:
    def test_bare_underscore_outside_math_stays_literal(self) -> None:
        assert _latex_to_speech("upper_bound") == "upper_bound"

    def test_escaped_underscore_outside_math_unescapes(self) -> None:
        assert _latex_to_speech(r"upper\_bound") == "upper_bound"

    def test_bare_texttt_unwraps_and_unescapes(self) -> None:
        assert _latex_to_speech(r"\texttt{upper\_bound}") == "upper_bound"

    def test_math_wrapped_texttt_unwraps_and_unescapes(self) -> None:
        assert _latex_to_speech(r"$\texttt{upper\_bound}$") == "upper_bound"

    def test_all_four_variants_converge(self) -> None:
        expected = "upper_bound = begin(): nothing ≤ 3"
        assert _latex_to_speech("upper_bound = begin(): nothing ≤ 3") == expected
        assert (
            _latex_to_speech("upper\\_bound = begin(): nothing ≤ 3") == expected
        )
        assert (
            _latex_to_speech(
                "\\texttt{upper\\_bound} = begin(): nothing ≤ 3"
            )
            == expected
        )
        assert (
            _latex_to_speech(
                "$\\texttt{upper\\_bound}$ = begin(): nothing ≤ 3"
            )
            == expected
        )

    def test_dp_i_subscript_regression_pin(self) -> None:
        # MANDATORY regression pin: scoping speech transforms to $...$
        # must NOT break the existing subscript-speech contract.
        assert _latex_to_speech("$dp_i$") == "dp subscript i"

    def test_mixed_text_and_math_only_math_transforms(self) -> None:
        # "one interpretation" within a SINGLE string: the literal
        # underscore outside math stays literal while the math segment's
        # subscript still speaks as "subscript".
        assert (
            _latex_to_speech("max_value is $x_i$ now")
            == "max_value is x subscript i now"
        )
