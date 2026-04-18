# 04 — Code Smells

Research date: 2026-04-18  
Scope: `scriba/` package (67 Python files, ~24 k LOC). Scripts, benchmarks, and tests noted separately but not counted against production targets.

---

## Summary (counts table)

| Smell | Count | Severity |
|---|---|---|
| Mutable default arguments | 0 | — clean |
| `from x import *` | 0 | — clean |
| Bare `except:` | 0 (production) | — clean |
| `except Exception:` without re-raise | 4 (all `# noqa: BLE001`) | MEDIUM |
| `Optional[...]` legacy syntax | 1 occurrence | LOW |
| `Union[...]` legacy syntax (not in `TYPE_CHECKING`) | 5 occurrences (2 files) | LOW |
| `type: ignore` suppressions | 5 | LOW |
| `noqa` suppressions (production only) | 8 | LOW |
| `Any` in container annotations (`dict[str, Any]` etc.) | 118 | HIGH |
| God functions (>50 lines) | 30 in `scriba/` | HIGH |
| God functions (>150 lines) | 14 | HIGH |
| Functions with >5 parameters | 33 | HIGH |
| Deep nesting (≥5 indent levels, 20+ spaces) | 1 742 lines | HIGH |
| Deepest nesting observed | 9 levels (`emitter.py:534`) | HIGH |
| Non-frozen `@dataclass` classes | 3 | MEDIUM |
| Module-level mutable state (`global` float) | 1 (`_cumulative_elapsed`) | MEDIUM |
| Abandoned module-level list (`_CAPTURED_PRINTS`) | 1 | MEDIUM |
| Deferred scriba intra-package imports (runtime) | ~25 call sites | MEDIUM |
| `_animation_error` re-imported per call site in `tree.py` | 7 repeated imports | MEDIUM |
| Magic numbers (raw numeric literals ≠ 0/1/-1) | 439 | MEDIUM |
| `print()` in production `scriba/` code | 0 | — clean |
| `logging.getLogger` used consistently | 9 files | — good |
| Missing return type annotation (public API) | 2 | LOW |
| `str.format()` used in non-template contexts | ~10 call sites | LOW |
| `f"..."` dominant | yes | — good |

---

## Mutable Defaults

**Status: clean.**

AST scan of all 67 `scriba/` files found zero functions with list (`[]`) or dict (`{}`) mutable defaults. The project uses `field(default_factory=...)` consistently where mutable collection defaults are needed on dataclasses (e.g. `SceneState` in `scriba/animation/scene.py:153-158`).

---

## Missing / Weak Type Hints

### `Any` overuse — HIGH

`dict[str, Any]`, `list[Any]`, and bare `: Any` / `-> Any` appear **118 times** across 15 files. The heaviest concentrations:

| File | Any-bearing annotations |
|---|---|
| `scriba/animation/scene.py` | 18 |
| `scriba/animation/starlark_worker.py` | 14 |
| `scriba/animation/primitives/plane2d.py` | 6 |
| `scriba/animation/primitives/grid.py` | 6 |
| `scriba/animation/renderer.py` | 5 |

Most of these are on the Starlark bridge (`caller_globals: dict[str, Any]`, `namespace: dict[str, Any]`) and SVG primitive dispatch (`params: dict[str, Any]`). These are legitimate escape hatches but should be narrowed where the shape is known.

Specific targets for tightening:

- `scriba/animation/renderer.py:153-155` — `_resolve_params(params: dict[str, Any], bindings: dict[str, Any]) -> dict[str, Any]`: `bindings` values are always JSON-serialisable scalars or lists; a `JsonValue` type alias would document this.
- `scriba/animation/scene.py:107` — `apply_params: list[dict[str, Any]] | None` on `ShapeTargetState` — the inner dict shape is fixed (keys `"cmd"`, `"params"`, etc.); a `TypedDict` would eliminate the `Any`.
- `scriba/animation/starlark_worker.py:447` — `_serialize_value(value: Any, ...) -> Any` — return type is always `str | int | float | bool | list | dict | None`; model with `type JsonValue = str | int | float | bool | list["JsonValue"] | dict[str, "JsonValue"] | None`.

### Public functions without return annotation — LOW

Only 2 public functions lack return annotations (AST scan):

