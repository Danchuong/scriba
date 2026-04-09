# 04 — Packaging and Build Specification

> Normative reference for the `scriba` wheel layout, build system, dependencies, vendored assets, and versioning scheme. Binds verbatim to [`01-architecture.md`](01-architecture.md) (package layout, `RendererAssets`, `SCRIBA_VERSION`) and to [`02-tex-plugin.md`](02-tex-plugin.md) (KaTeX worker resolution, static assets). Where this file and those documents appear to disagree, `01-architecture.md` wins and this file is the bug.

## 1. Build system

Scriba uses **Hatchling** as its PEP 517 build backend:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

No compiled extensions, no Cython, no CFFI. The wheel is pure Python plus static JS/CSS/font assets. `pip wheel .` and `pip install -e ".[dev]"` are the only build commands that need to work.

## 2. Python version requirement

```
requires-python = ">=3.10"
```

Scriba targets Python 3.10+ and tests against 3.10, 3.11, and 3.12. The lower bound is driven by `match` statement usage, `|` union type syntax in annotations, and `importlib.resources.files()` behavior (stable since 3.9 but practically reliable from 3.10).

## 3. Dependencies

### 3.1 Runtime dependencies (PyPI)

| Package | Constraint | Purpose |
|---------|-----------|---------|
| `pygments` | `>=2.17,<2.20` | Syntax highlighting for `\begin{lstlisting}` code blocks. Upper bound prevents silent output changes from new Pygments token categories. |

Scriba has exactly **one** runtime PyPI dependency. This is intentional — rendering libraries must be lightweight to embed in backend services.

### 3.2 External runtime requirements

| Dependency | Version | Why |
|------------|---------|-----|
| **Node.js** | 18+ | The KaTeX math worker (`katex_worker.js`) runs as a persistent Node.js subprocess via `SubprocessWorker`. Node is **not** a PyPI dependency — it must be present on `$PATH` (or supplied via `TexRenderer(node_executable="/path/to/node")`). |

`pip install scriba` does not install or verify Node.js. If `node` is absent, the first math render raises `WorkerError` with a clear diagnostic. This is documented in `README.md` and is by design — Scriba does not silently degrade when math rendering is unavailable.

### 3.3 Dev dependencies

```toml
[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "bleach>=6.1",
  "lxml>=5.0",
]
```

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner. |
| `bleach` | Used in integration tests to verify that Scriba output survives sanitization through the shipped `ALLOWED_TAGS` / `ALLOWED_ATTRS` allowlist. |
| `lxml` | HTML tree assertions in snapshot tests. |

Install with `pip install -e ".[dev]"`.

## 4. Vendored dependencies

### 4.1 KaTeX 0.16.11

KaTeX is vendored inside the wheel at `scriba/tex/vendor/katex/` so that `pip install scriba` is self-contained — no separate `npm install -g katex` step is required.

**Location:**

```
scriba/tex/vendor/katex/
├── katex.min.js          # 269 KiB — consumed by katex_worker.js
├── katex.min.css         # 21 KiB — served to the browser by the consumer
├── LICENSE               # MIT (Khan Academy)
├── VENDORED.md           # Provenance metadata, SHA-256 checksums
└── fonts/
    └── KaTeX_*.woff2     # 20 font files, 296 KiB total
```

**SHA-256 verification (pinned in `VENDORED.md`):**

| File | SHA-256 |
|------|---------|
| `katex.min.js` | `e6bfe5deebd4c7ccd272055bab63bd3ab2c73b907b6e6a22d352740a81381fd4` |
| `katex.min.css` | `f0dbfcc2940b4d788c805c1a1e117e898d2814b0f1a52bf16640543216e0964d` (post-strip) |

The vendored `katex.min.css` has `.woff` and `.ttf` `@font-face` fallbacks stripped — only `.woff2` sources remain. Modern browsers support woff2 universally; stripping the unused formats avoids 18 dead 404 requests.

### 4.2 Update process

To bump the vendored KaTeX version (e.g. `0.16.11` -> `0.16.12`):

```bash
packages/scriba/scripts/vendor_katex.sh 0.16.12
```

The script:

1. Downloads `katex.min.js`, `katex.min.css`, and the `LICENSE` from jsDelivr CDN.
2. Downloads all `KaTeX_*.woff2` fonts referenced by the CSS.
3. Strips `.woff` and `.ttf` `@font-face` fallbacks from the CSS (woff2-only).
4. Computes SHA-256 checksums for `katex.min.js` and the post-strip `katex.min.css`.
5. Updates `VENDORED.md` in place with the new version, date, and checksums.

