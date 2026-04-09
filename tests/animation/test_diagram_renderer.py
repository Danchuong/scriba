"""Tests for DiagramRenderer — static figure rendering.

Covers detection, validation (forbidden commands), rendering, and
persistent highlight behavior.
"""

from __future__ import annotations

import pytest

from scriba.core.context import RenderContext
from scriba.core.errors import ValidationError
from scriba.animation.detector import detect_diagram_blocks
from scriba.animation.renderer import DiagramRenderer


@pytest.fixture
def ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
    )


@pytest.fixture
def renderer() -> DiagramRenderer:
    return DiagramRenderer()


class TestDetectDiagramBlocks:
    """Detection of \\begin{diagram}...\\end{diagram} blocks."""

    def test_detect_single_diagram_block(self) -> None:
        source = r"""
\begin{diagram}[id="test"]
\shape{T}{Tree}{nodes=[1,2,3]}
\end{diagram}
"""
        blocks = detect_diagram_blocks(source)
        assert len(blocks) == 1
        assert blocks[0].kind == "diagram"
        assert blocks[0].metadata is not None
        assert blocks[0].metadata["options"]["id"] == "test"

    def test_detect_no_diagram_blocks(self) -> None:
        source = "Just plain text, no diagrams here."
        blocks = detect_diagram_blocks(source)
        assert blocks == []

    def test_detect_multiple_diagram_blocks(self) -> None:
        source = r"""
\begin{diagram}[id="first"]
\shape{A}{Tree}{nodes=[1,2]}
\end{diagram}

Some text between.

\begin{diagram}[id="second"]
\shape{B}{Tree}{nodes=[3,4]}
\end{diagram}
"""
        blocks = detect_diagram_blocks(source)
        assert len(blocks) == 2
        assert blocks[0].metadata["options"]["id"] == "first"
        assert blocks[1].metadata["options"]["id"] == "second"


class TestRejectStepInDiagram:
    """E1050: \\step is forbidden in diagram blocks."""

    def test_step_raises_validation_error(
        self, renderer: DiagramRenderer, ctx: RenderContext
    ) -> None:
        source = r"""
\begin{diagram}[id="bad"]
\shape{T}{Tree}{nodes=[1,2,3]}
\step
\recolor{T.node[1]}{state=current}
\end{diagram}
"""
        blocks = renderer.detect(source)
        assert len(blocks) == 1
        with pytest.raises(ValidationError, match="E1050"):
            renderer.render_block(blocks[0], ctx)


class TestRejectNarrateInDiagram:
    """E1054: \\narrate is forbidden in diagram blocks."""

    def test_narrate_raises_validation_error(
        self, renderer: DiagramRenderer, ctx: RenderContext
    ) -> None:
        source = r"""
\begin{diagram}[id="bad"]
\shape{T}{Tree}{nodes=[1,2,3]}
\narrate{This should not work}
\end{diagram}
"""
        blocks = renderer.detect(source)
        assert len(blocks) == 1
        with pytest.raises(ValidationError, match="E1054"):
            renderer.render_block(blocks[0], ctx)


class TestRenderStaticFigure:
    """DiagramRenderer produces a single static <figure>."""

    def test_renders_single_figure(
        self, renderer: DiagramRenderer, ctx: RenderContext
    ) -> None:
        source = r"""
\begin{diagram}[id="tree-structure"]
\shape{T}{Tree}{root=1, nodes=[1,2,3,4,5,6,7], edges=[(1,2),(1,3),(2,4),(2,5),(3,6),(3,7)]}
\recolor{T.node[1]}{state=current}
\recolor{T.node[2]}{state=done}
\recolor{T.node[3]}{state=done}
\end{diagram}
"""
        blocks = renderer.detect(source)
        assert len(blocks) == 1
        artifact = renderer.render_block(blocks[0], ctx)

        assert 'class="scriba-diagram"' in artifact.html
        assert 'data-scriba-scene="tree-structure"' in artifact.html
        assert "<svg" in artifact.html

        # No controls, no narration
        assert "scriba-controls" not in artifact.html
        assert "scriba-narration" not in artifact.html

    def test_no_js_assets(
        self, renderer: DiagramRenderer, ctx: RenderContext
    ) -> None:
        source = r"""
\begin{diagram}[id="simple"]
\shape{T}{Tree}{nodes=[1,2]}
\end{diagram}
"""
        blocks = renderer.detect(source)
        artifact = renderer.render_block(blocks[0], ctx)
        assert artifact.js_assets == frozenset()


class TestMultiplePrimitivesInDiagram:
    """Multiple shapes rendered in a single diagram."""

    def test_multiple_shapes(
        self, renderer: DiagramRenderer, ctx: RenderContext
    ) -> None:
        source = r"""
\begin{diagram}[id="multi"]
\shape{A}{Tree}{nodes=[1,2,3]}
\shape{B}{Tree}{nodes=[4,5,6]}
\end{diagram}
"""
        blocks = renderer.detect(source)
        artifact = renderer.render_block(blocks[0], ctx)

        # Should contain SVG elements for both shapes
        assert artifact.html.count("<svg") >= 2


class TestHighlightIsPersistent:
    """In diagram mode, \\highlight state is persistent (not ephemeral)."""

    def test_highlight_persists(
        self, renderer: DiagramRenderer, ctx: RenderContext
    ) -> None:
        source = r"""
\begin{diagram}[id="persistent"]
\shape{T}{Tree}{nodes=[1,2,3]}
\highlight{T.node[1]}{state=highlight}
\recolor{T.node[2]}{state=done}
\end{diagram}
"""
        blocks = renderer.detect(source)
        artifact = renderer.render_block(blocks[0], ctx)

        # Both the highlight and recolor should be present
        assert 'data-state="highlight"' in artifact.html
        assert 'data-state="done"' in artifact.html


class TestDiagramRendererProtocol:
    """DiagramRenderer satisfies the Renderer protocol shape."""

    def test_has_required_attributes(self) -> None:
        r = DiagramRenderer()
        assert r.name == "diagram"
        assert r.version == 1
        assert r.priority == 10

    def test_assets_returns_renderer_assets(self) -> None:
        r = DiagramRenderer()
        assets = r.assets()
        assert hasattr(assets, "css_files")
        assert hasattr(assets, "js_files")
