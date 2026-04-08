# Scriba

Backend-only Python package for rendering Online Judge problem statements (LaTeX + diagrams).

## Install

```bash
pip install scriba

# System prerequisites
apt-get install nodejs   # or brew install node
npm install -g katex@0.16.11
```

## Quick start

```python
from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer

pool = SubprocessWorkerPool()
renderer = TexRenderer(worker_pool=pool, pygments_theme="one-light")
pipeline = Pipeline([renderer])

ctx = RenderContext(
    resource_resolver=lambda name: f"/cdn/problems/1/{name}",
    theme="light",
    dark_mode=False,
    metadata={},
    render_inline_tex=None,
)

doc = pipeline.render(r"\section{Hello} Cho $x^2$ là bình phương.", ctx)
print(doc.html)           # HTML fragment
print(doc.required_css)   # {"scriba-tex-content.css", "scriba-tex-pygments-light.css"}
print(doc.required_js)    # {"scriba-tex-copy.js"}

pipeline.close()
```

## Sanitize before embedding

Scriba does NOT sanitize output. Consumers must sanitize:

```python
import bleach
from bleach.css_sanitizer import CSSSanitizer
from scriba import ALLOWED_TAGS, ALLOWED_ATTRS

css = CSSSanitizer(allowed_css_properties=("transform","transform-origin","width","height"))
safe = bleach.clean(doc.html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, css_sanitizer=css, strip=True)
```

## Serve static assets

Assets ship inside the Python package. Copy them at deploy time:

```python
from importlib.resources import files
import shutil
src = files("scriba.tex.static")
shutil.copytree(str(src), "./public/scriba", dirs_exist_ok=True)
```

Then include in your template:

```html
<link rel="stylesheet" href="/cdn/katex/katex.min.css">
<link rel="stylesheet" href="/public/scriba/scriba-tex-content.css">
<link rel="stylesheet" href="/public/scriba/scriba-tex-pygments-light.css">
<script defer src="/public/scriba/scriba-tex-copy.js"></script>

<article class="scriba-tex-content">{{ doc.html }}</article>
```

## Status

- **0.1.0-alpha** — TeX plugin complete; diagram plugin (D2) planned for 0.2/0.3.
- See `docs/scriba/` in the ojcloud repo for the full architecture contract, roadmap, and open questions.

## License

MIT. See `LICENSE`.
