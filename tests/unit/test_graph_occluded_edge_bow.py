"""JZ-18 — edges that pass through a non-endpoint node bow around it.

Hierarchical LR ranks a chain-with-shortcut collinear (1 → 3 → 2): the
rank-skipping edge 1→2 was drawn as a straight center-to-center segment
lying exactly on top of 1→3 + 3→2 — invisible as a distinct object — and
its weight pill anchored at the segment midpoint, i.e. on the intermediate
node (or, post-GEP slide, on the other edge's stroke: every point of the
buried stroke lies on another edge or a node, so no pill-only fix exists).

The fix is geometric, not rank bookkeeping: any drawn edge whose straight
segment passes within ink-contact distance of a visible non-endpoint node
bows onto a quadratic arc (reusing the C2 antiparallel machinery), scaled
so the arc clears the blocker; the weight pill rides the apex.  Straight
edges with no blocker stay byte-identical <line>s.
"""

from __future__ import annotations

import math
import re

from scriba.animation.primitives.graph import (
    Graph,
    _OCCLUSION_CLEARANCE,
)

_R = 20  # default node radius


# --- helpers (mirror test_graph_antiparallel.py) ----------------------------


def _mk_collinear(**params) -> Graph:
    """Directed chain-with-shortcut pinned collinear at y=150.

    A(100) -> M(200) -> B(300), plus the rank-skipping A -> B.  This is the
    cses-1671 geometry: hierarchical LR puts each layer's single node at the
    same y, so the long edge is buried under the two short ones.
    """
    base = {
        "nodes": ["A", "M", "B"],
        "edges": [("A", "B", 6), ("A", "M", 2), ("M", "B", 3)],
        "directed": True,
        "show_weights": True,
    }
    base.update(params)
    g = Graph("G", base)
    g.positions = {"A": (100, 150), "M": (200, 150), "B": (300, 150)}
    return g


def _edge_block(svg: str, u: str, v: str) -> str:
    m = re.search(
        rf'<g data-target="G\.edge\[\({u},{v}\)\]".*?</g>', svg, re.DOTALL
    )
    assert m, f"edge ({u},{v}) group not found"
    return m.group(0)


def _path_d(block: str) -> str:
    m = re.search(r'<path d="([^"]+)"', block)
    assert m, f"no <path d=…> in block: {block[:120]}"
    return m.group(1)


def _quad_points(d: str) -> tuple[float, ...]:
    nums = [float(x) for x in re.findall(r"[-\d.]+", d)]
    assert len(nums) >= 6, f"not a quadratic path: {d!r}"
    return tuple(nums[:6])  # sx, sy, qx, qy, ex, ey


def _min_dist_to_point(d: str, px: float, py: float) -> float:
    sx, sy, qx, qy, ex, ey = _quad_points(d)
    best = float("inf")
    for i in range(101):
        t = i / 100.0
        bx = (1 - t) ** 2 * sx + 2 * (1 - t) * t * qx + t**2 * ex
        by = (1 - t) ** 2 * sy + 2 * (1 - t) * t * qy + t**2 * ey
        best = min(best, math.hypot(bx - px, by - py))
    return best


def _pill_center(block: str) -> tuple[float, float]:
    m = re.search(
        r'<rect class="scriba-graph-pill" x="([-\d.]+)" y="([-\d.]+)"'
        r' width="([-\d.]+)" height="([-\d.]+)"',
        block,
    )
    assert m, f"no weight pill in block: {block[:160]}"
    x, y, w, h = (float(g) for g in m.groups())
    return (x + w / 2, y + h / 2)


# --- the bug: buried rank-skip edge bows into its own visible arc -----------


class TestOccludedEdgeBows:
    def test_skip_edge_emits_quadratic_path(self) -> None:
        svg = _mk_collinear().emit_svg()
        ab = _edge_block(svg, "A", "B")
        assert " Q " in _path_d(ab), "buried edge must bow into a quadratic"
        assert "<line" not in ab

    def test_short_edges_stay_straight_lines(self) -> None:
        svg = _mk_collinear().emit_svg()
        for u, v in (("A", "M"), ("M", "B")):
            block = _edge_block(svg, u, v)
            assert "<line" in block, f"({u},{v}) must stay a straight line"
            assert " Q " not in block

    def test_bow_clears_the_blocking_node(self) -> None:
        svg = _mk_collinear().emit_svg()
        d = _path_d(_edge_block(svg, "A", "B"))
        # The arc keeps daylight between itself and the blocker's ink.
        assert _min_dist_to_point(d, 200.0, 150.0) >= _R + 2.0

    def test_pill_leaves_the_shared_corridor(self) -> None:
        svg = _mk_collinear().emit_svg()
        cx, cy = _pill_center(_edge_block(svg, "A", "B"))
        # Off the blocking node...
        assert math.hypot(cx - 200.0, cy - 150.0) >= _R + 4.0
        # ...and off the straight y=150 corridor both other edges live on.
        assert abs(cy - 150.0) >= 8.0

    def test_bow_is_deterministic(self) -> None:
        g = _mk_collinear()
        assert g.emit_svg() == g.emit_svg()

    def test_undirected_collinear_chain_also_bows(self) -> None:
        svg = _mk_collinear(directed=False).emit_svg()
        assert " Q " in _path_d(_edge_block(svg, "A", "B"))


