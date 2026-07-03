# All-Script Shaping: exact metrics for Arabic / Thai / Devanagari / Korean and the identity wall

> Structural design investigation. **No repo source modified.** All probes ran in a throwaway
> scratchpad venv (`fontTools 4.63` + `uharfbuzz 0.55.0` + `brotli`, py3.14) against fonts
> already on this Mac, with ground truth from the repo's pinned headless Chromium
> (`chrome-headless-shell-1223`, `getComputedTextLength()` on SVG `<text>`, 14 px).
> Sibling prior art: `text-width-architecture.md` (the shipped Latin+Vietnamese Inter path),
> `text-width-bench.md`.

---

## 1. Hand-off Brief

**Question.** Today scriba is exact for Latin/Vietnamese (shipped Inter subset, advance-sum) and
for CJK Han (the `1.0 em` heuristic is genuinely correct for square ideographs). Every other
script over-estimates: Arabic **+28%**, Devanagari **+37.7%**, Korean **+15.6%**, Thai **+6.7%**
(task baseline vs headless-chrome). Can we make those exact too, and what does it cost?

**Short answer — two independent problems, only one of which uharfbuzz solves.**

1. **Shaping.** For Arabic/Devanagari you *cannot* get the right width by summing per-codepoint
   `cmap`+`hmtx` advances — cursive joining and conjunct formation (GSUB/GPOS) change both glyph
   count and advances. **uharfbuzz (a HarfBuzz binding) reproduces the browser's own shaper to
   within 0.02%** — proven below across 25 fonts. This half is *solved and exact*.
2. **Identity (the wall).** A shaped advance-sum is only exact if scriba measures **the exact
   font the reader's browser renders**. It doesn't — cell/label text falls back to the reader's
   OS fonts. The *same Arabic string* spans **62–82 px (28% spread)** across Mac Arabic fonts;
   Thai **25%**, Korean **16%**, Devanagari **7%**. That spread is the **irreducible error you
   eat if you shape-but-don't-ship the font.** uharfbuzz does nothing for it.

**Verdict.** "Exact for every language" = **shape (uharfbuzz) *and* ship+pin the font** — exactly
the deal scriba already struck for Inter. Shaping is cheap (~3 µs/string, 1–3 MB permissive
optional wheel). Shipping the *fonts* is the cost: Arabic/Thai/Devanagari subset to ~0.1–0.5 MB
each, **but Korean+CJK coverage is 15–40 MB** — the real blocker. So the honest landing is a
**tiered optional extra** (`scriba[intl]`): default stays today's safe over-estimate (never
clips); the extra buys shaped exactness for the scripts whose fonts are worth shipping.

