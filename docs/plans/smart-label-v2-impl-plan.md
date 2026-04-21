---
title: Smart-Label v2 Implementation Plan
version: 1.0.0-draft
status: draft
date: 2026-04-21
author: architect (W1) + Claude Opus 4.7
inputs:
  - docs/spec/smart-label-ruleset.md (v2.0.0-draft.r3)
  - docs/archive/smart-label-ruleset-hardening-2026-04-21/
supersedes: N/A
---

# Smart-Label v2 Implementation Plan

## 1. Executive Summary

Close the three code-requiring blockers (ISSUE-A4 opacity, ISSUE-A5
dashed leader, ISSUE-below-math AC-6 off-by-one) and land the MW-3
`_place_pill` helper that makes the per-candidate clamp invariant
enforceable at the primitive boundary. Execute in **3 waves, 6–7
agents**, serialized on `_svg_helpers.py` to avoid merge conflicts.
Total engineering budget: ~44h across 7 PRs. Earliest v2-final
shippable: **v0.10.x**. a11y gate flips blocking **2026-05-05**.

## 2. Scope

**In scope.**
- Fix 3 blocker issues with code-level patches.
- Introduce MW-3 `_place_pill` in `_svg_helpers.py` as sole placement entry-point.
- Migrate 15 primitives to `PrimitiveProtocol`. Plane2D first (FP dense).
- Stand up first-commit conformance subset (5 pytest files).
- Seed golden corpus (3 fixtures) with SHA256 pinning.
- Add `scripts/lint_smart_label.py` + CI hook (advisory).
- Commit Alloy `.als` as documentation.

**Out of scope.**
- Full 44-fixture golden corpus (v0.11.0).
- MW-2 typed registry (v0.11.0+).
- T-4 KaTeX nightly job (v0.12.0+).
- A-2 math 0.90× multiplier retire (v0.11.0).

## 3. Architecture Overview

### 3.1 MW-3 `_place_pill` helper

Sole placement primitive. Per-candidate clamp **inside** the candidate
loop (not after selection) closes ISSUE-A3 clamp-race.

```python
def _place_pill(
    *,
    natural_x: float, natural_y: float,
    pill_w: float, pill_h: float,
    placed_labels: list[_LabelPlacement],
    viewbox_w: float, viewbox_h: float,
    side_hint: str | None = None,
    overlap_pad: float = 0.0,
    _debug_capture: dict[str, Any] | None = None,
) -> tuple[_LabelPlacement, bool]:
    """
    Return (placement, fits_cleanly).

    - Generates N candidates around (natural_x, natural_y).
    - For each candidate: clamp-to-viewport FIRST, then collision-check.
    - Tie-breakers: G-5 (below > above > right > left).
    - Emits debug to _debug_capture if provided (SCRIBA_DEBUG_LABELS).
    """
```

**Key invariants enforced:**
- **AC-3** (pill inside viewport): clamp pre-collision so every
  returned placement is within `[0, viewbox_w] × [0, viewbox_h]`.
- **C-4** (non-overlap): tested against `placed_labels` after clamp.
- **G-5** (tie-break): deterministic ordering below > above > right > left.
- **AC-6** (label below math): orientation + height handled by caller
  passing correct `natural_y` and `side_hint`.

### 3.2 Engine flag lifecycle

`SCRIBA_LABEL_ENGINE ∈ {legacy, unified, both}` already present.

| Phase | Default | Notes |
|-------|---------|-------|
| v0.10.x (now) | `unified` | legacy kept as rollback |
| v0.11.0 | `unified` | legacy removed if zero field regressions |

## 4. PR Sequence

| # | Title | LOC | Agent | Blocks | Est. |
|---|-------|----:|-------|--------|-----:|
| PR-1 | ISSUE-below-math AC-6 two-line fix + test | ~20 | W2-A | — | 0.5h |
| PR-2 | ISSUE-A4 opacity raise + contrast test | ~15 | W2-D | — | 0.5h |
| PR-3 | MW-3 `_place_pill` + Plane2D migration + conformance subset | ~800 | W2-A | all downstream | 14h |
| PR-4 | ISSUE-A5 dashed leader (non-colour redundant cue) | ~60 | W2-D | PR-3 | 1h |
| PR-5 | `scripts/lint_smart_label.py` + `PrimitiveProtocol` advisory | ~400 | W2-C | PR-3 | 6h |
| PR-6 | Golden corpus seed (3 fixtures) + normalizer | ~300 | W2-B | PR-3 | 4h |
| PR-7 | Remaining 14 primitives migrate to Protocol | ~600 | W3 | PR-5 | 12h |

Parallelism: PR-1, PR-2 ship immediately (independent). PR-3 is
longest-path. PR-4/5/6 branch from PR-3. PR-7 serializes after PR-5.

## 5. Wave Topology

### Wave 1 — Plan (this doc)
Single architect agent. Output: this file. **DONE.**

### Wave 2 — Parallel implementation (4 agents)

File-touch matrix designed to avoid conflicts:

