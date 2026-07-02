"""Finding A (twin-drift): mid-timeline captions must be reserved by layout.

``\\apply{p}{label=…}`` is applied only in the emit loop — the scene stores
the caption in ``ShapeTargetState.label`` and excludes it from
``apply_params``, so neither measurement pass (viewBox, reserved offsets)
ever saw it. A caption appearing after frame 1 painted past the declared
viewBox (measured: baseline 151 vs viewBox 148) and overlapped the next
stacked primitive by 28px.

Contract: every frame's caption paints inside the viewBox, and the next
primitive is stacked below the caption block.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext

_DOC = r"""
\begin{animation}[id="capla"]
\shape{g}{Grid}{rows=2, cols=3}
\shape{a}{Array}{size=3}
\step
\narrate{Chưa có chú thích.}
\step
\apply{g}{label="chú thích xuất hiện muộn, tương đối dài để phải xuống dòng"}
\apply{a}{label="chú thích muộn trên primitive cuối cùng tràn qua đáy viewBox"}
\narrate{Chú thích xuất hiện.}
\end{animation}
"""


@pytest.fixture(scope="module", params=["interactive", "static"])
def html(request) -> str:
    blocks = detect_animation_blocks(_DOC)
    assert blocks
    r = AnimationRenderer()
    ctx = RenderContext(
        resource_resolver=lambda n: n,
        metadata={"output_mode": request.param},
    )
    return r.render_block(blocks[0], ctx).html


def _frames(html: str) -> list[str]:
    return re.findall(r"<svg class=\"scriba-stage-svg\"[^>]*>.*?</svg>", html, re.S)


class TestLateCaptionReserved:
    def test_late_caption_fits_viewbox(self, html: str) -> None:
        for svg in _frames(html):
            caps = re.findall(
                r'<text class="scriba-primitive-label"[^>]*y="([\d.]+)"', svg
            )
            if not caps:
                continue  # caption-less frame
            vb_h = int(re.search(r'viewBox="0 0 \d+ (\d+)"', svg).group(1))
            gys = re.findall(r'<g transform="translate\([\d.]+,([\d.]+)\)">', svg)
            # captions appear in group order; the array's (last group, last
            # caption) is the one that can cross the viewBox bottom
            baseline = float(gys[-1]) + float(caps[-1])
            assert baseline + 6 <= vb_h + 0.01, (
                f"caption paints at {baseline + 6:.1f} but viewBox is {vb_h}"
            )

    def test_late_caption_not_covered_by_next_primitive(self, html: str) -> None:
        for svg in _frames(html):
            caps = re.findall(
                r'<text class="scriba-primitive-label"[^>]*y="([\d.]+)"', svg
            )
            if not caps:
                continue
            gys = re.findall(r'<g transform="translate\([\d.]+,([\d.]+)\)">', svg)
            grid_y, array_y = float(gys[0]), float(gys[1])
            caption_bottom = grid_y + float(caps[0]) + 6
            assert array_y >= caption_bottom - 0.01, (
                f"next primitive at y={array_y} overlaps the caption block "
                f"ending at {caption_bottom:.1f}"
            )
