# 05 -- Fast Interactive Animation Patterns

**Date**: 2026-04-13
**Context**: The 5-phase micro-sequence (1100ms/step) from reports 01--04 was designed for *video-paced* educational animation (Manim style). Scriba is an *interactive step-through widget* where the user clicks Next and expects near-instant feedback. This report corrects the timing model.

---

## 1. The Core Problem: Video Pace vs Interactive Pace

### Why 1100ms Feels Like Lag

The 1100ms 5-phase sequence was derived from Manim timing conventions and Mayer's multimedia learning research. Those sources assume **passive viewing** -- the animation plays at its own pace and the viewer watches. In that context, 1--2 seconds per step is appropriate because:

- The viewer has no control over pacing.
- The animation must be self-explanatory without interaction.
- There is no "I clicked something and nothing happened yet" frustration.

In an **interactive stepper**, the mental model is fundamentally different:

- The user initiates each step with a deliberate action (click/keypress).
- They already know something is *supposed* to happen.
- The delay between their action and visible response is perceived as **latency**, not **animation**.

### Nielsen Norman Group Response Time Thresholds

| Threshold | Perception | Source |
|-----------|-----------|--------|
| **100ms** | Feels instant. System responds to user action with no perceivable delay. | Miller 1968, Card et al. 1991, NN/g |
| **200--300ms** | Noticeable but smooth. User perceives motion, not delay. | NN/g, Material Design |
| **1000ms** | Limit of "flow". Beyond this, users feel they are *waiting*. | NN/g (Jakob Nielsen, 1993) |
| **10000ms** | Attention lost. Users switch context. | NN/g |

**1100ms per step puts Scriba right at the flow-breaking threshold.** Every click feels like a loading spinner, not a visualization.

### The Interactive Tool Standard

When a user clicks "Next" in a step-through tool:

- **Target**: The new visual state should be *recognizably present* within **200--350ms**.
- **Acceptable**: Up to **500ms** if the animation clearly communicates causality (A causes B).
- **Unacceptable**: >600ms before the user can tell what changed.

The key insight: the user's click *already provides the "signal" phase*. They don't need a 150ms "dim others / highlight source" phase because *they chose to advance*. The animation's job is to show *what changed*, not to set up context.

---

## 2. Interactive Tool Timing Analysis

### Visualgo (visualgo.net)

Visualgo is the gold standard for interactive algorithm visualization with speed control.

- **Speed slider**: Range from "slow" to "fast", mapped to roughly **50ms to 2000ms per action**.
- **Default speed**: Approximately **750ms per atomic action** (e.g., one comparison, one swap, one edge relaxation).
- **"Fast" setting**: ~200ms per action. Still perceivable but snappy.
- **"Fastest" setting**: ~50ms per action. Essentially auto-play; transitions blur together.
- **BFS step at default**: One vertex dequeue + neighbor examination = ~750ms. At fast = ~200ms.
- **User behavior**: Most returning users immediately slide to fast (200--400ms range). The slow end is for first-time learners.
- **Key pattern**: Visualgo uses a single-phase animation per action. There is no multi-phase "signal -> connect -> compute" sequence. One action = one visual change = one duration.

### USFCA Data Structure Visualizations (cs.usfca.edu/~galles)

- **Speed slider**: Range labeled "Animation Speed" from slow to fast.
- **Default**: ~400--500ms per operation.
- **Fast**: ~100ms per operation.
- **Instant**: Skip button jumps to end state with no animation.
- **Per-step timing**: Single-phase. A BST insert at default speed: node comparison highlight (instant class swap) + node movement to new position (~400ms translate).
- **Key pattern**: Color changes are *instant* (CSS class swap, no transition). Movement is the only animated property. This feels fast because color = state, position = action.

### Algorithm Visualizer (algorithm-visualizer.org)

