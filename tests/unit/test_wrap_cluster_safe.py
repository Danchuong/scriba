"""Spaceless-script wrap: oversized tokens split cluster-safely (F4).

``_wrap_label_lines`` splits only on space/comma/+/= — Thai/Khmer/Lao
write without spaces, so a Thai label became ONE un-splittable token
overflowing far past the figure (allscript-render-audit.md, DEGRADED).
Oversized non-math tokens now split at the width budget WITHOUT ever
starting a line on a combining mark (torn clusters render corrupt).
"""

from __future__ import annotations

import unicodedata

from scriba.animation.primitives._svg_helpers import _wrap_label_lines
from scriba.animation.primitives._text_render import estimate_text_width

_THAI = "ขั้นตอนวิธีการค้นหาแบบทวิภาคสำหรับแถวลำดับที่เรียงแล้ว"


class TestOversizedTokenSplit:
    def test_thai_wraps_within_budget(self) -> None:
        lines = _wrap_label_lines(_THAI, max_px=132.0, font_px=11)
        assert len(lines) >= 2, "spaceless Thai must wrap, not overflow"
        for ln in lines:
            assert estimate_text_width(ln, 11) <= 132.0 + 8, ln

    def test_no_line_starts_on_combining_mark(self) -> None:
        lines = _wrap_label_lines(_THAI, max_px=100.0, font_px=11)
        for ln in lines:
            assert ln and unicodedata.category(ln[0]) not in ("Mn", "Mc"), (
                f"torn cluster: line starts with combining mark {ln[:6]!r}"
            )

    def test_char_mode_also_splits(self) -> None:
        lines = _wrap_label_lines(_THAI, max_chars=24)
        assert len(lines) >= 2
        for ln in lines:
            assert unicodedata.category(ln[0]) not in ("Mn", "Mc")

    def test_math_token_still_never_splits(self) -> None:
        label = "$dp[i][j] = \\min(dp[i-1][j], dp[i][j-1]) + cost$"
        assert _wrap_label_lines(label, max_px=60.0, font_px=11) == [label]

    def test_latin_behaviour_unchanged(self) -> None:
        text = "so sánh phần tử hiện tại với phần tử kế tiếp"
        assert _wrap_label_lines(text, max_px=132.0, font_px=11) == \
            _wrap_label_lines(text, max_px=132.0, font_px=11)
        joined = "".join(_wrap_label_lines(text, max_px=132.0, font_px=11))
        assert joined.replace(" ", "") == text.replace(" ", "")
