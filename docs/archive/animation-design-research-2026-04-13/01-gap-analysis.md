# Animation Gap Analysis — Scriba Primitives

**Date**: 2026-04-13
**Scope**: All 15 primitives in `scriba/animation/primitives/` vs the current animation runtime (`differ.py` + `emitter.py` JS)

---

## Executive Summary

The current animation system operates at the **state-transition** level: it diffs `shape_states` between consecutive frames and emits one of eight transition kinds. All animated transitions (element_add, element_remove, position_move, annotation_add/remove) use a flat 180ms WAAPI animation with no sequencing. The four remaining kinds (recolor, value_change, highlight_on, highlight_off) are **instant** CSS class/text swaps with zero visual interpolation.

This means every primitive — regardless of its educational semantics — gets the same treatment: instant color flips, instant value swaps, and uniform 180ms opacity fades. There is no concept of:

1. **Sequenced transitions** (step A, then B, then C within a single frame advance)
2. **Semantic animations** (e.g., "traverse this edge," "fill this cell," "slide this pointer")
3. **Interpolated property changes** (e.g., smooth color transitions, number counter roll-ups)
4. **Directional motion** (e.g., data flowing left-to-right through a linked list)

The gap is fundamental: the differ only knows about property deltas, not about the educational *intent* behind them.

---

## Current Animation System Architecture

### differ.py — Transition Computation

Compares consecutive `FrameData` objects and emits `Transition` records:

| Kind | What it does | Animated? |
|------|-------------|-----------|
| `recolor` | CSS class swap (`scriba-state-X` to `scriba-state-Y`) | **No** — instant class string replacement |
| `value_change` | `<text>` content swap | **No** — instant `textContent` assignment |
| `highlight_on` | Adds `scriba-highlighted` class | **No** — instant class addition |
| `highlight_off` | Removes `scriba-highlighted` class | **No** — instant class removal |
| `element_add` | Clones element from next-frame SVG, opacity 0 to 1 | **Yes** — 180ms `ease-in` WAAPI |
| `element_remove` | Fades existing element opacity 1 to 0 | **Yes** — 180ms `ease-out` WAAPI |
| `position_move` | Translates element from old to new position | **Yes** — 180ms `ease-out` WAAPI |
| `annotation_add` | Clones annotation, opacity 0 to 1 | **Yes** — 180ms `ease-in` WAAPI |
| `annotation_remove` | Fades annotation opacity 1 to 0 | **Yes** — 180ms `ease-out` WAAPI |

### emitter.py JS Runtime — Animation Execution

- All transitions within a frame advance execute **simultaneously** (no sequencing).
- After all WAAPI animations resolve via `Promise.all`, the runtime does a full SVG swap to the target frame (`stage.innerHTML = frames[toIdx].svg`).
- The 180ms duration (`DUR`) is a hardcoded constant shared across all transition types.
- `prefers-reduced-motion: reduce` disables all WAAPI animations entirely.
- Transition data is serialized as compact `[target, prop, from, to, kind]` arrays — no room for per-transition timing metadata.

### Structural Limitation

The differ has **no knowledge of primitive type**. It sees only generic shape_states dicts. This means it cannot emit primitive-specific transition kinds (e.g., "dp_fill", "edge_traverse", "pointer_slide"). Any enrichment must happen either:

1. In the differ (by inspecting `data-primitive` prefixes or a primitive type registry), or
2. In a new animation planning layer between the differ and the JS runtime.

---

## Per-Primitive Gap Analysis

---

### 1. Array (`array.py`)

**What it visualizes**: Fixed-length horizontal row of indexed cells with optional index labels, caption, and annotation arrows.

