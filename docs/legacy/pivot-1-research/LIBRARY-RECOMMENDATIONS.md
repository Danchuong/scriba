# Scriba Library Recommendations — Synthesis

> Tổng hợp 8 research reports trong `docs/scriba/research/01..08`. Mỗi report đứng riêng với chi tiết comparison + implementation tasks. File này chỉ là **single-page summary + ranking** dùng cho roadmap planning.

---

## TL;DR — single recommendation per gap

| # | Gap | Library / approach | License | Bundle | Effort |
|---|---|---|---|---|---|
| 1 | Animatable equations | **KaTeX** + `\hl{}` macro + sidecar DOM | MIT | (build-time) | Low |
| 2 | 2D continuous geometry | **Two.js** (render) + **flatten-js** (compute) | MIT + MIT | ~55 KB | Medium |
| 3 | Graph layout beyond D2 | **Graphviz** (sfdp/circo/twopi) + **ELK.js** (compound + incremental) | EPL-1.0 + EPL-2.0 | (build-time) | Medium |
| 4 | Animation engine | **Motion One** (WAAPI wrapper) | MIT | ~18 KB | Medium |
| 5 | Plot / instrumentation | **uPlot** (runtime) + **Observable Plot** (SSR/print) | MIT + ISC | ~50 KB + (build) | Medium |
| 6 | Manim-style math animation | **Accept defeat** — extend A1 với `::eqn-steps` + `::math-video` link | — | 0 | Trivial |
| 7 | Widget runtime | **Lit 3** Custom Element per widget | BSD-3 | ~5 KB | Medium |
| 8 | Escape hatch | **Excalidraw** authoring + `embed`/`sequence`/`link` directives + DOMPurify SVG | MIT | 0 (compile-time) | Low |

**Tổng bundle runtime per widget**: ~73 KB gzipped (Motion One 18 + uPlot 50 + Lit 5). Within Scriba's "compiles to clean HTML you can email" promise, just barely.

---

## Per-gap summary

### A1 — Animatable equations (`research/01-animatable-equations.md`)
- **KaTeX** is the only renderer with fast deterministic SSR + `\htmlId` trust macro + small footprint
- Author writes `\hl{step1}{a^d}`, preprocessor expands to `\htmlId{E__step1}{\htmlClass{tex-term}{...}}`
- Animation = CSS class toggling on `.tex-term[data-step]`, reuses existing step controller
- Pipeline: **sidecar DOM** (NOT `<foreignObject>`, NOT D2 label HTML) — each scene emits 1 D2 SVG + N absolutely-positioned equation divs
- Source map via `\htmlData{origin=L:C}` round-tripping through KaTeX
- **Unlocks**: Frog DP recurrence highlight, Burnside derivation, Mobius inversion, loop invariants
- **Effort**: low (extends existing TexRenderer)

### A2 — 2D continuous geometry (`research/02-2d-geometry.md`)
- No single library covers both CP geometry semantics + keyframe-diffable SSR-able SVG
- **Split: Two.js (render) + flatten-js (compute) + Scriba-owned algorithm simulators**
- Two.js: MIT, ~55KB, headless Node SVG, scene graph
- flatten-js: pure geometry (point/line/polygon/segment ops, no rendering)
- New `plane` shape primitive, declarative DSL: `plane hull_demo { points = [...]; algorithm = "andrew_monotone" }`
- **Rejected**: GeoGebra (proprietary/iframe), JSXGraph (kept as fallback), Konva (canvas-only), Paper.js (no good SSR)
- **Unlocks**: convex hull, half-plane intersection, line sweep, rotating calipers, Li Chao tree
- **Risks**: tween topology changes (vertex count differs frame-to-frame), half-plane numerical stability
- **Effort**: medium (~1 engineer-week)

