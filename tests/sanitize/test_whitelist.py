"""Structural checks on ALLOWED_TAGS / ALLOWED_ATTRS plus a bleach roundtrip.

See docs/scriba/01-architecture.md §Sanitization and 03-diagram-plugin.md §11.
"""

from __future__ import annotations

from typing import Mapping

import pytest

from scriba import ALLOWED_ATTRS, ALLOWED_TAGS, RenderContext


# ---------------------------------------------------------------------------
# Contract-stability snapshots (Agent 15, finding 15-L1)
#
# These snapshots lock the exact membership of ALLOWED_TAGS and ALLOWED_ATTRS
# so any accidental removal (or silent addition) forces a deliberate commit
# that updates this file. Treat a failure here as a prompt to audit the
# emitter <-> sanitizer contract, not as a reason to loosen the test.
# ---------------------------------------------------------------------------


EXPECTED_ALLOWED_TAGS: frozenset[str] = frozenset({
    # Text formatting
    "p", "br", "strong", "b", "em", "i", "u", "s", "del",
    "sub", "sup", "small", "span",
    # Headings
    "h1", "h2", "h3", "h4", "h5", "h6",
    # Lists
    "ul", "ol", "li",
    # Links and media
    "a", "img",
    # Code
    "pre", "code",
    # Tables
    "table", "thead", "tbody", "tr", "th", "td",
    # Block
    "div", "blockquote", "hr", "figure", "figcaption", "footer",
    # Interactive
    "button",
    # MathML (KaTeX output)
    "math", "semantics", "mrow", "mi", "mo", "mn", "ms", "mtext", "mspace",
    "msub", "msup", "msubsup", "mfrac", "msqrt", "mroot",
    "mover", "munder", "munderover",
    "mtable", "mtr", "mtd", "mstyle", "menclose", "mpadded", "mphantom",
    "merror",
    "annotation", "annotation-xml",
    # SVG base
    "svg", "path", "line", "rect", "circle", "g", "defs", "use", "clipPath",
    "polyline", "text", "marker",
    # SVG diagram additions
    "polygon", "ellipse", "tspan", "mask", "pattern",
    "foreignObject", "desc", "title",
})


EXPECTED_ALLOWED_ATTR_KEYS: frozenset[str] = frozenset({
    "*", "a", "annotation", "annotation-xml", "button", "circle",
    "clipPath", "code", "defs", "desc", "div", "ellipse", "figure",
    "foreignObject", "g", "img", "line", "marker", "mask", "math",
    "menclose", "mo", "mspace", "mstyle", "mtable", "mtd", "mtr",
    "path", "pattern", "polygon", "polyline", "pre", "rect", "span",
    "svg", "table", "td", "text", "th", "title", "tspan", "use",
})


