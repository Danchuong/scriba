"""DECORATE design, verb 2 — the untethered ``\\note`` callout.

``\\note{id}{text=..., at=<anchor>}`` drops a free margin callout pill keyed
``note[{id}]-solo``, painted inside the existing viewBox at a board-relative
anchor. It is a stage-level command (a sibling of ``\\link``): not tied to any
shape, riding the shipped ``annotation_add`` / ``annotation_remove`` /
``annotation_recolor`` contract with zero new motion kinds. Fills the
teaching-framing census's untethered-note gap (investigations/
teaching-framing-attention.md): before this, every callout had to hang off a
shape selector (E1010 on a raw coordinate).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from scriba.animation.differ import compute_transitions
from scriba.animation.emitter import FrameData
from scriba.animation.parser.grammar import SceneParser
from scriba.core.errors import ValidationError

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


def _notes(src: str) -> list:
    ir = SceneParser().parse(src)
    return [
        c
        for f in ir.frames
        for c in f.commands
        if type(c).__name__ == "NoteCommand"
    ]


def _render(source: str, tmp_path: Path) -> str:
    tex_path = tmp_path / "in.tex"
    tex_path.write_text(source, encoding="utf-8")
    out_path = tmp_path / "out.html"
    render_file(tex_path, out_path)
    return out_path.read_text(encoding="utf-8")


class TestGrammar:
    def test_note_parses_to_command(self) -> None:
        cmds = _notes(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            '\\note{n1}{text="careful: 0-indexed", at=top-right, color=warn}\n'
        )
        assert cmds, "no NoteCommand parsed"
        assert cmds[0].note_id == "n1"
        assert cmds[0].text == "careful: 0-indexed"
        assert cmds[0].at == "top-right"
        assert cmds[0].color == "warn"

    def test_note_default_anchor(self) -> None:
        cmds = _notes(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            '\\note{n1}{text="hi"}\n'
        )
        assert cmds and cmds[0].at in {
            "top-left", "top", "top-right", "right",
            "bottom-right", "bottom", "bottom-left", "left",
        }

    def test_note_missing_text_raises_e1120(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _notes(
                "\\shape{a}{Array}{size=2, data=[1,2]}\n"
                "\\step\n"
                "\\note{n1}{}\n"
            )
        assert exc.value.code == "E1120"

    def test_note_missing_id_raises_e1120(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _notes(
                "\\shape{a}{Array}{size=2, data=[1,2]}\n"
                "\\step\n"
                '\\note{}{text="hi"}\n'
            )
        assert exc.value.code == "E1120"

    def test_note_bad_anchor_raises_e1121(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _notes(
                "\\shape{a}{Array}{size=2, data=[1,2]}\n"
                "\\step\n"
                '\\note{n1}{text="hi", at=nowhere}\n'
            )
        assert exc.value.code == "E1121"


class TestEmit:
    def test_note_emits_solo_key_at_anchor(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="note"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            '\\note{n1}{text="hi there", at=top-right, color=warn}\n'
            "\\end{animation}\n"
        )
        html_out = _render(source, tmp_path)
        assert 'data-annotation="note[n1]-solo"' in html_out
        assert "hi there" in html_out
        # Rides the shipped annotation color classes — no dedicated note CSS.
        assert "scriba-annotation-warn" in html_out

    def test_note_coord_inside_viewbox(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="note"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            '\\note{n1}{text="x", at=top-right}\n'
            "\\end{animation}\n"
        )
        html_out = _render(source, tmp_path)
        vb = re.search(r'viewBox="([\d.\- ]+)"', html_out)
        assert vb
        min_x, min_y, w, h = (float(v) for v in vb.group(1).split())
        note = re.search(
            r'data-annotation="note\[n1\]-solo"[^>]*>\s*<rect x="(-?[\d.]+)" '
            r'y="(-?[\d.]+)"',
            html_out,
        )
        assert note, "note pill rect missing"
        nx, ny = float(note.group(1)), float(note.group(2))
        assert min_x <= nx <= min_x + w
        assert min_y <= ny <= min_y + h


class TestDiffer:
    def _frame(self, notes: list[dict]) -> FrameData:
        return FrameData(
            step_number=1,
            total_frames=2,
            narration_html="",
            shape_states={},
            annotations=[],
            notes=notes,
        )

    def test_note_add_rides_annotation_add(self) -> None:
        prev = self._frame([])
        curr = self._frame([{"id": "n1", "text": "x", "color": "info"}])
        kinds = {t.kind for t in compute_transitions(prev, curr).transitions}
        assert kinds == {"annotation_add"}
        t = compute_transitions(prev, curr).transitions[0]
        assert t.target == "note[n1]-solo"

    def test_note_remove_rides_annotation_remove(self) -> None:
        prev = self._frame([{"id": "n1", "text": "x", "color": "info"}])
        curr = self._frame([])
        kinds = {t.kind for t in compute_transitions(prev, curr).transitions}
        assert kinds == {"annotation_remove"}

    def test_note_recolor_rides_annotation_recolor(self) -> None:
        prev = self._frame([{"id": "n1", "text": "x", "color": "info"}])
        curr = self._frame([{"id": "n1", "text": "x", "color": "warn"}])
        kinds = {t.kind for t in compute_transitions(prev, curr).transitions}
        assert kinds == {"annotation_recolor"}

    def test_note_only_closed_kinds(self) -> None:
        _CLOSED = {
            "annotation_add", "annotation_remove", "annotation_recolor",
        }
        prev = self._frame([{"id": "n1", "text": "x", "color": "info"}])
        curr = self._frame(
            [
                {"id": "n1", "text": "x", "color": "good"},
                {"id": "n2", "text": "y", "color": "info"},
            ]
        )
        for t in compute_transitions(prev, curr).transitions:
            assert t.kind in _CLOSED


class TestDeterminism:
    def test_note_same_coord_across_frames(self, tmp_path: Path) -> None:
        # A persistent note spans both frames; the viewBox is byte-identical
        # every frame, so the note lands in the same spot each time.
        source = (
            '\\begin{animation}[id="d", label="note determinism"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            '\\note{n1}{text="pin", at=bottom-left}\n'
            "\\step\n"
            "\\recolor{a.cell[0]}{state=current}\n"
            "\\end{animation}\n"
        )
        html_out = _render(source, tmp_path)
        groups = re.findall(
            r'(<g[^>]*data-annotation="note\[n1\]-solo".*?</g>)',
            html_out,
        )
        assert len(groups) >= 2, "note should appear in both frames"
        assert len(set(groups)) == 1, "note geometry drifted between frames"


class TestNoteMathAndBidi:
    """sweep3-decor M6 + LOW: docs §5.21 promise ``$math$`` in \\note text
    (the pill channel already renders it via KaTeX foreignObject), and the
    0.29 bidi-isolation fix shipped only on annotation pills — notes were
    left stripping math to literal text and scrambling RTL."""

    def test_note_math_renders_katex_not_stripped(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="note math"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            '\\note{n1}{text="$O(n \\log n)$", at=bottom-left}\n'
            "\\end{animation}\n"
        )
        html_out = _render(source, tmp_path)
        groups = re.findall(
            r'(<g[^>]*data-annotation="note\[n1\]-solo".*?</g>)',
            html_out,
            re.S,
        )
        assert groups, "note group missing"
        g = groups[0]
        assert "foreignObject" in g, (
            "math note must render through the KaTeX foreignObject path"
        )
        # aria-label rightly carries the stripped plain text; the PAINTED
        # content must not.
        painted = re.sub(r'aria-label="[^"]*"', "", g)
        assert "O(nlog n)" not in painted and "O(n log n)" not in painted, (
            "math note painted as stripped literal text"
        )

    def test_note_rtl_carries_bidi_isolation(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="note rtl"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            '\\note{n1}{text="مرحبا بالعالم", at=top-left}\n'
            "\\end{animation}\n"
        )
        html_out = _render(source, tmp_path)
        groups = re.findall(
            r'(<g[^>]*data-annotation="note\[n1\]-solo".*?</g>)',
            html_out,
            re.S,
        )
        assert groups, "note group missing"
        assert "unicode-bidi:plaintext" in groups[0], (
            "RTL note text must carry bidi isolation (0.29 pill parity)"
        )

    def test_note_plain_ltr_emit_unchanged(self, tmp_path: Path) -> None:
        # The plain-LTR note keeps its exact pre-fix <text> shape — the
        # byte-identity guard for the whole existing corpus.
        source = (
            '\\begin{animation}[id="d", label="note plain"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            '\\note{n1}{text="careful", at=top-right}\n'
            "\\end{animation}\n"
        )
        html_out = _render(source, tmp_path)
        groups = re.findall(
            r'(<g[^>]*data-annotation="note\[n1\]-solo".*?</g>)',
            html_out,
            re.S,
        )
        assert groups, "note group missing"
        assert (
            'style="text-anchor:middle;dominant-baseline:central"' in groups[0]
        ), "plain note <text> style changed — corpus would churn"
        assert "foreignObject" not in groups[0]
