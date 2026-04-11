"""Base protocol, helpers, and shared constants for animation primitives.

Every primitive type (Array, Grid, DPTable, Graph, Tree, NumberLine)
implements the :class:`Primitive` factory and the :class:`PrimitiveInstance`
interface.

See ``docs/06-primitives.md`` for the authoritative catalog.
"""

from __future__ import annotations

import abc
import re
from dataclasses import dataclass
from typing import Any, Callable, Protocol


# ---------------------------------------------------------------------------
# Bounding box value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned bounding box for a primitive's SVG footprint."""

    x: int
    y: int
    width: int
    height: int


# ---------------------------------------------------------------------------
# Valid state names (§2.3 in 06-primitives.md)
# ---------------------------------------------------------------------------

VALID_STATES: frozenset[str] = frozenset(
    ("idle", "current", "done", "dim", "error", "good", "highlight", "path")
)

DEFAULT_STATE = "idle"

# ---------------------------------------------------------------------------
# Wong CVD-safe color map for inline SVG styling
# ---------------------------------------------------------------------------

STATE_COLORS: dict[str, dict[str, str]] = {
    "idle":      {"fill": "#f6f8fa", "stroke": "#d0d7de", "text": "#212529"},
    "current":   {"fill": "#0072B2", "stroke": "#0072B2", "text": "#ffffff"},
    "done":      {"fill": "#009E73", "stroke": "#009E73", "text": "#ffffff"},
    "dim":       {"fill": "#e9ecef", "stroke": "#dee2e6", "text": "#adb5bd"},
    "error":     {"fill": "#D55E00", "stroke": "#D55E00", "text": "#ffffff"},
    "good":      {"fill": "#56B4E9", "stroke": "#3a95c9", "text": "#0c4a6e"},
    "highlight": {"fill": "#F0E442", "stroke": "#d4c836", "text": "#212529"},
    "path":      {"fill": "#dbeafe", "stroke": "#2563eb", "text": "#0c4a6e"},
}


def svg_style_attrs(state_name: str) -> dict[str, str]:
    """Return fill, stroke, text-fill for a state."""
    return STATE_COLORS.get(state_name, STATE_COLORS["idle"])

# ---------------------------------------------------------------------------
# Layout constants shared across cell-based primitives
# ---------------------------------------------------------------------------

CELL_WIDTH = 60
CELL_HEIGHT = 40
CELL_GAP = 2
INDEX_LABEL_OFFSET = 16  # vertical offset below the cell for index labels


def estimate_text_width(text: str, font_size: int = 14) -> int:
    """Estimate rendered text width in pixels using conservative heuristics.

    Uses a simple character-count model tuned for common monospace and
    sans-serif fonts.  Callers should add padding on top of this estimate.
    """
    s = str(text)
    # Average character width ≈ 0.6 × font_size for sans-serif,
    # ≈ 0.62 × font_size for monospace.  Use 0.62 (conservative).
    avg_char_w = font_size * 0.62
    return int(len(s) * avg_char_w + 0.5)

# ---------------------------------------------------------------------------
# Selector regex helpers
# ---------------------------------------------------------------------------

_CELL_1D_RE = re.compile(r"^(?P<name>\w+)\.cell\[(?P<idx>\d+)\]$")
_CELL_2D_RE = re.compile(
    r"^(?P<name>\w+)\.cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$"
)
_RANGE_RE = re.compile(
    r"^(?P<name>\w+)\.range\[(?P<lo>\d+):(?P<hi>\d+)\]$"
)
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")


# ---------------------------------------------------------------------------
# Protocols (for cell-based primitives: Array, Grid, DPTable)
# ---------------------------------------------------------------------------


class PrimitiveInstance(Protocol):
    """A declared primitive instance with layout computed."""

    shape_name: str
    primitive_type: str

    def addressable_parts(self) -> list[str]:
        """Return all valid selector targets.

        Examples: ``['a.cell[0]', 'a.cell[1]', 'a.all']``
        """
        ...

    def validate_selector(self, selector_str: str) -> bool:
        """Check whether *selector_str* is valid for this instance."""
        ...

    def emit_svg(
        self,
        state: dict[str, dict[str, Any]],
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> str:
        """Emit SVG markup for the current frame.

        *state* maps ``target_str -> {state, value, label, ...}``.
        """
        ...

    def bounding_box(self) -> tuple[float, float, float, float] | BoundingBox:
        """Return ``(x, y, width, height)`` for viewBox computation."""
        ...


class Primitive(Protocol):
    """Factory interface for animation primitives."""

    name: str

    def declare(self, params: dict[str, Any]) -> PrimitiveInstance:
        r"""Create an instance from ``\shape`` params.

        Validates required params and raises
        :func:`~scriba.animation.errors.animation_error` with ``E1103``
        on missing required fields.
        """
        ...


# ---------------------------------------------------------------------------
# Abstract base (for node/edge primitives: Graph, Tree)
# ---------------------------------------------------------------------------


class PrimitiveBase(abc.ABC):
    """Base class for primitives that manage their own internal state.

    Used by Graph, Tree, and other node/edge-based primitives.
    Cell-based primitives (Array, DPTable) use the Protocol approach instead.
    """

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        self.name = name
        self.params = params
        self._states: dict[str, str] = {}  # target suffix -> state name

    # ----- state management ------------------------------------------------

    def set_state(self, target: str, state: str) -> None:
        """Set the CSS state class for an addressable target."""
        self._states[target] = state

    def get_state(self, target: str) -> str:
        """Return the CSS state class for *target*, defaulting to ``idle``."""
        return self._states.get(target, "idle")

    # ----- abstract interface ----------------------------------------------

    @abc.abstractmethod
    def addressable_parts(self) -> list[str]:
        """Return all valid selector suffixes for this primitive."""

    @abc.abstractmethod
    def validate_selector(self, suffix: str) -> bool:
        """Return ``True`` if *suffix* is a valid addressable part."""

    @abc.abstractmethod
    def bounding_box(self) -> BoundingBox:
        """Return the bounding box of this primitive in SVG coordinates."""

    @abc.abstractmethod
    def emit_svg(self, *, render_inline_tex: "Callable[[str], str] | None" = None) -> str:
        """Return the SVG fragment (``<g data-primitive="...">...</g>``)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def state_class(target_state: str) -> str:
    """Return the CSS class for a given state name."""
    return f"scriba-state-{target_state}"


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
    parts: list[str] = []
    last = 0
    for m in _INLINE_MATH_RE.finditer(str(text)):
        # Escape the literal text before this match
        if m.start() > last:
            parts.append(_escape_xml(str(text)[last : m.start()]))
        # Render the math fragment — wrap in $…$ because the callback
        # (from _make_inline_tex_callback / tex_inline_provider) expects
        # text that may contain ``$...$`` delimiters.
        parts.append(render_inline_tex(f"${m.group(1)}$"))
        last = m.end()
    # Trailing literal text
    tail = str(text)[last:]
    if tail:
        parts.append(_escape_xml(tail))
    return "".join(parts)


def _render_svg_text(
    text: str | Any,
    x: int,
    y: int,
    *,
    fill: str = "#212529",
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
