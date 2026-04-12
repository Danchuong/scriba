# Extension E5 — CSS `@keyframes` Animation Slots in Primitives

> **Status:** Accepted extension to `environments.md`. This document
> specifies how SVG primitives may declare compile-time CSS `@keyframes`
> animations for continuous motion effects independent of step navigation.
>
> Cross-references: `environments.md` §3.5 (`\apply`), §8 (HTML output
> shape), §9 (CSS contract); `00-ARCHITECTURE-DECISION-2026-04-09.md` E5 and
> coverage row #4 (FFT twiddle factors); `primitives/plane2d.md` §8.6 (orbit
> coordinates in Plane2D math space); `primitives/graph-stable-layout.md` §8
> (data-layout attribute on stable-layout SVG).

> **Data attribute convention:** All custom data attributes introduced by this
> extension follow the project-wide `data-scriba-<kebab-case-name>` namespace
> (e.g. `data-scriba-beta`, `data-scriba-step-id`). The exception is
> `data-orbit-direction`, which is a preset-specific parameter and is prefixed
> accordingly (`data-scriba-orbit-direction` in new implementations; the bare
> form is retained here for backwards-compatibility with the existing spec text).

---

## 1. Purpose

Filmstrip frames are discrete. Some editorial content requires **continuous,
looping motion** within a single frame — a complex root rotating on the unit
circle, a pulsing pointer indicating the current comparison, an orbiting satellite
in an orbital mechanics diagram. CSS `@keyframes` provides this without any
JavaScript: the browser's compositor handles the animation loop independently of
the filmstrip's fragment-navigation mechanism.

This extension adds a small, fixed vocabulary of animation **presets** that
authors attach to primitive elements via `\apply` parameters. Each preset compiles
to exactly one `@keyframes` block inlined in the `<style>` of the affected frame
or animation. No runtime JS is added; no user-defined CSS is accepted.

### HARD-TO-DISPLAY problems unlocked

| # | Problem | How keyframe animation helps |
|---|---------|------------------------------|
| 4 | FFT butterfly | Twiddle-factor point orbits the unit circle at a fixed period, running independently of step navigation; authors walk through butterfly levels while the point rotates continuously |

The `pulse` preset is also useful for emphasising a current node in a tree or
graph during editorial transitions, and `trail` is useful for tracing path history
in graph search editorials.

---

## 2. Animation preset vocabulary

The vocabulary is intentionally small and closed. Authors choose from exactly
seven presets. Custom `@keyframes` names are not accepted (E1380).

| Preset name             | Duration default | Direction default | Reduced-motion fallback | What it does |
|-------------------------|-----------------|-------------------|-------------------------|--------------|
| `rotate`                | `2s`            | `normal`          | Static (no transform)   | Rotates the target element 360° around its own centre. Useful for spinning indicators. |
| `orbit`                 | `3s`            | `cw`              | Static at initial position | Moves the target element along a circular path centred on a specified anchor point. Designed for complex-root twiddle factors on a `Plane2D` unit circle. |
| `pulse`                 | `1.5s`          | `alternate`       | Static (scale 1)        | Scales the target element between 1× and 1.15× and back, once per period. Useful for "current focus" emphasis. |
| `trail`                 | `2s`            | `alternate`       | Static (full opacity)   | Fades the target element from full opacity to 20% and back. Useful for path-history echoes. |
| `fade-loop`             | `1.5s`          | `alternate`       | Static (full opacity)   | Fades the target element between full opacity and 0. Useful for blinking or highlight-pulse effects. |
| `slide-in-vertical`     | `0.3s`          | `normal`          | Static (final position) | Slides the target element in from above (negative Y offset to zero). Triggered on element append (Stack push). Does **not** synchronise with step navigation. |
| `slide-in-horizontal`   | `0.3s`          | `normal`          | Static (final position) | Slides the target element in from the left (negative X offset to zero). Triggered on element append (Stack push). Does **not** synchronise with step navigation. |