**State changes supported**:
- Per-cell state (idle, current, done, error, highlight, hidden)
- Per-cell value override
- Per-cell and per-range highlighting
- Annotation arrows between cells

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Cell state change (e.g., idle to current) | Instant CSS class swap | **Color interpolation** — 200ms `ease-out` background fill transition using CSS `transition` on the rect fill property. For "current" state, a brief **pulse/scale** effect (1.0 to 1.05 to 1.0, 250ms) draws the eye. |
| Cell value change | Instant text swap | **Counter roll-up** for numeric values (digits tick from old to new over 150ms). For non-numeric, a **cross-fade** (old text fades out 80ms, new fades in 80ms, staggered 40ms). |
| Highlight on | Instant class add | **Glow pulse** — 300ms `ease-in-out` box-shadow or SVG filter glow that settles to steady highlight state. |
| Highlight off | Instant class remove | **Glow fade** — 200ms `ease-out` glow dissipation. |
| Annotation arrow add | 180ms opacity fade-in | **Arrow draw** — SVG `stroke-dashoffset` animation from full length to 0, 400ms `ease-out`, creating a "drawing" effect along the arrow path. Arrowhead appears at the end (last 50ms). |
| Annotation arrow remove | 180ms opacity fade-out | **Arrow retract** — reverse draw (dashoffset from 0 to full), 300ms, then fade. |
| Range highlight | Instant class swap per cell | **Sweep highlight** — cells in the range illuminate left-to-right with 30ms stagger, creating a visual "scan" effect. Total: ~30ms x range_length + 200ms base. |

**Missing entirely**:
- **Pointer/cursor animation**: A small triangle or arrow indicator that slides along the array to show "we are now looking at cell[i]." Would use `position_move` semantics but needs a dedicated pointer element.
- **Swap animation**: When two cells exchange values (common in sorting), show the values physically moving between cells via curved arc paths (300ms `ease-in-out`).
- **Comparison animation**: Brief side-by-side bounce or scale-up of two cells being compared (150ms).

---

### 2. DPTable (`dptable.py`)

**What it visualizes**: 1D or 2D DP recurrence table with index labels and transition arrows showing cell dependencies.

**State changes supported**:
- Per-cell state (same palette as Array)
- Per-cell value override
- Highlighting (per-cell, ranges in 1D)
- Annotation arrows (Bezier curves between cells)

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Cell fill (idle to current/done) | Instant CSS class swap | **Progressive fill** — a `clip-path` or gradient wipe that fills the cell from left-to-right (or top-to-bottom for 2D), 250ms `ease-out`. This visually represents "this cell is being computed now." |
| Cell value write | Instant text swap | **Typewriter/counter** — for numeric DP values, a rapid counter animation ticking from 0 (or the previous value) to the new value, 200ms. For the first write into an empty cell, the number "materializes" with a slight scale-up (0.8 to 1.0) and fade-in (150ms). |
| Dependency arrow add | 180ms opacity fade | **Sequenced draw-then-fill**: (1) Arrow path draws from source cell to target cell via `stroke-dashoffset`, 350ms `ease-out`. (2) On draw completion, the target cell begins its fill animation. This creates the causal chain: "dp[i] depends on dp[i-1] and dp[i-2]." Total: ~600ms for arrow + fill. |
| Multiple dependency arrows | All fade in simultaneously | **Staggered draw** — when multiple arrows target the same cell, draw them with 100ms stagger so the viewer can trace each dependency individually before the cell fills. |
| 2D cell traversal | Instant state changes | **Wavefront sweep** — for 2D DP (e.g., edit distance), cells along a diagonal or row fill in sequence with 20ms stagger, visually showing the computation order. |

**Missing entirely**:
- **Recurrence visualization**: Animated formula overlay showing e.g. "dp[i] = dp[i-1] + dp[i-2]" with the source values flying into the formula and the result dropping into the target cell (complex but extremely educational).
- **Subproblem highlighting**: When computing dp[i], briefly pulse the cells that dp[i] depends on (dp[i-1], dp[i-2]) before drawing arrows, creating a "look back" effect.
- **Optimal path trace**: For completed DP tables, an animated backtracking path that highlights the optimal solution path cell-by-cell with directional arrows, ~100ms per cell.

---

### 3. Graph (`graph.py`)

**What it visualizes**: Force-directed graph with nodes (circles) and edges (lines), supporting directed/undirected, weighted, and hidden states.

