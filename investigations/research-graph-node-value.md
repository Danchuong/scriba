# Research — Should the Graph primitive render a PER-NODE value?

**Question:** Should `Graph` render a per-node value (Dijkstra distances, BFS
levels, DP states, low-link numbers, max-flow labels) the way Tree/Forest do?
Today (0.26.5) `\apply{g.node[X]}{value=...}` is rejected with **E1105**
("value= is edge-scoped on Graph"). The value-flipback design
(`investigations/design-value-flipback.md`) flagged per-node value display as a
**viable but deferred product call**. This case answers: is it worth building,
and if so, how?

**Read-only investigation + feature-design recommendation. No implementation.**

**Evidence grades:** Confirmed = cite `path:line` + rendered output •
Deduced = code-path / corpus reasoning • Hypothesized = plausible, unproven.

---

## TL;DR

- **Demand: REAL and pervasive (Confirmed).** Six flagship graph examples each
  hand-build a *side Array / DPTable / VariableWatch* to carry a per-node value
  the graph node cannot hold. Tarjan bridges builds **two** mirror arrays
  (`disc`+`low`). The two structures that *can* hold a value (Grid cells, Tree
  nodes) get the value painted on-structure — Graph is the conspicuous gap.
- **Workaround: acceptable but painful (Confirmed by render).** A per-node value
  costs **1 extra `\shape` + ~2 commands per update on a separate primitive**,
  plus an index→node mapping convention and reader eye-tracking. A direct
  `\apply{g.node[X]}{value=d}` would be **1 command, on the node, 0 setup**.
- **Design: mirror Tree/Forest (Confirmed feasible).** The node already renders a
  centered `<text>` (`graph.py:2264`), identical to Tree (`tree.py:1004`) and
  Forest (`forest.py:577`). Option A = read `get_value` there + flip
  `renders_value` to accept `node[`. **~S, byte-identical for all existing docs,
  no golden re-bless, no `SCRIBA_VERSION` bump.**
- **Recommendation: BUILD (small).** High value (unblocks the single most common
  graph-teaching gesture), low cost, clean precedent. Frame as the **Option-A
  resolution** of a design the flipback investigation already teed up: the E1105
  reject becomes a render for the one primitive where it is semantically
  defensible.

---

## PART 1 — DEMAND: which CP algorithms display a per-node value on a graph?

A per-node numeric label is the *output* or *core state* of most classic graph
algorithms. Corpus census — every general-graph example in `examples/` that has
a per-node quantity works around the missing feature:

| Algorithm | Per-node quantity | How the corpus shows it TODAY | Node-value centrality | Grade |
|---|---|---|---|---|
| **Dijkstra / SPFA / Bellman-Ford** | `dist[v]` | `dijkstra.tex`, `dijkstra_editorial.tex`: side `Array` (`dist`/`d`, 5–6 cells, `labels="0..5"`) + transient `\annotate{G.node[B]}{label="2+1=3"}` | **HIGH** — the distance label *is* the algorithm's output | Confirmed |
| **BFS / 0-1 BFS levels** | `level[v]` | `bfs.tex`: Tree-depth proxy + `\annotate{G.node[B]}{label="d+1"}`; `bfs_grid_editorial.tex`: `dist` painted **on Grid cells** via `\apply{g.cell[r][c]}{value=N}` | **HIGH** — the level per node is the answer | Confirmed |
| **Tarjan bridges / articulation / SCC** | `disc[v]`, `low[v]` | `cses/necessary_roads.tex`: **TWO** side Arrays `disc` + `low` (21 `\apply` calls) | **HIGH** — low-link numbers per node *are* the algorithm | Confirmed |
| **DSU (union-find)** | `parent[v]`; `rank`/`size` | `union_find.tex`: side `Array parent[]` (7 cells); rank/size only in narration | **MED-HIGH** — parent shown as edges; rank/size latent | Confirmed |
| **DP on tree** | `dp[v]` | Tree node-value override — **already works** (`tree.py:1004`, docs: "value replaces that node's display") | **HIGH** | Confirmed |
| **DP on DAG** | `dp[v]` | *No shipping example* — no on-Graph path exists | **MED-HIGH** | Deduced |
| **Max-flow** | excess / height `h(v)` (push-relabel) | `maxflow.tex` (Edmonds-Karp): `VariableWatch` scalar state; per-node excess/height **not shown** (EK/Dinic track scalar + level, not per-node labels) | **MED** — central for push-relabel, absent for augmenting-path | Deduced |
| **Binary lifting / LCA** | `depth[v]` | `cses/planets_queries2.tex`: `DPTable` (genuinely 2D per-node×level — a table is appropriate) + `ans` Array | **LOW-MED** | Confirmed |
| **Topological sort (Kahn)** | in-degree counter `[v]` | *No shipping example* | **LOW-MED** | Hypothesized |

