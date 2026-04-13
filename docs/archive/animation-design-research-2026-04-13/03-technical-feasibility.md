# Technical Feasibility: Animation Capabilities in Scriba

**Date:** 2026-04-13
**Constraints:** Self-contained HTML, inline SVG, WAAPI + CSS transitions only, no external libraries, `prefers-reduced-motion` respected, 150-transition mobile cap, SVG regenerated per frame via `innerHTML`.

## Architectural Context

The JS runtime (`emitter.py` lines 908-1112) drives all animation. Key details:

- **`DUR=180`** (180ms) for all WAAPI animations.
- **`animateTransition(toIdx)`** parses the next frame's SVG via `DOMParser`, matches elements by `data-target`, and applies per-element animations on the *current* DOM.
- After WAAPI animations complete (`Promise.all(pending)`), a **full `innerHTML` sync** replaces the DOM with the canonical next-frame SVG (`fs:1` flag).
- **`_canAnim`** gates all animation: `false` when WAAPI is unavailable OR `prefers-reduced-motion: reduce` is active.
- CSS transitions on `[data-target] > rect`, `[data-target] > circle`, etc. already provide 180ms `fill`/`stroke`/`stroke-width` interpolation for class-swap state changes (lines 604-613 of `scriba-scene-primitives.css`).
- The whitelist (`whitelist.py`) controls which SVG attributes pass sanitization. Attributes not in the whitelist cannot appear in the output HTML.

### Animation Lifecycle

```
User clicks "Next" -> animateTransition(toIdx)
  1. Parse next frame SVG (DOMParser)
  2. For each transition record [target, prop, from, to, kind]:
     - Find element by data-target in current DOM
     - Apply WAAPI animation (opacity fade, transform translate, etc.)
  3. Promise.all(pending).then(() => {
       stage.innerHTML = frames[toIdx].svg;  // full sync
     })
```

Animations operate on the **current DOM** between two `innerHTML` swaps. The final canonical SVG always wins. This means WAAPI animations are ephemeral visual polish -- they do not need to produce the final state, only bridge the visual gap between frames.

---

## 1. SVG Path Animation (Draw-On Effect)

### 1a. stroke-dashoffset Animation (Draw-On)

**Can it be done?** Yes.

**How it works:** Set `stroke-dasharray` to the path's total length, then animate `stroke-dashoffset` from that length to 0. The stroke appears to draw itself along the path.

**Browser support:**
| Browser | WAAPI `stroke-dashoffset` | CSS transition `stroke-dashoffset` |
|---------|--------------------------|-----------------------------------|
| Chrome  | Yes (37+)                | Yes (27+)                         |
| Firefox | Yes (48+)                | Yes (28+)                         |
| Safari  | Yes (13.1+)              | Yes (9+)                          |

**Performance:** Excellent. `stroke-dashoffset` is a paint-only property -- no layout, no composite layer promotion needed. A single path draw-on costs ~0.1ms per frame on mobile.

**Code snippet:**

```js
// Inside animateTransition, for kind === 'edge_add' or 'arrow_draw':
var pathEl = stage.querySelector(sel + ' path') || stage.querySelector(sel + ' line');
if (pathEl && pathEl.getTotalLength) {
  var len = pathEl.getTotalLength();
  pathEl.style.strokeDasharray = len;
  pathEl.style.strokeDashoffset = len;
  var a = pathEl.animate(
    [{ strokeDashoffset: len }, { strokeDashoffset: 0 }],
    { duration: DUR, easing: 'ease-out', fill: 'forwards' }
  );
  _anims.push(a); pending.push(a.finished);
}
```

**Limitations:**
- `getTotalLength()` only works on `<path>`, `<line>`, `<polyline>`, `<polygon>`, `<circle>`, `<ellipse>` -- not on `<rect>`. For rect draw-on, convert to a `<path>` equivalent.
- `<line>` elements have `getTotalLength()` in Chrome/Firefox but not reliably in older Safari. Fallback: compute length manually as `Math.hypot(x2-x1, y2-y1)`.
- The path must already exist in the DOM before animating. For edge additions, clone the element from the parsed frame first (as `element_add` already does), then animate.

