"""Integration tests for depth-2 substory nesting via _materialise_substory.

Verifies the full pipeline: LaTeX source -> AnimationRenderer -> SubstoryData
with particular focus on:
- Parent shape state preserved after inner substory exits
- Inner substory-local shapes do NOT leak to parent scope
- Frame indices are sequential across the nesting
"""

from __future__ import annotations

import pytest

from scriba.animation.renderer import AnimationRenderer
from scriba.core.artifact import Block
from scriba.core.context import RenderContext


# ---------------------------------------------------------------------------
# Shared fixtures
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
        metadata={"output_mode": "static", "minify": False},
        render_inline_tex=None,
    )


def _render(renderer: AnimationRenderer, ctx: RenderContext, source: str):
    """Detect and render the first block in source."""
    blocks = renderer.detect(source)
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    return renderer.render_block(blocks[0], ctx)


# ---------------------------------------------------------------------------
# Source: depth-2 nesting (\substory inside \substory)
# ---------------------------------------------------------------------------

# Outer animation has shape 'a' (Array).
# Step 1: outer substory with shape 'b' (local), which in turn has
#         an inner substory with shape 'c' (doubly-local).
_DEPTH_2_SOURCE = r"""\begin{animation}[id="depth2-test"]
\shape{a}{Array}{size=3}
\step
\recolor{a.cell[0]}{state=current}
\substory[title="Outer sub", id="outer"]
\shape{b}{Array}{size=2}
\step
\recolor{b.cell[0]}{state=current}
\substory[title="Inner sub", id="inner"]
\shape{c}{Array}{size=1}
\step
\recolor{c.cell[0]}{state=done}
\endsubstory
\step
\recolor{b.cell[1]}{state=done}
\endsubstory
\step
\recolor{a.cell[1]}{state=done}
\end{animation}"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDepth2SubstoryNesting:
    r"""Integration tests for \substory inside \substory (_materialise_substory)."""

    def test_render_completes_without_error(
        self, renderer: AnimationRenderer, ctx: RenderContext
    ) -> None:
        """Full depth-2 nesting renders without raising."""
        artifact = _render(renderer, ctx, _DEPTH_2_SOURCE)
        assert artifact.html

    def test_parent_shape_state_preserved_after_inner_substory(
        self, renderer: AnimationRenderer, ctx: RenderContext
    ) -> None:
        """Parent shape 'a' is unchanged after inner and outer substories exit.

        apply_substory() saves and restores parent state, so mutations inside
        any substory must not bleed back to the parent SceneState.
        """
        _render(renderer, ctx, _DEPTH_2_SOURCE)

        # last_snapshots holds snapshots of the top-level frames only
        snapshots = renderer.last_snapshots
        assert len(snapshots) == 2, "Expected 2 top-level frames"

        snap_frame1 = snapshots[0]
        # In frame 1, parent applied recolor to a.cell[0] → state=current
        assert "a" in snap_frame1.shape_states
        a_states = snap_frame1.shape_states["a"]
        assert a_states.get("a.cell[0]") is not None
        assert a_states["a.cell[0]"].state == "current"

        snap_frame2 = snapshots[1]
        # After frame 2, a.cell[1] is done but a.cell[0] still carries current
        a_states2 = snap_frame2.shape_states["a"]
        assert a_states2.get("a.cell[1]") is not None
        assert a_states2["a.cell[1]"].state == "done"
        # a.cell[0] persists from frame 1 (persistent state)
        assert a_states2.get("a.cell[0]") is not None
        assert a_states2["a.cell[0]"].state == "current"

    def test_inner_local_shapes_do_not_leak_to_parent(
        self, renderer: AnimationRenderer, ctx: RenderContext
    ) -> None:
        """Shapes 'b' and 'c' declared inside substories must not appear in parent snapshots."""
        _render(renderer, ctx, _DEPTH_2_SOURCE)

        snapshots = renderer.last_snapshots
        for snap in snapshots:
            assert "b" not in snap.shape_states, (
                f"Substory-local shape 'b' leaked to parent frame {snap.index}"
            )
            assert "c" not in snap.shape_states, (
                f"Doubly-local shape 'c' leaked to parent frame {snap.index}"
            )

    def test_frame_indices_are_sequential(
        self, renderer: AnimationRenderer, ctx: RenderContext
    ) -> None:
        """Top-level frame snapshots have sequential indices starting at 1."""
        _render(renderer, ctx, _DEPTH_2_SOURCE)

        snapshots = renderer.last_snapshots
        assert len(snapshots) >= 1
        for expected, snap in enumerate(snapshots, start=1):
            assert snap.index == expected, (
                f"Expected frame index {expected}, got {snap.index}"
            )

    def test_outer_substory_rendered_in_html(
        self, renderer: AnimationRenderer, ctx: RenderContext
    ) -> None:
        """HTML output contains the outer substory section."""
        artifact = _render(renderer, ctx, _DEPTH_2_SOURCE)
        assert 'data-substory-id="outer"' in artifact.html

    def test_outer_substory_depth_attribute(
        self, renderer: AnimationRenderer, ctx: RenderContext
    ) -> None:
        """Outer substory has data-substory-depth='1'."""
        artifact = _render(renderer, ctx, _DEPTH_2_SOURCE)
        assert 'data-substory-depth="1"' in artifact.html

    def test_inner_substory_depth_is_2_in_data_structure(
        self, renderer: AnimationRenderer, ctx: RenderContext
    ) -> None:
        """_materialise_substory assigns depth=2 to the inner substory object.

        The emitter may not emit depth-2 HTML attributes in static mode;
        the test therefore inspects the intermediate FrameData tree directly.
        """
        from scriba.animation.parser.grammar import SceneParser

        ir = SceneParser().parse(
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\recolor{a.cell[0]}{state=current}\n"
            '\\substory[title="Outer sub", id="outer"]\n'
            "\\shape{b}{Array}{size=2}\n"
            "\\step\n"
            "\\recolor{b.cell[0]}{state=current}\n"
            '\\substory[title="Inner sub", id="inner"]\n'
            "\\shape{c}{Array}{size=1}\n"
            "\\step\n"
            "\\recolor{c.cell[0]}{state=done}\n"
            "\\endsubstory\n"
            "\\step\n"
            "\\recolor{b.cell[1]}{state=done}\n"
            "\\endsubstory\n"
            "\\step\n"
            "\\recolor{a.cell[1]}{state=done}\n"
        )
        frame_data_list = renderer._materialise(ir, ctx, "depth2-test")
        # frame_data_list[0] is frame 1; it has one substory (outer)
        assert frame_data_list[0].substories is not None
        outer = frame_data_list[0].substories[0]
        assert outer.substory_id == "outer"
        assert outer.depth == 1
        # outer's first sub-frame has one nested substory (inner, depth=2)
        assert outer.frames[0].substories is not None
        inner = outer.frames[0].substories[0]
        assert inner.substory_id == "inner"
        assert inner.depth == 2
