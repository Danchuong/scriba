# Scriba Ruleset Review — 2026-04-10

> 3-agent parallel review of `docs/spec/ruleset.md` covering compute model,
> grammar/syntax quality, and DSL design comparison.

---

## CRITICAL (1)

### C1. Excessive verbosity — no loop-to-command bridge

`\compute` can bind variables but cannot emit `\recolor`/`\apply` calls
programmatically. For a DP problem with N=100, the author must write hundreds
of lines by hand or use an external code generator. Every other programmable
visualization DSL (Manim, TikZ `\foreach`, Penrose constraints) allows the
logic layer to drive the visual layer. This is the single biggest usability
problem.

**Source:** DSL Design agent

---

## HIGH (3)

### H1. Unbounded recursion via `def`

The spec bans `while` but allows `def` and `for`. Since `def` is unrestricted,
users can write mutually recursive functions (e.g., `def f(n): return f(n+1)`).
The AST scanner does not check for or limit recursion. Resource limits (5s wall
clock, 10^8 ops, Python ~1000 recursion limit) make it safe in practice, but
the spec doesn't explicitly document recursion depth limit — Python's limit is
an implementation detail, not a spec guarantee.

**Verdict:** The subset is theoretically Turing-complete. The resource limits
make it *effectively* non-Turing-complete in practice, which is the correct
design for a DSL sandbox.

**Source:** Compute Model agent

### H2. `exec()`-based sandbox weaknesses

The sandbox relies on AST scanning + restricted `__builtins__`, which is a
known-weak approach. Specific concerns:

- **`hash()` is exposed and non-deterministic** — `hash()` returns randomized
  values across Python invocations (PYTHONHASHSEED). If a user stores `hash()`
  output in bindings, results differ between runs, breaking the byte-identical
  determinism guarantee.
- **`RLIMIT_AS` not enforced on macOS/Darwin** — memory bomb via
  `x = [0] * (10**7)` is not reliably caught.
- **`SIGALRM` is Unix-only** — Windows has no wall-clock backstop, only the
  step counter. If `sys.settrace` is bypassed (e.g., C-extension code paths in
  builtins like `sorted` on huge lists), there is no fallback.
- **`isinstance` is exposed** — can probe the type hierarchy.

**Source:** Compute Model agent

### H3. Selector parse errors have no error codes

`SelectorParser._error()` raises `ValidationError` with `position=` but no
`code=`. The `_expect()` method in the main parser also raises without `code=`.
All selector syntax errors go unclassified. The error catalog has `E1106`
("Unknown target selector") but that covers semantic resolution, not
parse-level syntax errors.

**Source:** Grammar/Syntax agent

---

## MEDIUM (7)

### M1. Mutable global state leaks across frames

The spec says frame-local scope shadows global, but the implementation sends
`globals` dict to the worker per-request. A frame-local `\compute` that
modifies a *mutable* global (e.g., `my_list.append(x)`) will persist that
mutation because Python lists are mutable references. The AST scanner does not
prevent `.append()`, `.extend()`, `.pop()`, or dict mutation via `[]=`. This
contradicts the "frame-local dropped at next step" promise unless the renderer
deep-copies globals before each frame eval.

**Source:** Compute Model agent

### M2. `\recolor` overloaded with annotation semantics

`\recolor` accepts both `state=` (element recoloring, palette: idle/current/
done/dim/error/good/path) and `color=` (annotation recoloring, palette: info/
warn/good/error/muted/path). This is action-at-a-distance: the command name
says "recolor" but it modifies a child annotation identified by an implicit
selector via `arrow_from=`. Should be a separate command or use explicit
annotation targeting.

Additionally, `\recolor` with `color=` overlaps `\annotate` with `color=` —
both can change annotation colors. The `\recolor` route accepts `arrow_from=`
as a string while `\annotate` parses it as a Selector. This asymmetry (string
vs. Selector for the same concept) is an inconsistency.

**Source:** Grammar/Syntax agent + DSL Design agent

### M3. Spec BNF vs implementation mismatch for generic indexed accessors

The BNF in the spec (Section 3) and `selectors.py` docstring both show
`accessor ::= ... | IDENT`, but the implementation also handles
`IDENT "[" idx "]"` (e.g., `point[0]`, `line[1]`) by constructing
`NamedAccessor(name="point[0]")` — embedding the index in the name string.
This works but is undocumented in the spec's BNF and makes downstream
pattern-matching fragile.

**Source:** Grammar/Syntax agent

### M4. `NamedAccessor` catch-all delays error reporting

