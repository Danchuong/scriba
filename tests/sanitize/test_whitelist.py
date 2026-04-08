"""Structural checks on ALLOWED_TAGS / ALLOWED_ATTRS plus a bleach roundtrip.

See docs/scriba/01-architecture.md §Sanitization and 03-diagram-plugin.md §11.
"""

from __future__ import annotations

from typing import Mapping

import pytest

from scriba import ALLOWED_ATTRS, ALLOWED_TAGS, RenderContext


def test_allowed_tags_is_frozenset():
    assert isinstance(ALLOWED_TAGS, frozenset)


def test_allowed_tags_contains_math_tags():
    for tag in ("math", "semantics", "mrow", "mi", "mo", "mn", "msub", "msup"):
        assert tag in ALLOWED_TAGS, f"missing math tag: {tag}"


def test_allowed_tags_contains_svg_tags():
    for tag in ("svg", "g", "path", "circle", "rect", "polygon", "ellipse"):
        assert tag in ALLOWED_TAGS, f"missing svg tag: {tag}"


def test_allowed_attrs_is_mapping():
    assert isinstance(ALLOWED_ATTRS, Mapping)


def test_allowed_attrs_wildcard_has_class_id():
    wildcard = ALLOWED_ATTRS.get("*", frozenset())
    assert "class" in wildcard
    assert "id" in wildcard
    # The current scaffold scopes "style" to specific tags rather than
    # the wildcard. Verify it appears at least on div and span.
    assert "style" in ALLOWED_ATTRS["div"]
    assert "style" in ALLOWED_ATTRS["span"]


def test_allowed_attrs_data_step_on_widget_tags():
    for tag in ("div", "figure", "g"):
        assert "data-step" in ALLOWED_ATTRS[tag], f"data-step missing on {tag}"


def test_bleach_roundtrip_inline_math(pipeline):
    bleach = pytest.importorskip("bleach")
    ctx = RenderContext(resource_resolver=lambda n: None)
    doc = pipeline.render(r"$x^2$", ctx)
    safe = bleach.clean(
        doc.html,
        tags=set(ALLOWED_TAGS),
        attributes={k: list(v) for k, v in ALLOWED_ATTRS.items()},
        strip=True,
    )
    assert "katex" in safe
    assert "<script" not in safe.lower()
