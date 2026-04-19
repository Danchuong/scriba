"""Tests for scriba.animation.renderer — ~8 cases."""

from __future__ import annotations

import logging
import re

import pytest

from scriba.animation.errors import AnimationError, FrameCountError
from scriba.animation.renderer import AnimationRenderer
from scriba.core.artifact import Block
from scriba.core.context import RenderContext


@pytest.fixture
def renderer() -> AnimationRenderer:
    return AnimationRenderer()


@pytest.fixture
def ctx() -> RenderContext:
    """Default context uses static mode for backward-compatible tests."""
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "static"},
        render_inline_tex=None,
    )


@pytest.fixture
def ctx_interactive() -> RenderContext:
    """Context using the new interactive (default) mode."""
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={},
        render_inline_tex=None,
    )


@pytest.fixture
def ctx_with_tex() -> RenderContext:
    def render_tex(text: str) -> str:
        return f"<span class='tex'>{text}</span>"

    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "static"},
        render_inline_tex=render_tex,
    )


class TestDetect:
    """detect() returns correct blocks."""

    def test_detect_returns_blocks(self, renderer: AnimationRenderer) -> None:
        source = r"\begin{animation}" "\nstuff\n" r"\end{animation}"
        blocks = renderer.detect(source)
        assert len(blocks) == 1
        assert blocks[0].kind == "animation"
        assert blocks[0].raw == source


