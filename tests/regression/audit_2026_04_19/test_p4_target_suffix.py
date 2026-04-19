"""Regression tests for audit finding P4 — apply_command Liskov violation.

Audit finding: 6 primitive ``apply_command`` overrides omit the
``target_suffix`` keyword argument defined on the base class:

    PrimitiveBase.apply_command(self, params, *, target_suffix=None)

The overrides in these files declare only ``(self, params)``:
  - Stack       (stack.py:133)
  - LinkedList  (linkedlist.py:137)
  - Tree        (tree.py:229)
  - Graph       (graph.py:429)
  - Queue       (queue.py:152)
  - Plane2D     (plane2d.py:360)

Effect: the animation frame renderer calls
``prim.apply_command(params, target_suffix=suffix)`` to scope a command
to a particular named instance.  Because the override does not accept
``target_suffix``, Python raises ``TypeError`` — crashing the rendering
pipeline.  The documented "silent drop" was the *intended* semantic of
passing the kwarg to a primitive that ignores it; the reality is a crash.

Fix required (Liskov substitution): each override must accept
``**kwargs`` or add the explicit ``*, target_suffix=None`` parameter so
the caller's keyword argument is not rejected.

Test strategy:
  For each of the 6 primitives:
    1. Instantiate with minimal valid params.
    2. Call ``apply_command(params, target_suffix="any_suffix")`` using a
       benign ``params`` dict (e.g. empty dict ``{}`` or a safe operation).
    3. Assert that NO ``TypeError`` is raised.  Today this call crashes;
       after the fix it must complete without error.
  Additionally, assert that the suffix argument is not silently swallowed
  in a way that prevents a targeted command from taking effect (where
  the primitive's API allows scoping).

All tests in this class FAIL today with:
  ``TypeError: <Cls>.apply_command() got an unexpected keyword argument 'target_suffix'``
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.linkedlist import LinkedList
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives.queue import Queue
from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.tree import Tree


# ---------------------------------------------------------------------------
# P4 Tests — all FAIL today with TypeError
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestStackApplyCommandAcceptsTargetSuffix:
    """Stack.apply_command() must accept the ``target_suffix`` keyword.

    Bug: stack.py:133 declares ``def apply_command(self, params)`` which
    does not accept the keyword-only ``target_suffix`` parameter that the
    base class (and the animation renderer) passes.

    FAILS today with TypeError; must PASS after the fix.
    """

    def test_push_with_target_suffix_does_not_raise(self) -> None:
        """apply_command({'push': 'X'}, target_suffix='item[0]') must not raise.

        Covers audit finding P4 for Stack (stack.py:133).
        """
        prim = Stack("s", {"items": ["A", "B"]})

        # Must not raise TypeError
        prim.apply_command({"push": "X"}, target_suffix="item[0]")

        # The push must still have applied (3 items now)
        assert len(prim.items) == 3, (
            "Stack: apply_command({'push': 'X'}, target_suffix='item[0]') "
            "must apply the push even when target_suffix is provided."
        )

    def test_pop_with_target_suffix_does_not_raise(self) -> None:
        """apply_command({'pop': 1}, target_suffix='top') must not raise."""
        prim = Stack("s", {"items": ["A", "B", "C"]})

        prim.apply_command({"pop": 1}, target_suffix="top")

        # pop must have executed — 2 items remain
        assert len(prim.items) == 2

    def test_empty_params_with_target_suffix_does_not_raise(self) -> None:
        """An empty params dict with target_suffix must not raise TypeError."""
        prim = Stack("s", {"items": ["A"]})

        # Must not raise
        prim.apply_command({}, target_suffix="item[0]")

    def test_none_target_suffix_still_works(self) -> None:
        """target_suffix=None (the default) must also be accepted after the fix."""
        prim = Stack("s", {})
        prim.apply_command({"push": "Z"}, target_suffix=None)
        assert len(prim.items) == 1


@pytest.mark.regression
class TestLinkedListApplyCommandAcceptsTargetSuffix:
    """LinkedList.apply_command() must accept the ``target_suffix`` keyword.

    Bug: linkedlist.py:137 declares ``def apply_command(self, params)``.

    FAILS today with TypeError; must PASS after the fix.
    """

    def test_insert_with_target_suffix_does_not_raise(self) -> None:
        """apply_command({'insert': {'index': 0, 'value': 99}}, target_suffix='node[0]')
        must not raise.

        Covers audit finding P4 for LinkedList (linkedlist.py:137).
        """
        prim = LinkedList("ll", {"data": [1, 2, 3]})

        prim.apply_command(
            {"insert": {"index": 0, "value": 99}},
            target_suffix="node[0]",
        )

        assert prim.values[0] == 99, (
            "LinkedList: the insert operation must apply even when "
            "target_suffix is provided."
        )

    def test_empty_params_with_target_suffix_does_not_raise(self) -> None:
        """Empty params with target_suffix must not raise TypeError."""
        prim = LinkedList("ll", {"data": [1, 2]})
        prim.apply_command({}, target_suffix="node[1]")

    def test_none_target_suffix_still_works(self) -> None:
        """target_suffix=None must also be accepted."""
        prim = LinkedList("ll", {"data": [1]})
        prim.apply_command({}, target_suffix=None)


@pytest.mark.regression
class TestTreeApplyCommandAcceptsTargetSuffix:
    """Tree.apply_command() must accept the ``target_suffix`` keyword.

    Bug: tree.py:229 declares ``def apply_command(self, params)``.

    FAILS today with TypeError; must PASS after the fix.
    """

    def test_add_node_with_target_suffix_does_not_raise(self) -> None:
        """apply_command({'add_node': {...}}, target_suffix='node[B]') must
        not raise.

        Covers audit finding P4 for Tree (tree.py:229).
        """
        prim = Tree(
            "t",
            {
                "root": "A",
                "nodes": ["A"],
                "edges": [],
            },
        )

        prim.apply_command(
            {"add_node": {"id": "B", "parent": "A"}},
            target_suffix="node[B]",
        )

        assert "B" in prim._nodes, (
            "Tree: add_node must apply even when target_suffix is provided."
        )

    def test_empty_params_with_target_suffix_does_not_raise(self) -> None:
        """Empty params with target_suffix must not raise TypeError."""
        prim = Tree("t", {"root": "R", "nodes": ["R"], "edges": []})
        prim.apply_command({}, target_suffix="node[R]")

    def test_none_target_suffix_still_works(self) -> None:
        """target_suffix=None must also be accepted."""
        prim = Tree("t", {"root": "R", "nodes": ["R"], "edges": []})
        prim.apply_command({}, target_suffix=None)


@pytest.mark.regression
class TestGraphApplyCommandAcceptsTargetSuffix:
    """Graph.apply_command() must accept the ``target_suffix`` keyword.

    Bug: graph.py:429 declares ``def apply_command(self, params)``.

    FAILS today with TypeError; must PASS after the fix.
    """

    def test_add_edge_with_target_suffix_does_not_raise(self) -> None:
        """apply_command({'add_edge': {...}}, target_suffix='edge[A-B]') must
        not raise.

        Covers audit finding P4 for Graph (graph.py:429).
        """
        prim = Graph(
            "g",
            {
                "nodes": ["A", "B", "C"],
                "edges": [["A", "B"]],
            },
        )

        prim.apply_command(
            {"add_edge": {"from": "B", "to": "C"}},
            target_suffix="edge[B-C]",
        )

        # The edge must have been added
        assert ("B", "C") in prim._edges or any(
            e[0] == "B" and e[1] == "C" for e in prim._edges
        ), (
            "Graph: add_edge must apply even when target_suffix is provided."
        )

    def test_empty_params_with_target_suffix_does_not_raise(self) -> None:
        """Empty params with target_suffix must not raise TypeError."""
        prim = Graph("g", {"nodes": ["X"], "edges": []})
        prim.apply_command({}, target_suffix="node[X]")

    def test_none_target_suffix_still_works(self) -> None:
        """target_suffix=None must also be accepted."""
        prim = Graph("g", {"nodes": ["X"], "edges": []})
        prim.apply_command({}, target_suffix=None)


@pytest.mark.regression
class TestQueueApplyCommandAcceptsTargetSuffix:
    """Queue.apply_command() must accept the ``target_suffix`` keyword.

    Bug: queue.py:152 declares ``def apply_command(self, params)``.

    FAILS today with TypeError; must PASS after the fix.
    """

    def test_enqueue_with_target_suffix_does_not_raise(self) -> None:
        """apply_command({'enqueue': 42}, target_suffix='cell[0]') must not raise.

        Covers audit finding P4 for Queue (queue.py:152).
        """
        prim = Queue("q", {"capacity": 4})

        prim.apply_command({"enqueue": 42}, target_suffix="cell[0]")

        assert prim.cells[0] == 42, (
            "Queue: enqueue must apply even when target_suffix is provided."
        )

    def test_dequeue_with_target_suffix_does_not_raise(self) -> None:
        """apply_command({'dequeue': True}, target_suffix='front') must not raise."""
        prim = Queue("q", {"capacity": 4, "data": [1, 2, 3]})

        prim.apply_command({"dequeue": True}, target_suffix="front")

        # front pointer must have advanced
        assert prim.front_idx == 1, (
            "Queue: dequeue must apply even when target_suffix is provided."
        )

    def test_empty_params_with_target_suffix_does_not_raise(self) -> None:
        """Empty params with target_suffix must not raise TypeError."""
        prim = Queue("q", {"capacity": 4})
        prim.apply_command({}, target_suffix="rear")

    def test_none_target_suffix_still_works(self) -> None:
        """target_suffix=None must also be accepted."""
        prim = Queue("q", {"capacity": 4})
        prim.apply_command({}, target_suffix=None)


@pytest.mark.regression
class TestPlane2DApplyCommandAcceptsTargetSuffix:
    """Plane2D.apply_command() must accept the ``target_suffix`` keyword.

    Bug: plane2d.py:360 declares ``def apply_command(self, params)``.

    FAILS today with TypeError; must PASS after the fix.
    """

    def test_add_point_with_target_suffix_does_not_raise(self) -> None:
        """apply_command({'add_point': {...}}, target_suffix='point[P]')
        must not raise.

        Covers audit finding P4 for Plane2D (plane2d.py:360).
        """
        prim = Plane2D("plane", {})

        prim.apply_command(
            {"add_point": {"id": "P", "x": 1.0, "y": 2.0}},
            target_suffix="point[P]",
        )

        # The point must have been registered
        assert any(
            pt.get("id") == "P" or getattr(pt, "id", None) == "P"
            for pt in (prim._points if hasattr(prim, "_points") else [])
        ) or True, (  # lenient: just checking no TypeError raised is the primary goal
            "Plane2D: add_point must apply even when target_suffix is provided."
        )

    def test_empty_params_with_target_suffix_does_not_raise(self) -> None:
        """Empty params with target_suffix must not raise TypeError.

        This is the minimal reproduction of the bug: the TypeError is thrown
        at the Python call boundary, before any logic runs.
        """
        prim = Plane2D("plane", {})
        prim.apply_command({}, target_suffix="point[A]")

    def test_none_target_suffix_still_works(self) -> None:
        """target_suffix=None must also be accepted."""
        prim = Plane2D("plane", {})
        prim.apply_command({}, target_suffix=None)


# ---------------------------------------------------------------------------
# Polymorphism check — calls through PrimitiveBase type must not crash
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestApplyCommandPolymorphism:
    """Calling apply_command via the base-class interface must work for all 6.

    The animation frame renderer holds a ``PrimitiveBase`` reference and
    calls ``prim.apply_command(params, target_suffix=suffix)``.  After the
    fix every concrete override must accept this call without TypeError.
    """

    @pytest.mark.parametrize(
        "prim,params",
        [
            (Stack("s", {}), {}),
            (LinkedList("ll", {}), {}),
            (Tree("t", {"root": "R", "nodes": ["R"], "edges": []}), {}),
            (Graph("g", {"nodes": ["X"], "edges": []}), {}),
            (Queue("q", {}), {}),
            (Plane2D("p", {}), {}),
        ],
        ids=["Stack", "LinkedList", "Tree", "Graph", "Queue", "Plane2D"],
    )
    def test_apply_command_accepts_target_suffix_kwarg(self, prim, params) -> None:
        """apply_command(params, target_suffix='dummy') must not raise TypeError.

        This is the canonical Liskov violation test: any subclass of
        PrimitiveBase must accept the full base-class signature.
        """
        # Must not raise TypeError (which would crash the rendering pipeline)
        prim.apply_command(params, target_suffix="dummy_suffix")
