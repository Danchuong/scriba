"""Math-in-caption rendering: wrap, whitespace, per-line KaTeX boxes.

Bug class (v0.21.1): a ``label=`` caption containing ``$...$`` never wrapped
("Math captions are never wrapped" in ``_caption_lines``) and rendered inside
a single fixed ``footprint×20`` ``<foreignObject>`` whose ``display:flex`` div
ate the whitespace around inline-math spans and vertically clipped any label
taller than one line.

Fixed behaviour under test:

- ``_caption_lines`` wraps math captions through ``_wrap_label_lines`` (which
  is already ``$...$``-safe) instead of returning them as one long line.
- ``_emit_caption`` renders a wrapped math caption one line per
  ``_render_svg_text`` call so each line keeps the KaTeX foreignObject path.
- ``_render_svg_text``'s foreignObject path drops ``display:flex`` (whitespace
  around math spans survives), pins ``white-space:nowrap`` +
  ``line-height:{h}px`` (single-line semantics, vertical centering), and
  carries ``css_class`` / ``font-size`` like the ``<text>`` fast path does.
- ``_caption_block_height``/``_caption_block_width`` reserve bbox space for
  the wrapped math block (math line height, ``$``-stripped measurement).
"""

from __future__ import annotations

import re

from scriba.animation.primitives._text_render import (
    _render_svg_text,
    estimate_text_width,
)
from scriba.animation.primitives._svg_helpers import (
    _label_width_text,
    _wrap_label_lines,
)
from scriba.animation.primitives.base import (
    _CAPTION_FONT_PX,
    _CAPTION_SAFETY_PAD,
    _CELL_HORIZONTAL_PADDING,
    _MATH_CAPTION_LINE_H,
)
from scriba.animation.primitives.grid import GridPrimitive


def _fake_tex(fragment: str) -> str:
    """Stand-in for the KaTeX callback: ``$x$`` -> ``<span class="fake-katex">x</span>``."""
    return f'<span class="fake-katex">{fragment.strip("$")}</span>'


# Same shape as the caption that surfaced the bug (Number Spiral editorial).
_LONG_MATH_LABEL = (
    "5 lớp đầu: hàng y xuống dưới, cột x sang phải. "
    "Lớp m chứa các số nguyên $(m-1)^2+1$ tới $m^2$."
)


def _grid(label: str) -> GridPrimitive:
    return GridPrimitive("g", {"rows": 5, "cols": 5, "label": label})


# ---------------------------------------------------------------------------
# _render_svg_text — foreignObject box styling
# ---------------------------------------------------------------------------


class TestForeignObjectBox:
    def test_whitespace_around_math_preserved_no_flex(self) -> None:
        out = _render_svg_text(
            "a $x$ b",
            100,
            10,
            fo_width=200,
            fo_height=20,
            render_inline_tex=_fake_tex,
        )
        assert "<foreignObject" in out
        # flex made every text node / span a flex item and discarded the
        # whitespace between them — the div must be a normal inline flow.
        assert "display:flex" not in out
        assert 'a <span class="fake-katex">x</span> b' in out

    def test_single_line_box_nowrap_and_line_height_centering(self) -> None:
        out = _render_svg_text(
            "a $x$ b",
            100,
            10,
            fo_width=200,
            fo_height=20,
            render_inline_tex=_fake_tex,
        )
        assert "white-space:nowrap" in out
        assert "line-height:20px" in out

    def test_css_class_carried_on_foreignobject(self) -> None:
        out = _render_svg_text(
            "$x$",
            0,
            0,
            css_class="scriba-primitive-label",
            fo_width=100,
            fo_height=20,
            render_inline_tex=_fake_tex,
        )
        assert 'class="scriba-primitive-label"' in out

    def test_font_size_applied_to_div(self) -> None:
        out = _render_svg_text(
            "$x$",
            0,
            0,
            font_size="11",
            fo_width=100,
            fo_height=20,
            render_inline_tex=_fake_tex,
        )
        assert "font-size:11px" in out

    def test_plain_text_fast_path_untouched(self) -> None:
        out = _render_svg_text("plain", 5, 7, fill="#123456")
        assert out == '<text x="5" y="7" fill="#123456">plain</text>'


# ---------------------------------------------------------------------------
# _caption_lines — math captions wrap
# ---------------------------------------------------------------------------


