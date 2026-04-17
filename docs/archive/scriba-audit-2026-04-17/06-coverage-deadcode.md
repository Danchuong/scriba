# Scriba Coverage & Dead Code Audit — 2026-04-17

Scope: `scriba/` (production) + `tests/` (2299 tests, 1 skipped).
Tool: `uv run pytest --cov=scriba --cov-report=term-missing` (pytest-cov already installed).

---

## Summary

| Metric | Value |
|--------|-------|
| Overall coverage | **84.72 %** (required threshold: 75 %) |
| Total statements | 8 927 |
| Missed statements | 1 110 |
| Branch coverage (partial) | 426 branches partially hit |
| Dead functions confirmed | **3** (never called outside definition file) |
| Dead no-op function (preserved for compat) | **1** (`emit_arrow_marker_defs`) |
| Error codes raised in code but absent from `error-codes.md` | **15** |
| Error codes in `error-codes.md` but never raised in code | **7** (range-cap sentinel values) |
| Test quality smells (no-assert tests) | **50** |
| Empty / zero-byte snapshot files with live tests | **3** |
| Stale "Currently unused / Wave N migration" markers | **3 sites** |

---

## Coverage gaps by module

Modules below 80 % or with high-risk uncovered branches:

### `scriba/animation/errors.py` — 61 %
Missing lines 616–641, 692, 765–770.

- **Lines 616–641**: `format_compute_traceback()` — the function body is entirely uncovered. The function is *called* from `starlark_worker.py:604` so it is not dead, but the integration path that reaches it is never exercised in the unit test suite (Starlark subprocess not started).
- **Line 692**: `validation_error_from_selector()` return statement — confirmed dead (see §Dead code inventory).
- **Lines 765–770**: `AnimationError.to_render_warning()` method — no test exercises the conversion from `AnimationError` to a `RenderWarning`. This is a public conversion path used by the renderer; its absence risks silent regressions in warning-surfacing behaviour.

Riskiest uncovered function: `AnimationError.to_render_warning()` — used at the renderer/pipeline boundary where errors are downgraded to warnings; a regression here surfaces as silently dropped user-visible diagnostics.

---

### `scriba/animation/primitives/base.py` — 67 %
Missing lines 180–200, 331–343, 353–373, 414, 447, 460–475, 558–624 (the `text_outline=` deprecated path), 799–815, 845–866, 942–943, 945–946, 962–977, 1106–1120, 1153–1157, 1187–1207, 1261, 1282–1292.

Key uncovered regions:

- **Lines 558–624**: The deprecated `text_outline=` parameter path inside `_render_svg_text()`. Documented for removal in v0.7.0 but never tested even for the deprecation warning. Low risk (CSS overrides it anyway) but the warning itself is untested.
- **Lines 799–815**: `emit_arrow_svg()` — leader-line rendering branch (displacement > 30 px). Arrow annotations with large label displacement (long arrow arcs) are not covered.
- **Lines 845–866**: Multi-line label `<tspan>` path inside `emit_arrow_svg()`. Labels that exceed `_LABEL_MAX_WIDTH_CHARS = 24` characters are not tested.
- **Lines 962–977**: `arrow_height_above()` — the `layout="2d"` branch. All tested animations use horizontal layout; the 2D layout variant (used by DPTable and Grid arrow annotations) is uncovered.
- **Lines 1187–1207**: `emit_plain_arrow_svg()` — the entire plain-arrow (no source arc) rendering path is uncovered.

Riskiest uncovered function: `emit_plain_arrow_svg()` — plain `arrow=True` annotations produce entirely untested SVG.

---

### `scriba/animation/primitives/plane2d.py` — 74 %
Missing lines 167, 193, 252, 290–315, 336–349, 461, 500–516, 538, 550–595, 623–629, 656, 670, 720, 769–805, 862–886, 982, 989–999, 1019–1026, 1042–1051, 1065–1075, 1133–1139, 1147, 1163–1175, 1226, 1270, 1286.

Key uncovered regions:

- **Lines 550–595**: Text annotation rendering inside `Plane2D.emit_svg()` — the branch that draws text labels on plane elements is uncovered.
- **Lines 769–805**: Bezier curve rendering for plane function plots.
- **Lines 862–886**: Polygon rendering path.
- **Lines 1042–1075**: Plane2D annotation arrow sub-path for text elements.

Riskiest uncovered functions: text-label rendering and polygon SVG output — both are user-facing primitives that could silently produce malformed SVG.

---

