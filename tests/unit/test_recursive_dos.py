"""Recursive / deep-nesting denial-of-service regression tests.

Originally written Wave 4A Cluster 9 to cover audit findings 17-M3
and 10 (performance / DoS) — dimensional caps (Matrix/DPTable 250k,
Plane2D 500-per-frame, foreach 10k×3-deep) plus a pair of xfailed
tests for Tree recursion + Graph O(N^2) that were fixed in Wave 4B
Cluster 1 (iterative reingold_tilford + Graph._MAX_NODES=100). The
two strict xfails are now converted into passing regression tests
in ``TestTreeRecursionDoS`` and ``TestGraphQuadraticLayoutDoS``.

Update when:

* Primitive element caps are tightened or relaxed (update the
  assertions with the new limit).
* A new deep-recursion surface is added (e.g., nested segment trees).
* The foreach iterable cap (``_MAX_ITERABLE_LEN``) changes.
* ``Graph._MAX_NODES`` or ``_MAX_FOREACH_DEPTH`` is retuned.

Each test must either complete in <5s or raise a specific E-code.
No test in this file should time out the suite.
"""

from __future__ import annotations

import sys
import time

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives.tree import Tree, reingold_tilford
from scriba.animation.primitives.graph import Graph, _MAX_NODES
from scriba.core.errors import ValidationError


_TIME_BUDGET_S = 5.0


# Wave 4B Cluster 1 replaced the 2 strict-xfailed tests in
# TestDeeplyNestedTree and TestCyclicGraph with passing regression
# tests in TestTreeRecursionDoS and TestGraphQuadraticLayoutDoS at the
# bottom of this file. The remaining smaller-boundary tests
# (100-level tree, 100 self-loops) are preserved below as
# TestDeeplyNestedTreeBaseline / TestCyclicGraphBaseline to keep the
# small-input happy-path pinned.


class TestDeeplyNestedTreeBaseline:
    """Small-input happy paths (kept after Wave 4B C1 rewrote the
    oversized cases into TestTreeRecursionDoS below)."""

    def test_100_level_linear_tree_constructs(self) -> None:
        """At depth 100 the layout succeeds quickly — this is the
        baseline happy-path that kept the non-xfailed slot alive
        through Wave 4A."""
        depth = 100
        nodes = [f"n{i}" for i in range(depth)]
        edges = [[f"n{i}", f"n{i + 1}"] for i in range(depth - 1)]
        start = time.monotonic()
        prim = Tree("t", {"root": "n0", "nodes": nodes, "edges": edges})
        elapsed = time.monotonic() - start
        assert elapsed < _TIME_BUDGET_S
        assert len(prim.nodes) == depth


class TestCyclicGraphBaseline:
    """Graph small-input happy path (the 1000-node cycle is now in
    TestGraphQuadraticLayoutDoS below)."""

    def test_graph_with_100_self_loops_completes(self) -> None:
        """100 self-loops must not cause infinite recursion and must
        finish in well under the time budget."""
        n = 100
        nodes = [f"n{i}" for i in range(n)]
        edges = [[f"n{i}", f"n{i}"] for i in range(n)]  # self loops
        start = time.monotonic()
        Graph("g", {"nodes": nodes, "edges": edges})
        elapsed = time.monotonic() - start
        assert elapsed < _TIME_BUDGET_S


class TestOversizedDimensionalCaps:
    """Cluster 5 + Wave 2 Cluster 2 dimensional caps fire at 250k cells
    with code E1425 (Matrix/DPTable cell count exceeded)."""

    def test_dptable_250k_plus_one_cells_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E1425"):
            DPTablePrimitive("dp", {"rows": 501, "cols": 500})

    def test_dptable_1d_250k_plus_one_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E1425"):
            DPTablePrimitive("dp", {"n": 250_001})

    def test_dptable_exactly_250k_accepted(self) -> None:
        """250k cells is the last accepted size."""
        inst = DPTablePrimitive("dp", {"rows": 500, "cols": 500})
        assert inst.rows * inst.cols == 250_000

    def test_matrix_250k_plus_one_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E1425"):
            MatrixPrimitive("m", {"rows": 501, "cols": 500})

    def test_matrix_exactly_250k_accepted(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 500, "cols": 500})
        assert inst.rows * inst.cols == 250_000


