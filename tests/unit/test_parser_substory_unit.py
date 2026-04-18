"""Unit tests for _parse_substory and _check_substory_trailing.

Exercises substory parsing logic through SceneParser.parse() end-to-end
with narrow inputs covering positive paths and error conditions.

Wave F1a prerequisite for grammar.py mixin split (Wave F2-F6).
"""

from __future__ import annotations

import warnings

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.parser.ast import (
    SubstoryBlock,
    HighlightCommand,
    RecolorCommand,
    ApplyCommand,
    ComputeCommand,
    ShapeCommand,
)
from scriba.animation.errors import EmptySubstoryWarning
from scriba.core.errors import ValidationError


@pytest.fixture()
def parser() -> SceneParser:
    return SceneParser()


@pytest.mark.unit
class TestSubstoryPositivePaths:
    """Positive: valid substory constructs parse without error."""

    def test_empty_substory_warns_but_parses(self, parser: SceneParser) -> None:
        """A substory with zero \\step blocks produces an EmptySubstoryWarning
        but still returns a SubstoryBlock with no frames."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\endsubstory\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ir = parser.parse(src)

        substory_warnings = [
            w for w in caught if issubclass(w.category, EmptySubstoryWarning)
        ]
        assert substory_warnings, "expected EmptySubstoryWarning for zero-step substory"
        assert len(ir.frames) == 1
        assert len(ir.frames[0].substories) == 1
        sub = ir.frames[0].substories[0]
        assert isinstance(sub, SubstoryBlock)
        assert sub.frames == ()

    def test_substory_with_title_option(self, parser: SceneParser) -> None:
        """substory[title=...] sets the title attribute on SubstoryBlock."""
        src = (
            "\\shape{a}{Array}{size=2}\n"
            "\\step\n"
            "\\substory[title=\"My detail\"]\n"
            "\\step\n"
            "\\highlight{a.cell[0]}\n"
            "\\endsubstory\n"
        )
        ir = parser.parse(src)
        sub = ir.frames[0].substories[0]
        assert isinstance(sub, SubstoryBlock)
        assert sub.title == "My detail"
        assert len(sub.frames) == 1

    def test_substory_with_id_option(self, parser: SceneParser) -> None:
        """substory[id=...] sets substory_id on SubstoryBlock."""
        src = (
            "\\shape{a}{Array}{size=2}\n"
            "\\step\n"
            "\\substory[id=\"detail-1\"]\n"
            "\\step\n"
            "\\recolor{a.cell[0]}{state=done}\n"
            "\\endsubstory\n"
        )
        ir = parser.parse(src)
        sub = ir.frames[0].substories[0]
        assert sub.substory_id == "detail-1"

    def test_substory_with_primitives_shape_and_compute(
        self, parser: SceneParser
    ) -> None:
        """Substory can have its own \\shape and \\compute in the prelude."""
        src = (
            "\\step\n"
            "\\substory[title=\"Sub\"]\n"
            "\\shape{sub}{Array}{size=2, data=[3,1]}\n"
            "\\compute{x = 42}\n"
            "\\step\n"
            "\\highlight{sub.cell[0]}\n"
            "\\endsubstory\n"
        )
        ir = parser.parse(src)
        sub = ir.frames[0].substories[0]
        assert len(sub.shapes) == 1
        assert isinstance(sub.shapes[0], ShapeCommand)
        assert len(sub.compute) == 1
        assert isinstance(sub.compute[0], ComputeCommand)
        assert len(sub.frames) == 1

    def test_substory_with_multiple_steps(self, parser: SceneParser) -> None:
        """Substory accumulates multiple steps into frames."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\substory[title=\"Detail\"]\n"
            "\\step\n"
            "\\recolor{a.cell[0]}{state=current}\n"
            "\\step\n"
            "\\recolor{a.cell[0]}{state=done}\n"
            "\\endsubstory\n"
        )
        ir = parser.parse(src)
        sub = ir.frames[0].substories[0]
        assert len(sub.frames) == 2
        assert isinstance(sub.frames[0].commands[0], RecolorCommand)
        assert isinstance(sub.frames[1].commands[0], RecolorCommand)

    def test_substory_auto_id_assigned_when_not_specified(
        self, parser: SceneParser
    ) -> None:
        """When no [id=...] option is given, substory_id defaults to 'substory1'."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        ir = parser.parse(src)
        sub = ir.frames[0].substories[0]
        assert sub.substory_id == "substory1"

    def test_substory_with_apply_inside_step(self, parser: SceneParser) -> None:
        """\\apply is valid inside a substory step."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=42}\n"
            "\\endsubstory\n"
        )
        ir = parser.parse(src)
        sub = ir.frames[0].substories[0]
        assert len(sub.frames) == 1
        assert isinstance(sub.frames[0].commands[0], ApplyCommand)


@pytest.mark.unit
class TestSubstoryErrorPaths:
    """Error: invalid substory constructs raise ValidationError or warnings."""

    def test_unclosed_substory_raises_e1361(self, parser: SceneParser) -> None:
        """EOF without \\endsubstory raises E1361."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\recolor{a.cell[0]}{state=done}\n"
        )
        with pytest.raises(ValidationError, match="E1361"):
            parser.parse(src)

    def test_substory_recursion_depth_limit_raises_e1360(
        self, parser: SceneParser
    ) -> None:
        """Nesting substories beyond MAX depth (3) raises E1360."""
        # Build 4-level nesting: substory inside substory inside substory inside substory
        src = (
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1360"):
            parser.parse(src)

    def test_trailing_tokens_after_substory_raises_e1368(
        self, parser: SceneParser
    ) -> None:
        """Text on the same line as \\substory raises E1368."""
        src = (
            "\\step\n"
            "\\substory extra_text\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1368"):
            parser.parse(src)

    def test_trailing_tokens_after_endsubstory_raises_e1368(
        self, parser: SceneParser
    ) -> None:
        """Text on the same line as \\endsubstory raises E1368."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\endsubstory extra\n"
        )
        with pytest.raises(ValidationError, match="E1368"):
            parser.parse(src)

    def test_highlight_in_substory_prelude_raises_e1057(
        self, parser: SceneParser
    ) -> None:
        """\\highlight before first \\step inside substory raises E1057."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\substory\n"
            "\\highlight{a.cell[0]}\n"
            "\\step\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1057"):
            parser.parse(src)

    def test_substory_in_prelude_before_step_raises_e1362(
        self, parser: SceneParser
    ) -> None:
        """\\substory nested inside a substory prelude (before \\step) raises E1362."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\substory\n"
            "\\step\n"
            "\\endsubstory\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1362"):
            parser.parse(src)

    def test_endforeach_inside_substory_raises_e1172(
        self, parser: SceneParser
    ) -> None:
        """Orphan \\endforeach inside substory (no matching \\foreach) raises E1172."""
        src = (
            "\\step\n"
            "\\substory\n"
            "\\step\n"
            "\\endforeach\n"
            "\\endsubstory\n"
        )
        with pytest.raises(ValidationError, match="E1172"):
            parser.parse(src)
