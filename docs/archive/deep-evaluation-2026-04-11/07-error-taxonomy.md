# Agent 7: Error Taxonomy Deep Audit

**Score: 6.8/10**

## Critical Findings

### C1: Bare ValueError in hashmap.py (lines 76-83)

Two `ValueError` raises without error codes. Should be `animation_error("E1103", ...)`.

### C2: E1103 is a Mega-Bucket Code

Single code covers 30+ distinct primitive validation failures across Array, Grid, Tree, Matrix, DPTable, NumberLine. No way for callers to distinguish.

### C3: Starlark RuntimeError with Embedded Code

`starlark_worker.py` raises `RuntimeError("E1153: step count exceeded")` instead of proper exception class.

## High Findings

### H1: 8 Range Boundary Codes Are Dead Weight

E1099, E1149, E1179, E1199, E1369, E1469, E1489 — never raised, only documentation markers.

### H2: No AnimationError Base Class

All animation errors use generic `ValidationError`. Can't do `except AnimationError:`.

### H3: Inconsistent Exception Construction

Mix of `animation_error()` factory, `ValidationError(..., code=)`, and dedicated classes.

## Message Quality Assessment (15 samples)

| Quality | Count | Example |
|---------|-------|---------|
| GOOD | 7 | E1004: "unknown option key {key!r}; valid: {list}" |
| FAIR | 4 | E1005: "invalid option value" (no detail) |
| POOR | 4 | E1001: "Unclosed \begin{animation}" (no location hint) |

**Average Quality: 6.1/10**

## Recovery Guidance

- ✓ What failed: 90%
- ✓ Location context: 85%
- ✗ Why it failed: 40%
- ✗ How to fix: 25%

## ISO/IEC 25010 Compliance

| Attribute | Score |
|-----------|-------|
| Maturity | 7/10 |
| Fault tolerance | 5/10 |
| Recoverability | 5/10 |
| **Overall Reliability** | **5.6/10** |

## Priority Fixes

1. Replace bare ValueError with error codes (30 min)
2. Create AnimationError base class (1 hour)
3. Remove/clarify 8 dead boundary codes (30 min)
4. Split E1103 into primitive-specific codes (2-3 hours)
5. Fix Starlark RuntimeError (30 min)
