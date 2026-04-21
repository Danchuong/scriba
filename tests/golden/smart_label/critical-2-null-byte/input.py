"""Golden fixture: critical-2-null-byte

Scenario: Annotation label contains a null byte (U+0000): "a\\x00b".
The null byte MUST be stripped before insertion into the SVG <text> element
so that the output is well-formed XML.

Bug class: C-2 (null byte in label text).
Invariants exercised: T-1, §2.4

Expected outcome (FIXED state):
  - Null byte stripped; label rendered as "ab".
  - SVG parses as valid XML.
  - No null byte in aria-label or <text> content.

Known-failing status:
  This fixture is marked known_failing=True because the null-byte stripping
  guard has not yet been merged into main. The expected.svg captures the
  FIXED state (null stripped). Until the fix lands, the rendered output will
  contain a raw null byte and fail XML validation.

  Rebase: once the sanitization fix lands, run SCRIBA_UPDATE_GOLDEN=1 against
  this fixture to flip known_failing to False and update the pin.

OUTPUT is set to the raw SVG string so the corpus runner can read it.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# Monkey-patch missing stub so package loads cleanly in in-progress state.
import scriba.animation.primitives._svg_helpers as _helpers_module  # noqa: E402

if not hasattr(_helpers_module, "_place_pill"):
    _helpers_module._place_pill = None  # type: ignore[attr-defined]

from scriba.animation.primitives._svg_helpers import (  # noqa: E402
    _LabelPlacement,
    emit_position_label_svg,
)

CELL_W = 60
CELL_H = 40
PAD_TOP = 50
SVG_W = 200
SVG_H = 100

lines: list[str] = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_W} {SVG_H}">',
]
for i in range(3):
    cx = 10 + i * CELL_W
    cy = PAD_TOP
    lines.append(
        f'  <rect x="{cx}" y="{cy}" width="{CELL_W}" height="{CELL_H}"'
        f' fill="white" stroke="#333" stroke-width="1"/>'
    )

placed: list[_LabelPlacement] = []
ann = {
    "label": "a\x00b",  # raw null byte — regression trigger
    "color": "info",
    "position": "above",
    "target": "arr.cell[0]",
}
anchor_x = 10.0 + 0 * CELL_W + CELL_W / 2.0
anchor_y = float(PAD_TOP)
emit_position_label_svg(
    lines=lines,
    ann=ann,
    anchor_point=(anchor_x, anchor_y),
    cell_height=float(CELL_H),
    placed_labels=placed,
)
lines.append("</svg>")

OUTPUT: str = "\n".join(lines) + "\n"
