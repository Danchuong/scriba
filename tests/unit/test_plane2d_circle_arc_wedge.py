"""Unit tests for Plane2D circle / arc / wedge element kinds (Wave-1 · B4).

Three new element kinds are added to Plane2D following the established
5-kind pattern (point / line / segment / polygon / region):

- Prelude population from ``circles`` / ``arcs`` / ``wedges`` params.
- Dynamic ``add_*`` / ``remove_*`` via ``apply_command``.
- Tombstone index stability (remove keeps later indices valid).
- ``validate_selector`` + ``addressable_parts`` for the new selectors.
- ``resolve_annotation_point`` anchors (circle=center, arc=arc-midpoint,
  wedge=sector interior along the mid-angle).
- ``emit_svg`` produces ``<circle>`` / ``<path>`` carrying the state class.
- Malformed add-specs and negative radii raise ``E1467``.
- Aspect handling: a circle is emitted as a ``<circle>`` *inside* the
  math->SVG transform, so it is a true circle when ``aspect="equal"`` and a
  geometrically-honest ellipse (rx=r*|sx|, ry=r*|sy|) when ``aspect="auto"``.

All tests operate on Plane2D directly — no parser/emitter layers required.
"""

from __future__ import annotations

import math

import pytest

from scriba.animation.primitives.plane2d import Plane2D, _TOMBSTONE
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _make_plane(**extra) -> Plane2D:
    params = {"xrange": [-10, 10], "yrange": [-10, 10], "width": 320}
    params.update(extra)
    return Plane2D("p", params)


# ---------------------------------------------------------------
# 1. Prelude population from \shape params
# ---------------------------------------------------------------


class TestPrelude:
    def test_circles_param_populates(self) -> None:
        p = _make_plane(circles=[{"cx": 1, "cy": 2, "r": 3}])
        assert len(p.circles) == 1
        assert p.circles[0] == {"cx": 1.0, "cy": 2.0, "r": 3.0}
        assert "circle[0]" in p.addressable_parts()

    def test_arcs_param_populates(self) -> None:
        p = _make_plane(arcs=[{"cx": 0, "cy": 0, "r": 2, "a0": 0, "a1": 90}])
        assert len(p.arcs) == 1
        assert p.arcs[0] == {"cx": 0.0, "cy": 0.0, "r": 2.0, "a0": 0.0, "a1": 90.0}
        assert "arc[0]" in p.addressable_parts()

    def test_wedges_param_populates(self) -> None:
        p = _make_plane(wedges=[{"cx": 0, "cy": 0, "r": 2, "a0": 30, "a1": 120}])
        assert len(p.wedges) == 1
        assert "wedge[0]" in p.addressable_parts()

    def test_tuple_specs_accepted(self) -> None:
        p = _make_plane(
            circles=[(1, 2, 3)],
            arcs=[(0, 0, 2, 0, 90)],
            wedges=[(0, 0, 2, 0, 90)],
        )
        assert p.circles[0]["r"] == 3.0
        assert p.arcs[0]["a1"] == 90.0
        assert p.wedges[0]["a0"] == 0.0

    def test_addressable_parts_ordering(self) -> None:
        """New kinds appear after the 5 legacy kinds, before "all"."""
        p = _make_plane(
            points=[(0, 0)],
            circles=[{"cx": 1, "cy": 1, "r": 1}],
            arcs=[{"cx": 0, "cy": 0, "r": 1, "a0": 0, "a1": 45}],
            wedges=[{"cx": 0, "cy": 0, "r": 1, "a0": 0, "a1": 45}],
        )
        parts = p.addressable_parts()
        assert parts == ["point[0]", "circle[0]", "arc[0]", "wedge[0]", "all"]


# ---------------------------------------------------------------
# 2. Dynamic add via apply_command
# ---------------------------------------------------------------


