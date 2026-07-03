# Text-Width Architecture: exact per-font metrics vs the `estimate_text_width` heuristic

> **STATUS: LANDED (v1 scope) 2026-07-03** — commit 0cd523b: Scriba Sans subset + `_text_metrics.TextMeasurer`, 14px sans surface exact (<1% vs browser). v2 (mono font, textLength flag) remains designed-not-scheduled.

> Structural design investigation. No source was modified; all probes ran in a throwaway
> scratchpad venv (`fonttools` + `uharfbuzz`, py3.14) against fonts already on this machine.
> Related prior art in this folder: `label-rendering-investigation.md`.

---

## 1. Hand-off Brief

**Question.** Can we replace the `estimate_text_width` heuristic
(`scriba/animation/primitives/_text_render.py:78`) with exact per-font metrics, given
scriba's hard constraints — pure-Python render, fully self-contained HTML, deterministic
bytes for the 105-file golden corpus?

**Short answer.** Yes for the *shipped-and-pinned* surface; **impossible in principle for
anything scriba does not both ship and pin.** Exact metrics are only "exact" if the viewer
renders the exact font we measured. Today scriba pins **no** text font: cell/node values
render in `inherit` (the host/system sans) and every label/pill/caption/index renders in
generic `ui-monospace, monospace` (`scriba-scene-primitives.css:79-94`). Both resolve to
whatever the *reader's* OS/browser/host page supplies, whose advances scriba cannot know.
So "exact metrics" is not a measurement upgrade — it is a **decision to ship a font and pin
`font-family` to it first in the stack.** Everything else follows.

**Feasibility verdict (evidence-backed):**

| Constraint | Verdict | Evidence |
|---|---|---|
| Pure-Python | ✅ `fontTools` is pure-Python; `uharfbuzz` (compiled) is **not needed** | §3, §5 measurer resolves `tnum` in pure Python |
| Self-contained HTML | ✅ base64-embed a woff2 exactly like KaTeX | `css_bundler.py:42` precedent |
| Font size budget | ✅ Inter subset **Latin+Vietnamese = 43 KB woff2 / 57 KB base64** (⅛ of the 380 KB KaTeX blob) | §3 probe |
| Deterministic bytes | ✅ same font bytes → identical advances (sha256-stable, reopen-stable) | §3 probe |
| Golden stability | ⚠️ **all 105 goldens re-pin once**, `SCRIBA_VERSION` 11→12 | §6 |

**Two findings that make the naive plan wrong** (both empirically confirmed, §3):

1. **`tabular-nums` is active on cells/nodes** (`scriba-scene-primitives.css:375`,`415`).
   A raw `hmtx` advance sum is *wrong* for digits — the most common cell content. Inter's
   default digits are proportional (833–1323 units); under `tnum` they collapse to one
   width (1328). `"12345"@14px` = **40.23 px default vs 45.39 px tabular** — a 13% error if
   you forget the feature. The measurer **must** replay the CSS's active OpenType features.
2. **Combining marks are not all zero-width, and input may be decomposed.** Vietnamese
   `U+0323` (dot-below) carries advance 495 in Inter; NFC-precomposed `ệ (U+1EC7)` is one
   6.41 px glyph. The measurer **must** NFC-normalize first (matching what a browser paints
   for precomposed text) or widths drift for decomposed input.

