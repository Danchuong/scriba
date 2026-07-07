"""Bake KaTeX glyph advances for label-math measurement.

Slices ``fontMetricsData`` out of the vendored ``katex.min.js`` (the
identifier is minified away but the tables are verbatim) and writes
``scriba/tex/vendor/katex/katex_advances.json`` with, per glyph, the two
values horizontal measurement needs:

    metrics[font][charcode] = [width_em, italic_correction_em]

KaTeX's own structure is ``[depth, height, italic, skew, width]`` — width
is index 4, italic correction index 2 (load-bearing for Math-Italic
capitals: KaTeX bakes it into the glyph's box advance;
investigations/folabel-measure.md §2).

Only the five fonts inline label math can reach are baked (~18 KB). Run
this after every KaTeX vendor refresh:

    python scripts/build_katex_metrics.py

Runtime consumers (`_math_metrics.py`) are stdlib-only; this script is the
build-time tool, mirroring scripts/build_text_font.py.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KATEX_JS = REPO / "scriba" / "tex" / "vendor" / "katex" / "katex.min.js"
OUT = REPO / "scriba" / "tex" / "vendor" / "katex" / "katex_advances.json"

# The only fonts reachable from inline label math (folabel-measure.md §2):
# digits/delimiters/operators, italic variables, AMS relations, inline big
# operators, bold labels. SansSerif-Bold is the annotation-pill text face
# (the 600-weight pill label paints in KaTeX_SansSerif Bold, matching the
# KaTeX math it sits beside — spec-fix-annot-pill-font-clash).
FONTS = ("Main-Regular", "Math-Italic", "AMS-Regular", "Size1-Regular", "Main-Bold", "SansSerif-Bold")

_ENTRY_RE = re.compile(r"(\d+):\[([^\]]*)\]")


def _extract_block(text: str, name: str) -> str | None:
    key = f'"{name}":{{'
    i = text.find(key)
    if i < 0:
        return None
    start = i + len(key) - 1
    depth = 0
    for j in range(start, len(text)):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : j + 1]
    return None


def _parse_block(block: str) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for m in _ENTRY_RE.finditer(block):
        vals: list[float] = []
        for v in m.group(2).split(","):
            v = v.strip() or "0"
            if v.startswith("."):
                v = "0" + v
            elif v.startswith("-."):
                v = "-0" + v[1:]
            vals.append(float(v))
        if len(vals) >= 5:
            # keep [width, italic, height, depth] (KaTeX order is
            # [depth, height, italic, skew, width])
            out[m.group(1)] = [vals[4], vals[2], vals[1], vals[0]]
    return out


def main() -> int:
    text = KATEX_JS.read_text("utf-8")
    version = "unknown"
    vm = re.search(r'version:"([^"]+)"', text)
    if vm:
        version = vm.group(1)

    metrics: dict[str, dict[str, list[float]]] = {}
    for font in FONTS:
        block = _extract_block(text, font)
        if block is None:
            print(f"ERROR: font table {font!r} not found in {KATEX_JS}", file=sys.stderr)
            return 1
        parsed = _parse_block(block)
        if len(parsed) < 40:
            print(f"ERROR: {font} parsed only {len(parsed)} glyphs", file=sys.stderr)
            return 1
        metrics[font] = parsed
        print(f"{font}: {len(parsed)} glyphs")

    payload = {"katex_version": version, "values": "[width_em, italic_em, height_em, depth_em]", "metrics": metrics}
    OUT.write_text(json.dumps(payload, separators=(",", ":")), "utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes, katex {version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