- **Speed control**: Adjustable delay between steps, typically 100--1000ms.
- **Default**: ~500ms between steps.
- **Animation within a step**: Minimal. Mostly instant state swaps (color fills) with the delay being *between* steps, not *within* them.
- **Key pattern**: The delay is a *pause*, not an animation duration. State changes are near-instant; the pause gives reading time.

### D3.js Observable Notebooks

- **Default transition duration**: `d3.transition().duration(250)` is the community convention.
- **Common range**: 150--400ms for data-driven transitions.
- **Staggered enter**: `delay((d, i) => i * 30)` with `duration(200)` -- so each element animates for 200ms but they start 30ms apart.
- **Observable practice**: Most interactive D3 visualizations use 200--300ms transitions. Longer durations (>500ms) are rare and typically only for dramatic effect.
- **Key pattern**: D3 transitions overlap. Multiple elements animate simultaneously with stagger, so perceived total time is `duration + (n-1) * stagger_delay`, but the *first visible change* happens at 0ms.

### React Flow / xyflow

- **Node position animation**: 200ms with ease-out.
- **Edge path update**: 150ms.
- **Selection highlight**: Instant (0ms -- CSS class swap).
- **Key pattern**: Only *movement* is animated. State changes (selected, highlighted) are instant class swaps with no transition.

### Excalidraw

- **Element creation**: Instant (appears on mouseup).
- **Undo/redo**: Instant state swap, no animation.
- **Collaboration cursor movement**: ~100ms interpolation.
- **Key pattern**: A tool-first approach. Zero decorative animation. Everything is instant unless motion is needed for spatial understanding.

---

## 3. Animation Perception Thresholds

Research-backed durations for the minimum time an animation must last to be *perceived as motion* rather than an instant jump:

| Animation Type | Perception Threshold | "Sweet Spot" for Interactive | Source |
|---------------|---------------------|------------------------------|--------|
| **Color change** (fill/stroke) | 50ms (below = instant pop) | **80--150ms** | Google Material Design; Val Head "Designing Interface Animation" |
| **Opacity fade** (in or out) | 60ms (below = flash) | **100--150ms** in, **80--120ms** out | Material Design (enter 225ms / exit 195ms are *maximums*) |
| **Position translate** | 70ms (below = teleport) | **120--200ms** | Material Design; Apple HIG (spring animations ~200ms settle) |
| **Stroke draw-on** (dashoffset) | 80ms (below = just appears) | **150--250ms** | Empirical; Visualgo edge animation |
| **Counter roll-up** (text number change) | 100ms (need 3+ intermediate frames to read) | **120--200ms** | Game UI conventions (damage numbers) |
| **Dot travel along edge** | 100ms (need to see start and end position) | **150--250ms** | D3 convention for path animation |
| **Scale pulse** | 80ms (below = glitch) | **150--250ms** for full cycle (grow + shrink) | Material Design ripple: 225ms |

### The "Invisible Animation" Floor

Below **~50ms**, CSS transitions and WAAPI animations are effectively invisible -- the browser may not even render an intermediate frame at 60fps (16.7ms/frame). A 50ms animation gets ~3 frames, which is the bare minimum for perceiving motion.

### The "Decorative vs Functional" Line

- **Below 100ms**: Animation is *felt* (subconscious smoothness) but not *seen* (user cannot describe what moved). Good for state changes where you want polish without delay.
- **100--250ms**: Animation is *seen* and *understood*. User can describe the motion. Good for communicating *what changed*.
- **250--500ms**: Animation is *watched*. User's attention is held by the motion. Only appropriate when the motion IS the information (e.g., "this edge connects A to B").
- **Above 500ms**: Animation is *waited for*. Only justified in auto-play / video mode.

---

## 4. Game UI Timing (Fast Feedback Masters)

Game UIs are the best reference for "maximum information, minimum delay":

