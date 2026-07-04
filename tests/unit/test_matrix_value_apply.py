"""A2b: Matrix single-cell value mutation via ``\\apply{m.cell[r][c]}{value=X}``.

The Matrix spec (docs/primitives/matrix.md §5.1) promised value mutation with
automatic colorscale recompute, but the emit path only ever read the static
``self.data`` — the value channel was silently swallowed
(investigations/gap-inert-primitive-ops.md §A2b, conflict #1).

The fix keeps fill inside the colorscale (no state-fill override): emit reads
the ``get_value`` override, re-derives ``t`` from the new numeric value, and
recolours the cell through the SAME colorscale. The declared vmin/vmax range
stays frozen to the initial data, so colours remain stable across frames.
"""

from __future__ import annotations

import re

from scriba.animation.differ import _diff_shape_states
from scriba.animation.primitives.matrix import (
    VIRIDIS,
    MatrixPrimitive,
    interpolate_color,
)


def _cell_fill(svg: str, row: int, col: int) -> str | None:
    """Extract the ``fill`` of the ``cell[row][col]`` rect from *svg*."""
    m = re.search(
        rf'data-target="m\.cell\[{row}\]\[{col}\]".*?fill="([^"]+)"',
        svg,
        re.S,
    )
    return m.group(1) if m else None


def _cell_text(svg: str, row: int, col: int) -> str | None:
    """Extract the displayed ``<text>`` content of ``cell[row][col]``."""
    m = re.search(
        rf'data-target="m\.cell\[{row}\]\[{col}\]".*?<text[^>]*>([^<]*)</text>',
        svg,
        re.S,
    )
    return m.group(1) if m else None


class TestMatrixValueApply:
    def test_value_override_recomputes_fill_through_colorscale(self) -> None:
        m = MatrixPrimitive(
            "m", {"rows": 1, "cols": 2, "data": [[0.0, 1.0]], "vmin": 0.0, "vmax": 1.0}
        )
        # Bump cell[0][0] from 0.0 to 1.0 → it should now paint the max colour.
        m.set_value("cell[0][0]", "1.0")
        svg = m.emit_svg()
        assert _cell_fill(svg, 0, 0) == interpolate_color(1.0, VIRIDIS)
        # ...and it matches its neighbour that is natively 1.0.
        assert _cell_fill(svg, 0, 0) == _cell_fill(svg, 0, 1)

    def test_value_override_updates_shown_text(self) -> None:
        m = MatrixPrimitive(
            "m", {"rows": 1, "cols": 1, "data": [[3.0]], "show_values": True}
        )
        assert _cell_text(m.emit_svg(), 0, 0) == "3"
        m.set_value("cell[0][0]", "7")
        assert _cell_text(m.emit_svg(), 0, 0) == "7"

    def test_no_override_is_byte_identical(self) -> None:
        # A matrix with no value applied must render exactly as before (the
        # golden-stable guarantee: the get_value read is a no-op when unset).
        params = {"rows": 2, "cols": 2, "data": [[0.0, 0.5], [0.5, 1.0]]}
        assert MatrixPrimitive("m", params).emit_svg() == MatrixPrimitive(
            "m", params
        ).emit_svg()

    def test_range_stays_frozen_to_initial_data(self) -> None:
        # Auto range from data is [0.0, 1.0]. Overriding a cell to 5.0 must NOT
        # rescale the colorscale — t clamps to 1.0 (spec §5.1 frozen range).
        m = MatrixPrimitive("m", {"rows": 1, "cols": 2, "data": [[0.0, 1.0]]})
        m.set_value("cell[0][0]", "5.0")
        svg = m.emit_svg()
        assert _cell_fill(svg, 0, 0) == interpolate_color(1.0, VIRIDIS)

    def test_non_numeric_value_keeps_datum(self) -> None:
        # Matrix values drive the colorscale, so a non-numeric override cannot
        # map to a colour — it soft-drops to the declared datum (fill unchanged).
        m = MatrixPrimitive(
            "m", {"rows": 1, "cols": 1, "data": [[0.0]], "vmin": 0.0, "vmax": 1.0}
        )
        m.set_value("cell[0][0]", "not-a-number")
        svg = m.emit_svg()
        assert _cell_fill(svg, 0, 0) == interpolate_color(0.0, VIRIDIS)

    def test_differ_emits_value_change_for_matrix_cell(self) -> None:
        # The differ compares shape_states, so a cell that gains a value across
        # frames yields a value_change transition (no primitive-specific wiring).
        prev = {"m": {"m.cell[0][0]": {"state": "idle"}}}
        curr = {"m": {"m.cell[0][0]": {"state": "idle", "value": "7"}}}
        transitions = _diff_shape_states(prev, curr)
        assert ("m.cell[0][0]", "value_change") in [
            (t.target, t.kind) for t in transitions
        ]
