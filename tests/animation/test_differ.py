"""Tests for the frame-diff engine (scriba.animation.differ)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scriba.animation.differ import Transition, TransitionManifest, compute_transitions
from scriba.animation.emitter import FrameData

GOLDEN_DIR = Path(__file__).parent.parent / "golden" / "animation"


def _load_golden(name: str) -> list:
    return json.loads((GOLDEN_DIR / name).read_text())


def _frame(
    shape_states: dict[str, dict[str, dict]],
    annotations: list[dict] | None = None,
) -> FrameData:
    return FrameData(
        step_number=1,
        total_frames=2,
        narration_html="",
        shape_states=shape_states,
        annotations=annotations or [],
    )


# ---------------------------------------------------------------------------
# Shape-state transitions
# ---------------------------------------------------------------------------


class TestIdenticalFrames:
    def test_identical_frames(self) -> None:
        states = {"arr": {"arr.cell[0]": {"state": "idle", "value": "5"}}}
        manifest = compute_transitions(_frame(states), _frame(states))
        assert manifest.to_compact() == _load_golden("differ_empty.json")
        assert manifest.skip_animation is False


class TestSingleRecolor:
    def test_single_recolor(self) -> None:
        prev = _frame({"arr": {"arr.cell[0]": {"state": "idle"}}})
        curr = _frame({"arr": {"arr.cell[0]": {"state": "current"}}})
        manifest = compute_transitions(prev, curr)
        assert manifest.to_compact() == _load_golden("differ_recolor.json")


class TestMultipleRecolors:
    def test_multiple_recolors(self) -> None:
        prev_targets = {
            f"arr.cell[{i}]": {"state": "idle"} for i in range(5)
        }
        curr_targets = {
            f"arr.cell[{i}]": {"state": "current"} for i in range(5)
        }
        manifest = compute_transitions(
            _frame({"arr": prev_targets}),
            _frame({"arr": curr_targets}),
        )
        assert len(manifest.transitions) == 5
        assert all(t.kind == "recolor" for t in manifest.transitions)


class TestValueChange:
    def test_value_change(self) -> None:
        prev = _frame({"dp": {"dp.cell[1]": {"state": "idle", "value": "?"}}})
        curr = _frame({"dp": {"dp.cell[1]": {"state": "idle", "value": "4"}}})
        manifest = compute_transitions(prev, curr)
        assert manifest.to_compact() == _load_golden("differ_value_change.json")


class TestStateAndValueChange:
    def test_state_and_value_change(self) -> None:
        prev = _frame({"dp": {"dp.cell[0]": {"state": "idle", "value": "?"}}})
        curr = _frame({"dp": {"dp.cell[0]": {"state": "done", "value": "7"}}})
        manifest = compute_transitions(prev, curr)
        assert len(manifest.transitions) == 2
        kinds = {t.kind for t in manifest.transitions}
        assert kinds == {"recolor", "value_change"}


class TestElementAdd:
    def test_element_add(self) -> None:
        """Structural add: target has apply_params (e.g. push)."""
        prev = _frame({"arr": {}})
        curr = _frame({"arr": {"arr.cell[5]": {"state": "idle", "apply_params": [{"push": "42"}]}}})
        manifest = compute_transitions(prev, curr)
        assert manifest.to_compact() == _load_golden("differ_element_add.json")


class TestElementRemove:
    def test_element_remove(self) -> None:
        """Structural remove: target had apply_params."""
        prev = _frame({"arr": {"arr.cell[5]": {"state": "idle", "apply_params": [{"push": "42"}]}}})
        curr = _frame({"arr": {}})
        manifest = compute_transitions(prev, curr)
        assert manifest.to_compact() == _load_golden("differ_element_remove.json")


class TestHighlightOn:
    def test_highlight_on(self) -> None:
        prev = _frame({"arr": {"arr.cell[0]": {"state": "idle", "highlighted": False}}})
        curr = _frame({"arr": {"arr.cell[0]": {"state": "idle", "highlighted": True}}})
        manifest = compute_transitions(prev, curr)
        assert len(manifest.transitions) == 1
        t = manifest.transitions[0]
        assert t.kind == "highlight_on"
        assert t.prop == "highlighted"
        assert t.to_val == "True"


class TestHighlightOff:
    def test_highlight_off(self) -> None:
        prev = _frame({"arr": {"arr.cell[0]": {"state": "idle", "highlighted": True}}})
        curr = _frame({"arr": {"arr.cell[0]": {"state": "idle", "highlighted": False}}})
        manifest = compute_transitions(prev, curr)
        assert len(manifest.transitions) == 1
        t = manifest.transitions[0]
        assert t.kind == "highlight_off"
        assert t.prop == "highlighted"
        assert t.from_val == "True"


# ---------------------------------------------------------------------------
# Annotation transitions
# ---------------------------------------------------------------------------


class TestAnnotationAdd:
    def test_annotation_add(self) -> None:
        prev = _frame({}, annotations=[])
        curr = _frame(
            {},
            annotations=[
                {
                    "target": "dp.cell[3]",
                    "label": "+4",
                    "ephemeral": False,
                    "arrow_from": "dp.cell[0]",
                    "color": "good",
                }
            ],
        )
        manifest = compute_transitions(prev, curr)
        assert manifest.to_compact() == _load_golden("differ_annotations.json")


class TestAnnotationRemove:
    def test_annotation_remove(self) -> None:
        prev = _frame(
            {},
            annotations=[
                {
                    "target": "dp.cell[3]",
                    "arrow_from": "dp.cell[0]",
                    "color": "good",
                }
            ],
        )
        curr = _frame({}, annotations=[])
        manifest = compute_transitions(prev, curr)
        assert len(manifest.transitions) == 1
        t = manifest.transitions[0]
        assert t.kind == "annotation_remove"
        assert t.from_val == "good"


class TestAnnotationRecolor:
    def test_annotation_recolor(self) -> None:
        prev = _frame(
            {},
            annotations=[
                {"target": "dp.cell[3]", "arrow_from": "dp.cell[0]", "color": "good"}
            ],
        )
        curr = _frame(
            {},
            annotations=[
                {"target": "dp.cell[3]", "arrow_from": "dp.cell[0]", "color": "bad"}
            ],
        )
        manifest = compute_transitions(prev, curr)
        assert len(manifest.transitions) == 1
        t = manifest.transitions[0]
        assert t.kind == "annotation_recolor"
        assert t.from_val == "good"
        assert t.to_val == "bad"


# ---------------------------------------------------------------------------
# Edge cases and structural tests
# ---------------------------------------------------------------------------


class TestEmptyFrames:
    def test_empty_frames(self) -> None:
        manifest = compute_transitions(_frame({}), _frame({}))
        assert manifest.to_compact() == _load_golden("differ_empty.json")
        assert manifest.skip_animation is False


class TestPerformanceThreshold:
    def test_performance_threshold(self) -> None:
        prev_targets = {f"arr.cell[{i}]": {"state": "idle"} for i in range(151)}
        curr_targets = {f"arr.cell[{i}]": {"state": "current"} for i in range(151)}
        manifest = compute_transitions(
            _frame({"arr": prev_targets}),
            _frame({"arr": curr_targets}),
        )
        assert manifest.skip_animation is True
        assert len(manifest.transitions) == 151
        assert manifest.to_compact() == _load_golden("differ_over_threshold.json")


class TestToCompactFormat:
    def test_to_compact_format(self) -> None:
        prev = _frame({"arr": {"arr.cell[0]": {"state": "idle"}}})
        curr = _frame({"arr": {"arr.cell[0]": {"state": "current"}}})
        compact = compute_transitions(prev, curr).to_compact()
        assert isinstance(compact, list)
        for row in compact:
            assert isinstance(row, list)
            assert len(row) == 5


class TestMultiShapeDiff:
    def test_multi_shape_diff(self) -> None:
        prev = _frame({
            "arr": {
                "arr.cell[0]": {"state": "idle"},
                "arr.cell[1]": {"state": "current"},
            },
            "dp": {
                "dp.cell[3]": {"state": "pending", "value": "?"},
            },
        })
        curr = _frame({
            "arr": {
                "arr.cell[0]": {"state": "current"},
                "arr.cell[1]": {"state": "done"},
            },
            "dp": {
                "dp.cell[3]": {"state": "done", "value": "7"},
            },
            "G": {
                "G.node[A]": {"state": "idle", "apply_params": [{"add_node": "A"}]},
            },
        })
        manifest = compute_transitions(prev, curr)
        assert manifest.to_compact() == _load_golden("differ_mixed.json")


class TestAddAndRemoveSameStep:
    def test_add_and_remove_same_step(self) -> None:
        """Non-structural: cell[0] returns to idle (disappears from tracking),
        cell[1] appears with state=current (recolor from implicit idle)."""
        prev = _frame({"arr": {"arr.cell[0]": {"state": "done"}}})
        curr = _frame({"arr": {"arr.cell[1]": {"state": "current"}}})
        manifest = compute_transitions(prev, curr)
        # cell[0]: was done, now absent → recolor done→idle
        # cell[1]: was absent, now current → recolor idle→current
        assert len(manifest.transitions) == 2
        kinds = {t.kind for t in manifest.transitions}
        assert kinds == {"recolor"}


class TestAnnotationCompositeKeyCollision:
    """R-32 L4 regression surface: composite key is f\"{target}-{arrow_from}\".

    Two distinct (target, arrow_from) pairs can collapse to the same composite
    string whenever either side contains a hyphen. This test documents the
    current format and pins expected behavior for non-colliding keys so a
    future fix (structured separator) does not regress happy paths.

    xfail: a parenthetical hyphen inside the target is enough to let two
    different pairs share a composite — the differ still emits two distinct
    transitions (good), but both land on the same ``data-annotation`` string
    (the collision) so the JS runtime would mis-route them.
    """

    def test_no_hyphen_in_keys_unique_composite(self) -> None:
        prev = _frame({}, annotations=[])
        curr = _frame({}, annotations=[
            {"target": "dp.cellA", "arrow_from": "dp.cellB", "color": "good"},
            {"target": "dp.cellC", "arrow_from": "dp.cellD", "color": "bad"},
        ])
        manifest = compute_transitions(prev, curr)
        adds = [t for t in manifest.transitions if t.kind == "annotation_add"]
        targets = {t.target for t in adds}
        assert len(adds) == 2
        assert targets == {"dp.cellA-dp.cellB", "dp.cellC-dp.cellD"}

    @pytest.mark.xfail(
        reason="L4 known collision surface: hyphen in target/arrow_from"
               " produces identical composite keys. Deferred fix requires"
               " coordinated emitter ann_key format change.",
        strict=True,
    )
    def test_hyphen_collision_documented(self) -> None:
        prev = _frame({}, annotations=[])
        curr = _frame({}, annotations=[
            # pair A: target "a-b", arrow "c"  →  "a-b-c"
            {"target": "a-b", "arrow_from": "c", "color": "good"},
            # pair B: target "a",   arrow "b-c" →  "a-b-c"   ← collides
            {"target": "a", "arrow_from": "b-c", "color": "bad"},
        ])
        manifest = compute_transitions(prev, curr)
        adds = [t for t in manifest.transitions if t.kind == "annotation_add"]
        targets = {t.target for t in adds}
        # With the current f"{target}-{arrow_from}" composite this collapses
        # to a single key — the assertion below expresses the intended
        # post-fix behavior, hence the xfail(strict=True).
        assert len(adds) == 2
        assert len(targets) == 2
