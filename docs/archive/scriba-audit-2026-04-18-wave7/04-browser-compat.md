# Browser Compatibility Audit — Wave 7
**Date:** 2026-04-18
**Source audited:** `scriba/animation/emitter.py`, `scriba/animation/static/*.css`, `render.py`
**Rendered sample:** `examples/tutorial_en.tex` → `tutorial_out.html`
**Target baseline:** Safari 14+, Firefox ESR (128+), Chrome 90+

---

## Summary

| Severity | Count |
|----------|-------|
| HIGH     | 3     |
| MEDIUM   | 6     |
| LOW      | 4     |
| INFO     | 3     |

No ES2020+ features that break target browsers were found in the inline JS. The widget script is written in conservative ES5 `var`-based style throughout — no arrow functions, `const`, `let`, optional chaining (`?.`), nullish coalescing (`??`), `Array.at()`, `Object.hasOwn`, `BigInt`, dynamic `import()`, or top-level `await`. All JS APIs used land within the stated target range with one exception and two medium-severity patterns noted below.

---

## HIGH Severity

### H1 — `matchMedia.addEventListener` — breaks Safari ≤ 13
**File:** `scriba/animation/emitter.py:1089`
**Feature:** `MediaQueryList.addEventListener('change', ...)`

```js
_motionMQ.addEventListener('change', function(ev) { ... });
```

The modern `MediaQueryList.addEventListener` was not supported in Safari until **Safari 14** (released Sep 2020). Safari 13 and earlier only support the deprecated `MediaQueryList.addListener(callback)`. The target floor is stated as Safari 14+, which makes this safe for the stated target — however if the effective floor ever drops to Safari 13 (common in older iOS installs), the reduced-motion listener silently stops working and `_canAnim` is never updated after page load.

**Breaking in:** Safari ≤ 13, iOS 13
**Impact:** `prefers-reduced-motion` changes mid-session are not honoured; user enabling "reduce motion" in Accessibility settings after page load does not disable WAAPI animations.
**Fix:** Guard with a feature-detect or dual-register:
```js
if (_motionMQ.addEventListener) {
  _motionMQ.addEventListener('change', handler);
} else if (_motionMQ.addListener) {
  _motionMQ.addListener(function(mq) { handler({matches: mq.matches}); });
}
```

---

### H2 — `CSS.escape` — absent in all IE, missing in some older Android WebViews
**File:** `scriba/animation/emitter.py:1138, 1188, 1212, 1219, 1227`
**Feature:** `CSS.escape(target)`

```js
var sel = '[data-target="' + CSS.escape(target) + '"]';
```

`CSS.escape` is called in five places inside `_applyTransition` to construct attribute selectors. It is supported in Chrome 46+, Firefox 31+, and Safari 10+, so the stated target browsers are all fine. However the function is called with **no guard**, meaning if it is absent the entire animation engine throws `TypeError: CSS.escape is not a function` and the widget freezes at step 0.

**Breaking in:** Any environment without `CSS.escape` (IE 11, some Android 4.x WebViews). Not a target, but the failure mode is catastrophic rather than graceful.
**Impact:** Complete animation breakage — widget loads but no step transitions work.
**Fix:** Add a polyfill at widget initialisation time or a one-line guard before first use:
```js
if (!window.CSS || !CSS.escape) {
  CSS = { escape: function(s) { return s.replace(/[^\w-]/g, '\\$&'); } };
}
```
A spec-compliant polyfill (`css.escape` on npm, 500 bytes) is the safer option given the regex complexity of the full spec.

---

### H3 — `orient="auto-start-reverse"` — broken in Firefox ≤ 88
**File:** `scriba/animation/emitter.py:342`, `scriba/animation/primitives/graph.py:219`
**Feature:** SVG `<marker orient="auto-start-reverse">`

```python
'<marker id="scriba-arrow" viewBox="0 0 10 10" '
'refX="10" refY="5" '
'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
```

`orient="auto-start-reverse"` is the SVG 2 form that flips the arrowhead automatically for bidirectional edges. Firefox added full support in **Firefox 89** (June 2021). Firefox ESR 78 (widely deployed in enterprise at the time of writing) and any Firefox before 89 silently ignore the `orient` value and render the arrowhead pointing in the wrong direction on the return edge of bidirectional graphs.

