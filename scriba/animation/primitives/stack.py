"""Stack primitive — variable-length LIFO with push/pop operations.

Supports vertical and horizontal orientations with animated push/pop
via ``\\apply`` commands.

See ``docs/primitives/stack.md`` for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives._text_metrics import measure_value_text, measure_text
from scriba.animation.primitives.base import (
    BoundingBox,
    PrimitiveBase,
    THEME,
    _escape_xml,
    _inset_rect_attrs,
    _render_svg_text,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)

from scriba.animation.primitives._protocol import register_primitive as _protocol_register

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
@_protocol_register
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
    # \apply structural verbs (push={label,value}, pop=N).
    APPLY_KEYS: ClassVar[frozenset[str]] = frozenset({"push", "pop"})

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "item[{i}]": "item by index",
        "top": "top of stack",
        "all": "all items",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "items",
        "orientation",
        "max_visible",
        "label",
    })

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
        # Annotation geometry (Layer B/C): linear layout; the cell height the
        # shared engine uses to offset pills/arrows from an item anchor.
        self._arrow_layout = "1d"
        self._arrow_cell_height = float(_CELL_HEIGHT)

    # ----- internal: dynamic sizing ----------------------------------------

    def _compute_cell_width(self) -> int:
        """Compute cell width from current item labels."""
        max_w = max(
            (measure_value_text(str(item.label), 14) for item in self.items),
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

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Center anchor for an ``item[i]`` (or ``top``) selector.

        Reuses the exact render-time positioning (orientation, reversed vertical
        order, and the ``max_visible`` window) so anchors track the drawn item.
        Items scrolled out of the visible window have no anchor. Stack annotations
        were previously dropped entirely (no resolver, no emit path).
        """
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        if _TOP_RE.match(local) and self.items:
            local = f"item[{len(self.items) - 1}]"
        m = _ITEM_RE.match(local)
        if not m:
            return None
        idx = int(m.group("idx"))
        n = len(self.items)
        if not (0 <= idx < n):
            return None
        visible_count = min(n, self.max_visible)
        start_idx = max(0, n - visible_count)
        if idx < start_idx:
            return None  # scrolled out of the visible window
        vi = idx - start_idx
        cw = self._cell_width
        if self.orientation == "horizontal":
            x = _PADDING + vi * (cw + _CELL_GAP)
            y = _PADDING
        else:
            rev_vi = (visible_count - 1) - vi
            x = _PADDING
            y = _PADDING + rev_vi * (_CELL_HEIGHT + _CELL_GAP)
        return (float(x + cw / 2), float(y + _CELL_HEIGHT / 2))

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit below the whole stack (callout lane),
        clear of the cells. Orientation-dependent: the content bottom is one
        cell row for horizontal, the visible-window column height for vertical
        — mirrors :meth:`bounding_box`'s content height per orientation."""
        visible = min(len(self.items), self.max_visible) or 1
        if self.orientation == "horizontal":
            return float(_CELL_HEIGHT + 2 * _PADDING)
        return float(visible * (_CELL_HEIGHT + _CELL_GAP) - _CELL_GAP + 2 * _PADDING)

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

        # Layer A: fold the (wrapped) caption width into the footprint.
        content_w = w
        core_w = max(w, self._caption_block_width(content_w))
        h += self._caption_block_height(content_w)

        # Layer B/C: reserve space for annotation arrows + position pills.
        # No annotations -> all terms are 0, so the box is byte-stable.
        arrow_above = self._reserved_arrow_above()
        h += arrow_above
        # Layer C: below-pill callout lane sits below the content + caption.
        h += self._below_lane_height()

        # #1: reserve horizontal room for position=left/right pills. Both pads
        # are 0 (int) without left/right pills, so the box stays byte-stable.
        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)

        return BoundingBox(x=0, y=0, width=w, height=h)

    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        parts: list[str] = []
        parts.append(
            f'<g data-primitive="stack" data-shape="{_escape_xml(self.name)}">'
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
                f'fill="{THEME["fg_dim"]}" '
                f'style="font-size:11px">'
                f'empty</text>'
            )
            parts.append("</g>")
            return "".join(parts)

        # Reserve space above for annotation arrows/pills and shift content down.
        # No annotations -> arrow_above is 0 and no group opens (byte-stable).
        effective_anns = self._annotations
        arrow_above = self._reserved_arrow_above()
        # #1: shift content right to make room for position=left pills (0 when
        # none → "translate(0, …)", byte-identical to the pre-#1 output).
        left_pad, _right = self._h_label_pad()
        if arrow_above > 0 or left_pad > 0:
            parts.append(f'  <g transform="translate({left_pad}, {arrow_above})">')

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
                f'<g data-target="{_escape_xml(target)}" '
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
                f'fill="{THEME["fg_muted"]}" '
                f'style="font-size:11px">'
                f'+{overflow} more</text>'
            )

        # Caption
        if self.label is not None:
            visible = min(len(self.items), self.max_visible) or 1
            cw = self._cell_width
            if self.orientation == "horizontal":
                content_w = visible * (cw + _CELL_GAP) - _CELL_GAP + 2 * _PADDING
            else:
                content_w = cw + 2 * _PADDING
            bbox = self.bounding_box()
            self._emit_caption(
                parts,
                content_width=content_w,
                footprint_width=int(bbox.width),
                top_y=int(bbox.height - self._caption_block_height(content_w)),
                render_inline_tex=render_inline_tex,
            )

        # Annotations (arrows + position pills) via the shared engine, inside
        # the translate group so anchors share the content frame (Layer B/C).
        if effective_anns:
            self.emit_annotation_arrows(
                parts,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
            )

        if arrow_above > 0 or left_pad > 0:
            parts.append("  </g>")
        parts.append("</g>")
        return "".join(parts)

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []
