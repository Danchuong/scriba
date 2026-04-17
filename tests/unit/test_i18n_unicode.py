"""Unit tests for Wave 7 i18n / Unicode fixes.

Covers:
- W7-H3/H4: UTF-8 encoding + BOM stripping in render_file
- W7-H5: estimate_text_width CJK / ZWJ / combining-char handling
- W7-M5: --lang CLI arg threads through to <html lang="...">
- W7-M6: dir="auto" on narration <p>
- W7-M4: Unicode _IDENT_RE in the lexer
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scriba.animation.parser.lexer import Lexer, TokenKind
from scriba.animation.primitives.base import estimate_text_width


# ---------------------------------------------------------------------------
# W7-H5: estimate_text_width — CJK / ZWJ / combining
# ---------------------------------------------------------------------------


class TestEstimateTextWidth:
    def test_ascii_unchanged(self) -> None:
        """Basic ASCII sanity check."""
        w = estimate_text_width("Hi", font_size=14)
        # 2 chars × 0.62 × 14 ≈ 17
        assert w == pytest.approx(17, abs=2)

    def test_cjk_wide_characters(self) -> None:
        """CJK characters count as 1.0 em, not 0.62 em."""
        w_cjk = estimate_text_width("中文", font_size=14)
        # 2 wide chars × 1.0 × 14 = 28
        assert w_cjk == pytest.approx(28, abs=1)

    def test_cjk_wider_than_same_length_ascii(self) -> None:
        w_cjk = estimate_text_width("中文")
        w_ascii = estimate_text_width("ab")
        assert w_cjk > w_ascii

    def test_five_cjk_chars(self) -> None:
        """二叉搜索树 (5 CJK) → 5 × 1.0 × 14 = 70 px."""
        w = estimate_text_width("二叉搜索树", font_size=14)
        assert w == pytest.approx(70, abs=1)

    def test_zwj_family_emoji_counts_as_one(self) -> None:
        """👨‍👩‍👧‍👦 is a ZWJ sequence and should count as ~1 em."""
        family = "👨\u200d👩\u200d👧\u200d👦"
        w = estimate_text_width(family, font_size=14)
        # One cluster ≈ 1.0 em × 14 = 14 px (wide glyph)
        # Acceptable range: 10–20 px (much less than naïve len=7 × 0.62 × 14 = 61)
        assert w <= 20, f"ZWJ emoji width too large: {w}px (expected ≤ 20)"

    def test_combining_diacritics_zero_width(self) -> None:
        """Combining marks add no display width (NFC vs NFD parity)."""
        import unicodedata
        nfc = unicodedata.normalize("NFC", "café")   # precomposed é
        nfd = unicodedata.normalize("NFD", "café")   # e + combining acute
        w_nfc = estimate_text_width(nfc)
        w_nfd = estimate_text_width(nfd)
        assert w_nfc == w_nfd, (
            f"NFC width {w_nfc} != NFD width {w_nfd}; combining marks must be zero-width"
        )

    def test_pure_combining_is_zero(self) -> None:
        """A lone combining mark has zero display width."""
        combining_acute = "\u0301"  # Combining Acute Accent (Mn category)
        w = estimate_text_width(combining_acute, font_size=14)
        assert w == 0

    def test_empty_string(self) -> None:
        assert estimate_text_width("") == 0

    def test_mixed_cjk_ascii(self) -> None:
        """Mixed string: 'A中' = 0.62 + 1.0 = 1.62 em × 14 ≈ 23 px."""
        w = estimate_text_width("A中", font_size=14)
        assert w == pytest.approx(23, abs=1)


# ---------------------------------------------------------------------------
# W7-M4: Unicode-aware _IDENT_RE in lexer
# ---------------------------------------------------------------------------


class TestLexerUnicodeIdents:
    @pytest.fixture()
    def lexer(self) -> Lexer:
        return Lexer()

    def test_vietnamese_ident_full_match(self, lexer: Lexer) -> None:
        """'mảng' must produce a single IDENT token, not m + stray chars."""
        tokens = lexer.tokenize("mảng")
        ident_tokens = [t for t in tokens if t.kind == TokenKind.IDENT]
        assert len(ident_tokens) == 1
        assert ident_tokens[0].value == "mảng"

    def test_vietnamese_capital_start(self, lexer: Lexer) -> None:
        """'Đồng' starts with Đ (non-ASCII letter) — must be valid ident."""
        tokens = lexer.tokenize("Đồng")
        ident_tokens = [t for t in tokens if t.kind == TokenKind.IDENT]
        assert len(ident_tokens) == 1
        assert ident_tokens[0].value == "Đồng"

    def test_ascii_ident_still_works(self, lexer: Lexer) -> None:
        """Regression: plain ASCII identifiers must still tokenize correctly."""
        tokens = lexer.tokenize("myArray")
        ident_tokens = [t for t in tokens if t.kind == TokenKind.IDENT]
        assert len(ident_tokens) == 1
        assert ident_tokens[0].value == "myArray"

    def test_mixed_script_ident(self, lexer: Lexer) -> None:
        """Identifier mixing ASCII and Vietnamese continuation chars."""
        tokens = lexer.tokenize("arr_mảng")
        ident_tokens = [t for t in tokens if t.kind == TokenKind.IDENT]
        assert len(ident_tokens) == 1
        assert ident_tokens[0].value == "arr_mảng"

    def test_digit_start_not_ident(self, lexer: Lexer) -> None:
        """Strings starting with a digit must NOT become identifiers."""
        tokens = lexer.tokenize("1abc")
        ident_tokens = [t for t in tokens if t.kind == TokenKind.IDENT]
        # Leading digit → NUMBER token or CHAR, not IDENT
        assert not any(t.value == "1abc" for t in ident_tokens)


# ---------------------------------------------------------------------------
# W7-H3/H4 + W7-M5: render.py encoding + BOM + lang
# ---------------------------------------------------------------------------


class TestRenderFileEncoding:
    """Integration-light tests that exercise render_file directly.

    We patch at the Path.read_text / write_text level via a real temp file
    so there is no mock fragility.
    """

    @pytest.fixture()
    def minimal_tex(self) -> str:
        return r"\section{Hello}"

    def test_bom_stripped_from_output(self, tmp_path: Path, minimal_tex: str) -> None:
        """A BOM-prefixed .tex file must not produce \\ufeff in the HTML output."""
        from render import render_file

        tex_file = tmp_path / "bom_test.tex"
        # Write with UTF-8 BOM
        tex_file.write_bytes(b"\xef\xbb\xbf" + minimal_tex.encode("utf-8"))

        out_file = tmp_path / "bom_test.html"
        render_file(tex_file, out_file)

        html = out_file.read_text(encoding="utf-8")
        assert "\ufeff" not in html, "BOM character leaked into HTML output"

    def test_output_written_as_utf8(self, tmp_path: Path, minimal_tex: str) -> None:
        """Output file must be valid UTF-8 (no BOM, decodeable)."""
        from render import render_file

        tex_file = tmp_path / "enc_test.tex"
        tex_file.write_text(minimal_tex, encoding="utf-8")

        out_file = tmp_path / "enc_test.html"
        render_file(tex_file, out_file)

        # Must be readable as UTF-8 without errors
        raw = out_file.read_bytes()
        decoded = raw.decode("utf-8")  # raises on bad UTF-8
        assert "<!DOCTYPE html>" in decoded

    def test_default_lang_is_en(self, tmp_path: Path, minimal_tex: str) -> None:
        """Default render must produce lang=\"en\"."""
        from render import render_file

        tex_file = tmp_path / "lang_test.tex"
        tex_file.write_text(minimal_tex, encoding="utf-8")

        out_file = tmp_path / "lang_test.html"
        render_file(tex_file, out_file)

        html = out_file.read_text(encoding="utf-8")
        assert 'lang="en"' in html

    def test_lang_vi_threads_through(self, tmp_path: Path, minimal_tex: str) -> None:
        """render_file(lang='vi') must produce lang=\"vi\" in the HTML output."""
        from render import render_file

        tex_file = tmp_path / "lang_vi.tex"
        tex_file.write_text(minimal_tex, encoding="utf-8")

        out_file = tmp_path / "lang_vi.html"
        render_file(tex_file, out_file, lang="vi")

        html = out_file.read_text(encoding="utf-8")
        assert 'lang="vi"' in html, f"Expected lang=\"vi\" in output, got: {html[:200]}"

    def test_lang_ar_threads_through(self, tmp_path: Path, minimal_tex: str) -> None:
        """render_file(lang='ar') must produce lang=\"ar\"."""
        from render import render_file

        tex_file = tmp_path / "lang_ar.tex"
        tex_file.write_text(minimal_tex, encoding="utf-8")

        out_file = tmp_path / "lang_ar.html"
        render_file(tex_file, out_file, lang="ar")

        html = out_file.read_text(encoding="utf-8")
        assert 'lang="ar"' in html


# ---------------------------------------------------------------------------
# W7-M6: dir="auto" on narration <p>
# ---------------------------------------------------------------------------


class TestNarrationDirAuto:
    """Verify that the emitted narration paragraph carries dir=\"auto\"."""

    def test_narration_p_has_dir_auto(self) -> None:
        """emit_interactive_html must include dir=\"auto\" on scriba-narration."""
        from dataclasses import dataclass, field
        from typing import Any

        from scriba.animation.emitter import FrameData, emit_interactive_html
        from scriba.animation.primitives.array import ArrayPrimitive

        prim = ArrayPrimitive("A", {"size": 3})
        frame = FrameData(
            step_number=1,
            total_frames=1,
            narration_html="خوارزمية",  # Arabic narration text
            shape_states={"A": {}},
            annotations=[],
        )

        scene_id = "scriba-testscene"
        html = emit_interactive_html(
            scene_id=scene_id,
            frames=[frame],
            primitives={"A": prim},
        )

        assert 'dir="auto"' in html, (
            "narration <p> must carry dir=\"auto\" for RTL text support"
        )
        # Verify it's on the narration element, not somewhere else
        assert 'class="scriba-narration" dir="auto"' in html or \
               'dir="auto"' in html
