"""Unit tests for tests/helpers/svg_normalize.py.

Covers: float precision, attribute ordering independence (idempotency),
whitespace normalization, timestamp stripping, nested element handling,
KaTeX class stripping, ID canonicalization, defs sorting, empty element
collapsing, debug comment preservation, and sha256_of helper.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

# Ensure tests/helpers is importable regardless of working directory.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.helpers.svg_normalize import (
    _canonicalize_floats,
    _canonicalize_ids,
    _normalize_empty_elements,
    _normalize_whitespace,
    _sort_defs_children,
    _strip_generation_comments,
    _strip_katex_version_tokens,
    normalize,
    sha256_of,
)


# ---------------------------------------------------------------------------
# Case 1: Float precision canonicalization
# ---------------------------------------------------------------------------


class TestCanonicalizeFloats:
    def test_rounds_to_two_decimal_places(self) -> None:
        svg = '<rect x="10.123456" y="20.99999"/>'
        result = _canonicalize_floats(svg)
        assert 'x="10.12"' in result
        assert 'y="21.00"' in result

    def test_leaves_short_floats_unchanged(self) -> None:
        svg = '<rect x="10.5" y="20.1"/>'
        result = _canonicalize_floats(svg)
        # Two or fewer decimal places → no change
        assert result == svg

    def test_handles_negative_float(self) -> None:
        svg = '<path d="M-10.9876,5.12345"/>'
        result = _canonicalize_floats(svg)
        assert "-10.99" in result
        assert "5.12" in result

    def test_avoids_negative_zero(self) -> None:
        svg = '<rect x="-0.001"/>'
        result = _canonicalize_floats(svg)
        # -0.001 rounds to 0.0, not -0.0
        assert 'x="0.0"' in result

    def test_preserves_nan_inf_in_known_bad_fixtures(self) -> None:
        svg = '<polygon points="nan,80.0 inf,60.0"/>'
        result = _canonicalize_floats(svg)
        # NaN/Inf are not changed by float-rounding step
        assert "nan" in result
        assert "inf" in result


# ---------------------------------------------------------------------------
# Case 2: Attribute order independence (idempotency check)
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_normalize_idempotent_simple(self) -> None:
        svg = '<svg viewBox="0 0 200 100"><rect x="10.12345" y="50"/></svg>'
        once = normalize(svg)
        twice = normalize(once)
        assert once == twice

    def test_normalize_idempotent_with_ids(self) -> None:
        svg = (
            '<svg><defs><marker id="arr-head"></marker></defs>'
            '<line href="#arr-head"/></svg>'
        )
        once = normalize(svg)
        twice = normalize(once)
        assert once == twice

    def test_normalize_idempotent_with_defs(self) -> None:
        svg = (
            '<svg><defs>'
            '<marker id="z-mark"></marker>'
            '<marker id="a-mark"></marker>'
            '</defs></svg>'
        )
        once = normalize(svg)
        twice = normalize(once)
        assert once == twice


# ---------------------------------------------------------------------------
# Case 3: Whitespace normalization
# ---------------------------------------------------------------------------


class TestNormalizeWhitespace:
    def test_strips_trailing_whitespace(self) -> None:
        svg = "<svg>  \n  <rect/>  \n</svg>  "
        result = _normalize_whitespace(svg)
        for line in result.splitlines():
            assert line == line.rstrip(), f"Trailing whitespace in: {repr(line)}"

    def test_removes_blank_lines(self) -> None:
        svg = "<svg>\n\n  <rect/>\n\n</svg>"
        result = _normalize_whitespace(svg)
        assert "\n\n" not in result

    def test_ends_with_single_newline(self) -> None:
        svg = "<svg><rect/></svg>"
        result = _normalize_whitespace(svg)
        assert result.endswith("\n")
        assert not result.endswith("\n\n")


# ---------------------------------------------------------------------------
# Case 4: Timestamp / generation comment stripping
# ---------------------------------------------------------------------------


class TestStripGenerationComments:
    def test_strips_generated_at_comment(self) -> None:
        svg = '<!-- generated at 2026-04-21T10:30:00Z --><svg/>'
        result = _strip_generation_comments(svg)
        assert "generated at" not in result

    def test_strips_scriba_version_comment(self) -> None:
        svg = '<!-- scriba version 0.10.0 --><svg/>'
        result = _strip_generation_comments(svg)
        assert "scriba version" not in result

    def test_strips_katex_version_comment(self) -> None:
        svg = '<!-- KaTeX version 0.16.9 --><svg/>'
        result = _strip_generation_comments(svg)
        assert "KaTeX version" not in result

    def test_preserves_label_collision_debug_comment(self) -> None:
        svg = '<!-- scriba:label-collision id=arr.cell[0] --><svg/>'
        result = _strip_generation_comments(svg)
        assert "scriba:label-collision" in result

    def test_case_insensitive(self) -> None:
        svg = '<!-- GENERATED AT 2026-04-21 --><svg/>'
        result = _strip_generation_comments(svg)
        assert "GENERATED AT" not in result


# ---------------------------------------------------------------------------
# Case 5: KaTeX version token stripping
# ---------------------------------------------------------------------------


class TestStripKatexVersionTokens:
    def test_strips_version_token(self) -> None:
        svg = '<text class="katex katex-version-0.16.9 foo">x</text>'
        result = _strip_katex_version_tokens(svg)
        assert "katex-version-0.16.9" not in result
        assert "katex" in result  # the base token should remain
        assert "foo" in result

    def test_strips_numeric_version_token(self) -> None:
        svg = '<text class="katex-0.16.9 bar">x</text>'
        result = _strip_katex_version_tokens(svg)
        assert "katex-0.16.9" not in result

    def test_leaves_unversioned_katex_class_intact(self) -> None:
        svg = '<text class="katex katex-html">x</text>'
        result = _strip_katex_version_tokens(svg)
        assert 'class="katex katex-html"' in result


# ---------------------------------------------------------------------------
# Case 6: Nested element handling (defs sorting + empty element collapse)
# ---------------------------------------------------------------------------


class TestNestedElements:
    def test_sorts_defs_children_by_id(self) -> None:
        svg = (
            "<svg><defs>\n"
            '  <marker id="z-end"></marker>\n'
            '  <marker id="a-start"></marker>\n'
            "</defs></svg>"
        )
        result = _sort_defs_children(svg)
        idx_a = result.index('id="a-start"')
        idx_z = result.index('id="z-end"')
        assert idx_a < idx_z, "a-start should sort before z-end"

    def test_collapses_empty_elements(self) -> None:
        svg = "<svg><rect></rect><g></g></svg>"
        result = _normalize_empty_elements(svg)
        assert "<rect/>" in result
        assert "<g/>" in result

    def test_empty_element_with_attributes(self) -> None:
        svg = '<svg><rect x="0" y="0"></rect></svg>'
        result = _normalize_empty_elements(svg)
        assert '<rect x="0" y="0"/>' in result


# ---------------------------------------------------------------------------
# Case 7: ID canonicalization
# ---------------------------------------------------------------------------


class TestCanonicalizeIds:
    def test_replaces_id_with_sequential_name(self) -> None:
        svg = '<svg><marker id="arr-f3a9"/></svg>'
        result = _canonicalize_ids(svg)
        assert 'id="id-0001"' in result
        assert "arr-f3a9" not in result

    def test_updates_href_references(self) -> None:
        svg = '<svg><marker id="head"/><line href="#head"/></svg>'
        result = _canonicalize_ids(svg)
        assert 'href="#id-0001"' in result

    def test_updates_url_references(self) -> None:
        svg = '<svg><marker id="head"/><line marker-end="url(#head)"/></svg>'
        result = _canonicalize_ids(svg)
        assert "url(#id-0001)" in result

    def test_multiple_ids_sequential(self) -> None:
        svg = '<svg><marker id="x"/><marker id="y"/></svg>'
        result = _canonicalize_ids(svg)
        assert 'id="id-0001"' in result
        assert 'id="id-0002"' in result


# ---------------------------------------------------------------------------
# Case 8: sha256_of helper
# ---------------------------------------------------------------------------


class TestSha256Of:
    def test_returns_64_char_hex(self) -> None:
        result = sha256_of("<svg/>")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self) -> None:
        svg = '<svg><rect x="10" y="20"/></svg>'
        assert sha256_of(svg) == sha256_of(svg)

    def test_different_raw_same_normalized_same_hash(self) -> None:
        """Two SVGs that differ only in float precision normalize to same SHA256."""
        svg_a = '<svg><rect x="10.123456" y="20.99999"/></svg>'
        svg_b = '<svg><rect x="10.12" y="21.00"/></svg>'
        assert sha256_of(svg_a) == sha256_of(svg_b)

    def test_matches_manual_computation(self) -> None:
        svg = '<svg/>'
        normalized = normalize(svg)
        expected = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        assert sha256_of(svg) == expected