**State changes supported**:
- Per-node state (idle, current, done, error, highlight, hidden)
- Per-edge state (same palette)
- Node/edge highlighting
- Structural mutations: add_edge, remove_edge, set_weight
- Annotation arrows between nodes

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Edge state change (e.g., idle to current) | Instant CSS class swap | **Edge traversal** — a colored pulse travels along the edge from source to destination node. Implemented as an SVG `<animate>` or WAAPI animation of a small circle/dot moving along the line path, 400ms `ease-in-out`. After the pulse arrives, the edge recolors. This is the single most impactful missing animation for graph algorithms (BFS/DFS). |
| Node state change | Instant CSS class swap | **Ripple fill** — the node circle fills radially from center outward using a radial `clip-path` animation, 250ms `ease-out`. For "current" state, add a brief ring pulse (a second circle that scales up and fades, 300ms). |
| Edge add (structural) | 180ms opacity fade | **Edge draw** — line draws from source to destination via `stroke-dashoffset`, 350ms `ease-out`. For directed graphs, the arrowhead appears at the end of the draw. |
| Edge remove (structural) | 180ms opacity fade | **Edge retract** — line erases from destination back to source (reverse dashoffset), 250ms. |
| Node weight/value change | Instant text swap | **Counter roll** — numeric weight ticks from old to new value, 200ms. |
| Set weight | Instant (no visual feedback) | **Weight label flash** — the weight label briefly scales up (1.0 to 1.3, then back), with the old value cross-fading to the new, 250ms. |
| Node relayout after edge mutation | 180ms translate | Current `position_move` is correct in principle but too fast for educational use. Increase to 400ms `ease-in-out` with slight overshoot easing (`cubic-bezier(0.34, 1.56, 0.64, 1)`) so the student sees nodes "settling." |

**Missing entirely**:
- **BFS wavefront**: When multiple nodes at the same BFS level change to "current" simultaneously, stagger them with 50ms delay per node, creating a visible expansion wavefront.
- **DFS backtrack**: When a node returns from "current" to "done," show a brief backward pulse along the edge that was used to reach it, 200ms.
- **Flow animation**: For network flow problems, animate flow along edges with a dashed-line animation (`stroke-dashoffset` cycling) whose speed is proportional to flow value.
- **Shortest path highlight**: Animated path trace from source to destination, edge-by-edge with 150ms per edge, showing the discovered shortest path.
- **Edge relaxation**: When an edge is "relaxed" in Dijkstra/Bellman-Ford, briefly show the old distance crossed out and the new distance appearing, with the relaxing edge pulsing.

---

### 4. Tree (`tree.py`)

**What it visualizes**: Rooted tree (Reingold-Tilford layout) supporting BSTs, segment trees, and sparse segment trees.

**State changes supported**:
- Per-node state, per-edge state
- Node value override (important for segment tree sum updates)
- Structural mutations: add_node, remove_node (with cascade), reparent
- Annotation arrows
- Hidden state for nodes and edges

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Node state change | Instant CSS class swap | **Depth-aware fill** — node fills with a radial clip-path (like Graph), but the fill color propagates downward through child edges with 80ms stagger per level, showing the "visiting subtree" semantics. |
| Node add | 180ms opacity fade | **Growth animation** — new node starts at parent position, then slides to its computed position via `position_move` (300ms `ease-out`). Simultaneously, the connecting edge draws from parent to new position. Sibling nodes reposition with 400ms smooth translate. |
| Node remove | 180ms opacity fade | **Shrink and collapse** — removed node shrinks (scale 1.0 to 0, 200ms), connecting edge retracts upward, then siblings/cousins slide into reclaimed space (400ms). |
| Reparent | Instant position swap | **Detach-float-reattach**: (1) Old edge fades/retracts (150ms). (2) Node floats to new position with a gentle arc path (400ms cubic-bezier). (3) New edge draws from new parent (200ms). (4) Affected nodes relayout (400ms). Total: ~800ms sequenced. |
| Segment tree update | Instant value swap | **Bottom-up propagation** — value change starts at the leaf, then propagates upward to ancestors with 100ms stagger per level. Each ancestor's value counter-animates from old sum to new sum. Edges along the update path pulse as the update flows upward. |
| Edge state change | Instant CSS class swap | **Edge glow** — 200ms color transition on the stroke, with a brief increased stroke-width pulse (1.5px to 3px to 2px). |

