# Completeness Audit

**Subject:** `docs/SCRIBA-TEX-REFERENCE.md` (1493 lines) vs. code surface in `scriba/animation/`.

**Verdict:** The doc is broadly complete — all 15 primitives, all 13 inner commands, every state, and the major `\apply` operations are present. However, there is one *factual* completeness defect (a documented `\apply` param that does not exist in code), a handful of genuinely missing construction params and operations (Graph `set_weight`/`seed`, CodePanel `source=`, Array `values=`/`n=`), and several spots where required-vs-optional is under-specified for primitive construction. **Overall score: Medium-High.** No primitive is wholly missing, but the `tooltip=` claim and the missing ops should be fixed before this can be trusted as a single-source reference.

## Method

For each primitive under `scriba/animation/primitives/`, I extracted `ACCEPTED_PARAMS`, `SELECTOR_PATTERNS`, and the `apply_command` op branches, then compared against the doc. `\apply` value/label/extra routing was confirmed in `scene.py::_apply_apply` (lines 604-631). `\cursor` params confirmed in `parser/_grammar_commands.py` (lines 258-338).

## Findings

| # | Area | Issue | Code reference | Doc line | Severity | Fix |
|---|------|-------|----------------|----------|----------|-----|
| 1 | `\apply` §5.5 | **`tooltip=` is documented but does NOT exist anywhere in code.** `grep tooltip scriba/` returns zero hits. `_apply_apply` only special-cases `value`/`label`; any other key is passed to the primitive `apply_command` as an extra param, and no primitive reads `tooltip`. Authors will get a silent no-op. | `scene.py:604-631`; no primitive matches | 332 | **HIGH** | Remove `tooltip=` from the "Common" list, or implement it. Current text misleads authors. |
| 2 | Graph §7.4 | **`set_weight` op missing.** `apply_command` supports `add_edge`, `remove_edge`, **and `set_weight={from,to,value}`** (E1473). Doc documents only add_edge/remove_edge plus the `value=` edge-label form. `set_weight` is the proper way to mutate a numeric weight. | `graph.py:828-880` (set_weight branch) | 687-696 | **MEDIUM** | Add `\apply{G}{set_weight={from="A", to="B", value=7}}` with E1473 to the Dynamic edge mutation block. |
| 3 | Graph §7.4 | **`seed` construction param missing.** `ACCEPTED_PARAMS` includes both `layout_seed` and `seed` (alias). Doc documents only `layout_seed`. | `graph.py:581` ACCEPTED_PARAMS; `layout_seed` read at 700 | 663-685 | **LOW** | Note `seed=` is an accepted alias for `layout_seed=`. |
| 4 | CodePanel §7.11 | **`source=` construction param missing.** `ACCEPTED_PARAMS = {source, lines, label}`. `source="...multiline..."` is split on newlines as an alternative to `lines=[...]`. Doc shows only `lines=`. | `codepanel.py:78-105` | 885-890 | **MEDIUM** | Document `source=` as a multiline-string alternative to `lines=`. |
| 5 | Array §7.1 | **`values=` and `n=` aliases missing.** `ACCEPTED_PARAMS = {size, n, data, labels, label, values}`. `n=` is an alias for `size=`; `values=[...]` supplies both size and data in one param (size inferred from len). Doc shows only `size=` and `data=`. | `array.py:97-148` | 636-641 | **MEDIUM** | Document `n=` (alias for `size`) and `values=` (combined size+data). |
| 6 | DPTable §7.3 | **`n=` documented for 1D but param table/required-vs-optional not stated.** DPTable accepts `n`, `rows`, `cols`, `data`, `labels`, `label`. Doc shows usage but never states which are required (1D needs `n`; 2D needs `rows`+`cols`) nor that `labels`/`data` are optional. | `dptable.py:93,104-180` | 650-658 | **LOW** | Add a param table with required-vs-optional (1D: `n` required; 2D: `rows`+`cols` required). |
| 7 | Stack §7.8 | **`push={label,value}` dict form under-documented.** Doc shows `push="C"` and `pop=1` only. Code also accepts `push={"label":"text","value":1.0}`. | `stack.py:143-167` | 806 | **LOW** | Document the dict form of `push`. |
| 8 | Tree §7.5 | **`remove_node` E1434 mismatch.** Doc says E1434 = "root removal without cascade". Code: `remove_node` accepts a bare id (cascade=false) or `{id, cascade}`. Removing root without cascade is allowed at the apply layer; doc's stated trigger should be verified against actual raise sites (errors.py). | `tree.py:236-275` | 762-773 | **LOW** | Verify E1434/E1433 trigger conditions against `errors.py` and `_remove_node_internal`; align wording. |
| 9 | Plane2D §7.9 | **`add_region` spec is `add_region=...` (elided).** Every other op shows a concrete example; `add_region` does not, so authors cannot construct one. Region dict shape is `{polygon=[...], fill=...}`. | `plane2d.py:352-356` (region parse); `apply_command:374` | 838 | **MEDIUM** | Replace `\apply{p}{add_region=...}` with a concrete `{polygon=[...], fill="..."}` example. |
| 10 | MetricPlot §7.10 | **E1483 per-series point cap not documented.** `apply_command` raises E1483 when a series exceeds `_MAX_POINTS`. Not in the doc's error table or Limits. | `metricplot.py:251-270` | 850-883, §14 | **LOW** | Add E1483 (MetricPlot max points/series) to §14 / §15. |
| 11 | HashMap §7.12 | **No construction-param required/optional + no whole-map op.** `ACCEPTED_PARAMS={capacity,label}`. `capacity` is the only sizing param; `apply_command` only sets bucket values via `bucket[i]` + `value=`. Doc is essentially correct but does not state `capacity` is required nor that there is no put/get key-hashing op (values are author-supplied strings). | `hashmap.py:79-160` | 892-898 | **LOW** | State `capacity` required; clarify buckets hold author-supplied display strings, no auto-hashing. |
| 12 | VariableWatch §7.15 | **`\apply` operations entirely undocumented.** Code supports both `\apply{vars.var[name]}{value=X}` and bulk `\apply{vars}{i=3, j=5}` (sets multiple vars by name in one call). Doc §7.15 lists selectors only — no operations section. | `variablewatch.py:131-156` | 927-932 | **MEDIUM** | Add an Operations block: per-var `value=` and bulk `\apply{vars}{name=val,...}`. |
| 13 | Queue §7.14 | **`dequeue=false`/`0` semantics worth noting; `cell[i]{value=}` direct-set undocumented.** `dequeue` only fires on a truthy flag; direct `\apply{q.cell[i]}{value=X}` is supported (set_value). Doc shows enqueue/dequeue only. | `queue.py:157-205` | 917-925 | **LOW** | Note direct `\apply{q.cell[i]}{value=}` and that `dequeue` requires truthy. |
| 14 | §10 Env options | **`theme` on lstlisting documented (§2.5) but no per-scene completeness issue;** `layout=filmstrip\|stack` and `grid` (ignored) are covered. No gap. | `scene.py` env parse | 1256-1267 | — | None. |

