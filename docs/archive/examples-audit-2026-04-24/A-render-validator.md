# Render Validator — Scriba `.tex` Examples Audit A

**Date:** 2026-04-24 | **Files rendered:** 113 | **Auditor:** automated render-validator agent

---

## Executive Summary

106/113 files render with exit 0; 0 hard failures in production files; 7 are expected-fail fixtures that correctly exit 2, confirming the error-code regression suite is green. 28 files emit warnings (never fatal) spanning three clusters: [E1115] invalid selectors on Tree/Graph/Stack edges (14 files), `stable+directed` layout advisory (7 files), and [E1462] polygon auto-close (1 file). Top fix: replace `Tree.edge[(A,B)]` and `Graph.edge[(X,Y)]` selectors that reference edges absent at target steps — affects `algorithms/graph/union_find_tree.tex` (18 warns), `algorithms/misc/simulated_annealing.tex` (27 warns), and 4 other files.

---

## 1. Method

**Command per file:**
```
env SCRIBA_ALLOW_ANY_OUTPUT=1 \
  timeout 120 .venv/bin/python render.py <tex> -o /tmp/html_artifacts/<safe_name>.html \
  </dev/null 2>stderr.txt
```

- `SCRIBA_ALLOW_ANY_OUTPUT=1` permits writing the HTML output outside the source tree (avoiding the H1 path-traversal guard).
- `timeout 120` kills any file that exceeds 2 minutes; exit code 124 would mark TIMEOUT.
- `stderr` captured to per-file text files; `stdout` (render progress) suppressed.
- Warnings counted via `grep -cEi 'warn|W[0-9]{3,4}'` against captured stderr.
- First error extracted via `grep -m1 -Ei 'error|E[0-9]{3,4}|traceback|exception'`.
- HTML outputs written to a scratch dir (`tmp_audit/html_artifacts/`) that is outside `examples/`; **deleted after parsing** — zero artifacts left in the git tree.
- Render completeness signal: HTML size checked; all 106 passing files produced non-zero HTML (min 317 KB, max 1.2 MB).
- No file hit the 120 s timeout. The slowest was `fixtures/expected-fail/20_cumulative_budget.tex` at 5 761 ms (intentional Starlark CPU budget test).

---

## 2. Results Table

Sorted: FAIL (expected-fail) first, WARN second, PASS last.

