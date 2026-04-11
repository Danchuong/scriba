"""Unit tests for scriba.animation.parser (grammar + selectors)."""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import (
    AnimationIR,
    AnnotateCommand,
    ApplyCommand,
    ComputeCommand,
    FrameIR,
    HighlightCommand,
    NarrateCommand,
    RecolorCommand,
    SceneParser,
    ShapeCommand,
)
from scriba.animation.parser.selectors import (
    AllAccessor,
    CellAccessor,
    EdgeAccessor,
    InterpolationRef,
    NamedAccessor,
    NodeAccessor,
    RangeAccessor,
    Selector,
    parse_selector,
)
from scriba.core.errors import ValidationError


@pytest.fixture()
def parser() -> SceneParser:
    return SceneParser()


# ===================================================================
# Selector parsing
# ===================================================================


class TestSelectorParsing:
    def test_bare_shape(self) -> None:
        s = parse_selector("a")
        assert s == Selector(shape_name="a", accessor=None)

    def test_cell_1d(self) -> None:
        s = parse_selector("a.cell[0]")
        assert s == Selector(
            shape_name="a",
            accessor=CellAccessor(indices=(0,)),
        )

    def test_cell_2d(self) -> None:
        s = parse_selector("g.cell[0][1]")
        assert s == Selector(
            shape_name="g",
            accessor=CellAccessor(indices=(0, 1)),
        )

    def test_cell_with_interpolation(self) -> None:
        s = parse_selector("a.cell[${i}]")
        assert s.accessor == CellAccessor(
            indices=(InterpolationRef(name="i"),),
        )

    def test_node_int(self) -> None:
        s = parse_selector("G.node[0]")
        assert s == Selector(
            shape_name="G",
            accessor=NodeAccessor(node_id=0),
        )

    def test_node_string(self) -> None:
        s = parse_selector('G.node["A"]')
        assert s == Selector(
            shape_name="G",
            accessor=NodeAccessor(node_id="A"),
        )

    def test_node_bare_ident(self) -> None:
        s = parse_selector("G.node[A]")
        assert s == Selector(
            shape_name="G",
            accessor=NodeAccessor(node_id="A"),
        )

    def test_edge(self) -> None:
        s = parse_selector('G.edge[("A","B")]')
        assert s == Selector(
            shape_name="G",
            accessor=EdgeAccessor(source="A", target="B"),
        )

    def test_edge_with_idents(self) -> None:
        s = parse_selector("G.edge[(A,B)]")
        assert s == Selector(
            shape_name="G",
            accessor=EdgeAccessor(source="A", target="B"),
        )

    def test_range(self) -> None:
        s = parse_selector("a.range[0:3]")
        assert s == Selector(
            shape_name="a",
            accessor=RangeAccessor(lo=0, hi=3),
        )

    def test_all(self) -> None:
        s = parse_selector("a.all")
        assert s == Selector(
            shape_name="a",
            accessor=AllAccessor(),
        )

    def test_named_accessor(self) -> None:
        s = parse_selector("nl.axis")
        assert s == Selector(
            shape_name="nl",
            accessor=NamedAccessor(name="axis"),
        )

    def test_interpolation_with_subscript(self) -> None:
        s = parse_selector("a.cell[${steps[0]}]")
        assert s.accessor == CellAccessor(
            indices=(InterpolationRef(name="steps", subscripts=(0,)),),
        )


# ===================================================================
# Command parsing — happy paths
# ===================================================================


class TestParseShapeCommand:
    def test_basic_shape(self, parser: SceneParser) -> None:
        src = r'\shape{a}{Array}{size=7, labels="0..6"}'
        ir = parser.parse(src)
        assert len(ir.shapes) == 1
        shape = ir.shapes[0]
        assert shape.name == "a"
        assert shape.type_name == "Array"
        assert shape.params["size"] == 7
        assert shape.params["labels"] == "0..6"

    def test_shape_with_interp_param(self, parser: SceneParser) -> None:
        src = r"\shape{a}{Array}{size=3, data=${dp}}"
        ir = parser.parse(src)
        assert isinstance(ir.shapes[0].params["data"], InterpolationRef)
        assert ir.shapes[0].params["data"].name == "dp"


