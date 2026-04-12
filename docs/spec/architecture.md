# 01 — Architecture

## Purpose of this document

This document is a **contract**, not a proposal. Every class name, dataclass field, protocol method signature, and constant named here is locked. Wave 2 documents (`02-tex-plugin.md`, `03-diagram-plugin.md`, `04-packaging.md`) and all implementation work must bind to these names verbatim. If a later document introduces a new public name, it must not contradict anything defined here.

## Package layout

```
scriba/
├── pyproject.toml                      # Project metadata, deps, entry points.            ~80 lines
├── README.md                           # Short overview, link to docs/scriba/.            ~100 lines
├── LICENSE                             # MIT.                                             single file
├── scriba/
│   ├── __init__.py                     # Public API surface (see §6).                     ~60 lines
│   ├── _version.py                     # __version__, SCRIBA_VERSION.                     ~10 lines
│   ├── core/
│   │   ├── __init__.py                 # Re-exports core symbols for scriba.__init__.     ~30 lines
│   │   ├── artifact.py                 # Block, RenderArtifact, Document dataclasses.     ~120 lines
│   │   ├── context.py                  # RenderContext dataclass, ResourceResolver.       ~120 lines
│   │   ├── renderer.py                 # Renderer and RendererAssets protocols.           ~100 lines
│   │   ├── pipeline.py                 # Pipeline class (detect/render/stitch).           ~280 lines
│   │   ├── workers.py                  # SubprocessWorker, SubprocessWorkerPool.          ~380 lines
│   │   └── errors.py                   # ScribaError hierarchy.                           ~60 lines
│   ├── tex/
│   │   ├── __init__.py                 # Exports TexRenderer and tex-plugin symbols.      ~20 lines
│   │   ├── renderer.py                 # TexRenderer implementation.                      ~600 lines
│   │   ├── parser.py                   # Brace/command/environment parser primitives.    ~400 lines
│   │   ├── math.py                     # KaTeX batching, macro handling.                  ~200 lines
│   │   ├── highlight.py                # Pygments integration, language detection.       ~250 lines
│   │   ├── copy_button.py              # Static <button> emitter for code blocks.        ~80 lines
│   │   ├── validate.py                 # validate_tex_content() helper.                   ~150 lines
│   │   ├── katex_worker.js             # Bundled Node.js worker.                          ~80 lines
│   │   └── static/
│   │       ├── scriba-tex-content.css
│   │       ├── scriba-tex-pygments-light.css
│   │       ├── scriba-tex-pygments-dark.css
│   │       └── scriba-tex-copy.js
│   ├── diagram/                        # 0.2+. Wave 2 elaborates in 03-diagram-plugin.md.
│   │   ├── __init__.py
│   │   ├── renderer.py                 # DiagramRenderer.
│   │   ├── engine.py                   # DiagramEngine protocol, D2Engine.
│   │   ├── steps.py                    # Step-annotation SVG post-processor.
│   │   └── static/
│   │       ├── scriba-diagram.css
│   │       └── scriba-diagram-steps.js
│   ├── sanitize/
│   │   ├── __init__.py                 # Exports ALLOWED_TAGS, ALLOWED_ATTRS.             ~20 lines
│   │   └── whitelist.py                # Whitelist constants.                             ~200 lines
│   └── py.typed                        # PEP 561 marker.                                  empty
├── tests/
│   ├── unit/
│   │   ├── test_pipeline.py
│   │   ├── test_workers.py
│   │   ├── test_tex_parser.py
│   │   ├── test_tex_math.py
│   │   ├── test_tex_highlight.py
│   │   └── test_sanitize_whitelist.py
│   ├── integration/
│   │   ├── test_tex_end_to_end.py      # Real KaTeX worker subprocess.
│   │   └── snapshots/                  # HTML fixtures for regression.
│   └── conftest.py
└── examples/
    ├── minimal_flask.py
    ├── minimal_fastapi.py
    └── sample_problems/
```

Total source budget: ~3000 lines of Python + ~200 lines of vanilla JS + ~400 lines of CSS.

## Core abstractions — locked API

All symbols below live in `scriba.core` and are re-exported from `scriba`. Field names, method names, and type annotations are frozen.

### `Block`

```python
from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True)
class Block:
    """A byte range in the source document claimed by a single Renderer.

    A Block is produced by Renderer.detect() and consumed by Renderer.render_block().
    Blocks are immutable and carry enough information for the owning renderer to
    reproduce the claimed region without re-scanning the source.
    """

    start: int
    """Inclusive byte offset into the source string."""

    end: int
    """Exclusive byte offset into the source string. end > start."""

    kind: str
    """Renderer-specific tag for this block, e.g. "math.display", "tex.itemize",
    "diagram.d2". Used by the owning renderer to dispatch internally. Must not
    be consulted by the Pipeline."""

    raw: str
    """The exact substring source[start:end]. Stored to avoid re-slicing on render."""

    metadata: Mapping[str, Any] | None = None
    """Optional opaque data attached by detect() for use by render_block(),
    e.g. parsed arguments, detected language. Must be hashable-friendly if
    the caller wants to cache on it, but the Pipeline does not hash it."""
```

