"""JudgeZone #12: below-cell band reservation (base.py ``_below_lane_height``).

Every tenant of the below-cell band — index labels, the caret stack (``▲``
+ id), a ``position=below`` annotation pill, and a ``label=`` caption — must
occupy a disjoint vertical interval. Sibling of the report #7 fix covered by
``test_cursor_label_lane.py``: that fix anchored the caret's *origin* to the
label lane so the caret never paints on the index row. This defect is the
mirror image — the *caption*'s own placement formula never consulted the
caret's reach, so a bound multi-char-id caret painted its ``▲`` + id text
inside the caption block below it.

Root cause and fix are written up in full in
``_bmad-output/implementation-artifacts/investigations/
judgezone-12-caret-caption-collision-investigation.md`` and
``_bmad-output/implementation-artifacts/
spec-fix-judgezone-12-below-band-reservation.md``.
"""

from __future__ import annotations

import math
import re

import pytest

from scriba.animation.primitives._types import INDEX_FONT_PX
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.bar import Bar
from scriba.animation.primitives.base import (
    _CAPTION_FONT_PX,
    _CURSOR_H,
    _CURSOR_ID_FONT_PX,
)
from scriba.animation.primitives.codepanel import CodePanel
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.forest import Forest
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.hashmap import HashMap
from scriba.animation.primitives.hypercube import Hypercube
from scriba.animation.primitives.layout import ASCENDER_RATIO, DESCENDER_RATIO
from scriba.animation.primitives.linkedlist import LinkedList
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.animation.primitives.queue import Queue
from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.tracetable import TraceTable
from scriba.animation.primitives.tree import Tree
from scriba.animation.primitives.variablewatch import VariableWatch

from tests.unit.test_cursor_label_lane import (
    _caret_apex_y,
    _caret_body,
    _caret_id_xy,
    _central_band,
    _hanging_band,
    _index_label_y_at,
)

# Long enough to wrap onto a second display line for any of the small
# fixtures below — exercises the multi-line/alphabetic-baseline caption
# branch, which is the exact shape of the reported collision (triangle vs
# caption line 1, id text vs caption line 2).
_LONG_CAPTION = "a caption long enough that it wraps onto a second display line every time"


# ---------------------------------------------------------------------------
# SVG parse helpers
# ---------------------------------------------------------------------------

_CAPTION_RE = re.compile(
    r'<text class="scriba-primitive-label"([^>]*)>(.*?)</text>', re.S
)


def _alphabetic_band(y: float, font: float) -> "tuple[float, float]":
    """Default SVG ``<text>`` baseline (no ``dominant-baseline`` set): ascent
    above *y*, descent below — the multi-line caption's own text/tspan block."""
    return (y - ASCENDER_RATIO * font, y + DESCENDER_RATIO * font)


def _caption_line_bands(svg: str) -> "list[tuple[float, float]]":
    """(top, bottom) of every rendered caption line, in paint order.

    Single line -> one ``dominant-baseline:central`` ``<text>`` at a fixed y.
    Multi-line -> one alphabetic-baseline ``<text>`` whose ``<tspan>``s carry
    cumulative ``dy`` offsets from the first line's y (see base.py
    ``_emit_caption``).
    """
    m = _CAPTION_RE.search(svg)
    if not m:
        return []
    attrs, body = m.group(1), m.group(2)
    y_match = re.search(r'y="([\d.]+)"', attrs)
    assert y_match, "caption <text> missing y="
    y0 = float(y_match.group(1))
    dys = re.findall(r'<tspan[^>]*\bdy="([\d.]+)"', body)
    if not dys:
        band = (
            _central_band(y0, _CAPTION_FONT_PX)
            if "dominant-baseline:central" in attrs
            else _alphabetic_band(y0, _CAPTION_FONT_PX)
        )
        return [band]
    y = y0
    bands = []
    for dy in dys:
        y += float(dy)
        bands.append(_alphabetic_band(y, _CAPTION_FONT_PX))
    return bands


def _disjoint(a: "tuple[float, float]", b: "tuple[float, float]") -> bool:
    return a[1] <= b[0] or b[1] <= a[0]


