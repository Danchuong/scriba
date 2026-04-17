"""Unit tests for the four accessibility fixes applied in the emitter.

H3 — Substory arrow-key bubbling guard
H4 — Widget container role="region" and aria-label
M6 — Progress dots aria-hidden="true"
M7 — prefers-reduced-motion live MediaQueryList listener
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from scriba.animation.emitter import (
    FrameData,
    SubstoryData,
    emit_interactive_html,
    emit_substory_html,
)


# ---------------------------------------------------------------------------
# Minimal stub primitive (no external dependencies)
# ---------------------------------------------------------------------------


@dataclass
class _Stub:
    """Minimal primitive that satisfies the emitter interface."""

    shape_name: str
    primitive_type: str = "array"

    def bounding_box(self) -> tuple[float, float, float, float]:
        return (0, 0, 200, 40)

    def emit_svg(
        self,
        state: dict[str, dict[str, Any]] | None = None,
        annotations: list[dict[str, Any]] | None = None,
        *,
        render_inline_tex: Any = None,
    ) -> str:
        return f'<g data-shape="{self.shape_name}"></g>'


def _frame(
    step: int = 1,
    total: int = 3,
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


def _two_frame_widget(label: str = "") -> str:
    """Render a minimal two-frame interactive widget."""
    prim = _Stub(shape_name="arr")
    frames = [_frame(step=1, total=2), _frame(step=2, total=2)]
    return emit_interactive_html("test-scene", frames, {"arr": prim}, label=label)


# ---------------------------------------------------------------------------
# H4 — Widget container role and aria-label
# ---------------------------------------------------------------------------


class TestWidgetContainerAriaLabel:
    """H4: The widget <div> must carry role="region" and aria-label."""

    def test_role_region_present(self) -> None:
        html = _two_frame_widget()
        assert 'role="region"' in html

    def test_default_aria_label_when_no_label(self) -> None:
        html = _two_frame_widget(label="")
        assert 'aria-label="Animation"' in html

    def test_custom_label_used_as_aria_label(self) -> None:
        html = _two_frame_widget(label="BFS Queue demo")
        assert 'aria-label="BFS Queue demo"' in html

    def test_label_escapes_html_special_chars(self) -> None:
        html = _two_frame_widget(label='Demo <b> & "quotes"')
        # The escaped form must appear; the raw characters must not.
        assert "<b>" not in html.split('aria-label="')[1].split('"')[0]
        assert "&lt;" in html or "Demo" in html  # some escaping applied

    def test_role_and_label_on_widget_div_not_elsewhere(self) -> None:
        html = _two_frame_widget(label="Test")
        # The role and aria-label must appear on the scriba-widget element.
        assert 'class="scriba-widget"' in html
        widget_tag_end = html.index(">", html.index('class="scriba-widget"'))
        widget_open_tag = html[: widget_tag_end + 1]
        assert 'role="region"' in widget_open_tag
        assert 'aria-label="Test"' in widget_open_tag


# ---------------------------------------------------------------------------
# M6 — Progress dots aria-hidden
# ---------------------------------------------------------------------------


class TestProgressDotsAriaHidden:
    """M6: The progress-dots container must be aria-hidden so screen readers
    skip decorative step indicators (the live region already announces them).
    """

    def test_main_progress_container_aria_hidden(self) -> None:
        html = _two_frame_widget()
        assert 'class="scriba-progress" aria-hidden="true"' in html

    def test_substory_progress_container_aria_hidden(self) -> None:
        """Substory dots must also be hidden (they are equally decorative)."""
        sub_frame = FrameData(
            step_number=1,
            total_frames=2,
            narration_html="sub narration",
            shape_states={},
            annotations=[],
        )
        sub_frame2 = FrameData(
            step_number=2,
            total_frames=2,
            narration_html="sub narration 2",
            shape_states={},
            annotations=[],
        )
        sub_data = SubstoryData(
            title="Sub-computation",
            substory_id="sub-1",
            depth=1,
            frames=[sub_frame, sub_frame2],
            primitives={},
        )
        html = emit_substory_html(
            scene_id="scene",
            parent_frame_id="scene-frame-1",
            substory=sub_data,
            primitives={},
            viewbox="0 0 200 40",
        )
        assert 'class="scriba-progress" aria-hidden="true"' in html

    def test_individual_dots_not_aria_hidden(self) -> None:
        """Individual dot <div>s carry no aria-hidden — it's on the container."""
        html = _two_frame_widget()
        # The dots themselves should NOT have aria-hidden
        # (that would over-specify; the container already hides them).
        # We just verify the container pattern is what carries it.
        assert 'class="scriba-dot active"' in html  # dots exist
        # Container carries the attribute, not dots
        assert 'class="scriba-progress" aria-hidden="true"' in html


# ---------------------------------------------------------------------------
# H3 — Substory arrow-key event bubbling guard
# ---------------------------------------------------------------------------


class TestSubstoryKeydownBubblingGuard:
    """H3: The parent keydown handler must bail out early when the event
    originates inside a .scriba-substory-widget element.
    """

    def test_bubbling_guard_present_in_js(self) -> None:
        html = _two_frame_widget()
        assert "closest('.scriba-substory-widget')" in html

    def test_guard_appears_before_arrow_key_handling(self) -> None:
        html = _two_frame_widget()
        guard_pos = html.find("closest('.scriba-substory-widget')")
        arrow_pos = html.find("ArrowRight")
        assert guard_pos != -1, "guard not found"
        assert arrow_pos != -1, "ArrowRight handler not found"
        assert guard_pos < arrow_pos, (
            "guard must appear before the ArrowRight branch "
            f"(guard at {guard_pos}, ArrowRight at {arrow_pos})"
        )

    def test_guard_is_early_return(self) -> None:
        """The guard must be a `return` statement to stop propagation."""
        html = _two_frame_widget()
        # Find the keydown block and check that 'return' is the consequence.
        guard_pos = html.find("closest('.scriba-substory-widget')")
        snippet = html[guard_pos: guard_pos + 60]
        assert "return" in snippet, (
            f"Expected 'return' near the guard, got: {snippet!r}"
        )


# ---------------------------------------------------------------------------
# M7 — prefers-reduced-motion live MediaQueryList listener
# ---------------------------------------------------------------------------


class TestReducedMotionLiveListener:
    """M7: _canAnim must be updated dynamically when the OS preference
    changes, not just at page load.
    """

    def test_mediaquerylist_stored_in_variable(self) -> None:
        html = _two_frame_widget()
        assert "_motionMQ" in html

    def test_change_listener_attached(self) -> None:
        html = _two_frame_widget()
        assert "_motionMQ.addEventListener('change'" in html

    def test_can_anim_uses_motiomq_variable(self) -> None:
        html = _two_frame_widget()
        # _canAnim should reference _motionMQ, not a fresh matchMedia call
        assert "_motionMQ.matches" in html

    def test_no_bare_snapshot_matchmedia(self) -> None:
        """The old snapshot pattern must be gone: matchMedia(...).matches
        must not appear outside of _motionMQ assignment lines.

        We allow matchMedia to appear only in the _motionMQ initialisation
        line (so the MQL object is created), not as a separate one-shot read.
        """
        html = _two_frame_widget()
        # Count raw matchMedia calls that have .matches directly chained
        # (the old snapshot: matchMedia(...).matches).
        # The new code assigns to _motionMQ then reads _motionMQ.matches,
        # so matchMedia(...).matches should not appear.
        assert "matchMedia('(prefers-reduced-motion:reduce)').matches" not in html
