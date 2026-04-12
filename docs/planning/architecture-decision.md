# Pivot #2: Zero-JS maxed out for HARD-TO-DISPLAY coverage (2026-04-09)

**Status:** ACCEPTED

---

## Context

Three facts forced a decision:

1. **Locked spec covers 1/10 HARD-TO-DISPLAY problems.** `environments.md` defines a solid foundation — `Array`, `DPTable`, `Graph`, `Grid`, `Tree`, `NumberLine`, `\begin{animation}`, `\begin{diagram}`, Starlark worker, filmstrip HTML. That primitive set is sufficient for ~70% of everyday CP editorials but handles only one of the ten pathological cases catalogued in `cookbook/HARD-TO-DISPLAY.md` (Problem #1 Zuma, partially, via DPTable).

2. **Pre-pivot research A1–A8 covers 9/10 but kills portability.** The research documents in `legacy/pivot-1-research/` proposed augmenting Scriba with Lit 3 custom elements, Motion One animations, uPlot charts, ELK.js graph layout, and a Graphviz WASM runtime. That architecture would cover 9 of the 10 hard problems. It was **rejected** because runtime JavaScript is stripped by Codeforces, AtCoder, GitHub Markdown, email clients, PDF renderers, and Notion — the exact platforms where CP editorials live. Shipping a Scriba that requires a JS runtime defeats the purpose.

3. **A third option exists.** Every capability in A1–A8 that requires runtime JS can be reimplemented as a pure-Python, compile-time primitive that emits deterministic SVG. The insight: we do not need Motion One to animate twiddle-factor rotation; we need a `@keyframes` slot in the SVG emitter. We do not need ELK.js to stabilize graph layout across frames; we need a `Graph layout=stable` mode computed once at build time. We do not need uPlot to render a metric chart; we need a `MetricPlot` primitive that emits a `<svg polyline>`. Extending the locked spec to max out this primitive set closes the gap without touching the portability contract.

---

## Decision

Extend the zero-JS locked spec (`environments.md`) with 10 new features grouped in two batches. The `\begin{animation}` and `\begin{diagram}` environments, Starlark worker, and filmstrip HTML shape are **unchanged**. All additions are pure Python, compile-time, zero runtime JS.

### Extensions (5) — new environments and macros

| ID | Feature | Summary |
|----|---------|---------|
| E1 | `\begin{figure-embed}` | Vetted SVG embed with DOMPurify; `alt`, `caption`, `credit` mandatory. Lets authors include hand-crafted or Matplotlib-generated SVGs as filmstrip frames. |
| E2 | `\hl{step-id}{tex}` | LaTeX term highlight macro synced to filmstrip frame via CSS `:target` selector. Zero JS — the browser's built-in fragment navigation drives the highlight. |
| E3 | `\fastforward{N}{sample_every=K}` | Meta-step for iterative heuristics. Tells the Starlark worker to run the `@compute` block N times and emit one frame every K iterations. Determinism preserved via seeded RNG. |
| E4 | `\substory` / `\endsubstory` | Inline linear drilldown. Expands to a nested `<ol>` inside the enclosing filmstrip frame. Replaces the "recursive callout sub-widget" proposal from research — same intent, CSS-only, no JS. |
| E5 | CSS `@keyframes` animation slot | A named slot in the SVG emitter that lets primitives declare a `@keyframes` block inlined into the `<style>` of a frame. Enables continuous rotation (FFT twiddle factors), pulse, and fade effects entirely in CSS. |

### Primitives (5) — new shape types

| ID | Primitive | Summary |
|----|-----------|---------|
| P1 | `Matrix` / `Heatmap` | Dense 2D data visualization. Renders as an `<svg>` grid of colored cells with optional value labels. Covers residual-graph snapshots and bipartite assignment matrices at editorial scale (N ≤ 20). |
| P2 | `Stack` | Monotonic deque / hull stack. Renders as a horizontal or vertical sequence of cells with push/pop animations. Covers the convex hull trick deque operations. |
| P3 | `Plane2D` | 2D coordinate plane with animatable lines, points, segments, and shaded regions. Emits a pure `<svg>` viewport with a fixed axis grid. Covers convex hull trick geometry and computational geometry editorials broadly. Replaces the Two.js proposal from research A2. |
| P4 | `MetricPlot` | Compile-time SVG line chart that tracks one or more scalar values across filmstrip frames. Emits a `<svg polyline>` per series. Covers potential-function overlays (Splay), energy curves (SA), and any convergence argument. Replaces the uPlot proposal from research A5. |
| P5 | `Graph layout=stable` | Joint layout optimization precomputed across all frames of an animation, so node positions do not jump when edges are added or removed. Replaces the ELK.js proposal from research A3. |

---

## Consequences

### Positive

- **9/10 HARD-TO-DISPLAY coverage** (Problem #3 4D Knapsack remains partial — see below).
- **100% portability preserved.** No runtime JS added. Output still works in Codeforces editorials, AtCoder, GitHub, email, PDF, Notion.
- **Pure Python pipeline.** No Node runtime, no WASM sidecar, no CDN dependency.
- **Determinism preserved.** All new primitives emit SVG deterministically; `\fastforward` uses seeded RNG. The content-hash cache in `tenant-backend` continues to work without modification.
- **Scope-contained.** All 10 new features fit inside the existing `Renderer` + `Pipeline` + Starlark worker architecture. No architectural surgery required.

### Negative

- **+3.5 weeks timeline.** 12 weeks total to v0.5 GA instead of the ~5 weeks projected by the locked base roadmap. Agent 4 will rewrite `04-roadmap.md` and `05-implementation-phases.md` with the revised schedule.
- **Problem #3 (4D Knapsack) still partial.** Small-multiples DPTable covers 2 synchronized 2D slices of a 4D tensor. The full tensor visualization requires a Tensor primitive with a scrubber (research item #7, labelled "effort: high"). This is accepted as a cognitive limit: no platform covers 4D DP well, and the editorial value is low relative to the implementation cost.

### Neutral

- Research dir A1–A8 archived to `legacy/pivot-1-research/`. Ideas cherry-picked; implementations rewritten in Python from scratch.
- The `\begin{figure-embed}` escape hatch formally accepts Problem #10 (Planar Separator) as "accept the limitation" — authors provide a hand-crafted SVG, Scriba handles the narration wrapper.

---

## Coverage matrix

| # | Problem | Primary Scriba feature | Status |
|---|---------|----------------------|--------|
| 1 | Zuma (interval DP + palindrome merge) | `\substory` + `DPTable` + `\hl` | Full |
| 2 | Miller–Rabin Primality | `\hl` + `Array` | Full |
| 3 | 4D Knapsack / multidimensional DP | Small-multiples `DPTable` (2 slices) | Partial (cognitive limit) |
| 4 | FFT / NTT butterfly | `Graph` + CSS `@keyframes` slot + multi-`\apply` | Full |
| 5 | Min-Cost Max-Flow on dense graph | `Graph layout=stable` + `Matrix` | Full (at N ≤ 20 editorial scale) |
| 6 | Convex Hull Trick / Li Chao Tree | `Plane2D` + `Stack` | Full |
| 7 | Splay Tree amortized analysis | `MetricPlot` + `Tree` + `\hl` | Full |
| 8 | Burnside / Pólya counting | `\hl` + `Grid` | Full |
| 9 | Simulated Annealing | `\fastforward` + `MetricPlot` + `figure-embed` | Full |
| 10 | Planar Separator / Graph Minor | `figure-embed` + `Graph` | Full (author provides SVG) |

---

## Rejected alternatives

**(a) Ship locked spec as-is.** Covers 1/10 HARD-TO-DISPLAY. Rejected — the gap is too large to call v0.5 a credible CP editorial tool.

**(b) Option A: runtime JS (research A1–A8).** Covers 9/10. Rejected — breaks portability to every target platform (Codeforces, AtCoder, GitHub, email, PDF, Notion). This was the core finding that triggered Pivot #2.

**(c) Dual render path (static + interactive).** Compile two output variants and let platforms pick. Estimated 6–8 months to spec, implement, test, and maintain two diverging output contracts. Rejected — disproportionate cost, and the static-only path already covers 9/10 problems cleanly.

---

## Related documents

| Document | Role |
|----------|------|
| [`environments.md`](../spec/environments.md) | Base locked spec. Still the single source of truth for `\begin{animation}`, `\begin{diagram}`, inner commands, Starlark host, filmstrip HTML shape. EXTENDED by this decision, not replaced. |
| [`04-roadmap.md`](roadmap.md) | Will be rewritten by Agent 4 to reflect the 12-week revised timeline. |
| [`05-implementation-phases.md`](implementation-phases.md) | Will be rewritten by Agent 4 with revised phases incorporating 10 new features. |
| [`extensions/`](../extensions/) | Agent 2 will write 5 spec files: `figure-embed.md`, `hl-macro.md`, `fastforward.md`, `substory.md`, `keyframe-animation.md`. |
| [`primitives/`](../primitives/) | Agent 3 will write 5 spec files: `matrix.md`, `stack.md`, `plane2d.md`, `metricplot.md`, `graph-stable-layout.md`. |
| [`legacy/pivot-1-research/`](../legacy/pivot-1-research/) | Archived A1–A8 research documents. Preserved for decision trail only. Do not cite as current spec. |
| [`cookbook/HARD-TO-DISPLAY.md`](../cookbook/HARD-TO-DISPLAY.md) | The 10-problem stress test that motivated this decision. |
