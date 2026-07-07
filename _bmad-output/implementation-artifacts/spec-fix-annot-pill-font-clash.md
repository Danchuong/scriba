---
title: 'Fix mixed math+text annotation pill font clash (KaTeX_SansSerif unification)'
type: 'bugfix'
created: '2026-07-08'
status: 'done'
context: []
baseline_commit: '3d1148a37313e9cc5c813f65a45f3a376ece15f0'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** An `\annotate` label mixing inline math and text (e.g. `"$1 < 3$ · exit"`) renders the math run in KaTeX_Main serif and the text run in `ui-monospace` 600 — two clashing typefaces inside one pill (bug report #8, JudgeZone).

**Approach:** Pin annotation pill labels to the already-vendored `KaTeX_SansSerif` face (Bold, matching the current 600 weight) and give the measurer a real SansSerif-Bold advance table — same pattern as the existing 0.22.1 KaTeX_Main path. Mixed labels then pair KaTeX math + KaTeX sans text: one family, no clash, measurement stays browser-free and exact.

## Boundaries & Constraints

**Always:**
- Scope the face + metrics change to **annotation pills only** (`.scriba-annot-label`, `.scriba-annotation > text`, and the pill measurement path). Measurement must model the exact face CSS selects.
- `pill_dimensions` stays the single source of truth for wrap + measure; text-run and math-run widths sum additively as today.
- Regenerate `katex_advances.json` only via `scripts/build_katex_metrics.py` (add `SansSerif-Bold` to `FONTS`); never hand-edit the JSON.
- Golden corpus updates only via `SCRIBA_UPDATE_GOLDEN=1`; inspect a sample diff (pill `<rect width>` changes only, no layout breakage) before accepting.

**Ask First:**
- If `KaTeX_SansSerif-Bold` glyph coverage misses characters common in labels (Vietnamese diacritics, `·`, `≮`, arrows) with no sane fallback modeling, HALT — fallback face choice is a design decision.
- If scoping requires touching the shared `estimate_text_width` signature used by non-pill callers, HALT.

**Never:**
- Do NOT change the shared mono heuristic `estimate_text_width` (~0.62 em/char) or the Inter `measure_text` path — axis labels, captions, codepanel, graph, metricplot all depend on them.
- Do NOT change `_wrap_label_lines` wrapping formulas or `position_label_height_above/below` (hard constraint from the annotation-legibility structural-lift plan).
- Do NOT change the `math_rendered=False` raw-TeX fallback path.
- No new font files, no new `@font-face` (SansSerif woff2 + faces already vendored in `scriba/tex/vendor/katex/`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mixed label | `label="$1 < 3$ · exit"` | Math run KaTeX_Main, text run KaTeX_SansSerif Bold — same family pairing, one pill; pill width = KaTeX advance sum for both runs | N/A |
| Plain-text label | `label="1 < 3 · exit"` | Whole pill in KaTeX_SansSerif Bold, width from SansSerif table | N/A |
| Math-only label | `label="$\binom{n}{k}$"` | Unchanged vs today (KaTeX_Main path untouched) | N/A |
| Glyph not in SansSerif table | text run contains uncovered codepoint (e.g. `ế`) | Width falls back per-char to existing heuristic (`_char_display_width`-style) — never crash, never 0-width | Silent fallback, over-estimate acceptable |
| Non-pill labels (axis, caption, cursor) | any | Byte-identical output — mono face and mono heuristic untouched | N/A |

</frozen-after-approval>

## Code Map

- `scriba/animation/static/scriba-scene-primitives.css:99,528-541` -- `--scriba-annotation-font` token + `.scriba-annotation > text` / `.scriba-annot-label` pins (the face to change)
- `scriba/animation/primitives/_svg_helpers.py:1398-1446,1586,1600,1678,2105,2470,2778,3567` -- `pill_dimensions` + pill emitters / FO label divs
- `scriba/animation/primitives/_text_metrics.py:162` -- `measure_label_line` splits math vs text runs; text runs currently → mono heuristic
- `scriba/animation/primitives/_math_metrics.py:190-206,456` -- `_tables()` loads `katex_advances.json`; `measure_inline_math` KaTeX path to mirror
- `scripts/build_katex_metrics.py:38` -- `FONTS` tuple to extend with `"SansSerif-Bold"`
- `scriba/tex/vendor/katex/katex_advances.json` -- baked advance data (regenerate)
- `scriba/animation/_frame_renderer.py:1390,1558,1570` -- link + note label measure sites (paint via `.scriba-annotation > text` → switched to `text_face="katex-sans"` in review patch; note math-branch via shared `measure_value_text` deferred, see deferred-work.md)
- `docs/spec/animation-css.md:89,111,791` -- annotation font contract doc
- `tests/unit/test_pill_math_wrap.py` -- structural pill assertions (line-height literals 13/19, width inequalities)
- `tests/golden/examples/` + `tests/doc_coverage/corpus/` -- byte-for-byte HTML goldens embedding pill rect widths

## Tasks & Acceptance

**Execution:**
- [x] `scripts/build_katex_metrics.py` -- add `"SansSerif-Bold"` to `FONTS`; run it to regenerate `scriba/tex/vendor/katex/katex_advances.json` -- metrics source for the new face
- [x] `scriba/animation/primitives/_math_metrics.py` -- expose a text-run measurer over the SansSerif-Bold table (e.g. `sans_text_width(text, font_px)`): per-char advance sum, per-char fallback to the existing display-width heuristic for uncovered codepoints -- mirrors the 0.22.1 KaTeX path. **Deviation:** scaled by `× font_px` ONLY, NOT `× _KATEX_BASE_EM` — the pill text run paints directly in `.scriba-annot-label` at the label font-size, not inside the `.katex` 1.21em box (that factor applies only to the math run's KaTeX spans). Applying 1.21 would over-measure the text run 21% and defeat the exactness the fix exists for.
- [x] `scriba/animation/primitives/_text_metrics.py` -- add opt-in face selection to `measure_label_line` (`text_face="mono"|"katex-sans"` keyword, default `"mono"`); `"katex-sans"` routes text runs to the SansSerif measurer -- pills switch, all other callers untouched by default (default path byte-identical)
- [x] `scriba/animation/primitives/_svg_helpers.py` -- `pill_dimensions` (math_rendered=True path) and the three direct pill measurers (multi-line FO box_w, plain-arrow pill_w, `position_label_pill_width` extents) pass `text_face="katex-sans"`; verified FO label divs don't re-pin mono via inline font-family (they inherit `.scriba-annot-label`) -- pill measurement matches painted face. The `math_rendered=False` raw-TeX fallback path left untouched (frozen).
- [x] `scriba/animation/static/scriba-scene-primitives.css` -- `--scriba-annotation-font: 600 11px KaTeX_SansSerif, ui-monospace, monospace` (mono stays as fallback); comment updated -- painted face change
- [x] `tests/unit/test_pill_math_wrap.py` -- extended (`TestKatexSansTextFace`): mixed label width == sans(text runs) + katex(math run) sum; plain-text sans; default-face byte-identical; sans narrower than mono; uncovered-glyph fallback never 0; pill >= painted. Line-height literals unchanged (measured face does not alter them) -- lock the contract
- [x] `tests/golden/` -- regenerated via `SCRIBA_UPDATE_GOLDEN=1`; diffs confined to the embedded CSS token/comment + annotation pill rect widths/coords/fonts (verified no non-pill element changed) -- baseline refresh
- [x] `docs/spec/animation-css.md` -- updated font token + `.scriba-annotation > text` / `.scriba-annot-label` contract -- doc sync

**Acceptance Criteria:**
- Given the repro (`label="$1 < 3$ · exit"`), when rendered, then the text run paints in KaTeX_SansSerif (not ui-monospace) and pill width equals the measurer's prediction.
- Given any non-annotation label surface (axis, caption, cursor, codepanel), when the full test suite runs, then their outputs are byte-identical to pre-change (only annotation-pill golden diffs).
- Given a text run with a codepoint absent from the SansSerif table, when measured, then width uses fallback heuristic and rendering does not clip (pill ≥ painted width).

## Spec Change Log

## Verification

**Commands:**
- `python scripts/build_katex_metrics.py` -- expected: regenerated JSON includes `SansSerif-Bold` block
- `pytest tests/unit/test_pill_math_wrap.py tests/unit/test_math_metrics.py -q` -- expected: pass
- `SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden tests/doc_coverage -q && git diff --stat tests/` -- expected: diffs confined to files containing annotation pills
- `pytest -q` -- expected: full suite green

**Manual checks (if no CLI):**
- Render the repro animation; confirm one visual family inside the pill and no text clipping at pill edges.

## Suggested Review Order

**Measurement model (the design core)**

- New width oracle: SansSerif-Bold advance sum × font_px only — no 1.21 KaTeX box factor (the documented deviation)
  [`_math_metrics.py:238`](../../scriba/animation/primitives/_math_metrics.py#L238)

- `text_face` opt-in keyword: math runs always KaTeX, text runs mono (default) or katex-sans — non-pill callers byte-identical
  [`_text_metrics.py:162`](../../scriba/animation/primitives/_text_metrics.py#L162)

**Painted face (CSS contract)**

- Token flips to `600 11px KaTeX_SansSerif, ui-monospace, monospace`; mono stays fallback for uncovered glyphs
  [`scriba-scene-primitives.css:103`](../../scriba/animation/static/scriba-scene-primitives.css#L103)

**Measure sites switched to match the painted face**

- `pill_dimensions` math_rendered path — the single source of truth for pill wrap+measure
  [`_svg_helpers.py:1398`](../../scriba/animation/primitives/_svg_helpers.py#L1398)

- Link-label pill width (review-found gap: painted sans via `.scriba-annotation > text`, was measured mono)
  [`_frame_renderer.py:1391`](../../scriba/animation/_frame_renderer.py#L1391)

- Note-label no-math branch, same review-found gap (math branch via shared `measure_value_text` deferred — safe over-measure)
  [`_frame_renderer.py:1559`](../../scriba/animation/_frame_renderer.py#L1559)

**Metrics data**

- `FONTS` += `SansSerif-Bold`; regenerated `katex_advances.json` (+120-glyph block, script-only)
  [`build_katex_metrics.py:38`](../../scripts/build_katex_metrics.py#L38)

**Peripherals**

- Contract tests: mixed-label additivity, default-face byte-identity, uncovered-glyph fallback, pill ≥ painted
  [`test_pill_math_wrap.py:128`](../../tests/unit/test_pill_math_wrap.py#L128)

- Link/note measure-face spies
  [`test_link_label_obstacle.py:197`](../../tests/unit/test_link_label_obstacle.py#L197), [`test_note_command.py:344`](../../tests/unit/test_note_command.py#L344)

- Font contract doc sync
  [`animation-css.md:89`](../../docs/spec/animation-css.md#L89)

- ~115 golden HTML baselines regenerated (annotation pill/link/note geometry + embedded CSS token only)
