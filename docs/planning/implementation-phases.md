# 05 — Implementation Phases

> **Revised 2026-04-09 for Pivot #2. Supersedes the prior phases document.**
> See [`00-ARCHITECTURE-DECISION-2026-04-09.md`](architecture-decision.md)
> for rationale and [`04-roadmap.md`](roadmap.md) for the milestone view.
>
> This file refines the roadmap into a week-by-week task breakdown. Every task
> binds to the contracts in [`04-environments-spec.md`](../spec/environments.md),
> [`01-architecture.md`](../spec/architecture.md), and the current
> `packages/scriba/` source tree (v0.1.1-alpha). Extension tasks bind to their
> spec files in `docs/scriba/extensions/`; primitive tasks bind to their spec
> files in `docs/scriba/primitives/`. Effort estimates assume a single mid-senior
> engineer in focused mode. With two engineers, independent bullets in the same
> section can parallelize — estimate collapses to roughly 60%.
>
> Format: each task is a single sentence + estimate (`h` = hours, `d` = days).
> Tasks are grouped by week and labelled with the file they target where possible.

## Phase A — v0.2.0 (animation + 3 base primitives + `\hl` + `@keyframes`), 3 weeks solo

Goal: `\begin{animation}` works end-to-end with `Array`, `DPTable`, `Graph`;
`\hl{step-id}{tex}` macro wired; CSS `@keyframes` named-slot infrastructure shipped.

### Week A1 — scaffolding, detector, parser, Starlark worker

**Package scaffold**
- [ ] `packages/scriba/scriba/animation/__init__.py` — create, export `AnimationRenderer` placeholder. (1 h)
- [ ] `pyproject.toml` — add `scriba.animation` to package data + `package_data` globs for `static/*.css`. (30 min)
- [ ] `scriba/_version.py` — bump to `0.2.0.dev0`; leave `SCRIBA_VERSION = 2`. (15 min)
- [ ] Delete pre-pivot `scriba/diagram/` directory and its tests. (1 h)

**Carve-out detector**
- [ ] `scriba/animation/detector.py` — scan source for `\begin{animation}` at start of line, match `\end{animation}`, return `Block` instances per `04-environments-spec.md` §2.2. (3 h)
- [ ] `tests/unit/test_animation_detector.py` — 12 cases: happy path, trailing text on begin line (`E1002`), nested begin (`E1003`), unclosed env, adjacent envs, env inside `lstlisting`, options block present, unknown key (`E1004`). (3 h)

**Renderer skeleton**
- [ ] `scriba/animation/renderer.py` — `AnimationRenderer` class, `name = "animation"`, `version = 1`, `priority = 10` (per base spec §10.2; matches `FigureEmbedRenderer.priority`; earlier = higher priority), `detect()` delegates to detector, `render_block()` raises `NotImplementedError`. (2 h)
- [ ] `tests/conftest.py` — register `AnimationRenderer` fixture alongside `tex_renderer`. (30 min)

**Inner-command parser**
- [ ] `scriba/animation/parser/lexer.py` — tokenize brace-matched args, identifiers, numbers, strings, `%` comments, `${interp}`, `[list]`. (4 h)
- [ ] `scriba/animation/parser/ast.py` — frozen dataclasses: `ShapeCmd`, `ComputeCmd`, `StepMarker`, `NarrateCmd`, `ApplyCmd`, `HighlightCmd`, `RecolorCmd`, `AnnotateCmd`, `Selector`. (2 h)
- [ ] `scriba/animation/parser/grammar.py` — recursive-descent parser following the BNF in `04-environments-spec.md` §2.1; raises `ValidationError` with position + `E1xxx` code. (5 h)
- [ ] `scriba/animation/parser/selectors.py` — selector parser for `name.cell[i]`, `name.node[${u}]`, `name.edge[(a,b)]`, `name.range[lo:hi]`, `name.all` per `04-environments-spec.md` §4. (3 h)
- [ ] `scriba/animation/parser/selectors.py` — extend base spec §4.1 selector grammar to accept `range[(NUMBER,NUMBER):(NUMBER,NUMBER)]` tuple-range form for 2D primitives (`Matrix`, `Plane2D` polygon); emit E1062 invalid-tuple-range on malformed tuple. Add 1 day to this Week. (1 d)
- [ ] `tests/unit/test_animation_parser.py` — 30 cases across all 8 commands, every error code `E10xx`/`E11xx` reachable from the parser; add tuple-range happy-path and E1062 error cases. (5 h)