**Missing entirely**:
- **Traversal path visualization**: For DFS/BFS on trees, animate a "cursor" (highlighted ring) that moves from node to node following the traversal order, with edges briefly pulsing as they are traversed.
- **Rotation animation** (BST): For AVL/Red-Black tree rotations, animate the topological rearrangement: the rotating subtree pivots visually (nodes move along curved paths), making the rotation structure intuitive.
- **Subtree collapse/expand**: Animate subtrees folding into their root (accordion-style) or expanding outward, useful for showing recursive decomposition.

---

### 5. LinkedList (`linkedlist.py`)

**What it visualizes**: Singly-linked list as horizontal chain of two-part boxes (value + pointer) connected by directional arrows.

**State changes supported**:
- Per-node state
- Per-link state
- Insert (at index), remove (at index)
- Value override
- Annotation arrows

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Node insert | 180ms opacity fade-in | **Split and insert**: (1) Nodes after insertion point slide right 80px (300ms `ease-out`). (2) New node fades in at the gap (200ms). (3) Pointer arrows re-route: old arrow from predecessor fades (100ms), new arrow draws to inserted node (200ms), new arrow from inserted node draws to successor (200ms). Total: ~700ms sequenced. |
| Node remove | 180ms opacity fade-out | **Collapse and heal**: (1) Outgoing arrows from removed node fade (100ms). (2) Removed node shrinks/fades (200ms). (3) A new bypass arrow draws from predecessor to successor (200ms, dashed during draw, solid on completion). (4) Remaining nodes slide left to close gap (300ms). Total: ~600ms. |
| Link state change | Instant CSS class swap | **Arrow pulse** — a colored dot travels along the link arrow from source to destination, 300ms. Then the arrow recolors. This shows "traversing this pointer." |
| Node state change | Instant CSS class swap | **Box fill** — left-to-right wipe fill on the value half of the node box, 200ms. |
| Value change | Instant text swap | **Slot update** — old value slides up and fades out while new value slides in from below, 200ms. |

**Missing entirely**:
- **Pointer redirect animation**: When a pointer changes target (e.g., during reversal), the arrow should visually bend/curve from old target to new target over 300ms, rather than just appearing in the new configuration.
- **Traversal cursor**: A highlighted ring or arrow that slides along the list node-by-node, following the pointer chain, 200ms per hop.
- **Cycle detection visualization**: When a fast/slow pointer algorithm runs, show two cursors moving at different speeds along the list.

---

### 6. Queue (`queue.py`)

**What it visualizes**: Fixed-capacity horizontal FIFO with front/rear pointer arrows above cells.

**State changes supported**:
- Per-cell state
- Front/rear pointer state
- Enqueue (add at rear), dequeue (remove at front)
- Cell value override

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Enqueue | 180ms opacity fade (if structural) | **Slide-in from right**: (1) New value slides in from the right edge of the widget to the rear cell position (300ms `ease-out`). (2) Cell fills with "done" color (150ms). (3) Rear pointer slides one position right (200ms `ease-out`). Total: ~500ms sequenced. |
| Dequeue | 180ms opacity fade (if structural) | **Slide-out to left**: (1) Front cell value slides left and fades (200ms). (2) Cell empties (background returns to idle, 100ms). (3) Front pointer slides one position right (200ms). Total: ~400ms. |
| Pointer move | Not animated (pointer is re-rendered in new position) | **Smooth pointer slide** — the triangular pointer arrow translates horizontally from old cell to new cell, 250ms `ease-out`. This is critical: the pointer is the primary teaching element in queue visualizations. |
| Cell state change | Instant CSS class swap | **Fill transition** — 200ms background color interpolation. |

**Missing entirely**:
- **Circular queue wrapping**: When the rear pointer wraps around in a circular queue, animate the pointer arc from the last cell back to the first cell (curved path, 400ms).
- **Overflow/underflow indication**: When enqueue fails (full) or dequeue fails (empty), a brief red flash/shake animation on the relevant pointer (300ms).

---

