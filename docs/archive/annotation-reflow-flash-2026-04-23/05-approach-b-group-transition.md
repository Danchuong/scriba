# Design Doc: Approach B — Animated Group Transform

## 1. Technical Feasibility

### CSS `transition: transform` on SVG `<g>`

CSS transitions on SVG `transform` attributes work, but with an important caveat about the property name. Browsers accept `transition: transform 250ms ease` on `<g>` elements when the transform is expressed as a **CSS property** (`style="transform: translate(Xpx, Ypx)"`), not as an XML presentation attribute (`transform="translate(X,Y)"`). The distinction matters: CSS `transition` only fires when the CSS `transform` property changes; it does not observe changes to the SVG presentation attribute.

Current Scriba output (`_frame_renderer.py:479`):
```python
svg_parts.append(f'<g transform="translate({x_offset},{y_cursor})">')
```
This writes a **presentation attribute**, not a CSS property. A CSS transition rule on `transform` will not fire when this attribute changes. The fix is to write `style="transform: translate({x_offset}px, {y_cursor}px)"` instead, which makes the value visible to the CSS transition engine.

Browser support for CSS `transform` transitions on SVG elements:
- Chrome 88+: full support
- Firefox 72+: full support (Firefox ≤71 required prefixed `transform-origin` for SVG but that is irrelevant here)
- Safari 14+: full support; Safari 13.1 has gaps with `transform-box` affecting origin calculation, but `translate(Xpx, Ypx)` without rotation is safe

The project's stated floor is Safari 14+ (established in `scriba-scene-primitives.css:24`), so CSS transform transitions on SVG `<g>` are within the compatibility envelope.

### SMIL `<animateTransform>`

SMIL declares the animation inline in SVG markup and fires deterministically from the moment the element is inserted. It requires no DOM identity preservation across frames and no JS. However it has been deprecated in Chrome (though never actually removed), never worked in IE, and creates coordination headaches: the animation fires on load, not on frame-swap. SMIL requires the correct `from`/`to` to be embedded at emit time, which would require diffing transform values in Python. It is complex without clear benefit over CSS. Not recommended.

### JS-driven tween

The runtime JS in `_script_builder.py` already uses `Element.animate()` (WAAPI) for `annotation_add`, `element_add`, `position_move`, and `element_remove` transitions. Extend the same machinery to animate `<g>` translate changes. This is already present in the codebase and does not require adding a new dependency.

**Chosen path:** CSS `transition` on the CSS `transform` property (requires swapping attribute syntax to `style=`), augmented with WAAPI for the JS-driven fallback path that the runtime already uses for annotation transitions.

---

## 2. Identity Contract

### How the frame switcher works

Reading `_html_stitcher.py:571-591` and `_script_builder.py:108-116`:

The interactive widget (`emit_interactive_html`) renders all frames at build time, stores each frame's SVG as a JS template-literal string in `frames[i].svg`, and on step, runs:

```js
function snapToFrame(i) {
    stage.innerHTML = frames[i].svg;  // line 111 — full innerHTML replacement
    ...
}
```

`animateTransition` (line 282–325) runs WAAPI on DOM elements in the *current* stage before calling `stage.innerHTML = frames[toIdx].svg` at the end. It does **not** preserve DOM elements across frames — it reads the target frame's SVG from a string, parses it with `DOMParser`, clones elements out of that parsed document, appends them to the live stage, animates them, and then does a final full `innerHTML` sync.

**This is a full-replacement model.** There are no persistent DOM elements with stable identity across frames. Every `<g transform="...">` element is destroyed and recreated on each step.

### What this means for CSS transitions

CSS transitions require the **same DOM node** to persist across the property change. Since `snapToFrame` replaces `stage.innerHTML` wholesale, there is no same-node persistence — transitions on `<g>` elements cannot fire through the CSS engine alone.

### Required refactor to enable group-level transitions

Two approaches:

