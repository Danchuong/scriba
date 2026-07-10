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
    "line_box_h",
    "_char_display_width",
    "estimate_text_width",
    "_escape_xml",
    "_INLINE_MATH_RE",
    "_has_math",
    "_render_mixed_html",
    "_render_svg_text",
    "_render_split_label_svg",
    "_scaled_font_size",
]

# Global diagram font-size scale knob. Every inline font-size emitted into
# SVG text is multiplied by this CSS custom property so a consumer embedding
# Scriba output can resize ALL diagram text with a single declaration:
#   :root { --scriba-diagram-font-scale: 1.3; }
# Default (var unset) resolves to 1, leaving rendered size unchanged.
_FONT_SCALE_VAR = "--scriba-diagram-font-scale"


_RTL_RE = re.compile(r"[\u0590-\u08ff\ufb1d-\ufdff\ufe70-\ufeff]")


def _bidi_style(text: str) -> str:
    """``unicode-bidi:plaintext`` for strings containing RTL codepoints.

    scriba emits bidi-naked <text>; a pure-RTL run reorders fine, but an
    RTL-first string with embedded Latin/parens mis-mirrors and scrambles
    ("نتيجة (result) = 42"). plaintext makes the UA resolve paragraph
    direction from the first strong character per UAX#9 — verified fix in
    investigations/allscript-render-audit.md. Only RTL-bearing strings get
    the style so LTR output stays byte-identical.
    """
    return "unicode-bidi:plaintext" if _RTL_RE.search(str(text)) else ""


def line_box_h(font_px: int) -> int:
    """Single-line text box height for a given font size (the ubiquitous
    ``font_px + 2`` — one formula, one home; hand-copied +2s drift)."""
    return font_px + 2


def _scaled_font_size(font_size: str) -> str:
    """Return a CSS ``font-size`` value in SVG user units (fixed px).

    The global ``--scriba-diagram-font-scale`` is applied uniformly by scaling
    the whole ``<svg>`` viewport (its ``max-width`` carries the var), NOT each
    font-size. Scaling the viewport scales text AND geometry by the same ratio,
    so text can never overflow its shapes at any scale — see the SVG sizing in
    ``_frame_renderer.render_frame``. This returns the bare unit-bearing size.

    ``font_size`` may be a bare number (treated as ``px``) or already carry a
    unit (``px``/``em``/``rem``/``%``).
    """
    if any(font_size.endswith(u) for u in ("px", "em", "rem", "%")):
        return font_size
    return f"{font_size}px"


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

# Identifier fragment for the interpolation shape gate below -- duplicated
# from ``scriba.tex.renderer.TexRenderer._INTERP_IDENT`` (itself duplicated
# from ``scriba.animation.parser.lexer._IDENT_RE``) rather than imported, to
# keep this low-level SVG text helper free of a dependency on the tex
# renderer module. Same character ranges, so a combining-mark identifier is
# recognised identically everywhere.
_INTERP_IDENT = (
    r"[^\W\d](?:\w|[̀-ͯ҃-҉֑-ֽؐ-ؚ"
    r"ً-ٰٟۖ-ۜ۟-ۤऀ-ः"
    r"ऺ-ॏ॑-ॗॢॣঁ-ঃั"
    r"ิ-ฺ็-๎ັິ-ຼ່-ໍ"
    r"ါ-ှၖ-ၙ឴-៓ᩕ-᩿᷀-᷿"
    r"⃐-⃰︠-︯])*"
)
# ``${...}`` is interpolation syntax IFF its brace content is
# identifier-shaped, optionally followed by ``[index]``/``.attr`` tails --
# mirrors ``TexRenderer._INTERP_SHAPE_RE``. Labels/notes are not a
# documented interpolation position (SCRIBA-TEX-REFERENCE.md sec 13.2), so
# an identifier-shaped run reaching here is always an unresolved literal --
# but its lone "$" still mis-pairs with the next real $...$ unless shielded
# from the pairing regex below (judgezone-11 reverse risk: the mirror image
# of the interpolation-position bug fixed in tex/renderer.py).
_INTERP_SHAPE_RE = re.compile(
    r"^\{" + _INTERP_IDENT + r"(?:\[[^\]]*\]|\." + _INTERP_IDENT + r")*\}$"
)
_INTERP_REF_RE = re.compile(r"\$\{[^}]*\}")


def _shield_interp_refs(text: str) -> "tuple[str, dict[str, str]]":
    """Replace identifier-shaped ``${...}`` runs with an opaque, ``$``-free
    placeholder so they cannot be swept into ``$...$`` math pairing (here,
    or in ``strip_math_markup``'s own internal pairing once restored past
    it -- callers must restore AFTER any such pairing pass, not before).

    Non-identifier-shaped ``${...}`` (e.g. the math body of
    ``${5 \\choose 3}$``) is left untouched and falls through to normal
    math pairing, per the judgezone-11 shape contract.
    """
    placeholders: dict[str, str] = {}

    def _sub(m: "re.Match[str]") -> str:
        if not _INTERP_SHAPE_RE.match(m.group(0)[1:]):
            return m.group(0)
        ph = f"\x00SCRIBA_INTERP{len(placeholders)}\x00"
        placeholders[ph] = m.group(0)
        return ph

    return _INTERP_REF_RE.sub(_sub, text), placeholders


def _unshield_interp_refs(text: str, placeholders: "dict[str, str]") -> str:
    """Restore placeholders from ``_shield_interp_refs`` to their original
    (unresolved) ``${...}`` text."""
    for ph, original in placeholders.items():
        text = text.replace(ph, original)
    return text


def _has_math(text: str) -> bool:
    """Return True if *text* contains at least one ``$...$`` fragment.

    Identifier-shaped ``${...}`` runs are shielded first so text made up
    only of unresolved interpolation refs (no real math) reports False and
    stays on the plain-``<text>`` fast path instead of round-tripping
    through the foreignObject/KaTeX machinery for nothing (judgezone-11
    reverse risk -- see ``_render_mixed_html``).
    """
    shielded, _ = _shield_interp_refs(str(text))
    return "$" in shielded and _INLINE_MATH_RE.search(shielded) is not None


def _render_mixed_html(
    text: str,
    render_inline_tex: "Callable[[str], str]",
) -> str:
    """Render a string that may contain ``$...$`` math into HTML.

    Non-math segments get the JZ-13 "one interpretation" literal pass
    (``strip_math_markup``: ``\\_`` unescape, ``\\texttt{}`` unwrap) then
    XML-escaping; math segments are rendered via the *render_inline_tex*
    callback (which takes a bare fragment, no ``$`` delimiters) and
    returned as-is (already HTML).

    Identifier-shaped ``${...}`` runs are shielded from math pairing
    before the ``$...$`` split runs, so an unresolved ``${name}`` next to
    real math stays literal instead of being swept into a bogus math span
    or corrupting the following pair's boundary (judgezone-11 reverse
    risk).
    """
    # W7-H1: hide escaped \$ before math regex so two escaped dollars
    # cannot pair up as a phantom math span.
    _SENTINEL = "\x00SCRIBA_BASE_DOLLAR\x00"
    src = str(text).replace("\\$", _SENTINEL)
    src, _interp_placeholders = _shield_interp_refs(src)

    def _restore(segment: str) -> str:
        return _unshield_interp_refs(segment, _interp_placeholders).replace(
            _SENTINEL, "$"
        )

    parts: list[str] = []
    last = 0
    for m in _INLINE_MATH_RE.finditer(src):
        if m.start() > last:
            # strip_math_markup runs BEFORE placeholders/sentinel are
            # restored: the segment is guaranteed $-free at this point
            # (interp refs are opaque placeholders, \$ is sentinelled), so
            # its own "$" not in text check always takes the literal-only
            # branch — restoring first could let two independent refs/
            # escapes re-pair into a phantom math span inside
            # strip_math_markup's own unshielded pairing.
            seg = strip_math_markup(src[last : m.start()])
            parts.append(_escape_xml(_restore(seg)))
        parts.append(render_inline_tex(f"${_restore(m.group(1))}$"))
        last = m.end()
    tail = src[last:]
    if tail:
        tail = strip_math_markup(tail)
        parts.append(_escape_xml(_restore(tail)))
    return "".join(parts)


_STRIP_CMD_RE = re.compile(r"\\([a-zA-Z]+)")

