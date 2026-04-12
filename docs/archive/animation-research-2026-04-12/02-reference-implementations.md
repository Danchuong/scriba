# Reference Implementations: Animation Systems for Algorithm/Math Visualization

Research date: 2026-04-12

---

## 1. Manim (3Blue1Brown)

### Architecture

Manim operates as a Python-to-video pipeline. A `Scene` subclass defines a sequence of animation calls. When `Scene.render()` executes, it walks through the `construct()` method, and each `self.play()` call blocks execution while it renders frames for that animation segment. The core loop is:

1. User calls `self.play(Transform(mobject, target), run_time=2)`.
2. `play()` resolves the animation's total frame count from `run_time * fps` (typically 60 fps).
3. For each frame index `i` in `[0, total_frames]`, it computes `alpha = i / total_frames`, applies the rate function to get `sub_alpha = rate_func(alpha)`, calls `animation.interpolate(sub_alpha)`, renders the scene to a Cairo surface or OpenGL framebuffer, and writes the frame to disk.
4. After all `play()` calls complete, ffmpeg encodes the frame sequence into MP4 or GIF.

The critical insight is that **Manim is not real-time**. It renders offline, frame by frame. There is no animation loop or event loop; the Python control flow *is* the timeline.

### Interpolation model

Every animation has an `interpolate_mobject(alpha)` method. For a `Transform(A, B)`, this method computes the intermediate state between mobject A and target B at progress `alpha` (0 to 1). The interpolation is per-attribute: position is linearly interpolated, color channels are interpolated independently, path points are interpolated element-wise (which is why source and target must have matching point counts -- Manim uses `align_data()` to ensure this).

Rate functions (`rate_func`) map the linear `alpha` to a curved `sub_alpha`. The default is `smooth` (a sigmoid-like S-curve). Others include `linear`, `rush_into` (ease-in), `rush_from` (ease-out), `there_and_back`. These are plain Python functions `float -> float` mapping `[0,1] -> [0,1]`.

### Simultaneous animations

`AnimationGroup` takes multiple animations and plays them in parallel within a single `play()` call. Each sub-animation has its own `interpolate_mobject()` called at the same alpha. `Succession` chains animations sequentially within one `play()`. `LaggedStart` staggers the start times with a configurable `lag_ratio`.

Under the hood, `AnimationGroup.interpolate(alpha)` distributes alpha across its children according to their relative `run_time` weights and lag configuration. Each child still receives a `[0,1]` alpha within its own active window.

### Step-by-step algorithm visualization

Manim has no built-in concept of "algorithm steps." The user manually writes `self.play()` calls for each step. Backward navigation does not exist -- since frames are rendered offline and composited into video, "stepping back" means seeking in the video player. The Python imperative flow is inherently forward-only.

### Output and cost

Output: MP4, GIF, or PNG sequences. Runtime cost is dominated by rendering -- Cairo for vector scenes, OpenGL for 3D. A typical 30-second explainer takes 2-10 minutes to render depending on complexity. Bundle size is irrelevant (not browser-deployed). The Python dependency tree is heavy (~200 MB with Cairo, ffmpeg, LaTeX).

### Lessons for Scriba

The `play(Transform(A, B))` abstraction -- "animate from current state to target state" -- is the right mental model. It is intuitive because it matches how humans think about transitions: "now move this here, then change that color." The weakness is that it is purely imperative and forward-only, making interactive scrubbing impossible without re-rendering. Scriba should adopt the play-to-target model but compute transitions as serializable state diffs rather than imperative render calls, so they can be replayed in either direction.

---

## 2. Motion Canvas

### Architecture

Motion Canvas is a TypeScript framework that renders to an HTML5 Canvas element and exports to video via a custom exporter (frame-by-frame capture similar to Manim, but running in a browser/Node context). The scene graph is a tree of `Node` objects (rectangles, circles, lines, text, layout containers) with a custom renderer -- not SVG, not DOM, but direct Canvas 2D drawing.

The defining architectural feature is **signal-based reactivity** inspired by SolidJS. Every visual property (position, rotation, fill, opacity) is a `Signal<T>`. When a signal's value changes, only the affected parts of the scene graph are marked dirty and re-rendered. This is the same fine-grained reactivity model as SolidJS/Preact Signals, applied to a canvas scene graph rather than DOM.

### Generator-based sequencing

Animations are defined as generator functions. A scene's `run()` method is a generator that `yield*` delegates to animation calls:

```typescript
yield* rect().position.x(300, 1);      // animate x to 300 over 1 second
yield* waitFor(0.5);                     // pause 0.5 seconds
yield* rect().fill('#ff0000', 0.3);     // animate fill over 0.3 seconds
```

Each `yield*` suspends the generator until the animation completes. The runtime steps through the generator, advancing time by the frame duration on each tick. This gives imperative-looking code that is actually a coroutine-based timeline. Parallel animations use `yield* all(animA, animB)`, which runs multiple generators concurrently until all complete.

The generator model means the "timeline" is emergent from the code's execution order, not declared as a data structure. The runtime can step forward frame by frame, and because signal values are deterministic for a given time, it can also jump to any arbitrary time by fast-forwarding the generators from t=0.

### Timing and interpolation

Each property animation takes a duration and an optional timing function. The interpolation is per-signal: `position.x(300, 1)` creates a tween from the current value to 300 over 1 second. The timing function (easing curve) is applied to the normalized progress. Motion Canvas ships standard easings (linear, easeInOut, easeInOutCubic, etc.) and supports custom curves.

### SVG-like scenes

Motion Canvas does not render SVG. Its scene graph is purpose-built for Canvas 2D. SVG paths can be imported and drawn, but the rendering is always rasterized to canvas. This means no DOM overhead, but also no CSS styling or SVG feature reuse.

### Output and cost

Output: MP4 via frame export, or interactive preview in the browser editor. The editor provides a timeline scrubber, which works by re-executing generators from t=0 to the target time (fast-forward, not random access). Bundle size for the editor is moderate (~2-3 MB); the exported video has no runtime cost.

### Lessons for Scriba

The generator-yield model for sequencing is the most elegant approach surveyed. It reads like imperative code but is actually a pausable, steppable coroutine. The signal-based reactivity ensures efficient updates. The weakness is that random-access seeking requires replaying from t=0, which is O(t) in the number of frames. For Scriba's interactive step-through use case, this could be addressed by snapshotting state at regular intervals (keyframes) and replaying only from the nearest keyframe.

---

## 3. D3 Transitions

### Architecture

D3 transitions operate on the DOM. A transition is created from a selection (`d3.select(...).transition()`), which schedules interpolated attribute changes on actual DOM/SVG elements. The transition system uses `requestAnimationFrame` internally. Each transition has a start time, duration, delay, and easing function. On each frame, D3 computes `t = (now - start) / duration`, applies the easing to get `t'`, and sets each attribute to `interpolator(t')`.

There is no scene graph, no virtual DOM, no frame buffer. D3 manipulates the real DOM directly. This is both its strength (any SVG/HTML element is animatable) and its limitation (performance is bound by DOM mutation cost).

### Data joins and element identity

The data join (`selection.data(newData, keyFn)`) is D3's most distinctive concept. It produces three sub-selections:

- **enter**: data elements with no corresponding DOM node (new items)
- **update**: data elements matched to existing DOM nodes (changed items)
- **exit**: DOM nodes with no corresponding data element (removed items)

Each sub-selection can have different transitions: enter elements fade in, update elements interpolate to new positions, exit elements fade out and are removed. The key function determines identity -- typically a unique ID from the data.

This enter/update/exit pattern is essentially a **state diff model for visual elements**. Given state S1 and state S2, D3 computes which elements are added, changed, or removed, and applies appropriate transitions to each group.

### Interpolation

`d3-interpolate` is a standalone module that handles per-attribute interpolation. It auto-detects the type:
- Numbers: linear interpolation
- Colors: interpolation in Lab color space (perceptually uniform)
- Strings with embedded numbers (e.g., `"translate(10, 20)"` to `"translate(50, 80)"`): extracts numbers, interpolates them, reconstructs the string
- Dates: numeric interpolation on timestamps
- Arrays/objects: recursive element-wise interpolation

Custom interpolators can be registered for any attribute. For SVG paths, `d3-interpolate-path` (community module) aligns path commands and interpolates control points.

### Staggered transitions

Staggering is done via `.delay(i => i * 50)`, where the delay is a function of the element's index. This creates a cascade effect. Combined with data joins, you get staggered enter animations and staggered exit animations naturally.