| Element | Duration | Notes |
|---------|----------|-------|
| Health bar change | 100--200ms | Ease-out. Immediate visual feedback on damage. |
| Damage number pop | 80--120ms rise + 200ms fade | Number appears near-instantly, then fades. |
| State transition (poisoned, buffed) | Instant icon + 150ms color tint | The state change is instant; the polish animation follows. |
| Card flip / reveal | 200--300ms | Spring easing. The reveal IS the interaction. |
| Inventory slot highlight | 0ms (instant) | No transition on hover highlight in fast-paced games. |
| Combo counter increment | 50--80ms scale punch | Number visibly punches up, then settles. |
| Turn indicator move | 150--200ms slide | Communicates "it's your turn now". |

**Key game UI principle**: Show the *result* immediately (or within 100ms), then let polish animations play *after* the result is visible. The user never waits for an animation to see the outcome.

---

## 5. Revised Phase Model for Interactive Scriba

### Kill the 5-Phase Sequence

The 5-phase model (Signal 150ms -> Connect 350ms -> Compute 200ms -> Result 250ms -> Settle 200ms) is wrong for interactive use. Replace it with a **2-phase model**:

#### Phase 1: Instant State (0ms)
- All CSS class swaps happen immediately (recolor, highlight, dim).
- CSS `transition` on `fill`/`stroke` handles the visual interpolation automatically.
- The user sees the *result* state within one frame (~16ms).

#### Phase 2: Motion Overlay (120--250ms, concurrent)
- Draw-on animations, position translates, counter roll-ups fire simultaneously.
- These run *on top of* the already-visible new state.
- They communicate *how* the state changed, not *what* changed.
- Total phase 2 duration: **never exceeds 300ms**.

This means: **click -> result visible in <20ms -> motion completes by 250ms**.

### Why This Works Educationally

The 5-phase model assumed animations must *reveal* information sequentially. But in a stepper:

1. The narration text already explains what happens ("Relax edge A->B, update distance to 5").
2. The user reads the narration, *then* clicks Next.
3. They already know what to expect. The animation confirms, not reveals.

Sequential reveal is valuable in *auto-play video*. In *manual step-through*, it's just delay.

---

## 6. Speed Slider Design

### Survey of Existing Implementations

| Tool | Range | Default | Labels | Implementation |
|------|-------|---------|--------|---------------|
| Visualgo | ~50ms -- 2000ms | ~750ms | Unlabeled slider | Multiplier on base duration |
| USFCA | ~100ms -- 1500ms | ~400ms | "Animation Speed" | Multiplier |
| Algorithm Visualizer | 0ms -- 1000ms | ~500ms | Step delay | Pause between steps |
| Sorting.at | 1ms -- 500ms | ~50ms | Speed | Delay between comparisons |

### Recommended Design for Scriba

**Default should be FAST** with option to slow down. Rationale: most users of an interactive stepper want snappy feedback. Learners who want to study motion will discover the slider.

| Label | Multiplier | Effect on 200ms base | Use case |
|-------|-----------|---------------------|----------|
| **Instant** | 0x | 0ms (CSS transition only) | Power users, re-reviewing |
| **Fast** (default) | 1x | 200ms | Normal interactive use |
| **Study** | 2.5x | 500ms | First-time learning, studying motion |
| **Slow** | 5x | 1000ms | Detailed motion analysis, accessibility |

The slider should go from "Instant" on the left to "Slow" on the right. **Fast is the default, not the exception.**

### Implementation

```javascript
// Speed multiplier applied to all animation durations
const SPEED_MAP = { instant: 0, fast: 1, study: 2.5, slow: 5 };
function dur(baseMs) {
  return Math.round(baseMs * speedMultiplier);
}
```

When multiplier is 0, all WAAPI animations are skipped; CSS transitions still fire at their declared duration (80--150ms), providing minimal visual polish even in "instant" mode.

---

## 7. Per-Animation-Type Timing Recommendations

### Recolor (fill / stroke change)

**Recommendation: Do NOT animate with WAAPI. Use CSS `transition` only.**

