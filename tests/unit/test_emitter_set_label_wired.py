"""Regression tests that the emitter forwards ``label`` entries to
``PrimitiveBase.set_label``.

The parser stores ``\\relabel{target}{text}`` into
``ShapeTargetState.label`` and the renderer propagates that as the
``label`` key on the per-target dict in ``FrameData.shape_states``.
Before Wave 5.2 the emitter ignored that key entirely, leaving
``\\relabel`` as dead code.  These tests lock the wiring in.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from scriba.animation.emitter import FrameData, emit_animation_html
from scriba.animation.primitives.base import PrimitiveBase


# Guard for environments where set_label may be removed in the future.
_SET_LABEL_EXISTS = hasattr(PrimitiveBase, "set_label")


@dataclass
class _RecordingPrim:
    """Minimal primitive that records set_label invocations."""

    name: str = "arr"
    primitive_type: str = "array"
    set_label_calls: list[tuple[str, str]] = field(default_factory=list)
    _states: dict[str, str] = field(default_factory=dict)
    _values: dict[str, str] = field(default_factory=dict)
    _labels: dict[str, str] = field(default_factory=dict)

    # ---- bounding box / emit ------------------------------------------------
    def bounding_box(self):
        from scriba.animation.primitives.base import BoundingBox

        return BoundingBox(x=0, y=0, width=200, height=40)

    def emit_svg(self, *, render_inline_tex=None) -> str:
        return '<g data-primitive="array" data-shape="arr"></g>'

    # ---- addressable interface ----------------------------------------------
    def addressable_parts(self) -> list[str]:
        return ["cell[0]", "cell[1]", "all"]

    def validate_selector(self, suffix: str) -> bool:
        return suffix in ("cell[0]", "cell[1]", "all")

    # ---- state / value / label setters --------------------------------------
    def set_state(self, suffix: str, state: str) -> None:
        self._states[suffix] = state

    def get_state(self, suffix: str) -> str:
        return self._states.get(suffix, "idle")

    def set_value(self, suffix: str, value: str) -> None:
        self._values[suffix] = value

    def set_label(self, suffix: str, label: str) -> None:
        # Record the call so the test can assert on it.
        self.set_label_calls.append((suffix, label))
        self._labels[suffix] = label


@pytest.mark.skipif(
    not _SET_LABEL_EXISTS,
    reason=(
        "PrimitiveBase.set_label does not exist — the emitter wiring is "
        "a no-op until the base primitive grows a set_label API. Remove "
        "this skip once the base method exists."
    ),
)
class TestEmitterSetLabelWiring:
    """The emitter must forward per-target label entries to set_label."""

    def test_label_entry_calls_set_label(self) -> None:
        prim = _RecordingPrim()
        frame = FrameData(
            step_number=1,
            total_frames=1,
            narration_html="",
            shape_states={
                "arr": {
                    "arr.cell[0]": {
                        "state": "current",
                        "label": "pivot",
                    },
                },
            },
            annotations=[],
        )
        emit_animation_html(
            "scriba-test",
            [frame],
            {"arr": prim},
            render_inline_tex=None,
        )
        assert ("cell[0]", "pivot") in prim.set_label_calls

    def test_no_label_entry_no_set_label_call(self) -> None:
        prim = _RecordingPrim()
        frame = FrameData(
            step_number=1,
            total_frames=1,
            narration_html="",
            shape_states={
                "arr": {
                    "arr.cell[0]": {"state": "current", "value": "42"},
                },
            },
            annotations=[],
        )
        emit_animation_html(
            "scriba-test",
            [frame],
            {"arr": prim},
            render_inline_tex=None,
        )
        assert prim.set_label_calls == []

    def test_multiple_labels_all_forwarded(self) -> None:
        prim = _RecordingPrim()
        frame = FrameData(
            step_number=1,
            total_frames=1,
            narration_html="",
            shape_states={
                "arr": {
                    "arr.cell[0]": {"state": "idle", "label": "lo"},
                    "arr.cell[1]": {"state": "idle", "label": "hi"},
                },
            },
            annotations=[],
        )
        emit_animation_html(
            "scriba-test",
            [frame],
            {"arr": prim},
            render_inline_tex=None,
        )
        labelled = {suffix: label for suffix, label in prim.set_label_calls}
        assert labelled == {"cell[0]": "lo", "cell[1]": "hi"}

    def test_primitive_base_actually_stores_label(self) -> None:
        """Use the real PrimitiveBase path via a concrete subclass."""
        from scriba.animation.primitives.array import ArrayPrimitive

        arr = ArrayPrimitive("arr", {"size": 3})
        frame = FrameData(
            step_number=1,
            total_frames=1,
            narration_html="",
            shape_states={
                "arr": {
                    "arr.cell[0]": {"state": "idle", "label": "start"},
                },
            },
            annotations=[],
        )
        emit_animation_html(
            "scriba-test",
            [frame],
            {"arr": arr},
            render_inline_tex=None,
        )
        # PrimitiveBase stores labels in self._labels keyed by suffix.
        assert arr._labels.get("cell[0]") == "start"
