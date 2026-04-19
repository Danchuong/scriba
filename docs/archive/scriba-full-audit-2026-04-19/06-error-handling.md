# Error Handling & UX Audit — Scriba

**Date:** 2026-04-19  
**Auditor:** claude-sonnet-4-6  
**Scope:** All error paths, the E1xxx error code system, user-facing messages  
**Files examined:** `scriba/core/errors.py`, `scriba/animation/errors.py`, `scriba/core/warnings.py`, `scriba/core/pipeline.py`, `scriba/animation/renderer.py`, `scriba/animation/scene.py`, `scriba/animation/_frame_renderer.py`, `scriba/animation/starlark_worker.py`, `scriba/animation/starlark_host.py`, `scriba/animation/parser/grammar.py`, all `primitives/*.py`, `scriba/core/workers.py`, `scriba/tex/renderer.py`

---

## 1. Score: 7.5 / 10

**Rationale:** The foundation is genuinely strong. Scriba has a Rust-style hierarchical exception system (`ScribaError` → `AnimationError` → specific subclasses), a comprehensive machine-readable E-code catalog, source-caret pointers on parse errors, fuzzy-match "did you mean" suggestions on typos, and a structured RFC-002 warning channel that routes silent fixups into `Document.warnings`. What costs points is: (a) E1199 is raised but never catalogued; (b) E1157/E1158 are spec'd in `ruleset.md` but missing from the live `ERROR_CATALOG`; (c) one live `E1103` raise site uses the deprecated mega-bucket instead of the specific E14xx code; (d) five `except Exception: pass` blocks swallow detail in best-effort paths; (e) some multi-condition codes have ambiguous catalog descriptions that mix two unrelated conditions under one number.

---

## 2. Complete E1xxx Code Inventory

### Parse / Detection Errors (E1001–E1049)

| Code | File:line | Meaning | Example message | Severity |
|------|-----------|---------|-----------------|----------|
| E1001 | `parser/lexer.py:305,361,421` | Unclosed `\begin{animation}` or unbalanced braces | `[E1001] at line 7, col 1: unclosed \begin{animation}` | ERROR |
| E1003 | `animation/errors.py:442` | Nested `\begin{animation}` detected | `[E1003]: nested \begin{animation}` | ERROR |
| E1004 | `parser/grammar.py:508` | Unknown environment/substory option key | `[E1004] at line 2, col 4: unknown option key 'ids'` | ERROR |
| E1005 | `animation/emitter.py:177` | Invalid option or parameter value | `[E1005]: duplicate frame label 'step1'` | ERROR |
| E1006 | `parser/grammar.py:352,381` | Unknown backslash command | `[E1006] at line 5, col 1: unknown command '\foobar'` | ERROR |
| E1007 | `parser/lexer.py:279`, `detector.py:102` | Stray `\end{animation}` or missing opening brace | `[E1007] at line 4, col 9: expected '{' after '\shape'` | ERROR |
| E1009 | `parser/selectors.py:322` | Selector parse error (general) | `[E1009]: malformed selector syntax` | ERROR |
| E1010 | `parser/selectors.py` | Selector: expected number/identifier/char | `[E1010]: unexpected character at position 3` | ERROR |
| E1011 | `parser/selectors.py` | Unterminated string literal in selector | `[E1011]: unterminated string literal` | ERROR |
| E1012 | `parser/selectors.py` | Unexpected token kind | `[E1012]: unexpected token` | ERROR |
| E1013 | `parser/grammar.py:85` | Source exceeds 1MB | `[E1013]: source exceeds maximum size of 1MB` | ERROR |

### Uniqueness Errors (E1017–E1019)

| Code | File:line | Meaning | Example message | Severity |
|------|-----------|---------|-----------------|----------|
| E1017 | `animation/uniqueness.py:67` | Shape id invalid charset/too long | `[E1017]: shape id 'my-shape' contains invalid characters` | ERROR |
| E1018 | `animation/uniqueness.py:97` | Duplicate shape id within animation scope | `[E1018]: duplicate shape id 'arr'` | ERROR |
| E1019 | `animation/uniqueness.py:127` | Duplicate animation id across document | `[E1019]: duplicate animation id 'scene1'` | WARNING (in `Document.warnings`) |

### Diagram / Semantic Errors (E1050–E1057)