**`slide-in-vertical` and `slide-in-horizontal`** exist specifically to support
the `Stack` primitive push enter-animation (see `primitives/stack.md` §4.1 and
§10). They are triggered when a new Stack item element is appended to the DOM
(on Stack push), not on filmstrip step navigation. They run once per push; they
do not loop. The `duration` parameter applies; no preset-specific extra
parameters are required.

These presets are documented as part of the Scriba authoring guide; they cannot
be extended by authors without modifying the Scriba source.

---

## 3. Grammar

### 3.1 Attaching a preset via `\apply`

Authors attach a keyframe animation to a primitive element using `\apply` with two
new parameters:

```
animate_param  ::= "animate" "=" PRESET_NAME
                 | "duration" "=" DURATION_STRING

PRESET_NAME    ::= "rotate" | "orbit" | "pulse" | "trail" | "fade-loop"
                 | "slide-in-vertical" | "slide-in-horizontal"
DURATION_STRING ::= NUMBER "s" | NUMBER "ms"
```

The `animate` and `duration` parameters are added to the existing `\apply` command
parameter vocabulary (see `environments.md` §3.5). They are valid on any
`\apply` target that selects a single element (not `*.all` or `*.range`):

```latex
\apply{plane.point[0]}{animate="orbit", duration="3s"}
```

To stop an animation on a target, apply `animate="none"`:
```latex
\apply{plane.point[0]}{animate="none"}
```

Like all `\apply` mutations, animation assignment is **persistent** — it carries
forward to all subsequent frames until explicitly overridden.

### 3.2 Preset-specific parameters

Additional parameters refine preset behaviour. These are passed alongside `animate=`:

| Preset   | Extra parameter    | Type   | Default  | Meaning |
|----------|--------------------|--------|----------|---------|
| `orbit`  | `orbit_cx`         | float  | 0.0      | X coordinate of orbit centre in SVG user units |
| `orbit`  | `orbit_cy`         | float  | 0.0      | Y coordinate of orbit centre in SVG user units |
| `orbit`  | `orbit_r`          | float  | 20.0     | Orbit radius in SVG user units |
| `orbit`  | `orbit_direction`  | ident  | `cw`     | `cw` (clockwise) or `ccw` (counter-clockwise) |
| `rotate` | `rotate_cx`        | float  | element centre | X pivot in SVG user units |
| `rotate` | `rotate_cy`        | float  | element centre | Y pivot in SVG user units |
| `pulse`  | `pulse_scale`      | float  | 1.15     | Maximum scale factor (1.0 = no pulse) |
| `trail`  | `trail_min_opacity`| float  | 0.2      | Minimum opacity during trail (0.0–1.0) |

### 3.3 Supported primitives

Keyframe animation is supported on the following primitive types:

| Primitive type | Supported sub-targets | Notes |
|----------------|-----------------------|-------|
| `Plane2D`      | `point[N]`, `segment[N]` | All 7 presets |
| `Graph`        | `node[N]` | All 7 presets |
| `Stack`        | `item[N]` | `slide-in-vertical` and `slide-in-horizontal` only; applied automatically by the Stack emitter on push — authors do not call `\apply{...}{animate=...}` manually for Stack push animation |

Applying `animate=` to a primitive type not in this list is E1382.
Applying `animate=` to `*.all` or `*.range` is also E1382.
`Array`, `Grid`, `DPTable`, `Tree`, `NumberLine` do not support keyframe animation
(they are tabular, not geometric). Authors wishing to animate these primitives
should use `\recolor` / `\highlight` to draw attention to cells.

---

## 4. HTML output shape

### 4.1 Target element classes

When `animate="orbit"` (or any preset) is applied to `plane.point[0]`:

```html
<g data-target="plane.point[0]"
   class="scriba-state-current scriba-animate-orbit"
   style="animation-duration: 3s; --scriba-orbit-cx: 120; --scriba-orbit-cy: 120; --scriba-orbit-r: 50;">
  <!-- SVG circle or path for the point -->
</g>
```