**Recommendation (Hybrid A+C).** Ship one OFL sans (Inter) subset to Latin+Vietnamese,
base64-embed it gated exactly like KaTeX, pin it first in `--scriba-cell-font` /
`--scriba-node-font`, and add a pure-Python `fontTools` `TextMeasurer` (NFC + `tnum`/`zero`
resolution) behind a `Protocol` seam whose no-font fallback is today's estimator. Keep the
monospace label surface on the heuristic in v1 (a constant-advance mono is already the
heuristic's best case) and layer **`textLength`+`lengthAdjust` (Option C)** as an
opt-in "exactness-by-decree" safety net under the measurer. This is the smallest change that
makes the dominant width driver (14 px numeric cells → viewBox sizing) truly exact.

---

## 2. Choke-point + font-stack audit

### 2.1 The heuristic model (`_text_render.py`)

`_char_display_width` (`_text_render.py:61-75`) returns exactly three values:

| Class | Rule | Value |
|---|---|---|
| `Mn` / `Me` / `Cf` (combining / enclosing / format) | zero display | `0.0` |
| East-Asian `W` / `F` (CJK wide/fullwidth) | ~1 em | `1.0` |
| everything else | "sans-serif Latin average" | `0.62` |

`estimate_text_width(text, font_size=14)` (`_text_render.py:78-118`) sums those, with a
two-pass ZWJ-cluster merge (an entire `U+200D` emoji cluster counts as `1.0`), then returns
`int(total * font_size + 0.5)`.

**Correction to the brief's premise.** There is **no "1.15 Vietnamese factor."** The only
`1.15` in the codebase is the **KaTeX math-width** scale inside `_label_width_text`
(`_svg_helpers.py:1349-1372`), unrelated to Vietnamese. Vietnamese is handled solely by the
generic `0.62` (base letters) plus `0.0` (combining marks) rules — i.e. Vietnamese is
measured *identically to English* except that decomposed diacritics vanish. This is exactly
where the heuristic is weakest: real Vietnamese strings measured **+20%** under the true
Inter width (§3), because `0.62` is a poor average for the diacritic-dense, accent-stacked
Latin that Vietnamese uses.

**How wrong is `0.62`?** Measured against real Inter advances (§3): `+27%` for `"Hello"`,
**`+154%`** for `"iiiii"`, **`-38%`** for `"WWWWW"`, `+44%` for `"array[i]"`. The constant
is a mid-point that is wrong in both directions by large margins; it survives because every
caller pads generously and because nothing downstream is pixel-audited.

### 2.2 Is `estimate_text_width` the single choke point? Mostly — but callers pre/post-adjust

`estimate_text_width` is imported in **16 files** with **34 call sites**. It is the single
measurement primitive, **but a new engine cannot just swap it** — three caller-side
transforms wrap it and must be preserved verbatim:

1. **`_label_width_text` pre-transform** (`_svg_helpers.py:1340-1373`): strips `$…$`
   delimiters, strips `\command` tokens and `{ }` braces, then **inflates by 1.15×** (append
   15% of chars) so the linear estimator lands on KaTeX's ~15%-wider math render. A real
   measurer measures *glyphs*, not this proxy string — so for math labels the measurer must
   **not** be fed `_label_width_text` output; math width stays a KaTeX concern
   (`_has_math` routes to the `<foreignObject>` path, `_text_render.py:224`). The seam must
   branch: plain text → measurer; `$…$` → leave the existing math-proxy path untouched.

2. **The `+pad` / `+12` constants** live in the callers, not the estimator. A new measurer
   returns a raw glyph width; every caller keeps its additive pad. Inventory:

   | Pad constant | Value | Where |
   |---|---|---|
   | `_CELL_HORIZONTAL_PADDING` | `12` | `_types.py:175` (cells, caption block) |
   | `_LABEL_PILL_PAD_X / _Y` | `6 / 3` | `_svg_helpers.py:95-96` (pills, weights) |
   | `_CAPTION_SAFETY_PAD` | `8` | `base.py:196` — *literally "estimate_text_width under-counts; pad"* |
   | `+12` (fo_width) | inline | `metricplot.py:567,578,592,766` |
   | `_LINE_LABEL_PAD` / `+16` / `+20` | `10` / — | `plane2d.py:979`, `variablewatch.py:107,124`, `hashmap.py:120` |

   **Design note:** `_CAPTION_SAFETY_PAD = 8` exists *only* to compensate for the estimator
   under-counting. With an exact measurer it becomes a genuine safety margin (or shrinks) —
   changing it is a golden-affecting choice, so v1 should **keep all pads byte-identical**
   and let the measured width change alone drive the re-pin.

3. **The wrap loop is recursively measurement-bound.** `_wrap_label_lines`
   (`_svg_helpers.py:1671`) calls `estimate_text_width(_label_width_text(cand), font_px)`
   *inside* its break decision, and `pill_dimensions` (`_svg_helpers.py:1384`) +
   `_caption_lines` (`base.py:629`) sit on top. So a metrics change doesn't just resize a
   box — it **moves line breaks**, which changes `<tspan>` splits, which changes bytes for
   every wrapped label/caption. This is why the goldens re-pin wholesale (§6) and why a
   parity test must assert *wrap output*, not just width numbers.

### 2.3 Caller families → font_px → **rendered font** (the map that decides exactness)

The measured surfaces fall into **two font regimes**. Column "Rendered font" is the actual
computed `font-family`, which is what an exact metric would have to match.

| Surface (caller) | path:line | `font_px` | CSS token / class | **Rendered font-family** | Regime |
|---|---|---|---|---|---|
| Array cell values | `array.py:164` | 14 | `--scriba-cell-font: 500 14px inherit` | **`inherit`** → host/system sans | proportional |
| Array index labels | `array.py:169` | 11 | `--scriba-cell-index-font: … ui-monospace, monospace` | **monospace** | mono |
| Stack items | `stack.py:140` | 14 | `--scriba-cell-font` | `inherit` sans | proportional |
| Queue cells | `queue.py:146,177,202` | 14 | `--scriba-cell-font` | `inherit` sans | proportional |
| LinkedList values | `linkedlist.py:129` | 14 | `--scriba-cell-font` | `inherit` sans | proportional |
| Graph/Tree node text | via base | 14 | `--scriba-node-font: 500 14px inherit` | `inherit` sans | proportional |
| Graph weight pills | `graph.py:1268,1476`, `_layout_expand.py:132,290` | 11 | `--scriba-annotation-font: … monospace` / `.scriba-graph-weight` | **monospace** | mono |
| HashMap index/entries | `hashmap.py:120,128` | 13 | inline `_ENTRIES_FONT_SIZE` | (cell-ish) | proportional* |
| Matrix row/col labels | `matrix.py:229,234` | 10 | label | `inherit`/mono | mixed |
| NumberLine ticks | `numberline.py:147` | 10 | label | mono | mono |
| VariableWatch names/values | `variablewatch.py:107,124` | 12 / 13 | name/value | mixed | mixed |
| Captions (all primitives) | `base.py:647` | 11 | **`.scriba-primitive-label`** = `--scriba-label-font: 600 11px ui-monospace, monospace` | **monospace** | mono |
| Pill labels (annotations) | `pill_dimensions` → `_svg_helpers.py:1408,1552,2031,3127` | 11 | `.scriba-primitive-label` | **monospace** | mono |
| Plane2D point/line labels | `plane2d.py:1016,1054` | 10 | `var(--scriba-font-mono, ui-monospace, monospace)` | **monospace** | mono |
| MetricPlot axis/legend | `metricplot.py:567,578,592,766` | 11 | `.scriba-metricplot-* { font-family: inherit }` (`scriba-metricplot.css:1`) | `inherit` sans | proportional |
| CodePanel header/code | `codepanel.py:235,394` | 12 | inline `font-family:monospace` (`codepanel.py:285`) | **monospace** | mono |

`*` HashMap sets `font-size` inline but no `font-family`, so it inherits the sans.

**Consequences for the design:**
- The **dominant width driver is the 14 px `inherit` sans surface** (array/stack/queue/
  linkedlist/graph/tree cells+nodes). It sizes the viewBox (`_prescan_value_widths`,
  `_frame_renderer.py:45`, feeds `compute_viewbox`). Pinning + exactly measuring *this one
  regime* captures most of the value.
- The **monospace regime** (labels/pills/captions/weights/index/plane2d/codepanel) is the
  heuristic's *best* case: a real monospace has a single advance, so `chars × ratio` is
  already near-exact — it's just not *pinned* (SF Mono ≈ 0.60 em, Consolas ≈ 0.55, DejaVu
  Mono ≈ 0.60, so the *ratio* differs per reader). Making mono exact means shipping a mono
  and pinning it — a second font. v1 defers this (see §4/§5).

