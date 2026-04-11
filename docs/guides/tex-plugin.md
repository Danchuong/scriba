# 02 — `scriba.tex` plugin

> Wave 2 elaboration. Binds verbatim to names locked in [`01-architecture.md`](../spec/architecture.md): `Block`, `RenderArtifact`, `Document`, `RenderContext`, `Renderer`, `RendererAssets`, `Pipeline`, `SubprocessWorker`, `SubprocessWorkerPool`, `ScribaError`, `RendererError`, `WorkerError`, `ValidationError`, `ResourceResolver`, `ALLOWED_TAGS`, `ALLOWED_ATTRS`. Do not relitigate those names here — if you think one is wrong, file an entry in `07-open-questions.md`.

## 1. Purpose

Port the existing `services/tenant/backend/app/utils/tex_renderer.py` (1686 lines) into `scriba/tex/*`, stripping every implicit frontend coupling. The resulting module implements the `Renderer` protocol from `01-architecture.md` §"Renderer protocol" and produces a self-contained `RenderArtifact` whose HTML fragment depends only on `scriba/tex/static/*` assets — no Tailwind classes, no hardcoded `/api/problems/{id}/...` URLs, no `@_traced_render` imports, no frontend regex that rewrites the HTML after the fact.

The current renderer does three things backwards for a shipping library:

1. It bakes `class="katex-display my-4 text-center"` and inline `style="border: 1px solid #374151"` directly into HTML, binding consumers to Tailwind and a fixed palette.
2. It reaches into Flask config for `base_url` and `problem_id` inside utility functions (`tex_renderer.py:150`, `:311`).
3. It expects the frontend (`services/tenant/frontend/components/pre-rendered-tex.tsx`) to regex-inject copy buttons and rewrite `src` attributes at hydration time.

Scriba's `TexRenderer` reverses all three: emits stable `scriba-tex-*` class names, receives URL resolution via `ctx.resource_resolver`, and writes `<button>` elements statically at render time.

## 2. Public API

```python
# scriba/tex/renderer.py
from __future__ import annotations

from pathlib import Path
from typing import Literal, Mapping

from scriba.core.artifact import Block, RenderArtifact
from scriba.core.context import RenderContext
from scriba.core.errors import RendererError, ValidationError, WorkerError
from scriba.core.renderer import Renderer, RendererAssets
from scriba.core.workers import SubprocessWorker, SubprocessWorkerPool


class TexRenderer:
    """Render a TeX-flavored problem statement to a self-contained HTML fragment.

    Implements the :class:`scriba.Renderer` protocol (see 01-architecture.md).
    ``TexRenderer`` is a *whole-document* renderer: unlike a fenced diagram
    renderer, it claims the entire source as a single :class:`scriba.Block`
    from :meth:`detect`, and :meth:`render_block` drives the full parser
    pipeline over that block.

    The renderer is stateless per render call. All mutable state (the KaTeX
    inline LRU cache, the subprocess handle) is held on the instance and is
    thread-safe: the subprocess is guarded by :class:`SubprocessWorker`'s
    internal lock, and the LRU cache uses :func:`functools.lru_cache` which
    is itself thread-safe.

    Construction-time arguments are keyword-only so that future additions
    never silently shift positional meanings.

    Parameters
    ----------
    worker_pool:
        The :class:`SubprocessWorkerPool` owned by the enclosing
        :class:`scriba.Pipeline`. ``TexRenderer`` registers its KaTeX worker
        into this pool under the stable name ``"katex"`` at ``__init__`` time.
        ``TexRenderer`` never owns or constructs its own pool — see §2.1
        below for the resolution of Wave 1 Ambiguity #5.
    pygments_theme:
        Which Pygments stylesheet this renderer expects the consumer to ship.
        One of ``"one-light"``, ``"one-dark"``, ``"github-light"``,
        ``"github-dark"``, or ``"none"``. Defaults to ``"one-light"``.
        ``"none"`` disables highlighting entirely and emits
        ``<pre class="scriba-tex-code-plain">`` with HTML-escaped source.
        Scriba 0.1 ships stylesheets for ``one-light`` and ``one-dark``;
        ``github-light`` and ``github-dark`` are reserved names and fall
        back to ``one-*`` until 0.2.
    enable_copy_buttons:
        If ``True`` (default), every ``lstlisting`` code block is followed
        by a static ``<button class="scriba-tex-copy-btn">`` element and
        :meth:`assets` includes ``scriba-tex-copy.js`` in ``js_files``. If
        ``False``, no button is emitted and the JS asset is omitted.
    katex_macros:
        Optional mapping of macro name to KaTeX macro expansion, forwarded
        verbatim to the KaTeX worker on every batch request
        (``{"type": "batch", "macros": {...}, "items": [...]}``). Example:
        ``{"\\RR": "\\mathbb{R}"}``. Defaults to ``None`` (no macros).
    katex_worker_path:
        Override path to ``katex_worker.js``. Defaults to the bundled
        ``importlib.resources.files("scriba.tex").joinpath("katex_worker.js")``.
        Provided so ops teams can pin a patched worker without rebuilding
        the wheel.
    katex_worker_timeout:
        Per-request read timeout in seconds, forwarded to the registered
        :class:`SubprocessWorker`. Defaults to ``10.0``.
    katex_worker_max_requests:
        Respawn threshold forwarded to the registered
        :class:`SubprocessWorker`. Defaults to ``50_000``, matching the
        existing ojcloud ``KaTeXWorker._max_requests``
        (``services/tenant/backend/app/utils/katex_worker.py:46``).
    node_executable:
        Name or path of the Node.js binary used to launch the worker.
        Defaults to ``"node"`` (resolved via ``$PATH``). Consumers on
        systems with a non-standard Node install pass an absolute path.
    strict_math:
        If ``True``, a KaTeX parse error raises
        :class:`scriba.RendererError`. If ``False`` (default), parse errors
        are caught and rendered as ``<span class="scriba-tex-math-error">``
        with the offending source in a ``title`` attribute, matching the
        current ojcloud behavior.
    """

    name: str = "tex"
    version: int = 1

    def __init__(
        self,
        *,
        worker_pool: SubprocessWorkerPool,
        pygments_theme: Literal[
            "one-light", "one-dark", "github-light", "github-dark", "none"
        ] = "one-light",
        enable_copy_buttons: bool = True,
        katex_macros: Mapping[str, str] | None = None,
        katex_worker_path: str | Path | None = None,
        katex_worker_timeout: float = 10.0,
        katex_worker_max_requests: int = 50_000,
        node_executable: str = "node",
        strict_math: bool = False,
    ) -> None: ...

    def detect(self, source: str) -> list[Block]:
        """Return a single :class:`Block` covering the entire source.

        TeX is a whole-document dialect: there are no fenced "tex blocks"
        to isolate. The returned list always has length 1 with
        ``start=0``, ``end=len(source)``, ``kind="tex"``, ``raw=source``,
        ``metadata=None``.

        The :class:`scriba.Pipeline` overlap-resolution algorithm (see
        01-architecture.md step 2) still applies: if a later renderer (e.g.
        :class:`DiagramRenderer`) claims a narrower range inside the TeX
        document, that narrower range wins only if the diagram renderer was
        registered *before* ``TexRenderer`` in the :class:`Pipeline`
        constructor list. In the default 0.1 ordering TeX is registered
        first and owns the whole document.
        """

    def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact:
        """Render the full TeX block to a :class:`RenderArtifact`.

        Raises
        ------
        RendererError
            If ``strict_math`` is ``True`` and KaTeX reports a parse error,
            or if the parser encounters an unrecoverable structural fault
            that :meth:`validate` would also reject.
        WorkerError
            Propagated from the KaTeX :class:`SubprocessWorker` on crash
            or timeout. ``TexRenderer`` does not swallow worker errors.
        """

    def assets(self) -> RendererAssets:
        """Return the always-on CSS/JS files this plugin ships.

        Always includes ``scriba-tex-content.css`` plus the stylesheet
        selected by ``pygments_theme`` (unless ``"none"``). Includes
        ``scriba-tex-copy.js`` only when ``enable_copy_buttons`` is
        ``True``. Paths are resolved via
        ``importlib.resources.files("scriba.tex") / "static" / name``.
        """

    def validate(self, content: str) -> tuple[bool, str | None]:
        """Structural pre-check for a TeX source.

        Returns ``(True, None)`` on success or ``(False, message)`` on
        failure. Never raises. Intended for consumers that want to reject
        malformed input at submission time without attempting a full render.
        See §10 for the 6 validator test cases.
        """

    def close(self) -> None:
        """Shut down this renderer's resources.

        ``TexRenderer`` does not own the :class:`SubprocessWorkerPool`, so
        ``close()`` does **not** close the pool. It only clears the
        internal LRU cache and marks the instance closed. Idempotent.
        The enclosing :class:`Pipeline` is responsible for closing the pool.
        """

    def __enter__(self) -> "TexRenderer": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...

    # --- private API consumed by the Pipeline ------------------------------

    def _render_inline(self, tex: str) -> str:
        """Render a standalone inline-math fragment to HTML.

        Called by :class:`Pipeline` when auto-populating
        :attr:`RenderContext.render_inline_tex` for other plugins (see §12
        Ambiguity #2). Not part of the public API. Uses the same LRU cache
        as :meth:`render_block`.
        """
```

