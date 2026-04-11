# Phase D: Generality Refactoring Plan ✅ COMPLETE

Based on 6-agent generality audit (2026-04-11). Fixes 4 systemic issues.

All phases completed 2026-04-11:
- S1 ✅ `0185173d` — Unified primitive interface
- S2 ✅ `88db77b8` — Theme colors + CSS cleanup
- S3 ✅ `3e1ecbfc` — Dynamic sizing recalc
- S4.1+S4.2 ✅ `6465dd3b` — Registry catalog + selector patterns
- S4.3 ✅ `88db77b8` — Centralize enums

---

## S1: Unified Primitive Interface ✅

**Problem:** emit_svg() has 3 signatures, constructor has 2 patterns, emitter uses if/elif on type names.

**Plan:**

### S1.1 — Unify emit_svg() signature
- **Files:** all 12 primitives + emitter.py
- **Change:** All primitives implement `emit_svg(self, *, render_inline_tex=None) -> str`
  - Cell-based primitives (Array, Grid, DPTable, NumberLine, Matrix) currently take `state` dict as first arg — move state management INTO the primitive (like PrimitiveBase subclasses already do)
  - Remove `annotations` param from emit_svg — pass via `set_annotations()` method before render
- **Emitter change:** Single dispatch: `prim.emit_svg(render_inline_tex=cb)` for ALL primitives
- **Delete:** The if/elif chain at emitter.py:325-342

### S1.2 — Unify constructor pattern
- **Files:** renderer.py, all Protocol-based primitives
- **Change:** All primitives use `Cls(name, params)` constructor (like PrimitiveBase)
  - Convert ArrayPrimitive, GridPrimitive, DPTablePrimitive, NumberLinePrimitive, MatrixPrimitive from `Factory().declare()` to direct `__init__(name, params)`
  - Or: all use factory pattern. Pick ONE.
- **Delete:** The if/elif chain at renderer.py:198-201

### S1.3 — Generic selector expansion
- **Files:** emitter.py, scene.py
- **Change:** Add `expand_range(lo, hi) -> list[str]` method to primitive interface
  - Primitive returns its own target names for a range (e.g., Array returns `cell[0]..cell[n]`, NumberLine returns `tick[0]..tick[n]`)
  - Delete hardcoded "numberline" check in emitter.py:213-229
- **Change:** Add `expand_alias(alias) -> list[str]` method
  - Stack returns `item[top_idx]` for `.top`
  - Delete hardcoded "stack" check in scene.py:225-229

### S1.4 — Generic annotation support
- **Files:** emitter.py, base.py
- **Change:** Add optional `set_annotations(anns)` and `annotation_height() -> int` to interface
  - Delete `hasattr(prim, "_arrow_height_above")` magic check

**Agents needed:** 3
1. Unify emit_svg + constructor (S1.1 + S1.2) — touches all primitives
2. Generic selector expansion (S1.3) — emitter + scene + all primitives
3. Generic annotation support (S1.4) — emitter + base + array + dptable

---

## S2: Theme-Aware Colors (Dark Mode) ✅

**Problem:** All primitives hardcode light-theme hex colors (`#f6f8fa`, `#d0d7de`, `#212529`, `#6c757d`). CSS variables exist but are ignored because inline styles have higher specificity.

**Plan:**

### S2.1 — Define color constants in base.py
- **File:** base.py
- **Change:** Create a `ThemeColors` dataclass with all shared colors:
  ```python
  @dataclass(frozen=True)
  class ThemeColors:
      bg: str = "#f6f8fa"
      bg_alt: str = "#f1f3f5"
      border: str = "#d0d7de"
      border_light: str = "#dee2e6"
      fg: str = "#212529"
      fg_muted: str = "#6c757d"
      fg_dim: str = "#adb5bd"
  
  LIGHT_THEME = ThemeColors()
  DARK_THEME = ThemeColors(
      bg="#161b22", bg_alt="#1c2128", border="#30363d",
      border_light="#21262d", fg="#c9d1d9", fg_muted="#8b949e",
      fg_dim="#484f58",
  )
  ```
- **All primitives:** Replace hardcoded hex with `self._theme.bg`, `self._theme.border`, etc.
- **Emitter:** Pass theme to primitives based on document options

