"""JudgeZone #15: top-band caption/pill reservation (base.py ``_top_caption_band``,
``_emit_top_caption``, and the ``arrow_above`` lane consumed by Tree/Forest/Graph's
``emit_svg``).

Mirror image of the report #12 fix (``test_below_band_lanes.py``): that fix made
the *bottom* band's caption consult the caret's real reach. Tree/Forest/Graph
paint their ``label=`` caption ABOVE the crown content instead of below it, and
a ``position=above`` annotation pill on a crown-ish node (one close enough to
the frame's own y=0 that its natural reach pokes above the origin) shares that
same top lane. Neither tenant's placement consulted the other: the caption is
emitted at the outer ``translate(r, r + arrow_above)`` frame, so its absolute
position drifts down by ``arrow_above``; the pill paints inside a *second*,
nested ``translate(0, label_offset)`` group, so ``arrow_above`` cancels out of
its absolute position entirely (it always lands at ``r + label_offset``). When
``arrow_above`` is large enough, the drifting caption overprints the
fixed-position pill.

Root cause and fix are written up in full in
``_bmad-output/implementation-artifacts/investigations/
judgezone-15-topband-caption-investigation.md`` and
``_bmad-output/implementation-artifacts/
spec-fix-judgezone-15-top-band-reservation.md``.
"""

from __future__ import annotations

import re

import pytest

import math

from scriba.animation.primitives.forest import Forest
from scriba.animation.primitives.graph import _GROUP_CORNER_R, _GROUP_PAD, Graph
from scriba.animation.primitives.layout import ASCENDER_RATIO, DESCENDER_RATIO
from scriba.animation.primitives.tree import Tree, _link_bow_apex

_CAPTION_FONT_PX = 11

_LONG_CAPTION = "a caption long enough that it wraps onto a second display line every time"


# ---------------------------------------------------------------------------
# SVG parse helpers
# ---------------------------------------------------------------------------


def _central_band(y: float, font: float = _CAPTION_FONT_PX) -> "tuple[float, float]":
    return (y - font / 2, y + font / 2)


def _alphabetic_band(y: float, font: float = _CAPTION_FONT_PX) -> "tuple[float, float]":
    """Default SVG ``<text>`` baseline (no ``dominant-baseline`` set): ascent
    above *y*, descent below. Matches ``test_below_band_lanes.py``'s helper of
    the same name — the multi-line caption branch is the same code path."""
    return (y - ASCENDER_RATIO * font, y + DESCENDER_RATIO * font)


def _disjoint(a: "tuple[float, float]", b: "tuple[float, float]") -> bool:
    return a[1] <= b[0] or b[1] <= a[0]


