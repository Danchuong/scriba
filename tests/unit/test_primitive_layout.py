"""Tests for the vstack vertical layout helper.

The helper replaces hardcoded Y-offset magic numbers in Array and
DPTable emit_svg. Invariant: for any combination of font sizes and
baselines, consecutive glyph boxes never overlap.

Test matrix:

    TestTextBox          — dataclass field defaults and immutability
    TestGlyphHeight      — LINE_BOX_RATIO scaling + fo_height override
    TestVStack           — empty, single, multi-item, baseline mixing
    TestStackBottom      — tight bounding bottom for empty and populated
    TestInvariant        — property: no overlapping glyph boxes ever
    TestPixelReproduce   — vstack reproduces the exact coordinates the
                           old hardcoded math produced for h12_kruskal_mst
"""

from __future__ import annotations

from itertools import product

import pytest

from scriba.animation.primitives.layout import (
    ASCENDER_RATIO,
    DESCENDER_RATIO,
    LINE_BOX_RATIO,
    TextBox,
    glyph_height,
    stack_bottom,
    vstack,
)


class TestModuleConstants:
    def test_ratios_are_positive(self) -> None:
        assert 0 < ASCENDER_RATIO < 1
        assert 0 < DESCENDER_RATIO < 1

    def test_line_box_ratio_is_sum(self) -> None:
        assert LINE_BOX_RATIO == pytest.approx(
            ASCENDER_RATIO + DESCENDER_RATIO
        )

    def test_line_box_within_typographic_bounds(self) -> None:
        """Sans-serif line box is typically 0.9-1.2 em. 1.0 is the
        conservative safe default Scriba ships with."""
        assert 0.9 <= LINE_BOX_RATIO <= 1.2


class TestTextBox:
    def test_minimal_construction(self) -> None:
        box = TextBox(font_size=10, role="label")
        assert box.font_size == 10
        assert box.role == "label"
        assert box.height is None
        assert box.baseline == "hanging"

    def test_full_construction(self) -> None:
        box = TextBox(
            font_size=14,
            role="caption",
            height=20,
            baseline="central",
        )
        assert box.height == 20
        assert box.baseline == "central"

    def test_is_frozen(self) -> None:
        box = TextBox(font_size=10, role="label")
        with pytest.raises((AttributeError, Exception)):
            box.font_size = 20  # type: ignore[misc]


class TestGlyphHeight:
    def test_default_ratio(self) -> None:
        box = TextBox(font_size=10, role="label")
        assert glyph_height(box) == pytest.approx(10 * LINE_BOX_RATIO)

    def test_font_size_scales_linearly(self) -> None:
        assert glyph_height(TextBox(font_size=10, role="cell")) == pytest.approx(
            10 * LINE_BOX_RATIO
        )
        assert glyph_height(TextBox(font_size=20, role="cell")) == pytest.approx(
            20 * LINE_BOX_RATIO
        )
        assert glyph_height(
            TextBox(font_size=20, role="cell")
        ) == 2 * glyph_height(TextBox(font_size=10, role="cell"))

    def test_height_override_respected(self) -> None:
        """<foreignObject> math blocks pass their actual bounds via
        ``height`` — the helper should return it verbatim instead of
        approximating from font_size."""
        box = TextBox(font_size=14, role="math", height=60)
        assert glyph_height(box) == 60.0

    def test_height_zero_override(self) -> None:
        box = TextBox(font_size=14, role="math", height=0)
        # Zero is a valid explicit override
        assert glyph_height(box) == 0.0


class TestVStack:
    def test_empty_returns_empty(self) -> None:
        assert vstack([], start_y=100, gap=5) == []

    def test_single_hanging_item(self) -> None:
        box = TextBox(font_size=10, role="label", baseline="hanging")
        ys = vstack([box], start_y=50, gap=5)
        assert ys == [50.0]  # hanging → y attribute equals start_y

    def test_single_central_item(self) -> None:
        box = TextBox(font_size=10, role="caption", baseline="central")
        ys = vstack([box], start_y=50, gap=5)
        # central → y attribute shifted down by half the glyph height
        # so the visual top still sits at start_y
        assert ys == [50.0 + 5.0]

    def test_hanging_then_hanging(self) -> None:
        items = [
            TextBox(font_size=10, role="label", baseline="hanging"),
            TextBox(font_size=11, role="caption", baseline="hanging"),
        ]
        ys = vstack(items, start_y=56, gap=8)
        # First at 56 (hanging). Next cursor = 56 + 10 + 8 = 74.
        assert ys == [56.0, 74.0]

    def test_hanging_then_central(self) -> None:
        """The canonical Array label+caption case."""
        items = [
            TextBox(font_size=10, role="label", baseline="hanging"),
            TextBox(font_size=11, role="caption", baseline="central"),
        ]
        ys = vstack(items, start_y=56, gap=9)
        # Label: hanging → 56.
        # After label: cursor = 56 + 10 + 9 = 75.
        # Caption: central → 75 + 11/2 = 80.5.
        assert ys == [56.0, 80.5]

    def test_honors_height_override(self) -> None:
        items = [
            TextBox(font_size=10, role="math", height=60, baseline="hanging"),
            TextBox(font_size=10, role="label", baseline="hanging"),
        ]
        ys = vstack(items, start_y=0, gap=5)
        # First item forced to 60px tall.
        # Cursor after = 0 + 60 + 5 = 65.
        assert ys == [0.0, 65.0]


