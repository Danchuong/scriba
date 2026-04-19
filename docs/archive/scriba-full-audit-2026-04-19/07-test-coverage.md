# 07 — Test Coverage Audit (2026-04-19)

**Tool:** `pytest --cov=scriba --cov-report=term-missing` (pytest-cov 5.x, branch coverage enabled)
**Run:** 2830 passed, 1 skipped, 83 warnings — 17.6 s wall clock
**Python:** 3.10.20
**Config threshold:** `fail_under = 75` in `[tool.coverage.report]`

---

## 1. Score: 7 / 10

Overall line coverage is **86.3%** and branch coverage is approximately **80%**, comfortably above the project's 75% threshold. The test corpus is large (2,268 `def test_*` functions across 112 test files) and is diverse enough to include property-based tests (Hypothesis), golden/snapshot fixtures, security red-team tests, and integration end-to-end tests. The suite runs fast at under 18 seconds total.

Points are lost for:

- Four modules below 75% line coverage, including a heavily-used SVG helper pair (`_text_render.py` at 56%, `_svg_helpers.py` at 68%).
- `animation/renderer.py` at 74% with the `_materialise_substory` path entirely absent from tests.
- Marks (`@pytest.mark.unit`) are used inconsistently and are unregistered — pytest emits 80+ `PytestUnknownMarkWarning` warnings per run, making mark-based filtering non-functional.
- No E2E browser tests exist for any rendered HTML output; the integration layer stops at Python-level HTML string assertions.
- The `_minify_html` / `_minify_js` fast-paths and the `_minify_style_block` bypass (the performance optimisation at lines 101–104 in `_minify.py`) are not covered.

---

## 2. Coverage Table

Measured by `pytest --cov=scriba --cov-report=json`. Branch percentages are computed as `covered_branches / num_branches`. Files with 100% line coverage are rolled up into their section row.

### Per-module (all files, sorted by line %)

