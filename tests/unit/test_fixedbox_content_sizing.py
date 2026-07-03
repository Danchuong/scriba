"""C-sweep: DPTable/Grid/Matrix fixed boxes go content-based, frame-stable.

The fixed 60px (24px matrix) box clipped any content wider than it, math
or plain ($\\max(0,i)$ 64.7px and 1000000 62px clip alike). The fix ports
the Queue/Array monotonic `_cell_width` pattern: seed from init data,
grow in set_value; `_prescan_value_widths` already pushes the max across
the WHOLE timeline before measure/emit, so frame 0 is as wide as the
widest future value — no breathing (investigations/
fixedbox-content-sizing.md).
"""

from __future__ import annotations

from scriba.animation.primitives._types import CELL_WIDTH
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.matrix import MatrixPrimitive


class TestDPTableContentWidth:
    def test_wide_initial_value_widens_cell(self) -> None:
        dp = DPTablePrimitive("dp", {"n": 3, "data": ["1000000", "1", "2"]})
        assert dp._cell_width > CELL_WIDTH
        # cell rect is inset 2px from the pitch
        assert f'width="{dp._cell_width - 2}.0"' in dp.emit_svg()

    def test_applied_value_widens_and_is_frame_stable(self) -> None:
        dp = DPTablePrimitive("dp", {"n": 3})
        before = dp.resolve_annotation_point("dp.cell[2]")
        dp.set_value("cell[1]", "1000000")  # what prescan replays
        after_anchor = dp.resolve_annotation_point("dp.cell[2]")
        assert dp._cell_width > CELL_WIDTH
        # anchor computed AFTER the grow uses the widened pitch
        assert after_anchor[0] > before[0]

    def test_narrow_content_keeps_floor_byte_identical(self) -> None:
        dp = DPTablePrimitive("dp", {"n": 3, "data": ["0", "1", "2"]})
        assert dp._cell_width == CELL_WIDTH
        assert f'width="{CELL_WIDTH - 2}.0"' in dp.emit_svg()

    def test_annotation_anchor_tracks_width(self) -> None:
        wide = DPTablePrimitive("dp", {"n": 3, "data": ["1000000", "1", "2"]})
        narrow = DPTablePrimitive("dp", {"n": 3, "data": ["0", "1", "2"]})
        assert (
            wide.resolve_annotation_point("dp.cell[2]")[0]
            > narrow.resolve_annotation_point("dp.cell[2]")[0]
        )


class TestGridContentWidth:
    def test_wide_value_widens(self) -> None:
        g = GridPrimitive("g", {"rows": 1, "cols": 2, "data": [["1000000", "1"]]})
        assert g._cell_width > CELL_WIDTH

    def test_narrow_keeps_floor(self) -> None:
        g = GridPrimitive("g", {"rows": 1, "cols": 2, "data": [["0", "1"]]})
        assert g._cell_width == CELL_WIDTH

    def test_applied_value_grows(self) -> None:
        g = GridPrimitive("g", {"rows": 1, "cols": 2, "data": [["0", "1"]]})
        g.set_value("cell[0][1]", "1000000")
        assert g._cell_width > CELL_WIDTH


class TestMatrixShowValuesFloor:
    def test_wide_value_floors_cell_size(self) -> None:
        m = MatrixPrimitive(
            "m",
            {"rows": 1, "cols": 2, "data": [[1000000, 1]], "show_values": True},
        )
        assert m.cell_size > 24

    def test_narrow_values_keep_default(self) -> None:
        m = MatrixPrimitive(
            "m", {"rows": 1, "cols": 2, "data": [[1, 2]], "show_values": True}
        )
        assert m.cell_size == 24

    def test_heatmap_without_values_untouched(self) -> None:
        m = MatrixPrimitive(
            "m", {"rows": 1, "cols": 2, "data": [[1000000, 1]]}
        )
        assert m.cell_size == 24