class TestAddDynamic:
    def test_add_circle(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 5}})
        assert p.validate_selector("circle[0]") is True
        assert p.circles[0]["r"] == 5.0

    def test_add_arc(self) -> None:
        p = _make_plane()
        p.apply_command({"add_arc": {"cx": 0, "cy": 0, "r": 2, "a0": 0, "a1": 180}})
        assert p.validate_selector("arc[0]") is True

    def test_add_wedge(self) -> None:
        p = _make_plane()
        p.apply_command({"add_wedge": {"cx": 0, "cy": 0, "r": 2, "a0": 0, "a1": 90}})
        assert p.validate_selector("wedge[0]") is True

    def test_add_is_independent_per_kind(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 1}})
        p.apply_command({"add_arc": {"cx": 0, "cy": 0, "r": 1, "a0": 0, "a1": 90}})
        p.apply_command({"add_wedge": {"cx": 0, "cy": 0, "r": 1, "a0": 0, "a1": 90}})
        assert len(p.circles) == 1
        assert len(p.arcs) == 1
        assert len(p.wedges) == 1


# ---------------------------------------------------------------
# 3. Remove / tombstone semantics (index stability, E1437)
# ---------------------------------------------------------------


class TestRemoveTombstone:
    def test_remove_circle_keeps_later_indices(self) -> None:
        p = _make_plane()
        for i in range(3):
            p.apply_command({"add_circle": {"cx": i, "cy": i, "r": 1}})
        original_c2 = dict(p.circles[2])
        p.apply_command({"remove_circle": 1})
        assert p.circles[1] is _TOMBSTONE
        assert len(p.circles) == 3  # slot retained
        assert p.circles[2] == original_c2
        parts = p.addressable_parts()
        assert "circle[0]" in parts
        assert "circle[1]" not in parts
        assert "circle[2]" in parts

    def test_remove_arc_and_wedge(self) -> None:
        p = _make_plane()
        p.apply_command({"add_arc": {"cx": 0, "cy": 0, "r": 1, "a0": 0, "a1": 90}})
        p.apply_command({"add_wedge": {"cx": 0, "cy": 0, "r": 1, "a0": 0, "a1": 90}})
        p.apply_command({"remove_arc": 0})
        p.apply_command({"remove_wedge": 0})
        assert p.arcs[0] is _TOMBSTONE
        assert p.wedges[0] is _TOMBSTONE
        assert p.addressable_parts() == ["all"]

    def test_remove_out_of_range_raises_e1437(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_circle": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_arc": 5})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_wedge": -1})

    def test_double_remove_raises_e1437(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 1}})
        p.apply_command({"remove_circle": 0})
        with pytest.raises(ValidationError, match="E1437"):
            p.apply_command({"remove_circle": 0})

    def test_remove_circle_does_not_affect_points(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_circle": {"cx": 1, "cy": 1, "r": 1}})
        p.apply_command({"remove_circle": 0})
        parts = p.addressable_parts()
        assert "point[0]" in parts
        assert "circle[0]" not in parts


# ---------------------------------------------------------------
# 4. validate_selector
# ---------------------------------------------------------------


class TestValidateSelector:
    def test_valid_and_tombstoned(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 1}})
        p.apply_command({"add_circle": {"cx": 1, "cy": 1, "r": 1}})
        p.apply_command({"remove_circle": 1})
        assert p.validate_selector("circle[0]") is True
        assert p.validate_selector("circle[1]") is False

    def test_out_of_range_returns_false(self) -> None:
        p = _make_plane()
        assert p.validate_selector("circle[0]") is False
        assert p.validate_selector("arc[3]") is False
        assert p.validate_selector("wedge[0]") is False


# ---------------------------------------------------------------
# 5. resolve_annotation_point anchors
# ---------------------------------------------------------------


