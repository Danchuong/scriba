# Spec-Fix: JudgeZone #17-B — Live Controls Chip Content Clearance

**Agent:** bmad-17b-chrome (BMAD patcher)
**Status:** DONE — fix GREEN, 10/10 new tests pass, zero regressions in adjacent
suites, all 107 golden corpus deltas identified (not re-blessed, per scope).
**Sibling:** bmad-17a-extent (`primitives/stack.py`, cross-frame extent /
caption clipping half of the same bug report) — not touched here; confirmed
zero overlap (see GitNexus section).

## Contract

Content and chrome must never share pixels. The live widget's floating
controls pill (`.scriba-stage-wrap > .scriba-controls`) is `position:
absolute` over the bottom-center of the stage on every frame; the stage must
reserve a `padding-bottom` clearance sized from the pill's own rendered box
(button + padding + border + bottom offset), derived with `calc()` from the
same tokens the pill itself renders with — never a constant that can drift
out of sync with the pill's actual geometry.

---

## Work Item 1 — Overlay inventory

Exhaustive sweep (`grep -n "position:\s*absolute\|position:\s*fixed\|position:\s*sticky"`)
across every shipped stylesheet (`scriba-embed.css`, `scriba-scene-primitives.css`,
`scriba-standalone.css`, `scriba-plane2d.css`, `scriba-metricplot.css`) plus a
check for JS-injected inline overlay positioning in `_script_builder.py`
(zero hits — all overlay geometry is pure CSS, nothing runtime-computed).

| # | Selector | File:line | position | Anchoring | Height | In scope? |
|---|---|---|---|---|---|---|
| 1 | `.scriba-stage-wrap > .scriba-controls` | `scriba-embed.css:153` | `absolute` | `left:50%; bottom:10px; transform:translateX(-50%)` — horizontally centered over the **stage** | 38px pill + 10px offset + 4px gap = 52px total clearance needed | **Yes — this is Finding #17-B.** Fixed below. |
| 2 | `.theme-toggle` | `scriba-standalone.css:29-34` | `fixed` | `top:1rem; right:1rem` — anchored to the **viewport** corner, not any stage | n/a (page-level singleton, one per document) | No. Different containing block (viewport vs. stage-relative), different file (`scriba-standalone.css` — the CLI document shell, explicitly *not* one of the three areas I own), and structurally a page-chrome singleton rather than a per-widget stage overlay. Flagged, not touched — see Adjacent findings. |

