# Completeness Audit 07: Author a Segment Tree with Lazy Propagation

Agent 7/14. Scriba v0.5.1 @ eb4f017. Date 2026-04-11.

## Scope

Simulate an editorial author using the Scriba DSL cookbook workflow to animate
a classic competitive-programming data structure: a segment tree with lazy
propagation supporting range-add + range-sum on an array of 8 elements. The
author needs a dual-view visualization (the underlying array plus the tree),
per-node metadata that changes over time (running sum and a lazy tag), and a
visible pushdown animation where dirty subtrees become clean.

Prior convex-hull audits flagged: API inconsistency, silent auto-fix on bad
input, manual loop unroll, and warning noise. Goal here: see whether those
friction patterns bite again for a harder data-structure animation, and find
the new ones that only a non-trivial algorithm surfaces.

No files in `scriba/` or `examples/` were modified. One probe file was written
to `/tmp/completeness_audit/` to test whether `\annotate` is wired to the Tree
primitive.

## Algorithm being animated

Array `a = [1, 2, 3, 4, 5, 6, 7, 8]`. Segment tree storing subtree sums.
Operations demonstrated in sequence:

1. Build tree from the array.
2. Range update `a[2..5] += 3`. Fully-covered nodes `[2,3]` and `[4,5]` get a
   lazy tag `+3`; their subtrees are left stale on purpose.
3. Range sum query over `a[3..6]`. When descent hits a tagged node, push the
   tag down to children (apply to their sums, accumulate into their own lazy
   slot), then clear the tag on the parent and continue.
4. Expected result: `7 + 8 + 9 + 7 = 31`.

Visual goals:

- Array primitive shows `a` at the top.
- Tree primitive shows the segment tree with running sums baked into labels.
- A second Array primitive (`L`) acts as a parallel lazy-tag table, one cell
  per internal-node DFS id.
- `state=dim` marks stale subtrees; `state=current`/`good` marks the path
  currently being walked and the nodes that contribute to the query answer.

## Final .tex (inline)

`/tmp/completeness_audit/07-segtree-lazy.tex`, 105 lines, 15 steps:

```latex
\begin{animation}[id="segtree-lazy", label="Segment Tree with Lazy Propagation -- Range Add + Range Sum"]
\shape{A}{Array}{size=8, data=[1,2,3,4,5,6,7,8], labels="0..7", label="Array a[0..7]"}
\shape{T}{Tree}{data=[1,2,3,4,5,6,7,8], kind="segtree", show_sum=true, label="Segment tree (sum)"}
\shape{L}{Array}{size=15, data=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], labels="0..14", label="Lazy tags (by DFS order)"}

\step
\narrate{Segment tree with lazy propagation supports range update + range query in O(log n). ...}

\step
\recolor{T.node["[0,7]"]}{state=done}
\recolor{T.node["[0,3]"]}{state=done}
... (full build — 15 recolors, one per node)
\recolor{A.all}{state=done}
\narrate{Build phase. Root [0,7]=36, left [0,3]=10, right [4,7]=26. ...}

\step
\highlight{A.range[2:5]}
\recolor{T.node["[0,7]"]}{state=current}
\recolor{T.node["[0,3]"]}{state=current}
\recolor{T.node["[4,7]"]}{state=current}
\narrate{Range update: add 3 to a[2..5]. ...}

\step
\recolor{T.node["[2,3]"]}{state=good}
\recolor{T.node["[4,5]"]}{state=good}
\apply{L.cell[4]}{value="+3"}
\apply{L.cell[10]}{value="+3"}
\recolor{L.cell[4]}{state=good}
\recolor{L.cell[10]}{state=good}
\narrate{[2,3] and [4,5] are FULLY covered by [2,5]. ... update their subtree sums: [2,3]=5+6=11 and [4,5]=9+6=15. ...}

... (pushdown and query steps follow the same pattern)

\end{animation}
```

Full file has 15 `\step` blocks. The complete unabridged file is on disk at
`/tmp/completeness_audit/07-segtree-lazy.tex`.

## Compile result

```
$ uv run python render.py /tmp/completeness_audit/07-segtree-lazy.tex -o /tmp/completeness_audit/07-segtree-lazy.html
Rendered 1 block(s) -> /tmp/completeness_audit/07-segtree-lazy.html
```