def _assert_all_disjoint(named_bands: "dict[str, tuple[float, float]]") -> None:
    items = list(named_bands.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (name_a, band_a), (name_b, band_b) = items[i], items[j]
            assert _disjoint(band_a, band_b), (
                f"{name_a} {band_a} overlaps {name_b} {band_b}"
            )


def _top_group_transforms(svg: str, tag: str) -> "tuple[float, float]":
    """``(outer_ty, inner_ty)`` for the primitive's own ``<g translate(...)>``
    and, if present, the nested ``translate(0, label_offset)`` content group
    that Tree/Forest/Graph open right after the caption. ``inner_ty`` is 0.0
    when no caption is rendered (no nested group is emitted at all)."""
    m = re.search(
        r'<g data-primitive="' + tag + r'"[^>]*transform="translate\(([\d.\-]+),([\d.\-]+)\)"',
        svg,
    )
    assert m, f"{tag} primitive group not found"
    outer_ty = float(m.group(2))
    tail = svg[m.end() : m.end() + 400]
    m2 = re.search(r'<g transform="translate\(([\d.\-]+),([\d.\-]+)\)"', tail)
    inner_ty = float(m2.group(2)) if m2 else 0.0
    return outer_ty, inner_ty


def _caption_bands_abs(svg: str, outer_ty: float) -> "list[tuple[float, float]]":
    """Caption is emitted at the outer level (never inside the nested content
    group), so only ``outer_ty`` composes into its absolute position."""
    m = re.search(r'<text class="scriba-primitive-label"([^>]*)>(.*?)</text>', svg, re.S)
    assert m, "caption <text> not found"
    attrs, body = m.group(1), m.group(2)
    y0 = float(re.search(r'y="([\d.]+)"', attrs).group(1)) + outer_ty
    dys = re.findall(r'<tspan[^>]*\bdy="([\d.\-]+)"', body)
    if not dys:
        return [_central_band(y0)]
    y = y0
    bands = []
    for dy in dys:
        y += float(dy)
        bands.append(_alphabetic_band(y))
    return bands


def _pill_band_abs(
    svg: str, data_annotation_value: str, outer_ty: float, inner_ty: float
) -> "tuple[float, float]":
    """Pill paints inside the nested content group, so both offsets compose."""
    idx = svg.find(f'data-annotation="{data_annotation_value}"')
    assert idx >= 0, f"annotation {data_annotation_value!r} not found"
    chunk = svg[idx : idx + 400]
    y = float(re.search(r'<rect[^>]*\by="([\d.\-]+)"', chunk).group(1))
    h = float(re.search(r'<rect[^>]*\bheight="([\d.\-]+)"', chunk).group(1))
    ty = outer_ty + inner_ty
    return (y + ty, y + h + ty)


# ---------------------------------------------------------------------------
# Tree: the reported shape — caption + position=above pill on the root.
# ---------------------------------------------------------------------------


class TestTreeTopBandDisjoint:
    def _tree(self, *, label: str) -> Tree:
        t = Tree(
            "t",
            {
                "root": "1",
                "nodes": ["1", "2", "3"],
                "edges": [("1", "2"), ("1", "3")],
                "label": label,
            },
        )
        return t

    def test_pill_above_root_and_caption_disjoint(self) -> None:
        t = self._tree(label="a caption line on top")
        t.set_annotations(
            [{"target": "t.node[1]", "label": "pill above root", "position": "above", "color": "good"}]
        )
        _ = t.bounding_box()
        svg = t.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "tree")
        bands = {f"caption_line_{i}": b for i, b in enumerate(_caption_bands_abs(svg, outer_ty))}
        bands["above_pill"] = _pill_band_abs(
            svg, "t.node[1]-position-above", outer_ty, inner_ty
        )
        _assert_all_disjoint(bands)

    def test_wrapped_caption_still_disjoint_from_pill(self) -> None:
        """Long caption stress: ``_top_caption_band`` grows past the historical
        28px single-line floor. The fix must hold for any label_offset, not
        just the constant's default value."""
        t = self._tree(label=_LONG_CAPTION)
        t.set_annotations(
            [{"target": "t.node[1]", "label": "pill above root", "position": "above", "color": "good"}]
        )
        _ = t.bounding_box()
        svg = t.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "tree")
        bands = {f"caption_line_{i}": b for i, b in enumerate(_caption_bands_abs(svg, outer_ty))}
        assert len(bands) >= 2, "expected the long caption to wrap"
        bands["above_pill"] = _pill_band_abs(
            svg, "t.node[1]-position-above", outer_ty, inner_ty
        )
        _assert_all_disjoint(bands)

    def test_deep_node_pill_no_reservation_needed(self) -> None:
        """Control: a pill on a non-crown (leaf) node never reaches above
        y=0, so ``arrow_above`` is 0 and there is nothing to protect the
        caption from — this must stay disjoint before AND after the fix."""
        t = self._tree(label="a caption line on top")
        t.set_annotations(
            [{"target": "t.node[2]", "label": "pill on a leaf", "position": "above", "color": "good"}]
        )
        assert t.annotation_height_above() == 0
        _ = t.bounding_box()
        svg = t.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "tree")
        bands = {f"caption_line_{i}": b for i, b in enumerate(_caption_bands_abs(svg, outer_ty))}
        bands["above_pill"] = _pill_band_abs(
            svg, "t.node[2]-position-above", outer_ty, inner_ty
        )
        _assert_all_disjoint(bands)

    def test_no_caption_pill_path_byte_stable(self) -> None:
        """Byte-stability guard: no ``label=`` -> no nested content group at
        all, and the outer ``ty`` stays exactly ``r + arrow_above`` (the
        historical formula), regardless of the fix."""
        t = Tree(
            "t",
            {"root": "1", "nodes": ["1", "2", "3"], "edges": [("1", "2"), ("1", "3")]},
        )
        t.set_annotations(
            [{"target": "t.node[1]", "label": "pill above root", "position": "above", "color": "good"}]
        )
        arrow_above = t._reserved_arrow_above()
        assert arrow_above > 0
        _ = t.bounding_box()
        svg = t.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "tree")
        assert outer_ty == t._node_radius + arrow_above
        assert inner_ty == 0.0

    def test_caption_no_pill_path_matches_historical_formula(self) -> None:
        """Byte-stability guard: with no annotation, ``arrow_above == 0``, so
        the new ``outer_ty == r`` formula and the historical
        ``outer_ty == r + arrow_above`` formula coincide exactly — a
        caption-only frame is unaffected by the fix."""
        t = self._tree(label="a caption line on top")
        assert t._reserved_arrow_above() == 0
        _ = t.bounding_box()
        svg = t.emit_svg()
        outer_ty, _inner_ty = _top_group_transforms(svg, "tree")
        assert outer_ty == t._node_radius