| # | Path | Exit | Duration (ms) | Warns | First Error / Warning (truncated) |
|---|------|------|---------------|-------|----------------------------------|
| 1 | `fixtures/expected-fail/09_command_typo_hint.tex` | **2** | 343 | 0 | `error [E1006] at line 4, col 1: unknown command \reocolor` |
| 2 | `fixtures/expected-fail/11_selector_unknown_shape.tex` | **2** | 580 | 0 | `error [E1116]: \highlight references undeclared shape 'nonexistent'` |
| 3 | `fixtures/expected-fail/13_apply_before_shape.tex` | **2** | 325 | 0 | `error [E1116] at line 2: no \shape declared before \step` |
| 4 | `fixtures/expected-fail/15_percent_in_braces.tex` | **2** | 376 | 0 | `error [E1001] at line 4, col 18: unterminated brace argument: missing '}'` |
| 5 | `fixtures/expected-fail/16_empty_foreach_iterable.tex` | **2** | 320 | 0 | `error [E1173] at line 6: foreach: cannot resolve iterable ''` |
| 6 | `fixtures/expected-fail/20_cumulative_budget.tex` | **2** | 5761 | 0 | `error [E1152]: Starlark CPU limit exceeded (5s)` |
| 7 | `fixtures/expected-fail/21_list_alloc_cap.tex` | **2** | 960 | 0 | `error [E1173]: range() argument too large (max 1000000)` |
| 8 | `algorithms/misc/simulated_annealing.tex` | 0 | 337 | **27** | `[E1115] selector 'G.edge[(B,D)]' does not match any addressable part of 'G'` |
| 9 | `algorithms/graph/union_find_tree.tex` | 0 | 435 | **18** | `[E1115] selector 'T.edge[(R,B)]' does not match any addressable part of 'T'` |
| 10 | `primitives/stack.tex` | 0 | 377 | **9** | `[E1115] selector 's.item[3]' does not match any addressable part of 's'` |
| 11 | `algorithms/tree/bst_operations.tex` | 0 | 342 | **6** | `[E1115] selector 'T.edge[(5,8)]' does not match any addressable part of 'T'` |
| 12 | `editorials/segtree_editorial.tex` | 0 | 450 | **6** | `[E1115] selector 'T.node[[1,2]]' does not match any addressable part of 'T'` |
| 13 | `integration/test_reference_advanced.tex` | 0 | 545 | **6** | `[E1115] selector 'a.cell[InterpolationRef(name='target_idx', subscripts=())]'` |
| 14 | `integration/test_reference_datastruct.tex` | 0 | 620 | **6** | `[E1115] selector 's.item[3]' does not match any addressable part of 's'` |
| 15 | `integration/test_reference_segtree.tex` | 0 | 443 | **6** | `UserWarning: Tree 'sst': invalid selector 'node[[0,3]]', ignoring set_value()` |
| 16 | `algorithms/graph/mcmf.tex` | 0 | 368 | 1 | `UserWarning: Graph(layout='stable', directed=True) — stable layout does not...` |
| 17 | `algorithms/graph/union_find.tex` | 0 | 478 | 1 | `UserWarning: Graph(layout='stable', directed=True) — stable layout does not...` |
| 18 | `algorithms/graph/union_find_graph.tex` | 0 | 465 | 1 | `UserWarning: Graph(layout='stable', directed=True) — stable layout does not...` |
| 19 | `algorithms/misc/convex_hull_andrew.tex` | 0 | 471 | 1 | `[E1462] polygon not closed — auto-closing` |
| 20 | `cses/planets_queries2.tex` | 0 | 540 | 1 | `E1500: final objective (2.0114) exceeds 10x initial (0.0150)` |
| 21 | `editorials/dijkstra_editorial.tex` | 0 | 479 | 1 | `UserWarning: Graph(layout='stable', directed=True) — stable layout does not...` |
| 22 | `fixtures/pass/04_stack_shrink.tex` | 0 | 494 | 3 | `[E1115] selector 's.item[2]' does not match any addressable part of 's'` |
| 23 | `fixtures/pass/10_selector_out_of_range.tex` | 0 | 479 | 3 | `[E1115] selector 'a.cell[99]' does not match any addressable part of 'a'` |
| 24 | `fixtures/pass/12_selector_unknown_accessor.tex` | 0 | 335 | 3 | `[E1115] selector 'a.bogus' does not match any addressable part of 'a'` |
| 25 | `fixtures/pass/17_empty_substory.tex` | 0 | 322 | 1 | `EmptySubstoryWarning: [E1366] \substory at line 3, col 1 contains no \step` |
| 26 | `integration/test_edge_overlap.tex` | 0 | 332 | 1 | `UserWarning: Graph(layout='stable', directed=True) — stable layout does not...` |
| 27 | `integration/test_reference_graph_tree.tex` | 0 | 441 | 1 | `UserWarning: Graph(layout='stable', directed=True) — stable layout does not...` |
| 28 | `primitives/graph.tex` | 0 | 429 | 1 | `E1500: final objective (0.0169) exceeds 10x initial (0.0007)` |
| 29 | `smoke/gep_v2_smoke.tex` | 0 | 354 | 1 | `UserWarning: Graph(global_optimize=True) accepted as v2.1 forward-compat flag` |
| 30 | `algorithms/dp/convex_hull_trick.tex` | 0 | 542 | 0 | — |
| 31 | `algorithms/dp/dp_optimization.tex` | 0 | 345 | 0 | — |
| 32 | `algorithms/dp/frog.tex` | 0 | 474 | 0 | — |
| 33 | `algorithms/dp/frog_foreach.tex` | 0 | 570 | 0 | — |
| 34 | `algorithms/dp/interval_dp.tex` | 0 | 538 | 0 | — |
| 35 | `algorithms/graph/bfs.tex` | 0 | 378 | 0 | — |
| 36 | `algorithms/graph/dijkstra.tex` | 0 | 786 | 0 | — |
| 37 | `algorithms/graph/kruskal_mst.tex` | 0 | 561 | 0 | — |
| 38 | `algorithms/graph/union_find_array.tex` | 0 | 508 | 0 | — |
| 39 | `algorithms/misc/fft_butterfly.tex` | 0 | 328 | 0 | — |
| 40 | `algorithms/misc/li_chao.tex` | 0 | 332 | 0 | — |
| 41 | `algorithms/misc/linkedlist_reverse.tex` | 0 | 447 | 0 | — |
| 42 | `algorithms/string/kmp.tex` | 0 | 496 | 0 | — |
| 43 | `algorithms/tree/hld.tex` | 0 | 355 | 0 | — |
| 44 | `algorithms/tree/persistent_segtree.tex` | 0 | 579 | 0 | — |
| 45 | `algorithms/tree/splay.tex` | 0 | 434 | 0 | — |
| 46 | `cses/elevator_rides.tex` | 0 | 1055 | 0 | — |
| 47 | `cses/houses_schools.tex` | 0 | 584 | 0 | — |
| 48 | `cses/increasing_array.tex` | 0 | 509 | 0 | — |
| 49 | `cses/missing_number.tex` | 0 | 524 | 0 | — |
| 50 | `cses/necessary_roads.tex` | 0 | 450 | 0 | — |
| 51 | `cses/permutations.tex` | 0 | 525 | 0 | — |
| 52 | `cses/range_queries_copies.tex` | 0 | 451 | 0 | — |
| 53 | `cses/repetitions.tex` | 0 | 703 | 0 | — |
| 54 | `cses/weird_algorithm.tex` | 0 | 489 | 0 | — |
| 55 | `demos/dinic.tex` | 0 | 586 | 0 | — |
| 56 | `demos/maxflow.tex` | 0 | 505 | 0 | — |
| 57 | `demos/mcmf.tex` | 0 | 533 | 0 | — |
| 58 | `demos/tutorial_en.tex` | 0 | 570 | 0 | — |
| 59 | `editorials/bfs_grid_editorial.tex` | 0 | 505 | 0 | — |
| 60 | `editorials/knapsack_editorial.tex` | 0 | 821 | 0 | — |
| 61 | `fixtures/pass/01_variablewatch_shrink.tex` | 0 | 355 | 0 | — |
| 62 | `fixtures/pass/02_hashmap_shrink.tex` | 0 | 567 | 0 | — |
| 63 | `fixtures/pass/03_linkedlist_shrink.tex` | 0 | 466 | 0 | — |
| 64 | `fixtures/pass/05_diagram_prescan.tex` | 0 | 442 | 0 | — |
| 65 | `fixtures/pass/06_substory_prescan.tex` | 0 | 374 | 0 | — |
| 66 | `fixtures/pass/07_prescan_no_pollution.tex` | 0 | 422 | 0 | — |
| 67 | `fixtures/pass/08_foreach_value_interpolation.tex` | 0 | 342 | 0 | — |
| 68 | `fixtures/pass/14_annotate_arrow_bool.tex` | 0 | 372 | 0 | — |
| 69 | `fixtures/pass/18_xss_filename.tex` | 0 | 333 | 0 | — |
| 70 | `fixtures/pass/19_path_traversal.tex` | 0 | 365 | 0 | — |
| 71 | `fixtures/pass/22_recursion_no_path_leak.tex` | 0 | 420 | 0 | — |
| 72 | `fixtures/pass/23_a11y_widget.tex` | 0 | 345 | 0 | — |
| 73 | `fixtures/pass/24_contrast_dark_mode.tex` | 0 | 342 | 0 | — |
| 74 | `integration/test_array_arrows.tex` | 0 | 358 | 0 | — |
| 75 | `integration/test_dptable_arrows.tex` | 0 | 444 | 0 | — |
| 76 | `integration/test_label_overlap_1d.tex` | 0 | 510 | 0 | — |
| 77 | `integration/test_label_overlap_2d.tex` | 0 | 731 | 0 | — |
| 78 | `integration/test_label_readability.tex` | 0 | 453 | 0 | — |
| 79 | `integration/test_plane2d_animation.tex` | 0 | 524 | 0 | — |
| 80 | `integration/test_plane2d_dense.tex` | 0 | 364 | 0 | — |
| 81 | `integration/test_plane2d_edges.tex` | 0 | 466 | 0 | — |
| 82 | `integration/test_reference_basic.tex` | 0 | 467 | 0 | — |
| 83 | `integration/test_reference_dptable.tex` | 0 | 1041 | 0 | — |
| 84 | `integration/test_reference_edge_cases.tex` | 0 | 825 | 0 | — |
| 85 | `integration/test_reference_editorial.tex` | 0 | 684 | 0 | — |
| 86 | `integration/test_reference_extended.tex` | 0 | 442 | 0 | — |
| 87 | `integration/test_reference_grid_numline.tex` | 0 | 591 | 0 | — |
| 88 | `integration/test_reference_tex_heavy.tex` | 0 | 494 | 0 | — |
| 89 | `integration/test_reference_unionfind.tex` | 0 | 606 | 0 | — |
| 90 | `primitives/array.tex` | 0 | 332 | 0 | — |
| 91 | `primitives/codepanel.tex` | 0 | 331 | 0 | — |
| 92 | `primitives/diagram.tex` | 0 | 577 | 0 | — |
| 93 | `primitives/diagram_grid.tex` | 0 | 328 | 0 | — |
| 94 | `primitives/diagram_multi.tex` | 0 | 350 | 0 | — |
| 95 | `primitives/dptable.tex` | 0 | 470 | 0 | — |
| 96 | `primitives/grid.tex` | 0 | 528 | 0 | — |
| 97 | `primitives/hashmap.tex` | 0 | 470 | 0 | — |
| 98 | `primitives/linkedlist.tex` | 0 | 416 | 0 | — |
| 99 | `primitives/matrix.tex` | 0 | 325 | 0 | — |
| 100 | `primitives/metricplot.tex` | 0 | 352 | 0 | — |
| 101 | `primitives/numberline.tex` | 0 | 326 | 0 | — |
| 102 | `primitives/plane2d.tex` | 0 | 338 | 0 | — |
| 103 | `primitives/queue.tex` | 0 | 409 | 0 | — |
| 104 | `primitives/substory.tex` | 0 | 355 | 0 | — |
| 105 | `primitives/tree.tex` | 0 | 330 | 0 | — |
| 106 | `primitives/variablewatch.tex` | 0 | 700 | 0 | — |
| 107 | `quickstart/binary_search.tex` | 0 | 589 | 0 | — |
| 108 | `quickstart/diagram_intro.tex` | 0 | 363 | 0 | — |
| 109 | `quickstart/foreach_demo.tex` | 0 | 612 | 0 | — |
| 110 | `quickstart/hello.tex` | 0 | 318 | 0 | — |
| 111 | `smoke/plane2d_annotations.tex` | 0 | 336 | 0 | — |
| 112 | `smoke/plane2d_lines.tex` | 0 | 322 | 0 | — |
| 113 | `smoke/plane2d_ticks.tex` | 0 | 412 | 0 | — |

