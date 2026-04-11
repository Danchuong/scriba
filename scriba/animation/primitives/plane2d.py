"""Plane2D primitive — 2D coordinate plane with lines, points, segments,
polygons, and shaded regions.

Emits pure ``<svg>`` with no runtime JavaScript.  All coordinates are
authored in math convention (origin bottom-left, Y up) and transformed to
SVG native coordinates (origin top-left, Y down) via an affine transform.

See ``docs/primitives/plane2d.md`` for the authoritative specification.
Error codes: E1460–E1469.
"""

from __future__ import annotations

import logging
import math
import re
from html import escape as html_escape
from typing import Any, Callable, ClassVar, Sequence

from scriba.animation.errors import animation_error
from scriba.animation.primitives.base import BoundingBox, PrimitiveBase, THEME, _render_svg_text, register_primitive, svg_style_attrs
from scriba.animation.primitives.plane2d_compute import clip_line_to_viewport

__all__ = ["Plane2D"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PAD = 32
_POINT_RADIUS = 4  # px in math-space (inside transformed group)
_ELEMENT_CAP = 500
_LABEL_OFFSET = 6  # px offset for labels in SVG space
_TICK_FONT_SIZE = 10
_MIN_TICK_SPACING_PX = 12
_ARROWHEAD_LEN = 6
_ARROWHEAD_HALF_W = 3

# Selector regexes
_POINT_RE = re.compile(r"^point\[(?P<idx>\d+)\]$")
_LINE_RE = re.compile(r"^line\[(?P<idx>\d+)\]$")
_SEGMENT_RE = re.compile(r"^segment\[(?P<idx>\d+)\]$")
_POLYGON_RE = re.compile(r"^polygon\[(?P<idx>\d+)\]$")
_REGION_RE = re.compile(r"^region\[(?P<idx>\d+)\]$")

# ---------------------------------------------------------------------------
# Internal data holders (plain dicts for immutability-friendliness)
# ---------------------------------------------------------------------------

# Each element is stored as a dict.
# Points:   {"x": float, "y": float, "label": str|None, "radius": int}
# Lines:    {"label": str|None, "slope": float, "intercept": float}
# Segments: {"x1": float, "y1": float, "x2": float, "y2": float, "label": str|None}
# Polygons: {"points": list[(float,float)]}
# Regions:  {"polygon": list[(float,float)], "fill": str}


# ---------------------------------------------------------------------------
# Plane2D primitive
# ---------------------------------------------------------------------------


@register_primitive("Plane2D")
class Plane2D(PrimitiveBase):
    """2D coordinate plane primitive.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``p``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
    """

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "point[{i}]": "point by index",
        "line[{i}]": "line by index",
        "segment[{i}]": "segment by index",
        "polygon[{i}]": "polygon by index",
        "region[{i}]": "shaded region by index",
        "all": "all elements",
    }

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        # --- range params ---
        self.xrange: tuple[float, float] = tuple(params.get("xrange", [-5.0, 5.0]))  # type: ignore[assignment]
        self.yrange: tuple[float, float] = tuple(params.get("yrange", [-5.0, 5.0]))  # type: ignore[assignment]

        if self.xrange[1] - self.xrange[0] == 0:
            raise animation_error("E1460", "xrange has equal endpoints (degenerate viewport)")
        if self.yrange[1] - self.yrange[0] == 0:
            raise animation_error("E1460", "yrange has equal endpoints (degenerate viewport)")

        # --- display params ---
        self.grid: bool | str = params.get("grid", True)
        self.axes: bool = bool(params.get("axes", True))
        aspect = params.get("aspect", "equal")
        if aspect not in ("equal", "auto"):
            raise animation_error("E1465", f"aspect must be 'equal' or 'auto', got {aspect!r}")
        self.aspect: str = aspect

        self.width: int = int(params.get("width", 320))

        if self.aspect == "equal":
            computed_h = self.width * (self.yrange[1] - self.yrange[0]) / (self.xrange[1] - self.xrange[0])
            explicit_h = params.get("height")
            if explicit_h is not None:
                self.height = min(int(explicit_h), int(computed_h))
            else:
                self.height = int(computed_h)
        else:
            self.height = int(params.get("height", 320))

        # --- compute transform ---
        self._compute_transform()

        # --- element lists ---
        self.points: list[dict[str, Any]] = []
        self.lines: list[dict[str, Any]] = []
        self.segments: list[dict[str, Any]] = []
        self.polygons: list[dict[str, Any]] = []
        self.regions: list[dict[str, Any]] = []

        # Populate from initial params
        for pt in params.get("points", []):
            self._add_point_internal(pt)
        for ln in params.get("lines", []):
            self._add_line_internal(ln)
        for seg in params.get("segments", []):
            self._add_segment_internal(seg)
        for poly in params.get("polygons", []):
            self._add_polygon_internal(poly)
        for reg in params.get("regions", []):
            self._add_region_internal(reg)

        self.primitive_type: str = "plane2d"

    # ----- transform -------------------------------------------------------

    def _compute_transform(self) -> None:
        """Pre-compute the affine math->SVG transform parameters."""
        xspan = self.xrange[1] - self.xrange[0]
        yspan = self.yrange[1] - self.yrange[0]

        self._sx = (self.width - 2 * _PAD) / xspan
        self._sy = -(self.height - 2 * _PAD) / yspan  # negative = Y-flip
        self._tx = _PAD + (-self.xrange[0]) * self._sx
        self._ty = (self.height - _PAD) + self.yrange[0] * (self.height - 2 * _PAD) / yspan

    def math_to_svg(self, x: float, y: float) -> tuple[float, float]:
        """Convert math-convention coordinates to SVG coordinates."""
        svg_x = self._tx + x * self._sx
        svg_y = self._ty + y * self._sy
        return svg_x, svg_y

    # ----- internal element helpers ----------------------------------------

    def _total_elements(self) -> int:
        return (
            len(self.points)
            + len(self.lines)
            + len(self.segments)
            + len(self.polygons)
            + len(self.regions)
        )

    def _check_cap(self) -> bool:
        if self._total_elements() >= _ELEMENT_CAP:
            logger.error("[E1466] element cap of %d reached", _ELEMENT_CAP)
            return False
        return True

    def _add_point_internal(self, pt: Any) -> None:
        if not self._check_cap():
            return
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            x, y = float(pt[0]), float(pt[1])
            label = pt[2] if len(pt) > 2 else None
        elif isinstance(pt, dict):
            x, y = float(pt["x"]), float(pt["y"])
            label = pt.get("label")
        else:
            return
        # Warn if outside viewport
        if not (self.xrange[0] <= x <= self.xrange[1] and self.yrange[0] <= y <= self.yrange[1]):
            logger.warning("[E1463] point (%.2f, %.2f) is outside viewport", x, y)
        self.points.append({"x": x, "y": y, "label": label, "radius": _POINT_RADIUS})

    def _add_line_internal(self, ln: Any) -> None:
        if not self._check_cap():
            return
        if isinstance(ln, (list, tuple)):
            if len(ln) == 3 and not isinstance(ln[1], dict):
                label, slope, intercept_val = ln[0], float(ln[1]), float(ln[2])
            elif len(ln) == 2 and isinstance(ln[1], dict):
                label = ln[0]
                d = ln[1]
                a, b, c = float(d.get("a", 0)), float(d.get("b", 0)), float(d.get("c", 0))
                if abs(a) < 1e-12 and abs(b) < 1e-12:
                    logger.warning("[E1461] degenerate line (a=0, b=0)")
                    return
                if abs(b) < 1e-12:
                    # Vertical line x = c/a — store as special case
                    slope = float("inf")
                    intercept_val = c / a
                else:
                    slope = -a / b
                    intercept_val = c / b
            else:
                return
        elif isinstance(ln, dict):
            label = ln.get("label")
            slope = float(ln.get("slope", 0))
            intercept_val = float(ln.get("intercept", 0))
        else:
            return
        self.lines.append({"label": label, "slope": slope, "intercept": intercept_val})

    def _add_segment_internal(self, seg: Any) -> None:
        if not self._check_cap():
            return
        if isinstance(seg, (list, tuple)) and len(seg) == 2:
            p1, p2 = seg
            x1, y1 = float(p1[0]), float(p1[1])
            x2, y2 = float(p2[0]), float(p2[1])
        elif isinstance(seg, dict):
            x1, y1 = float(seg["x1"]), float(seg["y1"])
            x2, y2 = float(seg["x2"]), float(seg["y2"])
        else:
            return
        self.segments.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "label": None})

    def _add_polygon_internal(self, poly: Any) -> None:
        if not self._check_cap():
            return
        if isinstance(poly, (list, tuple)):
            pts = [(float(p[0]), float(p[1])) for p in poly]
            if len(pts) >= 2 and pts[0] != pts[-1]:
                logger.warning("[E1462] polygon not closed — auto-closing")
            self.polygons.append({"points": pts})
        elif isinstance(poly, dict):
            pts = [(float(p[0]), float(p[1])) for p in poly.get("points", [])]
            if len(pts) >= 2 and pts[0] != pts[-1]:
                logger.warning("[E1462] polygon not closed — auto-closing")
            self.polygons.append({"points": pts})

    def _add_region_internal(self, reg: Any) -> None:
        if not self._check_cap():
            return
        if isinstance(reg, dict):
            pts = [(float(p[0]), float(p[1])) for p in reg.get("polygon", [])]
            fill = reg.get("fill", "rgba(0,114,178,0.2)")
            self.regions.append({"polygon": pts, "fill": fill})

    # ----- apply commands --------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Process add/modify commands from ``\\apply``."""
        # Dynamic additions
        if "add_point" in params:
            self._add_point_internal(params["add_point"])
            return
        if "add_line" in params:
            self._add_line_internal(params["add_line"])
            return
        if "add_segment" in params:
            self._add_segment_internal(params["add_segment"])
            return
        if "add_polygon" in params:
            self._add_polygon_internal(params["add_polygon"])
            return
        if "add_region" in params:
            self._add_region_internal(params["add_region"])
            return

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for i in range(len(self.points)):
            parts.append(f"point[{i}]")
        for i in range(len(self.lines)):
            parts.append(f"line[{i}]")
        for i in range(len(self.segments)):
            parts.append(f"segment[{i}]")
        for i in range(len(self.polygons)):
            parts.append(f"polygon[{i}]")
        for i in range(len(self.regions)):
            parts.append(f"region[{i}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True

        m = _POINT_RE.match(suffix)
        if m:
            return int(m.group("idx")) < len(self.points)

        m = _LINE_RE.match(suffix)
        if m:
            return int(m.group("idx")) < len(self.lines)

        m = _SEGMENT_RE.match(suffix)
        if m:
            return int(m.group("idx")) < len(self.segments)

        m = _POLYGON_RE.match(suffix)
        if m:
            return int(m.group("idx")) < len(self.polygons)

        m = _REGION_RE.match(suffix)
        if m:
            return int(m.group("idx")) < len(self.regions)

        return False

    def bounding_box(self) -> BoundingBox:
        return BoundingBox(x=0, y=0, width=self.width, height=self.height)

    # ----- SVG emission ----------------------------------------------------

    def emit_svg(self, *, render_inline_tex: Callable[[str], str] | None = None) -> str:
        parts: list[str] = []
        parts.append(
            f'<g data-primitive="plane2d" data-shape="{html_escape(self.name)}" '
            f'data-scriba-xrange="{self.xrange[0]} {self.xrange[1]}" '
            f'data-scriba-yrange="{self.yrange[0]} {self.yrange[1]}">'
        )

        # Layer 1: grid and axes (SVG coordinates, no transform)
        parts.append(self._emit_grid())
        parts.append(self._emit_axes())

        # Layer 2: geometric content (inside transform group)
        parts.append(
            f'<g class="scriba-plane-content" '
            f'transform="translate({self._tx:.4f}, {self._ty:.4f}) '
            f'scale({self._sx:.4f}, {self._sy:.4f})">'
        )
        parts.append(self._emit_regions())
        parts.append(self._emit_polygons())
        parts.append(self._emit_lines())
        parts.append(self._emit_segments())
        parts.append(self._emit_points())
        parts.append("</g>")

        # Layer 3: text labels (SVG coordinates, outside transform)
        parts.append(self._emit_labels())

        parts.append("</g>")
        return "".join(parts)

    # ----- Grid rendering --------------------------------------------------

    def _emit_grid(self) -> str:
        if not self.grid:
            return ""

        parts: list[str] = ['<g class="scriba-plane-grid">']
        xmin, xmax = self.xrange
        ymin, ymax = self.yrange

        # Integer grid
        x_start = math.ceil(xmin)
        x_end = math.floor(xmax)
        y_start = math.ceil(ymin)
        y_end = math.floor(ymax)

        for xi in range(x_start, x_end + 1):
            sx, sy_top = self.math_to_svg(xi, ymax)
            _, sy_bot = self.math_to_svg(xi, ymin)
            parts.append(
                f'<line x1="{sx:.2f}" y1="{sy_top:.2f}" '
                f'x2="{sx:.2f}" y2="{sy_bot:.2f}" '
                f'stroke="{THEME["border"]}" stroke-width="0.5" opacity="0.6"/>'
            )

        for yi in range(y_start, y_end + 1):
            sx_left, sy = self.math_to_svg(xmin, yi)
            sx_right, _ = self.math_to_svg(xmax, yi)
            parts.append(
                f'<line x1="{sx_left:.2f}" y1="{sy:.2f}" '
                f'x2="{sx_right:.2f}" y2="{sy:.2f}" '
                f'stroke="{THEME["border"]}" stroke-width="0.5" opacity="0.6"/>'
            )

        # Fine grid (0.2 intervals)
        if self.grid == "fine":
            step = 0.2
            x_fine = xmin
            while x_fine <= xmax + 1e-9:
                # Skip integer positions (already drawn)
                if abs(x_fine - round(x_fine)) > 0.05:
                    sx, sy_top = self.math_to_svg(x_fine, ymax)
                    _, sy_bot = self.math_to_svg(x_fine, ymin)
                    parts.append(
                        f'<line x1="{sx:.2f}" y1="{sy_top:.2f}" '
                        f'x2="{sx:.2f}" y2="{sy_bot:.2f}" '
                        f'stroke="{THEME["border"]}" stroke-width="0.25" opacity="0.3"/>'
                    )
                x_fine += step

            y_fine = ymin
            while y_fine <= ymax + 1e-9:
                if abs(y_fine - round(y_fine)) > 0.05:
                    sx_left, sy = self.math_to_svg(xmin, y_fine)
                    sx_right, _ = self.math_to_svg(xmax, y_fine)
                    parts.append(
                        f'<line x1="{sx_left:.2f}" y1="{sy:.2f}" '
                        f'x2="{sx_right:.2f}" y2="{sy:.2f}" '
                        f'stroke="{THEME["border"]}" stroke-width="0.25" opacity="0.3"/>'
                    )
                y_fine += step

        parts.append("</g>")
        return "".join(parts)

    # ----- Axes rendering --------------------------------------------------

    def _emit_axes(self) -> str:
        if not self.axes:
            return ""

        parts: list[str] = ['<g class="scriba-plane-axes">']
        xmin, xmax = self.xrange
        ymin, ymax = self.yrange

        # X-axis: y = 0 (or clamped to viewport boundary)
        y_axis_math = max(ymin, min(0.0, ymax))
        sx_left, sy_xaxis = self.math_to_svg(xmin, y_axis_math)
        sx_right, _ = self.math_to_svg(xmax, y_axis_math)
        parts.append(
            f'<line x1="{sx_left:.2f}" y1="{sy_xaxis:.2f}" '
            f'x2="{sx_right:.2f}" y2="{sy_xaxis:.2f}" '
            f'stroke="{THEME["fg"]}" stroke-width="1.5"/>'
        )

        # X-axis arrowhead at positive end
        parts.append(
            f'<path d="M {sx_right:.2f} {sy_xaxis:.2f} '
            f'l -{_ARROWHEAD_LEN} -{_ARROWHEAD_HALF_W} '
            f'l 0 {_ARROWHEAD_HALF_W * 2} Z" '
            f'fill="{THEME["fg"]}"/>'
        )

        # Y-axis: x = 0 (or clamped to viewport boundary)
        x_axis_math = max(xmin, min(0.0, xmax))
        sx_yaxis, sy_bottom = self.math_to_svg(x_axis_math, ymin)
        _, sy_top = self.math_to_svg(x_axis_math, ymax)
        parts.append(
            f'<line x1="{sx_yaxis:.2f}" y1="{sy_bottom:.2f}" '
            f'x2="{sx_yaxis:.2f}" y2="{sy_top:.2f}" '
            f'stroke="{THEME["fg"]}" stroke-width="1.5"/>'
        )

        # Y-axis arrowhead at positive end (top in SVG = small y)
        parts.append(
            f'<path d="M {sx_yaxis:.2f} {sy_top:.2f} '
            f'l -{_ARROWHEAD_HALF_W} {_ARROWHEAD_LEN} '
            f'l {_ARROWHEAD_HALF_W * 2} 0 Z" '
            f'fill="{THEME["fg"]}"/>'
        )

        parts.append("</g>")
        return "".join(parts)

    # ----- Geometric element rendering (inside transform group) ------------

    def _emit_points(self) -> str:
        parts: list[str] = []
        hl_suffixes = getattr(self, "_highlighted", set())
        # Scale radius from pixels to math-space units so it renders
        # at the desired pixel size after the transform is applied.
        scale_factor = abs(self._sx) if self._sx != 0 else 1
        for i, pt in enumerate(self.points):
            suffix = f"point[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            colors = svg_style_attrs(state)
            r_px = pt.get("radius", _POINT_RADIUS)
            r_math = r_px / scale_factor
            is_hl = suffix in hl_suffixes
            hl_overlay = ""
            if is_hl:
                r_hl = (r_px + 2) / scale_factor
                hl_overlay = (
                    f'<circle cx="{pt["x"]}" cy="{pt["y"]}" r="{r_hl:.4f}" '
                    f'fill="none" stroke="#F0E442" stroke-width="3" '
                    f'stroke-dasharray="6 3" '
                    f'vector-effect="non-scaling-stroke"/>'
                )
            parts.append(
                f'<g data-target="{html_escape(target)}" '
                f'class="scriba-plane-point scriba-state-{state}">'
                f'<circle cx="{pt["x"]}" cy="{pt["y"]}" r="{r_math:.4f}" '
                f'fill="{colors["fill"]}" stroke="{colors["stroke"]}" '
                f'stroke-width="1.5" vector-effect="non-scaling-stroke"/>'
                f'{hl_overlay}'
                f'</g>'
            )
        return "".join(parts)

    def _emit_lines(self) -> str:
        parts: list[str] = []
        for i, ln in enumerate(self.lines):
            suffix = f"line[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            colors = svg_style_attrs(state)
            slope = ln["slope"]
            intercept_val = ln["intercept"]

            if math.isinf(slope):
                # Vertical line x = intercept_val
                x_val = intercept_val
                if self.xrange[0] <= x_val <= self.xrange[1]:
                    endpoints = ((x_val, self.yrange[0]), (x_val, self.yrange[1]))
                else:
                    logger.warning("[E1461] vertical line x=%.2f outside viewport", x_val)
                    continue
            else:
                result = clip_line_to_viewport(slope, intercept_val, self.xrange, self.yrange)
                if result is None:
                    logger.warning("[E1461] line (slope=%.2f, intercept=%.2f) outside viewport", slope, intercept_val)
                    continue
                endpoints = result

            (x1, y1), (x2, y2) = endpoints
            sw = "1.5" if state == "idle" else "2"
            parts.append(
                f'<g data-target="{html_escape(target)}" '
                f'class="scriba-plane-line scriba-state-{state}">'
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{colors["stroke"]}" stroke-width="{sw}" '
                f'vector-effect="non-scaling-stroke"/>'
                f'</g>'
            )
        return "".join(parts)

    def _emit_segments(self) -> str:
        parts: list[str] = []
        for i, seg in enumerate(self.segments):
            suffix = f"segment[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            colors = svg_style_attrs(state)
            sw = "2" if state != "idle" else "1.5"
            parts.append(
                f'<g data-target="{html_escape(target)}" '
                f'class="scriba-plane-segment scriba-state-{state}">'
                f'<line x1="{seg["x1"]}" y1="{seg["y1"]}" '
                f'x2="{seg["x2"]}" y2="{seg["y2"]}" '
                f'stroke="{colors["stroke"]}" stroke-width="{sw}" '
                f'stroke-linecap="round" vector-effect="non-scaling-stroke"/>'
                f'</g>'
            )
        return "".join(parts)

    def _emit_polygons(self) -> str:
        parts: list[str] = []
        for i, poly in enumerate(self.polygons):
            suffix = f"polygon[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            colors = svg_style_attrs(state)
            pts = poly["points"]
            # Auto-close: SVG <polygon> auto-closes, but ensure the points list
            points_str = " ".join(f"{p[0]},{p[1]}" for p in pts)
            parts.append(
                f'<g data-target="{html_escape(target)}" '
                f'class="scriba-plane-polygon scriba-state-{state}">'
                f'<polygon points="{points_str}" '
                f'fill="rgba(0,114,178,0.15)" '
                f'stroke="{colors["stroke"]}" stroke-width="1.5" '
                f'vector-effect="non-scaling-stroke"/>'
                f'</g>'
            )
        return "".join(parts)

    def _emit_regions(self) -> str:
        parts: list[str] = []
        for i, reg in enumerate(self.regions):
            suffix = f"region[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            pts = reg["polygon"]
            fill = reg["fill"]
            points_str = " ".join(f"{p[0]},{p[1]}" for p in pts)
            parts.append(
                f'<g data-target="{html_escape(target)}" '
                f'class="scriba-plane-region scriba-state-{state}">'
                f'<polygon points="{points_str}" '
                f'fill="{html_escape(fill)}" stroke="none"/>'
                f'</g>'
            )
        return "".join(parts)

    # ----- Label layer (SVG coordinates, outside transform) ----------------

    def _emit_labels(self) -> str:
        parts: list[str] = ['<g class="scriba-plane-labels">']

        # Tick labels on axes
        if self.axes:
            parts.append(self._emit_tick_labels())

        # Point labels
        for i, pt in enumerate(self.points):
            if pt.get("label"):
                sx, sy = self.math_to_svg(pt["x"], pt["y"])
                parts.append(
                    f'<text x="{sx + _LABEL_OFFSET:.2f}" '
                    f'y="{sy - _LABEL_OFFSET:.2f}" '
                    f'font-size="{_TICK_FONT_SIZE}" fill="{THEME["fg"]}">'
                    f'{html_escape(str(pt["label"]))}</text>'
                )

        # Line labels
        for i, ln in enumerate(self.lines):
            if ln.get("label"):
                slope = ln["slope"]
                intercept_val = ln["intercept"]
                if math.isinf(slope):
                    label_x, label_y = self.math_to_svg(intercept_val, self.yrange[1])
                else:
                    result = clip_line_to_viewport(slope, intercept_val, self.xrange, self.yrange)
                    if result is None:
                        continue
                    (_, _), (x2, y2) = result
                    label_x, label_y = self.math_to_svg(x2, y2)
                parts.append(
                    f'<text x="{label_x + _LABEL_OFFSET:.2f}" '
                    f'y="{label_y - _LABEL_OFFSET:.2f}" '
                    f'font-size="{_TICK_FONT_SIZE}" fill="{THEME["fg"]}">'
                    f'{html_escape(str(ln["label"]))}</text>'
                )

        parts.append("</g>")
        return "".join(parts)

    def _emit_tick_labels(self) -> str:
        parts: list[str] = []
        xmin, xmax = self.xrange
        ymin, ymax = self.yrange

        y_axis_math = max(ymin, min(0.0, ymax))
        x_axis_math = max(xmin, min(0.0, xmax))

        # Compute tick spacing in SVG pixels
        sx_per_unit = abs(self._sx)
        sy_per_unit = abs(self._sy)

        # X-axis tick labels
        x_start = math.ceil(xmin)
        x_end = math.floor(xmax)
        for xi in range(x_start, x_end + 1):
            if xi == 0 and self.xrange[0] <= 0 <= self.xrange[1]:
                continue  # skip origin label on x-axis
            if sx_per_unit < _MIN_TICK_SPACING_PX:
                continue
            sx, sy = self.math_to_svg(xi, y_axis_math)
            parts.append(
                f'<text x="{sx:.2f}" y="{sy + _TICK_FONT_SIZE + 2:.2f}" '
                f'text-anchor="middle" font-size="{_TICK_FONT_SIZE}" '
                f'fill="{THEME["fg_muted"]}">{xi}</text>'
            )

        # Y-axis tick labels
        y_start = math.ceil(ymin)
        y_end = math.floor(ymax)
        for yi in range(y_start, y_end + 1):
            if yi == 0 and self.yrange[0] <= 0 <= self.yrange[1]:
                continue
            if sy_per_unit < _MIN_TICK_SPACING_PX:
                continue
            sx, sy = self.math_to_svg(x_axis_math, yi)
            parts.append(
                f'<text x="{sx - _LABEL_OFFSET:.2f}" y="{sy + 3:.2f}" '
                f'text-anchor="end" font-size="{_TICK_FONT_SIZE}" '
                f'fill="{THEME["fg_muted"]}">{yi}</text>'
            )

        return "".join(parts)
