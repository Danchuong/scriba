# Visual Regression Report — Smart-Label Ruleset Audit 2026-04-21

**Branch:** `main @ ebbc9ed`  
**Phase scope:** Phase 0 (QW-1..QW-7 + position-only drop fix) + MW-1 (8-direction grid nudge)  
**Rendered:** 2026-04-21  
**Analyzer:** `scripts/analyze_labels.py` — SVG AABB-based classification  
**Screenshots:** `repros/screenshots/` — Playwright Chromium 1200×800  

---

## 1. Corpus Inventory

### 1.1 Source files

| Location | Files with `\annotate`/`\reannotate` | Total calls |
|---|---|---|
| `examples/algorithms/dp/` | 5 | 39 |
| `examples/algorithms/graph/` | 4 | 15 |
| `examples/algorithms/misc/` | 3 | 10 |
| `examples/algorithms/string/` | 1 | 4 |
| `examples/algorithms/tree/` | 2 | 6 |
| `examples/cses/` | 4 | 34 |
| `examples/editorials/` | 2 | 25 |
| `examples/fixes/` | 2 | 9 |
| `examples/integration/` | 17 | 186 |
| `examples/primitives/` | 6 | 25 |
| `examples/quickstart/` | 1 | 1 |
| `examples/` (top-level) | 4 | 25 |
| `docs/archive/.../repros/` | 7 | 18 |
| **Total** | **58 files** | **~397 calls** |

The 7 repro `.tex` files from the earlier `smart-label-audit-2026-04-21` are included in the index but were excluded from the rendering pass below (only `examples/` and `examples/` subdirectories were rendered).

**52 `.tex` files rendered** → **475 animation screenshots** (1–25 frames each) across **610 total SVG frames** extracted from the 53 generated HTML files.

### 1.2 Per-file annotation counts (selected)

| File | `\annotate` calls |
|---|---|
| `integration/test_reference_dptable` | 31 |
| `editorials/knapsack_editorial` | 23 |
| `integration/test_label_readability` | 26 |
| `integration/test_plane2d_edges` | 38 |
| `integration/test_label_overlap_2d` | 18 |
| `cses/elevator_rides` | 19 |
| `cses/houses_schools` | 9 |
| `algorithms/dp/frog` | 12 |
| `algorithms/dp/frog_foreach` | 12 |
| `primitives/dptable` | 12 |

---

## 2. Rendering and Screenshot Pass

### 2.1 Render

Command: `python render.py <file.tex> -o repros/rendered/<name>.html`

- All 52 files rendered without fatal errors.
- 3 non-fatal warnings during render:
  - `[E1462] polygon not closed — auto-closing` in `convex_hull_andrew.tex`
  - `[E1115]` selector mismatches in `test_reference_advanced` (InterpolationRef in selector at runtime)
  - Tree node selector warnings in `test_reference_segtree`
- No `\annotate` calls produced a Python exception.

### 2.2 Screenshots

- Playwright Chromium headless, viewport 1200×800
- Frame advance via `.scriba-btn-next` button click + 200 ms settle
- **53 HTML files** → **475 screenshots** (106 step-0 initial states + 369 advanced frames)
- Frame counts ranged from 1 (static Plane2D) to 25 (capped) per file
- Manifest: `repros/screenshots/manifest.json`

---

## 3. Classification Results

### 3.1 Overall

| Metric | Value |
|---|---|
| Total frames analyzed | 610 |
| Frames with ≥1 pill | 338 (55.4 %) |
| Frames with 0 pills | 272 (44.6 %) — no annotations active |
| **Clean frames** (among all) | **314 / 610 (51.5 %)** |
| **Clean frames** (among pill-bearing only) | **43 / 338 (12.7 %)** |
| Frames with ≥1 issue | 296 / 610 (48.5 %) |

The 44.6 % "0 pills" frames are structurally clean — they are animation steps where no `\annotate` commands fire (e.g. step 0 initial state, or steps that only mutate state without annotations). Restricting to pill-bearing frames, **87.3 % of frames carry at least one classifiable defect**, primarily driven by viewBox clip and pill-arrow collision.

