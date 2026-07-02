"""Array primitive — a fixed-length horizontal row of indexed cells.

See ``docs/spec/primitives.md`` §3 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives.base import (
    ALL_RE,
    CELL_1D_RE,
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    CellMetrics,
    INDEX_LABEL_OFFSET,
    RANGE_RE,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _inset_rect_attrs,
    _label_has_math,
    _LABEL_PILL_MAX_W_PX,
    _LABEL_PILL_PAD_X,
    _render_svg_text,
    _wrap_label_lines,
    arrow_height_above,
    position_label_height_above,
    position_below_lane_height,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._types import (
    _CELL_HORIZONTAL_PADDING,
    SUFFIX_CELL_RE,
    SUFFIX_RANGE_RE,
)
from scriba.animation.primitives.layout import TextBox, stack_bottom, vstack

# Font sizes for each role — must match the CSS variables below. A CI
# guard test (``tests/unit/test_css_font_sync.py``) parses the stylesheet
# and asserts these values equal the numbers in
# ``scriba-scene-primitives.css``::
#
#   --scriba-cell-font         700 14px inherit
#   --scriba-cell-index-font   500 10px ui-monospace, monospace
#   --scriba-label-font        600 11px ui-monospace, monospace
_FONT_SIZE_CELL: int = 14
_FONT_SIZE_INDEX: int = 10
_FONT_SIZE_CAPTION: int = 11

# Vertical whitespace between consecutive items in the bottom stack
# (index-label row → caption row). Replaces the old ``_CAPTION_GAP``
# magic number. ``vstack`` guarantees glyph boxes cannot overlap for any
# combination of font sizes within the ±5 % cross-font drift envelope
# absorbed by this gap. See ``layout.py`` for the invariant contract.
_STACK_GAP: int = 9
# Caption wrap/pad constants now live in base (PrimitiveBase Layer A helpers,
# shared by all caption-bearing primitives).


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

# Full-qualified selectors (with shape name prefix) — canonical from base.py.
_CELL_RE = CELL_1D_RE
_RANGE_RE = RANGE_RE
_ALL_RE = ALL_RE

# Suffix-only regexes (no shape name prefix) — canonical from ._types.
_SUFFIX_CELL_RE = SUFFIX_CELL_RE
_SUFFIX_RANGE_RE = SUFFIX_RANGE_RE


# ---------------------------------------------------------------------------
# ArrayPrimitive
# ---------------------------------------------------------------------------


@register_primitive("Array")
@_protocol_register
class ArrayPrimitive(PrimitiveBase):
    """A fixed-length horizontal row of indexed cells.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type = "array"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "cell[{i}]": "cell by index",
        "range[{lo}:{hi}]": "contiguous range of cells",
        "all": "all cells",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "size",
        "n",
        "data",
        "labels",
        "label",
        # ``values`` is an alias that supplies BOTH ``size`` (inferred from
        # len) and ``data`` in a single parameter, so authors can write
        # ``\shape{a}{Array}{values=[1,2,3]}`` without repeating themselves.
        "values",
    })

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)
        size = self.params.get("size", self.params.get("n"))
        values_alias = self.params.get("values")
        if size is None and isinstance(values_alias, list):
            size = len(values_alias)
        if size is None:
            raise _animation_error(
                "E1400",
                detail="Array requires 'size', 'n', or 'values' parameter",
                hint="example: \\shape{a}{Array}{size=10}",
            )
        size = int(size)
        if size < 1:
            raise _animation_error(
                "E1401",
                detail=f"Array size {size} is out of range; valid: 1..10000",
            )
        if size > 10_000:
            raise _animation_error(
                "E1401",
                detail=(
                    f"Array size {size} exceeds maximum; valid: 1..10000"
                ),
            )

        raw_data = self.params.get("data")
        if raw_data is None and isinstance(values_alias, list):
            raw_data = values_alias
        data: list[Any] = list(raw_data or [])
        if data and len(data) != size:
            raise _animation_error(
                "E1402",
                detail=(
                    f"Array 'data' length ({len(data)}) does not match "
                    f"size ({size}); valid: len(data) == size or omit data"
                ),
            )
        if not data:
            data = [""] * size

        self.size: int = size
        self.data: list[Any] = data
        self.labels: str | None = self.params.get("labels")
        self.label: str | None = self.params.get("label")

        # Compute dynamic cell width from data and labels
        max_content_w = max(
            (estimate_text_width(str(v), 14) for v in self.data), default=0
        )
        if self.labels:
            parsed = _parse_index_labels(self.labels, self.size)
            max_label_w = max(
                (estimate_text_width(str(lb), 11) for lb in parsed), default=0
            )
        else:
            max_label_w = 0
        self._cell_width: int = max(CELL_WIDTH, max_content_w + _CELL_HORIZONTAL_PADDING, max_label_w + 8)

    # -- PrimitiveBase interface --------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector suffixes."""
        parts: list[str] = []
        for i in range(self.size):
            parts.append(f"cell[{i}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        """Check whether *suffix* is a valid addressable part."""
        m = _SUFFIX_CELL_RE.match(suffix)
        if m:
            return 0 <= int(m.group("idx")) < self.size

        m = _SUFFIX_RANGE_RE.match(suffix)
        if m:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            return 0 <= lo <= hi < self.size

        return suffix == "all"

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the array.

        Reads state from internal ``_states``/``_values``/``_annotations``
        managed by :class:`PrimitiveBase`.
        """
        effective_anns = self._annotations

        # Compute vertical space needed above cells for arrow curves and
        # position=above pill labels.
        computed = arrow_height_above(
            effective_anns, self.resolve_annotation_point, cell_height=CELL_HEIGHT
        )
        pos_above = position_label_height_above(effective_anns, cell_height=CELL_HEIGHT)
        arrow_above = max(computed, pos_above, getattr(self, "_min_arrow_above", 0))

        lines: list[str] = [
            f'<g data-primitive="array" data-shape="{self.name}">'
        ]

        # Shift all content down so arrows curve into valid space above y=0
        if arrow_above > 0:
            lines.append(f'  <g transform="translate(0, {arrow_above})">')

        # Bottom area, visual top-to-bottom: index row → callout lane
        # (position=below pills) → caption. Only the index row is in this
        # vstack; the lane and caption are placed below it (see the caption
        # block after the cell loop) so the caption is always the bottom-most
        # element, beneath any callout pills.
        stack_items = self._index_stack_items()
        stack_ys = vstack(
            stack_items,
            start_y=CELL_HEIGHT + INDEX_LABEL_OFFSET,
            gap=_STACK_GAP,
        )
        stack_y_by_role: dict[str, int] = {
            box.role: int(y) for box, y in zip(stack_items, stack_ys)
        }

        # Defect 6 — when a caption is wider than the cell row, the footprint
        # (bbox) widens but the renderer centers the whole group on bbox width
        # and ignores bbox.x. Shift the cell row right by ``row_dx`` so cells
        # stay centered under the caption. Anchors apply the same shift
        # (``_cell_center`` / ``_range_center``) so annotations track the row.
        row_dx = self._row_dx()

        for i in range(self.size):
            target = f"{self.name}.cell[{i}]"
            suffix = f"cell[{i}]"

            value = self.get_value(suffix)
            if value is None:
                value = self.data[i]
            effective_state = self.resolve_effective_state(suffix)

            css = state_class(effective_state)
            # ``svg_style_attrs`` is still used for <text> fill until the
            # CSS text rule ships; rect fill/stroke/stroke-width are owned
            # by the state class in scriba-scene-primitives.css.
            colors = svg_style_attrs(effective_state)

            cw = self._cell_width
            x = int(i * (cw + CELL_GAP)) + row_dx
            y = 0

            lines.append(
                f'  <g data-target="{target}" class="{css}">'
            )
            rect_attrs = _inset_rect_attrs(x, y, cw, CELL_HEIGHT)
            lines.append(
                f'    <rect x="{rect_attrs["x"]}" y="{rect_attrs["y"]}" '
                f'width="{rect_attrs["width"]}" '
                f'height="{rect_attrs["height"]}"/>'
            )
            text_x = int(x + cw // 2)
            text_y = int(y + CELL_HEIGHT // 2)
            lines.append(
                "    "
                + _render_svg_text(
                    value,
                    text_x,
                    text_y,
                    fill=colors["text"],
                    fo_width=cw,
                    fo_height=CELL_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )
            lines.append("  </g>")

            # Index labels below the cell — y computed once by vstack above
            if self.labels is not None:
                idx_labels = _parse_index_labels(self.labels, self.size)
                lines.append(
                    "  "
                    + _render_svg_text(
                        idx_labels[i],
                        text_x,
                        stack_y_by_role["label"],
                        fill=THEME["fg_muted"],
                        css_class="scriba-index-label idx",
                        fo_width=cw,
                        fo_height=20,
                        render_inline_tex=render_inline_tex,
                    )
                )

        # Caption — the figure's description — placed BELOW the callout lane so
        # it is the bottom-most element (not buried between the index row and
        # the position=below pills). Wrapped to multiple lines so a long caption
        # never overflows the viewBox. Centered on the footprint width; cells
        # (shifted by row_dx) share the same center line.
        if self._caption_lines(self._total_width()):
            lane_h = position_below_lane_height(effective_anns, cell_height=CELL_HEIGHT)
            caption_top = int(self.resolve_below_baseline() + lane_h + _STACK_GAP)
            self._emit_caption(
                lines,
                content_width=self._total_width(),
                footprint_width=self._bbox_width(),
                top_y=caption_top,
                render_inline_tex=render_inline_tex,
            )

        # Arrow annotations
        if effective_anns:
            _cell_metrics = CellMetrics(
                cell_width=float(self._cell_width),
                cell_height=float(CELL_HEIGHT),
                grid_cols=int(self.size),
                grid_rows=1,
                origin_x=0.0,
                origin_y=0.0,
            )
            self.emit_annotation_arrows(
                lines,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
                cell_metrics=_cell_metrics,
            )

        # Close the translate group if we opened one for arrow space
        if arrow_above > 0:
            lines.append("  </g>")

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> BoundingBox:
        """Return ``(x, y, width, height)``.

        The height includes vertical space needed above the cells
        for arrow curves when annotations have been set, plus the
        vstack-computed bottom stack below the cells when index labels
        or a caption are present.
        """
        effective_anns = self._annotations
        # Defect 6 — the caption width participates in the footprint so a
        # caption wider than the cell row is not clipped by the viewBox.
        w = self._bbox_width()

        # Bottom area in visual order: index row → callout lane → caption.
        # ``resolve_below_baseline`` is the bottom of the index row (or the
        # cell bottom when there is no index); the lane and the (possibly
        # multi-line) caption stack below it. Single source shared with
        # emit_svg so geometry never drifts.
        below_baseline = self.resolve_below_baseline() or float(CELL_HEIGHT)
        lane_h = position_below_lane_height(effective_anns, cell_height=CELL_HEIGHT)
        bottom = below_baseline + lane_h
        caption_h = self._caption_block_height(self._total_width())
        if caption_h:
            bottom = below_baseline + lane_h + _STACK_GAP + caption_h

        computed = arrow_height_above(
            effective_anns, self.resolve_annotation_point, cell_height=CELL_HEIGHT
        )
        pos_above = position_label_height_above(effective_anns, cell_height=CELL_HEIGHT)
        arrow_above = max(computed, pos_above, getattr(self, "_min_arrow_above", 0))
        return BoundingBox(x=0, y=0, width=float(w), height=float(arrow_above + bottom))

    def _cell_center(self, selector_str: str) -> tuple[int, int] | None:
        """Return the ``(cx, cy)`` pixel center of a cell selector.

        ``cx`` includes ``_row_dx`` so anchors track the cell row when a wide
        caption shifts it (Defect 6 keeps content and anchors in sync).
        """
        m = _CELL_RE.match(selector_str)
        if m and m.group("name") == self.name:
            i = int(m.group("idx"))
            if 0 <= i < self.size:
                cw = self._cell_width
                x = int(i * (cw + CELL_GAP) + cw // 2) + self._row_dx()
                y = 0  # top edge of cell — arrows curve above
                return (x, y)
        return None

    def _range_center(self, selector_str: str) -> tuple[int, int] | None:
        """Return the ``(cx, cy)`` anchor for a ``range[lo:hi]`` selector.

        Defect 5 — ``range`` targets previously had no anchor, so a position
        label or arrow on a range was silently dropped. The span is inclusive
        (cells ``lo..hi``), matching the renderer's range expansion
        (``_frame_renderer.py`` ``range(lo, hi + 1)``). ``cx`` is the midpoint
        of the span's outer edges; ``cy`` is the cell top edge like cells.
        """
        m = _RANGE_RE.match(selector_str)
        if m and m.group("name") == self.name:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            if 0 <= lo <= hi < self.size:
                cw = self._cell_width
                left = lo * (cw + CELL_GAP)
                right = hi * (cw + CELL_GAP) + cw
                x = int((left + right) // 2) + self._row_dx()
                return (x, 0)
        return None

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Resolve a cell or range selector to its arrow anchor (cell top)."""
        result = self._cell_center(selector)
        if result is None:
            result = self._range_center(selector)
        if result is None:
            return None
        return (float(result[0]), float(result[1]))

    def resolve_label_anchor(self, selector: str) -> tuple[float, float] | None:
        """Anchor for position-only pill labels — the cell *center*.

        Defect 1a — pill offsets in ``emit_position_label_svg`` are measured
        from the element center (``ay ± cell_height/2``), but Array's arrow
        anchor is the cell *top* (``y=0``, so arrows curve above). Returning
        the top here makes a ``position=below`` pill land ``cell_height/2`` too
        high — inside the cell body. Shift to the center for labels while
        leaving ``resolve_annotation_point`` (arrows) on the top edge.
        """
        pt = self.resolve_annotation_point(selector)
        if pt is None:
            return None
        return (pt[0], pt[1] + CELL_HEIGHT / 2)

    def resolve_annotation_box(self, selector: str) -> BoundingBox | None:
        """Return the cell (or range) AABB so the pill placer treats it as a
        MUST blocker (Defect 1b). Coordinates are local and include ``_row_dx``
        so the box tracks the (possibly caption-shifted) cell row.

        Unconditional (not scoped to below pills like the newer cell primitives):
        Array's box predates the unified scoping and its committed output already
        includes the R-07/R-08 spanning leader on wide above-cell pills; scoping
        it would *remove* those established leaders. The newer primitives scope
        instead so they don't *introduce* such leaders (both choices = 0 churn).
        """
        cw = self._cell_width
        m = _CELL_RE.match(selector)
        if m and m.group("name") == self.name:
            i = int(m.group("idx"))
            if 0 <= i < self.size:
                x = i * (cw + CELL_GAP) + self._row_dx()
                return BoundingBox(x=int(x), y=0, width=int(cw), height=int(CELL_HEIGHT))
        m = _RANGE_RE.match(selector)
        if m and m.group("name") == self.name:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            if 0 <= lo <= hi < self.size:
                left = lo * (cw + CELL_GAP) + self._row_dx()
                right = hi * (cw + CELL_GAP) + cw + self._row_dx()
                return BoundingBox(
                    x=int(left), y=0, width=int(right - left), height=int(CELL_HEIGHT)
                )
        return None

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []

    # -- internal -----------------------------------------------------------

    def _index_stack_items(self) -> list[TextBox]:
        """The index-label row (the only fixed bottom-stack item).

        Visual bottom order is: index row → callout lane → caption. The lane
        and caption are placed *below* the index row (not in this vstack), so
        the caption always reads as the figure's description at the very
        bottom, beneath any ``position=below`` callout pills.
        """
        if self.labels is None:
            return []
        return [TextBox(font_size=_FONT_SIZE_INDEX, role="label", baseline="hanging")]

    def resolve_below_baseline(self) -> float | None:
        """Y where ``position=below`` callout pills start — just below the index
        row (or the cells when there is no index row). Pills sit here, and the
        caption is placed below them.
        """
        items = self._index_stack_items()
        if not items:
            return float(CELL_HEIGHT)
        return float(
            stack_bottom(items, start_y=CELL_HEIGHT + INDEX_LABEL_OFFSET, gap=_STACK_GAP)
        )

    def _total_width(self) -> int:
        """Width of the cell row only (no caption)."""
        if self.size == 0:
            return 0
        return self.size * self._cell_width + (self.size - 1) * CELL_GAP


    def _below_pill_width(self, label: str) -> int:
        """Rendered width of a ``position=below`` callout pill for *label*
        (wrapped the same way ``emit_position_label_svg`` wraps it)."""
        s = str(label)
        if _label_has_math(s):
            lines = [s]
        else:
            lines = _wrap_label_lines(s, max_px=_LABEL_PILL_MAX_W_PX, font_px=11)
        widest = max((estimate_text_width(ln, 11) for ln in lines), default=0)
        return widest + 2 * _LABEL_PILL_PAD_X

    def _bbox_width(self) -> int:
        """Footprint width: wide enough for the cell row, the caption, AND the
        ``position=below``/``left``/``right`` callout pills (which extend past
        the row on edge cells — otherwise they clip).

        Defect 6 (caption) + lane-pill extent + #1 left/right extent. Single
        source of truth shared by ``emit_svg`` and ``bounding_box``. Computed in
        content-local space (cells before ``row_dx``), centred on the cell-row
        centre, so the result is symmetric and ``row_dx`` keeps everything
        centred. (Anchors include ``row_dx`` so this stays non-circular by using
        content-local cell centres, not ``resolve_label_anchor``.)
        """
        content = self._total_width()
        cw = self._cell_width
        half = max(content / 2.0, self._caption_block_width(self._total_width()) / 2.0)
        center = content / 2.0
        gap = max(4.0, CELL_HEIGHT * 0.1)
        for a in self._annotations:
            pos = a.get("position", "above")
            if (
                not a.get("label")
                or pos not in ("below", "left", "right")
                or a.get("arrow_from")
                or a.get("arrow")
            ):
                continue
            target = a.get("target", "")
            m = _CELL_RE.match(target)
            if m and m.group("name") == self.name and 0 <= int(m.group("idx")) < self.size:
                cell_cx = int(m.group("idx")) * (cw + CELL_GAP) + cw / 2.0
            elif (mr := _RANGE_RE.match(target)) and mr.group("name") == self.name:
                lo, hi = int(mr.group("lo")), int(mr.group("hi"))
                cell_cx = (lo * (cw + CELL_GAP) + hi * (cw + CELL_GAP) + cw) / 2.0
            else:
                continue
            pw = self._below_pill_width(a["label"])
            if pos == "below":
                half = max(half, abs(cell_cx - center) + pw / 2.0)
            elif pos == "right":
                half = max(half, (cell_cx + pw + gap) - center)
            else:  # left
                half = max(half, center - (cell_cx - pw - gap))
        return int(2 * half)

    def _row_dx(self) -> int:
        """Horizontal shift that keeps the cell row centered under a wider
        caption. Zero unless the caption widens the footprint."""
        return (self._bbox_width() - self._total_width()) // 2


# ---------------------------------------------------------------------------
# Backward-compatible alias: ArrayInstance -> ArrayPrimitive
# ---------------------------------------------------------------------------

ArrayInstance = ArrayPrimitive


# ---------------------------------------------------------------------------
# Index label parser
# ---------------------------------------------------------------------------


def _parse_index_labels(fmt: str, size: int) -> list[str]:
    """Parse ``labels`` format string into a list of label strings.

    Supports:
    - ``"0..6"`` -> ``["0", "1", "2", "3", "4", "5", "6"]``
    - ``"dp[0]..dp[6]"`` -> ``["dp[0]", "dp[1]", ..., "dp[6]"]``
    """
    m = re.match(r"^(\d+)\.\.(\d+)$", fmt)
    if m:
        return [str(i) for i in range(size)]

    m = re.match(r"^(.+?)\[(\d+)\]\.\.(.+?)\[(\d+)\]$", fmt)
    if m:
        prefix = m.group(1)
        return [f"{prefix}[{i}]" for i in range(size)]

    # Fallback: plain indices
    return [str(i) for i in range(size)]
