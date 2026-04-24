# C — Consolidation Plan: Scriba `.tex` Examples
**Date:** 2026-04-24 | **Audit ref:** 00-scout-triage.md | **Agent:** C

---

## Executive Summary

Of the 113 `.tex` example files, **8 are redundant or clearly misplaced** (1 delete candidate, 1 move, 1 near-duplicate merge, 1 naming-only rename cluster), yielding a **target count of ~106 files** after Phase 1–2 cleanup. The single biggest win is deleting `algorithms/graph/mcmf.tex` (58 lines, 5 steps) and moving `algorithms/dp/frog_foreach.tex` to `quickstart/`, both of which are currently blocked by two references in `tests/integration/test_htd_coverage.py` and `docs/cookbook/` — updating those references is the gating action. The directory taxonomy itself is sound and requires no merges or splits, only a clarified charter for each subdir.

---

## 1. Duplicate / Near-Duplicate Cluster Table

| Cluster | File (full path) | Lines | Similarity hypothesis | Action |
|---------|-----------------|-------|-----------------------|--------|
| **UF-GRAPH** | `examples/algorithms/graph/union_find.tex` | 129 | PRIMARY: path-compression trace in English, `id="union-find"`, layout_seed=17 | **KEEP** |
| | `examples/algorithms/graph/union_find_graph.tex` | 91 | Same algorithm, same Graph+Array primitives, fixed-position layout (layout_seed=42), narrate in Vietnamese, shorter story — subset of union_find.tex | **MERGE into union_find.tex** (absorb Vietnamese locale note as `\narrate` variant or comment) |
| **UF-ARRAY** | `examples/algorithms/graph/union_find_array.tex` | 94 | Distinct: only Array primitive + `\reannotate` arcs — different primitive angle | **KEEP** |
| **UF-TREE** | `examples/algorithms/graph/union_find_tree.tex` | 113 | Distinct: Tree primitive + virtual root — different primitive | **KEEP** |
| **FROG-DP** | `examples/algorithms/dp/frog.tex` | 68 | PRIMARY: manual step-by-step AtCoder DP-A | **KEEP** (in algorithms/dp/) |
| | `examples/algorithms/dp/frog_foreach.tex` | 75 | Same data (`h[]`), same algorithm, same final dp[] values; differs only in using `\foreach`+`\compute` instead of manual steps — pure syntax demo | **MOVE** to `quickstart/` |
| **MCMF** | `examples/algorithms/graph/mcmf.tex` | 58 | Thin sketch: 5 steps, single Graph primitive, bare narrate in Vietnamese, `id="mcmf"` — strict subset of demos/ version | **DELETE** (blocked — see §7) |
| | `examples/demos/mcmf.tex` | 266 | Full multi-animation flagship: prose, `\section`, diagram + animation, VariableWatch, `id="mcmf-spfa"` | **KEEP** |

**diff evidence:**
- `union_find.tex` vs `union_find_graph.tex`: 41 lines added / 79 removed / ~17 modified. The graph is structurally identical (7 nodes A–G, same union/find sequence); only narrate language and seed differ. Not independently valuable.
- `frog.tex` vs `frog_foreach.tex`: 45 lines added / 38 removed. Identical `\shape` declarations and final dp[] values; every operational difference is `\foreach`/`\compute` syntax sugar — pedagogical home is quickstart/, not dp/.
- `algorithms/graph/mcmf.tex` vs `demos/mcmf.tex`: 256 lines added / 48 removed; the thin file's entire animation body appears as a subset of the demos/ walkthrough.

---

## 2. Misplaced-File Table

| File | Current dir | Proposed dir | Reason |
|------|-------------|--------------|--------|
| `examples/algorithms/dp/frog_foreach.tex` | `algorithms/dp/` | `quickstart/` | Adds no new algorithm; sole purpose is demonstrating `\foreach`+`\compute` syntax — fits alongside `foreach_demo.tex` in quickstart/ |
| `examples/primitives/diagram.tex` | `primitives/` | `primitives/` (keep, but expand) | 6 lines — technically correct subdir but trivially thin; candidate for expansion in Agent D, not a move |
| `examples/primitives/diagram_multi.tex` | `primitives/` | `primitives/` (keep, expand) | Same — 6 lines, two shapes, no prose |
| `examples/integration/test_reference_editorial.tex` | `integration/` | `editorials/` | 129 lines of Two-Sum editorial prose with `\section`; it is a full editorial, not a render-stress test. Naming (`test_reference_*`) is misleading. |
| `examples/integration/test_reference_datastruct.tex` | `integration/` | `integration/` (keep, clarify) | 292 lines of data-structure omnibus — borderline, but it exercises render stress across 6 primitives simultaneously; legitimate integration test |