**Starlark worker**
- [ ] Prototype spike: Go binary (`starlark-go`) vs pure Python (`google.starlark`), 2 h each; record findings in `07-open-questions.md` Q21. (4 h)
- [ ] `scriba/animation/starlark_worker.{go|py}` — subprocess entrypoint following the `katex_worker.js` contract: JSON-line protocol, `ready` signal on stderr, memory rlimit 64 MB, 5 s wall-clock timeout, 10^8 step cap. (1 d)
- [ ] `scriba/animation/starlark_host.py` — Python wrapper registering the worker in `SubprocessWorkerPool` as `"starlark"` with `mode="persistent"`; exposes `.eval(env_id, globals, source)`. (3 h)
- [ ] `tests/integration/test_starlark_worker.py` — 10 cases: basic eval, function def, recursion (tree DP on 1 000 nodes), timeout, step cap, memory cap, forbidden `while`, forbidden `import`, forbidden `class`, print capture. (4 h)

### Week A2 — scene, primitives, emitter, CSS, wiring

**Scene materializer**
- [ ] `scriba/animation/scene.py` — `SceneState` dict, delta application rules from `04-environments-spec.md` §6.1: inherit prev frame, clear highlights, drop ephemeral annotations, apply commands in source order. (4 h)
- [ ] `tests/unit/test_animation_scene.py` — 15 cases: persistence rules, highlight ephemerality, annotation ephemerality, frame-1 prelude inheritance, frame-local `\compute` scoping. (3 h)

**Primitives — Array, DPTable, Graph**
- [ ] `scriba/animation/primitives/base.py` — `Primitive` protocol: `declare(params) -> dict`, `addressable_parts(scene) -> list[str]`, `emit_svg(scene_entry) -> str`. (2 h)
- [ ] `scriba/animation/primitives/array.py` — `Array` with `size=`, `labels=`, `data=`; addressable parts `cell[i]`, `range[l:r]`, `all`. (5 h)
- [ ] `scriba/animation/primitives/dptable.py` — `DPTable` 1D/2D with `rows=`, `cols=`, `data=`, `headers=`; parts `cell[i]`, `cell[i][j]`, `range`, `all`. (5 h)
- [ ] `scriba/animation/primitives/graph.py` — `Graph` with `nodes=`, `edges=`, `directed=`; deterministic seeded Fruchterman–Reingold layout in pure Python. (1 d)
- [ ] `tests/integration/snapshots/animation/` — 18 snapshot SVGs covering every addressable part of the 3 primitives under every state class. (4 h)

**SVG stage emitter**
- [ ] `scriba/animation/emitter.py` — produces the HTML tree from `04-environments-spec.md` §8.1 verbatim: `<figure class="scriba-animation" ...>` → `<ol class="scriba-frames">` → `<li class="scriba-frame" data-step>` → `<header>` + `<div class="scriba-stage">` + `<p class="scriba-narration">`. (5 h)
- [ ] `scriba/animation/emitter.py` — auto-hashed scene id: `"scriba-" + sha256(env_body)[:10]`. (30 min)
- [ ] `scriba/animation/emitter.py` — `<defs>` extraction: deduplicate arrow markers and gradient defs across frames via shared `<defs>` on frame 1 + `<use>` references on frames 2..N. (3 h)

**CSS**
- [ ] `scriba/animation/static/scriba-scene-primitives.css` — base cell, node, edge, label styles using `--scriba-*` variables per `04-environments-spec.md` §9.1. (3 h)
- [ ] `scriba/animation/static/scriba-animation.css` — `.scriba-animation` filmstrip grid, `@media (max-width: 640px)` and `@media print` vertical-stack fallbacks, `.scriba-frame:target` outline, Wong CVD-safe state classes per `04-environments-spec.md` §9.2. (5 h)
- [ ] Verify contrast in light and dark themes with axe-core CLI. (1 h)

**Wiring + narration**
- [ ] `scriba/animation/renderer.py` — `AnimationRenderer.render_block()`: parser → scene → primitives → emitter; pass each `\narrate{...}` body through `ctx.render_inline_tex` (fallback to escaped plain text with `data-scriba-tex-fallback="true"` if `None`). (4 h)
- [ ] `scriba/animation/renderer.py` — frame-count limits: warning at 30 (`E1180`), error at 100 (`E1181`). (1 h)
- [ ] `tests/integration/test_animation_end_to_end.py` — 8 fixtures: binary search, knapsack, two-pointer, BFS on tiny grid, prelude-only `\shape`, frame-local `\compute`, narration with inline LaTeX, narration without `TexRenderer`. (5 h)
- [ ] `services/tenant/frontend/lib/sanitize.ts` — extend whitelist with new classes and data attributes; smoke-test in staging. (2 h)

