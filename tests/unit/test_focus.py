"""Tests for the ``\\focus{sel}`` spotlight command (⑤, R-40).

``\\focus`` clones the ``\\highlight`` command spine: lexer keyword →
``FocusCommand`` AST → ephemeral scene set → snapshot → ``FrameData`` →
baked ``scriba-defocused`` class on every addressable part of a *focused*
shape that is NOT in the focus set.  It is ephemeral (cleared at the next
``\\step``, so it auto-reverts) and dims only shapes that carry a ``\\focus``
this frame — other shapes are untouched.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.scene import SceneState
from scriba.core.errors import ValidationError

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


def _materialise(body: str):
    """Parse *body* and drive SceneState, returning the per-frame snapshots."""
    ir = SceneParser().parse(body)
    state = SceneState()
    state.apply_prelude(
        shapes=ir.shapes,
        prelude_commands=ir.prelude_commands,
        prelude_compute=ir.prelude_compute,
    )
    return [state.apply_frame(f) for f in ir.frames]


def _targets_with_defocus(html: str) -> set[str]:
    """Return the set of ``data-target`` values whose ``<g>`` is defocused."""
    result: set[str] = set()
    for m in re.finditer(r'<g data-target="([^"]+)" class="([^"]*)"', html):
        if "scriba-defocused" in m.group(2):
            result.add(m.group(1))
    return result


class TestFocusScene:
    def test_focus_records_target(self) -> None:
        snaps = _materialise(
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            "\\focus{a.cell[1]}\n"
        )
        assert snaps[0].focus == frozenset({"a.cell[1]"})

    def test_focus_is_ephemeral(self) -> None:
        snaps = _materialise(
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            "\\focus{a.cell[1]}\n"
            "\\step\n"
            "\\apply{a.cell[0]}{state=current}\n"
        )
        assert snaps[0].focus == frozenset({"a.cell[1]"})
        # Auto-reverse: the next step carries no focus.
        assert snaps[1].focus == frozenset()

    def test_focus_union(self) -> None:
        snaps = _materialise(
            "\\shape{a}{Array}{size=4, data=[1,2,3,4]}\n"
            "\\step\n"
            "\\focus{a.cell[1]}\n"
            "\\focus{a.cell[2]}\n"
        )
        assert snaps[0].focus == frozenset({"a.cell[1]", "a.cell[2]"})

    def test_focus_undeclared_shape_raises_e1116(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _materialise(
                "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
                "\\step\n"
                "\\focus{b.cell[0]}\n"
            )
        assert exc.value.code == "E1116"


class TestFocusEmit:
    def _render(self, source: str, tmp_path: Path) -> str:
        tex_path = tmp_path / "in.tex"
        tex_path.write_text(source, encoding="utf-8")
        out_path = tmp_path / "out.html"
        render_file(tex_path, out_path)
        return out_path.read_text(encoding="utf-8")

    def test_defocus_on_complement_only(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="focus"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            "\\focus{a.cell[1]}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        dimmed = _targets_with_defocus(html_out)
        # The focused cell is NOT dimmed; its complement IS.
        assert "a.cell[1]" not in dimmed
        assert "a.cell[0]" in dimmed
        assert "a.cell[2]" in dimmed

    def test_range_focus_expands(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="focus range"]\n'
            "\\shape{a}{Array}{size=4, data=[1,2,3,4]}\n"
            "\\step\n"
            "\\focus{a.range[1:2]}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        dimmed = _targets_with_defocus(html_out)
        assert "a.cell[1]" not in dimmed
        assert "a.cell[2]" not in dimmed
        assert "a.cell[0]" in dimmed
        assert "a.cell[3]" in dimmed

    def test_other_shape_untouched(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="focus two shapes"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\shape{b}{Array}{size=2, data=[3,4]}\n"
            "\\step\n"
            "\\focus{a.cell[0]}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        dimmed = _targets_with_defocus(html_out)
        # Only shape a is focused; shape b is entirely untouched.
        assert "a.cell[1]" in dimmed
        assert "b.cell[0]" not in dimmed
        assert "b.cell[1]" not in dimmed

    def test_no_focus_no_defocus(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="no focus"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            "\\recolor{a.cell[0]}{state=current}\n"
            "\\end{animation}\n"
        )
        html_out = self._render(source, tmp_path)
        assert "scriba-defocused" not in _joined_g_classes(html_out)


def _joined_g_classes(html: str) -> str:
    """All ``<g ...>`` open tags joined, so a CSS-only occurrence of the class
    name does not create a false positive."""
    return "\n".join(re.findall(r"<g [^>]*>", html))
