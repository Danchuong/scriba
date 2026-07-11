
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

## 2026-07-11 — from JudgeZone #15 sweep wave (other top-band tenants)
- **Forest `\note{at=top-left/top-right}` collides with Forest's own caption
  (~14px overlap); Tree/Graph don't have this problem.** Repro: `\shape{f}
  {Forest}{nodes=["A","B"], edges=[], label="Forest Caption"}` +
  `\note{n1}{text="hi", at=top-left}` in the same step — the note's SVG
  rect band lands at abs y=(8,27), Forest's caption text band lands at abs
  y=(9,23): `overlap=14.0`. Root cause is NOT the top-band reservation model
  JZ-15 fixed (that governs decorations painted *inside* a primitive's own
  bbox, e.g. `\annotate` pills / `\group` hulls / Tree `\link` / Graph
  antiparallel bows — all confirmed disjoint from captions, see the "Sweep
  wave" section of `spec-fix-judgezone-15-top-band-reservation.md`). This is
  the *other*, separate placement mechanism: scene-level `\note`/`\link`
  cross-shape bridges, positioned by `_scene_content_obstacles()`/
  `_place_pill()` in `scriba/animation/_frame_renderer.py`, which appears to
  assume a roughly-fixed caption band position. That assumption holds for
  Tree/Graph (`_top_band_layout(r, ...)`, caption paints at `base_ty=r`,
  observed abs band (29,43)) but not Forest (`_top_band_layout(0, ...)`,
  `base_ty=0`, observed abs band (9,23) — Forest has no root-circle radius
  to push its outer transform down, so its caption legitimately sits ~20px
  higher than Tree/Graph's). Fix belongs in `_frame_renderer.py`'s obstacle
  computation (read the actual primitive's caption band instead of assuming
  a fixed one) — outside `primitives/*.py`, so outside a primitive-only
  sweep's fence; also a file with concurrent in-flight edits from another
  agent this session. Owner: whoever next touches
  `_scene_content_obstacles()`/`_place_pill()`.

## 2026-07-11 — from JudgeZone #15 sweep wave (Forest wrap-width divergence, root-caused)
- **Caption word-wrap point is decided before `\annotate` right-reach is known
  — shared across Tree/Forest/Graph, not Forest-specific as first flagged.**
  Supersedes/sharpens the "Forest wrap-width divergence" item in
  `investigations/judgezone-15-topband-caption-investigation.md` § Out-of-scope
  Observations #1 — same symptom, now root-caused. All three primitives call
  `_emit_top_caption(content_width=content_w, footprint_width=int(self.
  bounding_box().width), ...)` (`forest.py:606-612`, `tree.py:1100-1106`,
  `graph.py` mirrors) where `content_w` is the primitive's *own* base content
  width (Forest: `_envelope_width`; Tree/Graph: `width + 2r`) — computed with
  **no knowledge of `\annotate` pill right-reach** (`annotation_h_pads()` /
  `_h_label_pad()`). The wrap decision (`_caption_lines`, called with
  `content_width=content_w`) locks in line breaks at that narrower width; the
  caption is then *centered* in the wider `footprint_width` (which **does**
  fold in `right_reach` via `bounding_box()`'s `w = left_pad + max(core_w,
  right_reach)`) — so when `right_reach` alone exceeds the base content width,
  the caption can wrap a line earlier than the final box needs.
  Verified end-to-end (real `emit_svg()` output, not just arithmetic) on
  Forest: a 5-node Forest with a long caption + one `\annotate{position=right}`
  pill on a node gives `content_w=320` vs `bounding_box().width=415`
  (right_reach=415 alone, entirely annotation-driven); the caption paints as
  `["...grows wide ", "quickly here today value label width"]` (breaks after
  "wide") when the true 415px footprint would fit `["...grows wide quickly
  here", "today value label width"]` (breaks after "here" — visibly more
  balanced, ~95px of unused width on line 1 as painted). Confirmed the same
  mechanism reproduces on Tree (content_w=440 vs bbox.width=462 with an
  equivalent `\annotate{position=right}` pill) — that specific case didn't
  cross a word boundary, but the arithmetic gap is the same shape, confirming
  this is a `base.py`-pattern issue, not an artifact of Forest's
  `_envelope_width` machinery specifically.
  Word-wrap point selection only — not a collision/clipping bug (the box
  itself is always >= what it needs to be; only the incidental line-break
  choice is occasionally suboptimal). Not fixed here: the real fix reorders
  `bounding_box()`/`emit_svg()` in all three files to compute `right_reach`
  (via `_h_label_pad()`) *before* the caption-wrap content width is decided,
  which is a shared-helper-level signature/ordering change across three
  primitives with a corpus-wide (not just directed-graph) golden blast
  radius — sized beyond a sweep tack-on, same as the original investigation's
  call. Owner: whoever next revisits the shared caption-block helpers in
  `base.py` (`_caption_lines` / `_caption_block_width` / `_emit_top_caption`).

## 2026-07-08 — from spec-fix-annot-pill-face-scriba-sans review (r2)
- **Extend Inter subset with arrows/math-ops blocks (U+2190-21FF, U+2200-22FF).** Structural closure for raw-symbol labels (`"1 ≮ 1"`-style, the SPEC-recommended authoring pattern): glyphs would paint AND measure Scriba Sans exactly, removing the residual measured-KaTeX-vs-painted-system-sans mismatch that r2's P3 conservative floor only pads. Blockers to analyze first: (1) `≮` U+226E absent from the Inter master (`~/Library/Fonts/Inter-Regular.ttf` cmap check 2026-07-08) — needs per-glyph fallback story anyway; (2) the subset+`inter_advances.json` is the CELL oracle too — adding table entries changes `measure_text` for any cell containing those glyphs (today they route via `symbol_em`), so non-annotation goldens may shift; needs corpus impact scan + its own spec.
