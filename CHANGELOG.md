# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — v0.9.0

### Removed

- **BREAKING: `StarlarkHost.eval_raw` removed** — the deprecated `eval_raw` method has been deleted. Use `\compute{...}` blocks instead. Wire-level requests with `op="eval_raw"` now return a structured error `E1156` with a migration hint.

## [0.8.3] - 2026-04-18

Wave 8 landing release. All changes are additive or bug fixes; fully
backward compatible with 0.8.2 consumers. `SCRIBA_VERSION` unchanged.

### CSP / Runtime (Wave 8 — M12/M13)

- **External JS runtime** — the animation runtime is now shipped as a
  standalone `scriba.<sha384[:8]>.js` asset alongside the rendered HTML.
  The new CLI flags (`--inline-runtime` / `--no-inline-runtime`,
  `--asset-base-url`, `--copy-runtime` / `--no-copy-runtime`) select
  between three deployment modes: inline (default, `file://`-safe),
  external-copy (serve alongside HTML, enables `script-src 'self'` CSP),
  and CDN (supply your own host via `--asset-base-url`).
  `scriba.animation.runtime_asset` exports `RUNTIME_JS_BYTES`,
  `RUNTIME_JS_FILENAME`, and `RUNTIME_JS_SHA384` for programmatic use.
  Inline mode is deprecated and will no longer be the default in v0.9.0.

### CLI

- **New flags** — `--lang` (BCP 47 tag for the HTML `lang=` attribute,
  default `en`), `--inline-runtime`, `--no-inline-runtime`,
  `--asset-base-url`, `--copy-runtime`, `--no-copy-runtime` (see CSP
  deployment guide at `docs/csp-deployment.md` for usage).
- **`--debug` / `SCRIBA_DEBUG=1`** — enable verbose output including full
  stack traces and intermediate render state. Intended for authoring
  diagnostics; not recommended for production CI pipelines.
- **`ScribaError` handler** — unhandled `ScribaError` exceptions in the
  CLI now print a clean one-line diagnostic without a Python traceback.
  Pass `--debug` to restore full traceback output.
- **Input extension check** — `render.py` now rejects input files that
  do not end in `.tex` with a clear error message (F-03).
- **Overwrite guard for `-o input.tex`** — the CLI refuses to overwrite
  the input file when `-o` is set to the same path as the input.
- **E1116 promoted to error** — undeclared shape references that
  previously surfaced as warnings are now raised as errors at render
  time, matching the severity documented in `docs/spec/error-codes.md`.

### Animation

- **Corrected easing curves** — `element_add` and `element_remove`
  transitions now use `ease-out` (was `linear`); `annotation_add` uses
  `ease-in-out` (was `ease-out`). Matches the authored intent from the
  Wave 6.3 transition manifest spec.
- **Named timing constants** — animation durations previously scattered
  as magic numbers are now centralised as named constants in the emitter
  (`TRANSITION_MS_FAST`, `TRANSITION_MS_NORMAL`, `TRANSITION_MS_SLOW`).

### Accessibility

- **KaTeX MathML output** — the KaTeX worker now emits both HTML and
  MathML (`output: "htmlAndMathml"`). Screen readers receive structured
  math rather than falling back to the raw LaTeX source.
- **Live-region cleanup** — the narration `aria-live="polite"` region is
  now cleared on frame reset so stale text is not re-announced when the
  animation loops or rewinds.
- **Substory narration** — substory steps now update the parent
  animation's narration region, ensuring sub-step text is announced by
  assistive technology.
- **Filmstrip `aria-label` fallback** — the static filmstrip `<figure>`
  element now falls back to `aria-label="Animation"` when no `label=`
  option is supplied, eliminating unlabelled landmark warnings.

### SVG

- **Plane2D grid `vector-effect`** — grid lines in `Plane2D` primitives
  now carry `vector-effect="non-scaling-stroke"` so grid line width
  stays visually consistent across zoom levels.
- **Print-mode dark mode fix** — the `@media print` CSS block now
  correctly resets `color-scheme` to `light` when dark mode is active,
  preventing black-on-black printed output.

### Performance

- **~7–8% render speedup** on large and medium fixtures (benchmark:
  `examples/algorithms/graph/dijkstra.tex`, `h15_kmp_matching.tex`)
  via reduced per-frame SVG allocation and deferred selector expansion.
- **−100 ms cold start** — KaTeX worker startup deferred until the first
  math expression is encountered; documents with no math pay no startup
  cost.
- **−360 KB output** on math-free renders — KaTeX font data no longer
  inlined when no `$...$` or `\[...\]` expressions are present.

### Hygiene (Wave 8 audit — P1/P3)

- **`errors.py` `__all__`** — public exception classes and `ERROR_CATALOG`
  now listed explicitly; internal helpers (`_animation_error`,
  `_suggest_closest`, `_format_compute_traceback`) prefixed with `_` and
  excluded (Round D). Audit finding P1 F-01.
- **Underscore-prefix internals** — module-private helpers across
  `emitter.py`, `scene.py`, and `starlark_worker.py` renamed with a
  leading underscore to make the public surface explicit (Round D).
- **`SubprocessWorker` deprecation message** — the `DeprecationWarning`
  now includes the replacement name (`PersistentSubprocessWorker`) and
  the version it will be removed in (`v1.0.0`). Audit finding P3 H1.
- **Extension API stability** — `DiagramRenderer` added to
  `scriba.animation.__all__` (Round A); import path documented in
  `docs/spec/environments.md`. Audit finding P1 F-05.

## [0.8.2] - 2026-04-15

### Fixed

- **Position-aware auto-ID generation** — `_scene_id()` and `scene_id_from_source()` now hash `"{position}:{raw}"` instead of just the raw content. Two animation/diagram blocks with identical content at different document positions now produce distinct HTML element IDs, fixing a bug where animation 2's JavaScript bound to animation 1's DOM element.
- **CSS selector tests updated** — Stability tests for primitive CSS centering now match the `:where()`-wrapped selectors introduced in v0.8.0.

### Added

- **Duplicate block ID warning** — The pipeline (step 4b) now scans rendered artifacts for duplicate `block_id` values and emits a `CollectedWarning(code="E1019", severity="dangerous")` on `Document.warnings`. This catches both explicit `[id="..."]` reuse and auto-generated hash collisions.

## [0.8.0] - 2026-04-14

### Fixed

- **State styling CSS specificity regression** — Cell/node/edge state colors (`current`, `error`, `good`, `highlight`, etc.) were silently overridden by primitive base selectors due to a CSS specificity conflict. Primitive base selectors now use `:where()` to zero their qualifying specificity, so `.scriba-state-*` rules always win. Browser support: Chrome 88+, Firefox 78+, Safari 14+.

### Changed

- **CSS deduplication via `css_bundler`** — The ~470-line inline CSS block in `render.py` was replaced by `scriba.core.css_bundler`, reading CSS from source `.css` files at render time.
- **Widget chrome extracted** — `scriba-standalone.css` split into `scriba-embed.css` for widget chrome CSS.

## [0.6.3] - 2026-04-13

### Added

- **Arrow draw-on animation** — Annotation arrows now draw progressively via `stroke-dashoffset` rAF animation (120ms, ease-out) instead of fading in. Arrowhead polygon computed via `getPointAtLength()` appears at 70% progress. Falls back to 180ms opacity fade when `<path>` is absent or `getTotalLength` unavailable.
- **Value change pulse** — `value_change` transitions now fire a non-blocking WAAPI scale pulse (`1 → 1.15 → 1`, 100ms) on the `<text>` element, drawing the eye to which cell changed.
- **2-phase micro-sequencing** — Transitions are split into two phases: annotations and highlights fire at t=0, everything else fires at t=50ms. Arrows are visible before the state changes they explain. Total worst-case per step: ~230ms.

### Fixed

- **Annotation position flash on draw-on** — Annotation clones inserted during `annotation_add` animation now preserve intermediate SVG `transform` groups between the annotation and its `data-shape` ancestor. Previously, clones were appended directly to the `data-shape` container, skipping transforms like `translate(0, 44)` and causing a visible position jump until the full-frame sync corrected it.

## [0.6.2] - 2026-04-12

### Fixed

- **Animation transition integration tests** — Updated stale golden files and regex patterns in `tests/integration/test_animation_transitions.py` to match current emitter output. All 12 test cases pass.
- **Documentation accuracy** — Corrected `docs/guides/animation-plugin.md` non-goals section which falsely claimed transitions were not produced and no runtime JavaScript existed. The frame-to-frame differ (`scriba/animation/differ.py`) and JS animation runtime (`emitter.py`) are fully operational: the differ computes transition manifests (`recolor`, `value_change`, `element_add`, `element_remove`, `highlight_on`, `highlight_off`), serialized as `tr:` fields in the JS frames array, with WAAPI animations and `prefers-reduced-motion` support.

