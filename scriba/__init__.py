"""Scriba — backend renderer for Online Judge problem statements.

Public API surface. Plugins (TexRenderer, DiagramRenderer, D2Engine) live
under :mod:`scriba.tex` and :mod:`scriba.diagram` and are NOT re-exported
from this top-level module.
"""

from scriba._version import __version__, SCRIBA_VERSION
from scriba.core.artifact import Block, RenderArtifact, Document
from scriba.core.context import RenderContext, ResourceResolver
from scriba.core.renderer import Renderer, RendererAssets
from scriba.core.pipeline import Pipeline
from scriba.core.workers import SubprocessWorker, SubprocessWorkerPool
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
    "SubprocessWorker",
    "SubprocessWorkerPool",
    "ScribaError",
    "RendererError",
    "WorkerError",
    "ValidationError",
    "ALLOWED_TAGS",
    "ALLOWED_ATTRS",
]
