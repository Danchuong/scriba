"""P0 of the unified decoration plan: 2-D ``block[r0:r1][c0:c1]`` selector.

Grid (and 2-D DPTable) had no area selector — only ``cell[r][c]`` and
``all`` — so an area whose meaning IS its size (the (m-1)^2 base block in
CSES 1071) could not be recolored or annotated as a unit
(investigations/feat-grid-block-selector.md, unified-decoration-model.md).

Inclusive on both ends, mirroring the 1-D ``range[lo:hi]`` convention.
"""

from __future__ import annotations

from scriba.animation._frame_renderer import _expand_selectors
from scriba.animation.parser.selectors import parse_selector
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.grid import GridPrimitive


def _grid() -> GridPrimitive:
    return GridPrimitive(
        "g", {"rows": 3, "cols": 3, "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
    )


class TestParse:
    def test_block_parses_and_round_trips(self) -> None:
        from scriba.animation.scene import _selector_to_str

        sel = parse_selector("g.block[0:1][0:2]")
        assert _selector_to_str(sel) == "g.block[0:1][0:2]"

    def test_block_interpolation_ref_fields(self) -> None:
        # ${...} in any of the 4 indices resolves through the generic
        # fields(acc) walk in scene._resolve_selector — dataclass fields
        # must therefore hold the 4 index expressions directly
        from dataclasses import fields

        sel = parse_selector("g.block[0:1][0:1]")
        acc = sel.accessor
        assert len(fields(acc)) == 4


class TestExpand:
    def test_recolor_block_expands_to_cell_product(self) -> None:
        state = {"g.block[0:1][0:1]": {"state": "done"}}
        out = _expand_selectors(state, "g", _grid())
        assert set(out) == {
            "g.cell[0][0]", "g.cell[0][1]", "g.cell[1][0]", "g.cell[1][1]"
        }
        assert all(v["state"] == "done" for v in out.values())

    def test_block_merge_preserves_highlight(self) -> None:
        state = {
            "g.block[0:0][0:1]": {"state": "done"},
            "g.cell[0][0]": {"highlighted": True},
        }
        out = _expand_selectors(state, "g", _grid())
        assert out["g.cell[0][0]"]["highlighted"] is True
        assert out["g.cell[0][0]"]["state"] == "done"


class TestValidateAndAnchor:
    def test_grid_validates_block_bounds(self) -> None:
        g = _grid()
        assert g.validate_selector("block[0:1][0:1]")
        assert g.validate_selector("block[0:2][2:2]")
        assert not g.validate_selector("block[0:3][0:1]")  # row OOB
        assert not g.validate_selector("block[1:0][0:1]")  # reversed

    def test_grid_block_anchor_is_block_center(self) -> None:
        g = _grid()
        pt = g.resolve_annotation_point("g.block[0:1][0:1]")
        assert pt is not None
        cell00 = g.resolve_annotation_point("g.cell[0][0]")
        cell11 = g.resolve_annotation_point("g.cell[1][1]")
        assert pt[0] == (cell00[0] + cell11[0]) / 2
        assert pt[1] == (cell00[1] + cell11[1]) / 2

    def test_grid_block_box_is_union_rect(self) -> None:
        box = _grid().resolve_annotation_box("g.block[0:1][0:1]")
        assert box is not None
        # spans exactly cells (0,0)..(1,1)
        assert box.x == 0.0 and box.y == 0.0

    def test_dptable_2d_block(self) -> None:
        dp = DPTablePrimitive(
            "dp", {"rows": 2, "cols": 3, "data": ["1", "2", "3", "4", "5", "6"]}
        )
        assert dp.validate_selector("block[0:1][1:2]")
        assert dp.resolve_annotation_point("dp.block[0:1][1:2]") is not None

    def test_1d_primitive_rejects_block(self) -> None:
        dp1 = DPTablePrimitive("dp", {"n": 4})
        assert not dp1.validate_selector("block[0:1][0:1]")