### Week A2.5 — `\hl` macro + `@keyframes` slots

**`\hl` macro (Extension E2, spec: `docs/scriba/extensions/hl-macro.md`)**
- [ ] `scriba/animation/extensions/hl_macro.py` — parse `\hl{step-id}{tex}` calls from narration bodies; resolve `step-id` to the enclosing `scriba-frame` element id. (3 h)
- [ ] `scriba/animation/extensions/hl_macro.py` — integrate with `TexRenderer` KaTeX trust config; emit `<span class="scriba-hl" data-hl-step="step-id">` wrapping the KaTeX output. (2 h)
- [ ] `scriba/animation/static/scriba-animation.css` — add CSS `:target ~ .scriba-frames .scriba-hl[data-hl-step]` sibling-selector rule that activates highlight without JS. (2 h)
- [ ] `tests/unit/test_hl_macro.py` — 10 cases: basic highlight, multi-term highlight per step, step-id not found (`E1xxx`), XSS in tex arg, nested `\hl`, highlight in prelude narration. (3 h)
- [ ] `tests/integration/snapshots/hl/` — 4 snapshot HTML fixtures covering highlight activation state. (2 h)

**`@keyframes` animation slots (Extension E5, spec: `docs/scriba/extensions/keyframe-animation.md`)**
- [ ] `scriba/animation/extensions/keyframes.py` — named-slot registry: `rotate`, `orbit`, `pulse`, `trail`, `fade-loop` preset CSS `@keyframes` declarations. (2 h)
- [ ] `scriba/animation/extensions/keyframes.py` — slot resolution at emit time: collect declared slots from primitive SVG output, inline into each frame's `<style>` block with a `scriba-{scene-id}-{slot}` name prefix to avoid cross-frame leakage. (3 h)
- [ ] `scriba/animation/static/scriba-scene-primitives.css` — utility classes `scriba-anim-rotate`, `scriba-anim-pulse`, etc. referencing the named keyframes. (1 h)
- [ ] `tests/unit/test_keyframes.py` — 8 cases: each preset emitted correctly, name prefix applied, unknown slot raises `E1xxx`, duplicate slot deduplicated, email-client-safe scope. (2 h)
- [ ] `tests/integration/snapshots/keyframes/` — 2 snapshot fixtures: FFT twiddle-factor rotation, pulse overlay. (1 h)

**Phase A exit criteria**
- [ ] All Phase A tasks checked.
- [ ] Ojcloud tenant backend pinned to local git `scriba==0.2.0a1`.
- [ ] One real editorial rendered end-to-end in staging.
- [ ] `code-reviewer` + `security-reviewer` agents report no CRITICAL/HIGH.
- [ ] Tag `0.2.0rc1`, then `0.2.0` final after maintainer approval.

---

## Phase B — v0.3.0 (diagram + 3 base primitives + `figure-embed` + `Matrix` + `Stack`), 2.5 weeks solo

Goal: `\begin{diagram}` works; 6 base primitives complete; `figure-embed`, `Matrix`,
`Stack` shipped; 5 cookbook editorials built; 5/10 HARD-TO-DISPLAY covered.

### Week B1 — DiagramRenderer, Grid / Tree / NumberLine, cookbook rewrites

**DiagramRenderer**
- [ ] `scriba/animation/renderer.py` — add `DiagramRenderer` class sharing parser + scene + emitter with `AnimationRenderer`; reject `\step` (`E1050`), reject `\narrate` (`E1054`), allow `\compute` and `\highlight` (persistent in diagram). (4 h)
- [ ] `scriba/animation/detector.py` — add `\begin{diagram}` carve-out alongside `\begin{animation}`. (1 h)
- [ ] `scriba/animation/emitter.py` — diagram HTML shape per `04-environments-spec.md` §8.2. (2 h)
- [ ] `scriba/animation/static/scriba-diagram.css` — diagram-only overrides, optional `grid=on` debug overlay. (2 h)
- [ ] `tests/integration/test_diagram_end_to_end.py` — 6 fixtures: static tree, static DP table, static graph, `\compute`-precomputed sort, `\highlight` persistence, `grid=on` overlay. (3 h)

**Grid primitive**
- [ ] `scriba/animation/primitives/grid.py` — 2D grid with `rows=`, `cols=`, `cell[r][c]` / `all`, obstacles via `data=`. (5 h)
- [ ] `tests/integration/snapshots/grid/` — snapshot fixtures. (2 h)

