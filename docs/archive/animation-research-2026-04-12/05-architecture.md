# 05 — Animation Retrofit Architecture

Technical architecture for adding smooth step-to-step animation to the
Scriba emitter without breaking the existing static rendering pipeline.

---

## 1. Current Architecture Summary

The rendering pipeline is strictly linear:

```
.tex source
  |
  v
SceneParser.parse()          -> AnimationIR (shapes, frames, commands)
  |
  v
SceneState (scene.py)        -> FrameSnapshot per step
  state machine replays         (shape_states dict, highlights,
  commands in order               annotations, bindings)
  |
  v
AnimationRenderer            -> list[FrameData]
  _snapshot_to_frame_data()     (step_number, shape_states,
                                 narration_html, annotations)
  |
  v
emit_interactive_html()      -> HTML string
  _emit_frame_svg() per frame    with inline <script>
  bundles SVGs into JS array
```

The JS widget does `stage.innerHTML = frames[i].svg` on every
Next/Prev click -- a full DOM replacement. There is no element
matching, no diffing, and no animation between frames.

### Key data structures

**FrameData** (frozen dataclass):
- `shape_states: dict[str, dict[str, dict]]` -- shape name -> target key -> `{state, value, label, apply_params, highlighted}`
- `annotations: list[dict]` -- `{target, label, ephemeral, arrow_from, color}`
- `narration_html: str`

**ShapeTargetState** (scene.py):
- `state: str` (idle | current | done | error | ...)
- `value: str | None`
- `label: str | None`
- `apply_params: list[dict] | None`

**SVG identity**: every primitive emits `data-target="shape.accessor"` on
its `<g>` groups (e.g. `data-target="arr.cell[0]"`,
`data-target="G.node[A]"`, `data-target="G.edge[(A,B)]"`).  This is
already present in all primitives: Array, Grid, DPTable, Graph, Tree,
NumberLine, HashMap, Matrix, Stack, Queue, Plane2D, MetricPlot.

---

## 2. Frame Diff Engine (Python-side)

### 2.1 Location

New module: `scriba/animation/differ.py`.  Pure function, no side effects.

### 2.2 Interface

```python
@dataclass(frozen=True)
class Transition:
    target: str          # e.g. "arr.cell[0]", "G.edge[(A,B)]"
    prop: str            # "state" | "value" | "label" | "add" | "remove" | "highlighted"
    from_val: str | None # previous value (None for additions)
    to_val: str | None   # new value (None for removals)
    kind: str            # "recolor" | "value_change" | "element_add" | "element_remove"
                         # | "highlight_on" | "highlight_off" | "annotation_add"
                         # | "annotation_remove" | "annotation_recolor"

@dataclass(frozen=True)
class TransitionManifest:
    transitions: tuple[Transition, ...]
    duration_ms: int = 300
    easing: str = "ease-out"

def compute_transitions(
    prev: FrameData,
    curr: FrameData,
) -> TransitionManifest:
    ...
```

### 2.3 Diff algorithm

Walk both frames' `shape_states` dictionaries in a single pass:

```
all_shapes = prev.shape_states.keys() | curr.shape_states.keys()
for shape in all_shapes:
    prev_targets = prev.shape_states.get(shape, {})
    curr_targets = curr.shape_states.get(shape, {})
    all_targets = prev_targets.keys() | curr_targets.keys()

    for target in all_targets:
        p = prev_targets.get(target)
        c = curr_targets.get(target)

        if p is None and c is not None:
            emit Transition(target, "add", None, c["state"], "element_add")
        elif p is not None and c is None:
            emit Transition(target, "remove", p["state"], None, "element_remove")
        else:
            if p["state"] != c["state"]:
                emit Transition(target, "state", p["state"], c["state"], "recolor")
            if p.get("value") != c.get("value"):
                emit Transition(target, "value", p.get("value"), c.get("value"), "value_change")
            if p.get("highlighted") != c.get("highlighted"):
                kind = "highlight_on" if c.get("highlighted") else "highlight_off"
                emit Transition(target, "highlighted", ..., ..., kind)
```