**Verdict: demand is REAL, not thin.** The most-taught graph algorithms
(Dijkstra, BFS, Tarjan, DSU, DP) all center a per-node number. The repo's own
corpus proves the want empirically: **6 examples build side mirrors**, and the
two substrates that *can* hold a value (Grid, Tree) get it on-structure. The
"array mirror" is a rendering crutch for Graph, not an independently-taught data
structure — except in Dijkstra, where `dist[]` is genuinely also an array, so
on-node display would *complement* (not replace) the array there. For BFS-level,
low-link, DSU-rank, DAG-DP, and push-relabel height, on-node display is strictly
better than a parallel primitive.

---

## PART 2 — CURRENT WORKAROUND (rendered + counted)

Rendered a 4-step, 5-node Dijkstra fragment (source A) with the shipping idiom —
a side `Array` mirroring node→dist — to `_wa.html` (exit 0, cleaned up). The
graph nodes render **A–E** (letters only); the distances live in the Array below,
tied to nodes only by the `labels="0..4"` + `label="$dist[A,B,C,D,E]$"`
convention.

**Command cost of the per-node value (this fragment, 4 distance updates):**

| Piece | Count |
|---|---|
| Extra `\shape{dist}{Array}` (the mirror primitive) | **1 setup** |
| `\apply{dist.cell[i]}{value=...}` (the value sets) | 4 |
| `\recolor{dist.cell[i]}{...}` (highlight the mirror cell) | 5 |
| `\annotate{G.node[B]}{label="2+1=3"}` (transient value *near* the node) | 1 |
| **Total value-plumbing commands** | **10 + 1 shape** |

**Hypothetical `\apply{g.node[X]}{value=d}`:** 0 extra shapes, **4 `\apply` on
the node itself** (one per update), value persistent + co-located.
`\recolor{G.node}` for state is orthogonal (already written).

So: **10 cmds + 1 shape → 4 cmds, 0 setup** — a ~60% cut in value-plumbing plus
elimination of an entire primitive.

**Invisible (non-command) costs of the workaround:**
- The **index→node mapping** (`labels="0..4"`, `"0:A 1:B ..."`) the reader must
  internalize and the author must keep aligned (cell `i` ≡ node `i`).
- **Eye-tracking** between two primitives (graph up top, array below) — the value
  is never co-located with the node.
- `\annotate{...label="2+1=3"}` puts a value *near* the node but is **transient**
  (a callout with a leader arrow, gone next step) — not a persistent node value.

**Assessment: acceptable but genuinely painful.** It ships (used in 6 examples),
but it forces a parallel primitive + a mapping convention + reader eye-tracking
for a quantity that conceptually lives *on the node*. The pain scales with node
count and with the number of per-node quantities (Tarjan needs **two** arrays).

**Reject confirmed (Confirmed by render):** `\apply{G.node[A]}{value="7"}` on a
3-node graph → `error [E1105]: Graph \apply parameter 'value=' is not rendered on
'node[A]'; it would be silently dropped ... hint: value= is edge-scoped on Graph;
node values are not rendered — apply value= to an edge[(u,v)] instead`.

---

## PART 3 — TREE PRECEDENT + GRAPH DESIGN

### The Tree/Forest/Hypercube mechanism (Confirmed)

Tree and Forest render a node value by letting an applied value **override the
node's display label** — a single `get_value` read in the emit loop:

```python
# tree.py:1004  (Forest identical at forest.py:577)
override = self.get_value(self._node_key(node_id))
display_label = override if override is not None else self.node_labels.get(node_id, str(node_id))
```

