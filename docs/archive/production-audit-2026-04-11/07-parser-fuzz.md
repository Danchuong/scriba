# Agent 07: Parser/Lexer Fuzz Edge Cases

**Score:** 4/10
**Verdict:** needs-work

## Prior fixes verified

| Finding | Status | Evidence |
|---------|--------|----------|
| **H3** Selector parse errors no codes | ✓ FIXED | All errors have codes (E1010, E1011) |
| **M4** validate_selector() never called | ✓ FIXED | Called in emitter.py:362 with proper validation |
| **M6** Out-of-range index silent | ✓ FIXED (PARTIAL) | Warnings issued in `_validate_expanded_selectors()` |
| **H6** Error recovery silent | ✗ UNFIXED | No warning when `error_recovery=True` captures errors |
| **M3** NamedAccessor catch-all | ✗ UNFIXED | `a.nonexistent_accessor` parses, error delayed |

## Critical Findings

**C1: Unclosed brace at EOF accepted silently**
- `\shape{a}{Array}{size=5` (missing final `}`) parses successfully
- `_read_param_brace()` at line 1106-1107 returns `{}` when no LBRACE found instead of raising E1001
- **Impact:** Silently truncated animations, data loss
- **Code path:** grammar.py `_read_param_brace() → if at_end: return {}` (no error)

**C2: Empty parameter braces accepted**
- `\shape{a}{Array}{}` treated as `params={}` without validation
- Should require at least `{size=N}` for Array primitive
- **Impact:** Animations render empty shapes, confusing users

## High Findings

**H1: Mismatched braces with content treated as EOF**
- `\shape{a}{Array}{size=5 content here` stops at EOF rather than erroring on missing `}`
- Lexer correctly produces tokens, but parser's EOF-as-valid-terminator masks the error

**H2: Unicode support verified but undocumented**
- `\shape{café}{Array}{size=5}` parses correctly
- Identifiers accept Unicode (isalpha/isalnum) but spec doesn't guarantee this
- Emoji in `\narrate{🚀}` also parses (no escaping required)

**H3: Deeply nested `\foreach` (5+ levels) allowed**
- Parser has no depth limit on `\foreach` nesting (unlike `\substory` with `_MAX_SUBSTORY_DEPTH=3`)
- 5+ levels parse without error; may cause exponential expansion at runtime
- Should add configurable limit or warn

## Medium Findings

**M1: `\foreach` without `\endforeach` properly caught**
- E1172 raised correctly at EOF (verified ✓)

**M2: `\substory` without `\endsubstory` properly caught**
- E1361 raised correctly at EOF (verified ✓)

**M3: Negative numbers in selectors accepted**
- `a.cell[-1]` parses as `CellAccessor(indices=(-1,))`
- No semantic validation that index >= 0
- Primitive emitter/renderer must catch; no parser-level check

**M4: Unknown primitive accepted at parse time**
- `\shape{a}{UnknownPrimitive}{}` parses successfully
- Validation deferred to runtime (by design for extensibility, but risky)

**M5: Unknown keys in `\apply` accepted**
- `\apply{a.cell[0]}{badkey=10}` parses without error
- Primitive.validate_selector() doesn't validate parameter keys

**M6: `${}` interpolation syntax validated late**
- `${undefined_var}` accepted at parse time, fails at runtime frame expansion
- No static check for variable binding availability

## Low Findings

**L1: Selector chains not validated**
- `a.cell[0].cell[0]` raises E1009 correctly (secondary accessors not allowed)
- But error message could be clearer

**L2: Very long identifiers/strings accepted**
- 10k+ char identifiers and strings parse without limits
- No DoS protection for parser input size (only 1MB source limit at top level)

**L3: Comment handling correct**
- `%` inside strings correctly NOT treated as comment start
- Lexer properly scans only outside string literals

## Notes

**Fuzz matrix summary** (17 tests):
- Empty env: OK
- Mismatched braces: silently parsed (C1)
- 5-level foreach: OK (but no depth limit warning)
- Unicode: OK
- Integer overflow (99999999999): OK (primitive validates)
- Unknown primitive: OK (runtime validation)
- Negative index: parsed (runtime validation)
- Trailing comma in lists: E1010 (correct)

**Error recovery (H6) verdict:** When `error_recovery=True`, parsing errors are collected but user receives no warning until all parsing completes. If 10 commands fail, animation appears partial with no indication of failures. Use Python `warnings.warn()` in `_raise_combined_errors()` (line 340) but it's only issued if errors exist — verify it's reached.

**Recommendation:** Fix C1 (unclosed braces EOF handling) before v0.5.0 release. Add depth limit warning for `\foreach`. Implement strict parameter validation in primitives.
