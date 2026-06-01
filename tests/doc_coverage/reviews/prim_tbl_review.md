# Render-content review: `prim_tbl_` (Array / Grid / DPTable / Matrix)

**Date:** 2026-06-01
**Reviewer scope:** content-correctness ("renders ok but wrong content") over the 36 `prim_tbl_*` snippets.
**Method:** READ-ONLY. For each snippet I extracted the stage `<svg>` (the one whose `<g>` cells carry `data-target="a|g|dp|m.…"`, distinct from the ~400 KB shared shell that embeds unrelated example primitives) and verified: cell-element count vs declared dims, per-cell `scriba-state-*` highlight placement, cell value/label text, captions, axis labels, arrow geometry, and Matrix fill behaviour.

## Summary tally

**36 / 36 OK — 0 SUSPECT.**

- 23 snippets render HTML; all verified structurally correct.
- 13 snippets are negative tests (`expect: error E####`) with **no HTML** by design — nothing to verify in render output. They are listed OK (= no render-content defect; the error path is out of scope for this HTML review).

Two behaviours are *intentional design* worth recording (NOT bugs): inclusive `range[i:j]` selection, and the per-cell 1px inset on cell rects. Detail in the Notes section.

## Per-snippet table

| id | intent | verdict | reason |
|----|--------|---------|--------|
| prim_tbl_array_anim_value | Array value change across anim steps | OK | 2 steps: f0 cell[0]=5/current; f1 cell[0]=done + cell[1]=9. states+values exact |
| prim_tbl_array_apply_value | Array set cell via apply | OK | cell[0]="42", cells 1-3 blank (no data) — correct |
| prim_tbl_array_data | Array data matching size | OK | size=4 → 4 rects, values 1,3,5,7 |
| prim_tbl_array_data_mismatch | E1402 (data len) | OK | negative test, no HTML (by design) |
| prim_tbl_array_label | Array label caption | OK | size=3 → 3 cells, KaTeX caption `$arr$` in foreignObject; cells blank (no data) |
| prim_tbl_array_labels | labels "0..7" + caption | OK | 8 cells, values 1..15 interleaved with index labels 0..7 |
| prim_tbl_array_labels_named | named labels dp[0]..dp[7] | OK | 8 cells, labels dp[0]..dp[7], blank values |
| prim_tbl_array_missing_size | E1400 | OK | negative test, no HTML |
| prim_tbl_array_n_alias | n alias of size | OK | n=4 → 4 cells |
| prim_tbl_array_sel_all | all=dim | OK | all 5 cells scriba-state-dim |
| prim_tbl_array_sel_cell | cell[2]=current | OK | only a.cell[2] = current |
| prim_tbl_array_sel_range | range[1:3]=done | OK | cells 1,2,3 = done (inclusive range — see Notes) |
| prim_tbl_array_size | size param | OK | size=5 → 5 rects/5 texts/5 targets |
| prim_tbl_array_values_alias | values alias | OK | 4 cells, values 2,4,6,8 |
| prim_tbl_dptable_1d | 1D n+labels+label | OK | 7 cells, index labels 0..6 + caption dp[i] |
| prim_tbl_dptable_1d_data | 1D flat data | OK | 4 cells, values 0,1,2,3 |
| prim_tbl_dptable_2d | 2D rows×cols | OK | 6×6 = 36 cells + caption dp[l][r] |
| prim_tbl_dptable_2d_data | 2D flat data | OK | 2×3 = 6 cells, values 1..6 row-major |
| prim_tbl_dptable_apply | fill cell via apply | OK | cell[0]="0", rest blank |
| prim_tbl_dptable_arrow | transition arrow | OK | 5 cells + 1 `<path>` arrow + `from` label tooltip |
| prim_tbl_dptable_cellcap | E1425 (cell cap) | OK | negative test, no HTML |
| prim_tbl_dptable_data_mismatch | E1429 | OK | negative test, no HTML |
| prim_tbl_dptable_data_nested | E1429 (must be flat) | OK | negative test, no HTML |
| prim_tbl_dptable_missing | E1426 | OK | negative test, no HTML |
| prim_tbl_dptable_sel_cell1d | cell[2]=current | OK | only dp.cell[2] = current |
| prim_tbl_dptable_sel_cell2d | cell[1][2]=current | OK | 4×4=16 cells, only dp.cell[1][2] = current |
| prim_tbl_dptable_sel_range1d | range[1:3]=done | OK | cells 1,2,3 = done (inclusive range) |
| prim_tbl_grid_basic | rows×cols default | OK | 3×3 = 9 cells |
| prim_tbl_grid_data_flat | flat data + label | OK | 2×3=6 cells, values 1..6 + caption Board |
| prim_tbl_grid_data_mismatch | E1412 | OK | negative test, no HTML |
| prim_tbl_grid_data_nested | nested 2D data | OK | 2×3=6 cells, values 1..6 row-major (matches flat) |
| prim_tbl_grid_missing_cols | E1410 | OK | negative test, no HTML |
| prim_tbl_grid_sel_all | all=done | OK | all 9 cells = done |
| prim_tbl_grid_sel_cell | cell[1][2]=current | OK | only g.cell[1][2] = current |
| prim_tbl_matrix_axis_labels | row/col labels + label | OK | 2×2=4 cells + c0,c1 / r0,r1 axis labels + caption M |
| prim_tbl_matrix_basic | rows×cols default zeros | OK | 4×4=16 cells, uniform viridis fill (all zeros), no values |
| prim_tbl_matrix_cell_size | cell_size=40 | OK | 4 cells render 38px (40 − 1px inset each side); default basic is 22px → genuine scale-up |
| prim_tbl_matrix_cellcap | E1425 | OK | negative test, no HTML |
| prim_tbl_matrix_colorscale_unknown | E1421 | OK | negative test, no HTML |
| prim_tbl_matrix_colorscale_viridis | colorscale viridis | OK | 2×2=4 cells, uniform mid-viridis teal (all-zero data → all equal) |
| prim_tbl_matrix_data_flat | flat data + show_values | OK | 4 cells, values 0.1/0.3/0.5/0.9, viridis gradient |
| prim_tbl_matrix_data_mismatch | E1422 | OK | negative test, no HTML |
| prim_tbl_matrix_data_nested | nested 2D data | OK | 4 cells viridis gradient row-major; no values (show_values off) |
| prim_tbl_matrix_heatmap_alias | Heatmap = Matrix alias | OK | 3×3=9 cells, identical rendering to Matrix |
| prim_tbl_matrix_missing | E1420 | OK | negative test, no HTML |
| prim_tbl_matrix_sel_all | all=done | OK | all 9 cells = done |
| prim_tbl_matrix_sel_cell | cell[1][2]=current | OK | only m.cell[1][2] = current |
| prim_tbl_matrix_vmin_vmax | vmin/vmax clamp | OK | 4 cells, data [0,1,2,3] vmin=0 vmax=3 → full viridis spread purple→yellow |

