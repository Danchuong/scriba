"""Golden fixture: ok-simple

Scenario: Array n=3, single position-only annotation on cell[1],
label="ptr", color=info.

Invariants exercised: AC-1, AC-3, G-3
Expected outcome: Single pill above cell[1]; no leader; pill within viewBox.

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
    "label": "ptr",
    "color": "info",
    "position": "above",
    "target": "arr.cell[1]",
}
anchor_x = 10.0 + 1 * CELL_W + CELL_W / 2.0
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
