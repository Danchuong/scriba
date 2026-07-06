# Audit — Positional Node-Targeting Class (value_change and its siblings)

**Scope:** Every runtime handler / code path in `scriba/animation/static/scriba.js`
that selects a **child DOM node by position / first-match** inside a
`data-target` (or `data-annotation`) group and **assumes its identity**, where
the group can hold more than one candidate.

**Evidence grades:** Confirmed = cite `path:line` + rendered DOM proof •
Deduced = code-path reasoning • Hypothesized = plausible, unproven.

---

## Hand-off Brief

- **The reported bug (JudgeZone #6), Confirmed:** `value_change` picked the
  FIRST `<text>` of the target `<g>` and stamped the new value onto it. On a
  two-text row (`<text>NAME</text><text>VALUE</text>`) that wrote the value onto
  the NAME. Root cause = positional child selection in a multi-node group.
- **The fix LANDED DURING this audit.** My first read of `scriba.js:165` showed
  the old `el2.querySelector('text')`; by the end of the sweep the working tree
  had `querySelector('text[data-role="value"]')` + a last-`<text>` fallback
  (`scriba.js:164-181`), and the emitter tags value nodes via
  `_text_render.py` `data_role=` (`hashmap.py:363`, `variablewatch.py:369`,
  `linkedlist.py:436`). This report documents BOTH the pre-fix class and the
  post-fix residuals.
- **One Confirmed sibling of the class: HashMap** — target group is
  `[indexText, valueText]`; the old code stamped the value onto the bucket
  **index**. Same failure mode as VariableWatch.
- **Critical counterexample: LinkedList.** Its node group is `[valueText,
  captionText]` — the value is **FIRST**, with a trailing `node[N]` caption
  **LAST**. The fix's own comment ("value is last in every affected layout —
  never the first", `scriba.js:169`) is **FALSE** here. A naive last-`<text>`
  fallback would have stamped the value onto the caption. LinkedList is safe
  **only because** the fix also tagged its value text with `data-role="value"`.
- **Verdict on the fallback:** the last-`<text>` fallback is NOT self-sufficient.
  It is completed by the three explicit `data-role="value"` tags. For the
  current corpus it is complete; the durable risk is a future multi-text value
  primitive added without the tag whose value is not last.
- **No value is ever strictly mid-list** (max 2 `<text>` in any live value
  target). The "both-first-and-last-miss-it" nightmare does not exist today.
- **Residual the fix does NOT close (LOW, cosmetic, pre-existing):** a **math**
  value renders as `<foreignObject data-role="value">`, but the primary selector
  is `text[data-role="value"]` — it does not match a foreignObject — so the
  100 ms scale-bounce animates the NAME/first node. The write is correctly
  skipped for `$...$`, so there is no corruption.

---

## PART 1 — Handler scan (`_applyTransition` + helpers)

Every branch and the helper it calls, classified by whether it picks a child by
position and whether that pick can mis-identify.

| Branch | `scriba.js` | What it selects | Acts on | Positional child-pick? | Verdict |
|---|---|---|---|---|---|
| `recolor` | 156-162 | `querySelector(sel)` = the `<g data-target>` | class swap on the **group** | No — group's own `className` | **SAFE** (identity = the group) |
| `value_change` | 164-181 | `text[data-role="value"]` → else last `<text>`; anim `foreignObject>div` | **writes** text + scale anim | **YES — this is the class** | Fixed for tagged primitives; math-fo anim residual (below) |
| `highlight_on` | 182-191 | `querySelector(sel)` = group | class add on **group** | No | **SAFE** |
| `highlight_off` | 192-199 | `querySelector(sel)` = group | class remove on **group** | No | **SAFE** |
| `element_remove` | 200-206 | `querySelector(sel)` = group | opacity anim on **group** | No | **SAFE** |
| `element_add` | 207-225 | `parsed.querySelector(sel)` = group; parent via keyed `[data-shape]` (216) | clones whole group; keyed parent | No (keyed, not positional) | **SAFE** |
| `position_move` | 226-243 | `querySelector(sel)` = group | transform on **group** | No | **SAFE** |
| `annotation_remove` | 244-250 | `_annEl(stage,target)` keyed by `data-annotation` | opacity anim on whole annotation | No (keyed) | **SAFE** |
| `annotation_add` | 251-321 | `_annEl` keyed; then `clone8.querySelector('path'/'polygon'/'text')` (274,281,283) | opacity / draw-on anim of those children | **YES** first-match children | **LOW** — single-candidate in corpus; animation-only (see below) |
| `annotation_recolor` | 322-332 | `_annEl(stage,target)` keyed | class swap on **group** | No | **SAFE** |
| `cursor_move` | 333-349 | `querySelector('[data-annotation=X]')` keyed | transform on whole element | No | **SAFE** |

**Helpers**

| Helper | `scriba.js` | Note |
|---|---|---|
| `_setInv` | 32 | `invp[q].innerHTML=v[q]` — positional **parallel-array** (panel _q_ ← `inv[q]`). Not a child-of-target pick; adjacent positional assumption. If `.scriba-invariant` DOM order ever diverges from `frames[i].inv` order, panels cross-fill. Out of this class; noted. |
| `_fadeInNewAnnotations` | 102-112 | iterates `[data-annotation]`, keyed. **SAFE** |
| `_annEl` | 135-151 | keyed `querySelector([data-annotation=…])` + solo/side recovery; first-match matters only if annotation keys duplicate (they are unique). **SAFE** |
| `_emphasize` | 396-415 | keyed `[data-target]`/`[data-annotation]`, class toggle on whole element. **SAFE** |
| `snapToFrame` / `_updateControls` / `_arrowheadAt` / `initSub` / `_changedTargets` / `_pulseTargets` | — | no per-child positional pick inside a target group. **SAFE** |

**`annotation_add` child-picks — Confirmed benign.** Every rendered
`[data-annotation]` group carries exactly `text=1 path=1 polygon=1` (proof:
`_vw.html`, `_hm.html`, `_linkedlist.html` annotation groups). The picks feed
opacity/stroke-draw only — a hypothetical multi-text/​multi-path annotation would
leave the extra node un-faded (cosmetic), never a value write. Emitters that key
`data-annotation` are single-text (`_svg_helpers.py:2078,2857`,
`_frame_renderer.py:986,1133`).

**Handler-scan result:** 11 `_applyTransition` branches + ~8 helpers scanned.
Positional child-picks = **`value_change`** (write + fo-anim; the class) and
**`annotation_add`** (3 sub-picks, animation-only, single-candidate). Every other
branch operates on the `data-target` group **as a whole** (class / opacity /
transform) or via **keyed** `[data-shape]` / `[data-annotation]` lookups.

---

## PART 2 — Renderer ambiguity (all value-accepting primitives)

For each value primitive I rendered a `value_change` and dumped the target
group's descendant `<text>`/`<foreignObject>` order (method: render `.tex` →
extract inline `frames[]` svg + `tr` manifest → parse group). "value-text
position" is where the value sits among plain `<text>` nodes.

