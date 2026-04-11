"""Unit tests for the ``\\cursor`` animation command.

Covers parser-level behaviour (AST shape, error codes) and scene-level
behaviour (state transitions, multi-target, ephemeral vs persistent,
substory interaction, interpolation via compute).
"""

from __future__ import annotations

from typing import Any

import pytest

from scriba.animation.parser.ast import (
    CursorCommand,
    FrameIR,
    InterpolationRef,
    ShapeCommand,
)
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.scene import SceneState
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(source: str):
    return SceneParser().parse(source)


def _shape(name: str, type_name: str = "array") -> ShapeCommand:
    return ShapeCommand(line=0, col=0, name=name, type_name=type_name, params={})


class _MockStarlarkHost:
    """Minimal Starlark host that just exec()s the source locally."""

    def eval(
        self,
        globals: dict[str, Any],
        source: str,
        *,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        namespace = dict(globals)
        exec(  # noqa: S102 — test-only, not exposed to untrusted input
            source,
            {"__builtins__": {"len": len, "range": range, "list": list}},
            namespace,
        )
        return {k: v for k, v in namespace.items() if k not in globals}


# ===========================================================================
# Parser tests
# ===========================================================================


class TestCursorParsing:
    """Parser-level tests for ``\\cursor``."""

    def test_basic_cursor_parses(self) -> None:
        """``\\cursor{a.cell}{3}`` parses to a CursorCommand with one target."""
        ir = _parse(
            "\\shape{a}{Array}{values=[0,1,2,3,4,5,6,7,8,9]}\n"
            "\\step\n"
            "\\cursor{a.cell}{3}\n"
        )
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, CursorCommand)
        assert cmd.targets == ("a.cell",)
        assert cmd.index == 3
        assert cmd.prev_state == "dim"
        assert cmd.curr_state == "current"

    def test_multi_target_cursor_parses(self) -> None:
        """Comma-separated targets become a tuple of prefixes."""
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\shape{b}{Array}{values=[4,5,6]}\n"
            "\\step\n"
            "\\cursor{a.cell, b.cell}{0}\n"
        )
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, CursorCommand)
        assert cmd.targets == ("a.cell", "b.cell")
        assert cmd.index == 0

    def test_cursor_with_interpolated_index_parses(self) -> None:
        """``\\cursor{a.cell}{${i}}`` stores ``index`` as the raw string."""
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\compute{i = 2}\n"
            "\\step\n"
            "\\cursor{a.cell}{${i}}\n"
        )
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, CursorCommand)
        assert cmd.index == "${i}"

    def test_cursor_with_custom_states_parses(self) -> None:
        """``\\cursor{a.cell}{2, prev_state=done, curr_state=highlight}`` honours the params."""
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\cursor{a.cell}{2, prev_state=done, curr_state=highlight}\n"
        )
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, CursorCommand)
        assert cmd.prev_state == "done"
        assert cmd.curr_state == "highlight"

    def test_cursor_empty_targets_raises_e1180(self) -> None:
        """An empty target list raises ``E1180``."""
        src = (
            "\\shape{a}{Array}{values=[1,2]}\n"
            "\\step\n"
            "\\cursor{}{0}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1180"

    def test_cursor_missing_index_raises_e1181(self) -> None:
        """Missing index parameter raises ``E1181``."""
        src = (
            "\\shape{a}{Array}{values=[1,2]}\n"
            "\\step\n"
            "\\cursor{a.cell}{}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1181"

    def test_cursor_invalid_prev_state_raises_e1182(self) -> None:
        """Unknown ``prev_state`` raises ``E1182``."""
        src = (
            "\\shape{a}{Array}{values=[1,2]}\n"
            "\\step\n"
            "\\cursor{a.cell}{0, prev_state=bogus}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1182"

    def test_cursor_invalid_curr_state_raises_e1182(self) -> None:
        """Unknown ``curr_state`` raises ``E1182``."""
        src = (
            "\\shape{a}{Array}{values=[1,2]}\n"
            "\\step\n"
            "\\cursor{a.cell}{0, curr_state=nope}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1182"


# ===========================================================================
# Scene-state tests
# ===========================================================================


class TestCursorScene:
    """Scene-level tests — verify state transitions across frames."""

    def test_cursor_advances_target_state(self) -> None:
        """First cursor in a frame sets the target to ``curr_state``."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        cmd = CursorCommand(targets=("a.cell",), index=3)
        snap = state.apply_frame(FrameIR(line=0, commands=(cmd,)))

        key = "a.cell[3]"
        assert snap.shape_states["a"][key].state == "current"

    def test_cursor_clears_previous_on_frame_transition(self) -> None:
        """A cursor at a new index moves the ``current`` marker."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        state.apply_frame(
            FrameIR(line=0, commands=(CursorCommand(targets=("a.cell",), index=3),)),
        )
        snap2 = state.apply_frame(
            FrameIR(line=0, commands=(CursorCommand(targets=("a.cell",), index=5),)),
        )

        # New position is current.
        assert snap2.shape_states["a"]["a.cell[5]"].state == "current"
        # Previous position rolled back to the default ``prev_state`` (dim).
        assert snap2.shape_states["a"]["a.cell[3]"].state == "dim"

    def test_cursor_multi_target_updates_all_shapes(self) -> None:
        """Multi-target cursor sets ``current`` on every listed shape prefix."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"), _shape("b")))

        cmd = CursorCommand(targets=("a.cell", "b.cell"), index=0)
        snap = state.apply_frame(FrameIR(line=0, commands=(cmd,)))

        assert snap.shape_states["a"]["a.cell[0]"].state == "current"
        assert snap.shape_states["b"]["b.cell[0]"].state == "current"

    def test_cursor_state_persists_when_no_new_cursor(self) -> None:
        """A cursor placed in frame N persists into frame N+1 (it is state)."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        state.apply_frame(
            FrameIR(line=0, commands=(CursorCommand(targets=("a.cell",), index=2),)),
        )
        snap2 = state.apply_frame(FrameIR(line=0, commands=()))

        assert snap2.shape_states["a"]["a.cell[2]"].state == "current"

    def test_cursor_custom_prev_state(self) -> None:
        """Custom ``prev_state`` is applied to the previously-current cell."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        state.apply_frame(
            FrameIR(line=0, commands=(CursorCommand(targets=("a.cell",), index=0),)),
        )
        snap2 = state.apply_frame(
            FrameIR(
                line=0,
                commands=(
                    CursorCommand(
                        targets=("a.cell",),
                        index=1,
                        prev_state="done",
                    ),
                ),
            ),
        )
        assert snap2.shape_states["a"]["a.cell[0]"].state == "done"
        assert snap2.shape_states["a"]["a.cell[1]"].state == "current"

    def test_cursor_unknown_shape_creates_entry(self) -> None:
        """Cursor on an undeclared shape prefix records a target state.

        The scene layer currently does not hard-error on unknown shape names
        at ``\\cursor`` time (parser accepts any prefix; runtime validation
        is deferred to the emitter). This test pins current behaviour so a
        later tightening is visible.
        """
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        cmd = CursorCommand(targets=("ghost.cell",), index=0)
        # Should not raise.
        snap = state.apply_frame(FrameIR(line=0, commands=(cmd,)))

        assert "ghost" in snap.shape_states
        assert snap.shape_states["ghost"]["ghost.cell[0]"].state == "current"


# ===========================================================================
# Cursor inside \substory
# ===========================================================================


class TestCursorInSubstory:
    """``\\cursor`` should be a legal mutation inside a ``\\substory`` block."""

    def test_cursor_inside_substory_parses(self) -> None:
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3,4,5]}\n"
            "\\step\n"
            "\\narrate{outer}\n"
            '\\substory[title="Sub"]\n'
            "\\step\n"
            "\\narrate{inner}\n"
            "\\cursor{a.cell}{2}\n"
            "\\endsubstory\n"
        )
        outer_frame = ir.frames[0]
        assert len(outer_frame.substories) == 1
        inner_frame = outer_frame.substories[0].frames[0]
        cursors = [c for c in inner_frame.commands if isinstance(c, CursorCommand)]
        assert len(cursors) == 1
        assert cursors[0].index == 2
        assert cursors[0].targets == ("a.cell",)
