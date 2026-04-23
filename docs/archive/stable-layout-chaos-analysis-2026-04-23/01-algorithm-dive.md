# 01 — Algorithm Dive: How `graph_layout_stable.py` Works

## Summary

`layout="stable"` uses **Simulated Annealing** (not Fruchterman-Reingold) with
200 iterations, geometric cooling (α=0.97, T₀=10), and a two-term objective:
sum of edge crossings across all frames plus a quadratic distance penalty for
edges outside [0.3, 0.6] in the unit square. Nodes start at **pure random
positions** (seeded, but random scatter). There is no directional bias, no
layer assignment, no repulsion between non-adjacent nodes, and no cycle
handling. The loop always runs exactly 200 fixed iterations — there is no
energy-threshold early exit.

Chaos emerges from five compounding causes: (1) random initialization with no
structural prior; (2) crossing minimization is per-frame-only, so cross-frame
edge pairs create no pressure; (3) the flat [0.3, 0.6] ideal-length band gives
no single target spacing; (4) 200 iterations is far too few for the O(T·E²)
objective; and (5) a post-SA greedy overlap resolver (`_resolve_overlaps`, 10
passes) moves nodes without rechecking the SA objective, potentially undoing
the best placements the annealer found. The algorithm is deterministic for a
fixed seed but produces visually unstructured graphs for any directed or
layered topology.

## Algorithm Family

This is **Simulated Annealing (SA)** over a custom combinatorial objective. It
is NOT Fruchterman-Reingold, spring-embedder, or any force-directed method.
There are no attractive/repulsive force vectors and no velocity integration.
The fallback that runs when guards fire (E1501/E1502) delegates to a separate
Fruchterman-Reingold implementation in `graph.py` (`fruchterman_reingold`, line
383 of that file). The stable layout itself is pure SA.

## Objective Function (exact formulas, lines 135-152)

```
O(pos) = sum_t [ crossing_count(E_t, pos) ]
       + lambda * sum_{(u,v) in union(E_t)} [ distance_penalty(pos_u, pos_v) ]
```

**Edge crossing penalty** (lines 97-116):
- For each frame `t`, count all pairs of non-adjacent edges in `E_t` that
  geometrically intersect.
- Uses exact cross-product segment intersection test (lines 71-94).
  Shared-endpoint pairs are explicitly skipped (line 110).
- Each crossing contributes +1 to the objective.

**Distance penalty** per edge (lines 119-132):
```
penalty(u, v) = max(0, 0.3 - d)^2  +  max(0, d - 0.6)^2
```
where `d = sqrt((x_u - x_v)^2 + (y_u - y_v)^2)` in the unit square [0,1]^2.
- Penalizes edges shorter than 0.3 (quadratic below) and longer than 0.6
  (quadratic above).
- Ideal edge length is anywhere in [0.3, 0.6] — a flat zero-penalty band, not
  a single target length.
- Distance penalty is computed over the **union** of all edges across all
  frames (line 145-149), not per-frame.

**Lambda weight** (line 151): default 0.3, clamped to [0.01, 10.0] (lines
34-35, 241).

## Initialization (lines 277-302)

**Cold start (no `initial_positions`):** Every node placed at
`(rng.random(), rng.random())` — independent uniform random draws from [0,1]^2
(line 302). **Pure random scatter**, no grid, no circular placement, no
topology-aware seeding.

**Warm start (`initial_positions` supplied):** SVG pixel coordinates are
denormalized back into unit-square coordinates via:
```
nx = (svg_x - pad) / (width - 2*pad)
ny = (svg_y - pad) / (height - 2*pad)
```
then clamped to [0,1] (lines 283-298). Nodes absent from `initial_positions`
still get cold-start random placement (line 300). This path used by `Graph`
mutation warm-start.

**RNG:** `random.Random(seed)` — seeded Python stdlib RNG (line 278). Default
seed = 42 (line 183). Seed must be a non-negative integer; negative/non-integer
raises `ValidationError` E1505 (lines 219-223).

## Simulated Annealing Loop (lines 304-343)

**Parameters (lines 305-309):**

| Constant | Value |
|---|---|
| `t0` (initial temperature) | 10.0 |
| `alpha` (cooling factor) | 0.97 |
| `num_iterations` | 200 |
| `step_size_initial` | 0.2 |

**Per-iteration steps:**
1. Pick random node via `rng.choice(nodes)` (line 316).
2. Compute displacement magnitude: `magnitude = (temperature / t0) * step_size_initial` (line 320).
   At iteration 0: `(10.0/10.0) * 0.2 = 0.2`; decays multiplicatively with temperature.
3. Pick uniformly random angle in [0, 2π] (line 321). Displacement is a random
   unit vector scaled by magnitude.
4. Clamp new position to [0,1]^2 (lines 324-325) — hard boundary, no
   reflection.
5. Recompute full objective `_objective(...)` (line 329) — **full recomputation
   every step, not incremental**.
6. Accept if `delta <= 0`. Accept worse if `rng.random() < exp(-delta / temperature)`
   (lines 332-341, standard Metropolis criterion).
