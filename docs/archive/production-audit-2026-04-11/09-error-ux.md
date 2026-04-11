# Agent 09: Error UX Depth

**Score:** 6.2/10
**Verdict:** ship-with-caveats

## Prior fixes verified

- H5 context: PARTIAL — parser errors carry detail, but primitives use bare E1103 without context
- H6 recovery: PRESENT — error_recovery=True collects errors and raises combined ValidationError with all details
- L1 prefix: PARTIALLY FIXED — no redundant `[E1103]` added to message, but `animation_error()` factory doesn't propagate line/col from callsites
- C1 hashmap: MISSING — bare ValueError at starlark_worker.py (range() safety checks) for E1150/E1152/E1155, not wrapped in error codes
- C2 E1103 split: MISSING — E1103 still mega-bucket; 30+ distinct failures (Array size, Grid rows/cols, Matrix bounds, DPTable indexing, Queue capacity, Tree root, etc.) all map to one code with only `detail=` distinguishing them

## Critical Findings

**C1: Starlark ValueError leaks unprofessional error** (starlark_worker.py lines 192-199)
- Two bare `ValueError` raises for range() safety: `"range() argument too large"` and `"range() would produce X elements"`
- These surface in E1150 (parse error) message, confusing users (looks like syntax error, actually a runtime constraint)
- Fix: Wrap in proper exception at boundary

**C2: Error recovery shows raw multi-error dump** (grammar.py lines 348-358)
- When `error_recovery=True` and 2+ errors occur, raises combined ValidationError with `"\n".join(parts)` where parts are `f"  {i}. {err}"`
- String repr of ValidationError includes code prefix `[code]` — creating `"  1. [E1004] unknown key..."`, repetitive and unpolished
- No pagination or "first 3 errors shown" truncation for animations with 50+ errors

**C3: Selector validation silent downgrade** (emitter.py lines ~250)
- Invalid selectors like `a.cell[999]` on 10-cell array emit `warnings.warn()` only, no error raised
- User sees no indication in rendered output; animation silently renders without the recolor/annotation
- Counterintuitive UX: parser says "valid", emitter silently ignores

## High Findings

**H1: E1103 provides no actionable path** (primitives/*.py across 8 files)
- Array: `"Array size {size} exceeds maximum of 10,000"` — what's the valid range? Must read code.
- Grid: `"Grid rows/cols must be >= 1, got {x}"` — hint says "Grid requires both 'rows' and 'cols'" when one is missing. Vague.
- No "valid values: 1-10000" or "did you mean: size=100?" suggestions
- Compare gold standard from grammar.py: `"valid: {', '.join(sorted(VALID_ANNOTATION_COLORS))}"` — E1113 does it right

**H2: Line/col accuracy degraded in primitives** (array.py, grid.py, etc.)
- Primitives raise via `animation_error(E1103, detail="...")` with zero line/col arguments
- Error shows up in ValidationError with all None, users see error but not source location
- Parser-level errors carry `line=tok.line, col=tok.col`; primitives don't

**H3: Starlark traceback leaks implementation details** (starlark_worker.py line 405)
- E1151 (runtime error) returns full traceback filtered by `"<compute>"` substring
- User sees Python frame info like `'  File "<compute>", line 3, in <module>'` mixed with exception message
- Should be: `"line 3: RuntimeError: undefined variable 'x'" OR full TB opt-in via debug flag

**H4: Selector parser position off-by-one** (selectors.py line 271)
- `position=self._pos` records byte position in selector string (e.g., "a.cell[X]")
- But ValidationError expects `col=` (token column in source), not `position=` (substring index)
- Selector errors show "Selector parse error at position 7: ..." instead of annotating the exact source line

## Medium Findings

**M1: E1010 message lacks clarity** (selectors.py lines 222, 248, 260)
- `"expected number, got {found}"` — what is `found`? Shows raw character/repr
- Better: `"expected numeric index, got {found!r} (hint: try cell[0] or range[1:3])"`

**M2: Starlark error codes not exposed at raise** (starlark_worker.py lines 299-308)
- E1154 (forbidden construct) returns hardcoded message `f"forbidden construct '{reason}' at line {line}"`
- Reason is bare attribute name (e.g., `"__class__"`), not actionable hint
- Better: `"forbidden construct '__class__' (unsafe access); valid: standard builtins only"`

**M3: No source snippet in error output** (all error classes)
- ValidationError stores `line`, `col`, `code`, `message`, but NOT the source line itself
- User gets "line 42, col 15: unknown primitive type 'Arry'" but can't see context without reopening file
- Renderer could extract and show: `"  line 42: \shape{a}{Arry}...\n            ^^^^"`

**M4: Recovery error numbering misleading** (grammar.py lines 350-358)
- When 10 errors collected, shows `"found 10 errors:\n  1. [E1004]...\n  2. [E1051]...\n..."`
- But parser stops at a recovery point; later errors may be phantom consequences of first error
- User thinks "fix these 10 things" when actually just 2-3 root causes

## Low Findings

**L1: Bare position field unused** (validators, detector)
- ValidationError.__init__ accepts `position: int`, stored as `self.position`, but never displayed
- `__str__()` method uses only `line`, `col`, `code`, `hint` — `position` is dead field

**L2: FrameCountWarning not wired to user** (grammar.py line 591)
- `warnings.warn("E1180: animation has >30 frames...", stacklevel=2)` emitted but not caught/displayed
- Users never see "consider splitting" advice unless they explicitly enable warnings

**L3: Docs URL hardcoded per code** (core/errors.py line 59)
- `f"-> {_DOCS_BASE_URL}/{self.code}"` always shown, but no validation that URL exists
- If docs for E1103 don't exist, user sees broken link promise

## Notes

- **Error recovery works as designed** — collects errors until recovery point, raises combined ValidationError. But message formatting (repeated `[code]` prefixes, no summary) is unpolished.
- **Primitives and parser diverge** — parser errors are detailed with line/col and valid value lists; primitive errors are bare E1103 with only `detail=` field.
- **Starlark integration leaks abstraction** — raw ValueError and traceback filtering expose internal details; should be wrapped at boundary.
- **Selector validation is silent-by-design** — invalid selectors warn only, allowing "graceful degradation." This is documented but violates user expectation (parser said OK, runtime said no).

**Recommendation:** Ship with caveats; fix C1/C2/C3 (blocker-level bugs), prioritize H1/H2 (UX gaps). Medium issues are polish; Low are technical debt.
