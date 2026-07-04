"""Named binding-caret ``\\cursor`` — the slide-and-bind multi-cursor (R-38).

Case file: investigations/anim-multicursor.md (A-4 marker law in
investigations/anim-unified-motion-model.md).

New-form ``\\cursor{shape}{id=i, at="w.var[i]", color="state:current"}`` is
discriminated from the legacy ``\\cursor{targets}{index}`` recolor-hop by the
``id=`` key. It emits a ``▲`` caret inside
``<g data-annotation="{shape}.cursor[{id}]-solo">`` (the annotation structure
contract, so ``annotation_add``/``annotation_remove`` fade it for free), binds
its cell index to a VariableWatch value re-resolved every frame, and rides a
new ``cursor_move`` transition when that index changes.

RED-first: mirrors tests/unit/test_trace_primitive.py.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.differ import compute_transitions
from scriba.animation.emitter import FrameData
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.renderer import AnimationRenderer, _snapshot_to_frame_data
from scriba.animation.scene import CursorEntry, SceneState, ShapeTargetState
from scriba.core.context import RenderContext
from scriba.core.errors import ScribaError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cursor_cmds(ir):
    return [
        c
        for f in ir.frames
        for c in f.commands
        if type(c).__name__ == "CursorCommand"
    ]


def _ctx(collector=None):
    return RenderContext(
        resource_resolver=lambda name: f"/resources/{name}",
        metadata={"output_mode": "interactive"},
        warnings_collector=collector,
    )


def _render(body: str) -> str:
    renderer = AnimationRenderer()
    source = '\\begin{animation}[id="cursor-test"]\n' + body + "\n\\end{animation}"
    blocks = renderer.detect(source)
    assert len(blocks) == 1
    return renderer.render_block(blocks[0], _ctx()).html


_TWO_POINTER = """\\shape{arr}{Array}{values=[10,20,30,40,50]}
\\shape{w}{VariableWatch}{names=["i"]}
\\step
\\apply{w.var[i]}{value=1}
\\cursor{arr}{id=i, at="w.var[i]"}
\\step
\\apply{w.var[i]}{value=3}
\\cursor{arr}{id=i, at="w.var[i]"}
"""


# ---------------------------------------------------------------------------
# Grammar — legacy compat + new form discrimination
# ---------------------------------------------------------------------------


class TestGrammar:
    def test_legacy_cursor_still_parses(self) -> None:
        # 232-token backward-compat surface: bare-index arg stays legacy.
        ir = SceneParser().parse(
            "\\shape{a}{Array}{size=4}\n\\step\n\\cursor{a.cell}{3}\n"
        )
        cmds = _cursor_cmds(ir)
        assert len(cmds) == 1
        assert cmds[0].index == 3
        assert cmds[0].targets == ("a.cell",)
        # New optional fields default to None on the legacy path.
        assert cmds[0].cursor_id is None
        assert cmds[0].at is None
        assert cmds[0].color is None

    def test_legacy_cursor_with_states_unchanged(self) -> None:
        ir = SceneParser().parse(
            "\\shape{a}{Array}{size=4}\n\\step\n"
            "\\cursor{a.cell}{2, prev_state=done, curr_state=current}\n"
        )
        cmd = _cursor_cmds(ir)[0]
        assert cmd.index == 2
        assert cmd.prev_state == "done"
        assert cmd.curr_state == "current"
        assert cmd.cursor_id is None

    def test_new_form_parses_id_at_color(self) -> None:
        ir = SceneParser().parse(
            "\\shape{arr}{Array}{size=5}\n\\step\n"
            '\\cursor{arr}{id=i, at="w.var[i]", color="state:current"}\n'
        )
        cmd = _cursor_cmds(ir)[0]
        assert cmd.cursor_id == "i"
        assert cmd.at == "w.var[i]"          # quotes stripped
        assert cmd.color == "state:current"  # quotes stripped
        assert cmd.targets == ("arr",)

    def test_new_form_at_literal_int(self) -> None:
        ir = SceneParser().parse(
            "\\shape{arr}{Array}{size=5}\n\\step\n"
            "\\cursor{arr}{id=j, at=3}\n"
        )
        cmd = _cursor_cmds(ir)[0]
        assert cmd.cursor_id == "j"
        assert cmd.at == "3"

    def test_new_form_bad_at_raises_e1183(self) -> None:
        # v1 accepts INT | "shape.var[name]" only; a cell selector is rejected.
        with pytest.raises(ScribaError) as ei:
            SceneParser().parse(
                "\\shape{arr}{Array}{size=5}\n\\step\n"
                '\\cursor{arr}{id=i, at="arr.cell[2]"}\n'
            )
        assert "E1183" in str(ei.value)

    def test_new_form_default_color_info(self) -> None:
        ir = SceneParser().parse(
            "\\shape{arr}{Array}{size=5}\n\\step\n"
            "\\cursor{arr}{id=i, at=0}\n"
        )
        assert _cursor_cmds(ir)[0].color == "info"


# ---------------------------------------------------------------------------
# Scene — CursorEntry, update-in-place, ephemeral
# ---------------------------------------------------------------------------


def _apply_source(source: str) -> SceneState:
    """Parse + drive a SceneState through the full IR, returning it after
    the last frame so ``.cursors`` reflects the settled scene."""
    ir = SceneParser().parse(source)
    st = SceneState()
    st.apply_prelude(ir.shapes, ir.prelude_commands)
    for frame in ir.frames:
        st.apply_frame(frame)
    return st


class TestSceneEntry:
    def test_new_cursor_creates_entry(self) -> None:
        st = _apply_source(
            "\\shape{arr}{Array}{size=5}\n\\step\n"
            "\\cursor{arr}{id=i, at=2}\n"
        )
        assert len(st.cursors) == 1
        entry = st.cursors[0]
        assert isinstance(entry, CursorEntry)
        assert entry.target == "arr"
        assert entry.cursor_id == "i"
        assert entry.at == "2"

    def test_same_id_updates_in_place(self) -> None:
        st = _apply_source(
            "\\shape{arr}{Array}{size=5}\n"
            "\\step\n\\cursor{arr}{id=i, at=1}\n"
            "\\step\n\\cursor{arr}{id=i, at=4}\n"
        )
        # A re-issue of the same (shape, id) replaces — it is a *move*.
        matching = [c for c in st.cursors if c.cursor_id == "i"]
        assert len(matching) == 1
        assert matching[0].at == "4"

    def test_distinct_ids_coexist(self) -> None:
        st = _apply_source(
            "\\shape{arr}{Array}{size=5}\n\\step\n"
            "\\cursor{arr}{id=i, at=0}\n"
            "\\cursor{arr}{id=j, at=4}\n"
        )
        ids = sorted(c.cursor_id for c in st.cursors)
        assert ids == ["i", "j"]

    def test_ephemeral_cursor_clears_next_step(self) -> None:
        st = _apply_source(
            "\\shape{arr}{Array}{size=5}\n"
            "\\step\n\\cursor{arr}{id=i, at=1, ephemeral=true}\n"
            "\\step\n\\apply{arr.cell[0]}{value=x}\n"
        )
        assert st.cursors == []

    def test_undeclared_shape_raises_e1116(self) -> None:
        with pytest.raises(ScribaError) as ei:
            _apply_source(
                "\\shape{arr}{Array}{size=5}\n\\step\n"
                "\\cursor{ghost}{id=i, at=0}\n"
            )
        assert "E1116" in str(ei.value)


# ---------------------------------------------------------------------------
# Binding resolve — build phase in the renderer
# ---------------------------------------------------------------------------


class TestBindingResolve:
    def _frame_data(self, at: str, value: str | None, collector=None):
        st = SceneState()
        st.shape_states["arr"] = {}
        st.shape_states["w"] = (
            {"w.var[i]": ShapeTargetState(value=value)} if value is not None else {}
        )
        st.cursors = [CursorEntry(target="arr", cursor_id="i", at=at, color="info")]
        snap = st.snapshot(1)
        return _snapshot_to_frame_data(snap, 1, "scene-x", _ctx(collector))

    def test_literal_at_resolves_index(self) -> None:
        fd = self._frame_data(at="3", value=None)
        entry = next(c for c in fd.cursors if c["id"] == "i")
        assert entry["index"] == 3

    def test_bind_reads_watch_value(self) -> None:
        fd = self._frame_data(at="w.var[i]", value="2")
        entry = next(c for c in fd.cursors if c["id"] == "i")
        assert entry["index"] == 2

    def test_unparseable_binding_soft_drops(self) -> None:
        collector: list = []
        fd = self._frame_data(at="w.var[i]", value="----", collector=collector)
        assert all(c["id"] != "i" for c in (fd.cursors or []))
        assert any(w.code == "E1184" for w in collector)
        assert all(w.severity == "info" for w in collector if w.code == "E1184")

    def test_missing_watch_var_soft_drops(self) -> None:
        collector: list = []
        fd = self._frame_data(at="w.var[i]", value=None, collector=collector)
        assert all(c["id"] != "i" for c in (fd.cursors or []))
        assert any(w.code == "E1184" for w in collector)


# ---------------------------------------------------------------------------
# Emit — the caret glyph on the target primitive
# ---------------------------------------------------------------------------


def _array_with_cursor(index: int, cid: str = "i", color: str = "info") -> str:
    arr = ArrayPrimitive("arr", {"values": [10, 20, 30, 40, 50]})
    arr.set_cursors(
        [{"target": "arr", "id": cid, "index": index, "color": color}]
    )
    return arr.emit_svg()


class TestEmit:
    def test_glyph_structure(self) -> None:
        svg = _array_with_cursor(2)
        m = re.search(
            r'<g class="scriba-annotation scriba-annotation-info"'
            r'[^>]*data-annotation="arr\.cursor\[i\]-solo"[^>]*>(.*?)</g>',
            svg,
            re.S,
        )
        assert m, "cursor group missing"
        body = m.group(1)
        assert "<polygon" in body        # the ▲ caret
        assert re.search(r"<text[^>]*>i</text>", body)  # small id label

    def test_state_color_class(self) -> None:
        svg = _array_with_cursor(2, color="state:current")
        assert 'scriba-annotation-state-current' in svg
        assert 'data-annotation="arr.cursor[i]-solo"' in svg

    def test_caret_x_tracks_cell_center(self) -> None:
        arr = ArrayPrimitive("arr", {"values": [10, 20, 30, 40, 50]})
        arr.set_cursors([{"target": "arr", "id": "i", "index": 3, "color": "info"}])
        svg = arr.emit_svg()
        cx = arr.resolve_annotation_point("arr.cell[3]")[0]
        m = re.search(
            r'data-annotation="arr\.cursor\[i\]-solo".*?<polygon points="([\d.]+),',
            svg,
            re.S,
        )
        assert m, "caret polygon missing"
        assert abs(float(m.group(1)) - cx) < 0.6

    def test_oob_index_soft_dropped(self) -> None:
        svg = _array_with_cursor(99)
        assert "cursor[" not in svg  # index out of range -> caret dropped

    def test_get_cursor_positions_records_xy(self) -> None:
        arr = ArrayPrimitive("arr", {"values": [10, 20, 30, 40, 50]})
        arr.set_cursors([{"target": "arr", "id": "i", "index": 2, "color": "info"}])
        arr.emit_svg()
        positions = arr.get_cursor_positions()
        assert "arr.cursor[i]-solo" in positions
        x, y = positions["arr.cursor[i]-solo"]
        assert abs(x - arr.resolve_annotation_point("arr.cell[2]")[0]) < 0.6


# ---------------------------------------------------------------------------
# Differ — cursor_move + annotation add/remove
# ---------------------------------------------------------------------------


def _fd(cursors):
    return FrameData(
        step_number=0,
        total_frames=2,
        narration_html="",
        shape_states={},
        annotations=[],
        cursors=cursors,
    )


def _cur(cid, index, x, y):
    return {
        "target": "arr",
        "id": cid,
        "index": index,
        "color": "info",
        "x": x,
        "y": y,
    }


class TestDiffer:
    def test_move_emits_cursor_move(self) -> None:
        prev = _fd([_cur("i", 2, 130.0, 46.0)])
        curr = _fd([_cur("i", 4, 310.0, 46.0)])
        trs = compute_transitions(prev, curr).transitions
        moves = [t for t in trs if t.kind == "cursor_move"]
        assert len(moves) == 1
        mv = moves[0]
        assert mv.target == "arr.cursor[i]-solo"
        assert mv.from_val == "130.0,46.0"
        assert mv.to_val == "310.0,46.0"

    def test_no_move_when_position_stable(self) -> None:
        prev = _fd([_cur("i", 2, 130.0, 46.0)])
        curr = _fd([_cur("i", 2, 130.0, 46.0)])
        trs = compute_transitions(prev, curr).transitions
        assert not [t for t in trs if t.kind == "cursor_move"]

    def test_appear_uses_annotation_add(self) -> None:
        prev = _fd([])
        curr = _fd([_cur("i", 2, 130.0, 46.0)])
        trs = compute_transitions(prev, curr).transitions
        adds = [
            t
            for t in trs
            if t.kind == "annotation_add" and "cursor[i]" in t.target
        ]
        assert len(adds) == 1

    def test_disappear_uses_annotation_remove(self) -> None:
        prev = _fd([_cur("i", 2, 130.0, 46.0)])
        curr = _fd([])
        trs = compute_transitions(prev, curr).transitions
        rems = [
            t
            for t in trs
            if t.kind == "annotation_remove" and "cursor[i]" in t.target
        ]
        assert len(rems) == 1


# ---------------------------------------------------------------------------
# End-to-end — full pipeline (binding + injection + differ in the HTML)
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_caret_group_in_html(self) -> None:
        html = _render(_TWO_POINTER)
        assert 'data-annotation="arr.cursor[i]-solo"' in html

    def test_slide_emits_cursor_move_in_manifest(self) -> None:
        # i: 1 -> 3 across the two steps => one cursor_move on frame 2.
        html = _render(_TWO_POINTER)
        assert "cursor_move" in html

    def test_foreach_spawns_named_carets(self) -> None:
        source = (
            "\\shape{arr}{Array}{values=[10,20,30,40,50]}\n"
            '\\shape{w}{VariableWatch}{names=["a","b"]}\n'
            "\\step\n"
            "\\apply{w.var[a]}{value=0}\n"
            "\\apply{w.var[b]}{value=4}\n"
            '\\foreach{k}{["a","b"]}\n'
            '\\cursor{arr}{id=${k}, at="w.var[${k}]"}\n'
            "\\endforeach\n"
        )
        html = _render(source)
        assert 'data-annotation="arr.cursor[a]-solo"' in html
        assert 'data-annotation="arr.cursor[b]-solo"' in html


# ---------------------------------------------------------------------------
# Legacy end-to-end guard — the recolor-hop still churns cell states only
# ---------------------------------------------------------------------------


class TestLegacyUnchanged:
    def test_legacy_cursor_emits_recolor_not_caret(self) -> None:
        source = (
            "\\shape{a}{Array}{size=4}\n"
            "\\step\n\\cursor{a.cell}{0}\n"
            "\\step\n\\cursor{a.cell}{1}\n"
        )
        html = _render(source)
        # Legacy path is a pure state-hop: no caret glyph and no cursor_move
        # transition record (the JS handler string is always embedded, so the
        # check must target the manifest record, not the whole page).
        assert "cursor[" not in html
        assert ',"cursor_move"]' not in html