- `scriba/animation/primitives/base.py:277` — `register_primitive`
- `scriba/animation/primitives/base.py:315` — `decorator` (the inner decorator returned by `register_primitive`)

Both are in the primitive registration machinery and should be annotated `-> None` / `-> Callable[..., type]`.

---

## God Functions (>50 lines)

30 functions in `scriba/` exceed the 50-line project rule. The 14 most egregious (>125 lines):

| Lines | File | Function | Start |
|---|---|---|---|
| 339 | `animation/primitives/base.py` | `emit_arrow_svg` | :985 |
| 298 | `animation/parser/grammar.py` | `_parse_substory` | :1112 |
| 298 | `animation/emitter.py` | `_build_inline_script` | :1126 |
| 259 | `animation/emitter.py` | `emit_interactive_html` | :865 |
| 253 | `animation/primitives/linkedlist.py` | `emit_svg` | :230 |
| 208 | `animation/primitives/graph_layout_stable.py` | `compute_stable_layout` | :176 |
| 201 | `animation/primitives/graph.py` | `emit_svg` | :660 |
| 195 | `core/pipeline.py` | `render` | :156 |
| 185 | `animation/differ.py` | `_diff_shape_states` | :48 |
| 182 | `animation/primitives/base.py` | `emit_plain_arrow_svg` | :801 |
| 175 | `animation/primitives/variablewatch.py` | `emit_svg` | :212 |
| 173 | `animation/starlark_worker.py` | `_evaluate` | :619 |
| 172 | `animation/primitives/queue.py` | `emit_svg` | :247 |
| 172 | `animation/parser/grammar.py` | `parse` | :66 |

`_build_inline_script` (298 lines) is purely a template string and is arguably not logic, but it is a single function emitting ~250 lines of inlined JavaScript; extracting named sub-builders would help readability and testability.

`emit_arrow_svg` at 339 lines handles multiple arrow geometries with deeply nested conditionals — the single largest refactoring target.

`_parse_substory` at 298 lines mirrors `parse` structurally; both contain a hand-rolled recursive-descent loop that accumulates list state and should be extracted into smaller `_parse_frame`, `_parse_command`, and `_parse_substory_header` helpers.

---

## Deep Nesting (>4 levels)

**1 742 lines** in `scriba/` reach 5 or more indent levels (20+ spaces). Deepest observed:

| Depth | File | Line | Context |
|---|---|---|---|
| 9 levels | `animation/emitter.py` | :534 | `_emit_frame_svg` apply-params dispatch |
| 8 levels | `animation/parser/grammar.py` | :183–188 | `parse` — frame accumulation inside nested `while` + `if` + `try` |
| 8 levels | `animation/parser/grammar.py` | :1042–1045 | `_parse_foreach_body` |
| 8 levels | `animation/differ.py` | :114 | `_diff_shape_states` — nested shape/target/state loops |
| 8 levels | `core/workers.py` | :149 | subprocess read loop |

The 9-level site in `emitter.py:534` sits inside a five-level chain: function → `for shape` → `for snap` → `for target_key` → `if ap` → `for params` → `if _accepts_suffix`. Early-return / guard-clause extraction would flatten this to 3 levels.

---

## Mutation Patterns

The project states an immutability preference. Compliance is mixed:

**Good — frozen dataclasses used widely.** `scriba/animation/parser/ast.py` is 100% frozen (`@dataclass(frozen=True, slots=True)` throughout). `FrameData`, `SubstoryData`, `Transition`, all AST node types, `AnnotationEntry`, and `FrameSnapshot` are frozen.

**Violations — non-frozen dataclasses:**

| File | Class | Issue |
|---|---|---|
| `scriba/animation/scene.py:144` | `SceneState` | Intentionally mutable state-machine accumulator; documented as such. Acceptable but should be noted in the refactor guide. |
| `scriba/animation/scene.py:100` | `ShapeTargetState` | Mutable DTO used as a value object. Should be `frozen=True`; currently mutated in-place by `_apply_command`. |
| `scriba/animation/primitives/base.py:207` | `_LabelPlacement` | `@dataclass(slots=True)` without `frozen=True`; used for short-lived collision-avoidance tracking. Low risk but inconsistent. |

**Module-level mutable global state:**

