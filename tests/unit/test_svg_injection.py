"""SVG namespace attribute injection regression tests.

Covers audit finding 17-M3 (fuzz/regression adequacy) residuals that
were not captured by Cluster 7's sanitizer work.  The animation emitter
writes SVG with ``data-*`` attributes, ``aria-*`` labels, inline
``<text>`` elements, ``<title>``/``<desc>`` accessibility elements, and
attacker-controlled shape names / labels / narration can reach all of
those surfaces.

Written Wave 4A Cluster 9 to cover 17-M3 residuals.  Update when:

* The emitter gains new SVG attribute surfaces (add a test).
* The sanitizer allowlist (``scriba/sanitize/whitelist.py``) changes —
  verify that the dangerous attrs referenced here are still disallowed.
* A primitive's label rendering path is refactored.

The strategy is "defence in depth": each test threads an attacker
payload through a primitive label / narration / shape name, renders
through the emitter, and asserts either:

1. the payload is HTML-escaped (no raw ``<``/``"``/``javascript:``), or
2. the payload is allowed through but relies on the downstream
   bleach pass (tag/attr allowlist) to strip the dangerous bit —
   in that case the test asserts the tag/attr is not on the allowlist.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.emitter import (
    FrameData,
    emit_animation_html,
    emit_html,
    emit_interactive_html,
)
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.tree import Tree
from scriba.animation.renderer import AnimationRenderer
from scriba.core.artifact import Block
from scriba.core.context import RenderContext
from scriba.sanitize.whitelist import ALLOWED_ATTRS, ALLOWED_TAGS


def _ctx(mode: str = "static") -> RenderContext:
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        theme="light",
        dark_mode=False,
        metadata={"output_mode": mode},
        render_inline_tex=None,
    )


def _render(source: str, mode: str = "static") -> str:
    renderer = AnimationRenderer()
    full = f"\\begin{{animation}}\n{source}\n\\end{{animation}}"
    block = Block(start=0, end=len(full), kind="animation", raw=full)
    return renderer.render_block(block, _ctx(mode)).html


def _frame(
    *,
    step: int = 1,
    total: int = 1,
    narration: str = "",
    shape_states: dict | None = None,
    label: str | None = None,
) -> FrameData:
    return FrameData(
        step_number=step,
        total_frames=total,
        narration_html=narration,
        shape_states=shape_states or {},
        annotations=[],
        label=label,
    )


class TestSvgAttributeBreakout:
    """Verify attacker cannot break out of an attribute value."""

    def test_array_caption_cannot_break_attr_with_double_quote(self) -> None:
        """A caption with ``foo" onclick="alert(1)`` must be escaped."""
        payload = 'foo" onclick="alert(1)'
        prim = ArrayPrimitive("a", {"size": 3, "label": payload})
        svg = prim.emit_svg()
        # The raw double quote must be escaped — otherwise it breaks the attr.
        assert 'onclick="alert(1)"' not in svg
        assert "&quot;" in svg or "&#34;" in svg

    def test_array_caption_cannot_inject_event_handler(self) -> None:
        payload = 'foo onload=alert(1)'
        prim = ArrayPrimitive("a", {"size": 3, "label": payload})
        svg = prim.emit_svg()
        # onload ends up as text content of a <text> element — that's fine
        # because <text> content is not executed. The critical check is
        # that it did not become an attribute of the surrounding element.
        assert "onload=" not in _strip_text_content(svg)

    def test_aria_label_escapes_attacker_quote(self) -> None:
        """Frame label → figure aria-label must be escaped."""
        payload = 'x" data-evil="1'
        html = emit_animation_html(
            "scriba-test",
            [_frame(label=payload)],
            {},
        )
        assert 'data-evil="1"' not in html
        assert "&quot;" in html


class TestSvgScriptInjection:
    """Verify no path lets the attacker inject an executable <script>."""

    def test_svg_script_element_in_array_label_is_escaped(self) -> None:
        payload = "<svg:script>alert(1)</svg:script>"
        prim = ArrayPrimitive("a", {"size": 3, "label": payload})
        svg = prim.emit_svg()
        assert "<svg:script>" not in svg
        assert "&lt;svg:script&gt;" in svg

    def test_html_script_element_in_graph_label_is_escaped(self) -> None:
        payload = "<script>alert(1)</script>"
        prim = Graph(
            "g",
            {
                "nodes": ["a", "b"],
                "edges": [["a", "b"]],
                "label": payload,
            },
        )
        svg = prim.emit_svg()
        assert "<script>" not in svg
        assert "&lt;script&gt;" in svg

    def test_script_tag_not_in_sanitizer_allowlist(self) -> None:
        """Defence in depth: script must never enter the allowlist."""
        assert "script" not in ALLOWED_TAGS

    def test_end_to_end_narration_with_script_is_safe(self) -> None:
        """Narration with raw ``</script>`` must not terminate the JS block
        emitted by the interactive widget."""
        html = _render(
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\narrate{</script><img src=x onerror=alert(1)>}",
            mode="interactive",
        )
        assert r"<\/script>" in html or "&lt;/script&gt;" in html
        # The literal ``</script>`` must NOT appear as a real tag that
        # terminates the widget's JS block.
        # Search for "</script>" that is NOT preceded by a backslash
        # (which would mean the backslash-escaped form).
        raw_close = [
            i for i in _all_positions(html, "</script>")
            if i == 0 or html[i - 1] != "\\"
        ]
        # Exactly one real closing tag for the widget's script.
        assert len(raw_close) <= 1


class TestForeignObjectInjection:
    """Verify <foreignObject> + XHTML script content cannot be injected."""

    def test_foreign_object_in_label_is_escaped(self) -> None:
        payload = (
            '<foreignObject><body xmlns="http://www.w3.org/1999/xhtml">'
            "<script>alert(1)</script></body></foreignObject>"
        )
        prim = ArrayPrimitive("a", {"size": 3, "label": payload})
        svg = prim.emit_svg()
        assert "<foreignObject>" not in svg
        assert "<body" not in svg

    def test_foreign_object_on_allowlist_but_has_no_dangerous_attrs(self) -> None:
        """foreignObject itself IS on the allowlist (diagram plugin needs
        it), but it must not accept script-enabling attributes."""
        assert "foreignObject" in ALLOWED_TAGS
        attrs = ALLOWED_ATTRS.get("foreignObject", frozenset())
        for bad in ("onload", "onclick", "onerror", "src"):
            assert bad not in attrs


class TestXlinkHrefJavascriptScheme:
    """Verify xlink:href cannot smuggle ``javascript:`` schemes."""

    def test_xlink_href_not_allowed_on_most_elements(self) -> None:
        """xlink:href is only on ``<use>`` in the allowlist. It should not
        appear on paths, rects, circles, or text."""
        for tag in ("path", "rect", "circle", "text", "g"):
            attrs = ALLOWED_ATTRS.get(tag, frozenset())
            assert "xlink:href" not in attrs
            assert "href" not in attrs

    def test_use_element_href_allowlist_does_not_validate_scheme(self) -> None:
        """<use href=...> is on the allowlist. Verify the sanitizer
        pipeline — not Scriba — is responsible for scheme validation.
        This test documents the boundary."""
        use_attrs = ALLOWED_ATTRS.get("use", frozenset())
        assert "href" in use_attrs
        assert "xlink:href" in use_attrs
        # Scriba itself does not emit <use> with attacker-controlled href,
        # so this is a "contract" test: if a future change introduces
        # such a path, a dedicated scheme check must accompany it.


class TestStyleAttributeInjection:
    """Verify style attributes cannot smuggle ``url(javascript:...)``."""

    def test_style_attr_only_on_safe_elements(self) -> None:
        """``style`` is only allowed on ``div``, ``span``, ``img``."""
        style_bearing = [
            tag for tag, attrs in ALLOWED_ATTRS.items() if "style" in attrs
        ]
        # No SVG elements should allow inline style — only the HTML
        # wrappers (div, span, img).
        svg_tags = {
            "svg", "path", "line", "rect", "circle", "g", "text",
            "polygon", "polyline", "ellipse", "tspan",
        }
        for tag in style_bearing:
            assert tag not in svg_tags, (
                f"tag {tag!r} unexpectedly allows style attribute"
            )

    def test_style_with_expression_function_is_not_in_svg_emit(self) -> None:
        """No primitive should emit ``expression(...)`` in its SVG output."""
        prim = ArrayPrimitive("a", {"size": 3, "label": "expression(alert(1))"})
        svg = prim.emit_svg()
        # Label appears as <text> content (safe) — just confirm it is
        # not inside a style attribute.
        assert 'style="expression' not in svg


class TestTitleAndDescTextContent:
    """Verify SVG <title>/<desc>/ARIA accessibility text cannot escape."""

    def test_close_title_tag_in_label_is_escaped(self) -> None:
        payload = "</title><script>alert(1)</script>"
        prim = Tree(
            "t",
            {
                "root": "A",
                "nodes": ["A", "B"],
                "edges": [["A", "B"]],
                "label": payload,
            },
        )
        svg = prim.emit_svg()
        assert "</title><script>" not in svg
        # Must contain the escaped form somewhere.
        assert "&lt;/title&gt;" in svg or "&lt;script&gt;" in svg

    def test_aria_label_on_svg_element_is_quote_escaped(self) -> None:
        """The emitter uses html.escape(quote=True) for aria-labelledby."""
        frame_label = 'x"><script>alert(1)</script>'
        html = emit_animation_html(
            "scriba-test",
            [_frame(label=frame_label)],
            {},
        )
        # Must not contain the raw close quote + angle bracket break.
        assert '"><script>' not in html


class TestEntityEncodedPayloads:
    """Verify entity-encoded script tags are not decoded back to live
    markup by the emitter."""

    def test_entity_encoded_script_stays_entity_encoded(self) -> None:
        payload = "&lt;script&gt;alert(1)&lt;/script&gt;"
        prim = ArrayPrimitive("a", {"size": 3, "label": payload})
        svg = prim.emit_svg()
        # ``&`` must be double-escaped so the text shows ``&amp;lt;``
        # rather than ``&lt;`` (which a browser would render as ``<``).
        assert "&amp;lt;script&amp;gt;" in svg

    def test_numeric_entity_script_is_not_unfolded(self) -> None:
        payload = "&#x3c;script&#x3e;alert(1)&#x3c;/script&#x3e;"
        prim = ArrayPrimitive("a", {"size": 3, "label": payload})
        svg = prim.emit_svg()
        # ``&`` must be escaped — no raw ``<`` should appear.
        assert "<script>" not in svg


class TestUnicodeFullwidthScriptSubstitutes:
    """Verify full-width Unicode chars are NOT special-cased as tag
    characters (the HTML parser only treats ASCII ``<`` as a tag start)."""

    def test_fullwidth_less_than_is_not_a_tag_start(self) -> None:
        """``U+FF1C`` (＜) is visually similar to ``<`` but is not a tag
        start in HTML. The emitter should pass it through as text."""
        payload = "\uff1cscript\uff1ealert(1)\uff1c/script\uff1e"
        prim = ArrayPrimitive("a", {"size": 3, "label": payload})
        svg = prim.emit_svg()
        # The full-width chars stay as Unicode text content — not escaped
        # to &lt; because they're not special.
        assert "\uff1cscript\uff1e" in svg
        # But the ASCII close tag must NOT appear.
        assert "<script>" not in svg

    def test_fullwidth_in_aria_label_is_quote_safe(self) -> None:
        payload = "\uff02><script>"  # full-width quote + ASCII tag
        html = emit_animation_html(
            "scriba-test",
            [_frame(label=payload)],
            {},
        )
        # Must escape the raw ASCII ``<`` because that IS a tag start.
        assert '"><script>' not in html.replace("\uff02", "")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _strip_text_content(svg: str) -> str:
    """Remove all ``<text>...</text>`` bodies so we can check attributes."""
    return re.sub(r"<text[^>]*>.*?</text>", "<text/>", svg, flags=re.DOTALL)


def _all_positions(haystack: str, needle: str) -> list[int]:
    positions: list[int] = []
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx < 0:
            return positions
        positions.append(idx)
        start = idx + 1
