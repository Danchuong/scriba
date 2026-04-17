# Scriba Animation Runtime — JS & Accessibility Audit

**Date**: 2026-04-17  
**Auditor**: Claude Sonnet 4.6 (automated static + DOM analysis)  
**Fixtures rendered**: `examples/tutorial_en.tex`, `examples/primitives/queue.tex`, `examples/primitives/graph.tex`  
**Files inspected**:
- `scriba/animation/emitter.py` (59 KB — contains all widget JS inline)
- `scriba/animation/static/scriba-embed.css`
- `scriba/animation/static/scriba-scene-primitives.css`
- `scriba/animation/static/scriba-standalone.css`
- `scriba/animation/static/scriba-animation.css`
- `scriba/animation/primitives/base.py` (annotation rendering)
- `render.py` (HTML template and asset bundling)

---

## Summary

The scriba interactive widget is a functionally solid single-page widget with reasonable keyboard support and a working aria-live narration channel. The major a11y gaps are:

1. **No `role` or `aria-label` on the widget container div** — screen readers announce silence or a generic group when the widget receives focus via Tab.
2. **Arrow keys on focused substory buttons bubble to the parent widget** — pressing ArrowRight while a sub-step button has focus advances the main widget frame, not the sub-step.
3. **Buttons are undersized for touch** — estimated height ~29 px, well below the 44 px WCAG 2.5.5 minimum; progress dots (8×8 px) are purely decorative but would be unusable as tap targets if made interactive.
4. **`prefers-reduced-motion` is snapshotted at page load** — the `_canAnim` flag is evaluated once; toggling the OS-level setting mid-session has no effect on the JS animation engine (CSS transitions are correctly handled dynamically via the media query).
5. **No `<noscript>` fallback** — the print-frames div is `display:none` and inaccessible without JS; a non-JS visitor sees an empty stage.

Additional findings are ranked in **Top 5 Fixes** below.

---

## Keyboard / Focus Matrix

| Action | Target | Result | Status |
|--------|--------|--------|--------|
| Tab into widget | Container div (tabindex=0) | Receives focus; focus ring appears (2 px solid `--scriba-link`) | OK |
| Tab again | Next button (Prev disabled on frame 1) | Receives browser-default focus ring | OK |
| Tab again | Exits widget | Next page element | OK |
| ArrowRight on container | Widget div | Advances to next frame | OK |
| ArrowLeft on container | Widget div | Goes to previous frame | OK |
| Space on container | Widget div | Advances frame, `e.preventDefault()` suppresses page scroll | OK |
| Space on focused Next button | Next button | `keydown` bubbles to W, `e.preventDefault()` fires, single advance | OK |
| Enter on focused Next button | Next button | `click` event fires, single advance | OK |
| ArrowRight on focused sub-step button | Sub button inside W | Bubbles to parent W; **main widget advances** | **BUG** |
| Escape | Widget / buttons | No handler; browser default (no visible action) | MISSING |
| Home / End | Widget | No handler | MISSING |
| ArrowUp / ArrowDown | Widget | No handler (no vertical nav defined) | OK (N/A) |
| Tab within substory controls | Sub Prev → Sub Next | Standard button tab order | OK |
| Tab from last button to outside | Container exit | Focus leaves widget correctly | OK |
| Focus while animation plays | Widget | `_cancelAnims()` is NOT called on focus — in-flight animation continues | MINOR |
| Click Prev/Next | Button | Focus stays on the clicked button, not the widget container | OK (acceptable) |
| Click Prev/Next → Tab | Button | Focus moves to next button in DOM order | OK |

### Focus-visible gap on buttons

Buttons inside `.scriba-controls` have no explicit `:focus-visible` rule in scriba CSS. The browser default focus ring applies (adequate, but uncontrolled). The widget container itself has a well-defined 2 px solid blue ring via `.scriba-widget:focus-visible`.

---

## ARIA + Screen Reader Gaps

### 1. Widget container has no `role` or `aria-label`