### `scriba/animation/renderer.py` — 74 %
Missing lines 162–168, 183–189, 203, 236, 244–248, 309, 315–318, 469, 490–483 (branch), 519–521, 531–534, 571–576, 598–635.

Key uncovered regions:

- **Lines 162–168 / 183–189**: `_resolve_params()` and `_resolve_single()` — the subscript-resolution branches for `InterpolationRef` with list/dict subscripts (`value[0]`, `value["key"]`) are not tested.
- **Lines 598–635**: `DiagramRenderer.render()` — the diagram rendering path is exercised only via integration tests; unit coverage of the `DiagramRenderer.render()` method itself is 0 %.

Riskiest uncovered functions: `DiagramRenderer.render()` and the `InterpolationRef` subscript paths — both affect correctness of computed shape parameters.

---

### `scriba/animation/starlark_host.py` — 68 %
Missing lines 90–117, 209–218, 226–227, 234–235.

- **Lines 90–117**: `_starlark_preexec()` — the OS-level `RLIMIT_AS` / `RLIMIT_DATA` / `RLIMIT_CPU` setup. This is a `preexec_fn` called in the child process and cannot be covered under the current mock-based test setup. Justified omission, but lack of integration-level coverage means resource limit regressions would be invisible.
- **Lines 209–218**: `StarlarkHost.eval_raw()` — the entire method body. See §Dead code inventory.
- **Lines 226–227 / 234–235**: `StarlarkHost.ping()` error return and `StarlarkHost.close()` `KeyError` branch.

---

### `scriba/animation/emitter.py` — 85 %
Missing lines 172–187, 230, 232, 234, 245, 250–271, 378–382, 398, 404–416, 444, 454, 485–486, 519, 526, 580, 589, 594–596, 703–705, 711, 810, 903, 908–909, 912, 983, 1370–1377, 1406, 1423–1442, 1528, 1547.

Key uncovered regions:

- **Lines 1370–1377**: `_minify_css()` — tested indirectly via `_minify_html()` but not directly. Low risk.
- **Lines 1423–1442**: `_minify_html()` `<script>` block minification path — no test passes HTML with inline `<script>` to the minifier.
- **Lines 172–187**: `_inject_tree_positions()` — the branch where a shape exists in `shape_states` without an entry for the node being positioned. Represents an unusual but reachable state.

---

### `scriba/animation/parser/grammar.py` — 84 %
Missing lines 146–149, 171, 204, 210, 355, 442, 501, 524–527, 567–570, 593–594, 633–666, 708–731, 744–751, 755, 783, 792, 805, 887, 922, 936, 995, 1016, 1023, 1060, 1069, 1072, 1088–1097, 1144, 1150, 1160–1168, 1184, 1192, 1239, 1253, 1280, 1288, 1324–1325, 1336–1337, 1340–1351, 1356, 1363, 1368, 1378, 1389–1398, 1413, 1418, 1455–1456, 1461, 1463, 1469, 1537, 1561–1563, 1609, 1628–1630, 1643–1645, 1652–1665, 1678, 1683, 1717, 1722, 1739, 1760, 1784, 1794, 1806, 1809, 1826, 1834–1836, 1845.

At 84 % with 800 statements this is the largest gap in absolute terms (99 missed statements + 78 partial branches). The uncovered lines are spread across many error-recovery branches inside the recursive-descent parser — by construction these are hard-to-trigger paths that require malformed input combinations. The Hypothesis-based fuzz tests (`test_parser_hypothesis.py`) cover many of these but do not reach all of them.

Riskiest uncovered regions: substory parsing branches (lines 1389–1413) and `\foreach` body edge cases (lines 1060–1097).

---

### `scriba/core/workers.py` — 81 %
Missing lines 41, 45, 121–128, 144–152, 182–193, 196–200, 206, 210, 218–220, 251–254, 259–266, 280–283, 407–408.

- **Lines 121–128**: Windows-specific `readline()` path inside `_wait_for_ready()` — not tested on macOS CI.
- **Lines 182–193**: `_kill()` error branches — `OSError`/`ProcessLookupError` during `terminate()` or `kill()`. Requires mocking subprocess at the OS level; intentionally left as defensive code.
- **Lines 407–408**: `OneShotSubprocessWorker` timeout kill error branch.

---

### `scriba/tex/parser/escape.py` — 71 %
Missing lines 20, 30–33, 42–54, 101, 105–107.

