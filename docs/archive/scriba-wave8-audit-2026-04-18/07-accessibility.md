# Wave 8 Audit — P7: Accessibility Deep Dive

**Date:** 2026-04-18
**Auditor:** Static code audit (Wave 8)
**Scope:** Screen-reader experience, keyboard navigation, forced-colors / Windows High Contrast Mode, live regions, KaTeX math accessibility, `\narrate` block timing and DOM placement.

---

## Methodology

Files read in full:

- `scriba/animation/emitter.py` — HTML/SVG emitter, all interactive widget markup
- `scriba/animation/static/scriba.js` — external runtime (step navigation, animation)
- `scriba/animation/static/scriba-embed.css` — widget chrome CSS
- `scriba/animation/static/scriba-scene-primitives.css` — state tokens, HCM, focus ring, reduced-motion
- `scriba/animation/static/scriba-animation.css` — reduced-motion keyframe overrides
- `scriba/tex/katex_worker.js` — KaTeX subprocess worker configuration
- `scriba/tex/vendor/katex/katex.min.js` — vendored KaTeX bundle (aria attribute count verified)
- `scriba/tex/parser/math.py` — math extraction and wrapping

Pattern searches applied across all `.py`, `.js`, and `.css` under `scriba/`:
- `aria-live`, `aria-label`, `aria-hidden`, `aria-labelledby`, `role=`, `tabindex`, `:focus`, `focus-visible`
- `forced-colors`, `prefers-contrast`
- `narrat`, `narration`

No actual HTML render was executed (render requires a live Python+Node environment). All findings are based on static code analysis of the emitter templates and runtime.

---

## Findings Summary

| ID | Severity | Class | File:line | Effort |
|----|----------|-------|-----------|--------|
| A01 | 🔴 | Missing accessible name — filmstrip `<figure>` | `emitter.py:672` | Low |
| A02 | 🟠 | Dual `aria-live` creates double-announcement | `emitter.py:1107,1114` | Low |
| A03 | 🟠 | Silent step-change in animated path (narration update is early, no region flush) | `scriba.js:240` | Medium |
| A04 | 🟠 | Substory narration `<p>` missing `aria-live` | `emitter.py:853` | Low |
| A05 | 🟡 | No `:focus-visible` rule on `<button>` elements | `scriba-embed.css` (absent) | Low |
| A06 | 🟡 | Keyboard navigation requires focus on outer widget `div`, not buttons | `scriba.js:288` | Medium |
| A07 | 🟡 | Forced-colors coverage is incomplete — only text halo is addressed | `scriba-scene-primitives.css:574` | Medium |
| A08 | 🟡 | State conveyed purely by CSS fill/stroke — no non-color signal in SVG | `scriba-scene-primitives.css` (design) | High |
| A09 | 🔵 | KaTeX configured `output:"html"` — MathML branch not emitted | `katex_worker.js:43` | Medium |
| A10 | 🔵 | Progress dots carry no accessible label or count | `emitter.py:1091` | Low |

---

## Per-Finding Detail

---

### A01 — 🔴 Empty `aria-label` on filmstrip `<figure>`

**File:** `scriba/animation/emitter.py:670–676`

```python
return (
    f'<figure class="scriba-animation" '
    f'data-scriba-scene="{_escape(scene_id)}" '
    f'data-frame-count="0" '
    f'data-layout="filmstrip" '
    f'aria-label="">\n'          # <-- empty string when no frames
    f'  <ol class="scriba-frames">\n'
```

For the non-empty filmstrip path (line 771–775), the label is taken from the first frame with a label; if no frame carries a label, `aria_label` is `""` and the attribute is emitted as `aria-label=""`. A `<figure>` with an empty `aria-label` is announced by most screen readers as "figure" with no context, which tells a user nothing. NVDA/JAWS will not read the frame list heading because `<ol>` inside a `<figure>` gets no landmark role.

**Fix:** If `label` is empty, omit `aria-label` entirely and add an explicit `<figcaption>` with a descriptive default (e.g. "Algorithm animation, N steps"). Alternatively, fall back to `aria-label="Animation"` consistently (the interactive widget already does this at line 1095: `_aria_label = _escape(label) if label else "Animation"`). Align the filmstrip branch.