### Step-by-step algorithm visualization

D3 has no built-in step concept. Users typically implement it by maintaining an array of states and calling a `render(state[i])` function that performs a data join and transitions to the new state. Backward navigation is trivial at the data level (decrement index) but the visual transition plays forward (from current DOM state to previous data state). There is no "reverse animation" -- it is a new transition to the old state.

### Output and cost

Output: live DOM. No video export. Runtime cost is the DOM itself plus `requestAnimationFrame` overhead. For small-to-medium element counts (<1000 SVG nodes), performance is excellent. Beyond that, DOM thrashing becomes a bottleneck. Bundle size: `d3-transition` + `d3-interpolate` + `d3-selection` is ~15 KB minified+gzipped.

### Lessons for Scriba

D3's enter/update/exit is the right model for algorithm visualization where data structures change between steps. Rather than specifying "animate element X from position A to B," you specify "here is the new state" and let the framework diff it against the current state. The per-attribute interpolation system (`d3-interpolate`) is battle-tested and handles edge cases well. Scriba should adopt: (a) a state-diff model for determining what changed between algorithm steps, and (b) type-aware interpolation that handles numbers, colors, and transform strings correctly.

---

## 4. VisuAlgo

### Architecture

VisuAlgo uses a custom animation engine rendering to HTML5 Canvas (with some DOM overlays for UI). The core model is a **command queue**. Each algorithm step produces a list of animation commands (highlight node, move element, swap elements, update label). These commands are pushed into a global queue.

The animation loop dequeues commands one at a time (or in batches for simultaneous animations), executes them as tweens over a configurable duration, and waits for completion before advancing. Playback speed is controlled by scaling the tween duration.

### Step-by-step with play/pause/speed

The UI provides play, pause, step-forward, step-backward, and a speed slider. The queue model makes play/pause trivial: pause simply stops dequeuing. Speed control scales tween durations.

### Backward navigation ("undo")

This is VisuAlgo's most interesting architectural challenge. Each animation command has an **inverse command** stored alongside it. When stepping backward, the engine pops the most recent command from the "executed" stack and runs its inverse. For example:

- "Highlight node 5 red" has inverse "Unhighlight node 5" (restore previous color)
- "Swap elements at index 2 and 4" has inverse "Swap elements at index 4 and 2"
- "Set value of node 3 to 7" has inverse "Set value of node 3 to [previous value]"

This requires capturing the pre-mutation state for each command. In practice, each command stores a snapshot of the affected properties before execution. The backward animation plays the inverse command with the same tween parameters.

This is essentially the **Command pattern** with undo support, applied to animation.

### Output and cost

Output: live canvas in the browser. No export. Runtime cost is minimal -- canvas redraws are fast for the typical element counts in algorithm visualizations (<200 elements). The codebase is a monolithic JavaScript application; bundle size is moderate (~200-300 KB uncompressed) but not optimized for tree-shaking.

### Lessons for Scriba

The command-queue-with-inverse model is the most practical approach for step-by-step backward navigation. It avoids the cost of full state snapshots (only affected properties are captured) while enabling O(1) undo per step. Scriba should adopt a command/event model where each algorithm step emits a list of visual mutations, each paired with its inverse.

---

## 5. Remotion

### Architecture

Remotion treats video as a React application where `useCurrentFrame()` returns the current frame number and `useVideoConfig()` returns fps, width, height, and duration. The entire scene is re-rendered as a React component tree for each frame. There is no imperative animation API -- all motion is derived from the frame number.

```tsx
const frame = useCurrentFrame();
const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: 'clamp' });
return <div style={{ opacity }}>Hello</div>;
```

The `interpolate()` utility maps a frame range to an output range with optional easing. `spring()` provides physics-based animation by computing a spring simulation at the given frame.

### Composition model

Scenes are composed using `<Sequence>` components that offset their children's frame counter:

```tsx
<Sequence from={0} durationInFrames={60}><IntroScene /></Sequence>
<Sequence from={60} durationInFrames={90}><MainScene /></Sequence>
```

Each `<Sequence>` shifts `useCurrentFrame()` so its children see frame 0 at the sequence's start. This is declarative timeline composition.

### SVG handling