```html
<!-- Current -->
<div class="scriba-widget" id="bfs-queue" tabindex="0" data-scriba-speed="1">

<!-- Recommended -->
<div class="scriba-widget" id="bfs-queue" tabindex="0" data-scriba-speed="1"
     role="region" aria-label="Algorithm animation: BFS Queue">
```

When a screen reader user Tabs to the widget, they hear nothing (or just the element type, "group"). There is no `aria-label` derived from the `label=` parameter that `emit_interactive_html` accepts — the parameter is threaded through but never written into the HTML `aria-label` attribute.

**File**: `scriba/animation/emitter.py`, line 1053 (widget_html f-string).

### 2. Narration and step-counter both use `aria-live="polite"`

```html
<span class="scriba-step-counter" aria-live="polite" aria-atomic="true">Step 1 / 5</span>
<p class="scriba-narration" id="..." aria-live="polite"></p>
```

On every frame change, both regions announce. The screen reader says "Step 2 / 5" followed by the narration text. The double announcement is functional but chatty. The step counter context (Step N / M) is useful and the narration is the real content; the current pairing works but may interrupt narration reading if the counter fires first.

### 3. SVG stage is correctly announced via `aria-labelledby`

Each SVG injected into the stage has:

```html
<svg role="img" aria-labelledby="bfs-queue-narration" ...>
```

This correctly links the visualisation to the narration `<p id="bfs-queue-narration">`. As JS updates `narr.innerHTML`, the screen reader re-reads the narration because it is the live region. The SVG itself is treated as a single opaque image — individual data targets (`data-target="q.cell[0]"`) carry no per-cell `aria-label`, which is acceptable for this pattern.

### 4. Progress dots have no ARIA

```html
<div class="scriba-dot active"></div>
```

Dots are `<div>` elements with no `role`, `aria-label`, or `aria-hidden`. They are presentational and convey the same information as the step counter (`aria-live`). They should be explicitly hidden from the accessibility tree:

```html
<div class="scriba-dot active" aria-hidden="true"></div>
```

**File**: `scriba/animation/emitter.py`, dots_html loop, line ~1048.

### 5. Annotations have `role="graphics-symbol"` and `aria-label`

Annotation groups emit:

```html
<g role="graphics-symbol" aria-label="Arrow from dp.cell[0][0] to dp.cell[1][1]: match C">
```

The SVG also includes a `<title>` element on the `<path>`. Since the SVG container is `role="img"`, screen readers do not descend into child elements by default. The annotations are thus not read aloud individually. This is acceptable — the narration text should describe any semantically important annotation. Annotation labels are a visual aid only.

### 6. Substory section has `role="group"` and `aria-label`

```html
<section class="scriba-substory" role="group"
         aria-label="Sub-computation: substory1">
```

The substory wrapping is reasonable. However, the substory's own step counter (`Sub-step 1 / N`) has no `aria-live` attribute, so navigating sub-steps does not announce to screen readers. Only the visual state updates.

**File**: `scriba/animation/emitter.py`, `emit_substory_html`, line ~840.

### 7. Filmstrip (static mode) frame list has no `aria-label`

```html
<figure class="scriba-animation" aria-label="" data-layout="filmstrip">
  <ol class="scriba-frames">
    <li class="scriba-frame" id="..." data-step="1">
```

The `<figure>` `aria-label` is empty when no frame has a label. The `<ol>` has no `aria-label`. Screen readers announce the list without context.

### 8. No `<noscript>` fallback

The interactive widget's print-frames div:

```html
<div class="scriba-print-frames" style="display:none">
  <!-- all frames with full SVG and narration -->
</div>
```

This is set to `display:none` unconditionally. Without JS, a visitor sees only the controls (two disabled buttons) and an empty stage. Adding a `<noscript>` tag or using `noscript` CSS to expose print-frames would make the content accessible in JS-disabled environments.

---

## Multi-Widget Collisions

Two or more `\begin{animation}` blocks in the same `.tex` file produce two widgets on the same HTML page. The following was verified:

| Concern | Status |
|---------|--------|
| Scene ID collision | **Safe** — `scene_id_from_source` uses SHA-256 of content + byte-offset position; two identical blocks at different positions produce distinct IDs |
| Frame ID collision | **Safe** — frame IDs are namespaced under scene_id |
| Narration ID collision | **Safe** — `{scene_id}-narration` is unique per widget |
| JS variable leaks | **Safe** — all widget JS runs inside an IIFE; `var W`, `var frames`, etc. are scoped per-widget |
| Substory counter | **Module-global Python** (`_substory_counter = 0`) — counter increments across all widgets in a single `render.py` call; IDs are unique within a single HTML page, but differ across separate renders of the same file |
| Keydown event bleed | **Safe** — `W.addEventListener('keydown', ...)` registers on each widget's own container div; only the focused widget fires |
| MutationObserver theme | **Harmless** — each widget registers its own MutationObserver on `document.documentElement`; all widgets redraw on theme change |
| `aria-live` bleed | **None** — live regions are inside each widget; focus determines which one announces |

**Summary**: Multi-widget pages have no functional collisions. The module-global substory counter is a minor implementation concern (non-deterministic IDs across renders) but does not affect correctness within a single HTML file.

---

## Mobile / Touch Issues

### Touch target sizes

Measured from CSS:

```css
.scriba-controls button {
  padding: 0.3rem 0.7rem;
  font-size: 0.8rem;
}
```

Estimated rendered height at 16 px base: `0.6rem (top+bottom padding) + ~1.2rem (line-height)` = **~28–30 px**. WCAG 2.5.5 requires 44×44 px minimum. Both the Prev and Next buttons fall short by ~14–16 px.

Progress dots are 8×8 px and presentational (no click handler), so not a touch-target issue.

### Swipe gestures

No touch events (`touchstart`, `touchend`, `touchmove`) or pointer events (`pointerdown`, `pointerup`) are registered anywhere in the widget JS. Swipe-to-navigate is not supported. Mobile users must tap Prev/Next buttons.

### Pinch zoom

The HTML template includes:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

No `user-scalable=no` or `maximum-scale=1` — pinch zoom is permitted. This is correct.

### SVG scaling

The SVG uses `viewBox` with `width="100%"` and `height="auto"` (`scriba-stage-svg`), so it scales correctly on small screens. No fixed pixel widths are set on the SVG stage.

### Controls bar overflow

On narrow screens (< 320 px), the controls bar (`display: flex; gap: 0.75rem`) may overflow if all five or more progress dots plus two buttons plus the step counter don't fit. No `flex-wrap` or `overflow-x: auto` is set on `.scriba-controls`. This is a minor mobile layout risk for animations with many frames.

---

## Embed Mode Quirks

There is **no dedicated iframe or embed output mode**. "Embed mode" in scriba terminology means using `scriba-embed.css` (widget chrome only, no page-wide resets) instead of `scriba-standalone.css` (which adds body/layout resets). The assumption is the widget HTML is dropped directly into a host page's markup.

### CSS isolation

`scriba-embed.css` deliberately excludes `*`, `body`, `h1`, and `.theme-toggle` selectors, making it safe to inject into an existing page shell without clobbering host layout. However, `scriba-scene-primitives.css` writes `:root {}` custom properties (design tokens) that could conflict with host `:root` token names.

### Inline `<script>` blocks

The widget emits one `<script>` block per animation instance. Under a strict Content-Security-Policy that prohibits `'unsafe-inline'`, these scripts will be blocked and the widget will render as a static empty stage. There is no nonce injection point and no external JS file option.

```python
# render.py line 194: loads scriba-embed.css, not an external JS file
# emitter.py: <script>\n(function(){{ ... }})();\n</script>
```

**CSP mitigation**: The host page would need `script-src 'unsafe-inline'` or per-script nonces that scriba cannot currently emit.

### `onclick` attribute on theme toggle

`render.py`'s HTML template uses an inline `onclick`:

```html
<button class="theme-toggle" onclick="
  var t = document.documentElement.dataset.theme;
  document.documentElement.dataset.theme = t === 'dark' ? 'light' : 'dark';
">Toggle theme</button>
```

