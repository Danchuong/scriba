# Prior Art: Exact Text-Width Measurement in Browserless SVG Generation

> **STATUS: LANDED (informed v1) 2026-07-03** — shipped-font + baked-advance-table strategy implemented in 0cd523b; textLength remains the designed safety-net follow-up.

> Research brief for **scriba** (`scriba-tex`) — a pure-Python LaTeX→static-HTML/SVG renderer with
> self-contained output and zero JS-runtime layout dependencies. **This is a survey/design document
> only. No source code was modified.**

---

## Hand-off Brief

**The question.** scriba measures every geometric quantity exactly, but the *last estimated quantity* is
**text width**. Caption/label widths come from `estimate_text_width()`
(`scriba/animation/primitives/_text_render.py`), a pure-`unicodedata` per-character heuristic
(Latin `0.62 × font`, CJK Wide/Fullwidth `1.0 em`, combining marks `0.0`, ZWJ clusters `1.0 em`) plus an
`8 px` `_CAPTION_SAFETY_PAD` (`scriba/animation/primitives/base.py:196`). `layout.py` states the design
intent outright: *"Scriba does not measure the real browser-rendered font."* The goal is to learn how
serious projects get **exact (or near-exact) text width without a browser at render time.**

**The one fact that reframes everything.** There are two independent notions of "exact":

1. **Exact against the font file you measured** — trivial and cheap: sum per-glyph advance widths from the
   font's own metrics table (`hmtx` / AFM `WX` / TeX `.tfm`). Every serious system does this.
2. **Exact against what the *viewer* actually renders** — only holds if the viewer renders the *same font
   you measured*. This requires either **(a) shipping/embedding that exact font**, or **(b) converting glyphs
   to `<path>` outlines** so no viewer font is consulted at all.

**scriba is currently exposed on axis 2.** The KaTeX *math* fonts are base64-inlined into the CSS
(`scriba/core/css_bundler.py`, ~260 KB of woff2 across 20 files, `KaTeX_Main-Regular` = 26 KB), so inline
math is rendered in a shipped font. **But plain caption/label `<text>` is drawn in the viewer's *system*
sans-serif** (`scriba-standalone.css`: `font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
sans-serif`). So the text scriba estimates is rendered in whatever font the viewer substitutes — meaning
*no* measurement, however exact against a reference font, can be exact against the render unless scriba
also pins/ships that font or emits `textLength`. This is the same failure mode Graphviz documents.

**What the field does.** Three architectural families recur:

