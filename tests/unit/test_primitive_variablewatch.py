"""Tests for the VariableWatch primitive.

Covers declaration, selectors, addressable parts, state management,
SVG output, variable updates, and edge cases (empty names warning).
"""

from __future__ import annotations

import re
import warnings

import pytest

from scriba.animation.primitives.variablewatch import VariableWatch


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


class TestDeclare:
    def test_default_construction(self) -> None:
        inst = VariableWatch("vars", {"names": ["i", "j", "sum"]})
        assert inst.name == "vars"
        assert inst.var_names == ["i", "j", "sum"]
        assert inst.primitive_type == "variablewatch"

    def test_names_as_comma_string(self) -> None:
        inst = VariableWatch("vars", {"names": "x, y, z"})
        assert inst.var_names == ["x", "y", "z"]

    def test_initial_values_are_dashes(self) -> None:
        inst = VariableWatch("vars", {"names": ["a", "b"]})
        assert inst._values["a"] == "----"
        assert inst._values["b"] == "----"

    def test_label_parameter(self) -> None:
        inst = VariableWatch("vars", {"names": ["x"], "label": "Variables"})
        assert inst.label == "Variables"

    def test_empty_names_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            VariableWatch("vars", {"names": []})
            assert len(w) == 1
            assert "empty names" in str(w[0].message).lower()


# ---------------------------------------------------------------------------
# Addressable parts
# ---------------------------------------------------------------------------