### 2.4 Standalone vs embed: the pin is only half-controlled today

In **standalone** output (`render.py`), `body { font-family: -apple-system, …, sans-serif }`
(`scriba-standalone.css:15`) supplies the `inherit` for cells. In **embed** mode
`scriba-embed.css` deliberately sets no body/widget font (`scriba-embed.css:8-11`), so cells
inherit the **host page's** font — entirely outside scriba's control. Any exact-metrics
design must therefore set `font-family` on the *widget subtree itself* (not rely on the
standalone body), so embedded and standalone render — and measure — identically.

---

## 3. Embed precedent + dependency audit (+ live subset probe)

### 3.1 The KaTeX base64 precedent and its Opt-3 gate

`inline_katex_css()` (`css_bundler.py:42-70`) reads `vendor/katex/katex.min.css` and regex-
replaces every `url(fonts/KaTeX_*.woff2)` with `url(data:font/woff2;base64,…)`, `lru_cache`d
for the process. It is invoked once, **conditionally**, in the assembler:

```
render.py:267-285   # Opt-3: skip the ~380 KB KaTeX CSS+fonts blob when the document has no math
_has_math = bool(anim_blocks or diag_blocks or re.search(r"(?<!\\)\$", source))
if _has_math:
    css_parts.append(inline_katex_css())
```

This is the exact pattern a text font would reuse: read woff2 → base64 → concatenate into the
single inline `<style>`. `font-family` and `font-size` are already sanitizer-allowed on
`<text>`/`<tspan>` (`sanitize/whitelist.py:180,185`), so pinning is safe.

