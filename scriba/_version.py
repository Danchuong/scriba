"""Version constants for Scriba. Bumped on HTML output shape changes."""

__version__: str = "0.1.1-alpha"
"""PyPI SemVer. Bumped on every release."""

SCRIBA_VERSION: int = 2
"""Integer version of the core abstractions (Pipeline, Document, Renderer,
RenderArtifact, RenderContext). Bumped whenever the core API changes in a
way that invalidates consumer caches, independent of __version__."""
