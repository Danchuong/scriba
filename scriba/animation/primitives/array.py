"""Array primitive — a fixed-length horizontal row of indexed cells.

See ``docs/spec/primitives.md`` §3 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import E1103, _animation_error
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
    _escape_xml,
    _inset_rect_attrs,
    _render_svg_text,
    arrow_height_above,
    position_label_height_above,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._types import _CELL_HORIZONTAL_PADDING
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


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

# Full-qualified selectors (with shape name prefix) — canonical from base.py.
_CELL_RE = CELL_1D_RE
_RANGE_RE = RANGE_RE
_ALL_RE = ALL_RE

# Suffix-only regexes (no shape name prefix) — local, no base.py equivalent.
_SUFFIX_CELL_RE = re.compile(r"^cell\[(?P<idx>\d+)\]$")
_SUFFIX_RANGE_RE = re.compile(r"^range\[(?P<lo>\d+):(?P<hi>\d+)\]$")


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

        # Pre-compute the bottom stack (index labels + caption) once, via
        # the vstack helper which guarantees glyph boxes cannot overlap
        # regardless of baseline or font size. See ``layout.py`` for the
        # Wave 8 rationale. The ``stack_items`` list is built in visual
        # top-to-bottom order; the returned coordinates are keyed back to
        # their role so the cell loop below and the caption emission
        # after it can look them up without counting positions.
        stack_items: list[TextBox] = []
        if self.labels is not None:
            stack_items.append(
                TextBox(
                    font_size=_FONT_SIZE_INDEX,
                    role="label",
                    baseline="hanging",
                )
            )
        if self.label is not None:
            stack_items.append(
                TextBox(
                    font_size=_FONT_SIZE_CAPTION,
                    role="caption",
                    baseline="central",
                )
            )
        stack_ys = vstack(
            stack_items,
            start_y=CELL_HEIGHT + INDEX_LABEL_OFFSET,
            gap=_STACK_GAP,
        )
        stack_y_by_role: dict[str, int] = {
            box.role: int(y) for box, y in zip(stack_items, stack_ys)
        }

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
            x = int(i * (cw + CELL_GAP))
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

        # Caption label below the array — y computed once by vstack above
        if self.label is not None:
            total_width = self._total_width()
            center_x = int(total_width // 2)
            lines.append(
                "  "
                + _render_svg_text(
                    self.label,
                    center_x,
                    stack_y_by_role["caption"],
                    fill=THEME["fg_muted"],
                    css_class="scriba-primitive-label",
                    fo_width=total_width,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
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
        w = self._total_width()

        # Rebuild the stack descriptor used by emit_svg — must stay in
        # sync with the branches above. ``stack_bottom`` returns the
        # visual pixel where the last glyph box ends, so the bounding
        # box is exactly tight against the rendered content.
        stack_items: list[TextBox] = []
        if self.labels is not None:
            stack_items.append(
                TextBox(
                    font_size=_FONT_SIZE_INDEX,
                    role="label",
                    baseline="hanging",
                )
            )
        if self.label is not None:
            stack_items.append(
                TextBox(
                    font_size=_FONT_SIZE_CAPTION,
                    role="caption",
                    baseline="central",
                )
            )
        h = stack_bottom(
            stack_items,
            start_y=CELL_HEIGHT + INDEX_LABEL_OFFSET,
            gap=_STACK_GAP,
        ) if stack_items else float(CELL_HEIGHT)

        computed = arrow_height_above(
            effective_anns, self.resolve_annotation_point, cell_height=CELL_HEIGHT
        )
        pos_above = position_label_height_above(effective_anns, cell_height=CELL_HEIGHT)
        arrow_above = max(computed, pos_above, getattr(self, "_min_arrow_above", 0))
        h += arrow_above
        return BoundingBox(x=0, y=0, width=float(w), height=float(h))

    def _cell_center(self, selector_str: str) -> tuple[int, int] | None:
        """Return the ``(cx, cy)`` pixel center of a cell selector."""
        m = _CELL_RE.match(selector_str)
        if m and m.group("name") == self.name:
            i = int(m.group("idx"))
            if 0 <= i < self.size:
                cw = self._cell_width
                x = int(i * (cw + CELL_GAP) + cw // 2)
                y = 0  # top edge of cell — arrows curve above
                return (x, y)
        return None

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Delegate to ``_cell_center`` for annotation arrow resolution."""
        result = self._cell_center(selector)
        if result is None:
            return None
        return (float(result[0]), float(result[1]))

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []

    # -- internal -----------------------------------------------------------

    def _total_width(self) -> int:
        if self.size == 0:
            return 0
        return self.size * self._cell_width + (self.size - 1) * CELL_GAP


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