class TestAddressableParts:
    def test_returns_var_selectors_and_all(self) -> None:
        inst = VariableWatch("vars", {"names": ["i", "j"]})
        parts = inst.addressable_parts()
        assert parts == ["var[i]", "var[j]", "all"]

    def test_empty_names_only_all(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            inst = VariableWatch("vars", {"names": []})
        assert inst.addressable_parts() == ["all"]


# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------


class TestValidateSelector:
    def test_var_valid(self) -> None:
        inst = VariableWatch("vars", {"names": ["i", "j"]})
        assert inst.validate_selector("var[i]") is True
        assert inst.validate_selector("var[j]") is True

    def test_var_unknown_name(self) -> None:
        inst = VariableWatch("vars", {"names": ["i"]})
        assert inst.validate_selector("var[x]") is False

    def test_all_valid(self) -> None:
        inst = VariableWatch("vars", {"names": ["i"]})
        assert inst.validate_selector("all") is True

    def test_unknown_selector(self) -> None:
        inst = VariableWatch("vars", {"names": ["i"]})
        assert inst.validate_selector("cell[0]") is False
        assert inst.validate_selector("nonsense") is False


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class TestState:
    def test_set_state_on_var(self) -> None:
        inst = VariableWatch("vars", {"names": ["i", "j"]})
        inst.set_state("var[i]", "current")
        assert inst.get_state("var[i]") == "current"
        assert inst.get_state("var[j]") == "idle"

    def test_set_state_all(self) -> None:
        inst = VariableWatch("vars", {"names": ["i"]})
        inst.set_state("all", "done")
        assert inst.get_state("all") == "done"


# ---------------------------------------------------------------------------
# Value operations
# ---------------------------------------------------------------------------


class TestValues:
    def test_set_value(self) -> None:
        inst = VariableWatch("vars", {"names": ["i", "j"]})
        inst.set_value("var[i]", "42")
        assert inst._values["i"] == "42"

    def test_set_value_unknown_var_ignored(self) -> None:
        inst = VariableWatch("vars", {"names": ["i"]})
        inst.set_value("var[x]", "99")
        assert "x" not in inst._values

    def test_apply_command_on_target(self) -> None:
        inst = VariableWatch("vars", {"names": ["i", "j"]})
        inst.apply_command({"value": "10"}, target_suffix="var[i]")
        assert inst._values["i"] == "10"

    def test_apply_command_bulk(self) -> None:
        inst = VariableWatch("vars", {"names": ["i", "j"]})
        inst.apply_command({"i": "5", "j": "7"})
        assert inst._values["i"] == "5"
        assert inst._values["j"] == "7"


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------


class TestEmitSvg:
    def test_basic_structure(self) -> None:
        inst = VariableWatch("vars", {"names": ["i", "j"]})
        svg = inst.emit_svg()
        assert 'data-primitive="variablewatch"' in svg
        assert 'data-shape="vars"' in svg
        assert 'data-target="vars.var[i]"' in svg
        assert 'data-target="vars.var[j]"' in svg

    def test_default_idle_class(self) -> None:
        inst = VariableWatch("vars", {"names": ["x"]})
        svg = inst.emit_svg()
        assert "scriba-state-idle" in svg

    def test_state_applied_in_svg(self) -> None:
        inst = VariableWatch("vars", {"names": ["x"]})
        inst.set_state("var[x]", "current")
        svg = inst.emit_svg()
        assert "scriba-state-current" in svg

    def test_label_rendered(self) -> None:
        inst = VariableWatch("vars", {"names": ["x"], "label": "Vars"})
        svg = inst.emit_svg()
        assert "scriba-primitive-label" in svg

    def test_empty_names_placeholder(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            inst = VariableWatch("vars", {"names": []})
        svg = inst.emit_svg()
        assert "no variables" in svg

    def test_value_appears_in_svg(self) -> None:
        inst = VariableWatch("vars", {"names": ["count"]})
        inst.set_value("var[count]", "99")
        svg = inst.emit_svg()
        assert "99" in svg

    def test_default_dashes_in_svg(self) -> None:
        inst = VariableWatch("vars", {"names": ["x"]})
        svg = inst.emit_svg()
        assert "----" in svg


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_bounding_box_positive(self) -> None:
        inst = VariableWatch("vars", {"names": ["a", "b"]})
        bbox = inst.bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0

    def test_bounding_box_empty(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            inst = VariableWatch("vars", {"names": []})
        bbox = inst.bounding_box()
        assert bbox.width > 0
        assert bbox.height > 0

    def test_all_state_propagates_to_vars(self) -> None:
        inst = VariableWatch("vars", {"names": ["i", "j"]})
        inst.set_state("all", "done")
        svg = inst.emit_svg()
        assert svg.count("scriba-state-done") >= 2

    def test_variable_name_with_underscore(self) -> None:
        inst = VariableWatch("vars", {"names": ["my_var"]})
        assert inst.validate_selector("var[my_var]") is True
        parts = inst.addressable_parts()
        assert "var[my_var]" in parts


# ---------------------------------------------------------------------------
# Annotation-pill space reservation (#1 left/right width, #2 below-lane)
# ---------------------------------------------------------------------------


def _ann_pills(svg: str) -> list[tuple[str, float, float, float, float]]:
    """Parse ``(data-annotation, x, y, w, h)`` for each rendered pill rect."""
    pills: list[tuple[str, float, float, float, float]] = []
    for block in re.findall(r'<g class="scriba-annotation[^"]*".*?</g>', svg, re.S):
        key = re.search(r'data-annotation="([^"]*)"', block)
        rect = re.search(
            r'<rect x="([\-\d.]+)" y="([\-\d.]+)" '
            r'width="([\-\d.]+)" height="([\-\d.]+)"',
            block,
        )
        if rect:
            x, y, w, h = (float(g) for g in rect.groups())
            pills.append((key.group(1) if key else "", x, y, w, h))
    return pills


class TestAnnotationReservation:
    """#1 horizontal pill reservation + #2 below-pill callout lane."""

    @pytest.mark.parametrize("position", ["right", "left"])
    def test_side_pill_fits_bbox_width(self, position: str) -> None:
        inst = VariableWatch("v", {"names": ["i", "j", "sum"]})
        inst.set_annotations(
            [{
                "target": "v.var[i]",
                "label": "a fairly long side note",
                "position": position,
            }]
        )
        pills = _ann_pills(inst.emit_svg())
        assert pills, f"{position} pill not rendered"
        width = float(inst.bounding_box().width)
        for _key, x, _y, w, _h in pills:
            assert x >= -1.0, f"{position} pill left edge {x} clips the viewBox"
            assert x + w <= width + 1.0, (
                f"{position} pill right edge {x + w} exceeds bbox width {width}"
            )

    def test_below_pill_sits_below_content(self) -> None:
        inst = VariableWatch("v", {"names": ["i", "j", "sum"]})
        inst.set_annotations(
            [{"target": "v.var[j]", "label": "below note", "position": "below"}]
        )
        bbox = inst.bounding_box()
        baseline = inst.resolve_below_baseline()
        assert baseline is not None
        below = [
            p for p in _ann_pills(inst.emit_svg()) if p[0].endswith("position-below")
        ]
        assert below, "below pill not rendered"
        for _key, _x, y, _w, h in below:
            assert y >= baseline, (
                f"below pill top {y} is not below content bottom {baseline}"
            )
            assert y + h <= bbox.height + 1.0, "below pill clipped at bbox bottom"

    def test_unannotated_bbox_unchanged(self) -> None:
        inst = VariableWatch("v", {"names": ["i", "j", "sum"]})
        # No left/right or below pills → zero reservation (byte-stable footprint).
        assert inst._h_label_pad() == (0, 0)
        assert inst._below_lane_height() == 0
        bbox = inst.bounding_box()
        # No caption/annotations: height collapses to the content bottom.
        assert bbox.height == inst.resolve_below_baseline()
        assert (bbox.width, bbox.height) == (208, 128)
