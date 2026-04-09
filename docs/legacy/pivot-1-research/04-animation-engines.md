# Scriba Animation Engine Research

> Research note 04 — choosing an interpolation engine to complement Scriba's discrete step model.

## Executive summary

**Pick: Motion One (`motion.dev`), with a thin Scriba `Tween` layer on top.**

Scriba's current runtime is a step machine: each `step` emits a Delta, and frame N is `apply(frame N-1, Delta)`. This is correct for causality (every change is provable) but visually brutal for anything where position matters — splay rotations, link-cut re-parenting, FFT butterflies, SAM clone chains. We need smooth morphs *between* snapped frames without throwing away the step model.

Motion One wins because it:

1. Is a thin wrapper over the native **Web Animations API (WAAPI)** (`Element.animate`), so morph/tween runs on the browser compositor, not JS. See `motion.dev/docs/quick-start` and `developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API`.
2. Ships a **hybrid animate engine** under 18 KB min+gzip for the `animate()` + `timeline` subset we need; `motion.dev/docs/size`.
3. Supports **scrubbing natively** via `animation.currentTime` and `animation.playbackRate` — WAAPI's killer feature, and exactly what a timeline slider needs.
4. Is MIT-licensed. No commercial gate like GSAP's "no paywalled product" clause.
5. Animates arbitrary SVG elements and CSS custom properties with the same API, which matches Scriba's output (D2 + KaTeX + our own SVG groups).
6. Respects `prefers-reduced-motion` when we opt in; the hook is a one-liner.
7. Actively maintained in 2025 by Matt Perry (ex-Framer Motion core).

GSAP is more powerful but the v3.13+ "no-cost" license still forbids bundling inside commercial SaaS without a Business Green invoice, and it ships 35–70 KB depending on plugins — a bad tradeoff when WAAPI is free and native. Anime.js v4 is a strong second; keep it as fallback if Motion One's timeline DSL turns out too thin for SAM-clone sub-steps.

## Comparison matrix

Legend: Y = yes/good, P = partial, N = no, ? = unverified.

| Engine          | Morph SVG g | Timeline | Sub-step | Scrub | Bundle (min+gz) | License        | Arbitrary SVG | Reduced-motion | Maintained 2025 |
| --------------- | ----------- | -------- | -------- | ----- | --------------- | -------------- | ------------- | -------------- | --------------- |
| **Motion One**  | Y           | Y        | Y        | Y     | ~18 KB          | MIT            | Y             | Y (opt)        | Y               |
| GSAP            | Y           | Y (best) | Y        | Y     | 35–70 KB        | Custom (paid)  | Y             | Y              | Y               |
| anime.js v4     | Y           | Y        | Y        | Y     | ~17 KB          | MIT            | Y             | P (manual)     | Y               |
| Framer Motion   | Y           | Y        | Y        | P     | 50+ KB          | MIT            | Y (React)     | Y              | Y               |
| WAAPI (native)  | Y           | P        | P        | Y     | 0 KB            | n/a            | Y             | P (manual)     | Y               |
| Lottie          | N (baked)   | Y        | Y        | Y     | 60+ KB          | MIT            | N (JSON only) | N              | Y               |
| Rive            | Y           | Y        | Y        | Y     | 120+ KB (wasm)  | MIT (runtime)  | N (rive only) | N              | Y               |
| Theatre.js      | Y           | Y (best) | Y        | Y     | 70+ KB          | Apache-2.0     | Y             | P              | P (slowing)     |
| Velocity.js     | P           | P        | N        | N     | ~15 KB          | MIT            | P             | N              | N (abandoned)   |
| SVG.js animator | Y           | P        | P        | N     | ~20 KB (+core)  | MIT            | Y             | N              | Y               |
| Snap.svg        | Y           | P        | N        | N     | ~40 KB          | Apache-2.0     | Y             | N              | N (stale)       |

## Top 3 deep dive

### 1. Motion One — *the pick*

Motion One exposes two primitives: `animate(element, keyframes, options)` and `timeline([[element, keyframes, options], ...], options)`. Under the hood, whenever the target property is on the WAAPI fast-path (`transform`, `opacity`, `filter`, `clip-path`), it delegates to `element.animate()` — meaning the animation runs off the main thread in Chromium and WebKit. For anything else (CSS custom properties, attribute tweens) it falls back to a rAF loop with the same API surface.

Why this matters for Scriba: every data structure we care about lives in SVG `<g>` containers, and every morph we need is a `transform: translate(x,y) rotate(θ) scale(s)` change plus opacity. That's exactly the compositor fast-path. Splay rotations, link-cut re-parenting, and sliding-window pointers will hit 60 fps even on a school Chromebook.

Scrubbing: the `AnimationControls` object returned by `animate()` exposes `currentTime`, `playbackRate`, `pause()`, `play()`, `finished`. A Scriba timeline slider becomes `controls.currentTime = sliderValue`. No custom tween clock, no drift.