class TestRenderBlock:
    """render_block() produces correct HTML structure."""

    def test_produces_html_with_correct_frame_count(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        source = (
            r"\begin{animation}" "\n"
            r"\step" "\n"
            r"\narrate{First step}" "\n"
            r"\step" "\n"
            r"\narrate{Second step}" "\n"
            r"\end{animation}"
        )
        block = Block(start=0, end=len(source), kind="animation", raw=source)
        artifact = renderer.render_block(block, ctx)

        assert 'data-frame-count="2"' in artifact.html
        assert "scriba-animation" in artifact.html
        assert "Step 1 / 2" in artifact.html
        assert "Step 2 / 2" in artifact.html

    def test_render_block_with_narration(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        source = (
            r"\begin{animation}" "\n"
            r"\step" "\n"
            r"\narrate{We start here.}" "\n"
            r"\end{animation}"
        )
        block = Block(start=0, end=len(source), kind="animation", raw=source)
        artifact = renderer.render_block(block, ctx)

        assert "We start here." in artifact.html
        assert "scriba-narration" in artifact.html

    def test_render_block_with_inline_tex(
        self,
        renderer: AnimationRenderer,
        ctx_with_tex: RenderContext,
    ) -> None:
        source = (
            r"\begin{animation}" "\n"
            r"\step" "\n"
            r"\narrate{Compute $x^2$.}" "\n"
            r"\end{animation}"
        )
        block = Block(start=0, end=len(source), kind="animation", raw=source)
        artifact = renderer.render_block(block, ctx_with_tex)

        # The render_inline_tex callback wraps in <span class='tex'>.
        # Phase 5.5: bleach sanitize normalizes attribute quotes to ``"``.
        assert '<span class="tex">' in artifact.html

    def test_render_block_prelude_only(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        source = (
            r"\begin{animation}" "\n"
            r"\end{animation}"
        )
        block = Block(start=0, end=len(source), kind="animation", raw=source)
        artifact = renderer.render_block(block, ctx)

        assert 'data-frame-count="0"' in artifact.html

    def test_css_assets(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        source = (
            r"\begin{animation}" "\n"
            r"\step" "\n"
            r"\end{animation}"
        )
        block = Block(start=0, end=len(source), kind="animation", raw=source)
        artifact = renderer.render_block(block, ctx)

        assert "scriba-animation.css" in artifact.css_assets
        assert "scriba-scene-primitives.css" in artifact.css_assets


class TestInteractiveOutput:
    """render_block() produces interactive widget with default context."""

    def test_interactive_mode_produces_widget(
        self,
        renderer: AnimationRenderer,
        ctx_interactive: RenderContext,
    ) -> None:
        source = (
            r"\begin{animation}" "\n"
            r"\step" "\n"
            r"\narrate{Hello}" "\n"
            r"\step" "\n"
            r"\narrate{World}" "\n"
            r"\end{animation}"
        )
        block = Block(start=0, end=len(source), kind="animation", raw=source)
        artifact = renderer.render_block(block, ctx_interactive)

        assert 'class="scriba-widget"' in artifact.html
        assert "<script>" in artifact.html
        assert "scriba-btn-prev" in artifact.html
        assert "scriba-btn-next" in artifact.html
        assert "Hello" in artifact.html
        assert "World" in artifact.html


class TestFrameCountLimits:
    """Frame count warning and error thresholds."""

    def test_warning_at_31_frames(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        steps = "\n".join(r"\step" for _ in range(31))
        source = r"\begin{animation}" "\n" + steps + "\n" r"\end{animation}"
        block = Block(start=0, end=len(source), kind="animation", raw=source)

        with caplog.at_level(logging.WARNING):
            artifact = renderer.render_block(block, ctx)

        assert 'data-frame-count="31"' in artifact.html
        assert any("31 frames" in r.message for r in caplog.records)

    def test_error_at_101_frames(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        steps = "\n".join(r"\step" for _ in range(101))
        source = r"\begin{animation}" "\n" + steps + "\n" r"\end{animation}"
        block = Block(start=0, end=len(source), kind="animation", raw=source)

        with pytest.raises(FrameCountError) as exc_info:
            renderer.render_block(block, ctx)
        assert "E1181" in str(exc_info.value)


class TestAssets:
    """assets() returns CSS paths."""

    def test_assets_returns_css(self, renderer: AnimationRenderer) -> None:
        ra = renderer.assets()
        css_names = {p.name for p in ra.css_files}
        assert "scriba-animation.css" in css_names
        assert "scriba-scene-primitives.css" in css_names
        assert len(ra.js_files) == 0


class TestVersion:
    """Renderer metadata."""

    def test_version_is_1(self, renderer: AnimationRenderer) -> None:
        assert renderer.version == 1

    def test_name_is_animation(self, renderer: AnimationRenderer) -> None:
        assert renderer.name == "animation"

    def test_priority_is_10(self, renderer: AnimationRenderer) -> None:
        assert renderer.priority == 10


class TestNoShapeDeclaredGuard:
    r"""E1116: \apply/\highlight/\recolor/\annotate without a \shape declaration.

    Regression for the silent "No frames" / empty-stage failure mode where
    writing \apply{a.cell[0]}{value=5} + \step without a preceding
    \shape{a}{Array}{...} exits 0 and shows an empty widget.
    """

    def _render(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
        body: str,
    ) -> None:
        source = r"\begin{animation}" + "\n" + body + "\n" + r"\end{animation}"
        block = Block(start=0, end=len(source), kind="animation", raw=source)
        renderer.render_block(block, ctx)

    def test_apply_before_shape_raises_e1116(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        """Exact regression from the bug report: apply + step, no shape."""
        with pytest.raises(AnimationError) as exc_info:
            self._render(
                renderer,
                ctx,
                r"\apply{a.cell[0]}{value=5}" + "\n" + r"\step",
            )
        err = str(exc_info.value)
        assert "E1116" in err
        assert "\\shape" in err

    def test_highlight_before_shape_raises_e1116(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        with pytest.raises(AnimationError) as exc_info:
            self._render(
                renderer,
                ctx,
                r"\step" + "\n" + r"\highlight{x.cell[0]}",
            )
        assert "E1116" in str(exc_info.value)

    def test_recolor_before_shape_raises_e1116(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        with pytest.raises(AnimationError) as exc_info:
            self._render(
                renderer,
                ctx,
                r"\step" + "\n" + r"\recolor{x.cell[0]}{state=done}",
            )
        assert "E1116" in str(exc_info.value)

    def test_annotate_before_shape_raises_e1116(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        with pytest.raises(AnimationError) as exc_info:
            self._render(
                renderer,
                ctx,
                r"\step" + "\n" + r"\annotate{x.cell[0]}{text}",
            )
        assert "E1116" in str(exc_info.value)

    def test_steps_only_no_commands_no_error(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        """Steps with only narration (no shape refs) must NOT raise E1116."""
        artifact = None
        source = (
            r"\begin{animation}" + "\n"
            + r"\step" + "\n"
            + r"\narrate{Just narration, no shapes needed.}" + "\n"
            + r"\end{animation}"
        )
        block = Block(start=0, end=len(source), kind="animation", raw=source)
        # Must not raise
        artifact = renderer.render_block(block, ctx)
        assert artifact is not None

    def test_shape_declared_no_error(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        r"""When \shape is declared, \apply must not raise E1116."""
        source = (
            r"\begin{animation}" + "\n"
            + r"\shape{a}{Array}{size=3}" + "\n"
            + r"\step" + "\n"
            + r"\apply{a.cell[0]}{value=5}" + "\n"
            + r"\end{animation}"
        )
        block = Block(start=0, end=len(source), kind="animation", raw=source)
        artifact = renderer.render_block(block, ctx)
        assert artifact is not None
        assert "E1116" not in artifact.html

    def test_error_message_includes_hint(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        """E1116 error message must include an actionable hint."""
        with pytest.raises(AnimationError) as exc_info:
            self._render(
                renderer,
                ctx,
                r"\apply{a.cell[0]}{value=5}" + "\n" + r"\step",
            )
        err = str(exc_info.value)
        # hint: should tell the user how to fix it
        assert "Array" in err or "\\shape" in err
