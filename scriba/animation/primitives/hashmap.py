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
from typing import Any, Callable, ClassVar

from scriba.animation.errors import E1103, animation_error
from scriba.animation.primitives.base import (
    _LabelPlacement,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _render_svg_text,
    arrow_height_above,
    emit_arrow_marker_defs,
    emit_arrow_svg,
    estimate_text_width,
    register_primitive,
    svg_style_attrs,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_INDEX_COL_WIDTH = 40
_MIN_ENTRIES_COL_WIDTH = 200
_ROW_HEIGHT = 40
_PADDING = 4
_INDEX_FONT_SIZE = "13"
_ENTRIES_FONT_SIZE = "13"
_ENTRIES_FONT_SIZE_INT = 13

# ---------------------------------------------------------------------------
# Selector regex
# ---------------------------------------------------------------------------

_BUCKET_RE = re.compile(r"^bucket\[(?P<idx>\d+)\]$")
_ALL_RE = re.compile(r"^all$")

# ---------------------------------------------------------------------------
# HashMap primitive
# ---------------------------------------------------------------------------


@register_primitive("HashMap")
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

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "bucket[{i}]": "bucket by index",
        "all": "all buckets",
    }

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        raw_cap = params.get("capacity")
        if raw_cap is None:
            raise animation_error(
                "E1450",
                detail=f"HashMap '{name}' requires a 'capacity' parameter",
                hint="example: HashMap{h}{capacity=8}",
            )
        self.capacity: int = int(raw_cap)
        if self.capacity < 1:
            raise animation_error(
                "E1451",
                detail=(
                    f"HashMap '{name}' capacity {self.capacity} is out "
                    "of range; valid: positive integer"
                ),
            )

        self.label_text: str | None = params.get("label")
        self.primitive_type: str = "HashMap"

        # Per-bucket display text: index -> string (e.g. "cat:3  car:7")
        self._bucket_values: dict[int, str] = {
            i: "" for i in range(self.capacity)
        }

        # Monotonic max: never shrinks so bounding_box stays valid across frames
        self._max_entries_col_width: int = _MIN_ENTRIES_COL_WIDTH

    # ----- dynamic column widths ------------------------------------------

    def _index_col_width(self) -> int:
        """Compute index column width based on the number of digits needed."""
        max_idx = self.capacity - 1
        digit_count = len(str(max_idx))
        # For 1-2 digits the default is fine; for 3+ digits widen
        needed = estimate_text_width(str(max_idx), font_size=int(_INDEX_FONT_SIZE)) + 16
        return max(_MIN_INDEX_COL_WIDTH, needed)

    def _compute_entries_col_width(self) -> int:
        """Pure scan: compute entries column width from the longest bucket value."""
        max_text_w = 0
        for value in self._bucket_values.values():
            if value:
                w = estimate_text_width(value, font_size=_ENTRIES_FONT_SIZE_INT)
                max_text_w = max(max_text_w, w)
        # Add horizontal padding (8px left + 8px right)
        needed = max_text_w + 16
        return max(_MIN_ENTRIES_COL_WIDTH, needed)

    def _panel_width(self) -> int:
        """Total width of the index + entries columns."""
        return self._index_col_width() + self._max_entries_col_width

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
                    self._max_entries_col_width = max(
                        self._max_entries_col_width,
                        self._compute_entries_col_width(),
                    )
                return

    def set_value(self, suffix: str, value: str) -> None:
        """Set a bucket's display value (called by emitter)."""
        m = _BUCKET_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if 0 <= idx < self.capacity:
                self._bucket_values[idx] = value
                self._max_entries_col_width = max(
                    self._max_entries_col_width,
                    self._compute_entries_col_width(),
                )

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

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Map ``'hm.bucket[2]'`` to the SVG center of that bucket row."""
        # Strip shape-name prefix if present
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        m = _BUCKET_RE.match(local)
        if m:
            idx = int(m.group("idx"))
            if 0 <= idx < self.capacity:
                index_col_w = self._index_col_width()
                entries_col_w = self._max_entries_col_width
                cx = _PADDING + index_col_w + entries_col_w / 2
                cy = _PADDING + idx * _ROW_HEIGHT + _ROW_HEIGHT / 2
                return (cx, cy)
        return None

    def bounding_box(self) -> BoundingBox:
        h = self.capacity * _ROW_HEIGHT + 2 * _PADDING
        w = self._panel_width() + 2 * _PADDING

        if self.label_text:
            h += 20

        arrow_above = arrow_height_above(
            self._annotations,
            self.resolve_annotation_point,
            cell_height=_ROW_HEIGHT,
        )
        h += arrow_above

        return BoundingBox(x=0, y=0, width=w, height=h)

    def emit_svg(
        self, *, render_inline_tex: Callable[[str], str] | None = None
    ) -> str:
        index_col_w = self._index_col_width()
        entries_col_w = self._max_entries_col_width
        total_w = index_col_w + entries_col_w

        effective_anns = self._annotations
        arrow_above = arrow_height_above(
            effective_anns,
            self.resolve_annotation_point,
            cell_height=_ROW_HEIGHT,
        )

        parts: list[str] = []
        parts.append(
            f'<g data-primitive="HashMap" '
            f'data-shape="{html_escape(self.name)}">'
        )

        # Shift content down so arrows curve into valid space above y=0
        if arrow_above > 0:
            parts.append(f'<g transform="translate(0, {arrow_above})">')

        # Emit arrowhead marker defs
        emit_arrow_marker_defs(parts, effective_anns)

        table_h = self.capacity * _ROW_HEIGHT

        # Outer border
        parts.append(
            f'<rect x="{_PADDING}" y="{_PADDING}" '
            f'width="{total_w}" height="{table_h}" '
            f'fill="none" stroke="{THEME["border"]}" stroke-width="1" rx="4"/>'
        )

        # Column divider between index and entries
        divider_x = _PADDING + index_col_w
        parts.append(
            f'<line x1="{divider_x}" y1="{_PADDING}" '
            f'x2="{divider_x}" y2="{_PADDING + table_h}" '
            f'stroke="{THEME["border"]}" stroke-width="1"/>'
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
                    f'x2="{_PADDING + total_w}" y2="{row_y}" '
                    f'stroke="{THEME["border"]}" stroke-width="0.5"/>'
                )

            # Index column background (always gray)
            parts.append(
                f'<rect x="{_PADDING}" y="{row_y}" '
                f'width="{index_col_w}" height="{_ROW_HEIGHT}" '
                f'fill="{THEME["bg_alt"]}" stroke="none"/>'
            )

            # Entries column background (state-colored)
            entries_x = _PADDING + index_col_w
            parts.append(
                f'<rect x="{entries_x}" y="{row_y}" '
                f'width="{entries_col_w}" height="{_ROW_HEIGHT}" '
                f'fill="{colors["fill"]}" stroke="none"/>'
            )

            # Index text (centered in index column)
            idx_tx = _PADDING + index_col_w // 2
            idx_ty = row_y + _ROW_HEIGHT // 2
            parts.append(
                _render_svg_text(
                    str(row_idx),
                    idx_tx,
                    idx_ty,
                    fill=THEME["fg_muted"],
                    font_size=_INDEX_FONT_SIZE,
                    text_anchor="middle",
                    dominant_baseline="central",
                    fo_width=index_col_w - 4,
                    fo_height=_ROW_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )

            # Entries text (left-aligned in entries column)
            entry_tx = entries_x + 8
            fo_w = entries_col_w - 16
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
                        fo_width=fo_w,
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
                    fill=THEME["fg_muted"],
                    css_class="scriba-primitive-label",
                    text_anchor="middle",
                    fo_width=bbox.width,
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
                target = ann.get("target", "")
                arrow_index = sum(
                    1 for j, a in enumerate(arrow_anns)
                    if a.get("target") == target and j < idx
                )
                emit_arrow_svg(
                    parts, ann, src, dst, arrow_index,
                    _ROW_HEIGHT, render_inline_tex,
                    placed_labels=placed,
                )

        # Close translate group if opened for arrow space
        if arrow_above > 0:
            parts.append("</g>")

        parts.append("</g>")
        return "".join(parts)