# --- no blocker, no bow: straight edges stay byte-identical -----------------


class TestNoFalseTriggers:
    def test_triangle_positions_stay_lines(self) -> None:
        g = _mk_collinear()
        g.positions = {"A": (100, 150), "M": (200, 60), "B": (300, 150)}
        svg = g.emit_svg()
        assert " Q " not in svg
        assert svg.count("<line") == 3

    def test_near_miss_outside_ink_contact_stays_line(self) -> None:
        # Blocker r+10 off the chord: visible daylight already exists.
        g = _mk_collinear()
        g.positions = {"A": (100, 150), "M": (200, 150 + _R + 10), "B": (300, 150)}
        svg = g.emit_svg()
        assert " Q " not in svg

    def test_hidden_blocker_does_not_bow(self) -> None:
        g = _mk_collinear()
        g.set_state("node[M]", "hidden")
        svg = g.emit_svg()
        ab = _edge_block(svg, "A", "B")
        assert "<line" in ab and " Q " not in ab

    def test_endpoint_nodes_never_count_as_blockers(self) -> None:
        # Two nodes, one edge: endpoints must not self-trigger.
        g = Graph(
            "G",
            {"nodes": ["A", "B"], "edges": [("A", "B")], "directed": True},
        )
        g.positions = {"A": (100, 150), "B": (300, 150)}
        svg = g.emit_svg()
        assert " Q " not in svg


# --- side selection + extent honesty ----------------------------------------


class TestBowSideAndExtent:
    def test_bow_side_away_from_offset_blocker(self) -> None:
        # Blocker sits slightly BELOW the chord (still ink-contact): the arc
        # must bow UP (away), not into the blocker's side.
        g = _mk_collinear()
        g.positions = {"A": (100, 150), "M": (200, 158), "B": (300, 150)}
        svg = g.emit_svg()
        _sx, _sy, _qx, qy, _ex, _ey = _quad_points(
            _path_d(_edge_block(svg, "A", "B"))
        )
        assert qy < 150.0, "arc must bow away from the blocker's side"

    def test_bounding_box_grows_when_bow_escapes_top(self) -> None:
        # Chord pinned at the canvas top with the blocker just below it:
        # the arc is forced upward past y=0 and the box must reserve it.
        g = _mk_collinear()
        g.positions = {"A": (100, 4), "M": (200, 12), "B": (300, 4)}
        h_with_bow = float(g.bounding_box().height)

        flat = _mk_collinear()
        flat.positions = {"A": (100, 4), "M": (200, 60), "B": (300, 4)}
        h_no_bow = float(flat.bounding_box().height)

        assert h_with_bow > h_no_bow, (
            "an above-frame bow must grow the bounding box"
        )

    def test_bounding_box_grows_when_bow_escapes_bottom(self) -> None:
        g = _mk_collinear()
        # Canvas height default 300: chord at the bottom, blocker just above
        # it -> arc forced downward past the content bottom.
        g.positions = {"A": (100, 296), "M": (200, 288), "B": (300, 296)}
        h_with_bow = float(g.bounding_box().height)

        flat = _mk_collinear()
        flat.positions = {"A": (100, 296), "M": (200, 240), "B": (300, 296)}
        h_no_bow = float(flat.bounding_box().height)

        assert h_with_bow > h_no_bow, (
            "a below-frame bow must grow the bounding box"
        )


# --- antiparallel pairs keep their own (existing) bow ------------------------


class TestAntiparallelPrecedence:
    def test_pair_geometry_unchanged_by_occlusion_pass(self) -> None:
        # A<->B with a collinear blocker between them: the pair bows via the
        # C2 antiparallel rule (fixed 12px apex), not the occlusion rule.
        g = Graph(
            "G",
            {
                "nodes": ["A", "M", "B"],
                "edges": [("A", "B"), ("B", "A"), ("A", "M")],
                "directed": True,
            },
        )
        g.positions = {"A": (100, 150), "M": (200, 150), "B": (300, 150)}
        svg = g.emit_svg()
        for u, v in (("A", "B"), ("B", "A")):
            _sx, _sy, _qx, qy, _ex, _ey = _quad_points(
                _path_d(_edge_block(svg, u, v))
            )
            # C2 control offset is 24px off the chord — occlusion would have
            # pushed it to >= 2*(r + clearance) = 52.
            assert abs(qy - 150.0) < 2 * (_R + _OCCLUSION_CLEARANCE) - 4