**Breaking in:** Firefox ≤ 88 (including Firefox ESR 78)
**Impact:** Directed-graph arrowheads on reverse edges point backward — cosmetic corruption, not a crash.
**Fix:** Use `orient="auto"` for both markers (source and reverse) and emit a separate `<marker>` for each direction, rotating the path 180 ° for the reverse marker. This is the SVG 1.1 approach and is universally supported.

---

## MEDIUM Severity

### M1 — `font-synthesis-weight: none` — no effect in Firefox ≤ 106
**File:** `scriba/animation/static/scriba-scene-primitives.css:356, 393`
**Feature:** `font-synthesis-weight: none`

The longhand `font-synthesis-weight` (as opposed to the shorthand `font-synthesis`) was added to Firefox in **Firefox 107** (November 2022) and to Safari in **Safari 16.4** (March 2023). In older Firefox and Safari the declaration is silently ignored, meaning the browser may faux-bold SVG text glyphs when the chosen weight is unavailable, introducing an unwanted visual artefact in cell labels.

**Breaking in:** Firefox ≤ 106, Safari ≤ 16.3
**Impact:** Cosmetic — faux-bolded text in cells when the loaded font lacks a real 500-weight face.
**Fix:** Add the shorthand fallback above the longhand:
```css
font-synthesis: none;           /* broad compat */
font-synthesis-weight: none;    /* precise override where supported */
```

---

### M2 — `paint-order: stroke fill markers` — partial SVG support in older Safari/Firefox
**File:** `scriba/animation/static/scriba-scene-primitives.css:510`
**Feature:** `paint-order` on SVG `<text>`

```css
@media (forced-colors: none) {
  [data-primitive] text {
    paint-order: stroke fill markers;
```

`paint-order` on SVG text is supported from Chrome 35+, Firefox 60+, and Safari 11+, so no issue with the stated target floor. However the `markers` keyword (the third value) is not used by any inline SVG in scriba (no markers are applied to text) and can be dropped. Additionally, `paint-order` is only meaningful when `stroke` and `stroke-width` are set, which the halo block does. No breaking issue, but the `markers` keyword is dead weight.

**Breaking in:** None within target (Firefox 60+, Safari 11+)
**Impact (risk):** Cosmetic only; `markers` keyword is ignored where unsupported.
**Fix (minor):** Simplify to `paint-order: stroke fill` to match actual usage and avoid misleading `markers` keyword.

---

### M3 — `:where()` specificity pseudo-class — breaks Safari ≤ 13.1, Firefox ≤ 77
**File:** `scriba/animation/static/scriba-scene-primitives.css:322–324, 350–352, 379–380, 388–389`
**Feature:** `:where()` pseudo-class

```css
:where([data-primitive="array"] > [data-target]) > rect { ... }
```

`:where()` is used in twelve selectors across `scriba-scene-primitives.css` to zero-out specificity so state classes win. `:where()` shipped in Chrome 88 (Jan 2021), Firefox 78, and Safari 14. Within the target floor (Chrome 90+, Firefox ESR 128+, Safari 14+) this is fine. Safari 13.1 and Firefox 77 will silently drop all twelve rules, causing cells/nodes/edges to lose their idle-state fill, stroke, and stroke-width defaults — they will render as bare unstyled SVG shapes (black stroke, white fill browser default).

**Breaking in:** Safari ≤ 13.1, Firefox ≤ 77
**Impact:** All primitive cells lose default idle styling — major visual regression.
**Fix:** The `:where()` usage is intentional for specificity control. If the target floor ever drops below the stated one, replace `:where(sel)` with `sel` and adjust specificity by moving state-class rules after default rules, or by using `!important` on state overrides.

---

### M4 — Inline `onclick` attribute on theme toggle — CSP `unsafe-hashes` required
**File:** `render.py:42–45`
**Feature:** Inline event handler attribute

```html
<button class="theme-toggle" onclick="
  var t = document.documentElement.dataset.theme;
  document.documentElement.dataset.theme = t === 'dark' ? 'light' : 'dark';
">Toggle theme</button>
```

The theme toggle uses an `onclick` attribute. Under any Content Security Policy that omits `unsafe-inline`, `unsafe-hashes`, or a matching hash, this handler is silently blocked and the toggle does nothing. The issue was flagged in Wave 6 (05-security.md) and applies identically here. The rendered HTML also has no `<meta http-equiv="Content-Security-Policy">` or nonce on its single `<script>` block.

