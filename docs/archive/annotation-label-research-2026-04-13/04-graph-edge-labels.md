# 04 — Graph Edge Label Placement: Industry Survey

## Library Comparison

| Library | Auto-collision | Rotation | Background | Position control |
|---------|---------------|----------|------------|-----------------|
| **yFiles** | YES (integrated + generic) | Relative to edge | YES | Source/Center/Target + side |
| **Cytoscape.js** | NO (extension needed) | `autorotate` | `text-background-*` | Offset from midpoint |
| **GoJS** | NO | `OrientUpright` | Panel with fill | `segmentFraction` + `segmentOffset` |
| **JointJS** | NO | `keepGradient` + `ensureLegibility` | rect markup | `distance` + `offset` |
| **vis-network** | NO | NO | `font.background` | `font.align` top/bottom |
| **Dagre/ELK** | Partial (virtual node) | NO | NO | HEAD/CENTER/TAIL |
| **Graphviz** | `xlabel` post-pass | NO | NO | `label`/`headlabel`/`taillabel` |
| **mxGraph** | `mxEdgeLabelLayout` | NO | YES | x(-1..+1) + y(perpendicular) |

## yFiles: Gold Standard

Two strategies:
1. **Integrated labeling**: labels participate in layout computation — zero overlap guaranteed
2. **Generic labeling**: post-processing candidate evaluation across all labels simultaneously

`EdgeLabelPreferredPlacement`: position along edge (source/center/target),
side of edge (on/left/right), angle (absolute or relative to edge).

## 6 Key Techniques for Convergent Edges

### 1. Rotate Labels Along Edge Direction
Labels fan outward naturally when edges arrive from different angles.
Use "upright correction" to flip labels that would be upside-down.

### 2. Background Halo Behind Labels
White/semi-transparent rectangle prevents crossing edges from obscuring text.
Universal across all tools. Best: padding 3-5px, opacity 0.85-1.0, border-radius 2-3px.

### 3. Vary Label Position Along Edge Path
Instead of all labels at 50%, distribute: 30%, 40%, 50%, 60%, 70%.
Labels at lower fractions (closer to source) are in the "spread-out" zone.

### 4. Perpendicular Offset (Side Placement)
Push labels to left or right side of edge. Alternate sides for different edges.

### 5. Virtual Node (Label as Layout Participant)
Insert label as a dummy node at edge midpoint. Layout engine spaces it properly.
Used by Dagre and Graphviz `label` attribute.

### 6. Automatic Candidate Evaluation
Generate many candidate positions per label. Solve optimization problem for
global best assignment. Only yFiles does this at production quality.

## Recommendation for 4 Edges → Node D

1. Place labels at 25-35% of edge length (away from convergence zone)
2. Rotate labels to match edge angle with upright correction
3. Add white background pill (padding 4px, opacity 0.9, border-radius 2px)
4. If edges from A and B arrive at similar angles, use perpendicular offsets

## Sources

- yFiles label placement docs + edge label demo
- Cytoscape.js style docs, issues #714, #1374, #2872
- GoJS link labels intro
- JointJS link labels tutorial
- vis-network edges docs
- ELK edge label placement reference
- Graphviz xlabel/taillabel/headlabel docs
- mxGraph mxParallelEdgeLayout, mxEdgeLabelLayout
- Tom Sawyer: 3 Ways to Perfect Graph Edge Labels
