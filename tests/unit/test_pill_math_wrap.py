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


class TestScribaSansTextFace:
    """spec-fix-annot-pill-face-scriba-sans: annotation pill/link/note labels
    measure their text runs in the house "Scriba Sans" oracle (Inter subset,
    full Vietnamese coverage) — the same face cells use — so a mixed
    ``$math$ · text`` label pairs KaTeX math with the diagram's text voice, no
    serif/mono zebra. The switch is opt-in (``text_face``): the default mono
    path stays byte-identical for every non-pill caller."""

    def test_mixed_label_width_is_scriba_sans_plus_katex_math(self) -> None:
        from scriba.animation.primitives._math_metrics import measure_inline_math
        from scriba.animation.primitives._text_metrics import (
            measure_label_line,
            measure_text_run,
        )

        label = "$1 < 3$ · exit"
        got = measure_label_line(label, 11, text_face="scriba-sans")
        # split mirrors _render_mixed_html: math "1 < 3", trailing text " · exit".
        # Float math advance + float Inter run summed, then rounded ONCE at the
        # line level (additive, no per-segment double rounding).
        expected = measure_inline_math("1 < 3", 11) + measure_text_run(" · exit", 11)
        assert got == int(expected + 0.5)

    def test_plain_text_label_uses_scriba_sans_oracle(self) -> None:
        from scriba.animation.primitives._text_metrics import (
            measure_label_line,
            measure_text_run,
        )

        label = "1 < 3 · exit"
        assert measure_label_line(label, 11, text_face="scriba-sans") == int(
            measure_text_run(label, 11) + 0.5
        )

    def test_default_face_is_mono_and_byte_identical(self) -> None:
        from scriba.animation.primitives._text_metrics import measure_label_line
        from scriba.animation.primitives._text_render import estimate_text_width

        # plain text: default must equal the legacy mono heuristic exactly
        assert measure_label_line("exit here", 11) == estimate_text_width(
            "exit here", 11
        )
        assert measure_label_line("$1 < 3$ · exit", 11) != measure_label_line(
            "$1 < 3$ · exit", 11, text_face="scriba-sans"
        )

    def test_vietnamese_fully_covered_no_heuristic(self) -> None:
        # "đã thăm": every glyph lives in the Inter subset, so the run measures
        # by pure advance-sum — no symbol_em/heuristic fallback, no mono zebra.
        import unicodedata

        from scriba.animation.primitives._text_metrics import (
            ShippedFontMeasurer,
            get_measurer,
        )

        m = get_measurer()
        assert isinstance(m, ShippedFontMeasurer), "Inter table not vendored"
        for ch in unicodedata.normalize("NFC", "đã thăm"):
            if ch == " ":
                continue
            assert ord(ch) in m._advances, (
                f"{ch!r} outside Inter subset — would fall back and zebra"
            )

    def test_nfc_decomposed_equals_precomposed(self) -> None:
        import unicodedata

        from scriba.animation.primitives._text_metrics import (
            measure_label_line,
            measure_text_run,
        )

        pre = "đã thăm"
        dec = unicodedata.normalize("NFD", pre)
        assert dec != pre  # sanity: NFD really decomposes ã / ă
        assert measure_text_run(dec, 11) == measure_text_run(pre, 11)
        assert measure_label_line(
            dec, 11, text_face="scriba-sans"
        ) == measure_label_line(pre, 11, text_face="scriba-sans")

    def test_uncovered_glyph_fallback_never_zero(self) -> None:
        from scriba.animation.primitives._text_metrics import measure_text_run

        # math ops (→ ≤) live in KaTeX's tables (symbol_em); CJK falls to the
        # display-width heuristic — both stay > 0 (never clip, over-ok)
        for uncovered in ("→", "≤", "中"):
            assert measure_text_run(uncovered, 11) > 0.0

    def test_scriba_sans_pill_covers_painted_text(self) -> None:
        # the mixed-label pill (math_rendered=True measures scriba-sans) must be
        # at least as wide as the WHOLE thing it paints: the KaTeX math box plus
        # the full scriba-sans text run plus both pill pads. int() single-rounds
        # the summed advance, so allow its ≤0.5px slack — still far tighter than
        # the trivially-true text-run-only bound.
        from scriba.animation.primitives._math_metrics import measure_inline_math
        from scriba.animation.primitives._svg_helpers import _LABEL_PILL_PAD_X
        from scriba.animation.primitives._text_metrics import measure_text_run

        lines, _, pill_w, _ = pill_dimensions("$1 < 3$ · exit", 11)
        assert lines == ["$1 < 3$ · exit"]  # single line → bound below is exact
        painted = measure_inline_math("1 < 3", 11) + measure_text_run(" · exit", 11)
        assert pill_w >= painted + 2 * _LABEL_PILL_PAD_X - 0.5

    def test_all_arrow_kinds_weight_clamped_synthesis_free(self) -> None:
        # A1: good/path drop 700 -> 600 so the static 400 master renders without
        # faux-bold synthesis (advances == baked table == exact measurement).
        # P6a: the ≤600 invariant must hold for EVERY kind, not just good/path —
        # any 700 would synthesize a heavier face whose advances exceed the baked
        # table → under-measure → clipped labels. (CSS font-synthesis:none is the
        # paint-side fail-safe; this asserts the source-side invariant.)
        from scriba.animation.primitives._svg_helpers import ARROW_STYLES

        assert ARROW_STYLES  # guard: an empty dict would vacuously "pass"
        for kind, style in ARROW_STYLES.items():
            assert int(style["label_weight"]) <= 600, kind

    def test_middot_measured_via_inter_table(self) -> None:
        # P6b: · (U+00B7) IS in the Inter subset, so the run measures it by
        # advance-sum — no symbol_em/heuristic fallback — and stays > 0.
        from scriba.animation.primitives._text_metrics import (
            ShippedFontMeasurer,
            get_measurer,
            measure_text_run,
        )

        m = get_measurer()
        assert isinstance(m, ShippedFontMeasurer), "Inter table not vendored"
        assert ord("·") in m._advances  # table hit, not a symbol_em/heuristic miss
        assert measure_text_run("·", 11) > 0.0

    def test_missing_glyph_conservative_floor(self) -> None:
        # P3: a math/relation glyph absent from the Inter table (Sm/So) is
        # PAINTED by the CSS tail's system UI sans (~0.9em), wider than KaTeX's
        # symbol advance. measure_text_run (the annotation entry) opts into the
        # conservative floor so the pill never clips; the cell oracle
        # (measure_text, conservative_symbols=False) stays byte-identical.
        from scriba.animation.primitives._text_metrics import (
            get_measurer,
            measure_text,
            measure_text_run,
        )

        m = get_measurer()
        fp = 11
        for ch in ("≮", "→"):  # both Sm, both absent from the Inter subset
            w = measure_text_run(ch, fp)
            assert w >= 0.9 * fp - 1e-9, (ch, w)  # floored to the UI-sans em
            assert w > 0.0  # never zero
        # ≮ (KaTeX 0.778em) is raised by the 0.9em floor; the cell path is NOT.
        raw = m.measure_run("≮", fp, conservative_symbols=False)
        assert measure_text_run("≮", fp) > raw
        assert measure_text("≮", fp) == int(raw + 0.5)  # cells unchanged

    def test_caps_heavy_label_packs_with_sans_ruler(self) -> None:
        # P2: pill packing must use the SAME ruler the final width is measured
        # against. A caps-heavy label packs one line under the mono ruler (≤132)
        # but paints far wider in scriba-sans (>132); before the fix that
        # over-wide single line spilled the pill past its budget.
        from scriba.animation.primitives._svg_helpers import (
            _LABEL_PILL_MAX_W_PX,
            _LABEL_PILL_PAD_X,
            _wrap_label_lines,
        )
        from scriba.animation.primitives._text_metrics import measure_label_line

        label = "WORKING WM MEMO WWW"
        # fixture validity: mono ruler keeps it one line, sans ruler cannot
        assert (
            len(
                _wrap_label_lines(
                    label, max_px=132, font_px=11, math_rendered=True,
                    text_face="mono",
                )
            )
            == 1
        )
        assert measure_label_line(label, 11, text_face="scriba-sans") > 132

        # the fix: pill_dimensions packs in the scriba-sans face it measures
        lines, _, pill_w, _ = pill_dimensions(
            label, 11, wrap_px=132, math_rendered=True
        )
        assert len(lines) >= 2
        assert (
            max(measure_label_line(ln, 11, text_face="scriba-sans") for ln in lines)
            <= 132
        )
        assert pill_w <= _LABEL_PILL_MAX_W_PX + 2 * _LABEL_PILL_PAD_X


