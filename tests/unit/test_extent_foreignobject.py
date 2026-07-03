"""Extent parsers must see <foreignObject> boxes (the FO-blindness CI hole).

Both parsers matched only g|rect|circle|polygon|polyline|line|path, so a
foreignObject — the element every math label paints through — was invisible
to the painted⊆bbox honesty pins and to production reservation measurement
(investigations/folabel-emit-honesty.md: stripping every FO from a real
emit left the measured extent byte-identical).
"""

from __future__ import annotations

import sys

sys.path.insert(0, "tests")
from helpers.painted_extent import painted_extent  # noqa: E402

from scriba.animation.primitives._extent import measure_painted_extent


_SVG = (
    '<g transform="translate(10, 20)">'
    '<rect x="0" y="0" width="50" height="30"/>'
    '<foreignObject x="40" y="25" width="100" height="18">'
    '<div xmlns="http://www.w3.org/1999/xhtml">x</div>'
    "</foreignObject>"
    "</g>"
)


class TestForeignObjectCounted:
    def test_production_parser_includes_fo_box(self) -> None:
        ext = measure_painted_extent(_SVG)
        assert ext.max_x >= 10 + 40 + 100 - 0.01  # FO right edge
        assert ext.max_y >= 20 + 25 + 18 - 0.01  # FO bottom edge

    def test_test_twin_includes_fo_box(self) -> None:
        ext = painted_extent(_SVG)
        assert ext.max_x >= 150 - 0.01
        assert ext.max_y >= 63 - 0.01

    def test_parsers_agree_on_fo(self) -> None:
        a = measure_painted_extent(_SVG)
        b = painted_extent(_SVG)
        assert abs(a.max_x - b.max_x) < 0.01
        assert abs(a.max_y - b.max_y) < 0.01
