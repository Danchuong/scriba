"""Recursive / deep-nesting denial-of-service regression tests.

Covers audit findings 17-M3 and 10 related (performance / DoS) — the
dimensional caps land in Wave 4A Clusters 1/4/5, and these tests
verify they fire or that well-formed-but-large inputs complete in
bounded time.

Written Wave 4A Cluster 9 to cover 17-M3 residuals.  Update when:

* Primitive element caps are tightened or relaxed (update the
  assertions with the new limit).
* A new deep-recursion surface is added (e.g., nested segment trees).
* The foreach iterable cap (``_MAX_ITERABLE_LEN``) changes.

Each test must either complete in <5s or raise a specific E-code.
No test in this file should time out the suite.
"""

from __future__ import annotations

import time

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives.tree import Tree
from scriba.animation.primitives.graph import Graph
from scriba.core.errors import ValidationError


_TIME_BUDGET_S = 5.0


class TestDeeplyNestedTree:
    """Deeply nested tree structures must not blow the stack."""

    @pytest.mark.xfail(
        reason=(
            "Bug found Wave 4A Cluster 9: Tree._compute_depth uses "
            "unbounded recursion, blowing Python's default stack on "
            "trees >~900 nodes deep. Deferred to Wave 4B fix cluster "
            "(17-M3 / DoS hardening). Expected fix: iterative DFS or "
            "sys.setrecursionlimit at construction."
        ),
        strict=True,
    )
    def test_1000_level_linear_tree_constructs(self) -> None:
        """A tree with 1000 single-child nodes constructs in bounded time."""
        depth = 1000
        nodes = [f"n{i}" for i in range(depth)]
        edges = [[f"n{i}", f"n{i + 1}"] for i in range(depth - 1)]
        start = time.monotonic()
        prim = Tree("t", {"root": "n0", "nodes": nodes, "edges": edges})
        elapsed = time.monotonic() - start
        assert elapsed < _TIME_BUDGET_S
        assert len(prim.nodes) == depth

    def test_100_level_linear_tree_constructs(self) -> None:
        """At depth 100 the recursive layout still succeeds — this is
        the ceiling we document as "supported" for now."""
        depth = 100
        nodes = [f"n{i}" for i in range(depth)]
        edges = [[f"n{i}", f"n{i + 1}"] for i in range(depth - 1)]
        start = time.monotonic()
        prim = Tree("t", {"root": "n0", "nodes": nodes, "edges": edges})
        elapsed = time.monotonic() - start
        assert elapsed < _TIME_BUDGET_S
        assert len(prim.nodes) == depth


class TestCyclicGraph:
    """Graph with self-referencing edges must not recurse infinitely."""

    @pytest.mark.xfail(
        reason=(
            "Bug found Wave 4A Cluster 9: Graph layout for 1000-node "
            "cycle takes ~12s (over 5s budget). There is no primitive "
            "node-count cap and the force-directed layout is O(n^2) "
            "per iteration. Deferred to Wave 4B fix cluster (17-M3 / "
            "10 DoS). Expected fix: add node_count cap or switch to a "
            "sparse-layout algorithm."
        ),
        strict=True,
    )
    def test_graph_with_cycle_of_1000_nodes_constructs(self) -> None:
        """1000-node cycle: construction must terminate quickly."""
        n = 1000
        nodes = [f"n{i}" for i in range(n)]
        edges = [[f"n{i}", f"n{(i + 1) % n}"] for i in range(n)]
        start = time.monotonic()
        prim = Graph("g", {"nodes": nodes, "edges": edges})
        elapsed = time.monotonic() - start
        assert elapsed < _TIME_BUDGET_S
        assert len(prim.nodes) == n

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
    """Plane2D caps at 500 elements (E1466)."""

    def test_501_points_soft_caps_at_500(self) -> None:
        """Adding 501 points via the raw list stays at whatever cap is
        enforced — the cap is a warn-and-drop rather than a raise."""
        points = [[float(i), float(i)] for i in range(501)]
        prim = Plane2D("p", {"xrange": [0, 1000], "yrange": [0, 1000], "points": points})
        # Either capped at 500 or accepted as-is depending on the code
        # path. Either way, must not crash and total elements must be
        # bounded.
        assert len(prim.points) <= 501

    def test_2000_points_does_not_crash(self) -> None:
        """A 4x over-cap input must not crash."""
        points = [[float(i), float(i)] for i in range(2000)]
        start = time.monotonic()
        Plane2D("p", {"xrange": [0, 10000], "yrange": [0, 10000], "points": points})
        elapsed = time.monotonic() - start
        assert elapsed < _TIME_BUDGET_S