### 2.1 Worker-pool ownership — resolution

`TexRenderer` does **not** own a `SubprocessWorkerPool`. The `Pipeline` owns exactly one pool per instance and injects it into every `Renderer` that needs subprocess I/O at construction time. `TexRenderer.__init__` receives the pool via the `worker_pool` keyword argument and immediately registers its KaTeX worker:

```python
worker_pool.register(
    "katex",
    argv=[node_executable, str(resolved_katex_worker_path)],
    ready_signal="katex-worker ready",
    max_requests=katex_worker_max_requests,
    default_timeout=katex_worker_timeout,
)
```

The worker is not spawned here — `SubprocessWorkerPool.register()` only records the spec. The first call to `render_block()` that dispatches math triggers `worker_pool.get("katex")`, which lazily spawns the Node process on the calling thread. This matches the contract in `01-architecture.md` §"SubprocessWorkerPool".

**Constructing `TexRenderer` standalone (without a `Pipeline`).** Consumers who want to use the renderer outside of a `Pipeline` (e.g. in a one-off CLI script or a unit test) must construct their own `SubprocessWorkerPool`, pass it in, and close both objects explicitly:

```python
from scriba import SubprocessWorkerPool
from scriba.tex import TexRenderer

with SubprocessWorkerPool() as pool:
    renderer = TexRenderer(worker_pool=pool)
    # ... use renderer ...
    renderer.close()
```

In normal use inside `Pipeline`, the consumer never constructs the pool directly; the `Pipeline` constructor creates one and passes it to every registered renderer that accepts a `worker_pool` parameter. See §12 Ambiguity #5 for the migration note.

## 3. HTML output contract

Every TeX construct maps to a deterministic HTML shape with stable `scriba-tex-*` class names. No Tailwind, no inline color, no `style="font-size: 85%"` baked string literals, no `class="my-4 text-center"`. Inline `style=""` is permitted only for per-instance data that cannot live in a stylesheet: KaTeX display transform, `\includegraphics` explicit pixel width/height, and nothing else.