class TestCaptionLinesMathWrap:
    def test_long_math_label_wraps(self) -> None:
        lines = _grid(_LONG_MATH_LABEL)._caption_lines(320.0)
        assert len(lines) >= 2

    def test_math_fragments_never_split_across_lines(self) -> None:
        lines = _grid(_LONG_MATH_LABEL)._caption_lines(320.0)
        for ln in lines:
            assert ln.count("$") % 2 == 0, f"split math fragment in {ln!r}"

    def test_wrap_preserves_content(self) -> None:
        lines = _grid(_LONG_MATH_LABEL)._caption_lines(320.0)
        assert " ".join(lines).split() == _LONG_MATH_LABEL.split()

    def test_short_math_label_stays_single_line(self) -> None:
        lines = _grid("nhãn $m^2$")._caption_lines(320.0)
        assert lines == ["nhãn $m^2$"]

    def test_plain_label_wrap_unchanged(self) -> None:
        plain = (
            "một nhãn thuần văn bản đủ dài để buộc phải xuống dòng "
            "khi bề rộng nội dung chỉ có ba trăm hai mươi pixel"
        )
        assert _grid(plain)._caption_lines(320.0) == _wrap_label_lines(
            plain, max_px=320.0, font_px=_CAPTION_FONT_PX
        )


# ---------------------------------------------------------------------------
# bbox reservation — block height / width for math captions
# ---------------------------------------------------------------------------


class TestCaptionBlockMetrics:
    def test_block_height_uses_math_line_height(self) -> None:
        from scriba.animation.primitives._text_metrics import label_line_extra

        inst = _grid(_LONG_MATH_LABEL)
        lines = inst._caption_lines(320.0)
        n = len(lines)
        assert n >= 2
        # per-line adaptive: base box + tall-math extra per line (the fixed
        # 18px box clipped 16/20 bench fragments — TestTallMathExtra truth)
        expected = sum(
            _MATH_CAPTION_LINE_H + label_line_extra(ln, _CAPTION_FONT_PX)
            for ln in lines
        )
        assert inst._caption_block_height(320.0) == expected
        assert inst._caption_block_height(320.0) >= n * _MATH_CAPTION_LINE_H

    def test_block_height_plain_unchanged(self) -> None:
        inst = _grid("nhãn ngắn")
        assert inst._caption_block_height(320.0) == _CAPTION_FONT_PX + 2

    def test_block_width_measures_via_measure_label_line(self) -> None:
        # Math lines measure through the exact composer (KaTeX advance-sum
        # for $...$ segments) — NOT the raw line, NOT the old x1.15 strip.
        from scriba.animation.primitives._text_metrics import measure_label_line

        line = "x $aa$ y"
        exact_w = measure_label_line(line, _CAPTION_FONT_PX)
        raw_w = estimate_text_width(line, _CAPTION_FONT_PX)
        assert exact_w != raw_w  # guard: the two measurements differ
        w = _grid(line)._caption_block_width(320.0)
        assert w == int(
            exact_w + 2 * _CELL_HORIZONTAL_PADDING + _CAPTION_SAFETY_PAD
        )


# ---------------------------------------------------------------------------
# _emit_caption — one KaTeX-capable box per wrapped line
# ---------------------------------------------------------------------------

_FO_RE = re.compile(r'<foreignObject[^>]*y="(-?\d+)"[^>]*>')
# Caption line elements: math lines are foreignObject (y = TOP edge), plain
# lines inside a math block are <text> with dominant-baseline central
# (y = CENTER). Normalise both to center-y before comparing the stack.
_CAPTION_LINE_RE = re.compile(
    r'<(foreignObject|text) class="scriba-primitive-label"[^>]*y="(-?\d+)"'
)


