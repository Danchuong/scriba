"""Renderer Protocol. Re-exports RendererAssets from :mod:`scriba.core.artifact`.

See ``docs/scriba/01-architecture.md`` §Renderer protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from scriba.core.artifact import Block, RenderArtifact, RendererAssets
from scriba.core.context import RenderContext

__all__ = ["Renderer", "RendererAssets"]


@runtime_checkable
class Renderer(Protocol):
    """The interface every Scriba plugin implements.

    A Renderer is stateless with respect to a single render call: detect(),
    render_block(), and assets() may be called concurrently from multiple
    threads. Renderers MAY hold immutable configuration (theme, macros,
    binary paths) set at construction time.
    """

    name: str
    """Stable plugin identifier used as the key in Document.versions."""

    version: int
    """Integer plugin version. Starts at 1."""

    priority: int
    """Tie-breaker when two renderers detect blocks starting at the same
    offset. Lower wins. Default is 100 (see Pipeline docs)."""

    def detect(self, source: str) -> list[Block]:
        """Scan the source and return every Block this renderer claims.

        Returned Blocks MUST be non-overlapping with each other.
        """
        ...

    def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact:
        """Render a single Block to a RenderArtifact.

        May raise RendererError. Must not mutate the block.
        """
        ...

    def assets(self) -> RendererAssets:
        """Return the always-on CSS/JS asset files this renderer requires."""
        ...
