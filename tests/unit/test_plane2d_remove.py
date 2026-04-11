"""Unit tests for Plane2D dynamic remove ops (Wave 6.5 / RFC-001 §4.3).

Tombstone semantics verified:

- Remove ops mark the slot with a sentinel; index positions remain stable.
- ``addressable_parts`` and ``validate_selector`` both skip tombstoned slots.
- ``emit_svg`` does not render tombstoned or ``hidden``-state elements.
- Double-remove and out-of-range remove both raise ``E1437``.
- Convex-hull-style pop patterns (the motivating RFC use case) work.

All tests operate on Plane2D directly — no parser/emitter layers required.
"""

from __future__ import annotations

import pytest

from scriba.animation.constants import VALID_STATES
from scriba.animation.primitives.plane2d import Plane2D, _TOMBSTONE
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


HIDDEN_SUPPORTED = "hidden" in VALID_STATES


def _make_plane(**extra) -> Plane2D:
    params = {"xrange": [-10, 10], "yrange": [-10, 10], "width": 320}
    params.update(extra)
    return Plane2D("p", params)


# ---------------------------------------------------------------
# 1. Basic tombstone behavior (points)
# ---------------------------------------------------------------


class TestRemovePoint:
    def test_remove_middle_point_addressable_parts(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"add_point": (2, 2)})

        p.apply_command({"remove_point": 1})

        parts = p.addressable_parts()
        # 2 live points + "all"
        assert parts == ["point[0]", "point[2]", "all"]
        assert "point[1]" not in parts

    def test_remove_first_point(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"remove_point": 0})
        assert "point[0]" not in p.addressable_parts()
        assert "point[1]" in p.addressable_parts()

    def test_remove_last_point(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"remove_point": 1})
        assert "point[0]" in p.addressable_parts()
        assert "point[1]" not in p.addressable_parts()

    def test_tombstone_sentinel_in_place(self) -> None:
        """Internal slot is marked with the sentinel, not deleted."""
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"add_point": (2, 2)})
        p.apply_command({"remove_point": 1})
        assert len(p.points) == 3  # list length unchanged
        assert p.points[1] is _TOMBSTONE

    def test_remove_out_of_range_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"add_point": (2, 2)})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_point": 99})

    def test_remove_negative_index_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_point": -1})

    def test_remove_empty_plane_raises_e1437(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_point": 0})

    def test_double_remove_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"remove_point": 1})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_point": 1})


# ---------------------------------------------------------------
# 2. Index stability across removals
# ---------------------------------------------------------------


class TestIndexStability:
    def test_remove_middle_preserves_later_indices(self) -> None:
        """After removing point[2] from a 5-point plane, point[3] and point[4]
        must still resolve to their ORIGINAL values (no shift)."""
        p = _make_plane()
        for x in range(5):
            p.apply_command({"add_point": (float(x), float(x))})

        original_pt3 = dict(p.points[3])
        original_pt4 = dict(p.points[4])

        p.apply_command({"remove_point": 2})

        # point[3] and point[4] still point to the same dicts
        assert p.points[3] == original_pt3
        assert p.points[4] == original_pt4
        assert p.points[3]["x"] == 3.0
        assert p.points[4]["x"] == 4.0

    def test_remove_multiple_preserves_remaining_indices(self) -> None:
        p = _make_plane()
        for x in range(5):
            p.apply_command({"add_point": (float(x), float(x))})

        p.apply_command({"remove_point": 1})
        p.apply_command({"remove_point": 3})

        parts = p.addressable_parts()
        assert "point[0]" in parts
        assert "point[1]" not in parts
        assert "point[2]" in parts
        assert "point[3]" not in parts
        assert "point[4]" in parts


# ---------------------------------------------------------------
# 3. validate_selector behavior
# ---------------------------------------------------------------


class TestValidateSelector:
    def test_tombstoned_point_is_invalid(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"add_point": (2, 2)})
        p.apply_command({"remove_point": 2})
        assert p.validate_selector("point[0]") is True
        assert p.validate_selector("point[1]") is True
        assert p.validate_selector("point[2]") is False

    def test_all_selector_still_valid_after_remove(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"remove_point": 0})
        assert p.validate_selector("all") is True

    def test_out_of_range_selector_returns_false(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        assert p.validate_selector("point[99]") is False


# ---------------------------------------------------------------
# 4. emit_svg skips tombstones
# ---------------------------------------------------------------


class TestEmitSvgTombstones:
    def test_tombstoned_point_not_in_svg(self) -> None:
        p = _make_plane()
        # Use very distinctive coordinates so we can grep for them
        p.apply_command({"add_point": (7.7, 7.7)})
        p.apply_command({"add_point": (3.3, 3.3)})
        p.apply_command({"add_point": (7.7, 7.7)})  # same as first

        svg_before = p.emit_svg()
        assert 'cx="3.3"' in svg_before

        p.apply_command({"remove_point": 1})  # remove the 3.3,3.3 point

        svg_after = p.emit_svg()
        assert 'cx="3.3"' not in svg_after
        # The 7.7 points are still there (two of them)
        assert svg_after.count('cx="7.7"') == 2

    def test_tombstoned_point_label_not_in_svg(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (1.0, 1.0, "LABEL_KEEP")})
        p.apply_command({"add_point": (2.0, 2.0, "LABEL_DROP")})

        p.apply_command({"remove_point": 1})
        svg = p.emit_svg()

        assert "LABEL_KEEP" in svg
        assert "LABEL_DROP" not in svg


