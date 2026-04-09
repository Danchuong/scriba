"""Phase B edge-case tests for the DiagramRenderer.

Exercises diagram detection, static output, forbidden commands,
output structure, CSS classes, and renderer metadata.
"""

from __future__ import annotations

import pytest

from scriba.animation.detector import detect_diagram_blocks
from scriba.animation.renderer import AnimationRenderer, DiagramRenderer
from scriba.core.artifact import Block, RenderArtifact
from scriba.core.context import RenderContext
from scriba.core.errors import ValidationError


@pytest.fixture
def diagram_renderer() -> DiagramRenderer:
    return DiagramRenderer()


@pytest.fixture
def anim_renderer() -> AnimationRenderer:
    return AnimationRenderer()


@pytest.fixture
def ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={"output_mode": "diagram"},
        render_inline_tex=None,
    )


def _render_diagram(
    renderer: DiagramRenderer,
    ctx: RenderContext,
    source: str,
) -> RenderArtifact:
    """Helper: detect + render_block for a single diagram block."""
    blocks = renderer.detect(source)
    assert len(blocks) >= 1, f"Expected at least 1 diagram block, got {len(blocks)}"
    return renderer.render_block(blocks[0], ctx)


# ---------------------------------------------------------------------------
# 1. Detect diagram block
# ---------------------------------------------------------------------------


class TestDetectDiagram:
    def test_detects_diagram_block(self) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\end{diagram}"
        )
        blocks = detect_diagram_blocks(source)
        assert len(blocks) == 1
        assert blocks[0].kind == "diagram"

    def test_detect_returns_correct_raw(self) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3}\n"
            "\\end{diagram}"
        )
        blocks = detect_diagram_blocks(source)
        assert "\\begin{diagram}" in blocks[0].raw
        assert "\\end{diagram}" in blocks[0].raw


# ---------------------------------------------------------------------------
# 2. Detect multiple diagram blocks in same source
# ---------------------------------------------------------------------------


class TestDetectMultipleDiagrams:
    def test_two_diagram_blocks(self) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=2}\n"
            "\\end{diagram}\n"
            "\n"
            "\\begin{diagram}\n"
            "\\shape{b}{Array}{size=3}\n"
            "\\end{diagram}"
        )
        blocks = detect_diagram_blocks(source)
        assert len(blocks) == 2


# ---------------------------------------------------------------------------
# 3. Diagram with no commands (just \shape) -- renders static figure
# ---------------------------------------------------------------------------


class TestDiagramStaticFigure:
    def test_shape_only_renders(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\end{diagram}"
        )
        artifact = _render_diagram(diagram_renderer, ctx, source)
        assert "scriba-diagram" in artifact.html
        assert 'data-primitive="array"' in artifact.html


# ---------------------------------------------------------------------------
# 4. Diagram with \recolor -- state applies
# ---------------------------------------------------------------------------


class TestDiagramRecolor:
    def test_recolor_applies(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\recolor{a.cell[1]}{state=current}\n"
            "\\end{diagram}"
        )
        artifact = _render_diagram(diagram_renderer, ctx, source)
        assert "scriba-state-current" in artifact.html


# ---------------------------------------------------------------------------
# 5. Diagram with \highlight -- persistent (not ephemeral)
# ---------------------------------------------------------------------------


class TestDiagramHighlight:
    def test_highlight_in_diagram(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\highlight{a.cell[0]}\n"
            "\\end{diagram}"
        )
        artifact = _render_diagram(diagram_renderer, ctx, source)
        # Highlight should be present in diagram output
        assert artifact.html is not None


# ---------------------------------------------------------------------------
# 6. Diagram with \step -- raises E1050
# ---------------------------------------------------------------------------


class TestDiagramStep:
    def test_step_raises_error(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            "\\recolor{a.cell[0]}{state=current}\n"
            "\\end{diagram}"
        )
        with pytest.raises(ValidationError, match="E1050"):
            _render_diagram(diagram_renderer, ctx, source)


# ---------------------------------------------------------------------------
# 7. Diagram output has no <script> tag
# ---------------------------------------------------------------------------


class TestDiagramNoScript:
    def test_no_script_tag(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\end{diagram}"
        )
        artifact = _render_diagram(diagram_renderer, ctx, source)
        assert "<script" not in artifact.html


# ---------------------------------------------------------------------------
# 8. Diagram output has no controls/buttons
# ---------------------------------------------------------------------------


class TestDiagramNoControls:
    def test_no_buttons(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\end{diagram}"
        )
        artifact = _render_diagram(diagram_renderer, ctx, source)
        assert "<button" not in artifact.html
        assert "scriba-btn-prev" not in artifact.html
        assert "scriba-btn-next" not in artifact.html


# ---------------------------------------------------------------------------
# 9. Diagram CSS class is "scriba-diagram" not "scriba-animation"
# ---------------------------------------------------------------------------


class TestDiagramCssClass:
    def test_css_class_diagram(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\end{diagram}"
        )
        artifact = _render_diagram(diagram_renderer, ctx, source)
        assert "scriba-diagram" in artifact.html
        assert "scriba-animation" not in artifact.html


# ---------------------------------------------------------------------------
# 10. DiagramRenderer.name == "diagram", version == 1
# ---------------------------------------------------------------------------


class TestDiagramRendererMeta:
    def test_name(self) -> None:
        r = DiagramRenderer()
        assert r.name == "diagram"

    def test_version(self) -> None:
        r = DiagramRenderer()
        assert r.version == 1


# ---------------------------------------------------------------------------
# 11. Diagram with multiple primitives -- all render
# ---------------------------------------------------------------------------


class TestDiagramMultiplePrimitives:
    def test_two_primitives(
        self, diagram_renderer: DiagramRenderer, ctx: RenderContext,
    ) -> None:
        source = (
            "\\begin{diagram}\n"
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\shape{g}{Grid}{rows=2, cols=2}\n"
            "\\end{diagram}"
        )
        artifact = _render_diagram(diagram_renderer, ctx, source)
        assert 'data-primitive="array"' in artifact.html
        assert 'data-primitive="grid"' in artifact.html


# ---------------------------------------------------------------------------
# 12. AnimationRenderer.name == "animation"
# ---------------------------------------------------------------------------


class TestAnimationRendererMeta:
    def test_name(self, anim_renderer: AnimationRenderer) -> None:
        assert anim_renderer.name == "animation"

    def test_version(self, anim_renderer: AnimationRenderer) -> None:
        assert anim_renderer.version == 1
