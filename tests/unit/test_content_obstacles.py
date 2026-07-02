"""Pills must respect primitive content and use the horizontal space.

Diagnosed case (grid 5×5, arc cell[0][3]→cell[3][1], 40-codepoint label):
the pill sat at the arc bow peak — the grid interior — covering four cells,
because (1) cells were never obstacles, so every scoring term was blind to
content occlusion; (2) the arc wrapped in 24-char mode into a 148×45 tower;
(3) the auto side-hint could never propose the empty left side.

Structural fixes under test:
- W1 ``resolve_self_content_rects()``: primitives declare their own content
  AABBs; they join the scoring obstacles as SHOULD ``content_cell``.
- W2 arc labels wrap adaptively to the primitive's content span (via
  ``cell_metrics``) instead of the fixed char budget.
- W3 ``_infer_side_hint`` covers all four quadrants (down-left arrows now
  hint ``left`` instead of ``right``).
"""

from __future__ import annotations

import re

from scriba.animation.primitives._svg_helpers import _infer_side_hint
from scriba.animation.primitives.grid import GridPrimitive

_USER_LABEL = "m chẵn: vào từ trên-phải, xuống rồi trái"


def _user_case() -> GridPrimitive:
    g = GridPrimitive("g", {"rows": 5, "cols": 5})
    g.set_annotations([
        {
            "target": "g.cell[3][1]",
            "label": _USER_LABEL,
            "arrow_from": "g.cell[0][3]",
            "color": "good",
        }
    ])
    return g


def _pill_rect(svg: str) -> tuple[float, float, float, float]:
    m = re.search(
        r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"'
        r'[^>]*fill="white"',
        svg,
    )
    assert m, "no pill rect"
    x, y, w, h = map(float, m.groups())
    return x, y, w, h


def _cell_rects(svg: str) -> list[tuple[float, float, float, float]]:
    out = []
    for m in re.finditer(
        r'<g data-target="g\.cell\[\d+\]\[\d+\]"[^>]*>\s*<rect x="([\d.]+)" '
        r'y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"',
        svg,
    ):
        out.append(tuple(map(float, m.groups())))
    return out


class TestContentRectsHook:
    def test_grid_declares_all_cells(self) -> None:
        g = GridPrimitive("g", {"rows": 2, "cols": 3})
        rects = g.resolve_self_content_rects()
        assert len(rects) == 6
        first = rects[0]
        assert (first.x, first.y) == (0, 0)
        assert (first.width, first.height) == (60, 40)

    def test_base_default_is_empty(self) -> None:
        from scriba.animation.primitives.variablewatch import VariableWatch

        vw = VariableWatch("w", {"names": ["a"]})
        assert vw.resolve_self_content_rects() == []


class TestPillAvoidsCells:
    def test_user_case_pill_no_longer_buries_cells(self) -> None:
        svg = _user_case().emit_svg()
        px, py, pw, ph = _pill_rect(svg)
        pill_area = pw * ph
        covered = 0.0
        for cx, cy, cw, chh in _cell_rects(svg):
            ix = max(0.0, min(px + pw, cx + cw) - max(px, cx))
            iy = max(0.0, min(py + ph, cy + chh) - max(py, cy))
            covered += ix * iy
        assert covered <= 0.20 * pill_area, (
            f"pill still covers {covered / pill_area:.0%} of its area in cells "
            f"(pill at {px, py, pw, ph})"
        )


class TestAdaptiveWrap:
    def test_arc_label_wraps_to_grid_span_not_char_budget(self) -> None:
        svg = _user_case().emit_svg()
        _, _, pw, ph = _pill_rect(svg)
        # 24-char mode produced a 3-line 148x45 tower; with the grid span
        # (~288px budget) this 40-codepoint label fits in at most 2 lines
        # (good-color labels use a 12px font: 2*(12+2)+6 = 34).
        assert ph <= 2 * 14 + 6 + 0.01, (pw, ph)
        assert len(re.findall(r"<tspan", svg)) <= 2