Any unrecognized accessor name (e.g., `a.foo`) parses successfully as
`NamedAccessor(name="foo")`. Typos in accessor names won't be caught at parse
time — only downstream when the primitive rejects unknown parts. This is by
design for extensibility but delays error reporting.

**Source:** Grammar/Syntax agent

### M5. Stringly-typed state system

States (`current`, `done`, `dim`, `good`, `path`) are string literals with no
IDE support or compile-time checking beyond runtime error E1109. The fixed
7-state palette is limiting for complex visualizations that need to distinguish
3+ groups.

**Source:** DSL Design agent

### M6. No diff/delta semantics

Each step must re-specify the full set of changes from the previous frame.
There is no "only show what changed" shorthand. Authors repeat recoloring of
old cells to `dim`/`done` on every step. Manim handles this naturally with
`.animate` chaining.

**Source:** DSL Design agent

### M7. SIGALRM Unix-only

On Windows, `hasattr(signal, "SIGALRM")` is False, so only the step counter
protects against infinite loops. If `sys.settrace` is somehow bypassed, there
is no wall-clock backstop on Windows.

**Source:** Compute Model agent

---

## LOW (5)

### L1. Missing builtins for algorithm visualization

`chr`/`ord` (character conversion for string algorithms), `pow` (modular
exponentiation), `math.log`/`math.sqrt` (for metric plots) would be useful
additions to the pre-injected API.

### L2. Boolean parsing is implicit

`arrow=true` (ident) and `arrow="true"` (string) both work, but `arrow=True`
(not a valid token) does not. This is fine but undocumented.

### L3. Substory error code gaps

E1363, E1364, E1367 are unused/skipped in the E1360-E1369 range. Not a bug,
but the numbering gap suggests codes were reserved or removed.

### L4. No error code for matrix cell limit (10,000)

Section 13 of the ruleset lists the 10,000 cell limit but shows "--" for the
error code.

### L5. `_KNOWN_COMMANDS` whitelist in lexer

Unknown `\foo` is emitted as `CHAR`, meaning extension commands cannot be added
without modifying the lexer. Intentional but worth noting for extensibility.

---

## INFO — Positive Observations

### Grammar quality

- **Selectors are unambiguous.** The recursive-descent parser uses deterministic
  lookahead. Edge selectors `G.edge[(A,B)]` are visually distinct.
- **Parameter style is consistent.** All commands use `{target}{key=value,...}`.
- **Commands are orthogonal.** `\highlight` (ephemeral), `\recolor` (persistent
  state), `\apply` (data mutation), `\annotate` (labels/arrows) each serve
  distinct roles.
- **String quoting is clear.** Double-quote only, with `\"`, `\\`, `\n` escapes.
- **Good extensibility.** New primitives only need new accessor names.

### Determinism

- Well-addressed overall. No `random`, no I/O, no time functions. Python 3.7+
  dicts are insertion-ordered. `set` iteration sorted by `str()` representation.
- Only gap: `hash()` builtin (see H2).

### DSL comparison positioning

| vs | Verdict |
|----|---------|
| Mermaid / D2 | **Better** — step animation with narration is a genuine differentiator |
| TikZ | **Better** — much simpler for the target use case |
| VisuAlgo | **Comparable** — similar output quality, but VisuAlgo requires no authoring |
| Manim | **Worse** — no programmatic scene construction, no interpolated transitions |
| Penrose | **Worse** — no constraint solver; layout is manual for most primitives |

### Naming quality

Generally good. `\shape`, `\step`, `\narrate`, `\apply`, `\recolor`,
`\annotate` are self-documenting. Minor issues: `\apply` is vague, `\compute`
doesn't convey "bind variables." Learning curve is low for LaTeX users.

### Missing features for competitive programming education

- No code panel showing algorithm source alongside visualization
- No variable watch / call stack display
- No auto-step from code execution (trace mode)
- No comparison mode (two algorithms side by side)
- No export to GIF/MP4 for sharing on Codeforces/AtCoder editorials
- No conditional annotations (show annotation only when condition holds)

---

## Recommended Top Actions

1. **Add loop-to-command bridge** — let `\compute` emit commands, or add
   `\foreach` construct (addresses C1)
2. **Remove `hash()` from builtins** — breaks determinism, no use case
   (addresses H2)
3. **Add error codes for selector parse failures** — classify currently
   unclassified errors (addresses H3)
4. **Deep-copy globals between frames** — enforce scope isolation guarantee
   (addresses M1)
5. **Document recursion depth limit** — add explicit limit to spec (addresses H1)
