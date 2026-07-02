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
