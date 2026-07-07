"""Node-label fit — cross-frame-max label map + viewBox fold (nodefit A).

research-nodelabel-fit.md: node labels paint as a bare
``<text text-anchor="middle">`` at the node center with
``clip_overflow=False``; the viewBox and translate were label-blind, so a
wide ``value=``/id label clipped the frame (Graph ``"dist[v]=infinity"``
tw=96 clipped 8 px left at 0.29.0 — the confirmed repro).

The fix under test: ``PrimitiveBase._node_label_wmax`` — a monotonic
per-node cross-frame-max painted label width, seeded from base ids/labels
at ``__init__`` and grown by ``set_value`` (which the existing
``_prescan_value_widths`` replays for every frame BEFORE viewbox
computation) — folded into each primitive's ``_h_label_pad()`` so
``bounding_box`` (frame width) and ``emit_svg`` (content translate) move
in lockstep. Radius, positions, and pitch are UNCHANGED by A.
"""

from __future__ import annotations

import warnings

import pytest

from scriba.animation.primitives._text_metrics import measure_value_text
from scriba.animation.primitives.forest import Forest
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.hypercube import Hypercube
from scriba.animation.primitives.tree import Tree

_FONT = 14  # the node-label font painted by all four primitives

# The confirmed 0.29.0 clip repro (tw = 96 px > 2r = 40).
WIDE = "dist[v]=infinity"
# Wide enough to overhang even Tree's count-scaled canvas margins.
WIDER = "subtree_answer[v]=9007199254740993"


def _display_label(prim, suffix: str, base: str) -> str:
    override = prim.get_value(suffix)
    return override if override is not None else base


# ---------------------------------------------------------------------------
# Shared substrate (PrimitiveBase map)
# ---------------------------------------------------------------------------


class TestNodeLabelMap:
    @pytest.mark.unit
    def test_graph_seeds_base_ids_at_init(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["Bellman-Ford", "x"], "edges": [("Bellman-Ford", "x")]},
        )
        assert g.cross_frame_max_label_width(
            "node[Bellman-Ford]"
        ) == measure_value_text("Bellman-Ford", _FONT)
        assert g.cross_frame_max_label_width("node[x]") == measure_value_text(
            "x", _FONT
        )

    @pytest.mark.unit
    def test_set_value_grows_map_monotonically(self) -> None:
        g = Graph("G", {"nodes": ["a", "b"], "edges": [("a", "b")]})
        g.set_value("node[a]", WIDE)
        grown = g.cross_frame_max_label_width("node[a]")
        assert grown == measure_value_text(WIDE, _FONT)
        # Monotonic: a later, shorter value never shrinks the reservation
        # (the prescan replays frames in order; the max must persist).
        g.set_value("node[a]", "7")
        assert g.cross_frame_max_label_width("node[a]") == grown

    @pytest.mark.unit
    def test_invalid_selector_does_not_grow_map(self) -> None:
        g = Graph("G", {"nodes": ["a", "b"], "edges": [("a", "b")]})
        before = dict(g._node_label_wmax)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            g.set_value("node[zz]", WIDE)  # E1115 soft-drop
        assert g._node_label_wmax == before

    @pytest.mark.unit
    def test_map_survives_values_clear(self) -> None:
        """The prescan restores ``_values`` after the replay; the width map
        is a separate field (like Queue ``_cell_width``) and must keep its
        grown maximum."""
        g = Graph("G", {"nodes": ["a", "b"], "edges": [("a", "b")]})
        g.set_value("node[a]", WIDE)
        grown = g.cross_frame_max_label_width("node[a]")
        g._values.clear()  # what the prescan restore does
        assert g.cross_frame_max_label_width("node[a]") == grown


# ---------------------------------------------------------------------------
# Graph — the confirmed frame-clip (A1)
# ---------------------------------------------------------------------------


def _graph_label_extents(g: Graph) -> list[tuple[object, float, float]]:
    left_pad, _right = g._h_label_pad()
    r = g._node_radius
    out = []
    for node_id, (cx, _cy) in g.positions.items():
        label = _display_label(g, g._node_key(node_id), str(node_id))
        tw = measure_value_text(str(label), _FONT)
        px = r + left_pad + cx  # emit_svg translate(r + left_pad, ...) + cx
        out.append((node_id, px - tw / 2.0, px + tw / 2.0))
    return out