### 7. Stack (`stack.py`)

**What it visualizes**: Variable-length LIFO rendered as a vertical column of cells with push/pop operations.

**State changes supported**:
- Per-item state
- "top" selector for the topmost item
- Push (add item), pop (remove N items)

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Push | 180ms opacity fade-in | **Drop-in from above**: (1) New item appears above the stack, slightly scaled up. (2) Drops down to the top position with gravity easing (`cubic-bezier(0.22, 1, 0.36, 1)`), 300ms. (3) Existing items shift down if needed (200ms). (4) Brief "landing" bounce (50ms overshoot). |
| Pop | 180ms opacity fade-out | **Lift-off**: (1) Top item lifts upward with deceleration (300ms `ease-in`). (2) Simultaneously fades out over the last 100ms. (3) Remaining items shift up to close gap (200ms). |
| Item state change | Instant CSS class swap | **Fill transition** with 200ms interpolation. |
| Top indicator | No visual indicator | **Top marker** — a small arrow or bracket indicator on the right side that slides to track the current top item (250ms `ease-out` on every push/pop). |

**Missing entirely**:
- **Stack frame visualization**: For recursive algorithm stacks, show the connection between a stack frame being pushed and the recursive call it represents (e.g., a line connecting the stack item to a CodePanel line).
- **Multi-pop cascade**: When popping N items, stagger the lift-off with 80ms delay between items (top first), creating a visual "unwinding" effect.

---

### 8. HashMap (`hashmap.py`)

**What it visualizes**: Bucket-based hash table with index column and entries column showing key:value pairs.

**State changes supported**:
- Per-bucket state
- Bucket value override (set entries text)
- Highlighting

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Bucket state change | Instant CSS class swap | **Row highlight sweep** — background color transitions left-to-right across the bucket row, 200ms. |
| Bucket value change | Instant text swap | **Entry append animation**: When a new key:value pair is added to a bucket's chain, the new pair slides in from the right (200ms) and the arrow from the previous entry draws to it (150ms). |
| Hash computation | No visual representation | **Hash path animation**: (1) The input key briefly appears above the table. (2) An animated arrow drops from the key down to the target bucket (300ms, with a brief "computation" wiggle at midpoint). (3) Target bucket highlights. Total: ~500ms. This is the core educational moment for hash tables. |

**Missing entirely**:
- **Collision chain growth**: Animate the chaining — when a collision occurs, the new entry appends to the existing chain with a visible link.
- **Rehash animation**: If the table resizes, show entries lifting out of old buckets and redistributing to new buckets (complex, ~2s, but very educational).
- **Probe sequence** (for open addressing): Animate the probe bouncing from bucket to bucket until it finds an empty slot.

---

### 9. Grid (`grid.py`)

**What it visualizes**: 2D rows x cols matrix of uniform cells, used for maze/pathfinding/game-of-life visualizations.

**State changes supported**:
- Per-cell state via `cell[r][c]`
- Per-cell value override
- Highlighting
- Annotation arrows

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Cell state change | Instant CSS class swap | **Fill transition** — 200ms color interpolation. For pathfinding "visited" states, use a radial expand from center (150ms). |
| Multiple cell changes (wavefront) | All instant, simultaneous | **BFS wavefront**: Cells changing to "current" state stagger outward from the source cell with distance-proportional delay (20ms per Manhattan distance unit), creating a visible expanding wavefront. This is the single most impactful animation for grid-based pathfinding. |
| Path highlight | Instant state changes | **Path trace**: Cells along the discovered path highlight sequentially from start to end, 60ms per cell, with a subtle connecting line drawing between cell centers. |
| Cell value change | Instant text swap | **Counter/fade** — same as Array. |

**Missing entirely**:
- **Obstacle placement**: When walls/obstacles are set, a brief "solidify" animation (darkening with a hard edge, 100ms).
- **A* frontier visualization**: Animate the priority queue frontier as a colored border that expands and contracts.
- **Flood fill**: Radial color spread from a source cell outward, with timing proportional to distance.

---

### 10. NumberLine (`numberline.py`)

**What it visualizes**: Horizontal axis with evenly spaced tick marks, used for binary search, range queries, and number theory.

