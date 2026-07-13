"""JZ-17 residual — the viewBox must cover the SLOT layout, not the best frame.

``measure_scene_layout`` hands the emit loop fixed y-slots sized by each
primitive's TIMELINE-MAX bbox (``max_bbox``), but computed the viewBox height
as the max over frames of the SIMULTANEOUS per-frame stacked totals.  The two
disagree whenever two shapes reach their maxima on DIFFERENT frames — the
slotted layout is then taller than any single frame's total, and the bottom
shape's ink escapes the viewBox by exactly the other shape's growth-after-the-
critical-frame (cses-1192: the grid's ``position=above`` pill headroom peaks
on the last frame, the stack's depth on frame 4 → constant −13px clip on the
deepest frame, invariant under ``max_visible``).
"""

from __future__ import annotations

import re

from scriba.animation.primitives.layout import DESCENDER_RATIO
from scriba.animation.renderer import AnimationRenderer
from scriba.core.artifact import Block
from scriba.core.context import RenderContext

_CAPTION_FONT_PX = 11

_STAGE_SVG_RE = re.compile(
    r'<svg class="scriba-stage-svg" viewBox="0 0 ([\d.]+) ([\d.]+)".*?</svg>',
    re.S,
)

# One token per structural element we track: group open/close, rects, texts.
_TOKEN_RE = re.compile(
    r"<g\b[^>]*>|</g>|<rect\b[^>]*/>|<text\b[^>]*>.*?</text>",
    re.S,
)
_TRANSLATE_RE = re.compile(r"translate\(\s*[\-\d.]+[ ,]+([\-\d.]+)\s*\)")


def _ctx() -> RenderContext:
    # Static filmstrip: exactly one stage SVG per frame.
    return RenderContext(
        resource_resolver=lambda n: n,
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "static"},
        render_inline_tex=None,
    )


def _render(src: str) -> str:
    block = Block(start=0, end=len(src), kind="animation", raw=src)
    return AnimationRenderer().render_block(block, _ctx()).html


def _ink_bottoms(svg: str) -> tuple[float, float]:
    """(max rect bottom, max text glyph bottom) in stage coordinates.

    Walks the SVG token stream with a cumulative translate-y stack — the
    stage emits translate-only group transforms, so y accumulation is exact
    for rects; text bottoms add the caption descender below the last
    baseline (``y + sum(tspan dy)``).
    """
    depth_y = [0.0]
    rect_bottom = 0.0
    text_bottom = 0.0
    for tok in _TOKEN_RE.findall(svg):
        if tok.startswith("<g"):
            m = _TRANSLATE_RE.search(tok)
            depth_y.append(depth_y[-1] + (float(m.group(1)) if m else 0.0))
        elif tok.startswith("</g"):
            depth_y.pop()
        elif tok.startswith("<rect"):
            y = float(re.search(r'\by="([\-\d.]+)"', tok).group(1))
            h = float(re.search(r'\bheight="([\-\d.]+)"', tok).group(1))
            rect_bottom = max(rect_bottom, depth_y[-1] + y + h)
        else:  # <text>...</text>
            y_m = re.search(r'\by="([\-\d.]+)"', tok)
            if not y_m:
                continue
            dys = sum(float(d) for d in re.findall(r'<tspan[^>]*\bdy="([\d.]+)"', tok))
            glyph_bottom = (
                float(y_m.group(1)) + dys + DESCENDER_RATIO * _CAPTION_FONT_PX
            )
            text_bottom = max(text_bottom, depth_y[-1] + glyph_bottom)
    return rect_bottom, text_bottom


def _frames(html: str) -> list[tuple[float, str]]:
    """[(viewBox height, svg source), ...] per stage frame."""
    return [(float(m.group(2)), m.group(0)) for m in _STAGE_SVG_RE.finditer(html)]


# ---------------------------------------------------------------------------
# The bug: maxima on different frames -> bottom shape ink past the viewBox.
# ---------------------------------------------------------------------------


