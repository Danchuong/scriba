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
    _render_svg_text,
    register_primitive,
    state_class,
    svg_style_attrs,
)


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
                    E1103,
                    detail=f"DPTable n must be >= 1, got {n}",
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
                    E1103,
                    detail=f"DPTable rows must be >= 1, got {dim_rows}",
                )
            if dim_cols < 1:
                raise animation_error(
                    E1103,
                    detail=f"DPTable cols must be >= 1, got {dim_cols}",
                )
            n = dim_rows * dim_cols
        else:
            raise animation_error(
                E1103,
                detail="DPTable requires 'n' (1D) or 'rows'+'cols' (2D)",
            )

        max_cells = dim_rows * dim_cols
        if max_cells > 250_000:
            raise animation_error(
                "E1425",
                detail=(
                    f"Matrix/DPTable cell count {max_cells} "
                    f"exceeds maximum of 250000 "
                    f"(rows={dim_rows}, cols={dim_cols})"
                ),
            )

        data: list[Any] = list(self.params.get("data", []))
        if data and len(data) != n:
            raise animation_error(
                E1103,
                detail=(
                    f"DPTable 'data' length ({len(data)}) "
                    f"does not match expected size ({n})"
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

        lines: list[str] = [
            f'<g data-primitive="dptable" data-shape="{self.shape_name}">'
        ]

        if self.is_2d:
            self._emit_2d_cells(lines, render_inline_tex=render_inline_tex)
        else:
            self._emit_1d_cells(lines, render_inline_tex=render_inline_tex)

        # Arrow annotations
        if effective_anns:
            for ann in effective_anns:
                self._emit_arrow(lines, ann)

        # Caption label
        if self.label is not None:
            tw, th = self._grid_dimensions()
            center_x = int(tw // 2)
            base_y = th
            if not self.is_2d and self.labels:
                base_y += INDEX_LABEL_OFFSET
            label_y = int(base_y + INDEX_LABEL_OFFSET)
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

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> BoundingBox:
        """Return ``(x, y, width, height)``."""
        tw, th = self._grid_dimensions()
        h = th
        if not self.is_2d and self.labels:
            h += INDEX_LABEL_OFFSET
        if self.label:
            h += INDEX_LABEL_OFFSET
        return BoundingBox(x=0, y=0, width=float(tw), height=float(h))

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

            css = state_class(state_name)
            colors = svg_style_attrs(state_name)

            x = int(i * (CELL_WIDTH + CELL_GAP))
            y = 0
            stroke_w = "1.5" if state_name == "idle" else "2"

            lines.append(f'  <g data-target="{target}" class="{css}">')
            lines.append(
                f'    <rect x="{x}" y="{y}" '
                f'width="{CELL_WIDTH}" height="{CELL_HEIGHT}" '
                f'rx="4" fill="{colors["fill"]}" '
                f'stroke="{colors["stroke"]}" stroke-width="{stroke_w}"/>'
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

                css = state_class(state_name)
                colors = svg_style_attrs(state_name)

                x = int(c * (CELL_WIDTH + CELL_GAP))
                y = int(r * (CELL_HEIGHT + CELL_GAP))
                stroke_w = "1.5" if state_name == "idle" else "2"

                lines.append(
                    f'  <g data-target="{target}" class="{css}">'
                )
                lines.append(
                    f'    <rect x="{x}" y="{y}" '
                    f'width="{CELL_WIDTH}" height="{CELL_HEIGHT}" '
                    f'rx="4" fill="{colors["fill"]}" '
                    f'stroke="{colors["stroke"]}" stroke-width="{stroke_w}"/>'
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
    ) -> None:
        """Emit a cubic Bezier arrow annotation."""
        color = ann.get("color", "info")
        label_text = ann.get("label", "")
        target = ann.get("target", "")
        arrow_from = ann.get("arrow_from", "")

        src_center = self._cell_center(arrow_from)
        dst_center = self._cell_center(target)

        if src_center is None or dst_center is None:
            return

        x1, y1 = src_center
        x2, y2 = dst_center

        # Control points: curve upward
        mid_x = int((x1 + x2) // 2)
        mid_y = int(min(y1, y2) - 30)
        cx1 = int((x1 + mid_x) // 2)
        cy1 = mid_y
        cx2 = int((x2 + mid_x) // 2)
        cy2 = mid_y

        lines.append(
            f'  <g class="scriba-annotation scriba-annotation-{color}">'
        )
        lines.append(
            f'    <path d="M{x1},{y1} C{cx1},{cy1} {cx2},{cy2} {x2},{y2}" '
            f'stroke="currentColor" fill="none" '
            f'marker-end="url(#scriba-arrow-{color})"/>'
        )
        if label_text:
            lines.append(
                f'    <text x="{mid_x}" y="{mid_y}">'
                f"{_escape_xml(label_text)}</text>"
            )
        lines.append("  </g>")

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
