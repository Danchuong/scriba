# Correctness / Freshness Audit

**Document:** `docs/SCRIBA-TEX-REFERENCE.md` (1493 lines)
**Criterion:** Does the doc match CURRENT code behaviour (as of 2026-06-01)?
**Auditor pass:** verified every flagged claim against `scriba/animation/` source.

## Verdict: **Medium** freshness

The doc is broadly accurate, but the four commits landed today (`8989a10`, `cbdd7ce`, `e9de3f1`, `cc470a8`) plus two pre-existing error-code mismatches have left a handful of statements stale or outright wrong. Two are author-facing WRONG claims (Tree node-id quoting; `\hl` error codes E1320/E1321 that do not exist). The rest are STALE-by-today or CORRECT-BUT-RISKY.

---

## Findings Table

| # | Doc claim (line) | What the code actually does (file:line) | Verdict | Severity | One-line fix |
|---|------------------|------------------------------------------|---------|----------|--------------|
| 1 | §8 L943: "Quoted string IDs must match the declaration: if `nodes=[1,2,3]` (ints), use `G.node[1]`, **not** `G.node["1"]`." Rule is presented for **Graph AND Tree** (header L940). | `tree.py:171-176` (commit 8989a10) normalizes every node id to `str` at construction; `resolve_annotation_point` (`tree.py:546-552`) matches the raw string first. So for Tree, `T.node[8]` and `T.node["8"]` BOTH resolve, and `parent=3`/`parent="3"` both match. | **WRONG** (for Tree) | HIGH | Split the rule: for **Tree**, numeric and quoted-string node refs are interchangeable since they are str-normalized; the "must match declaration" constraint now applies to **Graph only**. |
| 2 | §5.13 L587: "Using `\hl` outside `\narrate` raises **E1320**." L588: "An unknown id raises **E1321**." | `grep E1320/E1321` across `scriba/` → **zero matches** (codes do not exist in `errors.py`). `extensions/hl_macro.py:100-113` silently `continue`s on malformed/missing braces; there is no unknown-step validation at all (`scene_id` is "reserved for future scoping", L65). | **WRONG** | HIGH | Remove the E1320/E1321 claims. State that malformed `\hl` is silently skipped and unknown step-ids are NOT validated (the span is emitted with a dead `data-hl-step` anchor). |
| 3 | §13.2 L1355-1375: "`${var}` outside `\foreach` is **unreliable / may fail**"; the worked example `\recolor{a.cell[${target}]}` is labelled "may fail" and a single-iteration-loop workaround is prescribed. | Commit `cbdd7ce` added `SceneState._resolve_interp` (`scene.py:575+`) wired into `_apply_apply` for `value`, `label`, and extra params. So `\apply{x}{value=${scalar}}` and `value=${dp_vals[i]}` now resolve. NOTE: the fix covers **`\apply` value/label/params**, not selector-index positions in `\recolor`. | **STALE (partial)** | MEDIUM | Update §13.2: `${scalar}` and `${list[i]}` in **`\apply` value/label** positions now resolve outside `\foreach` (since today's fix). The remaining caveat is narrower — selector **index** positions (`a.cell[${target}]` in `\recolor`) outside a loop. Re-scope the warning accordingly. |
| 4 | §5.11 L492: "`value=${i}` … (supported since v0.8.2)"; subscript example L517-531 `\apply{dp.cell[${i}]}{value=${dp_vals[i]}}`. | Commit `cbdd7ce` is the commit that actually made the subscript form (`${dp_vals[i]}`) resolve in `\apply` values — before today it "leaked the InterpolationRef repr." | **CORRECT-BUT-RISKY** | LOW | The subscript example now genuinely works, but the "v0.8.2" provenance for `value=${i}` is misleading given the real fix is today. Optionally note the subscript form was fixed in the 0.16.x line. |
| 5 | §7.4 L708: bipartite layout — "non-bipartite graphs raise **E1502**." | `errors.py:417` E1502 = "Too many **frames** for stable layout". `graph_layout_stable.py:230-239` raises E1502 for frame-count overflow only. No bipartite validation maps to E1502 (or any code). | **WRONG** | MEDIUM | Drop the E1502 reference for bipartite; either cite the correct behaviour (non-bipartite input is laid out best-effort, no dedicated error) or remove the claim. |
| 6 | §15 L1493: "E1501 — **Layout warning** — Too many nodes for stable layout — falling back to force layout." | `graph.py:611-622` raises E1501 as a **hard error** (`_animation_error`) when `len(nodes) > 100`. §7.4 L698 correctly calls it a hard limit. The §15 row mischaracterizes it as a warning/fallback (copies the catalog string `errors.py:416`, which is itself the stable-layout-fallback wording). | **WRONG / inconsistent** | MEDIUM | §15 row for E1501 should read "Hard limit — Graph exceeds 100-node maximum (force layout)", matching §7.4 and `graph.py:615`. |
| 7 | §7.11 / §13 CodePanel: doc describes `label="Code"` with no position; no claim about caption placement. | Commit `e9de3f1` moved the CodePanel label to a top IDE-style header bar (`codepanel.py`). | **CORRECT** (no stale text) | — | No change needed — doc never asserted bottom-caption placement. Optional: mention the top title bar for completeness. |
| 8 | §10 L1264-1265 viewBox `width`/`height` default "auto"; §13.8 headroom reserved at per-scene max. | Commit `cc470a8` added `compute_stable_viewbox` (`_frame_renderer.py:166`), wired into all three stitcher call sites (`_html_stitcher.py:212,452,774`). viewBox now sized to the **max extent across frames** (Stack/Queue/CodePanel growth no longer clipped). | **CORRECT** (consistent) | — | No change needed. The "auto" sizing claim and R-32 max-headroom claim remain true and are now actually honoured for growing primitives. Optional: add a note that growing Stack/Queue no longer clip. |
| 9 | §5.2 L235 forbidden Starlark list; L236 pre-injected builtins. | `starlark_worker.py:100-115` `_FORBIDDEN_NODE_TYPES` = Import, ImportFrom, While, Try, ClassDef, Lambda, NamedExpr(walrus), Match, AsyncFunctionDef, AsyncFor, AsyncWith, Await, Yield, YieldFrom. `_ALLOWED_BUILTINS` (L405-453) matches the doc list (note `def`/FunctionDef intentionally allowed). | **CORRECT** | — | No change. Forbidden + allowed lists match exactly. |
| 10 | §13.6 / §14 Starlark int literal ≤10,000,000; §14 range ≤1,000,000 (E1173). | `starlark_worker.py:60` `_MAX_INT_LITERAL = 10**7`; `:67` `_MAX_RANGE_LEN = 10**6`. Matches. | **CORRECT** | — | No change. |
| 11 | §15 error rows E1001, E1003, E1006, E1050, E1054, E1102, E1103, E1109, E1115, E1116, E1150/E1151/E1154, E1173, E1181, E1200, E1360, E1366, E1400, E1470. | All present in `errors.py` with matching semantics (E1109 L178 "Invalid \recolor state or missing required state/color"; E1116 L191 "Mutation references undeclared shape"; E1115 L187 "Selector matches nothing — silently dropped"). | **CORRECT** | — | No change. |
| 12 | §14 limit "Graph stable layout ≤20 nodes, ≤50 frames". | `graph_layout_stable.py:9` E1502 at "T > 50" frames confirms the 50-frame cap. ≤20-node guidance is advisory (matches §7.4). | **CORRECT** | — | No change. |

---

## Prioritized Fixes

1. **(HIGH) §8 L943 — Tree node-id quoting.** The single most author-impactful error: the doc tells authors numeric vs quoted Tree refs must match the declaration, but as of commit `8989a10` they are interchangeable. Split the Graph/Tree rule.
2. **(HIGH) §5.13 L587-588 — phantom error codes E1320/E1321.** These do not exist anywhere in the codebase. Authors relying on them for validation will get silent no-ops instead of errors. Rewrite to describe the actual silent-skip behaviour.
3. **(MEDIUM) §13.2 L1355-1375 — `${var}` outside `\foreach`.** Today's `_resolve_interp` fix makes `\apply` value/label interpolation reliable outside loops. Narrow the warning to `\recolor`/selector-index positions only; keep the single-iteration-loop workaround as a fallback for those.
4. **(MEDIUM) §7.4 L708 — E1502 ≠ bipartite.** E1502 is the stable-layout frame-count overflow code. Remove the bipartite claim.
5. **(MEDIUM) §15 L1493 — E1501 severity.** Reclassify from "Layout warning" to "Hard limit" to match `graph.py:615` and §7.4.
6. **(LOW) §5.11 L492 provenance, §7.11/§13 CodePanel header, §10/§13.8 viewBox.** Optional clarity touch-ups; behaviour is correct.

---

## Code references cited
- `scriba/animation/primitives/tree.py:171-176, 302, 546-552`
- `scriba/animation/extensions/hl_macro.py:65, 100-113`
- `scriba/animation/scene.py:575+` (`_resolve_interp`, commit cbdd7ce)
- `scriba/animation/errors.py:178, 187, 191, 416-417` (no E1320/E1321)
- `scriba/animation/primitives/graph.py:611-622` (E1501 hard raise)
- `scriba/animation/primitives/graph_layout_stable.py:9, 230-239` (E1502 = frames)
- `scriba/animation/starlark_worker.py:60, 67, 100-115, 405-453`
- `scriba/animation/_frame_renderer.py:166` + `_html_stitcher.py:212,452,774` (compute_stable_viewbox, commit cc470a8)
- `scriba/animation/primitives/codepanel.py` (top header bar, commit e9de3f1)
