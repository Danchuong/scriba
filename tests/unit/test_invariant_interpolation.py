"""Tests for live ``${}`` interpolation on the ``\\invariant`` panel (⑩b).

Historically ``\\invariant`` was **static v1**: its body was rendered once and
``${name}`` placeholders leaked literally (``Running sum = ${s}``), so a teacher
could not keep a running invariant value in sync with a ``\\compute`` binding.

This suite pins the *live* behaviour: an invariant body containing ``${...}`` is
resolved **per frame** against the same per-frame binding scope narration uses
(``SceneState._interpolate_narration``), the static panel shows frame 0's
resolved value, and each step's value is threaded into the interactive runtime.

Byte-stability gate: an invariant with **no** ``${`` stays byte-identical to the
static v1 panel and emits no per-frame runtime key.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402

# A live invariant: the running sum ``s`` is recomputed per step (global s=0 in
# the prelude, then 1 / 3 / 6 inside the three steps). The invariant body and
# the narration both interpolate the SAME ``${s}``, so they must agree per frame.
_LIVE_SOURCE = (
    '\\begin{animation}[id="linv", label="live invariant"]\n'
    "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
    "\\invariant{Running sum = ${s}}\n"
    "\\compute{ s = 0 }\n"
    "\\step\n"
    "\\compute{ s = 1 }\n"
    "\\narrate{Add a[0]: sum is ${s}.}\n"
    "\\step\n"
    "\\compute{ s = 3 }\n"
    "\\narrate{Add a[1]: sum is ${s}.}\n"
    "\\step\n"
    "\\compute{ s = 6 }\n"
    "\\narrate{Add a[2]: sum is ${s}.}\n"
    "\\end{animation}\n"
)

# A static invariant: no ``${`` anywhere. Must stay byte-identical to static v1.
_STATIC_SOURCE = (
    '\\begin{animation}[id="sinv", label="static invariant"]\n'
    "\\shape{a}{Array}{size=2, data=[1,2]}\n"
    "\\invariant{loop keeps the prefix sorted}\n"
    "\\step\n"
    "\\narrate{Step one.}\n"
    "\\step\n"
    "\\narrate{Step two.}\n"
    "\\end{animation}\n"
)

# The exact static-v1 panel bytes — pinned so a regression in the emitter is
# caught even if the class/role attributes are preserved elsewhere.
_STATIC_PANEL = (
    '<p class="scriba-invariant" role="note">loop keeps the prefix sorted</p>'
)


def _render(source: str, tmp_path: Path) -> str:
    tex_path = tmp_path / "in.tex"
    tex_path.write_text(source, encoding="utf-8")
    out_path = tmp_path / "out.html"
    render_file(tex_path, out_path)
    return out_path.read_text(encoding="utf-8")


def _js_frame_objects(html_out: str) -> list[str]:
    """Return one text block per inline frame, split at the ``{svg:`` boundary.

    The inline frames array literal is ``var frames=[ {svg:`...`,narration:`...`
    ,...,inv:[...]} , ... ]``. SVG template literals contain real newlines and
    escaped backticks, so a single-regex object match is fragile; splitting on
    the stable ``{svg:`` frame delimiter is not. Each returned block holds one
    frame's narration + (once live) its ``inv`` payload.
    """
    marker = "var frames=["
    region = html_out[html_out.index(marker) + len(marker):]
    return region.split("{svg:`")[1:]


class TestLiveInvariant:
    def test_invariant_interpolates_value_not_literal(self, tmp_path: Path) -> None:
        """The static panel shows frame 0's resolved value, never ``${s}``."""
        html_out = self._render_live(tmp_path)
        # Frame-0 binding is the step-local s=1, NOT the prelude global s=0 —
        # proving the invariant resolves against the per-frame scope.
        assert (
            '<p class="scriba-invariant" role="note">Running sum = 1</p>' in html_out
        )
        # The literal placeholder must be gone from the panel.
        assert "Running sum = ${s}" not in html_out
        assert "Running sum = \\${s}" not in html_out

    def test_invariant_updates_per_step(self, tmp_path: Path) -> None:
        """Each step threads its own resolved invariant into the runtime."""
        html_out = self._render_live(tmp_path)
        # Per-frame invariant payloads land in the inline frame array.
        assert "inv:[" in html_out
        # The three running values are each present as a per-frame invariant.
        assert "`Running sum = 1`" in html_out
        assert "`Running sum = 3`" in html_out
        assert "`Running sum = 6`" in html_out

    def test_invariant_scope_matches_narration(self, tmp_path: Path) -> None:
        """In every frame the invariant value equals the narration value —
        both resolve ``${s}`` against the identical per-frame binding scope."""
        html_out = self._render_live(tmp_path)
        frames = _js_frame_objects(html_out)
        assert len(frames) == 3, f"expected 3 frame objects, got {len(frames)}"
        for value, frame in zip(("1", "3", "6"), frames):
            assert f"sum is {value}." in frame, frame
            assert f"Running sum = {value}" in frame, frame

    def _render_live(self, tmp_path: Path) -> str:
        return _render(_LIVE_SOURCE, tmp_path)


class TestStaticInvariantByteStability:
    def test_static_panel_byte_identical(self, tmp_path: Path) -> None:
        """A no-``${`` invariant keeps the exact static-v1 panel bytes."""
        html_out = _render(_STATIC_SOURCE, tmp_path)
        assert _STATIC_PANEL in html_out
        # Exactly one panel across all frames (still emitted once, statically).
        assert html_out.count('class="scriba-invariant" role="note"') == 1

    def test_static_invariant_emits_no_per_frame_key(self, tmp_path: Path) -> None:
        """The per-frame runtime path is untaken for a static invariant, so no
        ``inv:`` key appears in the frame array (byte-stability gate)."""
        html_out = _render(_STATIC_SOURCE, tmp_path)
        assert "inv:[" not in html_out