```css
[data-t] > rect, [data-t] > circle {
  transition: fill 120ms ease-out, stroke 120ms ease-out;
}
```

- 120ms is perceivable as smooth but not sluggish.
- CSS transitions fire automatically on class swap -- zero JS overhead.
- At speed=instant (0x), set `transition-duration: 0ms` via a `.speed-instant` ancestor class.
- Current value of 250ms is too slow. Drop to **120ms**.

### Fade In (element_add)

| Context | Duration | Easing |
|---------|----------|--------|
| New node/edge appearing | **120ms** | ease-out |
| Annotation text appearing | **100ms** | ease-out |
| Large structural change | **150ms** | ease-out |

Material Design guidance: enter animations should be slightly longer than exits. But in an interactive tool, both should be fast. 120ms in, 80ms out.

### Fade Out (element_remove)

| Context | Duration | Easing |
|---------|----------|--------|
| Node/edge removal | **80ms** | ease-in |
| Annotation cleanup | **60ms** | ease-in |
| Ephemeral highlight removal | **0ms** (instant) | -- |

Exits should be *faster* than entrances. The user cares about what's appearing, not what's leaving.

### Draw-On (stroke-dashoffset)

| Context | Duration | Easing |
|---------|----------|--------|
| Short edge (< 100px path length) | **150ms** | ease-out |
| Medium edge (100--300px) | **200ms** | ease-out |
| Long edge (> 300px) | **250ms** | ease-out |

Scale draw-on duration to path length to maintain consistent perceived speed. Formula:

```javascript
function drawOnDuration(pathLength) {
  // ~1px per ms, clamped to 150--250ms
  return Math.max(150, Math.min(250, Math.round(pathLength * 0.8)));
}
```

**Current 600ms is far too slow.** At 600ms, the user watches a line slowly crawl. At 200ms, they see a line "snap" into existence with a directional cue.

### Counter Roll-Up (value_change on numeric text)

| Context | Duration |
|---------|----------|
| Small delta (1--9) | **120ms** |
| Medium delta (10--99) | **150ms** |
| Large delta (100+) | **200ms** |

At 120ms with ease-out-cubic, the counter shows 3--4 intermediate values at 60fps -- enough to perceive "the number changed" without reading each intermediate frame.

**Current 250ms is acceptable but should drop to 120--150ms.**

### Position Translate (element moves)

| Context | Duration | Easing |
|---------|----------|--------|
| Short move (< 50px) | **120ms** | ease-out |
| Medium move (50--200px) | **150ms** | ease-out |
| Long move (> 200px) | **200ms** | ease-out |

Use consistent *speed* (px/ms), not consistent *duration*. A 10px move at 200ms looks sluggish; a 300px move at 120ms looks like teleportation.

```javascript
function translateDuration(distance) {
  // ~1.5px per ms, clamped to 120--200ms
  return Math.max(120, Math.min(200, Math.round(distance / 1.5)));
}
```

### Dot Travel Along Edge

| Context | Duration |
|---------|----------|
| Short edge | **150ms** |
| Long edge | **250ms** |

Same scaling logic as draw-on. The dot must be visible at start and end positions, so a minimum of 150ms (9 frames at 60fps) is needed to perceive direction.

### Scale Pulse (emphasis)

| Context | Duration | Scale |
|---------|----------|-------|
| Subtle emphasis | **150ms** full cycle | 1.05x |
| Strong emphasis | **200ms** full cycle | 1.15x |

A pulse is grow (half duration) + shrink (half duration). At 150ms total, that's 75ms each way -- perceptible but not distracting.

### Swap Arc (sorting)

| Context | Duration |
|---------|----------|
| Adjacent swap | **180ms** |
| Multi-position jump | **220ms** |

The arc midpoint (vertical offset) should be ~15--20px. The two elements move simultaneously in opposite arcs.

---

## 8. When to Skip Animation Entirely

Some state changes should be **instant with no animation at all**:

| Change | Animation? | Rationale |
|--------|-----------|-----------|
| Highlight on/off | **No** -- instant class swap | Highlighting marks "this is active". Animating it adds delay to the most frequent operation. CSS `transition: fill 120ms` on the element provides enough smoothness. |
| Dim/undim | **No** -- instant class swap + CSS transition | Same as highlight. |
| Text content update (non-numeric) | **No** -- instant | Animating text swap (fade out old, fade in new) doubles the perceived latency for zero information gain. |
| Narration text change | **No** -- instant | The user reads text; animating it delays reading. |
| Progress bar / step counter update | **No** -- instant | UI chrome should respond instantly. |
| Reverting to previous step (Prev button) | **No** -- instant state swap | Going backwards should always be instant. Animation on Prev feels like the tool is fighting you. |
| Any step with > 20 transitions | **No** -- instant batch | Too many simultaneous animations create visual noise. Apply all changes instantly and let CSS transitions provide minimal smoothness. |

### The Prev Button Rule

**All backward navigation must be instant.** No animation, no phasing, no delay. The user pressed Prev to see the previous state, not to watch the animation in reverse. This is already implemented in the demo (`show(s-1, false)` passes `false` for animation) and must remain.

---

## 9. CSS Transition as the Primary Animation Layer

A key insight from USFCA and React Flow: **CSS transitions are often sufficient**.

If every SVG element already has:
```css
[data-t] > rect { transition: fill 120ms ease-out, stroke 120ms ease-out; }
```

Then a class swap from `state-idle` to `state-current` triggers a smooth 120ms fill transition *automatically*, with zero JS animation code. This is:

- Faster to execute (no WAAPI overhead, no Promise chains).
- Automatically respects `prefers-reduced-motion` (set `transition-duration: 0.01ms`).
- Batched by the browser's rendering pipeline.

**WAAPI should only be used for animations that CSS cannot handle:**

| Animation | CSS Transition? | WAAPI Needed? |
|-----------|----------------|---------------|
| Recolor | Yes | No |
| Highlight on/off | Yes | No |
| Opacity fade | Yes | No |
| Stroke width change | Yes | No |
| Draw-on (dashoffset) | No (needs keyframes) | **Yes** |
| Counter roll-up | No (needs rAF) | **rAF** |
| Position translate | Possible but janky | **Yes** (for controlled timing) |
| Dot travel | No | **Yes** |
| Scale pulse | Possible | **Yes** (cleaner with WAAPI) |
| Swap arc | No | **Yes** |

This means roughly **60% of transitions need zero JS animation code** -- just class swaps with CSS transitions.

---

## 10. Recommended Timing Table for Scriba

All durations are at **1x speed** (the "fast" default). Multiply by speed factor for other modes.

### Base Durations

| Animation Kind | Base Duration (ms) | Easing | Implementation |
|---------------|-------------------|--------|----------------|
| **recolor** | 0 (CSS: 120ms) | ease-out | Class swap only |
| **highlight_on** | 0 (CSS: 120ms) | ease-out | Class swap only |
| **highlight_off** | 0 (CSS: 80ms) | ease-in | Class swap only |
| **value_change** (text) | 0 | -- | Instant swap |
| **value_change** (numeric) | 120--150 | ease-out-cubic | rAF counter |
| **element_add** (node/cell) | 120 | ease-out | WAAPI opacity |
| **element_add** (edge/arrow) | 150--250 | ease-out | WAAPI dashoffset (scaled to path length) |
| **element_remove** | 80 | ease-in | WAAPI opacity |
| **position_move** | 120--200 | ease-out | WAAPI transform (scaled to distance) |
| **annotation_add** (text) | 100 | ease-out | WAAPI opacity |
| **annotation_add** (arrow) | 150--250 | ease-out | WAAPI dashoffset |
| **annotation_remove** | 60 | ease-in | WAAPI opacity |
| **dot_travel** | 150--250 | ease-in-out | WAAPI transform (scaled to path length) |
| **scale_pulse** | 150 | ease-in-out | WAAPI transform |
| **swap_arc** | 180 | ease-in-out | WAAPI transform |