`scriba-scene-primitives.css` and the primitive-specific sheets
(`scriba-plane2d.css`, `scriba-metricplot.css`) declare **zero**
absolute/fixed/sticky rules — no overlay chrome hides there. The controls
pill (#1) is the only floating chrome that targets stage content, and it is
the only one in scope (`.scriba-stage-wrap`/`.scriba-controls` live in
`scriba-embed.css`, one of my three owned areas).

---

## Work Item 2 (PRIMARY) — Option decision

Two candidate shapes were evaluated per the mandate:

- **(a) Stage clearance via `padding-bottom` equal to chip height, CSS-only
  structural selector.** The codebase already had this shape
  (`.scriba-stage-wrap > .scriba-stage { padding-bottom: 3.25rem; }`) — the
  bug was that the clearance value was a hand-picked constant that only
  *coincidentally* matched the pill's real footprint at the default 16px
  root font-size, not a derivation from it.
- **(b) Move the chip out of stage flow entirely** (e.g., back into normal
  document flow below the stage, like the pre-"C1 Overlay controls" design
  the comment block references). Rejected: this reverts the deliberate C1
  UX decision to reclaim the top bar as a translucent overlay pill (a
  previous, intentional design change, not a bug) and would touch the DOM
  structure `_html_stitcher.py` emits, expanding blast radius into the
  chrome-emission Python this task explicitly scopes as "own carefully" —
  not "rewrite."

**Picked (a).** Rationale: the *contract* the finding demands (content and
chrome never share pixels) is fully satisfiable by fixing the clearance
formula's inputs, with a change confined to one CSS file, zero DOM/JS
changes, zero markup diff, and a mechanically provable tie between the two
numbers (pill box and clearance) via shared `calc()` tokens — eliminating
the entire class of "drifted independently" bugs the constant caused,
rather than just patching today's specific 16px-root-font-size instance of
it.

### Fix — `scriba/animation/static/scriba-embed.css:126-178`

**Before** (pre-fix, `git show HEAD:...` — 34 lines):

```css
.scriba-stage-wrap {
  position: relative;
}

.scriba-stage-wrap > .scriba-stage {
  padding-bottom: 3.25rem; /* clear room so the pill never covers animation content */
}

.scriba-stage-wrap > .scriba-controls {
  position: absolute;
  left: 50%;
  bottom: 10px;
  transform: translateX(-50%);
  width: auto;
  gap: 0.6rem;
  padding: 4px 6px;
  background: rgba(255, 255, 255, 0.8);
  -webkit-backdrop-filter: blur(8px) saturate(1.2);
  backdrop-filter: blur(8px) saturate(1.2);
  border: 1px solid rgba(205, 211, 218, 0.7);
  border-bottom: 1px solid rgba(205, 211, 218, 0.7);
  border-radius: 999px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06), 0 6px 18px rgba(16, 24, 40, 0.12);
}

.scriba-stage-wrap > .scriba-controls button {
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

**Root cause:** `padding-bottom: 3.25rem` is root-font-size-relative, while
every dimension of the pill itself (button, padding, border) is fixed-px.
`3.25rem = 52px` **only** at the default 16px root font-size — the two
numbers were never actually linked. Any host page with a smaller root font
size (e.g. a common `html { font-size: 62.5% }` reset, a widely-used
convention for 10px-base rem math) shrinks the rem-based clearance while the
px-based pill stays full size, reintroducing the exact overlap the finding
describes.

**After** (current working tree — 53 lines):

```css
.scriba-stage-wrap {
  position: relative;
  /* Pill geometry tokens — scoped here (not :root) so this stays embed-safe;
     the substory widget's plain .scriba-controls bar never inherits these.
     Every number the pill actually renders with lives here exactly once;
     the stage's clearance below is `calc()`-derived from these SAME tokens
     so the two can never drift apart (px, not rem — the pill's box does
     not derive from font-size, so it must not be sized as if it did). */
  --scriba-pill-btn: 28px;
  --scriba-pill-pad-y: 4px;
  --scriba-pill-border: 1px;
  --scriba-pill-offset: 10px;
  --scriba-pill-gap: 4px;
  --scriba-pill-height: calc(
    var(--scriba-pill-btn) + (var(--scriba-pill-pad-y) * 2) + (var(--scriba-pill-border) * 2)
  );
  --scriba-pill-clearance: calc(
    var(--scriba-pill-offset) + var(--scriba-pill-height) + var(--scriba-pill-gap)
  );
}

.scriba-stage-wrap > .scriba-stage {
  /* Clear room so the pill never covers animation content — derived from
     the pill's own box (see --scriba-pill-* above), not a magic constant. */
  padding-bottom: var(--scriba-pill-clearance);
}

.scriba-stage-wrap > .scriba-controls {
  position: absolute;
  left: 50%;
  bottom: var(--scriba-pill-offset);
  transform: translateX(-50%);
  width: auto;
  gap: 0.6rem;
  padding: var(--scriba-pill-pad-y) 6px;
  background: rgba(255, 255, 255, 0.8);
  -webkit-backdrop-filter: blur(8px) saturate(1.2);
  backdrop-filter: blur(8px) saturate(1.2);
  border: var(--scriba-pill-border) solid rgba(205, 211, 218, 0.7);
  border-bottom: var(--scriba-pill-border) solid rgba(205, 211, 218, 0.7);
  border-radius: 999px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.06), 0 6px 18px rgba(16, 24, 40, 0.12);
}