**State changes supported**:
- Per-tick state
- Tick ranges
- Axis state
- Highlighting
- Annotation arrows

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Tick state change | Instant CSS class swap | **Tick pulse** — the tick mark briefly extends vertically (grows 50%, 150ms) while changing color, then settles to highlighted size. |
| Range highlight | Instant per-tick class swap | **Sweep** — a colored band sweeps along the axis from lo to hi, 30ms per tick. The band persists as a translucent overlay. |
| Binary search narrowing | Not specifically supported | **Range bracket** — animated brackets `[lo, hi]` that slide inward as the search narrows, 300ms per step. The eliminated range fades to a muted color. |

**Missing entirely**:
- **Sliding pointer**: An animated pointer/indicator that slides along the number line to a specific position (e.g., binary search midpoint), 250ms.
- **Interval visualization**: Animated brackets or braces that appear and resize to show intervals.

---

### 11. VariableWatch (`variablewatch.py`)

**What it visualizes**: Two-column table (name | value) displaying algorithm variable states.

**State changes supported**:
- Per-variable state
- Variable value override
- Highlighting

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Variable value change | Instant text swap | **Value transition**: (1) Old value slides up and fades (100ms). (2) New value slides in from below (100ms). (3) Row briefly flashes the "current" color (150ms) to draw attention. For numeric values, a counter roll-up from old to new (200ms). |
| Variable state change | Instant CSS class swap | **Row highlight** — 200ms color transition on the row background. |

**Missing entirely**:
- **Change indicator**: A brief delta annotation (e.g., "+3" or "5 -> 8") that appears beside the value and fades after 500ms.
- **Connection lines**: When a variable changes because of a specific cell/node operation, draw a brief animated line from the triggering element to the variable row (400ms, then fade).

---

### 12. CodePanel (`codepanel.py`)

**What it visualizes**: Monospace source code with line numbers and per-line state coloring. Shows which algorithm line is executing.

**State changes supported**:
- Per-line state (idle, current, done, error, highlight)

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Line state to "current" | Instant CSS class swap | **Execution indicator slide** — a left-border highlight bar slides from the previous "current" line to the new one (200ms `ease-out`). The line background transitions color over 150ms. |
| Line state to "done" | Instant CSS class swap | **Fade to done** — 200ms color transition from "current" highlight to muted "done" tint. |
| Multiple lines change | All simultaneous | **Sequential execution feel** — if the current line advances by 1, animate the indicator sliding down. If it jumps (e.g., function call or loop restart), use a faster "teleport" (100ms with a brief flash at the destination). |

**Missing entirely**:
- **Breakpoint pulse**: A pulsing red dot on "error" state lines.
- **Loop iteration counter**: A small badge showing iteration count when the same line becomes "current" repeatedly.
- **Call/return arrows**: When execution jumps to a distant line (function call), draw a brief curved arrow from the call site to the function entry, then back on return.

---

### 13. MetricPlot (`metricplot.py`)

**What it visualizes**: Line chart tracking one or more scalar series across animation frames.

**State changes supported**:
- Append data points to series (via apply_command)
- Up to 8 series with distinct colors and dash patterns
- Auto-scaling axes

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| New data point added | Full SVG re-render (no animation) | **Line extension** — the polyline path extends to the new point with a `stroke-dashoffset` draw animation (200ms). The new point dot scales up from 0 (150ms `ease-out`). |
| Axis rescale | Instant full re-render | **Smooth rescale** — all existing points and axis labels interpolate to new positions (300ms `ease-in-out`). This preserves spatial continuity. |
| Multiple series update | Instant full re-render | **Staggered draw** — each series extends its line with 50ms stagger between series. |

**Missing entirely**:
- **Hover/focus data point**: On the current step's data point, show a tooltip-like annotation with the exact value (static, no animation needed, but currently absent).
- **Convergence indicator**: When a series levels off (derivative approaches 0), a subtle horizontal reference line fades in.
- **Threshold line**: An animated horizontal line at a target value that appears when the series first crosses it.

---

### 14. Matrix / Heatmap (`matrix.py`)

