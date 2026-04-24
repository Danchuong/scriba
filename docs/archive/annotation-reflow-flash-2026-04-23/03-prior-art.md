# Prior Art: Layout-Preserving Step-by-Step Annotation Additions

**Problem context:** Scriba renders algorithm animations as a series of SVG frames. When
`\annotate{...}` is inserted between steps the target primitive's bounding box grows (to
accommodate the arrow and label), downstream primitives translate down instantly, and the
frame switcher snaps between the two layouts — producing a visible "flash". This document
surveys how peer frameworks avoid or mitigate the same class of problem.

---

## 1. Manim / ManimCE / ManimGL

### Scene graph model

Manim represents everything as a **Mobject** (mathematical object). Mobjects form a tree
through their `submobjects` list; the `VGroup` container is the standard way to bundle
related objects. The scene maintains a flat `Scene.mobjects` list (render order) and a
`z_index` property per object for depth sorting.
([Mobject API](https://docs.manim.community/en/stable/reference/manim.mobject.mobject.Mobject.html),
[Building blocks tutorial](https://docs.manim.community/en/stable/tutorials/building_blocks.html))

### Layout strategy

Manim uses a **global absolute coordinate system** centred at the origin; there is no
CSS-style flow layout. Primitive placement uses `move_to()` (absolute) or `next_to()`
(relative offset from another object's bounding box). When an arrow or brace annotation is
added to the scene it simply occupies additional coordinate space; it does **not** trigger
a reflow of sibling objects that were placed independently. Downstream objects only move if
the author explicitly calls `shift()` or recalculates a `next_to()` chain.

Annotations (`Arrow`, `Brace`, `SurroundingRectangle`, `CurvedArrow`) are first-class
Mobjects that coexist in the scene's coordinate space. Because there is no document-flow
engine, adding them never causes automatic redistribution of other objects.
([VGroup docs](https://docs.manim.community/en/stable/reference/manim.mobject.types.vectorized_mobject.VGroup.html),
[GrowArrow](https://docs.manim.community/en/stable/reference/manim.animation.growing.GrowArrow.html))

### Transition strategy

Manim explicitly **animates every state change** via `self.play(...)`. When an annotation
is introduced the author writes, for example:

```python
arrow = Arrow(start=node.get_bottom(), end=label.get_top())
self.play(GrowArrow(arrow), Write(label))
```

The arrow is grown over the configured run-time (default 1 s). If a downstream object must
shift to make room the author also includes
`self.play(my_group.animate.shift(DOWN * 0.5))` in the same or subsequent `play()` call,
and Manim interpolates the transform. Nothing moves by itself; every motion is declared.
([Animation API](https://docs.manim.community/en/stable/reference/manim.animation.animation.Animation.html),
[TransformAnimations](https://docs.manim.community/en/stable/reference/manim.animation.transform.TransformAnimations.html))

### Key takeaway for Scriba

Manim sidesteps the reflow problem by having **no flow layout at all**. The author bears
the cost of re-anchoring objects manually when layout changes. This is feasible for
hand-crafted videos but impractical for a declarative system like Scriba. The useful
principle is: *annotate on a separate coordinate plane and manage downstream shifts
explicitly as animated transforms rather than relying on a layout engine.*

---

## 2. Motion Canvas

### Scene graph model

Motion Canvas organises scenes as a **node tree**, where the root is the scene `view`.
Every node is an instance of a class extending `Node`. Layout-aware nodes extend `Layout`
(analogous to a flex container); plain `Node` subclasses are layout-agnostic.
([Scene hierarchy](https://motioncanvas.io/docs/hierarchy/),
[Layout API](https://motioncanvas.io/api/2d/components/Layout/))

### Layout strategy

Motion Canvas exposes a **flexbox-based opt-in layout** via the `layout` property.
Crucially, nodes that do **not** extend `Layout` (i.e. raw `Node` instances) are
**excluded from flow calculation** — they are treated as if they are not in the hierarchy
for layout purposes. This is the architectural escape hatch: place annotation nodes as
non-layout children or siblings, and they do not push other nodes around.
([Layouts docs](https://motioncanvas.io/docs/layouts/))

Nodes support an `absolutePosition` signal that operates in world space, enabling
annotations to be pinned to a world coordinate without participating in any flex flow.
([Positioning docs](https://motioncanvas.io/docs/positioning/))

### Transition strategy

Motion Canvas uses **generator-based imperative animation**: the author `yield`s animation
calls, and the framework interpolates signals between values over specified durations. When
layout changes between steps (e.g. a new flex child is added), sibling nodes reflow, but
Motion Canvas can interpolate the resulting position change by reading the signal's current
value and its target value at each frame. The author can wrap a layout mutation in a
`waitFor` or `all()` to play the reposition as a smooth tween rather than an instant snap.

### Key takeaway for Scriba

The **opt-out-of-layout node** pattern is directly transferable. Annotations could be
rendered as non-layout children of the scene root (or a dedicated annotation `<g>`) and
absolutely positioned to the correct world coordinate, leaving the main layout flow
untouched.

---

## 3. D3.js + d3-annotation

### Scene graph model

D3 has no scene graph; it manipulates DOM/SVG nodes directly. The conventional idiom is a
separate SVG `<g class="annotation-group">` appended after all data layers — annotations
are an **explicit overlay group** that has no spatial relationship to the data layers from
SVG's perspective. Each annotation in the `d3-annotation` library is a composite of three
sub-elements: *subject*, *connector*, and *note*.
([d3-annotation GitHub](https://github.com/susielu/d3-annotation),
[d3-annotation 2.0 release notes](https://www.susielu.com/data-viz/d3-annotation-2))

### Layout strategy

Because annotations live in a **dedicated `<g>` with absolute SVG coordinates** they
cannot affect the position of chart axes, bars, or other data elements. The annotation
co-ordinates are computed at render time from data values via the same scales used for the
chart — they shadow the data coordinate system but do not participate in any layout engine.
Labels can be positioned via absolute `nx`/`ny` (world coordinates) or relative `dx`/`dy`
offsets introduced in v2.0 to give finer control without triggering layout side-effects.

### Transition strategy

D3 transitions are applied to the annotation group by passing updated annotation data
through the generator and calling `.update()`. The article *Transitioning on D3 annotations*
(Henry Lau, 2019) demonstrates using `d3.interpolateNumber` inside a custom tween so that
annotation position and label content animate smoothly without any reflow of the underlying
chart — because the chart elements are in a completely separate DOM subtree.
([Henry Lau — Transitioning on D3 annotations](https://www.henrylau.co.uk/2019/09/19/transitioning-on-D3-annotations/))

### Key takeaway for Scriba

The **separate `<g>` overlay** pattern is the simplest and most applicable: render all
annotation arrows and labels into a `<g id="annotations">` that sits on top of the
primitive stack in the SVG, positioned with absolute coordinates derived from the primitive
geometry at commit time. Growing an annotation label in this group cannot affect sibling
primitive positions because SVG `<g>` elements have no block-formatting context.

---

## 4. Excalidraw

### Scene graph model

Excalidraw stores elements in a flat array. Render order (z-order) is determined by
**position in the elements array** — no tree, no layout engine. Bounding boxes are
computed per element at render time via `getCommonBounds()`, which returns
`[minX, minY, maxX, maxY]` over rotated element bounds.
([Element Transformations — DeepWiki](https://deepwiki.com/excalidraw/excalidraw/3.4-element-transformations))

### Layout strategy

Excalidraw is a freehand whiteboard: there is **no layout engine**. Every element has
absolute `x`, `y`, `width`, `height`. Adding a text annotation near an existing element
does not displace it. This is the same absolute-coordinate philosophy as Manim.

### Transition strategy

Excalidraw does not animate layout transitions. Resize/move interactions mutate element
coordinates directly and re-render. The framework is listed here because its flat
immutable-element model (each edit creates a new snapshot for undo) is architecturally
interesting: layout "flash" cannot occur because there is no layout pass to produce
inter-frame shifts.

### Key takeaway for Scriba

Excalidraw's immutable element snapshot approach — each frame is a complete, self-contained
scene — aligns with Scriba's existing model. The lesson is to **keep annotation geometry
fully resolved and stored alongside the frame**, rather than re-deriving it from bounding
boxes at render time.

---

## 5. Mermaid.js

### Scene graph model

Mermaid compiles diagram syntax to SVG using layout engines (Dagre by default for
flowcharts; ELK as an opt-in). Dagre builds a `graphlib.Graph`, runs its layout algorithm,
then positions SVG nodes at the resulting coordinates. There is **no incremental or live
layout** — the entire diagram is laid out from scratch for each render.
([Layout Engines — DeepWiki](https://deepwiki.com/mermaid-js/mermaid/2.3-layout-engines),
[Mermaid Layouts](https://mermaid.js.org/config/layouts.html))

### Layout strategy

Because Mermaid rerenders the full diagram on each source change it **cannot exhibit
annotation-injection reflow** in the interactive sense — but it also cannot animate
transitions between states. Applying a style change to a node (which resizes it) causes
full re-layout and re-render; there is no incremental patch.

### Transition strategy

None. Mermaid is a static diagram renderer. Users who want animated Mermaid-style diagrams
typically layer a D3 or GSAP transition on top of two rendered SVGs.

### Key takeaway for Scriba

Mermaid's approach is a cautionary example of what Scriba should avoid: a full re-layout
on every frame change is exactly the root cause of the "flash" problem. The relevant
insight is that **pre-computing and caching layout at authoring time** (as Mermaid does
per diagram, not per render) is preferable to dynamic re-layout at playback time.

---

## 6. Reveal.js Auto-Animate / Keynote Magic Move

### Scene graph model

Both tools use a **slide-pair model**: each "step" is a complete, independently laid-out
slide/frame. There is no shared live scene graph between steps.

Reveal.js `auto-animate` matches elements across adjacent slides by text content, `src`
attribute, or an explicit `data-id` attribute. Keynote Magic Move requires the author to
duplicate the slide; elements on both slides that are "the same object" (by object
identity, since the slide was duplicated) participate in the transition. Elements that
appear only on the destination slide fade in; elements that disappear fade out.
([Reveal.js Auto-Animate](https://revealjs.com/auto-animate/),
[Keynote Magic Move](https://support.apple.com/guide/keynote/add-transitions-tanff5ae749e/mac))

### Layout strategy

Each frame/slide is **statically laid out independently**. There is no concept of
"growing" a bounding box mid-animation — rather, the destination frame already contains
the fully-laid-out result (annotation included), and the transition engine animates *from*
the source geometry *to* the destination geometry.

### Transition strategy

Reveal.js internally applies a **CSS `transform`** to make each matched element appear to
start at its old position, then animates the removal of that offset to land at its new
position. Unmatched new elements fade in from opacity 0. This is effectively the FLIP
technique applied declaratively via element-identity matching.

Keynote uses native Core Animation under the hood with the same conceptual model: snapshot
old positions, snapshot new positions, emit position/scale tweens for matched elements,
crossfade unmatched ones.

### Key takeaway for Scriba

This is the most directly applicable model for Scriba's **frame-based architecture**:

1. Pre-render two complete SVG frames (before annotation, after annotation).
2. Use element identity (`data-id` or stable element IDs) to match primitives across
   frames.
3. At playback, FLIP-animate matched elements from their old bounding rect to their new
   one; fade in the new annotation elements.

This requires **no changes to layout computation** — it operates entirely in the display
layer.

---

## 7. GSAP FLIP Technique

### Overview

FLIP (First, Last, Invert, Play) was coined by Paul Lewis (Aerotwist, 2015) and
formalised as `Flip.getState()` / `Flip.from()` in GSAP's Flip plugin.
([Aerotwist — FLIP Your Animations](https://aerotwist.com/blog/flip-your-animations/),
[GSAP Flip plugin](https://gsap.com/docs/v3/Plugins/Flip/))

### How it works

1. **First** — capture bounding rects of all elements before the layout change
   (`Flip.getState(targets)`).
2. **Last** — apply the layout mutation (add DOM node, change class, etc.). Elements are
   now in their final positions but have *not* been painted yet.
3. **Invert** — apply `transform` offsets to every element so they *appear* to be in their
   old positions.
4. **Play** — animate the removal of those offsets, so elements glide to their new
   positions at 60 fps on the compositor thread.

Because only `transform` and `opacity` are animated (not `width`, `height`, `top`, or
`left`), the browser never triggers an expensive layout pass during the animation itself.

### Applicability

GSAP Flip is DOM/CSS-centric. The docs do not describe SVG-specific support. However, the
**algorithmic pattern** applies to SVG: capture `getBBox()` before and after, compute the
delta, emit a CSS `transform: translate(dx, dy)` tween on affected `<g>` elements, then
snap to final position when the tween completes. The SVG layout (attribute positions)
matches the final state throughout; only a visual offset is applied during the transition.

### Key takeaway for Scriba

FLIP is the **lowest-risk transition strategy** when frame layout is pre-computed. If
Scriba pre-resolves both the current and next frame's geometry at build time (which it
already does), FLIP reduces the "flash" to a short translate tween with zero layout
recalculation at playback.

---

## 8. Additional Framework: Remotion + Code Hike

Not in the original list but highly relevant.

**Remotion** renders React components to video frames using `useCurrentFrame()`. Each
frame is a deterministic pure function of the frame number — the same philosophy as
Scriba. Code Hike is a Remotion-integrated library for animating code annotations
step-by-step.

**Layout strategy:** Remotion's `<Sequence>` children are wrapped in `AbsoluteFill` by
default (opt out with `layout="none"`). Code annotations are rendered as React components
that overlay the code block without affecting its height. This is the same overlay
principle as d3-annotation's separate `<g>`.

**Transition strategy:** Between steps, Code Hike interpolates token positions using a
spring-based tween driven by the frame number, keeping the viewport stable while tokens
slide to their new positions. New tokens fade in; removed tokens fade out.
([Code Hike + Remotion](https://codehike.org/blog/remotion),
[Remotion Sequence docs](https://www.remotion.dev/docs/sequence))

---

## Comparison Table

| Framework | Annotation placement | Layout strategy | Transition strategy | Applicable to Scriba? |
|---|---|---|---|---|
| **Manim / ManimCE** | Same absolute coordinate space as primitives | No flow layout; absolute coords only | Explicit `play()` interpolation declared by author | Partial — absolute coords idea is applicable; author-declared transforms impractical |
| **Motion Canvas** | Non-layout `Node` (opt out of flex flow) | Opt-in flexbox; non-layout nodes excluded | Generator-based signal tweening; layout mutations interpolated | Yes — opt-out-of-layout pattern for annotation nodes |
| **D3 + d3-annotation** | Separate `<g class="annotation-group">` at top of SVG | No layout engine; absolute SVG coords | D3 transition tween on annotation group, independent of data layer | Yes — separate `<g>` overlay is directly adoptable |
| **Excalidraw** | Flat element array; absolute `x/y` per element | No layout engine; freehand absolute | None (instant mutation + re-render with undo snapshots) | Partial — immutable-snapshot model aligns with Scriba frames |
| **Mermaid.js** | Node labels inside layout graph | Full Dagre re-layout on each change | None (static re-render) | Negative example — full re-layout is the root cause of flash |
| **Reveal.js Auto-Animate** | Element on destination slide is fully laid-out | Each slide is independently laid out | CSS transform FLIP via element-id matching; fade for unmatched | Yes — frame-pair model + FLIP matches Scriba architecture exactly |
| **Keynote Magic Move** | Same object duplicated across slide pair | Each slide independently laid out | Core Animation tween from old to new bounds; fade for unmatched | Yes — same principle as Reveal.js |
| **GSAP FLIP** | Post-mutation; layout already settled | Layout computed by browser/engine first | `getBoundingClientRect` delta → compositor transform tween | Yes — adapt `getBBox()` delta → SVG `transform` tween |
| **Remotion + Code Hike** | Absolute overlay (`AbsoluteFill`) | Annotations outside flex flow | Spring-interpolated token positions per frame number | Yes — overlay + frame-function model mirrors Scriba |

---

## Recommendations

Three approaches are most directly applicable given Scriba's constraints (deterministic
SVG output, replay-safe, reduced-motion compatible, no JS-heavy runtime during playback):

### Recommendation 1 — Separate annotation `<g>` overlay (d3-annotation / Remotion pattern)

Move all annotation arrows and labels into a **dedicated `<g id="scriba-annotations">`**
that is appended after the primitive stack in every emitted SVG frame. Annotation
coordinates are resolved at build time from the target primitive's geometry; they are
stored as absolute SVG coordinates inside this group. Because SVG groups have no
block-formatting context, the annotation group can grow arbitrarily without displacing any
primitive. This is the smallest possible change to Scriba's current architecture, requires
no runtime JS, and is fully replay-safe.

### Recommendation 2 — Pre-resolve both frames + FLIP tween at playback (Reveal.js / GSAP pattern)

For animated playback (not static export), apply **element-identity-based FLIP
transitions** between the annotation-absent and annotation-present frames. Each primitive
`<g>` carries a stable `data-scriba-id` attribute. The frame switcher:

1. Reads `getBBox()` (or stored geometry) for each matched element in the current frame.
2. Swaps to the next frame (which already has correct final layout).
3. Computes the delta for each element whose position changed.
4. Applies a short CSS `transform: translate(dx, dy)` that cancels the delta.
5. Animates the transform to `translate(0, 0)` over ~150–300 ms.
6. New annotation elements start at `opacity: 0` and fade to `opacity: 1`.

This requires zero re-layout at playback; all positions are pre-computed. It degrades
gracefully under `prefers-reduced-motion` by skipping the tween and rendering the final
frame immediately.

### Recommendation 3 — Reserved-slot bounding box (Manim / Motion Canvas pattern)

At build time, if a primitive will have an annotation in *any subsequent frame*, reserve
vertical space equal to the annotation's measured height in *all earlier frames* (filling
it with transparent padding). This keeps the primitive's bounding box constant across the
transition, so no downstream shift occurs and no transition animation is needed. This is
the most aggressive layout-stabilisation strategy, similar to the browser's "content-size"
hint for images, and works with static SVG export without any JS. The downside is wasted
whitespace in pre-annotation frames and the need to forward-scan the annotation schedule
at build time.

**Recommended priority:** Recommendation 1 (separate `<g>`) should be the baseline fix
because it eliminates layout coupling entirely at zero playback cost. Recommendation 2
(FLIP tween) layers a smooth animated transition on top for interactive playback.
Recommendation 3 (reserved slot) is a fallback for contexts where the FLIP tween is
unacceptable (e.g. static PDF/PNG export requiring identical bounding boxes across all
frames).
