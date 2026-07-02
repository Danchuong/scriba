"""Caption clearance: one gap constant, every primitive, every branch.

Measured symptom: the Grid caption glyphs sat at -0.6px from the cell
bottoms (single-line captions anchor their CENTER at top_y+5, putting the
glyph top AT top_y, and grid/matrix/numberline passed top_y with ZERO gap).
Array/DPTable already kept a 9px _STACK_GAP; stack kept 8; queue kept 0 and
overlapped its own index labels; VariableWatch-family captions painted past
the bbox bottom whenever arrow_above > 0 (emitted inside the translate
group but anchored at bbox.height).
"""

from __future__ import annotations

import re

from scriba.animation.primitives._types import CELL_HEIGHT
from scriba.animation.primitives.base import _CAPTION_CLEAR_GAP
from scriba.animation.primitives.grid import GridPrimitive
from scriba.animation.primitives.matrix import MatrixPrimitive
from scriba.animation.primitives.numberline import NumberLinePrimitive
from scriba.animation.primitives.queue import Queue
from scriba.animation.primitives.variablewatch import VariableWatch

_CAPTION_FONT = 11


def _caption_glyph_top(svg: str) -> float:
    """Approx glyph top of the (single-line) caption in local coords."""
    m = re.search(r'<text class="scriba-primitive-label"[^>]*y="([-\d.]+)"', svg)
    assert m, "no caption <text>"
    y = float(m.group(1))
    # dominant-baseline:central — em box centered on y
    return y - _CAPTION_FONT / 2.0


def _inner_translate_y(svg: str) -> float:
    m = re.search(r'<g transform="translate\([-\d.]+,\s*([-\d.]+)\)">', svg)
    return float(m.group(1)) if m else 0.0


class TestFamilyBGap:
    def test_grid_caption_clears_cells(self) -> None:
        g = GridPrimitive("g", {"rows": 2, "cols": 2, "label": "chú thích"})
        svg = g.emit_svg()
        content_bottom = 2 * (CELL_HEIGHT + 2) - 2  # rows*(h+gap)-gap
        gap = _caption_glyph_top(svg) - content_bottom
        assert gap >= _CAPTION_CLEAR_GAP - 1.5, gap

    def test_matrix_caption_clears_cells(self) -> None:
        m = MatrixPrimitive("m", {"rows": 2, "cols": 2, "label": "chú thích"})
        svg = m.emit_svg()
        gap = _caption_glyph_top(svg) - m._total_height()
        assert gap >= _CAPTION_CLEAR_GAP - 1.5, gap

    def test_numberline_caption_clears_axis(self) -> None:
        n = NumberLinePrimitive("n", {"domain": [0, 4], "label": "chú thích"})
        svg = n.emit_svg()
        from scriba.animation.primitives.numberline import NL_HEIGHT

        gap = _caption_glyph_top(svg) - NL_HEIGHT
        assert gap >= _CAPTION_CLEAR_GAP - 1.5, gap

    def test_bbox_reserves_the_gap(self) -> None:
        # emit + bbox must move together or the caption clips the viewBox
        plain = GridPrimitive("g", {"rows": 2, "cols": 2})
        cap = GridPrimitive("g", {"rows": 2, "cols": 2, "label": "chú thích"})
        delta = cap.bounding_box().height - plain.bounding_box().height
        assert delta >= _CAPTION_CLEAR_GAP + 13 - 0.01  # gap + one line


class TestQueueCaptionVsIndexLabels:
    def test_caption_does_not_share_the_index_baseline(self) -> None:
        q = Queue("q", {"capacity": 3, "label": "hàng đợi"})
        svg = q.emit_svg()
        glyph_top = _caption_glyph_top(svg)
        idx_baselines = [
            float(y)
            for y in re.findall(
                r'<text class="scriba-index-label idx"[^>]*y="([-\d.]+)"', svg
            )
        ]
        assert idx_baselines
        # index glyphs (10px) end ~at their baseline; the caption glyph top
        # must start clearly below it
        assert glyph_top >= max(idx_baselines) + _CAPTION_CLEAR_GAP - 1.5, (
            glyph_top,
            max(idx_baselines),
        )


class TestFamilyCArrowAboveDoubleCount:
    def test_watch_caption_stays_inside_bbox_with_arrow(self) -> None:
        vw = VariableWatch("w", {"names": ["a", "b"], "label": "f = nền + d"})
        vw.set_annotations([
            {"target": "w.var[a]", "label": "x", "arrow_from": "w.var[b]"}
        ])
        svg = vw.emit_svg()
        ty = _inner_translate_y(svg)
        assert ty > 0, "case needs a reserved arrow lane"
        painted_caption_bottom = ty + _caption_glyph_top(svg) + _CAPTION_FONT
        assert painted_caption_bottom <= vw.bounding_box().height + 0.01, (
            painted_caption_bottom,
            vw.bounding_box().height,
        )
