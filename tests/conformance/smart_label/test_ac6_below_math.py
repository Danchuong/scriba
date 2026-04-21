"""AC-6 conformance tests — math headroom applies to position=below labels.

Spec §1.7 AC-6; error code E1568.
v1 I-9 addressed only `above`; v2 closes the `below` gap.
"""
from __future__ import annotations

import pytest

from scriba.animation.primitives._svg_helpers import (
    _LABEL_HEADROOM,
    _LABEL_PILL_PAD_Y,
    position_label_height_above,
    position_label_height_below,
)

# The math headroom delta = 32 - 24 = 8 px.
# Derived from spec §3.3: `_LABEL_MATH_HEADROOM_EXTRA = 8`.
_MATH_HEADROOM_EXTRA = 8  # 32 - _LABEL_HEADROOM(24)


class TestInvAC6MathHeadroomBelow:
    """AC-6 (MUST): Math headroom (32 px) MUST apply in both
    position_label_height_above and position_label_height_below when any
    position-only annotation label contains $…$.

    v1 I-9 addressed only `above`; v2 closes the `below` gap.
    Spec §1.7 AC-6; error code E1568.
    """

    @pytest.mark.conformance
    def test_inv_AC6_math_headroom_below(self) -> None:
        """position_label_height_below with a math label MUST return a value
        that exceeds the plain-text variant by at least _MATH_HEADROOM_EXTRA (8 px).

        The exact formula is implementation-private, but the result MUST be
        strictly greater than the plain-text result by the 32-24=8 px delta.
        """
        cell_height = 40.0
        l_font_px = 11

        plain_anns = [
            {"target": "arr.cell[0]", "label": "plain text", "position": "below"}
        ]
        math_anns = [
            {"target": "arr.cell[0]", "label": r"$O(n^2)$", "position": "below"}
        ]

        plain_h = position_label_height_below(
            plain_anns, l_font_px=l_font_px, cell_height=cell_height
        )
        math_h = position_label_height_below(
            math_anns, l_font_px=l_font_px, cell_height=cell_height
        )

        assert math_h >= plain_h + _MATH_HEADROOM_EXTRA, (
            f"AC-6 VIOLATION: position_label_height_below with math label "
            f"returned {math_h} px, but plain-text returned {plain_h} px. "
            f"Expected math_h >= plain_h + {_MATH_HEADROOM_EXTRA} "
            f"(= {plain_h + _MATH_HEADROOM_EXTRA}). "
            "The math-headroom branch in position_label_height_below is missing. "
            "See spec §1.7 AC-6, §3.3, E1568."
        )

    @pytest.mark.conformance
    def test_inv_AC6_above_also_uses_32px(self) -> None:
        """Confirm the existing above branch also honours the 32 px rule.

        This acts as a conformance lock in the new suite.
        """
        cell_height = 40.0
        l_font_px = 11

        plain_anns = [
            {"target": "arr.cell[0]", "label": "plain", "position": "above"}
        ]
        math_anns = [
            {"target": "arr.cell[0]", "label": r"$\frac{n}{k}$", "position": "above"}
        ]

        plain_h = position_label_height_above(
            plain_anns, l_font_px=l_font_px, cell_height=cell_height
        )
        math_h = position_label_height_above(
            math_anns, l_font_px=l_font_px, cell_height=cell_height
        )

        assert math_h >= plain_h + _MATH_HEADROOM_EXTRA, (
            f"AC-6 regression in above branch: math={math_h}, plain={plain_h}, "
            f"delta={math_h - plain_h} < required {_MATH_HEADROOM_EXTRA}."
        )

    @pytest.mark.conformance
    def test_inv_AC6_below_zero_when_no_below_annotations(self) -> None:
        """position_label_height_below returns 0 when no below-position annotations exist."""
        anns = [
            {"target": "arr.cell[0]", "label": r"$x^2$", "position": "above"},
        ]
        result = position_label_height_below(anns, l_font_px=11, cell_height=40.0)
        assert result == 0, (
            f"Expected 0 for no below-annotations, got {result}."
        )
