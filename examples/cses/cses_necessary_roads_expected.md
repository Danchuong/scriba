# CSES Necessary Roads: Expected Animation

## Overview

- **Frames:** 16 total
- **Primitives:** Graph (7 nodes, 8 edges), 2 Arrays (disc[] and low[], each size 7)
- **Visual flow:** DFS traversal with discovery/low value computation, back edge detection, bridge identification on backtrack

## Frame-by-Frame Description

### Frame 0 (Introduction)
- Graph: all nodes and edges in idle state
- disc[]: all cells show "-"
- low[]: all cells show "-"
- Narration introduces the bridge-finding problem and Tarjan's algorithm

### Frame 1 (Start DFS at node 1)
- g.node[1]: current (blue)
- disc[1] = 0, low[1] = 0, both cells current
- Narration: DFS begins at node 1

### Frame 2 (Visit node 2)
- g.node[1]: done (green), g.node[2]: current
- g.edge[(1,2)]: done (tree edge)
- disc[2] = 1, low[2] = 1

### Frame 3 (Visit node 3)
- g.node[2]: done, g.node[3]: current
- g.edge[(2,3)]: done (tree edge)
- disc[3] = 2, low[3] = 2

### Frame 4 (Back edge 3->1)
- g.edge[(3,1)]: current (yellow highlight for back edge)
- low[3] updated from 2 to 0, shown in good (sky blue)
- Narration explains back edge detection: node 3 can reach ancestor 1

### Frame 5 (Visit node 4)
- g.node[3]: done, g.node[4]: current
- g.edge[(3,4)]: done (tree edge), g.edge[(3,1)]: dim (back edge faded)
- disc[4] = 3, low[4] = 3

### Frame 6 (Visit node 5)
- g.node[4]: done, g.node[5]: current
- g.edge[(4,5)]: done (tree edge)
- disc[5] = 4, low[5] = 4

### Frame 7 (Visit node 6)
- g.node[5]: done, g.node[6]: current
- g.edge[(5,6)]: done
- disc[6] = 5, low[6] = 5

### Frame 8 (Visit node 7)
- g.node[6]: done, g.node[7]: current
- g.edge[(6,7)]: done
- disc[7] = 6, low[7] = 6

### Frame 9 (Back edge 7->5)
- g.edge[(7,5)]: current (back edge detected)
- low[7] updated from 6 to 4, shown in good (sky blue)
- Narration: cycle 5-6-7-5 protects those edges from being bridges

### Frame 10 (Backtrack 7->6)
- g.node[7]: done, g.edge[(7,5)]: dim
- low[6] updated to 4
- Bridge check: low[7]=4 > disc[6]=5? No -- edge 6-7 is safe

### Frame 11 (Backtrack 6->5)
- low[5] updated to 4
- Bridge check: low[6]=4 > disc[5]=4? No -- edge 5-6 is safe

### Frame 12 (Backtrack 5->4 -- bridge found)
- low[4] stays 3
- Bridge check: low[5]=4 > disc[4]=3? YES
- g.edge[(4,5)]: error (red) -- marked as bridge
- Narration: no back edge from {5,6,7} reaches above node 4

### Frame 13 (Backtrack 4->3 -- bridge found)
- Bridge check: low[4]=3 > disc[3]=2? YES
- g.edge[(3,4)]: error (red) -- marked as bridge
- Narration: node 4 has no back edges, its subtree is isolated

### Frame 14 (Backtrack to root)
- low[2] = 0, low[1] = 0
- Edge 2-3 and 1-2 both pass bridge check (not bridges)
- DFS complete

### Frame 15 (Final result)
- Cycle {1,2,3}: nodes and edges in good (sky blue)
- Cycle {5,6,7}: nodes and edges in good (sky blue)
- Node 4: error (red) -- articulation point
- Edges (3,4) and (4,5): error (red) -- bridges
- disc[] and low[] arrays: all good
- Narration summarizes: 2 bridges, O(n + m) complexity

## Visual Characteristics

- Tree edges colored done (green) as DFS progresses forward
- Back edges flash current (yellow) when detected, then dim
- low[] cells flash good (sky blue) when updated by back edges
- Bridge edges colored error (red) on backtrack when condition met
- Final frame shows clear biconnected component structure: two green/sky-blue cycles connected by red bridge edges through a red articulation point
- The two arrays provide a running log of the algorithm state at each DFS step