# ---------------------------------------------------------------------------
# Forest: same shared ``_top_caption_band`` / ``_emit_top_caption`` path,
# different outer-transform shape (no separate ``+r`` term).
# ---------------------------------------------------------------------------


class TestForestTopBandDisjoint:
    def _forest(self, *, label: str) -> Forest:
        return Forest(
            "f",
            {"nodes": ["1", "2", "3"], "edges": [("1", "2"), ("1", "3")], "label": label},
        )

    def test_pill_above_root_and_caption_disjoint(self) -> None:
        f = self._forest(label="forest caption on top")
        f.set_annotations(
            [
                {
                    "target": "f.node[1]",
                    "label": "pill above forest root",
                    "position": "above",
                    "color": "good",
                }
            ]
        )
        assert f.annotation_height_above() > 0
        _ = f.bounding_box()
        svg = f.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "forest")
        bands = {f"caption_line_{i}": b for i, b in enumerate(_caption_bands_abs(svg, outer_ty))}
        bands["above_pill"] = _pill_band_abs(
            svg, "f.node[1]-position-above", outer_ty, inner_ty
        )
        _assert_all_disjoint(bands)

    def test_no_caption_pill_path_byte_stable(self) -> None:
        f = Forest("f", {"nodes": ["1", "2", "3"], "edges": [("1", "2"), ("1", "3")]})
        f.set_annotations(
            [
                {
                    "target": "f.node[1]",
                    "label": "pill above forest root",
                    "position": "above",
                    "color": "good",
                }
            ]
        )
        arrow_above = f._reserved_arrow_above()
        assert arrow_above > 0
        _ = f.bounding_box()
        svg = f.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "forest")
        assert outer_ty == arrow_above
        assert inner_ty == 0.0

    def test_caption_no_pill_path_matches_historical_formula(self) -> None:
        f = self._forest(label="forest caption on top")
        assert f._reserved_arrow_above() == 0
        _ = f.bounding_box()
        svg = f.emit_svg()
        outer_ty, _inner_ty = _top_group_transforms(svg, "forest")
        assert outer_ty == 0.0


# ---------------------------------------------------------------------------
# Graph: same shared path, ``ty = r + arrow_above`` like Tree. Default
# force-directed layout rarely puts a node at the crown, so this pins a
# node's author position near the frame's own origin.
# ---------------------------------------------------------------------------