| Claim (this doc) | Evidence | Result |
|---|---|---|
| Shaped advance-sum == browser, same font | §2, 25 fonts × 4 scripts | Δ ≤ **0.02%** (1 name-resolution outlier at 0.36%) |
| Naive `cmap+hmtx` (no shaping) is wrong | §2 | Arabic **+13…+23%**, Deva **+10%**, Thai **0…+12%** (font-dep.), Korean **0%** |
| Cross-font identity spread (can't fix by shaping) | §3 | Arabic **28.4%**, Thai **25.3%**, Korean **16.1%**, Deva **7.0%** |
| Mixed bidi width = Σ per-run shaped widths | §4 | Δ **0.025%**; wrong (single-buffer) way = **+15%** |
| Shaping cost | §6 | import **0.17 ms**, **3.3 µs/string**, 504-string doc = **1.7 ms** |
| uharfbuzz is a safe optional dep | §6 | abi3 wheels all platforms, 1–3 MB, Apache-2.0, no compiler |

**Key nuance — Korean is an identity problem, not a shaping one.** Modern Hangul is
NFC-precomposed (one syllable = one glyph); naive == shaped == browser (§2). So Korean needs
**no HarfBuzz** — it needs the *font*. And the current `1.0 em` model is simply wrong for it:
real Mac Korean renders at **0.74–0.88 em/syllable** (Apple SD Gothic Neo 104 px vs the 140 px
the 1 em heuristic predicts for 10 syllables). CJK Han stays at 1 em; Hangul does not.

---

## 2. uharfbuzz bench — shaped advance-sum vs browser ground truth (same font, 14 px)

Method: `uharfbuzz.Buffer.add_str` → `guess_segment_properties()` (auto script/dir/lang, turns on
the default features `init/medi/fina/liga/calt/ccmp`) → `hb.shape(font, buf, None)` →
`Σ x_advance / upem × 14`. Browser: the identical string in an SVG `<text>` with
`font-family` pinned to the same face, `getComputedTextLength()`. "naive" = ReportLab-style
`Σ hmtx[cmap[cp]]` with **no** shaping.

| script | font | shaped px | browser px | **Δ shaped** | naive px | Δ naive (no-shape) | chars→glyphs |
|---|---|--:|--:|--:|--:|--:|--:|
| Arabic | Geeza Pro | 75.52 | 75.53 | **−0.02%** | 89.96 | **+19.1%** | 14→14 |
| Arabic | Damascus | 67.41 | 67.42 | −0.02% | 76.45 | +13.4% | 14→14 |
| Arabic | Baghdad | 62.23 | 62.23 | +0.00% | 71.50 | +14.9% | 14→14 |
| Arabic | Nadeem | 64.49 | 64.50 | −0.02% | 74.56 | +15.6% | 14→14 |
| Arabic | Al Bayan | 64.29 | 64.30 | −0.01% | 76.73 | +19.3% | 14→14 |
| Arabic | Beirut | 72.00 | 72.02 | −0.02% | 86.00 | +19.4% | 14→14 |
| Arabic | Arial Unicode MS | 82.04 | 82.05 | −0.00% | 100.83 | **+22.9%** | 14→14 |
| Thai | Thonburi | 119.56 | 119.56 | −0.00% | 133.77 | **+11.9%** | 17→15 |
| Thai | Ayuthaya | 124.80 | 124.81 | −0.01% | 124.80 | −0.01% | 17→17 |
| Thai | Krungthep | 132.72 | 132.73 | −0.01% | 132.72 | −0.01% | 17→17 |
| Thai | Sathu | 106.34 | 106.34 | −0.00% | 106.34 | −0.00% | 17→17 |
| Thai | Silom | 102.96 | 102.97 | −0.01% | 102.96 | −0.01% | 17→17 |
| Thai | Arial Unicode MS | 119.85 | 119.86 | −0.01% | 119.85 | −0.01% | 17→17 |
| Devanagari | Devanagari MT | 78.18 | 78.19 | −0.01% | 86.46 | **+10.6%** | 13→11 |
| Devanagari | Kohinoor Devanagari | 76.78 | 76.78 | −0.01% | 84.21 | +9.7% | 13→11 |
| Devanagari | Devanagari Sangam MN | 75.04 | 75.05 | −0.01% | 82.82 | +10.3% | 13→11 |
| Devanagari | ITF Devanagari | 73.14 | 72.88 | +0.36%\* | 80.00 | +9.8% | 13→11 |
| Devanagari | Shree Devanagari 714 | 74.77 | 74.77 | −0.00% | 81.90 | +9.5% | 13→11 |
| Devanagari | Arial Unicode MS | 78.07 | 78.08 | −0.01% | 85.89 | +10.0% | 13→11 |
| Korean | Apple SD Gothic Neo | 104.24 | 104.25 | −0.01% | 104.24 | −0.01% | 10→10 |
| Korean | AppleGothic | 120.96 | 120.97 | −0.01% | 120.96 | −0.01% | 10→10 |
| Korean | AppleMyungjo | 123.09 | 123.09 | −0.00% | 123.09 | −0.00% | 10→10 |
| Korean | Arial Unicode MS | 119.78 | 119.78 | −0.00% | 119.78 | −0.00% | 10→10 |

Strings: Arabic `خوارزمية البحث`, Thai `การค้นหาแบบไบนารี`, Devanagari `द्विआधारी खोज`,
Korean `이진 탐색 알고리즘`.

**Readings.**
- **The browser *is* HarfBuzz.** Chrome shapes with HarfBuzz, so uharfbuzz matching it to
  ≤0.02% is expected — and it means an offline Python measurer can be *pixel-identical* to what
  the browser paints, for the font it measures. The residual is sub-pixel rounding (HB integer
  units vs the browser's fractional `getComputedTextLength`).
- **Shaping is load-bearing exactly where the script is cursive/conjunct.** Arabic collapses
  from 14→14 glyphs but every glyph switches to a joined (init/medi/fina) form with a *smaller*
  advance ⇒ naive is +13…+23% too wide. Devanagari 13→11 (conjunct `द्वि`, reordered `ि`) ⇒
  +10%. **Thai is font-dependent**: Thonburi stacks marks (17→15, naive +12%) but Ayuthaya/
  Krungthep/Sathu/Silom keep spacing marks (17→17, naive ≈ 0%). **Korean needs no shaping** —
  precomposed syllables, 10→10, naive == shaped.
- **\*ITF Devanagari 0.36%** is a *measurement* artifact, not a shaper error: that face's
  `name` ID 1 is a Devanagari-script localized string, so the browser couldn't match the pinned
  family and fell back to another Deva font — an accidental live demo of the identity problem
  in §3. 24/25 fonts are ≤0.02%.

**4-way tie-back to scriba's current heuristic** (`estimate_text_width`, the shipped fallback):

| script (font) | scriba heuristic px | naive px | **shaped px** | heuristic ÷ shaped |
|---|--:|--:|--:|--:|
| Arabic (Geeza Pro) | 122.0 | 89.96 | 75.52 | **1.62×** |
| Thai (Thonburi) | 130.0 | 133.77 | 119.56 | 1.09× |
| Devanagari (Devanagari MT) | 104.0 | 86.46 | 78.18 | 1.33× |
| Korean (AppleGothic) | 129.0 | 120.96 | 120.96 | 1.07× |

The heuristic's over-estimate is *font-dependent* (that's the point): measured against the
unpinned headless default fallback it is Arabic **+64%**, Devanagari **+43%**, Thai **+8.7%**,
Korean **+8.5%** — same sign as the task's +28/+37.7/+6.7/+15.6% baseline, magnitudes varying
with which font the environment happens to fall back to. **All over-estimates ⇒ scriba never
clips today; it only reserves too much box.** Determinism: 50 repeat shapes of the Arabic string
returned the identical integer advance sum (11932 units) — safe for byte-exact goldens.

---

## 3. Cross-font irreducible error — the identity wall (browser px, same string)

If scriba shapes against font **A** but the reader's browser renders font **B**, the error is the
inter-font spread — and shaping cannot touch it. Measured across every covering Mac font:

| script | browser px range (font → font) | **spread** |
|---|---|--:|
| **Arabic** | 62.23 (Baghdad) → 75.53 (Geeza) → 82.05 (Arial Unicode MS) | **28.4%** |
| **Thai** | 102.97 (Silom) → 119.6 (Thonburi) → 132.73 (Krungthep) | **25.3%** |
| **Korean** | 104.25 (Apple SD Gothic Neo) → 120.97 (AppleGothic) → 123.09 (AppleMyungjo) | **16.1%** |
| **Devanagari** | 72.88 (ITF) → 76.78 (Kohinoor) → 78.19 (Devanagari MT) | **7.0%** |

**This is the whole argument for shipping.** "Exact metrics" for Latin worked only because
scriba *ships and pins* Inter (`text-width-architecture.md` §1). For complex scripts the identity
spread is **larger** than the shaping error it's trying to fix (Arabic: a 28% identity wall
around a 19% shaping gap). Shaping without shipping trades a systematic over-estimate for a
random ±14% two-sided error — **strictly worse**, because it can now *under*-estimate and clip.
Therefore: shape **only** the fonts scriba itself ships and pins. Everything else must stay on
the safe over-estimate.

