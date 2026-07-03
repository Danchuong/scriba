"""Exact text metrics for the shipped, pinned sans ("Scriba Sans").

The 14px cell/node surface is the dominant viewBox-sizing driver, and it
used a per-char heuristic (0.62em Latin average) that measured -38%..+154%
against real rendering. Since 0.22.0 that surface renders in a shipped
Inter subset pinned first in the font stack, so its width can be computed
EXACTLY: sum the font's own advance values (baked at vendor time into
``inter_advances.json`` by ``scripts/build_text_font.py``).

Runtime is stdlib-only — fontTools is a build-time tool; the wheel ships
the JSON table. Exactness bench: advance-sum predicts browser rendering of
the same font to p95 0.12% (investigations/text-width-bench.md).

Two correctness details baked into the table, not this module:
- digits store the ``tnum`` SUBSTITUTED advance (the cell CSS forces
  ``font-feature-settings: "tnum" "lnum" "zero" "ss01"``; a raw hmtx sum
  is ~13% narrow for numbers);
- the subset covers the combining block, and ``measure`` NFC-normalizes
  first, so decomposed Vietnamese input measures identically to
  precomposed.

Fallback ladder inside ``measure``: codepoints outside the table fall back
to the per-char heuristic unit (CJK ≈ 1em etc.); strings containing ZWJ
clusters fall back to the whole-string heuristic (cluster segmentation is
the estimator's specialty). If the vendored table is missing entirely,
``get_measurer()`` returns the heuristic measurer — behaviour degrades to
pre-0.22.0 estimates, never crashes.
"""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from importlib.resources import files
from typing import Protocol

from scriba.animation.primitives._text_render import (
    _char_display_width,
    estimate_text_width,
)

# Complex-script blocks whose widths are heuristic over-estimates (W1301).
# CJK is deliberately absent: its 1em-per-glyph fallback measures real
# rendering to ~0.0%, so there is nothing to warn about.
_COMPLEX_BLOCKS: tuple[tuple[int, int, str], ...] = (
    (0x0590, 0x05FF, "Hebrew"),
    (0x0600, 0x08FF, "Arabic"),
    (0x0900, 0x0DFF, "Indic (Devanagari…Sinhala)"),
    (0x0E00, 0x0E7F, "Thai"),
    (0x0E80, 0x0EFF, "Lao"),
    (0x1000, 0x109F, "Myanmar"),
    (0x1780, 0x17FF, "Khmer"),
    (0xAC00, 0xD7AF, "Hangul"),
    (0xFB1D, 0xFDFF, "Arabic/Hebrew presentation"),
    (0xFE70, 0xFEFF, "Arabic presentation"),
)
_warned_scripts: set[str] = set()


def _warn_heuristic_script(cp: int) -> None:
    """W1301, once per script per process: this run is a SAFE over-estimate
    (shaping only ever narrows text — investigations/allscript-shaping.md),
    so nothing clips; boxes may just be wider than necessary. Exact metrics
    for these scripts require a pinned font + shaping (the [intl] ladder in
    investigations/allscript-architecture.md)."""
    import warnings as _w

    for lo, hi, name in _COMPLEX_BLOCKS:
        if lo <= cp <= hi:
            if name not in _warned_scripts:
                _warned_scripts.add(name)
                _w.warn(
                    f"scriba W1301: {name} text is measured with a safe "
                    "heuristic over-estimate (never clips; boxes may be "
                    "wider than needed). Exact metrics for this script "
                    "need a pinned font — see "
                    "investigations/allscript-architecture.md.",
                    stacklevel=4,
                )
            return

__all__ = ["TextMeasurer", "get_measurer", "measure_label_line", "measure_text"]


class TextMeasurer(Protocol):
    def measure(self, text: str, font_px: int) -> int:
        """Rendered width in px (rounded like estimate_text_width)."""
        ...


class HeuristicMeasurer:
    """The pre-0.22.0 estimator, verbatim — the no-font fallback."""

    def measure(self, text: str, font_px: int) -> int:
        return estimate_text_width(text, font_px)


class ShippedFontMeasurer:
    """Exact advance-sum against the vendored "Scriba Sans" subset."""

    def __init__(self, advances: dict[int, int], upm: int) -> None:
        self._advances = advances
        self._upm = upm

    def measure(self, text: str, font_px: int) -> int:
        s = unicodedata.normalize("NFC", str(text))
        if "‍" in s:
            # ZWJ emoji clusters: the estimator's two-pass cluster logic is
            # the honest answer; the table has no cluster notion.
            return estimate_text_width(s, font_px)
        total_units = 0.0
        for ch in s:
            adv = self._advances.get(ord(ch))
            if adv is None:
                # out-of-subset (CJK, symbols): heuristic em-units, scaled
                # to font units so one sum stays exact for covered spans
                _warn_heuristic_script(ord(ch))
                total_units += _char_display_width(ch) * self._upm
            else:
                total_units += adv
        return int(total_units / self._upm * font_px + 0.5)


@lru_cache(maxsize=1)
def get_measurer() -> TextMeasurer:
    """Process-wide measurer: shipped-font table when vendored, else heuristic."""
    try:
        raw = (
            files("scriba.animation") / "vendor" / "inter" / "inter_advances.json"
        ).read_text("utf-8")
        data = json.loads(raw)
        advances = {int(k): int(v) for k, v in data["advances"].items()}
        return ShippedFontMeasurer(advances, int(data["upm"]))
    except (FileNotFoundError, KeyError, ValueError, OSError):
        return HeuristicMeasurer()


def measure_text(text: str, font_px: int) -> int:
    """Width of *text* on the pinned-sans surface (cells/nodes)."""
    return get_measurer().measure(text, font_px)


def measure_label_line(line: str, font_px: int) -> int:
    """Width of a mixed text+``$math$`` label line, in px.

    Mirrors the exact split `_render_mixed_html` renders with
    (``_INLINE_MATH_RE``): text segments flow in the label mono font
    (``estimate_text_width`` ≈0.62 em/char, a +3% safe over of the
    measured 0.60 mono advance), math segments take the KaTeX advance-sum
    (``measure_inline_math``). Inline flow adds no inter-segment gap, so
    the composition is additive — proven exact to <0.05% against Chromium
    (investigations/folabel-measure.md §5).
    """
    from scriba.animation.primitives._math_metrics import measure_inline_math
    from scriba.animation.primitives._text_render import _INLINE_MATH_RE

    if "$" not in line:
        return estimate_text_width(line, font_px)
    total = 0.0
    pos = 0
    for m in _INLINE_MATH_RE.finditer(line):
        text_seg = line[pos : m.start()]
        if text_seg:
            total += estimate_text_width(text_seg, font_px)
        total += measure_inline_math(m.group(1), font_px)
        pos = m.end()
    tail = line[pos:]
    if tail:
        total += estimate_text_width(tail, font_px)
    return int(total + 0.5)