Annotations diff follows the same pattern: match by `(target, arrow_from)`
composite key, detect additions/removals/recolors.

Structural mutations (`add_edge`, `add_node`, `push`, `enqueue`) appear
as new targets in `curr` that were absent in `prev` -- the diff engine
classifies these as `element_add`.  Removals (`remove_edge`, `pop`) are
targets present in `prev` but absent in `curr` -- classified as
`element_remove`.

### 2.4 Position changes

Position changes (e.g. graph layout shifting a node) are NOT tracked by
the diff engine in v1.  The Python-side shape_states dict stores logical
state, not coordinates.  Coordinates are computed at SVG emit time by each
primitive's layout algorithm.  Tracking position would require calling the
primitive's layout for both frames and comparing coordinates -- deferred
to v2.

### 2.5 Output format

The manifest is serialized to a compact JSON array:

```json
[
  ["arr.cell[0]", "state", "idle", "current", "recolor"],
  ["dp.cell[1]", "value", "?", "4", "value_change"],
  ["G.edge[(A,B)]", "add", null, "idle", "element_add"],
  ["stk.item[2]", "remove", "idle", null, "element_remove"]
]
```

Array-of-arrays rather than array-of-objects saves ~40% JSON bytes for
typical 5-15 transition manifests.  The JS runtime destructures by
position: `[target, prop, fromVal, toVal, kind]`.

---

## 3. SVG Element Identity Tracking

### 3.1 Elements with data-target (the common case)

Every addressable primitive element already emits:

```html
<g data-target="arr.cell[0]" class="state-idle">
  <rect .../>
  <text ...>5</text>
</g>
```

The `data-target` attribute is the identity key.  It is stable across
frames for the same logical element.  The JS runtime finds elements via:

```js
stage.querySelector(`[data-target="${CSS.escape(target)}"]`)
```

`CSS.escape` is necessary because target strings contain `.`, `[`, `]`,
`(`, `)` which are CSS selector metacharacters.

### 3.2 Elements without data-target

These fall into two categories:

**Structural decoration** (grid lines, axis lines, arrowhead defs):
- These do not change between frames
- They are re-emitted identically in every frame's SVG
- No animation needed -- the full SVG swap after transition handles them

**Annotations** (`<g class="scriba-annotation">`):
- Currently rendered inline by primitives that support them
- Identity key: `annotation-{target}-{arrow_from or 'solo'}`
- The diff engine emits `annotation_add` / `annotation_remove` /
  `annotation_recolor` transitions
- The JS runtime matches by a `data-annotation` attribute (to be added
  to annotation `<g>` elements in a follow-up primitive change)

### 3.3 Elements added/removed between frames

When the diff engine reports `element_add`, the target element exists in
frame N+1's static SVG but not in frame N's DOM.  The runtime cannot
animate something that does not exist yet.

Strategy: **two-phase transition**.

1. **Swap** the full SVG into the DOM (just like today's `innerHTML`).
2. Immediately set all `element_add` targets to `opacity: 0`.
3. Animate `opacity: 0 -> 1` over the transition duration.
4. Simultaneously animate all `element_remove` targets (which no longer
   exist after the swap) -- this is not possible with the post-swap
   approach.

Revised strategy for clean add/remove:

1. Parse the target frame's SVG string into a DocumentFragment (via
   `new DOMParser().parseFromString()`).
2. For each `element_add`: find the element in the fragment, clone it
   into the current DOM at the same position, set `opacity: 0`,
   animate to `opacity: 1`.
3. For each `element_remove`: animate the existing DOM element to
   `opacity: 0`, then remove it.
4. For each `recolor` / `value_change` / `highlight`: animate in-place
   on the existing DOM.
5. After all animations complete: do the full `innerHTML` swap to
   ensure DOM correctness (the animated state may have drifted from
   the canonical SVG due to floating-point or layout differences).

This means the static SVG is always the source of truth.  Animation is
a visual flourish layered on top, not a replacement for the static
rendering pipeline.

---

## 4. JS Animation Runtime

### 4.1 State machine

```
                click Next
    IDLE ──────────────────> ANIMATING
     ^                          |
     |     all transitions      |
     |       complete           v
     +──────────────────── COMPLETE
     |                          |
     |     click Next           |
     +<─────────────────────────+
           (move to next
            frame, start
            new animation)

    click Prev / click dot:
        cancel any running animation
        instant snap to target frame (innerHTML swap)
```

### 4.2 Runtime pseudocode

```js
function animateTransition(fromIdx, toIdx) {
  if (state === 'animating') {
    cancelAnimations();
    snapToFrame(toIdx);
    return;
  }

  state = 'animating';
  var manifest = frames[toIdx].transitions;
  if (!manifest || !manifest.length || prefersReducedMotion()) {
    snapToFrame(toIdx);
    return;
  }

  var pending = [];
  var targetSvgDoc = parseSvg(frames[toIdx].svg);

  // Phase 1: handle removals (fade out elements leaving)
  for (var [target, prop, from, to, kind] of manifest) {
    if (kind === 'element_remove') {
      var el = stage.querySelector('[data-target="' + CSS.escape(target) + '"]');
      if (el) pending.push(el.animate(
        [{opacity: 1}, {opacity: 0}],
        {duration: DURATION, easing: EASING, fill: 'forwards'}
      ));
    }
  }

  // Phase 2: handle recolors / value changes (in-place on current DOM)
  for (var [target, prop, from, to, kind] of manifest) {
    if (kind === 'recolor') {
      var el = stage.querySelector('[data-target="' + CSS.escape(target) + '"]');
      if (el) {
        // Swap CSS class: state-{from} -> state-{to}
        el.classList.remove('state-' + from);
        el.classList.add('state-' + to);
        // The CSS transition on fill/stroke handles the color interpolation
      }
    }
    if (kind === 'value_change') {
      var el = stage.querySelector('[data-target="' + CSS.escape(target) + '"]');
      if (el) {
        var txt = el.querySelector('text');
        if (txt) txt.textContent = to;
      }
    }
  }

  // Phase 3: handle additions (clone from target SVG, fade in)
  for (var [target, prop, from, to, kind] of manifest) {
    if (kind === 'element_add') {
      var newEl = targetSvgDoc.querySelector('[data-target="' + CSS.escape(target) + '"]');
      if (newEl) {
        var clone = newEl.cloneNode(true);
        clone.style.opacity = '0';
        // Insert into appropriate parent group in current DOM
        var parent = findParentGroup(stage, target);
        if (parent) {
          parent.appendChild(clone);
          pending.push(clone.animate(
            [{opacity: 0}, {opacity: 1}],
            {duration: DURATION, easing: EASING, fill: 'forwards'}
          ));
        }
      }
    }
  }

  // Phase 4: after all animations finish, snap to canonical SVG
  Promise.all(pending.map(a => a.finished)).then(function() {
    snapToFrame(toIdx);
    state = 'idle';
  });
}

function snapToFrame(i) {
  cur = i;
  stage.innerHTML = frames[i].svg;
  narr.innerHTML = frames[i].narration;
  // ... update controls, dots, substories (same as today)
  state = 'idle';
}
```

### 4.3 How each animation type works

| Kind | Technique | Detail |
|------|-----------|--------|
| `recolor` | CSS class swap | Remove `state-{old}`, add `state-{new}`. CSS `transition: fill 300ms, stroke 300ms` on `[data-target] > rect` handles interpolation. |
| `value_change` | Direct `textContent` set | No animation on the text itself (cross-fade text is jarring). The cell's state often changes simultaneously, providing visual feedback. |
| `element_add` | Clone + opacity fade | Clone from parsed target SVG. `element.animate([{opacity:0},{opacity:1}], opts)`. |
| `element_remove` | Opacity fade | `element.animate([{opacity:1},{opacity:0}], opts)`. Removed from DOM on completion by the final snap. |
| `highlight_on` | Add CSS class | `el.classList.add('highlighted')`. CSS transition handles the glow/ring effect. |
| `highlight_off` | Remove CSS class | `el.classList.remove('highlighted')`. |
| `annotation_add` | Opacity fade | Same as element_add but targeting `[data-annotation="..."]`. |
| `annotation_remove` | Opacity fade | Same as element_remove. |