| Stream | Agent | Owns | Reads only | Acceptance |
|--------|-------|------|------------|------------|
| A (core) | python | `_svg_helpers.py`, `plane2d.py`, `tests/conformance/smart_label/` | all primitives | PR-1 + PR-3 green |
| B (corpus) | python | `tests/golden/smart_label/`, `tests/helpers/svg_normalize.py` | `_svg_helpers.py` | 3 fixtures SHA256-pinned |
| C (lint) | python | `scripts/lint_smart_label.py`, `scriba/animation/primitives/_protocol.py` | all primitives | lint warns 12 FPs |
| D (a11y) | python | palette tokens, `arrow.py` leader line | WCAG contrast libs | A-1 + A-4 pass |

### Wave 3 — Finalize (2 agents)
- Determinism Hypothesis tests (7 properties for D-1..D-4).
- 14 primitives Protocol registration (post-Plane2D template).
- Alloy `.als` commit + `docs/formal/README.md`.

## 6. CI Gates

| Gate | Advisory until | Blocks merge | Notes |
|------|---------------:|-------------:|-------|
| Conformance (5 tests) | — | now | MUST pass |
| Lint FP-1..FP-6 | 2026-05-05 | flips blocking after Plane2D clean | warn-only initially |
| a11y contrast + CVD | 2026-05-05 | flips blocking on that date | WCAG 2.2 AA |
| Golden corpus diff | 2026-05-05 | rebase workflow documented | SVG normalized |
| `PrimitiveProtocol` register | never (v0.10.x) | advisory warn-on-register | flip v0.11.0 |
| Determinism (Hypothesis) | — | now | all 7 expected green |

## 7. Rollback Plan

- MW-3 regression → `SCRIBA_LABEL_ENGINE=legacy` per-process.
- Blocker patch regression → revert specific PR; blockers are
  independent (PR-1, PR-2, PR-4 each stand alone).
- Lint false positive → demote specific FP to warn in
  `.github/workflows/*` without code change.

## 8. Risk Register

| # | Risk | Prob | Impact | Mitigation |
|---|------|-----:|-------:|------------|
| R1 | MW-3 regresses existing primitive layouts | M | H | `SCRIBA_LABEL_ENGINE=both` dual-emit diff; field tests |
| R2 | Palette change breaks brand consistency | L | M | Confine to opacity; no hue change for `info`/`muted` |
| R3 | CVD matrices drift between libs | L | L | Pin Machado 2009 coefficients in repo |
| R4 | Plane2D migration exceeds 4h budget | M | M | Scope-bound to 5 FP sites; defer unrelated cleanup |
| R5 | Lint AST false positive | M | L | Advisory until 2026-05-05; allowlist escape hatch |
| R6 | Golden SVG non-determinism | L | H | Normalizer strips timestamps + sorts attrs |
| R7 | Protocol adoption blocks a primitive import | L | H | `warn-on-register` not `fail-on-register` in v0.10.x |
| R8 | Alloy tooling drift | L | L | Doc-only commit; no CI dep |

## 9. Open Decisions (human, before Wave 2)

1. **A-4 palette scope** — semantic triad only (`good`/`warn`/`error`)
   or all 6 tokens? **Recommend semantic triad only** — `info`/`muted`
   become decorative, simpler to defend.
2. **Alloy CI** — nightly `alloy check` or doc-only `.als`?
   **Recommend doc-only** — no field value until MW-2 lands.
3. **`PrimitiveProtocol` strictness v0.10.x** — `warn-on-register` or
   `fail-on-register`? **Recommend warn-on-register** — safe during
   migration window.
4. **Dasharray for `warn` leader** — `"3,2"`, `"4,2"`, `"6,3"`?
   **Recommend `"3,2"`** — tightest rhythm, most distinguishable from
   `error` solid stroke at render scale.

## 10. Acceptance

Wave-2 complete when:
- PR-1..PR-6 merged to `main`.
- 3 BLOCKER ISSUE markers removed from `docs/spec/smart-label-ruleset.md`.
- First-commit conformance subset green in CI.
- 3 golden fixtures SHA256-pinned.
- Lint advisory surfaces exactly 12 FPs (matches R3 audit).
- a11y contrast + CVD tests green for chosen palette scope.

Wave-3 complete when:
- 14 primitives registered via `PrimitiveProtocol`.
- 7 Hypothesis properties green.
- `docs/formal/smart-label-model.als` + `README.md` committed.
- v0.10.x tagged.

## Appendix A. 15-Primitive Migration Table

| # | Primitive | FPs | Effort | Owner | Wave |
|---|-----------|----:|-------:|-------|-----:|
| 1 | Plane2D | 5 | 4h | W2-A | 2 |
| 2 | Graph | 3 | 1.5h | W3 | 3 |
| 3 | Queue | 2 | 1.5h | W3 | 3 |
| 4 | NumberLine | 2 | 1.5h | W3 | 3 |
| 5–15 | Array, Stack, Tree, LinkedList, HashMap, Heap, Matrix, Grid, Timeline, BinaryTree, Graph3D | 0 | 0.25–0.5h each | W3 | 3 |

Plane2D alone = 5 of 6 FP categories. Migrating it first unlocks the
`_place_pill` call-site pattern for all other primitives.

## Cross-references

- v2 ruleset: `docs/spec/smart-label-ruleset.md`
- R3 synthesis: `docs/archive/smart-label-ruleset-hardening-2026-04-21/00-synthesis.md`
- R3 open-issue resolution: `docs/archive/smart-label-ruleset-hardening-2026-04-21/04-open-issue-resolution.md`
- Error codes: `docs/spec/error-codes.md` (E1560–E1579)
