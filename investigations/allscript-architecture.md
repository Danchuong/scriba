# All-Script Text-Metrics Architecture — the universal end-state and its staged landing

> **STATUS: RUNG 0 LANDED 2026-07-03** (17ece67, SCRIBA_VERSION 13); rungs 1–2 remain the designed ladder.

> Synthesis target. Design investigation; **no repo source modified**. Feasibility probes ran
> in the scratchpad `ftenv` (fontTools 4.63.0 + uharfbuzz 0.55.0 / harfbuzz 14.2.1, py3.14)
> against system complex-script fonts. Builds on the shipped v1
> (`investigations/text-width-architecture.md`, `text-width-bench.md`) and feeds the two
> in-flight agents (shaping bench + optional-dep design; RTL/complex-script rendering audit).

---

## 1. Hand-off Brief

**Where v1 landed (SCRIBA_VERSION 12, `_text_metrics.py:1-101`).** Cell/node text (the 14 px
surface that sizes every viewBox) is measured by summing exact per-glyph advances of a shipped,
pinned 34 KB Inter subset ("Scriba Sans"), NFC-normalized, `tnum` baked in. Result: **Latin +
Vietnamese exact (<1 %), CJK exact by the 1-em accident, every complex script a safe
over-estimate.** Any codepoint outside the table falls to `_char_display_width` em-units
(`_text_render.py:61-75`); the whole thing degrades to the pre-font heuristic if the table is
missing (`get_measurer()`, `_text_metrics.py:84-95`). This is a solid rung-0 floor.

**The question this doc settles.** How do we make the *other* scripts — Arabic, Thai, Lao,
Khmer, Devanagari + other Brahmic, Hebrew, Hangul — as good as Latin, *without* making every
user who never types them pay for it, and *without* coupling the 105-file byte-golden corpus to
a compiled shaping engine.

**The three findings that decide the architecture (all probed this session):**

1. **Shaping only ever *removes* width, so the rung-0 over-estimate is structurally safe — not
   luck.** Naive per-codepoint advance-sum ÷ HarfBuzz-shaped width, in the system fonts:

   | Script (font) | codepoints | shaped glyphs | naive/shaped | reading |
   |---|---:|---:|---:|---|
   | Arabic (GeezaPro) | 18 | 18 | **1.353** | joining + ligatures collapse advances → +35 % over-reserve |
   | Thai (Thonburi) | 12 | 10 | **1.180** | stacked vowels/tones take 0 advance when positioned → +18 % |
   | Devanagari (Kohinoor) | 13 | 11 | **1.057** | conjunct formation + reordering → +6 % |

   Every ratio > 1. Mark-to-base GPOS sets combining marks to zero x-advance; lig/conjunct GSUB
   fuses glyphs; Arabic joining picks narrower medial forms. **A per-codepoint sum is an upper
   bound on shaped width for these scripts.** That is *why* v1's "+7..+38 %" holds, and why the
   heuristic can never clip complex text — it can only waste box. (Confirms the v1 claim with a
   mechanism, not an observation.)

2. **Per-document runtime subsetting is cheap and deterministic — the PDF/Typst model works
   here.** In-process `fontTools.subset.Subsetter` on GeezaPro Arabic → the 8 codepoints a short
   run actually uses → woff2: **4.6–9.4 ms (warm ~4.7 ms), 1544 B out, byte-identical sha across
   trials.** A whole document is a handful of scripts → tens of ms, well inside a render's
   seconds budget. So the **output** carries only ~KB-scale per-doc subsets (like the string it
   renders); the **master fonts** (the size cost) live in an opt-in extra, and only intl users
   pay. This is the pivot the whole ladder turns on.

3. **HarfBuzz shaping is deterministic *within* a version but is a version-coupled input.**
   Re-shaping the same run in a fresh `hb.Font` gave `IDENTICAL` glyph+advance arrays every time
   (harfbuzz 14.2.1). But HB fixes shaping across major versions, so shaped widths — hence line
   wraps, hence viewBox bytes — can move on an HB upgrade. **Shaped widths must never enter the
   dep-free golden corpus.** (§5 resolves this.)

