"""DPTable primitive — 1D or 2D table with optional transition arrows.

See ``docs/spec/primitives.md`` §5 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives.base import (
    ALL_RE,
    CELL_1D_RE,
    CELL_2D_RE,
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    CellMetrics,
    INDEX_LABEL_OFFSET,
    RANGE_RE,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _inset_rect_attrs,
    _render_svg_text,
    arrow_height_above,
    position_label_height_above,
    position_label_height_below,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._types import (
    SUFFIX_CELL_RE,
    SUFFIX_CELL_2D_RE,
    SUFFIX_RANGE_RE,
)
from scriba.animation.primitives.layout import TextBox, stack_bottom

# Per-role font sizes — must match the CSS variables in
# ``scriba-scene-primitives.css``. See the matching constants in
# ``array.py``; a CI guard test (``test_css_font_sync.py``) asserts
# equality for every role.
_FONT_SIZE_INDEX: int = 10
_FONT_SIZE_CAPTION: int = 11

# Vertical whitespace between consecutive items in the bottom stack
# (index-label row → caption row). ``vstack`` guarantees no glyph-box
# overlap for any baseline/font-size combination; see ``layout.py``.
_STACK_GAP: int = 9


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

# Full-qualified selectors (with shape name prefix) — canonical from base.py.
_CELL_1D_RE = CELL_1D_RE
_CELL_2D_RE = CELL_2D_RE
_RANGE_RE = RANGE_RE
_ALL_RE = ALL_RE

# Suffix-only regexes (no shape name prefix) — canonical from ._types.
_SUFFIX_CELL_1D_RE = SUFFIX_CELL_RE
_SUFFIX_CELL_2D_RE = SUFFIX_CELL_2D_RE
_SUFFIX_RANGE_RE = SUFFIX_RANGE_RE


# ---------------------------------------------------------------------------
# DPTablePrimitive
# ---------------------------------------------------------------------------


@register_primitive("DPTable")
@_protocol_register
class DPTablePrimitive(PrimitiveBase):
    """A 1D or 2D DP table with optional transition arrows.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type = "dptable"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "cell[{i}]": "cell by index (1D mode)",
        "cell[{r}][{c}]": "cell by row,col (2D mode)",
        "range[{lo}:{hi}]": "contiguous range of cells (1D mode)",
        "all": "all cells",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "n",
        "rows",
        "cols",
        "data",
        "labels",
        "label",
    })

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)
        n = self.params.get("n")
        rows = self.params.get("rows")
        cols = self.params.get("cols")

        if n is not None:
            # 1D mode
            n = int(n)
            if n < 1:
                raise _animation_error(
                    "E1427",
                    detail=(
                        f"DPTable n {n} is out of range; valid: "
                        "positive integer"
                    ),
                )
            is_2d = False
            dim_rows = 1
            dim_cols = n
        elif rows is not None and cols is not None:
            # 2D mode
            is_2d = True
            dim_rows = int(rows)
            dim_cols = int(cols)
            if dim_rows < 1:
                raise _animation_error(
                    "E1428",
                    detail=(
                        f"DPTable rows {dim_rows} is out of range; "
                        "valid: positive integer"
                    ),
                )
            if dim_cols < 1:
                raise _animation_error(
                    "E1428",
                    detail=(
                        f"DPTable cols {dim_cols} is out of range; "
                        "valid: positive integer"
                    ),
                )
            n = dim_rows * dim_cols
        else:
            raise _animation_error(
                "E1426",
                detail="DPTable requires 'n' (1D) or 'rows'+'cols' (2D)",
                hint="example: \\shape{t}{DPTable}{n=10}",
            )

        max_cells = dim_rows * dim_cols
        if max_cells > 250_000:
            raise _animation_error(
                "E1425",
                detail=(
                    f"DPTable cell count {max_cells} (rows={dim_rows}, "
                    f"cols={dim_cols}) exceeds maximum; valid: "
                    f"rows*cols <= 250000"
                ),
            )

        data: list[Any] = list(self.params.get("data", []))
        if data and len(data) != n:
            raise _animation_error(
                "E1429",
                detail=(
                    f"DPTable 'data' length ({len(data)}) does not match "
                    f"expected size ({n}); valid: len(data) == "
                    f"{'rows*cols' if is_2d else 'n'}"
                ),
            )
        if not data:
            data = [""] * n

        self.is_2d: bool = is_2d
        self.rows: int = dim_rows
        self.cols: int = dim_cols
        self.data: list[Any] = data
        self.labels: str | None = self.params.get("labels")
        self.label: str | None = self.params.get("label")

    # -- PrimitiveBase interface --------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector suffixes."""
        parts: list[str] = []
        if self.is_2d:
            for r in range(self.rows):
                for c in range(self.cols):
                    parts.append(f"cell[{r}][{c}]")
        else:
            for i in range(self.cols):
                parts.append(f"cell[{i}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        """Check whether *suffix* is a valid addressable part."""
        if self.is_2d:
            m = _SUFFIX_CELL_2D_RE.match(suffix)
            if m:
                r, c = int(m.group("row")), int(m.group("col"))
                return 0 <= r < self.rows and 0 <= c < self.cols
        else:
            m = _SUFFIX_CELL_1D_RE.match(suffix)
            if m:
                return 0 <= int(m.group("idx")) < self.cols

            m = _SUFFIX_RANGE_RE.match(suffix)
            if m:
                lo, hi = int(m.group("lo")), int(m.group("hi"))
                return 0 <= lo <= hi < self.cols

        return suffix == "all"

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the DP table."""
        effective_anns = self._annotations

        # Compute vertical space needed above cells for arrow curves and
        # position=above pill labels.
        computed = arrow_height_above(
            effective_anns, self.resolve_annotation_point, cell_height=CELL_HEIGHT
        )
        pos_above = position_label_height_above(effective_anns, cell_height=CELL_HEIGHT)
        arrow_above = max(computed, pos_above, getattr(self, "_min_arrow_above", 0))

        lines: list[str] = [
            f'<g data-primitive="dptable" data-shape="{self.name}">'
        ]

        # Shift all content down so arrows curve into valid space above y=0
        if arrow_above > 0:
            lines.append(f'  <g transform="translate(0, {arrow_above})">')

        if self.is_2d:
            self._emit_2d_cells(lines, render_inline_tex=render_inline_tex)
        else:
            self._emit_1d_cells(lines, render_inline_tex=render_inline_tex)

        # Arrow annotations
        if effective_anns:
            _cell_metrics = CellMetrics(
                cell_width=float(CELL_WIDTH),
                cell_height=float(CELL_HEIGHT),
                grid_cols=int(self.cols),
                grid_rows=int(self.rows) if self.is_2d else 1,
                origin_x=0.0,
                origin_y=0.0,
            )
            self.emit_annotation_arrows(
                lines,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
                cell_metrics=_cell_metrics,
            )

        # Caption label — wrapped, width-folded, centered on the footprint
        # (shared Layer-A helper). ``_caption_top_y`` is the single source for
        # the caption's vertical placement (also used by ``bounding_box``), so
        # the drawn caption and the reserved box can never drift apart.
        if self.label is not None:
            self._emit_caption(
                lines,
                content_width=float(self._grid_dimensions()[0]),
                footprint_width=int(self.bounding_box().width),
                top_y=self._caption_top_y(),
                render_inline_tex=render_inline_tex,
            )

        # Close the translate group if we opened one for arrow space
        if arrow_above > 0:
            lines.append("  </g>")

        lines.append("</g>")
        return "\n".join(lines)

    def _caption_top_y(self) -> int:
        """Y of the caption block's top edge — the single source shared by
        ``bounding_box`` and ``emit_svg`` so the reserved box and the drawn
        caption never drift.

        For the 1D-with-labels layout the caption clears the index-label row;
        otherwise (2D, or 1D without index labels) it sits directly below the
        cells by ``INDEX_LABEL_OFFSET``.
        """
        _, th = self._grid_dimensions()
        if not self.is_2d and self.labels:
            index_bottom = stack_bottom(
                [TextBox(font_size=_FONT_SIZE_INDEX, role="label", baseline="hanging")],
                start_y=th + INDEX_LABEL_OFFSET,
                gap=_STACK_GAP,
            )
            return int(index_bottom + _STACK_GAP)
        return int(th + INDEX_LABEL_OFFSET)

    def bounding_box(self) -> BoundingBox:
        """Return ``(x, y, width, height)``.

        The caption width participates in the footprint (Defect 6) so a caption
        wider than the cell grid is folded into the box rather than clipped, and
        its (possibly wrapped) height is reserved below ``_caption_top_y`` — the
        same anchor ``emit_svg`` draws from. The no-caption index-row case keeps
        the tight ``stack_bottom`` height.
        """
        tw, th = self._grid_dimensions()
        content_w = float(tw)
        w = max(content_w, float(self._caption_block_width(content_w)))
        if self.label is not None:
            h = float(self._caption_top_y() + self._caption_block_height(content_w))
        elif not self.is_2d and self.labels:
            h = stack_bottom(
                [TextBox(font_size=_FONT_SIZE_INDEX, role="label", baseline="hanging")],
                start_y=th + INDEX_LABEL_OFFSET,
                gap=_STACK_GAP,
            )
        else:
            h = float(th)
        # Reserve space above for arrow annotations and position=above labels.
        computed = arrow_height_above(
            self._annotations, self.resolve_annotation_point, cell_height=CELL_HEIGHT
        )
        pos_above = position_label_height_above(self._annotations, cell_height=CELL_HEIGHT)
        arrow_above = max(computed, pos_above, getattr(self, "_min_arrow_above", 0))
        h += arrow_above
        pos_below = position_label_height_below(self._annotations, cell_height=CELL_HEIGHT)
        h += pos_below
        return BoundingBox(x=0, y=0, width=w, height=h)

    # -- internal: cell emission -------------------------------------------

    def _emit_1d_cells(
        self,
        lines: list[str],
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> None:
        """Emit cells for 1D layout (identical to Array)."""
        idx_labels = (
            _parse_index_labels(self.labels, self.cols)
            if self.labels
            else None
        )

        for i in range(self.cols):
            target = f"{self.name}.cell[{i}]"
            suffix = f"cell[{i}]"

            value = self.get_value(suffix)
            if value is None:
                value = self.data[i]
            effective_state = self.resolve_effective_state(suffix)

            css = state_class(effective_state)
            colors = svg_style_attrs(effective_state)

            x = int(i * (CELL_WIDTH + CELL_GAP))
            y = 0

            lines.append(f'  <g data-target="{target}" class="{css}">')
            rect_attrs = _inset_rect_attrs(x, y, CELL_WIDTH, CELL_HEIGHT)
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

            if idx_labels is not None:
                label_y = int(CELL_HEIGHT + INDEX_LABEL_OFFSET)
                lines.append(
                    "  "
                    + _render_svg_text(
                        idx_labels[i],
                        text_x,
                        label_y,
                        fill=THEME["fg_muted"],
                        css_class="scriba-index-label idx",
                        fo_width=CELL_WIDTH,
                        fo_height=20,
                        render_inline_tex=render_inline_tex,
                    )
                )

    def _emit_2d_cells(
        self,
        lines: list[str],
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
    ) -> None:
        """Emit cells for 2D grid layout."""
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

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Resolve a cell or 1D ``range`` selector to its arrow anchor.

        Layer B — a ``range[lo:hi]`` target validates true but previously had no
        anchor, so the annotation was silently dropped (no arrow, no label).
        Mirrors Array's Defect-5 fix; range is 1D-only.
        """
        result = self._cell_center(selector)
        if result is None:
            result = self._range_center(selector)
        if result is None:
            return None
        return (float(result[0]), float(result[1]))

    def _range_center(self, selector_str: str) -> tuple[int, int] | None:
        """Center anchor for a 1D ``range[lo:hi]`` selector (inclusive span)."""
        if self.is_2d:
            return None
        m = _RANGE_RE.match(selector_str)
        if m and m.group("name") == self.name:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            if 0 <= lo <= hi < self.cols:
                left = lo * (CELL_WIDTH + CELL_GAP)
                right = hi * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH
                return (int((left + right) // 2), int(CELL_HEIGHT // 2))
        return None

    def resolve_annotation_box(self, selector: str) -> BoundingBox | None:
        """Return the 1D ``range`` span AABB so the range gets a span bracket and
        is treated as a blocker by the pill placer (Layer B). Local coords, cell
        top at ``y=0``.

        Scoped to ranges: single-cell targets keep the base default (``None``)
        so existing cell-annotation placement is byte-stable — the cell-obstacle
        refinement (Layer C) is tracked separately.
        """
        if self.is_2d:
            return None
        m = _RANGE_RE.match(selector)
        if m and m.group("name") == self.name:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            if 0 <= lo <= hi < self.cols:
                left = lo * (CELL_WIDTH + CELL_GAP)
                right = hi * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH
                return BoundingBox(
                    x=int(left), y=0, width=int(right - left), height=int(CELL_HEIGHT)
                )
        return None

    def _cell_center(self, selector_str: str) -> tuple[int, int] | None:
        """Return the ``(cx, cy)`` pixel center of a cell selector."""
        m = _CELL_1D_RE.match(selector_str)
        if m and m.group("name") == self.name:
            i = int(m.group("idx"))
            x = int(i * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2)
            y = int(CELL_HEIGHT // 2)
            return (x, y)

        m = _CELL_2D_RE.match(selector_str)
        if m and m.group("name") == self.name:
            r, c = int(m.group("row")), int(m.group("col"))
            x = int(c * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2)
            y = int(r * (CELL_HEIGHT + CELL_GAP) + CELL_HEIGHT // 2)
            return (x, y)

        return None

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []

    # -- internal: dimensions ----------------------------------------------

    def _grid_dimensions(self) -> tuple[int, int]:
        """Return ``(total_width, total_height)`` of the cell grid."""
        if self.cols == 0:
            return (0, 0)
        w = self.cols * CELL_WIDTH + (self.cols - 1) * CELL_GAP
        h = self.rows * CELL_HEIGHT + (self.rows - 1) * CELL_GAP
        return (w, h)


# ---------------------------------------------------------------------------
# Backward-compatible alias
# ---------------------------------------------------------------------------

DPTableInstance = DPTablePrimitive


# ---------------------------------------------------------------------------
# Index label parser (shared with Array)
# ---------------------------------------------------------------------------


def _parse_index_labels(fmt: str, size: int) -> list[str]:
    """Parse ``labels`` format string into a list of label strings."""
    m = re.match(r"^(\d+)\.\.(\d+)$", fmt)
    if m:
        return [str(i) for i in range(size)]

    m = re.match(r"^(.+?)\[(\d+)\]\.\.(.+?)\[(\d+)\]$", fmt)
    if m:
        prefix = m.group(1)
        return [f"{prefix}[{i}]" for i in range(size)]

    return [str(i) for i in range(size)]