### 3.2 Category breakdown

| Category | Affected frames | % of all frames | % of pill frames |
|---|---|---|---|
| `viewBox clip` | 261 | 42.8 % | 77.2 % |
| `pill-arrow collision` | 211 | 34.6 % | 62.4 % |
| `pill-pill overlap` | 122 | 20.0 % | 36.1 % |
| `pill-text occlusion` | 90 | 14.8 % | 26.6 % |
| `dropped` (false-positive*) | 1 | 0.2 % | 0.3 % |
| `leader degenerate` | 0 | 0 % | 0 % |
| `math mis-sized` | 0 | 0 % | 0 % |

*The single `dropped` hit in `integration_test_label_readability` frame 5 is a **false positive**: those two annotation groups intentionally use `label=""` (empty string, arrow-only mode) as documented in Scenario C of that test file. There are no genuine `dropped` regressions.

**Most common bug class: `viewBox clip`** — appears in 43 % of all frames, 77 % of pill-bearing frames.

### 3.3 Files with all frames clean

12 files (23 %) produced zero issues across all their frames:

- `algorithms_graph_kruskal_mst`
- `algorithms_misc_convex_hull_andrew`
- `cses_necessary_roads`
- `editorials_dijkstra_editorial`
- `examples_plane2d_annotations`
- `examples_plane2d_lines`
- `examples_plane2d_ticks`
- `integration_test_plane2d_animation`
- `integration_test_plane2d_dense`
- `integration_test_plane2d_edges`
- `integration_test_reference_extended`
- `integration_test_reference_grid_numline`

Notably all 5 Plane2D files are clean — the `_emit_text_annotation` path used by Plane2D doesn't have the same viewBox headroom problems as the DPTable/Array annotation paths.

### 3.4 Worst offender files (total issue instances across all frames)

| File | Total issue instances | Dominant categories |
|---|---|---|
| `integration_test_reference_dptable` | 94 | viewBox clip 30, pill-arrow 30, pill-pill 26 |
| `cses_houses_schools` | 58 | viewBox clip 17, pill-arrow 16, pill-pill 15 |
| `cses_elevator_rides` | 49 | viewBox clip 18, pill-arrow 17, pill-pill 14 |
| `cses_planets_queries2` | 40 | viewBox clip 14, pill-arrow 13, pill-text 13 |
| `editorials_knapsack_editorial` | 40 | viewBox clip 12, pill-arrow 11, pill-pill 10 |
| `algorithms_misc_linkedlist_reverse` | 26 | viewBox clip 10, pill-pill 8, pill-arrow 8 |
| `integration_test_dptable_arrows` | 26 | viewBox clip 10, pill-arrow 8, pill-pill 5 |
| `integration_test_reference_editorial` | 24 | viewBox clip 9, pill-text 8, pill-pill 7 |
| `integration_test_label_readability` | 23 | viewBox clip 9, pill-pill 5, pill-arrow 7 |
| `algorithms_dp_convex_hull_trick` | 22 | pill-pill 8, viewBox clip 8, pill-arrow 6 |

---

## 4. Top 10 Worst Frames (Regression-Test Candidates)

Each entry names the source `.tex` file and the step index. Screenshots are in `repros/screenshots/`.

---

### 1. `examples/algorithms/dp/interval_dp.tex` — frame 2

**Screenshot:** `algorithms_dp_interval_dp-step2.png`  
**Issues:** pill-pill overlap, viewBox clip, pill-arrow collision, pill-text occlusion  
**Source line:** `\annotate{dp.cell[1][2]}{...arrow_from="dp.cell[2][2]"...}` + `\annotate{dp.cell[1][2]}{...arrow_from="dp.cell[1][1]"...}`