| Module | Line % | Branch % | Statements | Missing lines |
|--------|--------|----------|-----------|---------------|
| `animation/primitives/_text_render.py` | 55.7% | 54.2% | 101 | 44 |
| `animation/primitives/_svg_helpers.py` | 68.2% | 45.7% | 326 | 83 |
| `tex/parser/escape.py` | 71.3% | 65.4% | 68 | 18 |
| `animation/primitives/__init__.py` | 73.3% | 0.0% | 28 | 6 |
| `animation/renderer.py` | 74.0% | 57.8% | 284 | 55 |
| `animation/_minify.py` | 74.3% | 83.3% | 58 | 16 |
| `animation/starlark_host.py` | 74.7% | 64.3% | 85 | 20 |
| `animation/primitives/plane2d.py` | 77.2% | 71.3% | 651 | 132 |
| `animation/emitter.py` | 77.3% | 59.1% | 75 | 13 |
| `tex/parser/math.py` | 77.5% | 68.8% | 64 | 13 |
| `tex/parser/tables.py` | 78.8% | 69.4% | 155 | 27 |
| `tex/renderer.py` | 80.8% | 73.8% | 271 | 46 |
| `animation/primitives/queue.py` | 81.4% | 67.7% | 185 | 26 |
| `core/workers.py` | 81.5% | 76.3% | 275 | 47 |
| `animation/_frame_renderer.py` | 81.6% | 77.8% | 217 | 35 |
| `animation/scene.py` | 83.0% | 75.6% | 342 | 45 |
| `animation/parser/_grammar_substory.py` | 83.5% | 76.6% | 160 | 20 |
| `animation/primitives/dptable.py` | 83.5% | 75.7% | 199 | 27 |
| `animation/primitives/base.py` | 83.8% | 72.5% | 127 | 16 |
| `core/renderer.py` | 84.2% | n/a | 19 | 3 |
| `tex/parser/_urls.py` | 84.6% | 87.5% | 18 | 3 |
| `animation/primitives/variablewatch.py` | 85.2% | 75.9% | 156 | 18 |
| `animation/primitives/numberline.py` | 85.3% | 77.8% | 163 | 20 |
| `tex/parser/images.py` | 85.4% | 79.2% | 65 | 8 |
| `animation/extensions/hl_macro.py` | 85.9% | 77.3% | 49 | 5 |
| `tex/validate.py` | 86.0% | 84.2% | 62 | 8 |
| `core/text_utils.py` | 86.0% | 71.4% | 29 | 2 |
| `animation/primitives/hashmap.py` | 86.5% | 76.1% | 146 | 15 |
| `tex/highlight.py` | 86.9% | 87.5% | 45 | 6 |
| `animation/primitives/grid.py` | 87.0% | 81.2% | 129 | 14 |
| `animation/primitives/linkedlist.py` | 87.1% | 77.8% | 179 | 18 |
| `animation/parser/_grammar_compute.py` | 87.7% | 80.8% | 47 | 4 |
| `animation/parser/_grammar_foreach.py` | 88.1% | 80.6% | 65 | 5 |
| `animation/parser/_grammar_tokens.py` | 88.4% | 82.7% | 189 | 16 |
| `animation/primitives/array.py` | 88.6% | 78.8% | 149 | 12 |
| `animation/primitives/tree.py` | 88.7% | 86.2% | 313 | 32 |
| `core/__init__.py` | 88.9% | 50.0% | 16 | 1 |
| `animation/parser/lexer.py` | 89.9% | 84.8% | 211 | 18 |
| `animation/parser/selectors.py` | 90.8% | 84.8% | 185 | 13 |
| `tex/parser/environments.py` | 91.2% | 75.0% | 79 | 5 |
| `tex/parser/code_blocks.py` | 91.3% | 70.0% | 36 | 1 |
| `tex/parser/lists.py` | 91.5% | 78.6% | 57 | 3 |
| `core/pipeline.py` | 92.1% | 87.5% | 186 | 11 |
| `animation/parser/_grammar_commands.py` | 92.8% | 85.7% | 110 | 5 |
| `animation/primitives/graph.py` | 93.2% | 91.1% | 344 | 21 |
| `animation/primitives/matrix.py` | 93.4% | 87.9% | 190 | 9 |
| `animation/primitives/graph_layout_stable.py` | 93.4% | 92.0% | 161 | 10 |
| `animation/differ.py` | 94.0% | 87.0% | 105 | 3 |
| `animation/parser/grammar.py` | 94.3% | 92.3% | 228 | 11 |
| `animation/_html_stitcher.py` | 94.9% | 92.5% | 212 | 9 |
| `core/warnings.py` | 95.2% | 83.3% | 15 | 0 |
| `animation/errors.py` | 95.6% | 90.0% | 71 | 2 |
| `animation/primitives/metricplot.py` | 96.4% | 94.7% | 301 | 9 |
| `animation/detector.py` | 96.4% | 91.2% | 77 | 1 |
| `animation/primitives/plane2d_compute.py` | 97.2% | 96.0% | 93 | 2 |
| `animation/primitives/stack.py` | 97.8% | 97.9% | 138 | 3 |
| `animation/primitives/tree_layout.py` | 98.5% | 97.2% | 97 | 1 |
| `core/errors.py` | 98.6% | 94.4% | 52 | 0 |
| `animation/primitives/codepanel.py` | 100% | 100% | 112 | 0 |
| `animation/primitives/layout.py` | 100% | 100% | 40 | 0 |
| `animation/parser/ast.py` | 100% | n/a | 147 | 0 |
| `animation/constants.py` | 100% | n/a | 10 | 0 |
| `core/css_bundler.py` | 100% | 100% | 26 | 0 |
| `sanitize/whitelist.py` | 100% | n/a | 4 | 0 |
| `tex/__init__.py` | 100% | 100% | 15 | 0 |
| `tex/parser/dashes_quotes.py` | 100% | n/a | 10 | 0 |
| `tex/parser/text_commands.py` | 100% | 100% | 16 | 0 |

### Section subtotals

| Section | Line % | Branch % | Statements |
|---------|--------|----------|-----------|
| `animation/primitives` | 88.1% | 79.4% | 4363 |
| `animation/parser` | 93.4% | 84.3% | 1395 |
| `animation` (non-parser, non-primitives) | 87.7% | 77.0% | 1668 |
| `core` | 90.8% | 81.9% | 709 |
| `tex` | 85.7% | 75.5% | 962 |
| `sanitize` | 100% | n/a | 6 |
| **TOTAL** | **86.3%** | **~80%** | **9121** |

