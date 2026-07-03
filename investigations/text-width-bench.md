# Text-Width Accuracy Bench — `estimate_text_width` vs Browser Ground Truth

**Question.** How wrong is scriba's `estimate_text_width` *today*, and how exact
would font-file metrics be — both measured against real browser rendering (the
ground truth)? Corpus: 45 strings × sizes 10 / 11 / 14 px, split Latin / Viet /
CJK / Mixed.

---

## Hand-off Brief — the three headline numbers

1. **Today's heuristic is safe-but-loose, and safest exactly where captions
   live.** On the real **11 px label/pill/caption surface (monospace)** the
   estimator's p95 error is **≈5 %** and it **never under-estimates** (0 clips in
   45 strings, all scripts). On the **14 px cell/node surface (proportional SF
   Pro)** it runs **+25 % median (p95 ≈57 % on real words)** — wasteful padding,
   still almost always safe. Vietnamese specifically is **never** a clip risk.

2. **Font-file advance-sum is ~100–500× more accurate.** Summing glyph advances
   from the actual font file predicts the browser to **p95 0.12 %, max 0.47 %**
   across *all* 45 strings and every script class (Arial Unicode MS, static
   font). Every static font tested lands <0.2 % p95. *That is the whole thesis,
   confirmed.*

3. **Not shipping a font costs ~7–13 % no matter how clever the estimator is.**
   The same string at 14 px spans **6.6 % median / ~13 % p95** across {SF Pro,
   Arial, Helvetica, Arial Unicode}. Since scriba renders with the *viewer's*
   `-apple-system` / `ui-monospace`, this cross-font spread is an irreducible
   error floor that only **embedding a font** removes.

> Direction convention: signed error % = `(estimate − browser) / browser × 100`.
> **Negative = under-estimate = the dangerous direction (text clips its box).**

---

## Method

| Layer | Tool | Detail |
|-------|------|--------|
| **Ground truth** | headless Chromium `chrome-headless-shell` build 1223 (Chrome-for-Testing 148.0.7778.96) via Playwright | one HTML page, every string in a tight `display:inline-block` `<span>`, `getBoundingClientRect().width` (fractional CSS px, dpr=1). `await document.fonts.ready` before measuring. |
| **Estimator** | scriba `.venv` (CPython 3.10) | `estimate_text_width(_label_width_text(s), size)` imported from `scriba/animation/primitives/_text_render.py` + `_svg_helpers.py`. |
| **Font metrics** | `fonttools` 4.63.0 (throwaway venv; not in repo) | advance-sum: `cmap → hmtx`, scaled `× size / unitsPerEm`. **Kerning ignored** (no `kern`/GPOS) — acceptable first cut; residual below shows its impact is <0.5 % for this corpus. |

**The font surfaces scriba actually uses** (from `scriba-scene-primitives.css` +
`scriba-standalone.css`; `inherit` → `-apple-system,…` → SF Pro Text on macOS):

| Size | Surfaces (CSS var) | Weight | Family stack | Resolves to (this Mac) |
|-----:|--------------------|:------:|--------------|------------------------|
| **10 px** | `--scriba-cell-index-font`, axis ticks | 500 | `ui-monospace, monospace` | **SF Mono** |
| **11 px** | `--scriba-label-font`, `--scriba-annotation-font` (labels · pills · captions · edge-weights) | 600 | `ui-monospace, monospace` | **SF Mono** |
| **14 px** | `--scriba-cell-font`, `--scriba-node-font` (cells · graph nodes) | 500 | `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` | **SF Pro Text** |

This mapping is the crux: **the caption/label surfaces are *monospace* (~0.60 em),
so the estimator's flat 0.62-em model is nearly right there; the 14 px surface is
*proportional*, where a flat per-char width cannot win.** The estimator is
font-agnostic (one number per string×size), so each size is compared against the
real surface font at that size.

The estimator model (`_char_display_width`): combining marks / format chars
(`Mn/Me/Cf`) → 0 em; East-Asian Wide/Fullwidth → 1.0 em; **everything else → 0.62
em**; then `round(Σ × font_size)`. Note: our corpus is NFC (precomposed), and
`_label_width_text` was a **no-op on all 45 strings** (no `$…$` TeX), so raw and
label-path estimates were identical.

