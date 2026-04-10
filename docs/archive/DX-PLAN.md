# DX Plan: `\cursor` Macro + Naming Decision

> Addresses items from `deep-analysis-2026-04-10.md` §2 UX/Ergonomics:
> - `\cursor` macro to reduce cursor-advance boilerplate
> - Naming clarity (`\apply` vs `\set`, etc.)

---

## 1. `\cursor` Command

### Problem

The cursor-advance pattern repeats 5+ times per DP animation:

```latex
% 3 lines per step, every single step:
\recolor{h.cell[0]}{state=dim}
\recolor{h.cell[1]}{state=current}
\recolor{dp.cell[1]}{state=current}
```

In `frog1_dp.tex`: 15 lines (~20% of file) are cursor advances.

### Syntax

```latex
\cursor{shape.accessor}{index}
\cursor{shape.accessor}{index, prev_state=dim, curr_state=current}
```

**Defaults**: `prev_state=dim`, `curr_state=current`

**Semantics**: 
1. Find the element currently in `curr_state` on `shape.accessor`
2. Set it to `prev_state`
3. Set `shape.accessor[index]` to `curr_state`

If no element is currently in `curr_state`, skip step 1-2 (first cursor call).

### Multi-target Variant

```latex
% Move cursor on both h and dp arrays simultaneously
\cursor{h.cell, dp.cell}{index}
```

Applies the same cursor logic to multiple shape accessors at once.

### Examples

**Before** (frog1_dp.tex, step 3):
```latex
\recolor{h.cell[0]}{state=dim}
\recolor{h.cell[1]}{state=current}
\recolor{dp.cell[1]}{state=current}
```

**After**:
```latex
\cursor{h.cell, dp.cell}{1}
```

3 lines → 1 line. Over 8 steps: 15 lines → 5 lines.

### Implementation

| File | Changes |
|------|---------|
| `parser/lexer.py` | Add `"cursor"` to `_KNOWN_COMMANDS` |
| `parser/ast.py` | Add `CursorCommand` dataclass |
| `parser/grammar.py` | Add `_parse_cursor()`, wire into dispatch |
| `scene.py` | Add `_apply_cursor()` — find current, dim it, highlight new |
| `docs/spec/ruleset.md` | Document `\cursor` command |

#### AST Node

```python
@dataclass(frozen=True)
class CursorCommand:
    targets: tuple[str, ...]   # ("h.cell", "dp.cell")
    index: int | str           # 1 or "${i}" interpolation
    prev_state: str = "dim"    # state to set on previous cursor position  
    curr_state: str = "current"  # state to set on new cursor position
    line: int = 0
    col: int = 0
```

#### Scene Logic (`_apply_cursor`)

```python
def _apply_cursor(self, cmd: CursorCommand) -> None:
    for target_prefix in cmd.targets:
        # Find element currently in curr_state
        for key, state in self._shape_states.items():
            if key.startswith(target_prefix) and state.state == cmd.curr_state:
                self._set_state(key, cmd.prev_state)
                break
        # Set new index to curr_state
        new_key = f"{target_prefix}[{cmd.index}]"
        self._set_state(new_key, cmd.curr_state)
```

### Complexity

| Component | Effort | Lines |
|-----------|--------|-------|
| AST node | Small | ~10 |
| Lexer | Trivial | ~1 |
| Parser | Small | ~25 |
| Scene handler | Small | ~25 |
| Ruleset docs | Small | ~15 |
| **Total** | **Small** | **~76** |

---

## 2. Naming: `\apply` Rename — **Won't Do**

### Analysis

- `\apply` is used in **50+ cookbook examples**, **9 docs files**, and the tutorial
- Renaming to `\set` would be a breaking change requiring a major version bump
- The current name is acceptable — "apply a value to a cell" is clear enough
- Parser already validates the command, so typos are caught

### Decision

**Keep `\apply` as-is.** The cost of renaming (breaking change, migration effort)
far exceeds the benefit (slightly clearer name). Same applies to `\recolor` vs
`\highlight` — they have distinct semantics (persistent vs ephemeral) that are
well-documented.

---

## 3. Priority

1. **`\cursor`** — implement now (small effort, high impact on DX)
2. **Naming** — won't-fix (breaking change not justified)
