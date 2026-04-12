# Animation Technology Survey for Scriba

**Date:** 2026-04-12
**Scope:** Smooth transitions between algorithm visualization steps — color morphs, node movements, edge draw-in, value changes.

## Scriba Architecture Context

Scriba renders SVG frames inside self-contained HTML files. Each visualization step is a complete SVG fragment stored in a JS array. The widget controller (`~15KB` inlined) swaps frames via `stage.innerHTML = frames[i].svg`. State classes like `scriba-state-current`, `scriba-state-done` are applied to `<g data-target="...">` wrappers containing `<rect>`, `<circle>`, `<text>`, and `<line>` elements. The CSS token system uses `--scriba-state-*-fill`, `--scriba-state-*-stroke`, and `--scriba-state-*-text` custom properties. A `paint-order: stroke fill` halo cascade on `[data-primitive] text` elements provides text readability via `--scriba-halo`. Dark mode flips tokens via `[data-theme="dark"]`.

The current frame-swap model (`innerHTML` replacement) is the key architectural constraint: animation requires either (a) morphing the existing DOM between states instead of replacing it, or (b) cross-fading between complete SVG snapshots. Option (a) is far more powerful (enables per-element stagger, path morphing, position interpolation) but requires a DOM-diffing step. Option (b) is simpler but limits transitions to opacity fades.

---

## 1. CSS Transitions

**How it works.** CSS transitions interpolate property values when a class change alters a computed style. The browser's compositor handles the interpolation natively. When Scriba changes `scriba-state-idle` to `scriba-state-current` on a `<g>` element, adding `transition: fill 200ms ease-out, stroke 200ms ease-out` to the child `<rect>` causes a smooth color morph. No JavaScript is needed beyond the class toggle. However, this requires the DOM elements to persist across frames — the current `innerHTML` swap destroys them, so Scriba would need a DOM-diffing frame update strategy.

**Bundle size:** 0 KB. Pure CSS, no runtime.

**SVG attribute animation:** Partial. CSS can transition `fill`, `stroke`, `opacity`, `transform`, `stroke-dashoffset`, and `stroke-width` on SVG elements in all modern browsers. It cannot transition SVG-specific attributes like `d` (path data), `cx`/`cy` (circle center), `x`/`y` (rect/text position), or `points` (polygon vertices). For node movement, you must use CSS `transform: translate()` rather than changing `x`/`y` attributes directly.

**SVG transform:** Yes. `transform: translate(Xpx, Ypx) scale(S)` transitions work on SVG elements when using CSS transform syntax (not the SVG `transform` attribute string).

**Print fallback:** Trivial. `@media print { * { transition: none !important; } }` disables all transitions. Print renders the final state instantly.

**Reduced motion:** Trivial. `@media (prefers-reduced-motion: reduce) { * { transition-duration: 0s !important; } }` collapses all transitions to instant state changes.

**License:** N/A (browser-native).

**Browser support:** All browsers since 2013. SVG `fill`/`stroke` transitions: Chrome 27+, Firefox 28+, Safari 9+, Edge 12+.

**Integration complexity:** Medium. Requires replacing `innerHTML` swap with DOM diffing/patching so elements persist across frames. The class-toggle mechanism already exists.

**Code snippet — Scriba cell color transition:**

```css
/* Add to scriba state rules */
.scriba-state-idle > rect,
.scriba-state-current > rect,
.scriba-state-done > rect {
  transition: fill 200ms ease-out, stroke 200ms ease-out,
              stroke-width 150ms ease-out;
}

.scriba-state-idle > text,
.scriba-state-current > text,
.scriba-state-done > text {
  transition: fill 200ms ease-out;
}

/* Paint-order halo: transition the halo stroke color too */
[data-primitive] [data-target] > text {
  transition: fill 200ms ease-out, stroke 200ms ease-out;
}

@media (prefers-reduced-motion: reduce) {
  [data-primitive] * { transition-duration: 0s !important; }
}

@media print {
  [data-primitive] * { transition: none !important; }
}
```