def _assert_all_disjoint(named_bands: "dict[str, tuple[float, float]]") -> None:
    """Pairwise-disjoint check over every named y-band (the lane contract)."""
    items = list(named_bands.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (name_a, band_a), (name_b, band_b) = items[i], items[j]
            assert _disjoint(band_a, band_b), (
                f"{name_a} {band_a} overlaps {name_b} {band_b}"
            )


def _caret_bands(svg: str, key: str) -> "dict[str, tuple[float, float]]":
    body = _caret_body(svg, key)
    apex_y = _caret_apex_y(body)
    _, id_y = _caret_id_xy(body)
    return {
        "caret_triangle": (apex_y, apex_y + _CURSOR_H),
        "caret_id": _central_band(id_y, _CURSOR_ID_FONT_PX),
    }


# ---------------------------------------------------------------------------
# Array: the full matrix — {labels present/absent} x caption present x
# bound cursor present (multi-char id). The bug is independent of labels=
# and of id length, so both label combinations must clear the caption.
# ---------------------------------------------------------------------------


def _array_with(*, labels: bool, caption: bool, cursor_id: "str | None") -> "tuple[ArrayPrimitive, str]":
    cfg: "dict" = {"values": [10, 20, 30]}
    if labels:
        cfg["labels"] = "0..2"
    if caption:
        cfg["label"] = _LONG_CAPTION
    arr = ArrayPrimitive("arr", cfg)
    if cursor_id is not None:
        arr.set_cursors([{"target": "arr", "id": cursor_id, "index": 0, "color": "info"}])
    return arr, arr.emit_svg()


class TestArrayBelowBandMatrix:
    """Caption + bound multi-char-id caret together — the reported shape."""

    @pytest.mark.parametrize("labels", [True, False], ids=["labels", "no_labels"])
    def test_caret_caption_and_index_all_disjoint(self, labels: bool) -> None:
        arr, svg = _array_with(labels=labels, caption=True, cursor_id="idx")
        cap_bands = _caption_line_bands(svg)
        assert cap_bands, "expected a rendered (wrapped) caption"

        bands = _caret_bands(svg, "arr.cursor[idx]")
        for i, band in enumerate(cap_bands):
            bands[f"caption_line_{i}"] = band
        if labels:
            id_x, _ = _caret_id_xy(_caret_body(svg, "arr.cursor[idx]"))
            idx_y = _index_label_y_at(svg, id_x)
            bands["index_label"] = _hanging_band(idx_y, INDEX_FONT_PX)

        _assert_all_disjoint(bands)

    def test_no_caption_cursor_reserves_caret_reach_only(self) -> None:
        """No caption -> nothing for the caret to protect against, but the
        shared helper is not caption-conditional: it still reserves exactly
        the caret's own reach past the baseline, matching the formula."""
        arr, svg = _array_with(labels=False, caption=False, cursor_id="idx")
        assert "cursor[idx]" in svg
        baseline = arr.resolve_below_baseline()
        assert baseline is not None
        expected = max(math.ceil(arr._cursor_extent_below() - float(baseline)), 0)
        assert arr._below_lane_height() == expected


class TestNoCursorCaptionByteStable:
    """Byte-stability guard: with no bound caret, ``_cursor_extent_below()``
    is 0.0, so ``caret_reach = ceil(0.0 - baseline) <= 0`` for any positive
    baseline, and ``max(lane, caret_reach, 0) == lane`` — the fix is a hard
    no-op for every caption-only frame. This must hold both before and after
    the fix; it is not itself a RED case, it is the regression guard for it.
    """

    def test_caption_only_no_cursor_lane_unchanged(self) -> None:
        arr, svg = _array_with(labels=True, caption=True, cursor_id=None)
        assert not getattr(arr, "_cursors", [])
        assert arr._cursor_extent_below() == 0.0
        baseline = arr.resolve_below_baseline()
        assert baseline is not None and baseline > 0
        pre_fix_lane = arr.annotation_below_overhang(float(baseline))
        assert arr._below_lane_height() == pre_fix_lane
        assert _caption_line_bands(svg), "expected a rendered caption"


# ---------------------------------------------------------------------------
# Spot checks: Grid, DPTable, Queue, Stack — same shared helper, same
# contract. Matrix/LinkedList/HashMap are not covered: no cursor code.
# ---------------------------------------------------------------------------


class TestSpotChecksOtherPrimitives:
    def test_grid_lane_height_reserves_caret_reach(self) -> None:
        """Grid's R-38 caret targeting is 2D-only (``cell[row][col]``); the
        base class's default ``_cursor_cell_suffix`` only ever emits a flat
        ``cell[N]``, so no scalar-index ``\\cursor`` binding can resolve a
        Grid cell today (soft-dropped before painting — a pre-existing DSL
        gap, unrelated to this fix; see the deliverable's regression notes).
        This exercises the actual fix target directly: stub
        ``_cursor_extent_below`` the way a real caret would report a deep
        reach, and assert the shared helper folds it into the reservation
        exactly like Array/DPTable/Queue/Stack do through a real caret."""
        grid = GridPrimitive("g", {"rows": 2, "cols": 2, "label": _LONG_CAPTION})
        baseline = grid.resolve_below_baseline()
        assert baseline is not None
        deep_reach = float(baseline) + 50.0
        grid._cursor_extent_below = lambda: deep_reach  # type: ignore[method-assign]
        assert grid._below_lane_height() == math.ceil(deep_reach - float(baseline))

    def test_dptable_caret_caption_disjoint(self) -> None:
        dp = DPTablePrimitive("dp", {"n": 4, "labels": "0..3", "label": _LONG_CAPTION})
        dp.set_cursors([{"target": "dp", "id": "idx", "index": 0, "color": "info"}])
        svg = dp.emit_svg()
        cap_bands = _caption_line_bands(svg)
        assert cap_bands, "expected a rendered caption"
        id_x, _ = _caret_id_xy(_caret_body(svg, "dp.cursor[idx]"))
        idx_y = _index_label_y_at(svg, id_x)
        bands = _caret_bands(svg, "dp.cursor[idx]")
        bands["index_label"] = _hanging_band(idx_y, INDEX_FONT_PX)
        for i, band in enumerate(cap_bands):
            bands[f"caption_line_{i}"] = band
        _assert_all_disjoint(bands)

    def test_queue_caret_caption_disjoint(self) -> None:
        q = Queue("q", {"capacity": 4, "data": [1, 2], "label": _LONG_CAPTION})
        q.set_cursors([{"target": "q", "id": "idx", "index": 0, "color": "info"}])
        svg = q.emit_svg()
        cap_bands = _caption_line_bands(svg)
        assert cap_bands, "expected a rendered caption"
        bands = _caret_bands(svg, "q.cursor[idx]")
        for i, band in enumerate(cap_bands):
            bands[f"caption_line_{i}"] = band
        _assert_all_disjoint(bands)

    def test_stack_caret_caption_disjoint(self) -> None:
        s = Stack("s", {"items": [1, 2, 3], "label": _LONG_CAPTION})
        s.set_cursors([{"target": "s", "id": "idx", "index": 0, "color": "info"}])
        svg = s.emit_svg()
        cap_bands = _caption_line_bands(svg)
        assert cap_bands, "expected a rendered caption"
        bands = _caret_bands(svg, "s.cursor[idx]")
        for i, band in enumerate(cap_bands):
            bands[f"caption_line_{i}"] = band
        _assert_all_disjoint(bands)

    def test_numberline_caret_caption_disjoint(self) -> None:
        """NumberLine is the 12th ``_below_lane_height`` caller and the only
        sweep-scope primitive that supports BOTH captions and R-38 carets
        (``emit_cursors_under`` at numberline.py:370). The shared call-site
        fix covers it automatically — this pins that coverage."""
        n = NumberLinePrimitive("n", {"domain": [0, 5], "label": _LONG_CAPTION})
        n.set_cursors([{"target": "n", "id": "cab", "index": 2, "color": "info"}])
        svg = n.emit_svg()
        cap_bands = _caption_line_bands(svg)
        assert cap_bands, "expected a rendered caption"
        bands = _caret_bands(svg, "n.cursor[cab]")
        for i, band in enumerate(cap_bands):
            bands[f"caption_line_{i}"] = band
        _assert_all_disjoint(bands)


# ---------------------------------------------------------------------------
# Sweep wave (wave 2): the remaining 11 primitives wave 1 never touched
# (bar, codepanel, forest, graph, hashmap, hypercube, linkedlist, matrix,
# tracetable, tree, variablewatch). None of them call ``emit_cursors_under``
# (grep-verified against every primitives/*.py) so no R-38
# ``\cursor{shape}{id=..., at=...}`` binding can ever paint a caret against
# one. ``_cursor_aware_below_baseline()`` therefore must be a hard no-op for
# all 11 -- this is the sweep's byte-stability pin, generalising
# ``TestNoCursorCaptionByteStable`` beyond Array.
# ---------------------------------------------------------------------------

_SWEEP_SCOPE_SPECS: "dict[str, tuple[type, dict]]" = {
    "bar": (Bar, {"data": [1, 2, 3], "label": _LONG_CAPTION}),
    "hashmap": (HashMap, {"capacity": 4, "label": _LONG_CAPTION}),
    "hypercube": (Hypercube, {"bits": 3, "label": _LONG_CAPTION}),
    "linkedlist": (LinkedList, {"data": [1, 2, 3], "label": _LONG_CAPTION}),
    "matrix": (MatrixPrimitive, {"rows": 2, "cols": 2, "label": _LONG_CAPTION}),
    "tracetable": (TraceTable, {"columns": ["i", "j"], "label": _LONG_CAPTION}),
    "variablewatch": (VariableWatch, {"names": ["i", "j"], "label": _LONG_CAPTION}),
    "codepanel": (CodePanel, {"source": "x = 1\ny = 2", "label": _LONG_CAPTION}),
    "forest": (Forest, {"nodes": [0, 1, 2, 3], "label": _LONG_CAPTION}),
    "graph": (Graph, {"nodes": ["a", "b"], "edges": [("a", "b")], "label": _LONG_CAPTION}),
    "tree": (Tree, {"root": "r", "nodes": ["r", "c"], "edges": [("r", "c")], "label": _LONG_CAPTION}),
}


class TestSweepScopeNoCursorSupport:
    """Declaring a bound cursor on any of these 11 primitives must not move
    a byte: ``_cursor_extent_below()`` resolves each entry in ``self._cursors``
    regardless of whether the shape ever paints a caret, so this is the
    guard that ``_cursor_aware_below_baseline()``'s ``max(baseline,
    _cursor_extent_below())`` stays a no-op when the caret side can never
    resolve to anything a real paint call would produce.
    """

    @pytest.mark.parametrize("name", sorted(_SWEEP_SCOPE_SPECS))
    def test_declaring_cursor_is_byte_identical_noop(self, name: str) -> None:
        cls, params = _SWEEP_SCOPE_SPECS[name]
        baseline_svg = cls(name, dict(params)).emit_svg()

        cursored = cls(name, dict(params))
        cursored.set_cursors([{"target": name, "id": "idx", "index": 0, "color": "info"}])
        cursored_svg = cursored.emit_svg()

        assert cursored_svg == baseline_svg, (
            f"{name}: declaring a bound cursor changed the emitted SVG -- "
            "this primitive may now support R-38 carets and needs real "
            "below-band disjointness coverage, not just this no-op pin"
        )
        assert 'aria-roledescription="cursor"' not in cursored_svg
        assert f'data-annotation="{name}.cursor[idx]"' not in cursored_svg


# ---------------------------------------------------------------------------
# Array: the 4th tenant. Wave 1 proved caret + caption + index labels
# disjoint (3-way). A ``position=below`` annotation pill is a 4th
# independent tenant of the same band, and wave 1 never combined it with a
# bound caret. Two distinct collisions existed before
# ``_cursor_aware_below_baseline()`` (base.py):
#
# * same-cell: the caption's scratch-measurement pass ran before the real
#   paint call populated the caret's F2 obstacle box for this frame, so the
#   caption started before the pill's actual (F2-nudged) position.
# * different-cell: F2's obstacle box only spans the caret's own column, so
#   a pill on any *other* cell was never nudged and landed inside the
#   caret's own triangle+id band -- a violation of the caret's
#   column-agnostic contract (a bound caret can slide between cells across
#   steps, so its band must stay clear of every column's pill, not just its
#   own).
# ---------------------------------------------------------------------------


class TestArrayFourTenantDisjoint:
    @pytest.mark.parametrize(
        "same_cell", [True, False], ids=["same_cell", "different_cell"]
    )
    def test_pill_caret_caption_index_all_disjoint(self, same_cell: bool) -> None:
        arr = ArrayPrimitive(
            "arr",
            {"values": [10, 20, 30, 40, 50], "labels": "0..4", "label": _LONG_CAPTION},
        )
        pill_cell = 2
        cursor_cell = 2 if same_cell else 4
        arr.set_cursors(
            [{"target": "arr", "id": "idx", "index": cursor_cell, "color": "info"}]
        )
        arr.set_annotations(
            [
                {
                    "target": f"arr.cell[{pill_cell}]",
                    "label": "pivot label here",
                    "position": "below",
                    "color": "warn",
                }
            ]
        )
        svg = arr.emit_svg()

        cap_bands = _caption_line_bands(svg)
        assert cap_bands, "expected a rendered (wrapped) caption"
        bands: "dict[str, tuple[float, float]]" = {
            f"caption_line_{i}": band for i, band in enumerate(cap_bands)
        }
        bands.update(_caret_bands(svg, "arr.cursor[idx]"))

        id_x, _ = _caret_id_xy(_caret_body(svg, "arr.cursor[idx]"))
        idx_y = _index_label_y_at(svg, id_x)
        bands["index_label_at_caret"] = _hanging_band(idx_y, INDEX_FONT_PX)

        pill_match = re.search(
            r'data-annotation="arr\.cell\[\d+\]-position-below"[^>]*>.*?'
            r'<rect[^>]*\by="([\d.\-]+)"[^>]*\bheight="([\d.\-]+)"',
            svg,
            re.S,
        )
        assert pill_match, "position=below pill rect not found"
        pill_top = float(pill_match.group(1))
        bands["below_pill"] = (pill_top, pill_top + float(pill_match.group(2)))

        _assert_all_disjoint(bands)