| Code | File:line | Meaning | Example message | Severity |
|------|-----------|---------|-----------------|----------|
| E1050 | `animation/renderer.py:716` | `\step` in diagram environment | `[E1050]: \step is not allowed in diagram` | ERROR |
| E1051 | `parser/grammar.py:250` | `\shape` after first `\step` | `[E1051]: \shape must appear before the first \step` | ERROR |
| E1052 | `parser/_grammar_tokens.py:445` | Trailing text after `\step` | `[E1052]: trailing text after \step` | ERROR |
| E1053 | `parser/grammar.py:292` | `\highlight` in animation prelude | `[E1053]: \highlight is not allowed in the prelude` | ERROR |
| E1054 | `animation/renderer.py:704` | `\narrate` in diagram | `[E1054]: \narrate is not allowed in a diagram` | ERROR |
| E1055 | `parser/grammar.py:280` | Duplicate `\narrate` in same step | `[E1055]: duplicate \narrate in same step` | ERROR |
| E1056 | `parser/grammar.py:271` | `\narrate` outside `\step` | `[E1056]: \narrate must be inside a \step block` | ERROR |
| E1057 | `animation/errors.py:155` (catalog) | Mutation command in substory prelude | `[E1057]: \highlight not allowed in substory prelude` | ERROR |

### Parse / Type Errors (E1100–E1116)

| Code | File:line | Meaning | Example message | Severity |
|------|-----------|---------|-----------------|----------|
| E1100 | `animation/errors.py:521` (class) | General parse failure | `[E1100]: parse failure` | ERROR |
| E1102 | `animation/renderer.py:205`, `parser/grammar.py:555,573` | Unknown primitive type | `[E1102]: unknown primitive type 'Heap'; did you mean 'HashMap'?` | ERROR |
| E1103 | `animation/scene.py:668` | DEPRECATED mega-bucket (annotation cap) | `[E1103]: annotation count 51 exceeds maximum of 50 per frame` | ERROR |
| E1109 | `parser/_grammar_commands.py:102,145` | Invalid `\recolor` state | `[E1109]: unknown state 'active'; valid: idle, current, done, ...` | ERROR |
| E1112 | `parser/_grammar_commands.py:224` | Unknown annotation position | `[E1112]: unknown position 'center'; valid: above, below, ...` | ERROR |
| E1113 | `parser/_grammar_commands.py:122,173,183,234` | Invalid annotation color | `[E1113]: unknown color 'blue'; valid: info, warn, good, ...` | ERROR |
| E1114 | `animation/primitives/base.py:238` | Unknown shape kwarg | `[E1114]: unknown Array parameter 'sz'; did you mean 'size'?` | ERROR |
| E1115 | `animation/_frame_renderer.py:306,322` | Selector matches no addressable part (warning) | `[E1115] selector 'arr.cell[99]' does not match any addressable part of 'arr'` | WARNING (silent drop) |
| E1116 | `animation/renderer.py:371`, `scene.py:639,654,721` | Mutation command references undeclared shape | `[E1116]: \apply references undeclared shape 'arr'` | ERROR |

### Render Errors (E1200)

| Code | File:line | Meaning | Example message | Severity |
|------|-----------|---------|-----------------|----------|
| E1200 | `tex/renderer.py:96,109` | KaTeX inline error in rendered output | `[E1200]: KaTeX parse error: Unknown command '\foo'` | WARNING (in collector) |

### Starlark Sandbox Errors (E1150–E1156)

| Code | File:line | Meaning | Example message | Severity |
|------|-----------|---------|-----------------|----------|
| E1150 | `starlark_worker.py:705,882,932` | Starlark parse/syntax error | `[E1150]: SyntaxError: unexpected token` | ERROR |
| E1151 | `starlark_worker.py:758,778` | Starlark runtime evaluation failure | `[E1151]: Starlark evaluation error: ZeroDivisionError` | ERROR |
| E1152 | `starlark_host.py:235`, `starlark_worker.py:563,615,694` | Starlark timed out | `[E1152]: cumulative Starlark wall-clock budget exceeded (6.2s > 5s)` | ERROR |
| E1153 | `starlark_worker.py:716` | Step count exceeded | `[E1153]: step count limit exceeded` | ERROR |
| E1154 | `starlark_worker.py:307,315,329,336,350,357,375,383,645` | Forbidden construct | `[E1154]: forbidden construct 'import' at line 3` | ERROR |
| E1155 | `starlark_worker.py:728,839` | Memory limit exceeded | `[E1155]: peak memory 68MB exceeds 64MB limit` | ERROR |
| E1156 | `starlark_worker.py:916` | `eval_raw` removed | `[E1156]: eval_raw has been removed; use \compute{...} instead` | ERROR |