### `RenderArtifact`

```python
@dataclass(frozen=True)
class RenderArtifact:
    """The return value of Renderer.render_block().

    Carries an HTML fragment plus the CSS/JS asset filenames the fragment requires.
    Asset filenames are basenames only (e.g. "scriba-tex-content.css"), never paths.
    The consumer resolves each filename to an on-disk location via
    importlib.resources.files("scriba.<plugin>") / "static" / name.
    """

    html: str
    """Rendered HTML fragment. Not sanitized, not wrapped in an outer element
    unless the renderer chose to wrap. May contain data-* attributes that must
    survive consumer sanitization."""

    css_assets: frozenset[str]
    """Filenames (basenames) of CSS files this fragment depends on."""

    js_assets: frozenset[str]
    """Filenames (basenames) of JS files this fragment depends on."""

    inline_data: Mapping[str, Any] | None = None
    """Optional plugin-private data returned to the Pipeline but not exposed
    on the final Document. Reserved for future use (e.g. diagram step counts
    used by the pipeline to validate cross-references). Default None."""
```

### `Document`

```python
from pathlib import Path

@dataclass(frozen=True)
class Document:
    """The aggregated result of Pipeline.render().

    This is the only object consumers see. Everything they need to serve the
    rendered fragment is on this dataclass.
    """

    html: str
    """Complete HTML fragment. Not sanitized."""

    required_css: frozenset[str]
    """Namespaced CSS asset keys of the form ``"<renderer>/<basename>"``
    (e.g. ``"tex/scriba-tex-content.css"``). Union of all css_assets
    produced by every RenderArtifact during this render, plus each
    plugin's always-on CSS declared via Renderer.assets(). Keys are the
    stable contract — see the §Asset namespace format section below."""

    required_js: frozenset[str]
    """Namespaced JS asset keys of the form ``"<renderer>/<basename>"``
    (e.g. ``"tex/scriba-tex-content.js"``). Union of all js_assets
    produced by every RenderArtifact during this render, plus each
    plugin's always-on JS declared via Renderer.assets()."""

    versions: Mapping[str, int]
    """Mapping of plugin-name -> integer version. Always contains the key
    "core" (value == SCRIBA_VERSION) and one key per Renderer in the
    Pipeline (keyed on Renderer.name). Consumers cache keyed on this
    mapping plus a hash of the source."""

    block_data: Mapping[str, Any] = field(default_factory=dict)
    """Public per-block data payloads, keyed by ``RenderArtifact.block_id``.
    Populated from every RenderArtifact that carries both a ``block_id``
    and a non-None ``data`` mapping. Added in **v0.1.1**. Empty mapping
    when no artifact exposes block-level data."""

    required_assets: Mapping[str, Path] = field(default_factory=dict)
    """Resolved filesystem paths for every namespaced asset key that
    appears in :attr:`required_css` or :attr:`required_js`. Keys match
    those sets exactly (i.e. ``"<renderer>/<basename>"``). Values are
    absolute :class:`pathlib.Path` instances produced via
    :mod:`importlib.resources`. Added in **v0.1.1**. Consumers use this
    map when they want a direct disk path rather than resolving the
    basename themselves."""
```

#### Asset namespace format

`Document.required_css`, `Document.required_js`, and the keys of
`Document.required_assets` all use the form:

```text
"<renderer>/<basename>"
```

Where:

* `<renderer>` is the owning plugin's stable `Renderer.name` attribute
  (for example `tex`, `diagram`, `animation`). This is the same string
  used as the key in `Document.versions`.
* `<basename>` is a plain filename with no directory components
  (e.g. `scriba-tex-content.css`, `katex.min.js`).
* The separator is a literal forward slash (`/`) and never changes.

This format lets two renderers ship assets with colliding basenames
without clobbering one another, and it gives consumers a way to map any
key in `required_css` / `required_js` back to the renderer that produced
it. The namespace was introduced in **v0.1.1** as a BREAKING change and
is a **locked contract** from that release onward — renaming a renderer
or changing the separator is a MAJOR bump.

Consumer rules:

1. Do not pattern-match on the basename portion in isolation; use the
   whole namespaced key as the cache key.
2. The prefix plus separator plus basename is stable: consumers may
   split on the first `/` to recover either half.
3. A renderer whose `name` changes between releases is a BREAKING
   change, per the stability policy in `STABILITY.md`.

### `RenderContext`

