"""Shared fixtures for the Scriba Phase 2 RED test suite.

These fixtures intentionally exercise the real construction path. Because
Phase 1A scaffolds raise ``NotImplementedError`` from ``__init__``, every
fixture below will error at session setup; that propagates as ERROR rows in
the pytest report and counts as our RED signal until sub-phases 2b/2c/2d
land the implementations.
"""

from __future__ import annotations

import pytest

from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer


@pytest.fixture(scope="session")
def worker_pool():
    pool = SubprocessWorkerPool()
    try:
        yield pool
    finally:
        pool.close()


@pytest.fixture(scope="session")
def tex_renderer(worker_pool):
    r = TexRenderer(worker_pool=worker_pool, pygments_theme="one-light")
    try:
        yield r
    finally:
        r.close()


@pytest.fixture(scope="session")
def tex_renderer_no_highlight(worker_pool):
    r = TexRenderer(worker_pool=worker_pool, pygments_theme="none")
    try:
        yield r
    finally:
        r.close()


@pytest.fixture(scope="session")
def tex_renderer_with_macros(worker_pool):
    r = TexRenderer(
        worker_pool=worker_pool,
        pygments_theme="one-light",
        katex_macros={r"\RR": r"\mathbb{R}"},
    )
    try:
        yield r
    finally:
        r.close()


@pytest.fixture(scope="session")
def pipeline(tex_renderer):
    p = Pipeline([tex_renderer])
    try:
        yield p
    finally:
        p.close()


@pytest.fixture(scope="session")
def pipeline_no_highlight(tex_renderer_no_highlight):
    p = Pipeline([tex_renderer_no_highlight])
    try:
        yield p
    finally:
        p.close()


@pytest.fixture(scope="session")
def pipeline_with_macros(tex_renderer_with_macros):
    p = Pipeline([tex_renderer_with_macros])
    try:
        yield p
    finally:
        p.close()


@pytest.fixture
def ctx():
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={},
        render_inline_tex=None,
    )


@pytest.fixture
def ctx_missing_resource():
    return RenderContext(
        resource_resolver=lambda name: None,
        theme="light",
        dark_mode=False,
        metadata={},
        render_inline_tex=None,
    )
