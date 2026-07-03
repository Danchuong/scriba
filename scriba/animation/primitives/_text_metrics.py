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

__all__ = ["TextMeasurer", "get_measurer", "measure_text"]


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
