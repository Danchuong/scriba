"""Phase B integration tests -- end-to-end render through the pipeline.

Each test exercises: parse .tex -> render HTML -> check output structure.
"""

from __future__ import annotations

import pytest

from scriba.animation.renderer import AnimationRenderer, DiagramRenderer
from scriba.core.artifact import Block, RenderArtifact
from scriba.core.context import RenderContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def renderer() -> AnimationRenderer:
    return AnimationRenderer()


@pytest.fixture
def diagram_renderer() -> DiagramRenderer:
    return DiagramRenderer()


@pytest.fixture
def ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "static"},
        render_inline_tex=None,
    )


@pytest.fixture
def ctx_interactive() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "interactive"},
        render_inline_tex=None,
    )


def _render(
    renderer: AnimationRenderer,
    ctx: RenderContext,
    source: str,
) -> RenderArtifact:
    """Helper: detect + render_block for a single animation block."""
    blocks = renderer.detect(source)
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    return renderer.render_block(blocks[0], ctx)


def _render_diagram(
    renderer: DiagramRenderer,
    ctx: RenderContext,
    source: str,
) -> RenderArtifact:
    """Helper: detect + render_block for a single diagram block."""
    blocks = renderer.detect(source)
    assert len(blocks) >= 1
    return renderer.render_block(blocks[0], ctx)


# ---------------------------------------------------------------------------
# 1. Render Grid animation -- output has scriba-widget
# ---------------------------------------------------------------------------


