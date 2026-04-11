# 02 — Dynamic-Op Gaps

**Agent:** 2 / 14 (Completeness audit)
**Scope:** Dynamic operation matrix across the 11 user-facing primitives.
**Method:** Read-only scan of `scriba/animation/primitives/*.py`, `scriba/animation/scene.py`, `scriba/animation/emitter.py`, and `examples/cookbook/*.tex`.
**Audit frame:** what DSL commands can *mutate* a primitive between frames? Structural ops (add/remove/clear/move/swap), identity ops (rename/replace), and attribute ops (update_attr).

## Scope

A primitive's dynamic surface is the union of three channels:

1. **`\apply{target}{...}`** — dispatched into `Primitive.apply_command(params)` in `emitter.py:361-386` (pre-pass, before bbox). This is the only channel that can mutate **structure** (e.g. push an item, insert a node, append a point).
2. **`\apply{target}{value=X}`** — stored on `ShapeTargetState.value` (`scene.py:528-530`), then routed to `prim.set_value(suffix, val)` in `emitter.py:445-446` during render. This is an **in-place replace** with no structural change.
3. **`\recolor` / `\reannotate` / `\highlight` / `\annotate` / `\cursor`** — attribute-only channels acting on already-declared addressable parts. These can never create or destroy parts.

`\apply{...}{label=X}` is parsed into `ShapeTargetState.label` (`scene.py:531-533`) but **never consumed** by `emitter.py` or `renderer.py`. `PrimitiveBase.set_label()` is defined (`base.py:228`) but has zero callers outside its own definition — a dead API. Relabel is therefore broken across **all 11 primitives**, and this is counted as a `❌` in the matrix below.

Of the 11 primitives, only **6** implement `apply_command`:

| Primitive | `apply_command` | `set_value` (override) |
|-----------|:---------------:|:----------------------:|
| Array         | ❌  | base (generic)   |
| NumberLine    | ❌  | base             |
| Plane2D       | ✅ (add-only) | ❌       |
| Grid (2D)     | ❌  | base             |
| Tree          | ❌  | base             |
| Graph         | ❌  | base             |
| Stack         | ✅ (push/pop) | ❌       |
| Queue         | ✅ (enqueue/dequeue) | ✅ |
| HashMap (Dict)| ✅ (bucket value) | ✅   |
| LinkedList    | ✅ (insert/remove/value) | ✅ |
| MetricPlot    | ✅ (append-only feed) | ❌ |

## Coverage matrix (11 × 8)

Columns: **Add** (insert new element), **Remove** (delete), **Clear** (wipe all), **Move** (reposition without delete+add), **Rename** (change label text), **Swap** (exchange two elements), **Replace** (substitute value in place), **Attr** (update_attr: color/state/highlight without structural change).

Legend:  ✅ supported (with command) — ⚠️ workaround only — ❌ missing.