class TestGraphNodefitA:
    def _ring(self) -> Graph:
        nodes = ["a", "b", "c", "d", "e"]
        edges = [("a", "b"), ("b", "c"), ("c", "d"), ("d", "e"), ("e", "a")]
        return Graph("G", {"nodes": nodes, "edges": edges, "layout_seed": 3})

    @pytest.mark.unit
    def test_wide_value_label_within_viewbox(self) -> None:
        g = self._ring()
        for n in ("a", "b", "c", "d", "e"):
            g.set_value(f"node[{n}]", WIDE)
        w = g.bounding_box().width
        for node_id, lo, hi in _graph_label_extents(g):
            assert lo >= 0.0, f"node {node_id} label clips left: {lo:.1f}"
            assert hi <= w, f"node {node_id} label clips right: {hi:.1f} > {w}"

    @pytest.mark.unit
    def test_wide_base_id_within_viewbox(self) -> None:
        """Static ids (no prescan involved) must be covered by the __init__
        seeding alone — the test_reference_tex_heavy 'Bellman-Ford' case."""
        g = Graph(
            "G",
            {
                "nodes": ["Bellman-Ford", "Dijkstra", "SPFA"],
                "edges": [
                    ("Bellman-Ford", "Dijkstra"),
                    ("Dijkstra", "SPFA"),
                ],
                "layout_seed": 3,
            },
        )
        w = g.bounding_box().width
        for node_id, lo, hi in _graph_label_extents(g):
            assert lo >= 0.0, f"node {node_id} label clips left: {lo:.1f}"
            assert hi <= w, f"node {node_id} label clips right: {hi:.1f} > {w}"

    @pytest.mark.unit
    def test_short_labels_byte_inert(self) -> None:
        """The ``tw <= 2r`` case must leave pads, box, and translate exactly
        as before (int 0 folds) — the byte-identity guard for the corpus."""
        g = Graph("G", {"nodes": ["a", "b"], "edges": [("a", "b")]})
        r = g._node_radius
        assert g._h_label_pad() == (0, 0)
        assert g.bounding_box().width == g.width + 2 * r
        assert f'transform="translate({r},' in g.emit_svg()


# ---------------------------------------------------------------------------
# Tree (A2 — defensive: canvas already scales with node count)
# ---------------------------------------------------------------------------


class TestTreeNodefitA:
    @pytest.mark.unit
    def test_wide_leaf_values_within_viewbox(self) -> None:
        leaves = [f"l{i}" for i in range(8)]
        t = Tree(
            "T",
            {
                "root": "r",
                "nodes": ["r", *leaves],
                "edges": [("r", leaf) for leaf in leaves],
            },
        )
        for node_id in ("r", *leaves):
            t.set_value(f"node[{node_id}]", WIDER)
        left_pad, _right = t._h_label_pad()
        r = t._node_radius
        w = t.bounding_box().width
        tw = measure_value_text(WIDER, _FONT)
        for node_id, (cx, _cy) in t.positions.items():
            px = r + left_pad + cx
            assert px - tw / 2.0 >= 0.0, f"{node_id} clips left"
            assert px + tw / 2.0 <= w, f"{node_id} clips right"

    @pytest.mark.unit
    def test_short_labels_byte_inert(self) -> None:
        t = Tree(
            "T",
            {"root": "a", "nodes": ["a", "b"], "edges": [("a", "b")]},
        )
        r = t._node_radius
        assert t._h_label_pad() == (0, 0)
        assert t.bounding_box().width == t.width + 2 * r


# ---------------------------------------------------------------------------
# Forest (A3 — fold rides the monotonic envelope)
# ---------------------------------------------------------------------------


class TestForestNodefitA:
    @pytest.mark.unit
    def test_wide_values_within_envelope(self) -> None:
        f = Forest("F", {"nodes": [0, 1, 2, 3]})
        for i in range(4):
            f.set_value(f"node[{i}]", WIDER)
        left_pad, _right = f._h_label_pad()
        w = f.bounding_box().width
        tw = measure_value_text(WIDER, _FONT)
        for nid, (x, _y) in f._current_positions().items():
            px = left_pad + x  # emit_svg translate(left_pad, ...)
            assert px - tw / 2.0 >= 0.0, f"node {nid} clips left"
            assert px + tw / 2.0 <= w, f"node {nid} clips right"

    @pytest.mark.unit
    def test_short_labels_byte_inert(self) -> None:
        f = Forest("F", {"nodes": [0, 1, 2]})
        assert f._h_label_pad() == (0, 0)
        w0 = f.bounding_box().width
        assert w0 == f._envelope_width  # no label widening


# ---------------------------------------------------------------------------
# Hypercube (A3 — subset[i] value spill)
# ---------------------------------------------------------------------------


