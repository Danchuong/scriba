"""Regression tests for Unicode NFC normalization in parser identifiers.

Covers Wave 5.1 Fix 3: the parser must NFC-normalize identifier
comparisons so that NFD-encoded ``café`` (cafe + U+0301 combining
acute) matches NFC-encoded ``café`` (U+00E9 precomposed e-acute).

Without normalization, an author whose editor emits NFD could declare
``\\shape{café}{Array}{size=3}`` one way and select it as
``\\apply{café.cell[0]}`` another, and the two identifier bytes would
differ so shape lookup would fail silently.
"""

from __future__ import annotations

import unicodedata

import pytest

from scriba.animation.parser.grammar import (
    ApplyCommand,
    SceneParser,
    ShapeCommand,
)
from scriba.animation.parser.selectors import parse_selector

# NFC and NFD forms of ``café``.
NFC_CAFE = "café"  # e-acute precomposed (U+00E9)
NFD_CAFE = unicodedata.normalize("NFD", NFC_CAFE)  # e + U+0301


@pytest.fixture()
def parser() -> SceneParser:
    return SceneParser()


@pytest.mark.unit
class TestNfcIdentifier:
    def test_nfc_and_nfd_differ_byte_wise(self) -> None:
        """Sanity check: NFC and NFD forms of 'café' are not byte-equal."""
        assert NFC_CAFE != NFD_CAFE
        assert unicodedata.normalize("NFC", NFD_CAFE) == NFC_CAFE

    def test_selector_parser_normalizes_nfd_text(self) -> None:
        """Raw selector parser should produce the same AST for either form."""
        nfc = parse_selector(f"{NFC_CAFE}.cell[0]")
        nfd = parse_selector(f"{NFD_CAFE}.cell[0]")
        assert nfc == nfd
        assert nfc.shape_name == NFC_CAFE  # stored as NFC

    def test_scene_parser_source_normalized(self, parser: SceneParser) -> None:
        """\\shape and \\apply using different forms still bind to one key."""
        src = (
            f"\\shape{{{NFC_CAFE}}}{{Array}}{{size=3}}\n"
            "\\step\n"
            f"\\apply{{{NFD_CAFE}.cell[0]}}{{value=1}}\n"
        )
        ir = parser.parse(src)
        shapes = ir.shapes
        assert len(shapes) == 1
        assert isinstance(shapes[0], ShapeCommand)
        assert shapes[0].name == NFC_CAFE

        apply_cmds = [
            c
            for f in ir.frames
            for c in f.commands
            if isinstance(c, ApplyCommand)
        ]
        assert len(apply_cmds) == 1
        # Both the shape declaration and the selector should agree on NFC
        assert apply_cmds[0].target.shape_name == NFC_CAFE

    def test_nfd_shape_declaration_normalized_to_nfc(
        self, parser: SceneParser
    ) -> None:
        """An NFD-declared shape should be stored as its NFC form."""
        src = f"\\shape{{{NFD_CAFE}}}{{Array}}{{size=2}}\n"
        ir = parser.parse(src)
        assert ir.shapes[0].name == NFC_CAFE

    def test_ascii_unchanged(self, parser: SceneParser) -> None:
        """Pure ASCII identifiers must be unaffected by normalization."""
        src = "\\shape{arr}{Array}{size=3}\n\\step\n\\apply{arr.cell[0]}{value=9}\n"
        ir = parser.parse(src)
        assert ir.shapes[0].name == "arr"
        apply_cmds = [
            c
            for f in ir.frames
            for c in f.commands
            if isinstance(c, ApplyCommand)
        ]
        assert apply_cmds[0].target.shape_name == "arr"