Remotion renders whatever React renders. SVG elements work natively -- you animate SVG attributes by deriving them from `useCurrentFrame()`. Libraries like `@remotion/paths` provide utilities for SVG path interpolation and manipulation.

### Rendering pipeline

For preview: React renders in the browser at real-time speed. For export: Remotion opens a headless Chromium instance, navigates to each frame's URL (or renders via React server-side), screenshots, and pipes frames to ffmpeg. This is similar to Manim's offline rendering but uses a browser as the render engine.

### Output and cost

Output: MP4, WebM, GIF, PNG sequences. Rendering cost is dominated by Chromium's paint time per frame. A 30-second video at 30fps = 900 frames, each requiring a full React render + Chromium paint + screenshot. Typical render: 3-15 minutes. Bundle size is irrelevant for video output; for the preview player, it is a standard React app.

### Lessons for Scriba

Remotion's purely declarative model -- where visual state is a pure function of the frame number -- makes the entire animation deterministic and trivially seekable. `state = f(frame)` means random access is O(1): just render frame N. The trade-off is that complex stateful animations (where step N depends on step N-1) must be expressed as pure functions of time, which can be awkward for algorithm visualization where the "state" is an evolving data structure.

For Scriba, the lesson is: if algorithm state at step N can be computed from the initial state + step index (i.e., the algorithm is deterministic and replayable), then a Remotion-like `state = f(step)` model works. But if computing step N requires running all N-1 prior steps, snapshots or caching are needed.

---

## 6. Observable Plot / D3 in Observable

### Architecture

Observable notebooks are reactive documents. Each cell is a reactive expression that re-evaluates when its dependencies change. Animation in Observable typically uses one of three approaches:

1. **Generators as cells**: A cell can be a generator that yields values over time. Observable's runtime calls `next()` on each animation frame, and the yielded value updates the cell. Downstream cells that reference it re-evaluate, producing animated output. Example: a cell yielding incrementing `t` values drives a D3 visualization that redraws on each tick.

2. **D3 transitions within cells**: A cell creates a D3 selection and applies transitions. The transitions run inside the cell's DOM via requestAnimationFrame, same as standalone D3.

3. **Observable Plot's built-in transitions**: Observable Plot (the higher-level charting library) does not have a rich animation API as of 2025. State changes cause full re-renders. Animated transitions between Plot states are typically handled by wrapping Plot output in D3 transitions or by using the generator approach to interpolate data values.

### Responsive SVG animation

Observable renders SVG by default. Responsive sizing is handled by Observable's runtime, which provides `width` as a reactive built-in that updates on window resize. SVG viewBox handles scaling. Animations are resolution-independent because SVG is vector-based.

### Lessons for Scriba

The generator-as-animation-driver pattern (Observable cells that yield over time) is a simpler version of Motion Canvas's generator model. Observable demonstrates that generators are a natural way to express time-varying state in JavaScript. The weakness is that Observable's generator cells are forward-only with no built-in scrubbing.

For algorithm visualization, the most relevant Observable pattern is the "scrubber" input: a slider that drives a reactive variable (e.g., `step`), which in turn drives the visualization. The visualization is a pure function of `step`. This is essentially the Remotion model applied to interactive notebooks.

---

## 7. Algorithm Visualizer (algorithm-visualizer.org)

### Architecture

Algorithm Visualizer is a web application with three panels: code editor, trace/log panel, and visualization canvas. The user writes algorithm code (JavaScript) instrumented with tracer API calls. When executed, the tracer calls produce a **log of visualization commands** (a JSON trace). The visualization panel replays this trace.

### Sequencing model

The algorithm code runs to completion synchronously, emitting trace commands as side effects:

```javascript
const tracer = new Array2DTracer();
tracer.set([3, 1, 4, 1, 5]);      // initial state
tracer.select(0);                    // highlight index 0
tracer.deselect(0);                  // unhighlight
tracer.patch(0, 1, 2);              // swap indices 1 and 2
```

Each tracer call appends a command to the trace log. After execution completes, the visualization player iterates through the log, animating each command sequentially with configurable delay between commands.

### Animation model

Animations are simple CSS transitions or Canvas tweens. Each command type (select, deselect, patch, set) has a corresponding visual animation (color change, position swap). The animations are fire-and-forget with fixed duration.

### Backward navigation

