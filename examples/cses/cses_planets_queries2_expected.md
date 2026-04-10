# CSES Planets Queries II: Expected Animation

## Overview

- **Frames:** 20 total
- **Primitives:** Graph (6 nodes, 2 directed cycles), DPTable (3x6 binary lifting table), Array (answer display)
- **Example graph:** Two 3-cycles: 1->2->3->1 and 4->5->6->4
- **Queries demonstrated:** (1,3) = 2, (4,2) = -1, (1,1) = 0

## Frame-by-Frame Description

### Frame 0 -- Graph Introduction
- Graph displayed with all 6 nodes and 6 directed edges, all idle
- DPTable and Answer array visible but empty
- Narration: introduces functional graph concept (outdegree = 1, rho-shaped components)

### Frame 1 -- Component 1 Highlight
- Nodes 1, 2, 3 and edges (1,2), (2,3), (3,1) recolored to `current` (blue)
- Narration: identifies first cycle of length 3

### Frame 2 -- Component 2 Highlight
- Component 1 returns to idle
- Nodes 4, 5, 6 and edges (4,5), (5,6), (6,4) recolored to `current`
- Narration: identifies second cycle, notes cross-component unreachability

### Frame 3 -- Table Setup
- All graph nodes back to idle
- Narration: introduces binary lifting table structure (rows = k, cols = nodes)

### Frame 4 -- Fill lift[0] (1-step)
- DPTable row 0 filled: [2, 3, 1, 5, 6, 4]
- Row 0 cells marked `current`
- Narration: explains lift[0][i] = t[i], the direct teleport destination

### Frame 5 -- Fill lift[1] (2-step)
- Row 0 cells become `done`
- Row 1 filled: [3, 1, 2, 6, 4, 5]
- Row 1 cells marked `current`
- Narration: explains double-jump formula lift[1][i] = lift[0][lift[0][i]]

### Frame 6 -- Fill lift[2] (4-step)
- Row 1 cells become `done`
- Row 2 filled: [2, 3, 1, 5, 6, 4]
- Row 2 cells marked `current`
- Narration: 4 mod 3 = 1, so lift[2] matches lift[0] due to cycle length

### Frame 7 -- Table Complete
- All DPTable cells become `done`
- Narration: table complete, ready for queries

### Frame 8 -- Query 1 Setup: (1, 3)
- Node 1 recolored `current`, node 3 highlighted (ephemeral)
- Answer shows "?"
- Narration: introduces query, both nodes in same component

### Frame 9 -- Query 1 Step 1
- Edge (1,2) becomes `current`, node 2 becomes `done`
- Node 3 still highlighted
- Narration: first teleportation, 1 -> 2

### Frame 10 -- Query 1 Step 2
- Edge (2,3) becomes `current`, edge (1,2) becomes `done`
- Node 1 becomes `done`, node 3 becomes `good` (sky blue)
- Narration: second teleportation, 2 -> 3, target reached, distance = 2

### Frame 11 -- Query 1 Answer
- Answer updates to "2", marked `good`
- Narration: confirms answer = 2

### Frame 12 -- Query 2 Setup: (4, 2)
- Graph reset to idle
- Node 4 recolored `current`, node 2 highlighted
- Answer reset to "?"
- Narration: cross-component query

### Frame 13 -- Query 2 Rejection
- Nodes 4 and 2 recolored `error` (red)
- All edges dimmed
- Narration: different components, impossible to reach

### Frame 14 -- Query 2 Answer
- Answer updates to "-1", marked `error`
- Narration: confirms answer = -1

### Frame 15 -- Bonus Query Setup: (1, 1)
- Graph reset to idle
- Node 1 recolored `current` and highlighted
- Answer reset to "?"
- Narration: same source and target

### Frame 16 -- Bonus Query Answer
- Answer updates to "0", marked `good`
- Node 1 marked `good`
- Narration: zero teleportations needed, already at destination

### Frame 17 -- Tail Node Discussion
- Graph and table reset to idle
- Narration: explains how tail nodes (trees hanging off cycles) are handled with depth computation

### Frame 18 -- Summary
- All nodes and edges marked `good` (sky blue)
- Narration: summarizes the full algorithm -- binary lifting + cycle detection, O((n+q) log n) total

## Visual Characteristics

- **Graph** uses stable layout with directed edges showing the two separate 3-cycles
- **DPTable** shows the binary lifting table filling row by row (k=0,1,2)
- **Color progression:**
  - `idle` (gray) -- default state
  - `current` (blue) -- active node or being processed
  - `done` (green) -- already visited
  - `good` (sky blue) -- answer found / success
  - `error` (red) -- impossible / unreachable
  - `dim` (faded) -- irrelevant edges
- **highlight** (ephemeral yellow) marks the target node during query walkthroughs
- The animation demonstrates three distinct query types: same-cycle reachable, cross-component unreachable, and trivial self-query
