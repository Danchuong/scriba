# Smart-Label Ruleset Hardening — 2026-04-21 (Round 3)

**Purpose.** Round 2 produced the normative v2 document. Round 3 closes
**enforcement gaps**: verify clauses → executable tests, forbidden
patterns → lint gates, known-bad repros → pinned golden corpus, open
issues → decided, determinism axis → property tests, accessibility
axis → automated measurement, tie-breakers → formal model.

Seven opus agents in parallel produced this foundation. Each agent read
v2 + Round-2 synthesis and addressed one enforcement axis. Total
output: ~8,110 lines of foundation + 353 lines of runnable Alloy.

## TL;DR

- **Invariant coverage achievable**: 34/42 hard + 5 xfail + 3 manual = 42/42 under a gated suite.
- **Forbidden-pattern violations today**: 12 unique primitive×FP instances across 5 primitives. Plane2D is the single biggest offender.
- **Currently-failing a11y pairs**: 2 distinct colour pairs (`info` vs `muted` all-conditions; `warn` vs `error` under deuteranopia).
- **Open markers in v2 draft**: 20 total → 1 ACCEPT, 6 FIX (4 block v2-final), 13 tracked under existing milestones.
- **Golden corpus size**: 44 fixtures → 30/42 invariant coverage (71.4%) today, 36/42 (85.7%) with partial.
- **Determinism properties**: 7 distinct, 0 expected failures on current code.
- **Alloy model**: 10 invariants encoded, 11 `check` commands, all three geometric tie-breakers proven consistent.
- **Earliest shippable v2-final**: v0.10.x after 4 blockers land. Recommended CI gate date for a11y: **2026-05-05**.

## Where to start reading

| Order | Report | Read for |
|------:|--------|----------|
| 1 | [04-open-issue-resolution.md](04-open-issue-resolution.md) | What blocks v2-final, what ships in v0.11, what defers. **Read this before any code change.** |
| 2 | [01-conformance-suite.md](01-conformance-suite.md) | How each Verify clause becomes a pytest. Contains 5 worked examples incl. one intentional TDD-Red. |
| 3 | [03-lint-and-protocol-enforcement.md](03-lint-and-protocol-enforcement.md) | 15-primitive FP audit + `scripts/lint_smart_label.py` + runtime `PrimitiveProtocol`. |
| 4 | [02-golden-corpus.md](02-golden-corpus.md) | 44 fixtures, SHA256 pinning, sanitization pipeline, rebase workflow. |
| 5 | [06-a11y-automation.md](06-a11y-automation.md) | WCAG contrast + Machado CVD + 6×6 matrix + concrete remediation. |
| 6 | [05-determinism-property-tests.md](05-determinism-property-tests.md) | Hypothesis strategies, 7 properties, no new dep needed. |
| 7 | [07-alloy-model.md](07-alloy-model.md) + [smart-label-model.als](smart-label-model.als) | Formal consistency of tie-breakers. 5-bit integer scope, 11 assertions. |

## Per-axis report inventory

| # | File | Lines | Key deliverable |
|---|------|------:|-----------------|
| 1 | [01-conformance-suite.md](01-conformance-suite.md) | 1419 | 42-row invariant→test map, 7-file directory layout, helper API, 5 worked pytest examples. |
| 2 | [02-golden-corpus.md](02-golden-corpus.md) | 1267 | 44-fixture catalogue (8 bug + 6 critical + 12 high + 18 good-path), SVG normalizer, rebase procedure, 5 fixture drafts. |
| 3 | [03-lint-and-protocol-enforcement.md](03-lint-and-protocol-enforcement.md) | 1658 | FP-1..FP-6 AST patterns, standalone lint script sketch, 15-primitive audit, `PrimitiveProtocol`. |
| 4 | [04-open-issue-resolution.md](04-open-issue-resolution.md) | 1008 | 20 open markers inventoried, ACCEPT/FIX/DEFER for each, v2-final patch plan. |
| 5 | [05-determinism-property-tests.md](05-determinism-property-tests.md) | 760 | 7 Hypothesis properties for D-1..D-4, strategies, KaTeX quarantine. |
| 6 | [06-a11y-automation.md](06-a11y-automation.md) | 1216 | Tool choice per invariant, Machado matrices, 6×6 palette matrix, remediation. |
| 7 | [07-alloy-model.md](07-alloy-model.md) | 890 | Design notes for .als model, scope rationale, encoded/deferred list. |
| 7b | [smart-label-model.als](smart-label-model.als) | 353 | Runnable Alloy 6: 8 sigs, 7 facts, 5 preds, 11 asserts, 11 check commands. |

**Total**: ~8,570 lines foundation + runnable formal model.

## Consolidated action list

**Blockers for v2-final (must ship together, commit order):**

1. **Text-only edits** per 04-open-issue-resolution.md §v2-final patch plan — remove "code update pending" qualifier, close ISSUE-A1.
2. **ISSUE-A4 fix** — raise `info`/`muted` group opacity to meet A-1 contrast.
3. **ISSUE-A5 fix** — run CVD simulation on palette, confirm or patch A-4.
4. **ISSUE-below-math fix** — two-line patch to `position_label_height_below` to close AC-6.

**v2-final supporting commits (land after blockers):**

