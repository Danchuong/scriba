"""Tests for the \\hl{step-id}{tex} macro processor."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.extensions.hl_macro import process_hl_macros
from scriba.core.errors import ScribaError

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


class TestBasicReplacement:
    def test_single_hl_produces_span(self) -> None:
        result = process_hl_macros(
            r"\hl{step1}{x^2}", scene_id="s1"
        )
        assert '<span class="scriba-hl"' in result
        assert 'data-hl-step="step1"' in result
        assert "x^2" in result

    def test_no_hl_returns_text_unchanged(self) -> None:
        text = "Just plain narration with no macros."
        assert process_hl_macros(text, scene_id="s1") == text

    def test_mixed_text_and_hl(self) -> None:
        text = r"Consider \hl{s1}{x} in the equation."
        result = process_hl_macros(text, scene_id="sc")
        assert result.startswith("Consider ")
        assert result.endswith(" in the equation.")
        assert 'data-hl-step="s1"' in result


class TestMultipleMacros:
    def test_two_hl_in_same_narration(self) -> None:
        text = r"We add \hl{a}{x} and \hl{b}{y}."
        result = process_hl_macros(text, scene_id="s1")
        assert result.count("scriba-hl") == 2
        assert 'data-hl-step="a"' in result
        assert 'data-hl-step="b"' in result


class TestRenderCallback:
    def test_callback_is_invoked(self) -> None:
        def fake_katex(tex: str) -> str:
            return f'<span class="katex">{tex}</span>'

        result = process_hl_macros(
            r"\hl{s1}{x^2}", scene_id="s1", render_inline_tex=fake_katex
        )
        assert '<span class="katex">x^2</span>' in result

    def test_without_callback_html_escapes(self) -> None:
        result = process_hl_macros(
            r"\hl{s1}{<b>bad</b>}", scene_id="s1"
        )
        assert "&lt;b&gt;bad&lt;/b&gt;" in result
        assert "<b>" not in result


class TestXssSafety:
    def test_step_id_is_attribute_escaped(self) -> None:
        result = process_hl_macros(
            r'\hl{"><script>alert(1)</script>}{x}', scene_id="s1"
        )
        assert "<script>" not in result
        assert "&quot;" in result
        assert "&#x27;" in result or "&gt;" in result

    def test_tex_body_escaped_when_no_callback(self) -> None:
        result = process_hl_macros(
            r"\hl{s1}{<img onerror=alert(1)>}", scene_id="s1"
        )
        assert "<img" not in result
        assert "&lt;img" in result


class TestNestedBraces:
    def test_one_level_of_nesting(self) -> None:
        result = process_hl_macros(
            r"\hl{s1}{x^{2}}", scene_id="s1"
        )
        assert "x^{2}" in result or "x^{2}" in result

    def test_simple_tex_with_subscript(self) -> None:
        result = process_hl_macros(
            r"\hl{s2}{a_{i}}", scene_id="s1"
        )
        assert 'data-hl-step="s2"' in result


class TestEdgeCases:
    def test_empty_step_id(self) -> None:
        """Empty step-id should not match the regex (requires [^}]+)."""
        text = r"\hl{}{x}"
        result = process_hl_macros(text, scene_id="s1")
        # The regex requires at least one char for step-id
        assert "scriba-hl" not in result

    def test_empty_tex_body(self) -> None:
        result = process_hl_macros(r"\hl{s1}{}", scene_id="s1")
        assert 'data-hl-step="s1"' in result
        assert "></span>" in result


class TestStepIdValidation:
    """E1321 — unknown step-id raises instead of silently emitting a span."""

    def test_unknown_step_id_raises_e1321(self) -> None:
        with pytest.raises(AnimationError) as exc:
            process_hl_macros(
                r"\hl{nonexistent}{x}",
                scene_id="s1",
                valid_step_ids=frozenset({"init", "step1"}),
            )
        assert exc.value.code == "E1321"
        assert "nonexistent" in str(exc.value)

    def test_known_label_passes(self) -> None:
        result = process_hl_macros(
            r"\hl{init}{x}",
            scene_id="s1",
            valid_step_ids=frozenset({"init", "step1"}),
        )
        assert 'data-hl-step="init"' in result

    def test_implicit_step_n_passes(self) -> None:
        result = process_hl_macros(
            r"\hl{step1}{x}",
            scene_id="s1",
            valid_step_ids=frozenset({"init", "step1"}),
        )
        assert 'data-hl-step="step1"' in result

    def test_no_valid_set_skips_validation(self) -> None:
        # Backward-compatible: when valid_step_ids is None, no validation.
        result = process_hl_macros(
            r"\hl{whatever}{x}", scene_id="s1", valid_step_ids=None
        )
        assert 'data-hl-step="whatever"' in result

    def test_e1321_hint_suggests_close_match(self) -> None:
        with pytest.raises(AnimationError) as exc:
            process_hl_macros(
                r"\hl{inot}{x}",
                scene_id="s1",
                valid_step_ids=frozenset({"init", "fill"}),
            )
        assert exc.value.code == "E1321"
        assert exc.value.hint is not None
        assert "init" in exc.value.hint


class TestHlOutsideNarrate:
    """E1320 — bare \\hl as a standalone animation-body command.

    A standalone ``\\hl`` (outside any ``\\narrate{...}`` body) must raise the
    documented **E1320** ("`\\hl` is only valid inside a `\\narrate{...}`
    body") rather than the generic E1006 "unknown command" the parser used to
    emit before any semantic check ran. See docs §5.13 / §15.
    """

    def _render(self, source: str, tmp_path: Path) -> ScribaError:
        tex_path = tmp_path / "in.tex"
        tex_path.write_text(source, encoding="utf-8")
        out_path = tmp_path / "out.html"
        with pytest.raises(ScribaError) as exc:
            render_file(tex_path, out_path)
        return exc.value

    def test_standalone_hl_raises_e1320(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="hl outside narrate"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step[label=init]\n"
            "\\hl{init}{stray}\n"
            "\\narrate{Body.}\n"
            "\\end{animation}\n"
        )
        err = self._render(source, tmp_path)
        assert err.code == "E1320", f"expected E1320, got {err.code}"
        assert err.code != "E1006"

    def test_hl_inside_narrate_still_renders(self, tmp_path: Path) -> None:
        """A legitimate \\hl inside \\narrate{...} must keep rendering."""
        source = (
            '\\begin{animation}[id="d", label="hl inside narrate"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step[label=init]\n"
            "\\narrate{Consider \\hl{init}{x} here.}\n"
            "\\end{animation}\n"
        )
        tex_path = tmp_path / "ok.tex"
        tex_path.write_text(source, encoding="utf-8")
        out_path = tmp_path / "ok.html"
        # Must not raise — valid \hl flows through process_hl_macros.
        render_file(tex_path, out_path)
        html_out = out_path.read_text(encoding="utf-8")
        assert 'data-hl-step="init"' in html_out