**Whitelist status:** `stroke-dasharray` is already whitelisted on `<path>`, `<line>`, and `<polyline>`. `stroke-dashoffset` is NOT currently whitelisted -- it would need to be added to the sanitization whitelist for any paths that ship with a pre-set dashoffset. However, since WAAPI sets it via JS (`el.style`), the whitelist is only needed if the emitter sets it as an SVG attribute. For pure WAAPI usage, no whitelist change is needed.

### 1b. Motion Along a Path (offset-path)

**Can it be done?** Partial -- CSS only, not inline SVG attribute.

**How it works:** CSS `offset-path: path('M...')` + `offset-distance: 0%` to `100%` moves an element along an arbitrary SVG path.

**Browser support:**
| Browser | `offset-path` | WAAPI `offset-distance` |
|---------|---------------|------------------------|
| Chrome  | Yes (55+)     | Yes (55+)              |
| Firefox | Yes (72+)     | Yes (72+)              |
| Safari  | Yes (16+)     | Yes (16+)              |

**Performance:** Good. Uses compositor when `offset-distance` is the only animated property. ~0.2ms per element on mobile.

**Code snippet:**

```js
// Move a marker element along an edge path
var marker = stage.querySelector('[data-target="pointer"]');
var edgePath = stage.querySelector('[data-target="G.edge[(A,B)]"] path');
if (marker && edgePath) {
  var d = edgePath.getAttribute('d');
  marker.style.offsetPath = "path('" + d + "')";
  marker.style.offsetRotate = 'auto';
  var a = marker.animate(
    [{ offsetDistance: '0%' }, { offsetDistance: '100%' }],
    { duration: DUR * 2, easing: 'ease-in-out', fill: 'forwards' }
  );
  _anims.push(a); pending.push(a.finished);
}
```

**Limitations:**
- `offset-path` must be set via CSS/JS style, not as an SVG attribute. This is fine for Scriba since the runtime sets it dynamically.
- The path data `d` attribute must use absolute coordinates. Relative path commands work but are harder to extract reliably.
- `offset-rotate: auto` rotates the element to follow the path tangent. Use `offset-rotate: 0deg` to keep orientation fixed.
- Safari 16+ support means this is viable for modern targets but NOT for older iOS devices (iOS 15 and below).

---

## 2. SVG Transform Animation

### 2a. translate / scale / rotate on `<g>` Elements

**Can it be done?** Yes. Already implemented for `position_move` (emitter.py lines 1029-1040).

**Browser support:**
| Browser | WAAPI `transform` on SVG | Notes |
|---------|--------------------------|-------|
| Chrome  | Yes (36+)                | Full support |
| Firefox | Yes (48+)                | Full support |
| Safari  | Yes (13.1+)              | Requires CSS `transform` syntax, not SVG `transform` attribute |

**Performance:** Excellent. `transform` is compositor-friendly. Promotes to GPU layer automatically. ~0.05ms per element.

**Current implementation:**

```js
// position_move (already in emitter.py)
var dx = parseFloat(pf[0]) - parseFloat(pt[0]);
var dy = parseFloat(pf[1]) - parseFloat(pt[1]);
var a9 = el9.animate([
  { transform: 'translate(' + dx + 'px,' + dy + 'px)' },
  { transform: 'translate(0,0)' }
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });
```

**Additional transform animations possible:**

```js
// Scale (zoom in on element)
el.animate([
  { transform: 'scale(0)' },
  { transform: 'scale(1)' }
], { duration: DUR, easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)', fill: 'forwards' });

// Rotate (spin effect)
el.animate([
  { transform: 'rotate(0deg)' },
  { transform: 'rotate(360deg)' }
], { duration: DUR, easing: 'linear', fill: 'forwards' });

// Combined (scale + translate for "fly in")
el.animate([
  { transform: 'translate(-20px, -10px) scale(0.5)', opacity: 0 },
  { transform: 'translate(0, 0) scale(1)', opacity: 1 }
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });
```