class TestForeachIterationCaps:
    """Foreach depth and iterable length caps fire at the right codes."""

    def test_foreach_depth_3_is_allowed(self) -> None:
        """The parser allows up to _MAX_FOREACH_DEPTH=3 levels.

        SceneParser expects the INNER content of an animation block (no
        \\begin{animation} wrapper). That wrapper is handled upstream by
        detect_animation_blocks.
        """
        src = (
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\foreach{i}{0..1}\n"
            "\\foreach{j}{0..1}\n"
            "\\foreach{k}{0..1}\n"
            "\\highlight{a.cell[0]}\n"
            "\\endforeach\n"
            "\\endforeach\n"
            "\\endforeach\n"
        )
        ir = SceneParser().parse(src)
        assert ir is not None

    def test_foreach_10k_plus_one_range_rejected_at_expand(self) -> None:
        """Foreach range with 10_001+ elements must be rejected during
        expansion. (The parser accepts the source — the cap fires at
        ``SceneState._resolve_iterable``.)"""
        from scriba.animation.scene import SceneState
        src = (
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\foreach{i}{0..10001}\n"  # 10002 elements → over cap
            "\\highlight{a.cell[0]}\n"
            "\\endforeach\n"
        )
        ir = SceneParser().parse(src)
        state = SceneState()
        state.apply_prelude(shapes=ir.shapes)
        with pytest.raises(ValidationError, match="E1173"):
            state.apply_frame(ir.frames[0])

    def test_foreach_9999_elements_is_allowed(self) -> None:
        """9999 elements (just under the 10_000 cap) must parse + expand
        in bounded time."""
        from scriba.animation.scene import SceneState
        src = (
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            "\\foreach{i}{1..9999}\n"
            "\\highlight{a.cell[0]}\n"
            "\\endforeach\n"
        )
        ir = SceneParser().parse(src)
        state = SceneState()
        state.apply_prelude(shapes=ir.shapes)
        start = time.monotonic()
        state.apply_frame(ir.frames[0])
        elapsed = time.monotonic() - start
        assert elapsed < _TIME_BUDGET_S


class TestPlane2dElementCap:
    """Plane2D caps at 500 elements, E1466 raised as a hard limit.

    Wave 4A Cluster 4 converted the cap from soft-drop+log to
    hard-raise per audit finding 06-H3. Pre-Cluster-4 these tests
    asserted silent truncation; they now assert E1466.
    """

    def test_501_points_raises_e1466(self) -> None:
        """Constructing with 501 points raises E1466 (hard limit)."""
        points = [[float(i), float(i)] for i in range(501)]
        with pytest.raises(ValidationError, match="E1466"):
            Plane2D("p", {"xrange": [0, 1000], "yrange": [0, 1000], "points": points})

    def test_2000_points_raises_e1466_quickly(self) -> None:
        """A 4x over-cap input must raise (not silently truncate) and
        bail out in well under the time budget — no O(N) walk through
        the oversized list before failing."""
        points = [[float(i), float(i)] for i in range(2000)]
        start = time.monotonic()
        with pytest.raises(ValidationError, match="E1466"):
            Plane2D("p", {"xrange": [0, 10000], "yrange": [0, 10000], "points": points})
        elapsed = time.monotonic() - start
        assert elapsed < _TIME_BUDGET_S


# ---------------------------------------------------------------------------
# Wave 4B Cluster 1: Tree iterative DFS + Graph _MAX_NODES cap
# (converted from strict xfails in Wave 4A Cluster 9)
# ---------------------------------------------------------------------------


