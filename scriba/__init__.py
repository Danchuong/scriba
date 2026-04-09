"""Scriba — backend renderer for LaTeX problem statements and CP editorial animations.

Public API surface. Plugins (TexRenderer, AnimationRenderer) live under
:mod:`scriba.tex` and :mod:`scriba.animation` and are NOT re-exported from
this top-level module.
"""

from scriba._version import __version__, SCRIBA_VERSION
from scriba.core.artifact import Block, RenderArtifact, Document
from scriba.core.context import RenderContext, ResourceResolver
from scriba.core.renderer import Renderer, RendererAssets
from scriba.core.pipeline import Pipeline
from scriba.core.workers import (
    OneShotSubprocessWorker,
    PersistentSubprocessWorker,
    SubprocessWorker,
    SubprocessWorkerPool,
    Worker,
)
from scriba.core.errors import (
    ScribaError,
    RendererError,
    WorkerError,
    ValidationError,
)
from scriba.sanitize.whitelist import ALLOWED_TAGS, ALLOWED_ATTRS

__all__ = [
    "__version__",
    "SCRIBA_VERSION",
    "Block",
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
    "ValidationError",
    "ALLOWED_TAGS",
    "ALLOWED_ATTRS",
]