def _caption_center_ys(svg: str) -> list[int]:
    ys: list[int] = []
    for tag, y in _CAPTION_LINE_RE.findall(svg):
        y = int(y)
        ys.append(y + _MATH_CAPTION_LINE_H // 2 if tag == "foreignObject" else y)
    return ys


class TestEmitCaptionMathMultiline:
    def test_each_math_line_gets_a_foreignobject(self) -> None:
        inst = _grid(_LONG_MATH_LABEL)
        svg = inst.emit_svg(render_inline_tex=_fake_tex)
        n_lines = len(inst._caption_lines(inst.bounding_box().width))
        assert svg.count('<foreignObject') >= 1
        assert "fake-katex" in svg
        # every wrapped line is emitted — no raw $...$ survives when a
        # renderer callback is available
        assert "$(m-1)^2+1$" not in svg
        assert "$m^2$" not in svg
        assert n_lines >= 2

    def test_caption_lines_stack_by_math_line_height(self) -> None:
        inst = _grid(_LONG_MATH_LABEL)
        svg = inst.emit_svg(render_inline_tex=_fake_tex)
        # read the emitted caption FO boxes directly: adaptive heights must
        # stack without overlap — each next top = previous top + previous
        # height — and every box is at least the base math line box
        boxes = [
            (int(m.group(1)), int(m.group(2)))
            for m in re.finditer(
                r'<foreignObject x="[^"]*" y="(-?\d+)" width="\d+" '
                r'height="(\d+)"[^>]*class="scriba-fo-line"',
                svg,
            )
        ]
        if not boxes:  # fall back: any caption FO emitted by _render_svg_text
            boxes = [
                (int(m.group(1)), int(m.group(2)))
                for m in re.finditer(
                    r'<foreignObject[^>]* y="(-?\d+)"[^>]* height="(\d+)"',
                    svg,
                )
            ]
        assert len(boxes) >= 2
        assert all(h >= _MATH_CAPTION_LINE_H for _, h in boxes)
        for (y0, h0), (y1, _h1) in zip(boxes, boxes[1:]):
            assert y1 - y0 == h0  # cumulative, no overlap

    def test_plain_lines_in_math_block_are_middle_anchored(self) -> None:
        # Plain <text> lines rely on inline text-anchor — the CSS
        # direct-child rule does not reach every embedding context, and
        # without it the line renders start-anchored from center_x and
        # overflows the right edge.
        inst = _grid(_LONG_MATH_LABEL)
        svg = inst.emit_svg(render_inline_tex=_fake_tex)
        plain_lines = re.findall(
            r'<text class="scriba-primitive-label"[^>]*>', svg
        )
        assert plain_lines
        for tag in plain_lines:
            assert "text-anchor:middle" in tag

    def test_no_callback_falls_back_to_wrapped_text(self) -> None:
        inst = _grid(_LONG_MATH_LABEL)
        svg = inst.emit_svg()
        # no KaTeX available: still wrapped (multi-line), no foreignObject
        assert "<foreignObject" not in svg
        assert svg.count("<tspan") >= 2

    def test_array_long_math_caption_renders_katex_not_raw_dollars(self) -> None:
        # Array kept a bespoke caption emitter (predating the shared Layer-A
        # helper). Once _caption_lines started wrapping math, its multi-line
        # branch escaped the raw $...$ into tspans instead of rendering KaTeX.
        from scriba.animation.primitives.array import ArrayPrimitive

        inst = ArrayPrimitive("a", {"size": 4, "data": [1, 2, 3, 4]})
        inst.label = _LONG_MATH_LABEL
        svg = inst.emit_svg(render_inline_tex=_fake_tex)
        assert "$(m-1)^2+1$" not in svg
        assert "$m^2$" not in svg
        assert "fake-katex" in svg
        ys = _caption_center_ys(svg)
        assert len(ys) >= 2

    def test_array_math_caption_bbox_reserves_math_line_height(self) -> None:
        from scriba.animation.primitives.array import ArrayPrimitive

        plain = ArrayPrimitive("a", {"size": 4, "data": [1, 2, 3, 4]})
        mathy = ArrayPrimitive("a", {"size": 4, "data": [1, 2, 3, 4]})
        plain.label = "x"
        mathy.label = "$x$ " + "dài " * 40  # forces a wrapped math block
        from scriba.animation.primitives._text_metrics import label_line_extra

        lines = mathy._caption_lines(mathy._total_width())
        n = len(lines)
        assert n >= 2
        block = sum(
            _MATH_CAPTION_LINE_H + label_line_extra(ln, _CAPTION_FONT_PX)
            for ln in lines
        )
        delta = mathy.bounding_box().height - plain.bounding_box().height
        assert delta == block - (_CAPTION_FONT_PX + 2)

    def test_caption_does_not_overhang_grid_rows(self) -> None:
        # The old fixed 673×20 box started at the grid's last row; the new
        # per-line boxes must sit fully below the content (top_y >= rows px).
        inst = _grid(_LONG_MATH_LABEL)
        svg = inst.emit_svg(render_inline_tex=_fake_tex)
        content_h = inst.rows * 42 - 4  # CELL_HEIGHT 38 + gap 4 per row
        ys = [int(m.group(1)) for m in _FO_RE.finditer(svg)]
        assert ys and all(y >= content_h for y in ys)
