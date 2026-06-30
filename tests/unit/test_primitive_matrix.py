"""Tests for the Matrix / Heatmap primitive.

Covers declaration, colorscale, selectors, SVG output, value display,
vmin/vmax, bounding box, and the Heatmap alias.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.primitives.matrix import (
    MatrixPrimitive,
    interpolate_color,
    VIRIDIS,
    _CELL_GAP as _MX_GAP,
)
from scriba.core.errors import ValidationError


def _annotation_rects(svg: str) -> list[dict[str, float]]:
    """Parse every annotation pill ``<rect>`` into a numeric attr dict.

    Robust to attribute order and to look-alike attrs (``rx``/``stroke-width``):
    each attribute is parsed by its full name, so ``width`` is the pill width,
    never ``stroke-width``.
    """
    rects: list[dict[str, float]] = []
    for block in re.findall(r'<g class="scriba-annotation.*?</g>', svg, re.S):
        for rect in re.findall(r"<rect\b[^>]*/>", block):
            attrs = dict(re.findall(r'([a-zA-Z][\w-]*)="([^"]*)"', rect))
            try:
                rects.append({k: float(attrs[k]) for k in ("x", "y", "width", "height")})
            except (KeyError, ValueError):
                pass
    return rects


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_basic_declaration(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 3, "cols": 4,
            "data": [float(i) for i in range(12)],
        })
        assert isinstance(inst, MatrixPrimitive)
        assert inst.rows == 3
        assert inst.cols == 4
        assert inst.name == "m"
        assert inst.primitive_type == "matrix"

    def test_2d_data(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 2, "cols": 2,
            "data": [[0.1, 0.2], [0.3, 0.4]],
        })
        assert inst.data == [[0.1, 0.2], [0.3, 0.4]]

    def test_flat_data_reshaping(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 2, "cols": 3,
            "data": [1, 2, 3, 4, 5, 6],
        })
        assert inst.data == [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]

    def test_missing_rows_raises(self) -> None:
        # v0.5.1: E1420 (Matrix missing rows/cols)
        with pytest.raises(ValidationError, match="E1420"):
            MatrixPrimitive("m", {"cols": 3, "data": [1, 2, 3]})

    def test_missing_cols_raises(self) -> None:
        with pytest.raises(ValidationError, match="E1420"):
            MatrixPrimitive("m", {"rows": 3, "data": [1, 2, 3]})

    def test_data_length_mismatch(self) -> None:
        # v0.5.1: E1422 (Matrix data length mismatch)
        with pytest.raises(ValidationError, match="E1422"):
            MatrixPrimitive("m", {"rows": 2, "cols": 2, "data": [1, 2, 3]})

    def test_zero_rows_raises_e1421(self) -> None:
        with pytest.raises(ValidationError, match="E1421"):
            MatrixPrimitive("m", {"rows": 0, "cols": 4})

    def test_zero_cols_raises_e1421(self) -> None:
        with pytest.raises(ValidationError, match="E1421"):
            MatrixPrimitive("m", {"rows": 4, "cols": 0})

    def test_cell_count_limit_raises_e1425(self) -> None:
        """A 251x1000 matrix (251,000 cells) exceeds the 250,000 limit."""
        with pytest.raises(ValidationError, match="E1425") as exc_info:
            MatrixPrimitive("m", {"rows": 251, "cols": 1000})
        # Error message must name the actual count and the 250000 limit.
        msg = str(exc_info.value)
        assert "251000" in msg
        assert "250000" in msg

    def test_cell_count_at_limit_ok(self) -> None:
        """Exactly 250,000 cells is still permitted."""
        inst = MatrixPrimitive("m", {"rows": 500, "cols": 500})
        assert inst.rows == 500 and inst.cols == 500

    def test_empty_data_fills_zeros(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 2, "cols": 2})
        assert inst.data == [[0.0, 0.0], [0.0, 0.0]]

    def test_default_colorscale(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 1, "cols": 1})
        assert inst.colorscale == "viridis"

    def test_unknown_colorscale_raises_e1421(self) -> None:
        # Unknown colorscale must fail loud instead of silently
        # falling back to viridis (audit B4).
        with pytest.raises(ValidationError, match="E1421"):
            MatrixPrimitive("m", {"rows": 1, "cols": 1, "colorscale": "plasma"})

    def test_show_values_default_false(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 1, "cols": 1})
        assert inst.show_values is False


# ---------------------------------------------------------------------------
# Colorscale interpolation
# ---------------------------------------------------------------------------


class TestColorscale:
    def test_t_zero_gives_first_stop(self) -> None:
        color = interpolate_color(0.0, VIRIDIS)
        assert color == "rgb(68,1,84)"

    def test_t_one_gives_last_stop(self) -> None:
        color = interpolate_color(1.0, VIRIDIS)
        assert color == "rgb(253,231,37)"

    def test_t_half_gives_teal(self) -> None:
        color = interpolate_color(0.5, VIRIDIS)
        assert color == "rgb(33,145,140)"

    def test_clamp_below_zero(self) -> None:
        color = interpolate_color(-0.5, VIRIDIS)
        assert color == "rgb(68,1,84)"

    def test_clamp_above_one(self) -> None:
        color = interpolate_color(1.5, VIRIDIS)
        assert color == "rgb(253,231,37)"

    def test_midpoint_interpolation(self) -> None:
        # t=0.125 is midpoint between stop 0 (0.0) and stop 1 (0.25)
        color = interpolate_color(0.125, VIRIDIS)
        assert color.startswith("rgb(")


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestSelectors:
    def test_cell_valid(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 3, "cols": 4})
        assert inst.validate_selector("cell[0][0]") is True
        assert inst.validate_selector("cell[2][3]") is True

    def test_cell_out_of_range(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 3, "cols": 4})
        assert inst.validate_selector("cell[3][0]") is False
        assert inst.validate_selector("cell[0][4]") is False

    def test_all_valid(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 2, "cols": 2})
        assert inst.validate_selector("all") is True

    def test_unknown_selector(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 2, "cols": 2})
        assert inst.validate_selector("nonsense") is False

    def test_addressable_parts(self) -> None:
        inst = MatrixPrimitive("m", {"rows": 2, "cols": 2})
        parts = inst.addressable_parts()
        assert "cell[0][0]" in parts
        assert "cell[0][1]" in parts
        assert "cell[1][0]" in parts
        assert "cell[1][1]" in parts
        assert "all" in parts
        assert len(parts) == 5  # 4 cells + all


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 2, "cols": 2,
            "data": [0.0, 0.5, 0.5, 1.0],
        })
        svg = inst.emit_svg()
        assert 'data-primitive="matrix"' in svg
        assert 'data-shape="m"' in svg
        assert 'data-target="m.cell[0][0]"' in svg
        assert 'data-target="m.cell[1][1]"' in svg

    def test_colorscale_applied(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 1, "cols": 2,
            "data": [0.0, 1.0],
        })
        svg = inst.emit_svg()
        # Should contain rgb fill colors from viridis
        assert "rgb(" in svg

    def test_show_values(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 1, "cols": 2,
            "data": [0.5, 1.0],
            "show_values": True,
        })
        svg = inst.emit_svg()
        assert ">0.5</text>" in svg
        assert ">1</text>" in svg

    def test_state_applied_via_stroke(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 2, "cols": 2,
            "data": [0, 0.5, 0.5, 1],
        })
        inst.set_state("cell[0][0]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_vmin_vmax(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 1, "cols": 2,
            "data": [5, 10],
            "vmin": 0, "vmax": 20,
        })
        svg = inst.emit_svg()
        # t for value 5 with vmin=0, vmax=20 -> 0.25, should be blue-ish
        assert "rgb(" in svg

    def test_label_rendered(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 1, "cols": 1,
            "label": "My Matrix",
        })
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg
        assert "My Matrix" in svg


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_basic_dimensions(self) -> None:
        inst = MatrixPrimitive("m", {
            "rows": 3, "cols": 4,
            "cell_size": 24,
        })
        x, y, w, h = inst.bounding_box()
        assert x == 0
        assert y == 0
        # 4 cells * 24 + 3 gaps * 1 = 99
        assert w == 99.0
        # 3 cells * 24 + 2 gaps * 1 = 74
        assert h == 74.0


# ---------------------------------------------------------------------------
# Heatmap alias
# ---------------------------------------------------------------------------


class TestHeatmapAlias:
    def test_heatmap_is_matrix(self) -> None:
        from scriba.animation.primitives.matrix import HeatmapPrimitive
        inst = HeatmapPrimitive("h", {
            "rows": 2, "cols": 2,
            "data": [0.1, 0.2, 0.3, 0.4],
        })
        assert isinstance(inst, MatrixPrimitive)
        assert inst.primitive_type == "matrix"


# ---------------------------------------------------------------------------
# Annotations — position pills + arrows (Layer B/C)
#
# Regression: Matrix accepted cell selectors (validate_selector) and stored
# annotations (set_annotations) but emit_svg rendered none of them — they were
# silently dropped. Matrix now resolves cell anchors and routes annotations
# through the shared engine (mirrors Grid), reserving space in bounding_box().
# Matrices without annotations are byte-stable (no reservation, no group).
# ---------------------------------------------------------------------------


class TestAnnotations:
    def test_cell_anchor_center(self) -> None:
        m = MatrixPrimitive("m", {"rows": 2, "cols": 3})
        cs = m.cell_size
        assert m.resolve_annotation_point("m.cell[0][0]") == (
            float(cs // 2),
            float(cs // 2),
        )
        assert m.resolve_annotation_point("m.cell[1][2]") == (
            float(2 * (cs + _MX_GAP) + cs // 2),
            float(1 * (cs + _MX_GAP) + cs // 2),
        )

    def test_invalid_cell_no_anchor(self) -> None:
        m = MatrixPrimitive("m", {"rows": 2, "cols": 3})
        assert m.resolve_annotation_point("m.cell[5][5]") is None

    def test_position_pill_above_renders(self) -> None:
        m = MatrixPrimitive("m", {"rows": 2, "cols": 3})
        m.set_annotations(
            [{"target": "m.cell[0][1]", "label": "HOT", "position": "above"}]
        )
        svg = m.emit_svg()
        assert "HOT" in svg  # was silently dropped
        assert "scriba-annotation" in svg

    def test_position_pill_below_renders(self) -> None:
        m = MatrixPrimitive("m", {"rows": 2, "cols": 3})
        m.set_annotations(
            [{"target": "m.cell[1][1]", "label": "COLD", "position": "below"}]
        )
        assert "COLD" in m.emit_svg()

    def test_no_annotation_bbox_unchanged(self) -> None:
        """Regression: an unannotated matrix reserves no annotation space."""
        plain = MatrixPrimitive("m", {"rows": 2, "cols": 3})
        _, _, _, h0 = plain.bounding_box()
        # height equals content (+ caption=0) with no annotation reservation
        assert h0 == float(plain._total_height())

    def test_annotation_reserves_space_above(self) -> None:
        m = MatrixPrimitive("m", {"rows": 2, "cols": 3})
        h_before = m.bounding_box().height
        m.set_annotations(
            [{"target": "m.cell[0][1]", "label": "HOT", "position": "above"}]
        )
        assert m.bounding_box().height > h_before  # reserved arrow space


# ---------------------------------------------------------------------------
# #1 horizontal pill reservation + #2 below-lane callout (mirrors Grid)
#
# #1: bounding_box() reserves horizontal room for position=left/right pills so a
#     right pill fits within bbox.width (no viewBox clip / left-clamp).
# #2: position=below pills sit in a callout lane below the WHOLE matrix (below
#     resolve_below_baseline), not just under the labelled cell.
# Byte-stability: an unannotated matrix's bbox is unchanged (ratchet).
# ---------------------------------------------------------------------------


class TestHorizontalReservationAndBelowLane:
    def test_unannotated_bbox_unchanged(self) -> None:
        # Captured pre-change values — byte-stability ratchet for this migration.
        assert tuple(
            MatrixPrimitive("m", {"rows": 3, "cols": 4, "cell_size": 24}).bounding_box()
        ) == (0, 0, 99.0, 74.0)

    def test_right_pill_fits_bbox_width(self) -> None:
        m = MatrixPrimitive("m", {"rows": 2, "cols": 3})
        m.set_annotations(
            [{"target": "m.cell[1][2]", "label": "a fairly long side note",
              "position": "right"}]
        )
        rects = _annotation_rects(m.emit_svg())
        assert rects, "right pill not rendered"
        bbox_w = float(m.bounding_box().width)
        for r in rects:
            assert r["x"] >= -1.0, f"left edge {r['x']} clips viewBox"
            assert r["x"] + r["width"] <= bbox_w + 1.0, (
                f"right edge {r['x'] + r['width']} exceeds bbox width {bbox_w}"
            )

    def test_below_pill_on_top_cell_sits_below_content(self) -> None:
        # A below pill on the TOP row must clear the whole matrix (callout lane),
        # not sit under row 0 where it would overlap the lower rows.
        m = MatrixPrimitive("m", {"rows": 3, "cols": 3})
        m.set_annotations(
            [{"target": "m.cell[0][0]", "label": "lane", "position": "below"}]
        )
        rects = _annotation_rects(m.emit_svg())
        assert rects, "below pill not rendered"
        content_bottom = float(m._total_height())  # 74
        assert m.resolve_below_baseline() >= content_bottom
        assert min(r["y"] for r in rects) >= content_bottom

    def test_cell_box_added(self) -> None:
        # Layer C: Matrix gained a cell AABB (offset-aware), returned ONLY for a
        # cell that carries a position=below pill (scoped so a wide above pill
        # over a narrow cell never trips the spanning leader).
        m = MatrixPrimitive("m", {"rows": 3, "cols": 3})
        assert m.resolve_annotation_box("m.cell[0][0]") is None  # no below pill
        m.set_annotations(
            [
                {"target": "m.cell[0][0]", "label": "a", "position": "below"},
                {"target": "m.cell[1][2]", "label": "b", "position": "below"},
            ]
        )
        assert tuple(m.resolve_annotation_box("m.cell[0][0]")) == (0, 0, 24, 24)
        assert tuple(m.resolve_annotation_box("m.cell[1][2]")) == (50, 25, 24, 24)
        assert m.resolve_annotation_box("m.cell[9][9]") is None

    def test_cell_box_offset_aware_with_labels(self) -> None:
        # With row/col headers, the box shifts by the same offsets as the anchor.
        m = MatrixPrimitive(
            "m",
            {"rows": 2, "cols": 2, "row_labels": ["r0", "r1"], "col_labels": ["c0", "c1"]},
        )
        m.set_annotations(
            [{"target": "m.cell[0][0]", "label": "a", "position": "below"}]
        )
        box = m.resolve_annotation_box("m.cell[0][0]")
        assert box is not None
        assert box.x == m.row_label_offset
        assert box.y == m.col_label_offset