### S2.2 — Replace hardcoded colors in each primitive
- **Files:** All 12 primitives
- **Change:** Replace every `"#f6f8fa"`, `"#d0d7de"`, `"#212529"`, `"#6c757d"`, `"#adb5bd"` with theme attribute reference
- **Scope per primitive:**
  - CodePanel: 4 color constants → theme refs
  - VariableWatch: ~6 hardcoded colors → theme refs
  - HashMap: ~5 hardcoded colors → theme refs
  - LinkedList: ~4 hardcoded colors → theme refs
  - Queue: uses STATE_COLORS (already good) + ~2 hardcoded
  - Graph/Tree: ~2 hardcoded colors
  - Array/Grid/DPTable: ~2 hardcoded colors
  - Stack: ~2 hardcoded colors
  - NumberLine: ~3 hardcoded colors
  - Matrix: ~3 hardcoded colors
  - Plane2D: ~8 hardcoded colors (worst offender)

### S2.3 — CSS variable alignment
- **File:** render.py, scriba-scene-primitives.css
- **Change:** Remove conflicting global `svg text` rule entirely (primitives set their own fonts)
- **Change:** Add `[data-theme="dark"]` CSS overrides that match DARK_THEME colors

**Agents needed:** 3
1. base.py ThemeColors + emitter integration (S2.1)
2. Replace colors in 6 new primitives: Queue, LinkedList, HashMap, CodePanel, VariableWatch, Plane2D (S2.2a)
3. Replace colors in 6 existing primitives: Array, Grid, DPTable, Stack, NumberLine, Matrix + CSS cleanup (S2.2b + S2.3)

---

## S3: Remaining Dynamic Sizing Gaps ✅ DONE

- Queue set_value recalc ✅
- LinkedList set_value recalc ✅
- VariableWatch value column dynamic + recalc ✅
- HashMap already dynamic (computes per-render) ✅

**Remaining minor items:**
- NumberLine: col_label_offset hardcoded to 14
- Matrix: col_label_offset hardcoded to 14
- Extract padding magic numbers (+12, +16, +20) to named constants

**Agents needed:** 1 (NumberLine + Matrix col_label fix + extract padding constants)

---

## S4: Parser Generalization ✅

**Problem:** Hardcoded command list, selector accessor dispatch, validation enums scattered.

**Plan:**

### S4.1 — Registry-based primitive catalog
- **File:** renderer.py
- **Change:** Replace hardcoded `PRIMITIVE_CATALOG` dict with decorator-based registration:
  ```python
  @register_primitive("Queue")
  class Queue(PrimitiveBase): ...
  ```
  - Auto-discover primitives from `primitives/` package
  - Auto-register CSS assets via class attribute `css_file = "scriba-queue.css"`
- **Delete:** Manual imports and catalog dict in renderer.py

### S4.2 — Generic selector accessor
- **File:** selectors.py
- **Change:** Replace hardcoded if/elif dispatch with primitive-provided accessor patterns:
  ```python
  class Queue(PrimitiveBase):
      SELECTOR_PATTERNS = {"cell": int, "front": None, "rear": None}
  ```
  - Parser validates against primitive's declared patterns
  - No need to add code for each new accessor type

### S4.3 — Centralize validation enums
- **File:** Create `scriba/animation/constants.py`
- **Change:** Single source of truth for valid states, colors, positions
  ```python
  VALID_STATES = frozenset({"idle", "current", "done", ...})
  VALID_ANNOTATION_COLORS = frozenset({"info", "warn", ...})
  ```
- **Parser:** Import from constants.py instead of defining local frozensets
- **Error messages:** Auto-include valid values: `f"unknown state {s!r}, valid: {', '.join(sorted(VALID_STATES))}"`

### S4.4 — Configurable starlark limits
- **Files:** starlark_worker.py, starlark_host.py
- **Change:** Move all limits to a `StarlarkConfig` dataclass, pass from renderer
- **Low priority** — current limits work fine

**Agents needed:** 2
1. Registry + generic selectors (S4.1 + S4.2)
2. Centralize enums + error messages (S4.3)

---

## Priority Order

| Phase | Effort | Impact | Agents |
|-------|--------|--------|--------|
| **S3 remaining** | Small | Medium | 1 |
| **S2 (dark mode)** | Medium | High — users see broken dark mode | 3 |
| **S1 (unified interface)** | Large | High — enables future primitives | 3 |
| **S4 (parser)** | Medium | Medium — developer experience | 2 |
| **Total** | | | **9 agents** |

## Recommended Execution

1. **S3 remaining** (1 agent) — quick win
2. **S2** (3 agents parallel) — visible user impact
3. **S1** (3 agents, some sequential: S1.1+S1.2 first, then S1.3+S1.4) — architecture
4. **S4** (2 agents parallel) — developer ergonomics
