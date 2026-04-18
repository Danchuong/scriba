"""Unit tests for _check_interpolation_binding and _collect_compute_bindings.

Exercises interpolation binding logic through SceneParser.parse() end-to-end
with narrow inputs. Positive paths verify that known compute bindings suppress
the UserWarning; error paths verify that undefined references emit warnings and
that scope/type edge cases behave correctly.

Wave F1a prerequisite for grammar.py mixin split (Wave F2-F6).
"""

from __future__ import annotations

import warnings

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.parser.ast import (
    ApplyCommand,
    ForeachCommand,
    HighlightCommand,
    InterpolationRef,
)
from scriba.core.errors import ValidationError

# Sentinel text that appears in the warning emitted by
# _check_interpolation_binding when no binding is found.
_NO_BINDING_MSG = "no compute-scope binding"


@pytest.fixture()
def parser() -> SceneParser:
    return SceneParser()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _binding_warnings(caught: list) -> list[str]:
    """Return message strings for all caught UserWarnings about missing bindings."""
    return [str(w.message) for w in caught if _NO_BINDING_MSG in str(w.message)]


# ---------------------------------------------------------------------------
# Positive paths — known binding suppresses the warning
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInterpolationBindingPositivePaths:
    """_check_interpolation_binding should remain silent for known bindings."""

    def test_compute_binding_used_in_apply_no_warning(
        self, parser: SceneParser
    ) -> None:
        """A \\compute binding referenced in \\apply produces no warning."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\compute{dp = [0, 1, 2, 3]}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=${dp}}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ir = parser.parse(src)

        assert _binding_warnings(caught) == [], (
            f"expected no binding warning, got: {_binding_warnings(caught)}"
        )
        # The parsed value should be an InterpolationRef
        cmd = [c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)][0]
        assert isinstance(cmd.params["value"], InterpolationRef)
        assert cmd.params["value"].name == "dp"

    def test_compute_binding_used_in_highlight_selector_no_warning(
        self, parser: SceneParser
    ) -> None:
        """A \\compute binding used inside a highlight selector produces no warning."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\compute{idx = 2}\n"
            "\\step\n"
            "\\highlight{a.cell[${idx}]}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ir = parser.parse(src)

        assert _binding_warnings(caught) == [], (
            f"expected no binding warning, got: {_binding_warnings(caught)}"
        )

    def test_compute_binding_used_in_apply_selector_no_warning(
        self, parser: SceneParser
    ) -> None:
        """A \\compute binding referenced in an \\apply selector produces no warning."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\compute{pos = 1}\n"
            "\\step\n"
            "\\apply{a.cell[${pos}]}{value=99}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src)

        assert _binding_warnings(caught) == []

    def test_foreach_loop_var_not_flagged_inside_body(
        self, parser: SceneParser
    ) -> None:
        """The foreach loop variable is a known binding inside the body and
        should not trigger a warning."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..3}\n"
            "  \\apply{a.cell[${i}]}{value=1}\n"
            "\\endforeach\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src)

        assert _binding_warnings(caught) == [], (
            f"foreach var 'i' should not warn, got: {_binding_warnings(caught)}"
        )

    def test_def_binding_from_compute_no_warning(
        self, parser: SceneParser
    ) -> None:
        """A 'def name(...):' in \\compute registers the function name as a binding."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\compute{def my_fn(x): return x}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=${my_fn}}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src)

        assert _binding_warnings(caught) == []

    def test_multi_assignment_binding_no_warning(
        self, parser: SceneParser
    ) -> None:
        """A tuple assignment 'a, b = ...' registers both names as bindings."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\compute{x, y = 1, 2}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=${x}}\n"
            "\\apply{a.cell[1]}{value=${y}}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src)

        assert _binding_warnings(caught) == []


# ---------------------------------------------------------------------------
# Error paths — undefined references emit UserWarning
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInterpolationBindingErrorPaths:
    """_check_interpolation_binding should warn for undefined references."""

    def test_undefined_interpolation_in_apply_warns(
        self, parser: SceneParser
    ) -> None:
        """An \\apply referencing ${nope} with no compute binding emits a warning."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=${nope}}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src)

        msgs = _binding_warnings(caught)
        assert msgs, "expected warning about undefined binding 'nope'"
        assert "nope" in msgs[0]

    def test_undefined_interpolation_in_foreach_iterable_warns(
        self, parser: SceneParser
    ) -> None:
        """An undefined ${ref} used as a foreach iterable emits a warning."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{${undefined_list}}\n"
            "  \\recolor{a.cell[${i}]}{state=done}\n"
            "\\endforeach\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src)

        msgs = _binding_warnings(caught)
        assert msgs, "expected warning about undefined binding 'undefined_list'"
        assert "undefined_list" in msgs[0]

    def test_undefined_interpolation_in_apply_param_value_warns(
        self, parser: SceneParser
    ) -> None:
        """${ghost} as an \\apply param value with no prior compute binding
        emits a warning. Note: selector index interpolations go through
        the standalone parse_selector() which does not call
        _check_interpolation_binding, so we exercise the param-value path."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=${ghost}}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src)

        msgs = _binding_warnings(caught)
        assert msgs, "expected warning about undefined binding 'ghost'"
        assert "ghost" in msgs[0]

    def test_foreach_loop_var_not_visible_after_endforeach(
        self, parser: SceneParser
    ) -> None:
        """The loop variable should not remain in scope after \\endforeach;
        referencing it in an \\apply param value outside the block warns about
        an undefined binding. Uses value=${i} (param path) since selector
        index interpolations bypass _check_interpolation_binding."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\foreach{i}{0..1}\n"
            "  \\recolor{a.cell[${i}]}{state=done}\n"
            "\\endforeach\n"
            # 'i' should no longer be a known binding here
            "\\apply{a.cell[0]}{value=${i}}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src)

        msgs = _binding_warnings(caught)
        assert msgs, (
            "expected warning: 'i' should not be in scope after \\endforeach"
        )
        assert "i" in msgs[0]

    def test_error_recovery_mode_suppresses_interpolation_warning(
        self, parser: SceneParser
    ) -> None:
        """When error_recovery=True the interpolation warning is suppressed
        (_check_interpolation_binding early-exits for recovery mode)."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=${no_binding}}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src, error_recovery=True)

        msgs = _binding_warnings(caught)
        assert msgs == [], (
            f"error_recovery=True should suppress binding warnings, got: {msgs}"
        )

    def test_collect_compute_bindings_for_stmt(
        self, parser: SceneParser
    ) -> None:
        """A 'for var in ...:' statement in \\compute registers the loop variable."""
        src = (
            "\\shape{a}{Array}{size=4}\n"
            "\\compute{for item in range(4): pass}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{value=${item}}\n"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser.parse(src)

        # 'item' should be recognized as a known binding from the 'for' stmt
        msgs = _binding_warnings(caught)
        assert msgs == [], (
            f"'for item in ...' should register 'item' as a binding, got: {msgs}"
        )
