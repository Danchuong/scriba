# Algorithm Visualization Animation Research

**Date:** 2026-04-13
**Purpose:** Document animation patterns from established algorithm visualization tools to inform Scriba's animation design.

---

## 1. DP Table Animations

### 1.1 Cell-by-Cell Reveal Patterns

**Manim approach (3Blue1Brown style):**
Manim's `Table` and `MathTable` classes provide `add_highlighted_cell((row, col), color=GREEN)` to place a `BackgroundRectangle` behind a cell, and `get_cell((row, col))` to retrieve cell mobjects for animation. A DP table fill is animated by iterating cells in fill order and calling:

```python
self.play(
    table.get_cell((i, j)).animate.set_fill(GREEN, opacity=0.5),
    run_time=0.3
)
```

The default `run_time` for any Manim animation is **1.0 second**. For DP tables with many cells, this is typically reduced to **0.2--0.5 seconds** per cell to maintain pacing. Manim's `LaggedStart` composition allows staggering cell fills with a `lag_ratio` (e.g., 0.05--0.25), so cells overlap in their animation start times rather than waiting for each to complete. This creates a "wave" effect across the table.

**Wave patterns:**
The most educationally clear DP table fills use one of three patterns:
1. **Row-major scan:** cells fill left-to-right, top-to-bottom. Used for 1D DP problems (Fibonacci, coin change). Each cell lights up 200--400ms after the previous.
2. **Diagonal wave:** cells fill along anti-diagonals. Used for interval DP (matrix chain multiplication, longest palindromic subsequence). The diagonal sweep makes dependency structure visually obvious --- every cell in diagonal `d` depends on cells in diagonals `< d`.
3. **Bottom-up pyramid:** cells fill from base cases upward. Used for knapsack, edit distance. The base row or column fills first (fast stagger, ~100ms each), then each subsequent row fills with slightly longer stagger (~200ms each) as the viewer tracks the growing solution.

**D3.js approach:**
D3 transitions use `selection.transition().delay((d, i) => i * 50).duration(300)` to stagger cell fills. The default transition duration is **250ms** with `d3.easeCubic` easing. For a grid/table, the common pattern is:

```javascript
cells.transition()
  .delay((d, i) => i * 80)   // 80ms stagger between cells
  .duration(300)              // each cell fill takes 300ms
  .style("fill", "#4CAF50")
  .style("opacity", 1);
```

The index-based delay `(d, i) => i * staggerMs` is the canonical D3 stagger pattern.

### 1.2 Recurrence Relation Visualization

**Dependency arrows:**
The most effective DP visualizations (seen in Manim-based YouTube content and VisuAlgo) show arrows from source cells to the target cell being computed. The animation sequence for filling cell `(i, j)` is:

1. **Highlight source cells** (the cells that `(i, j)` depends on) --- typically 2--3 cells for edit distance, or an entire row/column for knapsack. Each source cell gets a brief pulse (Manim's `Indicate` animation: scales mobject up by 1.2x then back, ~0.5s). In CSS/SVG terms: a `transform: scale(1.15)` with `ease-out` over 200ms, then back.
2. **Draw dependency arrows** from each source cell to the target cell. In Manim, this uses `Create(Arrow(...))` with `run_time=0.5`. The arrow draws progressively from tail to head (stroke-dashoffset animation in SVG terms). Duration: 300--500ms per arrow, or all arrows simultaneously with `AnimationGroup`.
3. **Show formula overlay** --- a small `MathTex` label appears near the target cell showing the recurrence (e.g., `dp[i][j] = dp[i-1][j-1] + 1`). Uses `FadeIn(formula, shift=UP*0.3)` over 0.5s.
4. **Fill target cell** with computed value. The cell background transitions to the "done" color (300ms) while the text value fades in or transforms from "?" to the computed number (200ms).
5. **Fade out arrows and formula** --- `FadeOut` with 200ms duration, removing visual clutter before the next cell.

**Timing for a complete cell-fill micro-sequence:** approximately 1.5--2.5 seconds total, comprising:
- Source highlight: 300ms
- Arrow draw-in: 400ms
- Formula display: 500ms (plus a 300ms hold for reading)
- Cell fill + value write: 400ms
- Cleanup fade: 200ms

### 1.3 What Makes Manim DP Animations Clear

Three key factors:
1. **Isolation of attention:** Only the relevant cells (source + target) are highlighted at any moment. All other cells are dimmed or at resting state. This is achieved by reducing opacity of non-active cells to 0.3--0.5.
2. **Temporal separation of concepts:** The dependency (arrows), computation (formula), and result (cell fill) are shown as distinct sequential phases, not simultaneously. Each phase has its own animation beat.
3. **Consistent visual vocabulary:** Source cells always use the same highlight color (e.g., yellow), target cells use another (e.g., green), arrows are always the same style. The viewer learns the visual language in the first 2--3 cells and can then predict and follow the pattern.

---

## 2. Graph Algorithm Animations

### 2.1 BFS/DFS Edge Traversal

**VisuAlgo's three-state vertex system:**
- **Unvisited:** black circle (default)
- **Explored/frontier:** blue circle (reached but neighbors not fully processed)
- **Visited/resolved:** orange circle (all neighbors processed)

**Edge coloring in VisuAlgo:**
- **Tree edges:** red --- edges that form the DFS/BFS spanning tree
- **Back edges:** blue --- edges pointing to an ancestor (cycle indicator)
- **Forward/cross edges:** grey --- non-tree, non-back edges

**Edge traversal animation patterns across tools:**

1. **Pulse along edge (most common):** An SVG `stroke-dashoffset` animation draws the edge progressively from source vertex to target vertex over 300--500ms. The edge starts fully dashed (invisible) and the dashoffset decreases to 0, revealing the line from tail to head. This directional reveal communicates traversal direction unambiguously.

2. **Color wave:** The edge color transitions from the source vertex's color to a highlight color (e.g., red) starting at the source end. Implemented via an SVG gradient that shifts its stop positions over time, or via `stroke-dasharray` with a colored segment that grows. Duration: 400--600ms.

3. **Glow/pulse effect:** The edge briefly thickens (stroke-width from 2px to 4px) and gains a glow (SVG filter: `feGaussianBlur` + composite) as it is traversed, then settles back to normal thickness in the new color. Total duration: 500ms (200ms expand, 300ms settle).

**BFS layer-by-layer visualization:**
The most effective BFS animations (VisuAlgo, USFCA) process vertices level-by-level with a visible "frontier wave":
- All vertices in the current frontier are highlighted simultaneously (blue)
- Edges from frontier to next layer are drawn with staggered starts (50--100ms offset per edge)
- Next-layer vertices turn blue as their incoming edge reaches them
- Previous frontier vertices turn orange (visited) in a batch after all next-layer edges complete
- This creates a perceivable wave expanding outward from the source

**DFS backtracking visualization:**
- The current path is highlighted with a distinct edge color (red)
- When backtracking, the current vertex transitions from blue (explored) to orange (visited) with a 200ms color morph
- The backtrack edge fades to grey (300ms), visually "releasing" it
- The previous vertex on the stack becomes the new active vertex (regains a pulsing highlight ring)

### 2.2 Dijkstra / Shortest Path

**VisuAlgo's approach:**
- Dual display: original graph (left) and evolving SSSP spanning tree (right)
- Shortest path distances displayed as red text beneath each vertex, updated in real-time during relaxation
- When edge `(u, v)` is relaxed: the edge briefly highlights (red pulse, ~400ms), and if `D[v]` decreases, the distance text beneath `v` animates from old value to new value (number morph or fade-replace, ~300ms)
- On hover (post-completion), the shortest path from source to any vertex is highlighted on the spanning tree

**Edge relaxation animation (common pattern across tools):**
1. Highlight current vertex `u` (scale up slightly, bright color) --- 200ms
2. For each neighbor `v` of `u`:
   a. Highlight edge `(u, v)` with directional pulse toward `v` --- 300ms
   b. Show tentative distance calculation near `v`: `D[u] + w(u,v) = X` --- FadeIn 200ms + hold 400ms
   c. If `X < D[v]`: animate distance label update (old value fades out / new value fades in, 250ms). Edge `(u, v)` turns green briefly (200ms) to signal improvement. Arrow in spanning tree updates.
   d. If `X >= D[v]`: edge returns to default color. Tentative calculation fades out with a red flash (100ms) or simply disappears.
3. Mark `u` as resolved (color transition to "done" state) --- 300ms

**USFCA Dijkstra visualization:**
Uses HTML5 Canvas with the command-based animation model. Each algorithmic operation (select min, relax edge, update distance) maps to a discrete animation frame. The animation manager supports forward/backward stepping and variable speed via a slider. Canvas redraws the entire state each frame, with color-coded vertices and edge weights.

### 2.3 Flow Network Animations

**iFlow (Interactive Max-Flow Visualizer):**
- Augmenting paths highlighted in **purple** when selected
- Capacity information shown via **blue** edge labels in format `applied_flow/original_capacity`
- **Bottleneck edge** highlighted distinctly when user requests a hint
- The tool uses a manual-step approach: user selects path, chooses flow amount, then updates residual graph --- each phase is a discrete visual state rather than a continuous animation
- Residual graph shows both forward edges (with remaining capacity) and backward edges (with flow amount that can be "pushed back")

**VisuAlgo max-flow:**
- Source drawn on leftmost side, sink on rightmost
- Augmenting path discovery animated edge-by-edge as a BFS/DFS traversal
- Flow update along path shown by edges simultaneously changing their flow labels
- Three algorithms available (Ford-Fulkerson, Edmonds-Karp, Dinic's) with distinct visual phases

**Effective flow animation pattern:**
1. BFS/DFS to find augmenting path: standard graph traversal animation (see 2.1)
2. **Path highlight:** all edges on the found path simultaneously change to a bright color (gold/yellow), 300ms transition
3. **Bottleneck identification:** the minimum-capacity edge on the path pulses or flashes (Manim `Flash` animation: radiating lines from the edge, 500ms)
4. **Flow push:** flow values on all path edges animate simultaneously --- counters increment/decrement over 400ms, edge thickness may change proportionally to flow
5. **Residual update:** backward edges appear (FadeIn, 300ms) or existing edges update their capacity labels

---

## 3. Array / Sorting Animations

### 3.1 Swap Animations

**The canonical swap animation** (used by VisuAlgo, Toptal, SortVisualizer, and virtually all sorting visualizers):

1. **Highlight the two elements to be swapped** --- both bars/cells simultaneously change to a comparison color (typically red or yellow). Duration: 150--200ms.
2. **Physically move elements** --- Element A translates rightward while Element B translates leftward along an arc or straight path. The arc path (elements move up, across, then down) is more readable than a straight cross because it avoids visual overlap.
   - Arc swap: Element A moves `up 30px` over 150ms, `right N*cellWidth` over 200ms, `down 30px` over 150ms. Element B mirrors. Total: ~500ms.
   - Straight swap: Both elements translate horizontally to each other's positions. Duration: 300--400ms. Simpler but elements cross through each other at the midpoint.
3. **Settle into new positions** --- Elements change back to default color. Duration: 150ms with ease-out.

**Total swap animation duration:** 400--700ms depending on distance and style.

**CSS/SVG implementation pattern:**
```css
.swapping-left {
  transition: transform 400ms cubic-bezier(0.34, 1.56, 0.64, 1); /* slight overshoot */
  transform: translateX(calc(var(--swap-distance) * -1));
}
.swapping-right {
  transition: transform 400ms cubic-bezier(0.34, 1.56, 0.64, 1);
  transform: translateX(var(--swap-distance));
}
```

The `cubic-bezier(0.34, 1.56, 0.64, 1)` provides a slight overshoot that makes the swap feel physical and tangible, as if elements have momentum.

### 3.2 Comparison Highlights

**VisuAlgo sorting animations:**
- Keyboard controls: spacebar play/pause, left/right arrows step, +/- speed control
- Compared elements flash briefly in a distinct color (red/orange)
- Speed slider adds a per-array-access delay; due to 1ms timer resolution on some platforms, the scale is compressed at the fast end
- Real-time swap and comparison counters displayed alongside the visualization

**Common comparison pattern:**
1. Both compared elements transition to comparison color (yellow/red) --- 100--150ms
2. Hold for 200--400ms (longer at slow speeds to allow viewer to read values)
3. If no swap needed: both return to default color --- 100ms
4. If swap needed: transition into swap animation (see 3.1)

### 3.3 Partition Animations (Quicksort)

**Chris Laux's quicksort visualization:**
- Pivot element colored **red**, stands out from all others
- Elements smaller than or equal to pivot colored **green** as they are identified
- Elements larger than pivot colored **blue**
- As the algorithm scans left-to-right, each element transitions to green or blue upon comparison (200ms color transition)
- When a swap occurs during partitioning, elements physically slide to their new positions (300--400ms)
- Two pointer indicators (`i` and `j` or `low` and `high`) move visually along the array, typically as arrow markers or highlighted borders below/above the array

**Y. Daniel Liang's partition animation:**
- Step-by-step with "low" and "high" pointers shown as labeled arrows
- Each pointer movement animates as a slide (200ms)
- Swap between low and high elements uses the arc-swap pattern
- Pivot placement at the end slides the pivot to its final sorted position (400ms)

### 3.4 Merge Animations

**Merge step visualization (VisuAlgo and others):**
1. Two sorted subarrays shown side by side or in separate regions
2. Two pointer/cursor indicators mark the current comparison position in each subarray
3. At each step:
   a. Both pointed-to elements highlight (200ms)
   b. The smaller element slides downward (or into a result array area) at the next available position --- 300ms `translateY` + `translateX` animation
   c. The pointer in that subarray advances one position (100ms slide)
4. When one subarray is exhausted, remaining elements slide into the result array in sequence (100ms stagger each)
5. The merged result array replaces the original two subarrays --- this is either an in-place slide-up (400ms) or a fade-swap

**Total duration for merging N elements:** approximately `N * 500ms` at default speed, with speed slider providing 0.25x--4x multiplier.

### 3.5 Pointer/Cursor Movement

Pointers and cursors in array visualizations are typically rendered as:
- **Arrow below the array** pointing up at the current element (most common)
- **Colored border** on the current element (simpler, less visual clutter)
- **Labeled marker** (e.g., "i", "j", "pivot") sliding along a track beneath the array

Movement animation: `translateX` transition of `150--250ms` with `ease-out`. When a pointer jumps multiple positions (e.g., binary search), the movement is still animated but at higher speed (same duration, longer distance) to maintain temporal consistency.

---

## 4. Tree Animations

### 4.1 Node Insertion with Subtree Reorganization

**USFCA BST visualization:**
- New node appears at the root and "falls" through the tree following the insertion path
- At each comparison, the current node briefly highlights (200ms color change)
- The new node slides left or right based on comparison (300ms transition)
- This continues until the new node reaches its insertion point
- Final placement: node slides to its computed position and tree edges redraw

**VisuAlgo BST animation:**
- Insertion follows a top-down path from root
- Each visited node turns blue (explored), then orange (visited) after the algorithm moves past it
- The new node appears at its final position with a `FadeIn` or `GrowFromCenter` effect (300ms)
- If the tree needs to rebalance (AVL/RB), rebalancing animations follow immediately

### 4.2 Tree Rotation (AVL, Red-Black)

**USFCA AVL/Red-Black visualizations:**
Tree rotations are among the most complex animations in algorithm visualization. The USFCA tool animates rotations as follows:

**Single rotation (e.g., right rotation at node X):**
1. Highlight the pivot node X and its left child Y (300ms pulse)
2. Y's right subtree (T2) detaches from Y --- the edge fades out (200ms)
3. T2 slides to become X's new left child --- edge draws in from X to T2 (300ms)
4. X slides downward and rightward to become Y's right child --- smooth position interpolation (500ms, ease-in-out)
5. Y slides upward to X's former position (500ms, ease-in-out, simultaneous with step 4)
6. All affected subtrees shift positions to maintain proper tree layout (400ms, eased)
7. Edge colors update to reflect new parent-child relationships (200ms)

**Total single rotation:** ~1.2--1.5 seconds

**Double rotation:** Two single rotations in sequence, with a brief pause (200ms) between them to let the viewer register the intermediate state.

**Key technique:** Position interpolation. Every node has a target `(x, y)` coordinate computed from the new tree structure. All nodes transition simultaneously from old positions to new positions using `ease-in-out` easing over 400--600ms. This creates a smooth "reorganization" effect where the entire tree seems to shift as a fluid structure.

### 4.3 Level-Order Traversal with Wave Highlight

**Pattern used across tools:**
1. Root node highlights first (color transition to "active" state, 200ms)
2. After a hold of 300--500ms, root transitions to "visited" state
3. All depth-1 nodes highlight simultaneously (or with 50ms stagger within the level)
4. After hold, they transition to visited; depth-2 nodes highlight
5. This creates a visible "wave" descending level by level through the tree

The wave effect is enhanced by:
- Using a bright, saturated color for the "active" frontier (e.g., electric blue)
- Using a muted color for already-visited nodes (e.g., light grey or pale orange)
- Optionally drawing a horizontal "level line" that descends with the wave

### 4.4 Path Highlighting (Root to Target)

**Common pattern (USFCA, VisuAlgo):**
1. Start at root: node highlights with bright color (200ms)
2. Edge to next node on path draws in with directional pulse (300ms stroke-dashoffset animation)
3. Next node highlights (200ms)
4. Repeat until target is reached
5. Target node gets a special effect: scale pulse (1.0 -> 1.3 -> 1.0, 400ms) or ring/glow effect
6. The entire path remains highlighted in the final state as a distinct color trail

**Manim equivalent:**
```python
for edge in path_edges:
    self.play(
        edge.animate.set_color(YELLOW).set_stroke(width=4),
        run_time=0.3
    )
    self.play(
        Indicate(target_vertex, scale_factor=1.3),
        run_time=0.4
    )
```

---

## 5. Linked List Animations

### 5.1 Pointer Redirection

**VisuAlgo linked list operations:**
- Pointers drawn as curved arrows from one node's "next" field to the next node
- When a pointer is redirected (e.g., during insertion or deletion), the old arrow fades out (200ms) and a new arrow draws in from the source node to the new target (400ms stroke-dashoffset from tail to head)
- The arrow path may use a brief arc animation: the arrow "detaches" from the old target, swings through an arc, and "attaches" to the new target (600ms total with ease-in-out)

**DSA Visualizer approach:**
- Separate speed controls for node animation and pointer animation
- Pointer arrows animate with visible directional flow (a small dot or highlight traveling along the arrow path, 300ms)

**Effective pointer redirection sequence:**
1. Old pointer arrow turns red (danger/change signal) --- 150ms
2. Old pointer fades out or "unlinks" (the arrow tip detaches and the line retracts toward the source node) --- 300ms
3. New pointer draws from source to new target --- 400ms, directional (stroke-dashoffset)
4. New pointer settles into final color (default arrow color) --- 150ms

### 5.2 Node Insertion Between Existing Nodes

**Animation sequence:**
1. New node fades in or scales up from zero **above** the insertion point (GrowFromCenter, 300ms). It floats above the list, not yet connected.
2. Existing pointer from predecessor to successor turns red (about to change) --- 150ms
3. Predecessor's pointer redirects to new node --- old arrow retracts, new arrow draws to new node (400ms)
4. New node's pointer draws from new node to successor (400ms)
5. New node slides downward into the list's horizontal line (translateY, 300ms ease-out)
6. Surrounding nodes may slide apart to make room (translateX on all subsequent nodes, 300ms)

**Total insertion animation:** ~1.5--2.0 seconds

### 5.3 Traversal Cursor

**Common approach:**
- A pointer/arrow labeled "current" or "ptr" sits below or above the first node
- As traversal advances, the cursor slides to the next node (200--300ms translateX with ease-out)
- The visited node transitions to a "visited" color (200ms)
- When the cursor reaches the target or end of list, it may pulse or flash (Indicate animation, 400ms)

---

## 6. General Animation Patterns

### 6.1 Animation Sequencing and Composition

**Manim's composition system (gold standard for sequencing):**

| Primitive | Behavior | Default lag_ratio |
|-----------|----------|------------------|
| `AnimationGroup` | All animations play together (simultaneous) | 0.0 |
| `LaggedStart` | Staggered start times | 0.05 |
| `LaggedStartMap` | Maps an animation type to a group of mobjects with stagger | 0.05 |
| `Succession` | Animations play one after another | 1.0 |

The `lag_ratio` parameter controls overlap:
- `0.0` = all start at the same time (fully parallel)
- `1.0` = each starts when the previous finishes (fully sequential)
- `0.25` = each starts when the previous is 25% complete (overlapping cascade)

**Micro-animation chaining pattern (applicable to Scriba):**
A single algorithm "step" often comprises 3--5 micro-animations that should be perceived as a cohesive unit:

```
Step: "Relax edge (u, v)"
  Phase 1 (simultaneous):  highlight u, highlight edge (u,v)     [300ms]
  Phase 2 (sequential):    show distance calculation              [400ms]
  Phase 3 (conditional):   update distance label OR flash red     [250ms]
  Phase 4 (simultaneous):  reset highlights, advance to next edge [200ms]
```

In CSS/SVG, this maps to chained `transition` + `transitionend` event listeners, or CSS `@keyframes` with percentage-based timing, or a JavaScript animation scheduler using `requestAnimationFrame` with a queue of timed callbacks.

**D3.js chaining pattern:**
```javascript
// Chain transitions sequentially
selection.transition("phase1")
  .duration(300)
  .attr("fill", "yellow")
  .transition("phase2")
  .delay(100)
  .duration(400)
  .attr("fill", "green");
```

### 6.2 Easing Curves for Educational Content

**Manim rate functions (easing curves):**

| Function | Behavior | Best for |
|----------|----------|----------|
| `smooth` (default) | S-curve, slow-fast-slow | General purpose, most natural |
| `linear` | Constant speed | Progress bars, clocks, uniform motion |
| `ease_out_sine` | Fast start, gentle stop | Elements arriving at destination |
| `ease_in_sine` | Gentle start, fast end | Elements departing |
| `ease_in_out_quad` | Symmetric acceleration | Position swaps, bilateral motion |
| `there_and_back` | Smooth out and return | Pulse/indicate effects |
| `lingering` | Reaches end early, holds | Emphasis on final state |
| `exponential_decay` | Quick initial change, slow tail | Settling after disturbance |

**CSS easing recommendations for educational viz:**

| Effect | CSS Value | Use Case |
|--------|-----------|----------|
| Natural motion | `ease-out` / `cubic-bezier(0, 0, 0.58, 1)` | Elements moving to a new position |
| Entrance | `cubic-bezier(0.16, 1, 0.3, 1)` (expo-out) | FadeIn, GrowFromCenter |
| Exit | `cubic-bezier(0.7, 0, 0.84, 0)` (expo-in) | FadeOut, elements leaving |
| Swap overshoot | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Array element swaps (slight bounce at end) |
| Subtle bounce | `cubic-bezier(0.68, -0.55, 0.27, 1.55)` | Attention-grabbing arrivals |

**Key principle:** For educational content, `ease-out` (deceleration) is almost always preferred for element arrivals. The viewer's eye tracks the element during the slow-down phase, landing on the final position. `ease-in` (acceleration) is reserved for exits where the viewer should focus on the departure point, not the destination.

Avoid `linear` easing for spatial movement --- it looks mechanical and unnatural. Reserve `linear` for progress indicators and timing-based animations.

### 6.3 Duration Sweet Spots

**Research-backed timing guidelines:**

| Animation Type | Duration | Source |
|----------------|----------|--------|
| Human visual perception threshold | ~230ms | Model Human Processor (Card, Moran, Newell) |
| "Instant" feedback | ~100ms | Nielsen Norman Group |
| Simple state change (color flip) | 150--250ms | NN/g, Val Head |
| Moderate transition (position swap, panel slide) | 300--500ms | NN/g, Val Head |
| Complex multi-phase transition | 500--800ms | Val Head |
| Entrance animation | 200--400ms | NN/g |
| Exit animation | 150--300ms (shorter than entrance) | NN/g |
| Maximum before feeling "draggy" | ~500ms per individual animation | NN/g |
| Per-cell stagger in table fill | 50--100ms offset | D3.js convention |
| Per-element stagger in sorting | 80--150ms offset | Common in sorting visualizers |

**Asymmetric timing principle (NN/g):** Entrances should take longer than exits. A modal takes 300ms to appear but 200ms to disappear. For algorithm viz: a cell filling (entrance of value) takes 300ms, but clearing a highlight (exit) takes 150--200ms.

**Speed control in educational tools:**
All major tools (VisuAlgo, USFCA, Algorithm Visualizer) provide a speed slider, typically offering 0.25x to 4x speed relative to a default. The default speed is calibrated so a single algorithm step takes roughly **0.5--1.5 seconds** for simple operations (compare, swap) and **1.5--3.0 seconds** for compound operations (rotate tree, relax edge with calculation). This maps to the 200--500ms range for individual micro-animations within those steps.

### 6.4 Attention Guidance Techniques

**Dimming / de-emphasis (most effective):**
Non-active elements reduce to 30--50% opacity. This is the single most effective attention guidance technique across all surveyed tools. In Manim, this is:
```python
self.play(*[mob.animate.set_opacity(0.3) for mob in inactive_mobjects])
```

In CSS: `opacity: 0.3; transition: opacity 200ms ease-out;` on inactive elements.

**Manim indication animations:**

| Animation | Visual Effect | Duration | Use Case |
|-----------|--------------|----------|----------|
| `Indicate` | Scale up 1.2x then back, brief yellow flash | 0.5s | "Look at this element" |
| `Flash` | Radiating lines burst outward from center | 0.5s | "Something important happened here" |
| `Circumscribe` | Temporary line drawn around the mobject | 1.0s | "This group of elements matters" |
| `FocusOn` | Spotlight shrinks onto a position | 0.5s | "Zoom attention here" |
| `Wiggle` | Brief side-to-side oscillation | 0.5s | "This value just changed" |
| `ShowPassingFlash` | Bright highlight sweeps along a path | 0.5s | "Follow this edge/path" |
| `ApplyWave` | Sinusoidal wave ripples through text/shape | 1.0s | "This text is important" |

**Color-based attention (common across all tools):**
- **Active/current:** Bright, saturated color (electric blue, vivid green)
- **Frontier/processing:** Medium saturation (standard blue, orange)
- **Visited/done:** Muted, desaturated (pale grey, light green)
- **Unvisited/default:** Neutral (white, light grey, black outline)
- **Danger/error/reject:** Red (brief flash for failed comparisons, rejected paths)

**Scale-based attention:**
- Active elements may be 10--20% larger than resting state
- Manim's `Indicate` uses `scale_factor=1.2` by default
- CSS: `transform: scale(1.15)` with `transition: transform 200ms ease-out`
- Do not exceed 1.3x scale --- larger distorts the layout and feels cartoonish

### 6.5 Narration Sync and Text-Animation Coordination

**Manim approach:**
Manim animations are defined in code alongside `self.wait(duration)` calls. Text explanations appear as `Text` or `MathTex` mobjects that `FadeIn` before the animation they describe and `FadeOut` after. The pattern is:

```python
# 1. Show explanation text
explanation = Text("Now we relax edge (u,v)").scale(0.5)
self.play(FadeIn(explanation, shift=UP*0.3), run_time=0.3)
self.wait(0.5)  # reading time

# 2. Perform the animation
self.play(edge.animate.set_color(YELLOW), run_time=0.4)

# 3. Remove explanation
self.play(FadeOut(explanation), run_time=0.2)
```

**VisuAlgo approach:**
- Pseudocode panel on the side highlights the current line of code being executed
- Line highlighting syncs with the animation step --- when edge relaxation animates, the corresponding `if D[v] > D[u] + w(u,v)` line is highlighted
- Status bar text updates to describe the current operation in natural language
- Both pseudocode highlight and status text update at the **start** of each animation step (not the end)

**Effective narration sync pattern:**
1. Update status text / highlight pseudocode line (instant or 100ms fade)
2. Brief pause for reading (200--300ms)
3. Execute the visual animation (300--800ms depending on complexity)
4. Brief pause after animation for comprehension (100--200ms)
5. Move to next step

**Key finding from academic research (Hundhausen et al., 2002):** "How students use AV technology has a greater impact on effectiveness than what AV technology shows them." Passive viewing of animations has limited educational benefit. Interactivity --- stepping, predicting, answering embedded questions --- is what drives comprehension. This means the animation system must support pause/step/speed-control as first-class features, not afterthoughts.

### 6.6 USFCA Animation Architecture

**Implementation details:**
- Originally Java, rewritten in ActionScript3 (Flash), then ported to JavaScript + HTML5 Canvas
- **Command-based animation model:** Each algorithm operation generates a sequence of discrete animation commands pushed onto a queue
- **Bidirectional traversal:** Users can step forward and backward through the animation history
- Each command represents an atomic visual change (move node, change color, update label)
- The animation manager processes commands at a rate controlled by the speed slider
- Canvas is fully redrawn each frame (immediate mode rendering), not DOM-diffed

**The command queue pattern** is notable because it cleanly separates algorithm logic from rendering. The algorithm produces a flat list of visual commands; the renderer consumes them at whatever speed the user chooses. This is the same architecture VisuAlgo uses (generators yielding actions) and is directly applicable to Scriba's frame-based model.

---

## 7. Tool-Specific Architecture Summary

### 7.1 Manim

- **Rendering:** Pre-rendered video frames (not interactive)
- **Default duration:** 1.0 second per animation
- **Easing:** `smooth` (S-curve) by default
- **Composition:** `AnimationGroup`, `LaggedStart`, `Succession` for sequencing
- **Strengths:** Precise control over every visual element, beautiful output, excellent for explanation
- **Weakness for Scriba:** Not interactive, pre-rendered only

### 7.2 VisuAlgo

- **Rendering:** Web-based (HTML5, CSS3, JavaScript)
- **Architecture:** Algorithm engine emits atomic actions; renderer consumes them with animations
- **Interactivity:** Play/pause/step, speed control, custom input
- **Strengths:** Comprehensive algorithm coverage, pseudocode sync, educational design
- **Most relevant to Scriba:** Action queue architecture, step-based playback, dual pseudocode+animation display

### 7.3 USFCA (David Galles)

- **Rendering:** HTML5 Canvas (immediate mode)
- **Architecture:** Command queue with bidirectional traversal
- **Interactivity:** Forward/backward stepping, speed slider, canvas resize
- **Strengths:** Wide coverage of data structures, simple and clean interface
- **Most relevant to Scriba:** Command queue pattern, backward stepping support

### 7.4 D3.js Ecosystem

- **Rendering:** SVG DOM manipulation
- **Default duration:** 250ms per transition
- **Default easing:** `d3.easeCubic`
- **Composition:** Chained `.transition()` calls, index-based delay for stagger
- **Enter/Exit/Update:** Data-join pattern for adding/removing/updating elements
- **Strengths:** SVG-native (like Scriba), data-driven, extensive easing library
- **Most relevant to Scriba:** Transition timing patterns, stagger conventions, SVG animation approach

### 7.5 Algorithm Visualizer (algorithm-visualizer.org)

- **Rendering:** Web-based with multiple visualization backends
- **Architecture:** Algorithm code as generator functions yielding visualization commands
- **Strengths:** Open-source, supports many languages
- **Most relevant to Scriba:** Generator-based algorithm definition

---

## 8. Academic Research Findings

### 8.1 Meta-Study of Algorithm Visualization Effectiveness

**Hundhausen, Douglas, Stasko (2002)** conducted a meta-study analyzing multiple AV effectiveness experiments. Key findings:

1. **Interactivity matters more than visual fidelity.** Students who actively engaged with visualizations (answering questions, predicting next steps, constructing their own visualizations) learned significantly more than passive viewers. Merely watching even beautifully animated algorithms provided limited benefit over textbook study.

2. **Mixed results for passive animation.** Attempts to demonstrate that animation alone improves comprehension "produced disappointing results." The visual appeal of animations does not automatically translate to learning gains.

3. **Engagement taxonomy (Naps et al.):** Levels from least to most effective:
   - **Viewing:** Passive watching (minimal benefit)
   - **Responding:** Answering questions about what the visualization shows (moderate benefit)
   - **Changing:** Modifying input data and observing effects (good benefit)
   - **Constructing:** Building the visualization step-by-step (best benefit)
   - **Presenting:** Explaining the visualization to others (highest benefit)

### 8.2 Implications for Scriba

1. **Step control is essential.** Autoplay is a convenience, but the educational value comes from stepping and pausing. Scriba's existing step buttons are on the right track.
2. **Prediction prompts increase learning.** Before revealing the next step, asking "what value will cell (i,j) contain?" forces active engagement. This is a UX feature beyond pure animation but should inform animation design --- the system should be able to pause at a "prediction point" before revealing the answer.
3. **Animation serves comprehension, not decoration.** Every animation should communicate algorithmic meaning (this cell depends on those cells; this edge was relaxed; this node was visited). Gratuitous flourishes that don't map to algorithmic concepts are noise.
4. **Speed control with a sensible default.** Default speed should be slow enough for a first-time learner (~1 second per elementary step), with the ability to speed up 4x for review.

### 8.3 VR/Immersive Studies

A 2023 Frontiers in Education study on sorting algorithm visualization in VR found that "students who studied sorting methods using VR better understand the conditions of bubble sorting and selection sorting methods." 90.8% of pilot study students agreed that visualization tools facilitate faster learning. While VR is out of scope for Scriba, this validates the general approach of animated visualization for algorithm education.

---

## 9. Concrete Timing Recommendations for Scriba

Based on this research, the following timing values are recommended for Scriba's animation system:

### 9.1 Base Durations

| Animation Type | Duration | Easing |
|----------------|----------|--------|
| Color state change (fill/stroke morph) | 200--300ms | ease-out |
| Element position swap (translateX/Y) | 350--500ms | cubic-bezier(0.34, 1.56, 0.64, 1) |
| Edge draw-in (stroke-dashoffset) | 300--500ms | ease-out |
| FadeIn (new element appearing) | 200--350ms | ease-out |
| FadeOut (element departing) | 150--250ms | ease-in |
| Scale pulse (Indicate effect) | 300--500ms | ease-in-out or there-and-back |
| Text value change (number update) | 200--300ms | ease-out |
| Pointer/cursor slide | 150--250ms | ease-out |

### 9.2 Stagger Offsets

| Context | Stagger Per Element |
|---------|-------------------|
| DP table cell fill (dense) | 50--100ms |
| Array element comparison wave | 80--120ms |
| Tree level highlight | 50ms within level, 300ms between levels |
| Graph frontier expansion | 50--100ms per edge |
| Linked list traversal | 200--300ms per node |

### 9.3 Compound Step Timing

| Algorithm Step | Total Duration | Micro-animation Breakdown |
|----------------|---------------|--------------------------|
| DP cell fill (with arrows) | 1.5--2.5s | highlight sources 300ms + draw arrows 400ms + show formula 500ms + fill cell 300ms + cleanup 200ms |
| Array swap | 0.5--0.8s | highlight 200ms + move 400ms + settle 150ms |
| Edge relaxation | 1.0--1.8s | highlight vertex 200ms + pulse edge 300ms + show calc 400ms + update label 250ms + reset 200ms |
| Tree rotation | 1.2--1.8s | highlight pivot 300ms + detach subtree 200ms + reposition nodes 500ms + redraw edges 300ms |
| Linked list insert | 1.5--2.0s | show new node 300ms + redirect pointer 400ms + draw new pointer 400ms + slide into position 300ms |

### 9.4 Speed Multiplier Range

- **Slowest (0.25x):** For first-time learners or complex algorithms. Multiply all durations by 4.
- **Default (1.0x):** The timings above.
- **Fast (2.0x):** For review. Divide durations by 2.
- **Fastest (4.0x):** For skimming. Divide durations by 4. Below this, animations become imperceptible and should snap instantly.

---

## Sources

- [Manim Community Documentation - Animation](https://docs.manim.community/en/stable/reference/manim.animation.animation.html)
- [Manim Community - Rate Functions](https://docs.manim.community/en/stable/reference/manim.utils.rate_functions.html)
- [Manim Community - Indication Animations](https://docs.manim.community/en/stable/reference/manim.animation.indication.html)
- [Manim Community - Animation Composition (AnimationGroup, LaggedStart, Succession)](https://docs.manim.community/en/stable/reference/manim.animation.composition.html)
- [Manim Community - Table](https://docs.manim.community/en/stable/reference/manim.mobject.table.Table.html)
- [Manim Community - Graph](https://docs.manim.community/en/stable/reference/manim.mobject.graph.Graph.html)
- [How I animate 3Blue1Brown - Grant Sanderson](https://3blue1brown.substack.com/p/how-i-animate-3blue1brown)
- [VisuAlgo - Visualising Data Structures and Algorithms](https://visualgo.net/en)
- [VisuAlgo - DFS & BFS Notes](https://visualgo.net/en/dfsbfs/print)
- [VisuAlgo - SSSP Notes (Dijkstra)](https://visualgo.net/en/sssp/print)
- [VisuAlgo - Network Flow](https://visualgo.net/en/maxflow)
- [USFCA Data Structure Visualizations - David Galles](https://www.cs.usfca.edu/~galles/visualization/)
- [USFCA Visualization - About](https://www.cs.usfca.edu/~galles/visualization/about.html)
- [D3.js Transition Timing](https://d3js.org/d3-transition/timing)
- [D3.js Transitions - d3indepth](https://www.d3indepth.com/transitions/)
- [iFlow: An Interactive Max-Flow/Min-Cut Algorithms Visualizer](https://arxiv.org/html/2411.10484v1)
- [Hundhausen et al. - A Meta-Study of Algorithm Visualization Effectiveness (2002)](https://faculty.cc.gatech.edu/~stasko/papers/jvlc02.pdf)
- [The efficacy of animation and visualization in teaching data structures (2024)](https://link.springer.com/article/10.1007/s11423-024-10382-w)
- [Visualization of sorting algorithms in VR (Frontiers in Education, 2023)](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2023.1195200/full)
- [Executing UX Animations: Duration and Motion Characteristics - Nielsen Norman Group](https://www.nngroup.com/articles/animation-duration/)
- [How fast should your UI animations be? - Val Head](https://valhead.com/2016/05/05/how-fast-should-your-ui-animations-be/)
- [How to code animations of data structures and algorithms - Chris Laux](https://dev.to/chrislaux/how-to-code-animations-of-data-structures-and-algorithms-hje)
- [Algorithm Visualizer](https://algorithm-visualizer.org/)
- [Toptal Sorting Algorithms Animations](https://www.toptal.com/developers/sorting-algorithms)
- [Easing Functions Cheat Sheet](https://easings.net/)
- [Understanding easing and cubic-bezier curves in CSS - Josh Collinsworth](https://joshcollinsworth.com/blog/easing-curves)
