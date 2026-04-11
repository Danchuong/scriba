"""Matrix / Heatmap primitive — dense 2D grid with colorscale mapping.

Supports viridis colorscale with linear interpolation, cell-level
selectors, and optional value display.

See ``docs/primitives/matrix.md`` for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from scriba.animation.errors import E1103, animation_error
from scriba.animation.primitives.base import (
    DEFAULT_STATE,
    THEME,
    PrimitiveBase,
    _render_svg_text,
    estimate_text_width,
    register_primitive,
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
# Selector matching
# ---------------------------------------------------------------------------

_CELL_2D_RE = re.compile(
    r"^(?P<name>\w+)\.cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$"
)
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")

# Suffix-only regex (no shape name prefix)
_SUFFIX_CELL_2D_RE = re.compile(r"^cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$")

# ---------------------------------------------------------------------------
# MatrixPrimitive
# ---------------------------------------------------------------------------


@register_primitive("Matrix", "Heatmap")
class MatrixPrimitive(PrimitiveBase):
    """A dense 2D grid with colorscale mapping.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type: str = "matrix"

    SELECTOR_PATTERNS: dict[str, str] = {
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
                detail="Matrix requires 'rows' and 'cols' parameters",
            )
        rows = int(rows)
        cols = int(cols)
        if rows < 1:
            raise animation_error(
                E1103,
                detail=f"Matrix rows must be >= 1, got {rows}",
            )
        if cols < 1:
            raise animation_error(
                E1103,
                detail=f"Matrix cols must be >= 1, got {cols}",
            )
        if rows * cols > 10_000:
            raise animation_error(
                E1103,
                detail=(
                    f"Matrix dimensions {rows}x{cols} "
                    f"({rows * cols} cells) exceeds maximum of 10,000"
                ),
            )

        raw_data = self.params.get("data", [])
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

        colorscale = str(self.params.get("colorscale", "viridis"))
        show_values = bool(self.params.get("show_values", False))
        cell_size = int(self.params.get("cell_size", _DEFAULT_CELL_SIZE))
        vmin = self.params.get("vmin")
        vmax = self.params.get("vmax")
        row_labels = self.params.get("row_labels")
        col_labels = self.params.get("col_labels")
        label = self.params.get("label")

        # Dynamic label offset based on actual label content
        row_label_offset = 0
        if row_labels:
            max_label_w = max(estimate_text_width(str(l), 10) for l in row_labels)
            row_label_offset = max(_LABEL_OFFSET, max_label_w + 4)

        col_label_offset = 0
        if col_labels:
            max_col_h = max(estimate_text_width(str(c), 10) for c in col_labels)
            col_label_offset = max(_LABEL_OFFSET, max_col_h + 4)

        self.shape_name: str = name
        self.rows: int = rows
        self.cols: int = cols
        self.data: list[list[float]] = data_2d
        self.colorscale: str = colorscale
        self.show_values: bool = show_values
        self.cell_size: int = cell_size
        self.vmin: float | None = float(vmin) if vmin is not None else None
        self.vmax: float | None = float(vmax) if vmax is not None else None
        self.row_labels: list[str] | None = row_labels
        self.col_labels: list[str] | None = col_labels
        self.label: str | None = label
        self.row_label_offset: int = row_label_offset
        self.col_label_offset: int = col_label_offset

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
            row = int(m.group("row"))
            col = int(m.group("col"))
            return 0 <= row < self.rows and 0 <= col < self.cols

        return suffix == "all"

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the matrix/heatmap."""

        stops = COLORSCALES.get(self.colorscale, VIRIDIS)
        effective_vmin, effective_vmax = self._compute_range()

        lines: list[str] = [
            f'<g data-primitive="matrix" data-shape="{self.shape_name}">'
        ]

        # Compute offsets for row/col labels (use dynamic values)
        x_offset = self.row_label_offset if self.row_labels else 0
        y_offset = self.col_label_offset if self.col_labels else 0

        # Column labels
        if self.col_labels:
            for c, cl in enumerate(self.col_labels[:self.cols]):
                cx = x_offset + c * (self.cell_size + _CELL_GAP) + self.cell_size // 2
                lines.append(
                    "  "
                    + _render_svg_text(
                        str(cl),
                        cx,
                        y_offset - 3,
                        fill=THEME["fg_muted"],
                        text_anchor="middle",
                        font_size="10",
                        fo_width=self.cell_size,
                        fo_height=self.col_label_offset,
                        render_inline_tex=render_inline_tex,
                    )
                )

        # Row labels
        if self.row_labels:
            for r, rl in enumerate(self.row_labels[:self.rows]):
                ry = y_offset + r * (self.cell_size + _CELL_GAP) + self.cell_size // 2
                lines.append(
                    "  "
                    + _render_svg_text(
                        str(rl),
                        x_offset - 3,
                        ry,
                        fill=THEME["fg_muted"],
                        text_anchor="end",
                        dominant_baseline="central",
                        font_size="10",
                        fo_width=self.row_label_offset,
                        fo_height=self.cell_size,
                        render_inline_tex=render_inline_tex,
                    )
                )

        for r in range(self.rows):
            for c in range(self.cols):
                target = f"{self.shape_name}.cell[{r}][{c}]"
                suffix = f"cell[{r}][{c}]"

                state_name = self.get_state(suffix)
                highlighted = suffix in self._highlighted

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
                        "    "
                        + _render_svg_text(
                            self._format_value(val),
                            tx,
                            ty,
                            fill=text_fill,
                            text_anchor="middle",
                            dominant_baseline="central",
                            font_size=str(font_size),
                            fo_width=self.cell_size,
                            fo_height=self.cell_size,
                            render_inline_tex=render_inline_tex,
                        )
                    )

                # Highlight overlay
                if highlighted:
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
                "  "
                + _render_svg_text(
                    self.label,
                    center_x,
                    label_y,
                    fill=THEME["fg_muted"],
                    css_class="scriba-primitive-label",
                    text_anchor="middle",
                    fo_width=total_w,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
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
        label_offset = self.row_label_offset if self.row_labels else 0
        if self.cols == 0:
            return label_offset
        return label_offset + self.cols * self.cell_size + (self.cols - 1) * _CELL_GAP

    def _total_height(self) -> int:
        label_offset = self.col_label_offset if self.col_labels else 0
        if self.rows == 0:
            return label_offset
        return label_offset + self.rows * self.cell_size + (self.rows - 1) * _CELL_GAP

    @staticmethod
    def _format_value(v: float) -> str:
        """Format a float for display: strip trailing zeros."""
        if v == int(v):
            return str(int(v))
        return f"{v:.2f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# Backward-compatible aliases
# ---------------------------------------------------------------------------

MatrixInstance = MatrixPrimitive
HeatmapPrimitive = MatrixPrimitive
