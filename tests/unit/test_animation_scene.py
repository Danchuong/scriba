"""Tests for scriba.animation.scene — ~15 cases."""

from __future__ import annotations

import pytest

from scriba.animation.parser.ast import (
    AnnotateCmd,
    ApplyCmd,
    ComputeBlock,
    FrameIR,
    HighlightCmd,
    RecolorCmd,
    ShapeDecl,
)
from scriba.animation.scene import AnnotationEntry, SceneState, ShapeTargetState


class TestPrelude:
    """Shape registration and prelude commands."""

    def test_shape_declarations_recorded(self) -> None:
        state = SceneState()
        state.apply_prelude(
            shapes=(
                ShapeDecl(name="arr", shape_type="array"),
                ShapeDecl(name="graph", shape_type="graph"),
            ),
        )
        assert "arr" in state.shape_states
        assert "graph" in state.shape_states

    def test_prelude_apply_sets_initial_state(self) -> None:
        state = SceneState()
        state.apply_prelude(
            shapes=(ShapeDecl(name="arr", shape_type="array"),),
            prelude_commands=(ApplyCmd(target="arr.0", value="5"),),
        )
        assert state.shape_states["arr"]["arr.0"].value == "5"


class TestApply:
    """\\apply — persistent value/label."""

    def test_value_persists_across_frames(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(ShapeDecl(name="arr", shape_type="array"),))

        frame1 = FrameIR(
            index=1,
            commands=(ApplyCmd(target="arr.0", value="10"),),
        )
        snap1 = state.apply_frame(frame1)

        frame2 = FrameIR(index=2, commands=())
        snap2 = state.apply_frame(frame2)

        assert snap1.shape_states["arr"]["arr.0"].value == "10"
        assert snap2.shape_states["arr"]["arr.0"].value == "10"

    def test_apply_with_label(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(ShapeDecl(name="arr", shape_type="array"),))

        frame = FrameIR(
            index=1,
            commands=(ApplyCmd(target="arr.0", value="42", label="answer"),),
        )
        snap = state.apply_frame(frame)

        assert snap.shape_states["arr"]["arr.0"].value == "42"
        assert snap.shape_states["arr"]["arr.0"].label == "answer"

    def test_apply_overwrites_previous_value(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(ShapeDecl(name="arr", shape_type="array"),))

        frame1 = FrameIR(
            index=1,
            commands=(ApplyCmd(target="arr.0", value="10"),),
        )
        state.apply_frame(frame1)

        frame2 = FrameIR(
            index=2,
            commands=(ApplyCmd(target="arr.0", value="20"),),
        )
        snap2 = state.apply_frame(frame2)

        assert snap2.shape_states["arr"]["arr.0"].value == "20"


class TestRecolor:
    """\\recolor — persistent state replacement."""

    def test_recolor_persists(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(ShapeDecl(name="arr", shape_type="array"),))

        frame1 = FrameIR(
            index=1,
            commands=(RecolorCmd(target="arr.0", state="visited"),),
        )
        snap1 = state.apply_frame(frame1)

        frame2 = FrameIR(index=2, commands=())
        snap2 = state.apply_frame(frame2)

        assert snap1.shape_states["arr"]["arr.0"].state == "visited"
        assert snap2.shape_states["arr"]["arr.0"].state == "visited"

    def test_recolor_replaces_prior_state(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(ShapeDecl(name="arr", shape_type="array"),))

        frame1 = FrameIR(
            index=1,
            commands=(RecolorCmd(target="arr.0", state="visited"),),
        )
        state.apply_frame(frame1)

        frame2 = FrameIR(
            index=2,
            commands=(RecolorCmd(target="arr.0", state="active"),),
        )
        snap2 = state.apply_frame(frame2)

        assert snap2.shape_states["arr"]["arr.0"].state == "active"


