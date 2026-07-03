"""P1 of the unified decoration plan: ``bracket=true`` glyph on block
annotations — a no-fill dashed rounded outline hugging the block, with the
label pill going through the standard placement pipeline (R-35 family;
investigations/unified-{decoration-model,spec}.md)."""

from __future__ import annotations

import re

from scriba.animation.primitives.grid import GridPrimitive


def _grid_with(ann: dict) -> str:
    g = GridPrimitive(
        "g", {"rows": 3, "cols": 3, "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
    )
    g.set_annotations([{"target": "g.block[0:1][0:1]", "label": "nền", **ann}])
    return g.emit_svg()


class TestGrammar:
    def test_bracket_param_parses_to_command(self) -> None:
        from scriba.animation.parser.grammar import SceneParser

        src = (
            "\\shape{g}{Grid}{rows=2, cols=2, data=[[1,2],[3,4]]}\n"
            "\\step\n"
            '\\annotate{g.block[0:1][0:1]}{label="x", bracket=true}\n'
        )
        ir = SceneParser().parse(src)
        cmds = [
            c
            for f in ir.frames
            for c in f.commands
            if type(c).__name__ == "AnnotateCommand"
        ]
        assert cmds and cmds[0].bracket is True


class TestEmit:
    def test_bracket_outline_emitted_with_own_key(self) -> None:
        svg = _grid_with({"bracket": True})
        assert "-block-bracket" in svg
        m = re.search(
            r'<g class="scriba-annotation[^"]*"[^>]*data-annotation="g.block\[0:1\]\[0:1\]-block-bracket"[^>]*>\s*<rect ([^>]+)/>',
            svg,
        )
        assert m, "bracket outline group+rect missing"
        rect = m.group(1)
        assert 'fill="none"' in rect
        assert "stroke-dasharray" in rect
        assert 'rx="6"' in rect

    def test_bracket_outline_hugs_block_box(self) -> None:
        g = GridPrimitive(
            "g", {"rows": 3, "cols": 3, "data": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        )
        g.set_annotations(
            [{"target": "g.block[0:1][0:1]", "label": "nền", "bracket": True}]
        )
        svg = g.emit_svg()
        box = g.resolve_annotation_box("g.block[0:1][0:1]")
        m = re.search(
            r'data-annotation="g.block\[0:1\]\[0:1\]-block-bracket"[^>]*>\s*<rect x="(-?[\d.]+)" y="(-?[\d.]+)" width="([\d.]+)" height="([\d.]+)"',
            svg,
        )
        assert m
        x, y, w, h = (float(v) for v in m.groups())
        # 3px outward hug
        assert x == box.x - 3 and y == box.y - 3
        assert w == box.width + 6 and h == box.height + 6

    def test_pill_still_placed(self) -> None:
        svg = _grid_with({"bracket": True})
        assert "nền" in svg  # label pill present

    def test_no_bracket_no_outline(self) -> None:
        svg = _grid_with({})
        assert "-block-bracket" not in svg

    def test_bracket_on_non_block_target_ignored(self) -> None:
        g = GridPrimitive("g", {"rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]})
        g.set_annotations(
            [{"target": "g.cell[0][0]", "label": "x", "bracket": True}]
        )
        assert "-block-bracket" not in g.emit_svg()