Key output rules:
- The class `scriba-animate-{preset}` is added alongside any existing state classes.
- `animation-duration` is set via an inline `style` attribute (not a CSS class).
- Preset-specific parameters are passed as CSS custom properties in the inline style
  (e.g. `--scriba-orbit-cx`, `--scriba-orbit-r`) so the `@keyframes` rule can
  reference them without generating per-instance rule names.
- The `@keyframes` rule itself is shared across all elements using the same preset
  (it is not duplicated per instance).

### 4.2 Static CSS delivery

All preset `@keyframes` rules and `.scriba-animate-{preset}` class rules live in
the static file `scriba/animation/static/scriba-keyframes.css`, delivered via
`required_css["keyframes/scriba-keyframes.css"]`. **No inline `<style>` block is
injected into the emitted SVG.** Elements receive the class `scriba-animate-{preset}`
and animation parameters via inline `style` properties (CSS custom properties and
`animation-duration`); the keyframe definitions and class rules are resolved by the
external stylesheet.

This design keeps emitted HTML free of inline `<style>` (consistent with
`FORBID_TAGS: ["style"]` in the figure-embed sanitizer for author-provided SVG),
and ensures all preset CSS ships from a single canonical file rather than being
duplicated per frame.

---

## 5. The 7 preset `@keyframes` rules

These are the exact CSS rules that ship in `scriba/animation/static/scriba-keyframes.css`.
They are fixed and are not customisable by authors.

```css
/* 1. rotate — full 360° spin around transform-origin */
@keyframes scriba-rotate {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.scriba-animate-rotate {
  transform-origin: var(--scriba-rotate-cx, 50%) var(--scriba-rotate-cy, 50%);
  animation-timing-function:  linear;
  animation-iteration-count:  infinite;
  animation-direction:        normal;
  animation-fill-mode:        none;
}

/* 2. orbit — circular path via SVG animateMotion equivalent in CSS.
   Because CSS alone cannot describe an arbitrary circular path without
   a <path> element, orbit is implemented via two nested rotation transforms.
   The outer element translates by orbit_r then rotates; the inner counter-
   rotates to keep the element upright. */
@keyframes scriba-orbit-rotate {
  from { transform: rotate(0deg)   translateX(var(--scriba-orbit-r, 20px)) rotate(0deg); }
  to   { transform: rotate(360deg) translateX(var(--scriba-orbit-r, 20px)) rotate(-360deg); }
}
@keyframes scriba-orbit-rotate-ccw {
  from { transform: rotate(0deg)    translateX(var(--scriba-orbit-r, 20px)) rotate(0deg); }
  to   { transform: rotate(-360deg) translateX(var(--scriba-orbit-r, 20px)) rotate(360deg); }
}
.scriba-animate-orbit {
  transform-origin: var(--scriba-orbit-cx, 0px) var(--scriba-orbit-cy, 0px);
  animation-timing-function:  linear;
  animation-iteration-count:  infinite;
  animation-fill-mode:        none;
}

/* 3. pulse — scale breathe */
@keyframes scriba-pulse {
  0%   { transform: scale(1); }
  50%  { transform: scale(var(--scriba-pulse-scale, 1.15)); }
  100% { transform: scale(1); }
}
.scriba-animate-pulse {
  transform-origin: center;
  animation-timing-function:  ease-in-out;
  animation-iteration-count:  infinite;
  animation-fill-mode:        none;
}

/* 4. trail — opacity oscillation */
@keyframes scriba-trail {
  0%   { opacity: 1; }
  50%  { opacity: var(--scriba-trail-min-opacity, 0.2); }
  100% { opacity: 1; }
}
.scriba-animate-trail {
  animation-timing-function:  ease-in-out;
  animation-iteration-count:  infinite;
  animation-fill-mode:        none;
}

/* 5. fade-loop — full opacity oscillation */
@keyframes scriba-fade-loop {
  0%   { opacity: 1; }
  50%  { opacity: 0; }
  100% { opacity: 1; }
}
.scriba-animate-fade-loop {
  animation-timing-function:  ease-in-out;
  animation-iteration-count:  infinite;
  animation-fill-mode:        none;
}

/* 6. slide-in-vertical — enter from above (Stack push) */
@keyframes scriba-slide-in-vertical {
  from { transform: translateY(-100%); opacity: 0; }
  to   { transform: translateY(0);     opacity: 1; }
}
.scriba-animate-slide-in-vertical {
  animation-timing-function:  ease-out;
  animation-iteration-count:  1;
  animation-fill-mode:        both;
}

/* 7. slide-in-horizontal — enter from the left (Stack push) */
@keyframes scriba-slide-in-horizontal {
  from { transform: translateX(-100%); opacity: 0; }
  to   { transform: translateX(0);     opacity: 1; }
}
.scriba-animate-slide-in-horizontal {
  animation-timing-function:  ease-out;
  animation-iteration-count:  1;
  animation-fill-mode:        both;
}
```

