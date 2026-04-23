"""SVG text rendering helpers for animation primitives.

Extracted from base.py (Wave C1 split). Re-exported from base.py for
backward compatibility — all existing imports from base.py continue to work.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:  # pragma: no cover - type checking only
    pass


__all__ = [
    "_char_display_width",
    "estimate_text_width",
    "_escape_xml",
    "_INLINE_MATH_RE",
    "_has_math",
    "_render_mixed_html",
    "_render_svg_text",
    "_render_split_label_svg",
]


def _char_display_width(ch: str) -> float:
    """Return display-width multiplier for one Unicode codepoint.

    Returns:
        0.0  — combining marks / format chars (zero display width)
        1.0  — Wide / Fullwidth CJK (≈ 1 em in CJK fonts)
        0.62 — everything else (Latin/ASCII average)
    """
    cat = unicodedata.category(ch)
    if cat in ("Mn", "Me", "Cf"):  # combining / enclosing mark / format
        return 0.0
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("W", "F"):  # Wide / Fullwidth
        return 1.0
    return 0.62


def estimate_text_width(text: str, font_size: int = 14) -> int:
    """Estimate rendered text width in pixels using Unicode-aware heuristics.

    Handles CJK full-width characters, combining diacritics, ZWJ emoji
    sequences, and ASCII Latin text.  Uses pure stdlib (unicodedata).

    Rules applied in order:
    - ZWJ sequences (U+200D joiners): the entire joined cluster counts
      as exactly 1.0 em.  The algorithm uses a two-pass approach:
      first identify cluster boundaries, then sum widths.
    - Combining marks / format chars (Mn, Me, Cf category): 0 width.
    - East-Asian Wide / Fullwidth: 1.0 em.
    - All other chars: 0.62 em (sans-serif Latin average).

    Callers should add padding on top of this estimate.
    """
    s = str(text)
    total: float = 0.0
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\u200d":
            # Bare ZWJ between clusters — skip; the previous cluster
            # was already merged by look-ahead below.
            i += 1
            continue
        # Peek: if ANY later codepoint in this cluster is joined via ZWJ,
        # consume the whole ZWJ run as a single 1.0 em cluster.
        if i + 1 < n and s[i + 1] == "\u200d":
            # Walk forward past the entire ZWJ sequence.
            i += 1  # skip ch (base of cluster)
            while i < n and s[i] == "\u200d":
                i += 1  # skip ZWJ
                if i < n and s[i] != "\u200d":
                    i += 1  # skip next base in cluster
            total += 1.0  # whole cluster = 1 em
            continue
        total += _char_display_width(ch)
        i += 1
    return int(total * font_size + 0.5)


def _escape_xml(text: str) -> str:
    """Minimal XML text escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Inline TeX / foreignObject helpers
# ---------------------------------------------------------------------------

_INLINE_MATH_RE = re.compile(r"\$([^\$]+?)\$")


def _has_math(text: str) -> bool:
    """Return True if *text* contains at least one ``$...$`` fragment."""
    return "$" in str(text) and _INLINE_MATH_RE.search(str(text)) is not None


def _render_mixed_html(
    text: str,
    render_inline_tex: "Callable[[str], str]",
) -> str:
    """Render a string that may contain ``$...$`` math into HTML.

    Non-math segments are XML-escaped; math segments are rendered via
    the *render_inline_tex* callback (which takes a bare fragment, no
    ``$`` delimiters) and returned as-is (already HTML).
    """
    # W7-H1: hide escaped \$ before math regex so two escaped dollars
    # cannot pair up as a phantom math span.
    _SENTINEL = "\x00SCRIBA_BASE_DOLLAR\x00"
    src = str(text).replace("\\$", _SENTINEL)
    parts: list[str] = []
    last = 0
    for m in _INLINE_MATH_RE.finditer(src):
        if m.start() > last:
            parts.append(_escape_xml(src[last : m.start()].replace(_SENTINEL, "$")))
        parts.append(render_inline_tex(f"${m.group(1).replace(_SENTINEL, '$')}$"))
        last = m.end()
    tail = src[last:]
    if tail:
        parts.append(_escape_xml(tail.replace(_SENTINEL, "$")))
    return "".join(parts)