class TestGraphTopBandDisjoint:
    def _graph(self, *, label: str) -> Graph:
        return Graph(
            "g",
            {
                "nodes": ["a", "b"],
                "edges": [("a", "b")],
                "label": label,
                "positions": [("a", 0, 0), ("b", 1, 1)],
            },
        )

    def test_pill_above_top_node_and_caption_disjoint(self) -> None:
        g = self._graph(label="graph caption on top")
        g.set_annotations(
            [{"target": "g.node[a]", "label": "pill above root", "position": "above", "color": "good"}]
        )
        assert g.annotation_height_above() > 0
        _ = g.bounding_box()
        svg = g.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "graph")
        bands = {f"caption_line_{i}": b for i, b in enumerate(_caption_bands_abs(svg, outer_ty))}
        bands["above_pill"] = _pill_band_abs(
            svg, "g.node[a]-position-above", outer_ty, inner_ty
        )
        _assert_all_disjoint(bands)

    def test_no_caption_pill_path_byte_stable(self) -> None:
        g = Graph(
            "g",
            {"nodes": ["a", "b"], "edges": [("a", "b")], "positions": [("a", 0, 0), ("b", 1, 1)]},
        )
        g.set_annotations(
            [{"target": "g.node[a]", "label": "pill above root", "position": "above", "color": "good"}]
        )
        arrow_above = g._reserved_arrow_above()
        assert arrow_above > 0
        _ = g.bounding_box()
        svg = g.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "graph")
        assert outer_ty == g._node_radius + arrow_above
        assert inner_ty == 0.0

    def test_caption_no_pill_path_matches_historical_formula(self) -> None:
        g = self._graph(label="graph caption on top")
        assert g._reserved_arrow_above() == 0
        _ = g.bounding_box()
        svg = g.emit_svg()
        outer_ty, _inner_ty = _top_group_transforms(svg, "graph")
        assert outer_ty == g._node_radius


# ---------------------------------------------------------------------------
# Graph \group hulls: a second top-band tenant independent of \annotate.
# annotation_height_above() (and therefore _reserved_arrow_above()) has no
# visibility into \group hulls, so a hull/title-pill near the frame's crown
# was not counted in the top-band reservation at all (JudgeZone sweep,
# out-of-scope observation #2 in the JZ-15 investigation doc).
# ---------------------------------------------------------------------------


class TestGraphGroupTopBandDisjoint:
    def _graph(self, *, label: "str | None") -> Graph:
        return Graph(
            "g",
            {
                "nodes": ["a", "b"],
                "edges": [("a", "b")],
                "label": label,
                "positions": [("a", 0, 0), ("b", 1, 1)],
            },
        )

    def test_group_label_and_caption_disjoint(self) -> None:
        g = self._graph(label="graph caption on top")
        g.set_groups(
            [{"target": "g", "id": "c1", "nodes": ["a"], "color": "info", "label": "component X"}]
        )
        _ = g.bounding_box()
        svg = g.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "graph")
        bands = {f"caption_line_{i}": b for i, b in enumerate(_caption_bands_abs(svg, outer_ty))}
        bands["group_label"] = _pill_band_abs(
            svg, "g.group[c1]-solo-label", outer_ty, inner_ty
        )
        _assert_all_disjoint(bands)

    def test_group_label_no_caption_stays_in_viewbox(self) -> None:
        g = self._graph(label=None)
        g.set_groups(
            [{"target": "g", "id": "c1", "nodes": ["a"], "color": "info", "label": "component X"}]
        )
        _ = g.bounding_box()
        svg = g.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "graph")
        top, _bottom = _pill_band_abs(svg, "g.group[c1]-solo-label", outer_ty, inner_ty)
        assert top >= 0, f"group label pill paints above the viewBox (top={top})"

    def test_group_extent_above_unlabeled_hull(self) -> None:
        """Direct check on the pure reservation function: an unlabeled
        group whose hull alone reaches above y=0 must still be counted
        (the hull has no pill, so the SVG has no plain-rect proxy to parse
        independently — this is a white-box check on the same staticmethod
        the fix consumes, not a from-scratch re-derivation)."""
        g = self._graph(label=None)
        g.set_groups([{"target": "g", "id": "c1", "nodes": ["a"], "color": "info"}])
        r = g._node_radius
        centers = [g.positions["a"]]
        inflate = float(r) + _GROUP_PAD
        _d, (_minx, miny, _maxx, _maxy) = Graph._group_hull_path(
            centers, inflate, _GROUP_CORNER_R
        )
        assert miny < 0, "fixture must reach above y=0 to be meaningful"
        assert g._group_extent_above() == int(math.ceil(-miny))

    def test_group_extent_above_zero_without_groups(self) -> None:
        g = self._graph(label="caption")
        assert g._group_extent_above() == 0


