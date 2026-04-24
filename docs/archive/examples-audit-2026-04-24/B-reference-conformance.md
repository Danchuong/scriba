# Audit B — Reference Conformance Report
**Date:** 2026-04-24 | **Files scanned:** 113 | **Non-conformant:** 18 | **Reference:** SCRIBA-TEX-REFERENCE.md (1487 lines)

---

## 1. Executive Summary

113 `.tex` files were audited against the canonical reference. 18 files contain at least one conformance drift; the remaining 95 are fully conformant. The single worst-offender file is `algorithms/misc/convex_hull_andrew.tex`, which concentrates three distinct CRITICAL/HIGH violations in one `\shape` declaration (`grid=on`, unquoted `aspect=equal`, unquoted `orientation=horizontal`). The most systemic category is **quoting-rule-miss**: integer node IDs used unquoted in Graph/Tree selector positions appear across 5 files, and the `stable+directed=true` combination (documented to emit a `UserWarning`) appears in 6 files. Scout triage correctly flagged `grid=on`; its claim of a duplicate `id="mcmf"` across two files is **incorrect** — `demos/mcmf.tex` uses `id="mcmf-graph"` and `id="mcmf-spfa"`, not `"mcmf"`.

---

## 2. Per-Issue Table

| Sev | File : Line | Snippet | Issue | Reference § |
|-----|------------|---------|-------|-------------|
| CRITICAL | `algorithms/misc/convex_hull_andrew.tex:23` | `grid=on,` | `grid=` accepts bool only; `"on"` is an undocumented string value — silently ignored or raises E-code | §10 env-options table: `grid` type = bool |
| CRITICAL | `algorithms/misc/convex_hull_andrew.tex:22` | `aspect=equal,` | Unquoted bare identifier `equal`; reference type is enum string `"equal"` | §7.9 Plane2D params table: `aspect "equal"/"auto"` |
| CRITICAL | `algorithms/misc/convex_hull_andrew.tex:37` | `orientation=horizontal,` | Unquoted bare `horizontal` for Stack; reference shows `orientation="horizontal"` | §7.8 Stack params |
| HIGH | `demos/dinic.tex:59–60,68–69,168–171` (8 sites) | `\recolor{G.node[A]}{state=highlight}` | `state=highlight` is documented as "ephemeral focus (via `\highlight` only)"; applying it via `\recolor` is undocumented and bypasses the ephemeral-clear semantics | §6 Visual States: `highlight … via \highlight only` |
| HIGH | `demos/maxflow.tex:140` | `\recolor{G.edge[(A,C)]}{state=highlight}` | Same as above — `state=highlight` via `\recolor` is undocumented | §6 Visual States |
| HIGH | `smoke/gep_v2_smoke.tex:76–77,123,192` (4 sites) | `\recolor{G3.node[A]}{state=highlight}` | Same `state=highlight` via `\recolor` violation | §6 Visual States |
| MED | `cses/planets_queries2.tex:2` | `nodes=[1,2,3,4,5,6]` | Integer node IDs in Graph; §8 quoting rule states unquoted form is for identifiers matching `[A-Za-z_][A-Za-z0-9_]*` — integers do not match | §8 Node ID quoting rule |
| MED | `cses/planets_queries2.tex:10–36,113–193` (~30 sites) | `g.node[1]`, `g.edge[(1,2)]` | Integer node IDs unquoted in selectors throughout file | §8 |
| MED | `cses/necessary_roads.tex:2` | `nodes=[1,2,3,4,5,6,7]` | Integer Graph node IDs — same quoting issue | §8 |
| MED | `cses/necessary_roads.tex:10–145` (~20 sites) | `g.node[1]`, `g.edge[(1,2)]` | Unquoted integer selectors throughout | §8 |
| MED | `algorithms/tree/hld.tex:2` | `nodes=[1,2,3,4,5,6,7,8,9]` | Integer Tree node IDs — quoting rule applies to Tree equally | §8 |
| MED | `algorithms/tree/hld.tex:9–75` (~20 sites) | `T.node[1]` … `T.node[9]` | Unquoted integer Tree selectors | §8 |
| MED | `algorithms/tree/splay.tex:14,19,24,31,36` | `reparent={node=2, parent=7}` | Integer node IDs unquoted in `reparent` dict; reference shows `reparent={node="E", parent="C"}` | §7.5 Tree mutation ops |
| MED | `algorithms/graph/union_find.tex:2` | `directed=true, layout="stable"` | `layout="stable"` with `directed=true` emits `UserWarning` per §7.4.1 decision guide | §7.4 Graph, §7.4.1 Layout Decision Guide |
| MED | `algorithms/graph/union_find_graph.tex:2` | `directed=true, layout="stable"` | Same stable+directed UserWarning | §7.4.1 |
| MED | `algorithms/graph/mcmf.tex:2` | `directed=true, layout="stable"` | Same stable+directed UserWarning | §7.4.1 |
| MED | `cses/planets_queries2.tex:2` | `directed=true, layout="stable"` | Same stable+directed UserWarning | §7.4.1 |
| MED | `integration/test_reference_graph_tree.tex:8,18` | `directed=true, … layout="stable"` | Two shapes both with stable+directed | §7.4.1 |
| MED | `primitives/graph.tex:2` | `directed=true, layout="stable"` | Same | §7.4.1 |
| MED | `quickstart/binary_search.tex:1` | `id="binary-search"` | Duplicate scene ID — same id also used in `integration/test_reference_grid_numline.tex:123`; composing both in one HTML breaks step navigation | §10 env-options: `id` is a "stable scene ID" |
| MED | `primitives/hashmap.tex:1` | `id="hashmap-demo"` | Duplicate — same id in `integration/test_reference_datastruct.tex:42` | §10 |
| LOW | `smoke/gep_v2_smoke.tex:97,184` | `global_optimize=true` | Documented no-op that emits `UserWarning`; using it in example teaches pattern that silently does nothing | §7.4 Graph params: "currently a no-op — emits a `UserWarning`" |
| LOW | `editorials/bfs_grid_editorial.tex:21,41,230,250` | `\begin{diagram}` / `\begin{animation}` with no `[...]` | Four environments have no `id=` or `label=`; `id` defaults to auto (acceptable) but `label` = accessibility label and is strongly implied required for editorial files | §10 env-options table |

