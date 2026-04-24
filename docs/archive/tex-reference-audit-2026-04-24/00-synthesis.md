# TEX-REFERENCE Audit — Synthesis

**Date:** 2026-04-24
**Target:** `docs/SCRIBA-TEX-REFERENCE.md` (956 lines) — single-source-of-truth for AI agents authoring `.tex` for Scriba.
**Method:** 4 parallel independent audits.

- [A1 — Code vs Reference](A1-code-vs-reference.md) — ground-truth (hallucination + omission)
- [A2 — Spec vs Reference](A2-spec-vs-reference.md) — doc gap analysis across 14 spec files
- [A3 — Examples vs Reference](A3-examples-vs-reference.md) — pattern coverage vs 53 .tex examples
- [A4 — LLM Cold-Read](A4-llm-coldread.md) — usability audit standalone

---

## Converged Findings (flagged by ≥2 audits)

### CRITICAL — factual errors in reference

1. **"16 primitives" wrong** (A1 HIGH). Code has 15. Change heading.
2. **`\hl` missing from §5 command list** (A1 HIGH, A2 LOW, A4 MEDIUM). §5 says "12 inner commands" but `\hl` is a functional 13th. Add §5.13.
3. **`hidden` state color fabricated** (A1 HIGH). Reference says color="invisible" but code has no `STATE_COLORS` entry — elements are omitted from SVG entirely.
4. **Visual state hex values wrong** (A1 MEDIUM). Reference Wong palette ≠ actual `STATE_COLORS`. Either replace or drop hex.

### HIGH — silent wrong-output risks for AI authors

5. **`\compute` inside `\step` frame-local** (A2 HIGH, A4 HIGH — contradiction between §3.1 prelude and §9.5 example). Bindings from in-step `\compute` are dropped at next step. Must clarify.
6. **`${var}` outside `\foreach` unreliable** (A4 HIGH). §13.2 says "may fail" with no reason or workaround. Explain.
7. **Missing Starlark builtins** (A2 HIGH). `isinstance, repr, round, chr, ord, pow, map, filter` allowed in code, absent from §5.2.
8. **Missing Starlark forbidden constructs** (A1 LOW, A2). Reference lists 5 forbidden; code forbids 13+ (`async def`, `async for`, `async with`, `await`, `yield`, `yield from`, walrus, `match`).
9. **Starlark `range()` 10^6 cap** (A2 HIGH). E1173 on overflow, undocumented.
10. **Tree mutation ops missing** (A2 HIGH). `add_node`, `remove_node`, `cascade`, `reparent` — only way to mutate Tree during animation; absent.
11. **Plane2D severely underdocumented** (A1 MEDIUM, A3 HIGH). Missing `add_segment`, `add_polygon`, `add_region`, `remove_*` ops, inline batch params `points=/lines=/segments=`, `aspect=`, per-primitive `width=`.
12. **Graph dynamic ops missing** (A1 CRITICAL). `add_edge` / `remove_edge` with E1471/E1472 codes absent from §7.4.
13. **Graph flow-network params missing** (A1 MEDIUM, A2 MEDIUM, A3 MEDIUM). `orientation`, `auto_expand`, `split_labels`, `tint_by_source`, `tint_by_edge`, `global_optimize` — production-used in `demos/mcmf.tex`, `demos/dinic.tex`.
14. **Queue `.front` / `.rear` selectors absent** (A1 CRITICAL, A2 MEDIUM). In SELECTOR_PATTERNS; not documented.
15. **LinkedList `insert` / `remove` ops absent** (A1 HIGH).
16. **Matrix advanced params missing** (A2 MEDIUM). `colorscale`, `vmin/vmax`, `row_labels`, `col_labels`.
17. **MetricPlot advanced params missing** (A2 LOW). `show_legend`, two-axis mode, per-series config.

### HIGH — usability / cold-read

18. **No render/run instructions** (A4 HIGH). Cold AI can't self-verify.
19. **Multi-target `\cursor{a.cell, b.cell}{i}` not shown** (A3 HIGH, 8+ example files). §5.10 only shows single-target.
20. **Nested `for` loops in `\compute` for 2D DP** (A3 HIGH, 6+ files). §5.2 shows only one-liners.
21. **Graph layout decision criteria absent** (A4 HIGH). When to use `force`/`stable`/`hierarchical`? No guidance.
22. **Dijkstra-shape example missing** (A4 HIGH). No `Graph` + `Array` side-by-side example in §9.

### MEDIUM — clarifications

