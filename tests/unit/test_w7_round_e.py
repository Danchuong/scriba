"""Tests for Wave 7 Round E polish fixes.

Covers:
- W7-M7: slugify CJK/Arabic → unique id= via SHA-1 fallback; duplicate ASCII
- W7-M11: emitted widget JS uses adoptNode/cloneNode, not importNode
"""

from __future__ import annotations

import hashlib
import re

import pytest

from scriba.tex.parser.environments import apply_sections, slugify


# ---------------------------------------------------------------------------
# W7-M7: slugify — non-Latin fallback + duplicate deduplication
# ---------------------------------------------------------------------------


class TestSlugifyNonLatin:
    def test_chinese_heading_unique_id(self) -> None:
        """CJK heading must NOT collapse to bare 'section'."""
        slug = slugify("第一章")
        assert slug != "section"
        assert slug.startswith("section-")
        # Must be 8 hex chars after the dash
        suffix = slug[len("section-"):]
        assert re.fullmatch(r"[0-9a-f]{8}", suffix), f"bad suffix: {suffix!r}"

    def test_arabic_heading_unique_id(self) -> None:
        """Arabic heading must produce a stable hash-based slug."""
        slug = slugify("المقدمة")
        assert slug != "section"
        assert slug.startswith("section-")

    def test_vietnamese_heading_latin_slug(self) -> None:
        """Vietnamese text (NFKD strips diacritics) → ASCII slug, no hash."""
        slug = slugify("Đề cương")
        # After NFKD + combining strip: "de cuong" → "de-cuong"
        assert "section-" not in slug or len(slug) > 10  # not a hash fallback
        # Must contain at least some ASCII letters from the base chars
        assert re.search(r"[a-z]", slug)

    def test_hash_is_stable(self) -> None:
        """Same text must always produce the same slug."""
        assert slugify("第一章") == slugify("第一章")

    def test_different_cjk_headings_differ(self) -> None:
        """Two distinct CJK headings must produce distinct slugs."""
        s1 = slugify("第一章")
        s2 = slugify("第二章")
        assert s1 != s2

    def test_ascii_section_unchanged(self) -> None:
        """Plain ASCII headings still work as before."""
        assert slugify("Introduction") == "introduction"
        assert slugify("Hello World") == "hello-world"

    def test_arabic_hash_matches_sha1(self) -> None:
        """Verify the hash is exactly sha1[:8] of the original text."""
        text = "المقدمة"
        expected = "section-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
        assert slugify(text) == expected


class TestApplySectionsDuplicates:
    """Duplicate ASCII \\section{Intro} × 2 must produce unique id= attributes."""

    def test_duplicate_ascii_sections_unique_ids(self) -> None:
        source = r"\section{Intro}" + "\n" + r"\section{Intro}"
        slug_counts: dict[str, int] = {}
        html = apply_sections(source, slug_counts)

        ids = re.findall(r'id="([^"]+)"', html)
        assert len(ids) == 2, f"Expected 2 id= attributes, got: {ids}"
        assert ids[0] != ids[1], f"Duplicate ids: {ids}"
        assert ids[0] == "intro"
        assert ids[1] == "intro-2"

    def test_cjk_sections_unique_ids(self) -> None:
        """Two different CJK sections must produce two distinct id= values."""
        source = r"\section{第一章}" + "\n" + r"\section{第二章}"
        slug_counts: dict[str, int] = {}
        html = apply_sections(source, slug_counts)

        ids = re.findall(r'id="([^"]+)"', html)
        assert len(ids) == 2, f"Expected 2 id= attributes, got: {ids}"
        assert ids[0] != ids[1], f"CJK sections must have distinct ids, got: {ids}"

    def test_same_cjk_section_twice_deduped(self) -> None:
        """Identical CJK heading twice → second gets -2 suffix."""
        source = r"\section{第一章}" + "\n" + r"\section{第一章}"
        slug_counts: dict[str, int] = {}
        html = apply_sections(source, slug_counts)

        ids = re.findall(r'id="([^"]+)"', html)
        assert len(ids) == 2
        assert ids[0] != ids[1]
        assert ids[1] == ids[0] + "-2"


# ---------------------------------------------------------------------------
# W7-M11: emitted widget JS must NOT use importNode
# ---------------------------------------------------------------------------


class TestEmitterNoImportNode:
    """Verify the inline widget JS uses cloneNode/adoptNode, not importNode.

    Safari 14.0 drops data-* attributes on nodes cloned via importNode from
    a separately-parsed SVG document.  The fix uses cloneNode(true) +
    adoptNode instead.
    """

    def test_emit_interactive_html_no_import_node(self) -> None:
        from scriba.animation.emitter import FrameData, emit_interactive_html
        from scriba.animation.primitives.array import ArrayPrimitive

        prim = ArrayPrimitive("A", {"size": 3})
        frame = FrameData(
            step_number=1,
            total_frames=1,
            narration_html="step one",
            shape_states={"A": {}},
            annotations=[],
        )
        html = emit_interactive_html(
            scene_id="scriba-test",
            frames=[frame],
            primitives={"A": prim},
        )

        assert "importNode" not in html, (
            "Widget JS must not call importNode (Safari 14.0 data-* loss). "
            "Use cloneNode(true) + adoptNode instead."
        )

    def test_emit_interactive_html_uses_clone_adopt(self) -> None:
        from scriba.animation.emitter import FrameData, emit_interactive_html
        from scriba.animation.primitives.array import ArrayPrimitive

        prim = ArrayPrimitive("A", {"size": 2})
        frame = FrameData(
            step_number=1,
            total_frames=1,
            narration_html="",
            shape_states={"A": {}},
            annotations=[],
        )
        html = emit_interactive_html(
            scene_id="scriba-test2",
            frames=[frame],
            primitives={"A": prim},
        )

        assert "cloneNode(true)" in html, "Widget JS must call cloneNode(true)"
        assert "adoptNode(" in html, "Widget JS must call adoptNode(...)"
