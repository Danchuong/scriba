# 03 — Stable vs Hierarchical: Side-by-Side

## Summary

`stable` is a simulated-annealing optimizer: it minimizes edge crossings and
distance penalties across all frames jointly, but it is **topology-blind** — it
has no concept of edge direction, ranks, or hierarchy. Positions are
pseudo-random within a unit square, cooled over only 200 SA iterations with a
hard cap at 20 nodes / 50 frames. The annealing budget is too small to
guarantee a global optimum, so the result is often a locally-stuck
configuration that looks arbitrary.

`hierarchical` (Sugiyama) is fully deterministic: breaks cycles, assigns
longest-path ranks, runs 24 barycenter sweeps for crossing reduction, and
spreads nodes on a regular grid anchored by direction. Always produces a clean
top-down or left-right flow.

The dispatch in `graph.py` (lines 709–759) sends each layout to its own module
and post-expands the viewport only for hierarchical, whose layer-gap contract
can legally exceed the default canvas size.

## Side-by-side table

| Property | `stable` (simulated annealing) | `hierarchical` (Sugiyama) |
|---|---|---|
| **Algorithm family** | Metaheuristic / combinatorial optimization (SA) | Layered / topological (Sugiyama-style) |
| **Determinism** | Seed-deterministic *only if* the SA run is identical. Two equal seeds produce equal output, but convergence quality varies with graph topology. | Fully deterministic — same input always produces the same layer assignment, order, and coordinates. Seed only affects tie-breaking in `_barycenter_sort`. |
| **Edge-direction awareness** | None. Edges are treated as undirected pairs `(u, v)` in the objective function. Direction is invisible to the optimizer. | Core to the algorithm. Edges define the DAG for longest-path ranking; direction drives the entire layer structure. |
| **Cycle handling** | None. Cycles are silently accepted; the SA objective counts crossings regardless of direction, so back-edges cause no special treatment. | Explicit iterative DFS cycle-break (`_break_cycles`). Back-edges are reversed for layering, then logically restored in the caller's edge list. |
| **Crossing reduction** | Implicit — the objective penalizes edge crossings across all frames jointly, but 200 SA iterations is usually insufficient to reach a global minimum, especially for dense graphs. | Explicit barycenter heuristic — 12 forward + 12 backward sweeps (`_BARYCENTER_SWEEPS = 12`), matching dagre's default. Converges for N ≤ ~30 before the cap. |
| **Symmetry** | No symmetry enforcement. Positions are seeded randomly and evolved by local perturbation; symmetric structure in the graph is not preserved. | Implicit structural symmetry: nodes at the same rank are evenly spread across the secondary axis, so a balanced DAG produces a visually symmetric output. |
| **Hierarchy enforcement** | None. There is no notion of "level" or "rank"; sources, sinks, and intermediates can land anywhere in the unit square. | Strict. Every node gets `layer = max(predecessor_layers) + 1`. Sources always appear at layer 0. |
| **Compactness** | Attempts edge-length control via `_distance_penalty` (target: 0.3–0.6 in unit coords). In practice, nodes cluster or spread depending on SA convergence. | Fixed grid: layers are evenly spaced along the primary axis with `_MIN_LAYER_GAP = 140 px` minimum; nodes within a layer are evenly spread on the secondary axis. Regular but can be sparse for small graphs. |
| **Complexity** | O(N · T · E²) per SA iteration (crossing count is O(E²)); 200 iterations total → O(200 · N · T · E²). Hard caps: N ≤ 20, T ≤ 50. Falls back to Fruchterman–Reingold on overflow. | O(V + E) layering (Kahn's BFS) + O(sweeps · E) crossing reduction = O(V + sweeps · E). No node/frame caps; returns `None` only for invalid orientation. |
| **Viewport contract** | Outputs stay within `[pad, width−pad] × [pad, height−pad]`. A post-pass (`_resolve_overlaps`) clamps any remaining node collisions inside the canvas. | May legally exceed the caller's canvas. `graph.py` post-dispatch expands `self.width`/`self.height` to `max(existing, max_coord + pad)` (lines 752–757). Caller must accommodate overflow. |
| **Failure modes** | E1500 convergence warning (objective diverged); E1501/E1502/E1503 size-guard fallback; E1504 lambda clamp; E1505 bad seed. SA can get stuck in poor local optima — nodes look arbitrarily placed even with a valid seed. | E1505 bad seed (raises); E1506 empty node list (returns `{}`); invalid orientation returns `None`. No convergence failure mode; the algorithm terminates in fixed O(sweeps) time. |
| **Multi-frame stability** | Primary design goal. The objective is summed across *all* `frame_edge_sets` jointly so positions do not jump between frames. | Achieves stability by unioning all frame edges before layering. A node's rank reflects the union graph, not per-frame topology. |
| **Orientation support** | None — layout is always 2-D undirected in unit square. | `"TB"` (top-to-bottom) or `"LR"` (left-to-right) via `orientation` parameter. |

## What stable does NOT do that hierarchical does

**No topology awareness.** The SA objective sees edges only as pairs of
endpoints. It has no concept of "source" or "sink." A graph like `A→B→C→D` is
indistinguishable from a cycle `A↔B↔C↔D`. Hierarchical's longest-path ranking
assigns `A=0, B=1, C=2, D=3` and places them on four distinct horizontal bands.
Stable may place them in any arrangement that happens to minimize crossings —
often clustering them near each other in a corner.

**No guaranteed structure.** Hierarchical guarantees that every edge points in
the primary-axis direction (top-down or left-right) after cycle-breaking.
Stable gives no such guarantee; an edge from a "high" node to a "low" node is
just as valid as the reverse.

**Insufficient iteration budget.** 200 SA iterations is extremely conservative.
For a 10-node, 12-edge graph the crossing count alone is O(12²/2) = 72
candidate pairs per move, and the probability of escaping a bad local minimum
drops rapidly as temperature cools (α = 0.97 → after 200 steps, T ≈
10 × 0.97²⁰⁰ ≈ 0.002). This is the principal cause of "chaos": the optimizer
freezes in a poor configuration early and cannot escape it.

**No symmetry or regularity.** Hierarchical enforces a regular grid. Stable's
only regularizing forces are the distance penalty (edges between 0.3–0.6 unit
length) and crossing avoidance. Both are weak and can be satisfied by many
different configurations, none of which looks "orderly" to a human reader.

## What hierarchical does NOT do that stable does

**Multi-frame joint optimization.** Stable's entire purpose is to find a single
position set that is acceptable for *all* frames simultaneously. Hierarchical
unions edges before layering but does not weight frames differently; a node
that is isolated in 9 of 10 frames but connected in 1 will still be placed
according to the union graph's rank.

**Graceful handling of undirected/symmetric graphs.** For graphs without
meaningful direction (e.g., an undirected mesh), hierarchical's rank
assignment is arbitrary — the node that happens to appear first in the sorted
edge list becomes a source. Stable makes no directional assumptions and treats
such graphs uniformly.

**Overlap resolution.** Stable explicitly calls `_resolve_overlaps` after
annealing. Hierarchical relies on even spacing to avoid overlaps but has no
post-pass; nodes at the same layer in a narrow viewport can still overlap if
`node_radius` is large relative to `secondary / (n−1)`.

**Compact small-graph layouts.** Hierarchical's `_MIN_LAYER_GAP = 140 px` means
a 2-layer graph in a 300 px viewport places layers at y=36 and y=264 — nearly
the full height — regardless of how few nodes there are. Stable will cluster a
2-node graph near the center with a single short edge.

## Dispatch path (graph.py lines 709–759)

- `layout == "stable"` → `compute_stable_layout`, receives single-frame edge
  list, falls through to Fruchterman–Reingold on `None` return (size guard).
- `layout == "hierarchical"` → `compute_hierarchical_layout`, receives
  single-frame edge list, post-expands `self.width`/`self.height` if layered
  coords exceed default canvas, falls through on `None` return (bad
  orientation).
- Default → `fruchterman_reingold` directly.

Neither `stable` nor `hierarchical` ever shares its fallback with the other; a
size-guarded stable graph does not attempt hierarchical.
