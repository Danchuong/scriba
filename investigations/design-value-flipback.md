# Design — `value_change` Flip-Back on Value-Not-Honoring Primitives

**Scope:** the ADJACENT class from `investigations/audit-node-targeting-class.md`
finding #4 — the differ emits a real `value_change` transition for primitives
whose `emit_svg` ignores the applied value, so the runtime JS stamps the value
into a `<text>` and the server's fs-snap frame (which never rendered it) reverts
it → a flip-back flash.

**Read-only design case. No implementation.** The lead reviews before any bump.

**Evidence grades:** Confirmed = cite `path:line` + rendered SVG / extracted `tr`
manifest • Deduced = code-path reasoning • Hypothesized = plausible, unproven.

---

## Root cause (Confirmed) — the value channel is honored in two independent places, and they can disagree

An `\apply{X}{value=V}` splits into **two** independent downstream paths:

1. **Differ / motion path.** `scene._apply_apply` records `value=new_value` into
   `shape_states` **unconditionally** — no primitive is consulted
   (`scene.py:978-1015`, esp. `:1010`). The renderer copies it into the frame
   (`renderer.py:426-427` `entry["value"]=ts.value`), and the differ turns any
   value delta into a `value_change` Transition (`differ.py:140-149` new-element,
   `differ.py:223-234` both-exist). **Nothing in this path checks whether the
   primitive can render the value.**
2. **Render path.** A best-effort pre-pass calls `prim.set_value(suffix, val)`
   (`_frame_renderer.py:105-124`). Whether that surfaces in the SVG depends
   entirely on whether the primitive's `emit_svg` reads it back
   (`get_value` / a mutated render field).

When path 2 is a no-op (emit ignores the value) but path 1 still fires, the
manifest carries a `value_change` the server SVG never honored. At runtime the
handler writes it in:

```js
// scriba.js:183  (handler selection 164-181)
if(txt&&toVal!=null&&String(toVal).indexOf('$')===-1){txt.textContent=toVal;}
```

`txt` resolves to the target group's `[data-role="value"]` node, else the **last
`<text>`** (`scriba.js:172-176`). The value stamps in, then the fs-snap replaces
`innerHTML` with the server SVG (which shows the original) → **flip-back**.
`fs`/needs-sync is set whenever the frame SVG differs at all — even only in the
narration `<title>` (`_html_stitcher.py:664`), which it almost always does — so
the revert reliably fires.

Note `value` is a **universally-accepted** apply key (`_GENERIC_APPLY_KEYS =
{value, label}`, `_frame_renderer.py:727`), so it **never** raises `E1105` on the
key today — even for a primitive that does nothing with it. That is precisely the
"accepted but does nothing → silently vanishes from the render" anti-pattern the
project's own guard exists to kill (`SCRIBA-TEX-REFERENCE.md:352, :455`;
`_version.py:286`).

---

## PART 1 — Scope: every value-accepting primitive

Method: render `\apply{part}{value=ZZZ}` (numeric `9`/`99` for numeric-semantics
cells), extract the `tr` manifest and count the token inside server-rendered
`<text>/<tspan>/<foreignObject>` across frames. Probes + extractors in scratchpad.