# \texttt{...} argument: a literal-text-island, same everywhere regardless
# of $...$ context (mirrors core/text_utils.py::apply_text_commands).
_TEXTT_RE = re.compile(r"\\texttt\{([^{}]*)\}")

# Protects a literal underscore that came from unescaping \_ inside a
# \texttt{} argument so a later subscript-detection regex (which only ever
# runs on math fragments — some of which may have wrapped a \texttt{}) can
# never misread it as a subscript trigger. Callers MUST restore this to
# "_" as their very last step, after all math-only processing has run.
_SENT_LIT_USCORE = "\x00LU\x00"


def _unescape_literal(text: str) -> str:
    r"""Literal (non-math) text: ``\_`` is the only recognized escape and
    unescapes to a plain underscore. No other TeX-speech/markup transform
    runs outside ``$...$`` (JZ-13 "one interpretation" contract)."""
    return text.replace("\\_", "_")


def _unwrap_texttt(text: str) -> str:
    r"""Unconditional pre-pass: ``\texttt{...}`` is a literal-text-island
    command authors use both inside and outside ``$...$`` — it always
    unwraps to its (unescaped) argument, independent of math context.
    Must run BEFORE any ``$...$`` split. See ``_SENT_LIT_USCORE`` for why
    the argument's ``\_`` unescapes to a sentinel, not a bare ``_``."""

    def _sub(m: "re.Match[str]") -> str:
        return m.group(1).replace("\\_", _SENT_LIT_USCORE)

    return _TEXTT_RE.sub(_sub, text)