```js
// Instead of stage.innerHTML = frames[i].svg, diff and patch:
function applyFrame(stage, frameData) {
  const parser = new DOMParser();
  const newDoc = parser.parseFromString(frameData.svg, 'image/svg+xml');
  const newSvg = newDoc.documentElement;
  // For each <g data-target="...">, update class to trigger CSS transition
  newSvg.querySelectorAll('[data-target]').forEach(newG => {
    const target = newG.getAttribute('data-target');
    const oldG = stage.querySelector(`[data-target="${target}"]`);
    if (oldG) {
      oldG.className.baseVal = newG.className.baseVal;
      // Update text content if changed
      const oldText = oldG.querySelector('text');
      const newText = newG.querySelector('text');
      if (oldText && newText && oldText.textContent !== newText.textContent) {
        oldText.textContent = newText.textContent;
      }
    }
  });
}
```

---

## 2. CSS @keyframes

**How it works.** CSS keyframe animations define multi-step animation sequences that run independently of class changes. Unlike transitions (which interpolate between two states), keyframes can define arbitrary intermediate states, loop, alternate direction, and use complex timing. For Scriba, keyframes would be useful for entrance effects (`fadeIn`, `scaleIn`), pulsing highlights, edge draw-in via `stroke-dashoffset`, and attention-drawing effects. They are not ideal for state-to-state morphing (transitions are better for that).

**Bundle size:** 0 KB. Pure CSS.

**SVG attribute animation:** Same as CSS transitions — `fill`, `stroke`, `opacity`, `transform`, `stroke-dashoffset` work. Path `d` attribute does not.

**SVG transform:** Yes, same as transitions.

**Print fallback:** `@media print { * { animation: none !important; } }` — element renders in its final state (or initial state if `animation-fill-mode` is not `forwards`). Use `animation-fill-mode: forwards` to ensure the final keyframe state is what prints.

**Reduced motion:** `@media (prefers-reduced-motion: reduce) { * { animation-duration: 0s !important; animation-iteration-count: 1 !important; } }` — jumps to final state.

**License:** N/A.

**Browser support:** Universal since 2013.

**Integration complexity:** Small for decorative effects (entrance animations, pulse). Does not solve the core frame-transition problem — that still needs transitions or JS.

**Code snippet — edge draw-in with stroke-dashoffset:**

```css
@keyframes scriba-edge-draw {
  from { stroke-dashoffset: var(--edge-length); }
  to   { stroke-dashoffset: 0; }
}

.scriba-state-current > line.scriba-edge-new {
  stroke-dasharray: var(--edge-length);
  animation: scriba-edge-draw 400ms ease-out forwards;
}

@media (prefers-reduced-motion: reduce) {
  .scriba-edge-new { animation: none !important; stroke-dashoffset: 0; }
}
```

---

## 3. SMIL (SVG Animation)

**How it works.** SMIL (Synchronized Multimedia Integration Language) embeds animation directives directly into SVG markup via `<animate>`, `<animateTransform>`, `<animateMotion>`, and `<set>` elements. Animations are declarative, self-contained within the SVG, and can target any SVG attribute including `d`, `cx`, `cy`, `x`, `y`, and `points` — attributes that CSS cannot transition. SMIL animations can be chained via `begin="prev.end"`, synchronized, and triggered by events. For Scriba, SMIL is the only zero-JS approach that can animate path morphing and position attributes.

**Bundle size:** 0 KB. SVG-native.

**SVG attribute animation:** Full. SMIL can animate every SVG presentation attribute including `d` (path data), `cx`, `cy`, `r`, `x`, `y`, `width`, `height`, `points`, `viewBox`. This is its unique advantage.

**SVG transform:** Yes, via `<animateTransform>`.

**Print fallback:** Poor. SMIL animations are always "running" in the SVG. There is no `@media print` mechanism to disable them. The printed state depends on when the print snapshot occurs. Workaround: use `begin="indefinite"` and trigger via JS, then remove animation elements for print. This is fragile.

**Reduced motion:** No native support. Must use JS to detect `prefers-reduced-motion` and set `begin="indefinite"` or remove `<animate>` elements. Fragile.

**License:** N/A.

**Browser support:** Chrome, Firefox, Safari, Edge (Chromium). Microsoft deprecated SMIL in old Edge but Chromium Edge supports it. Chrome threatened deprecation in 2015 but reversed course. Currently stable, but the spec is not actively developed.

