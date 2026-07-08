# Investigation: Annotation-pill text face i18n — structural fix for Vietnamese zebra

## Hand-off Brief

1. **What happened.** (Confirmed) Pill text runs paint KaTeX_SansSerif Bold — a 120-glyph face with 0/90 Vietnamese coverage — so diacritic glyphs fall per-glyph to ui-monospace bold: mixed faces inside one word.
2. **Where the case stands.** Concluded. Three parallel research agents graded all candidates; root cause and structural fix direction Confirmed.
3. **What's needed next.** Decide the weight strategy (the single open design call), then implement candidate A via bmad-quick-dev.

## Case Info

| Field            | Value |
| ---------------- | ----- |
| Ticket           | follow-up to JudgeZone #8 / spec-fix-annot-pill-font-clash |
| Date opened      | 2026-07-08 |
| Status           | Concluded (pending weight decision) |
| System           | scriba @ b119f0a, KaTeX 0.16.11, Inter subset upm 2048 |
| Evidence sources | woff2 cmap dumps (fontTools), katex_advances.json, inter_advances.json, source, render pipeline, golden corpus |

## Problem Statement

Label thuần Việt (`"đã thăm"`) zebra: base-ASCII sans, diacritics mono bold. Structural fix required; constraints: browser-free exact measurement, no clipping, golden determinism.

## Evidence Inventory

| Source | Status | Notes |
| ------ | ------ | ----- |
| KaTeX_SansSerif-Bold coverage | Available (Confirmed) | 120 glyphs; 0/90 VN (U+1EA0–1EF9); no ·/→/</≮ |
| Inter subset coverage | Available (Confirmed) | 759 glyphs; **90/90 VN**, đ ơ ư Ơ Ư ₫ · dashes; woff2 cmap ⇄ inter_advances.json in sync. Missing: math ops → ≤ ≥ ≠ ≮ − ∞ (by design; live in `$...$`) |
| Inter weight semantics | Available (Confirmed) | static 400 master, no fvar/HVAR/gvar; @font-face `400 500 600` (css_bundler.py:59); advances weight-invariant |
| Pill inline weights | Available (Confirmed) | per-kind stamps override token: info/muted=500, warn/error=600, good/path=**700** (_svg_helpers.py:1929-1978) |
| Paint availability | Available (Confirmed) | `inline_text_font_css()` unconditional first CSS part (render.py:260); KaTeX css conditional `_has_math` (render.py:281-283) |
| Pairing precedent | Available (Confirmed) | Scriba Sans + KaTeX_Main already the norm: equation.py:371, _text_render.py:329,383. Pill is the outlier |
| Vertical metrics vs face | Available (Confirmed) | pill height purely font_px-derived (`line_height=l_font_px+2`, pads); face affects width only |
| NFC drift | Available (Confirmed) | sans_text_width does not normalize: decomposed "đã thăm" 41.27 vs precomposed 43.36px; ShippedFontMeasurer NFC-normalizes |

## Timeline of Events

| Time | Event | Source | Confidence |
| ---- | ----- | ------ | ---------- |
| 0.22.1 | mono pin + KaTeX_Main advance-sum for math runs | changelog / spec | Confirmed |
| b119f0a (2026-07-08) | pill/link/note text runs → KaTeX_SansSerif Bold + SansSerif-Bold table | commit | Confirmed |
| 2026-07-08 | Vietnamese zebra identified during release verification | this case | Confirmed |

## Confirmed Findings

### Finding 1: zebra mechanism
**Evidence:** scriba-scene-primitives.css:103 (stack `KaTeX_SansSerif, ui-monospace, monospace`); per-character CSS font matching; SansSerif-Bold cmap 0/90 VN.
**Detail:** Uncovered glyphs paint mono bold beside sans glyphs in one run.

### Finding 2: Inter subset fully covers the text-run case
**Evidence:** build_text_font.py:37 subset ranges incl. U+1EA0-1EF9, U+01A0-01B0, U+20AB; fontTools cmap dump 90/90; inter_advances.json keys match woff2 (sha-verified by agent).
**Detail:** Missing set = math operators that belong in `$...$` (measured by symbol_em, painted KaTeX in math runs).

### Finding 3: Scriba-Sans-next-to-KaTeX is the established pairing
**Evidence:** equation.py:371; _text_render.py:329,383 (`--scriba-fo-font-family: "Scriba Sans", ...` css:84).
**Detail:** Equations and cell/node values already pair Inter text with KaTeX_Main math in one FO. The pill's KaTeX-sans text is the odd one out.

### Finding 4: weight is the only exactness gate
**Evidence:** static 400 master (no variable axes, OS/2 400); folabel-fonts.md:175-187 (Chrome renders declared-600 as regular, no synth); good/path stamp 700 (outside declared range → faux-bold synthesis → paint wider than table → under-measure).
**Detail:** Weights ≤600 = regular strokes, advances = table = exact. Weight 700 = synthesis = clip risk.

### Finding 5: candidate A dissolves the deferred note-math mismatch
**Evidence:** measure_value_text (_text_metrics.py:222-239) uses base=measure_text when mono=False; note calls mono=False (_frame_renderer.py:1540,1553).
**Detail:** Under A, paint face == measure_text face → base and stripped-fallback terms align with zero signature change.

