# 00 — Synthesis

## Question

"Tại sao layout stable lại trông có vẻ hỗn loạn chẳng có quy tắc nào vậy?"
(Why does `layout="stable"` look chaotic with no apparent rules?)

## One-line answer

Because `graph_layout_stable.py` is a topology-blind Simulated Annealing
optimizer over edge-crossings + edge-length — it has no concept of
source/sink/layer/direction, starts from pure random scatter, and burns its
200-iteration budget before exploring the solution space.

## Findings (cross-doc summary)

### 1 — Algorithmic truth (from 01-algorithm-dive.md)

- **Family:** Simulated Annealing, NOT Fruchterman-Reingold. No force vectors.
- **Init:** pure random in [0,1]² — no topology prior.
- **Objective:** `crossings(per-frame) + λ · distance_penalty(union)` where
  distance penalty has a flat zero band for edge-length ∈ [0.3, 0.6].
- **Budget:** 200 fixed iterations, `T₀=10`, `α=0.97`. By iteration 75 T<1;
  last 125 iterations microscopic moves.
- **No edge direction term. No global repulsion. No layer constraint.**
- **Post-pass `_resolve_overlaps`** can undo SA progress.
- **Size guards:** N≤20, T≤50 — silent fallback to FR.

### 2 — Empirical chaos (from 02-empirical-evidence.md)

Across 4 canonical directed topologies × 3 seeds:
- **Parent-above-child violation: 47% avg, 83% peak** (binary tree seed 17:
  5 of 6 edges place parent below child).
- Node positions shift **100–355 px** across seeds on 400-wide canvas —
  effectively full re-randomization.
- 2 runs emitted **E1500** (final obj > 10× initial) — 200 iterations too
  short even for 5–7 node graphs.
- Hierarchical: **0 violations across all 4 graphs**, fully deterministic.

### 3 — Comparative gap (from 03-stable-vs-hierarchical.md)

What stable does NOT do that hierarchical does:
1. No topology awareness — treats A→B identical to B→A.
2. No guaranteed structure — any edge direction valid.
3. Insufficient iteration budget for graph size.
4. No symmetry or regularity — weak regularizing forces.

What hierarchical does NOT do that stable does:
1. Multi-frame joint optimization (stable's core value).
2. Graceful undirected/symmetric handling.
3. Explicit overlap resolution post-pass.
4. Compact small-graph layouts (hierarchical uses full 140 px min gap).

### 4 — RCA + fix (from 04-rca-and-recommendations.md)

**7 compounding root causes** (RC-1 topology-blind, RC-2 under-budgeted SA,
RC-3 random-init sensitivity, RC-4 dense-graph crossing noise, RC-5
distance-penalty anti-topology, RC-6 no global repulsion, RC-7 overlap-pass
undoes progress).

**Determinism:** conditional — same `(nodes, edges, seed)` in same order →
identical output. But `rng.choice(nodes)` uses caller's list order, so
reordering silently changes result.

**Recommended migration (3 steps):**

1. **Patch:** emit `UserWarning` when `layout="stable"` + `directed=True`.
2. **Minor:** add `layout="auto"` that dispatches to hierarchical for DAGs
   (detect via `_break_cycles(...)[1]` empty), FR for cyclic.
3. **Minor:** flip default from `"force"` to `"auto"`. Re-pin directed-graph
   goldens. `layout="stable"` path preserved — retains multi-frame stability
   use-case.

**Blast radius:** `Graph.__init__` dispatcher line 632;
`graph_layout_stable.compute_cache_key`; integration tests asserting SVG
geometry for directed graphs with no explicit `layout`. Run `gitnexus_impact`
before editing.

## Bottom line

User's perception is correct. Stable-SA is not a bug — it is a
multi-frame-stability optimizer that was never designed for hierarchy. Three
options exist:

- **fastest relief:** switch current `maxflow.tex` and similar DAG examples to
  `layout="hierarchical"` explicitly;
- **best default experience:** implement `layout="auto"` (Option A);
- **keep API clean:** flip default in next minor, warn in current patch.

## Files in this archive

| # | File |
|---|------|
| 00 | `00-synthesis.md` (this file) |
| 01 | `01-algorithm-dive.md` |
| 02 | `02-empirical-evidence.md` |
| 03 | `03-stable-vs-hierarchical.md` |
| 04 | `04-rca-and-recommendations.md` |