| TeX source | Emitted HTML |
|---|---|
| `$x^2$` (inline math) | `<span class="scriba-tex-math-inline"><span class="katex">…MathML + SVG…</span></span>` |
| `$$\sum_i a_i$$` (display) | `<div class="scriba-tex-math-display"><span class="katex-display">…</span></div>` |
| `$$$\sum_i a_i$$$` (Polygon triple-dollar display) | Identical to `$$…$$` — the triple form is normalized to display mode during tokenization. |
| `\textbf{A}` | `<strong>A</strong>` |
| `\textit{A}`, `\emph{A}`, `\it A` | `<em>A</em>` |
| `\texttt{A}`, `\tt A` | `<code class="scriba-tex-code-inline">A</code>` |
| `\underline{A}` | `<u>A</u>` |
| `\sout{A}` | `<s>A</s>` |
| `\textsc{A}` | `<span class="scriba-tex-smallcaps">A</span>` |
| `\tiny A` | `<span class="scriba-tex-size-tiny">A</span>` |
| `\scriptsize A` | `<span class="scriba-tex-size-scriptsize">A</span>` |
| `\small A` | `<span class="scriba-tex-size-small">A</span>` |
| `\normalsize A` | `<span class="scriba-tex-size-normalsize">A</span>` |
| `\large A` | `<span class="scriba-tex-size-large">A</span>` |
| `\Large A` | `<span class="scriba-tex-size-Large">A</span>` |
| `\LARGE A` | `<span class="scriba-tex-size-LARGE">A</span>` |
| `\huge A` | `<span class="scriba-tex-size-huge">A</span>` |
| `\Huge A` | `<span class="scriba-tex-size-Huge">A</span>` |
| `\section{Intro}` | `<h2 id="intro" class="scriba-tex-heading scriba-tex-heading-2">Intro</h2>` |
| `\subsection{Step One}` | `<h3 id="step-one" class="scriba-tex-heading scriba-tex-heading-3">Step One</h3>` |
| `\subsubsection{Detail}` | `<h4 id="detail" class="scriba-tex-heading scriba-tex-heading-4">Detail</h4>` |
| `\begin{itemize} \item A \end{itemize}` | `<ul class="scriba-tex-list scriba-tex-list-unordered"><li class="scriba-tex-list-item">A</li></ul>` |
| `\begin{enumerate} \item A \end{enumerate}` | `<ol class="scriba-tex-list scriba-tex-list-ordered"><li class="scriba-tex-list-item">A</li></ol>` |
| `\begin{center} X \end{center}` | `<div class="scriba-tex-center">X</div>` |
| `\begin{tabular}{…} … \end{tabular}` | `<table class="scriba-tex-table">…</table>` (see §3.2) |
| `\begin{lstlisting}[language=cpp] … \end{lstlisting}` + Pygments | `<div class="scriba-tex-code-block" data-language="cpp" data-code="ESCAPED_SOURCE"><div class="highlight"><pre><span class="tok-k">int</span>…</pre></div><button type="button" class="scriba-tex-copy-btn" aria-label="Copy code">Copy</button></div>` |
| `\begin{lstlisting} … \end{lstlisting}` (theme=none or unknown lang) | `<div class="scriba-tex-code-block" data-code="…"><pre class="scriba-tex-code-plain"><code>…</code></pre><button …>Copy</button></div>` |
| `\includegraphics[scale=0.5]{fig.png}` | `<img src="RESOLVED_URL" alt="fig.png" class="scriba-tex-image" style="transform: scale(0.5); transform-origin: top left" />` |
| `\includegraphics[width=5cm]{fig.png}` | `<img src="RESOLVED_URL" alt="fig.png" class="scriba-tex-image" style="width: 189px" />` (37.8 px/cm, rounded) |
| `\includegraphics{missing.png}` where `resource_resolver` returns `None` | `<span class="scriba-tex-image-missing" data-filename="missing.png">[missing image: missing.png]</span>` |
| `\epigraph{To iterate is human.}{Donald Knuth}` | `<blockquote class="scriba-tex-epigraph"><p class="scriba-tex-epigraph-quote">To iterate is human.</p><footer class="scriba-tex-epigraph-attribution">Donald Knuth</footer></blockquote>` |
| `\url{https://a.example}` | `<a class="scriba-tex-link" href="https://a.example" rel="noopener noreferrer">https://a.example</a>` |
| `\href{https://a.example}{click}` | `<a class="scriba-tex-link" href="https://a.example" rel="noopener noreferrer">click</a>` |
| `---` | `—` (U+2014) |
| `--` | `–` (U+2013) |
| `` ` `` + `` ` `` | `"` (U+201C opening); closing `''` → `"` (U+201D) |
| `~` | `&nbsp;` |
| `\\` | `<br />` |
| Blank line | Paragraph break — closes the current `<p class="scriba-tex-paragraph">` and opens a new one |

### 3.1 Heading id slugification

Heading text is slugified to produce the `id` attribute with these rules, applied in order:

1. Lowercase the text.
2. Normalize to NFKD and strip combining marks.
3. Replace every run of characters that is not `[a-z0-9]` with a single `-`.
4. Strip leading and trailing `-`.
5. If the resulting slug is empty (e.g. heading was `$\alpha$` only), use `section`.
6. Deduplication is scoped to one render call. A shared counter maps `base_slug -> next_suffix`. The first occurrence of a slug gets the bare slug; the second gets `-2`; the third `-3`; etc. Counters are per-render and reset on every `render_block` call.

Examples:

- `\section{Introduction}` → `id="introduction"`
- `\section{Bài toán 1}` → `id="bai-toan-1"` (NFKD strips the Vietnamese diacritics)
- Two `\section{Examples}` in one document → `id="examples"` then `id="examples-2"`
- `\section{  Big   Spaces  }` → `id="big-spaces"`
- `\section{$\alpha$}` → `id="section"` (math is stripped pre-slug, leaving empty)

### 3.2 Tabular — detailed contract

A `\begin{tabular}{|l|c|r|}` declares three columns with alignments left / center / right and vertical borders between them. Scriba emits:

```html
<table class="scriba-tex-table">
  <tr class="scriba-tex-table-row">
    <td class="scriba-tex-table-cell scriba-tex-align-left scriba-tex-border-left scriba-tex-border-right">…</td>
    <td class="scriba-tex-table-cell scriba-tex-align-center scriba-tex-border-right">…</td>
    <td class="scriba-tex-table-cell scriba-tex-align-right scriba-tex-border-right">…</td>
  </tr>
</table>
```

Rules:

- **Column spec parsing.** The column spec string is tokenized into a sequence where `l|c|r` chars produce alignment tokens and `|` chars produce a pending left-border flag that attaches to the next alignment token. A leading `|` attaches to the first column as `scriba-tex-border-left`. A trailing `|` attaches to the last column as `scriba-tex-border-right`. Interior `|` chars emit `scriba-tex-border-right` on the preceding column.
- **`\hline`.** A `\hline` before a row adds `scriba-tex-border-top` to every `<td>` in that row. A `\hline` after the last row adds `scriba-tex-border-bottom` to every `<td>` in the preceding row. Two consecutive `\hline` commands produce a double border by emitting both classes (no separate double-border class in 0.1).
- **`\cline{a-b}`.** Adds `scriba-tex-border-top` to cells in columns `a..b` (1-indexed, inclusive) of the following row only.
- **`\multicolumn{N}{spec}{content}`.** Emits `<td colspan="N" class="scriba-tex-table-cell scriba-tex-align-{…}">content</td>`. Border classes come from the `spec` string using the same rules as the full column spec. The cell consumes `N` column positions — the next cell in this row starts at column `current + N`.
- **`\multirow{N}{*}{content}`.** Emits `<td rowspan="N" class="…">content</td>`. Following rows skip this column position when rendering (tracked via a per-column rowspan counter).
- **Cell content.** Cell content passes through the full inline TeX parser — math, bold, italic, code, etc. all work inside a cell.

### 3.3 What inline `style=""` is allowed

Only three constructs emit inline `style`:

1. `\includegraphics[scale=…]` → `style="transform: scale(X); transform-origin: top left"`.
2. `\includegraphics[width=…]` / `[height=…]` → `style="width: Npx"` or `"height: Npx"` or both.
3. `scriba-tex-math-display` wrapper when KaTeX returns a display formula that needs a per-instance transform. (0.1 does not use this; reserved for 0.2.)

