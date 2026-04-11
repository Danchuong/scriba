"""Base class, helpers, and shared constants for animation primitives.

Every primitive type (Array, Grid, DPTable, Graph, Tree, NumberLine, etc.)
extends :class:`PrimitiveBase` and implements the unified interface:
``Cls(name, params)`` constructor with self-managed state.

See ``docs/spec/primitives.md`` for the authoritative catalog.
"""

from __future__ import annotations

import abc
import re
import warnings
from dataclasses import dataclass
from typing import Any, Callable, ClassVar


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

    def __iter__(self):
        """Support tuple unpacking: ``x, y, w, h = bbox``."""
        return iter((self.x, self.y, self.width, self.height))


# ---------------------------------------------------------------------------
# Valid state names (§2.3 in primitives.md)
# ---------------------------------------------------------------------------

from scriba.animation.constants import DEFAULT_STATE, VALID_STATES  # noqa: F401 — re-exported

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
# Theme colors — single source of truth for non-state colors
# ---------------------------------------------------------------------------

THEME = {
    "bg": "#f6f8fa",         # panel / cell idle background
    "bg_alt": "#f1f3f5",     # alternate row / index column background
    "border": "#d0d7de",     # borders, dividers, outlines
    "border_light": "#dee2e6",  # lighter borders
    "fg": "#212529",         # primary text
    "fg_muted": "#6c757d",   # secondary text (labels, indices, captions)
    "fg_dim": "#adb5bd",     # placeholder / disabled text
    "empty_bg": "#f6f8fa",   # empty state dashed background
}

DARK_THEME = {
    "bg": "#161b22",
    "bg_alt": "#1c2128",
    "border": "#30363d",
    "border_light": "#21262d",
    "fg": "#c9d1d9",
    "fg_muted": "#8b949e",
    "fg_dim": "#484f58",
    "empty_bg": "#0d1117",
}

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
# Primitive registry — auto-populated by @register_primitive decorator
# ---------------------------------------------------------------------------

_PRIMITIVE_REGISTRY: dict[str, type["PrimitiveBase"]] = {}


def register_primitive(*type_names: str):
    """Decorator to register a primitive class under one or more type names.

    Usage:
        @register_primitive("Queue")
        class Queue(PrimitiveBase): ...

        @register_primitive("Matrix", "Heatmap")  # aliases
        class MatrixPrimitive(PrimitiveBase): ...
    """
    def decorator(cls):
        for name in type_names:
            _PRIMITIVE_REGISTRY[name] = cls
        return cls
    return decorator


def get_primitive_registry() -> dict[str, type["PrimitiveBase"]]:
    """Return a copy of the registered primitive catalog."""
    return dict(_PRIMITIVE_REGISTRY)


# ---------------------------------------------------------------------------
# Abstract base for all animation primitives
# ---------------------------------------------------------------------------


class PrimitiveBase(abc.ABC):
    """Base class for all animation primitives.

    Every primitive manages its own internal state (CSS state classes,
    per-part values, annotations) and renders itself via :meth:`emit_svg`.
    """

    # Subclasses override to declare their selector patterns as metadata.
    # Format: {"suffix_pattern": description}
    # Special patterns:
    #   "cell[{i}]"        — integer-indexed (validated against size/capacity)
    #   "cell[{r}][{c}]"   — 2D indexed
    #   "node[{i}]"        — integer-indexed
    #   "link[{i}]"        — integer-indexed
    #   "tick[{i}]"        — integer-indexed
    #   "var[{name}]"      — named variable
    #   "all"              — select all parts
    #   "front", "rear", "top" — named parts (no index)
    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {}

    def __init__(self, name: str = "", params: dict[str, Any] | None = None) -> None:
        self.name = name
        self.params = params if params is not None else {}
        self._states: dict[str, str] = {}  # target suffix -> state name
        self._values: dict[str, str] = {}  # target suffix -> display value
        self._labels: dict[str, str] = {}  # target suffix -> display label
        self._annotations: list[dict[str, Any]] = []
        self._highlighted: set[str] = set()

    # ----- state management ------------------------------------------------

    def set_state(self, target: str, state: str) -> None:
        """Set the CSS state class for an addressable target."""
        if not self.validate_selector(target):
            warnings.warn(
                f"{self.__class__.__name__} '{self.name}': "
                f"invalid selector '{target}', ignoring set_state()",
                stacklevel=2,
            )
            return
        if state not in VALID_STATES:
            warnings.warn(
                f"{self.__class__.__name__} '{self.name}': "
                f"invalid state '{state}', ignoring set_state()",
                stacklevel=2,
            )
            return
        self._states[target] = state

    def get_state(self, target: str) -> str:
        """Return the CSS state class for *target*, defaulting to ``idle``."""
        return self._states.get(target, "idle")

    def set_value(self, suffix: str, value: str) -> None:
        """Set display value for an addressable part."""
        if not self.validate_selector(suffix):
            warnings.warn(
                f"{self.__class__.__name__} '{self.name}': "
                f"invalid selector '{suffix}', ignoring set_value()",
                stacklevel=2,
            )
            return
        self._values[suffix] = value

    def get_value(self, suffix: str) -> str | None:
        """Return display value for *suffix*, or ``None`` if unset."""
        return self._values.get(suffix)

    def set_label(self, suffix: str, label: str) -> None:
        """Set display label for an addressable part."""
        if not self.validate_selector(suffix):
            warnings.warn(
                f"{self.__class__.__name__} '{self.name}': "
                f"invalid selector '{suffix}', ignoring set_label()",
                stacklevel=2,
            )
            return
        self._labels[suffix] = label

    def set_annotations(self, annotations: list[dict[str, Any]]) -> None:
        """Set annotations for this primitive."""
        self._annotations = annotations

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