## SUSPECTS

None. No render-bug or wrong-content findings in this prefix.

## Notes (intentional behaviours, recorded for completeness — not defects)

1. **Inclusive `range[i:j]`.** Both `prim_tbl_array_sel_range` (`a.range[1:3]`) and
   `prim_tbl_dptable_sel_range1d` (`dp.range[1:3]`) highlight **three** cells
   (indices 1, 2, **and** 3), not the two a Python half-open slice would give.
   This is consistent across both primitives, so it is the documented
   inclusive-range selector semantics, not a render bug. Classified **expected**.
   (Worth a one-line confirmation against SCRIBA-TEX-REFERENCE that `range[i:j]`
   is intended inclusive on both ends — the corpus render is internally consistent
   either way.)

2. **1px cell inset.** Every cell `<rect>` sits at `x="1.0" y="1.0"` with
   width/height = declared cell size − 2 (e.g. `cell_size=40` → 38px rect;
   default Matrix cell 24 → 22px rect; default Array cell 60 → 58px rect). This is
   a uniform stroke/gap inset applied by the renderer, verified consistent across
   Array/DPTable/Grid/Matrix. The cell *does* scale with `cell_size` (38 vs the
   default 22), so the param takes effect. Classified **expected**.

3. **Matrix fill correctness.** Viridis fills verified to vary correctly with data:
   uniform teal `rgb(33,145,140)` for all-equal data (basic / viridis / heatmap),
   full purple→yellow spread for `vmin_vmax` data [0,1,2,3], and a graded sequence
   for nested [[0.1,0.3],[0.5,0.9]]. Row-major ordering confirmed throughout.

4. **Animation frames.** `prim_tbl_array_anim_value` emits 4 stage SVGs (the two
   authored steps, duplicated for the playback buffer). Step states/values are
   exact: step1 cell[0]=5 `current`; step2 cell[0]=`done` + cell[1]=9.

## Cross-check vs SANITY-FLAGS.md

Phase-1 reported `prim_tbl_` as 0/36 flagged (clean) on its heuristics. This
content-level review independently confirms 0 defects in the 23 rendered
snippets, so the two layers agree for this prefix.
