# prim_lin_ render-output review

**Scope:** 29 `prim_lin_*` snippets (Stack, Queue, LinkedList, HashMap primitives).
**Method:** READ-ONLY. Parsed each `.tex` op sequence and `.expect` contract, then
grepped the corresponding `.html` stage `<svg>` blocks for `data-primitive`,
`data-target`, `<text>` labels, `scriba-state-*` classes, and geometry
(`rect`/`circle`/`line`/`path`/`polygon`). Counts tracked per op.

## Summary tally

| Outcome | Count |
|---------|------:|
| OK (ok-contract, HTML verified) | 23 |
| OK (error-contract, no HTML by design) | 4 |
| SUSPECT | 2 |
| **Total** | **29** |

- 4 snippets are negative tests (`error E14xx`): `hashmap_capacity_invalid`,
  `hashmap_capacity_missing`, `queue_capacity_invalid`, `stack_max_visible_invalid`.
  Each correctly has **no `.html`** (render is expected to raise). Not render-bugs.
- SANITY-FLAGS.md reports `prim_lin_` as 0/29 flagged by the automated heuristic
  checker; my structural pass agrees the *checker* heuristics are clean. The 2
  SUSPECTs below are semantic (state-application) discrepancies the heuristic
  checker does not test for.

### Frame model note (not a bug)
Every `.html` emits **2 stage SVGs per `\step`** (a static copy + an animated copy;
`scriba-frame` keyframes appear 20× per file). So a 1-step snippet shows 2 identical
frames and a 2-step snippet shows 4 frames in (step1,step1,step2,step2) order. All
counts below are per-step after de-duplicating the doubling.

## Per-snippet table

| id | intent | verdict | reason |
|----|--------|---------|--------|
| hashmap_bucket_value | bucket[1] value="key:val", cap 4 | OK | 4 buckets `hm.bucket[0..3]`, `key:val` text present in bucket[1], idx labels 0..3 |
| hashmap_capacity | cap 4 | OK | 4 buckets, labels 0..3, all idle |
| hashmap_capacity_invalid | cap=0 → E1451 | OK | error contract, no html (correct) |
| hashmap_capacity_missing | no capacity → E1450 | OK | error contract, no html (correct) |
| hashmap_sel_all | recolor all=dim | OK | all 4 buckets `scriba-state-dim` |
| hashmap_sel_bucket | recolor bucket[2]=current | OK | bucket[2] current, others idle |
| linkedlist_data_json | data="[3,7,1]" | OK | 3 nodes, 2 links, vals 3,7,1 |
| linkedlist_data_list | data=[3,7,1,9] | OK | 4 nodes, 3 links, vals 3,7,1,9 |
| linkedlist_insert | insert 42@idx1 | OK | 5 nodes, 4 links, vals 3,42,7,1,9 (42 at node[1]) |
| linkedlist_remove | remove idx2 | OK | 3 nodes, 2 links, vals 3,7,9 (node "1" removed) |
| linkedlist_sel_all | recolor all=dim | OK | all 7 node+link targets dim |
| linkedlist_sel_link | recolor link[0]=good | OK | link[0] good, link[1..2] idle |
| linkedlist_sel_node | recolor node[0]=current | OK | node[0] current, node[1..3] idle |
| queue_capacity_data | cap 6, data=[1] | OK | 6 cells, 1 occupied (val "1"), front+rear labels |
| queue_capacity_invalid | cap=0 → E1440 | OK | error contract, no html (correct) |
| queue_cell_value | cell[1] value=99 | OK | cells show 1,99,3 (cap 6) |
| queue_dequeue_false_noop | dequeue=false | OK | no-op: still 1,2 occupied |
| queue_enqueue_dequeue | enqueue 3; dequeue=true | OK | step1 → 1,2,3; step2 → 2,3 (per-frame verified) |
| queue_gotcha_same_step | enqueue 3 + recolor cell[2] same step | **SUSPECT** | see below |
| queue_sel_all | recolor all=dim | OK | all 8 cell targets dim |
| queue_sel_front_rear | front=current, rear=good | OK | q.front current, q.rear good |
| stack_gotcha_next_step | push C (s1) then recolor item[2] (s2) | OK | s1 item[2]=idle, s2 item[2]=current — correct §13.1 behaviour |
| stack_gotcha_same_step | push C + recolor item[2] same step | **SUSPECT** | see below |
| stack_items_dict | items=[{A,1},{B}] | OK | 2 items A,B |
| stack_items_list | items=["A","B"] | OK | 2 items A,B |
| stack_max_visible | 5 items, max_visible=2 | OK | shows D,E + "+3 more" overflow indicator |
| stack_max_visible_invalid | max_visible=0 → E1441 | OK | error contract, no html (correct) |
| stack_orientation_horizontal | 3 items horizontal | OK | 3 items A,B,C |
| stack_push_dict | push={C,3} onto ["A"] | OK | 2 items A,C |
| stack_push_string_pop | push C (s1); pop=1 (s2) | OK | s1 → A,B,C (3); s2 → A,B (2) |
| stack_sel_all | recolor all=dim | OK | 3 items dim |
| stack_sel_item | recolor item[0]=current | OK | item[0] (bottom) current, others idle |
| stack_sel_top | recolor top=good | OK | item[2] (top) good |