```python
from typing import Any, Callable, Literal, Mapping, Protocol

class ResourceResolver(Protocol):
    """Callback that maps a referenced filename (image, attachment) to a URL.

    Called by renderers whenever source markup references an external file
    (e.g. \\includegraphics{foo.png}). Returning None means the resource is
    unavailable; the renderer will emit a placeholder.
    """

    def __call__(self, filename: str) -> str | None: ...


@dataclass(frozen=True)
class RenderContext:
    """Per-request rendering context.

    Constructed by the consumer and passed to Pipeline.render(). Immutable.
    """

    resource_resolver: ResourceResolver
    """Callback resolving referenced filenames to URLs."""

    theme: Literal["light", "dark", "auto"] = "auto"
    """Intended display theme. Affects which Pygments stylesheet the TeX
    plugin selects. "auto" means the consumer will ship both stylesheets
    and switch via [data-theme="dark"]."""

    dark_mode: bool = False
    """Legacy boolean flag. When theme == "auto", dark_mode is ignored.
    When theme == "light" or "dark", dark_mode must agree with theme.
    Retained for ergonomic consumer code that wants a plain bool."""

    metadata: Mapping[str, Any] = field(default_factory=dict)
    """Arbitrary consumer-provided data. Plugins may read it but must
    tolerate missing keys. Examples: {"problem_id": 123, "locale": "vi"}."""

    render_inline_tex: Callable[[str], str] | None = None
    """Optional TeX-rendering callback that plugins use to render LaTeX
    fragments that appear inside their own markup (e.g. per-step descriptions
    in a diagram walkthrough). The Pipeline auto-populates this with a
    closure over the registered TexRenderer instance when one is present.
    Plugins that do not need LaTeX-in-markup can ignore it."""
```

### `Renderer` protocol

```python
@runtime_checkable
class Renderer(Protocol):
    """The interface every Scriba plugin implements.

    A Renderer is stateless with respect to a single render call: detect(),
    render_block(), and assets() may be called concurrently from multiple
    threads. Renderers MAY hold immutable configuration (theme, macros,
    binary paths) set at construction time.
    """

    name: str
    """Stable plugin identifier used as the key in Document.versions and
    as the ``<renderer>`` prefix in namespaced asset keys (see
    §Asset namespace format). Examples: "tex", "diagram", "animation".
    Lowercase, no spaces, no dots."""

    version: int
    """Integer plugin version. Incremented whenever the HTML shape
    produced by this renderer changes in a way that invalidates consumer
    caches. Starts at 1."""

    priority: int
    """Integer overlap tie-breaker. When two renderers both detect blocks
    whose ranges start at the same byte offset, the renderer with the
    lower ``priority`` wins. The conventional default is **100**; the
    locked default is enforced by the Pipeline when a renderer exposes
    no ``priority`` attribute. Added in **v0.1.1**."""

    def detect(self, source: str) -> list[Block]:
        """Scan the source and return every Block this renderer claims.

        Returned Blocks MUST be non-overlapping with each other. Overlaps
        across different renderers are resolved by the Pipeline using
        renderer-list order (first wins).
        """
        ...

    def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact:
        """Render a single Block to a RenderArtifact.

        May raise RendererError. Must not mutate the block."""
        ...

    def assets(self) -> "RendererAssets":
        """Return the always-on CSS/JS asset files this renderer requires,
        regardless of whether any Block was actually detected. Called once
        per Pipeline render and unioned into Document.required_css/js."""
        ...
```

### `RendererAssets`

```python
from pathlib import Path

@dataclass(frozen=True)
class RendererAssets:
    """Declaration of files a renderer ships on disk inside its package.

    Paths are absolute locations produced via
    importlib.resources.files("scriba.<plugin>") / "static" / name. The
    Pipeline does not read these files; it only exposes the basenames on
    Document.required_css / required_js. The consumer uses the basenames
    to resolve on-disk paths via the same importlib.resources mechanism.
    """

    css_files: frozenset[Path]
    js_files: frozenset[Path]
```

### `Pipeline`

```python
class Pipeline:
    """The top-level entry point. Construct one per process at startup."""

    def __init__(self, renderers: list[Renderer]) -> None:
        """Register the renderers in priority order (first wins on overlap).

        The constructor validates that every renderer satisfies the Renderer
        protocol and that renderer names are unique. It does NOT spawn any
        subprocess workers — workers are lazy-spawned on first render.
        """

    def render(self, source: str, ctx: RenderContext) -> Document:
        """Render the full source to a Document.

        Algorithm:

        1. For each registered renderer in order, call detect(source) and
           collect all returned Blocks tagged with the owning renderer.
        2. Sort all collected blocks by (start ascending, renderer order
           ascending). Walk the sorted list left-to-right; drop any block
           whose [start, end) overlaps an already-kept block. This gives
           "first renderer wins" on conflict.
        3. Walk the source left-to-right. For each accepted block, append
           the intervening plain-text run (HTML-escaped) to an output buffer
           and append a unique placeholder token of the form
           f"\\x00SCRIBA_BLOCK_{i}\\x00" where i is the block's index in
           the accepted list.
        4. For each accepted block i, call renderer.render_block(block, ctx)
           and record the returned RenderArtifact.
        5. Replace each placeholder in the output buffer with the artifact's
           html field. Placeholder collisions are impossible because \\x00 is
           stripped from source on entry (see ValidationError below).
        6. Union every artifact.css_assets and artifact.js_assets with the
           css_files/js_files basenames from every registered renderer's
           assets() result. Produce Document.required_css / required_js.
        7. Build Document.versions as {"core": SCRIBA_VERSION, **{r.name: r.version for r in self._renderers}}.
        8. Return Document.

        Placeholder collision handling: if the input source contains any
        \\x00 byte, render() raises ValidationError(position=<first NUL offset>)
        before step 1.

        Renderer precedence: the list passed to __init__ is the priority
        list. Earlier renderers win overlap resolution.

        Thread safety: render() is safe to call concurrently from multiple
        threads on the same Pipeline instance. Subprocess workers are
        per-Pipeline and guarded internally by SubprocessWorker locks.
        """

    def close(self) -> None:
        """Shut down all subprocess workers owned by this pipeline. After
        close(), render() raises ScribaError. Idempotent."""

    def __enter__(self) -> "Pipeline": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...
```

