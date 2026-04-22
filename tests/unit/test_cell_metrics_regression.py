"""Phase D/3 regression tests for CellMetrics field values.

Pins the per-primitive CellMetrics fields that each primitive's
``emit_svg`` passes to ``emit_annotation_arrows`` when an annotation
is attached.  Catches silent drift in ``cell_width`` / ``cell_height``
/ ``grid_cols`` / ``grid_rows`` / ``origin_x`` / ``origin_y`` without
needing a full golden SVG regen round-trip.

Each test:
  1. constructs a minimal primitive with a single ``arrow_from``
     annotation,
  2. patches ``PrimitiveBase.emit_annotation_arrows`` to capture the
     ``cell_metrics`` kwarg,
  3. calls ``emit_svg`` to trigger dispatch,
  4. asserts on the exact CellMetrics field values.
"""

from __future__ import annotations

from typing import Any

import pytest

from scriba.animation.primitives import base as _base
from scriba.animation.primitives import queue as _queue_module
from scriba.animation.primitives._svg_helpers import CellMetrics
from scriba.animation.primitives._types import CELL_HEIGHT, CELL_WIDTH
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.dptable import DPTablePrimitive
from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.queue import Queue
from scriba.animation.primitives.tree import Tree


# ---------------------------------------------------------------------------
# Helper — intercept the cell_metrics kwarg
# ---------------------------------------------------------------------------


