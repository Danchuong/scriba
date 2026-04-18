"""Unit tests for _parse_foreach and _parse_foreach_body.

Exercises the foreach parsing logic through SceneParser.parse() end-to-end
with narrow inputs covering positive paths and error conditions.

Wave F1a prerequisite for grammar.py mixin split (Wave F2-F6).
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.parser.ast import (
    ForeachCommand,
    RecolorCommand,
    ApplyCommand,
    HighlightCommand,
)
from scriba.core.errors import ValidationError


@pytest.fixture()
def parser() -> SceneParser:
    return SceneParser()


@pytest.mark.unit
class TestForeachPositivePaths:
    """Positive: valid foreach constructs parse without error."""

    def test_simple_foreach_range(self, parser: SceneParser) -> None:
        """Basic foreach with a range iterable produces a ForeachCommand."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..3}\n"
            "  \\recolor{a.cell[${i}]}{state=current}\n"
            "\\endforeach\n"
        )
        ir = parser.parse(src)
        assert len(ir.frames) == 1
        cmds = ir.frames[0].commands
        assert len(cmds) == 1
        fe = cmds[0]
        assert isinstance(fe, ForeachCommand)
        assert fe.variable == "i"
        assert fe.iterable_raw == "0..3"
        assert len(fe.body) == 1
        assert isinstance(fe.body[0], RecolorCommand)

    def test_foreach_with_multiple_body_commands(self, parser: SceneParser) -> None:
        """foreach body can hold more than one command."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..3}\n"
            "  \\recolor{a.cell[${i}]}{state=current}\n"
            "  \\apply{a.cell[${i}]}{value=1}\n"
            "\\endforeach\n"
        )
        ir = parser.parse(src)
        fe = ir.frames[0].commands[0]
        assert isinstance(fe, ForeachCommand)
        assert len(fe.body) == 2
        assert isinstance(fe.body[0], RecolorCommand)
        assert isinstance(fe.body[1], ApplyCommand)

    def test_nested_foreach(self, parser: SceneParser) -> None:
        """Two-level nested foreach is legal (depth 2 <= MAX 3)."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..1}\n"
            "  \\foreach{j}{0..1}\n"
            "    \\recolor{a.cell[${j}]}{state=done}\n"
            "  \\endforeach\n"
            "\\endforeach\n"
        )
        ir = parser.parse(src)
        outer = ir.frames[0].commands[0]
        assert isinstance(outer, ForeachCommand)
        assert outer.variable == "i"
        assert len(outer.body) == 1
        inner = outer.body[0]
        assert isinstance(inner, ForeachCommand)
        assert inner.variable == "j"

    def test_foreach_with_list_literal_iterable(self, parser: SceneParser) -> None:
        """foreach accepts a list literal as the iterable."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{[0,1,2,3]}\n"
            "  \\recolor{a.cell[${i}]}{state=good}\n"
            "\\endforeach\n"
        )
        ir = parser.parse(src)
        fe = ir.frames[0].commands[0]
        assert isinstance(fe, ForeachCommand)
        assert fe.iterable_raw == "[0,1,2,3]"

    def test_foreach_with_compute_binding_iterable(self, parser: SceneParser) -> None:
        """foreach iterable can reference a compute binding via ${name}."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\compute{path = [0, 1, 2, 3]}\n"
            "\\step\n"
            "\\foreach{i}{${path}}\n"
            "  \\recolor{a.cell[${i}]}{state=path}\n"
            "\\endforeach\n"
        )
        ir = parser.parse(src)
        fe = ir.frames[0].commands[0]
        assert isinstance(fe, ForeachCommand)
        assert "${path}" in fe.iterable_raw

    def test_foreach_depth_resets_between_siblings(self, parser: SceneParser) -> None:
        """After a sibling foreach closes, depth counter resets so the next
        foreach at the same level also parses successfully."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..1}\n"
            "  \\recolor{a.cell[${i}]}{state=done}\n"
            "\\endforeach\n"
            "\\foreach{j}{0..1}\n"
            "  \\recolor{a.cell[${j}]}{state=idle}\n"
            "\\endforeach\n"
        )
        ir = parser.parse(src)
        assert len(ir.frames[0].commands) == 2
        assert all(isinstance(c, ForeachCommand) for c in ir.frames[0].commands)

    def test_foreach_with_highlight_body(self, parser: SceneParser) -> None:
        """\\highlight is a valid foreach body command."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..2}\n"
            "  \\highlight{a.cell[${i}]}\n"
            "\\endforeach\n"
        )
        ir = parser.parse(src)
        fe = ir.frames[0].commands[0]
        assert isinstance(fe, ForeachCommand)
        assert isinstance(fe.body[0], HighlightCommand)


@pytest.mark.unit
class TestForeachErrorPaths:
    """Error: invalid foreach constructs raise ValidationError with the
    expected error codes."""

    def test_unclosed_foreach_raises_e1172(self, parser: SceneParser) -> None:
        """EOF without \\endforeach raises E1172 (unclosed \\foreach)."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..3}\n"
            "  \\recolor{a.cell[${i}]}{state=current}\n"
        )
        with pytest.raises(ValidationError, match="E1172"):
            parser.parse(src)

    def test_invalid_binding_name_empty_raises_e1173(
        self, parser: SceneParser
    ) -> None:
        """Empty variable name in foreach raises E1173."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{}{0..3}\n"
            "  \\recolor{a.cell[0]}{state=current}\n"
            "\\endforeach\n"
        )
        with pytest.raises(ValidationError, match="E1173"):
            parser.parse(src)

    def test_recursion_depth_limit_raises_e1170(self, parser: SceneParser) -> None:
        """Four-level nesting (> MAX 3) raises E1170 at parse time."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{a}{0..1}\n"
            "  \\foreach{b}{0..1}\n"
            "    \\foreach{c}{0..1}\n"
            "      \\foreach{d}{0..1}\n"
            "        \\recolor{a.cell[${d}]}{state=done}\n"
            "      \\endforeach\n"
            "    \\endforeach\n"
            "  \\endforeach\n"
            "\\endforeach\n"
        )
        with pytest.raises(ValidationError, match="E1170"):
            parser.parse(src)

    def test_step_inside_foreach_body_raises_e1172(
        self, parser: SceneParser
    ) -> None:
        """\\step is not allowed inside a foreach body; raises E1172."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..3}\n"
            "  \\step\n"
            "\\endforeach\n"
        )
        with pytest.raises(ValidationError, match="E1172"):
            parser.parse(src)

    def test_substory_inside_foreach_body_raises_e1172(
        self, parser: SceneParser
    ) -> None:
        """\\substory is not allowed inside foreach body; raises E1172."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..3}\n"
            "  \\substory\n"
            "  \\step\n"
            "  \\endsubstory\n"
            "\\endforeach\n"
        )
        with pytest.raises(ValidationError, match="E1172"):
            parser.parse(src)

    def test_five_level_nested_foreach_raises_e1170(
        self, parser: SceneParser
    ) -> None:
        """Five-level foreach nesting is firmly rejected with E1170."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{a}{0..1}\n"
            "  \\foreach{b}{0..1}\n"
            "    \\foreach{c}{0..1}\n"
            "      \\foreach{d}{0..1}\n"
            "        \\foreach{e}{0..1}\n"
            "          \\recolor{a.cell[${e}]}{state=done}\n"
            "        \\endforeach\n"
            "      \\endforeach\n"
            "    \\endforeach\n"
            "  \\endforeach\n"
            "\\endforeach\n"
        )
        with pytest.raises(ValidationError, match="E1170"):
            parser.parse(src)