Clean compile, first try, zero warnings. This looks good but is misleading —
see friction points below. The HTML renders, the animation plays, but several
things the author promised in `\narrate{}` are simply not visible in the SVG.

## Friction points

### F1. Tree node labels are frozen at `\shape` time — no way to show changing sums (CRITICAL)

The biggest hit. `Tree._init_segtree()` at
`scriba/animation/primitives/tree.py:365-370` precomputes every node's sum
once and stores it in `self.node_labels` as the string `"[lo,hi]=<sum>"`.
`emit_svg()` then reads `self.node_labels.get(node_id, str(node_id))` on every
step (line 514), so the label is the **same** on every frame.

Meanwhile the DSL has no `\setvalue`, no `\relabel`, no mutate-label command
for tree nodes. `PrimitiveBase.set_value()` exists (`base.py:213`) but
`Tree.emit_svg()` never calls `self.get_value(...)` — only Array and friends
do. So even if you squeeze a value in via `\apply{T.node[...]}{value=...}`,
the Tree renderer ignores it.

Consequence for this example: my narration says "root `[0,7]` grows from 36
to 43 after range add", but the rendered SVG shows `[0,7]=36` on every single
frame. Verified:

```
$ grep -o '\[0,7\]=[0-9]*' 07-segtree-lazy.html | sort -u
[0,7]=36    (all 15 steps)
[0,7]=15    (false positive — substring of narration "15 steps")
```

Same for every other internal node. The whole point of lazy propagation is
that the sum field on a tagged node reflects the pending update; Scriba
cannot show this. The author is forced to carry the "true" sum values in
`\narrate{}` prose and hope the viewer reads it — which defeats the entire
animation medium.

A working cookbook example would require either:
- a `\relabel{T.node[id]}{text}` command, or
- `Tree.emit_svg()` honoring `self.get_value(suffix)` as Array does, or
- a live "metadata slot" on each node.

### F2. `\annotate` is a silent no-op on Tree nodes (HIGH, silent failure)

The DSL exposes `\annotate{target}{label=..., position=..., color=...}`
(`grammar.py:782`) and it parses fine for a Tree target like
`T.node["[2,3]"]`. The annotation is stored on the primitive via
`PrimitiveBase.set_annotations()` (`base.py:239`). But `Tree.emit_svg()`
(`tree.py:448-540`) never reads `self._annotations`. Array reads it and
renders arrows/badges; Tree does not.

Probe test (`/tmp/completeness_audit/07b-probe.tex`):

```latex
\shape{T}{Tree}{data=[1,2,3,4], kind="segtree", show_sum=true}
\step
\annotate{T.node["[0,1]"]}{label="+3", position=above, color=warn}
\narrate{probe}
```

Output: compile succeeds, zero warnings, and the HTML contains zero `+3`
text and zero `scriba-annotation*` elements. Absolutely nothing is rendered.
No diagnostic, no hint that the command was a no-op.

This is the natural mechanism an author would reach for to put a lazy tag
above a tree node. It looks like it works. It silently doesn't. This is
**exactly** the "silent auto-fix" anti-pattern from the prior convex-hull
audit, wearing different clothes — the DSL accepts the input, the pipeline
runs, the result is wrong in a way the author cannot detect without inspecting
the SVG byte-for-byte.

### F3. No way to make the lazy-tag view actually parallel to the tree (MEDIUM)

I worked around F1/F2 by introducing a second Array primitive `L` with 15
cells indexed "by DFS id" and stuffing `"+3"` into it via `\apply`. This
works — `\apply{L.cell[4]}{value="+3"}` does render — but it is cosmetic
parallelism, not real parallelism:

- The author has to hand-pick which cell index corresponds to which tree
  node and keep the mapping straight mentally. (`[2,3]` is node index 4 in
  my DFS. `[4,5]` is node index 10. Nothing enforces this.)
- The lazy-tag array and the tree are physically separated on screen; the
  viewer has to visually reconcile them.
- A renaming of tree structure would silently break the mapping with no
  validation.
- Array index labels are integers `0..14`, not segment ranges, so the two
  views don't share a vocabulary.

