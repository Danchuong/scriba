"""Shape validation for ``_ValuesMixin._parse_interp_ref`` (judgezone-11 sibling).

Same root cause as the renderer shield (judgezone-11): ``_parse_interp_ref``
built an ``InterpolationRef`` from ``${...}`` content without validating that
the content is actually identifier-shaped. A structured ``value=${...}``
containing math-shaped garbage (e.g. ``value=${5 \\choose 3}``) silently
became ``InterpolationRef(name="5 \\choose 3")``, which is never a real
\\compute binding, so ``scene.py``'s ``.get(name, name)`` fallback quietly
returns the literal garbage string as the resolved value instead of failing.

The fix validates the name (and any non-int subscript) with
``str.isidentifier()`` -- the same shape gate ``_grammar_compute.py``'s
``_check_interpolation_binding`` already uses -- and raises a fail-loud
``AnimationError`` (E1161) instead of building an unusable reference.

No dot/``.attr`` tail support here (unlike the renderer's shield): nothing
downstream resolves a dotted ``InterpolationRef.name``, and no real usage
in examples/tests/docs relies on one, so only ``name`` and ``name[sub]*``
are accepted.
"""

from __future__ import annotations

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.parser.ast import InterpolationRef
from scriba.animation.parser.grammar import SceneParser


@pytest.fixture()
def parser() -> SceneParser:
    return SceneParser()


# -----------------------------------------------------------------------------
# Direct unit tests: _parse_interp_ref is a pure function of its `content`
# string (no tokenizer/position state), so it's exercised directly.
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestParseInterpRefValidShapes:
    def test_bare_identifier(self, parser: SceneParser) -> None:
        ref = parser._parse_interp_ref("total")
        assert ref == InterpolationRef(name="total")

    def test_identifier_with_int_subscript(self, parser: SceneParser) -> None:
        ref = parser._parse_interp_ref("arr[2]")
        assert ref.name == "arr"
        assert ref.subscripts == (2,)

    def test_identifier_with_name_subscript(self, parser: SceneParser) -> None:
        ref = parser._parse_interp_ref("arr[i]")
        assert ref.name == "arr"
        assert ref.subscripts == ("i",)

    def test_identifier_with_multiple_subscripts(self, parser: SceneParser) -> None:
        ref = parser._parse_interp_ref("grid[i][2]")
        assert ref.name == "grid"
        assert ref.subscripts == ("i", 2)

    def test_underscore_and_digit_identifier(self, parser: SceneParser) -> None:
        ref = parser._parse_interp_ref("a_1")
        assert ref == InterpolationRef(name="a_1")

    def test_unicode_identifier(self, parser: SceneParser) -> None:
        """Combining-mark identifiers (e.g. Thai) are valid names too."""
        ref = parser._parse_interp_ref("ค่า")
        assert ref == InterpolationRef(name="ค่า")


@pytest.mark.unit
class TestParseInterpRefRejectsMathShape:
    def test_choose_expression_raises_e1161(self, parser: SceneParser) -> None:
        with pytest.raises(AnimationError) as exc_info:
            parser._parse_interp_ref("5 \\choose 3")
        assert exc_info.value.code == "E1161"

    def test_backslash_command_raises_e1161(self, parser: SceneParser) -> None:
        with pytest.raises(AnimationError) as exc_info:
            parser._parse_interp_ref("\\text{x}")
        assert exc_info.value.code == "E1161"

    def test_empty_content_raises_e1161(self, parser: SceneParser) -> None:
        with pytest.raises(AnimationError) as exc_info:
            parser._parse_interp_ref("")
        assert exc_info.value.code == "E1161"

    def test_arithmetic_subscript_raises_e1161(self, parser: SceneParser) -> None:
        """Arithmetic like ``i+1`` is not evaluated -- matches the existing
        E1159 hint for the same trap at the selector-index position."""
        with pytest.raises(AnimationError) as exc_info:
            parser._parse_interp_ref("arr[i+1]")
        assert exc_info.value.code == "E1161"

    def test_whitespace_name_raises_e1161(self, parser: SceneParser) -> None:
        with pytest.raises(AnimationError) as exc_info:
            parser._parse_interp_ref("5 choose 3")
        assert exc_info.value.code == "E1161"


# -----------------------------------------------------------------------------
# End-to-end: the real judgezone-11 sibling repro via SceneParser().parse(),
# mirroring the harness in test_parser_interpolation.py.
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestParseInterpRefEndToEnd:
    def test_valid_compute_binding_value_still_parses(self, parser: SceneParser) -> None:
        """Regression guard: a legitimate value=${name} keeps working."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\compute{dp = [0, 1, 2, 3]}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=${dp}}\n"
        )
        ir = parser.parse(src)
        assert ir is not None

    def test_math_shaped_apply_value_raises_e1161(self, parser: SceneParser) -> None:
        """The sibling repro: value=${5 \\choose 3} must fail loudly, not
        silently resolve to the literal garbage string at runtime."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=${5 \\choose 3}}\n"
        )
        with pytest.raises(AnimationError) as exc_info:
            parser.parse(src)
        assert exc_info.value.code == "E1161"