| Primitive | value target | #`<text>` in group | value-text pos | `data-role="value"` tag | old first-`<text>` | landed selector | grade |
|---|---|---|---|---|---|---|---|
| **VariableWatch** | `vars.var[n]` | 2 `[name,value]` | **LAST** | YES (`variablewatch.py:369`) | picks NAME ✗ | role → **OK** | Confirmed |
| **HashMap** | `hm.bucket[i]` | 2 `[index,value]` | **LAST** | YES (`hashmap.py:363`) | picks INDEX ✗ | role → **OK** | Confirmed |
| **LinkedList** | `ll.node[i]` | 2 `[value,caption]` | **FIRST** | YES (`linkedlist.py:436`) | picks VALUE ✓ | role → **OK** (last-fallback would be **✗**) | Confirmed |
| CodePanel | `code.line[i]` | 2 `[lineNo,code]` | value not honored by emit | NO | picks lineNo ✗ | last → `code`; value ignored anyway | Confirmed |
| Array / Grid / Matrix / DPTable | `*.cell[..]` | 1 | ONLY | NO | ✓ | ✓ | Confirmed |
| Queue | `q.cell[i]` | 1 | ONLY | NO | ✓ | ✓ | Confirmed |
| Tree | `T.node[i]` | 1 | ONLY | NO | ✓ | ✓ | Confirmed |
| Bar | `h.bar[i]` | 1 | ONLY | NO | ✓ | ✓ | Confirmed |
| Forest | `f.node[i]` | 1 | ONLY | NO | ✓ | ✓ | Confirmed |
| Hypercube | `L.subset[i]` | 1 | ONLY | NO | ✓ | ✓ | Confirmed |
| TraceTable (cell) | `t.cell[k][j]` | 1 | ONLY | NO | ✓ | ✓ | Confirmed |
| TraceTable (row) | `t.row[k]` | N (one per column) | — | NO | (would pick col 0) | **not a value target** (value is keyed by cell) | Confirmed |
| Equation term | `E.term[id]` | 0 (`<span>` in `<fo>`) | — | NO | `querySelector('text')`→null | **no-op** (no write, no anim) | Confirmed |
| MetricPlot | `plot` | 21 (axis ticks) | — | NO | (would pick tick 0) | **NOT value_change-eligible** | Confirmed |
| Stack | `s.item[i]` | 1 | value not honored | NO | ✗* | ✗* (1-text; server reverts) | Confirmed |
| Graph (node) | `g.node[i]` | 1 | value not honored | NO | ✗* | ✗* | Confirmed |
| NumberLine | `nl.tick[i]` | 1 | value not honored | NO | ✗* | ✗* | Confirmed |
| Plane2D | `p.point[i]` | needs a live point | — | NO | — | not exercised (invalid selector without points) | Deduced |

