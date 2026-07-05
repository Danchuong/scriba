"""Unit tests for Array ``reorder`` — the element-identity layer (A5).

Design (investigations/gap-motion-identity-reorder.md §5.4, spec-diff §6(b)):

Two identity layers coexist. ``cell[i]`` is the **SLOT** — a fixed position
that anchors annotations and recolors (R-42, unchanged). ``item[k]`` is the
**ELEMENT** — assigned at t0 (item ``k`` born at slot ``k``), carrying a value
and a *mobile* position. ``\\apply{a}{reorder=[...]}`` permutes the live prefix
so items glide to new slots (differ ``position_move``), reusing the bulk
``apply_params`` path — no new verb.

**Order semantics (CONFIRMED, gather):** ``order`` is a list of SOURCE-SLOT
indices. After the op, slot ``j`` displays the pre-op value of slot
``order[j]`` — i.e. ``new[j] = old[order[j]]``.

Invariants exercised here:
- value + ``_item_of_slot`` permute together by the gather rule
- double reorder composes as function composition
- invalid ``order`` (length, non-permutation, non-int, mixed with
  insert/remove) raises E1404 loudly and leaves the array untouched
- ``data-item`` is emitted ONLY after a reorder (byte-stability of pre-A5
  goldens); ``get_node_positions`` is empty until then
- ``get_node_positions`` keys are ``item[k]`` at the new slot center
- a recolor keyed on ``cell[i]`` stays pinned to the slot, not the value
"""

from __future__ import annotations

import re

import pytest

from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives._types import CELL_GAP, CELL_HEIGHT
from scriba.core.errors import ValidationError


def _make(size: int, data=None, **extra) -> ArrayPrimitive:
    params: dict = {"size": size}
    if data is not None:
        params["data"] = list(data)
    params.update(extra)
    return ArrayPrimitive("a", params)


def _cell_open_tag(svg: str, idx: int) -> str:
    """The opening ``<g data-target="a.cell[idx]" ...>`` tag (attributes only)."""
    m = re.search(rf'<g data-target="a\.cell\[{idx}\]"[^>]*>', svg)
    return m.group(0) if m else ""


# ---------------------------------------------------------------------------
# 1. gather semantics — value permute, new[j] = old[order[j]]
# ---------------------------------------------------------------------------


def test_reorder_permutes_values_gather_semantics() -> None:
    a = _make(5, [10, 20, 30, 40, 50])
    a.apply_command({"reorder": [3, 0, 1, 4, 2]})
    # slot j takes the pre-op value of slot order[j]:
    #   0<-3=40, 1<-0=10, 2<-1=20, 3<-4=50, 4<-2=30
    assert a.data == [40, 10, 20, 50, 30]
    assert a.live == 5


def test_reorder_identity_order_is_noop() -> None:
    a = _make(4, [1, 2, 3, 4])
    a.apply_command({"reorder": [0, 1, 2, 3]})
    assert a.data == [1, 2, 3, 4]
    assert a._item_of_slot == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# 2. _item_of_slot tracks the element layer by the same gather rule
# ---------------------------------------------------------------------------


def test_reorder_permutes_item_of_slot() -> None:
    a = _make(5, [10, 20, 30, 40, 50])
    assert a._item_of_slot == [0, 1, 2, 3, 4]  # born identity
    a.apply_command({"reorder": [3, 0, 1, 4, 2]})
    # item at source slot order[j] now sits at slot j
    assert a._item_of_slot == [3, 0, 1, 4, 2]
    # item k still carries the value it was born with (item 3 born at slot 3
    # with value 40; it now sits at slot 0, which reads 40)
    assert a.data[0] == 40  # slot 0 holds item 3


# ---------------------------------------------------------------------------
# 3. double reorder composes as function composition
# ---------------------------------------------------------------------------


def test_double_reorder_composes() -> None:
    a = _make(3, [10, 20, 30])
    a.apply_command({"reorder": [2, 0, 1]})  # rotate
    assert a.data == [30, 10, 20]
    assert a._item_of_slot == [2, 0, 1]
    a.apply_command({"reorder": [1, 2, 0]})  # inverse rotate -> identity
    assert a.data == [10, 20, 30]
    assert a._item_of_slot == [0, 1, 2]


