"""Public API surface tests for TexRenderer.

Locks: name, version, kwarg-only constructor, context-manager protocol,
idempotent close, asset basenames, single-block detect.
"""

from __future__ import annotations

import pytest

from scriba import SubprocessWorkerPool
from scriba.tex import TexRenderer


def test_name_is_tex():
    assert TexRenderer.name == "tex"


def test_version_is_int():
    assert TexRenderer.version == 1
    assert isinstance(TexRenderer.version, int)


def test_constructor_requires_worker_pool():
    with pytest.raises(TypeError):
        TexRenderer()  # type: ignore[call-arg]


def test_constructor_all_kwargs_only():
    pool = object()
    with pytest.raises(TypeError):
        TexRenderer(pool)  # type: ignore[misc]


def test_context_manager(worker_pool):
    with TexRenderer(worker_pool=worker_pool) as r:
        assert r is not None
        assert r.name == "tex"


def test_close_idempotent(worker_pool):
    r = TexRenderer(worker_pool=worker_pool)
    r.close()
    r.close()  # second call must not raise


def test_assets_returns_expected_files(tex_renderer):
    a = tex_renderer.assets()
    css_basenames = {p.name for p in a.css_files}
    js_basenames = {p.name for p in a.js_files}
    assert "scriba-tex-content.css" in css_basenames
    assert "scriba-tex-pygments-light.css" in css_basenames
    assert "scriba-tex-copy.js" in js_basenames


def test_detect_returns_full_document_block(tex_renderer):
    source = "Some \\textbf{content} with $x^2$."
    blocks = tex_renderer.detect(source)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.start == 0
    assert b.end == len(source)
    assert b.kind == "tex"
    assert b.raw == source
