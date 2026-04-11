"""Unicode homograph / visual-spoofing regression tests.

Covers audit finding 17-M3 (fuzz/regression adequacy) for Unicode
attacks on labels, narration, shape names, and URL-like attribute
values.

Written Wave 4A Cluster 9 to cover 17-M3 residuals, then updated in
Wave 5.1 when the parser gained NFC normalization for identifiers
(see ``SceneParser.parse`` and ``SelectorParser.__init__``).

Current policy:

* **Shape names and selectors** are NFC-normalized by the parser, so
  NFC ``café`` and NFD ``café`` collide into a single identifier.
  This prevents silent mismatches where a shape declared in one form
  cannot be found by an apply/selector written in the other form.
* **Labels and narration text** are still pass-through (not
  normalized) — the sanitizer is the last line of defence and
  preserves author-visible bytes.
* Cyrillic/Latin visual look-alikes are still treated as distinct
  identifiers: NFC normalization does not collapse homograph codepoints.
"""

from __future__ import annotations

import unicodedata

import pytest

from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives.array import ArrayPrimitive
from scriba.tex.parser._urls import is_safe_url


def _parse(source: str):
    return SceneParser().parse(f"\\begin{{animation}}\n{source}\n\\end{{animation}}"
                               if "\\begin" not in source else source)


class TestCyrillicHomographs:
    """Cyrillic letters visually identical to Latin are distinct identifiers."""

    def test_latin_a_vs_cyrillic_a_are_different_shape_names(self) -> None:
        """``a`` (U+0061) and ``а`` (U+0430) must be treated as distinct."""
        src = (
            "\\shape{a}{Array}{size=3}\n"
            "\\shape{\u0430}{Array}{size=3}\n"
            "\\step\n"
        )
        ir = SceneParser().parse(src)
        names = {s.name for s in ir.shapes}
        assert "a" in names
        assert "\u0430" in names
        assert len(names) == 2

    def test_full_cyrillic_spoof_of_paypal_is_distinct(self) -> None:
        """All-Cyrillic ``раураl`` is not the ASCII ``paypal``."""
        cyr = "\u0440\u0430\u0443\u0440\u0430l"  # р а у р а l
        assert cyr != "paypal"
        # Verify it renders through a primitive label without crash.
        prim = ArrayPrimitive("a", {"size": 3, "label": cyr})
        svg = prim.emit_svg()
        # The Cyrillic text must survive into the output.
        assert cyr in svg

    def test_mixed_script_name_parses(self) -> None:
        """A shape name mixing Latin + Cyrillic must not silently collide."""
        src = (
            "\\shape{ab\u0430}{Array}{size=3}\n"  # a b а(cyr)
            "\\shape{aba}{Array}{size=3}\n"
            "\\step\n"
        )
        ir = SceneParser().parse(src)
        names = [s.name for s in ir.shapes]
        assert names == ["ab\u0430", "aba"]


class TestRightToLeftOverride:
    """Right-to-left override (U+202E) handling."""

    def test_rlo_in_narration_does_not_crash(self) -> None:
        """U+202E in narration must render without traceback."""
        rlo = "\u202e"
        src = (
            "\\shape{a}{Array}{size=3}\n"
            "\\step\n"
            f"\\narrate{{visible{rlo}reversed}}\n"
        )
        ir = SceneParser().parse(src)
        assert ir.frames[0].narrate_body is not None
        # Narration passes through unchanged (sanitizer is downstream).
        assert rlo in ir.frames[0].narrate_body

    def test_rlo_in_label_passes_through(self) -> None:
        """U+202E in a primitive label does not crash the emitter."""
        rlo = "\u202e"
        prim = ArrayPrimitive("a", {"size": 3, "label": f"hello{rlo}world"})
        svg = prim.emit_svg()
        # The RLO char is NOT an HTML-special character, so it should
        # survive into the SVG text content.
        assert rlo in svg


class TestZalgoCombiningDiacritics:
    """Stacked combining marks (Zalgo text) must not blow up."""

    def test_50_combining_marks_does_not_crash(self) -> None:
        """A character with 50 stacked combining diacritics renders."""
        base = "a"
        combining = "\u0301" * 50  # combining acute accent
        payload = base + combining
        prim = ArrayPrimitive("a", {"size": 3, "label": payload})
        svg = prim.emit_svg()
        # Output size should be proportional — not exponential.
        assert len(svg) < 100_000
        assert payload in svg

    def test_200_combining_marks_is_bounded(self) -> None:
        """Even 200 stacked marks must stay within 2x of a normal label."""
        payload = "a" + "\u0301" * 200
        normal = ArrayPrimitive("n", {"size": 3, "label": "hello"}).emit_svg()
        zalgo = ArrayPrimitive("a", {"size": 3, "label": payload}).emit_svg()
        # SVG output growth is linear in label length (the label appears
        # exactly once in the <text> element).
        assert len(zalgo) < len(normal) + 1000