---

## 3. Gap Analysis — Top 10 Untested / Weakly-Tested Modules

Ranked by absolute line deficit (missing lines × risk).

### 1. `scriba/animation/primitives/_text_render.py` — 55.7% line, 54.2% branch

**File:** `scriba/animation/primitives/_text_render.py`

The most severely under-covered file. The entire `_render_svg_text` foreign-object path (lines 234–291) — the slow path that embeds KaTeX math inside SVG via `<foreignObject>` — has zero test coverage. Specific missing blocks:

- **Line 70–71**: bare ZWJ between clusters in `estimate_text_width` — no test for a leading ZWJ character.
- **Lines 123–135**: `_render_mixed_html` body — the escaped-dollar sentinel swap, multi-span interleaving, and tail segment all uncovered.
- **Lines 218–228**: `text_outline=` deprecation warning branch in `_render_svg_text` (emitting `DeprecationWarning`).
- **Lines 235–291**: entire `<foreignObject>` code path (math present + callback provided) — `text_anchor="start"`, `text_anchor="end"`, custom `font_size`, `font_weight` inside the foreign-object path.

Risk: every primitive that renders math labels (metricplot axes, array cells with `$...$`) hits this path at runtime but the test only exercises the fast (no-math) path.

### 2. `scriba/animation/primitives/_svg_helpers.py` — 68.2% line, 45.7% branch

**File:** `scriba/animation/primitives/_svg_helpers.py`

83 missing statements; branch coverage is the worst in the whole codebase at 45.7%.

- **Lines 78–98**: `_wrap_label_lines` multi-token wrapping — only the single-line (no-wrap) path is tested.
- **Lines 276–289**: `emit_plain_arrow_svg` multi-line label rendering loop.
- **Lines 333–340**: `arrow_height_above` pill-height calculation for multi-line labels.
- **Lines 416–451**: `emit_arrow_svg` — the arc-source arrow geometry path, including `_LabelPlacement.overlaps()` collision detection.
- **Lines 564–605, 627–681**: curved arrow rendering geometry and the `emit_arrow_marker_defs` SVG `<defs>` block variant.

Risk: annotations drawn on all primitives use these helpers. A regression in arrow geometry produces silently malformed SVG.

### 3. `scriba/animation/renderer.py` — 74.0% line, 57.8% branch

**File:** `scriba/animation/renderer.py`

- **Lines 162–168**: `_resolve_params` — subscript resolution on a `list` value (`InterpolationRef` with `isinstance(sub, int)` path).
- **Lines 183–189**: `_resolve_single` — the `InterpolationRef` path within list elements.
- **Lines 607–644**: `_materialise_substory` — substory-local `\shape` declarations (`sub_primitives` population at lines 608–614) and nested substory recursion (lines 623–630) are never exercised. The `depth > 1` code path is dead from a test perspective.
- **Lines 528–543**: `_instantiate_primitives` — the `prelude_compute` branch (Starlark bindings feeding into shape params) is absent.
- **Lines 580–585**: substory collection loop inside `_materialise` — only exercised when a frame has substories; the integration tests hit this but miss the nested case.

### 4. `scriba/animation/primitives/_svg_helpers.py` (branch coverage sub-issue)

Separately: `_LabelPlacement.overlaps()` — the four overlap conditions (left, right, above, below) have only the trivial non-overlapping case exercised. The four boundary conditions (just-touching, coincident) are uncovered (lines 63–70 branch paths).

### 5. `scriba/animation/starlark_host.py` — 74.7% line, 64.3% branch

**File:** `scriba/animation/starlark_host.py`

- **Lines 94–125**: `_set_resource_limits` function — the full body that calls `resource.setrlimit`. On macOS (`sys.platform == "darwin"`) and Windows this runs as `preexec_fn` in a subprocess, making it structurally hard to exercise without a fork. The Linux `RLIMIT_AS` path and the `OSError` exception branches at lines 103–104 and 111–112 are uncovered.
- **Lines 227, 246–247, 254–255**: `StarlarkHost` methods related to budget tracking across renderers and `begin_render()` call edge cases.

### 6. `scriba/tex/parser/escape.py` — 71.3% line, 65.4% branch

**File:** `scriba/tex/parser/escape.py`