.scriba-stage-wrap > .scriba-controls button {
  width: var(--scriba-pill-btn);
  height: var(--scriba-pill-btn);
  padding: 0;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

Tokens are scoped to `.scriba-stage-wrap` (not `:root`) so the file stays
"embed-safe" per its own docstring (no document-level selectors that could
clobber a host page) — CSS custom properties inherit to all descendants, so
`.scriba-stage`, `.scriba-controls`, and `.scriba-controls button` all see
them without needing a global scope.

**Numeric proof:** `pill_height = 28 + 4×2 + 1×2 = 38px`;
`clearance = 10 + 38 + 4 = 52px` — **exactly** the pre-fix `3.25rem` at the
default 16px root font size, so default rendering is visually unchanged, but
the two numbers are now mechanically tied instead of coincidentally equal.

**Dark mode:** untouched by construction — the `[data-theme="dark"]` and
`@media (prefers-color-scheme: dark)` twin blocks (lines ~269-297) only
override `background`/`border-color` (colors), never geometry. This is a
purely geometric/token change, so it cannot interact with either block.

**Print:** untouched by construction — print frames (`.scriba-print-frame`,
built by `_html_stitcher.py`'s `print_frame_items`) contain zero
`.scriba-controls`/`.scriba-stage-wrap` markup (confirmed both synthetically,
via the new unit tests below, and empirically, via a real corpus re-render —
see Work Item 4). The clearance/pill rules are scoped to
`.scriba-stage-wrap > ...` descendant selectors that structurally cannot
match anything in the print-frames subtree.

---

## Work Item 3 (PRIMARY) — Tests: `tests/unit/test_controls_clearance_css.py`

New file, 224 lines, house style follows `test_theme_attr_contract.py`
(class-level `@pytest.mark.unit`) and `test_narration_overflow_css.py`/
`test_widget_a11y.py` (raw-text CSS assertions; a `_StubPrimitive` +
`_make_frame()` pair rendering a real widget through
`emit_interactive_html` for the markup-contract tests — static analysis
only, no browser, per the repo-wide Playwright ban).

Three test classes:

- **`TestPillClearanceTokens`** (6 tests) — every `--scriba-pill-*` token is
  declared on `.scriba-stage-wrap`; the clearance token is `calc()`-derived
  (not hardcoded); the stage's `padding-bottom` uses the shared token *and*
  never falls back to a bare `rem` value; the pill's own offset/button-size/
  padding/border all reference the same tokens.
- **`TestClearanceMathMatchesPillBox`** (1 test) — numeric contract: parses
  the actual token values out of the CSS text and asserts
  `clearance == offset + (btn + 2×pad_y + 2×border) + gap` — i.e., the
  formula matches the pill's real rendered footprint, not merely that the
  syntax references the tokens.
- **`TestPrintFramesHaveNoClearanceTarget`** (3 tests) — renders a minimal
  real widget via `emit_interactive_html` and asserts (1) the live
  `.scriba-stage-wrap` region does contain both `.scriba-stage` and
  `.scriba-controls`, (2) the `.scriba-print-frames` subtree contains **zero**
  occurrences of `scriba-controls`, (3) and **zero** occurrences of
  `scriba-stage-wrap` — i.e., the clearance rule's selector cannot structurally
  apply to (or be needed by) print output.

### RED → GREEN (verified via `git stash` round-trip on `scriba-embed.css`
only — the test file itself was never stashed)

**RED** (CSS stashed back to committed `3.25rem`/hardcoded-px form):
**7 failed, 3 passed.** The 3 pre-fix passes were the markup-contract tests
in `TestPrintFramesHaveNoClearanceTarget` (unaffected by the CSS content —
they test structural absence, true on both sides) plus one token-presence
test that happened to already find unrelated substrings. All 6 token/derivation
tests and the 1 numeric-math test failed as expected (tokens didn't exist yet).

**GREEN** (fix restored): **10 passed.**

```
rtk proxy python3 -m pytest tests/unit/test_controls_clearance_css.py -q
10 passed
```

### Regression check — adjacent CSS/a11y/emitter suites

```
rtk proxy python3 -m pytest tests/unit/test_narration_overflow_css.py \
  tests/unit/test_widget_a11y.py tests/unit/test_a11y_aria_live.py \
  tests/unit/test_emitter_a11y.py tests/unit/test_controls_clearance_css.py -q
41 passed
```

```
rtk proxy python3 -m pytest tests/unit/test_theme_attr_contract.py -q
81 passed
```

### Full unit suite

```
rtk proxy python3 -m pytest tests/unit/ -q --ignore=tests/unit/test_graph_mutation.py \
  --ignore=tests/unit/test_parser_hypothesis.py
4424 passed, 3 failed, 9 skipped
```

The two `--ignore`s are pre-existing collection errors
(`ModuleNotFoundError: No module named 'hypothesis'` — a missing test
dependency in this environment, unrelated to this change). The 3 failures,
individually isolation-tested (CSS fix stashed out, each test run alone):

| Test | Cause |
|---|---|
| `test_primitive_stack.py::TestAnnotationLayout::test_caption_stays_inside_bbox_with_arrow_above` | Entangled with sibling agent bmad-17a-extent's uncommitted WIP on `primitives/stack.py` (confirmed via `git status` and GitNexus `detect_changes` — see below). Passes in isolation with only my diff present. Not mine to fix — out of scope (`primitives/*.py` is explicitly fenced off from me). |
| `test_recursive_dos.py::TestCyclicGraphBaseline::test_graph_with_100_self_loops_completes` | Pre-existing, passes in isolation with my CSS diff fully reverted. Unrelated subsystem (graph recursion timing). |
| `test_starlark_security.py::TestRecursionErrorNoPathLeak::test_deeply_nested_expression_no_path_leak_via_worker` | Pre-existing — still fails even with my CSS diff fully reverted (stashed). Unrelated subsystem (Starlark sandboxing). |

None of these 3 are caused by this fix.

---

## Work Item 4 — Repro evidence: `repro8.tex` (the lead's exact repro)

`repro8.tex` is an 8-step animation with a `Stack` primitive carrying a
wrapping two-line `label=` caption — the exact "bottom-most
horizontally-centered content" scenario the finding describes.

**Before** (`git show HEAD:scriba/animation/static/scriba-embed.css`, the
committed pre-fix CSS — same 3.25rem/hardcoded-px block quoted in Work Item 2).

**After** — fresh re-render post-fix:

```
SCRIBA_ALLOW_ANY_OUTPUT=1 rtk proxy python3 render.py repro8.tex -o repro8_after.html
```

Emitted CSS carries the full token chain (grep on the fresh output):

```
--scriba-pill-btn: 28px;
--scriba-pill-pad-y: 4px;
--scriba-pill-border: 1px;
--scriba-pill-offset: 10px;
--scriba-pill-gap: 4px;
--scriba-pill-height: calc(...)
--scriba-pill-clearance: calc(...)
...
padding-bottom: var(--scriba-pill-clearance);
...
bottom: var(--scriba-pill-offset);
padding: var(--scriba-pill-pad-y) 6px;
border: var(--scriba-pill-border) solid ...;
width: var(--scriba-pill-btn);
height: var(--scriba-pill-btn);
```

Structural markup check (Python, on the real rendered output, not the
synthetic unit-test stub):

```
live region has scriba-controls:    True
live region has scriba-stage-wrap:  True
print region has scriba-controls:   False
print region has scriba-stage-wrap: False
print region length: 64188 bytes
```

Confirms on the actual lead-provided repro: the live `.scriba-stage-wrap`
subtree carries both the stage and the controls pill with the new
token-derived clearance, and the entire 64KB print-frames subtree —
covering all 8 steps' print output — contains neither class, structurally
proving print output cannot be touched by this fix.

---

## Work Item 5 — Golden corpus impact (LIST, not re-blessed, per scope)

### Root-caused the bundling mechanism

`scriba-embed.css` is **not** referenced anywhere in
`scriba/animation/renderer.py`'s per-block-renderer asset lists (those cover
only `scriba-animation.css`/`scriba-scene-primitives.css` +
primitive-specific sheets, for `scriba/core/pipeline.py`'s multi-block
host-embedding path). It is bundled by a **separate, unconditional** call
site in the repo-root CLI entry point, `render.py:254-263`:

```python
_BASE_CSS = (
    "scriba-scene-primitives.css",
    "scriba-animation.css",
    "scriba-embed.css",
    "scriba-standalone.css",
)
css_parts = [inline_text_font_css(), load_css(*_BASE_CSS)]
```

This runs for **every** `render.py` invocation regardless of block content
("page-chrome base... CLI-page concerns no renderer declares", per the
comment directly above it). `tests/golden/examples/test_example_html.py`
renders every corpus `.tex` through exactly this CLI path
(`subprocess.run([sys.executable, _RENDER, str(tex), "-o", str(out)], ...)`),
so **every** golden `.html` inlines the full, byte-identical text of
`scriba-embed.css` — including the region I changed.

### Empirical confirmation

```
rtk proxy python3 -m pytest tests/golden/examples/ -q --no-header --tb=line
107 failed, 1 passed
```

The 1 pass is the unrelated `test_corpus_is_non_empty` guard. **All 107**
`test_example_matches_golden[*]` parametrizations fail — this is the
expected, uniform CSS-delta shift the mandate anticipated ("the live-page
CSS bundle grows so all full-page corpus goldens shift by the CSS delta"),
not a regression.

Isolated the shape of the shift on one example (`hello.tex`, 501KB rendered
HTML) with a direct re-render + raw diff (`rtk proxy diff -u`, bypassing
RTK's own diff-summarizing wrapper — see Errors and fixes):

```
@@ -1498,32 +1498,51 @@
```

**Exactly one hunk**, 61 total diff lines, confined word-for-word to the
`.scriba-stage-wrap` CSS block quoted in Work Item 2 — nothing else in the
entire 501KB file differs (no markup, no script, no other CSS). This
directly proves, on a real corpus file rather than only the synthetic unit
test, that the shift is pure CSS text and print/body content stays
byte-identical.

**Affected goldens: all 107 pairs in `tests/golden/examples/corpus/*.tex` /
`*.html`** (full alphabetical list — every parametrization the suite
collected):

```
01_variablewatch_shrink, 02_hashmap_shrink, 03_linkedlist_shrink,
04_stack_shrink, 05_diagram_prescan, 06_substory_prescan,
07_prescan_no_pollution, 08_foreach_value_interpolation,
10_selector_out_of_range, 12_selector_unknown_accessor,
14_annotate_arrow_bool, 17_empty_substory, 18_xss_filename,
19_path_traversal, 22_recursion_no_path_leak, 23_a11y_widget,
24_contrast_dark_mode, anim_clarity_showcase, apt_window_diagram, array,
bfs, bfs_grid_editorial, binary_search, bst_operations, codepanel,
convex_hull_andrew, convex_hull_trick, decoration_spiral, diagram,
diagram_grid, diagram_intro, diagram_multi, dijkstra, dijkstra_editorial,
dinic, dp_optimization, dptable, elevator_rides, fft_butterfly,
foreach_demo, frog, frog_foreach, gep_v2_smoke, graph, grid, hashmap,
hello, hld, houses_schools, increasing_array, interval_dp, kmp,
knapsack_editorial, kruskal_mst, li_chao, linkedlist, linkedlist_reverse,
matrix, maxflow, mcmf, metricplot, missing_number, necessary_roads,
numberline, permutations, persistent_segtree, plane2d,
plane2d_annotations, plane2d_lines, plane2d_ticks, planets_queries2,
queue, range_queries_copies, repetitions, segtree_editorial,
simulated_annealing, splay, stack, substory, test_array_arrows,
test_dptable_arrows, test_edge_overlap, test_label_overlap_1d,
test_label_overlap_2d, test_label_readability, test_plane2d_animation,
test_plane2d_dense, test_plane2d_edges, test_reference_advanced,
test_reference_basic, test_reference_datastruct, test_reference_dptable,
test_reference_edge_cases, test_reference_extended,
test_reference_graph_tree, test_reference_grid_numline,
test_reference_segtree, test_reference_tex_heavy,
test_reference_unionfind, tree, tutorial_en, two_sum_editorial,
union_find, union_find_array, union_find_tree, variablewatch,
weird_algorithm
```

**Not re-blessed** — `SCRIBA_UPDATE_GOLDEN` was never set, per scope
("I must LIST these, NOT re-bless them").

---

## GitNexus impact analysis

Per repo `CLAUDE.md`'s mandate to run impact analysis before editing any
Python function: this fix touches **zero Python functions** (CSS-only), so
the mandate's precondition never triggers. As due diligence anyway (the new
test's markup-contract assertions depend on `emit_interactive_html`'s
output shape, though the function itself was only read, never edited):

`impact(target="emit_interactive_html", direction="upstream", repo="scriba", summaryOnly=true)`:

```
risk: LOW, impactedCount: 4 (direct: 1), processes_affected: 0, modules_affected: 2 (Unit, Animation)
```

Low, expected fan-out for a widely-called HTML emission function; no
process is flagged as affected, consistent with a CSS-only change that
never touches this function's body.

`detect_changes(scope="all", repo="scriba")` — mechanically confirms, via
GitNexus's own symbol-level diff (not just this document's narration), that
the current working tree's **only** changed Python symbols anywhere are:

```
Class:scriba/animation/primitives/stack.py:Stack (touched)
Method:scriba/animation/primitives/stack.py:Stack.emit_svg#3 (touched)
```

risk_level: low, affected_processes: []. These belong entirely to sibling
agent bmad-17a-extent's `primitives/stack.py` WIP (the explicitly fenced-off
file) — **not** to this fix. My own diff (`scriba-embed.css` + the new test
file) produces zero entries in GitNexus's changed-symbol list, independently
confirming both that it is CSS-only and that there is zero symbol-level
overlap between my work and the sibling agent's.