def _render_svg_text(
    text: str | Any,
    x: int,
    y: int,
    *,
    fill: str = "#11181c",
    css_class: str | None = None,
    font_weight: str | None = None,
    font_size: str | None = None,
    text_anchor: str | None = None,
    dominant_baseline: str | None = None,
    fo_width: int = 0,
    fo_height: int = 0,
    render_inline_tex: "Callable[[str], str] | None" = None,
    text_outline: str | None = None,
) -> str:
    """Render a text value as either a plain ``<text>`` or a ``<foreignObject>``.

    When *text* contains no ``$`` math delimiters or *render_inline_tex* is
    ``None``, this emits a standard SVG ``<text>`` element with
    ``_escape_xml(text)`` — identical to the original behaviour with zero
    overhead.

    When math IS present and a callback is provided, the text is rendered
    inside a ``<foreignObject>`` with an XHTML ``<div>`` so that KaTeX
    HTML can be embedded.

    Parameters
    ----------
    x, y:
        Centre coordinates of the text (for ``<text>`` these become the
        ``x``/``y`` attributes; for ``<foreignObject>`` the element is
        positioned so the text is visually centred on this point).
    fo_width, fo_height:
        Width and height of the ``<foreignObject>``.  When zero the
        caller should supply the enclosing cell dimensions.
    text_outline:
        **Deprecated as of Wave 9 (v0.6.1).** Use the CSS halo cascade in
        ``scriba-scene-primitives.css`` instead — every ``<text>`` child
        of a ``[data-primitive]`` now gets a state-aware halo via
        ``paint-order: stroke fill`` and per-state ``--scriba-halo`` CSS
        custom properties. The cascade flips automatically in dark mode
        and scales stroke width per role (cells 3px, labels 2px, node
        text 4px). Passing this parameter still emits the old inline
        ``stroke`` attribute for one release so external callers can
        migrate, but the inline value has lower CSS specificity than the
        new rules and will be silently overridden at render time in all
        Scriba-controlled contexts. Scheduled for removal in v0.7.0.
    """
    text_str = str(text)

    # Fast path — no math or no callback: emit a plain <text>
    if render_inline_tex is None or not _has_math(text_str):
        attrs = f'x="{x}" y="{y}" fill="{fill}"'
        if css_class:
            attrs = f'class="{css_class}" {attrs}'
        # Build inline style for properties that must override the global
        # ``svg text { … }`` CSS rule.  SVG presentation attributes have
        # lower specificity than stylesheet rules, so without ``style``
        # the CSS defaults would silently win (e.g. text-anchor: middle
        # overriding a start-aligned name column).
        style_parts: list[str] = []
        if text_anchor:
            style_parts.append(f"text-anchor:{text_anchor}")
        if dominant_baseline:
            style_parts.append(f"dominant-baseline:{dominant_baseline}")
        if font_weight:
            style_parts.append(f"font-weight:{font_weight}")
        if font_size:
            fs = font_size if any(font_size.endswith(u) for u in ("px", "em", "rem", "%")) else f"{font_size}px"
            style_parts.append(f"font-size:{fs}")
        if style_parts:
            attrs += f' style="{";".join(style_parts)}"'
        if text_outline:
            # Deprecated Wave 9 — see docstring. The CSS cascade in
            # scriba-scene-primitives.css supersedes this inline stroke
            # in every Scriba-rendered HTML context, so the emitted
            # attribute is effectively a no-op for pipeline and CLI
            # users. Kept for external callers migrating to v0.6.1; to
            # be removed in v0.7.0.
            import warnings as _w
            _w.warn(
                "text_outline= is deprecated as of Wave 9 (v0.6.1); the "
                "CSS halo cascade in scriba-scene-primitives.css handles "
                "every <text> element automatically and overrides any "
                "inline stroke. This parameter is scheduled for removal "
                "in v0.7.0.",
                DeprecationWarning,
                stacklevel=2,
            )
            attrs += (
                f' stroke="{text_outline}" stroke-width="4"'
                f' paint-order="stroke"'
            )
        return f"<text {attrs}>{_escape_xml(text_str)}</text>"

    # Slow path — render via foreignObject
    inner_html = _render_mixed_html(text_str, render_inline_tex)

    w = fo_width if fo_width > 0 else 80
    h = fo_height if fo_height > 0 else 30

    # Position the foreignObject so that ``x`` has the same meaning as
    # for the plain ``<text>`` path — i.e. it respects *text_anchor*:
    #   "start"  → x is the LEFT edge
    #   "end"    → x is the RIGHT edge
    #   "middle" → x is the CENTER  (default)
    if text_anchor == "start":
        fo_x = x
    elif text_anchor == "end":
        fo_x = x - w
    else:
        fo_x = x - w // 2
    fo_y = y - h // 2

    # Match text alignment inside the div to the requested anchor
    if text_anchor == "start":
        h_align = "flex-start"
        t_align = "left"
    elif text_anchor == "end":
        h_align = "flex-end"
        t_align = "right"
    else:
        h_align = "center"
        t_align = "center"

    style_parts: list[str] = [
        "display:flex",
        "align-items:center",
        f"justify-content:{h_align}",
        f"width:{w}px",
        f"height:{h}px",
        f"color:{fill}",
        f"text-align:{t_align}",
        "line-height:1",
        "overflow:hidden",
        "text-overflow:ellipsis",
    ]
    if font_weight:
        style_parts.append(f"font-weight:{font_weight}")
    if font_size:
        fs = font_size if any(font_size.endswith(u) for u in ("px", "em", "rem", "%")) else f"{font_size}px"
        style_parts.append(f"font-size:{fs}")

    style = ";".join(style_parts)

    return (
        f'<foreignObject x="{fo_x}" y="{fo_y}" width="{w}" height="{h}">'
        f'<div xmlns="http://www.w3.org/1999/xhtml" style="{style}">'
        f"{inner_html}"
        f"</div>"
        f"</foreignObject>"
    )