# ---------------------------------------------------------------
# 5. Hidden state (RFC-001 §4.4)
# ---------------------------------------------------------------


@pytest.mark.skipif(
    not HIDDEN_SUPPORTED,
    reason="'hidden' state not yet in VALID_STATES (W6.3 pending)",
)
class TestHiddenState:
    def test_hidden_point_not_rendered(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (7.7, 7.7)})
        p.apply_command({"add_point": (3.3, 3.3)})
        p.set_state("point[0]", "hidden")
        svg = p.emit_svg()
        assert 'cx="7.7"' not in svg
        assert 'cx="3.3"' in svg

    def test_hidden_is_separate_from_tombstone(self) -> None:
        """Hidden elements still count as addressable."""
        p = _make_plane()
        p.apply_command({"add_point": (1.0, 1.0)})
        p.apply_command({"add_point": (2.0, 2.0)})
        p.set_state("point[0]", "hidden")
        # Still addressable — hidden is a render-time concern
        assert "point[0]" in p.addressable_parts()
        assert p.validate_selector("point[0]") is True


# ---------------------------------------------------------------
# 6. Cross-element isolation
# ---------------------------------------------------------------


class TestCrossElement:
    def test_remove_line_does_not_affect_points(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_point": (1, 1)})
        p.apply_command({"add_point": (2, 2)})
        p.apply_command({"add_line": ("L1", 1.0, 0.0)})
        p.apply_command({"add_line": ("L2", 2.0, 0.0)})

        p.apply_command({"remove_line": 0})

        parts = p.addressable_parts()
        assert "point[0]" in parts
        assert "point[1]" in parts
        assert "point[2]" in parts
        assert "line[0]" not in parts
        assert "line[1]" in parts

    def test_remove_point_does_not_affect_segments(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        p.apply_command({"add_segment": ((1, 1), (2, 2))})

        p.apply_command({"remove_point": 0})

        parts = p.addressable_parts()
        assert "point[0]" not in parts
        assert "segment[0]" in parts
        assert "segment[1]" in parts


# ---------------------------------------------------------------
# 7. Remove line / segment / polygon / region parity
# ---------------------------------------------------------------


class TestRemoveLine:
    def test_remove_line_basic(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("L1", 1.0, 0.0)})
        p.apply_command({"add_line": ("L2", 2.0, 0.0)})
        p.apply_command({"remove_line": 0})
        parts = p.addressable_parts()
        assert "line[0]" not in parts
        assert "line[1]" in parts

    def test_remove_line_out_of_range_raises_e1437(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_line": 0})

    def test_remove_line_double_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("L1", 1.0, 0.0)})
        p.apply_command({"remove_line": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_line": 0})

    def test_tombstoned_line_not_in_svg(self) -> None:
        p = _make_plane()
        p.apply_command({"add_line": ("L_KEEP", 1.0, 0.0)})
        p.apply_command({"add_line": ("L_DROP", -1.0, 5.0)})
        p.apply_command({"remove_line": 1})
        svg = p.emit_svg()
        assert "L_KEEP" in svg
        assert "L_DROP" not in svg


class TestRemoveSegment:
    def test_remove_segment_basic(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        p.apply_command({"add_segment": ((1, 1), (2, 2))})
        p.apply_command({"remove_segment": 0})
        parts = p.addressable_parts()
        assert "segment[0]" not in parts
        assert "segment[1]" in parts

    def test_remove_segment_out_of_range_raises_e1437(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_segment": 5})

    def test_remove_segment_double_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        p.apply_command({"remove_segment": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_segment": 0})


class TestRemovePolygon:
    def test_remove_polygon_basic(self) -> None:
        p = _make_plane()
        p.apply_command({"add_polygon": [(0, 0), (1, 0), (1, 1), (0, 0)]})
        p.apply_command({"add_polygon": [(2, 2), (3, 2), (3, 3), (2, 2)]})
        p.apply_command({"remove_polygon": 0})
        parts = p.addressable_parts()
        assert "polygon[0]" not in parts
        assert "polygon[1]" in parts

    def test_remove_polygon_out_of_range_raises_e1437(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_polygon": 0})

    def test_remove_polygon_double_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_polygon": [(0, 0), (1, 0), (1, 1), (0, 0)]})
        p.apply_command({"remove_polygon": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_polygon": 0})


class TestRemoveRegion:
    def test_remove_region_basic(self) -> None:
        p = _make_plane()
        p.apply_command({"add_region": {"polygon": [(0, 0), (1, 0), (1, 1)], "fill": "red"}})
        p.apply_command({"add_region": {"polygon": [(2, 2), (3, 2), (3, 3)], "fill": "blue"}})
        p.apply_command({"remove_region": 0})
        parts = p.addressable_parts()
        assert "region[0]" not in parts
        assert "region[1]" in parts

    def test_remove_region_out_of_range_raises_e1437(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_region": 0})


# ---------------------------------------------------------------
# 8. Convex-hull authenticity
# ---------------------------------------------------------------


class TestConvexHullPop:
    def test_pop_pattern_preserves_surviving_indices(self) -> None:
        """Motivating RFC use case: a convex-hull algorithm pops points
        off the candidate list. After popping point[2] and point[4], the
        surviving addressable parts must be exactly [0, 1, 3]."""
        p = _make_plane()
        for i in range(5):
            p.apply_command({"add_point": (float(i), float(i * i % 7))})

        p.apply_command({"remove_point": 2})
        p.apply_command({"remove_point": 4})

        parts = [s for s in p.addressable_parts() if s.startswith("point[")]
        assert parts == ["point[0]", "point[1]", "point[3]"]


# ---------------------------------------------------------------
# 9. Mixed add + remove sequencing
# ---------------------------------------------------------------


class TestMixedAddRemove:
    def test_add_remove_add_preserves_original_index(self) -> None:
        """After adding two points, removing point[0], then adding a third
        point, the surviving original point[1] must still be at index 1
        and the new point must be at index 2 (list append semantics)."""
        p = _make_plane()
        p.apply_command({"add_point": (1.0, 1.0)})  # index 0
        p.apply_command({"add_point": (2.0, 2.0)})  # index 1
        p.apply_command({"remove_point": 0})
        p.apply_command({"add_point": (3.0, 3.0)})  # index 2 (append)

        # Surviving live parts
        parts = p.addressable_parts()
        assert "point[0]" not in parts
        assert "point[1]" in parts
        assert "point[2]" in parts

        # Original values preserved
        assert p.points[1]["x"] == 2.0
        assert p.points[2]["x"] == 3.0
        assert p.points[0] is _TOMBSTONE

    def test_remove_then_add_does_not_reuse_slot(self) -> None:
        """Tombstones are permanent — new adds never reuse a tombstoned slot."""
        p = _make_plane()
        p.apply_command({"add_point": (1.0, 1.0)})
        p.apply_command({"remove_point": 0})
        p.apply_command({"add_point": (2.0, 2.0)})
        assert p.points[0] is _TOMBSTONE
        assert p.points[1]["x"] == 2.0
        assert len(p.points) == 2


# ---------------------------------------------------------------
# 10. Cap interaction — tombstoned slots still count
# ---------------------------------------------------------------


class TestCapWithTombstones:
    def test_tombstones_count_toward_cap(self) -> None:
        """Tombstones preserve index stability, so they continue to occupy
        a slot in the underlying list and count toward the element cap."""
        p = _make_plane()
        for i in range(5):
            p.apply_command({"add_point": (float(i), float(i))})
        p.apply_command({"remove_point": 2})
        # Only 4 live points but the list still has 5 slots
        assert len(p.points) == 5
        assert len([x for x in p.points if x is not _TOMBSTONE]) == 4


# ---------------------------------------------------------------
# 11. Smoke — emit_svg never raises on all-tombstone lists
# ---------------------------------------------------------------


class TestEmitSmoke:
    def test_emit_svg_with_all_points_removed(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (1.0, 1.0)})
        p.apply_command({"add_point": (2.0, 2.0)})
        p.apply_command({"remove_point": 0})
        p.apply_command({"remove_point": 1})
        # Must not raise — just produces a plane with no points
        svg = p.emit_svg()
        assert isinstance(svg, str)
        assert 'cx="1.0"' not in svg
        assert 'cx="2.0"' not in svg

    def test_emit_svg_with_mixed_element_removals(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (1.0, 1.0)})
        p.apply_command({"add_line": ("L", 1.0, 0.0)})
        p.apply_command({"add_segment": ((0, 0), (1, 1))})
        p.apply_command({"add_polygon": [(0, 0), (1, 0), (0, 1), (0, 0)]})

        p.apply_command({"remove_point": 0})
        p.apply_command({"remove_line": 0})
        p.apply_command({"remove_segment": 0})
        p.apply_command({"remove_polygon": 0})

        # Must not raise
        svg = p.emit_svg()
        assert isinstance(svg, str)
        assert p.addressable_parts() == ["all"]
