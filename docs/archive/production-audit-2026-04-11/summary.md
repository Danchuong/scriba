# Production Readiness Audit — 2026-04-11

21-agent parallel production-grade audit of Scriba v0.5.0, conducted after two prior audits (2026-04-10 review, 2026-04-11 ruleset audit) and the 10-agent deep evaluation (2026-04-11) claimed all 84 findings resolved via commits `da100de` and `2e8a0e2`.

**Goal:** Independent verification that Scriba meets production-grade standards across every dimension of its ruleset, not just the ones already audited. Each agent was briefed NOT to trust commit messages, to verify prior fixes landed, and to find NEW defects in its slice that peer agents would not catch.

---

## Scores

| # | Agent | Score | Verdict |
|---|-------|-------|---------|
| 01 | Grammar Formalism & Ambiguity | **8.0** | ship-with-caveats |
| 02 | Spec Internal Consistency | **6.0** | ship-with-caveats |
| 03 | Spec Clarity & Example Coverage | **6.0** | needs-work |
| 04 | Registry Drift | **6.0** | needs-work |
| 05 | Error Code Catalog | **5.5** | needs-work |
| 06 | Limits & CSS/HTML Contract | **8.0** | ship-with-caveats |
| 07 | Parser/Lexer Fuzz Edge Cases | **4.0** | needs-work |
| 08 | Starlark Sandbox & Determinism | **6.0** | needs-work |
| 09 | Error UX Depth | **6.2** | ship-with-caveats |
| 10 | Performance, Memory, DoS Safety | **7.0** | ship-with-caveats |
| 11 | XSS, HTML Injection, URL Safety | **9.0** | **production-ready** |
| 12 | Path Traversal & Supply Chain | **9.0** | **production-ready** |
| 13 | Sandbox Red-Team (Adversarial) | **6.5** | needs-work |
| 14 | Public API Surface + Semver | **7.0** | ship-with-caveats |
| 15 | Long-Term Contract Stability | **6.0** | needs-work |
| 16 | Rule-to-Test Mapping | **6.0** | ship-with-caveats |
| 17 | Fuzz / Property / Regression | **6.0** | needs-work |
| 18 | Docs Ecosystem Accuracy | **7.0** | ship-with-caveats |
| 19 | DSL Ergonomics Simulation | **6.0** | ship-with-caveats |
| 20 | Cross-Cutting Red-Team | **6.0** | ship-with-caveats |
| 21 | Ops, Release, Platform Matrix | **6.0** | ship-with-caveats |
| | **Weighted Average** | **6.5** | ship-with-caveats |

Verdict distribution: **2 production-ready**, **11 ship-with-caveats**, **8 needs-work**, **0 blocked**.

---

## Finding Counts by Severity

| Severity | Count | Notes |
|----------|-------|-------|
| CRITICAL | ~40 | Includes 3 sandbox red-team escape vectors, 2 spec-code DoS-limit mismatches, HTML allowlist gap, parser silent-accept bugs |
| HIGH | ~55 | Registry drift, error code orphans, contract stability gaps, ergonomic blockers |
| MEDIUM | ~75 | |
| LOW | ~45 | |
| **Total** | **~215** | |

Approximately 5× the prior audit's finding count — agents dug into angles the previous 13 auditors did not touch (red-team, ergonomics, contract stability, ops matrix, property testing, cross-cutting integration defects).

---

## Top 15 Critical Findings (Blocker-Class)

### Spec ↔ Code Drift & DoS Surface
1. **Matrix/DPTable cell limit spec says 10k, code enforces 250k** (Agent 06 H2, Agent 10 C1) — 25× discrepancy, no error code E1425 registered in code
2. **Starlark memory limit: spec says 64 MB, code allows 128-256 MB** (Agent 08 C1) — undermines DoS guarantee
3. **Duplicate §5.3 in ruleset.md** (Agent 02 C1) — all subsequent subsection numbers off by one

### Sandbox Escape Vectors
4. **`.format()` string-based attribute access bypasses AST scanner** (Agent 13 C1) — `"{0.append.__self__.__class__.__mro__}".format([])` leaks class hierarchy
5. **F-string partial dunder bypass** (Agent 13 C2) — `f"{[].append.__self__.__class__}"` returns class object
6. **`hash()` builtin NOT forbidden** (Agent 08 C2) — breaks byte-identical determinism guarantee per PYTHONHASHSEED
7. **Generator introspection (`gi_frame`, `gi_code`) accessible** (Agent 13 C3) — not in BLOCKED_ATTRIBUTES