`get_value` returns `None` when unset → the id label renders unchanged → existing
output is byte-identical. Docs already document this for **Tree segtree**
("value replaces that node's display"), **Forest**, and **Hypercube**
(`\apply{L.subset[i]}{value=X}` "overrides a node's text (DP value on a subset)")
— i.e. per-node value override is an **established, documented pattern** across
three primitives. Graph is the odd one out.

### Where the value would show on a Graph node — the key design choice

The Graph node already emits a centered `<text>` identical to Tree/Forest:

```python
# graph.py:2264  — today hard-codes str(node_id) as the label
node_text = _render_svg_text(str(node_id), cx, cy, ...)
```

Two placements, materially different for Graph because **the node name is
load-bearing** (edges are `(A,B)`, narration says "settle A", selectors are
`G.node[A]`):

| Option | Where value shows | Keeps name? | Cost | Notes |
|---|---|---|---|---|
| **A1 — Override (mirror Tree exactly)** | *inside* the circle, replacing the id | No (author composes `"A:7"` if both wanted) | **S** | ~3-line `get_value` read at `:2264` + flip `renders_value` at `:1460`. 0 new motion kind. Exactly how Tree segtree shows `"[0,3]=11"`. |
| **A3 — Dedicated badge beside/below** | a second pill at the circle corner / below-lane, id stays in circle | Yes, automatically (`A` + `7`) | **M–L** | Nicer for graphs, but the badge is a **new paintable** that must join Graph's obstacle/collision system (edge-weight pills, GEP-06, `resolve_self_content_rects`) — the hairiest part of `graph.py`. New CSS class + layout participation. |

**Recommended: A1 (override) now; A3 as a future polish.** A1 is the
least-vocabulary, zero-new-motion, byte-identical option that closes the E1105
gap immediately. It rides the existing `value_change` transition — **no new
motion kind** — and mirrors an established primitive. The one tradeoff (override
loses the letter) is mitigated exactly as Tree already does it: the author
composes the string (`value="A:7"` or `value="7"` when position already
identifies the node). Add A3 only if compose-your-own-name proves insufficient in
practice; it is disproportionate for a first cut and touches Graph's collision
core.

### Motion / CSS / version impact (Confirmed)

- **Motion:** none new. The differ already emits `value_change` for
  `g.node[...]` value deltas — that emit is precisely what causes today's
  flip-back (`design-value-flipback.md`, `scriba.js:183` stamps the value into
  the node `<text>`). Option A makes the **server SVG agree** with the runtime
  stamp; the runtime handler is **untouched**.
- **CSS:** none for A1 (reuses the node text + existing state halo cascade).
- **Byte-identity for non-users:** **airtight.** Grep of `examples/` +
  `tests/golden` finds **zero** docs applying `value=` to a graph node — and none
  *can* exist, since it's been E1105-rejected since 0.26.3. So every existing doc
  renders byte-for-byte identically (`get_value` unset → `str(node_id)`
  fallback). **Zero golden re-bless.**
- **`SCRIBA_VERSION`:** **no bump required.** `SCRIBA_VERSION` guards the
  runtime/HTML *contract* for existing docs; A1 changes no existing doc's bytes
  and the runtime JS already stamps node values. (Contrast 0.26.4's caret, which
  bumped because `data-role` tag bytes changed in *every* existing doc.) A
  conservative "capability-signal" bump is *available* if the project wants to
  flag "a graph node can now render a value," but it is not needed for
  correctness and would still be **0 re-bless**. Package version = **minor**
  (new feature).

### Implementation surface (design only — 2 coordinated points)

1. `graph.py:2264` — read `override = self.get_value(self._node_key(node_id))`,
   use `str(override) if override is not None else str(node_id)` as the label
   (byte-for-byte the Tree/Forest edit).
2. `graph.py:1460` `renders_value` — return
   `suffix.startswith(("edge[", "node["))` (edges keep the documented weight
   feature; nodes now honor value=). This flips the `_frame_renderer.py:103-153`
   pre-differ gate from *reject* to *pass* for `node[`, so no flip-back can occur
   (the server now renders what the runtime stamps).

