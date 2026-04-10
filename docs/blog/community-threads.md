# Community Thread Templates -- Scriba v0.5.0 Launch

## Show HN

**Title:** Scriba -- Compile LaTeX editorials into animated HTML+SVG visualizations, zero JS

**Body:**

I write competitive programming editorials (explanations of algorithm solutions). The hard part isn't the algorithm -- it's explaining it. When I write about DP state transitions, graph augmentations, or convex hull tricks, the editorial degrades into "see the code" because static text can't carry the visualization.

Scriba is a Python library that compiles LaTeX `\begin{animation}` environments into self-contained HTML+SVG+CSS filmstrips. You declare shapes (Array, DPTable, Graph, Tree, Plane2D, etc.), steps, highlights, and narrations in LaTeX. Scriba compiles them to inline SVG frames at build time.

Two output modes:
- **Static**: pure HTML+SVG+CSS, zero JavaScript. Works in email, RSS, PDF, Codeforces blog posts, GitHub Markdown -- any platform that accepts HTML, including ones that strip `<script>`.
- **Interactive**: adds a ~2KB inline controller with keyboard nav and progress dots.

The compute layer uses Starlark (a deterministic Python subset) for data-driven animations. Same source + same version = byte-identical output. No RNG, no I/O, no network in the sandbox.

We stress-tested against 10 notoriously hard-to-visualize CP problems (interval DP, MCMF, Li Chao trees, splay amortized analysis, FFT butterflies, simulated annealing). Scriba covers 9/10; the remaining one (4D tensor DP) is a documented cognitive limit.

11 primitive types, 5 extensions (step-synced LaTeX highlighting, SVG escape hatch, nested drilldowns, sampled iteration loops, CSS keyframes). MIT licensed, Python 3.10+.

GitHub: https://github.com/ojcloud/scriba
Docs: https://scriba.ojcloud.dev

---

## Lobsters

**Title:** Scriba: compile-time LaTeX-to-animated-HTML for algorithm editorials

**Body:**

Scriba is a Python library for turning LaTeX competitive programming editorials into animated HTML visualizations. You write `\begin{animation}` environments with declared shapes (Array, Graph, DPTable, Tree, Plane2D, Stack, etc.), step through highlights and narrations, and Scriba compiles everything to self-contained HTML+SVG+CSS at build time.

The key design constraint: the static output mode uses zero JavaScript. Output is pure HTML+SVG+CSS that renders in Codeforces, email, RSS, PDF, and GitHub Markdown without modification. An optional interactive mode adds a ~2KB controller for web platforms.

Compute blocks use Starlark for deterministic, sandboxed data generation. The system was stress-tested against 10 hard-to-visualize algorithm problems (MCMF, FFT butterflies, splay amortized analysis, etc.) and covers 9/10. 11 primitives, MIT license.

GitHub: https://github.com/ojcloud/scriba

---

## Codeforces Blog

**Title:** Scriba: animated editorials in LaTeX, portable to CF blog posts

**Body:**

If you have ever tried to explain interval DP transitions, MCMF residual graph augmentations, or Li Chao tree lower envelopes in an editorial, you know the problem: the explanation falls apart where the visualization should be. You end up writing "see the code" or linking to a YouTube video.

Scriba is a Python library that lets you write `\begin{animation}` environments directly in your LaTeX editorial source. You declare shapes -- `Array`, `DPTable`, `Graph`, `Grid`, `Tree`, `Stack`, `Plane2D`, `Matrix`, `MetricPlot`, `NumberLine` -- and walk through steps with `\highlight`, `\recolor`, `\apply`, and `\narrate`. Scriba compiles everything at build time into a self-contained HTML fragment.

Here is what a simple DP editorial looks like:

```latex
\begin{animation}[id="knapsack", label="0/1 Knapsack DP"]
\shape{dp}{DPTable}{rows=4, cols=6, labels=("item","cap")}

\step
\recolor{dp.cell[1][3]}{state=current}
\narrate{Consider item 1 (w=2, v=3) at capacity 3. dp[1][3] = max(dp[0][3], dp[0][1]+3).}

\step
\recolor{dp.cell[1][3]}{state=done, value=3}
\narrate{dp[1][3] = 3. Take item 1.}
\end{animation}
```

**Why this matters for CF authors:**

- **Static mode**: the output is pure HTML+SVG+CSS with zero JavaScript. It passes CF's sanitizer. No external CDN, no `<script>`, no iframe hacks.
- **LaTeX-native**: you write the animation in the same `.tex` file as the rest of your editorial. No separate tool, no GUI.
- **`\compute{...}`**: Starlark blocks generate data deterministically, so you can compute DP tables, graph traversals, or coordinate geometry inline.
- **Portable**: same source renders to CF blog, AtCoder editorial, GitHub README, email, PDF.

We built Scriba specifically around 10 hard-to-display CP problems: Zuma interval DP, Miller-Rabin, FFT butterflies, MCMF, Li Chao / CHT, splay amortized analysis, Burnside counting, simulated annealing, and planar separators. v0.5.0 covers 9/10 (4D knapsack tensor remains a known limitation).

`pip install scriba`. MIT license. Python 3.10+ and Node 18+ (for KaTeX).

GitHub: https://github.com/ojcloud/scriba

---

## CP Discord

**Title:** scriba 0.5.0 -- animated editorials from LaTeX

**Body:**

Made a tool for writing animated CP editorials. You write `\begin{animation}` blocks in LaTeX with shapes like Array, DPTable, Graph, Tree, Plane2D, Stack. Each `\step` becomes a frame with highlights and narration. Scriba compiles it to HTML+SVG at build time.

Static mode has zero JS so it works on CF blog posts (passes the sanitizer). Also works in email, PDF, GitHub markdown. Interactive mode adds keyboard nav for web.

Stress-tested on 10 hard editorial problems (interval DP, MCMF, Li Chao, splay amortized, FFT butterfly, SA). Covers 9/10.

11 primitives. Starlark for inline compute. `pip install scriba`. MIT.

https://github.com/ojcloud/scriba
