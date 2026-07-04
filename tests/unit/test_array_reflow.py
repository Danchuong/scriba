"""Unit tests for Array insert/remove reflow + sentinel slots (Phase D v1).

Design source: ``investigations/anim-reflow-sentinel.md`` — verdict **strategy
(a), slot-identity on a fixed max-N grid (the Queue model)**. Insert/remove are
a ``value_change`` cascade inside a reserved envelope so cell *positions* never
move and **R-32** (frame-stable centering, ``_frame_renderer.py`` line 746)
holds by construction. Finalised open questions:

- **OQ2** — after ``remove`` the freed *tail* slot renders as an **empty cell**
  (keeps the grid, preserves R-32). Never an interior hole.
- **OQ1** — sentinels are the bare named parts ``before``/``after`` (mirrors
  Queue's ``front``/``rear``), excluded from ``all``/``range``.
- **OQ3** — v1 requires the author to declare ``size = max-N`` (no auto-grow);
  inserting into a full array errors rather than silently growing the envelope.
- **OQ4** — insert accepts ``at`` (preferred) and ``index`` (alias).

All tests drive :class:`ArrayPrimitive` directly — no parser/emitter layers,
mirroring ``tests/unit/test_plane2d_remove.py``.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives._types import CELL_GAP, CELL_HEIGHT, CELL_WIDTH
from scriba.core.errors import ValidationError

_PITCH = CELL_WIDTH + CELL_GAP  # cell pitch for single-digit content (cw == 60)


def _make(size: int, data=None, **extra) -> ArrayPrimitive:
    params: dict = {"size": size}
    if data is not None:
        params["data"] = list(data)
    params.update(extra)
    return ArrayPrimitive("a", params)


def _cell_rect_xs(svg: str) -> list[str]:
    """Ordered list of each cell rect's ``x`` attribute (position pins)."""
    pairs = re.findall(
        r'data-target="a\.cell\[(\d+)\]".*?<rect x="([\d.]+)"', svg, re.DOTALL
    )
    return [x for _idx, x in pairs]


def _cell_group_count(svg: str) -> int:
    return len(re.findall(r'data-target="a\.cell\[\d+\]"', svg))


# ---------------------------------------------------------------------------
# 1. remove reflows — no interior hole, freed tail is empty
# ---------------------------------------------------------------------------


def test_array_remove_reflows_no_hole() -> None:
    a = _make(5, [1, 2, 3, 4, 5])
    a.apply_command({"remove": 1})
    # value 2 removed; [3,4,5] slid left into slots 1..3; slot 4 vacated.
    assert a.data == [1, 3, 4, 5, ""]
    assert a.live == 4


# ---------------------------------------------------------------------------
# 2. insert shifts right within the fixed grid, grows live
# ---------------------------------------------------------------------------


def test_array_insert_shifts_right() -> None:
    a = _make(5, [1, 2, 3, 4])  # partial fill, live == 4 (E1402 relaxation)
    a.apply_command({"insert": {"at": 2, "value": 9}})
    assert a.data == [1, 2, 9, 3, 4]
    assert a.live == 5


def test_array_insert_index_alias() -> None:
    a = _make(5, [1, 2, 3, 4])
    a.apply_command({"insert": {"index": 0, "value": 7}})
    assert a.data == [7, 1, 2, 3, 4]
    assert a.live == 5


# ---------------------------------------------------------------------------
# 3. R-32 — bbox width is frame-invariant across insert AND remove
# ---------------------------------------------------------------------------


def test_array_reflow_bbox_frame_stable() -> None:
    a = _make(5, [1, 2, 3, 4])
    w0 = a.bounding_box().width
    a.apply_command({"insert": {"at": 1, "value": 9}})
    w1 = a.bounding_box().width
    a.apply_command({"remove": 0})
    w2 = a.bounding_box().width
    assert w0 == w1 == w2
    # equals the fixed max-N envelope, independent of live
    assert w0 == float(5 * CELL_WIDTH + 4 * CELL_GAP)


# ---------------------------------------------------------------------------
# 4. insert past the fixed size errors (do not silently grow in v1)
# ---------------------------------------------------------------------------


def test_array_insert_overflow_errors() -> None:
    a = _make(5, [1, 2, 3, 4, 5])  # full: live == size
    with pytest.raises(ValidationError, match="E1403"):
        a.apply_command({"insert": {"at": 2, "value": 9}})
    # failed insert must not mutate the array
    assert a.data == [1, 2, 3, 4, 5]
    assert a.live == 5


def test_array_insert_position_out_of_range_errors() -> None:
    a = _make(5, [1, 2, 3])  # live == 3
    with pytest.raises(ValidationError, match="E1403"):
        a.apply_command({"insert": {"at": 10, "value": 9}})


def test_array_remove_out_of_range_errors() -> None:
    a = _make(5, [1, 2, 3])  # live == 3
    with pytest.raises(ValidationError, match="E1403"):
        a.apply_command({"remove": 3})


# ---------------------------------------------------------------------------
# 5. sentinels addressable from t0, excluded from all/range
# ---------------------------------------------------------------------------