---

### A02 — 🟠 Dual `aria-live` regions cause double-announcement on step advance

**File:** `scriba/animation/emitter.py:1107,1114`

```html
<span class="scriba-step-counter"
      aria-live="polite"
      aria-atomic="true">Step 1 / N</span>

<p class="scriba-narration"
   dir="auto"
   id="{scene_id}-narration"
   aria-live="polite"></p>
```

Both the step counter and the narration panel are marked `aria-live="polite"`. When a step advances, `_updateControls` sets `ctr.textContent` and `snapToFrame`/`animateTransition` sets `narr.innerHTML`. Both mutations fire within the same JS tick (or within the animation phase-2 callback). Screen readers queue two separate polite announcements: first "Step N / M", then the full narration text. The narration announcement is what users actually need; the step counter is redundant noise layered on top.

**Fix:** Remove `aria-live` from `.scriba-step-counter`. The narration panel already carries the substantive content and is `aria-live="polite"`. The step counter is visual chrome; its content is implied by the narration context. If a separate status announcement is desired, use a single, hidden `role="status"` element updated atomically with `"Step N of M: {narration}"`.

---

### A03 — 🟠 Animated path updates narration before SVG settles

**File:** `scriba/animation/static/scriba.js:235–241`

```js
function animateTransition(toIdx){
  if(_animState==='animating'){_cancelAnims();snapToFrame(toIdx);return;}
  var tr=frames[toIdx]&&frames[toIdx].tr;
  if(!tr||!tr.length||!_canAnim){snapToFrame(toIdx);return;}
  _animState='animating';
  narr.innerHTML=frames[toIdx].narration;   // <-- updated immediately
  _updateControls(toIdx);
  // SVG animation then runs for up to ~220ms via WAAPI
```

When `_canAnim` is true (animations enabled, no `prefers-reduced-motion`), `narr.innerHTML` is set at the *start* of the WAAPI transition. The screen reader fires the `aria-live="polite"` announcement almost immediately, while the SVG is still mid-animation. A user following the narration with a screen reader hears "step N text" while the visual for step N-1 is still on screen fading out. This breaks the audio-visual sync that narration is supposed to provide.

**Fix:** Move `narr.innerHTML = frames[toIdx].narration` into `_finish()` (called after `Promise.all(pending)`), or use a short `setTimeout` matching `DUR` + phase delay. Narration should land *after* the SVG settles, not before it starts.

---

### A04 — 🟠 Substory narration `<p>` missing `aria-live`

**File:** `scriba/animation/emitter.py:853`

```python
f'          <p class="scriba-narration"></p>\n'
```

The substory widget's narration `<p>` has no `aria-live` attribute. When `sh(i)` fires in `scriba.js:46`:

```js
function sh(i){
  sc=i;
  ss.innerHTML=fd[i].svg;
  sn.innerHTML=fd[i].narration;   // sn = substory .scriba-narration
  ...
}
```

The inner narration update is completely silent to screen readers. A user navigating a substory receives no spoken feedback that the sub-step changed.

**Fix:** Add `aria-live="polite"` to the substory narration `<p>` in `emit_substory_html`. Because substories are nested inside the main widget (which itself has a live narration region), use `aria-live="polite"` with `aria-atomic="true"` so only the substory text is announced, not re-reading the parent region.

---

### A05 — 🟡 Buttons lack `:focus-visible` styling

**File:** `scriba/animation/static/scriba-embed.css` (absent)

The widget CSS defines `:focus` only on the outer `.scriba-widget` container:

```css
/* scriba-scene-primitives.css:738 */
.scriba-widget:focus,
.scriba-widget:focus-visible {
  outline: var(--scriba-widget-focus-ring);
  outline-offset: 2px;
}
```

The individual `<button>` elements (`.scriba-btn-prev`, `.scriba-btn-next`) have no `:focus` or `:focus-visible` rule. Browsers apply the default outline, which differs by browser and is suppressed entirely by `scriba-embed.css`'s scoped reset (`box-sizing: border-box` with no focus override). In many configurations, Tab-navigating into the Prev/Next buttons produces no visible focus ring.