**Tree primitive**
- [ ] `scriba/animation/primitives/tree.py` — Reingold–Tilford layout, root at `node[0]`, supports arbitrary `node[i]`, `edge[(p,c)]`. (1 d)
- [ ] `scriba/animation/primitives/tree.py` — test against 10 real editorial shapes (unbalanced DFS tree, segment tree, trie). (3 h)

**NumberLine primitive**
- [ ] `scriba/animation/primitives/numberline.py` — axis with `domain=`, `tick[i]`, `range[lo:hi]`. (4 h)
- [ ] `tests/integration/snapshots/numberline/` — snapshot fixtures. (2 h)

**Cookbook rewrites (5 editorials)**
- [ ] `docs/scriba/cookbook/01-binary-search/input.tex` — `Array` + `NumberLine` animation, 10 frames. (3 h)
- [ ] `docs/scriba/cookbook/02-dp-knapsack/input.tex` — 2D `DPTable` animation, 15 frames. (4 h)
- [ ] `docs/scriba/cookbook/03-bfs-grid/input.tex` — `Grid` + `Graph` animation, 20 frames. (4 h)
- [ ] `docs/scriba/cookbook/04-tree-traversal/input.tex` — `Tree` animation, 12 frames. (3 h)
- [ ] `docs/scriba/cookbook/05-segment-tree/input.tex` — `Tree` + `Array` animation, 18 frames. (4 h)
- [ ] Each cookbook entry: `expected.html` snapshot + `axe.json` accessibility audit result. (3 h)

**Migration + version bumps**
- [ ] `scriba/_version.py` — bump to `0.3.0.dev0`; `AnimationRenderer.version = 1`, `DiagramRenderer.version = 1`. (30 min)
- [ ] Write one-off migration script to rewrite lingering `d2` fenced blocks in ojcloud content to `\begin{diagram}` stubs with author-notice comments. (2 h)

### Week B2 — `figure-embed` extension

**`figure-embed` extension (Extension E1, spec: `docs/scriba/extensions/figure-embed.md`)**
- [ ] `scriba/animation/extensions/figure_embed.py` — `\begin{figure-embed}` environment detector: carve-out scanner for `\begin{figure-embed}` / `\end{figure-embed}` blocks; options: `alt=`, `caption=`, `credit=`, `src=`. (3 h)
- [ ] `scriba/animation/extensions/figure_embed.py` — SVG sanitization pass using DOMPurify (Python port or subprocess); allowlist tuned for Matplotlib SVG output; reject if `alt` or `caption` or `credit` is missing (`E1xxx` linter error). (4 h)
- [ ] `scriba/animation/extensions/figure_embed.py` — PNG pass-through path: base64-encode into `<img>`; same mandatory field validation. (2 h)
- [ ] `scriba/animation/extensions/figure_embed.py` — `scriba.lock` content-hash integration: compute SHA-256 of the embedded asset; write `{path: hash}` entry to `scriba.lock` at build time. (3 h)
- [ ] `tests/unit/test_figure_embed.py` — 12 cases: valid SVG, valid PNG, missing `alt` error, missing `credit` error, XSS script tag stripped, malicious `<use>` reference stripped, large file (`E1xxx`), hash written to lock file, hash mismatch detected on rebuild. (4 h)
- [ ] `tests/integration/snapshots/figure_embed/` — 3 snapshot fixtures: SVG embed, PNG embed, sanitized output. (2 h)

### Week B2.5 — `Matrix` and `Stack` primitives

**`Matrix` / `Heatmap` primitive (Primitive P1, spec: `docs/scriba/primitives/matrix.md`)**
- [ ] `scriba/animation/primitives/matrix.py` — `Matrix` shape: dense 2D `<svg>` grid with optional value labels; `cell[r][c]` / `all` selectors; `N ≤ 20` editorial-scale limit. (3 h)
- [ ] `scriba/animation/primitives/matrix.py` — `Heatmap` variant: `viridis`, `magma`, `rdbu` compile-time colorscales; palette lookup table hardcoded in Python (no numpy, no scipy). (3 h)
- [ ] `scriba/animation/primitives/matrix.py` — `colorscale=`, `vmin=`, `vmax=` params; cell color interpolated at build time. (2 h)
- [ ] `tests/unit/test_matrix.py` — 10 cases: basic matrix render, heatmap viridis, heatmap rdbu, missing label, size > 20 warning, `cell[r][c]` selector, `all` highlight. (3 h)
- [ ] `tests/integration/snapshots/matrix/` — 4 snapshot SVGs: sparse matrix, dense heatmap, MCMF bipartite assignment case, single-row. (2 h)

