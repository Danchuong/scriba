# Transition Taxonomy for Scriba Algorithm Animations

Catalog of every visual transition Scriba needs when animating step N to step N+1. Currently each step renders as a static SVG frame; these specifications define how to interpolate between frames so that clicking "Next" produces smooth, readable motion instead of a hard snap.

Throughout this document, **duration** is the base value at 1x playback speed. See the Timing Model section for the speed multiplier table.

---

## 1. Color Transitions

### 1.1 Fill Morph

| Field | Value |
|---|---|
| **Description** | Background fill of a rect or circle transitions between state colors (e.g. idle `#f8f9fa` to current `#0090ff`). |
| **Primitives** | Array, Grid, DPTable, Stack, Queue, Matrix, HashTable, LinkedList |
| **SVG properties** | `fill` on `<rect>` or `<circle>` child of `<g data-target>` |
| **Duration** | 180 ms |
| **Easing** | `ease-out` (`cubic-bezier(0, 0, 0.58, 1)`) |
| **Composition** | Parallel with stroke morph, text fill morph, and halo morph (they form a state-change bundle; see 4.1) |
| **Reduced-motion** | Instant snap (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- before (idle) -->
<rect x="1" y="1" width="44" height="44" fill="#f8f9fa" stroke="#dfe3e6" stroke-width="1"/>

<!-- after (current) -->
<rect x="1" y="1" width="44" height="44" fill="#0090ff" stroke="#0b68cb" stroke-width="2"/>
```

### 1.2 Stroke Morph

| Field | Value |
|---|---|
| **Description** | Border stroke color and width change to signal a state transition. Signal states use `stroke-width: 2` (the `--scriba-cell-stroke-width-signal` token); non-signal states use `1`. Both color and width interpolate together. |
| **Primitives** | Array, Grid, DPTable, Stack, Queue, Matrix, HashTable, LinkedList, Graph (circle), Tree (circle) |
| **SVG properties** | `stroke`, `stroke-width` on `<rect>` or `<circle>` |
| **Duration** | 180 ms |
| **Easing** | `ease-out` |
| **Composition** | Parallel with fill morph (same bundle) |
| **Reduced-motion** | Instant snap (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- idle -->
<rect stroke="#dfe3e6" stroke-width="1" .../>

<!-- current -->
<rect stroke="#0b68cb" stroke-width="2" .../>
```

### 1.3 Text Fill Morph

| Field | Value |
|---|---|
| **Description** | Text color changes to match state (e.g. idle `#11181c` to current `#ffffff`). |
| **Primitives** | All primitives that render `<text>` inside state groups |
| **SVG properties** | `fill` on `<text>` |
| **Duration** | 180 ms |
| **Easing** | `ease-out` |
| **Composition** | Parallel with fill morph (same bundle) |
| **Reduced-motion** | Instant snap (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- idle -->
<text fill="#11181c" x="23" y="23">5</text>

<!-- current -->
<text fill="#ffffff" x="23" y="23">5</text>
```

### 1.4 Opacity Fade (Dim State)

| Field | Value |
|---|---|
| **Description** | Element fades to 50% opacity and desaturates to 30%. Used when entering the `dim` state. The CSS rule applies `opacity: 0.5; filter: saturate(0.3)` on the whole `<g>` wrapper. |
| **Primitives** | All primitives (applied at the `<g data-target>` level via `.scriba-state-dim`) |
| **SVG/CSS properties** | `opacity` (1 to 0.5), `filter: saturate()` (1 to 0.3) |
| **Duration** | 200 ms |
| **Easing** | `linear` (opacity perceives linear as natural) |
| **Composition** | Parallel with fill/stroke/text morph if the state also changes color tokens |
| **Reduced-motion** | Instant snap to final opacity and saturation (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- before (idle, full opacity) -->
<g data-target="a.cell[3]" class="scriba-state-idle" style="opacity:1; filter:saturate(1)">
  <rect fill="#f8f9fa" stroke="#dfe3e6" .../>
  <text fill="#11181c">7</text>
</g>

<!-- after (dim) -->
<g data-target="a.cell[3]" class="scriba-state-dim" style="opacity:0.5; filter:saturate(0.3)">
  <rect fill="#f1f3f5" stroke="#e6e8eb" .../>
  <text fill="#687076">7</text>
</g>
```

### 1.5 Halo Color Morph

| Field | Value |
|---|---|
| **Description** | The CSS text halo (`paint-order: stroke fill` with `--scriba-halo`) changes color to match the new state's fill. This keeps text readable against any background. The halo stroke color must animate in sync with the rect fill so the halo never mismatches the background mid-transition. |
| **Primitives** | Graph (node text, 4 px halo), Tree (node text, 4 px halo), Array/Grid/DPTable (cell text, 3 px halo) |
| **SVG/CSS properties** | `stroke` on `<text>` (via CSS `paint-order: stroke fill`), driven by `--scriba-halo` custom property |
| **Duration** | 180 ms (must match fill morph exactly) |
| **Easing** | `ease-out` (must match fill morph exactly) |
| **Composition** | Must run simultaneously with fill morph; zero offset. They share a single CSS `transition` shorthand. |
| **Reduced-motion** | Instant snap (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- idle: halo matches idle fill -->
<text fill="#11181c" stroke="#f8f9fa" stroke-width="3" paint-order="stroke fill">5</text>

<!-- current: halo matches current fill -->
<text fill="#ffffff" stroke="#0090ff" stroke-width="3" paint-order="stroke fill">5</text>
```

---

## 2. Geometry Transitions

### 2.1 Node Position Lerp

| Field | Value |
|---|---|
| **Description** | A Graph node moves to a new position after the force-directed layout recalculates (e.g. after `add_edge`). The node's `<g transform="translate(cx, cy)">` wrapper interpolates from old (cx, cy) to new (cx, cy). Connected edges follow. |
| **Primitives** | Graph |
| **SVG properties** | `transform: translate(cx, cy)` on the node `<g>`, plus `x1,y1,x2,y2` on connected `<line>` edges |
| **Duration** | 300 ms |
| **Easing** | `ease-in-out` (`cubic-bezier(0.42, 0, 0.58, 1)`) for natural deceleration |
| **Composition** | All moving nodes animate in parallel. Connected edges update in parallel with their endpoints. |
| **Reduced-motion** | Instant teleport to final position (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- before: node at (100, 80) -->
<g data-target="g.node[A]" transform="translate(100, 80)">
  <circle r="20" .../>
  <text>A</text>
</g>

<!-- after: node at (160, 120) -->
<g data-target="g.node[A]" transform="translate(160, 120)">
  <circle r="20" .../>
  <text>A</text>
</g>
```

### 2.2 Tree Subtree Migration

| Field | Value |
|---|---|
| **Description** | A node is reparented (e.g. BST rotation or delete-and-reattach). The entire subtree rooted at the moved node slides from old Reingold-Tilford coordinates to new ones. Each node in the subtree gets its own translate interpolation so the motion is rigid-body-like. |
| **Primitives** | Tree |
| **SVG properties** | `transform: translate(cx, cy)` on each node `<g>` in the subtree; `x1,y1,x2,y2` on parent-child `<line>` edges |
| **Duration** | 350 ms |
| **Easing** | `ease-in-out` |
| **Composition** | All nodes in the subtree move in parallel. Old parent edge fades out (see 2.4) while new parent edge draws in (see 2.3), both in parallel with the position animation. |
| **Reduced-motion** | Instant teleport (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- before: node 7 at (200, 120), child of node 10 -->
<line x1="250" y1="60" x2="200" y2="120" stroke="#c1c8cd"/>
<g data-target="t.node[7]" transform="translate(200, 120)">
  <circle r="20" .../>
</g>

<!-- after: node 7 at (120, 120), child of node 5 -->
<line x1="100" y1="60" x2="120" y2="120" stroke="#c1c8cd"/>
<g data-target="t.node[7]" transform="translate(120, 120)">
  <circle r="20" .../>
</g>
```

### 2.3 Edge Draw-In

| Field | Value |
|---|---|
| **Description** | A new edge appears by animating `stroke-dashoffset` from the full path length down to 0, creating a "drawing" effect from source to target. The edge `<line>` or `<path>` starts fully dashed (invisible) and progressively reveals. |
| **Primitives** | Graph, Tree |
| **SVG properties** | `stroke-dasharray` (set to path length), `stroke-dashoffset` (path length to 0) |
| **Duration** | 250 ms |
| **Easing** | `ease-out` |
| **Composition** | Can run in parallel with node position lerp. If a node is also appearing (e.g. BST insert), the node scale-in should lead by 50 ms so the user sees the node before the edge reaches it. |
| **Reduced-motion** | Instant appear (0 ms, edge is immediately fully visible) |

**Before/after SVG snippet:**

```xml
<!-- t=0: edge invisible -->
<line x1="100" y1="60" x2="200" y2="120" stroke="#c1c8cd" stroke-width="1.5"
      stroke-dasharray="140" stroke-dashoffset="140"/>

<!-- t=250ms: edge fully drawn -->
<line x1="100" y1="60" x2="200" y2="120" stroke="#c1c8cd" stroke-width="1.5"
      stroke-dasharray="140" stroke-dashoffset="0"/>
```

### 2.4 Edge Removal

| Field | Value |
|---|---|
| **Description** | An existing edge disappears. Two strategies depending on context: (a) **Fade out** for deletion/disconnect -- opacity goes from 1 to 0. (b) **Retract** for reparent -- stroke-dashoffset animates from 0 back to the full path length, reversing the draw-in. |
| **Primitives** | Graph, Tree |
| **SVG properties** | `opacity` (fade variant) or `stroke-dashoffset` (retract variant) |
| **Duration** | 200 ms (fade), 200 ms (retract) |
| **Easing** | `ease-in` for fade (accelerating disappearance feels intentional); `ease-in` for retract |
| **Composition** | Runs in parallel with other geometry transitions. For reparent, the old edge retracts while the new edge draws in simultaneously. |
| **Reduced-motion** | Instant disappear (0 ms) |

**Before/after SVG snippet (fade variant):**

```xml
<!-- t=0: visible -->
<line x1="100" y1="60" x2="200" y2="120" stroke="#c1c8cd" opacity="1"/>

<!-- t=200ms: gone -->
<line x1="100" y1="60" x2="200" y2="120" stroke="#c1c8cd" opacity="0"/>
```

### 2.5 Point Appear (Plane2D)

| Field | Value |
|---|---|
| **Description** | A new point on the coordinate plane scales from radius 0 to the target `_POINT_RADIUS` (4 px in math-space). Uses `transform: scale()` on the `<circle>` for compositor-friendly animation. |
| **Primitives** | Plane2D |
| **SVG properties** | `r` (logical) via `transform: scale(0)` to `scale(1)` on the circle, or direct `r` interpolation from 0 to 4 |
| **Duration** | 150 ms |
| **Easing** | `ease-out` with slight overshoot: `cubic-bezier(0.34, 1.56, 0.64, 1)` -- the point "pops" into existence |
| **Composition** | Multiple points appearing in the same step animate in parallel (no stagger needed for Plane2D since points are spatially separated). |
| **Reduced-motion** | Instant appear at final size (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- t=0 -->
<circle cx="120" cy="80" r="4" fill="#0090ff" transform="scale(0)" transform-origin="120 80"/>

<!-- t=150ms -->
<circle cx="120" cy="80" r="4" fill="#0090ff" transform="scale(1)" transform-origin="120 80"/>
```

### 2.6 Line Sweep (Plane2D)

| Field | Value |
|---|---|
| **Description** | A new line on the coordinate plane draws in from one endpoint to the other using `stroke-dashoffset`, identical technique to edge draw-in but for infinite lines clipped to the viewport. |
| **Primitives** | Plane2D |
| **SVG properties** | `stroke-dasharray`, `stroke-dashoffset` |
| **Duration** | 300 ms |
| **Easing** | `ease-out` |
| **Composition** | Parallel with point appear if both happen in the same step. |
| **Reduced-motion** | Instant appear (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- t=0: line invisible -->
<line x1="32" y1="200" x2="368" y2="50" stroke="#0090ff" stroke-width="1.5"
      stroke-dasharray="380" stroke-dashoffset="380"/>

<!-- t=300ms: line fully visible -->
<line x1="32" y1="200" x2="368" y2="50" stroke="#0090ff" stroke-width="1.5"
      stroke-dasharray="380" stroke-dashoffset="0"/>
```

### 2.7 Cell Scale Pulse

| Field | Value |
|---|---|
| **Description** | A highlight ring effect on an Array cell. The `<g>` wrapper briefly scales from 1.0 to 1.04 and back to 1.0, drawing the eye without displacing neighbors. This is a fire-and-forget animation that plays once, not a persistent transform. |
| **Primitives** | Array (highlight state) |
| **SVG properties** | `transform: scale()` on the `<g data-target>` wrapper, with `transform-origin` set to the cell center |
| **Duration** | 250 ms total (120 ms up, 130 ms down) |
| **Easing** | Up: `ease-out`; Down: `ease-in-out` |
| **Composition** | Runs in parallel with the fill/stroke state change that triggers the highlight. |
| **Reduced-motion** | Omit entirely (no scale change) |

**Before/after SVG snippet:**

```xml
<!-- t=0: normal scale -->
<g data-target="a.cell[2]" transform="scale(1)" transform-origin="92 23">...</g>

<!-- t=120ms: peak -->
<g data-target="a.cell[2]" transform="scale(1.04)" transform-origin="92 23">...</g>

<!-- t=250ms: settled -->
<g data-target="a.cell[2]" transform="scale(1)" transform-origin="92 23">...</g>
```

---

## 3. Content Transitions

### 3.1 Value Crossfade

| Field | Value |
|---|---|
| **Description** | A cell's displayed value changes (e.g. `"?"` to `"4"`). The old text fades out while the new text fades in, both centered at the same position. Uses two overlapping `<text>` elements with opposing opacity animations. |
| **Primitives** | Array, DPTable, Grid, Matrix, Stack, Queue |
| **SVG properties** | `opacity` on two `<text>` elements (old: 1 to 0, new: 0 to 1) |
| **Duration** | 160 ms |
| **Easing** | `linear` |
| **Composition** | Runs in parallel with any state color change on the same cell. The crossfade is independent of fill/stroke transitions. |
| **Reduced-motion** | Instant swap (old text replaced by new text, 0 ms) |

**Before/after SVG snippet:**

```xml
<!-- t=0 -->
<text fill="#11181c" x="23" y="23" opacity="1">?</text>
<text fill="#11181c" x="23" y="23" opacity="0">4</text>

<!-- t=80ms (midpoint, both half-visible) -->
<text fill="#11181c" x="23" y="23" opacity="0.5">?</text>
<text fill="#11181c" x="23" y="23" opacity="0.5">4</text>

<!-- t=160ms -->
<text fill="#11181c" x="23" y="23" opacity="0">?</text>
<text fill="#11181c" x="23" y="23" opacity="1">4</text>
```

### 3.2 Value Counter

| Field | Value |
|---|---|
| **Description** | A numeric value visually increments or decrements through intermediate integers (e.g. 0, 1, 2, 3, 4). The text content updates at fixed intervals. This is an optional advanced effect suitable for counters, DP table fills, and metric displays. |
| **Primitives** | DPTable, MetricPlot, VariableWatch (optional, only when delta is small: abs(new - old) <= 20) |
| **SVG properties** | Text content (not a CSS property; requires JS to update the `<text>` textContent at each tick) |
| **Duration** | 200 ms total, ticks evenly spaced (e.g. 5 steps = 40 ms per tick) |
| **Easing** | `ease-out` on tick spacing (early ticks faster, final ticks slower) |
| **Composition** | Runs in parallel with state color changes. |
| **Reduced-motion** | Instant final value (0 ms, no intermediate numbers) |

**Pseudocode (not SVG):**

```
tick 0 (0ms):   textContent = "0"
tick 1 (30ms):  textContent = "1"
tick 2 (70ms):  textContent = "2"
tick 3 (120ms): textContent = "3"
tick 4 (200ms): textContent = "4"
```

### 3.3 Label Appear

| Field | Value |
|---|---|
| **Description** | An annotation label (e.g. "i", "lo", "hi", "min") fades in below or above an Array cell. Uses opacity animation on the annotation `<text>` element. |
| **Primitives** | Array (annotations), DPTable (annotations) |
| **SVG properties** | `opacity` (0 to 1) on `<text>` |
| **Duration** | 150 ms |
| **Easing** | `ease-out` |
| **Composition** | Parallel with state changes on the same cell. If multiple labels appear, they all animate simultaneously (no stagger). |
| **Reduced-motion** | Instant appear (0 ms) |

**Before/after SVG snippet:**

```xml
<!-- t=0 -->
<text x="23" y="60" fill="#0b68cb" font-size="11" opacity="0">i</text>

<!-- t=150ms -->
<text x="23" y="60" fill="#0b68cb" font-size="11" opacity="1">i</text>
```

### 3.4 Arrow Draw

| Field | Value |
|---|---|
| **Description** | An annotation arrow (cubic Bezier path) draws along its curve from the source cell to the target cell, using the same `stroke-dashoffset` technique as edge draw-in. The arrowhead marker appears at the end of the draw. |
| **Primitives** | Array (Bezier annotation arrows, e.g. DP transitions) |
| **SVG properties** | `stroke-dasharray`, `stroke-dashoffset` on `<path>`; `opacity` on the `<marker>` arrowhead (0 to 1 at 80% of the draw duration) |
| **Duration** | 250 ms (path draw), arrowhead appears at t=200 ms |
| **Easing** | `ease-out` for path; `ease-out` for arrowhead fade |
| **Composition** | Parallel with other annotations appearing in the same step. Sequential after the state change that triggers the annotation. |
| **Reduced-motion** | Instant appear (0 ms, full path and arrowhead visible immediately) |

**Before/after SVG snippet:**

```xml
<!-- t=0 -->
<path d="M 23,0 C 23,-30 115,-30 115,0" stroke="#059669" stroke-width="2.2"
      fill="none" marker-end="url(#scriba-arrow-good)"
      stroke-dasharray="160" stroke-dashoffset="160"/>

<!-- t=250ms -->
<path d="M 23,0 C 23,-30 115,-30 115,0" stroke="#059669" stroke-width="2.2"
      fill="none" marker-end="url(#scriba-arrow-good)"
      stroke-dasharray="160" stroke-dashoffset="0"/>
```

---

## 4. Composite Transitions

### 4.1 State Change Bundle

| Field | Value |
|---|---|
| **Description** | When a cell transitions from one state to another (e.g. `idle` to `current`), fill, stroke, stroke-width, text fill, and halo all change. These MUST animate as a single 180 ms transition, not as separate sequential animations. A single CSS `transition` shorthand on the `<g>` covers all properties at once. |
| **Properties in bundle** | `fill`, `stroke`, `stroke-width`, `text fill`, `paint-order stroke color` |
| **Duration** | 180 ms |
| **Easing** | `ease-out` (uniform across all properties in the bundle) |

**CSS implementation:**

```css
.scriba-state-idle > rect,
.scriba-state-current > rect,
.scriba-state-done > rect,
.scriba-state-dim > rect,
.scriba-state-error > rect,
.scriba-state-good > rect,
.scriba-state-highlight > rect {
  transition: fill 180ms ease-out,
              stroke 180ms ease-out,
              stroke-width 180ms ease-out;
}

[data-primitive] text {
  transition: fill 180ms ease-out,
              stroke 180ms ease-out;
}

.scriba-state-dim {
  transition: opacity 200ms linear,
              filter 200ms linear;
}
```

### 4.2 Multi-Cell Stagger

| Field | Value |
|---|---|
| **Description** | When a cursor sweeps across an array (e.g. marking cells [2..6] as `done`), the cells animate in sequence rather than simultaneously. Each cell's state-change bundle starts 40 ms after the previous cell. This creates a "wave" effect that communicates traversal direction. |
| **Stagger offset** | 40 ms per cell |
| **Max stagger** | Capped at 5 cells (200 ms total stagger). Beyond 5, all remaining cells start at 200 ms offset (batch). This prevents long arrays from producing multi-second animations. |
| **Total duration** | 180 ms (single cell transition) + min(N-1, 5) * 40 ms stagger |
| **Direction** | Stagger follows index order (low to high) by default. If the algorithm is scanning right-to-left, reverse the order. |
| **Composition** | Each cell's bundle is independent but time-offset. |
| **Reduced-motion** | All cells snap simultaneously (0 ms, no stagger) |

**Example: 4-cell stagger (cells 2, 3, 4, 5 going idle to done):**

```
Cell 2: starts at t=0,    ends at t=180ms
Cell 3: starts at t=40ms, ends at t=220ms
Cell 4: starts at t=80ms, ends at t=260ms
Cell 5: starts at t=120ms,ends at t=300ms
Total frame time: 300ms
```

### 4.3 Frame Transition (Step N to Step N+1)

| Field | Value |
|---|---|
| **Description** | The complete orchestration of all transitions in a single step. This is the top-level timeline that the playback controller manages. |

**Phase ordering within a frame transition:**

| Phase | Content | Start | Typical Duration |
|---|---|---|---|
| **Phase 1: Exit** | Elements leaving (edge removal, label fade-out, old value fade-out) | t=0 | 0-200 ms |
| **Phase 2: Move** | Position changes (node lerp, subtree migration) | t=0 (parallel with Phase 1) | 0-350 ms |
| **Phase 3: Update** | State color changes (fill/stroke/text bundle), value crossfade | t=0 (parallel) | 180-300 ms (with stagger) |
| **Phase 4: Enter** | New elements (edge draw-in, point appear, label appear, arrow draw) | After Phase 2 settles, or t=100 ms, whichever is later | 150-250 ms |

**Total frame budget:**

| Scenario | Budget |
|---|---|
| Color-only step (most common) | 180-300 ms |
| Color + value change | 200-300 ms |
| Geometry + color | 350-450 ms |
| Complex (reparent + multi-cell stagger) | 400-500 ms |
| Hard cap | 500 ms (anything beyond feels sluggish) |

---

## 5. Timing Model

### 5.1 Duration Budget

| Transition category | Per-transition duration | Notes |
|---|---|---|
| Color (fill, stroke, text) | 180 ms | Fast enough to feel instant, slow enough to track |
| Opacity (dim, fade) | 200 ms | Linear easing; slightly longer because opacity changes are subtle |
| Position (node lerp) | 300 ms | Needs time for the eye to follow spatial movement |
| Subtree migration | 350 ms | Slightly longer than single-node to convey structural change |
| Draw-in (edge, line, arrow) | 250 ms | Enough to perceive the source-to-target direction |
| Scale (point appear, pulse) | 150-250 ms | Short; scale changes are immediately noticeable |
| Content (crossfade) | 160 ms | Fast swap; lingering overlap looks muddy |
| Content (counter) | 200 ms | Fixed budget regardless of delta magnitude |

### 5.2 Easing Library

| Easing | CSS value | Use for |
|---|---|---|
| `ease-out` | `cubic-bezier(0, 0, 0.58, 1)` | Color transitions, draw-in, label appear -- fast start, gentle stop |
| `ease-in-out` | `cubic-bezier(0.42, 0, 0.58, 1)` | Position movement -- smooth start and stop for spatial motion |
| `ease-in` | `cubic-bezier(0.42, 0, 1, 1)` | Exit animations (fade-out, retract) -- accelerating departure |
| `linear` | `cubic-bezier(0, 0, 1, 1)` | Opacity, desaturation -- perceptually even |
| `overshoot` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Point appear only -- playful pop |

### 5.3 Composition Rules

| Mode | When to use |
|---|---|
| **Parallel** (default) | Independent property changes on the same element (fill + stroke + text), or independent elements changing simultaneously |
| **Stagger** | Multiple cells undergoing the same state change in index order (see 4.2) |
| **Sequential** | Exit before enter (old edge retracts, then new edge draws in during reparent). Position settles before new children draw in. |
| **Lead/follow** | Node appears 50 ms before its incoming edge begins drawing |

### 5.4 Interruption Policy

When the user clicks "Next" while the current transition is still running:

| Strategy | Behavior |
|---|---|
| **Snap-to-end** (recommended) | All in-progress transitions immediately jump to their final values. The new step's transitions then begin from those final values. No queueing. |
| Rationale | Users who click quickly want speed, not animation. Queueing creates a backlog. Canceling loses the target state. Snap-to-end is the only strategy that keeps the visual state correct at all times. |

Implementation: on "Next" event, call `element.getAnimations().forEach(a => a.finish())` (Web Animations API) or set all transitioning properties to their target values and force a reflow.

Clicking "Previous" follows the same policy: snap current transitions to end, then begin the reverse step's transitions.

### 5.5 Speed Control

The user can select a playback speed multiplier. All durations are divided by the multiplier.

| Speed label | Multiplier | Effect on 180 ms transition |
|---|---|---|
| 0.5x (slow) | 0.5 | 360 ms |
| 1x (normal) | 1.0 | 180 ms |
| 1.5x (fast) | 1.5 | 120 ms |
| 2x (fastest) | 2.0 | 90 ms |

**Floor rule:** No transition should go below 60 ms regardless of speed multiplier, because sub-60 ms is imperceptible and creates visual glitches. Implementation: `max(baseDuration / speed, 60)`.

**Auto-play mode:** When auto-playing through steps, insert a pause of `max(400 / speed, 200)` ms between steps so the user can read the narration.

---

## 6. Reduced-Motion Fallbacks

For users with `prefers-reduced-motion: reduce`, all animated transitions are replaced with instant state changes. The mapping:

| Transition category | Normal behavior | Reduced-motion fallback |
|---|---|---|
| **Color** (fill, stroke, text, halo) | 180 ms ease-out interpolation | Instant snap (0 ms) |
| **Opacity** (dim, fade-in, fade-out) | 200 ms linear interpolation | Instant snap to final value (0 ms) |
| **Position** (node lerp, subtree) | 300-350 ms ease-in-out interpolation | Instant teleport to final position (0 ms) |
| **Draw-in** (edge, line, arrow) | 250 ms dashoffset animation | Instant appear at full length (0 ms) |
| **Scale** (point appear, cell pulse) | 150-250 ms scale animation | Instant final size; pulse omitted entirely |
| **Content crossfade** | 160 ms opacity crossfade | Instant text swap (0 ms) |
| **Content counter** | 200 ms tick sequence | Instant final value (0 ms) |
| **Multi-cell stagger** | 40 ms offset per cell | All cells change simultaneously (0 ms) |

**CSS implementation:**

```css
@media (prefers-reduced-motion: reduce) {
  [data-primitive] *,
  [data-primitive] {
    transition-duration: 0ms !important;
    animation-duration: 0ms !important;
  }
}
```

This single media query blankets all transitions. Individual JavaScript animations (value counter, dashoffset) must also check `window.matchMedia('(prefers-reduced-motion: reduce)').matches` and skip to the final state.

---

## 7. Summary Table

| # | Transition | Primitives | Properties | Duration | Easing | Reduced-motion |
|---|---|---|---|---|---|---|
| 1.1 | Fill morph | Array, Grid, DPTable, Stack, Queue, Matrix | `fill` | 180 ms | ease-out | 0 ms snap |
| 1.2 | Stroke morph | Same + Graph, Tree | `stroke`, `stroke-width` | 180 ms | ease-out | 0 ms snap |
| 1.3 | Text fill morph | All with `<text>` | `fill` on text | 180 ms | ease-out | 0 ms snap |
| 1.4 | Opacity fade | All (dim state) | `opacity`, `filter` | 200 ms | linear | 0 ms snap |
| 1.5 | Halo color morph | Graph, Tree, Array, Grid, DPTable | `stroke` on text | 180 ms | ease-out | 0 ms snap |
| 2.1 | Node position lerp | Graph | `transform` | 300 ms | ease-in-out | 0 ms teleport |
| 2.2 | Subtree migration | Tree | `transform`, edge coords | 350 ms | ease-in-out | 0 ms teleport |
| 2.3 | Edge draw-in | Graph, Tree | `stroke-dashoffset` | 250 ms | ease-out | 0 ms appear |
| 2.4 | Edge removal | Graph, Tree | `opacity` or `dashoffset` | 200 ms | ease-in | 0 ms disappear |
| 2.5 | Point appear | Plane2D | `transform: scale` | 150 ms | overshoot | 0 ms appear |
| 2.6 | Line sweep | Plane2D | `stroke-dashoffset` | 300 ms | ease-out | 0 ms appear |
| 2.7 | Cell scale pulse | Array | `transform: scale` | 250 ms | out/in-out | omit |
| 3.1 | Value crossfade | Array, DPTable, Grid, Matrix, Stack, Queue | `opacity` x2 | 160 ms | linear | 0 ms swap |
| 3.2 | Value counter | DPTable, MetricPlot, VariableWatch | textContent | 200 ms | ease-out ticks | 0 ms final |
| 3.3 | Label appear | Array, DPTable | `opacity` | 150 ms | ease-out | 0 ms appear |
| 3.4 | Arrow draw | Array | `stroke-dashoffset` | 250 ms | ease-out | 0 ms appear |
| 4.1 | State bundle | All | fill+stroke+text+halo | 180 ms | ease-out | 0 ms snap |
| 4.2 | Multi-cell stagger | Array, Grid, DPTable | per-cell offset | +40 ms/cell | -- | 0 ms all |
| 4.3 | Frame transition | All | orchestration | 180-500 ms | mixed | 0 ms all |
