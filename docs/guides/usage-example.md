# 08 — End-to-end usage example

> A complete worked example showing how a `.tex` problem statement that
> uses one `\begin{animation}` block flows through the `scriba.Pipeline`
> and becomes HTML. Uses the real Python API from the `scriba/` package.
> Does not re-derive the HTML/CSS contract — see
> [`environments.md`](../spec/environments.md) for the canonical output
> shape; this file only shows the outline you should expect.
>
> **Note (v0.5.x):** `\begin{diagram}` is reserved for extension E5 and
> is not a first-class IR. Prefer a single-frame `\begin{animation}`
> everywhere a "diagram" would have been used. The legacy
> `DiagramRenderer` shim is no longer part of the public API surface.

## 1. The scenario

You are `tenant-backend`. An author has submitted a Frog DP problem. They
want one picture in the statement: a small **animation** showing the
first three `dp` cells getting filled in — a filmstrip with three
frames, one narration sentence each.

The author writes one `.tex` file. You run it through Scriba. You cache
the resulting HTML by content hash and serve it.

## 2. The source `.tex` file

`problems/frog1/statement.tex`:

```tex
\section*{Frog 1}

Có $n$ hòn đá được đánh số từ $1$ tới $n$. Con ếch đứng ở hòn đá $1$
và muốn tới hòn đá $n$. Tại hòn đá $i$ ếch có thể nhảy tới $i+1$ hoặc
$i+2$, tốn chi phí $|h_i - h_j|$ với $h$ là chiều cao từng hòn.

Gọi $dp[i]$ là chi phí tối thiểu để tới hòn đá $i$. Ta có:
\[
  dp[i] = \min\bigl(dp[i-1] + |h_i - h_{i-1}|,\; dp[i-2] + |h_i - h_{i-2}|\bigr)
\]

\subsection*{Minh hoạ với $h = [10, 30, 40, 20]$}

\begin{animation}[id=frog1-mini, label="Frog 1 — three base steps"]
  % Precompute the small table so we don't hand-write frame values.
  \shape{dp}{Array}{size=4, labels="dp[0]..dp[3]"}
  \compute{
      h = [10, 30, 40, 20]
      n = len(h)
      INF = 10**9
      dp = [INF] * n
      dp[0] = 0
      dp[1] = abs(h[1] - h[0])
      for i in range(2, n):
          a = dp[i-1] + abs(h[i] - h[i-1])
          b = dp[i-2] + abs(h[i] - h[i-2])
          dp[i] = min(a, b)
  }

  \step
    \apply{dp.cell[0]}{value=${dp[0]}}
    \recolor{dp.cell[0]}{state=done}
    \narrate{Khởi tạo: $dp[0] = 0$ vì ếch đã ở hòn đá đầu tiên.}

  \step
    \apply{dp.cell[1]}{value=${dp[1]}}
    \highlight{dp.cell[1]}
    \narrate{Chỉ có một cách: nhảy từ $0$ sang $1$, chi phí $|30 - 10| = 20$.}

  \step
    \apply{dp.cell[2]}{value=${dp[2]}}
    \highlight{dp.cell[2]}
    \narrate{$dp[2] = \min(dp[1] + 10,\; dp[0] + 30) = 30$.}
\end{animation}
```

Two things to notice:

1. Everything outside the environment is plain LaTeX. It will be picked
   up by `TexRenderer` in the usual way.
2. The animation uses `\compute{...}` (Starlark) to fill in actual values
   from `h`. The narration prose is hand-written — Starlark computes
   numbers, the author writes sentences.

## 3. The Python entry point

This is what your caller in `tenant-backend` (or a notebook, or a CLI
wrapper) actually runs. Every import below is the real package layout
under `packages/scriba/scriba/`:

```python
from __future__ import annotations

from pathlib import Path

from scriba import (
    Pipeline,
    RenderContext,
    SubprocessWorkerPool,
)
from scriba.tex import TexRenderer
from scriba.animation import AnimationRenderer


def build_pipeline() -> Pipeline:
    """Construct a Pipeline once per process.

    Order matters: AnimationRenderer MUST precede TexRenderer so that
    the Pipeline's first-wins overlap rule carves out the
    ``\\begin{animation}`` regions before TexRenderer's detector ever
    sees them.
    """
    pool = SubprocessWorkerPool(max_workers=4)
    return Pipeline(
        renderers=[
            AnimationRenderer(),          # uses the default in-process Starlark host
            TexRenderer(worker_pool=pool),
        ]
    )


def no_external_resources(_filename: str) -> str | None:
    """This problem has no \\includegraphics — resolver returns None."""
    return None


def render_problem(source_path: Path, out_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    ctx = RenderContext(
        resource_resolver=no_external_resources,
        theme="light",
    )

    with build_pipeline() as pipeline:
        doc = pipeline.render(source, ctx)

    out_path.write_text(doc.html, encoding="utf-8")

    print("required_css:", sorted(doc.required_css))
    print("required_js :", sorted(doc.required_js))  # [] — zero runtime JS
    print("versions    :", doc.versions)
    # versions looks like:
    #   {"core": N, "animation": 1, "tex": 1}
    # Use this as part of your content-hash cache key.


if __name__ == "__main__":
    render_problem(
        Path("problems/frog1/statement.tex"),
        Path("problems/frog1/statement.html"),
    )
```

