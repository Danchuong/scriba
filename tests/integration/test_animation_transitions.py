"""Integration tests for animation transition manifests.

Compiles .tex source through the full pipeline and compares the output
HTML ``tr:`` fields against hand-written golden files to verify that
animation transition manifests are correct.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scriba.animation.renderer import AnimationRenderer
from scriba.core.artifact import RenderArtifact
from scriba.core.context import RenderContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GOLDEN_DIR = Path(__file__).parent.parent / "golden" / "animation"


@pytest.fixture
def renderer() -> AnimationRenderer:
    return AnimationRenderer()


@pytest.fixture
def ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "interactive"},
        render_inline_tex=None,
    )


@pytest.fixture
def ctx_static() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "static"},
        render_inline_tex=None,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _render(
    renderer: AnimationRenderer,
    ctx: RenderContext,
    source: str,
) -> RenderArtifact:
    """Helper: detect + render_block for a single-block source."""
    blocks = renderer.detect(source)
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    return renderer.render_block(blocks[0], ctx)


def _load_golden(name: str) -> str:
    """Load a golden HTML file by name."""
    return (GOLDEN_DIR / name).read_text()


def _extract_tr_fields(html: str) -> list[str]:
    """Extract tr: values from JS frames array.

    Returns a list of strings, each either ``"null"`` or a JSON array
    like ``'[["a.cell[1]","state","idle","current","recolor"]]'``.
    """
    return re.findall(r",tr:(null|\[\[.*?\]\]),fs:\d\}", html)


def _has_animation_runtime(html: str) -> bool:
    """Check whether the animation runtime functions are present."""
    return all(
        s in html
        for s in [
            "_cancelAnims",
            "animateTransition",
            "snapToFrame",
            "_canAnim",
            "prefers-reduced-motion",
        ]
    )


# ---------------------------------------------------------------------------
# Test sources
# ---------------------------------------------------------------------------

_SOURCE_RECOLOR = (
    '\\begin{animation}[id="test-recolor"]\n'
    "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
    "\n"
    "\\step\n"
    "\\narrate{Initial state.}\n"
    "\n"
    "\\step\n"
    "\\recolor{a.cell[1]}{state=current}\n"
    "\\narrate{Recolored.}\n"
    "\\end{animation}"
)

_SOURCE_VALUE_CHANGE = (
    '\\begin{animation}[id="test-value"]\n'
    "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
    "\n"
    "\\step\n"
    "\\narrate{Initial.}\n"
    "\n"
    "\\step\n"
    '\\apply{a.cell[0]}{value="X"}\n'
    "\\narrate{Changed.}\n"
    "\\end{animation}"
)

_SOURCE_ELEMENT_ADD = (
    '\\begin{animation}[id="test-push"]\n'
    "\\shape{s}{Stack}{capacity=5}\n"
    "\n"
    "\\step\n"
    "\\narrate{Empty.}\n"
    "\n"
    "\\step\n"
    "\\apply{s}{push=42}\n"
    "\\narrate{Pushed.}\n"
    "\\end{animation}"
)

_SOURCE_IDENTICAL = (
    '\\begin{animation}[id="test-identical"]\n'
    "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
    "\n"
    "\\step\n"
    "\\narrate{Step one.}\n"
    "\n"
    "\\step\n"
    "\\narrate{Step two.}\n"
    "\\end{animation}"
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTwoStepRecolor:
    """Compile a 2-step recolor and compare tr fields with golden."""

    def test_two_step_recolor_tr(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, _SOURCE_RECOLOR)
        compiled_trs = _extract_tr_fields(artifact.html)
        golden_trs = _extract_tr_fields(_load_golden("html_two_step_recolor.html"))

        assert compiled_trs == golden_trs, (
            f"tr fields mismatch:\n"
            f"  compiled: {compiled_trs}\n"
            f"  golden:   {golden_trs}"
        )

    def test_recolor_frame0_null(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, _SOURCE_RECOLOR)
        trs = _extract_tr_fields(artifact.html)
        assert trs[0] == "null", f"Frame 0 should be null, got {trs[0]}"

    def test_recolor_frame1_has_transition(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, _SOURCE_RECOLOR)
        trs = _extract_tr_fields(artifact.html)
        assert '"recolor"' in trs[1], f"Frame 1 should contain recolor, got {trs[1]}"


class TestValueChange:
    """Compile a value change and compare tr fields with golden."""

    def test_value_change_tr(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, _SOURCE_VALUE_CHANGE)
        compiled_trs = _extract_tr_fields(artifact.html)
        golden_trs = _extract_tr_fields(_load_golden("html_value_change.html"))

        assert compiled_trs == golden_trs, (
            f"tr fields mismatch:\n"
            f"  compiled: {compiled_trs}\n"
            f"  golden:   {golden_trs}"
        )


class TestElementAdd:
    """Compile a stack push and compare tr fields with golden."""

    def test_element_add_tr(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, _SOURCE_ELEMENT_ADD)
        compiled_trs = _extract_tr_fields(artifact.html)
        golden_trs = _extract_tr_fields(_load_golden("html_element_add.html"))

        assert compiled_trs == golden_trs, (
            f"tr fields mismatch:\n"
            f"  compiled: {compiled_trs}\n"
            f"  golden:   {golden_trs}"
        )

    def test_element_add_kind(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, _SOURCE_ELEMENT_ADD)
        trs = _extract_tr_fields(artifact.html)
        assert '"element_add"' in trs[1], (
            f"Frame 1 should contain element_add, got {trs[1]}"
        )


class TestFirstFrameAlwaysNull:
    """Frame 0 always has tr:null regardless of source content."""

    @pytest.mark.parametrize(
        "source",
        [_SOURCE_RECOLOR, _SOURCE_VALUE_CHANGE, _SOURCE_ELEMENT_ADD, _SOURCE_IDENTICAL],
        ids=["recolor", "value_change", "element_add", "identical"],
    )
    def test_first_frame_always_null(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
        source: str,
    ) -> None:
        artifact = _render(renderer, ctx, source)
        trs = _extract_tr_fields(artifact.html)
        assert len(trs) >= 1, "Should have at least 1 frame"
        assert trs[0] == "null", f"Frame 0 should be null, got {trs[0]}"


class TestStaticMode:
    """Static mode has no tr fields and no animation runtime."""

    def test_static_mode_no_tr(
        self,
        renderer: AnimationRenderer,
        ctx_static: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx_static, _SOURCE_RECOLOR)
        trs = _extract_tr_fields(artifact.html)
        assert trs == [], f"Static mode should have no tr fields, got {trs}"

    def test_no_script_in_static(
        self,
        renderer: AnimationRenderer,
        ctx_static: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx_static, _SOURCE_RECOLOR)
        assert "<script>" not in artifact.html

    def test_animation_runtime_absent_static(
        self,
        renderer: AnimationRenderer,
        ctx_static: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx_static, _SOURCE_RECOLOR)
        assert not _has_animation_runtime(artifact.html), (
            "Static mode should not contain animation runtime functions"
        )


class TestIdenticalSteps:
    """Identical steps produce null tr (no changes = no manifest)."""

    def test_identical_steps_null(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, _SOURCE_IDENTICAL)
        compiled_trs = _extract_tr_fields(artifact.html)
        golden_trs = _extract_tr_fields(_load_golden("html_identical_steps.html"))

        assert compiled_trs == golden_trs, (
            f"tr fields mismatch:\n"
            f"  compiled: {compiled_trs}\n"
            f"  golden:   {golden_trs}"
        )

    def test_both_frames_null(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, _SOURCE_IDENTICAL)
        trs = _extract_tr_fields(artifact.html)
        assert trs == ["null", "null"], f"Both frames should be null, got {trs}"


class TestAnimationRuntime:
    """Interactive mode includes all animation runtime functions."""

    def test_animation_runtime_present(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, _SOURCE_RECOLOR)
        assert _has_animation_runtime(artifact.html), (
            "Interactive mode should contain all animation runtime functions"
        )