| Primitive    | Add                         | Remove | Clear | Move | Rename                        | Swap | Replace                        | Attr |
|--------------|-----------------------------|--------|-------|------|-------------------------------|------|--------------------------------|------|
| Array        | ❌ fixed-size                | ⚠️ `recolor state=dim` | ❌ | ❌ | ❌ `label=` unwired | ⚠️ 2× `value=` | ✅ `\apply{a.cell[i]}{value=X}` | ✅ `\recolor`/`\highlight` |
| NumberLine   | ❌ fixed domain/ticks        | ⚠️ `state=dim` on tick | ❌ | ❌ | ❌                            | ❌ | ❌ tick labels frozen at shape | ✅ |
| Plane2D      | ✅ `add_point`/`add_line`/`add_segment`/`add_polygon`/`add_region` | ⚠️ **`state=dim` only** (convex-hull workaround) | ❌ | ❌ | ❌ | ❌ | ❌ no replace_point | ✅ |
| Grid (2D)    | ❌ fixed rows×cols           | ⚠️ `state=dim` on cell | ❌ | ❌ | ❌                            | ⚠️ 2× `value=` | ✅ `\apply{g.cell[r][c]}{value=X}` | ✅ |
| Tree         | ❌ nodes/edges frozen at `\shape` | ⚠️ `state=dim` on node/edge | ❌ | ❌ | ❌ `node_labels` frozen | ❌ | ❌ no change node value | ✅ |
| Graph        | ❌ nodes/edges frozen        | ⚠️ `state=dim` | ❌ | ❌ | ❌                            | ❌ | ❌ | ✅ |
| Stack        | ✅ `\apply{s}{push="X"}`    | ✅ `\apply{s}{pop=N}` | ❌ no `pop=all` | ❌ | ❌ | ❌ | ❌ can't edit mid-stack | ✅ |
| Queue        | ✅ `\apply{q}{enqueue=X}`   | ✅ `\apply{q}{dequeue=true}` | ❌ | ❌ | ❌ | ❌ | ✅ `\apply{q.cell[i]}{value=X}` | ✅ |
| HashMap/Dict | ❌ bucket slots frozen at capacity; only values change | ⚠️ set bucket to `""` | ❌ | ❌ | ❌ | ❌ 2× `value=` | ✅ `\apply{hm.bucket[i]}{value=X}` | ✅ |
| LinkedList   | ✅ `\apply{ll}{insert={index,value}}` | ✅ `\apply{ll}{remove=i}` | ❌ | ❌ | ❌ | ❌ | ✅ `\apply{ll.node[i]}{value=X}` | ✅ |
| MetricPlot   | ✅ `\apply{p}{phi=3.2,...}` (append-only time-series feed) | ❌ no rewind | ❌ | N/A | ❌ rename series | N/A | ❌ no overwrite last sample | ✅ state on series |

**Observations from the matrix:**

- **8 of 11** primitives have no structural `add`.
- **10 of 11** have no real `remove` (LinkedList is the only true deletion; Stack/Queue delete but only from an end).
- **0 of 11** support `clear`, `move`, `swap`, or `rename`.
- `update_attr` is the only universally complete column, delivered by `\recolor` / `\highlight` / `\annotate` plus `get_state`/`set_state` in `PrimitiveBase`.

## Prioritized gap list (HIGH first)

### HIGH — blocks common CP / algorithms courseware

1. **`Plane2D.remove_point` / `remove_segment` / `remove_line` / `remove_polygon`**
   *Algorithms:* Andrew's monotone chain and Graham scan (pop interior points); Delaunay edge flip (remove old edge, add new); incremental convex hull maintenance; sweep-line event removal; art gallery / visibility polygon edits.
   *Current workaround:* `\recolor{plane.point[2]}{state=dim}` in `convex_hull_andrew.tex` (8 occurrences at lines 113–224). Dimmed points still consume indices, bounding box, and visual ink — **pedagogically misleading**: the algorithm deletes them, the lesson pretends it doesn't.
   *Cost:* moderate. Selectors are list-indexed (`point[i]`), so removal shifts subsequent indices and breaks any references already baked into later frames. Needs a design decision: (a) tombstone-in-place, keeping indices stable; (b) stable-ID rewrite where points carry opaque IDs rather than list positions; (c) per-frame snapshot where later frames rebuild from scratch. Option (a) is the smallest patch.

2. **`Tree.remove_node` / `remove_edge` / `add_node` / `add_edge`**
   *Algorithms:* BST insertion + deletion (the entire point of the visualization); AVL / red-black rotations (which combine removal + re-add); splay tree restructuring (already in cookbook as `h07_splay_amortized.tex`, relying only on `state=dim`); trie insertion; tree DP with node elimination.
   *Current workaround:* declare all possible final nodes/edges at `\shape` time, then state=dim the "not-yet-inserted" ones. Works for pre-computable executions, fails for data-dependent shapes.
   *Cost:* needs design. Reingold-Tilford layout recomputes every frame from `children_map`, so structural mutation is tractable, but edge endpoints and node IDs need a stable-ID story. Estimate: medium design, small-to-medium code.