- **A. Heuristic average-width tables** — cheap, approximate, zero font files (Graphviz's built-in
  fallback; npm `string-width`; shields.io's precomputed Verdana table). This is essentially what scriba
  does today, but scriba's table is a *single* 0.62 average rather than per-glyph.
- **B. Real font metrics → emit `<text>` + `font-family`** — exact at build, **breaks if the viewer's font
  differs** (Graphviz plain `-Tsvg`, mermaid SVG). Mitigation is always *embed the font* or *outline*.
- **C. Real metrics/shaping → convert to `<path>` outlines** — exact **and** font-independent; the viewer
  sees exactly what was measured (matplotlib default `svg.fonttype:path`, Typst, resvg/usvg, Satori). Cost:
  text is no longer selectable / searchable / screen-reader accessible, and files grow.

**The cheap escape hatch.** SVG `textLength` + `lengthAdjust` lets you *declare the box width and force the
real text to fit it* — "lie but never overflow." Zero dependencies (it is an attribute string), keeps text
real/accessible, Baseline since July 2015, and is exactly what PlantUML and shields.io emit. It converts
scriba's estimate from "must be right or text overflows" into "an accuracy hint the browser absorbs."

**scriba-specific bottom line.** Keep the pure-Python estimator, but (1) emit `textLength` as a
zero-dependency no-overflow backstop *now*; (2) for exactness, ship one subsetted **Latin+Vietnamese**
woff2 (~10–45 KB — proportionate to the ~260 KB already inlined), pin it as the caption font, and bake a
per-codepoint advance table from it **at build time with fontTools** so the *runtime* stays pure-stdlib;
(3) reserve `uharfbuzz` (build-time only) for shaping-exact numbers if kerning/decomposed Vietnamese ever
matters. Details and ranking at the end.

---

## Survey Table

| System | Mechanism (how width is obtained) | Exact? | Deps | Font shipped? (viewer sees what was measured?) | Fit for scriba |
|---|---|---|---|---|---|
| **matplotlib** (`svg.fonttype:path`, default; PNG; PDF) | FreeType glyph advances at save-time → glyphs emitted as `<path>` | **Exact** (both axes) | Heavy: FreeType (C), optional HarfBuzz/libraqm | **Yes** — outlines embedded; viewer-independent | Model to copy (path route); impl needs C |
| **matplotlib** (`svg.fonttype:none`) | Same FreeType measure, but emits `<text>`+font-family | Heuristic at viewer | same | **No** — depends on viewer fonts | Anti-pattern (scriba's current exposure) |
| **matplotlib** AFM (PS/PDF, `ps.useafm`) | Sum `.afm` `WX` advances (1000-unit em), **pure-Python parser** | Exact for the 14 core PS fonts | **Light — pure data** | Assumes core fonts present | Great *template* for pure-Python metric tables |
| **Typst** (SVG export) | rustybuzz shaping → advances; ttf-parser `outline_glyph` → `<path>` | **Exact** | Medium: Rust crates, no C | **Yes** — glyphs pathed "so SVG looks the same across all devices" | Architectural blueprint; loses text selectability |
| **TeX / LaTeX** | `.tfm` char widths (fix_word, design-size units); layout without rasterizing | **Exact** | **Featherweight — static data files** | Assumes exact font+metrics shipped | The canonical "measure from a tiny table" proof |
| **Graphviz** (real path: pango/cairo) | Pango→HarfBuzz→FreeType real advances; fontconfig resolves font | Exact at build | Heavy (C: pango, cairo, fontconfig, freetype) | Plain `-Tsvg`: **No**; `-Tsvg:cairo`: **Yes** (embeds font) | Documents the exact "measure-font ≠ render-font" bug scriba risks |
| **Graphviz** (fallback: `estimate_text_width_1pt`) | Hardcoded per-font **ASCII advance tables** ÷ units_per_em | Heuristic (ASCII only) | **Zero** | N/A (build-time only) | Portable idea: per-glyph tables beat a single 0.62 average |
| **resvg / usvg + fontdb + rustybuzz** | fontdb resolves fonts deterministically; rustybuzz shapes; `Text::flattened()` → paths | **Exact** | Medium: pure Rust | **Yes** (raster), given pinned fonts | Reference C-strategy; Python analog = fontTools+uharfbuzz |
| **Mermaid-cli / mermaid.ink** | Real headless **Chromium** (`getBBox`/`getComputedTextLength`) | Exact | **Very heavy** (Chromium) | SVG keeps `<text>` (viewer-dependent) unless rasterized | The approach scriba explicitly avoids |
| **npm `string-width`** | East-Asian-Width monospace **cell** counting | Terminal-only heuristic | Zero | N/A | Only a CJK cell heuristic; not pixel width |
| **opentype.js / text-to-svg** | Pure-JS parse; `getAdvanceWidth()`; text→`<path>` | Near-exact (advances; no complex shaping) | Light (pure JS) | **Yes** (paths) | Direct JS twin of the fontTools approach |
| **Vercel Satori** | opentype.js `getAdvanceWidth` (incl. kerning) + Yoga layout; default text→`<path>` | Near-exact | Medium (WASM Yoga) | **Yes** by default (`embedFont`) | The modern analog of what scriba could build in Python |
| **shields.io / badgen (`anafanafo`)** | **Precomputed Verdana/Helvetica width table** (built offline via Puppeteer) + `textLength` | Near-exact for that font | **Zero at runtime** | **No** (system `<text>`) → forced to fit via `textLength` | Closest working analog to scriba's constraints |
| **Python `fontTools`** | Read `hmtx` advances ÷ `unitsPerEm` × size; parse `kern`/GPOS | Exact (advance sum); near-exact w/ kerning | **Pure Python** | Whatever you emit | **Best pure-Python fit** |
| **Python `uharfbuzz`** | Real HarfBuzz `hb.shape()`; sum `x_advance` | **Browser-exact, all scripts** | Native `abi3` wheel (~1–3 MB) | Whatever you emit | Optional build-time accuracy ceiling |
| **Python `Pillow.getlength`** | FreeType `getlength()`; complex shaping needs libraqm | Exact (basic); shaping gated on Raqm | Heavy binary wheel | Whatever you emit | Overkill unless already a dep |
| **Pango / PyGObject** | Full GTK text engine | Exact | **System libs (not pip-shippable)** | Whatever you emit | Reject for a self-contained lib |
| **SVG `textLength`+`lengthAdjust`** | Declare box width; UA fits real text to it | Width-exact, glyph-approx | **Zero (attribute string)** | Width yes; glyphs viewer-dependent | **Killer cheap backstop** |
| **CSS `font-size-adjust`** | Normalize x-height of fallback font | Reduces (not removes) fallback error | Zero (CSS) | Approximate | Only if staying on system `<text>` |
| **SVG2 `inline-size`** | Auto-wrapping text region | N/A (wrapping, not width) | Zero (CSS) | — | Chromium-only; avoid |

---

## Deep Notes per System

### 1. matplotlib — FreeType at save-time, AFM as the pure-data fallback

**Mechanism.** matplotlib measures text from **FreeType** glyph metrics at render/save time. In
`RendererAgg.get_text_width_height_descent` it calls `font.set_text(...)` then `font.get_width_height()`,
dividing by `64.0` because FreeType returns 26.6 fixed-point subpixels; `textpath.TextToPath` mirrors this
for vector backends and reads each glyph's advanced position from `_text_helpers.layout()` (HarfBuzz/libraqm
when present). It deliberately measures **advance width**, not the ink bounding box.

**SVG backend — the decisive knob is `svg.fonttype`** (default `'path'`), a single branch in
`RendererSVG.draw_text`:

- `'path'` — *"compute the path of the glyphs … so that the SVG will look the same on all computers
  independent of what fonts are installed. However, the text will not be editable."* **Exact + viewer-independent.**
- `'none'` — *"smaller files and the text will appear directly in the markup. However, the appearance may
  vary based on the SVG viewer and what fonts are available."* This is **strategy B** (system `<text>`).
- `'svgfont'` — embed SVG `<font>` defs; effectively dead (Chrome/Safari/Opera only).

**AFM fallback** (PS/PDF backend with `ps.useafm`, restricted to the 14 PostScript core fonts): matplotlib
measures from **Adobe Font Metrics** files — *"all that is supplied … are font metrics (specified in AFM
format), and it is the job of the viewer applications to supply the glyph definitions."* An `.afm` stores,
per glyph, `WX` (advance) in a **1000-unit em**, plus `KPX` kerning pairs; `AFM.get_str_bbox_and_descent`
sums `wx + kern`. **This is a pure-data, pure-Python metric path** — the closest existing analog to what
scriba should build for a bundled font.