## [0.6.1] - 2026-04-11

### Fixed

- **Double-pass rendering bug eliminated** (`9f433db`) — `emit_interactive_html` now renders each frame's SVG in a single pass. Previously, the two-loop design (JS + print) caused structural mutations (`add_edge`/`remove_edge`/`add_node`/`remove_node`/`reparent`) to accumulate across passes, breaking every animation using mutation ops. The hidden-state pre-declaration pattern is no longer required (but remains a valid best practice).
- **Graph node collision resolution** (`1ecca61`) — Added `_resolve_overlaps()` post-pass to `fruchterman_reingold()` and `compute_stable_layout()`, guaranteeing minimum node separation of `2 * radius + 12px`. No two graph nodes overlap visually.
- **Narration math escape** (`4c386ee`) — `$\min_{j<1}$` inside `\narrate{...}` no longer fails. `process_hl_macros` now defers plain-text escaping when a TeX renderer is available, so `<` reaches KaTeX intact.
- **KaTeX support in 8 text sites** (`c12b2fb`, `06b0362`, `7b319f1`) — All user-authored text now supports `$...$` inline math via KaTeX. Previously literal in: annotation labels, Plane2D point labels, Plane2D line labels, MetricPlot xlabel, MetricPlot ylabel, MetricPlot ylabel_right, MetricPlot legend series names, Graph edge weights, and CodePanel caption labels.

## [0.6.0] - 2026-04-11 (Completeness audit — Phase 4 GA)

General-availability release graduating 0.6.0-alpha1. Landing **Wave 7** —
the cookbook truth pass and widget accessibility polish — plus a late-wave
Graph `hidden`-state regression fix. Six parallel worktree agents shipped
**10 new cookbook examples** (+2 rewrites) and fixed a widget a11y gap.

**`SCRIBA_VERSION` stays at 3** (bumped 2→3 in 0.6.0-alpha1). The Wave 7
deliverables are all additive or bug-fixes; no core contract change from
the alpha.

### Cookbook truth pass (Wave 7.0 — lying examples fixed)

- **`h07_splay_amortized.tex`** — rewritten to use real `\apply{T}{reparent=...}`
  structural rotations. Five reparent calls perform a textbook zig-zig that
  lifts a depth-3 node to depth 1. Verification: 6 distinct edge-coordinate
  layouts across 7 frames (vs 1 layout in the 0.5.x version — that was the
  "lie" flagged by Agent 7). Phi amortized-cost curve drops 8.5 → 5.8
  across the rotation sequence, now visibly attached to actual structural
  change rather than recolor-only.
- **`h08_persistent_segtree.tex`** — rewritten to use `\apply{T.node["X"]}{value=...}`
  for sum cascade updates. Two cascaded updates (`a[3]+=10`, `a[5]+=5`)
  model persistent versions V0/V1/V2. Root `[0,7]` deliberately on both
  update paths: its value visibly changes 36→46→51 across frames. 15
  distinct tree-node targets and 12 distinct label values rendered per
  frame, resolving Agent 7 F1 CRITICAL.

### Cookbook canonical examples (Wave 7.1-7.4 — 8 new files)

- **`h11_dijkstra_weighted.tex`** (W7.1) — 148 lines, 16 steps. Weighted
  Graph with `show_weights=true`, parallel distance Array, full relaxation
  trace showing `dist[B]` going 4→3 and `dist[D]` going 10→8. 288 weight
  label occurrences in rendered HTML.
- **`h12_kruskal_mst.tex`** (W7.1) — 108 lines, 11 steps. Same 6-node
  graph as h11 for direct algorithm comparison. 5 accepted + 4 rejected
  edges, visible accept/reject narrative via `state=good` vs `state=dim`.
- **`h13_bst_insert_delete.tex`** (W7.2) — 122 lines, 15 steps. BST insert
  (6 calls growing 1→7 nodes) + delete (leaf, then root via rename-and-
  remove using value layer override). Tree node counts visibly shrink:
  `7→7→7→6→6→6→6→5→5`.
- **`h14_bfs_tree.tex`** (W7.2) — 129 lines, 16 steps. Parallel
  graph/tree/queue/visited-array showing BFS construction on 6 nodes.
- **`h15_kmp_matching.tex`** (W7.3) — 186 lines, 22 steps. Full
  failure-function build on `ABABCABAB` (yields `F=[0,0,1,2,0,1,2,3,4]`)
  plus matching trace on `ABABDABACDABABCABAB` with 2 mismatch/fallback
  cycles before the final match at `T[10..18]`.
- **`h16_binary_search.tex`** (W7.3) — 85 lines, 11 steps. Happy path
  (target=7 found first iteration) + not-found path (target=8, 3
  narrowing iterations). Includes cookbook notes on the
  `lo + (hi-lo)/2` overflow bug and `lower_bound`/`upper_bound` variants.
- **`h17_union_find.tex`** (W7.4) — 129 lines, 18 steps. Truthful DSU
  with real path compression: 9 `add_edge` calls + 2 `remove_edge`
  rewrites (`find(D)` rewrites `D→C→A` to `D→A`; `find(F)` rewrites
  `F→E→A` to `F→A`). Parent array visibly tracks union state.
- **`h18_linkedlist_reverse.tex`** (W7.4) — 89 lines, 12 steps.
  Three-pointer (prev/curr/next) cursor trace showing in-place reversal.

Cookbook matrix coverage rose from ~42% (Agent 12 estimate) to ~70%
including all weighted-graph algorithms.

### Widget accessibility + late-wave fixes (Wave 7.5 + GA)

- **Widget `aria-label`** — `<button class="scriba-btn-prev">` now carries
  `aria-label="Previous step"` and `<button class="scriba-btn-next">` carries
  `aria-label="Next step"`. Substory widgets carry "Previous sub-step" /
  "Next sub-step" variants. Visible button text is unchanged.
- **`prefers-reduced-motion`** — `scriba-scene-primitives.css` extends its
  existing reduced-motion block with explicit widget button selectors
  (`.scriba-btn-prev`, `.scriba-btn-next`, `.scriba-dot`) set to
  `transition: none !important`. Defense-in-depth against future regressions.
- **Graph `hidden` state** (GA commit) — `Graph.emit_svg` now honors the
  `hidden` state with early-return in both the edge and node loops.
  Edges incident on a hidden node are also skipped (matches Tree.emit_svg
  behavior). Fixes a gap flagged by W7.1 Dijkstra — before the fix, `hidden`
  fell through to idle styling in Graph. 4 new regression tests in
  `tests/unit/test_graph_mutation.py::TestHiddenState`.

### Wave 7.5 correction

The FIX_PLAN Phase 4 Truth pass 3 described `scriba/animation/static/*.css`
as "orphan" files and asked W7.5 to merge them into an inline `render.py`
template. W7.5 correctly identified that those files are NOT orphans —
they ship through `AnimationRenderer.assets()` at `renderer.py:347-363`
as separate asset files per the pipeline's namespacing contract. No
inline CSS template exists. The agent left the static files intact,
extended the existing reduced-motion block, and added `aria-label` in
`emitter.py` instead. Spec bug reported; no Python source change needed.

### Tests

- **+14 new tests** across 3 new or extended files vs 0.6.0-alpha1:
  - `tests/unit/test_widget_a11y.py` (9, Wave 7.5)
  - `tests/unit/test_graph_mutation.py::TestHiddenState` (4, GA fix)
  - `tests/unit/test_graph_layout_stable.py` was extended by Wave 6.2; no
    Wave 7 additions (it just works).
- **Full suite: 2009 passed, 1 skipped, 0 failed.** (0.6.0-alpha1 was
  1996 passed.)

### Known follow-ups (not blocking v0.6.0 GA)

- **`emit_interactive_html` double-pass state bug** — W7.0, W7.2, and W7.4
  independently noted that `_emit_frame_svg` is called twice per frame
  (once for the interactive JS payload, once for the print-mode filmstrip)
  without snapshotting/restoring primitive state between passes. The
  interactive widget (the user-visible playback) is correct; the
  print-filmstrip shows the final mutated state for every frame and would
  re-raise `E1433`/`E1436`/`E1471`/`E1437` on structural mutations under
  certain rendering paths. Tracked for v0.6.1 (single-agent fix, ~50 LoC
  in `emitter.py`). Workaround: cookbook authors can use the `state=hidden`
  pre-declaration pattern (as W7.2 did for BST / BFS).
- **Animation id dup check (W6.4)** — helper exists in `animation/uniqueness.py`
  but document-level wiring needs `renderer.py` edit. Tracked for v0.6.1.
- **Starlark cumulative budget (W6.4)** — reset/consume helpers ship,
  host-side wiring at `starlark_host.py` is 2 lines away. Tracked for v0.6.1.