**What it visualizes**: Dense 2D grid with viridis colorscale mapping, used for attention matrices, distance matrices, correlation heatmaps.

**State changes supported**:
- Per-cell state
- Per-cell value override
- Colorscale interpolation (viridis)
- Cell highlighting

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Cell color change (via value) | Instant color swap | **Smooth color interpolation** — the cell's fill color transitions from old viridis value to new viridis value over 250ms. This is a pure CSS transition on the `fill` attribute. |
| Cell state change | Instant CSS class swap | **Border highlight** — 200ms transition. The viridis fill should remain (it carries data meaning); only the border/outline should change to indicate state. |
| Row/column scan | Instant simultaneous changes | **Sequential sweep** — cells in a row or column update with 15ms stagger, creating a visible scan pattern. |
| Full matrix update | Instant full re-render | **Heat diffusion** — cells interpolate from old colors to new colors over 300ms, creating a smooth "temperature change" effect. |

**Missing entirely**:
- **Attention beam**: For attention matrix visualizations, an animated line connecting the query token (row) to the key token (column) with thickness proportional to attention weight.
- **Row/column highlight band**: A translucent colored band that sweeps across a row or column when it is being computed.
- **Colorscale legend animation**: When the data range changes, the legend bar smoothly rescales.

---

### 15. Plane2D (`plane2d.py`)

**What it visualizes**: 2D coordinate plane with points, lines, segments, polygons, and shaded regions in math coordinates.

**State changes supported**:
- Per-element state (point, line, segment, polygon, region)
- Dynamic add/remove for all element types (with tombstone semantics)
- Annotation arrows

| State Change | Current Animation | Ideal Educational Animation |
|---|---|---|
| Point add | 180ms opacity fade | **Point pop** — point scales from 0 to 1.0 with slight overshoot (`cubic-bezier(0.34, 1.56, 0.64, 1)`), 200ms. |
| Point remove | 180ms opacity fade | **Point shrink** — scale from 1.0 to 0, 150ms `ease-in`. |
| Line add | 180ms opacity fade | **Line draw** — `stroke-dashoffset` animation across the viewport, 400ms `ease-out`. |
| Segment add | 180ms opacity fade | **Segment draw** — `stroke-dashoffset` from start point to end point, 300ms. |
| Polygon add | 180ms opacity fade | **Edge-by-edge draw** — each polygon edge draws sequentially (100ms per edge), then the fill fades in (150ms). |
| Region add | 180ms opacity fade | **Fill flood** — the shaded region expands from a seed point (or from the boundary inward) via `clip-path` animation, 300ms. |
| Point/line state change | Instant CSS class swap | **Color transition** — 200ms fill/stroke color interpolation. |
| Element remove (tombstone) | 180ms opacity fade | **Dissolve** — element fades with a slight shrink/retract (200ms). |

**Missing entirely**:
- **Sweep line**: An animated vertical or horizontal line that sweeps across the plane, critical for computational geometry algorithms (line sweep, plane sweep). 500ms for full traverse, with events highlighted as the line crosses them.
- **Convex hull construction**: Animated hull edges drawing sequentially as the algorithm discovers them.
- **Point movement**: Smooth translation of a point from one coordinate to another (for iterative algorithms like gradient descent). Currently requires remove + add, losing visual continuity.
- **Intersection highlight**: When two lines/segments intersect, a brief pulse/ring at the intersection point (200ms).
- **Rotation/transformation**: Animated geometric transforms (rotation, scaling, shearing) applied to polygons/point sets.

---

## Cross-Cutting Gaps (Affect All Primitives)

### 1. Transition Sequencing

**Current**: All transitions within a frame advance fire simultaneously.
**Needed**: An ordered sequence with dependencies. Example for a DP step: draw arrow (0-350ms) -> fill cell (350-550ms) -> update value (550-700ms). This requires a `sequence` or `timeline` concept in the transition manifest.

**Proposed data model**:
```
Transition gains: group: int (execution order), delay_ms: int (offset within group)
```

### 2. Interpolated Color Transitions

