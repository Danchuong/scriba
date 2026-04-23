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
from typing import Any, Callable, ClassVar, Sequence

from scriba.animation.errors import _emit_warning, _animation_error
from scriba.animation.primitives.base import (
    ARROW_STYLES,
    _LabelPlacement,
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    THEME,
    _render_svg_text,
    arrow_height_above,
    register_primitive,
    svg_style_attrs,
)
from scriba.animation.primitives._svg_helpers import (
    _LABEL_PILL_PAD_X as _SVG_LABEL_PILL_PAD_X,
    _LABEL_PILL_PAD_Y as _SVG_LABEL_PILL_PAD_Y,
    _LABEL_PILL_RADIUS as _SVG_LABEL_PILL_RADIUS,
    emit_position_label_svg,
    _place_pill,
)
from scriba.animation.primitives._obstacle_types import ObstacleSegment
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
_ARROW_CELL_HEIGHT = 35  # virtual cell height for arrow curve offset calculation

# Selector regexes
_POINT_RE = re.compile(r"^point\[(?P<idx>\d+)\]$")
_LINE_RE = re.compile(r"^line\[(?P<idx>\d+)\]$")
_SEGMENT_RE = re.compile(r"^segment\[(?P<idx>\d+)\]$")
_POLYGON_RE = re.compile(r"^polygon\[(?P<idx>\d+)\]$")
_REGION_RE = re.compile(r"^region\[(?P<idx>\d+)\]$")

# ---------------------------------------------------------------------------
# Tombstone sentinel (RFC-001 §4.3 — dynamic remove ops)
# ---------------------------------------------------------------------------