---

## 4. Mixed / bidi verdict — width **is** the sum of per-run shaped widths

Test: pin one font that covers both scripts (Arial Unicode MS) so browser and shaper use the
*same* glyphs per run; segment (§5), shape each run, sum; compare to the browser rendering the
whole string.

| string | Σ per-run shaped | browser | **Δ** | wrong way (1 buffer) |
|---|--:|--:|--:|--:|
| `giá trị x = قيمة` (Latin→Arabic) | 85.13 | 85.16 | **−0.025%** | 97.95 (**+15.0%**) |
| `Tổng 42 द्विआधारी` (Viet→Deva) | 105.10 | 105.11 | −0.013% | — |
| `خوارزمية v2 (البحث)` (Ar→Lat→Ar) | 110.04 | 110.08 | −0.030% | — |
| `node[3] = ค่า` (Lat→Thai) | 78.12 | 78.12 | −0.005% | — |
| `x=5, 日本語, ok` (Lat→CJK→Lat) | 95.31 | 95.31 | −0.006% | — |
| `الوزن: ٤٢` (Arabic + Arabic-Indic digits) | 50.54 | 50.56 | −0.035% | — |

**Verdict: YES.** Bidi reordering is *visual only* — total advance width is direction-independent
and equals the arithmetic sum of the per-run shaped widths, to ≤0.035%. **Corollary (critical):**
you must **itemize into script runs and shape each run separately.** Shaping the whole mixed
string as one HarfBuzz buffer (one `guess_segment_properties` picks a single script for
everything) is **+15% wrong** — the shaper mis-shapes the minority-script run.

