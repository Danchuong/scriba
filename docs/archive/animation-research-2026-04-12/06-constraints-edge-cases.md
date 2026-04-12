# 06 -- Constraints, Edge Cases & Risk Analysis

> Animation research artifact 06. Scope: identify constraints, edge cases,
> and risk areas for adding frame-to-frame animation to Scriba's interactive
> widget. No code changes; analysis only.
>
> Date: 2026-04-12

---

## 1. Performance

### 1.1 Large DPTable (20x20 = 400 cells)

Each cell is a `<g data-target>` wrapping a `<rect>` + `<text>`. A worst-case
step where every cell changes state means 400 simultaneous fill transitions on
`<rect>` elements plus 400 text-color transitions. The CSS state system
(`scriba-scene-primitives.css` lines 149-298) assigns fill/stroke/text per
state class, so a class-swap approach triggers 400 repaints in one frame.

**Paint budget.** At 60 fps the browser has ~16.6 ms per frame. Each SVG rect
repaint is cheap individually (~0.02 ms on a modern GPU-composited layer), but
400 simultaneous color interpolations via WAAPI or CSS transitions push the
style-recalc phase to 2-5 ms and the paint phase to 3-8 ms on desktop Chrome.
On mobile Safari (iPhone SE, 4 GB RAM) this doubles. Expect dropped frames
above ~200 simultaneous color transitions on low-end devices.

**Recommendation.** Set a threshold: if a transition manifest contains > 150
simultaneous property changes, degrade to instant class-swap (no interpolation).
The emitter already computes per-frame `shape_states` diffs
(`emitter.py:243-309`), so counting changed targets is trivial.

### 1.2 Graph relayout (20 nodes, 30 edges)

Transform animations on `<g>` elements (translate) are compositor-friendly.
WAAPI can handle 20 simultaneous `transform` animations without issue. The
edges (`<line>` elements) must update `x1/y1/x2/y2` attributes, which are NOT
compositor-friendly -- they trigger layout. For 30 edges this is ~1 ms on
desktop, ~3 ms on mobile. Acceptable for v1.

**SVG `vector-effect: non-scaling-stroke`** on Plane2D interacts with
transform animations: the stroke width stays constant during scale, which is
the desired behavior. No conflict found.

### 1.3 Matrix heatmap (viridis, 100 cells)

Each cell has a unique data-driven fill color (not a state class). CSS class
animation cannot handle this. WAAPI with per-element `fill` keyframes is
required. 100 fill interpolations are within budget (see 1.1 threshold of 150).

### 1.4 MetricPlot (8 series x 100 points = 800 SVG elements)

Animating new data-point appearance (opacity 0 to 1 with stagger) on 800
elements is the heaviest case. At 50 ms stagger per point the animation takes
40 seconds -- too long. At 0 ms stagger (all at once) 800 opacity transitions
are ~4 ms style-recalc on desktop. Recommended approach: stagger per-series
(8 groups), not per-point.

### 1.5 Mobile floor

| Device       | RAM  | Browser       | Max simultaneous animations | Notes                    |
|-------------|------|---------------|----------------------------|--------------------------|
| iPhone SE   | 4 GB | Safari 15.4+  | ~100 color, ~50 transform   | Below threshold = snap   |
| Pixel 4a    | 6 GB | Chrome 88+    | ~150 color, ~80 transform   |                          |
| Desktop     | 8 GB | Any modern    | ~300 color, ~150 transform  |                          |

**v1 recommendation.** Max simultaneous animations = 150. Above that, instant
snap with no interpolation.

---

## 2. Print & Static Fallback

### 2.1 Print media

The current CSS (`scriba-scene-primitives.css` lines 645-730) hides the
interactive stage and shows `.scriba-print-frames` with all frames stacked
vertically. Animation JS must not interfere with this:

- Animation JS must be gated behind a check that `window.matchMedia('print')`
  is not active.
- Any WAAPI-applied inline styles must be cleaned up on `beforeprint` event,
  or the print path must use the `.scriba-print-frames` container which is a
  separate DOM tree from the animated stage.
- Current architecture already separates print frames from interactive frames,
  so the risk is LOW as long as animation targets only the interactive
  `.scriba-stage` container.

### 2.2 `--static` CLI flag

`render.py` line 622-625 passes `output_mode="static"` when `--static` is
set. The emitter must check `output_mode` and skip all animation JS/manifest
emission when static. This is a simple conditional gate.