_TOMBSTONE: Any = object()
"""Sentinel marking a slot that has been removed. ``addressable_parts``,
``validate_selector``, and the per-element ``_emit_*`` loops skip tombstoned
slots, but the index positions remain stable across later frames so existing
selectors (e.g. ``point[5]``) remain valid when ``point[2]`` is removed."""

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

    primitive_type = "plane2d"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "point[{i}]": "point by index",
        "line[{i}]": "line by index",
        "segment[{i}]": "segment by index",
        "polygon[{i}]": "polygon by index",
        "region[{i}]": "shaded region by index",
        "all": "all elements",
    }

    # Accepted keyword parameters for ``\\shape{name}{Plane2D}{...}``.
    # Unknown keys raise E1114 with a fuzzy "did you mean" hint via
    # :meth:`PrimitiveBase._validate_accepted_params`.
    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset(
        {
            "xrange",
            "yrange",
            "grid",
            "axes",
            "aspect",
            "width",
            "height",
            "points",
            "lines",
            "segments",
            "polygons",
            "regions",
            "show_coords",
        }
    )

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        # --- range params ---
        self.xrange: tuple[float, float] = tuple(params.get("xrange", [-5.0, 5.0]))  # type: ignore[assignment]
        self.yrange: tuple[float, float] = tuple(params.get("yrange", [-5.0, 5.0]))  # type: ignore[assignment]

        if self.xrange[1] - self.xrange[0] == 0:
            raise _animation_error("E1460", "xrange has equal endpoints (degenerate viewport)")
        if self.yrange[1] - self.yrange[0] == 0:
            raise _animation_error("E1460", "yrange has equal endpoints (degenerate viewport)")

        # --- display params ---
        self.grid: bool | str = params.get("grid", True)
        self.axes: bool = bool(params.get("axes", True))
        aspect = params.get("aspect", "equal")
        if aspect not in ("equal", "auto"):
            raise _animation_error("E1465", f"aspect must be 'equal' or 'auto', got {aspect!r}")
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

        self.show_coords: bool = bool(params.get("show_coords", False))

        self._arrow_cell_height = float(_ARROW_CELL_HEIGHT)
        self._arrow_layout = "2d"

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

    def _check_cap(self) -> None:
        """Raise E1466 if adding one more element would exceed the cap.

        Converts the previous soft-drop behaviour to a hard limit so users
        see data loss instead of silently receiving a truncated plane.
        """
        current = self._total_elements()
        if current >= _ELEMENT_CAP:
            raise _animation_error(
                "E1466",
                f"Plane2D element count {current + 1} exceeds maximum "
                f"{_ELEMENT_CAP} per frame; remove elements or split into "
                f"multiple \\step frames",
            )

    def _add_point_internal(self, pt: Any) -> None:
        self._check_cap()
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            x, y = float(pt[0]), float(pt[1])
            label = pt[2] if len(pt) > 2 else None
        elif isinstance(pt, dict):
            x, y = float(pt["x"]), float(pt["y"])
            label = pt.get("label")
        else:
            return
        # Warn if outside viewport — SF-2 (RFC-002): hidden severity,
        # never auto-raised, always observable via Document.warnings.
        if not (self.xrange[0] <= x <= self.xrange[1] and self.yrange[0] <= y <= self.yrange[1]):
            logger.warning("[E1463] point (%.2f, %.2f) is outside viewport", x, y)
            _emit_warning(
                self._ctx,
                "E1463",
                f"point ({x:.2f}, {y:.2f}) is outside viewport "
                f"[{self.xrange[0]}, {self.xrange[1]}] x "
                f"[{self.yrange[0]}, {self.yrange[1]}]",
                primitive=self.name,
                severity="hidden",
            )
        self.points.append({"x": x, "y": y, "label": label, "radius": _POINT_RADIUS})

    def _add_line_internal(self, ln: Any) -> None:
        self._check_cap()
        if isinstance(ln, (list, tuple)):
            if len(ln) == 3 and not isinstance(ln[1], dict):
                label, slope, intercept_val = ln[0], float(ln[1]), float(ln[2])
            elif len(ln) == 2 and isinstance(ln[1], dict):
                label = ln[0]
                d = ln[1]
                a, b, c = float(d.get("a", 0)), float(d.get("b", 0)), float(d.get("c", 0))
                if abs(a) < 1e-12 and abs(b) < 1e-12:
                    logger.warning("[E1461] degenerate line (a=0, b=0)")
                    _emit_warning(
                        self._ctx,
                        "E1461",
                        "degenerate line: both a and b are zero "
                        "(ax + by = c has no well-defined direction)",
                        primitive=self.name,
                        severity="dangerous",
                    )
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
        self._check_cap()
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
        self._check_cap()
        if isinstance(poly, (list, tuple)):
            pts = [(float(p[0]), float(p[1])) for p in poly]
            if len(pts) >= 2 and pts[0] != pts[-1]:
                logger.warning("[E1462] polygon not closed — auto-closing")
                _emit_warning(
                    self._ctx,
                    "E1462",
                    "polygon not closed — auto-closing by appending the "
                    "first point to the end of the list",
                    primitive=self.name,
                    severity="dangerous",
                )
                # SF-1 correctness fix: explicitly append the first point
                # so the internal list matches what the emitter draws.
                pts.append(pts[0])
            self.polygons.append({"points": pts})
        elif isinstance(poly, dict):
            pts = [(float(p[0]), float(p[1])) for p in poly.get("points", [])]
            if len(pts) >= 2 and pts[0] != pts[-1]:
                logger.warning("[E1462] polygon not closed — auto-closing")
                _emit_warning(
                    self._ctx,
                    "E1462",
                    "polygon not closed — auto-closing by appending the "
                    "first point to the end of the list",
                    primitive=self.name,
                    severity="dangerous",
                )
                pts.append(pts[0])
            self.polygons.append({"points": pts})

    def _add_region_internal(self, reg: Any) -> None:
        self._check_cap()
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
        # Dynamic removals (RFC-001 §4.3 — tombstone semantics)
        if "remove_point" in params:
            self._remove_point_internal(int(params["remove_point"]))
            return
        if "remove_line" in params:
            self._remove_line_internal(int(params["remove_line"]))
            return
        if "remove_segment" in params:
            self._remove_segment_internal(int(params["remove_segment"]))
            return
        if "remove_polygon" in params:
            self._remove_polygon_internal(int(params["remove_polygon"]))
            return
        if "remove_region" in params:
            self._remove_region_internal(int(params["remove_region"]))
            return

    # ----- internal remove helpers (RFC-001 §4.3) --------------------------

    def _remove_point_internal(self, idx: int) -> None:
        if not (0 <= idx < len(self.points)):
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' has no point[{idx}] "
                f"(valid: 0..{len(self.points) - 1 if self.points else -1})",
            )
        if self.points[idx] is _TOMBSTONE:
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' point[{idx}] already removed",
            )
        self.points[idx] = _TOMBSTONE

    def _remove_line_internal(self, idx: int) -> None:
        if not (0 <= idx < len(self.lines)):
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' has no line[{idx}] "
                f"(valid: 0..{len(self.lines) - 1 if self.lines else -1})",
            )
        if self.lines[idx] is _TOMBSTONE:
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' line[{idx}] already removed",
            )
        self.lines[idx] = _TOMBSTONE

    def _remove_segment_internal(self, idx: int) -> None:
        if not (0 <= idx < len(self.segments)):
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' has no segment[{idx}] "
                f"(valid: 0..{len(self.segments) - 1 if self.segments else -1})",
            )
        if self.segments[idx] is _TOMBSTONE:
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' segment[{idx}] already removed",
            )
        self.segments[idx] = _TOMBSTONE

    def _remove_polygon_internal(self, idx: int) -> None:
        if not (0 <= idx < len(self.polygons)):
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' has no polygon[{idx}] "
                f"(valid: 0..{len(self.polygons) - 1 if self.polygons else -1})",
            )
        if self.polygons[idx] is _TOMBSTONE:
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' polygon[{idx}] already removed",
            )
        self.polygons[idx] = _TOMBSTONE

    def _remove_region_internal(self, idx: int) -> None:
        if not (0 <= idx < len(self.regions)):
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' has no region[{idx}] "
                f"(valid: 0..{len(self.regions) - 1 if self.regions else -1})",
            )
        if self.regions[idx] is _TOMBSTONE:
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' region[{idx}] already removed",
            )
        self.regions[idx] = _TOMBSTONE

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for i, p in enumerate(self.points):
            if p is not _TOMBSTONE:
                parts.append(f"point[{i}]")
        for i, ln in enumerate(self.lines):
            if ln is not _TOMBSTONE:
                parts.append(f"line[{i}]")
        for i, s in enumerate(self.segments):
            if s is not _TOMBSTONE:
                parts.append(f"segment[{i}]")
        for i, poly in enumerate(self.polygons):
            if poly is not _TOMBSTONE:
                parts.append(f"polygon[{i}]")
        for i, reg in enumerate(self.regions):
            if reg is not _TOMBSTONE:
                parts.append(f"region[{i}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True

        m = _POINT_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return idx < len(self.points) and self.points[idx] is not _TOMBSTONE

        m = _LINE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return idx < len(self.lines) and self.lines[idx] is not _TOMBSTONE

        m = _SEGMENT_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return idx < len(self.segments) and self.segments[idx] is not _TOMBSTONE

        m = _POLYGON_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return idx < len(self.polygons) and self.polygons[idx] is not _TOMBSTONE

        m = _REGION_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return idx < len(self.regions) and self.regions[idx] is not _TOMBSTONE

        return False

    # ----- annotation point resolution -------------------------------------

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG ``(x, y)`` for an annotation selector.

        Supported selector forms (``P`` is the shape name):
        - ``P.point[i]``   — center of point *i*
        - ``P.line[i]``    — midpoint of the visible line segment
        - ``P.segment[i]`` — midpoint of the segment

        Returns ``None`` when the selector does not match this primitive
        or the referenced element does not exist / is tombstoned.
        """
        # Strip the ``<name>.`` prefix if present
        prefix = f"{self.name}."
        if selector.startswith(prefix):
            suffix = selector[len(prefix):]
        else:
            return None

        # --- point ---
        m = _POINT_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if idx < len(self.points) and self.points[idx] is not _TOMBSTONE:
                pt = self.points[idx]
                return self.math_to_svg(pt["x"], pt["y"])
            return None

        # --- line (use visible midpoint) ---
        m = _LINE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if idx < len(self.lines) and self.lines[idx] is not _TOMBSTONE:
                ln = self.lines[idx]
                slope = ln["slope"]
                intercept_val = ln["intercept"]
                if math.isinf(slope):
                    x_val = intercept_val
                    if self.xrange[0] <= x_val <= self.xrange[1]:
                        mid_y = (self.yrange[0] + self.yrange[1]) / 2
                        return self.math_to_svg(x_val, mid_y)
                    return None
                result = clip_line_to_viewport(
                    slope, intercept_val, self.xrange, self.yrange,
                )
                if result is None:
                    return None
                (x1, y1), (x2, y2) = result
                return self.math_to_svg((x1 + x2) / 2, (y1 + y2) / 2)
            return None

        # --- segment (midpoint) ---
        m = _SEGMENT_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if idx < len(self.segments) and self.segments[idx] is not _TOMBSTONE:
                seg = self.segments[idx]
                mid_x = (seg["x1"] + seg["x2"]) / 2
                mid_y = (seg["y1"] + seg["y2"]) / 2
                return self.math_to_svg(mid_x, mid_y)
            return None

        # --- polygon (centroid) ---
        m = _POLYGON_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if idx < len(self.polygons) and self.polygons[idx] is not _TOMBSTONE:
                pts = self.polygons[idx]["points"]
                if pts:
                    cx = sum(p[0] for p in pts) / len(pts)
                    cy = sum(p[1] for p in pts) / len(pts)
                    return self.math_to_svg(cx, cy)
            return None

        return None

    # ----- bounding box ----------------------------------------------------

    def bounding_box(self) -> BoundingBox:
        arrow_above = arrow_height_above(
            self._annotations,
            self.resolve_annotation_point,
            cell_height=float(_ARROW_CELL_HEIGHT),
            layout="2d",
        )
        return BoundingBox(
            x=0,
            y=0,
            width=self.width,
            height=self.height + arrow_above,
        )

    # ----- SVG emission ----------------------------------------------------

    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        effective_anns = self._annotations
        arrow_above = arrow_height_above(
            effective_anns,
            self.resolve_annotation_point,
            cell_height=float(_ARROW_CELL_HEIGHT),
            layout="2d",
        )

        parts: list[str] = []
        parts.append(
            f'<g data-primitive="plane2d" data-shape="{_escape_xml(self.name)}" '
            f'data-scriba-xrange="{self.xrange[0]} {self.xrange[1]}" '
            f'data-scriba-yrange="{self.yrange[0]} {self.yrange[1]}">'
        )

        # Shift all content down when arrows need space above the plot
        if arrow_above > 0:
            parts.append(f'<g transform="translate(0, {arrow_above})">')

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
        parts.append(self._emit_labels(render_inline_tex=render_inline_tex))

        # Layer 4: annotations (SVG coordinates, outside transform)
        if effective_anns:
            arrow_anns = [a for a in effective_anns if a.get("arrow_from") or a.get("arrow")]
            text_anns = [a for a in effective_anns if not a.get("arrow_from") and not a.get("arrow")]
            if arrow_anns:
                self.emit_annotation_arrows(
                    parts,
                    arrow_anns,
                    render_inline_tex=render_inline_tex,
                    scene_segments=scene_segments,
                    self_offset=self_offset,
                )
            # FP-1/FP-2/FP-4 fix: route position-only annotations through
            # emit_position_label_svg (uses _svg_helpers collision registry,
            # viewBox clamp, and canonical pill metrics) instead of the legacy
            # _emit_text_annotation that emitted <text> directly with hardcoded
            # metrics and no clamp.
            if text_anns:
                text_placed: list[_LabelPlacement] = []
                for ann in text_anns:
                    target = ann.get("target", "")
                    anchor = self.resolve_annotation_point(target)
                    if anchor is None:
                        continue
                    emit_position_label_svg(
                        parts,
                        ann,
                        anchor_point=anchor,
                        cell_height=float(_ARROW_CELL_HEIGHT),
                        render_inline_tex=render_inline_tex,
                        placed_labels=text_placed,
                    )

        # Close the translate group if we opened one for arrow space
        if arrow_above > 0:
            parts.append("</g>")

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
                f'stroke="{THEME["border"]}" stroke-width="0.5" opacity="0.6"'
                f' vector-effect="non-scaling-stroke"/>'
            )

        for yi in range(y_start, y_end + 1):
            sx_left, sy = self.math_to_svg(xmin, yi)
            sx_right, _ = self.math_to_svg(xmax, yi)
            parts.append(
                f'<line x1="{sx_left:.2f}" y1="{sy:.2f}" '
                f'x2="{sx_right:.2f}" y2="{sy:.2f}" '
                f'stroke="{THEME["border"]}" stroke-width="0.5" opacity="0.6"'
                f' vector-effect="non-scaling-stroke"/>'
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
                        f'stroke="{THEME["border"]}" stroke-width="0.25" opacity="0.3"'
                        f' vector-effect="non-scaling-stroke"/>'
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
                        f'stroke="{THEME["border"]}" stroke-width="0.25" opacity="0.3"'
                        f' vector-effect="non-scaling-stroke"/>'
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
            if pt is _TOMBSTONE:
                continue
            suffix = f"point[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            if state == "hidden":
                continue
            colors = svg_style_attrs(state)
            r_px = pt.get("radius", _POINT_RADIUS)
            r_math = r_px / scale_factor
            is_hl = suffix in hl_suffixes
            # β: highlight is a state, not a dashed overlay. Promote to the
            # highlight state class when the point is otherwise idle; leave
            # non-idle states alone so current/error/good keep their signal.
            effective_state = "highlight" if (is_hl and state == "idle") else state
            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
                f'class="scriba-plane-point scriba-state-{effective_state}">'
                f'<circle cx="{pt["x"]}" cy="{pt["y"]}" r="{r_math:.4f}" '
                f'vector-effect="non-scaling-stroke"/>'
                f'</g>'
            )
        return "".join(parts)

    def _emit_lines(self) -> str:
        parts: list[str] = []
        for i, ln in enumerate(self.lines):
            if ln is _TOMBSTONE:
                continue
            suffix = f"line[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            if state == "hidden":
                continue
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
                f'<g data-target="{_escape_xml(target)}" '
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
            if seg is _TOMBSTONE:
                continue
            suffix = f"segment[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            if state == "hidden":
                continue
            colors = svg_style_attrs(state)
            sw = "2" if state != "idle" else "1.5"
            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
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
            if poly is _TOMBSTONE:
                continue
            suffix = f"polygon[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            if state == "hidden":
                continue
            colors = svg_style_attrs(state)
            pts = poly["points"]
            # Auto-close: SVG <polygon> auto-closes, but ensure the points list
            points_str = " ".join(f"{p[0]},{p[1]}" for p in pts)
            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
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
            if reg is _TOMBSTONE:
                continue
            suffix = f"region[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            if state == "hidden":
                continue
            pts = reg["polygon"]
            fill = reg["fill"]
            points_str = " ".join(f"{p[0]},{p[1]}" for p in pts)
            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
                f'class="scriba-plane-region scriba-state-{state}">'
                f'<polygon points="{points_str}" '
                f'fill="{_escape_xml(fill)}" stroke="none"/>'
                f'</g>'
            )
        return "".join(parts)

    # ----- Label layer (SVG coordinates, outside transform) ----------------

    def _emit_labels(self, *, render_inline_tex: "Callable[[str], str] | None" = None) -> str:
        parts: list[str] = ['<g class="scriba-plane-labels">']

        # Tick labels on axes
        if self.axes:
            parts.append(self._emit_tick_labels())

        # Point labels (with opt-in coordinate display)
        for i, pt in enumerate(self.points):
            if pt is _TOMBSTONE:
                continue
            if self.get_state(f"point[{i}]") == "hidden":
                continue
            label_text = pt.get("label")
            if not label_text and self.show_coords:
                label_text = f"({pt['x']:.6g}, {pt['y']:.6g})"
            if label_text:
                sx, sy = self.math_to_svg(pt["x"], pt["y"])
                parts.append(
                    _render_svg_text(
                        str(label_text),
                        round(sx + _LABEL_OFFSET),
                        round(sy - _LABEL_OFFSET),
                        fill=THEME["fg"],
                        font_size=str(_TICK_FONT_SIZE),
                        render_inline_tex=render_inline_tex,
                    )
                )

        # Line labels — with collision avoidance and viewBox clamping.
        # FP-3 fix: use canonical constants from _svg_helpers instead of
        # hardcoded local values for PAD_X, PAD_Y, and PILL_R.
        _LINE_LABEL_CHAR_W = 7  # approx px per char at _TICK_FONT_SIZE (line-label font)
        _LINE_LABEL_H = 14
        _LINE_LABEL_PAD = 10
        _LINE_PILL_PAD_X = _SVG_LABEL_PILL_PAD_X   # was: 5 (FP-3 fix)
        _LINE_PILL_PAD_Y = _SVG_LABEL_PILL_PAD_Y   # was: 2 (FP-3 fix)
        _LINE_PILL_R = _SVG_LABEL_PILL_RADIUS       # was: 3 (FP-3 fix)
        _LINE_NUDGE_STEP = 16
        _LINE_MAX_NUDGE = 4

        placed_labels: list[_LabelPlacement] = []
        vb_w = self.width
        vb_h = self.height

        for i, ln in enumerate(self.lines):
            if ln is _TOMBSTONE:
                continue
            if self.get_state(f"line[{i}]") == "hidden":
                continue
            if ln.get("label"):
                label_text = str(ln["label"])
                slope = ln["slope"]
                intercept_val = ln["intercept"]
                if math.isinf(slope):
                    label_x, label_y = self.math_to_svg(
                        intercept_val, self.yrange[1],
                    )
                else:
                    result = clip_line_to_viewport(
                        slope, intercept_val, self.xrange, self.yrange,
                    )
                    if result is None:
                        continue
                    (_, _), (x2, y2) = result
                    label_x, label_y = self.math_to_svg(x2, y2)

                label_x += _LABEL_OFFSET
                label_y -= _LABEL_OFFSET

                est_w = len(label_text) * _LINE_LABEL_CHAR_W + _LINE_LABEL_PAD
                pill_w = est_w + _LINE_PILL_PAD_X * 2
                pill_h = _LINE_LABEL_H + _LINE_PILL_PAD_Y * 2

                # Collision avoidance: nudge downward if overlapping
                candidate = _LabelPlacement(
                    x=label_x, y=label_y,
                    width=est_w, height=_LINE_LABEL_H,
                )
                for _attempt in range(_LINE_MAX_NUDGE):
                    if not any(
                        candidate.overlaps(p) for p in placed_labels
                    ):
                        break
                    label_y += _LINE_NUDGE_STEP
                    candidate = _LabelPlacement(
                        x=label_x, y=label_y,
                        width=est_w, height=_LINE_LABEL_H,
                    )

                # Clamp within viewBox
                half_w = est_w / 2
                label_x = max(
                    _PAD + half_w,
                    min(label_x, vb_w - _PAD - half_w),
                )
                label_y = max(12.0, min(label_y, vb_h - 4.0))

                candidate = _LabelPlacement(
                    x=label_x, y=label_y,
                    width=est_w, height=_LINE_LABEL_H,
                )
                placed_labels.append(candidate)

                # Background pill for readability
                pill_rx = label_x - pill_w / 2
                pill_ry = label_y - pill_h / 2
                parts.append(
                    f'<rect x="{pill_rx:.1f}" y="{pill_ry:.1f}" '
                    f'width="{pill_w}" height="{pill_h}" '
                    f'rx="{_LINE_PILL_R}" fill="white" '
                    f'fill-opacity="0.85"/>'
                )
                parts.append(
                    _render_svg_text(
                        label_text,
                        round(label_x),
                        round(label_y),
                        fill=THEME["fg"],
                        font_size=str(_TICK_FONT_SIZE),
                        text_anchor="middle",
                        render_inline_tex=render_inline_tex,
                    )
                )

        parts.append("</g>")
        return "".join(parts)

    @staticmethod
    def _nice_ticks(vmin: float, vmax: float, max_ticks: int = 10) -> list[float]:
        """Generate a list of nicely-spaced tick values between *vmin* and *vmax*.

        Picks a "nice" step from {1, 2, 2.5, 5} x 10^n so that the number of
        ticks is roughly between 5 and *max_ticks*.  Ported from
        ``MetricPlot._nice_ticks``.
        """
        if vmax <= vmin:
            return [vmin]
        raw_step = (vmax - vmin) / max(max_ticks - 1, 1)
        magnitude = 10 ** math.floor(math.log10(max(abs(raw_step), 1e-15)))
        residual = raw_step / magnitude
        if residual <= 1.0:
            nice_step = magnitude
        elif residual <= 2.0:
            nice_step = 2 * magnitude
        elif residual <= 2.5:
            nice_step = 2.5 * magnitude
        elif residual <= 5.0:
            nice_step = 5 * magnitude
        else:
            nice_step = 10 * magnitude

        start = math.ceil(vmin / nice_step) * nice_step
        ticks: list[float] = []
        t = start
        while t <= vmax + nice_step * 0.01:
            ticks.append(round(t, 10))
            t += nice_step
        return ticks if ticks else [vmin]

    @staticmethod
    def _format_tick(v: float) -> str:
        """Format a tick value: use int when exact, else compact float."""
        if v == int(v):
            return str(int(v))
        return f"{v:.6g}"

    def _emit_tick_labels(self) -> str:
        parts: list[str] = []
        xmin, xmax = self.xrange
        ymin, ymax = self.yrange

        y_axis_math = max(ymin, min(0.0, ymax))
        x_axis_math = max(xmin, min(0.0, xmax))

        x_ticks = self._nice_ticks(xmin, xmax)
        y_ticks = self._nice_ticks(ymin, ymax)

        # X-axis tick labels — skip adjacent ticks that are too close in px
        prev_sx: float | None = None
        for v in x_ticks:
            # Suppress origin "0" only when it is interior to the range
            if v == 0 and xmin < 0 < xmax:
                continue
            sx, sy = self.math_to_svg(v, y_axis_math)
            if prev_sx is not None and abs(sx - prev_sx) < _MIN_TICK_SPACING_PX:
                continue
            label = self._format_tick(v)
            parts.append(
                f'<text x="{sx:.2f}" y="{sy + _TICK_FONT_SIZE + 2:.2f}" '
                f'text-anchor="middle" font-size="{_TICK_FONT_SIZE}" '
                f'fill="{THEME["fg_muted"]}">{label}</text>'
            )
            prev_sx = sx

        # Y-axis tick labels — skip adjacent ticks that are too close in px
        prev_sy: float | None = None
        for v in y_ticks:
            if v == 0 and ymin < 0 < ymax:
                continue
            sx, sy = self.math_to_svg(x_axis_math, v)
            if prev_sy is not None and abs(sy - prev_sy) < _MIN_TICK_SPACING_PX:
                continue
            label = self._format_tick(v)
            parts.append(
                f'<text x="{sx - _LABEL_OFFSET:.2f}" y="{sy + 3:.2f}" '
                f'text-anchor="end" font-size="{_TICK_FONT_SIZE}" '
                f'fill="{THEME["fg_muted"]}">{label}</text>'
            )
            prev_sy = sy

        return "".join(parts)

    # -- obstacle protocol (v0.12.0 W3-α) ------------------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list[ObstacleSegment]:
        """Return segment obstacles for the current frame (R-31).

        Returns all plotted lines (``p.line[*]``) and axis spines in SVG
        pixel coordinates (the same coordinate space as pill placements).

        Segment state mapping:
            ``"current"`` → severity ``"MUST"`` (hard-block in scoring)
            all other visible states → severity ``"SHOULD"``

        Coordinate space: endpoints are computed via :meth:`math_to_svg` so
        they live in SVG user-coordinate space, matching the space used by
        ``_LabelPlacement.x/y`` and ``_score_candidate``.

        Ordering (stable, D-1 deterministic):
            1. Plotted lines in index order (``line[0]``, ``line[1]``, …).
            2. Axis spines (X-spine then Y-spine) if ``self.axes`` is True.

        Hidden lines and tombstoned slots are skipped.
        """
        segments: list[ObstacleSegment] = []

        # --- 1. Plotted lines (p.line[*]) ---
        for i, ln in enumerate(self.lines):
            if ln is _TOMBSTONE:
                continue
            suffix = f"line[{i}]"
            state = self.get_state(suffix)
            if state == "hidden":
                continue

            slope = ln["slope"]
            intercept_val = ln["intercept"]

            if math.isinf(slope):
                # Vertical line x = intercept_val
                x_val = intercept_val
                if not (self.xrange[0] <= x_val <= self.xrange[1]):
                    continue
                endpoints: tuple[tuple[float, float], tuple[float, float]] = (
                    (x_val, self.yrange[0]),
                    (x_val, self.yrange[1]),
                )
            else:
                result = clip_line_to_viewport(
                    slope, intercept_val, self.xrange, self.yrange
                )
                if result is None:
                    continue
                endpoints = result

            (mx0, my0), (mx1, my1) = endpoints
            sx0, sy0 = self.math_to_svg(mx0, my0)
            sx1, sy1 = self.math_to_svg(mx1, my1)

            # Map state → state literal for ObstacleSegment
            obs_state: str
            if state == "current":
                obs_state = "current"
            elif state in ("dim",):
                obs_state = "dim"
            elif state in ("done",):
                obs_state = "done"
            else:
                obs_state = "default"

            severity = "MUST" if obs_state == "current" else "SHOULD"

            segments.append(
                ObstacleSegment(
                    kind="plot_line",
                    x0=sx0,
                    y0=sy0,
                    x1=sx1,
                    y1=sy1,
                    state=obs_state,  # type: ignore[arg-type]
                    severity=severity,  # type: ignore[arg-type]
                )
            )

        # --- 2. Axis spines (kind="axis_tick", severity always "SHOULD") ---
        if self.axes:
            xmin, xmax = self.xrange
            ymin, ymax = self.yrange

            # X-axis spine: y = 0 clamped to viewport
            y_axis_math = max(ymin, min(0.0, ymax))
            sx_left, sy_xaxis = self.math_to_svg(xmin, y_axis_math)
            sx_right, _ = self.math_to_svg(xmax, y_axis_math)
            segments.append(
                ObstacleSegment(
                    kind="axis_tick",
                    x0=sx_left,
                    y0=sy_xaxis,
                    x1=sx_right,
                    y1=sy_xaxis,
                    state="default",
                    severity="SHOULD",
                )
            )

            # Y-axis spine: x = 0 clamped to viewport
            x_axis_math = max(xmin, min(0.0, xmax))
            sx_yaxis, sy_bottom = self.math_to_svg(x_axis_math, ymin)
            _, sy_top = self.math_to_svg(x_axis_math, ymax)
            segments.append(
                ObstacleSegment(
                    kind="axis_tick",
                    x0=sx_yaxis,
                    y0=sy_bottom,
                    x1=sx_yaxis,
                    y1=sy_top,
                    state="default",
                    severity="SHOULD",
                )
            )

        return segments
