"""Unit tests for the ``\\playeach`` frame macro (Phase C, item ⑥).

``\\playeach{shape.range[lo:hi]}{actions}`` is a *step-level* macro: it expands
at **parse time** into one real ``FrameIR`` per swept element, so that every
downstream consumer (scene, differ, emitter, runtime) sees an ordinary
hand-authored ``\\step`` sequence.  This is the load-bearing A-5 rule
(``docs/spec/motion-ruleset.md``): *a frame macro expands to indistinguishable
hand-frames*.

Coverage:
- N frames generated (1-D range and 2-D block)
- Byte-indistinguishability: the FrameData a ``\\playeach`` produces is *equal*
  to the FrameData the equivalent hand-authored ``\\step`` list produces
- narrate template ``${i}`` / ``${r}``/``${c}`` interpolation
- cursor binding-caret follows the sweep
- frame cap (E1493), bad selector (E1494), bad action (E1495)
- undeclared shape degrades through the normal E1116 scene path
- a ``\\foreach`` in a neighbouring step is unaffected
"""

from __future__ import annotations

import pytest

from scriba import RenderContext
from scriba.animation.parser.ast import (
    CellAccessor,
    CursorCommand,
    FrameIR,
    RecolorCommand,
    Selector,
)
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.renderer import AnimationRenderer
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(source: str):
    return SceneParser().parse(source)


def _ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={},
        render_inline_tex=None,
    )


def _framedata(source: str):
    """Materialise *source* into the downstream ``list[FrameData]``.

    This is exactly the list the emitter consumes, so equality between two
    FrameData lists is the operational definition of A-5 indistinguishability.
    """
    ir = _parse(source)
    renderer = AnimationRenderer()
    return renderer._materialise(ir, _ctx(), "demo")


# ===================================================================
# Frame generation — the macro produces N real FrameIR at parse time
# ===================================================================


class TestPlayeachExpansion:
    def test_range_generates_one_frame_per_element(self):
        """``\\playeach{a.range[1:5]}{state=done}`` → 5 top-level frames."""
        ir = _parse(
            "\\shape{a}{Array}{size=6}\n"
            "\\playeach{a.range[1:5]}{state=done}\n"
        )
        assert len(ir.frames) == 5
        for offset, frame in enumerate(ir.frames):
            assert isinstance(frame, FrameIR)
            recolors = [c for c in frame.commands if isinstance(c, RecolorCommand)]
            assert len(recolors) == 1
            acc = recolors[0].target.accessor
            assert isinstance(acc, CellAccessor)
            assert acc.indices == (offset + 1,)
            assert recolors[0].state == "done"

    def test_range_frames_are_plain_frameir_not_a_macro_node(self):
        """No downstream consumer should see a bespoke node — just FrameIR."""
        ir = _parse(
            "\\shape{a}{Array}{size=4}\n"
            "\\playeach{a.range[0:2]}{state=current}\n"
        )
        assert all(type(f) is FrameIR for f in ir.frames)
        assert len(ir.frames) == 3

    def test_block_generates_frame_per_cell_row_major(self):
        """2-D ``block`` sweeps the inclusive product row-major."""
        ir = _parse(
            "\\shape{g}{Grid}{rows=2, cols=2}\n"
            "\\playeach{g.block[0:1][0:1]}{state=done}\n"
        )
        assert len(ir.frames) == 4
        seen = []
        for frame in ir.frames:
            rc = [c for c in frame.commands if isinstance(c, RecolorCommand)][0]
            seen.append(rc.target.accessor.indices)
        assert seen == [(0, 0), (0, 1), (1, 0), (1, 1)]

    def test_total_frames_counts_generated_frames(self):
        """Each FrameData reports total_frames == the generated frame count."""
        frames = _framedata(
            "\\shape{a}{Array}{size=6}\n"
            "\\playeach{a.range[1:5]}{state=done}\n"
        )
        assert len(frames) == 5
        assert all(fd.total_frames == 5 for fd in frames)
        assert [fd.step_number for fd in frames] == [1, 2, 3, 4, 5]


# ===================================================================
# A-5 — indistinguishable from a hand-authored \step list
# ===================================================================


