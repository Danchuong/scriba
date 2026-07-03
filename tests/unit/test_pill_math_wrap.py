"""Math-bearing pill labels: wrap like plain labels, render KaTeX per line.

Legacy behaviour exempted any ``$...$`` label from wrapping ("would split
inside $...$" — but ``_wrap_label_lines`` is $-safe), so a long mixed label
became one over-wide single-line pill spilling across neighbour cells.

Fixed behaviour under test:
- mixed text+math labels wrap through the same ``$``-safe wrapper as plain
  labels (an unbreakable single ``$...$`` fragment stays one line);
- a multi-line block containing math renders every line as a KaTeX-capable
  foreignObject (non-flex, whitespace-preserving) instead of escaping the
  raw ``$`` into tspans;
- pill dimensions come from one shared helper (``pill_dimensions``) used by
  emit and measurement alike, with a taller line box for math lines;
- the arc's natural label anchor uses the REAL pill height, not the
  hardcoded one-line 19px estimate.
"""

from __future__ import annotations

import re

from scriba.animation.primitives._svg_helpers import pill_dimensions
from scriba.animation.primitives.array import ArrayPrimitive

from tests.helpers.painted_extent import painted_extent


def _fake_tex(fragment: str) -> str:
    return f'<span class="fake-katex">{fragment.strip("$")}</span>'


# long enough to exceed the 8-cell arc wrap budget (~468px) under EXACT
# metrics too — the old heuristic over-measured +40% and wrapped earlier
_MIXED_MATH_LABEL = (
    "chuyển trạng thái $dp[i][j]$ bằng cách lấy $\\min$ của ô trên và ô trái"
    " rồi cộng thêm chi phí $c[i][j]$ của chính ô hiện tại"
)


def _annotate(prim, target: str, **kv) -> None:
    prim.set_annotations(prim._annotations + [{"target": target, **kv}])


class TestPillDimensions:
    def test_mixed_math_label_wraps(self) -> None:
        lines, line_h, pill_w, pill_h = pill_dimensions(
            _MIXED_MATH_LABEL, 11, wrap_px=132
        )
        assert len(lines) >= 2
        for ln in lines:
            assert ln.count("$") % 2 == 0, ln

    def test_single_math_fragment_stays_one_line(self) -> None:
        label = "$dp[i][j] = \\min(dp[i-1][j], dp[i][j-1]) + c$"
        lines, line_h, pill_w, pill_h = pill_dimensions(label, 11, wrap_px=132)
        assert lines == [label]
        # single-line math keeps the legacy compact pill height
        assert line_h == 11 + 2

    def test_multiline_math_uses_taller_line_box(self) -> None:
        _, line_h_math, _, _ = pill_dimensions(_MIXED_MATH_LABEL, 11, wrap_px=132)
        _, line_h_plain, _, _ = pill_dimensions(
            "một nhãn thuần văn bản đủ dài để phải xuống dòng nhiều lần", 11,
            wrap_px=132,
        )
        assert line_h_plain == 13
        assert line_h_math > line_h_plain  # KaTeX strut clearance

    def test_plain_label_unchanged(self) -> None:
        lines, line_h, pill_w, pill_h = pill_dimensions("swap", 11)
        assert lines == ["swap"]
        assert line_h == 13
        assert pill_h == 13 + 6


class TestMathPillEmission:
    def test_arc_mixed_math_label_renders_katex_lines(self) -> None:
        arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
        _annotate(arr, "a.cell[6]", label=_MIXED_MATH_LABEL, arrow_from="a.cell[1]")
        svg = arr.emit_svg(render_inline_tex=_fake_tex)
        assert "fake-katex" in svg
        # raw $ may legally remain in aria-description (R-11 keeps raw TeX
        # there) — but must not leak into any VISIBLE text node
        assert "$dp[i][j]$</tspan>" not in svg
        assert re.search(r">[^<]*\$dp\[i\]\[j\]\$[^<]*</div>", svg) is None
        assert svg.count("scriba-annot-fobj") >= 2  # one KaTeX box per line

    def test_position_mixed_math_label_wraps_and_renders(self) -> None:
        arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
        _annotate(arr, "a.cell[3]", label=_MIXED_MATH_LABEL, position="above")
        svg = arr.emit_svg(render_inline_tex=_fake_tex)
        assert "fake-katex" in svg
        assert svg.count("scriba-annot-fobj") >= 2

    def test_plain_multiline_still_tspans(self) -> None:
        arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
        _annotate(
            arr, "a.cell[6]",
            label=(
                "so sánh phần tử hiện tại với phần tử kế tiếp rồi hoán đổi "
                "vị trí của cả hai ngay lập tức trước khi quét tiếp"
            ),
            arrow_from="a.cell[1]",
        )
        svg = arr.emit_svg(render_inline_tex=_fake_tex)
        assert "scriba-annot-fobj" not in svg
        assert svg.count("<tspan") >= 2

    def test_math_pill_painted_within_bbox(self) -> None:
        arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
        _annotate(arr, "a.cell[6]", label=_MIXED_MATH_LABEL, arrow_from="a.cell[1]")
        svg = arr.emit_svg(render_inline_tex=_fake_tex)
        ext = painted_extent(svg)
        bb = arr.bounding_box()
        assert ext.min_y >= -0.01 and ext.min_x >= -0.01
        assert ext.max_x <= bb.width + 0.01
        assert ext.max_y <= bb.height + 0.01

    def test_no_callback_falls_back_to_wrapped_tspans(self) -> None:
        arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
        _annotate(arr, "a.cell[6]", label=_MIXED_MATH_LABEL, arrow_from="a.cell[1]")
        svg = arr.emit_svg()  # no KaTeX available
        assert "scriba-annot-fobj" not in svg
        assert svg.count("<tspan") >= 2  # still wrapped, raw $ shown as text
