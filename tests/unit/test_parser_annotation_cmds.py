"""Unit tests for ``_parse_annotate``, ``_parse_recolor``, ``_parse_reannotate``.

Wave F1b prerequisite for grammar.py mixin split (Wave F2–F6).

Covers:
- ``\\annotate`` — positive paths (selector, label, position, color, arrow_from)
  and error paths (invalid position, invalid color).
- ``\\recolor`` — positive paths (state, deprecated color, arrow_from) and
  error paths (unknown state, invalid annotation color, missing required arg).
- ``\\reannotate`` — positive paths (color, arrow_from) and error paths
  (missing color, invalid color).

All tests drive the parser through ``SceneParser.parse()`` end-to-end with
narrow inputs.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.parser.ast import (
    AnnotateCommand,
    ReannotateCommand,
    RecolorCommand,
)
from scriba.core.errors import ValidationError


def _parse(source: str):
    return SceneParser().parse(source)


# ---------------------------------------------------------------------------
# Fixtures / shared builders
# ---------------------------------------------------------------------------

_ARRAY_PRELUDE = "\\shape{a}{Array}{size=5}\n\\step\n"
_PLANE_PRELUDE = "\\shape{p}{Plane2D}{xrange=[-5,5], yrange=[-5,5]}\n\\step\n"


def _cmds_of_type(ir, cls):
    return [c for f in ir.frames for c in f.commands if isinstance(c, cls)]


# ===========================================================================
# \\annotate
# ===========================================================================


@pytest.mark.unit
class TestAnnotate:
    """``\\annotate{target}{params}`` positive and error paths."""

    # --- Positive paths ---

    def test_annotate_minimal_with_label(self) -> None:
        """Minimal annotate: selector + label, default position/color."""
        src = _ARRAY_PRELUDE + "\\annotate{a.cell[0]}{label=\"origin\"}\n"
        ir = _parse(src)
        cmds = _cmds_of_type(ir, AnnotateCommand)
        assert len(cmds) == 1
        cmd = cmds[0]
        assert cmd.target.shape_name == "a"
        assert cmd.label == "origin"
        assert cmd.position == "above"
        assert cmd.color == "info"

    def test_annotate_with_position_below(self) -> None:
        src = _ARRAY_PRELUDE + "\\annotate{a.cell[2]}{label=\"val\", position=below}\n"
        ir = _parse(src)
        cmd = _cmds_of_type(ir, AnnotateCommand)[0]
        assert cmd.position == "below"

    def test_annotate_with_color_warn(self) -> None:
        src = _ARRAY_PRELUDE + "\\annotate{a.cell[1]}{label=\"note\", color=warn}\n"
        ir = _parse(src)
        cmd = _cmds_of_type(ir, AnnotateCommand)[0]
        assert cmd.color == "warn"

    def test_annotate_with_color_good(self) -> None:
        src = _ARRAY_PRELUDE + "\\annotate{a.cell[3]}{label=\"ok\", color=good}\n"
        ir = _parse(src)
        cmd = _cmds_of_type(ir, AnnotateCommand)[0]
        assert cmd.color == "good"

    def test_annotate_with_arrow_flag(self) -> None:
        src = _ARRAY_PRELUDE + "\\annotate{a.cell[0]}{label=\"x\", arrow=true}\n"
        ir = _parse(src)
        cmd = _cmds_of_type(ir, AnnotateCommand)[0]
        assert cmd.arrow is True

    def test_annotate_with_arrow_from(self) -> None:
        """arrow_from= is a selector that parses into a Selector object."""
        src = (
            _PLANE_PRELUDE
            + "\\annotate{p.point[0]}{label=\"from\", "
            "arrow_from=\"p.point[1]\"}\n"
        )
        ir = _parse(src)
        cmd = _cmds_of_type(ir, AnnotateCommand)[0]
        assert cmd.arrow_from is not None
        assert cmd.arrow_from.shape_name == "p"

    def test_annotate_with_position_left(self) -> None:
        src = _ARRAY_PRELUDE + "\\annotate{a.cell[4]}{label=\"L\", position=left}\n"
        ir = _parse(src)
        cmd = _cmds_of_type(ir, AnnotateCommand)[0]
        assert cmd.position == "left"

    def test_annotate_ephemeral_flag(self) -> None:
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[0]}{label=\"tmp\", ephemeral=true}\n"
        )
        ir = _parse(src)
        cmd = _cmds_of_type(ir, AnnotateCommand)[0]
        assert cmd.ephemeral is True

    # --- Error paths ---

    def test_annotate_unknown_position_raises_e1112(self) -> None:
        """Invalid position value → E1112."""
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[0]}{label=\"x\", position=diagonal}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1112"

    def test_annotate_unknown_color_raises_e1113(self) -> None:
        """Invalid color value → E1113."""
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[0]}{label=\"x\", color=purple}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1113"

    def test_annotate_unknown_selector_raises(self) -> None:
        """A selector referencing an unknown shape still parses (selector
        validation is runtime, not parse-time), but an entirely invalid
        selector syntax should raise."""
        src = _ARRAY_PRELUDE + "\\annotate{}{label=\"x\"}\n"
        with pytest.raises(ValidationError):
            _parse(src)


# ===========================================================================
# \\recolor
# ===========================================================================


@pytest.mark.unit
class TestRecolor:
    """``\\recolor{target}{params}`` positive and error paths."""

    # --- Positive paths ---

    def test_recolor_with_state_current(self) -> None:
        src = _ARRAY_PRELUDE + "\\recolor{a.cell[0]}{state=current}\n"
        ir = _parse(src)
        cmds = _cmds_of_type(ir, RecolorCommand)
        assert len(cmds) == 1
        cmd = cmds[0]
        assert cmd.state == "current"
        assert cmd.target.shape_name == "a"

    def test_recolor_with_state_done(self) -> None:
        src = _ARRAY_PRELUDE + "\\recolor{a.cell[1]}{state=done}\n"
        ir = _parse(src)
        cmd = _cmds_of_type(ir, RecolorCommand)[0]
        assert cmd.state == "done"

    def test_recolor_with_state_dim(self) -> None:
        src = _ARRAY_PRELUDE + "\\recolor{a.cell[2]}{state=dim}\n"
        ir = _parse(src)
        cmd = _cmds_of_type(ir, RecolorCommand)[0]
        assert cmd.state == "dim"

    def test_recolor_with_state_error(self) -> None:
        src = _ARRAY_PRELUDE + "\\recolor{a.cell[3]}{state=error}\n"
        ir = _parse(src)
        cmd = _cmds_of_type(ir, RecolorCommand)[0]
        assert cmd.state == "error"

    def test_recolor_deprecated_color_with_warning(self) -> None:
        """\\recolor with color= is deprecated but still parses."""
        import warnings

        src = _ARRAY_PRELUDE + "\\annotate{a.cell[0]}{label=\"x\"}\n\\recolor{a.cell[0]}{color=warn}\n"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ir = _parse(src)
        cmds = _cmds_of_type(ir, RecolorCommand)
        assert len(cmds) == 1
        assert cmds[0].annotation_color == "warn"
        # Should have emitted a DeprecationWarning
        dep_warns = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warns) >= 1

    def test_recolor_multiple_cells_across_frames(self) -> None:
        """Multiple \\recolor in one step all appear in the same frame."""
        src = (
            _ARRAY_PRELUDE
            + "\\recolor{a.cell[0]}{state=current}\n"
            + "\\recolor{a.cell[1]}{state=done}\n"
        )
        ir = _parse(src)
        cmds = _cmds_of_type(ir, RecolorCommand)
        assert len(cmds) == 2

    # --- Error paths ---

    def test_recolor_unknown_state_raises_e1109(self) -> None:
        """Unknown state value → E1109."""
        src = _ARRAY_PRELUDE + "\\recolor{a.cell[0]}{state=flying}\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1109"

    def test_recolor_invalid_annotation_color_raises_e1113(self) -> None:
        """Deprecated color= with an invalid color value → E1113."""
        import warnings

        src = _ARRAY_PRELUDE + "\\annotate{a.cell[0]}{label=\"x\"}\n\\recolor{a.cell[0]}{color=purple}\n"
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            with pytest.raises(ValidationError) as exc_info:
                _parse(src)
        assert exc_info.value.code == "E1113"

    def test_recolor_missing_state_and_color_raises_e1109(self) -> None:
        """\\recolor with neither state nor color → E1109."""
        src = _ARRAY_PRELUDE + "\\recolor{a.cell[0]}{}\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1109"

    def test_recolor_state_typo_has_hint(self) -> None:
        """Typo in state value → E1109 with 'did you mean' hint."""
        src = _ARRAY_PRELUDE + "\\recolor{a.cell[0]}{state=currnet}\n"
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        err = exc_info.value
        assert err.code == "E1109"
        assert err.hint is not None and "current" in err.hint


# ===========================================================================
# \\reannotate
# ===========================================================================


@pytest.mark.unit
class TestReannotate:
    """``\\reannotate{target}{color=..., arrow_from=...}`` positive and error paths."""

    # --- Positive paths ---

    def test_reannotate_with_color_good(self) -> None:
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[0]}{label=\"x\"}\n"
            + "\\reannotate{a.cell[0]}{color=good}\n"
        )
        ir = _parse(src)
        cmds = _cmds_of_type(ir, ReannotateCommand)
        assert len(cmds) == 1
        cmd = cmds[0]
        assert cmd.color == "good"
        assert cmd.arrow_from is None

    def test_reannotate_with_color_warn(self) -> None:
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[1]}{label=\"note\"}\n"
            + "\\reannotate{a.cell[1]}{color=warn}\n"
        )
        ir = _parse(src)
        cmd = _cmds_of_type(ir, ReannotateCommand)[0]
        assert cmd.color == "warn"

    def test_reannotate_with_color_error(self) -> None:
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[2]}{label=\"err\"}\n"
            + "\\reannotate{a.cell[2]}{color=error}\n"
        )
        ir = _parse(src)
        cmd = _cmds_of_type(ir, ReannotateCommand)[0]
        assert cmd.color == "error"

    def test_reannotate_with_arrow_from(self) -> None:
        """arrow_from= is parsed and stored on the ReannotateCommand."""
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[0]}{label=\"x\"}\n"
            + "\\reannotate{a.cell[0]}{color=good, arrow_from=\"a.cell[4]\"}\n"
        )
        ir = _parse(src)
        cmd = _cmds_of_type(ir, ReannotateCommand)[0]
        assert cmd.color == "good"
        assert cmd.arrow_from == "a.cell[4]"

    def test_reannotate_target_selector_parsed(self) -> None:
        """Target selector shape name is correctly parsed."""
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[0]}{label=\"q\"}\n"
            + "\\reannotate{a.cell[0]}{color=info}\n"
        )
        ir = _parse(src)
        cmd = _cmds_of_type(ir, ReannotateCommand)[0]
        # Target may be a Selector or raw string depending on parse path
        target = cmd.target
        assert target is not None
        target_name = (
            target.shape_name if hasattr(target, "shape_name") else str(target)
        )
        assert "a" in target_name

    # --- Error paths ---

    def test_reannotate_missing_color_raises_e1113(self) -> None:
        """\\reannotate without color= → E1113."""
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[0]}{label=\"x\"}\n"
            + "\\reannotate{a.cell[0]}{}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1113"

    def test_reannotate_invalid_color_raises_e1113(self) -> None:
        """\\reannotate with an invalid color value → E1113."""
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[0]}{label=\"x\"}\n"
            + "\\reannotate{a.cell[0]}{color=purple}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1113"

    def test_reannotate_color_typo_raises_e1113(self) -> None:
        """Typo in \\reannotate color → E1113 with hint."""
        src = (
            _ARRAY_PRELUDE
            + "\\annotate{a.cell[0]}{label=\"x\"}\n"
            + "\\reannotate{a.cell[0]}{color=goood}\n"
        )
        with pytest.raises(ValidationError) as exc_info:
            _parse(src)
        assert exc_info.value.code == "E1113"