### 4.4 CSS transition declarations (addition to scriba-scene-primitives.css)

```css
[data-target] > rect,
[data-target] > circle {
  transition: fill 300ms ease-out, stroke 300ms ease-out;
}

[data-target] > line {
  transition: stroke 300ms ease-out, opacity 300ms ease-out;
}

@media (prefers-reduced-motion: reduce) {
  [data-target] > rect,
  [data-target] > circle,
  [data-target] > line {
    transition-duration: 0ms !important;
  }
}
```

The CSS `transition` property handles color interpolation automatically
when classes are swapped.  WAAPI is only needed for opacity animations
on add/remove where CSS transitions cannot be triggered (the element
does not exist in the DOM before the animation starts).

### 4.5 Size budget

The animation runtime adds to the existing inline `<script>`:

| Component | Estimated size |
|-----------|---------------|
| `animateTransition()` | ~600 bytes minified |
| `parseSvg()` helper | ~80 bytes |
| `findParentGroup()` helper | ~120 bytes |
| `prefersReducedMotion()` | ~60 bytes |
| `cancelAnimations()` | ~80 bytes |
| CSS transition rules | ~200 bytes |
| **Total** | **~1.1 KB** |

Well under the 2 KB budget.  The manifest JSON per frame adds ~50-200
bytes depending on transition count, but this replaces zero bytes today
(the frames array already exists).

---

## 5. Integration with emit_interactive_html

### 5.1 Python-side changes

In `emit_interactive_html()`, after building the frames list, compute
transition manifests:

```python
# After the single-pass SVG rendering loop:
manifests: list[str] = ['null']  # frame 0 has no "previous"
for i in range(1, len(frames)):
    manifest = compute_transitions(frames[i - 1], frames[i])
    manifests.append(json.dumps(manifest.to_compact()))
```

Embed in the JS frame data:

```python
# Current:
js_frames.append(
    f'{{svg:`{svg_escaped}`,narration:`{narration_escaped}`,'
    f'substory:`{substory_escaped}`,label:`{label_escaped}`}}'
)

# Proposed:
js_frames.append(
    f'{{svg:`{svg_escaped}`,narration:`{narration_escaped}`,'
    f'substory:`{substory_escaped}`,label:`{label_escaped}`,'
    f'tr:{manifests[i]}}}'
)
```

The `tr` key is deliberately short to minimize payload.  `null` for
frame 0 (no transition into the first frame).

### 5.2 JS-side changes

Replace the current `show()` function:

```js
// Current:
function show(i) {
  cur = i;
  stage.innerHTML = frames[i].svg;
  narr.innerHTML = frames[i].narration;
  // ... controls update
}

// Proposed:
function show(i, animate) {
  if (animate && i === cur + 1 && frames[i].tr) {
    animateTransition(cur, i);
  } else {
    snapToFrame(i);
  }
}
```

Call sites:
- `next.addEventListener('click', function() { show(cur+1, true); })`
- `prev.addEventListener('click', function() { show(cur-1, false); })`
- `dot.addEventListener('click', function() { show(j, false); })`
- Keyboard ArrowRight: `show(cur+1, true)`
- Keyboard ArrowLeft: `show(cur-1, false)`

### 5.3 Backward compatibility

The `tr` field is optional.  If absent or `null`, `show()` falls back to
`snapToFrame()` -- identical to today's behavior.  This means:

- Old cached HTML without `tr` fields continues to work unchanged
- Filmstrip mode (`emit_animation_html`) is unaffected -- it never had JS
- Diagram mode is unaffected -- single frame, no transitions
- Substory widgets can independently adopt animation by adding `tr`
  fields to their JSON frame data