**`Stack` primitive (Primitive P2, spec: `docs/scriba/primitives/stack.md`)**
- [ ] `scriba/animation/primitives/stack.py` — `Stack` shape: vertical or horizontal sequence of labeled cells; `push`/`pop` delta semantics via scene state; `item[i]` / `top` / `all` selectors. (2 h)
- [ ] `scriba/animation/primitives/stack.py` — convex hull trick deque mode (`orientation="horizontal"`); monotone-deque annotation showing evicted lines. (2 h)
- [ ] `tests/unit/test_stack.py` — 8 cases: push, pop, peek, horizontal orientation, vertical orientation, empty-stack error, delta inheritance across frames. (2 h)
- [ ] `tests/integration/snapshots/stack/` — 3 snapshot fixtures: monotonic deque, hull stack eviction. (1 h)

**Phase B exit criteria**
- [ ] All Phase B tasks checked.
- [ ] `Document.versions` returns `{"core": 2, "tex": 1, "animation": 1, "diagram": 1}`.
- [ ] All 5 cookbook editorials pass axe-core.
- [ ] Pre-pivot `scriba.diagram` module deleted, migration script run on staging.
- [ ] Tag `0.3.0rc1`, then `0.3.0` final after maintainer approval.

---

## Phase C — v0.4.0 (heavy new primitives + docs site), 5 weeks solo

Goal: 5 high-engineering-effort Pivot #2 items shipped; docs site live; 9 HARD-TO-DISPLAY cookbook editorials built.

### Week C1 — `Plane2D` primitive

**`Plane2D` primitive (Primitive P3, spec: `docs/scriba/primitives/plane2d.md`)**
- [ ] `scriba/animation/primitives/plane2d.py` — `Plane2D` shape: fixed SVG viewport, axis grid, configurable `xrange=`, `yrange=`, `tick_spacing=`. (1 d)
- [ ] `scriba/animation/primitives/plane2d.py` — static declaration types: `line(slope, intercept)`, `point(x, y)`, `segment(x1, y1, x2, y2)`, `region(pts)` (shaded polygon). (1 d)
- [ ] `scriba/animation/primitives/plane2d.py` — `apply` command integration: highlight, recolor, add/remove individual declared items via `item[id]` selectors. (1 d)
- [ ] `scriba/animation/primitives/plane2d.py` — pure Python geometry compute helpers: line intersection, convex hull lower envelope, region inclusion test; exported for use in Starlark `@compute` blocks. (1 d)
- [ ] `scriba/animation/primitives/plane2d.py` — viewport clipping: clip all geometry to `[xrange, yrange]` at emit time; SVG `viewBox` + `clipPath` approach. (1 d)
- [ ] `tests/unit/test_plane2d.py` — 15 cases: line rendering, region shading, item selector, clip boundary, convex hull helper, lower-envelope helper, empty viewport error. (4 h)
- [ ] `tests/integration/snapshots/plane2d/` — 5 snapshot SVGs: 4-line lower envelope, query pointer, shaded feasible region, point set, segment with highlight. (3 h)

### Week C2 — `MetricPlot` + `Graph layout=stable`

**`MetricPlot` primitive (Primitive P4, spec: `docs/scriba/primitives/metricplot.md`)**
- [ ] `scriba/animation/primitives/metricplot.py` — `MetricPlot` shape: one `<svg polyline>` per scalar series, axes auto-scaled to data range, series declared via `\shape` with `series=` list. (2 h)
- [ ] `scriba/animation/primitives/metricplot.py` — frame-sync: each filmstrip frame appends the current scalar value(s) to the polyline; partial polyline emitted on frames before the last. (2 h)
- [ ] `scriba/animation/primitives/metricplot.py` — multi-series overlay: up to 6 series per plot, each styled with the Wong palette. (2 h)
- [ ] `tests/unit/test_metricplot.py` — 8 cases: single series, multi-series, auto-scale, frame-partial, empty series error, series count > 6 warning. (3 h)
- [ ] `tests/integration/snapshots/metricplot/` — 3 snapshot SVGs: potential function overlay (Splay), energy curve (SA), two-series comparison. (2 h)

