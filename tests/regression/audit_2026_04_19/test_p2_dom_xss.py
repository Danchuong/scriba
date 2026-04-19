"""Regression tests for audit finding P2 — DOM XSS via innerHTML in scriba.js.

Audit finding: scriba/animation/static/scriba.js lines 54, 72-74.
Bug: ``narr.innerHTML = frames[i].narration`` and
     ``stage.innerHTML = frames[i].svg`` set innerHTML from server-supplied
     content.  If either field contains a ``<script>`` tag the browser will
     execute it, achieving DOM-XSS.

The renderer's ``_escape_js`` function currently escapes the closing
``</script>`` tag as ``<\\/script>`` to avoid breaking the outer
``<script>`` block, but leaves the opening ``<script>`` tag intact.
When the JS runtime sets ``narr.innerHTML = frames[i].narration`` the
browser parses the narration string as HTML, encounters ``<script>``, and
executes the payload.

Fix options (any one suffices):
  A. Server-side: HTML-sanitize narration_html before embedding it into
     frames, stripping or escaping ``<script>`` and other executable tags.
  B. Client-side: replace ``innerHTML`` assignments with ``textContent``
     for the narration, or use a sanitizer (DOMPurify) before assignment.
  C. Add a strict Content-Security-Policy that forbids inline script
     execution, making ``<script>`` inside innerHTML a no-op.

These tests operate at the Python/server level: they render an animation
whose narration contains a ``<script>`` payload and assert that the
emitted HTML does NOT contain an *unescaped* ``<script>`` tag inside the
JS frames data structure that the client runtime will pass to ``innerHTML``.

P2 status: FAIL today (the opening ``<script>`` tag is present unescaped
inside the backtick template literal that flows to ``narr.innerHTML``).
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.emitter import FrameData, SubstoryData, emit_interactive_html


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _frames_with_narration(narration_html: str) -> list[FrameData]:
    """Construct a single-frame list with the given narration_html."""
    return [
        FrameData(
            step_number=1,
            total_frames=1,
            narration_html=narration_html,
            shape_states={},
            annotations=[],
            label=None,
        )
    ]


def _frames_with_svg(svg_html: str) -> list[FrameData]:
    """Construct a single-frame list where the SVG field contains the payload."""
    return [
        FrameData(
            step_number=1,
            total_frames=1,
            narration_html="",
            shape_states={},
            annotations=[],
            label=None,
        )
    ]


def _extract_js_narration_values(html: str) -> list[str]:
    """Return every narration value found inside JS frame literals.

    Matches both the backtick-template form used by inline-runtime mode
    (``narration:`...```) and the JSON form used by external-runtime mode
    (``"narration":"..."``).
    """
    # Backtick template literal: narration:`...` (may span multiple chars)
    backtick = re.findall(r'narration:`(.*?)`', html, re.DOTALL)
    # JSON string: "narration":"..." (double-quote form, escaped content)
    json_form = re.findall(r'"narration"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    return backtick + json_form


# ---------------------------------------------------------------------------
# P2 — Tests that FAIL today (RED phase)
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestNarrationScriptTagBlocked:
    """Narration content set via ``innerHTML`` must not contain executable
    ``<script>`` tags.

    The narration field goes directly to ``narr.innerHTML`` in scriba.js.
    After the fix the server must ensure no executable ``<script>`` survives.
    """

    def test_script_tag_in_narration_html_not_in_js_frames_raw(self) -> None:
        """A ``<script>`` injected into narration_html must not appear raw in JS frames.

        Audit finding P2: the ``_escape_js`` helper escapes ``</script>`` to
        ``<\\/script>`` but leaves ``<script>`` unescaped in the backtick
        literal.  When the client calls ``narr.innerHTML = frames[i].narration``
        the browser sees a ``<script>`` open tag and executes the payload.

        Post-fix expectation: the JS frame data must NOT contain the literal
        string ``<script>`` inside any narration value — it must be either
        HTML-entity-encoded (``&lt;script&gt;``) or stripped entirely.
        """
        payload = "<script>alert('xss-p2')</script>"
        html = emit_interactive_html(
            "test-p2-narration",
            _frames_with_narration(payload),
            {},
        )

        narration_values = _extract_js_narration_values(html)
        assert narration_values, (
            "Could not locate narration values in emitted JS frames. "
            "The extraction regex may need updating if the frame format changed."
        )

        for value in narration_values:
            assert "<script>" not in value, (
                "P2 DOM XSS: the literal string '<script>' appears inside the "
                "JS frames narration field.\n"
                f"narration value: {value!r}\n"
                "When the client executes narr.innerHTML=frames[i].narration "
                "the browser will parse and execute this script."
            )

    def test_script_tag_in_narration_is_html_entity_encoded(self) -> None:
        """The ``<`` in ``<script>`` must be encoded as ``&lt;`` in narration output.

        Acceptable encodings that survive innerHTML assignment safely:
          - ``&lt;script&gt;...&lt;/script&gt;``  (HTML entity encoding)
          - complete absence of the tag (stripped by sanitizer)

        Fails today because the raw ``<script>`` opening tag is present in
        the backtick literal that flows to ``innerHTML``.
        """
        payload = "<script>document.cookie='stolen'</script>"
        html = emit_interactive_html(
            "test-p2-entity",
            _frames_with_narration(payload),
            {},
        )

        narration_values = _extract_js_narration_values(html)
        for value in narration_values:
            # Either the tag is gone or it is entity-encoded
            tag_present_raw = "<script>" in value
            tag_present_encoded = "&lt;script&gt;" in value or "\\u003cscript" in value
            assert not tag_present_raw or tag_present_encoded, (
                "P2 DOM XSS: '<script>' is present unencoded in the narration "
                "JS frame value. It must be HTML-entity-encoded so that "
                "innerHTML assignment renders it as text, not executable code.\n"
                f"narration value: {value!r}"
            )

    def test_onerror_event_handler_in_narration_blocked(self) -> None:
        """An ``<img onerror=...>`` payload in narration must not survive raw.

        Even without ``<script>``, inline event handlers can execute JS via
        ``innerHTML``.  The fix must strip or encode all executable HTML.
        """
        payload = '<img src=x onerror="alert(\'p2-img\')">'
        html = emit_interactive_html(
            "test-p2-img",
            _frames_with_narration(payload),
            {},
        )

        narration_values = _extract_js_narration_values(html)
        for value in narration_values:
            assert "onerror=" not in value, (
                "P2 DOM XSS: '<img onerror=...>' survives into the narration "
                "JS frame value and will execute when set via innerHTML.\n"
                f"narration value: {value!r}"
            )

    def test_multiple_script_tags_all_blocked(self) -> None:
        """Multiple ``<script>`` tags in a single narration must all be blocked."""
        payload = (
            "<script>alert(1)</script>"
            " some text "
            "<script>alert(2)</script>"
        )
        html = emit_interactive_html(
            "test-p2-multi",
            _frames_with_narration(payload),
            {},
        )

        narration_values = _extract_js_narration_values(html)
        for value in narration_values:
            assert "<script>" not in value, (
                "P2 DOM XSS: '<script>' found in narration JS frame value "
                "even after multiple-tag sanitization.\n"
                f"narration value: {value!r}"
            )

    # ------------------------------------------------------------------
    # Negative: plain-text narration must be preserved.
    # ------------------------------------------------------------------

    def test_plain_text_narration_is_unchanged(self) -> None:
        """Plain-text narration without HTML tags must survive the fix unaltered.

        This test must PASS both before and after the fix — it is the
        non-regression guard confirming the sanitizer does not strip
        legitimate narration content.
        """
        narration = "We add element i to the front of the queue."
        html = emit_interactive_html(
            "test-p2-plain",
            _frames_with_narration(narration),
            {},
        )

        narration_values = _extract_js_narration_values(html)
        assert any(narration in v for v in narration_values), (
            "Plain-text narration was not preserved in the JS frames data. "
            "The sanitizer may be over-stripping content."
        )


# ---------------------------------------------------------------------------
# P2 — Substory narration bypass (A4 blocker)
# ---------------------------------------------------------------------------


def _frames_with_substory(substory_narration_html: str) -> list[FrameData]:
    """Construct a single main frame that contains a substory with the given narration.

    The substory narration flows through ``emit_substory_html`` into the
    ``data-scriba-frames`` JSON attribute, which the JS runtime parses and
    assigns to ``sn.innerHTML`` (scriba.js ``initSub``).  This path was not
    covered by the original A2 fix and is the bypass identified in A4's review.
    """
    sub_frame = FrameData(
        step_number=1,
        total_frames=1,
        narration_html=substory_narration_html,
        shape_states={},
        annotations=[],
        label=None,
    )
    substory = SubstoryData(
        title="Sub-computation",
        substory_id="substory1",
        depth=1,
        frames=[sub_frame],
        primitives=None,
    )
    main_frame = FrameData(
        step_number=1,
        total_frames=1,
        narration_html="Main narration.",
        shape_states={},
        annotations=[],
        label=None,
        substories=[substory],
    )
    return [main_frame]


def _extract_substory_frame_attr_values(html: str) -> list[str]:
    """Return the raw (entity-encoded) values of all ``data-scriba-frames``
    attributes in the emitted HTML.

    The substory widget stores frame data as a JSON array in the
    ``data-scriba-frames`` HTML attribute.  The emitter entity-encodes the
    value with ``html.escape()`` (turning ``<`` → ``&lt;``, ``"`` → ``&quot;``,
    etc.) so the attribute delimiter is never ambiguous.  No literal ``"``
    appears inside the attribute value.

    We return the *raw* encoded value because the double JSON-then-HTML
    encoding of nested SVG content makes full JSON.loads() unreliable in
    isolation.  Callers assert directly on the encoded string: if an XSS
    payload survives bleach it would appear as ``&lt;script&gt;`` in the
    encoded value (entity-encoded ``<script>``) or as the literal token
    ``onerror=`` (which ``html.escape`` does not touch because ``=`` is not a
    reserved HTML character).
    """
    return re.findall(r'data-scriba-frames="([^"]*)"', html)


@pytest.mark.regression
class TestSubstoryNarrationScriptTagBlocked:
    """Substory narration content must be sanitized before entering
    ``data-scriba-frames`` JSON.

    The JS runtime (scriba.js ``initSub``) assigns ``fd[i].narration`` to
    ``sn.innerHTML``.  Without sanitization the substory narration path is a
    complete bypass of the main-frame XSS fix (A4 blocker #1).

    Extraction strategy: we check the raw HTML-entity-encoded attribute value.
    If bleach strips ``<script>`` the narration becomes plain text (``alert(1)``)
    and neither the literal tag nor its entity form (``&lt;script&gt;``) appears
    in the narration region of the attribute.  If the fix is absent, the narration
    would contain ``&lt;script&gt;alert(1)&lt;/script&gt;`` (entity-encoded HTML)
    which is still dangerous because ``JSON.parse`` recovers the raw ``<script>``
    string and the JS runtime sets it as ``innerHTML``.
    """

    def test_script_tag_in_substory_narration_stripped(self) -> None:
        """``<script>alert(1)</script>`` in substory narration must not survive
        into the ``data-scriba-frames`` JSON attribute.

        After the fix, bleach strips the ``<script>`` tag to its text content
        (``alert(1)``).  Neither the literal ``&lt;script&gt;`` (entity form)
        nor ``<script>`` (which cannot appear in an HTML attribute) will be in
        the narration portion of the JSON payload.

        If the fix is absent, the entity-encoded narration JSON value would
        contain ``&lt;script&gt;`` — which ``JSON.parse`` recovers as the raw
        ``<script>`` tag and the JS runtime then sets as ``innerHTML``.
        """
        payload = "<script>alert(1)</script>"
        html = emit_interactive_html(
            "test-p2-substory-script",
            _frames_with_substory(payload),
            {},
        )

        attr_values = _extract_substory_frame_attr_values(html)
        assert attr_values, (
            "Could not locate data-scriba-frames attribute in emitted HTML. "
            "The extraction regex may need updating if the attribute format changed."
        )
        for raw_attr in attr_values:
            # &lt;script&gt; is the entity-encoded form of <script>.
            # If bleach stripped the tag, neither form will appear in the narration.
            assert "&lt;script&gt;" not in raw_attr, (
                "P2 DOM XSS (substory bypass): the entity-encoded tag "
                "'&lt;script&gt;' appears in the data-scriba-frames attribute.\n"
                "JSON.parse() recovers this as the raw '<script>' string. "
                "When sn.innerHTML=fd[i].narration is called the browser will "
                "execute it.\n"
                f"data-scriba-frames snippet: {raw_attr[:300]!r}"
            )

    def test_onerror_in_substory_narration_stripped(self) -> None:
        """Event-handler attributes in substory narration must be stripped.

        bleach removes ``onerror=`` from the narration before it enters the
        JSON.  ``html.escape()`` does not encode ``=`` so ``onerror=`` would
        appear verbatim in the attribute value if the fix were absent.
        """
        payload = '<img src=x onerror="alert(\'substory-xss\')">'
        html = emit_interactive_html(
            "test-p2-substory-onerror",
            _frames_with_substory(payload),
            {},
        )

        attr_values = _extract_substory_frame_attr_values(html)
        assert attr_values, (
            "Could not locate data-scriba-frames attribute in emitted HTML. "
            "The extraction regex may need updating if the attribute format changed."
        )
        for raw_attr in attr_values:
            assert "onerror=" not in raw_attr, (
                "P2 DOM XSS (substory bypass): 'onerror=' survives into the "
                "data-scriba-frames attribute value.\n"
                "JSON.parse() recovers this as an event-handler attribute. "
                "When sn.innerHTML=fd[i].narration is called the browser will "
                "execute the handler.\n"
                f"data-scriba-frames snippet: {raw_attr[:300]!r}"
            )
