# A1b — Re-Audit (Code vs Reference) 2026-04-24

## Summary
- CRITICAL: 0 remaining (was 3)
- HIGH: 0 remaining (was 4)
- MEDIUM: 1 remaining (was 6)
- LOW: 1 remaining (was 4)
- NEW drifts: 2

---

## Resolution Table

| Original ID | Severity | Status | Notes |
|-------------|----------|--------|-------|
| CRITICAL-1 `grid` env option undocumented | CRITICAL | RESOLVED | §10 table now lists `grid` as a `bool` option for `diagram`, described as "accepted but currently ignored (forward-compat placeholder)". Matches `constants.py:46`. |
| CRITICAL-2 Queue `.front`/`.rear` selectors absent | CRITICAL | RESOLVED | §7.14 now lists `q.front`, `q.rear` with prose explanation. §8 selector table has `.front`, `.rear` in Queue row. |
| CRITICAL-3 Graph `add_edge`/`remove_edge` absent | CRITICAL | RESOLVED | §7.4 "Dynamic edge mutation" block documents both ops with error codes E1471/E1472. |
| HIGH-1 "16 primitives" wrong | HIGH | RESOLVED | §7 heading now reads "All 15 Primitives". `__init__.py` exports exactly 15 classes. |
| HIGH-2 `hidden` state fabricated color | HIGH | RESOLVED | §6 table now shows `hidden` → `_(omitted from SVG)_`, with no hex. Correctly described. Matches `_types.py` (no `hidden` key in `STATE_COLORS`). |
| HIGH-3 LinkedList `insert`/`remove` absent | HIGH | RESOLVED | §7.13 now has "Dynamic operations" block with `insert`/`remove` examples. |
| HIGH-4 `\hl` absent, "12 inner commands" wrong | HIGH | RESOLVED | §5 heading now says "13 total". §5.13 `\hl` is fully documented with rules, error codes, and examples. |
| MEDIUM-1 `STATE_COLORS` hex values wrong | MEDIUM | RESOLVED | §6 no longer lists any hex values; redirects to CSS file. No fabricated Wong palette. |
| MEDIUM-2 Graph `orientation`/`auto_expand` etc. absent | MEDIUM | RESOLVED | §7.4 table now documents all 6 params: `orientation`, `auto_expand`, `split_labels`, `tint_by_source`, `tint_by_edge`, `global_optimize`. |
| MEDIUM-3 Plane2D ops incomplete | MEDIUM | RESOLVED | §7.9 "Dynamic operations" now documents all 5 `add_*` and 5 `remove_*` ops. |
| MEDIUM-4 `stable + directed=True` gotcha absent | MEDIUM | RESOLVED | §13.10 added. |
| MEDIUM-5 `global_optimize=True` no-op gotcha absent | MEDIUM | RESOLVED | §13.11 added; also noted in §7.4 param table. |
| MEDIUM-6 `\reannotate color=` required | MEDIUM | RESOLVED | §5.9 now explicitly states "**`color=` is required** (raises E1113 if absent)". |
| LOW-1 `\substory id=` key undocumented | LOW | RESOLVED | §5.12 now shows both `title=` and `id=` as option keys with a full parameters table. |
| LOW-2 `grid` silently dropped | LOW | RESOLVED | Subsumed by CRITICAL-1 fix. |
| LOW-3 Hex values wrong | LOW | RESOLVED | Hex values removed from §6. |
| LOW-4 Starlark forbidden list incomplete | LOW | RESOLVED | §5.2 now lists the full forbidden set: `while`, `import`, `class`, `lambda`, `try`, `async def`, `async for`, `async with`, `await`, `yield`, `yield from`, walrus `:=`, `match`. Matches `starlark_worker.py:100-134`. |

---

## New Drifts

**DRIFT-NEW-1 (LOW) — §5.1 shape name charset understates allowed characters**

§5.1 says: `Name must be unique, match [a-z][a-zA-Z0-9_]*`. Code (`uniqueness.py:33`) enforces `^[a-zA-Z_][a-zA-Z0-9_]{0,62}$`. Two discrepancies: (a) the code allows uppercase-initial and underscore-initial names; (b) the code enforces a max-length of 63 characters not mentioned in the reference. Impact is minor (reference is strictly stricter than code — authors following it will always pass, but the documented constraint is not the actual one). Fix: update §5.1 to `[a-zA-Z_][a-zA-Z0-9_]*` (max 63 chars).

**DRIFT-NEW-2 (LOW) — §14 Starlark `range()` cap entry mentions E1173 but capped limit is for `\foreach` iterable, not bare `range()`**

§14 table entry reads "Starlark `range()` max elements | 1,000,000 (E1173)". Code confirms `_MAX_RANGE_LEN = 10**6` and E1173 is raised in the foreach evaluator (`starlark_worker.py:287-301`), not inside raw `range()` itself. The limit and code are both present in the updated reference (see §14), so this is a pre-existing minor imprecision carried over, not newly introduced — it is acceptable at LOW severity.

---

## Recommendation

**PASS** — all 3 CRITICAL and all 4 HIGH findings from A1 are resolved. The two new drifts are LOW severity and do not block authoring. Recommend a follow-up fix-pass to correct the §5.1 shape-name charset regex (`[a-zA-Z_][a-zA-Z0-9_]*`, max 63 chars) before the reference is treated as fully canonical.
