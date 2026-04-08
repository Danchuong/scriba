"""Pipeline — the top-level entry point for rendering a source document.

See ``docs/scriba/01-architecture.md`` §Pipeline for the full algorithm.
"""

from __future__ import annotations

from typing import List

from scriba.core.artifact import Document
from scriba.core.context import RenderContext
from scriba.core.renderer import Renderer


class Pipeline:
    """The top-level entry point. Construct one per process at startup."""

    def __init__(self, renderers: list[Renderer]) -> None:
        """Register the renderers in priority order (first wins on overlap).

        The constructor validates that every renderer satisfies the Renderer
        protocol and that renderer names are unique. It does NOT spawn any
        subprocess workers — workers are lazy-spawned on first render.
        """
        raise NotImplementedError

    def render(self, source: str, ctx: RenderContext) -> Document:
        """Render the full source to a Document.

        See ``01-architecture.md`` §Pipeline for the full 8-step algorithm.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Shut down all subprocess workers owned by this pipeline.

        After close(), render() raises ScribaError. Idempotent.
        """
        raise NotImplementedError

    def __enter__(self) -> "Pipeline":
        raise NotImplementedError

    def __exit__(self, exc_type, exc, tb) -> None:
        raise NotImplementedError
