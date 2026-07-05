"""Unit tests for antiparallel curved edges (C2 gap).

When a *directed* graph holds both ``(u, v)`` and ``(v, u)`` (forward +
residual in flow/maxflow editorials), the two edges must not collapse onto
one straight ``<line>``. Each bows onto its own side as a quadratic
``<path>`` so the arrows and their ``f/c`` pills read as two distinct
edges. Every non-antiparallel edge stays a byte-identical straight line.
"""

from __future__ import annotations

import re

from scriba.animation.primitives.graph import Graph, _ANTIPARALLEL_CURVE_OFFSET


# --- helpers ---------------------------------------------------------------


def _mk(directed: bool = True, **params) -> Graph:
    """Directed 2-node graph with pinned horizontal positions.

    Positions are pinned so the chord A->B is horizontal (y=150); the
    perpendicular is vertical, making the two bow directions land at
    y>150 and y<150 for easy, orientation-free assertions.
    """
    base = {"nodes": ["A", "B"], "edges": [("A", "B")], "directed": directed}
    base.update(params)
    g = Graph("G", base)
    g.positions = {"A": (100, 150), "B": (300, 150)}
    return g


def _edge_block(svg: str, u: str, v: str) -> str:
    """Return the ``<g data-target="G.edge[(u,v)]">…</g>`` substring.

    Horizontal edges emit no rotate wrapper, so a non-greedy match to the
    first ``</g>`` captures exactly one edge group.
    """
    m = re.search(
        rf'<g data-target="G\.edge\[\({u},{v}\)\]".*?</g>', svg, re.DOTALL
    )
    assert m, f"edge ({u},{v}) group not found"
    return m.group(0)


def _path_d(block: str) -> str:
    m = re.search(r'<path d="([^"]+)"', block)
    assert m, f"no <path d=…> in block: {block[:120]}"
    return m.group(1)


def _quad_ctrl(d: str) -> tuple[float, float]:
    """Extract the (qx, qy) quadratic control point from ``M .. Q qx qy ..``."""
    m = re.search(r"Q\s+([-\d.]+)\s+([-\d.]+)\s", d)
    assert m, f"no quadratic control point in d={d!r}"
    return float(m.group(1)), float(m.group(2))


def _path_midpoint(d: str) -> tuple[float, float]:
    """Geometric midpoint B(0.5) of ``M sx sy Q qx qy ex ey``."""
    nums = [float(x) for x in re.findall(r"[-\d.]+", d)]
    sx, sy, qx, qy, ex, ey = nums[:6]
    return (
        0.25 * sx + 0.5 * qx + 0.25 * ex,
        0.25 * sy + 0.5 * qy + 0.25 * ey,
    )


def _pill_center(block: str) -> tuple[float, float]:
    m = re.search(
        r'<rect class="scriba-graph-pill" x="([-\d.]+)" y="([-\d.]+)"'
        r' width="([-\d.]+)" height="([-\d.]+)"',
        block,
    )
    assert m, f"no weight pill in block: {block[:160]}"
    x, y, w, h = (float(g) for g in m.groups())
    return (x + w / 2, y + h / 2)


# --- pair -> two symmetric curved paths ------------------------------------


class TestAntiparallelPair:
    def test_pair_emits_two_quadratic_paths(self) -> None:
        g = _mk(edges=[("A", "B"), ("B", "A")])
        svg = g.emit_svg()
        ab = _edge_block(svg, "A", "B")
        ba = _edge_block(svg, "B", "A")
        # Both bow into a quadratic <path>; neither collapses to <line>.
        assert " Q " in _path_d(ab)
        assert " Q " in _path_d(ba)
        assert "<line" not in ab
        assert "<line" not in ba

    def test_pair_control_points_symmetric(self) -> None:
        g = _mk(edges=[("A", "B"), ("B", "A")])
        svg = g.emit_svg()
        qx_ab, qy_ab = _quad_ctrl(_path_d(_edge_block(svg, "A", "B")))
        qx_ba, qy_ba = _quad_ctrl(_path_d(_edge_block(svg, "B", "A")))
        # Chord is horizontal at y=150: the two control points straddle it
        # symmetrically (opposite signs, equal magnitude) and share x.
        assert (qy_ab - 150) * (qy_ba - 150) < 0, "must bow to opposite sides"
        assert abs((qy_ab - 150) + (qy_ba - 150)) < 1e-6, "must be symmetric"
        assert abs(qx_ab - qx_ba) < 1e-6

    def test_pair_apex_offset_matches_constant(self) -> None:
        g = _mk(edges=[("A", "B"), ("B", "A")])
        svg = g.emit_svg()
        m_ab = _path_midpoint(_path_d(_edge_block(svg, "A", "B")))
        m_ba = _path_midpoint(_path_d(_edge_block(svg, "B", "A")))
        # Each path midpoint sits ~one apex-offset off the chord centre line.
        assert abs(abs(m_ab[1] - 150) - _ANTIPARALLEL_CURVE_OFFSET) < 3.0
        assert abs(abs(m_ba[1] - 150) - _ANTIPARALLEL_CURVE_OFFSET) < 3.0

    def test_pair_path_midpoints_separated(self) -> None:
        g = _mk(edges=[("A", "B"), ("B", "A")])
        svg = g.emit_svg()
        m_ab = _path_midpoint(_path_d(_edge_block(svg, "A", "B")))
        m_ba = _path_midpoint(_path_d(_edge_block(svg, "B", "A")))
        sep = abs(m_ab[1] - m_ba[1])
        # The whole point: the two arcs read apart, not one line. Probe
        # threshold is >=16px.
        assert sep >= 16.0, f"paths only {sep:.1f}px apart"

    def test_curved_edges_keep_forward_arrowhead(self) -> None:
        g = _mk(edges=[("A", "B"), ("B", "A")])
        svg = g.emit_svg()
        ab = _edge_block(svg, "A", "B")
        ba = _edge_block(svg, "B", "A")
        # Each path self-draws in its own direction, so the shared forward
        # marker suffices — no scriba-arrow-rev needed on the geometry.
        assert 'marker-end="url(#scriba-arrow-fwd)"' in ab
        assert 'marker-end="url(#scriba-arrow-fwd)"' in ba
        assert "scriba-arrow-rev" not in svg

    def test_curved_path_has_fill_none(self) -> None:
        g = _mk(edges=[("A", "B"), ("B", "A")])
        ab = _edge_block(g.emit_svg(), "A", "B")
        # A filled path would paint the area under the arc; strokes only.
        assert 'fill="none"' in ab