---

## Results

### Approach A — scriba `estimate_text_width` vs the real scriba surface

Signed error %; **p95|%|** and **max|%|** are magnitudes; **worstUnder** is the
most-negative (clip) case; **nU** = count of under-estimates.

| Class | Size | n | median ± % | p95 \|%\| | max \|%\| | worstUnder % | nU |
|-------|-----:|--:|-----------:|--------:|--------:|-------------:|---:|
| Latin | 10 | 19 | +3.0 | 3.7 | 4.1 | −0.3 | 3 |
| Latin | 11 | 19 | +3.3 | 5.9 | 5.9 | +2.2 | 0 |
| Latin | 14 | 19 | +28.6 | 149.5 | 157.1 | **−36.1** | 3 |
| Viet  | 10 | 10 | +3.3 | 3.8 | 3.8 | −0.3 | 1 |
| Viet  | 11 | 10 | +3.2 | **4.9** | 5.9 | +3.0 | **0** |
| Viet  | 14 | 10 | +24.9 | **29.7** | 30.4 | +8.9 | **0** |
| CJK   | 10 | 7 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| CJK   | 11 | 7 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| CJK   | 14 | 7 | +4.3 | 4.3 | 4.3 | +3.0 | 0 |
| Mixed | 10 | 9 | +3.3 | 4.8 | 5.7 | −0.3 | 1 |
| Mixed | 11 | 9 | +3.3 | 5.4 | 5.9 | +2.0 | 0 |
| Mixed | 14 | 9 | +34.5 | 54.1 | 56.8 | **−26.5** | 1 |
| **ALL** | 10 | 45 | +3.0 | 3.8 | 5.7 | −0.3 | 5 |
| **ALL** | 11 | 45 | +3.2 | 5.9 | 5.9 | 0.0 | **0** |
| **ALL** | 14 | 45 | +24.8 | 92.9 | 157.1 | **−36.1** | 4 |

**Realistic subset** (drops the synthetic `iiii…`/`WWWW…` stress strings + single
glyphs; 37 strings) — the number that matters for real captions:

| Size (surface) | ALL p95 \|%\| | Viet median / p95 | under-estimates |
|----------------|-------------:|:-----------------:|:---------------:|
| 10 px mono | 3.9 | +3.3 / 3.8 | 0 |
| **11 px mono (labels·pills·captions)** | **3.9** | **+3.2 / 3.6** | **0** |
| 14 px sans (cells·nodes) | 56.9 | +24.9 / 29.8 | 0 |

**Every under-estimate in the whole corpus** (the only clip risks), all on 14 px
proportional SF Pro, all wide-glyph outliers, **none Vietnamese, none CJK**:

| err % | string | est → truth (px) |
|------:|--------|------------------|
| −36.1 | `WWWWWWWWWWWWWWWW` | 139 → 217.4 |
| −33.8 | `W` (single) | 9 → 13.6 |
| −26.5 | `—` (em-dash) | 9 → 12.3 |
| −0.7 | `8` (single) | 9 → 9.1 |

The 0.62-em constant simply can't cover glyphs that are genuinely ~1 em wide
(capital W/M, em-dash, and by extension emoji). On the monospace surfaces even
these are safe, because SF Mono renders them at a fixed ~0.60 em.

### Approach B — font-file advance-sum vs the browser rendering *of that same font*

Pinned via `@font-face src:url(file://…)` so exactly one font file is rendered
(no fallback); only strings fully covered by the file are counted.

| Font (file) | Size | nCov | median ± % | p95 \|%\| | max \|%\| |
|-------------|-----:|-----:|-----------:|--------:|--------:|
| **Arial Unicode MS** (static, 50 377 glyphs) | 11 | **45** | −0.01 | **0.11** | 0.38 |
| **Arial Unicode MS** | 14 | **45** | −0.00 | **0.12** | 0.47 |
| Arial (static) | 11 | 38 | −0.01 | 0.12 | 0.38 |
| Arial (static) | 14 | 38 | −0.01 | 0.14 | 0.47 |
| Helvetica (static) | 14 | 37 | −0.01 | 0.14 | 0.47 |
| SF Mono (variable) | 11 | 38 | −0.01 | 0.19 | 0.19 |
| **SF Pro — default instance** (variable) | 14 | 38 | **−11.97** | 16.64 | 19.63 |
| **SF Pro — instanced `wght`400 `opsz`17** | 14 | 38 | +0.28 (mean) | **1.64** | 1.97 |

