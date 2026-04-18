"""Grid primitive -- a 2D rows x cols matrix of uniform cells.

See ``docs/spec/primitives.md`` section 4 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import E1103, _animation_error
from scriba.animation.primitives.base import (
    ALL_RE,
    CELL_2D_RE,
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    INDEX_LABEL_OFFSET,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _inset_rect_attrs,
    _render_svg_text,
    arrow_height_above,
    _LabelPlacement,
    emit_arrow_marker_defs,
    emit_arrow_svg,
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

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG (x, y) center for an annotation selector.

        Supports ``"<name>.cell[<row>][<col>]"`` selectors.
        Returns the top-center of the cell (y=top edge) so arrows curve above.
        """
        m = _CELL_2D_RE.match(selector)
        if m and m.group("name") == self.shape_name:
            r = int(m.group("row"))
            c = int(m.group("col"))
            if 0 <= r < self.rows and 0 <= c < self.cols:
                x = c * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2
                y = r * (CELL_HEIGHT + CELL_GAP) + CELL_HEIGHT // 2  # cell center
                return (float(x), float(y))
        return None

    def _arrow_height_above(self, annotations: "list[dict]") -> int:
        """Compute arrow height above, locked to cross-frame max to prevent jitter."""
        computed = arrow_height_above(
            annotations, self.resolve_annotation_point, cell_height=CELL_HEIGHT,
            layout="2d",
        )
        return max(computed, getattr(self, "_min_arrow_above", 0))

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the grid."""
        effective_anns = self._annotations

        # Compute vertical space needed above cells for arrow curves
        arrow_above = self._arrow_height_above(effective_anns)

        lines: list[str] = [
            f'<g data-primitive="grid" data-shape="{self.shape_name}">'
        ]

        # Shift all content down so arrows curve into valid space above y=0
        if arrow_above > 0:
            lines.append(f'  <g transform="translate(0, {arrow_above})">')

        # Emit arrowhead marker defs when annotations with arrows are present
        emit_arrow_marker_defs(lines, effective_anns)

        for r in range(self.rows):
            for c in range(self.cols):
                target = f"{self.shape_name}.cell[{r}][{c}]"
                suffix = f"cell[{r}][{c}]"

                state_name = self.get_state(suffix)
                value = self.get_value(suffix)
                if value is None:
                    flat_idx = r * self.cols + c
                    value = self.data[flat_idx]

                # β redesign — highlight is a state, not an overlay.
                highlighted = suffix in self._highlighted
                if highlighted and state_name == "idle":
                    effective_state = "highlight"
                else:
                    effective_state = state_name

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

        # Arrow annotations
        arrow_anns = [a for a in effective_anns if a.get("arrow_from")]
        placed: list[_LabelPlacement] = []
        for idx, ann in enumerate(arrow_anns):
            src = self.resolve_annotation_point(ann.get("arrow_from", ""))
            dst = self.resolve_annotation_point(ann.get("target", ""))
            if src and dst:
                arrow_index = sum(
                    1
                    for prev in arrow_anns[:idx]
                    if prev.get("target") == ann.get("target")
                )
                emit_arrow_svg(
                    lines, ann, src, dst, arrow_index,
                    CELL_HEIGHT, render_inline_tex,
                    layout="2d",
                    placed_labels=placed,
                )

        # Close the translate group if we opened one for arrow space
        if arrow_above > 0:
            lines.append("  </g>")

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> BoundingBox:
        """Return the bounding box of this grid."""
        tw, th = self._grid_dimensions()
        h = th
        if self.label:
            h += INDEX_LABEL_OFFSET
        arrow_above = self._arrow_height_above(self._annotations)
        h += arrow_above
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
