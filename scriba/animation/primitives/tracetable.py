"""TraceTable primitive -- an accumulating dry-run trace table.

Columns are a **pinned header row**; DATA rows grow downward, one per
``\\apply{t}{row=[...]}`` append. The newest data row renders ``current``
by default and older rows demote to ``idle`` (auto-advancing cursor), so a
line-by-line dry-run needs no manual row bookkeeping.

Visual layout::

    ┌─────┬───────┬───────┐   <- pinned header (columns=[i, "a[i]", sum])
    │  i  │  a[i] │  sum  │
    ├─────┼───────┼───────┤
    │  0  │   3   │   3   │   <- \\apply{t}{row=[0, 3, 3]}  (idle, retired)
    │  1  │   1   │   4   │   <- \\apply{t}{row=[1, 1, 4]}  (current)
    └─────┴───────┴───────┘   ... grows downward into pre-reserved space

Like :class:`LinkedList`, the surface grows structurally, so the bounding
box tracks a monotonic row *envelope* (``_envelope_rows``) grown in
``apply_command`` and by the structural prescan — never the live row count.
:meth:`bounding_box` is therefore a pure function of the envelope and the
per-column widths, so the stage viewBox is byte-invariant across frames as
rows accumulate (spec R-32), exactly as ``bar.py`` / ``linkedlist.py``.

Append rides the shipped ``element_add`` motion (a new ``<g data-target=
"t.row[k]">`` appears); the current->idle advance rides ``recolor`` — zero
new motion vocabulary (A-2). No CSS rule, no scriba.js change: rows reuse
the ``scriba-state-*`` classes (Grid model) and the header is inline chrome.

See ``investigations/design-accumulate.md`` §3 for the authoritative design.
"""

from __future__ import annotations

import re
from typing import Any, Callable, ClassVar

from scriba.animation.errors import _animation_error
from scriba.animation.primitives._text_metrics import measure_value_text
from scriba.animation.primitives.base import (
    _CAPTION_CLEAR_GAP,
    CELL_GAP,
    CELL_HEIGHT,
    CELL_WIDTH,
    BoundingBox,
    PrimitiveBase,
    _escape_xml,
    _inset_rect_attrs,
    _render_svg_text,
    register_primitive,
    state_class,
    svg_style_attrs,
    _CELL_HORIZONTAL_PADDING,
)
from scriba.animation.primitives._protocol import register_primitive as _protocol_register
from scriba.animation.primitives._types import _DEFAULT_FONT_SIZE_PX

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_ROW_H = CELL_HEIGHT      # header + every data row share the cell height
_ROW_GAP = CELL_GAP       # vertical gap between rows (and horizontal between cols)
_MIN_COL_W = CELL_WIDTH   # minimum column width (widened to fit content)
_MAX_COLS = 64            # column-count ceiling (E1522)

# ---------------------------------------------------------------------------
# Selector regexes (applied against the suffix after ``name.``)
# ---------------------------------------------------------------------------

_CELL_RE = re.compile(r"^cell\[(?P<k>\d+)\]\[(?P<j>\d+)\]$")
_ROW_RE = re.compile(r"^row\[(?P<k>\d+)\]$")
_COL_RE = re.compile(r"^col\[(?P<j>\d+)\]$")


# ---------------------------------------------------------------------------
# TraceTable primitive
# ---------------------------------------------------------------------------


