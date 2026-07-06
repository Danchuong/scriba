"""Decoration-geometry honesty — five structural fixes (0.26.x hunt follow-up).

Each fix closes a case where a decoration's rendered geometry lied about what
the author asked for. Sources: investigations/hunt-feature-interactions.md
(strike x hidden, note x zoom) + investigations/hunt-authoring-traps-026.md
(F1 note overflow, F2 at= detonation, F4 bare-shape annotate).

FIX 1  strike over a state=hidden cell must be SKIPPED (design-decorate.md
       :279-280) — the strike <g> is a sibling of the display:none cell, so it
       would otherwise float a diagonal over a blank slot.
FIX 2  a \\note wider than the board WRAPS (annotation-pill machinery); a note
       that still cannot fit is clamped into the viewBox + soft-warns E1125.
FIX 3  a \\note on a \\zoom frame anchors to the CROPPED viewBox so compass
       anchors stay corner-pinned inside the crop.
FIX 4  \\annotate{shape}{strike=true|label=..} on a BARE shape resolves to the
       whole-shape content box (strike) / warns E1119 (label) instead of a
       silent no-op.
FIX 5  at=[row,col] COMPACTS empty grid tracks, so a sparse/typo'd index can no
       longer detonate the board into a multi-megapixel canvas.
"""

from __future__ import annotations

import re
import sys
import types
import warnings
from pathlib import Path

import pytest

from scriba.animation.primitives.array import ArrayPrimitive

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


def _render(source: str, tmp_path: Path) -> str:
    tex = tmp_path / "in.tex"
    tex.write_text(source, encoding="utf-8")
    out = tmp_path / "out.html"
    render_file(tex, out)
    return out.read_text(encoding="utf-8")


def _viewboxes(html: str) -> list[str]:
    return re.findall(r'class="scriba-stage-svg" viewBox="([\d.\- ]+)"', html)


def _note_group(html: str) -> str | None:
    m = re.search(r'(<g[^>]*data-annotation="note\[n1\]-solo".*?</g>)', html, re.S)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# FIX 1 — strike over a hidden (display:none) cell is skipped.
# ---------------------------------------------------------------------------


class TestFix1StrikeOverHidden:
    def test_strike_over_hidden_cell_is_skipped(self) -> None:
        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        a.set_state("cell[1]", "hidden")
        a.set_annotations([{"target": "a.cell[1]", "strike": True}])
        svg = a.emit_svg()
        assert "scriba-state-hidden" in svg  # the cell IS hidden
        assert "a.cell[1]-strike" not in svg  # ...so no floating strike

    def test_strike_over_visible_cell_still_drawn(self) -> None:
        # Regression guard: strike over a NON-hidden cell is unaffected.
        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        a.set_state("cell[1]", "current")
        a.set_annotations([{"target": "a.cell[1]", "strike": True}])
        svg = a.emit_svg()
        assert "a.cell[1]-strike" in svg

    def test_strike_over_idle_cell_still_drawn(self) -> None:
        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        a.set_annotations([{"target": "a.cell[1]", "strike": True}])
        assert "a.cell[1]-strike" in a.emit_svg()

    def test_strike_over_hidden_via_scene(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            "\\recolor{a.cell[1]}{state=hidden}\n"
            "\\annotate{a.cell[1]}{strike=true}\n"
            "\\end{animation}\n"
        )
        html = _render(source, tmp_path)
        assert "a.cell[1]-strike" not in html


# ---------------------------------------------------------------------------
# FIX 4 — bare-shape \annotate resolves to the whole-shape box (strike) or
# warns (label), instead of a silent no-op.
# ---------------------------------------------------------------------------