The trace log is an array of commands. Stepping backward is supported by maintaining a parallel array of inverse commands (similar to VisuAlgo) or by re-executing the trace from the beginning up to step N-1. The implementation varies by tracer type, but the general approach is snapshot-based: each command stores enough state to reverse itself.

### Output and cost

Output: live browser visualization. No video export. Runtime cost is trivial -- the trace log is small, and animations are simple CSS/Canvas transitions. Bundle size is moderate (~150 KB).

### Lessons for Scriba

Algorithm Visualizer's trace-log model is the cleanest separation of concerns: algorithm execution is fully decoupled from visualization. The algorithm runs once, produces a trace, and the visualizer replays it independently. This means the algorithm code does not need to "know" about animation -- it just emits events. Scriba should consider this decoupled model: the algorithm emits a trace of state mutations, and the animation runtime replays the trace with appropriate interpolations.

---

## Design Lessons for Scriba

### Abstraction model: imperative play() vs. declarative state-diff vs. generator yield

Three dominant models emerged from this survey:

**Imperative play()** (Manim): The author writes `play(Transform(A, B))`. Advantages: intuitive, mirrors how humans describe animations ("now move X to Y"). Disadvantages: forward-only, hard to seek, tightly couples animation definition to execution order.

**Declarative state-diff** (D3, Remotion, Observable scrubber): The author provides the target state; the framework computes the diff and animates. In Remotion, `state = f(frame)` makes this explicit. In D3, the data join computes enter/update/exit. Advantages: naturally supports random-access seeking (just evaluate f(t) for any t), clean separation of state from presentation. Disadvantages: expressing complex multi-phase animations purely as functions of time can be verbose; algorithm state is naturally sequential, not random-access.

**Generator yield** (Motion Canvas, Observable generators): The author writes sequential code with `yield` at each animation point. The runtime steps through the generator. Advantages: reads like imperative code but is pausable and steppable, natural for sequencing. Disadvantages: forward-only unless combined with snapshots, generator state is opaque (hard to serialize).