The other three flip-back parts (Stack `item`, NumberLine `tick`, CodePanel
`line`) **correctly stay E1105** — none has a defensible value slot. Graph node
is the single Option-A candidate the flipback doc identified, and this confirms it.

---

## PART 4 — RECOMMENDATION: build or leave?

**BUILD (small).** Framing: a **feature**, delivered as the **Option-A
resolution** of a deferred design — the E1105 reject becomes a render for the one
primitive where per-node value is semantically defensible and precedented.

**Value (HIGH):**
- Unblocks the single most common graph-teaching gesture — a number on each node
  — across Dijkstra, BFS/0-1-BFS, Tarjan (bridges/SCC/artic), DSU rank/size,
  DP-on-DAG, and push-relabel. 6 flagship examples currently pay the workaround
  tax; Tarjan pays it twice.
- Removes a whole class of authoring friction (side primitive + index-mapping +
  eye-tracking) and closes a **substrate asymmetry** users can already feel: Grid
  and Tree hold values, Graph doesn't.
- Turns a **loud reject the author hits naturally** (E1105 on the obvious
  `\apply{g.node[X]}{value=d}`) into the thing they wanted.

**Cost (LOW, ~S):**
- ~3-line emit read + 1-line `renders_value` change, mirroring code that already
  exists in three primitives.
- Byte-identical for all existing docs; **zero golden re-bless**; **no
  `SCRIBA_VERSION` bump**; runtime untouched.
- Test churn: add a render assertion (`g.node[A]` value= shows in server SVG,
  both frames) + a doc using node value=; move Graph's row in
  `test_generic_value_label`/flip-back tests from the reject set to the render
  set. (Stack/NumberLine/CodePanel stay in the reject set.)

**Why not leave it:** the workaround is *acceptable* but the fix is so cheap and
so well-precedented, and the demand so pervasive, that the value/cost ratio is
lopsided in favor of building. Leaving it also perpetuates the asymmetry and the
"natural first attempt → error" papercut.

**One honest caveat:** override (A1) trades the node letter for the value. For
Dijkstra that is usually fine (position + edges + narration identify the node,
and `dist[]` as an array can still coexist); where the letter must stay, the
author composes `"A:7"`. If real usage shows compose-your-own-name is too
fiddly, add the A3 badge later — but do **not** gate the S-sized win on the M–L
badge.

---

## Conclusion

- **Demand is REAL and pervasive (Confirmed):** 6 flagship graph examples
  hand-build side Array/DPTable/VariableWatch mirrors for per-node values;
  Tarjan builds two; Grid and Tree (which *can* hold values) paint them
  on-structure. Graph is the gap.
- **Workaround is acceptable but painful (Confirmed by render):** 1 extra shape +
  ~2 cmds/update on a separate primitive + an index-mapping convention + reader
  eye-tracking, vs. a hypothetical 1 `\apply` on the node.
- **Design is clean and cheap (Confirmed):** mirror Tree/Forest — `get_value`
  override in the node emit + `renders_value` accepting `node[`. **~S,
  byte-identical, 0 re-bless, no `SCRIBA_VERSION` bump.** Recommend **A1
  (override, compose `"A:7"` for name+value)** now; defer the **A3 badge** (M–L,
  obstacle-system integration) unless usage demands it.
- **Recommendation: BUILD.** HIGH value / LOW cost. Frame as the Option-A
  resolution the flipback design already scoped; Stack/NumberLine/CodePanel stay
  E1105.

**Confidence: HIGH.** Demand is a corpus census (6 examples, cited); the
workaround cost and the E1105 reject are both **rendered** (not asserted); the
design is grounded in three existing implementations (`tree.py:1004`,
`forest.py:577`, Hypercube docs) plus the exact Graph toggle points
(`graph.py:2264`, `graph.py:1460`, `_frame_renderer.py:103-153`); byte-identity
is airtight (0 corpus docs use the path, and none can pre-fix). The single open
item is a **product choice, not a fact**: whether to also ship the A3 badge
(keep name automatically) or rely on author-composed `"A:7"` — and whether to
spend a conservative `SCRIBA_VERSION` capability-bump that correctness does not
require.