**Gating question — can a text font be Opt-3-gated like KaTeX?** No, and it shouldn't try:
**text is always present** (every primitive has cells/labels), so unlike math the font is
*always* paid. The budget must be justified on its own (it is: 43 KB, §3.3), not deferred.
The one legitimate gate is **format capability, not content**: emit the `@font-face` only in
the self-contained standalone/embed HTML that scriba fully controls; a host integration that
prefers its own font can opt out via a flag (the font-face is additive; if a consumer doesn't
want it they set `--scriba-cell-font` to their own family and skip the blob).

### 3.2 Dependency reality

- **`fonttools`: absent** from `pyproject.toml` (deps are just `pygments`; dev adds pytest/
  bleach/lxml/hypothesis/pytest-cov) and **not installed** in `.venv`. It is **pure-Python**
  (with optional `brotli` for woff2 I/O). Adding it violates nothing — MIT-licensed, no
  compiled artifact.
- **`uharfbuzz`: absent**, and it is a **compiled wheel**. I confirmed a py3.14 macOS wheel
  installs and imports (0.55.0), so it *is* available — but §3.4/§5 show scriba's text needs
  **no complex shaping** (no contextual kerning, no mark-to-base positioning for the
  precomposed-NFC + `tnum` cases), so pure `fontTools` suffices. **Recommendation: do not
  add uharfbuzz** — it buys nothing here and adds a binary dependency to a pure-Python
  package.

> **Build-time vs runtime split.** The subsetting tool (`pyftsubset`) and any width-table
> precompute run **at build/vendor time only**. If the design precomputes an advance table
> (§5 variant), the *shipped wheel needs no fonttools at all* — it reads a small JSON/pickle.
> If the design measures live, `fonttools` becomes a runtime dep. Both are viable; §5 picks
> the precomputed-table route to keep runtime dependency-free and deterministic.

### 3.3 Live subset-size probe (real numbers, this machine)

Source: `~/Library/Fonts/Inter-Regular.ttf` (411,640 B). `pyftsubset … --flavor=woff2`:

| Subset | unicode ranges | woff2 | base64 (inline cost) |
|---|---|---:|---:|
| Latin only (Google `latin`) | `U+0000-00FF` + punctuation | 39,872 B | 53,164 B |
| **Latin + Vietnamese** (Google `latin`+`vietnamese`) | + `U+1EA0-1EF9`, `U+01A0-01B0`, `₫` … | **43,016 B** | **57,356 B** |
| Broad (full Latin-Ext A/B + Viet Additional + combining + `kern`) | `U+0000-024F,0300-036F,1E00-1EFF` | 73,164 B | 97,552 B |
| Broad, no layout features | same, `kern` dropped | 54,452 B | 72,604 B |
| — KaTeX blob (for scale) | — | ~380,000 B | — |

**Coverage confirmed:** the Latin+Vietnamese subset covers the entire `U+1EA0–1EF9`
Vietnamese block with **0 missing** codepoints. Recommended ship target: **Latin +
Vietnamese + `U+0300-036F` combining block** (so decomposed input still measures) ≈ **45–50 KB
woff2 / ~65 KB base64** — about **⅛ of the KaTeX blob** scriba already ships when math is
present. Drop `kern`/GPOS from the subset (§3.4): scriba never renders kerned running text
that needs it, and it saves ~25%.

### 3.4 Determinism + the two measurement gotchas (probed)

**Determinism:** `sha256(woff2)` is stable; reopening the font yields byte-identical
advances; there is **no per-machine nondeterminism** in `fontTools` advance reads (it is pure
table lookup — same font bytes → same integers). Safe for byte-exact goldens.

**Gotcha 1 — `tabular-nums` (load-bearing).** The cell/node CSS forces
`font-variant-numeric: tabular-nums lining-nums slashed-zero` +
`font-feature-settings: "tnum" "lnum" "zero" "ss01"` (`scriba-scene-primitives.css:375-376`,
`415-416`). Probed:

```
default '12345' @14px = 40.23 px   (proportional digits, advances 833..1323 units)
tnum    '12345' @14px = 45.39 px   (all digits → 1328 units, uniform)
```

A raw `hmtx` sum picks the *default* glyphs and is **13% wrong for numbers**. The measurer
must resolve the `tnum`/`zero` GSUB single-substitutions and use the substituted glyph
advances. I did this in pure `fontTools` (walk `GSUB` `FeatureRecord['tnum'] → LookupList →
mapping`), reproducing 45.39 exactly — **no uharfbuzz needed.**

