"""Base class, helpers, and shared constants for animation primitives.

Every primitive type (Array, Grid, DPTable, Graph, Tree, NumberLine, etc.)
extends :class:`PrimitiveBase` and implements the unified interface:
``Cls(name, params)`` constructor with self-managed state.

See ``docs/spec/primitives.md`` for the authoritative catalog.
"""

from __future__ import annotations

import abc
import math
import warnings
from typing import TYPE_CHECKING, Any, Callable, ClassVar

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from scriba.core.context import RenderContext

from scriba.animation.primitives._extent import (
    PaintedExtent,
    measure_painted_extent,
)

# Cache sentinel: annotations measured, nothing painted (distinct from
# ``None`` = cache invalidated).
_NO_EXTENT = object()

# ---------------------------------------------------------------------------
# Re-export everything from the split sub-modules so all existing import
# paths (``from scriba.animation.primitives.base import X``) keep working.
# ---------------------------------------------------------------------------
from scriba.animation.primitives._types import *  # noqa: F401, F403
from scriba.animation.primitives._types import (  # noqa: F401 — explicit for IDEs
    ALL_RE,
    CELL_1D_RE,
    CELL_2D_RE,
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    DARK_THEME,
    DEFAULT_STATE,
    INDEX_LABEL_OFFSET,
    RANGE_RE,
    STATE_COLORS,
    THEME,
    VALID_STATES,
    BoundingBox,
    _CELL_HORIZONTAL_PADDING,
    _CELL_STROKE_INSET,
    _PRIMITIVE_LABEL_Y,
    _inset_rect_attrs,
    svg_style_attrs,
)
from scriba.animation.primitives._text_render import *  # noqa: F401, F403
from scriba.animation.primitives._text_metrics import (
    label_line_extra,
    measure_label_line,
)
from scriba.animation.primitives._text_render import (  # noqa: F401 — explicit for IDEs
    _INLINE_MATH_RE,
    _bidi_style,
    _char_display_width,
    _escape_xml,
    _has_math,
    _render_mixed_html,
    _render_split_label_svg,
    _render_svg_text,
    estimate_text_width,
    strip_math_markup,
)
from scriba.animation.primitives._svg_helpers import *  # noqa: F401, F403
from scriba.animation.primitives._svg_helpers import (  # noqa: F401 — explicit for IDEs
    ARROW_STYLES,
    CellMetrics,
    _LABEL_BG_OPACITY,
    _LABEL_HEADROOM,
    _LABEL_MAX_WIDTH_CHARS,
    _LABEL_PILL_MAX_W_PX,
    _LABEL_PILL_PAD_X,
    _LABEL_PILL_PAD_Y,
    _LABEL_PILL_RADIUS,
    _PLAIN_ARROW_STEM,
    _LabelPlacement,
    _Obstacle,
    _label_has_math,
    _label_width_text,
    _segment_to_obstacle,
    _translate_segment,
    _wrap_label_lines,
    arrow_height_above,
    position_label_h_extents,
    position_label_height_below,
    position_below_lane_height,
    emit_arrow_marker_defs,
    emit_arrow_svg,
    emit_plain_arrow_svg,
    emit_position_label_svg,
    annotation_color_class,
)


# ---------------------------------------------------------------------------
# Primitive registry — auto-populated by @register_primitive decorator
# ---------------------------------------------------------------------------

_PRIMITIVE_REGISTRY: dict[str, type["PrimitiveBase"]] = {}


def allow_forbidden_pattern(fp: str, *, reason: str, issue: str = ""):
    """Marker decorator read by ``scripts/lint_smart_label.py``.

    Suppresses ONE forbidden-pattern code (e.g. ``"FP-2"``) on the decorated
    method, leaving an in-source audit trail (*reason*, *issue*). No runtime
    effect — the linter collects the suppression from the AST.
    """
    def _wrap(fn):
        return fn
    return _wrap


def register_primitive(*type_names: str):
    """Decorator to register a primitive class under one or more type names.

    This is the **stable extension-point API** for third-party primitive
    plugins. Decorating a :class:`PrimitiveBase` subclass with
    ``@register_primitive("MyType")`` makes it available to the Scriba
    animation parser under ``\\shape{name}{MyType{...}}``.

    **Stability:** This decorator is part of the locked extension API.
    Its signature will not change before ``1.0.0``. See ``STABILITY.md``
    §Extension API for the full contract.

    Parameters
    ----------
    *type_names:
        One or more string names to register. Multiple names create
        aliases (e.g. ``@register_primitive("Matrix", "Heatmap")`` allows
        both ``Matrix{...}`` and ``Heatmap{...}`` to resolve to the same
        class). Names are case-sensitive.

    Returns
    -------
    Callable[[type], type]
        A class decorator that registers the class and returns it
        unchanged, so it may be stacked with other decorators.

    Examples
    --------
    Single-name registration::

        @register_primitive("Queue")
        class Queue(PrimitiveBase): ...

    Alias registration::

        @register_primitive("Matrix", "Heatmap")
        class MatrixPrimitive(PrimitiveBase): ...
    """
    def decorator(cls):
        for name in type_names:
            _PRIMITIVE_REGISTRY[name] = cls
        return cls
    return decorator


def get_primitive_registry() -> dict[str, type["PrimitiveBase"]]:
    """Return a snapshot copy of the registered primitive catalog.

    The catalog maps type-name strings (e.g. ``"Array"``, ``"Graph"``) to
    their :class:`PrimitiveBase` subclass. This is the **stable inspection
    API** for tooling that needs to enumerate or validate available
    primitive types at runtime.

    **Stability:** This function is part of the locked extension API. Its
    return type (``dict[str, type[PrimitiveBase]]``) will not change
    before ``1.0.0``. See ``STABILITY.md`` §Extension API for the full
    contract.

    Returns
    -------
    dict[str, type[PrimitiveBase]]
        A fresh ``dict`` copy — mutating the returned mapping does not
        affect the internal registry. Keys are the registered type-name
        strings; values are the corresponding primitive classes.

    Notes
    -----
    All built-in primitives are registered at import time via the
    ``@register_primitive`` decorator in their respective modules. Third-
    party primitives appear in this dict as soon as their module is
    imported. Import order determines registration order, though the dict
    itself is unordered for lookup purposes.
    """
    return dict(_PRIMITIVE_REGISTRY)


