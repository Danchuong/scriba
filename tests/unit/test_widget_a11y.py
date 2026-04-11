"""Accessibility tests for the animation widget (Wave 7.5).

Covers:
- aria-label on Prev/Next buttons in the main widget
- aria-label on Prev/Next buttons in substory widgets
- prefers-reduced-motion coverage in the shipped CSS asset

These tests intentionally work against the emitted HTML string and the
static CSS asset file so that they remain insulated from the internal
primitive/parser machinery.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from typing import Any

import pytest

from scriba.animation.emitter import (
    FrameData,
    SubstoryData,
    emit_interactive_html,
)


# ---------------------------------------------------------------------------
# Minimal primitive stub (mirrors the shape used by the emitter tests)
# ---------------------------------------------------------------------------


@dataclass
class _StubPrimitive:
    shape_name: str
    primitive_type: str = "array"
    _bbox: tuple[float, float, float, float] = (0, 0, 200, 40)

    def bounding_box(self) -> tuple[float, float, float, float]:
        return self._bbox

    def emit_svg(
        self,
        state: dict[str, dict[str, Any]] | None = None,
        annotations: list[dict[str, Any]] | None = None,
        *,
        render_inline_tex: Any = None,
    ) -> str:
        return (
            f'<g data-primitive="{self.primitive_type}"'
            f' data-shape="{self.shape_name}"></g>'
        )


def _make_frame(step: int = 1, total: int = 2, narration: str = "") -> FrameData:
    return FrameData(
        step_number=step,
        total_frames=total,
        narration_html=narration,
        shape_states={},
        annotations=[],
    )


def _make_substory_frame(
    step: int = 1, total: int = 2, narration: str = ""
) -> FrameData:
    return FrameData(
        step_number=step,
        total_frames=total,
        narration_html=narration,
        shape_states={},
        annotations=[],
    )


@pytest.fixture
def widget_html() -> str:
    prim = _StubPrimitive(shape_name="a")
    frames = [_make_frame(step=1, total=2), _make_frame(step=2, total=2)]
    return emit_interactive_html("a11y-test", frames, {"a": prim})


@pytest.fixture
def widget_html_with_substory() -> str:
    prim = _StubPrimitive(shape_name="a")
    sub_frames = [
        _make_substory_frame(step=1, total=2, narration="sub 1"),
        _make_substory_frame(step=2, total=2, narration="sub 2"),
    ]
    sub = SubstoryData(
        title="inner loop",
        substory_id="sub1",
        depth=1,
        frames=sub_frames,
    )
    top = FrameData(
        step_number=1,
        total_frames=1,
        narration_html="",
        shape_states={},
        annotations=[],
        substories=[sub],
    )
    return emit_interactive_html("a11y-test-sub", [top], {"a": prim})


# ---------------------------------------------------------------------------
# Top-level widget aria-label assertions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_prev_button_has_aria_label(widget_html: str) -> None:
    assert 'class="scriba-btn-prev"' in widget_html
    assert 'aria-label="Previous step"' in widget_html


@pytest.mark.unit
def test_next_button_has_aria_label(widget_html: str) -> None:
    assert 'class="scriba-btn-next"' in widget_html
    assert 'aria-label="Next step"' in widget_html


@pytest.mark.unit
def test_prev_button_keeps_visible_text(widget_html: str) -> None:
    # Visible text is preserved for sighted users; aria-label adds a
    # screen-reader-friendly description without replacing it.
    assert ">Prev</button>" in widget_html


@pytest.mark.unit
def test_next_button_keeps_visible_text(widget_html: str) -> None:
    assert ">Next</button>" in widget_html


# ---------------------------------------------------------------------------
# Substory widget aria-label assertions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_substory_prev_button_has_aria_label(
    widget_html_with_substory: str,
) -> None:
    assert 'aria-label="Previous sub-step"' in widget_html_with_substory


@pytest.mark.unit
def test_substory_next_button_has_aria_label(
    widget_html_with_substory: str,
) -> None:
    assert 'aria-label="Next sub-step"' in widget_html_with_substory


# ---------------------------------------------------------------------------
# prefers-reduced-motion coverage
# ---------------------------------------------------------------------------


def _read_css_asset(name: str) -> str:
    static = files("scriba.animation").joinpath("static")
    return (static / name).read_text(encoding="utf-8")


@pytest.mark.unit
def test_scene_primitives_has_reduced_motion_block() -> None:
    css = _read_css_asset("scriba-scene-primitives.css")
    assert "@media (prefers-reduced-motion: reduce)" in css


@pytest.mark.unit
def test_reduced_motion_disables_widget_button_transitions() -> None:
    """The reduced-motion block explicitly neutralises widget button motion.

    We look for the targeted rule introduced in Wave 7.5, not just the
    broad universal-selector fallback, so that future regressions which
    drop the explicit selectors are caught.
    """
    css = _read_css_asset("scriba-scene-primitives.css")
    # Find the @media (prefers-reduced-motion: reduce) block boundaries.
    marker = "@media (prefers-reduced-motion: reduce)"
    start = css.find(marker)
    assert start != -1, "reduced-motion media block missing"
    # Capture from start to a reasonable end — the block is the tail of
    # the file in the current layout, but we slice defensively to the
    # next top-level @media or EOF.
    tail = css[start:]
    assert ".scriba-btn-prev" in tail
    assert ".scriba-btn-next" in tail
    assert "transition: none !important" in tail
    assert "animation: none !important" in tail


@pytest.mark.unit
def test_animation_css_has_reduced_motion_block() -> None:
    css = _read_css_asset("scriba-animation.css")
    assert "@media (prefers-reduced-motion: reduce)" in css