Note: `integration/test_reference_editorial.tex` is the only clear misplacement worth acting on in a reorganisation.

---

## 3. Proposed Directory Structure

```
examples/
├── algorithms/          # Bare animation widgets, one per algorithm; no prose required.
│   ├── dp/              # Dynamic programming (frog, interval_dp, convex_hull_trick, dp_optimization)
│   ├── graph/           # Graph algorithms (bfs, dijkstra, kruskal_mst, union_find×3, mcmf DELETED)
│   ├── misc/            # Uncategorised algorithms (convex_hull_andrew, fft_butterfly, li_chao,
│   │                    #   linkedlist_reverse, simulated_annealing)
│   ├── string/          # String algorithms (kmp)
│   └── tree/            # Tree algorithms (bst_operations, hld, persistent_segtree, splay)
│
├── cses/                # One file per CSES problem; stand-alone animation widgets.
│
├── demos/               # Flagship multi-animation showcases with full prose (dinic, maxflow, mcmf,
│                        #   tutorial_en). High visual polish; referenced from README/docs.
│
├── editorials/          # Full editorial documents: \section + prose + animation.
│                        #   Add test_reference_editorial.tex here (renamed → two_sum_editorial.tex).
│
├── fixtures/            # Regression fixtures only; numeric prefix required.
│   ├── pass/            # Must render successfully.
│   └── expected-fail/   # Must fail with a specific E-code.
│
├── integration/         # Render-stress / feature-coverage tests (test_* prefix required).
│                        #   Remove test_reference_editorial.tex (moved to editorials/).
│
├── primitives/          # One minimal demo per primitive type (15 files + 3 diagram variants
│                        #   + substory). Intentionally thin — first-look reference.
│
├── quickstart/          # First-5-minutes onboarding sequence: hello, diagram_intro,
│                        #   binary_search, foreach_demo. Add frog_foreach.tex here.
│
└── smoke/               # Fast sanity renders; should cover all major primitive families,
                         #   not just Plane2D. Expand to include Array/DPTable/Tree smoke tests.
```

**Justification for no merges/splits:**
- `demos/` and `editorials/` kept separate: demos are multi-animation flagships; editorials are prose-first documents.
- `integration/` and `fixtures/` remain separate: fixtures are pinned regression cases; integration/ tests cover render quality without expected-fail semantics.
- No new directories invented.

---

## 4. Move / Delete Manifest

### DELETE (1 file)
- `git rm examples/algorithms/graph/mcmf.tex`
  - BLOCKED until: (a) `tests/integration/test_htd_coverage.py` line 25 removed, (b) `docs/cookbook/HARD-TO-DISPLAY-COVERAGE.md` line 74 updated.

### MOVE (2 files)
- `git mv examples/algorithms/dp/frog_foreach.tex examples/quickstart/frog_foreach.tex`
  - BLOCKED until: `docs/cookbook/12-foreach-apply-dp-table.md` line 200 path updated; `docs/cookbook/README.md` line 32 file-list updated.
- `git mv examples/integration/test_reference_editorial.tex examples/editorials/two_sum_editorial.tex`
  - No external references found — safe to execute in Phase 2.

### MERGE (1 file pair → 1 file)
- Absorb content from `examples/algorithms/graph/union_find_graph.tex` into `examples/algorithms/graph/union_find.tex`, then `git rm examples/algorithms/graph/union_find_graph.tex`.
  - No external references to `union_find_graph.tex` found — safe once merge is reviewed.

### RENAME (0 files)
- No renames needed in Phase 1; naming convention violations are documentation-only in this pass.

### KEEP (remaining 109 files)

---

## 5. Naming Convention

**Current state:** The corpus uses exclusively `snake_case` for all example file names. Zero `kebab-case` names. Fixtures use `NN_description.tex` numeric-prefix pattern.