class TestAnchor:
    def test_circle_anchor_is_center(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 2, "cy": -3, "r": 4}})
        anchor = p.resolve_annotation_point("p.circle[0]")
        assert anchor == p.math_to_svg(2.0, -3.0)

    def test_arc_anchor_is_arc_midpoint(self) -> None:
        p = _make_plane()
        p.apply_command({"add_arc": {"cx": 0, "cy": 0, "r": 2, "a0": 0, "a1": 90}})
        anchor = p.resolve_annotation_point("p.arc[0]")
        mid = math.radians(45.0)
        expected = p.math_to_svg(2 * math.cos(mid), 2 * math.sin(mid))
        assert anchor == pytest.approx(expected)

    def test_wedge_anchor_is_interior(self) -> None:
        p = _make_plane()
        p.apply_command({"add_wedge": {"cx": 0, "cy": 0, "r": 2, "a0": 0, "a1": 90}})
        anchor = p.resolve_annotation_point("p.wedge[0]")
        assert anchor is not None
        # Interior point sits along the 45-degree mid-angle, closer to center
        # than the arc radius (r*0.5).
        mid = math.radians(45.0)
        expected = p.math_to_svg(1.0 * math.cos(mid), 1.0 * math.sin(mid))
        assert anchor == pytest.approx(expected)

    def test_anchor_none_for_tombstone(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 1}})
        p.apply_command({"remove_circle": 0})
        assert p.resolve_annotation_point("p.circle[0]") is None

    def test_anchor_none_for_out_of_range(self) -> None:
        p = _make_plane()
        assert p.resolve_annotation_point("p.circle[9]") is None


# ---------------------------------------------------------------
# 6. emit_svg contains the right element + state class
# ---------------------------------------------------------------


class TestEmit:
    def test_circle_emits_circle_element(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 4}})
        svg = p.emit_svg()
        assert "scriba-plane-circle" in svg
        assert '<circle cx="0.0" cy="0.0" r="4.0"' in svg

    def test_arc_emits_path_element(self) -> None:
        p = _make_plane()
        p.apply_command({"add_arc": {"cx": 0, "cy": 0, "r": 2, "a0": 0, "a1": 90}})
        svg = p.emit_svg()
        assert "scriba-plane-arc" in svg
        assert "<path" in svg
        assert " A " in svg  # SVG elliptical-arc command

    def test_wedge_emits_filled_path(self) -> None:
        p = _make_plane()
        p.apply_command({"add_wedge": {"cx": 0, "cy": 0, "r": 2, "a0": 0, "a1": 90}})
        svg = p.emit_svg()
        assert "scriba-plane-wedge" in svg
        assert "<path" in svg
        assert "Z" in svg  # closed sector path

    def test_state_class_current(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 1}})
        p.set_state("circle[0]", "current")
        svg = p.emit_svg()
        assert "scriba-state-current" in svg

    def test_highlight_promotes_state(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 1}})
        p._highlighted = {"circle[0]"}
        svg = p.emit_svg()
        assert "scriba-state-highlight" in svg

    def test_tombstoned_circle_not_in_svg(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 7, "cy": 7, "r": 1}})
        p.apply_command({"add_circle": {"cx": 3, "cy": 3, "r": 1}})
        p.apply_command({"remove_circle": 0})
        svg = p.emit_svg()
        assert 'cx="3"' in svg or 'cx="3.0"' in svg
        assert 'cx="7"' not in svg and 'cx="7.0"' not in svg

    def test_hidden_state_not_rendered(self) -> None:
        p = _make_plane()
        p.apply_command({"add_circle": {"cx": 5, "cy": 5, "r": 1}})
        p.set_state("circle[0]", "hidden")
        svg = p.emit_svg()
        assert "scriba-plane-circle" not in svg


# ---------------------------------------------------------------
# 7. Arc geometry helpers (pure functions)
# ---------------------------------------------------------------


class TestArcGeometry:
    def test_sweep_normalization(self) -> None:
        assert Plane2D._arc_sweep(0, 90) == pytest.approx(90.0)
        assert Plane2D._arc_sweep(0, 270) == pytest.approx(270.0)
        assert Plane2D._arc_sweep(350, 10) == pytest.approx(20.0)  # wrap-around
        assert Plane2D._arc_sweep(90, 0) == pytest.approx(270.0)  # CCW the long way
        assert Plane2D._arc_sweep(0, 0) == pytest.approx(360.0)  # full turn

    def test_arc_path_small_arc_flags(self) -> None:
        d = Plane2D._arc_path_d(0, 0, 2, 0, 90, wedge=False)
        # start point (2,0), large-arc-flag 0, sweep-flag 1
        assert d.startswith("M 2.0000 0.0000 A 2.0000 2.0000 0 0 1")

    def test_arc_path_large_arc_flag(self) -> None:
        d = Plane2D._arc_path_d(0, 0, 2, 0, 270, wedge=False)
        # "A rx ry x-rot large-arc sweep": x-rot 0, large-arc 1 (270>180), sweep 1
        assert "A 2.0000 2.0000 0 1 1 " in d

    def test_wedge_path_closes_to_center(self) -> None:
        d = Plane2D._arc_path_d(1, 1, 2, 0, 90, wedge=True)
        assert d.startswith("M 1.0000 1.0000 L")  # move to center, line to rim
        assert d.endswith("Z")  # closed


