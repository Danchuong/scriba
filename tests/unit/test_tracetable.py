"""Unit tests for the TraceTable primitive (dry-run trace table).

TraceTable pins ``columns`` as a header row and grows DATA rows downward,
one per ``\\apply{t}{row=[...]}`` append. It rides the LinkedList
structural-prescan envelope (R-32): the bounding box is a pure function of
the row *envelope* (max rows ever reached) and the per-column widths, never
of the live row count, so the stage viewBox is byte-invariant as rows
accumulate.

See ``investigations/design-accumulate.md`` §3 for the authoritative design
and ``tests/unit/test_linkedlist_envelope.py`` for the envelope twin.
"""

from __future__ import annotations

import re

import pytest

from scriba.animation._frame_renderer import _prescan_value_widths
from scriba.animation.differ import compute_transitions
from scriba.animation.emitter import FrameData
from scriba.animation.errors import AnimationError
from scriba.animation.primitives import get_primitive_registry
from scriba.animation.primitives.tracetable import TraceTable

# The closed motion-kind registry (A-2). TraceTable must add zero new kinds.
_CLOSED_11_KINDS: frozenset[str] = frozenset(
    {
        "recolor",
        "value_change",
        "element_add",
        "element_remove",
        "highlight_on",
        "highlight_off",
        "annotation_add",
        "annotation_remove",
        "annotation_recolor",
        "position_move",
        "cursor_move",
    }
)


def _row_segment(svg: str, k: int) -> str:
    """Return the SVG slice belonging to data row ``k`` (up to the next row
    group or the end of the string)."""
    start = svg.index(f'data-target="t.row[{k}]"')
    nxt = svg.find(f'data-target="t.row[{k + 1}]"', start)
    return svg[start:] if nxt == -1 else svg[start:nxt]


class _Frame:
    """Minimal frame stub for the structural prescan (mirrors the LinkedList
    envelope test's ``_Frame``)."""

    def __init__(self, shape_states: dict) -> None:
        self.shape_states = shape_states


