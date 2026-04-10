"""Unit tests for \\foreach / \\endforeach loop expansion (C1).

Covers:
- Parser tests: parsing foreach AST nodes from .tex source
- Scene expansion tests: expanding ForeachCommand into flat mutation commands
- Error handling: E1170-E1174
"""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import MagicMock

import pytest

from scriba.animation.parser.ast import (
    AnnotateCommand,
    ApplyCommand,
    CellAccessor,
    ComputeCommand,
    ForeachCommand,
    FrameIR,
    HighlightCommand,
    InterpolationRef,
    RecolorCommand,
    Selector,
    ShapeCommand,
)
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.scene import SceneState
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(source: str):
    """Parse source and return AnimationIR."""
    return SceneParser().parse(source)


def _shape(name: str, type_name: str = "array") -> ShapeCommand:
    return ShapeCommand(line=0, col=0, name=name, type_name=type_name, params={})


def _sel(target_str: str) -> Selector:
    return Selector(shape_name=target_str)


def _recolor(target: str, state: str) -> RecolorCommand:
    return RecolorCommand(line=0, col=0, target=_sel(target), state=state)


def _annotate(
    target: str,
    text: str = "",
    arrow: bool = False,
) -> AnnotateCommand:
    return AnnotateCommand(
        line=0, col=0, target=_sel(target), label=text, arrow=arrow,
    )


def _frame(
    commands: tuple = (),
    compute: tuple = (),
    narrate_body: str | None = None,
) -> FrameIR:
    return FrameIR(line=0, commands=commands, compute=compute, narrate_body=narrate_body)


class MockStarlarkHost:
    """Minimal mock that evaluates simple Python expressions."""

    def eval(
        self,
        globals: dict[str, Any],
        source: str,
        *,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        namespace = dict(globals)
        exec(source, {"__builtins__": {"len": len, "range": range, "list": list}}, namespace)
        return {k: v for k, v in namespace.items() if k not in globals}


# ===================================================================
# Parser tests
# ===================================================================


class TestForeachParsing:
    """Parser tests for \\foreach blocks."""

    def test_foreach_range_parses(self):
        """\\foreach{i}{0..2}{\\recolor{...}{state=done}}\\endforeach parses to ForeachCommand."""
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\foreach{i}{0..2}\n"
            "\\recolor{a.cell[${i}]}{state=done}\n"
            "\\endforeach\n"
        )
        frame = ir.frames[0]
        assert len(frame.commands) == 1
        cmd = frame.commands[0]
        assert isinstance(cmd, ForeachCommand)
        assert cmd.variable == "i"
        assert cmd.iterable_raw == "0..2"
        assert len(cmd.body) == 1
        assert isinstance(cmd.body[0], RecolorCommand)

    def test_foreach_binding_parses(self):
        """\\foreach{i}{${xs}}{...}\\endforeach parses with interpolation ref."""
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\foreach{i}{${xs}}\n"
            "\\recolor{a.cell[${i}]}{state=done}\n"
            "\\endforeach\n"
        )
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, ForeachCommand)
        assert cmd.iterable_raw == "${xs}"

    def test_foreach_nested_parses(self):
        """Nested foreach parses correctly."""
        ir = _parse(
            "\\shape{g}{Grid}{rows=3, cols=3}\n"
            "\\step\n"
            "\\foreach{i}{0..1}\n"
            "\\foreach{j}{0..1}\n"
            "\\recolor{g.cell[${i}][${j}]}{state=done}\n"
            "\\endforeach\n"
            "\\endforeach\n"
        )
        outer = ir.frames[0].commands[0]
        assert isinstance(outer, ForeachCommand)
        assert outer.variable == "i"
        assert len(outer.body) == 1
        inner = outer.body[0]
        assert isinstance(inner, ForeachCommand)
        assert inner.variable == "j"
        assert len(inner.body) == 1
        assert isinstance(inner.body[0], RecolorCommand)

    def test_foreach_empty_body_error(self):
        """\\foreach{i}{0..2}\\endforeach with no body raises E1171."""
        src = (
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\foreach{i}{0..2}\n"
            "\\endforeach\n"
        )
        with pytest.raises(ValidationError, match="E1171"):
            _parse(src)

    def test_foreach_unclosed_error(self):
        """\\foreach{i}{0..2}{...} without \\endforeach raises E1172."""
        src = (
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\foreach{i}{0..2}\n"
            "\\recolor{a.cell[0]}{state=done}\n"
        )
        with pytest.raises(ValidationError, match="E1172"):
            _parse(src)


# ===================================================================
# Scene expansion tests
# ===================================================================