**Fix:** Add to `scriba-embed.css`:

```css
.scriba-controls button:focus-visible {
  outline: var(--scriba-widget-focus-ring);
  outline-offset: 2px;
}
```

---

### A06 — 🟡 Arrow-key navigation requires focus on the widget container `div`, not on its child buttons

**File:** `scriba/animation/static/scriba.js:288–292`

```js
W.addEventListener('keydown',function(e){
  if(e.target.closest('.scriba-substory-widget'))return;
  if(e.key==='ArrowRight'||e.key===' '){
    e.preventDefault();
    if(cur<frames.length-1)show(cur+1,true);
  }
  if(e.key==='ArrowLeft'){e.preventDefault();if(cur>0)show(cur-1,false);}
});
```

The `keydown` handler is on `W` (the `.scriba-widget` `div`, which has `tabindex="0"`). When a keyboard user Tabs inside the widget and lands on the **Prev** or **Next** `<button>`, focus moves to the button. A `keydown` on the button bubbles to `W`, so Arrow keys still work. However:

1. Pressing Space on the **Next** button fires *both* the button's click handler (via default) and the Space→next-step handler. Step advance happens twice if the button click also calls `show`. In practice `next.addEventListener('click',...` runs first, then the keydown fires `e.preventDefault()` — but `e.preventDefault()` on `keydown` does not suppress an already-dispatched `click`. This is a race condition that warrants verification.
2. While focus is on the **Prev** button, pressing `ArrowLeft` calls `show(cur-1, false)` but does not move button focus — the Prev button remains focused even after it becomes disabled. A screen reader will not re-announce its disabled state until the user re-queries it.

**Fix:** Explicitly call `prev.focus()` / `next.focus()` after `show()` when the trigger was a keyboard event, or move keyboard handling onto the button elements themselves using `role="application"` on the widget container with documented key bindings in an `aria-keyshortcuts` attribute.

---

### A07 — 🟡 Forced-colors / Windows High Contrast Mode: only text halo is addressed

**File:** `scriba/animation/static/scriba-scene-primitives.css:574–580`

```css
@media (forced-colors: active) {
  [data-primitive] text {
    paint-order:  normal;
    stroke:       none;
    stroke-width: 0;
  }
}
```

This is the *only* `forced-colors` block in the entire CSS surface (confirmed: no `forced-colors` rules in `scriba-embed.css`, `scriba-animation.css`, `scriba-plane2d.css`, `scriba-metricplot.css`). Under Windows High Contrast Mode:

- **Widget chrome** (buttons, step counter, progress dots, narration panel) relies on hardcoded `#ffffff` / `#11181c` color pairs in `scriba-embed.css`. In HCM, the OS substitutes `ButtonText`, `ButtonFace`, `Canvas`, and `CanvasText` system colors; the hardcoded hex values are overridden. The widget should still be functional because HCM's system-color substitution is automatic for standard HTML elements — but no author-side verification of button, dot, or narration panel appearance under HCM exists.
- **SVG state classes** (`.scriba-state-current`, `.scriba-state-error`, etc.) use `--scriba-state-*` custom properties for fill and stroke. Under HCM, `forced-colors: active` forces custom-property fills on SVG shapes to `currentColor` or system colors. The visual distinction between `idle`, `current`, `error`, and `good` states collapses — all cells will look similar. The `stroke-width` signal (1px vs. 2px for signal states) survives HCM, but this alone is a thin semantic signal.
- **Annotation arrows** carry color-coded meaning (`scriba-annotation-info`, `scriba-annotation-warn`, `scriba-annotation-error`). In HCM all strokes become `currentColor`; the semantic color difference is lost entirely with no alternative indicator.
- **Progress dots** (`.scriba-dot`, `.scriba-dot.active`, `.scriba-dot.done`) convey progress through background color only — no shape, border, or text fallback. Under HCM they will all render as the same system-color square.