### Foreach Errors (E1170–E1173)

| Code | File:line | Meaning | Example message | Severity |
|------|-----------|---------|-----------------|----------|
| E1170 | `parser/_grammar_foreach.py:68`, `scene.py:345` | `\foreach` nesting depth > 3 | `[E1170]: \foreach nesting depth exceeds maximum (3)` | ERROR |
| E1171 | `parser/_grammar_foreach.py:137` | `\foreach` with empty body | `[E1171]: \foreach body must contain at least one command` | ERROR |
| E1172 | `parser/_grammar_foreach.py:175,197`, `grammar.py:321`, `_grammar_substory.py:334` | Unclosed `\foreach` or forbidden command | `[E1172]: unclosed \foreach` | ERROR |
| E1173 | `scene.py:373,385,392,399,412,418,425,436`, `_grammar_foreach.py:93`, `starlark_worker.py:279,286` | Iterable validation failure | `[E1173]: \foreach iterable exceeds maximum length` | ERROR |

### Frame / Cursor Errors (E1180–E1182, E1199)

| Code | File:line | Meaning | Example message | Severity |
|------|-----------|---------|-----------------|----------|
| E1180 | `parser/_grammar_commands.py:268,277` | `\cursor` missing targets, or >30 frames warning | `[E1180]: \cursor requires at least one target` | WARNING/ERROR |
| E1181 | `parser/_grammar_commands.py:288`, `animation/errors.py:574` | >100 frames hard limit, or `\cursor` missing index | `[E1181]: animation has 105 frames, exceeding the 100-frame limit` | ERROR |
| E1182 | `parser/_grammar_commands.py:318,328` | Invalid `\cursor` state value | `[E1182]: invalid curr_state 'selected'` | ERROR |
| **E1199** | `core/workers.py:294` | **Worker subprocess terminated without response** | `[E1199]: worker 'katex' closed unexpectedly (empty response)` | ERROR |

> **Note:** E1199 is raised in `core/workers.py` but is **absent from `ERROR_CATALOG`** in `animation/errors.py`. The code range `E1183–E1199` is documented as "reserved" in `environments.md` but E1199 is live in production. This is a catalog gap.

### Substory Errors (E1360–E1368)

| Code | File:line | Meaning | Example message | Severity |
|------|-----------|---------|-----------------|----------|
| E1360 | `parser/_grammar_substory.py` | Substory nesting depth > 3 | `[E1360]: substory nesting depth exceeds maximum (3)` | ERROR |
| E1361 | `parser/_grammar_substory.py` | Unclosed `\substory` | `[E1361]: unclosed \substory` | ERROR |
| E1362 | `parser/grammar.py:332` | `\substory` outside `\step` | `[E1362]: \substory must be inside a \step block` | ERROR |
| E1365 | `parser/grammar.py:343` | `\endsubstory` without matching `\substory` | `[E1365]: \endsubstory without matching \substory` | ERROR |
| E1366 | `animation/errors.py:548` (class) | Empty substory (zero `\step` inside) | `[E1366] \substory at line 12, col 1 contains no \step` | WARNING (UserWarning) |
| E1368 | `parser/_grammar_substory.py` | Text on same line as `\substory`/`\endsubstory` | `[E1368]: non-whitespace text on same line as \substory` | ERROR |

### Primitive Parameter Errors (E1400–E1474)

