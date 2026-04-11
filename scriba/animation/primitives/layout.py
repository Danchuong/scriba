"""Vertical text layout helper — replaces hardcoded Y-offset magic numbers.

Wave 8 background
-----------------

Before Wave 8, ``scriba.animation.primitives.array`` (and siblings
``grid``, ``dptable``) computed index-label and caption Y coordinates from
hardcoded pixel constants::

    INDEX_LABEL_OFFSET = 16
    _CAPTION_GAP       = 24   # retuned from 12 to 24 after Wave 8 baseline flip

Those numbers were tuned empirically for a specific ``dominant-baseline``
choice. When Wave 8 flipped ``.scriba-index-label`` from ``alphabetic`` to
``hanging``, the labels' glyph boxes moved from *above* their ``y``
attribute to *below* it — and the caption (unchanged at ``y + 24`` with
``central`` baseline) suddenly overlapped the label's descended glyphs.

The root cause is that the caller's Y-coordinate arithmetic didn't know
how big the glyphs actually are, so it guessed. Every baseline / font-size
change required another round of re-tuning.

This module kills the ratchet: callers declare what they want to stack
(``TextBox`` descriptors with font size and baseline) and ``vstack``
returns the per-item Y coordinates, guaranteeing that no two glyph
bounding boxes overlap for *any* font size or baseline combination.

The glyph box is approximated from ``font_size`` alone using conservative
sans-serif / monospace ratios published in the W3C CSS Inline Layout spec
(`ascender ≈ 0.80 × font_size`, `descender ≈ 0.20 × font_size`). Real
browser metrics vary by ±5 % across Inter, Roboto, SF Pro, Menlo, SF Mono,
Consolas, DejaVu Sans Mono — the ``gap`` argument absorbs that drift with
room to spare.

API contract
------------

``vstack(items, *, start_y, gap)`` returns a ``list[float]`` of Y values to
pass to ``_render_svg_text``. The contract:

1. ``start_y`` is the visual top of the first glyph box. If the first
   item's baseline is ``hanging`` the returned Y equals ``start_y`` (SVG
   hanging anchors the glyph top to ``y``). If the first item's baseline
   is ``central`` the returned Y is ``start_y + glyph_height / 2`` so
   that the glyph top still lands at ``start_y``.
2. Subsequent items are placed so that their glyph top is ``gap`` pixels
   below the previous item's glyph bottom. The glyph bottom is computed
   from ``glyph_height(box)`` so the invariant holds regardless of
   baseline.
3. ``glyph_height`` respects a caller-supplied ``height`` override (for
   ``<foreignObject>`` math blocks whose actual size is fixed by the
   enclosing rectangle). Otherwise it returns ``LINE_BOX_RATIO *
   font_size``.

The only surviving pixel constants (``ASCENDER_RATIO``, ``DESCENDER_RATIO``,
``LINE_BOX_RATIO``) are font-metric ratios with published sources, not
empirical glyph fudge. See module-level constants below for citations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence


# ---------------------------------------------------------------------------
# Font metric ratios — conservative Latin sans-serif / monospace values
# ---------------------------------------------------------------------------
#
# These are typographic fractions of ``font_size``, not absolute pixels.
# Scriba does not measure the real browser-rendered font; the intent is to
# produce an overestimate of the glyph box so the ``gap`` parameter can
# absorb cross-font drift without introducing overlap.
#
# Sources:
# - W3C CSS Inline Layout Module Level 3 (https://www.w3.org/TR/css-inline-3/)
#   defines the ascent/descent model; typical sans-serif fonts fall
#   within 0.75–0.82 ascent and 0.18–0.25 descent relative to em size.
# - Inter (rsms.me/inter) — UPM 2048, ascent 2728 → 0.80 em at default
#   metric-override.
# - Roboto (fonts.google.com/specimen/Roboto) — hhea ascent 1900/2048 ≈
#   0.93, typo ascent 1536/2048 ≈ 0.75; the conservative 0.80 fits.
# - SF Pro (Apple HIG) — UPM-normalized ascender ≈ 0.77, descender ≈ 0.23.
# - JetBrains Mono, SF Mono, Consolas — cap-height ≈ 0.70–0.73, ascender
#   ≈ 0.78–0.82; 0.80/0.20 is a safe envelope.
#
# If a future change introduces a font whose ascender exceeds 0.85 em or
# descender exceeds 0.25 em, bump these constants.

ASCENDER_RATIO: float = 0.80
"""Fraction of ``font_size`` occupied by the ascender (above the
baseline). Conservative upper bound for the sans-serif and monospace
families Scriba's CSS falls back through."""

DESCENDER_RATIO: float = 0.20
"""Fraction of ``font_size`` occupied by the descender (below the
baseline)."""

LINE_BOX_RATIO: float = ASCENDER_RATIO + DESCENDER_RATIO
"""Total vertical footprint of one line of text as a fraction of
``font_size``. For ``ASCENDER_RATIO = 0.80`` and ``DESCENDER_RATIO =
0.20`` this equals ``1.00`` (i.e. glyph box height ≈ ``font_size``)."""


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

