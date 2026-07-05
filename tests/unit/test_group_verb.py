"""``\\group`` / ``\\ungroup`` — the overlay-hull verb family
(investigations/gap-dsu-forest-design.md §6 Phase 1, Wave-3).

Covers the full slice: parse (id / nodes / color / label + the loud E-codes),
GroupEntry lifecycle in the snapshot (persistent, re-group grows the cluster,
\\ungroup removes by id), the per-shape emit contract on Graph (``<path>`` hull +
``data-annotation`` key + label pill), hull enclosure (every node centre inside
the path), absolute layout stability (the node-set / viewBox never move — a
group is a pure decoration), and the differ transitions (add / remove / recolor
+ node-set-change redraw) whose key matches the emit key exactly.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.differ import _diff_groups, compute_transitions
from scriba.animation.emitter import FrameData
from scriba.animation.parser.ast import GroupCommand, UngroupCommand
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.graph import Graph
from scriba.animation.scene import FrameSnapshot, GroupEntry, SceneState
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PRELUDE = (
    '\\shape{G}{Graph}{nodes=["a","b","c","d","e","f"], '
    'edges=[("a","b",1),("b","c",2),("d","e",2),("e","f",3),("c","d",8)], '
    'layout="stable", layout_seed=7}\n'
)


def _parse(body: str) -> "list[FrameSnapshot]":
    """Parse a one-Graph animation body and materialise its snapshots."""
    ir = SceneParser().parse(_PRELUDE + body)
    st = SceneState()
    st.apply_prelude(shapes=ir.shapes, prelude_commands=ir.prelude_commands)
    return [st.apply_frame(f) for f in ir.frames]


def _commands(body: str, kind: type) -> list:
    ir = SceneParser().parse(_PRELUDE + body)
    out = list(ir.prelude_commands)
    for f in ir.frames:
        out.extend(f.commands)
    return [c for c in out if isinstance(c, kind)]


def _graph() -> Graph:
    return Graph(
        "G",
        {
            "nodes": ["a", "b", "c", "d", "e", "f"],
            "edges": [
                ("a", "b", 1), ("b", "c", 2), ("d", "e", 2),
                ("e", "f", 3), ("c", "d", 8),
            ],
            "layout": "stable",
            "layout_seed": 7,
            "directed": False,
        },
    )


def _emit(groups: "list[dict]") -> str:
    g = _graph()
    g.set_groups(groups)
    return g.emit_svg()


def _path_of(svg: str, gid: str) -> str:
    m = re.search(
        rf'data-annotation="G\.group\[{re.escape(gid)}\]-solo".*?<path d="([^"]+)"',
        svg, re.S,
    )
    assert m, f"no hull path emitted for group {gid!r}"
    return m.group(1)


def _path_bbox(d: str) -> "tuple[float, float, float, float]":
    nums = [float(x) for x in re.findall(r"-?\d+\.?\d*", d)]
    xs, ys = nums[0::2], nums[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def _fd(groups: "list[dict]") -> FrameData:
    return FrameData(
        step_number=1, total_frames=2, narration_html="",
        shape_states={}, annotations=[], groups=groups,
    )


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


class TestParse:
    def test_group_parses_id_nodes_label_color(self) -> None:
        cmds = _commands(
            '\\group{G}{nodes=["a","b","c"], id=c1, label="SCC 1", color=good}\n',
            GroupCommand,
        )
        assert len(cmds) == 1
        assert cmds[0].shape == "G"
        assert cmds[0].group_id == "c1"
        assert cmds[0].node_ids == ("a", "b", "c")
        assert cmds[0].color == "good"
        assert cmds[0].label == "SCC 1"

    def test_group_color_defaults_to_info(self) -> None:
        cmds = _commands('\\group{G}{nodes=["a"], id=c1}\n', GroupCommand)
        assert cmds[0].color == "info"
        assert cmds[0].label is None

    def test_ungroup_parses_id(self) -> None:
        cmds = _commands(
            '\\group{G}{nodes=["a"], id=c1}\n\\ungroup{G}{id=c1}\n',
            UngroupCommand,
        )
        assert len(cmds) == 1
        assert cmds[0].shape == "G"
        assert cmds[0].group_id == "c1"

    def test_group_missing_id_is_E1506(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse('\\group{G}{nodes=["a","b"]}\n')
        assert exc.value.code == "E1506"

    def test_group_missing_nodes_is_E1506(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse("\\group{G}{id=c1}\n")
        assert exc.value.code == "E1506"

    def test_group_empty_nodes_is_E1506(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse("\\group{G}{nodes=[], id=c1}\n")
        assert exc.value.code == "E1506"

    def test_ungroup_missing_id_is_E1506(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse("\\ungroup{G}{}\n")
        assert exc.value.code == "E1506"

    def test_group_unknown_node_is_E1507(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse('\\group{G}{nodes=["a","zzz"], id=c1}\n')
        assert exc.value.code == "E1507"

    def test_group_undeclared_shape_is_E1507(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse('\\group{ghost}{nodes=["a"], id=c1}\n')
        assert exc.value.code == "E1507"

    def test_group_non_graph_shape_is_E1507(self) -> None:
        src = (
            "\\shape{A}{Array}{values=[1,2,3]}\n"
            '\\step\n\\group{A}{nodes=["0"], id=c1}\n'
        )
        with pytest.raises(ValidationError) as exc:
            ir = SceneParser().parse(src)
            st = SceneState()
            st.apply_prelude(shapes=ir.shapes, prelude_commands=ir.prelude_commands)
        assert exc.value.code == "E1507"
        assert "Graph" in str(exc.value)

    def test_group_bad_color_is_E1113(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _parse('\\group{G}{nodes=["a"], id=c1, color=chartreuse}\n')
        assert exc.value.code == "E1113"


# ---------------------------------------------------------------------------
# Snapshot lifecycle
# ---------------------------------------------------------------------------


class TestSnapshotLifecycle:
    def test_group_entry_lands_in_snapshot(self) -> None:
        snaps = _parse(
            '\\group{G}{nodes=["a","b"], id=c1, label="s", color=good}\n'
            "\\step\n\\narrate{f1}\n"
        )
        assert len(snaps[0].groups) == 1
        g = snaps[0].groups[0]
        assert isinstance(g, GroupEntry)
        assert g.target == "G"
        assert g.group_id == "c1"
        assert g.node_ids == ("a", "b")
        assert g.color == "good"
        assert g.label == "s"

    def test_group_is_persistent_without_reissue(self) -> None:
        snaps = _parse(
            '\\group{G}{nodes=["a","b"], id=c1}\n'
            "\\step\n\\narrate{f1}\n"
            "\\step\n\\narrate{f2}\n"
        )
        assert len(snaps[0].groups) == 1
        assert len(snaps[1].groups) == 1  # persistent — survives with no re-issue

    def test_regroup_same_id_grows_node_set(self) -> None:
        snaps = _parse(
            '\\group{G}{nodes=["a","b"], id=c1}\n'
            "\\step\n\\narrate{f1}\n"
            '\\step\n\\group{G}{nodes=["a","b","c"], id=c1}\n\\narrate{f2}\n'
        )
        assert snaps[0].groups[0].node_ids == ("a", "b")
        # same id, larger node-set — one entry, replaced (a Kruskal component)
        assert len(snaps[1].groups) == 1
        assert snaps[1].groups[0].group_id == "c1"
        assert snaps[1].groups[0].node_ids == ("a", "b", "c")

    def test_two_ids_are_independent(self) -> None:
        snaps = _parse(
            '\\group{G}{nodes=["a","b"], id=c1}\n'
            '\\group{G}{nodes=["d","e"], id=c2}\n'
            "\\step\n\\narrate{f1}\n"
        )
        by_id = {g.group_id: g.node_ids for g in snaps[0].groups}
        assert by_id == {"c1": ("a", "b"), "c2": ("d", "e")}

    def test_ungroup_removes_by_id(self) -> None:
        snaps = _parse(
            '\\group{G}{nodes=["a","b"], id=c1}\n'
            '\\group{G}{nodes=["d","e"], id=c2}\n'
            "\\step\n\\narrate{f1}\n"
            "\\step\n\\ungroup{G}{id=c1}\n\\narrate{f2}\n"
        )
        assert {g.group_id for g in snaps[0].groups} == {"c1", "c2"}
        assert {g.group_id for g in snaps[1].groups} == {"c2"}  # only c1 gone

    def test_ungroup_unknown_id_is_noop(self) -> None:
        snaps = _parse(
            '\\group{G}{nodes=["a","b"], id=c1}\n'
            "\\step\n\\ungroup{G}{id=nope}\n\\narrate{f1}\n"
        )
        assert {g.group_id for g in snaps[0].groups} == {"c1"}


# ---------------------------------------------------------------------------
# Emit contract  (per-shape, inside Graph.emit_svg)
# ---------------------------------------------------------------------------


class TestEmit:
    def test_hull_g_key_class_and_path(self) -> None:
        svg = _emit(
            [{"target": "G", "id": "c1", "nodes": ["a", "b", "c"],
              "color": "good", "label": "SCC 1"}]
        )
        assert 'data-annotation="G.group[c1]-solo"' in svg
        assert "scriba-group" in svg
        assert "scriba-annotation-good" in svg
        assert "<path d=" in svg
        assert ">SCC 1<" in svg  # label pill text
        assert 'aria-roledescription="group"' in svg

    def test_color_class_tracks_color(self) -> None:
        svg = _emit([{"target": "G", "id": "c2", "nodes": ["d", "e"], "color": "info"}])
        assert "scriba-annotation-info" in svg

    def test_hull_drawn_before_edges_and_nodes(self) -> None:
        svg = _emit([{"target": "G", "id": "c1", "nodes": ["a", "b", "c"], "color": "good"}])
        i_group = svg.index('data-annotation="G.group[c1]-solo"')
        i_edges = svg.index('class="scriba-graph-edges"')
        i_node = svg.index('data-target="G.node[a]"')
        assert i_group < i_edges < i_node  # hull is the bottom-most layer

    def test_label_drawn_after_nodes(self) -> None:
        # hunt-visual BUG 1: the hull fill stays under nodes, but the label
        # pill must be painted OVER nodes or a node overdraws it (illegible).
        svg = _emit(
            [{"target": "G", "id": "c1", "nodes": ["a", "b", "c"],
              "color": "good", "label": "SCC 1"}]
        )
        i_node = svg.index('data-target="G.node[a]"')
        i_label = svg.index(">SCC 1<")
        assert i_label > i_node, "group label must paint after (over) nodes"

    def test_empty_cluster_soft_drops(self) -> None:
        # all-unknown nodes -> no centres -> whole hull dropped, no crash
        svg = _emit([{"target": "G", "id": "c1", "nodes": ["zzz"], "color": "good"}])
        assert "G.group[c1]" not in svg

    def test_no_groups_emits_no_hull(self) -> None:
        svg = _emit([])
        assert "scriba-group" not in svg
        assert "G.group[" not in svg

    def test_single_node_fallback_emits(self) -> None:
        # <=2 nodes -> rounded-rect fallback, still a valid closed path
        svg = _emit([{"target": "G", "id": "solo", "nodes": ["a"], "color": "info"}])
        assert 'data-annotation="G.group[solo]-solo"' in svg
        assert "<path d=" in svg


# ---------------------------------------------------------------------------
# Hull enclosure — every node centre inside the painted path
# ---------------------------------------------------------------------------


class TestHullBounds:
    @pytest.mark.parametrize("nodes", [
        ["a", "b", "c"],           # >=3 -> convex hull
        ["a", "b", "c", "d", "e"],  # bigger hull
        ["a", "b"],                # 2 -> rounded-rect fallback
        ["a"],                     # 1 -> rounded-rect fallback
    ])
    def test_every_node_centre_inside_path_bbox(self, nodes) -> None:
        g = _graph()
        g.set_groups([{"target": "G", "id": "c1", "nodes": nodes, "color": "good"}])
        svg = g.emit_svg()
        minx, miny, maxx, maxy = _path_bbox(_path_of(svg, "c1"))
        for n in nodes:
            cx, cy = g.positions[n]
            assert minx <= cx <= maxx, f"{n} x={cx} outside [{minx},{maxx}]"
            assert miny <= cy <= maxy, f"{n} y={cy} outside [{miny},{maxy}]"

    def test_pad_clears_the_node_radius(self) -> None:
        # the hull bbox must extend past the tight node-centre bbox by at least
        # the node radius (the circle sits inside the tint, not on its edge)
        g = _graph()
        nodes = ["a", "b", "c"]
        g.set_groups([{"target": "G", "id": "c1", "nodes": nodes, "color": "good"}])
        svg = g.emit_svg()
        hminx, hminy, hmaxx, hmaxy = _path_bbox(_path_of(svg, "c1"))
        cxs = [g.positions[n][0] for n in nodes]
        cys = [g.positions[n][1] for n in nodes]
        assert hminx < min(cxs) - g._node_radius + 1
        assert hmaxx > max(cxs) + g._node_radius - 1
        assert hminy < min(cys) - g._node_radius + 1
        assert hmaxy > max(cys) + g._node_radius - 1


# ---------------------------------------------------------------------------
# Absolute layout stability — a group is a pure decoration
# ---------------------------------------------------------------------------


class TestLayoutStability:
    def test_node_blocks_byte_identical_with_and_without_group(self) -> None:
        base = _graph().emit_svg()
        g = _graph()
        g.set_groups([{"target": "G", "id": "c1", "nodes": ["a", "b", "c"], "color": "good"}])
        grouped = g.emit_svg()

        def node_blocks(s: str) -> list:
            return re.findall(r'<g data-target="G\.node\[[^"]+\]".*?</g>', s, re.S)

        assert node_blocks(base) == node_blocks(grouped)

    def test_stripping_hull_yields_the_group_free_svg(self) -> None:
        base = _graph().emit_svg()
        g = _graph()
        g.set_groups([{"target": "G", "id": "c1", "nodes": ["a", "b", "c"], "color": "good"}])
        grouped = g.emit_svg()
        stripped = re.sub(
            r'\s*<g class="scriba-annotation[^"]*scriba-group"[^>]*>.*?</g>',
            "", grouped, flags=re.S,
        )
        assert stripped == base  # only the hull <g> was added; nothing else moved

    def test_bounding_box_unchanged_by_group(self) -> None:
        base = _graph().bounding_box()
        g = _graph()
        g.set_groups([{"target": "G", "id": "c1", "nodes": ["a", "b", "c"], "color": "good"}])
        after = g.bounding_box()
        assert (base.x, base.y, base.width, base.height) == (
            after.x, after.y, after.width, after.height
        )


# ---------------------------------------------------------------------------
# Differ transitions
# ---------------------------------------------------------------------------


class TestDiffer:
    def test_group_appear_emits_annotation_add(self) -> None:
        prev = _fd([])
        curr = _fd([{"target": "G", "id": "c1", "nodes": ["a", "b"], "color": "good"}])
        trs = compute_transitions(prev, curr).transitions
        adds = [t for t in trs if t.kind == "annotation_add"]
        assert any(t.target == "G.group[c1]-solo" for t in adds)

    def test_group_disappear_emits_annotation_remove(self) -> None:
        prev = _fd([{"target": "G", "id": "c1", "nodes": ["a", "b"], "color": "good"}])
        curr = _fd([])
        trs = compute_transitions(prev, curr).transitions
        rems = [t for t in trs if t.kind == "annotation_remove"]
        assert any(t.target == "G.group[c1]-solo" for t in rems)

    def test_group_recolor_emits_annotation_recolor(self) -> None:
        prev = [{"target": "G", "id": "c1", "nodes": ["a", "b"], "color": "info"}]
        curr = [{"target": "G", "id": "c1", "nodes": ["a", "b"], "color": "good"}]
        trs = _diff_groups(prev, curr)
        assert len(trs) == 1
        assert trs[0].kind == "annotation_recolor"
        assert trs[0].target == "G.group[c1]-solo"
        assert trs[0].from_val == "info"
        assert trs[0].to_val == "good"

    def test_node_set_change_emits_remove_plus_add(self) -> None:
        prev = [{"target": "G", "id": "c1", "nodes": ["a", "b"], "color": "good"}]
        curr = [{"target": "G", "id": "c1", "nodes": ["a", "b", "c"], "color": "good"}]
        trs = _diff_groups(prev, curr)
        kinds = sorted(t.kind for t in trs)
        assert kinds == ["annotation_add", "annotation_remove"]
        assert all(t.target == "G.group[c1]-solo" for t in trs)
        # a node-set change is a redraw, not a recolor
        assert not any(t.kind == "annotation_recolor" for t in trs)

    def test_stable_group_emits_no_transition(self) -> None:
        gr = [{"target": "G", "id": "c1", "nodes": ["a", "b"], "color": "good"}]
        assert _diff_groups(gr, list(gr)) == []

    def test_differ_key_matches_emit_key(self) -> None:
        """The differ key and the emit data-annotation key must be identical or
        the runtime cannot match the hull it fades."""
        svg = _emit([{"target": "G", "id": "c1", "nodes": ["a", "b", "c"], "color": "good"}])
        emit_key = re.search(r'data-annotation="(G\.group\[[^"]*)"', svg).group(1)
        diff_key = _diff_groups(
            [], [{"target": "G", "id": "c1", "nodes": ["a", "b", "c"], "color": "good"}]
        )[0].target
        assert emit_key == diff_key
