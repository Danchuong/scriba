"""R-38 binding-caret vs below-label-lane collision (JudgeZone #7 + audit).

A bound ``\\cursor`` caret is emitted directly by ``emit_cursors_under``
(base.py) at a fixed offset below the *cell bottom*, bypassing the obstacle
placer. When the target reserves a below-label lane (Array ``labels=`` index
row, NumberLine tick labels), the caret's ``▲`` + id land *on* those labels:

  * Array ``labels="0..k"``: id "i" (central f11) over the index digit
    (hanging f10) — 6.5 px, same column.
  * NumberLine ``labels="0..k"``: id over the tick label (5.5 px) *and* the
    ▲ jammed into the tick marks.

Fix: anchor the caret apex at ``max(cell_bottom, resolve_below_baseline())``
so it drops into the same callout lane ``position=below`` pills already use.
A target with no below-lane (no-label Array, where ``resolve_below_baseline()``
returns the cell bottom) must stay byte-identical.

Bands are computed from the glyph baseline rules (default ``svg text`` =
``central``; ``.scriba-index-label`` = ``hanging``), matching the audit probe.
"""

from __future__ import annotations

import re

from scriba.animation.primitives._types import CELL_HEIGHT, INDEX_FONT_PX
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.base import (
    _CURSOR_GAP,
    _CURSOR_H,
    _CURSOR_ID_DY,
    _CURSOR_ID_FONT_PX,
)
from scriba.animation.primitives.numberline import (
    NL_LABEL_Y,
    NL_TICK_BOTTOM,
    NumberLinePrimitive,
)


# ---------------------------------------------------------------------------
# SVG parse helpers — pull the caret ▲ / id and the label glyphs numerically
# ---------------------------------------------------------------------------


def _caret_body(svg: str, key: str) -> str:
    m = re.search(
        r'data-annotation="' + re.escape(key) + r'-solo"[^>]*>(.*?)</g>', svg, re.S
    )
    assert m, f"caret group {key!r} missing from svg"
    return m.group(1)


def _caret_apex_y(body: str) -> float:
    # points="apex_x,apex_y base_lx,base_y base_rx,base_y"
    m = re.search(r'<polygon points="[\d.]+,([\d.]+) ', body)
    assert m, "caret polygon missing"
    return float(m.group(1))


def _caret_id_xy(body: str) -> tuple[float, float]:
    m = re.search(r'<text x="([\d.]+)" y="([\d.]+)"', body)
    assert m, "caret id text missing"
    return float(m.group(1)), float(m.group(2))


def _index_label_y_at(svg: str, x: float) -> float:
    for m in re.finditer(
        r'<text class="scriba-index-label[^"]*" x="([\d.]+)" y="([\d.]+)"', svg
    ):
        if abs(float(m.group(1)) - x) < 0.6:
            return float(m.group(2))
    raise AssertionError(f"no index label near x={x}")


# central-baseline glyph: y is the vertical middle
def _central_band(y: float, font: float) -> tuple[float, float]:
    return (y - font / 2.0, y + font / 2.0)


# hanging-baseline glyph (index labels): y is the top
def _hanging_band(y: float, font: float) -> tuple[float, float]:
    return (y, y + font)


# ---------------------------------------------------------------------------
# Array with index labels — the seed report #7 collision
# ---------------------------------------------------------------------------


def _labeled_array_caret(index: int = 0):
    arr = ArrayPrimitive("arr", {"values": [10, 20, 30], "labels": "0..2"})
    arr.set_cursors([{"target": "arr", "id": "i", "index": index, "color": "info"}])
    return arr, arr.emit_svg()


class TestLabeledArrayCaret:
    def test_caret_id_drops_below_index_lane(self) -> None:
        """Caret id must sit fully below the index digit — no y-band overlap."""
        arr, svg = _labeled_array_caret(0)
        body = _caret_body(svg, "arr.cursor[i]")
        id_x, id_y = _caret_id_xy(body)
        idx_y = _index_label_y_at(svg, id_x)

        # Lead's numeric form: id baseline below the index digit's bottom.
        assert id_y > idx_y + INDEX_FONT_PX, (
            f"caret id y={id_y} not clear of index digit "
            f"[{idx_y}, {idx_y + INDEX_FONT_PX}] (report #7 collision)"
        )

        # Full band non-overlap: top of id band >= bottom of index band.
        id_top, _ = _central_band(id_y, _CURSOR_ID_FONT_PX)
        _, idx_bot = _hanging_band(idx_y, INDEX_FONT_PX)
        assert id_top >= idx_bot, (
            f"id band top {id_top} overlaps index band bottom {idx_bot}"
        )

    def test_caret_apex_below_index_lane(self) -> None:
        """The ▲ apex clears the index digits (not just the id label)."""
        arr, svg = _labeled_array_caret(0)
        body = _caret_body(svg, "arr.cursor[i]")
        apex_y = _caret_apex_y(body)
        idx_y = _index_label_y_at(svg, _caret_id_xy(body)[0])
        _, idx_bot = _hanging_band(idx_y, INDEX_FONT_PX)
        assert apex_y >= idx_bot, f"apex {apex_y} inside index band (bottom {idx_bot})"

    def test_caret_apex_anchored_to_below_lane(self) -> None:
        """Apex origin is the below-baseline (index-row bottom) + the gap."""
        arr, svg = _labeled_array_caret(0)
        body = _caret_body(svg, "arr.cursor[i]")
        apex_y = _caret_apex_y(body)
        expected = arr.resolve_below_baseline() + _CURSOR_GAP
        assert abs(apex_y - expected) < 0.01, f"apex {apex_y} != lane origin {expected}"