EXPECTED_ALLOWED_ATTRS: Mapping[str, frozenset[str]] = {
    "*": frozenset({
        "class", "id", "title", "lang", "dir", "role",
        "aria-hidden", "aria-label", "aria-labelledby", "aria-describedby",
        "tabindex",
    }),
    "div": frozenset({
        "class", "id", "style",
        "data-step", "data-step-current", "data-step-count", "data-step-mode",
        "data-scriba-frames",
    }),
    "figure": frozenset({
        "class", "id",
        "data-step", "data-step-current", "data-step-count", "data-step-mode",
        "data-scriba-scene", "data-frame-count", "data-layout",
        "aria-label",
    }),
    "span": frozenset({"class", "id", "style"}),
    "a": frozenset({"href", "target", "rel", "title"}),
    "img": frozenset({"src", "alt", "width", "height", "loading", "style"}),
    "pre": frozenset({"class", "data-code", "data-language"}),
    "code": frozenset({"class", "data-language"}),
    "button": frozenset({
        "type", "class", "data-code", "data-step-target", "aria-label",
    }),
    "table": frozenset({"class"}),
    "th": frozenset({"class", "colspan", "rowspan", "scope"}),
    "td": frozenset({"class", "colspan", "rowspan"}),
    "math": frozenset({"xmlns", "display"}),
    "annotation": frozenset({"encoding"}),
    "annotation-xml": frozenset({"encoding"}),
    "mo": frozenset({
        "fence", "stretchy", "symmetric", "lspace", "rspace",
        "minsize", "maxsize", "accent",
    }),
    "mspace": frozenset({"width"}),
    "mtable": frozenset({
        "columnalign", "rowalign", "columnspacing", "rowspacing",
        "columnlines", "rowlines", "frame",
    }),
    "mtr": frozenset({"columnalign", "rowalign"}),
    "mtd": frozenset({"columnalign", "rowalign"}),
    "menclose": frozenset({"notation"}),
    "mstyle": frozenset({"displaystyle", "scriptlevel", "mathvariant"}),
    "svg": frozenset({
        "viewBox", "xmlns", "xmlns:xlink", "width", "height",
        "fill", "focusable", "preserveAspectRatio",
        "role", "aria-labelledby",
    }),
    "path": frozenset({
        "d", "fill", "stroke", "stroke-width", "stroke-dasharray",
        "stroke-linecap", "stroke-linejoin",
        "fill-opacity", "stroke-opacity", "opacity",
        "transform", "clip-path", "mask",
        "marker-start", "marker-mid", "marker-end",
        "data-step",
    }),
    "line": frozenset({
        "x1", "y1", "x2", "y2",
        "stroke", "stroke-width", "stroke-linecap", "stroke-dasharray",
        "opacity", "stroke-opacity",
        "marker-start", "marker-mid", "marker-end",
        "data-step",
    }),
    "rect": frozenset({
        "x", "y", "width", "height", "rx", "ry",
        "fill", "stroke", "stroke-width",
        "fill-opacity", "stroke-opacity", "opacity",
        "transform", "clip-path", "mask",
        "data-step",
    }),
    "circle": frozenset({
        "cx", "cy", "r",
        "fill", "stroke", "stroke-width",
        "fill-opacity", "stroke-opacity", "opacity",
        "transform", "data-step",
    }),
    "ellipse": frozenset({
        "cx", "cy", "rx", "ry",
        "fill", "stroke", "stroke-width",
        "fill-opacity", "stroke-opacity", "opacity",
        "transform", "data-step",
    }),
    "g": frozenset({
        "transform", "fill", "stroke", "clip-path", "mask", "opacity",
        "data-step", "data-scriba-action", "data-target",
    }),
    "defs": frozenset(),
    "use": frozenset({"href", "xlink:href", "x", "y", "width", "height"}),
    "clipPath": frozenset({"id"}),
    "mask": frozenset({"id"}),
    "pattern": frozenset({
        "id", "x", "y", "width", "height", "patternUnits",
    }),
    "polyline": frozenset({
        "points", "fill", "stroke", "stroke-width",
        "stroke-linecap", "stroke-linejoin", "stroke-dasharray",
        "fill-opacity", "stroke-opacity", "opacity",
        "marker-start", "marker-mid", "marker-end",
        "data-step",
    }),
    "polygon": frozenset({
        "points", "fill", "stroke", "stroke-width",
        "stroke-linecap", "stroke-linejoin",
        "fill-opacity", "stroke-opacity", "opacity",
        "data-step",
    }),
    "text": frozenset({
        "x", "y", "fill", "font-family", "font-size", "font-weight",
        "text-anchor", "dominant-baseline",
        "opacity", "transform", "data-step",
    }),
    "tspan": frozenset({
        "x", "y", "dx", "dy", "fill", "font-family", "font-size",
        "font-weight", "text-anchor",
    }),
    "marker": frozenset({
        "id", "viewBox", "refX", "refY",
        "markerWidth", "markerHeight", "orient",
    }),
    "foreignObject": frozenset({
        "x", "y", "width", "height", "transform", "data-step",
    }),
    "desc": frozenset(),
    "title": frozenset(),
}


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


# ---------------------------------------------------------------------------
# Contract stability: snapshot assertions (Agent 15 / finding 15-L1).
# ---------------------------------------------------------------------------


def test_allowed_tags_membership_locked():
    """Lock the exact ALLOWED_TAGS set.

    Any diff here is a deliberate sanitizer contract change and must be
    approved by updating ``EXPECTED_ALLOWED_TAGS`` in this file.
    """
    assert ALLOWED_TAGS == EXPECTED_ALLOWED_TAGS, (
        "ALLOWED_TAGS changed — added: "
        f"{sorted(ALLOWED_TAGS - EXPECTED_ALLOWED_TAGS)}, "
        "removed: "
        f"{sorted(EXPECTED_ALLOWED_TAGS - ALLOWED_TAGS)}"
    )


def test_allowed_attrs_keys_locked():
    """Lock the set of tags that have per-tag attribute entries."""
    actual_keys = frozenset(ALLOWED_ATTRS.keys())
    assert actual_keys == EXPECTED_ALLOWED_ATTR_KEYS, (
        "ALLOWED_ATTRS keys changed — added: "
        f"{sorted(actual_keys - EXPECTED_ALLOWED_ATTR_KEYS)}, "
        "removed: "
        f"{sorted(EXPECTED_ALLOWED_ATTR_KEYS - actual_keys)}"
    )


