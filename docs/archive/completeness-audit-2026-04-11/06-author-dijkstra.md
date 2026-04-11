# Completeness Audit 06 — Author Experience: Dijkstra on a Weighted Graph

## Scope

Agent 6/14 of the completeness audit. Task: write a cookbook-style animation of Dijkstra's shortest-path algorithm on a small weighted graph from the perspective of a real editorial author, compile it, iterate until clean, and record every friction point.

Target primitives exercised: `Graph` (undirected, 6 nodes, 9 edges), `Array` (distance + predecessor), `Queue` (simulating a priority queue), plus `\step`, `\recolor`, `\apply`, `\narrate`.

Source repo: scriba v0.5.1, HEAD `da100de` (local working copy tip). Scriba internals and `examples/` were **not** modified. Output lives at `/tmp/completeness_audit/06-dijkstra.tex` and `/tmp/completeness_audit/06-dijkstra.html`.

## Algorithm being animated

Dijkstra from source `A` on a 6-node (A–F) undirected weighted graph with 9 edges. Weights chosen so that edge relaxations actually happen (i.e. `dist[B]` first becomes 4 via `A–B`, then later relaxes to 3 via `A–C–B`) and so that F ends up with two update rounds as well. The visualization shows:

1. The graph with current/visited/path-tree states via node + edge recoloring.
2. A 6-cell `dist` array that starts at `inf` and fills in with the relaxed distances.
3. A 6-cell `prev` array tracking the predecessor of each settled node.
4. A `Queue` primitive standing in for a min-priority queue — author has to eyeball the ordering and narrate "stale entry skipped" whenever lazy deletion happens, because there is no real PQ primitive.
5. A final "shortest-path tree" frame where the five tree edges go `good` and the four non-tree edges go `dim`.

The final result: `dist = [0, 3, 2, 8, 10, 13]`, tree `A–C, C–B, B–D, D–E, E–F`.

## Final .tex (inline)

The full source is at `/tmp/completeness_audit/06-dijkstra.tex`. 157 lines, 17 `\step` blocks. Relevant structure (abridged — one frame each of init, relax, update, stale-pop, final):

```tex
\begin{animation}[id="dijkstra", label="Dijkstra shortest paths -- 6-node weighted graph"]
\shape{G}{Graph}{nodes=["A","B","C","D","E","F"],
  edges=[("A","B"),("A","C"),("B","C"),("B","D"),("C","D"),
         ("C","E"),("D","E"),("D","F"),("E","F")],
  directed=false, layout="stable"}
\shape{dist}{Array}{size=6, data=["inf","inf","inf","inf","inf","inf"],
  labels="A,B,C,D,E,F", label="$dist$"}
\shape{prev}{Array}{size=6, data=["-","-","-","-","-","-"],
  labels="A,B,C,D,E,F", label="$prev$"}
\shape{pq}{Queue}{capacity=8, label="PQ (sorted by dist)"}

\step
\narrate{Dijkstra ... Edge weights: AB=4, AC=2, BC=1, BD=5, CD=8, CE=10, DE=2, DF=6, EF=3. Source = A.}

\step
\apply{dist.cell[0]}{value=0}
\recolor{dist.cell[0]}{state=done}
\recolor{G.node[A]}{state=current}
\apply{pq}{enqueue="(0,A)"}
\narrate{Initialise. $dist[A]=0$, all others $\infty$. Push $(0,A)$ onto PQ.}

...

\step
\apply{pq}{dequeue=true}
\narrate{Pop $(4,B)$ -- stale, B already done. Skip and continue.}

...

\step
\recolor{G.node[F]}{state=done}
\recolor{G.edge[(A,C)]}{state=good}
\recolor{G.edge[(B,C)]}{state=good}
\recolor{G.edge[(B,D)]}{state=good}
\recolor{G.edge[(D,E)]}{state=good}
\recolor{G.edge[(E,F)]}{state=good}
\recolor{G.edge[(A,B)]}{state=dim}
...
\narrate{Done. Shortest distances from A: $dist=[0,3,2,8,10,13]$. Tree: A-C, C-B, B-D, D-E, E-F.}
\end{animation}
```

## Compile result

**Status: partial success.** The file compiles and renders 17 frames (one `<svg class="scriba-stage-svg">` per frame, 2263 lines of HTML) but emits 2 `UserWarning`s and has one silent semantic failure (labels ignored).

Command:
```bash
cd /Users/mrchuongdan/Documents/GitHub/scriba && \
  uv run python render.py /tmp/completeness_audit/06-dijkstra.tex \
    -o /tmp/completeness_audit/06-dijkstra.html 2>&1 | \
  tee /tmp/completeness_audit/06-dijkstra.log
```