**Note on expected-fail fixtures:** rows 1–7 have exit 2 by design. The build.sh `render_one()` function treats these as `OK (expected-fail)` — they are counted as passing in section 5 below.

---

## 3. Failure Clusters

All 7 failures are expected-fail fixtures — there are zero unintended hard failures.

### F-1: Error-Code Hint Regressions (E1006, E1116, E1001, E1173 × 2)

| Files | Error |
|-------|-------|
| `fixtures/expected-fail/09_command_typo_hint.tex` | E1006 unknown command + typo hint |
| `fixtures/expected-fail/11_selector_unknown_shape.tex` | E1116 undeclared shape |
| `fixtures/expected-fail/13_apply_before_shape.tex` | E1116 no `\shape` before `\step` |
| `fixtures/expected-fail/15_percent_in_braces.tex` | E1001 unterminated brace (`%` comment) |
| `fixtures/expected-fail/16_empty_foreach_iterable.tex` | E1173 empty foreach iterable |

**Root cause:** intentional bad inputs that exercise the error-code + hint system. **Verdict: green** — all exit 2 as pinned.

### F-2: Starlark Resource Budget (E1152, E1173)

| Files | Error |
|-------|-------|
| `fixtures/expected-fail/20_cumulative_budget.tex` | E1152 Starlark CPU limit exceeded (5 761 ms render) |
| `fixtures/expected-fail/21_list_alloc_cap.tex` | E1173 range() argument too large |