### 2.3 Standalone HTML (render.py)

`render.py` produces self-contained HTML files (`HTML_TEMPLATE` at line 58).
Animation JS must be inlined -- no external script tags, no CDN dependencies.
The JS runtime must work when the file is opened via `file://` protocol
offline, years later. WAAPI is a browser built-in (no library needed), which
makes this feasible.

**KaTeX dependency.** The standalone template already uses a CDN link for
KaTeX CSS (line 607). Animation JS must NOT introduce a second CDN dependency.
The WAAPI wrapper must be fully self-contained inline JS.

### 2.4 Offline durability

WAAPI is a W3C standard implemented in all evergreen browsers since 2020. A
file saved today and opened in 2028 will work. No external dependencies means
no link rot. Risk: LOW.

---

## 3. Accessibility

### 3.1 `prefers-reduced-motion: reduce`

The CSS already handles this (`scriba-scene-primitives.css` lines 604-625)
with `!important` overrides that set `transition-duration: 0.01ms` and
`animation: none`. For WAAPI animations, the JS runtime must query
`matchMedia('(prefers-reduced-motion: reduce)')` at initialization and:

- **Option A:** Set all WAAPI durations to 0 ms (instant). This preserves the
  animation code path but removes visible motion. Preferred -- simpler than
  branching.
- **Option B:** Skip WAAPI entirely and use instant class-swap. Functionally
  identical to Option A with duration=0.

Both options are acceptable. Option A is recommended because it avoids a
separate code path.

The `matchMedia` listener must also handle dynamic changes (user toggles the
OS setting mid-session).

### 3.2 Screen reader announcement timing

The narration div currently uses `aria-live="polite"` and updates via
`innerHTML` swap. With animation, the screen reader should announce the NEW
narration, not an intermediate state. Two strategies:

- **Swap narration at animation START.** The screen reader queues the
  announcement immediately. Visual animation plays in parallel. This is the
  simplest and matches user intent (they clicked Next, they want the next
  narration).
- **Swap narration at animation END.** The screen reader waits 300-800 ms.
  Users with screen readers experience a delay that feels broken.

**Recommendation:** Swap narration HTML at animation start. Visual transitions
are decorative enhancement; narration is the semantic content.

### 3.3 Focus management during animation

If the user tabs into the widget during a transition, focus must land on the
widget container (which has `tabindex="0"` and `.scriba-widget:focus-visible`
styling at line 594-598). Animation must not move focus. SVG elements inside
the stage have `pointer-events: none` on text (line 343, 381), so they are
not focusable. No conflict.

### 3.4 Keyboard navigation during animation

Enter/Space = Next, Shift+Enter = Prev. If the user presses Next during an
active animation:

- **Queue:** Accumulates delay. Bad UX.
- **Interrupt + snap:** Cancel current animation, snap to current target frame,
  then start the new transition. Best UX.

**Recommendation:** Interrupt and snap. Call `animation.finish()` on all active
WAAPI animations, apply the target frame's classes, then begin the next
transition.

---

## 4. CSS Specificity & Halo Cascade

### 4.1 Halo sync during fill transitions

The halo system (`scriba-scene-primitives.css` lines 467-528) uses
`paint-order: stroke fill markers` with `--scriba-halo` set per state class
(e.g., `.scriba-state-current > text { --scriba-halo: var(--scriba-state-current-fill); }`).

If the rect fill is animated via WAAPI (which applies an inline `fill` style),
but the halo color is driven by the CSS class (which changes at animation
start), the halo snaps to the new color instantly while the rect fill
interpolates. This creates a 300 ms window where the halo color mismatches
the visible fill.

**Mitigation options:**

1. **Animate halo in parallel.** Use WAAPI to animate the text `stroke` (halo)
   property alongside the rect `fill`. Doubles the animation count.
2. **Swap class at animation END.** Keep the old class during animation, swap
   at `onfinish`. The halo matches the OLD fill during transition, which is
   less jarring than matching the NEW fill.
3. **Accept the desync.** The halo is 3px and the same general tone as the
   fill. Users are unlikely to notice a 300 ms mismatch.

**Recommendation for v1:** Option 3 (accept desync). Option 2 for v2 if users
report visual artifacts.

### 4.2 WAAPI inline style vs CSS class