def test_rect_ink_inside_viewbox_when_maxima_disagree() -> None:
    """s1 peaks on frame 1, s2 on frame 2: the slotted layout places s2 below
    s1's TIMELINE-MAX slot, so s2's cells must still sit inside the viewBox on
    its own peak frame."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{s1}{Stack}{}" "\n"
        r"\shape{s2}{Stack}{}" "\n"
        r"\step" "\n"
        r'\apply{s1}{push="A"}' "\n"
        r'\apply{s1}{push="B"}' "\n"
        r'\apply{s1}{push="C"}' "\n"
        r"\narrate{s1 tall}" "\n"
        r"\step" "\n"
        r"\apply{s1}{pop=3}" "\n"
        r'\apply{s2}{push="X"}' "\n"
        r'\apply{s2}{push="Y"}' "\n"
        r'\apply{s2}{push="Z"}' "\n"
        r"\narrate{s2 tall}" "\n"
        r"\end{animation}"
    )
    frames = _frames(_render(src))
    assert len(frames) == 2
    for i, (vb_h, svg) in enumerate(frames):
        rect_bottom, _ = _ink_bottoms(svg)
        assert rect_bottom <= vb_h + 0.01, (
            f"frame {i}: rect ink bottom {rect_bottom} escapes viewBox "
            f"height {vb_h}"
        )


def test_bottom_caption_inside_viewbox_when_shape_above_grows_later() -> None:
    """cses-1192 mechanism, caption victim: the bottom shape carries a
    wrapped caption and peaks on frame 1; the shape ABOVE it peaks on
    frame 2 (pill headroom in the real file — plain growth here).  The
    caption rides the bottom of the slotted layout, so it must stay inside
    the cross-frame viewBox on the bottom shape's own peak frame."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{top}{Stack}{}" "\n"
        r'\shape{s}{Stack}{max_visible=8, label="a caption that wraps into '
        r'two display lines under the stack"}' "\n"
        r"\step" "\n"
        r'\apply{s}{push="(1,1)"}' "\n"
        r'\apply{s}{push="(1,2)"}' "\n"
        r'\apply{s}{push="(2,2)"}' "\n"
        r'\apply{s}{push="(2,3)"}' "\n"
        r"\narrate{deepest bottom stack}" "\n"
        r"\step" "\n"
        r"\apply{s}{pop=4}" "\n"
        r'\apply{top}{push="A"}' "\n"
        r'\apply{top}{push="B"}' "\n"
        r'\apply{top}{push="C"}' "\n"
        r"\narrate{the shape above grows after the bottom peak}" "\n"
        r"\end{animation}"
    )
    frames = _frames(_render(src))
    assert len(frames) == 2
    for i, (vb_h, svg) in enumerate(frames):
        rect_bottom, text_bottom = _ink_bottoms(svg)
        assert rect_bottom <= vb_h + 0.01, (
            f"frame {i}: rect ink bottom {rect_bottom} escapes viewBox {vb_h}"
        )
        assert text_bottom <= vb_h + 1.0, (
            f"frame {i}: caption glyph bottom {text_bottom} escapes "
            f"viewBox {vb_h}"
        )


# ---------------------------------------------------------------------------
# Stability: co-occurring maxima keep the old (best-frame) height exactly.
# ---------------------------------------------------------------------------


def test_viewbox_unchanged_when_maxima_cooccur() -> None:
    """A single growing shape (plus a static one) reaches every shape's max
    on the SAME frame — slot-sum equals the best-frame total, so the fix must
    not inflate the viewBox."""
    src = (
        r"\begin{animation}" "\n"
        r"\shape{g}{Grid}{rows=2, cols=3, data=[[1,2,3],[4,5,6]]}" "\n"
        r"\shape{s}{Stack}{}" "\n"
        r"\step" "\n"
        r'\apply{s}{push="A"}' "\n"
        r"\narrate{one}" "\n"
        r"\step" "\n"
        r'\apply{s}{push="B"}' "\n"
        r"\narrate{two}" "\n"
        r"\end{animation}"
    )
    frames = _frames(_render(src))
    assert len(frames) == 2
    vb_heights = {vb for vb, _ in frames}
    assert len(vb_heights) == 1
    vb_h = vb_heights.pop()
    # Slot layout equals the frame-2 simultaneous total here (both shapes at
    # max on the same frame), so the slot-sum fix must not inflate anything:
    # padding + grid max bbox + gap + stack max bbox (2 items) + padding.
    from scriba.animation._frame_renderer import _PADDING, _PRIMITIVE_GAP
    from scriba.animation.primitives.grid import GridPrimitive
    from scriba.animation.primitives.stack import Stack

    grid_h = GridPrimitive(
        "g", {"rows": 2, "cols": 3, "data": [[1, 2, 3], [4, 5, 6]]}
    ).bounding_box().height
    stack_h = Stack("s", {"items": ["A", "B"]}).bounding_box().height
    assert vb_h == 2 * _PADDING + grid_h + _PRIMITIVE_GAP + stack_h