def _coverage(svg: str) -> float:
    px, py, pw, ph = _pill_rect(svg)
    covered = 0.0
    for cx, cy, cw, chh in _cell_rects(svg):
        ix = max(0.0, min(px + pw, cx + cw) - max(px, cx))
        iy = max(0.0, min(py + ph, cy + chh) - max(py, cy))
        covered += ix * iy
    return covered


class TestEscapeLanes:
    """W4 (R-34): a short arrow deep inside the grid can't nudge free.

    The 48-nudge scan reaches 2.5*pill_h (~50px) from the natural anchor;
    an anchor on the middle row of a 5-row grid is ~110px from the nearest
    clear lane, so the pill settled on the least-covered cells — covering
    the annotation's own target cell. Lane candidates derived from the
    content extent close the gap (measured: lane scores 193 vs 482 for the
    best in-grid candidate, so the scorer picks the lane on merit).
    """

    def _short_arrow_case(self, label: str, src: str, dst: str) -> str:
        g = GridPrimitive("g", {"rows": 5, "cols": 5})
        g.set_annotations([
            {"target": dst, "label": label, "arrow_from": src, "color": "good"}
        ])
        return g.emit_svg()

    def test_mid_grid_vertical_arrow_escapes_cells(self) -> None:
        # user doc frame 4: pill buried the arrow's own target cell ("8")
        svg = self._short_arrow_case(
            "rẽ lên tới ô đích", "g.cell[2][2]", "g.cell[1][2]"
        )
        assert _coverage(svg) == 0.0, _pill_rect(svg)

    def test_mid_grid_horizontal_arrow_escapes_cells(self) -> None:
        # user doc frame 3
        svg = self._short_arrow_case(
            "m lẻ: đi phải, +1 mỗi ô", "g.cell[2][0]", "g.cell[2][2]"
        )
        assert _coverage(svg) == 0.0, _pill_rect(svg)

    def test_lane_pill_keeps_clearance_from_content(self) -> None:
        svg = self._short_arrow_case(
            "rẽ lên tới ô đích", "g.cell[2][2]", "g.cell[1][2]"
        )
        px, py, pw, ph = _pill_rect(svg)
        cells = _cell_rects(svg)
        top = min(c[1] for c in cells)
        bottom = max(c[1] + c[3] for c in cells)
        outside = py + ph <= top or py >= bottom
        assert outside
        gap = (top - (py + ph)) if py + ph <= top else (py - bottom)
        assert gap >= 4 - 0.01, gap

    def test_helper_yields_both_lanes(self) -> None:
        from scriba.animation.primitives._svg_helpers import (
            _Obstacle,
            _escape_lane_candidates,
        )

        # _Obstacle x/y are CENTERS: rows span y 0..40 and y 168..208
        obs = (
            _Obstacle(kind="content_cell", x=30, y=20, width=60, height=40,
                      severity="SHOULD"),
            _Obstacle(kind="content_cell", x=30, y=188, width=60, height=40,
                      severity="SHOULD"),
        )
        cands = _escape_lane_candidates(obs, natural_x=100.0, pill_h=20.0)
        assert (100.0, 0 - 10.0 - 4.0) in cands
        assert (100.0, 208 + 10.0 + 4.0) in cands
        assert len(cands) == 2

    def test_helper_empty_without_content_obstacles(self) -> None:
        from scriba.animation.primitives._svg_helpers import (
            _Obstacle,
            _escape_lane_candidates,
        )

        obs = (
            _Obstacle(kind="pill", x=0, y=0, width=60, height=20,
                      severity="SHOULD"),
        )
        assert _escape_lane_candidates(obs, natural_x=50.0, pill_h=20.0) == []


class TestSideHintQuadrants:
    def test_down_left_hints_left(self) -> None:
        assert _infer_side_hint(-10.0, 100.0) == "left"

    def test_down_right_hints_right(self) -> None:
        assert _infer_side_hint(10.0, 100.0) == "right"

    def test_horizontalish_hints_above(self) -> None:
        assert _infer_side_hint(100.0, 10.0) == "above"
        assert _infer_side_hint(-100.0, -10.0) == "above"

    def test_zero_vector_hints_none(self) -> None:
        assert _infer_side_hint(0.0, 0.0) is None
