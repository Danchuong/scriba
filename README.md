# Scriba

**Status:** v0.6.0 · MIT · Python 3.10+

Scriba is a backend Python library that renders LaTeX problem statements and
competitive-programming editorials to self-contained HTML fragments. It is
LaTeX-first: drop a `.tex` source in, get out HTML plus the exact CSS/JS
asset basenames needed to display it.

## What is Scriba?

- **LaTeX-first rendering** for CP problem statements and editorials, with
  KaTeX math, Pygments code highlighting, lists, tables, sections, figures,
  `\href` / `\url` with XSS hardening, and `\begin{lstlisting}` code blocks.
- **Self-contained output contract:** every render produces an HTML fragment
  plus a namespaced set of required CSS and JS basenames and a block-data
  map — consumers decide how to serve the static assets.
- **`\begin{animation}` environment** (shipping since 0.2.0) for step-through
  editorial walkthroughs with 16 built-in primitives (arrays, grids, graphs,
  trees, DP tables, number lines, matrices/heatmaps, stacks, plane-2D,
  metric plots, and the 5 data-structure primitives: code panel, hash map,
  linked list, queue, variable watch). `\begin{diagram}` for inline
  static graph/tree figures is reserved under extension E5. See
  [`docs/spec/ruleset.md`](docs/spec/ruleset.md) for the full grammar and
  error catalog.

## What's new in v0.6.0

- **Wave 8 — vstack layout.** Array, DP-table, and related primitives now
  compose their caption, index labels, and cells through a shared
  `scriba/animation/primitives/layout.py` vstack helper. No more hardcoded
  Y offsets: cell, index, and caption font sizes drive the layout through
  real font metrics.
- **Wave 9 — CSS-first text halo cascade.** Every `[data-primitive] text`
  element now inherits `paint-order: stroke fill markers` with a
  `--scriba-halo` CSS variable that each state class overrides. The block is
  wrapped in `@media (forced-colors: none)` so Windows High Contrast Mode
  strips it cleanly. The per-call `text_outline=` parameter on primitives is
  deprecated and scheduled for removal in v0.7.0 — authors should rely on
  the CSS cascade instead.
- **RFC-001 — structural mutation ops.** Tree, Graph, and Plane2D primitives
  gained safe structural ops (`add_node`, `remove_node`, `reparent`, and
  friends) plus a new `hidden` state for elements that are modeled but not
  yet rendered. See `docs/guides/hidden-state-pattern.md` for the intended
  authoring flow.
- **RFC-002 — strict mode and document warnings.** The pipeline now
  surfaces non-fatal issues on `Document.warnings` as a tuple of typed
  `CollectedWarning` entries (code, message, source line/col, primitive,
  severity). Setting `RenderContext(strict=True)` promotes a designated
  set of dangerous codes (`E1461`, `E1462`, `E1463`, `E1484`, `E1501`,
  `E1502`, `E1503`) into hard render errors; `strict_except` opts specific
  codes back out. Strict mode is a `RenderContext` field, not a core CLI
  flag — CLIs wrap it themselves. See
  [`docs/guides/strict-mode.md`](docs/guides/strict-mode.md).
- **Cookbook refresh.** Eleven new or rewritten editorial examples land
  under `examples/cookbook/`: the h07 and h08 rewrites, canonical h11–h18
  algorithm walkthroughs, and h19 (DP convex hull trick). See
  [`docs/cookbook/README.md`](docs/cookbook/README.md) for the full
  index.

## Install

```bash
pip install scriba
```

Scriba shells out to a small Node.js worker for KaTeX math, so the host
environment needs Node.js 18+ on PATH:

```bash
# System prerequisite — Node.js only
apt-get install nodejs   # or: brew install node
```

KaTeX `0.16.11` is vendored inside the wheel (at
`scriba/tex/vendor/katex/katex.min.js`), so **no separate
`npm install -g katex` step is required**. `pip install scriba` is all
you need once Node is present.

## Hello world

```python
from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer

pool = SubprocessWorkerPool()
pipeline = Pipeline([TexRenderer(worker_pool=pool, pygments_theme="one-light")])

ctx = RenderContext(
    resource_resolver=lambda name: f"/cdn/problems/1/{name}",
    theme="light", dark_mode=False, metadata={}, render_inline_tex=None,
)

doc = pipeline.render(r"\section{Hello} Let $x^2$ be the square.", ctx)
print(doc.html)          # HTML fragment
print(doc.required_css)  # namespaced CSS keys
pipeline.close()
```

## Sanitize before embedding

Scriba does **not** sanitize its output — consumers must pass it through a
vetted sanitizer before embedding in a page. Scriba ships an allowlist that
matches its output contract:

```python
import bleach
from bleach.css_sanitizer import CSSSanitizer
from scriba import ALLOWED_TAGS, ALLOWED_ATTRS

css = CSSSanitizer(allowed_css_properties=("transform","transform-origin","width","height"))
safe = bleach.clean(doc.html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
                    css_sanitizer=css, strip=True)
```

## Serving static assets

Assets ship inside the Python package. Copy them at deploy time:

```python
from importlib.resources import files
import shutil
shutil.copytree(str(files("scriba.tex.static")), "./public/scriba", dirs_exist_ok=True)
```

Then include them alongside the rendered fragment:

```html
<link rel="stylesheet" href="/cdn/katex/katex.min.css">
<link rel="stylesheet" href="/public/scriba/scriba-tex-content.css">
<link rel="stylesheet" href="/public/scriba/scriba-tex-pygments-light.css">
<script defer src="/public/scriba/scriba-tex-copy.js"></script>

<article class="scriba-tex-content">{{ doc.html }}</article>
```

## Documentation

Full architecture, contracts, and roadmap live under the project docs tree:
<https://github.com/ojcloud/scriba/tree/main/docs>
<!-- TODO: update once public mirror exists -->

## License

MIT. See [`LICENSE`](LICENSE).
