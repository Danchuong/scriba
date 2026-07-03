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
from typing import Any, Callable, ClassVar

from scriba.animation.primitives._text_metrics import measure_text
from scriba.animation.primitives.base import (
    INDEX_LABEL_OFFSET,
    _CAPTION_CLEAR_GAP,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    _render_svg_text,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._types import (
    _CELL_HORIZONTAL_PADDING,
    _DEFAULT_FONT_SIZE_PX,
)

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_VALUE_WIDTH_MIN = 50  # minimum left half of the node (value display)
_PTR_WIDTH = 30  # right half of the node (pointer indicator)
_NODE_HEIGHT = 40
_LINK_GAP = 30  # horizontal gap between nodes (arrow space)
_PADDING = 12
_INDEX_LABEL_OFFSET = INDEX_LABEL_OFFSET  # single source: _types (C6)
_CORNER_RADIUS = 4
_NULL_INDICATOR_PAD = 4  # inset for the null diagonal line in the pointer area

# ---------------------------------------------------------------------------
# Selector regexes (applied against the suffix after ``name.``)
# ---------------------------------------------------------------------------

_NODE_RE = re.compile(r"^node\[(?P<idx>\d+)\]$")
_LINK_RE = re.compile(r"^link\[(?P<idx>\d+)\]$")
_ALL_RE = re.compile(r"^all$")

# Full-qualified selector regex (with shape name prefix) for annotation points
_FULL_NODE_RE = re.compile(r"^(?P<name>\w+)\.node\[(?P<idx>\d+)\]$")

# ---------------------------------------------------------------------------
# LinkedList primitive
# ---------------------------------------------------------------------------


@register_primitive("LinkedList")
@_protocol_register
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

    primitive_type = "linkedlist"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "node[{i}]": "node by index",
        "link[{i}]": "link arrow by index",
        "all": "all nodes and links",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "data",
        "label",
    })

    # ``link[i]`` addresses the outgoing arrow *after* ``node[i]`` — i.e.
    # the link that points from ``node[i]`` to ``node[i+1]``. Valid
    # indices are therefore ``0 <= i < len(values) - 1``; the last node
    # has no outgoing link. This semantic is enforced in
    # :meth:`validate_selector` and exposed in :meth:`addressable_parts`.

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
        self.label: str | None = params.get("label")

        # Dynamic sizing based on actual content
        self._recalc_widths()

    # ----- layout helpers --------------------------------------------------

    def _recalc_widths(self) -> None:
        """Recompute dynamic node widths from current values (monotonic)."""
        if self.values:
            current = max(
                _VALUE_WIDTH_MIN,
                max(measure_text(str(v), _DEFAULT_FONT_SIZE_PX) + _CELL_HORIZONTAL_PADDING for v in self.values),
            )
        else:
            current = _VALUE_WIDTH_MIN
        # Monotonic: never shrink so bounding_box stays valid across frames
        self._value_width = max(getattr(self, "_value_width", _VALUE_WIDTH_MIN), current)
        self._node_width = self._value_width + _PTR_WIDTH
        self._arrowhead_size = max(4, min(8, _LINK_GAP // 4))

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

        # Recompute widths whenever values change
        if insert_val is not None or remove_val is not None:
            self._recalc_widths()

    def set_value(self, suffix: str, value: str) -> None:
        """Set a node's display value (called by emitter)."""
        m = _NODE_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            if 0 <= idx < len(self.values):
                self.values[idx] = value
                self._recalc_widths()

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

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Return SVG (x, y) center for an annotation selector.

        Supports ``"<name>.node[<i>]"`` selectors.
        Returns the top-center of the node so arrows curve above.
        """
        m = _FULL_NODE_RE.match(selector)
        if m and m.group("name") == self.name:
            idx = int(m.group("idx"))
            if 0 <= idx < len(self.values):
                nx = _PADDING + idx * (self._node_width + _LINK_GAP)
                x = nx + self._node_width // 2
                y = _PADDING  # top edge of node
                return (float(x), float(y))
        return None

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit below the whole list (nodes + index
        labels) in a callout lane, clear of the content. Matches the content
        bottom reserved by :meth:`bounding_box`."""
        return float(2 * _PADDING + _NODE_HEIGHT + _INDEX_LABEL_OFFSET)

    def bounding_box(self) -> BoundingBox:
        n = max(len(self.values), 1)
        content_w = n * self._node_width + (n - 1) * _LINK_GAP
        # Layer A: fold the (wrapped) caption width into the footprint.
        core_w = max(2 * _PADDING + content_w, self._caption_block_width(content_w))
        h = 2 * _PADDING + _NODE_HEIGHT + _INDEX_LABEL_OFFSET
        h += self._caption_block_height(content_w)
        if self.label is not None:
            h += _CAPTION_CLEAR_GAP
        arrow_above = self._reserved_arrow_above()
        h += arrow_above
        # Layer C: below-pill callout lane (0 without below pills → byte-stable).
        h += self._below_lane_height()
        # #1: reserve horizontal room for position=left/right pills. Both pads
        # are 0 (int) without left/right pills, so the box stays byte-stable.
        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)
        return BoundingBox(x=0, y=0, width=w, height=h)

    # ----- SVG rendering ---------------------------------------------------

    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        effective_anns = self._annotations

        # Compute vertical space needed above nodes for arrow curves
        arrow_above = self._reserved_arrow_above()
        # #1: shift content right for position=left pills (0 when none →
        # "translate(0, …)", byte-identical to the pre-#1 output).
        left_pad, _ = self._h_label_pad()

        parts: list[str] = []
        parts.append(
            f'<g data-primitive="linkedlist"'
            f' data-shape="{_escape_xml(self.name)}">'
        )

        # Shift content down (arrows) and right (left pills) into valid space.
        if arrow_above > 0 or left_pad > 0:
            parts.append(f'<g transform="translate({left_pad}, {arrow_above})">')

        # --- Arrowhead marker definition ---
        ah = self._arrowhead_size
        marker_id = f"arrowhead-{_escape_xml(self.name)}"
        parts.append("<defs>")
        parts.append(
            f'<marker id="{marker_id}" markerWidth="{ah}"'
            f' markerHeight="{ah}" refX="{ah}"'
            f' refY="{ah // 2}" orient="auto"'
            f' markerUnits="userSpaceOnUse">'
            f'<path d="M0,0 L{ah},{ah // 2}'
            f" L0,{ah} Z\""
            f' fill="{THEME["border"]}" class="scriba-ll-arrowhead"/>'
            f"</marker>"
        )
        parts.append("</defs>")

        if not self.values:
            # Empty list placeholder
            parts.append(
                f'<rect x="{_PADDING}" y="{_PADDING}"'
                f' width="{self._node_width}" height="{_NODE_HEIGHT}"'
                f' fill="{THEME["bg"]}" stroke="{THEME["border"]}" stroke-width="1"'
                f' stroke-dasharray="4 2" rx="{_CORNER_RADIUS}"/>'
            )
            parts.append(
                f'<text x="{_PADDING + self._node_width // 2}"'
                f' y="{_PADDING + _NODE_HEIGHT // 2}"'
                f' text-anchor="middle" dominant-baseline="central"'
                f' fill="{THEME["fg_dim"]}"'
                f' style="font-size:11px">'
                f'empty</text>'
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
                + i * (self._node_width + _LINK_GAP)
                + self._value_width
                + _PTR_WIDTH // 2
            )
            # Arrow ends at the left edge of node[i+1]
            x_end = (
                _PADDING
                + (i + 1) * (self._node_width + _LINK_GAP)
            )
            y_mid = _PADDING + _NODE_HEIGHT // 2

            stroke_color = link_colors["stroke"]
            stroke_w = "1.5" if link_state == "idle" else "2.5"

            # Update arrowhead color via a per-link marker when non-idle
            if link_state != "idle":
                link_marker_id = f"arrowhead-{_escape_xml(self.name)}-{i}"
                parts.append(
                    f'<defs><marker id="{link_marker_id}"'
                    f' markerWidth="{ah}"'
                    f' markerHeight="{ah}"'
                    f' refX="{ah}"'
                    f' refY="{ah // 2}" orient="auto"'
                    f' markerUnits="userSpaceOnUse">'
                    f'<path d="M0,0 L{ah},'
                    f"{ah // 2}"
                    f" L0,{ah} Z\""
                    f' fill="{stroke_color}"/>'
                    f"</marker></defs>"
                )
                arrow_marker = f"url(#{link_marker_id})"
            else:
                arrow_marker = f"url(#{marker_id})"

            parts.append(
                f'<g data-target="{_escape_xml(link_target)}"'
                f' class="{state_class(link_state)}">'
            )
            parts.append(
                f'<line x1="{x_start}" y1="{y_mid}"'
                f' x2="{x_end - ah}" y2="{y_mid}"'
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

            nx = _PADDING + i * (self._node_width + _LINK_GAP)
            ny = _PADDING

            parts.append(
                f'<g data-target="{_escape_xml(node_target)}"'
                f' class="{state_class(node_state)}">'
            )

            # Full node outline
            parts.append(
                f'<rect x="{nx}" y="{ny}"'
                f' width="{self._node_width}" height="{_NODE_HEIGHT}"'
                f' rx="{_CORNER_RADIUS}" fill="{colors["fill"]}"'
                f' stroke="{colors["stroke"]}" stroke-width="{stroke_w}"/>'
            )

            # Divider between value and pointer areas
            div_x = nx + self._value_width
            parts.append(
                f'<line x1="{div_x}" y1="{ny}"'
                f' x2="{div_x}" y2="{ny + _NODE_HEIGHT}"'
                f' stroke="{colors["stroke"]}" stroke-width="{stroke_w}"/>'
            )

            # Value text (centered in the left half)
            val_cx = nx + self._value_width // 2
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
                    fo_width=self._value_width,
                    fo_height=_NODE_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )

            # Pointer area (right half)
            ptr_cx = nx + self._value_width + _PTR_WIDTH // 2
            ptr_cy = ny + _NODE_HEIGHT // 2

            if i < node_count - 1:
                # Draw a small filled circle (pointer dot)
                parts.append(
                    f'<circle cx="{ptr_cx}" cy="{ptr_cy}" r="4"'
                    f' fill="{colors["text"]}"/>'
                )
            else:
                # Null indicator — diagonal line through the pointer area
                null_x1 = nx + self._value_width + _NULL_INDICATOR_PAD
                null_y1 = ny + _NODE_HEIGHT - _NULL_INDICATOR_PAD
                null_x2 = nx + self._node_width - _NULL_INDICATOR_PAD
                null_y2 = ny + _NULL_INDICATOR_PAD
                parts.append(
                    f'<line x1="{null_x1}" y1="{null_y1}"'
                    f' x2="{null_x2}" y2="{null_y2}"'
                    f' stroke="{colors["text"]}" stroke-width="1.5"/>'
                )

            # Index label below the node
            label_x = nx + self._node_width // 2
            label_y = ny + _NODE_HEIGHT + _INDEX_LABEL_OFFSET
            parts.append(
                f'<text x="{label_x}" y="{label_y}"'
                f' text-anchor="middle" dominant-baseline="central"'
                f' fill="{THEME["fg_muted"]}"'
                f' style="font-size:10px">'
                f'node[{i}]</text>'
            )

            parts.append("</g>")

        # --- Caption label ---
        if self.label is not None:
            n = max(len(self.values), 1)
            content_w = n * self._node_width + (n - 1) * _LINK_GAP
            bbox = self.bounding_box()
            self._emit_caption(
                parts,
                content_width=content_w,
                footprint_width=int(bbox.width),
                # minus arrow_above: the caption is emitted INSIDE the
                # translate(_, arrow_above) group, so anchoring at raw
                # bbox.height painted it arrow_above px PAST the bbox
                # bottom, eating the inter-primitive gap.
                top_y=int(
                    bbox.height
                    - self._caption_block_height(content_w)
                    - self._reserved_arrow_above()
                ),
                render_inline_tex=render_inline_tex,
            )

        # Annotation arrow rendering
        if effective_anns:
            arrow_lines: list[str] = []
            self.emit_annotation_arrows(arrow_lines, effective_anns, render_inline_tex=render_inline_tex)
            parts.extend(arrow_lines)

        # Close the translate group if we opened one
        if arrow_above > 0 or left_pad > 0:
            parts.append("</g>")

        parts.append("</g>")
        return "".join(parts)

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []
