# Animation V2 — Implementation Plan

**Date:** 2026-04-12
**Status:** Complete (G2 deferred to V3)
**Depends on:** Animation V1 (differ.py, emitter.py `<script>`, CSS transitions)

---

## Problem Statement

Animation V1 shipped with basic CSS transitions + WAAPI for recolor/value_change/element_add/remove. The research agents found these gaps:

| # | Gap | Severity | Effort |
|---|-----|----------|--------|
| G1 | MetricPlot has zero animation support (no `data-target`) | HIGH | M |
| G2 | Only Array + DPTable render annotations (arrows) — 9 other primitives ignore `_annotations` | HIGH | XL (deferred to V3) |
| G3 | Missing `examples/primitives/dptable.tex` demo | HIGH | S |
| G4 | 5 CSES files lack cursor + annotations (elevator_rides, planets_queries2, houses_schools, necessary_roads, range_queries_copies) | HIGH | L |
| G5 | 3 DP algorithm files lack annotation arrows (convex_hull_trick, interval_dp, dp_optimization) | MED | M |
| G6 | Persistent segtree examples too sparse — no shared-vs-new node distinction | MED | M |
| G7 | KMP phase 2 missing cursor | LOW | S |
| G8 | BST operations missing rotation visualization | LOW | M |

**Scope:** G1, G3-G7 (G2 deferred to V3 — requires implementing full arrow rendering for each primitive's coordinate system. G8 deferred — rotation requires tree layout recalculation mid-step).

---

## Architecture

### What exists (V1)

```
differ.py                   computes TransitionManifest between FrameData pairs
emitter.py                  wires manifests into JS frames as `tr` field
scriba-scene-primitives.css CSS transitions on [data-target] > rect/circle/line/text
<script> in emitter.py      animateTransition() + snapToFrame() runtime (~1.1KB)
```

### What V2 adds

1. **`data-annotation` on all primitives that support annotations** (G2)
   - Currently only `array.py` and `dptable.py` emit `data-annotation="target-arrow_from"` on annotation `<g>` elements.
   - Need to add the same pattern to: `graph.py`, `tree.py`, `grid.py`, `numberline.py`, `plane2d.py`, `linkedlist.py`, `hashmap.py`, `queue.py`, `variablewatch.py`.
   - The differ already handles annotation transitions — the JS runtime already queries `[data-annotation="..."]`. Only the SVG emission is missing.

2. **`data-target` on MetricPlot elements** (G1)
   - MetricPlot currently emits no `data-target` attributes. The whole SVG is re-rendered each frame.
   - Strategy: MetricPlot is fundamentally different — it's a compile-time chart where the entire SVG changes each step (new polyline points, new markers). Full CSS morphing is impractical.
   - Instead: add `data-target="{name}"` on the root `<g>` so the differ can detect "metricplot changed" and the JS runtime can apply a crossfade (opacity 0→1) instead of an instant snap.
   - This gives a smooth visual transition without trying to morph polyline coordinates.

3. **Content improvements** (G3-G7)
   - New/improved .tex files with richer step-by-step animations.

---

## Waves

### Wave 1 — Primitive Infrastructure (2 agents, parallel)

#### Agent 1A: `data-annotation` on 9 primitives

**Files to modify:**
- `scriba/animation/primitives/graph.py`
- `scriba/animation/primitives/tree.py`
- `scriba/animation/primitives/grid.py`
- `scriba/animation/primitives/numberline.py`
- `scriba/animation/primitives/plane2d.py`
- `scriba/animation/primitives/linkedlist.py`
- `scriba/animation/primitives/hashmap.py`
- `scriba/animation/primitives/queue.py`
- `scriba/animation/primitives/variablewatch.py`

**What to do:**

In each primitive's annotation rendering method, find where it creates the `<g>` element wrapping the annotation and add `data-annotation="{ann_key}"` where:
```python
ann_key = f"{target}-{arrow_from}" if arrow_from else f"{target}-solo"
```

This matches the pattern already used in `array.py:503` and `dptable.py:474`.

**Reference implementation** (from `array.py:498-503`):
```python
# In the annotation rendering loop:
arrow_from = ann.get("arrow_from", "")
ann_key = f"{target}-{arrow_from}" if arrow_from else f"{target}-solo"
# Then on the <g> element:
f' data-annotation="{_escape_xml(ann_key)}"'
```

**Acceptance criteria:**
- All 11 primitives that support annotations emit `data-annotation`
- `grep -r 'data-annotation' scriba/animation/primitives/ | wc -l` >= 11
- Existing tests still pass
- New test: `tests/animation/test_annotation_data_attr.py` — render a Graph with an annotation, assert `data-annotation` appears in SVG output

#### Agent 1B: MetricPlot crossfade support

**Files to modify:**
- `scriba/animation/primitives/metricplot.py` (line 364)
- `scriba/animation/emitter.py` (JS runtime, `animateTransition()`)

**What to do:**

1. In `metricplot.py:emit_svg()`, add `data-target="{self.name}"` to the root `<g>`:
```python
# Line 364, change:
parts.append(
    f'<g data-primitive="metricplot" data-shape="{html.escape(self.name)}"'
    f' data-scriba-series="{html.escape(series_names_str)}">'
)
# To:
parts.append(
    f'<g data-primitive="metricplot" data-shape="{html.escape(self.name)}"'
    f' data-target="{html.escape(self.name)}"'
    f' data-scriba-series="{html.escape(series_names_str)}">'
)
```

2. In the JS `animateTransition()` function inside `emitter.py`, the existing code handles recolor (CSS class swap) and element_add/remove (WAAPI opacity). MetricPlot changes show up as value_change or recolor on the shape-level target. No JS change needed — the CSS transition on `[data-target]` elements already covers opacity, and the differ will detect state changes.

3. Add CSS transition for metricplot in `scriba-scene-primitives.css`:
```css
[data-primitive="metricplot"] {
    transition: opacity 200ms ease-out;
}
```

**Acceptance criteria:**
- `grep 'data-target' scriba/animation/primitives/metricplot.py` returns a match
- MetricPlot SVG has `data-target` attribute in rendered HTML
- Existing metricplot tests still pass

---

### Wave 2 — DPTable Demo + DP Annotation Improvements (2 agents, parallel)

#### Agent 2A: DPTable primitive demo

**File to create:** `examples/primitives/dptable.tex`

**Content requirements:**
- Declare a 1D DPTable (size 6) and a 2D DPTable (4x4)
- Step 1: Show empty tables with labels
- Step 2: Fill base cases with `\apply`, mark `state=done`
- Step 3: Show transition with `\annotate` (arrow from source cell to target cell, label="+cost")
- Step 4: Fill more cells, show `\reannotate` to highlight optimal path
- Step 5: Complete the table, show final path with `state=path`
- Use `\narrate` to explain each step
- ~20 lines, 5-6 steps

**Reference:** Follow the pattern in `examples/primitives/array.tex` for structure, `docs/tutorial/getting-started.md` section 5 "Applying Values" for DP patterns.

**Acceptance criteria:**
- File compiles with `examples/build.sh` without errors
- Uses DPTable primitive with both 1D and 2D addressing
- Has `\annotate` and `\apply` commands
- At least 5 `\step` commands

#### Agent 2B: Retrofit DP algorithm files with annotations

**Files to modify:**
- `examples/algorithms/dp/convex_hull_trick.tex`
- `examples/algorithms/dp/interval_dp.tex`
- `examples/algorithms/dp/dp_optimization.tex`

**What to do for each file:**

Read the existing file, understand the algorithm, then add `\annotate` commands showing where DP values come from. Pattern:

```tex
% Before filling dp[i], show candidates:
\annotate{dp.cell[i]}{label="+cost1", arrow_from="dp.cell[j]", color=info}
\annotate{dp.cell[i]}{label="+cost2", arrow_from="dp.cell[k]", color=good}
\narrate{Two candidates for $dp[i]$: from $j$ (cost1) or $k$ (cost2).}

% Next step: commit the winner
\reannotate{dp.cell[i]}{color=path, arrow_from="dp.cell[k]"}
\apply{dp.cell[i]}{value=result}
\recolor{dp.cell[i]}{state=done}
```

**Constraints:**
- Do NOT increase total step count by more than 3 per file
- Add annotations to existing steps where DP transitions happen
- Do NOT change the algorithm logic or shape declarations

**Acceptance criteria:**
- Each file has at least 3 `\annotate` commands after modification
- Each file still compiles without errors
- No steps removed or algorithm logic changed

---

### Wave 3 — CSES Editorial Enrichment (3 agents, parallel)

#### Agent 3A: elevator_rides.tex + houses_schools.tex

**Files to modify:**
- `examples/cses/elevator_rides.tex`
- `examples/cses/houses_schools.tex`

**For elevator_rides.tex:**
- Add `\cursor` to track bitmask iteration (which mask is being evaluated)
- Add `\annotate` showing which previous masks contribute to current DP state
- Add `state=dim` for masks already processed

**For houses_schools.tex:**
- Add `\cursor` to track which (house, school) pair is being evaluated
- Add `\annotate` arrows from `dp[j-1][i']` to `dp[j][i]` showing cost function
- Dim completed rows with `state=dim`

**Acceptance criteria:**
- Each file has at least 2 `\cursor` commands and 3 `\annotate` commands
- Each file still compiles without errors

#### Agent 3B: planets_queries2.tex + necessary_roads.tex

**Files to modify:**
- `examples/cses/planets_queries2.tex`
- `examples/cses/necessary_roads.tex`

**For planets_queries2.tex:**
- Add `\cursor` on the binary lifting table construction phase
- Add `\annotate` showing `up[k][v] = up[k-1][up[k-1][v]]` lifting relation
- Highlight query path with `state=path`

**For necessary_roads.tex:**
- Add `\cursor` tracking DFS traversal order
- Add `\annotate` on bridge edges showing low-link comparison
- Mark bridges with `state=error` (critical/important)

**Acceptance criteria:**
- Each file has at least 2 `\cursor` commands and 2 `\annotate` commands
- Each file still compiles without errors

#### Agent 3C: range_queries_copies.tex + KMP phase 2

**Files to modify:**
- `examples/cses/range_queries_copies.tex`
- `examples/algorithms/string/kmp.tex`

**For range_queries_copies.tex:**
- Add `\cursor` tracking which version of persistent segtree is being queried
- Use `state=dim` for shared (old) nodes vs `state=current` for new nodes on copy-on-write
- Add `\annotate` showing which nodes are "shared pointers" vs "new copies"

**For kmp.tex (phase 2 gap):**
- The file currently has cursor usage in phase 1 (failure array construction)
- Add `\cursor` in phase 2 (text scanning): track both text pointer `i` and pattern pointer `j`
- When mismatch occurs, show `\annotate` with `arrow_from` pointing to `fail[j-1]` showing where pattern pointer jumps

**Acceptance criteria:**
- range_queries_copies.tex has `state=dim` for shared nodes
- kmp.tex has `\cursor` in both phases
- Both files compile without errors

---

### Wave 4 — Persistent Segtree Enrichment (1 agent)

#### Agent 4A: Persistent segtree visualization

**Files to modify:**
- `examples/algorithms/tree/persistent_segtree.tex`

**What to do:**
- Current file has only ~12 steps and doesn't distinguish shared vs new nodes
- Add steps showing copy-on-write:
  1. Show original tree with all nodes `state=done`
  2. Update triggers: highlight path from root to leaf with `state=current`
  3. New nodes created along path: use `add_node` structural mutation
  4. Old shared nodes: `state=dim`
  5. New version root: `state=good`
- Add `\annotate` on shared nodes with `label="shared"`, `color=muted`
- Add `\narrate` explaining version pointers

**Constraints:**
- Keep within 20 steps total
- Use Tree primitive's `add_node` for new version nodes
- Use existing `kind="segtree"` parameter

**Acceptance criteria:**
- File has visual distinction between shared and new nodes
- Uses `add_node` for at least 2 copy-on-write operations
- Has at least 3 `\annotate` commands
- Compiles without errors

---

## Wave Dependencies

```
Wave 1 (infra) ──┐
                  ├── Wave 2 (DPTable demo + DP annotations)
                  ├── Wave 3 (CSES enrichment) ─── parallel, 3 agents
                  └── Wave 4 (persistent segtree)
```

Wave 1 must complete first because:
- Wave 2B needs `data-annotation` on primitives to actually animate the new annotations
- Wave 3 benefits from MetricPlot crossfade (weird_algorithm.tex uses MetricPlot)

Waves 2, 3, 4 can all run in parallel after Wave 1.

---

## Summary

| Wave | Agents | Work | Files Modified | Files Created |
|------|--------|------|----------------|---------------|
| 1 | 2 | Primitive infra (data-annotation, MetricPlot) | 11 .py, 1 .css | 1 test |
| 2 | 2 | DPTable demo + DP annotation retrofit | 3 .tex | 1 .tex |
| 3 | 3 | CSES editorial enrichment | 5 .tex | 0 |
| 4 | 1 | Persistent segtree enrichment | 1 .tex | 0 |
| **Total** | **8** | | **20 files** | **2 files** |

**Estimated agent count:** 8 agents across 2 sequential rounds (Wave 1, then Waves 2+3+4 parallel).
