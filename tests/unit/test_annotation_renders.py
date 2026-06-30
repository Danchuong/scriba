"""Regrowth guard (ratchet): a position annotation on a valid target must RENDER.

The "annotation accepted but silently dropped" defect — ``validate_selector``
returns True and ``set_annotations`` stores the annotation, but ``emit_svg``
draws nothing — was fixed structurally for DPTable (1D range), NumberLine
(position pills + range) and Matrix (all annotations). Array and Grid already
rendered position pills.

This test codifies the bug **class** so it cannot silently return: every
primitive in ``_ANNOTATION_BEARERS`` must render a ``position=above`` pill on
its first addressable cell/tick. A primitive that newly drops annotations fails
here; a new annotation-bearing primitive is added to the set when wired up — so
the guarantee can only grow, never silently regress. No silent technical debt.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.stack import Stack

from tests.unit.test_obstacle_protocol import _ALL_PRIMITIVE_CLASSES, _make_instance

# Primitives whose minimal _make_instance recipe renders no targets (an item-less
# Stack) need richer construction so the guard has a concrete cell to annotate.
_RICH_CTOR: dict[type, tuple[str, dict]] = {
    Stack: ("s", {"items": [1, 2, 3]}),
}

# Primitives that accept a cell/tick selector and MUST render an annotation on
# it. GROWS as primitives gain annotation support. Never shrinks.
_ANNOTATION_BEARERS: set[str] = {
    "array",
    "dptable",
    "numberline",
    "grid",
    "matrix",
    "queue",
    "stack",
    "codepanel",
}

# Selector suffixes that are not concrete targets.
_META_PARTS = {"all", "axis"}


@pytest.mark.parametrize("cls", _ALL_PRIMITIVE_CLASSES, ids=lambda c: c.__name__)
def test_position_annotation_renders(cls: type) -> None:
    rich = _RICH_CTOR.get(cls)
    inst = cls(*rich) if rich else _make_instance(cls)
    if inst.primitive_type not in _ANNOTATION_BEARERS:
        pytest.skip(f"{cls.__name__} is not a tracked annotation-bearer")

    targets = [p for p in inst.addressable_parts() if p not in _META_PARTS]
    assert targets, f"{cls.__name__} exposes no concrete target to annotate"
    target = f"{inst.name}.{targets[0]}"

    inst.set_annotations(
        [{"target": target, "label": "GUARDLBL", "position": "above"}]
    )
    svg = inst.emit_svg()

    assert "GUARDLBL" in svg, (
        f"{cls.__name__}: position annotation on {target} was silently dropped "
        f"(accepted by validate_selector but not rendered)."
    )
    assert "scriba-annotation" in svg, (
        f"{cls.__name__}: annotation label rendered but not as a pill element."
    )
