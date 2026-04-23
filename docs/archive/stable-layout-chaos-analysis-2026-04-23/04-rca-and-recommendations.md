# 04 — RCA and Recommendations

## Summary

The "chaotic stable layout" is a direct consequence of six compounding
algorithmic choices in `graph_layout_stable.py`. The SA objective function has
no concept of edge direction (RC-1), so for a DAG it treats A→B and B→A as
equivalent. The iteration budget (200 steps, alpha=0.97) is too small to
escape the random initialization basin (RC-2, RC-3). The distance penalty
actively fights long-chain topologies (RC-5). And there is no global repulsion
to spread unconnected nodes (RC-6).

The layout is deterministic for identical inputs in identical node-list order,
but silently non-deterministic when node ordering varies — a common real-world
condition.

The highest-leverage fix is Option A: add `layout="auto"` that dispatches to
`compute_hierarchical_layout` when the graph is a DAG (detectable by calling
`_break_cycles` and checking whether the reversed-edge set is empty — code
that already exists). The hierarchical layout is fully deterministic,
topology-respecting, and has 30 passing tests today.

The recommended migration is a three-step sequence: (1) add a `UserWarning`
for `directed=True` + `layout="stable"` immediately, (2) ship `layout="auto"`
as an opt-in in the next minor release, (3) flip the default from `"force"` to
`"auto"` in the release after, with golden re-pins for directed-graph tests.
The `layout="stable"` path is never removed — it retains its valid use case of
multi-frame animation stability for small undirected graphs.

## 1. Root Causes — Why Stable Layout Inherently Looks Chaotic

### RC-1: The objective function is topology-blind

The SA objective (`_objective`) minimizes two things: edge crossing count and
edge length deviation. It has no knowledge of edge direction, topological
depth (layer), or source/sink structure. For a DAG with a clear causal flow
(A→B→C→D), the optimizer is equally happy placing D above A as below it. The
result is that what the user's eye reads as "flow" is randomized — any
left-to-right or top-to-bottom pattern they expect from a directed graph is
noise.

### RC-2: Simulated annealing with 200 iterations is severely under-budgeted

Schedule: `t0=10.0`, `alpha=0.97`, 200 iterations. After 200 steps temperature
is `10.0 × 0.97^200 ≈ 0.24`. Step size at final iteration is
`(0.24/10.0) × 0.2 ≈ 0.005` — less than one half-percent of the canvas. Early
moves are large and exploratory, but only 200 total moves across all nodes.
For N=6 nodes that is ~33 moves per node on average. Search terminates long
before the landscape is adequately explored.

### RC-3: Local minima sensitivity from random initialization

Initial positions drawn uniformly at random from `[0,1]²` (lines 302–303). SA
with a short schedule will almost always stay close to the basin of that
random initialization. Different seeds produce qualitatively different layouts
for the same graph, and none respects the graph's structure.

### RC-4: The objective counts crossings equally regardless of graph density

`_count_edge_crossings` is O(E²) and called once per full objective evaluation,
which itself is called on every accepted or rejected step. For E=10 this is
45 comparisons per step, 200 steps × 45 = 9,000 comparisons total — barely
enough to move a 6-node graph. More importantly: a complete graph has so many
crossings that minimizing them provides no structural signal; all
configurations look equally bad.

### RC-5: The distance penalty works against topology

The penalty penalizes edges shorter than 0.3 or longer than 0.6 (unit square).
For a DAG with long chains, the "correct" hierarchical layout requires edges
of varying lengths. The penalty actively pushes all edges toward the same
length band, producing a circular or blob arrangement regardless of structure.

### RC-6: No repulsion between non-adjacent nodes

Force-directed layouts (like the FR fallback) include a global repulsion term
spreading all nodes apart. The SA objective has no such term. Nodes that start
close together can remain clustered because neither crossing count nor
distance penalty notices — no edges between them, both terms zero.

### RC-7: Post-pass overlap resolution can undo SA progress