**Proposed rule:** `snake_case` throughout. No kebab-case. Fixtures keep `NN_` prefix.

**Violations:** None. All 113 files already comply.

---

## 6. Per-Subdir Verdict

**algorithms/ — KEEP, thin cleanup.** Retain 23→21 files after deleting `mcmf.tex` and moving `frog_foreach.tex`. The four union-find files should reduce to three after the `union_find_graph.tex` merge.

**cses/ — KEEP as-is.** All 10 files are distinct CSES problems with no duplicates.

**demos/ — KEEP as-is.** Four flagship demos are well-structured and well-referenced from `benchmarks/bench_render.py`.

**editorials/ — KEEP, accept one addition.** Accept `test_reference_editorial.tex` moved from integration/ and renamed `two_sum_editorial.tex`.

**fixtures/ — KEEP as-is.** Twenty-four files, all correctly organized into pass/expected-fail.

**integration/ — KEEP, lose one file.** After moving `test_reference_editorial.tex` out, 20 files remain.

**primitives/ — KEEP, expand in place.** All 19 files are correctly placed. Thin diagram files are candidates for Agent D expansion.

**quickstart/ — KEEP, accept one addition.** Absorbing `frog_foreach.tex` brings it to 5 files and completes the narrative: hello → diagram → binary_search → foreach_demo → frog_foreach.

**smoke/ — KEEP, flag for expansion.** All 4 files exercise Plane2D exclusively. Should expand to include Array/DPTable/Tree smoke tests (Agent F task).

---

## 7. Impact on Build / CI — Hardcoded Path References

| Blocking action | File | Location | Update required |
|----------------|------|----------|-----------------|
| DELETE `algorithms/graph/mcmf.tex` | `tests/integration/test_htd_coverage.py` | Line 25 | Remove tuple; update `test_algorithm_count` lower-bound `>=19` → `>=18` |
| DELETE `algorithms/graph/mcmf.tex` | `docs/cookbook/HARD-TO-DISPLAY-COVERAGE.md` | Line 74 | Note superseded by demos/ version |
| MOVE `frog_foreach.tex` → quickstart/ | `docs/cookbook/12-foreach-apply-dp-table.md` | Line 200 | Update path |
| MOVE `frog_foreach.tex` → quickstart/ | `docs/cookbook/README.md` | Line 32 | Remove from dp/, note in quickstart/ |

**CI analysis:** `test.yml`/`release.yml` contain no hardcoded `.tex` paths. `build.sh` uses `find`. Only test-suite path check is `test_algorithm_count` asserting `>=19`.

**Benchmarks:** `benchmarks/bench_render.py` hardcodes files not in change set — no benchmark updates required.

**Visual regression references:** None of the moved/deleted files are cited as regression baselines.

---

## 8. Phased Execution Plan

### Phase 1 — Safe deletes + moves
1. Update `tests/integration/test_htd_coverage.py` line 25: remove `mcmf.tex` tuple; change `>=19` → `>=18`.
2. Update `docs/cookbook/HARD-TO-DISPLAY-COVERAGE.md` line 74: note superseded.
3. `git rm examples/algorithms/graph/mcmf.tex`
4. Update `docs/cookbook/12-foreach-apply-dp-table.md` line 200: new path.
5. Update `docs/cookbook/README.md` line 32: move frog_foreach from dp/ list to quickstart/ list.
6. `git mv examples/algorithms/dp/frog_foreach.tex examples/quickstart/frog_foreach.tex`

Commit: `chore(examples): delete thin mcmf sketch, move frog_foreach to quickstart`

### Phase 2 — Directory reorganisation
1. `git mv examples/integration/test_reference_editorial.tex examples/editorials/two_sum_editorial.tex`

Commit: `chore(examples): promote two_sum_editorial from integration/ to editorials/`

### Phase 3 — Merge duplicate content
1. Manually review `union_find_graph.tex` (91 lines) against `union_find.tex` (129 lines).
2. Add `\substory` or `\narrate` note covering fixed-position layout variant.
3. `git rm examples/algorithms/graph/union_find_graph.tex`

Commit: `chore(examples): merge union_find_graph into union_find, remove near-duplicate`

**Total file delta:** 113 → 110 after Phase 1 → 109 after Phase 3. Target steady-state: **109 files**.