What the author actually wants is a way to decorate each tree node with a
sibling badge showing its lazy tag — i.e. what F2's `\annotate` should have
done.

### F4. No `show_lazy` / `metadata` option on `Tree{kind="segtree"}` (MEDIUM)

`Tree` has one knob for node metadata: `show_sum: bool` (`tree.py:265`). It
bakes static sums into labels. That's it. There is no `show_lazy`, no
`show_count`, no way to pass a dict of per-node extra labels, no way to pass
a formatter callback. Any segment-tree variant beyond plain static sum
(lazy, persistent, merge-sort tree, Li Chao, …) is visually indistinguishable
from a plain segtree after the first frame.

For comparison, `h08_persistent_segtree.tex` also suffers from this — it
animates path-copy via `state=` coloring but the "new sum on a new version"
text is carried in narration only; the SVG labels remain the V0 values. So
this gap already shows up in the shipped cookbook, not just in my audit.

### F5. Tree build requires enumerating every node by hand (LOW, manual-unroll echo)

Step 2 (Build) needed 15 `\recolor` calls — one per node — to color the tree
green. `T.all` would be natural but there is no `Tree.all` selector
(`Tree.SELECTOR_PATTERNS` at `tree.py:254` lists only `node[{id}]`,
`edge[({u},{v})]`, `all`; `validate_selector` actually accepts `"all"` but
`set_state` only fires for explicit suffixes). In convex hull the author had
to unroll hull-edge colorings by hand; here the author unrolls node
colorings. Same smell.

`\foreach` exists but iterating "every tree node" requires the author to
type out the node-id list, which is the very thing they wanted to avoid.

### F6. `show_sum` labels have a structural conflict with `\recolor` text color (LOW)

Once `show_sum=true`, labels are long strings like `[0,7]=36`. On a `state=
current` node (light fill, dark text) this is fine, but on small node radii
the text is clipped — `Tree.__init__` computes a radius of
`min(20, width/(2*nodes))`, which for 15 nodes gives radius 13. At radius 13
the `[0,7]=36` string overflows the circle. Visible in the rendered HTML.
The author has no way to shrink font or move the label outside the circle.

### F7. Node selectors require triple-quoting (LOW, ergonomic)

`\recolor{T.node["[0,7]"]}{...}` — the inner `"[0,7]"` must be a quoted
string because the selector parser otherwise thinks `[0,7]` is an index
expression. This is correct behavior but easy to mistype. `T.node[0,7]`
looks inviting and silently fails selector validation without a targeted
hint. Not a blocker, but friction.

## Feature requests

### FR1. Live per-node metadata on Tree (resolves F1, F2, F3, F4)

Add one of:

```latex
\shape{T}{Tree}{data=[...], kind="segtree", show_sum=true, show_lazy=true}
\apply{T.node["[2,3]"]}{value="11", meta="+3"}
```

or a dedicated command:

```latex
\relabel{T.node["[2,3]"]}{text="[2,3]=11", badge="+3"}
```

`Tree.emit_svg()` should then call `self.get_value(suffix)` / `get_meta` and
render both the primary label and an optional badge adjacent to the node.
Concretely: add a second line of text below each circle (where there is
already whitespace in the Reingold-Tilford layout) for the badge. This one
change unlocks every stateful tree animation: lazy propagation, splay
rotations, DSU rank updates, treap priorities, persistent version numbers.

### FR2. Wire `\annotate` to Tree primitives (resolves F2)

Either:
- Implement annotation rendering in `Tree.emit_svg()` analogous to
  `ArrayPrimitive.emit_svg()` (arrows + labels pinned to node positions).
- Or, at minimum, emit a ValidationError at parse time when `\annotate`
  targets a primitive that doesn't support annotations, with code E14xx and
  a hint pointing to alternatives.

The current silent no-op is the worst of both worlds.

### FR3. `T.all` and subtree selectors