### `SubprocessWorkerPool`

```python
class SubprocessWorker:
    """One persistent subprocess speaking JSON-line over stdin/stdout.

    Supports both Node scripts (KaTeX: `node katex_worker.js`) and native
    binaries (D2: `/usr/local/bin/d2 --watch -`). Thread-safe via an internal
    lock: concurrent callers serialize through send().
    """

    def __init__(
        self,
        name: str,
        argv: list[str],
        *,
        ready_signal: str | None = None,
        max_requests: int = 50_000,
        default_timeout: float = 10.0,
    ) -> None:
        """
        name: stable identifier, e.g. "katex" or "d2".
        argv: full process command line, e.g. ["node", "/path/to/katex_worker.js"].
        ready_signal: if not None, worker startup waits for this exact line
            on stderr before the worker is considered ready. Matches the
            current KaTeX worker which emits "katex-worker ready\\n" on stderr.
        max_requests: respawn threshold. Default 50_000 matches the existing
            KaTeXWorker._max_requests (services/tenant/backend/app/utils/katex_worker.py:46).
        default_timeout: per-request read timeout in seconds.
        """

    def send(self, request: dict, *, timeout: float | None = None) -> dict:
        """Send one JSON request, read one JSON response line.

        On BrokenPipeError / empty response / JSON decode failure, the worker
        is killed and WorkerError is raised. The next call transparently
        respawns the worker. On timeout, the worker is killed and WorkerError
        is raised with a timeout stderr capture.
        """

    def close(self) -> None:
        """Graceful shutdown. Idempotent."""


class SubprocessWorkerPool:
    """Named registry of SubprocessWorker instances, lazily spawned.

    One pool per Pipeline. Workers are keyed by name, e.g. "katex" and "d2".
    """

    def __init__(self) -> None: ...

    def register(
        self,
        name: str,
        argv: list[str],
        *,
        ready_signal: str | None = None,
        max_requests: int = 50_000,
        default_timeout: float = 10.0,
    ) -> None:
        """Register a worker spec. Does not spawn the process."""

    def get(self, name: str) -> SubprocessWorker:
        """Return the worker, spawning it on first access. Raises KeyError
        if name was not registered."""

    def close(self) -> None:
        """Close every spawned worker. Idempotent."""

    def __enter__(self) -> "SubprocessWorkerPool": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...
```

**Subprocess protocol (normative).** Every Scriba subprocess worker speaks the same newline-delimited JSON protocol: one JSON object per line on stdin is a request, exactly one JSON object per line on stdout is the response. Workers MUST emit a `ready_signal` line on stderr before reading stdin if one was declared. Crashed workers are transparently respawned on the next `send()` call. Timeouts kill the worker and raise `WorkerError` with the captured stderr on the exception.

## Exception hierarchy

```python
class ScribaError(Exception):
    """Base exception for all Scriba failures."""


class RendererError(ScribaError):
    """Raised by a Renderer when render_block() cannot produce output."""

    def __init__(self, message: str, *, renderer: str | None = None) -> None:
        super().__init__(message)
        self.renderer = renderer


class WorkerError(ScribaError):
    """Raised when a subprocess worker fails (crash, timeout, bad JSON)."""

    def __init__(self, message: str, *, stderr: str | None = None) -> None:
        super().__init__(message)
        self.stderr = stderr


class ScribaRuntimeError(ScribaError):
    """Raised when a required external runtime dependency is missing or broken.

    Typical causes: ``node`` not on PATH, or the ``katex`` npm module
    cannot be resolved by the Node.js runtime that Scriba will spawn.
    Added in **v0.1.1**. Carries an optional ``component`` attribute
    naming the failing runtime (e.g. ``"node"``, ``"katex"``).
    """

    def __init__(
        self, message: str, *, component: str | None = None
    ) -> None:
        super().__init__(message)
        self.component = component


class ValidationError(ScribaError):
    """Raised on structurally invalid input (NUL bytes, unmatched braces)."""

    def __init__(self, message: str, *, position: int | None = None) -> None:
        super().__init__(message)
        self.position = position
```

## Versioning policy

