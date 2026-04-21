"""Golden fixture: bug-B

Scenario: Self-loop annotation — arrow_from == target cell.
`annotate{arr.cell[0]}{label="self", arrow_from="arr.cell[0]"}`

The src and dst points are identical (zero-length displacement), which
triggers division-by-zero in the direction-vector computation.

Bug class: §2.4 guard, G-5
Invariants exercised: §2.4 self-loop guard, G-5 (no NaN/Inf in SVG path data)

Expected outcome (POST-FIX state):
  - No `nan` or `inf` literals in SVG path/polygon coordinate data.
  - Arrow suppressed or a safe degenerate stub emitted.
  - SVG remains parseable XML.

Pre-fix state (CURRENT — AC-6 fix not yet landed on main):
  - Arrow may be emitted with degenerate geometry.
  - This fixture captures the pre-fix rendering so any regression
    (unexpected change) is immediately visible.

BLOCKER NOTE: The ISSUE-below-math (AC-6) fix from Stream A had not landed
on main as of 2026-04-21. This fixture's expected.sha256 reflects the
PRE-FIX rendered state. Once "close AC-6" appears in git log, re-run:

    SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/smart_label/ -k bug-B

and update the pin and known_failing status accordingly.

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
    emit_arrow_svg,
)

CELL_W = 60
CELL_H = 40
PAD_TOP = 80
SVG_W = 200
SVG_H = 140

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
    "label": "self",
    "color": "info",
    "target": "arr.cell[0]",
    "arrow_from": "arr.cell[0]",  # same as target — self-loop
}
# src == dst: zero-length displacement triggers the NaN guard
center_x = 10.0 + 0 * CELL_W + CELL_W / 2.0
src_point = (center_x, float(PAD_TOP))
dst_point = (center_x, float(PAD_TOP))

emit_arrow_svg(
    lines=lines,
    ann=ann,
    src_point=src_point,
    dst_point=dst_point,
    arrow_index=0,
    cell_height=float(CELL_H),
    placed_labels=placed,
)
lines.append("</svg>")

OUTPUT: str = "\n".join(lines) + "\n"
