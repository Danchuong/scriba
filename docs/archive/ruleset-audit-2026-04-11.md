# Ruleset Audit — 2026-04-11

6-agent parallel audit of Scriba documentation and validation quality after Phase D refactoring.

## Agents

1. **Ruleset vs Code** — ruleset.md vs actual implementation
2. **Spec Consistency** — all docs/spec/*.md cross-references and accuracy
3. **Primitive Docs** — per-primitive documentation completeness
4. **Tutorial/Guide** — getting-started, guides, extensions accuracy
5. **Legacy Cleanup** — archive/legacy misplaced files, stale docs
6. **Error/Validation** — error messages, validation, edge cases

---

## CRITICAL (2)

### C1: Selectors not validated at runtime

**File:** `scriba/animation/emitter.py` lines 174-240

`_expand_selectors()` accepts arbitrary target keys from `shape_state` without calling `prim.validate_selector()`. Invalid selectors like `a.cell[999]` on a 10-cell array silently pass through — no error, no warning, silent data loss.

**Impact:** Users think their command worked when it did nothing.

**Fix:** Add `prim.validate_selector(suffix)` check in `_emit_frame_svg()` before `set_state()`.

### C2: 54 error codes undocumented

**File:** `scriba/animation/errors.py`

Only 8 of 54 error codes have documented exception classes. The remaining 46 are raised via generic `animation_error(code, detail)` without dedicated classes.

Undocumented codes include: E1004–E1007, E1009–E1013, E1050–E1056, E1102, E1109, E1112–E1113, E1150–E1155, E1170–E1173, E1182, E1360–E1368, E1460–E1505.

---

## HIGH (8)

### H1: 5 primitives have zero documentation

Queue, CodePanel, HashMap, LinkedList, VariableWatch have no .md files anywhere. Only documented in code comments.

Missing docs should cover: constructor params, selector patterns, apply commands, state colors, example .tex.

### H2: 5 primitives missing from ruleset.md

ruleset.md §5 says "11 types" but code registers 16. Missing: CodePanel, HashMap, LinkedList, Queue, VariableWatch.

### H3: Selectors for 5 primitives missing from ruleset §3

Per-Primitive Selectors table omits:
- CodePanel: `.line[i]`, `.all`
- HashMap: `.bucket[i]`, `.all`
- LinkedList: `.node[i]`, `.link[i]`, `.all`
- Queue: `.cell[i]`, `.front`, `.rear`, `.all`
- VariableWatch: `.var[name]`, `.all`

### H4: Empty collection not validated

- VariableWatch: `names=[]` silently renders empty
- Graph: `nodes=[]` → `fruchterman_reingold()` returns `{}` silently
- Array: `size=0` accepted, renders nothing
- No `E1103` raised for any of these

### H5: Error messages lack context

Some errors say "expected number" without showing what was found. Compare:
- Bad: `"unterminated string in selector"` (no syntax hint)
- Good: `f"unknown recolor state {state!r}; valid: {', '.join(sorted(VALID_STATES))}"` (grammar.py)

### H6: Parser error recovery silent

When `error_recovery=True`, parsing errors collected but user not warned until all parsing completes. User may think animation is correct when 10 commands failed silently.

### H7: environments.md only documents 8/14 commands

Missing: `\cursor`, `\reannotate`, `\foreach`, `\endforeach`, `\substory`, `\endsubstory`. These are in ruleset.md §2 but absent from the "single source of truth" environments.md.

### H8: getting-started.md only lists 6/16 primitives

New users will think only Array, Grid, DPTable, Graph, Tree, NumberLine exist. Missing 9 modern primitives.

---

## MEDIUM (12)

### M1: animation-plugin.md wrong CSS class

Lines 212, 219, 265: `scriba-filmstrip` → should be `scriba-frames`.

### M2: usage-example.md wrong data attributes

Lines 212, 215: `data-frame` → `data-step`, `scriba-stage` → `scriba-stage-svg`. Missing required `id` attribute.

### M3: Array/Matrix don't reject size=0

`\shape{a}{Array}{size=0}` accepted silently. Should raise E1103 for `size < 1`. Same for Matrix `rows=0` or `cols=0`.

### M4: validate_selector() exists but never called

Every primitive implements `validate_selector()` but the framework never invokes it. Orphaned validation code.

### M5: Starlark security sets not centralized

`_BLOCKED_ATTRIBUTES`, `_FORBIDDEN_BUILTINS`, `_FORBIDDEN_NODE_TYPES` defined inline in `starlark_worker.py`. Should be in `constants.py`.

### M6: Out-of-range index silent

`\recolor{a.cell[999]}{}` on 10-cell array: parser accepts, scene stores, emitter passes through, primitive stores state but never renders it. No error at any stage.

### M7: Annotation target not validated

`\annotate{a.cell[999]}{...}` on 10-cell array silently vanishes.

### M8: Lexer error codes undocumented

E1012, E1013, E1099 used in lexer.py but not documented in errors.py.

### M9: \recolor vs \reannotate docs inconsistent

environments.md §3.7 shows `\recolor` with `color=` and `arrow_from=` params. ruleset.md §2 shows `\reannotate` as the primary annotation command. scene-ir.md shows both. Should standardize.

### M10: PHASE-D-PLAN.md duplicated

Both `/docs/PHASE-D-PLAN.md` (root) and `/docs/planning/phase-d.md` exist with near-identical content.

### M11: extensions/fastforward.md still in active docs

Feature was removed in Phase C but spec file remains in active `extensions/` directory. Should move to `archive/`.

### M12: CodePanel 1-based indexing undocumented

CodePanel uses `line[1]`, `line[2]` (1-based) while all other primitives use 0-based. Not documented anywhere.

---

## LOW (3)

### L1: E1103 message formatting inconsistent

array.py line 76: `f"[E1103] Array size {size} exceeds..."` — redundant `[E1103]` prefix since ValidationError already includes `code=E1103`.

### L2: DEFAULT_STATE not asserted

`DEFAULT_STATE = "idle"` assumed to be in `VALID_STATES` but no assertion at module load time.

### L3: Narration HTML escaping order

`_render_narration()` handles `$...$` math but escape order may allow `<script>` in narration text if hl macros are applied first.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 2 |
| HIGH | 8 |
| MEDIUM | 12 |
| LOW | 3 |
| **Total** | **25** |

## Recommended Fix Order

1. **Plan A — Docs** (H1-H3, H7-H8, M1-M2, M9-M12): Fix ruleset, create 5 primitive docs, update tutorials
2. **Plan B — Validation** (C1, C2, H4, M3-M4, M6-M8): Runtime selector validation, zero-size rejection, error code docs
3. **Plan C — Error UX** (H5-H6, M5, M8, L1-L3): Better error messages, centralize security sets
