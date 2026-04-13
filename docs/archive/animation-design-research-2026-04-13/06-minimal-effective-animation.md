# Minimal Effective Animation for Algorithm Visualizations

Date: 2026-04-13
Context: Scriba interactive algorithm editorial stepper

## Current Baseline

Scriba's JS runtime uses `DUR = 180` ms for all WAAPI animations. CSS provides
`transition: fill 180ms ease-out` on `[data-target] > rect`, `> circle`,
`> line`, `> text`. The result is that `recolor` transitions already animate
smoothly through CSS alone -- the JS just swaps a class name and the browser
interpolates the fill over 180ms.

Current transition kinds handled by JS:
- `recolor` -- CSS class swap (CSS transitions handle the visual)
- `value_change` -- instant textContent assignment
- `highlight_on/off` -- instant class toggle
- `element_add` / `annotation_add` -- 180ms opacity fade-in (WAAPI)
- `element_remove` / `annotation_remove` -- 180ms opacity fade-out (WAAPI)
- `position_move` -- 180ms translate (WAAPI)

This baseline is already solid. The question is what to add, what to leave
alone, and what would actively hurt the experience.

---

## Analysis of Each Proposed Animation

### 1. Arrow Draw-On (stroke-dashoffset) vs Simple Fade-In

**Current behavior:** Annotation arrows fade in via 180ms opacity WAAPI.

**The user complaint ("chua ve that su"):** The arrow appears but does not
visually communicate direction. A fade-in treats the arrow as a static
decoration, not a relationship indicator.