**Gotcha 2 — NFC + combining marks.** `U+0323` (Vietnamese dot-below) has advance **495**,
not 0, as a standalone glyph; the heuristic's blanket `Mn→0` is itself inaccurate. In
practice Vietnamese uses NFC-precomposed codepoints (`ệ = U+1EC7`, one 6.41 px glyph), and
`NFC(e+◌̣+◌̂) == ệ` was confirmed. **The measurer must `unicodedata.normalize("NFC", text)`
first**, then it measures precomposed glyphs exactly and the combining-mark edge case
disappears.

**Heuristic-vs-exact deltas (Inter, probed):**

| text | `font_px` | exact px | heuristic px | Δ |
|---|---:|---:|---:|---:|
| `Hello` | 14 | 33.74 | 43 | +27% |
| `iiiii` | 14 | 16.95 | 43 | +154% |
| `WWWWW` | 14 | 68.97 | 43 | −38% |
| `12345` (tnum) | 14 | 45.39 | 43 | −5% |
| `array[i]` | 14 | 47.74 | 69 | +44% |
| `Tổng số phần tử` | 11 | 84.95 | 102 | +20% |
| `Đường đi ngắn nhất` | 11 | 102.09 | 123 | +20% |

---

## 4. Architecture options A–D evaluated

### Option A — Shipped-font exact metrics (measure what we pin)

Ship one OFL sans, subset to Latin+Vietnamese, base64-embed it, pin it **first** in the
cell/node tokens with a system fallback, and measure with `fontTools` `hmtx` + `tnum`
resolution over NFC-normalized text.

- **Font choice:** **Inter** (OFL-1.1; SIL license explicitly permits embedding & subsetting;
  full Vietnamese; the reference sans metrics probed above). Alternatives — **Noto Sans**
  (OFL, present on this machine, slightly wider glyphs, official Vietnamese subset) and
  **IBM Plex Sans** (OFL, Vietnamese via Plex). All three ship at roughly the same subset
  size. Inter's `tnum` + `ss01`/`zero` map cleanly to the CSS already in the repo.
- **CJK:** the size killer, and *unnecessary to ship*. CJK is rare in this CP-editorial
  corpus and the heuristic's `1.0 em` rule (`_char_display_width` `W/F → 1.0`) is already the
  correct model for CJK in any CJK font. **Keep measure-CJK-by-class**: exact metrics for the
  shipped-coverage codepoints (Latin+Vietnamese), `1.0 em` fallback for `W/F`, estimator for
  the rest. No 10 MB CJK font.
- **Pros:** truly exact for the dominant surface; deterministic; ~⅛ KaTeX cost.
- **Cons:** must also *pin* (a visible rendering change — cells stop using the reader's
  system font); re-pins all goldens; introduces the font blob + measurer.
- **Verdict:** the core of the recommendation.

**A-variants on scope:**
- **A-min (ship sans, pin+measure cells/nodes only; leave mono labels on heuristic).**
  Cheapest; captures the viewBox-driving surface. Monospace labels keep today's behaviour.
- **A1 (consolidate to one font).** Repoint the mono label tokens to the shipped sans too, so
  there is one font and one metric table. Simplest *measurer*, but changes the label
  aesthetic (mono → sans) everywhere — a larger visual diff.
- **A2 (ship sans + a mono).** Pin both regimes to shipped fonts, two metric tables,
  ~+40 KB. Preserves aesthetics, exact everywhere. Most cost/complexity.

### Option B — Metrics table without shipping a font

Bundle an AFM-style advance table (e.g. Helvetica/Arial widths) as data, embed **no** font.

- **Pros:** tiny (a few KB of numbers), no font blob, no `@font-face`.
- **Cons:** **still not exact** — you measured Helvetica but the reader renders their system
  font. It's a *better estimate*, not exactness. And it can't honour `tnum` (that's a
  font+CSS interaction, not a static table) — so it re-introduces the 13% numeric error.
- **Verdict:** the accuracy jump (from `0.62`-average to Helvetica-average) is real but
  **not worth a new subsystem** when, for the same order of effort, Option A gets you
  *actual* exactness by also pinning. Reject as a standalone; its table-precompute idea is
  reused *inside* A (§5) — but computed from the *shipped* font, which makes it exact.

### Option C — `textLength` + `lengthAdjust` (exactness by decree)

Emit `textLength="W" lengthAdjust="spacing"` on caption/pill `<text>` so the browser
*forces* the glyphs to fit scriba's declared width, whatever font renders.

- **Pros:** the rendered text width **equals** scriba's number by construction — immune to
  font substitution, works in embed mode against an unknown host font. No font blob.
