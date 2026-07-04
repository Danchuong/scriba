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
