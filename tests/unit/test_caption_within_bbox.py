"""Regrowth guard (ratchet): a primitive's caption must fit inside its bbox.

The "caption-not-in-bbox-width" defect (a long ``label=`` caption clips at the
viewBox edge) was fixed structurally for Array. This test codifies the bug
**class** so it can only ever shrink:

- Primitives in ``_CAPTION_MIGRATED`` MUST keep their caption within
  ``bounding_box().width`` (the fix holds).
- Every other caption-bearing primitive is asserted to STILL clip. When you
  migrate one (caption width folded into bbox + wrap), this test fails with a
  message telling you to move it into ``_CAPTION_MIGRATED`` — so the set is
  monotonic and the class cannot silently regrow. No silent technical debt.
"""

from __future__ import annotations

import html as _html
import re

import pytest

from scriba.animation.primitives._text_render import estimate_text_width

from tests.unit.test_obstacle_protocol import _ALL_PRIMITIVE_CLASSES, _make_instance

# Primitives whose caption width is reflected in bounding_box() (migrated).
# GROWS as primitives adopt the shared caption layer. Never shrinks.
_CAPTION_MIGRATED: set[str] = {
    "array",
    "queue",
    "hashmap",
    "linkedlist",
    "variablewatch",
    "matrix",
    "stack",
    "grid",
}

# Long enough to exceed any minimally-constructed primitive's content width.
_LONG_CAPTION = (
    "a deliberately very long descriptive caption that far exceeds the content "
    "width of any minimally constructed primitive instance by a wide margin"
)
_CAPTION_FONT_PX = 11


def _caption_drawn_width(svg: str) -> float:
    """Widest rendered line of the ``scriba-primitive-label`` caption, or 0."""
    m = re.search(
        r'<text class="scriba-primitive-label"[^>]*>(.*?)</text>', svg, re.S
    )
    if not m:
        # math captions render in a foreignObject div with the same class
        m = re.search(
            r'<div class="scriba-primitive-label"[^>]*>(.*?)</div>', svg, re.S
        )
        if not m:
            return 0.0
    body = m.group(1)
    spans = re.findall(r"<tspan[^>]*>(.*?)</tspan>", body, re.S)
    lines = spans if spans else [body]
    lines = [_html.unescape(re.sub(r"<[^>]+>", "", ln)) for ln in lines]
    return max(
        (estimate_text_width(ln, _CAPTION_FONT_PX) for ln in lines), default=0.0
    )


@pytest.mark.parametrize("cls", _ALL_PRIMITIVE_CLASSES, ids=lambda c: c.__name__)
def test_caption_fits_bounding_box(cls: type) -> None:
    inst = _make_instance(cls)
    if not hasattr(inst, "label"):
        pytest.skip(f"{cls.__name__} has no caption attribute")
    inst.label = _LONG_CAPTION
    svg = inst.emit_svg()
    if "scriba-primitive-label" not in svg:
        pytest.skip(f"{cls.__name__} does not render a bottom caption")

    bbox_w = float(inst.bounding_box().width)
    cap_w = _caption_drawn_width(svg)
    fits = cap_w <= bbox_w + 1.0  # +1 rounding tolerance

    if inst.primitive_type in _CAPTION_MIGRATED:
        assert fits, (
            f"{cls.__name__}: caption width {cap_w:.0f} exceeds bbox width "
            f"{bbox_w:.0f} — a migrated primitive regressed."
        )
    else:
        # Ratchet: not yet migrated → expected to clip. If it now fits, the
        # caption fix has landed for it; add it to _CAPTION_MIGRATED.
        assert not fits, (
            f"{cls.__name__}: caption now fits its bbox — the caption fix has "
            f"landed; add '{inst.primitive_type}' to _CAPTION_MIGRATED."
        )