**Integration complexity:** Large. Scriba's Python renderer would need to emit `<animate>` elements inline in SVG markup for each transition. This couples animation timing to the rendering pipeline, bloats SVG size, and makes the print/reduced-motion fallbacks awkward.

**Code snippet — cell fill transition in SMIL:**

```xml
<g data-target="arr.cell.3" class="scriba-state-current">
  <rect x="10" y="10" width="40" height="40" rx="6"
        fill="var(--scriba-state-idle-fill)">
    <animate attributeName="fill"
             from="var(--scriba-state-idle-fill)"
             to="var(--scriba-state-current-fill)"
             dur="200ms" fill="freeze"
             begin="indefinite" id="cell3-fill"/>
  </rect>
  <text x="30" y="35">7</text>
</g>
```

**Verdict:** SMIL's unique path animation capability is valuable, but the poor print/reduced-motion story and the need to embed animation in the SVG markup make it a poor fit as Scriba's primary animation system. Could be used surgically for path morphing only, with JS fallback.

---

## 4. Web Animations API (WAAPI)

**How it works.** WAAPI is the JavaScript interface to the browser's native animation engine — the same engine that powers CSS transitions and keyframes. It provides programmatic control: `element.animate(keyframes, options)` returns an `Animation` object with `play()`, `pause()`, `reverse()`, `cancel()`, `finished` (Promise), and `currentTime` properties. WAAPI can animate any CSS property that CSS transitions can animate, plus it offers precise timing control, grouping (via `Promise.all` on `finished`), and dynamic keyframe generation. For Scriba, WAAPI is the natural evolution: the widget controller already has JS; WAAPI adds zero-dependency animation with full programmatic control.

**Bundle size:** 0 KB. Browser-native API.

**SVG attribute animation:** Same as CSS transitions — `fill`, `stroke`, `opacity`, `transform`, `stroke-dashoffset`, `stroke-width` work. Cannot animate SVG attributes like `d`, `cx`, `cy`, `x`, `y` directly (these are SVG attributes, not CSS properties). Workaround: use CSS `transform: translate()` for position, and `stroke-dashoffset` for edge draw-in.

**SVG transform:** Yes, via CSS `transform` property.

**Print fallback:** Call `animation.finish()` or `animation.cancel()` before print. Or: simply do not start animations when `window.matchMedia('print').matches`. Clean and controllable.

**Reduced motion:** Check `window.matchMedia('(prefers-reduced-motion: reduce)').matches` before animating. If true, apply final state immediately. Clean.

**License:** N/A.

**Browser support:** Chrome 36+, Firefox 48+, Safari 13.1+, Edge 79+. Safari 13.1 (released March 2020) added full support. Pre-13.1 Safari (iOS 12 and earlier, now < 1% of traffic) needs a polyfill. The `web-animations-js` polyfill is 15KB gzipped but is likely unnecessary in 2026.

**Integration complexity:** Medium. Same DOM-diffing requirement as CSS transitions (elements must persist). But WAAPI adds sequencing, staggering, and completion callbacks that CSS transitions lack.

**Code snippet — Scriba cell color transition with stagger:**

```js
function transitionFrame(stage, newFrameData, opts = {}) {
  const duration = reducedMotion() ? 0 : (opts.duration || 200);
  const stagger = reducedMotion() ? 0 : (opts.stagger || 30);
  const animations = [];

  const changes = computeChanges(stage, newFrameData);
  changes.forEach((change, i) => {
    const el = change.element;
    // Animate fill on rect/circle child
    const shape = el.querySelector('rect, circle');
    if (shape && change.oldFill !== change.newFill) {
      animations.push(
        shape.animate(
          [{ fill: change.oldFill }, { fill: change.newFill }],
          { duration, delay: i * stagger, easing: 'ease-out', fill: 'forwards' }
        )
      );
    }
    // Animate text fill (including halo stroke)
    const text = el.querySelector('text');
    if (text && change.oldTextFill !== change.newTextFill) {
      animations.push(
        text.animate(
          [{ fill: change.oldTextFill }, { fill: change.newTextFill }],
          { duration, delay: i * stagger, easing: 'ease-out', fill: 'forwards' }
        )
      );
    }
  });

  // After all animations complete, apply final classes
  return Promise.all(animations.map(a => a.finished)).then(() => {
    applyFinalClasses(stage, newFrameData);
  });
}

function reducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
```

