# Scriba DSL Ruleset Audit — 2026-04-17

User reported past confusion: `\foreach` with `i` as loop var while assigning value
caused errors. Audit of grammar, error reporting, and documentation completeness.

## Reports

1. [01-grammar-parser.md](01-grammar-parser.md) — command inventory + selector grammar + foreach semantics + footguns
2. [02-errors-edge-cases.md](02-errors-edge-cases.md) — empirical error-message stress test, foreach-`i` bug reproduction
3. [03-docs-coverage.md](03-docs-coverage.md) — SCRIBA-TEX-REFERENCE / cookbook / tutorial coverage gaps

## Critical Findings

### 🔴 BUG (one-line fix) — `value=${i}` renders raw Python repr

In `scene.py:445–457`, `_sub_value` handles `str/dict/list/tuple/Selector` but
NOT `InterpolationRef`. When user writes `\apply{a.cell[${i}]}{value=${i}}`,
the cell value renders as the literal string `InterpolationRef(name='i', subscripts=())`.

`_sub_index_expr` (scene.py:487) handles `InterpolationRef` correctly for
selector positions; `_sub_value` is missing the equivalent branch. Fix:

```python
# in _sub_value, before fallthrough:
if isinstance(v, InterpolationRef) and v.name == variable:
    return val_str
```

### 🔴 Silent failures (every selector mistake)

| Mistake | Current behavior |
|---|---|
| `a.cell[99]` (out of range) | UserWarning only, no line, no E-code |
| `a.cell[abc]` (non-numeric) | UserWarning only |
| `a.bogus` (unknown accessor) | UserWarning only |
| `nonexistent.cell[0]` (unknown shape) | **Zero output**, exit 0 |
| `\apply` before `\shape` / `\step` | Renders empty "No frames" widget |

These should all be hard errors with E-codes and source location.

### 🟠 Footgun: bare identifier in selector vs `${}`

`a.cell[i]` parses as the literal string `"i"` (no warning).
`a.cell[${i}]` is the only way to interpolate.
Parser does not warn when bare identifier matches a foreach/compute variable name.
Documented nowhere prominent.

### 🟠 Command-typo hints not wired

`suggest_closest` exists in `errors.py:43` and works for enum values
(`state=currnet` → "did you mean `current`?") but is NOT called in
`_raise_unknown_command` (`grammar.py:374`). So `\reocolor` lists every valid
command instead of suggesting `\recolor`. One-line fix.

### 🟠 `%` inside brace argument breaks parsing

`\apply{a.cell[0]}{value=5%inline comment}` raises misleading E1001
"unterminated brace argument". Real cause: `%` is the LaTeX comment char
and is stripped to end of line, leaving brace unbalanced.

### 🟡 Doc inconsistencies

- `error-codes.md` says Starlark timeout 3s; spec + reference say 5s
- `error-codes.md` says memory 128 MB; spec + reference say 64 MB
- E1182 collision: "invalid cursor state" vs "missing narration"
- E1057 documented as reserved but is actively raised
- Tutorial §10 falsely claims `\foreach`/`\compute` don't work in diagrams (they do)
- `SCRIBA-TEX-REFERENCE` §8 selector table omits ALL Plane2D selectors
- `\step[label=...]`, `\annotate arrow=true` undocumented
- No `\substory` recipe in cookbook or tutorial

## Suggested Fix Order

### Round 1 — Bugs (no design debate)
1. `_sub_value` InterpolationRef branch (`scene.py:457`)
2. Wire `suggest_closest` into `_raise_unknown_command` (`grammar.py:374`)
3. Convert selector `UserWarning`s into E1115/E1106 with source location
4. Hard error when `\apply` runs with no `\shape` defined

### Round 2 — Doc fixes
5. Reconcile error catalog discrepancies (timeout, memory, E1182, E1057)
6. Add Plane2D selector table to SCRIBA-TEX-REFERENCE §8
7. Document foreach scoping + bare-`i` vs `${i}` distinction prominently
8. Fix tutorial §10 `\foreach`/`\compute` claim
9. Add `\substory` tutorial section + cookbook recipe
10. Document `\step[label=...]` and `\annotate arrow=true`

### Round 3 — Polish
11. `%` inside brace args: emit a clear error explaining LaTeX comment behavior
12. Empty `\foreach{i}{}{...}` → suggest range/list syntax
13. Empty substory → emit warning with line info

## Bug Severity Matrix

| ID | Severity | Class | Effort |
|---|---|---|---|
| `_sub_value` InterpolationRef | 🔴 critical | runtime correctness | trivial (1 line) |
| Silent unknown shape | 🔴 critical | error reporting | small |
| Selector UserWarning → error | 🔴 critical | error reporting | medium |
| `\apply` before `\shape` silent | 🔴 critical | error reporting | small |
| Bare `i` vs `${i}` | 🟠 high | docs + parser warn | small |
| Command-typo hints | 🟠 high | UX | trivial |
| `%` in brace args | 🟠 high | parser error msg | small |
| Catalog inconsistencies | 🟡 medium | docs | small |
| Plane2D selectors missing | 🟡 medium | docs | small |
| Tutorial §10 wrong | 🟡 medium | docs | trivial |
