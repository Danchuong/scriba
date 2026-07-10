"""Shared-obstacle model — ``\\group`` title pill dodges a hull-corner node.

The ``\\group`` overlay-hull title pill was emitted directly by
``_emit_group_hulls`` (graph.py) at a fixed corner (``prx=minx``,
``pry=miny-ph-4``), bypassing the R-33/R-34 smart-label placer. A Graph node
standing at that hull corner sat *under* the pill (16.4 px / 41 % overlap,
measured pre-fix on the seed-2 layout), overdrawing the label.

Fix (investigations/design-shared-obstacle.md, mechanism a): route the pill
through the shared ``_place_pill`` scorer with the Graph node circles / edge
pills (``resolve_self_content_rects``) as SHOULD obstacles, so the pill slides
off the corner node. A group whose corner is already clear keeps its exact
natural seat — the placer is a no-op — so its markup stays byte-identical.

Bands: an SVG ``<circle>`` covers ``[cy-r, cy+r]``; a pill ``<rect>`` covers
``[y, y+h]``. A collision needs overlap on BOTH axes.
"""

from __future__ import annotations

import re

from scriba.animation.primitives.graph import Graph


def _label_rect(svg: str) -> tuple[float, float, float, float]:
    m = re.search(r'class="scriba-group-label"[^>]*>(.*?)</g>', svg, re.S)
    assert m, "group label pill missing from svg"
    r = re.search(
        r'<rect x="([\d.-]+)" y="([\d.-]+)" width="(\d+)" height="(\d+)"', m.group(1)
    )
    assert r, "group label rect missing"
    return tuple(float(v) for v in r.groups())  # type: ignore[return-value]


def _node_circles(svg: str) -> list[tuple[float, float, float]]:
    return [
        (float(a), float(b), float(c))
        for a, b, c in re.findall(
            r'<circle cx="([\d.-]+)" cy="([\d.-]+)" r="([\d.]+)"', svg
        )
    ]


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _worst_node_overlap(svg: str) -> float:
    """Largest min-axis pill∩node overlap — >0 means the pill covers a node."""
    rx, ry, rw, rh = _label_rect(svg)
    worst = 0.0
    for cx, cy, cr in _node_circles(svg):
        oy = _overlap(ry, ry + rh, cy - cr, cy + cr)
        ox = _overlap(rx, rx + rw, cx - cr, cx + cr)
        if oy > 0 and ox > 0:
            worst = max(worst, min(oy, ox))
    return worst


def _graph(seed: int) -> Graph:
    return Graph(
        "G",
        {
            "nodes": ["1", "2", "3", "4", "5"],
            "edges": [("1", "2", 1), ("2", "3", 1), ("3", "4", 1), ("4", "5", 1)],
            "layout": "stable",
            "layout_seed": seed,
            "directed": False,
        },
    )


class TestGroupLabelDodgesCornerNode:
    def test_label_dodges_corner_node(self) -> None:
        """Seed-2: the title pill's natural corner has node-2 under it
        (16.4 px pre-fix). After the fix the pill band clears every node."""
        g = _graph(2)
        g.set_groups(
            [{"target": "G", "id": "c1", "nodes": ["1", "2", "3"],
              "color": "info", "label": "component X"}]
        )
        svg = g.emit_svg()
        assert _worst_node_overlap(svg) == 0.0, (
            "group title pill still overlaps a node "
            f"(worst={_worst_node_overlap(svg)}) — placer did not dodge"
        )


class TestGroupLabelByteIdentityWhenClear:
    """A group whose natural corner is clear (seed-1: no node under the pill)
    keeps its exact pre-placer markup — the scorer is a no-op."""

    _PRE_FIX = (
        '<g class="scriba-group-label" data-annotation="G.group[c1]-solo-label">'
        '<rect x="61.9" y="34.1" width="87" height="19" rx="4" fill="white"'
        ' fill-opacity="0.92" stroke="#506882" stroke-width="0.5"'
        ' stroke-opacity="0.4"/>'
        '<text class="scriba-group-label-text" x="105.4" y="43.6" fill="#506882"'
        ' style="text-anchor:middle;dominant-baseline:central">component X</text>'
        "</g>"
    )

    def test_clear_corner_byte_identical(self) -> None:
        g = _graph(1)
        assert _worst_node_overlap_precondition(g) == 0.0
        g2 = _graph(1)
        g2.set_groups(
            [{"target": "G", "id": "c1", "nodes": ["1", "2", "3"],
              "color": "info", "label": "component X"}]
        )
        svg = g2.emit_svg()
        m = re.search(r'(<g class="scriba-group-label".*?</g>)', svg, re.S)
        assert m, "group label missing"
        assert m.group(1) == self._PRE_FIX


def _worst_node_overlap_precondition(g: Graph) -> float:
    g.set_groups(
        [{"target": "G", "id": "c1", "nodes": ["1", "2", "3"],
          "color": "info", "label": "component X"}]
    )
    return _worst_node_overlap(g.emit_svg())
