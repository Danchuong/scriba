> **Active pivot in progress (2026-04-09): Pivot #2 — Zero-JS maxed out for HARD-TO-DISPLAY coverage.**
>
> See [`architecture-decision.md`](planning/architecture-decision.md) for the decision. New feature specs are being written under `extensions/` and `primitives/`. Current locked spec in `spec/environments.md` remains the base and will be EXTENDED, not replaced.

---

# Scriba

> **Scriba is not a DSL.** It is a Python rendering pipeline that turns LaTeX
> problem statements into safe, self-contained HTML — plus two new LaTeX
> environments, `\begin{animation}` and `\begin{diagram}`, that let authors
> embed algorithmic visualizations without leaving `.tex` and without
> shipping a single byte of runtime JavaScript.

## What Scriba actually is

Scriba lives in `packages/scriba/` as a Python package. At its core it is a
small, deterministic pipeline:

```
source (.tex-flavored string)
        │
        ▼
┌──────────────────┐
│     Pipeline     │  ← scriba.Pipeline
├──────────────────┤
│  Renderers:      │
│    animation     │  ← AnimationRenderer  (new in v0.3)
│    diagram       │  ← DiagramRenderer    (new in v0.3)
│    tex           │  ← TexRenderer        (existing)
└──────────────────┘
        │
        ▼
      Document  (html, required_css, required_js, versions, block_data)
```

Each `Renderer` is a plugin. It implements `detect(source)` to carve out the
regions it owns and `render_block(block, ctx)` to turn those regions into
sanitized HTML. The Pipeline resolves overlaps with a first-wins rule
(`start`, then `priority`, then list order), substitutes placeholders, and
aggregates the CSS/JS assets each plugin needs.

`TexRenderer` is what you already have. It calls a KaTeX worker, sanitizes,
and emits `<span class="scriba-tex">…</span>`. **Scriba v0.3 adds two more
renderers that sit in front of it**, and nothing else. No CLI, no custom
element, no runtime step controller, no mini-language with its own parser.

- `AnimationRenderer` claims every `\begin{animation} … \end{animation}`
  region and expands it to an `<ol class="scriba-filmstrip">` of
  pre-rendered SVG frames plus narration paragraphs.
- `DiagramRenderer` claims every `\begin{diagram} … \end{diagram}` region
  and emits a single static `<figure>` with one SVG inside.

Authors write ordinary LaTeX. They use these environments the way they
already use `tikzpicture`. The output is zero-JS static HTML that works in
email clients, print, PDF export, RSS readers, and every browser we care
about.

## Who this is for

- **OJ maintainers** at ojcloud who run the Scriba pipeline inside
  `tenant-backend` and cache the rendered HTML per content hash. You need
  a deterministic, sandboxed, pure-Python renderer you can call from a
  request handler or a background job and trust with untrusted author
  input.
- **CP editorial authors** who write problem statements in LaTeX and want
  DP tables, trees, graphs, grids, and number lines to animate *inside the
  problem statement itself* — not in a separate video, not in a separate
  tool, not behind a JS widget that breaks in the learner's email client.

If you write problems like *Frog 1*, *Knapsack*, *Binary Search on the
Answer*, *BFS on a grid*, or *segment tree queries* and you have been
reaching for screenshots, GIFs, or hand-drawn SVGs — you are the audience.

## The 60-second pitch

1. You already write LaTeX. Keep writing LaTeX.
2. When a step-by-step picture would help, open a `\begin{animation}`
   block, declare a primitive (`\shape{dp}{Array}{size=7}`), then write
   one `\step` per frame with one `\narrate{…}` sentence and one or two
   `\apply` / `\highlight` / `\recolor` calls.
3. Run the source through `Pipeline.render(source, ctx)`.
4. You get back a `Document` with HTML, a frozen set of required CSS
   files, and a content-hashable version map. Drop the HTML into your
   page. Ship the CSS once, globally. There is no JavaScript step.
5. The same source produces byte-identical HTML every time. The tenant
   backend's content-hash cache just works.

No new tool. No new runtime. No new authoring surface. Two new
environments inside the same LaTeX file the author was already writing.

## Minimal hello

A full, rendering-capable problem fragment with a five-line animation:

```tex
The frog starts at stone $1$ and wants to reach stone $n$. Define
$dp[i]$ as the minimum cost to reach stone $i$.

\begin{animation}[id=frog-mini, label="Frog DP base cases"]
  \shape{dp}{Array}{size=4, labels="0..3"}
  \step \apply{dp.cell[0]}{value=0} \narrate{Base case: $dp[0] = 0$.}
  \step \apply{dp.cell[1]}{value=2} \highlight{dp.cell[1]} \narrate{From stone 0 we jump to 1 at cost $|h_0 - h_1| = 2$.}
  \step \apply{dp.cell[2]}{value=3} \highlight{dp.cell[2]} \narrate{$dp[2] = \min(dp[0]+3,\; dp[1]+1) = 3$.}
\end{animation}
```

And the Python that turns it into HTML:

```python
from pathlib import Path

from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer
from scriba.animation import AnimationRenderer, DiagramRenderer  # v0.3

def noop_resolver(_filename: str) -> str | None:
    return None

pool = SubprocessWorkerPool(max_workers=2)

pipeline = Pipeline(renderers=[
    AnimationRenderer(worker_pool=pool),  # priority before tex
    DiagramRenderer(worker_pool=pool),
    TexRenderer(worker_pool=pool),
])

source = Path("frog.tex").read_text(encoding="utf-8")
ctx = RenderContext(resource_resolver=noop_resolver, theme="light")

with pipeline:
    doc = pipeline.render(source, ctx)

Path("frog.html").write_text(doc.html, encoding="utf-8")
print("CSS to include:", sorted(doc.required_css))
print("JS to include :", sorted(doc.required_js))   # → [] for animation/diagram
print("Versions      :", doc.versions)
```