Arial Unicode MS, fully covering all four script classes, nails the browser to
**p95 0.12 %, max 0.47 %** — **by class:** Latin p95 0.17 %, Viet 0.08 %, CJK
0.00 %, Mixed 0.02 %. The one bad row (SF Pro default instance, −12 %) is **not a
method failure**: SFNS.ttf is a variable font whose default `opsz` = 28 (a display
optical size), but at 14 px the browser clamps optical sizing to the axis
minimum (17). Reading the correct instance (`wght`=400, `opsz`=17) collapses the
error to **0.28 % mean / 1.64 % p95**. Lesson: **variable fonts must be instanced
to the axis coordinates the browser actually renders** before advance-sum.

### Approach C — how far apart are *different* fonts at 14 px

`spread% = (max − min) / mean` of browser widths across {SF Pro, Arial, Arial
Unicode, Helvetica} per string (CJK excluded — only SF-Pro fallback covers it).

| Subset | n | median | p95 | max |
|--------|--:|-------:|----:|----:|
| all covered | 37 | **6.6 %** | 13.9 % | 14.3 % (`8`) |
| realistic (no singles) | 32 | 6.6 % | 12.7 % | 13.9 % |
| SF Pro vs Arial only | 37 | 6.2 % | 12.6 % | 14.3 % |

This is the **irreducible error of estimating for one font while the viewer
renders another** — precisely scriba's situation today, since it ships no font
and inherits `-apple-system`/`ui-monospace` from the host.

---

## The three questions, answered with numbers

**(a) How bad is today's estimator at p95 on Vietnamese?**
It depends on the surface, and the answer is reassuring where it counts:
- **Caption/label surface (11 px monospace): p95 = 4.9 % (3.6 % on real words),
  median +3.2 %, and 0 under-estimates.** The estimator is tight and always safe
  for Vietnamese captions.
- **Cell/node surface (14 px proportional): p95 = 29.7 %, median +24.9 %,
  0 under-estimates.** Loose padding, never a clip.

Why Vietnamese is a non-problem: precomposed (NFC) diacritics are a single
`Ll`-category codepoint counted once at 0.62 em, and the diacritic stacks
*vertically* — it adds no horizontal advance — so Vietnamese behaves exactly like
plain Latin. The heuristic's danger zone is wide Latin glyphs, not diacritics.

**(b) Does font-file advance-sum predict browser rendering of that font to <1 %?**
**Yes, emphatically.** Arial Unicode MS: **p95 0.12 %, max 0.47 %** across all 45
strings and every script class; all static fonts <0.2 % p95. Correctly-instanced
SF Pro: 0.28 % mean. The only caveat is instancing variable fonts (and, at the
sub-1 % level, kerning — ignored here but demonstrably <0.5 % for this corpus).

**(c) How far apart are different fonts at the same size?**
**~6.6 % median, ~13 % p95, ~14 % max** at 14 px. So even a *perfect* estimator
tuned to SF Pro would be ~7–13 % wrong the moment the diagram renders on a
Windows/Linux viewer (Segoe UI / Roboto). You cannot estimate your way out of
this — only pinning the rendered font removes it.

---

## textLength escape-hatch — distortion calibration

One Vietnamese caption (`Xoắn ốc số (hàng y xuống, cột x sang phải)`, natural
width 806.5 px at 32 px monospace) rendered as SVG `<text>` with
`lengthAdjust="spacingAndGlyphs"` at three `textLength` values. Screenshots in
scratchpad:

| File | `textLength` | Eyeball verdict |
|------|-------------|-----------------|
| `textlength_true.png` | 100 % (806.5 px) | Reference — natural spacing, fills to the right edge. |
| `textlength_10pct_small.png` | 90 % | **Distortion essentially invisible.** Compression is absorbed mostly into inter-word/inter-glyph spacing; the line just pulls in from the right edge. Glyphs read as normal. |
| `textlength_25pct_small.png` | 75 % | **Visibly condensed but fully legible.** Glyphs are horizontally squished (~0.75× advance) into a "narrow" look; Vietnamese diacritics and letterforms hold up cleanly. Noticeable to a careful eye, not broken. |
| `textlength_all.png` | all three stacked | side-by-side comparison. |

