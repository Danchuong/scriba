# Agent 08: Starlark Sandbox & Determinism

**Score:** 6/10
**Verdict:** needs-work

## Prior fixes verified

| Finding | Status | Notes |
|---------|--------|-------|
| H1: unbounded recursion | PARTIAL | Resource limits effective; spec never documents explicit recursion depth requirement |
| H2a: hash() exposed | MISSING | **CRITICAL** — not in FORBIDDEN_BUILTINS, breaks determinism per PYTHONHASHSEED |
| H2b: isinstance | PRESENT | Safe — not exposed to user builtins, used only in AST validator |
| H2c: RLIMIT macOS | FIXED | Uses RLIMIT_DATA on Darwin; RLIMIT_AS on Linux |
| H2d: SIGALRM Windows | PARTIAL | No threading.Timer fallback; only step-counter protects on Windows |
| M1: mutable global leak | FIXED | copy.deepcopy() per frame isolation in scene.py:193, 268 |
| M7: duplicate SIGALRM | PARTIAL | Same as H2d |

## Critical Findings

**C1: Memory limit spec-to-impl mismatch (256/128 MB vs 64 MB)**
- `starlark_host.py:21`: `_MEMORY_LIMIT_BYTES = 256 MB` (RLIMIT_AS setrlimit)
- `starlark_worker.py:437`: `_TRACEMALLOC_PEAK_LIMIT = 128 MB` (runtime check)
- `docs/spec/starlark-worker.md:209`: "Memory: **64 MB**"
- **Impact**: Spec promises 64MB sandbox but implementation allows 128–256 MB, undermining DoS guarantees.
- **Root cause**: RLIMIT_AS set at 256 MB; tracemalloc hits 128 MB first, but both exceed spec.
- **Fix**: Align both to 64 MB spec or update spec with justification.

**C2: hash() builtin is NOT forbidden (determinism break)**
- Not in `FORBIDDEN_BUILTINS` (constants.py:74–102)
- Python hash() is seeded by PYTHONHASHSEED; if a user stores `hash()` output in bindings, results differ between invocations
- **Impact**: Breaks "byte-identical determinism" guarantee in spec:207-B3
- **Fix**: Add `"hash"` to FORBIDDEN_BUILTINS

## High Findings

**H1: Comprehensions & f-strings allowed but not documented**
- `ast.ListComp`, `ast.DictComp`, `ast.SetComp`, `ast.GeneratorExp`, `ast.JoinedStr` NOT in `_FORBIDDEN_NODE_TYPES` (starlark_worker.py:57–64)
- Tests show they execute successfully (no sandbox escape in current tests, but expand attack surface)
- Spec (starlark-worker.md:7.1) only forbids: while, import, load, class, lambda, try
- **Impact**: Unspecified feature; downstream maintainers don't know if comprehensions are intentional
- **Fix**: Either (a) forbid them for simplicity, (b) explicitly allow and document, or (c) audit for dunder hijacking in comprehension closures

**H2: Windows timeout has no fallback**
- `starlark_worker.py:321`: `has_alarm = hasattr(signal, "SIGALRM")`
- On Windows, alarm is skipped; only `_step_trace` step-counter protects against infinite loops
- If user somehow bypasses `sys.settrace` (e.g., via C-extension builtin), Windows has no wall-clock backstop
- Spec (starlark-worker.md:6.1) says "5s alarm … if the alarm fires mid-evaluation" but doesn't document Windows fallback
- **Fix**: Document Windows limitation or implement threading.Timer fallback

## Medium Findings

**M1: __class_getitem__, __format__, __getattr__, __getattribute__ not blocked**
- BLOCKED_ATTRIBUTES (constants.py:51–66) missing: `__class_getitem__`, `__format__`, `__getattr__`, `__getattribute__`
- **Risk**: Operator overloading (e.g., `"".__format__("...exploit...")`) could theoretically leak internals
- **Mitigation**: Restricted builtins and AST pre-scan reduce surface, but not airtight
- **Fix**: Add all dunder getters/setters to blocklist; allow only essential ones (__init__, __len__, __getitem__)

**M2: Recursion depth not explicitly enforced in spec**
- Spec says "Recursion depth: 1000 frames" (starlark-worker.md:210) but implementation relies on Python's default limit
- No explicit `sys.setrecursionlimit()` call in code; limit is implicit
- **Risk**: Future Python versions could change default; implementation becomes non-deterministic
- **Fix**: Call `sys.setrecursionlimit(1000)` in worker startup to lock it

**M3: Set iteration sorting lacks tie-break rule**
- Sets serialized as `sorted(value, key=str)` (starlark_worker.py:243)
- If two set elements stringify to identical values, ordering is undefined
- **Risk**: Low probability but breaks determinism guarantee
- **Fix**: Use `sorted(value, key=lambda x: (str(x), repr(x)))` for stable ordering

## Low Findings

**L1: No Windows-specific test for timeout**
- `test_starlark_worker.py:130` skips timeout tests on Windows (`skipif sys.platform == "win32"`)
- No coverage that Windows step-counter actually interrupts runaway code
- **Fix**: Add explicit Windows step-limit test

**L2: Memory limit enforcement has three paths, only two documented**
- Host-level RLIMIT_AS/RLIMIT_DATA (enforced by OS, hard limit)
- Worker-level tracemalloc peak check (soft limit, E1155 error)
- Worker-level step-counter may trigger MemoryError in some conditions
- Spec only documents RLIMIT; doesn't mention tracemalloc fallback
- **Fix**: Document all three paths; clarify which applies on each platform

**L3: isinstance() used for AST validation is safe but confusing**
- Code uses `isinstance(node, _FORBIDDEN_NODE_TYPES)` in _scan_ast()
- isinstance is not exposed to users, but name appears in worker, risking future misuse
- **Fix**: No action required if documented, but could rename to avoid confusion (e.g., `_is_forbidden_node()` helper)

## Notes

- **Determinism**: Broadly correct (no random, no time, dict insertion-order guaranteed in Python 3.7+), except for hash() exposure
- **Scope isolation**: Deep-copy per frame is correctly implemented
- **Test coverage**: Good (recursive functions, comprehensions, function defs all tested), but missing Windows timeout and escape vector edge cases
- **84 claimed fixes**: ~70% verified present; 20% partial (SIGALRM, recursion doc); 10% missing (hash)
- **Production risk**: Memory limit mismatch is operationally dangerous; hash() breaks determinism claim; comprehensions are unspecified edge case