class TestTreeRecursionDoS:
    """``reingold_tilford`` must stay iterative for deeply nested trees."""

    def test_1000_level_linear_tree_constructs(self) -> None:
        """A 1000-level linear tree must construct without RecursionError.

        Wave 4B fix: ``reingold_tilford`` uses iterative DFS so depth
        and layout passes no longer push the Python call stack.
        """
        n = 1000
        nodes = list(range(n))
        edges = [(i, i + 1) for i in range(n - 1)]

        start = time.perf_counter()
        tree = Tree(
            "T",
            {
                "root": 0,
                "nodes": nodes,
                "edges": edges,
            },
        )
        elapsed = time.perf_counter() - start

        assert len(tree.nodes) == n
        assert tree._compute_max_depth() == n - 1
        # Every node gets a position.
        assert len(tree.positions) == n
        # Bounded time: the iterative algorithm is O(N) and should
        # complete comfortably under 1 second on commodity hardware.
        assert elapsed < 1.0, (
            f"Tree construction took {elapsed:.2f}s; "
            f"expected < 1.0s (iterative layout)"
        )

    def test_1500_level_linear_tree_exceeds_stack_limit(self) -> None:
        """Safety margin: a 1500-level tree must still construct.

        The default recursion limit is 1000; a naive recursive
        implementation would fail here.
        """
        n = 1500
        assert n > sys.getrecursionlimit() * 1.4
        nodes = list(range(n))
        edges = [(i, i + 1) for i in range(n - 1)]
        tree = Tree(
            "T",
            {
                "root": 0,
                "nodes": nodes,
                "edges": edges,
            },
        )
        assert len(tree.positions) == n

    def test_reingold_tilford_direct_deep_chain(self) -> None:
        """Direct ``reingold_tilford`` call must handle deep chains.

        Separated from the ``Tree`` wrapper so future regressions in
        the layout function itself are isolated.
        """
        n = 1200
        children_map: dict[str | int, list[str | int]] = {
            i: [i + 1] for i in range(n - 1)
        }
        children_map[n - 1] = []
        positions = reingold_tilford(0, children_map)
        assert len(positions) == n
        # Y-coordinates should strictly increase with depth.
        y_values = [positions[i][1] for i in range(n)]
        assert y_values == sorted(y_values)

    def test_deep_tree_depth_reported_correctly(self) -> None:
        """Iterative depth computation must match tree height."""
        n = 800
        nodes = list(range(n))
        edges = [(i, i + 1) for i in range(n - 1)]
        tree = Tree(
            "T",
            {
                "root": 0,
                "nodes": nodes,
                "edges": edges,
            },
        )
        assert tree._compute_max_depth() == n - 1


# ---------------------------------------------------------------------------
# Bug 2: Graph O(N^2) layout DoS
# ---------------------------------------------------------------------------


class TestGraphQuadraticLayoutDoS:
    """``Graph`` must reject oversized node sets before running layout."""

    def test_graph_with_cycle_of_1000_nodes_raises_e1501(self) -> None:
        """A 1000-node cycle must be rejected, not silently rendered.

        Wave 4B fix: ``Graph.__init__`` now raises ``E1501`` when
        ``len(nodes) > _MAX_NODES`` so a malicious editorial cannot
        burn seconds of renderer time on O(N^2) force-layout.
        """
        n = 1000
        nodes = list(range(n))
        edges = [(i, (i + 1) % n) for i in range(n)]
        with pytest.raises(Exception, match="E1501"):
            Graph("G", {"nodes": nodes, "edges": edges})

    def test_graph_at_exactly_max_nodes_succeeds(self) -> None:
        """A graph with exactly ``_MAX_NODES`` nodes must still build."""
        nodes = list(range(_MAX_NODES))
        edges = [(i, (i + 1) % _MAX_NODES) for i in range(_MAX_NODES)]
        g = Graph("G", {"nodes": nodes, "edges": edges})
        assert len(g.nodes) == _MAX_NODES
        assert len(g.positions) == _MAX_NODES

    def test_graph_one_above_cap_raises(self) -> None:
        """One node above the cap must raise ``E1501``."""
        n = _MAX_NODES + 1
        nodes = list(range(n))
        edges: list[tuple[int, int]] = []
        with pytest.raises(Exception, match="E1501"):
            Graph("G", {"nodes": nodes, "edges": edges})

    def test_graph_cap_error_message_mentions_stable_layout(self) -> None:
        """Error message should hint at the ``layout=stable`` workaround."""
        n = _MAX_NODES + 50
        nodes = list(range(n))
        with pytest.raises(Exception) as excinfo:
            Graph("G", {"nodes": nodes, "edges": []})
        msg = str(excinfo.value)
        assert "E1501" in msg
        # Message must surface both the offending count and the
        # maximum so users can understand and fix.
        assert str(n) in msg
        assert str(_MAX_NODES) in msg
        assert "stable" in msg.lower() or "split" in msg.lower()

    def test_graph_construction_fast_for_reasonable_size(self) -> None:
        """Graphs under the cap should construct in bounded time."""
        nodes = list(range(50))
        edges = [(i, (i + 1) % 50) for i in range(50)]
        start = time.perf_counter()
        Graph("G", {"nodes": nodes, "edges": edges})
        elapsed = time.perf_counter() - start
        # 50 nodes × 50 iters ≈ 125k force-pair ops; should be well
        # under a second.
        assert elapsed < 2.0, (
            f"50-node graph construction took {elapsed:.2f}s; "
            f"expected < 2.0s"
        )