class TestRenderGrid:
    SOURCE = (
        "\\begin{animation}\n"
        "\\shape{g}{Grid}{rows=2, cols=2, data=[1,2,3,4]}\n"
        "\n"
        "\\step\n"
        "\\recolor{g.cell[0][0]}{state=current}\n"
        "\\narrate{Checking top-left.}\n"
        "\\end{animation}"
    )

    def test_grid_svg_present(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-primitive="grid"' in artifact.html
        assert 'data-shape="g"' in artifact.html

    def test_grid_cells_present(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        for r in range(2):
            for c in range(2):
                assert f'data-target="g.cell[{r}][{c}]"' in artifact.html


# ---------------------------------------------------------------------------
# 2. Render Tree animation -- output has tree SVG
# ---------------------------------------------------------------------------


class TestRenderTree:
    SOURCE = (
        "\\begin{animation}\n"
        "\\shape{T}{Tree}{root=1, nodes=[1,2,3], edges=[(1,2),(1,3)]}\n"
        "\n"
        "\\step\n"
        "\\recolor{T.node[1]}{state=current}\n"
        "\\narrate{Visit root.}\n"
        "\\end{animation}"
    )

    def test_tree_svg_present(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-primitive="tree"' in artifact.html
        assert 'data-shape="T"' in artifact.html

    def test_tree_nodes_rendered(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "scriba-tree-nodes" in artifact.html

    def test_tree_edges_rendered(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "scriba-tree-edges" in artifact.html


# ---------------------------------------------------------------------------
# 3. Render NumberLine animation -- ticks visible
# ---------------------------------------------------------------------------


class TestRenderNumberLine:
    SOURCE = (
        "\\begin{animation}\n"
        "\\shape{nl}{NumberLine}{domain=[0,5]}\n"
        "\n"
        "\\step\n"
        "\\recolor{nl.tick[2]}{state=current}\n"
        "\\narrate{Mark tick 2.}\n"
        "\\end{animation}"
    )

    def test_numberline_svg_present(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-primitive="numberline"' in artifact.html
        assert 'data-shape="nl"' in artifact.html

    def test_numberline_ticks(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-target="nl.tick[0]"' in artifact.html
        assert 'data-target="nl.tick[5]"' in artifact.html

    def test_numberline_state(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "scriba-state-current" in artifact.html


# ---------------------------------------------------------------------------
# 4. Render Diagram -- output has scriba-diagram, no script
# ---------------------------------------------------------------------------


class TestRenderDiagram:
    SOURCE = (
        "\\begin{diagram}\n"
        "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
        "\\recolor{a.cell[0]}{state=done}\n"
        "\\end{diagram}"
    )

    def test_diagram_class(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render_diagram(diagram_renderer, ctx, self.SOURCE)
        assert "scriba-diagram" in artifact.html

    def test_diagram_no_script(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render_diagram(diagram_renderer, ctx, self.SOURCE)
        assert "<script" not in artifact.html

    def test_diagram_state_applied(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render_diagram(diagram_renderer, ctx, self.SOURCE)
        assert "scriba-state-done" in artifact.html


# ---------------------------------------------------------------------------
# 5. Render Matrix -- output has colored cells
# ---------------------------------------------------------------------------


class TestRenderMatrix:
    SOURCE = (
        "\\begin{animation}\n"
        "\\shape{m}{Matrix}{rows=2, cols=2, data=[0,0.5,0.5,1]}\n"
        "\n"
        "\\step\n"
        "\\recolor{m.cell[0][0]}{state=current}\n"
        "\\narrate{Highlight origin.}\n"
        "\\end{animation}"
    )

    def test_matrix_svg_present(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-primitive="matrix"' in artifact.html
        assert "rgb(" in artifact.html


# ---------------------------------------------------------------------------
# 6. Render Stack -- output has stack items
# ---------------------------------------------------------------------------


class TestRenderStack:
    SOURCE = (
        "\\begin{animation}\n"
        "\\shape{s}{Stack}{items=[a,b,c]}\n"
        "\n"
        "\\step\n"
        "\\recolor{s.item[0]}{state=current}\n"
        "\\narrate{Check bottom.}\n"
        "\\end{animation}"
    )

    def test_stack_svg_present(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert 'data-primitive="stack"' in artifact.html
        assert 'data-shape="s"' in artifact.html


# ---------------------------------------------------------------------------
# 7. All state colors correct
# ---------------------------------------------------------------------------


class TestStateColors:
    SOURCE_CURRENT = (
        "\\begin{animation}\n"
        "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
        "\\step\n"
        "\\recolor{a.cell[0]}{state=current}\n"
        "\\end{animation}"
    )

    SOURCE_DONE = (
        "\\begin{animation}\n"
        "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
        "\\step\n"
        "\\recolor{a.cell[0]}{state=done}\n"
        "\\end{animation}"
    )

    def test_current_color(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE_CURRENT)
        assert "#0072B2" in artifact.html  # current fill

    def test_done_color(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE_DONE)
        assert "#009E73" in artifact.html  # done fill


# ---------------------------------------------------------------------------
# 8. Render with range recolor -- expanded correctly
# ---------------------------------------------------------------------------


class TestRenderRangeRecolor:
    SOURCE = (
        "\\begin{animation}\n"
        "\\shape{a}{Array}{size=5, data=[1,2,3,4,5]}\n"
        "\\step\n"
        "\\recolor{a.range[1:3]}{state=done}\n"
        "\\end{animation}"
    )

    def test_range_expands_to_individual_cells(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        # Cells 1, 2, 3 should have done state
        assert "scriba-state-done" in artifact.html

    def test_range_recolor_count(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        # done fill color should appear for cells 1-3
        assert artifact.html.count("#009E73") >= 3


# ---------------------------------------------------------------------------
# 9. Render with highlight -- overlay present
# ---------------------------------------------------------------------------


class TestRenderHighlight:
    SOURCE = (
        "\\begin{animation}\n"
        "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
        "\\step\n"
        "\\highlight{a.cell[1]}\n"
        "\\end{animation}"
    )

    def test_highlight_in_output(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        # The highlight should produce some visual indication
        assert artifact.html is not None
        assert len(artifact.html) > 0


# ---------------------------------------------------------------------------
# 10. CSS assets present
# ---------------------------------------------------------------------------


class TestCssAssets:
    SOURCE = (
        "\\begin{animation}\n"
        "\\shape{a}{Array}{size=2}\n"
        "\\step\n"
        "\\narrate{Hello.}\n"
        "\\end{animation}"
    )

    def test_css_assets(
        self, renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        artifact = _render(renderer, ctx, self.SOURCE)
        assert "scriba-animation.css" in artifact.css_assets
        assert "scriba-scene-primitives.css" in artifact.css_assets
