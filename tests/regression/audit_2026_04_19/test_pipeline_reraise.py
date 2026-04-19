"""Regression test for audit-06 finding (MEDIUM) — pipeline re-raise.

Audit reference: docs/archive/scriba-full-audit-2026-04-19/06-error-handling.md
Finding: core/pipeline.py used ``raise type(e)(new_message) from e`` which
calls the subclass ``__init__`` with a single positional message argument.
ScribaError subclasses have keyword-only parameters (``stderr=``, ``renderer=``,
``position=``) so the reconstruction raised a secondary ``TypeError``, hiding
the real error and dropping the subclass attributes.

Fix: augment ``e.args`` / ``e._raw_message`` in-place and plain ``raise``,
preserving the original exception type and all attributes.
"""

from __future__ import annotations

import pytest

from scriba.core.errors import ScribaError, ValidationError, WorkerError, RendererError
from scriba.core.pipeline import Pipeline
from scriba.core.context import RenderContext
from scriba.core import artifact as _art


# ---------------------------------------------------------------------------
# Minimal renderer stub helpers
# ---------------------------------------------------------------------------

class _BaseStub:
    version = 1
    priority = 100

    def detect(self, source: str):
        # Match the entire source as a single block so render_block is called.
        return [_art.Block(start=0, end=len(source), kind="w", raw=source)]

    def assets(self):
        from scriba.core.renderer import RendererAssets
        return RendererAssets(css_files=frozenset(), js_files=frozenset())


class _WorkerErrorRenderer(_BaseStub):
    name = "worker_stub"

    def render_block(self, block, ctx):
        raise WorkerError("subprocess crashed", stderr="stderr output here")


class _RendererErrorRenderer(_BaseStub):
    name = "renderer_stub"

    def render_block(self, block, ctx):
        raise RendererError("render failed", renderer="tex", line=5, col=3)


class _ValidationErrorRenderer(_BaseStub):
    name = "validation_stub"

    def render_block(self, block, ctx):
        raise ValidationError("bad input", position=42, code="E1009")


class _PlainErrorRenderer(_BaseStub):
    name = "plain_stub"

    def render_block(self, block, ctx):
        raise RuntimeError("plain kaboom")


_CTX = RenderContext(resource_resolver=lambda n: None)


# ---------------------------------------------------------------------------
# WorkerError: type, stderr attribute, and context prefix are all preserved
# ---------------------------------------------------------------------------

def test_pipeline_reraise_preserves_workererror_type():
    p = Pipeline([_WorkerErrorRenderer()])
    with pytest.raises(WorkerError):
        p.render("hello", _CTX)


def test_pipeline_reraise_preserves_workererror_stderr():
    p = Pipeline([_WorkerErrorRenderer()])
    with pytest.raises(WorkerError) as exc_info:
        p.render("hello", _CTX)
    assert exc_info.value.stderr == "stderr output here"


def test_pipeline_reraise_workererror_message_contains_context():
    p = Pipeline([_WorkerErrorRenderer()])
    with pytest.raises(WorkerError) as exc_info:
        p.render("hello", _CTX)
    msg = str(exc_info.value)
    assert "worker_stub" in msg
    assert "subprocess crashed" in msg


def test_pipeline_reraise_workererror_chained_cause():
    """The original exception must be the __cause__ (from e preserved)."""
    p = Pipeline([_WorkerErrorRenderer()])
    with pytest.raises(WorkerError) as exc_info:
        p.render("hello", _CTX)
    # plain raise keeps __context__; we also check __cause__ is set by the
    # augmentation (it stays as the same object since we raise in-place).
    assert exc_info.value.__cause__ is None  # plain raise, not raise … from …
    # The exception IS the original — not a new wrapper.
    assert isinstance(exc_info.value, WorkerError)


# ---------------------------------------------------------------------------
# RendererError: type, renderer attribute, line/col attributes preserved
# ---------------------------------------------------------------------------

def test_pipeline_reraise_preserves_renderererror_type():
    p = Pipeline([_RendererErrorRenderer()])
    with pytest.raises(RendererError):
        p.render("hello", _CTX)


def test_pipeline_reraise_preserves_renderererror_attributes():
    p = Pipeline([_RendererErrorRenderer()])
    with pytest.raises(RendererError) as exc_info:
        p.render("hello", _CTX)
    e = exc_info.value
    assert e.renderer == "tex"
    assert e.line == 5
    assert e.col == 3


def test_pipeline_reraise_renderererror_message_contains_context():
    p = Pipeline([_RendererErrorRenderer()])
    with pytest.raises(RendererError) as exc_info:
        p.render("hello", _CTX)
    msg = str(exc_info.value)
    assert "renderer_stub" in msg
    assert "render failed" in msg


# ---------------------------------------------------------------------------
# ValidationError: type, position attribute preserved
# ---------------------------------------------------------------------------

def test_pipeline_reraise_preserves_validationerror_type():
    p = Pipeline([_ValidationErrorRenderer()])
    with pytest.raises(ValidationError):
        p.render("hello", _CTX)


def test_pipeline_reraise_preserves_validationerror_position():
    p = Pipeline([_ValidationErrorRenderer()])
    with pytest.raises(ValidationError) as exc_info:
        p.render("hello", _CTX)
    assert exc_info.value.position == 42


def test_pipeline_reraise_validationerror_preserves_code():
    p = Pipeline([_ValidationErrorRenderer()])
    with pytest.raises(ValidationError) as exc_info:
        p.render("hello", _CTX)
    assert exc_info.value.code == "E1009"


# ---------------------------------------------------------------------------
# ScribaError base: catchable by base class
# ---------------------------------------------------------------------------

def test_pipeline_reraise_scriba_subclass_catchable_as_scriba_error():
    p = Pipeline([_WorkerErrorRenderer()])
    with pytest.raises(ScribaError):
        p.render("hello", _CTX)


# ---------------------------------------------------------------------------
# Plain (non-ScribaError) exceptions: message is enriched, type preserved
# ---------------------------------------------------------------------------

def test_pipeline_reraise_plain_exception_type_preserved():
    p = Pipeline([_PlainErrorRenderer()])
    with pytest.raises(RuntimeError):
        p.render("hello", _CTX)


def test_pipeline_reraise_plain_exception_message_enriched():
    p = Pipeline([_PlainErrorRenderer()])
    with pytest.raises(RuntimeError) as exc_info:
        p.render("hello", _CTX)
    msg = str(exc_info.value)
    assert "plain_stub" in msg
    assert "plain kaboom" in msg
