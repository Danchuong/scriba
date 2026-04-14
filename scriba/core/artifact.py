"""Frozen dataclasses for Blocks, RenderArtifacts, and Documents.

See ``docs/scriba/01-architecture.md`` §Core abstractions for the locked
field names and types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.abc import Traversable
from pathlib import Path
from typing import Any, Literal, Mapping


def traversable_to_path(t: Traversable | Path) -> Path:
    """Cast an importlib.resources Traversable to a concrete Path.

    ``importlib.resources.files()`` returns a Traversable which is not a
    ``pathlib.Path``.  For unzipped installs (the default for pip) the
    underlying object is already backed by the filesystem, so
    ``Path(str(t))`` yields a usable path.  This helper centralises that
    cast so the intent is documented and easy to find if we later need to
    switch to ``importlib.resources.as_file()`` for zipped packages.
    """
    return t if isinstance(t, Path) else Path(str(t))


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
    At the artifact level each asset is declared as a plain basename; the
    Pipeline is responsible for namespacing the name as
    ``"<renderer>/<basename>"`` before merging it into
    :attr:`Document.required_css` / :attr:`Document.required_js`. See
    ``STABILITY.md`` §Asset namespace format for the stable contract.
    """

    html: str
    """Rendered HTML fragment. Not sanitized."""

    css_assets: frozenset[str]
    """Filenames (basenames) of CSS files this fragment depends on. The
    Pipeline namespaces these as ``"<renderer>/<basename>"`` on the final
    :class:`Document`."""

    js_assets: frozenset[str]
    """Filenames (basenames) of JS files this fragment depends on. The
    Pipeline namespaces these as ``"<renderer>/<basename>"`` on the final
    :class:`Document`."""

    inline_data: Mapping[str, Any] | None = None
    """Optional plugin-private data returned to the Pipeline but not
    exposed on the final Document."""

    block_id: str | None = None
    """Stable identifier a renderer may attach to this block so downstream
    consumers can look up associated data on ``Document.block_data``."""

    data: Mapping[str, Any] | None = None
    """Optional public data payload, exposed on ``Document.block_data``
    keyed by ``block_id``. Skipped if either is missing."""


@dataclass(frozen=True)
class CollectedWarning:
    """A structured warning emitted during a render and collected on
    :class:`Document`.

    Strict mode (RFC-002) introduces a structured warning channel so that
    silent ``logger.warning(...)`` or ``warnings.warn(...)`` calls made by
    primitives and parsers can be surfaced on the aggregated
    :class:`Document` — and optionally promoted to errors when the
    consumer asks for strict rendering.

    Fields
    ------
    code:
        E-code (e.g. ``"E1462"``). Must match a key in
        :data:`scriba.animation.errors.ERROR_CATALOG` whenever possible.
    message:
        Human-readable description. Usually the same string the helper
        would have passed to ``animation_error(..., detail=...)``.
    source_line, source_col:
        Optional 1-indexed source location where the problem originated.
    primitive:
        Optional name of the primitive instance that raised the warning
        (e.g. ``"plane2d_demo"``).
    severity:
        One of ``"dangerous"``, ``"hidden"``, ``"info"``. ``"dangerous"``
        codes are the ones that may be promoted to raised errors in
        strict mode.
    """

    code: str
    message: str
    source_line: int | None = None
    source_col: int | None = None
    primitive: str | None = None
    severity: Literal["dangerous", "hidden", "info"] = "hidden"


@dataclass(frozen=True)
class Document:
    """The aggregated result of Pipeline.render().

    The only object consumers see.
    """

    html: str
    """Complete HTML fragment. Not sanitized."""

    required_css: frozenset[str]
    """Namespaced CSS asset keys of the form ``"<renderer>/<basename>"``
    (e.g. ``"tex/scriba-tex-content.css"``). Union of all css_assets
    across every RenderArtifact produced during this render, plus each
    plugin's always-on CSS. The namespace format is part of the stability
    contract — see ``STABILITY.md``."""

    required_js: frozenset[str]
    """Namespaced JS asset keys of the form ``"<renderer>/<basename>"``
    (e.g. ``"tex/scriba-tex-content.js"``). Union of all js_assets across
    every RenderArtifact produced during this render, plus each plugin's
    always-on JS. The namespace format is part of the stability contract
    — see ``STABILITY.md``."""

    versions: Mapping[str, int]
    """Mapping of plugin-name -> integer version. Always contains "core"
    and one key per Renderer in the Pipeline."""

    block_data: Mapping[str, Any] = field(default_factory=dict)
    """Public data payloads keyed by ``RenderArtifact.block_id``."""

    required_assets: Mapping[str, Path] = field(default_factory=dict)
    """Resolved filesystem paths for every namespaced asset key present in
    ``required_css`` and ``required_js``. Keys match those sets exactly."""

    warnings: tuple[CollectedWarning, ...] = ()
    """Structured warnings collected during this render.

    Populated by the strict-mode warning collector (RFC-002). Always a
    tuple — empty when nothing was collected. Callers that want to
    surface issues without failing the render can inspect this field.
    Order is insertion order. See :class:`CollectedWarning`.
    """


@dataclass(frozen=True)
class RendererAssets:
    """Declaration of files a renderer ships on disk inside its package.

    Paths are absolute locations produced via importlib.resources. The
    Pipeline does not read these files; it only exposes the basenames on
    Document.required_css / required_js.
    """

    css_files: frozenset[Path]
    js_files: frozenset[Path]
