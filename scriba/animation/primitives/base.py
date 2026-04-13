"""Base class, helpers, and shared constants for animation primitives.

Every primitive type (Array, Grid, DPTable, Graph, Tree, NumberLine, etc.)
extends :class:`PrimitiveBase` and implements the unified interface:
``Cls(name, params)`` constructor with self-managed state.

See ``docs/spec/primitives.md`` for the authoritative catalog.
"""

from __future__ import annotations

import abc
import math
import re
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, ClassVar

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from scriba.core.context import RenderContext


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
# β "Tonal Architecture" color map — Radix slate + blue.
# These values are the inline fallback when CSS custom properties are not
# yet applied (test snapshots, raw emitter output, non-browser consumers).
# They must stay in lockstep with ``scriba-scene-primitives.css`` :root.
# ---------------------------------------------------------------------------

STATE_COLORS: dict[str, dict[str, str]] = {
    "idle":      {"fill": "#f8f9fa", "stroke": "#dfe3e6", "text": "#11181c"},
    "current":   {"fill": "#0090ff", "stroke": "#0b68cb", "text": "#ffffff"},
    "done":      {"fill": "#e6e8eb", "stroke": "#c1c8cd", "text": "#11181c"},
    "dim":       {"fill": "#f1f3f5", "stroke": "#e6e8eb", "text": "#687076"},
    "error":     {"fill": "#f8f9fa", "stroke": "#e5484d", "text": "#11181c"},
    "good":      {"fill": "#e6e8eb", "stroke": "#2a7e3b", "text": "#11181c"},
    "highlight": {"fill": "#f8f9fa", "stroke": "#0090ff", "text": "#0b68cb"},
    "path":      {"fill": "#e6e8eb", "stroke": "#c1c8cd", "text": "#687076"},
}


def svg_style_attrs(state_name: str) -> dict[str, str]:
    """Return fill, stroke, text-fill for a state."""
    return STATE_COLORS.get(state_name, STATE_COLORS["idle"])

# ---------------------------------------------------------------------------
# Theme colors — single source of truth for non-state colors.
# β slate system; must match scriba-scene-primitives.css base tokens.
# ---------------------------------------------------------------------------

THEME = {
    "bg": "#f8f9fa",         # slate-2 — panel / cell idle background
    "bg_alt": "#f1f3f5",     # slate-3 — alternate row / index column
    "border": "#dfe3e6",     # slate-6 — borders, dividers, outlines
    "border_light": "#e6e8eb",  # slate-5 — lighter borders
    "fg": "#11181c",         # slate-12 — primary text
    "fg_muted": "#687076",   # slate-11 — labels, indices, captions
    "fg_dim": "#9ba1a6",     # slate-10 — placeholder / disabled text
    "empty_bg": "#f1f3f5",   # slate-3 — empty state dashed background
}

DARK_THEME = {
    "bg": "#1a1d1e",         # slate-1 dark
    "bg_alt": "#202425",     # slate-2 dark
    "border": "#313538",     # slate-6 dark
    "border_light": "#2b2f31",  # slate-5 dark
    "fg": "#ecedee",         # slate-12 dark
    "fg_muted": "#9ba1a6",   # slate-11 dark
    "fg_dim": "#687076",     # slate-10 dark
    "empty_bg": "#202425",
}

# ---------------------------------------------------------------------------
# Layout constants shared across cell-based primitives
# ---------------------------------------------------------------------------

CELL_WIDTH = 60
CELL_HEIGHT = 40
CELL_GAP = 2
INDEX_LABEL_OFFSET = 16  # vertical offset below the cell for index labels

# β redesign — half-pixel stroke inset for crisp 1-2px strokes at DPR=1.
# The worst-case (2px signal states) is applied uniformly so the cell
# bounding box stays deterministic regardless of state.
_CELL_STROKE_INSET: float = 1.0


