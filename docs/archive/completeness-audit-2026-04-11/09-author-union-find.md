# 09 — Author: Union-Find (DSU) with Path Compression

**Audit agent:** 9 / 14 (completeness, editorial-author lens)
**Scriba:** v0.5.1, HEAD `eb4f017`
**Date:** 2026-04-11

## Scope

Author a cookbook-style animation for Union-Find (Disjoint Set Union) on 8
elements with union-by-rank plus path compression. The editorial must depict:

1. Eight singleton sets.
2. Seven `union` operations building a forest.
3. A `find` that walks a chain, followed by path compression — one node's
   parent pointer gets rewritten mid-animation.
4. A final union collapsing everything into a single set.

The central question: can Scriba animate **dynamic re-parenting** — a node
whose parent changes mid-scene — using a primitive, without redrawing the
entire picture per frame?

## Algorithm

Concrete operation sequence, union-by-rank with path compression:

| # | Op              | Result                                             |
|---|-----------------|----------------------------------------------------|
| 1 | `union(1,2)`    | `parent[2]=1`, `rank[1]=1`                         |
| 2 | `union(3,4)`    | `parent[4]=3`, `rank[3]=1`                         |
| 3 | `union(1,3)`    | rank tie, `parent[3]=1`, `rank[1]=2`               |
| 4 | `union(5,6)`    | `parent[6]=5`, `rank[5]=1`                         |
| 5 | `union(7,8)`    | `parent[8]=7`, `rank[7]=1`                         |
| 6 | `union(5,7)`    | `parent[7]=5`, `rank[5]=2`                         |
| 7 | `find(8)`       | walks `8 -> 7 -> 5`, then **compresses**: `parent[8]:=5` |
| 8 | `union(1,5)`    | rank tie, `parent[5]=1`, `rank[1]=3`               |

The critical frame is #7: an edge `(8,7)` must be *replaced* by `(8,5)`. Every
other step is an edge addition, but this is a **topology mutation in place**.

## Primitive choice + rationale

I inspected both candidate primitives.

**`Tree`** (`scriba/animation/primitives/tree.py`):

- Takes `root`, `nodes`, `edges` at construction time and runs the
  Reingold–Tilford layout once. Position map is frozen.
- Implements `PrimitiveBase` but has **no** `apply_command` method. A grep of
  `scriba/animation/primitives` confirms only `array`, `stack`, `queue`,
  `linkedlist`, `hashmap`, `plane2d`, `metricplot`, and `variablewatch` have
  `apply_command`. Tree and Graph are structurally static.
- `scriba/animation/scene.py::apply_prelude` registers shapes exactly once;
  `_apply_command` dispatches `\apply` to the primitive's `apply_command`,
  which Tree does not expose. There is no delete/insert edge API.

**`Graph`** (`scriba/animation/primitives/graph.py`):

- Same story. Edges are fixed at prelude time; layout runs once; no
  `apply_command`.
- Upside vs Tree: supports `directed=true`, so I can draw parent pointers as
  arrows and multiple arrows can emanate from one node (needed for path
  compression where node 8 has both an "old parent" arrow and a "new parent"
  arrow visible simultaneously in different states).
- Upside vs Tree: Graph tolerates arbitrary edge sets including the
  "replaced" edge case. Tree with `(8,7)` and `(8,5)` both declared would
  either error out (two parents for node 8) or render a malformed
  parent-child map under Reingold–Tilford.

**Decision — I document both approaches:**

1. **Tree approach (pre-baked final shape, dim-then-light).** Declare a Tree
   whose edge set is *the final rooted forest after step 8* (rooted at 8 or 1
   — either works, but picking one forces a particular final layout).
   Pre-dim everything; light edges as unions fire. Path compression must be
   narrated only, because Tree cannot show the (8,5) shortcut edge alongside
   the (8,7) stale edge. The old edge can be dimmed, but no new edge can
   appear.

