"""FP-2: content labels share one placement registry per primitive.

Confirmed bug (browser, 11x9px): Plane2D point labels and line labels used
two isolated registries — the point label at (9.05, 9.9) printed straight
through the "y = x" line label because neither list saw the other. Point
labels additionally had NO registry at all (bare <text>, no nudge, no
viewBox clamp).

Structure under test (investigations/fp2-isolated-registries.md):
- ``register_decorations()`` — ONE pure registry for all content labels
  (points then lines, deterministic order), nudge + clamp for both kinds;
  ``_emit_labels`` paints exactly these placements.
- ``resolve_self_content_rects()`` — the same placements exposed as
  obstacles, so \\annotate pills avoid content labels on BOTH the emit and
  measure paths (parity by construction; never an emit-only seed).
- Graph exposes node circles + weight-pill boxes the same way.
"""

from __future__ import annotations

from scriba.animation.primitives.graph import Graph
from scriba.animation.primitives.plane2d import Plane2D


def _fp2_plane() -> Plane2D:
    p = Plane2D("p", {"xrange": [0, 10], "yrange": [0, 10]})
    p.apply_command({"add_line": ("y = x", 1.0, 0.0)})
    p.apply_command({"add_point": (9.05, 9.9, "P(9.05, 9.9)")})
    return p


def _boxes_disjoint(a, b) -> bool:
    ax1, ay1 = a.x - a.width / 2, a.y - a.height / 2
    bx1, by1 = b.x - b.width / 2, b.y - b.height / 2
    ix = min(ax1 + a.width, bx1 + b.width) - max(ax1, bx1)
    iy = min(ay1 + a.height, by1 + b.height) - max(ay1, by1)
    return ix <= 0 or iy <= 0


class TestPlane2DUnifiedRegistry:
    def test_fp2_repro_point_and_line_labels_disjoint(self) -> None:
        recs = _fp2_plane().register_decorations()
        assert len(recs) == 2
        placements = [r["placement"] for r in recs]
        assert _boxes_disjoint(placements[0], placements[1]), (
            f"point label {placements[0]} still overlaps line label "
            f"{placements[1]}"
        )

    def test_registry_is_pure(self) -> None:
        p = _fp2_plane()
        first = [(r["kind"], r["placement"]) for r in p.register_decorations()]
        second = [(r["kind"], r["placement"]) for r in p.register_decorations()]
        assert first == second

    def test_emit_paints_the_registered_placements(self) -> None:
        p = _fp2_plane()
        recs = p.register_decorations()
        svg = p.emit_svg()
        for r in recs:
            # the painted x for both kinds is the rounded placement center
            # (text_anchor=middle) — pin at least one coordinate per record
            assert f'x="{round(r["placement"].x)}"' in svg, r

    def test_content_rects_expose_the_labels(self) -> None:
        p = _fp2_plane()
        rects = p.resolve_self_content_rects()
        assert len(rects) == len(p.register_decorations())
        assert rects == p.resolve_self_content_rects()  # pure


class TestGraphContentRects:
    def test_nodes_and_weight_pills_exposed(self) -> None:
        g = Graph(
            "g",
            {"nodes": ["A", "B", "C"], "edges": [("A", "B", 7), ("B", "C", 3)],
             "show_weights": True},
        )
        rects = g.resolve_self_content_rects()
        # 3 node circles + 2 weight pills
        assert len(rects) == 5
        assert rects == g.resolve_self_content_rects()  # pure

    def test_hidden_node_not_exposed(self) -> None:
        g = Graph(
            "g",
            {"nodes": ["A", "B"], "edges": [("A", "B", 7)], "show_weights": True},
        )
        g.set_state("node[A]", "hidden")
        rects = g.resolve_self_content_rects()
        # hidden node drops, and so does its incident edge's weight pill
        assert len(rects) == 1
