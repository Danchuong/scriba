# All-Script / RTL Render Audit — what breaks visually today

**Scope.** How scriba *renders* complex-script and RTL text today (width metrics
aside). Every finding below was produced by authoring `.tex` in the scratchpad,
rendering with `render.py`, and reading headless-Chromium screenshots. No repo
source was modified.

**Toolchain.** `.venv/bin/python render.py` (static filmstrip + interactive) →
Playwright `chrome-headless-shell-1223` @ `device_scale_factor` 2–4. Driver +
probes: `drive_allscript.py`, `zoom_bidi.py`, `narr_probe.py`, `svg_bidi_fix.py`
(all in the session scratchpad).

---

## 1. Hand-off Brief

The headline is good news with three sharp exceptions. **The browser does almost
all the hard work for scriba.** Complex-script *shaping* — Arabic joining, Thai
mark stacking, Devanagari conjuncts, Korean composition — is 100% correct
everywhere, because every surface ultimately emits a plain SVG `<text>`/`<tspan>`
(or an XHTML `foreignObject`) and lets the UA shape and bidi-reorder it. Two more
lucky saves compound this: (a) **every** text surface is emitted with
`text-anchor:middle`, which hides the fact that the SVG base direction is LTR
(centered RTL text doesn't *look* mis-aligned); and (b) a single-script run
(e.g. a pure-Arabic cell or a pure-Arabic wrapped pill) is reordered RTL
correctly by the UA even inside an LTR-base element. So single-script cells,
captions, VariableWatch columns, and Arabic/Devanagari/Korean pills all render
**correctly**.

What actually breaks:

1. **Thai/Lao/Khmer/CJK pill & caption wrap** — `_wrap_label_lines` splits on
   space/comma/`+`/`=` only. Spaceless scripts become one un-splittable token
   that renders as one absurdly wide line spilling far past the figure. It does
   **not** tear clusters (the over-long token is emitted whole), so this is
   *degraded overflow*, not *data-destroying corruption* — a real correction to
   the original hypothesis.
2. **Bidi in SVG text** — no `dir`/`unicode-bidi` is set on any SVG text. Pure
   runs survive, but an **RTL-first string with embedded Latin/number/parens**
   (e.g. `نتيجة (result) = 42`) mis-mirrors the parens and scrambles segment
   order. Proven, and proven fixable with a one-word style addition.
3. **Narration `dir="auto"` is applied to only 1 of 4 emit sites** — the
   interactive on-screen paragraph is bidi-correct, but static-mode and
   print/PDF copies are not, so RTL-first narration degrades there.

Plus one **adjacent parser blocker** (not a render bug, but it stops the
VariableWatch *value* surface cold for two scripts): the selector tokenizer
rejects combining marks, so `\apply{v.var[ค่า]}` / `[खोज]` fail to parse.

---

## 2. Findings matrix (surface × script → grade)

Grades: **WORKS** (UA saves us) / **DEGRADED** (readable but wrong-ish) /
**BROKEN** (unreadable / data-destroying / unauthorable).

| Surface | Arabic | Thai | Devanagari | Korean | Mixed bidi | Screenshot |
|---|---|---|---|---|---|---|
| **Array cell value** | WORKS | WORKS (marks stack) | WORKS (conjuncts) | WORKS | WORKS (Latin-first) | `as_cells.png` |
| **Caption `label=`** (single line, fits) | WORKS¹ | WORKS | WORKS | WORKS | WORKS¹ | `as_bidi.png`, `as_bidi_zoom.png` |
| **Caption wrap** (long) | WORKS (word-wrap) | **DEGRADED** (overflow) | WORKS | WORKS | — | inherits pill wrap |
| **Annotation pill** (long → wrap) | WORKS (3 lines, RTL order OK) | **DEGRADED** (1 wide line) | WORKS (conjuncts intact) | WORKS (2 lines) | n/a | `as_pills.png` |
| **VariableWatch name column** | WORKS | WORKS | WORKS | WORKS | — | `as_watch.png` |
| **VariableWatch value column** | WORKS (render) | WORKS (render) | WORKS (render) | WORKS (render) | — | `as_watch.png` |
| **…VariableWatch value *authoring*** | WORKS | **BROKEN**² | **BROKEN**² | WORKS | — | (E1010 parse fail) |
| **Narration — interactive/default** | WORKS | WORKS | WORKS | WORKS | WORKS | `narr_probe.png` |
| **Narration — static & print/PDF** | **DEGRADED**³ | WORKS | WORKS | WORKS | WORKS (Latin-first) | `narr_probe.png` |
| **SVG text, RTL-first + embedded Latin/parens** | **DEGRADED→BROKEN**⁴ | — | — | — | **DEGRADED** | `svg_bidi_fix.png` |

¹ Reads acceptably only because `text-anchor:middle` centers it and the run
reorders per-UA; base direction is still LTR (latent — see ⁴).
² `\apply`/`\recolor` selector cannot be authored at all (parser, §3-R4).
³ RTL-*first* paragraphs go LTR-base: wrong alignment + reordered trailing
clause. Latin-first (e.g. `"Arabic: …"`) is unaffected.
⁴ Parens mirror the wrong way and segment order scrambles; see `svg_bidi_fix.png`
top row.

### What each screenshot shows
- **`as_cells.png`** — 5 arrays, one per script. All cell glyphs correct: Thai
  tone/vowel marks sit on their bases, Devanagari `द्वि`/`एल्गोरिथ्म` conjuncts
  form, Arabic words are RTL-internal, Korean syllables compose, mixed
  `giá trị x | = | قيمة البحث` reads correctly. No clipping (over-estimated cell
  width leaves room).
- **`as_pills.png`** — the money shot. Arabic pill wraps to 3 lines in correct
  RTL top-to-bottom order; Devanagari 3 lines with conjuncts intact; Korean 2
  lines. **Thai is one unwrapped line stretching wider than the whole 6-cell
  array** (pill box grows to contain it — not clipped, not torn).
- **`as_watch.png`** — name column (Arabic/Thai/Deva/Korean) and value column all
  render correctly and fit their cells.
- **`as_bidi_zoom.png`** — 4× crop: pure-Arabic pill/cells read correctly;
  `giá trị = قيمة` and `(result) = ٤٢` caption read acceptably.
- **`narr_probe.png`** — same Arabic-first sentence with `dir="auto"` (right-
  aligned, RTL, correct) vs without (left-aligned, LTR, trailing clause
  reordered).
- **`svg_bidi_fix.png`** — `نتيجة البحث (result) = 42` as SVG `<text>`: current
  no-bidi emit mirrors the parens wrong; `unicode-bidi:plaintext` fixes it.

---

## 3. Root causes (path:line)

### R1 — Space-only wrap; no segmentation for spaceless scripts  *(→ Thai/CJK DEGRADED)*
`scriba/animation/primitives/_svg_helpers.py:1671` `_wrap_label_lines`, tokenizer
at **1702–1710**:
```python
if not in_math and ch in (" ", ",", "+", "="):   # only these 4 break chars
    tokens.append(current); current = ""
```
Thai/Lao/Khmer/Chinese/Japanese have no such delimiters → the whole label is a
single token. In pixel mode (**1714–1726**) the first token is assigned to a line
unconditionally (`if line and …` — the guard is false on the first token), so an
over-long token is emitted **whole**, never char-split. Net effect: *overflow*,
not torn clusters. Same helper backs captions via
`base.py:629` `_caption_lines` → `base.py:639`, and pill height reservation at
`_svg_helpers.py:3085` / `3125`.

### R2 — No `dir`/`unicode-bidi` on any SVG text  *(→ RTL-first mixed DEGRADED→BROKEN)*
Grep of `scriba/` finds exactly **one** `dir=` in the whole source, and it's on
the narration `<p>` (R3), never on SVG text. Emit sites, all bidi-naked:
- `scriba/animation/primitives/_text_render.py:225–265` — plain `<text>` fast
  path (used by array cells `array.py:290,308`, VariableWatch `variablewatch.py:328,348`,
  single-line captions).
- `_text_render.py:299–338` — the `foreignObject` math path (`text-align` set,
  `dir` not).
- `_svg_helpers.py:1575–1600` — multi-line **pill** tspans (`text-anchor:middle`,
  no dir).
- `base.py:745–755` — multi-line **caption** tspans (`text-anchor:middle`,
  no dir).
- `_text_render.py:341–382` `_render_split_label_svg` — emits primary then
  separator+secondary in **hard visual order** (latent: reversed for RTL edge
  labels).

Consequence: SVG base direction is the UA default (LTR). Single-script runs
reorder fine, and `text-anchor:middle` hides the alignment error — but an
RTL-first run containing Latin/digits/paired punctuation resolves its neutrals
against the LTR base and mis-orders. `svg_bidi_fix.png` (top) shows `(result)`
rendered with mirrored/broken parens; adding `unicode-bidi:plaintext` to the same
`<text>` style (bottom) restores correct order in Chromium.

### R3 — Narration `dir="auto"` applied to 1 of 4 emit sites  *(→ static/print DEGRADED)*
`scriba/animation/_html_stitcher.py`:
- **:628** interactive-live `<p class="scriba-narration" dir="auto" …>` — **has it** ✓
- **:268** static-filmstrip per-frame `<p class="scriba-narration" id=…>` — no dir
- **:559** print-frame `<p class="scriba-narration" id=…>` — no dir
- **:550** print-substory `<p class="scriba-narration">` — no dir

No CSS sets `direction`/`unicode-bidi` on `.scriba-narration` (verified), so the
attribute is the only lever. `narr_probe.py` computed styles: Arabic-first with
`dir=auto` → `direction:rtl`; without → `direction:ltr`. So `--static`, and any
printed/PDF export, lose RTL narration correctness that the on-screen default has.

### R4 — Selector identifier scan rejects combining marks  *(adjacent parser BLOCKER)*
`scriba/animation/parser/selectors.py:266` `_expect_ident`, **269–276**:
```python
self._text[self._pos].isalpha() or self._text[self._pos] == "_"   # start
self._text[self._pos].isalnum() or self._text[self._pos] == "_"   # continue
```
Python's `isalpha`/`isalnum` return **False** for combining marks (category Mn/Mc).
Isolated result (`parse_selector`): `v.var[الفهرس]` OK, `v.var[결과]` OK, but
`v.var[ค่า]` and `v.var[खोज]` raise **E1010** at the tone mark U+0E48 / vowel
sign U+094B. So a VariableWatch (or any) variable named in Thai-with-tones or
Devanagari-with-vowel-signs **cannot be targeted by `\apply`/`\recolor`** — the
value surface is unauthorable for those scripts even though it renders fine once
set. (This is why `as_watch.tex` had to use ASCII handles for the value test.)

---

## 4. What the browser already handles for free

Do **not** re-implement any of these — the UA is already correct:

- **Shaping / clustering.** Arabic contextual joining, Thai above/below mark
  stacking, Devanagari conjunct formation, Korean jamo composition — all correct
  in `<text>`, `<tspan>`, and `foreignObject`. `_escape_xml` preserves bytes; the
  UA does the rest. (`as_cells.png`, `as_watch.png`.)
- **Per-run bidi reordering.** A single-script Arabic run inside an LTR-base
  `<text>` still lays out RTL. This is why pure-Arabic cells, the 3-line Arabic
  pill (correct top-to-bottom logical order), and Arabic captions read right
  despite no `dir`. (`as_pills.png`, `as_bidi_zoom.png`.)
- **`text-anchor:middle` as accidental armor.** Centering masks the LTR-base
  *alignment* bug for RTL text on every surface. (If any surface used
  `anchor:start`, RTL would visibly left-align — none currently do.)
- **HTML paragraph bidi with `dir="auto"`.** Full first-strong resolution incl.
  RTL-first — the interactive narration is correct for every script tested.
- **aria-label byte order.** The R-11 speech path (`_latex_to_speech`) only
  rewrites LaTeX tokens; on pure non-Latin text it passes bytes through unchanged,
  and the emitted `aria-label` preserves logical order (screen readers apply
  their own bidi). No visual/AT mangling observed.

---

## 5. Fix inventory (ranked by severity)

| # | Severity | Fix | Effort | Where |
|---|---|---|---|---|
| F1 | **BROKEN** (unauthorable) | Accept Unicode letters **and** combining marks in selector idents: replace `isalpha()/isalnum()` with a category test allowing `L*`, `Mn`, `Mc`, `Nd` (or gate on `str.isidentifier()` semantics after NFC). Unblocks Thai/Devanagari VariableWatch names. | one function | `selectors.py:269–276` |
| F2 | DEGRADED (cheap) | Add `dir="auto"` to the 3 remaining narration `<p>` sites (static/print/substory) to match the interactive one. | 3 one-liners | `_html_stitcher.py:268, 550, 559` |
| F3 | DEGRADED→BROKEN (cheap, verified) | Add `unicode-bidi:plaintext` (the SVG analog of `dir="auto"`) to the style string of every SVG text emitter, so RTL-first mixed runs get first-strong base direction. Proven to fix parens/order in Chromium (`svg_bidi_fix.png`). Low risk: LTR content is unaffected. | style-string edits | `_text_render.py:225–265, 299–338`; `_svg_helpers.py:1575–1600`; `base.py:745–755` |
| F4 | DEGRADED (harder) | Script-aware wrap: when a single token exceeds `max_px`, fall back to breaking at **grapheme-cluster** boundaries (never inside a cluster) for spaceless scripts — ideally ICU/`uniseg` line-break; at minimum a grapheme-safe hard break. Fixes Thai/Lao/Khmer/CJK pill & caption overflow. | new helper + wire into pixel-mode branch | `_svg_helpers.py:1714–1726` (+ callers) |
| F5 | LOW (latent) | `_render_split_label_svg` emits secondary in hard visual order — reversed for RTL. Gate ordering on run direction, or set `unicode-bidi:plaintext`. Low priority (numeric edge labels). | small | `_text_render.py:341–382` |

**Recommended sequencing.** F1 + F2 + F3 are small, independent, and clear the
BROKEN/mis-order cases (they are the "`dir="auto"` one-liners" tier). F4 is the
one real feature (script-aware segmentation) and is the only item requiring a new
dependency or non-trivial code. F5 is opportunistic.

**One caveat to carry forward.** The width work is a *safe over-estimate*
off-Latin, which is exactly why nothing clipped in these renders — cells and
pills had spare room. If width is ever tightened toward exact for these scripts,
re-run this matrix: the wrap-overflow (F4) and the missing-`dir` mis-order (F3)
would start clipping instead of merely spilling, upgrading DEGRADED → BROKEN.
