# Smart-Label Ruleset Strengthening — 2026-04-21 (Round 2)

Round 2 deep work: **strengthen the ruleset document itself** before any
further code. Seven opus agents in parallel produced foundation material
to rewrite `docs/spec/smart-label-ruleset.md` as a normative, testable,
versioned v2.

> **Round 1** (`../smart-label-ruleset-audit-2026-04-21/`) found *operational*
> gaps — bugs, test coverage, WCAG fails. **Round 2 closes *specification*
> gaps** — ambiguity, under-specification, missing conformance surface.

## Start here

- **[00-synthesis.md](00-synthesis.md)** — consolidation, v2 outline,
  invariant inventory, conflicts, action list.

## Per-axis reports

| # | File | Lines | Focus |
|---|------|------:|-------|
| 1 | [01-first-principles.md](01-first-principles.md) | 1120 | Derive 42 invariants from domain theory. 7 axes (Geometry, Collision, Typography, Accessibility, Determinism, Error, Author contract). Moves 12 non-invariants out of normative scope. Documents 6 conflicts + tie-breakers. |
| 2 | [02-normative-rewrite.md](02-normative-rewrite.md) | 906 | RFC 2119 rewrite. 14 MUST / 8 SHOULD / 6 MAY rules with error codes, message templates, detection points, recovery. Reserves E1560–E1571 (+ E1579 ceiling). Ambiguous-language audit of v1. |
| 3 | [03-api-contracts.md](03-api-contracts.md) | 1585 | Hoare-triple-style contracts for 14 functions. 6 signature hazards (H-1..H-6), 6 API asymmetries (A-1..A-6). Full MW-3 `_place_pill` helper contract. |
| 4 | [04-edge-cases.md](04-edge-cases.md) | 705 | 16-category taxonomy, ~147 rows. 5 Critical (NaN/crash/corruption) + 12 High empirically confirmed. NaN/inf/null-byte guards for v2. |
| 5 | [05-primitive-contract.md](05-primitive-contract.md) | 1298 | Primitive Participation Contract: 6 required methods, 15-primitive conformance matrix, 6 forbidden patterns with citations, 17.5 h migration plan. |
| 6 | [06-spec-style.md](06-spec-style.md) | 1331 | W3C/TC39/WHATWG/SVG 2 comparison. 9 MUST + 2 SHOULD style conventions. ECMAScript Let/Assert/Return algorithm style. Alloy feasibility verdict. |
| 7 | [07-non-goals-versioning.md](07-non-goals-versioning.md) | 871 | 18 non-goals (NG-1..NG-18). 12-section versioning policy: stability markers, deprecation, compat thresholds. 8 px = major-break boundary. |

**Total**: ~7800 lines foundation material.

## How to use this audit

1. Read `00-synthesis.md` end to end (~20 min).
2. Use the §"Revised v2 ruleset outline" as the table-of-contents for
   rewriting `docs/spec/smart-label-ruleset.md` from scratch.
3. Pull content from the per-axis reports:
   - §1 invariants → report 1
   - §2 algorithm step style → report 6
   - §4 error codes → report 2
   - §5 primitive contract → report 5
   - §2.3 pre-conditions + guards → report 4
   - §8 non-goals + §10 versioning → report 7
4. Write front-matter, RFC 2119 preamble, conformance classes → report 2 §1.
5. Commit v2 + reserve E1560–E1579 in `error-codes.md`.

## Scope

**In scope**: ruleset document quality, conformance surface, versioning,
edge-case coverage, primitive interface formalisation.

**Out of scope** (Round 1 or later rounds): actual code fixes (A1..A5 P0
patches, MW-2/3/4 implementation). Those are separate PRs after v2 lands.

## Status

All 7 agents completed. Synthesis written. Ruleset v2 not yet written —
that is the next step and should land as its own commit.

See `00-synthesis.md` §"Action list" for the concrete P0 checklist.