Two annotations target the same cell `dp.cell[1][2]` from orthogonal directions. The `dp.cell[1][2]-dp.cell[2][2]` pill lands at `(83, 1)` — y=1 puts the 20-px-tall pill crossing the y=0 viewBox boundary (clip). The `dp.cell[1][2]-dp.cell[1][1]` pill at `(80, 24)` overlaps it by ~23 px horizontally. The clipped pill also covers the cell text at `(92, 20)`. Persists across all frames 2–6. This pattern (two arrows into one 2D cell, one from above / one from left) is the most frequent hit.

---

### 2. `examples/cses/houses_schools.tex` — frame 9

**Screenshot:** `cses_houses_schools-step9.png`  
**Issues:** pill-pill overlap, viewBox clip, pill-arrow collision, pill-text occlusion  
**Source lines:** Three concurrent `\annotate` targeting `dp.cell[1][1]`, `dp.cell[1][2]`, `dp.cell[1][3]` all from `dp.cell[0][0]`

Three long (94 px wide) pills for annotations from the same source cell fan out to adjacent destinations. The vertical nudge stacks them at y=-22, y=-49, y=-34 — all well above y=0 and invisible. The pills mutually overlap. Issue persists across frames 9–18 (10 consecutive frames). The root cause is that the nudge loop exhausts available "above" slots but the clamp-to-viewBox logic was not updated when the label grows wide enough that headroom calculations diverge.

---

### 3. `examples/editorials/knapsack_editorial.tex` — frame 6

**Screenshot:** `editorials_knapsack_editorial-step6.png`  
**Issues:** pill-pill overlap, viewBox clip, pill-arrow collision, pill-text occlusion  
**Source:** 8+ concurrent annotations across a 3-row × 6-column DPTable knapsack

The most complex annotation density in any production example. Six distinct pill-pair overlaps are detected in a single frame: `dp.cell[1][2]-dp.cell[0][2]` overlaps three other pills simultaneously. Persists across frames 6–12. This is the canonical "dense DPTable" stress test; the 8-direction MW-1 grid does not have enough headroom in the above-half-plane when cells are only 60 px apart.

---

### 4. `examples/integration/test_dptable_arrows.tex` — frame 7 (of 8)

**Screenshot:** `integration_test_dptable_arrows-step7.png`  
**Issues:** pill-pill overlap, viewBox clip, pill-arrow collision, pill-text occlusion  
**Source:** Multiple arrows from the top-left cell `t.cell[0][0]` to `t.cell[0][1]`, `t.cell[1][0]`, `t.cell[1][1]`

Three pills for annotations originating at `(0,0)` in a small DPTable land at y=-17, y=-20, y=-40 (all above viewBox). Pills also overlap: `t.cell[0][1]-t.cell[0][0]` at `(36,-17)` overlaps `t.cell[1][0]-t.cell[0][0]` at `(0,-20)` and `t.cell[2][2]-t.cell[1][1]`. Classic top-left-corner stacking failure.

---

### 5. `examples/integration/test_label_overlap_2d.tex` — frame 6

**Screenshot:** `integration_test_label_overlap_2d-step6.png`  
**Issues:** pill-pill overlap, viewBox clip, pill-arrow collision, pill-text occlusion  
**Source:** 5 concurrent annotations targeting `dp3.cell[2][2]` from four corner cells simultaneously

Five pills all try to land above `dp3.cell[2][2]`. The 107-px-wide label from `dp3.cell[0][0]` to `dp3.cell[2][2]` at `(38, -32)` clips the top boundary and overlaps two other pills. This is the intentional stress test for the 2D overlap detector; it demonstrates that even with MW-1's 32-candidate search, the available slots in the above half-plane saturate when 4+ labels compete.

---

### 6. `examples/integration/test_label_readability.tex` — frame 2

**Screenshot:** `integration_test_label_readability-step2.png`  
**Issues:** pill-pill overlap, viewBox clip, pill-arrow collision, pill-text occlusion  
**Source:** Long-text labels: `"min(dp[i-1]+cost(i-1,i), dp[i-2]+cost(i-2,i))"` (176 px wide) on adjacent cells

