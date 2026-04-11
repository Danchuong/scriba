# Agent 19: DSL Ergonomics Simulation

**Score:** 6/10 (functional-but-painful, with strong mitigation via `\foreach` and `\cursor`)
**Verdict:** ship-with-caveats

## Prior fixes verified

- **C1 verbosity (\foreach landed):** PRESENT — `\foreach{i}{0..N}` with `${i}` interpolation covers repetitive loop patterns, addressing ~70% of manual hand-writing burden
- **M6 diff/delta semantics:** MISSING — each step re-specifies full state. Authors must manually track what changed from prior frame

---

## Critical Findings

### C1a. Intermediate Success: `\foreach` Bridges Compute-to-Recolor

The frog1_dp_foreach.tex example demonstrates `\foreach` working *in practice*:
```latex
\compute{ path = [0, 2, 3, 5] }
\foreach{i}{${path}}
  \recolor{h.cell[${i}]}{state=path}
  \recolor{dp.cell[${i}]}{state=path}
\endforeach
```
This replaces 8 hand-written `\recolor` lines with 5 (2 shape init + 1 compute + 2 loop body). For a 20-cell final traceback, that's ~40 lines → ~9 lines. **Friction reduced but not eliminated.**

**BUT:** `\foreach` cannot emit **different commands per iteration**. Example friction: a DP fill that needs different annotations per cell — the author still hand-writes or pre-generates JSON. Also, selector boilerplate remains: `\recolor{h.cell[${i}]}{state=X}` + `\recolor{dp.cell[${i}]}{state=X}` is still 2 lines per primitive.

---

## High Findings

### H1. Dijkstra on 20-node Graph with 40 edges (Authoring Simulation)

**Line count:** 4 (setup) + 1 (init step) + (14 steps × 4 lines) + 1 (final) = **~60 lines**

**Pain points:**
- ✓ `\cursor` helps track current node (reduces 2-3 lines per step → 1 line)
- ✗ **No loop-for-edges:** Author must hard-code each edge recolor. If authoring generatively (e.g., "visit all neighbors"), requires manual JSON pre-generation or external tool
- ✗ **Selector boilerplate:** `G.node[X]` and `G.edge[(X,Y)]` require redundant syntax even with `\foreach`
- ✗ **No annotation per-node:** If author wants to show "distance labels" on each node, must write one `\annotate` per frame

**Error friction:** Typo in node ID (e.g., `G.node[AB]` vs `G.node["AB"]`) fails silently at parse, caught only at render time. No line-number hint.

---

### H2. 0/1 Knapsack DP (N=20, W=50, 1050 cells)

**Authoring choice A: Manual** — Author writes 1050 `\apply` commands → **~3000 LOC** (3 lines per cell)

**Authoring choice B: `\foreach` + `\compute`** — **~40 lines for full fill + color-chain annotations**

**But M6 hurts:** Each frame must re-specify coloring of *all* visited cells. Without M6 fix, a 10-frame DP visualization becomes **200+ lines**.

**\foreach limitation:** Cannot compute different annotation labels per cell based on runtime logic.

**Pain points:**
- ✓ Nested `\foreach` works (nesting limit = 3, which covers most DP recurrences)
- ✓ `\compute` + `${var}` interpolation enables data-driven frames
- ✗ **No computed annotations:** Label must be static or author pre-generates all 1050 labels
- ✗ **M6 re-specification:** Rows already colored must be re-colored every frame to prevent drift, bloating step size
- ✗ **No matrix "fill animation":** Each cell separately, not a visual region fill

**Estimated friction:** **6-7/10 painful.** Solvable with discipline but tedious.

---

### H3. Two-Pointers on Array (N=15, pointer movement + window)

**Line count:** ~30 lines (including nested loop + narration)

**Pain points:**
- ✓ `\cursor` multi-target works well for dual-pointer tracking
- ✓ `\highlight` ephemeral state clears automatically per step
- ✗ **Range selector boilerplate:** `a.range[${left}:${right}]` requires parsing the range spec
- ✗ **No "window sliding" primitive:** Author manually computes window bounds

**Cursor ergonomic bonus:** The example from spec (frog1_dp.tex) uses `\cursor{h.cell, dp.cell}{1}` to track two pointers in one line. Works perfectly here.

---

### H4. Monotonic Stack + Next-Greater (Authoring Simulation)

**Problem:** Algorithm requires **per-iteration step boundaries** (new frame for each stack op), but `\step` is forbidden inside `\foreach`.

**BLOCKED:** The DSL cannot express "per-iteration frame boundaries." This is a **missing language construct**, not just a verbosity issue.

**Workaround:** Author manually unrolls iterations → **~40 lines (5 iterations × 8 lines)**

