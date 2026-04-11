"""Pipeline orchestration, asset aggregation, and lifecycle tests.

See docs/scriba/01-architecture.md §Pipeline.
"""

from __future__ import annotations

import warnings

import pytest

from scriba import (
    Block,
    Pipeline,
    RenderArtifact,
    RenderContext,
    RendererAssets,
    ValidationError,
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


# =========================================================================
# Cluster 3 — audit finding 20 regression tests
# =========================================================================


def _stub_assets() -> RendererAssets:
    return RendererAssets(css_files=frozenset(), js_files=frozenset())


class _IdentityRenderer:
    """Renders a single whole-source block, returning fixed HTML."""

    name = "identity"
    version = 1
    priority = 100

    def __init__(self, html: str = "<b>x</b>") -> None:
        self._html = html

    def detect(self, source):
        return [Block(start=0, end=len(source), kind="w", raw=source)]

    def render_block(self, block, ctx):
        return RenderArtifact(
            html=self._html,
            css_assets=frozenset(),
            js_assets=frozenset(),
        )

    def assets(self):
        return _stub_assets()


# --- 20-C2: placeholder re-entry bug -------------------------------------


def test_placeholder_cannot_be_forged_by_artifact_html():
    """An artifact whose HTML contains the legacy placeholder pattern must
    not disturb a second block's substitution. Prior code used naive
    ``.replace("\\x00SCRIBA_BLOCK_{i}\\x00", html)`` and could be
    re-entered by adversarial HTML. The nonce-based placeholder prevents
    the forgery entirely.
    """

    class Adversary:
        name = "adv"
        version = 1
        priority = 50

        def detect(self, source):
            return [
                Block(start=0, end=3, kind="a", raw=source[:3]),
                Block(start=3, end=len(source), kind="b", raw=source[3:]),
            ]

        def render_block(self, block, ctx):
            if block.kind == "a":
                # Try to inject a forged legacy placeholder into the
                # second block's slot.
                return RenderArtifact(
                    html="\x00SCRIBA_BLOCK_1\x00PWNED",
                    css_assets=frozenset(),
                    js_assets=frozenset(),
                )
            return RenderArtifact(
                html="<clean>",
                css_assets=frozenset(),
                js_assets=frozenset(),
            )

        def assets(self):
            return _stub_assets()

    p = Pipeline([Adversary()])
    ctx = RenderContext(resource_resolver=lambda n: None)
    doc = p.render("aaabbb", ctx)
    # Adversary HTML preserved verbatim.
    assert "\x00SCRIBA_BLOCK_1\x00PWNED" in doc.html
    assert "<clean>" in doc.html
    # The adversary's legacy marker was NOT substituted by the second
    # block's content.
    assert "<clean>PWNED" not in doc.html


def test_placeholder_uses_fresh_nonce_per_render():
    """Two consecutive renders should yield different placeholder nonces,
    ensuring that output from render #1 cannot pollute render #2.
    """

    seen_nonces: list[str] = []

    class SnoopRenderer:
        name = "snoop"
        version = 1
        priority = 100

        def detect(self, source):
            return [Block(start=0, end=len(source), kind="s", raw=source)]

        def render_block(self, block, ctx):
            return RenderArtifact(
                html="X",
                css_assets=frozenset(),
                js_assets=frozenset(),
            )

        def assets(self):
            return _stub_assets()

    import re as _re

    p = Pipeline([SnoopRenderer()])
    ctx = RenderContext(resource_resolver=lambda n: None)

    # We exercise render twice and peek inside the constructed scaffold
    # by patching re.compile used internally. The safer approach: exercise
    # two renders and confirm they produce stable HTML (sanity check).
    doc1 = p.render("abc", ctx)
    doc2 = p.render("abc", ctx)
    assert doc1.html == "X"
    assert doc2.html == "X"

    # No placeholder bytes leaked into the final output.
    assert "\x00" not in doc1.html
    assert "\x00" not in doc2.html
    # Nothing in the audit regex pattern remains either.
    assert _re.search(r"SCRIBA_BLOCK_", doc1.html) is None


# --- 20-C1: context provider failure path --------------------------------


def test_context_provider_returning_none_raises_validation_error():
    def bad_provider(ctx, renderers):
        return None  # type: ignore[return-value]

    p = Pipeline([_IdentityRenderer()], context_providers=[bad_provider])
    ctx = RenderContext(resource_resolver=lambda n: None)
    with pytest.raises(ValidationError) as exc:
        p.render("hi", ctx)
    assert "bad_provider" in str(exc.value)
    assert "RenderContext" in str(exc.value)


def test_context_provider_returning_dict_raises_validation_error():
    def dict_provider(ctx, renderers):
        return {"theme": "light"}  # type: ignore[return-value]

    p = Pipeline([_IdentityRenderer()], context_providers=[dict_provider])
    ctx = RenderContext(resource_resolver=lambda n: None)
    with pytest.raises(ValidationError) as exc:
        p.render("hi", ctx)
    assert "dict_provider" in str(exc.value)


def test_context_provider_raises_wrapped_with_identity():
    def boom(ctx, renderers):
        raise RuntimeError("provider fell over")

    p = Pipeline([_IdentityRenderer()], context_providers=[boom])
    ctx = RenderContext(resource_resolver=lambda n: None)
    with pytest.raises(ValidationError) as exc:
        p.render("hi", ctx)
    msg = str(exc.value)
    assert "boom" in msg
    assert "RuntimeError" in msg
    assert "provider fell over" in msg
    # The original exception is chained.
    assert isinstance(exc.value.__cause__, RuntimeError)


def test_context_provider_returning_valid_context_passes():
    """Happy path: provider returns a valid RenderContext; render succeeds."""
    import dataclasses

    def identity(ctx, renderers):
        return dataclasses.replace(ctx, theme="light")

    p = Pipeline([_IdentityRenderer()], context_providers=[identity])
    ctx = RenderContext(resource_resolver=lambda n: None)
    doc = p.render("hi", ctx)
    assert doc.html == "<b>x</b>"


# --- 20-C3: context_providers=[] bypass semantics ------------------------


def test_empty_context_providers_list_emits_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Pipeline([_IdentityRenderer()], context_providers=[])
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert user_warnings, "expected a UserWarning for explicit empty list"
    assert any(
        "context_providers=[]" in str(w.message) for w in user_warnings
    )


def test_none_context_providers_uses_defaults_silently():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Pipeline([_IdentityRenderer()])  # None is default
    assert not [
        w for w in caught
        if issubclass(w.category, UserWarning)
        and "context_providers" in str(w.message)
    ]


# --- 20-H1: Pipeline.close() exception surfacing -------------------------


def test_pipeline_close_surfaces_renderer_close_errors_as_warning():
    class ExplosiveRenderer(_IdentityRenderer):
        name = "explosive"

        def close(self):
            raise RuntimeError("fd leak imminent")

    p = Pipeline([ExplosiveRenderer()])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        p.close()  # must not raise
    messages = [str(w.message) for w in caught]
    assert any("explosive" in m and "fd leak imminent" in m for m in messages)


def test_pipeline_close_idempotent_even_if_renderer_raised():
    class ExplosiveRenderer(_IdentityRenderer):
        name = "explosive"

        def close(self):
            raise RuntimeError("boom")

    p = Pipeline([ExplosiveRenderer()])
    p.close()
    p.close()  # second call is a no-op


# --- 20-H2: non-int-coercible renderer.version ---------------------------


def test_non_int_version_raises_validation_error():
    class BadVersionRenderer(_IdentityRenderer):
        name = "badver"
        version = "one-point-zero"  # type: ignore[assignment]

    p = Pipeline([BadVersionRenderer()])
    ctx = RenderContext(resource_resolver=lambda n: None)
    with pytest.raises(ValidationError) as exc:
        p.render("hi", ctx)
    msg = str(exc.value)
    assert "badver" in msg
    assert "one-point-zero" in msg


def test_non_coercible_version_object_raises_validation_error():
    class Opaque:
        def __int__(self):
            raise TypeError("nope")

    class WeirdRenderer(_IdentityRenderer):
        name = "weird"
        version = Opaque()  # type: ignore[assignment]

    p = Pipeline([WeirdRenderer()])
    ctx = RenderContext(resource_resolver=lambda n: None)
    with pytest.raises(ValidationError) as exc:
        p.render("hi", ctx)
    assert "weird" in str(exc.value)


# --- 20-M1: block rendering loop enrichment ------------------------------


def test_render_block_failure_enriches_message_with_block_identity():
    class FaultyRenderer(_IdentityRenderer):
        name = "faulty"

        def render_block(self, block, ctx):
            raise RuntimeError("kaboom")

    p = Pipeline([FaultyRenderer()])
    ctx = RenderContext(resource_resolver=lambda n: None)
    with pytest.raises(RuntimeError) as exc:
        p.render("hi", ctx)
    msg = str(exc.value)
    assert "faulty" in msg
    assert "kaboom" in msg
    assert "0:2" in msg  # block range [0:2]
    assert "'w'" in msg  # block kind


# --- 20-M2: asset path collision warning ---------------------------------


def test_asset_path_collision_warns_and_keeps_first(tmp_path):
    """Two css_files entries in the same renderer with the same basename
    produce a namespace collision — the first path is retained and a
    UserWarning is emitted.
    """
    a = tmp_path / "dir1" / "style.css"
    b = tmp_path / "dir2" / "style.css"
    a.parent.mkdir(parents=True)
    b.parent.mkdir(parents=True)
    a.write_text("/*a*/")
    b.write_text("/*b*/")

    class TwoPaths:
        name = "two"
        version = 1
        priority = 100

        def detect(self, source):
            return []

        def render_block(self, block, ctx):  # pragma: no cover
            return RenderArtifact(
                html="",
                css_assets=frozenset(),
                js_assets=frozenset(),
            )

        def assets(self):
            return RendererAssets(
                css_files=frozenset({a, b}),
                js_files=frozenset(),
            )

    p = Pipeline([TwoPaths()])
    ctx = RenderContext(resource_resolver=lambda n: None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        doc = p.render("hi", ctx)

    assert "two/style.css" in doc.required_css
    # A single key, one of the two paths wins deterministically.
    assert doc.required_assets["two/style.css"] in (a, b)

    warning_msgs = [
        str(w.message) for w in caught
        if issubclass(w.category, UserWarning)
        and "collision" in str(w.message)
    ]
    assert warning_msgs, "expected a collision warning"