- **Cons / risks:**
  - **Distortion.** `lengthAdjust="spacing"` stretches/squeezes inter-glyph spacing only
    (safe-ish); `"spacingAndGlyphs"` scales glyph shapes (visible distortion) — never use the
    latter. Even `"spacing"` looks wrong if scriba's estimate is far off (the `±150%`
    heuristic errors would produce visibly gappy or cramped text).
  - **Wrapping interaction.** `textLength` applies per `<text>`/`<tspan>`; scriba already
    splits wrapped captions into per-line `<tspan>`s (`base.py:751`), so each line needs its
    own `textLength` — workable but fiddly, and it fights the wrap loop that *chose* those
    breaks from the same estimate.
  - **Copy/paste + a11y** are unaffected (text content is intact).
  - **Sanitizer.** `textLength`/`lengthAdjust` are **not** in the `<text>`/`<tspan>`
    allowlists (`sanitize/whitelist.py:180-186`) — adding them is a (small, low-risk) security-
    surface change.
- **Verdict:** **not a replacement** (it decrees the box, it doesn't *know* the width, so a
  bad estimate still yields ugly spacing), but an excellent **safety net layered under A**:
  once A makes the number nearly exact, `lengthAdjust="spacing"` closes the residual
  sub-pixel/kern gap and defends embed-mode against host-font substitution with *zero*
  distortion (because the forced width ≈ the natural width).

### Option D — Hybrid (recommended)

**A (A-min scope) + C.** Ship+pin+measure the sans cell/node regime exactly; keep the mono
label regime on the heuristic for v1 (it's mono's best case); add `textLength` on the
pinned-sans `<text>` as a decree-level safety net for embed-mode font substitution. This is
the minimum change that makes the dominant width driver exact while keeping the blast radius
one regime and the runtime dependency-free.

---

## 5. Chosen design — full spec

### 5.1 The seam: a `TextMeasurer` Protocol with an estimator fallback

New module `scriba/animation/primitives/_text_metrics.py`:

```python
from typing import Protocol

class TextMeasurer(Protocol):
    def measure(self, text: str, font_px: float) -> float: ...   # raw glyph width, px

class HeuristicMeasurer:
    """Today's estimate_text_width, verbatim — the no-font fallback."""
    def measure(self, text, font_px): return estimate_text_width(text, int(font_px))

class ShippedFontMeasurer:
    """Exact advances for the pinned sans (Inter), NFC + tnum/zero honoured."""
    # Backed by a precomputed advance table (built at vendor time), so the
    # shipped wheel needs NO fonttools at runtime and is fully deterministic.
```

- `estimate_text_width` **stays** as the module-level function and as
  `HeuristicMeasurer.measure` — it remains the fallback for: CJK (`W/F`), any codepoint
  outside the shipped subset, and any surface not yet pinned (all mono labels in v1).
- A single process-level `get_measurer()` (lru-cached) returns the `ShippedFontMeasurer` when
  the advance table is present, else `HeuristicMeasurer`. Callers do **not** each decide.

**Wiring through the caller families (minimal edits, pads untouched):**
- `array.py`/`stack.py`/`queue.py`/`linkedlist.py`/`graph.py`/`tree.py` cell/node width:
  route the 14 px calls through `get_measurer().measure(...)`.
- `pill_dimensions`, `_wrap_label_lines`, `_caption_block_width`: these feed the **mono**
  regime and the **math-proxy** (`_label_width_text`) path — **leave on the estimator in
  v1.** (They only become exact under A2; keeping them stable shrinks the v1 golden diff to
  the sans surface.)
- **Branch rule:** if `_has_math(text)` → existing `<foreignObject>`/`_label_width_text`
  path, never the measurer. Plain sans text → measurer. Everything else → estimator.

### 5.2 The measurer algorithm (why it's exact and pure-Python)

```
def measure(text, font_px):
    s = unicodedata.normalize("NFC", str(text))       # gotcha 2
    total = 0.0
    for ch in s:
        adv = TABLE.get(ord(ch))                        # tnum/zero already baked in for digits
        if adv is None:
            total += _char_display_width(ch) * UPM      # CJK / out-of-subset → heuristic units
        else:
            total += adv
    return total / UPM * font_px
```

- `TABLE` is built at vendor time from the subset woff2: for `0-9` it stores the **`tnum`
  substituted** advance (1328), for `ss01`/`zero`-affected glyphs the substituted advance,
  for everything else the default `hmtx` advance. Digits therefore come out at 45.39, not
  40.23 — matching what the CSS actually paints.
