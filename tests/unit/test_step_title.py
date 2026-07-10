"""Tests for the ``\\step[title="..."]`` option (⑩a).

The ``title`` option adds a short human-readable caption to a step.  It:

* parses alongside ``label`` in ``_try_parse_step_options`` (returns a
  ``(label, title)`` pair now);
* threads onto ``StepCommand.title`` → ``FrameIR.title`` → ``FrameData.title``;
* renders a ``<span class="scriba-step-title">`` heading folded into the
  narration so it travels with the JS narration swap AND prints;
* supersedes the narration-derived ``<title>``/``aria-labelledby`` on the SVG;
* is fully opt-in: absent ``title`` leaves the rendered bytes unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scriba.animation.parser.grammar import SceneParser

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


def _parse(body: str):
    return SceneParser().parse(body)


class TestStepTitleParse:
    def test_title_and_label_together(self) -> None:
        ir = _parse(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step[label=init, title=\"Fill the base row\"]\n"
            "\\narrate{Body.}\n"
        )
        assert ir.frames[0].label == "init"
        assert ir.frames[0].title == "Fill the base row"

    def test_title_alone(self) -> None:
        ir = _parse(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step[title=\"Only a title\"]\n"
            "\\narrate{Body.}\n"
        )
        assert ir.frames[0].label is None
        assert ir.frames[0].title == "Only a title"

    def test_label_alone_leaves_title_none(self) -> None:
        ir = _parse(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step[label=init]\n"
            "\\narrate{Body.}\n"
        )
        assert ir.frames[0].label == "init"
        assert ir.frames[0].title is None

    def test_no_options_leaves_title_none(self) -> None:
        ir = _parse(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            "\\narrate{Body.}\n"
        )
        assert ir.frames[0].title is None

    def test_unknown_option_still_errors(self) -> None:
        from scriba.core.errors import ValidationError

        with pytest.raises(ValidationError) as exc:
            _parse(
                "\\shape{a}{Array}{size=2, data=[1,2]}\n"
                "\\step[bogus=x]\n"
                "\\narrate{Body.}\n"
            )
        assert exc.value.code == "E1004"


class TestStepTitleRender:
    def _render(self, source: str, tmp_path: Path) -> str:
        tex_path = tmp_path / "in.tex"
        tex_path.write_text(source, encoding="utf-8")
        out_path = tmp_path / "out.html"
        render_file(tex_path, out_path)
        return out_path.read_text(encoding="utf-8")

    def test_title_renders_heading(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="step title"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            '\\step[title="Fill the base row"]\n'
            "\\narrate{Consider the array.}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        assert 'class="scriba-step-title"' in html_out
        assert "Fill the base row" in html_out

    def test_title_supersedes_svg_title(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="supersede"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            '\\step[title="Explicit Caption"]\n'
            "\\narrate{Narration body text here.}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        # The SVG <title> should be the explicit caption, NOT the
        # narration-derived "Narration body text here.".
        assert "<title>Explicit Caption</title>" in html_out

    def test_no_title_has_no_step_title_span(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="no title"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            "\\narrate{Consider the array.}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        # The CSS selector is always inlined; assert the *element* is absent.
        assert 'class="scriba-step-title"' not in html_out

    def test_no_narration_no_title_omits_svg_title(self, tmp_path: Path) -> None:
        """JudgeZone #10, Finding 4: a step with neither \\narrate nor
        \\step[title=...] has no natural-language content to name the SVG
        (no validator enforces either being present). Per the
        accessible-name policy, <title> must be omitted -- it must never
        fall back to the internal id="d" slug."""
        source = (
            '\\begin{animation}[id="d"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            "\\highlight{a.cell[0]}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        # This test renders through the full HTML-document pipeline, which
        # always emits one document-level <title>Scriba — ...</title> (see
        # render.py's HTML_TEMPLATE) -- unrelated to the SVG's own <title>.
        # Assert that's the *only* one (no SVG-level <title> got added), and
        # that the scene id never leaks in as a fake accessible name.
        assert html_out.count("<title>") == 1
        assert "<title>d</title>" not in html_out