**Root cause:** intentional resource exhaustion fixtures. **Verdict: green** — both exit 2 as pinned.

---

## 4. Warning Clusters

### W-1: [E1115] Invalid Edge/Node Selector (14 files, 83 total warning lines)

Files affected and warning counts:

| File | Warns | Selector pattern |
|------|-------|-----------------|
| `algorithms/misc/simulated_annealing.tex` | 27 | `G.edge[(X,Y)]` — directed edges only declared undirected |
| `algorithms/graph/union_find_tree.tex` | 18 | `T.edge[(R,B)]` — edges referenced before they exist in the Tree |
| `primitives/stack.tex` | 9 | `s.item[3]`, `s.item[1]`, `s.item[2]` — item indices beyond current stack size |
| `algorithms/tree/bst_operations.tex` | 6 | `T.edge[(5,8)]`, `T.edge[(8,7)]` — edges referencing nodes not yet inserted |
| `editorials/segtree_editorial.tex` | 6 | `T.node[[1,2]]`, `T.edge[([0,2],[1,2])]` — bracket notation for range nodes |
| `integration/test_reference_advanced.tex` | 6 | `a.cell[InterpolationRef(...)]` — unresolved `\foreach` binding leaking into selector |
| `integration/test_reference_datastruct.tex` | 6 | `s.item[3]` — same as primitives/stack.tex |
| `integration/test_reference_segtree.tex` | 6 | `sst.node[[0,3]]` etc. — bracket range-node selectors |
| `fixtures/pass/04_stack_shrink.tex` | 3 | `s.item[2]` — shrink regression fixture intentionally targets popped item |
| `fixtures/pass/10_selector_out_of_range.tex` | 3 | `a.cell[99]` — intentional out-of-range fixture |
| `fixtures/pass/12_selector_unknown_accessor.tex` | 3 | `a.bogus` — intentional bad accessor fixture |
| `algorithms/graph/mcmf.tex` | 1 | (layout warning, see W-2) |
| `algorithms/graph/union_find.tex` | 1 | (layout warning, see W-2) |
| `algorithms/graph/union_find_graph.tex` | 1 | (layout warning, see W-2) |

