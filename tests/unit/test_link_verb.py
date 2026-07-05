"""``\\link`` / ``\\combine`` — the cross-shape bridge verb family
(investigations/gap-cross-shape-bridge.md, Wave-3).

Covers the full slice: parse (both arrow spellings + the combine sugar),
LinkEntry lifecycle in the snapshot (persistent vs ephemeral), the combine
desugar, the stage-level emit contract (``<path>`` + ``data-annotation`` key),
the cross-shape anchor math (two different primitives, endpoints landing inside
each shape's stage bbox), the differ transitions, and the loud E-codes.
"""

from __future__ import annotations

import re
import types

import pytest

from scriba.animation.differ import _diff_links, compute_transitions
from scriba.animation.emitter import FrameData
from scriba.animation.parser.ast import CombineCommand, LinkCommand
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.tree import Tree
from scriba.animation._frame_renderer import (
    _emit_scene_links,
    _resolve_link_point,
)
from scriba.animation.scene import FrameSnapshot, LinkEntry, SceneState
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(body: str) -> "list[FrameSnapshot]":
    """Parse a two-shape animation body and materialise its snapshots."""
    src = (
        '\\shape{T}{Tree}{root="A", nodes=["A","B","C","D","E"], '
        'edges=[("A","B"),("A","C"),("B","D"),("B","E")]}\n'
        "\\shape{a}{Array}{values=[10,20,30,40,50,60]}\n" + body
    )
    ir = SceneParser().parse(src)
    st = SceneState()
    st.apply_prelude(shapes=ir.shapes, prelude_commands=ir.prelude_commands)
    return [st.apply_frame(f) for f in ir.frames]


def _commands(body: str, kind: type) -> list:
    src = (
        '\\shape{T}{Tree}{root="A", nodes=["A","B","C","D","E"], '
        'edges=[("A","B"),("A","C"),("B","D"),("B","E")]}\n'
        "\\shape{a}{Array}{values=[10,20,30,40,50,60]}\n" + body
    )
    ir = SceneParser().parse(src)
    out = list(ir.prelude_commands)
    for f in ir.frames:
        out.extend(f.commands)
    return [c for c in out if isinstance(c, kind)]


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