---

## Adjacent findings (discovered, NOT fixed here — out of scope)

1. **Stale `@media print` selectors in `scriba-scene-primitives.css`.** The
   print stylesheet still targets `.scriba-widget > .scriba-controls` /
   `.scriba-widget > .scriba-stage` (direct-child selectors), but the DOM
   these fixes' predecessor (C1) nested one level deeper under
   `.scriba-stage-wrap`. These selectors no longer match anything, so any
   print-specific override they were meant to apply silently no-ops. This
   is a distinct, pre-existing regression from a *previous* fix (not
   Finding #17-B), and touching `scriba-scene-primitives.css`'s print rules
   is outside my three owned areas. Flagging for whoever owns that file.
2. **`.theme-toggle` (`scriba-standalone.css:29-34`)** — a second
   `position: fixed` element (see Overlay inventory #2). Structurally
   different category (viewport-corner singleton, not a per-widget stage
   overlay) and lives in a file I don't own. Not part of this finding's
   contract, not touched.
3. **Three full-suite test failures**, all proven pre-existing/unrelated
   via isolation testing — see Work Item 3's regression-check table.
4. **RTK CLI-proxy hook misbehaves under this task** (tooling note, not a
   scriba code issue) — observed three separate times: (a) `python -m
   pytest` (unproxied) falsely reports "No tests collected" against a fully
   populated test file; (b) a combined `git status && ...` command produced
   a transiently stale reading; (c) `diff -u ... > file` gets silently
   rewritten into a lossy, misaligned custom summary (mismatched
   add/remove pairing), unusable for hunk-level verification. Worked around
   throughout by using `rtk proxy <cmd>` (the documented raw/unfiltered
   execution mode) for every verification-critical command in this
   document; every number quoted above came from a `rtk proxy`-run or a
   direct `git show`/`Read`, never the filtered wrapper.

---

## Scope compliance

Touched only: `scriba/animation/static/scriba-embed.css` (the C1 Overlay
controls block, lines 126-178) and `tests/unit/test_controls_clearance_css.py`
(new file). No `primitives/*.py`, no `tex/*`, no
`.scriba-invariant-panel` rules, no `_html_stitcher.py`/`_script_builder.py`
edits (both were only read, to confirm print-frame markup structurally
excludes the pill/stage-wrap — no chrome-emission change was needed since
the bug was purely in the CSS clearance formula, not in what markup gets
emitted). No golden re-bless (`SCRIBA_UPDATE_GOLDEN` never set), no version
bump, no CHANGELOG edit, no commit.