Full log:
```
/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/emitter.py:339:
  UserWarning: selector 'pq' does not match any addressable part of 'pq'
/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/emitter.py:441:
  UserWarning: Queue 'pq': invalid selector 'pq', ignoring set_state()
Rendered 1 block(s) -> /tmp/completeness_audit/06-dijkstra.html
```

Reproduced cleanly on `examples/cookbook/convex_hull_andrew.tex` (same warning pair fires with `'stk'` and `'plane'`), so this is a pre-existing systemic issue, not something I provoked by being sloppy.

## Friction points

Numbered by the order I hit them while writing the .tex and re-compiling.

### F1. No priority-queue primitive — had to fake it with `Queue`

**File**: `scriba/animation/primitives/__init__.py` — no `PriorityQueue` registered.

Dijkstra is *the* textbook priority-queue algorithm. I wanted `\shape{pq}{PriorityQueue}{capacity=..., order=min}` where the primitive keeps items sorted by key and the pop animation highlights the current min. Instead I used `Queue{...}` and every narration frame had to say "(sorted by dist)" and the author is responsible for pushing in sorted order, which I immediately cheated on (`(4,B)` and `(3,B)` live in the queue simultaneously). Worse, when B relaxes from 4 to 3, I left the stale `(4,B)` in the queue and had to dedicate two separate `\step` frames (step 10 and the first half of step 14) purely to narrate "pop stale, skip" — pure ceremony with no state change on the graph. About **3 of my 17 frames** exist only because I had no real PQ.

### F2. `\apply{pq}{enqueue=...}` emits a false-positive warning

**File**: `scriba/animation/emitter.py:338–342` (and `:441`).

```
UserWarning: selector 'pq' does not match any addressable part of 'pq'
UserWarning: Queue 'pq': invalid selector 'pq', ignoring set_state()
```

Root cause: in `_validate_expanded_selectors` (scene.py → emitter.py), when the target key is the bare shape name (no dot), the suffix-stripping branch at `emitter.py:326` doesn't fire (`'pq'.startswith('pq.')` is false), so `suffix` stays as `'pq'` which is obviously not in `addressable_parts()`. The scene-level `_apply_apply` stores whole-shape apply params under the bare key `pq`, but the emitter's validator was written assuming every target has a dotted suffix. Same path also triggers the `set_state` fall-through at `emitter.py:441`.

Fix would be: treat an empty suffix (i.e. `target_key == shape_name`) as the "whole shape" selector, skip state validation, and route straight to `apply_command`. This is documented in the convex-hull audit (Agent 6 from the prior 21-agent round saw the same thing for `Stack`). Every queue/stack/plane2d animation in the repo hits this — the warnings are noise and the author has no way to silence them without modifying `scriba/`.

### F3. `Array.labels` silently drops comma-separated label lists

**File**: `scriba/animation/primitives/array.py:515–532` (`_parse_index_labels`).

I wrote `labels="A,B,C,D,E,F"` for both `dist` and `prev` because I wanted the cells labeled by node name. The parser only understands two formats — `"0..6"` and `"name[0]..name[6]"` — and the fallback at line 532 silently returns plain numeric labels `["0","1","2","3","4","5"]`. No warning, no error. I only noticed because I checked the source, not because the renderer told me. In the HTML the `dist` and `prev` arrays show `0,1,2,3,4,5` under the cells instead of `A,B,C,D,E,F`, which means viewers have to mentally re-index every narration sentence.

This is a design gap: either the parser should accept comma lists, or `_parse_index_labels` should raise `E1xxx` with a hint when the format is unrecognised.

### F4. Graph edges have no weight labels

**File**: `scriba/animation/primitives/graph.py` entire edge-rendering block (lines 364–395).

The Graph primitive renders unweighted edges only. Dijkstra without visible edge weights is half an animation — I had to cram `AB=4, AC=2, BC=1, BD=5, CD=8, CE=10, DE=2, DF=6, EF=3` into the very first narration and hope the viewer memorises it. There is no `edges_weights=[...]` param, no `weight_label` param on edge tuples, and `\annotate` on an edge (`\annotate{G.edge[(A,B)]}{label="4"}`) would work for one frame but I'd have to repeat the label on every frame to keep it visible, 9 edges × 17 frames = 153 annotation commands. Completely unreasonable workaround; I just didn't bother.

### F5. No way to recolor a Graph node/edge back to `idle` and have it feel visually distinct from "never visited"

