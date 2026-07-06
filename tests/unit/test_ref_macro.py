"""Tests for the ``\\ref{sel}{text}`` narration state-link macro (④, R-39).

``\\ref`` tints ``text`` in the narration with ``sel``'s *current-frame* state
ink (R-36 ``--scriba-annotation-state-*``) when that state is a signalling
colour; an idle / unstated target renders as a bare ``scriba-ref`` (inherits
body colour); an undeclared shape degrades to plain text with a soft **E1322**
warning.  It processes in the same pass-1 stash as ``\\hl`` so its ``<span>``
(and any ``$math$`` in ``text``) survives the narration escape.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scriba.animation.extensions.ref_macro import process_ref_macros

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


class TestRefMacroUnit:
    def test_signal_state_tints(self) -> None:
        out, targets = process_ref_macros(
            r"\ref{a.cell[2]}{pivot}",
            state_of=lambda sel: "current",
        )
        assert '<span class="scriba-ref scriba-ref-state-current">pivot</span>' in out
        assert targets == {"a.cell[2]"}

    def test_each_signal_state_maps_to_class(self) -> None:
        for state in ("current", "done", "dim", "good", "error", "path"):
            out, _ = process_ref_macros(
                r"\ref{a.cell[0]}{x}", state_of=lambda sel, s=state: s
            )
            assert f'scriba-ref-state-{state}' in out

    def test_idle_is_bare_ref(self) -> None:
        out, targets = process_ref_macros(
            r"\ref{a.cell[0]}{x}", state_of=lambda sel: "idle"
        )
        assert '<span class="scriba-ref">x</span>' in out
        assert "scriba-ref-state-" not in out
        # The target still exists (valid shape), so it is a ref target.
        assert targets == {"a.cell[0]"}

    def test_highlight_and_hidden_are_bare(self) -> None:
        for state in ("highlight", "hidden"):
            out, _ = process_ref_macros(
                r"\ref{a.cell[0]}{x}", state_of=lambda sel, s=state: s
            )
            assert '<span class="scriba-ref">x</span>' in out
            assert "scriba-ref-state-" not in out

    def test_unknown_target_warns_and_degrades_to_plain(self) -> None:
        seen: list[tuple[str, str]] = []
        out, targets = process_ref_macros(
            r"before \ref{bogus.cell[0]}{label} after",
            state_of=lambda sel: None,
            warn=lambda code, msg: seen.append((code, msg)),
        )
        assert "label" in out
        assert "scriba-ref" not in out  # no wrapper at all
        assert targets == set()
        assert seen and seen[0][0] == "E1322"

    def test_math_in_text_rendered_via_callback(self) -> None:
        out, _ = process_ref_macros(
            r"\ref{a.cell[1]}{$x^2$}",
            state_of=lambda sel: "done",
            render_inline_tex=lambda t: f"<KX>{t}</KX>",
        )
        assert "<KX>$x^2$</KX>" in out
        assert 'class="scriba-ref scriba-ref-state-done"' in out

    def test_html_in_text_escaped_without_callback(self) -> None:
        out, _ = process_ref_macros(
            r"\ref{a.cell[0]}{<b>bad</b>}", state_of=lambda sel: "current"
        )
        assert "&lt;b&gt;bad&lt;/b&gt;" in out
        assert "<b>" not in out

    def test_no_ref_returns_text_unchanged(self) -> None:
        text = "Plain narration, no macros here."
        out, targets = process_ref_macros(text, state_of=lambda sel: "current")
        assert out == text
        assert targets == set()


class TestRefMacroRender:
    def _render(self, source: str, tmp_path: Path) -> str:
        tex_path = tmp_path / "in.tex"
        tex_path.write_text(source, encoding="utf-8")
        out_path = tmp_path / "out.html"
        render_file(tex_path, out_path)
        return out_path.read_text(encoding="utf-8")

    def test_ref_tint_tracks_state_per_frame(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="ref"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            "\\recolor{a.cell[1]}{state=current}\n"
            "\\narrate{The \\ref{a.cell[1]}{pivot} is chosen.}\n"
            "\\step\n"
            "\\recolor{a.cell[1]}{state=done}\n"
            "\\narrate{The \\ref{a.cell[1]}{pivot} is placed.}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        # Frame 1 tints current; frame 2 tints done — both appear across the
        # print/JS frame copies.
        assert "scriba-ref-state-current" in html_out
        assert "scriba-ref-state-done" in html_out

    def test_ref_prints_in_static_frames(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="ref print"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            "\\recolor{a.cell[0]}{state=good}\n"
            "\\narrate{Look at \\ref{a.cell[0]}{the base}.}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        # The print-frames block is static (no JS); the ref span must be there.
        assert 'class="scriba-print-frames"' in html_out
        assert "scriba-ref-state-good" in html_out
        assert "the base" in html_out

    def test_bad_ref_target_degrades_but_renders(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="ref bad"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            "\\narrate{Typo \\ref{zzz.cell[0]}{here} still shows.}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        # Degrades to plain text — the word renders, no ref span element for it.
        # (The CSS selectors are always inlined; assert on the element form.)
        assert "here" in html_out
        assert 'class="scriba-ref' not in html_out
