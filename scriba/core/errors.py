"""Exception hierarchy for Scriba.

See ``docs/scriba/01-architecture.md`` §Exception hierarchy.
"""

from __future__ import annotations


class ScribaError(Exception):
    """Base exception for all Scriba failures."""


class RendererError(ScribaError):
    """Raised by a Renderer when render_block() cannot produce output."""

    def __init__(self, message: str, *, renderer: str | None = None) -> None:
        super().__init__(message)
        self.renderer = renderer


class WorkerError(ScribaError):
    """Raised when a subprocess worker fails (crash, timeout, bad JSON)."""

    def __init__(self, message: str, *, stderr: str | None = None) -> None:
        super().__init__(message)
        self.stderr = stderr


class ScribaRuntimeError(ScribaError):
    """Raised when a required external runtime dependency is missing or broken.

    Typical causes: ``node`` not on PATH, or the ``katex`` npm module cannot
    be resolved by the Node.js runtime that Scriba will spawn.
    """

    def __init__(self, message: str, *, component: str | None = None) -> None:
        super().__init__(message)
        self.component = component


class ValidationError(ScribaError):
    """Raised on structurally invalid input (NUL bytes, unmatched braces)."""

    def __init__(self, message: str, *, position: int | None = None) -> None:
        super().__init__(message)
        self.position = position