- **Lines 42–54**: The `\textbackslash`, `\textasciicircum`, `\textasciitilde` escape-to-HTML conversion paths. These LaTeX commands are defined but no test exercises them.
- **Lines 20 / 30–33**: Branch where the input string is empty or has specific short-circuit conditions.

---

### `scriba/tex/parser/math.py` — 78 %
Missing lines 44–50, 118, 132, 142–152.

- **Lines 44–50**: Display-math `\[...\]` environment parser path.
- **Lines 142–152**: Math error-fallback path when KaTeX rendering fails — the fallback that wraps the raw LaTeX in a `<code>` element is never triggered in tests.

---

## Dead code inventory

| File:line | Symbol | Why dead |
|-----------|--------|----------|
| `scriba/animation/errors.py:644` | `validation_error_from_selector()` | Explicitly documented "Currently unused — Wave 3 will migrate selectors.py." Wave 3 is complete and `selectors.py` was never updated to call this. No caller exists anywhere in the codebase. Safe to remove after confirming no external consumers (it is not exported from any `__init__.py`). |
| `scriba/animation/starlark_host.py:197` | `StarlarkHost.eval_raw()` | No caller in production code or tests. Not exported in `scriba/__init__.py`. Added as a debugging convenience; never wired up. Flag for human review before removal — it could be intentionally kept for REPL/debugging use. |
| `scriba/animation/primitives/base.py:1303` | `emit_arrow_marker_defs()` | Confirmed **intentional no-op** — the function body is a single `pass` with a comment: *"Arrowheads are now rendered as inline `<polygon>` elements … No `<marker>` `<defs>` needed. This function is kept as a no-op for call-site compat."* It is imported and called by 11 primitive files. Removing it requires updating all 11 call sites simultaneously; the function itself is 0 runtime cost. |
| `scriba/animation/emitter.py:1370` | `_minify_css()` | Called only from `_minify_html()` (which is itself only called when `minify=True`). Not dead, but the `minify=True` path (`emit_animation_html(…, minify=True)`) is never exercised in the test suite — 7 lines missed as a result. |

---

## Error code drift

### Raised in production code but absent from `error-codes.md`

These codes are fully implemented and in the `ERROR_CATALOG` in `errors.py` but have no entry in the public spec document.

| Code | Location | Description (from ERROR_CATALOG) |
|------|----------|----------------------------------|
| E1057 | `parser/grammar.py:1308,1320,1332` | `\narrate` duplicate or out-of-place in substory |
| E1114 | `primitives/base.py:318` | `set_color()` called with unknown color name |
| E1200 | `tex/renderer.py:85` | TeX renderer generic error |
| E1433 | `primitives/tree.py:537` | Tree mutation: node already exists |
| E1434 | `primitives/tree.py:530` | Tree mutation: parent node not found |
| E1435 | `primitives/tree.py:446,607–619` | Tree mutation: remove_node on non-leaf or non-existent node |
| E1436 | `primitives/tree.py:421,437,480,488,521,597,602,629` | Tree mutation: invalid edge or cycle detected |
| E1437 | `primitives/plane2d.py:400–462` | Plane2D: element add/remove validation error |
| E1471 | `primitives/graph.py:423,431,467,472` | Graph mutation: add_node duplicate or invalid |
| E1472 | `primitives/graph.py:440,485` | Graph mutation: add_edge invalid node reference |
| E1473 | `primitives/graph.py:449,501,507` | Graph mutation: remove_edge / remove_node invalid |
| E1474 | `primitives/graph.py:331,336` | Graph: weight validation failure |
| E1017 | `uniqueness.py:67` | Shape ID invalid charset or too long |
| E1018 | `uniqueness.py:97` | Duplicate shape ID within animation |
| E1019 | `uniqueness.py:127` / `core/pipeline.py:252` | Duplicate animation ID across document |

**Action required**: Add entries for all 15 codes to `docs/spec/error-codes.md`. E1017–E1019 are particularly important as they are user-visible validation errors.

---

### In `error-codes.md` but never raised in production code

These are range-cap sentinel codes (e.g. `E1409`, `E1419`) that mark the *end* of a code range in the spec document but correspond to no actual error condition. They appear as section headers in the catalog (`### Array (E1400--E1409)`) but the trailing sentinel is not a real error.

