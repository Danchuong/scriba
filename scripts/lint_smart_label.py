#!/usr/bin/env python3
"""Smart-label forbidden-pattern linter for scriba primitives.

Walks the AST of every file in scriba/animation/primitives/*.py
(excluding base.py, _svg_helpers.py, and infrastructure files) and
reports violations of the six Forbidden Patterns (FP-1..FP-6) defined in:
    docs/spec/smart-label-ruleset.md §5.3

Usage:
    python scripts/lint_smart_label.py [--json] [--advisory] [--strict] [--path PATH]

Exit codes:
    0  No violations found (also advisory mode regardless of violations).
    1  One or more ERROR-severity violations found (strict or default mode).
    2  Only WARNING-severity violations found.
    3  Script error (bad arguments, file not found, parse error).

Modes:
    Default (advisory): exits 0 always, prints violations as warnings.
    --advisory:         same as default — always exits 0.
    --strict:           exits 1 on any ERROR violation, 2 on WARNING-only.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Iterator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Names that indicate a variable holds hardcoded pill/glyph metrics (FP-3).
_FP3_SUSPICIOUS_NAMES: frozenset[str] = frozenset({
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
})

# Names of the three annotation helper functions whose direct use triggers FP-6.
_ANNOTATION_HELPERS: frozenset[str] = frozenset({
    "emit_arrow_svg",
    "emit_plain_arrow_svg",
    "emit_position_label_svg",
})

# Files excluded from all checks (infrastructure / helpers, not consumers).
_EXCLUDED_FILES: frozenset[str] = frozenset({
    "base.py",
    "_svg_helpers.py",
    "_text_render.py",
    "_types.py",
    "layout.py",
    "graph_layout_stable.py",
    "tree_layout.py",
    "plane2d_compute.py",
    "__init__.py",
})

# Default search path relative to this script.
_DEFAULT_PRIMITIVES_PATH = (
    pathlib.Path(__file__).parent.parent
    / "scriba" / "animation" / "primitives"
)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class Violation:
    file: str
    line: int
    col: int
    code: str       # e.g. "E1570-A"
    severity: str   # "ERROR" or "WARNING"
    message: str
    fp: str         # e.g. "FP-1"
    suppressed: bool = False


@dataclass
class FileContext:
    """Per-file state accumulated during a single AST walk."""

    path: pathlib.Path
    tree: ast.Module
    violations: list[Violation] = field(default_factory=list)
    # Names imported at module level.
    module_imports: set[str] = field(default_factory=set)
    # Set of (classname, methodname, fp_code) triples with @allow_forbidden_pattern.
    suppressed: set[tuple[str, str, str]] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node_name(node: ast.expr) -> str | None:
    """Extract simple name string from an AST Name or Attribute node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_primitive_class(node: ast.ClassDef) -> bool:
    """Heuristic: a class is a primitive if it defines an emit_svg method."""
    for item in ast.walk(node):
        if isinstance(item, ast.FunctionDef) and item.name == "emit_svg":
            return True
    return False


def _collect_module_imports(tree: ast.Module) -> set[str]:
    """Collect all names imported at module level."""
    names: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _collect_suppressed(tree: ast.Module) -> set[tuple[str, str, str]]:
    """Return set of (classname, methodname, fp_code) for suppressed violations.

    A suppression is declared by:
        @allow_forbidden_pattern("FP-X", reason="...", issue="...")
        def some_method(self): ...
    """
    suppressed: set[tuple[str, str, str]] = set()
    for class_node in ast.walk(tree):
        if not isinstance(class_node, ast.ClassDef):
            continue
        for method_node in ast.walk(class_node):
            if not isinstance(method_node, ast.FunctionDef):
                continue
            for decorator in method_node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                if _node_name(func) != "allow_forbidden_pattern":
                    continue
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    fp_code = decorator.args[0].value
                    suppressed.add((class_node.name, method_node.name, fp_code))
    return suppressed