- **Lines 42–54**: `parse_command_args` — the multi-brace consumption loop. The regex match-failure branch (line 20: `start_pos >= len(text)`) and the unbalanced-brace edge case in `extract_brace_content` (line 33) are uncovered.
- **Lines 101, 105–107**: `PlaceholderManager.restore_inline` — the `is_block` filter branch and `restore_blocks` method body are never reached in any test.

### 7. `scriba/animation/primitives/plane2d.py` — 77.2% line, 71.3% branch

**File:** `scriba/animation/primitives/plane2d.py`

132 missing lines is the largest raw count in the codebase. Key uncovered regions:

- **Lines 290–302**: `_add_line_internal` — the `dict` branch (line specifying `slope`/`intercept` directly) and the vertical-line special case (`slope=inf`).
- **Lines 311–315**: `_add_segment_internal` — the `dict` input branch.
- **Lines 550–595**: `get_svg_position` — coordinate lookup for `line[N]`, `segment[N]`, and `polygon[N]` target types. The annotation arrow system calls this for non-point targets; no test provides a line or polygon target for annotation.
- **Lines 792–818**: `remove` operation on lines, segments, and polygons.
- **Lines 921–983**: label emission in `_emit_svg` for lines with vertical/infinite slope and for polygon centroids.
- **Lines 997–1007**: segment SVG emission with explicit label.

### 8. `scriba/tex/parser/math.py` — 77.5% line, 68.8% branch

**File:** `scriba/tex/parser/math.py`

- **Lines 44–50**: `_preprocess_text_command_chars` — the `_esc` closure body and the four `re.sub` calls inside it. No test passes a `\text{}` or `\texttt{}` with `_`, `#`, `%`, or `&` inside it.
- **Lines 142–152**: `render_math_batch` — the `html is None` error branch with `strict=False`, which produces the `<span class="scriba-tex-math-error">` fallback HTML including the XML-escape of the source math.

### 9. `scriba/tex/parser/tables.py` — 78.8% line, 69.4% branch

**File:** `scriba/tex/parser/tables.py`

- **Lines 92–93**: `_render_cell` — the `cell_renderer is None` fallback path (HTML-escape-only, no inline TeX rendered).
- **Lines 155–160**: trailing `\hline`/`\cline` at end of table body — assigned to previous row's bottom border.
- **Lines 192–200**: `active_rowspans` multirow placeholder skip — `\multicolumn` placeholders that span active multirow columns.
- **Lines 216–240**: `colspan` / `rowspan` attribute emission (`colspan > 1`, `rowspan > 1`), border application on multicolumn cells.
- **Lines 266, 274–275**: column `right_borders` and `has_left_border` rendering paths.

### 10. `scriba/animation/_minify.py` — 74.3% line, 83.3% branch

**File:** `scriba/animation/_minify.py`

- **Lines 28–35**: `_minify_css` — the four regex passes (`_re.sub`) inside the function body. No dedicated unit test for this function exists; it is only reached via `_minify_html`.
- **Lines 81–83**: `_minify_style_block` fast-path bypass — when a `<style>` block has fewer than 50 newlines and no double-newlines, the expensive CSS minification is skipped. This is a performance-critical branch (described in the comment as "56% of total render time saved") but has no test confirming the bypass fires or that it produces correct output.
- **Lines 95–107**: `_minify_script_block` closure — the inner function that minifies `<script>` content is never independently tested.

---

## 4. Test Quality Findings

