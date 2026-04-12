"""Array primitive — a fixed-length horizontal row of indexed cells.

See ``docs/spec/primitives.md`` §3 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import E1103, animation_error
from scriba.animation.primitives.base import (
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    INDEX_LABEL_OFFSET,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    _inset_rect_attrs,
    _render_svg_text,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
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


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

_CELL_RE = re.compile(r"^(?P<name>\w+)\.cell\[(?P<idx>\d+)\]$")
_RANGE_RE = re.compile(r"^(?P<name>\w+)\.range\[(?P<lo>\d+):(?P<hi>\d+)\]$")
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")

# Suffix-only regexes (no shape name prefix)
_SUFFIX_CELL_RE = re.compile(r"^cell\[(?P<idx>\d+)\]$")
_SUFFIX_RANGE_RE = re.compile(r"^range\[(?P<lo>\d+):(?P<hi>\d+)\]$")


# ---------------------------------------------------------------------------
# ArrayPrimitive
# ---------------------------------------------------------------------------


@register_primitive("Array")
class ArrayPrimitive(PrimitiveBase):
    """A fixed-length horizontal row of indexed cells.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type: str = "array"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "cell[{i}]": "cell by index",
        "range[{lo}:{hi}]": "contiguous range of cells",
        "all": "all cells",
    }

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)
        size = self.params.get("size", self.params.get("n"))
        if size is None:
            raise animation_error(
                "E1400",
                detail="Array requires 'size' or 'n' parameter",
                hint="example: \\shape{a}{Array}{size=10}",
            )
        size = int(size)
        if size < 1:
            raise animation_error(
                "E1401",
                detail=f"Array size {size} is out of range; valid: 1..10000",
            )
        if size > 10_000:
            raise animation_error(
                "E1401",
                detail=(
                    f"Array size {size} exceeds maximum; valid: 1..10000"
                ),
            )

        data: list[Any] = list(self.params.get("data", []))
        if data and len(data) != size:
            raise animation_error(
                "E1402",
                detail=(
                    f"Array 'data' length ({len(data)}) does not match "
                    f"size ({size}); valid: len(data) == size or omit data"
                ),
            )
        if not data:
            data = [""] * size

        self.shape_name: str = name
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
        self._cell_width: int = max(CELL_WIDTH, max_content_w + 12, max_label_w + 8)

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
    ) -> str:
        """Emit SVG ``<g>`` for the array.

        Reads state from internal ``_states``/``_values``/``_annotations``
        managed by :class:`PrimitiveBase`.
        """
        effective_anns = self._annotations

        # Compute vertical space needed above cells for arrow curves
        arrow_above = self._arrow_height_above(effective_anns)

        lines: list[str] = [
            f'<g data-primitive="array" data-shape="{self.shape_name}">'
        ]

        # Shift all content down so arrows curve into valid space above y=0
        if arrow_above > 0:
            lines.append(f'  <g transform="translate(0, {arrow_above})">')

        # Emit arrowhead marker defs when annotations with arrows are present
        arrow_anns = [a for a in effective_anns if a.get("arrow_from")]
        if arrow_anns:
            colors_used = {a.get("color", "info") for a in arrow_anns}
            lines.append("  <defs>")
            for color in sorted(colors_used):
                marker_style = self._ARROW_STYLES.get(
                    color, self._ARROW_STYLES["info"]
                )
                marker_fill = marker_style["stroke"]
                lines.append(
                    f'    <marker id="scriba-arrow-{color}" '
                    f'viewBox="0 0 10 10" refX="10" refY="5" '
                    f'markerWidth="6" markerHeight="6" '
                    f'orient="auto-start-reverse">'
                    f'<title>Arrowhead ({color})</title>'
                    f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{marker_fill}"/>'
                    f"</marker>"
                )
            lines.append("  </defs>")

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
            target = f"{self.shape_name}.cell[{i}]"
            suffix = f"cell[{i}]"

            state_name = self.get_state(suffix)
            value = self.get_value(suffix)
            if value is None:
                value = self.data[i]
            highlighted = suffix in self._highlighted

            # β redesign — highlight becomes a state rather than an
            # additive dashed overlay. A plain cell that is marked
            # highlighted becomes ``highlight``; a cell already in a
            # stronger signal state (current/error/good/etc.) keeps its
            # state so the two signals don't visually compete.
            if highlighted and state_name == "idle":
                effective_state = "highlight"
            else:
                effective_state = state_name

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
            for ann in effective_anns:
                self._emit_arrow(lines, ann, annotations=effective_anns, render_inline_tex=render_inline_tex)

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

        arrow_above = self._arrow_height_above(effective_anns)
        h += arrow_above
        return BoundingBox(x=0, y=0, width=float(w), height=float(h))

    # -- internal: arrows ---------------------------------------------------

    # Inline style map for arrow annotations — each color gets distinct
    # stroke, width, opacity, and label styling so that winner vs loser
    # arrows are visually differentiated without relying on CSS classes.
    _ARROW_STYLES: ClassVar[dict[str, dict[str, str]]] = {
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

    def _emit_arrow(
        self,
        lines: list[str],
        ann: dict[str, Any],
        annotations: list[dict[str, Any]] | None = None,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> None:
        """Emit a cubic Bezier arrow annotation."""
        color = ann.get("color", "info")
        label_text = ann.get("label", "")
        target = ann.get("target", "")
        arrow_from = ann.get("arrow_from", "")

        if not arrow_from:
            return

        src_center = self._cell_center(arrow_from)
        dst_center = self._cell_center(target)

        if src_center is None or dst_center is None:
            return

        x1, y1 = src_center
        x2, y2 = dst_center

        # Compute arrow_index: how many earlier arrows target the same cell
        arrow_index = 0
        if annotations:
            for other in annotations:
                if other is ann:
                    break
                if (
                    other.get("target") == target
                    and other.get("arrow_from")
                ):
                    arrow_index += 1

        # Control points: curve upward — scale with horizontal distance
        # and stagger when multiple arrows target the same cell
        base_offset = max(CELL_HEIGHT * 0.75, abs(x2 - x1) * 0.25)
        stagger = CELL_HEIGHT * 0.5
        total_offset = base_offset + arrow_index * stagger

        mid_x = int((x1 + x2) // 2)
        mid_y = int(min(y1, y2) - total_offset)
        cx1 = int((x1 + mid_x) // 2)
        cy1 = mid_y
        cx2 = int((x2 + mid_x) // 2)
        cy2 = mid_y

        # Resolve inline style for this color
        style = self._ARROW_STYLES.get(color, self._ARROW_STYLES["info"])
        s_stroke = style["stroke"]
        s_width = style["stroke_width"]
        s_opacity = style["opacity"]

        ann_desc = (
            f"Arrow from {_escape_xml(str(arrow_from))} "
            f"to {_escape_xml(str(target))}"
        )
        if label_text:
            ann_desc += f": {_escape_xml(label_text)}"

        ann_key = f"{target}-{arrow_from}" if arrow_from else f"{target}-solo"
        lines.append(
            f'  <g class="scriba-annotation scriba-annotation-{color}"'
            f' data-annotation="{_escape_xml(ann_key)}"'
            f' opacity="{s_opacity}"'
            f' role="graphics-symbol" aria-label="{ann_desc}">'
        )
        lines.append(
            f'    <path d="M{x1},{y1} C{cx1},{cy1} {cx2},{cy2} {x2},{y2}" '
            f'stroke="{s_stroke}" stroke-width="{s_width}" fill="none" '
            f'marker-end="url(#scriba-arrow-{color})">'
            f'<title>{ann_desc}</title>'
            f'</path>'
        )
        if label_text:
            label_y = mid_y - 4  # slightly above the curve peak
            l_fill = style["label_fill"]
            l_weight = style["label_weight"]
            l_size = style["label_size"]
            lines.append(
                "    "
                + _render_svg_text(
                    label_text,
                    mid_x,
                    label_y,
                    fill=l_fill,
                    font_weight=l_weight,
                    font_size=l_size,
                    text_anchor="middle",
                    dominant_baseline="auto",
                    render_inline_tex=render_inline_tex,
                )
            )
        lines.append("  </g>")

    def _arrow_height_above(self, annotations: list[dict[str, Any]]) -> int:
        """Compute the max vertical extent above y=0 that arrows need."""
        if not annotations:
            return 0
        arrow_anns = [a for a in annotations if a.get("arrow_from")]
        if not arrow_anns:
            return 0

        max_height = 0
        for idx, ann in enumerate(arrow_anns):
            src = self._cell_center(ann.get("arrow_from", ""))
            dst = self._cell_center(ann.get("target", ""))
            if src is None or dst is None:
                continue
            x1, _y1 = src
            x2, _y2 = dst
            # Count arrows targeting same cell before this one
            target = ann.get("target", "")
            arrow_index = sum(
                1
                for j, a in enumerate(arrow_anns)
                if a.get("target") == target
                and j < idx
            )
            base_offset = max(CELL_HEIGHT * 0.75, abs(x2 - x1) * 0.25)
            stagger = CELL_HEIGHT * 0.5
            total_offset = base_offset + arrow_index * stagger
            max_height = max(max_height, int(total_offset) + 14)

        return max_height

    def _cell_center(self, selector_str: str) -> tuple[int, int] | None:
        """Return the ``(cx, cy)`` pixel center of a cell selector."""
        m = _CELL_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            i = int(m.group("idx"))
            if 0 <= i < self.size:
                cw = self._cell_width
                x = int(i * (cw + CELL_GAP) + cw // 2)
                y = 0  # top edge of cell — arrows curve above
                return (x, y)
        return None

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