**Breaking in:** Any deployment behind a strict CSP (Next.js, Vite, GitHub Pages with CSP headers)
**Impact:** Theme toggle silently non-functional; widget JS also blocked without `unsafe-inline` or nonce.
**Fix (theme toggle):** Replace `onclick` with `id="theme-toggle"` and attach the listener in the main `<script>` block. **Fix (widget script):** Add a `nonce` attribute to the `<script>` tag and propagate it through `emit_interactive_html`.

---

### M5 — `DOMParser` SVG parsing loses namespace in some WebKit versions
**File:** `scriba/animation/emitter.py:1298`
**Feature:** `new DOMParser().parseFromString(svg, 'image/svg+xml')`

```js
var parsed = new DOMParser().parseFromString(frames[toIdx].svg, 'image/svg+xml');
```

`DOMParser` with `image/svg+xml` is universally supported (Chrome 4+, Firefox 10+, Safari 3.2+). However, `querySelector` on a parsed SVG document in Safari returns elements using the SVG namespace, which is correct. The animation engine subsequently calls `document.importNode(src, true)` to clone nodes from the parsed tree into the live document. In Safari ≤ 14.0, `importNode` on nodes from a separately-parsed `image/svg+xml` document can silently discard custom data attributes (`data-target`, `data-shape`, `data-annotation`) in rare cases where the SVG element lacks an explicit `xmlns` attribute on the cloned subtree root. The emitter currently emits namespace-less `<g>` child elements inside an `<svg xmlns="...">` root, which is spec-correct but the namespace inheritance through `importNode` is not guaranteed in all Safari 14 minor versions.

**Breaking in:** Safari 14.0 (not 14.1+); rare, version-specific
**Impact:** Cloned animation nodes may lose `data-*` attributes, causing CSS state selectors to miss, leaving cells stuck in their previous visual state.
**Fix:** After `document.importNode`, verify `clone.dataset` is populated. Alternatively parse with `text/html` and extract the SVG subtree via a wrapper `<div>`, which avoids the namespace ambiguity at the cost of one extra DOM level.

---

### M6 — `@media (forced-colors: none)` — ignored in Firefox ≤ 88
**File:** `scriba/animation/static/scriba-scene-primitives.css:508`
**Feature:** `forced-colors` media query

```css
@media (forced-colors: none) {
  [data-primitive] text {
    paint-order: stroke fill markers;
    stroke: var(--scriba-halo, var(--scriba-bg));
    stroke-width: 3;
  }
}
```

`forced-colors` media query is supported from Chrome 89+, Firefox 89+, and Safari 16+. In Firefox ≤ 88, the entire block is silently skipped, meaning the text-halo effect never applies there. Since Firefox ESR 78 is in this range, Windows High Contrast users on older Firefox have the reverse problem from the intent: halo strokes are applied unconditionally (falling through to the non-guarded rules above the block) — but in practice there are no unguarded halo rules, so the halo is simply absent, leaving text less legible when it overflows cells.

**Breaking in:** Firefox ≤ 88, Safari ≤ 15 (no halo rendered)
**Impact:** Cosmetic — text overflow legibility slightly reduced; no hard break.
**Fix:** Acceptable at the stated target floor. If support for Firefox 78 ESR is needed, duplicate the halo rules without the `forced-colors` guard and wrap only the Windows HCM suppression override inside `@media (forced-colors: active)`.

---

## LOW Severity

### L1 — `scroll-snap-type: x mandatory` — Safari ≤ 10 prefix required
**File:** `scriba/animation/static/scriba-embed.css:162`, `scriba-animation.css:42`
**Feature:** CSS Scroll Snap

Both the static filmstrip `<ol class="scriba-frames">` and substory frames list use `scroll-snap-type: x mandatory` / `scroll-snap-align: start`. These are fully supported in Chrome 69+, Firefox 68+, and Safari 11+ without prefixes. No issue at the stated target floor.

**Breaking in:** Safari ≤ 10 (prefix `-webkit-scroll-snap-*` required; not a target)
**Impact (current target):** None. Filmstrip falls back to regular horizontal scroll without snap.
**Fix:** No action needed for stated target. Add `-webkit-` prefix only if iOS 10 must be supported.

---

