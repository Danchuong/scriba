"""Shared-obstacle model — ``\\trace`` mid-label + stroke registration.

Two mechanisms (investigations/design-shared-obstacle.md):

* (a) the ``\\trace`` mid-vertex LABEL routes through the shared ``_place_pill``
  scorer (replacing the old x-only grid clamp), so it slides off the cells it
  grazed. Every trace label sat ~12 px into the row it labels (the "near-miss
  over cell backgrounds"); the placer lifts its midline out of that band.
* (b) the ``\\trace`` STROKE — a polyline threading cell centres, which cannot
  itself dodge — is REGISTERED as a SHOULD ``segment`` obstacle so a LATER pill
  dodges it. The stroke bytes stay identical (registering never moves the
  registrant); only the other pill moves.

Bands: an SVG ``<rect>`` covers ``[y, y+h]``; a stroke of width ``w`` centred
on ``y`` covers ``[y-w/2, y+w/2]``.
"""

from __future__ import annotations

import re

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.grid import GridPrimitive


def _trace_label_rect(svg: str, tid: str = "t0") -> tuple[float, float, float, float]:
    m = re.search(
        r'data-annotation="g\.trace\[' + tid + r'\]-solo"[^>]*>(.*?)</g>', svg, re.S
    )
    assert m, "trace group missing"
    r = re.search(
        r'<rect x="([\d.-]+)" y="([\d.-]+)" width="(\d+)" height="(\d+)"', m.group(1)
    )
    assert r, "trace label rect missing"
    return tuple(float(v) for v in r.groups())  # type: ignore[return-value]


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _cell_y_overlap(rect: tuple[float, float, float, float], cells) -> float:
    """Total vertical overlap of the label band with every cell it shares an
    x-column with (the content occlusion the placer minimises)."""
    rx, ry, rw, rh = rect
    total = 0.0
    for b in cells:
        if _overlap(rx, rx + rw, b.x, b.x + b.width) > 0:
            total += _overlap(ry, ry + rh, b.y, b.y + b.height)
    return total


# ---------------------------------------------------------------------------
# (a) mid-label routes through the placer — lifts off the cells it grazed
# ---------------------------------------------------------------------------


class TestTraceLabelDodgesCells:
    def test_label_midline_lifts_out_of_traced_row(self) -> None:
        """Trace on the TOP row of a 2-row grid: the label's natural seat sits
        ~12 px into row 0 (band bottom at 12 vs cell top 0). The placer lifts
        its midline above the row and cuts the cell overlap."""
        g = GridPrimitive("g", {"rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]})
        g.set_traces(
            [{"id": "t0", "cells": [[0, 0], [0, 1]], "color": "good", "label": "hi"}]
        )
        svg = g.emit_svg()
        rx, ry, rw, rh = _trace_label_rect(svg)
        cells = g.resolve_self_content_rects()

        # Natural seat (pre-placer): centred above the mid vertex.
        midx, midy = g.resolve_trace_point("g.cell[0][1]")
        nat_ry = midy - rh - 8
        nat_overlap = _cell_y_overlap((rx, nat_ry, rw, rh), cells)
        emit_overlap = _cell_y_overlap((rx, ry, rw, rh), cells)

        # The label's midline is now above the traced row's cells (row 0 top=0).
        assert ry + rh / 2.0 < 0.0, (
            f"label midline {ry + rh / 2.0} not lifted above the grid top"
        )
        # And it occludes strictly less cell area than its natural seat.
        assert emit_overlap < nat_overlap, (
            f"label overlap not reduced (emit={emit_overlap}, natural={nat_overlap})"
        )


# ---------------------------------------------------------------------------
# (b) stroke registered as an obstacle — a later pill dodges it, stroke frozen
# ---------------------------------------------------------------------------


class TestTraceStrokeAsObstacle:
    def _grid_traced_inside_pill(self) -> str:
        # Trace threads the MIDDLE row (stroke at y=62, band [60.75,63.25]).
        g = GridPrimitive(
            "g", {"rows": 3, "cols": 3, "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        )
        g.set_traces([{"id": "t0", "cells": [[1, 0], [1, 1], [1, 2]], "color": "good"}])
        g.set_annotations([{"target": "g.cell[1][1]", "label": "P", "position": "inside"}])
        return g.emit_svg()

    def test_inside_pill_dodges_trace_stroke(self) -> None:
        """An inside pill on a traced cell would sit on the row-centre stroke
        (band y[49,68] over stroke [60.75,63.25] pre-fix). With the stroke
        registered, the pill lifts clear of the stroke band."""
        svg = self._grid_traced_inside_pill()
        m = re.search(
            r'data-annotation="g.cell\[1\]\[1\]-position-inside"(.*?)</g>', svg, re.S
        )
        assert m, "inside pill missing"
        r = re.search(
            r'<rect x="([\d.-]+)" y="([\d.-]+)" width="([\d.]+)" height="([\d.]+)"',
            m.group(1),
        )
        assert r, "inside pill rect missing"
        _, py, _, ph = (float(v) for v in r.groups())
        stroke_lo, stroke_hi = 60.75, 63.25  # y=62, stroke-width 2.5
        assert _overlap(py, py + ph, stroke_lo, stroke_hi) == 0.0, (
            f"inside pill band [{py},{py + ph}] still crosses trace stroke "
            f"[{stroke_lo},{stroke_hi}]"
        )

    def test_stroke_bytes_unchanged_by_registration(self) -> None:
        """Registering the stroke as an obstacle must not move the stroke —
        the ``<path>``/``<polygon>`` bytes are identical to a plain trace."""
        g = GridPrimitive(
            "g", {"rows": 3, "cols": 3, "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        )
        g.set_traces([{"id": "t0", "cells": [[2, 0], [2, 1], [2, 2]], "color": "good"}])
        svg = g.emit_svg()
        body = re.search(
            r'data-annotation="g\.trace\[t0\]-solo"[^>]*>(.*?)</g>', svg, re.S
        ).group(1)
        assert body == (
            '<path d="M30.0,104.0 L92.0,104.0 L154.0,104.0" fill="none"'
            ' stroke="#027a55" stroke-width="2.5" stroke-linecap="round"'
            ' stroke-linejoin="round" opacity="0.85"/>'
            '<polygon points="154.0,104.0 147.0,107.5 147.0,100.5" fill="#027a55"/>'
        )


class TestTraceStrokeRegisteredEvenWithoutLabel:
    def test_segments_registered_on_array(self) -> None:
        """emit_traces_under stashes the stroke segments regardless of a label,
        so emit_annotation_arrows can consume them."""
        a = ArrayPrimitive("arr", {"values": [10, 20, 30]})
        a.set_traces([{"id": "t0", "cells": [0, 1, 2], "color": "good"}])
        a.emit_svg()
        segs = getattr(a, "_trace_obstacle_segments", None)
        assert segs, "trace stroke segments not registered"
        assert all(s.kind == "segment" for s in segs)
        assert len(segs) == 2  # 3 cells -> 2 segments
