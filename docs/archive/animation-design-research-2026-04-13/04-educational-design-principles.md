# Educational Animation Design Principles for Algorithm Visualization

Research compilation for Scriba's animation system. Covers cognitive science, timing research, accessibility, and competitive programming editorial design.

---

## 1. Cognitive Load and Multimedia Learning

### Mayer's Principles Applied to Algorithm Animation

Richard Mayer's Cognitive Theory of Multimedia Learning (2001) rests on three assumptions: **dual-channel processing** (visual and auditory channels are separate), **limited capacity** (each channel can process only a small amount of information at once), and **active processing** (learners must select, organize, and integrate information to learn). These directly constrain how Scriba should animate algorithm steps.

The most relevant of Mayer's 12 principles for algorithm animation:

#### Signaling Principle

> "Learning is enhanced when cues are added to draw attention to vital information."

For algorithm visualization this means: before computing a DP cell value, highlight the dependency cells with arrows or color changes. Before a BFS step explores edges, visually mark the dequeued node. The signal precedes the action. Research on attention cueing in instructional animations (de Koning et al., 2009) found that visual cues limit time spent fixating on irrelevant areas, enabling more synchronized processing. Critically, cueing is most effective for **novices** --- once learners develop expertise, redundant cues add unnecessary cognitive load.

**Scriba implication**: Provide attention cues (highlight, glow, arrow) before the main animation action. Consider reducing cues at higher playback speeds or for expert users.

Sources:
- Mayer, R. E. (2001). *Multimedia Learning*. Cambridge University Press.
- de Koning, B. B., Tabbers, H. K., Rikers, R. M. J. P., & Paas, F. (2009). Towards a framework for attention cueing in instructional animations. *Educational Psychology Review*, 21, 113--140.

#### Temporal Contiguity Principle

> "Present words and pictures simultaneously rather than sequentially."

Narration text (the editorial explanation) must appear **at the same time** as the corresponding animation, not before or after. If Scriba shows "We relax edge (u, v) and update dist[v]" as text, the arrow from u to v and the cell update should animate concurrently with that text appearing.

**Scriba implication**: Sync annotation text appearance with the animation it describes. Never show a paragraph of explanation followed by a disconnected animation.

#### Segmenting Principle

> "People learn more deeply when a multimedia message is presented in learner-paced segments rather than as a continuous unit."