def _inset_rect_attrs(
    x: float, y: float, width: float, height: float
) -> dict[str, str]:
    """Return SVG rect attributes inset for half-pixel stroke alignment.

    Used by cell primitives (array, grid, dptable, stack, queue, matrix,
    numberline) to keep 1-2px strokes crisp at DPR=1. Does NOT emit rx,
    fill, stroke, or stroke-width — those come from CSS state classes.
    """
    return {
        "x": f"{x + _CELL_STROKE_INSET}",
        "y": f"{y + _CELL_STROKE_INSET}",
        "width": f"{width - 2 * _CELL_STROKE_INSET}",
        "height": f"{height - 2 * _CELL_STROKE_INSET}",
    }


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
# Smart label placement constants & helpers
# ---------------------------------------------------------------------------

_LABEL_MAX_WIDTH_CHARS = 24
_LABEL_PILL_PAD_X = 6
_LABEL_PILL_PAD_Y = 3
_LABEL_PILL_RADIUS = 4
_LABEL_BG_OPACITY = 0.92
_LABEL_HEADROOM = 24


@dataclass(slots=True)
class _LabelPlacement:
    """Tracks the bounding box of a placed annotation label for collision avoidance."""

    x: float
    y: float
    width: float
    height: float

    def overlaps(self, other: "_LabelPlacement") -> bool:
        """Return True if this placement overlaps *other*."""
        return not (
            self.x + self.width / 2 < other.x - other.width / 2
            or self.x - self.width / 2 > other.x + other.width / 2
            or self.y + self.height / 2 < other.y - other.height / 2
            or self.y - self.height / 2 > other.y + other.height / 2
        )


