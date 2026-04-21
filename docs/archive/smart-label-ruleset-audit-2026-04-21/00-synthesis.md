# Synthesis — Smart-Label Ruleset Audit 2026-04-21

Ten parallel agents audited the smart-label ruleset shipped on main (Phase 0 QW-1..QW-7 + MW-1).
This file consolidates findings into a prioritized action list.

---

## TL;DR

The ruleset documented in `docs/spec/smart-label-ruleset.md` is **structurally
sound but operationally incomplete**. The algorithm itself is correct; the
gap is between what it claims to do and what the rest of the system actually
lets it do.

Five findings rise to **P0** (ship-blocker or near-miss):

1. **WCAG contrast FAIL on 4 of 6 color tokens** after group-opacity compositing
   (a11y §A-1..A-4). `info` effective ratio 2.01:1, `muted` 1.49:1. Hover-dim
   compounds `info` to ~1.1:1. (#10)
2. **`_LabelPlacement.overlaps()` has zero-gap semantics, but I-2 claims 2 px.**
   Every test passes even when pills touch. Spec or code must change. (#1)
3. **Only 12.7 % of pill-bearing frames are visually clean** across the full
   52-example corpus. Primary failure: viewBox clip (42.8 %). Phase 0 + MW-1
   shifted defects from clipped-invisible into clipped-visible — no new
   defect classes, but increased visible defect counts on some files. (#6)
4. **QW-5 multiplier is backwards.** 1.15× over-estimates math width on 16 of
   20 labels (RMSE 17.1 px). Optimal 0.81× (RMSE 11.5). Recommended 0.90×. (#5)
5. **Clamp runs after collision check.** A candidate can escape collision with
   pre-clamp x=-40, then the clamp pulls it to x=+30 on top of a prior label.
   MEDIUM severity repro confirmed. (#2)

Six findings are **P1** (correctness or coverage):

6. Only 2 of 15 primitives fully wired (Array, DPTable). 6 more accidentally
   emit pills through `base.emit_annotation_arrows` but never expand viewBox
   headroom. 3 orphan emitters (Plane2D, Queue, NumberLine). 4 dark (Stack,
   Matrix, MetricPlot, CodePanel). (#3)
7. `emit_position_label_svg` uses a different 4-direction/16-candidate loop,
   not the 8-direction 32-candidate grid used elsewhere. Unspecified. (#1)
8. Test coverage 73 % line+branch (gate 75 %). `layout="2d"` branches and
   `emit_position_label_svg` collision block are 0 % covered. QW-4 math-guard
   condition never actually triggers under any existing test input. (#4)
9. MW roadmap order is inverted — MW-3 (helper) should ship before MW-2
   (registry) so MW-2's seeders are one-line calls instead of triplicated
   code. Revised order: MW-3 → MW-2 → MW-4a → (MW-4b only if needed). (#7)
10. CVD unsafe claim in `svg-emitter.md §8.4` is false: deuteranopia renders
    `warn`/`good`/`error` indistinguishable, `info` and `path` are literally
    the same hex. (#10)
11. 87 % of annotation-bearing frames have at least one classifiable defect;
    34.6 % have pill-arrow collisions (a defect category not tracked by
    I-1..I-10). (#6)

Five findings are **P2** (polish, performance, prior-art alignment):

12. Nudge step-size progression `(0.25, 0.5, 1.0, 1.5)` has no rationale. (#2)
13. Performance: `_nudge_candidates` sort is 73–81 % of its cost. Pre-sorted
    module constant would give 3.1× speedup. Width-cache gives 27× speedup
    on repeated labels. Fold both into MW-2. (#9)
14. Vega-label occupancy-bitmap model (pre-register marks) is the right
    conceptual upgrade for MW-2. Mapbox `text-variable-anchor` ordered-list is
    the right model for MW-3 `_place_pill`. d3fc greedy argmin-by-overlap-area
    is the right MW-4 fallback. (#8)
15. `emit_arrow_marker_defs` is dead code (body is `pass`). `pill_w` param
    on `_nudge_candidates` is accepted but never read. (#1, #2)
16. `position_label_height_below` never branches on math — below-position math
    labels do not receive the 32 px headroom that above-position math labels
    do (I-9 under-specified). (#1)

---

## Prioritized action list

Every item points back to the source audit file. Numbers in brackets indicate
agent report. Severity: P0 (before any further MW work) / P1 (in MW-2/3) /
P2 (defer or fold into MW-4).

### P0 — Pre-MW blockers

| # | Action | Fixes | Audit ref | Est |
|---|--------|-------|-----------|-----|
| A1 | Decide I-2 semantics: `overlaps(pad=2)` or `overlaps(pad=0)`. Update code or spec. Add test that fails under the wrong choice. | #2 discrepancy | 01 §A1, 04 §I-2 | 0.25 d |
| A2 | Flip QW-5 math multiplier 1.15× → 0.90×. Add `overflow: visible` to `.scriba-annot-fobj`. Add test cases from `math-samples/`. | #4 wrong direction | 05 §Rec | 0.25 d |
| A3 | Apply clamp **inside** collision check, not after. Repro test from #9 FALSIFIABLE. | #5 clamp races | 02 §9 | 0.5 d |
| A4 | Raise group opacity floor to ensure WCAG AA. Options: (a) bump `info` opacity to 0.75, drop hover-dimming; (b) re-palette to satisfy AA at opacity 1.0; (c) remove group opacity entirely and use per-element fill alpha. | #1 contrast fail | 10 §Contrast | 0.75 d |
| A5 | Re-palette `info` / `path` to distinct hex. Pick CVD-distinguishable `warn`/`good`/`error` via simulator. | #10 CVD + hex collision | 10 §CVD | 0.5 d |

Total P0: ~2.25 agent-days. Ship before starting MW-2.

### P1 — Fold into MW-2 / MW-3

| # | Action | Fixes | Audit ref | MW |
|---|--------|-------|-----------|-----|
| B1 | MW-3 first: `_place_pill(natural_x, natural_y, pill_w, pill_h, l_font_px, side_hint, placed_labels, viewbox_w, viewbox_h)` — deletes 3 copies of the compute→nudge→clamp→register sequence. Port `emit_position_label_svg` to `_nudge_candidates`. | #7 + #8 | 07 §MW-3, 01 §12 | MW-3 |
| B2 | MW-2 typed registry: `kind: LabelKind ∈ {pill, cell_text, leader_path, decoration}`. Primitive seeders for DPTable, Array, Grid, Plane2D, Graph, Tree. | #11 + #3 | 07 §MW-2, 03 | MW-2 |
| B3 | Wire headroom (`position_label_height_above/below`) in every primitive that dispatches through `base.emit_annotation_arrows` — not just Array/DPTable. | #6 | 03, 07 | MW-2 |
| B4 | Fix viewBox clip: allocate above-top-edge corridor by N-pill count per frame before finalizing viewBox height. | #3 systemic | 06 §Root cause | MW-2 |
| B5 | Test backfill: `layout="2d"` branches, `emit_position_label_svg` collision, `_wrap_label_lines` with inputs long enough to trigger QW-4. Target coverage 85 %+. | #8 | 04 §Gaps | MW-3 |
| B6 | `position_label_height_below` math branch: mirror the 32/24 px split from `_above`. | #16 | 01 §I-9 | MW-2 |
| B7 | Accessibility §9 invariants A-1..A-14 added to ruleset. Enforced by CSS + tests. | #1, #10 | 10 §Invariants | MW-2 |

Total P1: Extends MW-2/3 cost estimates from agent #7. New totals:
- MW-3: 0.75 + 0.25 (B1 position port) + 0.25 (B5 tests) = **1.25 d**
- MW-2: 1.5 + 0.25 (B3) + 0.5 (B4 corridor) + 0.1 (B6) + 0.5 (B7 css+tests) = **2.85 d**

### P2 — Defer or bundle into MW-4

| # | Action | Fixes | Audit ref | When |
|---|--------|-------|-----------|-----|
| C1 | Pre-sort candidate table as module constant. | #13 perf | 09 §OPT-A | MW-2 polish |
| C2 | `@functools.cache` on `_label_width_text` per `(label, font_px)`. | #13 perf | 09 §OPT-C | MW-2 polish |
| C3 | Drop dead code: `emit_arrow_marker_defs`, `pill_w` param. | #15 | 01 §Dead | MW-3 cleanup |
| C4 | Step-size rationale: document why `(0.25, 0.5, 1.0, 1.5)` or switch to `(0.25, 0.5, 1.0, 2.0)` with a benchmark. | #12 | 02 §5 | MW-4 |
| C5 | MW-4a: `forbidden_region: BoundingBox \| None` param on `_place_pill`. Plane2D passes content bbox → fixes bug-E/F without force solver. | #7 alt | 07 §MW-4a | After MW-2 |
| C6 | MW-4b (only if MW-4a insufficient): d3fc greedy argmin-by-overlap-area + adjustText anchor distance tie-break. Deterministic. | #14 | 08 §MW-4, 07 §MW-4b | Conditional |
| C7 | Screen-reader semantics: drop `role="img"` on SVG root; put `aria-labelledby` targets in `aria-hidden=false` region. | #10 | 10 §SR | MW-2+ |

---

## Revised roadmap

```
NOW → P0 batch (A1..A5) → ship → re-run visual regression
  ↓
MW-3: _place_pill helper + dead code + P0 tests
  ↓
MW-2: typed registry + primitive seeders + corridor + a11y §9 + P2 perf
  ↓
MW-4a: forbidden_region param for Plane2D
  ↓ (conditional)
MW-4b: greedy argmin solver — only if Plane2D forbidden_region insufficient
```

---

## What changes in the ruleset itself

The following deltas should land in `docs/spec/smart-label-ruleset.md` after
P0 ships:

1. **I-2**: re-state pad value to match `overlaps()` implementation (or update
   both after A1 decision).
2. **I-9**: extend to cover `position_label_height_below` math branch (B6).
3. **Add I-11 (leader length floor)**: "Arrow leader length MUST be ≥ 30 px
   or the leader is suppressed" — promote `_svg_helpers.py:937` magic
   number to a named constant + spec rule.
4. **Add I-12 (position-only algorithm parity)**: once B1 ships, state that
   `emit_position_label_svg` uses `_nudge_candidates` identically to the
   arrow emitters. Until then, mark `emit_position_label_svg` as using a
   non-parity algorithm.
5. **Add §9 Accessibility** with A-1..A-14 (agent #10 full proposal):
   opacity-corrected contrast floor, hover-dim floor, CVD distinguishability,
   accessible name requirements, forced-colors fallback, font-size minimum.
6. **Update §2.3** known limitations: reduce from "registry is pill-only" to
   "registry will track pill + cell_text + leader_path + decoration after
   MW-2; prior to MW-2, only pill is tracked."
7. **Update §5 known-bad repros**: add pill-arrow collision category (34.6 %
   of frames) — not covered by any current bug letter.
8. **Add §10 Environment flags table** — consolidate `SCRIBA_DEBUG_LABELS`,
   `SCRIBA_LABEL_ENGINE`, and any new flags from P1/P2.

---

## Numeric scorecard

| Metric | Current | Target (post-MW-2) | Audit ref |
|--------|---------|--------------------|-----------|
| Frame visual cleanliness (pill-bearing) | 12.7 % | ≥ 85 % | #6 |
| Line+branch coverage `_svg_helpers.py` | 73 % | ≥ 85 % | #4 |
| Primitives fully wired | 2 / 15 | 15 / 15 | #3 |
| Math-width RMSE (11 px font) | 17.1 px | ≤ 8 px | #5 |
| WCAG AA pass rate across 6 tokens | 2 / 6 | 6 / 6 | #10 |
| CVD-distinguishable token pairs | 7 / 15 | 15 / 15 | #10 |
| `_nudge_candidates` cost @ N=50 | 6 ms | ≤ 2 ms | #9 |

---

## What this audit did NOT cover

- Temporal coherence (label persistence frame→frame) — scriba currently
  re-computes from scratch each frame.
- Interactive features — scriba is batch-only.
- Real KaTeX glyph metrics via a headless measure round-trip — would require
  a two-pass render pipeline.
- Priority-weighted culling à la Mapbox — all labels in scriba are required.
- Cross-primitive registry (two primitives in one scene sharing a registry).
- Per-theme contrast audit beyond light + dark.
