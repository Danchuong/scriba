"""DPTable primitive — 1D or 2D table with optional transition arrows.

See ``docs/spec/primitives.md`` §5 for the authoritative specification.
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
    _LabelPlacement,
    arrow_height_above,
    emit_arrow_marker_defs,
    emit_arrow_svg,
    emit_plain_arrow_svg,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives.layout import TextBox, stack_bottom, vstack

# Per-role font sizes — must match the CSS variables in
# ``scriba-scene-primitives.css``. See the matching constants in
# ``array.py``; a CI guard test (``test_css_font_sync.py``) asserts
# equality for every role.
_FONT_SIZE_INDEX: int = 10
_FONT_SIZE_CAPTION: int = 11

# Vertical whitespace between consecutive items in the bottom stack
# (index-label row → caption row). ``vstack`` guarantees no glyph-box
# overlap for any baseline/font-size combination; see ``layout.py``.
_STACK_GAP: int = 9


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

_CELL_1D_RE = re.compile(r"^(?P<name>\w+)\.cell\[(?P<idx>\d+)\]$")
_CELL_2D_RE = re.compile(
    r"^(?P<name>\w+)\.cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$"
)
_RANGE_RE = re.compile(
    r"^(?P<name>\w+)\.range\[(?P<lo>\d+):(?P<hi>\d+)\]$"
)
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")

# Suffix-only regexes (no shape name prefix)
_SUFFIX_CELL_1D_RE = re.compile(r"^cell\[(?P<idx>\d+)\]$")
_SUFFIX_CELL_2D_RE = re.compile(r"^cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$")
_SUFFIX_RANGE_RE = re.compile(r"^range\[(?P<lo>\d+):(?P<hi>\d+)\]$")


# ---------------------------------------------------------------------------
# DPTablePrimitive
# ---------------------------------------------------------------------------


@register_primitive("DPTable")
class DPTablePrimitive(PrimitiveBase):
    """A 1D or 2D DP table with optional transition arrows.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type: str = "dptable"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "cell[{i}]": "cell by index (1D mode)",
        "cell[{r}][{c}]": "cell by row,col (2D mode)",
        "range[{lo}:{hi}]": "contiguous range of cells (1D mode)",
        "all": "all cells",
    }

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)
        n = self.params.get("n")
        rows = self.params.get("rows")
        cols = self.params.get("cols")

        if n is not None:
            # 1D mode
            n = int(n)
            if n < 1:
                raise animation_error(
                    "E1427",
                    detail=(
                        f"DPTable n {n} is out of range; valid: "
                        "positive integer"
                    ),
                )
            is_2d = False
            dim_rows = 1
            dim_cols = n
        elif rows is not None and cols is not None:
            # 2D mode
            is_2d = True
            dim_rows = int(rows)
            dim_cols = int(cols)
            if dim_rows < 1:
                raise animation_error(
                    "E1428",
                    detail=(
                        f"DPTable rows {dim_rows} is out of range; "
                        "valid: positive integer"
                    ),
                )
            if dim_cols < 1:
                raise animation_error(
                    "E1428",
                    detail=(
                        f"DPTable cols {dim_cols} is out of range; "
                        "valid: positive integer"
                    ),
                )
            n = dim_rows * dim_cols
        else:
            raise animation_error(
                "E1426",
                detail="DPTable requires 'n' (1D) or 'rows'+'cols' (2D)",
                hint="example: \\shape{t}{DPTable}{n=10}",
            )

        max_cells = dim_rows * dim_cols
        if max_cells > 250_000:
            raise animation_error(
                "E1425",
                detail=(
                    f"DPTable cell count {max_cells} (rows={dim_rows}, "
                    f"cols={dim_cols}) exceeds maximum; valid: "
                    f"rows*cols <= 250000"
                ),
            )

        data: list[Any] = list(self.params.get("data", []))
        if data and len(data) != n:
            raise animation_error(
                "E1429",
                detail=(
                    f"DPTable 'data' length ({len(data)}) does not match "
                    f"expected size ({n}); valid: len(data) == "
                    f"{'rows*cols' if is_2d else 'n'}"
                ),
            )
        if not data:
            data = [""] * n

        self.shape_name: str = name
        self.is_2d: bool = is_2d
        self.rows: int = dim_rows
        self.cols: int = dim_cols
        self.data: list[Any] = data
        self.labels: str | None = self.params.get("labels")
        self.label: str | None = self.params.get("label")

    # -- PrimitiveBase interface --------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector suffixes."""
        parts: list[str] = []
        if self.is_2d:
            for r in range(self.rows):
                for c in range(self.cols):
                    parts.append(f"cell[{r}][{c}]")
        else:
            for i in range(self.cols):
                parts.append(f"cell[{i}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        """Check whether *suffix* is a valid addressable part."""
        if self.is_2d:
            m = _SUFFIX_CELL_2D_RE.match(suffix)
            if m:
                r, c = int(m.group("row")), int(m.group("col"))
                return 0 <= r < self.rows and 0 <= c < self.cols
        else:
            m = _SUFFIX_CELL_1D_RE.match(suffix)
            if m:
                return 0 <= int(m.group("idx")) < self.cols

            m = _SUFFIX_RANGE_RE.match(suffix)
            if m:
                lo, hi = int(m.group("lo")), int(m.group("hi"))
                return 0 <= lo <= hi < self.cols

        return suffix == "all"

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the DP table."""
        effective_anns = self._annotations

        # Compute vertical space needed above cells for arrow curves
        arrow_above = self._arrow_height_above(effective_anns)

        lines: list[str] = [
            f'<g data-primitive="dptable" data-shape="{self.shape_name}">'
        ]

        # Shift all content down so arrows curve into valid space above y=0
        if arrow_above > 0:
            lines.append(f'  <g transform="translate(0, {arrow_above})">')

        # Emit arrowhead marker defs when annotations with arrows are present
        emit_arrow_marker_defs(lines, effective_anns)

        if self.is_2d:
            self._emit_2d_cells(lines, render_inline_tex=render_inline_tex)
        else:
            self._emit_1d_cells(lines, render_inline_tex=render_inline_tex)

        # Arrow annotations
        if effective_anns:
            placed: list[_LabelPlacement] = []
            for ann in effective_anns:
                self._emit_arrow(lines, ann, annotations=effective_anns, render_inline_tex=render_inline_tex, placed_labels=placed)

        # Caption label
        if self.label is not None:
            tw, th = self._grid_dimensions()
            center_x = int(tw // 2)
            # For the 1D-with-labels layout the caption is the second
            # item of a two-item vstack (index labels then caption) —
            # reuse the same helper Array uses. For the 2D layout the
            # caption sits directly below the cells with no index row
            # to clear, so a simple translation by ``INDEX_LABEL_OFFSET``
            # is fine. See ``layout.py`` for the Wave 8 rationale.
            if not self.is_2d and self.labels:
                caption_items = [
                    TextBox(
                        font_size=_FONT_SIZE_INDEX,
                        role="label",
                        baseline="hanging",
                    ),
                    TextBox(
                        font_size=_FONT_SIZE_CAPTION,
                        role="caption",
                        baseline="central",
                    ),
                ]
                stack_ys = vstack(
                    caption_items,
                    start_y=th + INDEX_LABEL_OFFSET,
                    gap=_STACK_GAP,
                )
                label_y = int(stack_ys[1])
            else:
                label_y = int(th + INDEX_LABEL_OFFSET)
            lines.append(
                "  "
                + _render_svg_text(
                    self.label,
                    center_x,
                    label_y,
                    fill=THEME["fg_muted"],
                    css_class="scriba-primitive-label",
                    fo_width=tw,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
            )

        # Close the translate group if we opened one for arrow space
        if arrow_above > 0:
            lines.append("  </g>")

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> BoundingBox:
        """Return ``(x, y, width, height)``.

        For the 1D-with-labels case the height is computed from
        ``stack_bottom`` so the box is exactly tight against the
        vstack-positioned index labels and caption. Other cases keep
        the simpler ``INDEX_LABEL_OFFSET`` translation.
        """
        tw, th = self._grid_dimensions()
        h = float(th)
        if not self.is_2d and self.labels:
            stack_items: list[TextBox] = [
                TextBox(
                    font_size=_FONT_SIZE_INDEX,
                    role="label",
                    baseline="hanging",
                )
            ]
            if self.label:
                stack_items.append(
                    TextBox(
                        font_size=_FONT_SIZE_CAPTION,
                        role="caption",
                        baseline="central",
                    )
                )
            h = stack_bottom(
                stack_items,
                start_y=th + INDEX_LABEL_OFFSET,
                gap=_STACK_GAP,
            )
        elif self.label:
            h += INDEX_LABEL_OFFSET
        # Reserve space above for arrow annotations (same as Array)
        arrow_above = self._arrow_height_above(self._annotations)
        h += arrow_above
        return BoundingBox(x=0, y=0, width=float(tw), height=h)

    # -- internal: cell emission -------------------------------------------

    def _emit_1d_cells(
        self,
        lines: list[str],
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> None:
        """Emit cells for 1D layout (identical to Array)."""
        idx_labels = (
            _parse_index_labels(self.labels, self.cols)
            if self.labels
            else None
        )

        for i in range(self.cols):
            target = f"{self.shape_name}.cell[{i}]"
            suffix = f"cell[{i}]"

            state_name = self.get_state(suffix)
            value = self.get_value(suffix)
            if value is None:
                value = self.data[i]

            # β redesign — ``highlight`` is a standalone state; fall back
            # to the current state when the cell is already a stronger
            # signal so the two don't visually compete.
            highlighted = suffix in self._highlighted
            if highlighted and state_name == "idle":
                effective_state = "highlight"
            else:
                effective_state = state_name

            css = state_class(effective_state)
            # Text fill still comes from svg_style_attrs — rect fill,
            # stroke, stroke-width, and rx are owned by CSS state classes.
            colors = svg_style_attrs(effective_state)

            x = int(i * (CELL_WIDTH + CELL_GAP))
            y = 0

            lines.append(f'  <g data-target="{target}" class="{css}">')
            rect_attrs = _inset_rect_attrs(x, y, CELL_WIDTH, CELL_HEIGHT)
            lines.append(
                f'    <rect x="{rect_attrs["x"]}" y="{rect_attrs["y"]}" '
                f'width="{rect_attrs["width"]}" '
                f'height="{rect_attrs["height"]}"/>'
            )
            text_x = int(x + CELL_WIDTH // 2)
            text_y = int(y + CELL_HEIGHT // 2)
            lines.append(
                "    "
                + _render_svg_text(
                    value,
                    text_x,
                    text_y,
                    fill=colors["text"],
                    fo_width=CELL_WIDTH,
                    fo_height=CELL_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )
            lines.append("  </g>")

            if idx_labels is not None:
                label_y = int(CELL_HEIGHT + INDEX_LABEL_OFFSET)
                lines.append(
                    "  "
                    + _render_svg_text(
                        idx_labels[i],
                        text_x,
                        label_y,
                        fill=THEME["fg_muted"],
                        css_class="scriba-index-label idx",
                        fo_width=CELL_WIDTH,
                        fo_height=20,
                        render_inline_tex=render_inline_tex,
                    )
                )

    def _emit_2d_cells(
        self,
        lines: list[str],
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> None:
        """Emit cells for 2D grid layout."""
        for r in range(self.rows):
            for c in range(self.cols):
                target = f"{self.shape_name}.cell[{r}][{c}]"
                suffix = f"cell[{r}][{c}]"

                state_name = self.get_state(suffix)
                value = self.get_value(suffix)
                if value is None:
                    flat_idx = r * self.cols + c
                    value = self.data[flat_idx]

                # β redesign — highlight is a state, not an overlay.
                highlighted = suffix in self._highlighted
                if highlighted and state_name == "idle":
                    effective_state = "highlight"
                else:
                    effective_state = state_name

                css = state_class(effective_state)
                colors = svg_style_attrs(effective_state)

                x = int(c * (CELL_WIDTH + CELL_GAP))
                y = int(r * (CELL_HEIGHT + CELL_GAP))

                lines.append(
                    f'  <g data-target="{target}" class="{css}">'
                )
                rect_attrs = _inset_rect_attrs(
                    x, y, CELL_WIDTH, CELL_HEIGHT
                )
                lines.append(
                    f'    <rect x="{rect_attrs["x"]}" y="{rect_attrs["y"]}" '
                    f'width="{rect_attrs["width"]}" '
                    f'height="{rect_attrs["height"]}"/>'
                )
                text_x = int(x + CELL_WIDTH // 2)
                text_y = int(y + CELL_HEIGHT // 2)
                lines.append(
                    "    "
                    + _render_svg_text(
                        value,
                        text_x,
                        text_y,
                        fill=colors["text"],
                        fo_width=CELL_WIDTH,
                        fo_height=CELL_HEIGHT,
                        render_inline_tex=render_inline_tex,
                    )
                )
                lines.append("  </g>")

    # -- internal: arrows --------------------------------------------------

    def _emit_arrow(
        self,
        lines: list[str],
        ann: dict[str, Any],
        annotations: list[dict[str, Any]] | None = None,
        render_inline_tex: "Callable[[str], str] | None" = None,
        placed_labels: "list[_LabelPlacement] | None" = None,
    ) -> None:
        """Emit an arrow annotation — Bezier arc or plain pointer."""
        arrow_from = ann.get("arrow_from", "")

        # Plain arrow=true: short straight pointer, no source arc.
        if not arrow_from and ann.get("arrow"):
            dst_center = self._cell_center(ann.get("target", ""))
            if dst_center is not None:
                emit_plain_arrow_svg(
                    lines,
                    ann,
                    dst_point=dst_center,
                    render_inline_tex=render_inline_tex,
                    placed_labels=placed_labels,
                )
            return

        if not arrow_from:
            return

        src_center = self._cell_center(arrow_from)
        dst_center = self._cell_center(ann.get("target", ""))

        if src_center is None or dst_center is None:
            return

        # Compute arrow_index: how many earlier arrows target the same cell
        target = ann.get("target", "")
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

        emit_arrow_svg(
            lines,
            ann,
            src_point=src_center,
            dst_point=dst_center,
            arrow_index=arrow_index,
            cell_height=CELL_HEIGHT,
            render_inline_tex=render_inline_tex,
            placed_labels=placed_labels,
        )

    def _arrow_height_above(self, annotations: list[dict[str, Any]]) -> int:
        """Compute vertical extent above y=0 that arrows need."""
        computed = arrow_height_above(
            annotations, self._cell_center, cell_height=CELL_HEIGHT
        )
        return max(computed, getattr(self, "_min_arrow_above", 0))

    def _cell_center(self, selector_str: str) -> tuple[int, int] | None:
        """Return the ``(cx, cy)`` pixel center of a cell selector."""
        m = _CELL_1D_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            i = int(m.group("idx"))
            x = int(i * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2)
            y = int(CELL_HEIGHT // 2)
            return (x, y)

        m = _CELL_2D_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            r, c = int(m.group("row")), int(m.group("col"))
            x = int(c * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2)
            y = int(r * (CELL_HEIGHT + CELL_GAP) + CELL_HEIGHT // 2)
            return (x, y)

        return None

    # -- internal: dimensions ----------------------------------------------

    def _grid_dimensions(self) -> tuple[int, int]:
        """Return ``(total_width, total_height)`` of the cell grid."""
        if self.cols == 0:
            return (0, 0)
        w = self.cols * CELL_WIDTH + (self.cols - 1) * CELL_GAP
        h = self.rows * CELL_HEIGHT + (self.rows - 1) * CELL_GAP
        return (w, h)


# ---------------------------------------------------------------------------
# Backward-compatible alias
# ---------------------------------------------------------------------------

DPTableInstance = DPTablePrimitive


# ---------------------------------------------------------------------------
# Index label parser (shared with Array)
# ---------------------------------------------------------------------------


def _parse_index_labels(fmt: str, size: int) -> list[str]:
    """Parse ``labels`` format string into a list of label strings."""
    m = re.match(r"^(\d+)\.\.(\d+)$", fmt)
    if m:
        return [str(i) for i in range(size)]

    m = re.match(r"^(.+?)\[(\d+)\]\.\.(.+?)\[(\d+)\]$", fmt)
    if m:
        prefix = m.group(1)
        return [f"{prefix}[{i}]" for i in range(size)]

    return [str(i) for i in range(size)]
