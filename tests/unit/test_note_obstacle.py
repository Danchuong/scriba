"""Shared-obstacle model — ``\\note`` callout dodges the cell value it floats over.

The scene-level ``\\note`` pill was placed directly at a compass-margin anchor
(``_emit_scene_notes``), bypassing the placer, so a note whose anchor lands over
a cell value painted on top of it. Fix (design-shared-obstacle.md, mechanism a):
the scene renderer now hands ``_emit_scene_notes`` the frame's primitives +
stage offsets, gathers every shape's ``resolve_self_content_rects()`` as
stage-global SHOULD obstacles, and routes each note through ``_place_pill`` so it
slides off the content. A note over an empty board corner keeps its exact anchor
(the placer is a no-op → byte-identical).

Bands: a pill ``<rect>`` covers ``[y, y+h]``; a central-baseline value glyph of
font ``f`` centred on ``y`` covers ``[y-f/2, y+f/2]``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402
from scriba.animation._frame_renderer import _note_anchor_xy  # noqa: E402

_VALUE_FONT_PX = 14.0


def _render(source: str, tmp_path: Path) -> str:
    tex = tmp_path / "in.tex"
    tex.write_text(source, encoding="utf-8")
    out = tmp_path / "out.html"
    render_file(tex, out)
    return out.read_text(encoding="utf-8")


def _note_rect(html: str, nid: str = "n1") -> tuple[float, float, float, float]:
    m = re.search(
        r'note\[' + nid + r'\]-solo"[^>]*>\s*<rect x="(-?[\d.]+)" y="(-?[\d.]+)"'
        r' width="([\d.]+)" height="([\d.]+)"',
        html,
    )
    assert m, f"note {nid} rect missing"
    return tuple(float(v) for v in m.groups())  # type: ignore[return-value]


def _viewbox(html: str) -> tuple[float, float, float, float]:
    m = re.search(r'viewBox="([\d.\- ]+)"', html)
    assert m
    return tuple(float(v) for v in m.group(1).split()[:4])  # type: ignore[return-value]


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


class TestNoteDodgesCellValue:
    def test_wide_note_clears_corner_value(self, tmp_path: Path) -> None:
        """A wide ``top-right`` note over a labelled array — its natural anchor
        band [8,27] buries the last cell's value "50" (band [13,27]). The placer
        slides the note down into the clear lane below the row."""
        src = (
            '\\begin{animation}[id="d", label="note"]\n'
            '\\shape{a}{Array}{size=5, data=[10,20,30,40,50], labels="0..4"}\n'
            "\\step\n"
            '\\note{n1}{text="zero indexed", at=top-right}\n'
            "\\end{animation}\n"
        )
        html = _render(src, tmp_path)
        nx, ny, nw, nh = _note_rect(html)

        # Locate the value "50" glyph (rightmost, top row) and its band.
        val = re.search(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*>50</text>', html)
        assert val, "value 50 glyph missing"
        vy = float(val.group(2))
        v_lo, v_hi = vy - _VALUE_FONT_PX / 2.0, vy + _VALUE_FONT_PX / 2.0

        assert _overlap(ny, ny + nh, v_lo, v_hi) == 0.0, (
            f"note band [{ny},{ny + nh}] still buries value 50 band "
            f"[{v_lo},{v_hi}]"
        )
        # And it stays inside the viewBox (placer clamps to the board).
        vx0, vy0, vw, vh = _viewbox(html)
        assert vx0 <= nx and nx + nw <= vx0 + vw
        assert vy0 <= ny and ny + nh <= vy0 + vh


class TestNoteByteIdentityWhenClear:
    def test_empty_corner_note_keeps_anchor(self, tmp_path: Path) -> None:
        """A note in an empty corner of a tall board keeps its exact compass
        anchor — the placer is a no-op, so the pill markup is unchanged."""
        src = (
            '\\begin{animation}[id="d", label="note"]\n'
            '\\shape{t}{Tree}{root="A", nodes=["A","B","C"],'
            ' edges=[("A","B"),("A","C")]}\n'
            "\\step\n"
            '\\note{n1}{text="hi", at=top-left}\n'
            "\\end{animation}\n"
        )
        html = _render(src, tmp_path)
        nx, ny, nw, nh = _note_rect(html)
        vx0, vy0, vw, vh = _viewbox(html)
        nat_x, nat_y = _note_anchor_xy("top-left", 0, vx0, vy0, vw, vh, nw, nh)
        assert abs(nx - nat_x) < 0.05 and abs(ny - nat_y) < 0.05, (
            f"clear-corner note moved: emitted=({nx},{ny}) natural=({nat_x},{nat_y})"
        )
