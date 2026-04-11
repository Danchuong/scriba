"""Core abstractions for Scriba. Re-exported from :mod:`scriba`.

The deprecated alias :class:`SubprocessWorker` is lazy-loaded via PEP 562
``__getattr__`` so that ``from scriba.core import Pipeline`` does not emit
a ``DeprecationWarning`` for consumers who never touch the legacy name.
See ``STABILITY.md``.
"""

from scriba.core.artifact import Block, CollectedWarning, Document, RenderArtifact
from scriba.core.context import RenderContext, ResourceResolver
from scriba.core.renderer import Renderer, RendererAssets
from scriba.core.pipeline import Pipeline
from scriba.core.workers import (
    OneShotSubprocessWorker,
    PersistentSubprocessWorker,
    SubprocessWorkerPool,
    Worker,
)
from scriba.core.errors import (
    ScribaError,
    RendererError,
    WorkerError,
    ScribaRuntimeError,
    ValidationError,
)

__all__ = [
    "Block",
    "CollectedWarning",
    "RenderArtifact",
    "Document",
    "RenderContext",
    "ResourceResolver",
    "Renderer",
    "RendererAssets",
    "Pipeline",
    "Worker",
    "SubprocessWorker",
    "PersistentSubprocessWorker",
    "OneShotSubprocessWorker",
    "SubprocessWorkerPool",
    "ScribaError",
    "RendererError",
    "WorkerError",
    "ScribaRuntimeError",
    "ValidationError",
]


def __getattr__(name: str):  # PEP 562 lazy attribute access
    """Lazy-load deprecated names so package import stays warning-free.

    Accessing :data:`SubprocessWorker` via this module emits a
    :class:`DeprecationWarning` for callers outside the ``scriba`` package.
    """
    if name == "SubprocessWorker":
        import sys
        import warnings

        caller_module = ""
        try:
            caller_module = sys._getframe(1).f_globals.get("__name__", "")
        except ValueError:  # pragma: no cover - defensive
            caller_module = ""

        is_internal = caller_module == "scriba" or caller_module.startswith(
            "scriba."
        )
        if not is_internal:
            warnings.warn(
                "SubprocessWorker is a deprecated alias for "
                "PersistentSubprocessWorker and will be removed in 0.2.0. "
                "Import PersistentSubprocessWorker instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return PersistentSubprocessWorker
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )
