# 04 — Roadmap

> **Revised 2026-04-09 for Pivot #2. Supersedes the prior roadmap.**
> See [`00-ARCHITECTURE-DECISION-2026-04-09.md`](architecture-decision.md)
> for rationale. The source of truth for the base environments model remains
> [`04-environments-spec.md`](../spec/environments.md); all milestones below bind
> to the class names, environment grammar, HTML output shape, error codes, and CSS
> contract defined there. Do not relitigate locked decisions in this file; open an
> entry in [`07-open-questions.md`](open-questions.md) instead.

## 1. Current state — v0.1.1-alpha (shipped)

Scriba `0.1.1-alpha` is live on the ojcloud tenant and published internally. It contains:

- `scriba.core` — `Pipeline`, `Document`, `RenderArtifact`, `RenderContext`,
  `PersistentSubprocessWorker` / `OneShotSubprocessWorker`, `SubprocessWorkerPool`,
  `Worker` protocol, exception hierarchy.
- `scriba.tex` — full TeX plugin: KaTeX math, Pygments highlighting, `\includegraphics`,
  URL safety, source-size caps (`MAX_SOURCE_SIZE = 1_048_576`), math-item caps
  (`MAX_MATH_ITEMS = 500`), and four-case XSS hardening.
- `scriba.sanitize` — `ALLOWED_TAGS`, `ALLOWED_ATTRS` consumer whitelist.
- 71 passing tests (snapshot, XSS, validator, pipeline, workers, sanitize).
- `SCRIBA_VERSION = 2`, `TexRenderer.version = 1`.
- Namespaced `required_css` / `required_js` / `required_assets` keyed by
  `"<renderer>/<basename>"`.

The base locked spec (`04-environments-spec.md`) is frozen: `\begin{animation}`,
`\begin{diagram}`, the 6 original primitives (`Array`, `DPTable`, `Graph`, `Grid`,
`Tree`, `NumberLine`), Starlark worker, filmstrip HTML shape, CSS contract, and error
codes are **unchanged**. Pivot #2 ADDS 10 features — 5 extensions and 5 primitives —
without modifying the base grammar. All additions are pure Python, compile-time,
zero runtime JS.

The 10 additions and their coverage targets are documented in
[`00-ARCHITECTURE-DECISION-2026-04-09.md`](architecture-decision.md).
Extension specs live in [`docs/scriba/extensions/`](../extensions/) and primitive specs
in [`docs/scriba/primitives/`](../primitives/).

## 2. Roadmap at a glance

| Version | Phase | Scope | Solo effort | 2-eng effort | GA blocker? |
|---------|-------|-------|-------------|--------------|-------------|
| **0.2.0** | A | `\begin{animation}` scaffold + `Array`/`DPTable`/`Graph` + `\hl` macro (E2) + `@keyframes` slots (E5) | 3 weeks | ~2 weeks | Yes |
| **0.3.0** | B | `\begin{diagram}` + `Grid`/`Tree`/`NumberLine` + `figure-embed` (E1) + `Matrix`/`Heatmap` (P1) + `Stack` (P2) | 2.5 weeks | ~1.5 weeks | Yes |
| **0.4.0** | C | `Plane2D` (P3) + `MetricPlot` (P4) + `Graph layout=stable` (P5) + `\substory` (E4) + `\fastforward` (E3) + docs site + integration examples | 5 weeks | ~3 weeks | Yes |
| **0.5.0** | D | Polish, error UX, PyPI final, Homebrew tap, launch + HARD-TO-DISPLAY verification | 1.5 weeks | ~1 week | — |
| post-0.5 | — | On-demand primitives, optional Lit 3 interactive runtime (deferred) | on demand | No | — |

**Total to v0.5 GA: ~12.5 weeks solo, ~7.5–8.5 weeks with 2 engineers.**

## 3. Philosophy

### Dual output modes (interactive default, static for portability)

`AnimationRenderer` supports two output modes (see `04-environments-spec.md` §8.0):

- **Interactive mode** (default): renders a single widget with step controller,
  keyboard navigation, progress dots, and frame transitions. Includes a small
  (~2KB) inline `<script>`. This is the default for ojcloud tenant and any web
  platform.
- **Static mode**: compiles to a pure `<figure>` + `<ol>` + inline `<svg>`
  filmstrip with zero runtime JavaScript. The HTML works in email, RSS, print,
  PDF export, Codeforces embed, and any sanitizer-aware consumer.