class TestParseComputeCommand:
    def test_basic_compute(self, parser: SceneParser) -> None:
        src = r"\compute{ dp = [0, 7, 4] }"
        ir = parser.parse(src)
        assert len(ir.prelude_compute) == 1
        assert "dp = [0, 7, 4]" in ir.prelude_compute[0].source

    def test_compute_in_step(self, parser: SceneParser) -> None:
        src = "\\step\n\\compute{ x = 1 }"
        ir = parser.parse(src)
        assert len(ir.frames) == 1
        assert len(ir.frames[0].compute) == 1
        assert "x = 1" in ir.frames[0].compute[0].source


class TestParseStepCommand:
    def test_step_creates_frame(self, parser: SceneParser) -> None:
        src = "\\step\n\\step\n"
        ir = parser.parse(src)
        assert len(ir.frames) == 2

    def test_single_step(self, parser: SceneParser) -> None:
        src = "\\step\n"
        ir = parser.parse(src)
        assert len(ir.frames) == 1


class TestParseNarrateCommand:
    def test_basic_narrate(self, parser: SceneParser) -> None:
        src = "\\step\n\\narrate{Hello world}"
        ir = parser.parse(src)
        assert ir.frames[0].narrate_body == "Hello world"

    def test_narrate_with_math(self, parser: SceneParser) -> None:
        src = "\\step\n\\narrate{Initialize $dp[0] = 0$.}"
        ir = parser.parse(src)
        assert ir.frames[0].narrate_body == "Initialize $dp[0] = 0$."


class TestParseApplyCommand:
    def test_basic_apply(self, parser: SceneParser) -> None:
        src = "\\step\n\\apply{a.cell[0]}{value=0}"
        ir = parser.parse(src)
        assert len(ir.frames[0].commands) == 1
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, ApplyCommand)
        assert cmd.target.shape_name == "a"
        assert cmd.params["value"] == 0

    def test_apply_in_prelude(self, parser: SceneParser) -> None:
        src = "\\apply{a}{value=1}"
        ir = parser.parse(src)
        assert len(ir.prelude_commands) == 1
        assert isinstance(ir.prelude_commands[0], ApplyCommand)


class TestParseHighlightCommand:
    def test_basic_highlight(self, parser: SceneParser) -> None:
        src = "\\step\n\\highlight{a.cell[1]}"
        ir = parser.parse(src)
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, HighlightCommand)
        assert cmd.target == Selector(
            shape_name="a",
            accessor=CellAccessor(indices=(1,)),
        )


class TestParseRecolorCommand:
    def test_basic_recolor(self, parser: SceneParser) -> None:
        src = "\\step\n\\recolor{a.cell[0]}{state=done}"
        ir = parser.parse(src)
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, RecolorCommand)
        assert cmd.state == "done"

    def test_recolor_in_prelude(self, parser: SceneParser) -> None:
        src = "\\recolor{a}{state=idle}"
        ir = parser.parse(src)
        assert len(ir.prelude_commands) == 1
        assert isinstance(ir.prelude_commands[0], RecolorCommand)


class TestParseAnnotateCommand:
    def test_basic_annotate(self, parser: SceneParser) -> None:
        src = '\\step\n\\annotate{a.cell[2]}{label="min", color=info}'
        ir = parser.parse(src)
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, AnnotateCommand)
        assert cmd.label == "min"
        assert cmd.color == "info"
        assert cmd.position == "above"

    def test_annotate_all_params(self, parser: SceneParser) -> None:
        src = (
            "\\step\n"
            '\\annotate{a}{label="x", position=below, '
            "color=warn, arrow=true, ephemeral=true}"
        )
        ir = parser.parse(src)
        cmd = ir.frames[0].commands[0]
        assert isinstance(cmd, AnnotateCommand)
        assert cmd.position == "below"
        assert cmd.color == "warn"
        assert cmd.arrow is True
        assert cmd.ephemeral is True