**Current**: `recolor` is an instant CSS class swap.
**Needed**: CSS `transition` declarations on `.scriba-state-*` classes, e.g.:
```css
[data-primitive] rect,
[data-primitive] circle {
  transition: fill 200ms ease-out, stroke 200ms ease-out;
}
```
This single CSS addition would make every `recolor` transition across all primitives visually smooth with zero JS changes.

### 3. Value Change Animation

**Current**: Instant `textContent` swap.
**Needed**: At minimum, a brief cross-fade (opacity 1 to 0 to 1 on the `<text>` element, 150ms total). At best, a counter roll-up for numeric values.

### 4. Configurable Duration

**Current**: Hardcoded `DUR=180` for everything.
**Needed**: Per-kind or per-primitive duration overrides. Educational animations need different timings — a cell fill should be faster than an edge traversal. Proposed: a duration map in the JS runtime, keyed by `kind`.

### 5. Stagger/Cascade Animations

**Current**: No concept of staggering.
**Needed**: When N elements change to the same state in a single frame, stagger them with a configurable per-element delay. Essential for BFS wavefronts, DP wavefront fills, and sweep-line algorithms.

### 6. Reduced Motion Degradation

**Current**: `prefers-reduced-motion: reduce` disables ALL WAAPI animations, falling back to instant swaps.
**Needed**: A graceful degradation where reduced-motion users still get short cross-fades (under 100ms, no spatial motion) instead of jarring instant swaps.

### 7. Easing Variety

**Current**: Only `ease-in` (add) and `ease-out` (remove) are used.
**Needed**: Easing should match the semantic intent:
- `ease-out` (decelerate) for elements arriving (natural "landing")
- `ease-in` (accelerate) for elements departing (natural "launch")
- `ease-in-out` for positional moves (smooth start and stop)
- Spring easing (`cubic-bezier(0.34, 1.56, 0.64, 1)`) for attention-grabbing pop-ins
- Linear for uniform-speed effects (sweep lines, traversal pulses)

---

## Priority Ranking

Ranked by educational impact vs implementation complexity:

| Priority | Gap | Impact | Complexity | Primitives Affected |
|----------|-----|--------|------------|-------------------|
| P0 | CSS color transitions on recolor | Very High | Very Low | All 15 |
| P0 | Value change cross-fade | High | Low | All with text |
| P1 | Transition sequencing in manifest | Very High | Medium | All |
| P1 | Edge/arrow traversal pulse (Graph, Tree) | Very High | Medium | Graph, Tree, LinkedList |
| P1 | Stroke-dashoffset arrow draw (annotations) | High | Low-Medium | DPTable, Graph, Tree, all with arrows |
| P2 | Stagger/cascade for wavefront effects | High | Medium | Grid, DPTable (2D), Graph (BFS) |
| P2 | Pointer slide animation (Queue, Array) | Medium | Low | Queue, Stack, Array |
| P2 | Structural mutation choreography (insert/remove) | High | High | LinkedList, Tree, Stack, Queue |
| P3 | Counter roll-up for numeric values | Medium | Medium | DPTable, VariableWatch, Matrix |
| P3 | MetricPlot line extension | Medium | Medium | MetricPlot |
| P3 | Sweep line for Plane2D | Medium | Medium | Plane2D |
| P4 | Complex choreography (rotation, rehash, recurrence overlay) | High | Very High | Tree (rotation), HashMap (rehash), DPTable (recurrence) |

---

## Appendix: State Palette (shared across all primitives)

All primitives share the same state names, mapped to colors via `svg_style_attrs()` in `base.py`:

| State | Semantics | Fill | Text | Stroke |
|-------|-----------|------|------|--------|
| `idle` | Default/untouched | light gray | dark | gray |
| `current` | Currently being processed | blue | white | blue |
| `done` | Completed/visited | green | white | green |
| `error` | Error/invalid | red | white | red |
| `highlight` | Attention (promoted from highlighted flag) | yellow | dark | yellow |
| `hidden` | Not rendered | n/a | n/a | n/a |

The `highlight` state was redesigned in the beta wave to be a full state rather than a dashed overlay, so it competes with other states (current/done/error take precedence when both are set).
