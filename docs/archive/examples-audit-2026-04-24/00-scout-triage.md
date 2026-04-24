# Scout Triage — Scriba `.tex` Examples Audit
**Date:** 2026-04-24 | **Files scanned:** 113 | **Reference version:** post-47-issue-fix

---

## Executive Summary

The 113-file example corpus is structurally sound (all `\begin`/`\end` pairs balance at 191 environments; no `\documentclass`; no unsupported math delimiters outside `$$`), but suffers from three systemic problems. First, the **algorithms/** and **cses/** subdirectories consist entirely of bare animation widgets with zero surrounding prose, `\section`, or context — they are usable only as isolated SVGs, not as copyable editorial templates. Second, **union-find is over-represented** (4 dedicated files + references in 4 others across 3 subdirs) while **CodePanel** has only 2 examples, **Matrix** appears only in integration boilerplate, and **`\hl`/`\substory`/`\reannotate`/`\cursor`** are near-invisible in the pedagogical tier. Third, the boundary between **integration/**, **fixtures/**, and **demos/** is blurry: integration tests embed full editorial prose, demos duplicate algorithms/ content, and smoke/ exercises Plane2D almost exclusively. One genuine conformance smell exists: `grid=on` in `algorithms/misc/convex_hull_andrew.tex` (reference requires bool `true`/`false`). Recommended priority: (1) render-validator agent across all 113 files to surface the `grid=on` class of param errors at runtime, (2) reference-conformance auditor targeting the 23 algorithms/ files and 10 cses/ files for missing prose scaffolding, (3) consolidation agent to merge the 4 union-find variants.

---

## 1. Inventory Table

### algorithms/ (23 files)

| File | Lines | Env | Primitives | Key Commands | Purpose |
|------|-------|-----|-----------|--------------|---------|
| dp/convex_hull_trick.tex | 235 | anim | Array, Plane2D | step narrate recolor annotate compute | CHT min-cost DP with geometric visualization |
| dp/dp_optimization.tex | 104 | anim | DPTable, NumberLine | step narrate recolor annotate | Knuth DP optimization |
| dp/frog.tex | 68 | anim | Array | step narrate apply recolor cursor | AtCoder DP-A frog problem |
| dp/frog_foreach.tex | 75 | anim | Array | step narrate apply recolor cursor foreach compute | Same as frog.tex but using \foreach — near-duplicate |
| dp/interval_dp.tex | 98 | anim | Array, DPTable | step narrate recolor annotate substory | Zuma interval DP |
| graph/bfs.tex | 132 | anim | Array, Graph, Queue, Tree | step narrate recolor annotate | BFS tree construction |
| graph/dijkstra.tex | 151 | anim | Array, Graph | step narrate apply recolor annotate cursor | Dijkstra shortest path |
| graph/kruskal_mst.tex | 111 | anim | Array, Graph | step narrate recolor annotate | Kruskal MST with union-find |
| graph/mcmf.tex | 58 | anim | Graph | step narrate recolor annotate | Min-cost max-flow sketch (thin: 5 steps only) |
| graph/union_find.tex | 129 | anim | Array, Graph | step narrate recolor annotate | DSU with path compression (Graph view) |
| graph/union_find_array.tex | 94 | anim | Array | step narrate recolor annotate reannotate | DSU shown as parent[] array + arc annotations |
| graph/union_find_graph.tex | 91 | anim | Array, Graph | step narrate recolor annotate | DSU Graph primitive fixed-position |
| graph/union_find_tree.tex | 113 | anim | Array, Tree | step narrate recolor annotate | DSU Tree primitive with virtual root |
| misc/convex_hull_andrew.tex | 304 | anim | Plane2D, Stack | step narrate recolor annotate compute | Andrew's monotone chain convex hull |
| misc/fft_butterfly.tex | 91 | multi | Array, Plane2D | step narrate recolor | FFT butterfly diagram + unit circle (mixed diag+anim) |
| misc/li_chao.tex | 51 | anim | Plane2D | step narrate apply | Li Chao tree visualization |
| misc/linkedlist_reverse.tex | 93 | anim | LinkedList | step narrate recolor annotate cursor | In-place list reversal three-pointer trace |
| misc/simulated_annealing.tex | 75 | anim | Graph, MetricPlot | step narrate recolor | SA for TSP with cost metric |
| string/kmp.tex | 208 | anim | Array | step narrate recolor annotate cursor | KMP string matching |
| tree/bst_operations.tex | 163 | anim | Tree | step narrate recolor annotate | BST insert/delete |
| tree/hld.tex | 77 | anim | Array, Tree | step narrate recolor | Heavy-light decomposition (7 steps only) |
| tree/persistent_segtree.tex | 137 | anim | Tree | step narrate recolor annotate | Persistent segment tree (7 steps) |
| tree/splay.tex | 46 | anim | MetricPlot, Tree | step narrate recolor | Splay tree zig-zig rotation (7 steps, thin) |

### cses/ (10 files)

| File | Lines | Env | Primitives | Key Commands | Purpose |
|------|-------|-----|-----------|--------------|---------|
| elevator_rides.tex | 161 | anim | Array, DPTable | step narrate recolor annotate cursor | Bitmask DP |
| houses_schools.tex | 149 | anim | Array, DPTable | step narrate recolor annotate cursor | Interval DP + D&C optimization |
| increasing_array.tex | 52 | anim | Array | step narrate recolor annotate cursor | Make array non-decreasing |
| missing_number.tex | 61 | anim | Array | step narrate recolor annotate cursor compute | Missing number via sum formula |
| necessary_roads.tex | 153 | anim | Array, Graph | step narrate recolor annotate cursor | Tarjan's bridge finding |
| permutations.tex | 55 | anim | Array | step narrate recolor annotate cursor compute | Beautiful permutation construction |
| planets_queries2.tex | 204 | anim | Array, DPTable, Graph | step narrate recolor annotate cursor | Functional graph distance (binary lifting) |
| range_queries_copies.tex | 171 | anim | Array, Tree | step narrate recolor annotate cursor | Persistent segtree on CSES |
| repetitions.tex | 62 | anim | Array | step narrate recolor annotate cursor | Longest consecutive repetition |
| weird_algorithm.tex | 143 | anim | Array, MetricPlot | step narrate recolor annotate | Collatz sequence visualization |

### demos/ (4 files)

| File | Lines | Env | Primitives | Key Commands | Purpose |
|------|-------|-----|-----------|--------------|---------|
| dinic.tex | 310 | anim | Graph, VariableWatch | step narrate recolor annotate | Flagship Dinic max-flow demo |
| maxflow.tex | 268 | anim | Graph, VariableWatch | step narrate recolor annotate | Edmonds-Karp max-flow |
| mcmf.tex | 266 | multi | Array, Graph, VariableWatch | step narrate recolor annotate | MCMF flagship (multi-anim) |
| tutorial_en.tex | 309 | anim | Grid, VariableWatch | step narrate recolor annotate | English tutorial walkthrough |

### editorials/ (4 files)

| File | Lines | Env | Primitives | Key Commands | Purpose |
|------|-------|-----|-----------|--------------|---------|
| bfs_grid_editorial.tex | 417 | multi | Grid, Queue | step narrate recolor annotate | Full BFS-on-grid editorial with prose |
| dijkstra_editorial.tex | 192 | multi | Array, Graph | step narrate recolor annotate | Dijkstra editorial with sections |
| knapsack_editorial.tex | 279 | multi | Array, DPTable | step narrate recolor annotate | 0/1 knapsack full editorial |
| segtree_editorial.tex | 167 | multi | Array, Tree | step narrate recolor annotate | Segment tree full editorial |

### fixtures/ (24 files — 7 expected-fail, 17 pass)

| File | Lines | Env | Primitives | Purpose |
|------|-------|-----|-----------|---------|
| pass/01–04 | 21–25 | anim | VW/HashMap/LL/Stack | Width-shrink regression (4 variants) |
| pass/05 | 9 | diag | VariableWatch | diagram prescan regression |
| pass/06 | 29 | anim | Array, VariableWatch | substory prescan |
| pass/07 | 27 | anim | HashMap, LL, Queue | prescan no-pollution |
| pass/08 | 8 | anim | Array | foreach value interpolation |
| pass/10,12 | 12 | anim | Array | selector error codes |
| pass/14 | 21 | anim | Array | annotate arrow=true bool parse |
| pass/17 | 17 | anim | — | empty substory warning |
| pass/18,19,22 | 13–23 | anim | Array | XSS/path-traversal/recursion security |
| pass/23 | 31 | anim | Array | a11y (role/aria) |
| pass/24 | 37 | anim | Array | contrast + dark-mode |
| expected-fail/09,11,13,15,16 | 8–16 | anim | Array | Error-code hint regressions |
| expected-fail/20 | 210 | multi | Array | Cumulative budget C1 regression |
| expected-fail/21 | 21 | anim | Array | List alloc H2 regression |

### integration/ (21 files)

| File | Lines | Env | Primitives | Purpose |
|------|-------|-----|-----------|---------|
| test_array_arrows.tex | 31 | anim | Array | annotate arrow arc smoke |
| test_dptable_arrows.tex | 56 | multi | DPTable | DPTable arrow arcs |
| test_edge_overlap.tex | 22 | diag | Graph | edge overlap layout |
| test_label_overlap_1d/2d.tex | 67/94 | multi | DPTable | label collision avoidance |
| test_label_readability.tex | 87 | multi | DPTable | readability checks |
| test_plane2d_animation.tex | 71 | anim | Plane2D | point animation |
| test_plane2d_dense.tex | 73 | diag | Plane2D | dense point cloud |
| test_plane2d_edges.tex | 184 | multi | Plane2D | edge-case xranges (9 shapes) |
| test_reference_advanced.tex | 126 | anim | Array, DPTable, VW | substory + \hl usage |
| test_reference_basic.tex | 114 | anim | Array | lstlisting + math |
| test_reference_datastruct.tex | 292 | multi | CodePanel, HashMap, LL, Queue, Stack, VW | data-structure omnibus |
| test_reference_dptable.tex | 316 | multi | Array, DPTable, VW | 2D DP, annotate arcs, cursor |
| test_reference_edge_cases.tex | 315 | multi | Array, DPTable, Graph, Grid | edge-case omnibus |
| test_reference_editorial.tex | 129 | multi | Array | Two-Sum editorial mock |
| test_reference_extended.tex | 148 | multi | Matrix, MetricPlot, Plane2D | extended primitives |
| test_reference_graph_tree.tex | 153 | multi | Array, Graph, Tree, VW | Dijkstra-like exploration |
| test_reference_grid_numline.tex | 189 | multi | Grid, NumberLine, VW | grid + numberline |
| test_reference_segtree.tex | 160 | multi | Array, Tree | segtree animations |
| test_reference_tex_heavy.tex | 260 | diag | Graph | heavy LaTeX prose + math |
| test_reference_unionfind.tex | 295 | multi | Array, Graph, VW | union-find comprehensive |

### primitives/ (19 files)

One `.tex` per primitive (Array, CodePanel, DPTable, Graph, Grid, HashMap, LinkedList, Matrix, MetricPlot, NumberLine, Plane2D, Queue, Stack, Tree, VariableWatch) plus 3 diagram variants (diagram, diagram_grid, diagram_multi) and 1 substory demo. All are minimal showcases (6–72 lines).

### quickstart/ (4 files)

| File | Lines | Env | Purpose |
|------|-------|-----|---------|
| hello.tex | 15 | anim | Introductory Array animation |
| diagram_intro.tex | 5 | diag | Single Graph diagram |
| binary_search.tex | 85 | anim | Binary search with cursor |
| foreach_demo.tex | 79 | anim | \foreach loop demonstration |

### smoke/ (4 files)

All exercise Plane2D exclusively: `gep_v2_smoke.tex` (193 lines, Graph+GEP-v2 flags), `plane2d_annotations.tex` (44), `plane2d_lines.tex` (38), `plane2d_ticks.tex` (84).

---

## 2. Axis 1 — Reference Conformance Red Flags

| File | Flag | Severity | Detail |
|------|------|----------|--------|
| algorithms/misc/convex_hull_andrew.tex | `grid=on` | HIGH | Reference §Plane2D params uses bool (`true`/`false`). `"on"` is a non-standard string value; behavior at parse time is unknown — may be silently ignored or raise E1xxx |
| algorithms/dp/frog.tex + frog_foreach.tex | Near-identical | MEDIUM | Same `h[]` data, same algorithm — two files exist solely to demo `\foreach`; the foreach version adds no standalone pedagogical value |
| algorithms/graph/mcmf.tex | Thin (5 steps) | LOW | Exists in algorithms/ AND a richer version is in demos/mcmf.tex; the thin copy overlaps without adding value |
| algorithms/misc/fft_butterfly.tex | Mixed diagram+animation in one file | LOW | Uses both `\begin{diagram}` and `\begin{animation}` in one file — valid but unusual; the animation portion has 7 `\step` blocks with no clear narrative progression |
| algorithms/tree/splay.tex | Only 7 steps, MetricPlot misuse | LOW | Uses MetricPlot with `add_data` to show amortized cost, but provides no context or axis labels — MetricPlot is opaque without prose |
| smoke/plane2d_ticks.tex + integration/test_plane2d_edges.tex | `grid=true` on Plane2D | OK | `grid=` is a **documented and valid** Plane2D bool param (reference §9, line 859). Not a flag. |
| integration/test_reference_tex_heavy.tex | `$$\begin{align}` | OK | Reference §2.3 explicitly permits `align`, `cases` inside `$$` delimiters. Not a flag. |
| algorithms/tree/persistent_segtree.tex + editorials/segtree_editorial.tex | `show_sum=true` on Tree | OK | Documented at reference §9 Tree params line 717. Not a flag. |
| demos/mcmf.tex vs algorithms/graph/mcmf.tex | Duplicate id risk | MEDIUM | Both use `id="mcmf"` — if ever concatenated into a single document, duplicate scene IDs will break navigation |

**Zero `\hl{}` usage in any pedagogical file.** The `\hl{label}{text}` cross-reference command (§5.13) is unused in all of algorithms/, cses/, editorials/, and quickstart/. Only `integration/test_reference_advanced.tex` exercises it.

**`\reannotate` is nearly absent.** Only 4 integration files and 1 algorithms file use it. None of the pedagogical tutorials demonstrate the pattern.

---

## 3. Axis 2 — Duplicates / Near-Duplicates

### Union-Find (most over-represented algorithm)

| File | Subdir | Approach | Unique value? |
|------|--------|----------|--------------|
| algorithms/graph/union_find.tex | algorithms | Graph view, path compression trace | PRIMARY |
| algorithms/graph/union_find_array.tex | algorithms | Array view + reannotate arcs | Adds arc annotation demo |
| algorithms/graph/union_find_graph.tex | algorithms | Graph, fixed layout | Near-duplicate of union_find.tex |
| algorithms/graph/union_find_tree.tex | algorithms | Tree primitive + virtual root | Somewhat distinct primitive use |
| integration/test_reference_unionfind.tex | integration | Comprehensive test | Dev test, not pedagogical |
| algorithms/graph/kruskal_mst.tex | algorithms | References DSU inline | Incidental |

**Recommendation:** consolidate union_find.tex + union_find_graph.tex into one; keep union_find_array.tex (distinct primitive) and union_find_tree.tex (distinct primitive).

### Frog DP (exact near-duplicate)

| File | Diff |
|------|------|
| algorithms/dp/frog.tex | Manual step-by-step |
| algorithms/dp/frog_foreach.tex | `\foreach` + `\compute` variant |

Same data, same algorithm. The foreach version is a style demo — it belongs in **quickstart/** alongside `foreach_demo.tex`, not duplicated in dp/.

### MCMF / Max-Flow

| File | Subdir | Primitives | Detail |
|------|--------|-----------|--------|
| algorithms/graph/mcmf.tex | algorithms | Graph only | Thin sketch (5 steps) |
| demos/mcmf.tex | demos | Array+Graph+VW | Full multi-animation flagship |
| demos/maxflow.tex | demos | Graph+VW | Edmonds-Karp |
| demos/dinic.tex | demos | Graph+VW | Dinic |

The thin algorithms/graph/mcmf.tex adds no value over the demos/ version. Candidate for deletion.

### Dijkstra

| File | Subdir |
|------|--------|
| algorithms/graph/dijkstra.tex | algorithms |
| editorials/dijkstra_editorial.tex | editorials |
| integration/test_reference_graph_tree.tex | integration |
| integration/test_reference_tex_heavy.tex | integration |

Two separate pedagogical versions (algorithms vs editorial) is acceptable — they differ in depth. The integration files are dev tests.

### Persistent Segment Tree

| File | Subdir |
|------|--------|
| algorithms/tree/persistent_segtree.tex | algorithms |
| cses/range_queries_copies.tex | cses |
| integration/test_reference_edge_cases.tex | integration |

The algorithms and cses versions cover different angles (conceptual vs CSES problem). Acceptable.

### BFS

| File | Subdir | Angle |
|------|--------|-------|
| algorithms/graph/bfs.tex | algorithms | Graph/tree BFS |
| editorials/bfs_grid_editorial.tex | editorials | Grid BFS full editorial |
| primitives/grid.tex | primitives | Grid BFS minimal |
| primitives/queue.tex | primitives | Queue-based BFS |
| integration/test_reference_grid_numline.tex | integration | Dev test |

Three distinct angles (graph, grid, queue-centric) — acceptable differentiation.

---

## 4. Axis 3 — Coverage Gaps

### Primitive example counts (all subdirs excluding fixtures/integration)

| Primitive | Count (non-test) | Files |
|-----------|-----------------|-------|
| Array | ~30+ | ubiquitous |
| Graph | ~12 | well-covered |
| DPTable | ~8 | good |
| Tree | ~7 | adequate |
| Plane2D | ~8 | adequate |
| VariableWatch | ~5 | adequate |
| Grid | ~4 | adequate |
| Queue | ~3 | sparse |
| LinkedList | ~2 | **SPARSE** |
| Stack | ~2 | **SPARSE** |
| MetricPlot | ~3 | minimal |
| HashMap | ~1 (primitives only) | **UNDER-REPRESENTED** |
| NumberLine | ~1 (primitives only) | **UNDER-REPRESENTED** |
| Matrix | ~1 (primitives only) | **UNDER-REPRESENTED** |
| CodePanel | ~1 (primitives only) | **UNDER-REPRESENTED** |

**Primitives with <2 real (non-fixture, non-integration) examples:**
- `HashMap` — only `primitives/hashmap.tex`
- `NumberLine` — only `primitives/numberline.tex`
- `Matrix` — only `primitives/matrix.tex`
- `CodePanel` — only `primitives/codepanel.tex`

### Inner command coverage across all pedagogical files (algorithms + cses + editorials + quickstart)

| Command | Used in pedagogical? | Notes |
|---------|---------------------|-------|
| `\shape` | yes | universal |
| `\compute` | yes (frog_foreach, missing_number, permutations, convex_hull) | limited |
| `\step` | yes | universal |
| `\narrate` | yes | universal |
| `\apply` | yes (frog, dptable, li_chao) | moderate |
| `\highlight` | yes (bfs, dijkstra) | sparse |
| `\recolor` | yes | universal |
| `\annotate` | yes | common |
| `\reannotate` | only 1 pedagogical file (union_find_array) | **under-used** |
| `\cursor` | yes (frog, linkedlist_reverse, kmp, binary_search) | moderate |
| `\foreach` | only frog_foreach, foreach_demo | **under-used** |
| `\substory` | only interval_dp | **under-used** |
| `\hl` | **ZERO pedagogical uses** | **critical gap** |

### Algorithm coverage gaps

No example for: **Trie**, **Fenwick tree (BIT)**, **Topological sort**, **Bellman-Ford**, **Floyd-Warshall**, **Segment tree beats**, **SCC (Tarjan/Kosaraju)**, **Suffix array**, **LCA**, **centroid decomposition**.

---

## 5. Axis 4 — Pedagogy / Style Smells

| File | Smell | Detail |
|------|-------|--------|
| algorithms/* (all 23) | No prose / no `\section` | Every algorithms/ file is a bare animation widget — no surrounding explanation, no context paragraph, no section header. Unusable as a standalone editorial. |
| cses/* (all 10) | No prose / no `\section` | Same as above — raw animation blobs with no editorial framing. |
| algorithms/graph/mcmf.tex | One-frame-per-major-transition, thin | Only 5 steps for a complex algorithm — pedagogically insufficient compared to demos/mcmf.tex |
| algorithms/tree/splay.tex | 7 steps, no MetricPlot axis label | MetricPlot used for amortized cost but no `\apply{p}{label=...}` or axis annotations |
| algorithms/tree/hld.tex | 7 steps | HLD is complex; 7 steps under-explains the chain decomposition |
| algorithms/misc/fft_butterfly.tex | Mixed env, no narrative arc | Animation portion tracks FFT stages but no `\narrate` explains why each butterfly operation matters |
| primitives/diagram.tex | 6 lines, trivial | Shows Tree in a diagram but provides zero explanation; barely distinguishable from a fixture |
| primitives/diagram_multi.tex | 6 lines, trivial | Two shapes, no prose |
| quickstart/diagram_intro.tex | 5 lines, trivial | Shortest file in corpus; serves as intro but has no narrative at all |
| algorithms/dp/frog_foreach.tex | Duplicate of frog.tex | Purely a syntax demo — belongs in quickstart/ not dp/ |

---

## 6. Axis 5 — Render Health Signals

| File | Signal | Detail |
|------|--------|--------|
| algorithms/misc/convex_hull_andrew.tex:23 | `grid=on` | Boolean param passed as string `"on"` — may trigger E-code at parse time or silently no-op; either way it is non-conformant |
| demos/mcmf.tex + algorithms/graph/mcmf.tex | Duplicate `id="mcmf"` | If ever composed together in one HTML render, duplicate scene IDs will break step navigation |
| algorithms/misc/fft_butterfly.tex | Mixed diagram+animation | First block is `\begin{diagram}`, second is `\begin{animation}` in same file — valid but the animation's `\step` count of 7 combined with no `\narrate` risk silent step-drop |
| integration/test_reference_tex_heavy.tex | Labeled as `diag` but large | 260 lines marked as diagram (`diag`) in inventory — cross-check: it has no animation env but contains a single large Graph diagram; the file name says "tex_heavy" which suggests rendering stress |
| fixtures/expected-fail/20_cumulative_budget.tex | 210 lines, multi-env, expected-fail | Largest expected-fail fixture — intentionally exercises cumulative budget overflow; render validator must confirm exit-nonzero |
| cses/planets_queries2.tex | 204 lines | References `DPTable` with computed binary-lifting tables via `\compute` — largest compute block in corpus; stress-test for Starlark eval budget |

**No orphan `\end` tags found.** All 191 environment tags balance (151 animation + 40 diagram = 191).

**No `\documentclass`, `\usepackage`, `\newcommand`, TikZ found** in any file.

---

## 7. Subdir-Level Verdicts

| Subdir | Verdict | Notes |
|--------|---------|-------|
| **algorithms/** | Needs major cleanup | 23 bare animation widgets with no prose. High-value content (KMP, CHT, convex hull, HLD) is buried without context. 4 union-find files is 2 too many. algorithms/mcmf.tex should be deleted (superseded by demos/). frog_foreach.tex should move to quickstart/. |
| **cses/** | Needs cleanup | 10 raw animations. Content quality is good (realistic CSES problems) but zero editorial framing. Should either gain `\section` + prose scaffolding or be explicitly designated as a "stand-alone widget" subdir. |
| **demos/** | Healthy | 4 flagship demos are well-structured (prose + sections + narrate). Overlap with algorithms/ on mcmf is the only issue. |
| **editorials/** | Healthy | 4 well-formed full editorials. bfs_grid_editorial.tex at 417 lines is the corpus's richest file. Good model for other subdirs to follow. |
| **fixtures/** | Healthy | Well-organized into pass/expected-fail with numeric prefixes. Comment headers clearly state the regression being tested. Minor gap: no fixture for `\hl`, `\reannotate`, `\cursor` edge cases. |
| **integration/** | Partially redundant | 21 test files with heavy overlap — test_reference_unionfind.tex (295 lines) and test_reference_datastruct.tex (292 lines) are essentially editorials. The boundary with editorials/ is blurry. Consider extracting the prose-heavy ones into editorials/ and keeping integration/ as pure render-stress tests. |
| **primitives/** | Healthy but minimal | All 15 primitives covered (+ 3 diagram variants + substory). Files are intentionally minimal (6–72 lines). Gap: primitives/substory.tex demonstrates the env correctly but the 3 diagram.tex files are near-trivially small (5–10 lines). |
| **quickstart/** | Healthy but thin | Good 4-file intro sequence. Could absorb frog_foreach.tex from algorithms/dp/ as a `\foreach` + `\compute` pattern example. No `\substory` or `\hl` example at the intro level. |
| **smoke/** | Too Plane2D-focused | 3 of 4 smoke tests exercise Plane2D exclusively. gep_v2_smoke.tex is the only one covering Graph. No smoke test for Array, DPTable, or Tree. |

---

## 8. Recommended Follow-Up Agents

### Agent A — Render Validator (priority: HIGH)
**Target:** All 113 `.tex` files (focus first on 23 algorithms/, then 10 cses/, then 4 demos/).
**Task:** Run `python3 render.py <file>` on each, parse stdout/stderr for E-codes and warnings; confirm expected-fail fixtures exit non-zero; capture render time to flag Starlark budget stress (especially `cses/planets_queries2.tex`).
**Key check:** Confirm `grid=on` in `convex_hull_andrew.tex` produces an E-code or documented no-op.
**Estimated:** ~50 files with substantive animations; can batch in parallel by subdir.

### Agent B — Reference Conformance Auditor (priority: HIGH)
**Target:** 23 algorithms/ files + 10 cses/ files (33 total).
**Task:** Deep-read each against reference §5–§10: verify all `\shape` param names match the documented table for that primitive; flag any param not in the reference (candidate undocumented options). Cross-check selector syntax (`primitive.cell[i]` forms). Verify `\compute` Starlark only uses allowed builtins (no `while`, `import`, `lambda`).
**Key suspects:** `convex_hull_trick.tex` (long \compute block), `planets_queries2.tex` (binary lifting via \compute).

### Agent C — Consolidation Planner (priority: MEDIUM)
**Target:** 
- The 4 union-find files (`union_find.tex`, `union_find_graph.tex`, `union_find_tree.tex`, `union_find_array.tex`)
- `algorithms/dp/frog.tex` vs `frog_foreach.tex`
- `algorithms/graph/mcmf.tex` vs `demos/mcmf.tex`
**Task:** Propose a merge/delete/move plan. Produce replacement files that preserve the best of each variant. Move `frog_foreach.tex` → `quickstart/`. Delete `algorithms/graph/mcmf.tex`.

### Agent D — Prose Scaffolding Writer (priority: MEDIUM)
**Target:** All 23 algorithms/ files and 10 cses/ files.
**Task:** Add `\section{...}`, a 2–3 sentence problem description paragraph, and a complexity note around each bare animation. This transforms them from isolated SVG widgets into embeddable editorial fragments matching the editorials/ standard.

### Agent E — Coverage Gap Filler (priority: LOW)
**Target:** Create new example files for:
- `HashMap` (2 new: hash collision resolution, frequency counting)
- `NumberLine` (1 new: binary search on number line)
- `Matrix` (1 new: matrix chain multiplication DP)  
- `CodePanel` (1 new: pseudocode walkthrough synced with Array cursor)
- `\hl` command (add to at least 3 existing files in editorials/)
- `\substory` (add to at least 2 files in algorithms/)
**Estimated:** 7–10 new files + 5 edits.

### Agent F — Smoke Test Expander (priority: LOW)
**Target:** smoke/ subdir.
**Task:** Add smoke tests for Array, DPTable, Tree, and LinkedList (4 new files). The current smoke/ is Plane2D-only. Each new smoke test should be ≤50 lines and exercise one render-critical feature (e.g., large DPTable with annotate arcs).