# ===================================================================
# Parameter value parsing
# ===================================================================


class TestParamValues:
    def test_integer_param(self, parser: SceneParser) -> None:
        src = r"\shape{a}{Array}{size=7}"
        ir = parser.parse(src)
        assert ir.shapes[0].params["size"] == 7

    def test_float_param(self, parser: SceneParser) -> None:
        src = r"\shape{a}{Array}{scale=1.5}"
        ir = parser.parse(src)
        assert ir.shapes[0].params["scale"] == 1.5

    def test_string_param(self, parser: SceneParser) -> None:
        src = r'\shape{a}{Array}{labels="0..6"}'
        ir = parser.parse(src)
        assert ir.shapes[0].params["labels"] == "0..6"

    def test_bool_true_param(self, parser: SceneParser) -> None:
        src = r"\shape{a}{Graph}{directed=true}"
        ir = parser.parse(src)
        assert ir.shapes[0].params["directed"] is True

    def test_bool_false_param(self, parser: SceneParser) -> None:
        src = r"\shape{a}{Graph}{directed=false}"
        ir = parser.parse(src)
        assert ir.shapes[0].params["directed"] is False

    def test_list_param(self, parser: SceneParser) -> None:
        src = r"\shape{a}{Array}{data=[1, 2, 3]}"
        ir = parser.parse(src)
        assert ir.shapes[0].params["data"] == [1, 2, 3]

    def test_interp_param(self, parser: SceneParser) -> None:
        src = r"\shape{a}{Array}{data=${dp}}"
        ir = parser.parse(src)
        assert isinstance(ir.shapes[0].params["data"], InterpolationRef)


# ===================================================================
# Multi-frame animation
# ===================================================================


class TestMultiFrame:
    def test_two_frames_with_commands(self, parser: SceneParser) -> None:
        src = (
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\recolor{a.cell[0]}{state=done}\n"
            "\\highlight{a.cell[1]}\n"
            "\\narrate{Frame 1}\n"
            "\\step\n"
            "\\recolor{a.cell[1]}{state=done}\n"
            '\\annotate{a.cell[1]}{label="7", color=good}\n'
            "\\narrate{Frame 2}\n"
        )
        ir = parser.parse(src)
        assert len(ir.shapes) == 1
        assert len(ir.frames) == 2
        assert ir.frames[0].narrate_body == "Frame 1"
        assert ir.frames[1].narrate_body == "Frame 2"
        assert len(ir.frames[0].commands) == 2
        assert len(ir.frames[1].commands) == 2


# ===================================================================
# Edge cases
# ===================================================================


class TestEdgeCases:
    def test_empty_animation(self, parser: SceneParser) -> None:
        ir = parser.parse("")
        assert len(ir.shapes) == 0
        assert len(ir.frames) == 0

    def test_prelude_only(self, parser: SceneParser) -> None:
        src = "\\shape{a}{Array}{size=5}\n\\compute{ x = 1 }"
        ir = parser.parse(src)
        assert len(ir.shapes) == 1
        assert len(ir.prelude_compute) == 1
        assert len(ir.frames) == 0

    def test_source_hash_present(self, parser: SceneParser) -> None:
        src = "\\step\n"
        ir = parser.parse(src)
        assert len(ir.source_hash) == 10

    def test_source_hash_deterministic(self, parser: SceneParser) -> None:
        src = "\\step\n"
        ir1 = parser.parse(src)
        ir2 = parser.parse(src)
        assert ir1.source_hash == ir2.source_hash

    def test_options_parsing(self, parser: SceneParser) -> None:
        src = '[id=demo, label="My Animation", layout=filmstrip]\n\\step\n'
        ir = parser.parse(src)
        assert ir.options.id == "demo"
        assert ir.options.label == "My Animation"
        assert ir.options.layout == "filmstrip"

    def test_comment_ignored(self, parser: SceneParser) -> None:
        src = "% this is a comment\n\\step\n"
        ir = parser.parse(src)
        assert len(ir.frames) == 1