---

## 6. Backward/Forward Navigation

| Action | Behavior |
|--------|----------|
| **Next (click/ArrowRight)** | Animate using transition manifest (if present) |
| **Prev (click/ArrowLeft)** | Instant snap to previous frame's static SVG |
| **Jump (click dot)** | Instant snap to target frame |
| **Autoplay** (future) | Chain forward animations with configurable interval |

Reverse animation is explicitly out of scope for v1.  Computing reverse
transitions is non-trivial for structural changes (un-adding an edge
requires knowing where it was drawn), and the visual benefit does not
justify the complexity.

---

## 7. Fallback Paths

| Scenario | Behavior |
|----------|----------|
| **No JavaScript** | `<noscript>` already shows print frames in DOM. Static SVG, no animation. Works today unchanged. |
| **@media print** | Print frames div (`scriba-print-frames`) is shown, interactive widget hidden. Works today unchanged. |
| **prefers-reduced-motion** | `prefersReducedMotion()` returns true -> `animateTransition()` short-circuits to `snapToFrame()`. CSS transitions set to `0ms`. Zero motion. |
| **Old browsers (no WAAPI)** | `typeof Element.prototype.animate === 'undefined'` -> fall back to `snapToFrame()`. Full DOM swap, no animation, no crash. |
| **Missing tr field** | `frames[i].tr` is null/undefined -> `snapToFrame()`. Graceful degradation for cached or legacy output. |

The detection function:

```js
function canAnimate() {
  return typeof Element.prototype.animate === 'function'
      && !prefersReducedMotion();
}
```

Called once at widget init.  If false, the `animate` parameter is never
passed as true, eliminating all animation code paths.

---

## 8. Data Flow Diagram

```
                          Python (build time)
  +-----------------------------------------------------------------+
  |                                                                 |
  |  .tex ─> SceneParser ─> AnimationIR                             |
  |                             |                                   |
  |                             v                                   |
  |                        SceneState                               |
  |                    (apply_prelude,                               |
  |                     apply_frame x N)                             |
  |                             |                                   |
  |                    list[FrameSnapshot]                           |
  |                             |                                   |
  |                             v                                   |
  |                    list[FrameData]                               |
  |                        |         |                              |
  |                        v         v                              |
  |              _emit_frame_svg   compute_transitions              |
  |              (per frame)       (per consecutive pair)            |
  |                        |         |                              |
  |                        v         v                              |
  |                   SVG strings   TransitionManifests             |
  |                        |         |                              |
  |                        v         v                              |
  |              emit_interactive_html()                             |
  |                        |                                        |
  |                        v                                        |
  |           HTML with inline <script>                             |
  |           frames = [{svg, narration, tr}, ...]                  |
  +-----------------------------------------------------------------+

                          Browser (runtime)
  +-----------------------------------------------------------------+
  |                                                                 |
  |  User clicks "Next"                                             |
  |       |                                                         |
  |       v                                                         |
  |  show(cur+1, true)                                              |
  |       |                                                         |
  |       +-- frames[i].tr exists?                                  |
  |       |       |                                                 |
  |       |   YES |              NO                                 |
  |       |       v               v                                 |
  |       | animateTransition()  snapToFrame()                      |
  |       |       |              (innerHTML swap)                   |
  |       |       v                                                 |
  |       | parse target SVG                                        |
  |       | diff current DOM vs manifest                            |
  |       | animate removals (fade out)                             |
  |       | animate recolors (class swap + CSS transition)          |
  |       | animate additions (clone + fade in)                     |
  |       |       |                                                 |
  |       |       v                                                 |
  |       | Promise.all(animations.finished)                        |
  |       |       |                                                 |
  |       |       v                                                 |
  |       | snapToFrame() -- canonical DOM replacement              |
  |       |                                                         |
  +-----------------------------------------------------------------+
```

---

## 9. JS Runtime State Machine