Size: `import { animate, timeline } from "motion"` is ~18 KB min+gz per the published size table (`motion.dev/docs/size`). The mini `animate` standalone is ~4 KB but lacks timeline sequencing, which we need for sub-steps.

Caveats: Motion One's timeline DSL is less expressive than GSAP's (no labels, no `addPause`, limited nested timelines). We wrap it in a Scriba `Tween` abstraction so we can swap engines without touching authoring code.

### 2. GSAP — *the reference point*

GSAP is the industry gold standard. Its Timeline is unmatched: labels, nested timelines, staggered children, `addPause()`, `tweenTo(label)`, MorphSVG, DrawSVG, MotionPath. For splay visualizations the MorphSVG plugin would be delightful. Scrubbing works via `timeline.time(t)` or `timeline.progress(p)`.

Two reasons we do not pick it:

- **License.** As of v3.13 (2024), GSAP moved to a "no-cost for most" model but the Club GreenSock plugins (MorphSVG, DrawSVG, SplitText) and commercial-SaaS usage still require Business Green. Scriba runs inside a paid tenant product, which is exactly the tripwire. Even the core is under GreenSock's standard license, not MIT, which makes downstream redistribution awkward.
- **Bundle.** Core alone is ~35 KB min+gz; with ScrollTrigger and MorphSVG we blow past 70 KB. That eats the entire widget JS budget for a landing-page-shaped runtime.

We keep GSAP as a documented "if the license is cleared, swap the adapter" option.

### 3. anime.js v4 — *the fallback*

Anime.js v4 (rewritten in TS, released 2024) is MIT, ~17 KB, and supports timelines, stagger, scrubbing (`anime.set` + manual `seek`), and SVG morph via `anime.path()`. It is the closest free-and-clear alternative to GSAP in terms of timeline ergonomics.

Why second, not first: anime.js runs its tweens on a single rAF loop in JS, not WAAPI, so very long timelines with many concurrent tweens (FFT butterflies over 256 points) measurably cost more than Motion One's WAAPI delegation. Its reduced-motion handling is manual — you have to read `matchMedia` yourself. Its scrubbing API requires calling `.seek(ms)` on each timeline, which is fine but we'd wrap it anyway.

If Motion One's timeline turns out too limited for SAM clone chains, anime.js is the drop-in replacement behind the `Tween` interface.

## API sketch — integrating with Scriba deltas

Today a step emits a Delta, and the runtime does `frame = apply(frame, delta)`. We extend the Delta vocabulary with a `morph` directive that describes a *visual* transition from the previous frame to the next one, without changing semantics.

```ts
// scriba/runtime/tween.ts
export interface Tween {
  targets: SvgSelector[];                  // e.g. ["#node-7", ".heap-rot"]
  from?: Partial<TweenState>;              // optional override of pre-frame state
  to: Partial<TweenState>;                 // authoritative post-frame state
  duration: number;                        // ms
  easing?: Easing;                         // cubic-bezier | spring | "ease-out-expo"
  delay?: number;
  ghost?: { opacity: number; fade: number }; // leaves a trail
}

export interface TweenState {
  x: number; y: number;
  rotate: number; scale: number;
  opacity: number;
  fill?: string; stroke?: string;
  // compositor-safe only — NO width/height/top/left
}

// A step Delta can now optionally carry tweens alongside its mutations.
export interface Delta {
  mutations: Mutation[];     // existing — state truth
  tweens?: Tween[];          // new — visual transition from prev to this frame
  substeps?: SubStep[];      // new — sequential micro-frames within one editorial step
}
```

In the runtime widget:

```ts
import { animate, timeline } from "motion";

async function playStep(prev: Frame, next: Frame, delta: Delta) {
  // 1. Pre-stage: snap SVG to 'prev' state (idempotent).
  render(prev);

  // 2. Build a Motion One timeline from delta.tweens + delta.substeps.
  const tl = timeline(
    buildSequence(delta),
    { defaultOptions: { easing: "ease-out-expo" }, duration: totalMs(delta) }
  );

  // 3. Expose controls for the scrubber.
  scrubber.bind(tl);

  // 4. Await completion, then commit 'next' as the canonical frame.
  await tl.finished;
  render(next);
}
```

The key invariant: **`render(next)` at the end is always identical to the old step-snap runtime.** Tweens are purely visual; if JS is disabled or `prefers-reduced-motion: reduce` fires, we skip the timeline and call `render(next)` immediately. Correctness unchanged.

## Sub-step / keyframe DSL extension

Today:

```scriba
step "insert key 42" {
  insert(tree, 42)
}
```

Proposed:

