"""Pin: ``${...}`` stays inert outside the five documented interpolation
positions (SCRIBA-TEX-REFERENCE.md sec 13.2: ``\\foreach`` bodies, ``\\apply``
values, selector indices, ``\\narrate`` text, ``\\invariant`` panels).

judgezone-11 wave-2 Item 4: probes ``\\step[title=]`` and the top-level
``\\begin{animation}[label=]`` attribute -- both explicitly excluded from the
interpolation position list -- to confirm an unresolved, unbound ``${x}``
sitting next to real ``$y_i$`` math renders as inert literal text: no
``\\compute`` substitution, no E1159/E1161, no crash. Both positions turned
out to have no math-rendering path at all (title/label are plain attribute
text, never reaching ``_has_math``/``_render_mixed_html``), so there is no
mis-pairing surface here the way there was for ``label=``/``\\note text=``
(see ``test_interp_reverse_risk_shield.py``) -- these are regression pins
confirming that, not shape-gate fixes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


def _render(source: str, tmp_path: Path) -> str:
    tex_path = tmp_path / "in.tex"
    tex_path.write_text(source, encoding="utf-8")
    out_path = tmp_path / "out.html"
    render_file(tex_path, out_path)
    return out_path.read_text(encoding="utf-8")


@pytest.mark.unit
class TestStepTitleInterpInert:
    def test_unbound_ref_next_to_math_stays_literal(self, tmp_path):
        src = (
            '\\begin{animation}[id="step-title-inert", label="plain"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            '\\step[title="cost ${x} is $y_i$ done"]\n'
            "\\highlight{a.cell[0]}\n"
            "\\end{animation}\n"
        )
        html = _render(src, tmp_path)
        assert "cost ${x} is $y_i$ done" in html
        assert 'class="scriba-tex-math-inline"' not in html


@pytest.mark.unit
class TestAnimationLabelInterpInert:
    def test_unbound_ref_next_to_math_stays_literal(self, tmp_path):
        src = (
            '\\begin{animation}[id="anim-label-inert", '
            'label="cost ${x} is $y_i$ done"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            "\\highlight{a.cell[0]}\n"
            "\\end{animation}\n"
        )
        html = _render(src, tmp_path)
        assert 'aria-label="cost ${x} is $y_i$ done"' in html
