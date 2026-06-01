# SCRIBA-TEX-REFERENCE.md — Completion Plan (close remaining PARTIAL/OPEN)

**Date:** 2026-06-01
**Input:** `docs/archive/tex-reference-audit-2026-06-01/verify-reaudit.md` (post-Phase-4 status: ~68% closed, ~27% partial, ~5% open — all CRITICAL/HIGH already done).
**Target:** `docs/SCRIBA-TEX-REFERENCE.md`. **Goal:** drive remaining findings to CLOSED.
**Scope:** doc-only, single file → serial integrator (main thread); no parallel edits. All remaining items are LOW severity (cross-links, ctor/dynamic parity, tag cleanup, glossary/index tables). No code changes — facts come from `00-ground-truth.md`.

## Already closed in Phase 4 (`45edb72`) — do not redo
§8 five-families wording (C5); Matrix `cell_size`=24; `grid` §10→Appendix pointer; MetricPlot/Plane2D limits in §14.

## Phases (each = one commit)

### Phase 5 — Field-clarity & completeness tail
- Plane2D ctor list element shapes: cross-link `points=`/`lines=`/`segments=`/`polygons=`/`regions=` rows to the dynamic `add_*` shapes (field-clarity #6/#11/#12).
- Stack `items` dict form `{label,value?}` (completeness #7, field-clarity #18).
- Queue direct cell set `\apply{q.cell[i]}{value=}` (completeness #13).
- MetricPlot: note `E1486` (degenerate range), `E1487` (same-axis series share scale), and `E1483` in §7.10 (field-clarity #14/#17).

### Phase 6 — Consistency & noise tail
- §7.4: drop the redundant `G.node["A"]` from the example selector line (C7) — quoting rule lives in §8.
- §8 selector matrix: fill the `All` column for Stack/HashMap/LinkedList/MetricPlot (ground-truth cross-check).
- Strip leftover internal tags: `(supported since v0.8.2)` at §5.11 (corr #4 / s-n #9); `(R-32)` in §13.8 heading (s-n #8).
- §15: add the self-cited codes the body uses but the table omits (E1004/E1005/E1052/E1113/E1320/E1437/E1471/E1472/E1433–E1436), or note they live in `spec/error-codes.md` (self-sufficiency #5).

### Phase 7 — Disambiguation & navigability tail
- Add a single **Indexing conventions** table (0-based Array/Grid/Plane2D, 1-based CodePanel, Stack `item[0]`=bottom) — disambiguation #3.
- Add a short **`label` glossary** enumerating its 4 meanings (annotation pill / `\step` id / env aria-label / primitive caption) — disambiguation #2.
- Add a **diagram vs animation** capability mini-table in §4 — disambiguation #10.
- Per-primitive "Gotchas: see §13.x" back-pointers (Stack/Queue→§13.1, CodePanel→§13.9, annotate→§13.8) — navigability #4.

### Phase 8 — Verify (1 agent)
Re-audit the remaining items + render the §9 examples once more; confirm no new dangling anchors/refs and the new tables match ground truth. Write `docs/archive/.../verify-completion.md`.

## Agent budget
| Phase | Agents |
|------|--------|
| 5 / 6 / 7 | 0 (serial integrator) |
| 8 verify | 1 |
| **Total** | **1** |

## Out of scope
Multi-file restructuring; any code change. If a remaining item turns out to require a code fix (not expected), stop and report rather than editing code.