| Primitive · part | `value=` renders in server SVG? | differ emits `value_change`? | target `<g>` exists at runtime? | **Flip-back?** | grade |
|---|---|---|---|---|---|
| **Stack** `s.item[i]` | **NO** — emit renders `item.label` only | YES `["s.item[0]","value",null,"ZZZ",…]` | YES (1 `<text>` `['A']`) | **YES** | Confirmed |
| **Graph** `g.node[name]` | **NO** — node emit has no `get_value` | YES `["g.node[A]",…]` | YES (1 `<text>` `['A']`) | **YES** | Confirmed |
| **NumberLine** `nl.tick[i]` | **NO** — tick = axis coordinate | YES `["nl.tick[2]",…]` | YES (1 `<text>` `['2']`) | **YES** | Confirmed |
| **CodePanel** `c.line[i]` | **NO** — emit renders `self.lines[i]` | YES `["c.line[1]",…]` | YES (2 `<text>` `['1','alpha']`; stamps last=code) | **YES** | Confirmed |
| Array `a.cell[i]` | YES (`get_value`, array.py:532) | YES | YES | no | Confirmed |
| Grid `g.cell[r][c]` | YES (grid.py:334) | YES | YES | no | Confirmed |
| Queue `q.cell[i]` | YES (`self.cells[idx]`, queue.py:247-256) | YES | YES | no | Confirmed |
| Deque `d.cell[i]` | YES (inherits Queue) | YES | YES | no | Confirmed |
| Tree `T.node[id]` | YES (tree.py:1004; docs:1272) | YES | YES | no | Confirmed |
| Forest `f.node[i]` | YES (forest.py:577) | YES | YES | no | Confirmed |
| Hypercube `L.subset[i]` | YES (hypercube.py:190) | YES | YES | no | Confirmed |
| HashMap `hm.bucket[i]` | YES (`_bucket_values`, hashmap.py:349) | YES | YES | no | Confirmed |
| VariableWatch `vars.var[name]` | YES (`_values`, variablewatch.py:355) | YES | YES | no | Confirmed |
| LinkedList `ll.node[i]` | YES (`self.values[idx]`, linkedlist.py:187,418) | YES | YES | no | Confirmed |
| Graph **edge** `g.edge[(u,v)]` | YES (graph.py:1945; docs:1125) | YES | YES | no | Confirmed |
| DPTable `dp.cell[i]` | YES (dptable.py:443,507) | YES | YES | no | Deduced (audit-Confirmed) |
| TraceTable `t.cell[k][j]` | YES (tracetable.py:412) | YES | YES | no | Deduced (audit-Confirmed) |
| Equation `E.line[i]` | YES (equation.py:307-314) | YES | YES | no | Deduced |
| **Bar** `h.bar[i]` | numeric YES (bar.py:222-240) / **non-numeric NO** (soft-drop) | YES | YES | **only on non-numeric** | Confirmed |
| **Matrix** `m.cell[r][c]` | numeric YES (matrix.py:530-545) / **non-numeric NO** | YES | YES | **only on non-numeric** | Confirmed |
| Plane2D `p.point[i]` | NO — E1115 invalid selector | YES (spurious) | **NO element** | no (runtime no-op) | Confirmed |
| MetricPlot `plot.point[i]` | NO — E1115 invalid selector | YES (spurious) | **NO element** | no (runtime no-op) | Confirmed |

**Four primitives are the flip-back class: Stack, Graph (node), NumberLine,
CodePanel.** All four emit a real `value_change` whose target `<g>` exists, so
the runtime stamps then reverts. CodePanel additionally has 2 texts
`[lineNo, code]` and is untagged, so the last-`<text>` fallback stamps the **code
line** (not the number) — a positional detail on top of the flip-back.

**Two secondary sub-findings (Confirmed):**

- **Bar / Matrix non-numeric** (`h.bar[0]`/`m.cell[0][0]` `value=ZZZ`): emit
  soft-drops a non-numeric value to the declared datum (numeric-semantics cells),
  but the manifest still carries `value_change` with the raw string → flip-back
  **only** for a non-numeric value (an author-error input; numeric values are
  honored end-to-end). Narrower than the four, same mechanism.
- **Spurious `value_change` for E1115-invalid selectors** (Plane2D/MetricPlot
  `point[i]`; also `g.node[<index>]` in index form): `scene._apply_apply` records
  the value even though `set_value` rejected the selector (E1115), so the differ
  emits a `value_change` for a target that has **no DOM element**. Runtime is a
  no-op (nothing to stamp), so no visible flash — but the manifest is dishonest.
  Same root: path 1 records unconditionally.

---

## PART 2 — Fix decision per primitive

**Decision rule (from evidence):** the honoring primitives (Array, Tree, Queue,
LinkedList, HashMap, Graph-edge, …) each have a **designed per-element value
display** that `value=` feeds. The four flip-back primitives **do not** —
confirmed structurally, not just "emit forgot to read it":

- **Stack** `StackItem` carries a `value` slot (`stack.py:46-53`) yet emit renders
  only `label` (`stack.py:141-143`); even the documented `push={label,value=3}`
  renders no value (probe: pushed item shows `['C']`, no `3`). There is **no
  value display slot at all.**
- **NumberLine** ticks are axis coordinates set by `domain`/`ticks`/`labels`
  (`SCRIBA-TEX-REFERENCE.md §7.6`); a per-tick value is not a coordinate.
- **CodePanel** `SCRIBA-TEX-REFERENCE.md:1466` states **"Operations: none"**;
  lines are static source.
- **Graph** documents `value=` for **edges only** (`:1125` dynamic edge labels);
  nodes are name-keyed identities used by selectors.

So `value=` on these parts is an **op the primitive does not support**. Under the
project's stated contract ("an op the primitive does not support fails loudly at
build rather than vanishing from the render", `:455`) the honest fix is to
**reject it (E1105)** — not to silently suppress the emit (which is the same
silent-swallow, just moved) and not to invent a value display the primitive was
never designed to show.