- **CLI `--report=path.json`** — render-report serialization for CI
  consumers. Tracked for v0.6.1.
- **KaTeX `errorCallback` migration** — replaces the HTML regex scan.
  Tracked for v0.6.1.
- **Tree `\annotate` rendering** — Agent 7 F2 HIGH. v0.7 scope.
- **Cross-frame endpoint tween** — Agent 9 FR4. v0.7 scope.
- **Graph node mutation** — v0.7 scope; v0.6.0 ships edge mutation only.

## [0.6.0a1] - 2026-04-11 (Completeness audit — Phase 3 alpha)

Pre-release alpha landing **Wave 6** — the Phase 3 implementation wave from
the 14-agent completeness audit. Five parallel worktree agents (W6.1 Tree
mutation, W6.2 Graph mutation + warm-start layout, W6.3 strict mode
infrastructure, W6.4 uniqueness + red-team hardening, W6.5 Plane2D tombstone
remove ops) shipped **~3900 LoC** across 17 files, with **+247 new tests**
(1996 passing vs 1747 baseline). Two design RFCs locked the contract first:
`docs/rfc/001-tree-graph-mutation.md` and `docs/rfc/002-strict-mode.md`.

**`SCRIBA_VERSION` bumped 2 → 3** — first break since v0.1.1. The `Document`
dataclass gained a new `warnings: tuple[CollectedWarning, ...]` field, and
the Tree / Graph / Plane2D primitives gained structural mutation APIs.
Consumer caches keyed on SCRIBA_VERSION must invalidate.

### Primitive mutation APIs (RFC-001)

- **Tree.apply_command** — `\apply{T}{add_node={id,parent}}`,
  `\apply{T}{remove_node={id,cascade}}`, `\apply{T}{reparent={node,parent}}`.
  Reingold-Tilford recomputes on every mutation; iterative DFS avoids
  recursion. Cycle detection, cascade-on-remove, duplicate-id rejection.
  Error codes E1433, E1434, E1435, E1436. (primitives/tree.py)
- **Tree value layer** — `emit_svg` now honors `get_value(suffix)` as an
  override for `self.node_labels`, unlocking segtree sum updates and
  lazy-tag propagation visualizations. Resolves Agent 7 F1 CRITICAL.
- **Graph.apply_command** — `\apply{G}{add_edge={from,to,weight}}`,
  `\apply{G}{remove_edge={from,to}}`, `\apply{G}{set_weight={from,to,value}}`.
  Undirected edge orientation normalized in lookup. Error codes E1471,
  E1472, E1473, E1474. (primitives/graph.py)
- **Graph weighted edges** — 3-tuple edge syntax `edges=[("A","B",4)]`,
  `show_weights=true` flag renders midpoint weight text. Mixed
  weighted/unweighted raises E1474.
- **Graph warm-start layout** — `compute_stable_layout` gained an
  `initial_positions` kwarg. After mutation, the new layout seeds from
  the pre-mutation positions rather than re-rolling from RNG, keeping
  existing nodes approximately in place. Unlocks Dijkstra, Prim, Kruskal,
  Bellman-Ford visualizations. (primitives/graph_layout_stable.py)
- **Plane2D.apply_command** — 4 new tombstone-based remove ops:
  `remove_point`, `remove_line`, `remove_segment`, `remove_polygon`
  (plus bonus `remove_region`). Indices stay stable across removes
  (tombstone-in-place) so existing selectors don't break. Convex hull
  pop is now authentic rather than faked with `state=dim`. Error code
  E1437. (primitives/plane2d.py)
- **`hidden` state** — new first-class state in `VALID_STATES`. Element
  is skipped in emit_svg entirely (distinct from `dim` which still
  renders). Agent 9 F2 fix. Applied to Tree nodes/edges, Graph
  nodes/edges (implicit via state checks), Plane2D points/lines/
  segments/polygons/regions/labels.

### Strict mode and render report (RFC-002)

- **`CollectedWarning` dataclass** exported from `scriba.core.artifact` —
  `(code, message, source_line, source_col, primitive, severity)` frozen
  record for structured warning surfacing.
- **`Document.warnings: tuple[CollectedWarning, ...]`** — new field on
  the return type. Always populated by the pipeline, regardless of
  `strict` setting. Empty tuple when no warnings.
- **`RenderContext.strict`, `strict_except`, `warnings_collector`** —
  new fields. `strict=False` default preserves 0.5.x behavior; opting in
  promotes DANGEROUS-class warnings to raised exceptions.
- **9 silent-fix sites promoted** (Agent 4 inventory):
  - **Promoted strict** (raise under `strict=True`): SF-1 polygon
    auto-close E1462 **(with correctness fix — pts[0] now explicitly
    appended to internal list)**, SF-3 degenerate line E1461, SF-4
    log-scale clamp E1484, SF-6 stable-layout fallback E1501/E1502/E1503.
  - **No opt-out** (always raise): SF-8 stray `\end{animation}` E1007,
    SF-9 substory prelude command drop E1057.
  - **Collector-only** (never raise): SF-2 point outside viewport E1463,
    SF-5 `layout_lambda` clamp E1504, SF-14 emitter selector mismatch
    E1115 (legacy `warnings.warn` path preserved for test compat).
- **KaTeX error capture** — new E1200 code. A post-render HTML scanner
  in `tex/renderer.py` walks the output for `<span class="katex-error">`
  elements and populates the collector with the embedded ParseError
  title. Resolves Agent 14 finding 3e/3f (macro bombs).
- **`_emit_warning(ctx, code, msg, ...)` helper** in `animation/errors.py`
  is the single surface for all primitive-level warning emission.
  Threaded through `PrimitiveBase._ctx` class attribute assigned by the
  pipeline.

### Uniqueness + red-team hardening (W6.4)

- **New module `animation/uniqueness.py`** — `validate_shape_id_charset`
  (E1017), `check_duplicate_shape_ids` (E1018), `check_duplicate_animation_ids`
  (E1019). Shape id charset and duplicate checks wired into
  `scene.py::apply_prelude` and `apply_substory`. Animation id dup helper
  ships as a standalone — document-level wiring is a follow-up.
- **Starlark budget tightening** — per-block wall-clock reduced from 3s
  to 1s. New cumulative budget `_CUMULATIVE_BUDGET_SECONDS = 5.0` across
  all compute blocks in a render, with `reset_cumulative_budget()` and
  `consume_cumulative_budget()` helpers (trip code E1152).
- **KaTeX macro-expansion hardening** — `katex_worker.js` now passes
  `macros: {}` (per-call, no cross-render `\def` persistence),
  `trust: false` (blocks `\href`/`\url`/`\htmlId` and raw HTML),
  `maxExpand: 100` (down from KaTeX default 1000). Closes Agent 14
  finding 3b and reduces macro-bomb headroom.

### Tests

- **+247 new tests** across 9 new files:
  - `tests/unit/test_tree_mutation.py` (42, Wave 6.1)
  - `tests/unit/test_graph_mutation.py` (29, Wave 6.2)
  - `tests/unit/test_graph_layout_stable.py` (+14, Wave 6.2)
  - `tests/core/test_strict_mode.py` (62, Wave 6.3)
  - `tests/unit/test_uniqueness.py` (44, Wave 6.4)
  - `tests/unit/test_starlark_budget.py` (15, Wave 6.4)
  - `tests/unit/test_plane2d_remove.py` (37, Wave 6.5 — 35 tests + 2 hidden-state tests now active via VALID_STATES)
- **Full suite: 1996 passed, 1 skipped, 0 failed.**
- `TestErrorCatalogMergeGuards` parameterized over all 16 new E-codes as
  a cross-wave integration safety net.

### Known follow-ups

- **Animation id dup check** — helper exists but document-level wiring
  needs `renderer.py` edit (outside W6.4 scope). Tracked for v0.6.0 GA.
- **Starlark host integration** — `reset_cumulative_budget` /
  `consume_cumulative_budget` helpers ship, but the host-side call site
  in `starlark_host.py` is outside W6.4 scope; 2-line wiring tracked
  for v0.6.0 GA.
- **CLI `--report=path.json` flag** — render-report serialization for
  CI consumers. Deferred to v0.6.1.
- **KaTeX `errorCallback` migration** — replaces the HTML regex scan
  in `_scan_katex_errors` with a structured worker protocol. Deferred
  to v0.6.1.
- **Tree annotate rendering** — Agent 7 F2 HIGH. Out of v0.6.0 scope.
- **Cross-frame endpoint tween** — Agent 9 FR4. Deferred to v0.7.
- **Graph node mutation** — Deferred to v0.7. v0.6 covers edges only.
- **Cookbook truth pass** (Phase 4) — rewrite `h07_splay_amortized.tex`
  and `h08_persistent_segtree.tex` to use the new mutation APIs; add 8
  canonical examples (Dijkstra, Kruskal, BST insert/delete, BFS tree,
  KMP, binary search, Union-Find, LinkedList reverse). Pre-GA.

