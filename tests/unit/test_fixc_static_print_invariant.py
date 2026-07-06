"""Fix C — \\invariant honesty in the static filmstrip and interactive print.

Two static-honesty breaches from investigations/hunt-runtime-static.md:

* **F1 (High)** — a ``\\invariant`` panel is DROPPED ENTIRELY from the
  ``--static`` zero-JS filmstrip (``emit_html(mode="static")`` never hands
  ``invariants`` to ``emit_animation_html``, and that emitter had no invariant
  code). Spec s5.17 promises the panel is "shown across all frames ... visible
  on screen and in print", so the zero-JS filmstrip must carry it per frame.

* **F2 (Medium)** — in the interactive widget's ``@media print`` fallback a
  *live* ``${}`` invariant freezes at frame 0's value: the print frames carry no
  invariant panel, so a single frame-0 panel prints for every frame. Each print
  frame must carry its own frame's resolved value (hidden on screen, shown in
  print — exactly like per-frame narration).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402

# A live invariant (running sum ``s`` recomputed per step) — the panel body and
# the narration interpolate the SAME ``${s}``, so per frame they must agree.
_LIVE_SOURCE = (
    '\\begin{animation}[id="linv", label="live invariant"]\n'
    "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
    "\\invariant{Running sum = ${s}}\n"
    "\\compute{ s = 0 }\n"
    "\\step\n\\compute{ s = 1 }\n\\narrate{Add a[0]: sum is ${s}.}\n"
    "\\step\n\\compute{ s = 3 }\n\\narrate{Add a[1]: sum is ${s}.}\n"
    "\\step\n\\compute{ s = 6 }\n\\narrate{Add a[2]: sum is ${s}.}\n"
    "\\end{animation}\n"
)

# A static invariant (no ``${``) — same predicate on every frame.
_STATIC_SOURCE = (
    '\\begin{animation}[id="sinv", label="static invariant"]\n'
    "\\shape{a}{Array}{size=2, data=[1,2]}\n"
    "\\invariant{loop keeps the prefix sorted}\n"
    "\\step\n\\narrate{Step one.}\n"
    "\\step\n\\narrate{Step two.}\n"
    "\\end{animation}\n"
)


def _render(source: str, tmp_path: Path, *, mode: str = "interactive") -> str:
    tex = tmp_path / "in.tex"
    out = tmp_path / "out.html"
    tex.write_text(source, encoding="utf-8")
    render_file(tex, out, output_mode=mode, minify=False)
    return out.read_text(encoding="utf-8")


def _filmstrip_frames(html_out: str) -> list[str]:
    """Split the static ``<figure>`` filmstrip into per-``<li>`` frame blocks."""
    marker = '<li class="scriba-frame"'
    parts = html_out.split(marker)
    return [marker + p for p in parts[1:]]


def _print_frames(html_out: str) -> list[str]:
    """Split the interactive widget into per-print-frame blocks."""
    marker = '<div class="scriba-print-frame"'
    parts = html_out.split(marker)
    return [marker + p for p in parts[1:]]


# ---------------------------------------------------------------------------
# F1 — static filmstrip carries the invariant per frame
# ---------------------------------------------------------------------------


class TestStaticFilmstripInvariant:
    def test_static_invariant_present_in_filmstrip(self, tmp_path: Path) -> None:
        html_out = _render(_STATIC_SOURCE, tmp_path, mode="static")
        # The zero-JS filmstrip is a <figure> of <li> frames (no widget div;
        # ``.scriba-widget`` still appears in the inlined CSS, so match the
        # element markup, not the bare class token).
        assert '<figure class="scriba-animation"' in html_out
        assert '<div class="scriba-widget"' not in html_out
        # The predicate must appear (previously it was dropped entirely).
        assert "loop keeps the prefix sorted" in html_out
        assert 'class="scriba-invariant"' in html_out

    def test_static_invariant_repeated_on_every_frame(self, tmp_path: Path) -> None:
        html_out = _render(_STATIC_SOURCE, tmp_path, mode="static")
        frames = _filmstrip_frames(html_out)
        assert len(frames) == 2, f"expected 2 filmstrip frames, got {len(frames)}"
        for frame in frames:
            assert 'class="scriba-invariant"' in frame
            assert "loop keeps the prefix sorted" in frame

    def test_live_invariant_resolves_per_frame_in_filmstrip(
        self, tmp_path: Path
    ) -> None:
        html_out = _render(_LIVE_SOURCE, tmp_path, mode="static")
        frames = _filmstrip_frames(html_out)
        assert len(frames) == 3, f"expected 3 filmstrip frames, got {len(frames)}"
        # Frame k carries frame-k's own resolved running sum (1 / 3 / 6),
        # NOT a single frozen value.
        for value, frame in zip(("1", "3", "6"), frames):
            assert f"Running sum = {value}" in frame, frame
        # The raw ${} placeholder never leaks into the static output.
        assert "Running sum = ${s}" not in html_out


# ---------------------------------------------------------------------------
# F2 — interactive print frames carry each frame's own invariant value
# ---------------------------------------------------------------------------


class TestInteractivePrintInvariant:
    def test_live_print_frames_carry_own_value(self, tmp_path: Path) -> None:
        html_out = _render(_LIVE_SOURCE, tmp_path, mode="interactive")
        frames = _print_frames(html_out)
        assert len(frames) == 3, f"expected 3 print frames, got {len(frames)}"
        # Each print frame carries its OWN running sum inside an invariant panel
        # (not the frame-0 value for all three).
        for value, frame in zip(("1", "3", "6"), frames):
            assert 'class="scriba-invariant"' in frame, frame
            assert f"Running sum = {value}" in frame, frame

    def test_static_invariant_interactive_byte_stable(self, tmp_path: Path) -> None:
        """A no-``${`` invariant keeps EXACTLY one panel (the pinned widget-level
        one) — the print frames do not gain a redundant per-frame copy, so the
        static-invariant output is unchanged."""
        html_out = _render(_STATIC_SOURCE, tmp_path, mode="interactive")
        assert html_out.count('class="scriba-invariant"') == 1