| Code | File:line | Meaning | Severity |
|------|-----------|---------|---------|
| E1400 | `primitives/array.py:105` | Array: missing `size`/`n` | ERROR |
| E1401 | `primitives/array.py:112,117` | Array: `size` out of range 1..10000 | ERROR |
| E1402 | `primitives/array.py:126` | Array: `data` length != `size` | ERROR |
| E1410 | `primitives/grid.py:120` | Grid: missing `rows`/`cols` | ERROR |
| E1411 | `primitives/grid.py:129,134,139,144` | Grid: `rows`/`cols` out of range 1..500 | ERROR |
| E1412 | `primitives/grid.py:52,66` | Grid: `data` length != `rows*cols` | ERROR |
| E1420 | `primitives/matrix.py:157` | Matrix: missing `rows`/`cols` | ERROR |
| E1421 | `primitives/matrix.py:165,170` | Matrix: `rows`/`cols` must be positive int | ERROR |
| E1422 | `primitives/matrix.py:195` | Matrix: `data` length != `rows*cols` | ERROR |
| E1425 | `primitives/matrix.py:175`, `primitives/dptable.py:145` | Matrix/DPTable: cell cap (250k) exceeded | ERROR |
| E1426 | `primitives/dptable.py:137` | DPTable: missing `n` or `rows`/`cols` | ERROR |
| E1427 | `primitives/dptable.py:104` | DPTable: `n` not positive int | ERROR |
| E1428 | `primitives/dptable.py:120,128` | DPTable: `rows`/`cols` not positive int | ERROR |
| E1429 | `primitives/dptable.py:156` | DPTable: `data` length mismatch | ERROR |
| E1430 | `primitives/tree.py:152` | Tree: missing `root` | ERROR |
| E1431 | `primitives/tree.py:185` | Tree (segtree): missing `data` | ERROR |
| E1432 | `primitives/tree.py:210` | Tree (sparse_segtree): missing `range_lo`/`range_hi` | ERROR |
| E1433 | `primitives/tree.py:351` | Tree: remove non-leaf without `cascade=true` | ERROR |
| E1434 | `primitives/tree.py:344` | Tree: remove root without `cascade=true` | ERROR |
| E1435 | `primitives/tree.py:264,419,424,431` | Tree: reparent creates cycle | ERROR |
| E1436 | `primitives/tree.py:239,255,296,304,335,409,414,441` | Tree: referenced node does not exist | ERROR |
| E1437 | `primitives/plane2d.py:400,406,414,420,428,434,442,448,456,462` | Plane2D: remove index out of range | ERROR |
| E1440 | `primitives/queue.py:119` | Queue: `capacity` not positive int | ERROR |
| E1441 | `primitives/stack.py:97` | Stack: `max_visible` not positive int | ERROR |
| E1450 | `primitives/hashmap.py:87` | HashMap: missing `capacity` | ERROR |
| E1451 | `primitives/hashmap.py:94` | HashMap: `capacity` not positive int | ERROR |
| E1452 | `primitives/numberline.py:89` | NumberLine: missing `domain` | ERROR |
| E1453 | `primitives/numberline.py:95` | NumberLine: `domain` not 2-element list | ERROR |
| E1454 | `primitives/numberline.py:118` | NumberLine: `ticks` > 1000 | ERROR |
| E1460 | `primitives/plane2d.py:148,150` | Plane2D: degenerate viewport | ERROR |
| E1461 | `primitives/plane2d.py:278,281` | Plane2D: degenerate/out-of-viewport line | WARNING (logger + collector) |
| E1462 | `primitives/plane2d.py:323,326,339,342` | Plane2D: polygon not closed (auto-closed) | WARNING (logger + collector) |
| E1463 | `primitives/plane2d.py:256,259` | Plane2D: point outside viewport | WARNING (collector) |
| E1465 | `primitives/plane2d.py:157` | Plane2D: invalid `aspect` value | ERROR |
| E1466 | `primitives/plane2d.py:237` | Plane2D: element cap (500) reached | ERROR |
| E1470 | `primitives/graph.py:324` | Graph: missing `nodes` list | ERROR |
| E1471 | `primitives/graph.py:449,457,500,505` | Graph `add_edge`: unknown endpoint | ERROR |
| E1472 | `primitives/graph.py:466,517` | Graph `remove_edge`: edge does not exist | ERROR |
| E1473 | `primitives/graph.py:475,532,538` | Graph `set_weight`: edge does not exist | ERROR |
| E1474 | `primitives/graph.py:356,361` | Graph: mixed weighted/unweighted edges | ERROR |
| E1480 | `primitives/metricplot.py:142` | MetricPlot: no series | ERROR |
| E1481 | `primitives/metricplot.py:145` | MetricPlot: too many series (>8) | ERROR |
| E1483 | `primitives/metricplot.py:263` | MetricPlot: series exceeds 1000 points | ERROR |
| E1484 | `primitives/metricplot.py:634,639` | MetricPlot: log scale non-positive value (clamped) | WARNING (collector) |
| E1485 | `primitives/metricplot.py:170` | MetricPlot: series data validation error | ERROR |
| E1486 | `primitives/metricplot.py:209` | MetricPlot: degenerate xrange | ERROR |
| E1487 | `primitives/metricplot.py:241` | MetricPlot: mixed scales on same axis | ERROR |
| E1500 | `primitives/graph_layout_stable.py:348,356,359` | Graph layout: SA optimizer no convergence | WARNING (collector) |
| E1501 | `primitives/graph_layout_stable.py:246,251,255`, `graph.py:336` | Graph: too many nodes for stable layout | WARNING (collector) |
| E1502 | `primitives/graph_layout_stable.py:262,269,273` | Graph: too many frames for stable layout | WARNING (collector) |
| E1503 | `primitives/graph_layout_stable.py:248,252,256,266,270,274` | Graph: fell back to force layout | WARNING (collector) |
| E1504 | `primitives/graph_layout_stable.py:228,237,240` | Graph: `layout_lambda` clamped | WARNING (collector) |
| E1505 | `primitives/graph_layout_stable.py:222`, `graph.py:387,393` | Graph: invalid `layout_seed` | ERROR |

