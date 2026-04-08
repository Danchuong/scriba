"""DiagramRenderer — Renderer implementation for D2 (and future) blocks.

See ``docs/scriba/03-diagram-plugin.md`` §Public API.
"""

from __future__ import annotations

from typing import Literal

from scriba.core.artifact import Block, RenderArtifact, RendererAssets
from scriba.core.context import RenderContext
from scriba.core.workers import SubprocessWorkerPool
from scriba.diagram.engine import DiagramEngine


class DiagramRenderer:
    """:class:`Renderer` implementation for fenced ``d2`` code blocks.

    Holds a reference to a :class:`DiagramEngine` and to the shared
    :class:`SubprocessWorkerPool`.
    """

    name: str = "diagram"
    version: int = 1

    def __init__(
        self,
        *,
        engine: DiagramEngine,
        worker_pool: SubprocessWorkerPool,
        default_step_mode: Literal["cumulative", "exclusive"] = "cumulative",
        enable_controls: bool = True,
    ) -> None:
        """Configure the diagram renderer. See ``03-diagram-plugin.md``."""
        raise NotImplementedError

    def detect(self, source: str) -> list[Block]:
        """Return one :class:`Block` per fenced ``d2`` block in ``source``."""
        raise NotImplementedError

    def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact:
        """Render a single diagram block."""
        raise NotImplementedError

    def assets(self) -> RendererAssets:
        """Return the CSS and JS files this renderer needs at page-load time."""
        raise NotImplementedError
