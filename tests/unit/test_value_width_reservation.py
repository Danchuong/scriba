"""Value-channel width reservation (RQ family B).

An applied ``value=`` (and static ``show_values``) must reserve the width it
is PAINTED at, or a wide value clips its cell / overruns neighbours. Array was
the one cell-box primitive that painted an applied value without growing its
``_cell_width`` envelope; Matrix measured its ``show_values`` reserve at the
pre-growth font but painted at the post-growth font. See
investigations/bmad-rq-valuegrow.md.
"""

from __future__ import annotations

from scriba.animation.primitives._text_metrics import measure_value_text
from scriba.animation.primitives._types import CELL_WIDTH
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.matrix import MatrixPrimitive

WIDE = "1234567890123"  # 118px @14px -> needs ~130px cell (> 60px floor)


class TestArrayValueWidthReservation:
    def test_applied_value_grows_cell_width(self) -> None:
        # prescan replays set_value per frame; the applied value must widen
        # the reserved envelope (was a no-op: stayed 60).
        a = ArrayPrimitive("a", {"size": 6, "data": [1, 2, 3, 4, 5, 6]})
        a.set_value("cell[0]", WIDE)
        assert a._cell_width >= measure_value_text(WIDE, 14) + 12

    def test_applied_value_frame_stable_pitch(self) -> None:
        # widened cell -> widened pitch, uniform across cells (R-32 stable).
        a = ArrayPrimitive("a", {"size": 6})
        a.set_value("cell[3]", WIDE)
        c0 = a.resolve_annotation_point("a.cell[0]")[0]
        c1 = a.resolve_annotation_point("a.cell[1]")[0]
        assert (c1 - c0) >= 130

    def test_narrow_value_keeps_default_cell_width(self) -> None:
        # GREEN guard: a value under the 60px floor never grows -> byte-stable.
        a = ArrayPrimitive("a", {"size": 6, "data": [1, 2, 3, 4, 5, 6]})
        a.set_value("cell[0]", "picked")  # 56px < 60
        assert a._cell_width == CELL_WIDTH


class TestMatrixShowValuesFont:
    def test_paint_font_fits_reserved_cell(self) -> None:
        # reserve font must equal paint font, so the painted extent fits.
        m = MatrixPrimitive(
            "m", {"rows": 1, "cols": 1, "data": [[-1234.5]], "show_values": True}
        )
        fmt = m._format_value(-1234.5)
        assert measure_value_text(fmt, m._value_font_px) + 4 <= m.cell_size

    def test_narrow_matrix_unchanged(self) -> None:
        # GREEN guard: single-decimal values never grow the cell.
        m = MatrixPrimitive(
            "m",
            {"rows": 2, "cols": 2, "data": [[0.1, 0.5], [0.9, 1.0]], "show_values": True},
        )
        assert m.cell_size == 24