## [0.5.2] - 2026-04-11 (Completeness audit — Phase 1 quick wins)

Patch release landing **Wave 5** — the Phase 1 quick wins from the 14-agent
completeness audit recorded in `docs/archive/completeness-audit-2026-04-11/`.
Three parallel worktree agents (W5.1 Parser, W5.2 Emitter+Primitives, W5.3
Error hints) shipped ~160 LoC of concrete, audit-backed fixes with
`file_path:line_number` precision. `SCRIBA_VERSION` unchanged (= 2); fully
backward compatible with 0.5.1 consumers.

**Total shipped**: 3 clusters, 1747 tests passing (+50 from 0.5.1), 0
regressions, 0 strict xfails. Convex hull (`h06_li_chao.tex`) and dijkstra
(`demo10.tex`) cookbook examples now compile with zero `UserWarning` stderr.

### Parser (Wave 5.1)

- **Bare-token fallthrough in `_read_param_brace`.** `\apply{stk}{pop}` now
  parses natively as `{"pop": True}` instead of raising E1005. Zero-churn for
  primitives — `Stack.apply_command` already reads `pop_val` as truthy-then-int,
  so `\apply{stk}{pop}` means "pop one" with no downstream changes. `{k=v}`
  form still works identically. (grammar.py:~1422-1482)
- **LBRACE branch in `_parse_param_value`.** Nested dict values like
  `\apply{ll}{insert={index=0, value=42}}` now parse. The recursive call to
  `_read_param_brace` makes LinkedList's `insert={dict}` reachable for the
  first time. (grammar.py:~1527-1540)
- **NFC normalization on identifiers.** Source is NFC-normalized at lex time
  (grammar.py:~105-113) and `SelectorParser.__init__` defends the direct-call
  path (selectors.py:~56). NFD-encoded shape names and selectors collapse to
  a single NFC identifier — homograph Cyrillic/Latin detection still works.

### Emitter + Primitives (Wave 5.2)

- **Skip guard for bare-shape selectors.** `_validate_expanded_selectors`
  (emitter.py:324-332) and `_emit_frame_svg`'s per-target loop
  (emitter.py:442-456) both early-out when the target key is the shape name
  itself. Kills the `Plane2D 'p': invalid selector 'p', ignoring set_state()`
  warning class that polluted `h06_li_chao.tex`'s render log. Invalid
  dot-path selectors like `arr.cell[99]` still warn — the guard only masks
  whole-shape targets.
- **Truthiness check for `dequeue=false`.** `Queue.apply_command` previously
  treated `dequeue=false` as truthy and silently popped. New
  `_is_truthy_flag` helper (queue.py:50-65) accepts only Python `True` or
  case-insensitive `"true"`. `False`, `"false"`, `0`, `None`, `""` all
  correctly NO-OP now. (queue.py:~162)
- **`PrimitiveBase.set_label` wired into the emitter.** `ShapeTargetState.label`
  was being populated by the parser but the emitter never consumed it, so
  `\relabel`-style label mutations were dead code. `_emit_frame_svg` now
  calls `prim.set_label(suffix, str(label_val))` when `label` is set.
  (emitter.py:466-473)

### Error UX (Wave 5.3)

- **`suggest_closest` hoisted to `errors.py`.** Old private `_fuzzy_suggest`
  in grammar.py was moved to a public `suggest_closest(needle, candidates,
  *, cutoff=0.6)` helper in `scriba.animation.errors`. Enables cross-module
  reuse without circular imports. The E1102 primitive-type validator was
  updated to use it directly.
- **`_raise_unknown_enum` helper collapses 6 enum raise sites.** A new
  `SceneParser._raise_unknown_enum` (grammar.py:377-406) builds uniform
  `"unknown &lt;field&gt; &lt;val&gt;; valid: a,b,c (did you mean \`X\`?)"`
  messages. Six enum raise sites collapsed to 1-line calls — error codes
  unchanged (E1004×3, E1109, E1112, E1113×2). Typing `\recolor{arr}{currnet}`
  now hints "did you mean `current`?" via difflib.
- **New `E1114` for unknown shape kwargs.** `PrimitiveBase.ACCEPTED_PARAMS:
  ClassVar[frozenset[str]] = frozenset()` added at base.py:187-213. When
  non-empty, unknown kwargs raise E1114 with a `suggest_closest` hint.
  `Plane2D` populated with 12 concrete kwargs (`xrange, yrange, grid, axes,
  aspect, width, height, points, lines, segments, polygons, regions`);
  typing `Plane2D(xranges=...)` now raises E1114 hinting "did you mean
  `xrange`?". Empty frozenset is the opt-out — legacy primitives are
  unaffected. (base.py, plane2d.py:86-103)

### Tests

- +50 new tests across 9 new test files:
  - `tests/unit/test_parser_bare_token_apply.py` (8)
  - `tests/unit/test_parser_nested_dict_value.py` (5)
  - `tests/unit/test_parser_nfc_identifier.py` (5)
  - `tests/unit/test_queue_dequeue_false.py` (15)
  - `tests/unit/test_emitter_bare_shape_selector.py` (5)
  - `tests/unit/test_emitter_set_label_wired.py` (4)
  - `tests/unit/test_suggest_closest.py` (8)
  - `tests/unit/test_error_hints_enum.py` (5)
  - `tests/unit/test_error_hints_kwarg.py` (4)
- `tests/unit/test_unicode_homograph.py::test_nfc_and_nfd_shape_names_are_distinct`
  flipped to `_collapse_to_single_nfc_identifier` per the file's own
  pre-planned docstring directive.

## [0.5.1] - 2026-04-11 (Production audit fixes)

Patch release landing **Wave 1**, **Wave 2**, **Wave 3**, **Wave 4A**,
and **Wave 4B** fixes from the 21-agent production-readiness audit
recorded in `docs/archive/production-audit-2026-04-11/`. All changes are
backward compatible with 0.5.0 consumers; the only behavioral diffs are
stricter validation, structured error codes in place of opaque failures,
and a few previously silent bugs now raising `ValidationError`.

**Total shipped**: 24 clusters across 5 waves, 1697 tests passing
(+386 from the 0.5.0 baseline of 1311), 86% coverage, 0 known CVEs,
0 strict xfails.

### Security / Sandbox

- **Starlark sandbox: 3 escape vectors closed (13-C1, 13-C2, 13-C3).**
  - `str.format()` templates that touch attributes (`"{0.__class__}".format(x)`)
    are now rejected with `E1154`. Plain positional/keyword `{0}`/`{name}`
    substitution still works.
  - F-string / recursive attribute chain bypass closed: the AST scanner
    now walks every `.attr` in an attribute chain, so
    `f"{[].append.__self__.__class__}"` is rejected at the `__class__`
    link.
  - Generator / coroutine / async-generator introspection attributes
    (`gi_frame`, `gi_code`, `gi_yieldfrom`, `gi_running`, `cr_frame`,
    `cr_code`, `cr_running`, `cr_await`, `ag_frame`, `ag_code`) added
    to `BLOCKED_ATTRIBUTES`.
- **Determinism: `hash()` removed from Starlark builtins (08-C2).** The
  prior exposure broke the byte-identical-output guarantee because the
  builtin is seeded by `PYTHONHASHSEED`.
- **Memory limit aligned to spec (08-C1).** `_MEMORY_LIMIT_BYTES` and
  `_TRACEMALLOC_PEAK_LIMIT` both pinned at 64 MB (spec §6.3). The prior
  256 MB host / 128 MB tracemalloc drift is gone.
- **Dunder blocklist expanded (08-M1).** `__class_getitem__`,
  `__format__`, `__getattr__`, `__getattribute__`, `__set_name__`,
  `__init_subclass__` added to the sandbox dunder blocklist.
- **Walrus and `match` statements forbidden (13-H1, 13-H3).**
  `ast.NamedExpr` and `ast.Match` added to `_FORBIDDEN_NODE_TYPES`.
- **Recursion limit pinned (08-M2).** `sys.setrecursionlimit(1000)` is
  now called explicitly at worker startup so the spec's 1000-frame
  limit is enforced independent of the host interpreter default.
- **Deterministic set iteration (08-M3).** Set serialization uses
  `(str(x), repr(x))` as the tie-break key for stable ordering when
  `str(x)` collides.
- **Sanitizer allowlist expanded (06-C1, 06-H1, 06-M1).** `bleach`
  was silently stripping attributes the emitter actually writes:
  - `<figure>`: `data-scriba-scene`, `data-frame-count`, `data-layout`,
    `aria-label`
  - `<div>`: `data-scriba-frames` (substory widget)
  - `<svg>`: `aria-labelledby`, `role`
  - `<g>`: `data-target` (primitive shape-group selectors)
  Each addition is documented as inert (no URL-accepting attribute, no
  script execution, no `is_safe_url` wiring needed).

