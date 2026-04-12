"""Queue primitive — fixed-capacity horizontal FIFO with front/rear pointers.

Supports enqueue/dequeue operations via ``\\apply`` commands.  Front and
rear pointers are rendered as small triangular arrows above the cells.

See ``docs/archive/PRIMITIVES-PLAN.md`` §1 for the design specification.
"""

from __future__ import annotations

import re
from html import escape as html_escape
from typing import Any, Callable, ClassVar

from scriba.animation.errors import E1103, animation_error
from scriba.animation.primitives.base import (
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
    emit_arrow_marker_defs,
    emit_arrow_svg,
    estimate_text_width,
    register_primitive,
    svg_style_attrs,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_POINTER_HEIGHT = 20  # vertical space for pointer arrows above cells
_POINTER_LABEL_GAP = 14  # gap between pointer triangle and its label text
_POINTER_TRIANGLE_SIZE = 8  # half-width of the pointer triangle
_DEFAULT_CAPACITY = 8
_LABEL_PADDING = 20  # horizontal padding for pointer labels extending beyond cells

# ---------------------------------------------------------------------------
# Selector regexes (suffix-only, without shape name prefix)
# ---------------------------------------------------------------------------

_CELL_RE = re.compile(r"^cell\[(?P<idx>\d+)\]$")
_FRONT_RE = re.compile(r"^front$")
_REAR_RE = re.compile(r"^rear$")
_ALL_RE = re.compile(r"^all$")

# Full-qualified selector regex (with shape name prefix) for annotation points
_FULL_CELL_RE = re.compile(r"^(?P<name>\w+)\.cell\[(?P<idx>\d+)\]$")


def _is_truthy_flag(value: Any) -> bool:
    """Return True only when *value* is an explicit truthy boolean flag.

    The parser normalises ``true``/``false`` literals to Python booleans,
    but defensive callers may still pass through raw strings.  We accept
    ``True`` and case-insensitive ``"true"``; everything else —
    including ``False``, ``None``, ``"false"``, ``0``, and ``""`` — is
    treated as "not set".
    """
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() == "true":
        return True
    return False

# ---------------------------------------------------------------------------
# Queue primitive
# ---------------------------------------------------------------------------


@register_primitive("Queue")
class Queue(PrimitiveBase):
    """Fixed-capacity FIFO queue with front/rear pointer visualisation.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``q``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
        Recognised keys: ``capacity``, ``data``, ``label``.
    """

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "cell[{i}]": "cell by index",
        "front": "front pointer",
        "rear": "rear pointer",
        "all": "all cells and pointers",
    }

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        self.capacity: int = int(params.get("capacity", _DEFAULT_CAPACITY))
        if self.capacity < 1:
            raise animation_error(
                "E1440",
                detail=(
                    f"Queue capacity {self.capacity} is out of range; "
                    "valid: positive integer"
                ),
            )
        self.label_text: str | None = params.get("label")

        # Internal data store — one slot per capacity position
        self.cells: list[Any] = [""] * self.capacity

        # Populate initial data
        raw_data: list[Any] = list(params.get("data", []))
        for i, val in enumerate(raw_data):
            if i < self.capacity:
                self.cells[i] = val

        # Front/rear indices
        self.front_idx: int = 0
        self.rear_idx: int = len(raw_data)  # points one past the last element

        # Dynamic cell width: at least CELL_WIDTH, wider if content requires it
        self._cell_width: int = max(
            CELL_WIDTH,
            max(
                (estimate_text_width(str(v), 14) + 12 for v in raw_data),
                default=CELL_WIDTH,
            ),
        )

        self.primitive_type: str = "queue"

    # ----- apply commands --------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Process enqueue/dequeue/value commands from ``\\apply``.

        *target_suffix* is the part after ``<name>.`` — either empty string
        (whole-queue operations like enqueue/dequeue) or ``cell[i]`` for
        direct value assignment.

        Supported params on the queue itself:
        - ``enqueue=<value>`` — add element at rear, advance rear pointer
        - ``dequeue=true`` — remove element at front, advance front pointer

        Supported params on ``cell[i]``:
        - ``value=<X>`` — set cell value directly
        """
        # Whole-queue operations (target is the queue name itself)
        enqueue_val = params.get("enqueue")
        dequeue_val = params.get("dequeue")

        if enqueue_val is not None:
            if self.rear_idx < self.capacity:
                self.cells[self.rear_idx] = enqueue_val
                self.rear_idx += 1
                # Widen cells if the new value is wider than current cell width
                new_w = estimate_text_width(str(enqueue_val), 14) + 12
                if new_w > self._cell_width:
                    self._cell_width = new_w

        # ``dequeue`` must act only on an explicit truthy value.  Accept
        # both Python ``True`` (from the parser's bool coercion) and the
        # literal string "true" (in case a raw token ever reaches us).
        # ``dequeue=false``, ``dequeue=0`` and ``dequeue=None`` must NOT
        # trigger a dequeue — previously we keyed off ``is not None``
        # which turned ``dequeue=false`` into a silent no-op bug.
        if _is_truthy_flag(dequeue_val):
            if self.front_idx < self.rear_idx:
                self.cells[self.front_idx] = ""
                self.front_idx += 1

        # Direct cell value assignment (handled by scene.py _apply_apply)

    def set_value(self, suffix: str, value: str) -> None:
        """Set a cell's display value (called by emitter)."""
        m = _CELL_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if 0 <= idx < self.capacity:
                self.cells[idx] = value
                # Recalc cell width if new value is wider
                needed = estimate_text_width(str(value), 14) + 12
                if needed > self._cell_width:
                    self._cell_width = needed

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for i in range(self.capacity):
            parts.append(f"cell[{i}]")
        parts.append("front")
        parts.append("rear")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix in ("all", "front", "rear"):
            return True

        m = _CELL_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return 0 <= idx < self.capacity

        return False

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG (x, y) center for an annotation selector.

        Supports ``"<name>.cell[<i>]"`` selectors.
        Returns the top-center of the cell so arrows curve above.
        """
        m = _FULL_CELL_RE.match(selector)
        if m and m.group("name") == self.name:
            idx = int(m.group("idx"))
            if 0 <= idx < self.capacity:
                cell_y = _POINTER_HEIGHT + _POINTER_LABEL_GAP
                x = _LABEL_PADDING + idx * (self._cell_width + CELL_GAP) + self._cell_width // 2
                y = cell_y  # top edge of cell
                return (float(x), float(y))
        return None

    def bounding_box(self) -> BoundingBox:
        w = self._total_width() + 2 * _LABEL_PADDING
        h = _POINTER_HEIGHT + _POINTER_LABEL_GAP + CELL_HEIGHT + INDEX_LABEL_OFFSET
        if self.label_text:
            h += 20
        arrow_above = arrow_height_above(
            self._annotations, self.resolve_annotation_point,
            cell_height=CELL_HEIGHT,
        )
        h += arrow_above
        return BoundingBox(x=0, y=0, width=w, height=h)

    def emit_svg(
        self, *, render_inline_tex: Callable[[str], str] | None = None
    ) -> str:
        effective_anns = self._annotations

        # Compute vertical space needed above content for arrow curves
        arrow_above = arrow_height_above(
            effective_anns, self.resolve_annotation_point,
            cell_height=CELL_HEIGHT,
        )

        parts: list[str] = []
        parts.append(
            f'<g data-primitive="queue" data-shape="{html_escape(self.name)}">'
        )

        # Shift all content down so arrows curve into valid space above y=0
        if arrow_above > 0:
            parts.append(f'  <g transform="translate(0, {arrow_above})">')

        # Emit arrowhead marker defs for annotation arrows
        ann_arrow_lines: list[str] = []
        emit_arrow_marker_defs(ann_arrow_lines, effective_anns)
        if ann_arrow_lines:
            parts.append("\n".join(ann_arrow_lines))

        # Y offset: leave room for pointer arrows above cells
        cell_y = _POINTER_HEIGHT + _POINTER_LABEL_GAP

        # --- Render cells ---
        for i in range(self.capacity):
            suffix = f"cell[{i}]"
            target = f"{self.name}.{suffix}"

            state_name = self.get_state(suffix)
            # "all" selector propagates to individual cells
            all_state = self.get_state("all")
            if all_state != "idle" and state_name == "idle":
                state_name = all_state

            # β redesign — highlight is a standalone state.
            highlighted = suffix in self._highlighted
            if highlighted and state_name == "idle":
                effective_state = "highlight"
            else:
                effective_state = state_name

            colors = svg_style_attrs(effective_state)

            x = _LABEL_PADDING + i * (self._cell_width + CELL_GAP)
            value = self.cells[i]

            parts.append(
                f'  <g data-target="{html_escape(target)}" '
                f'class="scriba-state-{effective_state}">'
            )
            rect_attrs = _inset_rect_attrs(
                x, cell_y, self._cell_width, CELL_HEIGHT
            )
            parts.append(
                f'    <rect x="{rect_attrs["x"]}" y="{rect_attrs["y"]}" '
                f'width="{rect_attrs["width"]}" '
                f'height="{rect_attrs["height"]}"/>'
            )
            text_x = x + self._cell_width // 2
            text_y = cell_y + CELL_HEIGHT // 2
            parts.append(
                "    "
                + _render_svg_text(
                    value,
                    text_x,
                    text_y,
                    fill=colors["text"],
                    text_anchor="middle",
                    dominant_baseline="central",
                    fo_width=self._cell_width,
                    fo_height=CELL_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )
            parts.append("  </g>")

            # Index label below the cell
            idx_label_y = cell_y + CELL_HEIGHT + INDEX_LABEL_OFFSET
            parts.append(
                "  "
                + _render_svg_text(
                    f"[{i}]",
                    text_x,
                    idx_label_y,
                    fill=THEME["fg_muted"],
                    css_class="scriba-index-label idx",
                    text_anchor="middle",
                    dominant_baseline="central",
                    font_size="11",
                )
            )

        # Compute the cell index where the rear pointer arrow is drawn.
        # rear_idx is one past the last occupied cell; display at the last
        # occupied cell (rear_idx - 1), clamping to 0 for an empty queue.
        rear_display = max(self.rear_idx - 1, 0)
        # Clamp front_idx the same way _emit_pointer does before comparing,
        # so we detect overlap when both pointers land on the same cell
        # (e.g., empty queue where front_idx >= capacity).
        front_display = max(0, min(self.front_idx, self.capacity - 1))
        pointers_overlap = front_display == rear_display

        # --- Render front pointer arrow ---
        self._emit_pointer(
            parts,
            index=self.front_idx,
            label="front",
            cell_y=cell_y,
            offset_label=pointers_overlap,
            render_inline_tex=render_inline_tex,
        )

        # --- Render rear pointer arrow ---
        self._emit_pointer(
            parts,
            index=rear_display,
            label="rear",
            cell_y=cell_y,
            offset_label=pointers_overlap,
            render_inline_tex=render_inline_tex,
        )

        # --- Caption label ---
        if self.label_text is not None:
            bbox = self.bounding_box()
            cx = bbox.width // 2
            cy = bbox.height - 4
            parts.append(
                "  "
                + _render_svg_text(
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

        # Annotation arrow rendering
        arrow_anns = [a for a in effective_anns if a.get("arrow_from")]
        if arrow_anns:
            arrow_lines: list[str] = []
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
                        arrow_lines, ann, src, dst, arrow_index,
                        CELL_HEIGHT, render_inline_tex,
                    )
            parts.extend(arrow_lines)

        # Close the translate group if we opened one for arrow space
        if arrow_above > 0:
            parts.append("  </g>")

        parts.append("</g>")
        return "\n".join(parts)

    # ----- internal helpers ------------------------------------------------

    def _emit_pointer(
        self,
        parts: list[str],
        *,
        index: int,
        label: str,
        cell_y: int,
        offset_label: bool = False,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> None:
        """Emit a downward-pointing triangle arrow above a cell with a label.

        The pointer is rendered above the cell at *index*.  If *index* is
        out of range (can happen when queue is empty), it is clamped.

        When *offset_label* is True the label is nudged horizontally so that
        two overlapping pointers (front and rear on the same cell) remain
        readable.  "front" is nudged left, "rear" is nudged right.
        """
        # Clamp index to valid cell range
        idx = max(0, min(index, self.capacity - 1))

        target = f"{self.name}.{label}"
        state_name = self.get_state(label)
        colors = svg_style_attrs(state_name)

        cell_center_x = _LABEL_PADDING + idx * (self._cell_width + CELL_GAP) + self._cell_width // 2

        # Triangle tip points down, touching the top of the cell
        tip_y = cell_y - 2
        tri_top_y = tip_y - _POINTER_TRIANGLE_SIZE
        tri_left_x = cell_center_x - _POINTER_TRIANGLE_SIZE
        tri_right_x = cell_center_x + _POINTER_TRIANGLE_SIZE

        triangle_points = (
            f"{tri_left_x},{tri_top_y} "
            f"{tri_right_x},{tri_top_y} "
            f"{cell_center_x},{tip_y}"
        )

        pointer_color = colors["stroke"] if state_name != "idle" else THEME["fg_muted"]

        parts.append(
            f'  <g data-target="{html_escape(target)}" '
            f'class="scriba-state-{state_name}">'
        )
        parts.append(
            f'    <polygon points="{triangle_points}" '
            f'fill="{pointer_color}" stroke="none"/>'
        )

        # Label text above the triangle
        label_y = tri_top_y - 6
        # Nudge label horizontally when front/rear share a cell
        label_x = cell_center_x
        if offset_label:
            nudge = self._cell_width // 2
            label_x += -nudge if label == "front" else nudge
        parts.append(
            "    "
            + _render_svg_text(
                label,
                label_x,
                label_y,
                fill=pointer_color,
                text_anchor="middle",
                dominant_baseline="auto",
                font_size="11",
                font_weight="600",
                render_inline_tex=render_inline_tex,
            )
        )
        parts.append("  </g>")

    def _total_width(self) -> int:
        if self.capacity == 0:
            return 0
        return self.capacity * self._cell_width + (self.capacity - 1) * CELL_GAP