| Primitive | Decision | Why (evidence) |
|---|---|---|
| **Stack** `s.item[i]` | **B — reject (E1105)** | No value display slot exists; even own `push` value is unrendered (Confirmed). Option A = **new feature** (add a value sub-label to every item) → re-bless all Stack goldens; disproportionate. |
| **NumberLine** `nl.tick[i]` | **B — reject (E1105)** | Tick label **is** the coordinate; §7.6 lists no value op. Option A is mechanically feasible (tick has a text slot) but **semantically wrong** — it would print `ZZZ` where the axis value belongs. |
| **CodePanel** `c.line[i]` | **B — reject (E1105)** | §7.11 "Operations: none"; static source. Option A (mirror Equation `line[i]` override) is coherent **only if** code-line rewrite becomes a wanted feature — not today. |
| **Graph** `g.node[name]` | **B — reject (E1105)** primary; **A viable** | Docs scope value= to edges. **A is the strongest of the four**: the node already renders a text slot and Tree/Forest set precedent (`tree.py:1004`, `forest.py:577`, docs:1272 "value **replaces** that node's display"). Choose A **iff** per-node computed-value display (e.g. Dijkstra distances) is wanted; else B for docs-consistency. |
| Bar / Matrix (non-numeric) | **separate — soft-drop is by design**; consider a numeric-validation warning | Numeric path is honest. A non-numeric value= on a numeric cell is author error; today it silently soft-drops **and** flip-backs. Out of the core-4 scope; flag for a follow-up (warn/E-code on non-numeric), not part of this fix. |

### Why NOT "suppress the differ emit"
The mandate floated making the differ skip `value_change` for these targets.
**Rejected:** the author wrote `value=` and would get *no render and no error* —
the exact silent-swallow the E1105 regime (0.26.2 class) was built to eliminate.
Suppression also mutates the `tr` manifest bytes (a runtime-contract change →
`SCRIBA_VERSION` bump) for a strictly-worse UX. E1105 is both smaller and honest.

### Structural mechanism for B (design, not implementation)
1. Add a capability to `PrimitiveBase`: `renders_value(suffix: str) -> bool`,
   **default `True`** (mirrors the existing `validate_selector` shape,
   `base.py:773`). Override to `False` on the non-rendering parts:
   Stack (`item[*]`), NumberLine (`tick[*]`), CodePanel (`line[*]`), and Graph
   returns `suffix.startswith("edge[")` (edges keep the documented feature; nodes
   reject).
2. **A dedicated pre-differ validation pass** raises `E1105` when a
   `shape_states` value targets a part with `renders_value == False`. It must NOT
   live inside `set_value`: the existing value pre-pass wraps `set_value` in
   best-effort `try/except: pass` (`_frame_renderer.py:122-124`), which would
   swallow the raise. It must run **before** the differ so the render aborts and
   no dishonest `value_change` is ever produced.
3. Reuse the existing helper/hint machinery (`_animation_error("E1105", …,
   hint=…)`, `_frame_renderer.py:766`); hint steers to the right verb, e.g.
   *"Stack items have no per-item value; use `push={label,value}` or `\recolor`"*,
   *"NumberLine ticks are set by `domain`/`labels`"*, *"CodePanel has no ops"*,
   *"Graph value= applies to edges; nodes are identified by label"*.
4. The same `renders_value` gate (or gating scene's value-record on
   `validate_selector`) also closes the **spurious-manifest** sub-finding
   (Plane2D/MetricPlot) — defense in depth, optional to this ticket.

Option A, where chosen (Graph node only, if desired): make node `emit_svg` read
`override = self.get_value(node_key)` and render it in place of the id label —
byte-for-byte the Tree/Forest pattern (`tree.py:1004`). `get_value` returns
`None` when unset → the id renders unchanged → **existing goldens byte-identical**.

---

## PART 3 — Golden / version impact

**No example or golden applies `value=` to Stack item, Graph node, NumberLine
tick, or CodePanel line** (corpus grep: value= on nodes appears only for
Tree/LinkedList/Heap — all honoring). This collapses the impact for BOTH options.

| | Option B (reject, all four) — **recommended** | Option A (render — Graph node only, if wanted) |
|---|---|---|
| Existing golden SVG bytes | **Byte-identical** (nothing in corpus uses these) | **Byte-identical** (`get_value` unset → id fallback) |
| `tr` / `fs` manifest bytes | Unchanged for valid docs | Unchanged (`value_change` still emitted, now honest) |
| `scriba.js` runtime | **Untouched** | **Untouched** (handler already stamps correctly) |
| **`SCRIBA_VERSION`** | **No bump** — build-time error path, nothing baked into HTML | **No bump** — additive server-render; no bytes change for existing docs (contrast 0.26.4, which bumped because data-role tag bytes changed existing docs) |
| Golden re-bless | **None** | **None** (only *new* value=node docs render differently) |
| Package version | patch/minor (new error path) + `_version.py` narrative note | minor (new feature) |
| Test churn | Revise `test_generic_value_label_never_flagged` — `value` becomes *conditionally* generic (allowed where `renders_value`, else E1105); add RED E1105 tests | Add render assertion + a doc using node value= |

