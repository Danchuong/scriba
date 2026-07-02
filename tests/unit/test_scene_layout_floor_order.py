"""Scene viewBox must be measured AFTER the cross-frame arrow floor.

Measured on the user's doc: the stitcher computed the stable viewBox
BEFORE ``_apply_min_arrow_above`` and the reserved offsets AFTER it.
The floor lifts every frame's above-lane to the cross-frame max, so a
frame whose pill sits in the BELOW lane (below-overhang, no own above
need) becomes ``base + floor_above + below_overhang`` — a combination
taller than any single un-floored frame. Grid per-frame heights went
[229,229,253,253,267] → viewBox 500, but post-floor [267,267,291,...] →
offsets placed the watch at y=323, needing 524. The watch caption
(painted flush with its bbox bottom) landed 12px past the viewBox and
was clipped by ``overflow:hidden``, with the floating controls pill
covering the surviving sliver.

Contract: for every frame, every primitive's translate offset plus its
tallest post-floor bounding box fits inside the declared viewBox.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext

_DOC = r"""
\begin{animation}[id="combo"]
\shape{g}{Grid}{rows=5, cols=5}
\shape{w}{VariableWatch}{names=[m, base, d, val], label="f = nền + d"}
\step
\annotate{g.cell[4][2]}{label="đi phải dọc đáy", arrow_from="g.cell[4][0]", color=good, ephemeral=true}
\narrate{Bước một.}
\step
\annotate{g.cell[1][2]}{label="m chẵn: vào từ trên-phải, xuống rồi trái", arrow_from="g.cell[2][2]", color=good, ephemeral=true}
\narrate{Bước hai.}
\end{animation}
"""


@pytest.fixture(scope="module")
def html() -> str:
    blocks = detect_animation_blocks(_DOC)
    assert blocks
    r = AnimationRenderer()
    ctx = RenderContext(resource_resolver=lambda n: n)
    return r.render_block(blocks[0], ctx).html


def _frames(html: str) -> list[str]:
    return re.findall(r"<svg class=\"scriba-stage-svg\"[^>]*>.*?</svg>", html, re.S)


class TestViewBoxCoversFlooredLayout:
    def test_last_primitive_fits_every_frame(self, html: str) -> None:
        for svg in _frames(html):
            vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
            assert vb
            vb_h = int(vb.group(2))
            # the watch is the last stacked primitive; its caption paints
            # flush with its bbox bottom, so translate_y + caption baseline
            # + descender must stay inside the viewBox
            groups = re.findall(r'<g transform="translate\([\d.]+,([\d.]+)\)">', svg)
            assert groups
            watch_y = float(groups[-1])
            cap = re.search(
                r'<text class="scriba-primitive-label"[^>]*y="([\d.]+)"', svg
            )
            assert cap, "watch caption missing"
            # captions of both primitives match; take the LAST (watch's)
            caps = re.findall(
                r'<text class="scriba-primitive-label"[^>]*y="([\d.]+)"', svg
            )
            baseline = watch_y + float(caps[-1])
            assert baseline + 6 <= vb_h + 0.01, (
                f"caption paints at {baseline + 6:.1f} but viewBox is {vb_h} "
                f"(watch at y={watch_y})"
            )
