# Cookbook Coverage Matrix — Agent 12/14

## Scope

Map every `examples/cookbook/*.tex` example (Scriba v0.5.1, HEAD `eb4f017`) against
the full primitive × pattern matrix to find which author scenarios lack a
demonstrable template. Read-only inventory derived from the `.tex` sources
themselves (no rendering). Patterns evaluated: **add**, **highlight**,
**recolor**, **apply/modify**, **compose**, **narrate**. The brief listed
"11 primitives"; Scriba actually ships 15 primitive classes under
`scriba/animation/primitives/`. This audit uses the 11 the brief implies
(Array, DPTable, NumberLine, Plane2D, Stack, Queue, Graph, Tree, MetricPlot,
HashMap, LinkedList) and notes the rest (`Matrix`, `Grid`, `CodePanel`,
`VariableWatch`) as zero-coverage extras in the gap list.

## Cookbook inventory

13 `.tex` files totaling 1 182 lines / 114 `\step` frames.

| # | File | Lines | Steps | Primitives declared | Topic |
|---|------|------:|------:|---------------------|-------|
| 1 | `foreach_demo.tex` | 79 | 7 | Array×2 | pattern demo (loop) |
| 2 | `frog1_dp.tex` | 68 | 8 | Array×2 | DP (linear) |
| 3 | `frog1_dp_foreach.tex` | 75 | 8 | Array×2 | DP (linear, foreach rewrite) |
| 4 | `convex_hull_andrew.tex` | 301 | 23 | Plane2D, Stack | Geometry (convex hull) |
| 5 | `h01_zuma_interval_dp.tex` | 93 | 9 | Array, DPTable | DP (interval) |
| 6 | `h02_dp_optimization.tex` | 98 | 7 | DPTable, NumberLine | DP (Knuth opt) |
| 7 | `h04_fft_butterfly.tex` | 91 | 7 | Plane2D, Array | Math (FFT) |
| 8 | `h05_mcmf.tex` | 58 | 5 | Graph | Graph (flow) |
| 9 | `h06_li_chao.tex` | 51 | 8 | Plane2D | DP (CHT via Li Chao) |
| 10 | `h07_splay_amortized.tex` | 58 | 9 | Tree, MetricPlot | Tree (splay) |
| 11 | `h08_persistent_segtree.tex` | 62 | 7 | Tree(segtree) | Tree (persistent) |
| 12 | `h09_simulated_annealing.tex` | 75 | 9 | Graph, MetricPlot | Heuristic (SA/TSP) |
| 13 | `h10_hld.tex` | 73 | 7 | Tree, Array | Tree (HLD) |

Primitive-occurrence totals (shapes actually declared in cookbook):
Array 8, DPTable 3, Plane2D 3, Tree 3, Graph 2, MetricPlot 2, Stack 1,
NumberLine 1, **HashMap 0, Queue 0, LinkedList 0** (+ Matrix / Grid /
CodePanel / VariableWatch all 0).

## Primitive × Pattern matrix (11 × 6)

Legend: filename(s) = demonstrated; ⚠ = present but trivial / only 1 frame;
❌ = no example.

| Primitive \\ Pattern | add | highlight | recolor | apply/modify | compose | narrate |
|---|---|---|---|---|---|---|
| **Array** | ❌ (no mid-anim insert) | ⚠ `convex_hull` (via Plane2D only — Array `\highlight` never used) | `frog1_dp`, `frog1_dp_foreach`, `foreach_demo`, `h01_zuma`, `h04_fft`, `h10_hld` | `frog1_dp`, `frog1_dp_foreach`, `h04_fft`, `h10_hld`, `foreach_demo` (value writes) | `h01_zuma` (Array+DPTable), `h04_fft` (Array+Plane2D), `h10_hld` (Array+Tree), `frog1_dp` (Array+Array) | every Array file |
| **DPTable** | ❌ | ❌ | `h01_zuma`, `h02_dp_opt` | `h01_zuma`, `h02_dp_opt` (value=) | `h01_zuma` (+Array), `h02_dp_opt` (+NumberLine) | both |
| **NumberLine** | ❌ | ❌ | ⚠ `h02_dp_opt` (tick recolor only) | ❌ (no `set_value` / marker push) | `h02_dp_opt` (+DPTable) | `h02_dp_opt` |
| **Plane2D** | `convex_hull` (`add_segment`), `h04_fft` (`add_point`), `h06_li_chao` (`add_line`) | `convex_hull` (`\highlight{plane.point[..]}`) | `h04_fft`, `h06_li_chao`, `convex_hull` (segment states) | `convex_hull` (add_segment / add_point) | `convex_hull` (+Stack), `h04_fft` (+Array) | all three |
| **Stack** | `convex_hull` (`push=`) | ❌ | ❌ (no state recolor of stack cells) | `convex_hull` (push/pop via apply) | `convex_hull` (+Plane2D) | `convex_hull` |
| **Queue** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Graph** | ❌ (no `add_node` / `add_edge` mid-anim) | ❌ (no `\highlight{G.node[..]}`) | `h05_mcmf`, `h09_sim_anneal` | ❌ (no structural mutation — edges recolored only) | `h09_sim_anneal` (+MetricPlot) | both |
| **Tree** | ❌ | ❌ | `h07_splay`, `h08_persistent`, `h10_hld` | ⚠ `h07_splay` (implicit — uses recolor, no rotate op) | `h07_splay` (+MetricPlot), `h10_hld` (+Array) | all three |
| **MetricPlot** | ❌ (series declared, no `add_series`) | ❌ | ❌ | `h07_splay`, `h09_sim_anneal` (`phi=`, `cost=`, `temp=`) | `h07_splay` (+Tree), `h09_sim_anneal` (+Graph) | both |
| **HashMap** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **LinkedList** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Raw cell counts:** 66 total cells, **28 covered (42 %)**, **3 trivial (5 %)**,
**35 empty (53 %)**. Two primitives (HashMap, Queue, LinkedList — three if
counted) are completely absent from the cookbook.