The zero-JS constraint applies only to static mode. Interactive mode is the
default for web platforms where JavaScript is available. Consumers select the
mode via `RenderContext.metadata["output_mode"]`.

### Build-time determinism

`\compute{...}` Starlark runs once in a sandboxed `SubprocessWorker`. No RNG,
no clocks, no I/O, no `load()`. Identical source + identical Scriba version +
identical Starlark worker version = byte-identical HTML. `\fastforward` preserves
this contract via a seeded RNG (`seed=42` default). This is what keeps the
consumer's content-hash cache (`Document.versions`) correct across redeploys.

### 0.x is unstable

Breaking changes between minor releases are permitted in the 0.x series. Any
change to the HTML output shape of a plugin MUST bump that plugin's integer
`version` field before tagging. Consumers key their render cache on
`Document.versions`; a silent HTML change without a version bump is a cache
corruption bug.

Version fields tracked:

- `SCRIBA_VERSION` — core abstractions. Currently `2`. Bumps only on core API
  changes (frozen dataclass fields, protocol signatures).
- `TexRenderer.version` — TeX HTML shape. Currently `1`.
- `AnimationRenderer.version` — introduced at `0.2.0`, starts at `1`.
- `DiagramRenderer.version` — introduced at `0.3.0`, starts at `1`.
- `FigureEmbedRenderer.version` — introduced at `0.3.0`, starts at `1`. Any
  change to the `<figure class="scriba-figure-embed">` HTML output shape MUST
  bump this value to avoid silent cache corruption in `Document.versions`.

### Portability as a first-class goal

Editorial output must render correctly in Codeforces blog posts, AtCoder editorials,
GitHub Markdown, email clients, RSS readers, PDF renderers, and Notion — without
modification, without a JS runtime, without a CDN dependency. Every primitive, every
extension, every CSS pattern is evaluated against this constraint before acceptance.
This is why the runtime-JS path (research A1–A8) was rejected in Pivot #2: covering
9/10 HARD-TO-DISPLAY problems is worthless if the output is stripped by 5 of the 7
target platforms.

### Ship strategy

1. **PyPI first** — every alpha/RC/final tag is published to PyPI as `scriba`.
2. **Homebrew tap at 0.5.0** — `brew install ojcloud/tap/scriba` for cookbook
   authors who want the CLI examples to work without Python tooling.
3. **Docs site concurrent with 0.4.0** — Astro Starlight built from the
   `docs/scriba/` directory in the monorepo, deployed to
   `scriba.ojcloud.dev` (or equivalent) on every tag.

No version is tagged until ojcloud's tenant backend has migrated to it.
Tagging final requires human approval from ojcloud maintainers.

## 4. Phase A — v0.2.0 (animation + 3 base primitives + `\hl` + `@keyframes`)

### 4.1 Goals

Ship a working `\begin{animation}` environment end-to-end for three of the six
locked primitive types: `Array`, `DPTable`, `Graph`. These three cover roughly
60% of the CP editorial genres ojcloud publishes. Layer on the two lowest-risk
Pivot #2 additions — the `\hl` macro (E2) and CSS `@keyframes` slots (E5) — both
of which extend `TexRenderer` and the SVG emitter without touching the parser or
Starlark host.

### 4.2 Deliverables

- `scriba/animation/__init__.py` — exports `AnimationRenderer`.
- `scriba/animation/renderer.py` — `AnimationRenderer`, `name = "animation"`,
  `version = 1`, `priority = 10` (per base spec §10.2; earlier = higher priority,
  first-wins).
- `scriba/animation/detector.py` — regex carve-out scanner per
  `04-environments-spec.md` §2.2.
- `scriba/animation/parser/` — lexer, AST, grammar, selector parser for the 8
  inner commands per `04-environments-spec.md` §3–4.
- `scriba/animation/scene.py` — `SceneState` delta materializer per
  `04-environments-spec.md` §6.1.
- `scriba/animation/starlark_worker.{go|py}` + `scriba/animation/starlark_host.py`.
- `scriba/animation/primitives/array.py`, `dptable.py`, `graph.py`.
- `scriba/animation/emitter.py` — frozen HTML shape from `04-environments-spec.md` §8.1.
- `scriba/animation/static/scriba-animation.css` + `scriba-scene-primitives.css`
  per `04-environments-spec.md` §9.
