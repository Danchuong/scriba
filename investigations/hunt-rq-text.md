# Hunt: Render-Quality — TEXT / LABEL / VALUE / MATH

BMAD render-quality hunt. Slice: text/label/value/math rendering quality
(clipping, overflow, mis-centering, KaTeX sizing, multilingual width).
Read-only source; evidence graded **Confirmed** (code cite + rendered SVG proof
with numbers) / **Deduced** / **Hypothesized**. No browser — render server SVG,
measure text extents numerically against the vendored fonts (woff2 hmtx + KaTeX
advance tables, decoded with fontTools).

## Hand-off Brief

- **3 confirmed defects.** Ranked: F3 note vertical clip (HIGH) > F2 bar value
  collision (MED-HIGH) > F1 symbol under-measurement (MED).
- The core measurement engine is **genuinely solid**: covered Latin + Vietnamese
  measure EXACTLY (advance-sum == woff2 hmtx, verified), Equation `&` columns
  align, captions wrap/center correctly, per-primitive `bounding_box()` reserves
  the viewBox so cell/pill/hashmap content never breaches it. The defects live in
  the **gaps**: glyphs outside the pinned subset, and the two decoration surfaces
  that place text against a *fixed* box (bar value labels, scene notes).
- Method note: viewBox-overflow is the *wrong* signal here — bbox reservation is
  so thorough that overrunning content stays inside the viewBox. The real defects
  are **intra-figure** (text over neighbour / label over label / text below a
  fixed box edge). Two candidate hits (long_caption, annot_pills) were
  **false positives** from nested `translate()` groups + `<tspan>` concatenation
  and were discarded after a transform-accurate re-check.

## Defect table

| # | Surface | String (input) | Measured vs box | Overflow | Sev | Grade |
|---|---------|----------------|-----------------|----------|-----|-------|
| F3 | `\note` (multi-line) | `"This is a fairly long note … within its box"` on a 3-cell Array | pill **h=85** vs viewBox **vh=64** | **bottom 21 px → last 2 lines cut off** | HIGH | Confirmed |
| F2 | `Bar` `show_values` | `data=[1000000001..4]` | 4 labels, ~**70 px** wide, **44 px** pitch, all at **y=14** | **26 px** label-over-label overprint (illegible) | MED-HIGH | Confirmed |
| F1 | Queue/Array/… cell (uncovered symbols) | `"1→2→3→4→5"`, `"∞∞∞∞∞∞∞"` | true ~**101/98 px** in **90 px** cell (scriba measured 80/61) | **~5.5 / ~4 px** each side into gap/neighbour | MED | Confirmed |
| F1b | text-measure of `∞ → ≤ ≥ − ± × √ ∈` | any | `measure_text("∞",14)=9 px` (0.62 em) vs scriba's own KaTeX table **1.0 em = 14 px** | 56 % under, **silent** (no W1301) | MED | Confirmed |

## F3 — Multi-line `\note` clipped at the viewBox bottom (HIGH, Confirmed)

`scriba/animation/_frame_renderer.py` `_emit_scene_notes` (~L1447–1479) +
`_note_anchor_xy` (~L1377). The scene viewBox `(vx,vy,vw,vh)` is fixed by the
**shapes** before notes are placed; the note is then laid *inside* it. The code
wraps the note to fit the viewBox **WIDTH** and even warns E1125 when a note is
wider than the board:

```
board_avail = max(1.0, vw - 2.0 * _NOTE_MARGIN)          # WIDTH only
wrap_px     = min(board_avail, float(_LABEL_PILL_MAX_W_PX))
...
ph = float(LABEL_FONT_PX * len(lines) + 8)                # height just falls out
```

There is **no height counterpart** — no `board_avail_h`, no clamp, no warning if
`ph > vh`. So a note with enough wrapped lines is taller than the viewBox and its
bottom rows fall off the SVG viewport (default `overflow:hidden`; embed.css also
pins `overflow:hidden`).

Rendered proof — same note, small figure (3-cell Array, `viewBox 0 0 208 64`),
note-`<g>` is a top-level sibling (no transform), exact tspan y-coords:

```
note_ok : pill rect x=66 y=0 w=142 h=85  -> bottom=85 vs vh=64  => 21px CLIPPED
   line y=42.5 'describing the loop'
   line y=53.5 'invariant i <= n'
   line y=64.5 'that should wrap or'   <-- below vh=64 (CLIPPED)
   line y=75.5 'fit within its box'    <-- below vh=64 (CLIPPED)
note_short "short": pill h=19 -> fits (clean A/B control)
```

