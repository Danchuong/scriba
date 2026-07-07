"""Single-line annotation pills must carry unicode-bidi:plaintext for RTL text.

The multi-line label path applies _bidi_style, but the single-line <text>
fallback omitted it, so a short Arabic/Hebrew pill label scrambled (the RTL
run rendered without bidi isolation). RQ hunt2-crossprim.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402

_ARABIC = "نتيجة"  # "result"


def _render(source: str, tmp_path: Path) -> str:
    t, o = tmp_path / "in.tex", tmp_path / "out.html"
    t.write_text(source, encoding="utf-8")
    render_file(t, o)
    return o.read_text(encoding="utf-8")


def _text_tag_containing(html: str, needle: str) -> str | None:
    m = re.search(r"<text\b[^>]*>[^<]*" + re.escape(needle), html)
    return m.group(0) if m else None


class TestRtlPillBidi:
    def test_single_line_arabic_pill_has_bidi(self, tmp_path: Path) -> None:
        html = _render(
            '\\begin{animation}[id="r", label="rtl pill"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            f'\\annotate{{a.cell[1]}}{{label="{_ARABIC}", position=above}}\n'
            "\\end{animation}\n",
            tmp_path,
        )
        tag = _text_tag_containing(html, _ARABIC)
        assert tag is not None, "Arabic pill <text> not found"
        assert "unicode-bidi:plaintext" in tag, (
            "single-line RTL pill omits bidi isolation -> scrambles"
        )

    def test_latin_pill_unchanged(self, tmp_path: Path) -> None:
        # Byte guard: an LTR label must NOT gain the bidi property.
        html = _render(
            '\\begin{animation}[id="r", label="ltr pill"]\n'
            "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
            "\\step\n"
            '\\annotate{a.cell[1]}{label="pivot", position=above}\n'
            "\\end{animation}\n",
            tmp_path,
        )
        tag = _text_tag_containing(html, "pivot")
        assert tag is not None
        assert "unicode-bidi" not in tag