---

## 3. Issue Category Rollup

### bad-option-value (1 issue, 1 file)
- `grid=on` in `algorithms/misc/convex_hull_andrew.tex:23` — only `true`/`false` accepted
- **Fix:** change to `grid=true`

### unquoted-enum-string (2 issues, 1 file)
- `aspect=equal` and `orientation=horizontal` in `algorithms/misc/convex_hull_andrew.tex:22,37` — reference always shows enum strings quoted
- **Fix:** `aspect="equal"`, `orientation="horizontal"`

### undocumented-state-via-recolor (13 occurrences, 3 files)
- `\recolor{...}{state=highlight}` in `demos/dinic.tex`, `demos/maxflow.tex`, `smoke/gep_v2_smoke.tex`
- Reference reserves `highlight` state exclusively for `\highlight` command
- Top sites: `demos/dinic.tex:59`, `demos/dinic.tex:168`, `smoke/gep_v2_smoke.tex:76`
- **Fix:** replace `\recolor{X}{state=highlight}` with `\highlight{X}`; note semantics change (ephemeral vs persistent) so surrounding frame logic may need adjustment

### quoting-rule-miss — integer node IDs (5 files)
- Integer node IDs used unquoted in `G.node[1]`, `T.node[3]`, `reparent={node=2}`
- Files: `cses/planets_queries2.tex`, `cses/necessary_roads.tex`, `algorithms/tree/hld.tex`, `algorithms/tree/splay.tex`, and implicitly `primitives/diagram.tex`, `primitives/tree.tex`
- Note: §7.5 example in the reference itself uses integer node arrays without showing explicit quoting — creating internal inconsistency (see §5)
- **Fix:** wrap integer IDs with quotes: `g.node["1"]`, `T.node["1"]`, `reparent={node="2", parent="7"}`