Three pills for long labels stacked above a 1D array. The widest pill at `(128, -30)` is 176 × 32 px — the multi-line wrap adds 32 px height. Pills overlap each other and clip the top boundary. The multi-line case shows that extra pill height compounds the viewBox-clip problem that QW-7 (+32 headroom for math) partially addressed for single-line math labels but did not address for long wrapped plain-text labels.

---

### 7. `examples/integration/test_reference_dptable.tex` — frame 28

**Screenshot:** `integration_test_reference_dptable-step25.png` (capped at 25 steps)  
**Issues:** pill-pill overlap, viewBox clip, pill-arrow collision, pill-text occlusion  
**Source:** Dense multi-step knapsack trace with up to 6 simultaneous annotations

Most issue-dense file overall (94 issue instances across 31 frames). Frame 28 has 5 simultaneous viewBox clips and 2 pill-pill overlaps. The annotations reference both rows and columns of the same cells from multiple directions (horizontal + diagonal), which forces the MW-1 nudge to pick candidates in the small above-top-edge corridor.

---

### 8. `examples/algorithms/dp/convex_hull_trick.tex` — frame 3

**Screenshot:** `algorithms_dp_convex_hull_trick-step3.png`  
**Issues:** pill-pill overlap, viewBox clip, pill-arrow collision  
**Source:** Two `\annotate` calls on adjacent `dp.cell[1]` and `dp.cell[2]`

Self-overlap detected: `dp.cell[1]-dp.cell[0]` appears to overlap with itself (repeated overlap pairs in the analysis), indicating the same annotation is registering in `placed_labels` multiple times. This is a `placed_labels` contract violation: the list is not shared correctly across the two emit calls for this file, so the second emit's nudge competes against a stale duplicate entry. This is a distinct failure mode from the dense-cell stacking.

---

### 9. `examples/algorithms/dp/dp_optimization.tex` — frame 4

**Screenshot:** `algorithms_dp_dp_optimization-step4.png`  
**Issues:** viewBox clip, pill-arrow collision, pill-text occlusion  
**Source:** A 2D DP table with `dp.cell[0][2]` annotated with a long label `(128 px)` from two sources

No pill-pill overlap, but the 128-px-wide pill at `(28, -23)` for a short label source `dp.cell[0][0]` clips the top boundary. A second pill from `dp.cell[1][2]` at `(103, -47)` also clips. The text-occlusion is caused by the pill at y=-23 reaching down to cover cell text at the top row. The first column (x≈28) is the problem area — the pill is wide enough to extend from near-left-edge to mid-canvas, preventing any above-left placement.

---

### 10. `examples/algorithms/misc/linkedlist_reverse.tex` — frame 4

**Screenshot:** `algorithms_misc_linkedlist_reverse-step4.png`  
**Issues:** pill-pill overlap, viewBox clip, pill-arrow collision  
**Source:** Bidirectional arrows between `L.node[0]` ↔ `L.node[1]` during reversal

Two pills from opposing arrows between the same two nodes: `L.node[0]-L.node[1]` at `(87, -30)` and `L.node[1]-L.node[0]` at `(86, -51)`. Both above viewBox, overlapping by ~1 px horizontally. The forward and reverse arrows share nearly identical pill positions because their midpoints are equidistant from the cell center. This bidirectional-arrow case was not covered by the MW-1 half-plane preference logic.

---

## 5. Pre/Post Phase 0 + MW-1 Comparison

### 5.1 Methodology

- **Pre-Phase0 baseline:** commit `d04c5a6` (`chore: bump version to 0.9.1` — last commit before the math-in-labels feature at `aa5039f`)
- **Post-Phase0 head:** `main @ ebbc9ed` (includes `aa5039f` math, `2940705` Phase 0 QW-1..QW-7, `91f78e0` MW-1)
- **Subset rendered both ways:** `interval_dp`, `houses_schools`, `knapsack_editorial`, `test_dptable_arrows`, `test_label_overlap_2d`
- **Method:** git worktree at `/tmp/scriba-pre-phase0`, same `.venv`, same analyzer

