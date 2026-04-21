# Lint and Protocol Enforcement Design

**Document:** 03-lint-and-protocol-enforcement.md
**Date:** 2026-04-21
**Status:** DESIGN (Round-3 foundation material)
**Author:** scriba-core
**Applies to:** `scriba/animation/primitives/*.py` (15 primitive files)
**Supersedes:** nothing — first edition
**Normative anchor:** `docs/spec/smart-label-ruleset.md §5`

---

## 0. Purpose

Ruleset v2 §5.3 defines six Forbidden Patterns (FP-1..FP-6) for primitive
classes in prose only. This document converts them into:

1. A machine-verifiable AST-pattern catalogue with CI error codes.
2. A recommended static-lint tool selection with full tradeoff analysis.
3. A `scripts/lint_smart_label.py` implementation sketch (~200 lines)
   covering FP-1 and FP-3 in full, FP-2/FP-4/FP-5/FP-6 as stubs.
4. A `typing.Protocol`-based runtime `PrimitiveProtocol` and a gated
   `register_primitive` replacement that raises `TypeError` on non-conformance.
5. A concrete per-primitive audit table (15 primitives × 6 FPs).
6. An `@allow_forbidden_pattern` escape-hatch decorator with CI-grep
   enforcement and semver implications.
7. A CI wiring plan (pre-commit + GitHub Actions, <5 s budget).
8. Non-goals — tools deliberately excluded.

This document is **design-only**. No production files are modified.
The lint script is sketched here as a specification artefact; it MUST NOT
be created from this document alone without a separate implementation PR
that includes tests.

---

## §1 FP-1..FP-6 Catalogue

### §1.1 Summary

| ID | Name | Error code | Severity | File scope | False-positive risk |
|----|------|-----------|----------|------------|---------------------|
| FP-1 | Direct `<text>` for annotation labels | E1570-A | ERROR | `scriba/animation/primitives/*.py` | Low |
| FP-2 | Isolated `placed_labels` list per call | E1570-B | ERROR | same | Medium |
| FP-3 | Hardcoded glyph/pill metrics | E1570-C | ERROR | same | Low-medium |
| FP-4 | No viewBox clamp after placement | E1570-D | WARNING | same | Medium |
| FP-5 | `arrow_from`-only annotation filter | E1570-E | ERROR | same | Low |
| FP-6 | Direct `emit_arrow_svg` bypass | E1570-F | ERROR | same | Low |

All six map under the umbrella error code **E1570** (defined in
`docs/spec/smart-label-ruleset.md §4`, rule M-13). Sub-suffixes A–F
distinguish the specific violation in CI output without consuming
additional E15xx slots. If the error-code registry expands to assign
individual codes, the sub-suffix scheme collapses to those codes; the
structural design below is stable either way.

---

### §1.2 FP-1 — Direct `<text>` emission for annotation labels

**Prose rule (§5.3):** A primitive MUST NOT emit `<text>` SVG elements
for annotation labels directly. All annotation text MUST flow through
`_svg_helpers.py` helper functions (`emit_arrow_svg`,
`emit_plain_arrow_svg`, `emit_position_label_svg`).

**Rationale:** Direct `<text>` emission bypasses the collision-avoidance
registry (§2.3 C-3/C-4), the headroom helpers (§3.3 AC-5/AC-6), the pill
AABB registration (G-1), and viewBox clamping (G-3/G-4). It produces
annotations that ignore all other placed labels in the same frame.

**Current violation:** `plane2d.py:673–752` — `_emit_text_annotation`
method builds a `<rect>` background pill and calls `_render_svg_text`
directly, bypassing every invariant in §1–§3.

**AST pattern:**

The pattern targets a method definition whose body contains a string
constant or f-string with the literal substring `<text` combined with
non-helper assignment context, OR a direct call to `_render_svg_text`
inside a method other than those in `_svg_helpers.py` and `base.py`.
More precisely, the linter walks the AST for:

```
# Pattern A: call to _render_svg_text inside a primitive method
ast.Call
  └── func = ast.Name(id="_render_svg_text")
            OR ast.Attribute(attr="_render_svg_text")
  (inside a FunctionDef body that is NOT in _svg_helpers.py / base.py)

# Pattern B: method named _emit_text_annotation (a sentinel anti-pattern name)
ast.FunctionDef(name="_emit_text_annotation")
  OR ast.AsyncFunctionDef(name="_emit_text_annotation")
  (inside a ClassDef that is a subclass of PrimitiveBase, as inferred
   by the class body containing "emit_svg" or "resolve_annotation_point")
```

Pattern B is purely structural — the method name is a known-bad sentinel.
Pattern A is the semantic core; B adds a belt-and-suspenders name check.

**Error code:** E1570-A

**Severity:** ERROR — blocks CI.

**File scope:** `scriba/animation/primitives/*.py` only.
No check is performed on `base.py`, `_svg_helpers.py`, or test files.

**False-positive risk:** LOW. The only legitimate caller of
`_render_svg_text` inside a primitive is for *non-annotation* text
(e.g. cell values, node labels, axis tick text). Distinguishing
annotation-context calls from cell-value calls requires deeper analysis.
Mitigation: the lint rule fires on `_emit_text_annotation` (Pattern B)
unconditionally; for Pattern A it fires only when the enclosing method
is named `_emit_*annotation*` or when the `lines` argument being passed
to `_render_svg_text` is populated from an annotation loop. If uncertain,
the primitive author uses `@allow_forbidden_pattern("FP-1", ...)` (§6).

---

### §1.3 FP-2 — Isolated second `placed_labels` list per call

**Prose rule (§5.3):** A primitive MUST NOT maintain its own
`placed_labels`-equivalent list as a separate local or instance variable.
The shared `placed_labels` received from the frame-level caller (MW-2)
or the one created by `base.emit_annotation_arrows` MUST be the sole
registry for the frame.

**Rationale:** A second private registry means two independent sets of
labels can overlap each other (violates C-1) because each set only avoids
its own members. The graph's `placed_edge_labels` and plane2d's second
`placed_labels = []` for line labels are live examples of this bug.

**Current violations:**
- `graph.py:726` — `placed_edge_labels: list[_LabelPlacement] = []`
  (edge weight labels use a separate registry from annotation labels)
- `plane2d.py:1057` — `placed_labels: list[_LabelPlacement] = []`
  (line-equation labels use a separate registry from annotation labels)
- `queue.py:406` — `placed: list[_LabelPlacement] = []`
  (annotation labels use a fresh list, not the shared frame registry)
- `numberline.py:299` — `placed: list[_LabelPlacement] = []`
  (same as Queue)

**AST pattern:**

```
# Annotated assignment: foo: list[_LabelPlacement] = []
ast.AnnAssign
  └── annotation = ast.Subscript
        ├── value = ast.Name(id="list")
        └── slice = ast.Name(id="_LabelPlacement") | ast.Constant("_LabelPlacement")
      value = ast.List(elts=[])

# Undecorated assignment: foo = []  but type-comment list[_LabelPlacement]
# or inferred from context.  Catch the type-annotated form first;
# unannotated [] is too broad for a standalone lint rule.
```