**Limitations:**
- **`transform-origin` in SVG:** This is the main gotcha. SVG elements default `transform-origin` to `0 0` (top-left of the SVG viewport), not the element's center. You must explicitly set `transform-origin` via JS:
  ```js
  // For a rect at (x, y) with width w, height h:
  el.style.transformOrigin = (x + w/2) + 'px ' + (y + h/2) + 'px';
  // For a circle at (cx, cy):
  el.style.transformOrigin = cx + 'px ' + cy + 'px';
  ```
- **SVG `transform` attribute vs CSS `transform`:** WAAPI uses CSS `transform` syntax (`translate(Xpx, Ypx)`) which coexists with the SVG `transform` attribute but does not replace it. If an element has both, the CSS transform applies on top of the SVG transform. This is actually useful -- the SVG attribute positions the element, and the CSS/WAAPI transform adds the animation offset.
- **Nested transforms:** Animating `transform` on a `<g>` that already has a `transform` attribute works but the WAAPI animation replaces the CSS transform, not the SVG attribute. The current `position_move` implementation handles this correctly by computing the delta.

### 2b. SVG `d` Path Morphing

**Can it be done?** Partial. CSS `d` property interpolation.

**Browser support:**
| Browser | CSS `d` interpolation | WAAPI `d` |
|---------|-----------------------|-----------|
| Chrome  | Yes (Chrome 89+)      | No        |
| Firefox | Yes (Firefox 97+)     | No        |
| Safari  | Yes (Safari 17.2+)    | No        |

CSS can interpolate the `d` property on `<path>` elements IF both paths have the same number and type of commands. WAAPI cannot animate `d` directly.

**Workaround for WAAPI:** Use CSS transitions on `d` instead:

```js
// Set transition on the path element via CSS
// path { transition: d 180ms ease-out; }
// Then just update the attribute:
pathEl.setAttribute('d', newPathData);
// The CSS transition handles the interpolation
```

**Limitations:**
- Both source and target `d` values must have identical command structure (same number of M, L, C, etc. commands). Scriba's edge paths between graph/tree nodes would need normalized path formats.
- Safari 17.2+ requirement limits iOS support.
- Not recommended for the initial implementation due to cross-browser fragility.

---

## 3. Color / Fill Animation

### 3a. fill, stroke, opacity

**Can it be done?** Yes. Partially already implemented via CSS transitions.

**Current state:** CSS transitions on `[data-target] > rect` already animate `fill`, `stroke`, and `stroke-width` over 180ms when state classes change (scriba-scene-primitives.css lines 604-613).

**WAAPI approach:**

```js
// Animate fill color change
el.animate([
  { fill: '#f8f9fa' },  // idle fill
  { fill: '#0090ff' }   // current fill
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });

// Animate stroke color
el.animate([
  { stroke: '#dfe3e6' },
  { stroke: '#0b68cb' }
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });

// Opacity fade
el.animate([
  { opacity: 1 },
  { opacity: 0.3 }
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });
```

**Browser support:**
| Browser | WAAPI `fill`/`stroke` on SVG | WAAPI `opacity` |
|---------|------------------------------|-----------------|
| Chrome  | Yes (84+)                    | Yes (36+)       |
| Firefox | Yes (80+)                    | Yes (48+)       |
| Safari  | Yes (13.1+)                  | Yes (13.1+)     |

**Performance:**
- `opacity`: Compositor-only, cheapest possible (~0.02ms per element).
- `fill`/`stroke`: Paint operation, slightly more expensive (~0.1ms per element). Still well within budget for 150 elements.

**Limitations:**
- WAAPI `fill`/`stroke` animation on SVG was inconsistent before ~2020. Chrome 84+ and Firefox 80+ are reliable. Safari 13.1+ works but older WebKit versions had bugs.
- CSS transitions on `fill`/`stroke` (which Scriba already uses) are more reliable across browsers than WAAPI for color changes. **Recommendation:** Keep CSS transitions for state-class color morphs. Use WAAPI only for non-class-based color animations (e.g., custom highlight flash).
- `fill` animation does not work on elements whose fill is set via CSS class with `!important`. Scriba's state classes do not use `!important`, so this is not an issue.

