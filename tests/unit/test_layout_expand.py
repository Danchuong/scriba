"""RED tests for Phase 5 Auto-Expansion (GEP v2.0 U-15).

These tests are intentionally written BEFORE the implementation module
``scriba/animation/primitives/_layout_expand.py`` exists.  Every test in this
file is expected to fail with ``ImportError`` or ``AttributeError`` until the
implementation is in place (TDD RED state).

Design doc: docs/plans/phase-5-auto-expansion-design.md
"""

from __future__ import annotations

import copy
import math

import pytest

from scriba.animation.primitives._layout_expand import (  # noqa: F401 — RED import
    _cascade_fallback_count,
    _find_min_scale,
    _min_scale_analytic,
)
from scriba.animation.primitives.graph import Graph


# ---------------------------------------------------------------------------
# Pentagon helper — deterministic K5 positions (no RNG)
# ---------------------------------------------------------------------------


def _k5_positions() -> dict[str, tuple[float, float]]:
    """Return 5 nodes on a regular pentagon centred at (200, 150), r=100.

    Labelled "A"–"E".  All coordinates are deterministic — no random seed
    dependence.
    """
    cx, cy, r = 200.0, 150.0, 100.0
    nodes = ["A", "B", "C", "D", "E"]
    return {
        n: (
            cx + r * math.cos(2 * math.pi * i / 5 - math.pi / 2),
            cy + r * math.sin(2 * math.pi * i / 5 - math.pi / 2),
        )
        for i, n in enumerate(nodes)
    }


def _k5_edges_data() -> list[tuple[str, str, float | None]]:
    """All 10 edges of K5 with weight 1.0."""
    nodes = ["A", "B", "C", "D", "E"]
    return [
        (u, v, 1.0)
        for i, u in enumerate(nodes)
        for v in nodes[i + 1 :]
    ]


# ---------------------------------------------------------------------------
# Test 1 — analytic per-edge formula (hand-computed)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_min_scale_per_edge_formula() -> None:
    """_min_scale_analytic returns max(1.0, max(s_min_edge)) over all edges.

    Scenario A — horizontal edge, edge_len=100, pill_w=40, aabb_w=40, node_r=10:
        s_min_edge = (pill_w + 2*node_r) / edge_len = (40 + 20) / 100 = 0.60
        clamped:    max(1.0, 0.60) = 1.0

    Scenario B — tight edge, edge_len=50, pill_w=40, aabb_w=40, node_r=10:
        s_min_edge = (40 + 20) / 50 = 1.20
        clamped:    max(1.0, 1.20) = 1.20
    """
    node_r = 10.0

    # Scenario A — single horizontal edge of length 100
    edges_a: list[tuple[float, float, float, float, float, float]] = [
        (0.0, 0.0, 100.0, 0.0, 40.0, 40.0),
    ]
    result_a = _min_scale_analytic(edges_a, node_r)
    assert math.isclose(result_a, 1.0, abs_tol=1e-6), (
        f"Scenario A: expected 1.0, got {result_a}"
    )

    # Scenario B — tight horizontal edge of length 50
    edges_b: list[tuple[float, float, float, float, float, float]] = [
        (0.0, 0.0, 50.0, 0.0, 40.0, 40.0),
    ]
    result_b = _min_scale_analytic(edges_b, node_r)
    assert math.isclose(result_b, 1.2, abs_tol=1e-6), (
        f"Scenario B: expected 1.2, got {result_b}"
    )


# ---------------------------------------------------------------------------
# Test 2 — binary search converges on a crowded K5
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_binary_search_converges() -> None:
    """_find_min_scale returns s in (1.0, 3.0] such that fallback_count == 0.

    K5 (5 nodes, 10 edges) on a 400×300 canvas with node_r=20.  At scale 1.0
    the dense pentagon geometry forces at least one pill into a leader stage.
    The binary search must return a scale that eliminates all fallbacks.
    """
    positions = _k5_positions()
    edges_data = _k5_edges_data()
    node_r = 20.0

    s = _find_min_scale(
        positions,
        edges_data,
        node_r=node_r,
        directed=False,
        canvas_w=400.0,
        canvas_h=300.0,
    )

    assert 1.0 < s <= 3.0, f"Expected s in (1.0, 3.0], got {s}"

    # Scale positions by s and verify zero fallbacks at the returned scale
    scaled: dict[str, tuple[float, float]] = {
        k: (v[0] * s, v[1] * s) for k, v in positions.items()
    }
    count = _cascade_fallback_count(
        scaled,
        edges_data,
        node_r=node_r,
        directed=False,
    )
    assert count == 0, (
        f"Expected 0 fallbacks at s={s:.4f}, got {count}"
    )


