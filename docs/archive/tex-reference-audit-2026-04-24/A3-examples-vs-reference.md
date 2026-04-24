# A3 — Examples vs. Reference Pattern Coverage

**Date:** 2026-04-24
**Scope:** `.tex` files in `examples/` vs. `docs/SCRIBA-TEX-REFERENCE.md` (956 lines)
**Sampled:** 5 algorithms/dp, 5 algorithms/graph+misc+tree, 5 cses, 5 primitives, 3 demos, 2 editorials, all integration/smoke/quickstart fixtures

---

## Executive Summary

- **Plane2D severely under-documented.** Reference shows only `add_point` / `add_line`; examples use `add_segment`, `add_polygon`, inline `points=`/`lines=`/`segments=` shape params, plus `aspect=equal|"auto"` and per-primitive `width=`. None in §7.9.
- **Graph has two undocumented production params.** `orientation="LR"` (hierarchical L→R) and `tint_by_edge=true` used across `demos/mcmf.tex`, `demos/dinic.tex`. Absent from §7.4 and §12.
- **Multi-target `\cursor` used in >3 files but §5.10 shows only single-target.** `\cursor{h.cell, dp.cell}{1}` (sync two arrays) appears in `algorithms/dp/frog.tex`, `cses/necessary_roads.tex` — load-bearing for all dual-array DP walkthroughs.
- **`\substory` with `\recolor`/`\annotate` inside represented in only 1 integration test.** `primitives/substory.tex` and `algorithms/dp/interval_dp.tex` use inner `\annotate` with `arrow_from=` — §5.12 doesn't show this.
- **Starlark `for`-loop `\compute` building 2D DP tables is dominant idiom but §5.2 only mentions comprehensions in passing.** `test_reference_dptable.tex` nested `for` loops building full 2D `dp_vals` is canonical for 2D DP animations.

---

## Missing Patterns Table

| Frequency | Pattern | Example File(s) | Suggested Reference Section | Priority |
|---|---|---|---|---|
| 8+ files | `\cursor{a.cell, b.cell}{i}` — multi-target cursor syncing two primitives | `algorithms/dp/frog.tex`, `cses/necessary_roads.tex`, `cses/range_queries_copies.tex` | §5.10 — add multi-target example | **HIGH** |
| 6+ files | Nested `for` loops in `\compute` computing 2D DP arrays | `integration/test_reference_dptable.tex`, `editorials/knapsack_editorial.tex` | §5.2 — add 2D table construction example | **HIGH** |
| 4 files | `Plane2D` inline shape params `points=[…]`, `lines=[…]`, `segments=[…]` | `algorithms/misc/convex_hull_andrew.tex`, `algorithms/dp/convex_hull_trick.tex` | §7.9 — add inline batch params | **HIGH** |
| 4 files | `\apply{plane}{add_segment=[[x1,y1],[x2,y2]]}` | `algorithms/misc/convex_hull_andrew.tex`, `integration/test_plane2d_edges.tex` | §7.9 Operations | **HIGH** |
| 2 demos | `Graph` param `orientation="LR"` | `demos/mcmf.tex`, `demos/dinic.tex` | §7.4 — add param row | **MEDIUM** |
| 2 demos | `Graph` param `tint_by_edge=true` | `demos/mcmf.tex`, `demos/dinic.tex` | §7.4 — add param row | **MEDIUM** |
| 2 files | `Plane2D` `aspect=equal` / `"auto"` | `convex_hull_andrew.tex`, `convex_hull_trick.tex` | §7.9 — add `aspect` | **MEDIUM** |
| 2 files | `Plane2D` per-primitive `width=<px>` (distinct from env `width`) | `convex_hull_andrew.tex`, `convex_hull_trick.tex` | §7.9 — distinguish from §10 env width | **MEDIUM** |
| 1 file | `\apply{plane}{add_polygon=[[x,y],…]}` | `convex_hull_andrew.tex` | §7.9 Operations — polygon op | **LOW** (single use, rare) |
| 3+ files | `\reannotate{…}{color=path, arrow_from="…"}` chain — DP traceback bulk repaint | `algorithms/dp/frog.tex`, `frog_foreach.tex`, `editorials/knapsack_editorial.tex` | §12 — promote Traceback to own sub-block | **MEDIUM** |
| 3 files | `range(start, stop, step)` 3-arg form in Starlark | `cses/permutations.tex`, `integration/test_reference_dptable.tex` | §5.2 — clarify range signature | **LOW** |
| 4+ files | Starlark filtered comprehension `[i for i in range(n) if i % 2 == 0]` | `integration/test_reference_advanced.tex`, `cses/permutations.tex` | §5.2 — add filtered example | **MEDIUM** |
| 2 files | `\annotate` with `arrow_from=` AND `ephemeral=true` (transient recurrence marker) | `integration/test_reference_advanced.tex`, `algorithms/dp/interval_dp.tex` | §5.8 — note substory interaction | **LOW** |
| 3 files | `\substory` with inner `\annotate{…}{arrow_from=…}` | `algorithms/dp/interval_dp.tex`, `integration/test_reference_advanced.tex`, `fixtures/pass/23_a11y_widget.tex` | §5.12 — expand example | **MEDIUM** |

---

## Idioms Used Once — Do NOT Promote

- `add_region=` — not found in any example. Selector table §8 lists `.region[i]` but no example uses it. Dead weight.
- `aspect="auto"` — only in `convex_hull_trick.tex`; contrasts with `aspect=equal` in sibling file. Semantics unstable. Hold.

---

## Underweight Reference Sections

**§5.2 `\compute`** — currently only simple one-liners + passing mention of comprehensions/`def`. Add:
1. Filtered list comprehension (4+ files): `even_indices = [i for i in range(n) if i % 2 == 0]`
2. Nested `for` block building 2D DP table (integration tests, editorials): `test_reference_dptable.tex` prelude is canonical.

**§5.10 `\cursor`** — single-target only. Multi-target `\cursor{h.cell, dp.cell}{i}` used in every dual-array DP walkthrough. One-line example here prevents redundant `\recolor` pairs.

**§7.9 Plane2D** — Operations line lists `add_point` + `add_line` only. Three ops (`add_segment`, `add_polygon`, inline batch params) + two shape params (`aspect`, `width`) absent. `convex_hull_andrew.tex` + `convex_hull_trick.tex` authoritative.

**§7.4 Graph** — `orientation` + `tint_by_edge` in both MCMF demos. Flow-network layout controls. Deserve dedicated rows.

**§5.12 `\substory`** — reference example is a stub (shape + 1 step + narrate). Real usages (`interval_dp.tex`, `test_reference_advanced.tex`) include `\annotate{…}{arrow_from=…}` to trace sub-computations.

**§12 Common Patterns** — "Traceback with reannotate" compressed. Uses `\foreach` over `\compute`-bound path list + `\reannotate` chains → #1 pattern for DP answer-path highlighting (8+ files). Promote to named copy-ready block with 2D variant (`knapsack_editorial.tex`'s `dp.cell[r][c]` traceback).