## SUSPECTS

Both SUSPECTs are the same root issue (§13.1 same-step recolor of a freshly
push/enqueue'd cell). The structures, labels, and counts are all fine — the concern
is purely whether the dropped-recolor warning has the documented visual effect.

### 1. `prim_lin_stack_gotcha_same_step` — render-bug (low severity) / possible doc mismatch

**Op sequence (single `\step`):** `\apply{s}{push="C"}` then
`\recolor{s.item[2]}{state=current}` in the **same** step.

**Contract:** `.expect` says `ok` / "Stack same-step recolor of pushed item dropped
(warning, not error)". Docs §13.1 states: *"the new item is not addressable for
`\recolor` in the same `\step`"* and the WRONG example annotates the recolor with
`% WARNING: selector not found`.

**Evidence:** the HTML applies the recolor anyway.
```
prim_lin_stack_gotcha_same_step  → s.item[2] = scriba-state-current
prim_lin_stack_gotcha_next_step  → step1 s.item[2] = scriba-state-idle   (push only)
                                    step2 s.item[2] = scriba-state-current (recolor)
```
If the same-step recolor were genuinely *dropped*, `item[2]` should render `idle`
in the same step (identical to the next_step snippet's step-1 frame). Instead it is
`current` — i.e. the recolor visibly took effect, contradicting "dropped" in both
the docs and the `.expect` wording.

**Classification:** render-bug (the documented drop did not occur), low severity.
Alternative reading: a *doc/contract wording* inconsistency — the recolor logs a
warning but, since `push` has committed to the model by the time the step's final
frame is rendered, `item[2]` resolves and is colored. Either way the HTML and the
"dropped" contract disagree. Worth a maintainer decision: either (a) actually drop
the recolor (item[2] stays idle), or (b) soften the docs/`.expect` to "warns but
still applies in the committed frame". The harness only asserts ok/error, so it
does not catch this.

### 2. `prim_lin_queue_gotcha_same_step` — render-bug (low severity) / possible doc mismatch

**Op sequence (single `\step`):** `\apply{q}{enqueue=3}` then
`\recolor{q.cell[2]}{state=current}` same step.

**Evidence:** `q.cell[2] = scriba-state-current` in the rendered frame, with value
text "3" present (enqueue committed). Same discrepancy as #1: §13.1 documents the
same-step recolor of a freshly enqueued cell as not-addressable/dropped, but the
HTML colors `cell[2]` current.

**Classification:** identical root cause to #1 (render-bug, low severity / doc
wording). Both should be resolved by the same decision.

## Notes / non-issues observed
- No off-canvas, overlap, garbled-label, or missing-label problems found.
- `stack_items_dict`: dict `{label="A", value=1}` renders the **label** ("A") as the
  cell text; `value` is not shown as visible text. Consistent with the label-form
  rendering used elsewhere — treated as expected, not a SUSPECT.
- `stack_max_visible` correctly truncates to the top 2 (`D`,`E`) and emits a
  `"+3 more"` overflow indicator; `data-target` only exposes the visible
  `s.item[3]`, `s.item[4]` — expected for a truncated view.
- LinkedList arrow/link counts are exactly nodes−1 in every case (no dangling or
  duplicate arrows).