`*` = adjacent oddity, not the positional class — see Part 3.

**Structural proofs (rendered DOM):**
- VariableWatch: `<g data-target="vars.var[i]">` → `<rect>` `<text …>i</text>`
  `<text data-role="value" …>3</text>` → value LAST, tagged.
- HashMap: `<g data-target="hm.bucket[0]">` → `<text>0</text>`
  `<text data-role="value">cat:3  car:7</text>` → value LAST, tagged.
- LinkedList: `<g data-target="ll.node[0]">` → `<rect><line>`
  `<text data-role="value" …>SENT</text>` `<circle>` `<text …>node[0]</text>`
  → **value FIRST**, caption LAST, value tagged.
- Math value (VariableWatch): `<text data-role="name">x</text>`
  `<foreignObject data-role="value">…KaTeX…</foreignObject>` → value is a
  foreignObject; `text[data-role="value"]` does not match it.

---

## PART 3 — Verdict

### Confirmed siblings
- **HashMap** — a true sibling of the value_change/VariableWatch class: value
  target group is `[indexText, valueText]`, so the pre-fix first-`<text>` pick
  stamped the value onto the bucket index. Fixed by `data-role="value"`
  (`hashmap.py:363`). Repro: `examples/primitives/hashmap.tex`, step 2 —
  pre-fix, bucket 0's "0" becomes "cat:3".
- **LinkedList** — same structural family (2-text value group) but the inverse
  layout: value FIRST + trailing `node[N]` caption. Not broken by the old
  first-`<text>` code, but it **is the counterexample that refutes a
  last-`<text>`-only fallback**. Safe only because the fix tagged it
  (`linkedlist.py:436`). Repro: `\apply{ll.node[0]}{value=SENT}` renders
  `[SENT, node[0]]`; a last-text fallback would target `node[0]`.

### "Is the value ever mid-list (neither first nor last)?"
**No.** Every live `value_change` target holds at most 2 `<text>` nodes; the
value is either LAST (VariableWatch, HashMap, CodePanel-code) or FIRST
(LinkedList). No 3-text value group exists (TraceTable's multi-text `row[k]` and
MetricPlot's 21-text `plot` are **not** value targets; the value is keyed to the
1-text cell / is not eligible). So neither the old first-pick nor a last-fallback
can be defeated by a strictly-middle value **today**.