**Option B1 — Patch the existing `<g>` nodes in place (minimal diff)**

Instead of replacing the entire `stage.innerHTML`, the JS runtime could:
1. Parse `frames[toIdx].svg` with `DOMParser`
2. For each primitive `<g data-shape="...">`, find the matching `<g>` in the live stage by `data-shape`
3. Update only the `transform` (or `style`) attribute
4. Let CSS transition fire naturally

The primitive `<g>` elements need a stable `data-shape` attribute (already being written — see `_frame_renderer.py:529` where `data-shape` is referenced from JS). Verifying this: the JS runtime at `_script_builder.py:177-181` uses `srcP.getAttribute('data-shape')` to find the parent shape container. So `data-shape` is already emitted on the outer `<g>`.

**Option B2 — WAAPI on the outer `<g>` (no DOM identity needed)**

In `animateTransition`, after parsing the next frame's SVG:
1. Extract each primitive's `<g>` translate from the parsed document
2. In the live stage, find the corresponding `<g data-shape>`
3. Use `.animate([{transform: from}, {transform: to}], {duration: 250, easing: 'ease-out', fill: 'forwards'})` on it
4. After the animation settles, do the normal `innerHTML` sync

This follows the same pattern already used for `position_move` (line 189–201 in `_script_builder.py`), which animates a `translate` from a previous position to `translate(0,0)`. Approach B2 extends that pattern to the outermost primitive group.

**Option B2 is lower risk and requires no change to the Python emit pipeline.** It fits the existing WAAPI pattern and does not require DOM identity preservation or a change to the innerHTML-swap model.

---

## 3. Determinism and Replay Contract

### Does Scriba have a byte-identity requirement?

Scanning `docs/spec/ruleset.md`: no rule labelled U-06 or determinism is present in the first 180 lines. The spec does establish that `scene_id` is a deterministic SHA-256 digest (`emitter.py:114-122`) and that primitive rendering is stateless per frame. But the spec contains no clause requiring byte-identical SVG output across Python versions or runs.

The relevant concern is **snapshot mode determinism**: the print frames (`scriba-print-frames`) are rendered at Python emit time and stored as static HTML strings. They are never touched by CSS transitions or WAAPI. A user printing or taking a screenshot of a specific step always sees the fully-resolved final state for that step with no transient animation state. Approach B2 is purely a JS runtime concern; the Python pipeline does not change at all.

CSS transitions in the live interactive stage do produce transient states, but these only affect the live DOM during the 250ms tween window. They never affect the static `scriba-print-frames` content.

**Conclusion:** Approach B2 does not affect the determinism contract of the Python pipeline. The static SVG strings stored in `frames[i].svg` remain unchanged.

---

## 4. Reduced-Motion Accessibility

The runtime already checks `prefers-reduced-motion` at line 71 in `_script_builder.py`:

```js
var _canAnim = (typeof Element.prototype.animate === 'function') && !_motionMQ.matches;
```

And listens for changes:
```js
var _mh = function(ev) { _canAnim = !ev.matches; };
```

All WAAPI animations are gated on `_canAnim`. The proposed group-translate WAAPI animation must follow the same gate — if `_canAnim` is false, snap directly without tweening.