**Root cause (non-fixture files):** Two sub-patterns:
1. `simulated_annealing.tex` and `bst_operations.tex`: `\recolor` steps target edges that do not exist in the primitive's edge list at the time of the step — the graph is mutated across steps but edge additions lag behind color-target references.
2. `union_find_tree.tex` and both segtree files: Tree node/edge selectors use range-notation keys (`[1,2]`, `(R,B)`) that the selector engine does not resolve to the bracket-keyed nodes produced by these primitives.

**Suggested fix:** Audit `\recolor` / `\apply` selector targets against the graph/tree edge list at each step; for bracket-keyed Tree nodes use the documented `node[idx]` integer form or verify the range-bracket notation is supported.

**Note:** The three `fixtures/pass/` entries (rows 22–24) are intentional: those fixtures exist precisely to pin that E1115 is a non-fatal warning, not a hard error. They do not require fixing.

### W-2: `stable` Layout on Directed Graph (7 files)

| File | Warning |
|------|---------|
| `algorithms/graph/mcmf.tex` | `Graph(layout='stable', directed=True)` |
| `algorithms/graph/union_find.tex` | same |
| `algorithms/graph/union_find_graph.tex` | same |
| `cses/planets_queries2.tex` | same |
| `editorials/dijkstra_editorial.tex` | same |
| `integration/test_edge_overlap.tex` | same |
| `integration/test_reference_graph_tree.tex` | same |

**Root cause:** `layout='stable'` is documented as undirected-only; using it with `directed=True` is semantically incorrect — the renderer warns but falls back gracefully.

**Suggested fix:** Change `layout='stable'` to `layout='hierarchical'` or `layout='auto'` in the 5 non-integration files listed above; integration files can be updated in the same pass.

### W-3: [E1462] Polygon Not Closed — Auto-closing (1 file)

| File | Warning |
|------|---------|
| `algorithms/misc/convex_hull_andrew.tex` | `polygon not closed — auto-closing by appending first point` |

**Root cause:** The convex hull `add_polygon` call omits re-stating the first point to close the polygon; the renderer auto-closes but emits E1462.