I wanted to distinguish:
- `unvisited` (haven't popped yet, outside the frontier)
- `in frontier` (in PQ but not yet popped)
- `visited` (popped, settled)
- `being-relaxed` (currently-examined edge)

The only available states I know of from the cookbook examples are `idle`, `current`, `done`, `good`, `dim`, `path`. That's fine for a BFS/DFS tree walk but Dijkstra has four natural categories and the palette doesn't cleanly map. I ended up toggling edges back to `idle` after relaxing them (step 7, step 8, step 13) which visually flashes them off — not ideal but the least bad option. A `frontier` or `pending` state would be welcome.

### F6. `\apply{pq}{dequeue=true}` with no explicit target suffix is undocumented

**File**: `scriba/animation/primitives/queue.py:122–123` (docstring), examples only.

The Queue docstring says "whole-queue operations" but the only example of `enqueue`/`dequeue` I could find was by reading the source code. The `h05_mcmf.tex` example doesn't use Queue, `convex_hull_andrew.tex` uses Stack with `push="X"` and `pop=1` (a count). I guessed `dequeue=true` and it worked, but I could equally well have tried `dequeue=1`, `dequeue="A"`, or `dequeue` with no value. The Stack `pop=N` form and the Queue `dequeue=true` form are gratuitously inconsistent — why a count for Stack and a boolean for Queue?

### F7. Queue never shrinks visually after dequeue — cells stay "consumed" but rendered

**File**: `scriba/animation/primitives/queue.py:141–144`.

After `dequeue=true`, the code blanks the cell and advances `front_idx`. The SVG still reserves horizontal space for the front cells because `capacity=8`. For a running algorithm this means the PQ widget is an 8-wide row of mostly blanks, with the live elements drifting rightward until capacity is hit. I set `capacity=8` but pushed ~8 items total across the run so I was right at the edge — more pushes would have silently failed (`rear_idx < self.capacity` check, no warning).

### F8. Silent enqueue-overflow when `rear_idx >= capacity`

**File**: `scriba/animation/primitives/queue.py:133`.

```python
if self.rear_idx < self.capacity:
    self.cells[self.rear_idx] = enqueue_val
    self.rear_idx += 1
```

If you enqueue into a full queue, nothing happens. No warning, no error, no `animation_error("E1xxx", ...)`. For an algorithm author this is a loaded footgun: you bump up against capacity, your animation silently desyncs from the narration, and the only way to find out is eyeballing the rendered HTML.

### F9. The `labels` key on the `Array` shape param collides conceptually with the `label` (singular) key and the `cell[i].label` annotation field

I had `labels="A,B,C,D,E,F"` (index labels, plural) and `label="$dist$"` (array caption, singular) on the same shape. I got these confused on my first draft and wrote `label="A..F"` which did nothing visible. Only noticed when the cells rendered with no caption. The naming is confusing: `label` = caption, `labels` = per-cell index labels, and `\apply{arr.cell[i]}{label="X"}` (also singular) = per-cell annotation. Three different meanings, overloaded names.

### F10. `layout="stable"` is necessary for reproducibility but not default

I used `layout="stable"` on Graph to match `h05_mcmf.tex`. Without it, the force-directed layout reshuffles nodes based on random seed and the author has zero intuition about where A will land. The cookbook writer has to know to set this, and I only knew because I read another example first. For small graphs (<20 nodes) `layout="stable"` should probably be the default, or at least the docs should point loudly at it.

### F11. Edge selector `edge[(u,v)]` is order-sensitive on undirected graphs

I declared `("A","B")` in the edges list. A natural author reflex when relaxing B from the C side is to write `\recolor{G.edge[(B,C)]}{state=current}`. I happened to have declared `("B","C")` that way so it worked, but if I'd declared `("C","B")` I'd have had to be careful. There's no alias lookup for undirected graphs. An undirected edge really ought to be accessible as either `edge[(A,B)]` or `edge[(B,A)]`.

### F12. No way to show "relax but no update" cleanly

When I pop D and consider D–F, that's a true relaxation (it updates `dist[F]`). But when I pop F and look at E (already visited), the classic Dijkstra pseudocode still *checks* the edge and rejects it — there's no visual idiom for "we examined this edge and it didn't help". I just skipped narrating those checks, but pedagogically they're the whole point of the `d[u] + w < d[v]` line.

## Feature requests surfaced

Ordered roughly by value-for-effort from an author point of view:

1. **`PriorityQueue` primitive** (resolves F1, F6). Min/max, rebalances on push/pop, highlights the current head. Removes 2–3 ceremonial frames per Dijkstra/Prim/A* animation.
2. **Weighted edges on `Graph`** (resolves F4). `edges=[("A","B",4), ("A","C",2), ...]` with a `show_weights=true` flag. Dijkstra, Prim, Kruskal, Bellman-Ford, Floyd-Warshall, MST are all essentially unusable without this.
3. **Fix whole-shape `\apply` warning** (resolves F2). `_validate_expanded_selectors` should treat `target_key == shape_name` as the "whole shape" selector and skip node-level validation. This is one conditional in `emitter.py` around line 326.
4. **`Array.labels` accepts comma-separated lists** (resolves F3). Extend `_parse_index_labels` with a third pattern: if the string contains `,`, split on `,` and return the list (trimming whitespace). Raise `E1xxx` when length mismatches `size`.
5. **Undirected edge selectors normalise both orders** (resolves F11). When `directed=false`, `edge[(B,A)]` should resolve to the same element as `edge[(A,B)]`.
6. **Queue enqueue overflow raises `E1xxx`** (resolves F8). Silent truncation is the wrong default.
7. **Named states for graph animation** (resolves F5, F12). A `frontier` / `pending` state color that's distinct from both `idle` and `current` would make PQ-based algorithms visually clean.
8. **`layout="stable"` becomes the default for `n <= 20`** (resolves F10). Or rename it to `layout="deterministic"` and warn when the implicit `force` layout is used on small graphs.
9. **`label` vs `labels` rename** (resolves F9). `caption=` for the whole-shape title and `cell_labels=` for the per-index labels would eliminate the collision.

## Author effort

- **.tex size**: 157 lines, 17 `\step` blocks (roughly one per relax/pop). Counting narrate-only frames, visual-change frames, and ceremonial "stale pop" frames:
  - 1 intro frame (problem statement)
  - 1 init frame
  - 8 substantive relax/pop frames
  - 3 ceremonial "stale entry skipped" frames (F1 tax)
  - 2 bookkeeping "reset edge color" frames
  - 1 intermediate narration-only frame
  - 1 final shortest-path-tree frame
- **Frames that would disappear with a real `PriorityQueue` primitive**: 3.
- **Frames that would be visually clearer with weighted edges**: all 17.
- **Time estimate**: ~35 minutes for someone who has read 2 existing cookbook examples and the `graph.py` / `queue.py` / `array.py` source. Without source-reading, probably 60–90 minutes because the `labels` gotcha (F3), the bare-shape warning (F2), and the Stack-vs-Queue API divergence (F6) each cost a compile-inspect-fix cycle.
- **Compile cycles to reach the current state**: 1 successful compile on first try (2 pre-existing warnings, no blockers).

## Severity summary

| # | Friction | Severity | Blocker? | Workaround exists? |
|---|---|---|---|---|
| F1 | No `PriorityQueue` primitive | HIGH | No | Use `Queue`, manually manage order, 3 wasted frames |
| F2 | Whole-shape `\apply` false-positive warning | MEDIUM | No | Ignore the warning (but noise is demoralising) |
| F3 | `Array.labels` silently drops comma lists | HIGH | No | Rewrite narration to use numeric indices — loses semantics |
| F4 | Graph edges have no weight labels | HIGH | No | Cram weights into narration text |
| F5 | No `frontier` / `pending` state | MEDIUM | No | Toggle edges to `idle` between steps (visually flashes) |
| F6 | Queue `dequeue=true` undocumented, inconsistent with Stack `pop=N` | LOW | No | Read source |
| F7 | Queue never visually shrinks on dequeue | LOW | No | Use large capacity and hope |
| F8 | Queue enqueue overflow is silent | MEDIUM | No | Manual capacity accounting |
| F9 | `label` / `labels` / per-cell `label` naming collision | LOW | No | Just memorise it |
| F10 | `layout="stable"` isn't default | LOW | No | Know to set it |
| F11 | Undirected edge selectors order-sensitive | LOW | No | Stick to declared order |
| F12 | No idiom for "relaxed but no update" | LOW | No | Skip that narration |

**Blockers**: none. The animation compiles and renders. But of 12 friction points, 3 are HIGH severity and specifically hit this algorithm category (weighted graph algorithms) hard. An author trying to build Prim, Kruskal, Bellman-Ford, Floyd-Warshall, or A* would run into the same three HIGH items (F1, F3, F4) plus probably F11. Until weighted edges and a `PriorityQueue` primitive exist, Scriba's `Graph` primitive is really only suited for unweighted traversal (BFS/DFS) and flow network visualisations where weights live in narration.

**Key source references**:

- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/graph.py` — no weight rendering
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/array.py:515–532` — label parser fallback silently returns numeric indices
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/queue.py:122–144` — enqueue/dequeue API, silent overflow
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/emitter.py:312–342` — `_validate_expanded_selectors` false-positive on whole-shape apply
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/emitter.py:441` — `set_state` fall-through triggering a second warning
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/scene.py:524–541` — `_apply_apply` stores whole-shape params under bare key
- `/tmp/completeness_audit/06-dijkstra.tex` — final source
- `/tmp/completeness_audit/06-dijkstra.html` — rendered output (17 frames, 2263 lines)
- `/tmp/completeness_audit/06-dijkstra.log` — compile log