@pytest.fixture
def capture_cell_metrics(monkeypatch: pytest.MonkeyPatch):
    """Patch emit_annotation_arrows to record each cell_metrics kwarg."""
    captured: list[CellMetrics | None] = []
    original = _base.PrimitiveBase.emit_annotation_arrows

    def _spy(
        self: Any,
        parts: list[str],
        annotations: list[dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        captured.append(kwargs.get("cell_metrics"))
        return original(self, parts, annotations, **kwargs)

    monkeypatch.setattr(_base.PrimitiveBase, "emit_annotation_arrows", _spy)
    return captured


@pytest.fixture
def capture_queue_cell_metrics(monkeypatch: pytest.MonkeyPatch):
    """Patch queue module's emit_arrow_svg to record cell_metrics directly.

    Queue bypasses ``emit_annotation_arrows`` and calls ``emit_arrow_svg``
    directly, so it needs a separate capture hook.
    """
    captured: list[CellMetrics | None] = []
    original = _queue_module.emit_arrow_svg

    def _spy(*args: Any, **kwargs: Any) -> None:
        captured.append(kwargs.get("cell_metrics"))
        return original(*args, **kwargs)

    monkeypatch.setattr(_queue_module, "emit_arrow_svg", _spy)
    return captured


# ---------------------------------------------------------------------------
# Array
# ---------------------------------------------------------------------------


class TestArrayCellMetrics:
    def test_array_default_cell_width(
        self, capture_cell_metrics: list[CellMetrics | None]
    ) -> None:
        inst = ArrayPrimitive("a", {"size": 5})
        inst.set_annotations(
            [{"target": "a.cell[2]", "label": "X", "arrow_from": "a.cell[0]"}]
        )
        inst.emit_svg()

        assert len(capture_cell_metrics) == 1
        cm = capture_cell_metrics[0]
        assert cm is not None
        assert cm.cell_width == float(CELL_WIDTH)
        assert cm.cell_height == float(CELL_HEIGHT)
        assert cm.grid_cols == 5
        assert cm.grid_rows == 1
        assert cm.origin_x == 0.0
        assert cm.origin_y == 0.0


# ---------------------------------------------------------------------------
# DPTable — 1D
# ---------------------------------------------------------------------------


class TestDPTable1DCellMetrics:
    def test_dptable_1d_shape(
        self, capture_cell_metrics: list[CellMetrics | None]
    ) -> None:
        inst = DPTablePrimitive("dp", {"n": 5})
        inst.set_annotations(
            [{"target": "dp.cell[2]", "label": "X", "arrow_from": "dp.cell[0]"}]
        )
        inst.emit_svg()

        assert len(capture_cell_metrics) == 1
        cm = capture_cell_metrics[0]
        assert cm is not None
        assert cm.cell_width == float(CELL_WIDTH)
        assert cm.cell_height == float(CELL_HEIGHT)
        assert cm.grid_cols == 5
        # 1D tables collapse to a single row.
        assert cm.grid_rows == 1
        assert cm.origin_x == 0.0
        assert cm.origin_y == 0.0


# ---------------------------------------------------------------------------
# DPTable — 2D
# ---------------------------------------------------------------------------


class TestDPTable2DCellMetrics:
    def test_dptable_2d_shape(
        self, capture_cell_metrics: list[CellMetrics | None]
    ) -> None:
        inst = DPTablePrimitive("dp", {"rows": 3, "cols": 4})
        inst.set_annotations(
            [
                {
                    "target": "dp.cell[1][2]",
                    "label": "X",
                    "arrow_from": "dp.cell[0][0]",
                }
            ]
        )
        inst.emit_svg()

        assert len(capture_cell_metrics) == 1
        cm = capture_cell_metrics[0]
        assert cm is not None
        assert cm.cell_width == float(CELL_WIDTH)
        assert cm.cell_height == float(CELL_HEIGHT)
        assert cm.grid_cols == 4
        assert cm.grid_rows == 3


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------


class TestQueueCellMetrics:
    def test_queue_capacity_is_grid_cols(
        self, capture_queue_cell_metrics: list[CellMetrics | None]
    ) -> None:
        inst = Queue("q", {"capacity": 4, "data": [1, 2]})
        inst.set_annotations(
            [{"target": "q.cell[1]", "label": "X", "arrow_from": "q.cell[0]"}]
        )
        inst.emit_svg()

        assert len(capture_queue_cell_metrics) == 1
        cm = capture_queue_cell_metrics[0]
        assert cm is not None
        assert cm.cell_height == float(CELL_HEIGHT)
        assert cm.grid_cols == 4
        assert cm.grid_rows == 1
        assert cm.origin_x == 0.0
        assert cm.origin_y == 0.0


# ---------------------------------------------------------------------------
# Graph — node-diameter proxy
# ---------------------------------------------------------------------------


class TestGraphCellMetrics:
    def test_graph_node_diameter_proxy(
        self, capture_cell_metrics: list[CellMetrics | None]
    ) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "B", "C"], "edges": [("A", "B"), ("A", "C")]},
        )
        g.set_annotations(
            [{"target": "G.node[A]", "label": "X", "arrow_from": "G.node[B]"}]
        )
        g.emit_svg()

        assert len(capture_cell_metrics) == 1
        cm = capture_cell_metrics[0]
        assert cm is not None
        expected_diam = float(g._node_radius * 2)
        assert cm.cell_width == expected_diam
        assert cm.cell_height == expected_diam
        assert cm.grid_cols == 3  # len(nodes)
        assert cm.grid_rows == 1
        assert cm.origin_x == 0.0
        assert cm.origin_y == 0.0


# ---------------------------------------------------------------------------
# Tree — node-diameter proxy
# ---------------------------------------------------------------------------


class TestTreeCellMetrics:
    def test_tree_node_diameter_proxy(
        self, capture_cell_metrics: list[CellMetrics | None]
    ) -> None:
        t = Tree(
            "T",
            {"root": 1, "nodes": [1, 2, 3], "edges": [(1, 2), (1, 3)]},
        )
        t.set_annotations(
            [{"target": "T.node[2]", "label": "X", "arrow_from": "T.node[1]"}]
        )
        t.emit_svg()

        assert len(capture_cell_metrics) == 1
        cm = capture_cell_metrics[0]
        assert cm is not None
        expected_diam = float(t._node_radius * 2)
        assert cm.cell_width == expected_diam
        assert cm.cell_height == expected_diam
        assert cm.grid_cols == 3
        assert cm.grid_rows == 1