---

## 6. Reduced-motion compliance

`animation-name` is intentionally **absent** from the base `.scriba-animate-*`
rules in §5. It is set exclusively inside `@media (prefers-reduced-motion: no-preference)`.
Users who prefer reduced motion therefore see the **static state** of the animated
element (the element as positioned by `\apply`, without motion).

```css
/* Default: no animation applied — element is static for reduced-motion users */
.scriba-animate-rotate,
.scriba-animate-orbit,
.scriba-animate-pulse,
.scriba-animate-trail,
.scriba-animate-fade-loop,
.scriba-animate-slide-in-vertical,
.scriba-animate-slide-in-horizontal {
  /* animation-name intentionally absent here */
}

/* Motion enabled only for users who have NOT requested reduced motion */
@media (prefers-reduced-motion: no-preference) {
  .scriba-animate-rotate          { animation-name: scriba-rotate;           }
  .scriba-animate-orbit           { animation-name: scriba-orbit-rotate;     }
  .scriba-animate-orbit[data-orbit-direction="ccw"] { animation-name: scriba-orbit-rotate-ccw; }
  .scriba-animate-pulse           { animation-name: scriba-pulse;            }
  .scriba-animate-trail           { animation-name: scriba-trail;            }
  .scriba-animate-fade-loop       { animation-name: scriba-fade-loop;        }
  .scriba-animate-slide-in-vertical   { animation-name: scriba-slide-in-vertical;   }
  .scriba-animate-slide-in-horizontal { animation-name: scriba-slide-in-horizontal; }
}
```

For `orbit`, the static state is the initial position: the element appears at its
declared coordinates without orbital offset. For `rotate`, static state is
`transform: none`. For `pulse`, `trail`, `fade-loop`, static state is full opacity
/ scale 1. For `slide-in-vertical` and `slide-in-horizontal`, the static state is
the final rendered position (the item appears already placed, without sliding).

---

## 7. Print rendering

Under `@media print`, all keyframe animations are disabled and elements render in
their static positions:

```css
@media print {
  .scriba-animate-rotate,
  .scriba-animate-orbit,
  .scriba-animate-pulse,
  .scriba-animate-trail,
  .scriba-animate-fade-loop,
  .scriba-animate-slide-in-vertical,
  .scriba-animate-slide-in-horizontal {
    animation: none !important;
  }
}
```

---

## 8. Determinism note

Keyframe animation timing is browser-local. Two browsers rendering the same HTML
will show different animation phases at any given wall-clock moment. This is
acceptable because:

1. The HTML output is byte-identical across builds (no timing information is
   embedded in the HTML).
2. The consumer's content-hash cache (`01-architecture.md` §Versioning) compares
   HTML bytes, not visual appearance.
3. The animation loops continuously so phase offset is cosmetically irrelevant —
   users see the same motion regardless of when they open the page.

The extension does NOT attempt to synchronise keyframe animation start times to
filmstrip navigation. The animation is not paused when the reader is on a
different frame; it loops independently at all times.