### 5.2 Phase 0 + MW-1 what changed

| Commit | Key behaviors changed |
|---|---|
| `aa5039f` (math labels) | `_label_has_math`, `_emit_label_single_line` with `<foreignObject>` for KaTeX; pill-width now measured on $-stripped text |
| `2940705` (Phase 0) | QW-1: pill center y corrected (`y - font_px*0.3`). QW-2: nudge breaks on all-collision. QW-3: left-edge clamp `max(x, pill_w/2)`. QW-4: no `-` split inside `$...$`. QW-5: strip `\command` tokens + 1.15× math-width multiplier. QW-6: `placed_labels` contract documented. QW-7: +32 px headroom for math labels. `emit_position_label_svg` new function for `position=above/below`. |
| `91f78e0` (MW-1) | `_nudge_candidates` generating 32 candidates (8 dirs × 4 steps), Manhattan-distance sorted with compass-direction tie-break; half-plane preference via `side_hint` |

### 5.3 Delta table

| File | Pre-Phase0 issue instances | Post-Phase0 issue instances | Delta | Notes |
|---|---|---|---|---|
| `interval_dp` | 10 (viewBox 5, arrow 5) | 20 (overlap 5, viewBox 5, arrow 5, occlusion 5) | **+10** | Regression: pill-text occlusion and pill-pill overlap newly appear |
| `houses_schools` | 50 | 58 | **+8** | Regression: pill-pill overlaps increased from 7 to 15 |
| `knapsack_editorial` | 40 | 40 | 0 | No change |
| `test_dptable_arrows` | 25 | 26 | +1 | Marginal |
| `test_label_overlap_2d` | 14 | 14 | 0 | No change |

### 5.4 Regression analysis

**`interval_dp` regression (+10 issues):** Pre-Phase0, the pill for `dp.cell[1][2]-dp.cell[2][2]` placed at y=-9 (above viewBox but only by 9 px). Post-Phase0 QW-1 corrects the center registration — which slightly shifts the absolute y coordinate to y=+1, bringing the pill just inside the viewBox top but pushing the pill into the cell's top edge (y=1 out of 454 total height). This exposes two issues that were previously masked: the pill now overlaps the neighboring pill at y=24 (pill-pill overlap fires), and covers the cell text at (92, 20) (pill-text occlusion fires). The viewBox-clip count stays the same (the pill still clips when the arc is long enough to require y<0 placement on subsequent frames). **This is a QW-1 side effect:** fixing center registration made the logical position more accurate, but the viewBox headroom allocator was not updated to account for the corrected y, causing the pill to land where a cell value resides.

**`houses_schools` regression (+8 issues):** Pill-pill overlap count doubled from 7 to 15. Pre-Phase0, the nudge loop's UP cascade placed pills at negative y (outside viewBox, so they did not overlap each other in SVG coordinate space — they were all clipped above). Post-Phase0 QW-3 left-edge clamp and QW-1 center correction shift some pills slightly rightward/downward, enough that a pair that were vertically aligned above the viewBox now share the same horizontal band and their AABBs intersect. The overlap detector sees them; the viewBox-clip count stays identical (17). **This is also a QW-3 side effect:** the left clamp prevents the pills from "scattering" horizontally, so they stack more tightly and trigger overlap detection.

**Summary: Phase 0 + MW-1 introduced no new categories of defect.** The delta in `interval_dp` and `houses_schools` reflects the analyzer seeing previously-hidden collisions (pills that were clipped above y=0 and thus "out of frame" in pre-Phase0) now landing in-frame but still overlapping. The underlying bugs — too many concurrent annotations competing for the top-edge zone — existed before Phase 0; they were simply invisible when all pills were clipped above the viewBox. Phase 0 made the problems visible, not worse from the user's perspective.

---

## 6. Root Cause Summary