### 3b. Gradient Animation (fill spreading)

**Can it be done?** Partial, with workarounds.

WAAPI cannot directly animate SVG `<linearGradient>` stop positions or colors. However, two workarounds exist:

**Approach A -- Animated clip-path reveal (preferred):**

```js
// Simulate a fill spreading from left to right using clip-path
var rect = el.querySelector('rect');
rect.style.clipPath = 'inset(0 100% 0 0)';  // fully clipped
rect.animate([
  { clipPath: 'inset(0 100% 0 0)' },
  { clipPath: 'inset(0 0% 0 0)' }
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });
```

**Approach B -- Overlay rect with animated width:**

```js
// Create an overlay rect that grows to reveal the fill
var overlay = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
overlay.setAttribute('x', x); overlay.setAttribute('y', y);
overlay.setAttribute('width', '0'); overlay.setAttribute('height', h);
overlay.setAttribute('fill', targetFill);
overlay.setAttribute('rx', rx);
parentG.insertBefore(overlay, parentG.querySelector('text'));
overlay.animate([
  { width: '0px' }, { width: w + 'px' }
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });
```

**Limitations:**
- Approach A (`clip-path` on SVG elements) has inconsistent support (see Section 6).
- Approach B requires creating temporary DOM elements, which the `innerHTML` sync will clean up -- this is fine with Scriba's architecture.
- True gradient animation (animating `<stop>` elements) requires SMIL `<animate>` or `requestAnimationFrame` loops, both of which are heavier.

### 3c. CSS Custom Property Animation

**Can it be done?** Yes, with `@property` registration.

```css
@property --scriba-state-current-fill {
  syntax: '<color>';
  inherits: true;
  initial-value: #0090ff;
}
```

Once registered, CSS custom properties with `<color>` syntax can be transitioned/animated. This would allow animating the theme tokens themselves.

**Browser support:**
| Browser | `@property` | WAAPI custom property |
|---------|-------------|----------------------|
| Chrome  | Yes (85+)   | Yes (via CSS transition) |
| Firefox | Yes (128+)  | Yes (via CSS transition) |
| Safari  | Yes (15.4+) | Yes (via CSS transition) |

**Performance:** Same as `fill`/`stroke` -- paint operation.

**Recommendation:** Not recommended for initial implementation. The CSS variable cascade in Scriba is complex (light/dark tokens, state tokens, halo tokens). Animating the variables themselves risks visual glitches during the transition where intermediate values are computed.

---

## 4. Sequencing and Choreography

### 4a. Animation.finished Promise Chaining

**Can it be done?** Yes. Already used (`Promise.all(pending)` at line 1086).

```js
// Sequential: first fade out old, then fade in new
var fadeOut = oldEl.animate([{opacity:1},{opacity:0}], {duration:DUR/2, fill:'forwards'});
fadeOut.finished.then(function() {
  var fadeIn = newEl.animate([{opacity:0},{opacity:1}], {duration:DUR/2, fill:'forwards'});
  return fadeIn.finished;
}).then(function() {
  // all done
});
```

**Browser support:** All browsers with WAAPI support (Chrome 36+, Firefox 48+, Safari 13.1+).

### 4b. Staggered Delays

**Can it be done?** Yes. Use the `delay` option in WAAPI timing.

```js
// Stagger array cell highlights with 30ms delay each
for (var i = 0; i < cells.length; i++) {
  var a = cells[i].animate(
    [{ fill: oldFill }, { fill: newFill }],
    { duration: DUR, delay: i * 30, easing: 'ease-out', fill: 'forwards' }
  );
  _anims.push(a); pending.push(a.finished);
}
```

**Performance consideration:** With 150-element cap and 30ms stagger, the total animation time would be `DUR + 150*30 = 4680ms`. This is too long. **Recommendation:** Cap stagger at 10-15 elements, use ~20ms delay, keeping total time under `DUR + 300ms = 480ms`.

