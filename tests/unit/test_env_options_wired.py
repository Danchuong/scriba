"""Env options must reach the output: label / width / height / layout.

They were parsed into ``AnimationOptions`` and then dropped — zero readers
besides ``id`` — despite the reference promising ``label`` as the scene's
aria label and ``width``/``height`` as size constraints. ``grid`` was
accepted by the option validator without even being a field.
"""

from __future__ import annotations

import pytest

from scriba.animation.emitter import FrameData
from scriba.animation._html_stitcher import emit_html
from scriba.animation.parser.grammar import SceneParser


def _frame(**kw) -> FrameData:
    defaults = dict(
        step_number=1,
        total_frames=1,
        narration_html="<p>x</p>",
        shape_states={},
        annotations=[],
        label="",
    )
    defaults.update(kw)
    return FrameData(**defaults)


def _emit(mode: str, **kw) -> str:
    return emit_html(
        "scene-x", [_frame()], {}, mode=mode, minify=False, **kw
    )


class TestEnvLabelWired:
    def test_interactive_uses_env_label(self) -> None:
        html = _emit("interactive", label="Number Spiral walkthrough")
        assert 'aria-label="Number Spiral walkthrough"' in html

    def test_static_uses_env_label(self) -> None:
        html = _emit("static", label="Number Spiral walkthrough")
        assert 'aria-label="Number Spiral walkthrough"' in html

    def test_diagram_uses_env_label(self) -> None:
        html = _emit("diagram", label="Sơ đồ 5 lớp")
        assert 'aria-label="Sơ đồ 5 lớp"' in html


class TestSizeWired:
    def test_width_height_become_max_constraints(self) -> None:
        html = _emit("interactive", width="8cm", height="300")
        assert "max-width:8cm" in html
        assert "max-height:300px" in html

    def test_diagram_size(self) -> None:
        html = _emit("diagram", width="480")
        assert "max-width:480px" in html


class TestLayoutWired:
    def test_static_layout_attribute_reflects_option(self) -> None:
        html = _emit("static", layout="stack")
        assert 'data-layout="stack"' in html


class TestDiagramAria:
    def test_diagram_svg_has_no_dangling_labelledby(self) -> None:
        html = _emit("diagram")
        assert "aria-labelledby" not in html


class TestGridOptionRejected:
    def test_grid_key_is_no_longer_silently_accepted(self) -> None:
        src = '[id="x", grid=true]\n\\shape{a}{Array}{size=2}\n\\step\n\\narrate{x}'
        with pytest.raises(Exception):
            SceneParser().parse(src)


class TestDiagramRendererForwardsOptions:
    """The emitter half was wired and tested — but DiagramRenderer never fed
    it, so a documented ``\\begin{diagram}[label=..., width=...]`` silently
    dropped the aria-label and the max-size constraints (environments.md
    §12.3 promises both)."""

    @staticmethod
    def _render(opts: str) -> str:
        from scriba.animation.detector import detect_diagram_blocks
        from scriba.animation.renderer import DiagramRenderer
        from scriba.core.context import RenderContext

        doc = (
            "\\begin{diagram}" + opts + "\n"
            "\\shape{a}{Array}{size=2}\n"
            "\\end{diagram}\n"
        )
        blocks = detect_diagram_blocks(doc)
        assert blocks
        return DiagramRenderer().render_block(
            blocks[0], RenderContext(resource_resolver=lambda n: n)
        ).html

    def test_diagram_label_reaches_figure(self) -> None:
        html = self._render('[id="d", label="A small BST"]')
        assert 'aria-label="A small BST"' in html

    def test_diagram_label_reaches_svg_title(self) -> None:
        """JudgeZone #10: label= must also reach the SVG's own <title>, not
        just the figure's aria-label. The <title> element -- not the
        figure's aria-label -- is what drives the SVG's own computed
        accessible name and the native hover tooltip (SVG 2 §5.1)."""
        html = self._render('[id="internal-slug-x", label="A small BST"]')
        assert "<title>A small BST</title>" in html
        assert "<title>internal-slug-x</title>" not in html

    def test_diagram_without_label_omits_svg_title(self) -> None:
        """Diagrams forbid \\step[title=] and \\narrate (E1050/E1054), so
        with no label= there is no natural-language content to name the
        SVG. Per the accessible-name policy, <title> must be omitted
        entirely -- it must never fall back to the internal id=."""
        html = self._render('[id="internal-slug-x"]')
        assert "<title>" not in html

    def test_diagram_without_label_keeps_role_img_and_no_dangling_aria(
        self,
    ) -> None:
        """Omitting <title> must not regress the surrounding a11y wiring:
        role="img" stays, and no aria-labelledby dangles (a diagram has no
        narration paragraph for it to reference)."""
        html = self._render('[id="internal-slug-x"]')
        assert 'role="img"' in html
        assert "aria-labelledby" not in html

    def test_diagram_width_becomes_max_width(self) -> None:
        html = self._render('[id="d", width=480]')
        assert "max-width:480px" in html

    def test_diagram_without_size_stays_unstyled(self) -> None:
        import re

        html = self._render('[id="d"]')
        fig = re.search(r"<figure[^>]*>", html).group(0)
        assert "style=" not in fig  # the stage svg's intrinsic calc() is fine
