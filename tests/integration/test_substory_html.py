"""Integration tests for substory HTML output."""

from __future__ import annotations

import re

from scriba.animation.emitter import (
    FrameData,
    SubstoryData,
    emit_animation_html,
    emit_substory_html,
)


def _make_frame(
    step: int,
    total: int,
    narration: str = "",
    substories: list[SubstoryData] | None = None,
) -> FrameData:
    return FrameData(
        step_number=step,
        total_frames=total,
        narration_html=narration,
        shape_states={},
        annotations=[],
        substories=substories,
    )


def _make_substory(
    title: str = "Sub-computation",
    substory_id: str = "substory1",
    depth: int = 1,
    frame_count: int = 2,
    nested: list[SubstoryData] | None = None,
) -> SubstoryData:
    frames = []
    for i in range(1, frame_count + 1):
        sub_frame_substories = nested if (i == 1 and nested) else None
        frames.append(
            _make_frame(i, frame_count, f"sub narration {i}", sub_frame_substories),
        )
    return SubstoryData(
        title=title,
        substory_id=substory_id,
        depth=depth,
        frames=frames,
    )


class TestSubstoryHtmlOutput:
    """Integration tests for substory HTML rendering."""

    def test_substory_renders_section(self):
        """Substory renders nested <section class="scriba-substory">."""
        sub = _make_substory()
        frames = [_make_frame(1, 1, "parent narration", substories=[sub])]
        html = emit_animation_html("test-scene", frames, {})
        assert 'class="scriba-substory"' in html
        assert "scriba-substory-widget" in html

    def test_substory_has_widget_id(self):
        """Substory has a unique widget ID."""
        sub = _make_substory(substory_id="substory1", frame_count=2)
        frames = [_make_frame(1, 1, "", substories=[sub])]
        html = emit_animation_html("test-scene", frames, {})
        assert "scriba-substory-widget" in html

    def test_substory_has_controls(self):
        """Substory has Prev/Next controls."""
        sub = _make_substory()
        frames = [_make_frame(1, 1, "", substories=[sub])]
        html = emit_animation_html("test-scene", frames, {})
        assert "scriba-substory-controls" in html

    def test_substory_depth_attribute(self):
        """data-substory-depth attribute is correct."""
        sub = _make_substory(depth=1)
        frames = [_make_frame(1, 1, "", substories=[sub])]
        html = emit_animation_html("test-scene", frames, {})
        assert 'data-substory-depth="1"' in html

    def test_substory_aria_label_includes_title(self):
        """aria-label includes title."""
        sub = _make_substory(title="DP trace")
        frames = [_make_frame(1, 1, "", substories=[sub])]
        html = emit_animation_html("test-scene", frames, {})
        assert 'aria-label="Sub-computation: DP trace"' in html

    def test_parent_frame_content_preserved(self):
        """Parent frame content before substory is preserved."""
        sub = _make_substory()
        frames = [_make_frame(1, 1, "parent text here", substories=[sub])]
        html = emit_animation_html("test-scene", frames, {})
        assert "parent text here" in html
        # Parent narration should appear before substory
        parent_narr_pos = html.index("parent text here")
        substory_pos = html.index("scriba-substory")
        assert parent_narr_pos < substory_pos

    def test_nested_substory_depth_2(self):
        """Nested substory (depth 2) — outer substory renders."""
        inner_sub = _make_substory(
            title="inner", substory_id="inner1", depth=2, frame_count=1,
        )
        outer_sub = _make_substory(
            title="outer", substory_id="outer1", depth=1, frame_count=1,
            nested=[inner_sub],
        )
        frames = [_make_frame(1, 1, "", substories=[outer_sub])]
        html = emit_animation_html("test-scene", frames, {})
        # Outer substory renders
        assert 'data-substory-depth="1"' in html
        assert 'data-substory-id="outer1"' in html
        assert "scriba-substory-widget" in html

    def test_substory_step_label_format(self):
        """Substory step counter uses 'Sub-step N / M' format."""
        sub = _make_substory(frame_count=3)
        frames = [_make_frame(1, 1, "", substories=[sub])]
        html = emit_animation_html("test-scene", frames, {})
        assert "Sub-step 1 / 3" in html