**Commit all changed files together:** `katex.min.js`, `katex.min.css`, `fonts/*.woff2`, `LICENSE`, and `VENDORED.md`. A KaTeX version bump is a coordinated change — also update `CHANGELOG.md` and `README.md` where the version is referenced.

## 5. Package data included in wheel

The `[tool.hatch.build.targets.wheel.package-data]` section declares exactly which non-Python files ship inside the wheel:

```toml
[tool.hatch.build.targets.wheel.package-data]
"scriba" = ["py.typed"]
"scriba.tex" = [
  "katex_worker.js",
  "static/*.css",
  "static/*.js",
  "vendor/katex/*.js",
  "vendor/katex/*.css",
  "vendor/katex/*.md",
  "vendor/katex/LICENSE",
  "vendor/katex/fonts/*.woff2",
]
"scriba.diagram" = ["static/*.css", "static/*.js"]
```

### 5.1 TeX plugin package data

| Path | Purpose |
|------|---------|
| `scriba/tex/katex_worker.js` | Node.js worker script, spawned by `SubprocessWorker` via `importlib.resources`. |
| `scriba/tex/static/scriba-tex-content.css` | Base content styling (sections, lists, tables, figures, code blocks). |
| `scriba/tex/static/scriba-tex-pygments-light.css` | Pygments light theme stylesheet. |
| `scriba/tex/static/scriba-tex-pygments-dark.css` | Pygments dark theme stylesheet. |
| `scriba/tex/static/scriba-tex-copy.js` | Copy-to-clipboard handler for code blocks. |
| `scriba/tex/vendor/katex/katex.min.js` | Vendored KaTeX runtime (consumed server-side by the worker). |
| `scriba/tex/vendor/katex/katex.min.css` | Vendored KaTeX stylesheet (served client-side by the consumer). |
| `scriba/tex/vendor/katex/fonts/*.woff2` | 20 vendored KaTeX math fonts (served client-side). |
| `scriba/tex/vendor/katex/VENDORED.md` | Provenance and SHA-256 metadata. |
| `scriba/tex/vendor/katex/LICENSE` | KaTeX MIT license. |

### 5.2 Diagram plugin package data

| Path | Purpose |
|------|---------|
| `scriba/diagram/static/scriba-diagram.css` | Diagram figure styling. |
| `scriba/diagram/static/scriba-diagram-steps.js` | Step animation runtime (diagram walkthroughs). |

### 5.3 Top-level marker

| Path | Purpose |
|------|---------|
| `scriba/py.typed` | PEP 561 marker — declares the package ships inline type information. |

## 6. Wheel build include/exclude

```toml
[tool.hatch.build.targets.wheel]
packages = ["scriba"]
include = [
  "scriba/**",
  "README.md",
  "CHANGELOG.md",
  "CONTRIBUTING.md",
  "SECURITY.md",
  "LICENSE",
]
exclude = [
  "PHASE2_DECISIONS.md",
  "tests/**",
  "examples/**",
]
```

User-facing docs (`README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`) ship with the wheel. Internal design logs (`PHASE2_DECISIONS.md`), tests, and examples are excluded.

## 7. Asset namespace convention

Asset basenames follow the convention `<renderer>/<basename>`, where `<renderer>` matches `Renderer.name`:

- `tex/scriba-tex-content.css`
- `tex/scriba-tex-pygments-light.css`
- `tex/scriba-tex-copy.js`
- `diagram/scriba-diagram.css`
- `diagram/scriba-diagram-steps.js`

Within the Python package, these map to `scriba.<renderer>.static.<basename>`. All CSS/JS filenames are prefixed with `scriba-<renderer>-` to guarantee global uniqueness when consumers dump assets from multiple plugins into a single static directory.

`RenderArtifact.css_assets` and `RenderArtifact.js_assets` carry **basenames only** (e.g. `"scriba-tex-content.css"`), never paths. `RendererAssets.css_files` and `RendererAssets.js_files` carry **absolute `Path` objects** resolved via `importlib.resources` at construction time. The `Pipeline` unions the basenames onto `Document.required_css` / `Document.required_js`; consumers use the basenames to locate the on-disk files.

## 8. Asset serving strategy for consumers

Scriba renders HTML fragments, not full pages. Consumers are responsible for serving the required CSS, JS, and font assets. Two approaches are supported:

### 8.1 Copy at deploy time (recommended)

```python
from importlib.resources import files
import shutil

# Copy TeX plugin static assets
shutil.copytree(
    str(files("scriba.tex.static")),
    "./public/scriba",
    dirs_exist_ok=True,
)

# Copy vendored KaTeX CSS + fonts (consumer must serve these to the browser)
shutil.copytree(
    str(files("scriba.tex.vendor.katex")),
    "./public/katex",
    dirs_exist_ok=True,
)
```