### 4c. GroupEffect / SequenceEffect (WAAPI Level 2)

**Can it be done?** No. Not implemented in any browser.

`GroupEffect` and `SequenceEffect` are part of the Web Animations Level 2 specification. As of April 2026:
- Chrome: Not shipped (behind flag only)
- Firefox: Not implemented
- Safari: Not implemented

**Workaround:** Manual sequencing with `Promise` chains (4a) or staggered delays (4b). Both are fully sufficient for Scriba's needs.

### 4d. Manual Sequencing Pattern

**Recommended approach for Scriba:**

```js
function runPhases(phases) {
  // phases = [[anim1, anim2], [anim3], [anim4, anim5]]
  // Each inner array runs in parallel; arrays run sequentially
  var chain = Promise.resolve();
  for (var p = 0; p < phases.length; p++) {
    (function(phase) {
      chain = chain.then(function() {
        var batch = [];
        for (var j = 0; j < phase.length; j++) {
          batch.push(phase[j].finished);
        }
        return Promise.all(batch);
      });
    })(phases[p]);
  }
  return chain;
}

// Usage: fade out removed elements, then move remaining, then fade in new
runPhases([
  removeAnims,   // phase 1: parallel fade-outs
  moveAnims,     // phase 2: parallel position moves
  addAnims       // phase 3: parallel fade-ins
]).then(function() { _finish(needsSync); });
```

**Performance:** Zero overhead beyond the animations themselves. Promise chaining is negligible.

---

## 5. Text Animation

### 5a. Text Content Change (Counter/Number Animation)

**Can it be done?** Not via WAAPI. Manual JS required.

WAAPI cannot animate `textContent`. For counter/number animations, use `requestAnimationFrame`:

```js
function animateNumber(textEl, from, to, duration) {
  var start = performance.now();
  var diff = to - from;
  function tick(now) {
    var t = Math.min((now - start) / duration, 1);
    var eased = t * (2 - t); // ease-out quad
    textEl.textContent = Math.round(from + diff * eased);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
```

**Performance:** Single `requestAnimationFrame` loop is negligible. For multiple counters, batch all updates in one rAF callback.

**Limitation:** The current `value_change` kind (emitter.py line 982-984) does instant text replacement. To add number animation, the differ would need to emit `from_val` and `to_val` as numbers (not strings), and the runtime would need a `typeof to === 'number'` branch.

### 5b. Text Position Animation (Sliding)

**Can it be done?** Yes, via `transform: translate()`.

```js
// Slide text from old position to new
textEl.animate([
  { transform: 'translateY(-10px)', opacity: 0 },
  { transform: 'translateY(0)', opacity: 1 }
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });
```

**Browser support:** Same as transform animation (Section 2a). Full support.

**Performance:** Compositor-only when combined with opacity. Excellent.

### 5c. Text Opacity Reveal

**Can it be done?** Yes. Already implemented for `element_add` and `annotation_add`.

```js
// Fade in text element
textEl.animate([
  { opacity: 0 },
  { opacity: 1 }
], { duration: DUR, easing: 'ease-in', fill: 'forwards' });
```

### 5d. Character-by-Character Reveal

**Can it be done?** Partial. Requires `<tspan>` per character.

For the emitter to support this, it would need to wrap each character in a `<tspan>` and animate each with a stagger delay:

```js
// Assuming text is split into <tspan> children
var spans = textEl.querySelectorAll('tspan');
for (var i = 0; i < spans.length; i++) {
  spans[i].style.opacity = '0';
  var a = spans[i].animate(
    [{ opacity: 0 }, { opacity: 1 }],
    { duration: DUR / 2, delay: i * 40, fill: 'forwards' }
  );
  _anims.push(a); pending.push(a.finished);
}
```

**Limitation:** Requires SVG structure changes from the Python emitter. Each character as a `<tspan>` increases SVG size significantly. **Not recommended** unless used sparingly for emphasis text.

---

## 6. Clip-path and Mask Animation

### 6a. CSS clip-path on SVG Elements