A meta-analysis by Rey et al. (2019) found that segmented presentations improved retention (71.4% of studies) and transfer (83.3% of studies) compared to continuous presentations. Importantly, research shows that most novice learners who are given pause buttons **choose not to use them** --- they do not know when to pause. This argues for **system-defined segment boundaries** (Scriba's step-by-step design) rather than relying solely on a pause button.

**Scriba implication**: Each algorithm step should be a discrete segment. Auto-advance between segments with a visible pause between them. Provide both auto-play and manual step modes, but default to system-paced segments since novices benefit from forced pauses.

Sources:
- Rey, G. D., Beege, M., Nebel, S., Wirzberger, M., Schmitt, T. H., & Schneider, S. (2019). A meta-analysis of the segmenting effect. *Educational Psychology Review*, 31, 389--419.
- Spanjers, I. A. E., van Gog, T., Wouters, P., & van Merrienboer, J. J. G. (2012). Guided self-management of transient information in animations. *Educational Technology Research and Development*, 60, 977--994.

#### Pre-training Principle

> "Introduce key concepts and definitions before the main content."

Before animating a segment tree build, first show the static structure --- the array, the tree layout, the node labels --- and let the learner orient. Only then begin the animation. This reduces the "where am I?" cognitive load during the animation itself.

**Scriba implication**: Each visualization widget should have a brief "setup" phase showing the initial state with labels before any animation begins. The editorial text can introduce terminology during this static phase.

#### Coherence Principle

> "Exclude unnecessary information that distracts from learning goals."

Every animated element must serve the explanation. No decorative transitions, no gratuitous particle effects, no background animations. Research from Sundararajan & Adesope (2020) demonstrated that **decorative animations impair recall** compared to static images, even when the decorative animation is thematically relevant. The animations act as "seductive details" that consume working memory without contributing to learning.

**Scriba implication**: Strip all animation to functional purpose. If highlighting a cell does not aid understanding, do not highlight it. If a fade-in does not signal something meaningful, use an instant appear instead.

Sources:
- Sundararajan, N., & Adesope, O. (2020). Decorative animations impair recall and are a source of extraneous cognitive load. *Advances in Physiology Education*, 44(3), 376--382.

#### Modality Principle

> "Students learn better from visuals with spoken words than from text overlaid on visuals."

In Scriba's context (no audio), this means: keep on-screen text minimal during animation. The editorial narrative should be spatially separated from the visualization, not overlaid on top of animated elements. Dense text competing with motion overloads the visual channel.

**Scriba implication**: Place step descriptions beside or below the visualization, not on top of animated elements. Keep annotation text short (one sentence per step).

---

## 2. Animation Sequencing for Algorithms

### The Problem with Simultaneous State Changes

Tversky, Morrison, & Betrancourt (2002) reviewed nearly 100 studies comparing static and animated graphics and found that animation rarely outperformed static images. Their key insight: animations fail when they present too many simultaneous changes, because humans cannot track multiple moving elements at once. The visual system processes sequential changes far better than parallel ones.

> "If there are benefits to animation, they should be evident especially for continuous rather than discrete changes, in particular, for manner of change and for microsteps."

**The Congruence Principle**: The format of the graphic should match the format of the concept. Algorithm steps are inherently sequential --- each step depends on the previous one. Animation should mirror this sequentiality.

**The Apprehension Principle**: The graphic must be accurately perceived. If an animation is too fast or too complex, learners cannot apprehend it, and it becomes worse than a static diagram.

Sources:
- Tversky, B., Morrison, J. B., & Betrancourt, M. (2002). Animation: Can it facilitate? *International Journal of Human-Computer Studies*, 57(4), 247--262.

### Optimal Micro-Animation Sequences

Based on Mayer's principles and animation research, each algorithm operation should decompose into a **signaling-action-result** sequence:

#### DP Recurrence Step

| Phase | Animation | Duration | Purpose |
|-------|-----------|----------|---------|
| 1. Signal | Highlight source cells (dependencies) | 200--300ms | Pre-training / signaling |
| 2. Connect | Draw dependency arrows from sources to target | 300--400ms | Show relationship |
| 3. Compute | Display formula evaluation near target cell | 200--300ms | Temporal contiguity with text |
| 4. Fill | Color/fill target cell with computed value | 150--200ms | Result confirmation |
| 5. Settle | Brief pause, dim arrows, return to neutral | 200--300ms | Segmenting boundary |

**Total per step**: 1050--1500ms

#### BFS Step

| Phase | Animation | Duration | Purpose |
|-------|-----------|----------|---------|
| 1. Dequeue | Pop node from queue, highlight it | 200--300ms | Signal active element |
| 2. Explore | Sequentially highlight outgoing edges | 150--200ms each | Show traversal |
| 3. Update | Update neighbor distances/labels | 200--250ms each | Show state change |
| 4. Enqueue | Move updated neighbors into queue | 200--300ms | Show result |
| 5. Settle | Dim processed node, pause | 200--300ms | Segment boundary |

**Total per step**: 950--1350ms (varies with degree)

#### Sorting Comparison/Swap

| Phase | Animation | Duration | Purpose |
|-------|-----------|----------|---------|
| 1. Compare | Highlight two elements being compared | 200ms | Signal |
| 2. Decide | Brief color cue (green = in order, red = swap needed) | 150ms | Show decision |
| 3. Swap | Animate position exchange with arc/slide | 300--400ms | Main action |
| 4. Settle | Return to neutral coloring | 150ms | Reset |

**Total per step**: 800--900ms

### Manim's Sequencing Patterns

Manim (the mathematical animation engine used by 3Blue1Brown) follows a consistent pattern documented in community guides and the research paper by Liu & Sun (2024):

1. **Create** --- introduce elements with `FadeIn`, `Write`, or `GrowFromCenter`
2. **Transform** --- morph, move, or recolor to show state change
3. **Emphasize** --- briefly scale up, glow, or circumscribe the result
4. **FadeOut** --- remove elements no longer needed

For dual visualizations (e.g., tree + array for heapsort), Manim plays related animations simultaneously so learners see the correspondence, but only when both views show the **same logical operation**. Never mix unrelated operations.

Sources:
- Manim Community Documentation v0.20.1.
- Liu, T. & Sun, T. (2024). Manim for STEM Education: Visualizing Complex Problems Through Animation. arXiv:2510.01187.

### Stagger Timing

When multiple elements animate in sequence (e.g., highlighting BFS neighbors one by one), the **stagger delay** --- the offset between consecutive element animations --- should be:

- **50--100ms** for items that are conceptually part of the same operation (e.g., neighbors being enqueued)
- **100--200ms** for items that represent distinct sub-steps (e.g., relaxing different edges)
- **Rule of thumb**: stagger delay should be less than 50% of the individual animation duration, so the next animation starts before the current one finishes, creating a cascading "wave" effect

Sources:
- GSAP Staggers documentation.
- Motion.dev stagger() API documentation.

---

## 3. Timing and Duration

### Research-Backed Duration Ranges

The Nielsen Norman Group and Material Design guidelines provide empirically grounded ranges. The Model Human Processor (Card, Moran, & Newell, 1983) establishes that the average human visual perception cycle is ~230ms.

| Animation Type | Recommended Duration | Notes |
|----------------|---------------------|-------|
| **Instant feedback** (color swap, toggle) | 80--150ms | Must feel "immediate." Below 80ms may be imperceptible. |
| **Small state change** (cell fill, opacity shift) | 150--250ms | Long enough to notice, short enough to not delay comprehension. |
| **Movement** (element sliding, arrow drawing) | 250--400ms | Sweet spot for visual tracking. The eye needs time to follow. |
| **Complex entrance** (fade in + slide, grow from center) | 300--500ms | Compound motion needs more time but must not exceed 500ms. |
| **Exit animation** (fade out, shrink) | 150--250ms | Exits should be ~70% the duration of entrances (asymmetry principle). |
| **Large screen transition** | 300--500ms | Maximum before users feel the animation is "dragging." |

**Critical threshold**: At 500ms+, animations start to feel slow and annoying (NN/g). At 1000ms+, users lose their flow of thought. Educational animations can stretch slightly longer (up to 600--800ms for complex movements) because the motion itself carries information, but this tolerance is limited.

**Below-threshold warning**: Animations under 100ms are perceived as instantaneous and provide no motion cue. If the purpose is to show "something happened here," the animation needs to be at least 150ms.

Sources:
- Nielsen Norman Group. (2020). Executing UX Animations: Duration and Motion Characteristics.
- Material Design Guidelines: Motion duration and easing.
- Card, S. K., Moran, T. P., & Newell, A. (1983). *The Psychology of Human-Computer Interaction*. Lawrence Erlbaum.
- Val Head. (2016). How fast should your UI animations be?

### Pauses Between Animations

The "breathing room" between animation segments is critical for the segmenting principle:

- **Within a step** (between micro-animations): 50--150ms implicit pause, often achieved by having the next animation start slightly after the previous one ends
- **Between steps**: 300--600ms explicit pause. This is the segment boundary. It gives the learner time to consolidate what they just saw.
- **Between phases** (e.g., "setup complete, now solving"): 800--1200ms pause, optionally with a visual divider or text update
- **At decision points** (when auto-play reaches a conceptual milestone): Consider a full stop with "Continue" button or longer pause (1500--2000ms)

### Auto-Play vs Manual Step

Research findings on learner control (Spanjers et al., 2012; Rey et al., 2019):

| Mode | Pros | Cons | Best for |
|------|------|------|----------|
| **Auto-play** | Smooth flow, shows temporal relationships, less effort | Novices cannot control pace, may miss steps | Review/replay, demonstrations, simple algorithms |
| **Manual step** | Full learner control, forced processing at each step | Disrupts flow, learners may click through without processing | Complex algorithms, first encounter, DP/graph problems |
| **Hybrid** (auto-play with pause at segment boundaries) | Balances flow and processing time | Requires well-defined segment boundaries | Recommended default for Scriba |

**Scriba recommendation**: Default to hybrid auto-play that pauses at step boundaries. Provide speed controls (0.5x, 1x, 1.5x, 2x) and a manual step mode. The speed control adjusts animation durations and inter-step pause durations proportionally.

---

## 4. Visual Hierarchy in Animation

### Making the Main Action Stand Out

The attention cueing framework (de Koning et al., 2009) identifies three cueing functions:

1. **Selection cueing** --- directing attention to a specific location ("look here")
2. **Organization cueing** --- emphasizing the structure of information ("these elements are related")
3. **Integration cueing** --- showing relationships between elements ("this causes that")

For algorithm visualization, all three are needed at different moments.

### Dimming and Brightening

The most effective visual hierarchy technique for algorithm animation:

- **Active elements**: Full opacity (1.0), saturated color, possibly slightly scaled up (1.05x--1.1x)
- **Relevant context**: Reduced opacity (0.6--0.7), desaturated, normal scale
- **Irrelevant elements**: Low opacity (0.2--0.4), heavily desaturated or grayed out
- **Processed/completed elements**: Distinct muted color (e.g., light gray or a "done" color), opacity 0.5--0.6

The transition between states should take 150--250ms, fast enough to not distract but slow enough to be perceptible.

### Scale and Size as Attention Cues

- A brief scale pulse (1.0 to 1.15 to 1.0 over 300--400ms) on the result cell after computation effectively says "look at this result"
- Scale changes should be subtle. Beyond 1.2x, elements overlap neighbors and create visual noise.
- Never scale text --- it looks broken. Scale containers/cells instead.

### Ghost/Trail Effects

For showing "where a value came from":

- A semi-transparent copy of the value that slides from source to destination before the destination updates
- Ghost opacity: 0.3--0.5, fading to 0 by the time it reaches the destination
- This technique is highly effective for DP transitions where the recurrence pulls values from specific cells

### Glow and Pulse Effects

- **Glow (box-shadow or filter: drop-shadow)**: Useful for signaling the currently active element. Keep it subtle --- 2--4px spread, moderate opacity. Effective when paired with a brief pulse (grow shadow, shrink shadow over 400--600ms).
- **When glow helps**: Marking the "current node" in graph traversal, indicating "this cell is being computed"
- **When glow distracts**: Applying it to many elements simultaneously, using it purely for decoration, pulsing continuously (becomes noise after 2--3 cycles)
- **Recommendation**: Use glow for at most 1--2 elements at any time. Pulse at most twice, then hold steady. Remove when the element is no longer active.

---

## 5. Easing and Motion Design

### Easing Recommendations by Animation Type

Based on UX research and the Easing Blueprint (animations.dev):

| Animation Type | Easing | Rationale |
|----------------|--------|-----------|
| **Element entrance** (fade in, slide in) | `ease-out` / `cubic-bezier(0.0, 0.0, 0.2, 1.0)` | Starts fast (responsive), decelerates into final position. Feels like the element "arrives." |
| **Element exit** (fade out, slide out) | `ease-in` / `cubic-bezier(0.4, 0.0, 1.0, 1.0)` | Starts slow, accelerates away. Element "leaves" naturally. |
| **On-screen movement** (cell sliding, arrow drawing) | `ease-in-out` / `cubic-bezier(0.4, 0.0, 0.2, 1.0)` | Mimics natural acceleration/deceleration. Best for elements that start and end at rest. |
| **Color/opacity transition** | `ease` / `cubic-bezier(0.25, 0.1, 0.25, 1.0)` | Gentle curve for subtle property changes. |
| **Continuous/progress** (progress bar, timer) | `linear` | Constant rate correctly represents uniform progress. |
| **Emphasis pulse** (scale up and back) | `ease-out` for growth, `ease-in` for shrink | The growth should feel snappy, the return gentle. |

### Spring Physics

Spring-based animation (e.g., react-spring, Framer Motion springs) produces natural-looking motion with overshoot and settling. Assessment for educational visualization:

- **Appropriate**: Subtle spring on element entrance (slight overshoot on slide-in, damping ratio ~0.7--0.8). Makes elements feel "physical" without being distracting.
- **Inappropriate**: Heavy bounce/spring on data value changes. A cell value should not "bounce" into place --- it undermines the precision that algorithm visualization requires.
- **Never**: Spring physics on arrow drawing, graph edge animation, or any element that represents a mathematical relationship. These should move with clean ease-in-out.

**Recommendation for Scriba**: Use ease-in-out as the default for all movement. Use ease-out for entrances. Avoid spring physics except possibly for very subtle UI chrome animations (button presses, panel slides). Algorithm state changes should feel precise, not playful.

### Overshoot and Bounce

- **Overshoot** (element goes past its target then settles): Acceptable in very small amounts (1--3px overshoot) for element positioning in non-data contexts. Never for values, labels, or data representations.
- **Bounce** (multiple oscillations): Not appropriate for educational algorithm content. Bounce adds visual complexity without informational value and can be perceived as unprofessional.
- **Exception**: A single, very subtle overshoot on a "new result" appearance can add satisfying physicality if kept under 5% of the movement distance.

---

## 6. Accessibility

### prefers-reduced-motion

WCAG 2.1 Success Criterion 2.3.3 (Animation from Interactions, AAA level) requires providing a mechanism to disable non-essential animation. The `prefers-reduced-motion` media query is the primary implementation mechanism.

**What to show instead of animation when reduced motion is requested:**

| Normal behavior | Reduced-motion alternative |
|----------------|---------------------------|
| Slide/movement transitions | Instant position change (opacity crossfade at most) |
| Fade in/out (200ms+) | Instant appear/disappear, or very brief crossfade (100ms max) |
| Color transitions | Instant color change |
| Scale pulse emphasis | Brief opacity flash or border highlight |
| Arrow drawing animation | Arrow appears instantly |
| Complex sequenced micro-animations | All state changes applied simultaneously, instantly |

**Critical**: Do NOT remove the state changes themselves. The final visual state must be identical whether animations play or not. Only the transitions between states change.

Implementation pattern:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

For JavaScript-driven animations, detect the preference:

```javascript
const prefersReducedMotion = window.matchMedia(
  "(prefers-reduced-motion: reduce)"
).matches;
```

Sources:
- W3C WAI WCAG 2.1 Technique C39.
- MDN Web Docs: prefers-reduced-motion.
- Pope Tech. (2025). Design accessible animation and movement.

### Color-Blind Friendly Animation Cues

Algorithm visualizations commonly use red/green to indicate "wrong/right" or "unvisited/visited." This is invisible to ~8% of males with red-green color deficiency.

**Requirements**:
- Never rely on color alone to convey state. Always pair with a second channel: shape, pattern, label, or icon.
- For cell states: use color + a text label or symbol (checkmark, X, number overlay).
- For graph traversal: use color + line style (solid = visited, dashed = unvisited) + node fill pattern.
- For highlighting: use color + increased border weight or a distinct border style.
- Test all color schemes with a deuteranopia simulator.

**Recommended accessible palette strategy**: Use a blue-orange diverging palette instead of red-green. Blue (unprocessed) to orange (active) to gray (completed) works well for most forms of color vision deficiency.

### Screen Reader Announcements

For users who cannot see animations, state changes must be announced via ARIA live regions:

```html
<div aria-live="polite" aria-atomic="true" class="sr-only">
  <!-- Updated by JS when algorithm state changes -->
  Step 3: Relaxed edge (2, 5). Distance to node 5 updated from infinity to 7.
</div>
```

**Guidelines**:
- Use `aria-live="polite"` (not assertive) --- algorithm steps are not urgent
- Use `aria-atomic="true"` so the full step description is read, not just the changed portion
- Keep announcements concise: state what changed and the result
- Announce at the **step** level, not the micro-animation level (do not announce "highlighting cell" --- announce "computed dp[3][4] = 7")
- The live region must exist in the DOM before content is injected (add it on page load, empty)

### Keyboard Control

Users must be able to:
- **Space/Enter**: Play/pause the animation
- **Right arrow**: Advance one step
- **Left arrow**: Go back one step
- **Home/End**: Jump to beginning/end
- **Speed control**: Accessible via keyboard (e.g., +/- keys or a labeled slider)

All interactive controls must have visible focus indicators and appropriate ARIA labels.

### Vestibular Disorder Considerations

Animations that can trigger vestibular reactions:
- Large-scale zoom in/out
- Parallax scrolling
- Rapid repeated flashing (3+ flashes per second violates WCAG 2.3.1)
- Continuous background motion

For Scriba: algorithm visualizations are generally small-scale, contained within a widget, and do not involve full-screen motion. The primary risk is rapid sequential highlighting that could resemble flashing. Ensure that highlight transitions take at least 150ms and that no element flashes more than 3 times per second.

---

## 7. Competitive Programming Editorial Specifics

### What Makes Editorials Hard to Follow

Based on Codeforces community discussions and editorial best practices:

1. **The formalism gap**: Editorials jump from problem statement to formal recurrence (`dp[i][j] = min(dp[i-1][j], dp[i][j-1] + cost[i][j])`) without showing *why* that recurrence is correct. The reader must mentally simulate the algorithm.

2. **Missing intermediate states**: Text says "after processing all edges from node 3" but the reader cannot see what the graph looks like at that point.

3. **Implicit dependencies**: "Note that we need the values from the previous row" --- which cells specifically? The spatial relationships are described but never shown.

4. **Speed of exposition**: Editorials are written for other experts. Steps are skipped because the author considers them obvious. A visualization can show every micro-step without slowing down the expert (who can skip) while helping the novice.

5. **No backtracking**: Text is linear. If a reader does not understand step 5, they must re-read the entire editorial. A visualization lets them replay just step 5.

### How Animation Bridges the Gap

| Editorial weakness | Animation solution |
|-------------------|-------------------|
| Abstract recurrence | Show dependency arrows from source cells to target cell |
| Missing intermediate states | Display the full data structure state at every step |
| Implicit spatial relationships | Highlight the specific cells/nodes/edges being referenced |
| Expert-speed exposition | User controls playback speed; every micro-step is shown |
| No backtracking | Step-back functionality to replay any step |

### Annotating Complexity Visually

During animation, show running complexity:
- A small counter showing "Operations so far: 42" or "Current: O(n log n), step 15 of n"
- For nested loops: visually nest the animations (outer loop = slow phase changes, inner loop = fast micro-animations within each phase)
- For amortized analysis: show a "potential" meter or accumulated cost bar that resets at key points

### Connecting Code and Visual State

The most powerful editorial technique: **synchronized code highlighting**. As the animation proceeds:
- Highlight the line of pseudocode/code that corresponds to the current animation step
- Show variable values updating in a side panel
- Draw visual connections between code variables and their visual representations (e.g., `i=3` in code linked to the highlighted row 3 in the visualization)

This is the algorithmic equivalent of Mayer's temporal contiguity principle --- the code and the visualization advance in lockstep.

---

## 8. Anti-Patterns

### Animations That Obscure Rather Than Clarify

1. **The "fireworks" effect**: Animating every element change simultaneously. When a DP table updates an entire row, do NOT animate all cells at once. Animate them left-to-right (or in dependency order) with stagger.

2. **The "conveyor belt"**: Auto-playing through steps so fast that the learner cannot process any single step. If total step duration is under 600ms for a complex operation, it is too fast.

3. **The "magician's misdirection"**: A flashy entrance animation (spinning, bouncing, scaling) that draws attention to the animation itself rather than the data it carries. Element entrances should be functional (fade in, slide in) not performative.

4. **The "invisible change"**: State changes that are too subtle --- e.g., changing a cell value from 5 to 7 without any highlight or transition. The change is correct but the user does not notice it happened.

### Too Many Simultaneous Animations

Working memory can track approximately **3--4 visual objects** simultaneously (Cowan, 2001). If more than 3 elements are animating at the same time, comprehension drops sharply. Rules:

- **Maximum 2 primary animations** at any moment (e.g., an arrow drawing + a cell highlighting)
- **Maximum 3--4 secondary animations** (e.g., opacity fades on background elements)
- If an algorithm step logically affects more than 3 elements, sequence them --- do not parallelize

Sources:
- Cowan, N. (2001). The magical number 4 in short-term memory. *Behavioral and Brain Sciences*, 24(1), 87--114.

### Animations That Are Too Slow

The "patience threshold" for educational animation:

- **Single micro-animation**: If it takes more than 500ms for a simple state change, it feels sluggish
- **Full algorithm step**: If it takes more than 2000ms (2 seconds) including pauses, the learner becomes impatient
- **Full algorithm run**: If a complete visualization of an O(n^2) algorithm on n=10 takes more than 60 seconds at 1x speed, it needs to be faster

The fix is not to remove animation but to tighten durations and reduce inter-step pauses. Provide speed controls (1x, 1.5x, 2x) so experts can watch at higher speeds.

### Decorative Animations with No Educational Value

Per Sundararajan & Adesope (2020), decorative animations **actively impair learning** even when thematically relevant. Examples to avoid:

- Background particle systems or ambient motion
- Animated gradients on cells or borders that do not represent data
- Transition effects between widget pages (fancy page turns, 3D flips)
- Loading spinners that are more elaborate than necessary
- Animated logos or branding elements within the visualization

### Inconsistent Animation Speed/Style

If cell highlighting takes 200ms in step 1 and 400ms in step 5, the learner's internal model of "what a highlight means" is disrupted. Consistency requirements:

- **Same animation type = same duration** across all steps (e.g., all cell fills are 200ms)
- **Same easing curve** for the same type of animation throughout the editorial
- **Same color mapping** for the same semantic meaning (e.g., "active" is always the same shade of blue)
- **Same stagger timing** for equivalent operations (e.g., highlighting neighbors always uses 100ms stagger)

---

## Summary: Scriba Animation Design Guidelines

### Duration Quick-Reference

| Animation | Duration | Easing |
|-----------|----------|--------|
| Color/opacity change | 150--200ms | ease |
| Cell fill / value update | 200--250ms | ease-out |
| Element slide / movement | 300--400ms | ease-in-out |
| Arrow draw | 300--400ms | ease-in-out |
| Entrance (fade in) | 200--300ms | ease-out |
| Exit (fade out) | 150--200ms | ease-in |
| Emphasis pulse | 300--400ms | ease-out + ease-in |
| Stagger between items | 50--150ms | -- |
| Pause between micro-animations | 50--150ms | -- |
| Pause between steps | 300--600ms | -- |
| Pause at phase boundary | 800--1200ms | -- |

### Core Principles

1. **Signal before act**: Highlight dependencies before computing results.
2. **One thing at a time**: Maximum 2 primary animations simultaneously.
3. **Consistent timing**: Same animation type = same duration everywhere.
4. **Functional only**: Every animation must serve comprehension. If it does not, remove it.
5. **Learner-paced segments**: Break into steps with pauses. Default to hybrid auto-play.
6. **Accessible by default**: Respect reduced-motion. Never rely on color alone. Announce to screen readers.
7. **Sync text and animation**: Editorial narration appears simultaneously with corresponding visual changes.
8. **Speed control**: Provide 0.5x--2x playback speed. Adjust all durations proportionally.

### Recommended Step Sequence Template

For any algorithm step:

```
1. SIGNAL    (200ms)  --- Highlight relevant elements, show what we are about to do
2. CONNECT   (300ms)  --- Draw arrows/lines showing relationships
3. COMPUTE   (200ms)  --- Show the operation/calculation
4. RESULT    (200ms)  --- Fill in the result, update state
5. SETTLE    (300ms)  --- Dim signal elements, pause before next step
```

Total: ~1200ms per step at 1x speed. Adjustable via speed control.