### A3 — Graph layout beyond D2 (`research/03-graph-layout-beyond-d2.md`)
- D2 stays default. Add **two complementary engines**:
  - **Graphviz** (sfdp/circo/twopi/neato) — large graphs, force-directed, non-hierarchical, CLI subprocess (mirrors D2's pipeline shape)
  - **ELK.js** — compound nesting, ports, **position-stable incremental layout** for animation frames
- **No engine does true planar embedding** — planar demos need hand-coordinates or offline `networkx.planar_layout`
- ELK is the ONLY credible option for stable-position incremental layout (treap/splay rotations) via `interactive` mode with coordinate hints
- Dispatcher: select by `layout:` field in IR. Single worker pool for D2+Graphviz binaries, separate `worker_threads` for ELK
- Cache: `(backend, version, ir-hash)` content-hash
- **Rejected**: Cytoscape/G6/Sigma/vis (runtime-interactive first, not SSR)
- **Unlocks**: suffix automaton, Tarjan SCC, Dinic level graph, treap rotation morph
- **Effort**: medium

### A4 — Animation engine (`research/04-animation-engines.md`)
- **Motion One** behind a thin Scriba `Tween` adapter
- MIT, ~18KB min+gz, delegates to native WAAPI for compositor-driven SVG morphs
- Native scrubbing via `AnimationControls.currentTime`
- Good `prefers-reduced-motion` ergonomics
- GSAP rejected (license + bundle); anime.js v4 kept as drop-in fallback
- New IR: `Delta { tweens[]; substeps[] }`
- New DSL: `substeps { @Nms "label" {...} }` for sub-step keyframes; standalone `animate` blocks for continuous params (calipers angle, FFT rotation)
- **Risks**: Safari WAAPI SVG quirks, scrub-mid-tween reproducibility, reduced-motion fallback
- **Acceptance test**: splay rotation demo
- **Unlocks**: splay/treap morph, SAM clone sub-frames, sliding window pointer, FFT butterfly timing, ghost trails
- **Effort**: medium

### A5 — Plot / instrumentation (`research/05-plot-instrumentation.md`)
- **uPlot** as runtime renderer (sub-50KB, multi-series, log axes, annotations, Grafana-adjacent track record)
- Pair with **Observable Plot** invoked build-time in Node for static artifacts + PDF export
- Runtime interactivity → uPlot. Print/SSR initial frame → Observable Plot
- **Rejected**: Chart.js (bloated canvas), ECharts (500KB), Vega-Lite (200KB), Recharts/Visx (React), Frappe (abandoned), peity/sparkline (no multi-series)
- **Fallback**: Observable Plot alone if Node SSR complexity is unwelcome (~5ms redraw at 2k pts is acceptable for our step counts)
- **Unlocks**: sliding window pointer counter, splay potential plot, Mo's amortization, simulated annealing temperature
- **Effort**: medium

### A6 — Manim-style math animation (`research/06-manim-style-math-animation.md`)
- **Verdict: accept defeat on Manim-class integration**
- No surveyed tool (Manim CE, Motion Canvas, Penrose, Theatre.js, Mafs, Framer Motion, MathBox, reveal.js, WebManim, smile.js) satisfies all of: build-time CLI + per-step SVG output + equation term-rewriting semantics + KaTeX compatibility
- Manim needs 5GB LaTeX install and rasterizes TeX to `<image>`; Motion Canvas is canvas-raster; Penrose has no temporal/rewrite model
- **Recommendation**:
  1. Extend Agent 1 with `::eqn-steps` primitive emitting N KaTeX SVGs + step manifest — covers Frog DP, Burnside, Mobius, loop invariants
  2. Add `::math-video` primitive linking to external videos (3B1B for FFT) — for genuinely continuous derivations
  3. Add "Manim integration" to `docs/scriba/non-goals.md`
- **Effort**: trivial (compose with A1)

### A7 — Widget runtime (`research/07-widget-runtime.md`)
- **Lit 3** inside a single Custom Element per widget — emit `<scriba-widget>` tag with inline `<script type="module">`
- Shadow DOM is non-negotiable: prevents CSS leakage between multiple widgets per page
- BSD-3, ~5KB runtime, SSR-friendly (`@lit-labs/ssr`)
- Sub-widget composition via nested custom elements with isolated state
- Print-friendly fallback via `@media print` collapsing to keyframe image
- **Migration**: cookbook outputs go from inline JS → `<scriba-widget>` tag. Backward-compat via codegen.
- **Unlocks**: multi-widget pages, hover-to-reveal interactivity, recursive drilldown, isolated state
- **Effort**: medium (one-time runtime rewrite)

### A8 — Escape hatch (`research/08-escape-hatch.md`)
- **Excalidraw** as primary authoring tool (whiteboard aesthetic matches CP editorial vibe)
- tldraw for collaboration, Figma only if already in use
- **Format**: inline SVG primary, PNG@2x fallback. Reject Lottie/GIF/MP4 in-tree
- **Syntax**: `embed "path.svg" { alt caption credit }`, plus `sequence` block for multi-frame hand-drawn cascades, plus `link` for external video cards
- Embedded SVGs **replace** (not overlay) the auto-canvas for their step
- ID-namespacing lets `highlight` still target glyphs inside hand-drawn figures
- **Determinism**: SHA-256 per embed in `scriba.lock`, keyed to tenant-backend HTML cache
- **Print/email**: SVG inline for HTML/PDF, parallel PNG@1200px for email
- **Sanitization**: DOMPurify SVG profile (mandatory)
- **Author rules**: alt+caption+credit mandatory (compiler hard-fails on missing alt); lint warning if >30% of steps are embeds
- **Unlocks**: planar separator, MCMF residual graph, splay rotation cascade, FFT butterfly textbook figure, external video links
- **Effort**: low

---

## Coverage matrix — hostile problems × unlocked by

| Problem | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 |
|---|---|---|---|---|---|---|---|---|
| Zuma interval DP | ✓ | | | ✓ | | | | |
| Miller-Rabin primality | ✓ | | | | | ⚪ | | |
| 4D Knapsack | | | | | | | ✓ | |
| FFT / NTT | ✓ | | | ✓ | | ⚪→video | | ✓ |
| Min-Cost Max-Flow | | | ✓ | | | | | ✓ |
| Li Chao tree | ✓ | ✓ | | ✓ | | | | |
| Splay amortized | | | ✓ | ✓ | ✓ | | | |
| Burnside / Pólya | ✓ | | | | | ⚪ | | |
| Simulated Annealing | | | | | ✓ | | | |
| Planar separator | | | ⚠ | | | | | ✓ |
| Sliding window amortized | | | | ✓ | ✓ | | | |
| Mo's algorithm | | | | ✓ | ✓ | | | |
| Suffix automaton | | | ✓ | ✓ | | | | |
| Tarjan SCC | | | ✓ | | | | | |
| Half-plane intersection | | ✓ | | ✓ | | | | |
| Convex hull animation | | ✓ | | ✓ | | | | |

✓ = directly unlocked  ⚪ = partial / depends on extension  ⚠ = "no engine does this, escape hatch needed"

**All 10 hostile problems get at least partial coverage.** MCMF and planar separator land in the "escape hatch" bucket as expected.

---

## Roadmap by impact × effort

### Phase A (v0.3.1 — quick wins, ship in 2 weeks)
1. **A1 KaTeX `\hl{}` macro + sidecar DOM** — extends existing TexRenderer, low risk, unlocks 5+ problems
2. **A8 Escape hatch (`embed` directive + DOMPurify)** — pure compile-time, unlocks "give up gracefully" cases, sets quality bar via mandatory alt/caption/credit
3. **A6 `::math-video` link primitive** — trivial composition, prevents wasted Manim integration effort

### Phase B (v0.4 — runtime + animation rebuild, ship in 4-6 weeks)
4. **A7 Lit 3 Custom Element runtime** — must come before A4 because animation engine needs a stable runtime substrate. One-time rewrite of the cookbook output codegen.
5. **A4 Motion One adapter + sub-step DSL** — splay rotation as acceptance test
6. **A3 Graphviz subprocess + ELK.js worker** — D2 stays default; new dispatcher selects by `layout:` field

### Phase C (v0.5 — geometry + plotting, ship in 6-8 weeks)
7. **A2 `plane` primitive: Two.js + flatten-js** — unlocks all of computational geometry
8. **A5 `plot` primitive: uPlot runtime + Observable Plot SSR** — finishes the amortization story

### Phase D (v0.6+ — research / accept-defeat)
9. **Sub-widget composition** (recursive drilldown) — needs A7 to be stable first
10. **Tensor slice scrubber** for 4D DP — niche, low priority
11. **Continuous parameter animation** for FFT roots/calipers — explore via A4's `animate` block

---

## Risks & open questions

| Risk | Severity | Mitigation |
|---|---|---|
| Bundle bloat (A4 + A5 + A7 = ~73KB) | Medium | Code-split per shape primitive; widgets without `plane`/`plot` skip those libs |
| Build pipeline becomes Node-heavy (KaTeX + ELK.js + Observable Plot all want Node) | Medium | Pin Node version in `scriba.toml`, single worker pool, content-hash cache |
| Two.js + flatten-js split adds 2 deps to maintain | Low | Both MIT, both stable, clear ownership boundary |
| Lit 3 migration breaks existing cookbook outputs | Medium | Gate behind v0.4 major bump; provide vanilla codegen as fallback for v0.3.x |
| Manim "accept defeat" disappoints math editorial authors | Low | A1 + `::eqn-steps` covers 80% of math editorial needs; `::math-video` covers the rest with external links |
| ELK.js incremental layout doesn't handle rotation cleanly | High | Splay rotation demo is the acceptance test; if it fails, fall back to manual coordinate hints in IR |

---

## Implementation order — concrete next 5 PRs

1. **PR #1**: A1 `\hl{}` macro + sidecar DOM for equations (Phase A) — **low risk, high leverage**
2. **PR #2**: A8 `embed` directive + DOMPurify SVG sanitizer + alt/caption mandatory linter (Phase A)
3. **PR #3**: A6 `::math-video` link primitive (Phase A) — 1-day task
4. **PR #4**: A7 Lit 3 runtime rewrite (Phase B) — most invasive, gates Phase B
5. **PR #5**: A4 Motion One adapter + splay rotation demo (Phase B) — first visual win on hard problems

After PR #5 ships, re-evaluate Phase C priorities based on which cookbook examples land first.

---

## Files

- `01-animatable-equations.md` — KaTeX `\hl{}` + sidecar DOM
- `02-2d-geometry.md` — Two.js + flatten-js
- `03-graph-layout-beyond-d2.md` — Graphviz + ELK.js
- `04-animation-engines.md` — Motion One
- `05-plot-instrumentation.md` — uPlot + Observable Plot
- `06-manim-style-math-animation.md` — accept defeat
- `07-widget-runtime.md` — Lit 3
- `08-escape-hatch.md` — Excalidraw + `embed` directive

Each contains full comparison matrix, top-3 deep dive, API sketch, risks, and implementation tasks.