class TestStackBottom:
    def test_empty_returns_start_y(self) -> None:
        assert stack_bottom([], start_y=100, gap=5) == 100.0

    def test_single_item_no_gap_contribution(self) -> None:
        box = TextBox(font_size=10, role="label", baseline="hanging")
        # start_y + font_size * LINE_BOX_RATIO = 50 + 10
        assert stack_bottom([box], start_y=50, gap=5) == pytest.approx(60.0)

    def test_two_items_single_gap(self) -> None:
        items = [
            TextBox(font_size=10, role="label", baseline="hanging"),
            TextBox(font_size=11, role="caption", baseline="central"),
        ]
        # 56 + 10 + 11 + 9 = 86.0
        assert stack_bottom(items, start_y=56, gap=9) == pytest.approx(86.0)


class TestInvariantNoOverlap:
    """Property: for any combination of font sizes and baselines, no
    two consecutive glyph boxes overlap in Y. This is the core contract
    vstack exists to enforce."""

    @pytest.mark.parametrize(
        "font_sizes",
        [
            (10, 11),
            (10, 14),
            (14, 11),
            (12, 12),
            (20, 8),
            (10, 10, 10),
            (10, 14, 11),
        ],
    )
    @pytest.mark.parametrize(
        "baselines",
        [
            ("hanging", "hanging"),
            ("hanging", "central"),
            ("central", "hanging"),
            ("central", "central"),
        ],
    )
    @pytest.mark.parametrize("gap", [0, 1, 5, 10])
    def test_no_overlap(
        self,
        font_sizes: tuple[int, ...],
        baselines: tuple[str, ...],
        gap: int,
    ) -> None:
        # Only test combinations where the baseline tuple covers every
        # font size — skip 3-item font_sizes × 2-item baselines.
        if len(font_sizes) > len(baselines):
            return
        items = [
            TextBox(font_size=fs, role="label", baseline=bl)  # type: ignore[arg-type]
            for fs, bl in zip(font_sizes, baselines)
        ]
        ys = vstack(items, start_y=0, gap=gap)
        # Visual bounds for each item
        bounds: list[tuple[float, float]] = []
        for y, box in zip(ys, items):
            gh = glyph_height(box)
            if box.baseline == "hanging":
                top, bottom = y, y + gh
            else:
                top, bottom = y - gh / 2, y + gh / 2
            bounds.append((top, bottom))
        # No two consecutive boxes overlap, and the gap is respected
        for (t1, b1), (t2, b2) in zip(bounds, bounds[1:]):
            assert t2 >= b1, (
                f"Overlap: item ends at {b1}, next starts at {t2} "
                f"(gap={gap}, items={items})"
            )
            assert t2 - b1 == pytest.approx(float(gap)), (
                f"Wrong gap: got {t2 - b1}, expected {gap}"
            )


class TestPixelReproduction:
    """The Array migration seed (start_y=56, gap=9) MUST reproduce the
    exact h12_kruskal_mst queue array coordinates produced by the old
    hardcoded math, otherwise every cookbook example changes pixels."""

    def test_h12_queue_array_coordinates(self) -> None:
        items = [
            TextBox(font_size=10, role="label", baseline="hanging"),
            TextBox(font_size=11, role="caption", baseline="central"),
        ]
        ys = vstack(items, start_y=56, gap=9)
        # int() on the results (as emit_svg does) must hit the exact
        # pre-migration pixels: label_y=56, caption_y=80.
        assert int(ys[0]) == 56
        assert int(ys[1]) == 80

    def test_bounding_bottom_is_tight(self) -> None:
        """The old bounding box was h=96 for an Array with labels +
        caption; the real visual bottom of the caption glyphs is at
        y=86, so the old box was 10px loose. vstack tightens it."""
        items = [
            TextBox(font_size=10, role="label", baseline="hanging"),
            TextBox(font_size=11, role="caption", baseline="central"),
        ]
        bottom = stack_bottom(items, start_y=56, gap=9)
        assert bottom == pytest.approx(86.0)
        # Strictly less than the old hardcoded bbox of 96
        assert bottom < 96
