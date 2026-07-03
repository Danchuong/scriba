"""ShippedFontMeasurer: exact, deterministic, honest fallbacks.

Fixed vectors come from the architecture probes
(investigations/text-width-architecture.md §3.4): Inter tnum digits are
uniformly 1328/2048 em ("12345"@14 = 45.39px — a raw hmtx sum says 40.23,
13% narrow), and NFC equivalence must hold for decomposed Vietnamese.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from importlib.resources import files

from scriba.animation.primitives._text_metrics import (
    HeuristicMeasurer,
    ShippedFontMeasurer,
    get_measurer,
    measure_text,
)
from scriba.animation.primitives._text_render import estimate_text_width


def _vendor(name: str):
    return files("scriba.animation") / "vendor" / "inter" / name


class TestVendoredAssets:
    def test_table_matches_shipped_font(self) -> None:
        data = json.loads(_vendor("inter_advances.json").read_text("utf-8"))
        woff2 = _vendor("Inter-subset.woff2").read_bytes()
        assert data["sha256_woff2"] == hashlib.sha256(woff2).hexdigest(), (
            "advance table was built from a different font file — rerun "
            "scripts/build_text_font.py"
        )

    def test_vietnamese_block_fully_covered(self) -> None:
        data = json.loads(_vendor("inter_advances.json").read_text("utf-8"))
        missing = [
            cp for cp in range(0x1EA0, 0x1EFA) if str(cp) not in data["advances"]
        ]
        assert missing == []


class TestShippedMeasurer:
    def test_digits_use_tabular_advance(self) -> None:
        # tnum: five digits x 1328/2048 em x 14px = 45.39 -> 45
        assert measure_text("12345", 14) == 45

    def test_proportional_not_flat(self) -> None:
        assert measure_text("iiiii", 14) < measure_text("WWWWW", 14)
        # the heuristic said both are 43
        assert estimate_text_width("iiiii", 14) == estimate_text_width("WWWWW", 14)

    def test_nfc_equivalence(self) -> None:
        pre = "ệ"  # U+1EC7
        de = unicodedata.normalize("NFD", pre)
        assert len(de) > 1
        assert measure_text(pre, 14) == measure_text(de, 14)

    def test_cjk_falls_back_to_em_units(self) -> None:
        # out-of-subset CJK: 1em per glyph
        assert measure_text("斜率", 14) == 28

    def test_deterministic(self) -> None:
        a = measure_text("Tổng số phần tử", 14)
        assert a == measure_text("Tổng số phần tử", 14)
        assert isinstance(a, int)

    def test_active_measurer_is_the_shipped_one(self) -> None:
        assert isinstance(get_measurer(), ShippedFontMeasurer)


class TestFallbacks:
    def test_heuristic_parity(self) -> None:
        h = HeuristicMeasurer()
        for s in ("swap", "Đường đi ngắn nhất", "斜率很大"):
            assert h.measure(s, 11) == estimate_text_width(s, 11)

    def test_zwj_cluster_routes_to_heuristic(self) -> None:
        fam = "👨‍👩‍👧"
        assert measure_text(fam, 14) == estimate_text_width(fam, 14)
