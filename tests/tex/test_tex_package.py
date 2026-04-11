"""Coverage for ``scriba.tex`` package-level exports.

Targets the ``tex_inline_provider`` context provider, which wires a
``TexRenderer._render_inline`` callback into :class:`RenderContext` when
a renderer is registered with the pipeline. Cluster 8 coverage push.
"""

from __future__ import annotations

import dataclasses

import pytest

import scriba.tex as scriba_tex
from scriba import RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer, tex_inline_provider


def _make_ctx(**overrides: object) -> RenderContext:
    base = dict(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={},
        render_inline_tex=None,
    )
    base.update(overrides)  # type: ignore[arg-type]
    return RenderContext(**base)  # type: ignore[arg-type]


def test_exports_are_public():
    """The package exports ``TexRenderer`` and ``tex_inline_provider``."""
    assert hasattr(scriba_tex, "TexRenderer")
    assert hasattr(scriba_tex, "tex_inline_provider")
    assert "TexRenderer" in scriba_tex.__all__
    assert "tex_inline_provider" in scriba_tex.__all__


def test_tex_renderer_symbol_is_class():
    assert isinstance(TexRenderer, type)
    assert TexRenderer.name == "tex"
    assert isinstance(TexRenderer.version, int)


def test_provider_installs_callback_when_tex_renderer_present(tex_renderer):
    ctx = _make_ctx()
    assert ctx.render_inline_tex is None

    new_ctx = tex_inline_provider(ctx, [tex_renderer])

    assert new_ctx is not ctx, "provider must return a new context"
    assert callable(new_ctx.render_inline_tex)
    # Delegates to TexRenderer._render_inline for real math.
    out = new_ctx.render_inline_tex("x^2")
    assert "scriba-tex-math-inline" in out


def test_provider_is_idempotent_when_callback_already_set(tex_renderer):
    """If the context already has ``render_inline_tex``, the provider leaves
    it alone and returns the context unchanged."""
    existing = lambda s: f"<stub:{s}>"
    ctx = _make_ctx(render_inline_tex=existing)

    result = tex_inline_provider(ctx, [tex_renderer])

    assert result is ctx
    assert result.render_inline_tex is existing


def test_provider_noop_when_no_tex_renderer():
    """No TexRenderer in list -> context is returned unchanged."""
    ctx = _make_ctx()
    # Not a TexRenderer; should be skipped.
    fake = object()

    result = tex_inline_provider(ctx, [fake])  # type: ignore[list-item]

    assert result is ctx
    assert result.render_inline_tex is None


def test_provider_noop_with_empty_renderer_list():
    ctx = _make_ctx()
    result = tex_inline_provider(ctx, [])
    assert result is ctx
    assert result.render_inline_tex is None


def test_provider_picks_first_tex_renderer(tex_renderer):
    """When multiple candidates are supplied, the first TexRenderer wins."""
    ctx = _make_ctx()
    result = tex_inline_provider(ctx, [object(), tex_renderer])  # type: ignore[list-item]
    assert callable(result.render_inline_tex)


def test_provider_delegate_ignores_empty(tex_renderer):
    """The wired delegate tolerates empty/whitespace math (consistent with
    TexRenderer._render_inline)."""
    ctx = _make_ctx()
    new_ctx = tex_inline_provider(ctx, [tex_renderer])
    assert new_ctx.render_inline_tex("") == ""
    assert new_ctx.render_inline_tex("   ") == ""


def test_provider_returns_dataclass_copy(tex_renderer):
    """Provider should use ``dataclasses.replace``; verify original untouched."""
    ctx = _make_ctx()
    new_ctx = tex_inline_provider(ctx, [tex_renderer])

    assert dataclasses.is_dataclass(new_ctx)
    # Other fields are preserved.
    assert new_ctx.resource_resolver is ctx.resource_resolver
    assert new_ctx.theme == ctx.theme
    assert new_ctx.dark_mode == ctx.dark_mode
    assert new_ctx.metadata == ctx.metadata
    # Original context still has the ``None`` callback.
    assert ctx.render_inline_tex is None
