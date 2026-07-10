"""Tests for the ``${...}`` interpolation shape gate in ``TexRenderer._render_cell``.

judgezone-11: the shield regex ``\\$\\{[^}]*\\}`` used to fire unconditionally,
consuming one ``$`` per match regardless of whether the brace content was
actually interpolation syntax. For math-shaped content like
``${5 \\choose 3}$`` this ate only the opening dollar (not the ``$`` the
author wrote to close the math), leaving an odd dollar count that
mis-paired every later ``$...$`` on the line. The fix gates the shield on
``TexRenderer._INTERP_SHAPE_RE``: only identifier(+subscript/attr)-shaped
brace content is shielded; math-shaped content falls through to normal
``$...$`` pairing, restoring the §13.4 "never clashes with math" guarantee.
"""

from __future__ import annotations

import pytest

from scriba.tex.renderer import TexRenderer

_MATH_SPAN = 'class="scriba-tex-math-inline"'

# Narration text from the judgezone-11 repro fixture (bug present): a
# math-shaped ${...} immediately followed by four ordinary $...$ spans.
_REPRO_NARRATION = (
    r"Cho ${5 \choose 3}$ đọc ba ô: $\texttt{x}[b]$ và $\texttt{y}[c]$ "
    r"ở đây. Là $a-b=2$, không phải $b$."
)

# Control: same sentence with \binom{5}{3} instead of ${5 \choose 3} --
# never contains the literal substring "${" so it never reaches the shield
# regex at all, before or after the fix. Included as a baseline: it must
# keep rendering to the same 5-clean-span shape the fix restores for the
# repro line.
_CONTROL_NARRATION = (
    r"Cho $\binom{5}{3}$ đọc ba ô: $\texttt{x}[b]$ và $\texttt{y}[c]$ "
    r"ở đây. Là $a-b=2$, không phải $b$."
)

# \invariant panel text from the judgezone-11 repro fixture -- same clash,
# different call site. Both \narrate and \invariant funnel through
# render_inline_text/_render_cell, so exercising that method directly
# covers both without standing up the full animation/SceneParser pipeline.
_INVARIANT_NARRATION = (
    r"Inv ${5 \choose 3}$ đọc ba ô: $\texttt{x}[b]$ và $\texttt{y}[c]$ "
    r"ở đây. Là $a-b=2$, không phải $b$."
)


# -----------------------------------------------------------------------------
# (a) / (b) / (c) -- repro, control, and \invariant all yield 5 clean spans
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestInterpShapeGateRepro:
    def test_repro_narration_yields_five_clean_math_spans(self, tex_renderer):
        html = tex_renderer.render_inline_text(_REPRO_NARRATION)
        assert html.count(_MATH_SPAN) == 5
        assert "${5" not in html
        assert "$" not in html

    def test_control_narration_yields_five_clean_math_spans(self, tex_renderer):
        html = tex_renderer.render_inline_text(_CONTROL_NARRATION)
        assert html.count(_MATH_SPAN) == 5
        assert "$" not in html

    def test_invariant_narration_yields_five_clean_math_spans(self, tex_renderer):
        html = tex_renderer.render_inline_text(_INVARIANT_NARRATION)
        assert html.count(_MATH_SPAN) == 5
        assert "${5" not in html
        assert "$" not in html


# -----------------------------------------------------------------------------
# (d) / (e) -- genuine interp forms remain shielded
# -----------------------------------------------------------------------------
#
# The renderer has no notion of "bound" vs "unbound" -- resolution against
# \compute bindings happens upstream (scene.py). An unresolved ${name}
# reaching render_inline_text is indistinguishable from any other
# unresolved identifier-shaped ${...}, so (d) "every genuine interp form is
# still shielded" and (e) "unbound-but-identifier-shaped still echoes
# literally" collapse to the same renderer-level assertion: the literal
# text survives unchanged and is never mistaken for math.


@pytest.mark.unit
class TestInterpShapeGateStillShields:
    @pytest.mark.parametrize(
        "interp",
        ["${a}", "${a_1}", "${arr[i]}", "${total}", "${arr.length}"],
    )
    def test_genuine_interp_form_echoes_literally(self, tex_renderer, interp):
        html = tex_renderer.render_inline_text(f"before {interp} after")
        assert interp in html
        assert _MATH_SPAN not in html

    def test_shielded_interp_does_not_disturb_neighbouring_math(self, tex_renderer):
        html = tex_renderer.render_inline_text(
            r"${arr[i]} then $x^2$ then ${total}"
        )
        assert "${arr[i]}" in html
        assert "${total}" in html
        assert html.count(_MATH_SPAN) == 1


# -----------------------------------------------------------------------------
# Direct regex-level contract (no KaTeX worker needed -- fast)
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestInterpShapeRegexContract:
    @pytest.mark.parametrize(
        "content,expected",
        [
            ("{a}", True),
            ("{a_1}", True),
            ("{arr[i]}", True),
            ("{total}", True),
            ("{arr.length}", True),
            ("{ค่า}", True),  # Thai combining-mark identifier
            ("{5 \\choose 3}", False),  # math body, not interpolation
            ("{n \\choose k}", False),
            ("{}", False),
        ],
    )
    def test_shape_gate_classifies_content(self, content, expected):
        assert bool(TexRenderer._INTERP_SHAPE_RE.match(content)) is expected
