"""Tests for scriba.animation.scene — ~15 cases."""

from __future__ import annotations

import pytest

from scriba.animation.parser.ast import (
    AnnotateCommand,
    ApplyCommand,
    ComputeCommand,
    FrameIR,
    HighlightCommand,
    RecolorCommand,
    Selector,
    ShapeCommand,
)
from scriba.animation.scene import AnnotationEntry, SceneState, ShapeTargetState


# ---------------------------------------------------------------------------
# Helpers to build AST nodes succinctly
# ---------------------------------------------------------------------------


def _shape(name: str, type_name: str = "array") -> ShapeCommand:
    return ShapeCommand(line=0, col=0, name=name, type_name=type_name, params={})


def _sel(target_str: str) -> Selector:
    """Build a bare ``Selector`` from a dotted string like ``arr.0``."""
    return Selector(shape_name=target_str)


def _apply(target: str, value: str | None = None, label: str | None = None) -> ApplyCommand:
    params: dict = {}
    if value is not None:
        params["value"] = value
    if label is not None:
        params["label"] = label
    return ApplyCommand(line=0, col=0, target=_sel(target), params=params)


def _recolor(target: str, state: str) -> RecolorCommand:
    return RecolorCommand(line=0, col=0, target=_sel(target), state=state)


def _highlight(target: str) -> HighlightCommand:
    return HighlightCommand(line=0, col=0, target=_sel(target))


def _annotate(
    target: str,
    text: str = "",
    ephemeral: bool = False,
) -> AnnotateCommand:
    return AnnotateCommand(
        line=0, col=0, target=_sel(target), label=text, ephemeral=ephemeral,
    )


def _compute(source: str) -> ComputeCommand:
    return ComputeCommand(line=0, col=0, source=source)


def _frame(
    commands: tuple = (),
    compute: tuple = (),
    narrate_body: str | None = None,
) -> FrameIR:
    return FrameIR(line=0, commands=commands, compute=compute, narrate_body=narrate_body)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPrelude:
    """Shape registration and prelude commands."""

    def test_shape_declarations_recorded(self) -> None:
        state = SceneState()
        state.apply_prelude(
            shapes=(_shape("arr"), _shape("graph", "graph")),
        )
        assert "arr" in state.shape_states
        assert "graph" in state.shape_states

    def test_prelude_apply_sets_initial_state(self) -> None:
        state = SceneState()
        state.apply_prelude(
            shapes=(_shape("arr"),),
            prelude_commands=(_apply("arr.0", value="5"),),
        )
        assert state.shape_states["arr"]["arr.0"].value == "5"


class TestApply:
    """\\apply — persistent value/label."""

    def test_value_persists_across_frames(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(_shape("arr"),))

        snap1 = state.apply_frame(_frame(commands=(_apply("arr.0", value="10"),)))
        snap2 = state.apply_frame(_frame())

        assert snap1.shape_states["arr"]["arr.0"].value == "10"
        assert snap2.shape_states["arr"]["arr.0"].value == "10"

    def test_apply_with_label(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(_shape("arr"),))

        snap = state.apply_frame(
            _frame(commands=(_apply("arr.0", value="42", label="answer"),))
        )

        assert snap.shape_states["arr"]["arr.0"].value == "42"
        assert snap.shape_states["arr"]["arr.0"].label == "answer"

    def test_apply_overwrites_previous_value(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(_shape("arr"),))

        state.apply_frame(_frame(commands=(_apply("arr.0", value="10"),)))
        snap2 = state.apply_frame(_frame(commands=(_apply("arr.0", value="20"),)))

        assert snap2.shape_states["arr"]["arr.0"].value == "20"


class TestRecolor:
    """\\recolor — persistent state replacement."""

    def test_recolor_persists(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(_shape("arr"),))

        snap1 = state.apply_frame(_frame(commands=(_recolor("arr.0", "visited"),)))
        snap2 = state.apply_frame(_frame())

        assert snap1.shape_states["arr"]["arr.0"].state == "visited"
        assert snap2.shape_states["arr"]["arr.0"].state == "visited"

    def test_recolor_replaces_prior_state(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(_shape("arr"),))

        state.apply_frame(_frame(commands=(_recolor("arr.0", "visited"),)))
        snap2 = state.apply_frame(_frame(commands=(_recolor("arr.0", "active"),)))

        assert snap2.shape_states["arr"]["arr.0"].state == "active"


class TestHighlight:
    """\\highlight — ephemeral, cleared at next frame."""

    def test_highlight_present_in_frame(self) -> None:
        state = SceneState()
        snap = state.apply_frame(_frame(commands=(_highlight("arr.0"),)))
        assert "arr.0" in snap.highlights

    def test_highlight_cleared_at_next_frame(self) -> None:
        state = SceneState()
        state.apply_frame(_frame(commands=(_highlight("arr.0"),)))
        snap2 = state.apply_frame(_frame())
        assert "arr.0" not in snap2.highlights


class TestAnnotate:
    """\\annotate — persistent by default, ephemeral if flagged."""

    def test_persistent_annotation(self) -> None:
        state = SceneState()
        snap1 = state.apply_frame(_frame(commands=(_annotate("arr.0", text="note"),)))
        snap2 = state.apply_frame(_frame())

        assert len(snap1.annotations) == 1
        assert snap1.annotations[0].text == "note"
        assert len(snap2.annotations) == 1  # persists

    def test_ephemeral_annotation_cleared(self) -> None:
        state = SceneState()
        snap1 = state.apply_frame(
            _frame(commands=(_annotate("arr.0", text="temp", ephemeral=True),))
        )
        snap2 = state.apply_frame(_frame())

        assert len(snap1.annotations) == 1
        assert len(snap2.annotations) == 0


class TestCompute:
    """\\compute — frame-scoped vs. global."""

    def test_global_compute_persists(self) -> None:
        host = _FakeStarlarkHost({"x": 42})
        state = SceneState()
        state.apply_prelude(
            prelude_compute=(_compute("x = 42"),),
            starlark_host=host,
        )

        snap = state.apply_frame(_frame())
        assert snap.bindings.get("x") == 42

    def test_frame_local_compute_scoped(self) -> None:
        host = _FakeStarlarkHost({"y": 99})
        state = SceneState()

        snap1 = state.apply_frame(
            _frame(compute=(_compute("y = 99"),)),
            starlark_host=host,
        )
        snap2 = state.apply_frame(_frame())

        assert snap1.bindings.get("y") == 99
        assert "y" not in snap2.bindings


class TestMultipleShapes:
    """Multiple shapes maintain independent state."""

    def test_independent_shape_state(self) -> None:
        state = SceneState()
        state.apply_prelude(shapes=(_shape("arr"), _shape("stack")))

        snap = state.apply_frame(
            _frame(
                commands=(
                    _apply("arr.0", value="A"),
                    _apply("stack.0", value="B"),
                    _recolor("arr.0", "visited"),
                ),
            )
        )

        assert snap.shape_states["arr"]["arr.0"].value == "A"
        assert snap.shape_states["arr"]["arr.0"].state == "visited"
        assert snap.shape_states["stack"]["stack.0"].value == "B"
        assert snap.shape_states["stack"]["stack.0"].state == "default"


class _FakeStarlarkHost:
    """Test double for the Starlark host."""

    def __init__(self, result: dict) -> None:
        self._result = result

    def eval(self, bindings: dict, code: str) -> dict:
        return dict(self._result)

    def evaluate(self, code: str, bindings: dict) -> dict:
        return dict(self._result)