Everything else — borders, colors, font sizes, margins, text alignment — is a class that references a CSS custom property in `scriba-tex-content.css`. The bleach config in `01-architecture.md` §"Sanitization policy" restricts inline CSS to `transform`, `transform-origin`, `width`, `height`, which matches this list exactly.

## 4. Diff vs current ojcloud renderer

Line numbers refer to `services/tenant/backend/app/utils/tex_renderer.py` in the current repo. Changes below are what the port physically does — the rest of the file is mechanical function-body copies into smaller modules (see §11).

| Current code | Replacement |
|---|---|
| **Line 1200, 1209:** `f'<div class="katex-display my-4 text-center">{html}</div>'` | `<div class="scriba-tex-math-display">{html}</div>`. The `my-4` (margin) and `text-center` (alignment) move to `.scriba-tex-math-display { margin: 1rem 0; text-align: center }` in `scriba-tex-content.css`. |
| **Line 1058, 1062, 1067:** `style="border: 1px solid #374151"` on table cells | `class="scriba-tex-border-top scriba-tex-border-bottom scriba-tex-border-left scriba-tex-border-right"` selected from the column spec + `\hline` / `\cline` state. Color moves to `.scriba-tex-table-cell { border-color: var(--scriba-border) }`. |
| **Line 1272–1275:** epigraph inline styles (`style="border-left: 4px solid #6b7280; padding-left: 1rem; margin: 1rem 0; font-style: italic"`) | `<blockquote class="scriba-tex-epigraph">` with all visuals in CSS referencing `--scriba-epigraph-border`. |
| **Line 1350–1375:** `\tiny`/`\small`/`\Large`/… emitted as `<span style="font-size: 85%">` etc. with nine hardcoded percentages | Nine classes `scriba-tex-size-{tiny,scriptsize,small,normalsize,large,Large,LARGE,huge,Huge}` referencing nine `--scriba-font-size-*` variables already declared in `01-architecture.md` §"CSS variable naming convention". No inline `style` at all on size spans. |
| **Line 150:** `return f"{base_url}/api/problems/{problem_id}/{filename}"` hard-coding a tenant-specific URL shape | `return ctx.resource_resolver(filename)`. The consumer owns URL shape entirely. If the resolver returns `None`, the `scriba-tex-image-missing` placeholder is emitted (§3 table). |
| **Line 311:** second occurrence of the same base-URL concatenation inside `\includegraphics` handling | Same replacement — collapses to the single resolver call. |
| **Line 306, 309:** `@_traced_render("TeX body")` decorators importing `app.utils.tracing_decorators` | Deleted. Tracing is a consumer concern. A consumer that wants spans wraps `pipeline.render()` with their own decorator or OpenTelemetry instrumentation; Scriba does not import any observability library. |
| **Line 706:** `data-code="{escaped_source}"` attribute used by frontend JS for the copy button | Kept verbatim — the attribute still holds the escaped source. The only change is that Scriba also emits the static `<button>` right next to it, so the frontend JS no longer has to inject anything. |
| **Line 732–734:** `<div class="code-block-wrapper">` with a comment stating "frontend injects copy button here" | Replaced with `<div class="scriba-tex-code-block">` containing the actual static `<button class="scriba-tex-copy-btn" …>Copy</button>`. The class rename and the static button are a single atomic change. |

Everything else in `tex_renderer.py` — the brace matcher, the command dispatcher, the math parser, the Pygments call, the typographic replacements, the validator — is copied module-for-module per §11. No behavior change.

## 5. KaTeX worker integration

`TexRenderer` uses exactly one named worker, `"katex"`, registered into the injected `SubprocessWorkerPool` at construction time. The worker is a long-lived Node.js subprocess running `scriba/tex/katex_worker.js` (verbatim copy of `services/tenant/backend/katex_worker.js`, shipped as package data via `importlib.resources`).

### 5.1 Worker script path resolution

```python
import importlib.resources

if katex_worker_path is None:
    resolved = importlib.resources.files("scriba.tex").joinpath("katex_worker.js")
else:
    resolved = Path(katex_worker_path)
if not Path(str(resolved)).is_file():
    raise RendererError(
        f"KaTeX worker script not found at {resolved}",
        renderer="tex",
    )
```

`importlib.resources.files("scriba.tex").joinpath("katex_worker.js")` returns a `Traversable` which is a real filesystem path when the package is installed from a wheel and a zip path when installed from a zipapp. Scriba 0.1 supports the filesystem case only; zipapp installs are documented in `04-packaging.md` as unsupported.

### 5.2 Batching strategy

A single `render_block` call parses the source and collects every math expression into two ordered lists: `inline_items: list[str]` and `display_items: list[str]`. A single JSON request is dispatched:

```json
{
  "type": "batch",
  "macros": {"\\RR": "\\mathbb{R}"},
  "items": [
    {"id": "i0", "mode": "inline",  "tex": "x^2"},
    {"id": "i1", "mode": "inline",  "tex": "a_i"},
    {"id": "d0", "mode": "display", "tex": "\\sum_i a_i"}
  ]
}
```

The worker returns one response line:

```json
{
  "results": [
    {"id": "i0", "html": "<span class=\"katex\">…</span>"},
    {"id": "i1", "html": "<span class=\"katex\">…</span>"},
    {"id": "d0", "html": "<span class=\"katex-display\">…</span>"}
  ]
}
```

`TexRenderer` then substitutes each result back into the placeholder positions during the HTML emit pass. This matches the whole-document placeholder strategy the `Pipeline` itself uses — the same `\x00SCRIBA_MATH_{i}\x00` trick, scoped internally to `TexRenderer`. Math placeholders use a distinct tag (`SCRIBA_MATH`) from the pipeline's `SCRIBA_BLOCK` so the two are impossible to confuse.

The LRU cache described in §2 sits in front of the batch: on each `render_block` call, cached expressions are filtered out of the batch before dispatching. Only cache misses are sent to the worker. This keeps the batch size bounded by the number of *novel* math expressions in the document.

### 5.3 Fallback when Node is missing

If `SubprocessWorker` fails to spawn the Node process (e.g. `node` is not on `$PATH`), the first `get("katex")` call raises `WorkerError` with `stderr` containing the OS-level `FileNotFoundError` message. `TexRenderer` does not silently degrade to a text fallback — math is a first-class feature of problem statements and silent degradation would mask a real ops misconfiguration. Consumers who want a degradation path catch `WorkerError` at their render boundary and return a 500 with a clear error message.