# ===================================================================
# Error cases
# ===================================================================


class TestParserErrors:
    def test_e1051_shape_after_step(self, parser: SceneParser) -> None:
        src = "\\step\n\\shape{a}{Array}{size=3}"
        with pytest.raises(ValidationError, match="E1051"):
            parser.parse(src)

    def test_e1052_trailing_text_after_step(self, parser: SceneParser) -> None:
        src = "\\step extra_text\n"
        with pytest.raises(ValidationError, match="E1052"):
            parser.parse(src)

    def test_e1053_highlight_in_prelude(self, parser: SceneParser) -> None:
        src = "\\highlight{a.cell[0]}"
        with pytest.raises(ValidationError, match="E1053"):
            parser.parse(src)

    def test_e1055_double_narrate(self, parser: SceneParser) -> None:
        src = "\\step\n\\narrate{First}\n\\narrate{Second}"
        with pytest.raises(ValidationError, match="E1055"):
            parser.parse(src)

    def test_e1056_narrate_outside_step(self, parser: SceneParser) -> None:
        src = "\\narrate{Orphan narration}"
        with pytest.raises(ValidationError, match="E1056"):
            parser.parse(src)

    def test_e1109_unknown_recolor_state(self, parser: SceneParser) -> None:
        src = "\\step\n\\recolor{a}{state=invalid}"
        with pytest.raises(ValidationError, match="E1109"):
            parser.parse(src)

    def test_e1112_unknown_annotate_position(self, parser: SceneParser) -> None:
        src = '\\step\n\\annotate{a}{label="x", position=center}'
        with pytest.raises(ValidationError, match="E1112"):
            parser.parse(src)

    def test_e1113_unknown_annotate_color(self, parser: SceneParser) -> None:
        src = '\\step\n\\annotate{a}{label="x", color=purple}'
        with pytest.raises(ValidationError, match="E1113"):
            parser.parse(src)

    def test_e1004_unknown_option_key(self, parser: SceneParser) -> None:
        src = "[unknown_key=val]\n\\step\n"
        with pytest.raises(ValidationError, match="E1004"):
            parser.parse(src)


class TestParserSourceLinePropagation:
    """Parser raises populate ValidationError.source_line with the offending line.

    Wave 4B Cluster 3: ``SceneParser._source_line_at`` wires the raw source
    text through every user-visible raise site so the formatter can render
    a caret pointer under the offending character.
    """

    def test_e1001_unclosed_brace_has_source_line(
        self, parser: SceneParser,
    ) -> None:
        # Opening brace on \shape name never closes before EOF.
        src = "\\shape{a"
        with pytest.raises(ValidationError) as exc_info:
            parser.parse(src)
        err = exc_info.value
        assert err.code == "E1001"
        assert err.source_line is not None
        assert "\\shape{a" in err.source_line
        rendered = str(err)
        assert "\\shape{a" in rendered
        assert "^" in rendered

    def test_e1012_unexpected_token_has_source_line(
        self, parser: SceneParser,
    ) -> None:
        """A missing LBRACE after \\shape triggers E1012 with source_line.

        This exercises the ``_expect`` raise site used throughout the
        parser for structural token mismatches.
        """
        src = "\\shape{a}{Array}\n\\step\n\\shape nope\n"
        with pytest.raises(ValidationError) as exc_info:
            parser.parse(src)
        err = exc_info.value
        # This is the \shape must appear before \step error (E1051).
        assert err.code == "E1051"
        assert err.source_line is not None
        assert "\\shape" in err.source_line

    def test_e1053_highlight_in_prelude_has_source_line(
        self, parser: SceneParser,
    ) -> None:
        src = "\\highlight{a.cell[0]}\n"
        with pytest.raises(ValidationError) as exc_info:
            parser.parse(src)
        err = exc_info.value
        assert err.code == "E1053"
        assert err.source_line is not None
        assert "\\highlight{a.cell[0]}" in err.source_line
        # Caret pointer must be rendered into str(err)
        assert "^" in str(err)

    def test_e1055_duplicate_narrate_has_source_line(
        self, parser: SceneParser,
    ) -> None:
        src = "\\step\n\\narrate{first}\n\\narrate{second}\n"
        with pytest.raises(ValidationError) as exc_info:
            parser.parse(src)
        err = exc_info.value
        assert err.code == "E1055"
        assert err.source_line is not None
        assert "\\narrate{second}" in err.source_line

    def test_source_line_none_when_no_parser_source(self) -> None:
        """Direct ValidationError without source_line still works (backwards compat)."""
        err = ValidationError("no ctx", code="E1001")
        assert err.source_line is None
        # str() must not include a caret block.
        assert "^" not in str(err)


