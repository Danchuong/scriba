"""DPTable primitive — 1D or 2D table with optional transition arrows.

See ``docs/06-primitives.md`` §5 for the authoritative specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from scriba.animation.errors import E1103, animation_error
from scriba.animation.primitives.base import (
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    DEFAULT_STATE,
    INDEX_LABEL_OFFSET,
    _escape_xml,
    state_class,
)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class DPTablePrimitive:
    """Factory that creates :class:`DPTableInstance` from ``\\shape`` params."""

    name: str = "DPTable"

    def declare(
        self, shape_name: str, params: dict[str, Any]
    ) -> DPTableInstance:
        """Validate params and build a :class:`DPTableInstance`."""
        n = params.get("n")
        rows = params.get("rows")
        cols = params.get("cols")

        if n is not None:
            # 1D mode
            n = int(n)
            is_2d = False
            dim_rows = 1
            dim_cols = n
        elif rows is not None and cols is not None:
            # 2D mode
            is_2d = True
            dim_rows = int(rows)
            dim_cols = int(cols)
            n = dim_rows * dim_cols
        else:
            raise animation_error(
                E1103,
                detail="DPTable requires 'n' (1D) or 'rows'+'cols' (2D)",
            )

        data: list[Any] = list(params.get("data", []))
        if data and len(data) != n:
            raise animation_error(
                E1103,
                detail=(
                    f"DPTable 'data' length ({len(data)}) "
                    f"does not match expected size ({n})"
                ),
            )
        if not data:
            data = [""] * n

        labels: str | None = params.get("labels")
        label: str | None = params.get("label")

        return DPTableInstance(
            shape_name=shape_name,
            is_2d=is_2d,
            rows=dim_rows,
            cols=dim_cols,
            data=data,
            labels=labels,
            label=label,
        )


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

_CELL_1D_RE = re.compile(r"^(?P<name>\w+)\.cell\[(?P<idx>\d+)\]$")
_CELL_2D_RE = re.compile(
    r"^(?P<name>\w+)\.cell\[(?P<row>\d+)\]\[(?P<col>\d+)\]$"
)
_RANGE_RE = re.compile(
    r"^(?P<name>\w+)\.range\[(?P<lo>\d+):(?P<hi>\d+)\]$"
)
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")


# ---------------------------------------------------------------------------
# Instance
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DPTableInstance:
    """A declared DPTable instance with layout pre-computed."""

    shape_name: str
    is_2d: bool
    rows: int
    cols: int
    data: list[Any] = field(default_factory=list)
    labels: str | None = None
    label: str | None = None
    primitive_type: str = "dptable"

    # -- protocol -----------------------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector targets."""
        parts: list[str] = []
        if self.is_2d:
            for r in range(self.rows):
                for c in range(self.cols):
                    parts.append(f"{self.shape_name}.cell[{r}][{c}]")
        else:
            for i in range(self.cols):
                parts.append(f"{self.shape_name}.cell[{i}]")
        parts.append(f"{self.shape_name}.all")
        return parts

    def validate_selector(self, selector_str: str) -> bool:
        """Check whether *selector_str* is valid for this instance."""
        if self.is_2d:
            m = _CELL_2D_RE.match(selector_str)
            if m and m.group("name") == self.shape_name:
                r, c = int(m.group("row")), int(m.group("col"))
                return 0 <= r < self.rows and 0 <= c < self.cols
        else:
            m = _CELL_1D_RE.match(selector_str)
            if m and m.group("name") == self.shape_name:
                return 0 <= int(m.group("idx")) < self.cols

            m = _RANGE_RE.match(selector_str)
            if m and m.group("name") == self.shape_name:
                lo, hi = int(m.group("lo")), int(m.group("hi"))
                return 0 <= lo <= hi < self.cols

        m = _ALL_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            return True

        return False

    def emit_svg(
        self,
        state: dict[str, dict[str, Any]],
        annotations: list[dict[str, Any]] | None = None,
    ) -> str:
        """Emit SVG ``<g>`` for the DP table.

        *annotations* is an optional list of dicts with keys:
        ``target``, ``arrow_from``, ``label``, ``color``.
        """
        lines: list[str] = [
            f'<g data-primitive="dptable" data-shape="{self.shape_name}">'
        ]

        if self.is_2d:
            self._emit_2d_cells(lines, state)
        else:
            self._emit_1d_cells(lines, state)

        # Arrow annotations
        if annotations:
            for ann in annotations:
                self._emit_arrow(lines, ann)

        # Caption label
        if self.label is not None:
            tw, th = self._grid_dimensions()
            center_x = int(tw // 2)
            base_y = th
            if not self.is_2d and self.labels:
                base_y += INDEX_LABEL_OFFSET
            label_y = int(base_y + INDEX_LABEL_OFFSET)
            lines.append(
                f'  <text class="scriba-primitive-label" '
                f'x="{center_x}" y="{label_y}">'
                f"{_escape_xml(self.label)}</text>"
            )

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> tuple[float, float, float, float]:
        """Return ``(x, y, width, height)``."""
        tw, th = self._grid_dimensions()
        h = th
        if not self.is_2d and self.labels:
            h += INDEX_LABEL_OFFSET
        if self.label:
            h += INDEX_LABEL_OFFSET
        return (0, 0, float(tw), float(h))

    # -- internal: cell emission -------------------------------------------

    def _emit_1d_cells(
        self,
        lines: list[str],
        state: dict[str, dict[str, Any]],
    ) -> None:
        """Emit cells for 1D layout (identical to Array)."""
        idx_labels = (
            _parse_index_labels(self.labels, self.cols)
            if self.labels
            else None
        )

        for i in range(self.cols):
            target = f"{self.shape_name}.cell[{i}]"
            cell_state = state.get(target, {})
            css = state_class(cell_state.get("state", DEFAULT_STATE))
            value = cell_state.get("value", self.data[i])

            x = int(i * (CELL_WIDTH + CELL_GAP))
            y = 0

            lines.append(f'  <g data-target="{target}" class="{css}">')
            lines.append(
                f'    <rect x="{x}" y="{y}" '
                f'width="{CELL_WIDTH}" height="{CELL_HEIGHT}" />'
            )
            text_x = int(x + CELL_WIDTH // 2)
            text_y = int(y + CELL_HEIGHT // 2)
            lines.append(
                f'    <text x="{text_x}" y="{text_y}">'
                f"{_escape_xml(value)}</text>"
            )
            lines.append("  </g>")

            if idx_labels is not None:
                label_y = int(CELL_HEIGHT + INDEX_LABEL_OFFSET)
                lines.append(
                    f'  <text class="scriba-index-label" '
                    f'x="{text_x}" y="{label_y}">'
                    f"{_escape_xml(idx_labels[i])}</text>"
                )

    def _emit_2d_cells(
        self,
        lines: list[str],
        state: dict[str, dict[str, Any]],
    ) -> None:
        """Emit cells for 2D grid layout."""
        for r in range(self.rows):
            for c in range(self.cols):
                target = f"{self.shape_name}.cell[{r}][{c}]"
                cell_state = state.get(target, {})
                css = state_class(cell_state.get("state", DEFAULT_STATE))
                flat_idx = r * self.cols + c
                value = cell_state.get("value", self.data[flat_idx])

                x = int(c * (CELL_WIDTH + CELL_GAP))
                y = int(r * (CELL_HEIGHT + CELL_GAP))

                lines.append(
                    f'  <g data-target="{target}" class="{css}">'
                )
                lines.append(
                    f'    <rect x="{x}" y="{y}" '
                    f'width="{CELL_WIDTH}" height="{CELL_HEIGHT}" />'
                )
                text_x = int(x + CELL_WIDTH // 2)
                text_y = int(y + CELL_HEIGHT // 2)
                lines.append(
                    f'    <text x="{text_x}" y="{text_y}">'
                    f"{_escape_xml(value)}</text>"
                )
                lines.append("  </g>")

    # -- internal: arrows --------------------------------------------------

    def _emit_arrow(
        self,
        lines: list[str],
        ann: dict[str, Any],
    ) -> None:
        """Emit a cubic Bezier arrow annotation."""
        color = ann.get("color", "info")
        label_text = ann.get("label", "")
        target = ann.get("target", "")
        arrow_from = ann.get("arrow_from", "")

        src_center = self._cell_center(arrow_from)
        dst_center = self._cell_center(target)

        if src_center is None or dst_center is None:
            return

        x1, y1 = src_center
        x2, y2 = dst_center

        # Control points: curve upward
        mid_x = int((x1 + x2) // 2)
        mid_y = int(min(y1, y2) - 30)
        cx1 = int((x1 + mid_x) // 2)
        cy1 = mid_y
        cx2 = int((x2 + mid_x) // 2)
        cy2 = mid_y

        lines.append(
            f'  <g class="scriba-annotation scriba-annotation-{color}">'
        )
        lines.append(
            f'    <path d="M{x1},{y1} C{cx1},{cy1} {cx2},{cy2} {x2},{y2}" '
            f'stroke="currentColor" fill="none" '
            f'marker-end="url(#scriba-arrow-{color})"/>'
        )
        if label_text:
            lines.append(
                f'    <text x="{mid_x}" y="{mid_y}">'
                f"{_escape_xml(label_text)}</text>"
            )
        lines.append("  </g>")

    def _cell_center(self, selector_str: str) -> tuple[int, int] | None:
        """Return the ``(cx, cy)`` pixel center of a cell selector."""
        m = _CELL_1D_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            i = int(m.group("idx"))
            x = int(i * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2)
            y = int(CELL_HEIGHT // 2)
            return (x, y)

        m = _CELL_2D_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            r, c = int(m.group("row")), int(m.group("col"))
            x = int(c * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2)
            y = int(r * (CELL_HEIGHT + CELL_GAP) + CELL_HEIGHT // 2)
            return (x, y)

        return None

    # -- internal: dimensions ----------------------------------------------

    def _grid_dimensions(self) -> tuple[int, int]:
        """Return ``(total_width, total_height)`` of the cell grid."""
        if self.cols == 0:
            return (0, 0)
        w = self.cols * CELL_WIDTH + (self.cols - 1) * CELL_GAP
        h = self.rows * CELL_HEIGHT + (self.rows - 1) * CELL_GAP
        return (w, h)


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
