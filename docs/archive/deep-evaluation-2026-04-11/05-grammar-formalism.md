# Agent 5: Grammar Formalism Audit

**Score: 7/10**

## Executive Summary

Well-written BNF specification with clear notation. Parser implements 12/14 documented productions. Two significant gaps: diagram mode unimplemented, step label options unsupported.

## Critical Findings

### C1: Diagram Mode Unimplemented

Spec documents `\begin{diagram}...\end{diagram}` as a top-level environment. DiagramIR type defined in ast.py. But parser only returns AnimationIR — no diagram parsing code exists.

**Impact:** Users cannot use `\begin{diagram}` environments. Dead code in AST.

### H1: Step Label Options Not Supported

Spec defines `\step[label=...]` syntax. Parser's `_check_step_trailing()` explicitly rejects any non-NEWLINE token after `\step` (raises E1052).

**Impact:** `\step[label=...]` syntax documented but unusable.

## Medium Findings

### M1: .item[i] Accessor Undocumented in BNF

Stack's `.item[i]` is implemented and in per-primitive table but missing from formal accessor BNF (§3 lines 81-92).

## Completeness Matrix

| Category | Total | Documented | Implemented | Coverage |
|----------|-------|-----------|-------------|----------|
| Tokens | 18 | 10 | 18 | 56% |
| Commands | 12 | 12 | 12 | 100% |
| Accessors | 9 | 8 | 9 | 89% |
| Top-level modes | 2 | 2 | 1 | 50% |
| **Overall** | — | — | — | **82%** |

## Recommendations

1. **Implement diagram parsing** or remove DiagramIR/DiagramOptions from AST
2. **Implement step label options** or update spec to remove them
3. Add `.item[i]` to selector BNF
4. Remove unused RAW_BRACE_CONTENT token
