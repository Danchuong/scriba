# M2: Split `\recolor` Annotation Overload — `\reannotate` Command

> Addresses MEDIUM finding M2 from `ruleset-review-2026-04-10.md`:
> `\recolor` is overloaded with annotation semantics.

---

## 1. Problem

`\recolor` currently serves double duty:

```latex
% Element state change (clear semantics)
\recolor{dp.cell[2]}{state=done}

% Annotation recoloring (confusing — "recolor" modifies a child annotation)
\recolor{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}
```

Issues:
- Command name says "recolor element" but it modifies a child annotation
- Two different color palettes: `state=` (idle/current/done/...) vs `color=` (info/warn/good/...)
- `arrow_from=` as string in `\recolor` vs `Selector` in `\annotate` — inconsistent types
- Action-at-a-distance: which annotation gets recolored is implicit

---

## 2. Chosen Approach: Option B — `\reannotate` Command

**Rationale:** Lowest effort-to-value ratio. Only 3 lines in 1 file use the
annotation-recoloring form. Clean separation of concerns.

### New syntax

```latex
% Before (confusing)
\recolor{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}

% After (clear)
\reannotate{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}
```

### `\recolor` simplification

After migration, `\recolor` only accepts `state=` (required):
```latex
\recolor{target}{state=done}
```

### Deprecation path

1. Phase 1 (this PR): Add `\reannotate`, keep `color=`/`arrow_from=` on `\recolor` with deprecation warning
2. Phase 2 (future): Remove `color=`/`arrow_from=` from `\recolor`

---

## 3. Implementation

### Files to modify

| File | Changes |
|------|---------|
| `parser/lexer.py` | Add `"reannotate"` to `_KNOWN_COMMANDS` |
| `parser/ast.py` | Add `ReannotateCommand` dataclass |
| `parser/grammar.py` | Add `_parse_reannotate()`, wire into dispatch |
| `scene.py` | Add `_apply_reannotate()`, extract annotation-recolor logic from `_apply_recolor()` |
| `examples/cookbook/frog1_dp.tex` | Update 3 lines to use `\reannotate` |
| `docs/spec/ruleset.md` | Add `\reannotate` to command table, document deprecation |

### AST node

```python
@dataclass(frozen=True)
class ReannotateCommand:
    target: Selector | str
    color: str              # info/warn/good/error/muted/path
    arrow_from: str | None  # filter by source selector string
    line: int = 0
    col: int = 0
```

### Parser (`_parse_reannotate`)

1. Parse `{target}` — selector
2. Parse `{params}` — `color=` (required), `arrow_from=` (optional)
3. Validate color against `_VALID_ANNOTATE_COLORS`
4. Return `ReannotateCommand`

### Scene (`_apply_reannotate`)

Extract the annotation-recolor loop from current `_apply_recolor()` into
`_apply_reannotate()`. The logic is identical — just moved to its own handler.

### `\recolor` cleanup (Phase 1 — backward compatible)

In `_parse_recolor()`:
- If `color=` or `arrow_from=` is present, emit deprecation warning
- Still parse and create `RecolorCommand` with annotation fields
- `_apply_recolor()` still handles both paths

---

## 4. Error Codes

No new error codes needed — reuses existing:
- `E1113` — Unknown annotation color (already exists)
- `E1111` — Unknown annotate target (already exists)

---

## 5. Breaking Changes

- **0 breaking changes** in Phase 1 (backward compatible with deprecation warning)
- **3 lines** in `frog1_dp.tex` change from `\recolor` to `\reannotate`
- `frog1_dp_foreach.tex` also has 3 `\recolor` lines with `color=` to update

---

## 6. Complexity Estimate

| Component | Effort | Lines (est.) |
|-----------|--------|-------------|
| AST node | Small | ~10 |
| Lexer | Trivial | ~1 |
| Parser | Small | ~30 |
| Scene handler | Small | ~20 |
| Example updates | Trivial | ~6 |
| Docs/ruleset | Small | ~15 |
| **Total** | **Small** | **~80** |

Single agent can handle this.