**Recommendation — a three-rung ladder, not a single answer.** Reject shipping static per-script
fonts in the base wheel (unbounded size; the 99 % of docs that are Latin/Viet pay for Arabic +
Thai + Devanagari + Korean masters). Adopt: **rung 0 default** (stdlib, safe over-estimate,
system-font rendering, *loud* warning) → **rung 1 `[intl]`** (fontTools + master fonts, per-doc
subset + advance-sum + pin: font-exact width, tiny output) → **rung 2 `[shaping]`** (uharfbuzz:
collapses the Arabic/Indic over-reserve to exact). **Capability (installed) is decoupled from
activation (an explicit opt-in flag)** so default output is *always* rung-0 and the goldens stay
dep-free (§5 — the hardest CI question).

---

## 2. The coverage ladder

The central dilemma is that "exact width" requires *measured-font == rendered-font*, which forces
a decision to **ship and pin** a font. v1 did that for one sans. Doing it for every script
statically is unbounded. The ladder makes the cost proportional to use.

| Rung | Install | Runtime deps | Ship/output size | Exactness by script | Rendering | Who it's for |
|---|---|---|---|---|---|---|
| **0 — heuristic (default)** | `pip install scriba-tex` | **stdlib only** | 0 added (34 KB Scriba Sans already shipped) | Latin/Viet **exact**; CJK **1 em** (≈exact); Arabic/Thai/Indic/Hebrew/Hangul **safe over-estimate** (Arabic +35 %, Thai +18 %, Deva +6 % — §1) | Latin/Viet pinned to Scriba Sans; **everything else = viewer's system font** (unpinned, unknowable) | Everyone. The 99 % Latin/Viet/CP-editorial corpus. |
| **1 — `[intl]`** | `pip install "scriba-tex[intl]"` | **fontTools** (pure-Python) + master fonts (bundled or `scriba-fonts` wheel) | Wheel/extra: bounded by # bundled masters (~100–600 KB each, Noto). **Output: per-doc subset ~1–5 KB/script** | + **font-exact** for any script whose width = advance-sum: Hebrew, Thai/Lao base runs, Greek/Cyrillic, CJK-if-master-bundled. Arabic/Indic still over-estimate (shaping unaccounted) but now *font-pinned* | non-Latin runs pinned to bundled Noto + subset embedded → measured == rendered | Docs that actually use intl scripts and want pinned rendering + tight boxes. **Recommended rung for intl.** |
| **2 — `[shaping]`** | `pip install "scriba-tex[shaping]"` | + **uharfbuzz** (compiled) | same output as rung 1 | + **exact for Arabic/Indic**: HB shaped advance collapses the +35 %/+6 % over-reserve; complex marks/conjuncts/ligatures accounted | same as rung 1 | RTL/Indic-heavy docs needing tight layout; power users. Niche. |

**Reading the ladder.** Rung 0 is *safe everywhere and exact where 99 % of content lives* —
it never ships broken, it ships *loose* (padded boxes) for scripts it can't pin, and it says so
(the loud warning, §5.4). Rung 1 buys pinning + exactness for the "simple-width" scripts at the
cost of a bounded master-font download that *only intl users install*, and a *tiny* per-document
output subset. Rung 2 is the last 6–35 % of box-tightness for the two shaping-heavy script
families, at the cost of a compiled wheel and a version-pinned CI lane.

**Why not the other options, explicitly:**
- **(i) static per-script fonts in base wheel** — rejected: unbounded, everyone pays for scripts
  they never use. Its good idea (bundled masters) survives *inside the `[intl]` extra*.
- **(iv) textLength blanket for all non-Latin** — not a *measurement* rung; it's a *safety net*
  layered under every rung (§6). It decrees the box, it doesn't know the width, so alone it just
  redistributes the heuristic's error into spacing distortion. Kept as belt-and-suspenders.

---

## 3. Measurer pipeline spec

Today `measure_text(text, font_px)` (`_text_metrics.py:98-100`) treats a string as one
undifferentiated span. The universal design makes it **itemize → per-run engine → sum**.
Call sites are unchanged (`array.py:165`, `stack.py:141`, `queue.py:147,178,203`,
`linkedlist.py:130` — all 14 px cell surface; `measure_text` is the single seam per GitNexus
`Set_value → Measure` flow); the run structure lives behind the existing `TextMeasurer` Protocol
(`_text_metrics.py:46-49`).

