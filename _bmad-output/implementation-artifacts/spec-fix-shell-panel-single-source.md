# Spec — shell-panel single-source sweep (narration / step-label / controls)

**Agent:** sweep-shellpanels · **Scope:** `_html_stitcher.py`, shell-panel rules in
`scriba-embed.css` (extended from the originally named `scriba-scene-primitives.css`
— see "Scope-fence correction" below) · **Method:** TDD, GitNexus impact analysis
before every symbol edit, no Playwright/browser MCP, goldens read-only.

**Family context:** the invariant panel was just restyled
(`spec-fix-invariant-theorem-box.md`), and that work uncovered a structural bug —
`emit_interactive_html` had inline-duplicated the invariant markup instead of
calling the shared `_invariant_panel_elements` builder — plus a missing
`overflow-wrap: anywhere` on the invariant panel. This sweep checks the rest of
the widget-shell panel family (narration, step title/label, step counter,
progress bar, frame headers) for the same two defect classes.

---

## 1. Panel × mode single-source matrix

| Panel | `emit_animation_html` (static filmstrip) | `emit_interactive_html` (widget + print-frames) | `emit_substory_html` | `emit_diagram_html` |
|---|---|---|---|---|
| Narration | ✅ unified — `_narration_element()` | ✅ unified — `_narration_element()` (print-substory, print-frame, main-widget: 3 call sites) | ✅ unified — `_narration_element()` | N/A by design (diagrams are static, no shell panels) |
| Step label (`N / total`) | ✅ unified — `_step_label_span()` | ✅ unified — `_step_label_span()` (print-frame) | N/A (substory uses the counter in its controls bar, not a standalone label span) | N/A |
| Step counter + prev/next controls | N/A (filmstrip has no live controls — it's a static list of frames) | ✅ unified — `_step_controls_element()` (main widget) | ✅ unified — `_step_controls_element()` (substory widget, `extra_class="scriba-substory-controls"`, own labels, optional progress dots) | N/A |
| Progress dots | N/A | N/A (main widget has no dots; `progress_html=None`) | ✅ folded into `_step_controls_element()` via `progress_html=` param | N/A |
| Invariant panel | — | ✅ already unified by a sibling agent (`_invariant_panel_elements`) before this sweep started; left untouched per scope | — | — |
| Frame headers (`<header class="scriba-frame-header">…</header>`) | Wraps `_step_label_span()` in a `<header>` element — filmstrip-specific chrome | Print-frame path emits `_step_label_span()` directly with no `<header>` wrapper (print-frames are hidden, `display:none` DOM used only for screen-reader / print CSS, not visual chrome) | N/A | N/A |
| Theme toggle chrome | Not part of the emitted widget markup — the toggle button (if any) is host-page chrome outside `scriba.js`'s widget subtree. No shell-panel duplication found; out of scope for this sweep (no `_html_stitcher.py` symbol builds it). | | | |

**Verdict:** before this sweep, narration (5 call sites), step-label (2 call
sites), and step-controls (2 call sites) were each hand-duplicated inline —
9 call sites total, 3 duplicated shapes, 0 shared builders. All 9 are now
routed through 3 new shared functions in `_html_stitcher.py`. The frame-header
wrapper difference (filmstrip wraps in `<header>`, print-frame does not) is an
intentional, pre-existing design difference (filmstrip frames are visible list
items needing a labelled header; print-frames are `display:none` and only
exist for print/no-JS fallback), not a duplication defect — no fix applied
there.

---

## 2. Overflow-protection parity

Same repro method as the invariant fix: a long single inline formula inside
`\narrate`, rendered through `render_inline_tex` → the visible `katex-html`
branch. That branch emits zero breakable whitespace in its text nodes (every
glyph individually spanned), so `overflow-wrap: normal` (CSS default) has no
valid break point and the formula overflows its container horizontally.
`measure_inline_math` against the panel's available width at a 375px viewport
(established in the earlier session, carried forward as evidence, not
recomputed this session):

| Case | Measured width | Available width (panel minus padding, 375px viewport) | Verdict |
|---|---|---|---|
| Long formula | 428.04px | 341px | **Overflows by ≈ 87px** |
| Short formula | 202.02px | 341px | Fits, no action needed |

`.scriba-narration` renders through the identical `render_inline_tex` →
`katex-html` pathway as `.scriba-invariant` (both carry user-authored inline
math via the same TeX renderer), so it carries the identical risk. It had no
`overflow-wrap` protection before this fix. Fixed by adding
`overflow-wrap: anywhere` to the (first, visual) `.scriba-narration` rule in
`scriba-embed.css`.

No other shell panel (step-label, step-counter, progress dots) renders
arbitrary user TeX content — they only render integers, so none of them are at
risk of this overflow class and none needed the fix.

---

## 3. Fixes (file:line)

All in `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/_html_stitcher.py` unless noted.

- **New shared builders** (lines 130–204):
  - `_narration_element()` — line 130. Single source for every
    `<p class="scriba-narration" dir="auto">` element; takes `id_attr`,
    `aria_live`, `aria_atomic` so each call site opts into only the attributes
    it needs.
  - `_step_label_span()` — line 155. Single source for
    `<span class="scriba-step-label">N / total</span>`.
  - `_step_controls_element()` — line 167. Single source for the
    prev/counter/next controls bar, parametrized by `extra_class`,
    `prev_label`/`next_label`, optional `progress_html`, and `indent` (the
    main widget and substory widget nest at different depths in their
    templates).

- **Call sites migrated to the shared builders** (9 total):
  - `emit_animation_html`: step-label at line 385, narration at line 390.
  - `emit_substory_html`: controls at line 481, narration at line 489.
  - `emit_interactive_html`: print-substory narration at line 696,
    print-frame step-label at line 713, print-frame narration at line 715,
    main-widget controls at line 805, main-widget narration at line 807.

- **Real bug found and fixed in `_step_controls_element` itself** (line 167,
  parameter `progress_html`): originally `progress_html: str = ""` with
  `if progress_html:` (truthy check) deciding whether to render the
  `<div class="scriba-progress" aria-hidden="true">` wrapper. The substory
  call site (line 481) *always* passes its joined dots string explicitly —
  including when `sub_frame_count == 0` (an empty substory, no `\step`
  commands), where the joined string is `""`. The truthy check treated that
  as "omit the wrapper," but the pre-refactor inline code always emitted the
  wrapper unconditionally regardless of dots content. Fixed by changing the
  parameter to `progress_html: str | None = None` and the check to
  `if progress_html is not None:` — presence, not truthiness, decides
  rendering. Caught by the golden corpus (`17_empty_substory`), not by the
  initial unit tests — see §5.

- **CSS fix**:
  `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/static/scriba-embed.css`,
  lines 183–190, the first (visual) `.scriba-narration` rule — added
  `overflow-wrap: anywhere;`. The second `.scriba-narration` rule at line 197
  (transition-only: `transition: opacity 0.2s ease;`) was left untouched — not
  the visual rule.

---

## 4. Tests — RED → GREEN

**`tests/unit/test_shell_panel_single_source.py`** (new, 17 tests):
- `TestNarrationElement` (5): filmstrip/print-substory/main-widget/substory-widget
  attribute shapes + bare-call has no stray attributes.
- `TestStepLabelSpan` (2): shape, single-frame.
- `TestStepControlsElement` (5): main-widget multi-frame, main-widget
  single-frame disables next, substory-with-progress-dots,
  `test_empty_but_not_none_progress_html_still_renders_wrapper` (regression
  lock for the bug in §3), `test_none_progress_html_omits_wrapper`.
- `TestCrossModeStepLabelConsistency` (1): filmstrip vs. interactive
  print-frames emit identical `(step, total)` pairs for identical input,
  called directly against `emit_animation_html` / `emit_interactive_html`
  with hand-built `FrameData` (no DSL parsing needed — pattern borrowed from
  `tests/integration/test_substory_html.py`).
- `TestCrossModeNarrationConsistency` (1): same cross-mode agreement check for
  narration text.
- `TestControlsShapeConsistency` (1): builds a `SubstoryData` + parent
  `FrameData`, calls `emit_interactive_html` directly, asserts main-widget and
  substory controls bars share identical button classes/order while
  correctly differing in labels and disabled-state.

All 17 written RED first against the pre-refactor inline markup (verified
failing), GREEN after the call-site migration.

**`tests/unit/test_narration_overflow_css.py`** (new, 2 tests):
- `test_narration_rule_exists` — sanity check the rule is present.
- `test_narration_gets_overflow_wrap_anywhere` — RED first (failed, error
  message showed the exact pre-fix CSS block with no `overflow-wrap`), GREEN
  after the CSS edit.

**Full targeted regression** (my 2 new files + every test file that imports
`_html_stitcher` or `scriba.animation.emitter`, 30 files total — includes
`tests/unit/test_invariant_panel_wrapper.py` per the sibling agent's precedent
and `tests/integration/test_substory_html.py`):

```
927 passed, 1 xfailed, 2 warnings
```

Zero failures. The 1 xfail is a pre-existing, unrelated `strict=False` xfail
in the suite (not touched by this sweep).

**Full golden corpus** (`tests/golden/examples/`, 107 examples with committed
HTML goldens): every one of the 107 fails byte-comparison in
`test_example_html.py` — expected, since goldens are intentionally not
re-blessed (see §6). Verified programmatically (via `difflib.SequenceMatcher`
opcodes, not just eyeballing a diff) that **all 107** differ from a fresh
render by exactly one inserted line — the new
`  overflow-wrap: anywhere;` in `.scriba-narration` — and nothing else. Zero
files showed any other divergence. This is what caught the `progress_html`
bug in §3: before that fix, `17_empty_substory` showed a *second* hunk (a
missing `<div class="scriba-progress">` wrapper); after the fix, it shows only
the one accepted CSS line, identical to the other 106.

Also checked and confirmed **not affected**:
- `tests/doc_coverage/` — `test_doc_coverage.py` (422 passed) only asserts an
  ok/error *contract* per `.expect` file; it renders to a scratch `tmp_path`
  and never compares against the 303 `.html` files sitting in
  `tests/doc_coverage/corpus/` (those are orphaned artifacts from corpus
  generation, not active golden fixtures). `test_smart_label_lint.py` is a
  source-pattern linter, unrelated to rendered HTML.
- `tests/golden/smart_label/` and `tests/conformance/smart_label/` — goldens
  there are bare `.svg` fragments (label-placement geometry), zero `.html`
  fixtures. Unrelated concern, no overlap with shell-panel chrome.

---

## 5. Impact analysis (GitNexus, repo=scriba)

Run before editing, on each function whose call sites were migrated:

| Symbol | Direction | Risk | Direct callers | Notes |
|---|---|---|---|---|
| `emit_animation_html` | upstream | **LOW** | 1 | impactedCount 4, 0 processes affected |
| `emit_substory_html` | upstream | **LOW** | 2 | impactedCount 5, 0 processes affected |
| `emit_interactive_html` | upstream | **LOW** | 1 | impactedCount 4, 0 processes affected |

`_step_controls_element` itself returned "not found" on `impact()` at the time
of the bug fix — it's a brand-new, uncommitted symbol, not yet in GitNexus's
index. Accepted as low-risk to proceed on: both of its call sites were written
by me this session, and the fix was verified directly via the golden corpus
(§4) rather than relying on impact analysis for a symbol GitNexus can't yet
see.

**`detect_changes(scope=unstaged)` returned `risk_level: critical` — this is
the aggregate of every agent's uncommitted work sharing this working tree**,
not a critical rating on this sweep's own changes. Cross-checked against
`git status`: of the 27 changed symbols and 126 changed files it reports, the
`primitives/base.py`, `primitives/forest.py`, `primitives/graph.py`,
`primitives/tree.py`, and `renderer.py` symbols belong to sibling agents'
already-landed work (Tree/Forest/Graph top-band fix, invariant renderer fix —
confirmed via their own untracked spec files sitting alongside mine in
`_bmad-output/implementation-artifacts/`), explicitly outside this sweep's
scope fence. My own footprint is exactly two modified files
(`_html_stitcher.py`, `scriba-embed.css`) plus two new test files; four of the
27 "changed" symbols GitNexus attributed near my insertion
(`_escape_js`, `_get_frame_id_fn`, `_get_is_id_safe_label_fn`,
`_apply_min_arrow_above`) are confirmed, via `git diff -U0` hunk ranges, to be
line-shift attribution artifacts from inserting 71 new lines just above
them — none of their bodies are actually touched.

---

## 6. Goldens — NOT re-blessed (list, do not touch)

107 files under `tests/golden/examples/corpus/`, each differing from a fresh
render by exactly the one accepted narration `overflow-wrap` CSS line (§4):

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

Re-blessing (`SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/examples/ -v`) is a
release-time decision for whoever owns landing this sweep's CSS change — not
run here per mandate.

---

## 7. Dark-mode spot check

`.scriba-narration`'s two dark-mode overrides
(`scriba-embed.css:256` and the `prefers-color-scheme: dark` block at
`scriba-embed.css:272`) set only `color` and `border-color` — neither
redeclares `overflow-wrap`, `padding`, `line-height`, nor any other layout
property. `overflow-wrap` is a layout-only property with no theme dependency:
the base rule's `overflow-wrap: anywhere` is never overridden or reset by the
dark-mode selectors, so it applies identically in light and dark automatically
through normal CSS cascade — exactly mirroring why the invariant panel's own
`overflow-wrap` fix needed no separate dark-mode declaration. No gap found, no
change needed.

---

## 8. Scope-fence correction

The original mandate named `scriba-animation.css` / `scriba-scene-primitives.css`
as the CSS files in scope. `.scriba-narration`'s visual rule actually lives in
`scriba-embed.css` (confirmed by that file's own header comment: "Embed-safe
widget chrome for host applications... Narration panel..."). This extension
was identified and disclosed in the prior session before editing; flagging it
again here for the record since it's a deviation from the literally-named
scope fence, though within the spirit of "shell-panel rules only" and nowhere
near the fenced-off `.scriba-invariant-panel` rules.

---

## 9. Handoffs / out of scope

- **Theme toggle chrome**: no `_html_stitcher.py` symbol builds it; confirmed
  no shell-panel duplication in this family. No action taken, nothing to hand
  off.
- **Golden re-blessing**: 107 files listed in §6, all showing only the
  accepted CSS-line diff. Left for whoever owns the release/CHANGELOG step.
- **`detect_changes` CRITICAL aggregate**: reflects the whole shared working
  tree (multiple agents' uncommitted work), not this sweep. Whoever
  coordinates the final merge should re-run `detect_changes` after all
  sibling agents' work is either committed or reconciled, since this
  snapshot is a moving target.
- No `scriba.js` live-swap contract changes were needed — the unification
  preserved exact node order/attributes at every call site (verified via the
  golden corpus), so no handoff needed there.