### Parser Silent-Accept Bugs
8. **Unclosed brace at EOF accepted silently** (Agent 07 C1) — `\shape{a}{Array}{size=5` parses successfully, data loss
9. **Empty parameter braces accepted without validation** (Agent 07 C2) — `\shape{a}{Array}{}` → empty shape
10. **Diagram mode unimplemented** (Agent 01 C1) — spec promises `\begin{diagram}`, parser always returns AnimationIR

### Error Catalog & UX
11. **26 orphan error codes (42% of catalog)** (Agent 05 C1) — codes documented but never raised anywhere
12. **E1103 remains a mega-bucket** (Agent 05 H1, Agent 09 C2) — 30+ distinct failures map to one code; not split as claimed
13. **Selector validation silent downgrade** (Agent 09 C3) — invalid selectors warn only; parser says OK, emitter silently ignores

### Integration & Contract
14. **Pipeline placeholder substitution re-entry bug** (Agent 20 C2) — naive `.replace()` on `\x00SCRIBA_BLOCK_N\x00`; adversarial artifact HTML can inject placeholders
15. **HTML attribute allowlist gap** (Agent 06 C1) — emitter emits `data-scriba-scene`, `data-frame-count`, `data-layout`, `aria-label` on `<figure>`; sanitizer strips them silently

---

## Top High Findings

1. **Step label options documented but parser rejects** (Agent 01 H1) — `\step[label=...]` in spec line 546; parser raises E1052
2. **Unknown commands silently disappear** (Agent 01 H2) — lexer emits unknown `\foo` as CHAR, parser treats as garbage
3. **ScribaRuntimeError not in public API** (Agent 14 C1) — error class exists but not exported
4. **Architecture.md missing block_data, required_assets** (Agent 14 C2) — Document shape drifted since 0.1.1, spec unchanged
5. **No stability policy document** (Agent 15 C1) — no STABILITY.md, no v1.0 commitment, contracts frozen only in CHANGELOG
6. **`\cursor` command completely untested** (Agent 16 C2) — 0 tests for frame-state transition command
7. **109 error codes, only 51 (47%) have tests** (Agent 16 C1) — 53% regression risk
8. **No property-based testing** (Agent 17 C1) — zero hypothesis usage for grammar-heavy DSL
9. **No fuzz testing harness** (Agent 17 C2) — TeX parser accepts untrusted input
10. **30 snapshot tests are 0 bytes** (Agent 17 C3) — blocks regression detection
11. **CI infrastructure absent** (Agent 21 C2) — no GitHub Actions, no Python/Node matrix, no coverage
12. **SECURITY.md version outdated** (Agent 21 C1) — claims 0.1.x only, package is 0.5.0
13. **Loop-to-step bridge missing** (Agent 19 H4) — `\step` forbidden inside `\foreach`; blocks algorithms with per-iteration frames (monotonic stack, amortized analysis)
14. **M6 diff/delta semantics never landed** (Agent 19) — every frame re-specifies full state; O(N²) boilerplate for DP
15. **Deprecated SubprocessWorker alias has no deprecation warning** (Agent 14 H2) — marked "remove in 0.2.0"; now at 0.5.0 silently

---

## Strengths

- **XSS / HTML injection: 9/10** (Agent 11) — `is_safe_url` hardening against URL smuggling (unicode separators, control chars, percent-encoded bypass) is airtight. innerHTML usage in interactive widget is properly defended with `_escape_js()`.
- **Path traversal & supply chain: 9/10** (Agent 12) — No shell injection, KaTeX vendored & SHA-256 verified, Pygments CSS pre-generated, `importlib.resources` not mixed with user input, list-based argv everywhere.
- **Grammar is deterministic LL(1)** (Agent 01) — single-token lookahead sufficient, no reduce-reduce conflicts, selector BNF unambiguous.
- **All 16 primitives registered** (Agent 04) — Phase D successfully resolved H2/H3 from prior audit; registry drift limited to Stack spec and CodePanel 1-based indexing.
- **Performance limits enforced with E-codes** (Agent 10) — frame limit 100 (E1181), foreach 10k items + depth 3, Graph 20 nodes, MetricPlot 8 series, KaTeX 1 MB source, SIGKILL cascade for hanging workers.
- **Primitive test coverage: 15/15 have unit test files** (Agent 16) — Phase D fixed the 5-primitive test gap.
- **Deep-copy per frame isolation** (Agent 08) — M1 mutable global leak correctly fixed via `copy.deepcopy()` in scene.py.
- **Error recovery mode works** (Agent 09) — `error_recovery=True` collects errors into combined `ValidationError`.