### 3.1 The itemizer (script-run splitter) — UAX #24 / HarfBuzz-parity

New module `scriba/animation/primitives/_script_runs.py`, **stdlib-only, in every rung** (rung 0
needs it to pick per-script heuristic constants and to decide RTL; rungs 1/2 need it to pick the
font + shaper). Algorithm:

```
itemize(text) -> tuple[Run, ...]     # Run = (script, base_dir, text)
  1. s = unicodedata.normalize("NFC", text)      # matches grammar.py:84, selectors.py:66,
                                                 # and the v1 measurer (_text_metrics.py:67)
  2. per codepoint: script = SCRIPT_OF(cp)       # bundled compact ranges table (§3.2)
  3. resolve UAX #24 run boundaries:
       - Common  (space, 0-9, ASCII punct, parens, +, =, /, currency) -> attach to the
                  script of the *preceding strong* run; if none yet, to the *following* strong;
                  if a run is all-Common -> Latin (the shipped table)
       - Inherited (Mn/Mc/Me combining marks) -> always the base char's script
     This is exactly HarfBuzz's itemization, so a rung-1/2 run is measured against the same
     font+shaper the browser will use on that run.
  4. base_dir = RTL if script in {Arabic, Hebrew, Syriac, Thaana, NKo, ...} else LTR
```

**Where spaces/digits/punct/parens attach — settled:** to the surrounding strong script (a space
between two Arabic words joins Arabic; Latin digits inside an Arabic run stay Arabic; a `(` before
a Thai word joins Thai). This keeps the run count minimal and identical to the browser's, so
measured width and rendered width itemize the same way. Pure-neutral strings (all digits/punct)
resolve to Latin → the shipped exact table, preserving today's numeric exactness.

### 3.2 The script table

`unicodedata` exposes `category`/`east_asian_width`/`combining` but **not** the Script property.
Bundle a generated `_script_ranges.py`: a sorted tuple of `(start, end, script)` derived from
Unicode `Scripts.txt`, looked up by `bisect` — a few KB, deterministic, stdlib-only. (Same shape
as the existing East-Asian-width logic in `_text_render.py:72`.) Generated at vendor time by a
documented script, like `inter_advances.json`.

### 3.3 Per-run engine dispatch

```
measure_run(run, font_px, rung) -> float:
  Latin/Latin-Ext/Vietnamese cp in Scriba Sans table -> advance-sum        (exact, all rungs)
  CJK Han/Kana/Hangul-wide (EAW W/F)                 -> 1em rule            (≈exact, all rungs)
  complex (Arabic/Thai/Indic/Hebrew/...):
     rung 0 -> per-script calibrated heuristic constant  (safe over-estimate; §3.4)
     rung 1 -> advance-sum over the bundled MASTER for that script  (font-exact for simple-width
               scripts; still over-estimate for Arabic/Indic, but pinned)
     rung 2 -> HarfBuzz shaped advance over the master   (exact)
  anything else -> _char_display_width fallback          (never crash — v1 guarantee kept)
```

Measurement always reads the **full master** (process-loaded once); the **subset** is an *output*
concern (§4), not a measurement input — so measurement is independent of subset-build determinism.

### 3.4 Rung-0 calibration (a landable-now improvement)

Replace the flat `0.62`/`1.0`/`0.0` (`_text_render.py:61-75`) with **per-script constants** for
the complex scripts, chosen to stay a safe over-estimate while shrinking waste. My system-font
probe gives first cuts (Arabic ≈ shaped×1.35 → so a per-cp constant near the *isolated* advance
is already safe; Thai ×1.18; Deva ×1.06), but the constant must be calibrated against the
**bundled Noto masters** the audit/bench agents are benchmarking, at rung 0's real target: never
under-estimate. Open question to the bench agent (§8).

### 3.5 Caching (measure is called hundreds of times per render)

Three cache tiers, by lifetime:

