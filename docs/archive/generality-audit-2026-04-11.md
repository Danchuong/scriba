# Generality Audit — 2026-04-11

**6-agent audit** checking whether solutions across the entire Scriba project are general or hardcoded.

---

## Agent 1: _render_svg_text() Callers — ALL 30 CALLS PASS

After the base.py change (foreignObject respects text_anchor), all 30 callers are consistent:
- 9 calls with `text_anchor="start"` → x = LEFT EDGE
- 15 calls with `text_anchor="middle"` → x = CENTER
- 3 calls with `text_anchor="end"` → x = RIGHT EDGE
- 3 calls with default → x = CENTER

**Status: NO ISSUES**

---

## Agent 2: Dynamic Sizing — 3/6 STILL HARDCODED

| Primitive | Sizing Dynamic? | Mutation Recalc | Verdict |
|-----------|----------------|-----------------|---------|
| Queue | Partial | Missing set_value() | STILL HARDCODED |
| LinkedList | YES | Missing set_value() | MOSTLY GENERAL |
| HashMap | Partial | NO recalc at all | STILL HARDCODED |
| VariableWatch | Partial | NO recalc; value col static 100px | STILL HARDCODED |
| CodePanel | YES | N/A (immutable) | GENERAL |
| Stack | YES | YES (push/pop) | MOSTLY GENERAL |

### Key Issues:
1. **VariableWatch value column is completely static** — always 100px, never computed from values
2. **HashMap never recalculates** column widths after apply_command/set_value
3. **Queue/LinkedList missing set_value() recalc** — cell stays oversized after dequeue
4. **Hardcoded padding** (`+12`, `+16`, `+20`) everywhere instead of computed/constants

---

## Agent 3: Emitter + Scene + Renderer — 9 CATEGORIES HARDCODING

### CRITICAL:
1. **emit_svg() signature dispatch** (emitter.py:325-342) — if/elif chain checks primitive type name to decide which arguments to pass. Violates Liskov Substitution.
2. **Constructor dispatch** (renderer.py:198-201) — hardcoded list of type names decides `Factory(name, params)` vs `Factory().declare(name, params)`.
3. **Selector expansion** (emitter.py:213-229) — special-cases "numberline" for `.tick[i]` vs `.cell[i]`, and "stack" for `.top`.

### HIGH:
4. **Magic attribute check** `_arrow_height_above` — not an interface contract
5. **CSS asset mapping** — hardcoded dict of primitive→CSS file

### MEDIUM:
6. **Global layout constants** `_PADDING=16`, `_PRIMITIVE_GAP=50` — not per-primitive
7. **All primitives centered** — no left/right alignment option
8. **`.top` special case** only for Stack in scene.py

### Impact: Adding ANY new primitive requires changes in 3-4 files.

---

## Agent 4: Graph/Tree/Array/NumberLine/Matrix Fixes

| File | Status | Issues |
|------|--------|--------|
| graph.py | PASS | None |
| tree.py | PASS | None |
| array.py | PASS | 1 minor clarity |
| numberline.py | FAIL | 3 hardcoded: caption height, col_label_offset=14, min tick spacing |
| matrix.py | CONDITIONAL | col_label_offset hardcoded to 14 instead of computed |

---

## Agent 5: Parser + Starlark — 23 ISSUES

### CRITICAL (3):
1. **Selector accessor dispatch** (selectors.py:76-89) — hardcoded if/elif chain for cell/tick/item/node/edge/range
2. **Known commands** (lexer.py:61-78) — hardcoded frozenset, new commands need manual addition
3. **Primitive catalog** (renderer.py) — hardcoded dict, no plugin/discovery

### HIGH (5):
4. Validation enums scattered across grammar.py (states, colors, positions) — 4-6 locations to update per change
5. Default values scattered between parser and AST
6. Error messages don't show valid values

### MEDIUM (12):
7. All 12 Starlark sandbox limits hardcoded with no configuration mechanism

### Impact: Adding new command = 2-3 files. New primitive = 3-4 files. New state = 4-6 locations.

---

## Agent 6: CSS + HTML Template — 12 ISSUES

### CRITICAL:
1. **Dark mode broken for ALL primitives** — hardcoded light-theme hex colors in Python (`#f6f8fa`, `#d0d7de`, `#212529`), never reference CSS variables
2. **Global `svg text` rule** still sets font-family/size/weight on all text
3. **Highlight stroke-width** hardcoded in CSS, doesn't use variable system
4. **MetricPlot print** forces `#000 !important`

### HIGH:
5. CodePanel colors completely not theme-aware
6. VariableWatch/HashMap border colors hardcoded
7. Plane2D grid colors bypass CSS variables
8. LinkedList text colors hardcoded

### MEDIUM:
9. CSS variables defined but Python never uses them
10. Plane2D axes not themeable
11. Print styles missing for most primitives

### Root cause: Colors defined in TWO places (CSS variables AND Python constants). Python wins because inline styles have highest specificity, making CSS variables useless.

---

## Summary: Systemic Issues

### Issue 1: No Unified Primitive Interface
- emit_svg() has 3 different signatures
- Constructor has 2 different patterns
- Selector expansion is per-type
- **Fix**: Define a single ABC/Protocol that all primitives implement

### Issue 2: Colors Hardcoded in Python, Not CSS
- Every primitive hardcodes `#f6f8fa`, `#d0d7de`, `#212529`, `#6c757d`
- CSS variables exist but are bypassed by inline styles
- Dark mode is completely broken for primitives
- **Fix**: Primitives should emit CSS classes, not inline colors (except state colors)

### Issue 3: Dynamic Sizing Not Truly Dynamic
- 3/6 new primitives have static widths despite "dynamic sizing" changes
- set_value() doesn't trigger recalc in most primitives
- Hardcoded padding constants everywhere
- **Fix**: Centralize sizing logic, recalc on every mutation

### Issue 4: Adding New Primitives Requires 3-4 File Changes
- renderer.py: catalog + constructor dispatch
- emitter.py: emit_svg dispatch + selector expansion
- lexer.py: known commands (if new command)
- selectors.py: accessor dispatch (if new selector pattern)
- **Fix**: Plugin/registration system instead of hardcoded catalogs