3. **`Graph.add_edge` / `remove_edge`**
   *Algorithms:* Kruskal's MST (add edge per step); Prim's MST (grow tree); Borůvka; dynamic connectivity; edge contraction (min-cut); MCMF residual updates (`h05_mcmf.tex` currently relies on `state=dim` for `G.edge[(a,d)]`).
   *Cost:* moderate. Nodes are fixed at layout time, so edges alone is tractable. Force-directed layout already accepts seeded positions; adding/removing edges doesn't require relayout and is the cheap first cut.

4. **Universal `rename` / relabel**
   *Algorithms:* Union-Find (`parent[x] = root`); renaming sub-problem boundaries in DP; labeling nodes after BFS/DFS discovery order; relabelling in amortized analysis.
   *Current state:* the DSL `\apply{...}{label=X}` path parses correctly (`scene.py:531`) but nothing consumes `ShapeTargetState.label` in the emitter. `PrimitiveBase.set_label()` exists but has zero call sites. This is **dead code** masquerading as a feature.
   *Cost:* trivial. One ~5-line patch in `emitter.py` alongside the existing `set_value` dispatch at 445–446 would wire it through, plus a per-primitive decision about where the label lives (e.g. tree node label override, array cell label override, stack item label override).

### MEDIUM — nice for clarity and pedagogy

5. **Universal `clear` / `reset`**
   *Algorithms:* resetting the visited set between graph traversals; clearing the DP working row between phases; clearing a queue at phase boundary (BFS layer reset). Currently simulated by dimming every element in a `\foreach` block.
   *Cost:* trivial on apply_command-aware primitives (Stack, Queue, LinkedList, Plane2D). Zero-cost alias: `\apply{s}{pop=999}` already works for Stack; formalizing `clear=true` is a one-liner.

6. **`Plane2D.move_point` (reposition without delete+add)**
   *Algorithms:* gradient descent / simulated annealing trajectories (cookbook `h09_simulated_annealing.tex` currently `add_point`s a new dot every frame and dims the old ones, accumulating visual noise); physics integration; particle swarm.
   *Cost:* trivial if IDs are stable — mutate `self.points[i]` in place. Today, selectors are index-based so `move` is indistinguishable from `replace-in-place`, making the surface design small.

7. **Array / Grid / LinkedList `swap`**
   *Algorithms:* every sorting algorithm (bubble, insertion, selection, quicksort partition, heapsort sift-down); union-find path compression; BST rotation.
   *Current workaround:* two sequential `\apply{...}{value=X}` writes with a highlight in between. Works, but the semantic "these two cells swapped" is lost to the viewer — they see two unrelated writes.
   *Cost:* moderate. A first-class `swap` would allow a choreographed cross-fade / motion-path animation; the state model is fine today, the motion story is the hard part.

8. **HashMap/Dict `remove` (delete key)**
   *Algorithms:* tombstoning in open addressing; LRU cache eviction; Rabin-Karp window slide (remove old key, add new).
   *Current workaround:* `\apply{hm.bucket[i]}{value=""}` — empty string, not a real deletion. Works for open-addressing but tombstones vs. empty is a real distinction the current model cannot express.
   *Cost:* trivial; adds a `"tombstone"` state alongside `idle`/`active`/etc.

### LOW — edge cases

9. **MetricPlot `truncate` / `rewind`** — undo last sample for interactive "what-if" traces. Rarely needed; authors re-shape instead.
10. **NumberLine dynamic ticks** — resize/append ticks. Algorithms almost never need this; a wider NumberLine with dimmed unused ticks suffices.
11. **Grid row/column insert** — used in editorial DP visualizations to "reveal" a new row. Currently done by sizing the grid to the final dimensions and dimming the not-yet-computed cells. Loses nothing pedagogically.