**Golden-character expectation:** with Option B, `pytest tests/golden/...` stays
green with **zero re-bless** — the full corpus is byte-identical because no golden
exercises the rejected path; the only new failures are the intended RED E1105
tests until the guard lands. Stack "render" (A) is explicitly **disfavored**: it
would add a value sub-label to every item and re-bless the entire Stack golden set
for a feature nobody requested.

---

## PART 4 — RED-first test plan

Order: write RED, confirm they fail on `HEAD`, then make green.

**A. Flip-back repro (integration, one per flip-back primitive).** Render
`\shape` + `\apply{part}{value=ZZZ}`; assert the honest post-fix contract:

- *Under Option B:* `render` **raises `E1105`** for `s.item[0]`, `g.node[A]`,
  `nl.tick[2]`, `c.line[1]` — naming the primitive and a corrective hint. RED
  today (currently renders silently, emitting the dishonest `value_change`).
- *Manifest honesty:* the emitted `tr` for that step contains **no**
  `["…","value",…,"value_change"]` for the rejected target (because render
  aborts). Guards the flip-back at its source.

**B. Non-regression for honoring primitives (must stay green / stay working).**
`\apply{a.cell[0]}{value=ZZZ}`, `\apply{T.node[id]}{value="dp=1"}`,
`\apply{g.edge[(A,B)]}{value="3/10"}`, `\apply{q.cell[0]}{value=ZZZ}`,
`\apply{ll.node[0]}{value=ZZZ}` → server SVG **renders the value** AND the
manifest emits a `value_change` (honest). These MUST NOT start raising E1105 —
they are the regression fence around the `renders_value` default/override split.

**C. Guard-surface test.** Update `test_generic_value_label_never_flagged` to the
new contract: `value=`/`label=` are accepted on rendering parts, and `value=` on a
non-rendering part raises E1105 with a hint (mirrors
`test_typo_key_on_array_raises_e1105`).

**D. Differ unit (`tests/animation/test_differ.py`).** Assert the manifest for a
Stack/NumberLine/CodePanel/Graph-node value delta — post-fix, the frame never
reaches the differ (render aborts), so cover it at the render/validation layer
rather than the differ (the differ stays kind-agnostic and untouched).

**E. (If Graph node → Option A instead.)** Swap Graph's B-tests for: `g.node[A]`
value= **renders** in server SVG (both frames show `ZZZ`, not `A`), manifest
`value_change` is honest, and an unset-value Graph golden is byte-identical.

**F. Sub-findings (optional, flag-only this ticket).** (1) Bar/Matrix non-numeric
value → today flip-backs; add a `xfail`/TODO documenting the desired warn. (2)
Plane2D/MetricPlot `point[i]` value= → asserts no spurious `value_change` once the
`validate_selector` gate is added.

---

## Conclusion

- **Flip-back class = four primitives: Stack `s.item[i]`, Graph `g.node[name]`,
  NumberLine `nl.tick[i]`, CodePanel `c.line[i]`** — each emits a real
  `value_change` whose target `<g>` exists but whose `emit_svg` renders no value,
  so the runtime stamp reverts (Confirmed by rendered SVG + extracted `tr`).
- **Recommended fix: Option B — reject `value=` on these parts with `E1105`**, via
  a `renders_value(suffix)` capability (default True; False for the four parts,
  edge-scoped True for Graph) checked in a **dedicated pre-differ validation pass**
  (not inside the best-effort `set_value`). It is the doc-and-philosophy-aligned,
  loud-failure fix; **Graph node** is the one defensible Option-A candidate
  (mirror Tree/Forest node-value override) if per-node value display is wanted.
- **Reject the "suppress the emit" option** — it re-creates the silent-swallow and
  churns the manifest contract.
- **Impact is minimal for either option:** no golden re-bless, **no
  `SCRIBA_VERSION` bump** (no corpus doc uses these paths; nothing is baked into
  HTML). Option B adds a build-time error path + a `test_generic_value_label`
  revision; Stack-render (A) is disfavored (whole-corpus re-bless for an
  unrequested feature).
- **Two Confirmed sub-findings** to log separately: Bar/Matrix **non-numeric**
  value flip-back (numeric is honest), and **spurious `value_change`** for
  E1115-invalid selectors (Plane2D/MetricPlot) — same root (scene records value
  unconditionally), both closable by the same gate.

**Confidence: HIGH.** Every primitive verdict is backed by a rendered SVG + an
extracted `tr` manifest (23 probes) and cross-checked against `emit_svg` source
and the TeX reference's documented per-primitive value surface. The one genuinely
open item is a **product choice, not a fact**: whether Graph nodes should *gain*
value display (A) or *reject* value= (B).