**Fix required (high effort):** Add a comprehensive `@media (forced-colors: active)` block in `scriba-embed.css` and `scriba-scene-primitives.css` covering:
- Button `border-color` using `ButtonBorder` or `ButtonText` to preserve the interactive affordance
- Dot states using `border` or `outline` to distinguish active/done without relying on background fill
- SVG `[data-primitive] [data-target]` forced-color-aware stroke width rules
- Annotation shapes: use `stroke-dasharray` or shape difference to distinguish warn vs. error

---

### A08 — 🟡 State conveyed by color alone — no non-color signal in SVG data model

**File:** `scriba/animation/static/scriba-scene-primitives.css` (design-level)

The "Tonal Architecture" palette distinguishes seven states (idle, current, done, dim, error, good, highlight, path) primarily via fill color and secondarily via stroke color. The `stroke-width` signal-state distinction (1px vs. 2px for current/error/good) helps, but:

- SVG `<text>` elements contain the cell value only; no `aria-label` or `<title>` on cell `<g>` groups conveys the state to a screen reader.
- The `<svg>` itself carries `role="img" aria-labelledby="{narration_id}"` — the entire diagram is one image with one accessible name. Individual cell states are invisible to AT.
- A screen reader user navigating the narration text gets the step description but cannot independently query "what state is cell A[3] in?" because there are no accessible sub-elements.

This is a known limitation of the SVG-as-image pattern. For the current architecture the narration text is the primary AT channel; the SVG is intentionally opaque. The risk is that if a narration is sparse (or missing), AT users get no information about state changes.

**Recommended improvement (not a blocker):** Ensure every `\step` includes a `\narrate` block that explicitly names state changes. Add a lint warning (or documentation note) that sparse narration degrades the AT experience to zero. Long-term: consider `role="list"` + `role="listitem"` with `aria-label` on key primitive groups.

---

### A09 — 🔵 KaTeX rendered in HTML-only mode — no MathML output

**File:** `scriba/tex/katex_worker.js:43`

```js
const KATEX_OPTIONS_BASE = {
  throwOnError: false,
  output: "html",   // <-- HTML only, no MathML
  ...
};
```

KaTeX supports `output: "htmlAndMathml"` which emits both the visual `<span class="katex-html" aria-hidden="true">` layer AND a `<span class="katex-mathml">` layer containing MathML that screen readers (especially NVDA+Firefox and VoiceOver+Safari) can parse. With `output: "html"`, the single `<span class="katex-html">` gets `aria-hidden="true"` (confirmed in the vendored bundle at the `katex-html` class assignment). This means all rendered math is aria-hidden — screen readers read nothing for any formula in narration text.

```
// From katex.min.js (verified):
const l=Je(["katex-html"],s);
l.setAttribute("aria-hidden","true");
```

With `output: "html"` and no MathML companion, every `$...$` expression in narration is announced as silence. A formula like `$O(n \log n)$` becomes completely inaccessible.

**Fix:** Change `output: "html"` to `output: "htmlAndMathml"` in `katex_worker.js`. KaTeX will emit a hidden MathML subtree (`<span class="katex-mathml" aria-hidden="false"><math>...</math></span>`) that NVDA, JAWS, and VoiceOver can read. The visual output is unchanged; only the accessible tree gains math semantics. Note: this increases HTML payload slightly (~15-25% for math-heavy narrations).

---

### A10 — 🔵 Progress dots carry no accessible count or label

**File:** `scriba/animation/emitter.py:1090–1093`

```python
dots_html = "\n      ".join(
    f'<div class="scriba-dot{" active" if i == 0 else ""}"></div>'
    for i in range(frame_count)
)
```

The dot container is `aria-hidden="true"` (line 1109), which is correct — the step counter and narration are the accessible equivalents. However, if a sighted user moves focus to the widget and the dots are the only visible progress indicator, a low-vision user with browser zoom may find the 8px dots hard to see and may not connect them to the step counter text. No `aria-label` or `title` is present on the dots even before they are hidden. This is acceptable given `aria-hidden`, but worth documenting.

