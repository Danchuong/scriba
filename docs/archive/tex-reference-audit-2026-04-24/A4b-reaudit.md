# A4b — LLM Cold-Read Re-Audit 2026-04-24

## Rating: GOOD

## Dijkstra draft walkthrough

**Step 1 — File skeleton.** §1 is now clear: no `\documentclass`, body directly. No confusion. Render instructions in §0 are present and unambiguous (this was missing before).

**Step 2 — Graph declaration.** §7.4 now has a Layout Decision Guide table (§7.4.1). For a weighted directed graph I'd immediately select `layout="hierarchical"` with `orientation="LR"`. Weighted edges via `edges=[("s","A",3), ...]` with `show_weights=true` and `directed=true` — all clearly documented. Node ID quoting rule is now explicit in §8.

**Step 3 — Distance array.** `\shape{dist}{Array}{size=5, data=["inf",...], labels="0..4", label="$dist$"}` — straightforward.

**Step 4 — CodePanel.** `\shape{code}{CodePanel}{lines=[...], label="Dijkstra"}`. §13.9 warns CodePanel is 1-based — a gotcha I would have hit and is now documented.

**Step 5 — Prelude/delta semantics.** §3.2 now has an explicit operational definition of prelude → frame-0 state. No confusion on what happens before the first `\step`.

**Step 6 — Frames.** `\step[label=init]`, `\recolor`, `\apply`, `\annotate` with `arrow_from=`. `\cursor{dist.cell, code.line}{2}` for multi-target sync — clearly documented in §5.10. `\reannotate` for final path highlight — §5.9 now has a full parameter table including `label=` and `ephemeral=`.

**Step 7 — `\compute` usage.** I wanted to initialize `INF = 10**9` in the prelude; §13.6 documents the integer literal cap and the `10**N` workaround. §5.2 now explicitly states `\compute` is allowed inside `\step` — no contradiction with §3.1 (contradiction resolved).

**Step 8 — `${var}` outside foreach.** §13.2 now explains *why* (deferred resolver vs textual substitution) and gives the single-iteration `\foreach` workaround. No longer a silent mystery.

**Step 9 — `current` vs `path` semantics.** §6 now has an explicit semantic convention note: `current` = being processed now, `path` = final solution path. Clean mapping to Dijkstra.

**Result: I could draft a syntactically valid, pedagogically sensible Dijkstra animation — including the full §9.7 worked example — without inventing any syntax.**

---

## 1. Did you succeed without inventing syntax?

**Yes.** No syntax had to be invented. Every construct I reached for — weighted directed Graph with hierarchical layout, multi-target `\cursor`, `\annotate` with `arrow_from=`, `\reannotate` for path highlight, `\compute` with `10**9`, CodePanel 1-based indexing — was documented with enough precision to use correctly on first attempt.

---

## Friction points

| Issue | § | Severity |
|---|---|---|
| `\apply` param list still "common: value=, label=, tooltip=" — no exhaustive table. E.g., `add_edge`, `remove_edge`, `add_node` documented per-primitive (§7.4, §7.5) but `\apply` §5.5 itself gives no cross-reference to these. | §5.5 | annoying |
| `\compute` `print` behavior still unspecified — goes to build log? No-op? Minor debug friction. | §5.2 | minor |
| `VariableWatch` initial display value unspecified (blank cell, `"0"`, dash?). For Dijkstra I'd use it for `u` / current node tracking. | §7.15 | minor |
| `\substory` state-persistence clarified in §5.12 ("mutates parent state"), but whether `\shape` inside substory is accessible from parent after `\endsubstory` is not stated. | §5.12 | minor |
| Error code table (§15) stops at E1470; E1471/E1472 (add/remove edge errors) documented inline in §7.4 but absent from §15 table — minor lookup friction. | §15 | minor |

---

## Delta from A4

**Resolved:**
- `\compute` prelude-vs-in-step contradiction (§3.1 vs §9.5): fully resolved with operational definition
- No Graph layout decision criteria: §7.4.1 decision table added
- No render/run instructions: §0 added with clear CLI examples
- "delta-based" undefined: §3.2 operational definition added
- `${var}` outside foreach "may fail" with no explanation: §13.2 now explains mechanism and workaround
- No Dijkstra example: §9.7 full worked example added (all three primitives)
- `\reannotate` underdocumented: §5.9 now has full parameter table
- Node ID quoting rule: §8 now has explicit rule
- "selector" undefined: §8 now opens with a definition
- Semantic convention `current` vs `path`: §6 now has a note
- `CodePanel` 1-based indexing: §13.9 added
- Two-blue confusion: §6 now explicitly distinguishes `current` vs `path`

**Still open:**
- `\apply` has no exhaustive param table (per-primitive params scattered, no index)
- `\compute` `print` behavior unspecified
- `VariableWatch` initial display unspecified

**New:**
- §15 error table missing E1471/E1472 (documented in §7.4 prose but not in table)

---

## Recommendation

**PASS**

The reference has crossed from ACCEPTABLE to GOOD. A first-time LLM can now produce a correct, complete Dijkstra animation without inventing syntax. Remaining friction is documentation polish (exhaustive `\apply` param index, `print` behavior, `VariableWatch` initial state) — none is a correctness blocker. The §9.7 worked example is the single biggest improvement: it demonstrates the exact pattern (Graph + Array + CodePanel, hierarchical layout, `\cursor` multi-target, `\reannotate` path trace) that cold-read AI needs to anchor the unfamiliar parts.
