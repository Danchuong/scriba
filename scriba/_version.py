"""Version constants for Scriba. Bumped on HTML output shape changes."""

__version__: str = "0.5.2"
"""PyPI SemVer. Bumped on every release."""

SCRIBA_VERSION: int = 2
"""Integer version of the core abstractions (Pipeline, Document, Renderer,
RenderArtifact, RenderContext). Bumped whenever the core API changes in a
way that invalidates consumer caches, independent of __version__.

Note: 0.5.2 keeps SCRIBA_VERSION = 2 because the Document dataclass shape
(html, required_css, required_js, versions, block_data, required_assets)
is unchanged since 0.1.1. Consumer caches keyed on SCRIBA_VERSION remain
valid across the 0.5.1 → 0.5.2 upgrade — 0.5.2 is a quick-win patch from
the 14-agent completeness audit (Phase 1) with no core-contract changes."""