WAAPI applies inline styles during animation. Inline `fill` has higher
specificity than `.scriba-state-current > rect { fill: var(...) }`. After
animation completes, the inline style must be removed so the CSS class takes
over. WAAPI's `fill: "forwards"` mode leaves the inline style in place.
Options:

- Use `fill: "none"` or `fill: "auto"` and swap the class in the `onfinish`
  callback.
- Use `fill: "forwards"` and call `animation.commitStyles()` then
  `animation.cancel()` -- but this permanently inlines the style.

**Recommendation:** Use `fill: "none"` fill mode. In the `onfinish` callback:
swap the state class, which applies the correct CSS values. The visual result
is: old-state -> interpolated -> new-state (class).

### 4.3 `!important` rules

The CSS contains `!important` in two places:

1. `@media (prefers-reduced-motion: reduce)` block (lines 604-625): duration
   and animation overrides. These are intentional and should NOT be overridden.
2. `@media print` block (lines 645-730): display overrides. These are
   intentional and should NOT be overridden.

No `!important` rules exist on `fill`, `stroke`, `opacity`, or `transform` in
normal (non-media-query) selectors. WAAPI will not be blocked.

---

## 5. Dark Mode Mid-Animation

### 5.1 The problem

User toggles dark mode while a WAAPI animation is in-flight. The animation
was created with resolved hex values (e.g., `fill: ["#f8f9fa", "#0090ff"]`)
because WAAPI resolves `var()` references at animation creation time. The CSS
custom properties change instantly when `data-theme="dark"` is applied, but
the in-flight WAAPI keyframes still interpolate between the old light-theme
hex values.

**Duration of the glitch:** 300-800 ms (the animation duration). After
`onfinish`, the class swap applies the correct dark-mode colors.

### 5.2 Solution options

| Option | Complexity | Quality |
|--------|-----------|---------|
| Accept the glitch (300 ms) | Zero | Acceptable for v1 |
| Cancel all animations on theme change, snap to target frame | Low | Good |
| Use CSS transitions instead of WAAPI for color properties | Medium | Best -- vars resolve live |
| Re-create WAAPI animations with new resolved values on theme change | High | Overkill |

**Recommendation for v1:** Cancel and snap on theme change. Listen for
`data-theme` attribute mutation (MutationObserver on `<html>`) and call
`finish()` on all active animations.

---

## 6. SVG-Specific Issues

### 6.1 `<foreignObject>` with KaTeX math

KaTeX renders inline math inside `<foreignObject>` elements. These can be
animated for opacity and transform (the `<foreignObject>` wrapper). Content
swap (changing the math expression) requires a full re-render of the KaTeX
HTML inside the foreignObject. This is not animatable -- it must be an instant
swap, optionally with a crossfade (opacity out old, opacity in new).

### 6.2 SVG `filter:` (dim state)

The dim state uses `opacity: 0.5; filter: saturate(0.3)` (line 217-219).
Animating `filter` is expensive (CPU-side rasterization per frame). However,
animating `opacity` alone is compositor-friendly. For dim transitions:

- Animate `opacity` (cheap).
- Snap `filter: saturate()` at animation start or end (no interpolation).

### 6.3 SVG `<path d="...">` animation

Annotation Bezier curves use `<path d="...">`. Animating the `d` attribute
requires either SMIL (deprecated) or WAAPI with the CSS `d` property. Browser
support:

| Browser        | CSS `d` property | Min version |
|---------------|-----------------|-------------|
| Chrome        | Yes             | 88          |
| Firefox       | Yes             | 97          |
| Safari        | Yes             | 15.4        |
| Samsung Internet | Yes          | 18          |

All major browsers support this as of 2024. However, path animation requires
compatible path segments (same number and type of commands). Annotation paths
are generated per-frame and may have different segment counts. **Defer path
animation to v2.** For v1, annotations snap between frames.

### 6.4 `vector-effect: non-scaling-stroke`

Used on Plane2D primitives. This SVG attribute ensures stroke width remains
constant during `transform: scale()` animations. It works correctly with WAAPI
transform animations. No conflict.

---

## 7. Element Lifecycle

### 7.1 Element addition (add_node, add_edge, add_point)

The element does not exist in frame N's DOM but appears in frame N+1. You
cannot animate an element that does not yet exist.