def test_array_sentinel_addressable_from_t0() -> None:
    a = _make(5, [1, 2, 3, 4, 5], sentinels=True)
    parts = a.addressable_parts()

    assert "before" in parts
    assert "after" in parts
    assert a.validate_selector("before") is True
    assert a.validate_selector("after") is True

    # excluded from all/range: still exactly `size` cell[i] parts, nothing more.
    cell_parts = [p for p in parts if re.fullmatch(r"cell\[\d+\]", p)]
    assert len(cell_parts) == 5
    assert "before" not in cell_parts and "after" not in cell_parts

    before = a.resolve_annotation_point("a.before")
    after = a.resolve_annotation_point("a.after")
    c0 = a.resolve_annotation_point("a.cell[0]")
    c4 = a.resolve_annotation_point("a.cell[4]")
    assert before is not None and after is not None
    # before sits one pitch left of cell[0]; after one pitch right of cell[live-1]
    assert c0[0] - before[0] == float(_PITCH)
    assert after[0] - c4[0] == float(_PITCH)


def test_array_sentinels_off_have_no_named_parts() -> None:
    a = _make(5, [1, 2, 3, 4, 5])  # sentinels default off
    parts = a.addressable_parts()
    assert "before" not in parts and "after" not in parts
    assert a.validate_selector("before") is False
    assert a.resolve_annotation_point("a.before") is None


# ---------------------------------------------------------------------------
# 6. R-32 — sentinels reserve 2*(cw+gap) in EVERY frame
# ---------------------------------------------------------------------------


def test_array_sentinel_reserved_envelope() -> None:
    plain = _make(5, [1, 2, 3, 4, 5])
    sent = _make(5, [1, 2, 3, 4, 5], sentinels=True)
    reserve = sent.bounding_box().width - plain.bounding_box().width
    assert reserve == float(2 * _PITCH)

    # reserve is present even after the live count shrinks (nothing parks on it)
    sent.apply_command({"remove": 0})
    assert sent.bounding_box().width == plain.bounding_box().width + float(2 * _PITCH)


# ---------------------------------------------------------------------------
# 7. GREEN guard — `hidden` is still a visual no-op (remove is the ONLY delete)
# ---------------------------------------------------------------------------


def test_array_hidden_still_noop_guard() -> None:
    a = _make(5, [1, 2, 3, 4, 5])
    a.set_state("cell[2]", "hidden")
    svg = a.emit_svg()
    # hidden neither skips nor blanks: all 5 cells still emit, value 3 remains.
    assert _cell_group_count(svg) == 5
    assert ">3<" in svg or "3</text>" in svg


# ---------------------------------------------------------------------------
# 8. GREEN guard — a never-reflowed, sentinel-free array is byte-identical
# ---------------------------------------------------------------------------


def test_array_narrow_reflow_byte_identical() -> None:
    # Captured from pre-change HEAD (additive-only proof).
    expected = (
        '<g data-primitive="array" data-shape="a">\n'
        '  <g data-target="a.cell[0]" class="scriba-state-idle">\n'
        '    <rect x="1.0" y="1.0" width="58.0" height="38.0"/>\n'
        '    <text x="30" y="20" fill="#11181c" style="font-size:14px">10</text>\n'
        '  </g>\n'
        '  <g data-target="a.cell[1]" class="scriba-state-idle">\n'
        '    <rect x="63.0" y="1.0" width="58.0" height="38.0"/>\n'
        '    <text x="92" y="20" fill="#11181c" style="font-size:14px">20</text>\n'
        '  </g>\n'
        '  <g data-target="a.cell[2]" class="scriba-state-idle">\n'
        '    <rect x="125.0" y="1.0" width="58.0" height="38.0"/>\n'
        '    <text x="154" y="20" fill="#11181c" style="font-size:14px">30</text>\n'
        '  </g>\n'
        '</g>'
    )
    a = _make(3, [10, 20, 30])
    assert a.emit_svg() == expected
    assert a.bounding_box().width == float(3 * CELL_WIDTH + 2 * CELL_GAP)
    assert "scriba-sentinel" not in a.emit_svg()


# ---------------------------------------------------------------------------
# 9. OQ2 pin — removed tail renders as an EMPTY CELL (grid preserved)
# ---------------------------------------------------------------------------


def test_array_remove_frees_tail_empty_cell() -> None:
    a = _make(5, [1, 2, 3, 4, 5])
    a.apply_command({"remove": 1})
    svg = a.emit_svg()
    # grid preserved: still 5 physical cells (no shrink), tail slot is empty.
    assert _cell_group_count(svg) == 5
    # slot 4 (the freed tail) carries no value text
    tail = re.search(r'data-target="a\.cell\[4\]".*?</g>', svg, re.DOTALL).group(0)
    assert ">5<" not in tail and ">1<" not in tail  # no stale value in the tail


# ---------------------------------------------------------------------------
# 10. R-32 pin — cell[i] x attributes are byte-identical across insert/remove
# ---------------------------------------------------------------------------


def test_array_cell_x_byte_identical_across_ops() -> None:
    a = _make(5, [1, 2, 3, 4])
    xs0 = _cell_rect_xs(a.emit_svg())
    a.apply_command({"insert": {"at": 1, "value": 9}})
    xs1 = _cell_rect_xs(a.emit_svg())
    a.apply_command({"remove": 0})
    xs2 = _cell_rect_xs(a.emit_svg())

    assert len(xs0) == 5
    assert xs0 == xs1 == xs2
    # the fixed slot grid: 0, 62, 124, 186, 248 (+1.0 stroke inset)
    assert xs0 == ["1.0", "63.0", "125.0", "187.0", "249.0"]