## Confirmed-complete (no gaps)

- **Selectors:** Every `SELECTOR_PATTERNS` entry for all 15 primitives is reflected in §8's table and per-primitive sections (Array range/all, Queue front/rear/all, Plane2D 5 families + all, NumberLine tick/range/axis/all, Stack item/top/all, etc.). Plane2D's full 6-form set is correctly expanded at lines 965-976.
- **States:** All 8 `recolor` states + `highlight` documented (§6), matching `VALID_STATES`.
- **`\apply` ops:** Graph add_edge/remove_edge, Tree add_node/remove_node/reparent (+cascade), Plane2D add/remove for all 5 element types, Stack push/pop, Queue enqueue/dequeue, LinkedList insert/remove, MetricPlot series-append — all present. Only **Graph `set_weight`** (finding #2) is missing.
- **`\cursor`:** `prev_state=`/`curr_state=` defaults (dim/current) and multi-target form match `_grammar_commands.py`.
- **Limits & error codes:** §14/§15 align with `errors.py` for the documented subset (E1400/E1401/E1402, E1471/E1472, E1437, E1173, E1181, etc.). Missing: E1473 (#2), E1483 (#10).

## Prioritized fix list

1. **(HIGH, #1)** Remove or implement `tooltip=` in §5.5 — it is a phantom param and the single worst completeness defect.
2. **(MEDIUM, #2)** Add Graph `set_weight={from,to,value}` op + E1473 to §7.4 and §15.
3. **(MEDIUM, #12)** Add a VariableWatch Operations block (per-var + bulk apply).
4. **(MEDIUM, #4)** Document CodePanel `source=` multiline alternative.
5. **(MEDIUM, #5)** Document Array `values=` and `n=` aliases.
6. **(MEDIUM, #9)** Give `add_region` a concrete example in §7.9.
7. **(LOW, #3/#6/#7/#8/#10/#11/#13)** Sweep: Graph `seed=` alias; DPTable required-vs-optional param table; Stack `push` dict form; verify Tree E1433/E1434 wording; add E1483; HashMap `capacity` required + no auto-hash note; Queue direct cell set + dequeue-truthy note.
8. **Cross-cutting:** Add a per-primitive "required vs optional" marker to every §7 construction example. Currently most §7 entries show one usage line without stating which params are mandatory (Array `size`, Grid `rows`+`cols`, DPTable `n` or `rows`+`cols`, HashMap `capacity`, Graph `nodes`). This is the most systematic completeness weakness.