### Parser

- **Unclosed brace at EOF now raises `E1001` (07-C1).** Previously
  `\shape{a}{Array}{size=5` silently parsed to an empty shape, losing
  user data.
- **Unknown commands rejected with `E1006` (01-H2).** `\foo` (where
  `\foo` is not in `_KNOWN_COMMANDS`) now raises a structured error
  listing the valid commands instead of silently becoming a CHAR token.
  Bare backslashes (`\{`, `\\`) still parse as CHAR.
- **`\step[label=...]` now supported at parse level (01-H1).** The
  spec on line 546 documented step label options that the parser
  previously rejected with `E1052`. `FrameIR.label` carries the value
  through the AST; top-level and `\substory`-nested steps both accept
  it. Emitter wiring will land in a follow-up.
- **`\foreach` depth limit enforced at parse time (07-H3).** Mirrors
  the runtime limit in `scene.py` so deep nesting now errors out at
  parse time with a structured code rather than producing a
  pathological IR tree.
- **`FrameIR.label` field added** to the animation AST.

### Error codes & UX

- **`E1103` mega-bucket split (05-C2, 09-C2, 09-H1).** The previous
  catch-all has been replaced with primitive-specific codes carrying
  valid-range hints in the message:
  - `E1400` — empty params at primitive construction
  - `E1401` — Array size overflow (valid: 1..10000)
  - `E1411` — Grid rows/cols overflow
  - `E1412` — Grid data shape mismatch
  - `E1420` — Matrix missing rows/cols
  - `E1425` — Matrix / DPTable cell count exceeds 250 000
  - `E1430` — Tree missing root
  - `E1453` — NumberLine invalid domain
  - `E1454` — NumberLine domain overflow
  - (plus DPTable / Graph / HashMap / Queue / Stack specific codes;
    see the error catalog for the full list)
  - `E1103` itself is kept as a **deprecated alias** for user code that
    catches it generically.
- **`E1425` wired at Matrix/DPTable cell cap (06-H2, 10-C1).** The
  spec-code drift (spec said 10 000, code allowed 250 000, the cap
  raised generic `E1103`) is now resolved: both primitives raise
  `E1425` with the actual `rows*cols` value and the 250 000 limit.
- **`E1173` for foreach iterable overflow (05-C2).** `_safe_range()`
  now raises a structured `animation_error("E1173", ...)` instead of a
  bare `ValueError` (which previously collapsed to `E1151`).
- **`animation_error()` factory extended (05-C3, 09-H2).** New keyword
  arguments `line`, `col`, `hint`, `source_line` (all optional, fully
  backward compatible) are forwarded to `ValidationError.__init__`.
- **`ValidationError` source-snippet rendering (09-M3).** `__str__()`
  now appends a pointer line when `source_line` is provided:
  `at line 42, col 15:\n  <source>\n  ^` — omitted when unset, so
  existing callers see identical output.
- **`ValidationError.from_selector_error()` classmethod added (09-H4)**
  for selector-position → line/col translation.
- **`errors.format_compute_traceback()` helper added (09-H3)** — filters
  Python internals out of Starlark tracebacks so editorial authors see
  only their own `\compute` block stack.

### Pipeline & workers

- **Placeholder substitution re-entry hole closed (20-C2).** Each
  `render()` call now allocates a fresh 128-bit hex nonce baked into
  the placeholder prefix (`secrets.token_hex(16)`), and substitution
  walks markers in a single `re.sub` pass keyed by block index.
  Adversarial or buggy renderer output that happens to contain the
  legacy `\x00SCRIBA_BLOCK_N\x00` pattern can no longer trigger
  re-entrant substitution.
- **Context-provider validation (20-C1).** `Pipeline._prepare_ctx()`
  wraps each provider in `try/except` and asserts
  `isinstance(ctx, RenderContext)` after every provider returns.
  Provider exceptions are re-raised as `ValidationError` with provider
  identity; missing instance check raises with the offending type.
- **`renderer.version` coercion guarded (20-H2).** `int(renderer.version)`
  is now wrapped: non-int-coercible values yield `ValidationError`
  naming the renderer and the offending type instead of a bare
  `TypeError` mid-render.
- **Block-render error enrichment (20-M1).** Mid-loop failures are
  re-raised with `renderer.name`, block `kind`, and byte range via
  `__cause__` chaining so partial-failure diagnostics are actionable.
- **`Pipeline.close()` cleanup exceptions surfaced (20-H1).** Each
  failing `renderer.close()` now emits a `RuntimeWarning` and is
  logged with a traceback; cleanup remains best-effort.
- **Asset-path collision warning (20-M2).** When two renderers map the
  same namespaced `namespace/basename` key to different paths, a
  `UserWarning` is emitted and the first-seen path wins. Previously
  the second path silently clobbered the first.
- **`context_providers=[]` loud-opt-out (20-C3).** Passing an explicit
  empty list now emits a `UserWarning` so consumers notice they have
  opted out of every default provider (including TeX inline-rendering
  auto-wiring). Passing `None` or omitting the argument still activates
  the built-in defaults.
- **Worker JSON protocol is ASCII-safe (20-H3).** Both
  `PersistentSubprocessWorker.send` and `OneShotSubprocessWorker.send`
  now pass `ensure_ascii=True` so zero-width joiners, BOM, and LS/PS
  separators cannot break newline framing via adversarial Unicode in
  request payloads.
- **`SubprocessWorker` alias deprecated (14-H2).** The long-standing
  alias now emits a single `DeprecationWarning` at module import time.
  Identity is preserved (`isinstance` and `is` still match
  `PersistentSubprocessWorker`); the warning is the only behavioral
  change. Migrate to `PersistentSubprocessWorker`.
- **Dead `getattr` fallback removed (20-L1).** `__init__` already
  validates `renderer.name`, so the `getattr(renderer, "name",
  "unknown")` fallback in asset namespacing was unreachable and masked
  programmer errors.

### Primitives & limits

- **Matrix / DPTable raise `E1425` at cell cap (06-H2).** The error
  message now includes `rows`, `cols`, and the `rows*cols` overflow
  value so authors can see how much they were over.
- **Graph with empty nodes now raises (10-L / prior H4).**
  `Graph.__init__` raises `animation_error("E1103")` on missing or
  empty `nodes=[]` (previously warn-only). Two pre-existing tests
  updated to expect the raise.
- **Annotation list per-frame cap (10-M1).**
  `SceneState._MAX_ANNOTATIONS_PER_FRAME = 500`; overflow raises
  `ValidationError(E1103)` at `_apply_annotate()`.
- **CodePanel 1-based indexing made load-bearing (04-H4).**
  `validate_selector()` has an explicit `idx < 1` short-circuit and a
  docstring spelling out the one-off convention; boundary tests pin
  that `line[1]` is the first valid line and `line[0]` is rejected.
- **LinkedList `link[i]` semantics documented (04-M1).**
  Class-level comment pins `link[i]` as the outgoing arrow from
  `node[i]` to `node[i+1]`; valid indices are `0..N-2`.

### Spec & docs

- **Duplicate `§5.3` in `ruleset.md` renumbered (02-C1).** Former
  `§5.3` (second copy) → `§5.4`; `5.4–5.8` cascaded to `5.5–5.9`.
- **Stack spec drift fixed (04-C1).** `§5.2` / `§5.8` no longer
  reference the non-existent `cell_width` / `cell_height` / `gap`
  parameters; all remaining params clarified as optional.
- **`\begin{diagram}` marked reserved for extension E5 (01-C1).**
  v0.5.x treats diagram mode as unimplemented; parser still returns
  `AnimationIR` and the spec flags the gap explicitly.
- **`\step` forbidden inside `\foreach` documented (19-H4).** A
  prominent note in `ruleset.md §2.1` explains that `\step`,
  `\shape`, `\substory`, and `\endsubstory` are not allowed inside a
  `\foreach` body (→ `E1172`) and points at the manual-unroll pattern
  for algorithms that need per-iteration frames (monotonic stack,
  amortized walk).
- **CodePanel 1-based note added to `ruleset.md §3` (04-H4).**
- **`environments.md §3` header clarified (02-C3).** 12 block
  constructs (counted as one each).
- **`primitives.md` stale refs fixed (02-C2).**
  `04-environments-spec.md` → `environments.md`.
- **Sandbox spec §6.1 / §6.3 / §7.1 / §7.3 expanded (08-M2, 13-H1).**
  Windows SIGALRM fallback, three-layer memory enforcement,
  intentionally-allowed AST nodes (`ListComp`, `DictComp`, `SetComp`,
  `GeneratorExp`, `JoinedStr`, `isinstance`, generator `.send/.throw`)
  all documented.