```python
# scriba/_version.py
__version__: str = "0.1.0"
"""PyPI SemVer. Bumped on every release."""

SCRIBA_VERSION: int = 1
"""Integer version of the core abstractions (Pipeline, Document, Renderer,
RenderArtifact, RenderContext). Bumped whenever the core API changes in a
way that invalidates consumer caches, independent of __version__."""
```

Each plugin exposes its own integer `version` attribute on its Renderer class (e.g. `TexRenderer.version = 1`, `DiagramRenderer.version = 1`). Any change to the HTML output shape produced by a plugin bumps that plugin's version by 1. Changes to parser internals that do not affect HTML output do not bump the version.

**Consumer cache key pattern:**

```python
import hashlib
from scriba import SCRIBA_VERSION

def cache_key(source: str, doc_versions: Mapping[str, int]) -> str:
    parts = [f"scriba={SCRIBA_VERSION}"]
    for plugin in sorted(doc_versions):
        parts.append(f"{plugin}={doc_versions[plugin]}")
    parts.append(hashlib.sha256(source.encode("utf-8")).hexdigest())
    return "|".join(parts)
```

## Public API surface

`scriba/__init__.py` — minimal, plugins live under submodules:

```python
from scriba._version import __version__, SCRIBA_VERSION
from scriba.core.artifact import Block, RenderArtifact, Document
from scriba.core.context import RenderContext, ResourceResolver
from scriba.core.renderer import Renderer, RendererAssets
from scriba.core.pipeline import Pipeline
from scriba.core.workers import (
    OneShotSubprocessWorker,
    PersistentSubprocessWorker,
    SubprocessWorkerPool,
    Worker,
)
from scriba.core.errors import (
    ScribaError,
    RendererError,
    WorkerError,
    ScribaRuntimeError,
    ValidationError,
)
from scriba.sanitize.whitelist import ALLOWED_TAGS, ALLOWED_ATTRS

__all__ = [
    "__version__",
    "SCRIBA_VERSION",
    "Block",
    "RenderArtifact",
    "Document",
    "RenderContext",
    "ResourceResolver",
    "Renderer",
    "RendererAssets",
    "Pipeline",
    "Worker",
    "SubprocessWorker",
    "PersistentSubprocessWorker",
    "OneShotSubprocessWorker",
    "SubprocessWorkerPool",
    "ScribaError",
    "RendererError",
    "WorkerError",
    "ScribaRuntimeError",
    "ValidationError",
    "ALLOWED_TAGS",
    "ALLOWED_ATTRS",
]
```

Plugins (`TexRenderer`, `DiagramRenderer`, `D2Engine`) are NOT re-exported from the top level. Consumers import them explicitly from `scriba.tex` / `scriba.diagram`. This keeps the top-level namespace stable and lets plugins add private symbols without polluting `scriba.*`.

**Worker naming.** `Worker` is the runtime-checkable protocol every worker
implementation satisfies. `PersistentSubprocessWorker` (long-lived
subprocess) and `OneShotSubprocessWorker` (fresh process per request) are
the two concrete implementations. `SubprocessWorker` remains as a
deprecated alias for `PersistentSubprocessWorker` and is lazy-loaded via
PEP 562 ``__getattr__`` so that ``import scriba`` never emits a
``DeprecationWarning`` for consumers who never touch the legacy name.
Accessing ``scriba.SubprocessWorker`` or
``from scriba.core.workers import SubprocessWorker`` from outside the
``scriba`` package emits a ``DeprecationWarning``. The alias is scheduled
for removal in 0.2.0. Added in **v0.1.1**.

**`ScribaRuntimeError`** joins the error hierarchy in **v0.1.1** and is
exported alongside the other error classes. It signals a missing or
broken external runtime dependency (for example `node` not on PATH, or
an unresolvable `katex` npm package). See §Exception hierarchy.

**Symmetric `__all__`.** Both `scriba/__init__.py.__all__` and
`scriba/core/__init__.py.__all__` export the same core symbols. The only
exceptions are the top-level-only `ALLOWED_TAGS` / `ALLOWED_ATTRS` and
`__version__` / `SCRIBA_VERSION` constants, which live in
`scriba.sanitize` and `scriba._version` respectively and are re-exported
only from `scriba/__init__.py`.

## Sanitization policy

**Rationale.** Sanitization is (a) idempotent — running bleach twice on the same HTML produces the same result — (b) expensive — a full bleach pass on a 50 KB problem statement is ~5 ms, and (c) a cross-cutting concern the consumer already handles for every other piece of HTML on the page (comments, user bios, announcements). Scriba refuses to double-sanitize. It exports the whitelist it is safe against and lets the consumer run bleach once at the edge.

**`scriba.ALLOWED_TAGS`** — the complete tag whitelist, frozen:

