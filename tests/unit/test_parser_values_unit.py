"""Unit tests for ``_parse_interp_ref``, ``_parse_list_value``, ``_parse_tuple_value``.

Wave F1b prerequisite for grammar.py mixin split (Wave F2–F6).

These three private methods handle the lowest-level value-parsing concerns.
They are exercised via ``SceneParser.parse()`` end-to-end with narrow inputs
that isolate each method's behaviour:

- ``_parse_interp_ref`` — invoked when a ``${...}`` INTERP token is consumed
- ``_parse_list_value``  — invoked when a ``[`` LBRACKET is consumed
- ``_parse_tuple_value`` — invoked when a ``(`` LPAREN is consumed

All three are reached through ``_parse_param_value``, which is called by
``_read_param_brace`` (for ``\\shape`` / ``\\apply`` / etc.) and by the
selector-interpolation path.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser, ApplyCommand, ShapeCommand
from scriba.animation.parser.ast import InterpolationRef
from scriba.core.errors import ValidationError


def _parse(source: str):
    return SceneParser().parse(source)


def _apply_cmds(ir):
    return [c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)]


# Reusable preludes
_ARRAY_PRELUDE = "\\shape{a}{Array}{size=5}\n\\step\n"
_STACK_PRELUDE = "\\shape{s}{Stack}{size=4}\n\\step\n"


# ===========================================================================
# _parse_interp_ref
# ===========================================================================


@pytest.mark.unit
class TestParseInterpRef:
    """``_parse_interp_ref`` — builds ``InterpolationRef`` from ``${...}`` tokens."""

    def test_simple_name_no_subscript(self) -> None:
        """``${pts}`` → InterpolationRef(name='pts', subscripts=())."""
        src = (
            "\\compute{pts = [1,2,3]}\n"
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\apply{a}{values=${pts}}\n"
        )
        ir = _parse(src)
        cmd = _apply_cmds(ir)[0]
        ref = cmd.params["values"]
        assert isinstance(ref, InterpolationRef)
        assert ref.name == "pts"
        assert ref.subscripts == ()

    def test_single_int_subscript(self) -> None:
        """``${arr[0]}`` → subscripts=(0,)."""
        src = (
            "\\compute{arr = [10, 20, 30]}\n"
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\apply{a}{head=${arr[0]}}\n"
        )
        ir = _parse(src)
        ref = _apply_cmds(ir)[0].params["head"]
        assert isinstance(ref, InterpolationRef)
        assert ref.name == "arr"
        assert ref.subscripts == (0,)

    def test_double_int_subscript(self) -> None:
        """``${m[1][2]}`` → subscripts=(1, 2)."""
        src = (
            "\\compute{m = [[0,0],[0,42]]}\n"
            "\\shape{a}{Array}{size=2}\n"
            "\\step\n"
            "\\apply{a}{val=${m[1][2]}}\n"
        )
        ir = _parse(src)
        ref = _apply_cmds(ir)[0].params["val"]
        assert isinstance(ref, InterpolationRef)
        assert ref.name == "m"
        assert ref.subscripts == (1, 2)

    def test_string_subscript(self) -> None:
        """``${d[key]}`` — non-numeric subscript stored as string."""
        src = (
            "\\compute{d = {\"key\": 99}}\n"
            "\\shape{a}{Array}{size=1}\n"
            "\\step\n"
            "\\apply{a}{val=${d[key]}}\n"
        )
        ir = _parse(src)
        ref = _apply_cmds(ir)[0].params["val"]
        assert isinstance(ref, InterpolationRef)
        assert ref.name == "d"
        assert ref.subscripts == ("key",)

    def test_interp_ref_in_shape_declaration(self) -> None:
        """Interp ref in ``\\shape`` param brace (not just ``\\apply``)."""
        src = (
            "\\compute{pts = [(0,0),(1,1)]}\n"
            "\\shape{g}{Plane2D}{xrange=[-5,5], yrange=[-5,5], points=${pts}}\n"
        )
        ir = _parse(src)
        ref = ir.shapes[0].params["points"]
        assert isinstance(ref, InterpolationRef)
        assert ref.name == "pts"
        assert ref.subscripts == ()

    def test_interp_ref_no_compute_emits_warning(self) -> None:
        """Reference to an unbound name emits a ``UserWarning`` (not an error)."""
        import warnings

        src = _ARRAY_PRELUDE + "\\apply{a}{x=${unbound_var}}\n"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _parse(src)
        user_warns = [x for x in w if issubclass(x.category, UserWarning)]
        assert any("unbound_var" in str(x.message) for x in user_warns)


# ===========================================================================
# _parse_list_value
# ===========================================================================


@pytest.mark.unit
class TestParseListValue:
    """``_parse_list_value`` — ``[value, ...]`` → Python list."""

    def test_list_of_ints(self) -> None:
        src = "\\shape{a}{Array}{values=[1, 2, 3]}\n"
        ir = _parse(src)
        assert ir.shapes[0].params["values"] == [1, 2, 3]

    def test_list_of_strings(self) -> None:
        src = "\\shape{a}{Array}{values=[\"x\", \"y\"]}\n"
        ir = _parse(src)
        assert ir.shapes[0].params["values"] == ["x", "y"]

    def test_list_of_floats(self) -> None:
        src = "\\shape{a}{Array}{values=[0.1, 0.2, 0.3]}\n"
        ir = _parse(src)
        vals = ir.shapes[0].params["values"]
        assert vals == pytest.approx([0.1, 0.2, 0.3])

    def test_list_of_mixed_types(self) -> None:
        """List items may have heterogeneous types."""
        src = "\\shape{a}{Array}{values=[1, \"two\", true]}\n"
        ir = _parse(src)
        assert ir.shapes[0].params["values"] == [1, "two", True]

    def test_empty_list(self) -> None:
        src = "\\shape{a}{Array}{values=[]}\n"
        ir = _parse(src)
        assert ir.shapes[0].params["values"] == []

    def test_single_element_list(self) -> None:
        src = "\\shape{a}{Array}{values=[42]}\n"
        ir = _parse(src)
        assert ir.shapes[0].params["values"] == [42]

    def test_list_as_apply_param(self) -> None:
        src = _STACK_PRELUDE + "\\apply{s}{push_all=[1, 2, 3]}\n"
        ir = _parse(src)
        cmd = _apply_cmds(ir)[0]
        assert cmd.params["push_all"] == [1, 2, 3]

    def test_list_of_booleans(self) -> None:
        src = "\\shape{a}{Array}{flags=[true, false, true]}\n"
        ir = _parse(src)
        assert ir.shapes[0].params["flags"] == [True, False, True]


# ===========================================================================
# _parse_tuple_value
# ===========================================================================


@pytest.mark.unit
class TestParseTupleValue:
    """``_parse_tuple_value`` — ``(value, ...)`` → Python list."""

    def test_tuple_of_ints(self) -> None:
        """``(lo, hi)`` stored as a Python list."""
        src = "\\shape{g}{Plane2D}{xrange=(-5, 5), yrange=(-5, 5)}\n"
        ir = _parse(src)
        assert ir.shapes[0].params["xrange"] == [-5, 5]

    def test_tuple_of_floats(self) -> None:
        src = "\\shape{g}{Plane2D}{xrange=(-1.5, 1.5), yrange=(-2.0, 2.0)}\n"
        ir = _parse(src)
        assert ir.shapes[0].params["xrange"] == pytest.approx([-1.5, 1.5])

    def test_tuple_of_strings(self) -> None:
        src = _ARRAY_PRELUDE + "\\apply{a}{labels=(\"a\", \"b\")}\n"
        ir = _parse(src)
        cmd = _apply_cmds(ir)[0]
        assert cmd.params["labels"] == ["a", "b"]

    def test_single_element_tuple(self) -> None:
        """A one-element tuple ``(7)`` is stored as ``[7]``."""
        src = _ARRAY_PRELUDE + "\\apply{a}{t=(7)}\n"
        ir = _parse(src)
        cmd = _apply_cmds(ir)[0]
        assert cmd.params["t"] == [7]

    def test_tuple_of_booleans(self) -> None:
        src = _ARRAY_PRELUDE + "\\apply{a}{flags=(true, false)}\n"
        ir = _parse(src)
        cmd = _apply_cmds(ir)[0]
        assert cmd.params["flags"] == [True, False]

    def test_tuple_as_shape_param(self) -> None:
        """Tuple syntax is accepted in shape declarations."""
        src = "\\shape{g}{Plane2D}{xrange=(0, 10), yrange=(0, 10)}\n"
        ir = _parse(src)
        shape = ir.shapes[0]
        assert shape.params["xrange"] == [0, 10]
        assert shape.params["yrange"] == [0, 10]

    def test_empty_tuple_is_empty_list(self) -> None:
        """``()`` parses as an empty list."""
        src = _ARRAY_PRELUDE + "\\apply{a}{empty=()}\n"
        ir = _parse(src)
        cmd = _apply_cmds(ir)[0]
        assert cmd.params["empty"] == []


# ===========================================================================
# Error paths spanning all three methods
# ===========================================================================


@pytest.mark.unit
class TestValueParseErrors:
    """Error paths for list, tuple, and interp-ref value parsing."""

    def test_invalid_token_as_param_value_raises_e1005(self) -> None:
        """A raw backslash command where a value is expected → E1005."""
        src = "\\shape{a}{Array}{size=\\invalid}\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1005"

    def test_unterminated_list_raises_e1001(self) -> None:
        """``[1, 2`` without closing ``]`` leaves the outer brace unterminated → E1001."""
        src = "\\shape{a}{Array}{values=[1, 2\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1001"

    def test_unterminated_param_brace_in_shape_raises_e1001(self) -> None:
        """Param brace opened but never closed → E1001."""
        src = "\\shape{a}{Array}{size=3\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1001"

    def test_invalid_token_inside_list_raises(self) -> None:
        """A backslash command inside a list literal raises an error."""
        src = "\\shape{a}{Array}{values=[1, \\cmd, 2]}\n"
        with pytest.raises((ValidationError, Exception)):
            _parse(src)

    def test_unknown_command_token_as_value_raises_e1005(self) -> None:
        """COMMAND token (not a valid value) → E1005."""
        src = _ARRAY_PRELUDE + "\\apply{a}{key=\\bad}\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1005"
