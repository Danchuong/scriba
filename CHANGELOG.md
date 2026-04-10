# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-04-10 (Phase D)

### Added
- Structured error codes (`E1xxx`) with line and column information for all
  parse and render errors, replacing opaque tracebacks with actionable messages.
- HARD-TO-DISPLAY verification suite achieving 9/10 coverage across edge-case
  LaTeX constructs.
- Launch blog post and documentation site.
- Homebrew tap for CLI installation (`brew install ojcloud/tap/scriba`).

### Changed
- Error UX overhaul: every user-facing error now carries a unique `E1xxx` code,
  source location (line/col), and a human-readable suggestion.
- Development status upgraded from Alpha to Beta in PyPI classifiers.

### Fixed
- Remaining edge cases in error reporting for deeply nested LaTeX environments.

## [0.4.0] - 2026-04-09 (Phase C)

### Added
- `Plane2D` animation primitive for 2D coordinate plane visualizations.
- `MetricPlot` animation primitive for plotting algorithmic metrics over time.
- `Graph` layout mode `layout=stable` for deterministic node positioning across
  animation frames.
- `\substory` macro for composing nested editorial sub-narratives within a
  single animation timeline.
- `\fastforward` macro to skip ahead in the animation timeline, collapsing
  intermediate steps.

### Changed
- Graph renderer now supports stable layout by default when `layout=stable` is
  specified, preventing node jitter between frames.

### Fixed
- Graph layout instability when nodes are added or removed between frames.

## [0.3.0] - 2026-04-09 (Phase B)

### Added
- `scriba.diagram` plugin for rendering diagram blocks alongside TeX.
- `Grid` animation primitive for 2D grid-based visualizations (BFS/DFS grids,
  game boards).
- `Tree` animation primitive for tree structure visualizations with
  auto-layout.
- `NumberLine` animation primitive for 1D range and interval visualizations.
- `figure-embed` directive for embedding static or animated figures inline
  within editorial text.
- `Matrix` and `Heatmap` animation primitives for 2D numeric data
  visualization.
- `Stack` animation primitive for LIFO data structure visualization.

### Changed
- Animation scaffold extended to support diagram-originated primitives
  alongside TeX-originated ones.

### Fixed
- Figure embedding edge cases when mixing inline TeX math with diagram
  figures.

## [0.2.0] - 2026-04-08 (Phase A)

### Added
- Animation scaffold: `@keyframes`-based CSS animation engine for editorial
  step-by-step playback.
- `Array` animation primitive for visualizing array operations (swaps,
  highlights, pointer movement).
- `DPTable` animation primitive for dynamic programming table fill
  animations.
- `Graph` animation primitive for graph algorithm visualizations (BFS, DFS,
  shortest path).
- `\hl` (highlight) LaTeX macro for marking editorial text regions that
  synchronize with animation steps.
- `@keyframes` generation from editorial step descriptors, producing
  self-contained CSS animations without JavaScript dependencies.

### Changed
- `SCRIBA_VERSION` bumped to `3` for animation-aware `Document` shape.
- `Document` dataclass extended with animation timeline metadata.

### Fixed
- Snapshot test alignment after `Document` shape changes.

## [0.1.1-alpha] - 2026-04-08

Phase 3 architect-review fixes. Bumps `SCRIBA_VERSION` to `2` because
`Document` gains `block_data` and `required_assets` fields and the
asset key shape changes (now namespaced as `<renderer>/<basename>`).

### Added
- `scriba.core.Worker` -- runtime-checkable Protocol any worker satisfies
- `scriba.core.PersistentSubprocessWorker` -- renamed from
  `SubprocessWorker` (kept as deprecated alias for one release)
- `scriba.core.OneShotSubprocessWorker` -- spawns a fresh subprocess per
  call for engines that should not be kept alive
- `SubprocessWorkerPool.register(..., mode="persistent"|"oneshot")`
- `RenderArtifact.block_id` and `RenderArtifact.data` -- public per-block
  payload exposed on `Document.block_data`
- `Document.block_data` -- `{block_id: data}` aggregated from artifacts
- `Document.required_assets` -- `{namespaced-key: Path}` map for renderer
  assets, parallel to `required_css`/`required_js`
- `Renderer.priority: int` -- overlap tie-breaker (lower wins, default 100)
- `Pipeline(..., context_providers=[...])` -- pluggable hooks; default
  set keeps the previous TeX inline-renderer auto-wiring
- `scriba.tex.tex_inline_provider` -- explicit context provider that
  callers can pass to opt out of duck-typing detection
- `scriba.tex.parser._urls.is_safe_url` -- shared URL safety check used by
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
  two renderers can ship files with the same basename without collision.
- `Pipeline.render` overlap resolution now sorts by
  `(block.start, renderer.priority, list-index)` instead of just
  `(start, list-index)`.
- `_is_safe_url` rewritten to use `urllib.parse.urlparse` after
  stripping all C0 control characters and unicode line/paragraph
  separators.
- `extract_math` raises `ValidationError` if more than `MAX_MATH_ITEMS`
  expressions are found.
- `TexRenderer.detect` raises `ValidationError` for sources larger than
  `MAX_SOURCE_SIZE` bytes.

### Fixed
- `TexRenderer._render_inline` and the math batch fallback now log a
  `warning` before swallowing `WorkerError`.
- `Pipeline` no longer late-imports `scriba.tex` for inline-tex wiring.
- `apply_includegraphics` validates the resolver result through
  `is_safe_url`; unsafe URLs are treated as missing images.

## [0.1.0-alpha] - 2026-04-08

First alpha release. TeX plugin generalized from an earlier in-house KaTeX
worker; diagram plugin (0.2+) reserved.

### Added
- `scriba.core.Pipeline` -- plugin orchestration with
  detect-then-render-with-placeholders
- `scriba.core.SubprocessWorkerPool` / `SubprocessWorker` -- generalized
  persistent/per-call subprocess management
- `scriba.core.{Block, RenderArtifact, Document, RenderContext,
  RendererAssets}` -- frozen dataclasses for the plugin contract
- `scriba.core.{ScribaError, RendererError, WorkerError, ValidationError}`
  -- exception hierarchy
- `scriba.tex.TexRenderer` -- LaTeX to HTML renderer with KaTeX math,
  Pygments highlighting
- Shipped static assets: `scriba-tex-content.css`,
  `scriba-tex-pygments-{light,dark}.css`, `scriba-tex-copy.js`
- `scriba.sanitize.{ALLOWED_TAGS, ALLOWED_ATTRS}` -- bleach whitelist
  matching the output contract
- 71 tests: 30 snapshot + 5 XSS + 6 validator + 9 API + 7 pipeline +
  9 workers + 7 sanitize

[0.5.0]: https://github.com/ojcloud/scriba/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/ojcloud/scriba/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/ojcloud/scriba/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ojcloud/scriba/compare/v0.1.1-alpha...v0.2.0
[0.1.1-alpha]: https://github.com/ojcloud/scriba/compare/v0.1.0-alpha...v0.1.1-alpha
[0.1.0-alpha]: https://github.com/ojcloud/scriba/releases/tag/v0.1.0-alpha
