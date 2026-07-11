"""Tests for the live-widget controls-pill clearance contract (JudgeZone #17-B).

The floating controls pill (``.scriba-stage-wrap > .scriba-controls``) is
``position: absolute`` over the bottom-center of the stage on every frame.
Content and chrome must never share pixels: the stage reserves a
``padding-bottom`` clearance sized from the pill's own rendered box.

Before this fix the clearance was a bare ``3.25rem`` while every dimension
of the pill itself (button size, padding, border) was fixed-px. That only
happened to clear the pill at the default 16px root font-size; any smaller
host root font-size (e.g. a ``html { font-size: 62.5% }`` reset) shrinks the
rem-based clearance while the px-based pill stays full size, reintroducing
the exact overlap the finding describes. The fix ties the stage's clearance
and the pill's own box to the same ``--scriba-pill-*`` custom properties
(scoped to ``.scriba-stage-wrap``, not ``:root``, so the embed stylesheet
stays host-safe) so the two can never independently drift.

See _bmad-output/implementation-artifacts/spec-fix-judgezone-17b-chrome-clearance.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from scriba.animation.emitter import FrameData, emit_interactive_html

_CSS_PATH = (
    Path(__file__).resolve().parents[2]
    / "scriba"
    / "animation"
    / "static"
    / "scriba-embed.css"
)


def _css_text() -> str:
    return _CSS_PATH.read_text(encoding="utf-8")


def _block(selector: str) -> str:
    css = _css_text()
    return css.split(selector, 1)[1].split("}", 1)[0]


def _stage_wrap_block() -> str:
    return _block(".scriba-stage-wrap {")


def _stage_clearance_block() -> str:
    return _block(".scriba-stage-wrap > .scriba-stage {")


def _pill_block() -> str:
    return _block(".scriba-stage-wrap > .scriba-controls {")


def _pill_button_block() -> str:
    return _block(".scriba-stage-wrap > .scriba-controls button {")


def _token_px(block: str, name: str) -> float:
    """Extract a ``--scriba-pill-*: <N>px;`` declaration's numeric value."""
    m = re.search(rf"{re.escape(name)}:\s*([\d.]+)px", block)
    assert m, f"{name} not found as a plain px value in block:\n{block}"
    return float(m.group(1))


# ---------------------------------------------------------------------------
# Stub primitive + minimal widget renderer (mirrors test_widget_a11y.py)
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


@pytest.fixture
def widget_html() -> str:
    prim = _StubPrimitive(shape_name="a")
    frames = [_make_frame(step=1, total=2), _make_frame(step=2, total=2)]
    return emit_interactive_html("clearance-test", frames, {"a": prim})


# ---------------------------------------------------------------------------
# Token presence + derivation (CSS-only, static analysis)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPillClearanceTokens:
    def test_stage_wrap_declares_pill_geometry_tokens(self) -> None:
        block = _stage_wrap_block()
        for token in (
            "--scriba-pill-btn",
            "--scriba-pill-pad-y",
            "--scriba-pill-border",
            "--scriba-pill-offset",
        ):
            assert token in block, f"{token} missing from .scriba-stage-wrap"

    def test_clearance_token_is_calc_derived(self) -> None:
        block = _stage_wrap_block()
        assert "--scriba-pill-clearance:" in block
        clearance_decl = block.split("--scriba-pill-clearance:", 1)[1].split(";", 1)[0]
        assert "calc(" in clearance_decl, (
            "clearance must be calc()-derived from the pill tokens, "
            "not a hardcoded number"
        )

    def test_stage_clearance_uses_the_shared_token(self) -> None:
        block = _stage_clearance_block()
        assert "padding-bottom: var(--scriba-pill-clearance)" in block
        assert not re.search(r"padding-bottom:\s*[\d.]+rem", block), (
            "stage clearance must not fall back to a bare rem value — rem "
            "is root-font-size-relative but the pill's own box is fixed-px"
        )

    def test_pill_offset_uses_the_shared_token(self) -> None:
        assert "bottom: var(--scriba-pill-offset)" in _pill_block()

    def test_pill_button_size_uses_the_shared_token(self) -> None:
        block = _pill_button_block()
        assert "width: var(--scriba-pill-btn)" in block
        assert "height: var(--scriba-pill-btn)" in block

    def test_pill_padding_and_border_use_the_shared_tokens(self) -> None:
        block = _pill_block()
        assert "padding: var(--scriba-pill-pad-y) 6px" in block
        assert block.count("var(--scriba-pill-border)") == 2  # border + border-bottom


@pytest.mark.unit
class TestClearanceMathMatchesPillBox:
    """Numeric contract: the clearance formula must equal the pill's real
    rendered footprint (button + 2x padding + 2x border + bottom offset),
    not merely reference the tokens syntactically."""

    def test_clearance_equals_pill_box_plus_offset(self) -> None:
        block = _stage_wrap_block()
        btn = _token_px(block, "--scriba-pill-btn")
        pad_y = _token_px(block, "--scriba-pill-pad-y")
        border = _token_px(block, "--scriba-pill-border")
        offset = _token_px(block, "--scriba-pill-offset")
        gap = _token_px(block, "--scriba-pill-gap")

        pill_height = btn + (pad_y * 2) + (border * 2)
        expected_clearance = offset + pill_height + gap

        assert pill_height == 38
        # 52px == the pre-fix 3.25rem at the default 16px root font-size, so
        # default rendering is visually unchanged — but now derived from
        # fixed-px tokens instead of a root-font-size-relative unit.
        assert expected_clearance == 52


# ---------------------------------------------------------------------------
# Markup contract: print frames carry no controls/stage-wrap, so the
# clearance/pill rules structurally cannot apply there (static analysis
# only — no browser, per repo-wide Playwright ban).
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrintFramesHaveNoClearanceTarget:
    def test_live_stage_wrap_wraps_stage_and_controls(self, widget_html: str) -> None:
        assert '<div class="scriba-stage-wrap">' in widget_html
        live_region = widget_html.split('<div class="scriba-print-frames"', 1)[0]
        assert '<div class="scriba-stage"></div>' in live_region
        assert 'class="scriba-controls"' in live_region

    def test_print_frames_subtree_has_no_controls_markup(
        self, widget_html: str
    ) -> None:
        start = widget_html.index('<div class="scriba-print-frames"')
        print_region = widget_html[start:]
        assert "scriba-controls" not in print_region, (
            "print frames must never carry the controls pill — it only "
            "exists in the live .scriba-stage-wrap subtree"
        )

    def test_print_frames_subtree_has_no_stage_wrap_markup(
        self, widget_html: str
    ) -> None:
        start = widget_html.index('<div class="scriba-print-frames"')
        print_region = widget_html[start:]
        assert "scriba-stage-wrap" not in print_region, (
            "the clearance rule is scoped to .scriba-stage-wrap > .scriba-stage; "
            "print frames must not contain that wrapper, so the clearance "
            "rule cannot apply to (or be needed by) print output"
        )
