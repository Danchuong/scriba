# Agent 3: Validation Coverage Audit

**Score: 5/10**

## Executive Summary

Partial but incomplete validation coverage. Critical gaps in constructor validation (Grid zero-size), selector validation warnings (untested), and annotation target validation (missing entirely).

## Validation Coverage Matrix

| Validation Point | In Code | Has Tests | Status |
|---|---|---|---|
| `_validate_expanded_selectors()` called | ✓ | ✗ | NOT TESTED |
| `prim.validate_selector()` for selectors | ✓ | ✗ | NOT TESTED |
| Warnings for invalid selectors | ✓ | ✗ | **CRITICAL GAP** |
| Array: size >= 1 | ✓ | ✓ | COMPLETE |
| Array: size max 10k | ✓ | ✗ | NOT TESTED |
| Matrix: rows/cols >= 1 | ✓ | ✓ | COMPLETE |
| **Grid: rows/cols >= 1** | **✗ MISSING** | ✗ | **HIGH** |
| Graph: empty nodes warning | ✓ | ✗ | NOT TESTED |
| VariableWatch: empty names warning | ✓ | ✗ | NOT TESTED |
| Stack: constructor validation | ✗ | ✗ | NO VALIDATION |
| Queue: capacity validation | ✗ | ✗ | NO VALIDATION |
| LinkedList: constructor validation | ✗ | ✗ | NO VALIDATION |
| **\annotate target validation** | **✗ MISSING** | ✗ | **CRITICAL** |
| Stack.validate_selector() | ✓ | ✗ | NOT TESTED |
| Queue.validate_selector() | ✓ | ✗ | NOT TESTED |
| LinkedList.validate_selector() | ✓ | ✗ | NOT TESTED |
| VariableWatch.validate_selector() | ✓ | ✗ | NOT TESTED |

## Critical Issues

### C1: Missing Grid Minimum Size Validation
Grid accepts `rows=0, cols=0` without error. Matrix has this check but Grid doesn't.
**Fix:** Add `if rows < 1: raise E1103` in grid.py.

### C2: No Validation for \annotate Target Existence
`_apply_annotate()` in scene.py never validates that the target selector exists on any shape.
**Fix:** Call `prim.validate_selector()` in `_apply_annotate()`.

### C3: _validate_expanded_selectors() Warnings Not Tested
Function emits warnings but zero tests verify this path.

## Recommended Priority Fixes

| Priority | Issue | Effort |
|---|---|---|
| P0 | Grid min size validation | 5 min |
| P0 | \annotate target validation | 30 min |
| P1 | Test _validate_expanded_selectors warnings | 20 min |
| P1 | Test Graph/VariableWatch empty warnings | 15 min |
| P2 | Queue/Stack/LinkedList validation tests | 45 min |