5. First-commit conformance subset — 5 tests (G-1, C-4, D-2a/b, AC-6) in `tests/conformance/smart_label/`.
6. First-commit golden corpus — 3 fixtures: `ok-simple`, `critical-2-null-byte`, `bug-B`.
7. First-commit determinism — `test_d2a` + `test_d2b` + `test_d1_emit_arrow_svg` + `test_d4`.
8. `scripts/lint_smart_label.py` + CI hook, warning-only initially.
9. `PrimitiveProtocol` + registration gate, advisory initially.
10. Alloy model `.als` + `docs/formal/README.md` describing how to run.

**v0.11.0 targets:**

11. ISSUE-A2 — retire or re-justify 0.90× math multiplier.
12. ISSUE-A3 — per-candidate clamp via MW-3 `_place_pill` helper.
13. Expand conformance suite to 34 hard assertions.
14. Expand golden corpus to full 44 fixtures.
15. Flip a11y gate to blocking on **2026-05-05** after A-6 `role` fix + warn/error pattern fix land.
16. Flip lint to error on FP-1, FP-4 after Plane2D migration (~4 h).

**v0.12.0+:**

17. Expand golden corpus to MW-2 collision scenarios (C-6, C-7).
18. Full `PrimitiveProtocol` enforcement — move from advisory to blocking.
19. T-4 KaTeX nightly job wired in.

## Cross-cutting findings

### Palette problem is real (reports 06 + 04)

`info`/`muted` fail A-4 in all four vision conditions. `warn`/`error`
fail under deuteranopia. ISSUE-A4 and ISSUE-A5 were already flagged in
Round 2; Round 3 quantifies them: 5 condition-pair failures total.
**Non-colour redundant cues** (dashed leader lines) resolve
`warn`/`error` without palette change. `info`/`muted` need either
palette shift OR reclassification of A-4 to semantic-triad-only.

### Plane2D is the FP concentration (report 03)

Plane2D alone accounts for 5 of the 6 FP categories. Migration budget:
~4 h. No other primitive is close. Recommendation: land Plane2D cleanup
in the same PR as MW-3 `_place_pill` helper, since the helper eliminates
the FP-1/FP-3 call-site pattern.

### Determinism is structurally safe (report 05)

All three emitters are pure functions of their arguments; no global
mutable state, no randomness source, no timing dep. D-axis tests are
expected to pass out of the gate. This is good news — it means the
determinism axis is a **checkpoint**, not a **battle**. KaTeX version
drift is the one escape hatch, already documented.

### Alloy model is scope-limited but useful (report 07)

Bounded integer arithmetic (5-bit `[-16, 15]`, 5 atoms per sig) is
sufficient for the geometric axes (G-1..G-5, C-1/C-3/C-4, M-4, M-7).
Typography, accessibility, determinism are out of scope for Alloy —
prose + Hypothesis + corpus cover those. All three geometric
tie-breakers **proven consistent** (no counterexample found).

### Conformance suite needs MW-2 to fully close C-axis (report 01)

C-6 and C-7 are `@pytest.mark.skip` pending MW-2 typed registry. This
is acceptable — C-1..C-5 cover the critical bug-class today, and
MW-2 is on the committed roadmap.

## Open questions for the human

1. **Palette decision:** keep A-4 as written and fix `info`/`muted`, or
   reclassify A-4 to the semantic triad only (good/warn/error) and
   accept `info`/`muted` as decorative? Round 3 does not decide this.
2. **Alloy tooling:** commit the `.als` file as documentation only, or
   wire `alloy check` into CI nightly? Nightly gives no practical value
   until MW-3; committing as doc is the safe default.
3. **PrimitiveProtocol adoption:** advisory from day 1 → blocking when?
   Round 3 recommends "when all 5 offending primitives are clean"
   (post-Plane2D + Queue + NumberLine + Graph fixes).
4. **CHANGELOG template:** report 04 surfaced this as a gap but did not
   produce a template. Defer to a small follow-up PR or do it now?

## Round comparison

| Round | Focus | Output |
|-------|-------|--------|
| **Round 1** (`smart-label-ruleset-audit-2026-04-21/`) | Operational gaps — bugs, test coverage, WCAG fails | P0 patches A1..A5 (not yet landed) |
| **Round 2** (`smart-label-ruleset-strengthening-2026-04-21/`) | Specification gaps — ambiguity, missing conformance surface | v2.0.0-draft of ruleset (landed) |
| **Round 3** (this folder) | Enforcement gaps — prose → tests, gates, formal model | Foundation for conformance suite, lint, corpus, Alloy (not yet landed) |

Round 4 would be **implementation** — actually committing the pytest
suite, the lint script, the corpus fixtures, and the MW-3 helper. Not
launched yet.

## Acknowledgements

| Agent | Report | Lines | Duration |
|-------|--------|------:|---------:|
| R3-1 | 01-conformance-suite.md | 1419 | ~7 min |
| R3-2 | 02-golden-corpus.md | 1267 | ~6 min |
| R3-3 | 03-lint-and-protocol-enforcement.md | 1658 | ~9 min |
| R3-4 | 04-open-issue-resolution.md | 1008 | ~6 min |
| R3-5 | 05-determinism-property-tests.md | 760 | ~5 min |
| R3-6 | 06-a11y-automation.md | 1216 | ~7 min |
| R3-7 | 07-alloy-model.md + .als | 1243 | ~7 min |

All agents ran in parallel on opus. No agent failed.
