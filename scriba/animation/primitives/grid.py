"""Grid primitive -- a 2D rows x cols matrix of uniform cells.

See ``docs/spec/primitives.md`` section 4 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives.base import (
    ALL_RE,
    CELL_2D_RE,
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    BoundingBox,
    PrimitiveBase,
    _inset_rect_attrs,
    _render_svg_text,
    arrow_height_above,
    register_primitive,
    state_class,
    svg_style_attrs,
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
        self.label: str | None = self.params.get("label")
        self._arrow_layout = "2d"

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
                x = c * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2
                y = r * (CELL_HEIGHT + CELL_GAP) + CELL_HEIGHT // 2  # cell center
                return (float(x), float(y))
        return None

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit below the whole grid (callout lane),
        clear of the cells, with a leader line back to the labelled cell."""
        return float(self._grid_dimensions()[1])

    def resolve_annotation_box(self, selector: str) -> "BoundingBox | None":
        """Cell AABB (Layer C) so a below-pill gets a leader line and the placer
        treats the labelled cell as a blocker. Scoped to below-pill targets so a
        wide above/left/right pill on a cell never spuriously trips the spanning
        leader."""
        if not self._target_has_below_pill(selector):
            return None
        m = _CELL_2D_RE.match(selector)
        if m and m.group("name") == self.name:
            r = int(m.group("row"))
            c = int(m.group("col"))
            if 0 <= r < self.rows and 0 <= c < self.cols:
                x = c * (CELL_WIDTH + CELL_GAP)
                y = r * (CELL_HEIGHT + CELL_GAP)
                return BoundingBox(
                    x=int(x), y=int(y), width=int(CELL_WIDTH), height=int(CELL_HEIGHT)
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
        computed = arrow_height_above(
            effective_anns, self.resolve_annotation_point,
            cell_height=CELL_HEIGHT, layout="2d",
        )
        arrow_above = max(computed, getattr(self, "_min_arrow_above", 0))
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

                x = int(c * (CELL_WIDTH + CELL_GAP))
                y = int(r * (CELL_HEIGHT + CELL_GAP))

                lines.append(
                    f'  <g data-target="{target}" class="{css}">'
                )
                rect_attrs = _inset_rect_attrs(
                    x, y, CELL_WIDTH, CELL_HEIGHT
                )
                lines.append(
                    f'    <rect x="{rect_attrs["x"]}" y="{rect_attrs["y"]}" '
                    f'width="{rect_attrs["width"]}" '
                    f'height="{rect_attrs["height"]}"/>'
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

        # Caption below the grid, beneath the below-pill lane (Layer A/C). It is
        # drawn inside the left_pad translate group, so it centers on the grid
        # core width, not the (possibly left/right-padded) bbox width.
        if self.label is not None:
            tw, th = self._grid_dimensions()
            self._emit_caption(
                lines,
                content_width=tw,
                footprint_width=max(tw, self._caption_block_width(tw)),
                top_y=int(th + self._below_lane_height()),
                render_inline_tex=render_inline_tex,
            )

        # Arrow + position-pill annotations
        if effective_anns:
            self.emit_annotation_arrows(lines, effective_anns, render_inline_tex=render_inline_tex)

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
        computed = arrow_height_above(
            self._annotations, self.resolve_annotation_point,
            cell_height=CELL_HEIGHT, layout="2d",
        )
        arrow_above = max(computed, getattr(self, "_min_arrow_above", 0))
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
        w = self.cols * CELL_WIDTH + (self.cols - 1) * CELL_GAP
        h = self.rows * CELL_HEIGHT + (self.rows - 1) * CELL_GAP
        return (w, h)


# ---------------------------------------------------------------------------
# Backward-compatible alias
# ---------------------------------------------------------------------------

GridInstance = GridPrimitive
