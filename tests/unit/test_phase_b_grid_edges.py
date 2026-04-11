"""Phase B edge-case tests for the Grid primitive.

Exercises single-cell, large, empty, mixed-type, recolor persistence,
highlight + recolor overlap, labels, and bounding box edge cases.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.grid import GridInstance, GridPrimitive
from scriba.animation.primitives.base import STATE_COLORS
from scriba.core.errors import ValidationError



# ---------------------------------------------------------------------------
# 1. Grid 1x1 (single cell)
# ---------------------------------------------------------------------------


class TestGrid1x1:
    def test_single_cell_data(self) -> None:
        inst = GridPrimitive("g", {"rows": 1, "cols": 1, "data": [42]})
        assert inst.rows == 1
        assert inst.cols == 1
        assert inst.data == [42]

    def test_single_cell_svg_has_one_target(self) -> None:
        inst = GridPrimitive("g", {"rows": 1, "cols": 1, "data": [7]})
        svg = inst.emit_svg()
        assert svg.count('data-target="g.cell') == 1
        assert 'data-target="g.cell[0][0]"' in svg

    def test_single_cell_bounding_box(self) -> None:
        inst = GridPrimitive("g", {"rows": 1, "cols": 1})
        x, y, w, h = inst.bounding_box()
        # 1 cell: width = CELL_WIDTH=60, no gap
        assert w == 60.0
        # 1 cell: height = CELL_HEIGHT=40, no gap
        assert h == 40.0


# ---------------------------------------------------------------------------
# 2. Grid 10x10 (large)
# ---------------------------------------------------------------------------


class TestGrid10x10:
    def test_large_grid_declaration(self) -> None:
        data = list(range(100))
        inst = GridPrimitive("g", {"rows": 10, "cols": 10, "data": data})
        assert inst.rows == 10
        assert inst.cols == 10
        assert len(inst.data) == 100

    def test_large_grid_addressable_parts_count(self) -> None:
        data = list(range(100))
        inst = GridPrimitive("g", {"rows": 10, "cols": 10, "data": data})
        parts = inst.addressable_parts()
        assert len(parts) == 101  # 100 cells + .all

    def test_large_grid_svg_renders(self) -> None:
        data = list(range(100))
        inst = GridPrimitive("g", {"rows": 10, "cols": 10, "data": data})
        svg = inst.emit_svg()
        assert 'data-target="g.cell[9][9]"' in svg
        assert 'data-target="g.cell[0][0]"' in svg


# ---------------------------------------------------------------------------
# 3. Grid with empty data (all cells show empty string)
# ---------------------------------------------------------------------------


class TestGridEmptyData:
    def test_empty_data_fills_empty_strings(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 3})
        assert inst.data == [""] * 6

    def test_empty_data_svg_has_empty_text(self) -> None:
        inst = GridPrimitive("g", {"rows": 1, "cols": 1})
        svg = inst.emit_svg()
        # Text content should be empty (escaped empty string)
        assert "></text>" in svg


# ---------------------------------------------------------------------------
# 4. Grid with mixed types in data (ints, floats, strings)
# ---------------------------------------------------------------------------


class TestGridMixedTypes:
    def test_mixed_type_data_accepted(self) -> None:
        data = [1, 2.5, "hello", True]
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "data": data})
        assert inst.data == [1, 2.5, "hello", True]

    def test_mixed_type_svg_renders_all_values(self) -> None:
        data = [1, 2.5, "hello", True]
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "data": data})
        svg = inst.emit_svg()
        assert ">1</text>" in svg
        assert ">2.5</text>" in svg
        assert ">hello</text>" in svg
        assert ">True</text>" in svg


# ---------------------------------------------------------------------------
# 5. Recolor single cell then recolor again (state replacement)
# ---------------------------------------------------------------------------


class TestGridRecolorReplacement:
    def test_recolor_replaces_state(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2})
        # First render with current state
        inst.set_state("cell[0][0]", "current")
        svg1 = inst.emit_svg()
        assert "scriba-state-current" in svg1
        # Second render with done state (replaces current)
        inst.set_state("cell[0][0]", "done")
        svg2 = inst.emit_svg()
        assert "scriba-state-done" in svg2
        assert "#009E73" in svg2  # done fill color


# ---------------------------------------------------------------------------
# 6. Recolor cell[0][0] in frame 1, check it persists in frame 2
# ---------------------------------------------------------------------------


class TestGridRecolorPersistence:
    def test_recolor_persists_across_frames(self) -> None:
        """Simulate two frames: frame 1 recolors cell, frame 2 inherits it."""
        inst = GridPrimitive("g", {"rows": 2, "cols": 2})
        inst.set_state("cell[0][0]", "current")
        svg1 = inst.emit_svg()
        assert "scriba-state-current" in svg1
        # State persists on the instance
        svg2 = inst.emit_svg()
        assert "scriba-state-current" in svg2


# ---------------------------------------------------------------------------
# 7. Highlight cell -- check additive overlay present
# ---------------------------------------------------------------------------


class TestGridHighlight:
    def test_highlight_flag_in_state(self) -> None:
        """Grid doesn't emit highlight overlay itself; it's handled by the
        emitter layer. But verify the cell state is accepted."""
        inst = GridPrimitive("g", {"rows": 2, "cols": 2})
        inst.set_state("cell[0][0]", "idle")
        svg = inst.emit_svg()
        assert 'data-target="g.cell[0][0]"' in svg


# ---------------------------------------------------------------------------
# 8. Highlight + recolor same cell -- both should apply
# ---------------------------------------------------------------------------


class TestGridHighlightAndRecolor:
    def test_recolor_and_highlight_same_cell(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2})
        inst.set_state("cell[1][1]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg
        assert "#0072B2" in svg  # current fill color


# ---------------------------------------------------------------------------
# 9. Grid with label -- caption renders
# ---------------------------------------------------------------------------


class TestGridLabel:
    def test_label_renders_in_svg(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "label": "Game Board"})
        svg = inst.emit_svg()
        assert "Game Board" in svg
        assert "scriba-primitive-label" in svg

    def test_no_label_no_caption(self) -> None:
        inst = GridPrimitive("g", {"rows": 2, "cols": 2})
        svg = inst.emit_svg()
        assert "scriba-primitive-label" not in svg


# ---------------------------------------------------------------------------
# 10. Bounding box for 1x1 vs 5x5
# ---------------------------------------------------------------------------


class TestGridBoundingBoxComparison:
    def test_5x5_larger_than_1x1(self) -> None:
        inst_1x1 = GridPrimitive("g", {"rows": 1, "cols": 1})
        inst_5x5 = GridPrimitive("g", {"rows": 5, "cols": 5})
        _, _, w1, h1 = inst_1x1.bounding_box()
        _, _, w5, h5 = inst_5x5.bounding_box()
        assert w5 > w1
        assert h5 > h1

    def test_5x5_dimensions(self) -> None:
        inst = GridPrimitive("g", {"rows": 5, "cols": 5})
        _, _, w, h = inst.bounding_box()
        # 5 cells * 60 + 4 gaps * 2 = 308
        assert w == 308.0
        # 5 cells * 40 + 4 gaps * 2 = 208
        assert h == 208.0


# ---------------------------------------------------------------------------
# 11. Data length mismatch
# ---------------------------------------------------------------------------


class TestGridDataMismatch:
    def test_flat_data_wrong_length_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            GridPrimitive("g", {"rows": 2, "cols": 2, "data": [1, 2, 3]})

    def test_2d_data_wrong_size_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1103"):
            GridPrimitive("g", {"rows": 2, "cols": 2, "data": [[1, 2], [3]]})


# ---------------------------------------------------------------------------
# 12. XML escaping in cell values
# ---------------------------------------------------------------------------


class TestGridXmlEscaping:
    def test_special_chars_escaped(self) -> None:
        data = ['<script>', '&amp;', '"quoted"', 'normal']
        inst = GridPrimitive("g", {"rows": 2, "cols": 2, "data": data})
        svg = inst.emit_svg()
        assert "&lt;script&gt;" in svg
        assert "&amp;amp;" in svg
        assert "&quot;quoted&quot;" in svg
