"""Grid primitive -- a 2D rows x cols matrix of uniform cells.

See ``docs/spec/primitives.md`` section 4 for the authoritative specification.
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
    _render_svg_text,
    register_primitive,
    state_class,
    svg_style_attrs,
)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _flatten_2d(raw: Any, rows: int, cols: int) -> list[Any]:
    """Flatten a 2D list into a 1D flat list, or validate a flat list.

    If *raw* is empty, returns a flat list of empty strings.
    """
    if not raw:
        return [""] * (rows * cols)

    # 2D list: list of lists
    if isinstance(raw, (list, tuple)) and raw and isinstance(raw[0], (list, tuple)):
        flat: list[Any] = []
        for row in raw:
            flat.extend(row)
        expected = rows * cols
        if len(flat) != expected:
            raise animation_error(
                E1103,
                detail=(
                    f"Grid 'data' flattened length ({len(flat)}) "
                    f"does not match rows*cols ({expected})"
                ),
            )
        return flat

    # Already flat
    flat_list = list(raw)
    expected = rows * cols
    if len(flat_list) != expected:
        raise animation_error(
            E1103,
            detail=(
                f"Grid 'data' length ({len(flat_list)}) "
                f"does not match rows*cols ({expected})"
            ),
        )
    return flat_list


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

_CELL_2D_RE = re.compile(
    r"^(?P<name>\w+)\.cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$"
)
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")

# Suffix-only regex (no shape name prefix)
_SUFFIX_CELL_2D_RE = re.compile(r"^cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$")


# ---------------------------------------------------------------------------
# GridPrimitive
# ---------------------------------------------------------------------------


@register_primitive("Grid")
class GridPrimitive(PrimitiveBase):
    """A 2D rows x cols matrix of uniform cells.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type: str = "grid"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "cell[{r}][{c}]": "cell by row,col",
        "all": "all cells",
    }

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)
        rows = self.params.get("rows")
        cols = self.params.get("cols")

        if rows is None or cols is None:
            raise animation_error(
                E1103,
                detail="Grid requires both 'rows' and 'cols' parameters",
            )

        rows = int(rows)
        cols = int(cols)
        if rows < 1:
            raise animation_error(
                E1103,
                detail=f"Grid rows must be >= 1, got {rows}",
            )
        if cols < 1:
            raise animation_error(
                E1103,
                detail=f"Grid cols must be >= 1, got {cols}",
            )
        if rows > 500:
            raise animation_error(
                E1103,
                detail=f"Grid rows {rows} exceeds maximum of 500",
            )
        if cols > 500:
            raise animation_error(
                E1103,
                detail=f"Grid cols {cols} exceeds maximum of 500",
            )

        raw_data: Any = self.params.get("data", [])
        data: list[Any] = _flatten_2d(raw_data, rows, cols)

        self.shape_name: str = name
        self.rows: int = rows
        self.cols: int = cols
        self.data: list[Any] = data
        self.label: str | None = self.params.get("label")

    # -- PrimitiveBase interface --------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector suffixes."""
        parts: list[str] = []
        for r in range(self.rows):
            for c in range(self.cols):
                parts.append(f"cell[{r}][{c}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        """Check whether *suffix* is a valid addressable part."""
        m = _SUFFIX_CELL_2D_RE.match(suffix)
        if m:
            r, c = int(m.group("row")), int(m.group("col"))
            return 0 <= r < self.rows and 0 <= c < self.cols

        return suffix == "all"

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the grid."""

        lines: list[str] = [
            f'<g data-primitive="grid" data-shape="{self.shape_name}">'
        ]

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

        # Caption label below the grid
        if self.label is not None:
            tw, th = self._grid_dimensions()
            center_x = int(tw // 2)
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

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> BoundingBox:
        """Return the bounding box of this grid."""
        tw, th = self._grid_dimensions()
        h = th
        if self.label:
            h += INDEX_LABEL_OFFSET
        return BoundingBox(x=0, y=0, width=tw, height=h)

    # -- internal -----------------------------------------------------------

    def _grid_dimensions(self) -> tuple[int, int]:
        """Return ``(total_width, total_height)`` of the cell grid."""
        if self.cols == 0 or self.rows == 0:
            return (0, 0)
        w = self.cols * CELL_WIDTH + (self.cols - 1) * CELL_GAP
        h = self.rows * CELL_HEIGHT + (self.rows - 1) * CELL_GAP
        return (w, h)


# ---------------------------------------------------------------------------
# Backward-compatible alias
# ---------------------------------------------------------------------------

GridInstance = GridPrimitive
