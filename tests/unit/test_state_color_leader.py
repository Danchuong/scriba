"""P2 of the unified decoration plan: label<->state color binding
(`color="state:X"`) and the opt-in `leader=true` connector
(investigations/feat-label-state-colors.md, unified-spec.md R-37).

The quoted form is mandatory — a bare colon dies in the value lexer
(E1012), confirmed by three independent probes."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.grid import GridPrimitive


def _parse(body: str):
    return SceneParser().parse(
        "\\shape{g}{Grid}{rows=2, cols=2, data=[[1,2],[3,4]]}\n\\step\n" + body
    )


class TestStateColorGrammar:
    def test_quoted_state_color_accepted(self) -> None:
        ir = _parse('\\annotate{g.cell[0][0]}{label="x", color="state:current"}\n')
        anns = [c for f in ir.frames for c in f.commands
                if type(c).__name__ == "AnnotateCommand"]
        assert anns[0].color == "state:current"

    def test_invalid_state_rejected_e1113(self) -> None:
        from scriba.core.errors import ValidationError

        with pytest.raises(ValidationError) as ei:
            _parse('\\annotate{g.cell[0][0]}{label="x", color="state:hidden"}\n')
        assert "E1113" in str(ei.value)

    def test_plain_colors_untouched(self) -> None:
        ir = _parse('\\annotate{g.cell[0][0]}{label="x", color=good}\n')
        anns = [c for f in ir.frames for c in f.commands
                if type(c).__name__ == "AnnotateCommand"]
        assert anns[0].color == "good"


class TestStateColorEmit:
    def test_class_is_sanitized_no_colon(self) -> None:
        g = GridPrimitive("g", {"rows": 2, "cols": 2, "data": [[1, 2], [3, 4]]})
        g.set_annotations(
            [{"target": "g.cell[0][0]", "label": "x", "color": "state:current"}]
        )
        svg = g.emit_svg()
        assert "scriba-annotation-state-current" in svg
        assert 'class="scriba-annotation scriba-annotation-state:current"' not in svg

    def test_css_tokens_and_rules_exist_both_themes(self) -> None:
        css = Path("scriba/animation/static/scriba-scene-primitives.css").read_text()
        for st in ("current", "done", "dim", "good", "error", "path"):
            assert f"--scriba-annotation-state-{st}:" in css
            assert f".scriba-annotation-state-{st} > text" in css
        # dark block overrides too
        assert css.count("--scriba-annotation-state-current:") >= 2

    def test_arrowhead_and_pill_border_covered_by_rules(self) -> None:
        css = Path("scriba/animation/static/scriba-scene-primitives.css").read_text()
        assert ".scriba-annotation-state-current > polygon" in css
        assert ".scriba-annotation-state-current > rect" in css


class TestLeader:
    def test_leader_threads_to_entry(self) -> None:
        ir = _parse('\\annotate{g.cell[0][0]}{label="x", leader=true}\n')
        anns = [c for f in ir.frames for c in f.commands
                if type(c).__name__ == "AnnotateCommand"]
        assert anns[0].leader is True

    def test_position_pill_emits_dotted_leader_and_dot(self) -> None:
        arr = ArrayPrimitive("a", {"size": 6, "data": list(range(6))})
        arr.set_annotations(
            [{"target": "a.cell[2]", "label": "chốt", "position": "above",
              "leader": True}]
        )
        svg = arr.emit_svg()
        m = re.search(r'data-annotation="a.cell\[2\]-position-above"(.*?)</g>', svg, re.S)
        assert m, "position annotation group missing"
        body = m.group(1)
        assert re.search(r'<line [^>]*stroke-dasharray="2,3"', body), "dotted leader"
        assert re.search(r'<circle [^>]*r="2"', body), "anchor dot"

    def test_no_leader_by_default(self) -> None:
        arr = ArrayPrimitive("a", {"size": 6, "data": list(range(6))})
        arr.set_annotations(
            [{"target": "a.cell[2]", "label": "chốt", "position": "above"}]
        )
        svg = arr.emit_svg()
        m = re.search(r'data-annotation="a.cell\[2\]-position-above"(.*?)</g>', svg, re.S)
        assert m and 'stroke-dasharray="2,3"' not in m.group(1)
