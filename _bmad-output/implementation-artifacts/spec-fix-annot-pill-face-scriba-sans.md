---
title: 'Annotation labels adopt the house text oracle (Scriba Sans) — kill Vietnamese zebra'
type: 'bugfix'
created: '2026-07-08'
status: 'done'
context: ['{project-root}/_bmad-output/implementation-artifacts/investigations/annot-pill-i18n-face-investigation.md']
baseline_commit: 'b119f0a602f98d8a5efaff03a4442442229f7f8d'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Annotation pill/link/note text runs paint KaTeX_SansSerif Bold (120 glyphs, 0/90 Vietnamese) — diacritic glyphs fall per-glyph to ui-monospace bold, mixing faces inside one word (`"đã thăm"` zebra). A parallel measurement oracle (`sans_text_width`) duplicates the house one and lacks NFC normalization.

**Approach:** Investigation candidate A1 (Confirmed, High confidence): re-point annotation-label text runs at the existing house oracle — paint "Scriba Sans" (Inter subset: 759 glyphs, 90/90 VN, unconditionally embedded) and measure via a float ShippedFontMeasurer advance-sum (NFC-correct). Clamp `good`/`path` inline weights 700→600 so the static 400 master stays synthesis-free (repo-confirmed: ≤600 renders regular, advances == table → exact, no clip). Delete `sans_text_width`. This matches the pairing equations and cell values already use (Scriba Sans text beside KaTeX math).

## Boundaries & Constraints

**Always:**
- Measurement must model the exact face CSS selects, per painted surface.
- New float text-run measurer: NFC-normalize, per-char Inter advance, fallback `symbol_em` (KaTeX) then `_char_display_width` heuristic — never zero, never crash; single int round at line level (no per-segment double rounding).
- `text_face` stays opt-in on `measure_label_line`; default `"mono"` byte-identical for all non-annotation callers.
- Golden updates only via `SCRIBA_UPDATE_GOLDEN=1`; verify diffs confined to annotation markup + embedded CSS before accepting.
- Remove code orphaned by THIS change (`sans_text_width` and, if then-unused, its imports/tests).

**Ask First:**
- If any pill kind's visual weight loss (bold→regular) looks illegible at 11px against the halo in a rendered sample, HALT with a screenshot-in-words before golden regen.
- If clamping 700→600 requires touching non-annotation consumers of `ARROW_STYLES`, HALT.

**Never:**
- No new font files or @font-face (A1 explicitly rejects vendoring a bold master).
- Do NOT change `measure_text`'s existing int API (cells depend on it) — add a float path alongside.
- Do NOT change `estimate_text_width`, `_wrap_label_lines` formulas, `position_label_height_above/below`, or `measure_value_text`'s signature.
- Do NOT touch the `math_rendered=False` raw-TeX fallback or the mono default path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Vietnamese label | `label="đã thăm"` | Whole run paints Scriba Sans (no zebra); width = Inter advance-sum | N/A |
| NFC drift | same label, decomposed vs precomposed input | identical measured width (NFC normalize) | N/A |
| Mixed label | `label="$1 < 3$ · exit"` | math run KaTeX (unchanged); text run Scriba Sans; width = katex(math)+inter(text) | N/A |
| Math-op literal in text run | `label="A → B"` (no `$`) | measured via symbol_em (real KaTeX advance) or heuristic; painted via CSS tail — conservative, never clips | silent fallback |
| Weight clamp | `color=good` / `color=path` pill | inline weight ≤600; paint = regular master; measured == painted advances | N/A |
| Non-annotation surfaces | any | byte-identical (mono default untouched) | N/A |

</frozen-after-approval>

## Code Map