2. **Graph approach (superset of all edges).** Declare a Graph whose edges
   are the union of every parent pointer that ever exists across the run
   (eight edges: `(2,1),(4,3),(3,1),(6,5),(8,7),(7,5),(8,5),(5,1)`). All
   start dim. Each step lights the relevant edge. Path compression is
   truthfully rendered: edge `(8,7)` returns to dim and edge `(8,5)` lights
   up.

The Graph approach is the only one that **visually** captures re-parenting.
The Tree approach can only narrate it. I adopt Graph as the primary
implementation.

## Final .tex (inline)

Primary submission — `/tmp/completeness_audit/09-union-find.tex`
(the existing file on disk was an earlier Tree-based draft; for the
authoritative Graph-based version I also wrote
`/tmp/completeness_audit/09-union-find-graph.tex`):

```tex
\begin{animation}[id="dsu-graph-probe", label="DSU via Graph primitive probe"]
\shape{G}{Graph}{nodes=[1,2,3,4,5,6,7,8],
  edges=[(2,1),(4,3),(3,1),(6,5),(8,7),(7,5),(8,5),(5,1)],
  directed=true, layout="stable"}

\recolor{G.edge[(2,1)]}{state=dim}
\recolor{G.edge[(4,3)]}{state=dim}
\recolor{G.edge[(3,1)]}{state=dim}
\recolor{G.edge[(6,5)]}{state=dim}
\recolor{G.edge[(8,7)]}{state=dim}
\recolor{G.edge[(7,5)]}{state=dim}
\recolor{G.edge[(8,5)]}{state=dim}
\recolor{G.edge[(5,1)]}{state=dim}

\step
\narrate{DSU on 8 elements. All potential parent edges pre-declared and
dimmed; they will be lit as unions fire. Path compression will swap one
active edge for another.}

\step
\recolor{G.edge[(2,1)]}{state=good}
\narrate{union(1,2) -> parent[2]=1.}

\step
\recolor{G.edge[(4,3)]}{state=good}
\narrate{union(3,4) -> parent[4]=3.}

\step
\recolor{G.edge[(3,1)]}{state=good}
\narrate{union(1,3) -> rank tie, parent[3]=1, rank[1]=2.}

\step
\recolor{G.edge[(6,5)]}{state=good}
\narrate{union(5,6) -> parent[6]=5.}

\step
\recolor{G.edge[(8,7)]}{state=good}
\narrate{union(7,8) -> parent[8]=7.}

\step
\recolor{G.edge[(7,5)]}{state=good}
\narrate{union(5,7) -> 5 taller, parent[7]=5.}

\step
\recolor{G.edge[(8,7)]}{state=current}
\recolor{G.edge[(7,5)]}{state=current}
\narrate{find(8): walk 8 -> 7 -> 5 to reach the root.}

\step
\recolor{G.edge[(8,7)]}{state=dim}
\recolor{G.edge[(8,5)]}{state=good}
\recolor{G.edge[(7,5)]}{state=good}
\narrate{Path compression: parent[8] := 5. Edge (8,7) is dimmed; edge (8,5)
lights up. This is the re-parenting frame.}

\step
\recolor{G.edge[(5,1)]}{state=good}
\narrate{union(1,5) -> rank tie, parent[5]=1. One set.}
\end{animation}
```

## Compile result

Both files compile clean:

```text
$ uv run python render.py /tmp/completeness_audit/09-union-find.tex \
    -o /tmp/completeness_audit/09-union-find.html
Rendered 1 block(s) -> /tmp/completeness_audit/09-union-find.html

$ uv run python render.py /tmp/completeness_audit/09-union-find-graph.tex \
    -o /tmp/completeness_audit/09-union-find-graph.html
Rendered 1 block(s) -> /tmp/completeness_audit/09-union-find-graph.html
```