---

## 5. GSAP (GreenSock Animation Platform)

**How it works.** GSAP is a commercial-grade JavaScript animation library that interpolates any numeric property on any object. It uses its own ticker (requestAnimationFrame-based), supports complex timelines with labels, stagger, repeat, yoyo, and custom easing. GSAP can animate SVG attributes directly (including `cx`, `cy`, `x`, `y`, `d` via MorphSVG plugin, `viewBox`) — something no browser-native API can do. Its `gsap.to('.scriba-state-current rect', { fill: '#0090ff', duration: 0.2 })` syntax is concise. Timeline sequencing via `tl.to()` chains is excellent for multi-step algorithm animations.

**Bundle size:** `gsap.min.js` core: ~24KB gzipped. With ScrollTrigger: +9KB. MorphSVG plugin: +5KB (Club GreenSock members only). **This already meets the 25KB budget by itself — no room for plugins.**

**SVG attribute animation:** Full. GSAP treats SVG attributes as first-class. `attr: { cx: 100, cy: 200 }` animates SVG attributes directly. The MorphSVG plugin handles path morphing with point matching.

**SVG transform:** Yes, with its own transform shortcuts (`x`, `y`, `rotation`, `scale`) that work consistently across SVG and HTML.

**Print fallback:** Call `gsap.globalTimeline.pause()` and `gsap.globalTimeline.progress(1)` to jump to end. Or use `gsap.matchMedia()` to disable for print. Requires explicit handling.

**Reduced motion:** `gsap.matchMedia()` can detect `prefers-reduced-motion` and disable or shorten animations. Must be set up explicitly.

**License:** **Standard License is free for public-facing websites only.** "No Charge" license prohibits use in products/tools where end users don't interact with a GSAP-powered page directly. Scriba generates standalone HTML files — if they are viewed in a browser, this should qualify. But if Scriba is sold as a product, the license becomes ambiguous. Club GreenSock ($99/yr for Shockingly Green, $199/yr for Simply Green, $499/yr for Business Green) is required for MorphSVG and some plugins. **License complexity is a risk.**

**Browser support:** IE11+, all modern browsers.

**Integration complexity:** Medium-Large. Must inline the GSAP core (24KB gzipped) into every HTML file. The rich API reduces animation code, but the bundle cost is high for Scriba's budget.

**Code snippet:**

```js
// Inline gsap.min.js (~24KB gzip) in <script> tag
function transitionCell(target, newState) {
  const g = document.querySelector(`[data-target="${target}"]`);
  const rect = g.querySelector('rect');
  const text = g.querySelector('text');
  const fill = getComputedStyle(document.documentElement)
    .getPropertyValue(`--scriba-state-${newState}-fill`);
  const textFill = getComputedStyle(document.documentElement)
    .getPropertyValue(`--scriba-state-${newState}-text`);

  const tl = gsap.timeline();
  tl.to(rect, { fill: fill, stroke: strokeColor, duration: 0.2, ease: 'power2.out' })
    .to(text, { fill: textFill, duration: 0.2, ease: 'power2.out' }, '<');

  g.className.baseVal = `scriba-state-${newState}`;
}
```

---

## 6. anime.js

**How it works.** anime.js is a lightweight JavaScript animation library with a clean declarative API. It supports CSS properties, SVG attributes, DOM attributes, and JavaScript object properties. It provides built-in stagger, timeline sequencing, and path animation (following SVG paths). It uses requestAnimationFrame internally and supports custom easing functions. The API (`anime({ targets: '.el', fill: '#ff0', duration: 200 })`) is concise.

**Bundle size:** anime.js v3: ~17KB minified, ~6.5KB gzipped. anime.js v4 (ESM): ~15KB minified, ~5.5KB gzipped.

**SVG attribute animation:** Yes. Can animate `fill`, `stroke`, `d`, `cx`, `cy`, `r`, `x`, `y`, `points` via attribute targeting. Path morphing works if the paths have the same number of points.

**SVG transform:** Yes, via CSS transform or SVG transform attribute.

**Print fallback:** No built-in mechanism. Must manually pause/complete all animations. Less ergonomic than GSAP's global timeline.

**Reduced motion:** No built-in detection. Must wrap in `if (!reducedMotion)` check manually.

**License:** MIT. Free for any use.