# ---------------------------------------------------------------------------
# Tree second-class \link (add_link/remove_link bow arcs): a third top-band
# tenant independent of \annotate, same shape as the \group finding above.
# annotation_height_above()/_reserved_arrow_above() has no visibility into
# self.links -- a wide enough pair of linked siblings bows upward past the
# frame's own crown (JudgeZone sweep, work item 2).
# ---------------------------------------------------------------------------


class TestTreeLinkTopBandDisjoint:
    def _wide_tree(self, *, label: "str | None", n: int = 40) -> Tree:
        nodes = ["A"] + [f"c{i}" for i in range(n)]
        edges = [("A", f"c{i}") for i in range(n)]
        return Tree(
            "t",
            {"root": "A", "nodes": nodes, "edges": edges, "label": label},
        )

    def _link_path_apex_y(self, svg: str) -> float:
        m = re.search(r'class="scriba-tree-link[^"]*"[^>]*>\s*<path d="([^"]+)"', svg)
        assert m, "tree link path missing from svg"
        m2 = re.match(r"M[\d.\-]+,[\d.\-]+\s*Q([\d.\-]+),([\d.\-]+)", m.group(1))
        assert m2, f"unexpected path syntax: {m.group(1)}"
        return float(m2.group(2))

    def test_link_bow_and_caption_disjoint(self) -> None:
        """The reported shape: a wide tree's link bows upward far enough to
        reach the crown, with a caption present. Direction (rightmost ->
        leftmost) is chosen so the bow's perpendicular points up; the
        opposite order bows down (see test_bounding_box_identical in
        test_tree_links_charedges.py, which pins the safe direction)."""
        t = self._wide_tree(label="Tree Caption")
        xs = sorted((t.positions[n][0], n) for n in t.nodes if n != "A")
        leftmost, rightmost = xs[0][1], xs[-1][1]
        t._add_link_internal(rightmost, leftmost)
        assert t._reserved_arrow_above() == 0, "no \\annotate in this probe"
        assert t._link_extent_above() > 0, "fixture must reach above y=0 to be meaningful"
        _ = t.bounding_box()
        svg = t.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "tree")
        bands = {f"caption_line_{i}": b for i, b in enumerate(_caption_bands_abs(svg, outer_ty))}
        apex_local = self._link_path_apex_y(svg)
        ty = outer_ty + inner_ty
        bands["link_bow_apex"] = (apex_local + ty, apex_local + ty)
        _assert_all_disjoint(bands)

    def test_link_bow_no_caption_stays_in_viewbox(self) -> None:
        t = self._wide_tree(label=None)
        xs = sorted((t.positions[n][0], n) for n in t.nodes if n != "A")
        leftmost, rightmost = xs[0][1], xs[-1][1]
        t._add_link_internal(rightmost, leftmost)
        _ = t.bounding_box()
        svg = t.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "tree")
        apex_local = self._link_path_apex_y(svg)
        apex_abs = apex_local + outer_ty + inner_ty
        assert apex_abs >= 0, f"link bow paints above the viewBox (apex={apex_abs})"

    def test_link_extent_above_matches_bow_apex(self) -> None:
        """Direct check on the pure reservation function: a link whose bow
        alone reaches above y=0 must still be counted (white-box check on
        the same method the fix consumes, mirroring
        test_group_extent_above_unlabeled_hull)."""
        t = self._wide_tree(label=None)
        xs = sorted((t.positions[n][0], n) for n in t.nodes if n != "A")
        leftmost, rightmost = xs[0][1], xs[-1][1]
        t._add_link_internal(rightmost, leftmost)
        x1, y1 = t.positions[rightmost]
        x2, y2 = t.positions[leftmost]
        cx, cy = _link_bow_apex(x1, y1, x2, y2)
        assert cy < 0, "fixture must reach above y=0 to be meaningful"
        assert t._link_extent_above() == int(math.ceil(-cy))

    def test_link_extent_above_zero_without_links(self) -> None:
        t = self._wide_tree(label="caption")
        assert t._link_extent_above() == 0

    def test_link_extent_above_zero_when_bow_points_down(self) -> None:
        """Pin the safe direction used by test_bounding_box_identical in
        test_tree_links_charedges.py: linking ("1", "2") on the small
        4-node std tree bows downward, so the reservation stays 0 and
        bounding_box() is provably unaffected by that existing fixture."""
        t = Tree(
            "T",
            {
                "root": "0",
                "nodes": ["0", "1", "2", "3"],
                "edges": [("0", "1"), ("0", "2"), ("1", "3")],
                "links": [("1", "2")],
            },
        )
        assert t._link_extent_above() == 0