### warn-prone-layout (6 files, 6 `\shape` declarations)
- `layout="stable"` with `directed=true` — documented to emit `UserWarning` per §7.4.1
- Files: `algorithms/graph/union_find.tex:2`, `algorithms/graph/union_find_graph.tex:2`, `algorithms/graph/mcmf.tex:2`, `cses/planets_queries2.tex:2`, `integration/test_reference_graph_tree.tex:8,18`, `primitives/graph.tex:2`
- **Fix:** switch to `layout="force"` with `layout_seed=` for reproducibility, or change to `directed=false`

### duplicate-scene-id (2 pairs, 4 files)
- `id="binary-search"`: `quickstart/binary_search.tex` + `integration/test_reference_grid_numline.tex`
- `id="hashmap-demo"`: `primitives/hashmap.tex` + `integration/test_reference_datastruct.tex`
- **Fix:** rename IDs in integration files: `"binary-search-numline"`, `"hashmap-demo-bucket"`

### no-op-flag-in-example (1 file, 2 sites)
- `global_optimize=true` in `smoke/gep_v2_smoke.tex:97,184` — documented no-op + `UserWarning`
- **Fix:** either add `% forward-compat only` comment or remove

### missing-env-label (1 file, 4 environments)
- `bfs_grid_editorial.tex:21,41,230,250` — `\begin{diagram}` and `\begin{animation}` with no option brackets
- **Fix:** add `[id="bfs-grid-1", label="BFS grid setup"]` etc.

---

## 4. Files Fully Conformant (count per subdir)

| Subdir | Conformant / Total |
|--------|--------------------|
| algorithms/ | 18 / 23 |
| cses/ | 8 / 10 |
| demos/ | 2 / 4 |
| editorials/ | 3 / 4 |
| fixtures/ | 24 / 24 |
| integration/ | 19 / 21 |
| primitives/ | 17 / 19 |
| quickstart/ | 3 / 4 |
| smoke/ | 3 / 4 |
| **Total** | **97 / 113** |

Note: `fixtures/expected-fail/` files are intentionally invalid — counted conformant because their invalidity is their purpose.

---

## 5. Suggested Reference Edits

These patterns appear >3 times, look like intended usage, but the reference is either silent or internally inconsistent:

**1. Integer node IDs in Tree and Graph (5+ files; §7.5 reference example itself uses them)**
§8 quoting rule says unquoted requires `[A-Za-z_][A-Za-z0-9_]*`, excluding integers. Yet §7.5 shows `nodes=[8,3,10,1,6,14]` without any note on how to select them. Fix options:
- Add a note to §8: "Unquoted integers (`T.node[8]`) are also accepted when node IDs are pure integers", or
- Change the §7.5 example to use string IDs `nodes=["8","3","10","1","6","14"]`

**2. `\recolor{X}{state=highlight}` (3 files, 13 occurrences)**
Reference states highlight is "via `\highlight` only" but does not explicitly say `state=highlight` is rejected by `\recolor`. If runtime accepts it, document: "`state=highlight` is also accepted by `\recolor`; unlike `\highlight`, it is persistent (not ephemeral)" — or explicitly list it as an error.

**3. `stable+directed=true` (6 files)**
Buried in footnote-style sentence in §7.4.1. Given its frequency in real examples (union-find, graph traversal), deserves a dedicated gotcha callout: "If you use `layout="stable"` with `directed=true`, a `UserWarning` is emitted but rendering proceeds. Switch to `layout="force"` with `layout_seed=` for deterministic directed graphs."

**4. `\begin{animation}` / `\begin{diagram}` without option brackets (bfs_grid_editorial.tex)**
Reference §10 shows options as `[id="...", label="..."]` but never states they are required. The reference should clarify whether the bracket is required or optional, and what defaults apply when absent.