- Exactness: exact (`path`/PNG/PDF and AFM-for-core-fonts). Deps: heavy default (FreeType C), light AFM.
  Viewer fidelity: exact only when glyphs are pathed/embedded. Pure-Python fit: the *AFM model* and the
  *`path` model* are both directly portable ideas; the default C machinery is not.

Sources: <https://matplotlib.org/stable/users/explain/text/fonts.html> ·
`backend_agg.py`, `textpath.py`, `backend_svg.py`, `_afm.py` in
<https://github.com/matplotlib/matplotlib> · advance-vs-ink: <https://github.com/matplotlib/matplotlib/issues/253>

### 2. Typst — shape with rustybuzz, embed glyph outlines as `<path>`

Typst wraps **`rustybuzz`** (pure-Rust HarfBuzz port) for shaping and **`ttf-parser`** for metrics/outlines.
SVG export routes normal glyphs through `text.font.ttf().outline_glyph(glyph_id, builder)` → `<path>`,
deduped into `<symbol>`/`<use>`, scaled by `size / units_per_em`. The docs state the intent verbatim:
*"To ensure that the SVG file looks the same across all devices it is viewed on, Typst chooses [embedding
glyph shapes]"* — with the explicit tradeoff that *"the text … cannot be extracted automatically, for
example by copy/paste or a screen reader."* Fonts resolve deterministically via an embedded font book →
system fonts → `FontBook` similarity scoring.

- Exactness: exact. Deps: Rust crates (no C, but not pure-Python). Viewer fidelity: exact (outlines);
  loses selectable text. Pure-Python fit: **this is the architectural blueprint** — measure from advances,
  emit outlines — replicable in Python for Latin/Vietnamese with fontTools; only complex-script shaping
  needs a real shaper.

Sources: <https://typst.app/docs/reference/svg/> ·
`crates/typst-svg/src/text.rs` <https://github.com/typst/typst/blob/main/crates/typst-svg/src/text.rs> ·
open request for real-text export <https://github.com/typst/typst/issues/4702>

