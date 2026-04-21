# Smart-Label Ruleset Hardening — 2026-04-21 (Round 3)

Round 3 closes **enforcement gaps** in the normative v2 ruleset produced
by Round 2. Seven opus agents in parallel produced ~8,570 lines of
foundation material plus a runnable Alloy formal model.

> **Round 1** (`../smart-label-ruleset-audit-2026-04-21/`) — operational
> gaps (bugs, coverage, WCAG fails).
> **Round 2** (`../smart-label-ruleset-strengthening-2026-04-21/`) —
> specification gaps (ambiguity, missing conformance surface). Produced
> v2 ruleset.
> **Round 3** (this folder) — enforcement gaps (prose → tests, gates,
> formal model). Foundation for Round 4 implementation.

## Start here

- **[00-synthesis.md](00-synthesis.md)** — TL;DR, action list, cross-cutting findings, open questions.

## Per-axis reports

| # | File | Lines | Focus |
|---|------|------:|-------|
| 1 | [01-conformance-suite.md](01-conformance-suite.md) | 1419 | 42-invariant → pytest map, 7-file test layout, helper API, 5 worked examples (one intentional TDD-Red against current AC-6 bug). |
| 2 | [02-golden-corpus.md](02-golden-corpus.md) | 1267 | 44 fixtures (8 bug + 6 critical + 12 high + 18 good-path), SHA256 pinning, SVG normalizer, rebase workflow, 5 fixture drafts. |
| 3 | [03-lint-and-protocol-enforcement.md](03-lint-and-protocol-enforcement.md) | 1658 | FP-1..FP-6 AST patterns, standalone `scripts/lint_smart_label.py` design, 15-primitive violation audit (12 instances across 5 primitives), runtime `PrimitiveProtocol`. |
| 4 | [04-open-issue-resolution.md](04-open-issue-resolution.md) | 1008 | 20 OPEN / AT-RISK / PROPOSED markers inventoried. ACCEPT/FIX/DEFER decisions. v2-final patch plan. 4 blockers identified. |
| 5 | [05-determinism-property-tests.md](05-determinism-property-tests.md) | 760 | 7 Hypothesis properties for D-1..D-4. Strategies for AABB, unicode, NaN/inf. KaTeX quarantine. 0 expected failures on current code. |
| 6 | [06-a11y-automation.md](06-a11y-automation.md) | 1216 | Tool choice per A-1..A-7. Machado 2009 CVD matrices. 6×6 palette pass/fail matrix. Remediation candidates. CI gate date 2026-05-05. |
| 7 | [07-alloy-model.md](07-alloy-model.md) | 890 | Design notes for the .als model, 5-bit scope rationale, 10 encoded / 18 unencodable / 12 deferred invariants. |
| 7b | [smart-label-model.als](smart-label-model.als) | 353 | Runnable Alloy 6 model: 8 sigs, 7 facts, 5 preds, 11 asserts, 11 `check` commands, 3 `run` commands. All three geometric tie-breakers proven consistent. |

**Total**: ~8,570 lines foundation + 353 lines runnable formal model.

## How to use this audit

1. Read `00-synthesis.md` end-to-end (~15 min).
2. Read `04-open-issue-resolution.md` next — it defines what blocks
   v2-final and what can ship in v0.11.0.
3. For each of the 4 blockers in §"Consolidated action list", open an
   issue or PR and cite the relevant per-axis report for implementation
   detail.
4. Launch Round 4 (implementation) in parallel workstreams:
   - Stream A (tests): conformance suite + determinism + corpus
     (reports 01, 02, 05)
   - Stream B (lint): lint script + `PrimitiveProtocol` (report 03)
   - Stream C (a11y): palette remediation + role fix (report 06)
   - Stream D (formal, optional): commit .als + CI hook (report 07)

## Scope

**In scope**: enforcement design — tests, lint, gates, fixtures,
formal model for the v2 normative ruleset.

**Out of scope**: actual code patches (Round 4). The only changes
Round 3 wrote to the codebase are the documents in this folder.

## Status

All 7 agents completed successfully. Synthesis and README written. No
code changes yet. The v2 ruleset at `docs/spec/smart-label-ruleset.md`
still contains 20 open markers; Round 3 resolves them on paper, Round 4
will resolve them in code.

**Next step**: human review of 04-open-issue-resolution.md decisions,
then Round 4 implementation PRs.
