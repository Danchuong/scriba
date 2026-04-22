"""Unit tests for R-31 ext: prior-annotation arrow-stroke obstacles.

Covers:
  1. _sample_arrow_segments: unit tests for the sampling helper.
  2. Pill shift: second annotation's pill shifts when the first annotation's
     arrow geometry is present as an obstacle.
  3. Multi-annotation convergence: three annotations on one cell produce
     non-overlapping pills none of which sit on the arc samples.
  4. Determinism: two renders of the same scene produce byte-identical output.
"""

from __future__ import annotations

import math
import re

import pytest

from scriba.animation.primitives._obstacle_types import ObstacleSegment
from scriba.animation.primitives._svg_helpers import (
    _BEZIER_SAMPLE_N,
    _sample_arrow_segments,
    emit_arrow_svg,
    emit_plain_arrow_svg,
    _LabelPlacement,
    _segment_to_obstacle,
)
from scriba.animation.primitives.array import ArrayPrimitive


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CELL_W = 60  # ArrayPrimitive default cell width
_CELL_H = 40  # CELL_HEIGHT constant


def _array(size: int, annotations: list[dict]) -> ArrayPrimitive:
    inst = ArrayPrimitive("a", {"size": size})
    inst.set_annotations(annotations)
    return inst


def _cell_cx(idx: int, cell_w: int = _CELL_W, gap: int = 4) -> float:
    """Return x-centre of cell[idx] for a default ArrayPrimitive."""
    return float(idx * (cell_w + gap) + cell_w // 2)


def _extract_pill_xy(svg: str) -> list[tuple[int, int]]:
    """Extract all pill <rect x="..." y="..."> positions from SVG output."""
    return [(int(m.group(1)), int(m.group(2)))
            for m in re.finditer(r'<rect x="(\d+)" y="([^"]+)"', svg)]


def _rect_intervals(x: float, y: float, w: float, h: float) -> tuple:
    """Return (x_min, x_max, y_min, y_max) for a pill AABB."""
    return (x - w / 2, x + w / 2, y - h / 2, y + h / 2)


def _segment_intersects_pill(
    seg: ObstacleSegment,
    cx: float,
    cy: float,
    pw: float,
    ph: float,
) -> bool:
    """Return True if the segment overlaps the pill AABB (Liang-Barsky test)."""
    from scriba.animation.primitives._svg_helpers import _segment_rect_clip_length
    return _segment_rect_clip_length(
        seg.x0, seg.y0, seg.x1, seg.y1, cx, cy, pw, ph
    ) > 0.0


# ---------------------------------------------------------------------------
# 1. _sample_arrow_segments unit tests
# ---------------------------------------------------------------------------


class TestSampleArrowSegments:
    """Unit tests for _sample_arrow_segments helper."""

    def test_straight_line_returns_one_segment(self) -> None:
        segs = _sample_arrow_segments(
            (0.0, 0.0, 0.0, 0.0, 10.0, 20.0, 10.0, 20.0),
            is_straight=True,
        )
        assert len(segs) == 1

    def test_straight_line_endpoints_preserved(self) -> None:
        segs = _sample_arrow_segments(
            (5.0, 3.0, 5.0, 3.0, 15.0, 25.0, 15.0, 25.0),
            is_straight=True,
        )
        seg = segs[0]
        assert seg.x0 == pytest.approx(5.0)
        assert seg.y0 == pytest.approx(3.0)
        assert seg.x1 == pytest.approx(15.0)
        assert seg.y1 == pytest.approx(25.0)

    def test_bezier_returns_n_minus_1_segments(self) -> None:
        segs = _sample_arrow_segments(
            (0.0, 0.0, 10.0, -20.0, 30.0, -20.0, 40.0, 0.0),
            is_straight=False,
        )
        assert len(segs) == _BEZIER_SAMPLE_N - 1
        assert len(segs) == 7

    def test_bezier_first_segment_starts_at_p0(self) -> None:
        x0, y0 = 5.0, 10.0
        segs = _sample_arrow_segments(
            (x0, y0, 20.0, -30.0, 50.0, -30.0, 70.0, 10.0),
        )
        assert segs[0].x0 == pytest.approx(x0)
        assert segs[0].y0 == pytest.approx(y0)

    def test_bezier_last_segment_ends_at_p3(self) -> None:
        x3, y3 = 70.0, 10.0
        segs = _sample_arrow_segments(
            (5.0, 10.0, 20.0, -30.0, 50.0, -30.0, x3, y3),
        )
        assert segs[-1].x1 == pytest.approx(x3)
        assert segs[-1].y1 == pytest.approx(y3)

    def test_bezier_consecutive_segments_share_endpoints(self) -> None:
        segs = _sample_arrow_segments(
            (0.0, 0.0, 10.0, -20.0, 30.0, -20.0, 40.0, 0.0),
        )
        for i in range(len(segs) - 1):
            assert segs[i].x1 == pytest.approx(segs[i + 1].x0, abs=1e-9)
            assert segs[i].y1 == pytest.approx(segs[i + 1].y0, abs=1e-9)

    def test_all_segments_have_annotation_arrow_kind(self) -> None:
        segs_straight = _sample_arrow_segments(
            (0.0, 0.0, 0.0, 0.0, 5.0, 5.0, 5.0, 5.0), is_straight=True
        )
        segs_bezier = _sample_arrow_segments(
            (0.0, 0.0, 10.0, -10.0, 20.0, -10.0, 30.0, 0.0)
        )
        for seg in segs_straight + segs_bezier:
            assert seg.kind == "annotation_arrow"

    def test_all_segments_have_should_severity(self) -> None:
        segs = _sample_arrow_segments(
            (0.0, 0.0, 10.0, -10.0, 20.0, -10.0, 30.0, 0.0)
        )
        for seg in segs:
            assert seg.severity == "SHOULD"

    def test_state_propagated(self) -> None:
        segs = _sample_arrow_segments(
            (0.0, 0.0, 10.0, -10.0, 20.0, -10.0, 30.0, 0.0),
            state="warn",
        )
        for seg in segs:
            assert seg.state == "warn"

    def test_default_state_is_default(self) -> None:
        segs = _sample_arrow_segments(
            (0.0, 0.0, 10.0, -10.0, 20.0, -10.0, 30.0, 0.0),
        )
        for seg in segs:
            assert seg.state == "default"


# ---------------------------------------------------------------------------
# 2. Pill shift: second annotation shifts away from first arrow geometry
# ---------------------------------------------------------------------------


class TestPillShiftWithPriorArrow:
    """Second annotation's pill must shift when first arrow geometry is present.

    Geometry: ann1 is a long arc from (0,0)→(500,0); its mid-segment passes
    through y≈-35, which is exactly where ann2's natural pill (short arc from
    (240,0)→(260,0)) would land.  With prior-arrow obstacles the scorer
    penalises that position and the pill shifts upward.
    """

    # Fixed geometry that reliably produces arc-through-pill overlap.
    _SRC1 = (0.0, 0.0)
    _DST1 = (500.0, 0.0)
    _SRC2 = (240.0, 0.0)
    _DST2 = (260.0, 0.0)
    _LABEL2 = "Y"

    def _place_second_pill(self, inject_prior: bool) -> _LabelPlacement:
        """Emit ann1 and ann2; return ann2's placement with/without prior obstacles."""
        # Emit ann1 — capture its arc segments.
        ann1_segs = emit_arrow_svg(
            [],
            {"target": "B1", "arrow_from": "A1", "label": "X", "color": "info"},
            src_point=self._SRC1,
            dst_point=self._DST1,
            arrow_index=0,
            cell_height=float(_CELL_H),
            placed_labels=[],   # independent — no first-pill in the registry
        )

        prior_obs = (
            tuple(_segment_to_obstacle(s) for s in ann1_segs)
            if inject_prior and ann1_segs
            else None
        )

        placed: list[_LabelPlacement] = []
        emit_arrow_svg(
            [],
            {"target": "B2", "arrow_from": "A2",
             "label": self._LABEL2, "color": "info"},
            src_point=self._SRC2,
            dst_point=self._DST2,
            arrow_index=0,
            cell_height=float(_CELL_H),
            placed_labels=placed,
            primitive_obstacles=prior_obs,
        )
        assert placed, "emit_arrow_svg must register a placement"
        return placed[-1]

    def test_pill_shifts_when_prior_arrow_present(self) -> None:
        """The second pill position must differ between inject=True and False."""
        with_prior = self._place_second_pill(inject_prior=True)
        without_prior = self._place_second_pill(inject_prior=False)

        assert (with_prior.x, with_prior.y) != (without_prior.x, without_prior.y), (
            "Second pill should shift its position when prior arrow geometry "
            "is registered as an obstacle.\n"
            f"  without prior: ({without_prior.x}, {without_prior.y})\n"
            f"  with prior:    ({with_prior.x}, {with_prior.y})\n"
            "Both are identical — prior-annotation arc obstacles are not affecting scoring."
        )


# ---------------------------------------------------------------------------
# 3. Multi-annotation convergence — pills non-overlapping with arc samples
# ---------------------------------------------------------------------------


class TestMultiAnnotationConvergence:
    """Three annotations converging on one cell must produce non-colliding pills."""

    def _three_ann_svg(self) -> tuple[str, list[_LabelPlacement]]:
        """Render three annotations from cells 0, 1, 3 → cell 2."""
        inst = _array(6, [])
        src0 = inst.resolve_annotation_point("a.cell[0]")
        src1 = inst.resolve_annotation_point("a.cell[1]")
        src3 = inst.resolve_annotation_point("a.cell[3]")
        dst2 = inst.resolve_annotation_point("a.cell[2]")
        assert all(p is not None for p in [src0, src1, src3, dst2])

        placed: list[_LabelPlacement] = []
        all_segs: list[ObstacleSegment] = []
        all_parts: list[str] = []

        for idx, (src, label) in enumerate([
            (src0, "+2"),
            (src1, "+5"),
            (src3, "+7"),
        ]):
            prior_obs = (
                tuple(_segment_to_obstacle(s) for s in all_segs)
                if all_segs else None
            )
            new_segs = emit_arrow_svg(
                all_parts,
                {"target": "a.cell[2]", "arrow_from": f"a.cell[{idx if idx < 2 else 3}]",
                 "label": label, "color": "info"},
                src_point=src,
                dst_point=dst2,
                arrow_index=idx,
                cell_height=float(_CELL_H),
                placed_labels=placed,
                primitive_obstacles=prior_obs,
            )
            if new_segs:
                all_segs.extend(new_segs)

        return "\n".join(all_parts), placed

    def test_three_pills_non_overlapping(self) -> None:
        """All three placed pills must be pairwise non-overlapping."""
        _, placed = self._three_ann_svg()
        # Filter to only pills (placed list contains all registered labels)
        pills = list(placed)
        for i in range(len(pills)):
            for j in range(i + 1, len(pills)):
                assert not pills[i].overlaps(pills[j]), (
                    f"Pills {i} and {j} overlap: {pills[i]} vs {pills[j]}"
                )

    def test_pills_not_on_arc_segments(self) -> None:
        """Each pill must have zero or minimal intersection with all arc samples."""
        _, placed = self._three_ann_svg()
        inst = _array(6, [])
        src0 = inst.resolve_annotation_point("a.cell[0]")
        src1 = inst.resolve_annotation_point("a.cell[1]")
        src3 = inst.resolve_annotation_point("a.cell[3]")
        dst2 = inst.resolve_annotation_point("a.cell[2]")

        # Re-sample arcs for checking (we know the geometry).
        # Use a generous pill size for the intersection check.
        pill_w, pill_h = 50.0, 20.0

        # For each pill, assert no arc segment has significant clip length inside it.
        for pill in placed:
            px, py = pill.x, pill.y
            # We only have the pill centres from the placed registry.
            for src in [src0, src1, src3]:
                # Approximate arc control points (same formula as emit_arrow_svg).
                x1, y1 = float(src[0]), float(src[1])
                x2, y2 = float(dst2[0]), float(dst2[1])
                h_dist = abs(x2 - x1) + abs(y2 - y1)
                base_off = min(_CELL_H * 1.2,
                               max(_CELL_H * 0.5, math.sqrt(h_dist) * 2.5))
                mid_x = (x1 + x2) / 2
                mid_y = min(y1, y2) - base_off
                cx1 = (x1 + mid_x) / 2
                cy1 = mid_y
                cx2 = (x2 + mid_x) / 2
                cy2 = mid_y
                arc_segs = _sample_arrow_segments(
                    (x1, y1, cx1, cy1, cx2, cy2, x2, y2)
                )
                for seg in arc_segs:
                    # Allow a very small tolerance (floating-point boundary touch)
                    from scriba.animation.primitives._svg_helpers import (
                        _segment_rect_clip_length,
                    )
                    clip = _segment_rect_clip_length(
                        seg.x0, seg.y0, seg.x1, seg.y1,
                        px, py, pill.width, pill.height,
                    )
                    # Clip > 2 px is a genuine overlap — fail if any pill lands on arc.
                    assert clip < 2.0, (
                        f"Pill at ({px:.1f},{py:.1f}) overlaps arc segment "
                        f"({seg.x0:.1f},{seg.y0:.1f})->({seg.x1:.1f},{seg.y1:.1f}) "
                        f"with clip={clip:.2f}px"
                    )


# ---------------------------------------------------------------------------
# 4. Determinism: two renders must produce byte-identical SVG
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Same annotation scene rendered twice must produce identical SVG."""

    def _render_once(self) -> str:
        inst = _array(5, [
            {"target": "a.cell[2]", "arrow_from": "a.cell[0]",
             "label": "+h[0]^2", "color": "info"},
            {"target": "a.cell[2]", "arrow_from": "a.cell[1]",
             "label": "+h[1]^2", "color": "warn"},
            {"target": "a.cell[3]", "arrow_from": "a.cell[2]",
             "label": "result", "color": "good"},
        ])
        return inst.emit_svg()

    def test_two_renders_byte_identical(self) -> None:
        first = self._render_once()
        second = self._render_once()
        assert first == second, (
            "Two renders of the same scene must produce byte-identical SVG. "
            "Determinism broken — check for non-deterministic state in "
            "_sample_arrow_segments or emit_annotation_arrows."
        )

    def test_three_renders_byte_identical(self) -> None:
        renders = [self._render_once() for _ in range(3)]
        assert renders[0] == renders[1] == renders[2], (
            "Three renders of the same scene must produce identical SVG."
        )


# ---------------------------------------------------------------------------
# 5. emit_arrow_svg return value: geometry is returned as ObstacleSegment list
# ---------------------------------------------------------------------------


class TestEmitArrowSvgReturnsGeometry:
    """emit_arrow_svg and emit_plain_arrow_svg must return list[ObstacleSegment]."""

    def _cell_points(self) -> tuple[tuple[float, float], tuple[float, float]]:
        inst = _array(4, [])
        src = inst.resolve_annotation_point("a.cell[0]")
        dst = inst.resolve_annotation_point("a.cell[3]")
        assert src is not None and dst is not None
        return src, dst

    def test_emit_arrow_svg_returns_list(self) -> None:
        src, dst = self._cell_points()
        parts: list[str] = []
        result = emit_arrow_svg(
            parts,
            {"target": "a.cell[3]", "arrow_from": "a.cell[0]",
             "label": "X", "color": "info"},
            src_point=src,
            dst_point=dst,
            arrow_index=0,
            cell_height=float(_CELL_H),
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_emit_arrow_svg_returns_obstacle_segments(self) -> None:
        src, dst = self._cell_points()
        parts: list[str] = []
        result = emit_arrow_svg(
            parts,
            {"target": "a.cell[3]", "arrow_from": "a.cell[0]",
             "label": "X", "color": "info"},
            src_point=src,
            dst_point=dst,
            arrow_index=0,
            cell_height=float(_CELL_H),
        )
        for seg in result:
            assert isinstance(seg, ObstacleSegment)
            assert seg.kind == "annotation_arrow"
            assert seg.severity == "SHOULD"

    def test_emit_arrow_svg_bezier_returns_7_segments(self) -> None:
        src, dst = self._cell_points()
        parts: list[str] = []
        result = emit_arrow_svg(
            parts,
            {"target": "a.cell[3]", "arrow_from": "a.cell[0]",
             "label": "X", "color": "info"},
            src_point=src,
            dst_point=dst,
            arrow_index=0,
            cell_height=float(_CELL_H),
        )
        assert len(result) == _BEZIER_SAMPLE_N - 1

    def test_emit_plain_arrow_svg_returns_list(self) -> None:
        inst = _array(4, [])
        dst = inst.resolve_annotation_point("a.cell[1]")
        assert dst is not None
        parts: list[str] = []
        result = emit_plain_arrow_svg(
            parts,
            {"target": "a.cell[1]", "label": "Y", "color": "info"},
            dst_point=dst,
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_emit_plain_arrow_svg_returns_one_segment(self) -> None:
        inst = _array(4, [])
        dst = inst.resolve_annotation_point("a.cell[1]")
        assert dst is not None
        parts: list[str] = []
        result = emit_plain_arrow_svg(
            parts,
            {"target": "a.cell[1]", "label": "Y", "color": "info"},
            dst_point=dst,
        )
        assert len(result) == 1

    def test_emit_plain_arrow_svg_returns_obstacle_segment(self) -> None:
        inst = _array(4, [])
        dst = inst.resolve_annotation_point("a.cell[1]")
        assert dst is not None
        parts: list[str] = []
        result = emit_plain_arrow_svg(
            parts,
            {"target": "a.cell[1]", "label": "Y", "color": "info"},
            dst_point=dst,
        )
        seg = result[0]
        assert isinstance(seg, ObstacleSegment)
        assert seg.kind == "annotation_arrow"
        assert seg.severity == "SHOULD"


# ---------------------------------------------------------------------------
# 6. Annotation_arrow kind is handled by P7 (not hard-blocked via MUST)
# ---------------------------------------------------------------------------


class TestAnnotationArrowScoringKind:
    """annotation_arrow segments must be treated as SHOULD (P7) not MUST."""

    def test_annotation_arrow_segment_never_hard_blocks(self) -> None:
        """A SHOULD-severity annotation_arrow must not return inf from scoring."""
        from scriba.animation.primitives._svg_helpers import (
            _score_candidate,
            _ScoreContext,
            _Obstacle,
        )
        # Create an annotation_arrow obstacle as segment kind.
        # A straight horizontal segment through x=50,y=0 to x=50,y=100.
        seg_obs = _Obstacle(
            kind="segment",       # annotation_arrow is mapped via _segment_to_obstacle
            x=0.0, y=50.0,
            width=0.0, height=0.0,
            x2=100.0, y2=50.0,
            severity="SHOULD",
        )
        ctx = _ScoreContext(
            natural_x=50.0,
            natural_y=50.0,
            pill_w=40.0,
            pill_h=20.0,
            side_hint=None,
            arc_direction=(1.0, 0.0),
            color_token="info",
            viewbox_w=400.0,
            viewbox_h=300.0,
        )
        # Placing the pill exactly on the segment — SHOULD never returns inf.
        score = _score_candidate(50.0, 50.0, (seg_obs,), ctx)
        assert score != float("inf"), (
            "SHOULD-severity annotation_arrow segment must not hard-block "
            "(must not return inf). Got inf — severity enforcement is wrong."
        )
        assert score > 0.0, "Segment overlap should produce a non-zero penalty."

    def test_annotation_arrow_kind_classified_as_segment(self) -> None:
        """_segment_to_obstacle must map annotation_arrow to segment kind."""
        from scriba.animation.primitives._svg_helpers import _segment_to_obstacle
        seg = ObstacleSegment(
            kind="annotation_arrow",
            x0=0.0, y0=0.0, x1=50.0, y1=50.0,
            state="default",
            severity="SHOULD",
        )
        obs = _segment_to_obstacle(seg)
        assert obs.kind == "segment", (
            "_segment_to_obstacle must produce kind='segment' for annotation_arrow "
            "so it participates in P7 edge-occlusion scoring."
        )
        assert obs.severity == "SHOULD"
