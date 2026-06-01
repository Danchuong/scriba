# SCRIBA Code-Quality Fix Plan (Track B)

**Date:** 2026-06-01
**Origin:** audit loại-B findings — cases where the doc exposed a *code* defect
(phantom feature, silent failure, footgun), not just stale text.
**Relation:** runs **BEFORE** the doc-fix plan (`tex-reference-fix-plan-2026-06-01.md`).
Doc then describes the *new* (correct) behaviour, not the old broken one.
**Theme:** every item is a **silent-failure / phantom** → fix = *fail loud*
(boundary validation + real error code), per CLAUDE.md "never silently swallow errors".

## Findings → intended fix

| # | Finding | File(s) | Intended fix | Decision needed |
|---|---------|---------|--------------|-----------------|
| B1 | `tooltip=` documented, never implemented | `scene.py` | **Remove** (no demand) OR implement hover tooltip | **implement vs remove** |
| B2 | `\hl` silently skips bad/unknown step-id (doc claims E1320/E1321) | `hl_macro.py`, `renderer.py` | Add validation: raise E1320 (outside `\narrate`) / E1321 (unknown id) | none — impl as documented |
| B3 | `${var}` in selector-index outside `\foreach` → silent no-op + warning | `scene.py` / selector resolver | Resolve it (extend `cbdd7ce`) OR keep + loud error | **resolve vs error-out** |
| B4 | `colorscale` only `viridis`; unknown name silently falls back | `matrix.py` | Raise/warn on unknown name; optionally add more scales | **add scales? (optional)** |
| B5 | Plane2D / `\apply` malformed field value renders wrong silently | `plane2d.py`, `scene.py` | Validate at boundary → raise E1437/E-code instead of garbage | none — validate |

## Hard rules (per project CLAUDE.md / GitNexus)

- **`gitnexus_impact` before editing any symbol**; report blast radius; stop on HIGH/CRITICAL.
- **TDD**: write failing test first, then fix.
- **`gitnexus_detect_changes` before each commit**; one commit per finding.

## Phases

### Phase C0 — Triage & decide (1 agent, read-only) — BLOCKING
Confirm current behaviour in code for B1–B5; resolve the 3 decision points
(B1 implement/remove, B3 resolve/error, B4 add-scales y/n) with a recommendation
each. **Output:** `docs/archive/.../C0-code-triage.md`. **Gate:** user signs off
the 3 decisions before C1.

### Phase C1 — Fixes (mixed parallel/serial) — depends on C0
Each fix = impact analysis → failing test → fix → tests green → commit.
- **Parallel (disjoint files):** B2 `hl_macro.py`, B4 `matrix.py`, B5 `plane2d.py`
  → 3 agents, worktree isolation.
- **Serial after (shared `scene.py`):** B1 then B3 → 1 agent, sequential (both touch
  `_apply_apply` / resolver; avoid conflict).
- **Output:** up to 5 commits. **Gate:** each fix's new test passes + no regressions.

### Phase C2 — Verify (1 agent) — depends on C1
Full suite (`pytest`, hypothesis-excluded set as in this session) + render the
affected example `.tex` to confirm bad input now raises loudly. **Output:**
`docs/archive/.../C2-code-verify.md`.

## Agent budget

| Phase | Parallel | Serial | Total |
|------|----------|--------|-------|
| C0 triage | — | 1 | 1 |
| C1 fixes | 3 (worktree) | 1 | 4 |
| C2 verify | — | 1 | 1 |
| **Total** | | | **6** |

## Sequencing

C0 → (user signs off decisions) → C1 → C2 → **then** doc-fix plan Phase 1+.
Code track and doc track never overlap (doc must describe finished code behaviour).