| Code | Spec description |
|------|-----------------|
| E1059 | End-of-range sentinel for Diagram-specific errors (E1050–E1059) |
| E1409 | End-of-range sentinel for Array errors (E1400–E1409) |
| E1419 | End-of-range sentinel for Grid errors (E1410–E1419) |
| E1439 | End-of-range sentinel for Tree errors (E1430–E1439) |
| E1449 | End-of-range sentinel for Queue/Stack errors (E1440–E1449) |
| E1459 | End-of-range sentinel for HashMap/NumberLine errors (E1450–E1459) |
| E1479 | End-of-range sentinel for Graph errors (E1470–E1479) |

These are not true drift — they are documented range boundaries. No action required, but the spec could be clarified to mark them explicitly as "range reserved, not a raised code."

---

## Stale markers

No `# TODO`, `# FIXME`, or `# XXX` comments exist in `scriba/` production code. However, the following docstring-embedded deferred-migration markers remain unresolved:

| File | Lines | Marker text | Age (last file commit) |
|------|-------|-------------|------------------------|
| `scriba/animation/errors.py` | 600–602 | *"Currently unused. Cluster 1 owns `starlark_worker.py` and will migrate the raw-traceback assembly to call this helper in a follow-up change"* — for `format_compute_traceback()`. **Update**: the migration was completed (`starlark_worker.py:604` now calls it), but the docstring still says "currently unused." The docstring is stale. | 2026-04-17 |
| `scriba/animation/errors.py` | 686–690 | *"Currently unused. Wave 3 will migrate `scriba/animation/parser/selectors.py` to call this helper"* — for `validation_error_from_selector()`. Wave 3 is complete; the migration never happened. The function remains truly unused. | 2026-04-17 |
| `scriba/animation/primitives/plane2d.py` | 115 | *"no rendered effect — tracked as v0.6.2 follow-up"* for a Plane2D text annotation attribute. | 2026-04-17 |
| `scriba/core/workers.py` | 323 | *"Wave 1 Cluster 3 introduced a module-import-time warning; Wave 3 Cluster 9 …"* — historical wave annotation in a comment, not a deferred action item. Low priority. | 2026-04-11 |

---

## Duplicate logic

### Cell-selector regex patterns (high duplication)

The pattern `r"^cell\[(?P<idx>\d+)\]$"` and its variants are re-defined as module-level compiled regexes in every primitive file that handles cell addressing. Each primitive essentially re-implements the same selector parsing logic independently.

| Pattern | Files (with line) |
|---------|-------------------|
| `r"^cell\[(?P<idx>\d+)\]$"` (suffix form) | `array.py:64`, `queue.py:49`, `dptable.py:61` |
| `r"^(?P<name>\w+)\.cell\[(?P<idx>\d+)\]$"` (full form) | `array.py:59`, `queue.py:55`, `dptable.py:51`, `base.py:207` |
| `r"^cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$"` (2D suffix) | `grid.py:86`, `matrix.py:115`, `dptable.py:62` |
| `r"^range\[(?P<lo>\d+):(?P<hi>\d+)\]$"` (suffix range) | `array.py:65`, `dptable.py:63`, `numberline.py:53` |
| `r"^(?P<name>\w+)\.range\[.*\]$"` (full range) | `array.py:60`, `numberline.py:47`, `base.py:211` |
| `r"^(?P<name>\w+)\.node\[.*\]$"` (node form) | `tree.py:44`, `graph.py:65`, `linkedlist.py:58` |

**Consolidation opportunity**: `scriba/animation/primitives/base.py` already defines `_CELL_1D_RE`, `_CELL_2D_RE`, `_RANGE_RE`, and `_ALL_RE` at lines 207–214. The per-primitive duplicates should import from `base` instead of re-defining. Estimated removal: ~12–15 regex definitions across 6 files.

---

### `estimate_text_width()` — single canonical implementation, wide import surface

`estimate_text_width()` is defined once in `base.py:130` and imported by 9 primitive files. This is correct (not duplicated), but worth noting that the function's simple `0.62 × font_size` heuristic is the only width model used across all primitives — any improvement needs to land in exactly one place.

---

### Width-estimation logic in `_prescan_value_widths()` vs per-primitive `set_value()`

`emitter.py:204` (`_prescan_value_widths`) iterates all frames and calls each primitive's `set_value()` to warm width-tracking state before viewbox computation. Some primitives (e.g. `VariableWatch`, `Queue`) maintain internal `_value_col_width` / `_cell_width` state that grows monotonically on `set_value()`. This means the "prescan then restore" pattern in the emitter duplicates the "track max width on mutation" logic already inside those primitives. The two mechanisms serve the same goal (stable viewbox) via different paths — a potential source of subtle divergence bugs.