Zero warnings, zero errors. The Graph renders directed arrows for each
parent edge. Note: I did not open the HTML in a browser to verify that
`layout="stable"` places the 8 nodes legibly, and I did not check whether
Graph handles self-loops (which I deliberately avoided). Visual QA is out
of scope for a headless audit.

## Friction points (dynamic re-parenting)

### F1. Tree and Graph are topologically frozen at prelude time — CRITICAL

The single biggest gap. `\shape` is processed by `apply_prelude` once;
after that the primitive's edge list is read-only. There is no API for:

- adding an edge mid-animation
- removing an edge mid-animation
- changing a node's parent
- rebalancing / reshaping a Tree

This means any algorithm whose animation semantics depend on **mutating
structure** (DSU, splay, AVL rotations, link-cut, Euler-tour trees, persistent
data structures displayed over time) must be encoded as
"declare the superset, recolor the active subset". The author carries the
cognitive burden of enumerating every edge that will ever be needed *before
the story starts*, which is exactly the kind of forward reference that
cookbook authoring is supposed to eliminate.

Empirical confirmation: `examples/cookbook/h07_splay_amortized.tex` — the
"splay tree amortized analysis" example — **does not animate any rotation
at all**. It declares a fixed 7-node tree, then narrates the potential
function via MetricPlot while recoloring nodes. This is a tacit admission
in the shipping cookbook that splay rotations cannot be drawn.

### F2. Tree disallows multi-parent edge sets

If I tried to declare a Tree with both `(8,7)` and `(8,5)` to encode the
pre-compression and post-compression states, Tree's `children_map` would
list node 8 under both parents and Reingold–Tilford would misbehave (likely
picking whichever appeared first). The Graph primitive has no such
restriction. For DSU-style animations, Graph is strictly more expressive
than Tree despite being semantically *less* structured. That is an API
smell: Tree ought to be the better abstraction for rooted forests, but it
is so rigid that Graph wins by default.

### F3. No edge visibility control, only color states

`recolor ... state=dim` is the closest thing to "hide this edge", but the
edge is still rendered — just lower contrast. For the initial-singleton
frame of DSU I would ideally start with zero visible edges (eight
self-isolated dots). The best I can do is dim all eight edges so they sit
as ghostly hints in the background. Arguably useful as a preview but
inaccurate: a viewer seeing the very first frame sees "roughly the final
topology, faded out", not "eight singletons".

### F4. Directed graph self-loops are undefined

I avoided self-loops entirely (parent[i]=i in idle singletons), because
`fruchterman_reingold` with `dx=dy=0` would hit its `max(..., 0.01)` guard
and produce a degenerate zero-length line that the SVG pipeline would
render as an invisible dot. There is no documented self-loop rendering
path for Graph. An author wanting to depict "each node is its own parent"
literally has no primitive support.

### F5. Layout lock-in forces edge-set foreknowledge

Because layout runs once at construction, the positions of all nodes are
determined by the *complete* edge set at declaration time. If I had only
declared `(2,1)` and `(4,3)` at the start and then wanted to add edges
later, even if mutation were possible, the positions would no longer be
optimal for the new structure. In practice Graph authors must think of
the final topology first, then animate *backwards* — the opposite of how
an editorial narrative reads.

### F6. No ghost / stale-edge affordance

When path compression fires, the stale `(8,7)` edge would ideally fade
out and the `(8,5)` edge would slide into place. Scriba has no
cross-frame tweening of edge positions or any "ghost / stale" state;
`dim` is the only tool. The compression frame is therefore a *cut*, not
an animation — a viewer who blinks between steps 8 and 9 would see the
before and after but no motion.

### F7. Tree primitive's author-facing docs don't warn about this

`docs/spec/primitives.md` §7 (the spec referenced from `tree.py`) is the
obvious place to say "Tree is static topology; for DSU / splay / link-cut
use Graph with pre-declared edge superset and recolor". I did not audit
the spec file directly, but the splay cookbook example behaves as if the
author discovered this limit by running into it. Other editorial authors
will pay the same tax.