class TestFix4BareShapeAnnotate:
    def test_bare_shape_strike_unit_spans_content_box(self) -> None:
        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        a.set_annotations([{"target": "a", "strike": True}])
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # must NOT warn E1119 anymore
            svg = a.emit_svg()
        assert "a-strike" in svg
        m = re.search(
            r'data-annotation="a-strike"[^>]*>\s*<line ([^>]+)/>', svg
        )
        assert m, "bare-shape strike line missing"
        line = m.group(1)
        x1 = float(re.search(r'x1="(-?[\d.]+)"', line).group(1))
        x2 = float(re.search(r'x2="(-?[\d.]+)"', line).group(1))
        y1 = float(re.search(r'y1="(-?[\d.]+)"', line).group(1))
        y2 = float(re.search(r'y2="(-?[\d.]+)"', line).group(1))
        assert x1 != x2 and y1 != y2  # diagonal, corner to corner
        # Spans (roughly) the whole 3-cell row, not a single cell.
        assert abs(x2 - x1) > 100

    def test_bare_shape_strike_via_scene(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            "\\annotate{a}{strike=true}\n"
            "\\end{animation}\n"
        )
        html = _render(source, tmp_path)
        assert 'data-annotation="a-strike"' in html

    def test_bare_shape_label_warns_e1119(self) -> None:
        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        a.set_annotations([{"target": "a", "label": "hi"}])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            a.emit_svg()
        assert any("E1119" in str(x.message) for x in w)


# ---------------------------------------------------------------------------
# FIX 2 — \note overflow wraps; an unfittable note clamps + warns E1125.
# ---------------------------------------------------------------------------


class TestFix2NoteWrap:
    def test_short_note_stays_single_line(self, tmp_path: Path) -> None:
        # Byte-identity guard: a short note fits and must NOT wrap (no tspan).
        source = (
            '\\begin{animation}[id="d"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            '\\note{n1}{text="hi there", at=top-right}\n'
            "\\end{animation}\n"
        )
        html = _render(source, tmp_path)
        grp = _note_group(html)
        assert grp is not None
        assert "<tspan" not in grp  # single line
        assert "hi there" in grp

    def test_long_note_wraps_and_stays_in_viewbox(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            '\\note{n1}{text="careful: off-by-one the window is half-open [lo, hi)", at=top-right}\n'
            "\\end{animation}\n"
        )
        html = _render(source, tmp_path)
        vb = _viewboxes(html)[0]
        minx, miny, w, h = (float(v) for v in vb.split())
        grp = _note_group(html)
        assert grp is not None
        # Wrapped into multiple lines.
        tspans = re.findall(r'<tspan x="(-?[\d.]+)"', grp)
        assert len(tspans) >= 2, f"expected wrapped tspans, got {grp!r}"
        # Every painted x-coordinate lies inside the viewBox.
        rect_xs = [float(x) for x in re.findall(r'<rect x="(-?[\d.]+)"[^>]*width="(-?[\d.]+)"', grp) for x in [x[0]]]
        rect = re.search(r'<rect x="(-?[\d.]+)" y="(-?[\d.]+)" width="(-?[\d.]+)"', grp)
        rx, ry, rw = float(rect.group(1)), float(rect.group(2)), float(rect.group(3))
        assert minx <= rx and rx + rw <= minx + w, f"note rect {rx}+{rw} outside [{minx},{minx+w}]"
        for tx in tspans:
            assert minx <= float(tx) <= minx + w

    def test_unfittable_note_clamps_and_warns_e1125(self) -> None:
        # A note far wider than a tiny board cannot be wrapped small enough;
        # it must clamp into the viewBox AND soft-warn E1125.
        from scriba.animation._frame_renderer import _emit_scene_notes

        frame = types.SimpleNamespace(
            notes=[{"id": "n1", "text": "W" * 60, "at": "top-right", "color": "info"}]
        )
        parts: list[str] = []
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _emit_scene_notes(frame, "0 0 40 60", parts)
        blob = "".join(parts)
        assert any("E1125" in str(x.message) for x in w), "expected E1125 warn"
        # Every painted x lies within the 0..40 viewBox.
        for x in re.findall(r'x="(-?[\d.]+)"', blob):
            assert -0.01 <= float(x) <= 40.01, f"x={x} escaped the clamped viewBox"