- `scriba/animation/errors.py` — error code table `E10xx`/`E11xx`.
- **Pivot #2 — Extension E2:** `scriba/animation/extensions/hl_macro.py` —
  `\hl{step-id}{tex}` macro integration with `TexRenderer`; CSS `:target` sibling
  selector wired in `scriba-animation.css`. Spec:
  [`docs/scriba/extensions/hl-macro.md`](../extensions/hl-macro.md).
- **Pivot #2 — Extension E5:** `scriba/animation/extensions/keyframes.py` —
  CSS `@keyframes` named slot infrastructure: `rotate`, `orbit`, `pulse`,
  `trail`, `fade-loop` presets inlined into frame `<style>`. Spec:
  [`docs/scriba/extensions/keyframe-animation.md`](../extensions/keyframe-animation.md).

### 4.3 Success criteria

- [ ] A problem editorial written against three base primitives renders in staging.
- [ ] `\hl{step-id}{tex}` highlights the correct KaTeX term when the browser
      navigates to `#step-id`; zero JS required; passes axe-core.
- [ ] `@keyframes rotate` preset emitted correctly for an FFT twiddle-factor example.
- [ ] `\narrate{...}` with inline LaTeX routes through `ctx.render_inline_tex`.
- [ ] Starlark subprocess worker registers in `SubprocessWorkerPool` and
      survives 5 000 requests without leak.
- [ ] Frame-count soft limit (`E1180`, >30) and hard limit (`E1181`, >100)
      enforced and tested.
- [ ] CSS passes axe-core contrast checks in both light and dark themes.
- [ ] Filmstrip collapses to vertical `@media print` and `@media (max-width: 640px)`.
- [ ] No CRITICAL or HIGH issues from code review.
- [ ] `AnimationRenderer.version = 1` recorded in `Document.versions`.

### 4.4 Risk register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Starlark worker implementation choice (Go binary vs pure Python) | Medium | Prototype spike tracked in `07-open-questions.md` Q21. |
| Per-frame SVG size bloat on 30-frame animations | Medium | Share `<defs>` via `<use>` references; measure after primitives land. |
| `\hl` KaTeX trust config interacting with existing TexRenderer XSS hardening | Low | Extend the four-case XSS test suite to cover the new macro; security-reviewer agent pre-commit. |
| `@keyframes` leaking across frames in email clients | Low | Scope keyframe names with a per-scene hash prefix; test in Apple Mail and Gmail web. |
| Phase A parser budget underestimated | Medium | Phase A extended to 3 weeks (from 2.5) to accommodate: (a) `\hl` implicit label vs `\fastforward` step-label scheme alignment; (b) base-spec delta for `range[(NUMBER,NUMBER):(NUMBER,NUMBER)]` tuple-range selector grammar for 2D primitives (`Matrix`, `Plane2D` polygon) — adds E1062 invalid-tuple-range to the parser; (c) base-spec delta for `\step[label=]` syntax from hl-macro.md. |

## 5. Phase B — v0.3.0 (diagram + 3 base primitives + `figure-embed` + `Matrix` + `Stack`)

### 5.1 Goals

Ship `\begin{diagram}`, the remaining three base primitives (`Grid`, `Tree`,
`NumberLine`), and rewrite five flagship cookbook editorials. Layer on three
Pivot #2 additions that are architecturally similar to existing work: `figure-embed`
(E1, compile-time SVG pass-through), `Matrix`/`Heatmap` (P1, sibling of `DPTable`),
and `Stack` (P2, simple monotone-sequence shape). At the end of Phase B the full
v0.3 locked spec is implemented and 5/10 HARD-TO-DISPLAY problems are covered.

### 5.2 Deliverables

- `scriba/animation/renderer.py` — add `DiagramRenderer` (`name = "diagram"`,
  `version = 1`). Reuses parser, Starlark host, emitter from Phase A. Differences:
  `\step`/`\narrate` forbidden (`E1050`, `E1054`), `\highlight` persistent.
  HTML shape per `04-environments-spec.md` §8.2.
- `scriba/animation/primitives/grid.py`, `tree.py`, `numberline.py`.
- `scriba/animation/static/scriba-diagram.css`.
- `docs/scriba/cookbook/` rewrites (5 editorials: binary search, DP knapsack,
  BFS grid, tree traversal, segment tree).
- **Pivot #2 — Extension E1:** `scriba/animation/extensions/figure_embed.py` —
  `\begin{figure-embed}` environment: DOMPurify SVG sanitization, PNG pass-through,
  mandatory `alt`/`caption`/`credit` linter, `scriba.lock` content-hash entry.
  Spec: [`docs/scriba/extensions/figure-embed.md`](../extensions/figure-embed.md).
