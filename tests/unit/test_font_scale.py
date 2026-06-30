"""Global diagram font-scale knob (--scriba-diagram-font-scale).

Consumers embedding Scriba output can resize all diagram text with one CSS
declaration. The scale is applied **uniformly to the whole ``<svg>`` viewport**
(its ``max-width`` carries the var); every SVG ``font-size`` stays a fixed px in
user units. Because text and geometry live in the same viewBox coordinate
space, scaling the viewport scales them by the same ratio, so text can never
overflow its shapes at any scale. The default of 1 leaves rendered output
unchanged.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest

from scriba.animation.primitives._text_render import (
    _render_svg_text,
    _scaled_font_size,
)


def test_scaled_font_size_bare_number_gets_px() -> None:
    # Bare px in user units — the scale is NOT applied per-text anymore.
    assert _scaled_font_size("11") == "11px"


def test_scaled_font_size_preserves_existing_unit() -> None:
    assert _scaled_font_size("14px") == "14px"
    assert _scaled_font_size("1.2em") == "1.2em"


def test_render_svg_text_emits_fixed_font_size_no_per_text_scale() -> None:
    out = _render_svg_text("x", 0, 0, font_size="11")
    # Fixed px in user units; no per-text scale calc.
    assert "font-size:11px" in out
    assert "var(--scriba-diagram-font-scale" not in out


def test_render_svg_text_without_font_size_emits_no_inline_size() -> None:
    out = _render_svg_text("x", 0, 0)
    assert "font-size" not in out


def test_svg_viewport_carries_the_scale_var() -> None:
    """The scale moved from per-text font-size to the ``<svg>`` max-width, so
    the whole viewport (text + geometry) scales uniformly. The emitter wraps the
    viewBox width in the scale var (verified end-to-end by the golden corpus)."""
    from scriba.animation import _frame_renderer

    src = Path(_frame_renderer.__file__).read_text()
    assert (
        "max-width:calc({vb_width}px * var(--scriba-diagram-font-scale, 1))" in src
    )


@pytest.mark.parametrize(
    "css_file",
    ["scriba-scene-primitives.css"],
)
def test_css_declares_scale_var_without_per_text_calc(css_file: str) -> None:
    css = files("scriba.animation").joinpath("static", css_file).read_text()
    # The knob is still declared with a default of 1 (feeds the <svg> max-width)...
    assert "--scriba-diagram-font-scale:" in css
    # ...but the per-text font-size rules no longer multiply by it.
    assert "font-size:" in css.replace(" ", "")  # rules still exist
    assert "* var(--scriba-diagram-font-scale" not in css
