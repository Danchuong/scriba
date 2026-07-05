"""Unit tests for the Graph ``positions`` manual-placement param (census gap #3).

``positions=[(node, x, y), ...]`` pins every node to an author-supplied
abstract coordinate (scaled + centred to the canvas), bypassing the force /
hierarchical / stable solvers.  This is what lets FFT-butterfly, planar, and
geometric graphs draw at their true relative positions.

Structure:
  * ``map_manual_positions`` — the pure author→pixel mapping helper.
  * ``positions`` param — pinning, column separation, edge binding, layout
    precedence.
  * validation — every malformed ``positions`` is a loud E1475, never a silent
    fallback to force layout.
  * byte-stability — a graph WITHOUT ``positions`` is unperturbed by the new
    code path.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.primitives.graph import (
    Graph,
    fruchterman_reingold,
    map_manual_positions,
)
from scriba.core.errors import ValidationError

# Drawable region = [_PADDING, width-_PADDING] x [_PADDING, height-_PADDING]
# for the default 400x300 canvas (mirrors fruchterman_reingold bounds).
_MIN, _MAX_X, _MAX_Y = 20, 380, 280

# Capture each rendered node's centre: data-target="G.node[<id>]" ... <circle cx cy>.
_NODE_RE = re.compile(
    r'data-target="G\.node\[([^\]]+)\]"[^>]*>\s*<circle cx="([\d.]+)" cy="([\d.]+)"'
)
_EDGE_LINE_RE = re.compile(
    r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)"'
)


def _node_centers(svg: str) -> dict[str, tuple[float, float]]:
    return {
        m.group(1): (float(m.group(2)), float(m.group(3)))
        for m in _NODE_RE.finditer(svg)
    }


# ---------------------------------------------------------------------------
# map_manual_positions — pure author→pixel mapping
# ---------------------------------------------------------------------------


class TestMapManualPositions:
    def test_single_node_centered(self) -> None:
        # A lone node lands at the canvas centre, matching the force solver.
        assert map_manual_positions({"A": (0.0, 0.0)}) == {"A": (200, 150)}
        assert fruchterman_reingold(["A"], []) == {"A": (200, 150)}

    def test_all_coincident_center(self) -> None:
        result = map_manual_positions({"A": (5.0, 5.0), "B": (5.0, 5.0)})
        assert result == {"A": (200, 150), "B": (200, 150)}

    def test_columns_share_cx(self) -> None:
        # Two author columns (x=0 / x=1) → two distinct cx, and every node in a
        # column shares that cx exactly.
        coords = {
            "l0": (0.0, 0.0), "l1": (0.0, 1.0),
            "r0": (1.0, 0.0), "r1": (1.0, 1.0),
        }
        pos = map_manual_positions(coords)
        assert pos["l0"][0] == pos["l1"][0]
        assert pos["r0"][0] == pos["r1"][0]
        assert pos["l0"][0] < pos["r0"][0]

    def test_uniform_scale_preserves_aspect(self) -> None:
        # A unit square in author space stays square in pixels: the column gap
        # equals the row gap (no per-axis stretch that would distort geometry).
        coords = {
            "a": (0.0, 0.0), "b": (1.0, 0.0),
            "c": (0.0, 1.0), "d": (1.0, 1.0),
        }
        pos = map_manual_positions(coords)
        col_gap = pos["b"][0] - pos["a"][0]
        row_gap = pos["c"][1] - pos["a"][1]
        assert col_gap == row_gap

    def test_within_canvas_bounds(self) -> None:
        coords = {str(i): (float(i % 3), float(i // 3)) for i in range(9)}
        for x, y in map_manual_positions(coords).values():
            assert _MIN <= x <= _MAX_X
            assert _MIN <= y <= _MAX_Y

    def test_y_grows_downward(self) -> None:
        # Screen convention (matches force / hierarchical / SVG): the smallest
        # author y renders at the top (smallest pixel y).
        pos = map_manual_positions({"top": (0.0, 0.0), "bot": (0.0, 10.0)})
        assert pos["top"][1] < pos["bot"][1]

    def test_returns_integers(self) -> None:
        pos = map_manual_positions({"a": (0.0, 0.0), "b": (3.0, 7.0)})
        for x, y in pos.values():
            assert isinstance(x, int)
            assert isinstance(y, int)


# ---------------------------------------------------------------------------
# positions param — pinning behaviour
# ---------------------------------------------------------------------------


class TestPositionsParam:
    def test_positions_pin_exact_coordinates(self) -> None:
        coords = {"A": (0.0, 0.0), "B": (2.0, 1.0), "C": (1.0, 2.0)}
        g = Graph("G", {
            "nodes": ["A", "B", "C"],
            "edges": [("A", "B"), ("B", "C")],
            "positions": [("A", 0, 0), ("B", 2, 1), ("C", 1, 2)],
        })
        assert g.positions == map_manual_positions(coords)

    def test_svg_node_centers_match_mapping(self) -> None:
        coords = {"A": (0.0, 0.0), "B": (2.0, 1.0), "C": (1.0, 2.0)}
        expected = map_manual_positions(coords)
        g = Graph("G", {
            "nodes": ["A", "B", "C"],
            "edges": [("A", "B")],
            "positions": [("A", 0, 0), ("B", 2, 1), ("C", 1, 2)],
        })
        centers = _node_centers(g.emit_svg())
        for node, (px, py) in expected.items():
            assert centers[node] == (float(px), float(py))

    def test_fft_butterfly_two_columns(self) -> None:
        # 8-node butterfly: 4 nodes in the left column (x=0), 4 in the right
        # (x=1).  The render must show exactly two distinct cx columns, 4 nodes
        # each — the whole point of manual placement.
        nodes = [f"x{i}" for i in range(4)] + [f"y{i}" for i in range(4)]
        positions = (
            [(f"x{i}", 0, i) for i in range(4)]
            + [(f"y{i}", 1, i) for i in range(4)]
        )
        edges = [("x0", "y0"), ("x1", "y1"), ("x0", "y2"), ("x2", "y0")]
        g = Graph("G", {"nodes": nodes, "edges": edges, "positions": positions})
        centers = _node_centers(g.emit_svg())
        cxs = sorted({cx for cx, _cy in centers.values()})
        assert len(cxs) == 2
        left = [n for n, (cx, _cy) in centers.items() if cx == cxs[0]]
        right = [n for n, (cx, _cy) in centers.items() if cx == cxs[1]]
        assert len(left) == 4 and len(right) == 4
        assert set(left) == {"x0", "x1", "x2", "x3"}

    def test_edge_connects_pinned_nodes(self) -> None:
        # An undirected edge's <line> endpoints coincide with the two pinned
        # node centres (edges follow positions with no re-solve).
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
            "positions": [("A", 0, 0), ("B", 3, 0)],
        })
        svg = g.emit_svg()
        centers = _node_centers(svg)
        m = _EDGE_LINE_RE.search(svg)
        assert m is not None
        endpoints = {(float(m.group(1)), float(m.group(2))),
                     (float(m.group(3)), float(m.group(4)))}
        assert endpoints == {centers["A"], centers["B"]}

    def test_positions_override_layout(self) -> None:
        # positions wins over an explicit layout= — the node is pinned, not
        # force-solved.
        coords = {"A": (0.0, 0.0), "B": (1.0, 0.0)}
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
            "layout": "force",
            "positions": [("A", 0, 0), ("B", 1, 0)],
        })
        assert g.positions == map_manual_positions(coords)

    def test_int_node_ids(self) -> None:
        g = Graph("G", {
            "nodes": [1, 2, 3],
            "edges": [(1, 2)],
            "positions": [(1, 0, 0), (2, 2, 0), (3, 1, 1)],
        })
        assert set(g.positions) == {1, 2, 3}

    def test_float_coordinates_accepted(self) -> None:
        g = Graph("G", {
            "nodes": ["A", "B"],
            "edges": [],
            "positions": [("A", 0.5, 1.5), ("B", 2.25, 0.0)],
        })
        assert set(g.positions) == {"A", "B"}


# ---------------------------------------------------------------------------
# validation — every malformed positions is a loud E1475
# ---------------------------------------------------------------------------


class TestPositionsValidation:
    def _mk(self, positions: object) -> None:
        Graph("G", {
            "nodes": ["A", "B"],
            "edges": [("A", "B")],
            "positions": positions,
        })

    def test_unknown_node_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1475"):
            self._mk([("A", 0, 0), ("B", 1, 0), ("Z", 2, 0)])

    def test_missing_node_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1475"):
            self._mk([("A", 0, 0)])  # B omitted

    def test_non_numeric_coord_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1475"):
            self._mk([("A", 0, 0), ("B", "x", 0)])

    def test_bool_coord_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1475"):
            self._mk([("A", 0, 0), ("B", True, 0)])

    def test_wrong_arity_entry_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1475"):
            self._mk([("A", 0, 0), ("B", 1)])  # missing y

    def test_duplicate_node_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1475"):
            self._mk([("A", 0, 0), ("A", 1, 1), ("B", 2, 2)])

    def test_positions_not_a_list_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1475"):
            self._mk("nope")

    def test_scalar_entry_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1475"):
            self._mk([("A", 0, 0), 5])


# ---------------------------------------------------------------------------
# byte-stability — no positions ⇒ existing force path is untouched
# ---------------------------------------------------------------------------


class TestByteStability:
    def test_force_graph_positions_unchanged(self) -> None:
        # A seeded force graph without `positions` must produce exactly the
        # coordinates fruchterman_reingold yields — the new manual-placement
        # branch must not perturb the default path.
        nodes = ["A", "B", "C", "D"]
        edges = [("A", "B"), ("B", "C"), ("C", "D")]
        g = Graph("G", {"nodes": nodes, "edges": edges, "layout_seed": 7})
        assert g.positions == fruchterman_reingold(
            nodes, [(u, v) for u, v in edges], seed=7
        )

    def test_no_positions_attr_is_none(self) -> None:
        g = Graph("G", {"nodes": ["A", "B"], "edges": [("A", "B")]})
        assert g._manual_positions is None

    def test_positions_and_no_positions_svg_differs(self) -> None:
        # Sanity: the two paths are genuinely distinct (guards against the
        # branch silently no-opping).
        base = Graph("G", {"nodes": ["A", "B"], "edges": [("A", "B")],
                           "layout_seed": 1})
        pinned = Graph("G", {"nodes": ["A", "B"], "edges": [("A", "B")],
                             "positions": [("A", 0, 0), ("B", 5, 5)]})
        assert base.emit_svg() != pinned.emit_svg()