**Browser support:** Chrome 24+, Firefox 28+, Safari 8+, Edge 12+, IE11+.

**Integration complexity:** Small-Medium. 6.5KB gzipped is well within budget. API is simple. No global timeline makes cleanup slightly harder than GSAP.

**Code snippet:**

```js
// Inline anime.min.js (~6.5KB gzip) in <script> tag
function transitionCell(target, newState) {
  const g = document.querySelector(`[data-target="${target}"]`);
  const root = document.documentElement;
  const cs = getComputedStyle(root);

  anime({
    targets: g.querySelector('rect'),
    fill: cs.getPropertyValue(`--scriba-state-${newState}-fill`).trim(),
    stroke: cs.getPropertyValue(`--scriba-state-${newState}-stroke`).trim(),
    duration: 200,
    easing: 'easeOutQuad'
  });

  anime({
    targets: g.querySelector('text'),
    fill: cs.getPropertyValue(`--scriba-state-${newState}-text`).trim(),
    duration: 200,
    easing: 'easeOutQuad'
  });
}
```

---

## 7. Motion One

**How it works.** Motion One (by Matt Perry, creator of Framer Motion) is a WAAPI-based animation library that adds a developer-friendly API on top of the native Web Animations API. It provides `animate()`, `timeline()`, `stagger()`, and `spring()` functions. Because it delegates to WAAPI, animations run on the compositor thread where possible. The library primarily adds ergonomics: spring physics, timeline sequencing, and a cleaner API. It does NOT polyfill WAAPI — it requires native support.

**Bundle size:** `motion` (full): ~3.4KB gzipped. `@motionone/dom` (core animate): ~2.5KB gzipped. `@motionone/svg` (SVG utilities): +~0.8KB.

**SVG attribute animation:** Limited to what WAAPI supports — `fill`, `stroke`, `opacity`, `transform`, `stroke-dashoffset`. Cannot animate `d`, `cx`, `cy`, `x`, `y` (same as raw WAAPI). Motion One's SVG module adds helpers for `stroke-dasharray`/`stroke-dashoffset` line drawing.

**SVG transform:** Yes, via WAAPI's CSS transform.

**Print fallback:** Inherits WAAPI's story — call `animation.finish()` or skip animation entirely under print media query.

**Reduced motion:** Motion One v10+ respects `prefers-reduced-motion` automatically, reducing duration to 0. Older versions require manual checking.

**License:** MIT. Free for any use.

**Browser support:** Same as WAAPI: Chrome 36+, Firefox 48+, Safari 13.1+, Edge 79+.

**Integration complexity:** Small. Tiny bundle, clean API, WAAPI-native. Best trade-off between raw WAAPI (verbose) and full libraries (heavy).

**Code snippet:**

```js
// Inline motion.min.js (~3.4KB gzip)
import { animate, stagger, timeline } from 'motion';

function transitionFrame(stage, changes) {
  const sequence = changes.map((c, i) => [
    c.element.querySelector('rect'),
    { fill: c.newFill, stroke: c.newStroke },
    { duration: 0.2, delay: stagger(0.03), easing: 'ease-out' }
  ]);

  return timeline(sequence);
}
```

---

## 8. D3 Transition

**How it works.** D3's transition module provides data-driven animation by interpolating between bound data states. `d3.select(el).transition().duration(200).attr('fill', newColor)` creates a smooth interpolation. D3 handles SVG attribute interpolation natively — it can interpolate colors, numbers, paths (with matching point counts), and transforms. D3 transitions are chained, delayed, and eased. The key advantage: D3 is designed for exactly the kind of data visualization Scriba produces.

**Bundle size:** `d3-transition` alone: ~3KB gzipped. But it depends on `d3-selection` (~3KB), `d3-interpolate` (~5KB), `d3-ease` (~1.5KB), `d3-timer` (~1KB), `d3-color` (~2KB). Total isolated bundle: **~15KB gzipped**. Full D3 is ~90KB gzipped (far too large).

**SVG attribute animation:** Full. D3 interpolates any SVG attribute including `d` (paths), `cx`, `cy`, `x`, `y`, `points`, `viewBox`. Color interpolation is perceptually correct (Lab color space by default).

**SVG transform:** Yes, via `.attr('transform', ...)` with interpolation.

