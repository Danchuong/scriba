"""Tests for scriba.animation.renderer — ~8 cases."""

from __future__ import annotations

import logging
import re

import pytest

from scriba.animation.errors import FrameCountError
from scriba.animation.renderer import AnimationRenderer
from scriba.core.artifact import Block
from scriba.core.context import RenderContext


@pytest.fixture
def renderer() -> AnimationRenderer:
    return AnimationRenderer()


@pytest.fixture
def ctx() -> RenderContext:
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
        metadata={},
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

        # The render_inline_tex callback wraps in <span class='tex'>
        assert "<span class='tex'>" in artifact.html

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
        assert "E1151" in str(exc_info.value)


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