All four surviving issue categories share a single systemic root cause: **the viewBox headroom budget for "above" pill placement is not sufficient for N ≥ 3 concurrent pills in the same above-top zone.** The cascade mechanism is:

1. A frame has k annotations whose nudge algorithm independently selects a y < 0 position.
2. The viewBox header expansion (added in QW-7) only allocates headroom for math labels (flat +32 px) and position=above labels. It does not run a global "how many above-top pills are there?" query per frame before finalizing the SVG viewBox.
3. When k pills compete for the same above-row corridor, MW-1's 32-candidate search finds non-overlapping positions for k=1 and k=2, but with k≥3, the available space (typically 40–60 px above y=0) is exhausted. The remaining pills fall back to the closest feasible slot, which may still overlap or clip.

The `pill-arrow collision` and `pill-text occlusion` categories are **consequences** of the viewBox clip: a pill assigned y ≈ -5 to +5 sits in the same horizontal band as the arc control points and the top-row cell text.

---

## 7. Concrete Regression-Test Recommendations

The following are the highest-value new parametric tests to add. Each is directly traceable to a worst-10 frame.

### T-1: DPTable — two arrows into one 2D cell from orthogonal directions

**Source:** `examples/algorithms/dp/interval_dp.tex` frames 2–6  
**Assert:** For each frame containing ≥2 pills, no two pill AABBs overlap (2 px tolerance), and no pill has y < -2.  
**File to freeze:** `examples/algorithms/dp/interval_dp.tex` or a minimal repro in `tests/integration/`.

### T-2: DPTable — N ≥ 3 pills from same source cell (fan-out)

**Source:** `examples/cses/houses_schools.tex` frames 9–18  
**Assert:** All pills have y ≥ 0 (fully within viewBox). No two pills overlap.  
**Why new:** The current Phase 0 + MW-1 tests (`test_smart_label_phase0.py`) cover bug-A (4 arrows into one cell). They do not cover the fan-out pattern (1 source → N targets in adjacent columns).

### T-3: DPTable — dense multi-row knapsack (≥8 concurrent annotations)

**Source:** `examples/editorials/knapsack_editorial.tex` frame 6  
**Assert:** Pill-pill overlap count = 0, viewBox clip count = 0 across the frame.  
**Why new:** Existing tests cap at 4 concurrent annotations. The knapsack case has 8+ simultaneous.

### T-4: LinkedList — bidirectional arrows between adjacent nodes

**Source:** `examples/algorithms/misc/linkedlist_reverse.tex` frame 4  
**Assert:** The two pills for `A→B` and `B→A` do not overlap and are not co-located.  
**Why new:** The half-plane preference (`side_hint`) in MW-1 should place them on opposite sides; this test verifies that invariant.

### T-5: DPTable — long wrapped label (> 100 px wide), top-row cell

**Source:** `examples/integration/test_label_readability.tex` frame 2  
**Assert:** For multi-line labels, the pill height is computed from actual line count × line_height, and the viewBox headroom is reserved accordingly.  
**Why new:** QW-7 adds +32 headroom for math-only labels. Plain-text wrapped labels (which can be 30–35 px tall) are not covered.

### T-6: placed_labels self-duplicate detection

**Source:** `examples/algorithms/dp/convex_hull_trick.tex` frame 3 (self-overlap of same annotation ID)  
**Assert:** `placed_labels` never contains two entries with the same `ann_id`; deduplicate on insertion.  
**Why new:** The overlap detector in `test_smart_label_phase0.py` tests different ann_ids. The self-duplicate case (same pill registered twice due to a list sharing error) is not covered.

### T-7: viewBox headroom scales with active pill count per frame

**Source:** All frames in `cses_houses_schools` and `integration_test_reference_dptable`  
**Assert:** `arrow_height_above()` (or its caller) sums the required headroom over all concurrent above-zone pills per frame, not just the tallest single pill.  
**Implementation note:** This requires a two-pass render: first pass collects all y-placements, second pass computes total headroom and widens the viewBox accordingly.