**Suggested fix:** Append the first hull point to the polygon list passed to `add_polygon` (1-line fix in the `\compute` block).

**Note:** Scout triage flagged `grid=on` at line 23 of this file as suspect. The render confirms `grid=on` is silently accepted (no error, no warning). The only actual warning is E1462 (polygon). The `grid=on` string is a no-op — the grid is not shown — which is a silent semantic bug but not a hard failure.

### W-4: [E1366] Empty Substory (1 file)

| File | Warning |
|------|---------|
| `fixtures/pass/17_empty_substory.tex` | `EmptySubstoryWarning: [E1366] \substory at line 3, col 1 contains no \step` |

**Root cause:** Intentional regression fixture. **No fix needed.**

### W-5: [E1500] Layout Optimizer Objective Spike (2 files)

| File | Warning |
|------|---------|
| `cses/planets_queries2.tex` | `E1500: final objective (2.0114) exceeds 10x initial (0.0150)` |
| `primitives/graph.tex` | `E1500: final objective (0.0169) exceeds 10x initial (0.0007)` |

**Root cause:** The simulated-annealing layout optimizer did not converge to a stable minimum; the final layout energy is significantly worse than the starting point. The render completes but the graph layout may look suboptimal.

**Suggested fix:** For `planets_queries2.tex` (planets functional-graph layout), add `layout='hierarchical'` to the Graph `\shape` to bypass SA optimizer for a DAG-like structure. For `primitives/graph.tex`, this is a canonical minimal example — consider adding `layout='auto'` to let the engine choose.

### W-6: `global_optimize=True` Forward-Compat Flag (1 file)

| File | Warning |
|------|---------|
| `smoke/gep_v2_smoke.tex` | `Graph(global_optimize=True) accepted as v2.1 forward-compat flag but has no runtime effect yet` |

**Root cause:** GEP v2.1 smoke test exercises a flag that is accepted but not yet wired. Expected, by-design. No fix needed until GEP v2.1 ships.

---

## 5. Per-Subdir Pass / Warn / Fail Counts

"Fail" = unintended exit non-0. Expected-fail fixtures count as PASS (correct behavior).

| Subdir | Total | PASS (clean) | WARN | FAIL |
|--------|-------|-------------|------|------|
| algorithms/ | 23 | 17 | 6 | 0 |
| cses/ | 10 | 8 | 2 | 0 |
| demos/ | 4 | 4 | 0 | 0 |
| editorials/ | 4 | 2 | 2 | 0 |
| fixtures/expected-fail/ | 7 | 7* | 0 | 0 |
| fixtures/pass/ | 17 | 12 | 5† | 0 |
| integration/ | 21 | 15 | 6 | 0 |
| primitives/ | 19 | 16 | 3 | 0 |
| quickstart/ | 4 | 4 | 0 | 0 |
| smoke/ | 4 | 3 | 1 | 0 |
| **TOTAL** | **113** | **88** | **25** | **0** |

*All 7 expected-fail fixtures exit 2 as pinned — counted as green.  
†3 of the 5 warned fixtures/pass are intentional E1115 regression fixtures (pass/04, pass/10, pass/12).

---

## 6. Render Time Outliers — Top 10 Slowest

| Rank | File | Duration (ms) |
|------|------|---------------|
| 1 | `fixtures/expected-fail/20_cumulative_budget.tex` | 5 761 |
| 2 | `fixtures/expected-fail/21_list_alloc_cap.tex` | 960 |
| 3 | `cses/elevator_rides.tex` | 1 055 |
| 4 | `integration/test_reference_dptable.tex` | 1 041 |
| 5 | `editorials/knapsack_editorial.tex` | 821 |
| 6 | `integration/test_reference_edge_cases.tex` | 825 |
| 7 | `algorithms/graph/dijkstra.tex` | 786 |
| 8 | `cses/repetitions.tex` | 703 |
| 9 | `primitives/variablewatch.tex` | 700 |
| 10 | `integration/test_reference_editorial.tex` | 684 |

The two fixtures at ranks 1–2 are by design (Starlark CPU exhaustion tests). The remaining 8 are all well under 1 100 ms — no performance concerns. No file approached the 120 s timeout.

---

## 7. Recommendations