def strip_math_markup(text: str) -> str:
    r"""The no-KaTeX paint form of a mixed label/value: ``$`` delimiters
    dropped, ``\\cmd`` -> ``cmd``, braces dropped inside math segments.
    ``\$`` escapes survive untouched. This is exactly what the plain-text
    fallbacks paint, so it is also exactly what they must be measured as
    ("size what you paint"). Outside ``$...$`` the text is literal:
    ``\_`` unescapes to ``_``, no other transform applies (JZ-13 "one
    interpretation" contract). ``\texttt{...}`` unwraps unconditionally,
    independent of ``$...$``."""
    text = _unwrap_texttt(str(text))
    if "$" not in text:
        return _unescape_literal(text).replace(_SENT_LIT_USCORE, "_")
    _SENT = "\x00D\x00"
    src = text.replace("\\$", _SENT)
    parts: list[str] = []
    last = 0
    for m in _INLINE_MATH_RE.finditer(src):
        parts.append(_unescape_literal(src[last : m.start()]))
        frag = m.group(1)
        frag = _STRIP_CMD_RE.sub(r"\1", frag)
        frag = frag.replace("{", "").replace("}", "")
        parts.append(frag)
        last = m.end()
    parts.append(_unescape_literal(src[last:]))
    return "".join(parts).replace(_SENT, "\\$").replace(_SENT_LIT_USCORE, "_")


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
    clip_overflow: bool = True,
    line_height_px: "int | None" = None,
    data_role: str | None = None,
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
    data_role:
        When set, emits a ``data-role="{data_role}"`` hook on the ``<text>``
        (or ``<foreignObject>``) so the runtime can address it directly. Used
        by the ``value_change`` handler: on name+value rows the value node is
        tagged ``"value"`` (and the label ``"name"``) so the handler stamps the
        VALUE, not the first ``<text>`` (which is the label). ``None`` (the
        default) emits nothing — byte-identical to the pre-tag output, so
        single-text primitives stay unchanged.
    """
    text_str = str(text)

    # Fast path — no math or no callback: emit a plain <text>
    if render_inline_tex is None or not _has_math(text_str):
        # JZ-13 "one interpretation": literal text outside $...$ still
        # gets the \_ unescape / \texttt{} unwrap pass, not just the
        # has-math+no-callback case — strip_math_markup is a no-op for
        # plain text carrying neither marker, so this is safe
        # unconditionally, and measure_value_text sizes this exact string.
        # Identifier-shaped ${...} runs are shielded first: strip_math_markup
        # does its own unshielded $...$ pairing internally, which would
        # mis-pair two unresolved refs (or a ref + real math) the same way
        # _render_mixed_html would without a shield (judgezone-11 reverse
        # risk) — this call site just has no foreignObject slow path to
        # hide behind, so it is equally exposed.
        _shielded, _interp_ph = _shield_interp_refs(text_str)
        text_str = _unshield_interp_refs(strip_math_markup(_shielded), _interp_ph)
        attrs = f'x="{x}" y="{y}" fill="{fill}"'
        if css_class:
            attrs = f'class="{css_class}" {attrs}'
        if data_role:
            attrs = f'data-role="{data_role}" {attrs}'
        # Build inline style for properties that must override the global
        # ``svg text { … }`` CSS rule.  SVG presentation attributes have
        # lower specificity than stylesheet rules, so without ``style``
        # the CSS defaults would silently win (e.g. text-anchor: middle
        # overriding a start-aligned name column).
        style_parts: list[str] = []
        _bidi = _bidi_style(text_str)
        if _bidi:
            style_parts.append(_bidi)
        if text_anchor:
            style_parts.append(f"text-anchor:{text_anchor}")
        if dominant_baseline:
            style_parts.append(f"dominant-baseline:{dominant_baseline}")
        if font_weight:
            style_parts.append(f"font-weight:{font_weight}")
        if font_size:
            style_parts.append(f"font-size:{_scaled_font_size(font_size)}")
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
        t_align = "left"
    elif text_anchor == "end":
        t_align = "right"
    else:
        t_align = "center"

    # Normal inline flow, NOT flex: a flex container turns every text node
    # and KaTeX span into its own flex item and drops the whitespace between
    # them ("a $x$ b" rendered as "ax b"). Single-line semantics are pinned
    # with white-space:nowrap; line-height:{h}px vertically centres the line
    # inside the box (callers wrap long captions into one box per line).
    # line_height_px decouples the line box from the FO box: a box one px
    # taller than its line box absorbs KaTeX's fractional ink rounding, so
    # scrollHeight can never exceed clientHeight (the "+1 box-chasing"
    # residue in the caption bench).
    _lh = line_height_px if line_height_px is not None else h
    style_parts: list[str] = [
        f"width:{w}px",
        f"height:{h}px",
        f"line-height:{_lh}px",
        f"color:{fill}",
        f"text-align:{t_align}",
        "white-space:nowrap",
        # same face as the <text> twins — without this the div falls back
        # to the embedding page's body font and paints widths the
        # measurers never modelled. Label/caption/index surfaces render
        # mono like their <text> siblings; everything else, "Scriba Sans".
        (
            "font-family:var(--scriba-label-font-family, ui-monospace, monospace)"
            if css_class
            and (
                "scriba-primitive-label" in css_class
                or "scriba-index-label" in css_class
            )
            else "font-family:var(--scriba-fo-font-family, 'Scriba Sans', sans-serif)"
        ),
    ]
    if clip_overflow:
        style_parts.append("overflow:hidden")
        style_parts.append("text-overflow:ellipsis")
    else:
        # Overflow parity with plain <text>: node labels and floating axis
        # labels are allowed to spill past their box exactly like their
        # plain-text twins do (halo-for-overflow design).
        style_parts.append("overflow:visible")
    if font_weight:
        style_parts.append(f"font-weight:{font_weight}")
    if font_size:
        style_parts.append(f"font-size:{_scaled_font_size(font_size)}")

    style = ";".join(style_parts)

    fo_attrs = f'x="{fo_x}" y="{fo_y}" width="{w}" height="{h}"'
    if not clip_overflow:
        # UA stylesheets default <foreignObject> to overflow:hidden — the
        # attribute opens it so the div's visible overflow can paint.
        fo_attrs += ' overflow="visible"'
    if css_class:
        # The <text> fast path carries css_class; mirror it here so CSS
        # (font, halo) and tooling see the same hook on the math path.
        fo_attrs = f'class="{css_class}" {fo_attrs}'
    if data_role:
        # Mirror the <text> fast-path role hook so a math value/label is
        # self-describing too (the runtime queries <text>, but the tag keeps
        # the DOM uniform for tooling and future selectors).
        fo_attrs = f'data-role="{data_role}" {fo_attrs}'

    _bidi = _bidi_style(text_str)
    if _bidi:
        style += ";" + _bidi
    return (
        f"<foreignObject {fo_attrs}>"
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
