"""Wave 8 Round B — Accessibility fixes regression tests.

Covers:
    A02 — Step counter must NOT have aria-live (removed to prevent double-
          announcement alongside the narration live region).
    A03 — Narration update in animateTransition is deferred to _finish()
          so the aria-live announcement fires AFTER the SVG animation settles.
    A04 — Substory narration <p> must have aria-live="polite" aria-atomic="true"
          so sub-step advances are announced by assistive technology.
    A09 — KaTeX must be configured with output: "htmlAndMathml" so that a
          hidden MathML subtree accompanies every rendered formula, allowing
          screen readers to announce math in narration text.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from scriba.animation.emitter import (
    FrameData,
    SubstoryData,
    emit_interactive_html,
    emit_substory_html,
)


# ---------------------------------------------------------------------------
# Minimal stub primitive (mirrors the pattern in test_emitter_a11y.py)
# ---------------------------------------------------------------------------


@dataclass
class _Stub:
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


def _frame(step: int = 1, total: int = 2, narration: str = "") -> FrameData:
    return FrameData(
        step_number=step,
        total_frames=total,
        narration_html=narration,
        shape_states={},
        annotations=[],
    )


def _two_frame_widget(label: str = "") -> str:
    prim = _Stub(shape_name="arr")
    frames = [_frame(step=1, total=2), _frame(step=2, total=2)]
    return emit_interactive_html("test-scene", frames, {"arr": prim}, label=label)


def _substory_html() -> str:
    sub_frames = [
        FrameData(
            step_number=1,
            total_frames=2,
            narration_html="sub step 1",
            shape_states={},
            annotations=[],
        ),
        FrameData(
            step_number=2,
            total_frames=2,
            narration_html="sub step 2",
            shape_states={},
            annotations=[],
        ),
    ]
    sub = SubstoryData(
        title="Inner loop",
        substory_id="sub-1",
        depth=1,
        frames=sub_frames,
        primitives={},
    )
    return emit_substory_html(
        scene_id="scene",
        parent_frame_id="scene-frame-1",
        substory=sub,
        primitives={},
        viewbox="0 0 200 40",
    )


# ---------------------------------------------------------------------------
# A02 — Step counter must NOT carry aria-live
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_step_counter_has_no_aria_live() -> None:
    """A02: The step counter is visual-only chrome; its aria-live was removed
    to prevent a double-announcement every time a step advances (the narration
    live region is the authoritative spoken channel).
    """
    html = _two_frame_widget()
    # Find the step counter element
    assert 'class="scriba-step-counter"' in html
    counter_start = html.index('class="scriba-step-counter"')
    # Grab the opening tag (up to the next >)
    counter_tag_end = html.index(">", counter_start)
    counter_tag = html[counter_start:counter_tag_end]
    assert "aria-live" not in counter_tag, (
        "Step counter must not carry aria-live — it causes double-announcement "
        "alongside the narration live region."
    )


@pytest.mark.unit
def test_narration_still_has_aria_live() -> None:
    """A02: Removing aria-live from the counter must not touch the narration
    panel — the narration region remains the primary live channel.
    """
    html = _two_frame_widget()
    assert 'class="scriba-narration"' in html
    narr_start = html.index('class="scriba-narration"')
    narr_tag_end = html.index(">", narr_start)
    narr_tag = html[narr_start:narr_tag_end]
    assert 'aria-live="polite"' in narr_tag, (
        "Main narration <p> must still carry aria-live=\"polite\"."
    )


# ---------------------------------------------------------------------------
# A03 — narr.innerHTML deferred to _finish() in animateTransition
# ---------------------------------------------------------------------------

def _read_scriba_js() -> str:
    """Return the source of scriba.js (the canonical runtime, not the emitted HTML)."""
    js_path = (
        Path(__file__).parent.parent.parent
        / "scriba" / "animation" / "static" / "scriba.js"
    )
    return js_path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_narration_not_set_at_top_of_animate_transition() -> None:
    """A03: narr.innerHTML must NOT appear before function _finish in
    animateTransition.  Moving it into _finish() ensures the aria-live
    announcement fires only after the WAAPI animation completes.
    """
    source = _read_scriba_js()
    anim_pos = source.find("function animateTransition")
    assert anim_pos != -1, "animateTransition not found in scriba.js"
    finish_pos = source.find("function _finish", anim_pos)
    assert finish_pos != -1, "function _finish not found after animateTransition"
    # narr.innerHTML must appear inside _finish (i.e. after its definition line)
    narr_pos = source.find("narr.innerHTML", finish_pos)
    assert narr_pos != -1, (
        "narr.innerHTML must appear inside _finish(), not before it, "
        "to ensure the live-region fires after the SVG animation settles."
    )


@pytest.mark.unit
def test_narration_not_set_before_finish_in_animate_transition() -> None:
    """A03: narr.innerHTML must NOT appear in animateTransition before _finish.

    Occurrences between the function open and the _finish definition would
    mean narration fires at the START of the animation, not at the end.
    """
    source = _read_scriba_js()
    anim_pos = source.find("function animateTransition")
    assert anim_pos != -1
    finish_def_pos = source.find("function _finish", anim_pos)
    assert finish_def_pos != -1
    # Slice: from animateTransition opening to the _finish definition
    before_finish = source[anim_pos:finish_def_pos]
    assert "narr.innerHTML" not in before_finish, (
        "narr.innerHTML must not appear before function _finish() inside "
        "animateTransition — that would fire the announcement before the SVG settles."
    )


# ---------------------------------------------------------------------------
# A04 — Substory narration must have aria-live
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_substory_narration_has_aria_live() -> None:
    """A04: The substory narration <p> must carry aria-live=\"polite\" so that
    sub-step advances are announced by screen readers.
    """
    html = _substory_html()
    assert 'class="scriba-narration"' in html
    narr_start = html.index('class="scriba-narration"')
    narr_tag_end = html.index(">", narr_start)
    narr_tag = html[narr_start:narr_tag_end]
    assert 'aria-live="polite"' in narr_tag, (
        "Substory narration <p> must have aria-live=\"polite\" so sub-step "
        "changes are announced to assistive technology."
    )


@pytest.mark.unit
def test_substory_narration_has_aria_atomic() -> None:
    """A04: The substory narration must also carry aria-atomic=\"true\" so only
    the substory text is announced (not the parent live region re-read).
    """
    html = _substory_html()
    narr_start = html.index('class="scriba-narration"')
    narr_tag_end = html.index(">", narr_start)
    narr_tag = html[narr_start:narr_tag_end]
    assert 'aria-atomic="true"' in narr_tag, (
        "Substory narration <p> must have aria-atomic=\"true\" to prevent "
        "the parent region from being re-announced on sub-step change."
    )


# ---------------------------------------------------------------------------
# A09 — KaTeX configured with htmlAndMathml output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_katex_worker_uses_htmlAndMathml() -> None:
    """A09: katex_worker.js must specify output: \"htmlAndMathml\" so that KaTeX
    emits a MathML companion subtree alongside the visual HTML, making math
    accessible to screen readers.
    """
    worker_path = (
        Path(__file__).parent.parent.parent
        / "scriba" / "tex" / "katex_worker.js"
    )
    source = worker_path.read_text(encoding="utf-8")
    assert 'output: "htmlAndMathml"' in source, (
        "katex_worker.js must use output: \"htmlAndMathml\" — "
        "output: \"html\" hides all math from screen readers."
    )
    assert 'output: "html",' not in source, (
        "The old output: \"html\" setting must be replaced with "
        "output: \"htmlAndMathml\"."
    )
