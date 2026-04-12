"""MetricPlot primitive — compile-time SVG line chart for scalar tracking.

Tracks one or more scalar values across animation frames. Each ``\\step``
feeds new data points; the emitter computes the full chart SVG for that
frame from all accumulated data.

See ``docs/primitives/metricplot.md`` for the authoritative specification.
Error codes: E1480--E1489.
"""

from __future__ import annotations

import html
import logging
import math
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _emit_warning, animation_error
from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    _render_svg_text,
    register_primitive,
)

__all__ = ["MetricPlot"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# β "Tonal Architecture" categorical series palette.
# Radix step-9 accents with staggered lightness so adjacent series differ
# in *both* hue and lightness (ColorBrewer schemeTableau10 discipline).
# Seven discrete hues + one neutral ink for 8-series plots; dash patterns
# below disambiguate when more series are stacked than hues.
# ---------------------------------------------------------------------------

_WONG_COLORS: list[str] = [
    "#0b68cb",  # Radix blue-11  — series 1 (primary)
    "#e5484d",  # Radix red-9    — series 2
    "#2a7e3b",  # Radix grass-11 — series 3
    "#f5a524",  # Radix amber-9  — series 4
    "#8e4ec6",  # Radix violet-9 — series 5
    "#0d74b5",  # Radix cyan-11  — series 6
    "#d6409f",  # Radix pink-9   — series 7
    "#11181c",  # slate-12       — series 8 (neutral ink)
]

_DASH_PATTERNS: list[str] = [
    "",          # solid
    "6 3",
    "2 2",
    "8 3 2 3",
    "4 2 4 2",
    "10 4",
    "2 4",
    "6 2 2 2",
]

_MAX_SERIES = 8
_MAX_POINTS = 1000

# ---------------------------------------------------------------------------
# Series descriptor
# ---------------------------------------------------------------------------


class _SeriesInfo:
    """Resolved series configuration."""

    __slots__ = ("name", "color", "axis", "scale", "dash", "index")

    def __init__(
        self,
        name: str,
        color: str,
        axis: str,
        scale: str,
        dash: str,
        index: int,
    ) -> None:
        self.name = name
        self.color = color
        self.axis = axis
        self.scale = scale
        self.dash = dash
        self.index = index


# ---------------------------------------------------------------------------
# MetricPlot primitive
# ---------------------------------------------------------------------------


@register_primitive("MetricPlot")
class MetricPlot(PrimitiveBase):
    """Compile-time SVG line chart primitive.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``plot``).
    params:
        Dictionary of parameters from the ``\\shape`` command.

    Limits
    ------
    * At most ``8`` series per plot (``E1481``).
    * At most ``1000`` data points per series (``E1483``).  Appending beyond
      this limit raises rather than silently truncating, so authors see the
      overflow instead of getting a plot that is missing data.  If you need
      more points, down-sample the source data or split into multiple plots.
    """

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "all": "the entire plot",
    }

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)
        self.primitive_type: str = "metricplot"

        # --- parse series ---
        raw_series = params.get("series", [])
        if not raw_series:
            raise animation_error("E1480", "MetricPlot requires at least one series")
        if len(raw_series) > _MAX_SERIES:
            raise animation_error(
                "E1481",
                f"MetricPlot supports at most {_MAX_SERIES} series, got {len(raw_series)}",
            )

        self._series: list[_SeriesInfo] = []
        seen_names: set[str] = set()
        for idx, raw in enumerate(raw_series):
            if isinstance(raw, str):
                s_name = raw
                s_color = "auto"
                s_axis = "left"
                s_scale = "linear"
            elif isinstance(raw, dict):
                s_name = str(raw["name"])
                s_color = str(raw.get("color", "auto"))
                s_axis = str(raw.get("axis", "left"))
                s_scale = str(raw.get("scale", "linear"))
            else:
                s_name = str(raw)
                s_color = "auto"
                s_axis = "left"
                s_scale = "linear"

            if s_name in seen_names:
                raise animation_error(
                    "E1485",
                    f"duplicate series name {s_name!r} in MetricPlot",
                )
            seen_names.add(s_name)

            color = _WONG_COLORS[idx] if s_color == "auto" else s_color
            dash = _DASH_PATTERNS[idx]
            self._series.append(
                _SeriesInfo(
                    name=s_name,
                    color=color,
                    axis=s_axis,
                    scale=s_scale,
                    dash=dash,
                    index=idx,
                )
            )

        self._series_names: set[str] = {s.name for s in self._series}

        # --- validate axis-scale consistency (E1487) ---
        self._validate_axis_scales()

        # --- optional params ---
        self.xlabel: str = str(params.get("xlabel", "step"))
        self.ylabel: str = str(params.get("ylabel", "value"))
        self.ylabel_right: str | None = params.get("ylabel_right")
        self.grid: bool = bool(params.get("grid", True))
        self.width: int = int(params.get("width", 320))
        self.height: int = int(params.get("height", 200))
        self.show_legend: bool = bool(params.get("show_legend", True))
        self.show_current_marker: bool = bool(params.get("show_current_marker", True))

        # --- axis ranges ---
        self.xrange: str | list[float] = params.get("xrange", "auto")
        if isinstance(self.xrange, list) and len(self.xrange) == 2:
            if self.xrange[0] == self.xrange[1]:
                logger.error("[E1486] degenerate xrange [%s, %s]; falling back to auto",
                             self.xrange[0], self.xrange[1])
                raise animation_error(
                    "E1486",
                    f"degenerate xrange [{self.xrange[0]}, {self.xrange[1]}]",
                )

        self.yrange: str | list[float] = params.get("yrange", "auto")
        self.yrange_right: str | list[float] = params.get("yrange_right", "auto")

        # --- two-axis mode ---
        self.two_axis: bool = any(s.axis == "right" for s in self._series)

        # --- padding ---
        self.pad_left: int = 48
        self.pad_right: int = 48 if self.two_axis else 16
        self.pad_top: int = 16
        self.pad_bottom: int = 40

        # --- data storage ---
        self._data: dict[str, list[float]] = {s.name: [] for s in self._series}
        # Track which global step index each data point corresponds to
        self._step_index: int = 0

    # -----------------------------------------------------------------
    # Validation helpers
    # -----------------------------------------------------------------

    def _validate_axis_scales(self) -> None:
        """Check E1487: same-axis series must share the same scale."""
        for axis in ("left", "right"):
            scales = {s.scale for s in self._series if s.axis == axis}
            if len(scales) > 1:
                raise animation_error(
                    "E1487",
                    f"series on axis {axis!r} have mixed scales: {scales}",
                )

    # -----------------------------------------------------------------
    # Data accumulation via apply_command
    # -----------------------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Process data feeding from ``\\apply{plot}{phi=3.2, cost=5.1}``.

        Raises
        ------
        AnimationError
            ``E1483`` if appending would push any series beyond the
            ``_MAX_POINTS`` hard limit.  Previously a soft-drop with a log
            message; converted to a hard limit so data loss is visible.
        """
        for series_name, value in params.items():
            if series_name in self._series_names:
                if len(self._data[series_name]) >= _MAX_POINTS:
                    raise animation_error(
                        "E1483",
                        f"MetricPlot series {series_name!r} exceeded "
                        f"maximum {_MAX_POINTS} points per series; "
                        f"down-sample the source data or split into "
                        f"multiple plots",
                    )
                self._data[series_name].append(float(value))
        self._step_index += 1

    # -----------------------------------------------------------------
    # Coordinate mapping
    # -----------------------------------------------------------------

    def _data_to_svg_x(self, x: float, xmin: float, xmax: float) -> float:
        if xmax == xmin:
            return float(self.pad_left)
        return self.pad_left + (x - xmin) / (xmax - xmin) * (
            self.width - self.pad_left - self.pad_right
        )

    def _data_to_svg_y(self, y: float, ymin: float, ymax: float) -> float:
        if ymax == ymin:
            return float(self.height - self.pad_bottom)
        return (self.height - self.pad_bottom) - (y - ymin) / (ymax - ymin) * (
            self.height - self.pad_top - self.pad_bottom
        )

    # -----------------------------------------------------------------
    # Axis range computation
    # -----------------------------------------------------------------

    def _compute_xrange(self) -> tuple[float, float]:
        if isinstance(self.xrange, list) and len(self.xrange) == 2:
            return (float(self.xrange[0]), float(self.xrange[1]))
        # auto: [0, N-1]
        max_len = max((len(v) for v in self._data.values()), default=0)
        return (0.0, max(float(max_len - 1), 0.0))

    def _compute_yrange(self, axis: str) -> tuple[float, float]:
        range_param = self.yrange if axis == "left" else self.yrange_right
        if isinstance(range_param, list) and len(range_param) == 2:
            return (float(range_param[0]), float(range_param[1]))

        # auto: data min/max with 10% padding
        values: list[float] = []
        axis_scale = self._axis_scale(axis)
        for s in self._series:
            if s.axis == axis and self._data[s.name]:
                for v in self._data[s.name]:
                    if axis_scale == "log":
                        values.append(math.log10(max(v, 1e-9)))
                    else:
                        values.append(v)

        if not values:
            return (0.0, 1.0)

        dmin = min(values)
        dmax = max(values)
        span = dmax - dmin
        if span == 0:
            return (dmin - 1.0, dmax + 1.0)
        return (dmin - 0.1 * span, dmax + 0.1 * span)

    def _axis_scale(self, axis: str) -> str:
        """Return the scale for a given axis (all series on the same axis share it)."""
        for s in self._series:
            if s.axis == axis:
                return s.scale
        return "linear"

    # -----------------------------------------------------------------
    # Tick computation
    # -----------------------------------------------------------------

    @staticmethod
    def _nice_ticks(vmin: float, vmax: float, max_ticks: int = 6) -> list[float]:
        """Generate a list of nice tick values between vmin and vmax."""
        if vmax <= vmin:
            return [vmin]
        raw_step = (vmax - vmin) / max(max_ticks - 1, 1)
        magnitude = 10 ** math.floor(math.log10(max(abs(raw_step), 1e-15)))
        residual = raw_step / magnitude
        if residual <= 1.5:
            nice_step = magnitude
        elif residual <= 3.0:
            nice_step = 2 * magnitude
        elif residual <= 7.0:
            nice_step = 5 * magnitude
        else:
            nice_step = 10 * magnitude

        start = math.floor(vmin / nice_step) * nice_step
        ticks: list[float] = []
        t = start
        while t <= vmax + nice_step * 0.01:
            if t >= vmin - nice_step * 0.01:
                ticks.append(round(t, 10))
            t += nice_step
        return ticks if ticks else [vmin]

    # -----------------------------------------------------------------
    # SVG emission
    # -----------------------------------------------------------------

    def emit_svg(self, *, render_inline_tex: Callable[[str], str] | None = None) -> str:
        """Return the SVG fragment for the current frame."""
        xmin, xmax = self._compute_xrange()
        ymin_left, ymax_left = self._compute_yrange("left")
        ymin_right, ymax_right = (
            self._compute_yrange("right") if self.two_axis else (0.0, 1.0)
        )

        series_names_str = ",".join(s.name for s in self._series)

        parts: list[str] = []
        parts.append(
            f'<g data-primitive="metricplot" data-shape="{html.escape(self.name)}"'
            f' data-scriba-series="{html.escape(series_names_str)}">'
        )

        # Layer 1: Grid
        if self.grid:
            parts.append(self._emit_grid(xmin, xmax, ymin_left, ymax_left))

        # Layer 2: Axes
        parts.append(
            self._emit_axes(
                xmin, xmax, ymin_left, ymax_left, ymin_right, ymax_right,
                render_inline_tex=render_inline_tex,
            )
        )

        # Layer 3: Series polylines
        parts.append(
            self._emit_series(xmin, xmax, ymin_left, ymax_left, ymin_right, ymax_right)
        )

        # Layer 4: Current-step marker
        if self.show_current_marker:
            parts.append(
                self._emit_marker(xmin, xmax, ymin_left, ymax_left, ymin_right, ymax_right)
            )

        # Layer 5: Legend
        if self.show_legend:
            parts.append(self._emit_legend(render_inline_tex=render_inline_tex))

        parts.append("</g>")
        return "\n".join(parts)

    # --- Layer 1: Grid ---

    def _emit_grid(
        self,
        xmin: float, xmax: float,
        ymin: float, ymax: float,
    ) -> str:
        parts: list[str] = ['<g class="scriba-metricplot-grid">']

        # Horizontal grid lines from y ticks
        yticks = self._nice_ticks(ymin, ymax)
        for yt in yticks:
            sy = round(self._data_to_svg_y(yt, ymin, ymax), 2)
            parts.append(
                f'<line class="scriba-metricplot-gridline-h"'
                f' x1="{self.pad_left}" y1="{sy}"'
                f' x2="{self.width - self.pad_right}" y2="{sy}"/>'
            )

        # Vertical grid lines from x ticks
        xticks = self._nice_ticks(xmin, xmax, max_ticks=8)
        for xt in xticks:
            sx = round(self._data_to_svg_x(xt, xmin, xmax), 2)
            parts.append(
                f'<line class="scriba-metricplot-gridline-v"'
                f' x1="{sx}" y1="{self.pad_top}"'
                f' x2="{sx}" y2="{self.height - self.pad_bottom}"/>'
            )

        parts.append("</g>")
        return "\n".join(parts)

    # --- Layer 2: Axes ---

    def _emit_axes(
        self,
        xmin: float, xmax: float,
        ymin_left: float, ymax_left: float,
        ymin_right: float, ymax_right: float,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> str:
        parts: list[str] = ['<g class="scriba-metricplot-axes">']
        W = self.width
        H = self.height
        pl, pr, pt, pb = self.pad_left, self.pad_right, self.pad_top, self.pad_bottom

        # x-axis line
        parts.append(
            f'<line x1="{pl}" y1="{H - pb}"'
            f' x2="{W - pr}" y2="{H - pb}"'
            f' stroke="var(--scriba-fg, #11181c)" stroke-width="1.5"/>'
        )
        # left y-axis line
        parts.append(
            f'<line x1="{pl}" y1="{pt}"'
            f' x2="{pl}" y2="{H - pb}"'
            f' stroke="var(--scriba-fg, #11181c)" stroke-width="1.5"/>'
        )
        # right y-axis line (two-axis mode)
        if self.two_axis:
            parts.append(
                f'<line x1="{W - pr}" y1="{pt}"'
                f' x2="{W - pr}" y2="{H - pb}"'
                f' class="scriba-metricplot-right-axis"'
                f' stroke="var(--scriba-fg, #11181c)" stroke-width="1.5"/>'
            )

        # x-axis ticks and labels
        parts.append('<g class="scriba-metricplot-xticks">')
        xticks = self._nice_ticks(xmin, xmax, max_ticks=8)
        for xt in xticks:
            sx = round(self._data_to_svg_x(xt, xmin, xmax), 2)
            parts.append(
                f'<line x1="{sx}" y1="{H - pb}"'
                f' x2="{sx}" y2="{H - pb + 4}"'
                f' stroke="var(--scriba-fg, #11181c)" stroke-width="1"/>'
            )
            label = self._format_tick(xt)
            parts.append(
                f'<text x="{sx}" y="{H - pb + 14}"'
                f' text-anchor="middle" font-size="10">{html.escape(label)}</text>'
            )
        parts.append("</g>")

        # left y-axis ticks and labels
        parts.append('<g class="scriba-metricplot-yticks">')
        yticks_left = self._nice_ticks(ymin_left, ymax_left)
        for yt in yticks_left:
            sy = round(self._data_to_svg_y(yt, ymin_left, ymax_left), 2)
            parts.append(
                f'<line x1="{pl - 4}" y1="{sy}"'
                f' x2="{pl}" y2="{sy}"'
                f' stroke="var(--scriba-fg, #11181c)" stroke-width="1"/>'
            )
            label = self._format_tick(yt)
            parts.append(
                f'<text x="{pl - 8}" y="{round(sy + 4, 2)}"'
                f' text-anchor="end" font-size="10">{html.escape(label)}</text>'
            )
        parts.append("</g>")

        # right y-axis ticks and labels (two-axis mode)
        if self.two_axis:
            parts.append('<g class="scriba-metricplot-yticks-right">')
            yticks_right = self._nice_ticks(ymin_right, ymax_right)
            for yt in yticks_right:
                sy = round(self._data_to_svg_y(yt, ymin_right, ymax_right), 2)
                parts.append(
                    f'<line x1="{W - pr}" y1="{sy}"'
                    f' x2="{W - pr + 4}" y2="{sy}"'
                    f' stroke="var(--scriba-fg, #11181c)" stroke-width="1"/>'
                )
                label = self._format_tick(yt)
                parts.append(
                    f'<text x="{W - pr + 8}" y="{round(sy + 4, 2)}"'
                    f' text-anchor="start" font-size="10">{html.escape(label)}</text>'
                )
            parts.append("</g>")

        # Axis labels
        cx = round((pl + W - pr) / 2, 2)
        parts.append(
            _render_svg_text(
                self.xlabel, cx, H - 6,
                font_size="11",
                text_anchor="middle",
                render_inline_tex=render_inline_tex,
            )
        )
        cy = round((pt + H - pb) / 2, 2)
        ylabel_svg = _render_svg_text(
            self.ylabel, 12, cy,
            font_size="11",
            text_anchor="middle",
            render_inline_tex=render_inline_tex,
        )
        parts.append(
            f'<g transform="rotate(-90, 12, {cy})">{ylabel_svg}</g>'
        )
        if self.two_axis and self.ylabel_right:
            ylabel_right_svg = _render_svg_text(
                self.ylabel_right, W - 10, cy,
                font_size="11",
                text_anchor="middle",
                css_class="scriba-metricplot-right-axis-label",
                render_inline_tex=render_inline_tex,
            )
            parts.append(
                f'<g transform="rotate(90, {W - 10}, {cy})">{ylabel_right_svg}</g>'
            )

        parts.append("</g>")
        return "\n".join(parts)

    # --- Layer 3: Series polylines ---

    def _emit_series(
        self,
        xmin: float, xmax: float,
        ymin_left: float, ymax_left: float,
        ymin_right: float, ymax_right: float,
    ) -> str:
        parts: list[str] = ['<g class="scriba-metricplot-series">']

        for s in self._series:
            data = self._data[s.name]
            if s.axis == "left":
                ymin, ymax = ymin_left, ymax_left
            else:
                ymin, ymax = ymin_right, ymax_right

            parts.append(
                f'<g class="scriba-metricplot-series-{s.index}"'
                f' data-scriba-series-name="{html.escape(s.name)}">'
            )

            if data:
                # Build contiguous segments for polylines
                # For MetricPlot, data is always contiguous per series
                # but we support gaps via the step-tracking mechanism
                segments = self._build_segments(s, data, xmin, xmax, ymin, ymax)
                dash_attr = f' stroke-dasharray="{s.dash}"' if s.dash else ""
                for seg_points in segments:
                    points_str = " ".join(
                        f"{round(px, 2)},{round(py, 2)}" for px, py in seg_points
                    )
                    parts.append(
                        f'<polyline class="scriba-metricplot-line"'
                        f' points="{points_str}"'
                        f' fill="none"'
                        f' stroke="{s.color}"'
                        f' stroke-width="1.5"'
                        f'{dash_attr}'
                        f' stroke-linejoin="round"'
                        f' stroke-linecap="round"/>'
                    )

            parts.append("</g>")

        parts.append("</g>")
        return "\n".join(parts)

    def _build_segments(
        self,
        series: _SeriesInfo,
        data: list[float],
        xmin: float, xmax: float,
        ymin: float, ymax: float,
    ) -> list[list[tuple[float, float]]]:
        """Build polyline segments from data, handling log scale."""
        is_log = series.scale == "log"
        points: list[tuple[float, float]] = []

        for i, val in enumerate(data):
            sx = self._data_to_svg_x(float(i), xmin, xmax)
            if is_log:
                if val <= 0:
                    logger.warning(
                        "[E1484] log scale: non-positive value %s in series %r clamped to 1e-9",
                        val, series.name,
                    )
                    _emit_warning(
                        self._ctx,
                        "E1484",
                        f"log scale: non-positive value {val} in series "
                        f"{series.name!r} clamped to 1e-9",
                        primitive=self.name,
                        severity="dangerous",
                    )
                    val = 1e-9
                sy = self._data_to_svg_y(math.log10(val), ymin, ymax)
            else:
                sy = self._data_to_svg_y(val, ymin, ymax)
            points.append((sx, sy))

        return [points] if points else []

    # --- Layer 4: Current-step marker ---

    def _emit_marker(
        self,
        xmin: float, xmax: float,
        ymin_left: float, ymax_left: float,
        ymin_right: float, ymax_right: float,
    ) -> str:
        # Find the max data length to determine current x position
        max_len = max((len(v) for v in self._data.values()), default=0)
        if max_len == 0:
            return ""

        current_x_idx = max_len - 1
        sx = round(self._data_to_svg_x(float(current_x_idx), xmin, xmax), 2)

        parts: list[str] = ['<g class="scriba-metricplot-step-marker">']

        # Vertical dashed line
        parts.append(
            f'<line class="scriba-metricplot-marker"'
            f' x1="{sx}" y1="{self.pad_top}"'
            f' x2="{sx}" y2="{self.height - self.pad_bottom}"'
            f' stroke="var(--scriba-fg, #11181c)" stroke-width="1"'
            f' stroke-dasharray="4 3" opacity="0.6"/>'
        )

        # Circles on each series at the current x
        for s in self._series:
            data = self._data[s.name]
            if len(data) > current_x_idx:
                val = data[current_x_idx]
                if s.axis == "left":
                    ymin, ymax = ymin_left, ymax_left
                else:
                    ymin, ymax = ymin_right, ymax_right

                if s.scale == "log":
                    if val <= 0:
                        val = 1e-9
                    sy = round(self._data_to_svg_y(math.log10(val), ymin, ymax), 2)
                else:
                    sy = round(self._data_to_svg_y(val, ymin, ymax), 2)

                parts.append(
                    f'<circle class="scriba-metricplot-step-dot"'
                    f' cx="{sx}" cy="{sy}" r="4"'
                    f' fill="{s.color}"/>'
                )

        parts.append("</g>")
        return "\n".join(parts)

    # --- Layer 5: Legend ---

    def _emit_legend(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> str:
        parts: list[str] = ['<g class="scriba-metricplot-legend">']

        legend_x = self.width - self.pad_right - 80
        legend_y = self.pad_top + 4

        for i, s in enumerate(self._series):
            y = legend_y + i * 16
            dash_attr = f' stroke-dasharray="{s.dash}"' if s.dash else ""
            parts.append(
                f'<line x1="{legend_x}" y1="{y}"'
                f' x2="{legend_x + 20}" y2="{y}"'
                f' stroke="{s.color}" stroke-width="2"{dash_attr}/>'
            )
            parts.append(
                _render_svg_text(
                    s.name, legend_x + 26, round(y + 4, 2),
                    css_class="scriba-metricplot-legend-label",
                    font_size="11",
                    render_inline_tex=render_inline_tex,
                )
            )

        parts.append("</g>")
        return "\n".join(parts)

    # --- Helpers ---

    @staticmethod
    def _format_tick(value: float) -> str:
        """Format a tick value for display."""
        if value == int(value):
            return str(int(value))
        return f"{value:.1f}"

    # -----------------------------------------------------------------
    # PrimitiveBase interface
    # -----------------------------------------------------------------

    def addressable_parts(self) -> list[str]:
        return [self.name]

    def validate_selector(self, suffix: str) -> bool:
        return suffix == self.name or suffix == "all"

    def bounding_box(self) -> BoundingBox:
        return BoundingBox(x=0, y=0, width=self.width, height=self.height)