---

## 9. Not in scope

The following capabilities are explicitly out of scope for this extension and
MUST NOT be implemented without a new extension spec:

- **Sync with step navigation**: pausing animation on step change, scrubbing
  animation timeline, or timing animation to frame transitions. These require JS.
- **User-controlled playback**: play/pause buttons, speed controls, reverse. These
  require JS.
- **Arbitrary user CSS**: authors writing custom `@keyframes` directly. The preset
  vocabulary is closed to prevent CSS injection and style conflicts.
- **Animation on Array, DPTable, Grid, Tree, NumberLine**: these primitives use
  tabular layout where CSS transform-based animation produces confusing results.
  Use `\recolor` / `\highlight` for visual emphasis on these primitives.
- **SVG SMIL animations** (`<animate>`, `<animateTransform>`): SMIL has inconsistent
  browser support. The CSS `@keyframes` approach is used exclusively.

---

## 10. Error catalog (E1380–E1389)

| Code  | Severity | Meaning                                                              | Hint |
|-------|----------|----------------------------------------------------------------------|------|
| E1380 | **Error** | Unknown preset name in `animate=`                                    | Must be one of: `rotate`, `orbit`, `pulse`, `trail`, `fade-loop`, `slide-in-vertical`, `slide-in-horizontal`, `none`. |
| E1381 | **Error** | Invalid `duration` value (unparseable or zero/negative)              | Use `"3s"` or `"500ms"`. Duration must be positive. |
| E1382 | **Error** | `animate=` applied to an unsupported primitive type or multi-target selector | Only `Plane2D.point[N]`, `Plane2D.segment[N]`, and `Graph.node[N]` support keyframe animation. Cannot use `animate=` on `*.all` or `*.range`. |
| E1383 | Warning  | `duration` provided without `animate=` (parameter is ignored)        | Add `animate=` to activate the preset, or remove `duration=`. |
| E1384 | Warning  | `orbit_r` is 0: orbit animation is invisible                         | Set `orbit_r` to a positive SVG user unit value. |
| E1385 | Warning  | Keyframe animation applied in `\begin{diagram}` (static context)     | Animation will loop in browsers that render the SVG inline; this is allowed but unusual for a single-frame diagram. |

---

## 11. Acceptance test — FFT N=8 butterfly with twiddle factor orbit

An 8-point FFT butterfly diagram with a `Plane2D` unit circle inset. The twiddle
factor point `ω^k` orbits the unit circle at a 3-second period, independent of
step navigation.