- No kerning term: the subset drops GPOS/`kern` (§3.3) and scriba's cell/node text is
  short tokens where kerning is negligible; `textLength` (§5.4) absorbs the residual.
- Pure integer table math → **byte-deterministic**, no float platform drift beyond the single
  final `/UPM*font_px` (which is identical across machines for identical inputs).

### 5.3 Font pipeline + CSS

- **Vendor:** add `scriba/animation/vendor/inter/Inter-subset.woff2` (Latin+Vietnamese+
  combining, no GPOS) and a generated `inter_advances.json` (the `TABLE`). Build command
  (documented, run by a maintainer, not at install):
  ```
  pyftsubset Inter-Regular.ttf \
    --unicodes="U+0000-00FF,U+0100-024F,U+0300-036F,U+1EA0-1EF9,U+01A0-01B0,U+20AB,U+2000-206F" \
    --layout-features='tnum,zero,ss01,lnum' --flavor=woff2 \
    --output-file=Inter-subset.woff2
  ```
- **License:** ship `vendor/inter/OFL.txt`. OFL-1.1 permits bundling/subsetting/embedding;
  the only constraint is the Reserved Font Name — the subset must not be *named* "Inter" in a
  way that impersonates upstream; a `@font-face { font-family: "Scriba Sans"; ... }` local
  name sidesteps it cleanly.
- **CSS bundler:** add `inline_text_font_css()` beside `inline_katex_css()` in
  `css_bundler.py`, same base64 pattern, `lru_cache`d. It emits one `@font-face`
  (`font-family: "Scriba Sans"`) with the data-URI woff2.
- **Pin (the load-bearing line):** change the sans tokens in
  `scriba-scene-primitives.css:79,82` from `… inherit` to
  `--scriba-cell-font: 500 14px "Scriba Sans", -apple-system, BlinkMacSystemFont, "Segoe UI",
  Roboto, sans-serif;` (and `--scriba-node-font` identically). Shipped font **first**, system
  stack as graceful fallback. Set it on the widget subtree so embed mode is covered too
  (§2.4).
- **Wheel packaging:** extend `pyproject.toml` `[tool.hatch.build.targets.wheel.package-data]`
  `"scriba.animation"` to include `vendor/inter/*`.

### 5.4 Option C safety net (opt-in, layered)

On the pinned-sans `<text>` (cells/nodes) emit `textLength="{measured}" lengthAdjust="spacing"`
behind a flag (default on for standalone, on for embed where host-font risk is highest).
Requires adding `textLength`,`lengthAdjust` to the `<text>`/`<tspan>` allowlists
(`sanitize/whitelist.py`). Because the measured width ≈ natural width, `spacing` produces no
visible distortion; it only defends against a reader whose browser substitutes a different
"Scriba Sans".

### 5.5 Gating / budget justification

No content gate (text is always present, §3.1). The font blob is **always paid** in
self-contained output: **~65 KB base64**, ⅛ of the KaTeX blob, justified by making the
primary layout surface exact. Provide an escape hatch (`--no-embed-text-font` / consumer sets
their own `--scriba-cell-font`) for integrations that supply their own pinned font and don't
want the bytes.

---

## 6. Golden + `SCRIBA_VERSION` plan

- **Every metric change re-pins every golden.** The wrap loop is measurement-bound (§2.2), so
  measured-width changes move line breaks → change `<tspan>` bytes → change viewBox → change
  layout across the corpus. Expect **all ~105 `tests/golden/examples/*.html`** (plus the 5
  `tests/golden/animation/*` and `smart_label`) to change in one commit.
- **Mechanism (already exists):** `SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/examples/ -v`
  regenerates in place (`tests/golden/examples/test_example_html.py:26,112`); byte-for-byte
  compare otherwise. Review the diff by hand before committing (the harness prints the rebase
  command per-file).
- **`SCRIBA_VERSION` bump 11 → 12** (`scriba/_version.py:6`), consumed by
  `pipeline.py:330`'s `versions={"core": SCRIBA_VERSION}`. Add a `_version.py` note in the
  house style: *"12 bumps 11→12: cell/node text is measured against a shipped, pinned sans
  (Inter subset) with tabular-nums honoured instead of the 0.62 heuristic; text widths, line
  wraps, `<tspan>` splits and viewBox extents change across every labelled scene. Consumer
  caches keyed on rendered output MUST invalidate."*
- Bump `__version__` per release convention.
- **One-time, atomic:** land the font+measurer+CSS+goldens+version in a single commit so no
  intermediate state has stale goldens.

---

## 7. TDD plan (browserless suite; opt-in browser parity probe)