### Is fix-valuenode's last-`<text>` fallback complete?
**Not on its own — it is completed by three explicit tags.** The fallback's
premise ("value is last… never the first") is false for LinkedList; the fix
survives only because LinkedList, VariableWatch and HashMap all emit
`data-role="value"`. These are exactly the three multi-`<text>` value primitives
in the corpus (grep: `data_role="value"` → hashmap / variablewatch / linkedlist
only), so the current corpus is covered. **Durable risk:** any future multi-text
value primitive added without the tag whose value is not the last `<text>` will
be silently mis-stamped by the fallback.

### Residual instances the fix does NOT close
1. **Math-valued rows (LOW / cosmetic, pre-existing).** The value node is
   `<foreignObject data-role="value">`, but the primary selector
   `text[data-role="value"]` (`scriba.js:165`) matches `<text>` only, so it
   misses the tag; the fallback then grabs the last `<text>` (the NAME on a VW
   row), and `vt` scale-bounces that NAME. No corruption — the write is guarded
   by `String(toVal).indexOf('$')===-1` (`scriba.js:177`). Fix direction: select
   `[data-role="value"]` (element-agnostic) for `vt`, not `text[data-role=…]`.
2. **Equation terms** are `<span data-target>` inside a foreignObject with no
   `<text>` child → `value_change` is a silent no-op (no mis-stamp). Benign.

### Adjacent class discovered (NOT positional node-targeting)
The differ emits real `value_change` records for **Stack** (`s.item[i]`),
**Graph** (`g.node[i]`) and **NumberLine** (`nl.tick[i]`), but those primitives'
`emit_svg` ignores `set_value` (they render from `items` / `nodes` / `domain`).
Raw manifest e.g. `["s.item[0]","value",null,"SENT","value_change"]`. Each group
has 1 `<text>`, so there is **no positional mispick** — but the runtime writes
the new value while the server fs-snap reverts to the original, i.e. a
runtime↔server **flip-back mismatch**. Different root cause (spurious
value_change on value-not-honoring primitives); worth its own ticket.

---

## Conclusion

- The positional-node-targeting class has exactly **one live handler**:
  `value_change`. Every other `_applyTransition` branch acts on the `data-target`
  group as a whole or via keyed lookups; `annotation_add`'s child-picks are
  single-candidate and animation-only.
- Within `value_change`, the class has **two Confirmed members**: VariableWatch
  (reported) and **HashMap** (sibling) — plus **LinkedList** as the structural
  inverse that a last-text-only fix would have regressed.
- The landed `data-role="value"` + last-`<text>` fix is **correct and complete
  for the current corpus** (all three multi-text value primitives are tagged),
  with two caveats to surface: (a) the last-text fallback is load-bearing only
  because the tags exist — document that any new multi-text value primitive MUST
  emit `data-role="value"`; (b) the math/foreignObject value animation still
  bounces the wrong node (cosmetic).

**Cross-validation with fix-valuenode's own test.** `tests/unit/
test_value_change_value_node.py` (added by the fix, uncommitted) independently
documents the same three cases — VariableWatch/HashMap (value LAST → affected)
and LinkedList (value FIRST → "naive last-text fallback" hazard), asserting
`test_tag_beats_last_text_fallback` that the tag "must win over last-text;
last-text here is the index caption". This corroborates my Part 2/3 findings and
confirms the fix's scope is complete **for plain-text values in the corpus**. My
audit is ADDITIVE on two points the fix's test does not cover: (1) the
**math/foreignObject** value path — the test only exercises `<text
data-role="value">`, never a `<foreignObject data-role="value">`, so the
selector-mismatch animation residual is unguarded by tests; (2) the **adjacent
spurious-value_change** class (Stack/Graph/NumberLine).

**Confidence: HIGH.** All primitive claims are backed by rendered DOM + parsed
`tr` manifests (20 primitives exercised) and corroborated by the fix's own unit
test. The only Deduced (not rendered) entry is Plane2D `point[i]`, which needs a
pre-existing point to target; its points are coordinate markers (0–1 label), not
a multi-text value row, so it is not a plausible new sibling.