def _iter_primitive_methods(
    tree: ast.Module,
) -> Iterator[tuple[ast.ClassDef, ast.FunctionDef]]:
    """Yield (class_node, method_node) pairs for every method in a primitive class."""
    for class_node in ast.walk(tree):
        if not isinstance(class_node, ast.ClassDef):
            continue
        if not _is_primitive_class(class_node):
            continue
        for method_node in ast.walk(class_node):
            if isinstance(method_node, ast.FunctionDef):
                yield class_node, method_node


# ---------------------------------------------------------------------------
# FP-1: Direct <text> emission / _render_svg_text call
# ---------------------------------------------------------------------------


def _check_fp1(ctx: FileContext) -> None:
    """Detect direct annotation text emission (FP-1, E1570-A).

    Triggers on:
      (a) Any FunctionDef named _emit_text_annotation inside a primitive class.
      (b) Any call to _render_svg_text inside a method whose name contains
          the substring "annotation" in a primitive class.
    """
    for class_node, method_node in _iter_primitive_methods(ctx.tree):
        # (a) Sentinel method name
        if method_node.name == "_emit_text_annotation":
            if (class_node.name, method_node.name, "FP-1") not in ctx.suppressed:
                ctx.violations.append(Violation(
                    file=str(ctx.path),
                    line=method_node.lineno,
                    col=method_node.col_offset,
                    code="E1570-A",
                    severity="ERROR",
                    message=(
                        f"[E1570-A] {class_node.name}.{method_node.name}: "
                        "method named '_emit_text_annotation' emits annotation "
                        "<text> directly, bypassing _svg_helpers collision registry. "
                        "Replace with emit_position_label_svg() via "
                        "self.emit_annotation_arrows() (FP-1)."
                    ),
                    fp="FP-1",
                ))
            continue  # no need to also scan the body for (b)

        # (b) _render_svg_text call inside annotation-context method
        if "annotation" not in method_node.name:
            continue
        for call_node in ast.walk(method_node):
            if not isinstance(call_node, ast.Call):
                continue
            name = _node_name(call_node.func)
            if name != "_render_svg_text":
                continue
            if (class_node.name, method_node.name, "FP-1") in ctx.suppressed:
                break
            ctx.violations.append(Violation(
                file=str(ctx.path),
                line=call_node.lineno,
                col=call_node.col_offset,
                code="E1570-A",
                severity="ERROR",
                message=(
                    f"[E1570-A] {class_node.name}.{method_node.name}: "
                    "call to _render_svg_text inside annotation method "
                    "bypasses collision registry (FP-1). "
                    "Use emit_position_label_svg() instead."
                ),
                fp="FP-1",
            ))
            break  # one violation per method is enough


# ---------------------------------------------------------------------------
# FP-2: Isolated placed_labels list per call
# ---------------------------------------------------------------------------


def _check_fp2(ctx: FileContext) -> None:
    """Detect isolated placed_labels list creation (FP-2, E1570-B).

    Flags annotated assignments of the form:
        foo: list[_LabelPlacement] = []
    inside primitive class methods that are NOT named
    'register_decorations' or 'dispatch_annotations'.
    """
    # Methods that legitimately create fresh list[_LabelPlacement]:
    _ALLOWED_METHODS = frozenset({"register_decorations", "dispatch_annotations"})

    for class_node, method_node in _iter_primitive_methods(ctx.tree):
        if method_node.name in _ALLOWED_METHODS:
            continue
        if (class_node.name, method_node.name, "FP-2") in ctx.suppressed:
            continue

        for stmt in ast.walk(method_node):
            if not isinstance(stmt, ast.AnnAssign):
                continue
            # Check annotation is list[_LabelPlacement]
            ann = stmt.annotation
            if not isinstance(ann, ast.Subscript):
                continue
            outer = _node_name(ann.value)
            if outer != "list":
                continue
            inner = ann.slice
            inner_name = _node_name(inner)
            if inner_name != "_LabelPlacement":
                continue
            # Check value is an empty list literal
            if stmt.value is None:
                continue
            if not isinstance(stmt.value, ast.List) or stmt.value.elts:
                continue

            target_name = _node_name(stmt.target) or "<unknown>"
            ctx.violations.append(Violation(
                file=str(ctx.path),
                line=stmt.lineno,
                col=stmt.col_offset,
                code="E1570-B",
                severity="ERROR",
                message=(
                    f"[E1570-B] {class_node.name}.{method_node.name}: "
                    f"'{target_name}: list[_LabelPlacement] = []' creates an "
                    "isolated placement registry that breaks multi-primitive "
                    "collision avoidance (FP-2). Use the shared placed_labels "
                    "registry passed from the frame caller."
                ),
                fp="FP-2",
            ))