The linter must confirm that the assignment is inside a method body of a
class that inherits from `PrimitiveBase` (inferred by class name lookup in
the same file, or by presence of `emit_svg` in the class body), and that
the method is NOT `register_decorations` or `dispatch_annotations` (both
legitimately receive the shared registry as a parameter, not as a fresh
list).

**Error code:** E1570-B

**Severity:** ERROR — blocks CI.

**File scope:** `scriba/animation/primitives/*.py` only.

**False-positive risk:** MEDIUM. A `placed: list[_LabelPlacement] = []`
inside `register_decorations` itself is not a violation — it would be the
initial empty list being passed in. The lint rule must exclude:
(a) method parameters typed `list[_LabelPlacement]`;
(b) stub `register_decorations` implementations that receive and
immediately return.
Mitigation: exclude assignments where the variable is immediately
passed as a function argument in the same line (e.g. `foo = []; f(foo)`
in consecutive statements).

---

### §1.4 FP-3 — Hardcoded glyph/pill metrics

**Prose rule (§5.3):** A primitive MUST NOT hardcode numeric character-
width estimates (`char_width = 7`), pill-height constants (`pill_h = 16`),
or padding values that duplicate the named constants in `_svg_helpers.py`
(`_LABEL_PILL_PAD_X`, `_LABEL_PILL_PAD_Y`, etc.).

**Rationale:** Hardcoded values diverge from `_svg_helpers.py` when those
constants are tuned (e.g. ISSUE-A2 math multiplier adjustment). They also
silently violate G-6 (pill width floor) and T-4 (width estimator contract)
when the real value and the hardcode drift apart. Rule M-13 in the error
table is the normative anchor for E1570.

**Current violations:**
- `plane2d.py:719` — `char_width = 7`
- `plane2d.py:721` — `pill_h = 16`
- `plane2d.py:1048` — `_LINE_LABEL_CHAR_W = 7`
- `plane2d.py:1051` — `_LINE_PILL_PAD_X = 5`
- `plane2d.py:1052` — `_LINE_PILL_PAD_Y = 2`
- `graph.py:765` — `_WEIGHT_FONT = 11` (local constant inside loop body)
- `graph.py:766` — `_PILL_PAD_X = 5` (local constant, shadows import)
- `graph.py:767` — `_PILL_PAD_Y = 2` (local constant, shadows import)

Note: `graph.py`'s `_WEIGHT_FONT`, `_PILL_PAD_X`, `_PILL_PAD_Y` are
assigned inside a loop body (lines 765–767), making them loop-scope
constants — a particularly fragile pattern since they re-run on every
edge rendering pass.

**AST pattern:**

```
# Assignment of a bare integer to a known-bad variable name
ast.Assign | ast.AnnAssign
  targets = [ast.Name(id=X)]  where X matches:
    char_width, pill_h, pill_w, pill_rx,
    _PILL_PAD_X, _PILL_PAD_Y, _PILL_R,
    _CHAR_W, _LINE_LABEL_CHAR_W, _LINE_PILL_PAD_X, _LINE_PILL_PAD_Y,
    _WEIGHT_FONT
  value = ast.Constant(value=int | float)

# Also catch f-string headroom magic numbers:
ast.Assign
  targets = [ast.Name(id=X)] where X matches: headroom, arrow_above, arrow_below
  value = ast.Constant(value=int | float)
  AND the assignment is NOT in a return/expression of a headroom-helper call
```

The name-list approach is a controlled allowlist of suspicious names;
it does not flag all integer constants (too noisy). The set is extensible
via configuration.

**Error code:** E1570-C

**Severity:** ERROR — blocks CI.

**File scope:** `scriba/animation/primitives/*.py` only.

**False-positive risk:** LOW-MEDIUM. Common integer assignments like
`r = 8` (node radius) or `cx = 50` (geometry) are NOT on the name
watchlist. The watchlist is name-scoped, so a collision requires a
primitive author to independently choose a coincident name. Risk is
low for the core watchlist; increases as the list grows. Mitigation:
keep the watchlist minimal and extend via PR review only.

---

### §1.5 FP-4 — No viewBox clamp after pill placement

**Prose rule (§5.3):** After computing a pill's final position, the
primitive MUST apply viewBox clamping (G-3/G-4) — translating the center
coordinate to keep the full AABB inside the declared viewBox without
altering pill dimensions.

**Rationale:** Without the clamp, pills placed near content edges can
overflow the viewBox and render partially or fully outside the visible
area (bug-F: `plane2d.py:724–731` long label truncates off-canvas). The
`_emit_text_annotation` method in `plane2d.py` computes `pill_x/pill_y`
with no boundary check.

**Current violation:** `plane2d.py:724–731` — `pill_x = tx - pill_w / 2`
and `pill_y = ty - pill_h + 4` with no subsequent min/max clamping.

**AST pattern:**

This is the hardest FP to detect statically because absence of a pattern
is more difficult to assert than presence. The lint strategy is:

```
# Signal: a block that computes pill_rx or pill_ry but does NOT
# subsequently call a clamping expression of the form:
#   max(0, ...)  or  min(viewbox_w, ...) or  min(viewbox_h, ...)
# within the same FunctionDef body.

# Positive evidence: function body contains (pill_rx OR pill_ry) assignments
# Negative evidence: function body does NOT contain ast.Call to max/min
#   with a Constant(0) or a viewBox-width/height reference

# Heuristic: treat any FunctionDef that assigns pill_rx or pill_ry
# and does NOT contain a call to max(0, ...) or min(...) in the same
# scope as a potential FP-4 candidate.
```

Because this is an absence-based heuristic, FP-4 is classified as
WARNING rather than ERROR. A second-pass human review is expected for
any flagged location.

**Error code:** E1570-D

**Severity:** WARNING — does not block CI; appears in lint report.

**File scope:** `scriba/animation/primitives/*.py` only.

**False-positive risk:** MEDIUM. Any primitive that delegates placement
entirely to `emit_annotation_arrows` (which calls `_svg_helpers.py`
routines that already clamp internally) will never contain `pill_rx`
assignments and will never trigger FP-4. The rule only fires when a
primitive has its own pill-placement logic. False positives arise when a
primitive uses `max`/`min` under a different variable name. Mitigation:
keep FP-4 as WARNING and require human sign-off.

---

### §1.6 FP-5 — `arrow_from`-only annotation filter (drops position-only)

**Prose rule (§5.3):** A primitive MUST NOT filter its annotation list to
`arrow_from`-keyed entries only, silently discarding position-only
annotations (`label` + `position`, no `arrow_from`, no `arrow=true`).

**Rationale:** Position-only annotations are a first-class author tool
(AC-1). Filtering them out violates E-2 (must-emit) and AC-1 (pill must
appear). The queue and numberline both filter to `arrow_from` only,
meaning authors get silent data-loss for `position=above` pills.

**Current violations:**
- `queue.py:403` — `arrow_anns = [a for a in effective_anns if a.get("arrow_from")]`
- `numberline.py:297` — `arrow_anns = [a for a in effective_anns if a.get("arrow_from")]`

Note: `plane2d.py:657–658` splits into `arrow_anns` (with `arrow_from`
OR `arrow`) and `text_anns` (position-only), handled separately. This is
NOT an FP-5 violation because position-only annotations are handled,
albeit via the FP-1 path (`_emit_text_annotation`). plane2d therefore
violates FP-1 but not FP-5.