`scriba-scene-primitives.css:774-802` already contains the CSS-level reduced-motion block:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration:  0.01ms !important;
  }
  ...
  [data-target] > rect, [data-target] > circle, [data-target] > line, [data-target] > text {
    transition-duration: 0ms !important;
  }
}
```

For the CSS approach (B1), this block already zeroes out transitions. For the WAAPI approach (B2), the `_canAnim` gate handles it. No additional CSS is needed.

---

## 5. Annotation Fade-in / Fade-out

### What marks an annotation as "new this frame"

The differ in `_html_stitcher.py:519-535` calls `compute_transitions(frames[i-1], frames[i])` and produces a manifest that already includes `annotation_add` and `annotation_remove` transition records. The runtime in `_script_builder.py:209-280` already handles:

- `annotation_add`: stroke-dasharray path draw-in animation, then arrowhead/label opacity fade
- `annotation_remove`: opacity fade-out

So annotation fade-in for newly appearing annotations is **already implemented**. The draw-in animation fires over `DUR_PATH_DRAW = 120ms`, with arrowhead appearing at 70% completion (`DUR_ARROWHEAD = 36ms`).

The specific bug is at step 1 → step 2: when `\annotate` fires, the annotation's *target primitive bbox* grows (the array acquires arrow headroom), which shifts downstream primitives. This is a **layout shift**, not an annotation visibility problem. Annotation fade-in already works; the issue is the group translate snap.

### Summary for this section

Annotation opacity fade-in and draw-in are already implemented. No new work needed. The flash is caused by the outer `<g transform>` snapping, which Approach B2 addresses at the group level.

### Optional: stroke-dasharray draw-in for arrows

Already implemented and active for `annotation_add`. The path element gets `strokeDashoffset` animated from `len` to `0` over `DUR_PATH_DRAW`. This is in-place — no new work.

---

## 6. Interaction with Approach A (Reserve Gutter)

**Without Approach A:** When `\annotate` fires at step 2, the array bbox grows by the arrow headroom (typically 30–60px). The downstream primitive's `<g>` translate changes by that delta. A 250ms WAAPI tween over a 50px jump is visible and smooth but feels like a slide animation rather than a correction. At faster speeds (`data-scriba-speed > 1`) the tween may feel laggy.

**With Approach A (max viewbox + `set_min_arrow_above`):** The `emit_interactive_html` function already calls `set_min_arrow_above` on each primitive before rendering, which reserves the maximum arrow headroom across all frames (lines 384–403 in `_html_stitcher.py`). For the **interactive widget**, if `set_min_arrow_above` is correctly propagated before the per-frame SVG is rendered, the `<g>` translate values for downstream primitives should be **identical** across frames — there is no layout shift to animate in the first place.

Checking the flow: `emit_interactive_html` calls `set_min_arrow_above` in a loop (lines 384–403), then immediately calls `_emit_frame_svg` for each frame. If `set_min_arrow_above` reserves the maximum headroom at the start, all frames see the same `y_cursor` values and no translate delta exists. This is functionally Approach A already being applied in the interactive path.

The bug likely persists because either (a) `set_min_arrow_above` is not being reflected in `bounding_box()` output during the frame render loop, or (b) the annotation headroom is computed per-frame inside `_emit_frame_svg` at line 466–472 (setting annotations before computing bbox), which can override the pinned headroom. This would cause frames with no annotations to use a smaller bbox than frames with annotations, re-introducing the delta.

**Hybrid recommendation:** Fix Approach A properly (ensure `set_min_arrow_above` pins the bbox for all frames, including frames with no annotations). Then add Approach B2 as a polish layer for any residual delta. With Approach A fixed, Approach B2 will only animate tiny corrections (0–5px) or nothing at all, which is invisible and harmless. Without Approach A, Approach B2 animates a 30–60px jump, which is functional but feels like a layout slide rather than a polish fix.

---

## 7. Implementation Sketch

### Pseudocode (JS runtime addition in `_script_builder.py`)

In `animateTransition`, before the existing phase-1/phase-2 dispatch, add a group-translate phase:

```js
// --- Phase 0: animate outer <g data-shape> translate deltas ---
var parsedDoc = new DOMParser().parseFromString(frames[toIdx].svg, 'image/svg+xml');