**Does draw-on add comprehension?** YES -- but only for arrows that represent
a causal link (e.g., "dp[i] depends on dp[j]", "edge (u,v) is being
traversed"). The draw-on encodes directionality: the line grows FROM source
TO destination. This is information, not decoration.

**Duration analysis:**
- 400-600ms: Too slow for interactive stepping. At 30 steps, that is 12-18
  seconds of draw-on time alone if the user clicks through quickly.
- 200ms: Barely registers as "drawing" -- looks like a glitchy fade.
- 120-150ms: The sweet spot. At 120ms, the eye can track a short path growing
  from left to right. Below 100ms, perceptual research (Card, Mackinlay &
  Shneiderman, 1999) shows the onset is fast enough that direction is lost --
  it just "appears."

**Alternative considered:** Staggered opacity (path body 80ms, arrowhead 50ms
delayed 80ms). This is clever but adds implementation complexity for a weaker
directional cue. The arrowhead appearing last hints at direction, but the eye
has to notice two separate opacity events in 130ms total. A stroke-dashoffset
draw-on is a single continuous motion the eye tracks naturally.

**Decision: YES -- animate arrows with stroke-dashoffset draw-on.**
- Duration: 120ms
- Easing: `ease-out` (fast start reads as decisive)
- Implementation: Set `stroke-dasharray` and `stroke-dashoffset` to path
  length on insertion, then animate `stroke-dashoffset` to 0 via WAAPI.
  Arrowhead marker opacity goes 0 to 1 at the 70% mark (84ms in).
- Fade-out on removal: Keep the existing 180ms opacity fade. No reverse
  draw-on needed -- removal is less informationally important.

---

### 2. Edge Traversal Dot vs Simple Edge Recolor

**Current behavior:** Edge recolors via CSS transition (180ms fill/stroke).

**Does the dot add comprehension?** NO for most cases. The edge recolor +
source/destination node state changes already encode "we traversed this edge."
The dot is a redundant encoding of the same information.

**Evidence from existing tools:**
- VisuAlgo at high speed: edges just recolor. No dot. Nobody reports confusion.
- D3 graph tutorials: dots are used for NETWORK FLOW where the quantity
  traveling matters. For simple graph traversal (BFS, DFS, Dijkstra), the
  recolor is sufficient.
- The dot adds value ONLY when the edge has a "weight" or "flow" that is
  being transferred -- and even then, a value label change at the destination
  conveys this more clearly than a moving dot.

**If kept anyway:** Minimum perceivable travel time for direction on a typical
Scriba edge (~80-120px) is about 80ms. Below that, the dot just "appears" at
the destination.

**Decision: NO -- do not add edge traversal dots.**
- The CSS 180ms recolor is sufficient.
- If a future algorithm genuinely needs flow visualization (network flow,
  max-flow/min-cut), revisit as a special-case annotation, not a default
  behavior.

---

### 3. Counter Roll-Up vs Instant Value Change

**Current behavior:** Instant textContent swap.

**Does counter animation add comprehension?** NO. The roll-up animates HOW a
number changes but the user already knows WHY from the narration text. For
DP tables where the transition is `inf -> 3`, a counter ticking through
intermediate values is meaningless -- there are no meaningful intermediate
values between infinity and 3.

Counter roll-ups are useful for:
- Scoreboards (sports, games) where the COUNT is the point
- Financial dashboards where delta perception matters
- Nowhere in algorithm visualization

**The attention problem is real though.** When a value changes in a grid of 20
cells, the user needs to notice WHICH cell changed. The current instant swap
provides zero visual cue.

**Decision: NO counter roll-up. YES to a scale pulse.**
- On value change: apply a brief CSS transform pulse via WAAPI.
- Keyframes: `scale(1) -> scale(1.15) -> scale(1)` on the `<text>` element.
- Duration: 100ms total (50ms up, 50ms down)
- Easing: `ease-out`
- This draws the eye to the changed cell without delaying progression.
  The pulse is technically a WAAPI animation but at 100ms it never blocks
  meaningful interaction.

---

### 4. Five-Phase Sequencing vs Simpler Grouping

**Proposed 5 phases (Signal, Connect, Compute, Result, Settle): ~1100ms total.**

This is the single biggest source of slowness. 1100ms per step means a
30-step algorithm takes 33 seconds of mandatory animation time even if the
user clicks as fast as possible. That is unacceptable for an interactive
stepper.

**How many phases does comprehension require?**

The cognitive model for one algorithm step is:
1. Something is highlighted/selected (CAUSE)
2. Something changes state (EFFECT)

That maps to two phases, not five. The user needs to see the cause before
the effect. Everything else (arrow draw-on, dim removal) is detail that
can overlap or follow.

**But even 2 explicit phases may be overkill.** Consider that Scriba's CSS
transitions already create implicit sequencing. When the JS applies all
transitions simultaneously:
- Recolors take 180ms (CSS transition)
- Arrow draw-on takes 120ms (proposed WAAPI)
- Value pulse takes 100ms (proposed WAAPI)
- Fades take 180ms (existing WAAPI)

These overlap naturally. The eye processes the fastest changes first and
the slower ones catch up. The implicit stagger from different durations
is usually enough.

**The one case where explicit ordering matters:** Annotations (arrows) should
appear BEFORE state changes they explain. If an arrow says "dp[3] = dp[1] + 2"
and then dp[3] turns green with value 3, the arrow should be visible when the
value changes. A 50ms delay is enough.

**Decision: 2 micro-phases, not 5.**
- Phase 1 (0ms): Fire all annotation_add (arrows) and highlight_on transitions.
  Arrows draw on over 120ms.
- Phase 2 (50ms delay): Fire all recolor, value_change, element_add,
  element_remove, highlight_off, and annotation_remove transitions.
- Total overhead per step: 50ms sequencing + max(120ms arrow, 180ms recolor)
  = ~230ms worst case. Most steps have fewer transition types and finish in
  ~180ms.
- Compared to 1100ms, this is a 79% reduction in animation time.

---

### 5. Staggered Wavefront vs Simultaneous

**Proposed: 30-40ms stagger per cell in a BFS wavefront.**

**Perceptual threshold for "wave" vs "simultaneous":**
Research on apparent motion (Wertheimer, 1912; modern replications) shows that
for spatial sequences, the minimum onset asynchrony to perceive sequential
ordering is approximately 20-30ms per element. Below 20ms, elements appear
simultaneous. Above 50ms, the wave is obvious but slow.

For a wavefront of 8 cells at 30ms stagger: 240ms added. At 40ms: 320ms added.

**Does the wave add comprehension?** MARGINALLY. BFS wavefronts are about
"all at the same distance" -- simultaneity is the actual semantic. A wave
contradicts that message by implying ordering among peers. The stagger is
eye candy, not pedagogy.

**The exception:** For algorithms where processing order within a level
matters (e.g., left-to-right relaxation in DP), a subtle stagger does encode
real information. But BFS wavefronts are the wrong place.

**Decision: NO stagger for wavefronts. Simultaneous recolor.**
- All cells in a wavefront recolor together via CSS transition (180ms).
- The simultaneous change correctly communicates "same distance."
- If a specific algorithm's DSL script needs ordered processing, the author
  should use separate steps, not implicit staggering.

---

### 6. Arc-Swap (Sorting) vs Instant Swap

**Does swap animation add comprehension?** YES. Sorting is the one domain
where the MOTION IS THE ALGORITHM. The whole point is watching elements
exchange positions. An instant swap loses the core visual metaphor.

**Duration analysis:**
- VisuAlgo sorting: ~200-300ms per swap at default speed.
- 400ms (proposed): Too slow when there are O(n^2) swaps.
- 150ms: Sufficient for the eye to track "A went left, B went right." The
  arc path helps because vertical displacement prevents the two elements
  from overlapping mid-transit.
- 100ms: Borderline. Works for small movements (adjacent elements) but
  long-distance swaps lose readability.

**Decision: YES -- animate swaps with arc paths.**
- Duration: 150ms
- Easing: `ease-in-out` (smooth start and landing)
- Path: quadratic bezier arc with peak height = 30% of horizontal distance,
  capped at 40px. This prevents excessive arcs on long swaps.
- Implementation: Two simultaneous WAAPI animations, one per element, each
  following its arc. Use `offset-path` if browser support allows, otherwise
  decompose into translate keyframes (3 points: start, arc peak, end).

---

### 7. The "Just CSS Transitions" Baseline

**Is the existing CSS baseline good enough for most state changes?** YES.

The CSS `transition: fill 180ms ease-out` on `[data-target] > rect` already
handles the most common operation (recolor) beautifully. The JS runtime does
not need to do anything for recolor except swap a class name. The browser's
compositor handles the interpolation on the GPU.

**What CSS cannot do (requires JS/WAAPI):**
- `stroke-dashoffset` triggered by element insertion (arrow draw-on)
- Position moves (translate between coordinates)
- Element insertion/removal (opacity fade on dynamically added DOM nodes)
- Scale pulse on value change (no CSS trigger for textContent change)
- Arc-swap paths (multi-keyframe motion)

**What CSS already handles well (leave it alone):**
- Fill/stroke recoloring on state change
- Stroke-width changes
- Opacity transitions on metricplot

**Decision: Do not add JS animation for anything CSS already handles.**
The 180ms CSS transition on recolor is the backbone of the system. Changing
it to a JS-driven animation would be slower (WAAPI has scheduling overhead),
harder to maintain, and no smoother.

---

### 8. What Scriba Should NOT Animate

**Do not animate these -- they waste time or hinder comprehension:**

1. **Narration text changes.** The narration panel swaps via innerHTML. Do not
   fade or slide narration text. Users read it; any animation delays reading.

2. **Step counter updates.** "Step 5 / 20" should change instantly. A counter
   roll-up on the step indicator is pure decoration.

3. **Dot indicator updates.** The navigation dots swap classes. No transition
   needed -- the active dot should just be active.

4. **Full-frame innerHTML syncs.** When `skip_animation` is true (>150
   transitions) or when the user jumps non-sequentially, the full SVG swap
   must be instant. No fade-through-white, no crossfade. Instant.

5. **Grid/axis lines.** Static structural elements should never animate.
   If a grid resizes, snap it.

6. **Labels that do not change.** Node labels ("A", "B", "C") in a graph
   should never pulse or fade when the node recolors. Only the fill/stroke
   should transition.

7. **Highlight toggling.** Adding/removing the `scriba-highlighted` class
   should remain instant. The highlight is an attention cue -- delaying it
   with a fade defeats the purpose.

8. **Reverse animations on "Previous" button.** When stepping backward, do
   NOT play transitions in reverse. Just snap to the previous frame state.
   Reverse animations confuse the mental model ("is the algorithm undoing
   work?").

---

## Concrete Recommendation Summary

| Transition Kind | Animate? | Technique | Duration | Easing |
|---|---|---|---|---|
| `recolor` | CSS only | CSS `transition: fill 180ms ease-out` (already exists) | 180ms | `ease-out` |
| `value_change` | YES (pulse) | WAAPI scale pulse on `<text>`: 1 -> 1.15 -> 1 | 100ms | `ease-out` |
| `highlight_on` | NO | Instant class add | 0ms | -- |
| `highlight_off` | NO | Instant class remove | 0ms | -- |
| `element_add` | YES | WAAPI opacity 0 -> 1 (keep current) | 180ms | `ease-in` |
| `element_remove` | YES | WAAPI opacity 1 -> 0 (keep current) | 180ms | `ease-out` |
| `annotation_add` (arrow) | YES | WAAPI stroke-dashoffset draw-on + marker fade | 120ms | `ease-out` |
| `annotation_add` (label) | YES | WAAPI opacity 0 -> 1 (same as element_add) | 180ms | `ease-in` |
| `annotation_remove` | YES | WAAPI opacity 1 -> 0 (keep current) | 180ms | `ease-out` |
| `annotation_recolor` | CSS only | CSS transition on stroke/fill | 180ms | `ease-out` |
| `position_move` | YES | WAAPI translate (keep current) | 180ms | `ease-out` |
| Arc-swap (sorting) | YES | WAAPI arc-path translate (2 elements) | 150ms | `ease-in-out` |
| Edge traversal dot | NO | CSS recolor is sufficient | -- | -- |
| Counter roll-up | NO | Use scale pulse instead | -- | -- |
| Wavefront stagger | NO | Simultaneous recolor via CSS | -- | -- |
| Narration text | NO | Instant innerHTML swap | 0ms | -- |
| Step backward | NO | Instant snapToFrame (no transitions) | 0ms | -- |

## Phase Sequencing Per Step

```
t=0ms    Phase 1: annotation_add (arrows begin draw-on, 120ms)
                  highlight_on (instant)

t=50ms   Phase 2: recolor (CSS handles 180ms)
                  value_change (instant text + 100ms pulse)
                  element_add/remove (180ms fade)
                  highlight_off (instant)
                  annotation_remove (180ms fade)

t~230ms  All animations complete. Ready for next step.
```

**Total animation budget per step: ~230ms worst case.**
Compare to the proposed 5-phase system at 1100ms. This is 4.8x faster while
retaining the one sequencing cue that matters (arrows appear before state
changes).

## Implementation Priority

1. **Arrow draw-on** (120ms stroke-dashoffset) -- addresses the "chua ve that su"
   feedback directly. Highest comprehension-per-millisecond ratio.
2. **Value change pulse** (100ms scale) -- cheap attention cue, zero blocking.
3. **2-phase sequencing** (50ms gap) -- small code change, big UX improvement
   over the 5-phase proposal.
4. **Arc-swap for sorting** -- only needed when sorting primitives ship.
   Defer until then.
5. Everything else: leave the current system alone. It works.