# --- obstacle parity: the pill obstacle rides the bowed apex -----------------


class TestObstacleParity:
    def test_self_content_rect_rides_apex(self) -> None:
        g = _mk_collinear()
        rects = g.resolve_self_content_rects()
        # 3 node circles + 3 weight pills.
        pills = [b for b in rects if b.width != 2 * _R or b.height != 2 * _R]
        assert len(pills) == 3
        # The skip edge's pill obstacle must be OFF the y=150 corridor,
        # mirroring the painted apex anchor.
        off_corridor = [
            b for b in pills if abs((b.y + b.height / 2) - 150.0) >= 8.0
        ]
        assert off_corridor, (
            "no pill obstacle rides the bowed apex — measure/emit drift"
        )


# --- review HIGH-1: \recolor-driven antiparallel -> occlusion transition -----


def _quad_hull_min_y(d: str) -> float:
    """Convex-hull lower bound on a quadratic path's min y (sy, qy, ey)."""
    _sx, sy, _qx, qy, _ex, ey = _quad_points(d)
    return min(sy, qy, ey)


class TestAntiparallelToOcclusionTransition:
    """A \\recolor that hides ONE direction of an antiparallel pair drops
    the pair from C2 treatment; the surviving edge may occlusion-bow far
    past the C2 reserve. The prescan must see the transition (it replays
    frame states since the review fix) and reserve the bigger arc."""

    def _scene_html(self, with_recolor: bool) -> str:
        recolor = (
            "\n" r"\recolor{G.edge[(B,A)]}{state=hidden}" if with_recolor else ""
        )
        src = (
            r'\begin{animation}[id="t", label="x"]' "\n"
            r'\shape{G}{Graph}{nodes=["A","M","B","D"], '
            r'edges=[("A","B"),("B","A"),("D","B")], directed=true, '
            r'positions=[("A",0,0),("M",1,0.05),("B",2,0),("D",1,3)]}' "\n"
            r"\step" "\n"
            r"\narrate{pair intact}" "\n"
            r"\step" + recolor + "\n"
            r"\narrate{one direction hidden}" "\n"
            r"\end{animation}"
        )
        from scriba.animation.renderer import AnimationRenderer
        from scriba.core.artifact import Block
        from scriba.core.context import RenderContext

        block = Block(start=0, end=len(src), kind="animation", raw=src)
        ctx = RenderContext(
            resource_resolver=lambda n: n,
            theme="light",
            dark_mode=False,
            metadata={"output_mode": "static"},
            render_inline_tex=None,
        )
        return AnimationRenderer().render_block(block, ctx).html

    def test_survivor_bow_stays_inside_reserved_viewbox(self) -> None:
        html = self._scene_html(with_recolor=True)
        frames = re.findall(
            r'<svg class="scriba-stage-svg" viewBox="0 0 [\d.]+ ([\d.]+)".*?</svg>',
            html,
            re.S,
        )
        assert len(frames) == 2
        # Frame 2 must actually carry the occlusion bow (non-vacuous).
        svg2 = re.findall(
            r'<svg class="scriba-stage-svg".*?</svg>', html, re.S
        )[1]
        ab = _edge_block(svg2, "A", "B")
        d = _path_d(ab)
        assert " Q " in d
        # Cumulative translate of the graph group chain.
        shift = sum(
            float(m.group(1))
            for m in re.finditer(
                r'<g[^>]*transform="translate\([\d.\-]+,\s*([\d.\-]+)\)"', svg2
            )
        )
        vb_h = float(frames[1])
        hull_min = _quad_hull_min_y(d) + shift
        assert hull_min >= -0.01, (
            f"bow hull escapes the viewBox top by {-hull_min:.1f}px "
            "(prescan blind to the state-driven transition)"
        )
        assert vb_h >= shift + _quad_hull_min_y(d) + 1  # sanity: box covers

    def test_recolor_scene_reserves_more_than_static_pair(self) -> None:
        h_static = re.search(
            r'viewBox="0 0 [\d.]+ ([\d.]+)"', self._scene_html(False)
        ).group(1)
        h_recolor = re.search(
            r'viewBox="0 0 [\d.]+ ([\d.]+)"', self._scene_html(True)
        ).group(1)
        assert float(h_recolor) > float(h_static), (
            "hiding one pair direction must grow the reserved viewBox "
            "(occlusion bow of the survivor)"
        )

    def test_bounding_box_is_state_sensitive(self) -> None:
        g = Graph(
            "G",
            {
                "nodes": ["A", "M", "B"],
                "edges": [("A", "B"), ("B", "A")],
                "directed": True,
            },
        )
        g.positions = {"A": (100, 10), "M": (200, 16), "B": (300, 10)}
        assert g._occluded_extents() == (0, 0)  # pair -> C2, no occlusion
        h_pair = float(g.bounding_box().height)
        g.set_state("edge[(B,A)]", "hidden")
        above, _below = g._occluded_extents()
        assert above > 0, "survivor must occlusion-bow past the frame top"
        assert float(g.bounding_box().height) > h_pair