```python
ALLOWED_TAGS: frozenset[str] = frozenset({
    # Text formatting
    "p", "br", "strong", "b", "em", "i", "u", "s", "del", "sub", "sup", "small", "span",
    # Headings
    "h1", "h2", "h3", "h4", "h5", "h6",
    # Lists
    "ul", "ol", "li",
    # Links and media
    "a", "img",
    # Code
    "pre", "code",
    # Tables
    "table", "thead", "tbody", "tr", "th", "td",
    # Block
    "div", "blockquote", "hr", "figure", "figcaption", "footer",
    # Interactive (copy buttons, step controls)
    "button",
    # MathML (KaTeX output)
    "math", "semantics", "mrow", "mi", "mo", "mn", "ms", "mtext", "mspace",
    "msub", "msup", "msubsup", "mfrac", "msqrt", "mroot",
    "mover", "munder", "munderover",
    "mtable", "mtr", "mtd", "mstyle", "menclose", "mpadded", "mphantom", "merror",
    "annotation", "annotation-xml",
    # SVG (KaTeX + diagrams)
    "svg", "path", "line", "rect", "circle", "g", "defs", "use", "clipPath",
    "polyline", "text", "marker",
})
```

**`scriba.ALLOWED_ATTRS`** — per-tag attribute whitelist, frozen. Diagram `data-step*` attributes are explicitly listed on `div` and `figure` because the step controller reads them.

```python
ALLOWED_ATTRS: Mapping[str, frozenset[str]] = {
    "*": frozenset({"class", "id", "title", "lang", "dir", "role", "aria-hidden", "aria-label"}),
    # Per-instance inline styling. Consumer MUST pair this with a css_sanitizer
    # that restricts to transform, transform-origin, width, height only.
    "div": frozenset({
        "class", "id", "style",
        "data-step", "data-step-current", "data-step-count", "data-step-mode",
    }),
    "figure": frozenset({
        "class", "id",
        "data-step", "data-step-current", "data-step-count", "data-step-mode",
    }),
    "span": frozenset({"class", "id", "style"}),
    "a": frozenset({"href", "target", "rel", "title"}),
    "img": frozenset({"src", "alt", "width", "height", "loading", "style"}),
    "pre": frozenset({"class", "data-code", "data-language"}),
    "code": frozenset({"class", "data-language"}),
    "button": frozenset({"type", "class", "data-code", "data-step-target", "aria-label"}),
    "table": frozenset({"class"}),
    "th": frozenset({"class", "colspan", "rowspan", "scope"}),
    "td": frozenset({"class", "colspan", "rowspan"}),
    # KaTeX MathML attributes
    "math": frozenset({"xmlns", "display"}),
    "annotation": frozenset({"encoding"}),
    "annotation-xml": frozenset({"encoding"}),
    "mo": frozenset({"fence", "stretchy", "symmetric", "lspace", "rspace", "minsize", "maxsize", "accent"}),
    "mspace": frozenset({"width"}),
    "mtable": frozenset({"columnalign", "rowalign", "columnspacing", "rowspacing", "columnlines", "rowlines", "frame"}),
    "mtr": frozenset({"columnalign", "rowalign"}),
    "mtd": frozenset({"columnalign", "rowalign"}),
    "menclose": frozenset({"notation"}),
    "mstyle": frozenset({"displaystyle", "scriptlevel", "mathvariant"}),
    # SVG
    "svg": frozenset({"viewBox", "xmlns", "width", "height", "fill", "focusable", "preserveAspectRatio"}),
    "path": frozenset({"d", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "transform", "clip-path"}),
    "line": frozenset({"x1", "y1", "x2", "y2", "stroke", "stroke-width", "stroke-linecap"}),
    "rect": frozenset({"x", "y", "width", "height", "rx", "ry", "fill", "stroke", "stroke-width"}),
    "circle": frozenset({"cx", "cy", "r", "fill", "stroke", "stroke-width"}),
    "g": frozenset({"transform", "fill", "stroke", "clip-path", "data-step"}),
    "defs": frozenset(),
    "use": frozenset({"href", "xlink:href", "x", "y", "width", "height"}),
    "clipPath": frozenset({"id"}),
    "polyline": frozenset({"points", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"}),
    "text": frozenset({"x", "y", "fill", "font-size", "text-anchor", "dominant-baseline"}),
    "marker": frozenset({"id", "viewBox", "refX", "refY", "markerWidth", "markerHeight", "orient"}),
}
```

**Bleach usage example with a CSS sanitizer:**

```python
import bleach
from bleach.css_sanitizer import CSSSanitizer
from scriba import ALLOWED_TAGS, ALLOWED_ATTRS

css_sanitizer = CSSSanitizer(
    allowed_css_properties=["transform", "transform-origin", "width", "height"]
)

safe_html = bleach.clean(
    doc.html,
    tags=ALLOWED_TAGS,
    attributes=ALLOWED_ATTRS,
    css_sanitizer=css_sanitizer,
    strip=True,
)
```

## CSS variable naming convention