## Workaround patterns observed in cookbook

Scanned all 13 cookbook `.tex` files. Two dominant anti-patterns:

### Pattern A — "dim-as-delete" (49 occurrences across 11 files)

`\recolor{<selector>}{state=dim}` stands in for structural removal. Breakdown:

| File                         | `state=dim` uses | Primitive affected         | Intended op          |
|------------------------------|:----------------:|----------------------------|----------------------|
| `convex_hull_andrew.tex`     | 8                | Plane2D point + segment    | remove on pop        |
| `h04_fft_butterfly.tex`      | 7                | Plane2D point, Array cell  | remove / not-yet     |
| `frog1_dp_foreach.tex`       | 5                | Array cell                 | mark as "consumed"   |
| `h06_li_chao.tex`            | 3                | Plane2D line               | line replaced in trie|
| `h09_simulated_annealing.tex`| 6                | Plane2D point              | old trajectory point |
| `h10_hld.tex`                | 6                | Tree node/edge             | not on active chain  |
| `h08_persistent_segtree.tex` | 8                | Tree node                  | version abandoned    |
| `h05_mcmf.tex`               | 1                | Graph edge                 | saturated in residual|
| `h07_splay_amortized.tex`    | 2                | Tree node                  | splayed-away         |
| `h02_dp_optimization.tex`    | 1                | NumberLine tick            | pruned from sweep    |
| `foreach_demo.tex`           | 2                | Array, DPTable             | pedagogy step        |

**The `dim` state is overloaded.** It means "discarded", "not-yet-visited", "archived", "saturated", and "out-of-scope" depending on context. Viewers cannot distinguish. Every `HIGH` gap above is a cell in this table.

### Pattern B — "declare-all-up-front" (implicit in every Tree/Graph example)

Cookbook authors enumerate the full final Tree/Graph in `\shape{...}{Tree}{...}` and use `state=dim` as "not yet present" and `state=active` as "now present". This works for tutorials with known-at-author-time executions but falls apart for:

- data-dependent shapes (user-input BST sequence),
- algorithms whose node count *shrinks* (contraction),
- any demo that should compose two phases with different shapes.

### Pattern C — additive-only Plane2D with accumulating dim

The Plane2D cookbook files (`convex_hull_andrew`, `h04_fft_butterfly`, `h06_li_chao`, `h09_simulated_annealing`) share one visible symptom: by the final frame the canvas is crowded with dimmed elements from earlier stages. Two of these files explicitly narrate around the noise ("the dimmed points are discarded"). This is the single strongest pedagogical argument for `remove_*` on Plane2D.

## Severity summary

| Severity | Count | Items                                                                                   |
|----------|:-----:|-----------------------------------------------------------------------------------------|
| HIGH     | 4     | Plane2D remove; Tree add/remove; Graph add_edge/remove_edge; universal rename (unwired) |
| MEDIUM   | 4     | clear; Plane2D move; Array/Grid/LL swap; HashMap remove                                 |
| LOW      | 3     | MetricPlot rewind; NumberLine dynamic ticks; Grid row/col insert                        |

**Dead-API alert:** `PrimitiveBase.set_label()` at `scriba/animation/primitives/base.py:228` is never called. The parse path for `\apply{...}{label=X}` at `scene.py:531-533` records the label onto `ShapeTargetState.label` but no reader consumes it. Fixing this is the single cheapest completeness win on the board — one edit in `emitter.py` next to the existing `set_value` dispatch.

**Framing for triage:** if Scriba targets competitive-programming algorithm explainers, the HIGH block is not a polish concern — it determines whether the tool can faithfully render deletion-heavy algorithms at all. Today, any algorithm whose *structural* behavior is deletion (BST delete, hull pop, edge contraction, splay eviction, MCMF residual saturation) has to lie to the viewer with `state=dim`. Four files in the cookbook already demonstrate the lie.
