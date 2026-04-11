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
import logging
import re
import secrets
import warnings
from pathlib import Path
from typing import Any, Callable

from scriba._version import SCRIBA_VERSION
from scriba.core.artifact import Block, CollectedWarning, Document, RenderArtifact
from scriba.core.context import RenderContext
from scriba.core.errors import ScribaError, ValidationError
from scriba.core.renderer import Renderer

logger = logging.getLogger(__name__)

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


def _provider_identity(provider: ContextProvider) -> str:
    """Return a human-readable identity string for a context provider."""
    module = getattr(provider, "__module__", "?")
    qualname = getattr(provider, "__qualname__", None) or getattr(
        provider, "__name__", repr(provider)
    )
    return f"{module}.{qualname}"


class Pipeline:
    """The top-level entry point. Construct one per process at startup.

    Parameters
    ----------
    renderers
        Ordered list of renderers. Must be non-empty; every renderer must
        expose a unique string ``name``.
    context_providers
        Optional override for per-request context-preparation hooks.

        * ``None`` (omitted): use the built-in defaults (currently the
          TeX-inline provider). This is the recommended setting for almost
          all consumers.
        * ``[]`` (explicit empty list): use **no** providers at all. This
          disables auto-wiring of ``ctx.render_inline_tex`` and any future
          default provider; callers that pick this are responsible for
          populating the context themselves. A ``UserWarning`` is emitted
          as a reminder.
        * A non-empty list: use exactly those providers, in order.
    """

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
        if context_providers is None:
            self._context_providers: tuple[ContextProvider, ...] = (
                _DEFAULT_CONTEXT_PROVIDERS
            )
        else:
            self._context_providers = tuple(context_providers)
            if not self._context_providers:
                # Explicit empty list: loud warning about disabled defaults.
                warnings.warn(
                    "Pipeline(context_providers=[]) disables ALL default "
                    "context providers, including TeX inline-rendering "
                    "auto-wiring. Pass context_providers=None (or omit the "
                    "argument) to keep defaults, or populate "
                    "ctx.render_inline_tex manually.",
                    UserWarning,
                    stacklevel=2,
                )
        self._closed = False

    # ----- helpers -----

    def _prepare_ctx(self, ctx: RenderContext) -> RenderContext:
        for provider in self._context_providers:
            ident = _provider_identity(provider)
            try:
                new_ctx = provider(ctx, self._renderers)
            except Exception as e:
                raise ValidationError(
                    f"context provider {ident!r} raised {type(e).__name__}: {e}",
                ) from e
            if not isinstance(new_ctx, RenderContext):
                raise ValidationError(
                    f"context provider {ident!r} returned "
                    f"{type(new_ctx).__name__} instead of RenderContext"
                )
            ctx = new_ctx
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

        # RFC-002 strict-mode wiring. Ensure there is a mutable collector
        # bound to the context so downstream renderers and primitives can
        # push structured warnings through _emit_warning. Callers may
        # have supplied their own list (e.g. to accumulate across
        # multi-render sessions); we honour that.
        if ctx.warnings_collector is None:
            internal_collector: list[CollectedWarning] = []
            ctx = dataclasses.replace(ctx, warnings_collector=internal_collector)
        else:
            internal_collector = ctx.warnings_collector

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
        #
        # Placeholder safety: we generate a fresh, unforgeable nonce per
        # render() call. Artifact HTML produced by renderer plugins cannot
        # forge the full placeholder string because it doesn't know the
        # nonce, so a naive substring match is safe against re-entry.
        nonce = secrets.token_hex(16)
        placeholder_prefix = f"\x00SCRIBA_BLOCK_{nonce}_"
        placeholder_suffix = "\x00"

        def _make_placeholder(i: int) -> str:
            return f"{placeholder_prefix}{i}{placeholder_suffix}"

        out_parts: list[str] = []
        cursor = 0
        for i, (block, _r) in enumerate(accepted):
            if block.start > cursor:
                out_parts.append(_html.escape(source[cursor:block.start]))
            out_parts.append(_make_placeholder(i))
            cursor = block.end
        if cursor < len(source):
            out_parts.append(_html.escape(source[cursor:]))
        scaffold = "".join(out_parts)

        # 4. Render each accepted block.
        artifacts: list[RenderArtifact] = []
        for block, renderer in accepted:
            try:
                artifact = renderer.render_block(block, ctx)
            except Exception as e:
                # Enrich mid-loop failures with which block crashed.
                raise type(e)(
                    f"renderer {renderer.name!r} failed on block "
                    f"kind={block.kind!r} at [{block.start}:{block.end}]: {e}"
                ) from e
            artifacts.append(artifact)

        # 5. Substitute placeholders in a single pass via regex. Using
        # re.sub with a callback guarantees each marker is replaced exactly
        # once and prevents artifact HTML that happens to contain another
        # (valid) marker from triggering a re-entry substitution.
        pattern = re.compile(
            re.escape(placeholder_prefix) + r"(\d+)" + re.escape(placeholder_suffix)
        )
        by_index: dict[int, str] = {i: a.html for i, a in enumerate(artifacts)}

        def _sub(match: re.Match[str]) -> str:
            idx = int(match.group(1))
            # Fall back to the literal match (shouldn't happen because we
            # only emit indices we know). This is belt-and-braces only.
            return by_index.get(idx, match.group(0))

        rendered_html = pattern.sub(_sub, scaffold)

        # 6. Aggregate assets, namespaced by renderer name to avoid
        #    basename collisions between plugins.
        css_set: set[str] = set()
        js_set: set[str] = set()
        asset_paths: dict[str, Path] = {}
        # Artifacts still return bare basenames on their asset frozensets
        # (backwards compatible). We namespace them by the owning renderer.
        for artifact, (_block, renderer) in zip(artifacts, accepted):
            ns = renderer.name  # __init__ guarantees this exists.
            for basename in artifact.css_assets:
                css_set.add(f"{ns}/{basename}")
            for basename in artifact.js_assets:
                js_set.add(f"{ns}/{basename}")
        for renderer in self._renderers:
            ns = renderer.name
            assets = renderer.assets()
            for path in assets.css_files:
                basename = getattr(path, "name", str(path))
                key = f"{ns}/{basename}"
                css_set.add(key)
                resolved = path if isinstance(path, Path) else Path(str(path))
                if key in asset_paths and asset_paths[key] != resolved:
                    warnings.warn(
                        f"asset path collision for {key!r}: keeping "
                        f"{asset_paths[key]!s}, ignoring {resolved!s}",
                        UserWarning,
                        stacklevel=2,
                    )
                else:
                    asset_paths[key] = resolved
            for path in assets.js_files:
                basename = getattr(path, "name", str(path))
                key = f"{ns}/{basename}"
                js_set.add(key)
                resolved = path if isinstance(path, Path) else Path(str(path))
                if key in asset_paths and asset_paths[key] != resolved:
                    warnings.warn(
                        f"asset path collision for {key!r}: keeping "
                        f"{asset_paths[key]!s}, ignoring {resolved!s}",
                        UserWarning,
                        stacklevel=2,
                    )
                else:
                    asset_paths[key] = resolved

        # 7. Aggregate public block_data.
        block_data: dict[str, Any] = {}
        for artifact in artifacts:
            if artifact.block_id and artifact.data is not None:
                block_data[artifact.block_id] = artifact.data

        # 8. Versions.
        versions: dict[str, int] = {"core": SCRIBA_VERSION}
        for renderer in self._renderers:
            raw_version = getattr(renderer, "version", None)
            try:
                versions[renderer.name] = int(raw_version)
            except (TypeError, ValueError) as e:
                raise ValidationError(
                    f"renderer {renderer.name!r} has non-int-coercible "
                    f"version {raw_version!r} (type "
                    f"{type(raw_version).__name__}): {e}"
                ) from e

        # 9. Build Document.
        return Document(
            html=rendered_html,
            required_css=frozenset(css_set),
            required_js=frozenset(js_set),
            versions=versions,
            block_data=block_data,
            required_assets=asset_paths,
            warnings=tuple(internal_collector),
        )

    def close(self) -> None:
        """Shut down all renderers owned by this pipeline. Idempotent.

        Exceptions raised by individual renderer ``close()`` methods are
        caught so one broken renderer cannot block cleanup of the rest,
        but each failure is surfaced via :mod:`warnings` and the standard
        logger so resource leaks are visible instead of silent.
        """
        if self._closed:
            return
        self._closed = True
        for renderer in self._renderers:
            close = getattr(renderer, "close", None)
            if not callable(close):
                continue
            name = getattr(renderer, "name", "<unnamed>")
            try:
                close()
            except Exception as e:  # noqa: BLE001 - defensive cleanup
                msg = f"renderer {name!r} close() raised: {e}"
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
                logger.warning(msg, exc_info=True)

    def __enter__(self) -> "Pipeline":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
