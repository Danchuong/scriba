"""The two silent traps + two generality holes from the docs audits
(investigations/docs-{author,generality}-audit.md)."""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.scene import SceneState, _selector_to_str


def _scene(src: str, bindings: dict | None = None):
    ir = SceneParser().parse(src)
    sc = SceneState()
    sc.apply_prelude(ir.shapes, ir.prelude_commands, ir.prelude_compute)
    if bindings:
        sc.bindings.update(bindings)
    snaps = [sc.apply_frame(f) for f in ir.frames]
    return ir, sc, snaps


class TestComputedSelectorIndex:
    SRC = (
        "\\shape{g}{Grid}{rows=3, cols=3, data=[[1,2,3],[4,5,6],[7,8,9]]}\n"
        "\\step\n"
        "\\recolor{g.cell[${rows[k]}][${k}]}{state=done}\n"
    )

    def test_dynamic_subscript_resolves_to_element(self) -> None:
        _, sc, snaps = _scene(self.SRC, bindings={"rows": [2, 0], "k": 1})
        keys = set(snaps[0].shape_states["g"].keys())
        # rows[k] with k=1 -> rows[1] == 0 -> g.cell[0][1]
        assert "g.cell[0][1]" in keys, keys

    def test_unresolvable_subscript_is_loud(self) -> None:
        from scriba.core.errors import ScribaError

        src = (
            "\\shape{g}{Grid}{rows=2, cols=2, data=[[1,2],[3,4]]}\n"
            "\\step\n"
            "\\recolor{g.cell[${layer}][0]}{state=done}\n"
        )
        with pytest.raises(ScribaError) as ei:
            _scene(src, bindings={"layer": [[0, 0], [1, 1]]})
        assert "E1159" in str(ei.value)


class TestBulkApplyFeedsCaret:
    SRC = (
        "\\shape{a}{Array}{size=4, data=[1,2,3,4]}\n"
        "\\shape{w}{VariableWatch}{names=[\"i\"], label=\"w\"}\n"
        "\\cursor{a}{id=i, at=\"w.var[i]\"}\n"
        "\\step\n"
        "\\apply{w}{i=2}\n"
    )

    def test_bulk_apply_mirrors_var_entry(self) -> None:
        _, sc, snaps = _scene(self.SRC)
        ts = snaps[0].shape_states["w"].get("w.var[i]")
        assert ts is not None and ts.value == "2"

    def test_bulk_on_non_watch_not_mirrored(self) -> None:
        src = (
            "\\shape{a}{Array}{size=4, data=[1,2,3,4]}\n"
            "\\step\n"
            "\\apply{a}{insert={at=1, value=9}}\n"
        )
        _, sc, snaps = _scene(src)
        assert "a.var[insert]" not in snaps[0].shape_states["a"]


class TestHiddenStateCss:
    def test_css_hides_hidden_state_groups(self) -> None:
        from pathlib import Path

        css = Path("scriba/animation/static/scriba-scene-primitives.css").read_text()
        assert ".scriba-state-hidden" in css
        i = css.index(".scriba-state-hidden")
        block = css[i:css.index("}", i)]
        assert "display" in block and "none" in block

    def test_array_emits_hidden_class(self) -> None:
        from scriba.animation.primitives.array import ArrayPrimitive

        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        a.set_state("cell[1]", "hidden")
        assert "scriba-state-hidden" in a.emit_svg()