class TestHighlight:
    """\\highlight — ephemeral, cleared at next frame."""

    def test_highlight_present_in_frame(self) -> None:
        state = SceneState()
        frame = FrameIR(
            index=1,
            commands=(HighlightCmd(target="arr.0"),),
        )
        snap = state.apply_frame(frame)
        assert "arr.0" in snap.highlights

    def test_highlight_cleared_at_next_frame(self) -> None:
        state = SceneState()
        frame1 = FrameIR(
            index=1,
            commands=(HighlightCmd(target="arr.0"),),
        )
        state.apply_frame(frame1)

        frame2 = FrameIR(index=2, commands=())
        snap2 = state.apply_frame(frame2)

        assert "arr.0" not in snap2.highlights


class TestAnnotate:
    """\\annotate — persistent by default, ephemeral if flagged."""

    def test_persistent_annotation(self) -> None:
        state = SceneState()
        frame1 = FrameIR(
            index=1,
            commands=(AnnotateCmd(target="arr.0", text="note"),),
        )
        snap1 = state.apply_frame(frame1)

        frame2 = FrameIR(index=2, commands=())
        snap2 = state.apply_frame(frame2)

        assert len(snap1.annotations) == 1
        assert snap1.annotations[0].text == "note"
        assert len(snap2.annotations) == 1  # persists

    def test_ephemeral_annotation_cleared(self) -> None:
        state = SceneState()
        frame1 = FrameIR(
            index=1,
            commands=(
                AnnotateCmd(target="arr.0", text="temp", ephemeral=True),
            ),
        )
        snap1 = state.apply_frame(frame1)

        frame2 = FrameIR(index=2, commands=())
        snap2 = state.apply_frame(frame2)

        assert len(snap1.annotations) == 1
        assert len(snap2.annotations) == 0


class TestCompute:
    """\\compute — frame-scoped vs. global."""

    def test_global_compute_persists(self) -> None:
        host = _FakeStarlarkHost({"x": 42})
        state = SceneState()
        state.apply_prelude(
            prelude_compute=(ComputeBlock(code="x = 42", scope="global"),),
            starlark_host=host,
        )

        frame = FrameIR(index=1, commands=())
        snap = state.apply_frame(frame)
        assert snap.bindings.get("x") == 42

    def test_frame_local_compute_scoped(self) -> None:
        host = _FakeStarlarkHost({"y": 99})
        state = SceneState()

        frame1 = FrameIR(
            index=1,
            commands=(),
            compute_blocks=(ComputeBlock(code="y = 99", scope="frame"),),
        )
        snap1 = state.apply_frame(frame1, starlark_host=host)

        frame2 = FrameIR(index=2, commands=())
        snap2 = state.apply_frame(frame2)

        assert snap1.bindings.get("y") == 99
        assert "y" not in snap2.bindings


class TestMultipleShapes:
    """Multiple shapes maintain independent state."""

    def test_independent_shape_state(self) -> None:
        state = SceneState()
        state.apply_prelude(
            shapes=(
                ShapeDecl(name="arr", shape_type="array"),
                ShapeDecl(name="stack", shape_type="stack"),
            ),
        )

        frame = FrameIR(
            index=1,
            commands=(
                ApplyCmd(target="arr.0", value="A"),
                ApplyCmd(target="stack.0", value="B"),
                RecolorCmd(target="arr.0", state="visited"),
            ),
        )
        snap = state.apply_frame(frame)

        assert snap.shape_states["arr"]["arr.0"].value == "A"
        assert snap.shape_states["arr"]["arr.0"].state == "visited"
        assert snap.shape_states["stack"]["stack.0"].value == "B"
        assert snap.shape_states["stack"]["stack.0"].state == "default"


class _FakeStarlarkHost:
    """Test double for the Starlark host."""

    def __init__(self, result: dict) -> None:
        self._result = result

    def evaluate(self, code: str, bindings: dict) -> dict:
        return dict(self._result)