| Severity | Location | Issue | Fix |
|----------|----------|-------|-----|
| HIGH | `tests/unit/test_a11y_aria_live.py:108`, `tests/unit/test_contrast.py:100`, and ~30 other files | `@pytest.mark.unit` is applied across 30+ test functions but the mark is not registered in `pyproject.toml`. Pytest emits 83 `PytestUnknownMarkWarning` warnings each run and `-m unit` filtering is silently broken — running `pytest -m unit` matches nothing. | Add `markers = ["unit: unit tests", "integration: integration tests"]` to `[tool.pytest.ini_options]` in `pyproject.toml`. |
| HIGH | `tests/animation/`, `tests/integration/` | Only 5 integration test files exist (79 test functions) vs 92 unit test files (1,860 functions). The integration layer hits `AnimationRenderer.render_block()` for Array, DpTable, Graph, Tree, and a few others but not Queue, Stack, Hashmap, Linkedlist, Numberline, Metricplot, or Variablewatch as complete pipeline renders. | Add integration-level render tests for the 7 missing primitive types covering at least `detect → render_block → valid HTML` with real `RenderContext`. |
| HIGH | `tests/` (entire suite) | No E2E browser tests exist. The rendered HTML contains `<script>` blocks with animation runtime JS, ARIA live regions, and keyboard navigation. None of this behaviour is exercised in a browser — only string assertions on raw HTML. | Add Playwright smoke tests for: (1) animation stepping via keyboard, (2) ARIA counter updates, (3) static filmstrip rendering on a real DOM. |
| MEDIUM | `tests/unit/test_animation_renderer.py` | `_materialise_substory` (lines 600–651 of `renderer.py`) is entirely absent from tests. The nested-substory path (`depth > 1`) and substory-local `\shape` declarations are uncovered. The only integration test for substories checks HTML string presence, not the substory data structure. | Add unit tests for `AnimationRenderer._materialise_substory` with a substory that contains local shapes and a nested substory (depth 2). |
| MEDIUM | `tests/unit/test_animation_emitter.py` | `emitter.py` lines 198–213 — the `_inject_node_positions` function — is not covered. This function is the bridge between tree/graph mutations and smooth `position_move` animation transitions. | Add a test that renders a tree with an `add_node` command across frames and asserts `x`/`y` appear in `frame.shape_states`. |
| MEDIUM | `tests/tex/` | `tex/parser/math.py` — the `render_math_batch` error path with `strict=False` (lines 142–152) and the `_preprocess_text_command_chars` body (lines 44–50) are uncovered. The `\text{a_b}` preprocessing is a user-facing correctness concern. | Add: `test_text_command_underscore_escaped` using a `\text{a_b}` expression, and `test_render_math_batch_error_nonstict` mocking the KaTeX worker to return `{"error": "...", "html": null}`. |
| MEDIUM | `tests/unit/` (no dedicated file) | `_minify.py` has no dedicated test file. The `_minify_style_block` performance bypass (fast-path at lines 101–104) is uncovered. If the fast-path regresses it silently ships un-minified KaTeX CSS in every render, doubling output size. | Create `tests/unit/test_minify.py` with: (1) `_minify_css` unit tests including comment removal and semicolon stripping, (2) `_minify_js` URL-preservation test (`://` pattern), (3) `_minify_html` with a `<pre>` block and a `<style>` block short enough to hit the fast-path. |
| MEDIUM | `tests/unit/test_primitive_plane2d.py` | `plane2d.py` missing 132 lines. The `get_svg_position` method's line/segment/polygon branches (lines 550–595) are uncovered — annotation arrows on non-point targets silently return `None`, producing arrows that render to the origin. | Add tests for `p.get_svg_position("line[0]")`, `"segment[0]"`, and `"polygon[0]"` after adding the corresponding geometric elements. |
| LOW | `tests/unit/test_starlark_host.py` | `starlark_host.py:94–125` — `_set_resource_limits` is not tested. This runs as `preexec_fn` in a subprocess and cannot be called directly on macOS/Linux without forking. The `OSError` exception suppression branches (lines 103–112) and the `RLIMIT_CPU` split soft/hard limits (lines 119–125) are invisible to the test suite. | Add a test that monkeypatches `resource.setrlimit` to raise `OSError` and calls `_set_resource_limits()` directly — verifying the logger.debug path fires and no exception propagates. |
| LOW | `tests/unit/test_whitelist.py` | `sanitize/whitelist.py` reports 100% line coverage on the 4-statement module, but the whitelist policy itself (the full `ALLOWED_TAGS`/`ALLOWED_ATTRIBUTES` dict) is only tested structurally. No test renders a document containing a newly-safelisted tag (e.g. `<details>`, `<summary>`) and verifies it survives the sanitize pass end-to-end after a future whitelist addition. | Add a round-trip integration test: render LaTeX → sanitize output → assert all expected tags survive and a known-dangerous tag (`<script>`) is stripped. |
| LOW | `tests/` (suite-wide) | Session-scoped fixtures in `tests/conftest.py` (`worker_pool`, `tex_renderer`, `pipeline`) share a single subprocess worker across all tex tests. A worker crash mid-suite would corrupt subsequent tests. There is no explicit teardown test or isolation check. | Add a test that intentionally sends a malformed request to the shared worker pool and verifies the pool auto-recovers without poisoning later tests in the same session. |

