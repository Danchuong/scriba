# O1 — API Surface

> Source of truth: [`../04-environments-spec.md`](../spec/environments.md). This file ranks and freezes the **public** surface that Scriba v0.3 ships. Anything not listed here is internal and may change between patch releases.

## 1. What is "the API"?

After the pivot, Scriba is no longer a standalone DSL. It is a Python package that extends `scriba.Pipeline` with two new LaTeX environments. The public API therefore has three layers:

1. **Author surface** — what a problem-setter writes inside a `.tex` file.
2. **Python surface** — what an OJ backend or static site generator imports from `scriba`.
3. **HTML surface** — the DOM/CSS contract that consumers style against.

There is **no standalone CLI** (`scriba init/build/dev/check` are all cut). There is **no runtime JS** (`scriba-runtime/` is deleted). There is **no new file format** — authors keep writing `.tex`.

---

## 2. Author surface

### 2.1 Two environments

```latex
\begin{animation}[id=binsearch, width=60ex]
  ...
\end{animation}

\begin{diagram}[id=tree-example]
  ...
\end{diagram}
```

Both accept an optional `[key=value,...]` block. Keys are defined in `../04-environments-spec.md` §2.4: `width`, `height`, `id`, `label`.

- `animation` — ordered filmstrip of N frames, each a pre-rendered static SVG + narration paragraph.
- `diagram` — a single static figure. Same primitive vocabulary as `animation` minus `\step` and `\narrate`.

### 2.2 Eight inner commands

| Command | Arity | Legal in | Purpose |
|---|---|---|---|
| `\shape{name}{primitive}{params}` | 3 | anim prelude, diagram | Declare a primitive instance (array, grid, graph, tree, dptable, code) |
| `\compute{starlark}` | 1 | anim prelude, diagram | Run sandboxed Starlark at build time to produce named values |
| `\step` | 0 | animation only | Start a new frame |
| `\narrate{tex}` | 1 | inside `\step` | Attach narration paragraph; inner content is rendered via `TexRenderer` |
| `\apply{name}{params}` | 2 | anim prelude, `\step`, diagram | Mutate a shape's contents (set cell, add edge, etc.) |
| `\highlight{selector}` | 1 | anim prelude, `\step`, diagram | Apply a semantic state class to shape members |
| `\recolor{selector}{params}` | 2 | anim prelude, `\step`, diagram | Override the palette token for members |
| `\annotate{selector}{params}` | 2 | anim prelude, `\step`, diagram | Attach a short label/arrow/caption |

Precedence, selector grammar, parameter types, and validation rules live in `../04-environments-spec.md` §§3–6.

### 2.3 Six primitives (for `\shape`)

`array`, `grid`, `graph`, `tree`, `dptable`, `code`. Each primitive has a fixed parameter schema and selector vocabulary. Full catalog in `../04-environments-spec.md` §4.

### 2.4 Six semantic states (for `\highlight`)

`default`, `active`, `visited`, `candidate`, `rejected`, `accepted`. These map to CSS classes and are the only way to express "what is this element doing right now" without hardcoding colors. Full table in `../04-environments-spec.md` §6.

### 2.5 Starlark host rules (`\compute{}`)

- Sandboxed subprocess, no I/O, no time, no randomness
- Allowed builtins: `range`, `len`, `min`, `max`, `enumerate`, `zip`
- Hard CPU and memory caps
- Same input + same `scriba` version ⇒ byte-identical output
- Full contract in `../04-environments-spec.md` §5

---

## 3. Python surface

### 3.1 Imports

```python
from scriba import Pipeline, RenderContext
from scriba.tex import TexRenderer
from scriba.animation import AnimationRenderer, DiagramRenderer
```

### 3.2 Pipeline registration

```python
pipeline = Pipeline(renderers=[
    AnimationRenderer(worker_pool=pool),
    DiagramRenderer(worker_pool=pool),
    TexRenderer(worker_pool=pool),
])

html = pipeline.render(tex_source)
```

`AnimationRenderer` and `DiagramRenderer` MUST precede `TexRenderer` so the Pipeline's first-wins overlap rule carves out environment regions before the TeX plugin sees them.

### 3.3 Public names (v0.3 freeze)

| Category | Names |
|---|---|
| Core | `Pipeline`, `RenderContext`, `RenderResult`, `Renderer` (Protocol) |
| Renderers | `TexRenderer`, `AnimationRenderer`, `DiagramRenderer` |
| Worker pool | `SubprocessWorkerPool`, `WorkerPool` (Protocol) |
| Errors | `ScribaError`, `ParseError`, `StarlarkError`, plus error-code constants `E1001`…`E1299` |
| IR (read-only) | `Scene`, `Frame`, `PrimitiveInstance`, `Delta`, `Narration`, `Provenance` |

Everything under `scriba._internal` is private and may change.

### 3.4 Optional Typer helper (debugging only)

```bash
python -m scriba compile problem.tex --out problem.html
python -m scriba lint problem.tex
```

This exists purely so contributors can debug a single `.tex` file without booting a full OJ backend. It is **not** the primary surface, is **not** named `scriba init/build/dev/check`, and will never gain a dev-server or scaffold command.

---

## 4. HTML surface

Every `\begin{animation}` expands to:

```html
<figure class="scriba-figure scriba-animation" data-scriba-scene="..." aria-label="...">
  <ol class="scriba-filmstrip">
    <li class="scriba-frame" data-frame-index="0">
      <div class="scriba-stage"><svg ...>...</svg></div>
      <p class="scriba-narration">...</p>
    </li>
    ...
  </ol>
</figure>
```

Every `\begin{diagram}` expands to the same outer `<figure>` with a single `<div class="scriba-stage"><svg>…</svg></div>` and no `<ol>` / `<p>`.

No `<script>`. No custom elements. No hydration. The CSS class contract is frozen in `../04-environments-spec.md` §9 and is part of the public API — consumers may style against `.scriba-stage`, `.state-active`, etc.

---

## 5. What was cut from the pre-pivot plan

| Cut | Reason |
|---|---|
| `scriba init/build/dev/check` CLI | Scriba is a library, not a site generator |
| Lit 3 `<scriba-widget>` custom element | Output is pre-rendered static SVG — no runtime needed |
| `packages/scriba-runtime/` | Same |
| VS Code language extension | Authors already use LaTeX editors with existing tooling |
| `.scriba` file format | Authors keep writing `.tex` |
| `for_each` directive, `match` directive, push/pop/enqueue/dequeue ops | Folded into `\compute{}` + `\apply{}` |

## 6. Public API size

Around 25 exported Python names plus 2 environments, 8 commands, 6 primitives, 6 states. Well under the 40-name ceiling, and the author-facing vocabulary fits on a single reference card.
