# Scriba

**Status:** v0.9.0 · MIT · Python 3.10+

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

## What's new in v0.9.0

- **Breaking: `data-primitive` casing normalized.** `HashMap` and
  `VariableWatch` attributes are now lowercase (`"hashmap"`,
  `"variablewatch"`) to match all other primitives. Update any CSS or
  JS selectors that target the old casing.
- **Breaking: `eval_raw` removed.** The deprecated
  `StarlarkHost.eval_raw` method has been deleted. Use `\compute{...}`
  blocks instead; wire-level requests with `op="eval_raw"` now return
  error `E1156` with a migration hint.
- **External JS runtime (from v0.8.3) is now the default.** Inline
  mode is no longer the default. Use `--inline-runtime` to restore it.
  The `--asset-base-url` and `--copy-runtime` flags select CDN or
  external-copy deployment for `script-src 'self'` CSP compliance.
- **Structural refactors (waves A–D).** `grammar.py` split into mixin
  files, `base.py` reduced from 1436 to ~333 lines, warning emission
  centralised in `scriba.core.warnings`, and named constants replace
  inline magic values. No API changes for library consumers. See
  `CHANGELOG.md` for the full list.

<details>
<summary>v0.8.2 changelog</summary>

- **Position-aware auto-ID generation.** Duplicate animation/diagram
  blocks with identical content now produce distinct HTML element IDs.
- **Duplicate block ID warning.** The pipeline emits
  `CollectedWarning(code="E1019", severity="dangerous")` when two
  blocks share the same `block_id`.

</details>

<details>
<summary>v0.8.0 changelog</summary>

- **Fixed state styling regression.** Cell/node/edge state colors
  (`current`, `error`, `good`, `highlight`, etc.) were silently overridden
  by primitive base selectors due to a CSS specificity conflict. Primitive
  base selectors now use `:where()` to zero their qualifying specificity,
  so `.scriba-state-*` rules always win.

</details>

<details>
<summary>v0.7.0 changelog</summary>

- **Fully portable HTML output.** `render.py` now produces single-file,
  offline-ready HTML. All CSS (scene primitives, animation, widget chrome,
  Pygments syntax highlighting), KaTeX math fonts (20 woff2 files,
  base64-encoded), and `\includegraphics` images (data URIs) are inlined.
  Zero CDN dependencies — just open the `.html` in any browser.
- **CSS deduplication.** The ~470-line inline CSS block in `render.py` was
  replaced by a new `scriba.core.css_bundler` module that reads CSS from
  source `.css` files at render time. Single source of truth for all
  styling.
- **`traversable_to_path()` helper.** Centralised the
  `Path(str(traversable))` anti-pattern across 3 files into a documented
  helper in `scriba.core.artifact`, ready for future `as_file()` upgrade.
- **`text_outline=` parameter removed.** The per-call text outline parameter
  on primitives, deprecated in v0.6.0, is removed. Use the CSS halo
  cascade instead.

</details>

<details>
<summary>v0.6.0 changelog</summary>

- **Wave 8 — vstack layout.** Array, DP-table, and related primitives now
  compose their caption, index labels, and cells through a shared
  `scriba/animation/primitives/layout.py` vstack helper.
- **Wave 9 — CSS-first text halo cascade.** Every `[data-primitive] text`
  element now inherits `paint-order: stroke fill markers` with a
  `--scriba-halo` CSS variable that each state class overrides.
- **RFC-001 — structural mutation ops.** Tree, Graph, and Plane2D primitives
  gained safe structural ops (`add_node`, `remove_node`, `reparent`).
- **RFC-002 — strict mode and document warnings.** Pipeline surfaces
  non-fatal issues on `Document.warnings`. See
  [`docs/guides/strict-mode.md`](docs/guides/strict-mode.md).
- **Examples reorganized.** 53 `.tex` examples across `examples/quickstart/`,
  `examples/algorithms/`, `examples/cses/`, and `examples/primitives/`.
  See [`docs/cookbook/README.md`](docs/cookbook/README.md).

</details>

## Install

```bash
pip install scriba-tex
```

Scriba shells out to a small Node.js worker for KaTeX math, so the host
environment needs Node.js 18+ on PATH:

```bash
# System prerequisite — Node.js only
apt-get install nodejs   # or: brew install node
```

KaTeX `0.16.11` is vendored inside the wheel (at
`scriba/tex/vendor/katex/katex.min.js`), so **no separate
`npm install -g katex` step is required**. `pip install scriba-tex` is all
you need once Node is present.

## Using Scriba with an AI assistant

To have an AI write `.tex` for Scriba, give it one file:
**[`docs/SCRIBA-TEX-REFERENCE.md`](docs/SCRIBA-TEX-REFERENCE.md)**.

It's self-contained — all commands, all 15 primitives, all selectors,
all gotchas. No other spec files needed.

Prompt template:
> Read `SCRIBA-TEX-REFERENCE.md`. Write a Scriba `.tex` file that
> animates [algorithm]. Use only commands and primitives documented
> in that file.

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

## Standalone CLI

For quick rendering without writing Python, use `render.py` directly:

```bash
python render.py input.tex                # → input.html
python render.py input.tex -o out.html    # → custom output path
python render.py input.tex --open         # → render and open in browser
```

Output is a **single, fully portable HTML file** — all CSS, KaTeX math
fonts, syntax highlighting, and images (via `\includegraphics`) are
inlined as data URIs. No internet connection or external files needed.
Just open the `.html` file in any browser.

For legacy filmstrip mode (static frames, no JavaScript):

```bash
python render.py input.tex --static
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

> **Note:** This section applies to the **Pipeline API** (library usage),
> where you serve assets yourself. If you use `render.py` instead, the
> output HTML is fully self-contained — all CSS, KaTeX fonts (base64), and
> Pygments highlighting are inlined. No separate asset serving needed.

## Documentation

Full architecture, contracts, and roadmap live under the project docs tree:
<https://github.com/Danchuong/scriba/tree/main/docs>

## License

MIT. See [`LICENSE`](LICENSE).