## Deduced Conclusions

### Deduction 1: structural fix = adopt the house text oracle
**Based on:** Findings 2, 3, 5 + NFC drift + blast report (single oracle replaces sans_text_width special case).
**Reasoning:** The codebase already owns an exact, NFC-correct, VN-complete, unconditionally-embedded text oracle (Scriba Sans + inter_advances.json) used by every other mixed text+math surface. Re-pointing annotation labels at it removes the parallel oracle, the deferral, and the zebra in one move.
**Conclusion:** Candidate A is the structural fix; B-variants are patches around a second oracle.

## Hypothesized Paths

### Hypothesis 1: switch pill text runs to "Scriba Sans" (Inter)
**Status:** Confirmed (feasible; gated on weight decision)
**Resolution:** research-inter verdict feasible-with-caveats; caveat #1 = weight (see Finding 4); float advance-sum needed to avoid per-segment double rounding; fallback tail choice low-impact.

### Hypothesis 2: extend KaTeX_SansSerif with Vietnamese glyphs
**Status:** Refuted
**Resolution:** No upstream VN-capable KaTeX face; forged glyphs unmeasurable via build_katex_metrics.py (slices katex.min.js fontMetricsData); violates vendored-asset boundaries; breaks on vendor refresh.

### Hypothesis 3: CSS fallback layering only (`KaTeX_SansSerif, "Scriba Sans", ...`)
**Status:** Refuted as the structural fix (viable as cosmetic patch only)
**Resolution:** Deterministic and can be made measurement-exact (~4 lines in sans_text_width), but keeps two sans oracles + NFC drift + deferral, and introduces weight zebra (KaTeX bold beside Inter regular, x-height +19%) precisely on Vietnamese words. system-ui variant strictly worse (loses exactness + determinism; no screenshot CI to catch drift).

## Missing Evidence

| Gap | Impact | How to Obtain |
| --- | ------ | ------------- |
| none blocking | — | — |

## Source Code Trace

| Element | Detail |
| ------- | ------ |
| Error origin | scriba-scene-primitives.css:103 fallback stack × KaTeX_SansSerif coverage |
| Trigger | pill/link/note label with codepoints outside KaTeX_SansSerif |
| Condition | per-glyph CSS fallback to ui-monospace |
| Related files | _text_metrics.py (measure_label_line :162, ShippedFontMeasurer :113, measure_value_text :222), _math_metrics.py (sans_text_width :238 — deletable under A), _svg_helpers.py (:1438,:1587,:1929-1978,:2113,:3211), _frame_renderer.py (:1391,:1559,:1575), css_bundler.py (:52-60), render.py (:260), build_text_font.py (:37,:65), scriba-scene-primitives.css (:84,:103,:541-547), docs/spec/animation-css.md §2.1/§7.1 |

## Conclusion

**Confidence:** High

Root cause Confirmed: the b119f0a face choice picked a math-family sans whose coverage is inherently ASCII+Greek; any coverage gap surfaces as per-glyph fallback zebra. The structural fix (Confirmed feasible) is to re-point annotation-label text runs at the existing house oracle — "Scriba Sans" paint + ShippedFontMeasurer float advance-sum — matching what equations and cell values already do. One design decision remains open (weight), one implementation detail is mandatory (float advance-sum export), golden churn ~107 files, pill heights provably unchanged.

## Recommended Next Steps

### Fix direction (candidate A, gated on weight choice)

- **A1 — clamp weights to ≤600 (recommended):** demote good/path inline stamps 700→600; all pill text paints the regular master (repo-confirmed no synthesis ≤600), advances exact, zero new assets. Pill text weight matches cells (the diagram's voice); kind hierarchy stays carried by color+halo. Cheapest exact path.
- **A2 — vendor Inter-SemiBold subset + second advance table:** preserves a real bold voice at 600/700; cost ≈ +34KB data-URI per rendered HTML + build_text_font.py + measurer face-by-weight complexity.
- Complementary hardening (either): `textLength`/`lengthAdjust` backstop on pill text (prior-art ranked #1) — guarantees no overflow independent of measurement.

### Diagnostic
None required; all claims Confirmed from vendored assets.

## Reproduction Plan

Render `\annotate{...}{label="đã thăm", color=good}` at b119f0a → diacritics paint mono bold beside sans (zebra). Post-fix: whole run paints Scriba Sans; pill width == measurer prediction; decomposed input measures identically to precomposed (NFC).

## Side Findings

- (Confirmed) sans_text_width lacks NFC normalization — decomposed VN input under-measures ~2px/word at 11px (latent, fixed by A, must be patched if B ever shipped).
- (Confirmed) `font-weight: 400 500 600` three-value descriptor at css_bundler.py:59 is nonstandard (range takes 2 values) — browsers appear lenient, but worth normalizing to `400 600` when touched.
- (Confirmed) No screenshot/pixel CI exists; HTML-byte goldens only — platform-dependent CSS fallbacks are invisible to CI (argues against system-ui variants).
- (Confirmed) KaTeX CSS embedding is conditional on `_has_math` (render.py:281-283) — earlier session note said "unconditional"; corrected here. Pills always co-occur with `_has_math=true` docs in practice, and under A the pill face no longer depends on KaTeX CSS at all.
