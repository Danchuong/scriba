"""Grid primitive -- a 2D rows x cols matrix of uniform cells.

See ``docs/06-primitives.md`` section 4 for the authoritative specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from scriba.animation.errors import E1103, animation_error
from scriba.animation.primitives.base import (
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    DEFAULT_STATE,
    INDEX_LABEL_OFFSET,
    _escape_xml,
    state_class,
    svg_style_attrs,
)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class GridPrimitive:
    """Factory that creates :class:`GridInstance` from ``\\shape`` params."""

    name: str = "Grid"

    def declare(
        self, shape_name: str, params: dict[str, Any]
    ) -> GridInstance:
        """Validate params and build a :class:`GridInstance`."""
        rows = params.get("rows")
        cols = params.get("cols")

        if rows is None or cols is None:
            raise animation_error(
                E1103,
                detail="Grid requires both 'rows' and 'cols' parameters",
            )

        rows = int(rows)
        cols = int(cols)
        if rows > 500:
            raise animation_error(
                E1103,
                detail=f"[E1103] Grid rows {rows} exceeds maximum of 500",
            )
        if cols > 500:
            raise animation_error(
                E1103,
                detail=f"[E1103] Grid cols {cols} exceeds maximum of 500",
            )

        raw_data: Any = params.get("data", [])
        data: list[Any] = _flatten_2d(raw_data, rows, cols)

        label: str | None = params.get("label")

        return GridInstance(
            shape_name=shape_name,
            rows=rows,
            cols=cols,
            data=data,
            label=label,
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


# ---------------------------------------------------------------------------
# Instance
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GridInstance:
    """A declared Grid instance with layout pre-computed."""

    shape_name: str
    rows: int
    cols: int
    data: list[Any] = field(default_factory=list)
    label: str | None = None
    primitive_type: str = "grid"

    # -- protocol -----------------------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector targets."""
        parts: list[str] = []
        for r in range(self.rows):
            for c in range(self.cols):
                parts.append(f"{self.shape_name}.cell[{r}][{c}]")
        parts.append(f"{self.shape_name}.all")
        return parts

    def validate_selector(self, selector_str: str) -> bool:
        """Check whether *selector_str* is valid for this instance."""
        m = _CELL_2D_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            r, c = int(m.group("row")), int(m.group("col"))
            return 0 <= r < self.rows and 0 <= c < self.cols

        m = _ALL_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            return True

        return False

    def emit_svg(self, state: dict[str, dict[str, Any]]) -> str:
        """Emit SVG ``<g>`` for the grid."""
        lines: list[str] = [
            f'<g data-primitive="grid" data-shape="{self.shape_name}">'
        ]

        for r in range(self.rows):
            for c in range(self.cols):
                target = f"{self.shape_name}.cell[{r}][{c}]"
                cell_state = state.get(target, {})
                state_name = cell_state.get("state", DEFAULT_STATE)
                css = state_class(state_name)
                colors = svg_style_attrs(state_name)
                flat_idx = r * self.cols + c
                value = cell_state.get("value", self.data[flat_idx])

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
                    f'    <text x="{text_x}" y="{text_y}" '
                    f'fill="{colors["text"]}">'
                    f"{_escape_xml(value)}</text>"
                )
                lines.append("  </g>")

        # Caption label below the grid
        if self.label is not None:
            tw, th = self._grid_dimensions()
            center_x = int(tw // 2)
            label_y = int(th + INDEX_LABEL_OFFSET)
            lines.append(
                f'  <text class="scriba-primitive-label" '
                f'x="{center_x}" y="{label_y}" fill="#6c757d">'
                f"{_escape_xml(self.label)}</text>"
            )

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> tuple[float, float, float, float]:
        """Return ``(x, y, width, height)``."""
        tw, th = self._grid_dimensions()
        h = th
        if self.label:
            h += INDEX_LABEL_OFFSET
        return (0, 0, float(tw), float(h))

    # -- internal -----------------------------------------------------------

    def _grid_dimensions(self) -> tuple[int, int]:
        """Return ``(total_width, total_height)`` of the cell grid."""
        if self.cols == 0 or self.rows == 0:
            return (0, 0)
        w = self.cols * CELL_WIDTH + (self.cols - 1) * CELL_GAP
        h = self.rows * CELL_HEIGHT + (self.rows - 1) * CELL_GAP
        return (w, h)
