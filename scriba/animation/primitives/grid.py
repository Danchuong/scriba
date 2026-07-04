"""Grid primitive -- a 2D rows x cols matrix of uniform cells.

See ``docs/spec/primitives.md`` section 4 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives._text_metrics import measure_value_text
from scriba.animation.primitives.base import (
    _CAPTION_CLEAR_GAP,
    CellMetrics,
    ALL_RE,
    CELL_2D_RE,
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    BoundingBox,
    PrimitiveBase,
    _inset_rect_attrs,
    _render_svg_text,
    register_primitive,
    state_class,
    svg_style_attrs,
    _CELL_HORIZONTAL_PADDING,
)


from scriba.animation.primitives._protocol import register_primitive as _protocol_register

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
            raise _animation_error(
                "E1412",
                detail=(
                    f"Grid 'data' flattened length ({len(flat)}) "
                    f"does not match rows*cols ({expected}); "
                    "valid: 2D list with rows rows of cols items each"
                ),
            )
        return flat

    # Already flat
    flat_list = list(raw)
    expected = rows * cols
    if len(flat_list) != expected:
        raise _animation_error(
            "E1412",
            detail=(
                f"Grid 'data' length ({len(flat_list)}) does not match "
                f"rows*cols ({expected}); valid: flat list of rows*cols items"
            ),
        )
    return flat_list


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

# Full-qualified selectors (with shape name prefix) — canonical from base.py.
_CELL_2D_RE = CELL_2D_RE
_ALL_RE = ALL_RE

# Suffix-only regex (no shape name prefix) — local, no base.py equivalent.
_SUFFIX_CELL_2D_RE = re.compile(r"^cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$")

_SUFFIX_BLOCK_RE = re.compile(
    r"^block\[(?P<r0>\d+):(?P<r1>\d+)\]\[(?P<c0>\d+):(?P<c1>\d+)\]$"
)
_BLOCK_RE = re.compile(
    r"^(?P<name>[^.]+)\.block\[(?P<r0>\d+):(?P<r1>\d+)\]"
    r"\[(?P<c0>\d+):(?P<c1>\d+)\]$"
)



# ---------------------------------------------------------------------------
# GridPrimitive
# ---------------------------------------------------------------------------


@register_primitive("Grid")
@_protocol_register
class GridPrimitive(PrimitiveBase):
    """A 2D rows x cols matrix of uniform cells.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type = "grid"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "cell[{r}][{c}]": "cell by row,col",
        "all": "all cells",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "rows",
        "cols",
        "data",
        "label",
    })

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)
        rows = self.params.get("rows")
        cols = self.params.get("cols")

        if rows is None or cols is None:
            raise _animation_error(
                "E1410",
                detail="Grid requires both 'rows' and 'cols' parameters",
                hint="example: \\shape{g}{Grid}{rows=4, cols=5}",
            )

        rows = int(rows)
        cols = int(cols)
        if rows < 1:
            raise _animation_error(
                "E1411",
                detail=f"Grid rows {rows} is out of range; valid: 1..500",
            )
        if cols < 1:
            raise _animation_error(
                "E1411",
                detail=f"Grid cols {cols} is out of range; valid: 1..500",
            )
        if rows > 500:
            raise _animation_error(
                "E1411",
                detail=f"Grid rows {rows} exceeds maximum; valid: 1..500",
            )
        if cols > 500:
            raise _animation_error(
                "E1411",
                detail=f"Grid cols {cols} exceeds maximum; valid: 1..500",
            )

        raw_data: Any = self.params.get("data", [])
        data: list[Any] = _flatten_2d(raw_data, rows, cols)

        self.rows: int = rows
        self.cols: int = cols
        self.data: list[Any] = data

        # Content-based cell width (Queue/Array monotonic pattern; see
        # DPTable twin + investigations/fixedbox-content-sizing.md).
        max_content_w = max(
            (measure_value_text(str(v), 14) for v in self.data),
            default=0,
        )
        self._cell_width: int = max(
            CELL_WIDTH, max_content_w + _CELL_HORIZONTAL_PADDING
        )
        self.label: str | None = self.params.get("label")
        self._arrow_layout = "2d"

    # -- PrimitiveBase interface --------------------------------------------

    def set_value(self, suffix: str, value: str) -> None:
        super().set_value(suffix, value)
        needed = measure_value_text(str(value), 14) + _CELL_HORIZONTAL_PADDING
        if needed > self._cell_width:
            self._cell_width = needed

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
        b = _SUFFIX_BLOCK_RE.match(suffix)
        if b:
            r0, r1 = int(b.group("r0")), int(b.group("r1"))
            c0, c1 = int(b.group("c0")), int(b.group("c1"))
            # inclusive, non-reversed, in-bounds — mirrors range[lo:hi]
            return (
                r0 <= r1 < self.rows and c0 <= c1 < self.cols
            )

        return suffix == "all"

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG (x, y) center for an annotation selector.

        Supports ``"<name>.cell[<row>][<col>]"`` selectors.
        Returns the top-center of the cell (y=top edge) so arrows curve above.
        """
        m = _CELL_2D_RE.match(selector)
        if m and m.group("name") == self.name:
            r = int(m.group("row"))
            c = int(m.group("col"))
            if 0 <= r < self.rows and 0 <= c < self.cols:
                x = c * (self._cell_width + CELL_GAP) + self._cell_width // 2
                y = r * (CELL_HEIGHT + CELL_GAP) + CELL_HEIGHT // 2  # cell center
                return (float(x), float(y))
        b = _BLOCK_RE.match(selector)
        if b and b.group("name") == self.name:
            box = self._block_box(b)
            if box is not None:
                return (box.x + box.width / 2.0, box.y + box.height / 2.0)
        return None

    def _block_box(self, m: "re.Match[str]") -> "BoundingBox | None":
        """Union AABB of an inclusive ``block[r0:r1][c0:c1]`` (corner-based,
        same convention as resolve_self_content_rects). Bounds re-checked so
        an un-validated annotate target degrades to None (soft-drop),
        mirroring range."""
        r0, r1 = int(m.group("r0")), int(m.group("r1"))
        c0, c1 = int(m.group("c0")), int(m.group("c1"))
        if not (r0 <= r1 < self.rows and c0 <= c1 < self.cols):
            return None
        x = c0 * (self._cell_width + CELL_GAP)
        y = r0 * (CELL_HEIGHT + CELL_GAP)
        w = (c1 - c0 + 1) * self._cell_width + (c1 - c0) * CELL_GAP
        h = (r1 - r0 + 1) * CELL_HEIGHT + (r1 - r0) * CELL_GAP
        return BoundingBox(x=float(x), y=float(y), width=float(w), height=float(h))

    def resolve_self_content_rects(self) -> "list[BoundingBox]":
        """Every cell box — pills should not sit on top of the grid body."""
        return [
            BoundingBox(
                x=float(c * (self._cell_width + CELL_GAP)),
                y=float(r * (CELL_HEIGHT + CELL_GAP)),
                width=float(self._cell_width),
                height=float(CELL_HEIGHT),
            )
            for r in range(self.rows)
            for c in range(self.cols)
        ]

    def _annotation_cell_metrics(self) -> "CellMetrics":
        """Grid-aware flow context — single source for render AND measurement."""
        return CellMetrics(
            cell_width=float(self._cell_width),
            cell_height=float(CELL_HEIGHT),
            grid_cols=int(self.cols),
            grid_rows=int(self.rows),
            origin_x=0.0,
            origin_y=0.0,
        )

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit below the whole grid (callout lane),
        clear of the cells, with a leader line back to the labelled cell."""
        return float(self._grid_dimensions()[1])

    def resolve_annotation_box(self, selector: str) -> "BoundingBox | None":
        """Cell AABB (Layer C) so a below-pill gets a leader line and the placer
        treats the labelled cell as a blocker. Scoped to below-pill targets so a
        wide above/left/right pill on a cell never spuriously trips the spanning
        leader."""
        b = _BLOCK_RE.match(selector)
        if b and b.group("name") == self.name:
            # block boxes feed the placer/bracket regardless of position,
            # exactly like 1-D range boxes (see _target_has_below_pill note)
            return self._block_box(b)
        if not self._target_has_below_pill(selector):
            return None
        m = _CELL_2D_RE.match(selector)
        if m and m.group("name") == self.name:
            r = int(m.group("row"))
            c = int(m.group("col"))
            if 0 <= r < self.rows and 0 <= c < self.cols:
                x = c * (self._cell_width + CELL_GAP)
                y = r * (CELL_HEIGHT + CELL_GAP)
                return BoundingBox(
                    x=int(x), y=int(y), width=int(self._cell_width), height=int(CELL_HEIGHT)
                )
        return None

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the grid."""
        effective_anns = self._annotations

        # Compute vertical space needed above cells for arrow curves
        arrow_above = self._reserved_arrow_above()
        # #1: shift content right to make room for position=left pills (0 when
        # none → "translate(0, …)", byte-identical to the pre-#1 output).
        left_pad, _right = self._h_label_pad()

        lines: list[str] = [
            f'<g data-primitive="grid" data-shape="{self.name}">'
        ]

        # Shift content down (arrows) and right (left pills) into valid space.
        if arrow_above > 0 or left_pad > 0:
            lines.append(f'  <g transform="translate({left_pad}, {arrow_above})">')


        for r in range(self.rows):
            for c in range(self.cols):
                target = f"{self.name}.cell[{r}][{c}]"
                suffix = f"cell[{r}][{c}]"

                value = self.get_value(suffix)
                if value is None:
                    flat_idx = r * self.cols + c
                    value = self.data[flat_idx]
                effective_state = self.resolve_effective_state(suffix)

                css = state_class(effective_state)
                colors = svg_style_attrs(effective_state)

                x = int(c * (self._cell_width + CELL_GAP))
                y = int(r * (CELL_HEIGHT + CELL_GAP))

                lines.append(
                    f'  <g data-target="{target}" class="{css}">'
                )
                rect_attrs = _inset_rect_attrs(
                    x, y, self._cell_width, CELL_HEIGHT
                )
                lines.append(
                    f'    <rect x="{rect_attrs["x"]}" y="{rect_attrs["y"]}" '
                    f'width="{rect_attrs["width"]}" '
                    f'height="{rect_attrs["height"]}"/>'
                )
                text_x = int(x + self._cell_width // 2)
                text_y = int(y + CELL_HEIGHT // 2)
                lines.append(
                    "    "
                    + _render_svg_text(
                        value,
                        text_x,
                        text_y,
                        fill=colors["text"],
                        font_size="14",
                        fo_width=self._cell_width,
                        fo_height=CELL_HEIGHT,
                        render_inline_tex=render_inline_tex,
                    )
                )
                lines.append("  </g>")

        # Caption below the grid, beneath the below-pill lane (Layer A/C). It is
        # drawn inside the left_pad translate group, so it centers on the grid
        # core width, not the (possibly left/right-padded) bbox width.
        if self.label is not None:
            tw, th = self._grid_dimensions()
            self._emit_caption(
                lines,
                content_width=tw,
                footprint_width=max(tw, self._caption_block_width(tw)),
                top_y=int(th + self._below_lane_height() + _CAPTION_CLEAR_GAP),
                render_inline_tex=render_inline_tex,
            )

        # Arrow + position-pill annotations
        # R-37 traces: above the cell bodies (a filled cell would
        # swallow an under-stroke) but below pills/arrows; digits
        # stay legible via the global paint-order halo
        self.emit_traces_under(lines)
        # R-38 binding carets ride the same decoration band as traces.
        self.emit_cursors_under(lines)

        if effective_anns:
            self.emit_annotation_arrows(
                lines,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
                cell_metrics=self._annotation_cell_metrics(),
            )

        # Close the translate group if we opened one
        if arrow_above > 0 or left_pad > 0:
            lines.append("  </g>")

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> BoundingBox:
        """Return the bounding box of this grid."""
        tw, th = self._grid_dimensions()
        # Layer A: fold the (wrapped) caption width into the footprint.
        core_w = max(tw, self._caption_block_width(tw))
        # Layer C: below-pill callout lane sits between the grid and the caption.
        h = th + self._below_lane_height() + self._caption_block_height(tw)
        if self.label is not None:
            h += _CAPTION_CLEAR_GAP
        # R-38: keep a below-cell binding caret inside the box (0 when none).
        h = max(h, self._cursor_extent_below())
        arrow_above = self._reserved_arrow_above()
        h += arrow_above
        # #1: reserve horizontal room for position=left/right pills. Both pads
        # are 0 (int) without left/right pills, so the box stays byte-stable.
        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)
        return BoundingBox(x=0, y=0, width=w, height=h)

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []

    # -- internal -----------------------------------------------------------

    def _grid_dimensions(self) -> tuple[int, int]:
        """Return ``(total_width, total_height)`` of the cell grid."""
        if self.cols == 0 or self.rows == 0:
            return (0, 0)
        w = self.cols * self._cell_width + (self.cols - 1) * CELL_GAP
        h = self.rows * CELL_HEIGHT + (self.rows - 1) * CELL_GAP
        return (w, h)


# ---------------------------------------------------------------------------
# Backward-compatible alias
# ---------------------------------------------------------------------------

GridInstance = GridPrimitive