After SA completes, `_resolve_overlaps` runs (lines 377–383). If SA placed
nodes sensibly but two ended up slightly too close, the overlap resolver can
push one arbitrarily — displacement direction not constrained by topology, so
a node can jump across edges it was not previously crossing.

## 2. Is It Actually Deterministic?

**Yes — conditionally.** `rng = random.Random(seed)` on line 278 creates an
isolated RNG. With same `seed`, `nodes` list, and `frame_edge_sets`, output is
byte-for-byte identical across runs and Python versions (Mersenne Twister,
documented stable).

However, determinism has three practical failure modes:

1. **Node list ordering matters.** Cache key sorts nodes (`sorted(nodes)` in
   `compute_cache_key`), but SA loop uses the live `nodes` list order for
   `rng.choice`. Different caller order → different layout.
2. **Convergence warning (E1500) is not surfaced by default**
   (`severity="hidden"`), so a failed-to-converge layout looks identical to
   one that did.
3. **Warm-start `initial_positions`** bypass random initialization. Seed still
   governs subsequent SA moves, but starting basin now determined by previous
   frame's positions. Correct behavior, but means "stable" in "stable layout"
   refers to cross-frame stability, not determinism of initial solve.

**Bottom line:** given identical inputs in identical order, output is
deterministic. In practice users re-order node lists, silently changing result.

## 3. User-Facing Symptoms and When They Manifest

| Scenario | Symptom | Why |
|---|---|---|
| DAG with obvious flow (BFS tree, pipeline) | Nodes arranged in blob; source and sink indistinguishable | RC-1, RC-3 |
| Small sparse graph (N=3–5, E=2–4) | Layout varies widely between seeds; often asymmetric | RC-2, RC-3 |
| Dense graph (E close to N²) | All configs equally crossed; SA no progress | RC-4 |
| Long chain (A→B→C→D→E) | Chain wraps or doubles back on itself | RC-5 |
| Isolated nodes | Isolated nodes cluster in a corner | RC-6 |
| Re-render after adding node | New node appears in visually unrelated position | RC-7 + warm-start basin shift |
| N > 20 | Silent fallback to FR (E1501 "hidden") | Size guard, RC-1 still applies to FR |

The symptom is most severe for the canonical educational use-case: a DAG
representing an algorithm (BFS, topological sort, shortest path). That is the
primary use-case of the scriba Graph primitive, which makes RC-1 the critical
root cause.

## 4. Recommendations (Ranked)

### Option A — Add `layout="auto"` that selects hierarchical for DAGs (RECOMMENDED)

When user does not specify a layout, detect whether graph is a DAG (the
`_break_cycles` function already exists in `graph_layout_hierarchical.py` and
returns a `reversed_set`; if `reversed_set` is empty, graph is a DAG) and
dispatch to `compute_hierarchical_layout`. For cyclic graphs, fall back to the
existing FR default.

**Pros:**
- Zero breaking change: existing `layout="stable"` and `layout="force"`
  continue to work unchanged. Users who wrote nothing get better default.
- DAG detection is O(V+E) and already implemented — zero new algorithmic code.
- Hierarchical is fully deterministic and produces the structure users expect
  for educational directed-graph animations.

**Cons:**
- Default becomes `"auto"` in new editorials; a user who relied on the
  (undocumented) blob shape of the old default will see a different layout.
- A near-DAG with one back-edge still gets FR. Users can override with
  `layout="hierarchical"` which handles cycles via back-edge reversal.

**Implementation sketch (graph.py ~line 632):**
```python
raw_layout = str(params.get("layout", "auto"))
self.layout = raw_layout
# ... in the position dispatch block:
if self.layout in ("hierarchical", "auto"):
    _use_hier = (self.layout == "hierarchical")
    if self.layout == "auto":
        from scriba.animation.primitives.graph_layout_hierarchical import _break_cycles
        _dag_edges, _rev = _break_cycles(
            [str(n) for n in self.nodes],
            [(str(u), str(v)) for u, v, _w in self.edges],
        )
        _use_hier = (len(_rev) == 0)
    if _use_hier:
        # ... existing hierarchical dispatch
```

