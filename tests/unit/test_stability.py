"""Pin the locked contracts documented in ``STABILITY.md``.

These tests fail loudly if any locked contract drifts. Updating them
requires a matching update to ``STABILITY.md``, ``CHANGELOG.md`` (under
a ``BREAKING`` heading), and usually a MAJOR version bump.
"""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path

import pytest

from scriba import (
    ALLOWED_ATTRS,
    ALLOWED_TAGS,
    Document,
    Pipeline,
    Renderer,
    RendererAssets,
    RenderArtifact,
    SCRIBA_VERSION,
)


# ---------------------------------------------------------------------------
# Document shape
# ---------------------------------------------------------------------------


EXPECTED_DOCUMENT_FIELDS: frozenset[str] = frozenset(
    {
        "html",
        "required_css",
        "required_js",
        "versions",
        "block_data",
        "required_assets",
    }
)


def test_document_is_a_dataclass() -> None:
    assert dataclasses.is_dataclass(Document)


def test_document_fields_match_snapshot() -> None:
    names = frozenset(f.name for f in dataclasses.fields(Document))
    assert names == EXPECTED_DOCUMENT_FIELDS, (
        f"Document.fields drift: got {names}, expected "
        f"{EXPECTED_DOCUMENT_FIELDS}"
    )


def test_document_fields_have_expected_types() -> None:
    by_name = {f.name: f for f in dataclasses.fields(Document)}
    # Only the rough "shape" is asserted — typing.get_type_hints() would
    # require forward-ref resolution with __future__.annotations.
    assert by_name["html"].type == "str"
    assert "frozenset" in by_name["required_css"].type
    assert "frozenset" in by_name["required_js"].type
    assert "Mapping" in by_name["versions"].type
    assert "Mapping" in by_name["block_data"].type
    assert "Mapping" in by_name["required_assets"].type


def test_document_is_frozen() -> None:
    doc = Document(
        html="",
        required_css=frozenset(),
        required_js=frozenset(),
        versions={"core": SCRIBA_VERSION},
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        doc.html = "mutated"  # type: ignore[misc]


def test_document_new_fields_default_empty() -> None:
    doc = Document(
        html="<p>ok</p>",
        required_css=frozenset(),
        required_js=frozenset(),
        versions={"core": SCRIBA_VERSION},
    )
    assert doc.block_data == {}
    assert doc.required_assets == {}


# ---------------------------------------------------------------------------
# Asset namespace format
# ---------------------------------------------------------------------------


def test_required_css_keys_use_namespace_separator(pipeline, ctx) -> None:
    """Real renderers must produce namespaced keys of the form
    ``<renderer>/<basename>``.
    """
    doc = pipeline.render("plain text", ctx)

    assert doc.required_css, "TeX renderer should always ship CSS"
    for key in doc.required_css:
        assert "/" in key, f"required_css key {key!r} missing namespace"
        prefix, _, basename = key.partition("/")
        assert prefix == "tex", f"unexpected namespace prefix: {prefix!r}"
        assert basename, "basename must not be empty"
        assert "/" not in basename, "basename must not contain separators"


def test_required_assets_keys_match_required_css_js(pipeline, ctx) -> None:
    doc = pipeline.render("plain text", ctx)

    for key in doc.required_css | doc.required_js:
        assert key in doc.required_assets, (
            f"{key!r} missing from Document.required_assets"
        )
        assert isinstance(doc.required_assets[key], Path)


# ---------------------------------------------------------------------------
# SCRIBA_VERSION
# ---------------------------------------------------------------------------


def test_scriba_version_is_positive_int() -> None:
    assert isinstance(SCRIBA_VERSION, int)
    assert SCRIBA_VERSION >= 2


# ---------------------------------------------------------------------------
# Renderer protocol
# ---------------------------------------------------------------------------


def test_renderer_protocol_has_required_attributes() -> None:
    # Protocol attributes are expressed as annotated class members on the
    # Protocol subclass. Verify the names are present.
    annotations = getattr(Renderer, "__annotations__", {})
    for name in ("name", "version", "priority"):
        assert name in annotations, f"Renderer protocol missing {name!r}"


def test_renderer_priority_default_is_100_for_renderer_without_attr() -> None:
    """Pipeline must treat a renderer missing ``priority`` as 100.

    The default is enforced by ``getattr(renderer, 'priority', 100)`` in
    the Pipeline's overlap resolver. This test pins the literal value.
    """
    import inspect

    import scriba.core.pipeline as pipeline_mod

    src = inspect.getsource(pipeline_mod)
    # The literal '100' must appear next to a getattr(..., 'priority', ...)
    # call. We assert presence rather than exact surrounding whitespace.
    assert "getattr(renderer, \"priority\", 100)" in src, (
        "Pipeline no longer defaults Renderer.priority to 100"
    )


# ---------------------------------------------------------------------------
# ALLOWED_TAGS / ALLOWED_ATTRS
# ---------------------------------------------------------------------------


def test_allowed_tags_is_frozenset_of_strings() -> None:
    assert isinstance(ALLOWED_TAGS, frozenset)
    assert ALLOWED_TAGS, "ALLOWED_TAGS must not be empty"
    for tag in ALLOWED_TAGS:
        assert isinstance(tag, str) and tag


def test_allowed_attrs_values_are_frozensets() -> None:
    for tag, attrs in ALLOWED_ATTRS.items():
        assert isinstance(tag, str)
        assert isinstance(attrs, frozenset), (
            f"ALLOWED_ATTRS[{tag!r}] must be frozenset"
        )


# ---------------------------------------------------------------------------
# SVG scene ID format — scriba-<sha256[:10]>
# ---------------------------------------------------------------------------


def test_animation_scene_id_format_is_locked() -> None:
    """The animation scene ID must remain ``scriba-<sha256[:10]>``.

    Consumer CSS / JS that targets `#scriba-<hash>` breaks if this
    format changes. See STABILITY.md §SVG scene ID format.
    """
    from scriba.animation.renderer import _scene_id

    raw = "\\begin{animation}[id=test]\\end{animation}"
    sid = _scene_id(raw)
    assert sid.startswith("scriba-")
    suffix = sid[len("scriba-"):]
    assert len(suffix) == 10
    # Must match the first 10 chars of sha256 of the raw bytes.
    expected = hashlib.sha256(raw.encode()).hexdigest()[:10]
    assert suffix == expected


# ---------------------------------------------------------------------------
# RendererAssets shape (indirectly pins the Renderer.assets() return type)
# ---------------------------------------------------------------------------


def test_renderer_assets_fields() -> None:
    names = frozenset(f.name for f in dataclasses.fields(RendererAssets))
    assert names == frozenset({"css_files", "js_files"})


# ---------------------------------------------------------------------------
# RenderArtifact carries both block_id and data (0.1.1 additions)
# ---------------------------------------------------------------------------


def test_render_artifact_fields_include_block_id_and_data() -> None:
    names = frozenset(f.name for f in dataclasses.fields(RenderArtifact))
    assert "block_id" in names
    assert "data" in names
    assert "inline_data" in names
    assert "css_assets" in names
    assert "js_assets" in names
    assert "html" in names
