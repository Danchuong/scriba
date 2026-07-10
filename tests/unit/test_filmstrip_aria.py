"""Tests that the filmstrip <figure> always has a non-empty aria-label.

Wave 8 Round A — P7 A01 regression guard.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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


def _make_frame(
    label: str = "",
    step_number: int = 1,
    title: str | None = None,
    narration_html: str = "<p>narration</p>",
) -> FrameData:
    return FrameData(
        step_number=step_number,
        total_frames=1,
        label=label,
        narration_html=narration_html,
        shape_states={},
        annotations=[],
        substories=[],
        title=title,
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


# ---------------------------------------------------------------------------
# JudgeZone #10 / R-15: the SVG's own <title> content policy.  R-15 cites
# this file as its test ref, but until now nothing here asserted on
# <title> content itself -- only on the figure's aria-label attribute.
# Accessible names come from author-supplied natural language only; the
# internal scene id must never surface as a <title>.
# ---------------------------------------------------------------------------


def test_frame_with_title_uses_it_as_svg_title():
    """An explicit \\step[title=...] (threaded via FrameData.title) names
    the frame's own SVG <title>, not just the filmstrip figure."""
    frames = [_make_frame(title="Fill the base row")]
    html = emit_animation_html(
        scene_id="internal-slug-y",
        frames=frames,
        primitives=_PRIMITIVES,
    )
    assert "<title>Fill the base row</title>" in html
    assert "<title>internal-slug-y</title>" not in html


def test_frame_without_title_or_narration_omits_svg_title():
    """No title and no narration text means no natural-language content
    exists to name the SVG. <title> must be omitted entirely -- it must
    never fall back to the internal scene id."""
    frames = [_make_frame(title=None, narration_html="")]
    html = emit_animation_html(
        scene_id="internal-slug-y",
        frames=frames,
        primitives=_PRIMITIVES,
    )
    assert "<title>" not in html