### L2 — KaTeX `@font-face` declarations lack `font-display`
**File:** Rendered `<style>` block (injected by `scriba/core/css_bundler.py:inline_katex_css`)
**Feature:** `font-display` descriptor on `@font-face`

All 20 KaTeX `@font-face` rules (KaTeX 0.16.11, vendored) omit `font-display`. Because the fonts are inlined as `data:font/woff2;base64,...` URIs the fonts are technically embedded and load synchronously — there is no network fetch, so FOIT/FOUT is not a real concern here. The omission is low-risk in this deployment model.

**Breaking in:** N/A (data URIs load synchronously)
**Impact:** None in standalone rendered HTML. If the `inline_katex_css()` path is bypassed and raw font URLs are served over HTTP, FOIT applies until fonts load.
**Fix (low priority):** Patch `inline_katex_css()` in `css_bundler.py` to inject `font-display:swap` into each `@font-face` block during bundling as a defensive measure for non-data-URI deployment scenarios:
```python
css_text = re.sub(r'(@font-face\{)', r'\1font-display:swap;', css_text)
```

---

### L3 — `Element.closest` — Safari 9 required (fine for target)
**File:** `scriba/animation/emitter.py:1345`
**Feature:** `Element.prototype.closest`

```js
if (e.target.closest('.scriba-substory-widget')) return;
```

`Element.closest` is supported from Chrome 41+, Firefox 35+, and Safari 9+. Fully within target. Noted for completeness as it is called without guard.

**Breaking in:** None within target
**Impact:** None
**Fix:** No action needed.

---

### L4 — `margin-block-*` / `padding-inline-*` logical properties — Safari 12 required
**File:** `scriba/animation/static/scriba-animation.css:26–48`
**Feature:** CSS Logical Properties

```css
.scriba-substory { margin-block-start: 0.75rem; padding-inline-start: 1.5rem; }
```

Logical properties are supported from Chrome 69+, Firefox 41+, Safari 12.1+. All within stated target floor. No issue.

**Breaking in:** Safari ≤ 12.0 (not a target)
**Impact:** Layout direction fallback only.
**Fix:** No action needed for stated target.

---

## INFO — Features Confirmed Safe

### I1 — WAAPI (`Element.animate`) with `fill: 'forwards'`
**File:** `scriba/animation/emitter.py:1151–1210`

WAAPI shipped in Chrome 36+, Firefox 48+, and Safari 13.1+. The emitter guards with `typeof Element.prototype.animate === 'function'` before using it, and falls back to `snapToFrame()` when absent. The `fill: 'forwards'` option and `animation.finished` Promise are both supported in all target browsers. Safe.

### I2 — `MutationObserver` for theme change detection
**File:** `scriba/animation/emitter.py:1349–1352`

```js
if (typeof MutationObserver !== 'undefined') {
  new MutationObserver(...).observe(document.documentElement, {...});
}
```

Properly guarded. `MutationObserver` is universal since Chrome 26, Firefox 14, Safari 7. The `attributeFilter` option is supported since the same versions. Safe.

### I3 — SVG inline with no `<foreignObject>`, no masks, no `<filter>`, no `<use>`
The rendered `tutorial_out.html` uses only basic SVG primitives (`<g>`, `<rect>`, `<circle>`, `<line>`, `<path>`, `<text>`, `<polygon>`, `<marker>`). No `foreignObject`, no CSS `filter` on SVG elements, no `clip-path`, no `mask`, no `<symbol>`/`<use>`. This eliminates an entire class of cross-browser SVG edge cases. The sole SVG 2 feature in use is `orient="auto-start-reverse"` on graph arrowhead markers, covered under H3.

---

## Quick-Fix Priority

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| H3 | Replace `orient="auto-start-reverse"` with two separate `orient="auto"` markers | Low | Corrects graph arrows in Firefox ≤ 88 |
| H1 | Dual-register `matchMedia` listener | Trivial | Fixes reduced-motion updates in Safari 13 |
| H2 | Add `CSS.escape` polyfill guard | Low | Prevents catastrophic freeze in non-target envs |
| M4 | Move `onclick` to `<script>` block; add `nonce` to widget script | Medium | CSP compliance |
| M1 | Add `font-synthesis: none` shorthand above the longhand | Trivial | Fixes faux-bold in Firefox ≤ 106 |
| L2 | Inject `font-display:swap` in `inline_katex_css()` | Trivial | Defensive for non-data-URI deployment |
