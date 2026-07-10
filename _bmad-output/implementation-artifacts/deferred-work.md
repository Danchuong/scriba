
## 2026-07-08 — from spec-fix-annot-pill-font-clash review
- **Note math-branch measure/paint face mismatch (safe over-measure).** ~~`scriba/animation/_frame_renderer.py` note `has_math` branch (~:1540,:1553,:1586) measures via shared `measure_value_text` (mono-default `measure_label_line`, no `text_face` param) while the note `<text>` paints KaTeX_SansSerif via `.scriba-annotation > text`. Fixing requires threading `text_face` through `measure_value_text`'s shared signature (spec Ask-First boundary) — deferred. Direction is conservative (mono ≥ sans → no clipping); only cost is slightly over-wide math-note pills.~~
  **Resolved-by-alignment (spec-fix-annot-pill-face-scriba-sans, 2026-07-08).** Candidate A re-points the note `<text>` paint to "Scriba Sans" — which is exactly `measure_text`'s face — so `measure_value_text`'s base and stripped-fallback terms (`base = measure_text` when `mono=False`) now measure the painted face exactly, with zero signature change. The only residual is a benign over-measure on the `max()`'s math-model arm (`measure_label_line`, still mono default) — mono ≥ sans, so a math-bearing note pill can be a hair wider than needed, never clipped. Acceptable; no further work.

## 2026-07-10 — from JudgeZone #10 sweep (accessible-name policy, wave 2)
- **`\includegraphics` alt = raw filename — needs an `alt=` option key (feature,
  not this wave).** `scriba/tex/parser/images.py` has no `alt=` option; the
  emitted `alt` is unconditionally the filename. NOT a silent-wrong-choice bug:
  the behavior is a documented contract (`docs/guides/tex-plugin.md` §3 pins
  `alt="fig.png"`), 2 snapshot tests + 1 XSS test depend on it, and the
  filename is author-provided content (not an internal id), so the R-15/JZ-10
  "id never surfaces" policy does not strictly apply. Proper fix: new `alt=`
  option key (author text → alt; explicit `alt=""` → decorative; no alt= →
  keep filename or empty — decide in spec), parser + docs + snapshot regen,
  own contract review. Sized by two independent agents (sweep-title,
  sweep-label) as beyond a sweep tack-on. See "Follow-up finding" in
  spec-fix-judgezone-10-accessible-name-policy.md.

## 2026-07-10 — from JudgeZone #11 sweep (interp shield, wave 2)
- **`\note text=` paints a stray literal backslash before `${x}` that
  `\annotate label=` doesn't.** Cosmetic; lives UPSTREAM of `_text_render.py`
  (note's own text plumbing), not in the shield/pairing path the wave fixed.
  Repro: `\note{...}{text="cost ${x} is fine"}` with x unbound. Owner: whoever
  next touches `_frame_renderer.py`'s note channel. See "Sweep wave (wave 2)"
  in spec-fix-judgezone-11-interp-shape-gate.md.

## 2026-07-08 — from spec-fix-annot-pill-face-scriba-sans review (r2)
- **Extend Inter subset with arrows/math-ops blocks (U+2190-21FF, U+2200-22FF).** Structural closure for raw-symbol labels (`"1 ≮ 1"`-style, the SPEC-recommended authoring pattern): glyphs would paint AND measure Scriba Sans exactly, removing the residual measured-KaTeX-vs-painted-system-sans mismatch that r2's P3 conservative floor only pads. Blockers to analyze first: (1) `≮` U+226E absent from the Inter master (`~/Library/Fonts/Inter-Regular.ttf` cmap check 2026-07-08) — needs per-glyph fallback story anyway; (2) the subset+`inter_advances.json` is the CELL oracle too — adding table entries changes `measure_text` for any cell containing those glyphs (today they route via `symbol_em`), so non-annotation goldens may shift; needs corpus impact scan + its own spec.
