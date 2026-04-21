"""G-1 conformance tests — post-clamp AABB registration.

Spec §1.1 G-1; error code E1562.
The pill AABB registered in the registry MUST use the post-clamp center
coordinate, never the pre-clamp coordinate.
"""
from __future__ import annotations

import pytest

from scriba.animation.primitives._svg_helpers import (
    _LabelPlacement,
    _LABEL_PILL_PAD_X,
    emit_arrow_svg,
    emit_plain_arrow_svg,
    _place_pill,
)


class TestInvG1PostClampAABB:
    """G-1 (MUST): The pill AABB registered in the registry MUST use the
    post-clamp center coordinate, never the pre-clamp coordinate.

    Spec §1.1 G-1; error code E1562.
    """

    @pytest.mark.conformance
    def test_inv_G1_post_clamp_aabb(self) -> None:
        """Place a label whose natural x is negative; assert registered x >= pill_w/2.

        Strategy: choose dst_point.x so small that the label's natural center
        lies at x < 0. The clamp formula in emit_plain_arrow_svg is
        `clamped_x = max(final_x, pill_w / 2)`. The registered entry MUST use
        clamped_x, not final_x.
        """
        placed: list[_LabelPlacement] = []
        ann = {"target": "t.cell[0]", "label": "AAAA", "color": "info"}
        emit_plain_arrow_svg(
            [], ann, dst_point=(2.0, 60.0), placed_labels=placed
        )

        assert len(placed) == 1, "one label must be registered"
        pill_w = placed[0].width
        assert pill_w > 0, "pill_w must be positive"

        # G-1: registered x MUST be the post-clamp coordinate
        assert placed[0].x >= pill_w / 2 - 0.5, (
            f"G-1 VIOLATION: registered x={placed[0].x:.2f} < pill_w/2={pill_w/2:.2f}. "
            "Pre-clamp coordinate was registered instead of post-clamp. "
            "See spec §1.1 G-1, E1562."
        )

    @pytest.mark.conformance
    def test_inv_G1_place_pill_post_clamp(self) -> None:
        """_place_pill with natural_x < pill_w/2 must return clamped center.

        The returned placement.x MUST be >= pill_w/2 (left-edge clamp).
        """
        pill_w, pill_h = 60.0, 20.0
        placed: list[_LabelPlacement] = []

        placement, fits_cleanly = _place_pill(
            natural_x=-50.0,   # off left edge
            natural_y=100.0,
            pill_w=pill_w,
            pill_h=pill_h,
            placed_labels=placed,
            viewbox_w=400.0,
            viewbox_h=300.0,
        )

        assert fits_cleanly is True, "empty registry should always fit cleanly"
        assert placement.x >= pill_w / 2, (
            f"G-1 VIOLATION via _place_pill: returned x={placement.x:.2f} < "
            f"pill_w/2={pill_w/2:.2f}. Clamp was not applied. "
            "See spec §1.1 G-1, E1562."
        )
        # Verify right-edge also clamped correctly
        assert placement.x + pill_w / 2 <= 400.0, (
            "Right edge of pill must not exceed viewbox_w."
        )

    @pytest.mark.conformance
    def test_inv_G1_place_pill_right_edge_clamp(self) -> None:
        """_place_pill with natural_x beyond right edge must clamp to viewbox_w - pill_w/2."""
        pill_w, pill_h = 60.0, 20.0

        placement, _ = _place_pill(
            natural_x=500.0,   # beyond right edge (viewbox_w=400)
            natural_y=100.0,
            pill_w=pill_w,
            pill_h=pill_h,
            placed_labels=[],
            viewbox_w=400.0,
            viewbox_h=300.0,
        )

        expected_max_x = 400.0 - pill_w / 2
        assert placement.x <= expected_max_x + 0.5, (
            f"G-1 VIOLATION: x={placement.x:.2f} > expected max {expected_max_x:.2f}. "
            "Right-edge clamp not applied."
        )