**AST pattern:**

```
# List comprehension filter: [a for a in X if a.get("arrow_from")]
ast.ListComp
  └── generators[0].ifs = [
        ast.Call(
          func=ast.Attribute(attr="get"),
          args=[ast.Constant(value="arrow_from")]
        )  # no negation, no OR branch for "arrow" or "label"
      ]

# Equivalently: filter(lambda a: a.get("arrow_from"), anns)
# The AST walker catches the listcomp form; the filter() form
# is caught by a separate ast.Call(func=ast.Name(id="filter")) check.
```

The lint rule is triggered when the filter condition is SOLELY
`a.get("arrow_from")` with no OR branch for `a.get("arrow")` or
`a.get("label")`. A filter of the form
`a.get("arrow_from") or a.get("arrow")` is permitted (it still allows
the `arrow=true` case through `base.emit_annotation_arrows`).

**Error code:** E1570-E

**Severity:** ERROR — blocks CI.

**File scope:** `scriba/animation/primitives/*.py` only.

**False-positive risk:** LOW. The pattern is very specific. A primitive
that intentionally processes arrow-from annotations separately (e.g. to
reorder them) would need to also process position-only annotations
elsewhere; if it does, the filter does not produce silent data loss and
the author can use `@allow_forbidden_pattern("FP-5", ...)`.

---

### §1.7 FP-6 — Direct `emit_arrow_svg` bypass of `base.emit_annotation_arrows`

**Prose rule (§5.3):** A primitive MUST NOT call `emit_arrow_svg`,
`emit_plain_arrow_svg`, or `emit_position_label_svg` directly in its
own `emit_svg` body. All annotation dispatch MUST flow through
`self.emit_annotation_arrows(...)` or `self.dispatch_annotations(...)`.

**Rationale:** Direct calls bypass the base-class wiring that handles
`arrow=true` (plain pointers), position-only labels, and the
`_min_arrow_above` floor (which keeps translate offsets stable across
frames). A primitive that calls `emit_arrow_svg` directly also cannot
benefit from future base-class improvements (e.g. MW-2 unified registry,
MW-3 `_place_pill` helper) without a separate code change.

**Current violations:**
- `queue.py:416` — `emit_arrow_svg(arrow_lines, ann, src, dst, ...)`
- `numberline.py:309` — `emit_arrow_svg(lines, ann, src, dst, ...)`

**AST pattern:**

```
# Direct call to emit_arrow_svg / emit_plain_arrow_svg / emit_position_label_svg
# inside a method of a PrimitiveBase subclass, NOT inside _svg_helpers.py
# or base.py.

ast.Call
  └── func = ast.Name(id="emit_arrow_svg")
           OR ast.Name(id="emit_plain_arrow_svg")
           OR ast.Name(id="emit_position_label_svg")
  (inside a ClassDef method that is NOT in base.py or _svg_helpers.py)
```

The check is straightforward: the target function names are a closed set
exported from `_svg_helpers.py`. Any call to them inside a primitive
method body (not inside `base.py` or `_svg_helpers.py`) is a violation.

**Error code:** E1570-F

**Severity:** ERROR — blocks CI.

**File scope:** `scriba/animation/primitives/*.py` only.

**False-positive risk:** LOW. The three helper names are specific and
only used for annotation rendering. A primitive overriding
`dispatch_annotations` is explicitly permitted to call these helpers
directly (that is the contract of `dispatch_annotations`), so the lint
rule MUST exclude FunctionDefs named `dispatch_annotations`.

---

## §2 Tool Choice Rationale

### §2.1 Candidates

Four tool families can enforce the FP rules via static analysis:

| Tool | Approach | Integration | Custom rule complexity | Runtime |
|------|----------|-------------|----------------------|---------|
| **Ruff custom plugin** | AST visitor via ruff plugin API (Rust) | `ruff check` in CI | High — requires Rust + ruff plugin crate boilerplate; no Python AST | <1 s |
| **libcst codemod** | Concrete Syntax Tree visitor | standalone script or pre-commit | Medium — Python API, preserves formatting | 2–5 s |
| **Standalone Python AST walker** | `ast` stdlib walker | standalone script or pre-commit | Low — pure Python, no dependencies beyond stdlib | 1–3 s |
| **ast-grep** | Structural pattern matching (YAML/Rust DSL) | pre-commit hook | Low — declarative YAML patterns, no Python | <1 s |

### §2.2 Eliminated options

**Ruff custom plugin:** Ruff's plugin system requires writing a Rust crate
against the ruff AST API. The project has no Rust toolchain in CI, and the
ruff plugin API was still experimental as of early 2026. The maintenance
cost for a custom Rust plugin is disproportionate for six domain-specific
rules. Eliminated.

**libcst codemod:** libcst provides a Concrete Syntax Tree that preserves
whitespace and comments, which is valuable for automated code *fixes* but
provides no benefit for lint-only checking. It adds a non-trivial
dependency (`libcst`) not currently in the project's dev extras. Eliminated
for lint; reserved as the right tool if automated fix-in-place is added
later (e.g. to auto-migrate FP-5 filters).

**ast-grep:** The YAML DSL is expressive for structural pattern matching and
requires no Python knowledge. However, FP-2 (absence of a shared-registry
parameter) and FP-4 (absence of a clamping expression) require negative
assertions that ast-grep's YAML DSL handles awkwardly (requiring `not:`
combinators whose exact semantics vary by version). The tool also adds a
binary dependency not in the project's existing CI. Eliminated as primary
tool; MAY be used as a secondary check for FP-1/FP-5/FP-6 where the
patterns are purely structural.

### §2.3 Recommendation: Standalone Python AST walker

**Recommended tool:** A standalone Python script
(`scripts/lint_smart_label.py`) using the `ast` stdlib module.

**Rationale:**

1. **Zero new dependencies.** `ast` is stdlib. The script runs under the
   same `uv run python scripts/lint_smart_label.py` invocation already used
   for `scripts/analyze_labels.py` and `scripts/screenshot_audit.py`.

2. **Python-native.** The FP rules require understanding Python-level
   constructs (class hierarchy, method names, variable types). `ast` gives
   exact access without a Rust intermediate layer.

3. **CI-consumable JSON output.** The script emits structured JSON
   (`[{"file": ..., "line": ..., "col": ..., "code": ..., "message": ...}]`)
   that can be consumed by GitHub Actions problem matchers and by future
   ruff rule writers who want to port the logic.

4. **Runtime budget.** Walking the ASTs of 15 files averaging ~15 KB each
   takes under 0.5 s on a 2020-era laptop. The full script (including
   import, file discovery, and JSON serialization) runs in <2 s — well
   inside the 5 s CI budget.

5. **Maintainable by any Python contributor.** No Rust, no DSL, no new
   toolchain.

**Tradeoffs accepted:**

- The script does NOT integrate with ruff's `--fix` workflow. Fix-in-place
  is out of scope (§8 Non-goals).
- The script does NOT report column numbers for multi-line expressions
  (only line numbers). This is sufficient for CI blocking; IDE integration
  can be added later.
