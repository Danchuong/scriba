"""Breadth coverage for untested animation error codes.

Each test triggers exactly one error code and asserts that the parser,
detector, primitive, or Starlark host surfaces it. This is coverage
breadth, not deep behavioural testing — every new assertion pins one
previously-unverified code path so the suite can detect regressions in
error classification.

Codes covered (15 total):
  * Structural/parser: ``E1003``, ``E1013``, ``E1051``, ``E1052``,
    ``E1055``, ``E1056``, ``E1053``, ``E1172``
  * Primitive validation (E14xx): ``E1102``, ``E1103``, ``E1460``,
    ``E1465``, ``E1480``
  * Starlark sandbox (E115x): ``E1150``, ``E1154``
"""

from __future__ import annotations

import pytest

from scriba import RenderContext, SubprocessWorkerPool
from scriba.animation.detector import detect_animation_blocks
from scriba.animation.errors import NestedAnimationError
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.renderer import AnimationRenderer
from scriba.animation.starlark_host import StarlarkHost, WorkerError
from scriba.core.artifact import Block
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def animation_renderer() -> AnimationRenderer:
    return AnimationRenderer()


def _make_block(source: str) -> Block:
    """Wrap a full ``\\begin{animation}...\\end{animation}`` body in a ``Block``."""
    return Block(start=0, end=len(source), kind="animation", raw=source)


# ---------------------------------------------------------------------------
# Parser / structural codes
# ---------------------------------------------------------------------------


class TestParserCodes:
    """Error codes raised by the detector and parser layers."""

    def test_e1003_nested_animation_detected(self) -> None:
        src = (
            "\\begin{animation}\n"
            "\\begin{animation}\n"
            "\\end{animation}\n"
            "\\end{animation}\n"
        )
        with pytest.raises(NestedAnimationError) as exc_info:
            detect_animation_blocks(src)
        assert exc_info.value.code == "E1003"

    def test_e1013_source_exceeds_size_limit(self) -> None:
        # Parser hard-caps source at 1 MB; 2 MB should trigger E1013 early.
        src = "x" * (2 * 1024 * 1024)
        with pytest.raises(ValidationError) as exc_info:
            SceneParser().parse(src)
        assert exc_info.value.code == "E1013"

    def test_e1051_shape_after_step(self) -> None:
        src = "\\step\n\\shape{a}{Array}{values=[1]}\n"
        with pytest.raises(ValidationError) as exc_info:
            SceneParser().parse(src)
        assert exc_info.value.code == "E1051"

    def test_e1052_trailing_text_after_step(self) -> None:
        src = "\\shape{a}{Array}{values=[1]}\n\\step garbage\n"
        with pytest.raises(ValidationError) as exc_info:
            SceneParser().parse(src)
        assert exc_info.value.code == "E1052"

    def test_e1053_highlight_in_prelude(self) -> None:
        src = "\\shape{a}{Array}{values=[1]}\n\\highlight{a.cell[0]}{}\n"
        with pytest.raises(ValidationError) as exc_info:
            SceneParser().parse(src)
        assert exc_info.value.code == "E1053"

    def test_e1055_duplicate_narrate_in_step(self) -> None:
        src = (
            "\\shape{a}{Array}{values=[1]}\n"
            "\\step\n"
            "\\narrate{first}\n"
            "\\narrate{second}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            SceneParser().parse(src)
        assert exc_info.value.code == "E1055"

    def test_e1056_narrate_outside_step(self) -> None:
        src = "\\shape{a}{Array}{values=[1]}\n\\narrate{stray}\n"
        with pytest.raises(ValidationError) as exc_info:
            SceneParser().parse(src)
        assert exc_info.value.code == "E1056"

    def test_e1172_endforeach_without_foreach(self) -> None:
        src = "\\shape{a}{Array}{values=[1]}\n\\step\n\\endforeach\n"
        with pytest.raises(ValidationError) as exc_info:
            SceneParser().parse(src)
        assert exc_info.value.code == "E1172"


# ---------------------------------------------------------------------------
# Primitive / renderer codes (E14xx block)
# ---------------------------------------------------------------------------


class TestPrimitiveCodes:
    """Error codes raised during primitive construction."""

    def test_e1102_unknown_primitive_type(
        self, animation_renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        src = (
            "\\begin{animation}\n"
            "\\shape{a}{BogusType}{}\n"
            "\\end{animation}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            animation_renderer.render_block(_make_block(src), ctx)
        assert exc_info.value.code == "E1102"

    def test_e1103_array_missing_required_param(
        self, animation_renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        # ``Array`` requires ``size`` / ``n`` / ``values``; ``values=0`` is not a list.
        src = (
            "\\begin{animation}\n"
            "\\shape{a}{Array}{values=0}\n"
            "\\end{animation}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            animation_renderer.render_block(_make_block(src), ctx)
        assert exc_info.value.code == "E1103"

    def test_e1460_plane2d_degenerate_xrange(
        self, animation_renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        src = (
            "\\begin{animation}\n"
            "\\shape{p}{Plane2D}{xrange=(0,0), yrange=(0,10)}\n"
            "\\end{animation}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            animation_renderer.render_block(_make_block(src), ctx)
        assert exc_info.value.code == "E1460"

    def test_e1465_plane2d_invalid_aspect(
        self, animation_renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        src = (
            "\\begin{animation}\n"
            "\\shape{p}{Plane2D}{xrange=(0,10), yrange=(0,10), aspect=weird}\n"
            "\\end{animation}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            animation_renderer.render_block(_make_block(src), ctx)
        assert exc_info.value.code == "E1465"

    def test_e1480_metricplot_requires_series(
        self, animation_renderer: AnimationRenderer, ctx: RenderContext,
    ) -> None:
        src = (
            "\\begin{animation}\n"
            "\\shape{m}{MetricPlot}{xrange=(0,10)}\n"
            "\\end{animation}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            animation_renderer.render_block(_make_block(src), ctx)
        assert exc_info.value.code == "E1480"


# ---------------------------------------------------------------------------
# Starlark sandbox codes (E115x block)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def starlark_host():
    pool = SubprocessWorkerPool()
    host = StarlarkHost(worker_pool=pool)
    try:
        yield host
    finally:
        pool.close()


class TestStarlarkCodes:
    """Error codes raised by the Starlark sandbox subprocess."""

    def test_e1150_parse_error(self, starlark_host: StarlarkHost) -> None:
        """Malformed Starlark source surfaces ``E1150``."""
        with pytest.raises(WorkerError) as exc_info:
            starlark_host.eval({}, "x = ", timeout=2.0)
        assert exc_info.value.code == "E1150"

    def test_e1154_forbidden_import(self, starlark_host: StarlarkHost) -> None:
        """Forbidden constructs like ``import`` surface ``E1154``."""
        with pytest.raises(WorkerError) as exc_info:
            starlark_host.eval({}, "import os", timeout=2.0)
        assert exc_info.value.code == "E1154"
