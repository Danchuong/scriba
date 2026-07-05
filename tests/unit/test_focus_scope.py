"""DECORATE design, verb 3 — ``\\focus{target}{scope=board}`` board spotlight.

Today ``\\focus`` dims only the *complement inside one shape*; other shapes are
untouched (§5.16). The optional ``scope=board`` param extends the shipped
``.scriba-defocused`` overlay to also dim every OTHER shape on the board, so a
teacher can spotlight one structure against a dark stage. ``scope=shape``
(the default) is byte-identical to today's behaviour — pinned below. Zero new
CSS (reuses ``.scriba-defocused``), zero new motion kind (defocus is a baked
overlay, not a kind).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.core.errors import ValidationError

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402


def _focus_cmds(src: str) -> list:
    ir = SceneParser().parse(src)
    return [
        c
        for f in ir.frames
        for c in f.commands
        if type(c).__name__ == "FocusCommand"
    ]


def _render(source: str, tmp_path: Path) -> str:
    tmp_path.mkdir(parents=True, exist_ok=True)
    tex_path = tmp_path / "in.tex"
    tex_path.write_text(source, encoding="utf-8")
    out_path = tmp_path / "out.html"
    render_file(tex_path, out_path)
    return out_path.read_text(encoding="utf-8")


def _targets_with_defocus(html: str) -> set[str]:
    result: set[str] = set()
    for m in re.finditer(r'<g data-target="([^"]+)" class="([^"]*)"', html):
        if "scriba-defocused" in m.group(2):
            result.add(m.group(1))
    return result


class TestGrammar:
    def test_scope_board_parses(self) -> None:
        cmds = _focus_cmds(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            "\\focus{a.cell[0]}{scope=board}\n"
        )
        assert cmds and cmds[0].scope == "board"

    def test_default_scope_is_shape(self) -> None:
        cmds = _focus_cmds(
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\step\n"
            "\\focus{a.cell[0]}\n"
        )
        assert cmds and cmds[0].scope == "shape"

    def test_bad_scope_raises_e1122(self) -> None:
        with pytest.raises(ValidationError) as exc:
            _focus_cmds(
                "\\shape{a}{Array}{size=2, data=[1,2]}\n"
                "\\step\n"
                "\\focus{a.cell[0]}{scope=galaxy}\n"
            )
        assert exc.value.code == "E1122"


class TestBoardScope:
    def test_board_dims_other_shape(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="board focus"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\shape{b}{Array}{size=2, data=[3,4]}\n"
            "\\step\n"
            "\\focus{a.cell[0]}{scope=board}\n"
            "\\end{animation}\n"
        )
        dimmed = _targets_with_defocus(_render(source, tmp_path))
        # The focused cell stays lit; its intra-shape complement dims AND
        # the entire other shape b dims (this is the board spotlight).
        assert "a.cell[0]" not in dimmed
        assert "a.cell[1]" in dimmed
        assert "b.cell[0]" in dimmed
        assert "b.cell[1]" in dimmed

    def test_default_scope_leaves_other_shape_lit(self, tmp_path: Path) -> None:
        source = (
            '\\begin{animation}[id="d", label="shape focus"]\n'
            "\\shape{a}{Array}{size=2, data=[1,2]}\n"
            "\\shape{b}{Array}{size=2, data=[3,4]}\n"
            "\\step\n"
            "\\focus{a.cell[0]}\n"
            "\\end{animation}\n"
        )
        dimmed = _targets_with_defocus(_render(source, tmp_path))
        # Default scope=shape: only shape a's complement dims; b untouched.
        assert "a.cell[1]" in dimmed
        assert "b.cell[0]" not in dimmed
        assert "b.cell[1]" not in dimmed


class TestByteStability:
    def test_explicit_shape_scope_equals_implicit(self, tmp_path: Path) -> None:
        # The explicit default (scope=shape) must render byte-identically to
        # the un-scoped form: scope=shape is a no-op relative to today.
        implicit = (
            '\\begin{animation}[id="d", label="focus"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\shape{b}{Array}{size=2, data=[3,4]}\n"
            "\\step\n"
            "\\focus{a.cell[1]}\n"
            "\\end{animation}\n"
        )
        explicit = implicit.replace(
            "\\focus{a.cell[1]}", "\\focus{a.cell[1]}{scope=shape}"
        )
        html_implicit = _render(implicit, tmp_path / "imp")
        html_explicit = _render(explicit, tmp_path / "exp")
        assert html_implicit == html_explicit
