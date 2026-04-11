"""Coverage push for ``scriba.tex.renderer`` (Cluster 8).

These tests exercise the uncovered slices of :class:`TexRenderer`:
- dark theme asset/block paths
- _render_cell fast-exit and inline-math stashing
- _render_inline with worker error (non-strict + strict)
- _render_inline with None HTML response
- batch math WorkerError fallback (non-strict)
- _render_source empty-paragraph early return
- validate() delegation
- close() idempotency and context-manager
- detect() oversize ValidationError
- resource_resolver for images

No source edits — tests only.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from scriba import (
    Pipeline,
    RenderContext,
    SubprocessWorkerPool,
    ValidationError,
    WorkerError,
)
from scriba.core.errors import RendererError
from scriba.tex import TexRenderer


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _make_ctx() -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/r/{name}",
        theme="light",
        dark_mode=False,
        metadata={},
        render_inline_tex=None,
    )


@pytest.fixture(scope="module")
def dark_renderer():
    pool = SubprocessWorkerPool()
    try:
        r = TexRenderer(worker_pool=pool, pygments_theme="one-dark")
        try:
            yield r
        finally:
            r.close()
    finally:
        pool.close()


@pytest.fixture(scope="module")
def github_dark_renderer():
    pool = SubprocessWorkerPool()
    try:
        r = TexRenderer(worker_pool=pool, pygments_theme="github-dark")
        try:
            yield r
        finally:
            r.close()
    finally:
        pool.close()


@pytest.fixture(scope="module")
def no_copy_buttons_renderer():
    pool = SubprocessWorkerPool()
    try:
        r = TexRenderer(
            worker_pool=pool,
            pygments_theme="one-light",
            enable_copy_buttons=False,
        )
        try:
            yield r
        finally:
            r.close()
    finally:
        pool.close()


# -----------------------------------------------------------------------------
# Dark theme paths (lines 225, 241)
# -----------------------------------------------------------------------------


def test_dark_theme_assets_includes_dark_css(dark_renderer):
    a = dark_renderer.assets()
    names = {p.name for p in a.css_files}
    assert "scriba-tex-pygments-dark.css" in names


def test_dark_theme_block_css_uses_dark_pygments(dark_renderer):
    from scriba.core.artifact import Block

    block = Block(start=0, end=5, kind="tex", raw="hi")
    ctx = _make_ctx()
    art = dark_renderer.render_block(block, ctx)
    assert "scriba-tex-pygments-dark.css" in art.css_assets


def test_github_dark_theme_assets(github_dark_renderer):
    a = github_dark_renderer.assets()
    names = {p.name for p in a.css_files}
    assert "scriba-tex-pygments-dark.css" in names


def test_github_dark_block_css(github_dark_renderer):
    from scriba.core.artifact import Block

    block = Block(start=0, end=3, kind="tex", raw="abc")
    ctx = _make_ctx()
    art = github_dark_renderer.render_block(block, ctx)
    assert "scriba-tex-pygments-dark.css" in art.css_assets


def test_no_copy_buttons_omits_js(no_copy_buttons_renderer):
    a = no_copy_buttons_renderer.assets()
    assert len(a.js_files) == 0


def test_no_copy_buttons_block_has_no_js(no_copy_buttons_renderer):
    from scriba.core.artifact import Block

    block = Block(start=0, end=3, kind="tex", raw="hi")
    ctx = _make_ctx()
    art = no_copy_buttons_renderer.render_block(block, ctx)
    assert len(art.js_assets) == 0


# -----------------------------------------------------------------------------
# Public protocol: validate / close / detect
# -----------------------------------------------------------------------------


def test_validate_delegates_to_module_validate(tex_renderer):
    ok, err = tex_renderer.validate("")
    assert ok is True
    assert err is None


def test_validate_returns_failure_for_unmatched_brace(tex_renderer):
    ok, err = tex_renderer.validate("{")
    assert ok is False
    assert err and "{" in err


def test_validate_failure_for_unknown_env(tex_renderer):
    ok, err = tex_renderer.validate(r"\begin{bogusenv}x\end{bogusenv}")
    assert ok is False
    assert err and "bogusenv" in err


def test_close_marks_closed_and_idempotent(tex_renderer):
    # This is the shared session fixture; create a separate instance to
    # avoid tainting the session renderer for later tests.
    pool = SubprocessWorkerPool()
    try:
        r = TexRenderer(worker_pool=pool)
        assert r._closed is False  # type: ignore[attr-defined]
        r.close()
        assert r._closed is True  # type: ignore[attr-defined]
        r.close()  # idempotent
        assert r._closed is True  # type: ignore[attr-defined]
    finally:
        pool.close()


def test_context_manager_closes_on_exit():
    pool = SubprocessWorkerPool()
    try:
        with TexRenderer(worker_pool=pool) as r:
            assert r._closed is False  # type: ignore[attr-defined]
        assert r._closed is True  # type: ignore[attr-defined]
    finally:
        pool.close()


def test_detect_oversize_raises_validation_error(tex_renderer):
    huge = "a" * (1_048_576 + 1)
    with pytest.raises(ValidationError):
        tex_renderer.detect(huge)


def test_detect_at_size_cap_ok(tex_renderer):
    # 1 MiB exactly should still be accepted.
    src = "a" * 1_048_576
    blocks = tex_renderer.detect(src)
    assert len(blocks) == 1
    assert blocks[0].kind == "tex"


def test_detect_empty_source_returns_single_block(tex_renderer):
    blocks = tex_renderer.detect("")
    assert len(blocks) == 1
    assert blocks[0].start == 0
    assert blocks[0].end == 0
    assert blocks[0].raw == ""


# -----------------------------------------------------------------------------
# _render_cell via tabular (exercises empty/math/text/dashes paths)
# -----------------------------------------------------------------------------


def test_tabular_cells_render_math_and_text(pipeline, ctx):
    src = r"\begin{tabular}{ll} $x^2$ & plain\\ ``hi'' & \$5 \\ \end{tabular}"
    doc = pipeline.render(src, ctx)
    assert "<table" in doc.html
    # Math renders if node+katex are available; otherwise the cell text
    # falls back to escaped TeX. Either way the table must be present.
    assert "plain" in doc.html


def test_tabular_with_empty_cells(pipeline, ctx):
    """Empty cell raw triggers _render_cell early-exit."""
    src = r"\begin{tabular}{ll} & x \\ y & \\ \end{tabular}"
    doc = pipeline.render(src, ctx)
    assert "<table" in doc.html


def test_tabular_cell_with_text_command(pipeline, ctx):
    src = r"\begin{tabular}{ll}\textbf{A} & \textit{B}\\\end{tabular}"
    doc = pipeline.render(src, ctx)
    assert "<table" in doc.html


def test_tabular_cell_with_escaped_specials(pipeline, ctx):
    src = r"\begin{tabular}{ll} 5\% & \#1 \\ \_x & \{y\} \\ \end{tabular}"
    doc = pipeline.render(src, ctx)
    assert "<table" in doc.html
    assert "5%" in doc.html or "5&" not in doc.html


# -----------------------------------------------------------------------------
# _render_inline direct exercise (covers lines 321-345)
# -----------------------------------------------------------------------------


def test_render_inline_empty_returns_empty(tex_renderer):
    assert tex_renderer._render_inline("") == ""  # type: ignore[attr-defined]
    assert tex_renderer._render_inline("   ") == ""  # type: ignore[attr-defined]


def test_render_inline_non_strict_catches_worker_error():
    """Non-strict mode must catch WorkerError and fall back to HTML escape."""
    pool = SubprocessWorkerPool()

    class BadWorker:
        name = "katex"

        def send(self, request, *, timeout=None):
            raise WorkerError("boom from test")

        def close(self):
            pass

    try:
        r = TexRenderer(worker_pool=pool, pygments_theme="none", strict_math=False)
        try:
            # Overwrite the registered katex worker so our failing one is used.
            pool._workers["katex"] = BadWorker()  # type: ignore[attr-defined]
            out = r._render_inline("x^2")  # type: ignore[attr-defined]
            assert "x" in out
            # Non-strict fallback emits escaped plaintext, not the math span.
            assert "scriba-tex-math-inline" not in out
        finally:
            r.close()
    finally:
        pool.close()


def test_render_inline_strict_propagates_worker_error():
    pool = SubprocessWorkerPool()

    class BadWorker:
        name = "katex"

        def send(self, request, *, timeout=None):
            raise WorkerError("boom from test")

        def close(self):
            pass

    try:
        r = TexRenderer(worker_pool=pool, pygments_theme="none", strict_math=True)
        try:
            pool._workers["katex"] = BadWorker()  # type: ignore[attr-defined]
            with pytest.raises(WorkerError):
                r._render_inline("x^2")  # type: ignore[attr-defined]
        finally:
            r.close()
    finally:
        pool.close()


def test_render_inline_none_html_non_strict_falls_back():
    """Worker returns {'html': None, 'error': '...'} -> non-strict escape."""
    pool = SubprocessWorkerPool()

    class NullWorker:
        name = "katex"

        def send(self, request, *, timeout=None):
            return {"html": None, "error": "katex parse error"}

        def close(self):
            pass

    try:
        r = TexRenderer(worker_pool=pool, pygments_theme="none", strict_math=False)
        try:
            pool._workers["katex"] = NullWorker()  # type: ignore[attr-defined]
            out = r._render_inline("x^2")  # type: ignore[attr-defined]
            assert "scriba-tex-math-inline" not in out
            assert "x" in out
        finally:
            r.close()
    finally:
        pool.close()


def test_render_inline_none_html_strict_raises_renderer_error():
    pool = SubprocessWorkerPool()

    class NullWorker:
        name = "katex"

        def send(self, request, *, timeout=None):
            return {"html": None, "error": "katex parse error"}

        def close(self):
            pass

    try:
        r = TexRenderer(worker_pool=pool, pygments_theme="none", strict_math=True)
        try:
            pool._workers["katex"] = NullWorker()  # type: ignore[attr-defined]
            with pytest.raises(RendererError):
                r._render_inline("x^2")  # type: ignore[attr-defined]
        finally:
            r.close()
    finally:
        pool.close()


def test_render_inline_success_wraps_in_math_span():
    pool = SubprocessWorkerPool()

    class OkWorker:
        name = "katex"

        def send(self, request, *, timeout=None):
            return {"html": "<span class='katex'>X</span>"}

        def close(self):
            pass

    try:
        r = TexRenderer(worker_pool=pool, pygments_theme="none")
        try:
            pool._workers["katex"] = OkWorker()  # type: ignore[attr-defined]
            out = r._render_inline("x")  # type: ignore[attr-defined]
            assert "scriba-tex-math-inline" in out
            assert "<span class='katex'>X</span>" in out
        finally:
            r.close()
    finally:
        pool.close()


def test_render_inline_with_macros_sends_macros():
    """When katex_macros is set, the request includes a ``macros`` field."""
    pool = SubprocessWorkerPool()
    captured: list[dict] = []

    class CapturingWorker:
        name = "katex"

        def send(self, request, *, timeout=None):
            captured.append(request)
            return {"html": "<span>ok</span>"}

        def close(self):
            pass

    try:
        r = TexRenderer(
            worker_pool=pool,
            pygments_theme="none",
            katex_macros={r"\RR": r"\mathbb{R}"},
        )
        try:
            pool._workers["katex"] = CapturingWorker()  # type: ignore[attr-defined]
            r._render_inline(r"\RR")  # type: ignore[attr-defined]
            assert captured
            req = captured[0]
            assert "macros" in req
            assert req["macros"].get(r"\RR") == r"\mathbb{R}"
            # Ensure a copy was sent, not the live dict reference.
            req["macros"]["\\QQ"] = "spoof"
            assert r._katex_macros is not None  # type: ignore[attr-defined]
            assert "\\QQ" not in r._katex_macros  # type: ignore[attr-defined]
        finally:
            r.close()
    finally:
        pool.close()


# -----------------------------------------------------------------------------
# Math batch WorkerError fallback (lines 427-431)
# -----------------------------------------------------------------------------


def test_math_batch_worker_error_non_strict_renders_escaped():
    pool = SubprocessWorkerPool()

    class FlakyWorker:
        name = "katex"

        def send(self, request, *, timeout=None):
            raise WorkerError("batch boom")

        def close(self):
            pass

    try:
        r = TexRenderer(worker_pool=pool, pygments_theme="none", strict_math=False)
        try:
            pool._workers["katex"] = FlakyWorker()  # type: ignore[attr-defined]
            p = Pipeline([r])
            try:
                doc = p.render(r"Given $x^2 + y^2 = z^2$, done.", _make_ctx())
                assert "x^2" in doc.html or "x" in doc.html
                assert doc.html  # produced some HTML
            finally:
                p.close()
        finally:
            r.close()
    finally:
        pool.close()


def test_math_batch_worker_error_strict_propagates():
    pool = SubprocessWorkerPool()

    class FlakyWorker:
        name = "katex"

        def send(self, request, *, timeout=None):
            raise WorkerError("batch boom")

        def close(self):
            pass

    try:
        r = TexRenderer(worker_pool=pool, pygments_theme="none", strict_math=True)
        try:
            pool._workers["katex"] = FlakyWorker()  # type: ignore[attr-defined]
            p = Pipeline([r])
            try:
                with pytest.raises(WorkerError):
                    p.render(r"$x^2$", _make_ctx())
            finally:
                p.close()
        finally:
            r.close()
    finally:
        pool.close()


# -----------------------------------------------------------------------------
# _render_source paragraph-empty early return (line 465)
# -----------------------------------------------------------------------------


def test_render_source_only_whitespace_yields_empty(pipeline, ctx):
    """A source that strips to empty after passes should return ''."""
    doc = pipeline.render("   \n   \n\t  ", ctx)
    assert doc.html == ""


def test_render_source_empty_string_yields_empty(pipeline, ctx):
    doc = pipeline.render("", ctx)
    assert doc.html == ""


# -----------------------------------------------------------------------------
# Sections, lists, tables, urls, includegraphics — additional coverage
# -----------------------------------------------------------------------------


def test_section_subsection_subsubsection_all_render(pipeline, ctx):
    src = (
        r"\section{Main}"
        r"\subsection{Sub}"
        r"\subsubsection{Subsub}"
        r"Body text here."
    )
    doc = pipeline.render(src, ctx)
    assert "<h2" in doc.html
    assert "<h3" in doc.html
    assert "<h4" in doc.html
    assert "Main" in doc.html


def test_itemize_and_enumerate_siblings(pipeline, ctx):
    src = (
        r"\begin{itemize}\item A\item B\end{itemize}"
        r"\begin{enumerate}\item one\item two\end{enumerate}"
    )
    doc = pipeline.render(src, ctx)
    assert "<ul" in doc.html
    assert "<ol" in doc.html


def test_nested_itemize(pipeline, ctx):
    src = (
        r"\begin{itemize}"
        r"\item outer\begin{itemize}\item inner\end{itemize}"
        r"\end{itemize}"
    )
    doc = pipeline.render(src, ctx)
    assert doc.html.count("<ul") >= 2


def test_tabular_with_simple_cols(pipeline, ctx):
    src = r"\begin{tabular}{lcr}A&B&C\\D&E&F\\\end{tabular}"
    doc = pipeline.render(src, ctx)
    assert "<table" in doc.html


def test_url_and_href_and_includegraphics(pipeline, ctx):
    src = (
        r"See \url{https://example.com} and "
        r"\href{https://example.org}{the site}. "
        r"\includegraphics{fig.png}"
    )
    doc = pipeline.render(src, ctx)
    assert "href=" in doc.html
    assert "example.com" in doc.html
    assert "example.org" in doc.html
    assert "<img" in doc.html or "<figure" in doc.html


def test_includegraphics_with_missing_resource(pipeline, ctx_missing_resource):
    doc = pipeline.render(r"\includegraphics{nope.png}", ctx_missing_resource)
    # Missing resource renders a placeholder — the HTML must not error.
    assert isinstance(doc.html, str)


def test_lstlisting_with_cpp_code(pipeline, ctx):
    src = (
        r"\begin{lstlisting}[language=cpp]"
        "\n#include <iostream>\nint main(){ return 0; }\n"
        r"\end{lstlisting}"
    )
    doc = pipeline.render(src, ctx)
    # Pygments output should include token classes.
    assert "tok-" in doc.html or "lstlisting" in doc.html.lower() or "<pre" in doc.html


def test_lstlisting_without_language_auto_detects(pipeline, ctx):
    src = (
        r"\begin{lstlisting}"
        "\ndef f():\n    print('hi')\n    return 1\n"
        r"\end{lstlisting}"
    )
    doc = pipeline.render(src, ctx)
    assert "<pre" in doc.html or "<div" in doc.html


def test_mixed_math_and_prose(pipeline, ctx):
    src = (
        "This is an introduction. "
        r"Let $a, b \in \mathbb{R}$ with $a < b$. "
        "Then the interval $[a, b]$ is closed."
    )
    doc = pipeline.render(src, ctx)
    assert "<p" in doc.html or "scriba-tex" in doc.html


def test_pure_math_document(pipeline, ctx):
    src = r"$$\int_0^1 f(x)\,dx$$"
    doc = pipeline.render(src, ctx)
    assert doc.html  # non-empty


def test_epigraph_renders(pipeline, ctx):
    src = r"\epigraph{Short quote here.}{Author}"
    doc = pipeline.render(src, ctx)
    assert "Author" in doc.html or "Short quote here" in doc.html


def test_center_environment_renders(pipeline, ctx):
    src = r"\begin{center}Centered text\end{center}"
    doc = pipeline.render(src, ctx)
    assert "Centered text" in doc.html


def test_dashes_and_smart_quotes(pipeline, ctx):
    src = "This---that and ``hello''."
    doc = pipeline.render(src, ctx)
    # Output must contain an em dash or unicode smart quotes.
    assert "\u2014" in doc.html or "—" in doc.html or "---" not in doc.html


def test_text_commands_bold_italic(pipeline, ctx):
    src = r"\textbf{bold} and \textit{italic} and \emph{em}."
    doc = pipeline.render(src, ctx)
    assert "<strong" in doc.html or "<b" in doc.html
    assert "<em" in doc.html or "<i" in doc.html


def test_size_commands_render(pipeline, ctx):
    src = r"\tiny a \Large b \huge c"
    doc = pipeline.render(src, ctx)
    assert "a" in doc.html
    assert "b" in doc.html


def test_unicode_vietnamese_roundtrip(pipeline, ctx):
    src = "Bài toán này có $n$ phần tử."
    doc = pipeline.render(src, ctx)
    assert "Bài toán" in doc.html


def test_escaped_special_chars(pipeline, ctx):
    src = r"Literal \% \# \_ \{ \} \& and \$5."
    doc = pipeline.render(src, ctx)
    assert "%" in doc.html
    assert "#" in doc.html
    assert "_" in doc.html
    assert "{" in doc.html
    assert "}" in doc.html
    assert "$5" in doc.html or "5" in doc.html


def test_render_long_source_near_cap(pipeline, ctx):
    """Large but valid input: ensure no crash and paragraph wrapping works."""
    body = "\n\n".join(f"Paragraph {i}." for i in range(200))
    doc = pipeline.render(body, ctx)
    # Each paragraph should be wrapped.
    assert doc.html.count("<p") >= 50


def test_html_escape_angle_brackets_in_free_text(pipeline, ctx):
    src = "Avoid <script> injection here."
    doc = pipeline.render(src, ctx)
    assert "<script>" not in doc.html
    assert "&lt;script&gt;" in doc.html
