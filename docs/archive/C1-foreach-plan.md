# C1: Loop-to-Command Bridge — `\foreach` Implementation Plan

> Addresses CRITICAL finding C1 from `ruleset-review-2026-04-10.md`:
> `\compute` can bind variables but cannot emit visual commands programmatically.

---

## 1. Chosen Approach: Hybrid (Approach C)

**`\compute` binds data, `\foreach` iterates with normal DSL commands.**

Rationale (from DSL comparison research):
- Mirrors TikZ `\foreach` that LaTeX users already know
- Keeps Starlark as computation layer without requiring it to know about visual commands
- Avoids dual-API maintenance burden (Starlark emit API vs DSL commands)
- DSL gains iteration without becoming a programming language
- Clear separation: complex logic in `\compute`, simple iteration in `\foreach`

### Syntax

```latex
% Simple range iteration
\foreach{i}{0..5}{
  \recolor{dp.cell[${i}]}{state=done}
}

% Iterate over compute-bound list
\compute{ path = [0, 2, 3, 5] }
\foreach{i}{${path}}{
  \recolor{h.cell[${i}]}{state=path}
}

% Nested foreach
\foreach{i}{0..2}{
  \foreach{j}{0..2}{
    \recolor{grid.cell[${i}][${j}]}{state=done}
  }
}
```

### Before/After Example (frog1_dp.tex, last step)

**Before (8 lines):**
```latex
\recolor{h.cell[5]}{state=idle}
\recolor{h.cell[0]}{state=path}
\recolor{h.cell[2]}{state=path}
\recolor{h.cell[3]}{state=path}
\recolor{h.cell[5]}{state=path}
\recolor{dp.cell[0]}{state=path}
\recolor{dp.cell[2]}{state=path}
\recolor{dp.cell[3]}{state=path}
\recolor{dp.cell[5]}{state=path}
```

**After (3 lines):**
```latex
\compute{ path = [0, 2, 3, 5] }
\foreach{i}{${path}}{
  \recolor{h.cell[${i}]}{state=path}
  \recolor{dp.cell[${i}]}{state=path}
}
```

---

## 2. Architecture

### Pipeline Position

```
.tex → Lexer → Parser → AST (with ForeachNode) → apply_frame()
                                                      ↓
                                              1. Run \compute blocks
                                              2. Expand \foreach (resolve iterable, substitute ${var})
                                              3. Apply expanded MutationCommands
                                                      ↓
                                              FrameSnapshot → Renderer
```

**Key constraint:** Expansion MUST happen inside `apply_frame()` after compute blocks
run, because the iterable may reference compute bindings (e.g., `${path}`).

### Why not a pure pre-pass?

The iterable `${path}` is only available after `\compute` runs. So expansion is
binding-aware and must happen at scene-application time, not as an AST-to-AST
transform before scene processing.

---

## 3. Implementation Phases

### Phase 1: Core `\foreach` (MVP)

**Files to modify:**

| File | Changes |
|------|---------|
| `parser/lexer.py` | Add `"foreach"` and `"endforeach"` to `_KNOWN_COMMANDS` |
| `parser/ast.py` | Add `ForeachCommand` dataclass |
| `parser/grammar.py` | Add `_parse_foreach()` method, wire into dispatch |
| `scene.py` | Add `_expand_foreach()` in `apply_frame()` after compute |

**AST node:**
```python
@dataclass(frozen=True)
class ForeachCommand:
    variable: str           # loop variable name, e.g. "i"
    iterable: str | list    # range string "0..5" or interpolation ref "${path}"
    body: tuple[MutationCommand, ...]  # commands inside the loop
    line: int = 0
    col: int = 0
```

**Parser (`_parse_foreach`):**
1. Consume `\foreach`
2. Parse `{variable}` — single IDENT
3. Parse `{iterable}` — either `N..M` range literal or `${binding}` interpolation
4. Parse body commands until `\endforeach`
5. Return `ForeachCommand` node

**Scene expansion (`_expand_foreach`):**
1. Resolve iterable: if range string `"0..5"` → `range(0, 6)`, if `${name}` → lookup in `self.bindings`
2. For each value in iterable:
   a. Clone each body command with `${variable}` substituted in all selector strings and param values
   b. Append cloned commands to expanded list
3. Return flat list of `MutationCommand`

**Substitution strategy for frozen dataclasses:**
- Use `dataclasses.replace()` to create modified copies
- Selectors are stored as `Selector` objects — need a `substitute(var, value)` method on `Selector` that returns a new `Selector` with `${var}` replaced
- String params: simple `str.replace("${var}", str(value))`

### Phase 2: Nested `\foreach`

- `_expand_foreach` calls itself recursively when body contains `ForeachCommand`
- Max nesting depth: 3 (same as substory) → error `E1170`
- Each nesting level adds its variable to a substitution context dict

### Phase 3: `\if` / `\endif` (optional, future)

- Conditional command emission inside `\foreach`
- Only if user demand justifies added complexity
- NOT part of this plan — noted for future consideration

---

## 4. Detailed File Changes

### 4.1 `parser/lexer.py`

Add to `_KNOWN_COMMANDS`:
```python
"foreach", "endforeach"
```

### 4.2 `parser/ast.py`

```python
@dataclass(frozen=True)
class ForeachCommand:
    """Loop that expands body commands for each value in iterable."""
    variable: str
    iterable_raw: str        # raw text: "0..5" or "${path}" or "[1,2,3]"
    body: tuple[MutationCommand, ...]
    line: int = 0
    col: int = 0
```