### 5.4 Forwarding `katex_macros`

The `katex_macros` mapping is frozen at `__init__` time and copied into every batch request as the `macros` field. The KaTeX worker forwards it to `katex.renderToString(..., {macros: ...})`. Per-request macros (e.g. a problem-specific preamble) are **not** supported in 0.1; they would require thread-local state and break caching. Consumers that need per-problem macros construct one `TexRenderer` per macro set or wait for 0.2.

## 6. Pygments theme handling

Pygments is an **optional** runtime dependency declared as an extra in `pyproject.toml`: `scriba[pygments]`. The import is deferred until the first code block is rendered.

### 6.1 Theme selection

| `pygments_theme` value | Behavior |
|---|---|
| `"one-light"` | Highlight via `pygments`, emit `scriba-tex-code-block` with `<div class="highlight">…</div>`, include `scriba-tex-pygments-light.css` in `assets().css_files`. |
| `"one-dark"` | Same, dark stylesheet. |
| `"github-light"` | Reserved for 0.2. In 0.1, treated as `"one-light"` with a `DeprecationWarning` on first use. |
| `"github-dark"` | Same. Falls back to `"one-dark"`. |
| `"none"` | Pygments is not called. Emit `<pre class="scriba-tex-code-plain"><code>…</code></pre>` with HTML-escaped source. Neither light nor dark Pygments CSS appears in `assets().css_files`. |

### 6.2 Missing-Pygments fallback

If `pygments_theme != "none"` and `import pygments` fails at first use:

1. Log a warning once via `logging.getLogger("scriba.tex").warning(...)` with the message `"pygments not installed; falling back to plain code blocks. Install scriba[pygments] to enable highlighting."`.
2. Treat the renderer as if `pygments_theme="none"` for the remainder of its lifetime. The `assets()` return value is recomputed lazily on first call and cached, so the missing-Pygments state is visible to the consumer the first time they inspect `doc.required_css`.

This avoids a hard crash for consumers who install `scriba` without the extra and happen not to use code blocks.

### 6.3 Unknown language fallback

`\begin{lstlisting}[language=xyz]` where `xyz` is not a recognized Pygments lexer alias falls through to the `"none"` code path (plain `<pre class="scriba-tex-code-plain">`). This matches current ojcloud behavior and is covered by snapshot test #14 in §8.

## 7. Shipped assets

All assets ship inside `scriba/tex/static/` and are addressed by basename through `RendererAssets.css_files` / `js_files`. The `Pipeline` unions these into `Document.required_css` / `required_js`. The consumer resolves basename → on-disk path via `importlib.resources.files("scriba.tex") / "static" / name`.

| File | Purpose | Approx size |
|---|---|---|
| `scriba-tex-content.css` | All `.scriba-tex-*` class rules. Scoped under `.scriba-tex-content` wrapper so that consumers who drop `<div class="scriba-tex-content">…</div>` around the fragment get hermetic styling. Declares the full `--scriba-*` variable set from `01-architecture.md` §"CSS variable naming convention". | ~400 lines |
| `scriba-tex-pygments-light.css` | Pygments `.tok-*` selectors for the one-light theme. Uses `--scriba-*` variables where possible (e.g. comment color → `--scriba-fg-muted`). | ~120 lines |
| `scriba-tex-pygments-dark.css` | Dark-theme counterpart. Activated via `[data-theme="dark"]`. | ~120 lines |
| `scriba-tex-copy.js` | Vanilla IIFE, ~40 lines. Event-delegated click handler on `document` that matches `event.target.closest(".scriba-tex-copy-btn")`, reads the sibling `[data-code]` attribute, calls `navigator.clipboard.writeText(decoded)`, and swaps the button text to `"Copied"` for 2000 ms before reverting. No framework, no bundler. | ~40 lines |
| `katex_worker.js` | The Node worker script, shipped as package data (not under `static/` because it is not served to browsers). | ~80 lines |

`scriba/tex/__init__.py` declares the package-data manifest so `importlib.resources.files("scriba.tex")` finds all of the above (see `04-packaging.md` for `pyproject.toml` details).

### 7.1 `assets()` return logic

```python
def assets(self) -> RendererAssets:
    static = importlib.resources.files("scriba.tex") / "static"
    css: set[Path] = {Path(str(static / "scriba-tex-content.css"))}
    js: set[Path] = set()

    if self._effective_pygments_theme in ("one-light", "github-light"):
        css.add(Path(str(static / "scriba-tex-pygments-light.css")))
    elif self._effective_pygments_theme in ("one-dark", "github-dark"):
        css.add(Path(str(static / "scriba-tex-pygments-dark.css")))
    # theme == "none": no pygments CSS

    if self._enable_copy_buttons:
        js.add(Path(str(static / "scriba-tex-copy.js")))

    return RendererAssets(css_files=frozenset(css), js_files=frozenset(js))
```

`self._effective_pygments_theme` is the resolved theme after the missing-Pygments fallback in §6.2 — it may differ from the constructor argument if Pygments is absent.

## 8. Snapshot test list (30 cases)

All snapshot tests live in `tests/integration/test_tex_end_to_end.py` and use the real KaTeX worker (no mocks). Snapshot files live under `tests/integration/snapshots/`. Following `tdd-guide` methodology, these 30 cases are written BEFORE any of the port code is touched — they lock the current ojcloud behavior, then the port must reproduce them with only the class-name renames from §4.