# ---------------------------------------------------------------------------
# FP-3: Hardcoded glyph/pill metrics
# ---------------------------------------------------------------------------


def _check_fp3(ctx: FileContext) -> None:
    """Detect hardcoded glyph/pill metrics assigned to suspicious names (FP-3, E1570-C).

    Flags any assignment of the form:
        suspicious_name = <integer or float constant>
    inside a primitive class method body.
    """
    for class_node, method_node in _iter_primitive_methods(ctx.tree):
        if (class_node.name, method_node.name, "FP-3") in ctx.suppressed:
            continue

        for stmt in ast.walk(method_node):
            target_name: str | None = None
            value_node: ast.expr | None = None

            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    name = _node_name(t)
                    if name and name in _FP3_SUSPICIOUS_NAMES:
                        target_name = name
                        value_node = stmt.value
                        break
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                name = _node_name(stmt.target)
                if name and name in _FP3_SUSPICIOUS_NAMES:
                    target_name = name
                    value_node = stmt.value

            if target_name is None or value_node is None:
                continue
            if not isinstance(value_node, ast.Constant):
                continue
            if not isinstance(value_node.value, (int, float)):
                continue

            ctx.violations.append(Violation(
                file=str(ctx.path),
                line=stmt.lineno,
                col=stmt.col_offset,
                code="E1570-C",
                severity="ERROR",
                message=(
                    f"[E1570-C] {class_node.name}.{method_node.name}: "
                    f"hardcoded metric '{target_name} = {value_node.value}' "
                    "duplicates a named constant in _svg_helpers.py (FP-3). "
                    "Import and use the canonical constant instead."
                ),
                fp="FP-3",
            ))


# ---------------------------------------------------------------------------
# FP-4: No viewBox clamp after pill placement (WARNING)
# ---------------------------------------------------------------------------


def _check_fp4(ctx: FileContext) -> None:
    """Detect pill placement without viewBox clamping (FP-4, E1570-D).

    Heuristic: a FunctionDef that assigns 'pill_rx' or 'pill_ry' but
    does NOT contain any call to max(0, ...) or min(...) in the same
    scope is flagged as a WARNING.
    """
    _PILL_PLACEMENT_VARS = frozenset({"pill_rx", "pill_ry"})
    _CLAMP_FUNCS = frozenset({"max", "min"})

    for class_node, method_node in _iter_primitive_methods(ctx.tree):
        if (class_node.name, method_node.name, "FP-4") in ctx.suppressed:
            continue

        has_pill_placement = False
        has_clamp = False

        for node in ast.walk(method_node):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if _node_name(t) in _PILL_PLACEMENT_VARS:
                        has_pill_placement = True
            elif isinstance(node, ast.AnnAssign):
                if _node_name(node.target) in _PILL_PLACEMENT_VARS:
                    has_pill_placement = True
            elif isinstance(node, ast.Call):
                if _node_name(node.func) in _CLAMP_FUNCS:
                    has_clamp = True

        if has_pill_placement and not has_clamp:
            ctx.violations.append(Violation(
                file=str(ctx.path),
                line=method_node.lineno,
                col=method_node.col_offset,
                code="E1570-D",
                severity="WARNING",
                message=(
                    f"[E1570-D] {class_node.name}.{method_node.name}: "
                    "assigns pill_rx/pill_ry but has no max()/min() clamp call — "
                    "pill may overflow the viewBox (FP-4). "
                    "Add viewBox boundary clamping after computing pill position."
                ),
                fp="FP-4",
            ))