- **Pivot #2 — Primitive P1:** `scriba/animation/primitives/matrix.py` —
  `Matrix` + `Heatmap` with `viridis`/`magma`/`rdbu` compile-time colorscales,
  value-label overlay, `cell[r][c]`/`all` selectors, N ≤ 20 editorial scale.
  Spec: [`docs/scriba/primitives/matrix.md`](../primitives/matrix.md).
- **Pivot #2 — Primitive P2:** `scriba/animation/primitives/stack.py` — `Stack`
  vertical/horizontal labeled sequence with push/pop delta semantics.
  Spec: [`docs/scriba/primitives/stack.md`](../primitives/stack.md).
- One-off migration script for lingering pre-pivot `d2` fenced blocks.

### 5.3 Success criteria

- [ ] All five cookbook editorials build and render in staging, both themes.
- [ ] `Document.versions` at v0.3.0 returns `{"core": 2, "tex": 1,
      "animation": 1, "diagram": 1, "figure-embed": 1}`.
- [ ] `figure-embed` with a hand-crafted SVG renders sanitized output with
      `alt` and `caption` visible; missing `credit` raises `E1xxx` linter error.
- [ ] `scriba.lock` records a SHA-256 content hash for each embedded asset.
- [ ] `Matrix` heatmap (N=6 MCMF bipartite case) renders a color-scaled SVG
      matching the `viridis` palette reference snapshots.
- [ ] `Stack` push/pop operations animate via CSS state classes.
- [ ] Tenant frontend sanitizer whitelist updated for new classes and data
      attributes per `04-environments-spec.md` §8.
- [ ] Cookbook editorials pass axe-core accessibility audit.
- [ ] Pre-pivot `scriba.diagram` module deleted.

### 5.4 Risk register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Existing ojcloud content authored against pre-pivot `d2` blocks | Medium | Migration script + author-notice comments. See `05-migration.md`. |
| Tree primitive layout for unbalanced trees | Medium | Reingold–Tilford; test against 10 real CP editorials. |
| DOMPurify SVG allowlist overly permissive or too strict for real Matplotlib output | Medium | Audit 10 real Matplotlib SVG exports; tune allowlist; freeze in `figure_embed.py`. |
| `scriba.lock` format compatibility across Scriba versions | Low | Lock format versioned independently; document in spec. |

## 6. Phase C — v0.4.0 (heavy new primitives + docs site)

### 6.1 Goals

Ship the five most engineering-intensive Pivot #2 additions: `Plane2D` (P3),
`MetricPlot` (P4), `Graph layout=stable` (P5), `\substory` (E4), and `\fastforward`
(E3). These are clustered in Phase C because they require the most design care —
three of the five require non-trivial algorithms (simulated annealing layout
optimizer, seeded multi-iteration Starlark worker, nested filmstrip emitter).
Concurrent with Phase C: stand up the public docs site, integration examples, and
rewrite cookbook entries for the remaining HARD-TO-DISPLAY problems.

By the end of Phase C, 9/10 HARD-TO-DISPLAY problems are covered.

### 6.2 Deliverables

- **Pivot #2 — Primitive P3:** `scriba/animation/primitives/plane2d.py` —
  `Plane2D` 2D coordinate plane: fixed axis grid, animatable lines/points/segments/
  shaded regions, pure Python geometry compute helpers, viewport + transform.
  Spec: [`docs/scriba/primitives/plane2d.md`](../primitives/plane2d.md).
- **Pivot #2 — Primitive P4:** `scriba/animation/primitives/metricplot.py` —
  `MetricPlot` compile-time SVG line chart: `<svg polyline>` per series, scalar
  tracking across filmstrip frames, multi-series overlay.
  Spec: [`docs/scriba/primitives/metricplot.md`](../primitives/metricplot.md).
- **Pivot #2 — Primitive P5:** `scriba/animation/primitives/graph_stable_layout.py`
  — `Graph layout=stable` mode: pure Python SA joint-optimization across all
  animation frames; node positions computed once at build time and pinned.
  Spec: [`docs/scriba/primitives/graph-stable-layout.md`](../primitives/graph-stable-layout.md).