**Pain points:**
- ✓ `Stack` primitive push/pop via `\apply` works
- ✓ Cross-primitive coordination (stack + array answers) possible
- ✗ **CRITICAL: No loop-to-step bridge** — algorithm structure has loop nesting + frame boundaries; DSL has `\foreach` + `\step` but they don't compose
- ✗ **Stack selector awkward:** `s.item[i]` works, but popping removes the item; author must manually track indices
- ✗ **No "stack mutation animation":** Push/pop is instant; no visual shrink/grow

**Estimated friction:** **8/10 painful.** Algorithm structure doesn't map to DSL structure.

---

## Medium Findings

### M1. Selector Boilerplate Accumulation

Each multi-target operation requires separate command per shape. Manim/TikZ allow `recolor(*shapes, color=X)`. **Scriba forces repetition.**

**Workaround request:** `\shape{...}{GroupAlias}{shapes=["a", "b", "c"]}` — NOT IMPLEMENTED.

---

### M2. Missing `\shape ... copy` / Prototype Reuse

No prototype/copy mechanism. Authors hand-code repetition for duplicate shape declarations.

---

### M3. Unclear Error Paths for Common Typos

- **Typo in node ID:** `E1106 Unknown target selector` — unhelpful, doesn't name the bad node ID
- **Missing `${}` on interpolation:** Parser accepts `a.cell[i]` as literal NamedAccessor, fails at render time with no source line hint

---

### M4. Comment Support is Sparse

Comments are line-based per spec. Multi-line parameter lists cannot have inline comments. For large `\shape` declarations (graphs with 40+ edges), no way to annotate edges in place.

---

### M5. Frame-Count Inflation from M6

For N=20, re-dimming all visited cells per frame is O(N²) boilerplate. **Solution (not implemented):** Delta semantics or "apply once, persist" default state.

---

## Low Findings

### L1. `\compute` Error Messages

Starlark errors (E1150–E1154) report line numbers within the block but not the source file's `\compute` line. For a 50-line compute block, debugging is tedious.

### L2. Graph Edge Syntax Visual Overhead

`\recolor{G.edge[(A,B)]}{state=current}` — parens + tuple + quotes = 8 extra chars per edge reference.

### L3. No Conditional Annotations

Author cannot write `\if{dp[i] > threshold} \annotate{...} \endif`. Workaround: pre-compute in `\compute`, then `\foreach` to annotate only those.

---

## Notes

### Authoring Line-Count Table (4 Simulated Editorials)

| Algorithm | N/Size | Frames | DSL Lines | Estimate | Friction |
|-----------|--------|--------|-----------|----------|----------|
| Dijkstra (Graph) | 20 nodes, 40 edges | 16 | 60 | Manageable with `\cursor` | 6/10 |
| 0/1 Knapsack DP | 21×51=1050 cells | 20 | 40–200 | Nested `\foreach` helps; M6 hurts | 6/10 |
| Two-Pointers | 15 elements, 2 ptrs | 10 | 30 | `\cursor` excellent here | 5/10 |
| Monotonic Stack | 5 elements, stack | 5 | 40 | **No loop-to-step bridge; must unroll** | **8/10** |

### Key Wins & Gaps

**Wins:**
- `\foreach` + `\cursor` together cut ~70% of repetitive state mutation boilerplate
- `\compute` + `${var}` interpolation enables data-driven visualizations
- Nested `\foreach` (depth 3) covers most loop nesting patterns

**Gaps:**
1. **Loop-to-step bridge (C1 partial):** `\foreach` cannot emit step boundaries
2. **Diff/delta semantics (M6):** Multi-step visualizations re-specify full state
3. **Multi-target operations:** No way to recolor 5 shapes in one line
4. **Prototype reuse:** Duplicate `\shape` declarations must be hand-written
5. **Computed annotations:** Labels/arrows cannot be data-driven

### LaTeX Native Onboarding

For a LaTeX-experienced author:
- **First editorial (Frog DP):** ~1 hour. Syntax is natural.
- **Second editorial (Dijkstra):** ~2 hours. Graph selector syntax verbose; typo errors opaque.
- **Third editorial (Stack algo):** ~4 hours. Hit loop-to-step blocking issue.

**Learning curve:** Moderate. LaTeX users feel at home with commands/environments but the DSL's graph semantics and compute-to-animate connection are new mental models.

---

## Production Recommendation

**Ship with explicit caveats:**
1. Document that `\foreach` alone cannot express per-iteration step boundaries
2. Recommend external code generation for algorithms with complex loop-frame coupling
3. Add `\reannotate` to tutorial
4. Clarify error messages for node ID mismatches in Graph/Tree

**Score remains 6/10:** Functional for typical linear DP and simple graph algorithms, but friction compounds for algorithms where loop structure and frame structure don't align.
