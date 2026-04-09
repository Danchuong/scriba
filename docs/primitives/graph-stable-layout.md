# Primitive Spec: `Graph layout="stable"` Mode

> Status: **draft — Pivot #2 extension**. Extends the EXISTING `Graph` primitive defined
> in base spec `04-environments-spec.md` §5 with a new value for the `layout` parameter.
> This is NOT a new primitive type. The base spec `Graph` primitive already handles
> `layout="force"|"circular"|"bipartite"|"hierarchical"`. This spec adds `layout="stable"`.
>
> Error codes in range **E1500–E1509**.

---

## 1. Purpose

When a `Graph` primitive is used in an `\begin{animation}` and edges are added, removed,
or reversed across frames (as in a min-cost max-flow residual graph), the standard
`layout="force"` recomputes node positions at each frame independently. This causes nodes
to drift or jump between frames, making it impossible for readers to follow which node is
which. `layout="stable"` solves this by computing a single set of node positions valid
across ALL frames before emitting any SVG.

It unlocks:

- **HARD-TO-DISPLAY #5** (Min-Cost Max-Flow on a dense graph): the residual graph after
  each augmenting path, where edges gain/lose/reverse capacity. At N ≤ 20 editorial scale,
  stable positions allow the reader to track flow changes without losing orientation.
- Tarjan SCC and other DFS-based graph algorithms where the DFS tree emerges edge by edge.
- Any animation where the graph topology changes across frames.

`layout="stable"` replaces the runtime ELK.js proposal from research A3 with a pure
Python, compile-time simulated annealing optimizer.

---

## 2. Extended shape declaration

```latex
\shape{g}{Graph}{
  nodes=["s", "a", "b", "c", "t"],
  edges=[("s","a",{cap=3}), ("s","b",{cap=5}), ("a","c",{cap=2}),
         ("b","c",{cap=3}), ("c","t",{cap=4}), ("a","t",{cap=1})],
  directed=true,
  layout="stable",
  layout_seed=42,
  layout_lambda=0.3
}
```

### 2.1 New parameters (stable-layout-specific)

| Parameter        | Type          | Default | Description                                                         |
|------------------|---------------|---------|---------------------------------------------------------------------|
| `layout`         | string enum   | (varies)| Set to `"stable"` to activate this spec. Other values documented in base spec §5. |
| `layout_seed`    | integer       | 42      | Random seed for the simulated annealing optimizer. Deterministic output per seed. |
| `layout_lambda`  | float         | 0.3     | Weighting factor λ for the edge-length penalty term in the SA objective. See §4. |

### 2.2 Unchanged parameters

All parameters from the base `Graph` primitive apply unchanged: `nodes`, `edges`,
`directed`, `node_labels`, `edge_labels`, `node_radius`, `edge_width`, `edge_color`,
`width`, `height`. See base spec §5 for full list.

---

## 3. Why stable layout matters