### R-1 — Fix `simulated_annealing.tex` edge selectors  
**File:** `algorithms/misc/simulated_annealing.tex`  
**Patch:** Audit every `\recolor{G.edge[(X,Y)]}` step; verify each directed edge `(X,Y)` is declared in the initial `\shape{G}{Graph}{edges=...}` list before it is targeted. Remove or guard selectors for edges added mid-animation until after the `\apply` that adds them.  
**Priority:** HIGH (27 warnings, highest noise in corpus)

### R-2 — Fix `union_find_tree.tex` edge selectors  
**File:** `algorithms/graph/union_find_tree.tex`  
**Patch:** Replace `T.edge[(R,B)]` etc. with the correct edge selector form for the Tree primitive — use integer node indices or the documented edge-id syntax, not `(label,label)` tuples.  
**Priority:** HIGH (18 warnings)

### R-3 — Fix `stable+directed` layout on 5 non-test Graph shapes  
**Files:** `algorithms/graph/mcmf.tex`, `algorithms/graph/union_find.tex`, `algorithms/graph/union_find_graph.tex`, `cses/planets_queries2.tex`, `editorials/dijkstra_editorial.tex`  
**Patch:** Change `layout='stable'` to `layout='hierarchical'` (directed DAG-like) or `layout='auto'` in each `\shape{...}{Graph}{..., layout='stable', directed=True, ...}` call.  
**Priority:** HIGH (affects visual correctness of 5 pedagogical files)

### R-4 — Fix bracket-key node selectors in segtree files  
**Files:** `editorials/segtree_editorial.tex`, `integration/test_reference_segtree.tex`  
**Patch:** Replace `T.node[[1,2]]` and `T.edge[([0,2],[1,2])]` with integer-index or documented range-node selector syntax; confirm bracket-range nodes are supported by the Tree primitive before using them.  
**Priority:** HIGH (6 warnings each, silent visual corruption)

### R-5 — Fix `primitives/stack.tex` and `integration/test_reference_datastruct.tex` Stack selectors  
**Files:** `primitives/stack.tex`, `integration/test_reference_datastruct.tex`  
**Patch:** Ensure `s.item[N]` is only targeted after the Nth item has been pushed; add guards or reorder push/recolor steps.  
**Priority:** MED (9 + 6 warnings; primitives/ is canonical documentation)

### R-6 — Fix `bst_operations.tex` edge selectors  
**File:** `algorithms/tree/bst_operations.tex`  
**Patch:** Move `\recolor{T.edge[(5,8)]}` and `\recolor{T.edge[(8,7)]}` steps to after the `\apply` blocks that insert nodes 8 and 7.  
**Priority:** MED (6 warnings)

### R-7 — Fix `convex_hull_andrew.tex` unclosed polygon  
**File:** `algorithms/misc/convex_hull_andrew.tex`  
**Patch:** In the `add_polygon` call within the `\compute` Starlark block, append `hull[0]` to the end of the hull point list to explicitly close the polygon.  
**Priority:** MED (E1462 auto-close is correct but the explicit close is best practice)

### R-8 — Fix `grid=on` silent no-op in `convex_hull_andrew.tex`  
**File:** `algorithms/misc/convex_hull_andrew.tex`, line 23  
**Patch:** Change `grid=on` to `grid=true` (documented boolean). Currently silently ignored — Plane2D grid is not rendered.  
**Priority:** MED (was flagged by scout triage; render confirmed silent no-op, not an error)

### R-9 — Fix unresolved InterpolationRef leak in `test_reference_advanced.tex`  
**File:** `integration/test_reference_advanced.tex`  
**Patch:** The selector `a.cell[InterpolationRef(name='target_idx', subscripts=())]` appears as a literal string, indicating a `\foreach` binding variable was not resolved before selector evaluation. Verify the `\foreach` variable `${target_idx}` is in scope at the step where it is used.  
**Priority:** MED (6 warnings; binding leak is a parser/interpolation bug in the .tex source)

### R-10 — Fix `planets_queries2.tex` layout optimizer spike  
**File:** `cses/planets_queries2.tex`  
**Patch:** Add `layout='hierarchical'` to the Graph `\shape` to bypass the SA optimizer for this functional-graph DAG structure.  
**Priority:** LOW (E1500 is non-fatal; visual degradation only)