# --- review HIGH-2: near-endpoint blockers get true-profile clearance --------


class TestNearEndpointBlocker:
    def test_true_profile_clears_blocker_at_t_010(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "W", "B"],
             "edges": [("A", "B"), ("A", "W")],
             "directed": True},
        )
        g.positions = {"A": (0, 150), "W": (40, 150), "B": (400, 150)}
        svg = g.emit_svg()
        d = _path_d(_edge_block(svg, "A", "B"))
        # The old clamped formula left ~4px here (arc through the blocker's
        # ink); the true-profile requirement restores real daylight.
        assert _min_dist_to_point(d, 40.0, 150.0) >= _R + 1.0

    def test_pathological_blocker_caps_at_max_ctrl(self) -> None:
        from scriba.animation.primitives.graph import _OCCLUSION_MAX_CTRL

        g = Graph(
            "G",
            {"nodes": ["A", "W", "B"],
             "edges": [("A", "B"), ("A", "W")],
             "directed": True},
        )
        # t≈0.07: demanded ctrl ≈ 200 > cap — must saturate, not bulge.
        g.positions = {"A": (0, 150), "W": (28, 150), "B": (400, 150)}
        bows = g._occluded_bows_from_self_positions()
        assert abs(bows[("A", "B")]) == _OCCLUSION_MAX_CTRL


# --- review MEDIUM: multi-blocker + auto_expand + undirected duplicates ------


class TestMultiBlockerAndModes:
    def test_two_blockers_opposite_sides_both_cleared(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "P", "Q", "B"],
             "edges": [("A", "B"), ("A", "P"), ("Q", "B")],
             "directed": True},
        )
        g.positions = {
            "A": (40, 150), "P": (150, 158), "Q": (250, 144), "B": (360, 150),
        }
        svg = g.emit_svg()
        d = _path_d(_edge_block(svg, "A", "B"))
        assert _min_dist_to_point(d, 150.0, 158.0) >= _R + 1.0
        assert _min_dist_to_point(d, 250.0, 144.0) >= _R + 1.0

    def test_auto_expand_still_bows(self) -> None:
        g = _mk_collinear(auto_expand=True)
        svg = g.emit_svg()
        assert " Q " in _path_d(_edge_block(svg, "A", "B"))

    def test_undirected_duplicate_edges_take_opposite_arcs_on_tie(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "M", "B"],
             "edges": [("A", "B"), ("B", "A")],
             "directed": False},
        )
        g.positions = {"A": (100, 150), "M": (200, 150), "B": (300, 150)}
        svg = g.emit_svg()
        d_ab = _quad_points(_path_d(_edge_block(svg, "A", "B")))
        d_ba = _quad_points(_path_d(_edge_block(svg, "B", "A")))
        # Exact-collinear tie: the negated normal + the >=0 tie-break give
        # the two copies OPPOSITE arcs (they read as two edges, mirroring
        # the antiparallel pair), and each still clears the blocker.
        assert (d_ab[3] - 150.0) * (d_ba[3] - 150.0) < 0
        for d in (d_ab, d_ba):
            path = f"M {d[0]} {d[1]} Q {d[2]} {d[3]} {d[4]} {d[5]}"
            assert _min_dist_to_point(path, 200.0, 150.0) >= _R + 1.0

    def test_detector_skips_self_loop_and_zero_length(self) -> None:
        g = Graph(
            "G",
            {"nodes": ["A", "M", "B"],
             "edges": [("A", "A"), ("A", "B")],
             "directed": True},
        )
        g.positions = {"A": (100, 150), "M": (200, 150), "B": (100, 150)}
        # (A,A) self-loop skipped; (A,B) zero-length (coincident) skipped.
        assert g._occluded_bows_from_self_positions() == {}