- **Cookbook 06-frog1-dp `\compute{}` indentation bug fixed (18-C4).**
  The Starlark block previously had inconsistent indent levels that
  would fail Starlark parse. Rewritten with uniform 4-space indents;
  algorithmic meaning unchanged.
- **Blog post `launch-0.5.0.md` primitive count corrected (18-C3).**
  The table now enumerates all 16 primitives including the 5
  data-structure primitives (Queue, LinkedList, HashMap, CodePanel,
  VariableWatch); the stale "11 primitives" / "Plus 4 extensions"
  wording is gone.
- **CHANGELOG 0.5.0 back-fill (18-H3).** 5 data-structure primitives
  (Queue, LinkedList, HashMap, CodePanel, VariableWatch) are now
  retroactively acknowledged in the 0.5.0 "Added" section.
- **Cookbook example 11 added (19-H4):** `11-loop-to-step-manual-unroll.md`
  walks through the monotonic-stack next-greater pattern showing how
  to manually unroll `\step` blocks and use `\foreach` inside each
  step for per-iteration fanout.
- **README "Coming in v0.2.0" note removed.** The animation environment
  has been shipping since 0.2.0 and is part of 0.5.x; the forward-looking
  note was factually stale.

### Tests

- **1439 tests passing** (1311 baseline + Wave 3 additions). Wave 1+2
  contributed 50 Starlark red-team cases, 57 sanitizer-contract assertions
  (including 41 parametrized per-tag membership snapshots pinning
  `ALLOWED_TAGS` / `ALLOWED_ATTRS` against silent regression), 21 parser/
  lexer cases, 20 primitive cases, and 17 pipeline/worker cases. 16 tests
  across 8 files updated to expect the new specific error codes instead
  of `E1103`.

### Wave 3 — Test infrastructure & coverage (Cluster 7)

- **pytest-cov wired (17-H2).** `pyproject.toml` gains `pytest-cov>=5.0`
  and a `[tool.coverage.run]` / `[tool.coverage.report]` section with
  `fail_under = 75`, branch coverage, and sensible omits. Coverage runs
  opt-in via `uv run pytest --cov=scriba --cov-report=term-missing`;
  baseline is **84.33%** (above the 75% gate).
- **Hypothesis property tests (17-C1).** 10 property-based parser
  tests in `tests/unit/test_parser_hypothesis.py` covering identifiers,
  selectors, shape declarations, foreach iterables, unclosed-brace E1001,
  empty bodies, `.all` / `.node[]` / `.cell[]` accessors, and
  interpolation refs. Hypothesis is a new dev dependency.
- **`\cursor` command tests (16-C2).** 15 integration tests in
  `tests/unit/test_cursor_command.py` pinning E1180/E1181/E1182 and
  frame-to-frame state transitions. Previously the command had zero
  test coverage.
- **`\reannotate` / `\apply` / `\compute` coverage (16-H5).** 11 tests
  in `tests/unit/test_reannotate_apply_compute.py` covering recolor
  semantics, multi-primitive `\apply`, and the compute → `\foreach`
  binding bridge.
- **Error code coverage (16-C1).** 15 regression tests in
  `tests/unit/test_error_code_coverage.py` pinning previously-unverified
  codes (E1003, E1013, E1051-E1056, E1102, E1400, E1150, E1154, E1172,
  E1460, E1465, E1480). Net-new safety net against silent regression
  of error dispatch paths.
- **KaTeX worker stress tests (17-H3).** 2 tests in
  `tests/unit/test_workers_stress.py` — 100 concurrent inline-math
  requests and bad-math recovery — verifying no deadlocks and that
  one bad request does not kill the worker.

### Wave 3 — Public API surface & stability policy (Cluster 9)

- **`STABILITY.md` added at repo root (15-C1/C2/C3).** Documents the
  11 locked contracts Scriba promises to consumers: public API surface,
  `Document` shape, asset namespace format (`<renderer>/<basename>`),
  error code numbering (append-only in E1001–E1599), exception
  hierarchy, `ALLOWED_TAGS`/`ALLOWED_ATTRS`, CSS class names, SVG scene
  ID format (`scriba-<sha256[:10]>`), `SCRIBA_VERSION`, `Renderer`
  protocol, and `SubprocessWorker` deprecation. See `STABILITY.md` for
  SemVer/deprecation policy and the contract-change procedure.
- **`ScribaRuntimeError` exported from `scriba` and `scriba.core`
  (14-C1).** Previously the class existed in `scriba/core/errors.py`
  but was missing from `__all__`, so `from scriba import
  ScribaRuntimeError` failed. Now symmetric across both namespaces.
- **Lazy `SubprocessWorker` deprecation via PEP 562 `__getattr__`
  (14-H2 follow-up).** Wave 1 Cluster 3 emitted the deprecation warning
  at module import time, which fired on every plain `import scriba`.
  Wave 3 moved it to a lazy `__getattr__` hook so only external code
  that actually touches `SubprocessWorker` sees the warning; scriba's
  own internal imports and end-user `import scriba` stay silent.
- **`docs/spec/architecture.md` refreshed (14-C2).** Now documents
  `Document.block_data` and `Document.required_assets` (added in 0.1.1
  but never in the locked spec), the asset namespace format, and the
  full exception hierarchy including `ScribaRuntimeError`.
- **68 new contract-stability tests.**
  `tests/unit/test_public_api.py` (46) pins `__all__` membership for
  both `scriba` and `scriba.core`, verifies every symbol imports, and
  asserts the deprecation warning contract (silent on `import scriba`,
  fires on attribute access). `tests/unit/test_stability.py` (22)
  pins the `Document` field set, asset-key namespace separator,
  `Renderer` protocol attributes, `scriba-<sha256[:10]>` SVG ID format,
  and `ALLOWED_TAGS`/`ALLOWED_ATTRS` shape.

### Wave 3 — Ops, CI, release (Cluster 10)

- **GitHub Actions CI (`.github/workflows/test.yml`) (21-C2).**
  Python 3.10/3.11/3.12 × {ubuntu, macos} matrix with Node 20. A
  separate coverage job runs on ubuntu + Python 3.12 with
  `--cov-fail-under=75` and uploads `coverage.xml` as an artifact.
  Windows intentionally excluded; see `SECURITY.md` §Known limitations
  for the SIGALRM reason.
- **Release workflow template (`.github/workflows/release.yml`) (21-C3).**
  Triggers on `workflow_dispatch` and `push: tags v*`. Builds wheel +
  sdist via `uv build` and uploads as artifact. `uv publish` step is
  commented out pending PyPI trusted-publisher configuration; GitHub
  release job creates drafts for manual review. Clear TEMPLATE header.
- **Dependabot (`.github/dependabot.yml`).** Pip weekly, GitHub Actions
  monthly. KaTeX is vendored out-of-band, so no npm ecosystem entry.
- **`SECURITY.md` refreshed (21-C1).** Supported versions updated from
  stale `0.1.x` to `0.5.x Beta`. New "Known limitations" section
  documenting the Windows SIGALRM gap and the vendored KaTeX 0.16.11
  (latest upstream 0.16.22 is not yet integrated, pending a visual
  regression suite). New "Vendored dependencies" section pointing at
  `scripts/vendor_katex.sh` for the upgrade procedure.
- **`CONTRIBUTING.md` prerequisites section (21-H2).** Explicitly
  lists Python 3.10+, Node.js 18+, and `uv` as setup prereqs, with a
  fresh-clone quickstart (`uv sync --dev && uv run pytest -q`). Notes
  Windows is unsupported for development.
- **Homebrew formula marked as template (21-C3/21-H1).** Prominent
  header states SHA256 values will be populated at first PyPI release.
  Ruby syntax verified with `ruby -c`. Added `depends_on "node"` with
  an explanatory comment about vendored KaTeX.
- **KaTeX upgrade procedure documented (21-H4).** Seven-step checklist
  in `scripts/vendor_katex.sh` header covering release-note review,
  SHA-256 verification, full test run, snapshot-diff inspection, and
  SECURITY.md sync. The actual 0.16.11 → 0.16.22 upgrade is deferred
  to Wave 4+ pending a visual regression suite.
- **`scripts/check_deps.sh` helper.** Wraps `uv pip audit` / `pip-audit`
  for CVE scanning of the dependency tree.

### Wave 3 — Docs ecosystem cleanup (Cluster 8)

- **`CHANGELOG.md`** (this file) received the fat 0.5.1 entry you are
  reading, ingested from the Cluster 2 / Cluster 3 handoff file
  `docs/archive/production-audit-2026-04-11/changelog-pending.md`
  (now deleted).
- **5 data-structure primitives retroactively acknowledged in 0.5.0
  (18-H3).** The CHANGELOG had silently omitted Queue, LinkedList,
  HashMap, CodePanel, and VariableWatch since their introduction; they
  are now listed in the 0.5.0 "Added" section.
