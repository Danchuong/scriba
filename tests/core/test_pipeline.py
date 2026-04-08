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
    assert doc.versions == {"core": 2, "tex": 1}


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


# --- C2: block_data round-trip -------------------------------------------


def test_pipeline_block_data_roundtrip():
    from pathlib import Path

    class DataRenderer:
        name = "data"
        version = 1
        priority = 50

        def detect(self, source):
            return [Block(start=0, end=len(source), kind="d", raw=source)]

        def render_block(self, block, ctx):
            return RenderArtifact(
                html="<span>x</span>",
                css_assets=frozenset(),
                js_assets=frozenset(),
                block_id="b1",
                data={"foo": "bar", "n": 3},
            )

        def assets(self):
            return RendererAssets(css_files=frozenset(), js_files=frozenset())

    p = Pipeline([DataRenderer()])
    ctx = RenderContext(resource_resolver=lambda n: None)
    doc = p.render("hello", ctx)
    assert doc.block_data == {"b1": {"foo": "bar", "n": 3}}


# --- C3: namespaced assets ------------------------------------------------


def test_pipeline_asset_namespace_avoids_collision(tmp_path):
    from pathlib import Path

    a_css = tmp_path / "a" / "style.css"
    b_css = tmp_path / "b" / "style.css"
    a_css.parent.mkdir(parents=True)
    b_css.parent.mkdir(parents=True)
    a_css.write_text("/*a*/")
    b_css.write_text("/*b*/")

    class A:
        name = "aaa"
        version = 1
        priority = 100

        def detect(self, source):
            return []

        def render_block(self, block, ctx):  # pragma: no cover
            return RenderArtifact(
                html="", css_assets=frozenset(), js_assets=frozenset()
            )

        def assets(self):
            return RendererAssets(
                css_files=frozenset({a_css}), js_files=frozenset()
            )

    class B(A):
        name = "bbb"

        def assets(self):
            return RendererAssets(
                css_files=frozenset({b_css}), js_files=frozenset()
            )

    p = Pipeline([A(), B()])
    ctx = RenderContext(resource_resolver=lambda n: None)
    doc = p.render("hi", ctx)
    assert "aaa/style.css" in doc.required_css
    assert "bbb/style.css" in doc.required_css
    # Both paths exposed
    assert doc.required_assets["aaa/style.css"] == a_css
    assert doc.required_assets["bbb/style.css"] == b_css


# --- C4: priority tie-breaker --------------------------------------------


def test_pipeline_priority_breaks_overlap_ties():
    winner_calls: list[str] = []

    def make(name: str, priority: int):
        class R:
            pass

        R.name = name
        R.version = 1
        R.priority = priority

        def detect(self, source):
            return [Block(start=0, end=len(source), kind="x", raw=source)]

        def render_block(self, block, ctx):
            winner_calls.append(name)
            return RenderArtifact(
                html=f"<!{name}>",
                css_assets=frozenset(),
                js_assets=frozenset(),
            )

        def assets(self):
            return RendererAssets(css_files=frozenset(), js_files=frozenset())

        R.detect = detect
        R.render_block = render_block
        R.assets = assets
        return R()

    low = make("low", 10)  # lower priority number = wins
    high = make("high", 100)
    # Pass high FIRST to prove priority beats list order.
    p = Pipeline([high, low])
    ctx = RenderContext(resource_resolver=lambda n: None)
    doc = p.render("hello", ctx)
    assert winner_calls == ["low"]
    assert "<!low>" in doc.html


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