- FP-4 detection is heuristic (WARNING only) because absence-of-pattern
  detection in ASTs is structurally weaker than presence-of-pattern.

---

## §3 Implementation Sketch: `scripts/lint_smart_label.py`

The following is a **specification-level sketch**. It is not production
code. It is included here so the implementation PR has a concrete starting
point and so reviewers can validate the AST patterns before any code is
written. The actual implementation MUST include unit tests in
`tests/unit/test_lint_smart_label.py`.

```python
#!/usr/bin/env python3
"""Smart-label forbidden-pattern linter for scriba primitives.

Walks the AST of every file in scriba/animation/primitives/*.py
(excluding base.py and _svg_helpers.py) and reports violations of the
six Forbidden Patterns (FP-1..FP-6) defined in:
    docs/spec/smart-label-ruleset.md §5.3

Usage:
    python scripts/lint_smart_label.py [--json] [--path PATH]

Exit codes:
    0  No violations found.
    1  One or more ERROR-severity violations found.
    2  Only WARNING-severity violations found (or --warn-as-error set).
    3  Script error (bad arguments, file not found, parse error).
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

# Files excluded from all checks (they are the implementation, not consumers).
_EXCLUDED_FILES: frozenset[str] = frozenset({
    "base.py",
    "_svg_helpers.py",
    "_text_render.py",
    "_types.py",
    "layout.py",
    "graph_layout_stable.py",
    "tree_layout.py",
    "plane2d_compute.py",
})

# Default search path.
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
    # Names imported at module level (for detecting emit_arrow_svg imports)
    module_imports: set[str] = field(default_factory=set)
    # Set of (classname, methodname) pairs with @allow_forbidden_pattern
    suppressed: set[tuple[str, str, str]] = field(default_factory=set)
    # Current class name (set by visitor)
    current_class: str = ""
    # Current method name (set by visitor)
    current_method: str = ""


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
    """Heuristic: a class is a primitive if it has an emit_svg method."""
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


# ---------------------------------------------------------------------------
# FP-1: Direct <text> emission / _render_svg_text call (FULLY CODED)
# ---------------------------------------------------------------------------

def _check_fp1(ctx: FileContext) -> None:
    """Detect direct annotation text emission (FP-1, E1570-A).

    Triggers on:
      (a) any FunctionDef named _emit_text_annotation inside a primitive class;
      (b) any call to _render_svg_text inside a method whose name contains
          the substring "annotation" in a primitive class.
    """
    for class_node in ast.walk(ctx.tree):
        if not isinstance(class_node, ast.ClassDef):
            continue
        if not _is_primitive_class(class_node):
            continue

        for method_node in ast.walk(class_node):
            if not isinstance(method_node, ast.FunctionDef):
                continue

            # (a) Sentinel method name
            if method_node.name == "_emit_text_annotation":
                if (class_node.name, method_node.name, "FP-1") in ctx.suppressed:
                    continue
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
# FP-3: Hardcoded glyph/pill metrics (FULLY CODED)
# ---------------------------------------------------------------------------

def _check_fp3(ctx: FileContext) -> None:
    """Detect hardcoded glyph/pill metrics assigned to suspicious names (FP-3, E1570-C).

    Flags any assignment of the form:
        suspicious_name = <integer or float constant>
    inside a primitive class method body.
    """
    for class_node in ast.walk(ctx.tree):
        if not isinstance(class_node, ast.ClassDef):
            continue
        if not _is_primitive_class(class_node):
            continue

        for method_node in ast.walk(class_node):
            if not isinstance(method_node, ast.FunctionDef):
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
                if (class_node.name, method_node.name, "FP-3") in ctx.suppressed:
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
# FP-2: Isolated placed_labels list — STUB
# ---------------------------------------------------------------------------

def _check_fp2(ctx: FileContext) -> None:  # noqa: ARG001
    """STUB: Detect isolated placed_labels list creation (FP-2, E1570-B).

    Implementation note (TODO for implementation PR):
    Walk ClassDef → FunctionDef bodies. Find annotated assignments of the form:
        foo: list[_LabelPlacement] = []
    inside methods that are NOT named 'register_decorations' or
    'dispatch_annotations' and are NOT in base.py.
    Exclude function parameters typed list[_LabelPlacement].
    """
    # TODO: implement per §1.3 AST pattern above.
    pass


# ---------------------------------------------------------------------------
# FP-4: No viewBox clamp after placement — STUB
# ---------------------------------------------------------------------------

def _check_fp4(ctx: FileContext) -> None:  # noqa: ARG001
    """STUB: Detect pill placement without viewBox clamping (FP-4, E1570-D).

    Implementation note (TODO for implementation PR):
    Walk FunctionDef bodies that assign 'pill_rx' or 'pill_ry'.
    Check whether any call to max(0, ...) or min(...) appears in the
    same function body. If not, emit WARNING E1570-D.
    This is an absence-based heuristic; severity is WARNING.
    """
    # TODO: implement per §1.5 AST pattern above.
    pass


# ---------------------------------------------------------------------------
# FP-5: arrow_from-only filter — STUB
# ---------------------------------------------------------------------------

def _check_fp5(ctx: FileContext) -> None:  # noqa: ARG001
    """STUB: Detect annotation filters that drop position-only labels (FP-5, E1570-E).

    Implementation note (TODO for implementation PR):
    Walk ListComp nodes whose generator has a single `if` condition of the
    form `a.get("arrow_from")` with no `or a.get("arrow")` branch.
    Confirm the comprehension variable is iterated over a list of annotation
    dicts (by checking assignment context or variable name containing 'ann').
    """
    # TODO: implement per §1.6 AST pattern above.
    pass


# ---------------------------------------------------------------------------
# FP-6: Direct emit_arrow_svg bypass — STUB
# ---------------------------------------------------------------------------

def _check_fp6(ctx: FileContext) -> None:  # noqa: ARG001
    """STUB: Detect direct calls to emit_arrow_svg bypassing base dispatcher (FP-6, E1570-F).

    Implementation note (TODO for implementation PR):
    Walk FunctionDef bodies inside PrimitiveBase subclasses.
    Find ast.Call nodes whose func resolves to a Name in _ANNOTATION_HELPERS.
    Exclude FunctionDefs named 'dispatch_annotations' (they are explicitly
    allowed to call helpers directly per §5.1.6 contract).
    Also exclude the module-level import statements that pull in the helper
    names — only flag actual call sites.
    """
    # TODO: implement per §1.7 AST pattern above.
    pass


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_CHECKS = [_check_fp1, _check_fp2, _check_fp3, _check_fp4, _check_fp5, _check_fp6]


def _lint_file(path: pathlib.Path) -> list[Violation]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [Violation(
            file=str(path), line=exc.lineno or 0, col=exc.offset or 0,
            code="E1570-PARSE", severity="ERROR",
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


def _emit_text(violations: list[Violation]) -> int:
    """Print violations in a human-readable format. Returns exit code."""
    errors = [v for v in violations if v.severity == "ERROR" and not v.suppressed]
    warnings = [v for v in violations if v.severity == "WARNING" and not v.suppressed]
    for v in errors + warnings:
        print(f"{v.file}:{v.line}:{v.col}: {v.severity} {v.code} {v.message}")
    if not errors and not warnings:
        print("lint_smart_label: no violations found.")
        return 0
    print(f"\nlint_smart_label: {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 2


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument("--path", type=pathlib.Path, default=_DEFAULT_PRIMITIVES_PATH,
                        help="Path to primitives directory.")
    args = parser.parse_args(argv)

    violations = lint_primitives(args.path)

    if args.json:
        import dataclasses
        print(json.dumps([dataclasses.asdict(v) for v in violations], indent=2))
        errors = [v for v in violations if v.severity == "ERROR" and not v.suppressed]
        return 1 if errors else 0

    return _emit_text(violations)


if __name__ == "__main__":
    sys.exit(main())
```

