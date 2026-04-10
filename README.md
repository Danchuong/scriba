# Scriba

**Status:** v0.5.0 · MIT · Python 3.10+

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
- **Coming in v0.2.0:** a `\begin{animation}` environment for step-through
  editorial walkthroughs, followed by a `\begin{diagram}` environment for
  inline graph/tree figures. See
  [`docs/scriba/04-environments-spec.md`](https://github.com/ojcloud/scriba/tree/main/docs)
  <!-- TODO: update once public mirror exists -->.

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
