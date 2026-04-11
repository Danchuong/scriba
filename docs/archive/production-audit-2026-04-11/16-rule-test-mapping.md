# Agent 16: Rule-to-Test Mapping

**Score:** 6/10 (spot coverage of core commands/primitives, significant gap on error conditions)
**Verdict:** ship-with-caveats

## Prior fixes verified
- #3 C1 Grid validation (E1103): PRESENT in test_primitive_grid.py + test_security.py
- #3 C2 `\annotate` target tests: PRESENT (30+ assertions, E1112, E1113 tested, parameter validation)
- #3 C3 Selector validation warnings: PARTIAL (error codes tested, but E1150-E1153, E1158-E1159 untested)
- #10 M1 Five untested primitives: FIXED (all 15 primitives now have unit test files with 200+ test cases total)

## Critical Findings

1. **109 error codes, 51 tested (47%), 60 unpinned (53% regression risk)**
   - Untested categories: 13 lex/parse rules (E1002, E1006-E1013); 20 selector/command validation errors (E1149, E1155-E1159, E1320-E1329, E1420-E1429); 11 primitive limits (E1466, E1482, E1483, E1500, E1503, E1509); 8 frame lifecycle (E1179-E1182, E1199-E1202); 8 Starlark resource limits (E1100-E1111)

2. **\cursor command completely untested** — Zero tests in entire suite. Selector validation (E1150-E1153) logic undefined by tests. `\cursor` uses frame-local state transitions; absent testing means regression silently ships.

3. **E1180 (frame count warning, >30 frames) and E1181 (error, >100 frames) untested** — No integration test verifies frame limit enforcement. CHANGELOG claims 9/10 HARD-TO-DISPLAY coverage; HTD test suite confirms 9/10 via golden HTML files, but frame count itself never hit.

## High Findings

4. **\reannotate never tested with valid params** — Parser accepts the command (E1109, E1112, E1113 cover invalid params). No test verifies `color=` + `arrow_from=` actually recolor annotations. Mutation semantics unverified.

5. **59% of lex/parse/format errors untested** — E1002 (env not on own line), E1006-E1013 (brace argument parse), E1049 (foreach nesting), E1057-E1058 (foreach body/scope), E1099 (option parsing) all absent from test suite. Parser may regress silently.

6. **4/14 commands under-tested:**
   - `\cursor`: 0 tests
   - `\reannotate`: 0 validation tests (only param syntax)
   - `\apply`: 2 tests (shape-specific, missing primitive-agnostic validation)
   - `\compute`: 2 tests (Starlark eval, not Scriba AST integration)

## Medium Findings

7. **Starlark resource limits (E1150, E1151, E1152, E1153, E1158) sparsely tested** — 5 error codes with only 3 integration assertions. Recursion limit (E1158), timeout (E1152), operation budget (E1153) all touched by security.py but not systematically.

8. **Selector validation per-primitive untested for many shapes** — Graph/Tree/Plane2D have validate_selector tests; CodePanel, HashMap, LinkedList, Queue, VariableWatch do not. E.g., CodePanel `.line[999]` never validated.

9. **157 error assertions, but no mutation testing** — Tests assert *that* exception is raised, not *which code path* raises it. Multiple error codes may map to same exception; tests pass even if wrong code is triggered.

10. **HTD coverage 9/10 is golden-HTML-based, not rule-based** — test_htd_coverage.py verifies .tex source + _expected.html exist for 9 problems. Problem #3 (4D Knapsack) intentionally absent. But coverage does not verify each primitive's rules within those files.

## Low Findings

11. **Cursor command E1320 untested** — Cursor target list syntax (E1320: invalid target prefix format) has no assertion. Parser may accept malformed `{...}` arguments.

12. **Matrix/Heatmap `vmin`/`vmax` edge cases untested** — colorscale normalization logic in test_primitive_matrix.py (36 tests) but no tests for vmin > vmax, or vmin == vmax edge.

## Notes

**Rules counted:** 1035 lines in ruleset.md; 109 unique error codes extracted from spec.

**Pinned rules (≥1 test):** 51 error codes have ≥1 assertion.

**Unpinned rules (zero tests):** 60 error codes (55%); includes all 4 untested commands above.

**Test suite stats:**
- 1,109 test functions across 53 files
- 1,521 total tests/assertions (including pytest parametrized runs)
- 1,957 total error code mentions in test assertions

**Command coverage:** 14 commands; 10 have tests (71%), 4 have zero or <3 tests (cursor, reannotate validation, apply, compute).

**Primitive coverage:** 15/15 have unit test files; 200+ edge case tests exist.

**Least-tested command:** `\cursor` (0 tests, controls frame-to-frame state machine).

All 15 named primitives have dedicated test files with comprehensive selector validation, but cursor command — which selects those primitives — is completely unverified. Recommend adding 8-10 cursor integration tests before v0.5.0 GA, focusing on E1320-E1325 (target list validation) and frame-state transitions.
