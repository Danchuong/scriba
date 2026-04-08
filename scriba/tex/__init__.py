"""TeX plugin for Scriba. Exports :class:`TexRenderer`."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from scriba.tex.renderer import TexRenderer

if TYPE_CHECKING:
    from scriba.core.context import RenderContext
    from scriba.core.renderer import Renderer


def tex_inline_provider(
    ctx: "RenderContext", renderers: list["Renderer"]
) -> "RenderContext":
    """Explicit context provider that wires ``ctx.render_inline_tex`` when
    a :class:`TexRenderer` is registered with the pipeline.

    Callers who opt out of :class:`Pipeline`'s default providers can pass
    this to ``context_providers=[tex_inline_provider]`` to get the same
    behaviour without relying on duck typing.
    """
    if ctx.render_inline_tex is not None:
        return ctx
    for r in renderers:
        if isinstance(r, TexRenderer):
            inline = r._render_inline  # type: ignore[attr-defined]

            def _delegate(fragment: str, _inline=inline) -> str:
                return _inline(fragment)

            return dataclasses.replace(ctx, render_inline_tex=_delegate)
    return ctx


__all__ = ["TexRenderer", "tex_inline_provider"]