This is a standalone HTML viewer concern; host applications providing their own theme toggle would not include this button. However it confirms `'unsafe-inline'` is required for the standalone output.

### iframe sizing

If a consumer iframes a rendered scriba HTML file, the iframe will not auto-resize to content height (there is no `postMessage` resize protocol and no `ResizeObserver` messaging). Consumers must set explicit iframe dimensions or use `scrolling="yes"`.

### Dark-mode theme attribute

The MutationObserver watches `document.documentElement[data-theme]`. In an iframe, `document.documentElement` is the iframe's `<html>`, not the host's. Theme changes in the host page do not propagate unless the host explicitly also sets `data-theme` on the iframe's `documentElement` or sends a `postMessage`.

---

## Top 5 Fixes Ranked

| # | Issue | Severity | Effort | File : Line |
|---|-------|----------|--------|-------------|
| 1 | **Widget container missing `role` and `aria-label`** — screen readers offer no context on focus. Add `role="region"` and `aria-label` derived from the `label=` parameter that is already threaded through `emit_interactive_html` but never written to the DOM. | HIGH | Low (2-line change) | `scriba/animation/emitter.py` : 1053 (widget_html f-string) |
| 2 | **Substory arrow-key event bubbling** — ArrowRight/Left on a focused sub-step button bubbles to the parent widget's keydown handler and advances the main frame. Fix: add `if(e.target.closest('.scriba-substory-widget'))return;` at the top of the keydown handler. | HIGH | Low (1-line change) | `scriba/animation/emitter.py` : 1342 (keydown handler) |
| 3 | **Touch targets below 44 px** — Prev/Next buttons are ~28–30 px tall. Increase to `min-height: 44px` or `padding: 0.7rem 0.7rem`. Progress dots are decorational (acceptable). | MEDIUM | Low (CSS change) | `scriba/animation/static/scriba-embed.css` : 51–64 (`.scriba-controls button`) |
| 4 | **`prefers-reduced-motion` not tracked dynamically** — `_canAnim` is evaluated once at page load. If the user enables reduced-motion after load, JS animations continue firing until page refresh. Fix: replace `var _canAnim = ...matchMedia.matches` with a `MediaQueryList.addEventListener('change', ...)` that updates `_canAnim`. CSS transitions are already handled correctly by the `@media` rule. | MEDIUM | Low (3–5 lines) | `scriba/animation/emitter.py` : 1086 (`_canAnim` declaration) |
| 5 | **Progress dots not `aria-hidden`** — The dots are presentational and duplicate the step counter's `aria-live` region. Adding `aria-hidden="true"` prevents screen readers from announcing them as "group, 5 items" when the widget is explored. | LOW | Low (1-attr change per dot) | `scriba/animation/emitter.py` : ~1048–1050 (dots_html loop) |

### Honourable mentions (out of top 5 ranking)

- **No `<noscript>` fallback**: The print-frames div exists but is unconditionally `display:none`. A `<noscript>` tag exposing it would help JS-disabled users and server-side rendering pipelines. (`emitter.py`, widget_html template)
- **Substory sub-step counter not `aria-live`**: Navigating sub-steps produces no screen reader announcement. (`emitter.py`, `emit_substory_html`, line ~838)
- **Inline `onclick` on theme toggle**: CSP `'unsafe-inline'` is required. Move to an event listener in a `<script>` block. (`render.py`, HTML_TEMPLATE)
- **No `main` landmark in standalone HTML template**: The render.py template lacks `<main>`. (`render.py`, HTML_TEMPLATE)
- **Controls bar no `flex-wrap`**: May overflow on very narrow screens with many progress dots. (`scriba-embed.css`, `.scriba-controls`)
- **`label=` parameter unused for widget `aria-label`**: `emit_interactive_html` accepts `label=` and `emit_html` passes it through, but the widget HTML template never writes it as `aria-label`. (`emitter.py`, widget_html f-string and `emit_html` call in `renderer.py`)