# ---------------------------------------------------------------------------
# FP-5: arrow_from-only annotation filter (drops position-only)
# ---------------------------------------------------------------------------


def _check_fp5(ctx: FileContext) -> None:
    """Detect annotation filters that drop position-only labels (FP-5, E1570-E).

    Flags list comprehensions of the form:
        [a for a in X if a.get("arrow_from")]
    where there is no OR branch for a.get("arrow") or a.get("label").
    """
    for class_node, method_node in _iter_primitive_methods(ctx.tree):
        if (class_node.name, method_node.name, "FP-5") in ctx.suppressed:
            continue

        for node in ast.walk(method_node):
            if not isinstance(node, ast.ListComp):
                continue
            if len(node.generators) != 1:
                continue
            gen = node.generators[0]
            if len(gen.ifs) != 1:
                continue

            cond = gen.ifs[0]
            if not _is_sole_arrow_from_filter(cond):
                continue

            ctx.violations.append(Violation(
                file=str(ctx.path),
                line=node.lineno,
                col=node.col_offset,
                code="E1570-E",
                severity="ERROR",
                message=(
                    f"[E1570-E] {class_node.name}.{method_node.name}: "
                    'annotation filter [... if a.get("arrow_from")] discards '
                    "position-only labels (FP-5). "
                    'Add an OR branch: a.get("arrow_from") or a.get("arrow") '
                    'or a.get("label").'
                ),
                fp="FP-5",
            ))


def _is_sole_arrow_from_filter(cond: ast.expr) -> bool:
    """Return True if condition is solely a.get("arrow_from") with no OR broadening."""
    # Unwrap: might be a plain Call or a BoolOp
    if isinstance(cond, ast.BoolOp):
        # If there is an OR with "arrow" or "label" keys present, it is NOT FP-5.
        if isinstance(cond.op, ast.Or):
            for value in cond.values:
                if _extracts_key(value, ("arrow", "label", "position")):
                    return False
        # A pure AND of arrow_from checks is still only arrow_from — flag it.
        return any(_extracts_key(v, ("arrow_from",)) for v in cond.values)
    return _extracts_key(cond, ("arrow_from",)) and not _extracts_key(cond, ("arrow", "label"))


def _extracts_key(node: ast.expr, keys: tuple[str, ...]) -> bool:
    """Return True if node is a call of the form obj.get("<key>") for any key in keys."""
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
        return False
    if not node.args:
        return False
    first_arg = node.args[0]
    if not isinstance(first_arg, ast.Constant):
        return False
    return first_arg.value in keys


# ---------------------------------------------------------------------------
# FP-6: Direct emit_arrow_svg bypass of base.emit_annotation_arrows
# ---------------------------------------------------------------------------


