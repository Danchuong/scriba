"""Global diagram font-scale knob (--scriba-diagram-font-scale).

Consumers embedding Scriba output can resize all diagram text with one CSS
declaration. Every inline SVG font-size is emitted as
``calc(Npx * var(--scriba-diagram-font-scale, 1))`` so a host stylesheet can
scale it; the default of 1 leaves rendered sizes unchanged.
"""

from __future__ import annotations

from importlib.resources import files

import pytest

from scriba.animation.primitives._text_render import (
    _render_svg_text,
    _scaled_font_size,
)


def test_scaled_font_size_bare_number_gets_px() -> None:
    assert _scaled_font_size("11") == "calc(11px * var(--scriba-diagram-font-scale, 1))"


def test_scaled_font_size_preserves_existing_unit() -> None:
    assert _scaled_font_size("14px") == "calc(14px * var(--scriba-diagram-font-scale, 1))"
    assert _scaled_font_size("1.2em") == "calc(1.2em * var(--scriba-diagram-font-scale, 1))"


def test_render_svg_text_wraps_font_size_in_scale_calc() -> None:
    out = _render_svg_text("x", 0, 0, font_size="11")
    assert "font-size:calc(11px * var(--scriba-diagram-font-scale, 1))" in out
    # The bare, un-scaled form must not leak through.
    assert "font-size:11px" not in out


def test_render_svg_text_without_font_size_emits_no_inline_size() -> None:
    out = _render_svg_text("x", 0, 0)
    assert "font-size" not in out


@pytest.mark.parametrize(
    "css_file",
    ["scriba-scene-primitives.css"],
)
def test_css_defines_scale_var_and_uses_it(css_file: str) -> None:
    css = files("scriba.animation").joinpath("static", css_file).read_text()
    # The knob is declared with a default of 1...
    assert "--scriba-diagram-font-scale:" in css
    # ...and the role rules consume it so CSS-driven text scales too.
    assert "var(--scriba-diagram-font-scale, 1)" in css
