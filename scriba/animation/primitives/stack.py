"""Stack primitive — variable-length LIFO with push/pop operations.

Supports vertical and horizontal orientations with animated push/pop
via ``\\apply`` commands.

See ``docs/primitives/stack.md`` for the authoritative specification.
"""

from __future__ import annotations

import re
from html import escape as html_escape
from typing import Any, Callable, ClassVar

from scriba.animation.errors import E1103, _animation_error
from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    THEME,
    _inset_rect_attrs,
    _render_svg_text,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CELL_WIDTH = 80
_CELL_HEIGHT = 36
_CELL_GAP = 4
_PADDING = 8
_DEFAULT_MAX_VISIBLE = 10

# ---------------------------------------------------------------------------
# Stack item
# ---------------------------------------------------------------------------


class StackItem:
    """A single item on the stack."""

    __slots__ = ("label", "value")

    def __init__(self, label: str, value: Any = None) -> None:
        self.label = label
        self.value = value

    def __repr__(self) -> str:
        return f"StackItem({self.label!r})"


# ---------------------------------------------------------------------------
# Selector regex
# ---------------------------------------------------------------------------

_ITEM_RE = re.compile(r"^item\[(?P<idx>\d+)\]$")
_TOP_RE = re.compile(r"^top$")
_ALL_RE = re.compile(r"^all$")

# ---------------------------------------------------------------------------
# Stack primitive
# ---------------------------------------------------------------------------