## Feature requests

Ordered by how much they would have helped me on this task.

### FR1. `Tree.reparent(node, new_parent)` / `Graph.add_edge` / `Graph.remove_edge`

The highest-leverage change. Expose `apply_command` on Tree and Graph with
operations:

```
\apply{T}{op="reparent", node=5, parent=8}
\apply{G}{op="add_edge", from=8, to=5}
\apply{G}{op="remove_edge", from=8, to=7}
```

For Tree this requires recomputing Reingold–Tilford on mutation (cheap at
N <= 100). For Graph it requires keeping force-directed positions stable
across mutations (solvable via "warm start" where the old positions seed
the next layout pass; `graph_layout_stable.py` already exists as a
stability-oriented variant — extend it to accept an initial position
dict).

### FR2. Edge state `hidden` distinct from `dim`

Add a first-class "not present" state that omits the edge from SVG
entirely. Then initial DSU singletons would be eight isolated dots with
zero edges, exactly as the algorithm demands. This is a small, additive
change to `svg_style_attrs` and the Tree/Graph emitters.

### FR3. Self-loop rendering for Graph

When `u == v`, draw a small circular loop anchored at node `u` offset by
the node radius. Standard Graphviz / D3 handles this. Would let authors
depict "parent[i] = i" literally in DSU, cycle detection, fixpoint
iterations.

### FR4. Edge animation: tween between (u, v) and (u, v') across a `\step`

When a `recolor` transitions edge `(u, v)` to `hidden` and edge `(u, v')`
from `hidden` to `good` in the same frame, the renderer should interpolate
the endpoint — i.e. the arrow head slides from `v` to `v'`. Path
compression, splay rotations, and link-cut reroot operations all want this.
Stretch goal; the above three matter more.

### FR5. `Tree` kind `"dsu_forest"`

A specialised Tree kind that accepts `parent: dict[node, node]` and treats
it as the source of truth, recomputing layout on each `\apply`. Mirrors
the `"segtree"` and `"sparse_segtree"` precedents already in `tree.py`.

## Author effort

- **Spec reading:** ~10 minutes to skim Tree and Graph source, confirm no
  `apply_command`, cross-check the splay example for precedent.
- **First draft (Tree, pre-baked final shape):** effectively borrowed the
  existing file on disk. Compiles clean.
- **Second draft (Graph, edge superset):** ~15 minutes once I knew Graph
  was the right call. One typo (`\end{animation>`) caught on first
  compile. Compiles clean.
- **Total active time:** ~45 minutes including this writeup.
- **Without the friction:** a rich, primitive-mutation-driven DSU would
  be a ~20-line editorial — one `\shape{T}{Tree}{...singletons...}`
  followed by eight `\apply{T}{op="reparent", ...}` commands. That is the
  API I wish existed.

## Severity summary

| ID  | Friction                                             | Severity |
|-----|------------------------------------------------------|----------|
| F1  | Tree and Graph topology frozen at prelude time       | **CRITICAL** |
| F2  | Tree rejects multi-parent edges; Graph wins by default | HIGH |
| F3  | No hide/hidden edge state, only `dim`                | HIGH |
| F4  | Self-loops undefined for Graph                       | MEDIUM |
| F5  | Layout lock-in forces edge-set foreknowledge         | HIGH |
| F6  | No ghost / stale-edge tween                          | MEDIUM |
| F7  | Spec does not warn about Tree/Graph immutability     | LOW |

**Overall:** Scriba v0.5.1 can tell the DSU story with visuals, but only
by forcing the author to pre-declare the complete edge superset and
animate via color state. True dynamic re-parenting — the defining
interaction of DSU, splay, link-cut, and every other "structure mutates
as the algorithm runs" data structure — is **not supported**. The
cookbook's own splay example confirms this limitation ships to users.
The single most impactful fix is exposing `apply_command` on Tree and
Graph with `add_edge`, `remove_edge`, and `reparent` operations.