23. **"selector" term undefined** (A4 MEDIUM). Add 2-sentence definition in §8.
24. **Node ID quoting rule (`G.node[A]` vs `G.node["A"]`)** (A4 MEDIUM).
25. **"delta-based" not operationally defined** (A4 MEDIUM). Prelude → frame-0 semantics.
26. **`\reannotate` underdocumented** (A1 MEDIUM, A4 MEDIUM). §5.9 is one sentence. `color=` required (E1113), other modifiables unclear.
27. **Annotation headroom reflow gotcha (R-32)** (A2 LOW). Per-scene max → all frames shift. Should be §13.
28. **`grid` env option** (A1 CRITICAL, A2 MEDIUM). Accepted by parser, silently dropped. Either document or remove from `VALID_OPTION_KEYS`.
29. **`id` value constraint `[a-z][a-z0-9-]*`** (A2 MEDIUM).
30. **Top 15 error codes missing from reference** (A2 HIGH). Scattered inline; no consolidated index.
31. **Smart-label env flags gotcha** (A2 LOW). `SCRIBA_DEBUG_LABELS`, `SCRIBA_LABEL_ENGINE` — already in §5.8 block-quote; consider promoting to §13.
32. **Stable + directed UserWarning** (A1 MEDIUM). Upside-down DAG.
33. **`global_optimize=true` is no-op** (A1 MEDIUM). Forward-compat flag.
34. **`\substory` accepts `id=`** (A1 LOW).
35. **Substory state persistence across boundary** (A4 MEDIUM).

### LOW — documentation niceties

36. **Legacy text aliases `\bf`, `\it`, `\tt`** (A2 LOW). Polygon compat.
37. **Size commands `\tiny`…`\Huge`** (A2 MEDIUM). 9 commands, brace + switch forms.
38. **Triple-dollar `$$$...$$$` math alias** (A2 LOW).
39. **Curly-quote typography** (A2 LOW).
40. **`\href` URL scheme fallback** (A2 LOW).
41. **`lstlisting` themes** (A2 LOW). `one-light`, `one-dark`, `github-light`, `github-dark`, `none`.
42. **`\hl` errors E1320/E1321 + `step{N}` form inconsistency** (A2 LOW). Ref says unlabeled steps can't be targeted; spec says `step{N}` form works. Resolve.
43. **CodePanel 1-indexed gotcha** (A2 LOW). Buried; should be §13.
44. **`width`/`height` dimension format not shown** (A4 LOW).
45. **Two "blue" state conflict** (A4 LOW). `current` #0072B2 vs `path` #2563eb.
46. **`print()` builtin goes to build log only** (A4 LOW).
47. **`layout="auto"` in code warning but not documented** (A1 LOW).

---

## Recommended Fix Order

### Tier 1 — must fix (factual errors, silent bugs)

Fix items **1–17, 28**. These are either wrong (hallucinations, bad counts, wrong hex) or they produce silent wrong-output for AI authors. Estimated: ~200 lines of additions/corrections.

### Tier 2 — high-value usability (AI cold-read success)

Fix items **18–27**. Adds: §0 render instructions, Dijkstra example, `\cursor` multi-target, nested `for` Starlark, graph layout decision guide, selector definition, node ID quoting rule, delta-based semantics, expanded `\reannotate`, R-32 reflow gotcha. Estimated: ~300 lines.

### Tier 3 — nice-to-have (polish, edge cases)

Fix items **29–47**. Error-code quick-ref index, env option constraint notes, size commands, legacy aliases, typography, small clarifications. Estimated: ~150 lines.

### Also — README integration

Add `## Using Scriba with an AI assistant` section pointing at `docs/SCRIBA-TEX-REFERENCE.md`.

---

## Overall Verdict

Reference is **structurally sound but factually drifted** — claim counts are wrong (`16 primitives` → 15; `12 inner commands` → 13 with `\hl`), hex colors were reverse-engineered from palette intent rather than CSS truth, and feature coverage has drifted behind 3 recent changes (GEP v2.0 graph flow controls; Plane2D segment/polygon ops; Tree mutation ops).

For AI cold-read: **ACCEPTABLE** for basic 1D-DP / BFS walkthroughs, **INSUFFICIENT** for Dijkstra-class tasks (graph+array composition, flow networks, traceback patterns).

After Tier 1 + Tier 2 fixes: will be **GOOD** for one-shot AI authoring across all 15 primitives.

**Total fix budget:** ~650 lines of additions + ~50 lines corrections. Target file size after fixes: ~1500–1600 lines (still well within single-file-reference scope).