def _wrap_label_lines(text: str, max_chars: int = _LABEL_MAX_WIDTH_CHARS) -> list[str]:
    """Split label text into lines at natural break points if it exceeds *max_chars*."""
    if len(text) <= max_chars:
        return [text]
    # Split at spaces, operators, commas
    tokens: list[str] = []
    current = ""
    for ch in text:
        current += ch
        if ch in (" ", ",", "+", "=", "-"):
            tokens.append(current)
            current = ""
    if current:
        tokens.append(current)

    lines: list[str] = []
    line = ""
    for tok in tokens:
        if line and len(line) + len(tok) > max_chars:
            lines.append(line.rstrip())
            line = tok
        else:
            line += tok
    if line:
        lines.append(line.rstrip())
    return lines if lines else [text]


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

    # Subclasses override to declare the set of accepted keyword parameters
    # for the ``\\shape`` command. When non-empty, unknown keys are rejected
    # at construction time with ``E1114`` and a fuzzy "did you mean" hint.
    # An empty frozenset preserves backward compatibility for primitives
    # that have not yet migrated to the strict-params regime.
    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset()

    # RFC-002 strict-mode hook. Set per-instance by the Pipeline (via the
    # animation renderer) so primitives can route silent-fix warnings
    # through :func:`scriba.animation.errors._emit_warning`. Defaults to
    # ``None`` so direct unit-test instantiation still works without any
    # RenderContext in scope.
    _ctx: "RenderContext | None" = None

    def __init__(self, name: str = "", params: dict[str, Any] | None = None) -> None:
        self.name = name
        self.params = params if params is not None else {}
        if self.ACCEPTED_PARAMS:
            self._validate_accepted_params(self.params)
        self._states: dict[str, str] = {}  # target suffix -> state name
        self._values: dict[str, str] = {}  # target suffix -> display value
        self._labels: dict[str, str] = {}  # target suffix -> display label
        self._annotations: list[dict[str, Any]] = []
        self._highlighted: set[str] = set()

    @classmethod
    def _validate_accepted_params(cls, params: dict[str, Any]) -> None:
        """Reject keyword parameters not in ``ACCEPTED_PARAMS``.

        Raises ``E1114`` with a fuzzy "did you mean `X`?" hint whenever a
        close candidate exists in the accepted set. This import is local
        to sidestep the circular ``errors.py ↔ primitives`` dependency.
        """
        # Local import to avoid the ``errors.py`` <-> primitives cycle.
        from scriba.animation.errors import animation_error, suggest_closest

        accepted = cls.ACCEPTED_PARAMS
        for key in params:
            if key in accepted:
                continue
            suggestion = suggest_closest(key, accepted)
            hint = (
                f"did you mean `{suggestion}`?"
                if suggestion
                else f"valid: {', '.join(sorted(accepted))}"
            )
            raise animation_error(
                "E1114",
                (
                    f"unknown {cls.__name__} parameter {key!r}; "
                    f"valid: {', '.join(sorted(accepted))}"
                ),
                hint=hint,
            )

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

    def set_min_arrow_above(self, value: int) -> None:
        """Set minimum vertical space to reserve above cells for arrows.

        Called by the emitter with the max ``arrow_height_above`` across
        all animation frames so that primitives keep a stable translate
        offset even in frames with fewer (or no) arrows.
        """
        self._min_arrow_above = value

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

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG (x, y) center coordinates for an annotation selector.

        Primitives that support arrow annotations override this to map
        selectors like ``'arr.cell[3]'`` or ``'G.node[A]'`` to pixel
        coordinates.  Returns ``None`` if the selector cannot be resolved.
        """
        return None


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


# ---------------------------------------------------------------------------
# Shared arrow annotation infrastructure
# ---------------------------------------------------------------------------

ARROW_STYLES: dict[str, dict[str, str]] = {
    "good": {
        "stroke": "#059669",
        "stroke_width": "2.2",
        "opacity": "1.0",
        "label_fill": "#059669",
        "label_weight": "700",
        "label_size": "12px",
    },
    "info": {
        "stroke": "#94a3b8",
        "stroke_width": "1.5",
        "opacity": "0.45",
        "label_fill": "#94a3b8",
        "label_weight": "500",
        "label_size": "11px",
    },
    "warn": {
        "stroke": "#d97706",
        "stroke_width": "2.0",
        "opacity": "0.8",
        "label_fill": "#d97706",
        "label_weight": "600",
        "label_size": "11px",
    },
    "error": {
        "stroke": "#dc2626",
        "stroke_width": "2.0",
        "opacity": "0.8",
        "label_fill": "#dc2626",
        "label_weight": "600",
        "label_size": "11px",
    },
    "muted": {
        "stroke": "#cbd5e1",
        "stroke_width": "1.2",
        "opacity": "0.3",
        "label_fill": "#cbd5e1",
        "label_weight": "500",
        "label_size": "11px",
    },
    "path": {
        "stroke": "#2563eb",
        "stroke_width": "2.5",
        "opacity": "1.0",
        "label_fill": "#2563eb",
        "label_weight": "700",
        "label_size": "12px",
    },
}


def emit_arrow_svg(
    lines: list[str],
    ann: dict[str, Any],
    src_point: tuple[float, float],
    dst_point: tuple[float, float],
    arrow_index: int,
    cell_height: float,
    render_inline_tex: "Callable[[str], str] | None" = None,
    layout: str = "horizontal",
    shorten_src: float = 0.0,
    shorten_dst: float = 0.0,
    placed_labels: "list[_LabelPlacement] | None" = None,
) -> None:
    """Emit a cubic Bezier arrow annotation into *lines*.

    This is the shared arrow rendering used by Array, DPTable, and any
    future primitive that supports annotation arrows.  Each primitive is
    responsible for resolving selectors to SVG coordinates (via its own
    ``_cell_center`` / ``resolve_annotation_point``) and passing the
    results here.

    Parameters
    ----------
    lines:
        Output buffer -- SVG markup is appended in-place.
    ann:
        Annotation dict with keys ``target``, ``arrow_from``, and
        optional ``color`` and ``label``.
    src_point:
        ``(x, y)`` SVG coordinates of the arrow source.
    dst_point:
        ``(x, y)`` SVG coordinates of the arrow destination.
    arrow_index:
        Stagger index for multiple arrows targeting the same cell.
    cell_height:
        Cell height used for curve offset calculation.
    render_inline_tex:
        Optional callback for rendering ``$...$`` math in labels.
    layout:
        ``"horizontal"`` (default) curves upward for Array/DPTable etc.
        ``"2d"`` curves perpendicular to the source-destination line,
        suitable for Graph, Tree, Grid, and Plane2D.
    shorten_src:
        Pull the path start point toward the destination by this many
        pixels.  Useful for circular nodes so the arrow starts at the
        circle edge rather than the center.
    shorten_dst:
        Pull the path end point toward the source by this many pixels.
        Useful for circular nodes so the arrowhead stops at the circle
        edge rather than piercing into the node.
    placed_labels:
        Optional mutable list of already-placed label bounding boxes.
        When provided, collision avoidance nudges labels away from
        previous placements and appends the final position.
    """
    color = ann.get("color", "info")
    label_text = ann.get("label", "")
    target = ann.get("target", "")
    arrow_from = ann.get("arrow_from", "")

    x1, y1 = float(src_point[0]), float(src_point[1])
    x2, y2 = float(dst_point[0]), float(dst_point[1])

    # Shorten endpoints toward each other (for circle-edge arrows)
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy) or 1.0

    if shorten_src > 0 and dist > 0:
        x1 = x1 + (dx / dist) * shorten_src
        y1 = y1 + (dy / dist) * shorten_src
    if shorten_dst > 0 and dist > 0:
        x2 = x2 - (dx / dist) * shorten_dst
        y2 = y2 - (dy / dist) * shorten_dst

    # Recompute after shortening
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy) or 1.0

    # Control points: sqrt-scaled curve height capped at 1.2x cell height,
    # with compact stagger for multiple arrows targeting the same cell.
    h_dist = abs(x2 - x1) + abs(y2 - y1)
    base_offset = min(cell_height * 1.2, max(cell_height * 0.5, math.sqrt(h_dist) * 2.5))
    stagger = cell_height * 0.3
    total_offset = base_offset + arrow_index * stagger

    if layout == "2d":
        # Perpendicular Bezier: curve away from the connecting line
        perp_x = -dy / dist
        perp_y = dx / dist

        mid_x_f = (x1 + x2) / 2
        mid_y_f = (y1 + y2) / 2

        cx1 = int((x1 + mid_x_f) / 2 + perp_x * total_offset)
        cy1 = int((y1 + mid_y_f) / 2 + perp_y * total_offset)
        cx2 = int((x2 + mid_x_f) / 2 + perp_x * total_offset)
        cy2 = int((y2 + mid_y_f) / 2 + perp_y * total_offset)

        label_ref_x = int(mid_x_f + perp_x * (total_offset + 8))
        label_ref_y = int(mid_y_f + perp_y * (total_offset + 8))
        # Curve midpoint for leader line anchoring
        curve_mid_x = int(mid_x_f + perp_x * total_offset * 0.75)
        curve_mid_y = int(mid_y_f + perp_y * total_offset * 0.75)
    else:
        # Horizontal layout: curve upward (original formula)
        mid_x_f = (x1 + x2) / 2
        mid_y_val = int(min(y1, y2) - total_offset)

        # When source and target are nearly vertically aligned (same column
        # in a 2D DPTable), the default control points collapse to a vertical
        # line.  Offset them horizontally to produce a visible arc.
        h_span = abs(x2 - x1)
        if h_span < 4:
            h_nudge = total_offset * 0.6
            cx1 = max(0, int(mid_x_f - h_nudge))
            cy1 = mid_y_val
            cx2 = max(0, int(mid_x_f - h_nudge))
            cy2 = mid_y_val
            # Clamp label X so pill doesn't go negative.
            # Estimate pill half-width from label text.
            _est_pill_hw = (
                estimate_text_width(label_text, 11) // 2 + _LABEL_PILL_PAD_X
                if label_text else 20
            )
            raw_lx = int(mid_x_f - h_nudge - 8)
            label_ref_x = max(raw_lx, _est_pill_hw)
            label_ref_y = mid_y_val - 4
        else:
            cx1 = int((x1 + mid_x_f) / 2)
            cy1 = mid_y_val
            cx2 = int((x2 + mid_x_f) / 2)
            cy2 = mid_y_val
            label_ref_x = int(mid_x_f)
            label_ref_y = mid_y_val - 4  # slightly above the curve peak
        # Curve midpoint for leader line anchoring
        curve_mid_x = int(mid_x_f)
        curve_mid_y = mid_y_val

    ix1, iy1 = int(x1), int(y1)
    ix2, iy2 = int(x2), int(y2)

    # Resolve inline style for this color
    style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
    s_stroke = style["stroke"]
    s_width = style["stroke_width"]
    s_opacity = style["opacity"]

    ann_desc = (
        f"Arrow from {_escape_xml(str(arrow_from))} "
        f"to {_escape_xml(str(target))}"
    )
    if label_text:
        ann_desc += f": {_escape_xml(label_text)}"

    # Compute inline arrowhead polygon at the path endpoint.
    # This replaces SVG <marker> defs which have cross-browser issues
    # (Safari file://, innerHTML replacement, etc.).
    arrow_size = 10
    # Direction vector at the curve tip: approximate via last control
    # point → endpoint.
    adx = float(ix2 - cx2)
    ady = float(iy2 - cy2)
    ad = math.sqrt(adx * adx + ady * ady) or 1.0
    aux, auy = adx / ad, ady / ad       # unit vector toward tip
    apx, apy = -auy, aux                 # perpendicular
    hw = arrow_size * 0.5
    # Three vertices: tip, and two base corners
    p1x, p1y = ix2, iy2
    p2x = p1x - aux * arrow_size + apx * hw
    p2y = p1y - auy * arrow_size + apy * hw
    p3x = p1x - aux * arrow_size - apx * hw
    p3y = p1y - auy * arrow_size - apy * hw
    arrow_points = (
        f"{p1x:.1f},{p1y:.1f} {p2x:.1f},{p2y:.1f} {p3x:.1f},{p3y:.1f}"
    )

    ann_key = f"{target}-{arrow_from}" if arrow_from else f"{target}-solo"
    lines.append(
        f'  <g class="scriba-annotation scriba-annotation-{color}"'
        f' data-annotation="{_escape_xml(ann_key)}"'
        f' opacity="{s_opacity}"'
        f' role="graphics-symbol" aria-label="{ann_desc}">'
    )
    lines.append(
        f'    <path d="M{ix1},{iy1} C{cx1},{cy1} {cx2},{cy2} {ix2},{iy2}" '
        f'stroke="{s_stroke}" stroke-width="{s_width}" fill="none">'
        f'<title>{ann_desc}</title>'
        f'</path>'
    )
    lines.append(
        f'    <polygon points="{arrow_points}" fill="{s_stroke}"/>'
    )
    if label_text:
        l_fill = style["label_fill"]
        l_weight = style["label_weight"]
        l_size = style["label_size"]
        l_font_px = int(l_size.replace("px", "")) if l_size.endswith("px") else 11

        # Multi-line wrap
        label_lines = _wrap_label_lines(label_text)
        line_height = l_font_px + 2
        num_lines = len(label_lines)

        # Measure pill dimensions
        max_line_w = max(estimate_text_width(ln, l_font_px) for ln in label_lines)
        pill_w = max_line_w + _LABEL_PILL_PAD_X * 2
        pill_h = num_lines * line_height + _LABEL_PILL_PAD_Y * 2

        # Natural label position
        natural_x = float(label_ref_x)
        natural_y = float(label_ref_y)
        final_x = natural_x
        final_y = natural_y

        # Collision avoidance
        if placed_labels is not None:
            candidate = _LabelPlacement(
                x=final_x, y=final_y, width=float(pill_w), height=float(pill_h),
            )
            # Nudge directions: up, left, right, down
            nudge_step = pill_h + 2
            nudge_dirs = [
                (0, -nudge_step),    # up
                (-nudge_step, 0),    # left
                (nudge_step, 0),     # right
                (0, nudge_step),     # down
            ]
            for _ in range(4):
                if not any(candidate.overlaps(p) for p in placed_labels):
                    break
                # Pick the first nudge direction that resolves the overlap
                resolved = False
                for ndx, ndy in nudge_dirs:
                    test = _LabelPlacement(
                        x=candidate.x + ndx,
                        y=candidate.y + ndy,
                        width=candidate.width,
                        height=candidate.height,
                    )
                    if not any(test.overlaps(p) for p in placed_labels):
                        candidate = test
                        resolved = True
                        break
                if not resolved:
                    # Apply first nudge (up) and retry
                    candidate = _LabelPlacement(
                        x=candidate.x + nudge_dirs[0][0],
                        y=candidate.y + nudge_dirs[0][1],
                        width=candidate.width,
                        height=candidate.height,
                    )

            final_x = candidate.x
            final_y = candidate.y
            placed_labels.append(candidate)

        fi_x = int(final_x)
        fi_y = int(final_y)

        # Background pill: white rect with rounded corners, before text
        # Clamp so pill doesn't extend outside the viewBox (x/y >= 0).
        pill_rx = max(0, int(fi_x - pill_w / 2))
        pill_ry = int(fi_y - pill_h / 2 - l_font_px * 0.3)
        # If pill was clamped, shift label text to stay centered in pill
        fi_x = max(fi_x, pill_w // 2)
        lines.append(
            f'    <rect x="{pill_rx}" y="{pill_ry}"'
            f' width="{pill_w}" height="{pill_h}"'
            f' rx="{_LABEL_PILL_RADIUS}" ry="{_LABEL_PILL_RADIUS}"'
            f' fill="white" fill-opacity="{_LABEL_BG_OPACITY}"'
            f' stroke="{s_stroke}" stroke-width="0.5" stroke-opacity="0.3"/>'
        )

        # Leader line: if label was nudged far from its natural position
        displacement = math.sqrt(
            (final_x - natural_x) ** 2 + (final_y - natural_y) ** 2
        )
        if displacement > 30:
            lines.append(
                f'    <circle cx="{curve_mid_x}" cy="{curve_mid_y}" r="2"'
                f' fill="{s_stroke}" opacity="0.6"/>'
            )
            lines.append(
                f'    <polyline points="{curve_mid_x},{curve_mid_y}'
                f' {fi_x},{fi_y}"'
                f' fill="none" stroke="{s_stroke}"'
                f' stroke-width="0.75" stroke-dasharray="3,2"'
                f' opacity="0.6"/>'
            )

        # Render label text with paint-order halo
        if num_lines == 1:
            # Single line — use _render_svg_text with halo attributes
            text_attrs = (
                f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
                f' stroke="white" stroke-width="3"'
                f' stroke-linejoin="round" paint-order="stroke fill"'
            )
            style_parts = []
            if l_weight:
                style_parts.append(f"font-weight:{l_weight}")
            if l_size:
                style_parts.append(f"font-size:{l_size}")
            style_parts.append("text-anchor:middle")
            style_parts.append("dominant-baseline:auto")
            style_str = ";".join(style_parts)
            lines.append(
                f'    <text {text_attrs} style="{style_str}">'
                f'{_escape_xml(label_text)}</text>'
            )
        else:
            # Multi-line — use tspan elements
            text_attrs = (
                f'x="{fi_x}" y="{fi_y}" fill="{l_fill}"'
                f' stroke="white" stroke-width="3"'
                f' stroke-linejoin="round" paint-order="stroke fill"'
            )
            style_parts = []
            if l_weight:
                style_parts.append(f"font-weight:{l_weight}")
            if l_size:
                style_parts.append(f"font-size:{l_size}")
            style_parts.append("text-anchor:middle")
            style_parts.append("dominant-baseline:auto")
            style_str = ";".join(style_parts)
            tspans = ""
            for li, ln_text in enumerate(label_lines):
                dy_val = f'{line_height}' if li > 0 else "0"
                tspans += (
                    f'<tspan x="{fi_x}" dy="{dy_val}">'
                    f'{_escape_xml(ln_text)}</tspan>'
                )
            lines.append(
                f'    <text {text_attrs} style="{style_str}">{tspans}</text>'
            )

    lines.append("  </g>")


def arrow_height_above(
    annotations: list[dict[str, Any]],
    cell_center_resolver: "Callable[[str], tuple[float, float] | None]",
    cell_height: float = CELL_HEIGHT,
    layout: str = "horizontal",
) -> int:
    """Compute the max vertical extent above y=0 that arrows need.

    Parameters
    ----------
    annotations:
        Full list of annotations for the primitive.
    cell_center_resolver:
        Callable that maps a selector string (e.g. ``"arr.cell[3]"``)
        to ``(x, y)`` SVG coordinates, or ``None`` if unresolvable.
    cell_height:
        Cell height used for curve offset calculation.
    layout:
        ``"horizontal"`` (default) assumes upward-curving arrows.
        ``"2d"`` computes based on perpendicular offset from the
        source-destination line.
    """
    if not annotations:
        return 0
    arrow_anns = [a for a in annotations if a.get("arrow_from")]
    if not arrow_anns:
        return 0

    max_height = 0
    for idx, ann in enumerate(arrow_anns):
        src = cell_center_resolver(ann.get("arrow_from", ""))
        dst = cell_center_resolver(ann.get("target", ""))
        if src is None or dst is None:
            continue
        x1, y1 = src
        x2, y2 = dst
        # Count arrows targeting same cell before this one
        target = ann.get("target", "")
        arrow_index = sum(
            1
            for j, a in enumerate(arrow_anns)
            if a.get("target") == target
            and j < idx
        )
        h_dist = abs(x2 - x1) + abs(y2 - y1)
        base_offset = min(cell_height * 1.2, max(cell_height * 0.5, math.sqrt(h_dist) * 2.5))
        stagger = cell_height * 0.3
        total_offset = base_offset + arrow_index * stagger

        if layout == "2d":
            # For 2D layouts the curve bows perpendicular to the line
            # between source and destination.  The vertical component
            # above the topmost endpoint depends on the perpendicular
            # direction.
            dx = x2 - x1
            dy = y2 - y1
            dist = math.sqrt(dx * dx + dy * dy) or 1.0
            perp_y = dx / dist  # perpendicular y-component
            # The control points sit at roughly mid_y + perp_y * offset.
            # The worst-case vertical extent above the topmost point is
            # how far above min(y1, y2) the curve can reach.
            mid_y = (y1 + y2) / 2
            ctrl_y = mid_y + perp_y * total_offset
            extent_above = max(0, min(y1, y2) - ctrl_y)
            max_height = max(max_height, int(extent_above) + _LABEL_HEADROOM)
        else:
            # Horizontal: the curve peaks at min(y1, y2) - total_offset
            max_height = max(max_height, int(total_offset) + _LABEL_HEADROOM)

    return max_height


def emit_arrow_marker_defs(
    lines: list[str],
    annotations: list[dict[str, Any]],
) -> None:
    """Emit ``<defs>`` with ``<marker>`` elements for arrow colors.

    Only emits markers for colors actually used in *annotations*.
    Does nothing when no arrow annotations are present.

    Parameters
    ----------
    lines:
        Output buffer -- SVG markup is appended in-place.
    annotations:
        Full list of annotations; only those with ``arrow_from`` are
        considered.
    """
    # Arrowheads are now rendered as inline <polygon> elements inside
    # each annotation group by emit_arrow_svg().  No <marker> <defs>
    # needed.  This function is kept as a no-op for call-site compat.
    pass
