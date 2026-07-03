"""Build the shipped text font + advance table (maintainer tool, not install-time).

Produces, from an Inter-Regular.ttf source:
  scriba/animation/vendor/inter/Inter-subset.woff2   (Latin+Vietnamese, no GPOS)
  scriba/animation/vendor/inter/inter_advances.json  (the ShippedFontMeasurer TABLE)

The advance table bakes in the CSS reality (scriba-scene-primitives.css forces
``font-feature-settings: "tnum" "lnum" "zero" "ss01"`` on cell/node text): for
every codepoint whose glyph is rewritten by those GSUB single substitutions,
the SUBSTITUTED glyph's advance is stored — a raw hmtx sum is ~13% wrong for
digits otherwise (Inter tnum digits are uniformly 1328/2048 em vs 833-1323
default). Kerning/GPOS is deliberately dropped from the subset: scriba cell
text is short tokens, and the textLength safety clamp absorbs the residual.

Usage:
    python scripts/build_text_font.py [path/to/Inter-Regular.ttf]

Requires: fonttools + brotli (build-time only — the shipped wheel needs
neither; the runtime measurer reads the baked JSON with stdlib only).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parent.parent
VENDOR = REPO / "scriba" / "animation" / "vendor" / "inter"

# Latin + Latin-Ext A/B + combining block (decomposed input still measures) +
# full Vietnamese block + Horn vowels + dong sign + general punctuation.
UNICODES = "U+0000-00FF,U+0100-024F,U+0300-036F,U+1EA0-1EF9,U+01A0-01B0,U+20AB,U+2000-206F"
# GSUB features the cell/node CSS forces (scriba-scene-primitives.css).
FEATURES = ("tnum", "lnum", "zero", "ss01")


def _feature_substitutions(font: TTFont) -> dict[str, str]:
    """glyph -> substituted glyph for the forced GSUB single-sub features."""
    subs: dict[str, str] = {}
    if "GSUB" not in font:
        return subs
    gsub = font["GSUB"].table
    if not (gsub.FeatureList and gsub.LookupList):
        return subs
    wanted_lookups: list[int] = []
    for rec in gsub.FeatureList.FeatureRecord:
        if rec.FeatureTag in FEATURES:
            wanted_lookups.extend(rec.Feature.LookupListIndex)
    for li in wanted_lookups:
        lookup = gsub.LookupList.Lookup[li]
        if lookup.LookupType != 1:  # single substitution only
            continue
        for st in lookup.SubTable:
            subs.update(st.mapping)
    return subs


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path.home() / "Library/Fonts/Inter-Regular.ttf"
    )
    if not src.exists():
        print(f"source font not found: {src}", file=sys.stderr)
        return 1
    VENDOR.mkdir(parents=True, exist_ok=True)
    out_woff2 = VENDOR / "Inter-subset.woff2"

    subprocess.run(
        [
            sys.executable, "-m", "fontTools.subset", str(src),
            f"--unicodes={UNICODES}",
            "--layout-features=" + ",".join(FEATURES),
            "--flavor=woff2",
            f"--output-file={out_woff2}",
        ],
        check=True,
    )

    font = TTFont(str(out_woff2))
    upm = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    subs = _feature_substitutions(font)

    advances: dict[str, int] = {}
    for codepoint, glyph in cmap.items():
        final_glyph = subs.get(glyph, glyph)
        advances[str(codepoint)] = hmtx[final_glyph][0]

    table = {
        "family": "Scriba Sans (Inter subset)",
        "upm": upm,
        "sha256_woff2": hashlib.sha256(out_woff2.read_bytes()).hexdigest(),
        "features_baked": list(FEATURES),
        "advances": advances,
    }
    out_json = VENDOR / "inter_advances.json"
    out_json.write_text(
        json.dumps(table, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )

    viet_missing = [cp for cp in range(0x1EA0, 0x1EFA) if str(cp) not in advances]
    print(f"woff2: {out_woff2.stat().st_size:,} B")
    print(f"table: {len(advances)} codepoints, upm={upm}")
    print(f"vietnamese block missing: {len(viet_missing)}")
    print(f"digits tnum advance: {advances.get(str(ord('1')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
