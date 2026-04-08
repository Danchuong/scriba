# Changelog

## 0.1.0-alpha (2026-04-08)

First alpha release. TeX plugin port from ojcloud complete; diagram plugin
(0.2+) reserved.

### Added
- `scriba.core.Pipeline` — plugin orchestration with detect-then-render-with-placeholders
- `scriba.core.SubprocessWorkerPool` / `SubprocessWorker` — generalized persistent/per-call subprocess management, ported and generalized from ojcloud's katex_worker.py
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