### 3. TeX / LaTeX — the 40-year-old answer: TFM metrics, no rasterization

A **`.tfm` (TeX Font Metrics)** file is a compact **metrics-only** table: per-character width/height/depth/
italic-correction (stored as indices into shared tables for dedup — a whole Computer Modern TFM is < 2 KB),
a `lig_kern` program (ligatures + kerning), an `exten` table (extensible delimiters), and font-wide `param`
values. All numbers are **`fix_word`** — fixed-point multiples of the font's **design size**, so metrics are
resolution- and scale-independent; TeX multiplies by the point size at use.

**The crux the field keeps rediscovering:** TeX does *all* line-breaking and box/glue arithmetic **purely
from TFM numbers without ever rasterizing a glyph** — *"TeX … themselves need only know about the sizes of
characters and their interactions with each other, but not what characters look like."* It emits
device-independent **DVI**; the actual glyph program (PK/Type1/OTF) is consulted only later by the driver.
Because the metrics are a fixed data file and the arithmetic is exact fixed-point, the **same source yields
byte-identical line breaks on every machine** — the strongest determinism guarantee of any system here, and
it predates them all. Modern engines generalize without changing the principle: LuaTeX + `luaotfload` read
OpenType metrics directly (and drive HarfBuzz in `harf` mode for positioned glyph advances); `unicode-math`
reads the OpenType `MATH` table directly from the OTF.

- Exactness: exact. Deps: **featherweight — pure static data**; a TFM reader is trivial arithmetic (fontTools
  even ships a pure-Python `tfmLib`). Pure-Python fit: **proof that perfect layout comes from a tiny
  pure-data metric table.** The modern equivalent is reading a font's own `hmtx` advances rather than a
  separate `.tfm`.

Sources: <https://en.wikipedia.org/wiki/TeX_font_metric> · <https://texfaq.org/FAQ-tfm> ·
<https://fonttools.readthedocs.io/en/latest/tfmLib.html> · HarfBuzz-in-LuaTeX:
<https://tug.org/TUGboat/tb40-1/tb124hosny-harfbuzz.pdf>

### 4. Graphviz — the textbook "measure-font ≠ render-font" cautionary tale

Graphviz dispatches in `textspan_size()`: try the real text-layout plugin, else
`estimate_textspan_size()`. The **fallback** (`estimate_text_width_1pt` on `main`, formerly inline
`timesFontWidth[]`/`arialFontWidth[]`/`courFontWidth[]` tables) sums **hardcoded per-font ASCII advance
tables** and divides by `units_per_em` (e.g., Times: space=512, 'A'=1479, 'a'=909 at UPM 2048; Courier
uniform 1229). ASCII-only, no kerning. The **real path** (`plugin/pango/gvtextlayout_pango.c`) uses
Pango→HarfBuzz→FreeType for true extents, with fontconfig resolving the family to a concrete file.

**The failure mode, confirmed by the maintainer:** *"graphviz might run on a computer with a font, and
another computer might show the SVG without the font, and have to fall back to another font. Then the
originally-computed text size is wrong."* Plain `-Tsvg` emits `<text font-family=…>` with the raw string
(no paths), so viewer substitution breaks the fit. Graphviz's own mitigation is `-Tsvg:cairo`, which
**embeds the font** in the SVG.

- Takeaways for scriba: (i) a *per-glyph* table (even ASCII) is strictly better than a single 0.62 average;
  (ii) if you keep system `<text>`, you inherit exactly this bug unless you embed the font or emit
  `textLength`.

Sources: `textspan.c` / `textspan_lut.c`
<https://gitlab.com/graphviz/graphviz/-/blob/main/lib/common/textspan_lut.c> ·
maintainer on font mismatch
<https://forum.graphviz.org/t/how-does-graphviz-calculate-the-length-and-width-of-the-text/1301> ·
font FAQ <https://graphviz.org/faq/font/>

### 5. resvg / usvg + fontdb + rustybuzz — deterministic browserless outlining

resvg advertises *"No native text rendering."* `fontdb` (in-memory font DB with CSS-like queries) resolves
families deterministically from **explicitly loaded font files** (or `load_system_fonts()`); `rustybuzz`
shapes (kerning, ligatures, marks, complex scripts); `ttf-parser` supplies advances + outlines.
`usvg::Text::flattened()` returns *"Text converted into paths, ready to render"*, and `bounding_box()`
gives measured extents — so text is shaped and outlined **at parse time**, and the rasterized pixels are
exactly what was measured, independent of any viewer font. Determinism holds **only if the same font files
are present** (missing font → substitution → different result); i.e., pin/ship the fonts.
`@resvg/resvg-js` is the Node/WASM binding with `fontFiles`/`fontBuffers`/`loadSystemFonts`.

