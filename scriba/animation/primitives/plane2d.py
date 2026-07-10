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
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _emit_warning, _animation_error
from scriba.animation.primitives._params import coerce_int
from scriba.animation.primitives.base import (
    _label_width_text,
    allow_forbidden_pattern,
    estimate_text_width,
    _LabelPlacement,
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    THEME,
    _render_svg_text,
    position_label_height_below,
    register_primitive,
    svg_style_attrs,
)
from scriba.animation.primitives._text_metrics import measure_label_line
from scriba.animation.primitives._svg_helpers import (
    _LABEL_PILL_PAD_X as _SVG_LABEL_PILL_PAD_X,
    _LABEL_PILL_PAD_Y as _SVG_LABEL_PILL_PAD_Y,
    _LABEL_PILL_RADIUS as _SVG_LABEL_PILL_RADIUS,
)
from scriba.animation.primitives._obstacle_types import ObstacleSegment
from scriba.animation.primitives.plane2d_compute import clip_line_to_viewport

__all__ = ["Plane2D"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PAD = 32
_MIN_PLOT_H = 3 * _PAD  # 96: keeps interior (height-2*_PAD) >= _PAD — legible, non-inverted
_MAX_PLOT_H = 1280      # 4 * default width: bounds the tall-domain viewBox runaway
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
_CIRCLE_RE = re.compile(r"^circle\[(?P<idx>\d+)\]$")
_ARC_RE = re.compile(r"^arc\[(?P<idx>\d+)\]$")
_WEDGE_RE = re.compile(r"^wedge\[(?P<idx>\d+)\]$")

# Every addressable geometric part in one shape: ``<kind>[idx]``. Used by
# ``renders_value`` to reject a ``value=`` on any of them (none has a value
# display slot — see the method docstring).
_VALUE_LESS_PART_RE = re.compile(
    r"^(?:point|line|segment|polygon|region|circle|arc|wedge)\[\d+\]$"
)

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
# Circles:  {"cx": float, "cy": float, "r": float}
# Arcs:     {"cx": float, "cy": float, "r": float, "a0": float, "a1": float}  (degrees, CCW)
# Wedges:   {"cx": float, "cy": float, "r": float, "a0": float, "a1": float}  (degrees, CCW)


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
    # \apply geometry verbs: add_/remove_ every element kind, plus in-place
    # move_/rotate_ glides. Mirrors the apply_command dispatch below.
    APPLY_KEYS: ClassVar[frozenset[str]] = frozenset({
        "add_point", "add_line", "add_segment", "add_polygon", "add_region",
        "add_circle", "add_arc", "add_wedge",
        "remove_point", "remove_line", "remove_segment", "remove_polygon",
        "remove_region", "remove_circle", "remove_arc", "remove_wedge",
        "move_point", "move_line", "move_segment",
        "rotate_point", "rotate_line", "rotate_segment",
    })

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "point[{i}]": "point by index",
        "line[{i}]": "line by index",
        "segment[{i}]": "segment by index",
        "polygon[{i}]": "polygon by index",
        "region[{i}]": "shaded region by index",
        "circle[{i}]": "circle by index",
        "arc[{i}]": "arc by index",
        "wedge[{i}]": "wedge (sector) by index",
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
            "circles",
            "arcs",
            "wedges",
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
            explicit_h = params.get("height")
            if explicit_h is not None:
                # Honor the escape hatch verbatim — a user asking for a tall
                # plot on a wide domain must not be capped to the collapsed
                # equal-aspect value (was min(explicit, computed), RQ family E).
                self.height = int(explicit_h)
            else:
                computed_h = self.width * (self.yrange[1] - self.yrange[0]) / (self.xrange[1] - self.xrange[0])
                # Clamp into a legible, non-inverted, non-runaway band: the
                # transform inverts the Y-flip once the interior
                # (height - 2*_PAD) goes negative, and a tall/narrow domain
                # otherwise runs the viewBox to tens of thousands of px.
                self.height = int(min(max(computed_h, _MIN_PLOT_H), _MAX_PLOT_H))
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
        self.circles: list[dict[str, Any]] = []
        self.arcs: list[dict[str, Any]] = []
        self.wedges: list[dict[str, Any]] = []

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
        for circ in params.get("circles", []):
            self._add_circle_internal(circ)
        for arc in params.get("arcs", []):
            self._add_arc_internal(arc)
        for wed in params.get("wedges", []):
            self._add_wedge_internal(wed)

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
            + len(self.circles)
            + len(self.arcs)
            + len(self.wedges)
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
            raise _animation_error(
                "E1467",
                f"malformed point add-spec: {pt!r}",
                hint="expected (x, y), (x, y, label), or {x, y, label?}",
            )
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
                raise _animation_error(
                    "E1467",
                    f"malformed line add-spec: {ln!r}",
                    hint="expected (label, slope, intercept) or "
                    "(label, {a, b, c}) for ax+by=c",
                )
        elif isinstance(ln, dict):
            label = ln.get("label")
            slope = float(ln.get("slope", 0))
            intercept_val = float(ln.get("intercept", 0))
        else:
            raise _animation_error(
                "E1467",
                f"malformed line add-spec: {ln!r}",
                hint="expected (label, slope, intercept), "
                "(label, {a, b, c}), or {label?, slope, intercept}",
            )
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
            raise _animation_error(
                "E1467",
                f"malformed segment add-spec: {seg!r}",
                hint="expected ((x1, y1), (x2, y2)) or {x1, y1, x2, y2}",
            )
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
        else:
            raise _animation_error(
                "E1467",
                f"malformed polygon add-spec: {poly!r}",
                hint="expected [(x, y), ...] or {points: [(x, y), ...]}",
            )

    def _add_region_internal(self, reg: Any) -> None:
        self._check_cap()
        if isinstance(reg, dict):
            pts = [(float(p[0]), float(p[1])) for p in reg.get("polygon", [])]
            fill = reg.get("fill", "rgba(0,114,178,0.2)")
            self.regions.append({"polygon": pts, "fill": fill})
        else:
            raise _animation_error(
                "E1467",
                f"malformed region add-spec: {reg!r}",
                hint="expected {polygon: [(x, y), ...], fill?: <color>}",
            )

    # ----- circle / arc / wedge add-spec parsing ---------------------------

    @staticmethod
    def _parse_circle_fields(spec: Any, kind: str) -> tuple[float, float, float]:
        """Parse ``{cx, cy, r}`` or ``(cx, cy, r)`` into floats. E1467 on any
        malformed shape or a negative radius."""
        try:
            if isinstance(spec, dict):
                cx, cy, r = float(spec["cx"]), float(spec["cy"]), float(spec["r"])
            elif isinstance(spec, (list, tuple)) and len(spec) >= 3:
                cx, cy, r = float(spec[0]), float(spec[1]), float(spec[2])
            else:
                raise ValueError("wrong spec shape")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise _animation_error(
                "E1467",
                f"malformed {kind} add-spec: {spec!r}",
                hint="expected {cx, cy, r} or (cx, cy, r)",
            ) from exc
        if r < 0:
            raise _animation_error(
                "E1467",
                f"malformed {kind} add-spec: negative radius {r!r}",
                hint="radius must be >= 0",
            )
        return cx, cy, r

    @staticmethod
    def _parse_arc_fields(
        spec: Any, kind: str
    ) -> tuple[float, float, float, float, float]:
        """Parse ``{cx, cy, r, a0, a1}`` or ``(cx, cy, r, a0, a1)`` into floats
        (angles in degrees, CCW). E1467 on any malformed shape / negative radius."""
        try:
            if isinstance(spec, dict):
                cx, cy, r = float(spec["cx"]), float(spec["cy"]), float(spec["r"])
                a0, a1 = float(spec["a0"]), float(spec["a1"])
            elif isinstance(spec, (list, tuple)) and len(spec) >= 5:
                cx, cy, r = float(spec[0]), float(spec[1]), float(spec[2])
                a0, a1 = float(spec[3]), float(spec[4])
            else:
                raise ValueError("wrong spec shape")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise _animation_error(
                "E1467",
                f"malformed {kind} add-spec: {spec!r}",
                hint="expected {cx, cy, r, a0, a1} or (cx, cy, r, a0, a1); "
                "angles in degrees, CCW",
            ) from exc
        if r < 0:
            raise _animation_error(
                "E1467",
                f"malformed {kind} add-spec: negative radius {r!r}",
                hint="radius must be >= 0",
            )
        return cx, cy, r, a0, a1

    def _warn_center_offscreen(
        self, cx: float, cy: float, kind: str, r: float | None = None
    ) -> None:
        """Emit hidden E1463 when a circle/arc/wedge center — or, for a shape
        with a radius, its extent ``center±r`` — falls outside the viewport
        (mirrors the point off-viewport warning, SF-2/RFC-002). Checking the
        radius too catches an oversized circle that clips at the SVG edge even
        though its centre is in range (bmad-aspect)."""
        center_out = not (
            self.xrange[0] <= cx <= self.xrange[1]
            and self.yrange[0] <= cy <= self.yrange[1]
        )
        extent_out = r is not None and not (
            self.xrange[0] <= cx - r and cx + r <= self.xrange[1]
            and self.yrange[0] <= cy - r and cy + r <= self.yrange[1]
        )
        if center_out or extent_out:
            what = "center" if center_out else "radius"
            logger.warning(
                "[E1463] %s %s (%.2f, %.2f) is outside viewport", kind, what, cx, cy
            )
            _emit_warning(
                self._ctx,
                "E1463",
                f"{kind} {what} ({cx:.2f}, {cy:.2f}) "
                + (f"r={r:.2f} " if extent_out and not center_out else "")
                + f"extends outside viewport "
                f"[{self.xrange[0]}, {self.xrange[1]}] x "
                f"[{self.yrange[0]}, {self.yrange[1]}]",
                primitive=self.name,
                severity="hidden",
            )

    def _add_circle_internal(self, spec: Any) -> None:
        self._check_cap()
        cx, cy, r = self._parse_circle_fields(spec, "circle")
        self._warn_center_offscreen(cx, cy, "circle", r)
        self.circles.append({"cx": cx, "cy": cy, "r": r})

    def _add_arc_internal(self, spec: Any) -> None:
        self._check_cap()
        cx, cy, r, a0, a1 = self._parse_arc_fields(spec, "arc")
        self._warn_center_offscreen(cx, cy, "arc", r)
        self.arcs.append({"cx": cx, "cy": cy, "r": r, "a0": a0, "a1": a1})

    def _add_wedge_internal(self, spec: Any) -> None:
        self._check_cap()
        cx, cy, r, a0, a1 = self._parse_arc_fields(spec, "wedge")
        self._warn_center_offscreen(cx, cy, "wedge", r)
        self.wedges.append({"cx": cx, "cy": cy, "r": r, "a0": a0, "a1": a1})

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
        if "add_circle" in params:
            self._add_circle_internal(params["add_circle"])
            return
        if "add_arc" in params:
            self._add_arc_internal(params["add_arc"])
            return
        if "add_wedge" in params:
            self._add_wedge_internal(params["add_wedge"])
            return
        # Dynamic removals (RFC-001 §4.3 — tombstone semantics)
        if "remove_point" in params:
            self._remove_point_internal(coerce_int(params["remove_point"], "E1437", detail=f"Plane2D remove_point index {params['remove_point']!r} is not an integer"))
            return
        if "remove_line" in params:
            self._remove_line_internal(coerce_int(params["remove_line"], "E1437", detail=f"Plane2D remove_line index {params['remove_line']!r} is not an integer"))
            return
        if "remove_segment" in params:
            self._remove_segment_internal(coerce_int(params["remove_segment"], "E1437", detail=f"Plane2D remove_segment index {params['remove_segment']!r} is not an integer"))
            return
        if "remove_polygon" in params:
            self._remove_polygon_internal(coerce_int(params["remove_polygon"], "E1437", detail=f"Plane2D remove_polygon index {params['remove_polygon']!r} is not an integer"))
            return
        if "remove_region" in params:
            self._remove_region_internal(coerce_int(params["remove_region"], "E1437", detail=f"Plane2D remove_region index {params['remove_region']!r} is not an integer"))
            return
        if "remove_circle" in params:
            self._remove_circle_internal(coerce_int(params["remove_circle"], "E1437", detail=f"Plane2D remove_circle index {params['remove_circle']!r} is not an integer"))
            return
        if "remove_arc" in params:
            self._remove_arc_internal(coerce_int(params["remove_arc"], "E1437", detail=f"Plane2D remove_arc index {params['remove_arc']!r} is not an integer"))
            return
        if "remove_wedge" in params:
            self._remove_wedge_internal(coerce_int(params["remove_wedge"], "E1437", detail=f"Plane2D remove_wedge index {params['remove_wedge']!r} is not an integer"))
            return
        # In-place moves (A4 — element glides, identity preserved).
        # These mutate an element's coordinates while keeping its index (and
        # therefore its ``data-target``) stable, so the differ sees the same
        # identity with new (x, y) and emits ``position_move`` — a glide — in
        # place of the add+remove pair a re-add would produce. See
        # investigations/gap-motion-identity-reorder.md §5.1–5.3.
        if "move_point" in params:
            self._move_point_internal(params["move_point"])
            return
        if "move_line" in params:
            self._move_line_internal(params["move_line"])
            return
        if "move_segment" in params:
            self._move_segment_internal(params["move_segment"])
            return
        # In-place rotations (census gap #2 — angular motion). Each computes a
        # rotated destination via the CCW rotation matrix about a pivot, then
        # mutates the element in place keeping its index — so it rides the same
        # ``position_move`` glide as ``move_*`` (no new motion kind). The glide
        # is the straight chord of the anchor's rotation arc; small per-step
        # angles keep chord ≈ arc and read as rotation. See
        # investigations/completeness-census-post-0.24.md gap #2.
        if "rotate_point" in params:
            self._rotate_point_internal(params["rotate_point"])
            return
        if "rotate_segment" in params:
            self._rotate_segment_internal(params["rotate_segment"])
            return
        if "rotate_line" in params:
            self._rotate_line_internal(params["rotate_line"])
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

    def _remove_circle_internal(self, idx: int) -> None:
        if not (0 <= idx < len(self.circles)):
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' has no circle[{idx}] "
                f"(valid: 0..{len(self.circles) - 1 if self.circles else -1})",
            )
        if self.circles[idx] is _TOMBSTONE:
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' circle[{idx}] already removed",
            )
        self.circles[idx] = _TOMBSTONE

    def _remove_arc_internal(self, idx: int) -> None:
        if not (0 <= idx < len(self.arcs)):
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' has no arc[{idx}] "
                f"(valid: 0..{len(self.arcs) - 1 if self.arcs else -1})",
            )
        if self.arcs[idx] is _TOMBSTONE:
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' arc[{idx}] already removed",
            )
        self.arcs[idx] = _TOMBSTONE

    def _remove_wedge_internal(self, idx: int) -> None:
        if not (0 <= idx < len(self.wedges)):
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' has no wedge[{idx}] "
                f"(valid: 0..{len(self.wedges) - 1 if self.wedges else -1})",
            )
        if self.wedges[idx] is _TOMBSTONE:
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' wedge[{idx}] already removed",
            )
        self.wedges[idx] = _TOMBSTONE

    # ----- internal move helpers (A4 — mutate-in-place, identity stable) ----

    def _require_living(
        self, elements: list[Any], idx: int, kind: str
    ) -> None:
        """Guard shared by every move op: E1437 on an out-of-range or already
        tombstoned index — identical semantics to the remove helpers so a move
        onto a dead slot fails the same way a re-remove does."""
        if not (0 <= idx < len(elements)):
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' has no {kind}[{idx}] "
                f"(valid: 0..{len(elements) - 1 if elements else -1})",
            )
        if elements[idx] is _TOMBSTONE:
            raise _animation_error(
                "E1437",
                f"Plane2D '{self.name}' {kind}[{idx}] already removed",
            )

    @staticmethod
    def _move_index(spec: Any, kind: str, verb: str = "move") -> int:
        """Extract the integer index ``i`` from a move/rotate-spec dict. E1467
        when the spec is not a dict, omits ``i``, or ``i`` is not an integer.
        ``verb`` names the op in the message (``"move"`` default, ``"rotate"``)."""
        if not isinstance(spec, dict) or "i" not in spec:
            raise _animation_error(
                "E1467",
                f"malformed {kind} {verb}-spec: {spec!r}",
                hint=f"expected {{i, ...}} with an integer index i",
            )
        try:
            return int(spec["i"])
        except (TypeError, ValueError) as exc:
            raise _animation_error(
                "E1467",
                f"malformed {kind} {verb}-spec: index {spec.get('i')!r} "
                f"is not an integer",
                hint="i must be an integer",
            ) from exc

    def _move_point_internal(self, spec: Any) -> None:
        idx = self._move_index(spec, "point")
        self._require_living(self.points, idx, "point")
        fields = [k for k in ("x", "y") if k in spec]
        if not fields:
            raise _animation_error(
                "E1467",
                f"malformed point move-spec: {spec!r}",
                hint="expected {i, x?, y?} with at least one of x, y",
            )
        # Replace the slot with a fresh dict (immutable-update): the index —
        # and thus data-target ``{name}.point[{idx}]`` — stays the same.
        new_pt = dict(self.points[idx])
        for k in fields:
            new_pt[k] = float(spec[k])
        self.points[idx] = new_pt

    def _move_line_internal(self, spec: Any) -> None:
        idx = self._move_index(spec, "line")
        self._require_living(self.lines, idx, "line")
        if "to_x" not in spec:
            raise _animation_error(
                "E1467",
                f"malformed line move-spec: {spec!r}",
                hint="expected {i, to_x} to slide a vertical sweep line to x=to_x",
            )
        ln = self.lines[idx]
        # A vertical line is stored as slope=inf, intercept=x (x = c, i.e. b=0);
        # to_x repositions that x. A sloped line (b!=0) has no single x to set.
        if not math.isinf(ln["slope"]):
            raise _animation_error(
                "E1467",
                f"cannot move line[{idx}] by to_x: line is not vertical "
                f"(slope={ln['slope']!r})",
                hint="to_x only repositions a vertical sweep line (x=c); author "
                "it vertical via (label, {a:1, b:0, c:x}), or use add/remove to "
                "reshape a sloped line",
            )
        new_ln = dict(ln)
        new_ln["intercept"] = float(spec["to_x"])
        self.lines[idx] = new_ln

    def _move_segment_internal(self, spec: Any) -> None:
        idx = self._move_index(spec, "segment")
        self._require_living(self.segments, idx, "segment")
        fields = [k for k in ("x1", "y1", "x2", "y2") if k in spec]
        if not fields:
            raise _animation_error(
                "E1467",
                f"malformed segment move-spec: {spec!r}",
                hint="expected {i, x1?, y1?, x2?, y2?} with at least one "
                "endpoint coordinate",
            )
        # Partial move: only the provided endpoint fields change.
        new_seg = dict(self.segments[idx])
        for k in fields:
            new_seg[k] = float(spec[k])
        self.segments[idx] = new_seg

    # ----- internal rotate helpers (angular motion, census gap #2) ----------

    @staticmethod
    def _rotate_spec(spec: dict[str, Any], kind: str) -> tuple[float, float, float]:
        """Extract ``(by_degrees, cx, cy)`` from a rotate-spec dict. The caller
        pulls ``i`` first via :meth:`_move_index`. E1467 when ``by`` is missing
        or non-numeric, or ``about`` is not a numeric ``(cx, cy)`` pair
        (``about`` defaults to the origin)."""
        if "by" not in spec:
            raise _animation_error(
                "E1467",
                f"malformed {kind} rotate-spec: {spec!r}",
                hint="expected {i, by, about?} with by in degrees (CCW)",
            )
        try:
            by = float(spec["by"])
        except (TypeError, ValueError) as exc:
            raise _animation_error(
                "E1467",
                f"malformed {kind} rotate-spec: by {spec.get('by')!r} "
                f"is not a number",
                hint="by must be a number (degrees, CCW)",
            ) from exc
        about = spec.get("about", (0.0, 0.0))
        try:
            if not isinstance(about, (list, tuple)) or len(about) != 2:
                raise ValueError("about must be a (cx, cy) pair")
            cx, cy = float(about[0]), float(about[1])
        except (TypeError, ValueError, IndexError) as exc:
            raise _animation_error(
                "E1467",
                f"malformed {kind} rotate-spec: about {spec.get('about')!r} "
                f"is not a (cx, cy) pair",
                hint="about must be a numeric (cx, cy) pivot; omit for the origin",
            ) from exc
        return by, cx, cy

    @staticmethod
    def _rotate_xy(
        x: float, y: float, cx: float, cy: float, by_deg: float
    ) -> tuple[float, float]:
        """Rotate ``(x, y)`` by ``by_deg`` degrees CCW about ``(cx, cy)``.

        Math convention (Y up), so a positive angle is counter-clockwise — the
        same sense as the arc/wedge sweep. Standard rotation matrix."""
        r = math.radians(by_deg)
        cos_r, sin_r = math.cos(r), math.sin(r)
        dx, dy = x - cx, y - cy
        return (cx + dx * cos_r - dy * sin_r, cy + dx * sin_r + dy * cos_r)

    def _rotate_point_internal(self, spec: Any) -> None:
        idx = self._move_index(spec, "point", verb="rotate")
        self._require_living(self.points, idx, "point")
        by, cx, cy = self._rotate_spec(spec, "point")
        pt = self.points[idx]
        nx, ny = self._rotate_xy(pt["x"], pt["y"], cx, cy, by)
        new_pt = dict(pt)
        new_pt["x"], new_pt["y"] = nx, ny
        self.points[idx] = new_pt

    def _rotate_segment_internal(self, spec: Any) -> None:
        idx = self._move_index(spec, "segment", verb="rotate")
        self._require_living(self.segments, idx, "segment")
        by, cx, cy = self._rotate_spec(spec, "segment")
        seg = self.segments[idx]
        x1, y1 = self._rotate_xy(seg["x1"], seg["y1"], cx, cy, by)
        x2, y2 = self._rotate_xy(seg["x2"], seg["y2"], cx, cy, by)
        new_seg = dict(seg)
        new_seg["x1"], new_seg["y1"] = x1, y1
        new_seg["x2"], new_seg["y2"] = x2, y2
        self.segments[idx] = new_seg

    def _rotate_line_internal(self, spec: Any) -> None:
        idx = self._move_index(spec, "line", verb="rotate")
        self._require_living(self.lines, idx, "line")
        by, cx, cy = self._rotate_spec(spec, "line")
        ln = self.lines[idx]
        # Sample two points on the current line, rotate both about the pivot,
        # then refit slope/intercept — vertical (b=0) is stored as slope=inf,
        # intercept=x, matching the add/emit convention.
        slope = ln["slope"]
        intercept_val = ln["intercept"]
        if math.isinf(slope):
            p1, p2 = (intercept_val, 0.0), (intercept_val, 1.0)
        else:
            p1, p2 = (0.0, intercept_val), (1.0, slope + intercept_val)
        q1x, q1y = self._rotate_xy(p1[0], p1[1], cx, cy, by)
        q2x, q2y = self._rotate_xy(p2[0], p2[1], cx, cy, by)
        new_ln = dict(ln)
        if abs(q2x - q1x) < 1e-9:
            new_ln["slope"] = float("inf")
            new_ln["intercept"] = q1x
        else:
            m = (q2y - q1y) / (q2x - q1x)
            new_ln["slope"] = m
            new_ln["intercept"] = q1y - m * q1x
        self.lines[idx] = new_ln

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
        for i, c in enumerate(self.circles):
            if c is not _TOMBSTONE:
                parts.append(f"circle[{i}]")
        for i, a in enumerate(self.arcs):
            if a is not _TOMBSTONE:
                parts.append(f"arc[{i}]")
        for i, w in enumerate(self.wedges):
            if w is not _TOMBSTONE:
                parts.append(f"wedge[{i}]")
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

        m = _CIRCLE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return idx < len(self.circles) and self.circles[idx] is not _TOMBSTONE

        m = _ARC_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return idx < len(self.arcs) and self.arcs[idx] is not _TOMBSTONE

        m = _WEDGE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return idx < len(self.wedges) and self.wedges[idx] is not _TOMBSTONE

        return False

    def renders_value(self, suffix: str) -> bool:
        """Plane2D geometric parts have no per-element value display slot.

        Every part is pure geometry — a point is a ``<circle>`` (labels live in
        a separate ``scriba-plane-labels`` group), and line/segment/polygon/
        region/circle/arc/wedge are stroke/fill paths. ``emit_svg`` never reads
        ``get_value``, so a ``value=`` on any of them vanishes from the render
        while the differ still bakes a ``value_change`` the runtime stamps then
        the fs-snap reverts (a no-op flip-back). Reject an *in-range* part
        ``value=`` at build time via the shared E1105 gate; an *out-of-range*
        part is a separate invalid-selector soft-drop (E1115) and never reaches
        this check because its value-record is stripped pre-gate. Non-part
        targets (``all``/bare shape) keep the base default ``True``.
        """
        return not _VALUE_LESS_PART_RE.match(suffix)

    # ----- annotation point resolution -------------------------------------

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG ``(x, y)`` for an annotation selector.

        Supported selector forms (``P`` is the shape name):
        - ``P.point[i]``   — center of point *i*
        - ``P.line[i]``    — midpoint of the visible line segment
        - ``P.segment[i]`` — midpoint of the segment
        - ``P.polygon[i]`` — centroid of the polygon
        - ``P.circle[i]``  — center of the circle
        - ``P.arc[i]``     — midpoint of the arc (mid-angle on the rim)
        - ``P.wedge[i]``   — sector interior along the mid-angle (r*0.5)

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

        # --- circle (center) ---
        m = _CIRCLE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if idx < len(self.circles) and self.circles[idx] is not _TOMBSTONE:
                c = self.circles[idx]
                return self.math_to_svg(c["cx"], c["cy"])
            return None

        # --- arc (midpoint of the arc, on the rim) ---
        m = _ARC_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if idx < len(self.arcs) and self.arcs[idx] is not _TOMBSTONE:
                a = self.arcs[idx]
                mid = math.radians(a["a0"] + self._arc_sweep(a["a0"], a["a1"]) / 2.0)
                return self.math_to_svg(
                    a["cx"] + a["r"] * math.cos(mid),
                    a["cy"] + a["r"] * math.sin(mid),
                )
            return None

        # --- wedge (sector interior along the mid-angle) ---
        m = _WEDGE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if idx < len(self.wedges) and self.wedges[idx] is not _TOMBSTONE:
                w = self.wedges[idx]
                mid = math.radians(w["a0"] + self._arc_sweep(w["a0"], w["a1"]) / 2.0)
                rr = w["r"] * 0.5
                return self.math_to_svg(
                    w["cx"] + rr * math.cos(mid),
                    w["cy"] + rr * math.sin(mid),
                )
            return None

        return None

    # ----- position injection (A4 — position_move substrate) ---------------

    def _line_anchor_math(self, ln: dict[str, Any]) -> tuple[float, float] | None:
        """Math-space anchor for a line: the midpoint of its visible span.

        Mirrors the ``line[i]`` branch of :meth:`resolve_annotation_point`
        but stays in math coordinates (no ``math_to_svg``). Returns ``None``
        when the line does not intersect the viewport (nothing to anchor)."""
        slope = ln["slope"]
        intercept_val = ln["intercept"]
        if math.isinf(slope):
            x_val = intercept_val
            if self.xrange[0] <= x_val <= self.xrange[1]:
                return (x_val, (self.yrange[0] + self.yrange[1]) / 2)
            return None
        result = clip_line_to_viewport(
            slope, intercept_val, self.xrange, self.yrange,
        )
        if result is None:
            return None
        (x1, y1), (x2, y2) = result
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def get_node_positions(self) -> dict[str, tuple[float, float]]:
        """Return ``{data_target: (x, y)}`` in MATH coordinates for every living
        movable element (points, lines, segments, circles).

        Duck-typed by ``_inject_tree_positions`` (``hasattr`` gate) which copies
        these into ``frame.shape_states``; the differ then emits ``position_move``
        whenever an element's anchor moved between frames, so an in-place
        ``move_*`` mutation glides instead of add+remove. Tombstoned and
        off-viewport elements are omitted (no live anchor to move).

        Coordinates are MATH, not ``math_to_svg`` output: each ``<g data-target>``
        lives INSIDE the ``scale(sx, sy)`` content group (see :meth:`emit_svg`),
        so the runtime's ``translate(Δ)`` on that element is interpreted in the
        scaled local frame — a math-unit Δ yields Δ·sx px on screen and the
        negative ``sy`` supplies the Y-flip. (§5.3; verified by browser probe.)
        The invariant ``math_to_svg(anchor) == resolve_annotation_point(target)``
        holds for every family below.
        """
        result: dict[str, tuple[float, float]] = {}
        for i, pt in enumerate(self.points):
            if pt is _TOMBSTONE:
                continue
            result[f"{self.name}.point[{i}]"] = (pt["x"], pt["y"])
        for i, ln in enumerate(self.lines):
            if ln is _TOMBSTONE:
                continue
            anchor = self._line_anchor_math(ln)
            if anchor is not None:
                result[f"{self.name}.line[{i}]"] = anchor
        for i, seg in enumerate(self.segments):
            if seg is _TOMBSTONE:
                continue
            result[f"{self.name}.segment[{i}]"] = (
                (seg["x1"] + seg["x2"]) / 2,
                (seg["y1"] + seg["y2"]) / 2,
            )
        for i, c in enumerate(self.circles):
            if c is _TOMBSTONE:
                continue
            result[f"{self.name}.circle[{i}]"] = (c["cx"], c["cy"])
        return result

    # ----- bounding box ----------------------------------------------------

    def bounding_box(self) -> BoundingBox:
        arrow_above = self._reserved_arrow_above()
        pos_below = self.annotation_below_overhang(float(self.height))
        return BoundingBox(
            x=0,
            y=0,
            width=self.width,
            height=self.height + arrow_above + pos_below,
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
        arrow_above = self._reserved_arrow_above()

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
        parts.append(self._emit_wedges())
        parts.append(self._emit_polygons())
        parts.append(self._emit_circles())
        parts.append(self._emit_arcs())
        parts.append(self._emit_lines())
        parts.append(self._emit_segments())
        parts.append(self._emit_points())
        parts.append("</g>")

        # Layer 3: text labels (SVG coordinates, outside transform)
        parts.append(self._emit_labels(render_inline_tex=render_inline_tex))

        # Layer 4: annotations (SVG coordinates, outside transform).
        # One dispatcher call covers every annotation kind (FP-6): it splits
        # arrow_from / arrow=true / position-only internally, shares one
        # placement registry, and threads the obstacle sets — and it is the
        # same path _measure_emit replays, so measured == painted.
        if effective_anns:
            self.emit_annotation_arrows(
                parts,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
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

    # ----- Circle / arc / wedge rendering (inside transform group) ---------
    #
    # Aspect decision (case file §4.3): the circle is emitted as a ``<circle>``
    # *inside* the math->SVG transform group, so ``scale(sx, sy)`` maps a
    # math-unit radius to the geometrically-honest ellipse rx=r*|sx|, ry=r*|sy|.
    # When ``aspect="equal"`` (the default) |sx|==|sy| so it is a true circle;
    # when ``aspect="auto"`` it is the honest ellipse (the locus of math points
    # at distance r really is an ellipse in pixel space).  ``non-scaling-stroke``
    # keeps the outline width uniform under the non-uniform scale.  Arc and
    # wedge paths follow the same convention; their sweep-flag is 1 because the
    # CCW math arc is authored in the pre-flip local frame and the Y-flip in the
    # transform maps it to CCW on screen.

    @staticmethod
    def _arc_sweep(a0: float, a1: float) -> float:
        """CCW angular sweep from *a0* to *a1* in degrees, normalized to
        ``(0, 360]``.  ``a1 == a0`` is read as a full turn (360)."""
        delta = a1 - a0
        while delta <= 0:
            delta += 360.0
        while delta > 360.0:
            delta -= 360.0
        return delta

    @classmethod
    def _arc_path_d(
        cls,
        cx: float,
        cy: float,
        r: float,
        a0: float,
        a1: float,
        *,
        wedge: bool,
    ) -> str:
        """Build the SVG path ``d`` for an arc (``wedge=False``) or a filled
        sector (``wedge=True``) in math coordinates.  Angles in degrees, CCW."""
        a0r = math.radians(a0)
        a1r = math.radians(a1)
        x0 = cx + r * math.cos(a0r)
        y0 = cy + r * math.sin(a0r)
        x1 = cx + r * math.cos(a1r)
        y1 = cy + r * math.sin(a1r)
        large = 1 if cls._arc_sweep(a0, a1) > 180.0 else 0
        sweep = 1  # CCW in the local (pre-Y-flip) frame; see class-level note
        if wedge:
            return (
                f"M {cx:.4f} {cy:.4f} L {x0:.4f} {y0:.4f} "
                f"A {r:.4f} {r:.4f} 0 {large} {sweep} {x1:.4f} {y1:.4f} Z"
            )
        return (
            f"M {x0:.4f} {y0:.4f} "
            f"A {r:.4f} {r:.4f} 0 {large} {sweep} {x1:.4f} {y1:.4f}"
        )

    def _emit_circles(self) -> str:
        parts: list[str] = []
        hl_suffixes = getattr(self, "_highlighted", set())
        for i, c in enumerate(self.circles):
            if c is _TOMBSTONE:
                continue
            suffix = f"circle[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            if state == "hidden":
                continue
            colors = svg_style_attrs(state)
            is_hl = suffix in hl_suffixes
            effective_state = "highlight" if (is_hl and state == "idle") else state
            sw = "1.5" if state == "idle" else "2"
            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
                f'class="scriba-plane-circle scriba-state-{effective_state}">'
                f'<circle cx="{c["cx"]}" cy="{c["cy"]}" r="{c["r"]}" '
                f'fill="none" stroke="{colors["stroke"]}" stroke-width="{sw}" '
                f'vector-effect="non-scaling-stroke"/>'
                f'</g>'
            )
        return "".join(parts)

    def _emit_arcs(self) -> str:
        parts: list[str] = []
        hl_suffixes = getattr(self, "_highlighted", set())
        for i, a in enumerate(self.arcs):
            if a is _TOMBSTONE:
                continue
            suffix = f"arc[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            if state == "hidden":
                continue
            colors = svg_style_attrs(state)
            is_hl = suffix in hl_suffixes
            effective_state = "highlight" if (is_hl and state == "idle") else state
            sw = "1.5" if state == "idle" else "2"
            d = self._arc_path_d(a["cx"], a["cy"], a["r"], a["a0"], a["a1"], wedge=False)
            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
                f'class="scriba-plane-arc scriba-state-{effective_state}">'
                f'<path d="{d}" fill="none" stroke="{colors["stroke"]}" '
                f'stroke-width="{sw}" vector-effect="non-scaling-stroke"/>'
                f'</g>'
            )
        return "".join(parts)

    def _emit_wedges(self) -> str:
        parts: list[str] = []
        hl_suffixes = getattr(self, "_highlighted", set())
        for i, w in enumerate(self.wedges):
            if w is _TOMBSTONE:
                continue
            suffix = f"wedge[{i}]"
            target = f"{self.name}.{suffix}"
            state = self.get_state(suffix)
            if state == "hidden":
                continue
            colors = svg_style_attrs(state)
            is_hl = suffix in hl_suffixes
            effective_state = "highlight" if (is_hl and state == "idle") else state
            sw = "1.5" if state == "idle" else "2"
            d = self._arc_path_d(w["cx"], w["cy"], w["r"], w["a0"], w["a1"], wedge=True)
            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
                f'class="scriba-plane-wedge scriba-state-{effective_state}">'
                f'<path d="{d}" fill="rgba(0,114,178,0.15)" '
                f'stroke="{colors["stroke"]}" stroke-width="{sw}" '
                f'vector-effect="non-scaling-stroke"/>'
                f'</g>'
            )
        return "".join(parts)

    # ----- Label layer (SVG coordinates, outside transform) ----------------

    def register_decorations(self) -> "list[dict[str, Any]]":
        """One placement registry for ALL content labels (FP-2).

        Point labels and line labels used two isolated registries — point
        labels had none at all (bare ``<text>``, no nudge, no clamp) and
        printed straight through line labels sharing the corner. Every
        content label now joins one list in deterministic order (points by
        index, then lines by index) with the same downward nudge and
        viewBox clamp.

        Pure function of primitive state: reused by ``_emit_labels`` for
        painting and by ``resolve_self_content_rects`` for the annotation
        scorer, so the emit and measure paths see identical boxes.
        """
        _LINE_LABEL_H = 14
        _LINE_LABEL_PAD = 10
        _LINE_PILL_PAD_X = _SVG_LABEL_PILL_PAD_X
        _LINE_PILL_PAD_Y = _SVG_LABEL_PILL_PAD_Y
        _LINE_NUDGE_STEP = 16
        _LINE_MAX_NUDGE = 4

        placed: list[_LabelPlacement] = []
        records: list[dict[str, Any]] = []
        vb_w = self.width
        vb_h = self.height

        def _settle(cx: float, cy: float, w: float, h: float) -> _LabelPlacement:
            """Shared nudge-down + viewBox clamp for every content label."""
            cand = _LabelPlacement(x=cx, y=cy, width=w, height=h)
            for _attempt in range(_LINE_MAX_NUDGE):
                if not any(cand.overlaps(p) for p in placed):
                    break
                cy += _LINE_NUDGE_STEP
                cand = _LabelPlacement(x=cx, y=cy, width=w, height=h)
            half_w = w / 2
            cx = max(_PAD + half_w, min(cx, vb_w - _PAD - half_w))
            cy = max(12.0, min(cy, vb_h - 4.0))
            cand = _LabelPlacement(x=cx, y=cy, width=w, height=h)
            placed.append(cand)
            return cand

        for i, pt in enumerate(self.points):
            if pt is _TOMBSTONE:
                continue
            if self.get_state(f"point[{i}]") == "hidden":
                continue
            label_text = pt.get("label")
            if not label_text and self.show_coords:
                label_text = f"({pt['x']:.6g}, {pt['y']:.6g})"
            if not label_text:
                continue
            sx, sy = self.math_to_svg(pt["x"], pt["y"])
            w = float(measure_label_line(str(label_text), _TICK_FONT_SIZE) + 12)
            records.append({
                "kind": "point",
                "text": str(label_text),
                "placement": _settle(
                    sx + _LABEL_OFFSET + w / 2, sy - _LABEL_OFFSET, w, 16.0
                ),
                "pill_w": None,
                "pill_h": None,
            })

        for i, ln in enumerate(self.lines):
            if ln is _TOMBSTONE:
                continue
            if self.get_state(f"line[{i}]") == "hidden":
                continue
            if not ln.get("label"):
                continue
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

            # canonical width estimator (B-1): the hand-rolled len*7
            # under-sized CJK labels (each CJK glyph advances ~2x a Latin one)
            est_w = measure_label_line(label_text, _TICK_FONT_SIZE) + _LINE_LABEL_PAD
            records.append({
                "kind": "line",
                "text": label_text,
                "placement": _settle(
                    label_x + _LABEL_OFFSET, label_y - _LABEL_OFFSET,
                    float(est_w), float(_LINE_LABEL_H),
                ),
                "pill_w": float(est_w + _LINE_PILL_PAD_X * 2),
                "pill_h": float(_LINE_LABEL_H + _LINE_PILL_PAD_Y * 2),
            })

        return records

    def resolve_self_content_rects(self) -> "list[BoundingBox]":
        """Content-label boxes as scorer obstacles (corner-based, same frame
        as ``resolve_annotation_point``) — annotation pills avoid point and
        line labels on both the emit and measure paths."""
        return [
            BoundingBox(
                x=r["placement"].x - r["placement"].width / 2,
                y=r["placement"].y - r["placement"].height / 2,
                width=r["placement"].width,
                height=r["placement"].height,
            )
            for r in self.register_decorations()
        ]

    @allow_forbidden_pattern(
        "FP-4",
        reason=(
            "paints already-settled placements; the viewBox clamp lives in "
            "register_decorations._settle, shared by every content label"
        ),
        issue="investigations/fp2-isolated-registries.md",
    )
    def _emit_labels(self, *, render_inline_tex: "Callable[[str], str] | None" = None) -> str:
        parts: list[str] = ['<g class="scriba-plane-labels">']

        # Tick labels on axes
        if self.axes:
            parts.append(self._emit_tick_labels())

        _LINE_PILL_R = _SVG_LABEL_PILL_RADIUS

        for rec in self.register_decorations():
            placement = rec["placement"]
            if rec["kind"] == "point":
                parts.append(
                    _render_svg_text(
                        rec["text"],
                        round(placement.x),
                        round(placement.y),
                        fill=THEME["fg"],
                        css_class="scriba-plane-label-text",
                        font_size=str(_TICK_FONT_SIZE),
                        text_anchor="middle",
                        fo_width=int(placement.width),
                        fo_height=16,
                        render_inline_tex=render_inline_tex,
                        clip_overflow=False,
                    )
                )
                continue
            pill_w, pill_h = rec["pill_w"], rec["pill_h"]
            pill_rx = placement.x - pill_w / 2
            pill_ry = placement.y - pill_h / 2
            parts.append(
                f'<rect x="{pill_rx:.1f}" y="{pill_ry:.1f}" '
                f'width="{pill_w:g}" height="{pill_h:g}" '
                f'rx="{_LINE_PILL_R}" fill="white" '
                f'fill-opacity="0.85" class="scriba-plane-label-pill"/>'
            )
            parts.append(
                _render_svg_text(
                    rec["text"],
                    round(placement.x),
                    round(placement.y),
                    fill=THEME["fg"],
                    css_class="scriba-plane-label-text",
                    font_size=str(_TICK_FONT_SIZE),
                    text_anchor="middle",
                    fo_width=int(pill_w),
                    fo_height=int(pill_h),
                    render_inline_tex=render_inline_tex,
                    clip_overflow=False,
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
                f'<text class="scriba-plane-tick-label" '
                f'x="{sx:.2f}" y="{sy + _TICK_FONT_SIZE + 2:.2f}" '
                f'text-anchor="middle" '
                f'style="font-size:{_TICK_FONT_SIZE}px" '
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
                f'<text class="scriba-plane-tick-label" '
                f'x="{sx - _LABEL_OFFSET:.2f}" y="{sy + 3:.2f}" '
                f'text-anchor="end" '
                f'style="font-size:{_TICK_FONT_SIZE}px" '
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