class TestPlayeachIndistinguishable:
    def test_framedata_equals_handwritten_steps(self):
        """The macro output must equal the hand-authored equivalent, field for
        field, across the whole FrameData list (A-5)."""
        macro = (
            "\\shape{fac}{Array}{size=6}\n"
            "\\playeach{fac.range[1:5]}{state=done, narrate=\"fill ${i}\"}\n"
        )
        hand = (
            "\\shape{fac}{Array}{size=6}\n"
            "\\step\n\\recolor{fac.cell[1]}{state=done}\n\\narrate{fill 1}\n"
            "\\step\n\\recolor{fac.cell[2]}{state=done}\n\\narrate{fill 2}\n"
            "\\step\n\\recolor{fac.cell[3]}{state=done}\n\\narrate{fill 3}\n"
            "\\step\n\\recolor{fac.cell[4]}{state=done}\n\\narrate{fill 4}\n"
            "\\step\n\\recolor{fac.cell[5]}{state=done}\n\\narrate{fill 5}\n"
        )
        assert _framedata(macro) == _framedata(hand)

    def test_html_bytes_equal_handwritten_steps(self):
        """The strongest form: full emitted HTML (svg + tr + fs manifest) is
        byte-identical to the hand-authored sequence when the scene id is
        pinned (id= neutralises the source-hash scene id)."""
        from scriba.core.artifact import Block

        def _html(body: str) -> str:
            raw = "\\begin{animation}[id=demo]\n" + body + "\\end{animation}"
            block = Block(start=0, end=len(raw), kind="animation", raw=raw)
            return AnimationRenderer().render_block(block, _ctx()).html

        macro = (
            "\\shape{fac}{Array}{size=6}\n"
            "\\playeach{fac.range[1:4]}{state=done, cursor=w}\n"
        )
        hand = (
            "\\shape{fac}{Array}{size=6}\n"
            "\\step\n\\recolor{fac.cell[1]}{state=done}\n\\cursor{fac}{id=w, at=1}\n"
            "\\step\n\\recolor{fac.cell[2]}{state=done}\n\\cursor{fac}{id=w, at=2}\n"
            "\\step\n\\recolor{fac.cell[3]}{state=done}\n\\cursor{fac}{id=w, at=3}\n"
            "\\step\n\\recolor{fac.cell[4]}{state=done}\n\\cursor{fac}{id=w, at=4}\n"
        )
        assert _html(macro) == _html(hand)


# ===================================================================
# Narration templating
# ===================================================================


class TestPlayeachNarrate:
    def test_narrate_interpolates_element_index(self):
        frames = _framedata(
            "\\shape{a}{Array}{size=6}\n"
            "\\playeach{a.range[1:3]}{state=done, narrate=\"scan $a[${i}]$\"}\n"
        )
        texts = [fd.narration_html for fd in frames]
        assert "1" in texts[0] and "2" in texts[1] and "3" in texts[2]
        # The loop placeholder must not survive into the rendered narration.
        assert all("${i}" not in t for t in texts)

    def test_block_narrate_interpolates_row_and_col(self):
        ir = _parse(
            "\\shape{g}{Grid}{rows=2, cols=2}\n"
            "\\playeach{g.block[0:1][0:1]}{state=done, narrate=\"r${r} c${c}\"}\n"
        )
        bodies = [f.narrate_body for f in ir.frames]
        assert bodies == ["r0 c0", "r0 c1", "r1 c0", "r1 c1"]

    def test_non_loop_binding_placeholder_is_preserved(self):
        """Only the loop variable is substituted at parse time; other ``${...}``
        refs are left for the scene-time compute interpolation."""
        ir = _parse(
            "\\shape{a}{Array}{size=6}\n"
            "\\playeach{a.range[1:2]}{state=done, narrate=\"${total} at ${i}\"}\n"
        )
        assert ir.frames[0].narrate_body == "${total} at 1"


# ===================================================================
# Cursor binding-caret follows the sweep
# ===================================================================


class TestPlayeachCursor:
    def test_cursor_caret_tracks_each_element(self):
        frames = _framedata(
            "\\shape{a}{Array}{size=6}\n"
            "\\playeach{a.range[1:3]}{state=done, cursor=w}\n"
        )
        for offset, fd in enumerate(frames):
            assert fd.cursors is not None and len(fd.cursors) == 1
            caret = fd.cursors[0]
            assert caret["id"] == "w"
            assert caret["index"] == offset + 1

    def test_cursor_only_sweep_is_allowed(self):
        """A caret sweep with no recolor is a valid per-element action."""
        ir = _parse(
            "\\shape{a}{Array}{size=6}\n"
            "\\playeach{a.range[1:3]}{cursor=w}\n"
        )
        assert len(ir.frames) == 3
        for frame in ir.frames:
            assert any(isinstance(c, CursorCommand) for c in frame.commands)
            assert not any(isinstance(c, RecolorCommand) for c in frame.commands)


# ===================================================================
# Boundary interaction with the surrounding \step stream
# ===================================================================