---

## 3. Findings Table

| Severity | File:line | Issue | Fix |
|----------|-----------|-------|-----|
| HIGH | `core/workers.py:294` | **E1199 raised but missing from `ERROR_CATALOG`**. Code is raised in `WorkerError` for "worker closed unexpectedly (empty response)" but is absent from `animation/errors.py:ERROR_CATALOG`. The reserved-range comment in `environments.md` says E1183–E1199 are reserved, creating a false impression this code doesn't exist. | Add `"E1199": "Worker subprocess terminated without response (crash or ungraceful exit)."` to `ERROR_CATALOG`. Update the reserved-range comment in `environments.md` to note E1199 is live. |
| HIGH | `animation/errors.py` (catalog) | **E1157 and E1158 documented in `ruleset.md` (§compute) but absent from `ERROR_CATALOG` and not raised anywhere in source code.** `ruleset.md` defines E1157 as "Non-integer subscript" and E1158 as "Recursion depth exceeded" but neither exists as a raise site. | Either implement these raise sites in `starlark_worker.py` (subscript checking and recursion tracking) or explicitly mark them as reserved/unimplemented in the catalog with a note. |
| HIGH | `animation/primitives/numberline.py:110` | **Live `E1103` mega-bucket raise site for `ticks < 1`.** When `ticks < 1`, the code raises `E1103` (the deprecated mega-bucket) instead of the specific `E1454` code. The `ticks > 1000` branch correctly uses E1454, but the `ticks < 1` branch was never migrated. | Change the `ticks < 1` branch to raise `_animation_error("E1454", ...)` — the same code as the `ticks > 1000` branch — since both are NumberLine ticks range errors. |
| HIGH | `animation/errors.py:222-230` | **E1180 and E1181 are multi-condition codes.** The catalog entry for E1180 reads "Animation has >30 frames (warning) or `\cursor` requires at least one target" — two unrelated conditions sharing one code. A `\cursor`-missing-targets error has nothing to do with frame count. Same for E1181 (`>100 frames` OR `\cursor` missing index). This violates the one-issue-per-code principle and makes automated error categorization ambiguous. | Allocate separate codes for cursor errors (e.g. E1183/E1184 from the reserved range). `_grammar_commands.py:268,277` would raise E1183 for missing cursor targets; `_grammar_commands.py:288` would raise E1184 for missing cursor index. E1180/E1181 remain frame-count only. |
| MEDIUM | `animation/_frame_renderer.py:90-93` | **Silent `except Exception: pass` inside `_grow_widths_pass`.** The `prim.set_value(suffix, str(val))` call on line 91 is wrapped in a bare `except Exception: pass`. If a primitive's `set_value` raises for an unexpected reason (e.g. type error, attribute error), the failure is completely invisible. | Replace with `except (AttributeError, ValueError): pass` scoped to the expected exceptions. Log unexpected exceptions at `DEBUG` level: `except Exception: logger.debug("set_value %s failed: %s", suffix, exc)`. |
| MEDIUM | `animation/_frame_renderer.py:328` | **Silent `except Exception: pass` in E1115 warning-collector path.** If `_emit_warning` raises for any reason (e.g. bad `ctx` state), the exception is swallowed without even a log line. | At minimum log the suppressed exception: `except Exception as exc: logger.debug("E1115 collector failed: %s", exc)`. |
| MEDIUM | `animation/parser/_grammar_compute.py:39` | **Silent `except Exception: pass` in `_collect_compute_bindings`.** While the comment justifies this ("best effort, never fail parse"), a completely silent swallow means even logic errors inside `_collect_compute_bindings` (e.g. regex bug) go undetected. | Replace with `except (SyntaxError, re.error): pass` or the specific exceptions expected, and add `except Exception as exc: logger.debug(...)` for unexpected cases so bugs surface in test runs. |
| MEDIUM | `core/pipeline.py:227-232` | **Pipeline re-raises renderer exceptions with `type(e)(...)` which breaks custom exception types.** When `renderer.render_block()` raises an `AnimationError` (which has a custom `__init__` with keyword-only `code=`, `line=`, `col=`), `type(e)(f"renderer failed: {e}")` calls `AnimationError.__init__` with a positional arg it may not support, potentially raising `TypeError` and obscuring the original error. | Use `e.args = (f"renderer {renderer.name!r} failed ...: {e.args[0] if e.args else str(e)}",) + e.args[1:]` and `raise`, or simply `raise RuntimeError(msg) from e` when re-raising for diagnostic enrichment. |
| MEDIUM | `core/workers.py:493,510` | **`ValueError` used for internal invariant violations.** `register()` raises bare `ValueError("register() requires either argv or worker")` — a Python built-in that callers have no way to distinguish from user-data validation errors. | Replace with `ScribaError` or a dedicated `ConfigurationError(ScribaError)` so `except ScribaError` handlers catch these consistently. |
| MEDIUM | `animation/scene.py:668` | **Last surviving live E1103 raise site** (annotation cap). After the E14xx split, this is the only remaining production `E1103` raise that isn't the deprecated mega-bucket alias. Should have a dedicated E-code to allow precise error categorization by tooling. | Assign code `E1475` (or the next available in the graph block) or `E1300` in a new "scene" range, documenting it as "annotation-per-frame cap exceeded". |
| LOW | `animation/errors.py:208` | **E1155 catalog text says "Starlark memory limit exceeded" but the live message says "peak memory {N}MB exceeds 64MB limit".** The catalog gives no indication of the 64MB threshold, making it harder to reproduce without reading source. | Update catalog: `"E1155": "Starlark memory limit exceeded (64 MB); reduce data size."` |
| LOW | `core/pipeline.py:104,113` | **`ValueError` raised for invalid `Pipeline` construction.** `"Pipeline requires at least one renderer"` is a library user error that should carry a structured code and message. | Use `ScribaError(..., code="E1000")` if a general config code is reserved, or document these as `ValueError` by design in the public API. |
| LOW | `animation/starlark_worker.py:763` | **Broad `except Exception` in the worker's outer eval catch is intentional and safe** (it marshals errors to JSON for IPC). Not a silent swallow — all paths return structured `{ok: False, code: ...}`. No action needed, but the `# noqa: BLE001` comment is absent here unlike the other broad catches. | Add `# noqa: BLE001 - intentional: all exceptions serialized to JSON response` for consistency with other broad catches in the file. |

