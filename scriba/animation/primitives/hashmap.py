"""HashMap primitive -- bucket-based hash table with chained entries.

Renders a vertical table where each row is a bucket: an index column on the
left and an entries column on the right showing key:value pairs.  Operations
target buckets by integer index.

See ``docs/archive/PRIMITIVES-PLAN.md`` SS3 for the original specification.
The implementation uses the simplified bucket-level-only design described
in the task (no individual entry selectors).
"""

from __future__ import annotations

import re
from html import escape as html_escape
from typing import Any, Callable

from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    _render_svg_text,
    svg_style_attrs,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_INDEX_COL_WIDTH = 40
_ENTRIES_COL_WIDTH = 200
_ROW_HEIGHT = 40
_PADDING = 4
_TOTAL_WIDTH = _INDEX_COL_WIDTH + _ENTRIES_COL_WIDTH
_INDEX_FONT_SIZE = "13"
_ENTRIES_FONT_SIZE = "13"

# ---------------------------------------------------------------------------
# Selector regex
# ---------------------------------------------------------------------------

_BUCKET_RE = re.compile(r"^bucket\[(?P<idx>\d+)\]$")
_ALL_RE = re.compile(r"^all$")

# ---------------------------------------------------------------------------
# HashMap primitive
# ---------------------------------------------------------------------------


class HashMap(PrimitiveBase):
    """Bucket-based hash table visualization.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``hm``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
        Required keys: ``capacity`` (int).
        Optional keys: ``label``.
    """

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        raw_cap = params.get("capacity")
        if raw_cap is None:
            raise ValueError(
                f"HashMap '{name}' requires a 'capacity' parameter"
            )
        self.capacity: int = int(raw_cap)
        if self.capacity < 1:
            raise ValueError(
                f"HashMap '{name}' capacity must be >= 1, got {self.capacity}"
            )

        self.label_text: str | None = params.get("label")
        self.primitive_type: str = "HashMap"

        # Per-bucket display text: index -> string (e.g. "cat:3  car:7")
        self._bucket_values: dict[int, str] = {
            i: "" for i in range(self.capacity)
        }

    # ----- apply commands --------------------------------------------------

    def apply_command(
        self,
        params: dict[str, Any],
        *,
        target_suffix: str | None = None,
    ) -> None:
        """Process value-set commands from ``\\apply``.

        When the target is a specific bucket (e.g. ``hm.bucket[0]``),
        *target_suffix* is ``"bucket[0]"`` and *params* should contain
        ``value``.
        """
        if target_suffix is not None:
            m = _BUCKET_RE.match(target_suffix)
            if m:
                idx = int(m.group("idx"))
                if 0 <= idx < self.capacity and "value" in params:
                    self._bucket_values[idx] = str(params["value"])
                return

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for i in range(self.capacity):
            parts.append(f"bucket[{i}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True

        m = _BUCKET_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return 0 <= idx < self.capacity

        return False

    def bounding_box(self) -> BoundingBox:
        h = self.capacity * _ROW_HEIGHT + 2 * _PADDING
        w = _TOTAL_WIDTH + 2 * _PADDING

        if self.label_text:
            h += 20

        return BoundingBox(x=0, y=0, width=w, height=h)

    def emit_svg(
        self, *, render_inline_tex: Callable[[str], str] | None = None
    ) -> str:
        parts: list[str] = []
        parts.append(
            f'<g data-primitive="HashMap" '
            f'data-shape="{html_escape(self.name)}">'
        )

        table_h = self.capacity * _ROW_HEIGHT

        # Outer border
        parts.append(
            f'<rect x="{_PADDING}" y="{_PADDING}" '
            f'width="{_TOTAL_WIDTH}" height="{table_h}" '
            f'fill="none" stroke="#d0d7de" stroke-width="1" rx="4"/>'
        )

        # Column divider between index and entries
        divider_x = _PADDING + _INDEX_COL_WIDTH
        parts.append(
            f'<line x1="{divider_x}" y1="{_PADDING}" '
            f'x2="{divider_x}" y2="{_PADDING + table_h}" '
            f'stroke="#d0d7de" stroke-width="1"/>'
        )

        for row_idx in range(self.capacity):
            suffix = f"bucket[{row_idx}]"
            target = f"{self.name}.{suffix}"

            state = self.get_state(suffix)
            all_state = self.get_state("all")
            if all_state != "idle" and state == "idle":
                state = all_state

            colors = svg_style_attrs(state)
            row_y = _PADDING + row_idx * _ROW_HEIGHT

            parts.append(
                f'<g data-target="{html_escape(target)}" '
                f'class="scriba-state-{state}">'
            )

            # Row divider (skip first row)
            if row_idx > 0:
                parts.append(
                    f'<line x1="{_PADDING}" y1="{row_y}" '
                    f'x2="{_PADDING + _TOTAL_WIDTH}" y2="{row_y}" '
                    f'stroke="#d0d7de" stroke-width="0.5"/>'
                )

            # Index column background (always gray)
            parts.append(
                f'<rect x="{_PADDING}" y="{row_y}" '
                f'width="{_INDEX_COL_WIDTH}" height="{_ROW_HEIGHT}" '
                f'fill="#f1f3f5" stroke="none"/>'
            )

            # Entries column background (state-colored)
            entries_x = _PADDING + _INDEX_COL_WIDTH
            parts.append(
                f'<rect x="{entries_x}" y="{row_y}" '
                f'width="{_ENTRIES_COL_WIDTH}" height="{_ROW_HEIGHT}" '
                f'fill="{colors["fill"]}" stroke="none"/>'
            )

            # Index text (centered in index column)
            idx_tx = _PADDING + _INDEX_COL_WIDTH // 2
            idx_ty = row_y + _ROW_HEIGHT // 2
            parts.append(
                _render_svg_text(
                    str(row_idx),
                    idx_tx,
                    idx_ty,
                    fill="#6c757d",
                    font_size=_INDEX_FONT_SIZE,
                    text_anchor="middle",
                    dominant_baseline="central",
                    fo_width=_INDEX_COL_WIDTH - 4,
                    fo_height=_ROW_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )

            # Entries text (left-aligned in entries column)
            entry_tx = entries_x + 8
            entry_ty = row_y + _ROW_HEIGHT // 2
            display_value = self._bucket_values.get(row_idx, "")
            if display_value:
                parts.append(
                    _render_svg_text(
                        display_value,
                        entry_tx,
                        entry_ty,
                        fill=colors["text"],
                        font_size=_ENTRIES_FONT_SIZE,
                        text_anchor="start",
                        dominant_baseline="central",
                        fo_width=_ENTRIES_COL_WIDTH - 16,
                        fo_height=_ROW_HEIGHT,
                        render_inline_tex=render_inline_tex,
                    )
                )

            parts.append("</g>")

        # Caption / label
        if self.label_text is not None:
            bbox = self.bounding_box()
            cx = bbox.width // 2
            cy = bbox.height - 4
            parts.append(
                _render_svg_text(
                    str(self.label_text),
                    cx,
                    cy,
                    fill="#6c757d",
                    css_class="scriba-primitive-label",
                    text_anchor="middle",
                    fo_width=bbox.width,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
            )

        parts.append("</g>")
        return "".join(parts)