## Topic coverage

| CP topic | Status | Notes / nearest example |
|---|---|---|
| **Sort** (quick/merge/heap) | ❌ | No cookbook entry — foreach_demo touches an array but is a pattern demo, not a sort. |
| **Search — binary** | ❌ | None. |
| **Search — BFS/DFS** | ❌ | `h05_mcmf` traverses a graph but only as MCMF augmenting paths, not a BFS/DFS template. |
| **Graph — Dijkstra / MST / Toposort / SCC** | ⚠ | `h05_mcmf` covers flow; `h09_sim_anneal` uses Graph only as a TSP canvas. No Dijkstra / MST / topo / SCC. |
| **Tree — BST / AVL / segment / Fenwick / trie** | ⚠ | `h07_splay` (splay), `h08_persistent_segtree` (persistent segtree), `h10_hld` (HLD). No plain BST insert, no AVL, no Fenwick, no trie. |
| **DP — knapsack / LIS / coin change / interval / optimizations** | ✅ | `frog1_dp`(×2), `h01_zuma_interval_dp`, `h02_dp_optimization`, `h06_li_chao`. Classic 0/1 knapsack / LIS / coin change still missing. |
| **String — KMP / Z / suffix array / hashing** | ❌ | None. |
| **Geometry — convex hull / sweepline / closest pair** | ⚠ | `convex_hull_andrew` covers monotone chain — the only geometry example. No sweepline, no closest pair, no rotating-calipers. |
| **Math / number theory — sieve, GCD, modexp, CRT** | ⚠ | `h04_fft_butterfly` is the only math entry. No sieve / GCD / modexp / CRT. |

Overall: 1 topic family fully covered (DP, partially), 4 trivially covered, 4 empty.

## Prioritized gap list

### HIGH priority (common author scenarios with no template)

1. **Array × add** — inserting a value mid-animation (e.g. reading input,
   streaming). Blocks any "grow the array" narrative. No primitive blocker —
   Array already supports `apply{value=…}` on a pre-sized cell but no
   `append` / `resize`. (→ Agent 2.)
2. **Array × highlight** — `\highlight{a.cell[i]}` equivalent is never
   demonstrated; authors currently abuse `state=current`. Covered by `\cursor`
   in `frog1_dp`, but not explicitly.
3. **DPTable × add / highlight** — no example shows cell-range highlight or
   appending a row (authors will need it for online DP).
4. **Graph × add / apply** — a graph that grows edges/nodes mid-animation
   (e.g. Kruskal MST, incremental SCC, union-find). Entirely absent.
5. **Graph × highlight** — `\highlight{G.node[..]}` never used; MCMF / SA rely
   on `recolor` alone.
6. **Queue primitive — all 6 cells** — BFS is a flagship CP use case and
   cannot be demonstrated without a working Queue template.
7. **HashMap primitive — all 6 cells** — blocks sliding-window, two-sum,
   LRU, frequency-count narratives.
8. **String topic family** — KMP / Z / suffix array all require a primitive
   (Array or a dedicated StringRibbon) with highlight + recolor + apply.