---

## Top 5 cleanup tasks ranked

Ranked by (lines removed × risk reduction):

### 1. Add 15 missing error codes to `error-codes.md`
**Lines removed**: 0 (documentation addition, not deletion)
**Risk**: HIGH — E1471–E1474 (Graph mutations), E1433–E1437 (Tree mutations), E1437 (Plane2D) are raised frequently in real animations. Users who encounter these errors have no public reference to look them up. E1017/E1018/E1019 are validation errors shown on parse failure.
**Action**: Add table rows for all 15 codes in the appropriate sections of `docs/spec/error-codes.md`.

---

### 2. Remove or wire `validation_error_from_selector()` (dead function, ~55 lines)
**Lines removed**: ~55 (function body + docstring in `errors.py:644–698`)
**Risk**: LOW — confirmed zero callers inside the package; not exported from any `__init__.py`. The "Wave 3" migration it was written for is complete and chose a different approach.
**Caveat**: Flag for human review — if any external consumer imports from `scriba.animation.errors` directly (not via `scriba`), removal would be a breaking change. Given `animation.errors` is not in `__all__` it is unlikely to be used externally.

---

### 3. Consolidate duplicate cell-selector regexes (~12–15 definitions → imports)
**Lines removed**: ~20–25 (duplicate `re.compile(...)` calls across `array.py`, `queue.py`, `grid.py`, `matrix.py`, `dptable.py`, `linkedlist.py`)
**Risk**: LOW — mechanical substitution of local definitions with imports from `base`. The canonical versions already exist in `base.py:207–214`. Reduces maintenance surface and ensures consistent pattern behaviour.
**Action**: In each primitive file, replace the locally-defined regex with an import of the equivalent from `base`. Update suffix-only variants by stripping the name-group if needed, or add suffix-only variants to `base`.

---

### 4. Add tests for `emit_plain_arrow_svg()` and the `layout="2d"` arrow height path
**Lines removed**: 0 (test addition)
**Risk**: HIGH risk reduction — `emit_plain_arrow_svg()` (plain `arrow=True` annotations) is the entire implementation of pointer-style annotations used in many animation primitives, with 0 % unit coverage. The `layout="2d"` branch of `arrow_height_above()` is exercised by DPTable and Grid annotations but is uncovered.
**Action**: Add unit tests in `tests/unit/test_animation_emitter.py` or a new `test_arrow_annotations.py` targeting `emit_plain_arrow_svg()` and `arrow_height_above(layout="2d")` directly.

---

### 5. Fix stale docstring for `format_compute_traceback()` and remove dead `eval_raw()`
**Lines removed**: ~22 (stale docstring lines + `eval_raw` body in `starlark_host.py:197–218`)
**Risk**: LOW — `eval_raw()` has no callers; the stale docstring for `format_compute_traceback()` says "currently unused" when the function is in fact used. The misleading docstring increases the chance a future reader deletes the function incorrectly.
**Action**: (a) Update `errors.py:600–602` docstring to reflect that `format_compute_traceback()` is now wired into `starlark_worker.py`. (b) Remove `StarlarkHost.eval_raw()` after confirming no external consumers (flag for human review first given it is a public method on a public class).

---

## Test quality smells

50 tests matched the "no assert / no raises" pattern. Of these:

- **43** are snapshot tests (`test_tex_snapshots.py`) that delegate to `assert_snapshot_match()` (a helper function), which contains the real `assert`. The AST walker did not follow the call into the helper. These are **false positives** — the tests are correctly asserting via the helper.
- **3** are zero-byte or near-zero-byte snapshot files being compared: `textbf_nested_in_textit.html` (63 bytes), `unicode_vietnamese_with_math.html` (1 148 bytes), `url_and_href.html` (228 bytes). These are small but non-empty so they do pass. However, `textbf_nested_in_textit.html` at 63 bytes for a KaTeX-rendered output is suspiciously small — likely only contains a bare `<em><strong>` fragment without surrounding HTML. Worth reviewing against spec §3.
- **4** are genuine no-assert tests in `test_workers.py` and `test_pipeline.py` where the intent is "must not raise." This pattern is acceptable for idempotency checks but should be documented with a comment (e.g. `# assert: must not raise`).

**No `assert True` or pass-only test bodies found** across the entire test suite.

**No snapshot review trail**: The `test_tex_snapshots.py` snapshots have a documented update policy in `tests/tex/conftest.py` — this satisfies the "review trail" requirement. No action needed.