- **Blog post primitive count (18-C3).** `docs/blog/launch-0.5.0.md`
  now says "16 primitives" (was "11") and lists them in three labeled
  groups: Base (6), Extended (5), Data-structure (5). Removed the
  misleading "Plus 4 extensions" sentence.
- **Cookbook 06-frog1-dp Starlark indent fix (18-C4).**
  `docs/cookbook/06-frog1-dp/input.md` had inconsistent indentation in
  the `\compute` block that would have failed Starlark parse. Fixed
  to uniform 4-space style; semantics unchanged.
- **New cookbook recipe 11 (19-H4 deferred from Cluster 4).**
  `docs/cookbook/11-loop-to-step-manual-unroll.md` walks through the
  monotonic-stack next-greater pattern, showing how to manually unroll
  `\step` blocks when an algorithm needs per-iteration frames, with
  `\foreach` used inside each step for per-iteration fanout.
- **Primitive docs refreshed.** `docs/primitives/matrix.md` updated
  to 250k cell cap / E1425 (was stale 10k / E1421); `docs/primitives/
  stack.md` removed stale `cell_width`/`cell_height`/`gap` params.
- **`README.md` "Coming in v0.2.0" note removed.** Animation has been
  shipping since 0.2.0; the forward-looking paragraph was factually
  stale. Replaced with a factual 16-primitive summary.

### Wave 4A — Parser, emitter, sandbox, and test-surface polish

- **Parser improvements (01-H2, 07-M3/M4/M6, 07-H3, 09-H4).**
  Unknown primitive types rejected at parse with `E1102` + fuzzy
  "did you mean?" suggestion. Negative selector indices rejected
  with `E1010`. `\foreach` nesting depth enforced at parse time
  via `_MAX_FOREACH_DEPTH = 3` (E1170), matching the runtime
  check in `scene.py`. `${var}` interpolation references emit a
  best-effort UserWarning when no known compute-scope binding is
  declared. Selector-parse errors now carry accurate `line`/`col`.
- **Emitter `\step[label=...]` wiring (01-H1 follow-through).**
  Wave 3 Cluster 4 added AST+parser support for `FrameIR.label`;
  Wave 4A Cluster 2 wired it through 5 emitter sites. Frame IDs
  now use `{scene_id}-{label}` when the label is id-safe, else
  `{scene_id}-frame-{N}`. Duplicate labels within a scene raise
  `E1005`. Interactive widget and print-frame markup gain a
  `data-label` attribute when labels are present.
- **Starlark sandbox hardening (08-H2, 09-H3, 13-H1/H3).**
  `_FORBIDDEN_NODE_TYPES` expanded with `ast.NamedExpr` (walrus)
  and `ast.Match`. `format_compute_traceback()` helper now wired
  into `_evaluate` so `E1151` runtime errors show clean
  `<compute>` frames without Scriba-internal Python frames. Windows
  users get a one-shot `RuntimeWarning` at `StarlarkHost` init
  explaining that `SIGALRM` wall-clock backstop is Unix-only.
- **Primitive limit hardening (06-H3/H4, E1505).** Plane2D
  `_check_cap()` converted from soft-drop + log to hard-raise
  `E1466`. MetricPlot `_MAX_POINTS = 1000` cap converted to hard
  `E1483` with series name in message. Graph `layout_seed` now
  validated (rejects non-int, float, bool, negative) via `E1505`;
  `seed` accepted as alias when `layout_seed` is absent.
- **cses cookbook content fixes.** 4 files (`cses02_missing_number`,
  `cses03_repetitions`, `cses04_increasing_array`,
  `cses05_permutations`) had 2-space-indented `\compute` bodies
  that Starlark rejected as "unexpected indent". Dedented to
  column 0; 58/58 batch compile now clean.
- **Ruleset prose quality (03 series).** `docs/spec/ruleset.md`
  §1 RFC 2119 compliance note. §3.1 new "Interpolation and
  Subscript Semantics" subsection (E1155/E1156/E1157). §3.2 new
  "Command Evaluation Order". §4 `dim` state concrete CSS formula
  `color-mix(in oklch, var(--scriba-fg) 10%, transparent)`
  (previously the inaccurate "50% opacity"). §6.6 "Runtime Error
  Context". §8 frame lifecycle fully rewritten with 8 subsections
  + 13-row state-transition table. 15 prose "must/may" occurrences
  promoted to RFC 2119 MUST/MUST NOT/SHOULD.
- **Docs ecosystem sweep.** `docs/guides/editorial-principles.md`
  primitive count 6 → 16, state vocabulary corrected to canonical
  `idle/current/done/dim/good/error/path`. `docs/guides/
  diagram-plugin.md` + `animation-plugin.md` constructor signatures
  corrected (`starlark_host=` kwarg, dropped fictional
  `worker_pool`/`strict=` args). 4 primitive docs (plane2d,
  metricplot, graph-stable-layout, variablewatch) moved from
  "draft — Pivot #2" to "shipped in v0.5.x"; fictional error
  codes (E1105, E1106, E1464, E1482) removed. ~22 stale
  `04-environments-spec.md` cross-references replaced.
- **Test coverage improvement (17-H2 target).** 117 new tests
  bringing `scriba/tex/__init__.py` from 40% → 100%,
  `scriba/tex/renderer.py` 79% → 95%, `scriba/tex/highlight.py`
  49% → 87%, `scriba/core/workers.py` 71% → 82%. Overall coverage
  86% (above the 75% fail_under gate).
- **New test categories (17-M3).** `test_svg_injection.py` (19
  tests), `test_unicode_homograph.py` (17), `test_recursive_dos.py`
  (14), `test_substory_soft_limit.py` (8), and 8 new
  `TestSecurityWave4NewVectors` cases. Flagged 4 real bugs for
  Wave 4B (see below).
- **Ops follow-through.** `.github/SECURITY_CONTACTS.md` stub.
  First recorded pip-audit baseline in `docs/ops/dep-cve-baseline.md`
  (OPS-001: pygments 2.19.2 CVE-2026-4539). Visual regression
  scaffold `scripts/visual_regression/compare.py` (structural HTML
  diff; Layer 1 of a 3-layer plan documented in
  `docs/ops/visual-regression.md`).

### Wave 4B — Bug fixes from Wave 4A audit findings

- **Tree recursion DoS fix.** `reingold_tilford` converted from
  recursive DFS to iterative (explicit-stack, 3-pass). 1000/1500-
  level linear trees now build in <1s without hitting Python's
  1000-level recursion limit. Existing 80 tree tests pass
  unchanged — algorithm equivalence verified.
- **Graph O(N²) layout DoS fix.** `Graph.__init__` now raises
  `E1501` when `len(nodes) > _MAX_NODES` (100). A 1000-node cycle
  (which took ~12s force-layout under Wave 4A) is now rejected
  immediately with a message surfacing the offending count +
  `layout=stable` hint.
- **Sandbox `ast.FunctionDef` bypass fix.** `_FORBIDDEN_NODE_TYPES`
  expanded with `ast.Yield`, `ast.YieldFrom`, `ast.AsyncFunctionDef`,
  `ast.AsyncFor`, `ast.AsyncWith`, `ast.Await`. `def f(): yield 1`
  is now rejected by the pre-exec AST scan (via `ast.walk` recursion
  into function bodies), while plain `def f(): return x` helper
  functions remain legal — preserving cookbook 05/07/08 +
  `TestFunctionDef`/`TestRecursion`. `async def` is forbidden
  outright (no legitimate compute use).
- **NumberLine `ticks < 1` validation fix.** `NumberLinePrimitive`
  now raises `E1103` with explicit valid range `1..1000` when
  `ticks <= 0`. Previously the upper-bound check `ticks > 1000`
  silently accepted `ticks=0`, producing a degenerate primitive.
- **pygments CVE-2026-4539 closed.** `pyproject.toml` pin lifted
  `<2.20` → `<2.21`, pygments 2.20.0 locked. `uv run --with
  pip-audit pip-audit` now reports 0 known vulnerabilities.
  `docs/ops/dep-cve-baseline.md` updated with OPS-001 RESOLVED.
- **E1483 catalog polish.** Message updated from
  `"Series exceeded maximum point count (truncated)."` →
  `"MetricPlot series exceeded maximum point count (hard limit)."`
  matching Wave 4A Cluster 4's soft-drop → hard-raise conversion.
- **Parser source_line propagation (09-M3 follow-through).**
  `ValidationError` has a `source_line: str | None` field since
  0.1.1 but parser raise sites didn't populate it. Wave 4B Cluster
  3 wired 19 grammar.py raise sites + 6 selector-parse call sites
  via a new `SceneParser._source_line_at(line_number)` helper.
  Error messages now render a source snippet + caret pointer at
  the offending column:
  ```
  [E1053] at line 1, col 1: \highlight is not allowed in the prelude
        \highlight{a.cell[0]}
        ^
    -> https://scriba.ojcloud.dev/errors/E1053
  ```