def _append_frames(shape: str, rows: list[list]) -> list[_Frame]:
    """One frame per row, each carrying a bare-shape ``row=`` append."""
    return [
        _Frame({shape: {shape: {"apply_params": [{"row": row}]}}})
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_registered_under_tracetable() -> None:
    assert get_primitive_registry().get("TraceTable") is TraceTable


# ---------------------------------------------------------------------------
# Construction / validation errors (E1520, E1521, E1522)
# ---------------------------------------------------------------------------


def test_columns_required_raises_e1520_when_missing() -> None:
    with pytest.raises(AnimationError) as exc:
        TraceTable("t", {})
    assert exc.value.code == "E1520"


def test_columns_required_raises_e1520_when_empty() -> None:
    with pytest.raises(AnimationError) as exc:
        TraceTable("t", {"columns": []})
    assert exc.value.code == "E1520"


def test_row_length_mismatch_raises_e1521() -> None:
    t = TraceTable("t", {"columns": ["i", "a[i]", "sum"]})
    with pytest.raises(AnimationError) as exc:
        t.apply_command({"row": [1, 2]})  # 2 values, 3 columns
    assert exc.value.code == "E1521"


def test_columns_out_of_range_raises_e1522() -> None:
    with pytest.raises(AnimationError) as exc:
        TraceTable("t", {"columns": [f"c{i}" for i in range(65)]})  # > 64
    assert exc.value.code == "E1522"


def test_unknown_param_rejected() -> None:
    # ACCEPTED_PARAMS = {columns, label}; anything else is E1114 (base guard).
    with pytest.raises(AnimationError) as exc:
        TraceTable("t", {"columns": ["i"], "rows": 4})
    assert exc.value.code == "E1114"


# ---------------------------------------------------------------------------
# Header + build
# ---------------------------------------------------------------------------


def test_build_from_columns_pins_header_and_starts_empty() -> None:
    t = TraceTable("t", {"columns": ["i", "a[i]", "sum"]})
    assert t.values == []  # no data rows until an append
    svg = t.emit_svg()
    # Every column header is painted as chrome, above any body.
    for header in ("i", "a[i]", "sum"):
        assert header in svg
    # No data-row groups yet.
    assert 'data-target="t.row[' not in svg


def test_headers_pinned_and_not_addressable() -> None:
    t = TraceTable("t", {"columns": ["i", "sum"]})
    t.apply_command({"row": [0, 3]})
    # row[0] addresses the first DATA row, not the header.
    assert t.validate_selector("row[0]") is True
    assert t.validate_selector("cell[0][0]") is True
    # The header is chrome: it carries no data-target row/cell selector.
    svg = t.emit_svg()
    assert svg.count('data-target="t.row[') == 1  # exactly the one data row


# ---------------------------------------------------------------------------
# Append accumulation
# ---------------------------------------------------------------------------


def test_append_accumulates_rows() -> None:
    t = TraceTable("t", {"columns": ["i", "a[i]", "sum"]})
    counts = []
    for row in ([0, 3, 3], [1, 1, 4], [2, 4, 8]):
        t.apply_command({"row": row})
        counts.append(t.emit_svg().count('data-target="t.row['))
    assert counts == [1, 2, 3]  # frame k emits exactly k data-row groups
    assert t.values == [[0, 3, 3], [1, 1, 4], [2, 4, 8]]


def test_newest_row_is_current_prior_idle() -> None:
    t = TraceTable("t", {"columns": ["i", "sum"]})
    t.apply_command({"row": [0, 3]})
    t.apply_command({"row": [1, 4]})
    svg = t.emit_svg()
    seg0 = _row_segment(svg, 0)
    seg1 = _row_segment(svg, 1)
    # Auto-advance: newest row current, prior row demoted to idle — no manual
    # \recolor needed.
    assert "scriba-state-current" in seg1
    assert "scriba-state-idle" in seg0
    assert "scriba-state-current" not in seg0


# ---------------------------------------------------------------------------
# Growth envelope / R-32 (mirror tests/unit/test_linkedlist_envelope.py)
# ---------------------------------------------------------------------------


def test_structural_prescan_reaches_timeline_max_before_frame0() -> None:
    t = TraceTable("t", {"columns": ["i", "sum"]})
    frames = _append_frames("t", [[0, 3], [1, 4], [2, 8]])
    _prescan_value_widths(frames, {"t": t})
    # Display rows restored to the declared (empty) state...
    assert t.values == []
    # ...but the envelope saw the max row count (3 rows at peak).
    assert t._envelope_rows == 3
    # so the frame-0 bbox (0 rows) already has the final height.
    box0 = t.bounding_box()
    t.apply_command({"row": [0, 3]})
    t.apply_command({"row": [1, 4]})
    t.apply_command({"row": [2, 8]})
    box_full = t.bounding_box()
    assert (box_full.width, box_full.height) == (box0.width, box0.height)


def test_envelope_bbox_invariant_across_row_growth() -> None:
    """The whole point: bbox height AND width are constant as rows accumulate,
    once the envelope is at its timeline max (viewBox is byte-invariant)."""
    t = TraceTable("t", {"columns": ["i", "sum"]})
    frames = _append_frames("t", [[0, 3], [1, 4], [2, 8], [3, 15]])
    _prescan_value_widths(frames, {"t": t})
    ref = t.bounding_box()
    for row in ([0, 3], [1, 4], [2, 8], [3, 15]):
        t.apply_command({"row": row})
        box = t.bounding_box()
        assert box.height == ref.height
        assert box.width == ref.width


def test_bbox_height_grows_only_with_envelope_not_live_rows() -> None:
    # A taller envelope means a taller box; the LIVE row count never shrinks it.
    small = TraceTable("t", {"columns": ["i", "sum"]})
    _prescan_value_widths(_append_frames("t", [[0, 3]]), {"t": small})
    tall = TraceTable("t", {"columns": ["i", "sum"]})
    _prescan_value_widths(
        _append_frames("t", [[0, 3], [1, 4], [2, 8]]), {"t": tall}
    )
    assert tall.bounding_box().height > small.bounding_box().height


def test_column_width_monotonic_late_wide_value() -> None:
    """A wide value in a late row does not shrink earlier frames' width: the
    prescan grows the per-column width to the timeline max before frame 0."""
    t = TraceTable("t", {"columns": ["i", "sum"]})
    frames = _append_frames(
        "t", [[0, 3], [1, "a-very-wide-accumulated-value-here"]]
    )
    _prescan_value_widths(frames, {"t": t})
    w_frame0 = t.bounding_box().width
    t.apply_command({"row": [0, 3]})  # narrow first row
    assert t.bounding_box().width == w_frame0  # already sized for the wide cell


# ---------------------------------------------------------------------------
# Selectors: recolor cell / col / row, soft-drop OOB (the Grid contract)
# ---------------------------------------------------------------------------


def test_recolor_cell_sets_state() -> None:
    t = TraceTable("t", {"columns": ["i", "sum"]})
    t.apply_command({"row": [0, 3]})
    t.apply_command({"row": [1, 4]})
    t.set_state("cell[0][1]", "good")
    seg0 = _row_segment(t.emit_svg(), 0)
    assert "scriba-state-good" in seg0


def test_recolor_col_tints_whole_column() -> None:
    t = TraceTable("t", {"columns": ["i", "sum"]})
    t.apply_command({"row": [0, 3]})
    t.apply_command({"row": [1, 4]})
    t.set_state("col[1]", "path")
    svg = t.emit_svg()
    # Every data row's column-1 cell picks up the column emphasis.
    assert svg.count("scriba-state-path") >= 2


def test_recolor_row_overrides_auto_advance() -> None:
    t = TraceTable("t", {"columns": ["i", "sum"]})
    t.apply_command({"row": [0, 3]})
    t.apply_command({"row": [1, 4]})
    t.set_state("row[1]", "done")  # override the newest-row=current default
    seg1 = _row_segment(t.emit_svg(), 1)
    assert "scriba-state-done" in seg1
    assert "scriba-state-current" not in seg1


def test_out_of_range_selectors_soft_drop() -> None:
    t = TraceTable("t", {"columns": ["i", "sum"]})
    t.apply_command({"row": [0, 3]})
    # OOB row / cell / col all validate False (soft-drop, the Grid contract).
    assert t.validate_selector("row[9]") is False
    assert t.validate_selector("cell[9][0]") is False
    assert t.validate_selector("cell[0][9]") is False
    assert t.validate_selector("col[9]") is False
    # set_state on an invalid selector warns and is ignored (no crash).
    with pytest.warns(UserWarning):
        t.set_state("row[9]", "current")


def test_all_selector_in_addressable_parts() -> None:
    t = TraceTable("t", {"columns": ["i", "sum"]})
    t.apply_command({"row": [0, 3]})
    parts = t.addressable_parts()
    assert "all" in parts
    assert "cell[0][0]" in parts
    assert "cell[0][1]" in parts


# ---------------------------------------------------------------------------
# Differ: append rides element_add, no kind outside the closed 11 (A-2)
# ---------------------------------------------------------------------------


def _frame_data(shape_states: dict) -> FrameData:
    return FrameData(
        step_number=1,
        total_frames=2,
        narration_html="",
        shape_states=shape_states,
        annotations=[],
    )


def test_append_rides_element_add_no_new_motion_kind() -> None:
    # The first row-append is a bare-shape structural apply_params landing where
    # the shape was previously untouched → element_add (identical to a Stack
    # push; see tests/golden/animation/html_element_add.html).
    prev = _frame_data({"t": {}})
    curr = _frame_data(
        {"t": {"t": {"state": "idle", "apply_params": [{"row": [0, 3]}]}}}
    )
    manifest = compute_transitions(prev, curr)
    kinds = {tr.kind for tr in manifest.transitions}
    assert "element_add" in kinds
    # A-2: zero new motion vocabulary — every kind is one of the shipped 11.
    assert kinds <= _CLOSED_11_KINDS


def test_recolor_rides_recolor_kind() -> None:
    prev = _frame_data({"t": {"t.cell[0][0]": {"state": "idle"}}})
    curr = _frame_data({"t": {"t.cell[0][0]": {"state": "good"}}})
    manifest = compute_transitions(prev, curr)
    kinds = {tr.kind for tr in manifest.transitions}
    assert kinds == {"recolor"}
    assert kinds <= _CLOSED_11_KINDS


# ---------------------------------------------------------------------------
# Emit structure sanity
# ---------------------------------------------------------------------------


def test_emit_is_wellformed_group() -> None:
    t = TraceTable("t", {"columns": ["i", "sum"], "label": "Dry run"})
    t.apply_command({"row": [0, 3]})
    svg = t.emit_svg()
    assert svg.startswith('<g data-primitive="tracetable"')
    assert svg.rstrip().endswith("</g>")
    assert "Dry run" in svg  # caption present
    # Balanced <g> tags.
    assert len(re.findall(r"<g\b", svg)) == len(re.findall(r"</g>", svg))