```
              +-------+
              | IDLE  |<──────────────────────+
              +---+---+                       |
                  |                            |
           Next click                   animations done
          (animate=true)                      |
                  |                            |
                  v                            |
           +-----+------+     snap      +-----+------+
           | ANIMATING  +──────────────>| COMPLETE   |
           +-----+------+              +-----+------+
                  |                            |
          Prev/dot click                Next click
          (cancel + snap)               (new animation)
                  |                            |
                  v                            v
              +---+---+                 +------+-----+
              | IDLE  |                 | ANIMATING  |
              +-------+                 +------------+

  Any click during ANIMATING:
    1. Cancel all running WAAPI animations
    2. snapToFrame(target)
    3. State -> IDLE
```

---

## 10. Element Identity Matching

```
  Frame N DOM                Transition Manifest         Frame N+1 SVG (parsed)
  ============               ===================         ======================

  <g data-target=            ["arr.cell[0]",             <g data-target=
     "arr.cell[0]"  -------->  "state",    ------------>    "arr.cell[0]"
     class="state-idle">       "idle","current",           class="state-current">
    <rect fill="#fff"/>        "recolor"]                  <rect fill="#e3f2fd"/>
    <text>5</text>                                        <text>5</text>
  </g>                                                  </g>

  <g data-target=            ["arr.cell[1]",             <g data-target=
     "arr.cell[1]"  -------->  "value",    ------------>    "arr.cell[1]"
     class="state-idle">       "?","4",                    class="state-idle">
    <rect fill="#fff"/>        "value_change"]            <rect fill="#fff"/>
    <text>?</text>                                        <text>4</text>
  </g>                                                  </g>

  (not present)              ["G.edge[(A,B)]",           <g data-target=
                 <----------   "add",       <----------     "G.edge[(A,B)]"
                               null,"idle",                class="state-idle">
                               "element_add"]             <line .../>
                                                        </g>

  Runtime action per row:
    Row 1: el.classList.replace("state-idle","state-current")
           -> CSS transition animates fill from #fff to #e3f2fd
    Row 2: el.querySelector("text").textContent = "4"
    Row 3: clone from parsed N+1 SVG, insert into DOM, fade opacity 0->1
```

---

## 11. Open Questions and Future Work

### v1 scope (this architecture)

- Recolor animation (CSS class swap + transition)
- Value text replacement (instant, no animation on text)
- Element add/remove (opacity fade)
- Highlight on/off (CSS class toggle)
- Annotation add/remove (opacity fade)
- Reduced motion / old browser fallback
- Forward-only animation; backward = instant snap

### v2 candidates (deferred)

- **Position animation**: graph node relayout, array element swap.
  Requires computing layout coordinates for both frames in Python and
  emitting `transform: translate()` deltas in the manifest.
- **Reverse animation**: playing transitions backward on Prev click.
  Requires storing the inverse manifest or computing it on the fly.
- **Staggered timing**: animate elements sequentially rather than all
  at once (e.g. cascade across array cells).  Requires a `delay` field
  per transition and orchestration in the runtime.
- **Substory animation**: applying the same system to substory widgets.
  Mechanically identical but requires threading `tr` through the
  substory JSON data path.
- **Custom easing per transition kind**: different curves for add vs
  recolor.  Trivial to add once v1 is validated.

### Implementation order

1. `differ.py` -- pure Python, fully testable with existing FrameData fixtures
2. CSS transition declarations -- add to `scriba-scene-primitives.css`
3. JS runtime (`animateTransition`, `snapToFrame`, state machine) -- modify inline script in `emit_interactive_html`
4. Wire `compute_transitions` into `emit_interactive_html` frame loop
5. Add `data-annotation` attributes to annotation `<g>` elements in primitives
6. Integration tests: render known .tex files, verify manifest correctness
7. Visual regression: screenshot before/after to confirm no layout shift

Each step is independently shippable.  Steps 1-2 can land without
changing any visible behavior (manifests computed but not consumed;
CSS transitions present but no class swaps happen mid-frame).