**Print fallback:** Call `transition.end()` or set `duration(0)`. No built-in media query hook.

**Reduced motion:** Must check manually and set `duration(0)`.

**License:** ISC (BSD-like). Free for any use.

**Browser support:** All modern browsers. No IE11 (irrelevant in 2026).

**Integration complexity:** Large. D3's selection model conflicts with Scriba's template-based SVG generation. D3 wants to own DOM creation via data joins (`enter/update/exit`). Bolting D3 transitions onto externally-generated SVG is possible but fights the library's design. The 15KB dependency cost is also steep.

**Code snippet:**

```js
// Requires inlining d3-selection, d3-transition, d3-interpolate, d3-ease,
// d3-timer, d3-color (~15KB gzip total)
function transitionCell(target, newState) {
  const cs = getComputedStyle(document.documentElement);
  const fill = cs.getPropertyValue(`--scriba-state-${newState}-fill`).trim();

  d3.select(`[data-target="${target}"] rect`)
    .transition()
    .duration(200)
    .ease(d3.easeQuadOut)
    .attr('fill', fill);

  d3.select(`[data-target="${target}"] text`)
    .transition()
    .duration(200)
    .ease(d3.easeQuadOut)
    .attr('fill', textFill);
}
```

---

## 9. Framer Motion

**How it works.** Framer Motion is a React animation library that provides declarative animation via component props (`<motion.div animate={{ opacity: 1 }}>`). It handles layout animations, shared layout transitions, gestures, and spring physics. It is tightly coupled to React's component lifecycle and reconciliation.

**Bundle size:** ~45KB gzipped (full library). `motion/mini` variant: ~5KB gzipped, but React-only.

**SVG attribute animation:** Yes, for CSS-animatable properties. Can animate SVG `d` paths via `pathLength` and morphing utilities.

**SVG transform:** Yes.

**Print fallback:** Would need React rendering — entirely incompatible with Scriba's architecture.

**Reduced motion:** Built-in `useReducedMotion()` hook.

**License:** MIT.

**Browser support:** Modern browsers (React requirement).

**Integration complexity:** XL. **Framer Motion requires React.** Scriba outputs static HTML with vanilla JS. Adopting Framer Motion would mean shipping React (~40KB gzipped) plus Framer Motion (~45KB gzipped) = ~85KB. This exceeds the budget by 3.4x and fundamentally changes the architecture. **Not viable.**

---

## 10. Custom requestAnimationFrame Loop

**How it works.** A hand-rolled animation runtime using `requestAnimationFrame` to interpolate values over time. The developer writes a `lerp` (linear interpolation) function, an easing function, and a render loop that updates SVG attributes each frame. This approach has zero dependency cost and maximum control, but requires implementing color interpolation, easing curves, animation scheduling, and completion callbacks from scratch.

**Bundle size:** ~1-3KB gzipped for a minimal implementation (lerp, easing, scheduler, color parsing).

**SVG attribute animation:** Full. Since you write the interpolation, you can animate any attribute — `d` paths (with point matching), `cx`, `cy`, `x`, `y`, `fill`, `stroke`, transform matrices. No CSS limitations.

**SVG transform:** Yes, full control.

**Print fallback:** Trivial — skip the rAF loop, apply final values directly.

**Reduced motion:** Trivial — check media query, skip interpolation.

**License:** N/A (your own code).

**Browser support:** Universal. `requestAnimationFrame` is supported everywhere since 2012.

**Integration complexity:** Medium-Large initial effort, then Small ongoing. The initial build requires ~200-400 lines of well-tested code. Once built, it is perfectly tailored to Scriba's needs with no API mismatch.

**Code snippet — minimal animation runtime:**

