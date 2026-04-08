"""Frozen dataclasses for Blocks, RenderArtifacts, and Documents.

See ``docs/scriba/01-architecture.md`` §Core abstractions for the locked
field names and types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class Block:
    """A byte range in the source document claimed by a single Renderer.

    A Block is produced by Renderer.detect() and consumed by
    Renderer.render_block(). Blocks are immutable and carry enough
    information for the owning renderer to reproduce the claimed region
    without re-scanning the source.
    """

    start: int
    """Inclusive byte offset into the source string."""

    end: int
    """Exclusive byte offset into the source string. end > start."""

    kind: str
    """Renderer-specific tag for this block, e.g. "math.display",
    "tex.itemize", "diagram.d2". Used by the owning renderer to dispatch
    internally. Must not be consulted by the Pipeline."""

    raw: str
    """The exact substring source[start:end]."""

    metadata: Mapping[str, Any] | None = None
    """Optional opaque data attached by detect() for use by render_block()."""


@dataclass(frozen=True)
class RenderArtifact:
    """The return value of Renderer.render_block().

    Carries an HTML fragment plus the CSS/JS asset filenames it requires.
    Asset filenames are basenames only.
    """

    html: str
    """Rendered HTML fragment. Not sanitized."""

    css_assets: frozenset[str]
    """Filenames (basenames) of CSS files this fragment depends on."""

    js_assets: frozenset[str]
    """Filenames (basenames) of JS files this fragment depends on."""

    inline_data: Mapping[str, Any] | None = None
    """Optional plugin-private data returned to the Pipeline but not
    exposed on the final Document."""


@dataclass(frozen=True)
class Document:
    """The aggregated result of Pipeline.render().

    The only object consumers see.
    """

    html: str
    """Complete HTML fragment. Not sanitized."""

    required_css: frozenset[str]
    """Union of all css_assets across all RenderArtifacts produced during
    this render, plus each plugin's always-on CSS."""

    required_js: frozenset[str]
    """Union of all js_assets across all RenderArtifacts produced during
    this render, plus each plugin's always-on JS."""

    versions: Mapping[str, int]
    """Mapping of plugin-name -> integer version. Always contains "core"
    and one key per Renderer in the Pipeline."""


@dataclass(frozen=True)
class RendererAssets:
    """Declaration of files a renderer ships on disk inside its package.

    Paths are absolute locations produced via importlib.resources. The
    Pipeline does not read these files; it only exposes the basenames on
    Document.required_css / required_js.
    """

    css_files: frozenset[Path]
    js_files: frozenset[Path]