7. Cool: `temperature *= alpha` (line 343).

**Temperature schedule:** Geometric decay. After 200 iterations:
`T_final = 10.0 * 0.97^200 ≈ 10.0 * 0.00228 ≈ 0.0228`

Step size collapses from 0.2 (20% canvas width) to ~0.000456 (0.046%) over the
run.

## Convergence Criteria (lines 345-358)

There is **no energy threshold** or early-exit test. The loop always runs
exactly 200 iterations regardless of objective value. The only "convergence"
signal is a post-hoc warning (E1500) emitted if `current_obj > 10 * initial_obj`.
Diagnostic only; positions still returned. No re-run or restart logic.

## Determinism

Fully deterministic for a fixed `(nodes, frame_edge_sets, seed, lambda_weight,
width, height, node_radius, initial_positions)` tuple. Seeded `random.Random`
instance. However:

- `rng.choice(nodes)` (line 316) depends on the **order** of `nodes`. Different
  caller order → different positions.
- Cache key (lines 155-177) uses `sorted(nodes)` and `sorted(edges)` per frame
  — order-independent — but the SA loop itself is NOT (calls `rng.choice(nodes)`
  with the unsorted caller-supplied list).
- Tie-breaking: none. When `delta == 0` (lines 332-333), new position always
  accepted — sideways moves that don't improve objective drift positions.

## Size Guards and Fallback

| Guard | Limit | Error Code |
|---|---|---|
| Node count | `_MAX_NODES = 20` (line 31) | E1501 |
| Frame count | `_MAX_FRAMES = 50` (line 32) | E1502 |

Both return `None` (lines 257, 275). Caller interprets as "use force layout
instead." Fallback not implemented here.

## Post-SA Overlap Resolution (lines 369-383)

After SA completes and positions denormalize to SVG pixels, a separate greedy
overlap resolver runs:
- Imports `_resolve_overlaps`, `_NODE_OVERLAP_GAP = 12`, `_PADDING = 20` from
  `graph.py`.
- Min node separation: `min_sep = 2 * node_radius + 12` pixels.
- `_resolve_overlaps` runs up to 10 passes over all O(N²) pairs, pushing
  overlapping nodes apart along the connecting line by `(deficit/2 + 0.5)`
  pixels each (graph.py lines 355-380).
- Clamped to `[_PADDING, width/height - _PADDING]` = `[20, width-20]` /
  `[20, height-20]`.

This post-pass can **undo SA's edge-crossing optimization** by moving nodes
without rechecking the objective.

## Big-O Complexity

Let N = nodes, E = edges (union), T = frames, I = 200 iterations.

- `_count_edge_crossings` per frame: O(E_t²).
- `_objective`: O(T · E_max² + E_union) per call.
- Full SA loop: O(I · (T · E_max² + E_union)) = O(200 · T · E_max²).
- Worst case N=20 complete graph (E=190): O(200 · 50 · 190²) ≈ **361 million
  operations** — pure Python, no numpy.
- Overlap resolution: O(passes · N²) = O(10 · 400) = negligible.

## Known Failure Modes — why "chaotic"

1. **No directional/hierarchical bias (root cause).** SA treats positions as
   equivalent. No concept of "source at top, sink at bottom," no layer
   assignment, no left-to-right flow. Directed graphs scatter randomly.

2. **Crossing minimization per-frame-only (lines 142-148).** Edge pairs that
   never co-appear in a frame contribute zero crossing penalty. Nodes connected
   by edges from different frames can be placed arbitrarily close or far.

3. **Flat zero-penalty band [0.3, 0.6] (lines 125-132).** Any distance in that
   band is equally acceptable. No single "ideal length" pulling connected
   nodes to consistent spacing.

4. **200 iterations severely insufficient (line 307).** With N=10, T=5, the SA
   budget is 200 node-moves (20/node avg). Geometric cooling means ~70% of
   useful exploration spent in first 50 iterations before T drops below 1.0.
   Last 125 iterations make microscopic moves.

5. **Full objective recompute each step (line 329)** consumes budget rapidly
   but no incremental evaluation possible — can't afford more iterations
   without refactor.

6. **`rng.choice(nodes)` uniform (line 316).** High-degree nodes that most
   affect objective not prioritized.

7. **No cycle detection.** Cycles treated identically to DAGs. 3-cycle nodes
   can stack if crossing penalty is zero.

8. **Post-pass `_resolve_overlaps` runs without objective re-check
   (lines 369-383).** Can move nodes to positions that increase edge crossings,
   silently degrading a good SA solution.

9. **Warm-start reuses stale SVG coords from different canvas size
   (lines 292-297).** Clamping to [0,1] handles OOB but does not rescale
   proportionally — graph on 800×600 warm-started on 400×300 compresses into
   one quadrant.

10. **No repulsion between non-adjacent nodes.** Unlike Fruchterman-Reingold,
    no force pushing non-connected nodes apart. Only penalty terms are edge
    crossings and edge lengths. Two unconnected nodes can overlap completely
    with zero penalty.