Consider a 6-node MCMF graph (Problem #5) animating 3 augmenting path iterations:

- Frame 1: source → a → c → sink (capacity 2 flows)
- Frame 2: residual edges reverse; source → b → c → sink
- Frame 3: final state, all edges have residual capacity labels

Under `layout="force"`, node "c" might be placed at coordinates (120, 80) in frame 1 and
(95, 140) in frame 2, because the force-directed algorithm sees a different edge set. The
reader loses track of "c" between frames.

Under `layout="stable"`, "c" is at the same coordinates in all frames. The reader can
follow the capacity changes without re-locating nodes.

The stability guarantee: node positions `(x_i, y_i)` are IDENTICAL across all frames of
the animation. Only edge states (capacity, highlight, direction) change between frames.

---

## 4. Algorithm: joint simulated annealing

### 4.1 Input

The optimizer receives:

- Node set: `V = {v_0, ..., v_{N-1}}`, N nodes.
- Frame edge sets: `E_0, E_1, ..., E_T` where `E_t` is the set of edges present in frame t.
  These are derived from scene delta application: the base spec §6.1 `SceneState` is
  materialized for each frame during the scene materialization phase, and the edge sets are
  extracted before SVG emission.
- Parameters: `layout_seed`, `layout_lambda`.

### 4.2 Decision variables

Node positions `{(x_i, y_i) : i = 0..N-1}` in a normalized coordinate space `[0, 1] × [0, 1]`.
All frames share the same positions — that is the optimization target.

### 4.3 Objective function

```
O(positions) = sum_t [ edge_crossings(E_t, positions) ]
             + λ * sum_{(u,v) in union_edges} distance_penalty(u, v, positions)
```

Where:

**`edge_crossings(E_t, positions)`**: count of pairs of edges in `E_t` whose line segments
cross in the current layout. Computed in O(|E_t|^2) using the standard segment-intersection
check. For editorial-scale N ≤ 20, |E| ≤ N*(N-1)/2 ≤ 190; |E|^2 ≤ 36100; cost is fast.

**`distance_penalty(u, v, positions)`**: penalizes edges that are too short or too long:

```python
def distance_penalty(u, v, positions, target_dist=0.3):
    d = euclidean(positions[u], positions[v])
    return max(0, target_dist - d) ** 2 + max(0, d - 2 * target_dist) ** 2
```

`target_dist = 0.3` in the `[0,1]^2` normalized space (approximately 30% of the viewport
diagonal). This prevents nodes from collapsing to the same point or spreading to the
viewport corners.

**`union_edges`**: the union of all edges seen in any frame.

**λ default = 0.3**: biases the optimizer slightly toward readable edge lengths without
dominating the crossing-minimization goal. Configurable via `layout_lambda` in `[0.01, 10]`;
outside this range is **E1504** (lambda-out-of-range, warning; clamped to range).

### 4.4 Simulated annealing schedule

```
initial_temperature T0 = 10.0
cooling_rate α         = 0.97
num_iterations         = 200
step_size_initial      = 0.2   (in normalized [0,1]^2 space)
```

Per iteration:
1. Pick a random node i (uniform).
2. Propose new position by adding a random displacement of magnitude `T / T0 * step_size_initial`.
3. Compute `ΔO = O(new_positions) - O(old_positions)`.
4. Accept with probability `min(1, exp(-ΔO / T))`.
5. Decrease temperature: `T = T * α`.

After 200 iterations, temperature is `T0 * 0.97^200 ≈ 0.23` (well-cooled).

**Determinism**: the optimizer uses a seeded pseudorandom number generator initialized to
`layout_seed`. With identical `layout_seed`, identical nodes, and identical per-frame edge
sequences (not just union), the output is byte-identical across runs. This preserves the
content-hash cache in `tenant-backend` (see `01-architecture.md` §Versioning). SA
convergence is seeded and fully reproducible.

**Implementation**: pure Python in `scriba/animation/primitives/graph_layout_stable.py`.
No external dependencies (no scipy, no networkx). Uses Python's `random.Random(seed)` for
the seeded PRNG.

### 4.5 Position denormalization

After SA converges, normalized positions `[0,1]^2` are mapped to SVG viewport coordinates:

```
svg_x_i = pad + x_i * (width - 2 * pad)
svg_y_i = pad + y_i * (height - 2 * pad)
pad = node_radius + 8  (default: 24 px)
```

These SVG positions are then stored in the node dictionary for all frames. The SVG emitter
uses them as-is, identical for every frame.

### 4.6 Convergence check

After SA completes, if `O(final_positions) > 10 * O(random_baseline)` (where
`random_baseline` is the objective value of the initial random layout), the optimizer is
considered not converged and **E1500** (stable-layout-infeasible) is emitted as a warning.
Rendering continues with the best positions found.

---

## 5. Performance bounds and fallback

| Condition             | Code  | Severity | Behavior                                                      |
|-----------------------|-------|----------|---------------------------------------------------------------|
| N > 20 nodes          | E1501 | Warning  | Fall back to `layout="force"`. **E1503** (fallback-to-force) also emitted. |
| T > 50 frames         | E1502 | Warning  | Fall back to `layout="force"`. **E1503** also emitted.        |
| SA not converged      | E1500 | Warning  | Use best found positions; render proceeds.                    |

> **Audit fix (finding 1.10):** E1501 and E1502 were classified as "Error" but the fallback
> behavior (silent substitution of `layout="force"` + render continues) is inconsistent with
> a hard error that aborts rendering. Reclassified to **Warning** to match actual behavior.

**Fallback behavior**: when E1501 or E1502 triggers, the renderer silently substitutes
`layout="force"` and emits E1503 (warning) so the author knows layout stability was not
achieved.

### 5.1 Observed timing

Measured on a 2023 Apple M2 laptop running CPython 3.11:

| N nodes | Frames | SA iterations | Compile-time cost |
|---------|--------|---------------|-------------------|
| 6       | 4      | 200           | ~0.04 s           |
| 10      | 10     | 200           | ~0.12 s           |
| 15      | 30     | 200           | ~0.50 s           |
| 20      | 50     | 200           | ~1.80 s           |

These are within the Pipeline's per-shape timeout (5 seconds for `\compute`; the SA
optimizer runs in the primitive render phase, not in Starlark). Caching (see §5.2) makes
subsequent renders instantaneous.