# ---------------------------------------------------------------
# 8. Malformed specs -> E1467
# ---------------------------------------------------------------


class TestMalformed:
    def test_circle_wrong_type_raises_e1467(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"add_circle": "not-a-circle"})

    def test_circle_short_tuple_raises_e1467(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"add_circle": (0, 0)})

    def test_circle_missing_key_raises_e1467(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"add_circle": {"cx": 0, "cy": 0}})

    def test_circle_negative_radius_raises_e1467(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": -3}})

    def test_arc_missing_angle_raises_e1467(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"add_arc": {"cx": 0, "cy": 0, "r": 1, "a0": 0}})

    def test_wedge_wrong_type_raises_e1467(self) -> None:
        p = _make_plane()
        with pytest.raises(ValidationError, match="E1467"):
            p.apply_command({"add_wedge": 42})


# ---------------------------------------------------------------
# 9. Element cap counts new kinds
# ---------------------------------------------------------------


class TestCap:
    def test_total_elements_counts_new_kinds(self) -> None:
        p = _make_plane()
        p.apply_command({"add_point": (0, 0)})
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 1}})
        p.apply_command({"add_arc": {"cx": 0, "cy": 0, "r": 1, "a0": 0, "a1": 90}})
        p.apply_command({"add_wedge": {"cx": 0, "cy": 0, "r": 1, "a0": 0, "a1": 90}})
        assert p._total_elements() == 4


# ---------------------------------------------------------------
# 10. Aspect handling (true circle vs honest ellipse)
# ---------------------------------------------------------------


class TestAspect:
    def test_circle_present_under_equal(self) -> None:
        p = _make_plane(aspect="equal")
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 3}})
        svg = p.emit_svg()
        assert "<circle" in svg
        # aspect=equal -> |sx| == |sy| -> the <circle> renders as a true circle
        assert abs(p._sx) == pytest.approx(abs(p._sy))

    def test_circle_present_under_auto_as_honest_ellipse(self) -> None:
        # Non-square viewport with aspect="auto" -> |sx| != |sy|. The circle is
        # emitted inside the transform, so scale(sx, sy) distorts it into the
        # geometrically-honest ellipse rx=r*|sx|, ry=r*|sy|.
        p = _make_plane(yrange=[-5, 5], aspect="auto", height=320)
        p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 3}})
        svg = p.emit_svg()
        assert "<circle" in svg
        assert abs(p._sx) != pytest.approx(abs(p._sy))


class TestOversizedRadiusWarning:
    """A circle/arc/wedge whose CENTER is in range but whose RADIUS pushes it
    past the viewport gets the same E1463 diagnostic a point does — the
    warning previously only checked the center (bmad-aspect)."""

    def test_oversized_circle_warns(self, caplog) -> None:
        import logging
        from scriba.animation.primitives.plane2d import Plane2D

        p = Plane2D("p", {"xrange": [-2, 2], "yrange": [-2, 2], "aspect": "auto"})
        with caplog.at_level(logging.WARNING):
            p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 4}})
        assert any("E1463" in r.message for r in caplog.records)

    def test_wellsized_circle_silent(self, caplog) -> None:
        import logging
        from scriba.animation.primitives.plane2d import Plane2D

        p = Plane2D("p", {"xrange": [-2, 2], "yrange": [-2, 2]})
        with caplog.at_level(logging.WARNING):
            p.apply_command({"add_circle": {"cx": 0, "cy": 0, "r": 1}})
        assert not any("E1463" in r.message for r in caplog.records)
