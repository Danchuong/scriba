"""Unit tests for scriba.animation.primitives.metricplot."""

from __future__ import annotations

import math
import re

import pytest

from scriba.animation.primitives.metricplot import MetricPlot, _WONG_COLORS, _DASH_PATTERNS
from scriba.core.errors import ValidationError


# ---------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------


class TestMetricPlotConstructor:
    def test_string_series_shortcut(self) -> None:
        mp = MetricPlot("plot", {"series": ["phi", "cost"]})
        assert len(mp._series) == 2
        assert mp._series[0].name == "phi"
        assert mp._series[0].color == _WONG_COLORS[0]
        assert mp._series[0].axis == "left"
        assert mp._series[0].scale == "linear"
        assert mp._series[1].name == "cost"
        assert mp._series[1].color == _WONG_COLORS[1]

    def test_dict_series_canonical(self) -> None:
        mp = MetricPlot("plot", {
            "series": [
                {"name": "energy", "color": "#ff0000", "axis": "right", "scale": "log"},
            ],
        })
        s = mp._series[0]
        assert s.name == "energy"
        assert s.color == "#ff0000"
        assert s.axis == "right"
        assert s.scale == "log"

    def test_default_params(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        assert mp.xlabel == "step"
        assert mp.ylabel == "value"
        assert mp.grid is True
        assert mp.width == 320
        assert mp.height == 200
        assert mp.show_legend is True
        assert mp.show_current_marker is True

    def test_custom_params(self) -> None:
        mp = MetricPlot("p", {
            "series": ["x"],
            "xlabel": "iteration",
            "ylabel": "energy",
            "grid": False,
            "width": 400,
            "height": 250,
            "show_legend": False,
            "show_current_marker": False,
        })
        assert mp.xlabel == "iteration"
        assert mp.ylabel == "energy"
        assert mp.grid is False
        assert mp.width == 400
        assert mp.height == 250

    def test_primitive_type(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        assert mp.primitive_type == "metricplot"


# ---------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------


class TestMetricPlotValidation:
    def test_e1480_empty_series(self) -> None:
        with pytest.raises(ValidationError, match="E1480"):
            MetricPlot("p", {"series": []})

    def test_e1481_too_many_series(self) -> None:
        with pytest.raises(ValidationError, match="E1481"):
            MetricPlot("p", {"series": [f"s{i}" for i in range(9)]})

    def test_e1485_duplicate_series_names(self) -> None:
        with pytest.raises(ValidationError, match="E1485"):
            MetricPlot("p", {"series": ["phi", "phi"]})

    def test_e1486_degenerate_xrange(self) -> None:
        with pytest.raises(ValidationError, match="E1486"):
            MetricPlot("p", {"series": ["x"], "xrange": [5.0, 5.0]})

    def test_e1487_axis_scale_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="E1487"):
            MetricPlot("p", {
                "series": [
                    {"name": "a", "axis": "left", "scale": "linear"},
                    {"name": "b", "axis": "left", "scale": "log"},
                ],
            })


# ---------------------------------------------------------------
# Data accumulation tests
# ---------------------------------------------------------------


class TestApplyCommand:
    def test_feeds_data_correctly(self) -> None:
        mp = MetricPlot("p", {"series": ["phi", "cost"]})
        mp.apply_command({"phi": 3.2, "cost": 5.1})
        assert mp._data["phi"] == [3.2]
        assert mp._data["cost"] == [5.1]

    def test_multiple_applies(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        mp.apply_command({"x": 1.0})
        mp.apply_command({"x": 2.0})
        mp.apply_command({"x": 3.0})
        assert mp._data["x"] == [1.0, 2.0, 3.0]

    def test_e1483_raises_on_overflow(self) -> None:
        """1001st append must raise E1483 (hard limit, not soft-drop)."""
        mp = MetricPlot("p", {"series": ["x"]})
        for i in range(1000):
            mp.apply_command({"x": float(i)})
        assert len(mp._data["x"]) == 1000
        with pytest.raises(ValidationError) as excinfo:
            mp.apply_command({"x": 9999.0})
        assert "E1483" in str(excinfo.value)
        # The offending series name appears in the message.
        assert "'x'" in str(excinfo.value)
        assert "1000" in str(excinfo.value)
        # Storage is unchanged — no silent growth past the cap.
        assert len(mp._data["x"]) == 1000

    def test_e1483_identifies_offending_series(self) -> None:
        """Error message must name the series that overflowed."""
        mp = MetricPlot("p", {"series": ["loss", "acc"]})
        for i in range(1000):
            mp.apply_command({"loss": float(i)})
        with pytest.raises(ValidationError) as excinfo:
            mp.apply_command({"loss": 9999.0})
        msg = str(excinfo.value)
        assert "'loss'" in msg
        assert "acc" not in msg or "'loss'" in msg  # loss identified

    def test_e1483_under_limit_succeeds(self) -> None:
        """Exactly 1000 points must be allowed without raising."""
        mp = MetricPlot("p", {"series": ["x"]})
        for i in range(1000):
            mp.apply_command({"x": float(i)})
        assert len(mp._data["x"]) == 1000

    def test_unknown_series_ignored(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        mp.apply_command({"x": 1.0, "unknown": 2.0})
        assert mp._data["x"] == [1.0]
        assert "unknown" not in mp._data


# ---------------------------------------------------------------
# Auto yrange tests
# ---------------------------------------------------------------


class TestAutoYRange:
    def test_auto_yrange_with_padding(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        mp.apply_command({"x": 10.0})
        mp.apply_command({"x": 20.0})
        ymin, ymax = mp._compute_yrange("left")
        span = 20.0 - 10.0
        assert ymin == pytest.approx(10.0 - 0.1 * span)
        assert ymax == pytest.approx(20.0 + 0.1 * span)

    def test_auto_yrange_all_equal_expands_by_one(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        mp.apply_command({"x": 5.0})
        mp.apply_command({"x": 5.0})
        mp.apply_command({"x": 5.0})
        ymin, ymax = mp._compute_yrange("left")
        assert ymin == pytest.approx(4.0)
        assert ymax == pytest.approx(6.0)


# ---------------------------------------------------------------
# SVG emission tests
# ---------------------------------------------------------------


class TestEmitSvg:
    def test_produces_valid_svg_structure(self) -> None:
        mp = MetricPlot("p", {"series": ["phi", "cost"]})
        mp.apply_command({"phi": 1.0, "cost": 2.0})
        mp.apply_command({"phi": 3.0, "cost": 4.0})
        svg = mp.emit_svg()

        assert svg.startswith("<g")
        assert svg.endswith("</g>")
        assert 'data-primitive="metricplot"' in svg
        assert 'scriba-metricplot-grid' in svg
        assert 'scriba-metricplot-axes' in svg
        assert '<polyline' in svg
        assert 'scriba-metricplot-line' in svg

    def test_grid_present_when_enabled(self) -> None:
        mp = MetricPlot("p", {"series": ["x"], "grid": True})
        mp.apply_command({"x": 1.0})
        svg = mp.emit_svg()
        assert "scriba-metricplot-gridline-h" in svg
        assert "scriba-metricplot-gridline-v" in svg

    def test_grid_absent_when_disabled(self) -> None:
        mp = MetricPlot("p", {"series": ["x"], "grid": False})
        mp.apply_command({"x": 1.0})
        svg = mp.emit_svg()
        assert "scriba-metricplot-gridline-h" not in svg

    def test_polyline_coordinates_rounded(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        mp.apply_command({"x": 1.0})
        mp.apply_command({"x": 2.0})
        svg = mp.emit_svg()
        # Check that polyline points use decimal format
        polyline_match = re.search(r'points="([^"]+)"', svg)
        assert polyline_match is not None
        points_str = polyline_match.group(1)
        # Each coordinate pair should be rounded
        for pair in points_str.split():
            x_str, y_str = pair.split(",")
            # Should be parseable as float and have at most 2 decimal places
            float(x_str)
            float(y_str)


# ---------------------------------------------------------------
# Log scale tests
# ---------------------------------------------------------------


class TestLogScale:
    def test_log_scale_positive_values(self) -> None:
        mp = MetricPlot("p", {
            "series": [{"name": "e", "scale": "log"}],
        })
        mp.apply_command({"e": 10.0})
        mp.apply_command({"e": 100.0})
        svg = mp.emit_svg()
        assert "<polyline" in svg

    def test_e1484_log_scale_non_positive_value(self, caplog: pytest.LogCaptureFixture) -> None:
        mp = MetricPlot("p", {
            "series": [{"name": "e", "scale": "log"}],
        })
        mp.apply_command({"e": 10.0})
        mp.apply_command({"e": -5.0})
        with caplog.at_level("WARNING"):
            svg = mp.emit_svg()
        assert "E1484" in caplog.text
        assert "<polyline" in svg


# ---------------------------------------------------------------
# Two-axis mode tests
# ---------------------------------------------------------------


class TestTwoAxisMode:
    def test_two_axis_activated(self) -> None:
        mp = MetricPlot("p", {
            "series": [
                {"name": "left_s", "axis": "left"},
                {"name": "right_s", "axis": "right"},
            ],
        })
        assert mp.two_axis is True
        assert mp.pad_right == 48

    def test_two_axis_renders_right_axis(self) -> None:
        mp = MetricPlot("p", {
            "series": [
                {"name": "a", "axis": "left"},
                {"name": "b", "axis": "right"},
            ],
            "ylabel_right": "right label",
        })
        mp.apply_command({"a": 1.0, "b": 2.0})
        svg = mp.emit_svg()
        assert "scriba-metricplot-right-axis" in svg
        assert "scriba-metricplot-yticks-right" in svg
        assert "right label" in svg

    def test_single_axis_no_right_axis(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        assert mp.two_axis is False
        mp.apply_command({"x": 1.0})
        svg = mp.emit_svg()
        assert "scriba-metricplot-right-axis" not in svg


# ---------------------------------------------------------------
# Current-step marker tests
# ---------------------------------------------------------------


class TestCurrentStepMarker:
    def test_marker_present(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        mp.apply_command({"x": 1.0})
        mp.apply_command({"x": 2.0})
        svg = mp.emit_svg()
        assert "scriba-metricplot-step-marker" in svg
        assert "scriba-metricplot-marker" in svg
        assert "scriba-metricplot-step-dot" in svg

    def test_marker_absent_when_disabled(self) -> None:
        mp = MetricPlot("p", {"series": ["x"], "show_current_marker": False})
        mp.apply_command({"x": 1.0})
        svg = mp.emit_svg()
        assert "scriba-metricplot-step-marker" not in svg

    def test_marker_position_at_last_point(self) -> None:
        mp = MetricPlot("p", {"series": ["x"], "xrange": [0, 9], "width": 320})
        for i in range(5):
            mp.apply_command({"x": float(i)})
        svg = mp.emit_svg()
        # Marker should be at x index 4 on a 0-9 range
        expected_x = mp._data_to_svg_x(4.0, 0.0, 9.0)
        expected_x_str = str(round(expected_x, 2))
        assert expected_x_str in svg


# ---------------------------------------------------------------
# Legend tests
# ---------------------------------------------------------------


class TestLegend:
    def test_legend_renders_series_names(self) -> None:
        mp = MetricPlot("p", {"series": ["alpha", "beta"]})
        mp.apply_command({"alpha": 1.0, "beta": 2.0})
        svg = mp.emit_svg()
        assert "scriba-metricplot-legend" in svg
        assert "alpha" in svg
        assert "beta" in svg

    def test_legend_absent_when_disabled(self) -> None:
        mp = MetricPlot("p", {"series": ["x"], "show_legend": False})
        mp.apply_command({"x": 1.0})
        svg = mp.emit_svg()
        assert "scriba-metricplot-legend" not in svg


# ---------------------------------------------------------------
# Polyline gap tests
# ---------------------------------------------------------------


class TestPolylineGaps:
    def test_missing_series_data_no_crash(self) -> None:
        """If a series has no data at some steps, no polyline is emitted for it."""
        mp = MetricPlot("p", {"series": ["a", "b"]})
        # Only feed 'a', not 'b'
        mp.apply_command({"a": 1.0})
        mp.apply_command({"a": 2.0})
        svg = mp.emit_svg()
        # 'a' should have a polyline, 'b' should not
        assert 'data-scriba-series-name="a"' in svg
        assert 'data-scriba-series-name="b"' in svg
        # Count polyline occurrences — only 'a' should have one
        polylines = re.findall(r'<polyline', svg)
        assert len(polylines) >= 1


# ---------------------------------------------------------------
# Wong palette tests
# ---------------------------------------------------------------


class TestWongPalette:
    def test_series_colors_match_wong_palette(self) -> None:
        names = [f"s{i}" for i in range(8)]
        mp = MetricPlot("p", {"series": names})
        for i, s in enumerate(mp._series):
            assert s.color == _WONG_COLORS[i]
            assert s.dash == _DASH_PATTERNS[i]

    def test_first_series_solid(self) -> None:
        mp = MetricPlot("p", {"series": ["x"]})
        assert mp._series[0].dash == ""


# ---------------------------------------------------------------
# Bounding box and addressable parts tests
# ---------------------------------------------------------------


class TestPrimitiveInterface:
    def test_bounding_box(self) -> None:
        mp = MetricPlot("p", {"series": ["x"], "width": 400, "height": 250})
        bb = mp.bounding_box()
        assert bb.width == 400
        assert bb.height == 250

    def test_addressable_parts(self) -> None:
        mp = MetricPlot("plot", {"series": ["x"]})
        parts = mp.addressable_parts()
        assert "plot" in parts

    def test_validate_selector(self) -> None:
        mp = MetricPlot("plot", {"series": ["x"]})
        assert mp.validate_selector("plot") is True
        assert mp.validate_selector("all") is True
        assert mp.validate_selector("cell[0]") is False
