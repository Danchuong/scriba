"""Tests that the filmstrip <figure> always has a non-empty aria-label.

Wave 8 Round A — P7 A01 regression guard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from scriba.animation.emitter import FrameData, emit_animation_html


# ---------------------------------------------------------------------------
# Minimal stub primitive (mirrors test_emitter_a11y.py pattern)
# ---------------------------------------------------------------------------


@dataclass
class _Stub:
    shape_name: str
    primitive_type: str = "array"

    def bounding_box(self) -> tuple[float, float, float, float]:
        return (0, 0, 200, 40)

    def emit_svg(
        self,
        state: dict[str, Any] | None = None,
        annotations: list[Any] | None = None,
        *,
        render_inline_tex: Any = None,
    ) -> str:
        return f'<g data-shape="{self.shape_name}"></g>'

    def set_state(self, suffix: str, state: str) -> None:
        pass

    def set_value(self, suffix: str, value: str) -> None:
        pass

    def set_label(self, suffix: str, label: str) -> None:
        pass

    def set_annotations(self, anns: list[Any]) -> None:
        pass

    def set_min_arrow_above(self, h: float) -> None:
        pass


def _make_frame(label: str = "", step_number: int = 1) -> FrameData:
    return FrameData(
        step_number=step_number,
        total_frames=1,
        label=label,
        narration_html="<p>narration</p>",
        shape_states={},
        annotations=[],
        substories=[],
    )


_PRIMITIVES = {"arr": _Stub("arr")}


# ---------------------------------------------------------------------------
# A01: empty-frames path must NOT emit aria-label=""
# ---------------------------------------------------------------------------


def test_empty_frames_aria_label_not_empty():
    """Filmstrip with zero frames must use aria-label='Animation', not empty."""
    html = emit_animation_html(
        scene_id="test-empty",
        frames=[],
        primitives=_PRIMITIVES,
    )
    assert 'aria-label=""' not in html, (
        "Empty filmstrip emits aria-label='', should be 'Animation'"
    )
    assert 'aria-label="Animation"' in html, (
        "Empty filmstrip must fall back to aria-label='Animation'"
    )


# ---------------------------------------------------------------------------
# A01: non-empty frames with no label must also fall back to "Animation"
# ---------------------------------------------------------------------------


def test_frames_without_label_aria_label_not_empty():
    """Filmstrip with frames but no frame labels must use aria-label='Animation'."""
    frames = [_make_frame(label="", step_number=1)]
    html = emit_animation_html(
        scene_id="test-nolabel",
        frames=frames,
        primitives=_PRIMITIVES,
    )
    assert 'aria-label=""' not in html, (
        "Filmstrip with unlabelled frames emits aria-label='', should be 'Animation'"
    )
    assert 'aria-label="Animation"' in html, (
        "Unlabelled frames must fall back to aria-label='Animation'"
    )


# ---------------------------------------------------------------------------
# A01: when a frame does have a label, it takes precedence
# ---------------------------------------------------------------------------


def test_frames_with_label_uses_frame_label():
    """Filmstrip with a labelled frame must use that label, not 'Animation'."""
    frames = [_make_frame(label="Binary Search", step_number=1)]
    html = emit_animation_html(
        scene_id="test-withlabel",
        frames=frames,
        primitives=_PRIMITIVES,
    )
    assert 'aria-label="Binary Search"' in html, (
        "Filmstrip with labelled frame must use that label as aria-label"
    )