The two bottom teaching lines are silently cut off (width fit is fine, so E1125
never fires). Realistic: a `\note` is an explanatory callout; users add them to
small diagrams constantly. Fix: wrap/clamp height too (or grow the note's own
reserved band into the scene bbox like other decorations).

## F2 — `Bar` value labels overprint each other (MED-HIGH, Confirmed)

`scriba/animation/primitives/bar.py`: `_VALUE_FONT_PX = LABEL_FONT_PX` (11 px),
values printed centered above each column; column pitch = `bar_width (36) + _BAR_GAP`
= **44 px**. The value label width is **not** reserved in the pitch and there is
no inter-label collision avoidance, so any value wider than the pitch collides
with its neighbour. A 10-digit value is ~70 px at 11 px.

Rendered proof, `data=[1000000001,1000000002,1000000003,1000000004]`
(near-equal → equal-height bars → labels share one y band):

```
value cx=26  y=14 w=70 span=[-9, 61]
value cx=70  y=14 w=70 span=[35,105]  <-- overlaps prev by 26px
value cx=114 y=14 w=70 span=[79,149]  <-- overlaps prev by 26px
value cx=158 y=14 w=70 span=[123,193] <-- overlaps prev by 26px
```

All four 10-digit numbers overprint by 26 px each → illegible. Control:
`data=[1e9,2e9,3e9,4e9]` (different heights) staggers the labels in y (Δy=35 px)
so they *don't* visually collide — the bug bites when bars are **near-equal
height with wide values** (comparing similar large counts, a common chart).
The chart's own bbox does reserve the outer overhang (no viewBox clip), so this
is purely label-vs-label, not a clip.

## F1 — Uncovered math symbols under-measured on the "exact metrics" surface (MED, Confirmed)

`scriba/animation/primitives/_text_metrics.py`. The pinned "Scriba Sans" (Inter)
subset covers Basic-Latin + Latin-Ext + Vietnamese only (759 glyphs,
U+0000..U+20AB). Codepoints outside it hit the `_char_display_width` heuristic:
combining=0, CJK-wide=1.0 em, **everything else = 0.62 em**. Common algorithm
glyphs `∞ → ≤ ≥ − ± × √ ∈ ∅` are category Sm/So, EAW N/A → **0.62 em**, and they
are NOT in `_COMPLEX_BLOCKS`, so **W1301 never warns** (that guard only covers
whole scripts: Hebrew/Arabic/Indic/Thai/Hangul…). `measure_text("∞→≤∈∅",14)`
emits 0 warnings.

Internal contradiction — scriba's *own* KaTeX table knows the real widths:

```
sym  text-meas(14px)   KaTeX Main-Regular adv   implied px@14   under
∞         9 px          1.0   em                14.0 px         56%
→         9 px          1.0   em                14.0 px         56%
≤ ≥ − ± ×  9 px          0.778 em                10.9 px         21%
√         9 px          0.833 em                11.7 px         30%
```

So `$\infty$` (math) measures 14 px but a bare `∞` cell value measures 9 px.
Rendered impact — Queue with packed symbols (`_rq_queue_sym`, cell w=90,
text centered):

```
q.cell[0] "1→2→3→4→5"  rect[21,111] center=66 true≈101 -> ink[15.5,116.5] -> ~5.5px each side
q.cell[2] "∞∞∞∞∞∞∞"    rect[209,299] center=254 true≈98 -> ink[205,303]   -> ~4px each side
```

The text overruns its cell into the inter-cell gap / neighbour. **Mitigated** for
short values by the 60 px cell floor (`max(CELL_WIDTH, meas+PAD…)`): a single `∞`
sits comfortably in a 60 px cell, so the overrun needs several packed uncovered
glyphs to surface (hence MED, not HIGH). The shipped `dijkstra.tex` sidesteps it
by writing `data=["inf",…]` (ASCII) instead of `∞` — a telling workaround.
Real risk rises on **no-floor** surfaces (annotation pills, graph edge-weight
labels, bar/axis labels) where the box is sized tight to the measured width.

## Math (KaTeX) quality — checked, mostly sound

- **Linear inline math is exact** (advance-sum over the vendored KaTeX tables,
  their bench p50 0.06 % / p95 0.66 % vs Chromium). Verified the tables decode
  and the model reproduces per-glyph advances.
- **Nonlinear fragments** (`\frac \sqrt \sum` limits, `\begin…`) take
  `is_linear_math()==False` → `_heuristic_px`, which strips `\frac{a}{b}` to the
  *concatenated* `ab` ×1.15 → **over**-estimates the (vertically-stacked, narrow)
  fraction width. Safe horizontally (over-measure only pads). Rendered `eqn_nl`
  with `\sqrt{\frac{\sum…}{…}}` showed 0 viewBox anomalies.