# ---------------------------------------------------------------------------
# Array WITHOUT index labels — byte-identity regression guard
# ---------------------------------------------------------------------------


class TestNoLabelArrayByteIdentity:
    """No below-lane -> the origin fix is a no-op; caret geometry frozen.

    Pre-fix values (captured from HEAD before the origin change): the caret
    binds cell 0 (center x=30), apex at cell_bottom(40)+GAP(6)=46, base at
    46+H(8)=54, id baseline at 54+ID_DY(11)=65. resolve_below_baseline() for a
    no-label Array returns CELL_HEIGHT(40)==cell_bottom, so max() picks the
    cell bottom and nothing moves.
    """

    def test_nolabel_caret_geometry_frozen(self) -> None:
        arr = ArrayPrimitive("arr", {"values": [10, 20, 30]})
        arr.set_cursors([{"target": "arr", "id": "i", "index": 0, "color": "info"}])
        assert arr.resolve_below_baseline() == float(CELL_HEIGHT)  # == cell bottom
        svg = arr.emit_svg()
        body = _caret_body(svg, "arr.cursor[i]")

        apex_y = _caret_apex_y(body)
        _, id_y = _caret_id_xy(body)
        assert apex_y == CELL_HEIGHT + _CURSOR_GAP == 46.0
        base_y = CELL_HEIGHT + _CURSOR_GAP + _CURSOR_H
        assert id_y == base_y + _CURSOR_ID_DY == 65.0

        # Exact byte snapshot of the caret body (pre-fix).
        assert body == (
            '<polygon points="30.0,46.0 25.0,54.0 35.0,54.0" fill="#506882"/>'
            '<text x="30.0" y="65.0" fill="#506882" font-size="11"'
            ' style="text-anchor:middle;dominant-baseline:central">i</text>'
        )


# ---------------------------------------------------------------------------
# NumberLine tick labels — same root cause, degenerate top==center
# ---------------------------------------------------------------------------


def _numberline_caret(index: int = 3):
    nl = NumberLinePrimitive("nl", {"domain": [0, 6], "ticks": 7, "labels": "0..6"})
    nl.set_cursors([{"target": "nl", "id": "p", "index": index, "color": "info"}])
    return nl, nl.emit_svg()


class TestNumberLineCaret:
    def test_caret_apex_clears_tick_marks(self) -> None:
        """The ▲ apex must sit below the tick marks, not jammed into them."""
        nl, svg = _numberline_caret(3)
        body = _caret_body(svg, "nl.cursor[p]")
        apex_y = _caret_apex_y(body)
        assert apex_y > NL_TICK_BOTTOM, (
            f"apex {apex_y} inside tick marks (bottom {NL_TICK_BOTTOM})"
        )

    def test_caret_id_below_tick_labels(self) -> None:
        """Caret id must clear the tick-label band (central f10 at NL_LABEL_Y)."""
        nl, svg = _numberline_caret(3)
        body = _caret_body(svg, "nl.cursor[p]")
        _, id_y = _caret_id_xy(body)
        _, tick_bot = _central_band(NL_LABEL_Y, 10)
        id_top, _ = _central_band(id_y, _CURSOR_ID_FONT_PX)
        assert id_top >= tick_bot, (
            f"id band top {id_top} overlaps tick-label band bottom {tick_bot}"
        )
        assert id_y > NL_LABEL_Y + 10 / 2.0

    def test_caret_apex_anchored_to_below_lane(self) -> None:
        """Even with degenerate top==center, the lane origin lands the caret."""
        nl, svg = _numberline_caret(3)
        body = _caret_body(svg, "nl.cursor[p]")
        apex_y = _caret_apex_y(body)
        expected = nl.resolve_below_baseline() + _CURSOR_GAP
        assert abs(apex_y - expected) < 0.01, f"apex {apex_y} != lane origin {expected}"