# ---------------------------------------------------------------------------
# FIX 3 — a \note on a \zoom frame anchors to the cropped viewBox.
# ---------------------------------------------------------------------------


class TestFix3NoteUnderZoom:
    def test_note_pinned_inside_zoom_crop(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d"]\n'
            "\\shape{a}{Array}{size=6, data=[1,2,3,4,5,6]}\n"
            "\\step\n"
            '\\note{n1}{text="hi", at=top-right}\n'
            "\\zoom{a.cell[0]}\n"
            "\\end{animation}\n"
        )
        html = _render(source, tmp_path)
        vb = _viewboxes(html)[0]
        cx, cy, cw, ch = (float(v) for v in vb.split())
        # Not the full board — the crop actually happened.
        assert cw < 300, f"expected a crop, got viewBox {vb}"
        grp = _note_group(html)
        assert grp is not None
        rect = re.search(r'<rect x="(-?[\d.]+)" y="(-?[\d.]+)" width="(-?[\d.]+)"', grp)
        nx, ny, nw = float(rect.group(1)), float(rect.group(2)), float(rect.group(3))
        # Note is inside the cropped viewBox, pinned to its top-right corner.
        assert cx <= nx and nx + nw <= cx + cw, f"note x {nx}+{nw} outside crop [{cx},{cx+cw}]"
        assert nx + nw > cx + cw / 2.0, "top-right note should sit in the right half of the crop"

    def test_note_without_zoom_uses_full_board(self, tmp_path: Path) -> None:
        # Regression: a non-zoom frame anchors the note to the full board.
        source = (
            '\\begin{animation}[id="d"]\n'
            "\\shape{a}{Array}{size=6, data=[1,2,3,4,5,6]}\n"
            "\\step\n"
            '\\note{n1}{text="hi", at=top-right}\n'
            "\\end{animation}\n"
        )
        html = _render(source, tmp_path)
        vb = _viewboxes(html)[0]
        cx, cy, cw, ch = (float(v) for v in vb.split())
        grp = _note_group(html)
        rect = re.search(r'<rect x="(-?[\d.]+)"[^>]*width="(-?[\d.]+)"', grp)
        nx, nw = float(rect.group(1)), float(rect.group(2))
        assert nx + nw > cw / 2.0  # anchored to the full-board right edge


# ---------------------------------------------------------------------------
# FIX 5 — at=[row,col] compacts empty tracks (no board detonation).
# ---------------------------------------------------------------------------


class TestFix5AtCompaction:
    def _board_vb(self, tmp_path: Path, a_pos: str, b_pos: str) -> str:
        source = (
            '\\begin{animation}[id="d"]\n'
            f"\\shape{{a}}{{Array}}{{values=[1,2,3], at={a_pos}}}\n"
            f"\\shape{{b}}{{Array}}{{values=[4,5,6], at={b_pos}}}\n"
            "\\step\n"
            "\\narrate{x}\n"
            "\\end{animation}\n"
        )
        return _viewboxes(_render(source, tmp_path))[0]

    def test_sparse_indices_compact_to_dense(self, tmp_path: Path) -> None:
        sparse = self._board_vb(tmp_path, "[0,0]", "[100,100]")
        dense = self._board_vb(tmp_path, "[0,0]", "[1,1]")
        assert sparse == dense, f"sparse {sparse!r} != dense {dense!r}"

    def test_dense_board_unchanged(self, tmp_path: Path) -> None:
        # Golden guard: an already-dense board is byte-identical (compaction is
        # identity when occupied tracks are 0..N-1 contiguous).
        dense = self._board_vb(tmp_path, "[0,0]", "[1,1]")
        assert dense == "0 0 412 124"

    def test_extreme_index_no_detonation(self, tmp_path: Path) -> None:
        vb = self._board_vb(tmp_path, "[0,0]", "[100000,100000]")
        w, h = int(vb.split()[2]), int(vb.split()[3])
        assert w < 1000 and h < 1000, f"board detonated: {vb}"