@register_primitive("TraceTable")
@_protocol_register
class TraceTable(PrimitiveBase):
    """Accumulating dry-run trace table (pinned columns x growing rows).

    Parameters
    ----------
    name:
        Shape name used in selectors (e.g. ``t``).
    params:
        Recognised keys: ``columns`` (required, the pinned header strings —
        their count is the fixed column count) and ``label`` (optional
        caption).
    """

    # opt-in: the structural prescan replays each frame's ``row=`` append so
    # ``_envelope_rows`` (and per-column widths) reach their timeline maximum
    # before frame 0 is measured — R-32 for a surface whose row count grows.
    _structural_prescan: bool = True

    primitive_type = "tracetable"

    SELECTOR_PATTERNS: ClassVar[dict[str, str]] = {
        "row[{k}]": "data row by index",
        "cell[{k}][{j}]": "data cell by row,column",
        "col[{j}]": "column down all data rows",
        "all": "all data cells",
    }

    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({
        "columns",
        "label",
    })

    def __init__(self, name: str, params: dict[str, Any] | None = None) -> None:
        super().__init__(name, params)

        columns = self.params.get("columns")
        if columns is None or (
            isinstance(columns, (list, tuple)) and len(columns) == 0
        ):
            raise _animation_error(
                "E1520",
                detail="TraceTable requires a non-empty 'columns' list",
                hint='example: \\shape{t}{TraceTable}{columns=[i, "a[i]", sum]}',
            )
        if not isinstance(columns, (list, tuple)):
            raise _animation_error(
                "E1520",
                detail=(
                    f"TraceTable 'columns' must be a list of header strings, "
                    f"got {type(columns).__name__}"
                ),
                hint='example: \\shape{t}{TraceTable}{columns=[i, "a[i]", sum]}',
            )
        if len(columns) > _MAX_COLS:
            raise _animation_error(
                "E1522",
                detail=(
                    f"TraceTable 'columns' count ({len(columns)}) is out of "
                    f"range; valid: 1..{_MAX_COLS}"
                ),
            )

        self.columns: list[str] = [str(c) for c in columns]
        self._ncols: int = len(self.columns)

        # Data rows accumulate here (list of row lists). Stored in ``values``
        # so the frame renderer's prescan snapshots/restores it for free —
        # frame 0 renders zero data rows after the restore.
        self.values: list[list[Any]] = []

        # R-32 envelope: the box height follows the MAX row count ever reached,
        # never the live count — a mid-timeline append must not resize the
        # whole surface. Grown in apply_command and by the structural prescan;
        # deliberately survives the prescan restore (same contract as widths).
        self._envelope_rows: int = 0

        # Per-column widths grow monotonically to fit the widest cell (and the
        # header) in each column across the whole timeline (Grid's monotonic
        # ``_cell_width``, one per column).
        self._col_widths: list[int] = [
            self._fit_width(_MIN_COL_W, header) for header in self.columns
        ]

        self.label: str | None = self.params.get("label")

    # ----- width helpers ---------------------------------------------------

    @staticmethod
    def _fit_width(floor: int, value: Any) -> int:
        """Column width that fits *value* at the cell font, never below *floor*."""
        needed = (
            measure_value_text(str(value), _DEFAULT_FONT_SIZE_PX)
            + _CELL_HORIZONTAL_PADDING
        )
        return max(floor, int(needed))

    def _grow_col_width(self, j: int, value: Any) -> None:
        """Widen column *j* to fit *value* (monotonic — never shrinks)."""
        if 0 <= j < self._ncols:
            self._col_widths[j] = self._fit_width(self._col_widths[j], value)

    # ----- apply commands --------------------------------------------------

    def apply_command(self, params: dict[str, Any]) -> None:
        """Append one data row via ``\\apply{t}{row=[...]}``.

        The row length must equal the column count (``E1521``). The appended
        row becomes the CURRENT row; the envelope and per-column widths grow
        so the bounding box stays sized for the timeline maximum.
        """
        row = params.get("row")
        if row is None:
            return
        if not isinstance(row, (list, tuple)):
            raise _animation_error(
                "E1521",
                detail=(
                    f"TraceTable 'row' must be a list of {self._ncols} value(s), "
                    f"got {type(row).__name__}"
                ),
                hint=f"supply exactly {self._ncols} values, one per column",
            )
        if len(row) != self._ncols:
            raise _animation_error(
                "E1521",
                detail=(
                    f"TraceTable 'row' has {len(row)} value(s) but there are "
                    f"{self._ncols} column(s)"
                ),
                hint=f"supply exactly {self._ncols} values, one per column",
            )

        new_row = list(row)
        self.values.append(new_row)
        self._envelope_rows = max(self._envelope_rows, len(self.values))
        for j, cell in enumerate(new_row):
            self._grow_col_width(j, cell)

    def set_value(self, suffix: str, value: str) -> None:
        """Override a single data cell's display value (Grid parity).

        Rows normally arrive whole via ``row=``; this covers a targeted
        ``\\apply{t.cell[k][j]}{value=X}`` and keeps the column width honest.
        """
        super().set_value(suffix, value)
        m = _CELL_RE.match(suffix)
        if m:
            self._grow_col_width(int(m.group("j")), value)

    # ----- geometry --------------------------------------------------------

    def _col_x(self, j: int) -> int:
        """Left edge x of column *j*."""
        return sum(self._col_widths[:j]) + j * _ROW_GAP

    def _content_width(self) -> int:
        return sum(self._col_widths) + (self._ncols - 1) * _ROW_GAP

    def _row_y(self, k: int) -> int:
        """Top edge y of data row *k* (element index ``k + 1``; header is 0)."""
        return (k + 1) * (_ROW_H + _ROW_GAP)

    def _content_height(self, rows: int) -> int:
        """Height of the header + *rows* data rows (pure function of *rows*)."""
        return (rows + 1) * _ROW_H + rows * _ROW_GAP

    # ----- state resolution ------------------------------------------------

    def _effective_cell_state(self, k: int, j: int) -> str:
        """Resolve one data cell's state.

        Precedence: explicit ``cell[k][j]`` > ``row[k]`` > ``col[j]`` >
        auto-advance (newest data row = ``current``, older rows = ``idle``).
        An idle-but-highlighted cell degrades to ``highlight`` (base contract).
        """
        base = None
        for sel in (f"cell[{k}][{j}]", f"row[{k}]", f"col[{j}]"):
            if sel in self._states:
                base = self._states[sel]
                break
        if base is None:
            base = "current" if k == len(self.values) - 1 else "idle"
        if base == "idle" and self._is_highlighted(f"cell[{k}][{j}]"):
            return "highlight"
        return base

    # ----- Primitive interface ---------------------------------------------

    def addressable_parts(self) -> list[str]:
        """Every data cell, plus ``all``. ``row``/``col`` are input-only
        emphasis selectors (kept out of the ``all`` sweep)."""
        parts: list[str] = []
        for k in range(len(self.values)):
            for j in range(self._ncols):
                parts.append(f"cell[{k}][{j}]")
        parts.append("all")
        return parts

    def validate_selector(self, suffix: str) -> bool:
        """Accept ``row[k]`` / ``cell[k][j]`` / ``col[j]`` / ``all``.

        Out-of-range indices return ``False`` — the shipped soft-drop contract
        (annotate/recolor degrade to a no-op, matching Grid).
        """
        if suffix == "all":
            return True
        m = _CELL_RE.match(suffix)
        if m:
            k, j = int(m.group("k")), int(m.group("j"))
            return 0 <= k < len(self.values) and 0 <= j < self._ncols
        m = _ROW_RE.match(suffix)
        if m:
            return 0 <= int(m.group("k")) < len(self.values)
        m = _COL_RE.match(suffix)
        if m:
            return 0 <= int(m.group("j")) < self._ncols
        return False

    def resolve_annotation_point(self, selector: str) -> tuple[float, float] | None:
        """SVG (x, y) center of a ``cell[k][j]`` or ``row[k]`` target, or
        ``None`` (soft-drop) when out of range."""
        prefix = f"{self.name}."
        local = selector[len(prefix):] if selector.startswith(prefix) else selector
        m = _CELL_RE.match(local)
        if m:
            k, j = int(m.group("k")), int(m.group("j"))
            if 0 <= k < len(self.values) and 0 <= j < self._ncols:
                x = self._col_x(j) + self._col_widths[j] // 2
                y = self._row_y(k) + _ROW_H // 2
                return (float(x), float(y))
            return None
        m = _ROW_RE.match(local)
        if m:
            k = int(m.group("k"))
            if 0 <= k < len(self.values):
                x = self._content_width() // 2
                y = self._row_y(k) + _ROW_H // 2
                return (float(x), float(y))
        return None

    def resolve_self_content_rects(self) -> "list[BoundingBox]":
        """Header + data cell boxes so pills do not park on the table."""
        rects: list[BoundingBox] = []
        for j in range(self._ncols):
            rects.append(
                BoundingBox(
                    x=float(self._col_x(j)),
                    y=0.0,
                    width=float(self._col_widths[j]),
                    height=float(_ROW_H),
                )
            )
        for k in range(len(self.values)):
            for j in range(self._ncols):
                rects.append(
                    BoundingBox(
                        x=float(self._col_x(j)),
                        y=float(self._row_y(k)),
                        width=float(self._col_widths[j]),
                        height=float(_ROW_H),
                    )
                )
        return rects

    def resolve_below_baseline(self) -> "float | None":
        """``position=below`` pills sit below the whole table."""
        return float(self._content_height(self._envelope_rows))

    def bounding_box(self) -> BoundingBox:
        """Pure function of the row envelope and per-column widths — never the
        live row count — so the viewBox is invariant across frames (R-32)."""
        tw = self._content_width()
        th = self._content_height(self._envelope_rows)
        # Layer A: fold the (wrapped) caption width into the footprint.
        core_w = max(tw, self._caption_block_width(tw))
        # Layer C: below-pill callout lane sits between the table and caption.
        h = th + self._below_lane_height() + self._caption_block_height(tw)
        if self.label is not None:
            h += _CAPTION_CLEAR_GAP
        # Layer B: annotation arrow lane (0 without annotations → byte-stable).
        h += self._reserved_arrow_above()
        # #1: reserve horizontal room for position=left/right pills (0 without).
        left_pad, right_reach = self._h_label_pad()
        w = left_pad + max(core_w, right_reach)
        return BoundingBox(x=0, y=0, width=w, height=h)

    # ----- SVG rendering ---------------------------------------------------

    def emit_svg(
        self,
        *,
        render_inline_tex: "Callable[[str], str] | None" = None,
        scene_segments: "tuple | None" = None,
        self_offset: "tuple[float, float] | None" = None,
    ) -> str:
        """Emit the SVG ``<g>`` for the trace table."""
        effective_anns = self._annotations

        arrow_above = self._reserved_arrow_above()
        left_pad, _right = self._h_label_pad()

        lines: list[str] = [
            f'<g data-primitive="tracetable" data-shape="{_escape_xml(self.name)}">'
        ]
        if arrow_above > 0 or left_pad > 0:
            lines.append(f'  <g transform="translate({left_pad}, {arrow_above})">')

        # -- Pinned header band (chrome; carries no data-target, not addressable).
        self._emit_header(lines, render_inline_tex)

        # -- Data rows (grow downward; newest is current, older auto-idle).
        for k in range(len(self.values)):
            row_y = self._row_y(k)
            lines.append(f'  <g data-target="{self.name}.row[{k}]">')
            for j in range(self._ncols):
                state = self._effective_cell_state(k, j)
                css = state_class(state)
                colors = svg_style_attrs(state)
                x = self._col_x(j)
                w = self._col_widths[j]
                target = f"{self.name}.cell[{k}][{j}]"

                value = self.get_value(f"cell[{k}][{j}]")
                if value is None:
                    value = self.values[k][j]

                lines.append(f'    <g data-target="{target}" class="{css}">')
                ra = _inset_rect_attrs(x, row_y, w, _ROW_H)
                lines.append(
                    f'      <rect x="{ra["x"]}" y="{ra["y"]}" '
                    f'width="{ra["width"]}" height="{ra["height"]}"/>'
                )
                lines.append(
                    "      "
                    + _render_svg_text(
                        str(value),
                        int(x + w // 2),
                        int(row_y + _ROW_H // 2),
                        fill=colors["text"],
                        font_size=str(_DEFAULT_FONT_SIZE_PX),
                        fo_width=w,
                        fo_height=_ROW_H,
                        render_inline_tex=render_inline_tex,
                    )
                )
                lines.append("    </g>")
            lines.append("  </g>")

        # -- Caption below the table, beneath the below-pill lane.
        if self.label is not None:
            tw = self._content_width()
            self._emit_caption(
                lines,
                content_width=tw,
                footprint_width=max(tw, self._caption_block_width(tw)),
                top_y=int(
                    self._content_height(self._envelope_rows)
                    + self._below_lane_height()
                    + _CAPTION_CLEAR_GAP
                ),
                render_inline_tex=render_inline_tex,
            )

        # -- Annotation arrows + position pills.
        if effective_anns:
            self.emit_annotation_arrows(
                lines,
                effective_anns,
                render_inline_tex=render_inline_tex,
                scene_segments=scene_segments,
                self_offset=self_offset,
            )

        if arrow_above > 0 or left_pad > 0:
            lines.append("  </g>")
        lines.append("</g>")
        return "\n".join(lines)

    def _emit_header(
        self,
        lines: list[str],
        render_inline_tex: "Callable[[str], str] | None",
    ) -> None:
        """Paint the pinned header row. Reuses the ``done`` state palette as
        muted chrome (no new CSS); no ``data-target`` — headers are not
        addressable (``t.row[0]`` is the first DATA row)."""
        colors = svg_style_attrs("done")
        for j, header in enumerate(self.columns):
            x = self._col_x(j)
            w = self._col_widths[j]
            lines.append('  <g class="scriba-state-done">')
            ra = _inset_rect_attrs(x, 0, w, _ROW_H)
            lines.append(
                f'    <rect x="{ra["x"]}" y="{ra["y"]}" '
                f'width="{ra["width"]}" height="{ra["height"]}"/>'
            )
            lines.append(
                "    "
                + _render_svg_text(
                    str(header),
                    int(x + w // 2),
                    int(_ROW_H // 2),
                    fill=colors["text"],
                    font_size=str(_DEFAULT_FONT_SIZE_PX),
                    fo_width=w,
                    fo_height=_ROW_H,
                    render_inline_tex=render_inline_tex,
                )
            )
            lines.append("  </g>")

    # -- obstacle protocol stubs (v0.12.0 prep) -----------------------------

    def resolve_obstacle_boxes(self) -> list:
        """Return AABB obstacles for the current frame. Stub — returns []."""
        return []

    def resolve_obstacle_segments(self) -> list:
        """Return segment obstacles for the current frame. Stub — returns []."""
        return []