**RED → GREEN order:**

1. **Measurer unit tests** (`tests/unit/test_text_metrics.py`, pure, deterministic):
   - `HeuristicMeasurer.measure == estimate_text_width` (fallback parity, locks current
     behaviour).
   - `ShippedFontMeasurer` fixed-vector table: `"12345"@14 → 45.39±0.01` (tnum honoured),
     `"iiiii" < "WWWWW"` (proportional), `NFC(decomposed)==precomposed` width equality,
     out-of-subset codepoint falls back to heuristic units, CJK `W/F` → `1.0 em`.
   - **Determinism:** measure twice, assert identical; assert font `sha256` matches a pinned
     constant (guards an accidental font-file swap).
2. **Wrap-parity tests:** feed known strings through `_wrap_label_lines` / `pill_dimensions`
   and assert the *line splits* (not just widths) — this is what actually moves bytes.
3. **Golden regen** (§6) as the integration gate — the existing corpus test *is* the
   integration coverage.
4. **Font-subset guard:** a test asserts the shipped subset covers `U+1EA0-1EF9` (0 missing)
   and that `inline_text_font_css()` output contains exactly one `@font-face` + one
   `data:font/woff2;base64,` URI (mirrors `test_css_bundler_cache.py`).

**Opt-in browser parity probe (suite stays browserless):** add a Playwright check gated the
way the repo already gates browser probes — a `@pytest.mark.slow`/env-flag test that renders a
few strings in a headless browser with the shipped `@font-face`, reads
`getComputedTextLength()` / `measureText()`, and asserts the Python measurer is within a
tolerance (e.g. **≤1 px or ≤2%**) of browser ground truth for a sans-cell vector. It never
runs in the default suite (no browser dependency in CI's fast path); it's the "is our table
still telling the truth" canary, run before a font/version bump. This mirrors the existing
`mcp playwright` / opt-in browser tooling rather than adding a hard Playwright dep.

---

## 8. Landing order

1. **Vendor + build**: add Inter subset woff2 + `OFL.txt` + generated `inter_advances.json`;
   document the `pyftsubset` command; wheel `package-data`. *(no behaviour change yet)*
2. **Measurer module** `_text_metrics.py`: `TextMeasurer` Protocol, `HeuristicMeasurer`
   (==`estimate_text_width`), `ShippedFontMeasurer` (table-backed), `get_measurer()`.
   Ship with unit tests §7.1–7.2 **before** wiring. *(still no output change — fallback wins
   until the CSS pins)*
3. **CSS bundler**: `inline_text_font_css()` + wire into `render.py`'s CSS assembly next to
   the Opt-3 KaTeX block (always-on for self-contained output; `--no-embed-text-font` hatch).
4. **Pin**: repoint `--scriba-cell-font` / `--scriba-node-font` to `"Scriba Sans", <system>`
   and set the family on the widget subtree (embed parity).
5. **Route the 14 px sans call sites** (array/stack/queue/linkedlist/graph/tree) through
   `get_measurer()`. Leave mono/label/math paths on the estimator. Pads unchanged.
6. **Regen goldens** + **`SCRIBA_VERSION` 11→12** + `_version.py` note + `__version__` — one
   atomic commit.
7. *(Optional, same or follow-up release)* **Option C**: `textLength`+`lengthAdjust` on
   pinned-sans `<text>` + sanitizer allowlist entries + a distortion-tolerance test.
8. *(Deferred)* **A2**: ship a mono subset and make the label regime exact, if the monospace
   surfaces ever prove worth a second font.

---

### Appendix — key citations

- Heuristic: `scriba/animation/primitives/_text_render.py:61-118`
- Math proxy + 1.15× (not Vietnamese): `scriba/animation/primitives/_svg_helpers.py:1340-1373`
- Wrap loop (measurement-bound): `_svg_helpers.py:1671-1740`; `pill_dimensions:1384-1413`
- Caption width/height: `scriba/animation/primitives/base.py:196,629-663`; pad `base.py:196`
- Font tokens (the pin targets): `scriba/animation/static/scriba-scene-primitives.css:79-94`,
  active features `:375-376,415-416`; standalone body `scriba-standalone.css:15`;
  embed no-font `scriba-embed.css:8-11`
- KaTeX embed precedent: `scriba/core/css_bundler.py:42-70`; Opt-3 gate `render.py:267-285`
- Sanitizer allowlist (`font-family` ok; `textLength` absent): `scriba/sanitize/whitelist.py:180-186`
- Version + goldens: `scriba/_version.py:6`; `tests/golden/examples/test_example_html.py`
