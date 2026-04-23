# 01 — Graph + Tree param audit

**Date:** 2026-04-23
**Scope:** `scriba/animation/primitives/graph.py`, `scriba/animation/primitives/tree.py`
**Cross-check:** `docs/spec/primitives.md` §6/§7, `docs/spec/svg-emitter.md:305-309`, `docs/SCRIBA-TEX-REFERENCE.md`

## Graph

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `nodes` | WORKS | `graph.py:588` stores as `self.nodes`; used throughout `emit_svg` | Keep |
| `edges` | WORKS | `graph.py:610-631` parsed into `self.edges`; used in layout and SVG | Keep |
| `directed` | WORKS | `graph.py:632` → `self.directed`; read at `emit_svg` line ~1012, 1109 | Keep |
| `layout` | LIES | `graph.py:633` stores to `self.layout`. `self.layout` is **never read again** outside `__init__`. The initial layout call at line 708 unconditionally calls `fruchterman_reingold`. The warm-start relayout at line 861 always calls `compute_stable_layout` regardless of `self.layout`. Values `"circular"`, `"bipartite"`, `"hierarchical"` produce no different behavior from `"force"`. `"stable"` is documented in the error codes table but the routing branch does not exist. `docs/spec/primitives.md:340` and `docs/spec/svg-emitter.md:305-309` both list all five values as functional. | Strip `"circular"`, `"bipartite"`, `"hierarchical"` from docs; add a routing branch for `"stable"` or document it as LIES too until wired |
| `layout_seed` | WORKS | `graph.py:666-688` validates and stores to `self.layout_seed`; passed to `fruchterman_reingold` at line 714 and to `compute_stable_layout` at line 864 | Keep |
| `layout_lambda` | LIES / VESTIGIAL | `graph.py:575` lists in `ACCEPTED_PARAMS`; **never read from `params`** and `self.layout_lambda` never assigned in `__init__`. `compute_stable_layout` (graph_layout_stable.py:184) accepts a `lambda_weight` param, but `Graph.__init__` never passes it — always uses default 0.3. Undocumented in `primitives.md` §6. | Wire `self.layout_lambda = float(params.get("layout_lambda", 0.3))` and pass it, or remove from `ACCEPTED_PARAMS` |
| `seed` | UNDOCUMENTED | `graph.py:669` accepted as alias for `layout_seed` when `layout_seed` absent. Works correctly. Not in `primitives.md` §6 param table. | Document as alias or remove |
| `show_weights` | WORKS | `graph.py:634` → `self.show_weights`; read at `emit_svg` line ~1134 to control pill display | Document in `primitives.md` §6 |
| `label` | WORKS | `graph.py:690` → `self.label`; read in `emit_svg` line ~996 | Keep |
| `auto_expand` | WORKS | `graph.py:635` → `self.auto_expand`; read in `emit_svg` line ~1037 to scale positions | Document or mark internal |
| `split_labels` | WORKS | `graph.py:638` → `self.split_labels`; read in `emit_svg` line ~1267 | Document or mark internal |
| `tint_by_source` | WORKS | `graph.py:639` → `self.tint_by_source`; read in `emit_svg` line ~1254 | Document or mark internal |
| `global_optimize` | LIES | `graph.py:647` accepts and stores; lines 648-658 emit `UserWarning` stating it has no runtime effect. SA refine (GEP-20) not wired into `emit_svg`. Undocumented. | Remove from `ACCEPTED_PARAMS` until GEP-20 ships, or document as v2.1 forward-compat |

**Phantom capability in docs:** `svg-emitter.md:306-308` describes `"circular"`, `"bipartite"`, `"hierarchical"` as distinct algorithms with defined behaviors. They are not.

## Tree

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `root` | WORKS | `tree.py:152` required for standard kind; `_init_standard` raises E1430 if missing | Keep |
| `nodes` | WORKS | `tree.py:161` stored; used in layout and `emit_svg` | Keep |
| `edges` | WORKS | `tree.py:162-165` parsed; used to build `children_map` and in SVG rendering | Keep |
| `kind` | WORKS | `tree.py:99` → `self.kind`; read at line 104 to branch `_init_segtree`, `_init_sparse_segtree`, or `_init_standard` | Keep |
| `data` | WORKS | `tree.py:185` read inside `_init_segtree`; passed to `_build_segtree` | Keep |
| `range_lo` | WORKS | `tree.py:209` read inside `_init_sparse_segtree`; stored as `self.range_lo` | Keep |
| `range_hi` | WORKS | `tree.py:210` same path as `range_lo` | Keep |
| `show_sum` | WORKS | `tree.py:101` → `self.show_sum`; read at line 203 inside `_init_segtree` | Keep |
| `label` | WORKS | `tree.py:100` → `self.label`; read in `emit_svg` line ~599 | Keep |

Tree is clean. No kill list items.

## Kill list (Graph)

1. `layout="circular"` — **LIES**. Remove from `primitives.md:340` and `svg-emitter.md:306`.
2. `layout="bipartite"` — **LIES**. Same.
3. `layout="hierarchical"` — **LIES**. Same.
4. `layout="stable"` — **LIES** at construction. Warm-start uses `compute_stable_layout` unconditionally. Clarify or wire.
5. `layout_lambda` — **VESTIGIAL**. Never read; never passed through. Wire or drop.
6. `global_optimize` — **LIES** with `UserWarning`. Drop until GEP-20 ships.
7. `seed` alias — **UNDOCUMENTED**. Document or remove.
8. `show_weights`, `auto_expand`, `split_labels`, `tint_by_source` — **WORKS but UNDOCUMENTED** in `primitives.md` §6.