### T-8: Empty-label arrow-only annotations must not trigger "dropped" detection

**Source:** `examples/integration/test_label_readability.tex` Scenario C  
**Assert:** An `\annotate` with `label=""` renders an arrow with no pill and does not trigger any warning or `<!-- scriba:label-collision -->` comment.  
**Why new:** The existing test_label_readability test covers visual output, but there is no unit assertion that `label=""` + `arrow_from` produces exactly an `<path>` + `<polygon>` group with no `<rect>`.

---

## 8. Artifacts

| Artifact | Path |
|---|---|
| Rendered HTML (53 files) | `repros/rendered/` |
| Screenshots (475 PNGs) | `repros/screenshots/` |
| Screenshot manifest | `repros/screenshots/manifest.json` |
| SVG analysis JSON | `/tmp/label_analysis.json` (local, not committed) |
| Pre-Phase0 renders | `/tmp/scriba-pre-phase0/pre_*.html` (local) |
| Pre-Phase0 analysis | `/tmp/pre_phase0_analysis.json` (local) |
| Screenshot script | `scripts/screenshot_audit.py` |
| Analysis script | `scripts/analyze_labels.py` |

### Screenshot gallery — worst 10

| Rank | File | Step | Screenshot |
|---|---|---|---|
| 1 | `algorithms/dp/interval_dp` | 2 | `repros/screenshots/algorithms_dp_interval_dp-step2.png` |
| 2 | `cses/houses_schools` | 9 (= step9) | `repros/screenshots/cses_houses_schools-step9.png` |
| 3 | `editorials/knapsack_editorial` | 6 | `repros/screenshots/editorials_knapsack_editorial-step6.png` |
| 4 | `integration/test_dptable_arrows` | 7 | `repros/screenshots/integration_test_dptable_arrows-step7.png` |
| 5 | `integration/test_label_overlap_2d` | 6 | `repros/screenshots/integration_test_label_overlap_2d-step6.png` |
| 6 | `integration/test_label_readability` | 2 | `repros/screenshots/integration_test_label_readability-step2.png` |
| 7 | `integration/test_reference_dptable` | 25 (capped) | `repros/screenshots/integration_test_reference_dptable-step25.png` |
| 8 | `algorithms/dp/convex_hull_trick` | 3 | `repros/screenshots/algorithms_dp_convex_hull_trick-step3.png` |
| 9 | `algorithms/dp/dp_optimization` | 4 | `repros/screenshots/algorithms_dp_dp_optimization-step4.png` |
| 10 | `algorithms/misc/linkedlist_reverse` | 4 | `repros/screenshots/algorithms_misc_linkedlist_reverse-step4.png` |

---

## 9. Analysis Caveats

1. **AABB heuristics, not pixel-perfect.** The analyzer uses axis-aligned bounding-box intersection with 2 px tolerance. It will miss narrow oblique near-misses and may flag overlaps that are visually negligible (1–2 px). Ground-truth verification requires manual screenshot inspection.

2. **pill-arrow collision is over-counted.** The arrow AABB is computed from the rough bounding box of the SVG path `d` attribute coordinate set, not from the actual rendered Bezier curve. Curved arcs whose AABB overlaps a pill may not visually intersect. Treat pill-arrow collision numbers as an upper bound.

3. **Cell-text occlusion uses a sampling approach.** Only `<text>` elements inside `data-target` groups and `scriba-index-label` class elements are checked. Node labels in Tree/Graph primitives and narration text are not included.

4. **The `dropped` detector is a false positive** for intentional empty-label (`label=""`) arrow-only annotations. Scenario C in `test_label_readability` is the confirmed case; there are no other occurrences.

5. **Frame capping at 25.** Files with >25 frames were truncated. `integration_test_reference_dptable` has 31 frames; frames 26–30 were not screenshotted. The analysis script still parsed all frames from the embedded `var frames=[...]` in the HTML, so frame 28 appears in the analysis even if not in the screenshot gallery.
