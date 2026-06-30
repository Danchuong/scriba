# Structural Lift — annotation legibility to all primitives (no-debt)

**Status:** In progress · **Date:** 2026-06-30 · cross-validated by 3 research agents (matrix / architecture / blast-radius).

## Goal
Extend Array's annotation-legibility fixes (caption wrap+width-in-bbox+bottom, range anchor+bracket, below-lane+leader, target-cell obstacle) to the other primitives **structurally** (lift to `PrimitiveBase` + opt-in per-primitive hooks), with a **regrowth-guard ratchet** so the bug class cannot return = no technical debt.

## Hard constraint (unanimous across agents)
Keep the lift **additive**: override per-primitive hooks + lift caption rendering into concrete `PrimitiveBase` helpers, but **DO NOT change the formulas** of `position_label_height_above/below` or `_wrap_label_lines`. Under this rule every conformance gate (R-32, ac6_below_math, smart_label SHA ×3, determinism) stays green; only `test_primitive_grid.py:168` and `test_primitive_numberline.py:169` (with-label bbox height literals) need edits.

## Layers (opt-in; base defaults are no-op → non-opting primitives byte-stable)
- **A — caption block** (wrap + width-in-bbox + bottom placement). Lift `_caption_lines`/`_caption_block`/`_emit_caption`/`_footprint_width`/`_content_dx` to base; each primitive supplies `content_width` + `content_bottom`. Applies to 11 caption-bearers (NOT plane2d/metricplot; codepanel = top-header, separate).
- **B — range anchor + bracket** (1D only). dptable, numberline (Array done). Bracket already emitted by `emit_position_label_svg`. NOT 2D grids, NOT nodes.
- **C — below-lane + leader + target-cell obstacle**. Mechanism already in base/_svg_helpers; primitive supplies cell box (`resolve_annotation_box`) + below baseline (`resolve_below_baseline`) [+ `resolve_label_anchor` if top-anchored]. Rectangular-cell primitives. NOT graph/tree (circle nodes, center+`_arrow_shorten`), NOT plane2d (point/segment).

## Carve-outs (the R1 lesson — never violate)
`resolve_annotation_point` stays box-free (node center+shorten, segment midpoint). Layer B never for node/2D. Layer C hooks stay `None` for graph/tree/plane2d (leader/bracket gated on `cell_width is not None`). `resolve_label_anchor` +CELL_HEIGHT/2 only for top-anchored cell primitives.

## Adoption matrix
| Primitive | A | B | C | label_anchor | Notes |
|-----------|---|---|---|--------------|-------|
| array | ✓ done | ✓ | ✓ | ✓ | reference |
| dptable | ✓ | ✓(1D) | ✓ | – (center) | only non-Array with position=below; range accepted-but-dropped |
| numberline | ✓ | ✓ | ✓(degenerate box) | ✓ (tick top) | range accepted-but-dropped |
| grid | ✓ | ✗(2D) | ✓ | – | 0 range handling |
| matrix | ✓ | ✗ | (needs annot pipeline) | – | caption-only; 0 golden |
| queue | ✓ | ✗ | ✓ | ✓ (top) | |
| linkedlist | ✓ | ✗ | ✓ | ✓ (top) | |
| stack | ✓ | ✗ | (needs annot pipeline) | – | caption-only |
| hashmap | ✓ | ✗ | ✓ (row blocker) | – | lane marginal |
| variablewatch | ✓ | ✗ | ✓ (row blocker) | – | lane marginal |
| tree | ✓ (width+wrap; height already reserved) | ✗ | ✗ | – | node anchor |
| graph | ✓ (full: reserve+overlap = latent bug) | ✗ | ✗ | – | node anchor |
| codepanel | top-header (separate) | ✗ | ✗ | – | out of A |
| metricplot / plane2d | ✗ (no caption) | ✗ | ✗ | – | out |

