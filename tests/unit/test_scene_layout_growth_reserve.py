"""Finding B (twin-drift): structural growth must be reserved by stacking.

``compute_stable_viewbox`` replays push/pop on deep copies so the viewBox
covers the grown extent — but ``_build_reserved_offsets`` measured the real
primitives at their initial state and never replayed ``apply_params``. A
Stack growing above an Array kept the Array pinned at the initial-state
offset, overlapping the grown stack by up to 90px while the viewBox stayed
correct.

Contract: the downstream primitive sits below the grower's painted extent
in EVERY frame, and its offset is frame-stable (R-32.2).
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext

_DOC = r"""
\begin{animation}[id="growla"]
\shape{s}{Stack}{items=[1]}
\shape{a}{Array}{size=3, data=[7,8,9]}
\step
\narrate{Một.}
\step
\apply{s}{push="10"}
\narrate{Hai.}
\step
\apply{s}{push="20"}
\apply{s}{push="30"}
\narrate{Ba.}
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


def _stack_bottom_and_array_y(svg: str) -> tuple[float, float]:
    """Painted bottom of the first primitive group vs the second's offset."""
    parts = re.split(r'<g transform="translate\([\d.]+,([\d.]+)\)">', svg)
    # parts: [pre, y1, body1, y2, body2...]
    assert len(parts) >= 5, "expected two stacked primitive groups"
    y1, body1, y2 = float(parts[1]), parts[2], float(parts[3])
    bottoms = [
        float(m.group(1)) + float(m.group(2))
        for m in re.finditer(r'<rect[^>]* y="([-\d.]+)"[^>]* height="([\d.]+)"', body1)
    ]
    assert bottoms, "no rects found in the stack group"
    return y1 + max(bottoms), y2


class TestGrowthReserved:
    def test_growing_stack_never_overlaps_array(self, html: str) -> None:
        for i, svg in enumerate(_frames(html), 1):
            stack_bottom, array_y = _stack_bottom_and_array_y(svg)
            assert array_y >= stack_bottom - 0.01, (
                f"frame {i}: array offset {array_y} sits inside the stack "
                f"(painted bottom {stack_bottom:.1f})"
            )

    def test_downstream_offset_stable_across_frames(self, html: str) -> None:
        ys = set()
        for svg in _frames(html):
            ys.add(_stack_bottom_and_array_y(svg)[1])
        assert len(ys) == 1, f"downstream offset shifted between frames: {sorted(ys)}"
