"""Multi-line pill labels must be vertically centered in their pill.

The centered-first-baseline fix (first tspan dy = -line_height*(n-1)/2)
landed only in the position-label copy of the tspan emitter; the arc-label
and plain-arrow copies kept the old "first line AT fi_y, grow downward"
behaviour, so their >=3-line labels overflow the pill bottom (the pill rect
is centered on fi_y but the text block is not).

All three paths now share one emitter; these tests pin the centered layout
for each caller.
"""

from __future__ import annotations

import re

from scriba.animation.primitives.array import ArrayPrimitive

_TSPAN_DY_RE = re.compile(r'<tspan x="[-\d.]+" dy="(-?[\d.]+)">')

_THREE_LINE_LABEL = "so sánh phần tử rồi hoán đổi vị trí ngay lập tức"


def _first_dys(svg: str) -> list[float]:
    """First tspan dy of every multi-line label block in *svg*."""
    out: list[float] = []
    for text_block in re.findall(r"<text [^>]*>((?:<tspan[^>]*>.*?</tspan>)+)</text>", svg):
        dys = _TSPAN_DY_RE.findall(text_block)
        if len(dys) >= 2:
            out.append(float(dys[0]))
    return out


def _annotate(prim, target: str, **kv) -> None:
    prim.set_annotations(prim._annotations + [{"target": target, **kv}])


def test_arc_label_multiline_block_is_centered() -> None:
    arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
    _annotate(arr, "a.cell[6]", label=_THREE_LINE_LABEL, arrow_from="a.cell[1]")
    firsts = _first_dys(arr.emit_svg())
    assert firsts, "expected a multi-line label block"
    assert all(dy < 0 for dy in firsts), (
        f"first tspan dy must lift the block by half its height, got {firsts}"
    )


def test_plain_arrow_multiline_block_is_centered() -> None:
    arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
    _annotate(arr, "a.cell[3]", label=_THREE_LINE_LABEL, arrow=True)
    firsts = _first_dys(arr.emit_svg())
    assert firsts, "expected a multi-line label block"
    assert all(dy < 0 for dy in firsts), (
        f"first tspan dy must lift the block by half its height, got {firsts}"
    )


def test_position_pill_multiline_block_stays_centered() -> None:
    arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
    _annotate(arr, "a.cell[3]", label=_THREE_LINE_LABEL, position="above")
    firsts = _first_dys(arr.emit_svg())
    assert firsts, "expected a multi-line label block"
    assert all(dy < 0 for dy in firsts)


def test_all_three_paths_agree_on_layout() -> None:
    # Same label, three annotation kinds — the first-dy magnitude must be the
    # same formula (line_height * (n-1) / 2) in every path.
    results: dict[str, float] = {}
    for kind, kv in {
        "arc": {"arrow_from": "a.cell[1]"},
        "plain": {"arrow": True},
        "position": {"position": "above"},
    }.items():
        arr = ArrayPrimitive("a", {"size": 8, "data": list(range(8))})
        _annotate(arr, "a.cell[6]", label=_THREE_LINE_LABEL, **kv)
        firsts = _first_dys(arr.emit_svg())
        assert firsts, kind
        results[kind] = firsts[0]
    assert len(set(results.values())) == 1, results
