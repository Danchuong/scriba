# 00 — Param audit synthesis

**Date:** 2026-04-23
**Scope:** All primitive `ACCEPTED_PARAMS` vs docs (`docs/spec/primitives.md`, `docs/spec/svg-emitter.md`, `docs/primitives/matrix.md`, `docs/SCRIBA-TEX-REFERENCE.md`)
**Method:** 3 parallel Explore agents, direct source evidence with file:line citations.

## Categories

- **WORKS** — accepted, read, has rendered effect, documented.
- **LIES** — accepted and documented, but no rendered effect (or silently falls back).
- **UNDOCUMENTED** — accepted and works, but missing from user-facing docs.
- **VESTIGIAL** — in `ACCEPTED_PARAMS` but never read at all.
- **PHANTOM** — in docs but not in code.
- **STRUCTURAL** — code gap (e.g. missing `ACCEPTED_PARAMS` frozenset entirely).

## Tier 1 — Kill immediately (user-visible lies)

These mislead users into believing features exist. Priority fix:

| # | Primitive | Symbol | Category | Action |
|---|-----------|--------|----------|--------|
| 1 | Graph | `layout="circular"` | LIES | Remove from `primitives.md:340`, `svg-emitter.md:306` |
| 2 | Graph | `layout="bipartite"` | LIES | Remove from same |
| 3 | Graph | `layout="hierarchical"` | LIES | Remove from same |
| 4 | Graph | `layout="stable"` | LIES (init) | Wire routing branch or document as warm-start-only |
| 5 | Matrix | `colorscale="magma"` | LIES | Remove from `matrix.md` §3.1 |
| 6 | Matrix | `colorscale="plasma"` | LIES | Remove from same |
| 7 | Matrix | `colorscale="greys"` | LIES | Remove from same |
| 8 | Matrix | `colorscale="rdbu"` | LIES | Remove from same |
| 9 | Matrix | `title=` | PHANTOM | Remove from `matrix.md` §13.2 example |
| 10 | Matrix | `m.row[i]` selector | PHANTOM | Remove from `matrix.md` §4 |
| 11 | Matrix | `m.col[j]` selector | PHANTOM | Remove from `matrix.md` §4 |
| 12 | Matrix | `m.range[(i1,j1):(i2,j2)]` | PHANTOM | Remove from `matrix.md` §4, §5.3-5.4 |
| 13 | Plane2D | `xlabel` | LIES | Implement or drop from `ACCEPTED_PARAMS` + docs |
| 14 | Plane2D | `ylabel` | LIES | Same |
| 15 | Plane2D | `label` | LIES | Wire `self.label = params.get("label")` + render, or drop |

## Tier 2 — Kill / wire / drop vestigial

Internal gunk that adds noise without user-visible deception.

| # | Primitive | Symbol | Category | Action |
|---|-----------|--------|----------|--------|
| 16 | Graph | `layout_lambda` | VESTIGIAL | Wire through to `compute_stable_layout(lambda_weight=...)` or drop |
| 17 | Graph | `global_optimize` | LIES (warns) | Drop until GEP-20 ships, or document as v2.1 forward-compat |
| 18 | Array | `values` | VESTIGIAL | Drop from `ACCEPTED_PARAMS` (comment admits "Legacy alias — not consumed") |

## Tier 3 — Document what works

Capability exists, users can't discover it.

| # | Primitive | Symbol | Action |
|---|-----------|--------|--------|
| 19 | Graph | `show_weights` | Add to `primitives.md` §6 |
| 20 | Graph | `auto_expand` | Add to §6 or mark internal |
| 21 | Graph | `split_labels` | Add to §6 or mark internal |
| 22 | Graph | `tint_by_source` | Add to §6 or mark internal |
| 23 | Graph | `seed` (alias) | Document or remove alias |
| 24 | MetricPlot | `show_current_marker` | Add to reference §7.10 |
| 25 | MetricPlot | `yrange_right` | Same |
| 26 | MetricPlot | `ylabel_right` | Same |
| 27 | Stack | `orientation` | Add to reference §7.8 |
| 28 | Stack | `max_visible` | Same |

## Tier 4 — Structural

| # | Primitive | Issue | Action |
|---|-----------|-------|--------|
| 29 | Stack | No `ACCEPTED_PARAMS` frozenset → E1114 guard skipped | Add `frozenset({"items","orientation","max_visible","label"})` |

## Behavioral notes (not kills)

- DPTable 1D uses fixed `CELL_WIDTH`; Array uses content-derived width. Docs imply equivalence.
- Queue has no `orientation`; Stack does. Design asymmetry, undocumented.
- Plane2D `height` silently clamped when `aspect="equal"`. Should note in spec.

## Count

- **15 user-visible lies** (Tier 1) — biggest pedagogical hazard
- **3 internal vestigial/LIES** (Tier 2)
- **10 undocumented-but-working** (Tier 3)
- **1 structural bug** (Tier 4)

## Primitives that passed clean

- **Tree** — all 9 params wired and documented.
- **NumberLine** — all 4 params wired and documented.
- **Queue** — all 3 params wired and documented.
- **LinkedList** — all 2 params wired and documented.
- **VariableWatch** — all 2 params wired and documented.
- **CodePanel** — all 3 params wired and documented.
- **DPTable** — all 6 params wired and documented.
- **Grid** — all 4 params wired and documented.
- **HashMap** — all 2 params wired and documented.

## Sources

- `01-graph-tree.md` — Graph + Tree (agent a9f1f7d2a90c88978)
- `02-grid-family.md` — Array, DPTable, Grid, Matrix, HashMap (agent a67353f750be9134b)
- `03-plane2d-misc.md` — Plane2D, NumberLine, MetricPlot, Queue, Stack, LinkedList, VariableWatch, CodePanel (agent a449dde03da6ccfd3)