## Regrowth guard (the no-debt ratchet)
Parametrized test over the registry × scenarios (no-ann / long caption / position=below / range). Render through real `compute_viewbox` + `emit_svg`; assert every drawn rect/line/path/pill/caption-extent ∈ padded viewBox. `_MIGRATED` set + `xfail(strict=True)` for not-yet-migrated → migrating flips xfail→XPASS→fails until added to `_MIGRATED` → monotonic. Reuse `test_obstacle_protocol.py` `_make_instance` recipe.

## Implementation order (no-debt: foundation → migrate → ratchet)
0. **Lift Layer A to `PrimitiveBase`** (concrete helpers). Migrate **Array** onto them (de-dup; Array golden must stay stable / rebaseline identically). Foundation.
1. **Regrowth guard** test (Array migrated; all others xfail-tracked).
2. **graph caption** (opt into Layer A: reserve height + shift content; mirrors tree). Add to _MIGRATED.
3. **Cell-grid cluster**: dptable (A+B+C), numberline (A+B+C), grid (A+C), matrix (A). 
4. **Linear cluster**: variablewatch, queue, linkedlist, hashmap, stack (A [+C where it helps]).
5. **tree** (A width+wrap).
6. plane2d/metricplot/codepanel: out (documented).

Each step: TDD/new tests for range (no corpus coverage) + full suite + `SCRIBA_UPDATE_GOLDEN` reviewed per phase + flip _MIGRATED + self-review. Anything not reached stays xfail-tracked by the guard = explicit, not silent debt.

## Migration status — Layer A COMPLETE (2026-06-30)

**Layer A (caption fits its bbox) is done for every caption-bearing primitive.**
The regrowth guard (`tests/unit/test_caption_within_bbox.py`) now has **zero**
"still clips" entries: the defect class is eliminated catalog-wide and
CI-enforced (`_CAPTION_MIGRATED` is monotonic — any regression fails the gate).

**Done + committed:**
- Foundation: Layer A caption helpers lifted to `PrimitiveBase`
  (`_caption_lines`/`_caption_block_width`/`_caption_block_height`/`_emit_caption`,
  later generalized with `origin_x` + the top-band helpers `_top_caption_band`/
  `_emit_top_caption`). Array de-duplicated onto them.
- Regrowth-guard ratchet; graph caption overlap fix (reserve band + shift).
- **Centered Layer-A caption** (fold width + wrap) for the 12 data primitives:
  array, queue, hashmap, linkedlist, variablewatch, matrix, stack, **grid,
  numberline, dptable** (3-case bbox unified via `_caption_top_y`; fixes a
  latent 2D bottom-clip), **tree, graph** (top band, frame-aware via
  `origin_x=-r`; int footprint preserved so scaled transforms stay byte-stable).
- **codepanel** — its label is a left-aligned IDE-tab title (panel width driven
  by code, not title), so it fits by **ellipsis truncation** (`_header_label`),
  not width-fold. Added to the guard with that rationale.
- 4 unit-literal edits (grid:168, numberline:169 + phase_b_numberline:293);
  golden rebaselines per primitive, each verified to be the intended geometry
  delta only (no cell/text drift).

**Deferred (explicit, NOT silent debt — separate defect class, needs new tests):**
- **Layer B** (range anchor + `┌──┐` bracket) for dptable/numberline and
  **Layer C** (below-lane + leader) for the cell-grid set. The mechanism is
  already in base/`_svg_helpers` (gated on `cell_width is not None` + `is_range`);
  what's missing is per-primitive opt-in + **new unit tests** (0 corpus coverage —
  no example uses range/below annotations on a non-Array primitive). Tracked here;
  to be picked up as a follow-up epic, not blocking the caption fix.

## Blast radius (agent 3)
~42 distinct goldens total (~14 re-churn across multi-primitive scenes). Only 2 mandatory unit-literal edits (grid:168, numberline:169). Range fix = 0 golden churn → needs new unit tests. Cluster co-occurring primitives (test_reference_datastruct, 07_prescan, test_reference_edge_cases) to rebaseline once.