- Pure-Python analog: `fontTools` (ttf-parser role) + `uharfbuzz` (rustybuzz role), then emit `<path>`.

Sources: <https://github.com/linebender/resvg> · `Text::flattened()`
<https://docs.rs/usvg/latest/usvg/struct.Text.html> · <https://github.com/yisibl/resvg-js>

### 6. Mermaid / D3 server-side rendering — three sub-strategies

- **mermaid-cli / mermaid.ink**: launch **real headless Chromium via Puppeteer** and run mermaid.js in the
  page, using `SVGTextElement.getBBox()` / `getComputedTextLength()` — which *"is not implemented (and not
  easily implemented) in JSDOM"*, hence a real browser is required. Exact but **very heavy**; output SVG
  keeps `<text>` (viewer-dependent) unless rasterized. **The approach scriba is built to avoid.**
- **npm `string-width`**: counts monospace **terminal cells** via East-Asian-Width (wide=2, zero-width=0),
  strips ANSI. No proportional-pixel concept — a CJK cell heuristic only. (Notably scriba's own estimator
  is *more* pixel-aware than this.)
- **opentype.js / text-to-svg**: pure-JS font parsing; `Font.getAdvanceWidth(text, size)` *"corresponds to
  `canvas2dContext.measureText(text).width`"*; `getPath()`/`getD()` emit `<path>`. Font-independent, no
  native deps, supports kerning + letter-spacing. **The direct JS twin of the fontTools approach.**
- **Vercel Satori**: caller supplies font data (TTF/OTF/WOFF, **not woff2**); parses with a fork of
  opentype.js; `measureText` sums `getAdvanceWidth` (*"includes kerning"*); lays out with **Yoga** (WASM
  Flexbox); **defaults to rendering text as `<path>`** (`embedFont`) so downstream needs no fonts.
  Limitation: *"kerning, ligatures and other OpenType features are not currently supported"* → near-exact
  for Latin, imperfect for complex scripts. Typical stack: Satori (pathed SVG) → `@resvg/resvg-js` (PNG).

Sources: mermaid pipeline <https://deepwiki.com/mermaid-js/mermaid-cli/3.2-rendering-pipeline> ·
`string-width` <https://github.com/sindresorhus/string-width> ·
opentype.js <https://github.com/opentypejs/opentype.js> · text-to-svg
<https://github.com/shrhdk/text-to-svg> · Satori <https://github.com/vercel/satori> and
<https://deepwiki.com/vercel/satori/3.3-text-and-fonts>

### 7. Python options — hands-on viability for a zero-native-runtime-dep library

> scriba's venv currently has **no** fontTools, brotli, uharfbuzz, or Pillow — the only runtime dep is
> `pygments`. So fontTools is **not** already a transitive dependency here (it *is* for matplotlib/weasyprint
> users, but scriba doesn't pull those). Any of these is a *new* dependency decision.

**fontTools (`fontTools.ttLib`) — pure Python. Rank #1.**
```python
from fontTools.ttLib import TTFont
font = TTFont("Caption.ttf")            # .ttf/.otf: pure stdlib; .woff2 needs `brotli` (native)
upm  = font["head"].unitsPerEm
cmap = font.getBestCmap()               # codepoint -> glyph name
hmtx = font["hmtx"].metrics             # glyph name -> (advanceWidth, lsb)
adv_px = lambda ch, size: hmtx[cmap[ord(ch)]][0] / upm * size
width = sum(adv_px(c, 16) for c in "Việt Hello")
```
- **Pure Python** — *"no (required) external dependencies besides the modules included in the Python
  Standard Library."* All native pieces (`brotli` for woff2, `lxml`, `cu2qu`) are optional extras
  irrelevant to reading `head`/`cmap`/`hmtx`. Force pure with `pip install --no-binary=fonttools fonttools`.
- **Exactness:** exact for the advance-sum model (matches a browser with kerning off). It **parses** `kern`
  and GPOS but is **not a shaper** — it does not apply GPOS pair-kerning, GSUB ligatures, or mark
  positioning for you; you'd implement kerning lookups if needed (sub-pixel to ~1 px per pair at label
  sizes, usually negligible).
- **CJK:** exact (each ideograph = one glyph with its stored advance). **Vietnamese:** exact for
  **precomposed / NFC** (e.g. `ế` U+1EBF is one codepoint → one advance — the common web case); for
  **decomposed / NFD**, combining marks are zero-advance so the naive sum is *still* correct for width (only
  their *placement* is shaping fontTools won't do). scriba already treats combining marks as `0.0`, which is
  consistent with this.

Sources: <https://pypi.org/project/fonttools/> ·
<https://fonttools.readthedocs.io/en/latest/ttLib/ttFont.html> ·
hmtx <https://fonttools.readthedocs.io/en/latest/ttLib/tables/_h_m_t_x.html>

**uharfbuzz — HarfBuzz binding (C++). Rank #2 (build-time accuracy ceiling).**
```python
import uharfbuzz as hb
face = hb.Face(hb.Blob.from_file_path("Caption.ttf")); font = hb.Font(face)
buf = hb.Buffer(); buf.add_str("Việt"); buf.guess_segment_properties()
hb.shape(font, buf, {"kern": True, "liga": True})
width_units = sum(p.x_advance for p in buf.glyph_positions)
```
- **Browser-identical for every script** — HarfBuzz *is* the shaper in Chrome, Firefox, Edge, Android,
  LibreOffice, XeTeX, Figma, etc. Correct kerning, ligatures, and Vietnamese mark positioning (NFC *and*
  NFD).
- **Native `abi3` wheel (~1–3 MB)** bundling HarfBuzz — no system libs, broad wheel coverage (Win/mac
  universal2/manylinux/musllinux), one wheel for CPython 3.10+. Pip-installable, but **not pure-Python** →
  violates the "zero native runtime dep" rule if shipped. **Ideal as a build-time-only tool** to generate a
  width table that ships as pure data.

Sources: <https://pypi.org/project/uharfbuzz/> · <https://github.com/harfbuzz/uharfbuzz>

**Pillow `ImageFont.getlength()` — FreeType. Rank #3.** Exact basic advances (1/64 px), but complex
shaping needs **libraqm** (HarfBuzz+FriBidi+fontconfig), which is *not* reliably bundled in wheels. Heavy
binary for a text-metrics-only need; only justified if Pillow is already a dependency (it isn't for scriba).
Source: <https://pillow.readthedocs.io/en/stable/reference/ImageFont.html>

**Pango / PyGObject — reject.** Extremely accurate, but requires **system libraries installed before pip
runs** (GObject-Introspection, cairo, Pango, HarfBuzz, fontconfig, pkg-config). *Not self-contained through
pip alone* → incompatible with a self-contained pip library. Source:
<https://pygobject.gnome.org/getting_started.html>

**Lightest exact path for a KNOWN shipped font:** do the heavy work **offline once** and ship pure data.
Load the bundled font with fontTools (or uharfbuzz for shaping-exact numbers), iterate your supported
codepoints, and emit a `codepoint → advanceWidth` table (+ `unitsPerEm`, + any kerning pairs you care
about). At runtime, width = `adv_units / upm * size` with **zero third-party deps** — this is the AFM/TFM
model, and it keeps scriba's runtime pure-stdlib. **Avoid putting `brotli` on the runtime path** by
decompressing woff2→ttf once at build time (WOFF 1.0 uses stdlib zlib; only WOFF2 needs Brotli).

---

## The `textLength` Escape Hatch — Analysis

**What it is.** `textLength` on `<text>`/`<tspan>`/`<textPath>` declares the width the text must occupy;
*"the user agent will ensure that the text does not extend farther than that distance."* `lengthAdjust`
chooses how:

- **`spacing`** (default) — *"only the advance values are adjusted. The glyphs themselves are not stretched
  or compressed."* Changes inter-glyph tracking only.
- **`spacingAndGlyphs`** — *"the advance values are adjusted and the glyphs themselves stretched or
  compressed"* along the inline axis.

MDN's money quote: *"you can ensure that your SVG text displays at the same width regardless of conditions
including web fonts failing to load."* Baseline (widely available) since **July 2015**.

**Why this is compelling for scriba.** It directly neutralizes scriba's one exposure. Today, if the
viewer's system sans-serif is wider than the 0.62 estimate, caption text can overflow its box (the `8 px`
pad is the only cushion). Note scriba already scales the whole `<svg>` viewport by
`--scriba-diagram-font-scale` so text and geometry scale *together* (text never overflows shapes *at any
scale*) — the residual risk is purely the base estimate vs. the actual rendered font. Emitting
`textLength = estimated_width` makes the browser **fit the real glyphs to scriba's declared box**, turning
the estimator from a correctness requirement into an accuracy hint. Zero dependencies — it is an f-string
attribute. Text stays real: **selectable, searchable, screen-reader accessible** (unlike the `<path>`
outlining route). This is precisely how **PlantUML** and **shields.io** guarantee stable label widths
without a browser.

**Quality tradeoffs / when it distorts.**

- The interior is not deterministic — SVG 1.1 warns *"the locations of intermediate glyphs are not
  predictable because user agents might employ advanced algorithms."*
- `spacingAndGlyphs`: if the estimate is far from the true width, glyphs visibly **stretch** (estimate too
  wide) or **squish** (too narrow). Avoid unless the estimate is trusted.
- `spacing`: **loose gaps** (estimate too wide) or **crowding/overlap** (too narrow). Legibility, never
  overflow.
- **CJK is the worst case:** `spacing` inserts uneven gaps between normally uniform full-width ideographs;
  `spacingAndGlyphs` distorts their square proportions. Both read as broken. (Mitigation: for CJK runs,
  scriba's `1.0 em` estimate is already accurate, so keep `textLength` off or set it exactly.)
- **Vietnamese diacritic stacks:** marks ride the base glyph's advance, so `spacing` (which mostly changes
  inter-cluster gaps) is comparatively safe; `spacingAndGlyphs` would distort the base. A real report on
  RTL/**Persian** shows `textLength` can even break shaping (different glyph selection) in some viewers
  (Inkscape) though Chrome/Firefox cope — so scope it to Latin/Vietnamese/CJK, not complex scripts.

**Recommendation:** emit `textLength` with **`lengthAdjust="spacing"`** (never `spacingAndGlyphs` unless the
width is trusted). Because scriba's estimator is conservative, the adjustment stays near-imperceptible while
guaranteeing no overflow.

**Adjacent attributes.**
- **`font-size-adjust`** (CSS): normalizes a fallback font's x-height toward the intended font's aspect
  ratio, **reducing but not removing** the measured-vs-rendered error — relevant *only* if scriba stays on
  system `<text>`. Baseline "newly available" since **July 2024** (so not safe for old viewers). Pair with
  `textLength` if you keep system fonts. Source:
  <https://developer.mozilla.org/en-US/docs/Web/CSS/font-size-adjust>
- **`inline-size`** (SVG2 auto-wrap): **Chromium-only**, not in Firefox/Safari — avoid; keep explicit
  `<tspan>` breaks.

Sources: <https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/textLength> · SVG 1.1 text
<https://www.w3.org/TR/SVG11/text.html> · PlantUML real usage + failure mode
<https://forum.plantuml.net/17007/how-we-can-disable-textlength-at-svg-generation> · shields.io context
<https://github.com/metabolize/anafanafo>

---

## Ranked Shortlist — 3 Viable Strategies for scriba

Constraints that drive the ranking: **self-contained output**, **Vietnamese-heavy text**, **KaTeX fonts
already embedded but caption text on system fonts**, **pure-Python / zero-native-runtime-dep ethos**,
**accessible/selectable text is desirable**.

### #1 — Emit `textLength` (+ `lengthAdjust="spacing"`) on generated `<text>`. *Do this first.*
**Rationale.** Highest ROI by far: **zero dependencies**, a few lines in `_render_svg_text`, and it *directly
fixes the actual risk* — overflow when the viewer's system font is wider than the 0.62 estimate. Keep the
existing `estimate_text_width()` as the width source; feed that number as `textLength` so the browser
force-fits the real text into scriba's declared box. Text stays real and accessible. Proven at
billions-of-badges scale (shields.io) and by PlantUML. The `8 px` safety pad can be retired from its
"prevent overflow" duty and kept only as cosmetic breathing room.
**Caveats.** Use `spacing`, not `spacingAndGlyphs`. For CJK, prefer setting `textLength` exactly (the `1.0
em` estimate is already accurate) to avoid uneven ideograph gaps; consider omitting it for pure-CJK lines.
**Net:** near-zero cost, removes the overflow failure mode immediately. Does *not* by itself make the
estimate more accurate — it makes inaccuracy harmless.

### #2 — Ship one subsetted **Latin+Vietnamese** woff2, pin it as the caption font, and bake a per-codepoint advance table from it **at build time with fontTools**.
**Rationale.** This is the TeX/AFM/Satori model adapted to scriba, and it makes **text a *measured* quantity
like everything else geometric.** scriba *already* base64-inlines ~260 KB of KaTeX woff2, so adding one
caption font is philosophically consistent and proportionate: a Latin+Vietnamese subset of an OFL sans
(Inter/Roboto/Noto Sans) is ~**10 KB (Vietnamese-only) to ~40–45 KB (Latin+Vietnamese)** woff2 via
`pyftsubset --unicodes=...` (the Google-Fonts `vietnamese` range is `U+0102-0103, U+0110-0111, U+0128-0129,
U+0168-0169, U+01A0-01A1, U+01AF-01B0, U+1EA0-1EF9, U+20AB` plus Latin). Pin it as the caption/label
`font-family` (with the current system stack as fallback) so **the viewer renders the exact font scriba
measured** — closing axis 2. Measure it **offline** with fontTools (`hmtx ÷ unitsPerEm × size`) and commit a
pure-data width table, so the **runtime stays pure-stdlib** (no fontTools/brotli shipped; decompress
woff2→ttf once at build). fontTools' advance-sum is **exact for NFC Vietnamese and CJK**, and combining
marks are zero-advance — consistent with scriba's existing `0.0` handling. Combine with #1 as a
belt-and-suspenders backstop for hinting/sub-pixel drift.
**Caveats.** New bundled asset + font licensing (choose OFL). CJK would need a much larger font — out of
scope; keep CJK on the estimator + `textLength`. Replaces the single-0.62 average with real per-glyph
widths — a real accuracy jump for Vietnamese caption text specifically.

### #3 — Optional build-time **uharfbuzz** pass for shaping-exact widths (accuracy ceiling), *or* `<path>` outlining for font-independent pixel fidelity.
**Rationale.** If fontTools' no-kerning / NFD-mark-positioning limitation ever matters (tight boxes, kerned
display text, decomposed input), generate the width table with **uharfbuzz** instead — browser-identical
numbers, all scripts, correct Vietnamese mark handling — used **only at build time** so it never ships to
end users and the runtime stays pure-Python. The heavier alternative is the **Typst/matplotlib-`path`**
route: outline caption glyphs to `<path>` for pixel-exact, fully font-independent rendering with no shipped
font needed at all. Rank this last because it **loses text selectability, searchability, and screen-reader
access** and inflates SVG size — a poor fit for scriba's accessible-caption goals — but it is the ultimate
"viewer sees exactly what was measured" guarantee if that ever outweighs accessibility.
**Caveats.** uharfbuzz = build-time tooling only (keep it out of runtime deps). Path-outlining = accessibility
regression; reserve for special cases.

**Suggested path:** ship **#1 now** (cheap, removes overflow), adopt **#2** when exact Vietnamese caption
widths are worth one bundled font, and hold **#3** in reserve as a build-time accuracy upgrade.

---

### Appendix — scriba internals referenced (read-only)

- `scriba/animation/primitives/_text_render.py:78` — `estimate_text_width()` (`unicodedata`; Latin `0.62`,
  CJK Wide/Fullwidth `1.0 em`, combining/format marks `0.0`, ZWJ cluster `1.0 em`; returns
  `int(total*font_size+0.5)`). *(Note: the brief cited "CJK ~2×"; the code uses `1.0 em` ≈ 1.6× the Latin
  0.62. The "1.15 Vietnamese factor" lives in `_svg_helpers.py` as a string-padding trick for graph
  **weight labels**, not in the base estimator, which counts diacritics as `0.0`.)*
- `scriba/animation/primitives/base.py:196` — `_CAPTION_SAFETY_PAD = 8` ("estimate_text_width under-counts; pad").
- `scriba/animation/primitives/layout.py:28-33,66-99` — vertical metrics from W3C CSS Inline Layout ascent/
  descent (`0.80`/`0.20 em`); explicit: *"Scriba does not measure the real browser-rendered font."*
- `scriba/core/css_bundler.py` — base64-inlines `KaTeX_*.woff2` as `data:font/woff2;base64,…`.
- `scriba/animation/static/scriba-standalone.css:15` — caption font stack `-apple-system, …, Roboto,
  sans-serif` (system fonts → the axis-2 exposure).
- `scriba/tex/vendor/katex/fonts/` — 20 woff2, ~260 KB total; `KaTeX_Main-Regular.woff2` = 26 KB.
