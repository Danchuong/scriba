# Report 2 — Errors & Edge Cases (Empirical)

Tested via `uv run python render.py /tmp/test_*.tex -o /tmp/out.html`.

## Results Table

| Test | Variant | Behavior | Category | Severity | Source |
|------|---------|----------|----------|----------|--------|
| 1 | `value=$i$` (LaTeX math) | E1005 "unexpected token CHAR" line 5 col 30 — `$` not valid | VAGUE | high | `grammar.py:1594` |
| 1 | `value=${i}` (correct interp) | Exit 0, renders `InterpolationRef(name='i', subscripts=())` literal | **SILENT (wrong output)** | **🔴 critical** | `scene.py:445–457` |
| 1 | `value="i"` (quoted literal) | Exit 0, renders literal `"i"`, not loop index | SILENT | med | by-design but no warn |
| 1 | `value=i` (bare word) | Exit 0, renders literal `"i"` | SILENT | med | by-design but no warn |
| 2 | `a.cell[99]` out of range | Exit 0, two `UserWarning` lines, command silently dropped | SILENT | high | `emitter.py:459,593` |
| 2 | `a.cell[abc]` non-numeric | Exit 0, two `UserWarning` lines | SILENT | high | `emitter.py:459,593` |
| 2 | `a.bogus` unknown accessor | Exit 0, two `UserWarning` lines | SILENT | high | `emitter.py:459,593` |
| 2 | `nonexistent.cell[0]` unknown shape | Exit 0, **zero stderr**, command silently dropped | SILENT | high | `emitter.py` |
| 3a | `\shape{a}{Array}{}` missing size | E1400 "Array requires 'size' or 'n'" with hint | ACTIONABLE | low | `errors.py:E1400` |
| 3b | `\apply{a.cell[0]}{}` empty params | Exit 0, silent | SILENT | med | `grammar.py` |
| 3c | `\foreach{i}{}` empty iterable | E1173 "cannot resolve iterable ''" no hint | VAGUE | med | `scene.py:429` |
| 3d | `\foreach{}` missing var | E1173 "invalid variable name in foreach: ''" with caret | ACTIONABLE | low | `grammar.py:989` |
| 4a | `\reocolor` typo'd command | E1006 lists all valid commands — **no "did you mean?" hint** | VAGUE | med | `grammar.py:374` |
| 4b | `stat=current` typo'd param | E1109 generic — no "did you mean state?" hint | VAGUE | med | parser |
| 4c | `state=currnet` typo'd value | E1109 + "did you mean `current`?" | ACTIONABLE | low | `errors.py:suggest_closest` |
| 5a | `\apply` before `\shape`/`\step` | Exit 0, renders "No frames" widget — zero error | **SILENT** | **🔴 critical** | `scene.py / grammar.py` |
| 5b | Missing `\endsubstory` | E1361 "unclosed \substory" with caret | ACTIONABLE | low | `grammar.py:E1361` |
| 6 | Inline `%` after `value=5` | E1001 "unterminated brace argument" — misdiagnosis | VAGUE | high | `grammar.py:E1001` |
| 6b | Inline `%` after `\shape{...}` | Exit 0, renders correctly | OK | — | — |

## Summary

**Overall error-reporting quality is uneven but improving.** E14xx parameter errors (3a) are exemplary — code, hint, URL in one line. Value-typo detection (4c) correctly fires `suggest_closest`. Structural mistakes like unclosed `\substory` produce a caret pointer.

**Weak spots:** every selector failure (out-of-range, non-numeric, unknown accessor, unknown shape) only emits a Python `UserWarning` on stderr — no E-code, no line number, no entry in rendered output. Completely unknown shape produces zero signal. Command-level typos list all valid commands but never invoke `suggest_closest`, despite the infrastructure existing for enum values. Inline `%` comment produces a confusing E1001 "unterminated brace" rather than explaining `%` is the LaTeX comment char.

## The foreach-`i` Bug — Real, Two Failure Modes

**Mode A — `value=$i$`:** hard parse error (E1005, CHAR token) with no explanation that `${i}` is the correct interpolation form.

**Mode B — `value=${i}`:** silently renders garbage. `_sub_value` (`scene.py:445–457`) handles `str/dict/list/tuple/Selector` but the parameter value is stored as an `InterpolationRef` object (`grammar.py:1575–1576`), `_sub_value` hits the fallthrough `return v` at line 457 and passes the raw Python object to the emitter, which calls `str()` on it and writes `InterpolationRef(name='i', subscripts=())` into the SVG text node.

**Fix — one line:**
```python
# in _sub_value, before fallthrough:
if isinstance(v, InterpolationRef) and v.name == variable:
    return val_str
```

Root cause: `_sub_index_expr` (`scene.py:487`) correctly handles `InterpolationRef` for selector positions, but `_sub_value` (used for parameter values) has no equivalent branch.

`value=i` and `value="i"` silently render the literal string `i`; technically by-design for bare-word and quoted-string values, but no warning that `${i}` is the only path to the loop variable.

## Top 5 Footguns to Fix or Document

1. **`value=${i}` renders `InterpolationRef(...)` repr** — `_sub_value` must handle `InterpolationRef` like `_sub_index_expr` does. Bug; fix required.

2. **Unknown shape name fully silent** — `\recolor{nonexistent.cell[0]}{state=current}` exits 0 with no stderr. Should raise E1115 or named warning with the shape id and source location.

3. **Selector failures are `UserWarning` not E-codes** — out-of-range index, non-numeric index, unknown accessor surface only via `warnings.warn()` with no line number. Route through `warnings_collector` with E1115 + source location.

4. **`\apply` before `\shape`/`\step` silently produces "No frames"** — user who omits `\shape` gets no error, just empty widget. Pre-materialisation check that shape table is non-empty would catch this.

5. **Command-typo hints not wired** — `suggest_closest` exists in `errors.py:43` and is used for enum values but not for command names in `_raise_unknown_command` (`grammar.py:374`). Adding it = one-line change.
