"""Queue primitive — fixed-capacity horizontal FIFO with front/rear pointers.

Supports enqueue/dequeue operations via ``\\apply`` commands.  Front and
rear pointers are rendered as small triangular arrows above the cells.

See ``docs/archive/PRIMITIVES-PLAN.md`` §1 for the design specification.
"""

from __future__ import annotations

import re
from html import escape as html_escape
from typing import Any, Callable

from scriba.animation.primitives.base import (
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    INDEX_LABEL_OFFSET,
    BoundingBox,
    PrimitiveBase,
    _render_svg_text,
    svg_style_attrs,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_POINTER_HEIGHT = 20  # vertical space for pointer arrows above cells
_POINTER_LABEL_GAP = 14  # gap between pointer triangle and its label text
_POINTER_TRIANGLE_SIZE = 8  # half-width of the pointer triangle
_DEFAULT_CAPACITY = 8

# ---------------------------------------------------------------------------
# Selector regexes (suffix-only, without shape name prefix)
# ---------------------------------------------------------------------------

_CELL_RE = re.compile(r"^cell\[(?P<idx>\d+)\]$")
_FRONT_RE = re.compile(r"^front$")
_REAR_RE = re.compile(r"^rear$")
_ALL_RE = re.compile(r"^all$")

# ---------------------------------------------------------------------------
# Queue primitive
# ---------------------------------------------------------------------------


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

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        self.capacity: int = int(params.get("capacity", _DEFAULT_CAPACITY))
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

        if dequeue_val is not None:
            if self.front_idx < self.rear_idx:
                self.cells[self.front_idx] = ""
                self.front_idx += 1

        # Direct cell value assignment (handled by scene.py _apply_apply)

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

    def bounding_box(self) -> BoundingBox:
        w = self._total_width()
        h = _POINTER_HEIGHT + _POINTER_LABEL_GAP + CELL_HEIGHT + INDEX_LABEL_OFFSET
        if self.label_text:
            h += 20
        return BoundingBox(x=0, y=0, width=w, height=h)

    def emit_svg(
        self, *, render_inline_tex: Callable[[str], str] | None = None
    ) -> str:
        parts: list[str] = []
        parts.append(
            f'<g data-primitive="queue" data-shape="{html_escape(self.name)}">'
        )

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

            colors = svg_style_attrs(state_name)
            stroke_w = "1.5" if state_name == "idle" else "2"

            x = i * (CELL_WIDTH + CELL_GAP)
            value = self.cells[i]

            parts.append(
                f'  <g data-target="{html_escape(target)}" '
                f'class="scriba-state-{state_name}">'
            )
            parts.append(
                f'    <rect x="{x}" y="{cell_y}" '
                f'width="{CELL_WIDTH}" height="{CELL_HEIGHT}" '
                f'rx="4" fill="{colors["fill"]}" '
                f'stroke="{colors["stroke"]}" stroke-width="{stroke_w}"/>'
            )
            text_x = x + CELL_WIDTH // 2
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
                    fo_width=CELL_WIDTH,
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
                    fill="#6c757d",
                    css_class="scriba-index-label idx",
                    text_anchor="middle",
                    dominant_baseline="central",
                    font_size="11",
                )
            )

        # --- Render front pointer arrow ---
        self._emit_pointer(
            parts,
            index=self.front_idx,
            label="front",
            cell_y=cell_y,
            render_inline_tex=render_inline_tex,
        )

        # --- Render rear pointer arrow ---
        self._emit_pointer(
            parts,
            index=self.rear_idx - 1 if self.rear_idx > 0 else 0,
            label="rear",
            cell_y=cell_y,
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
                    fill="#6c757d",
                    css_class="scriba-primitive-label",
                    text_anchor="middle",
                    fo_width=bbox.width,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
            )

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
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> None:
        """Emit a downward-pointing triangle arrow above a cell with a label.

        The pointer is rendered above the cell at *index*.  If *index* is
        out of range (can happen when queue is empty), it is clamped.
        """
        # Clamp index to valid cell range
        idx = max(0, min(index, self.capacity - 1))

        target = f"{self.name}.{label}"
        state_name = self.get_state(label)
        colors = svg_style_attrs(state_name)

        cell_center_x = idx * (CELL_WIDTH + CELL_GAP) + CELL_WIDTH // 2

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

        pointer_color = colors["stroke"] if state_name != "idle" else "#6c757d"

        parts.append(
            f'  <g data-target="{html_escape(target)}" '
            f'class="scriba-state-{state_name}">'
        )
        parts.append(
            f'    <polygon points="{triangle_points}" '
            f'fill="{pointer_color}" stroke="none"/>'
        )

        # Label text above the triangle
        label_y = tri_top_y - 4
        parts.append(
            "    "
            + _render_svg_text(
                label,
                cell_center_x,
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
        return self.capacity * CELL_WIDTH + (self.capacity - 1) * CELL_GAP
