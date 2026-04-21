"""Unit tests for scripts/lint_smart_label.py.

Tests cover:
- Fixture-based detection of FP-1..FP-6 violations.
- Advisory mode always exits 0.
- Strict mode exits 1 on ERROR, 2 on WARNING-only.
- Clean primitive produces no violations.
- @allow_forbidden_pattern suppression.
"""

from __future__ import annotations

import pathlib
import textwrap
import types

import pytest

# ---------------------------------------------------------------------------
# Import the linter module from scripts/
# ---------------------------------------------------------------------------

import importlib.util
import sys

_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
_LINT_SCRIPT = _REPO_ROOT / "scripts" / "lint_smart_label.py"


def _load_lint_module():
    spec = importlib.util.spec_from_file_location("lint_smart_label", _LINT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lint_smart_label"] = mod
    spec.loader.exec_module(mod)
    return mod


_lint = _load_lint_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lint_source(source: str) -> list[_lint.Violation]:
    """Lint an in-memory source string as if it were a primitives file."""
    import ast
    tree = ast.parse(textwrap.dedent(source))
    ctx = _lint.FileContext(
        path=pathlib.Path("test_fixture.py"),
        tree=tree,
        module_imports=_lint._collect_module_imports(tree),
        suppressed=_lint._collect_suppressed(tree),
    )
    for check in _lint._CHECKS:
        check(ctx)
    return ctx.violations


def _codes(violations: list[_lint.Violation]) -> list[str]:
    return [v.code for v in violations]


def _fps(violations: list[_lint.Violation]) -> list[str]:
    return [v.fp for v in violations]


# ---------------------------------------------------------------------------
# FP-1: _emit_text_annotation sentinel (E1570-A)
# ---------------------------------------------------------------------------


class TestFP1:
    SOURCE_VIOLATION = """\
        class MyPrimitive:
            def emit_svg(self):
                return ""

            def _emit_text_annotation(self, lines, ann):
                pass
    """

    SOURCE_CLEAN = """\
        class MyPrimitive:
            def emit_svg(self):
                return ""

            def _emit_annotation_arrows(self, lines, ann):
                pass
    """

    def test_detects_sentinel_method_name(self):
        violations = _lint_source(self.SOURCE_VIOLATION)
        assert any(v.code == "E1570-A" for v in violations), violations

    def test_clean_no_violations(self):
        violations = _lint_source(self.SOURCE_CLEAN)
        assert not any(v.code == "E1570-A" for v in violations)

    def test_violation_is_error_severity(self):
        violations = _lint_source(self.SOURCE_VIOLATION)
        fp1 = [v for v in violations if v.code == "E1570-A"]
        assert all(v.severity == "ERROR" for v in fp1)

    def test_fp1_render_svg_text_in_annotation_method(self):
        source = """\
            class MyPrimitive:
                def emit_svg(self):
                    return ""

                def _emit_annotation_text(self, ann):
                    _render_svg_text("hello", 0, 0)
        """
        violations = _lint_source(source)
        assert any(v.code == "E1570-A" for v in violations)


# ---------------------------------------------------------------------------
# FP-2: Isolated placed_labels list (E1570-B)
# ---------------------------------------------------------------------------


class TestFP2:
    SOURCE_VIOLATION = """\
        class MyPrimitive:
            def emit_svg(self):
                placed: list[_LabelPlacement] = []
                return ""
    """

    SOURCE_CLEAN_PARAM = """\
        class MyPrimitive:
            def emit_svg(self, placed_labels=None):
                return ""
    """

    SOURCE_ALLOWED_METHOD = """\
        class MyPrimitive:
            def emit_svg(self):
                return ""

            def register_decorations(self, registry):
                placed: list[_LabelPlacement] = []
                return placed
    """

    def test_detects_isolated_list(self):
        violations = _lint_source(self.SOURCE_VIOLATION)
        assert any(v.code == "E1570-B" for v in violations), violations

    def test_allowed_method_no_violation(self):
        violations = _lint_source(self.SOURCE_ALLOWED_METHOD)
        assert not any(v.code == "E1570-B" for v in violations)

    def test_non_primitive_no_violation(self):
        # Class without emit_svg is not treated as a primitive.
        source = """\
            class Helper:
                def do_stuff(self):
                    placed: list[_LabelPlacement] = []
        """
        violations = _lint_source(source)
        assert not any(v.code == "E1570-B" for v in violations)

    def test_violation_is_error_severity(self):
        violations = _lint_source(self.SOURCE_VIOLATION)
        fp2 = [v for v in violations if v.code == "E1570-B"]
        assert all(v.severity == "ERROR" for v in fp2)


# ---------------------------------------------------------------------------
# FP-3: Hardcoded glyph/pill metrics (E1570-C)
# ---------------------------------------------------------------------------


class TestFP3:
    def _make_source(self, varname: str, value: int = 7) -> str:
        return textwrap.dedent(f"""\
            class MyPrimitive:
                def emit_svg(self):
                    {varname} = {value}
                    return ""
        """)

    @pytest.mark.parametrize("varname", [
        "char_width",
        "pill_h",
        "pill_w",
        "pill_rx",
        "_PILL_PAD_X",
        "_PILL_PAD_Y",
        "_PILL_R",
        "_CHAR_W",
        "_LINE_LABEL_CHAR_W",
        "_LINE_PILL_PAD_X",
        "_LINE_PILL_PAD_Y",
        "_WEIGHT_FONT",
    ])
    def test_detects_suspicious_name(self, varname):
        violations = _lint_source(self._make_source(varname))
        assert any(v.code == "E1570-C" for v in violations), (
            f"Expected E1570-C for {varname!r}"
        )

    def test_clean_variable_name_no_violation(self):
        source = """\
            class MyPrimitive:
                def emit_svg(self):
                    r = 8
                    cx = 50
                    return ""
        """
        violations = _lint_source(source)
        assert not any(v.code == "E1570-C" for v in violations)

    def test_string_value_no_violation(self):
        # Only integer/float values trigger FP-3.
        source = """\
            class MyPrimitive:
                def emit_svg(self):
                    char_width = "7px"
                    return ""
        """
        violations = _lint_source(source)
        assert not any(v.code == "E1570-C" for v in violations)

    def test_violation_is_error_severity(self):
        violations = _lint_source(self._make_source("pill_h"))
        fp3 = [v for v in violations if v.code == "E1570-C"]
        assert all(v.severity == "ERROR" for v in fp3)


# ---------------------------------------------------------------------------
# FP-4: No viewBox clamp after pill placement (E1570-D / WARNING)
# ---------------------------------------------------------------------------


class TestFP4:
    SOURCE_VIOLATION = """\
        class MyPrimitive:
            def emit_svg(self):
                pill_rx = cx - pill_w / 2
                pill_ry = cy - pill_h / 2
                return ""
    """

    SOURCE_CLEAN = """\
        class MyPrimitive:
            def emit_svg(self):
                pill_rx = cx - pill_w / 2
                pill_rx = max(0, pill_rx)
                return ""
    """

    def test_detects_missing_clamp(self):
        violations = _lint_source(self.SOURCE_VIOLATION)
        assert any(v.code == "E1570-D" for v in violations), violations

    def test_with_clamp_no_violation(self):
        violations = _lint_source(self.SOURCE_CLEAN)
        assert not any(v.code == "E1570-D" for v in violations)

    def test_violation_is_warning_severity(self):
        violations = _lint_source(self.SOURCE_VIOLATION)
        fp4 = [v for v in violations if v.code == "E1570-D"]
        assert fp4, "Should have at least one FP-4 violation"
        assert all(v.severity == "WARNING" for v in fp4)


# ---------------------------------------------------------------------------
# FP-5: arrow_from-only filter (E1570-E)
# ---------------------------------------------------------------------------


class TestFP5:
    SOURCE_VIOLATION = """\
        class MyPrimitive:
            def emit_svg(self, anns):
                arrow_anns = [a for a in anns if a.get("arrow_from")]
                return ""
    """

    SOURCE_CLEAN_OR = """\
        class MyPrimitive:
            def emit_svg(self, anns):
                arrow_anns = [a for a in anns if a.get("arrow_from") or a.get("arrow")]
                return ""
    """

    SOURCE_CLEAN_LABEL_OR = """\
        class MyPrimitive:
            def emit_svg(self, anns):
                arrow_anns = [a for a in anns if a.get("arrow_from") or a.get("label")]
                return ""
    """

    def test_detects_sole_arrow_from_filter(self):
        violations = _lint_source(self.SOURCE_VIOLATION)
        assert any(v.code == "E1570-E" for v in violations), violations

    def test_or_arrow_branch_no_violation(self):
        violations = _lint_source(self.SOURCE_CLEAN_OR)
        assert not any(v.code == "E1570-E" for v in violations)

    def test_or_label_branch_no_violation(self):
        violations = _lint_source(self.SOURCE_CLEAN_LABEL_OR)
        assert not any(v.code == "E1570-E" for v in violations)

    def test_violation_is_error_severity(self):
        violations = _lint_source(self.SOURCE_VIOLATION)
        fp5 = [v for v in violations if v.code == "E1570-E"]
        assert all(v.severity == "ERROR" for v in fp5)


# ---------------------------------------------------------------------------
# FP-6: Direct emit_arrow_svg bypass (E1570-F)
# ---------------------------------------------------------------------------


class TestFP6:
    @pytest.mark.parametrize("helper_name", [
        "emit_arrow_svg",
        "emit_plain_arrow_svg",
        "emit_position_label_svg",
    ])
    def test_detects_direct_call(self, helper_name: str):
        source = textwrap.dedent(f"""\
            class MyPrimitive:
                def emit_svg(self, anns):
                    {helper_name}([], {{}}, (0, 0), (1, 1), 0, 10, None)
                    return ""
        """)
        violations = _lint_source(source)
        assert any(v.code == "E1570-F" for v in violations), (
            f"Expected E1570-F for call to {helper_name!r}"
        )

    def test_dispatch_annotations_exempt(self):
        """Calls inside dispatch_annotations are explicitly permitted."""
        source = """\
            class MyPrimitive:
                def emit_svg(self):
                    return ""

                def dispatch_annotations(self, placed_labels):
                    emit_arrow_svg([], {}, (0, 0), (1, 1), 0, 10, None)
                    return []
        """
        violations = _lint_source(source)
        assert not any(v.code == "E1570-F" for v in violations)

    def test_violation_is_error_severity(self):
        source = """\
            class MyPrimitive:
                def emit_svg(self, anns):
                    emit_arrow_svg([], {}, (0, 0), (1, 1), 0, 10, None)
                    return ""
        """
        violations = _lint_source(source)
        fp6 = [v for v in violations if v.code == "E1570-F"]
        assert all(v.severity == "ERROR" for v in fp6)


# ---------------------------------------------------------------------------
# @allow_forbidden_pattern suppression
# ---------------------------------------------------------------------------


class TestSuppression:
    def test_fp1_suppressed_by_decorator(self):
        source = """\
            def allow_forbidden_pattern(fp, *, reason, issue):
                def decorator(func):
                    return func
                return decorator

            class MyPrimitive:
                def emit_svg(self):
                    return ""

                @allow_forbidden_pattern("FP-1", reason="legacy", issue="#1")
                def _emit_text_annotation(self, lines, ann):
                    pass
        """
        violations = _lint_source(source)
        # Suppressed — should not appear
        assert not any(v.code == "E1570-A" and not v.suppressed for v in violations)

    def test_fp3_suppressed_by_decorator(self):
        source = """\
            def allow_forbidden_pattern(fp, *, reason, issue):
                def decorator(func):
                    return func
                return decorator

            class MyPrimitive:
                def emit_svg(self):
                    return ""

                @allow_forbidden_pattern("FP-3", reason="legacy", issue="#1")
                def _render_edge_labels(self):
                    char_width = 7
                    return ""
        """
        violations = _lint_source(source)
        assert not any(v.code == "E1570-C" and not v.suppressed for v in violations)


# ---------------------------------------------------------------------------
# main() exit codes
# ---------------------------------------------------------------------------


class TestMainExitCodes:
    def _run_main(self, source: str, extra_args: list[str] | None = None) -> int:
        """Write source to a temp file, point linter at it, return exit code."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            p = pathlib.Path(tmpdir) / "test_prim.py"
            p.write_text(textwrap.dedent(source))
            argv = ["--path", tmpdir] + (extra_args or [])
            return _lint.main(argv)

    def test_advisory_mode_exits_0_on_error_violations(self):
        source = """\
            class MyPrimitive:
                def emit_svg(self):
                    return ""

                def _emit_text_annotation(self, lines, ann):
                    pass
        """
        code = self._run_main(source, ["--advisory"])
        assert code == 0

    def test_strict_mode_exits_1_on_error_violations(self):
        source = """\
            class MyPrimitive:
                def emit_svg(self):
                    return ""

                def _emit_text_annotation(self, lines, ann):
                    pass
        """
        code = self._run_main(source, ["--strict"])
        assert code == 1

    def test_strict_mode_exits_2_on_warning_only(self):
        """Only FP-4 produces WARNING; ensure exit code is 2 in strict mode."""
        # Use non-suspicious variable names for the computation so only
        # FP-4 (absence of clamping) fires, not FP-3 (hardcoded metric names).
        source = """\
            class MyPrimitive:
                def emit_svg(self):
                    cx = some_func()
                    cy = other_func()
                    pill_rx = cx - 5
                    pill_ry = cy - 8
                    return ""
        """
        code = self._run_main(source, ["--strict"])
        assert code == 2

    def test_default_mode_is_advisory(self):
        """Default (no flags) should behave like --advisory (exit 0 even with errors)."""
        source = """\
            class MyPrimitive:
                def emit_svg(self):
                    return ""

                def _emit_text_annotation(self, lines, ann):
                    pass
        """
        code = self._run_main(source)
        assert code == 0

    def test_clean_file_exits_0(self):
        source = """\
            class MyPrimitive:
                def emit_svg(self):
                    return ""
        """
        code = self._run_main(source, ["--strict"])
        assert code == 0


# ---------------------------------------------------------------------------
# Live codebase scan — detect exactly 12 unique (primitive, FP) pairs
# ---------------------------------------------------------------------------


class TestLiveScan:
    def test_live_scan_detects_12_primitive_fp_pairs(self):
        """Validate that the linter finds exactly 12 unique (primitive, FP) pairs
        as documented in R3 §5.1 audit table."""
        primitives_path = _REPO_ROOT / "scriba" / "animation" / "primitives"
        violations = _lint.lint_primitives(primitives_path)
        pairs = {
            (v.file.split("/")[-1].replace(".py", "").lower(), v.fp)
            for v in violations
        }
        assert len(pairs) == 12, (
            f"Expected 12 unique (primitive, FP) pairs, got {len(pairs)}: {sorted(pairs)}"
        )

    def test_live_scan_fp_counts_match_r3_audit(self):
        """Validate per-FP violation counts match R3 §5.1."""
        import collections

        primitives_path = _REPO_ROOT / "scriba" / "animation" / "primitives"
        violations = _lint.lint_primitives(primitives_path)

        # Count unique (primitive, fp) pairs per FP code
        pairs_by_fp: dict[str, set] = collections.defaultdict(set)
        for v in violations:
            fname = v.file.split("/")[-1].replace(".py", "").lower()
            pairs_by_fp[v.fp].add(fname)

        # R3 §5.1 expected primitive counts per FP
        expected = {
            "FP-1": 1,  # Plane2D
            "FP-2": 4,  # Graph, Plane2D, Queue, NumberLine
            "FP-3": 2,  # Plane2D, Graph
            "FP-4": 1,  # Graph (Plane2D FP-4 is only in _emit_text_annotation which FP-1 already catches)
            "FP-5": 2,  # Queue, NumberLine
            "FP-6": 2,  # Queue, NumberLine
        }
        for fp_code, expected_count in expected.items():
            actual_count = len(pairs_by_fp.get(fp_code, set()))
            assert actual_count == expected_count, (
                f"{fp_code}: expected {expected_count} primitives, "
                f"got {actual_count} ({sorted(pairs_by_fp.get(fp_code, set()))})"
            )
