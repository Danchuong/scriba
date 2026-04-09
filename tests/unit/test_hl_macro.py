"""Tests for the \\hl{step-id}{tex} macro processor."""

from __future__ import annotations

import pytest

from scriba.animation.extensions.hl_macro import process_hl_macros


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