```scriba
step "SAM clone state X" {
  substeps {
    @0ms    "highlight parent"    { highlight(parent) }
    @150ms  "spawn clone"         { spawn(clone) ghost(parent, 200ms) }
    @350ms  "rewire suffix links" { morph(edges, 250ms, ease-out-expo) }
    @700ms  "unhighlight"         { clear() }
  }
}
```

The parser compiles `substeps` into a sequenced `Delta.substeps[]`, each with its own tweens. The step is still *one* editorial unit from the reader's perspective (one click on Next), but visually unfolds as a choreographed timeline. Scrubbing lands on intermediate substep boundaries. `ghost(parent, 200ms)` is sugar for a trailing `opacity 1→0` tween on a clone of the `parent` group.

For continuous parameters (rotating calipers, FFT roots of unity) we add an `animate` directive that is not tied to a step at all — it runs on the widget's global clock between steps:

```scriba
animate "calipers-angle" {
  from: 0
  to: 2*PI
  duration: 4000ms
  loop: true
  bind: "#calipers" transform.rotate
}
```

## Bundle size budget

Target: Scriba runtime widget JS **≤ 80 KB min+gz**, aspiring ≤ 50 KB.

| Slice                               | Budget |
| ----------------------------------- | -----: |
| Core step runtime + renderer        |  25 KB |
| Motion One (`animate` + `timeline`) |  18 KB |
| Scriba `Tween` adapter + substep DSL runtime |  4 KB |
| Scrubber UI + keyboard nav          |   6 KB |
| Reserve                             |   7 KB |
| **Total cap**                       | **60 KB** |

KaTeX and D2 outputs are pre-rendered SVG strings cached server-side (see commits `0c36be0`, `699cafc`) and do not count against the runtime JS budget. If we later add `spring` physics, Motion One includes it in the 18 KB; no extra cost.

## Risks and fallbacks

1. **Motion One timeline DSL is too thin.** Risk: SAM clone choreography needs labels or nested timelines Motion One doesn't expose. Mitigation: the `Tween` adapter is engine-agnostic; swap to anime.js v4 behind the same interface. Budget stays intact.
2. **WAAPI SVG transform quirks in Safari.** Safari historically had bugs animating SVG `transform` via WAAPI. As of Safari 17.4+ this is fixed, but we add a feature test and fall back to CSS `transform` on the `<g>` wrapper when the test fails.
3. **Scrubbing past substep boundaries.** If the user drags the slider while a step is mid-tween, we need a "resolve to target frame" path. Mitigation: keep the snap-render fast (`<5 ms`) so we can always bail the timeline and call `render(next)` directly.
4. **Reduced motion**. We must honor `prefers-reduced-motion: reduce`. Mitigation: one-liner in the `Tween` adapter — if set, return a resolved controller that no-ops and calls `render(next)` immediately.
5. **Morphing too many elements.** A splay of 7 nodes is fine. A 256-point FFT butterfly at once is borderline. Mitigation: stagger in bands of 16 and keep per-tween duration short.

## Implementation tasks

1. **`scriba-tween` package.** New workspace package exporting `Tween`, `TweenState`, `playDelta(prev, next, delta)`, `bindScrubber(tl)`. Engine-agnostic interface; first implementation wraps Motion One.
2. **Delta schema v2.** Extend `Delta` with optional `tweens[]` and `substeps[]`. Back-compat: old deltas (no tweens) render exactly as today.
3. **Substep DSL.** Parser extension for `substeps { @Nms "label" { ... } }` and top-level `animate { ... }` blocks. Emit into the new Delta fields.
4. **Scrubber widget.** Slider + play/pause + keyboard (`←/→` step, `Space` play, `Shift+←/→` substep). Binds to `AnimationControls.currentTime`.
5. **Reduced-motion adapter.** Single hook reading `matchMedia('(prefers-reduced-motion: reduce)')`; bypass the timeline when set.
6. **Splay demo.** First consumer: rewrite the splay rotation demo to use `morph` on 5 nodes over 400 ms. This is the visual acceptance test.
7. **Sliding-window pointer demo.** Second consumer: the highlighted rectangle slides across array cells.
8. **SAM clone demo.** Third consumer: exercise `substeps` with 4 micro-frames and a ghost trail on the parent.
9. **Counter chip.** `tween` on a `data-value` attribute with a spring easing; 10 LoC.
10. **Bundle check.** Add a CI size gate on the runtime widget JS: fail the build if min+gz exceeds 80 KB.
11. **Docs.** Author-facing page in `docs/scriba/authoring/` explaining `substeps`, `morph`, `ghost`, `animate` with copy-pasteable examples.

## References

- Motion One docs: https://motion.dev/docs
- Motion One size table: https://motion.dev/docs/size
- Web Animations API: https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API
- anime.js v4: https://animejs.com/documentation/
- GSAP licensing: https://gsap.com/licensing/
- Framer Motion (React-only, excluded): https://motion.dev/docs/react
- `prefers-reduced-motion`: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion
