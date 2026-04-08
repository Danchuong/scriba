"""Pipeline — the top-level entry point for rendering a source document.

See ``docs/scriba/01-architecture.md`` §Pipeline for the full algorithm.

Overlap semantics
-----------------
When two renderers detect blocks that overlap, the Pipeline keeps the
block whose ``(start, renderer.priority, renderer-list-index)`` tuple
sorts first. Lower ``priority`` wins; ties are broken by the order the
renderer was passed to :class:`Pipeline`.
"""

from __future__ import annotations

import dataclasses
import html as _html
from pathlib import Path
from typing import Any, Callable

from scriba._version import SCRIBA_VERSION
from scriba.core.artifact import Block, Document, RenderArtifact
from scriba.core.context import RenderContext
from scriba.core.errors import ScribaError, ValidationError
from scriba.core.renderer import Renderer

_PLACEHOLDER_FMT = "\x00SCRIBA_BLOCK_{i}\x00"

ContextProvider = Callable[[RenderContext, list[Renderer]], RenderContext]


def _default_tex_inline_provider(
    ctx: RenderContext, renderers: list[Renderer]
) -> RenderContext:
    """Built-in provider that wires ``ctx.render_inline_tex`` when a
    TeX-flavored renderer is present.

    Detection is duck-typed on ``renderer.name == "tex"`` and the presence
    of a callable ``_render_inline`` attribute, so the core package never
    imports :mod:`scriba.tex`.
    """
    if ctx.render_inline_tex is not None:
        return ctx
    for r in renderers:
        if getattr(r, "name", None) != "tex":
            continue
        inline = getattr(r, "_render_inline", None)
        if not callable(inline):
            continue

        def _delegate(fragment: str, _inline=inline) -> str:
            return _inline(fragment)

        return dataclasses.replace(ctx, render_inline_tex=_delegate)
    return ctx


_DEFAULT_CONTEXT_PROVIDERS: tuple[ContextProvider, ...] = (
    _default_tex_inline_provider,
)


class Pipeline:
    """The top-level entry point. Construct one per process at startup."""

    def __init__(
        self,
        renderers: list[Renderer],
        *,
        context_providers: list[ContextProvider] | None = None,
    ) -> None:
        if not renderers:
            raise ValueError("Pipeline requires at least one renderer")
        seen: set[str] = set()
        for r in renderers:
            name = getattr(r, "name", None)
            if not isinstance(name, str):
                raise TypeError(
                    f"renderer {r!r} is missing a string `name` attribute"
                )
            if name in seen:
                raise ValueError(f"duplicate renderer name: {name!r}")
            seen.add(name)
        self._renderers: list[Renderer] = list(renderers)
        self._context_providers: tuple[ContextProvider, ...] = (
            tuple(context_providers)
            if context_providers is not None
            else _DEFAULT_CONTEXT_PROVIDERS
        )
        self._closed = False

    # ----- helpers -----

    def _prepare_ctx(self, ctx: RenderContext) -> RenderContext:
        for provider in self._context_providers:
            ctx = provider(ctx, self._renderers)
        return ctx

    # ----- main entry -----

    def render(self, source: str, ctx: RenderContext) -> Document:
        if self._closed:
            raise ScribaError("Pipeline is closed")

        nul_pos = source.find("\x00")
        if nul_pos != -1:
            raise ValidationError(
                "source contains NUL byte (reserved for placeholders)",
                position=nul_pos,
            )

        ctx = self._prepare_ctx(ctx)

        # 1. Detect blocks per renderer.
        all_blocks: list[tuple[Block, int, int, Renderer]] = []
        for idx, renderer in enumerate(self._renderers):
            priority = int(getattr(renderer, "priority", 100))
            blocks = renderer.detect(source) or []
            for b in blocks:
                all_blocks.append((b, priority, idx, renderer))

        # 2. Resolve overlap: sort by (start, priority, list-index).
        all_blocks.sort(key=lambda t: (t[0].start, t[1], t[2]))
        accepted: list[tuple[Block, Renderer]] = []
        last_end = -1
        for block, _pri, _idx, renderer in all_blocks:
            if block.start < last_end:
                continue
            accepted.append((block, renderer))
            last_end = block.end

        # 3. Build output buffer with placeholders for accepted blocks.
        out_parts: list[str] = []
        cursor = 0
        for i, (block, _r) in enumerate(accepted):
            if block.start > cursor:
                out_parts.append(_html.escape(source[cursor:block.start]))
            out_parts.append(_PLACEHOLDER_FMT.format(i=i))
            cursor = block.end
        if cursor < len(source):
            out_parts.append(_html.escape(source[cursor:]))
        scaffold = "".join(out_parts)

        # 4. Render each accepted block.
        artifacts: list[RenderArtifact] = []
        for block, renderer in accepted:
            artifact = renderer.render_block(block, ctx)
            artifacts.append(artifact)

        # 5. Substitute placeholders.
        rendered_html = scaffold
        for i, artifact in enumerate(artifacts):
            placeholder = _PLACEHOLDER_FMT.format(i=i)
            rendered_html = rendered_html.replace(placeholder, artifact.html)

        # 6. Aggregate assets, namespaced by renderer name to avoid
        #    basename collisions between plugins.
        css_set: set[str] = set()
        js_set: set[str] = set()
        asset_paths: dict[str, Path] = {}
        # Artifacts still return bare basenames on their asset frozensets
        # (backwards compatible). We namespace them by the owning renderer.
        for artifact, (_block, renderer) in zip(artifacts, accepted):
            ns = getattr(renderer, "name", "unknown")
            for basename in artifact.css_assets:
                css_set.add(f"{ns}/{basename}")
            for basename in artifact.js_assets:
                js_set.add(f"{ns}/{basename}")
        for renderer in self._renderers:
            ns = getattr(renderer, "name", "unknown")
            assets = renderer.assets()
            for path in assets.css_files:
                basename = getattr(path, "name", str(path))
                key = f"{ns}/{basename}"
                css_set.add(key)
                asset_paths[key] = path if isinstance(path, Path) else Path(str(path))
            for path in assets.js_files:
                basename = getattr(path, "name", str(path))
                key = f"{ns}/{basename}"
                js_set.add(key)
                asset_paths[key] = path if isinstance(path, Path) else Path(str(path))

        # 7. Aggregate public block_data.
        block_data: dict[str, Any] = {}
        for artifact in artifacts:
            if artifact.block_id and artifact.data is not None:
                block_data[artifact.block_id] = artifact.data

        # 8. Versions.
        versions: dict[str, int] = {"core": SCRIBA_VERSION}
        for renderer in self._renderers:
            versions[renderer.name] = int(renderer.version)

        # 9. Build Document.
        return Document(
            html=rendered_html,
            required_css=frozenset(css_set),
            required_js=frozenset(js_set),
            versions=versions,
            block_data=block_data,
            required_assets=asset_paths,
        )

    def close(self) -> None:
        """Shut down all renderers owned by this pipeline. Idempotent."""
        if self._closed:
            return
        self._closed = True
        for renderer in self._renderers:
            close = getattr(renderer, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    def __enter__(self) -> "Pipeline":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