---

## Weaknesses

- **Parser edge cases (4/10)** — unclosed braces silently accepted, empty params pass, 5-level foreach nesting unbounded
- **Error code catalog (5.5/10)** — 42% orphan codes, E1103 still a mega-bucket, 2 bare `ValueError` in starlark_worker
- **Sandbox adversarial depth (6.5/10)** — .format() bypass, f-string partial bypass, generator introspection holes, hash() breaks determinism
- **Contract stability (6/10)** — no STABILITY.md, CSS class names and SVG ID format not locked, ALLOWED_TAGS not pinned to exact membership
- **Rule-to-test mapping (6/10)** — 53% of rules have zero tests, `\cursor` command entirely untested
- **Fuzz/regression (6/10)** — no property testing, no fuzz harness, 30 empty snapshots, no mutation testing, no coverage metric
- **Ops (6/10)** — no CI, no platform matrix, KaTeX 11 commits behind latest, homebrew formula is a stub, no PyPI release workflow
- **DSL ergonomics (6/10)** — loop-to-step bridge missing, no diff/delta, algorithms with per-iteration frames must be hand-unrolled

---

## Recommended Fix Order

### Phase 1 — Blocker Fixes (before any public release)
1. Fix Matrix/DPTable spec-code limit mismatch (C6.H2) — either update spec to 250k or code to 10k; add E1425 enforcement
2. Remove `hash()` from Starlark builtins (C8.C2); align Starlark memory limit to spec or update spec (C8.C1)
3. Fix placeholder substitution re-entry bug in pipeline (C20.C2) — use UUID-based placeholders
4. Fix parser unclosed-brace silent accept (C7.C1, C7.C2)
5. Expand HTML attribute allowlist to cover emitter output (C6.C1) — add `data-scriba-scene`, `data-frame-count`, `data-layout`, `aria-label`, `data-target` on `<g>`
6. Fix duplicate §5.3 in ruleset.md (C2.C1) — renumber cascading subsections

### Phase 2 — Sandbox Red-Team Closure
7. AST scanner: recursively block dunders in attribute chains (C13.C2)
8. Add `gi_frame`, `gi_code`, `gi_yieldfrom`, `gi_running`, `cr_frame`, `cr_code` to BLOCKED_ATTRIBUTES (C13.C3)
9. Decide on `.format()` — disable entirely or implement safe format-spec validator (C13.C1)
10. Add `ast.Match`, `ast.NamedExpr` to FORBIDDEN_NODE_TYPES (C13.H1, C13.H3)
11. Document Windows fallback strategy for SIGALRM (C8.H2)

### Phase 3 — Error Catalog & UX
12. Split E1103 into primitive-specific codes; wire line/col into `animation_error()` factory (C5, C9)
13. Remove 26 orphan error codes OR wire them into raise sites (C5.C1)
14. Wrap bare `ValueError` in `starlark_worker.py` (C5.C2, C9.C1)
15. Add source snippet to `ValidationError.__str__()` (C9.M3)

### Phase 4 — Test Suite & Contract Lock-In
16. Populate 30 empty snapshot tests (C17.C3)
17. Write `\cursor` integration tests (C16.C2)
18. Add pytest-cov; enforce ≥75% line coverage (C17.H2)
19. Add hypothesis property tests for parser/selectors (C17.C1)
20. Create `STABILITY.md` documenting locked contracts (C15.C1)
21. Add snapshot test pinning `ALLOWED_TAGS`, `ALLOWED_ATTRS` exact membership (C15.L1)