No fix required; already correctly hidden. Recommendation: verify that the dots container does not receive focus during Tab traversal (it should not, since it contains only `<div>` elements with no `tabindex`).

---

## Forced-Colors / High Contrast Subsection

One `@media (forced-colors: active)` block exists, scoped exclusively to removing the text halo on `[data-primitive] text` elements. No other forced-colors rules exist anywhere in the CSS surface.

**What this means in Windows High Contrast Mode:**

| Element | Normal mode | HCM |
|---------|-------------|-----|
| Widget background | `#ffffff` | OS Canvas (OK) |
| Prev/Next buttons | styled with hex | OS ButtonFace/ButtonText (OK via browser default) |
| `.scriba-dot.active` | `background: #0070d5` | Forced to system color — indistinguishable from `.scriba-dot` |
| `.scriba-dot.done` | `background: #c1c8cd` | Forced to system color — indistinguishable |
| SVG cells (`.scriba-state-current`) | `fill: #0070d5` | Forced to `Highlight` or `ButtonText` — may still differ from idle |
| SVG cells (`.scriba-state-error`) | `stroke: #e5484d` (2px) | Stroke forced to `Highlight`; 2px width still distinguishes |
| Annotation color classes | stroke color | Forced to `currentColor` — all same |
| Step counter text | `#687076` | Forced to `CanvasText` (OK) |

The most impactful gap: **progress dots lose all state meaning** under HCM. Since the step counter already provides "Step N / M" in text, this is partially mitigated for AT users, but sighted HCM users have no visual dot indicator. A `border` or `outline` on `.scriba-dot.active` using `Highlight` system color would fix this.

---

## Live Regions / Step Announcements Subsection

**Interactive widget (emit_interactive_html):**

Two `aria-live` regions exist:

1. `<span class="scriba-step-counter" aria-live="polite" aria-atomic="true">` — updated by `ctr.textContent = 'Step N / M'` in `_updateControls()`.
2. `<p class="scriba-narration" aria-live="polite">` — updated by `narr.innerHTML = frames[i].narration` in `snapToFrame()` / `animateTransition()`.

**Snap path** (`snapToFrame`): both updates fire synchronously in the same function call. The browser queues two separate live-region announcements in insertion order. Most screen readers will announce the step counter first ("Step 2 / 5") then the narration. This is double-announcement — finding A02.

**Animated path** (`animateTransition`): narration is updated at the *start* of the WAAPI transition (line 240), counter is also updated immediately. The SVG then animates for ~200ms. The live region fires before the visual has completed — finding A03.

**Filmstrip (emit_animation_html):** The static filmstrip uses `:target` CSS pseudo-class (`scriba-frame:target`) and scroll-snap. There are no `aria-live` regions in the filmstrip output — correct, since it is a scrollable list of `<li>` elements, each containing a complete frame. Screen readers navigate via their virtual cursor through `<li>` / `<p>` elements normally.

**Substory:** No `aria-live` on substory narration — finding A04.

---

## Keyboard Navigation Subsection

**Tab order (interactive widget):**

```
[outer .scriba-widget div, tabindex=0]
  → [Prev button]
  → [Next button]
  → (dots are divs, no tabindex — skipped)
  → (stage div, no tabindex — skipped)
  → (narration p, no tabindex — skipped)
```

Tab order is logical: Prev before Next, no focus trap. The widget has `tabindex="0"` so it is reachable as a single Tab stop before entering its children. This is intentional — Arrow/Space keys work on the container before the user Tabs into buttons.

**Focus visibility:**

- `.scriba-widget:focus-visible` has an outline (2px solid `--scriba-link`). Good.
- `.scriba-controls button` has no `:focus-visible` rule. Browser default outline applies — inconsistent across browsers, suppressed in some reset contexts. Finding A05.

**Arrow key / Space interaction:**

- `ArrowRight` / Space → advance step
- `ArrowLeft` → retreat step

These bindings are on `W` (the container). When a child button has focus, keydown still bubbles to `W`. No focus trap is present. The substory guard (`e.target.closest('.scriba-substory-widget')`) correctly stops arrow keys from controlling the parent when focus is inside a substory — good.

