"""DECORATE design, verb 1 — strike-but-keep.

``\\annotate{x}{strike=true}`` draws a diagonal cross-out over the target,
orthogonal to the element's state color, inline-styled (zero new CSS),
riding the shipped ``annotation_add`` contract. Fills the teaching-gesture
census's one hard-MISSING marker verb (investigations/teaching-marker-verbs.md
GAP-1): before this, pruning a rejected candidate was a lossy binary —
``\\recolor``→error/dim (overwrites the role color) or →hidden (vanishes).
Strike-but-keep shows "considered, rejected, here is the X, still visible".
"""

from __future__ import annotations

import re
import warnings

from scriba.animation.primitives.array import ArrayPrimitive


def _array_with(ann: dict) -> str:
    a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
    a.set_annotations([{"target": "a.cell[1]", **ann}])
    return a.emit_svg()


class TestGrammar:
    def test_strike_param_parses_to_command(self) -> None:
        from scriba.animation.parser.grammar import SceneParser

        src = (
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            "\\annotate{a.cell[1]}{strike=true}\n"
        )
        ir = SceneParser().parse(src)
        cmds = [
            c
            for f in ir.frames
            for c in f.commands
            if type(c).__name__ == "AnnotateCommand"
        ]
        assert cmds and cmds[0].strike is True


class TestEmit:
    def test_strike_emits_inline_diagonal_group(self) -> None:
        svg = _array_with({"strike": True})
        assert "a.cell[1]-strike" in svg
        m = re.search(
            r'<g class="scriba-annotation[^"]*"[^>]*'
            r'data-annotation="a.cell\[1\]-strike"[^>]*>\s*<line ([^>]+)/>',
            svg,
        )
        assert m, "strike line group missing"
        line = m.group(1)
        assert "stroke=" in line
        x1 = float(re.search(r'x1="(-?[\d.]+)"', line).group(1))
        x2 = float(re.search(r'x2="(-?[\d.]+)"', line).group(1))
        y1 = float(re.search(r'y1="(-?[\d.]+)"', line).group(1))
        y2 = float(re.search(r'y2="(-?[\d.]+)"', line).group(1))
        assert x1 != x2 and y1 != y2  # a true diagonal, corner to corner

    def test_strike_adds_no_new_css_class(self) -> None:
        svg = _array_with({"strike": True, "color": "error"})
        assert "scriba-annotation-error" in svg  # reuses the shipped class
        assert "scriba-strike" not in svg
        assert "scriba-state-strike" not in svg

    def test_strike_coexists_with_state(self) -> None:
        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        a.set_state("cell[1]", "error")
        a.set_annotations([{"target": "a.cell[1]", "strike": True}])
        svg = a.emit_svg()
        assert "scriba-state-error" in svg  # keeps its role color
        assert "a.cell[1]-strike" in svg  # AND carries the strike

    def test_no_strike_no_line_group(self) -> None:
        svg = _array_with({"label": "x"})
        assert "-strike" not in svg

    def test_strike_composes_with_label(self) -> None:
        svg = _array_with({"strike": True, "label": "rejected"})
        assert "a.cell[1]-strike" in svg
        assert "rejected" in svg


class TestSoftDrop:
    def test_strike_unresolvable_soft_drops_e1119(self) -> None:
        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        a.set_annotations([{"target": "a.cell[99]", "strike": True}])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            svg = a.emit_svg()
        assert svg  # render did not blank
        assert any("E1119" in str(x.message) for x in w)
        assert "a.cell[99]-strike" not in svg
