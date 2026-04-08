"""Pipeline — the top-level entry point for rendering a source document.

See ``docs/scriba/01-architecture.md`` §Pipeline for the full algorithm.
"""

from __future__ import annotations

import dataclasses
import html as _html
from typing import Callable

from scriba._version import SCRIBA_VERSION
from scriba.core.artifact import Block, Document, RenderArtifact
from scriba.core.context import RenderContext
from scriba.core.errors import ScribaError, ValidationError
from scriba.core.renderer import Renderer

_PLACEHOLDER_FMT = "\x00SCRIBA_BLOCK_{i}\x00"


class Pipeline:
    """The top-level entry point. Construct one per process at startup."""

    def __init__(self, renderers: list[Renderer]) -> None:
        if not renderers:
            raise ValueError("Pipeline requires at least one renderer")
        # Verify uniqueness of renderer names.
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
        self._closed = False

    # ----- helpers -----

    def _find_tex_renderer(self) -> Renderer | None:
        try:
            from scriba.tex import TexRenderer  # late import: avoid cycle
        except Exception:
            return None
        for r in self._renderers:
            if isinstance(r, TexRenderer):
                return r
        return None

    def _make_inline_tex(
        self, tex_renderer: Renderer
    ) -> Callable[[str], str]:
        """Build the ``ctx.render_inline_tex`` callable closing over the
        registered TexRenderer.

        Sub-phase 2b stub: returns input unchanged. The diagram plugin
        (sub-phase 7+) will implement true inline TeX rendering. The wiring
        and observability are what 2b tests assert.
        """
        # Try to use the renderer's own _render_inline if it exists.
        inline = getattr(tex_renderer, "_render_inline", None)
        if callable(inline):
            def _delegate(fragment: str) -> str:
                return inline(fragment)
            return _delegate

        def _stub(fragment: str) -> str:
            return fragment

        return _stub

    def _prepare_ctx(self, ctx: RenderContext) -> RenderContext:
        if ctx.render_inline_tex is not None:
            return ctx
        tex = self._find_tex_renderer()
        if tex is None:
            return ctx
        return dataclasses.replace(
            ctx, render_inline_tex=self._make_inline_tex(tex)
        )

    # ----- main entry -----

    def render(self, source: str, ctx: RenderContext) -> Document:
        if self._closed:
            raise ScribaError("Pipeline is closed")

        # NUL-byte rejection: placeholders use \x00 sentinels.
        nul_pos = source.find("\x00")
        if nul_pos != -1:
            raise ValidationError(
                "source contains NUL byte (reserved for placeholders)",
                position=nul_pos,
            )

        ctx = self._prepare_ctx(ctx)

        # 1. Detect blocks per renderer.
        all_blocks: list[tuple[Block, int, Renderer]] = []
        for idx, renderer in enumerate(self._renderers):
            blocks = renderer.detect(source) or []
            for b in blocks:
                all_blocks.append((b, idx, renderer))

        # 2. Resolve overlap: sort by (start, renderer-priority), keep first.
        all_blocks.sort(key=lambda t: (t[0].start, t[1]))
        accepted: list[tuple[Block, Renderer]] = []
        last_end = -1
        for block, _idx, renderer in all_blocks:
            if block.start < last_end:
                continue  # overlap with already-kept block; drop
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

        # 6. Aggregate assets: union of artifact assets PLUS each renderer's
        #    always-on assets() declaration.
        css_set: set[str] = set()
        js_set: set[str] = set()
        for artifact in artifacts:
            css_set.update(artifact.css_assets)
            js_set.update(artifact.js_assets)
        for renderer in self._renderers:
            assets = renderer.assets()
            for path in assets.css_files:
                css_set.add(getattr(path, "name", str(path)))
            for path in assets.js_files:
                js_set.add(getattr(path, "name", str(path)))

        # 7. Versions.
        versions: dict[str, int] = {"core": SCRIBA_VERSION}
        for renderer in self._renderers:
            versions[renderer.name] = int(renderer.version)

        # 8. Build Document.
        return Document(
            html=rendered_html,
            required_css=frozenset(css_set),
            required_js=frozenset(js_set),
            versions=versions,
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
