"""Unit tests for scriba.animation.primitives.bar (Bar histogram primitive)."""

from __future__ import annotations

import re

import pytest

from scriba.animation.errors import AnimationError
from scriba.animation.primitives import get_primitive_registry
from scriba.animation.primitives.bar import Bar, _PLOT_HEIGHT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rect_heights(svg: str) -> list[float]:
    """Parse the ``<rect>`` heights (the columns) in document order."""
    return [float(h) for h in re.findall(r'<rect[^>]*\bheight="([0-9.]+)"', svg)]


def _rect_ys(svg: str) -> list[float]:
    return [float(y) for y in re.findall(r'<rect[^>]*\by="([0-9.]+)"', svg)]


# ---------------------------------------------------------------------------
# Construction & registry
# ---------------------------------------------------------------------------


class TestBarConstructor:
    def test_registered(self) -> None:
        assert get_primitive_registry().get("Bar") is Bar

    def test_primitive_type(self) -> None:
        assert Bar("h", {"data": [1, 2, 3]}).primitive_type == "bar"

    def test_values_parsed(self) -> None:
        b = Bar("h", {"data": [3, 1, 4, 1, 5]})
        assert b.values == [3.0, 1.0, 4.0, 1.0, 5.0]

    def test_int_and_float_mix(self) -> None:
        b = Bar("h", {"data": [1, 2.5, 3]})
        assert b.values == [1.0, 2.5, 3.0]

    def test_defaults(self) -> None:
        b = Bar("h", {"data": [1, 2]})
        assert b.label is None
        assert b.show_values is False

    def test_bar_width_alias(self) -> None:
        assert Bar("h", {"data": [1], "bar_width": 50}).bar_width == 50
        assert Bar("h", {"data": [1], "width": 24}).bar_width == 24
        # bar_width wins over width
        assert Bar("h", {"data": [1], "bar_width": 50, "width": 24}).bar_width == 50

    def test_unknown_param_rejected(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Bar("h", {"data": [1], "bogus": 1})
        assert "E1114" in str(ei.value)


# ---------------------------------------------------------------------------
# Data validation E-codes
# ---------------------------------------------------------------------------


class TestBarDataErrors:
    def test_missing_data_e1488(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Bar("h", {})
        assert "E1488" in str(ei.value)

    def test_empty_data_e1488(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Bar("h", {"data": []})
        assert "E1488" in str(ei.value)

    def test_string_data_e1489(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Bar("h", {"data": "abc"})
        assert "E1489" in str(ei.value)

    def test_scalar_data_e1489(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Bar("h", {"data": 7})
        assert "E1489" in str(ei.value)

    def test_non_numeric_element_e1490(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Bar("h", {"data": [1, "x", 3]})
        assert "E1490" in str(ei.value)

    def test_bool_element_rejected_e1490(self) -> None:
        with pytest.raises(AnimationError) as ei:
            Bar("h", {"data": [1, True]})
        assert "E1490" in str(ei.value)


# ---------------------------------------------------------------------------
# Height ∝ value
# ---------------------------------------------------------------------------


class TestBarHeights:
    def test_tallest_fills_plot(self) -> None:
        # ceiling defaults to max(data); that column fills the full plot.
        svg = Bar("h", {"data": [3, 6]}).emit_svg()
        hs = _rect_heights(svg)
        assert hs == [70.0, 140.0]
        assert abs(hs[1] - _PLOT_HEIGHT) < 1e-6

    def test_double_value_double_height(self) -> None:
        b = Bar("h", {"data": [2, 4, 6]})
        # Exact underlying computation is strictly proportional.
        ex = [b._bar_px_height(v) for v in b.values]
        assert abs(ex[1] - 2 * ex[0]) < 1e-9
        assert abs(ex[2] - 3 * ex[0]) < 1e-9
        # Parsed SVG heights agree within 2-dp rounding.
        hs = _rect_heights(b.emit_svg())
        assert abs(hs[1] - 2 * hs[0]) < 0.05

    def test_max_param_sets_full_scale(self) -> None:
        # With max=10 and a value of 5, the column is half the plot.
        hs = _rect_heights(Bar("h", {"data": [5], "max": 10}).emit_svg())
        assert abs(hs[0] - _PLOT_HEIGHT / 2) < 0.05

    def test_max_smaller_than_data_does_not_clip(self) -> None:
        # A max below the data is grown so the tall column still fits the plot.
        hs = _rect_heights(Bar("h", {"data": [5, 20], "max": 10}).emit_svg())
        assert max(hs) <= _PLOT_HEIGHT + 1e-6
        assert abs(hs[1] - _PLOT_HEIGHT) < 1e-6

    def test_zero_value_zero_height(self) -> None:
        hs = _rect_heights(Bar("h", {"data": [0, 5]}).emit_svg())
        assert hs[0] == 0.0

    def test_columns_share_baseline(self) -> None:
        # y + height == baseline for every column (bars grow up from one line).
        svg = Bar("h", {"data": [1, 3, 2]}).emit_svg()
        ys, hs = _rect_ys(svg), _rect_heights(svg)
        bottoms = [round(y + h, 2) for y, h in zip(ys, hs)]
        assert len(set(bottoms)) == 1


# ---------------------------------------------------------------------------
# Addressability, selectors, recolor
# ---------------------------------------------------------------------------


class TestBarSelectors:
    def test_addressable_parts(self) -> None:
        assert Bar("h", {"data": [1, 2, 3]}).addressable_parts() == [
            "bar[0]", "bar[1]", "bar[2]", "all",
        ]

    def test_validate_selector(self) -> None:
        b = Bar("h", {"data": [1, 2]})
        assert b.validate_selector("bar[0]")
        assert b.validate_selector("bar[1]")
        assert b.validate_selector("all")
        assert not b.validate_selector("bar[2]")
        assert not b.validate_selector("bar[-1]")
        assert not b.validate_selector("cell[0]")

    def test_recolor_applies_state_class(self) -> None:
        b = Bar("h", {"data": [1, 2, 3]})
        b.set_state("bar[1]", "current")
        svg = b.emit_svg()
        assert 'data-target="h.bar[1]"' in svg
        # The current column carries the state class; recolor swaps it at runtime.
        assert re.search(
            r'data-target="h\.bar\[1\]"\s+class="scriba-state-current"', svg
        )

    def test_all_sweep_colors_every_column(self) -> None:
        b = Bar("h", {"data": [1, 2]})
        b.set_state("all", "done")
        assert b.emit_svg().count("scriba-state-done") == 2

    def test_oob_selector_soft_drops(self) -> None:
        # set_state on an out-of-range column is a warned no-op (base E1115),
        # never an exception — mirrors the soft-drop selector contract.
        b = Bar("h", {"data": [1, 2]})
        with pytest.warns(UserWarning):
            b.set_state("bar[9]", "current")
        assert "scriba-state-current" not in b.emit_svg()


# ---------------------------------------------------------------------------
# Value apply → height change (rides value_change)
# ---------------------------------------------------------------------------


class TestBarValueApply:
    def test_set_value_changes_height(self) -> None:
        b = Bar("h", {"data": [2, 4, 6]})
        before = _rect_heights(b.emit_svg())[0]
        b.set_value("bar[0]", "6")  # 2 -> 6 (== ceiling)
        after = _rect_heights(b.emit_svg())[0]
        assert after > before
        assert abs(after - _PLOT_HEIGHT) < 1e-6

    def test_apply_command_value(self) -> None:
        b = Bar("h", {"data": [2, 4, 6]})
        b.apply_command({"value": 6}, target_suffix="bar[0]")
        assert abs(_rect_heights(b.emit_svg())[0] - _PLOT_HEIGHT) < 1e-6

    def test_set_value_out_of_range_ignored(self) -> None:
        b = Bar("h", {"data": [2, 4]})
        b.set_value("bar[9]", "5")  # silently dropped
        assert b.values == [2.0, 4.0]

    def test_set_value_non_numeric_ignored(self) -> None:
        b = Bar("h", {"data": [2, 4]})
        b.set_value("bar[0]", "not-a-number")
        assert b.values == [2.0, 4.0]

    def test_envelope_grows_no_clip(self) -> None:
        # A value above the initial ceiling grows the envelope; that column
        # fills the plot and the others rescale — nothing exceeds the plot.
        b = Bar("h", {"data": [2, 4, 6]})
        b.set_value("bar[0]", "12")
        hs = _rect_heights(b.emit_svg())
        assert max(hs) <= _PLOT_HEIGHT + 1e-6
        assert abs(hs[0] - _PLOT_HEIGHT) < 1e-6


# ---------------------------------------------------------------------------
# show_values
# ---------------------------------------------------------------------------


class TestBarShowValues:
    def test_show_values_renders_numbers(self) -> None:
        svg = Bar("h", {"data": [3, 7], "show_values": True}).emit_svg()
        assert ">3<" in svg
        assert ">7<" in svg

    def test_hidden_by_default(self) -> None:
        svg = Bar("h", {"data": [3, 7]}).emit_svg()
        # Only the two index labels (0, 1) are present, no value glyphs.
        assert ">3<" not in svg and ">7<" not in svg

    def test_integer_values_have_no_decimal(self) -> None:
        svg = Bar("h", {"data": [5], "show_values": True}).emit_svg()
        assert ">5<" in svg
        assert ">5.0<" not in svg


# ---------------------------------------------------------------------------
# Emit structure & bbox invariance (R-32)
# ---------------------------------------------------------------------------


class TestBarEmitStructure:
    def test_primitive_and_target_markers(self) -> None:
        svg = Bar("h", {"data": [1, 2]}).emit_svg()
        assert 'data-primitive="bar"' in svg
        assert 'data-shape="h"' in svg
        assert 'data-target="h.bar[0]"' in svg
        assert 'data-target="h.bar[1]"' in svg

    def test_one_rect_per_column(self) -> None:
        assert len(_rect_heights(Bar("h", {"data": [1, 2, 3, 4]}).emit_svg())) == 4

    def test_caption_rendered(self) -> None:
        svg = Bar("h", {"data": [1, 2], "label": "heights"}).emit_svg()
        assert "heights" in svg

    def test_bbox_invariant_across_value_change(self) -> None:
        # R-32: the envelope (viewBox) must not move when a column's height
        # changes — even past the initial ceiling.
        b = Bar("h", {"data": [2, 4, 6]})
        box0 = b.bounding_box()
        b.set_value("bar[0]", "6")
        box1 = b.bounding_box()
        b.set_value("bar[2]", "99")  # grows the envelope
        box2 = b.bounding_box()
        assert (box0.width, box0.height) == (box1.width, box1.height)
        assert (box0.width, box0.height) == (box2.width, box2.height)

    def test_bbox_height_independent_of_values(self) -> None:
        # Same shape, wildly different data → identical box (height is a pure
        # function of column count + layout constants).
        a = Bar("h", {"data": [1, 1, 1]}).bounding_box()
        c = Bar("h", {"data": [1000, 1, 500]}).bounding_box()
        assert (a.width, a.height) == (c.width, c.height)


# ---------------------------------------------------------------------------
# Annotation resolvers
# ---------------------------------------------------------------------------


class TestBarAnnotations:
    def test_annotation_point_is_column_top(self) -> None:
        b = Bar("h", {"data": [3, 6]})
        # bar[1] fills the plot, so its top-center sits at the plot top.
        pt = b.resolve_annotation_point("h.bar[1]")
        assert pt is not None
        assert abs(pt[1] - b._plot_top()) < 1e-6

    def test_annotation_point_tracks_height(self) -> None:
        b = Bar("h", {"data": [3, 6]})
        y_before = b.resolve_annotation_point("h.bar[0]")[1]
        b.set_value("bar[0]", "6")  # taller column → higher (smaller y) anchor
        y_after = b.resolve_annotation_point("h.bar[0]")[1]
        assert y_after < y_before

    def test_annotation_point_out_of_range_none(self) -> None:
        assert Bar("h", {"data": [1]}).resolve_annotation_point("h.bar[5]") is None

    def test_annotation_box_matches_column(self) -> None:
        b = Bar("h", {"data": [3, 6]})
        box = b.resolve_annotation_box("h.bar[1]")
        assert box is not None
        assert abs(box.height - _PLOT_HEIGHT) < 1e-6
        assert box.width == b.bar_width


class TestShowValuesLabelWidth:
    def test_near_equal_large_labels_do_not_overprint(self) -> None:
        # Near-equal large values -> equal heights -> all labels share one
        # y-row; 10-digit labels (~70px) at the default 44px pitch overprint.
        from scriba.animation.primitives._text_metrics import measure_value_text
        from scriba.animation.primitives.bar import _VALUE_FONT_PX, _fmt_value

        data = [1000000001, 1000000002, 1000000003, 1000000004]
        b = Bar("h", {"data": data, "show_values": True})
        centers = [b._bar_x(i) + b.bar_width / 2 for i in range(len(data))]
        pitch = centers[1] - centers[0]
        widest = max(measure_value_text(_fmt_value(v), _VALUE_FONT_PX) for v in data)
        assert pitch >= widest  # now 44 >= 70 -> FAILS; after fix ~76 >= 70

    def test_value_less_bars_keep_default_pitch(self) -> None:
        # No show_values -> pitch is byte-stable at bar_width + gap.
        b = Bar("h", {"data": [3, 6, 9]})
        assert b._bar_x(1) - b._bar_x(0) == b.bar_width + 8