### Phase 5 — Ops, Docs, Ergonomics
22. Create `.github/workflows/test.yml` with Python 3.10/3.11/3.12 × Node 18/20/22 matrix (C21.C2)
23. Update `SECURITY.md` for v0.5.0 beta line (C21.C1)
24. Fill homebrew formula SHA256, test build (C21.H1)
25. Fix blog post primitive count, CHANGELOG omissions for 5 data-structure primitives (C18.C3, C18.H1)
26. Fix cookbook 06-frog1-dp indentation error (C18.C4)
27. Document `\step` forbidden inside `\foreach` limitation in spec; add cookbook example for manual unroll pattern (C19.H4)

---

## Overall Verdict

**Weighted score: 6.5/10 — ship-with-caveats for internal use; blockers for public release.**

Scriba v0.5.0 has strong foundations:
- Web security (XSS, URL safety, supply chain) is at **9/10 production-grade**
- Grammar is formally clean (LL(1), unambiguous)
- All 16 primitives are registered, tested, documented
- DoS limits are mostly enforced with proper error codes

But **84 prior findings did not cover ~45 of the critical/high findings in this round**, including:
- **3 new sandbox escape vectors** the prior sandbox audit missed (.format bypass, f-string leak, generator introspection)
- **Spec-code DoS limit mismatches** (25× on Matrix cells, 2-4× on Starlark memory)
- **Parser silent-accept bugs** that cause data loss
- **Pipeline integration defects** (placeholder re-entry, context provider failure paths)
- **Contract stability gaps** (no STABILITY.md, ALLOWED_TAGS not pinned)
- **Test suite gaps** (0 byte snapshots, no property testing, `\cursor` untested)
- **Ops readiness absence** (no CI, no release workflow, outdated SECURITY.md)

**Recommendation:** Treat this audit's Phase 1 and Phase 2 findings as release-blockers. Phase 3-5 can be parallelized as fast-follow. Target a **v0.5.1 patch release** for Phase 1+2, then plan Phase 3-5 over subsequent minor releases before a v1.0 API freeze.

---

## Reports

| File | Slice | Score |
|------|-------|-------|
| [01-grammar-formalism.md](01-grammar-formalism.md) | Grammar Formalism & Ambiguity | 8.0 |
| [02-spec-consistency.md](02-spec-consistency.md) | Spec Internal Consistency | 6.0 |
| [03-spec-clarity.md](03-spec-clarity.md) | Spec Clarity & Example Coverage | 6.0 |
| [04-registry-drift.md](04-registry-drift.md) | Registry Drift | 6.0 |
| [05-error-catalog.md](05-error-catalog.md) | Error Code Catalog | 5.5 |
| [06-limits-css-html.md](06-limits-css-html.md) | Limits & CSS/HTML Contract | 8.0 |
| [07-parser-fuzz.md](07-parser-fuzz.md) | Parser/Lexer Fuzz Edge Cases | 4.0 |
| [08-starlark-sandbox.md](08-starlark-sandbox.md) | Starlark Sandbox & Determinism | 6.0 |
| [09-error-ux.md](09-error-ux.md) | Error UX Depth | 6.2 |
| [10-performance-dos.md](10-performance-dos.md) | Performance, Memory, DoS Safety | 7.0 |
| [11-xss-url.md](11-xss-url.md) | XSS, HTML Injection, URL Safety | 9.0 |
| [12-supply-chain.md](12-supply-chain.md) | Path Traversal & Supply Chain | 9.0 |
| [13-sandbox-redteam.md](13-sandbox-redteam.md) | Sandbox Red-Team (Adversarial) | 6.5 |
| [14-public-api-semver.md](14-public-api-semver.md) | Public API Surface + Semver | 7.0 |
| [15-contract-stability.md](15-contract-stability.md) | Long-Term Contract Stability | 6.0 |
| [16-rule-test-mapping.md](16-rule-test-mapping.md) | Rule-to-Test Mapping | 6.0 |
| [17-fuzz-regression.md](17-fuzz-regression.md) | Fuzz / Property / Regression | 6.0 |
| [18-docs-ecosystem.md](18-docs-ecosystem.md) | Docs Ecosystem Accuracy | 7.0 |
| [19-dsl-ergonomics.md](19-dsl-ergonomics.md) | DSL Ergonomics Simulation | 6.0 |
| [20-cross-cutting-redteam.md](20-cross-cutting-redteam.md) | Cross-Cutting Red-Team | 6.0 |
| [21-ops-release.md](21-ops-release.md) | Ops, Release, Platform Matrix | 6.0 |
