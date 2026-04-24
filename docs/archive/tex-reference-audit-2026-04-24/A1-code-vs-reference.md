# A1 — Code vs. Reference Ground-Truth Audit

**Date:** 2026-04-24
**Reference:** `docs/SCRIBA-TEX-REFERENCE.md` (956 lines)
**Scope:** Compare reference against actual code (`scriba/tex/`, `scriba/animation/primitives/`, `scriba/animation/`)

---

## Executive Summary

- **3 CRITICAL** gaps: `grid` env option undocumented; Queue `front`/`rear` selectors absent; Graph `add_edge`/`remove_edge` dynamic ops absent.
- **4 HIGH** gaps: "16 primitives" claim wrong (code has 15); `hidden` state color fabricated (no `STATE_COLORS` entry); LinkedList `insert`/`remove` ops undocumented; `\hl` not listed as inner command (claim of "12 total" wrong).
- **6 MEDIUM** gaps: `STATE_COLORS` hex values don't match reference; Graph `orientation`, `auto_expand`, `split_labels`, `tint_by_source`, `global_optimize` params missing; Plane2D `remove_*` ops missing; `stable + directed=true` silent UserWarning; `global_optimize=true` silent UserWarning; `\reannotate` requires `color=` but reference implies optional.
- **4 LOW** gaps: `\substory` accepts `id=` key (undocumented); `grid` accepted but silently dropped; 5 state hex values factually wrong; `layout="auto"` mentioned in code warning but not documented.

---

## Findings Table

| Severity | Reference § | Issue | Evidence | Fix |
|---|---|---|---|---|
| CRITICAL | §10 Env Options | `grid` is a valid option key (accepted, not rejected by E1004) but absent from §10. Parsed then silently ignored (not stored in `AnimationOptions`). | `constants.py:46`; `ast.py:291-298` (no `grid` field) | Add `grid` row to §10 or remove from `VALID_OPTION_KEYS` to force E1004 |
| CRITICAL | §7.14 Queue | Queue exposes `.front` and `.rear` selectors (pointer arrows), in `SELECTOR_PATTERNS` and validated. Absent from §7.14 and §8. | `queue.py:103-108, 218-220` | Add `.front` / `.rear` to §7.14 selectors + §8 Queue row |
| CRITICAL | §7.4 Graph Ops | Graph supports `\apply{G}{add_edge={from="A",to="B"}}` and `remove_edge`. Absent from §7.4. | `graph.py:828-868` (E1471/E1472) | Document both ops |
| HIGH | §7 "16 primitives" | `primitives/__init__.py` exports 15 classes. No 16th primitive exists. | `primitives/__init__.py:29-44` | Change to "15 primitives" |
| HIGH | §6 `hidden` state | Reference claims hidden = "invisible" color. Code: `"hidden"` in `VALID_STATES` but has **no entry** in `STATE_COLORS` — behavior is SVG skip via `if state == "hidden": continue`, not a CSS color. | `_types.py:74-86`; `tree.py:625`, `graph.py:1215`, `plane2d.py:831` | Correct §6: hidden elements omitted from SVG output, not given a CSS color |
| HIGH | §7.13 LinkedList | Supports `\apply{ll}{insert={"index":i,"value":v}}` and `{remove=i}`. §7.13 shows only construction + selectors. | `linkedlist.py:139-168` | Add `insert` / `remove` examples |
| HIGH | §5 "12 inner commands" | `\hl{step-id}{tex}` is a real inner command (in `\narrate`), referenced in §5.3 but not in the 12-command list. Effectively a 13th. | `extensions/hl_macro.py:1-127` | Add `\hl` as §5.13; update count to 13 |
| MEDIUM | §6 hex colors | Reference uses Wong CB-friendly palette (`current=#0072B2`, `good=#56B4E9`, etc.). Actual `STATE_COLORS` uses different values: `current=#0070d5`, `good` stroke=`#2a7e3b`, `path` fill=`#e6e8eb`, `error` stroke=`#e5484d`. | `_types.py:74-86` | Update hex in §6 or remove hex and say "see CSS" |
| MEDIUM | §7.4 Graph params | Accepts `orientation` (TB/LR), `auto_expand`, `split_labels`, `tint_by_source`, `tint_by_edge`, `global_optimize`. None in §7.4. | `graph.py:647-691` | Add at least `orientation`, `auto_expand` |
| MEDIUM | §7.9 Plane2D ops | Supports `remove_point/line/segment/polygon/region`, `add_segment`, `add_polygon`, `add_region`. §7.9 mentions only `add_point` + `add_line`. | `plane2d.py:358-392` | Add all 9 apply ops |
| MEDIUM | §13 Gotchas | `Graph(layout="stable", directed=True)` silently emits UserWarning about upside-down DAG. Undocumented. | `graph.py:652-665` | Add §13.8: "stable + directed renders poorly — use hierarchical for DAGs" |
| MEDIUM | §13 Gotchas | `Graph(global_optimize=True)` accepted but emits UserWarning (no-op, GEP-20 not wired). Silent non-behavior. | `graph.py:677-691` | Add §13.9 gotcha or note in §7.4: forward-compat flag, no current effect |
| MEDIUM | §5.9 `\reannotate` | Reference implies `color=` and `arrow_from=` both optional. Code requires `color=` (raises E1113 if absent). | `_grammar_commands.py:163-177` | Add "color= is required" note |
| LOW | §5.12 `\substory` | Accepts `id=` in addition to `title=`. Used for substory HTML id. §5.12 only shows `title=`. | `constants.py:49-52`; `_grammar_substory.py:100` | Document `id=` |
| LOW | §10 `grid` | Parsed (E1004 not raised) but no field in `AnimationOptions` — silently consumed. Authors may use it expecting effect. | `constants.py:46`; `ast.py:291-298`; `grammar.py:521-527` | Document as recognized-but-ignored, or remove from valid keys |
| LOW | §14 Limits | Reference says "Graph stable ≤20 nodes, ≤50 frames" (correct). Omits force-layout cap `_MAX_NODES=100`. 101-node force graph raises E1474. | `graph.py:63`; `graph_layout_stable.py:31-32` | Add "Graph (force layout): ≤100 nodes" |
| LOW | §5.2 Starlark forbidden | Reference lists `while, import, class, lambda, try`. Code also forbids `async def`, `async for`, `async with`, `await`, `yield`, `yield from`, walrus `:=`, `match`. | `starlark_worker.py:100-115` | Update forbidden list |