# --- labels ride the bow, so f/c pills no longer overlap --------------------


class TestAntiparallelLabels:
    def test_pair_pills_do_not_overlap(self) -> None:
        g = _mk(
            edges=[("A", "B", 5), ("B", "A", 3)],
            show_weights=True,
        )
        svg = g.emit_svg()
        c_ab = _pill_center(_edge_block(svg, "A", "B"))
        c_ba = _pill_center(_edge_block(svg, "B", "A"))
        # Anchored to opposite curve apexes, the two weight pills separate
        # vertically instead of stacking on the shared straight midpoint.
        assert abs(c_ab[1] - c_ba[1]) >= 16.0

    def test_pair_pills_on_opposite_sides(self) -> None:
        g = _mk(
            edges=[("A", "B", 5), ("B", "A", 3)],
            show_weights=True,
        )
        svg = g.emit_svg()
        c_ab = _pill_center(_edge_block(svg, "A", "B"))
        c_ba = _pill_center(_edge_block(svg, "B", "A"))
        assert (c_ab[1] - 150) * (c_ba[1] - 150) < 0


# --- single / non-antiparallel edges stay byte-identical lines --------------


class TestNonAntiparallelUnchanged:
    def test_single_directed_edge_is_line(self) -> None:
        g = _mk(edges=[("A", "B")])
        ab = _edge_block(g.emit_svg(), "A", "B")
        assert "<line" in ab
        assert "<path" not in ab
        assert " Q " not in ab

    def test_directed_chain_no_curves(self) -> None:
        # A->B->C with no reverse edges: every edge stays a straight line.
        g = Graph(
            "G",
            {
                "nodes": ["A", "B", "C"],
                "edges": [("A", "B"), ("B", "C")],
                "directed": True,
            },
        )
        svg = g.emit_svg()
        assert svg.count("<line") == 2
        assert " Q " not in svg

    def test_self_loop_is_not_antiparallel(self) -> None:
        # (A,A) is its own reverse but must never be treated as a pair.
        g = _mk(edges=[("A", "B"), ("A", "A")])
        svg = g.emit_svg()
        ab = _edge_block(svg, "A", "B")
        assert "<line" in ab and " Q " not in ab

    def test_emit_is_deterministic(self) -> None:
        g = _mk(edges=[("A", "B"), ("B", "A")])
        assert g.emit_svg() == g.emit_svg()


# --- undirected graphs: antiparallel is meaningless -------------------------


class TestUndirectedUnchanged:
    def test_undirected_duplicate_edges_stay_lines(self) -> None:
        # Even with both tuples present, an undirected graph never curves.
        g = _mk(directed=False, edges=[("A", "B"), ("B", "A")])
        svg = g.emit_svg()
        assert " Q " not in svg
        assert "<path" not in svg.split("scriba-graph-nodes")[0]
        assert "marker-end" not in svg


# --- mutation: a pair born mid-animation activates the curve -----------------


class TestAntiparallelMutation:
    def test_add_reverse_edge_activates_curve(self) -> None:
        g = _mk(edges=[("A", "B")])
        before = g.emit_svg()
        assert " Q " not in before  # straight until the residual appears

        # Residual edge added at some \step (\apply{G}{add_edge=…}).
        g.apply_command({"add_edge": {"from": "B", "to": "A"}})
        after = g.emit_svg()
        assert " Q " in _path_d(_edge_block(after, "A", "B"))
        assert " Q " in _path_d(_edge_block(after, "B", "A"))