class TestZeroWidthJoinerInUrls:
    """Zero-width joiner (U+200D) must be rejected by is_safe_url."""

    def test_zwj_in_url_is_rejected(self) -> None:
        # Reference: _urls.py lists U+200D as a dangerous smuggle char.
        assert is_safe_url("https://example.com/\u200dpath") is False

    def test_zero_width_space_in_url_is_rejected(self) -> None:
        assert is_safe_url("https://example.com/\u200bpath") is False

    def test_zero_width_non_joiner_in_url_is_rejected(self) -> None:
        assert is_safe_url("https://example.com/\u200cpath") is False

    def test_line_separator_in_url_is_rejected(self) -> None:
        assert is_safe_url("https://example.com/\u2028path") is False

    def test_clean_url_is_accepted(self) -> None:
        assert is_safe_url("https://example.com/path") is True


class TestMathematicalAlphanumerics:
    """Mathematical alphanumeric symbols (U+1D400+) are visually similar
    to ASCII but are distinct codepoints. They must not be normalized
    away."""

    def test_mathematical_bold_a_is_distinct_from_ascii_a(self) -> None:
        math_a = "\U0001d400"  # 𝐀 MATHEMATICAL BOLD CAPITAL A
        assert math_a != "A"
        prim = ArrayPrimitive("a", {"size": 3, "label": math_a})
        svg = prim.emit_svg()
        assert math_a in svg

    def test_mathematical_italic_word_parses_as_label(self) -> None:
        italic = "\U0001d44e\U0001d45b\U0001d45c"  # 𝑎𝑛𝑜
        prim = ArrayPrimitive("a", {"size": 3, "label": italic})
        svg = prim.emit_svg()
        assert italic in svg
        # NFKC normalization would fold these to "ano" — verify we do NOT.
        assert "ano" not in svg.replace(italic, "")


class TestNfcNfdConsistency:
    """NFC vs NFD normalization of identical-looking labels."""

    def test_nfc_and_nfd_are_different_without_normalization(self) -> None:
        """``é`` NFC (U+00E9) is one codepoint, NFD (U+0065 U+0301) is two.
        Scriba does not normalize, so they are distinct identifiers."""
        nfc = unicodedata.normalize("NFC", "é")
        nfd = unicodedata.normalize("NFD", "é")
        assert nfc != nfd
        assert len(nfc) == 1
        assert len(nfd) == 2

    def test_nfc_and_nfd_labels_both_render(self) -> None:
        nfc = unicodedata.normalize("NFC", "café")
        nfd = unicodedata.normalize("NFD", "café")
        svg_nfc = ArrayPrimitive("a", {"size": 3, "label": nfc}).emit_svg()
        svg_nfd = ArrayPrimitive("a", {"size": 3, "label": nfd}).emit_svg()
        assert nfc in svg_nfc
        assert nfd in svg_nfd

    def test_nfc_and_nfd_shape_names_collapse_to_single_nfc_identifier(
        self,
    ) -> None:
        """Wave 5.1: the parser normalizes identifiers to NFC so NFC
        ``café`` and NFD ``café`` collide into a single shape name.
        This prevents silent mismatches where a shape declared in one
        form cannot be found by a selector written in the other form.
        """
        nfc = unicodedata.normalize("NFC", "café")
        nfd = unicodedata.normalize("NFD", "café")
        assert nfc != nfd  # sanity: the source bytes really are different
        src = (
            f"\\shape{{{nfc}}}{{Array}}{{size=3}}\n"
            f"\\shape{{{nfd}}}{{Array}}{{size=3}}\n"
            "\\step\n"
        )
        # Both declarations canonicalize to the same NFC identifier.
        # The parser raises E1007 on duplicate shape names; catching
        # that here would confirm the normalization is wired end to
        # end.  We accept either the duplicate-shape error or a
        # successful parse that collapses the two into one name.
        try:
            ir = SceneParser().parse(src)
        except Exception as exc:  # noqa: BLE001 — explicit contract check
            assert "E1007" in str(exc) or "duplicate" in str(exc).lower()
            return
        # If parse succeeded, both entries share a single NFC name.
        assert ir.shapes[0].name == nfc
        if len(ir.shapes) == 2:
            assert ir.shapes[0].name == ir.shapes[1].name == nfc
