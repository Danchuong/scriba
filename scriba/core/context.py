"""RenderContext dataclass and ResourceResolver Protocol.

See ``docs/scriba/01-architecture.md`` §RenderContext for the locked fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Literal, Mapping, Protocol

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from scriba.core.artifact import CollectedWarning


class ResourceResolver(Protocol):
    """Callback that maps a referenced filename (image, attachment) to a URL.

    Called by renderers whenever source markup references an external file
    (e.g. ``\\includegraphics{foo.png}``). Returning ``None`` means the
    resource is unavailable; the renderer will emit a placeholder.
    """

    def __call__(self, filename: str) -> str | None: ...


@dataclass(frozen=True)
class RenderContext:
    """Per-request rendering context.

    Constructed by the consumer and passed to :meth:`Pipeline.render`.
    Immutable.
    """

    resource_resolver: ResourceResolver
    """Callback resolving referenced filenames to URLs."""

    theme: Literal["light", "dark", "auto"] = "auto"
    """Intended display theme."""

    dark_mode: bool = False
    """Legacy boolean flag."""

    metadata: Mapping[str, Any] = field(default_factory=dict)
    """Arbitrary consumer-provided data."""

    render_inline_tex: Callable[[str], str] | None = None
    """Optional TeX-rendering callback for rendering LaTeX fragments that
    appear inside plugin-owned markup (e.g. per-step descriptions)."""

    strict: bool = False
    """Strict-mode flag (RFC-002). When ``True``, dangerous warnings (see
    :mod:`scriba.animation.errors._DANGEROUS_CODES`) are promoted from
    collected :class:`CollectedWarning` entries into raised
    :class:`~scriba.core.errors.ValidationError` subclasses. Codes listed
    in :attr:`strict_except` are tolerated even when ``strict`` is set."""

    strict_except: frozenset[str] = frozenset()
    """Opt-out set of E-codes that should NOT be promoted to errors even
    when :attr:`strict` is enabled. Useful for consumers that know their
    source triggers a specific dangerous silent-fix but cannot correct
    the upstream document."""

    warnings_collector: list["CollectedWarning"] | None = None
    """Mutable list used by the strict-mode warning channel to accumulate
    :class:`CollectedWarning` entries during a single render. The
    :class:`~scriba.core.pipeline.Pipeline` replaces this with an internal
    list it owns before passing the context to renderers; consumers may
    pass their own pre-allocated list to capture warnings across a
    multi-render session."""