**`Graph layout=stable` (Primitive P5, spec: `docs/scriba/primitives/graph-stable-layout.md`)**
- [ ] `scriba/animation/primitives/graph_stable_layout.py` — two-phase layout: (1) run Fruchterman–Reingold on the union of all frames' edge sets as an initial approximation; (2) SA refinement with cache key = `sha256(json.dumps([sorted(frame.edges) for frame in scene.frames]))` — the ordered list of per-frame edge sets, NOT the union — to avoid cache collisions between scenes with identical union but different frame orderings; (3) pin resulting positions as the stable coordinates for every frame. (1 d)
- [ ] `scriba/animation/primitives/graph_stable_layout.py` — SA refinement: after F–R, run simulated annealing joint optimization minimizing total displacement across frames while maintaining aesthetic quality; deterministic via seeded RNG. (1 d)
- [ ] `scriba/animation/primitives/graph_stable_layout.py` — expose `layout="stable"` on the existing `Graph` primitive via a delegating constructor; `layout="stable-beta"` variant emits a `data-scriba-beta="true"` attribute and a console warning on the docs site. (2 h)
- [ ] `tests/unit/test_graph_stable_layout.py` — 10 cases: basic stable layout, node position invariant across frames with edge additions, edge removals, 6-node MCMF example, determinism check (same seed → same positions), degenerate single-node, isolated nodes. (4 h)
- [ ] `tests/integration/snapshots/graph_stable/` — 4 snapshot SVGs: 6-node MCMF augmentation sequence (3 frames), butterfly graph with added edges. (2 h)

### Week C3 — `\substory` + `\fastforward`

**`\substory` extension (Extension E4, spec: `docs/scriba/extensions/substory.md`)**
- [ ] `scriba/animation/extensions/substory.py` — `\substory` / `\endsubstory` parser: recognizes the delimiters inside a `\begin{animation}` body and extracts the inner command sequence as a nested block. (2 h)
- [ ] `scriba/animation/extensions/substory.py` — nested emitter: produces a `<ol class="scriba-substory">` inside the enclosing `<li class="scriba-frame">`; indented via CSS `padding-left`. (2 h)
- [ ] `scriba/animation/static/scriba-animation.css` — `.scriba-substory` indent rules, `@media print` collapse, no JS. (1 h)
- [ ] `tests/unit/test_substory.py` — 8 cases: basic substory, multiple substories per frame, nested inside prelude, `\narrate` inside substory, missing `\endsubstory` error (`E1xxx`), substory inside diagram (should reject). (3 h)
- [ ] `tests/integration/snapshots/substory/` — 2 snapshot fixtures: Zuma interval-DP drilldown, single-substory frame. (2 h)

**`\fastforward` extension (Extension E3, spec: `docs/scriba/extensions/fastforward.md`)**
- [ ] `scriba/animation/extensions/fastforward.py` — `\fastforward{N}{sample_every=K, seed=42}` parser: validate `N > 0`, `K > 0`, `K ≤ N`, `seed` is int. (2 h)
- [ ] `scriba/animation/extensions/fastforward.py` — Starlark worker elevated limits: for a `\fastforward` block, set `step_cap = N × 10^8` and inject the seeded RNG into the worker globals as `rand = Rand(seed)`; restore default cap after the block. (3 h)
- [ ] `scriba/animation/extensions/fastforward.py` — frame sampling: run the `@compute` block `N` times, emit one filmstrip frame every `K` iterations; enforce the 100-frame hard limit across the sampled frames (`E1181`). (3 h)
- [ ] `tests/unit/test_fastforward.py` — 10 cases: basic fast-forward, determinism (same seed), `sample_every` boundary, step cap exceeded error, frame limit from sampling, missing `seed` default applied, SA energy convergence example (output frames monotone-decreasing energy). (4 h)
- [ ] `tests/integration/snapshots/fastforward/` — 2 snapshot fixtures: SA with `N=1000, sample_every=33` producing 30 frames. (2 h)

### Week C4 — docs site + integration examples

- [ ] Scaffold `docs-site/` with Astro Starlight; configure sidebar from `docs/scriba/` file order. (3 h)
- [ ] Port `01-architecture.md`, `02-tex-plugin.md`, `04-environments-spec.md`, `04-roadmap.md`, `06-out-of-scope.md`, `07-open-questions.md` to `docs-site/src/content/docs/`. (3 h)
- [ ] Error catalog page auto-generated from `scriba/animation/errors.py`. (2 h)
- [ ] Primitive reference page auto-generated from docstrings (all 11 primitives). (3 h)
- [ ] Extension reference page auto-generated from docstrings (all 5 extensions). (2 h)
- [ ] Cookbook gallery page: each editorial rendered via a live `Pipeline.render()` call at build time. (4 h)
- [ ] Dark/light toggle, search, versioned sidebar. (2 h)
- [ ] `examples/plain-html/` — 30-line Python script + bleach sanitize pass. (2 h)
- [ ] `examples/nextjs/` — App Router `route.ts` renders at build time; `dangerouslySetInnerHTML` in a server component. (4 h)
- [ ] `examples/astro/` — Content Collection integration. (3 h)
- [ ] `examples/mdbook/` — Rust preprocessor routing `{{#scriba}}` blocks through `Pipeline`. (4 h)
- [ ] Playwright smoke test per example: load → assert `<figure class="scriba-animation">` rendered. (3 h)
- [ ] `README.md` rewrite: lead with `\begin{animation}` hello-world; remove all D2/Mermaid language. (2 h)
- [ ] `docs/scriba/contributing.md` — branch naming, PR template, test matrix. (2 h)