def _render_split_label_svg(
    primary: str,
    separator: str,
    secondary: str,
    x: int | float,
    y: int | float,
    *,
    fill: str = "#11181c",
    css_class: str | None = None,
    text_anchor: str | None = None,
    dominant_baseline: str | None = None,
    secondary_opacity: float = 0.55,
) -> str:
    """Render a two-value label as ``<text>`` with two ``<tspan>`` children.

    Phase 6 (GEP v2.0 U-03) — hierarchy cue for dual-value edge labels
    like capacity/flow.  Primary value renders bold at full fill; the
    separator + secondary value render together as a single dim tspan so
    the inline text flow is deterministic across renderers (no per-
    character ``dx`` arithmetic required).  Callers are expected to have
    split the label on the first separator (typically ``/``) and to pass
    non-empty ``primary`` and ``secondary`` strings.  ``xml:space="preserve"``
    keeps any internal whitespace intact.
    """
    attrs = f'xml:space="preserve" x="{x}" y="{y}" fill="{fill}"'
    if css_class:
        attrs = f'class="{css_class}" {attrs}'
    style_parts: list[str] = []
    if text_anchor:
        style_parts.append(f"text-anchor:{text_anchor}")
    if dominant_baseline:
        style_parts.append(f"dominant-baseline:{dominant_baseline}")
    if style_parts:
        attrs += f' style="{";".join(style_parts)}"'
    dim_style = f'style="font-weight:400;fill-opacity:{secondary_opacity:.2f}"'
    dim_body = _escape_xml(f"{separator}{secondary}")
    return (
        f"<text {attrs}>"
        f'<tspan style="font-weight:700">{_escape_xml(primary)}</tspan>'
        f"<tspan {dim_style}>{dim_body}</tspan>"
        f"</text>"
    )