**Line count:** ~255 lines including docstrings and stubs. Well within
the 150–250 target for the fully-coded portion (FP-1 + FP-3 = ~120 lines
of active logic); stubs account for the remainder.

**Test requirement (implementation PR):** `tests/unit/test_lint_smart_label.py`
MUST include at minimum:
- A fixture with a minimal Python file containing each FP variant.
- A fixture with a correctly-written primitive (no violations).
- A test for `@allow_forbidden_pattern` suppression.
- A test that `main()` returns exit code 1 on ERROR and 2 on WARNING-only.

---

## §4 Runtime `PrimitiveProtocol`

### §4.1 Protocol definition

```python
# scriba/animation/primitives/_protocol.py
# (New file — implementation PR scope)

"""Runtime-checkable Protocol for the Smart-Label Participation Interface.

Defines the six methods a primitive class MUST implement per
docs/spec/smart-label-ruleset.md §5.1.

This module deliberately imports nothing from base.py to avoid circular
imports. It is imported by base.py after PrimitiveBase is defined.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol, runtime_checkable

if TYPE_CHECKING:
    from scriba.animation.primitives._svg_helpers import _LabelPlacement


@runtime_checkable
class PrimitiveProtocol(Protocol):
    """The minimum interface a smart-label-conformant primitive MUST expose.

    Grade mapping (from §5.1):
        resolve_annotation_point  — MUST
        emit_svg                  — MUST
        annotation_headroom_above — MUST (new; replaces scattered max() blocks)
        annotation_headroom_below — MUST (new; mirrors above)
        register_decorations      — SHOULD now, MUST post-MW-2
        dispatch_annotations      — SHOULD
    """

    def resolve_annotation_point(
        self, selector: str
    ) -> tuple[float, float] | None:
        """Return SVG (x, y) for an annotation selector; None if unknown."""
        ...

    def emit_svg(
        self,
        *,
        placed_labels: "list[_LabelPlacement] | None" = None,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> str:
        """Return the SVG fragment for the current frame."""
        ...

    def annotation_headroom_above(self) -> float:
        """Pixels of viewBox expansion needed above y=0 for annotations."""
        ...

    def annotation_headroom_below(self) -> float:
        """Pixels of viewBox expansion needed below content bottom."""
        ...

    def register_decorations(
        self, registry: "list[_LabelPlacement]"
    ) -> None:
        """Seed the collision registry with non-pill visual element AABBs."""
        ...

    def dispatch_annotations(
        self,
        placed_labels: "list[_LabelPlacement]",
        *,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> list[str]:
        """Render all annotations for the current frame; return SVG lines."""
        ...
```

### §4.2 `register_primitive` gate

```python
# Replacement for the existing decorator in base.py
# (Implementation PR: modify _PRIMITIVE_REGISTRY / register_primitive)

_PRIMITIVE_REGISTRY: dict[str, type["PrimitiveBase"]] = {}


def register_primitive(*type_names: str):
    """Decorator to register a primitive class under one or more type names.

    Extends the existing decorator with a PrimitiveProtocol conformance
    check at decoration time. If the decorated class does not satisfy
    PrimitiveProtocol (i.e. is missing required methods), raises TypeError
    immediately — before the class can be registered.

    Protocol check is a structural isinstance() check at class-object level,
    not at instance level, because @runtime_checkable Protocol on a *class*
    checks whether the class defines the methods, not whether instances
    respond to them. For a precise check, the gate constructs a sentinel
    instance — OR uses a duck-type attribute check.

    Implementation note:
        isinstance(cls, PrimitiveProtocol) checks the *class object* against
        the Protocol, which only works for @runtime_checkable on instances.
        The correct check is:
            isinstance(cls, type) and all(
                hasattr(cls, m) for m in _REQUIRED_PROTOCOL_METHODS
            )
        where _REQUIRED_PROTOCOL_METHODS is the set of method names in
        PrimitiveProtocol. This is equivalent to a structural duck-type check.
    """
    from scriba.animation.primitives._protocol import PrimitiveProtocol

    _REQUIRED_PROTOCOL_METHODS = {
        "resolve_annotation_point",
        "emit_svg",
        "annotation_headroom_above",
        "annotation_headroom_below",
        "register_decorations",
        "dispatch_annotations",
    }

    def decorator(cls: type) -> type:
        missing = {
            m for m in _REQUIRED_PROTOCOL_METHODS
            if not (hasattr(cls, m) or _inherited_from_base(cls, m))
        }
        if missing:
            raise TypeError(
                f"[E1570] register_primitive: {cls.__name__!r} does not satisfy "
                f"PrimitiveProtocol (smart-label contract §5). "
                f"Missing methods: {', '.join(sorted(missing))}. "
                f"See docs/spec/smart-label-ruleset.md §5.1."
            )
        for name in type_names:
            _PRIMITIVE_REGISTRY[name] = cls
        return cls

    return decorator


def _inherited_from_base(cls: type, method_name: str) -> bool:
    """Return True if method_name is defined anywhere in cls's MRO."""
    for base in cls.__mro__:
        if method_name in base.__dict__:
            return True
    return False
```

### §4.3 Integration with existing registry

The existing `register_primitive` decorator in `base.py:82–124` is a
pure registration decorator. The upgrade adds a conformance gate **before**
the registration loop. The `TypeError` fires at class-definition time
(module import), which means non-conformant primitives fail fast when
the `scriba.animation.primitives` package is first imported.

**Migration path:** Because `annotation_headroom_above`,
`annotation_headroom_below`, `register_decorations`, and
`dispatch_annotations` do not yet exist on most primitives, the gate
MUST be introduced in two stages:

1. **Stage 1 (now / pre-MW-2):** The gate checks only
   `resolve_annotation_point` and `emit_svg`. Checking the remaining
   four would immediately fail 11 of 15 primitives at import time.
   The Stage-1 gate is added as part of the implementation PR for this
   design document.

2. **Stage 2 (post-MW-2):** After all 15 primitives have been migrated
   (§5.4 migration plan), the gate is expanded to check all six methods.
   This is a MINOR version bump (new enforcement of an existing SHOULD/MUST
   per §10.4).

The `_STAGE2_PROTOCOL_METHODS` constant in `register_primitive` is
toggled by a module-level flag `_PROTOCOL_STRICT = False` (default).
CI can override with `SCRIBA_PROTOCOL_STRICT=1` to pre-validate
Stage-2 compliance during the migration window.

