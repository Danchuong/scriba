"""Regrowth guard (ratchet): a position=left/right pill must fit the bbox.

`position=right`/`left` pills are placed as a horizontal offset from the anchor,
but bounding_box() historically reserved only VERTICAL space — so a right pill
could overflow the viewBox and a left pill clamp onto the labelled cell. The fix
reserves horizontal room (`position_label_h_extents` → grow width + shift content
right) per primitive.

This codifies the class: a primitive in ``_H_RESERVED`` MUST keep its left/right
pills within ``bounding_box().width`` (left edge >= 0, right edge <= width). The
set grows as primitives opt in; it never shrinks — so the fix cannot silently
regress. (No inverse "still clips" assertion: un-migrated primitives may fit by
content slack, so only the forward guarantee is asserted.)
"""

from __future__ import annotations

import re

import pytest

from tests.unit.test_obstacle_protocol import _ALL_PRIMITIVE_CLASSES, _make_instance

# Primitives whose bounding_box() reserves horizontal space for left/right
# pills. GROWS as primitives opt in. Never shrinks.
_H_RESERVED: set[str] = {
    "grid",
}


def _rect_x_extents(svg: str) -> list[tuple[float, float]]:
    """(left, right) x-edges of every annotation pill ``<rect>``."""
    out: list[tuple[float, float]] = []
    for block in re.findall(
        r'<g class="scriba-annotation[^"]*".*?</g>', svg, re.S
    ):
        for m in re.finditer(r'<rect x="([\-\d.]+)"[^>]*width="([\-\d.]+)"', block):
            x, w = float(m.group(1)), float(m.group(2))
            out.append((x, x + w))
    return out


def _first_cell_target(inst) -> str | None:
    parts = [p for p in inst.addressable_parts() if p not in ("all", "axis")]
    return f"{inst.name}.{parts[0]}" if parts else None


@pytest.mark.parametrize("cls", _ALL_PRIMITIVE_CLASSES, ids=lambda c: c.__name__)
@pytest.mark.parametrize("position", ["right", "left"])
def test_side_pill_within_bbox(cls: type, position: str) -> None:
    inst = _make_instance(cls)
    if inst.primitive_type not in _H_RESERVED:
        pytest.skip(f"{cls.__name__} not yet horizontal-reserved")
    target = _first_cell_target(inst)
    assert target, f"{cls.__name__} exposes no target"
    inst.set_annotations(
        [{"target": target, "label": "a fairly long side note", "position": position}]
    )
    svg = inst.emit_svg()
    extents = _rect_x_extents(svg)
    assert extents, f"{cls.__name__}: {position} pill not rendered"
    bbox_w = float(inst.bounding_box().width)
    for left, right in extents:
        assert left >= -1.0, (
            f"{cls.__name__}: {position} pill left edge {left:.0f} < 0 (clips/clamps)"
        )
        assert right <= bbox_w + 1.0, (
            f"{cls.__name__}: {position} pill right edge {right:.0f} exceeds bbox "
            f"width {bbox_w:.0f} (clips)"
        )