- **Pivot #2 — Extension E4:** `scriba/animation/extensions/substory.py` —
  `\substory` / `\endsubstory` inline linear drilldown: nested `<ol>` inside the
  enclosing `<li class="scriba-frame">`, CSS-only indent.
  Spec: [`docs/scriba/extensions/substory.md`](../extensions/substory.md).
- **Pivot #2 — Extension E3:** `scriba/animation/extensions/fastforward.py` —
  `\fastforward{N}{sample_every=K, seed=42}` meta-step: elevated Starlark worker
  step cap for the block, seeded RNG, frame sampling.
  Spec: `docs/scriba/extensions/fastforward.md` (removed).
- `docs-site/` — Astro Starlight project; sidebar from `docs/scriba/`; error
  catalog and primitive reference auto-generated.
- `examples/plain-html/`, `examples/nextjs/`, `examples/astro/`, `examples/mdbook/`.
- Cookbook entries for all 9 covered HARD-TO-DISPLAY problems.
- `docs/scriba/contributing.md`.

### 6.3 Success criteria

- [ ] `Plane2D` renders the Li Chao Tree lower-envelope example from HARD-TO-DISPLAY
      §6 as a static SVG with ≥ 4 lines + a query pointer, with correct geometry.
- [ ] `MetricPlot` overlays a `Φ(T)` potential curve across a Splay Tree animation
      (HARD-TO-DISPLAY §7 example).
- [ ] `Graph layout=stable` holds node positions stable across a 10-augmentation
      MCMF example with 6 nodes; positions computed once at build time.
- [ ] `\substory` renders as a nested `<ol>` inside the parent frame; no JS.
- [ ] `\fastforward{1000}{sample_every=33}` produces exactly 30 frames from a
      1 000-iteration SA run; identical output on repeated builds (seeded RNG).
- [ ] Docs site deployed with search, versioned sidebar, dark/light toggle.
- [ ] Each integration example has a working Playwright smoke test.
- [ ] All 9 covered HARD-TO-DISPLAY cookbook editorials build and pass axe-core.
- [ ] `README.md` passes `markdown-link-check`.

### 6.4 Risk register

| Risk | Severity | Mitigation |
|------|----------|------------|
| SA layout optimizer quality: node overlap or bad aspect ratio | High | Seed sweep + visual regression suite; expose `iterations=` knob in spec; document limits. |
| `Graph layout=stable` cache key correctness | High | Cache key MUST be `sha256(json.dumps([sorted(frame.edges) for frame in scene.frames]))` — i.e., a hash of the **ordered list of per-frame edge sets**, NOT the union of all edges. Two scenes with the same union but different frame orderings must NOT cache-collide. See `primitives/graph-stable-layout.md` §5.2. |
| `\fastforward` elevated step cap interacting with memory rlimit | Medium | Profile peak RSS at N=10^4; lower cap if needed; document ceiling in spec. |
| `Plane2D` SVG size with N ≥ 30 lines per frame | Medium | Clip to viewport at emit time; de-duplicate identical axis SVG via `<use>`. |
| Phase C scope (5 weeks solo) exceeding window | Medium | If SA layout stalls, ship `Graph layout=stable` as `layout="stable-beta"` with a warning. Parallelize with 2-eng split: eng-1 takes primitives, eng-2 takes docs site + cookbook. |

## 7. Phase D — v0.5.0 (polish + launch + HARD-TO-DISPLAY verification)

### 7.1 Goals