# ---------------------------------------------------------------------------
# Test 3 — auto_expand opt-in flag controls leader appearance in SVG
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_auto_expand_opt_in_flag() -> None:
    """auto_expand=True monotonically reduces or equals the leader count of
    auto_expand=False (default).

    Builds a dense Graph (K7, 21 edges, show_weights=True) with a fixed
    layout_seed so positions are deterministic.  If the default rendering
    produces leader markers, the expanded rendering must produce strictly
    fewer; if the default already has zero leaders (geometry too sparse on
    this canvas), the expanded rendering must also have zero.  Additionally,
    the two SVGs must differ whenever expansion was actually applied
    (s > 1.0 path), ensuring the flag has an observable effect.
    """
    base_params = {
        "nodes": ["A", "B", "C", "D", "E", "F", "G"],
        "edges": [
            ("A", "B", 1.0), ("A", "C", 2.0), ("A", "D", 3.0),
            ("A", "E", 4.0), ("A", "F", 5.0), ("A", "G", 6.0),
            ("B", "C", 7.0), ("B", "D", 8.0), ("B", "E", 9.0),
            ("B", "F", 10.0), ("B", "G", 11.0),
            ("C", "D", 12.0), ("C", "E", 13.0), ("C", "F", 14.0),
            ("C", "G", 15.0),
            ("D", "E", 16.0), ("D", "F", 17.0), ("D", "G", 18.0),
            ("E", "F", 19.0), ("E", "G", 20.0),
            ("F", "G", 21.0),
        ],
        "show_weights": True,
        "layout_seed": 42,
    }

    g_default = Graph("K7", {**base_params, "auto_expand": False})
    svg_default = g_default.emit_svg()
    assert isinstance(svg_default, str) and len(svg_default) > 0

    g_expand = Graph("K7", {**base_params, "auto_expand": True})
    svg_expand = g_expand.emit_svg()
    assert isinstance(svg_expand, str) and len(svg_expand) > 0

    leader_marker = 'stroke-dasharray="3,2"'
    leaders_default = svg_default.count(leader_marker)
    leaders_expand = svg_expand.count(leader_marker)

    # Observable-effect invariant: True must reduce (or equal, if canvas cap
    # binds per design §8) the leader count; never increase it.  GEP-17 remains
    # the correctness floor, so some leaders may persist when canvas_bound_scale
    # or the 3.0 hard cap forbid further expansion.
    assert leaders_expand <= leaders_default, (
        f"auto_expand=True must not increase leader count; "
        f"got default={leaders_default}, expand={leaders_expand}"
    )
    assert leaders_default >= 1, (
        "Test premise: K7+seed=42 on default canvas must produce ≥1 leader "
        f"at auto_expand=False; got {leaders_default}. Pick a denser setup."
    )
    assert leaders_expand < leaders_default, (
        f"auto_expand=True must strictly reduce leader count vs False "
        f"(observable effect); got default={leaders_default}, "
        f"expand={leaders_expand}"
    )


# ---------------------------------------------------------------------------
# Test 4 — canvas bound clamp caps s at min(3.0, canvas_bound_scale)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_canvas_bound_clamp() -> None:
    """_find_min_scale never exceeds min(3.0, canvas_bound_scale).

    Degenerate case: tiny 100×100 canvas, edge length 20, pill_w=80, node_r=10.
        s_min_analytic = (80 + 20) / 20 = 5.0  →  exceeds hard cap 3.0.

    The function must return s ≤ 3.0 (hard cap) and must equal the effective
    cap = min(3.0, canvas_bound_scale).
    """
    # Two nodes 20 px apart on a 100×100 canvas.
    positions: dict[str, tuple[float, float]] = {
        "U": (40.0, 50.0),
        "V": (60.0, 50.0),
    }
    # One edge with pill_w that forces analytic s_min far above 3.0.
    # We pass this through edges_data (Graph internal repr: (u, v, weight)).
    edges_data: list[tuple[str, str, float | None]] = [("U", "V", 1.0)]

    s = _find_min_scale(
        positions,
        edges_data,
        node_r=10.0,
        directed=False,
        canvas_w=100.0,
        canvas_h=100.0,
    )

    assert s <= 3.0, f"Expected s ≤ 3.0 (hard cap), got {s}"

    # The returned value must equal effective_cap = min(3.0, canvas_bound_scale).
    # canvas_bound_scale: largest s such that all scaled nodes stay in-canvas.
    # With node at x=60, canvas_w=100: canvas_bound_scale ≈ 100/60 ≈ 1.667.
    # effective_cap = min(3.0, ~1.667) = ~1.667.  s must equal that.
    max_x = max(x for (x, _y) in positions.values())
    max_y = max(y for (_x, y) in positions.values())
    canvas_w = 100.0
    canvas_h = 100.0
    canvas_bound_scale = min(canvas_w / max_x, canvas_h / max_y)
    effective_cap = min(3.0, canvas_bound_scale)

    assert math.isclose(s, effective_cap, abs_tol=0.05), (
        f"Expected s ≈ effective_cap={effective_cap:.4f}, got {s:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 5 — dataset topology preserved after emit_svg (U-05 working-copy check)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dataset_topology_preserved() -> None:
    """emit_svg with auto_expand=True must not mutate graph.edges, .nodes, .positions.

    Uses copy.deepcopy to snapshot the three attributes before the call, then
    asserts equality (not identity) after the call completes.  This verifies
    the working-copy pattern specified in the design doc: self.positions is
    never written during auto_expand scaling.
    """
    g = Graph(
        "Topo",
        {
            "nodes": ["A", "B", "C", "D"],
            "edges": [
                ("A", "B", 1.0),
                ("A", "C", 2.0),
                ("B", "C", 3.0),
                ("B", "D", 4.0),
                ("C", "D", 5.0),
            ],
            "show_weights": True,
            "auto_expand": True,
            "layout_seed": 7,
        },
    )

    snapshot_edges = copy.deepcopy(g.edges)
    snapshot_nodes = copy.deepcopy(g.nodes)
    snapshot_positions = copy.deepcopy(g.positions)

    _ = g.emit_svg()

    assert g.edges == snapshot_edges, (
        "emit_svg mutated graph.edges"
    )
    assert g.nodes == snapshot_nodes, (
        "emit_svg mutated graph.nodes"
    )
    assert g.positions == snapshot_positions, (
        "emit_svg mutated graph.positions (working-copy invariant violated)"
    )
