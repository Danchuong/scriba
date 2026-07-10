"""Hypothesis property tests for JZ-13's "one interpretation" contract:

    Text outside $...$ is literal text: `_` literal, `\\_` -> `_`, no
    TeX-speech transforms; math transforms and speech rules apply ONLY
    inside $...$ segments.

``tests/unit/test_label_one_interpretation.py`` pins this contract with
fixed examples (bare underscore, escaped underscore, ``\\texttt{}``, the
mixed text+math case, and the mandatory ``$dp_i$`` regression pin). This
file generalizes the same contract over a wide space of generated
identifier-ish strings (snake_case, Vietnamese diacritics, escaped
underscores, ``\\texttt{}``-wrapped text) via hypothesis, plus a
generalization of the defect #1 pill-padding invariant across many
generated multi-line labels.
"""
from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from scriba.animation.primitives._svg_helpers import (
    _LABEL_PILL_PAD_X,
    _latex_to_speech,
    pill_dimensions,
)
from scriba.animation.primitives._text_metrics import measure_text_run
from scriba.animation.primitives._text_render import (
    estimate_text_width,
    strip_math_markup,
)

_WORD_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_VIETNAMESE_ALPHABET = (
    "ạảấầẩẫậắằẳẵặàáâãèéêềếểễệìíîïòóôõơờởỡợùúûüưừửữựỳýỵỷỹđ "
)


@composite
def st_identifier_ish_literal(draw: st.DrawFn) -> str:
    """Literal text outside math — no ``$``, no command words other than
    the two literal-text-island forms the JZ-13 contract names explicitly
    (a bare/escaped underscore, ``\\texttt{...}``). Every string this
    strategy draws must resolve identically under paint and speech.
    """
    category = draw(
        st.sampled_from(
            ["snake_case", "vietnamese", "escaped_underscore", "texttt_wrapped", "plain_words"]
        )
    )
    words = st.text(alphabet=_WORD_ALPHABET, min_size=1, max_size=8)

    if category == "snake_case":
        parts = draw(st.lists(words, min_size=1, max_size=4))
        return "_".join(parts)
    elif category == "vietnamese":
        return draw(st.text(alphabet=_VIETNAMESE_ALPHABET, min_size=1, max_size=25))
    elif category == "escaped_underscore":
        parts = draw(st.lists(words, min_size=2, max_size=4))
        return r"\_".join(parts)
    elif category == "texttt_wrapped":
        parts = draw(st.lists(words, min_size=1, max_size=4))
        sep = draw(st.sampled_from(["_", r"\_"]))
        return "\\texttt{" + sep.join(parts) + "}"
    else:  # plain_words
        parts = draw(st.lists(words, min_size=1, max_size=5))
        return " ".join(parts)


@composite
def st_wrap_pressure_text(draw: st.DrawFn) -> str:
    """Long space-separated text likely to wrap across multiple lines —
    generalizes the fixed Vietnamese sentence in
    ``test_pill_math_wrap.py``'s two ``covers_painted_text_multiline``
    tests over a wider generated space (ASCII words and Vietnamese
    diacritics), still literal (no ``$``, no backslashes).
    """
    use_vietnamese = draw(st.booleans())
    alphabet = _VIETNAMESE_ALPHABET if use_vietnamese else _WORD_ALPHABET + " "
    return draw(st.text(alphabet=alphabet, min_size=30, max_size=70))


# ---------------------------------------------------------------------------
# Core contract: outside math, paint and speech are ONE interpretation.
# ---------------------------------------------------------------------------


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=10_000)
@given(text=st_identifier_ish_literal())
def test_paint_and_speech_converge_outside_math(text: str) -> None:
    """The contract's central claim: with no ``$...$`` present, the width
    ruler's text (``strip_math_markup``) and the aria/title builder's text
    (``_latex_to_speech``) resolve every character identically. The ONE
    sanctioned divergence is whitespace normalization: speech collapses
    runs of whitespace as its final a11y step (R-11 step 7), paint
    preserves them — so the comparison normalizes whitespace on both
    sides. Everything else (``_``, ``\\_``, ``\\texttt``) must agree
    byte-for-byte."""
    painted = " ".join(strip_math_markup(text).split())
    spoken = " ".join(_latex_to_speech(text).split())
    assert painted == spoken, text


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=10_000)
@given(text=st_identifier_ish_literal())
def test_no_escaped_underscore_survives_either_consumer(text: str) -> None:
    """defect #3: ``\\_`` must unescape to ``_`` for BOTH consumers — no
    leftover backslash-underscore artifact in painted or spoken text."""
    assert "\\_" not in strip_math_markup(text), text
    assert "\\_" not in _latex_to_speech(text), text


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=10_000)
@given(text=st_identifier_ish_literal())
def test_texttt_wrapper_never_leaks_into_either_consumer(text: str) -> None:
    """defect #4: ``\\texttt{...}`` is unwrapped unconditionally — neither
    consumer's output may still show the command name or its braces."""
    assert "texttt" not in strip_math_markup(text), text
    assert "texttt" not in _latex_to_speech(text), text


# ---------------------------------------------------------------------------
# Math-scoped speech: subscript speech still fires INSIDE $...$ (the
# mandatory $dp_i$ regression pin, generalized over many identifiers).
# ---------------------------------------------------------------------------


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=10_000)
@given(
    ident=st.text(alphabet=_WORD_ALPHABET, min_size=1, max_size=6),
    sub=st.text(alphabet=_WORD_ALPHABET + "0123456789", min_size=1, max_size=3),
)
def test_math_subscript_speech_generalizes_dp_i_pin(ident: str, sub: str) -> None:
    """MANDATORY regression pin (dp_i -> "dp subscript i"), generalized:
    scoping speech transforms to ``$...$`` must not break subscript speech
    for any identifier/subscript pair, only for the one pinned example."""
    assert (
        _latex_to_speech(f"${ident}_{sub}$") == f"{ident} subscript {sub}"
    ), (ident, sub)


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=10_000)
@given(
    prefix=st.text(alphabet=_WORD_ALPHABET, min_size=1, max_size=8),
    ident=st.text(alphabet=_WORD_ALPHABET, min_size=1, max_size=6),
    sub=st.text(alphabet=_WORD_ALPHABET, min_size=1, max_size=3),
    suffix=st.text(alphabet=_WORD_ALPHABET, min_size=1, max_size=8),
)
def test_mixed_literal_and_math_only_math_segment_transforms(
    prefix: str, ident: str, sub: str, suffix: str
) -> None:
    """"one interpretation" WITHIN a single string: literal text on either
    side of a ``$...$`` segment stays literal while the math segment still
    speaks its subscript — generalizes
    ``test_mixed_text_and_math_only_math_transforms``."""
    text = f"{prefix}_x is ${ident}_{sub}$ for {suffix}_y"
    expected = f"{prefix}_x is {ident} subscript {sub} for {suffix}_y"
    assert _latex_to_speech(text) == expected, text


# ---------------------------------------------------------------------------
# defect #1 generalization: pill_dimensions never under-reserves relative
# to an independently-measured painted width, across many generated labels.
# ---------------------------------------------------------------------------


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=10_000)
@given(label=st_wrap_pressure_text())
def test_pill_width_covers_independently_measured_lines_scriba_sans(label: str) -> None:
    """Generalizes
    ``test_scriba_sans_pill_covers_painted_text_multiline``: whatever the
    wrap policy produces, the returned ``pill_w`` must cover each line's
    independently-measured painted width (line + trailing inter-line
    space) plus padding on both sides."""
    lines, _, pill_w, _ = pill_dimensions(label, 11, wrap_px=132, math_rendered=True)
    num_lines = len(lines)
    for li, ln in enumerate(lines):
        painted = measure_text_run(ln, 11)
        if li < num_lines - 1:
            painted += measure_text_run(" ", 11)
        assert pill_w >= painted + 2 * _LABEL_PILL_PAD_X - 0.5, (label, li, ln)


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=10_000)
@given(label=st_wrap_pressure_text())
def test_pill_width_covers_independently_measured_lines_no_callback(label: str) -> None:
    """Generalizes ``test_no_callback_multiline_pill_covers_painted_text``
    (the ``math_rendered=False`` / no-KaTeX-callback path, where tspan is
    always the paint branch)."""
    lines, _, pill_w, _ = pill_dimensions(label, 11, wrap_px=132, math_rendered=False)
    num_lines = len(lines)
    for li, ln in enumerate(lines):
        painted = estimate_text_width(strip_math_markup(ln), 11)
        if li < num_lines - 1:
            painted += estimate_text_width(" ", 11)
        assert pill_w >= painted + 2 * _LABEL_PILL_PAD_X, (label, li, ln)
