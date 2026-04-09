"""Matrix / Heatmap primitive — dense 2D grid with colorscale mapping.

Supports viridis colorscale with linear interpolation, cell-level
selectors, and optional value display.

See ``docs/primitives/matrix.md`` for the authoritative specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from scriba.animation.errors import E1103, animation_error
from scriba.animation.primitives.base import (
    DEFAULT_STATE,
    _escape_xml,
    state_class,
    svg_style_attrs,
)

# ---------------------------------------------------------------------------
# Colorscale definitions
# ---------------------------------------------------------------------------

# Viridis 5-stop linear interpolation
VIRIDIS: list[tuple[float, tuple[int, int, int]]] = [
    (0.0, (68, 1, 84)),       # dark purple
    (0.25, (59, 82, 139)),     # blue
    (0.5, (33, 145, 140)),     # teal
    (0.75, (94, 201, 98)),     # green
    (1.0, (253, 231, 37)),     # yellow
]

COLORSCALES: dict[str, list[tuple[float, tuple[int, int, int]]]] = {
    "viridis": VIRIDIS,
}


def interpolate_color(
    t: float,
    stops: list[tuple[float, tuple[int, int, int]]],
) -> str:
    """Interpolate between colorscale stops.

    *t* is clamped to [0, 1].  Returns an ``rgb(r,g,b)`` string.
    """
    t = max(0.0, min(1.0, t))

    # Find the two surrounding stops
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            if t1 == t0:
                frac = 0.0
            else:
                frac = (t - t0) / (t1 - t0)
            r = int(c0[0] + frac * (c1[0] - c0[0]))
            g = int(c0[1] + frac * (c1[1] - c0[1]))
            b = int(c0[2] + frac * (c1[2] - c0[2]))
            return f"rgb({r},{g},{b})"

    # Fallback: last stop
    c = stops[-1][1]
    return f"rgb({c[0]},{c[1]},{c[2]})"


def _text_color_for_background(
    t: float,
    stops: list[tuple[float, tuple[int, int, int]]],
) -> str:
    """Return white or black text depending on background luminance."""
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            if t1 == t0:
                frac = 0.0
            else:
                frac = (t - t0) / (t1 - t0)
            r = c0[0] + frac * (c1[0] - c0[0])
            g = c0[1] + frac * (c1[1] - c0[1])
            b = c0[2] + frac * (c1[2] - c0[2])
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            return "#212529" if lum > 140 else "#ffffff"
    return "#ffffff"


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_DEFAULT_CELL_SIZE = 24
_CELL_GAP = 1
_LABEL_OFFSET = 14  # space for row/col labels

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class MatrixPrimitive:
    """Factory that creates :class:`MatrixInstance` from ``\\shape`` params."""

    name: str = "Matrix"

    def declare(
        self, shape_name: str, params: dict[str, Any],
    ) -> MatrixInstance:
        """Validate params and build a :class:`MatrixInstance`."""
        rows = params.get("rows")
        cols = params.get("cols")
        if rows is None or cols is None:
            raise animation_error(
                E1103,
                detail="Matrix requires 'rows' and 'cols' parameters",
            )
        rows = int(rows)
        cols = int(cols)

        raw_data = params.get("data", [])
        if not raw_data:
            data_2d: list[list[float]] = [
                [0.0] * cols for _ in range(rows)
            ]
        elif isinstance(raw_data, list) and raw_data and isinstance(raw_data[0], list):
            # Already 2D
            data_2d = [[float(v) for v in row] for row in raw_data]
        else:
            # Flat list -> 2D
            flat = [float(v) for v in raw_data]
            if len(flat) != rows * cols:
                raise animation_error(
                    E1103,
                    detail=(
                        f"Matrix data length ({len(flat)}) does not match "
                        f"rows*cols ({rows * cols})"
                    ),
                )
            data_2d = [
                flat[r * cols : (r + 1) * cols] for r in range(rows)
            ]

        colorscale = str(params.get("colorscale", "viridis"))
        show_values = bool(params.get("show_values", False))
        cell_size = int(params.get("cell_size", _DEFAULT_CELL_SIZE))
        vmin = params.get("vmin")
        vmax = params.get("vmax")
        row_labels = params.get("row_labels")
        col_labels = params.get("col_labels")
        label = params.get("label")

        return MatrixInstance(
            shape_name=shape_name,
            rows=rows,
            cols=cols,
            data=data_2d,
            colorscale=colorscale,
            show_values=show_values,
            cell_size=cell_size,
            vmin=float(vmin) if vmin is not None else None,
            vmax=float(vmax) if vmax is not None else None,
            row_labels=row_labels,
            col_labels=col_labels,
            label=label,
        )


# Heatmap is an alias for Matrix
HeatmapPrimitive = MatrixPrimitive
HeatmapPrimitive.name = "Heatmap"

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
class MatrixInstance:
    """A declared Matrix instance with layout pre-computed."""

    shape_name: str
    rows: int
    cols: int
    data: list[list[float]] = field(default_factory=list)
    colorscale: str = "viridis"
    show_values: bool = False
    cell_size: int = _DEFAULT_CELL_SIZE
    vmin: float | None = None
    vmax: float | None = None
    row_labels: list[str] | None = None
    col_labels: list[str] | None = None
    label: str | None = None
    primitive_type: str = "matrix"

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
            row = int(m.group("row"))
            col = int(m.group("col"))
            return 0 <= row < self.rows and 0 <= col < self.cols

        m = _ALL_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            return True

        return False

    def emit_svg(self, state: dict[str, dict[str, Any]]) -> str:
        """Emit SVG ``<g>`` for the matrix/heatmap."""
        stops = COLORSCALES.get(self.colorscale, VIRIDIS)
        effective_vmin, effective_vmax = self._compute_range()

        lines: list[str] = [
            f'<g data-primitive="matrix" data-shape="{self.shape_name}">'
        ]

        # Compute offsets for row/col labels
        x_offset = _LABEL_OFFSET if self.row_labels else 0
        y_offset = _LABEL_OFFSET if self.col_labels else 0

        # Column labels
        if self.col_labels:
            for c, cl in enumerate(self.col_labels[:self.cols]):
                cx = x_offset + c * (self.cell_size + _CELL_GAP) + self.cell_size // 2
                lines.append(
                    f'  <text x="{cx}" y="{y_offset - 3}" '
                    f'text-anchor="middle" fill="#6c757d" '
                    f'font-size="10">{_escape_xml(str(cl))}</text>'
                )

        # Row labels
        if self.row_labels:
            for r, rl in enumerate(self.row_labels[:self.rows]):
                ry = y_offset + r * (self.cell_size + _CELL_GAP) + self.cell_size // 2
                lines.append(
                    f'  <text x="{x_offset - 3}" y="{ry}" '
                    f'text-anchor="end" dominant-baseline="central" '
                    f'fill="#6c757d" font-size="10">{_escape_xml(str(rl))}</text>'
                )

        for r in range(self.rows):
            for c in range(self.cols):
                target = f"{self.shape_name}.cell[{r}][{c}]"
                cell_state = state.get(target, {})
                state_name = cell_state.get("state", DEFAULT_STATE)
                css = state_class(state_name)

                val = self.data[r][c]
                # Normalize value to [0, 1] for colorscale
                if effective_vmax == effective_vmin:
                    t = 0.5
                else:
                    t = (val - effective_vmin) / (effective_vmax - effective_vmin)

                fill = interpolate_color(t, stops)
                text_fill = _text_color_for_background(t, stops)

                # State overrides stroke, not fill (preserve colorscale)
                if state_name != DEFAULT_STATE:
                    colors = svg_style_attrs(state_name)
                    stroke = colors["stroke"]
                    stroke_w = "2.5"
                else:
                    stroke = "none"
                    stroke_w = "0"

                x = x_offset + c * (self.cell_size + _CELL_GAP)
                y = y_offset + r * (self.cell_size + _CELL_GAP)

                lines.append(
                    f'  <g data-target="{target}" class="{css}">'
                )
                lines.append(
                    f'    <rect x="{x}" y="{y}" '
                    f'width="{self.cell_size}" height="{self.cell_size}" '
                    f'fill="{fill}" '
                    f'stroke="{stroke}" stroke-width="{stroke_w}"/>'
                )

                if self.show_values:
                    tx = x + self.cell_size // 2
                    ty = y + self.cell_size // 2
                    font_size = max(8, self.cell_size // 3)
                    lines.append(
                        f'    <text x="{tx}" y="{ty}" '
                        f'text-anchor="middle" dominant-baseline="central" '
                        f'fill="{text_fill}" font-size="{font_size}">'
                        f'{_escape_xml(self._format_value(val))}</text>'
                    )

                # Highlight overlay
                if cell_state.get("highlighted"):
                    lines.append(
                        f'    <rect x="{x}" y="{y}" '
                        f'width="{self.cell_size}" height="{self.cell_size}" '
                        f'fill="none" stroke="#F0E442" stroke-width="3" '
                        f'stroke-dasharray="6 3"/>'
                    )

                lines.append("  </g>")

        # Caption label below the matrix
        if self.label is not None:
            total_w = self._total_width()
            center_x = total_w // 2
            label_y = self._total_height() + 14
            lines.append(
                f'  <text class="scriba-primitive-label" '
                f'x="{center_x}" y="{label_y}" '
                f'text-anchor="middle" fill="#6c757d">'
                f'{_escape_xml(self.label)}</text>'
            )

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> tuple[float, float, float, float]:
        """Return ``(x, y, width, height)``."""
        w = self._total_width()
        h = self._total_height()
        if self.label:
            h += 20
        return (0, 0, float(w), float(h))

    # -- internal -----------------------------------------------------------

    def _compute_range(self) -> tuple[float, float]:
        """Compute effective vmin/vmax from data or explicit params."""
        if self.vmin is not None and self.vmax is not None:
            return (self.vmin, self.vmax)

        all_vals = [v for row in self.data for v in row]
        if not all_vals:
            return (0.0, 1.0)

        data_min = min(all_vals)
        data_max = max(all_vals)

        return (
            self.vmin if self.vmin is not None else data_min,
            self.vmax if self.vmax is not None else data_max,
        )

    def _total_width(self) -> int:
        label_offset = _LABEL_OFFSET if self.row_labels else 0
        if self.cols == 0:
            return label_offset
        return label_offset + self.cols * self.cell_size + (self.cols - 1) * _CELL_GAP

    def _total_height(self) -> int:
        label_offset = _LABEL_OFFSET if self.col_labels else 0
        if self.rows == 0:
            return label_offset
        return label_offset + self.rows * self.cell_size + (self.rows - 1) * _CELL_GAP

    @staticmethod
    def _format_value(v: float) -> str:
        """Format a float for display: strip trailing zeros."""
        if v == int(v):
            return str(int(v))
        return f"{v:.2f}".rstrip("0").rstrip(".")
