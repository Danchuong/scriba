"""JudgeZone #16: ``position=below`` leader stub when the pill is displaced
far from its anchor by the shared below-lane reservation.

Root cause: ``emit_position_label_svg`` (``_svg_helpers.py``) rooted every
"below" leader at ``below_baseline`` -- the shape-global lane the pill was
moved into -- regardless of how far that lane sits from the *specific*
annotated target's own box edge. For a single-row layout (Array, Bar,
DPTable's 1D mode) the lane sits just past the index/caption stack (gap
measured 0-34px in the family-surface calibration) so rooting there reads
as a short, legitimate connector. For a non-bottom-row/internal target in a
taller structure (Tree, Grid, Matrix, DPTable's 2D mode, Graph, Hypercube)
the lane is the far edge of the *whole* structure, unrelated to this
specific target (gap measured 75-260px) -- rooting the leader there
produces a ~10px stub glued to the pill, disconnected from the anchor.

Fix roots the leader at the true anchor (converging on the geometry the
explicit ``leader=true`` connector, R-37, already uses) whenever the lane
sits far past the target's own box edge; the snug (single-row / bottom-row
/ leaf) case is untouched -- byte-identical, zero golden churn.

Root cause and fix are written up in full in
``_bmad-output/implementation-artifacts/investigations/
judgezone-16-leader-stub-investigation.md`` and
``_bmad-output/implementation-artifacts/spec-fix-judgezone-16-leader-span.md``.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.bar import Bar
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.forest import Forest
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.hypercube import Hypercube
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.tree import Tree

# Long enough that the pill is always wider than a single cell/node -- the
# precondition (``_pill_spans_neighbours``) for the automatic R-07/R-08
# leader to fire at all.
_LONG_LABEL = "a below pill on an internal node wide enough to span neighbours"

# Family-surface calibration (see the investigation doc): every snug case
# measured <=34px, every displaced case measured >=75px past the target's
# own box edge. 50 sits in the middle of that 41px gap with margin on both
# sides -- used here only as the *test's* boundary for sanity-checking each
# case is still exercising the scenario it claims to, independent of
# whatever internal cutoff the fix itself uses.
_CALIBRATION_MIDPOINT = 50.0


def _leader_line(svg: str, ann_key: str) -> "tuple[float, float, float, float] | None":
    """First plain (non-dashed) ``<line>`` inside the annotation group --
    the automatic R-07/R-08 leader. ``None`` means no spanning leader was
    drawn (e.g. Forest: no ``resolve_annotation_box`` override, so
    ``cell_width`` is never fed and the leader branch never fires)."""
    m = re.search(
        r'data-annotation="' + re.escape(ann_key) + r'"[^>]*>(.*?)</g>', svg, re.S
    )
    assert m, f"annotation group {ann_key!r} not found"
    body = m.group(1)
    lm = re.search(
        r'<line x1="([\d.\-]+)" y1="([\d.\-]+)" x2="([\d.\-]+)" y2="([\d.\-]+)"'
        r' stroke="[^"]*" stroke-width="0\.75" stroke-opacity="0\.45"/>',
        body,
    )
    if not lm:
        return None
    x1, y1, x2, y2 = (float(g) for g in lm.groups())
    return x1, y1, x2, y2


def _pill_rect(svg: str, ann_key: str) -> "tuple[float, float, float, float]":
    m = re.search(
        r'data-annotation="' + re.escape(ann_key) + r'"[^>]*>(.*?)</g>', svg, re.S
    )
    assert m, f"annotation group {ann_key!r} not found"
    rm = re.search(
        r'<rect x="([\d.\-]+)" y="([\d.\-]+)" width="([\d.\-]+)" height="([\d.\-]+)"',
        m.group(1),
    )
    assert rm, "pill <rect> not found"
    x, y, w, h = (float(g) for g in rm.groups())
    return x, y, w, h


# ---------------------------------------------------------------------------
# Family-surface case builders. Each returns (primitive, target_selector).
# ---------------------------------------------------------------------------

_TREE_KW = {
    "root": "A", "nodes": ["A", "B", "C", "D", "E"],
    "edges": [("A", "B"), ("A", "C"), ("B", "D"), ("B", "E")],
}
_GRAPH_KW = {
    "nodes": ["A", "B", "C", "D"],
    "edges": [("A", "B"), ("B", "C"), ("C", "D")],
    "directed": True,
}


def _tree_internal() -> "tuple[Tree, str]":
    return Tree("t", dict(_TREE_KW)), "t.node[B]"


def _tree_leaf() -> "tuple[Tree, str]":
    return Tree("t", dict(_TREE_KW)), "t.node[D]"


def _grid_top_row() -> "tuple[GridPrimitive, str]":
    return GridPrimitive("g", {"rows": 3, "cols": 3, "data": list(range(9)), "label": "Board"}), "g.cell[0][0]"


def _grid_bottom_row() -> "tuple[GridPrimitive, str]":
    return GridPrimitive("g", {"rows": 3, "cols": 3, "data": list(range(9)), "label": "Board"}), "g.cell[2][0]"


def _matrix_top_row() -> "tuple[MatrixPrimitive, str]":
    return MatrixPrimitive("m", {"rows": 4, "cols": 4, "data": [0.1] * 16}), "m.cell[0][0]"


def _matrix_bottom_row() -> "tuple[MatrixPrimitive, str]":
    return MatrixPrimitive("m", {"rows": 4, "cols": 4, "data": [0.1] * 16}), "m.cell[3][0]"


def _dptable_2d_top_row() -> "tuple[DPTablePrimitive, str]":
    return DPTablePrimitive("dp", {"rows": 4, "cols": 4, "label": "dp[l][r]"}), "dp.cell[0][0]"


def _dptable_2d_bottom_row() -> "tuple[DPTablePrimitive, str]":
    return DPTablePrimitive("dp", {"rows": 4, "cols": 4, "label": "dp[l][r]"}), "dp.cell[3][0]"


def _dptable_1d() -> "tuple[DPTablePrimitive, str]":
    return DPTablePrimitive("dp", {"n": 6, "labels": "0..5"}), "dp.cell[3]"


def _graph_top_node() -> "tuple[Graph, str]":
    return Graph("G", dict(_GRAPH_KW)), "G.node[A]"


def _graph_bottom_node() -> "tuple[Graph, str]":
    return Graph("G", dict(_GRAPH_KW)), "G.node[D]"


def _hypercube_top_node() -> "tuple[Hypercube, str]":
    return Hypercube("L", {"bits": 3}), "L.subset[7]"


def _hypercube_bottom_node() -> "tuple[Hypercube, str]":
    return Hypercube("L", {"bits": 3}), "L.subset[0]"


def _array_cell() -> "tuple[ArrayPrimitive, str]":
    return ArrayPrimitive("a", {"size": 6, "data": list(range(6))}), "a.cell[2]"


def _bar_tallest() -> "tuple[Bar, str]":
    return Bar("b", {"data": [3, 7, 2, 9, 4]}), "b.bar[3]"


_DISPLACED_CASES = {
    "tree_internal_node": _tree_internal,
    "grid_top_row_cell": _grid_top_row,
    "matrix_top_row_cell": _matrix_top_row,
    "dptable_2d_top_row_cell": _dptable_2d_top_row,
    "graph_top_node": _graph_top_node,
    "hypercube_top_node": _hypercube_top_node,
}

_SNUG_CASES = {
    "array_cell": _array_cell,
    "bar_tallest_bar": _bar_tallest,
    "dptable_1d_cell": _dptable_1d,
    "tree_leaf_node": _tree_leaf,
    "grid_bottom_row_cell": _grid_bottom_row,
    "matrix_bottom_row_cell": _matrix_bottom_row,
    "dptable_2d_bottom_row_cell": _dptable_2d_bottom_row,
    "graph_bottom_node": _graph_bottom_node,
    "hypercube_bottom_node": _hypercube_bottom_node,
}


class TestDisplacedBelowPillLeaderRootsAtAnchor:
    """The broken family surface: a non-bottom-row/internal target whose
    ``below_baseline`` lane sits far past its own box edge (>=75px measured;
    >50px asserted here) is a different node/cell/row's territory -- the
    leader must root at the true anchor, not the disconncted below_baseline
    stub (JudgeZone #16)."""

    @pytest.mark.parametrize("name", sorted(_DISPLACED_CASES))
    def test_leader_roots_at_anchor_not_baseline(self, name: str) -> None:
        prim, target = _DISPLACED_CASES[name]()
        prim.set_annotations(
            [{"target": target, "label": _LONG_LABEL, "position": "below"}]
        )

        ay = prim.resolve_label_anchor(target)[1]
        below_baseline = prim.resolve_below_baseline()
        box = prim.resolve_annotation_box(target)
        assert below_baseline is not None, f"{name}: expected a below_baseline"
        assert box is not None, f"{name}: expected a resolve_annotation_box"
        target_bottom = box.y + box.height
        gap = float(below_baseline) - target_bottom
        assert gap > _CALIBRATION_MIDPOINT, (
            f"{name}: expected a displaced (>{_CALIBRATION_MIDPOINT}px) gap "
            f"per the family-surface calibration, got {gap}px -- case may "
            f"no longer exercise the bug"
        )

        svg = prim.emit_svg()
        ann_key = f"{target}-position-below"
        leader = _leader_line(svg, ann_key)
        assert leader is not None, f"{name}: expected a spanning leader (wide label)"
        _x1, y1, _x2, y2 = leader

        assert y1 == pytest.approx(ay, abs=1.5), (
            f"{name}: leader origin y={y1} should be the true anchor "
            f"({ay}), not the below_baseline lane ({below_baseline})"
        )

        pill_x, pill_y, pill_w, pill_h = _pill_rect(svg, ann_key)
        span_top, span_bottom = min(y1, y2), max(y1, y2)
        assert span_top <= target_bottom + 2, (
            f"{name}: leader should start at/above the anchor's own bottom "
            f"edge ({target_bottom}), got span_top={span_top}"
        )
        assert pill_y - 2 <= span_bottom <= pill_y + pill_h + 2, (
            f"{name}: leader should terminate on the pill (y in "
            f"[{pill_y}, {pill_y + pill_h}]), got span_bottom={span_bottom}"
        )


class TestSnugBelowPillLeaderUnchanged:
    """Byte-stability guard: single-row layouts (Array, Bar, DPTable's 1D
    mode) and any bottom-row/leaf target sit within the calibrated snug
    band (<=34px measured; <=50px asserted here) of the target's own box
    edge -- the lane is the index/caption stack immediately below THIS
    target, not another row's content. Leader must stay rooted at
    below_baseline exactly as before the fix -- zero golden churn."""

    @pytest.mark.parametrize("name", sorted(_SNUG_CASES))
    def test_leader_roots_at_baseline_unchanged(self, name: str) -> None:
        prim, target = _SNUG_CASES[name]()
        prim.set_annotations(
            [{"target": target, "label": _LONG_LABEL, "position": "below"}]
        )

        below_baseline = prim.resolve_below_baseline()
        box = prim.resolve_annotation_box(target)
        assert below_baseline is not None, f"{name}: expected a below_baseline"
        assert box is not None, f"{name}: expected a resolve_annotation_box"
        target_bottom = box.y + box.height
        gap = float(below_baseline) - target_bottom
        assert gap <= _CALIBRATION_MIDPOINT, (
            f"{name}: expected a snug (<={_CALIBRATION_MIDPOINT}px) gap per "
            f"the family-surface calibration, got {gap}px -- case may need "
            f"to move to the displaced suite"
        )

        svg = prim.emit_svg()
        ann_key = f"{target}-position-below"
        leader = _leader_line(svg, ann_key)
        assert leader is not None, f"{name}: expected a spanning leader (wide label)"
        _x1, y1, _x2, _y2 = leader

        assert y1 == pytest.approx(float(below_baseline), abs=1.5), (
            f"{name}: leader origin y={y1} should stay rooted at "
            f"below_baseline ({below_baseline}) -- must not move"
        )


class TestForestNoLeaderConvention:
    """Forest has no ``resolve_annotation_box`` override, so ``cell_width``
    is never fed to ``emit_position_label_svg`` and the automatic leader
    branch never fires -- a pre-existing, tested convention elsewhere in the
    corpus (see test_primitive_codepanel.py::test_below_pill_has_no_leader_line,
    spec: CodePanel gets lane mode but NO leader since it has no
    resolve_annotation_box). Left as out-of-scope for this fix, matching
    that convention; pinned here so a future change to either Forest or the
    convention is a deliberate, visible decision."""

    def test_forest_below_pill_has_no_leader_line(self) -> None:
        f = Forest("f", {"nodes": [0, 1, 2, 3, 4, 5, 6]})
        f.apply_command({"union": {"a": 0, "b": 1}})
        f.apply_command({"union": {"a": 0, "b": 2}})
        f.apply_command({"union": {"a": 1, "b": 3}})
        f.set_annotations(
            [{"target": "f.node[0]", "label": _LONG_LABEL, "position": "below"}]
        )
        assert f.resolve_annotation_box("f.node[0]") is None

        svg = f.emit_svg()
        ann_key = "f.node[0]-position-below"
        assert _leader_line(svg, ann_key) is None