# ---------------------------------------------------------------------------
# Shared caption (Layer A) constants — see PrimitiveBase._caption_* helpers.
# ---------------------------------------------------------------------------
_CAPTION_FONT_PX: int = LABEL_FONT_PX  # one token: --scriba-label-font (guarded by test_layout_constant_sync)
_CAPTION_MIN_WRAP_W: int = 200      # caption never wraps narrower than this
_CAPTION_SAFETY_PAD: int = 8        # estimate_text_width under-counts; pad
# Vertical clearance between a primitive's content bottom and its caption.
# One constant for every primitive: Array/DPTable historically used 9
# (_STACK_GAP), Stack 8, Grid/Matrix/NumberLine 0 (the caption glyphs sat
# ON the cell border), Queue 0 (overlapping its own index labels).
_CAPTION_CLEAR_GAP: int = 8
# Per-line box height for captions containing $...$ math. KaTeX inline
# spans at 11px reach ~15px (superscript strut), so the plain 13px line
# would clip them; 18px clears the strut with 1-2px of air.
_MATH_CAPTION_LINE_H: int = line_box_h(LABEL_FONT_PX) + _MATH_PILL_LINE_EXTRA  # 13 + 5 — derived, not restated

# Top-band caption (tree, graph) — caption sits ABOVE the content.
_TOP_CAPTION_BAND: int = 28         # historical single-line band height
# top_y so the CSS `dominant-baseline: central` lands the line on the
# historical baseline (_PRIMITIVE_LABEL_Y): top_y + font//2 == baseline.
_TOP_CAPTION_TOP_Y: int = _PRIMITIVE_LABEL_Y - _CAPTION_FONT_PX // 2


# ---------------------------------------------------------------------------
# Abstract base for all animation primitives
# ---------------------------------------------------------------------------



def _trace_arrowhead(prev_pt, tip_pt, size: float = 7.0) -> str:
    """Polygon points for an arrowhead at *tip_pt* oriented along
    prev_pt->tip_pt (same construction as the runtime's dynamic head)."""
    import math as _m

    dx, dy = tip_pt[0] - prev_pt[0], tip_pt[1] - prev_pt[1]
    dist = _m.hypot(dx, dy) or 1.0
    ux, uy = dx / dist, dy / dist
    px, py = -uy, ux
    hw = size * 0.5
    bx, by = tip_pt[0] - ux * size, tip_pt[1] - uy * size
    return (
        f"{tip_pt[0]:.1f},{tip_pt[1]:.1f} "
        f"{bx + px * hw:.1f},{by + py * hw:.1f} "
        f"{bx - px * hw:.1f},{by - py * hw:.1f}"
    )


# R-38 binding-caret geometry: a ``▲`` pointing up at the bound cell from a
# band just below the row, with the cursor id as a small label beneath it.
_CURSOR_GAP: float = 6.0       # cell bottom -> caret apex
_CURSOR_H: float = 8.0         # apex -> base height of the ▲
_CURSOR_HALF_W: float = 5.0    # half the ▲ base width
_CURSOR_ID_FONT_PX: int = 11   # id label font
_CURSOR_ID_DY: float = 11.0    # ▲ base -> id label baseline