class TestForeachExpansion:
    """Scene-level tests for foreach command expansion."""

    def test_foreach_range_expands(self):
        """foreach over 0..2 expands to 3 recolor commands."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        foreach_cmd = ForeachCommand(
            variable="i",
            iterable_raw="0..2",
            body=(
                RecolorCommand(
                    line=0, col=0,
                    target=Selector(
                        shape_name="a",
                        accessor=CellAccessor(indices=(InterpolationRef(name="i"),)),
                    ),
                    state="done",
                ),
            ),
            line=1,
        )

        frame = _frame(commands=(foreach_cmd,))
        snap = state.apply_frame(frame)

        # Cells 0, 1, 2 should all be "done"
        for idx in range(3):
            key = f"a.cell[{idx}]"
            assert key in snap.shape_states["a"], f"Missing key {key}"
            assert snap.shape_states["a"][key].state == "done"

    def test_foreach_binding_expands(self):
        """foreach over ${xs} where xs=[1,3] expands to 2 commands."""
        host = MockStarlarkHost()
        state = SceneState()
        state.apply_prelude(
            shapes=(_shape("a"),),
            prelude_compute=(ComputeCommand(line=0, col=0, source="xs = [1, 3]"),),
            starlark_host=host,
        )

        foreach_cmd = ForeachCommand(
            variable="i",
            iterable_raw="${xs}",
            body=(
                RecolorCommand(
                    line=0, col=0,
                    target=Selector(
                        shape_name="a",
                        accessor=CellAccessor(indices=(InterpolationRef(name="i"),)),
                    ),
                    state="path",
                ),
            ),
            line=1,
        )

        frame = _frame(commands=(foreach_cmd,))
        snap = state.apply_frame(frame, starlark_host=host)

        assert "a.cell[1]" in snap.shape_states["a"]
        assert snap.shape_states["a"]["a.cell[1]"].state == "path"
        assert "a.cell[3]" in snap.shape_states["a"]
        assert snap.shape_states["a"]["a.cell[3]"].state == "path"
        # Verify only those two cells were touched (plus any default)
        done_cells = {
            k for k, v in snap.shape_states["a"].items() if v.state == "path"
        }
        assert done_cells == {"a.cell[1]", "a.cell[3]"}

    def test_foreach_nested_expands(self):
        """2-level nested foreach expands correctly."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("g"),))

        inner = ForeachCommand(
            variable="j",
            iterable_raw="0..1",
            body=(
                RecolorCommand(
                    line=0, col=0,
                    target=Selector(
                        shape_name="g",
                        accessor=CellAccessor(
                            indices=(
                                InterpolationRef(name="i"),
                                InterpolationRef(name="j"),
                            ),
                        ),
                    ),
                    state="done",
                ),
            ),
            line=2,
        )

        outer = ForeachCommand(
            variable="i",
            iterable_raw="0..1",
            body=(inner,),
            line=1,
        )

        frame = _frame(commands=(outer,))
        snap = state.apply_frame(frame)

        # 2x2 = 4 cells should be set to "done"
        for i in range(2):
            for j in range(2):
                key = f"g.cell[{i}][{j}]"
                assert key in snap.shape_states["g"], f"Missing {key}"
                assert snap.shape_states["g"][key].state == "done"

    def test_foreach_max_depth_error(self):
        """4-level nesting raises E1170."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        recolor = RecolorCommand(
            line=0, col=0,
            target=Selector(shape_name="a"),
            state="done",
        )

        # Build 4-deep nesting: foreach d -> foreach c -> foreach b -> foreach a -> recolor
        cmd = recolor
        for var_name in ["a", "b", "c", "d"]:
            cmd = ForeachCommand(
                variable=var_name,
                iterable_raw="0..1",
                body=(cmd,),
                line=0,
            )

        frame = _frame(commands=(cmd,))
        with pytest.raises(ValidationError, match="E1170"):
            state.apply_frame(frame)

    def test_foreach_invalid_iterable_error(self):
        """Non-iterable raises E1173."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        foreach_cmd = ForeachCommand(
            variable="i",
            iterable_raw="not_a_range_or_binding",
            body=(
                RecolorCommand(
                    line=0, col=0,
                    target=Selector(shape_name="a"),
                    state="done",
                ),
            ),
            line=1,
        )

        frame = _frame(commands=(foreach_cmd,))
        with pytest.raises(ValidationError, match="E1173"):
            state.apply_frame(frame)

    def test_foreach_substitution_in_params(self):
        """${var} replaced in both selector AND param values."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        foreach_cmd = ForeachCommand(
            variable="i",
            iterable_raw="0..1",
            body=(
                AnnotateCommand(
                    line=0, col=0,
                    target=Selector(
                        shape_name="a",
                        accessor=CellAccessor(indices=(InterpolationRef(name="i"),)),
                    ),
                    label="cell ${i}",
                ),
            ),
            line=1,
        )

        frame = _frame(commands=(foreach_cmd,))
        snap = state.apply_frame(frame)

        # Verify annotations were created with substituted labels
        labels = {a.text for a in snap.annotations}
        assert "cell 0" in labels
        assert "cell 1" in labels

    def test_foreach_in_prelude(self):
        """foreach works before \\step (in prelude)."""
        state = SceneState()

        foreach_cmd = ForeachCommand(
            variable="i",
            iterable_raw="0..2",
            body=(
                RecolorCommand(
                    line=0, col=0,
                    target=Selector(
                        shape_name="a",
                        accessor=CellAccessor(indices=(InterpolationRef(name="i"),)),
                    ),
                    state="done",
                ),
            ),
            line=1,
        )

        state.apply_prelude(
            shapes=(_shape("a"),),
            prelude_commands=(foreach_cmd,),
        )

        # After prelude, check cells are set
        for idx in range(3):
            key = f"a.cell[{idx}]"
            assert key in state.shape_states["a"]
            assert state.shape_states["a"][key].state == "done"

    def test_foreach_in_step(self):
        """foreach works inside a step."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        foreach_cmd = ForeachCommand(
            variable="i",
            iterable_raw="0..1",
            body=(
                RecolorCommand(
                    line=0, col=0,
                    target=Selector(
                        shape_name="a",
                        accessor=CellAccessor(indices=(InterpolationRef(name="i"),)),
                    ),
                    state="current",
                ),
            ),
            line=1,
        )

        frame = _frame(commands=(foreach_cmd,))
        snap = state.apply_frame(frame)

        assert snap.shape_states["a"]["a.cell[0]"].state == "current"
        assert snap.shape_states["a"]["a.cell[1]"].state == "current"

    def test_foreach_with_annotate(self):
        """foreach body containing \\annotate with arrow."""
        state = SceneState()
        state.apply_prelude(shapes=(_shape("a"),))

        foreach_cmd = ForeachCommand(
            variable="i",
            iterable_raw="0..1",
            body=(
                AnnotateCommand(
                    line=0, col=0,
                    target=Selector(
                        shape_name="a",
                        accessor=CellAccessor(indices=(InterpolationRef(name="i"),)),
                    ),
                    label="note",
                    arrow=True,
                ),
            ),
            line=1,
        )

        frame = _frame(commands=(foreach_cmd,))
        snap = state.apply_frame(frame)

        assert len(snap.annotations) == 2
        targets = {a.target for a in snap.annotations}
        assert "a.cell[0]" in targets
        assert "a.cell[1]" in targets
        assert all(a.arrow for a in snap.annotations)


