"""Unit tests for the obstacle-geometry Protocol extension (v0.12.0 prep).

Covers:
- All 15 concrete primitives expose ``resolve_obstacle_boxes`` and
  ``resolve_obstacle_segments`` as callable attributes.
- Stub implementations return an empty list on both methods.
- ``PrimitiveProtocol`` declares the two new methods.
- Existing ``_REQUIRED_PROTOCOL_METHODS`` set is unchanged (advisory mode
  for third-party primitives is not broken).

See docs/spec/smart-label-ruleset.md R-02/R-03/R-04 and
docs/archive/smart-label-edge-avoidance-2026-04-22/R-31-plan.md.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives._obstacle_types import ObstacleAABB, ObstacleSegment
from scriba.animation.primitives._protocol import (
    PrimitiveProtocol,
    _REQUIRED_PROTOCOL_METHODS,
)
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.codepanel import CodePanel
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.hashmap import HashMap
from scriba.animation.primitives.linkedlist import LinkedList
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.metricplot import MetricPlot
from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.animation.primitives.plane2d import Plane2D
from scriba.animation.primitives.queue import Queue
from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.tree import Tree
from scriba.animation.primitives.variablewatch import VariableWatch


# ---------------------------------------------------------------------------
# All primitive classes under test
# ---------------------------------------------------------------------------

_ALL_PRIMITIVE_CLASSES: list[type] = [
    ArrayPrimitive,
    CodePanel,
    DPTablePrimitive,
    Graph,
    GridPrimitive,
    HashMap,
    LinkedList,
    MatrixPrimitive,
    MetricPlot,
    NumberLinePrimitive,
    Plane2D,
    Queue,
    Stack,
    Tree,
    VariableWatch,
]


# ---------------------------------------------------------------------------
# Minimal constructor arguments for each class
# ---------------------------------------------------------------------------

def _make_instance(cls: type):
    """Return a minimally-constructed instance of *cls*.

    Uses the same minimal param sets seen in existing primitive unit tests.
    Raises pytest.skip if a class turns out to require non-trivial setup
    beyond what is documented here (should not happen for stubs).
    """
    if cls is ArrayPrimitive:
        return cls("a", {"size": 3})
    if cls is CodePanel:
        return cls("code", {"source": "x = 1"})
    if cls is DPTablePrimitive:
        return cls("dp", {"rows": 2, "cols": 3})
    if cls is Graph:
        return cls("G", {"nodes": ["A", "B"], "edges": [("A", "B")]})
    if cls is GridPrimitive:
        return cls("g", {"rows": 2, "cols": 2})
    if cls is HashMap:
        return cls("hm", {"capacity": 4})
    if cls is LinkedList:
        return cls("ll", {"data": [1, 2, 3]})
    if cls is MatrixPrimitive:
        return cls("m", {"rows": 2, "cols": 2})
    if cls is MetricPlot:
        return cls("mp", {"series": ["x"]})
    if cls is NumberLinePrimitive:
        return cls("nl", {"domain": [0, 10], "ticks": 5})
    if cls is Plane2D:
        return cls("p", {})
    if cls is Queue:
        return cls("q", {"capacity": 4})
    if cls is Stack:
        return cls("s", {})
    if cls is Tree:
        return cls("T", {"root": "A", "nodes": ["A", "B", "C"], "edges": [("A", "B"), ("A", "C")]})
    if cls is VariableWatch:
        return cls("vars", {"names": ["i", "j"]})
    pytest.skip(f"No constructor recipe for {cls.__name__}")


# ---------------------------------------------------------------------------
# Test: all primitives have resolve_obstacle_boxes
# ---------------------------------------------------------------------------


class TestAllPrimitivesHaveResolveObstacleBoxes:
    @pytest.mark.parametrize("cls", _ALL_PRIMITIVE_CLASSES, ids=lambda c: c.__name__)
    def test_callable(self, cls: type) -> None:
        assert callable(getattr(cls, "resolve_obstacle_boxes", None)), (
            f"{cls.__name__} is missing callable resolve_obstacle_boxes"
        )


# ---------------------------------------------------------------------------
# Test: all primitives have resolve_obstacle_segments
# ---------------------------------------------------------------------------


class TestAllPrimitivesHaveResolveObstacleSegments:
    @pytest.mark.parametrize("cls", _ALL_PRIMITIVE_CLASSES, ids=lambda c: c.__name__)
    def test_callable(self, cls: type) -> None:
        assert callable(getattr(cls, "resolve_obstacle_segments", None)), (
            f"{cls.__name__} is missing callable resolve_obstacle_segments"
        )


# ---------------------------------------------------------------------------
# Test: stubs return empty list (for primitives still on W0-[A] stubs)
# ---------------------------------------------------------------------------

# Plane2D gained a real resolve_obstacle_segments in v0.12.0 W3-α —
# it returns axis spines + plot lines.  It is excluded from the
# "stubs return empty" check below.
_SEGMENT_STUBS: list[type] = [c for c in _ALL_PRIMITIVE_CLASSES if c is not Plane2D]


class TestStubsReturnEmptyList:
    @pytest.mark.parametrize("cls", _ALL_PRIMITIVE_CLASSES, ids=lambda c: c.__name__)
    def test_resolve_obstacle_boxes_returns_empty(self, cls: type) -> None:
        inst = _make_instance(cls)
        result = inst.resolve_obstacle_boxes()
        assert result == [], (
            f"{cls.__name__}.resolve_obstacle_boxes() returned {result!r}, expected []"
        )

    @pytest.mark.parametrize("cls", _SEGMENT_STUBS, ids=lambda c: c.__name__)
    def test_resolve_obstacle_segments_returns_empty(self, cls: type) -> None:
        """Non-Plane2D primitives are still on W0-[A] stubs — must return []."""
        inst = _make_instance(cls)
        result = inst.resolve_obstacle_segments()
        assert result == [], (
            f"{cls.__name__}.resolve_obstacle_segments() returned {result!r}, expected []"
        )

    def test_plane2d_resolve_obstacle_segments_returns_list_of_obstacle_segment(
        self,
    ) -> None:
        """Plane2D.resolve_obstacle_segments has a real implementation (W3-α)."""
        from scriba.animation.primitives._obstacle_types import ObstacleSegment

        inst = _make_instance(Plane2D)
        result = inst.resolve_obstacle_segments()
        assert isinstance(result, list)
        for seg in result:
            assert isinstance(seg, ObstacleSegment), (
                f"Expected ObstacleSegment, got {type(seg)!r}"
            )


# ---------------------------------------------------------------------------
# Test: PrimitiveProtocol declares both methods
# ---------------------------------------------------------------------------


class TestProtocolDeclaresObstacleMethods:
    def test_resolve_obstacle_boxes_in_protocol(self) -> None:
        protocol_members = {
            name for name in dir(PrimitiveProtocol) if not name.startswith("_")
        }
        assert "resolve_obstacle_boxes" in protocol_members, (
            "PrimitiveProtocol does not declare resolve_obstacle_boxes"
        )

    def test_resolve_obstacle_segments_in_protocol(self) -> None:
        protocol_members = {
            name for name in dir(PrimitiveProtocol) if not name.startswith("_")
        }
        assert "resolve_obstacle_segments" in protocol_members, (
            "PrimitiveProtocol does not declare resolve_obstacle_segments"
        )

    def test_required_methods_set_unchanged(self) -> None:
        """_REQUIRED_PROTOCOL_METHODS must not include obstacle methods.

        Third-party primitives registered before v0.12.0 W2 ship must not
        receive advisory warnings for missing obstacle stubs. The required
        set stays at the original six methods.
        """
        assert "resolve_obstacle_boxes" not in _REQUIRED_PROTOCOL_METHODS, (
            "resolve_obstacle_boxes must not be in _REQUIRED_PROTOCOL_METHODS yet "
            "(would break third-party advisory-mode registration)"
        )
        assert "resolve_obstacle_segments" not in _REQUIRED_PROTOCOL_METHODS, (
            "resolve_obstacle_segments must not be in _REQUIRED_PROTOCOL_METHODS yet"
        )


# ---------------------------------------------------------------------------
# Test: ObstacleAABB and ObstacleSegment are frozen dataclasses
# ---------------------------------------------------------------------------


class TestObstacleTypes:
    def test_obstacle_aabb_is_frozen(self) -> None:
        box = ObstacleAABB(
            kind="target_cell", x=0.0, y=0.0, w=40.0, h=40.0, severity="MUST"
        )
        with pytest.raises((AttributeError, TypeError)):
            box.x = 99.0  # type: ignore[misc]

    def test_obstacle_aabb_fields(self) -> None:
        box = ObstacleAABB(
            kind="axis_label", x=10.0, y=20.0, w=30.0, h=15.0, severity="SHOULD"
        )
        assert box.kind == "axis_label"
        assert box.x == 10.0
        assert box.y == 20.0
        assert box.w == 30.0
        assert box.h == 15.0
        assert box.severity == "SHOULD"

    def test_obstacle_segment_is_frozen(self) -> None:
        seg = ObstacleSegment(
            kind="edge", x0=0.0, y0=0.0, x1=100.0, y1=100.0,
            state="current", severity="MUST",
        )
        with pytest.raises((AttributeError, TypeError)):
            seg.x0 = 99.0  # type: ignore[misc]

    def test_obstacle_segment_fields(self) -> None:
        seg = ObstacleSegment(
            kind="plot_line", x0=5.0, y0=10.0, x1=50.0, y1=80.0,
            state="dim", severity="SHOULD",
        )
        assert seg.kind == "plot_line"
        assert seg.x0 == 5.0
        assert seg.y0 == 10.0
        assert seg.x1 == 50.0
        assert seg.y1 == 80.0
        assert seg.state == "dim"
        assert seg.severity == "SHOULD"