### Week C5 — HARD-TO-DISPLAY cookbook demos + accessibility audit

- [ ] `docs/scriba/cookbook/06-zuma-interval-dp/input.tex` — `DPTable` + `\substory` + `\hl`; covers HARD-TO-DISPLAY #1. (4 h)
- [ ] `docs/scriba/cookbook/07-miller-rabin/input.tex` — `Array` + `\hl`; covers HARD-TO-DISPLAY #2. (3 h)
- [ ] `docs/scriba/cookbook/08-fft-butterfly/input.tex` — `Graph` + `@keyframes rotate` + multi-`\apply`; covers HARD-TO-DISPLAY #4. (5 h)
- [ ] `docs/scriba/cookbook/09-mcmf-dense/input.tex` — `Graph layout=stable` + `Matrix` heatmap; covers HARD-TO-DISPLAY #5. (4 h)
- [ ] `docs/scriba/cookbook/10-convex-hull-trick/input.tex` — `Plane2D` + `Stack`; covers HARD-TO-DISPLAY #6. (4 h)
- [ ] `docs/scriba/cookbook/11-splay-amortized/input.tex` — `MetricPlot` + `Tree` + `\hl`; covers HARD-TO-DISPLAY #7. (4 h)
- [ ] `docs/scriba/cookbook/12-burnside/input.tex` — `Grid` + `\hl`; covers HARD-TO-DISPLAY #8. (3 h)
- [ ] `docs/scriba/cookbook/13-simulated-annealing/input.tex` — `\fastforward` + `MetricPlot` + `figure-embed`; covers HARD-TO-DISPLAY #9. (5 h)
- [ ] `docs/scriba/cookbook/14-planar-separator/input.tex` — `figure-embed` + `Graph`; covers HARD-TO-DISPLAY #10. (3 h)
- [ ] Run axe-core accessibility audit on all 9 new cookbook editorials; fix all CRITICAL/HIGH findings. (4 h)
- [ ] `services/tenant/frontend/lib/sanitize.ts` — update whitelist to include all new CSS classes and `data-scriba-*` attributes introduced by Pivot #2 extensions (see `docs/scriba/extensions/SANITIZER-WHITELIST-DELTA.md` for the canonical delta list). Smoke-test in staging. (2 h)
- [ ] Document the canonical `scriba-*` class namespace and `data-scriba-*` attribute prefix convention in `docs/scriba/extensions/SANITIZER-WHITELIST-DELTA.md`. (1 h)
- [ ] Deploy docs site to staging. Tag `0.4.0rc1`, then `0.4.0` final. (2 h)

**Phase C exit criteria**
- [ ] All Phase C tasks checked.
- [ ] 9/10 HARD-TO-DISPLAY cookbook editorials render in staging, both themes.
- [ ] All Pivot #2 features ship with snapshot tests.
- [ ] `code-reviewer` + `security-reviewer` agents report no CRITICAL/HIGH.

---

## Phase D — v0.5.0 (polish + launch + HARD-TO-DISPLAY verification), 1.5 weeks solo

Goal: production-grade error UX, Homebrew tap, PyPI final, launch, and formal
9/10 HARD-TO-DISPLAY coverage verification.

### Week D1 — error UX, Homebrew tap, PyPI, launch

- [ ] `scriba/animation/errors.py` — every `E1xxx` emits source line + col + URL to the docs-site error page; add `error_url(code: str) -> str` helper. (4 h)
- [ ] `scriba/animation/errors.py` — `error_url()` used by both runtime and docs-site codegen to keep URLs in sync. (1 h)
- [ ] `tests/` — golden error snapshot suite: 40 cases, one per defined `E1xxx`. (4 h)
- [ ] Homebrew tap repo `ojcloud/homebrew-tap` with `scriba.rb` formula; CI tests `brew install` on macOS arm64 and x86_64. (4 h)
- [ ] Launch blog post on `scriba.ojcloud.dev/blog/`. (3 h)
- [ ] HN / Lobsters / CP Discord announcement drafts. (2 h)
- [ ] Final PyPI upload: `python -m build && twine upload dist/*`. (1 h)
- [ ] Tag `0.5.0` final after all checks green; human approval from ojcloud maintainers. (1 h)