class TestParse:
    def test_link_bidirectional_arrow(self) -> None:
        cmds = _commands(
            '\\link{T.node[D] <-> a.range[2:5]}{color=info, label="sub"}\n',
            LinkCommand,
        )
        assert len(cmds) == 1
        assert cmds[0].from_selector == "T.node[D]"
        assert cmds[0].to_selector == "a.range[2:5]"
        assert cmds[0].color == "info"
        assert cmds[0].label == "sub"
        assert cmds[0].ephemeral is False

    def test_link_directed_arrow_alias(self) -> None:
        cmds = _commands("\\link{T.node[D] -> a.cell[2]}{color=good}\n", LinkCommand)
        assert len(cmds) == 1
        assert cmds[0].from_selector == "T.node[D]"
        assert cmds[0].to_selector == "a.cell[2]"
        assert cmds[0].color == "good"

    def test_link_ephemeral_flag(self) -> None:
        cmds = _commands(
            "\\step\n\\link{a.cell[0] -> a.cell[1]}{ephemeral=true}\n", LinkCommand
        )
        assert cmds[0].ephemeral is True

    def test_combine_parses_sources_and_into(self) -> None:
        cmds = _commands(
            '\\step\n\\combine{a.cell[0], a.cell[1]}{into="a.cell[2]", color=good}\n',
            CombineCommand,
        )
        assert len(cmds) == 1
        assert cmds[0].sources == ("a.cell[0]", "a.cell[1]")
        assert cmds[0].into == "a.cell[2]"
        assert cmds[0].color == "good"
        assert cmds[0].ephemeral is True  # combine is ephemeral by default

    def test_link_missing_arrow_is_E1497(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse("\\step\n\\link{a.cell[0]}{color=info}\n")
        assert exc.value.code == "E1497"

    def test_link_three_endpoints_is_E1497(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse("\\step\n\\link{a.cell[0] -> a.cell[1] -> a.cell[2]}\n")
        assert exc.value.code == "E1497"

    def test_combine_without_into_is_E1497(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse("\\step\n\\combine{a.cell[0], a.cell[1]}{color=good}\n")
        assert exc.value.code == "E1497"

    def test_link_bad_color_is_E1113(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse("\\step\n\\link{a.cell[0] -> a.cell[1]}{color=chartreuse}\n")
        assert exc.value.code == "E1113"

    def test_link_undeclared_shape_is_E1498(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse("\\step\n\\link{ghost.cell[0] -> a.cell[1]}{color=info}\n")
        assert exc.value.code == "E1498"

    def test_combine_undeclared_into_is_E1498(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse('\\step\n\\combine{a.cell[0]}{into="ghost.cell[0]"}\n')
        assert exc.value.code == "E1498"


# ---------------------------------------------------------------------------
# Snapshot lifecycle
# ---------------------------------------------------------------------------


class TestSnapshotLifecycle:
    def test_link_entry_lands_in_snapshot(self) -> None:
        snaps = _parse(
            '\\link{T.node[D] <-> a.range[2:5]}{color=info, label="s"}\n'
            "\\step\n\\narrate{f1}\n"
        )
        assert len(snaps[0].links) == 1
        lk = snaps[0].links[0]
        assert isinstance(lk, LinkEntry)
        assert lk.from_selector == "T.node[D]"
        assert lk.to_selector == "a.range[2:5]"
        assert lk.color == "info"
        assert lk.label == "s"

    def test_persistent_link_survives_next_frame(self) -> None:
        snaps = _parse(
            "\\link{T.node[D] <-> a.range[2:5]}{color=info}\n"
            "\\step\n\\narrate{f1}\n"
            "\\step\n\\narrate{f2}\n"
        )
        assert len(snaps[0].links) == 1
        assert len(snaps[1].links) == 1  # persistent — still present next frame

    def test_ephemeral_link_cleared_next_frame(self) -> None:
        snaps = _parse(
            "\\step\n\\link{a.cell[0] -> a.cell[1]}{ephemeral=true}\n\\narrate{f1}\n"
            "\\step\n\\narrate{f2}\n"
        )
        assert len(snaps[0].links) == 1
        assert snaps[1].links == ()  # ephemeral — gone next frame

    def test_combine_desugars_to_two_links(self) -> None:
        snaps = _parse(
            "\\step\n"
            '\\combine{a.cell[0], a.cell[1]}{into="a.cell[2]", color=good}\n'
            "\\narrate{f1}\n"
        )
        links = snaps[0].links
        assert len(links) == 2
        assert {(lk.from_selector, lk.to_selector) for lk in links} == {
            ("a.cell[0]", "a.cell[2]"),
            ("a.cell[1]", "a.cell[2]"),
        }
        assert all(lk.ephemeral for lk in links)  # combine is ephemeral
        assert all(lk.color == "good" for lk in links)

    def test_combine_ephemeral_cleared_next_frame(self) -> None:
        snaps = _parse(
            "\\step\n"
            '\\combine{a.cell[0], a.cell[1]}{into="a.cell[2]"}\n\\narrate{f1}\n'
            "\\step\n\\narrate{f2}\n"
        )
        assert len(snaps[0].links) == 2
        assert snaps[1].links == ()


# ---------------------------------------------------------------------------
# Emit contract
# ---------------------------------------------------------------------------


def _emit(links: "list[dict]", primitives, offsets) -> str:
    parts: list[str] = []
    frame = types.SimpleNamespace(links=links)
    _emit_scene_links(frame, primitives, offsets, parts)
    return "".join(parts)


def _two_primitives():
    tree = Tree(
        "T",
        {
            "root": "A",
            "nodes": ["A", "B", "C", "D", "E"],
            "edges": [("A", "B"), ("A", "C"), ("B", "D"), ("B", "E")],
        },
    )
    arr = ArrayPrimitive("a", {"values": [10, 20, 30, 40, 50, 60]})
    return {"T": tree, "a": arr}


class TestEmit:
    def test_path_and_key_emitted(self) -> None:
        prims = _two_primitives()
        offsets = {"T": (0.0, 0.0), "a": (0.0, 300.0)}
        svg = _emit(
            [{"from": "T.node[D]", "to": "a.range[2:5]", "color": "info",
              "label": "sub", "ephemeral": False}],
            prims, offsets,
        )
        assert 'data-annotation="link[T.node[D]|a.range[2:5]]-solo"' in svg
        assert "scriba-link" in svg
        assert "scriba-annotation-info" in svg
        assert "<path" in svg and re.search(r'd="M[\d.]+,[\d.]+ Q', svg)
        assert ">sub<" in svg  # mid-path label

    def test_color_class_tracks_color(self) -> None:
        prims = _two_primitives()
        offsets = {"T": (0.0, 0.0), "a": (0.0, 300.0)}
        svg = _emit(
            [{"from": "a.cell[0]", "to": "a.cell[2]", "color": "good",
              "ephemeral": True}],
            prims, offsets,
        )
        assert "scriba-annotation-good" in svg

    def test_unresolvable_endpoint_soft_drops(self) -> None:
        prims = _two_primitives()
        offsets = {"T": (0.0, 0.0), "a": (0.0, 300.0)}
        # a.cell[99] is out of range -> resolve returns None -> whole link dropped
        svg = _emit(
            [{"from": "a.cell[0]", "to": "a.cell[99]", "color": "info"}],
            prims, offsets,
        )
        assert svg == ""

    def test_no_links_emits_nothing(self) -> None:
        prims = _two_primitives()
        assert _emit([], prims, {"T": (0.0, 0.0), "a": (0.0, 300.0)}) == ""


# ---------------------------------------------------------------------------
# Cross-shape anchor: endpoints land inside each shape's stage bbox
# ---------------------------------------------------------------------------


class TestCrossShapeAnchor:
    def test_endpoints_inside_respective_shape_bboxes(self) -> None:
        prims = _two_primitives()
        tree, arr = prims["T"], prims["a"]
        # Two genuinely different stage offsets — the two shapes do NOT share
        # an origin, so a correct resolver must dispatch each endpoint to its
        # own primitive and add that primitive's offset.
        off_t = (17.0, 5.0)
        off_a = (60.0, 320.0)
        offsets = {"T": off_t, "a": off_a}

        p_tree = _resolve_link_point("T.node[D]", prims, offsets)
        p_arr = _resolve_link_point("a.range[2:5]", prims, offsets)
        assert p_tree is not None and p_arr is not None

        # Each resolved point == local anchor + that shape's stage offset.
        loc_t = tree.resolve_annotation_point("T.node[D]")
        loc_a = arr.resolve_annotation_point("a.range[2:5]")
        assert p_tree == pytest.approx((loc_t[0] + off_t[0], loc_t[1] + off_t[1]))
        assert p_arr == pytest.approx((loc_a[0] + off_a[0], loc_a[1] + off_a[1]))

        # And each stage point lies within its shape's stage-translated bbox.
        def _within(point, prim, off) -> bool:
            bb = prim.bounding_box()
            x, y = point
            return (
                off[0] + bb.x - 1 <= x <= off[0] + bb.x + bb.width + 1
                and off[1] + bb.y - 1 <= y <= off[1] + bb.y + bb.height + 1
            )

        assert _within(p_tree, tree, off_t)
        assert _within(p_arr, arr, off_a)

        # The two endpoints are far apart in X (different shapes) — a genuine
        # cross-shape bridge, not two points in one primitive.
        assert abs(p_tree[0] - p_arr[0]) > 20

    def test_path_endpoints_match_resolved_points(self) -> None:
        prims = _two_primitives()
        offsets = {"T": (17.0, 5.0), "a": (60.0, 320.0)}
        svg = _emit(
            [{"from": "T.node[D]", "to": "a.range[2:5]", "color": "info"}],
            prims, offsets,
        )
        m = re.search(r'd="M([\d.]+),([\d.]+) Q[\d.]+,[\d.]+ ([\d.]+),([\d.]+)"', svg)
        assert m is not None
        mx, my, ex, ey = (float(g) for g in m.groups())
        p0 = _resolve_link_point("T.node[D]", prims, offsets)
        p1 = _resolve_link_point("a.range[2:5]", prims, offsets)
        assert (mx, my) == pytest.approx((round(p0[0], 1), round(p0[1], 1)), abs=0.1)
        assert (ex, ey) == pytest.approx((round(p1[0], 1), round(p1[1], 1)), abs=0.1)


# ---------------------------------------------------------------------------
# Differ transitions
# ---------------------------------------------------------------------------


def _fd(links: "list[dict]") -> FrameData:
    return FrameData(
        step_number=1, total_frames=2, narration_html="",
        shape_states={}, annotations=[], links=links,
    )


class TestDiffer:
    def test_link_appear_emits_annotation_add(self) -> None:
        prev = _fd([])
        curr = _fd([{"from": "a.cell[0]", "to": "a.cell[2]", "color": "good"}])
        trs = compute_transitions(prev, curr).transitions
        adds = [t for t in trs if t.kind == "annotation_add"]
        assert any(t.target == "link[a.cell[0]|a.cell[2]]-solo" for t in adds)

    def test_link_disappear_emits_annotation_remove(self) -> None:
        prev = _fd([{"from": "a.cell[0]", "to": "a.cell[2]", "color": "good"}])
        curr = _fd([])
        trs = compute_transitions(prev, curr).transitions
        rems = [t for t in trs if t.kind == "annotation_remove"]
        assert any(t.target == "link[a.cell[0]|a.cell[2]]-solo" for t in rems)

    def test_link_recolor_emits_annotation_recolor(self) -> None:
        prev = [{"from": "T.node[D]", "to": "a.range[2:5]", "color": "info"}]
        curr = [{"from": "T.node[D]", "to": "a.range[2:5]", "color": "good"}]
        trs = _diff_links(prev, curr)
        assert len(trs) == 1
        assert trs[0].kind == "annotation_recolor"
        assert trs[0].target == "link[T.node[D]|a.range[2:5]]-solo"
        assert trs[0].from_val == "info"
        assert trs[0].to_val == "good"

    def test_stable_link_emits_no_transition(self) -> None:
        lk = [{"from": "T.node[D]", "to": "a.range[2:5]", "color": "info"}]
        assert _diff_links(lk, list(lk)) == []

    def test_differ_key_matches_emit_key(self) -> None:
        """The differ key and the emit data-annotation key must be identical or
        the runtime cannot match the group it fades."""
        prims = _two_primitives()
        offsets = {"T": (0.0, 0.0), "a": (0.0, 300.0)}
        svg = _emit(
            [{"from": "T.node[D]", "to": "a.range[2:5]", "color": "info"}],
            prims, offsets,
        )
        emit_key = re.search(r'data-annotation="(link\[[^"]*)"', svg).group(1)
        diff_key = _diff_links(
            [], [{"from": "T.node[D]", "to": "a.range[2:5]", "color": "info"}]
        )[0].target
        assert emit_key == diff_key
