# Agent 17: Fuzz / Property / Regression Suite Adequacy

**Score:** 6/10
**Verdict:** needs-work

## Prior fixes verified
- deep-eval Phase 4 (sandbox escape test suite): PRESENT — 30 sandbox+escape tests in `test_security.py`
- regression policy: PARTIAL — Error codes tested but no systematic "fix → test lock-in"

## Critical Findings

1. **NO property-based testing:** Zero instances of `hypothesis` library, `@given` decorators, or Quickcheck-style generators in 1,109 test functions. For a grammar-heavy DSL with TeX parsing, LaTeX macro handling, and nested environment support, this is a major gap. Property-based testing would catch off-by-one errors in selector validation, dimension overflow, and macro expansion edge cases.

2. **NO fuzz testing:** No atheris, libFuzzer, or random mutation-based test harness. Critical for a LaTeX → HTML parser. The system accepts arbitrary user LaTeX input; fuzz tests should validate parser recovery, malformed environments, and unterminated math expressions.

3. **30 snapshot tests are EMPTY:** All 30 HTML snapshots in `tests/tex/snapshots/` are 0 bytes. The conftest enforces this explicitly — empty snapshots (except `empty_input.html`) raise `AssertionError` with message "snapshot empty: {name}; populate after manual review". This blocks regression detection: changes to HTML output structure will not be caught until snapshots are populated.

4. **Snapshot policy exists but is enforcement-only:** The conftest checks that snapshots are non-empty (blocking empty ones), but there is NO policy preventing unreviewed churn. Changes to an HTML snapshot require manual review per docs, but the test suite does not enforce that reviews happened — only that the file is not empty.

5. **HARD-TO-DISPLAY coverage is 9/10 constructs (not coverage metric):** `test_htd_coverage.py` verifies that 9 of 10 cookbook problems have `.tex` source and `_expected.html` golden files. The "9/10" means 9 problems are covered; problem #3 (4D Knapsack) is intentionally omitted. This is **file presence testing**, not behavioral coverage of parser/renderer logic.

## High Findings

1. **Regression tests exist but lack systematic lock-in discipline:** 34 tests reference error codes (E1xxx), and `test_security.py` is explicitly a "regression test suite" for sandbox/limits. However, there is NO test per past bug report. Prior phases mention bugs (e.g., Grid zero-size acceptance, \annotate target validation, state validation missing) but no dedicated regression tests lock these fixes in. A bug filed is not automatically covered by a test.

2. **NO mutation testing / coverage measurement tools:** pyproject.toml has NO pytest-cov, mutmut, coverage, or branch coverage config. 1,109 test functions provide breadth but **no quantitative coverage metric exists**. A single untested code path could ship undetected.

3. **KaTeX worker integration tests are limited:** `test_workers.py` has 9 subprocess tests covering crash-respawn, timeout, and idle spawn — but NO exhaustion tests (pool saturation), NO stress-test with slow worker responses, NO tests for malformed JSON from worker stdout.

4. **Cross-platform CI is absent:** No `.github/workflows/` directory. Docs mention macOS `RLIMIT_AS` silently fails, Windows has no `SIGALRM` signal handler, but NO test matrix validates behavior on Linux/macOS/Windows. Security limits are platform-specific and untested.

## Medium Findings

1. **Snapshot update mechanism unclear:** The conftest requires manual file writes; pytest has no `--snapshot-update` mode. Docs mention "authors...run pytest --snapshot-update" but the code doesn't support it. The policy is "populate after manual review against docs/scriba/02-tex-plugin.md §3" — enforcement is manual.

2. **26 test files (53 test modules, 1,109 functions) lack categorization:** No `@pytest.mark.integration`, `@pytest.mark.unit`, `@pytest.mark.regression`, `@pytest.mark.fuzz` taxonomy. The test suite has test_unit, test_integration, test_core directories but no pytest markers for filtering/reporting.

3. **Sandbox escape test suite is comprehensive for AST/limits but incomplete for JS injection:** TestSandboxAST covers 9 AST patterns (dunder chains, imports, while loops, eval). TestEscapeJS covers 4 script-tag injection vectors. But NO tests for:
   - SVG namespace attribute injection (animationWorker SVG output)
   - Unicode homograph attacks in display text
   - Recursive primitive nesting DoS (e.g., 1000-level Tree inside Tree)

## Low Findings

1. **Very long input test (10k chars) is present but not randomized:** `test_very_long_input_10k_chars` uses a hardcoded 225 paragraphs but does not vary paragraph counts, math density, or character distribution. A property-based approach would parameterize this.

2. **Windows platform support is documented as "theoretical":** Docs (M5-M6-M7-plans.md) state "Windows usage is theoretical" and step counter is the only protection there. No Windows CI exists; shipping without Windows testing is acceptable _only_ if docs clearly state "Unix/Linux/macOS only."

## Notes

- **Test volume is strong:** 53 test files, 1,109 test functions, 30 snapshot tests, 30 sandbox/resource tests demonstrate test discipline. No obvious test desert.
- **Architecture is clean:** Fixtures (worker_pool, pipeline, renderers) are session-scoped; isolation is good. No state leakage between tests.
- **Snapshot infrastructure is ready but unactivated:** conftest.py, snapshots/ directory, and 30 test functions are all in place; only the HTML golden files are empty.
- **Phase 4 TODO "Sandbox escape test suite" was completed:** test_security.py directly addresses this Phase 4 finding.
- **Grammar fuzzing is the #1 gap:** TeX is an infamously hard language to parse (nested groups, fragile commands, category codes). Hypothesis or AFL.rs fuzzing would be high-ROI.

**Recommendation:** Before shipping production:
1. Activate 30 snapshots with real golden files (manually review first occurrence per conftest policy)
2. Add hypothesis property tests for parser: math expressions, environments, nesting depth
3. Set up GitHub Actions CI with Linux/macOS matrix + coverage reporting (coverage.py minimum 75%)
4. Lock past bugs with regression tests (e.g., Grid zero-size, \annotate validation)