### 5.2 Caching

The stable layout optimizer result (final node positions) is cached using a content hash.

> **Audit fix C4 (finding 6.1, decision lock #5):** The previous cache key used
> `sorted_union_edges`, which is identical for two scene sequences that share the same
> edge union but have different per-frame edge distributions. Because the SA objective
> is `sum_t edge_crossings(E_t, ...)`, the per-frame edge **sequence** matters. Two such
> scenes would collide under the old key and produce wrong (swapped) positions for one of
> them. The corrected key hashes the **ordered list** of per-frame edge sets.

```python
import hashlib, json

cache_key = hashlib.sha256(
    json.dumps({
        "nodes": sorted(nodes_with_attrs),
        "frames": [sorted(frame.edges) for frame in scene.frames],
        "layout_lambda": 0.3,
        "layout_seed": 42,
        "version": 1
    }, sort_keys=True).encode()
).hexdigest()
```

Where `nodes_with_attrs` is a list of `(node_id, attr_dict)` pairs sorted by node id,
`scene.frames` is the ordered sequence of `SceneState` frames (NOT deduplicated),
and `frame.edges` is the set of edge tuples present in that frame.

The `"version": 1` field ensures that a future change to the SA algorithm or objective
function can invalidate all cached keys by bumping to `2`.

The cache is stored alongside the scene artifact in the `tenant-backend` content-hash
cache. On a cache hit, the optimizer is skipped entirely. This matches the determinism
guarantee: same inputs → same cache key → same positions.

---

## 6. Integration with scene frame rendering

The stable layout positions are computed ONCE during scene materialization (base spec §6.1)
before any SVG is emitted. The flow is:

1. Parser produces `SceneIR`.
2. Scene materializer applies delta-based commands (base spec §6.1) to produce a
   `SceneState` for each frame. Edge sets `E_0..E_T` are extracted from each frame's
   `SceneState`.
3. If `layout="stable"` is detected, `graph_layout_stable.compute(nodes, edge_sets,
   seed, lambda)` is called. Result: dict `{node_id: (svg_x, svg_y)}`.
4. The positions dict is injected into the Graph primitive's internal node registry.
5. SVG emitter for each frame uses positions from the registry (not recomputed per frame).

Steps 1–5 are otherwise transparent to the rest of the pipeline. The SVG emitter for
`Graph` primitive does not need to know whether it is using force-layout or stable-layout
positions; it just reads from the node registry.

---

## 7. Node enter/exit animations

Because positions are FIXED across frames, nodes that appear or disappear between frames
(edge addition/removal may imply isolated-node visibility changes) cannot use position
morphs. Instead:

- **Node entry** (a node becomes connected for the first time): CSS class
  `scriba-graph-node-enter` added to the node's `<g>`. This triggers the same opacity-fade
  keyframe used for standard `Graph` node entry in the base spec.
- **Node exit** (a node becomes isolated in a frame): CSS class
  `scriba-graph-node-exit` added. Opacity fades to 0.35 (dim), not removed from the DOM.
- **Edge entry** (an edge is added in a frame): `scriba-graph-edge-enter` fade-in, as in
  the base spec.
- **Edge exit**: `scriba-graph-edge-exit`, opacity fades to 0 (the edge is no longer in
  `E_t` for this frame, but its `<line>` element is still emitted with `display:none` or
  `opacity:0` so the DOM structure remains stable across frames).

All transitions are CSS-only, respecting `prefers-reduced-motion`.

---

## 8. HTML output contract

The HTML output is identical to the base `Graph` primitive (base spec §8). No new elements
or attributes are added. The difference is purely in the computed node position values in
`cx`/`cy` attributes.

```html
<!-- Same structure as base Graph primitive -->
<svg class="scriba-graph"
     data-layout="stable"
     viewBox="0 0 {W} {H}"
     xmlns="http://www.w3.org/2000/svg"
     role="img">
  <g class="scriba-graph-edges">
    <g data-target="g.edge[(s,a)]"
       class="scriba-graph-edge scriba-state-idle">
      <line x1="{stable_x_s}" y1="{stable_y_s}"
            x2="{stable_x_a}" y2="{stable_y_a}"
            stroke="currentColor" stroke-width="2"/>
      <!-- arrowhead marker if directed=true -->
      <!-- edge label if present -->
    </g>
    <!-- ... -->
  </g>
  <g class="scriba-graph-nodes">
    <g data-target="g.node[s]"
       class="scriba-graph-node scriba-state-idle">
      <circle cx="{stable_x_s}" cy="{stable_y_s}" r="{node_radius}"/>
      <text x="{stable_x_s}" y="{stable_y_s}"
            text-anchor="middle" dominant-baseline="central">s</text>
    </g>
    <!-- ... -->
  </g>
</svg>
```

The `data-layout="stable"` attribute on the root `<svg>` signals to downstream consumers
(CSS, E2E tests) that stable layout was used.

---

## 9. Interaction with `Matrix` primitive

For HARD-TO-DISPLAY #5 at editorial scale, the recommended pattern is:

1. Use `Graph layout=stable` for the N=6 toy flow network showing the augmenting path
   sequence with stable node positions.
2. Use `Matrix` (or `Heatmap`) for the N=200 final assignment heatmap, embedded via
   `figure-embed` if N·M > 10000.

Cross-reference `matrix.md` §1 for the full rationale.

Example pairing:

```latex
\begin{animation}[id=mcmf-example]
\shape{flow}{Graph}{
  nodes=["s","a","b","c","d","t"],
  edges=[...],
  directed=true,
  layout="stable",
  layout_seed=42
}
\shape{cap_matrix}{Matrix}{
  rows=6, cols=6,
  data=${initial_caps},
  colorscale="rdbu",
  vmin=-5, vmax=5,
  col_labels=["s","a","b","c","d","t"],
  row_labels=["s","a","b","c","d","t"]
}

\step
\narrate{Initial capacity matrix and flow network.}

\step
\apply{flow.edge[(s,a)]}{label="2/3"}
\apply{cap_matrix.cell[0][1]}{value=1}   % s→a residual capacity decreases
\narrate{Augment path s→a→c→t with flow 2.}
\end{animation}
```

---

## 10. Error code catalog (E1500–E1509)

| Code  | Severity | Condition                                              | Hint                                                         |
|-------|----------|--------------------------------------------------------|--------------------------------------------------------------|
| E1500 | Warning  | SA optimizer did not converge (objective still high)   | Try a different `layout_seed` or increase `layout_lambda`.   |
| E1501 | Warning  | N > 20 nodes with `layout="stable"`; fell back to force | Use `layout="force"` for large graphs; stable is N ≤ 20 only.|
| E1502 | Warning  | Frame count > 50 with `layout="stable"`; fell back to force | Use `layout="force"`; stable layout is T ≤ 50 frames only.|
| E1503 | Warning  | Fell back from `layout="stable"` to `layout="force"`   | Node positions may jump across frames.                       |
| E1504 | Warning  | `layout_lambda` out of range `[0.01, 10]`              | Clamped to range; prefer values around 0.3.                  |
| E1505 | Error    | `layout_seed` is not a non-negative integer            | Must be an integer ≥ 0.                                      |

Codes E1506–E1509 are reserved.

---

## 11. Acceptance tests

### 11.1 MCMF N=6 with 3 augmenting paths — stable positions (HARD-TO-DISPLAY #5)

```latex
\begin{animation}[id=mcmf-stable]
\compute{
  nodes = ["s", "a", "b", "c", "d", "t"]
  # Initial capacities
  edges_0 = [("s","a",3),("s","b",5),("a","c",2),("a","d",1),
             ("b","d",3),("c","t",4),("d","t",3)]
}
\shape{g}{Graph}{
  nodes=${nodes},
  edges=${edges_0},
  directed=true,
  layout="stable",
  layout_seed=42
}

\step
\highlight{g.edge[(s,a)]}
\highlight{g.edge[(a,c)]}
\highlight{g.edge[(c,t)]}
\narrate{Frame 1: augmenting path s→a→c→t, flow = 2.}

\step
% Edge (s,a) residual changes; reverse edge (a,s) appears
\apply{g.edge[(s,a)]}{label="1/3"}
\apply{g}{add_edge=("a","s",{label="2",style="dashed"})}
\recolor{g.edge[(a,s)]}{state=dim}
\highlight{g.edge[(s,b)]}
\highlight{g.edge[(b,d)]}
\highlight{g.edge[(d,t)]}
\narrate{Frame 2: augmenting path s→b→d→t, flow = 3. Residual edges visible.}

\step
\recolor{g.all}{state=idle}
\highlight{g.edge[(s,a)]}
\highlight{g.edge[(a,d)]}
\highlight{g.edge[(d,t)]}
\narrate{Frame 3: augmenting path s→a→d→t, flow = 1. Stable positions — nodes did not move.}

\step
\recolor{g.all}{state=done}
\narrate{All 3 augmenting paths found. Max flow = 6.}
\end{animation}
```

Expected:
- 4 frames.
- Node positions in frames 1–4 are identical (verify `cx`/`cy` attributes equal).
- `data-layout="stable"` on root `<svg>`.
- No E150x errors (N=6 ≤ 20, T=4 ≤ 50).
- E1503 NOT emitted (no fallback triggered).
- Reverse edge `(a,s)` added in frame 2 and visible; node "a" stays at same position.

### 11.2 Tarjan SCC on N=12 — DFS tree edges appearing one-by-one

```latex
\begin{animation}[id=tarjan-scc]
\compute{
  nodes = list(range(12))
  # DFS tree edges revealed sequentially
}
\shape{g}{Graph}{
  nodes=${nodes},
  edges=[],
  directed=true,
  layout="stable",
  layout_seed=7
}

\step
\apply{g}{add_edge=(0,1,{})}
\highlight{g.node[0]}
\narrate{DFS visits node 0, discovers edge to 1.}

\step
\apply{g}{add_edge=(1,2,{})}
\highlight{g.node[1]}
\narrate{DFS visits 1, discovers edge to 2.}

% ... 10 more steps revealing edges ...
\end{animation}
```

Expected:
- 12 frames (≤ 30 soft limit, ≤ 100 hard limit).
- N=12 ≤ 20: stable layout applied.
- All 12 nodes visible in all frames (initially isolated, then connected one by one).
- Node positions constant across frames.
- E1503 NOT emitted.

### 11.4 Cache key correctness — same union, different frame sequences

Two animations `A` and `B` with identical node set `{s, a, b, t}` and identical edge union
`{(s,a), (s,b), (a,t), (b,t)}` but different per-frame orderings:

- Animation A frames: `[{(s,a),(a,t)}, {(s,b),(b,t)}, {(s,a),(s,b),(a,t),(b,t)}]`
- Animation B frames: `[{(s,b),(b,t)}, {(s,a),(a,t)}, {(s,a),(s,b),(a,t),(b,t)}]`

Expected:
- `cache_key(A) ≠ cache_key(B)` (different per-frame sequences → different hashes).
- SA runs independently for A and B; node positions may differ (different crossing costs
  per frame).
- Neither animation returns cached positions of the other.

This test verifies the fix for audit finding 6.1 (cache key collision bug).

### 11.3 Fallback test — N=25 triggers E1501

```latex
\begin{diagram}
\shape{large_g}{Graph}{
  nodes=${range(25)},
  edges=[],
  layout="stable"
}
\end{diagram}
```

Expected:
- E1501 emitted (N=25 > 20).
- E1503 emitted (fallback to force).
- Graph renders with `layout="force"` positions.
- `data-layout="force"` (not "stable") on root `<svg>`.

---

## 12. Base-spec deltas

**§3.1 `\shape` command, Type parameter**: the primitive type list does not need updating
(Graph is already a known type). However, the list of valid `layout=` values for `Graph`
must be extended.

In base spec §5, the `Graph` primitive parameter table entry for `layout` currently reads:

> `layout`: `"force"` | `"circular"` | `"bipartite"` | `"hierarchical"` (default: `"force"`)

This should be updated to:

> `layout`: `"force"` | `"circular"` | `"bipartite"` | `"hierarchical"` | `"stable"`
> (default: `"force"`). See `primitives/graph-stable-layout.md` for the `"stable"` spec.

**§8 HTML output contract** — `data-layout="stable"` attribute (audit finding 4.8):

The `data-layout="stable"` attribute on the SVG root is a base-spec delta. Base spec §8
does not list `data-layout=` as a frozen data attribute. Agent 4 must add it to the
base-spec §8 attribute table under the note: "Graph primitives with `layout=stable` emit
`data-layout="stable"` on the root `<svg>` to signal to CSS and E2E tests that stable
layout was applied."

Per the `data-scriba-*` naming convention (audit finding 4.10), this attribute is exempt
because `data-layout` applies to the Graph primitive's native attribute set (not a
Scriba-specific extension attribute). However, if a consolidation pass is done, it should
be renamed to `data-scriba-layout`. This is noted for the sanitizer whitelist.

**§11** error catalog: add a note that error codes E1500–E1509 are reserved for
`Graph layout=stable`. The existing catalog in §11 (which uses ranges E1001..E1299) does
not need numeric changes; E1500 is outside the existing range and is compatible.

Agent 4 will merge both deltas.
