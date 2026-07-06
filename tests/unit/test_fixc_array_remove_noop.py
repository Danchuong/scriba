"""Fix C — F4: a structural REMOVAL must not emit a no-op ``element_add``.

From investigations/hunt-runtime-static.md (F4, Low): an
``\\apply{a}{remove=0}`` whose bare shape ``a`` is first touched by the remove
lands ``apply_params=[{'remove': 0}]`` on the bare-shape target. The differ's
``element_add`` branch keys purely on "a target with apply_params newly
appeared", so it emits ``["a","add",null,"idle","element_add"]`` — but a REMOVE
shrinks the structure; an "add" is semantically backwards, and ``data-target=
"a"`` is not even an addressable element (only ``a.cell[i]`` is), so both the
forward add and its reverse remove are no-ops that fs-snap already salvages.

The fix suppresses ``element_add`` when the triggering apply is a pure removal.
Additions (push / enqueue / insert / row-append) are unaffected — their
first-touch ``element_add`` still fires (Stack / Queue goldens rely on it).
"""

from __future__ import annotations

from scriba.animation.differ import compute_transitions
from scriba.animation.emitter import FrameData


def _fd(shape_states: dict) -> FrameData:
    return FrameData(
        step_number=1,
        total_frames=2,
        narration_html="",
        shape_states=shape_states,
        annotations=[],
    )


def _kinds(prev: dict, curr: dict) -> set[str]:
    return {t.kind for t in compute_transitions(_fd(prev), _fd(curr)).transitions}


# ---------------------------------------------------------------------------
# The bug: a first-touch removal emits a no-op element_add
# ---------------------------------------------------------------------------


def test_remove_first_touch_emits_no_element_add() -> None:
    # Frame 1: array untouched (only prelude data, no command state). Frame 2:
    # the FIRST command touching the bare shape is a remove.
    prev = _fd({"a": {}})
    curr = _fd({"a": {"a": {"state": "idle", "apply_params": [{"remove": 0}]}}})
    assert "element_add" not in _kinds({"a": {}}, curr.shape_states)
    # And no element_add appears in the full manifest.
    manifest = compute_transitions(prev, curr)
    assert all(t.kind != "element_add" for t in manifest.transitions)


def test_stack_pop_first_touch_emits_no_element_add() -> None:
    curr = {"s": {"s": {"state": "idle", "apply_params": [{"pop": True}]}}}
    assert "element_add" not in _kinds({"s": {}}, curr)


def test_queue_dequeue_first_touch_emits_no_element_add() -> None:
    curr = {"q": {"q": {"state": "idle", "apply_params": [{"dequeue": True}]}}}
    assert "element_add" not in _kinds({"q": {}}, curr)


# ---------------------------------------------------------------------------
# Guard: additions still emit element_add (fix is surgical)
# ---------------------------------------------------------------------------


def test_stack_push_first_touch_still_emits_element_add() -> None:
    curr = {"s": {"s": {"state": "idle", "apply_params": [{"push": 3}]}}}
    assert "element_add" in _kinds({"s": {}}, curr)


def test_array_insert_first_touch_still_emits_element_add() -> None:
    curr = {"a": {"a": {"state": "idle", "apply_params": [{"insert": {"at": 0, "value": 9}}]}}}
    assert "element_add" in _kinds({"a": {}}, curr)


def test_row_append_first_touch_still_emits_element_add() -> None:
    # TraceTable's row-append is an ADD, so its differ-level element_add stands.
    curr = {"t": {"t": {"state": "idle", "apply_params": [{"row": [0, 3]}]}}}
    assert "element_add" in _kinds({"t": {}}, curr)