Update `MutationCommand` union type to include `ForeachCommand`.

### 4.3 `parser/grammar.py`

Add `_parse_foreach()`:
- Parse `{var}` — expect single IDENT
- Parse `{iterable}` — consume raw text between braces (range literal, interpolation, or list literal)
- Collect body commands in a loop until `endforeach` token
- Recursive: body can contain nested `\foreach`
- Error: `\foreach` with empty body → `E1171`
- Error: unclosed `\foreach` (EOF before `\endforeach`) → `E1172`

Wire into dispatch in `_parse_frame_commands()` and `_parse_prelude_commands()`.

### 4.4 `scene.py`

Add `_expand_commands()` method:
```python
def _expand_commands(self, commands, depth=0):
    """Expand ForeachCommand nodes into flat MutationCommand lists."""
    if depth > 3:
        raise ValidationError("foreach nesting exceeds max depth 3", code="E1170")
    expanded = []
    for cmd in commands:
        if isinstance(cmd, ForeachCommand):
            values = self._resolve_iterable(cmd.iterable_raw)
            for val in values:
                substituted = self._substitute_body(cmd.body, cmd.variable, val)
                expanded.extend(self._expand_commands(substituted, depth + 1))
        else:
            expanded.append(cmd)
    return expanded
```

Call in `apply_frame()` after compute blocks, before command application:
```python
# After: for cb in frame_ir.compute: self._run_compute(cb, starlark_host)
# Before: for cmd in frame_ir.commands: self._apply_command(cmd)
expanded = self._expand_commands(frame_ir.commands)
for cmd in expanded:
    self._apply_command(cmd)
```

### 4.5 `parser/selectors.py`

Add `Selector.substitute(variable: str, value: Any) -> Selector`:
- Walk the selector tree, replace `InterpolationRef(name=variable)` with concrete value
- Return new `Selector` with substitution applied

---

## 5. Error Codes

| Code | Meaning |
|------|---------|
| E1170 | `\foreach` nesting exceeds max depth (3) |
| E1171 | `\foreach` with empty body |
| E1172 | Unclosed `\foreach` (EOF before `\endforeach`) |
| E1173 | Invalid iterable in `\foreach` (not a range, list, or binding) |
| E1174 | `\foreach` variable name conflicts with existing binding |

---

## 6. Ruleset Updates

Add to `docs/spec/ruleset.md`:
- Section 2.1: Add `\foreach` / `\endforeach` to Base Commands table
- Section 6: Note that `\foreach` iterables can reference compute bindings
- Section 11: Add E1170-E1174 error codes
- Section 13: Add `\foreach` nesting depth limit (3)

---

## 7. Test Plan

| Test | Description |
|------|-------------|
| `test_foreach_range` | `\foreach{i}{0..2}{\recolor{a.cell[${i}]}{state=done}}` expands to 3 recolors |
| `test_foreach_binding` | `\compute{xs=[1,3]}` + `\foreach{i}{${xs}}{...}` uses binding |
| `test_foreach_nested` | 2-level nested foreach expands correctly |
| `test_foreach_max_depth` | 4-level nesting raises E1170 |
| `test_foreach_empty_body` | Empty body raises E1171 |
| `test_foreach_unclosed` | Missing `\endforeach` raises E1172 |
| `test_foreach_invalid_iter` | Non-iterable raises E1173 |
| `test_foreach_in_prelude` | `\foreach` works in prelude (before `\step`) |
| `test_foreach_in_step` | `\foreach` works inside step |
| `test_foreach_with_annotate` | `\foreach` body contains `\annotate` with arrow |
| `test_foreach_substitution` | `${var}` replaced in selectors AND param values |

---

## 8. Complexity Estimate

| Component | Effort | Lines (est.) |
|-----------|--------|-------------|
| AST node | Small | ~15 |
| Lexer | Trivial | ~2 |
| Parser | Medium | ~60 |
| Scene expansion | Medium | ~80 |
| Selector substitution | Medium | ~40 |
| Tests | Medium | ~150 |
| Docs/ruleset | Small | ~30 |
| **Total** | **Medium** | **~375** |

Estimated agent count for implementation: **3 agents** in parallel
1. Parser + AST (lexer, ast.py, grammar.py)
2. Scene expansion + selector substitution (scene.py, selectors.py)
3. Tests + docs (test files, ruleset.md)

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Frozen dataclass substitution complexity | Medium | Use `dataclasses.replace()` + recursive walk |
| Iterable resolution timing | High | Expand AFTER compute, BEFORE command apply |
| Infinite loop via huge range | Low | Cap iterable length (e.g., 10,000) → E1175 |
| `\foreach` inside `\substory` | Low | Allow — expansion is command-agnostic |
| Variable shadowing in nested foreach | Low | Inner variable shadows outer, Starlark-style |

---

## 10. Non-Goals (Explicitly Out of Scope)

- `\if` / `\else` / `\endif` — future consideration only
- `\compute` emitting commands (Approach B) — rejected in favor of Approach C
- `\while` loops — banned, consistent with Starlark restrictions
- `\foreach` generating `\shape` declarations — shapes are prelude-only, foreach expansion happens at frame time
- `\foreach` generating `\step` — steps define frame boundaries, cannot be dynamically created