**Can it be done?** Partial. Browser support is inconsistent for SVG elements specifically.

**CSS `clip-path: inset()` on SVG elements:**
| Browser | Support |
|---------|---------|
| Chrome  | Yes (55+) |
| Firefox | Yes (54+) |
| Safari  | Partial (15+, buggy on `<g>` elements) |

**WAAPI animation of clip-path:**
| Browser | Support |
|---------|---------|
| Chrome  | Yes (Chrome 87+) |
| Firefox | Yes (Firefox 97+) |
| Safari  | No (as of Safari 17.x) -- falls back to no animation |

**Code snippet:**

```js
// Reveal from left to right via clip-path
el.style.clipPath = 'inset(0 100% 0 0)';
var a = el.animate([
  { clipPath: 'inset(0 100% 0 0)' },
  { clipPath: 'inset(0 0% 0 0)' }
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });
```

**Limitations:**
- Safari does not support WAAPI `clip-path` animation. The element will snap to the final state.
- `clip-path` on SVG `<g>` elements behaves differently than on HTML elements. The clipping is in the SVG coordinate space, not the element's local bounding box. `inset()` values are percentages of the element's bounding box only when `clip-path` is applied via CSS (not the SVG `clipPath` attribute).
- **Recommendation:** Use `clip-path` animation as progressive enhancement on Chrome/Firefox. Safari users get instant state change (acceptable degradation since the final state is always correct after `innerHTML` sync).

### 6b. SVG `<mask>` Animation

**Can it be done?** No via WAAPI. SMIL `<animate>` only.

SVG masks reference `<mask>` elements in `<defs>`. The mask's child elements (e.g., a `<rect>`) determine visibility. Animating the mask rect's width/height would create a reveal effect, but:
- WAAPI cannot target elements inside `<defs>` reliably.
- The `<mask>` element's children are not rendered elements -- they are paint servers.
- SMIL `<animate>` could do this but SMIL is deprecated in Chrome and has inconsistent support.

**Recommendation:** Use `clip-path` (6a) or opacity-based reveals instead. Masks are not viable for animation in Scriba's constraint set.

### 6c. SVG `clipPath` Attribute (Not CSS)

The SVG `clipPath` attribute (e.g., `clip-path="url(#myClip)"`) references a `<clipPath>` element in `<defs>`. Animating the geometry inside the `<clipPath>` element has the same SMIL limitation as masks.

**Verdict:** Not recommended. CSS `clip-path: inset()` is the only viable clip-based animation path, and it degrades gracefully on Safari.

---

## 7. Performance Budgets

### 7a. Simultaneous WAAPI Animation Count

| Device Class | Max Simultaneous WAAPI Animations | Notes |
|-------------|----------------------------------|-------|
| Desktop (2024+) | 500+ | No practical limit for simple property animations |
| Mobile mid-range (2023) | 100-150 | Beyond 150, frame drops below 60fps |
| Mobile low-end (2020) | 30-50 | Keep under 50 for smooth 30fps |

Scriba's existing 150-transition cap (`_MAX_TRANSITIONS` in differ.py) is appropriate for the mobile mid-range target.

### 7b. Property Cost Hierarchy

From cheapest to most expensive per animated element:

| Property | Cost | GPU Accelerated | Notes |
|----------|------|-----------------|-------|
| `opacity` | ~0.02ms | Yes | Compositor-only, no repaint |
| `transform` | ~0.05ms | Yes | Compositor-only, no repaint |
| `offset-distance` | ~0.05ms | Yes | Compositor when only animated property |
| `stroke-dashoffset` | ~0.1ms | No | Paint operation, but cheap |
| `fill` / `stroke` | ~0.1ms | No | Paint operation |
| `stroke-width` | ~0.15ms | No | May trigger layout in some browsers |
| `clip-path: inset()` | ~0.2ms | Partial | Chrome composites, Firefox paints |
| SVG `filter` | ~0.5-2ms | Partial | See Section 8 |

### 7c. Total Animation Budget

