"""Tests for ``.scriba-narration`` overflow protection parity (H6-class fix).

A long single inline formula in ``\\narrate`` renders through the same
``render_inline_tex`` pathway as ``\\invariant``. The visible ``katex-html``
branch KaTeX emits carries ZERO breakable whitespace in its text nodes (every
glyph is individually spanned) — confirmed by rendering a real repro and
inspecting the emitted HTML (see
_bmad-output/implementation-artifacts/spec-fix-shell-panel-single-source.md).
``overflow-wrap: normal`` (the CSS default) has no valid break point in that
output, so a long formula overflows its panel horizontally. ``.scriba-
invariant`` already carries ``overflow-wrap: anywhere`` for exactly this
reason; ``.scriba-narration`` — same rendering pathway, same risk — never
got the same protection until now.
"""

from __future__ import annotations

from pathlib import Path

_CSS_PATH = (
    Path(__file__).resolve().parents[2]
    / "scriba"
    / "animation"
    / "static"
    / "scriba-embed.css"
)


def _css_text() -> str:
    return _CSS_PATH.read_text(encoding="utf-8")


def _narration_block() -> str:
    css = _css_text()
    return css.split("\n.scriba-narration {", 1)[1].split("}", 1)[0]


class TestNarrationOverflowProtection:
    def test_narration_rule_exists(self) -> None:
        assert ".scriba-narration {" in _css_text()

    def test_narration_gets_overflow_wrap_anywhere(self) -> None:
        block = _narration_block()
        assert "overflow-wrap: anywhere" in block
