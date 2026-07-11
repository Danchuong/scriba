"""Tests for the ``.scriba-invariant-panel`` theorem-box wrapper (⑩b restyle).

``_invariant_panel_elements`` (scriba/animation/_html_stitcher.py) wraps the
emitted ``<p class="scriba-invariant" role="note">`` run in a single
``<div class="scriba-invariant-panel">`` chrome container, replacing the old
per-``<p>`` border-inline-start look (chrome moves to the wrapper). N stacked
``\\invariant`` calls land inside ONE wrapper. The wrapper is deliberately
caption-less: no visible label, no ``aria-label`` — the box chrome itself is
the signifier, so the feature carries no hardcoded human-language string
(i18n directive; a user may author in any language).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402

_WRAPPER_OPEN_RE = re.compile(r'<div class="scriba-invariant-panel"[^>]*>')

_SINGLE_SOURCE = (
    '\\begin{animation}[id="d", label="inv"]\n'
    "\\shape{a}{Array}{size=2, data=[1,2]}\n"
    "\\invariant{loop keeps the prefix sorted}\n"
    "\\step\n"
    "\\narrate{Step one.}\n"
    "\\end{animation}\n"
)

_STACKED_SOURCE = (
    '\\begin{animation}[id="d2", label="inv stacked"]\n'
    "\\shape{a}{Array}{size=2, data=[1,2]}\n"
    "\\invariant{first predicate}\n"
    "\\invariant{second predicate}\n"
    "\\step\n"
    "\\narrate{Step one.}\n"
    "\\end{animation}\n"
)


def _render(source: str, tmp_path: Path, **kwargs: object) -> str:
    tex_path = tmp_path / "in.tex"
    tex_path.write_text(source, encoding="utf-8")
    out_path = tmp_path / "out.html"
    render_file(tex_path, out_path, **kwargs)
    return out_path.read_text(encoding="utf-8")


class TestWrapperPresence:
    def test_single_invariant_gets_one_wrapper(self, tmp_path: Path) -> None:
        html_out = _render(_SINGLE_SOURCE, tmp_path)
        assert html_out.count('class="scriba-invariant-panel"') == 1
        # Inner <p> stays byte-identical (existing substring/count contracts
        # in test_invariant.py / test_invariant_interpolation.py).
        assert (
            '<p class="scriba-invariant" role="note">'
            "loop keeps the prefix sorted</p>" in html_out
        )

    def test_stacked_invariants_share_one_wrapper(self, tmp_path: Path) -> None:
        html_out = _render(_STACKED_SOURCE, tmp_path)
        # Exactly ONE wrapper even though there are two \invariant calls.
        assert html_out.count('class="scriba-invariant-panel"') == 1
        # Both predicates rendered, as two separate inner <p> elements.
        assert html_out.count('class="scriba-invariant" role="note"') == 2
        assert "first predicate" in html_out
        assert "second predicate" in html_out

    def test_wrapper_present_in_static_filmstrip(self, tmp_path: Path) -> None:
        html_out = _render(_SINGLE_SOURCE, tmp_path, output_mode="static")
        assert 'class="scriba-invariant-panel"' in html_out

    def test_wrapper_present_in_interactive_print_frames(
        self, tmp_path: Path
    ) -> None:
        # A live (${}) invariant so each print frame carries its own panel.
        source = (
            '\\begin{animation}[id="linv2", label="live"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\invariant{Running sum = ${s}}\n"
            "\\compute{ s = 0 }\n"
            "\\step\n\\compute{ s = 1 }\n\\narrate{One.}\n"
            "\\step\n\\compute{ s = 2 }\n\\narrate{Two.}\n"
            "\\end{animation}\n"
        )
        html_out = _render(source, tmp_path, output_mode="interactive")
        marker = '<div class="scriba-print-frame"'
        frames = [marker + p for p in html_out.split(marker)[1:]]
        assert len(frames) == 2
        for frame in frames:
            assert 'class="scriba-invariant-panel"' in frame


class TestNoHardcodedLanguageString:
    def test_wrapper_tag_carries_no_extra_attributes(self, tmp_path: Path) -> None:
        html_out = _render(_SINGLE_SOURCE, tmp_path)
        matches = _WRAPPER_OPEN_RE.findall(html_out)
        assert matches, "expected a .scriba-invariant-panel wrapper"
        for tag in matches:
            # No aria-label, no role, no other attribute snuck onto the
            # wrapper — the box chrome is the only signifier.
            assert tag == '<div class="scriba-invariant-panel">', tag

    def test_no_label_class_or_caption_span(self, tmp_path: Path) -> None:
        html_out = _render(_STACKED_SOURCE, tmp_path)
        assert "scriba-invariant-label" not in html_out
        assert 'aria-label="Invariant"' not in html_out
        assert ">Invariant<" not in html_out