def _check_fp6(ctx: FileContext) -> None:
    """Detect direct calls to emit_arrow_svg bypassing base dispatcher (FP-6, E1570-F).

    Flags calls to emit_arrow_svg / emit_plain_arrow_svg / emit_position_label_svg
    inside primitive class methods, EXCLUDING dispatch_annotations (which is
    explicitly allowed to call helpers directly per §5.1.6 contract).
    """
    _EXEMPT_METHODS = frozenset({"dispatch_annotations"})

    for class_node, method_node in _iter_primitive_methods(ctx.tree):
        if method_node.name in _EXEMPT_METHODS:
            continue
        if (class_node.name, method_node.name, "FP-6") in ctx.suppressed:
            continue

        for node in ast.walk(method_node):
            if not isinstance(node, ast.Call):
                continue
            name = _node_name(node.func)
            if name not in _ANNOTATION_HELPERS:
                continue

            ctx.violations.append(Violation(
                file=str(ctx.path),
                line=node.lineno,
                col=node.col_offset,
                code="E1570-F",
                severity="ERROR",
                message=(
                    f"[E1570-F] {class_node.name}.{method_node.name}: "
                    f"direct call to {name!r} bypasses "
                    "base.emit_annotation_arrows dispatcher (FP-6). "
                    "Route all annotation dispatch through "
                    "self.emit_annotation_arrows() or self.dispatch_annotations()."
                ),
                fp="FP-6",
            ))


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_CHECKS = [_check_fp1, _check_fp2, _check_fp3, _check_fp4, _check_fp5, _check_fp6]


def _lint_file(path: pathlib.Path) -> list[Violation]:
    """Parse and lint a single file, returning all violations."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [Violation(
            file=str(path),
            line=exc.lineno or 0,
            col=exc.offset or 0,
            code="E1570-PARSE",
            severity="ERROR",
            message=f"[E1570-PARSE] Cannot parse {path.name}: {exc}",
            fp="N/A",
        )]

    ctx = FileContext(
        path=path,
        tree=tree,
        module_imports=_collect_module_imports(tree),
        suppressed=_collect_suppressed(tree),
    )
    for check in _CHECKS:
        check(ctx)
    return ctx.violations


def lint_primitives(primitives_path: pathlib.Path) -> list[Violation]:
    """Walk primitives_path and return all violations."""
    all_violations: list[Violation] = []
    for py_file in sorted(primitives_path.glob("*.py")):
        if py_file.name in _EXCLUDED_FILES:
            continue
        all_violations.extend(_lint_file(py_file))
    return all_violations


def _emit_text(violations: list[Violation], *, advisory: bool) -> int:
    """Print violations in file:line:col format. Return the logical exit code."""
    errors = [v for v in violations if v.severity == "ERROR" and not v.suppressed]
    warnings = [v for v in violations if v.severity == "WARNING" and not v.suppressed]
    for v in sorted(errors + warnings, key=lambda x: (x.file, x.line, x.col)):
        print(f"{v.file}:{v.line}:{v.col}: {v.severity} {v.code} {v.message}")
    if not errors and not warnings:
        print("lint_smart_label: no violations found.")
        return 0
    print(
        f"\nlint_smart_label: {len(errors)} error(s), {len(warnings)} warning(s)."
        + (" [advisory mode — exit 0]" if advisory else "")
    )
    if advisory:
        return 0
    return 1 if errors else 2


def main(argv: list[str] | None = None) -> int:
    """Entry point for CLI invocation."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument(
        "--advisory",
        action="store_true",
        default=False,
        help="Always exit 0 (warn-only mode). This is the default.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Exit 1 on ERROR violations, 2 on WARNING-only. Overrides --advisory.",
    )
    parser.add_argument(
        "--path",
        type=pathlib.Path,
        default=_DEFAULT_PRIMITIVES_PATH,
        help="Path to primitives directory.",
    )
    args = parser.parse_args(argv)

    # Strict overrides advisory; default is advisory.
    advisory = (not args.strict)

    try:
        violations = lint_primitives(args.path)
    except Exception as exc:  # noqa: BLE001
        print(f"lint_smart_label: fatal error — {exc}", file=sys.stderr)
        return 3

    if args.json:
        import dataclasses

        print(json.dumps([dataclasses.asdict(v) for v in violations], indent=2))
        errors = [v for v in violations if v.severity == "ERROR" and not v.suppressed]
        if advisory:
            return 0
        return 1 if errors else 0

    return _emit_text(violations, advisory=advisory)


if __name__ == "__main__":
    sys.exit(main())
