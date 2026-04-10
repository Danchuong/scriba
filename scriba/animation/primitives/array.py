"""Array primitive — a fixed-length horizontal row of indexed cells.

See ``docs/06-primitives.md`` §3 for the authoritative specification.
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
    svg_style_attrs,
)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class ArrayPrimitive:
    """Factory that creates :class:`ArrayInstance` from ``\\shape`` params."""

    name: str = "Array"

    def declare(
        self, shape_name: str, params: dict[str, Any]
    ) -> ArrayInstance:
        """Validate params and build an :class:`ArrayInstance`."""
        size = params.get("size", params.get("n"))
        if size is None:
            raise animation_error(
                E1103,
                detail="Array requires 'size' or 'n' parameter",
            )
        size = int(size)
        if size > 10_000:
            raise animation_error(
                E1103,
                detail=f"[E1103] Array size {size} exceeds maximum of 10,000",
            )

        data: list[Any] = list(params.get("data", []))
        if data and len(data) != size:
            raise animation_error(
                E1103,
                detail=(
                    f"Array 'data' length ({len(data)}) "
                    f"does not match size ({size})"
                ),
            )
        if not data:
            data = [""] * size

        labels: str | None = params.get("labels")
        label: str | None = params.get("label")

        return ArrayInstance(
            shape_name=shape_name,
            size=size,
            data=data,
            labels=labels,
            label=label,
        )


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

_CELL_RE = re.compile(r"^(?P<name>\w+)\.cell\[(?P<idx>\d+)\]$")
_RANGE_RE = re.compile(r"^(?P<name>\w+)\.range\[(?P<lo>\d+):(?P<hi>\d+)\]$")
_ALL_RE = re.compile(r"^(?P<name>\w+)\.all$")


# ---------------------------------------------------------------------------
# Instance
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArrayInstance:
    """A declared Array instance with layout pre-computed."""

    shape_name: str
    size: int
    data: list[Any] = field(default_factory=list)
    labels: str | None = None
    label: str | None = None
    primitive_type: str = "array"

    # -- protocol -----------------------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector targets."""
        parts: list[str] = []
        for i in range(self.size):
            parts.append(f"{self.shape_name}.cell[{i}]")
        parts.append(f"{self.shape_name}.all")
        return parts

    def validate_selector(self, selector_str: str) -> bool:
        """Check whether *selector_str* is valid for this instance."""
        m = _CELL_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            return 0 <= int(m.group("idx")) < self.size

        m = _RANGE_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            return 0 <= lo <= hi < self.size

        m = _ALL_RE.match(selector_str)
        if m and m.group("name") == self.shape_name:
            return True

        return False

    def emit_svg(self, state: dict[str, dict[str, Any]]) -> str:
        """Emit SVG ``<g>`` for the array."""
        lines: list[str] = [
            f'<g data-primitive="array" data-shape="{self.shape_name}">'
        ]

        for i in range(self.size):
            target = f"{self.shape_name}.cell[{i}]"
            cell_state = state.get(target, {})
            state_name = cell_state.get("state", DEFAULT_STATE)
            css = state_class(state_name)
            colors = svg_style_attrs(state_name)
            value = cell_state.get("value", self.data[i])

            x = int(i * (CELL_WIDTH + CELL_GAP))
            y = 0

            stroke_w = "1.5" if state_name == "idle" else "2"

            lines.append(
                f'  <g data-target="{target}" class="{css}">'
            )
            lines.append(
                f'    <rect x="{x}" y="{y}" '
                f'width="{CELL_WIDTH}" height="{CELL_HEIGHT}" '
                f'rx="4" fill="{colors["fill"]}" '
                f'stroke="{colors["stroke"]}" stroke-width="{stroke_w}"/>'
            )
            text_x = int(x + CELL_WIDTH // 2)
            text_y = int(y + CELL_HEIGHT // 2)
            lines.append(
                f'    <text x="{text_x}" y="{text_y}" '
                f'fill="{colors["text"]}">'
                f"{_escape_xml(value)}</text>"
            )
            # Highlight overlay (additive — dashed gold border on top)
            if cell_state.get("highlighted"):
                lines.append(
                    f'    <rect x="{x}" y="{y}" '
                    f'width="{CELL_WIDTH}" height="{CELL_HEIGHT}" '
                    f'rx="4" fill="none" '
                    f'stroke="#F0E442" stroke-width="3" '
                    f'stroke-dasharray="6 3"/>'
                )
            lines.append("  </g>")

            # Index labels below the cell
            if self.labels is not None:
                idx_labels = _parse_index_labels(self.labels, self.size)
                label_y = int(CELL_HEIGHT + INDEX_LABEL_OFFSET)
                lines.append(
                    f'  <text class="scriba-index-label idx" '
                    f'x="{text_x}" y="{label_y}" fill="#6c757d">'
                    f"{_escape_xml(idx_labels[i])}</text>"
                )

        # Caption label below the array
        if self.label is not None:
            total_width = self._total_width()
            center_x = int(total_width // 2)
            label_y_offset = CELL_HEIGHT + (
                INDEX_LABEL_OFFSET + 12 if self.labels else INDEX_LABEL_OFFSET
            )
            label_y = int(label_y_offset)
            lines.append(
                f'  <text class="scriba-primitive-label" '
                f'x="{center_x}" y="{label_y}" fill="#6c757d">'
                f"{_escape_xml(self.label)}</text>"
            )

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> tuple[float, float, float, float]:
        """Return ``(x, y, width, height)``."""
        w = self._total_width()
        h = CELL_HEIGHT
        if self.labels:
            h += INDEX_LABEL_OFFSET
        if self.label:
            h += INDEX_LABEL_OFFSET + 12 if self.labels else INDEX_LABEL_OFFSET
        return (0, 0, float(w), float(h))

    # -- internal -----------------------------------------------------------

    def _total_width(self) -> int:
        if self.size == 0:
            return 0
        return self.size * CELL_WIDTH + (self.size - 1) * CELL_GAP


# ---------------------------------------------------------------------------
# Index label parser
# ---------------------------------------------------------------------------


def _parse_index_labels(fmt: str, size: int) -> list[str]:
    """Parse ``labels`` format string into a list of label strings.

    Supports:
    - ``"0..6"`` -> ``["0", "1", "2", "3", "4", "5", "6"]``
    - ``"dp[0]..dp[6]"`` -> ``["dp[0]", "dp[1]", ..., "dp[6]"]``
    """
    m = re.match(r"^(\d+)\.\.(\d+)$", fmt)
    if m:
        return [str(i) for i in range(size)]

    m = re.match(r"^(.+?)\[(\d+)\]\.\.(.+?)\[(\d+)\]$", fmt)
    if m:
        prefix = m.group(1)
        return [f"{prefix}[{i}]" for i in range(size)]

    # Fallback: plain indices
    return [str(i) for i in range(size)]