Polish error UX, finalize launch messaging, publish to PyPI as final (not alpha),
create the Homebrew tap, and announce. Add a half-week HARD-TO-DISPLAY coverage
verification pass: produce one canonical editorial per covered problem, run the
accessibility audit, and document the known partial (Problem #3, 4D Knapsack).

### 7.2 Deliverables

- Error messages surface `E1xxx` codes with source line + column and a
  pointer to the error-catalog page on the docs site.
- `brew tap ojcloud/tap` + `brew install scriba` formula.
- Launch blog post + community thread drafts (HN, Lobsters, CP Discord).
- Final `0.5.0` tag on PyPI.
- HARD-TO-DISPLAY coverage report: one editorial per covered problem (9),
  accessibility audit results, explicit documentation that Problem #3 (4D Knapsack)
  remains partial due to cognitive limits (see architecture decision §Consequences).

### 7.3 Success criteria

- [ ] `scriba 0.5.0` on PyPI with full changelog.
- [ ] `brew install scriba` works on macOS arm64 and x86_64.
- [ ] Announcement published; at least one external CP community reads it.
- [ ] No CRITICAL or HIGH issues open on the tracker.
- [ ] 9/10 HARD-TO-DISPLAY problems have a published editorial in the docs site
      cookbook; Problem #3 is documented as a known partial with rationale.
- [ ] All 9 covered editorials pass axe-core; CLS < 0.1 on filmstrip scroll.

## 8. Revised timeline summary

| Milestone | Solo effort | 2-eng effort | Key deliverables |
|-----------|-------------|--------------|-----------------|
| v0.2.0 | 3 weeks | ~2 weeks | `\begin{animation}`, `Array`/`DPTable`/`Graph`, `\hl`, `@keyframes` slots |
| v0.3.0 | 2.5 weeks | ~1.5 weeks | `\begin{diagram}`, `Grid`/`Tree`/`NumberLine`, `figure-embed`, `Matrix`, `Stack` |
| v0.4.0 | 5 weeks | ~3 weeks | `Plane2D`, `MetricPlot`, `Graph layout=stable`, `\substory`, `\fastforward`, docs site |
| v0.5.0 GA | 1.5 weeks | ~1 week | Polish, PyPI final, Homebrew, 9/10 HARD-TO-DISPLAY verification |
| **Total** | **~12 weeks** | **~7–8 weeks** | **9/10 HARD-TO-DISPLAY coverage, 100% portability** |

## 9. Post-launch (0.6+)

| Feature | Trigger | Status |
|---------|---------|--------|
| Lit 3 interactive runtime (opt-in scrubber) | Sustained demand from consumers who accept JS-only contexts | Deferred; may not happen |
| Additional primitives (Heap, SegTree, UnitCircle, Tensor slice) | Specific CP editorial requests with a PRD | On demand |
| 4D Tensor primitive with slice scrubber | Enough demand from multidimensional DP editorial authors | Deferred; HARD-TO-DISPLAY §3 accepted as cognitive limit |
| 1.0 API freeze | Two consecutive minor releases with no HTML shape change + one external OJ in production | Not scheduled |

See [`06-out-of-scope.md`](out-of-scope.md) for features that are **explicitly not
coming** in the 0.x series, including the interactive scrubber, true FFT-parallel
step mode, and Manim-class continuous animation.

## 10. Cross-reference

| Document | Relationship |
|----------|--------------|
| [`00-ARCHITECTURE-DECISION-2026-04-09.md`](architecture-decision.md) | Pivot #2 rationale, coverage matrix, rejected alternatives. |
| [`01-architecture.md`](../spec/architecture.md) | Locks `Pipeline`, `Renderer`, `SubprocessWorkerPool`. |
| [`02-tex-plugin.md`](../guides/tex-plugin.md) | v0.1 TeX internals. Still current. |
| [`04-environments-spec.md`](../spec/environments.md) | Locked grammar, HTML shape, CSS contract, error codes for v0.2–v0.3. Extended by Pivot #2, not replaced. |
| [`05-implementation-phases.md`](implementation-phases.md) | Week-by-week task breakdown refining this roadmap. |
| [`06-out-of-scope.md`](out-of-scope.md) | Explicit non-goals. |
| [`07-open-questions.md`](open-questions.md) | Deferred decisions (Q21: Starlark host choice). |
| [`cookbook/HARD-TO-DISPLAY.md`](../cookbook/HARD-TO-DISPLAY.md) | 10-problem stress test that motivated Pivot #2. |
| [`extensions/figure-embed.md`](../extensions/figure-embed.md) | E1 spec (written by Agent 2). |
| [`extensions/hl-macro.md`](../extensions/hl-macro.md) | E2 spec (written by Agent 2). |
| `extensions/fastforward.md` | E3 spec (removed). |
| [`extensions/substory.md`](../extensions/substory.md) | E4 spec (written by Agent 2). |
| [`extensions/keyframe-animation.md`](../extensions/keyframe-animation.md) | E5 spec (written by Agent 2). |
| [`primitives/matrix.md`](../primitives/matrix.md) | P1 spec (written by Agent 3). |
| [`primitives/stack.md`](../primitives/stack.md) | P2 spec (written by Agent 3). |
| [`primitives/plane2d.md`](../primitives/plane2d.md) | P3 spec (written by Agent 3). |
| [`primitives/metricplot.md`](../primitives/metricplot.md) | P4 spec (written by Agent 3). |
| [`primitives/graph-stable-layout.md`](../primitives/graph-stable-layout.md) | P5 spec (written by Agent 3). |
