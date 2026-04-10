# Scriba 0.5.0: Animated Algorithm Editorials That Work Everywhere

Competitive programming editorials have a visualization problem.

When you write about binary search, a sorted array and a few highlighted cells get the point across. But when you write about interval DP on palindromes, MCMF residual graph augmentations, Li Chao tree lower envelopes, or splay tree amortized potential functions, the editorial degrades into "see the code" and "trust the analysis." The algorithm is correct. The explanation fails because the medium cannot carry it.

We built Scriba to fix this. It is a Python library that compiles LaTeX editorials into animated HTML visualizations -- step-by-step, frame-by-frame, with the same primitives (arrays, DP tables, graphs, trees, coordinate planes) that editorial authors already think in.

## What it looks like

Here is a parenthesis-matching editorial using an Array and a Stack:

```latex
\begin{animation}[id="stack-parens", label="Parenthesis Matching"]
\shape{input}{Array}{size=8, data=["(","(",")",")","(","(",")",")"]}
\shape{s}{Stack}{items=[]}

\step
\recolor{input.cell[0]}{state=current}
\apply{s}{push="("}
\narrate{Char 1: ( is open. PUSH. Stack: [(.]}

\step
\recolor{input.cell[0]}{state=done}
\recolor{input.cell[1]}{state=current}
\apply{s}{push="("}
\narrate{Char 2: ( is open. PUSH. Stack: [(, (.]}

\step
\recolor{input.cell[1]}{state=done}
\recolor{input.cell[2]}{state=current}
\apply{s}{pop=1}
\narrate{Char 3: ) closes. POP top (. Match! Stack: [(.]}
\end{animation}
```

Scriba compiles this to a self-contained HTML fragment with inline SVG frames and CSS transitions. Each `\step` becomes one frame. Each `\narrate` becomes a caption. The reader clicks through (or uses arrow keys) and watches the algorithm unfold.

For a harder example, here is a Li Chao tree editorial using the `Plane2D` primitive:

```latex
\begin{animation}[id="li-chao", label="Li Chao Tree -- Lower Envelope"]
\shape{p}{Plane2D}{xrange=[0,8], yrange=[0,12], xlabel="x", ylabel="y"}

\step
\apply{p}{add_line=("L1", 1.5, 1)}
\recolor{p.line[0]}{state=current}
\narrate{Insert L1: y = 1.5x + 1. First line, trivially the lower envelope.}

\step
\recolor{p.line[0]}{state=done}
\apply{p}{add_line=("L2", -0.5, 10)}
\recolor{p.line[1]}{state=current}
\narrate{Insert L2: y = -0.5x + 10. Intersects L1 at x=4.5. Lower envelope updates.}
\end{animation}
```

No D3. No Manim render pipeline. No JavaScript. Just LaTeX environments that produce portable HTML.

## Two output modes

**Static mode** compiles to pure HTML + SVG + CSS. Zero JavaScript. The output works in Codeforces blog posts, AtCoder editorials, GitHub Markdown, email, RSS readers, and PDF. Any platform that accepts HTML can display it, including platforms with aggressive sanitizers that strip all `<script>` tags.

**Interactive mode** (the default for web platforms) adds a lightweight (~2KB) inline controller with keyboard navigation, progress dots, and frame transitions. Same content, better experience where JS is available.

The mode is selected at render time, not at authoring time. Write once, deploy to both.

## Architecture

Scriba is a compile-time system. The pipeline is:

1. **Parse** -- LaTeX `\begin{animation}` environments are extracted and parsed into an AST of shapes, steps, highlights, recolors, and narrations.
2. **Compute** -- `\compute{...}` blocks run deterministic Starlark code in a sandboxed subprocess worker. No RNG, no I/O, no network. Same source + same Scriba version = byte-identical output.
3. **Emit** -- The scene graph is materialized into SVG frames with CSS state classes and inline styles. Each frame is a `<li>` inside an `<ol>`, wrapped in a `<figure>`.

Everything happens at build time. The output is a frozen filmstrip, not a runtime application.

## 11 primitives

Scriba ships with 11 primitive types that cover the visualization vocabulary of competitive programming:

| Primitive | Use case |
|-----------|----------|
| Array | Sorted arrays, sequences, string characters |
| DPTable | 2D DP state tables with cell highlighting |
| Graph | Directed/undirected graphs with edge operations |
| Grid | 2D grids for BFS, flood fill, path problems |
| Tree | Rooted trees with Reingold-Tilford layout |
| NumberLine | Ranges, intervals, binary search bounds |
| Matrix / Heatmap | Dense matrices with colorscale overlays |
| Stack | Push/pop sequences for monotonic stacks, matching |
| Plane2D | 2D coordinate plane for geometry, CHT, Li Chao |
| MetricPlot | Live scalar tracking across frames (potential, cost) |

Plus 4 extensions: `\hl` (step-synced LaTeX highlighting), figure-embed (SVG/PNG escape hatch), `\substory` (nested drilldown), and CSS `@keyframes` slots.

## The 10 hard problems

We started Scriba with a specific stress test: 10 competitive programming problems whose editorials are notoriously difficult to visualize. Interval DP palindromes. FFT butterflies. MCMF residual graphs. Splay tree amortized analysis. Simulated annealing convergence. The full list is documented in [`HARD-TO-DISPLAY.md`](../cookbook/HARD-TO-DISPLAY.md).

After v0.5.0, Scriba covers 9 of the 10. The one remaining gap -- 4D Knapsack tensor visualization -- is a genuine cognitive limit documented as a known partial. We consider this an honest admission rather than a failure.

## Quick start

```bash
pip install scriba
```

Scriba requires Python 3.10+ and Node.js 18+ (for KaTeX math rendering). KaTeX is vendored inside the wheel.

```python
from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer
from scriba.animation import AnimationRenderer

pool = SubprocessWorkerPool()
pipeline = Pipeline([
    AnimationRenderer(worker_pool=pool),
    TexRenderer(worker_pool=pool),
])

ctx = RenderContext(
    resource_resolver=lambda name: f"/static/{name}",
    theme="light",
    dark_mode=False,
    metadata={"output_mode": "static"},  # or "interactive"
    render_inline_tex=None,
)

doc = pipeline.render(open("editorial.tex").read(), ctx)
# doc.html       -- the HTML fragment
# doc.required_css -- CSS basenames to include
```

The output is an HTML fragment. You are responsible for sanitizing it before embedding (Scriba ships an allowlist) and serving the static CSS assets.

## What's next

Scriba 0.5.0 is the first general-availability release. The 0.x API is not yet frozen -- breaking changes between minor versions are permitted, with version fields tracked in `Document.versions` so consumer caches stay correct.

On the horizon:
- **Optional Lit 3 interactive runtime** with a scrubber widget, if there is sustained demand from consumers who accept JS-only contexts.
- **Additional primitives** (Heap, SegTree, UnitCircle) driven by specific editorial requests.
- **1.0 API freeze** once two consecutive minor releases ship with no HTML shape changes and at least one external OJ is running Scriba in production.

Scriba is MIT-licensed. Source: [github.com/ojcloud/scriba](https://github.com/ojcloud/scriba).
