# Annotation Label Research — 2026-04-13

Research into annotation label placement, collision avoidance, and arrow-label
association for Scriba's `\annotate` system. Constraint: **no text truncation
or hiding** — all author-specified content must display fully.

## Files

| File | Topic |
|------|-------|
| `01-textpath-techniques.md` | SVG textPath for text along curves |
| `02-leader-lines.md` | Leader line / callout placement patterns |
| `03-layout-algorithms.md` | Force-directed, greedy, simulated annealing |
| `04-graph-edge-labels.md` | Industry survey: Cytoscape, vis.js, yFiles, GoJS, etc. |
| `05-educational-annotations.md` | Pedagogical patterns: VisuAlgo, Red Blob Games, Manim |
| `06-synthesis.md` | Combined strategy recommendation |

### Interactive Demos (open in browser)

| File | What it shows |
|------|---------------|
| `demo_smart_labels.html` | **Proposed solution**: pills, halo, nudge, leader lines, rotation, hover isolation |
| `demo_annotation_audit.html` | Current vs proposed: Array, DPTable 2D, Graph, Tree, Queue |
| `demo_annotation_complex.html` | Stress tests: 5-arrow knapsack, interval DP, Dijkstra, BFS tree, LIS traceback |
| `demo_prototype_strategies.html` | 6 alternative strategies compared side-by-side |

## Key Constraint

Authors decide what text to show. The rendering engine must display ALL label
content fully — no truncation, no hiding, no content removal. Solutions must
be purely about **smart positioning** and **visual association**.