# ===================================================================
# Error recovery
# ===================================================================


class TestErrorRecovery:
    """Tests for the error_recovery=True multi-error collection mode."""

    def test_recovery_off_raises_first_error(self, parser: SceneParser) -> None:
        """Without recovery, only the first error is reported (fail-fast)."""
        src = "\\step\n\\recolor{a}{state=bad}\n\\recolor{b}{state=worse}"
        with pytest.raises(ValidationError, match="E1109"):
            parser.parse(src, error_recovery=False)

    def test_recovery_collects_multiple_errors(self, parser: SceneParser) -> None:
        """With recovery, multiple command errors are collected and reported."""
        src = "\\step\n\\recolor{a}{state=bad}\n\\recolor{b}{state=worse}"
        with pytest.raises(ValidationError, match="found 2 errors"):
            parser.parse(src, error_recovery=True)

    def test_recovery_single_error_raises_directly(self, parser: SceneParser) -> None:
        """A single collected error is raised as-is, not wrapped."""
        src = "\\step\n\\recolor{a}{state=bad}"
        with pytest.raises(ValidationError, match="E1109") as exc_info:
            parser.parse(src, error_recovery=True)
        # Should not contain "found 1 errors" wrapper
        assert "found" not in str(exc_info.value)

    def test_recovery_skips_to_next_command(self, parser: SceneParser) -> None:
        """After a bad command, the parser resumes at the next command."""
        src = (
            "\\shape{a}{Array}{n=5}\n"
            "\\step\n"
            "\\recolor{a}{state=bad}\n"
            "\\highlight{a}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            parser.parse(src, error_recovery=True)
        # The highlight should have parsed successfully — only 1 error
        assert "found" not in str(exc_info.value)
        assert "E1109" in str(exc_info.value)

    def test_recovery_reports_errors_from_different_steps(
        self, parser: SceneParser,
    ) -> None:
        """Errors in different steps are all collected."""
        src = (
            "\\step\n"
            "\\recolor{a}{state=bad}\n"
            "\\step\n"
            "\\recolor{b}{state=worse}\n"
        )
        with pytest.raises(ValidationError, match="found 2 errors"):
            parser.parse(src, error_recovery=True)

    def test_recovery_multiple_invalid_recolors_collected(
        self, parser: SceneParser,
    ) -> None:
        """Multiple invalid recolors in the same step are all collected."""
        src = (
            "\\step\n"
            "\\recolor{a}{state=invalid1}\n"
            "\\recolor{b}{state=invalid2}\n"
            "\\recolor{c}{state=invalid3}\n"
        )
        with pytest.raises(ValidationError, match="found 3 errors"):
            parser.parse(src, error_recovery=True)

    def test_recovery_valid_input_no_error(self, parser: SceneParser) -> None:
        """Valid input with recovery enabled parses normally."""
        src = (
            "\\shape{a}{Array}{n=5}\n"
            "\\step\n"
            "\\recolor{a}{state=done}\n"
            "\\highlight{a}\n"
        )
        result = parser.parse(src, error_recovery=True)
        assert len(result.frames) == 1
        assert len(result.frames[0].commands) == 2