```js
// ~1.5KB gzipped
const SCRIBA_ANIM = (() => {
  const active = new Set();
  let raf = 0;

  function tick(now) {
    for (const a of active) {
      const t = Math.min((now - a.start) / a.dur, 1);
      const e = a.ease(t);
      a.update(e);
      if (t >= 1) { a.resolve(); active.delete(a); }
    }
    raf = active.size > 0 ? requestAnimationFrame(tick) : 0;
  }

  function animate(el, props, opts = {}) {
    const dur = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      ? 0 : (opts.duration || 200);
    if (dur === 0) {
      for (const [k, v] of Object.entries(props)) el.setAttribute(k, v);
      return Promise.resolve();
    }
    const from = {};
    for (const k of Object.keys(props)) from[k] = el.getAttribute(k);
    return new Promise(resolve => {
      const a = {
        start: performance.now() + (opts.delay || 0),
        dur,
        ease: opts.ease || easeOutQuad,
        update(e) {
          for (const [k, to] of Object.entries(props)) {
            el.setAttribute(k, interpolate(from[k], to, e));
          }
        },
        resolve
      };
      active.add(a);
      if (!raf) raf = requestAnimationFrame(tick);
    });
  }

  function easeOutQuad(t) { return t * (2 - t); }

  function interpolate(a, b, t) {
    // Color interpolation for fill/stroke
    if (a.startsWith('#') || a.startsWith('rgb')) {
      return lerpColor(a, b, t);
    }
    // Numeric
    return (+a + (+b - +a) * t).toString();
  }

  function lerpColor(a, b, t) {
    const [ar, ag, ab] = parseHex(a);
    const [br, bg, bb] = parseHex(b);
    const r = Math.round(ar + (br - ar) * t);
    const g = Math.round(ag + (bg - ag) * t);
    const bl = Math.round(ab + (bb - ab) * t);
    return `rgb(${r},${g},${bl})`;
  }

  function parseHex(c) {
    if (c.startsWith('#')) {
      const h = c.length === 4
        ? c[1]+c[1]+c[2]+c[2]+c[3]+c[3]
        : c.slice(1);
      return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)];
    }
    const m = c.match(/\d+/g);
    return m ? m.map(Number) : [0,0,0];
  }

  return { animate };
})();

// Usage for a Scriba cell transition:
const rect = document.querySelector('[data-target="arr.cell.3"] rect');
SCRIBA_ANIM.animate(rect, {
  fill: '#0090ff',
  stroke: '#0b68cb'
}, { duration: 200, delay: 90 });  // delay for stagger
```

---

## Evaluation Matrix

| Technology | Bundle (gzip KB) | SVG attr anim | SVG transform | Print fallback | Reduced motion | License | Browser | Integration |
|---|---|---|---|---|---|---|---|---|
| **CSS Transitions** | 0 | Partial (fill, stroke, opacity, transform) | Yes | Trivial (`@media print`) | Trivial (`@media`) | N/A | Universal | **M** |
| **CSS @keyframes** | 0 | Partial (same as transitions) | Yes | Trivial | Trivial | N/A | Universal | **S** |
| **SMIL** | 0 | **Full** (d, cx, cy, x, y) | Yes | **Poor** (no @media) | **Poor** (no @media) | N/A | All modern | **L** |
| **WAAPI** | 0 | Partial (CSS properties only) | Yes | Good (JS control) | Good (JS check) | N/A | Safari 13.1+ | **M** |
| **GSAP** | 24 | **Full** (via attr plugin) | Yes | Good (global timeline) | Good (matchMedia) | Free non-commercial* | Universal | **M-L** |
| **anime.js** | 6.5 | **Full** (attr targeting) | Yes | Manual | Manual | MIT | Universal | **S-M** |
| **Motion One** | 3.4 | Partial (WAAPI-limited) | Yes | Good (WAAPI) | **Auto** (v10+) | MIT | Safari 13.1+ | **S** |
| **D3 transition** | 15 | **Full** (d, cx, cy, etc.) | Yes | Manual | Manual | ISC | All modern | **L** |
| **Framer Motion** | 45+ (needs React) | Partial | Yes | **N/A** (React required) | Auto | MIT | React only | **XL** |
| **Custom rAF** | 1-3 | **Full** (hand-coded) | Yes | Trivial | Trivial | N/A | Universal | **M** (initial), **S** (ongoing) |

\* GSAP's free license covers public websites. Products/tools may need a paid license ($199-499/yr).

---

## Recommendation: Top 3 for Scriba

### 1. Hybrid: CSS Transitions + Custom rAF micro-runtime (RECOMMENDED)

**Rationale.** Use CSS transitions as the primary mechanism for the most common animation: state class color changes on `fill`, `stroke`, and `opacity`. This covers ~80% of Scriba's animation needs (cell highlight, done-fade, error-flash) at 0KB cost. Add a tiny custom rAF runtime (~1.5KB gzipped) for the remaining 20%: SVG attribute interpolation (`cx`, `cy`, `x`, `y` for node movement), edge draw-in (`stroke-dashoffset`), stagger orchestration, and value text morphing.