---

## 4. Silent-Failure List

| Location | Pattern | Risk | Notes |
|----------|---------|------|-------|
| `animation/_frame_renderer.py:90-93` | `except Exception: pass` on `prim.set_value()` | MEDIUM | Best-effort grow-widths pass. Silent failure means a primitive silently skips value initialization. No user feedback. |
| `animation/_frame_renderer.py:315-329` | `except Exception: pass` on E1115 collector routing | MEDIUM | Warning intended for `Document.warnings` may never arrive. User never knows the warning was attempted. |
| `animation/parser/_grammar_compute.py:37-40` | `except Exception: pass` on `_collect_compute_bindings` | MEDIUM | Static binding analysis is intentionally loose, but this silences any bug inside the regex engine or parser logic for compute blocks. |
| `core/workers.py:519-527` | `except Exception: ... logger.debug("pool close: %s", e)` | LOW | Cleanup path only; debug-level logging means the failure is visible if debug logging is enabled. Acceptable but loses the stack trace. |
| `core/pipeline.py:369-373` | `except Exception: warnings.warn(...); logger.warning(...)` | LOW | Renderer `close()` failures surface via `warnings.warn` + logger. This is correct behavior — exception is not swallowed, just demoted. Not a concern. |
| `tex/renderer.py:254-256` | `except Exception: _vendored_exists = False` on `traversable.exists()` | LOW | Falls back gracefully to global npm root discovery. Side effect: if the vendor file exists but `exists()` raises (e.g. permissions), the expensive `npm root -g` subprocess runs unnecessarily. |

