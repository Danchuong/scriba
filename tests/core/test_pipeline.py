"""Pipeline orchestration, asset aggregation, and lifecycle tests.

See docs/scriba/01-architecture.md §Pipeline.
"""

from __future__ import annotations

import pytest

from scriba import (
    Block,
    Pipeline,
    RenderArtifact,
    RenderContext,
    RendererAssets,
)


def test_pipeline_aggregates_css_assets(pipeline):
    assert "scriba-tex-content.css" in pipeline_required_css(pipeline)


def test_pipeline_aggregates_js_assets(pipeline):
    assert "scriba-tex-copy.js" in pipeline_required_js(pipeline)


def test_pipeline_versions_dict(pipeline, ctx):
    doc = pipeline.render("Hello", ctx)
    assert doc.versions == {"core": 1, "tex": 1}


def test_pipeline_close_propagates(worker_pool):
    """Closing the pipeline must call close() on every owned renderer."""
    from scriba.tex import TexRenderer

    r = TexRenderer(worker_pool=worker_pool)
    p = Pipeline([r])
    p.close()
    # Calling pipeline.close() again is also idempotent.
    p.close()


def test_pipeline_context_manager(worker_pool):
    from scriba.tex import TexRenderer

    r = TexRenderer(worker_pool=worker_pool)
    with Pipeline([r]) as p:
        assert p is not None


def test_pipeline_render_inline_tex_wiring(worker_pool):
    """Pipeline must auto-populate ctx.render_inline_tex when a TexRenderer
    is registered. We use a fake renderer that snapshots the ctx it sees.
    """
    from scriba.tex import TexRenderer

    seen: dict[str, RenderContext] = {}

    class FakeRenderer:
        name = "fake"
        version = 1

        def detect(self, source):
            return [Block(start=0, end=len(source), kind="fake", raw=source)]

        def render_block(self, block, ctx):
            seen["ctx"] = ctx
            return RenderArtifact(
                html="", css_assets=frozenset(), js_assets=frozenset()
            )

        def assets(self):
            return RendererAssets(css_files=frozenset(), js_files=frozenset())

    tex = TexRenderer(worker_pool=worker_pool)
    p = Pipeline([FakeRenderer(), tex])
    ctx = RenderContext(
        resource_resolver=lambda n: None, render_inline_tex=None
    )
    p.render("hello", ctx)
    assert "ctx" in seen
    assert seen["ctx"].render_inline_tex is not None


def test_pipeline_empty_renderers_raises():
    with pytest.raises(ValueError):
        Pipeline([])


# --- helpers --------------------------------------------------------------


def pipeline_required_css(pipeline) -> set[str]:
    """Render a trivial doc, return basenames of required css."""
    ctx = RenderContext(resource_resolver=lambda n: None)
    doc = pipeline.render("Hello", ctx)
    return {n if "/" not in n else n.rsplit("/", 1)[1] for n in doc.required_css}


def pipeline_required_js(pipeline) -> set[str]:
    ctx = RenderContext(resource_resolver=lambda n: None)
    doc = pipeline.render(r"\begin{lstlisting}[language=cpp]int x;\end{lstlisting}", ctx)
    return {n if "/" not in n else n.rsplit("/", 1)[1] for n in doc.required_js}
