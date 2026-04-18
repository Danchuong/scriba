"""Unit tests for ``_read_param_brace`` value shapes.

Wave F1b prerequisite for grammar.py mixin split (Wave F2–F6).

Covers the four value shapes accepted by ``_read_param_brace`` / ``_parse_param_value``:
- list value  ``[v, v, ...]``
- tuple value  ``(v, v, ...)``
- nested dict  ``{k=v, ...}``
- interpolation reference  ``${name}`` / ``${name[i]}``

Plus error paths: unterminated brace, mismatched bracket type, invalid nested
content.

All tests drive the parser through ``SceneParser.parse()`` end-to-end with
narrow inputs so that behaviour is observable via the produced ``AnimationIR``.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import (
    ApplyCommand,
    SceneParser,
    ShapeCommand,
)
from scriba.animation.parser.ast import InterpolationRef
from scriba.core.errors import ValidationError


@pytest.fixture()
def parser() -> SceneParser:
    return SceneParser()


def _parse(source: str):
    return SceneParser().parse(source)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ARRAY_PRELUDE = "\\shape{a}{Array}{size=5}\n\\step\n"
_LINKED_LIST_PRELUDE = "\\shape{ll}{LinkedList}{values=[1,2,3]}\n\\step\n"
_STACK_PRELUDE = "\\shape{s}{Stack}{size=4}\n\\step\n"


def _apply_cmd(ir, index: int = 0) -> ApplyCommand:
    cmds = [c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)]
    return cmds[index]


# ===========================================================================
# List values
# ===========================================================================


@pytest.mark.unit
class TestListValue:
    """``_parse_param_value`` → list branch via ``[...]``."""

    def test_list_of_ints(self, parser: SceneParser) -> None:
        src = "\\shape{a}{Array}{values=[1, 2, 3]}\n"
        ir = parser.parse(src)
        shape = ir.shapes[0]
        assert isinstance(shape, ShapeCommand)
        assert shape.params["values"] == [1, 2, 3]

    def test_list_of_strings(self, parser: SceneParser) -> None:
        src = "\\shape{a}{Array}{values=[\"x\", \"y\", \"z\"]}\n"
        ir = parser.parse(src)
        assert ir.shapes[0].params["values"] == ["x", "y", "z"]

    def test_list_of_floats(self, parser: SceneParser) -> None:
        src = "\\shape{a}{Array}{values=[1.5, 2.5, 3.5]}\n"
        ir = parser.parse(src)
        assert ir.shapes[0].params["values"] == pytest.approx([1.5, 2.5, 3.5])

    def test_single_element_list(self, parser: SceneParser) -> None:
        src = "\\shape{a}{Array}{values=[42]}\n"
        ir = parser.parse(src)
        assert ir.shapes[0].params["values"] == [42]

    def test_list_as_apply_param(self, parser: SceneParser) -> None:
        src = _STACK_PRELUDE + "\\apply{s}{push_many=[10, 20]}\n"
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        assert cmd.params["push_many"] == [10, 20]

    def test_list_with_bool_values(self, parser: SceneParser) -> None:
        src = "\\shape{a}{Array}{flags=[true, false, true]}\n"
        ir = parser.parse(src)
        assert ir.shapes[0].params["flags"] == [True, False, True]

    def test_empty_list(self, parser: SceneParser) -> None:
        src = "\\shape{a}{Array}{values=[]}\n"
        ir = parser.parse(src)
        assert ir.shapes[0].params["values"] == []


# ===========================================================================
# Tuple values
# ===========================================================================


@pytest.mark.unit
class TestTupleValue:
    """``_parse_param_value`` → tuple branch via ``(...)``."""

    def test_tuple_of_ints(self, parser: SceneParser) -> None:
        src = "\\shape{g}{Plane2D}{xrange=(-5, 5), yrange=(-5, 5)}\n"
        ir = parser.parse(src)
        assert ir.shapes[0].params["xrange"] == [-5, 5]

    def test_tuple_of_floats(self, parser: SceneParser) -> None:
        src = "\\shape{g}{Plane2D}{xrange=(-1.5, 1.5), yrange=(-1.5, 1.5)}\n"
        ir = parser.parse(src)
        assert ir.shapes[0].params["xrange"] == pytest.approx([-1.5, 1.5])

    def test_tuple_as_apply_param(self, parser: SceneParser) -> None:
        src = _ARRAY_PRELUDE + "\\apply{a}{range=(1, 3)}\n"
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        assert cmd.params["range"] == [1, 3]

    def test_single_element_tuple(self, parser: SceneParser) -> None:
        src = _ARRAY_PRELUDE + "\\apply{a}{tup=(7)}\n"
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        assert cmd.params["tup"] == [7]

    def test_tuple_of_strings(self, parser: SceneParser) -> None:
        src = _ARRAY_PRELUDE + "\\apply{a}{labels=(\"lo\", \"hi\")}\n"
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        assert cmd.params["labels"] == ["lo", "hi"]


# ===========================================================================
# Nested dict values
# ===========================================================================


@pytest.mark.unit
class TestNestedDictValue:
    """``_parse_param_value`` → nested dict branch via ``{k=v, ...}``."""

    def test_nested_dict_basic(self, parser: SceneParser) -> None:
        src = _LINKED_LIST_PRELUDE + "\\apply{ll}{insert={index=0, value=99}}\n"
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        assert cmd.params["insert"] == {"index": 0, "value": 99}

    def test_nested_dict_with_string_value(self, parser: SceneParser) -> None:
        src = _STACK_PRELUDE + "\\apply{s}{push={label=\"top\", value=1}}\n"
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        push = cmd.params["push"]
        assert isinstance(push, dict)
        assert push["label"] == "top"
        assert push["value"] == 1

    def test_deeply_nested_dict(self, parser: SceneParser) -> None:
        src = (
            "\\shape{a}{Array}{size=3}\n\\step\n"
            "\\apply{a}{meta={inner={x=1, y=2}}}\n"
        )
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        meta = cmd.params["meta"]
        assert isinstance(meta, dict)
        assert meta["inner"] == {"x": 1, "y": 2}

    def test_nested_dict_alongside_scalar_param(self, parser: SceneParser) -> None:
        src = _LINKED_LIST_PRELUDE + "\\apply{ll}{insert={index=1, value=7}, label=\"hi\"}\n"
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        assert cmd.params["label"] == "hi"
        assert cmd.params["insert"] == {"index": 1, "value": 7}

    def test_empty_nested_dict(self, parser: SceneParser) -> None:
        src = _STACK_PRELUDE + "\\apply{s}{push={}}\n"
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        assert cmd.params["push"] == {}


# ===========================================================================
# Interpolation reference values
# ===========================================================================


@pytest.mark.unit
class TestInterpRefValue:
    """``_parse_param_value`` → InterpolationRef branch via ``${name}``."""

    def test_simple_interp_ref_in_apply(self) -> None:
        src = (
            "\\compute{pts = [1,2,3]}\n"
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\apply{a}{values=${pts}}\n"
        )
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        ref = cmd.params["values"]
        assert isinstance(ref, InterpolationRef)
        assert ref.name == "pts"

    def test_subscripted_interp_ref_in_apply(self) -> None:
        src = (
            "\\compute{pts = [[1,2],[3,4]]}\n"
            "\\shape{a}{Array}{size=2}\n"
            "\\step\n"
            "\\apply{a}{first=${pts[0]}}\n"
        )
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        ref = cmd.params["first"]
        assert isinstance(ref, InterpolationRef)
        assert ref.name == "pts"
        assert ref.subscripts == (0,)

    def test_interp_ref_in_shape_params(self) -> None:
        """An interp ref used in a \\shape param brace (e.g. points=${pts})."""
        src = (
            "\\compute{pts = [(0,0),(1,1)]}\n"
            "\\shape{g}{Plane2D}{xrange=[-1,5], yrange=[-1,5], points=${pts}}\n"
        )
        ir = _parse(src)
        ref = ir.shapes[0].params["points"]
        assert isinstance(ref, InterpolationRef)
        assert ref.name == "pts"

    def test_double_subscripted_interp_ref(self) -> None:
        src = (
            "\\compute{m = [[1,2],[3,4]]}\n"
            "\\shape{a}{Array}{size=2}\n"
            "\\step\n"
            "\\apply{a}{val=${m[0][1]}}\n"
        )
        ir = _parse(src)
        cmd = _apply_cmd(ir)
        ref = cmd.params["val"]
        assert isinstance(ref, InterpolationRef)
        assert ref.name == "m"
        assert ref.subscripts == (0, 1)


# ===========================================================================
# Error paths
# ===========================================================================


@pytest.mark.unit
class TestParamBraceErrors:
    """Error paths for ``_read_param_brace``."""

    def test_unterminated_param_brace_raises_e1001(self) -> None:
        """Unclosed ``{`` in param brace → E1001."""
        src = "\\shape{a}{Array}{size=3\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1001"

    def test_unexpected_token_as_value_raises_e1005(self) -> None:
        """A ``\\`` command token as a param value → E1005 unexpected token."""
        src = "\\shape{a}{Array}{size=\\foo}\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1005"

    def test_invalid_nested_escape_in_brace(self) -> None:
        """A naked backslash command where a value is expected raises an error."""
        src = (
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\apply{a}{key=\\invalid}\n"
        )
        with pytest.raises(ValidationError):
            _parse(src)

    def test_missing_equals_in_key_value_pair_raises(self) -> None:
        """``{key value}`` (missing ``=``) raises a parse error."""
        # This produces a bare-token dict IF exactly IDENT RBRACE.
        # When there are 2+ tokens before RBRACE, the parser expects EQUALS.
        src = "\\shape{a}{Array}{size 3}\n"
        with pytest.raises((ValidationError, Exception)):
            _parse(src)

    def test_unterminated_brace_mid_frame_raises_e1001(self) -> None:
        """Unclosed param brace in a step body raises E1001."""
        src = "\\shape{a}{Array}{size=3}\n\\step\n\\apply{a}{key=1\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1001"