**Strategy:** At transition start, inject the new element into the live DOM
with `opacity: 0`, then animate opacity to 1. The transition manifest must
include an "enter" list of elements to inject. The emitter already diffs
`shape_states` between frames (`emitter.py:243-309`), so identifying new
targets is straightforward.

**Risk:** The new element's SVG markup must be available. Currently each frame
has a pre-rendered SVG string. Extracting individual `<g data-target>` elements
from the target frame SVG for injection requires DOM parsing at runtime.
Complexity: MEDIUM.

### 7.2 Element removal (remove_node, remove_edge)

The element exists in frame N but is absent in frame N+1. Must animate out
(opacity to 0) THEN remove from DOM. But the target frame's SVG does not
contain the element.

**Strategy:** At transition start, keep the old SVG in the DOM. Identify
removed elements. Animate their opacity to 0. On `onfinish`, swap to the
target frame SVG (which omits them naturally).

**Risk:** During the transition, the DOM contains a hybrid of old and new
elements. If new elements are also being added (7.1), the DOM must contain
both the departing and arriving elements simultaneously. This requires
building a composite SVG that unions both frames. Complexity: HIGH.

### 7.3 Reparent (tree node moves)

Element exists in both frames but at different DOM positions (different parent
`<g>` elements). Transform-based animation (FLIP technique) can handle this:
measure old position, swap DOM, measure new position, animate from old to new.

**Complexity:** HIGH. Requires FLIP calculation per reparented element.

**Recommendation:** Defer all three lifecycle animations to v2. For v1, when
elements are added/removed/reparented, use instant SVG swap (no interpolation
for that frame transition).

---

## 8. Frame Skip & Autoplay

### 8.1 Rapid clicking (5x Next in quick succession)

Five transitions queue up. Options:

| Strategy | Behavior | UX quality |
|----------|----------|-----------|
| Queue all | 5 x 300 ms = 1.5 s delay before reaching target | Poor |
| Cancel + snap to latest | Snap to step N+5 instantly, no intermediate | Good |
| Debounce (100 ms) | Accumulate clicks, snap to final target | Good |

**Recommendation:** Cancel current animation (`finish()`), snap to the latest
requested frame. No queuing. This matches how presentation software (Keynote,
Google Slides) handles rapid clicks.

### 8.2 Progress dot jump (step 1 to step 7)

Clicking a progress dot to jump multiple steps must NOT play 6 intermediate
transitions. Instant snap to the target frame. Animation only plays for
single-step navigation (Next/Prev).

### 8.3 Autoplay

If autoplay is added (interval = 2000 ms), the interval timer must wait for
the current transition to complete before starting the next countdown. Use
`onfinish` callback to restart the timer, not `setInterval`.

---

## 9. Backward Navigation

### 9.1 Prev during forward animation

User clicks Prev while a forward animation is playing. The animation must be
cancelled immediately (snap to the frame that was the animation's START, not
its END), then navigate backward.

### 9.2 Reverse animation

Playing transitions in reverse (undo effect) is visually appealing but doubles
the transition manifest size and introduces edge cases (what is the reverse of
an element addition? a removal with fade-out). Not worth the complexity for v1.

**Recommendation:** Backward navigation always uses instant snap. No
interpolation. This is consistent with most step-through educational tools
(e.g., VisuAlgo, Algorithm Visualizer).

---

## 10. File Size Impact

### 10.1 Transition manifest

Each frame-pair transition needs: a list of `(element_id, property, from, to)`
tuples. Estimated per transition:

- Average 10 state changes per step x ~80 bytes per entry = 800 bytes
- 10 steps = 8 KB of manifest data
- With JSON overhead: ~10 KB

### 10.2 JS runtime

A minimal WAAPI wrapper (create animations, handle finish callbacks, reduced-
motion check, keyboard interrupt) is estimated at:

- Unminified: ~4 KB
- Minified: ~2 KB
- Gzipped: ~1 KB

### 10.3 Total overhead

| Component | Size (uncompressed) | Size (gzipped) |
|-----------|-------------------|----------------|
| Transition manifests (10 steps) | ~10 KB | ~3 KB |
| JS runtime | ~4 KB | ~1 KB |
| **Total** | **~14 KB** | **~4 KB** |

Current HTML per cookbook: 30-80 KB. Adding ~14 KB (18-47% increase
uncompressed, ~5% gzipped) is acceptable.

