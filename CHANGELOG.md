# Changelog

## [Unreleased]

### Changed
- Vendored KaTeX `0.16.11` into the wheel at
  `scriba/tex/vendor/katex/katex.min.js`. `pip install scriba` now works
  without a separate `npm install -g katex@0.16.11` step — only Node.js
  18+ on PATH is required. The `_probe_runtime` hook now only checks for
  `node` and that the vendored KaTeX file is loadable; if the vendored
  file fails to load that is treated as a packaging bug with a
  file-a-bug error message. Resolves open question Q32.

## 0.1.1-alpha (2026-04-08)

Phase 3 architect-review fixes. Bumps `SCRIBA_VERSION` to `2` because
`Document` gains `block_data` and `required_assets` fields and the
asset key shape changes (now namespaced as `<renderer>/<basename>`).

### Added
- `scriba.core.Worker` — runtime-checkable Protocol any worker satisfies
- `scriba.core.PersistentSubprocessWorker` — renamed from
  `SubprocessWorker` (kept as deprecated alias for one release)
- `scriba.core.OneShotSubprocessWorker` — spawns a fresh subprocess per
  call for engines that should not be kept alive
- `SubprocessWorkerPool.register(..., mode="persistent"|"oneshot")`
- `RenderArtifact.block_id` and `RenderArtifact.data` — public per-block
  payload exposed on `Document.block_data`
- `Document.block_data` — `{block_id: data}` aggregated from artifacts
- `Document.required_assets` — `{namespaced-key: Path}` map for renderer
  assets, parallel to `required_css`/`required_js`
- `Renderer.priority: int` — overlap tie-breaker (lower wins, default 100)
- `Pipeline(..., context_providers=[...])` — pluggable hooks; default
  set keeps the previous TeX inline-renderer auto-wiring
- `scriba.tex.tex_inline_provider` — explicit context provider that
  callers can pass to opt out of duck-typing detection
- `scriba.tex.parser._urls.is_safe_url` — shared URL safety check used by
  href/url and the includegraphics resolver
- `scriba.tex.parser.math.MAX_MATH_ITEMS = 500`
- `scriba.tex.renderer.MAX_SOURCE_SIZE = 1_048_576`
- New tests: oneshot worker, Worker protocol, namespaced assets,
  block_data round-trip, priority tie-breaker, math item cap, source
  size cap, four new XSS tests for href URL smuggling, image resolver
  output validation

### Changed
- **BREAKING (cache key)** `Document.required_css` / `required_js` now
  contain namespaced strings of the form `"<renderer>/<basename>"` so
  two renderers can ship files with the same basename without
  collision. Consumers should treat the strings as opaque keys; the
  basename is the part after the final `/`.
- `Pipeline.render` overlap resolution now sorts by
  `(block.start, renderer.priority, list-index)` instead of just
  `(start, list-index)`.
- `_is_safe_url` rewritten to use `urllib.parse.urlparse` after
  stripping all C0 control characters and unicode line/paragraph
  separators. Catches `JAVASCRIPT:`, `java\tscript:`, `java\u2028script:`
  and newline-smuggle payloads.
- `extract_math` raises `ValidationError` if more than `MAX_MATH_ITEMS`
  expressions are found.
- `TexRenderer.detect` raises `ValidationError` for sources larger than
  `MAX_SOURCE_SIZE` bytes.
- `TexRenderer._render_inline` and the math batch fallback now log a
  `warning` before swallowing `WorkerError`.
- `Pipeline` no longer late-imports `scriba.tex` for inline-tex wiring;
  the default context provider duck-types on `name == "tex"` and
  callable `_render_inline`. The old isinstance check is gone.
- `SubprocessWorkerPool.get(name)` typed as returning the `Worker`
  protocol instead of the concrete subprocess class.
- Cleanup paths in `PersistentSubprocessWorker` now log via the module
  logger instead of swallowing every `Exception`.
- `apply_includegraphics` validates the resolver result through
  `is_safe_url`; unsafe URLs are treated as missing images.

### Sanitization
- Downstream consumers should pair `bleach.clean(...)` with
  `bleach.css_sanitizer.CSSSanitizer` to scrub the inline `style`
  attribute on `<img class="scriba-tex-image">`. Scriba does not ship
  a sanitizer.

## 0.1.0-alpha (2026-04-08)

First alpha release. TeX plugin generalized from an earlier in-house KaTeX
worker; diagram plugin (0.2+) reserved.

### Added
- `scriba.core.Pipeline` — plugin orchestration with detect-then-render-with-placeholders
- `scriba.core.SubprocessWorkerPool` / `SubprocessWorker` — generalized persistent/per-call subprocess management, generalized from an earlier in-house KaTeX worker
- `scriba.core.{Block, RenderArtifact, Document, RenderContext, RendererAssets}` — frozen dataclasses for the plugin contract
- `scriba.core.{ScribaError, RendererError, WorkerError, ValidationError}` — exception hierarchy
- `scriba.tex.TexRenderer` — LaTeX → HTML renderer with KaTeX math, Pygments highlighting
- `scriba.tex` HTML output: all math, text commands, lists, sections, tables, lstlisting, includegraphics, epigraph, url/href with `javascript:` hardening
- `scriba.sanitize.{ALLOWED_TAGS, ALLOWED_ATTRS}` — bleach whitelist matching the output contract
- Shipped static assets: `scriba-tex-content.css`, `scriba-tex-pygments-{light,dark}.css`, `scriba-tex-copy.js`

### Contract
- `SCRIBA_VERSION = 1`, `TexRenderer.version = 1`
- HTML output namespaced under `scriba-tex-*` class prefix
- Dark mode via `[data-theme="dark"]` attribute selector (NOT `.dark` Tailwind class)
- CSS variables under `--scriba-*` namespace

### Security
- Backend does NOT sanitize output; consumers must use `bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)`
- `\href{javascript:...}` and other non-`{http,https,mailto}` schemes emit `<span class="scriba-tex-link-disabled">` instead of `<a href>`
- `data-code` attribute on `scriba-tex-code-block` is HTML-entity-escaped (no breakout)

### Dependencies
- Python 3.10+
- `pygments>=2.17,<2.20`
- Node.js 18+ and `katex@0.16.11` npm package (runtime requirement for math rendering)
- Optional: `bleach` for sanitization at consumer layer

### Testing
- 71 tests: 30 snapshot + 5 XSS + 6 validator + 9 API + 7 pipeline + 9 workers + 7 sanitize
- All snapshots manually reviewed against `docs/scriba/02-tex-plugin.md` HTML output contract

### Not included (deferred)
- `scriba.diagram` plugin with D2 engine — Phase 7+, roadmap 0.2/0.3
- `MermaidEngine` — Phase 7+, roadmap 0.4 (conditional on user demand)
- Graph/codetrace/other plugins — 0.5+