### Total Step Duration Budget

| Speed Mode | Max Step Duration | CSS Transition | WAAPI Budget |
|-----------|------------------|----------------|-------------|
| **Instant** | ~120ms | 120ms (CSS only) | 0ms |
| **Fast** (default) | ~250ms | 120ms | 150--250ms |
| **Study** | ~625ms | 300ms | 375--625ms |
| **Slow** | ~1250ms | 600ms | 750--1250ms |

At **Fast** (default), the total time from click to animation-complete is **under 300ms**. The new state is *recognizable* within 120ms (CSS transitions settle) and *fully resolved* by 250ms (WAAPI completes).

### Phase Model (Simplified)

Replace the 5-phase model with:

```
Click
  |
  +-- [0ms]    Phase 0: Instant state swap
  |            - All CSS class changes applied
  |            - Text content updated
  |            - Narration updated
  |            - CSS transitions begin automatically (120ms)
  |
  +-- [0ms]    Phase 1: Motion overlay (concurrent with Phase 0)
  |            - Draw-on animations start
  |            - Position translates start
  |            - Counter roll-ups start
  |            - Dot travels start
  |
  +-- [250ms]  Complete
               - All WAAPI animations finished
               - Buttons re-enabled
               - Ready for next click
```

Both phases fire at t=0. There is **no sequential phasing**. The CSS transitions and WAAPI animations run concurrently. The user sees color changes settling while edges draw on simultaneously.

### CSS Variables for Speed Control

```css
.scriba-animation[data-speed="instant"] [data-t] > * {
  transition-duration: 0ms !important;
}
.scriba-animation[data-speed="fast"] [data-t] > * {
  /* Default: 120ms already declared */
}
.scriba-animation[data-speed="study"] [data-t] > * {
  transition-duration: 300ms !important;
}
.scriba-animation[data-speed="slow"] [data-t] > * {
  transition-duration: 600ms !important;
}
```

---

## 11. Migration from Current Timing

### What Changes

| Current | New | Reason |
|---------|-----|--------|
| 5-phase sequence (1100ms) | 2-phase concurrent (250ms) | Interactive, not video |
| CSS `fill` transition: 250ms | 120ms | Snappier |
| Draw-on: 600ms | 150--250ms (length-scaled) | 600ms is agonizing in a stepper |
| Counter roll-up: 250ms | 120--150ms | Still readable at 120ms |
| Fade in: 180ms | 120ms | Slight reduction |
| Fade out: 180ms | 80ms | Exits should be fast |
| Speed default: 1x (of slow base) | 1x (of fast base) | Fast is the new normal |
| Speed range: 0.25x--2x | instant/fast/study/slow | Named presets, not arbitrary |
| Sequential phases | Concurrent + CSS | No waiting for phase N before phase N+1 |

### What Stays

- `prefers-reduced-motion` behavior (instant swap, no WAAPI).
- 150-transition cap for instant-batch fallback.
- WAAPI as the animation engine.
- `stroke-dashoffset` for draw-on.
- `rAF` for counter roll-up.
- Prev button = always instant.

---

## 12. Summary

The original 1100ms 5-phase timing was designed for a medium (passive video) that Scriba is not. Interactive steppers demand:

1. **Result visible within 120ms** (CSS transition settles).
2. **Motion complete within 250ms** (WAAPI finishes).
3. **No sequential phasing** -- everything fires concurrently.
4. **Default speed = fast**, with option to slow down for studying.
5. **Backward navigation = always instant**.
6. **CSS transitions as the primary layer** -- WAAPI only for motion that CSS cannot express.

The target total step duration at default speed is **250ms**, not 1100ms. This is a **4.4x speedup** that brings Scriba in line with Visualgo (fast setting), USFCA, D3 interactive conventions, and game UI response time standards.
