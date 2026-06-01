# SCRIBA-TEX-REFERENCE.md — Fix Plan

**Date:** 2026-06-01
**Input:** `docs/archive/tex-reference-audit-2026-06-01/` (8 criterion reports) + `docs/analysis/tex-reference-audit-2026-06-01.md`
**Target:** `docs/SCRIBA-TEX-REFERENCE.md`
**Goal:** close audit findings so "read one file → author valid `.tex`" holds.
**Track:** this is **Track A (doc-only)**. It runs **AFTER** Track B
(`tex-reference-code-quality-plan-2026-06-01.md`), which fixes the loại-B code
defects first — so this doc describes the *new* (correct) behaviour, not the old
broken one. The 5 loại-B items (tooltip, `\hl` E13xx, `${var}` footgun, colorscale,
Plane2D silent-fail) are **owned by Track B** and excluded here.

## Hard constraint

All edits hit **one file**. Parallel agents must **NEVER edit it concurrently**
(write conflicts). Pattern every phase: **fan-out = DRAFT only (read-only, return
markdown blocks); apply = SERIAL** (one integrator agent or main thread applies in
order). Line numbers shift after each apply → drafters cite section anchors, not raw
line numbers, and the integrator re-locates before each edit.

## Phases

### Phase 0 — Ground truth (1 agent, read-only) — BLOCKING
Extract authoritative facts from code into a scratch sheet so every later edit uses
real data (the audit found the doc invents things).
- Per-primitive `ACCEPTED_PARAMS` + real defaults (`scriba/animation/primitives/`)
- Real error catalog (`scriba/animation/errors.py` `ERROR_CATALOG`)
- Confirm phantom items: `tooltip=`, `E1320`, `E1321`, `colorscale` names, `add_region`/`add_line` real shapes
- **Output:** `docs/archive/.../00-ground-truth.md`. **Gate:** main thread reads it before Phase 1+.

### Phase 1 — Correctness & consistency (1 agent, serial) — depends on P0
Small, scattered, interdependent edits → one agent, no fan-out.
- Delete phantom `tooltip=` (§5.5) and `E1320/E1321` (§5.13)
- Fix §8 Tree node-id rule (stale after `8989a10`: Tree=str-normalized ≠ Graph=strict)
- Fix §13.2 interpolation staleness (after `cbdd7ce`: `\apply` value/label resolves)
- Fix E1501 (two contradictory defs §7.4/§14 vs §15) + E1502 wrong meaning (§7.4)
- Fix dangling cross-ref "§7.1 of the spec" → §5.13 (L288/L290)
- Fix state count 8-vs-9 (§5.7 vs §6); lock boolean casing `true`/`false`
- **Output:** edited doc. **Gate:** `git diff` review.

### Phase 2 — Completeness + field clarity (4 drafters ∥ + 1 integrator) — depends on P0
Biggest chunk: one full param table (type/default/allowed/example) per primitive.
- 4 drafter agents split the 15 primitives (~4 each), each returns ready-to-paste
  tables + fixes for: `add_region`, `colorscale`, `add_line`, Matrix/Grid `data`
  shape, `ticks`, `labels` vs `label`, missing ops (`set_weight`, VariableWatch),
  alias params (`source=`,`values=`,`n=`,`seed=`), missing codes (E1473/E1483)
- 1 integrator applies all blocks serially
- **Output:** edited doc. **Gate:** every primitive has one param table.

### Phase 3 — Structure & cleanup (2 drafters ∥ + 1 integrator) — depends on P1, P2
Global/structural, interdependent (TOC must reflect new appendix).
- Drafter A: signal-to-noise — move `global_optimize`, diagram `grid`, debug env
  flags, R-22/Hirsch/R-06 block into a new "Appendix A — Internal / forward-compat";
  reframe §5.8 "read that document" as a maintainer-only note; repoint §15 to
  `docs/spec/error-codes.md`
- Drafter B: navigability + disambiguation — top TOC (anchor links), "Index by Task"
  table, consolidate interpolation into §5.11 (reciprocal pointer from §13.2), add
  `label` vs `labels` vs-table + an indexing-base table
- 1 integrator applies A then B
- **Output:** edited doc. **Gate:** TOC + appendix present, no orphan refs.

### Phase 4 — Verify (2 agents ∥) — depends on P3
- Agent 1: re-run the 8-criteria check on the edited doc; confirm each finding closed
- Agent 2: extract every fenced `latex` example in the doc, render via `render.py`,
  confirm zero errors (catches newly-introduced bad examples)
- **Output:** `docs/archive/.../verify-report.md`. **Gate:** all findings closed + examples render clean.

## Agent budget

| Phase | Parallel | Serial | Total |
|------|----------|--------|-------|
| 0 Ground truth | — | 1 | 1 |
| 1 Correctness/consistency | — | 1 | 1 |
| 2 Completeness/field-clarity | 4 draft | 1 apply | 5 |
| 3 Structure/cleanup | 2 draft | 1 apply | 3 |
| 4 Verify | 2 | — | 2 |
| **Total** | | | **12** |

## Sequencing & commits

Phases are **strictly sequential** (P0→P1→P2→P3→P4); only the drafters *within* P2/P4
run in parallel. One commit per phase (P1–P3), so each is independently reviewable;
P0/P4 outputs are audit artifacts (commit with their phase).

## Out of scope

No code changes — doc only. Restructuring `SCRIBA-TEX-REFERENCE.md` into multiple
files is deferred (would break the single-file promise this plan is fixing).