function _getGroupTranslate(root, shapeId) {
  var g = root.querySelector('[data-shape="' + _cssEscape(shapeId) + '"]');
  if (!g) return null;
  // Read from style.transform (CSS) or transform attribute (SVG presentation)
  var s = g.style && g.style.transform;
  if (s) {
    var m = s.match(/translate\(([^,]+)px,\s*([^)]+)px\)/);
    if (m) return {x: parseFloat(m[1]), y: parseFloat(m[2])};
  }
  var attr = g.getAttribute('transform');
  if (attr) {
    var m2 = attr.match(/translate\(([^,)]+)[, ]+([^)]+)\)/);
    if (m2) return {x: parseFloat(m2[1]), y: parseFloat(m2[2])};
  }
  return null;
}

stage.querySelectorAll('[data-shape]').forEach(function(liveG) {
  var shapeId = liveG.getAttribute('data-shape');
  var fromPos = _getGroupTranslate(stage, shapeId);   // current live position
  var toPos   = _getGroupTranslate(parsedDoc, shapeId); // target frame position
  if (!fromPos || !toPos) return;
  var dx = fromPos.x - toPos.x;
  var dy = fromPos.y - toPos.y;
  if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return; // no delta → skip
  if (!_canAnim) return;
  var a = liveG.animate(
    [{transform: 'translate(' + (toPos.x + dx) + 'px,' + (toPos.y + dy) + 'px)'},
     {transform: 'translate(' + toPos.x + 'px,' + toPos.y + 'px)'}],
    {duration: _dur(250), easing: 'ease-out', fill: 'forwards'}
  );
  _anims.push(a);
  pending.push(a.finished);
});
```

This runs before phase-1 transitions (annotation adds) so the group slides into position while annotations appear on top.

### Python emit change (prerequisite)

In `_frame_renderer.py:479`, change the attribute from XML presentation to CSS property so that CSS transitions can also observe it (needed for B1 compatibility, and good hygiene regardless):

```python
# Before:
svg_parts.append(f'<g transform="translate({x_offset},{y_cursor})">')

# After (add data-shape and CSS-property style):
svg_parts.append(
    f'<g data-shape="{shape_name}" '
    f'style="transform: translate({x_offset}px, {y_cursor}px)">'
)
```

Note: `data-shape` may already be emitted at a different level — confirm by checking `emit_svg` for each primitive. If the outer `<g>` from `_frame_renderer.py:479` does not carry `data-shape` today, this adds it, making the JS `querySelectorAll('[data-shape]')` work at the right level.

### CSS addition to `scriba-scene-primitives.css`

Only needed if pursuing pure CSS (B1). For B2 (WAAPI), no CSS changes are required. For documentation/fallback:

```css
/* Approach B: smooth group-level translate on frame swap (B1 / CSS path) */
.scriba-stage > g[data-shape] {
  transition: transform 250ms ease-out;
}

