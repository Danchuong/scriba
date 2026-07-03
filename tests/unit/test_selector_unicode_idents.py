"""Selector identifiers accept combining marks (Thai/Devanagari/… names).

``_expect_ident`` hand-rolled ``isalpha()/isalnum()`` — combining marks
(category Mn/Mc) fail ``isalnum()``, so ``v.var[ค่า]`` died with E1010 at
the first tone mark. Vietnamese never tripped it (precomposed), which is
how the gap survived the 0.21.1 Unicode-identifier pass that already
standardised VariableWatch's ``_VAR_RE`` on ``[^\\W\\d]\\w*`` (Python
``\\w`` includes Mn). The selector parser now uses the same charset.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.selectors import parse_selector


@pytest.mark.parametrize("sel,name", [
    ("v.var[ค่า]", "ค่า"),                # Thai: combining tone mark U+0E48
    ("v.var[खोज]", "खोज"),                # Devanagari: matra U+094B
    ("v.var[đáp_án]", "đáp_án"),          # Vietnamese precomposed (regression)
    ("v.var[значение]", "значение"),      # Cyrillic
    ("v.var[x_1]", "x_1"),                # ASCII (regression)
])
def test_unicode_var_names_parse(sel: str, name: str) -> None:
    result = parse_selector(sel)
    assert name in repr(result)


def test_digit_leading_ident_still_rejected() -> None:
    with pytest.raises(Exception):
        parse_selector("v.var[1abc]")


class TestEndToEndCombiningMarkNames:
    """The same Mn/Mc gap lived in every ident charset copy: the lexer,
    VariableWatch's _VAR_RE, the \\foreach interpolation scan and the
    \\step label id all used [^\\W\\d]\\w* — and Python's \\w does NOT
    include combining marks. One shared XID-style matcher now backs all
    of them."""

    def test_variablewatch_thai_name_updates(self) -> None:
        from scriba.animation.primitives.variablewatch import VariableWatch

        w = VariableWatch("v", {"names": ["ค่า", "खोज"]})
        w.set_value("var[ค่า]", "42")
        w.set_value("var[खोज]", "7")
        svg = w.emit_svg()
        assert "42" in svg and "7" in svg

    def test_step_label_thai_becomes_frame_id(self) -> None:
        from scriba.animation.emitter import _LABEL_ID_RE

        assert _LABEL_ID_RE.match("ค่าเริ่มต้น")
        assert _LABEL_ID_RE.match("đáp-án.1")
        assert not _LABEL_ID_RE.match("1abc")