# ---------------------------------------------------------------------------
# Graph antiparallel edges (C2: directed (u,v) whose reverse (v,u) is also
# drawn, bowed onto opposite arcs): a fourth top-band tenant independent of
# \annotate, same shape as \group/Tree-link above -- found during the sweep
# but analytically bounded safe (see the class docstring for the margin
# derivation), fixed anyway for consistency with the other two tenants and
# to make the margin an enforced reservation instead of a coincidence
# between unrelated constants.
# ---------------------------------------------------------------------------


class TestGraphAntiparallelTopBandDisjoint:
    """Unlike \\group and Tree's \\link (both confirmed-reachable JudgeZone
    sweep bugs), the antiparallel bow's reach above y=0 is bounded by fixed
    constants that never overlap the caption lane's own slack: ``ctrl_off =
    2 * _ANTIPARALLEL_CURVE_OFFSET = 24`` (fixed, not distance-scaled, unlike
    Tree's link bow) vs. ``_PADDING = 20`` (an unconditional floor on every
    node's y -- every layout mode, including the manual-position clamp,
    bounds to ``[_PADDING, ...]``), giving a worst-case exceedance of
    ``ceil(24 - 20) = 4px`` against the caption lane's ~6.5px slack at its
    own floor (``_TOP_CAPTION_BAND = 28``). Fixed anyway
    (``Graph._antiparallel_extent_above``) so that margin is an explicit,
    code-enforced reservation rather than a coincidence between constants
    that could silently invert if any of them is retuned later."""

    def _dense_graph(self, *, label: "str | None") -> Graph:
        """13 nodes forces the density-derived node radius down to its
        _NODE_MIN_RADIUS=12 floor -- the smallest legal radius. Filler
        nodes/edges sit away from the top row so they don't disturb the
        a/b antiparallel pair's topmost position."""
        fillers = [(f"d{i}", 0.1 * i, 2.0) for i in range(10)]
        filler_edges = [(f"d{i}", f"d{i + 1}") for i in range(9)]
        return Graph(
            "g",
            {
                "nodes": ["a", "b", "c"] + [n for n, _, _ in fillers],
                "edges": [("a", "b"), ("b", "a"), ("b", "c")] + filler_edges,
                "directed": True,
                "label": label,
                "positions": [("a", 0, 0), ("b", 1, 0), ("c", 0.5, 1)] + fillers,
            },
        )

    def _worst_bow_apex_abs(self, svg: str, outer_ty: float, inner_ty: float) -> float:
        """Worst (topmost) among ALL bowed edge paths -- an antiparallel
        pair bows its two members to OPPOSITE sides, so only one of them is
        the upward ("worst") one; a single match would grab whichever
        sorts first in the SVG regardless of bow direction. Graph emits
        space-separated path syntax (``M x y Q cx cy ex ey``), unlike
        Tree's comma-separated ``_link_geometry`` format."""
        matches = re.findall(
            r'data-target="(g\.edge\[[^\]]*\])"[^>]*>\s*<path d="([^"]+)"', svg
        )
        assert matches, "antiparallel edge path missing from svg"
        ty = outer_ty + inner_ty
        worst = None
        for _target, d in matches:
            m = re.match(r"M\s*[\d.\-]+\s+[\d.\-]+\s*Q\s*([\d.\-]+)\s+([\d.\-]+)", d)
            assert m, f"unexpected path syntax: {d}"
            abs_y = float(m.group(2)) + ty
            if worst is None or abs_y < worst:
                worst = abs_y
        assert worst is not None
        return worst

    def test_antiparallel_bow_and_caption_disjoint_at_min_radius(self) -> None:
        g = self._dense_graph(label="Graph Caption")
        assert g._node_radius == 12, "fixture must hit the density floor to be meaningful"
        assert g._reserved_arrow_above() == 0, "no \\annotate in this probe"
        assert g._group_extent_above() == 0, "no \\group in this probe"
        assert g._antiparallel_extent_above() > 0, "fixture must reach above y=0"
        _ = g.bounding_box()
        svg = g.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "graph")
        bands = {f"caption_line_{i}": b for i, b in enumerate(_caption_bands_abs(svg, outer_ty))}
        apex_abs = self._worst_bow_apex_abs(svg, outer_ty, inner_ty)
        bands["antiparallel_bow_apex"] = (apex_abs, apex_abs)
        _assert_all_disjoint(bands)

    def test_antiparallel_bow_no_caption_stays_in_viewbox(self) -> None:
        g = self._dense_graph(label=None)
        _ = g.bounding_box()
        svg = g.emit_svg()
        outer_ty, inner_ty = _top_group_transforms(svg, "graph")
        apex_abs = self._worst_bow_apex_abs(svg, outer_ty, inner_ty)
        assert apex_abs >= 0, f"antiparallel bow paints above the viewBox (apex={apex_abs})"

    def test_antiparallel_extent_above_matches_bow_geometry(self) -> None:
        """Direct check on the pure reservation function, mirroring
        test_group_extent_above_unlabeled_hull / test_link_extent_above_matches_bow_apex."""
        g = self._dense_graph(label=None)
        antiparallel = g._antiparallel_edges(set())
        assert antiparallel, "fixture must have a reciprocal edge pair"
        worst = 0.0
        for u, v in antiparallel:
            cx1, cy1 = g.positions[u]
            cx2, cy2 = g.positions[v]
            _qx, qy, *_rest = Graph._antiparallel_curve(
                float(cx1), float(cy1), float(cx2), float(cy2), g._node_radius
            )
            worst = min(worst, qy)
        assert worst < 0, "fixture must reach above y=0 to be meaningful"
        assert g._antiparallel_extent_above() == int(math.ceil(-worst))

    def test_antiparallel_extent_above_zero_without_reciprocal_edges(self) -> None:
        g = Graph(
            "g",
            {
                "nodes": ["a", "b"],
                "edges": [("a", "b")],
                "directed": True,
                "label": "caption",
                "positions": [("a", 0, 0), ("b", 1, 1)],
            },
        )
        assert g._antiparallel_extent_above() == 0

    def test_antiparallel_extent_above_zero_when_undirected(self) -> None:
        g = Graph(
            "g",
            {
                "nodes": ["a", "b"],
                "edges": [("a", "b")],
                "positions": [("a", 0, 0), ("b", 1, 1)],
            },
        )
        assert g._antiparallel_extent_above() == 0
