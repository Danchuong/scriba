"""TexRenderer — implements the Renderer protocol for TeX-flavored sources.

See ``docs/scriba/02-tex-plugin.md`` §Public API for the locked signature.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Mapping

from scriba.core.artifact import Block, RenderArtifact, RendererAssets
from scriba.core.context import RenderContext
from scriba.core.workers import SubprocessWorkerPool


class TexRenderer:
    """Render a TeX-flavored problem statement to a self-contained HTML fragment.

    Implements the :class:`scriba.Renderer` protocol. A ``TexRenderer``
    owns no subprocess directly; it borrows a KaTeX worker from the
    supplied :class:`SubprocessWorkerPool`.
    """

    name: str = "tex"
    version: int = 1

    def __init__(
        self,
        *,
        worker_pool: SubprocessWorkerPool,
        pygments_theme: Literal[
            "one-light", "one-dark", "github-light", "github-dark", "none"
        ] = "one-light",
        enable_copy_buttons: bool = True,
        katex_macros: Mapping[str, str] | None = None,
        katex_worker_path: str | Path | None = None,
        katex_worker_timeout: float = 10.0,
        katex_worker_max_requests: int = 50_000,
        node_executable: str = "node",
        strict_math: bool = False,
    ) -> None:
        """Configure the TeX renderer. See ``02-tex-plugin.md`` §Public API."""
        raise NotImplementedError

    def detect(self, source: str) -> list[Block]:
        """Return a single :class:`Block` covering the entire source.

        TeX is a whole-document dialect: a single block wraps everything.
        """
        raise NotImplementedError

    def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact:
        """Render the full TeX block to a :class:`RenderArtifact`."""
        raise NotImplementedError

    def assets(self) -> RendererAssets:
        """Return the always-on CSS/JS files this plugin ships."""
        raise NotImplementedError

    def validate(self, content: str) -> tuple[bool, str | None]:
        """Structural pre-check for a TeX source.

        Returns ``(True, None)`` on success or ``(False, message)`` on
        failure.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Shut down this renderer's resources. Does not close the pool."""
        raise NotImplementedError

    def __enter__(self) -> "TexRenderer":
        raise NotImplementedError

    def __exit__(self, exc_type, exc, tb) -> None:
        raise NotImplementedError