class TestPlayeachBoundaries:
    def test_pending_step_is_flushed_before_macro_frames(self):
        """A ``\\step`` that precedes ``\\playeach`` becomes its own frame,
        ahead of the generated frames."""
        ir = _parse(
            "\\shape{a}{Array}{size=6}\n"
            "\\step\n\\recolor{a.cell[0]}{state=current}\n"
            "\\playeach{a.range[1:3]}{state=done}\n"
        )
        assert len(ir.frames) == 4  # 1 pending + 3 generated
        first = ir.frames[0].commands[0]
        assert isinstance(first, RecolorCommand)
        assert first.target.accessor.indices == (0,)

    def test_trailing_step_after_macro(self):
        """Content after the macro opens a fresh trailing frame; the macro does
        not leave a spurious empty frame."""
        ir = _parse(
            "\\shape{a}{Array}{size=6}\n"
            "\\playeach{a.range[1:3]}{state=done}\n"
            "\\step\n\\recolor{a.cell[5]}{state=good}\n"
        )
        assert len(ir.frames) == 4  # 3 generated + 1 trailing
        assert ir.frames[-1].commands[0].target.accessor.indices == (5,)

    def test_macro_at_end_leaves_no_empty_frame(self):
        ir = _parse(
            "\\shape{a}{Array}{size=6}\n"
            "\\playeach{a.range[1:3]}{state=done}\n"
        )
        assert len(ir.frames) == 3
        assert all(f.commands for f in ir.frames)

    def test_foreach_in_neighbouring_step_unaffected(self):
        """A ``\\foreach`` inside an ordinary step still expands normally when a
        ``\\playeach`` lives in the same animation."""
        frames = _framedata(
            "\\shape{a}{Array}{size=6}\n"
            "\\playeach{a.range[1:2]}{state=done}\n"
            "\\step\n"
            "\\foreach{i}{3..5}\n"
            "\\recolor{a.cell[${i}]}{state=path}\n"
            "\\endforeach\n"
        )
        assert len(frames) == 3  # 2 generated + 1 foreach step
        last = frames[-1].shape_states["a"]
        for idx in (3, 4, 5):
            assert last[f"a.cell[{idx}]"]["state"] == "path"


# ===================================================================
# Error handling
# ===================================================================


class TestPlayeachErrors:
    def test_non_range_selector_is_e1494(self):
        with pytest.raises(ValidationError, match="E1494"):
            _parse(
                "\\shape{a}{Array}{size=6}\n"
                "\\playeach{a.cell[0]}{state=done}\n"
            )

    def test_bare_shape_selector_is_e1494(self):
        with pytest.raises(ValidationError, match="E1494"):
            _parse(
                "\\shape{a}{Array}{size=6}\n"
                "\\playeach{a}{state=done}\n"
            )

    def test_interpolated_bounds_is_e1494(self):
        """Bounds must be literal integers — the frame count is fixed at build."""
        with pytest.raises(ValidationError, match="E1494"):
            _parse(
                "\\shape{a}{Array}{size=6}\n"
                "\\compute{x = 3}\n"
                "\\playeach{a.range[1:${x}]}{state=done}\n"
            )

    def test_frame_cap_exceeded_is_e1493(self):
        with pytest.raises(ValidationError, match="E1493"):
            _parse(
                "\\shape{a}{Array}{size=200}\n"
                "\\playeach{a.range[1:100]}{state=done}\n"
            )

    def test_no_action_is_e1495(self):
        with pytest.raises(ValidationError, match="E1495"):
            _parse(
                "\\shape{a}{Array}{size=6}\n"
                "\\playeach{a.range[1:3]}{}\n"
            )

    def test_cursor_with_block_is_e1495(self):
        """The caret is a 1-D construct; it may not ride a 2-D block sweep."""
        with pytest.raises(ValidationError, match="E1495"):
            _parse(
                "\\shape{g}{Grid}{rows=2, cols=2}\n"
                "\\playeach{g.block[0:1][0:1]}{state=done, cursor=w}\n"
            )

    def test_invalid_state_reuses_recolor_e1109(self):
        with pytest.raises(ValidationError, match="E1109"):
            _parse(
                "\\shape{a}{Array}{size=6}\n"
                "\\playeach{a.range[1:3]}{state=bogus}\n"
            )

    def test_undeclared_shape_degrades_through_e1116(self):
        """A macro over an undeclared shape must surface the normal scene-level
        E1116, proving the generated commands travel the ordinary path."""
        from scriba.animation.errors import AnimationError

        with pytest.raises(AnimationError) as exc:
            _framedata(
                "\\shape{a}{Array}{size=6}\n"
                "\\playeach{ghost.range[1:3]}{state=done}\n"
            )
        assert exc.value.code == "E1116"

    def test_playeach_inside_foreach_is_forbidden(self):
        with pytest.raises(ValidationError, match="E1172"):
            _parse(
                "\\shape{a}{Array}{size=6}\n"
                "\\step\n"
                "\\foreach{i}{0..2}\n"
                "\\playeach{a.range[1:3]}{state=done}\n"
                "\\endforeach\n"
            )