class TestNoCallbackPillSizing:
    """folabel-sweep-measure-callers BUG B: without render_inline_tex the
    emitter paints the RAW $...$ string in mono, so the pill must be sized
    from the raw string too — browser-measured $dp_{i}$ painted 40.5px into
    a 29px KaTeX-model pill (+11.5px overhang)."""

    def test_pill_dimensions_raw_mode_measures_painted_string(self) -> None:
        from scriba.animation.primitives._svg_helpers import pill_dimensions
        from scriba.animation.primitives._text_render import (
            estimate_text_width,
            strip_math_markup,
        )

        label = "$dp_{i}$"
        _, _, w_raw, _ = pill_dimensions(label, 11, math_rendered=False)
        # the fallback paints the STRIPPED form ("dp_i"), so the pill
        # covers exactly that
        assert w_raw >= estimate_text_width(strip_math_markup(label), 11)

    def test_no_callback_emit_pill_wraps_painted_text(self) -> None:
        import re

        from scriba.animation.primitives.array import ArrayPrimitive
        from scriba.animation.primitives._text_render import estimate_text_width

        arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
        _annotate(arr, "a.cell[6]", label="$dp_{i}$", position="below")
        svg = arr.emit_svg()  # no KaTeX
        rects = re.findall(r'<rect [^>]*width="(\d+)"[^>]*rx="', svg)
        assert rects
        pill_w = max(int(w) for w in rects)
        # fallback paints stripped "dp_i" (no $ noise) — pill covers it
        from scriba.animation.primitives._text_render import strip_math_markup

        painted = estimate_text_width(strip_math_markup("$dp_{i}$"), 11)
        assert pill_w >= painted, (pill_w, painted)
        assert "$" not in re.sub(r"aria-[a-z]+=\"[^\"]*\"", "", svg)