9. **Tree × apply (structural)** — rotations, insertions, deletions in a
   BST / AVL / segtree build. `h07_splay` narrates splay verbally but never
   issues a structural mutation — the tree layout is fixed. Likely blocked
   by missing `Tree.rotate` / `Tree.insert` apply ops. (→ Agent 2.)

### MEDIUM priority

10. **Stack × highlight / recolor** — convex_hull only uses `push`. Stack cell
    state transitions (e.g. current-top, popped-dim) unused.
11. **NumberLine × apply / add** — no example pushes a marker, sweeps a
    pointer, or toggles a range interval. Would unblock binary search /
    two-pointer / sweepline stories.
12. **MetricPlot × add / highlight / recolor** — currently only append points;
    no example highlights a single marker or recolors a past curve segment.
13. **LinkedList primitive — all 6 cells** — lower author demand than
    HashMap / Queue, but still a named primitive with no template.
14. **Sort topic** — one example that walks quicksort or mergesort partitions
    an Array with recolor + compose narration would cover many onboarding
    scenarios at once.
15. **Binary search topic** — trivially composable from Array + NumberLine
    once NumberLine × apply lands.

### LOW priority

16. **MetricPlot × compose with a third primitive** — already covered by
    h07/h09 pairings; a 3-shape compose would be polish.
17. **Plane2D × highlight** — covered (convex_hull), but only via point
    highlight; a region / polygon highlight variant would round it out.
18. **Dedicated advanced primitives** (`Matrix`, `Grid`, `CodePanel`,
    `VariableWatch`) have zero cookbook coverage. Matrix + Grid matter for
    matrix-exponentiation and board-DP; CodePanel is useful for annotated
    pseudocode; VariableWatch for loop-variable tracing.

## Recommendations (next examples to add, in priority order)

1. **`bfs_shortest_path.tex`** — Graph + Queue, BFS from a source. Fills
   Queue primitive, Graph × highlight, Search topic. ~8 steps.
2. **`two_sum_hashmap.tex`** — Array + HashMap, streaming scan with
   `\apply{hm}{put=…}`. Fills HashMap primitive and Array × add. ~6 steps.
3. **`mergesort_sort.tex`** — Array × recolor + compose (left/right buffers),
   classic sort template. Fills Sort topic. ~10 steps.
4. **`kmp_prefix_function.tex`** — Array + (optional) CodePanel for pattern
   matching. Fills String topic. ~9 steps.
5. **`dijkstra_shortest_path.tex`** — Graph + Array (dist), priority-queue
   style, fills Graph topic beyond flow. ~10 steps.
6. **`bst_insert_rotations.tex`** — Tree × structural apply; blocked until
   Tree primitive exposes `insert` / `rotate` ops (coordinate with Agent 2).
7. **`sieve_of_eratosthenes.tex`** — Array recolor + NumberLine apply,
   fills Math topic and NumberLine × apply. ~7 steps.
8. **`binary_search.tex`** — Array + NumberLine compose, lo/mid/hi pointers.
   Fills Search topic and NumberLine gap. ~8 steps.
9. **`union_find_kruskal.tex`** — Graph × add (incremental), covers MST.
   Blocked on `Graph.add_edge` mid-animation if not yet wired.
10. **`linked_list_reverse.tex`** — LinkedList primitive opener (pointer
    rewiring), covers its matrix row.

Shared pattern: each recommendation tries to fill two gaps simultaneously
(one primitive cell × one topic family) so a small authoring sprint can
lift cookbook coverage from 42 % to ~70 % with ~10 new files.

## Severity summary

| Severity | Count | Examples |
|---|---:|---|
| CRITICAL (primitive with zero cookbook demonstration and clear author demand) | 3 | Queue, HashMap, LinkedList |
| HIGH (matrix cell missing + common use case) | 9 | Array×add, Graph×add/highlight/apply, DPTable×add/highlight, Tree×apply, Stack×highlight, NumberLine×apply |
| MEDIUM (topic family empty or trivial) | 6 | Sort, Binary search, BFS/DFS, String, Math, Graph algos beyond flow |
| LOW (polish, compose variants, extra primitives) | 4 | Matrix/Grid/CodePanel/VariableWatch absent |

**Bottom line:** the cookbook demonstrates ~42 % of the defined 11 × 6 matrix,
skews heavily toward Array + DP + Tree, and has **zero coverage for three
named primitives** and **four CP topic families**. Closing the HIGH-priority
gaps above needs ~10 new examples plus 1–2 primitive feature completions
(Tree structural apply, Graph mid-animation mutation) that should be
cross-checked against Agent 2's primitive feature report.
