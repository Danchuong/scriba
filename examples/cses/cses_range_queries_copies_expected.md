# CSES Range Queries and Copies: Expected Animation

## Overview

- **Frames:** 18 total
- **Primitives:** Array (current array state, size 4), Tree (segment tree, segtree kind with show_sum), Array (version tracker, size 1)
- **Example:** n=4, array=[1, 3, 2, 5]
- **Operations demonstrated:** build, range query, point update with path copying, copy (new version), second update, final query

## Frame-by-Frame Description

### Frame 0 -- Build
- Segment tree displayed with leaves [1, 3, 2, 5] and internal sums computed
- Array shows [1, 3, 2, 5]
- Version info shows 0
- Narration: introduces the initial segment tree for Version 0

### Frame 1 -- V0 Complete
- Root [0,3], [0,1], [2,3] recolored to `done` (green)
- Narration: summarizes node count and sums (root=11, left=4, right=7)

### Frame 2 -- Query sum(0,3) Full Coverage
- Root [0,3] highlighted
- Narration: full coverage returns sum=11 immediately, no recursion

### Frame 3 -- Query sum(1,2) Start
- Root highlighted, all nodes reset to idle
- Narration: partial overlap, must recurse into both children

### Frame 4 -- Query sum(1,2) Recurse
- Root dimmed, [0,1] and [2,3] highlighted
- Narration: neither child fully inside, recurse deeper

### Frame 5 -- Query sum(1,2) Leaves
- [0,0] and [3,3] marked `done` (outside range, skipped)
- [1,1] and [2,2] marked `good` (inside range, taken)
- [0,1] and [2,3] dimmed
- Narration: answer = 3 + 2 = 5

### Frame 6 -- Introduce Update
- All nodes reset to idle
- Narration: explains path copying concept -- update a[1]=7 creates new nodes, old nodes preserved

### Frame 7 -- Identify Path
- Leaf [1,1] highlighted and marked `current`
- Narration: path is [0,3] -> [0,1] -> [1,1], 3 new nodes for V1

### Frame 8 -- Path Copying Visualization
- Path nodes [0,3], [0,1], [1,1] marked `current` (blue) -- these are the NEW nodes
- Off-path nodes [2,3], [0,0], [2,2], [3,3] marked `dim` -- these are SHARED with V0
- Narration: explains new sums: leaf=7, [0,1]=8, root=15

### Frame 9 -- V1 Complete
- Path nodes marked `good` (sky-blue) -- new V1 nodes
- Shared nodes marked `dim`
- Array cell 1 updated to 7, marked `current`
- Version info updated to 1
- Narration: 3 new nodes created, V0's root (sum=11) still exists, O(log n) space

### Frame 10 -- Copy Operation Start
- All nodes reset to idle
- Array cell 1 reset
- Narration: copy V1 to create V2, just a pointer copy, O(1)

### Frame 11 -- V2 Created (Copy)
- All nodes marked `done` (green) -- entire tree shared with V1
- Version info updated to 2
- Narration: V2 is identical to V1, no nodes allocated

### Frame 12 -- Second Update Start
- All nodes reset to idle
- Narration: update a[3]=10 on V2, path is [0,3] -> [2,3] -> [3,3]

### Frame 13 -- Second Path Copy
- Path nodes [0,3], [2,3], [3,3] marked `current` (blue) -- new V2 nodes
- Off-path nodes [0,1], [0,0], [1,1], [2,2] marked `dim` -- shared from V1
- Narration: new sums: leaf=10, [2,3]=12, root=20

### Frame 14 -- V2 Updated
- Path nodes marked `good` (sky-blue)
- Shared nodes marked `done` (green)
- Array cell 3 updated to 10, marked `current`
- Narration: total nodes across 3 versions = 13 instead of 21

### Frame 15 -- Query V2 sum(0,3)
- Root highlighted
- Narration: V2 root sum=20, full coverage, return immediately

### Frame 16 -- Final Summary
- All nodes and modified array cells marked `good`
- Narration: 3 versions coexist (V0 sum=11, V1 sum=15, V2 sum=20), O(n + q log n) total

## Visual Characteristics

- **Color semantics:**
  - `idle` (default gray): inactive/reset nodes
  - `current` (blue): nodes being created or processed in this step
  - `done` (green): established nodes belonging to a version
  - `good` (sky-blue): newly completed nodes, final state emphasis
  - `dim` (faded): shared/reused nodes from a previous version
  - `error` (red): not used in this animation
- **highlight** (ephemeral yellow): currently inspected node during queries
- **Key teaching moments:**
  - Frame 8-9: path copying visualized -- blue path vs dim shared nodes
  - Frame 10-11: copy is O(1) -- just a pointer, all nodes green/shared
  - Frame 13-14: second update shows different path, different shared set
  - Frame 16: node count comparison (13 vs 21) drives home space savings
- **Persistence limitation:** The Tree primitive shows one tree structure. Old version roots are explained via narration since two simultaneous trees cannot be rendered. The dim/current/good color scheme distinguishes "new version nodes" from "shared old nodes" within a single tree view.