- `scriba/animation/starlark_worker.py:533` — `_cumulative_elapsed: float = 0.0` is mutated with `global` in two functions. This creates implicit shared state between test runs and concurrent callers. A `threading.local()` container (analogous to the existing `_step_local`) would make it concurrency-safe.
- `scriba/animation/starlark_worker.py:253` — `_CAPTURED_PRINTS: list[str] = []` is declared at module level but **never referenced again** in the file — `_evaluate` creates its own local `print_capture: list[str] = []` and passes it to `_make_print_fn`. The module-level list is dead code and should be removed.

**Instance-level mutation (61 call sites):** `self._states[target] = state`, `self._values[suffix] = value`, `self._labels[suffix] = label` in `primitives/base.py` represent controlled mutation inside value-object setters — acceptable given the rendering lifecycle, but all three could be eliminated if `BasePrimitive` adopted a copy-on-write or event-sourcing model.

---

## Logging vs Print

**Status: clean in production `scriba/` code.** `grep` finds zero `print()` calls in `scriba/`. The nine files that do I/O all use `logging.getLogger(__name__)` correctly.

`print()` is confined to:
- `render.py` (top-level CLI entry point — acceptable for CLI output)
- `benchmarks/` (intentional console output)
- `scripts/visual_regression/compare.py` (script tooling)
- `tests/` (test scaffolding / fixture strings)

No action needed in the library.

---

## Exception Handling

### Bare `except:` — clean
Zero bare `except:` clauses in `scriba/`. The one test hit (`test_security.py:71`) is a string literal fed to `_scan_ast`.

### `except Exception:` without re-raise — MEDIUM (4 sites)
All four are in production code and suppressed with `# noqa: BLE001`:

| File | Line | Context |
|---|---|---|
| `animation/emitter.py` | :256 | `_emit_frame_svg` — `set_value` best-effort; silent pass |
| `animation/emitter.py` | :492 | viewbox collector — best-effort; silent pass |
| `animation/parser/grammar.py` | :593 | error-recovery fallback — best-effort |
| `tex/renderer.py` | :254 | vendored KaTeX path probe — sets `_vendored_exists = False` |

The `tex/renderer.py:254` case is the weakest: it catches `Exception` just to determine whether a file path exists. `pathlib.Path.exists()` does not raise for missing files; the only exception thrown by `traversable_to_path(...).exists()` would be an OS or import error. A targeted `(OSError, ImportError)` clause would be more precise.

The two `emitter.py` cases swallow errors silently (`pass`). At minimum a `logger.debug("...", exc_info=True)` call would preserve debuggability without breaking the best-effort contract.

---

## Type Hint Modernization (Optional / Union → `X | None` / `X | Y`)

Python 3.10+ union syntax (`X | Y`, `X | None`) is the project standard. Three files still use legacy `typing` forms:

| File | Legacy form | Occurrences | Has `from __future__ import annotations` |
|---|---|---|---|
| `scriba/core/workers.py` | `Optional[subprocess.Popen]` | 1 | Yes |
| `scriba/animation/parser/ast.py` | `Union[int, str, ...]` | 5 | Yes |
| `scriba/animation/parser/grammar.py` | `Union` imported, used in annotation | 1 import | No |

`ast.py` uses `Union` only in module-level type aliases (`IndexExpr = Union[int, str, InterpolationRef]`). Because it has `from __future__ import annotations`, these aliases evaluate lazily — they can be rewritten as `int | str | InterpolationRef` without a runtime change.

`workers.py` imports `Optional` from `typing`; the single usage `Optional[subprocess.Popen]` should become `subprocess.Popen | None`.