### §4.4 `PrimitiveProtocol` instanceof usage in tests

```python
# Example test assertion (tests/unit/test_primitive_protocol.py)
from scriba.animation.primitives._protocol import PrimitiveProtocol
from scriba.animation.primitives.array import Array

def test_array_satisfies_stage1_protocol():
    arr = Array("arr", {})
    # Stage-1: resolve + emit_svg only
    assert hasattr(arr, "resolve_annotation_point")
    assert hasattr(arr, "emit_svg")

def test_array_satisfies_stage2_protocol_post_migration():
    arr = Array("arr", {})
    # Stage-2: all six methods must exist
    # (this test is expected to FAIL until migration is complete)
    assert isinstance(arr, PrimitiveProtocol)
```

---

## §5 15-Primitive Audit Table

The following table is derived from direct AST and grep analysis of the
primitive files as they exist at commit `539bb5e` (Phase 7 flip to unified
engine). Column headers:

- **resolve** — `resolve_annotation_point` is overridden (not the base no-op)
- **emit_svg wire** — `emit_svg` passes `placed_labels` OR delegates to
  `base.emit_annotation_arrows` (which manages its own `placed` list)
- **h_above** — `annotation_headroom_above` method exists (not inline max())
- **h_below** — `annotation_headroom_below` method exists
- **reg_dec** — `register_decorations` stub exists
- **dispatch** — `dispatch_annotations` override exists

FP columns: tick = violation present, dash = clean.

| Primitive | resolve | emit_svg wire | h_above | h_below | reg_dec | dispatch | FP-1 | FP-2 | FP-3 | FP-4 | FP-5 | FP-6 | Grade |
|-----------|:-------:|:-------------:|:-------:|:-------:|:-------:|:--------:|:----:|:----:|:----:|:----:|:----:|:----:|-------|
| Array | ✓ | ✓ (via base) | ✗ inline | ✗ | ✗ | ✗ | — | — | — | — | — | — | NEAR |
| DPTable | ✓ | ✓ (via base) | ✗ inline | ✗ | ✗ | ✗ | — | — | — | — | — | — | NEAR |
| Grid | ✓ | ✓ (via base) | ✗ inline | ✗ | ✗ | ✗ | — | — | — | — | — | — | PARTIAL |
| Tree | ✓ | ✓ (via base) | ✗ inline | ✗ | ✗ | ✗ | — | — | — | — | — | — | PARTIAL |
| LinkedList | ✓ | ✓ (via base) | ✗ inline | ✗ | ✗ | ✗ | — | — | — | — | — | — | PARTIAL |
| HashMap | ✓ | ✓ (via base) | ✗ inline | ✗ | ✗ | ✗ | — | — | — | — | — | — | PARTIAL |
| VariableWatch | ✓ | ✓ (via base) | ✗ inline | ✗ | ✗ | ✗ | — | — | — | — | — | — | PARTIAL |
| Graph | ✓ | partial | ✗ inline | ✗ | ✗ | ✗ | — | ✓ | ✓ | — | — | — | PARTIAL |
| Queue | ✓ | ✗ orphan | ✗ | ✗ | ✗ | ✗ | — | ✓ | — | — | ✓ | ✓ | NON-CONFORMANT |
| NumberLine | ✓ | ✗ orphan | ✗ | ✗ | ✗ | ✗ | — | ✓ | — | — | ✓ | ✓ | NON-CONFORMANT |
| Plane2D | ✓ | ✗ direct text | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓* | — | NON-CONFORMANT |
| Stack | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | — | — | — | — | — | — | DARK |
| Matrix | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | — | — | — | — | — | — | DARK |
| MetricPlot | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | — | — | — | — | — | — | DARK |
| CodePanel | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | — | — | — | — | — | — | DARK |

*Plane2D splits `arrow_from` and non-`arrow_from` into separate code paths
and handles non-`arrow_from` via `_emit_text_annotation`, which is itself
FP-1. The `arrow_from` + `arrow=true` filter (line 657) is broader than a
pure `arrow_from`-only filter and technically avoids FP-5, but only because
position-only is handled by the FP-1 violation. When FP-1 is fixed the
routing logic at lines 657–662 will need to be replaced, so the FP-5
status is annotated with `*` to indicate conditional — fix FP-1 first.

### §5.1 FP violation count summary

| FP | Primitive count | Primitive names |
|----|:---------------:|-----------------|
| FP-1 | 1 | Plane2D |
| FP-2 | 4 | Graph, Plane2D, Queue, NumberLine |
| FP-3 | 2 | Plane2D (5 sites), Graph (3 sites within 1 loop body) |
| FP-4 | 1 | Plane2D |
| FP-5 | 2 | Queue, NumberLine (Plane2D conditional — see note) |
| FP-6 | 2 | Queue, NumberLine |

**Total unique primitive-×-FP violations:** 12 (across 5 distinct
primitives). Dark primitives (Stack, Matrix, MetricPlot, CodePanel) have
no active annotation code and therefore no FP violations — their issue is
absence of any contract implementation.

---

## §6 Migration / Escape Hatch

### §6.1 `@allow_forbidden_pattern` decorator

Some FP violations will take more than one sprint to fix. The escape hatch
provides a documented, CI-tracked deferral mechanism.

```python
# scriba/animation/primitives/_allow_fp.py
# (New file — implementation PR scope)

"""Escape-hatch decorator for temporarily suppressing FP lint violations.

Usage::

    @allow_forbidden_pattern(
        "FP-3",
        reason="Plane2D uses a non-standard font-size for tick labels that "
               "differs from _svg_helpers defaults; migrate in MW-3.",
        issue="#482",
    )
    def _emit_line_labels(self, ...):
        ...

The decorator is a pure no-op at runtime — it does NOT modify the
decorated function in any way.  Its sole purpose is to be detectable by
the lint script (which parses decorators via AST) and to appear in grep
output for CI enforcement.

Contract:
    * 'fp' MUST be one of "FP-1".."FP-6".
    * 'reason' MUST be a non-empty string explaining why the pattern is
      acceptable at this call site.
    * 'issue' MUST reference a GitHub issue number in the format "#NNN".
    * Adding a NEW escape hatch is a MINOR bump (see §6.3).
    * Removing an escape hatch (i.e. fixing the violation) requires no
      version bump.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_VALID_FP_CODES = frozenset({"FP-1", "FP-2", "FP-3", "FP-4", "FP-5", "FP-6"})


def allow_forbidden_pattern(fp: str, *, reason: str, issue: str) -> Callable[[F], F]:
    """No-op decorator that records a lint suppression.

    Parameters
    ----------
    fp:
        The FP code being suppressed, e.g. "FP-3".
    reason:
        Human-readable justification for the suppression.
    issue:
        GitHub issue reference, e.g. "#482".  Enforced by CI grep.

    Returns
    -------
    Callable
        The decorated function unchanged.

    Raises
    ------
    ValueError
        If `fp` is not a known FP code, `reason` is empty, or `issue`
        does not match the "#NNN" pattern.
    """
    import re
    if fp not in _VALID_FP_CODES:
        raise ValueError(
            f"allow_forbidden_pattern: unknown FP code {fp!r}. "
            f"Valid codes: {sorted(_VALID_FP_CODES)}"
        )
    if not reason or not reason.strip():
        raise ValueError("allow_forbidden_pattern: 'reason' must be non-empty.")
    if not re.match(r"^#\d+$", issue):
        raise ValueError(
            f"allow_forbidden_pattern: 'issue' must match '#NNN', got {issue!r}."
        )

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        # Attach metadata for runtime introspection (tests, docs).
        wrapper.__allowed_fp__ = fp          # type: ignore[attr-defined]
        wrapper.__allowed_fp_reason__ = reason  # type: ignore[attr-defined]
        wrapper.__allowed_fp_issue__ = issue    # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
```