class TestValueWriteKeepsExpandedState:
    """A value-only \\apply must not clobber a state applied to the same
    cell through a different key (row/col/diag/block/range expansion).

    Root cause of the Gauss-pattern trap: ShapeTargetState defaulted
    state="idle", so renderer emitted state:"idle" for value-only
    entries and the _expand_selectors merge let it beat the expanded
    "done"/"current" (docs pass-3 W1 browser catch)."""

    @staticmethod
    def _expanded(src: str, shape: str, prim) -> dict:
        from scriba.animation._frame_renderer import _expand_selectors
        from scriba.animation.renderer import _snapshot_to_frame_data
        from scriba.core.context import RenderContext

        ir = SceneParser().parse(src)
        sc = SceneState()
        sc.apply_prelude(ir.shapes, ir.prelude_commands, ir.prelude_compute)
        snaps = [sc.apply_frame(f) for f in ir.frames]
        ctx = RenderContext(
            resource_resolver=lambda name: f"/resources/{name}",
            theme="light",
            dark_mode=False,
            metadata={},
            render_inline_tex=None,
        )
        fd = _snapshot_to_frame_data(snaps[0], total_frames=1, scene_id="s", ctx=ctx)
        return _expand_selectors(fd.shape_states.get(shape, {}), shape, prim)

    def test_diag_state_survives_value_write(self) -> None:
        from scriba.animation.primitives.matrix import MatrixPrimitive

        src = (
            "\\shape{m}{Matrix}{rows=3, cols=3,"
            " data=[[1,2,3],[4,5,6],[7,8,9]], show_values=true}\n"
            "\\step\n"
            "\\recolor{m.diag}{state=done}\n"
            "\\apply{m.cell[0][0]}{value=9}\n"
        )
        prim = MatrixPrimitive("m", {"rows": 3, "cols": 3,
                                     "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]})
        out = self._expanded(src, "m", prim)
        cell = out["m.cell[0][0]"]
        assert cell.get("state") == "done", out
        assert cell.get("value") == "9", out

    def test_row_state_survives_value_write(self) -> None:
        from scriba.animation.primitives.grid import GridPrimitive

        src = (
            "\\shape{g}{Grid}{rows=2, cols=2, data=[[1,2],[3,4]]}\n"
            "\\step\n"
            "\\recolor{g.row[0]}{state=current}\n"
            "\\apply{g.cell[0][1]}{value=7}\n"
        )
        prim = GridPrimitive("g", {"rows": 2, "cols": 2,
                                   "data": [[1, 2], [3, 4]]})
        out = self._expanded(src, "g", prim)
        cell = out["g.cell[0][1]"]
        assert cell.get("state") == "current", out
        assert cell.get("value") == "7", out


class TestMatrixBlock:
    def test_validate_and_anchor(self) -> None:
        from scriba.animation.primitives.matrix import MatrixPrimitive

        m = MatrixPrimitive("m", {"rows": 3, "cols": 3,
                                  "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]})
        assert m.validate_selector("block[0:1][0:1]")
        assert not m.validate_selector("block[2:1][0:1]")
        pt = m.resolve_annotation_point("m.block[0:1][0:1]")
        c00 = m.resolve_annotation_point("m.cell[0][0]")
        c11 = m.resolve_annotation_point("m.cell[1][1]")
        assert pt == ((c00[0] + c11[0]) / 2, (c00[1] + c11[1]) / 2)

    def test_block_box_spans_corners(self) -> None:
        # bracket=true needs a box (position-independent, like Grid's block
        # branch) or the annotation degrades to a plain position pill
        from scriba.animation.primitives.matrix import MatrixPrimitive

        m = MatrixPrimitive("m", {"rows": 3, "cols": 3,
                                  "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]})
        box = m.resolve_annotation_box("m.block[0:1][0:1]")
        assert box is not None
        c00 = m.resolve_annotation_point("m.cell[0][0]")
        c11 = m.resolve_annotation_point("m.cell[1][1]")
        # box center == block anchor midpoint
        assert box.x + box.width / 2 == pytest.approx((c00[0] + c11[0]) / 2, abs=1)
        assert box.y + box.height / 2 == pytest.approx((c00[1] + c11[1]) / 2, abs=1)
        assert m.resolve_annotation_box("m.block[0:3][0:1]") is None  # OOB

    def test_dptable_2d_block_box(self) -> None:
        # sibling of the Matrix gap: DPTable-2D bracket needs the same
        # position-independent block box
        from scriba.animation.primitives.dptable import DPTablePrimitive

        dp = DPTablePrimitive(
            "dp", {"rows": 2, "cols": 3, "data": ["1", "2", "3", "4", "5", "6"]}
        )
        box = dp.resolve_annotation_box("dp.block[0:1][1:2]")
        assert box is not None
        cx, cy = dp._block_center("dp.block[0:1][1:2]")
        assert box.x + box.width / 2 == pytest.approx(cx)
        assert box.y + box.height / 2 == pytest.approx(cy)
        assert dp.resolve_annotation_box("dp.block[0:2][0:0]") is None  # OOB