def test_double_reorder_non_identity_compose() -> None:
    a = _make(4, [1, 2, 3, 4])
    a.apply_command({"reorder": [1, 0, 2, 3]})  # swap 0,1 -> [2,1,3,4]
    a.apply_command({"reorder": [0, 1, 3, 2]})  # swap 2,3 -> [2,1,4,3]
    assert a.data == [2, 1, 4, 3]
    assert a._item_of_slot == [1, 0, 3, 2]


# ---------------------------------------------------------------------------
# 4. invalid order raises E1404 loudly and leaves the array untouched
# ---------------------------------------------------------------------------


def test_reorder_wrong_length_errors() -> None:
    a = _make(5, [10, 20, 30, 40, 50])
    with pytest.raises(ValidationError, match="E1404"):
        a.apply_command({"reorder": [0, 1, 2]})  # length 3 != live 5
    assert a.data == [10, 20, 30, 40, 50]  # untouched
    assert a._item_of_slot == [0, 1, 2, 3, 4]
    assert a._reordered is False


def test_reorder_not_a_permutation_errors() -> None:
    a = _make(5, [10, 20, 30, 40, 50])
    with pytest.raises(ValidationError, match="E1404"):
        a.apply_command({"reorder": [0, 0, 1, 2, 3]})  # dup 0, missing 4
    assert a.data == [10, 20, 30, 40, 50]


def test_reorder_out_of_range_index_errors() -> None:
    a = _make(3, [1, 2, 3])
    with pytest.raises(ValidationError, match="E1404"):
        a.apply_command({"reorder": [0, 1, 3]})  # 3 is out of 0..2


def test_reorder_non_integer_errors() -> None:
    a = _make(3, [1, 2, 3])
    with pytest.raises(ValidationError, match="E1404"):
        a.apply_command({"reorder": [0, "x", 2]})


def test_reorder_not_a_list_errors() -> None:
    a = _make(3, [1, 2, 3])
    with pytest.raises(ValidationError, match="E1404"):
        a.apply_command({"reorder": 5})


def test_reorder_on_live_prefix_only() -> None:
    # partial fill: live == 3 on a size-5 grid; order is over 0..2
    a = _make(5, [1, 2, 3])
    a.apply_command({"reorder": [2, 0, 1]})
    assert a.data[:3] == [3, 1, 2]
    assert a.data[3:] == ["", ""]  # empty tail untouched
    assert a._item_of_slot[:3] == [2, 0, 1]
    assert a._item_of_slot[3:] == [3, 4]  # tail item ids unchanged


# ---------------------------------------------------------------------------
# 4b. reorder cannot be mixed with insert/remove (either order) — E1404
# ---------------------------------------------------------------------------


def test_insert_then_reorder_errors() -> None:
    a = _make(5, [1, 2, 3])
    a.apply_command({"insert": {"at": 0, "value": 9}})
    with pytest.raises(ValidationError, match="E1404"):
        a.apply_command({"reorder": [0, 1, 2, 3]})


def test_reorder_then_insert_errors() -> None:
    a = _make(5, [1, 2, 3])
    a.apply_command({"reorder": [2, 0, 1]})
    with pytest.raises(ValidationError, match="E1404"):
        a.apply_command({"insert": {"at": 0, "value": 9}})


def test_reorder_then_remove_errors() -> None:
    a = _make(5, [1, 2, 3])
    a.apply_command({"reorder": [2, 0, 1]})
    with pytest.raises(ValidationError, match="E1404"):
        a.apply_command({"remove": 0})


def test_reorder_mixed_with_insert_in_one_call_errors() -> None:
    a = _make(5, [1, 2, 3])
    with pytest.raises(ValidationError, match="E1404"):
        a.apply_command({"reorder": [2, 0, 1], "insert": {"at": 0, "value": 9}})
    # nothing applied
    assert a.data[:3] == [1, 2, 3]
    assert a._reordered is False


