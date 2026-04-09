# Plot Instrumentation for Scriba Widgets

**Status:** Research / decision memo
**Scope:** Embedding a small, Tufte-style metric plot primitive inside Scriba CP editorial widgets so that amortization arguments (sliding window, splay potential, Mo's algorithm, simulated annealing) become visually legible per algorithmic step.

---

## Executive summary

**Adopt uPlot as the runtime renderer for Scriba `plot` widgets.** It is the only library in the field that combines a sub-50 KB footprint with per-step incremental updates, multi-series support, log axes, annotation plugins, and a production track record at Grafana-adjacent scale. It is canvas-first, which conflicts with Scriba's print/PDF/Tufte bias — so we pair it with a build-time SVG renderer (**Observable Plot** invoked in Node during compile) for static artifacts and PDF export. Runtime interactivity uses uPlot; server-rendered initial frame and print output use Observable Plot.

**Fallback:** If the Node-side SSR complexity is unwelcome, use **Observable Plot alone**, rendering SVG on every update. It is slower (~5 ms per redraw at 2k points) but correct, Tufte-aligned, and ships one mental model. For our step counts (hundreds, occasionally low thousands), this is acceptable.

**Explicitly rejected:** Chart.js (canvas, too opinionated, bloated), ECharts (500+ KB, wrong tool), Vega-Lite (declarative tax, 200+ KB runtime), Recharts/Visx (React-only — excluded by the brief), Frappe (cute but abandoned, no log axis), peity/sparkline.js (no multi-series, no annotations). Raw D3 is the floor, not a recommendation.

---

## Comparison matrix

| Library          | Bundle (min+gz) | Output  | API for 1-line 1-metric | SSR | Smooth update | Multi-series | Annotations      | License | Tufte-friendly |
|------------------|-----------------|---------|-------------------------|-----|---------------|--------------|------------------|---------|----------------|
| Observable Plot  | ~45 KB          | SVG     | Excellent (`Plot.lineY`)| Yes (Node)| Manual re-render | Yes | Yes (`Plot.text`)| ISC     | Excellent       |
| Vega-Lite        | ~210 KB (+Vega 320 KB) | SVG/Canvas | OK (JSON spec) | Yes (Node) | Built-in transition | Yes | Yes (layer)   | BSD-3   | Possible        |
| **uPlot**        | **~45 KB (~15 KB gz)** | Canvas | Good (array-of-arrays)  | No (canvas) | `setData()` instant | Yes | Plugin (`hooks`) | MIT | Good (configurable) |
| Chart.js v4      | ~75 KB gz       | Canvas  | Verbose (dataset config)| No  | Built-in tween | Yes | `chartjs-plugin-annotation` | MIT | Mediocre |
| D3 v7            | ~90 KB gz (full)| SVG     | Verbose (primitives)    | Yes | Manual        | Yes | Hand-rolled      | ISC     | Whatever you build |
| Apache ECharts   | ~330 KB gz      | Canvas/SVG | Heavy (option tree)  | Yes | Built-in      | Yes | Yes (`markLine`) | Apache-2| Mediocre |
| Frappe Charts    | ~20 KB gz       | SVG     | Simple                  | No (DOM) | Built-in | Limited | Basic        | MIT     | OK, no log axis |
| Recharts         | ~95 KB gz       | SVG     | React-only              | —   | —             | Yes          | Yes              | MIT     | — (excluded) |
| Visx             | ~50 KB gz/module | SVG    | React-only              | —   | —             | Yes          | Yes              | MIT     | — (excluded) |
| peity / sparkline.js | ~3 KB gz    | SVG/Canvas | Excellent for sparkline | Yes/No | None    | No           | No               | MIT     | Sparkline only |

(Sizes approximate, from bundlephobia / pkg-size as of 2024–2025; treat as order-of-magnitude, not contractual.)

---

## Top 3 deep dive

### 1. uPlot — runtime winner

- **Why:** Built explicitly for time-series incremental updates. `u.setData([xs, ys1, ys2])` re-renders in under a millisecond for 10k points on commodity hardware (leeoniya's benchmarks, github.com/leeoniya/uPlot). At Scriba's ~1000 points it is imperceptible.
- **API shape:** `new uPlot({width, height, series: [{}, {label, stroke}], scales: {y: {distr: 3 /* log */}}}, data, container)`. Low-level but small surface.
- **Multi-series + log axis:** First-class. Annealing's temperature-and-energy chart is literally an example in the uPlot docs.
- **Annotations:** No native markLine. Community plugin `uPlot-hooks` / the `hooks` API lets us draw custom overlay in `draw` hook — about 20 lines to annotate rotation events on splay chart.
- **Tradeoff:** Canvas. Bad for print, PDF export, dark-mode theming via CSS vars, and Tufte's "ink as text" aesthetic. We compensate with a parallel SSR path (below).
- **License:** MIT.

### 2. Observable Plot — SSR and print winner

- **Why:** Grammar of graphics, SVG output, headless via `jsdom`, authored by Mike Bostock. Idiomatic for editorial/scientific visuals — the closest thing to a Tufte API on npm.
- **API shape:** `Plot.plot({marks: [Plot.lineY(data, {x: "step", y: "phi"}), Plot.ruleX([rotations], {stroke: "red"})]}).outerHTML`. One mark per series, annotations are just more marks.
- **SSR:** Runs under Node with `jsdom` — returns SVG string directly. Perfect for Scriba's build-time HTML cache path (we already compile widgets server-side for the tenant-backend HTML cache, c.f. `0c36be0`).
- **Update animation:** None built-in. For runtime updates you re-render and swap innerHTML. Acceptable at <1k points; wasteful beyond.
- **Bundle:** ~45 KB gz, but pulls d3 subpackages. Fine for server, borderline for client.
- **License:** ISC.

### 3. Vega-Lite — the runner-up we are not picking

- **Why not:** It is the correct academic answer (declarative, composable, battle-tested at Jupyter/Altair scale) and the wrong pragmatic one. Bundle size is ~500 KB combined with Vega runtime. Init latency on a widget-per-page basis is visible. The spec → view compile step adds a frame of jank on every update. Its SVG output is fine but less typographically controllable than Plot's.
- **Use case where we'd flip:** If Scriba ever exposes plot authoring to end users as JSON (not a DSL), Vega-Lite becomes compelling because the JSON is portable to Python/R ecosystems.

---

## Scriba `plot` shape — authoring DSL

Scriba widgets emit step deltas during algorithm simulation. We introduce a new shape, `plot`, declared in the widget header and fed by `tick` instructions inside the step block.

```scriba
widget sliding_window {
  shape plot cumulative_moves {
    title: "Cumulative pointer moves"
    x_label: "step"
    y_label: "moves"
    series: [
      { id: "moves", label: "moves", color: accent }
    ]
    y_scale: linear
    height: 80
    mode: line
  }
}

# Emitted from the step loop — one per step delta
tick plot.cumulative_moves series=moves x=$step y=$total_moves
```

Multi-series + log scale + annotation:

```scriba
shape plot annealing {
  series: [
    { id: "temp",   label: "T",      color: muted,  axis: left  }
    { id: "energy", label: "E",      color: accent, axis: right, scale: log }
  ]
  height: 100
}

tick plot.annealing series=temp   x=$iter y=$T
tick plot.annealing series=energy x=$iter y=$E
mark plot.annealing x=$iter label="reheat" when=$reheated
```

Sparkline in a DPTable cell:

```scriba
cell dp[i][j] {
  value: $dp_ij
  spark: { data: $history_ij, height: 14, stroke: accent }
}
```

Bar chart / histogram:

```scriba
shape plot uf_size_dist {
  mode: bar
  x: category
  y: count
  height: 90
}

tick plot.uf_size_dist data=$size_buckets  # replaces entire dataset
```

The compiler translates `tick plot.X` into a JSON frame appended to the widget's step stream. The runtime `<scriba-plot>` web component subscribes to step events, buffers the series, and calls either `uplot.setData()` or re-renders Observable Plot output depending on build mode.

---

## Tufte design constraints

Non-negotiable defaults baked into both SSR and runtime paths:

- **Line weight:** 1.25 px for primary, 0.75 px for secondary, 0.5 px for axes and rules. No 2 px "default chart" lines.
- **Palette:** Inherit from Scriba CSS custom properties — `--scriba-plot-ink`, `--scriba-plot-accent`, `--scriba-plot-muted`, `--scriba-plot-grid`. Two-color default (ink + accent). Never more than three series colors without explicit authoring.
- **Typography:** Inherit widget body font (already serif in Scriba) — `font-size: 0.75em`, `font-feature-settings: "tnum"` for tabular numerals on axis ticks. Labels set in small caps variant where the font supports it.
- **Axis treatment:** No box frame. Bottom axis only (a single 0.5 px rule). Y axis implied by the leftmost tick label; no vertical spine. No minor ticks. 3–4 tick labels max per axis.
- **Gridlines:** None by default. Opt-in only for log-scale plots, drawn at 0.25 px in `--scriba-plot-grid`.
- **Annotations:** Inline text label near the annotated point, no callout lines, no boxes. A single vertical tick marks the x position.
- **Sparklines:** Height 14–20 px, no axes at all, single series, optional endpoint dot in accent.
- **Dark mode:** All colors defined as OKLCH variables at widget root; both themes compile to the same SVG structure with different `:root` overrides. Scriba already dual-themes via the `data-theme` attribute (`699cafc`), we plug straight into that.
- **Print / PDF:** SSR path emits pure SVG with inlined CSS custom property fallbacks so that print stylesheets and PDF rendering do not depend on JS.

---

## Bundle size budget

Widget runtime already ships roughly 30 KB gz of Scriba core. Plot primitive budget:

| Component                              | Budget (gz) |
|----------------------------------------|-------------|
| uPlot core                             | 15 KB       |
| Annotation/hook glue                   | 1 KB        |
| Scriba `<scriba-plot>` web component   | 2 KB        |
| Spark subrenderer (custom, no dep)     | 1 KB        |
| **Runtime total**                      | **19 KB**   |
| Observable Plot (SSR only, not shipped)| 0 KB client |

This fits under the 20 KB ideal. If we ever need to shed weight, the sparkline path is already custom — we can drop to uPlot-only for all charts and still stay comfortably under budget.

The SSR path runs in Node during `scriba compile` and ships zero bytes to the client beyond the resulting inline `<svg>`. Runtime upgrades the SVG to a live uPlot canvas on hydration when the widget is interactive; static exports leave the SVG untouched.

---

## Implementation tasks

1. **DSL** — add `plot` shape and `tick plot.X` / `mark plot.X` instructions to the Scriba grammar; update the AST and type checker.
2. **Compile-time SSR** — add `scriba-plot-ssr` package, wraps Observable Plot + jsdom, returns SVG string per widget; hook into the existing HTML cache invalidation path (`0c36be0`).
3. **Runtime web component** — `<scriba-plot>` custom element; lazy-imports uPlot on first upgrade; subscribes to the widget's step event bus; buffers series; calls `setData` per tick.
4. **Annotation hook** — implement `mark` support via uPlot `hooks.draw` overlay (vertical 0.5 px rule + text label, inheriting widget typography).
5. **Sparkline subrenderer** — hand-rolled SVG path builder, ~80 LOC, no dependency. Drives DPTable `spark:` field.
6. **Bar/histogram mode** — add `mode: bar` handling to both SSR (Plot `Plot.barY`) and runtime (uPlot bars series plugin).
7. **Theming** — define the `--scriba-plot-*` CSS custom property contract in `scriba.css`; validate both light and dark via visual regression.
8. **Print stylesheet** — ensure SVG survives `@media print` without JS; add a PDF golden snapshot test per representative widget (sliding window, splay, Mo's, annealing).
9. **Visual regression** — Playwright screenshots at 320 / 768 / 1440 per widget in both themes, per the project web testing rules.
10. **Authoring docs** — extend the Scriba author guide with the `plot` shape DSL and the Tufte constraint set, including worked examples for all four amortization widgets called out in the HARD-TO-DISPLAY analysis.

---

## Citations

- uPlot — https://github.com/leeoniya/uPlot (MIT, benchmarks and hooks API)
- Observable Plot — https://observablehq.com/plot (ISC, `Plot.plot`, `Plot.lineY`, `Plot.ruleX`, headless/jsdom usage)
- Vega-Lite — https://vega.github.io/vega-lite/ (BSD-3, spec model, bundle weight)
- Chart.js — https://www.chartjs.org/docs/latest/ (MIT, dataset config)
- ECharts — https://echarts.apache.org/ (Apache-2, markLine, bundle)
- D3 — https://d3js.org/ (ISC)
- Frappe Charts — https://frappe.io/charts (MIT)
- Tufte, _The Visual Display of Quantitative Information_ — design constraints distilled above are the standard small-multiples / sparkline / ink-minimization rules.