- `scriba/animation/primitives/_text_metrics.py:113-140,162-204,222-239` -- ShippedFontMeasurer (NFC, symbol_em fallback), `measure_label_line` (`text_face` routing), `measure_value_text` (aligns for free under A — base==paint)
- `scriba/animation/primitives/_math_metrics.py:238-265` -- `sans_text_width` to DELETE (+ `__all__`, `_char_display_width` import if orphaned)
- `scriba/animation/primitives/_svg_helpers.py:1438,1587,1929-1978,2113,3211` -- 4 measure sites (face value) + ARROW_STYLES per-kind weights (good/path 700→600)
- `scriba/animation/_frame_renderer.py:1391,1559,1575` -- link + note measure sites (face value)
- `scriba/animation/static/scriba-scene-primitives.css:84,103,533-547` -- token → `600 11px "Scriba Sans", <fo-family tail>`; comments rewrite (width oracle = the cell oracle)
- `scriba/core/css_bundler.py:52-60` -- @font-face already unconditional (render.py:260); normalize nonstandard `font-weight: 400 500 600` → `400 600` while touching
- `tests/unit/test_pill_math_wrap.py:128-191` -- TestKatexSansTextFace → rewrite for scriba-sans contract
- `tests/unit/test_link_label_obstacle.py:197-220`, `tests/unit/test_note_command.py:344-375` -- face-name spy asserts
- `docs/spec/animation-css.md` §2.1 (:88-92) + §7.1 (:793-804) -- font contract
- `_bmad-output/implementation-artifacts/deferred-work.md` -- note math-branch entry: mark resolved-by-alignment (residual = benign over-measure on math term)
- `tests/golden/examples/`, `tests/doc_coverage/` -- byte goldens (~107 files regen)

## Tasks & Acceptance

**Execution:**
- [x] `scriba/animation/primitives/_text_metrics.py` -- add float text-run measurer beside `measure_text` (NFC → Inter advance/upm × font_px per char; missing → `symbol_em` → `_char_display_width`); route `measure_label_line` `text_face="scriba-sans"` to it; drop the `"katex-sans"` branch -- single house oracle, no double rounding
- [x] `scriba/animation/primitives/_math_metrics.py` -- delete `sans_text_width` (+`__all__` entry, orphaned import) -- oracle created by b119f0a, superseded here
- [x] `scriba/animation/primitives/_svg_helpers.py` -- switch 4 sites to `text_face="scriba-sans"`; ARROW_STYLES `good`/`path` weight 700→600 -- measured face == painted face, synthesis-free
- [x] `scriba/animation/_frame_renderer.py` -- switch 3 sites to `text_face="scriba-sans"` -- link/note parity
- [x] `scriba/animation/static/scriba-scene-primitives.css` + `scriba/core/css_bundler.py` -- token `600 11px "Scriba Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`; comments say the pill now shares the cell width-oracle; `font-weight: 400 600` descriptor fix -- paint change
- [x] `tests/unit/` -- rewrite pill face tests (mixed additivity vs float Inter sum; NFC decomposed==precomposed; VN full-coverage no-heuristic assertion; missing-glyph → symbol_em/heuristic > 0; default-mono identity; pill ≥ painted); update link/note spies to `"scriba-sans"`; assert good/path stamped weight ≤600 -- lock contract
- [x] `tests/golden/` -- regen via `SCRIBA_UPDATE_GOLDEN=1`; verify diff scope (annotation markup, weights, widths, CSS hunks only) -- baseline refresh
- [x] `docs/spec/animation-css.md` + `deferred-work.md` -- contract sync; deferred note-math entry resolved-by-alignment -- docs truth

**Acceptance Criteria:**
- Given `label="đã thăm"`, when rendered, then every glyph paints Scriba Sans (no mono fallback) and pill width equals the float-oracle prediction.
- Given the same label decomposed (NFD), when measured, then width equals the precomposed measurement exactly.
- Given `color=good`, when the pill is emitted, then its inline font-weight ≤600 and no faux-bold synthesis face is requested.
- Given any non-annotation surface, when the suite runs, then output is byte-identical (only annotation goldens change).
- Given the full suite after golden regen, then green (known flaky starlark exempt).

## Spec Change Log

## Design Notes

