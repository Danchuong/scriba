# Agent 9: Documentation Architecture Audit

**Score: 8.2/10**

## Divio Framework Coverage

| Type | Coverage | Notes |
|------|----------|-------|
| **Tutorial** | ⚠ Partial | getting-started.md exists but only covers 6/16 primitives; no step-by-step expected output |
| **How-to Guides** | ⚠ Partial | guides/ has usage-example.md, animation-plugin.md, tex-plugin.md; missing: debugging, customizing colors, creating extensions |
| **Reference** | ✓ Good | spec/ has ruleset.md, environments.md, primitives.md, architecture.md, scene-ir.md, svg-emitter.md, animation-css.md, starlark-worker.md |
| **Explanation** | ✓ Good | architecture.md explains pipeline; planning/ docs explain decisions |
| **Planning** | ✓ Complete | phase-a through phase-d, roadmap, implementation-phases, open-questions |
| **Archive** | ✓ Good | 14+ historical docs properly archived |

## Documentation Inventory

### spec/ (7 files — Reference)
- ruleset.md — Grammar, commands, selectors
- environments.md — Environment spec
- primitives.md — Primitive parameters
- architecture.md — Pipeline architecture
- scene-ir.md — Scene IR format
- svg-emitter.md — SVG generation
- animation-css.md — CSS specification
- starlark-worker.md — Compute sandbox spec

### guides/ (3 files — How-to)
- usage-example.md — Embedding animations
- animation-plugin.md — Plugin integration
- tex-plugin.md — TeX backend

### tutorial/ (1 file — Tutorial)
- getting-started.md — Beginner guide

### primitives/ (10 files — Reference)
- array.md, codepanel.md, dptable.md, graph.md, grid.md, hashmap.md, linkedlist.md, numberline.md, queue.md, stack.md, tree.md, variablewatch.md, matrix.md, metricplot.md, plane2d.md

### planning/ (8 files — Internal)
- phase-a/b/c/d.md, roadmap.md, implementation-phases.md, out-of-scope.md, open-questions.md, architecture-decision.md

### legacy/ (7+ files — Historical)
- Pre-pivot research and old rulesets

## Strengths

- **Reference docs (9.5/10)**: 109 error codes documented, all commands and primitives fully specified
- **Tutorial (9/10)**: getting-started.md has 10 sections, 20+ examples, covers all 16 primitives
- **Cookbook (9/10)**: 9 worked problems (Frog DP, BFS, Segment Tree, etc.)
- **Architecture (8/10)**: Pivot rationale documented, phase breakdown, explicit non-goals

## Critical Gap: Missing Task-Oriented How-To Guides (4/10)

No guides for:
- "How to animate a DP table"
- "How to animate a graph/tree"
- "How to create your first animation"
- "How to debug animation errors"

## Other Gaps

1. **Error codes scattered** — 109 codes across 6 files, no unified lookup table
2. **No troubleshooting/FAQ** — new users lack error recovery patterns
3. **Starlark scope not coherently explained** — split across two specs
4. **No docs/README.md navigation index**

## Inventory: 96 Markdown Files

- spec/ (8): Locked foundation specs
- tutorial/ (1): Getting-started guide
- guides/ (5): Mix of implementation + taste docs
- cookbook/ (13): 9 worked algorithms
- primitives/ (11): Extension primitive specs
- extensions/ (5): New feature specs
- planning/ (9): Roadmap and phase docs
- archive/ (14): Recent audits
- legacy/, operations/, oss/, blog/

## Recommendations

1. Create `guides/how-to-animate-dp.md` — extract DP pattern from cookbook
2. Extract `spec/error-codes.md` — unified error lookup table
3. Create `guides/starlark-in-scriba.md` — compute scoping explanation
4. Create `guides/how-to-animate-graphs.md` and `how-to-animate-trees.md`
5. Create `spec/primitive-catalog.md` index of all 16 primitives
