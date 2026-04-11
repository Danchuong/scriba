"""LinkedList primitive — node boxes with pointer arrows.

Visualises a singly-linked list as a horizontal chain of two-part
node boxes connected by directional arrows.

Visual layout::

    ┌───┬───┐    ┌───┬───┐    ┌───┬───┐
    │ 3 │ ●─┼───→│ 7 │ ●─┼───→│ 1 │ ╱ │
    └───┴───┘    └───┴───┘    └───┴───┘
     node[0]      node[1]      node[2]

See ``docs/archive/PRIMITIVES-PLAN.md`` §2 for the authoritative spec.
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
# Layout constants
# ---------------------------------------------------------------------------

_VALUE_WIDTH = 50  # left half of the node (value display)
_PTR_WIDTH = 30  # right half of the node (pointer indicator)
_NODE_WIDTH = _VALUE_WIDTH + _PTR_WIDTH  # total node width = 80
_NODE_HEIGHT = 40
_LINK_GAP = 30  # horizontal gap between nodes (arrow space)
_PADDING = 12
_INDEX_LABEL_OFFSET = 16  # vertical offset below the node for index labels
_CORNER_RADIUS = 4
_ARROWHEAD_SIZE = 8

# ---------------------------------------------------------------------------
# Selector regexes (applied against the suffix after ``name.``)
# ---------------------------------------------------------------------------

_NODE_RE = re.compile(r"^node\[(?P<idx>\d+)\]$")
_LINK_RE = re.compile(r"^link\[(?P<idx>\d+)\]$")
_ALL_RE = re.compile(r"^all$")

# ---------------------------------------------------------------------------
# LinkedList primitive
# ---------------------------------------------------------------------------


class LinkedList(PrimitiveBase):
    """Singly-linked list visualisation primitive.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``ll``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
        Recognised keys: ``data`` (list of values), ``label``.
    """

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        raw_data = params.get("data", [])
        if isinstance(raw_data, str):
            # Handle stringified list — e.g. "[3,7,1]"
            raw_data = raw_data.strip()
            if raw_data.startswith("[") and raw_data.endswith("]"):
                import json

                raw_data = json.loads(raw_data)
            else:
                raw_data = [raw_data]

        self.values: list[Any] = list(raw_data)
        self.label_text: str | None = params.get("label")
        self.primitive_type: str = "linkedlist"

    # ----- apply commands --------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Process insert / remove / value-set commands.

        Supported params
        ~~~~~~~~~~~~~~~~
        - ``insert={"index": i, "value": v}`` — insert a node at *index*.
        - ``remove=i`` — remove node at *index*.
        - ``value=X`` (on a node selector) — handled by the renderer
          directly via state; listed here for documentation.
        """
        insert_val = params.get("insert")
        remove_val = params.get("remove")

        if insert_val is not None:
            if isinstance(insert_val, dict):
                idx = int(insert_val.get("index", len(self.values)))
                val = insert_val.get("value", "")
            else:
                idx = len(self.values)
                val = insert_val
            self.values.insert(idx, val)

        if remove_val is not None:
            idx = int(remove_val)
            if 0 <= idx < len(self.values):
                self.values.pop(idx)

    def set_value(self, suffix: str, value: str) -> None:
        """Set a node's display value (called by emitter)."""
        m = _NODE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if 0 <= idx < len(self.values):
                self.values[idx] = value

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = []
        for i in range(len(self.values)):
            parts.append(f"node[{i}]")
        # Links connect node[i] → node[i+1]; last node has no outgoing link
        for i in range(max(0, len(self.values) - 1)):
            parts.append(f"link[{i}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True

        m = _NODE_RE.match(suffix)
        if m:
            return 0 <= int(m.group("idx")) < len(self.values)

        m = _LINK_RE.match(suffix)
        if m:
            return 0 <= int(m.group("idx")) < len(self.values) - 1

        return False

    def bounding_box(self) -> BoundingBox:
        n = max(len(self.values), 1)
        w = (
            2 * _PADDING
            + n * _NODE_WIDTH
            + (n - 1) * _LINK_GAP
        )
        h = 2 * _PADDING + _NODE_HEIGHT + _INDEX_LABEL_OFFSET
        if self.label_text:
            h += 20
        return BoundingBox(x=0, y=0, width=w, height=h)

    # ----- SVG rendering ---------------------------------------------------

    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> str:
        parts: list[str] = []
        parts.append(
            f'<g data-primitive="linkedlist"'
            f' data-shape="{html_escape(self.name)}">'
        )

        # --- Arrowhead marker definition ---
        marker_id = f"arrowhead-{html_escape(self.name)}"
        parts.append("<defs>")
        parts.append(
            f'<marker id="{marker_id}" markerWidth="{_ARROWHEAD_SIZE}"'
            f' markerHeight="{_ARROWHEAD_SIZE}" refX="{_ARROWHEAD_SIZE}"'
            f' refY="{_ARROWHEAD_SIZE // 2}" orient="auto"'
            f' markerUnits="userSpaceOnUse">'
            f'<path d="M0,0 L{_ARROWHEAD_SIZE},{_ARROWHEAD_SIZE // 2}'
            f" L0,{_ARROWHEAD_SIZE} Z\""
            f' fill="#d0d7de" class="scriba-ll-arrowhead"/>'
            f"</marker>"
        )
        parts.append("</defs>")

        if not self.values:
            # Empty list placeholder
            parts.append(
                f'<rect x="{_PADDING}" y="{_PADDING}"'
                f' width="{_NODE_WIDTH}" height="{_NODE_HEIGHT}"'
                f' fill="#f6f8fa" stroke="#d0d7de" stroke-width="1"'
                f' stroke-dasharray="4 2" rx="{_CORNER_RADIUS}"/>'
            )
            parts.append(
                f'<text x="{_PADDING + _NODE_WIDTH // 2}"'
                f' y="{_PADDING + _NODE_HEIGHT // 2}"'
                f' text-anchor="middle" dominant-baseline="central"'
                f' fill="#adb5bd" font-size="11">empty</text>'
            )
            parts.append("</g>")
            return "".join(parts)

        node_count = len(self.values)

        # --- Render link arrows first (below nodes visually) ---
        for i in range(node_count - 1):
            link_suffix = f"link[{i}]"
            link_target = f"{self.name}.{link_suffix}"
            link_state = self.get_state(link_suffix)
            link_colors = svg_style_attrs(link_state)

            # Arrow starts from the pointer dot (centred in the ptr area)
            x_start = (
                _PADDING
                + i * (_NODE_WIDTH + _LINK_GAP)
                + _VALUE_WIDTH
                + _PTR_WIDTH // 2
            )
            # Arrow ends at the left edge of node[i+1]
            x_end = (
                _PADDING
                + (i + 1) * (_NODE_WIDTH + _LINK_GAP)
            )
            y_mid = _PADDING + _NODE_HEIGHT // 2

            stroke_color = link_colors["stroke"]
            stroke_w = "1.5" if link_state == "idle" else "2.5"

            # Update arrowhead color via a per-link marker when non-idle
            if link_state != "idle":
                link_marker_id = f"arrowhead-{html_escape(self.name)}-{i}"
                parts.append(
                    f'<defs><marker id="{link_marker_id}"'
                    f' markerWidth="{_ARROWHEAD_SIZE}"'
                    f' markerHeight="{_ARROWHEAD_SIZE}"'
                    f' refX="{_ARROWHEAD_SIZE}"'
                    f' refY="{_ARROWHEAD_SIZE // 2}" orient="auto"'
                    f' markerUnits="userSpaceOnUse">'
                    f'<path d="M0,0 L{_ARROWHEAD_SIZE},'
                    f"{_ARROWHEAD_SIZE // 2}"
                    f" L0,{_ARROWHEAD_SIZE} Z\""
                    f' fill="{stroke_color}"/>'
                    f"</marker></defs>"
                )
                arrow_marker = f"url(#{link_marker_id})"
            else:
                arrow_marker = f"url(#{marker_id})"

            parts.append(
                f'<g data-target="{html_escape(link_target)}"'
                f' class="scriba-state-{link_state}">'
            )
            parts.append(
                f'<line x1="{x_start}" y1="{y_mid}"'
                f' x2="{x_end - _ARROWHEAD_SIZE}" y2="{y_mid}"'
                f' stroke="{stroke_color}" stroke-width="{stroke_w}"'
                f' marker-end="{arrow_marker}"/>'
            )
            parts.append("</g>")

        # --- Render nodes ---
        for i in range(node_count):
            node_suffix = f"node[{i}]"
            node_target = f"{self.name}.{node_suffix}"
            node_state = self.get_state(node_suffix)
            colors = svg_style_attrs(node_state)
            stroke_w = "1" if node_state == "idle" else "2"

            nx = _PADDING + i * (_NODE_WIDTH + _LINK_GAP)
            ny = _PADDING

            parts.append(
                f'<g data-target="{html_escape(node_target)}"'
                f' class="scriba-state-{node_state}">'
            )

            # Full node outline
            parts.append(
                f'<rect x="{nx}" y="{ny}"'
                f' width="{_NODE_WIDTH}" height="{_NODE_HEIGHT}"'
                f' rx="{_CORNER_RADIUS}" fill="{colors["fill"]}"'
                f' stroke="{colors["stroke"]}" stroke-width="{stroke_w}"/>'
            )

            # Divider between value and pointer areas
            div_x = nx + _VALUE_WIDTH
            parts.append(
                f'<line x1="{div_x}" y1="{ny}"'
                f' x2="{div_x}" y2="{ny + _NODE_HEIGHT}"'
                f' stroke="{colors["stroke"]}" stroke-width="{stroke_w}"/>'
            )

            # Value text (centered in the left half)
            val_cx = nx + _VALUE_WIDTH // 2
            val_cy = ny + _NODE_HEIGHT // 2
            display_value = self.values[i]

            # Check if state dict has a value override
            # (handled externally by renderer state, but we also
            #  accept value in params for direct setting)
            parts.append(
                _render_svg_text(
                    str(display_value),
                    val_cx,
                    val_cy,
                    fill=colors["text"],
                    text_anchor="middle",
                    dominant_baseline="central",
                    fo_width=_VALUE_WIDTH,
                    fo_height=_NODE_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )

            # Pointer area (right half)
            ptr_cx = nx + _VALUE_WIDTH + _PTR_WIDTH // 2
            ptr_cy = ny + _NODE_HEIGHT // 2

            if i < node_count - 1:
                # Draw a small filled circle (pointer dot)
                parts.append(
                    f'<circle cx="{ptr_cx}" cy="{ptr_cy}" r="4"'
                    f' fill="{colors["text"]}"/>'
                )
            else:
                # Null indicator — diagonal line through the pointer area
                null_x1 = nx + _VALUE_WIDTH + 4
                null_y1 = ny + _NODE_HEIGHT - 4
                null_x2 = nx + _NODE_WIDTH - 4
                null_y2 = ny + 4
                parts.append(
                    f'<line x1="{null_x1}" y1="{null_y1}"'
                    f' x2="{null_x2}" y2="{null_y2}"'
                    f' stroke="{colors["text"]}" stroke-width="1.5"/>'
                )

            # Index label below the node
            label_x = nx + _NODE_WIDTH // 2
            label_y = ny + _NODE_HEIGHT + _INDEX_LABEL_OFFSET
            parts.append(
                f'<text x="{label_x}" y="{label_y}"'
                f' text-anchor="middle" dominant-baseline="central"'
                f' fill="#6c757d" font-size="10">node[{i}]</text>'
            )

            parts.append("</g>")

        # --- Caption label ---
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
                    dominant_baseline="central",
                    fo_width=bbox.width,
                    fo_height=20,
                    render_inline_tex=render_inline_tex,
                )
            )

        parts.append("</g>")
        return "".join(parts)