Role = Literal["cell", "label", "caption", "math"]
"""Semantic role of a text item in a layout stack. Callers use this for
documentation; ``vstack`` itself is role-agnostic."""

Baseline = Literal["hanging", "central"]
"""The only two ``dominant-baseline`` values Scriba's primitives currently
emit below cell rows. ``alphabetic`` (the SVG default) is intentionally
excluded — it was the source of the Wave 8 retune ratchet. If you find
yourself wanting ``alphabetic`` for a layout stack, first consider whether
``hanging`` would work; it almost always will."""


@dataclass(frozen=True)
class TextBox:
    """One item in a vertical stack.

    Parameters
    ----------
    font_size:
        Pixel size of the text. Must match the CSS that will actually
        render the text — if the Python primitive says ``font_size=10``
        but the stylesheet says ``14px``, the layout will be wrong. The
        CI guard test ``tests/unit/test_css_font_sync.py`` verifies this
        invariant across every role.
    role:
        Documentation hint — ``"cell"``, ``"label"``, ``"caption"``, or
        ``"math"``. Not consumed by ``vstack`` itself.
    height:
        Optional forced glyph-box height in pixels. Use this for
        ``<foreignObject>`` math blocks whose actual bounds are known
        (e.g. KaTeX output with a computed height). When ``None``,
        ``glyph_height`` falls back to ``LINE_BOX_RATIO * font_size``.
    baseline:
        Either ``"hanging"`` (glyph top sits at Y; glyphs grow downward)
        or ``"central"`` (glyph centered on Y). Default is ``"hanging"``
        because that is the most cross-browser-consistent SVG baseline
        and has the simplest math.
    """

    font_size: int
    role: Role
    height: int | None = None
    baseline: Baseline = "hanging"


def glyph_height(box: TextBox) -> float:
    """Total vertical footprint of *box*, in pixels.

    If ``box.height`` is set (``<foreignObject>`` math case), return it
    verbatim. Otherwise approximate from ``box.font_size`` using the
    conservative ``LINE_BOX_RATIO`` defined at module level.
    """
    if box.height is not None:
        return float(box.height)
    return LINE_BOX_RATIO * box.font_size


def vstack(
    items: Sequence[TextBox],
    *,
    start_y: float,
    gap: float,
) -> list[float]:
    """Compute the ``y`` attribute to pass to ``_render_svg_text`` for
    each *item*, given that the first item's **glyph top** sits at
    ``start_y`` and subsequent items are separated by ``gap`` pixels of
    empty space.

    Invariant
    ---------
    For any two consecutive items ``i`` and ``i + 1``::

        (visual_top of items[i + 1]) - (visual_bottom of items[i]) >= gap

    where::

        visual_top(hanging) = y
        visual_top(central) = y - glyph_height / 2
        visual_bottom(hanging) = y + glyph_height
        visual_bottom(central) = y + glyph_height / 2

    Regardless of how baselines, font sizes, or box heights interleave,
    no two glyph boxes will overlap.

    Parameters
    ----------
    items:
        Ordered top-to-bottom. Empty is valid (returns ``[]``).
    start_y:
        Visual top of the first glyph box, in SVG pixels. Callers
        typically supply ``CELL_HEIGHT + PADDING`` where ``PADDING`` is
        the structural gap between the bottom of the cell row and the
        top of the first stacked item.
    gap:
        Vertical whitespace between consecutive glyph boxes. Kept as a
        single knob that dominates the cross-font drift envelope (±5 %
        of ``font_size``).

    Returns
    -------
    list[float]
        One Y value per input item, suitable as the ``y`` attribute of
        an SVG ``<text>`` element (or the conceptual top of a
        ``<foreignObject>``). Length equals ``len(items)``.
    """
    y_cursor = float(start_y)
    out: list[float] = []
    for box in items:
        gh = glyph_height(box)
        if box.baseline == "hanging":
            # Glyph top sits at y — so y equals the current cursor.
            out.append(y_cursor)
        else:
            # Central — y is the geometric center of the glyph box.
            # Adding half-height keeps the visual top at y_cursor.
            out.append(y_cursor + gh / 2)
        y_cursor += gh + gap
    return out


def stack_bottom(items: Sequence[TextBox], *, start_y: float, gap: float) -> float:
    """Return the visual bottom (pixel coordinate) of the last item in
    the stack, so callers can size their bounding box without duplicating
    the ``vstack`` math.

    Equivalent to the running ``y_cursor`` inside ``vstack`` after the
    final item's ``glyph_height`` has been added, MINUS the trailing
    ``gap`` (since there is no next item to separate from).

    Empty ``items`` returns ``start_y`` unchanged — there is no stack to
    measure.
    """
    if not items:
        return float(start_y)
    total_height = sum(glyph_height(box) for box in items)
    total_gap = gap * (len(items) - 1)
    return float(start_y) + total_height + total_gap


__all__ = [
    "ASCENDER_RATIO",
    "DESCENDER_RATIO",
    "LINE_BOX_RATIO",
    "Baseline",
    "Role",
    "TextBox",
    "glyph_height",
    "stack_bottom",
    "vstack",
]
