"""RenderContext dataclass and ResourceResolver Protocol.

See ``docs/scriba/01-architecture.md`` §RenderContext for the locked fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Mapping, Protocol


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