---

## Risk Matrix

| # | Risk area | Severity | Likelihood | Mitigation |
|---|-----------|----------|-----------|------------|
| 1 | **Performance: large DPTable** | MED | MED | Threshold at 150 simultaneous animations; degrade to snap above that |
| 2 | **Print breakage** | LOW | LOW | Animation targets `.scriba-stage` only; print uses separate `.scriba-print-frames` DOM |
| 3 | **Reduced motion ignored** | HIGH | LOW | `matchMedia` check at init + dynamic listener; CSS `!important` fallback already exists |
| 4 | **Halo/fill desync** | LOW | HIGH | Accept for v1 (3px halo, 300 ms window); animate halo in v2 if reported |
| 5 | **Dark mode mid-animation** | MED | LOW | Cancel all animations on theme change, snap to target |
| 6 | **foreignObject re-render** | LOW | MED | Crossfade wrapper; content swap is instant |
| 7 | **Element lifecycle (add/remove)** | HIGH | MED | Defer to v2; use instant snap for frames with element additions/removals |
| 8 | **Rapid click queueing** | MED | HIGH | Cancel + snap to latest; no queue |
| 9 | **Backward animation** | LOW | MED | Always snap backward; no reverse interpolation |
| 10 | **File size bloat** | LOW | LOW | ~14 KB uncompressed overhead; well within budget |
| 11 | **WAAPI inline style vs class** | MED | HIGH | Use `fill: "none"` mode; swap class in `onfinish` callback |
| 12 | **Path `d` animation compat** | LOW | MED | Defer to v2; annotations snap between frames |
| 13 | **SVG filter animation cost** | MED | MED | Animate opacity only; snap `filter: saturate()` |
| 14 | **Screen reader timing** | MED | LOW | Swap narration at animation start, not end |
| 15 | **Keyboard interrupt during animation** | MED | HIGH | `finish()` all active animations on any navigation key |

---

## Version Scoping

### v1 MUST (launch blockers)

- Forward animation for single-step navigation (Next button, Enter key)
- `prefers-reduced-motion` support (duration = 0)
- Print fallback unbroken (animation targets interactive stage only)
- `--static` flag skips all animation emission
- Standalone HTML works offline (inline JS, no CDN)
- Color/opacity/stroke transitions via WAAPI
- Interrupt-and-snap on rapid clicks and keyboard
- Narration swap at animation start for screen readers
- `fill: "none"` WAAPI mode with class swap in `onfinish`
- Performance threshold: > 150 simultaneous changes = instant snap
- Cancel animations on dark mode toggle

### v1 SHOULD (quality targets, not blockers)

- Position lerp for graph node relayout (`transform` animation)
- Stagger groups (e.g., per-row in DPTable, per-series in MetricPlot)
- Configurable speed (0.5x, 1x, 2x via widget control)
- Opacity crossfade for foreignObject content swaps
- Halo color animation in parallel with fill

### v2 DEFER (too complex for initial release)

- Reverse animation (backward interpolation)
- Element lifecycle animation (enter/exit/reparent)
- SVG `<path d>` interpolation for annotation curves
- Autoplay with transition-aware interval
- Per-element stagger within a single primitive (800-point MetricPlot)
- FLIP-based reparent animation for tree restructuring
- Composite SVG construction for simultaneous enter + exit elements

---

## Summary

The highest-risk areas for v1 are **WAAPI inline style management** (risk 11),
**rapid-click handling** (risk 8), **keyboard interrupt** (risk 15), and
**halo desync** (risk 4) -- all rated HIGH likelihood. The mitigations are
well-understood (`fill: "none"` mode, `finish()` on interrupt, accept desync).

The highest-severity risks are **reduced motion compliance** (risk 3) and
**element lifecycle** (risk 7). Reduced motion is mitigated by the existing CSS
`!important` rules plus a JS `matchMedia` check. Element lifecycle is deferred
to v2 entirely.

File size overhead is minimal (~14 KB / ~4 KB gzipped). Performance is
manageable with the 150-animation threshold. The existing separation between
interactive stage and print frames means print/static modes are low risk.

The critical architectural decision is using WAAPI with `fill: "none"` and
class-swap-on-finish, which avoids the inline-style-vs-class specificity war
while keeping the CSS state system (`scriba-scene-primitives.css`) as the
single source of truth for visual state.