Then reference in HTML:

```html
<link rel="stylesheet" href="/public/katex/katex.min.css">
<link rel="stylesheet" href="/public/scriba/scriba-tex-content.css">
<link rel="stylesheet" href="/public/scriba/scriba-tex-pygments-light.css">
<script defer src="/public/scriba/scriba-tex-copy.js"></script>
```

The vendored `katex.min.css` references fonts via relative `url(fonts/KaTeX_*.woff2)`, so `katex.min.css` and the `fonts/` directory must live in the same parent.

### 8.2 Direct importlib.resources access

For environments where deploy-time copying is impractical (e.g. serverless), consumers can resolve asset paths at runtime:

```python
from importlib.resources import files

css_path = files("scriba.tex").joinpath("static", "scriba-tex-content.css")
```

`importlib.resources.files()` returns a `Traversable` which is a real filesystem path when the package is installed from a wheel. **Zipapp installs are unsupported in Scriba 0.1** — `katex_worker.js` must be a real file on disk for `SubprocessWorker` to pass it to `node` via `argv`.

## 9. Version scheme

Scriba uses two version identifiers that serve different purposes:

### 9.1 `__version__` (package version)

```python
__version__: str = "0.1.1-alpha"
```

Standard PEP 440 version string. Bumped on every PyPI release. Tracks the overall package lifecycle: new features, bug fixes, dependency bumps.

### 9.2 `SCRIBA_VERSION` (API contract version)

```python
SCRIBA_VERSION: int = 2
```

Integer version of the core abstractions (`Pipeline`, `Document`, `Renderer`, `RenderArtifact`, `RenderContext`). Bumped **only** when the core API changes in a way that invalidates consumer caches — independent of `__version__`.

Consumers key their render caches on `Document.versions`, which includes `{"core": SCRIBA_VERSION, "tex": <TexRenderer.version>, ...}`. A `SCRIBA_VERSION` bump signals that cached HTML must be re-rendered even if the source document has not changed.

Both constants live in `scriba/_version.py` and are re-exported from `scriba.__init__`.

## 10. Wheel structure

A built wheel contains the following top-level tree:

```
scriba/
├── __init__.py
├── _version.py
├── py.typed
├── core/
│   ├── __init__.py
│   ├── artifact.py
│   ├── context.py
│   ├── renderer.py
│   ├── pipeline.py
│   ├── workers.py
│   └── errors.py
├── tex/
│   ├── __init__.py
│   ├── renderer.py
│   ├── parser.py
│   ├── math.py
│   ├── highlight.py
│   ├── copy_button.py
│   ├── validate.py
│   ├── katex_worker.js
│   ├── static/
│   │   ├── scriba-tex-content.css
│   │   ├── scriba-tex-pygments-light.css
│   │   ├── scriba-tex-pygments-dark.css
│   │   └── scriba-tex-copy.js
│   └── vendor/
│       └── katex/
│           ├── katex.min.js
│           ├── katex.min.css
│           ├── VENDORED.md
│           ├── LICENSE
│           └── fonts/
│               └── KaTeX_*.woff2  (20 files)
├── diagram/
│   ├── __init__.py
│   ├── renderer.py
│   ├── engine.py
│   ├── steps.py
│   └── static/
│       ├── scriba-diagram.css
│       └── scriba-diagram-steps.js
└── sanitize/
    ├── __init__.py
    └── whitelist.py
```

Plus top-level metadata files at the wheel root: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`.

## 11. Entry points

Scriba 0.1 declares no console scripts, GUI scripts, or plugin entry points. The package is a library — consumers import it directly:

```python
from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer
```

Plugins (`TexRenderer`, `DiagramRenderer`) are **not** re-exported from the top-level `scriba` namespace. Consumers import them explicitly from `scriba.tex` / `scriba.diagram`. This keeps the top-level namespace stable and prevents plugin-private symbols from polluting `scriba.*`.

## 12. Constraints and non-goals

- **No compiled extensions.** The wheel is pure Python + static assets. No platform-specific wheels.
- **No zipapp support (v0.1).** `katex_worker.js` must exist as a real file on disk — `SubprocessWorker` passes it to `node` via argv. Zipapp-based installs where `importlib.resources` returns a zip-internal `Traversable` are unsupported.
- **No bundled Node.js.** Scriba does not vendor or download a Node.js runtime. Consumers provide it.
- **No automatic asset serving.** Scriba produces HTML fragments and declares which assets are needed. Consumers decide where and how to serve them.