def test_insert_and_remove_together_still_allowed() -> None:
    # both are the SAME (reflow) model — only reorder mixing is blocked
    a = _make(5, [1, 2, 3])
    a.apply_command({"insert": {"at": 1, "value": 9}})
    a.apply_command({"remove": 0})
    assert a._reflowed is True
    assert a._reordered is False


# ---------------------------------------------------------------------------
# 5. data-item byte-stability — emitted ONLY after a reorder
# ---------------------------------------------------------------------------


def test_data_item_absent_before_reorder() -> None:
    a = _make(4, [1, 2, 3, 4])
    svg = a.emit_svg()
    assert "data-item" not in svg


def test_emit_svg_byte_identical_when_never_reordered() -> None:
    # A never-reordered array must be byte-identical to a fresh one that also
    # carries the new item-layer state (proves the gate adds zero bytes).
    a = _make(4, [1, 2, 3, 4])
    b = _make(4, [1, 2, 3, 4])
    assert a.emit_svg() == b.emit_svg()
    assert "data-item" not in a.emit_svg()


def test_data_item_present_after_reorder() -> None:
    a = _make(4, [1, 2, 3, 4])
    a.apply_command({"reorder": [3, 2, 1, 0]})
    svg = a.emit_svg()
    assert "data-item" in svg
    # slot 0 now holds item 3; cell[0] carries data-item="a.item[3]"
    tag0 = _cell_open_tag(svg, 0)
    assert 'data-target="a.cell[0]"' in tag0
    assert 'data-item="a.item[3]"' in tag0


# ---------------------------------------------------------------------------
# 6. get_node_positions — keys item[k] at the NEW slot center
# ---------------------------------------------------------------------------


def test_get_node_positions_empty_before_reorder() -> None:
    a = _make(4, [1, 2, 3, 4])
    assert a.get_node_positions() == {}


def test_get_node_positions_item_keys_at_new_slot_centers() -> None:
    a = _make(5, [10, 20, 30, 40, 50])
    a.apply_command({"reorder": [3, 0, 1, 4, 2]})
    positions = a.get_node_positions()

    cw = a._cell_width
    dx = a._row_dx()
    cy = CELL_HEIGHT // 2
    # item k = _item_of_slot[i] sits at slot i -> center of slot i
    for i in range(a.live):
        k = a._item_of_slot[i]
        expected_x = int(i * (cw + CELL_GAP) + cw // 2) + dx
        assert positions[f"a.item[{k}]"] == (expected_x, cy)

    # every live item appears exactly once, keyed by its fixed id
    assert set(positions.keys()) == {f"a.item[{k}]" for k in range(a.live)}


def test_get_node_positions_tracks_across_two_reorders() -> None:
    a = _make(3, [10, 20, 30])
    a.apply_command({"reorder": [2, 0, 1]})
    first = a.get_node_positions()
    a.apply_command({"reorder": [1, 2, 0]})  # back to identity
    second = a.get_node_positions()
    cw = a._cell_width
    dx = a._row_dx()
    cy = CELL_HEIGHT // 2
    # after identity compose, item k is back at slot k
    for k in range(3):
        expected_x = int(k * (cw + CELL_GAP) + cw // 2) + dx
        assert second[f"a.item[{k}]"] == (expected_x, cy)
    # and the first (rotated) snapshot placed item 2 at slot 0
    assert first["a.item[2]"] == (int(0 + cw // 2) + dx, cy)


# ---------------------------------------------------------------------------
# 7. recolor keyed on cell[i] stays pinned to the SLOT, not the value (R-42)
# ---------------------------------------------------------------------------


def test_recolor_stays_on_slot_after_reorder() -> None:
    a = _make(3, [10, 20, 30])
    a.set_state("cell[0]", "current")  # slot 0 (value 10) marked current
    a.apply_command({"reorder": [2, 0, 1]})  # value 10 moves to slot 1
    svg = a.emit_svg()

    # State pinned to the SLOT: cell[0] is still current (now showing value 30)
    assert "scriba-state-current" in _cell_open_tag(svg, 0)
    # The value that moved to slot 1 did NOT drag the recolor with it
    assert "scriba-state-current" not in _cell_open_tag(svg, 1)
    # Value permuted underneath the fixed slot state
    assert a.data == [30, 10, 20]