class TestHypercubeNodefitA:
    @pytest.mark.unit
    def test_wide_subset_values_within_viewbox(self) -> None:
        h = Hypercube("L", {"bits": 3})
        for v in range(8):
            h.set_value(f"subset[{v}]", WIDE)
        left_pad, _right = h._h_label_pad()
        w = h.bounding_box().width
        tw = measure_value_text(WIDE, _FONT)
        for v, (cx, _cy) in h._positions.items():
            px = left_pad + cx  # emit_svg translate(left_pad, ...)
            assert px - tw / 2.0 >= 0.0, f"subset[{v}] clips left"
            assert px + tw / 2.0 <= w, f"subset[{v}] clips right: {px + tw / 2.0:.1f} > {w}"

    @pytest.mark.unit
    def test_short_masks_byte_inert(self) -> None:
        h = Hypercube("L", {"bits": 3})
        assert h._h_label_pad() == (0, 0)
        assert h.bounding_box().width == int(h._content_w)


# ---------------------------------------------------------------------------
# H1 (sweep3-nodefit): value= on a node that only exists after add_node
# ---------------------------------------------------------------------------


class TestTreeAddNodeWideValue:
    """A wide ``value=`` applied to a node ADDED mid-scene soft-dropped in
    the live prescan replay (the node isn't addressable yet), so its width
    never reached the label map: the born-wide node clipped the fixed
    viewBox and the late live regrow moved the tree mid-scene. The prescan
    now re-checks those values against the timeline-max clone and reserves
    the final pitch up front."""

    @staticmethod
    def _render(source: str, tmp_path) -> str:
        import sys
        from pathlib import Path as _P

        repo = _P(__file__).resolve().parents[2]
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
        from render import render_file

        tex = tmp_path / "in.tex"
        tex.write_text(source, encoding="utf-8")
        out = tmp_path / "out.html"
        render_file(tex, out)
        return out.read_text(encoding="utf-8")

    @pytest.mark.unit
    def test_added_node_wide_value_stable_and_contained(self, tmp_path) -> None:
        import re

        wide = "huge=99999999999999999999"
        source = (
            '\\begin{animation}[id="d", label="addnode wide"]\n'
            "\\shape{T}{Tree}{root=1, nodes=[1,2,3], edges=[(1,2),(1,3)]}\n"
            "\\step\n"
            "\\narrate{Small tree.}\n"
            "\\step\n"
            "\\apply{T}{add_node={id=99, parent=3}}\n"
            f'\\apply{{T.node[99]}}{{value="{wide}"}}\n'
            "\\narrate{Born wide.}\n"
            "\\end{animation}\n"
        )
        html = self._render(source, tmp_path)
        vbs = set(re.findall(r'viewBox="0 0 (\d+) (\d+)"', html))
        assert len(vbs) == 1, f"viewBox jumps mid-scene: {sorted(vbs)}"
        w = int(next(iter(vbs))[0])
        trs = set(
            re.findall(
                r'data-primitive="tree"[^>]*transform="translate\((\d+),(\d+)\)"',
                html,
            )
        )
        assert len(trs) == 1, f"tree translate jumps mid-scene: {sorted(trs)}"
        tx = int(next(iter(trs))[0])
        tw = measure_value_text(wide, _FONT)
        # final-frame painted extent of the added node's label ⊆ viewBox
        xs = [
            float(m)
            for m in re.findall(
                r'data-target="T\.node\[99\]" data-node-x="([\d.]+)"', html
            )
        ]
        assert xs, "added node not painted"
        for cx in xs:
            assert tx + cx - tw / 2.0 >= -0.5, "label clips left"
            assert tx + cx + tw / 2.0 <= w + 0.5, (
                f"label clips right: {tx + cx + tw / 2.0:.1f} > {w}"
            )


# ---------------------------------------------------------------------------
# nodefit B — label-aware pitch (node-node label collision)
# ---------------------------------------------------------------------------

_LABEL_H = 18.0  # one 14 px label line box


def _no_label_collision(positions, widths) -> list[tuple]:
    """Pairs whose label boxes overlap: |dx| < (w_i+w_j)/2 AND |dy| < box."""
    bad = []
    ids = list(positions)
    for i, u in enumerate(ids):
        for v in ids[i + 1:]:
            dx = abs(positions[u][0] - positions[v][0])
            dy = abs(positions[u][1] - positions[v][1])
            if dx < (widths[u] + widths[v]) / 2.0 and dy < _LABEL_H:
                bad.append((u, v, dx, dy))
    return bad


