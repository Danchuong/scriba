"""v1.1 polish batch: sentinel cursor parking, playeach on NumberLine
ticks, focus bad-part soft-skip, \\ref baked ring, playeach E1496."""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.animation.primitives.linkedlist import LinkedList  # noqa: F401


def _parse(src: str):
    return SceneParser().parse(src)


class TestSentinelCursor:
    def test_at_before_parses_and_emits(self) -> None:
        ir = _parse(
            '\\shape{a}{Array}{size=4, data=[1,2,3,4], sentinels=true}\n'
            "\\step\n"
            '\\cursor{a}{id=i, at="before"}\n'
        )
        cmds = [c for f in ir.frames for c in f.commands
                if type(c).__name__ == "CursorCommand"]
        assert cmds[0].at == "before"

    def test_caret_draws_on_sentinel(self) -> None:
        a = ArrayPrimitive("a", {"size": 4, "data": [1, 2, 3, 4], "sentinels": True})
        a.set_cursors([{"id": "i", "index": "before", "color": "info"}])
        svg = a.emit_svg()
        assert "a.cursor[i]-solo" in svg

    def test_bad_literal_still_rejected(self) -> None:
        from scriba.core.errors import ScribaError

        with pytest.raises(ScribaError):
            _parse(
                '\\shape{a}{Array}{size=4, data=[1,2,3,4]}\n'
                "\\step\n"
                '\\cursor{a}{id=i, at="sideways"}\n'
            )


class TestPlayeachNumberLine:
    def test_tick_targets_generated(self) -> None:
        ir = _parse(
            "\\shape{n}{NumberLine}{start=0, end=5}\n"
            "\\step\n"
            "\\playeach{n.range[1:3]}{state=done}\n"
        )
        recolors = [
            c for f in ir.frames for c in f.commands
            if type(c).__name__ == "RecolorCommand"
        ]
        from scriba.animation.scene import _selector_to_str

        targets = [_selector_to_str(c.target) for c in recolors]
        assert targets == ["n.tick[1]", "n.tick[2]", "n.tick[3]"]


class TestPlayeachUnknownKey:
    def test_e1496(self) -> None:
        from scriba.core.errors import ScribaError

        with pytest.raises(ScribaError) as ei:
            _parse(
                "\\shape{a}{Array}{size=4, data=[1,2,3,4]}\n"
                "\\step\n"
                '\\playeach{a.range[0:2]}{state=done, narrat="typo"}\n'
            )
        assert "E1496" in str(ei.value)


class TestFocusBadPartSoft:
    def test_bad_part_warns_and_does_not_dim_shape(self) -> None:
        import warnings as w

        from scriba.animation._frame_renderer import _apply_defocus

        class _F:
            focus = ("a.cell[99]",)

        a = ArrayPrimitive("a", {"size": 3, "data": [1, 2, 3]})
        svg = '<g data-target="a.cell[0]" class="scriba-state-idle"></g>'
        with w.catch_warnings(record=True) as rec:
            w.simplefilter("always")
            out = _apply_defocus(svg, _F(), {"a": a})
        assert "scriba-defocused" not in out  # whole shape NOT dimmed
        assert any("E1115" in str(r.message) for r in rec)


class TestRefMarkBaked:
    def test_ref_marks_class_applied(self) -> None:
        from scriba.animation._frame_renderer import _apply_ref_marks

        class _F:
            ref_marks = ["a.cell[1]"]

        svg = (
            '<g data-target="a.cell[0]" class="x"></g>'
            '<g data-target="a.cell[1]" class="x"></g>'
        )
        out = _apply_ref_marks(svg, _F())
        assert out.count("scriba-ref-mark") == 1
        assert 'data-target="a.cell[1]" class="x scriba-ref-mark"' in out

    def test_css_rule_exists(self) -> None:
        from pathlib import Path

        css = Path("scriba/animation/static/scriba-scene-primitives.css").read_text()
        assert ".scriba-ref-mark > rect" in css