**Recommendation for Scriba**: A hybrid. Algorithm steps produce a **trace log** (like Algorithm Visualizer) where each step is a list of state mutations. This gives the declarative state-diff benefit (each step's state is computable from the initial state + applying mutations 0..N). The authoring API should feel like imperative play() calls that internally emit trace entries. The playback runtime can then support both forward animation (apply mutation N with tweening) and backward navigation (apply inverse of mutation N). This combines the intuitiveness of the imperative model with the seekability of the declarative model.

### Interpolation approach: per-attribute vs. snapshot-diff

**Per-attribute interpolation** (D3, Manim, Motion Canvas): Each property (x, y, color, opacity) is interpolated independently with type-aware logic. Numbers lerp, colors interpolate in a perceptual color space, transforms decompose and interpolate components. This is the universal choice across all surveyed systems.

**Snapshot-diff** (conceptual): Diff two complete scene snapshots and interpolate the differences. No surveyed system uses this in pure form because it requires solving the "correspondence problem" (which element in snapshot A maps to which in snapshot B).

**Recommendation for Scriba**: Per-attribute interpolation, following D3's model. Each visual property has a registered interpolator. The mutation trace stores `{target, property, from, to}` tuples. The animation runtime calls `interpolate(from, to, t)` for each property during playback. Ship with interpolators for: numbers, colors (in OKLab for perceptual uniformity), 2D points, SVG transforms, and SVG path data. Allow custom interpolator registration for domain-specific types.

### Step-by-step sequencing: timeline vs. queue vs. automatic

**Timeline** (Remotion, Motion Canvas): Animations are placed on an explicit or implicit timeline with start times and durations. Good for video production, but over-specified for algorithm visualization where step duration should be user-controllable.

**Queue** (VisuAlgo, Algorithm Visualizer): Animation commands are queued and played sequentially. Each command has a duration; the next command starts when the previous finishes. Good for algorithm visualization because the user controls playback speed and can pause between steps.

**Automatic from state diff** (D3): No explicit sequencing -- transitions are triggered by data changes and run concurrently. Sequencing requires manual chaining via `.on('end', ...)`.

**Recommendation for Scriba**: A **step queue** with explicit grouping. Each algorithm step maps to one queue entry. Within a step, multiple mutations can run simultaneously (e.g., swap two elements = translate element A right + translate element B left, concurrently). The queue advances on user input (step forward) or automatically in play mode with configurable inter-step delay. This matches how algorithm visualizations are consumed: step by step, with the ability to pause and inspect.

### Backward/forward navigation and animations

This is the most architecturally significant decision. Three approaches exist:

**Re-render from scratch** (Remotion model): Compute `state = f(step_index)` for any step. Requires that state at step N is computable without running steps 0..N-1 in sequence. For algorithm visualization, this means either re-running the algorithm up to step N (O(N) per seek, acceptable if N is small) or caching states at all steps (O(N) memory, acceptable if states are small).

**Inverse commands** (VisuAlgo model): Each mutation stores its inverse. Stepping backward applies the inverse with a reverse animation. O(1) per step in both directions. Requires that every mutation type has a well-defined inverse. Works naturally for algorithm visualization where mutations are discrete (highlight, swap, set value).

**Keyframe snapshots** (Motion Canvas's implied model): Periodically snapshot the full state. To seek to step N, restore the nearest prior snapshot and fast-forward. Balances memory and seek time.

**Recommendation for Scriba**: **Inverse commands as the primary mechanism, with full-state snapshots as an optimization.** Every mutation in the trace stores `{property, from, to}`. The `from` value *is* the inverse -- to undo, tween from `to` back to `from`. This means backward navigation is free from the trace format itself; no separate inverse storage is needed. Additionally, cache the full visual state at every K-th step (e.g., K=10) for fast random-access seeking via the timeline scrubber.

### Minimum viable animation runtime

Based on the survey, the minimum viable animation runtime for Scriba needs:

1. **Scene graph**: A lightweight tree of visual nodes (rect, circle, line, text, group) with typed properties (position, size, fill, stroke, opacity, transform). Not DOM-based -- use a virtual scene graph that renders to SVG or Canvas. Estimated: 400-600 lines.

2. **Interpolation engine**: Per-property interpolation with type dispatch (number, color, point, path). A registry of interpolator functions. Easing functions (linear, ease-in-out, ease-out-cubic, spring). Estimated: 200-300 lines.

3. **Mutation trace format**: A JSON-serializable array of steps, each step being an array of mutations `{nodeId, property, from, to, easing?, duration?}`. This is the data contract between the algorithm layer and the animation layer. Estimated: 50-100 lines (types and validation).

4. **Playback controller**: Manages current step index, play/pause state, playback speed, and animation progress within the current step. On each frame (via requestAnimationFrame), advances the animation progress, applies interpolated values to the scene graph, and triggers re-render. Handles step-forward, step-backward (using `from`/`to` reversal), and seek-to-step (using cached snapshots). Estimated: 300-400 lines.

5. **Renderer**: Maps the virtual scene graph to SVG elements (preferred for Scriba's document-oriented output) or Canvas draw calls. SVG is recommended because it is resolution-independent, inspectable, and trivially serializable. Estimated: 200-300 lines.

**Total estimated minimum: ~1200-1700 lines of TypeScript.** This excludes the algorithm-to-trace compiler (which is domain-specific) and the UI controls (play/pause/scrubber, which are standard components).

For comparison: D3 transition + interpolate is ~2500 lines. Motion Canvas core is ~15,000 lines. Manim's animation subsystem is ~5,000 lines of Python. A purpose-built runtime for Scriba's constrained use case (algorithm/math visualization, step-based, SVG output) can be significantly smaller because it does not need to handle arbitrary animations, video export, or 3D rendering.

### Summary table

| Concern | Recommended approach | Primary inspiration |
|---|---|---|
| Authoring model | Imperative API that emits a trace log | Algorithm Visualizer, Manim |
| State representation | Virtual scene graph with typed properties | Motion Canvas |
| Interpolation | Per-attribute, type-dispatched, OKLab for color | D3 |
| Sequencing | Step queue with intra-step parallelism | VisuAlgo |
| Backward navigation | Inverse from trace (from/to reversal) + periodic snapshots | VisuAlgo + Remotion |
| Rendering target | SVG (primary), Canvas (optional) | D3 |
| Timing control | User-controlled step advance + configurable auto-play speed | VisuAlgo |
| Seekability | Random-access via cached snapshots every K steps | Remotion + Motion Canvas |
| Bundle budget | Target <5 KB gzipped for the runtime | -- |