class TestIsolatedLaneNodefit:
    """sweep3-nodefit M1: the isolated-node lane spaced by COUNT only, so
    wide value= labels on lane nodes overlapped (-61 px in the probe) while
    the connected solve was already halves-aware. The one-shot settle now
    re-lanes with the same label halves."""

    @pytest.mark.unit
    def test_isolated_lane_wide_labels_no_overlap(self) -> None:
        """The s4c probe shape: a packed all-isolated lane where only two
        ADJACENT nodes carry wide values — the total overhang grows the
        canvas a little, but an even count-spread still leaves the two wide
        neighbours overlapping (-61 px). The lane must pack by halves."""
        nodes = [f"a{i}" for i in range(12)]
        g = Graph("G", {"nodes": nodes, "edges": [], "layout_seed": 1})
        g.set_value("node[a5]", "555555555555")
        g.set_value("node[a6]", "666666666666")
        w = g.bounding_box().width  # settles the label relayout
        tw5 = measure_value_text("555555555555", _FONT)
        tw6 = measure_value_text("666666666666", _FONT)
        x5 = g.positions["a5"][0]
        x6 = g.positions["a6"][0]
        assert abs(x6 - x5) >= (tw5 + tw6) / 2.0, (
            f"adjacent lane labels overlap: |dx|={abs(x6 - x5):.1f} < "
            f"{(tw5 + tw6) / 2.0:.1f}"
        )
        left_pad, _right = g._h_label_pad()
        r = g._node_radius
        for n, tw in (("a5", tw5), ("a6", tw6)):
            cx = g.positions[n][0]
            assert r + left_pad + cx - tw / 2.0 >= 0.0, f"{n} clips left"
            assert r + left_pad + cx + tw / 2.0 <= w, f"{n} clips right"

    @pytest.mark.unit
    def test_short_label_lane_unchanged(self) -> None:
        """No wide labels → the lane keeps its historic count-based spread."""
        import warnings as _w

        with _w.catch_warnings():
            _w.simplefilter("ignore")
            g1 = Graph(
                "G",
                {"nodes": ["a", "b", "i1", "i2"], "edges": [("a", "b")],
                 "layout_seed": 1},
            )
        assert g1._h_label_pad() == (0, 0)  # nothing settles


class TestGraphNodefitB:
    @pytest.mark.unit
    def test_adjacent_labels_no_collision(self) -> None:
        n = 10
        g = Graph(
            "G",
            {
                "nodes": list(range(n)),
                "edges": [(i, (i + 1) % n) for i in range(n)],
                "layout_seed": 0,
            },
        )
        for i in range(n):
            g.set_value(f"node[{i}]", WIDE)
        g.bounding_box()  # settles the post-prescan label relayout
        tw = measure_value_text(WIDE, _FONT)
        widths = {i: tw for i in range(n)}
        bad = _no_label_collision(g.positions, widths)
        assert not bad, f"label collisions: {bad[:4]}"

    @pytest.mark.unit
    def test_labels_still_within_viewbox_after_relayout(self) -> None:
        """B must not un-fix A: after the label-aware spread, every painted
        label extent still sits inside the (re-grown) viewBox."""
        n = 10
        g = Graph(
            "G",
            {
                "nodes": list(range(n)),
                "edges": [(i, (i + 1) % n) for i in range(n)],
                "layout_seed": 0,
            },
        )
        for i in range(n):
            g.set_value(f"node[{i}]", WIDE)
        w = g.bounding_box().width
        for node_id, lo, hi in _graph_label_extents(g):
            assert lo >= 0.0, f"node {node_id} label clips left: {lo:.1f}"
            assert hi <= w, f"node {node_id} label clips right: {hi:.1f} > {w}"


class TestTreeNodefitB:
    @pytest.mark.unit
    def test_dense_siblings_no_label_collision(self) -> None:
        leaves = [f"l{i}" for i in range(8)]
        t = Tree(
            "T",
            {
                "root": "r",
                "nodes": ["r", *leaves],
                "edges": [("r", leaf) for leaf in leaves],
            },
        )
        for leaf in leaves:
            t.set_value(f"node[{leaf}]", WIDE)
        t.bounding_box()
        tw = measure_value_text(WIDE, _FONT)
        widths = {n: (tw if n in leaves else 0) for n in t.positions}
        bad = _no_label_collision(t.positions, widths)
        assert not bad, f"sibling label collisions: {bad[:4]}"


class TestForestNodefitB:
    @pytest.mark.unit
    def test_singleton_row_no_label_collision(self) -> None:
        f = Forest("F", {"nodes": [0, 1, 2, 3]})
        for i in range(4):
            f.set_value(f"node[{i}]", WIDE)
        f.bounding_box()
        tw = measure_value_text(WIDE, _FONT)
        positions = f._current_positions()
        widths = {n: tw for n in positions}
        bad = _no_label_collision(positions, widths)
        assert not bad, f"forest label collisions: {bad[:4]}"


class TestHypercubeNodefitB:
    @pytest.mark.unit
    def test_row_no_label_collision(self) -> None:
        h = Hypercube("L", {"bits": 3})
        for v in range(8):
            h.set_value(f"subset[{v}]", WIDE)
        h.bounding_box()
        tw = measure_value_text(WIDE, _FONT)
        widths = {v: tw for v in h._positions}
        bad = _no_label_collision(h._positions, widths)
        assert not bad, f"row label collisions: {bad[:4]}"