---

## 5. Top 3 Priorities

### Priority 1 — Add snapshot/golden tests for the `_render_svg_text` foreignObject path

`scriba/animation/primitives/_text_render.py` is at 55.7% coverage and the `<foreignObject>` slow path (lines 234–291) has zero tests. This code path is the sole mechanism for rendering KaTeX math inside SVG animations. A regression here produces broken SVG silently — math labels will appear as empty or malformed `<foreignObject>` elements.

Recommended tests in a new `tests/unit/test_text_render.py`:

1. `test_render_svg_text_no_math_plain` — text with no `$`, verifies `<text>` element returned.
2. `test_render_svg_text_with_math_foreignobject` — text `"val = $x^2$"` with a mock `render_inline_tex` callback, verifies `<foreignObject>` is emitted with correct `x`/`y` positioning.
3. `test_render_svg_text_text_anchor_start_end` — both `text_anchor="start"` and `text_anchor="end"` in the foreignObject path to cover `fo_x` calculation branches (lines 245–251).
4. `test_render_svg_text_deprecation_warning` — passing `text_outline="white"` triggers `DeprecationWarning` (lines 218–232).
5. `test_render_mixed_html_escaped_dollar_sentinel` — input `"price \\$5 and $x$"` verifies the sentinel prevents the escaped dollar pairing with the math dollar.
6. `test_estimate_text_width_zwj_sequence` — input `"👨‍👩‍👧"` (family emoji with ZWJs) verifies the ZWJ cluster is counted as one 1.0 em unit (lines 74–82).

### Priority 2 — Cover the `_materialise_substory` path and nested substory in `animation/renderer.py`

`animation/renderer.py` is at 74.0% and the substory materialisation path (lines 600–651) represents the most complex rendering branch in the system. Specifically, the combination of substory-local shapes (`sub_primitives` at lines 608–614) and depth-2 nested substories (lines 623–630) is completely absent from tests. Regressions here are invisible until a user renders an animation with nested substories that declare local primitives.

Recommended tests added to `tests/unit/test_animation_renderer.py` or a new `tests/integration/test_substory_materialise.py`:

1. `test_substory_local_shape_is_instantiated` — animation block with a substory containing a `\shape` declaration; assert `sub_primitives` dict is populated.
2. `test_nested_substory_depth_2` — frame with a substory that itself has a nested substory; assert depth=2 `SubstoryData` is present in the outer substory's frames.
3. `test_substory_label_passthrough` — labeled substory frame (`\step[label="step title"]`) verifies `sub_label` is propagated to `FrameData`.

### Priority 3 — Register pytest marks and add a `tests/unit/test_minify.py`

Two independent but quick wins that together remove 83 recurring warnings and add coverage to an unprotected performance-critical module.

**3a — Register marks** (5-line change to `pyproject.toml`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: fast isolated unit tests",
    "integration: tests that spawn subprocesses or do full pipeline renders",
    "slow: tests that take > 500 ms",
]
```

This makes `pytest -m unit` functional, silences all 83 warnings, and lets CI skip slow tests on fast feedback loops.

**3b — Create `tests/unit/test_minify.py`** with:

1. `test_minify_css_removes_comments` — `/* foo */ body { color: red; }` → `body{color:red}`.
2. `test_minify_css_strips_trailing_semicolon` — `a { color:red; }` → `a{color:red}`.
3. `test_minify_js_preserves_url` — a line containing `https://example.com` is not stripped.
4. `test_minify_js_strips_comment` — `var x = 1; // comment` → `var x = 1;`.
5. `test_minify_html_pre_block_preserved` — content inside `<pre>` is not whitespace-collapsed.
6. `test_minify_html_style_block_fast_path` — a `<style>` block with fewer than 50 newlines and no double-newlines verifies the fast-path fires (mock `_minify_css` and assert it is NOT called).
7. `test_minify_html_style_block_slow_path` — `<style>` with 60+ newlines verifies `_minify_css` IS called.