@register_primitive("Stack")
class Stack(PrimitiveBase):
    """Variable-length LIFO stack primitive.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``s``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
        Optional keys: ``items``, ``orientation``, ``max_visible``, ``label``.
    """

    primitive_type = "stack"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "item[{i}]": "item by index",
        "top": "top of stack",
        "all": "all items",
    }

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        self.orientation: str = str(params.get("orientation", "vertical"))
        self.max_visible: int = int(params.get("max_visible", _DEFAULT_MAX_VISIBLE))
        if self.max_visible < 1:
            raise _animation_error(
                "E1441",
                detail=(
                    f"Stack max_visible {self.max_visible} is out of "
                    "range; valid: positive integer"
                ),
            )
        self.label: str | None = params.get("label")

        # Initialize items from params
        raw_items = params.get("items", [])
        self.items: list[StackItem] = []
        for item in raw_items:
            if isinstance(item, dict):
                self.items.append(
                    StackItem(
                        label=str(item.get("label", "")),
                        value=item.get("value"),
                    )
                )
            else:
                self.items.append(StackItem(label=str(item)))

        self._cell_width: int = self._compute_cell_width()

    # ----- internal: dynamic sizing ----------------------------------------

    def _compute_cell_width(self) -> int:
        """Compute cell width from current item labels."""
        max_w = max(
            (estimate_text_width(str(item.label), 14) for item in self.items),
            default=0,
        )
        return max(_CELL_WIDTH, max_w + 16)

    # ----- apply commands --------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Process push/pop commands from ``\\apply``.

        Supported params:
        - ``push="label"`` or ``push={"label": "text", "value": 1.0}``
        - ``pop=N`` removes N items from the top
        """
        push_val = params.get("push")
        pop_val = params.get("pop")

        if push_val is not None:
            if isinstance(push_val, dict):
                self.items.append(
                    StackItem(
                        label=str(push_val.get("label", "")),
                        value=push_val.get("value"),
                    )
                )
            else:
                self.items.append(StackItem(label=str(push_val)))

        if pop_val is not None:
            count = int(pop_val)
            for _ in range(min(count, len(self.items))):
                self.items.pop()

        # Recalculate after any push/pop (monotonic: never shrink)
        self._cell_width = max(self._cell_width, self._compute_cell_width())

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for i in range(len(self.items)):
            parts.append(f"item[{i}]")
        if self.items:
            parts.append("top")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True
        if suffix == "top":
            return len(self.items) > 0

        m = _ITEM_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return 0 <= idx < len(self.items)

        return False

    def bounding_box(self) -> BoundingBox:
        visible = min(len(self.items), self.max_visible)
        if visible == 0:
            visible = 1  # minimum space

        cw = self._cell_width
        if self.orientation == "horizontal":
            w = visible * (cw + _CELL_GAP) - _CELL_GAP + 2 * _PADDING
            h = _CELL_HEIGHT + 2 * _PADDING
        else:
            w = cw + 2 * _PADDING
            h = visible * (_CELL_HEIGHT + _CELL_GAP) - _CELL_GAP + 2 * _PADDING

        if self.label:
            h += 20

        return BoundingBox(x=0, y=0, width=w, height=h)

    def emit_svg(self, *, render_inline_tex: Callable[[str], str] | None = None) -> str:
        parts: list[str] = []
        parts.append(
            f'<g data-primitive="stack" data-shape="{html_escape(self.name)}">'
        )

        cw = self._cell_width
        if not self.items:
            # Empty stack placeholder
            parts.append(
                f'<rect x="{_PADDING}" y="{_PADDING}" '
                f'width="{cw}" height="{_CELL_HEIGHT}" '
                f'fill="{THEME["bg"]}" stroke="{THEME["border"]}" stroke-width="1" '
                f'stroke-dasharray="4 2" rx="4"/>'
            )
            parts.append(
                f'<text x="{_PADDING + cw // 2}" '
                f'y="{_PADDING + _CELL_HEIGHT // 2}" '
                f'text-anchor="middle" dominant-baseline="central" '
                f'fill="{THEME["fg_dim"]}" font-size="11">empty</text>'
            )
            parts.append("</g>")
            return "".join(parts)

        visible_count = min(len(self.items), self.max_visible)
        # Show the top N items (most recent at top in vertical)
        start_idx = max(0, len(self.items) - visible_count)

        hl_suffixes = getattr(self, "_highlighted", set())

        for vi, idx in enumerate(range(start_idx, len(self.items))):
            item = self.items[idx]
            suffix = f"item[{idx}]"
            target = f"{self.name}.{suffix}"

            state = self.get_state(suffix)
            # "top" selector maps to the last item
            if idx == len(self.items) - 1:
                top_state = self.get_state("top")
                if top_state != "idle":
                    state = top_state

            is_hl = suffix in hl_suffixes or (
                idx == len(self.items) - 1 and "top" in hl_suffixes
            )
            # β redesign — highlight becomes a standalone state; it only
            # promotes an ``idle`` cell so a ``current`` item still wins.
            if is_hl and state == "idle":
                effective_state = "highlight"
            else:
                effective_state = state

            colors = svg_style_attrs(effective_state)

            if self.orientation == "horizontal":
                x = _PADDING + vi * (cw + _CELL_GAP)
                y = _PADDING
            else:
                # Vertical: top of stack (most recent) at the top
                # Reverse visual order so newest is at top
                rev_vi = (visible_count - 1) - vi
                x = _PADDING
                y = _PADDING + rev_vi * (_CELL_HEIGHT + _CELL_GAP)

            parts.append(
                f'<g data-target="{html_escape(target)}" '
                f'class="{state_class(effective_state)}">'
            )
            rect_attrs = _inset_rect_attrs(x, y, cw, _CELL_HEIGHT)
            parts.append(
                f'<rect x="{rect_attrs["x"]}" y="{rect_attrs["y"]}" '
                f'width="{rect_attrs["width"]}" '
                f'height="{rect_attrs["height"]}"/>'
            )
            tx = x + cw // 2
            ty = y + _CELL_HEIGHT // 2
            parts.append(
                _render_svg_text(
                    str(item.label),
                    tx,
                    ty,
                    fill=colors["text"],
                    text_anchor="middle",
                    dominant_baseline="central",
                    fo_width=cw,
                    fo_height=_CELL_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )

            parts.append("</g>")

        # Overflow indicator
        if len(self.items) > self.max_visible:
            overflow = len(self.items) - self.max_visible
            if self.orientation == "horizontal":
                ox = _PADDING + visible_count * (cw + _CELL_GAP)
                oy = _PADDING + _CELL_HEIGHT // 2
            else:
                ox = _PADDING + cw // 2
                oy = _PADDING + visible_count * (_CELL_HEIGHT + _CELL_GAP)
            parts.append(
                f'<text x="{ox}" y="{oy}" '
                f'text-anchor="middle" dominant-baseline="central" '
                f'fill="{THEME["fg_muted"]}" font-size="11">+{overflow} more</text>'
            )

        # Caption
        if self.label is not None:
            bbox = self.bounding_box()
            cx = bbox.width // 2
            cy = bbox.height - 4
            parts.append(
                _render_svg_text(
                    str(self.label),
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

        parts.append("</g>")
        return "".join(parts)