| Tier | Key | Lifetime | Why |
|---|---|---|---|
| Run measure | `(run_text, font_px, rung)` | process `lru_cache` | shaping/advance-sum a unique run once; repeated cells (`"0"`,`"1"`…) hit instantly |
| Master faces | script | process (module global) | load each Noto master once; measurement uses the full master, not per-doc |
| Output subset | `(script, frozenset(codepoints))` | **document-scoped** | the 5 ms subset runs once per script per document, not per string — it is an emit step, cached on the render context, never in the process cache (subsets differ per doc) |

Note the **lifetime split**: `get_measurer()` stays a process `lru_cache(maxsize=1)`
(`_text_metrics.py:84`) for rung 0 and for the *master*-backed measurers (masters are
doc-independent). The *subsetter* is document-scoped and lives on `RenderContext`, because its
input codepoint set is the document. Do not conflate them.

### 3.6 Determinism guarantees per rung

- **Rung 0** — pure integer table + `bisect` script lookup → **byte-stable** across machines and
  Python versions (v1's guarantee, `_text_metrics.py:72-81`, extended to the ranges table).
- **Rung 1** — advance-sum from master `hmtx` is a pure table read → **width byte-stable** given
  the master bytes (fontTools advance reads are version-independent). *The embedded subset woff2*
  is **not** cross-version stable (brotli/fontTools encoder) — but the subset is output, not a
  golden input in the default lane (§5).
- **Rung 2** — shaped advances are **deterministic within a pinned harfbuzz version** (probed:
  `IDENTICAL` on reshape) but **may move across HB major versions**. Assert `hb.version_string()`
  in the rung-2 CI lane; treat an HB bump as a deliberate re-pin event.

---

## 4. Font pipeline (rung 1/2) — per-document subsetting

Mirrors the KaTeX base64 precedent (`css_bundler.py:42-70`, gated in `render.py:267-285`), but
built per-document from the master:

1. **Itemize the whole document**, collect `used_codepoints[script]` (the renderer knows every
   string before it emits — the PDF/Typst property).
2. For each script with used codepoints, `Subsetter(...).populate(unicodes=used).subset(master)`
   → woff2 (**~5 ms, ~1.5 KB for a short run**, §1). Keep the layout features the script needs
   (`layout_features=["*"]`: `init/medi/fina/liga/mark/…`) so the *embedded* font shapes correctly
   in the browser even though rung-1 *measurement* ignored them.
3. `inline_intl_font_css()` beside `inline_katex_css()`: emit one `@font-face { font-family:
   "Scriba <Script>"; src: url(data:font/woff2;base64,…) }` per script, `lru_cache`d per render.
4. Pin the run: the emitter tags each non-Latin `<text>`/`<tspan>` with the matching
   `font-family` (already sanitizer-allowed, `whitelist.py:180,185`). Now measured == rendered.

**Master fonts live in the extra, subsets in the output.** The `[intl]` extra either bundles
`scriba/animation/vendor/noto/*` (wheel `package-data`, `pyproject.toml:102-105`) or pulls a
separate `scriba-fonts` wheel. Recommendation: **separate `scriba-fonts` wheel** — keeps the base
sdist/wheel small (its stated goal, `pyproject.toml:73-100`), lets fonts version independently,
and makes the intl download explicit. CJK master is the size outlier (10 MB+); keep CJK at the
1-em rule by default and offer exact-CJK only under an explicit `[cjk]` sub-extra (a per-doc CJK
subset is tiny, but the *master* is the cost).

---

## 5. The goldens-vs-extras CI decision (the hardest question)

**The trap.** If installing `[intl]`/`[shaping]` changes render output, then a developer with the
extra installed produces different bytes than dep-free CI → the 105-file golden corpus
(`tests/golden/examples/test_example_html.py:45`, `SCRIBA_UPDATE_GOLDEN=1`) fails locally for them
and passes in CI, or vice-versa. Shaped widths also move across HB versions (§3.6). Byte-goldens
and a version-coupled shaper are fundamentally incompatible.

**The decision: decouple *capability* from *activation*.**

- **Capability** is presence-detected (`importlib.util.find_spec("uharfbuzz")`).
- **Activation** is an **explicit opt-in**, default OFF: a `RenderContext`/render option
  `intl: "off" | "auto" | "shaping"` (default `"off"`). Rung 1/2 engines run **only** when the
  caller opts in *and* the dep is present; otherwise every render — on every machine, extra
  installed or not — is **rung 0**.

This is justified beyond CI hygiene: activating rung 1 doesn't just change a number, it **embeds
fonts and re-pins intl text from the system font to bundled Noto** — a visible rendering change a
user *should* opt into (the loud warning, §5.4, tells them how). The flag has real semantic
weight; it isn't a metrics micro-toggle.

**Consequences (clean):**
- **Default output is always rung 0** → the 105 goldens are generated dep-free and CI never
  installs the extras. No skip-if-installed hackery in the golden path.
- **Rungs 1/2 get their own small golden set** generated in a pinned-extra CI lane
  (`pytest.mark.skipif(find_spec(...) is None)` — the repo's established gate, e.g.
  `test_ipc_lifecycle.py:76`), plus a **browser-parity tolerance test** (assert Python width
  within ≤1 px / ≤2 % of `getComputedTextLength()`), *not* byte-equality, because subset woff2
  bytes and shaped widths are version-coupled.
- **Rung 2 pins harfbuzz** in that lane and asserts `hb.version_string()`; an HB upgrade is a
  deliberate rung-2 golden refresh, isolated from the main corpus.

**SCRIBA_VERSION impact (subtle, important):** opt-in rungs **do not bump SCRIBA_VERSION** —
default bytes are unchanged, so consumer caches keyed on default output stay valid. Only rung-0
*default* changes bump it. So: the rung-0 work (itemizer + calibrated constants + RTL emission +
cluster-safe wrap) bumps **12 → 13** with a `_version.py` note (`_version.py:6`) and a full
golden regen; rungs 1 and 2 ship **without** a core bump, documented as opt-in extras.

### 5.4 Loud degradation semantics

Rung 0 measuring a complex script heuristically is *safe but silent about being loose*. Make it
loud: on any render whose itemizer found a run in a not-exactly-measured script, emit **one**
structured warning via the existing `_emit_warning(ctx, code, message, severity=...)`
(`core/warnings.py`), a new code (e.g. `W1301`, `severity="info"`) listing the scripts measured
heuristically and pointing at `pip install "scriba-tex[intl]"`. Reuses the collected-warnings
channel already surfaced in `Document.warnings`; no new plumbing.

---

## 6. Thai / scriptless-space wrap decision

`_wrap_label_lines` (`_svg_helpers.py:1671-1735`) only breaks on `space , + =`. Thai/Lao/Khmer
write **without spaces**, so a long Thai caption is *one token* → never wraps → overflows its box
(and exact width doesn't help: the box is right, the text still can't fold). Decision **by
surface and by rung**:

| Surface | Rung 0 (default) | Rung 2+ (optional) |
|---|---|---|
| **Cells / pills / short labels** | **(a) never-wrap + `textLength` squeeze.** They're short; the bench shows ≤10 % squeeze is invisible, ≤25 % legible (`text-width-bench.md` textLength calibration). Keeps the word whole. | same |
| **Captions / long narration** | **(b) grapheme-cluster-safe char wrap.** When a run has no break opportunity, break at **grapheme-cluster** boundaries: a base char keeps its following `Mn/Mc/Me` marks (Thai vowel/tone signs, Indic matras) — no dictionary, breaks *words* but **never tears a cluster** and never overflows. Uses `unicodedata.combining`/`category`, stdlib. | **(c) dictionary segmentation** (ICU/pythainlp) — correct word breaks |

**Why not (c) by default:** it's heavy (MB-scale dictionaries), and dictionary versions are
another nondeterminism source that would couple goldens — so gate it exactly like shaping
(opt-in, own CI lane). **(b) is the honest rung-0 answer**: linguistically imperfect (breaks
mid-word) but structurally correct (clusters intact, no overflow), zero deps, deterministic. Pair
both with the `textLength` clamp as the guaranteed no-overflow backstop.

Cluster-safe wrap is a **rung-0, land-now** change (part of the 12→13 bump).

---

## 7. RTL emission spec

**Today:** the narration `<p>` already carries `dir="auto"` (`_html_stitcher.py:628`) and `dir`
is globally sanitizer-allowed (`whitelist.py:65`). But SVG `<text>`/`<tspan>` — every cell,
label, pill, caption — emit **no** direction, so RTL runs render visually reversed / misaligned.

**Where the decision is made:** at the emitter, **per string, from the itemizer's `base_dir`**
(§3.1) — not a global document mode. `_render_svg_text` (`_text_render.py:171-266`, the single
`<text>` fast path) gains: if the string's first strong run is RTL, emit the SVG presentation
attributes

```
direction="rtl" unicode-bidi="plaintext"
```

`unicode-bidi="plaintext"` gives first-strong base-direction resolution per run (so Latin
numerals inside Arabic sit correctly) — matching what the browser does *and* what the itemizer
measured. **`text-anchor` must follow the base direction**: an RTL label anchors to its visual
right (the existing anchor logic at `_text_render.py:234,278-283` picks the box side; RTL flips
start↔end). Mixed-direction single strings are rare in this corpus; `plaintext` handles them
without per-glyph `dx` arithmetic.

**Sanitizer additions (`whitelist.py`):** add `direction`, `unicode-bidi` to the **`text`**
(`whitelist.py:179-183`) and **`tspan`** (`whitelist.py:184-187`) allowlists as SVG presentation
attributes. They are inert (no URL, no script-execution surface) → the same safety class as the
`data-*`/`aria-*` note in the module docstring (`whitelist.py:9-24`). **Do not** open inline
`style` on `<text>` for this (note the pre-existing tension: `_render_svg_text` already emits
`style="text-anchor:…"` though `style` isn't in the `text` allowlist — use presentation
attributes, the sanitizer-clean route, not more inline style). `dir` needs no addition.

RTL emission is **rung-0** (direction is knowable from Unicode alone, no font needed) → part of
the 12→13 bump. What the audit agent finds *visually* broken (which surfaces, whether stacked
marks clip vertically) refines *where* it's mandatory (§8).

---

## 8. Staged landing plan

### Rung 0 — land now, zero deps, SCRIBA_VERSION 12 → 13
1. **`_script_runs.py`** itemizer + generated `_script_ranges.py` (NFC + UAX #24 attach). Unit
   tests: run boundaries, Common/Inherited attachment, RTL flag.
2. **Run-based `measure_text`**: itemize → per-run engine (shipped-table / 1 em / **calibrated
   per-script constants** from the bench agent). Keep the fallback-never-crash contract.
3. **RTL emission** in `_render_svg_text` + `direction`/`unicode-bidi` sanitizer adds
   (`whitelist.py:179-187`).
4. **Cluster-safe char wrap** in `_wrap_label_lines` for scriptless-space runs + `textLength`
   squeeze for short surfaces (coordinate with v1's Option-C `textLength`/`lengthAdjust`
   sanitizer work).
5. **Loud warning** `W1301` via `_emit_warning` (`core/warnings.py`).
6. **Regen 105 goldens** (`SCRIBA_UPDATE_GOLDEN=1`), bump `SCRIBA_VERSION` 12→13 + `_version.py`
   note + `__version__`, one atomic commit.
   *Tests:* itemizer units; wrap cluster-safety property test (never tears a combining mark);
   RTL snapshot; warning-emitted test.

### Rung 1 — `[intl]` extra, opt-in flag, **no SCRIBA_VERSION bump**
1. Add optional-dependency group `intl = ["fonttools>=4.4"]` + `scriba-fonts` wheel (masters);
   wheel `package-data` for any bundled vendor fonts (`pyproject.toml:102-105`).
2. `IntlFontMeasurer` (advance-sum from master, per-run `lru_cache`) + document-scoped
   `Subsetter` on `RenderContext` + `inline_intl_font_css()` (`css_bundler.py` sibling) + emitter
   pin.
3. Render option `intl="off"|"auto"` (default `"off"`); `find_spec` capability check.
4. **Separate rung-1 golden set** in a `skipif(find_spec is None)` lane + browser-parity tolerance
   test (≤1 px / ≤2 %).
   *Docs:* the extra, the flag, the "install for exact intl" story (ties to `W1301`).

### Rung 2 — `[shaping]` extra, opt-in, **no SCRIBA_VERSION bump**
1. `shaping = ["scriba-tex[intl]", "uharfbuzz>=0.40"]`.
2. `ShapedMeasurer` (HB shaped advance, per-run cache) — collapses Arabic +35 % / Indic +6 %
   over-reserve to exact.
3. **Pin harfbuzz** in the rung-2 CI lane; assert `hb.version_string()`; rung-2 goldens are
   tolerance-based / HB-version-pinned. Document the HB-upgrade → re-pin policy.

---

## 9. Open questions for the other two agents' data

**To the shaping-bench / optional-dep agent:**
1. **Cross-HB-version width drift** for Arabic/Thai/Devanagari across HB 8→…→14 — magnitude sets
   the rung-2 golden tolerance (or forces a hard pin). My within-version reshape was byte-identical;
   I have no cross-version delta.
2. **Rung-0 per-script over-estimate constants** measured against the **bundled Noto masters**
   (not the system GeezaPro/Kohinoor/Thonburi I probed): the smallest per-cp constant per script
   that never under-estimates shaped width. My system-font ratios (Arabic 1.35 / Thai 1.18 / Deva
   1.06) are the ballpark, not the answer.
3. **Master-font selection + subset-size budget** per script for the `[intl]`/`scriba-fonts`
   wheel (Noto Naskh Arabic vs Kufi; Noto Sans Thai/Devanagari sizes), and whether a `[cjk]`
   sub-extra with per-doc subsetting is worth it vs the 1-em rule.
4. Is `hb.version_string()` (I read 14.2.1) the right thing to assert in goldens, or does uharfbuzz
   expose a shaping-model/OT-version stamp that's more stable?

**To the RTL / complex-script rendering-audit agent:**
1. **Which surfaces visually break today** for RTL/complex (cells vs captions vs pills vs graph
   nodes)? Decides where §7 RTL emission is *mandatory* vs cosmetic.
2. Does the browser's own bidi already fix the narration `<p dir="auto">`
   (`_html_stitcher.py:628`) so that **only SVG `<text>` needs the new attributes**?
3. **Do stacked Thai/Indic marks clip vertically?** `line_box_h = font_px + 2`
   (`_text_render.py:38-41`) — if marks overshoot, the *height* metric also needs script-awareness,
   which this doc scopes to width only.
4. Confirm the **`textLength` squeeze renders acceptably for Thai/Arabic** — the bench calibrated
   distortion on *Vietnamese* only (`text-width-bench.md`); §6 leans on it for scriptless-space
   cells and I have no complex-script screenshot.

---

### Appendix — key citations
- Shipped v1 measurer + fallback ladder: `scriba/animation/primitives/_text_metrics.py:46-100`
- Heuristic engine (rung-0 base): `scriba/animation/primitives/_text_render.py:61-118`
- `measure_text` call sites (14 px cell seam): `array.py:165`, `stack.py:141`,
  `queue.py:147,178,203`, `linkedlist.py:130`
- Wrap loop (space/`,`/`+`/`=` only): `_svg_helpers.py:1671-1735`; pill sizing `1384-1413`
- `<text>` emitter + anchor logic: `_text_render.py:171-266`
- Sanitizer allowlists (`dir` global; `text`/`tspan` need `direction`/`unicode-bidi`):
  `sanitize/whitelist.py:65,179-187`
- Existing `dir="auto"` precedent: `animation/_html_stitcher.py:628`
- Warning channel: `core/warnings.py` `_emit_warning`
- KaTeX base64 embed + Opt-3 gate precedent: `core/css_bundler.py:42-70`, `render.py:267-285`
- Deps (pygments only; no fontTools/uharfbuzz today): `pyproject.toml:33-35`; wheel package-data
  `:102-105`; sdist size discipline `:73-100`
- Golden mechanism: `tests/golden/examples/test_example_html.py:45`; skipif precedent
  `tests/unit/test_ipc_lifecycle.py:76`
- Version + notes: `scriba/_version.py:6` (SCRIBA_VERSION 12)
- **Probes (this session, scratchpad `ftenv`):** `allscript_probe.py` — naive/shaped ratios,
  reshape determinism, and the 4.6–9.4 ms in-process Arabic subset.
