"""Version constants for Scriba. Bumped on HTML output shape changes."""

__version__: str = "0.14.0"
"""PyPI SemVer. Bumped on every release."""

SCRIBA_VERSION: int = 3
"""Integer version of the core abstractions (Pipeline, Document, Renderer,
RenderArtifact, RenderContext). Bumped whenever the core API changes in a
way that invalidates consumer caches, independent of __version__.

Note: 0.6.0 keeps SCRIBA_VERSION = 3 (bumped 2→3 in 0.6.0-alpha1). The
``Document`` dataclass gained a new ``warnings: tuple[CollectedWarning, ...]``
field (RFC-002) and the Tree/Graph/Plane2D primitives gained structural
mutation APIs (RFC-001). The additions are backward-compatible at the read
side, but consumer caches keyed on primitive rendered output MUST invalidate
because new states (``hidden``) and new edge parsing (3-tuple weighted)
produce strictly different SVG. This is the first SCRIBA_VERSION break
since v0.1.1."""
