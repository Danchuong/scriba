"""Tests for the shared shell-panel builders in ``_html_stitcher.py``.

``_narration_element``, ``_step_label_span``, and ``_step_controls_element``
are the single source for narration paragraphs, step-label markers, and
step-controller bars across the filmstrip (``emit_animation_html``), the
interactive widget + its hidden print-frames (``emit_interactive_html``), and
the substory widget (``emit_substory_html``) — mirroring the
``_invariant_panel_elements`` precedent (the invariant panel's own single-
source fix). Before this, each of the 9 call sites hand-rolled its own copy of
this markup; a shape change (or a bug fix) at one site had no way to reach the
others. These tests lock the shared shape so that kind of drift is caught
here instead of downstream in a rendered diff.
"""

from __future__ import annotations

import re

from scriba.animation._html_stitcher import (
    _narration_element,
    _step_controls_element,
    _step_label_span,
)
from scriba.animation.emitter import (
    FrameData,
    SubstoryData,
    emit_animation_html,
    emit_interactive_html,
)


def _frames(n: int, substories: list[SubstoryData] | None = None) -> list[FrameData]:
    result = []
    for i in range(1, n + 1):
        subs = substories if (i == 1 and substories) else None
        result.append(
            FrameData(
                step_number=i,
                total_frames=n,
                narration_html=f"Narration {i}.",
                shape_states={},
                annotations=[],
                substories=subs,
            )
        )
    return result


class TestNarrationElement:
    """Each call site passes only the id/aria bits it needs; class/dir/tag
    shape must stay identical everywhere."""

    def test_filmstrip_frame_shape(self) -> None:
        # emit_animation_html's per-frame narration: id only.
        assert (
            _narration_element("hello", id_attr="d-n1")
            == '<p class="scriba-narration" dir="auto" id="d-n1">hello</p>'
        )

    def test_print_substory_shape(self) -> None:
        # emit_interactive_html's print-substory narration: no attrs at all.
        assert (
            _narration_element("hello")
            == '<p class="scriba-narration" dir="auto">hello</p>'
        )

    def test_main_widget_shape(self) -> None:
        # emit_interactive_html's live widget narration: id + aria-live.
        assert _narration_element(
            "hello", id_attr="d-narration", aria_live="polite"
        ) == (
            '<p class="scriba-narration" dir="auto" '
            'id="d-narration" aria-live="polite">hello</p>'
        )

    def test_substory_widget_shape(self) -> None:
        # emit_substory_html's live narration slot: aria-live + aria-atomic,
        # content filled in by JS at runtime (starts empty).
        assert _narration_element("", aria_live="polite", aria_atomic=True) == (
            '<p class="scriba-narration" dir="auto" '
            'aria-live="polite" aria-atomic="true"></p>'
        )

    def test_bare_call_has_no_stray_attributes(self) -> None:
        assert _narration_element("") == '<p class="scriba-narration" dir="auto"></p>'


class TestStepLabelSpan:
    def test_shape(self) -> None:
        assert (
            _step_label_span(2, 5) == '<span class="scriba-step-label">2 / 5</span>'
        )

    def test_single_frame(self) -> None:
        assert (
            _step_label_span(1, 1) == '<span class="scriba-step-label">1 / 1</span>'
        )


class TestStepControlsElement:
    def test_main_widget_shape_multi_frame(self) -> None:
        ind = " " * 4
        out = _step_controls_element(3)
        expected = "\n".join(
            [
                f'{ind}<div class="scriba-controls">',
                f'{ind}  <button class="scriba-btn-prev" aria-label="Previous step" disabled>&#10094;</button>',
                f'{ind}  <span class="scriba-step-counter">1 / 3</span>',
                f'{ind}  <button class="scriba-btn-next" aria-label="Next step">&#10095;</button>',
                f"{ind}</div>",
            ]
        )
        assert out == expected

    def test_main_widget_shape_single_frame_disables_next(self) -> None:
        out = _step_controls_element(1)
        assert (
            '<button class="scriba-btn-next" aria-label="Next step" disabled>'
            in out
        )

    def test_substory_shape_with_progress_dots(self) -> None:
        ind = " " * 10
        out = _step_controls_element(
            2,
            extra_class="scriba-substory-controls",
            prev_label="Previous sub-step",
            next_label="Next sub-step",
            progress_html="<div></div>",
            indent=ind,
        )
        expected = "\n".join(
            [
                f'{ind}<div class="scriba-controls scriba-substory-controls">',
                f'{ind}  <button class="scriba-btn-prev" aria-label="Previous sub-step" disabled>&#10094;</button>',
                f'{ind}  <span class="scriba-step-counter">1 / 2</span>',
                f'{ind}  <button class="scriba-btn-next" aria-label="Next sub-step">&#10095;</button>',
                f'{ind}  <div class="scriba-progress" aria-hidden="true">',
                f"{ind}    <div></div>",
                f"{ind}  </div>",
                f"{ind}</div>",
            ]
        )
        assert out == expected

    def test_empty_but_not_none_progress_html_still_renders_wrapper(self) -> None:
        # Regression: the substory site always passes its joined dots string,
        # even when there are zero sub-frames (empty string, not None) — the
        # golden corpus's ``17_empty_substory`` example caught an earlier
        # version of this builder that used a truthy check and silently
        # dropped the wrapper for this exact case.
        ind = " " * 10
        out = _step_controls_element(
            0,
            extra_class="scriba-substory-controls",
            prev_label="Previous sub-step",
            next_label="Next sub-step",
            progress_html="",
            indent=ind,
        )
        expected = "\n".join(
            [
                f'{ind}<div class="scriba-controls scriba-substory-controls">',
                f'{ind}  <button class="scriba-btn-prev" aria-label="Previous sub-step" disabled>&#10094;</button>',
                f'{ind}  <span class="scriba-step-counter">1 / 0</span>',
                f'{ind}  <button class="scriba-btn-next" aria-label="Next sub-step" disabled>&#10095;</button>',
                f'{ind}  <div class="scriba-progress" aria-hidden="true">',
                f"{ind}    ",
                f"{ind}  </div>",
                f"{ind}</div>",
            ]
        )
        assert out == expected

    def test_none_progress_html_omits_wrapper(self) -> None:
        out = _step_controls_element(3)
        assert "scriba-progress" not in out


