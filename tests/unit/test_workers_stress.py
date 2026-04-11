"""Stress tests for the KaTeX worker subprocess pool.

Covers two scenarios called out in audit 17-H3:

1. **Saturation** — many concurrent inline-math requests execute without
   deadlocking the pool, and every response comes back complete.
2. **Faulty input recovery** — a syntactically bad LaTeX expression does
   not kill the worker; subsequent valid requests succeed.
"""

from __future__ import annotations

import concurrent.futures

import pytest

from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def stress_pipeline():
    pool = SubprocessWorkerPool()
    renderer = TexRenderer(worker_pool=pool, pygments_theme="none")
    pipe = Pipeline([renderer])
    try:
        yield pipe
    finally:
        pipe.close()
        renderer.close()
        pool.close()


@pytest.fixture
def ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={},
        render_inline_tex=None,
    )


# ---------------------------------------------------------------------------
# Saturation
# ---------------------------------------------------------------------------


class TestWorkerSaturation:
    """Hammer the KaTeX pool with many concurrent requests."""

    def test_100_concurrent_inline_math_succeeds(
        self, stress_pipeline: Pipeline, ctx: RenderContext,
    ) -> None:
        """100 concurrent inline-math renders all return valid HTML.

        Pass criteria:
        * No thread deadlocks (suite-level timeout will catch hangs).
        * Every response contains a KaTeX-rendered ``<span class="katex">``.
        * No request raises an exception.
        """
        formulas = [f"$x_{{{i}}}^2 + y_{{{i}}} = {i}$" for i in range(100)]

        def render_one(src: str) -> str:
            doc = stress_pipeline.render(src, ctx)
            return doc.html

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            results = list(executor.map(render_one, formulas))

        assert len(results) == 100
        for i, html in enumerate(results):
            assert html, f"result {i} is empty"
            assert "katex" in html, (
                f"result {i} missing KaTeX markup: {html[:120]!r}"
            )


# ---------------------------------------------------------------------------
# Fault recovery
# ---------------------------------------------------------------------------


class TestWorkerFaultRecovery:
    """Malformed LaTeX must not kill the worker pool."""

    def test_bad_math_followed_by_good_math(
        self, stress_pipeline: Pipeline, ctx: RenderContext,
    ) -> None:
        """After a KaTeX parse error, subsequent requests still succeed.

        KaTeX returns an error span inline for invalid macros rather
        than tearing down the worker. This test pins that behaviour so a
        regression to "one bad request breaks the pool" is visible.
        """
        # First: an input KaTeX rejects or renders as an error span.
        bad_tex = r"Partial: $\unknownmacro{x}$ rest"
        good_tex = r"Recovery: $a^2 + b^2 = c^2$"

        # The bad request must not raise a fatal exception.
        bad_doc = stress_pipeline.render(bad_tex, ctx)
        assert bad_doc.html, "bad-input render returned empty HTML"

        # And the pool must continue to serve valid requests.
        good_doc = stress_pipeline.render(good_tex, ctx)
        assert good_doc.html, "follow-up render returned empty HTML"
        assert "katex" in good_doc.html, (
            "follow-up render missing KaTeX markup"
        )

        # And the next sequential request also works — confirms no sticky state.
        another = stress_pipeline.render(r"$e^{i\pi} + 1 = 0$", ctx)
        assert "katex" in another.html