class PrimitiveBase(abc.ABC):
    """Base class for all animation primitives.

    Every primitive manages its own internal state (CSS state classes,
    per-part values, annotations) and renders itself via :meth:`emit_svg`.
    """

    # Subclasses set this to identify their primitive type string, e.g. "array".
    # Declared as ClassVar so type checkers know it belongs to the class, not
    # instances.  Concrete subclasses override with a plain assignment (no
    # annotation needed on the override).
    primitive_type: ClassVar[str] = ""

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
        self.label: str | None = None  # optional caption shown below the primitive
        self._states: dict[str, str] = {}  # target suffix -> state name
        self._values: dict[str, str] = {}  # target suffix -> display value
        self._labels: dict[str, str] = {}  # target suffix -> display label
        self._annotations: list[dict[str, Any]] = []
        # PaintedExtent | _NO_EXTENT | None(=invalidated)
        self._extent_above_cache: object | None = None
        self._highlighted: set[str] = set()
        # Arrow rendering defaults — subclasses override in __init__ as needed.
        self._arrow_cell_height: float = float(CELL_HEIGHT)
        self._arrow_layout: str = "1d"
        self._arrow_shorten: float = 0.0

    @classmethod
    def _validate_accepted_params(cls, params: dict[str, Any]) -> None:
        """Reject keyword parameters not in ``ACCEPTED_PARAMS``.

        Raises ``E1114`` with a fuzzy "did you mean `X`?" hint whenever a
        close candidate exists in the accepted set. This import is local
        to sidestep the circular ``errors.py ↔ primitives`` dependency.
        """
        # Local import to avoid the ``errors.py`` <-> primitives cycle.
        from scriba.animation.errors import _animation_error, _suggest_closest

        accepted = cls.ACCEPTED_PARAMS
        for key in params:
            if key in accepted:
                continue
            suggestion = _suggest_closest(key, accepted)
            hint = (
                f"did you mean `{suggestion}`?"
                if suggestion
                else f"valid: {', '.join(sorted(accepted))}"
            )
            raise _animation_error(
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
                f"[E1115] {self.__class__.__name__} '{self.name}': "
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
        """Set annotations for this primitive.

        The only sanctioned mutation point for ``self._annotations`` —
        the exact-reservation cache keys off it.
        """
        self._annotations = annotations
        self._extent_above_cache = None

    def annotation_height_above(self) -> int:
        """Exact px the current annotations paint above y=0.

        Runs the REAL annotation emitters (``emit_annotation_arrows``)
        into a scratch buffer and measures the painted extent of the
        output (closed-form Bézier extrema, stroke included). Reserved
        space therefore equals painted space by construction — no
        heuristic upper bound, and it cannot drift from the renderer.

        Measured in the natural (pre-collision) scene: cross-primitive
        ``scene_segments`` are not available before offsets exist, so a
        collision nudge from a neighbouring primitive is not part of the
        measurement; the placement engine is bounded to the reserved lane
        instead (see ``emit_annotation_arrows``).

        The result is cached until ``set_annotations`` replaces the
        annotation list (the emitters and the measurement are pure with
        respect to everything else).
        """
        ext = self._annotation_extent()
        if ext is None or ext.min_y >= 0:
            return 0
        return int(math.ceil(-ext.min_y))

    def _annotation_extent(self) -> "PaintedExtent | None":
        """Exact painted bbox of the current annotations, or ``None``.

        Single measurement consumed by ALL four reservation directions
        (above / left / right / below) — the same numbers the vertical
        lane already uses, so the horizontal and below reservations are
        exact by the same construction and include collision-nudge
        relocations between this primitive's own pills.
        """
        cached = getattr(self, "_extent_above_cache", None)
        if cached is not None:
            return cached if cached is not _NO_EXTENT else None
        ext: "PaintedExtent | None" = None
        if self._annotations:
            parts: list[str] = []
            self._measure_emit(parts)
            ext = measure_painted_extent("\n".join(parts))
        self._extent_above_cache = ext if ext is not None else _NO_EXTENT
        return ext

    def annotation_h_pads(self) -> "tuple[int, int]":
        """Exact ``(left_overhang, right_reach)`` of the annotations.

        ``left_overhang`` — px painted left of x=0 (content shifts right
        by this). ``right_reach`` — rightmost painted x (bbox width grows
        to at least this). Replaces the ``position_label_h_extents``
        estimate, which modelled only the natural single-pill anchor and
        missed collision-nudge relocations entirely.
        """
        ext = self._annotation_extent()
        if ext is None:
            return 0, 0
        left = int(math.ceil(-ext.min_x)) if ext.min_x < 0 else 0
        right = int(math.ceil(ext.max_x)) if ext.max_x > 0 else 0
        return left, right

    def annotation_below_overhang(self, baseline: float) -> int:
        """Exact px the annotations paint below *baseline*.

        Replaces the ``position_below_lane_height`` /
        ``position_label_height_below`` formula mirrors.
        """
        ext = self._annotation_extent()
        if ext is None or ext.max_y <= baseline:
            return 0
        return int(math.ceil(ext.max_y - baseline))

    def _annotation_cell_metrics(self) -> "CellMetrics | None":
        """Grid-aware flow context passed to the annotation engine.

        Single source of truth: ``emit_svg`` AND the extent measurement
        must call this same hook, otherwise measured geometry can diverge
        from rendered geometry (2D stagger-flip is gated on it).
        Default ``None`` — primitives with a grid/diameter proxy override.
        """
        return None

    def _measure_emit(self, parts: "list[str]") -> None:
        """Emit the current annotations exactly as ``emit_svg`` would.

        The extent measurement runs THIS hook into a scratch buffer.
        The default covers every primitive that routes annotations through
        ``emit_annotation_arrows``; a primitive with a custom annotation
        path (e.g. Queue's slot-pointer arrows) must override it to run
        that same custom path, or measured != painted.
        """
        self.emit_annotation_arrows(
            parts,
            self._annotations,
            cell_metrics=self._annotation_cell_metrics(),
        )

    def _reserved_arrow_above(self) -> int:
        """Reserved annotation lane above the content: the exact painted
        extent of this frame's annotations, floored by the cross-frame
        maximum the stitcher pinned via ``set_min_arrow_above`` (R-32
        uniform-layout contract). Single source for every primitive's
        ``bounding_box``/``emit_svg``."""
        return max(
            self.annotation_height_above(), getattr(self, "_min_arrow_above", 0)
        )

    def set_traces(self, traces: "list[dict]") -> None:
        """Attach this frame's ``\\trace`` decorations (R-37)."""
        self._traces = list(traces)

    def resolve_trace_point(self, selector: str) -> "tuple[float, float] | None":
        """Anchor a trace polyline vertex: the element CENTER. Defaults to
        ``resolve_label_anchor`` (center on every cell primitive);
        NumberLine overrides to the tick center — its annotation anchor is
        the tick TOP so arrows curve above, which would run the polyline
        along the tops (feat-trace-primitive.md geometry gotcha)."""
        return self.resolve_label_anchor(selector)

    def _trace_cell_suffix(self, cell) -> str:
        """Map one ``cells=`` entry to this primitive's selector suffix."""
        if isinstance(cell, (list, tuple)) and len(cell) == 2:
            return f"cell[{int(cell[0])}][{int(cell[1])}]"
        return f"cell[{int(cell)}]"

    def emit_traces_under(self, parts: "list[str]") -> None:
        """Paint every trace polyline UNDER the cells (call before the cell
        loop). Geometry runs through ``resolve_trace_point`` so the dynamic
        content-based pitch is honoured; an unresolvable vertex soft-drops
        the whole trace (mirrors selector semantics). The group carries the
        annotation structure contract — ``data-annotation`` + ``<path>`` +
        ``<polygon>`` — so the shipped runtime's ``annotation_add`` handler
        draw-ons it with zero JS changes. Reservation note: the polyline
        threads cell CENTERS, so its extent is inside the content box and
        never moves the viewBox; the painted⊆bbox honesty pins still see it
        via the FO/polyline-aware extent parsers.
        """
        for tr in getattr(self, "_traces", []):
            pts: "list[tuple[float, float]]" = []
            ok = True
            for cell in tr.get("cells", []):
                sel = f"{self.name}.{self._trace_cell_suffix(cell)}"
                pt = self.resolve_trace_point(sel)
                if pt is None:
                    ok = False
                    break
                pts.append(pt)
            if not ok or len(pts) < 2:
                continue
            color = tr.get("color", "info")
            style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
            stroke = style["stroke"]
            tid = tr.get("id", "t")
            key = f"{self.name}.trace[{tid}]-solo"
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            inner = (
                f'<path d="{d}" fill="none" stroke="{stroke}"'
                f' stroke-width="2.5" stroke-linecap="round"'
                f' stroke-linejoin="round" opacity="0.85"/>'
            )
            heads = []
            if tr.get("arrowhead", "end") in ("end", "both"):
                heads.append(_trace_arrowhead(pts[-2], pts[-1]))
            if tr.get("arrowhead") == "both":
                heads.append(_trace_arrowhead(pts[1], pts[0]))
            for hp in heads:
                inner += f'<polygon points="{hp}" fill="{stroke}"/>'
            if tr.get("dot") == "start":
                inner += (
                    f'<circle cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}"'
                    f' r="2.5" fill="{stroke}"/>'
                )
            label = tr.get("label")
            if label:
                midx, midy = pts[len(pts) // 2]
                lw = measure_label_line(str(label), LABEL_FONT_PX)
                ph = LABEL_FONT_PX + 8
                pw = lw + 12
                prx, pry = midx - pw / 2.0, midy - ph - 8
                # keep the pill inside the primitive's content span — a
                # midpoint on the last column would otherwise overflow the
                # viewBox (grid_cols/cell_width from the shared metrics)
                _cm = self._annotation_cell_metrics()
                if _cm is not None and getattr(_cm, "grid_cols", None):
                    _cw = float(_cm.cell_width)
                    _right = _cm.grid_cols * (_cw + 4.0) - 4.0
                    prx = max(2.0, min(prx, _right - pw - 2.0))
                _tx = prx + pw / 2.0
                inner += (
                    f'<rect x="{prx:.1f}" y="{pry:.1f}" width="{pw}"'
                    f' height="{ph}" rx="4" fill="white" fill-opacity="0.92"'
                    f' stroke="{stroke}" stroke-width="0.5" stroke-opacity="0.3"/>'
                    f'<text x="{_tx:.1f}" y="{pry + ph / 2.0:.1f}"'
                    f' fill="{style["label_fill"]}"'
                    f' style="text-anchor:middle;dominant-baseline:central">'
                    f"{_escape_xml(strip_math_markup(str(label)))}</text>"
                )
            parts.append(
                f'  <g class="scriba-annotation scriba-annotation-'
                f'{annotation_color_class(color)}"'
                f' data-annotation="{_escape_xml(key)}"'
                f' role="graphics-symbol" aria-roledescription="annotation"'
                f' aria-label="{_escape_xml(strip_math_markup(str(label or "trace")))}">'
                f"{inner}</g>"
            )

    def set_cursors(self, cursors: "list[dict]") -> None:
        """Attach this frame's R-38 binding carets (cell index already
        resolved by the renderer build phase)."""
        self._cursors = list(cursors)

    def _cursor_cell_suffix(self, index: "int") -> str:
        """Map a caret's resolved index to this primitive's cell selector
        suffix. NumberLine overrides to ``tick[i]``."""
        if isinstance(index, str) and index in ("before", "after"):
            return index  # sentinel slots (R-42)
        return f"cell[{int(index)}]"

    def get_cursor_positions(self) -> "dict[str, tuple[float, float]]":
        """Return ``{annotation_key: (x, y)}`` for the carets drawn by the last
        ``emit_cursors_under``. Read back into the wire after ``emit_svg`` so
        the differ can emit ``cursor_move`` (mirror of ``get_node_positions``)."""
        return dict(getattr(self, "_cursor_positions", {}))

    def emit_cursors_under(self, parts: "list[str]") -> None:
        """Paint every R-38 binding caret — a ``▲`` pointing up at its bound
        cell from a band just below the row, the cursor id a small label
        beneath. The group carries the annotation structure contract
        (``data-annotation="{shape}.cursor[{id}]-solo"``, a fresh ``cursor``
        infix that can never collide with a trace/annotation key), so the
        shipped runtime's ``annotation_add``/``annotation_remove`` fade it
        in/out for free; a resolved cell change rides the new ``cursor_move``
        kind. Geometry runs through the live cell resolvers so the dynamic
        content-based pitch is honoured; an out-of-range index soft-drops that
        caret. Records the drawn apex ``(x, y)`` for ``get_cursor_positions``.
        """
        self._cursor_positions: "dict[str, tuple[float, float]]" = {}
        for cur in getattr(self, "_cursors", []):
            index = cur.get("index")
            if index is None:
                continue
            sel = f"{self.name}.{self._cursor_cell_suffix(index)}"
            top = self.resolve_annotation_point(sel)
            center = self.resolve_label_anchor(sel)
            if top is None or center is None:
                continue  # out-of-range -> soft-drop (mirrors selectors)
            cx = center[0]
            # cell bottom = center + (center - top); place the apex a small gap
            # below it. cx/center come from the live cell geometry, so the
            # caret tracks the 0.22.1 content-based pitch automatically.
            apex_y = center[1] + (center[1] - top[1]) + _CURSOR_GAP
            base_y = apex_y + _CURSOR_H
            cid = str(cur.get("id", "c"))
            color = cur.get("color", "info")
            key = f"{self.name}.cursor[{cid}]-solo"
            style = ARROW_STYLES.get(color, ARROW_STYLES["info"])
            stroke = style["stroke"]
            pts = (
                f"{cx:.1f},{apex_y:.1f} "
                f"{cx - _CURSOR_HALF_W:.1f},{base_y:.1f} "
                f"{cx + _CURSOR_HALF_W:.1f},{base_y:.1f}"
            )
            inner = (
                f'<polygon points="{pts}" fill="{stroke}"/>'
                f'<text x="{cx:.1f}" y="{base_y + _CURSOR_ID_DY:.1f}"'
                f' fill="{stroke}" font-size="{_CURSOR_ID_FONT_PX}"'
                f' style="text-anchor:middle;dominant-baseline:central">'
                f"{_escape_xml(strip_math_markup(cid))}</text>"
            )
            parts.append(
                f'  <g class="scriba-annotation scriba-annotation-'
                f'{annotation_color_class(color)}"'
                f' data-annotation="{_escape_xml(key)}"'
                f' role="graphics-symbol" aria-roledescription="cursor"'
                f' aria-label="{_escape_xml(cid)}">'
                f"{inner}</g>"
            )
            self._cursor_positions[key] = (cx, apex_y)

    def _cursor_extent_below(self) -> float:
        """R-38: the deepest local-y any binding caret reaches this frame, so
        ``bounding_box`` can grow to keep the ``▲`` + id inside the viewBox.

        Returns ``0.0`` when there is no caret, so every non-cursor primitive
        and frame is byte-identical. Self-contained — it resolves each caret's
        cell exactly as ``emit_cursors_under`` does, so measured and painted
        extents can never disagree.
        """
        extent = 0.0
        for cur in getattr(self, "_cursors", []):
            index = cur.get("index")
            if index is None:
                continue
            sel = f"{self.name}.{self._cursor_cell_suffix(index)}"
            top = self.resolve_annotation_point(sel)
            center = self.resolve_label_anchor(sel)
            if top is None or center is None:
                continue
            cell_bottom = center[1] + (center[1] - top[1])
            caret_bottom = (
                cell_bottom
                + _CURSOR_GAP + _CURSOR_H + _CURSOR_ID_DY + _CURSOR_ID_FONT_PX / 2.0
            )
            extent = max(extent, caret_bottom)
        return extent

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
    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
        scene_segments: "tuple[tuple[Any, float, float, int], ...] | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        """Return the SVG fragment (``<g data-primitive="...">...</g>``).

        Parameters
        ----------
        scene_segments:
            Cross-primitive obstacle segments injected by the scene renderer
            (W3-α+). Each entry is ``(ObstacleSegment, x_off, y_off, prim_id)``
            where ``(x_off, y_off)`` are the scene-level translate offsets for
            the source primitive and ``prim_id`` is ``id(source_primitive)``
            used to exclude self-segments.  When ``None`` (default), only
            local ``resolve_obstacle_segments()`` results are used, which
            preserves backward-compatible behaviour for all callers outside
            the scene renderer.
        self_offset:
            The ``(x_off, y_off)`` translate of THIS primitive in the scene,
            used to convert foreign segment coordinates into this primitive's
            local frame.  Must be provided whenever *scene_segments* is not
            ``None``.
        """

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG (x, y) center coordinates for an annotation selector.

        Primitives that support arrow annotations override this to map
        selectors like ``'arr.cell[3]'`` or ``'G.node[A]'`` to pixel
        coordinates.  Returns ``None`` if the selector cannot be resolved.
        """
        return None

    def resolve_label_anchor(self, selector: str) -> tuple[float, float] | None:
        """Return the anchor for a position-only pill label.

        Defaults to :meth:`resolve_annotation_point` (the arrow anchor), which
        is correct for the primitives whose arrow anchor is already the element
        center. A primitive whose arrow anchor is an *edge* (e.g. Array returns
        the cell top so arrows curve above) overrides this to return the
        element *center*, because ``emit_position_label_svg`` offsets a pill by
        ``± cell_height / 2`` from the anchor assuming it is the center
        (Defect 1a). Arrow geometry keeps using ``resolve_annotation_point``.
        """
        return self.resolve_annotation_point(selector)

    def resolve_annotation_box(self, selector: str):
        """Return the ``BoundingBox`` of the annotated element, or ``None``.

        Used to register the annotated element as a MUST blocker so a pill is
        never placed over the thing it labels (Defect 1b, spec R-02). Defaults
        to ``None`` (no blocker) — only rectangular-cell primitives whose cell
        geometry is well-defined (e.g. Array) override this. Returning ``None``
        leaves placement unchanged, so non-overriding primitives are
        unaffected.
        """
        return None

    def _target_has_below_pill(self, selector: str) -> bool:
        """True if a ``position=below`` pill targets *selector*.

        Scopes ``resolve_annotation_box`` on cell/node primitives: base feeds the
        box width to *every* position pill as ``cell_width`` (which drives the
        R-07/R-08 spanning leader), so returning a box for an above/left/right
        target spuriously adds a leader on a narrow cell/node. Gating the cell
        box on an actual below pill keeps the box's effect inside the below lane,
        leaving above/left/right pills byte-stable. (Range boxes, used for the
        span bracket regardless of position, are NOT gated by this.)
        """
        return any(
            a.get("target") == selector
            and a.get("position") == "below"
            and not a.get("arrow_from")
            for a in self._annotations
        )

    def resolve_self_content_rects(self) -> "list[BoundingBox]":
        """Content AABBs of THIS primitive (cells, rows, nodes) that pill
        labels should avoid covering.

        Merged into the placement obstacle set as SHOULD ``content_cell``
        obstacles (W1 space-utilisation): without them every scoring term is
        blind to content occlusion and an arc pill happily parks on top of
        the cells at its natural anchor. Default ``[]`` — opt-in per
        primitive; non-overriding primitives are unaffected.
        """
        return []

    def resolve_below_baseline(self) -> "float | None":
        """Local-frame y below which ``position=below`` pills should be placed
        so they clear any index-label / caption stack (callout lane). ``None``
        → legacy cell-relative placement. Only primitives with a bottom stack
        (e.g. Array with index labels / a caption) override this.
        """
        return None

    def _below_lane_height(self) -> int:
        """Px reserved below ``resolve_below_baseline()`` for ``position=below``
        callout pills. 0 when nothing paints below the baseline (no-op for the
        common case). Shared by ``bounding_box``/caption placement of every
        primitive that opts into the lane.

        Exact painted extent below the baseline — includes downward collision
        nudges the retired ``position_below_lane_height`` formula never
        modelled."""
        baseline = self.resolve_below_baseline()
        if baseline is None:
            return 0
        return self.annotation_below_overhang(float(baseline))

    def _h_label_pad(self) -> "tuple[int, int]":
        """``(left_overhang, right_reach)`` of the annotations — the horizontal
        space to reserve so nothing clips the viewBox. Both 0 with no
        annotations (byte-stable footprint). Shared single source for
        ``bounding_box`` (grow width) and ``emit_svg`` (shift content right by
        the left overhang).

        Now the exact painted extent (same measurement as the vertical lane),
        so it covers left/right pills INCLUDING collision-nudge relocations,
        over-wide arc pills, and arrowheads — the retired
        ``position_label_h_extents`` estimate modelled only the natural
        single-pill anchor."""
        return self.annotation_h_pads()

    # -- Layer A: shared caption block (wrap + width-in-bbox) ----------------
    # Lifted from Array so every caption-bearing primitive folds its caption
    # width into the bounding box and wraps a long caption instead of clipping.
    # A primitive opts in by feeding its content width through these helpers in
    # bounding_box()/emit_svg(). Placement (top vs bottom) stays per-primitive.

    def _caption_lines(self, content_width: float) -> list[str]:
        """Wrap ``self.label`` to (at least) the content width. Math captions
        wrap too — ``_wrap_label_lines`` never splits inside ``$...$`` and
        measures math via ``_label_width_text``. Empty list when there is no
        caption."""
        s = getattr(self, "label", None)
        if not s:
            return []
        s = str(s)
        target = max(float(content_width), float(_CAPTION_MIN_WRAP_W))
        return _wrap_label_lines(s, max_px=target, font_px=_CAPTION_FONT_PX)

    def _caption_block_width(self, content_width: float) -> int:
        """Width of the wrapped caption block (widest line + padding), or 0."""
        lines = self._caption_lines(content_width)
        if not lines:
            return 0
        widest = max(
            measure_label_line(ln, _CAPTION_FONT_PX)
            for ln in lines
        )
        return int(widest + 2 * _CELL_HORIZONTAL_PADDING + _CAPTION_SAFETY_PAD)

    def _caption_block_height(self, content_width: float) -> int:
        """Total height of the wrapped caption block, or 0. Math lines use
        the taller ``_MATH_CAPTION_LINE_H`` box (KaTeX strut clearance)."""
        lines = self._caption_lines(content_width)
        if not lines:
            return 0
        if any(_label_has_math(ln) for ln in lines):
            # per-line: tall math (\frac, big-op limits, stacked scripts)
            # needs more than the standard KaTeX strut clearance — 16/20
            # bench fragments overflowed the fixed box (test_math_metrics
            # TestTallMathExtra pins the Chromium truth)
            return sum(
                _MATH_CAPTION_LINE_H + label_line_extra(ln, _CAPTION_FONT_PX) + 1
                for ln in lines
            )
        return len(lines) * (_CAPTION_FONT_PX + 2)

    def _emit_caption(
        self,
        out: "list[str]",
        *,
        content_width: float,
        footprint_width: int,
        top_y: int,
        origin_x: int = 0,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> None:
        """Emit the (possibly multi-line) caption centered on *footprint_width*,
        its first line at *top_y*. Single line uses the shared text renderer
        (keeps the KaTeX foreignObject path for ``$…$``); multi-line uses
        tspans with inline styling.

        *origin_x* is the frame-local x at which the footprint's left edge sits;
        pass a negative value when the caption is emitted inside a translated
        ``<g>`` (e.g. tree/graph's ``translate(r, …)``) so the caption still
        centers on the footprint rather than on the shifted frame. Defaults to
        0 — the common case where the emit frame and the footprint share an
        origin."""
        lines = self._caption_lines(content_width)
        if not lines:
            return
        center_x = int(footprint_width // 2) + origin_x
        line_h = _CAPTION_FONT_PX + 2
        if render_inline_tex is not None and any(
            _label_has_math(ln) for ln in lines
        ):
            # Math caption: one KaTeX-capable box per wrapped line, so a
            # long caption stacks below the content instead of clipping
            # inside a single fixed-height foreignObject. Plain lines in
            # the block go through the same call and come out as centred
            # <text> (dominant-baseline keeps both variants on one axis).
            # Per-line height mirrors _caption_block_height exactly; y is
            # cumulative so a tall \frac line pushes later lines down
            # instead of overlapping them. clip_overflow=False mirrors the
            # pill fix: any residual over-height paints past the box
            # instead of amputating the math.
            y_cursor = top_y
            for ln in lines:
                math_h = _MATH_CAPTION_LINE_H + label_line_extra(
                    ln, _CAPTION_FONT_PX
                )
                # box = line box + 1: absorbs KaTeX fractional ink rounding
                # so the audit invariant scrollHeight <= clientHeight holds
                box_h = math_h + 1
                out.append(
                    "  "
                    + _render_svg_text(
                        ln,
                        center_x,
                        y_cursor + box_h // 2,
                        fill=THEME["fg_muted"],
                        css_class="scriba-primitive-label",
                        font_size=str(_CAPTION_FONT_PX),
                        text_anchor="middle",
                        dominant_baseline="central",
                        fo_width=footprint_width,
                        fo_height=box_h,
                        render_inline_tex=render_inline_tex,
                        clip_overflow=False,
                        line_height_px=math_h,
                    )
                )
                y_cursor += box_h
            return
        if len(lines) == 1:
            out.append(
                "  "
                + _render_svg_text(
                    lines[0],
                    center_x,
                    # +2: center-anchored text otherwise puts its glyph top AT
                    # top_y, ~3px tighter than the multi-line/math branches.
                    top_y + _CAPTION_FONT_PX // 2 + 2,
                    fill=THEME["fg_muted"],
                    css_class="scriba-primitive-label",
                    # Inline anchor: the CSS direct-child rule does not reach
                    # a caption nested inside a translate group (animation
                    # frames with a reserved lane), where the SVG default
                    # text-anchor:start made the line run off to the right.
                    text_anchor="middle",
                    dominant_baseline="central",
                    fo_width=footprint_width,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
            )
        else:
            y0 = top_y + _CAPTION_FONT_PX
            # Trailing space on every non-final line: SVG trims it visually,
            # but textContent keeps it, so select-copy does not glue the
            # wrapped words together ("sang" + "phải" -> "sangphải").
            tspans = "".join(
                f'<tspan x="{center_x}" dy="{0 if i == 0 else line_h}">'
                f"{_escape_xml(strip_math_markup(ln) if _label_has_math(ln) else ln)}"
                f"{'' if i == len(lines) - 1 else ' '}</tspan>"
                for i, ln in enumerate(lines)
            )
            _bidi = _bidi_style(self.label or "")
            _bidi_attr = f' style="{_bidi}"' if _bidi else ""
            out.append(
                f'  <text class="scriba-primitive-label"{_bidi_attr} x="{center_x}"'
                f' y="{y0}" fill="{THEME["fg_muted"]}"'
                f' style="text-anchor:middle;font-size:{_CAPTION_FONT_PX}px">'
                f"{tspans}</text>"
            )

    def _top_caption_band(self, content_width: float) -> int:
        """Height reserved ABOVE the content for a top-band caption
        (tree, graph). Keeps the historical single-line band and grows only
        when the caption wraps to multiple lines."""
        if getattr(self, "label", None) is None:
            return 0
        block = _TOP_CAPTION_TOP_Y + self._caption_block_height(content_width)
        return max(_TOP_CAPTION_BAND, block)

    def _emit_top_caption(
        self,
        out: "list[str]",
        *,
        content_width: float,
        footprint_width: int,
        frame_radius: float,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> None:
        """Emit a top-band caption for a primitive whose content is wrapped in a
        ``translate(frame_radius, …)`` group (tree, graph). Centers on the
        footprint despite the frame shift, wraps to the footprint width, and
        anchors on the historical baseline so single-line captions are
        byte-stable."""
        self._emit_caption(
            out,
            content_width=content_width,
            footprint_width=footprint_width,
            top_y=_TOP_CAPTION_TOP_Y,
            origin_x=-int(frame_radius),
            render_inline_tex=render_inline_tex,
        )

    def _is_highlighted(self, suffix: str) -> bool:
        """Return True if *suffix* is in the highlighted set.

        Override in subclasses with non-trivial highlight membership
        (e.g. named-alias selectors like ``"top"``).
        """
        return suffix in self._highlighted

    def resolve_effective_state(self, suffix: str) -> str:
        """Combine get_state(suffix) with the highlight override.

        Returns ``"highlight"`` when the part is idle and highlighted;
        otherwise returns the stored state unchanged.
        """
        state = self.get_state(suffix)
        if state == "idle" and self._is_highlighted(suffix):
            return "highlight"
        return state

    def emit_annotation_arrows(
        self,
        parts: "list[str]",
        annotations: "list[dict[str, Any]]",
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
        scene_segments: "tuple[tuple[Any, float, float, int], ...] | None" = None,
        self_offset: "tuple[float, float] | None" = None,
        cell_metrics: "CellMetrics | None" = None,
    ) -> None:
        """Emit arrow and plain-pointer SVG for *annotations* into *parts*.

        Handles both Bezier-arc arrows (``arrow_from`` key) and plain
        straight-pointer annotations (``arrow=true``).  Honours the
        ``_min_arrow_above`` floor so the translate offset stays stable
        across frames.

        Instance attributes consulted:
            _arrow_cell_height  — virtual cell height for arc offset (default 40)
            _arrow_layout       — ``"1d"`` or ``"2d"`` (default ``"1d"``)
            _arrow_shorten      — pixels to shorten src/dst by (default 0)

        Parameters
        ----------
        scene_segments:
            Cross-primitive obstacle segments from the scene renderer (W3-α+).
            Each entry: ``(ObstacleSegment, x_off, y_off, prim_id)``.
            Segments from ``id(self)`` are skipped (self-exclusion).
        self_offset:
            The ``(x_off, y_off)`` translate of this primitive in the scene.
            Required when *scene_segments* is provided.
        """
        if not annotations:
            return

        emit_arrow_marker_defs(parts, annotations)

        # R-31 / W3-α+: merge local segments and cross-primitive segments.
        # 1. Start from this primitive's own local segments.
        _merged_segs: "list[Any]" = list(self.resolve_obstacle_segments())

        # 2. Append translated segments from other primitives in the scene.
        if scene_segments and self_offset is not None:
            self_x, self_y = self_offset
            self_id = id(self)
            for seg, src_x, src_y, src_prim_id in scene_segments:
                if src_prim_id == self_id:
                    # Skip self — already counted via resolve_obstacle_segments().
                    continue
                dx = src_x - self_x
                dy = src_y - self_y
                _merged_segs.append(_translate_segment(seg, dx, dy))

        # Convert to _Obstacle tuples once per frame.
        _prim_seg_obs: "tuple[_Obstacle, ...]" = ()
        if _merged_segs:
            _prim_seg_obs = tuple(_segment_to_obstacle(s) for s in _merged_segs)

        # W1: this primitive's own content cells join the obstacle set as
        # light SHOULD AABBs so P1/P5 can see (and avoid) content occlusion.
        _content_rects = self.resolve_self_content_rects()
        if _content_rects:
            _prim_seg_obs = _prim_seg_obs + tuple(
                _Obstacle(
                    kind="content_cell",
                    x=float(b.x) + float(b.width) / 2.0,
                    y=float(b.y) + float(b.height) / 2.0,
                    width=float(b.width),
                    height=float(b.height),
                    severity="SHOULD",
                )
                for b in _content_rects
            )

        # R-31 ext: accumulate prior-annotation arrow-stroke segments across the
        # annotation loop.  Each emit_*_arrow_svg call returns sampled segments
        # which are appended here and merged into the obstacle set for the NEXT
        # annotation's pill placement.  Segments are SHOULD-severity only (no
        # hard-block); they contribute the P7 edge-occlusion penalty term.
        prior_arrow_segments: "list[Any]" = []

        placed: "list[_LabelPlacement]" = []
        for ann in annotations:
            arrow_from = ann.get("arrow_from", "")

            # Build the combined obstacle tuple for this annotation:
            # base primitive segments + cross-primitive segments + prior arrow strokes.
            if prior_arrow_segments:
                _prior_obs: "tuple[_Obstacle, ...]" = tuple(
                    _segment_to_obstacle(s) for s in prior_arrow_segments
                )
                _combined_obs: "tuple[_Obstacle, ...]" = (
                    _prim_seg_obs + _prior_obs
                )
            else:
                _combined_obs = _prim_seg_obs

            if not arrow_from and ann.get("arrow"):
                dst_point = self.resolve_annotation_point(ann.get("target", ""))
                if dst_point is not None:
                    _new_segs = emit_plain_arrow_svg(
                        parts,
                        ann,
                        dst_point=dst_point,
                        render_inline_tex=render_inline_tex,
                        placed_labels=placed,
                        primitive_obstacles=_combined_obs if _combined_obs else None,
                    )
                    if _new_segs:
                        prior_arrow_segments.extend(_new_segs)
                continue

            if not arrow_from:
                # Position-only annotation: has a label and a position, but
                # no arrow_from and no arrow=true.  Emit a pill at the
                # computed offset from the target cell.  Plane2D-specific
                # label drop is handled separately; this covers Array and
                # DPTable (and any future primitive that implements
                # resolve_annotation_point).  Pills anchor at the element
                # *center* via resolve_label_anchor (Defect 1a); the base
                # default delegates to resolve_annotation_point so non-Array
                # primitives are unaffected.
                label_text = ann.get("label", "")
                # R-35 bracket glyph: a no-fill dashed rounded outline
                # hugging the block (3px outward), emitted in its own
                # annotation group so the extent parser, differ and runtime
                # treat it like any other decoration. Block targets only —
                # a single cell already reads as a unit.
                if ann.get("bracket") and ".block[" in ann.get("target", ""):
                    _bbox = self.resolve_annotation_box(ann.get("target", ""))
                    if _bbox is not None:
                        _bstyle = ARROW_STYLES.get(
                            ann.get("color", "info"), ARROW_STYLES["info"]
                        )
                        _bkey = f"{ann.get('target', '')}-block-bracket"
                        parts.append(
                            f'  <g class="scriba-annotation scriba-annotation-'
                            f'{annotation_color_class(ann.get("color", "info"))}"'
                            f' data-annotation="{_escape_xml(_bkey)}">'
                            f'<rect x="{_bbox.x - 3}" y="{_bbox.y - 3}"'
                            f' width="{_bbox.width + 6}" height="{_bbox.height + 6}"'
                            f' rx="6" ry="6" fill="none"'
                            f' stroke="{_bstyle["stroke"]}" stroke-width="1.5"'
                            f' stroke-opacity="0.55" stroke-dasharray="4,3"/>'
                            f"</g>"
                        )
                if label_text:
                    dst_point = self.resolve_label_anchor(ann.get("target", ""))
                    if dst_point is not None:
                        # Defect 1b — register the annotated cell as a MUST
                        # blocker so the placement nudger never pushes the pill
                        # back onto the cell it labels (spec R-02, scoped to the
                        # *annotated* cell only). Limited to ``position=below``,
                        # where the over-cell failure occurs; ``above``/``left``/
                        # ``right`` pills are already offset clear of the cell,
                        # so adding the blocker there only perturbs placement.
                        # Primitives without a box (default ``None``) add
                        # nothing → unaffected.
                        _cell_obs = _combined_obs
                        target_box = self.resolve_annotation_box(
                            ann.get("target", "")
                        )
                        _cell_w = float(target_box.width) if target_box is not None else None
                        if target_box is not None and ann.get("position") == "below":
                            bx, by, bw, bh = target_box
                            _cell_obs = _cell_obs + (
                                _Obstacle(
                                    kind="target_cell",
                                    x=float(bx) + float(bw) / 2.0,
                                    y=float(by) + float(bh) / 2.0,
                                    width=float(bw),
                                    height=float(bh),
                                    severity="MUST",
                                ),
                            )
                        emit_position_label_svg(
                            parts,
                            ann,
                            anchor_point=dst_point,
                            cell_height=self._arrow_cell_height,
                            render_inline_tex=render_inline_tex,
                            placed_labels=placed,
                            primitive_obstacles=_cell_obs if _cell_obs else None,
                            cell_width=_cell_w,
                            below_baseline=self.resolve_below_baseline(),
                            is_range="range[" in ann.get("target", ""),
                        )
                # Position-only annotations have no arrow geometry to accumulate.
                continue

            src_point = self.resolve_annotation_point(arrow_from)
            dst_point = self.resolve_annotation_point(ann.get("target", ""))
            if src_point is None or dst_point is None:
                continue

            target = ann.get("target", "")
            arrow_index = 0
            for other in annotations:
                if other is ann:
                    break
                if other.get("target") == target and other.get("arrow_from"):
                    arrow_index += 1

            kwargs: "dict[str, Any]" = {}
            if self._arrow_layout == "2d":
                kwargs["layout"] = "2d"
            if self._arrow_shorten:
                kwargs["shorten_src"] = self._arrow_shorten
                kwargs["shorten_dst"] = self._arrow_shorten

            _new_segs = emit_arrow_svg(
                parts,
                ann,
                src_point=src_point,
                dst_point=dst_point,
                arrow_index=arrow_index,
                cell_height=self._arrow_cell_height,
                render_inline_tex=render_inline_tex,
                placed_labels=placed,
                primitive_obstacles=_combined_obs if _combined_obs else None,
                cell_metrics=cell_metrics,
                **kwargs,
            )
            if _new_segs:
                prior_arrow_segments.extend(_new_segs)

    def apply_command(
        self,
        params: "dict[str, Any]",
        *,
        target_suffix: "str | None" = None,
    ) -> None:
        """Apply a primitive-specific command. Default: no-op. Override per primitive."""
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def state_class(target_state: str) -> str:
    """Return the CSS class for a given state name."""
    return f"scriba-state-{target_state}"