**Missing bindings:** No `Home`/`End` to jump to first/last step. No `Escape` to return focus to the container. These are not blockers but improve usability.

---

## Math Accessibility Subsection

KaTeX is configured with `output: "html"` (finding A09). This causes all rendered math to be:

```html
<span class="katex">
  <span class="katex-html" aria-hidden="true">
    <!-- visual glyph tree — hidden from AT -->
  </span>
</span>
```

No MathML companion is emitted. Consequently, every `$...$` or `$$...$$` expression in narration text is **announced as silence** by screen readers. A narration like `\narrate{Complexity is $O(n \log n)$}` renders as:

```
Complexity is [silence]
```

Scriba does **not** strip or override the `aria-hidden="true"` that KaTeX sets on `katex-html` — it is set inside the vendored KaTeX bundle automatically. The emitter's `narration_html` field accepts KaTeX output verbatim and places it inside `<p class="scriba-narration" aria-live="polite">`. The live region announces the narration `<p>` content — which includes the aria-hidden math spans, which AT skips.

Switching to `output: "htmlAndMathml"` in `katex_worker.js` (one-line change) resolves this for NVDA+Firefox and VoiceOver+Safari. JAWS with Chrome does not yet support MathML natively; JAWS users would benefit from a `aria-label` fallback on the math container, which `htmlAndMathml` mode does not add automatically.

---

## `\narrate` Blocks Subsection

**Parsing:** `\narrate{...}` is parsed by `grammar.py` into `NarrateCommand` (line 677). It is stored per-step as `narrate_body` and passed to `_render_narration()` in `renderer.py:113`. The rendered HTML is stored in `FrameData.narration_html`.

**DOM placement (interactive widget):**

```html
<p class="scriba-narration" dir="auto"
   id="{scene_id}-narration"
   aria-live="polite">
  <!-- narration_html injected here by JS at step-advance time -->
</p>
```

The narration `<p>` is **below** the `<div class="scriba-stage">` in the DOM. This is correct — screen readers in virtual/browse mode encounter the stage SVG first (announced as "image, [narration text via aria-labelledby]") and then the narration `<p>`. However:

- The SVG's `aria-labelledby` points to this same narration `<p>` (`id="{scene_id}-narration"`). So the SVG is labelled by the narration text, and the narration `<p>` also announces it separately. This produces **three** announcements on step advance: step counter, narration region, and potentially the SVG's accessible name if re-queried.
- In browse mode (not application mode), a screen reader reading linearly will read the SVG image first (using the narration as its accessible name) and then read the narration paragraph again as a separate element.

**DOM placement (filmstrip):**

```html
<li class="scriba-frame" id="{frame_id}">
  <header class="scriba-frame-header">
    <span class="scriba-step-label">Step N / M</span>
  </header>
  <div class="scriba-stage">
    <svg role="img" aria-labelledby="{frame_id}-narration">...</svg>
  </div>
  <p class="scriba-narration" id="{frame_id}-narration">{narration_html}</p>
</li>
```

In the filmstrip, each frame's narration `<p>` appears after the SVG. The `aria-labelledby` on the SVG correctly points to the per-frame narration `<p>`. A screen reader reading the `<li>` linearly will encounter: step label → SVG (announced with narration text) → narration paragraph (read again). Double-reading is inherent to the `aria-labelledby` pattern here; this is an acceptable trade-off for visual accessibility vs. screen-reader efficiency.

**Timing:** Narration text is pre-rendered at build time (Python pipeline). It does not depend on JS timing. The JS merely injects the pre-rendered HTML into the live region `<p>` at step advance. Timing issue A03 applies to *when* in the animation sequence the injection happens, not to the content itself.

---

## Recommended Screen-Reader Test Plan

This is an implementer guide. Run after fixing A02, A03, and A09.

### Setup

| SR | Browser | Expected math support |
|----|---------|-----------------------|
| NVDA 2024.x | Firefox 128 ESR | MathML via MathPlayer-free path |
| NVDA 2024.x | Chrome 120+ | No native MathML (KaTeX MathML read partially) |
| VoiceOver macOS 15 | Safari 18 | MathML supported |
| JAWS 2024 | Chrome | No native MathML |