_STEP_LABEL_RE = re.compile(r'<span class="scriba-step-label">(\d+) / (\d+)</span>')
_NARRATION_TAG_RE = re.compile(
    r'<p class="scriba-narration" dir="auto"[^>]*>(.*?)</p>', re.DOTALL
)


class TestCrossModeStepLabelConsistency:
    """Same frames in, filmstrip vs. interactive print-frames out — the
    (step, total) pairs must agree exactly. A mode passing the wrong
    frame_count (the invariant panel's fixed bug was in this family) would
    show up here as a mismatched pair, not just a missing class."""

    def test_static_and_interactive_agree_on_step_labels(self) -> None:
        frames = _frames(3)
        static_html = emit_animation_html("d", frames, {})
        interactive_html = emit_interactive_html("d", frames, {})

        static_labels = set(_STEP_LABEL_RE.findall(static_html))
        interactive_labels = set(_STEP_LABEL_RE.findall(interactive_html))

        expected = {("1", "3"), ("2", "3"), ("3", "3")}
        assert static_labels == expected
        assert interactive_labels == expected


class TestCrossModeNarrationConsistency:
    def test_static_and_interactive_carry_same_narration_text(self) -> None:
        frames = _frames(2)
        static_html = emit_animation_html("d", frames, {})
        interactive_html = emit_interactive_html("d", frames, {})

        static_texts = set(_NARRATION_TAG_RE.findall(static_html))
        interactive_texts = set(_NARRATION_TAG_RE.findall(interactive_html))

        expected_texts = {"Narration 1.", "Narration 2."}
        assert expected_texts <= static_texts
        assert expected_texts <= interactive_texts


_BTN_PREV_RE = re.compile(
    r'<button class="scriba-btn-prev" aria-label="([^"]+)" disabled>&#10094;</button>'
)
_BTN_NEXT_RE = re.compile(
    r'<button class="scriba-btn-next" aria-label="([^"]+)"( disabled)?>&#10095;</button>'
)
_STEP_COUNTER_RE = re.compile(r'<span class="scriba-step-counter">1 / (\d+)</span>')


class TestControlsShapeConsistency:
    """Main widget controls and substory controls are two call sites of the
    same builder — button classes/order must be identical; only label
    wording, extra_class, and the disabled state (driven by each site's own
    frame_count) are allowed to differ."""

    def test_main_widget_and_substory_controls_share_button_shape(self) -> None:
        sub = SubstoryData(
            title="Sub-computation",
            substory_id="sub1",
            depth=1,
            frames=_frames(2),
        )
        frames = [
            FrameData(
                step_number=1,
                total_frames=1,
                narration_html="parent",
                shape_states={},
                annotations=[],
                substories=[sub],
            )
        ]
        html = emit_interactive_html("d", frames, {})

        prev_labels = _BTN_PREV_RE.findall(html)
        next_matches = _BTN_NEXT_RE.findall(html)
        counters = _STEP_COUNTER_RE.findall(html)

        assert prev_labels == ["Previous step", "Previous sub-step"]
        assert [label for label, _ in next_matches] == ["Next step", "Next sub-step"]
        # Main widget: 1 total frame -> next disabled. Substory: 2 -> enabled.
        assert next_matches[0][1] == " disabled"
        assert next_matches[1][1] == ""
        assert counters == ["1", "2"]
        assert "scriba-substory-controls" in html