---

## 5. Top 3 Priorities

### Priority 1 — Catalog E1199 and close the reserved-range lie

**File:** `scriba/animation/errors.py` + `docs/spec/environments.md`

E1199 is raised live in production by `core/workers.py:294` but is not in `ERROR_CATALOG`. The `environments.md` spec says E1183–E1199 are "reserved", which actively misleads maintainers and tooling into believing the code doesn't exist. Any error-catalog sync tool, docs generator, or automated test that validates catalog completeness will miss it. This is a one-line fix with outsized correctness value.

**Fix:** Add to `ERROR_CATALOG`:
```python
"E1199": "Worker subprocess terminated without response (crash or ungraceful exit).",
```
And update `environments.md` to note E1199 is live (not reserved).

---

### Priority 2 — Migrate `numberline.py:110` off E1103 and clarify E1180/E1181 multi-condition

**Files:** `scriba/animation/primitives/numberline.py:110`, `scriba/animation/errors.py:222-230`, `scriba/animation/parser/_grammar_commands.py:268,277,288`

Two issues that together represent the last significant technical debt in the E1103 → E14xx migration:

(a) `numberline.py:110` raises deprecated `E1103` for `ticks < 1`. The `ticks > 1000` path correctly raises `E1454`. This inconsistency means two different error codes fire for what is logically the same constraint (`ticks` out of range `1..1000`).

(b) E1180 and E1181 each cover two unrelated conditions (frame count limit AND cursor missing required arg). These should be split. This prevents users from looking up an error code and finding a description that matches only one of the two triggers.

**Fix (a):** Change `numberline.py:110` from `E1103` to `E1454`.  
**Fix (b):** Allocate E1183 ("cursor requires at least one target") and E1184 ("cursor requires index parameter") and update the four raise sites in `_grammar_commands.py`.

---

### Priority 3 — Add `E1157`/`E1158` or explicitly mark them unimplemented

**Files:** `scriba/animation/errors.py`, `docs/spec/ruleset.md`

`ruleset.md` §compute (lines 1188–1190) documents E1157 (non-integer subscript) and E1158 (recursion depth exceeded ~1000 stack frames) as production error codes. Neither appears in `ERROR_CATALOG` nor has any raise site in the source code. This creates a documentation-code mismatch where users looking up an E1157 error will find spec documentation for a behavior that the runtime does not actually enforce.

The Starlark worker does catch `RecursionError` (at `starlark_worker.py:750`) but maps it to E1151, not E1158. Subscript boundary errors surface as generic E1151 runtime failures.

**Fix:** Either add these to the catalog with a `# status: unimplemented — fires as E1151` note so maintainers know the intent, or implement the two raise sites in `starlark_worker.py` and `starlark_host.py` to produce the specific codes as documented.

---

## Appendix — Codes in Spec but Missing from Live Catalog

| Code | Documented in | Status |
|------|-------------|--------|
| E1157 | `ruleset.md:1189` | Spec-only; no raise site; collapses to E1151 |
| E1158 | `ruleset.md:1190` | Spec-only; no raise site; collapses to E1151 |
| E1199 | `core/workers.py:294` | **Live but absent from `ERROR_CATALOG`** |
| E1320–E1324 | `ruleset.md:1222-1226` | Spec-reserved; no raise sites found in source |

## Appendix — Codes Mentioned Only in Docs (Never Raised)

E1101, E1104, E1105, E1106, E1107, E1108, E1110, E1111 appear in `docs/spec/primitives.md` and `docs/spec/error-codes.md` but have no raise sites in the current production source. They appear to be catalog entries for features not yet implemented or removed during refactoring. They are not bugs — the docs accurately say what conditions they cover — but a developer unfamiliar with the codebase would expect to find them as raise sites.
