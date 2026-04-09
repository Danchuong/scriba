"""End-to-end integration tests for the animation pipeline.

Each test exercises the FULL pipeline: LaTeX source -> SceneParser ->
SceneState -> primitives -> emitter -> RenderArtifact with HTML output.
"""

from __future__ import annotations

import logging
import re

import pytest

from scriba.animation.errors import FrameCountError
from scriba.animation.renderer import AnimationRenderer
from scriba.core.artifact import Block, RenderArtifact
from scriba.core.context import RenderContext
from scriba.core.pipeline import Pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
        return f'<span class="katex">{text}</span>'

    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={},
        render_inline_tex=render_tex,
    )


@pytest.fixture
def pipeline(renderer: AnimationRenderer) -> Pipeline:
    return Pipeline(renderers=[renderer])


def _render(
    renderer: AnimationRenderer,
    ctx: RenderContext,
    source: str,
) -> RenderArtifact:
    """Helper: detect + render_block for a single-block source."""
    blocks = renderer.detect(source)
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    return renderer.render_block(blocks[0], ctx)


# ---------------------------------------------------------------------------
# Test 1: Binary search animation (Array primitive)
# ---------------------------------------------------------------------------


class TestBinarySearchAnimation:
    """Full pipeline with Array primitive, recolor, and narration."""

    SOURCE = (
        '\\begin{animation}[id="test-bsearch"]' "\n"
        r"\shape{a}{Array}{size=5, data=[1,3,5,7,9]}" "\n"
        "\n"
        r"\step" "\n"
        r"\recolor{a.cell[2]}{state=current}" "\n"
        r"\narrate{Check middle element.}" "\n"
        "\n"
        r"\step" "\n"
        r"\recolor{a.cell[2]}{state=done}" "\n"
        r"\narrate{Found!}" "\n"
        r"\end{animation}"
    )

    def test_frame_count(self, renderer: AnimationRenderer, ctx: RenderContext) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-frame-count="2"' in artifact.html

    def test_scene_id(self, renderer: AnimationRenderer, ctx: RenderContext) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-scriba-scene="test-bsearch"' in artifact.html

    def test_array_svg_present(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-primitive="array"' in artifact.html
        assert 'data-shape="a"' in artifact.html

    def test_five_cells(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        for i in range(5):
            assert f'data-target="a.cell[{i}]"' in artifact.html

    def test_cell_state_current_frame1(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        # Frame 1: cell[2] should have state=current
        # The HTML has two frames; in the first one, cell[2] is "current"
        frames = artifact.html.split("scriba-frame-header")
        # Frame 1 is frames[1], frame 2 is frames[2]
        assert "scriba-state-current" in frames[1]

    def test_cell_state_done_frame2(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        frames = artifact.html.split("scriba-frame-header")
        assert "scriba-state-done" in frames[2]

    def test_narration_present(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "Check middle element." in artifact.html
        assert "Found!" in artifact.html

    def test_data_values_in_cells(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        for val in [1, 3, 5, 7, 9]:
            assert f">{val}<" in artifact.html

    def test_css_assets(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "scriba-animation.css" in artifact.css_assets
        assert "scriba-scene-primitives.css" in artifact.css_assets


# ---------------------------------------------------------------------------
# Test 2: DP with computed values
# ---------------------------------------------------------------------------


class TestDPTableAnimation:
    """Full pipeline with DPTable primitive and apply command."""

    SOURCE = (
        '\\begin{animation}[id="test-dp"]' "\n"
        r"\shape{dp}{DPTable}{n=5}" "\n"
        "\n"
        r"\step" "\n"
        r"\apply{dp.cell[0]}{value=0}" "\n"
        r"\recolor{dp.cell[0]}{state=done}" "\n"
        r"\narrate{Base case: dp[0] = 0.}" "\n"
        r"\end{animation}"
    )

    def test_frame_count(self, renderer: AnimationRenderer, ctx: RenderContext) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-frame-count="1"' in artifact.html

    def test_dptable_svg(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-primitive="dptable"' in artifact.html
        assert 'data-shape="dp"' in artifact.html

    def test_five_cells(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        for i in range(5):
            assert f'data-target="dp.cell[{i}]"' in artifact.html

    def test_cell_value_applied(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        # Cell 0 should display "0" after \apply{dp.cell[0]}{value=0}
        assert ">0<" in artifact.html

    def test_cell_state_done(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        # cell[0] should be in done state
        cell0_match = re.search(
            r'data-target="dp\.cell\[0\]"[^>]*class="([^"]*)"',
            artifact.html,
        )
        assert cell0_match is not None
        assert "scriba-state-done" in cell0_match.group(1)

    def test_narration(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "Base case: dp[0] = 0." in artifact.html


# ---------------------------------------------------------------------------
# Test 3: Graph BFS
# ---------------------------------------------------------------------------


class TestGraphBFSAnimation:
    """Full pipeline with Graph primitive and node recoloring."""

    SOURCE = (
        '\\begin{animation}[id="test-bfs"]' "\n"
        r'\shape{g}{Graph}{nodes=["A","B","C"], edges=[("A","B"),("A","C")],'
        r" directed=false}" "\n"
        "\n"
        r"\step" "\n"
        r'\recolor{g.node["A"]}{state=current}' "\n"
        r"\narrate{Start from A.}" "\n"
        "\n"
        r"\step" "\n"
        r'\recolor{g.node["A"]}{state=done}' "\n"
        r'\recolor{g.node["B"]}{state=current}' "\n"
        r"\narrate{Visit B.}" "\n"
        r"\end{animation}"
    )

    def test_frame_count(self, renderer: AnimationRenderer, ctx: RenderContext) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-frame-count="2"' in artifact.html

    def test_graph_svg(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-primitive="graph"' in artifact.html
        assert 'data-shape="g"' in artifact.html

    def test_three_nodes(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "scriba-graph-nodes" in artifact.html
        for label in ("A", "B", "C"):
            assert f">{label}<" in artifact.html

    def test_two_edges(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "scriba-graph-edges" in artifact.html

    def test_narration(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "Start from A." in artifact.html
        assert "Visit B." in artifact.html


# ---------------------------------------------------------------------------
# Test 4: Narration with inline TeX
# ---------------------------------------------------------------------------


class TestNarrationWithInlineTex:
    """Narration text is passed through ctx.render_inline_tex."""

    SOURCE = (
        '\\begin{animation}[id="test-tex"]' "\n"
        r"\step" "\n"
        r"\narrate{Compare $a_i$ with $a_j$.}" "\n"
        r"\end{animation}"
    )

    def test_tex_callback_invoked(
        self,
        renderer: AnimationRenderer,
        ctx_with_tex: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx_with_tex, self.SOURCE)
        # The render_inline_tex callback wraps in <span class="katex">
        assert '<span class="katex">' in artifact.html


# ---------------------------------------------------------------------------
# Test 5: Narration without TeX renderer
# ---------------------------------------------------------------------------


class TestNarrationWithoutTexRenderer:
    """Narration falls back to HTML escaping when no TeX renderer."""

    SOURCE = (
        '\\begin{animation}[id="test-no-tex"]' "\n"
        r"\step" "\n"
        r"\narrate{Value is <safe> & sound.}" "\n"
        r"\end{animation}"
    )

    def test_html_escaped(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        # HTML special chars should be escaped
        assert "&lt;safe&gt;" in artifact.html
        assert "&amp;" in artifact.html


# ---------------------------------------------------------------------------
# Test 6: Frame count warning (>30 frames)
# ---------------------------------------------------------------------------


class TestFrameCountWarning:
    """Animation with >30 frames emits a log warning."""

    def test_warning_at_31_frames(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        steps = "\n".join(r"\step" for _ in range(31))
        source = r"\begin{animation}" "\n" + steps + "\n" r"\end{animation}"
        block = Block(
            start=0, end=len(source), kind="animation", raw=source,
        )

        with caplog.at_level(logging.WARNING):
            artifact = renderer.render_block(block, ctx)

        assert 'data-frame-count="31"' in artifact.html
        assert any("31 frames" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Test 7: Frame count error (>100 frames)
# ---------------------------------------------------------------------------


class TestFrameCountError:
    """Animation with >100 frames raises FrameCountError."""

    def test_error_at_101_frames(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        steps = "\n".join(r"\step" for _ in range(101))
        source = r"\begin{animation}" "\n" + steps + "\n" r"\end{animation}"
        block = Block(
            start=0, end=len(source), kind="animation", raw=source,
        )

        with pytest.raises(FrameCountError) as exc_info:
            renderer.render_block(block, ctx)
        assert "E1151" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 8: Prelude-only (shapes declared but no \step)
# ---------------------------------------------------------------------------


class TestPreludeOnly:
    """Animation with shape declarations but no steps produces 0 frames."""

    SOURCE = (
        '\\begin{animation}[id="test-prelude"]' "\n"
        r"\shape{a}{Array}{size=3, data=[1,2,3]}" "\n"
        r"\end{animation}"
    )

    def test_zero_frames(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-frame-count="0"' in artifact.html

    def test_no_step_labels(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "scriba-step-label" not in artifact.html

    def test_block_id_set(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert artifact.block_id == "test-prelude"


# ---------------------------------------------------------------------------
# Test 9: Pipeline.render() integration
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Full Pipeline.render() path with animation blocks."""

    SOURCE = (
        '\\begin{animation}[id="pipeline-test"]' "\n"
        r"\shape{a}{Array}{size=3, data=[10,20,30]}" "\n"
        r"\step" "\n"
        r"\recolor{a.cell[1]}{state=current}" "\n"
        r"\narrate{Checking element 1.}" "\n"
        r"\end{animation}"
    )

    def test_pipeline_render(self, pipeline: Pipeline, ctx: RenderContext) -> None:
        doc = pipeline.render(self.SOURCE, ctx)
        assert "pipeline-test" in doc.html
        assert 'data-primitive="array"' in doc.html
        assert "Checking element 1." in doc.html

    def test_pipeline_css_assets(
        self, pipeline: Pipeline, ctx: RenderContext,
    ) -> None:
        doc = pipeline.render(self.SOURCE, ctx)
        css_names = {name.split("/")[-1] for name in doc.required_css}
        assert "scriba-animation.css" in css_names
        assert "scriba-scene-primitives.css" in css_names

    def test_pipeline_versions(
        self, pipeline: Pipeline, ctx: RenderContext,
    ) -> None:
        doc = pipeline.render(self.SOURCE, ctx)
        assert doc.versions["animation"] == 1

    def test_pipeline_block_data(
        self, pipeline: Pipeline, ctx: RenderContext,
    ) -> None:
        doc = pipeline.render(self.SOURCE, ctx)
        assert "pipeline-test" in doc.block_data
        assert doc.block_data["pipeline-test"]["frame_count"] == 1


# ---------------------------------------------------------------------------
# Test 10: Unknown primitive type
# ---------------------------------------------------------------------------


class TestUnknownPrimitiveType:
    """Unknown shape type raises ValidationError with E1102."""

    SOURCE = (
        r"\begin{animation}" "\n"
        r"\shape{x}{UnknownType}{size=3}" "\n"
        r"\step" "\n"
        r"\end{animation}"
    )

    def test_raises_validation_error(
        self,
        renderer: AnimationRenderer,
        ctx: RenderContext,
    ) -> None:
        from scriba.core.errors import ValidationError

        with pytest.raises(ValidationError, match="E1102"):
            _render(renderer, ctx, self.SOURCE)