- **Selector parser latent bug fixed.**
  `SelectorParser._error` was silently dropping `line`/`col`
  parameters entirely; now forwarded alongside `source_line`.

### Tests (final counts)

- Baseline 0.5.0: 1311 passing
- +227 from Wave 4A (parser, emitter, sandbox, coverage,
  new categories, etc.)
- +31 from Wave 4B (DoS fixes, sandbox FunctionDef gap,
  ticks<1, E1483 catalog, source_line wiring)
- Total: **1697 passing**, 1 skipped, 0 xfails, 0 failures

## [0.5.0] - 2026-04-10 (Phase D)

### Added
- Structured error codes (`E1xxx`) with line and column information for all
  parse and render errors, replacing opaque tracebacks with actionable messages.
- HARD-TO-DISPLAY verification suite achieving 9/10 coverage across edge-case
  LaTeX constructs.
- Launch blog post and documentation site.
- Homebrew tap for CLI installation (`brew install ojcloud/tap/scriba`).
- **Five data-structure primitives retroactively documented**
  (`Queue`, `LinkedList`, `HashMap`, `CodePanel`, `VariableWatch`). These
  landed across the 0.3.x–0.5.0 window without explicit CHANGELOG entries;
  they are pinned here for provenance. `CodePanel` is the one primitive
  in the catalog that uses **1-based** line indexing (every other
  primitive is 0-based) so that line numbers match the displayed
  gutter. See `docs/primitives/codepanel.md`, `queue.md`,
  `linkedlist.md`, `hashmap.md`, `variablewatch.md`.

### Changed
- Error UX overhaul: every user-facing error now carries a unique `E1xxx` code,
  source location (line/col), and a human-readable suggestion.
- Development status upgraded from Alpha to Beta in PyPI classifiers.

### Fixed
- Remaining edge cases in error reporting for deeply nested LaTeX environments.

## [0.4.0] - 2026-04-09 (Phase C)

### Added
- `Plane2D` animation primitive for 2D coordinate plane visualizations.
- `MetricPlot` animation primitive for plotting algorithmic metrics over time.
- `Graph` layout mode `layout=stable` for deterministic node positioning across
  animation frames.
- `\substory` macro for composing nested editorial sub-narratives within a
  single animation timeline.

### Changed
- Graph renderer now supports stable layout by default when `layout=stable` is
  specified, preventing node jitter between frames.

### Fixed
- Graph layout instability when nodes are added or removed between frames.

## [0.3.0] - 2026-04-09 (Phase B)

### Added
- `scriba.diagram` plugin for rendering diagram blocks alongside TeX.
- `Grid` animation primitive for 2D grid-based visualizations (BFS/DFS grids,
  game boards).
- `Tree` animation primitive for tree structure visualizations with
  auto-layout.
- `NumberLine` animation primitive for 1D range and interval visualizations.
- `figure-embed` directive for embedding static or animated figures inline
  within editorial text.
- `Matrix` and `Heatmap` animation primitives for 2D numeric data
  visualization.
- `Stack` animation primitive for LIFO data structure visualization.

### Changed
- Animation scaffold extended to support diagram-originated primitives
  alongside TeX-originated ones.

### Fixed
- Figure embedding edge cases when mixing inline TeX math with diagram
  figures.

## [0.2.0] - 2026-04-08 (Phase A)

### Added
- Animation scaffold: `@keyframes`-based CSS animation engine for editorial
  step-by-step playback.
- `Array` animation primitive for visualizing array operations (swaps,
  highlights, pointer movement).
- `DPTable` animation primitive for dynamic programming table fill
  animations.
- `Graph` animation primitive for graph algorithm visualizations (BFS, DFS,
  shortest path).
- `\hl` (highlight) LaTeX macro for marking editorial text regions that
  synchronize with animation steps.
- `@keyframes` generation from editorial step descriptors, producing
  self-contained CSS animations without JavaScript dependencies.

### Changed
- `SCRIBA_VERSION` bumped to `3` for animation-aware `Document` shape.
- `Document` dataclass extended with animation timeline metadata.

### Fixed
- Snapshot test alignment after `Document` shape changes.

## [0.1.1-alpha] - 2026-04-08

Phase 3 architect-review fixes. Bumps `SCRIBA_VERSION` to `2` because
`Document` gains `block_data` and `required_assets` fields and the
asset key shape changes (now namespaced as `<renderer>/<basename>`).

### Added
- `scriba.core.Worker` -- runtime-checkable Protocol any worker satisfies
- `scriba.core.PersistentSubprocessWorker` -- renamed from
  `SubprocessWorker` (kept as deprecated alias for one release)
- `scriba.core.OneShotSubprocessWorker` -- spawns a fresh subprocess per
  call for engines that should not be kept alive
- `SubprocessWorkerPool.register(..., mode="persistent"|"oneshot")`
- `RenderArtifact.block_id` and `RenderArtifact.data` -- public per-block
  payload exposed on `Document.block_data`
- `Document.block_data` -- `{block_id: data}` aggregated from artifacts
- `Document.required_assets` -- `{namespaced-key: Path}` map for renderer
  assets, parallel to `required_css`/`required_js`
- `Renderer.priority: int` -- overlap tie-breaker (lower wins, default 100)
- `Pipeline(..., context_providers=[...])` -- pluggable hooks; default
  set keeps the previous TeX inline-renderer auto-wiring
- `scriba.tex.tex_inline_provider` -- explicit context provider that
  callers can pass to opt out of duck-typing detection
- `scriba.tex.parser._urls.is_safe_url` -- shared URL safety check used by
  href/url and the includegraphics resolver
- `scriba.tex.parser.math.MAX_MATH_ITEMS = 500`
- `scriba.tex.renderer.MAX_SOURCE_SIZE = 1_048_576`
- New tests: oneshot worker, Worker protocol, namespaced assets,
  block_data round-trip, priority tie-breaker, math item cap, source
  size cap, four new XSS tests for href URL smuggling, image resolver
  output validation

### Changed
- **BREAKING (cache key)** `Document.required_css` / `required_js` now
  contain namespaced strings of the form `"<renderer>/<basename>"` so
  two renderers can ship files with the same basename without collision.
- `Pipeline.render` overlap resolution now sorts by
  `(block.start, renderer.priority, list-index)` instead of just
  `(start, list-index)`.
- `_is_safe_url` rewritten to use `urllib.parse.urlparse` after
  stripping all C0 control characters and unicode line/paragraph
  separators.
- `extract_math` raises `ValidationError` if more than `MAX_MATH_ITEMS`
  expressions are found.
- `TexRenderer.detect` raises `ValidationError` for sources larger than
  `MAX_SOURCE_SIZE` bytes.

### Fixed
- `TexRenderer._render_inline` and the math batch fallback now log a
  `warning` before swallowing `WorkerError`.
- `Pipeline` no longer late-imports `scriba.tex` for inline-tex wiring.
- `apply_includegraphics` validates the resolver result through
  `is_safe_url`; unsafe URLs are treated as missing images.

## [0.1.0-alpha] - 2026-04-08

First alpha release. TeX plugin generalized from an earlier in-house KaTeX
worker; diagram plugin (0.2+) reserved.

### Added
- `scriba.core.Pipeline` -- plugin orchestration with
  detect-then-render-with-placeholders
- `scriba.core.SubprocessWorkerPool` / `SubprocessWorker` -- generalized
  persistent/per-call subprocess management
- `scriba.core.{Block, RenderArtifact, Document, RenderContext,
  RendererAssets}` -- frozen dataclasses for the plugin contract
- `scriba.core.{ScribaError, RendererError, WorkerError, ValidationError}`
  -- exception hierarchy
- `scriba.tex.TexRenderer` -- LaTeX to HTML renderer with KaTeX math,
  Pygments highlighting
- Shipped static assets: `scriba-tex-content.css`,
  `scriba-tex-pygments-{light,dark}.css`, `scriba-tex-copy.js`
- `scriba.sanitize.{ALLOWED_TAGS, ALLOWED_ATTRS}` -- bleach whitelist
  matching the output contract
- 71 tests: 30 snapshot + 5 XSS + 6 validator + 9 API + 7 pipeline +
  9 workers + 7 sanitize

[0.5.1]: https://github.com/ojcloud/scriba/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/ojcloud/scriba/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/ojcloud/scriba/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/ojcloud/scriba/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ojcloud/scriba/compare/v0.1.1-alpha...v0.2.0
[0.1.1-alpha]: https://github.com/ojcloud/scriba/compare/v0.1.0-alpha...v0.1.1-alpha
[0.1.0-alpha]: https://github.com/ojcloud/scriba/releases/tag/v0.1.0-alpha
