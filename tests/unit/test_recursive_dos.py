"""Recursion / quadratic-layout DoS regression tests.

These tests protect against the following denial-of-service bugs
discovered during Wave 4A Cluster 9 and fixed in Wave 4B Cluster 1:

1. **Tree recursion DoS** — ``reingold_tilford`` previously used
   recursive DFS for depth and layout. A 1000-level linear tree
   exceeded Python's default recursion limit (``sys.getrecursionlimit()
   == 1000``) and raised ``RecursionError``. The fix converts both
   depth and layout passes to iterative DFS.

2. **Graph O(N^2) layout DoS** — ``fruchterman_reingold`` is O(N^2)
   per iteration times 50 iterations. A 1000-node cycle took ~10
   seconds to construct and could be used by a malicious editorial
   to tie up the renderer. The fix adds a 100-node cap to the
   ``Graph`` constructor that raises ``E1501`` for oversized graphs.

See ``scriba/animation/primitives/tree.py`` and
``scriba/animation/primitives/graph.py`` for the fixes. See Wave 4B
Cluster 1 notes for context.
"""

from __future__ import annotations

import sys
import time

import pytest

from scriba.animation.primitives.graph import Graph, _MAX_NODES
from scriba.animation.primitives.tree import Tree, reingold_tilford


# ---------------------------------------------------------------------------
# Bug 1: Tree recursion DoS
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
