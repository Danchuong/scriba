"""Tests for the ``\\invariant{text}`` pinned-panel command (⑩b, static v1).

``\\invariant`` is a **prelude-only** command that pins a predicate panel shown
across all frames — rendered once at the widget level (so it survives on screen
AND in print), with KaTeX applied to ``$math$`` in the text.  It carries no
per-frame state (no snapshot / FrameData / differ surface).  Placed after the
first ``\\step`` it is a hard **E1058**.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.core.errors import ValidationError

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


class TestInvariantParse:
    def test_prelude_invariant_collected(self) -> None:
        ir = SceneParser().parse(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\invariant{a is sorted}\n"
            "\\step\n"
            "\\narrate{Body.}\n"
        )
        assert ir.invariants == ("a is sorted",)

    def test_invariant_after_step_raises_e1058(self) -> None:
        with pytest.raises(ValidationError) as exc:
            SceneParser().parse(
                "\\shape{a}{Array}{size=2, data=[1,2]}\n"
                "\\step\n"
                "\\invariant{too late}\n"
            )
        assert exc.value.code == "E1058"

    def test_no_invariant_is_empty(self) -> None:
        ir = SceneParser().parse(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
        )
        assert ir.invariants == ()


class TestInvariantRender:
    def _render(self, source: str, tmp_path: Path) -> str:
        tex_path = tmp_path / "in.tex"
        tex_path.write_text(source, encoding="utf-8")
        out_path = tmp_path / "out.html"
        render_file(tex_path, out_path)
        return out_path.read_text(encoding="utf-8")

    def test_invariant_panel_rendered_once(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="inv"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\invariant{loop keeps the prefix sorted}\n"
            "\\step\n"
            "\\narrate{Step one.}\n"
            "\\step\n"
            "\\narrate{Step two.}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        assert 'class="scriba-invariant"' in html_out
        assert "loop keeps the prefix sorted" in html_out
        # Static: exactly one panel even across two frames.
        assert html_out.count('class="scriba-invariant"') == 1

    def test_invariant_renders_katex(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="inv katex"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\invariant{$a_i \\le a_{i+1}$}\n"
            "\\step\n"
            "\\narrate{Body.}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        assert 'class="scriba-invariant"' in html_out
        # KaTeX rendered the inline math inside the panel.
        assert "katex" in html_out