### Test Cases

**T1 — Widget discovery:**
Tab to the `.scriba-widget` container. Expected: SR announces "Animation, region" (or the label passed via `label=`). If label is empty, verify "Animation" is announced, not silence.

**T2 — Step counter:**
Press Arrow-Right. Expected: SR announces narration text only (after A02 fix). Verify step counter is NOT announced separately.

**T3 — Math in narration:**
Use an example with `\narrate{Complexity is $O(n \log n)$}`. After A09 fix (MathML mode), expected: "Complexity is O n log n" or equivalent MathML reading. Currently (pre-fix): "Complexity is" with silence for the formula.

**T4 — Button focus labels:**
Tab inside the widget to the Prev/Next buttons. Expected: "Previous step, button, dimmed" (Prev) and "Next step, button" (Next). Verify disabled state is announced when on first/last step.

**T5 — Focus visibility:**
Tab to Prev/Next buttons. Verify visible focus outline appears (post A05 fix). Check in both light and forced-colors mode (Windows HCM Aquatic / High Contrast Black themes).

**T6 — Substory narration:**
Navigate to a widget with a substory. Advance substory steps. Expected (post A04 fix): substory narration is announced. Currently: silence.

**T7 — Forced-colors dot states:**
In Windows HCM, verify that the active step dot is visually distinguishable from other dots (post A07 partial fix). Tab to widget, advance steps while watching progress indicator.

**T8 — Narration timing (animated path):**
With animation enabled, advance a step. Expected (post A03 fix): narration announces *after* SVG animation completes (~220ms). Verify no premature announcement heard before visual finishes.

**T9 — SVG description:**
In browse/virtual mode (NVDA: not in application mode), navigate through the SVG element. Expected: "image, [narration text]". Verify the narration is not read a second time immediately after the SVG description (this double-read is inherent to aria-labelledby; document it as known behavior if unfixable).

**T10 — Filmstrip navigation:**
Use arrow keys to navigate through filmstrip `<li>` elements. Expected: SR reads each frame's step label and narration in order. Verify no orphaned or duplicate announcements.

---

## Confirmed OK

- **Real `<button>` elements:** Prev/Next controls are `<button>` elements (not `<div>`), have `aria-label="Previous step"` / `aria-label="Next step"`. Correct.
- **Progress dots are `aria-hidden`:** `.scriba-progress[aria-hidden="true"]` correctly hides the decorative dot row from AT. The step counter provides the accessible equivalent.
- **SVG `role="img"`:** Every emitted SVG carries `role="img"` and `aria-labelledby` pointing to the narration `<p>`. Correct.
- **Substory `role="group"`:** `emit_substory_html` emits `<section role="group" aria-label="Sub-computation: {title}">`. This is reasonable; `<section>` with `role="group"` explicitly reduces it from a landmark to a non-landmark grouping, which avoids polluting the landmark list with substory nesting.
- **`prefers-reduced-motion`:** Both `scriba-scene-primitives.css` and `scriba-animation.css` have comprehensive `prefers-reduced-motion: reduce` rules. The JS runtime checks `window.matchMedia('(prefers-reduced-motion:reduce)')` and disables WAAPI animations. Correct.
- **`dir="auto"`:** Narration `<p>` carries `dir="auto"`, supporting RTL narration text without author intervention. Correct.
- **KaTeX aria-hidden on visual span:** The vendored KaTeX bundle correctly sets `aria-hidden="true"` on the visual `.katex-html` layer. Scriba does not strip or override this. The problem is the absence of the MathML companion (A09), not incorrect stripping.
- **Widget `tabindex="0"`:** The outer widget `div` is keyboard-reachable as a single tab stop. Arrow-key bindings on the container allow stepping without entering the button tab order. This is a valid roving-tabindex-adjacent pattern.
- **Filmstrip `<ol>` / `<li>` structure:** Static filmstrip uses a proper ordered list, giving screen readers accurate item-count information ("item 3 of 5").