```latex
\begin{animation}[id=fft-butterfly, label="FFT N=8: butterfly structure with twiddle factor"]

\shape{butterfly}{Graph}{
  nodes=8,
  layout=fixed,
  directed=true,
  coords=[
    [0,7],[0,5],[0,3],[0,1],
    [4,7],[4,5],[4,3],[4,1]
  ]
}
\shape{plane}{Plane2D}{
  domain=[-1.5,1.5],
  range=[-1.5,1.5],
  width=80,
  height=80,
  show_grid=false
}

\compute{
  import_note = "no imports in Starlark"
  pi = 3.14159265358979
  N = 8
  # Twiddle factor w^1 = e^{-2pi*i/N} initial position
  w_x =  0.707   # cos(-pi/4)
  w_y = -0.707   # sin(-pi/4)
  level_edges = [
    [(0,4),(1,5),(2,6),(3,7)],                 # level 1
    [(0,2),(1,3),(4,6),(5,7)],                 # level 2
    [(0,1),(2,3),(4,5),(6,7)],                 # level 3
  ]
}

% Prelude: place twiddle factor point on unit circle
\apply{plane.point[0]}{x=${w_x}, y=${w_y}, label="ω"}

% Attach orbit animation to the twiddle factor point
\apply{plane.point[0]}{
  animate="orbit",
  duration="3s",
  orbit_cx=0,
  orbit_cy=0,
  orbit_r=50,
  orbit_direction="ccw"
}

\step[label=level1]
\compute{
  edges = level_edges[0]
}
\recolor{butterfly.all}{state=idle}
\apply{butterfly.edge[(0,4)]}{value="ω^0"}
\apply{butterfly.edge[(1,5)]}{value="ω^1"}
\apply{butterfly.edge[(2,6)]}{value="ω^2"}
\apply{butterfly.edge[(3,7)]}{value="ω^3"}
\highlight{butterfly.node[4]}
\highlight{butterfly.node[5]}
\highlight{butterfly.node[6]}
\highlight{butterfly.node[7]}
\narrate{Bước 1 (level 1): 4 butterflies song song. Mỗi edge nhân với $\omega^k$
         ($\omega = e^{-2\pi i/8}$). Điểm $\omega$ đang quay liên tục trên đường tròn đơn vị.}

\step[label=level2]
\recolor{butterfly.node[4]}{state=done}
\recolor{butterfly.node[5]}{state=done}
\recolor{butterfly.node[6]}{state=done}
\recolor{butterfly.node[7]}{state=done}
\apply{butterfly.edge[(0,2)]}{value="ω^0"}
\apply{butterfly.edge[(1,3)]}{value="ω^2"}
\apply{butterfly.edge[(4,6)]}{value="ω^0"}
\apply{butterfly.edge[(5,7)]}{value="ω^2"}
\highlight{butterfly.node[2]}
\highlight{butterfly.node[3]}
\narrate{Bước 2 (level 2): 4 butterflies ở stride 2. Level 1 đã xong (xanh).}

\step[label=level3]
\recolor{butterfly.node[2]}{state=done}
\recolor{butterfly.node[3]}{state=done}
\apply{butterfly.edge[(0,1)]}{value="ω^0"}
\apply{butterfly.edge[(2,3)]}{value="ω^4"}
\apply{butterfly.edge[(4,5)]}{value="ω^0"}
\apply{butterfly.edge[(6,7)]}{value="ω^4"}
\highlight{butterfly.node[0]}
\highlight{butterfly.node[1]}
\narrate{Bước 3 (level 3): stride 4. Sau bước này toàn bộ DFT hoàn chỉnh.
         $\omega$ vẫn tiếp tục quay — animation không đồng bộ với step.}

\end{animation}
```

Expected: all three frames contain the twiddle factor point on the `Plane2D`
inset with class `scriba-animate-orbit` and `style="animation-duration: 3s; ..."`.
The orbit animation loops at 3 seconds per cycle regardless of which frame the
reader is viewing. Reduced-motion users see the point static at its initial
position `(cos(-π/4), sin(-π/4))`. Print renders the point static.

---

## 12. Base-spec deltas

The following changes to `environments.md` are REQUIRED.

1. **§3.5 `\apply`**: Document two new universal parameters for the `\apply`
   command:
   - `animate=<PRESET_NAME | "none">` — attaches or removes a keyframe animation
     preset from the target element. Persistent. Valid only on `Plane2D.point[N]`,
     `Plane2D.segment[N]`, `Graph.node[N]`. Other targets → E1382.
   - `duration=<DURATION_STRING>` — sets the `animation-duration` for the preset.
     Default `"2s"` if not provided. Ignored if `animate=` is not set (warning E1383).

2. **§9 CSS contract**: Note that `required_css` includes
   `scriba/animation/static/scriba-keyframes.css`, which contains `@keyframes`
   rules and `.scriba-animate-{preset}` class rules for all 7 presets defined in
   extension E5. `animation-name` is gated entirely on
   `@media (prefers-reduced-motion: no-preference)`; no inline `<style>` is
   emitted in the SVG output.

3. **§8.1 HTML output**: Note that `<g data-target="...">` elements may carry
   additional class `scriba-animate-{preset}` and inline `style` properties when
   a keyframe animation is active on that target.

4. **§11 Error catalog**: Reserve E1380–E1389 for keyframe animation errors.