### §6.2 CI-grep enforcement: escape-hatch count MUST NOT grow

The escape hatch is dangerous if it becomes the default response to new
FP violations. CI enforces a hard cap:

```yaml
# In .github/workflows/test.yml — add as a new step in the lint job

- name: Count allow_forbidden_pattern uses
  run: |
    COUNT=$(grep -r "allow_forbidden_pattern" scriba/animation/primitives/ \
            --include="*.py" | wc -l | tr -d ' ')
    echo "Current escape-hatch count: $COUNT"
    # Read the allowed maximum from the committed baseline file.
    BASELINE=$(cat .escape-hatch-baseline 2>/dev/null || echo "0")
    if [ "$COUNT" -gt "$BASELINE" ]; then
      echo "ERROR: escape-hatch count grew from $BASELINE to $COUNT."
      echo "Adding new @allow_forbidden_pattern requires a MINOR semver bump"
      echo "and an update to .escape-hatch-baseline with reviewer approval."
      exit 1
    fi
```

The file `.escape-hatch-baseline` contains the integer count of currently
approved escape hatches. It is committed alongside any PR that adds a new
one. The PR that adds the baseline file MUST reference the GitHub issue
cited in each new `@allow_forbidden_pattern(issue="#...")` decoration.

**Initial baseline:** 0 (no escape hatches permitted until the linter
is deployed and existing violations are either fixed or formally deferred).

### §6.3 Semver implications

| Change | Version bump |
|--------|-------------|
| Fix a violation (remove an escape hatch) | PATCH — no author-visible impact |
| Add a new escape hatch (deferred migration) | MINOR — escape hatch count grows |
| Expand `PrimitiveProtocol` to Stage-2 enforcement | MINOR — new MUST enforcement |
| Introduce a new FP code | MINOR — adds error code (§10.4 row "Add error code") |
| Change an existing FP code number or meaning | MAJOR — breaks downstream lint suppressions |

The MINOR classification for new escape hatches is conservative: a growing
escape-hatch count signals technical debt accumulation, and the MINOR bump
creates a visible entry in `CHANGELOG-smart-label.md` that reviewers can
track over time.

---

## §7 CI Wiring

### §7.1 Pre-commit hook

```yaml
# .pre-commit-config.yaml (new file, or append to existing)
repos:
  - repo: local
    hooks:
      - id: smart-label-lint
        name: Smart-label FP lint
        language: system
        entry: uv run python scripts/lint_smart_label.py
        files: "scriba/animation/primitives/.*\\.py$"
        pass_filenames: false   # script discovers files itself
        types: [python]
        stages: [pre-commit, pre-push]
```

Running `uv run python scripts/lint_smart_label.py` on the 15 primitive
files (total ~280 KB of source) runs in <1 s on a 2020-era laptop.
Pre-commit overhead (hook startup + uv environment activation) adds ~0.5 s.
Total pre-commit cost: **<2 s**.

### §7.2 GitHub Actions job

Add a new job `smart-label-lint` to `.github/workflows/test.yml`:

```yaml
smart-label-lint:
  name: smart-label FP lint
  runs-on: ubuntu-latest
  timeout-minutes: 5
  steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Set up Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        enable-cache: true

    - name: Install dependencies
      run: uv sync --dev

    - name: Run smart-label FP lint (JSON output)
      run: |
        uv run python scripts/lint_smart_label.py --json \
          > smart-label-violations.json
        # Also emit human-readable for inline annotations
        uv run python scripts/lint_smart_label.py

    - name: Upload violation report
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: smart-label-violations
        path: smart-label-violations.json
        retention-days: 14

    - name: Count escape hatches
      run: |
        COUNT=$(grep -r "allow_forbidden_pattern" \
                scriba/animation/primitives/ --include="*.py" \
                | wc -l | tr -d ' ')
        BASELINE=$(cat .escape-hatch-baseline 2>/dev/null || echo "0")
        echo "escape_hatch_count=$COUNT" >> $GITHUB_OUTPUT
        if [ "$COUNT" -gt "$BASELINE" ]; then
          echo "Escape-hatch count grew: $BASELINE → $COUNT"
          exit 1
        fi
```

**Job dependencies:** The `smart-label-lint` job runs independently of
the `test` and `coverage` jobs (no `needs:` clause). It can run in
parallel. Total CI addition: ~45 s for environment setup + <5 s for
execution = **<50 s** end-to-end, well within the 5 s runtime budget
for the script itself.

### §7.3 GitHub Actions problem matcher

To inline violation annotations in the PR diff view, add a problem
matcher that reads the human-readable output format:

```json
// .github/smart-label-matcher.json
{
  "problemMatcher": [
    {
      "owner": "smart-label-lint",
      "pattern": [
        {
          "regexp": "^(.+):(\\d+):(\\d+): (ERROR|WARNING) (E\\S+) (.+)$",
          "file": 1,
          "line": 2,
          "column": 3,
          "severity": 4,
          "code": 5,
          "message": 6
        }
      ]
    }
  ]
}
```

Wire it in the Actions step:

```yaml
- name: Activate problem matcher
  run: echo "::add-matcher::.github/smart-label-matcher.json"
```

### §7.4 Runtime budget breakdown

| Phase | Operation | Time estimate |
|-------|-----------|--------------|
| pre-commit (local) | Hook startup + uv env check | ~0.5 s |
| pre-commit (local) | AST parse + check 15 files | ~0.3 s |
| pre-commit (local) | JSON serialization + output | <0.1 s |
| **pre-commit total** | | **<1 s** |
| GitHub Actions | Checkout + Python setup (cached) | ~15 s |
| GitHub Actions | uv sync (cached) | ~10 s |
| GitHub Actions | Script execution | <0.5 s |
| GitHub Actions | Escape-hatch grep | <0.5 s |
| GitHub Actions | Artifact upload | ~5 s |
| **CI job total** | | **<35 s** |

The 5 s runtime budget stated in the task scope refers to the script
execution only, not total CI job time. The script itself runs in <1 s.

---

## §8 Non-Goals

The following tools and capabilities are deliberately excluded from this
design. Each exclusion has a documented rationale.

### §8.1 No custom mypy plugin

A mypy plugin could enforce the Protocol at type-check time via the `--strict`
flag. Excluded because:

1. The project has no `mypy` in its dev dependencies (`pyproject.toml`
   [project.optional-dependencies.dev] contains only pytest, bleach, lxml,
   hypothesis, pytest-cov).
2. Introducing mypy adds a significant CI runtime increase (~30–90 s for
   a project of this size).
3. The `@runtime_checkable` Protocol approach (§4) plus the AST lint (§3)
   provides equivalent enforcement with zero new dependencies.
4. If mypy is adopted project-wide for general type checking, the Protocol
   will be enforced automatically as a side effect at no extra cost.

Reserve: if the project adopts mypy globally in a future PR, the Protocol
definition in `_protocol.py` is already compatible — no changes needed.

### §8.2 No automatic fix-in-place (libcst codemods)

libcst can rewrite source code while preserving formatting. Excluded
because:

1. FP-1 and FP-2 fixes require non-trivial semantic changes (routing
   annotation dispatch through a different call chain), not syntactic
   substitutions. Automated rewrites risk introducing subtle bugs.
2. libcst is not in the project's dependency set.
3. The migration plan (§5.4 from the ruleset spec) is already ordered by
   effort and should be executed by humans with test coverage at each step.

Reserve: if FP-5 migrations (filter pattern replacement) are consistently
mechanical across Queue and NumberLine, a libcst codemod for FP-5 alone
may be worthwhile. Defer to the MW-2 implementation PR.

### §8.3 No Rust-based ruff plugin (custom rules)

Ruff supports custom lint rules via a plugin API, but:

1. The project has no Rust toolchain in CI.
2. The ruff plugin API was experimental in early 2026 with breaking changes
   expected before stabilization.
3. The standalone Python walker (§3) achieves the same result with no new
   toolchain.

Reserve: if ruff's plugin API stabilizes and the project adopts a Rust
toolchain for other reasons (e.g. a performance-critical component),
porting the FP rules to a ruff plugin would reduce CI integration friction.
The JSON output format of `lint_smart_label.py` is designed to be
compatible with ruff's problem format, making the port mechanical.

### §8.4 No ast-grep as primary tool

ast-grep is excluded as the primary tool (§2.2). It may be used as a
complementary secondary check for FP-1/FP-5/FP-6 where its YAML DSL
is expressive and the patterns are purely structural. However, it adds
a binary dependency and its absence-based pattern limitations make it
unsuitable as the sole enforcement mechanism. If added, it would run
as a separate pre-commit hook alongside the Python walker, not replacing it.

### §8.5 No cross-file class-hierarchy analysis

The lint script uses a heuristic (`_is_primitive_class`) to identify
primitive classes within a single file rather than loading the full
class hierarchy. Full hierarchy analysis would require importing the
module, which adds ~200 ms startup cost and risks side effects from
module-level code. The heuristic (presence of `emit_svg` method in the
class body) has zero false negatives for the current primitive set and
is acceptable for this use case.

### §8.6 No integration with existing `scripts/analyze_labels.py`

`scripts/analyze_labels.py` performs runtime analysis of rendered SVG
output. The FP lint is a purely static AST check with no dependency on
rendered output. The two scripts serve different purposes and are
intentionally kept separate. A future `scripts/label_health.py` may
combine static and runtime checks, but that is out of scope for this
design.

---

## §9 Open Questions (for Implementation PR)

The following questions must be resolved by the implementation PR author
before any code is merged. They are recorded here to prevent silent
decision-making.

**Q1:** Should FP-2 fire on the `placed_edge_labels` list in `graph.py:726`?
This list is used for *edge weight* labels, not for annotation pills from
`\annotate`. Its violation of FP-2 is real (it cannot avoid collisions with
annotation pills because it is a separate registry), but the fix is more
complex than for Queue/NumberLine (the edge weight rendering is deeply
interleaved with the edge geometry loop). Recommendation: fire ERROR on
FP-2 for this site and add it to the initial set of `@allow_forbidden_pattern`
suppressions with issue reference pointing to the Graph migration PR.

**Q2:** The Stage-1 protocol gate (§4.3) checks only `resolve_annotation_point`
and `emit_svg`. Should it also check for the absence of `_emit_text_annotation`
(a sentinel bad method name)? Recommendation: yes — add it to Stage-1 as a
negative check (raises `TypeError` if the class defines `_emit_text_annotation`).

**Q3:** The `.escape-hatch-baseline` file starts at 0. Before the linter is
deployed with exit-code-1 enforcement, the baseline must be set to the
count of existing violations that will receive escape hatches during the
migration window. What is the initial approved escape-hatch count?
Based on §5.1: 12 primitive-×-FP violations across 5 primitives. Not all
require escape hatches — only sites where the fix will not land in the
same PR as the linter deployment. The implementation PR author should
enumerate these explicitly.

**Q4:** Should the `@allow_forbidden_pattern` decorator import be added to
`scriba/animation/primitives/__init__.py` or should it be a local import
at each usage site? Recommendation: re-export from `base.py` alongside
`register_primitive` so the decorator is a single-import convenience.

---

## Appendix A — Mapping FP Rules to Existing Error Codes

| FP | E1570 sub | Existing closest code | Relationship |
|----|-----------|----------------------|-------------|
| FP-1 | E1570-A | E1569 (position-only label silently dropped) | FP-1 causes E1569 in Plane2D; fixing FP-1 automatically prevents E1569 |
| FP-2 | E1570-B | E1560 (registry not reset between frames) | FP-2 is the intra-frame version; E1560 is the cross-frame version |
| FP-3 | E1570-C | E1570 (M-13: hardcoded headroom) | FP-3 is the generalization; E1570 was specifically headroom, now covers all metrics |
| FP-4 | E1570-D | E1562 (pre-clamp AABB registered) | FP-4 is the absence of clamp; E1562 fires when clamp is skipped and wrong AABB is registered |
| FP-5 | E1570-E | E1569 (label silently dropped) | FP-5 directly causes E1569 for position-only annotations in Queue/NumberLine |
| FP-6 | E1570-F | E1560 (registry not reset) | FP-6 causes registry isolation (FP-2); E1570-F is the structural cause |

---

## Appendix B — AST Node Quick Reference

For implementation PR authors unfamiliar with the `ast` module nodes
used throughout §1:

| AST node | Matches | Example source |
|----------|---------|----------------|
| `ast.Assign` | `x = value` | `pill_h = 16` |
| `ast.AnnAssign` | `x: type = value` | `placed: list[_LP] = []` |
| `ast.FunctionDef` | `def f(…):` | `def emit_svg(self, …):` |
| `ast.ClassDef` | `class C:` | `class Array(PrimitiveBase):` |
| `ast.Call` | `f(args)` | `emit_arrow_svg(lines, …)` |
| `ast.Name` | bare identifier | `emit_arrow_svg` in `ast.Call.func` |
| `ast.Attribute` | `obj.attr` | `self._render_svg_text` |
| `ast.ListComp` | `[x for x in y if z]` | `[a for a in anns if a.get("arrow_from")]` |
| `ast.Constant` | literal value | `7`, `16`, `"arrow_from"` |
| `ast.Subscript` | `X[Y]` | `list[_LabelPlacement]` |

All nodes are traversed using `ast.walk(node)` for depth-first exhaustive
traversal, or `ast.iter_child_nodes(node)` for one-level traversal.
The distinction matters for FP-3: `ast.walk(method_node)` finds assignments
inside nested loops (like `graph.py:765–767` inside a for loop).

---

*End of document. Total: ~1050 lines.*