### Week D1.5 — HARD-TO-DISPLAY verification

- [ ] Produce one canonical editorial per covered problem (problems 1–2, 4–10): verify it builds cleanly from source, renders correctly in staging, passes axe-core. (1 d)
- [ ] Verify portability of all 9 editorials: copy HTML to a Codeforces blog draft (sandbox), GitHub Markdown preview, and a plain-HTML email client; confirm no JS required, no broken rendering. (4 h)
- [ ] Document Problem #3 (4D Knapsack) as a known partial in `docs-site/src/content/docs/coverage.md`: show the 2-slice DPTable workaround, explain the cognitive limit, link to the architecture decision. (2 h)
- [ ] Publish HARD-TO-DISPLAY coverage matrix as a docs site page, cross-linked from the cookbook gallery. (2 h)
- [ ] Final `0.5.0` tag on docs site; confirm all canonical URLs stable. (1 h)

**Phase D exit criteria**
- [ ] All Phase D tasks checked.
- [ ] `scriba 0.5.0` on PyPI.
- [ ] `brew install scriba` green on arm64 and x86_64.
- [ ] 9 covered HARD-TO-DISPLAY editorials published on docs site.
- [ ] Problem #3 documented as a known partial with rationale.
- [ ] No CRITICAL or HIGH issues open.

---

## Summary of totals

| Phase | Tasks (approx) | Solo effort | 2-eng effort | Key deliverables |
|-------|----------------|-------------|--------------|-----------------|
| A | ~52 | 15 d | ~9 d | Animation env, 3 base primitives, `\hl`, `@keyframes`, tuple-range selector |
| B | ~35 | 12.5 d | ~7.5 d | Diagram env, 3 base primitives, `figure-embed`, `Matrix`, `Stack` |
| C | ~55 | 25 d | ~15 d | `Plane2D`, `MetricPlot`, `Graph stable`, `\substory`, `\fastforward`, docs site, 9 cookbook editorials |
| D | ~15 | 7.5 d | ~5 d | Error UX, Homebrew, PyPI, 9/10 coverage verification |
| **Total** | **~155** | **~12 weeks** | **~7–8 weeks** | **9/10 HARD-TO-DISPLAY, 100% portability** |

## Cross-reference

- [`04-roadmap.md`](roadmap.md) — milestone-level view; phase allocation rationale; Pivot #2 feature list.
- [`00-ARCHITECTURE-DECISION-2026-04-09.md`](architecture-decision.md) — HARD-TO-DISPLAY coverage matrix; rejected alternatives.
- [`04-environments-spec.md`](../spec/environments.md) — source of truth for grammar, selectors, HTML shape, error codes referenced in every task above.
- [`07-open-questions.md`](open-questions.md) — Q21 on Starlark host choice may reshape Week A1 tasks.
- [`docs/scriba/extensions/hl-macro.md`](../extensions/hl-macro.md) — E2 spec.
- [`docs/scriba/extensions/keyframe-animation.md`](../extensions/keyframe-animation.md) — E5 spec.
- [`docs/scriba/extensions/figure-embed.md`](../extensions/figure-embed.md) — E1 spec.
- [`docs/scriba/extensions/substory.md`](../extensions/substory.md) — E4 spec.
- [`docs/scriba/extensions/fastforward.md`](../extensions/fastforward.md) — E3 spec.
- [`docs/scriba/primitives/matrix.md`](../primitives/matrix.md) — P1 spec.
- [`docs/scriba/primitives/stack.md`](../primitives/stack.md) — P2 spec.
- [`docs/scriba/primitives/plane2d.md`](../primitives/plane2d.md) — P3 spec.
- [`docs/scriba/primitives/metricplot.md`](../primitives/metricplot.md) — P4 spec.
- [`docs/scriba/primitives/graph-stable-layout.md`](../primitives/graph-stable-layout.md) — P5 spec.
- [`cookbook/HARD-TO-DISPLAY.md`](../cookbook/HARD-TO-DISPLAY.md) — editorial stress test that motivated Pivot #2; 9 of 10 problems resolved in Phase C.