**Risk:** LOW. DAG detection path already tested through
`graph_layout_hierarchical.py`'s 30 tests.

### Option B — Fix the stable algorithm itself (MEDIUM EFFORT, MEDIUM GAIN)

The SA objective is the right shape for multi-frame stability, but needs:

1. **Add direction-alignment term** for directed graphs: penalize edges where
   `y_target < y_source` (TB). Weight so does not overpower crossing
   objective.
2. **Increase iteration budget** from 200 to at least 1000–2000, or switch to
   restart strategy (run 5 independent SA chains, pick best).
3. **Add global repulsion term** between all node pairs (not just connected
   pairs) — the O(N²) term FR already uses and what prevents clustering.
4. **Loosen distance penalty** for directed graphs to allow long chains.

**Pros:** Stable layout retains its unique property (multi-frame position
stability across animation mutations).

**Cons:** Larger iteration budgets make N ≤ 20 guard more important, not less.
Size cap already means most real educational graphs hit FR fallback. Fixing
the algorithm helps only <20-node case. Diminishing returns vs Option A.

**Risk:** MEDIUM. Would require re-pinning SA golden test values.

### Option C — Document the limitation and direct DAG users to hierarchical (LOW EFFORT, LOW GAIN)

Add docstring note and runtime `UserWarning` when `layout="stable"` used with
directed graph:

```python
if self.layout == "stable" and self.directed:
    warnings.warn(
        "layout='stable' does not respect edge direction; "
        "consider layout='hierarchical' for DAGs.",
        UserWarning, stacklevel=2,
    )
```

**Pros:** Zero behavior change. Surfaces issue to editorials immediately.

**Cons:** Users who don't read the warning (or suppress it) get no
improvement. Does not fix the implicit-default case.

### Option D — Rename default to `"auto"`, implement smart dispatch (SAME AS A BUT EXPLICIT)

Same as Option A but makes default literal in the API
(`params.get("layout", "auto")` instead of `"force"`). More honest about
engine's intent.

Current code at line 632 defaults to `"force"`, but in-code comment at line
706–708 says `layout="stable"` is the documented default. **Existing
inconsistency**: code default is `"force"` (Fruchterman-Reingold), not
`"stable"`, even though error messages (line 607) tell users to "use
layout=stable for larger graphs." `layout="auto"` resolves this cleanly.

## 5. Proposed Migration Path and Impact Radius

### Recommended sequence

**Step 1 (no-breaking):** Add `UserWarning` when `layout="stable"` used with
`directed=True` (Option C). Ships in patch. Zero golden changes.

**Step 2 (additive):** Implement `layout="auto"` as explicit new value. Auto
selects hierarchical for DAGs, force for cyclic. Do not yet change default.
Update docs to recommend `layout="auto"` for new editorials. Ships in minor.
Zero existing test changes.

**Step 3 (default change):** Change `params.get("layout", "force")` to
`params.get("layout", "auto")`. Single breaking change. Impact radius:

- Any existing editorial/test using `directed=True` with no explicit `layout`
  now produces hierarchical instead of FR. Visually different but
  structurally better.
- Any editorial using `directed=False` with no explicit `layout` unaffected
  (`auto` falls through to `force` for cyclic/undirected).
- Golden SVG test files for directed-graph examples need re-pinning.
- `layout="stable"` path unchanged — no existing `layout="stable"` editorials
  break.

**Affected symbols (blast radius — run `gitnexus_impact` before touching):**
- `Graph.__init__` (dispatcher, line 632)
- `compute_cache_key` in `graph_layout_stable.py`
- Any integration tests asserting SVG geometry for directed graphs without
  explicit `layout` param

**Step 3 should carry a minor-version bump** and CHANGELOG entry linking back
to this analysis.

## Relevant files

- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/graph_layout_stable.py`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/graph_layout_hierarchical.py`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/graph.py` (dispatcher at lines 629–769)