`grammar.py` imports `Union` but does not appear to use it in any annotation (the import is present but the symbol does not appear in grammar.py's annotation sites after the import line). The import should be removed if unused, or the `Union` alias should be modernised.

---

## Frozen Dataclass Adoption

**Status: mostly good, three gaps.**

The pattern `@dataclass(frozen=True, slots=True)` is used on 35+ classes across the codebase. `scriba/animation/parser/ast.py` is a model example.

Gaps:

1. `ShapeTargetState` (`scene.py:100`) — `@dataclass` with no arguments. Used as a value object carrying per-frame state. It is mutated via direct attribute assignment inside `_apply_command`. Converting to frozen + returning a replaced copy would align it with the immutability rule.

2. `_LabelPlacement` (`primitives/base.py:207`) — `@dataclass(slots=True)`. Short-lived, private, low priority, but inconsistent.

3. `SceneState` (`scene.py:144`) — Intentionally mutable state machine; the docstring explicitly says "Mutable per-frame state accumulator." Freezing it is not appropriate here, but the class should carry a clear `# noqa: frozen-dataclass` or similar marker in the refactor guide to signal the deliberate exception.

---

## Magic Numbers

AST scan found **439 raw numeric literals** that are not `0`, `1`, `-1`, `2`, `0.0`, `1.0`, or `-1.0`. Top repeated values:

| Value | Occurrences | Likely meaning |
|---|---|---|
| `10.0` | 42 | Default axis range / tick size in `plane2d` and `numberline` |
| `4` | 38 | Padding / column count / tree fan-out |
| `20` | 32 | Font size / step limit / padding |
| `8` | 26 | Font size / column count |
| `14` | 18 | Font size (small label) |
| `12` | 17 | Font size (caption) |
| `16` | 17 | Padding constant (duplicates `_PADDING = 16` in `emitter.py`) |
| `1024` | 8 | Memory / buffer size |
| `1e-09` | 9 | Float epsilon |
| `0.01` | 10 | Convergence threshold |

`emitter.py` already defines `_PADDING = 16` and `_PRIMITIVE_GAP = 50`, but raw `16` and `50` still appear elsewhere in the same file.

In `plane2d.py` the default axis half-width `10.0` is scattered across at least six sites; `_DEFAULT_AXIS_HALF_WIDTH = 10.0` would consolidate them.

`1e-09` (epsilon for floating-point comparisons) appears 9 times across layout code. A single `_FLOAT_EPSILON = 1e-9` in a shared constants module would suffice.

---

## TODO / FIXME Triage

A case-insensitive scan for `TODO`, `FIXME`, `XXX`, and `HACK` found **zero occurrences** in `scriba/` Python files. The project is clean of deferred-work markers.

For reference, `type: ignore` suppressions (5) and `noqa` suppressions (8) in production files all carry justification comments:

- `# noqa: BLE001` — broad exception catch, best-effort context
- `# noqa: S102` — intentional `exec` in sandboxed Starlark evaluator
- `# noqa: F401` — deliberate re-export or side-effect import
- `# type: ignore[assignment]` — `tuple(...)` narrowing limitation in mypy
- `# type: ignore[attr-defined]` — optional renderer protocol duck-type

All are justified and low-risk.

---

## Circular Import Workarounds

**59 deferred `import` / `from` statements** appear inside function or method bodies in `scriba/`. They fall into three categories:

### Category A — `TYPE_CHECKING` guard (correct pattern, 10 sites)
`differ.py`, `lexer.py`, `context.py`, `base.py`, `errors.py`, `tex/__init__.py` all use:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from scriba.animation.emitter import FrameData
```
These are invisible at runtime and are the right solution. No action needed.

### Category B — Repeated `_animation_error` import per method (noisy, 13 sites in `tree.py` + `graph.py`)
`tree.py` has **7 identical** `from scriba.animation.errors import _animation_error` statements, one at the top of each method that can raise. `graph.py` has 6. This pattern was introduced to break an import cycle between `primitives/` and `errors.py`. The import is cheap (module cached after first load) but visually noisy. The cycle can be broken cleanly by:
- Moving `_animation_error` to `scriba.animation.primitives.errors` (a new thin module), or
- Importing it once at module-top using `TYPE_CHECKING` + a `TYPE_CHECKING`-safe forward-reference pattern.

### Category C — True deferred runtime imports (structural smell, ~12 sites)
| File | Deferred import | Reason |
|---|---|---|
| `animation/renderer.py:157,180` | `InterpolationRef` from `parser.ast` | Repeated twice in the same file; should be top-level |
| `animation/renderer.py:686` | `detect_diagram_blocks` from `detector` | Optional feature; lazy-load acceptable |
| `animation/parser/grammar.py:58` | `get_primitive_registry` from `primitives` | Breaks `grammar ↔ primitives` cycle |
| `animation/primitives/base.py:412` | `_animation_error, _suggest_closest` from `errors` | Same cycle as tree/graph |
| `animation/primitives/graph_layout_stable.py:369` | imports from `graph` | Mutual layout ↔ graph cycle |
| `tex/renderer.py:83` | `_emit_warning` from `animation.errors` | Cross-package tex ↔ animation cycle |
| `tex/parser/escape.py:42` | `import re` | Unnecessary deferral; `re` is stdlib, import cost is zero |

`animation/renderer.py:157,180` imports `InterpolationRef` inside two separate functions in the same file. This is straightforwardly wrong — moving it to the top level (or wrapping in `TYPE_CHECKING`) fixes it.

`tex/parser/escape.py:42` defers `import re` for no discernible reason; `re` has no import cost and no circularity risk.

---

## Refactor Punch-List (prioritized)

### P1 — HIGH, immediate correctness / maintainability risk

1. **Flatten `_emit_frame_svg` 9-level nesting** (`emitter.py:496–643`)  
   Extract `_apply_param_list(prim, params_list, suffix, accepts_suffix)` helper. Reduces max nesting to 4 levels. File: `scriba/animation/emitter.py`.

2. **Split `emit_arrow_svg` (339 lines)** (`primitives/base.py:985`)  
   Extract `_emit_straight_arrow`, `_emit_curved_arrow`, `_emit_double_arrow` — each is an independent geometry branch. File: `scriba/animation/primitives/base.py`.

3. **Split `parse` and `_parse_substory` (172 + 298 lines)** (`grammar.py`)  
   Extract `_parse_frame_body`, `_parse_command_dispatch`, `_parse_substory_header`. The two functions share 90% structural identity — factor the common accumulation loop. File: `scriba/animation/parser/grammar.py`.

4. **Narrow `dict[str, Any]` on hot paths**  
   Define `JsonValue = str | int | float | bool | list["JsonValue"] | dict[str, "JsonValue"] | None` in `scriba/animation/types.py`. Replace the 14 usages in `starlark_worker.py` and 18 in `scene.py`. Removes the largest single cluster of `Any` abuse.

5. **Fix `ShapeTargetState` — make frozen**  
   Change `@dataclass` to `@dataclass(frozen=True)` and update the two mutation sites in `scene.py` to use `dataclasses.replace(...)`. File: `scriba/animation/scene.py`.

### P2 — MEDIUM, code quality / latent bugs

6. **Remove dead `_CAPTURED_PRINTS` module-level list** (`starlark_worker.py:253`)  
   It is never read or written after the assignment. One-line deletion.

7. **Convert `_cumulative_elapsed` to `threading.local()`** (`starlark_worker.py:533`)  
   Currently a bare `global float` mutated with `global` keyword. Wrapping in `threading.local()` (like `_step_local`) eliminates the inter-thread shared state risk under concurrent rendering.

8. **Consolidate `_animation_error` imports in `tree.py` / `graph.py`**  
   Replace 13 repeated per-method deferred imports with a single module-level import. Either move `_animation_error` to a lower-level module, or accept the top-level import and annotate the deliberate cycle in a `# scriba: import-cycle-accepted` comment.

9. **Add named constants for recurring magic numbers**  
   Priority targets:
   - `_DEFAULT_AXIS_HALF_WIDTH = 10.0` in `primitives/plane2d.py`
   - `_FLOAT_EPSILON = 1e-9` in layout / plane2d code
   - `_LABEL_FONT_SIZE_SMALL = 14`, `_LABEL_FONT_SIZE_CAPTION = 12` in `primitives/base.py`

10. **Add `logger.debug(..., exc_info=True)` to silent `except Exception: pass` sites** (`emitter.py:256,492`)  
    Preserves best-effort semantics but makes failures observable under `DEBUG` logging.

11. **Modernise legacy typing imports**  
    - `workers.py`: `Optional[subprocess.Popen]` → `subprocess.Popen | None`
    - `ast.py`: all five `Union[...]` aliases → `|` syntax
    - Remove the unused `Union` import from `grammar.py` if confirmed unused in annotations.

### P3 — LOW, polish

12. **Remove `import re` deferral in `escape.py:42`** — move to module top.

13. **Move `InterpolationRef` imports in `renderer.py:157,180`** to module top (or `TYPE_CHECKING` guard).

14. **Annotate `register_primitive` and `decorator` return types** (`primitives/base.py:277,315`).

15. **Document `SceneState` as the intentional mutable exception** to the immutability rule, and mark `_LabelPlacement` with `frozen=True`.