Weight A1 rationale (from investigation, Confirmed): Inter subset is a static 400 master (no fvar/HVAR); Chrome renders declared-range ≤600 without synthesis (investigations/folabel-fonts.md:175-187), so advances == baked table == exact. 700 would synthesize → under-measure → clip. Kind hierarchy remains via color tokens + halo; pill text weight now matches cell text (the diagram's voice).

## Verification

**Commands:**
- `.venv/bin/pytest tests/unit/test_pill_math_wrap.py tests/unit/test_math_metrics.py tests/unit/test_link_label_obstacle.py tests/unit/test_note_command.py -q` -- expected: pass
- `SCRIBA_UPDATE_GOLDEN=1 .venv/bin/pytest tests/golden tests/doc_coverage -q && git diff --stat tests/` -- expected: annotation-bearing files only
- `.venv/bin/pytest -q` -- expected: green (flaky starlark exempt)
- `rg -n "sans_text_width|katex-sans" scriba/ tests/ docs/` -- expected: no hits (fully superseded)

**Manual checks (if no CLI):**
- Render a `color=good` VN-label sample; confirm single face, regular weight legible on halo, no clipping.

## Suggested Review Order

**The oracle (design core)**

- One house measurer: `measure_run` on the Protocol (NFC → Inter advances → symbol_em → heuristic; `conservative_symbols` floors Sm/So misses at 0.9em for annotation runs only — cells keep the exact old behavior)
  [`_text_metrics.py:99`](../../scriba/animation/primitives/_text_metrics.py#L99)

- `measure_text_run` — the float annotation entry (single line-level rounding); `measure_text` = same sum, int, byte-identical (proven old-vs-new over 90×5 cases)
  [`_text_metrics.py:208`](../../scriba/animation/primitives/_text_metrics.py#L208)

- `measure_label_line` routes `text_face="scriba-sans"`; `sans_text_width` oracle deleted from `_math_metrics.py`
  [`_text_metrics.py:222`](../../scriba/animation/primitives/_text_metrics.py#L222)

**Painted face + weight invariant**

- Token: `600 11px "Scriba Sans", …` (the cell family); `font-synthesis: none` pins ≤600 = no faux-bold
  [`scriba-scene-primitives.css:105`](../../scriba/animation/static/scriba-scene-primitives.css#L105)

- `ARROW_STYLES` — every kind's `label_weight` ≤600 (`good`/`path` 700→600); contract comment
  [`_svg_helpers.py:1937`](../../scriba/animation/primitives/_svg_helpers.py#L1937)

**Measure sites (paint == measure everywhere)**

- `pill_dimensions` + wrap ruler: `_wrap_label_lines` gains `text_face` so packing uses the painted ruler (review patch P2 — caps-heavy labels wrap instead of busting the 132px budget)
  [`_svg_helpers.py:1398`](../../scriba/animation/primitives/_svg_helpers.py#L1398), [`_svg_helpers.py:1719`](../../scriba/animation/primitives/_svg_helpers.py#L1719)

- Link + note labels, incl. the E1126 ellipsis recompute the review caught (P1)
  [`_frame_renderer.py:1391`](../../scriba/animation/_frame_renderer.py#L1391), [`_frame_renderer.py:1604`](../../scriba/animation/_frame_renderer.py#L1604)

**Peripherals**

- Contract tests (11): additivity, NFC, VN no-heuristic, `·` in-table, ≮/→ conservative floor, all-kinds weight, caps-ruler regression, tight pill≥painted bound
  [`test_pill_math_wrap.py:128`](../../tests/unit/test_pill_math_wrap.py#L128)

- `@font-face` descriptor `400 500 600`→`400 600`; docs contract §2.1/§7.1; deferred note-math entry resolved-by-alignment; new deferral: Inter subset arrows/math-ops extension
  [`css_bundler.py:59`](../../scriba/core/css_bundler.py#L59), [`animation-css.md`](../../docs/spec/animation-css.md), [`deferred-work.md`](deferred-work.md)

- 107 goldens: 106 CSS-only (`font-synthesis` lines), 1 geometry (`test_label_readability.html` — P2 re-wrap)
