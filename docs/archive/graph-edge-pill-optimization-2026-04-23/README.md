# Graph Edge-Pill Optimization Research (2026-04-23)

Research bundle evaluating current graph edge-pill placement and proposing a smart-label-inspired adaptation.

## Contents

| # | File | Summary |
|---|------|---------|
| 01 | [`01-current-audit.md`](./01-current-audit.md) | Audit of `graph.py:737–833` — 4 visual fails, 6 engineering issues, 5 collision gaps, 4 test gaps. **2 CRITICAL** (F1 + G1: pill overlaps node circle, confirmed in `dinic.html` + `mcmf.html`). |
| 02 | [`02-smart-label-study.md`](./02-smart-label-study.md) | Breakdown of the smart-label placer in `_svg_helpers.py`: 49 candidates (1 natural + 48 compass nudges), 7-penalty scoring (P1–P7, weights 0.3–40.0), segment + AABB obstacle model, greedy sequential with R-05 semantic sort, R-27c leader gate. Transfer table to graph edges. |
| 03 | [`03-external-survey.md`](./03-external-survey.md) | External survey: Graphviz (virtual-node `label` + R-tree `xlabel`), Mermaid (hardcoded `labelpos:'c'`), D3-graphviz / Cytoscape (no edge-label logic), yFiles `(t, side, distance)` discrete model, academic (ELP NP-hard, greedy MIS). |
| 04 | [`04-synthesis.md`](./04-synthesis.md) | Adaptation design: keep current fast path, fix F1/G1 in Phase 0, reuse `_pick_best_candidate` in Phase 1 with 24-candidate `(t, side, offset)` generator + `EdgePillContext`. 4-phase migration with LOC estimates. |

## Related

- `docs/archive/graph-edge-pill-logic-2026-04-23.md` — documentation of the *current* post-bugfix logic (commits `f3bc43d`, `db15cb2`). Read first.
- `docs/spec/smart-label-ruleset.md` — R-01 through R-31+ ruleset governing smart-label placer.

## Recommended next step

Phase 0 incremental fixes (~50 LOC) close both CRITICAL bugs without introducing the full scoring pipeline. Worth committing before Phase 1 design review.

## Addendum — 2026-04-23 product decision

User chose **edge-aligned rotation** over Graphviz-style plain text. Rationale + spec in `04-synthesis.md` §*Rotation addendum*. Implementation plan at `docs/plans/edge-pill-rotation-impl-plan.md`. Demo: `examples/fixes/edge_pill_rotated_demo.html` (gitignored).

**Phase order becomes:**
1. Phase 0 — F1/G1 guard + determinism + clamp (~50 LOC)
2. Phase 0.5 — Rotation (~80 LOC)
3. Phase 1+ — Full smart-label adoption (as originally planned, updated with OBB-aware obstacles).