At DUR=180ms and 60fps target, the browser has 3ms per frame for animation computation (out of 16.6ms frame budget, reserving the rest for layout/paint/composite).

**Safe budget per transition:**
- 150 elements * 0.05ms (transform/opacity) = 7.5ms -- fine at 30fps, tight at 60fps
- 150 elements * 0.1ms (fill/stroke) = 15ms -- at 60fps limit, works at 30fps
- 50 elements * 0.2ms (clip-path) = 10ms -- fine

**Recommendation:** For transitions with >100 elements, prefer `opacity` and `transform`. For transitions with <50 elements, any property is safe.

### 7d. Bail-out Heuristic

```js
// Already in differ.py: skip_animation when > 150 transitions
// Additional runtime heuristic:
if (tr.length > 100 && /Mobi|Android/.test(navigator.userAgent)) {
  // On mobile with many transitions, skip WAAPI and use instant swap
  snapToFrame(toIdx); return;
}
```

### 7e. Memory Impact

Each `Animation` object consumes ~1-2KB of memory. With 150 concurrent animations, that is ~150-300KB. The `_cancelAnims()` function clears the `_anims` array after each transition, releasing references. **No memory concern** at current scale.

However, if animations are created but never garbage collected (e.g., `fill: 'forwards'` keeps the animation alive), they persist until the element is removed. The `innerHTML` sync destroys all animated elements, so this is naturally cleaned up. No action needed.

---

## 8. Particle / Glow Effects

### 8a. SVG Filter Animation (feGaussianBlur, feDropShadow)

**Can it be done?** Partial. Not via WAAPI. CSS `filter` property only.

**CSS `filter` on SVG elements:**

```js
// Glow effect via CSS filter (not SVG filter element)
el.animate([
  { filter: 'drop-shadow(0 0 0px rgba(0,144,255,0))' },
  { filter: 'drop-shadow(0 0 6px rgba(0,144,255,0.6))' }
], { duration: DUR, easing: 'ease-out', fill: 'forwards' });
```

**Browser support:**
| Browser | WAAPI CSS `filter` on SVG | Performance |
|---------|--------------------------|-------------|
| Chrome  | Yes (84+)                | Good (GPU) |
| Firefox | Yes (80+)                | Moderate (CPU) |
| Safari  | Yes (13.1+)              | Moderate |

**Performance warning:** CSS `filter: drop-shadow()` forces a repaint of the entire subtree. On mobile, a single `drop-shadow` animation costs ~0.5-2ms per frame. With multiple elements, this quickly exceeds the budget.

**SVG `<filter>` element animation (feGaussianBlur stdDeviation):**
- WAAPI: Cannot animate `stdDeviation` attribute.
- SMIL `<animate>`: Technically works but SMIL is deprecated in Chrome.
- `requestAnimationFrame` loop: Can manually update `stdDeviation`:

```js
function animateBlur(filterEl, from, to, duration) {
  var blur = filterEl.querySelector('feGaussianBlur');
  var start = performance.now();
  function tick(now) {
    var t = Math.min((now - start) / duration, 1);
    var val = from + (to - from) * t;
    blur.setAttribute('stdDeviation', val);
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
```

**Performance:** SVG filters are the most expensive animation target. Each filter recalculation processes every pixel in the filter region. Budget: max 2-3 simultaneously animated filters on mobile.

**Recommendation:** Use CSS `filter: drop-shadow()` for glow effects on individual highlight elements only (1-3 at a time). Do not animate SVG `<filter>` elements. For a "highlight pulse" effect, prefer animating `stroke-width` or `opacity` which are much cheaper.

### 8b. SMIL `<animate>` Elements

**Can it be done?** Yes, but not recommended.

SMIL (`<animate>`, `<animateTransform>`, `<animateMotion>`) is built into SVG and runs without JS. However:
- Chrome deprecated SMIL in 2015, then reversed the deprecation, but has signaled low priority for new features.
- SMIL does not integrate with WAAPI -- no `.finished` promise, no programmatic control.
- SMIL animations are removed by `innerHTML` sync just like WAAPI, so there is no persistence advantage.

