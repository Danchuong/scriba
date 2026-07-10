"""Tests for the ``${...}`` reverse-risk shield in ``_text_render.py``.

judgezone-11 side-finding (sweep wave 2): shape/annotation ``label=`` and
``\\note`` ``text=`` are NOT a documented interpolation position (SCRIBA-TEX-
REFERENCE.md sec 13.2) -- \\compute/\\foreach/\\apply resolution never touches
them, so an unresolved ``${name}`` reaching these SVG text helpers is always
a literal the author wrote (deliberately or as a typo). Before this fix,
``_has_math``/``_render_mixed_html`` had NO shield at all for such runs: the
``${name}`` prefix's lone ``$`` mis-paired with the next real ``$...$`` on
the line -- the mirror image of the wave-1 bug (tex/renderer.py's
``_INTERP_SHAPE_RE``-gated shield), just in a position that had no shield to
begin with rather than an unconditional one.

Confirmed corruption (pre-fix), full pipeline, adversarial two-ref case
``"${x} and $mid$ and ${y} tail"``:
- genuine math ``$mid$`` silently degraded to unstyled literal text "mid"
  (lost its ``$`` delimiters and KaTeX rendering);
- the literal word " and " between the two refs was bogusly KaTeX-rendered
  as math;
- the second ref's leading "$" was silently eaten, leaving bare "{y}" --
  no longer even recognisable as ``${...}`` syntax.

Fix: shield identifier-shaped ``${...}`` runs (the same shape
``TexRenderer._INTERP_SHAPE_RE`` recognises, duplicated locally so this
low-level SVG helper module stays free of a dependency on ``scriba.tex``)
with an opaque, ``$``-free placeholder BEFORE ``$...$`` pairing runs, then
restore the placeholder to its original literal text in both plain and
math-fragment output. Math-shaped ``${...}`` (e.g. the body of
``${5 \\choose 3}$``) is left unshielded and falls through to normal
pairing, symmetric with the wave-1 gate.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from scriba.animation.primitives._text_render import _has_math, _render_mixed_html

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402

# Mirrors the _fake_tex convention in tests/unit/test_pill_math_wrap.py:
# render_inline_tex always receives a fragment WITH its $ delimiters.
_FAKE_MATH_CLASS = "fake-katex"


def _fake_tex(fragment: str) -> str:
    return f'<span class="{_FAKE_MATH_CLASS}">{fragment.strip("$")}</span>'


def _render(source: str, tmp_path: Path) -> str:
    tex_path = tmp_path / "in.tex"
    tex_path.write_text(source, encoding="utf-8")
    out_path = tmp_path / "out.html"
    render_file(tex_path, out_path)
    return out_path.read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# _render_mixed_html: unresolved ${ident} refs stay literal, real math stays
# clean -- direct unit level, fake callback (no KaTeX worker needed).
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderMixedHtmlShieldsInterpRefs:
    def test_ref_before_real_math_stays_literal_and_math_renders_clean(self):
        html = _render_mixed_html("cost ${x} is $y_i$ done", _fake_tex)
        assert "${x}" in html
        assert html.count(f'class="{_FAKE_MATH_CLASS}"') == 1
        assert ">y_i<" in html
        # bogus pre-fix capture must not appear (fake-katex wrapping "x} is")
        assert f'{_FAKE_MATH_CLASS}">x}} is' not in html
        assert "$done" not in html and "y_i$ done" not in html

    def test_two_refs_bracket_real_math_both_stay_literal_math_renders_clean(self):
        html = _render_mixed_html("${x} and $mid$ and ${y} tail", _fake_tex)
        # both refs survive verbatim, including their leading "$"
        assert "${x}" in html
        assert "${y}" in html
        # exactly one math fragment rendered -- "mid", not "and"
        assert html.count(f'class="{_FAKE_MATH_CLASS}"') == 1
        assert ">mid<" in html
        assert ">and<" not in html

    def test_ref_after_real_math_unaffected(self):
        # Odd dollar trails off the end here -- never posed a pairing risk
        # even pre-fix (nothing follows to mis-pair with), kept as a
        # regression control so the shield doesn't change this shape.
        html = _render_mixed_html("before $y_i$ then ${x} after", _fake_tex)
        assert html.count(f'class="{_FAKE_MATH_CLASS}"') == 1
        assert ">y_i<" in html
        assert "${x}" in html

    def test_pure_interp_refs_no_real_math_all_literal(self):
        html = _render_mixed_html("here ${x} and ${y} done", _fake_tex)
        assert "${x}" in html
        assert "${y}" in html
        assert _FAKE_MATH_CLASS not in html


# -----------------------------------------------------------------------------
# _has_math: pure-interpolation-only text must not trip the math fast/slow
# path split -- keeps such labels off the foreignObject/KaTeX machinery
# entirely.
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestHasMathShieldsInterpRefs:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("plain text, no dollars", False),
            ("here ${x} and ${y} done", False),  # refs only, no real math
            ("${arr[i]} and ${total} too", False),
            ("cost ${x} is $y_i$ done", True),  # ref + real math
            ("$a^2$ + $b^2$", True),  # real math only
            ("${5 \\choose 3}$", True),  # math-shaped -- falls through, IS math
        ],
    )
    def test_has_math_classification(self, text, expected):
        assert _has_math(text) is expected


# -----------------------------------------------------------------------------
# Math-shaped ${...} (not identifier-shaped) is not interpolation syntax at
# all -- falls through to normal pairing, symmetric with the wave-1 gate.
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestMathShapedRefFallsThrough:
    def test_math_shaped_brace_content_pairs_normally(self):
        html = _render_mixed_html(r"pick ${5 \choose 3}$ ways", _fake_tex)
        assert f'class="{_FAKE_MATH_CLASS}"' in html
        assert "${5" not in html
        assert "$" not in html


# -----------------------------------------------------------------------------
# Full pipeline (real TexRenderer.render_inline_text callback, real KaTeX
# worker) -- the adversarial repro from the investigation, through
# \\annotate label= and \\note text=.
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestInterpReverseRiskFullPipeline:
    _SRC = (
        '\\begin{{animation}}[id="jz11-reverse-risk", label="reverse risk"]\n'
        "\\shape{{a}}{{Array}}{{size=2, data=[1,2]}}\n"
        "\\step\n"
        '\\annotate{{a.cell[0]}}{{label="{text}"}}\n'
        '\\note{{n1}}{{text="{text}", at=top-right}}\n'
        "\\end{{animation}}\n"
    )

    def test_annotate_label_adversarial_refs_stay_literal(self, tmp_path):
        src = self._SRC.format(text="${x} and $mid$ and ${y} tail")
        html = _render(src, tmp_path)
        assert "${x}" in html
        assert "${y}" in html
        assert html.count('class="scriba-tex-math-inline"') >= 2  # label + note
        # the bogus "and" span must never appear
        label_divs = re.findall(
            r'<div xmlns="http://www.w3.org/1999/xhtml"[^>]*class="scriba-annot-label"[^>]*>(.*?)</div>',
            html,
            re.S,
        )
        assert label_divs, "expected at least one rendered annotation label div"
        for div in label_divs:
            assert ">and<" not in div