That is the entire surface area. `Pipeline`, `RenderContext`,
`SubprocessWorkerPool`, three renderers, one call to `render`. Everything
else in this folder is spec, cookbook, and taste.

## Table of contents

### `spec/` — Locked specs (source of truth)

| File | Purpose |
|---|---|
| [`architecture.md`](spec/architecture.md) | The Pipeline, Renderer, RenderContext, and Document contracts. Read this first if you are implementing a renderer or integrating Scriba into a service. |
| [`environments.md`](spec/environments.md) | **Locked** spec for the `animation` and `diagram` environments: grammar, the 8 inner commands, the 6 primitives, the 6 semantic states, the Starlark host, the HTML/CSS contract, and the error catalog. Single source of truth for implementation. |
| [`scene-ir.md`](spec/scene-ir.md) | Scene IR datatype definitions. |
| [`primitives.md`](spec/primitives.md) | Primitive catalog (Array, DPTable, Graph, Grid, Tree, NumberLine). |
| [`svg-emitter.md`](spec/svg-emitter.md) | SVG emitter specification. |
| [`animation-css.md`](spec/animation-css.md) | CSS stylesheet specification. |
| [`starlark-worker.md`](spec/starlark-worker.md) | Starlark worker wire protocol. |
| [`ruleset.md`](spec/ruleset.md) | Comprehensive ruleset derived from specs. |

### `guides/` — How-to and plugin docs

| File | Purpose |
|---|---|
| [`tex-plugin.md`](guides/tex-plugin.md) | TeX renderer internals: HTML output contract, snapshot spec, KaTeX worker. |
| [`diagram-plugin.md`](guides/diagram-plugin.md) | How `DiagramRenderer` fits into the pipeline and shares primitives with `AnimationRenderer`. |
| [`animation-plugin.md`](guides/animation-plugin.md) | How `AnimationRenderer` parses, runs Starlark, drives the scene IR, and emits the filmstrip HTML. |
| [`usage-example.md`](guides/usage-example.md) | A full end-to-end worked example: a real `.tex` problem with one `animation` and one `diagram`, the exact Python to run it, and the resulting HTML shape. |
| [`editorial-principles.md`](guides/editorial-principles.md) | Authoring principles. When to reach for `animation` vs `diagram`, how to budget frames, how to write narration that earns its place, and how to stay accessible by construction. |

### `planning/` — Roadmap, phases, decisions

| File | Purpose |
|---|---|
| [`roadmap.md`](planning/roadmap.md) | Release milestones and what each one ships. |
| [`implementation-phases.md`](planning/implementation-phases.md) | Ordered phases from parser to primitives to Starlark worker to SVG emitter to CSS. |
| [`architecture-decision.md`](planning/architecture-decision.md) | Pivot #2 rationale, coverage matrix, rejected alternatives. |
| [`phase-a.md`](planning/phase-a.md) | Phase A plan (core pipeline, parser, Array/DPTable/Graph). |
| [`phase-b.md`](planning/phase-b.md) | Phase B plan (Grid, Tree, NumberLine, Matrix, Stack). |
| [`phase-c.md`](planning/phase-c.md) | Phase C plan (Plane2D, MetricPlot, graph-stable-layout, substory). |
| [`phase-d.md`](planning/phase-d.md) | Phase D plan (polish, docs site, OSS launch). |
| [`open-questions.md`](planning/open-questions.md) | Known unresolved tradeoffs. File issues against this file, not the spec. |
| [`out-of-scope.md`](planning/out-of-scope.md) | Things that look like they belong in Scriba but explicitly do not. Read before proposing features. |

### `operations/` — Packaging and migration

| File | Purpose |
|---|---|
| [`packaging.md`](operations/packaging.md) | Wheel layout, build system, dependencies, vendored assets, versioning scheme. |
| [`migration.md`](operations/migration.md) | Migrating from the old renderer to Scriba. |

### `archive/` — One-off audit and verify reports

| File | Purpose |
|---|---|
| [`audit-2026-04-09.md`](archive/audit-2026-04-09.md) | Audit of the locked base spec (2026-04-09). |
| [`verify-2026-04-09.md`](archive/verify-2026-04-09.md) | Verification report (2026-04-09). |
| [`v020-verify.md`](archive/v020-verify.md) | v0.2.0 verification report. |

### Other directories (unchanged)

| Directory | Purpose |
|---|---|
| [`cookbook/`](cookbook/) | Worked problems. Frog DP, 0/1 Knapsack, BFS on a grid, segment tree query, binary search on the answer. Copy-paste starters. |
| [`extensions/`](extensions/) | Extension specs (figure-embed, hl-macro, fastforward, substory, keyframe-animation). |
| [`primitives/`](primitives/) | Draft primitive extension specs (matrix, stack, plane2d, metricplot, graph-stable-layout). |
| [`blog/`](blog/) | Launch blog posts and community thread templates. |
| [`oss/`](oss/) | Notes on the open-source pipeline: what ships publicly, what stays in-tree. |
| [`legacy/`](legacy/) | Earlier drafts preserved for context. Do not cite from implementation code. |

## Design commitments, in one breath

Zero runtime JavaScript. LaTeX-native authoring. Build-time determinism
inside a subprocess worker pool. Accessible by construction (real text,
real `<ol>`, real `<figure>`). Print-friendly (filmstrip collapses to
stack under `@media print`). No mutation of author input. No I/O,
randomness, or time inside `\compute`. Byte-identical output for
byte-identical input, so the content-hash cache in `tenant-backend` keeps
working.

Everything else is a detail. Start with
[`environments.md`](spec/environments.md).