# ===================================================================
# End-to-end parser + scene tests
# ===================================================================


class TestForeachEndToEnd:
    """Tests that parse .tex source and run through scene expansion."""

    def test_foreach_range_e2e(self):
        """Parse and expand a foreach over a range."""
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\step\n"
            "\\foreach{i}{0..2}\n"
            "\\recolor{a.cell[${i}]}{state=done}\n"
            "\\endforeach\n"
        )

        state = SceneState()
        state.apply_prelude(shapes=ir.shapes)
        snap = state.apply_frame(ir.frames[0])

        for idx in range(3):
            key = f"a.cell[{idx}]"
            assert key in snap.shape_states["a"]
            assert snap.shape_states["a"][key].state == "done"

    def test_foreach_in_prelude_e2e(self):
        """Parse foreach in prelude (before \\step)."""
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3]}\n"
            "\\foreach{i}{0..2}\n"
            "\\recolor{a.cell[${i}]}{state=done}\n"
            "\\endforeach\n"
            "\\step\n"
            "\\narrate{All done}\n"
        )

        state = SceneState()
        state.apply_prelude(
            shapes=ir.shapes,
            prelude_commands=ir.prelude_commands,
        )

        for idx in range(3):
            key = f"a.cell[{idx}]"
            assert key in state.shape_states["a"]
            assert state.shape_states["a"][key].state == "done"

    def test_foreach_with_compute_binding_e2e(self):
        """Parse foreach that iterates over a compute-bound list."""
        ir = _parse(
            "\\shape{a}{Array}{values=[1,2,3,4]}\n"
            "\\compute{path = [0, 2, 3]}\n"
            "\\step\n"
            "\\foreach{i}{${path}}\n"
            "\\recolor{a.cell[${i}]}{state=path}\n"
            "\\endforeach\n"
        )

        host = MockStarlarkHost()
        state = SceneState()
        state.apply_prelude(
            shapes=ir.shapes,
            prelude_compute=ir.prelude_compute,
            starlark_host=host,
        )
        snap = state.apply_frame(ir.frames[0], starlark_host=host)

        for idx in [0, 2, 3]:
            key = f"a.cell[{idx}]"
            assert key in snap.shape_states["a"]
            assert snap.shape_states["a"][key].state == "path"