**Total budget impact:** ~1.5KB gzipped. Well under the 25KB ceiling. Leaves 23.5KB headroom for future needs.

**Why this wins:**
- The `scriba-state-*` class system is already built for CSS transitions — adding `transition:` rules to existing selectors is the smallest possible change.
- The `paint-order: stroke fill` halo cascade works seamlessly because CSS transitions on `fill` and `stroke` are inherited properties; the halo `--scriba-halo` custom property updates via the class change, and the transition on `stroke` handles the halo color morph automatically.
- Print fallback: `@media print { * { transition: none !important; } }` plus `SCRIBA_ANIM` does nothing when reduced motion is detected.
- Dark mode: `[data-theme="dark"]` custom property values change, and transitions interpolate to the new values — no animation code changes needed.
- The rAF runtime is fully under Scriba's control — no dependency drift, no license risk, no API mismatch.

**Architecture change required:** Replace `stage.innerHTML = frames[i].svg` with a DOM-diffing function that walks `<g data-target="...">` elements and updates classes/attributes on existing nodes. New elements (e.g., new edges added via `add_edge`) get inserted with entrance animations. Removed elements get exit animations before removal. The `data-target` attribute is already a stable key for diffing.

### 2. WAAPI (native, zero-dependency)

**Rationale.** If the team prefers a fully JS-driven approach (no CSS transition rules to maintain), WAAPI provides the same capability as CSS transitions plus programmatic sequencing, stagger, and completion promises. The cost is 0KB, but the code is more verbose, and you still need a custom rAF supplement for SVG-specific attributes (`cx`, `cy`, `d`). The result is essentially the same as option 1, but with more JS and less CSS.

**When to prefer over #1:** If Scriba needs complex orchestration — e.g., "animate cells 0-4 in a wave, then draw the new edge, then highlight the destination" — WAAPI's `Promise.all(animations.map(a => a.finished))` chaining is cleaner than CSS transition event listeners.

**Total budget impact:** ~1.5KB for the rAF supplement.

### 3. anime.js (best pre-built option)

**Rationale.** If the team wants a battle-tested library that handles SVG attribute animation, color interpolation, stagger, and timeline sequencing out of the box, anime.js at 6.5KB gzipped is the best bang-for-buck. It can animate SVG attributes directly (no CSS limitations), has a clean API, MIT license, and universal browser support. The trade-off is 6.5KB of budget and an external dependency.

**When to prefer over #1:** If the custom rAF runtime proves insufficient — e.g., complex path morphing for tree rebalancing, multi-property timeline sequences — and the team does not want to expand the custom runtime.

**Total budget impact:** 6.5KB gzipped.

---

### Not recommended

- **GSAP:** Too large (24KB gzipped for core alone) and license risk for a tool/product.
- **D3 transition:** Too large (15KB), and D3's data-join model clashes with Scriba's template rendering.
- **Framer Motion:** Requires React. Non-starter.
- **SMIL:** Poor print/reduced-motion story. Couples animation to SVG markup in the Python renderer.
- **CSS @keyframes alone:** Good for decorative effects but cannot drive state-to-state morphing. Use as a complement to #1, not as a primary solution.

---

## Next Steps

1. **Prototype the DOM differ.** Write a `diffFrame(stage, newSvgString)` function that uses `data-target` as the reconciliation key. This is the critical enabler regardless of animation technology choice.
2. **Add CSS transition rules.** 10 lines of CSS on existing `.scriba-state-* > rect/circle/text/line` selectors.
3. **Build the rAF micro-runtime.** ~150 lines of vanilla JS for `animate(el, props, opts)` with color interpolation, easing, and Promise-based completion.
4. **Wire into the widget controller.** Replace `stage.innerHTML = ...` with `diffFrame()` + animation calls.
5. **Test print and reduced-motion.** Verify `@media print` disables all animation and `prefers-reduced-motion` collapses durations to 0.
6. **Test halo cascade.** Verify `paint-order: stroke fill` + `--scriba-halo` custom property transitions correctly during color morphs.