- **Tall math in fixed 40 px cells does NOT clip.** Array math cells emit a
  `foreignObject h=40 line-height=40 overflow:hidden`; scriba's own
  `math_tall_extra` model puts a 14 px `\frac`/`\sum` at ~36 px needed < 40 →
  fits (`_rq_tallmath_array` confirmed h=40 boxes, no vertical breach).
- **Equation `&` alignment is correct.** lhs is right-anchored to `col_x` and rhs
  left-anchored to the same `col_x`, so mis-measured fragment width can't break
  the column. Rendered `eqn_align`: every line's lhs-right == rhs-left ==
  col_x=63. Revealed/hidden lines reserve space (R-32) — no drift.
- Multi-line math pill (`_emit_label_multiline` FO-per-line): clean 30 px pitch,
  no line overlap.

## Multilingual width

- **Vietnamese is genuinely exact** (the headline claim holds). `measure_text`
  vs woff2 advance-sum: `"Chọn phần tử nhỏ nhất"` est **150** vs real **150.4**;
  `"Đường đi"` 60 vs 59.9; `"phần tử"` 50 vs 50.0. NFC-normalization means
  decomposed input measures identically. No defect.
- **CJK** falls to the 1.0 em fallback (`数组`→28 px/2 = 1.0 em each); plausible
  for full-width ideographs, no W1301 (deliberate — 1 em ≈ real). Not clipped in
  cells (60 px floor).
- **RTL** (Arabic/Hebrew) gets `unicode-bidi:plaintext` and a W1301 over-estimate
  warning — safe by design (shaping only narrows).
- Gap: the mono label/index/caption/tick surfaces measure at a flat 0.62 em but
  render `ui-monospace, monospace`; fine for ASCII (~0.60 em real, +3 % safe),
  but a CJK glyph in a *mono* label is measured 1.0 em while a real mono face
  renders it ~1.2 em (double-width) → **Hypothesized** under-measure on that
  narrow surface (not reproduced; mono+CJK labels are rare).

## Also verified ROBUST (ruled out)

- Long caption wrapping: 7 centered tspans, `x` shared, **trailing spaces kept**
  on non-final lines (copy-paste integrity holds).
- HashMap long entries extend into reserved chain space (no clip).
- CodePanel grows its panel to the longest mono line (viewBox 728, no clip).
- ss01 stylistic set does **not** change letter advances; tnum makes digits
  tabular (1328/2048). On surfaces WITHOUT the tnum CSS (Stack/Queue/LinkedList/
  Matrix/TraceTable) digits are measured tabular but render proportional →
  **over**-measure (boxes slightly wide) — cosmetic, never clips.

## Conclusion + Confidence

The text/math engine's *headline* claims are real: exact Inter/Vietnamese
metrics, exact linear-KaTeX, correct alignment and wrapping, thorough viewBox
reservation. The defects are at the edges:

1. **F3 (HIGH, Confidence: high)** — multi-line `\note` silently clipped at the
   viewBox bottom; height is never fit-checked where width is. Reproduced with an
   exact A/B and located in code.
2. **F2 (MED-HIGH, high)** — `Bar` value labels overprint (26 px) when near-equal
   large values share a y band; no width reservation in the column pitch.
3. **F1 (MED, high on the mismeasurement, medium on visible impact)** — the
   "exact metrics" surface silently under-measures common DP/graph symbols
   (`∞ → ≤ …`) by 21–56 %; confirmed cell overrun in Queue, largely masked by the
   60 px cell floor but exposed on tight/no-floor surfaces.

Overall confidence **high** for the three confirmed defects (each has a rendered
SVG with numbers + a code cite). The two discarded candidates underline that
naive coordinate parsing over-reports here — every number above is taken in the
element's own local frame or with accumulated transforms.

### Raw data / repro
- Probes: `scratchpad/probe_measure.py` (measurer vs woff2), `cellfit.py`
  (local-frame cell-fit), `walk.py` (transform-accurate viewBox), `gen_batch.py`
  / `gen_b2.py` (stress docs).
- Key renders (scratchpad, `SCRIBA_ALLOW_ANY_OUTPUT=1`):
  `_rq_note_ok.html` / `_rq_note_short.html` (F3), `_rq_bar_eqheight.html` /
  `_rq_bar_collide.html` (F2), `_rq_queue_sym.html` (F1), `_rq_eqn_align.html`
  (alignment control), `_rq_multiling.html` (Vietnamese/CJK).
- Fonts decoded with fonttools 4.63 (installed into `.venv` for verification):
  `Inter-subset.woff2` (759 glyphs), `katex_advances.json`.
