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
from scriba.animation.primitives._text_render import (  # noqa: F401 — explicit for IDEs
    _INLINE_MATH_RE,
    _char_display_width,
    _escape_xml,
    _has_math,
    _render_mixed_html,
    _render_split_label_svg,
    _render_svg_text,
    estimate_text_width,
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
)


# ---------------------------------------------------------------------------
# Primitive registry — auto-populated by @register_primitive decorator
# ---------------------------------------------------------------------------

_PRIMITIVE_REGISTRY: dict[str, type["PrimitiveBase"]] = {}


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
_CAPTION_FONT_PX: int = 11          # must match --scriba-label-font / array._FONT_SIZE_CAPTION
_CAPTION_MIN_WRAP_W: int = 200      # caption never wraps narrower than this
_CAPTION_SAFETY_PAD: int = 8        # estimate_text_width under-counts; pad
# Per-line box height for captions containing $...$ math. KaTeX inline
# spans at 11px reach ~15px (superscript strut), so the plain 13px line
# would clip them; 18px clears the strut with 1-2px of air.
_MATH_CAPTION_LINE_H: int = 18

# Top-band caption (tree, graph) — caption sits ABOVE the content.
_TOP_CAPTION_BAND: int = 28         # historical single-line band height
# top_y so the CSS `dominant-baseline: central` lands the line on the
# historical baseline (_PRIMITIVE_LABEL_Y): top_y + font//2 == baseline.
_TOP_CAPTION_TOP_Y: int = _PRIMITIVE_LABEL_Y - _CAPTION_FONT_PX // 2


# ---------------------------------------------------------------------------
# Abstract base for all animation primitives
# ---------------------------------------------------------------------------


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
            estimate_text_width(
                _label_width_text(ln) if _label_has_math(ln) else ln,
                _CAPTION_FONT_PX,
            )
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
            return len(lines) * _MATH_CAPTION_LINE_H
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
            math_h = _MATH_CAPTION_LINE_H
            for i, ln in enumerate(lines):
                out.append(
                    "  "
                    + _render_svg_text(
                        ln,
                        center_x,
                        top_y + math_h // 2 + i * math_h,
                        fill=THEME["fg_muted"],
                        css_class="scriba-primitive-label",
                        font_size=str(_CAPTION_FONT_PX),
                        text_anchor="middle",
                        dominant_baseline="central",
                        fo_width=footprint_width,
                        fo_height=math_h,
                        render_inline_tex=render_inline_tex,
                    )
                )
            return
        if len(lines) == 1:
            out.append(
                "  "
                + _render_svg_text(
                    lines[0],
                    center_x,
                    top_y + _CAPTION_FONT_PX // 2,
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
                f"{_escape_xml(ln)}{'' if i == len(lines) - 1 else ' '}</tspan>"
                for i, ln in enumerate(lines)
            )
            out.append(
                f'  <text class="scriba-primitive-label" x="{center_x}"'
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