@pytest.mark.parametrize("tag", sorted(EXPECTED_ALLOWED_ATTR_KEYS))
def test_allowed_attrs_values_locked(tag: str):
    """Lock the exact attribute set for each allowlisted tag."""
    actual = frozenset(ALLOWED_ATTRS[tag])
    expected = EXPECTED_ALLOWED_ATTRS[tag]
    assert actual == expected, (
        f"ALLOWED_ATTRS[{tag!r}] changed — added: "
        f"{sorted(actual - expected)}, removed: "
        f"{sorted(expected - actual)}"
    )


# ---------------------------------------------------------------------------
# Roundtrip tests for the emitter <-> sanitizer contract
# (06-C1 / 06-H1 / 06-M1). These confirm that the newly allowlisted
# data-/aria- attributes survive a realistic bleach invocation and that
# they do NOT enable a known XSS bypass.
# ---------------------------------------------------------------------------


def _bleach_clean(html: str):
    bleach = pytest.importorskip("bleach")
    return bleach.clean(
        html,
        tags=set(ALLOWED_TAGS),
        attributes={k: list(v) for k, v in ALLOWED_ATTRS.items()},
        strip=True,
    )


def test_bleach_preserves_figure_scriba_data_attrs():
    """06-C1: figure metadata (scene, frame-count, layout, aria-label)."""
    html = (
        '<figure class="scriba-animation" '
        'data-scriba-scene="s1" '
        'data-frame-count="5" '
        'data-layout="filmstrip" '
        'aria-label="Demo">content</figure>'
    )
    out = _bleach_clean(html)
    assert 'data-scriba-scene="s1"' in out
    assert 'data-frame-count="5"' in out
    assert 'data-layout="filmstrip"' in out
    assert 'aria-label="Demo"' in out


def test_bleach_preserves_substory_widget_frames_attr():
    """06-H1: substory widget JSON payload attribute."""
    html = (
        '<div class="scriba-substory-widget" '
        'data-scriba-frames="[{&quot;step&quot;:1}]">x</div>'
    )
    out = _bleach_clean(html)
    assert "data-scriba-frames=" in out
    assert "scriba-substory-widget" in out


def test_bleach_preserves_svg_aria_labelledby():
    """06-C1 (second part): main <svg> accessibility hook."""
    html = (
        '<svg class="scriba-stage-svg" viewBox="0 0 10 10" role="img" '
        'aria-labelledby="frame-1-narration" '
        'xmlns="http://www.w3.org/2000/svg"></svg>'
    )
    out = _bleach_clean(html)
    assert 'aria-labelledby="frame-1-narration"' in out
    assert 'role="img"' in out


def test_bleach_preserves_g_data_target():
    """06-M1: primitive shape-group selector."""
    html = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g data-target="arr.cell.3" class="scriba-state-active">'
        '<rect x="0" y="0" width="10" height="10"></rect>'
        '</g></svg>'
    )
    out = _bleach_clean(html)
    assert 'data-target="arr.cell.3"' in out
    assert "scriba-state-active" in out


# ---------------------------------------------------------------------------
# XSS hardening: new attributes MUST NOT enable a bypass.
# ---------------------------------------------------------------------------


def test_new_attrs_do_not_enable_script_injection():
    """Even with the new attrs allowlisted, <script> must still be stripped."""
    html = (
        '<figure data-scriba-scene="s1" data-layout="filmstrip">'
        '<script>alert(1)</script>'
        '<div data-scriba-frames="x">'
        '<svg aria-labelledby="n"><g data-target="t">'
        '<script>alert(2)</script>'
        '</g></svg>'
        '</div>'
        '</figure>'
    )
    out = _bleach_clean(html)
    # No script tags survive bleach even with our additions in place.
    # (bleach with strip=True leaves the inner text as plain text, which
    # is not executable — we only need to prove the <script> element is
    # gone.)
    assert "<script" not in out.lower()
    assert "</script" not in out.lower()
    # Sanity-check that the new attrs still survive in the same document.
    assert 'data-scriba-scene="s1"' in out
    assert 'data-layout="filmstrip"' in out
    assert 'data-scriba-frames="x"' in out
    assert 'aria-labelledby="n"' in out
    assert 'data-target="t"' in out


def test_new_attrs_do_not_allow_event_handlers():
    """on*= handlers must still be stripped on elements carrying new attrs."""
    html = (
        '<figure data-scriba-scene="s1" onload="alert(1)">x</figure>'
        '<div data-scriba-frames="[]" onclick="alert(1)">y</div>'
        '<svg aria-labelledby="n" onload="alert(1)"></svg>'
        '<g data-target="t" onmouseover="alert(1)"></g>'
    )
    out = _bleach_clean(html)
    assert "onload" not in out
    assert "onclick" not in out
    assert "onmouseover" not in out
    assert "alert(" not in out
    # Sanity-check that the legitimate new attrs still made it through.
    assert "data-scriba-scene" in out
    assert "data-scriba-frames" in out
    assert "aria-labelledby" in out
    assert "data-target" in out