`\recolor{T.all}{state=done}` should work. For lazy-propagation
visualizations, a `T.subtree[id]` selector ("every node reachable from this
one") would let the author color the dirty subtree under a tagged node in
one command instead of enumerating descendants.

### FR4. Automatic lazy/sum tracking for `kind="segtree"`

If the runtime already knows it is a segment tree (which it does, via
`kind="segtree"` and `build_segtree`), Scriba could expose a domain command:

```latex
\segtree_update{T}{2}{5}{+3}
\segtree_query{T}{3}{6}
```

that drives the state/value/lazy changes automatically, preserving correct
sums and lazy tags without the author having to hand-maintain them in
narration prose. This would turn a 100-line hand-rolled .tex into maybe 10
lines of intent, and would make the rendered animation actually correct
rather than correct-only-in-narration.

### FR5. Diagnostic for commands that target unsupported primitives

Running `\annotate` on Tree, `\cursor` on Array, `\apply{…}{value=…}` on
Tree — each of these either silently drops or errors in confusing ways. A
uniform validation pass ("primitive X does not accept command Y") would kill
an entire class of silent-wrong bugs.

## Author effort metrics

- Reading prior art: `h08_persistent_segtree.tex` (63 lines) + `h10_hld.tex`
  (74 lines) + relevant primitive source. ~8 minutes.
- Understanding the Tree API's limits (label immutability, missing annotate
  wiring, selector rules): ~12 minutes of reading `tree.py`, `base.py`,
  `grammar.py` plus one probe compile. This is the dominant cost and it is
  entirely re-discovery of tribal knowledge that the cookbook does not
  document.
- Writing the .tex: ~10 minutes, most of it bookkeeping the node list for
  the build step and matching lazy-array cell indices to tree-node DFS ids
  by hand.
- Compiling and debugging: 1 iteration, clean first compile. Zero warnings.
  Zero errors.
- Verifying the output was actually correct (i.e. noticing that the node
  labels never change even though the narration claims they do): ~6 minutes
  of `grep -o` spelunking against the emitted HTML. The fact that a clean
  compile does not imply a correct animation is itself a finding.

Total: ~35 minutes for a ~100-line cookbook entry whose rendered semantics
match the author's intent roughly 40%. The coloring is correct. The
metadata/value layer is not.

## Severity summary

| # | Severity | Friction |
|---|---|---|
| F1 | CRITICAL | Tree node labels are frozen at shape time; no DSL command can change a sum, count, or lazy tag after init. Every stateful tree animation lies in its narration. |
| F2 | HIGH | `\annotate` on tree nodes silently no-ops. No warning, no error, no rendered element. Parses and runs to completion. |
| F3 | MEDIUM | No mechanism to display per-node metadata adjacent to a tree node — author must fake it with a parallel Array and maintain the index mapping in their head. |
| F4 | MEDIUM | `Tree{kind="segtree"}` exposes `show_sum` only; no equivalent for lazy, count, or custom labels. |
| F5 | LOW | `T.all` is not a write target; build colorings have to be unrolled by hand. Same class of manual-unroll smell as convex hull. |
| F6 | LOW | Dense trees with `show_sum=true` clip labels inside the circles; no font/placement knob. |
| F7 | LOW | Selector requires `T.node["[lo,hi]"]` with inner quotes; easy to mistype and the failure mode is not well signposted. |

Prior-audit echo check:

- **API inconsistency** — confirmed. Array honors `get_value`/`set_value`
  and `_annotations`; Tree ignores both. Same pipeline, divergent contracts.
- **Silent auto-fix** — confirmed, worse form. Here the silent behavior is
  *silent drop*, not auto-correct: `\annotate` on Tree accepts input and
  emits nothing.
- **Manual loop unroll** — confirmed. `\recolor{T.all}` does not propagate;
  the build step needed 15 hand-written lines.
- **Warning noise** — not present for this example. The segtree run produced
  zero warnings. This is the only convex-hull pattern that did NOT repeat,
  and the reason is that I never triggered a Plane2D selector path.

Bottom line: the Tree primitive is expressive enough for *structure* (layout,
state coloring, recursion visualization) but not for *values*. For any
algorithm whose interesting state lives on the nodes — lazy propagation,
splay trees, Fenwick within segtree, persistent versions, treap priorities,
Li Chao line stacks — a Scriba author today has to push the value narrative
into `\narrate{}` prose. That is exactly the opposite of what an animation
medium is for.
