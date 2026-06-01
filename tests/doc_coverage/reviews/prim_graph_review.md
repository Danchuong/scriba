# prim_graph_ render-output review

**Reviewer:** render-output reviewer (read-only over corpus)
**Date:** 2026-06-01
**Scope:** all 47 `prim_graph_*` snippets (Graph + Tree primitives)
**Method:** per-snippet compare of `.tex` (intent) + `.expect` (contract) vs `.html` (output). For each renderable snippet, counted `data-target` node/edge elements, `<defs>` blocks, arrow-marker ids/refs, `scriba-state-*` classes, and `<text>` labels. Animations checked per-stage.

## Summary tally

- **47 snippets total** in scope.
- **37 are renderable** (have `.html`); **10 are error-only negative tests** (no `.html` — abort cases E1470/E1471/E1472/E1474/E1501/E1433/E1434/E1435/E1436). The error-only cases have no render output to inspect; they are out of render-review scope and counted N/A.
- **36 / 37 renderable: OK.**
- **1 / 37 renderable: SUSPECT** — `prim_graph_node_int_as_string_E1115` (contract/render mismatch, classified **render-bug**, but see note: could be a stale-contract / expected str-normalization question).
- **5 dup-defs render-bug files** (low severity, matches Phase 1 exactly): `directed_true`, `layout_hierarchical`, `orientation_lr`, `orientation_tb`, `stable_directed_warns_ok`. These render correctly otherwise, so verdict on each is OK-with-noted-bug (the duplicate `<defs>` is the known Phase-1 defect, not a content/count failure).

All node/edge/label counts match intent across the 37 renderable snippets (including segtree `nodes = 2·leaves − 1`, `edges = nodes − 1`, and sum arithmetic). No off-canvas/overlap/missing-label issues (consistent with Phase-1 text-bounds clean result). Directed graphs emit arrow markers; undirected graphs emit none.

## Per-snippet table

| id | intent | verdict | reason |
|----|--------|---------|--------|
| prim_graph_add_edge | Graph add_edge runtime | OK | 4 nodes, 1→2 edges; edge (A,D) added |
| prim_graph_add_edge_weighted | add_edge with weight | OK | 4 nodes, edge (A,D) added; weighted shape renders |
| prim_graph_auto_expand | auto_expand=true | OK | 3 nodes / 1 edge as declared |
| prim_graph_directed_false | directed=false | OK | 2 nodes / 1 edge; **no** arrow markers (correct) |
| prim_graph_directed_true | directed=true | OK* | 2 nodes / 1 edge; arrow markers present. **dup-defs bug** (2× `<defs>`, dup id fwd/rev) |
| prim_graph_edge_label_apply | dynamic edge label value= | OK | 2 nodes/1 edge; label text `3/10` present |
| prim_graph_edges_basic | edges (u,v) | OK | 3 nodes / 2 edges |
| prim_graph_label | label caption | OK | 2 nodes/1 edge; caption `My Graph` present |
| prim_graph_layout_auto | layout=auto | OK | 3 nodes / 2 edges |
| prim_graph_layout_force | layout=force | OK | 3 nodes / 2 edges |
| prim_graph_layout_hierarchical | layout=hierarchical | OK* | 3 nodes / 2 edges; directed → arrow markers. **dup-defs bug** |
| prim_graph_layout_seed | layout_seed | OK | 3 nodes / 1 edge |
| prim_graph_layout_stable | layout=stable | OK | 3 nodes / 2 edges |
| prim_graph_layout_unknown_fallback | unknown layout → force | OK | 2 nodes/1 edge; renders (silent fallback) |
| prim_graph_node_int_as_string_E1115 | int node addressed as string → matches nothing, dropped | **SUSPECT** | node 1 IS recolored `current`; identical to strict-ok. Contract says selector matches nothing. See SUSPECTS. |
| prim_graph_node_int_strict_ok | int node addressed as int (matches) | OK | node 1 → `scriba-state-current` (correct) |
| prim_graph_nodes_int | nodes (int ids) | OK | 3 nodes / 0 edges; labels 1,2,3 |
| prim_graph_nodes_str | nodes (string ids) | OK | 4 nodes / 0 edges; labels A,B,C,D |
| prim_graph_orientation_lr | orientation=LR | OK* | 3 nodes / 2 edges; directed → markers. **dup-defs bug** |
| prim_graph_orientation_tb | orientation=TB | OK* | 3 nodes / 2 edges; directed → markers. **dup-defs bug** |
| prim_graph_remove_edge | remove_edge runtime | OK | 3 nodes; 2→1 edges; (A,B) removed, (B,C) remains |
| prim_graph_seed_alias | seed alias for layout_seed | OK | 3 nodes / 1 edge |
| prim_graph_seed_both_layout_seed_wins | layout_seed wins over seed | OK | 3 nodes / 1 edge (renders; precedence not visible structurally) |
| prim_graph_selector_all | selector .all | OK | 2 nodes/1 edge; all 3 elements `scriba-state-dim` |
| prim_graph_selector_edge | selector edge[(u,v)] | OK | edge (A,B) → `scriba-state-path`; 3 idle nodes |
| prim_graph_selector_node | selector node[id] | OK | node A → `scriba-state-current` |
| prim_graph_set_weight | set_weight runtime | OK | 3 nodes/2 edges; weight A-C shows `9` (was 2) |
| prim_graph_show_weights | show_weights with weighted edges | OK | weight labels `4`,`2` present |
| prim_graph_split_labels | split_labels=true | OK | 2 nodes/1 edge; multi-word labels `Alpha Node`,`Beta Node` |
| prim_graph_stable_directed_warns_ok | stable+directed warns, renders ok | OK* | 3 nodes/2 edges; directed → markers. **dup-defs bug** |
| prim_graph_tint_by_edge | tint_by_edge=true | OK | 2 nodes/1 edge; weight `3` present |
| prim_graph_tint_by_source | tint_by_source=true | OK | 2 nodes/1 edge; weight `3` present |
| prim_graph_tree_add_node | Tree add_node | OK | 3→4 nodes; edge (B,E) added under B |
| prim_graph_tree_label | Tree label caption | OK | 3 nodes/2 edges; caption `My Tree` |
| prim_graph_tree_remove_node_cascade | remove_node cascade | OK | B + descendants C,D removed → only A remains |
| prim_graph_tree_remove_node_leaf | remove_node leaf | OK | leaf C removed → A,B + edge (A,B) |
| prim_graph_tree_reparent | reparent | OK | E moved B→C; edge (B,E) gone, (C,E) present |
| prim_graph_tree_segtree | segtree kind + show_sum | OK | 6 leaves → 11 nodes / 10 edges; sums correct (`[0,5]=22`) |
| prim_graph_tree_segtree_quoted_selector | segtree quoted node-id selector | OK | quoted `[0,5]` selector → 1 node `current` |
| prim_graph_tree_selector_edge | Tree edge[(p,c)] | OK | edge (1,2) → `scriba-state-path` |
| prim_graph_tree_selector_int_or_string | node[8]==node["8"] str-normalized | OK | node 8 `current`, node 3 `done` (string ref matched) |
| prim_graph_tree_show_sum_false | segtree show_sum=false | OK | 4 leaves → 7 nodes / 6 edges; range labels only, no sums |
| prim_graph_tree_sparse_add_node | sparse_segtree add_node quoted ids | OK | root [0,7]; after split → 3 nodes / 2 edges ([0,3],[4,7]) |
| prim_graph_tree_sparse_segtree | sparse_segtree kind | OK | single root node `[0,7]` |
| prim_graph_tree_standard | Tree standard kind | OK | 6 nodes / 5 edges as declared |
| prim_graph_tree_str_normalized_ok | str-normalized ids (int + string parent) | OK | 3→4 nodes; node 4 added under parent 2 |
| prim_graph_weighted_edges | weighted edges (u,v,w) | OK | 3 nodes / 2 edges |