**Verdict:** Avoid SMIL. WAAPI + CSS transitions cover all SMIL use cases with better programmatic control and reduced-motion integration.

### 8c. Lightweight Glow Alternative

Instead of filter-based glow, use a duplicate element with increased stroke-width and reduced opacity:

```js
// Clone the element, give it a wider, semi-transparent stroke
var glow = el.cloneNode(true);
glow.removeAttribute('data-target'); // prevent selector collision
var rect = glow.querySelector('rect') || glow.querySelector('circle');
if (rect) {
  rect.setAttribute('stroke-width', '6');
  rect.setAttribute('stroke-opacity', '0.3');
  rect.setAttribute('fill', 'none');
}
el.parentNode.insertBefore(glow, el);
var a = glow.animate([{opacity:0},{opacity:0.5},{opacity:0}],
  {duration: DUR*2, easing:'ease-in-out', fill:'forwards'});
_anims.push(a); pending.push(a.finished);
```

**Performance:** Same cost as a regular `opacity` animation (~0.02ms). Much cheaper than `drop-shadow`.

---

## 9. Summary Matrix

| Capability | Feasible | Browser Support | Performance | Recommended |
|-----------|----------|-----------------|-------------|-------------|
| stroke-dashoffset draw-on | Yes | All modern | Excellent | Yes |
| offset-path motion | Partial | Chrome/FF/Safari 16+ | Good | Phase 2 |
| transform (translate/scale/rotate) | Yes | All modern | Excellent | Yes (already used) |
| Path `d` morphing | Partial | Chrome 89+/FF 97+/Safari 17.2+ | Good | No (fragile) |
| fill/stroke color | Yes | All modern | Good | Yes (already via CSS) |
| opacity | Yes | All modern | Excellent | Yes (already used) |
| Gradient fill spread | Partial | Chrome/FF only | Moderate | Phase 2 |
| Promise chaining | Yes | All modern | N/A | Yes (already used) |
| Stagger delays | Yes | All modern | N/A | Yes |
| GroupEffect/SequenceEffect | No | None | N/A | No |
| Text number counter | Yes (rAF) | All | Good | Yes |
| Text position slide | Yes | All modern | Excellent | Yes |
| Character reveal | Partial | All modern | Moderate | No (SVG bloat) |
| CSS clip-path reveal | Partial | Chrome/FF (not Safari WAAPI) | Moderate | Progressive enhancement |
| SVG mask animation | No | N/A | N/A | No |
| CSS filter glow | Yes | All modern | Poor on mobile | Sparingly (1-3 elements) |
| SVG filter animation | Manual only | All | Very poor on mobile | No |
| Stroke-based glow | Yes | All modern | Excellent | Yes (preferred glow) |

## 10. Recommended Implementation Priority

### Phase 1 (Safe, high-impact, no new browser requirements)

1. **Stagger delays** on existing element_add / element_remove (20ms per element, capped at 15)
2. **stroke-dashoffset draw-on** for edge/arrow additions
3. **Scale-in for element_add** (replace plain opacity fade with `scale(0.8)->scale(1)` + opacity)
4. **Stroke-based glow pulse** for highlight_on (clone + animated opacity)
5. **Number counter animation** for value_change on numeric values

### Phase 2 (Progressive enhancement, broader browser requirements)

6. **clip-path inset reveal** for cell fill changes (Chrome/Firefox, Safari fallback to instant)
7. **offset-path motion** for pointer/cursor movement along edges
8. **Multi-phase sequencing** (remove -> move -> add ordering via Promise chains)

### Phase 3 (Optional polish)

9. **CSS filter drop-shadow** for emphasis glow (desktop only, mobile bail-out)
10. **Text slide** for label changes

### Not Recommended

- Path `d` morphing (fragile cross-browser, requires path normalization)
- SVG mask animation (no WAAPI support)
- SMIL (deprecated direction, no programmatic control)
- Character-by-character text reveal (SVG size overhead)
- GroupEffect/SequenceEffect (not shipped in any browser)
- Animated SVG filters (performance cost too high for mobile)
