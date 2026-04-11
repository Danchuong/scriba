# Deep Evaluation Summary — 2026-04-11

10-agent parallel deep evaluation of the Scriba animation system ruleset, code, and documentation quality.

## Scores

| # | Agent | Score | Standard Applied |
|---|-------|-------|-----------------|
| 1 | Code↔Docs Sync | **7/10** | API design consistency |
| 2 | Error Catalog Integrity | **9.5/10** | Catalog completeness |
| 3 | Validation Coverage | **5/10** | Runtime safety |
| 4 | Cross-refs & Links | **6.5/10** | Documentation integrity |
| 5 | Grammar Formalism | **7/10** | BNF/EBNF completeness |
| 6 | Primitive Contract | **7.8/10** | API contract compliance |
| 7 | Error Taxonomy (deep) | **6.8/10** | ISO/IEC 25010 reliability |
| 8 | Security Boundary | **8.5/10** | OWASP, sandbox analysis |
| 9 | Documentation Architecture | **8.2/10** | Divio framework |
| 10 | Runtime Fidelity | **8.5/10** | Behavioral spec testing |
| | **Weighted Average** | **7.5/10** | |

---

## Finding Counts by Severity

| Severity | Count | Source Agents |
|----------|-------|---------------|
| CRITICAL | 10 | #1(1), #3(3), #5(1), #6(4), #7(1) |
| HIGH | 11 | #1(2), #3(3), #4(1), #5(1), #7(3), #10(1) |
| MEDIUM | 16 | #1(3), #2(2), #3(2), #4(1), #5(1), #6(3), #8(2), #10(2) |
| LOW | 6 | #1(2), #8(2), #10(2) |
| **Total** | **43** | |

---

## Top 10 Critical/High Findings

### CRITICAL

1. **Stack parameter docs wrong** — ruleset.md says `capacity`/`n`, code accepts `orientation`/`max_visible`/`items` (#1-C1)
2. **Grid zero-size not validated** — `rows=0, cols=0` accepted silently (#3-C1)
3. **\annotate target not validated** — annotations to non-existent selectors silently succeed (#3-C2)
4. **Selector validation warnings untested** — `_validate_expanded_selectors()` emits warnings but no tests (#3-C3)
5. **Diagram mode unimplemented** — spec documents `\begin{diagram}` but parser doesn't support it (#5-C1)
6. **bounding_box() return type inconsistent** — 9/16 primitives return tuple instead of BoundingBox (#6-C1)
7. **No state validation in set_state()** — any string accepted, no VALID_STATES check (#6-C3)
8. **No selector validation in set_state()/set_value()** — out-of-range indices silently create ghost entries (#6-C4)
9. **15/16 primitives missing ClassVar on SELECTOR_PATTERNS** (#6-C2)
10. **Bare ValueError in hashmap.py** — should use animation_error("E1103") (#7-C1)

### HIGH

1. **6 broken links to removed fastforward.md** (#4-C1, treated as HIGH since in planning/ not spec/)
2. **README CSS class wrong** — `scriba-filmstrip` should be `scriba-frames` (#4-C2)
3. **Step label options documented but not implemented** — `\step[label=...]` rejected by parser (#5-H1)
4. **5 extended primitives lack unit tests** — CodePanel, HashMap, LinkedList, Queue, VariableWatch (#10-M1)
5. **E1103 mega-bucket** — single code covers 30+ different validation failures (#7-C2)

---

## Strengths

- **Security: 8.5/10** — Multi-layer sandbox (AST + builtins + attributes), consistent HTML/SVG escaping, resource limits
- **Error Catalog: 9.5/10** — 62 codes, 100% coverage, zero orphans
- **Runtime Fidelity: 8.5/10** — All 14 commands verified, 8 CSS states perfectly aligned
- **Pipeline architecture** — Clean separation: parser → scene → emitter → renderer
- **40+ example files** covering basic to advanced patterns

## Weaknesses

- **Validation: 5/10** — Validation exists but untested; critical paths missing (Grid, \annotate)
- **Documentation: 8.2/10** — Strong reference & tutorial, but missing task-oriented how-to guides
- **Primitive contracts: 7.8/10** — Type inconsistencies, no runtime state/selector validation
- **Error UX: 6.8/10** — Messages lack "how to fix" guidance; E1103 overloaded

---

## Recommended Fix Order

### Phase 1 — Critical Validation (est. 4 hours)
- Grid min size validation
- \annotate target validation
- set_state() / set_value() selector validation
- bounding_box() return type standardization
- Bare ValueError → animation_error in hashmap.py

### Phase 2 — Docs & Spec (est. 3 hours)
- Fix Stack params in ruleset.md
- Fix README CSS class
- Remove fastforward broken links (6 instances)
- Fix TEX-RENDERER-BACKEND-ONLY.md reference
- Clarify Matrix/Heatmap alias

### Phase 3 — Grammar & Error (est. 4 hours)
- Decide: implement diagram mode or remove from spec
- Decide: implement \step[label=...] or remove from spec
- Split E1103 or create primitive-specific codes
- Create AnimationError base class
- Add ClassVar annotations (15 primitives)

### Phase 4 — Tests & Docs Quality (est. 6 hours)
- Unit tests for 5 untested primitives
- Tests for _validate_expanded_selectors warnings
- Tests for empty collection warnings
- Documentation TOC/index
- Sandbox escape test suite

---

## Reports

| File | Agent |
|------|-------|
| [01-code-docs-sync.md](01-code-docs-sync.md) | Code↔Docs consistency |
| [02-error-catalog.md](02-error-catalog.md) | Error catalog integrity |
| [03-validation-coverage.md](03-validation-coverage.md) | Validation coverage |
| [04-crossrefs-links.md](04-crossrefs-links.md) | Cross-references & links |
| [05-grammar-formalism.md](05-grammar-formalism.md) | Grammar formalism |
| [06-primitive-contract.md](06-primitive-contract.md) | Primitive API contracts |
| [07-error-taxonomy.md](07-error-taxonomy.md) | Error taxonomy (deep) |
| [08-security-boundary.md](08-security-boundary.md) | Security boundary |
| [09-docs-architecture.md](09-docs-architecture.md) | Documentation architecture |
| [10-runtime-fidelity.md](10-runtime-fidelity.md) | Runtime fidelity |