`OK*` = renders correctly for content/counts but carries the known low-severity dup-defs bug.

**Error-only negative tests (no HTML, N/A for render review):** `add_edge_unknown_E1471`, `bad_edge_shape_E1474`, `empty_nodes_E1470`, `mixed_edges_E1474`, `over100_E1501`, `remove_edge_missing_E1472`, `tree_add_node_unknown_parent_E1436`, `tree_cycle_E1433`, `tree_reparent_bad_spec_E1435`, `tree_root_removal_E1434`.

## SUSPECTS

### prim_graph_node_int_as_string_E1115 — render-bug (contract mismatch)

**Evidence:**
- `.tex`: `nodes=[1,2,3]`, then `\recolor{G.node["1"]}{state=current}` (selector id is the **string** `"1"`).
- `.expect`: *"Graph int node addressed as string mismatches; selector matches nothing, command silently dropped (E1115 is a UserWarning, not an abort)."*
- `.html`: node `G.node[1]` carries `class="...scriba-state-current"` (current-count = 1). This is **identical** to the strict-match snippet `prim_graph_node_int_strict_ok` (`\recolor{G.node[1]}`), which also colors node 1 `current`.

**Why SUSPECT:** the contract says the string selector should match nothing and the recolor be dropped, leaving all nodes `idle`. Instead the renderer applied `state=current` to node 1 — i.e. it treated `G.node["1"]` and `G.node[1]` as the same selector (string-normalized), the opposite of what the `.expect` documents for Graph.

**Classification: render-bug** relative to the stated contract. The selector matched when the contract says it must not, so the documented E1115 "no-match, silently dropped" path did not occur.

**Caveat for triage:** the sibling Tree snippets (`prim_graph_tree_selector_int_or_string`, `prim_graph_tree_str_normalized_ok`) explicitly document and render *str-normalized* node ids (node[8] == node["8"]). If Graph node ids are in fact also str-normalized in current code, then the rendered output is correct and the `.expect` for this Graph snippet is **stale/wrong** (should read "matches via str-normalization", not "matches nothing"). Either way there is a real inconsistency between this snippet's contract and its output; it cannot be silently passed. Recommend the maintainer decide: (a) enforce strict int/string mismatch for Graph and fix the renderer, or (b) correct the `.expect` to reflect str-normalization. This is the only content-level discrepancy in the prefix.

## Dup-defs render-bug files (explicit list)

Low-severity known defect (Phase 1): directed graphs emit the arrow-marker `<defs>` block **twice** with duplicate `id="scriba-arrow-fwd"` / `id="scriba-arrow-rev"` (2× each). Confirmed by direct count (`defs=2`, `fwd_id=2`, `rev_id=2`). Content/node/edge/marker-ref output is otherwise correct.

All 5 prim_graph dup-defs files (matches Phase-1 SANITY-FLAGS exactly — all 5 flagged files in this prefix are mine):

1. `prim_graph_directed_true`
2. `prim_graph_layout_hierarchical`
3. `prim_graph_orientation_lr`
4. `prim_graph_orientation_tb`
5. `prim_graph_stable_directed_warns_ok`

No additional dup-defs cases found beyond Phase 1. Undirected graphs (`directed_false` and all default-undirected snippets) correctly emit `defs=0` / no markers. Trees emit no arrow markers (parent-child edges drawn as plain lines), consistent with intent.