All visual tokens live under the `--scriba-*` namespace. Plugins never use bare colors, borders, or font sizes inside emitted HTML; they reference variables that the consumer may override. Dark mode is a single ancestor selector: `[data-theme="dark"]` (Tailwind's `.dark` convention is **not** used).

**Canonical variables (declared in `scriba-tex-content.css` as defaults):**

```css
:root {
  /* Text and background */
  --scriba-fg: #1f2328;
  --scriba-fg-muted: #656d76;
  --scriba-bg: #ffffff;
  --scriba-bg-code: #f6f8fa;
  --scriba-bg-inline-code: rgba(175, 184, 193, 0.2);

  /* Borders and lines */
  --scriba-border: #d0d7de;
  --scriba-border-strong: #8c959f;

  /* Links */
  --scriba-link: #0969da;
  --scriba-link-hover: #0550ae;

  /* Errors (KaTeX parse errors, Pygments fallback) */
  --scriba-error: #cf222e;
  --scriba-error-bg: #ffebe9;

  /* Epigraph (quote block) */
  --scriba-epigraph-border: #6b7280;

  /* Copy button */
  --scriba-copy-btn-bg: #f6f8fa;
  --scriba-copy-btn-fg: #1f2328;
  --scriba-copy-btn-bg-hover: #eaeef2;
  --scriba-copy-btn-fg-hover: #0969da;
  --scriba-copy-btn-bg-copied: #dafbe1;
  --scriba-copy-btn-fg-copied: #1a7f37;

  /* Diagram */
  --scriba-diagram-dim-opacity: 0.2;
  --scriba-diagram-transition: 220ms cubic-bezier(0.16, 1, 0.3, 1);
  --scriba-diagram-active-fill: #0969da;
  --scriba-diagram-active-stroke: #0969da;

  /* Geometry and typography */
  --scriba-radius: 6px;
  --scriba-code-font: ui-monospace, "SF Mono", "Cascadia Mono", "Roboto Mono", monospace;

  /* TeX size commands (matches \tiny … \Huge) */
  --scriba-font-size-tiny: 0.625em;
  --scriba-font-size-scriptsize: 0.75em;
  --scriba-font-size-footnotesize: 0.85em;
  --scriba-font-size-small: 0.9em;
  --scriba-font-size-normalsize: 1em;
  --scriba-font-size-large: 1.2em;
  --scriba-font-size-Large: 1.4em;
  --scriba-font-size-LARGE: 1.6em;
  --scriba-font-size-huge: 1.9em;
  --scriba-font-size-Huge: 2.3em;
}

[data-theme="dark"] {
  --scriba-fg: #e6edf3;
  --scriba-fg-muted: #7d8590;
  --scriba-bg: #0d1117;
  --scriba-bg-code: #161b22;
  --scriba-bg-inline-code: rgba(110, 118, 129, 0.4);
  --scriba-border: #30363d;
  --scriba-border-strong: #6e7681;
  --scriba-link: #2f81f7;
  --scriba-link-hover: #58a6ff;
  --scriba-error: #ff7b72;
  --scriba-error-bg: rgba(248, 81, 73, 0.15);
  --scriba-epigraph-border: #8b949e;
  --scriba-copy-btn-bg: #21262d;
  --scriba-copy-btn-fg: #e6edf3;
  --scriba-copy-btn-bg-hover: #30363d;
  --scriba-copy-btn-fg-hover: #58a6ff;
  --scriba-copy-btn-bg-copied: rgba(46, 160, 67, 0.2);
  --scriba-copy-btn-fg-copied: #56d364;
  --scriba-diagram-active-fill: #58a6ff;
  --scriba-diagram-active-stroke: #58a6ff;
}
```

Size variables exist because TeX size commands are additive and need stable ratios even when the consumer overrides the base font size. There are nine size variables to cover the full LaTeX set: `\tiny`, `\scriptsize`, `\footnotesize`, `\small`, `\normalsize`, `\large`, `\Large`, `\LARGE`, `\huge`, `\Huge` (nine sizes emit classes `scriba-tex-size-*` that reference the corresponding variable).

## Thread and process model

Scriba is thread-safe by design for synchronous web frameworks:

- **Multi-threaded WSGI** (Flask with gthread, Django with gunicorn `--threads`): one `Pipeline` instance per process, shared across all threads in that process. `Pipeline.render()` serializes concurrent subprocess I/O through `SubprocessWorker._lock`; detection and HTML stitching are lock-free.
- **Multi-worker WSGI/ASGI** (gunicorn `--workers N`, uvicorn sync workers): each worker process holds its own `Pipeline` instance and therefore its own `SubprocessWorkerPool` and its own KaTeX / D2 subprocesses. RAM cost: ~30 MB per worker for the KaTeX process plus ~15 MB for D2. Acceptable for typical N ≤ 8.
- **Lifecycle.** The `Pipeline` is constructed at app startup (Flask `before_first_request` equivalent, FastAPI `lifespan`) and closed at shutdown via `pipeline.close()` or the context manager. Subprocess workers spawn lazily on first use and respawn after 50 000 requests to bound memory, matching the current ojcloud KaTeX worker behavior (`services/tenant/backend/app/utils/katex_worker.py:46`).
- **Async.** Scriba 0.x is sync-only. An `AsyncPipeline` that uses `asyncio.subprocess` is out of scope for 0.x and will be designed under a separate ADR before 1.0.

## Environment renderers (v0.3)

Scriba v0.3 introduces two additional Renderer implementations that live alongside `TexRenderer` and consume LaTeX-native environments. They bind verbatim to every contract on this page — `Renderer` protocol, `Block`, `RenderArtifact`, `RenderContext`, `SubprocessWorkerPool`, `RendererError` — and add no new core abstractions. See [`environments.md`](environments.md) for the frozen grammar, HTML output shape, CSS class contract, and error catalog, and [`03-diagram-plugin.md`](../guides/diagram-plugin.md) / [`09-animation-plugin.md`](../guides/animation-plugin.md) for the per-plugin specs.

**Registered renderers and priority (first-wins overlap):**

```python
from scriba import Pipeline
from scriba.tex import TexRenderer
from scriba.animation import AnimationRenderer, DiagramRenderer

pipeline = Pipeline(renderers=[
    AnimationRenderer(worker_pool=pool),  # name="animation", version=1, priority=10
    DiagramRenderer(worker_pool=pool),    # name="diagram",   version=1, priority=10
    TexRenderer(worker_pool=pool),        # name="tex",       version=1, priority=100
])
```

The Pipeline's overlap resolution (sort by `(start, priority, list-index)`, keep the first, drop anything overlapping) is unchanged. Because `AnimationRenderer` and `DiagramRenderer` both run at priority `10` and carry line-anchored `^\\begin{...}$` detectors, they carve out their environment regions **before** `TexRenderer.detect()` ever sees them. Outside the carved regions, every byte of the source flows to `TexRenderer` exactly as in v0.2. Inside the regions, the TeX plugin is re-entered only through `RenderContext.render_inline_tex` to render `\narrate{...}` bodies and inline math inside command parameters — the default tex-inline provider on `Pipeline` (`scriba/core/pipeline.py` `_default_tex_inline_provider`) already wires this closure when a TeX renderer is present.

**Starlark subprocess.** `\compute{...}` blocks execute in an out-of-process Starlark worker registered on the shared `SubprocessWorkerPool` under the name `"starlark"`. The worker script follows exactly the same newline-delimited JSON protocol as `scriba/tex/katex_worker.js`: one request object per stdin line, one response object per stdout line, a `ready_signal` on stderr before the first read, transparent respawn on crash or timeout, and a `max_requests` ceiling that bounds memory. Both `AnimationRenderer` and `DiagramRenderer` obtain the worker via `worker_pool.get("starlark")` and raise `WorkerError` on any protocol failure. No plugin spawns its own subprocess machinery.

**Dataflow addition.**

```
source ──► AnimationRenderer.detect()   (priority 10)  ─┐
       ──► DiagramRenderer.detect()     (priority 10)  ─┼──► Pipeline: sort + first-wins
       ──► TexRenderer.detect()         (priority 100) ─┘
                                                         │
                                                         ▼
                                                overlap-resolved blocks
                                                         │
           ┌─────────────────────────────────────────────┤
           │                                             │
           ▼                                             ▼
   AnimationRenderer.render_block()          DiagramRenderer.render_block()
   (SceneParser → Starlark worker →          (SceneParser → Starlark worker →
    primitive layout → SVG emitter →          primitive layout → SVG emitter →
    <ol class="scriba-frames">)                <figure class="scriba-diagram">)
           │                                             │
           └──────── ctx.render_inline_tex() ◄───────────┘
                              │
                              ▼
                       TexRenderer._render_inline (KaTeX worker)
```

`DiagramRenderer` and `AnimationRenderer` always sit **before** `TexRenderer` in the list passed to `Pipeline(renderers=[...])`. The Pipeline never reorders them.

## What Wave 2 agents must bind to

`02-tex-plugin.md` and `03-diagram-plugin.md` MUST use the class names, field names, and protocol contracts defined in this file verbatim. Specifically:

- `TexRenderer` must implement the `Renderer` protocol with `name = "tex"`, `version = 1`, and return `RenderArtifact` instances whose `css_assets` and `js_assets` are frozensets of basenames matching files under `scriba/tex/static/`.
- `DiagramRenderer` must implement the `Renderer` protocol with `name = "diagram"`, `version = 1`, and its step animation must use the `data-step`, `data-step-current`, `data-step-count`, `data-step-mode` attributes already listed in `ALLOWED_ATTRS` here.
- Both plugins must use `SubprocessWorkerPool` for their external processes (KaTeX, D2) — no plugin spawns its own subprocess machinery.
- Both plugins must raise `RendererError` / `WorkerError` from this file, not define their own top-level exceptions.
- Both plugins must accept `RenderContext` as defined here, including reading `resource_resolver`, `theme`, and (for the diagram plugin) `render_inline_tex`.

Wave 2 files elaborate; they do not diverge. If a Wave 2 author believes a locked name is wrong, they must open an entry in `07-open-questions.md` rather than rename it.