Notes on the API surface you are actually touching:

- `Pipeline(renderers=[...])` is the constructor. It validates that
  every renderer has a unique `name`. Order is the tiebreak after
  `(start, priority)`. See `scriba/core/pipeline.py`.
- `RenderContext` is a frozen dataclass. The only required field is
  `resource_resolver`. The Pipeline's default context provider
  automatically wires `render_inline_tex` from the registered
  `TexRenderer`, so `\narrate{...}` bodies get real KaTeX rendering for
  inline math without any extra setup.
- `pipeline.render(source, ctx)` returns a `Document` with:
  - `html: str` — the fully substituted, sanitized HTML.
  - `required_css: frozenset[str]` — namespaced basenames like
    `animation/filmstrip.css`, `animation/scene-primitives.css`,
    `tex/katex.css`. Ship these globally, once.
  - `required_js: frozenset[str]` — always empty for `animation`.
    `TexRenderer` also ships no runtime JS.
  - `versions: dict[str, int]` — include this in your cache key so a
    plugin bump invalidates exactly the right documents.
  - `block_data: dict[str, Any]` — optional per-block machine-readable
    payloads indexed by scene id (e.g. `frog1-mini`). Use for search,
    analytics, or regenerating thumbnails.
- `SubprocessWorkerPool` is the sandbox. `\compute{...}` runs inside a
  worker with CPU/memory/time caps. No I/O, no randomness, no clock.
  Identical input ⇒ identical output.
- `with pipeline:` closes every renderer and tears the pool down. Use
  the context manager in scripts. In a long-lived service, build the
  pipeline once at startup and call `pipeline.close()` on shutdown.

## 4. What the HTML looks like

The exact class names, ARIA attributes, and nested structure are locked
in [`environments.md`](../spec/environments.md). Do not duplicate that
contract here; reference it. What your caller should expect in broad
strokes:

```html
<!-- plain LaTeX rendered by TexRenderer (the problem statement itself) -->
<h2>Frog 1</h2>
<p>Có <span class="scriba-tex">…</span> hòn đá…</p>
<p>Gọi <span class="scriba-tex">…</span> là chi phí…</p>
<div class="scriba-tex-display">…</div>

<h3>Minh hoạ với …</h3>

<!-- AnimationRenderer output: one <figure> wrapping an <ol> of frames -->
<figure class="scriba-animation"
        data-scriba-scene="frog1-mini"
        aria-label="Frog 1 — three base steps">
  <ol class="scriba-frames">
    <li class="scriba-frame" id="frog1-mini-frame-1" data-step="1">
      <svg class="scriba-stage-svg" role="img" aria-labelledby="…">
        <!-- Array primitive, cell[0] in state=done -->
      </svg>
      <p class="scriba-narration">Khởi tạo: <span class="scriba-tex">…</span>.</p>
    </li>
    <li class="scriba-frame" id="frog1-mini-frame-2" data-step="2">…</li>
    <li class="scriba-frame" id="frog1-mini-frame-3" data-step="3">…</li>
  </ol>
</figure>
```

Every SVG is fully self-contained. No `<script>`. No `<foreignObject>`
containing HTML. No external references beyond the one global CSS file.
Under `@media print`, the CSS contract collapses `.scriba-frames` to
a vertical `display: block` stack so the filmstrip prints as three
numbered figures down the page.

## 5. What ships to the browser

- The `doc.html` string, dropped into your template.
- The CSS files named in `doc.required_css`. In ojcloud's setup these
  are served once, globally, by the tenant frontend and linked via a
  plain `<link rel="stylesheet">`. They are versioned by
  `doc.versions`, not per-request.
- Nothing else. No `<script>` tag. No polyfill. No web component
  upgrade. The page is fully rendered the moment the HTML parser
  finishes.

## 6. Caching

The combination that uniquely identifies rendered output is:

```
cache_key = sha256(source) || json.dumps(doc.versions, sorted) || theme
```

If either the source or any renderer version changes, the key changes
and the cache entry is regenerated. If nothing changes, you serve
bytes. Scriba guarantees determinism so this cache is safe.

## 7. Error handling

`pipeline.render` raises `ScribaError` (or a subclass) on anything the
renderers cannot recover from: grammar errors in an environment
(`E1xxx`), Starlark timeouts (`E1152`), sandbox violations, malformed
options. Catch it at the request boundary, log the error code, and
present the author a line-numbered diagnostic. See
[`error-codes.md`](../spec/error-codes.md) for the full error catalog.

```python
from scriba import ScribaError

try:
    doc = pipeline.render(source, ctx)
except ScribaError as exc:
    log.warning("scriba render failed: %s", exc)
    return render_author_error_page(exc)
```

That is the whole pipeline, end to end. One `.tex` file in, one HTML
string plus a CSS asset manifest out, no JavaScript anywhere.
