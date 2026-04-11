# Agent 05: Error Code Catalog

**Score:** 5.5/10
**Verdict:** needs-work

## Prior fixes verified
- C1 (hashmap ValueError): **FIXED** ✓ — now wrapped in animation_error(E1103)
- C2 (E1103 split): **MISSING** ✗ — still single mega-bucket covering 30+ parameter failures
- M8 (lexer codes): **ABSENT** ✓ — lexer raises ValidationError; grammar.py handles parse errors
- L3 (E1363/E1364/E1367): **MISSING** ✗ — codes not in ERROR_CATALOG at all
- L4 (matrix 10k limit): **MISSING** ✗ — no E-code assigned to matrix size constraints

## Critical Findings

**1. 26 orphan error codes (42% of catalog unused)**
- **E1003** (nested animation), **E1100** (general parse), **E1150-E1155** (all Starlark codes), **E1366** (zero-step substory), **E1461-E1463** (plane2d geometry), **E1481** (metricplot series limit)
- These are documented with descriptions but never raised anywhere in scriba/
- Suggests incomplete implementation or dead-code documentation

**2. Two bare ValueError exceptions in starlark_worker.py (lines 170, 175)**
- Range validation failures raise Python ValueError, not animation_error()
- Should map to E1173 (foreach validation) or new code E1155 (if memory/execution limit)
- Violates error code contract: all errors must have E-codes

**3. Positional data lost during error creation**
- animation_error() function accepts only (code, detail) parameters
- line/col/hint fields supported by parent ValidationError class but never populated
- All errors report "[E####]: message" with no source location
- Makes debugging animation source hard for users

**4. Incomplete diagram-mode implementation**
- E1050-E1056 (10 diagram-specific codes) documented but diagram mode not production-ready
- Raises NestedAnimationError/UnclosedAnimationError only; other E-codes untested
- Marked "reserved for future" in ruleset.md but catalog treats as current

## High Findings

**1. E1103 remains a catch-all (30+ parameter failure scenarios)**
- HashMap (capacity), Matrix (rows/cols/init), Tree (root/data), Array (size), NumberLine (min/max), etc. all map to E1103
- Recovery hint in catalog says "check parameter documentation" — too vague
- No sub-codes for HashMap vs Matrix vs Tree parameter failures
- Commit claimed "E1103 description improved" but no structural split

**2. Five animation_error() calls lack explicit detail messages**
- plane2d.py:94, 96, 103 pass only code without detail (relies on f-string in second param)
- metricplot.py:109 similar issue
- Makes error messages inconsistent (some human-readable, some terse)

**3. Selector parse errors (E1009-E1012) never actually raised**
- selectors.py uses `self._error(..., code="E101X")` in 4 places
- But selectors.py inherits from some error class; no animation_error() call found
- Either orphan codes or wrong error class used

## Medium Findings

**1. No version/stability tracking for error catalog**
- ERROR_CATALOG is plain dict with no version field
- No renumbering policy documented
- constants.py exists (commit mentions "error numbering scheme documented") but contains only limits, not scheme

**2. Starlark sandbox leaks Python exceptions**
- starlark_worker._safe_range() raises ValueError for max argument size
- These escape to user as bare "ValueError: range() argument too large"
- Should map to E1173 (foreach iterable validation) or E1155 (memory limit)
- Similar risk in StarlarkEvalError catch block (E1151) — may not catch all Starlark failures

**3. Matrix cell limit not documented with error code**
- Matrix primitives enforce 250k cell limit (from deep-eval commit)
- No E-code assigned; error message only appears in detail string
- Should be E1103 but not searchable/catalogable separately

## Low Findings

**1. Error class count mismatch**
- 7 exception classes defined (AnimationError, UnclosedAnimationError, NestedAnimationError, AnimationParseError, FrameCountWarning, FrameCountError, StarlarkEvalError)
- Only 3 are actually raised in practice (UnclosedAnimationError, NestedAnimationError, FrameCountError, StarlarkEvalError)
- AnimationParseError and FrameCountWarning appear to be dead code or only for warnings

**2. E1482 in catalog but E1481 raised instead**
- ERROR_CATALOG has both E1481 and E1482
- metricplot.py:111 raises E1481 (too many series)
- E1482 not referenced anywhere — possible off-by-one or overallocation

**3. Doc-code sync incomplete**
- error-codes.md references 62 codes ✓
- errors.py has 62 codes ✓
- But 26 codes never raised = docs claim full coverage that doesn't exist
- Commit da100de claimed "Unified error reference page (error-codes.md)" but inventory is stale

## Notes

- Commit da100de (43 deep-eval findings) claims error system resolved, but 5+ critical findings remain
- Orphan codes suggest incomplete refactoring: either features never implemented or error mapping missed during consolidation
- animation_error() factory function is undersized — should accept line/col/hint for full error contract
- Test coverage likely missing for 26 orphan codes (E1150-E1155, E1003, E1100, etc.)
- Starlark sandbox is the largest risk: 2 bare ValueError exceptions + StarlarkEvalError may not catch all failures