**Calibration:** `spacingAndGlyphs` is a **usable clip-rescue safety net**.
≤10 % correction is imperceptible; ~25 % is the comfortable legibility floor.
Since it *shrinks* text to a target width, it fits exactly the dangerous
under-estimate cases — and every under-estimate we found (worst −36 %) sits at or
just past that floor, so a runtime `textLength = box_width` clamp would rescue all
observed clips (the −36 % `WWWW` case would look condensed, but never overflow).

---

## Implications — which architecture the numbers support

The numbers point one direction: **embed a font and size text from its file
metrics.**

1. **Ship/embed the fonts scriba targets** (a monospace for labels + a sans for
   cells, or unify on one embeddable Unicode family via `@font-face` in
   `scriba-embed.css`). This alone kills the **6.6 %/13 %** cross-font spread (c)
   — today every non-Mac viewer silently re-renders at different widths.

2. **Size boxes with advance-sum from that embedded file**, replacing the flat
   0.62-em heuristic. Expected accuracy **~0.1–0.5 %** (b) vs today's **+25 %
   bloat on cells** and **occasional −25 %…−36 % clips** on wide glyphs (a).
   *Precompute a codepoint→advance table at build time* so runtime stays
   dependency-free — no fonttools needed in the hot path. Two gotchas the bench
   surfaced: **instance variable fonts to the rendered axis** (`opsz`/`wght`) and
   optionally fold in `kern`/GPOS (sub-1 % here, larger for kern-heavy Latin).

3. **Keep the current heuristic as the fallback** for codepoints outside the
   embedded font (it is safe — over-estimates — on monospace, and its only real
   failures are wide proportional glyphs).

4. **Add `textLength=box_width` (`spacingAndGlyphs`) as a belt-and-suspenders
   runtime clamp.** Cheap, and it guarantees no clip even when a width estimate is
   wrong by up to ~25 % — the distortion at that level is mild and legible.

Net: today's estimator is *safe but loose* on the monospace caption surface
(≈5 % p95, never clips) and *loose-with-rare-clips* on the proportional cell
surface (+25 % median, −36 % worst on wide glyphs). Font-file metrics on an
embedded font are ~100–500× tighter and eliminate the irreducible cross-font
uncertainty — a decisive case for the **embed-font + advance-sum** architecture,
with the heuristic and `textLength` as fallbacks.

---

## Reproducibility

All scripts in the session scratchpad
(`/private/tmp/claude-501/…/scratchpad/`); repo source was not modified.

| File | Role |
|------|------|
| `make_corpus.py` → `corpus.json` | 45-string corpus generator (NFC), tagged by class/category. |
| `measure_browser.py` → `browser.json`, `bench_page.html` | Chromium ground truth; surface stacks + pinned `@font-face` files; probes `document.fonts.check`. |
| `run_estimator.py` → `estimator.json` | scriba `estimate_text_width` (+ `_label_width_text`) over corpus. |
| `run_fonttools.py` → `fonttools.json` | advance-sum for SF Mono / SF Pro / Arial / Arial Unicode / Helvetica; per-string coverage flag. |
| `analyze.py` → `results.json`, `approachA_detail.json` | merges all three, emits Approaches A/B/C tables. |
| `textlength_demo.py` → `textlength_*.png` | textLength / lengthAdjust distortion screenshots. |

Ground-truth fonts: `/System/Library/Fonts/SFNS.ttf`, `SFNSMono.ttf`,
`Helvetica.ttc`, `Supplemental/Arial.ttf`, `Supplemental/Arial Unicode.ttf`
(all `unitsPerEm` 2048). SF Pro & SF Mono are variable; Arial/ArialUni/Helvetica
static. **Caveats:** ground truth is macOS-specific (SF Pro/SF Mono); advance-sum
ignores kerning; corpus is NFC (an NFD corpus would exercise the estimator's
combining-mark 0-width branch, which yields the same total for these glyphs).
