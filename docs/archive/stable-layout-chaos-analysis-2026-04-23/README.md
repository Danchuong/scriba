# Stable Layout Chaos Analysis — 2026-04-23

**Question:** "Tại sao layout stable lại trông có vẻ hỗn loạn chẳng có quy tắc nào vậy?"
(Why does `layout="stable"` look chaotic with no apparent rules?)

## Documents

| # | File | Scope |
|---|------|-------|
| 00 | `00-synthesis.md` | **Start here** — cross-doc synthesis + bottom line |
| 01 | `01-algorithm-dive.md` | How `graph_layout_stable.py` actually works — SA, constants, convergence, determinism |
| 02 | `02-empirical-evidence.md` | Measured positions across 4 topologies × 3 seeds; quantified topology violations |
| 03 | `03-stable-vs-hierarchical.md` | Side-by-side comparison with the Sugiyama implementation |
| 04 | `04-rca-and-recommendations.md` | Root causes, fix options, proposed default-switch migration |

## TL;DR

Stable-SA is topology-blind — no edge direction, layers, or source/sink
concept. 200 iterations from random init cannot find a hierarchical-looking
layout for a DAG. **47% avg parent-above-child violation** measured across 4
topologies × 3 seeds. Hierarchical scores 0. Fix: add `layout="auto"` that
routes DAGs to hierarchical, cyclic to FR.

Sources analyzed:
- `scriba/animation/primitives/graph_layout_stable.py`
- `scriba/animation/primitives/graph_layout_hierarchical.py`
- `scriba/animation/primitives/graph.py` (dispatcher)

Related prior archives:
- `arrow-routing-research-2026-04-22/`
- `graph-edge-pill-*` (three optimization passes)
