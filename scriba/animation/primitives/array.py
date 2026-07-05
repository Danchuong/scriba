"""Array primitive — a fixed-length horizontal row of indexed cells.

See ``docs/spec/primitives.md`` §3 for the authoritative specification.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives._params import coerce_int
from scriba.animation.primitives._text_metrics import measure_value_text, measure_text
from scriba.animation.primitives.base import (
    LABEL_FONT_PX,
    _CAPTION_CLEAR_GAP,
    ALL_RE,
    CELL_1D_RE,
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    CellMetrics,
    INDEX_LABEL_OFFSET,
    RANGE_RE,
    THEME,
    BoundingBox,
    PrimitiveBase,
    _inset_rect_attrs,
    _label_has_math,
    _LABEL_PILL_MAX_W_PX,
    _LABEL_PILL_PAD_X,
    _render_svg_text,
    _wrap_label_lines,
    position_below_lane_height,
    estimate_text_width,
    register_primitive,
    state_class,
    svg_style_attrs,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._types import (
    INDEX_FONT_PX,
    _CELL_HORIZONTAL_PADDING,
    SUFFIX_CELL_RE,
    SUFFIX_RANGE_RE,
)
from scriba.animation.primitives.layout import TextBox, stack_bottom, vstack

# Font sizes for each role — must match the CSS variables below. A CI
# guard test (``tests/unit/test_css_font_sync.py``) parses the stylesheet
# and asserts these values equal the numbers in
# ``scriba-scene-primitives.css``::
#
#   --scriba-cell-font         700 14px inherit
#   --scriba-cell-index-font   500 10px ui-monospace, monospace
#   --scriba-label-font        600 11px ui-monospace, monospace
_FONT_SIZE_CELL: int = 14
_FONT_SIZE_INDEX: int = INDEX_FONT_PX
_FONT_SIZE_CAPTION: int = LABEL_FONT_PX

# Vertical whitespace between consecutive items in the bottom stack
# (index-label row → caption row). Replaces the old ``_CAPTION_GAP``
# magic number. ``vstack`` guarantees glyph boxes cannot overlap for any
# combination of font sizes within the ±5 % cross-font drift envelope
# absorbed by this gap. See ``layout.py`` for the invariant contract.
_STACK_GAP: int = _CAPTION_CLEAR_GAP  # single source for caption clearance
# Caption wrap/pad constants now live in base (PrimitiveBase Layer A helpers,
# shared by all caption-bearing primitives).


# ---------------------------------------------------------------------------
# Selector matching
# ---------------------------------------------------------------------------

# Full-qualified selectors (with shape name prefix) — canonical from base.py.
_CELL_RE = CELL_1D_RE
_RANGE_RE = RANGE_RE
_ALL_RE = ALL_RE

# Suffix-only regexes (no shape name prefix) — canonical from ._types.
_SUFFIX_CELL_RE = SUFFIX_CELL_RE
_SUFFIX_RANGE_RE = SUFFIX_RANGE_RE

# Sentinel slots (opt-in ``sentinels=true``): bare named parts ``before``/
# ``after`` mirroring Queue's ``front``/``rear`` — zero regex change to the
# numeric ``cell[i]`` grammar, and structurally excluded from ``all``/``range``
# because they are named parts, not ``cell[i]``.
_SENTINEL_RE = re.compile(r"^(?P<name>.+)\.(?P<part>before|after)$")


def _is_truthy_flag(value: Any) -> bool:
    """True only for an explicit truthy flag (``True`` or the string ``"true"``)."""
    if value is True:
        return True
    return isinstance(value, str) and value.strip().lower() == "true"


# ---------------------------------------------------------------------------
# ArrayPrimitive
# ---------------------------------------------------------------------------


@register_primitive("Array")
@_protocol_register
class ArrayPrimitive(PrimitiveBase):
    """A fixed-length horizontal row of indexed cells.

    Extends :class:`PrimitiveBase` with self-managed state.
    """

    primitive_type = "array"
    supports_trace = True

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "cell[{i}]": "cell by index",
        "range[{lo}:{hi}]": "contiguous range of cells",
        "all": "all cells",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "size",
        "n",
        "data",
        "labels",
        "label",
        # ``values`` is an alias that supplies BOTH ``size`` (inferred from
        # len) and ``data`` in a single parameter, so authors can write
        # ``\shape{a}{Array}{values=[1,2,3]}`` without repeating themselves.
        "values",
        # ``sentinels=true`` reserves two dashed ``before``/``after`` slots
        # (begin()-1 / end()) an out-of-range annotation can park on.
        "sentinels",
    })

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)
        size = self.params.get("size", self.params.get("n"))
        values_alias = self.params.get("values")
        if size is None and isinstance(values_alias, list):
            size = len(values_alias)
        if size is None:
            raise _animation_error(
                "E1400",
                detail="Array requires 'size', 'n', or 'values' parameter",
                hint="example: \\shape{a}{Array}{size=10}",
            )
        size = coerce_int(
            size, "E1401",
            detail=f"Array size {size!r} is not an integer; valid: 1..10000",
        )
        if size < 1:
            raise _animation_error(
                "E1401",
                detail=f"Array size {size} is out of range; valid: 1..10000",
            )
        if size > 10_000:
            raise _animation_error(
                "E1401",
                detail=(
                    f"Array size {size} exceeds maximum; valid: 1..10000"
                ),
            )

        raw_data = self.params.get("data")
        if raw_data is None and isinstance(values_alias, list):
            raw_data = values_alias
        data: list[Any] = list(raw_data or [])
        if len(data) > size:
            raise _animation_error(
                "E1402",
                detail=(
                    f"Array 'data' length ({len(data)}) exceeds "
                    f"size ({size}); valid: len(data) <= size or omit data"
                ),
            )
        # ``live`` = number of populated slots (Queue-model slot identity). A
        # partial ``data`` (len < size) leaves the tail empty and addressable;
        # insert/remove move ``live`` within [0, size] on the fixed grid so cell
        # positions never change and R-32 centering holds by construction.
        self.live: int = len(data)
        if len(data) < size:
            data = data + [""] * (size - len(data))

        self.size: int = size
        self.data: list[Any] = data
        self.labels: str | None = self.params.get("labels")
        self.label: str | None = self.params.get("label")
        self._sentinels: bool = _is_truthy_flag(self.params.get("sentinels"))

        # Element-identity layer (A5 reorder). ``_item_of_slot[i]`` is the id
        # of the item currently occupying slot ``i``; every slot is born with
        # item ``i`` (the id is fixed for the item's lifetime). ``reorder``
        # permutes this map alongside ``data`` so ``item[k]`` travels with its
        # value to a new slot (differ ``position_move``) while slot identity
        # ``cell[i]`` stays fixed (R-42: annotations/recolors keyed on the
        # slot never move). ``_reordered`` gates the ``data-item`` attribute
        # and ``get_node_positions`` so a non-reordering array stays
        # byte-identical; ``_reflowed`` records insert/remove so the two
        # structural models are never mixed in one animation (E1404).
        self._item_of_slot: list[int] = list(range(size))
        self._reordered: bool = False
        self._reflowed: bool = False

        # Compute dynamic cell width from data and labels
        max_content_w = max(
            (measure_value_text(str(v), 14) for v in self.data), default=0
        )
        if self.labels:
            parsed = _parse_index_labels(self.labels, self.size)
            max_label_w = max(
                (measure_value_text(str(lb), 11, mono=True) for lb in parsed), default=0
            )
        else:
            max_label_w = 0
        self._cell_width: int = max(CELL_WIDTH, max_content_w + _CELL_HORIZONTAL_PADDING, max_label_w + 8)

    # -- structural apply commands ------------------------------------------

    def apply_command(
        self,
        params: dict[str, Any],
        *,
        target_suffix: str | None = None,
    ) -> None:
        """Structural mutation on the fixed max-N grid.

        Two structural models ride this one bulk ``apply_params`` path (no new
        verb — ``target_suffix`` is accepted but ignored, the op addresses the
        whole shape):

        * **Slot-identity reflow** — ``\\apply{a}{insert={at=k, value=v}}``
          shifts slots ``k..live-1`` one position right and writes ``v`` at
          ``k`` (``index`` is an accepted alias for ``at``);
          ``\\apply{a}{remove=k}`` shifts ``k+1..live-1`` one position left and
          vacates the freed tail to an **empty cell** (OQ2). Every cell
          *position* is fixed, so consecutive frames differ only in cell values
          → the differ emits a ``value_change`` cascade and R-32 centering holds
          by construction. The grid never grows past the declared ``size``:
          inserting into a full array is an error (E1403), not a silent grow.

        * **Element-identity reorder** — ``\\apply{a}{reorder=[3,0,1,4,2]}``
          permutes the live prefix by SOURCE-SLOT indices (gather semantics:
          slot ``j`` shows the pre-op value of slot ``order[j]``,
          ``new[j] = old[order[j]]``). Values travel with a fixed-id ``item[k]``
          element that glides to its new slot (``position_move``); see
          :meth:`_apply_reorder`.

        The two models are mutually exclusive within one animation: mixing
        ``reorder`` with ``insert``/``remove`` raises E1404 (v1 keeps the two
        identity substrates from interleaving; generalized later).
        """
        has_reorder = "reorder" in params
        has_reflow = "insert" in params or "remove" in params
        mixes = (has_reorder and (self._reflowed or has_reflow)) or (
            has_reflow and self._reordered
        )
        if mixes:
            raise _animation_error(
                "E1404",
                detail=(
                    "Array 'reorder' cannot be combined with insert/remove "
                    "in the same animation"
                ),
                hint=(
                    "reorder cannot mix with insert/remove in one animation "
                    "— file an issue if you need this"
                ),
            )
        if has_reorder:
            self._apply_reorder(params["reorder"])
            self._reordered = True
        if "insert" in params:
            self._apply_insert(params["insert"])
            self._reflowed = True
        if "remove" in params:
            self._apply_remove(params["remove"])
            self._reflowed = True

    def _apply_insert(self, spec: Any) -> None:
        if isinstance(spec, dict):
            at = spec.get("at", spec.get("index", self.live))
            value = spec.get("value", "")
        else:  # bare ``insert=k`` inserts an empty cell at k
            at, value = spec, ""
        try:
            at = int(at)
        except (TypeError, ValueError):
            at = self.live
        if self.live >= self.size:
            raise _animation_error(
                "E1403",
                detail=(
                    f"Array insert overflow: array is full "
                    f"(live={self.live} == size={self.size})"
                ),
                hint="declare a larger size= (v1 uses a fixed max-N grid)",
            )
        if not 0 <= at <= self.live:
            raise _animation_error(
                "E1403",
                detail=(
                    f"Array insert position {at} out of range; "
                    f"valid: 0..{self.live}"
                ),
            )
        for i in range(self.live, at, -1):
            self.data[i] = self.data[i - 1]
        self.data[at] = value
        self.live += 1
        self._grow_cell_width(value)

    def _apply_remove(self, spec: Any) -> None:
        if isinstance(spec, dict):
            spec = spec.get("at", spec.get("index"))
        try:
            at = int(spec)
        except (TypeError, ValueError):
            raise _animation_error(
                "E1403",
                detail=f"Array remove index {spec!r} is not an integer",
            )
        if not 0 <= at < self.live:
            raise _animation_error(
                "E1403",
                detail=(
                    f"Array remove index {at} out of range; valid: "
                    + (f"0..{self.live - 1}" if self.live else "array is empty")
                ),
            )
        for i in range(at, self.live - 1):
            self.data[i] = self.data[i + 1]
        self.data[self.live - 1] = ""  # OQ2: freed tail is an empty cell
        self.live -= 1

    def _grow_cell_width(self, value: Any) -> None:
        """Monotonically widen the cell for a newly inserted value (mirrors
        ``Queue.enqueue``). Never shrinks, so the reserved envelope only grows
        and R-32 holds across the timeline (the renderer's max-width prescan
        folds this into one stable frame envelope)."""
        needed = measure_value_text(str(value), 14) + _CELL_HORIZONTAL_PADDING
        if needed > self._cell_width:
            self._cell_width = needed

    def _apply_reorder(self, spec: Any) -> None:
        """Permute the live prefix by SOURCE-SLOT indices (gather semantics).

        ``order`` is a permutation of ``range(live)``. After the op, slot ``j``
        displays the pre-op value of slot ``order[j]`` — i.e.
        ``new[j] = old[order[j]]``. Example: ``reorder=[3,0,1,4,2]`` on
        ``[A,B,C,D,E]`` yields ``[D,A,B,E,C]`` (slot 0 takes source slot 3).

        Both the cell values and the element-identity map ``_item_of_slot`` are
        permuted the same way, so the item that sat at source slot ``order[j]``
        (id fixed since t0) now occupies slot ``j`` and carries its value there;
        :meth:`get_node_positions` then reports its new slot center and the
        differ emits a ``position_move`` gliding ``item[k]``. Slot identity
        ``cell[i]`` never moves (R-42): annotations and recolors keyed on the
        slot still address the fixed position.

        Validation is total before any mutation, so a rejected ``order`` leaves
        the array untouched. Invalid ``order`` (not a list, wrong length, or not
        a permutation of ``0..live-1``) raises E1404.
        """
        n = self.live
        if not isinstance(spec, (list, tuple)):
            raise _animation_error(
                "E1404",
                detail=(
                    f"Array reorder 'order' must be a list; got "
                    f"{type(spec).__name__}"
                ),
                hint="example: \\apply{a}{reorder=[3,0,1,4,2]}",
            )
        order = list(spec)
        if len(order) != n:
            raise _animation_error(
                "E1404",
                detail=(
                    f"Array reorder length {len(order)} does not match the "
                    f"live slot count {n}"
                ),
                hint="order must be a permutation of 0..live-1",
            )
        try:
            order_int = [int(x) for x in order]
        except (TypeError, ValueError):
            raise _animation_error(
                "E1404",
                detail=(
                    f"Array reorder 'order' has a non-integer index: {order!r}"
                ),
                hint="order must be a permutation of 0..live-1",
            )
        if sorted(order_int) != list(range(n)):
            raise _animation_error(
                "E1404",
                detail=(
                    f"Array reorder {order_int} is not a permutation of "
                    f"0..{n - 1}"
                ),
                hint="each source slot 0..live-1 must appear exactly once",
            )
        new_data = list(self.data)
        new_item = list(self._item_of_slot)
        for j in range(n):
            src = order_int[j]
            new_data[j] = self.data[src]
            new_item[j] = self._item_of_slot[src]
        self.data = new_data
        self._item_of_slot = new_item

    def get_node_positions(self) -> dict[str, tuple[int, int]]:
        """Return ``{item-target: (x, y)}`` for the element-identity layer.

        Empty until the array has received a ``reorder`` (``_reordered``), so a
        non-reordering array emits no ``item[k]`` entries and its interactive
        manifest stays byte-identical (mirrors the ``data-item`` gate in
        :meth:`emit_svg`; also keeps ``_inject_tree_positions`` a no-op for it).
        Once reordered, each live item ``k`` (``k = _item_of_slot[i]``) reports
        the center of the slot ``i`` it now occupies, so the differ emits a
        ``position_move`` that glides the item to its new slot. Coordinate
        semantics mirror ``Tree.get_node_positions`` (pre-``emit_svg``-translate
        frame) and the slot center from :meth:`_cell_center`.
        """
        if not self._reordered:
            return {}
        cw = self._cell_width
        dx = self._row_dx()
        cy = CELL_HEIGHT // 2
        result: dict[str, tuple[int, int]] = {}
        for i in range(self.live):
            k = self._item_of_slot[i]
            cx = int(i * (cw + CELL_GAP) + cw // 2) + dx
            result[f"{self.name}.item[{k}]"] = (cx, cy)
        return result

    # -- PrimitiveBase interface --------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Return all valid selector suffixes."""
        parts: list[str] = []
        for i in range(self.size):
            parts.append(f"cell[{i}]")
        parts.append("all")
        if self._sentinels:
            parts.append("before")
            parts.append("after")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        """Check whether *suffix* is a valid addressable part."""
        if self._sentinels and suffix in ("before", "after"):
            return True

        m = _SUFFIX_CELL_RE.match(suffix)
        if m:
            return 0 <= int(m.group("idx")) < self.size

        m = _SUFFIX_RANGE_RE.match(suffix)
        if m:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            return 0 <= lo <= hi < self.size

        return suffix == "all"

    def _annotation_cell_metrics(self) -> "CellMetrics":
        """Grid-aware flow context — single source for render AND measurement."""
        return CellMetrics(
            cell_width=float(self._cell_width),
            cell_height=float(CELL_HEIGHT),
            grid_cols=int(self.size),
            grid_rows=1,
            origin_x=0.0,
            origin_y=0.0,
        )

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        """Emit SVG ``<g>`` for the array.

        Reads state from internal ``_states``/``_values``/``_annotations``
        managed by :class:`PrimitiveBase`.
        """
        effective_anns = self._annotations

        # Compute vertical space needed above cells for arrow curves and
        # position=above pill labels.
        arrow_above = self._reserved_arrow_above()

        lines: list[str] = [
            f'<g data-primitive="array" data-shape="{self.name}">'
        ]

        # Shift all content down so arrows curve into valid space above y=0
        if arrow_above > 0:
            lines.append(f'  <g transform="translate(0, {arrow_above})">')


        # Bottom area, visual top-to-bottom: index row → callout lane
        # (position=below pills) → caption. Only the index row is in this
        # vstack; the lane and caption are placed below it (see the caption
        # block after the cell loop) so the caption is always the bottom-most
        # element, beneath any callout pills.
        stack_items = self._index_stack_items()
        stack_ys = vstack(
            stack_items,
            start_y=CELL_HEIGHT + INDEX_LABEL_OFFSET,
            gap=_STACK_GAP,
        )
        stack_y_by_role: dict[str, int] = {
            box.role: int(y) for box, y in zip(stack_items, stack_ys)
        }

        # Defect 6 — when a caption is wider than the cell row, the footprint
        # (bbox) widens but the renderer centers the whole group on bbox width
        # and ignores bbox.x. Shift the cell row right by ``row_dx`` so cells
        # stay centered under the caption. Anchors apply the same shift
        # (``_cell_center`` / ``_range_center``) so annotations track the row.
        row_dx = self._row_dx()

        for i in range(self.size):
            target = f"{self.name}.cell[{i}]"
            suffix = f"cell[{i}]"

            value = self.get_value(suffix)
            if value is None:
                value = self.data[i]
            effective_state = self.resolve_effective_state(suffix)

            css = state_class(effective_state)
            # ``svg_style_attrs`` is still used for <text> fill until the
            # CSS text rule ships; rect fill/stroke/stroke-width are owned
            # by the state class in scriba-scene-primitives.css.
            colors = svg_style_attrs(effective_state)

            cw = self._cell_width
            x = int(i * (cw + CELL_GAP)) + row_dx
            y = 0

            # ``data-item`` names the element-identity layer for the differ /
            # runtime (``item[k]`` = the item currently in this slot). Emitted
            # ONLY after a reorder so a non-reordering array is byte-identical
            # to pre-A5 goldens; values/states remain SLOT-addressed (R-42).
            if self._reordered:
                item_k = self._item_of_slot[i]
                lines.append(
                    f'  <g data-target="{target}" '
                    f'data-item="{self.name}.item[{item_k}]" class="{css}">'
                )
            else:
                lines.append(
                    f'  <g data-target="{target}" class="{css}">'
                )
            rect_attrs = _inset_rect_attrs(x, y, cw, CELL_HEIGHT)
            lines.append(
                f'    <rect x="{rect_attrs["x"]}" y="{rect_attrs["y"]}" '
                f'width="{rect_attrs["width"]}" '
                f'height="{rect_attrs["height"]}"/>'
            )
            text_x = int(x + cw // 2)
            text_y = int(y + CELL_HEIGHT // 2)
            lines.append(
                "    "
                + _render_svg_text(
                    value,
                    text_x,
                    text_y,
                    fill=colors["text"],
                    font_size="14",
                    fo_width=cw,
                    fo_height=CELL_HEIGHT,
                    render_inline_tex=render_inline_tex,
                )
            )
            lines.append("  </g>")

            # Index labels below the cell — y computed once by vstack above
            if self.labels is not None:
                idx_labels = _parse_index_labels(self.labels, self.size)
                lines.append(
                    "  "
                    + _render_svg_text(
                        idx_labels[i],
                        text_x,
                        stack_y_by_role["label"],
                        fill=THEME["fg_muted"],
                        css_class="scriba-index-label idx",
                        font_size="10",
                        fo_width=cw,
                        fo_height=20,
                        render_inline_tex=render_inline_tex,
                    )
                )

        # Sentinel slots — dashed chrome one pitch beyond each end, drawn on
        # top of the cells so ``after`` stays visible over the empty tail slot
        # it tracks. Opt-in (``sentinels=true``); the width they need is
        # reserved every frame by ``_bbox_width`` (R-32).
        if self._sentinels:
            self._emit_sentinels(lines)

        # Caption — the figure's description — placed BELOW the callout lane so
        # it is the bottom-most element (not buried between the index row and
        # the position=below pills). Wrapped to multiple lines so a long caption
        # never overflows the viewBox. Centered on the footprint width; cells
        # (shifted by row_dx) share the same center line.
        if self._caption_lines(self._total_width()):
            lane_h = self._below_lane_height()
            caption_top = int(self.resolve_below_baseline() + lane_h + _STACK_GAP)
            self._emit_caption(
                lines,
                content_width=self._total_width(),
                footprint_width=self._bbox_width(),
                top_y=caption_top,
                render_inline_tex=render_inline_tex,
            )

        # Arrow annotations
        # R-37 traces: above the cell bodies (a filled cell would
        # swallow an under-stroke) but below pills/arrows; digits
        # stay legible via the global paint-order halo
        self.emit_traces_under(lines)
        # R-38 binding carets ride the same decoration band as traces.
        self.emit_cursors_under(lines)

        if effective_anns:
            self.emit_annotation_arrows(
                lines,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
                cell_metrics=self._annotation_cell_metrics(),
            )

        # Close the translate group if we opened one for arrow space
        if arrow_above > 0:
            lines.append("  </g>")

        lines.append("</g>")
        return "\n".join(lines)

    def bounding_box(self) -> BoundingBox:
        """Return ``(x, y, width, height)``.

        The height includes vertical space needed above the cells
        for arrow curves when annotations have been set, plus the
        vstack-computed bottom stack below the cells when index labels
        or a caption are present.
        """
        effective_anns = self._annotations
        # Defect 6 — the caption width participates in the footprint so a
        # caption wider than the cell row is not clipped by the viewBox.
        w = self._bbox_width()

        # Bottom area in visual order: index row → callout lane → caption.
        # ``resolve_below_baseline`` is the bottom of the index row (or the
        # cell bottom when there is no index); the lane and the (possibly
        # multi-line) caption stack below it. Single source shared with
        # emit_svg so geometry never drifts.
        below_baseline = self.resolve_below_baseline() or float(CELL_HEIGHT)
        lane_h = self._below_lane_height()
        bottom = below_baseline + lane_h
        caption_h = self._caption_block_height(self._total_width())
        if caption_h:
            bottom = below_baseline + lane_h + _STACK_GAP + caption_h

        # R-38: a binding caret sits below the cells; grow the content box so
        # the ▲ + id are not clipped (0 when no caret → byte-stable).
        bottom = max(bottom, self._cursor_extent_below())

        arrow_above = self._reserved_arrow_above()
        return BoundingBox(x=0, y=0, width=float(w), height=float(arrow_above + bottom))

    def _cell_center(self, selector_str: str) -> tuple[int, int] | None:
        """Return the ``(cx, cy)`` pixel center of a cell selector.

        ``cx`` includes ``_row_dx`` so anchors track the cell row when a wide
        caption shifts it (Defect 6 keeps content and anchors in sync).
        """
        m = _CELL_RE.match(selector_str)
        if m and m.group("name") == self.name:
            i = int(m.group("idx"))
            if 0 <= i < self.size:
                cw = self._cell_width
                x = int(i * (cw + CELL_GAP) + cw // 2) + self._row_dx()
                y = 0  # top edge of cell — arrows curve above
                return (x, y)
        return None

    def _range_center(self, selector_str: str) -> tuple[int, int] | None:
        """Return the ``(cx, cy)`` anchor for a ``range[lo:hi]`` selector.

        Defect 5 — ``range`` targets previously had no anchor, so a position
        label or arrow on a range was silently dropped. The span is inclusive
        (cells ``lo..hi``), matching the renderer's range expansion
        (``_frame_renderer.py`` ``range(lo, hi + 1)``). ``cx`` is the midpoint
        of the span's outer edges; ``cy`` is the cell top edge like cells.
        """
        m = _RANGE_RE.match(selector_str)
        if m and m.group("name") == self.name:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            if 0 <= lo <= hi < self.size:
                cw = self._cell_width
                left = lo * (cw + CELL_GAP)
                right = hi * (cw + CELL_GAP) + cw
                x = int((left + right) // 2) + self._row_dx()
                return (x, 0)
        return None

    def _sentinel_center(self, selector_str: str) -> tuple[int, int] | None:
        """Anchor for the ``before``/``after`` sentinel slots (cell-top edge, so
        arrows curve above like cells). ``before`` is one pitch left of cell[0];
        ``after`` tracks ``live`` (one pitch right of cell[live-1]). Only when
        ``sentinels=true`` — otherwise the parts do not exist."""
        if not self._sentinels:
            return None
        m = _SENTINEL_RE.match(selector_str)
        if not (m and m.group("name") == self.name):
            return None
        cw = self._cell_width
        pitch = cw + CELL_GAP
        base_center = int(cw // 2) + self._row_dx()  # cell[0] center x
        if m.group("part") == "before":
            return (base_center - pitch, 0)
        return (base_center + self.live * pitch, 0)  # after — tracks live

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """Resolve a cell, range, or sentinel selector to its arrow anchor."""
        result = self._cell_center(selector)
        if result is None:
            result = self._range_center(selector)
        if result is None:
            result = self._sentinel_center(selector)
        if result is None:
            return None
        return (float(result[0]), float(result[1]))

    def resolve_label_anchor(self, selector: str) -> tuple[float, float] | None:
        """Anchor for position-only pill labels — the cell *center*.

        Defect 1a — pill offsets in ``emit_position_label_svg`` are measured
        from the element center (``ay ± cell_height/2``), but Array's arrow
        anchor is the cell *top* (``y=0``, so arrows curve above). Returning
        the top here makes a ``position=below`` pill land ``cell_height/2`` too
        high — inside the cell body. Shift to the center for labels while
        leaving ``resolve_annotation_point`` (arrows) on the top edge.
        """
        pt = self.resolve_annotation_point(selector)
        if pt is None:
            return None
        return (pt[0], pt[1] + CELL_HEIGHT / 2)

    def resolve_annotation_box(self, selector: str) -> BoundingBox | None:
        """Return the cell (or range) AABB so the pill placer treats it as a
        MUST blocker (Defect 1b). Coordinates are local and include ``_row_dx``
        so the box tracks the (possibly caption-shifted) cell row.

        Unconditional (not scoped to below pills like the newer cell primitives):
        Array's box predates the unified scoping and its committed output already
        includes the R-07/R-08 spanning leader on wide above-cell pills; scoping
        it would *remove* those established leaders. The newer primitives scope
        instead so they don't *introduce* such leaders (both choices = 0 churn).
        """
        cw = self._cell_width
        m = _CELL_RE.match(selector)
        if m and m.group("name") == self.name:
            i = int(m.group("idx"))
            if 0 <= i < self.size:
                x = i * (cw + CELL_GAP) + self._row_dx()
                return BoundingBox(x=int(x), y=0, width=int(cw), height=int(CELL_HEIGHT))
        m = _RANGE_RE.match(selector)
        if m and m.group("name") == self.name:
            lo, hi = int(m.group("lo")), int(m.group("hi"))
            if 0 <= lo <= hi < self.size:
                left = lo * (cw + CELL_GAP) + self._row_dx()
                right = hi * (cw + CELL_GAP) + cw + self._row_dx()
                return BoundingBox(
                    x=int(left), y=0, width=int(right - left), height=int(CELL_HEIGHT)
                )
        return None

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []

    # -- internal -----------------------------------------------------------

    def _index_stack_items(self) -> list[TextBox]:
        """The index-label row (the only fixed bottom-stack item).

        Visual bottom order is: index row → callout lane → caption. The lane
        and caption are placed *below* the index row (not in this vstack), so
        the caption always reads as the figure's description at the very
        bottom, beneath any ``position=below`` callout pills.
        """
        if self.labels is None:
            return []
        return [TextBox(font_size=_FONT_SIZE_INDEX, role="label", baseline="hanging")]

    def resolve_self_content_rects(self) -> "list[BoundingBox]":
        """Cell boxes (content frame) — pills should not bury the row."""
        cw = self._cell_width
        # Same frame as resolve_annotation_point: Array bakes _row_dx into
        # its anchors, so the content rects must carry it too (it is 0 in
        # the measurement frame), or the placement obstacles sit offset
        # from the anchors at render time and measured != painted.
        dx = self._row_dx()
        return [
            BoundingBox(
                x=float(i * (cw + CELL_GAP) + dx),
                y=0.0,
                width=float(cw),
                height=float(CELL_HEIGHT),
            )
            for i in range(self.size)
        ]

    def resolve_below_baseline(self) -> float | None:
        """Y where ``position=below`` callout pills start — just below the index
        row (or the cells when there is no index row). Pills sit here, and the
        caption is placed below them.
        """
        items = self._index_stack_items()
        if not items:
            return float(CELL_HEIGHT)
        return float(
            stack_bottom(items, start_y=CELL_HEIGHT + INDEX_LABEL_OFFSET, gap=_STACK_GAP)
        )

    def _total_width(self) -> int:
        """Width of the cell row only (no caption)."""
        if self.size == 0:
            return 0
        return self.size * self._cell_width + (self.size - 1) * CELL_GAP


    def _measure_emit(self, parts: "list[str]") -> None:
        """Measure annotations in the CONTENT frame (``_row_dx`` forced 0).

        Array's selector anchors include ``_row_dx``, which itself depends on
        the annotation extent — measuring with the live ``_row_dx`` would
        recurse. Since ``_row_dx`` is a pure horizontal translation, measuring
        at 0 and shifting by the final ``_row_dx`` afterwards is exact.
        """
        self._extent_content_frame = True
        try:
            super()._measure_emit(parts)
        finally:
            self._extent_content_frame = False

    def _h_shift(self) -> int:
        """Symmetric horizontal margin around the cell row.

        Exact: the painted annotation extent (measured in the content frame)
        and the centered caption block both must fit; ``S`` is the smallest
        symmetric margin that contains them, so ``bbox = content + 2*S`` and
        the row shifts right by exactly ``S``. Replaces the pill-width
        formula estimate (which hardcoded 11px against 12px label colors and
        never modelled collision nudges).
        """
        content = self._total_width()
        cap_half = (self._caption_block_width(content) - content) / 2.0
        need = max(0.0, cap_half)
        ext = self._annotation_extent()
        if ext is not None:
            need = max(need, -ext.min_x, ext.max_x - content)
        import math

        return int(math.ceil(need))

    def _bbox_width(self) -> int:
        """Footprint width: cell row + the two-sided sentinel reserve (0 when
        off) + symmetric margin for the caption and the exact painted annotation
        extent. Single source of truth shared by ``emit_svg`` and
        ``bounding_box``. The sentinel reserve is constant per frame, so a
        sentinel array's width is frame-invariant (R-32)."""
        return self._total_width() + self._sentinel_reserve() + 2 * self._h_shift()

    def _row_dx(self) -> int:
        """Horizontal shift that keeps the cell row centered inside the
        footprint. Includes the left sentinel reserve so the row makes room for
        ``before`` (0 when sentinels are off → non-sentinel arrays byte-stable).
        Zero in the content measurement frame (see ``_measure_emit``)."""
        if getattr(self, "_extent_content_frame", False):
            return 0
        return self._h_shift() + self._sentinel_left_dx()

    def _sentinel_left_dx(self) -> int:
        """One cell pitch reserved left of cell[0] for the ``before`` sentinel;
        shifts the cell row right so ``before`` sits at x >= 0. 0 when off."""
        return (self._cell_width + CELL_GAP) if self._sentinels else 0

    def _sentinel_reserve(self) -> int:
        """Total fixed width for both sentinels (2 pitches), reserved in EVERY
        frame regardless of ``live`` so the bbox is frame-invariant (R-32). 0
        when sentinels are off."""
        return 2 * (self._cell_width + CELL_GAP) if self._sentinels else 0

    def _emit_sentinels(self, lines: list[str]) -> None:
        """Draw the two dashed ``scriba-sentinel`` chrome slots. ``before`` is
        fixed one pitch left of cell[0]; ``after`` tracks ``live`` (one pitch
        right of cell[live-1]). Their coordinates share ``_row_dx`` with the
        cells so they stay aligned under a caption shift."""
        cw = self._cell_width
        pitch = cw + CELL_GAP
        cell0_left = self._row_dx()  # cell[0] left edge = 0*pitch + row_dx
        for part, x in (
            ("before", cell0_left - pitch),
            ("after", cell0_left + self.live * pitch),
        ):
            rect_attrs = _inset_rect_attrs(x, 0, cw, CELL_HEIGHT)
            lines.append(f'  <g data-target="{self.name}.{part}" class="scriba-sentinel">')
            lines.append(
                f'    <rect x="{rect_attrs["x"]}" y="{rect_attrs["y"]}" '
                f'width="{rect_attrs["width"]}" '
                f'height="{rect_attrs["height"]}"/>'
            )
            lines.append("  </g>")


# ---------------------------------------------------------------------------
# Backward-compatible alias: ArrayInstance -> ArrayPrimitive
# ---------------------------------------------------------------------------

ArrayInstance = ArrayPrimitive


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