| # | Name | Input (TeX) | Expected HTML shape |
|---|---|---|---|
| 1 | `inline_math_simple` | `The value is $x^2 + 1$.` | `<p class="scriba-tex-paragraph">The value is <span class="scriba-tex-math-inline"><span class="katex">…x²+1…</span></span>.</p>` |
| 2 | `display_math_double_dollar` | `$$\sum_{i=1}^{n} a_i$$` | `<div class="scriba-tex-math-display"><span class="katex-display">…</span></div>` |
| 3 | `display_math_triple_dollar` | `$$$\sum_{i=1}^{n} a_i$$$` | Identical HTML to #2 — triple-dollar normalizes to display. |
| 4 | `math_with_macros` | `$\RR$` with `katex_macros={"\\RR": "\\mathbb{R}"}` | `<span class="scriba-tex-math-inline">` containing KaTeX-rendered blackboard-bold R. |
| 5 | `escaped_dollar_literal` | `The price is \$5.` | `<p class="scriba-tex-paragraph">The price is $5.</p>` — no math, literal dollar, no escaping artifacts. |
| 6 | `textbf_in_textit` | `\textit{\textbf{A}}` | `<em><strong>A</strong></em>` |
| 7 | `sout_and_underline` | `\sout{\underline{A}}` | `<s><u>A</u></s>` |
| 8 | `all_nine_sizes` | `\tiny a \scriptsize b \small c \normalsize d \large e \Large f \LARGE g \huge h \Huge i` | Nine consecutive `<span class="scriba-tex-size-…">…</span>` spans in order. |
| 9 | `section_with_slug` | `\section{My Section}` | `<h2 id="my-section" class="scriba-tex-heading scriba-tex-heading-2">My Section</h2>` |
| 10 | `duplicate_section_ids` | `\section{A}\section{A}\section{A}` | Three `<h2>` elements with `id="a"`, `id="a-2"`, `id="a-3"`. |
| 11 | `itemize_simple` | `\begin{itemize}\item A\item B\end{itemize}` | `<ul class="scriba-tex-list scriba-tex-list-unordered"><li class="scriba-tex-list-item">A</li><li class="scriba-tex-list-item">B</li></ul>` |
| 12 | `enumerate_nested_in_itemize` | `\begin{itemize}\item A\begin{enumerate}\item x\item y\end{enumerate}\end{itemize}` | `<ul>` with one `<li>` containing `A` followed by a nested `<ol>` with two `<li>`. |
| 13 | `lstlisting_cpp` | `\begin{lstlisting}[language=cpp]int main(){return 0;}\end{lstlisting}` | `<div class="scriba-tex-code-block" data-language="cpp" data-code="…">` + Pygments `<div class="highlight">` + static `<button class="scriba-tex-copy-btn">`. |
| 14 | `lstlisting_unknown_language` | `\begin{lstlisting}[language=xyz]hello\end{lstlisting}` | Plain-code fallback: `<pre class="scriba-tex-code-plain">`, no `.highlight`, still has copy button and `data-code`. |
| 15 | `lstlisting_python` | `\begin{lstlisting}[language=python]def f(): pass\end{lstlisting}` | Pygments highlighted, `data-language="python"`. |
| 16 | `lstlisting_java` | `\begin{lstlisting}[language=java]class A{}\end{lstlisting}` | Pygments highlighted, `data-language="java"`. |
| 17 | `lstlisting_theme_none` | Same as #13 but renderer constructed with `pygments_theme="none"` | Plain-code fallback regardless of `[language=cpp]`. `assets().css_files` omits any pygments CSS. |
| 18 | `tabular_hlines_and_borders` | `\begin{tabular}{\|l\|c\|r\|}\hline A&B&C\\\hline\end{tabular}` | One `<tr>` with three `<td>` carrying `scriba-tex-align-{left,center,right}` + `scriba-tex-border-top` + `scriba-tex-border-bottom` + appropriate left/right borders from the column spec. |
| 19 | `tabular_multicolumn` | `\begin{tabular}{\|l\|l\|l\|}\multicolumn{2}{\|c\|}{Header} & X\\\end{tabular}` | First `<td colspan="2" class="scriba-tex-table-cell scriba-tex-align-center scriba-tex-border-left scriba-tex-border-right">Header</td>`, second normal cell. |
| 20 | `tabular_cline` | `\begin{tabular}{ll}A&B\\\cline{2-2} C&D\\\end{tabular}` | Second row's second cell has `scriba-tex-border-top`, first cell does not. |
| 21 | `includegraphics_scale` | `\includegraphics[scale=0.5]{fig.png}` | `<img … class="scriba-tex-image" style="transform: scale(0.5); transform-origin: top left" />`. |
| 22 | `includegraphics_width_cm` | `\includegraphics[width=5cm]{fig.png}` | `style="width: 189px"` (5 × 37.8 rounded). |
| 23 | `includegraphics_missing` | `\includegraphics{gone.png}` with resolver returning `None` | `<span class="scriba-tex-image-missing" data-filename="gone.png">[missing image: gone.png]</span>` |
| 24 | `epigraph_basic` | `\epigraph{Simplicity is prerequisite for reliability.}{Dijkstra}` | `<blockquote class="scriba-tex-epigraph"><p class="scriba-tex-epigraph-quote">Simplicity is prerequisite for reliability.</p><footer class="scriba-tex-epigraph-attribution">Dijkstra</footer></blockquote>` |
| 25 | `url_and_href` | `See \url{https://a.example} and \href{https://b.example}{B}.` | Two `<a class="scriba-tex-link"` elements, first with the URL as both href and text, second with `B` as text. Both carry `rel="noopener noreferrer"`. |
| 26 | `vietnamese_unicode_with_math` | `Bài toán 1: tìm $x$ sao cho $x^2 = 4$.` | Vietnamese diacritics preserved verbatim in the paragraph text, math rendered as inline KaTeX. |
| 27 | `dashes_and_quotes` | `` The quick---brown fox -- and ``this'' too. `` | Em dash `—`, en dash `–`, curly quotes `"this"`. |
| 28 | `empty_input` | `""` | Empty `<p class="scriba-tex-paragraph"></p>` — or exact `""` depending on final decision; snapshot locks whichever. Test locks: fragment is the empty string. |
| 29 | `very_long_input_10k` | Procedurally-generated 10 000-char source with mixed math, lists, and text | Snapshot asserts render completes under 500 ms on the CI machine and output contains the expected number of `<p>` elements. Test both correctness and a loose perf budget. |
| 30 | `paragraph_breaks_and_linebreak` | Multiple blank lines + `\\\\` inside a paragraph | Three `<p class="scriba-tex-paragraph">` elements separated by blank lines, with a `<br />` inside the middle one. |

Each snapshot test also asserts:

- `artifact.css_assets` matches the expected set for the theme in use.
- `artifact.js_assets == frozenset({"scriba-tex-copy.js"})` iff the test uses code blocks and `enable_copy_buttons=True`, else `frozenset()`.
- No Tailwind class (`my-`, `text-`, `bg-`, `border-`, `px-`, `py-`, `font-`, `rounded-`) appears in the output HTML. This is a `grep`-style assertion that catches regressions where a porter accidentally keeps a Tailwind class in the emitted string.

## 9. XSS test list (5 cases)

Lives in `tests/integration/test_tex_xss.py`. These tests assert that Scriba produces HTML that, after the documented consumer bleach pass from `01-architecture.md` §"Sanitization policy", contains no executable script or interactive URL handler.

| # | Name | Hostile input | Assertion on bleached output |
|---|---|---|---|
| 1 | `script_tag_in_text` | `Hello <script>alert(1)</script> world` | No `<script>` element present. Text `alert(1)` may remain as literal text. |
| 2 | `javascript_url_in_href` | `\href{javascript:alert(1)}{click}` | Resulting `<a>` has either no `href` or an `href` rewritten to `#`. Consumer bleach strips the scheme. Scriba itself MUST also refuse to emit `javascript:` hrefs from `\href` and `\url` — any href whose lowercase scheme is not in `{"http", "https", "mailto"}` is emitted as `<span class="scriba-tex-link-disabled">text</span>` instead. This is a belt-and-suspenders check independent of the consumer's sanitizer. |
| 3 | `quotes_in_includegraphics_filename` | `\includegraphics{fig".png}` (embedded quote) | The filename is HTML-attribute-escaped in the `alt` attribute (`&quot;`) and URL-encoded before being passed to `ctx.resource_resolver`. Output never contains a raw unescaped `"` inside an attribute. |
| 4 | `brace_imbalance_with_img_onerror` | `\textbf{ <img src=x onerror=alert(1)> }` | Any raw `<` in user content is HTML-escaped before being placed into the DOM, so the `<img` becomes `&lt;img`. Bleach sees escaped text, not an element. |
| 5 | `data_code_breakout` | `\begin{lstlisting}[language=cpp]" onload="alert(1)\end{lstlisting}` | The `data-code` attribute value is HTML-attribute-escaped (`&quot; onload=&quot;alert(1)`). Consumer bleach keeps `data-code` per the whitelist, and the escaped value is inert. |

Each test does:

```python
from scriba import ALLOWED_TAGS, ALLOWED_ATTRS
import bleach

artifact = renderer.render_block(block, ctx)
safe = bleach.clean(artifact.html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
assert "onerror" not in safe.lower()
assert "javascript:" not in safe.lower()
assert "<script" not in safe.lower()
```

## 10. Validator test list (6 cases)

Lives in `tests/unit/test_tex_validate.py`. Tests the pure `TexRenderer.validate()` method — no subprocess, no rendering.

| # | Name | Input | Expected result |
|---|---|---|---|
| 1 | `balanced_dollars` | `a $x$ b $$y$$ c` | `(True, None)` |
| 2 | `odd_dollar_count` | `a $x b $$y$$ c` | `(False, "unmatched $ at position 2")` |
| 3 | `unmatched_brace` | `\textbf{hello` | `(False, "unmatched { at position 8")` |
| 4 | `unknown_environment` | `\begin{unknownenv}x\end{unknownenv}` | `(False, "unknown environment 'unknownenv' at position 7")` |
| 5 | `mismatched_begin_end` | `\begin{itemize}\item A\end{enumerate}` | `(False, "\\begin{itemize} at position 0 does not match \\end{enumerate} at position 22")` |
| 6 | `empty_input` | `""` | `(True, None)` |

`validate()` is intentionally cheap — it runs the brace/command scanner but does NOT invoke the KaTeX worker. Consumers call it at submission time to reject malformed input before persisting.

## 11. File-by-file mapping from `tex_renderer.py` to `scriba/tex/*`

The port splits the 1686-line monolith into ten focused modules, all ≤ 400 lines. Every mapping below cites the line range in the current `services/tenant/backend/app/utils/tex_renderer.py` that moves to the target file. Line numbers are approximate ± 5 and will be reconciled during the actual port — what matters is the routing of functions, not exact offsets.

| Target file | Responsibility | Source lines (approx) |
|---|---|---|
| `scriba/tex/__init__.py` | Re-export `TexRenderer` and the private `_render_inline` symbol. No logic. | — |
| `scriba/tex/renderer.py` | `TexRenderer` class, constructor-time pool registration, the top-level orchestration of `render_block`: tokenize → parse → math batch → HTML emit → build `RenderArtifact`. ~400 lines. | 1–60 (imports, class header), 300–360 (orchestration entry), 1400–1500 (artifact assembly) |
| `scriba/tex/parser/math.py` | Math tokenization: `$…$`, `$$…$$`, `$$$…$$$`, escaped `\$`, inline vs display classification. Dispatches collected items to the KaTeX worker via the injected pool. Owns the internal LRU cache and the `SCRIBA_MATH_{i}` placeholder substitution. | 1100–1250 (math collect), 1190–1220 (display wrap), 150–200 (inline wrap) |
| `scriba/tex/parser/text_commands.py` | `\textbf`, `\textit`, `\emph`, `\it`, `\texttt`, `\tt`, `\underline`, `\sout`, `\textsc`, and the nine size commands. Thin dispatcher over the brace parser. | 1320–1420 |
| `scriba/tex/parser/lists.py` | `itemize`, `enumerate`, nested list handling, `\item` tokenization. | 830–930 |
| `scriba/tex/parser/tables.py` | `tabular` full implementation: column spec parsing, `\hline`, `\cline`, `\multicolumn`, `\multirow`, border class computation. The bulk of the table emission logic. | 950–1100 |
| `scriba/tex/parser/code_blocks.py` | `lstlisting` parsing, language detection, dispatch to `highlight.py`, static copy-button emission, `data-code` attribute escaping. | 650–760 |
| `scriba/tex/parser/images.py` | `\includegraphics` option parsing (`scale`, `width`, `height`, cm/in/pt conversion with 37.8 px/cm), `ctx.resource_resolver` call, missing-resource placeholder. | 140–220, 300–330 |
| `scriba/tex/parser/environments.py` | `center`, `epigraph`, `quote`, `blockquote`, `\section`/`\subsection`/`\subsubsection` including slug generation and the per-render duplicate counter. | 1250–1320, 1450–1540 |
| `scriba/tex/parser/escape.py` | Brace parser primitive (`parse_balanced_braces`), command dispatcher, placeholder manager (`SCRIBA_MATH_*`, `SCRIBA_BLOCK_*`), HTML-entity escape utility. Shared by every other parser module. | 60–140, 250–300 |
| `scriba/tex/parser/dashes_quotes.py` | `---` → em dash, `--` → en dash, `` `` `` / `''` → curly quotes, `~` → `&nbsp;`, `\\` → `<br />`, paragraph-break detection on blank lines. | 1540–1620 |
| `scriba/tex/highlight.py` | Pygments wrapper with lazy import, theme resolution, unknown-language fallback, plain-code fallback. Memoized per `(language, theme)` for the lexer+formatter pair. | 550–650 |
| `scriba/tex/validate.py` | `validate()` implementation. Pure brace/command scan, no math rendering, no I/O. | 1620–1686 |
| `scriba/tex/katex_worker.js` | Verbatim copy of `services/tenant/backend/katex_worker.js`, shipped as package data under `scriba/tex/katex_worker.js`. No edits except the `ready_signal` stderr line which already reads `"katex-worker ready"`. | (separate file) |

Every module re-imports only from `scriba.core.*` and `scriba.tex.parser.*` — never back up to `scriba.tex.renderer` — so the dependency graph is a strict DAG with `renderer.py` as the sole root.

## 12. Resolution of Wave 1 ambiguities

### 12.1 Ambiguity #2 — `render_inline_tex` auto-population

`RenderContext.render_inline_tex` is declared optional in `01-architecture.md` with the note "The Pipeline auto-populates this with a closure over the registered TexRenderer instance when one is present." Wave 1 left the mechanism unspecified. This document pins it.

**Resolution.** The `Pipeline` constructor introspects its `renderers` list at construction time. If at least one registered renderer is an instance of `scriba.tex.TexRenderer`, the `Pipeline` stores a reference to it as `self._tex_renderer`. On every call to `Pipeline.render(source, ctx)`, if `ctx.render_inline_tex is None`, the pipeline builds a replacement `RenderContext` (because `RenderContext` is frozen) via `dataclasses.replace(ctx, render_inline_tex=self._tex_renderer._render_inline)` and uses that replacement for the rest of the render. If `ctx.render_inline_tex` is already set by the consumer, the pipeline honors the consumer's callback and does not override.

The `TexRenderer._render_inline(tex: str) -> str` method accepts a bare TeX source fragment (no delimiters — always inline mode), hits the LRU cache, dispatches to the KaTeX worker on miss, and returns the HTML fragment. Concurrency is safe because `SubprocessWorker` serializes through its internal lock and the LRU cache is thread-safe.

If no `TexRenderer` is registered (e.g. a diagram-only Pipeline), `ctx.render_inline_tex` stays `None` and plugins that need it raise `RendererError("TexRenderer required for inline math in diagram steps")`.

### 12.2 Ambiguity #4 — LRU cache layers

Wave 1 did not specify whether math caching lives inside `TexRenderer` or on the consumer. This document defines **two independent layers**:

1. **Inside `TexRenderer`:** a `functools.lru_cache(maxsize=1024)` keyed on `(math_expr: str, display_mode: bool, frozen_macros_key: tuple[tuple[str, str], ...])` stores the KaTeX HTML fragment for each unique math expression. This layer amortizes repeated math across multiple `render_block` calls on the same renderer instance (one process-lifetime). The cache survives across render calls and is cleared on `close()`.
2. **Outside Scriba, on the consumer:** the consumer's response cache keyed on `(SCRIBA_VERSION, tex_version, hash(source))` as documented in `01-architecture.md` §"Versioning policy". This layer amortizes entire rendered documents across HTTP requests.

The two layers do not interact. Layer 1 is per-process and bounded at 1024 entries (approximately 2 MB of HTML at typical KaTeX output sizes). Layer 2 is the consumer's problem. Consumers who do not want layer 1 construct `TexRenderer` with a `maxsize=0` override — deferred to 0.2, not configurable in 0.1.

### 12.3 Ambiguity #5 — Singleton → per-Pipeline pool migration

Wave 1 §"Thread and process model" stated that each worker process gets its own `Pipeline` and therefore its own `SubprocessWorkerPool`. The current ojcloud renderer uses a **process-global** singleton via `get_katex_worker()` in `services/tenant/backend/app/utils/katex_worker.py`. This is a real behavioral change and needs an explicit migration note.

**Ops migration for ojcloud (tenant backend).**

1. **Before.** `services/tenant/backend/app/utils/katex_worker.py` exposes a module-level `_worker` variable and `get_katex_worker()` returns a lazily-spawned singleton. Because gunicorn uses `preload_app=False` by default, each gunicorn worker process already has its own `_worker` — so the singleton is effectively per-process today. Scriba preserves this property, just makes it explicit.
2. **After.** `create_app()` in the Flask factory constructs one `Pipeline` with one `SubprocessWorkerPool` and one registered `TexRenderer`. The `Pipeline` is stored on `app.extensions["scriba"]`. Each gunicorn worker process runs `create_app()` at boot and thus spawns exactly one KaTeX subprocess. The existing `_max_requests = 50_000` rollover is preserved via the `katex_worker_max_requests` kwarg on `TexRenderer`.
3. **RAM budget.** Per gunicorn worker: ~50 MB for Node + KaTeX (current measurement), plus ~10 MB for the Python process's share of Scriba itself. With the typical ojcloud production config of 4 gunicorn workers per tenant pod, baseline RAM is ~240 MB per pod. This matches the current tenant backend's measured baseline; the migration is net-neutral on RAM.
4. **Shutdown.** The Flask teardown hook calls `app.extensions["scriba"].close()`, which iterates every registered renderer calling `close()`, then closes the `SubprocessWorkerPool`, which SIGTERMs every spawned worker and waits up to 2 seconds before SIGKILL. This mirrors the current `atexit` handler in `katex_worker.py` but runs on app shutdown rather than interpreter exit, making graceful reloads under gunicorn's `--reload` flag work correctly.
5. **Testing.** Integration tests instantiate one `Pipeline` per test module via a pytest fixture scoped at `module` level; the fixture's teardown calls `pipeline.close()`. Test isolation is achieved by resetting the LRU cache between tests via `renderer._cache.cache_clear()` (private API, acceptable in tests).

This migration is fully elaborated in `05-migration.md`. This document only commits to the resolution above.

## 13. Summary of guarantees

After the port, `scriba.tex.TexRenderer` guarantees:

- Implements the `Renderer` protocol with `name = "tex"` and `version = 1`.
- Emits zero Tailwind class names, zero hardcoded colors, zero hardcoded URLs.
- Emits static `<button class="scriba-tex-copy-btn">` elements for code blocks — no frontend regex injection required.
- Accepts image URLs via `ctx.resource_resolver` — no Flask/Django/FastAPI coupling.
- Uses exactly one `SubprocessWorker` named `"katex"` registered into the pool owned by the enclosing `Pipeline`.
- Passes 30 snapshot tests (§8), 5 XSS tests (§9), and 6 validator tests (§10) before any port code is merged.
- Raises only `RendererError`, `WorkerError`, or `ValidationError` from the hierarchy in `01-architecture.md` — no new top-level exception types.
- Ships CSS and JS asset basenames via `RendererAssets` and never writes paths into HTML.

If an implementation deviates from any guarantee above, the implementation is wrong — not this document.
