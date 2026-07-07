"""Hypercube primitive — subset lattice for bitmask DP / SOS / Möbius.

Renders the Boolean lattice of an ``n``-bit universe as a Hasse diagram: one
node per subset (an integer ``0 .. 2**n - 1``), laid out in ``n + 1`` rows by
popcount.  The empty set (``0``) sits at the bottom row, the full mask
(``2**n - 1``) at the top, and every cover edge ``m ⊂ m ∪ {bit}`` is drawn as a
thin light connector beneath the nodes.  This makes bit-adjacency first-class,
which a flat ``DPTable`` cell index cannot express.

Selectors (phase 1, decimal addressing only)::

    \\shape{L}{Hypercube}{bits=4}
    \\recolor{L.subset[10]}{state=good}      % 10 == 0b1010
    \\annotate{L.subset[5]}{label="mask 0101", color=info}
    \\apply{L.subset[10]}{value="7"}          % DP value shown on the node

Binary-literal selectors (``subset[0b1010]``) and a ``\\sweep`` fold verb are
intentionally deferred — the shared selector parser only reads decimal indices
(see ``investigations/gap-new-substrates.md`` §5.3/§5.5).  Lattice **edges are
not addressable** in phase 1; they participate in placement as R-31 obstacle
segments but carry no ``edge[...]`` selector yet.

See ``docs/spec/primitives.md`` for the authoritative specification.
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives._params import coerce_int
from scriba.animation.primitives._obstacle_types import ObstacleSegment
from scriba.animation.primitives.base import (
    THEME,
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    _render_svg_text,
    register_primitive,
    state_class,
    svg_style_attrs,
)

from scriba.animation.primitives._protocol import register_primitive as _protocol_register

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Hard cap: bits=5 → 32 nodes / 80 edges, the densest layout that stays legible
# in a Hasse diagram (investigations/gap-new-substrates.md §5.4). Parallels the
# Plane2D element cap.
_MIN_BITS = 1
_MAX_BITS = 5

_NODE_RADIUS = 20  # matches Tree's default node radius
_H_GAP = 16  # horizontal gap between adjacent node slots within a row
_V_GAP = 30  # vertical gap between node rows (leaves room for edges)
_PADDING = 8
_NODE_FONT_SIZE = "13"

_H_PITCH = 2 * _NODE_RADIUS + _H_GAP  # slot width within a popcount row
_ROW_PITCH = 2 * _NODE_RADIUS + _V_GAP  # center-to-center vertical spacing

# ---------------------------------------------------------------------------
# Selector regex (suffix-only — the ``name.`` prefix is stripped upstream)
# ---------------------------------------------------------------------------

_SUBSET_RE = re.compile(r"^subset\[(?P<idx>\d+)\]$")
_ALL_RE = re.compile(r"^all$")


def _popcount(value: int) -> int:
    """Number of set bits in *value* (its Hasse row / lattice level)."""
    return bin(value).count("1")


# ---------------------------------------------------------------------------
# Hypercube primitive
# ---------------------------------------------------------------------------


@register_primitive("Hypercube")
@_protocol_register
class Hypercube(PrimitiveBase):
    """Subset-lattice (Boolean hypercube) primitive.

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``L``).
    params:
        Dictionary of parameters from the ``\\shape`` command.
        Required key: ``bits`` (integer ``1 <= bits <= 5``).
        Optional keys: ``label`` (caption), ``show_bits`` (bool, default
        ``True`` — node text is the zero-padded binary mask; ``False`` shows
        the decimal subset index).
    """

    primitive_type = "hypercube"
    # apply_command only reads the generic value= on subset[i]; no structural
    # \apply keys of its own.
    APPLY_KEYS: ClassVar[frozenset[str]] = frozenset()

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "subset[{i}]": "subset by decimal index (0 .. 2**bits - 1)",
        "all": "all subsets",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "bits",
        "label",
        "show_bits",
    })

    def __init__(self, name: str, params: dict[str, Any]) -> None:
        super().__init__(name, params)

        self.bits: int = coerce_int(
            params.get("bits", 0),
            "E1510",
            detail=(
                f"Hypercube bits {params.get('bits')!r} is not an integer; "
                f"valid: integer between {_MIN_BITS} and {_MAX_BITS} inclusive"
            ),
        )
        if not (_MIN_BITS <= self.bits <= _MAX_BITS):
            raise _animation_error(
                "E1510",
                detail=(
                    f"Hypercube bits {self.bits} is out of range; "
                    f"valid: integer between {_MIN_BITS} and {_MAX_BITS} inclusive"
                ),
            )

        self.label: str | None = params.get("label")
        self.show_bits: bool = bool(params.get("show_bits", True))

        self._node_count: int = 1 << self.bits

        # Group subsets by popcount (Hasse row). Within a row nodes are sorted
        # by mask value so the layout is deterministic.
        self._layers: dict[int, list[int]] = {}
        for v in range(self._node_count):
            self._layers.setdefault(_popcount(v), []).append(v)

        # Cover edges: (m, m | bit) for every unset bit — the submask relation
        # differing by exactly one bit. Count == bits * 2**(bits-1).
        self._edges: list[tuple[int, int]] = []
        for v in range(self._node_count):
            for b in range(self.bits):
                if not (v >> b) & 1:
                    self._edges.append((v, v | (1 << b)))

        # nodefit: seed the cross-frame-max label map with the static mask
        # labels; subset value= overrides grow it via set_value (prescan).
        for v in range(self._node_count):
            base = format(v, f"0{self.bits}b") if self.show_bits else str(v)
            self.note_node_label(f"subset[{v}]", base)

        self._positions: dict[int, tuple[float, float]] = {}
        self._content_w, self._content_h = self._compute_layout()

        # Annotation geometry: the node diameter is the local "cell" scale the
        # shared arrow/pill engine offsets from a node anchor.
        self._arrow_cell_height = float(_NODE_RADIUS * 2)
        self._arrow_shorten = float(_NODE_RADIUS)

    # ----- internal: layout ------------------------------------------------

    def _compute_layout(self) -> tuple[float, float]:
        """Place every subset node and return the ``(width, height)`` footprint.

        Rows are indexed by popcount. The full mask (popcount == bits) is the
        top row; the empty set (popcount 0) is the bottom row. Each row is
        centered horizontally against the widest row.
        """
        # nodefit B3: a row's slot pitch follows its widest painted label
        # (mask or value= override), so wide DP-state labels spread instead
        # of colliding. max() keeps the historic _H_PITCH — and every byte —
        # when labels fit their circles.
        row_pitch: dict[int, int] = {}
        content_w = 0
        for k, values in self._layers.items():
            widest_lbl = max(
                (
                    self.cross_frame_max_label_width(f"subset[{v}]")
                    for v in values
                ),
                default=0,
            )
            pitch = max(_H_PITCH, widest_lbl + _H_GAP)
            row_pitch[k] = pitch
            content_w = max(content_w, len(values) * pitch)
        content_h = self.bits * _ROW_PITCH + 2 * _NODE_RADIUS

        for k, values in self._layers.items():
            row_from_top = self.bits - k
            cy = _PADDING + _NODE_RADIUS + row_from_top * _ROW_PITCH
            pitch = row_pitch[k]
            layer_width = len(values) * pitch
            x0 = _PADDING + (content_w - layer_width) / 2.0
            for j, v in enumerate(values):
                cx = x0 + j * pitch + pitch / 2.0
                self._positions[v] = (cx, cy)

        return content_w, content_h

    def _node_label(self, value: int) -> str:
        """Display text for *value*: value override, else binary/decimal mask."""
        override = self.get_value(f"subset[{value}]")
        if override is not None:
            return override
        if self.show_bits:
            return format(value, f"0{self.bits}b")
        return str(value)

    def _node_state(self, value: int) -> str:
        """Effective render state of a node: stored state promoted by highlight."""
        return self.resolve_effective_state(f"subset[{value}]")

    # ----- apply commands --------------------------------------------------

    def apply_command(
        self,
        params: dict[str, Any],
        *,
        target_suffix: str | None = None,
    ) -> None:
        """Set a subset's displayed value via ``\\apply{L.subset[i]}{value=X}``.

        The value overrides the node's mask text so a bitmask-DP cell value can
        be shown on the subset. Purely a text change — the footprint is fixed by
        ``bits`` and never shifts (R-32).
        """
        if target_suffix is None:
            return
        m = _SUBSET_RE.match(target_suffix)
        if not m or "value" not in params:
            return
        idx = int(m.group("idx"))
        if 0 <= idx < self._node_count:
            self._values[target_suffix] = str(params["value"])
            # nodefit: this path writes _values directly (bypassing
            # set_value), so grow the label map here too.
            self._note_subset_label(target_suffix, str(params["value"]))

    def _note_subset_label(self, suffix: str, value: str) -> None:
        """Grow the label map; when the max actually grew, re-derive the
        row pitches (nodefit B3). The prescan replays every frame before
        the first viewbox read, so the lattice settles pre-measure and
        stays frame-stable (R-32)."""
        before = self.cross_frame_max_label_width(suffix)
        self.note_node_label(suffix, value)
        if self.cross_frame_max_label_width(suffix) > before:
            self._content_w, self._content_h = self._compute_layout()

    def set_value(self, suffix: str, value: str) -> None:
        super().set_value(suffix, value)
        # nodefit: a subset's value= paints centered at 14 px — grow the
        # cross-frame-max map only when the set actually landed (the base
        # soft-drops invalid selectors with E1115).
        if suffix.startswith("subset[") and self.get_value(suffix) == value:
            self._note_subset_label(suffix, value)

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        parts: list[str] = [f"subset[{i}]" for i in range(self._node_count)]
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        if suffix == "all":
            return True
        m = _SUBSET_RE.match(suffix)
        if m:
            idx = int(m.group("idx"))
            return 0 <= idx < self._node_count
        return False

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Map ``'L.subset[i]'`` to the SVG center of that subset node."""
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        m = _SUBSET_RE.match(local)
        if not m:
            return None
        idx = int(m.group("idx"))
        return self._positions.get(idx)

    def resolve_annotation_box(self, selector: str) -> "BoundingBox | None":
        """Annotated node's circle AABB so a ``position=below`` pill gets a
        leader line and treats the node as a MUST blocker (R-02). Gated on an
        actual below pill — mirrors Tree, since base feeds this width to every
        position pill and a bare node diameter would otherwise trip the
        spanning-leader heuristic for above/left/right pills."""
        if not self._target_has_below_pill(selector):
            return None
        pt = self.resolve_annotation_point(selector)
        if pt is None:
            return None
        cx, cy = pt
        r = _NODE_RADIUS
        return BoundingBox(
            x=int(cx - r), y=int(cy - r), width=int(2 * r), height=int(2 * r)
        )

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit in a callout lane below the whole
        lattice, clear of the empty-set row. Every node's ``cy + radius`` stays
        at or above this content-height baseline."""
        return float(_PADDING + self._content_h)

    def _h_label_pad(self) -> "tuple[int, int]":
        """Base pads plus the painted subset-label overhang (nodefit A3).

        A subset label paints ``(left_pad + cx) ± tw/2`` in frame space
        (the emit translate carries no radius term, unlike Graph/Tree);
        fold the left overhang into ``left_pad`` and the right overhang
        into ``right_reach``. Both folds stay int 0 when every label fits
        the frame, keeping existing lattices byte-identical.
        """
        left_pad, right_reach = super()._h_label_pad()
        lbl_l = 0
        lbl_r = 0
        for v, (cx, _cy) in self._positions.items():
            tw = self.cross_frame_max_label_width(f"subset[{v}]")
            if tw <= 2 * _NODE_RADIUS:
                continue  # fits inside the circle -> inside the frame
            half = tw / 2.0
            lbl_l = max(lbl_l, int(math.ceil(half - cx)))
            lbl_r = max(lbl_r, int(math.ceil(cx + half - self._content_w)))
        if lbl_l > 0:
            left_pad = max(left_pad, lbl_l)
        if lbl_r > 0:
            right_reach = max(right_reach, int(self._content_w) + lbl_r)
        return left_pad, right_reach

    def bounding_box(self) -> BoundingBox:
        content_w = float(self._content_w)
        # Layer A: fold the (wrapped) caption width into the footprint.
        core_w = max(content_w, self._caption_block_width(content_w))
        h = _PADDING + self._content_h
        h += self._caption_block_height(content_w)

        # Layer B/C: reserve space for annotation arrows + position pills. With
        # no annotations every term is 0, so the box is byte-stable and — since
        # it depends only on ``bits`` — invariant across frames (R-32).
        arrow_above = self._reserved_arrow_above()
        h += arrow_above
        h += self._below_lane_height()

        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)

        return BoundingBox(x=0, y=0, width=int(w), height=int(h))

    def emit_svg(
        self,
        *,
        render_inline_tex: Callable[[str], str] | None = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        effective_anns = self._annotations
        arrow_above = self._reserved_arrow_above()
        left_pad, _ = self._h_label_pad()

        parts: list[str] = []
        parts.append(
            f'<g data-primitive="hypercube" data-shape="{_escape_xml(self.name)}">'
        )

        # Shift content down (arrows) and right (left pills) into valid space.
        # 0/0 without annotations → byte-identical to the un-shifted output.
        if arrow_above > 0 or left_pad > 0:
            parts.append(f'<g transform="translate({left_pad}, {arrow_above})">')

        self._emit_edges(parts)
        self._emit_nodes(parts, render_inline_tex=render_inline_tex)

        # Caption below the lattice (mirrors the below-baseline lane); emitted
        # inside the translate group, so subtract arrow_above from the anchor.
        if self.label is not None:
            content_w = float(self._content_w)
            bbox = self.bounding_box()
            self._emit_caption(
                parts,
                content_width=content_w,
                footprint_width=int(bbox.width),
                top_y=int(
                    bbox.height
                    - self._caption_block_height(content_w)
                    - self._reserved_arrow_above()
                ),
                render_inline_tex=render_inline_tex,
            )

        if effective_anns:
            self.emit_annotation_arrows(
                parts,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
            )

        if arrow_above > 0 or left_pad > 0:
            parts.append("</g>")
        parts.append("</g>")
        return "".join(parts)

    # ----- internal: emit --------------------------------------------------

    def _emit_edges(self, parts: list[str]) -> None:
        """Draw cover edges as thin dim connectors beneath the nodes.

        An edge is skipped when either endpoint is hidden, mirroring Tree so a
        hidden subset drops its incident lattice lines too.
        """
        stroke = THEME["border"]
        for lo, hi in self._edges:
            if self._node_state(lo) == "hidden" or self._node_state(hi) == "hidden":
                continue
            x0, y0 = self._positions[lo]
            x1, y1 = self._positions[hi]
            parts.append(
                f'<line class="scriba-hypercube-edge" '
                f'x1="{x0:.1f}" y1="{y0:.1f}" '
                f'x2="{x1:.1f}" y2="{y1:.1f}" '
                f'stroke="{stroke}" stroke-width="1"/>'
            )

    def _emit_nodes(
        self,
        parts: list[str],
        *,
        render_inline_tex: Callable[[str], str] | None = None,
    ) -> None:
        """Draw one circle-and-text node per subset, on top of the edges."""
        for v in range(self._node_count):
            state = self._node_state(v)
            if state == "hidden":
                continue
            colors = svg_style_attrs(state)
            cx, cy = self._positions[v]
            node_sw = "1.5" if state == "idle" else "2"
            target = f"{self.name}.subset[{v}]"

            node_text = _render_svg_text(
                self._node_label(v),
                int(cx),
                int(cy),
                fill=colors["text"],
                text_anchor="middle",
                dominant_baseline="central",
                font_size=_NODE_FONT_SIZE,
                fo_width=_NODE_RADIUS * 2,
                fo_height=_NODE_RADIUS * 2,
                render_inline_tex=render_inline_tex,
                clip_overflow=False,
            )
            parts.append(
                f'<g data-target="{_escape_xml(target)}" '
                f'data-node-x="{cx:.1f}" data-node-y="{cy:.1f}" '
                f'class="{state_class(state)}">'
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{_NODE_RADIUS}" '
                f'fill="{colors["fill"]}" '
                f'stroke="{colors["stroke"]}" '
                f'stroke-width="{node_sw}"/>'
                f"{node_text}"
                f"</g>"
            )

    # -- obstacle protocol (R-31) -------------------------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Expose lattice edges as segment obstacles so pills don't cross them
        (R-31). Dim structural edges are ``SHOULD``-avoid; hidden-endpoint edges
        are omitted to match :meth:`_emit_edges`."""
        segments: list[ObstacleSegment] = []
        for lo, hi in self._edges:
            if self._node_state(lo) == "hidden" or self._node_state(hi) == "hidden":
                continue
            x0, y0 = self._positions[lo]
            x1, y1 = self._positions[hi]
            segments.append(
                ObstacleSegment(
                    kind="edge",
                    x0=float(x0),
                    y0=float(y0),
                    x1=float(x1),
                    y1=float(y1),
                    state="dim",
                    severity="SHOULD",
                )
            )
        return segments
