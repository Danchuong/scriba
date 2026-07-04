"""R-32 for LinkedList: insert/remove must not shift the structure.

The live-bbox landmine (investigations/anim-reflow-sentinel.md, executed
finding #2): bbox width followed len(values) per frame, so the
frame_renderer's centering offset moved every node ~110px mid-timeline.
The fix: a monotonic _envelope_n grown by apply_command AND by the
structural prescan, so frame 0 is as wide as the widest future frame."""

from __future__ import annotations

from scriba.animation._frame_renderer import _prescan_value_widths
from scriba.animation.primitives.linkedlist import LinkedList


class _Frame:
    def __init__(self, shape_states):
        self.shape_states = shape_states


def test_envelope_grows_on_insert_and_survives_remove() -> None:
    ll = LinkedList("l", {"data": [1, 2, 3]})
    w0 = ll.bounding_box().width
    ll.apply_command({"insert": {"index": 1, "value": 9}})
    w1 = ll.bounding_box().width
    assert w1 > w0
    ll.apply_command({"remove": 0})
    ll.apply_command({"remove": 0})
    assert ll.bounding_box().width == w1  # envelope never shrinks


def test_structural_prescan_reaches_timeline_max_before_frame0() -> None:
    ll = LinkedList("l", {"data": [1, 2]})
    frames = [
        _Frame({"l": {"l": {"apply_params": [{"insert": {"index": 0, "value": 7}}]}}}),
        _Frame({"l": {"l": {"apply_params": [
            {"insert": {"index": 0, "value": 8}},
            {"remove": 1},
        ]}}}),
    ]
    _prescan_value_widths(frames, {"l": ll})
    # values restored to the declared state...
    assert ll.values == [1, 2]
    # ...but the envelope saw the max count (4 nodes at peak)
    assert ll._envelope_n == 4
    # so frame-0 bbox already has the final width
    w_frame0 = ll.bounding_box().width
    ll.apply_command({"insert": {"index": 0, "value": 7}})
    ll.apply_command({"insert": {"index": 0, "value": 8}})
    assert ll.bounding_box().width == w_frame0


def test_no_structural_ops_byte_stable() -> None:
    a = LinkedList("l", {"data": [1, 2, 3]})
    b = LinkedList("l", {"data": [1, 2, 3]})
    _prescan_value_widths([], {"l": b})
    assert a.emit_svg() == b.emit_svg()