@media (prefers-reduced-motion: reduce) {
  .scriba-stage > g[data-shape] {
    transition: none !important;
  }
}
```

This is inert under B2 but provides a CSS-only fallback for environments where WAAPI is unavailable.

---

## 8. Browser Compatibility Matrix

| Browser | CSS `transform` transition on SVG `<g>` | WAAPI `Element.animate()` on SVG `<g>` | SMIL `<animateTransform>` | Notes |
|---|---|---|---|---|
| Chrome 90+ | Full support | Full support | Supported (not removed despite deprecation) | Recommended path |
| Firefox ESR 128+ | Full support | Full support | Full support | No caveats |
| Safari 14+ | Full support | Full support (Safari 13.1 had `fill:'forwards'` gap but 14 fixed it) | Partial (unreliable for declarative sequencing) | Project floor; safe |
| Safari 13.1 | Partial (`transform-box` issues with rotation; translate-only is fine) | Partial (`fill:'forwards'` unreliable) | Partial | Below project floor — out of scope |
| Firefox ESR 115 | Full support | Full support | Full support | Previous ESR; still in use; safe |

The project floor (`scriba-scene-primitives.css:24`) is Chrome 90 / Firefox ESR 128 / Safari 14. All three tiers fully support both CSS transform transitions and WAAPI on SVG elements. SMIL is excluded from the recommendation due to choreography complexity, not browser support gaps.

---

## 9. Risks

### Layout thrashing during transition

The `_getGroupTranslate` helper reads `style.transform` or the `transform` attribute from live DOM elements to determine the "from" position. Reading `style` does not force layout. However, calling `liveG.getBoundingClientRect()` inside a loop would. The proposed sketch uses attribute reads only and is safe.

If `animate()` with `fill:'forwards'` is called while a previous animation is still running (the `_animState === 'animating'` guard at line 283 calls `_cancelAnims()` which calls `finish()` on all pending animations), the element's committed style will be at its final value before the new animation starts. The `_getGroupTranslate` call for the "from" position must read from the **target-frame document** (the static string), not from the live element in its mid-animation state, to avoid reading a partially-transitioned value. The sketch above already does this correctly: `fromPos` comes from the current `stage` (live DOM, which after `_cancelAnims` is at a committed final state), and `toPos` comes from `parsedDoc` (the next frame).

### KaTeX `<foreignObject>` propagation

Some primitives may embed `<foreignObject>` for KaTeX math. CSS `transform` on an ancestor `<g>` propagates to `<foreignObject>` in all modern browsers. WAAPI `animate()` on the ancestor `<g>` also propagates. No issue expected. However, `<foreignObject>` content lives in a separate rendering context and may have its own stacking context; visually it will translate with the group as expected.

### Fast-stepping (frame-skip under rapid clicks)

The existing `animateTransition` guard at `_script_builder.py:283`:
```js
if (_animState === 'animating') { _cancelAnims(); snapToFrame(toIdx); return; }
```
If the user clicks Next rapidly (e.g., 5 times in succession), the second click fires `_cancelAnims()`, which calls `finish()` on all WAAPI animations including the group-translate ones, committing them to their final state instantly. The third click then sees a clean committed DOM and starts a new animation. This is correct behavior — mid-animation interrupts snap to the final state of the interrupted transition, then the new transition starts from that state. No frame-skip corruption occurs.

The `_anims` array receives the group-translate WAAPI `Animation` objects via `_anims.push(a)`, so they participate in the existing cancel/finish machinery automatically.

### The `data-shape` collision concern

The inner content of each primitive's `emit_svg()` may also emit `data-shape` on sub-elements (e.g., the JS at `_script_builder.py:177` looks for `data-shape` on parent nodes to find the shape container). If the outer `<g>` from `_frame_renderer.py:479` gains `data-shape`, the `querySelector('[data-shape]')` traversal in the JS annotation code must not accidentally match the outer `<g>` instead of an inner shape container. Audit the `_script_builder.py:173-182` walk: it starts from `src.parentNode` and walks upward, so it will find the first ancestor with `data-shape`. If both an outer `<g>` (at scene level) and an inner `<g>` (at primitive level) carry `data-shape`, the walk may stop at the inner one first, which is correct. However, this needs careful verification before the outer `<g>` is given a `data-shape` attribute — it may be safer to use a distinct attribute like `data-primitive-group` to avoid conflating the two levels.

---

## File locations referenced

- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/_frame_renderer.py` — line 479 (outer `<g>` emit), lines 442–449 (offset pre-computation loop)
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/_html_stitcher.py` — lines 384–403 (`set_min_arrow_above` loop), lines 429–438 (`_emit_frame_svg` call), lines 519–535 (transition manifest computation)
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/_script_builder.py` — lines 71–72 (`_canAnim` gate), lines 84–86 (`_cancelAnims`), lines 108–116 (`snapToFrame`), lines 189–201 (`position_move` WAAPI pattern), lines 282–325 (`animateTransition`)
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/static/scriba-scene-primitives.css` — lines 467–471 (`.scriba-annotation` opacity transition), lines 759–768 (`[data-target]` CSS transitions), lines 774–802 (reduced-motion block)
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/static/scriba-animation.css` — lines 57–70 (reduced-motion block for keyframe animations)