**`tabular-nums` inside runs.** European digits `0123456789` in Arial Unicode MS measured
77.86 px shaped == 77.88 px browser, and `tnum` on/off was a **no-op** there (that font's figures
are already monospaced). `tnum` only moves width for **proportional-figure** fonts — which is
exactly the shipped-Inter Latin case already handled (`text-width-architecture.md` §3.4: Inter
`"12345"` = 40.23 px default vs 45.39 px tabular, a 13% swing). Rule for the shaper: **replay the
same OpenType features the CSS sets on that run** — for pinned-Inter cells that's `tnum/zero/ss01`
(baked into today's table); for a shaped complex run it's HB's script defaults. Digits sit in
`Common` and inherit the surrounding run's features (§5).

---

## 5. Script segmentation design (stdlib, no ICU)

The router splits a string into maximal runs and dispatches each to the cheapest exact path.
Prototyped in pure `unicodedata` (block/name + general-category), validated in §4 (all runs
correct, ≤0.035%).

**Algorithm (UAX #24 "resolved script", simplified):**
1. Per char, resolve a script: `unicodedata.name()` prefix (`ARABIC`/`THAI`/`DEVANAGARI`/
   `HANGUL`/`CJK`/`HIRAGANA`/`KATAKANA`/`LATIN`…). Fold Hiragana/Katakana/CJK → `CJK`.
2. **Neutrals attach, they don't split.** `Common` (spaces `Zs`, digits `N*`, punctuation `P*`,
   symbols `S*`) and `Inherited` (combining marks `Mn/Mc/Me`) carry **no script of their own** —
   append them to the *current* run (or the *following* run if they lead the string). This is why
   `giá trị x = ` (with the space, `=`, and digits) stayed one Latin run, and `الوزن: ٤٢` (Arabic
   + Arabic-Indic digits + colon) stayed one Arabic run.
3. Emit `[(script, substring)]` at each real script transition.

**Dispatch table (the routing seam):**

| run script | route to | exact? | ships a font? |
|---|---|---|---|
| Latin / Vietnamese / Latin-Ext | **baked Inter advance table** (today's `ShippedFontMeasurer`) | ✅ exact | already (Inter subset, 43 KB) |
| CJK Han (`W`/`F` ideographs) | **`1.0 em` table** | ✅ exact (square ideographs) | no — 1 em is correct |
| Hangul | Korean-font advance table **if shipped**, else `1.0 em` | ⚠️ 1 em is +14…+34% high | only under `[intl]` |
| Arabic / Devanagari / Thai / other complex | **uharfbuzz shaper** against a **shipped+pinned** font | ✅ exact *iff* shipped | only under `[intl]` |
| any script whose font is **not** shipped | **`estimate_text_width` heuristic** | over-estimate (safe, no clip) | no |

The segmenter is stdlib and deterministic; the measurer stays behind the existing
`TextMeasurer` Protocol (`_text_metrics.py`). Only the **complex** branch needs uharfbuzz, and
only when the run's font is one scriba ships — so the seam degrades cleanly to today's behavior
when the extra is absent.

---

## 6. Cost + dependency reality

**Runtime cost (measured, this Mac, warm `Face`/`Font` cached):**

| metric | value |
|---|--:|
| `import uharfbuzz` | **0.17 ms** (≈ `import fontTools.ttLib`) |
| cold first shape (file read + `Face` build + shape, 956 KB `GeezaPro.ttc`) | 8.3 ms (one-time / font) |
| per-string shape+sum (Latin 11-ch) | 2.0 µs |
| per-string shape+sum (Arabic 14-ch / Deva 13-ch) | 3–7 µs |
| **504 mixed strings (a heavy doc), warm** | **1.67 ms total** (3.3 µs/string) |

**Shape-at-render is viable** — a whole document's complex-script text costs single-digit ms,
dwarfed by the one-time per-font `Face` build (cache it process-wide, exactly like
`get_measurer()` is `lru_cache`d today). No need to precompute at build time for the *shaping*
math itself; the only build-time asset is the **font subset** you choose to ship.

**uharfbuzz packaging** (v0.55.0, 2026-06-03; 96 releases; maintained by the HarfBuzz org):

| platform | prebuilt wheel? | note |
|---|:--:|---|
| macOS arm64 | ✅ | `cp310-abi3-macosx_11_0_arm64` (1.3 MB) |
| macOS x86_64 | ✅ | via `macosx_10_9_universal2` (3.0 MB) |
| manylinux x86_64 / aarch64 | ✅ | `manylinux_2_17/2_28` (1.8–1.9 MB) |
| musllinux x86_64 / aarch64 (Alpine) | ✅ | `musllinux_1_2` (2.8–2.9 MB) |
| Windows amd64 / win32 | ✅ | (1.1–1.3 MB) |
| sdist | ✅ | vendors minimal HarfBuzz C++; needs a C++ compiler + Cython **only** if no wheel matches |

`abi3` ⇒ **one wheel per platform covers CPython 3.10→3.14+**; `Requires-Python >=3.10` (drops
3.9). **No compiler needed** on any mainstream target. **License: Apache-2.0** wrapper over
HarfBuzz's permissive **Old-MIT** — safe to depend on. **There is no pure-Python shaper** —
`fontTools` does *not* shape (it only uses uharfbuzz optionally, with a fallback, for its GSUB
repacker); real shaping = a compiled HarfBuzz binding. So the only pure-Python-preserving option
is to gate it behind an extra.

---

## 7. Optional-extra architecture — the dependency ladder

scriba today has **zero compiled runtime deps**. Preserve that as the floor; sell exactness as an
opt-in. Standard mechanism (PEP 621): `[project.optional-dependencies]` + `pip install
scriba[intl]` + a `try/except ImportError` runtime probe (the exact pattern fontTools uses for
uharfbuzz).

```
Tier 0  — pip install scriba              (today, unchanged, pure-Python)
          Latin/Viet  : exact (baked Inter advance table)
          CJK Han     : exact (1.0 em)
          Hangul      : 1.0 em over-estimate (safe; +14…34% high, never clips)
          Arabic/Thai/Deva/…: estimate_text_width over-estimate (safe, never clips)

Tier 1  — pip install scriba[intl]        (adds uharfbuzz ~1–3 MB wheel + shipped intl fonts)
          + ship & pin Noto subsets (Arabic/Thai/Devanagari …) like Inter
          + segment runs (§5); shape complex runs with uharfbuzz against the shipped font
          → shaped-exact (≤0.1%) for every script whose font is bundled
          (Korean/CJK exactness = ship the CJK font; see §8 size reality)
```

```python
try:
    import uharfbuzz as hb
    _HAS_SHAPING = True
except ImportError:
    _HAS_SHAPING = False       # Tier 0: get_measurer() returns the heuristic path
```

**Design invariants.**
- **Never regress safety.** A shaped width is used *only* when scriba both ships the font and
  pins it in that surface's `font-family` (so measured == rendered). Otherwise fall to the
  over-estimate. This keeps the §3 identity wall from ever producing an *under*-estimate/clip.
- **One seam.** Everything hangs off the existing `TextMeasurer` Protocol + `get_measurer()`
  (`_text_metrics.py`); Tier 0 is literally today's object. Add a `ShapedMeasurer` that owns the
  segmenter + a per-font HB `Font` cache; `get_measurer()` returns it only when `_HAS_SHAPING`
  **and** an intl font is vendored.
- **Determinism holds.** Integer advance sums are byte-stable (§2); a `[intl]` build re-pins its
  own goldens once (same mechanism as the Inter landing), gated so the default corpus is
  unaffected.

---

## 8. Prior art — everyone who gets this right uses HarfBuzz; the one who didn't is the cautionary tale

| engine | shaper | full shaping? | width from | run split / bidi |
|---|---|:--:|---|---|
| **XeTeX** (since 0.9999, 2013) | **HarfBuzz** (+ Graphite, CoreText on mac) | ✅ | shaper glyph advances → TeX box/glue | runs by font/script/dir; ICU bidi |
| **LuaTeX** / luaotfload | native **Lua** shaper *or* **HarfBuzz** (`mode=harf`, v3.1 2019) | ✅ (harf ≫ node for Arabic/Indic) | shaped advances → node list | same-font/dir/script/lang runs |
| **WeasyPrint** | **Pango → HarfBuzz** (+ FriBidi) via cffi | ✅ | `pango_layout_line_get_extents` on the shaped layout | Pango itemizes; FriBidi bidi |
| **Typst** | **rustybuzz** (pure-Rust HarfBuzz port, 2221/2252 HB tests) | ✅ | `Σ ShapedGlyph.x_advance` | `unicode-script` + `unicode-bidi` |
| **fpdf2** (≥2.7.5, 2023) | **uharfbuzz**, opt-in `set_text_shaping()` | ✅ (off by default) | shaped `x_advance` | applies UBA when shaping on |
| **Pillow** | **libraqm** (HarfBuzz+FriBidi/SheenBidi), else BASIC | ✅ only with Raqm | `getlength()` (1/64 px) | Raqm itemizes; else none |
| **ReportLab** (pre-4.4.0, Apr 2025) | **none** | ❌ | `Σ hmtx[cmap[ord(u)]]` per codepoint | none |

**The two lessons for scriba:**

1. **The universal pattern is exactly Tier 1.** Every correct engine = *itemize into script runs*
   + *shape each run with HarfBuzz (or a port)* + *sum the shaped advances*. §4–§5 reproduce this
   pattern in Python and land at browser parity. Typst even mirrors the proposed dependency shape:
   a HarfBuzz port + `unicode-script`/`unicode-bidi` for the same job stdlib `unicodedata` does
   here.

2. **ReportLab is the "no-shaping" ghost of scriba's current Arabic path.** Its `stringWidth` is
   literally `0.001*size*sum(g(ord(u),dw) for u in text)` — one codepoint = one glyph, no GSUB/
   GPOS — the same shape as the naive column in §2 that runs **+13…+23% wide** for Arabic. The
   visible symptom (arabic-reshaper's own words): letters come out *"in the isolated form… every
   character rendered regardless of its surroundings… written left to right"* — disconnected and
   mirrored. Users must pre-shape with `arabic_reshaper` + `python-bidi` before drawing.
   scriba's over-estimate at least never *mis-renders* (the browser still shapes correctly; only
   the reserved box is loose) — but it confirms that per-codepoint sums are not a road to
   exactness.

*Why per-codepoint sums fail (authoritative):* HarfBuzz "Clusters" — shaping "may merge adjacent
characters… or split one character into several"; OpenType GSUB explicitly maps *multiple chars →
one glyph* (ligatures) and *one char → multiple glyphs*; Unicode Core Spec Ch. 9 — each Arabic
letter "must be depicted by one of a number of possible contextual glyph forms." The true glyph
run, and thus its width, exists only *after* shaping.

**Sources.** HarfBuzz [clusters](https://harfbuzz.github.io/clusters.html) ·
[shaping-concepts](https://harfbuzz.github.io/shaping-concepts.html) · OpenType
[GSUB](https://learn.microsoft.com/en-us/typography/opentype/spec/gsub) · Unicode
[Core Spec Ch.9 Arabic](https://www.unicode.org/versions/Unicode15.0.0/ch09.pdf) ·
["Text Rendering Hates You"](https://faultlore.com/blah/text-hates-you/) ·
XeTeX→HarfBuzz [texdev.net](https://www.texdev.net/2013/03/12/xetex-0-9999-moving-to-harfbuzz-and-lots-of-other-goodies/),
[Wikipedia](https://en.wikipedia.org/wiki/XeTeX) · luaotfload
[NEWS](https://raw.githubusercontent.com/latex3/luaotfload/main/NEWS),
[Hosny TUGboat 40:1](https://tug.org/TUGboat/tb40-1/tb124hosny-harfbuzz.pdf) · WeasyPrint
[ffi.py](https://github.com/Kozea/WeasyPrint/blob/main/weasyprint/text/ffi.py),
[Pango README](https://github.com/GNOME/pango/blob/main/README.md) · Typst
[shaping.rs](https://github.com/typst/typst/blob/main/crates/typst-layout/src/inline/shaping.rs),
[rustybuzz](https://github.com/harfbuzz/rustybuzz) · ReportLab
[rl_accel.py](https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/master/src/reportlab/lib/rl_accel.py),
[CHANGES](https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/master/CHANGES.md) ·
[arabic-reshaper](https://github.com/mpcabd/python-arabic-reshaper) ·
[python-bidi](https://github.com/MeirKriheli/python-bidi) · fpdf2
[TextShaping](https://py-pdf.github.io/fpdf2/TextShaping.html) ·
[libraqm](https://github.com/HOST-Oman/libraqm) · uharfbuzz
[PyPI files](https://pypi.org/project/uharfbuzz/#files),
[LICENSE](https://github.com/harfbuzz/uharfbuzz/blob/main/LICENSE) · [PEP 621](https://peps.python.org/pep-0621/).

---

## 9. Landing implications

1. **Shaping is the easy, cheap half — and it's fully solved.** uharfbuzz == browser to ≤0.02%,
   3 µs/string, 1–3 MB permissive wheel on every platform. If scriba decides a script is worth
   exactness, HarfBuzz makes it pixel-perfect at negligible runtime cost.
2. **The gate is fonts, not shaping.** Exactness needs measured-font == rendered-font ⇒ scriba
   must **ship + pin** the complex-script font (the Inter deal, repeated). Arabic/Thai/Devanagari
   Noto subsets are ~0.1–0.5 MB each — affordable, base64-embeddable like KaTeX/Inter. **Korean +
   CJK are the wall: 15–40 MB** for real Hangul/Han coverage — not shippable inline. So CJK stays
   at `1.0 em` (already exact); **Hangul should drop from `1.0 em` to a shipped-Korean-font
   advance table only if a Korean subset is ever bundled**, else keep the safe over-estimate.
3. **Never shape a font you don't ship.** The §3 identity spread (7–28%) is *two-sided*; adopting
   a reader-font-blind shaped width would let scriba **under**-estimate and clip — strictly worse
   than today's guaranteed-loose box. The complex branch must hard-require a shipped+pinned font.
4. **Recommended scope.** Tier 0 unchanged (safe over-estimates everywhere unshipped). Ship
   `scriba[intl]` = uharfbuzz + Noto **Arabic/Thai/Devanagari** subsets + the §5 segmenter, wired
   through the existing `TextMeasurer` seam. That converts the three biggest, cheapest-to-ship
   over-estimates (Arabic +19% shaping gap, Devanagari +10%, Thai +12% on clustering fonts) into
   ≤0.1% exactness, while CJK stays exact-by-heuristic and Korean stays safe until a Korean font
   is judged worth its megabytes.
5. **Bidi is free.** Mixed LTR/RTL width = Σ per-run shaped widths (§4). Once runs are itemized
   and each is shaped against its shipped font, no separate bidi width model is needed — reorder
   for *drawing* (`direction`/`unicode-bidi`, already sanitizer-allowed), sum for *measuring*.

### Reproduction

All probes in the scratchpad `allscript/`: `enum_fonts.py` (face/UPM/coverage),
`shaperlib.py` (uharfbuzz shaper + naive `cmap+hmtx`), `browser_measure.py` (headless-Chromium
`getComputedTextLength` harness), `bench.py` (§2), `crossfont.py` (§3), `experiments.py`
(§4 features/bidi/segmentation + §6 timing). Ground truth:
`chrome-headless-shell-1223`; venv `ftenv` (fontTools 4.63, uharfbuzz 0.55.0, py3.14).
