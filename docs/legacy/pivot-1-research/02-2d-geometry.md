# Scriba Research 02 — Continuous 2D Geometry Primitive

> Goal: choose a rendering / geometry library for Scriba's `Plane` primitive, which must render competitive-programming computational-geometry visualizations (convex hull, half-plane intersection, line sweep, rotating calipers, Li Chao tree) as SVG widgets with keyframe-style animation between algorithm states.

## Executive Summary

**Recommendation: Two.js as the renderer, composed with flatten-js as the compute layer. JSXGraph as the fallback.**

Scriba's existing primitives are discrete and rendered via D2 to SVG. For a continuous plane we need three capabilities that no single library bundles well:

1. A **compute kernel** that can produce the actual geometric state at step *k* (convex hull stack, half-plane intersection polygon, sweep status, tangent lines).
2. A **scene representation** that can be diffed between step *k* and step *k+1* so the authoring DSL stays declarative — the author says "at step 4 the hull is `[p0, p2, p5, p7]`" and the renderer handles the tween.
3. An **SVG emitter** usable in Node (SSR) so Scriba can bake widgets into HTML at compile time, matching how D2 is currently used.

Two.js ([jonobr1/two.js](https://github.com/jonobr1/two.js), ~8.4k stars, MIT, active) is the only pure-rendering option that targets SVG / Canvas / WebGL from a single declarative scene graph, runs headless in Node, stays under ~60 KB gzipped, and exposes a clean `Two.Path`/`Two.Anchor` API that's trivial to interpolate frame-by-frame. It has no geometry brain, which is fine: **flatten-js** ([alexbol99/flatten-js](https://github.com/alexbol99/flatten-js), MIT, ~1k stars) supplies Point / Segment / Line / Polygon / Box with boolean ops, containment, and distance — everything needed for hulls, half-plane intersection, and sweep status. Both are pure TypeScript/JS, install cleanly in the Scriba compiler, and the combined footprint is far under the landing-page JS budget even when both ship to the widget runtime.

Trade-offs accepted: we write the *algorithm simulators* ourselves (Andrew's chain, rotating calipers, Li Chao) — these are 30–80 lines each and are the actual editorial content anyway. We do not get JSXGraph's "drop a slider, get a live construction" magic, but Scriba is editorial, not interactive — keyframed SVG is the product.

## Comparison Matrix

Legend: ✅ good · ⚠️ usable with effort · ❌ blocker

| Library | Declarative CP API | State-to-state animation | SVG out | Node SSR | Bundle (gz) | License | Maintenance | Step controller fit |
|---|---|---|---|---|---|---|---|---|
| **JSXGraph** | ✅ `board.create('point', ...)`, `line`, `polygon` native | ⚠️ imperative `moveTo` tweens, no keyframe diff | ✅ native SVG board | ⚠️ works via jsdom, not first-class | ⚠️ ~220 KB | LGPL-3 / MIT dual | ✅ active, 20+ yrs | ⚠️ designed for sliders, not keyframes |
| **GeoGebra Web** | ✅ richest geometry DSL on the web | ✅ built-in construction protocol | ⚠️ canvas-first, SVG export is lossy | ❌ browser-only, iframe embed | ❌ >2 MB | ❌ proprietary, non-free | ✅ active | ❌ iframe, no compile-time bake |
| **CindyJS** | ✅ CindyScript, very expressive | ⚠️ animation via scripting, not keyframe | ⚠️ canvas + limited SVG | ❌ browser-only | ⚠️ ~400 KB | Apache-2.0 | ⚠️ slow (last release 2020) | ⚠️ imperative |
| **Paper.js** | ⚠️ vector-first, no `halfplane`; roll your own | ✅ `Path` segment interpolation is clean | ✅ `project.exportSVG()` | ⚠️ needs `paper-jsdom` | ⚠️ ~100 KB | MIT | ⚠️ slow (maintained, minor releases) | ✅ scene diff friendly |
| **Two.js** | ⚠️ primitives are `Path`/`Line`/`Circle`; wrap yourself | ✅ anchors are plain `{x,y}`, trivial to tween | ✅ `toString()` returns SVG | ✅ `Two({ type: Two.Types.svg })` headless | ✅ ~55 KB | MIT | ✅ active, 8.4k stars | ✅ scene graph diff |
| **Geometric.js / flatten-js** | ✅ pure geometry: `Polygon`, `Segment`, `BooleanOp` | n/a (no renderer) | n/a | ✅ pure JS | ✅ ~40 KB | MIT | ✅ flatten-js active; geometric.js stale | ✅ compute only |
| **Konva.js** | ⚠️ generic Shape API, no geometry semantics | ✅ `Tween` built-in | ❌ canvas only, no SVG export | ⚠️ `konva-node` via node-canvas (native deps) | ⚠️ ~150 KB | MIT | ✅ active | ⚠️ canvas locks out printable output |
| **Raw SVG + D3** | ⚠️ build everything from scratch | ✅ `d3.interpolate` is the gold standard | ✅ native | ✅ `d3-selection` + jsdom | ⚠️ modular, 30–80 KB | BSD-3 | ✅ active | ✅ full control |

## Detailed Analysis — Top 3

### 1. Two.js + flatten-js (recommended)

Two.js is a tiny scene-graph library whose core idea is a `Two.Group` containing `Two.Path` objects, each of which is a list of `Two.Anchor` control points with position, handles, and command type. The magic for Scriba is that the scene graph is *plain data*: rendering to SVG is `two.update()` followed by reading `two.renderer.domElement.outerHTML`. Running it headless in Node is documented and simple — instantiate with `type: Two.Types.svg` and a jsdom `document`, no native modules.

Because `Two.Path` vertices are mutable `{x, y}` pairs, interpolating `hull_k → hull_{k+1}` reduces to a per-vertex lerp with an easing function. When vertices are added (hull grows) or removed (stack pop), we pad the shorter path with a duplicate of the insertion point so the tween looks like a birth/death rather than a jump — the same trick d3-shape uses for area charts.

flatten-js gives us the compute side: `new Polygon(points)`, `polygon.intersect(line)`, `Point.distanceTo(segment)`, convex hull via `Polygon.convexHull` (via the graham-scan it pulls in), and a Box/BVH. It is pure JS, has TS types, and is used by a few production CAD tools. We wrap it behind Scriba's own `Plane` AST so authors never touch it directly.

The downside is that we inherit no "geometry primitives as first-class drawables" — a `halfplane` is not a Two.js shape, so we render it as a big clipped polygon against the plane's bounding box. This is a ~30-line helper, not a research project.

Effort estimate: **medium** (4–6 days: renderer wrapper, 6 algorithm simulators, DSL parser extension, SVG snapshot tests).

### 2. JSXGraph (fallback)

JSXGraph ([jsxgraph.org](https://jsxgraph.org), [jsxgraph/jsxgraph](https://github.com/jsxgraph/jsxgraph)) is the most CP-friendly API on paper: `board.create('point', [1,2])`, `create('line', [pA, pB])`, `create('polygon', [...])`, and even `create('angle', ...)`. It renders native SVG and has 20 years of math-education momentum behind it. For convex hull, half-plane intersection, and rotating calipers the primitives map 1:1.

Three problems for Scriba's specific use case:

1. **Animation model is dependency-based, not keyframe-based.** JSXGraph's philosophy is "bind a slider, derive everything else". For editorial widgets we want "at step 7, pop the top of the stack" — which in JSXGraph means manually `remove()` and `create()` on each frame, bypassing the point of the library.
2. **Node SSR is second-class.** It runs under jsdom but the docs assume browser, and the SVG output embeds event handlers we'd have to strip.
3. **Bundle size.** 220 KB gzipped is heavy for a per-widget payload if we ever hydrate; baking at compile time is fine but then we're mostly using it as a slow SVG printer.

JSXGraph remains the fallback if Two.js + flatten-js hits an unexpected wall on (say) half-plane intersection visuals.

Effort estimate: **medium-high** (similar code volume, plus jsdom/SSR plumbing).

### 3. Paper.js

Paper.js ([paperjs.org](http://paperjs.org), [paperjs/paper.js](https://github.com/paperjs/paper.js)) sits between Two.js and JSXGraph: rich path algebra (boolean ops on `Path`s, `Path.getIntersections`, `Path.getNearestPoint`), clean SVG export via `project.exportSVG()`, and a respected MIT codebase. It has `paper-jsdom` for headless Node. For half-plane intersection in particular its built-in path intersection is tempting — no flatten-js needed.

Why it's not the primary: (a) maintenance cadence has slowed significantly since 2022; (b) the bundle is ~100 KB vs Two.js's ~55 KB without offering much more for our needs once flatten-js is already on the compute side; (c) the scene graph is less amenable to mechanical keyframe diffing because `Path` segments carry bezier handles we don't want, and resetting them every frame is fighting the library.

Effort estimate: **medium**.

## Scriba API Sketch — the `Plane` primitive

The authoring DSL stays declarative. Authors describe *algorithm states*; Scriba computes keyframes, Two.js renders SVG, the step controller advances.

```scriba
plane hull_demo {
  bounds: [-1, -1, 10, 10]
  grid: 1

  points P = [(1,1), (2,5), (3,2), (5,6), (6,3), (7,7), (8,2), (9,5)]

  sim andrew_hull(P) as steps   // built-in simulator, yields {stack, candidate, turn}

  frame step in steps {
    draw points(P) style=dot
    draw point(step.candidate) style=active
    draw polyline(step.stack) style=hull.partial
    if step.turn == "right" {
      annotate step.stack[-2] "pop →" style=warn
    }
    caption "i=${step.i}  stack=${step.stack}"
  }

  transition ease=cubic duration=400ms
}
```

Under the hood: `andrew_hull` is a pure-JS simulator returning an array of frames `[{ i, stack: Point[], candidate: Point, turn: 'left'|'right' }]`. The `Plane` compiler walks each frame, builds a Two.js scene (a `Group` per style class), tweens anchors against the previous frame using d3-interpolate-style padding for added/removed vertices, and emits one SVG per keyframe plus a tiny ~2 KB runtime that advances via the shared step controller already used by Scriba's array/graph widgets.

For half-plane intersection the simulator yields `{ active: HalfPlane[], polygon: Polygon }` per step; rendering clips the plane bounding box to `polygon` via flatten-js boolean ops, producing a shrinking SVG `<path>`. Rotating calipers yields two parallel line segments whose angle advances; line sweep yields `{ sweepX, activeSet }`. Li Chao yields a collection of line segments restricted to their dominance intervals.

## Risks and Gaps

- **Topology changes under tween.** When a convex hull gains a vertex, interpolation must insert a degenerate vertex at the correct index, otherwise edges cross during the tween. Mitigation: reuse d3-shape's "key function" pattern, keyed by the point's original index in `P`.
- **Half-plane intersection numerical stability.** flatten-js uses floating-point; degenerate inputs (three concurrent lines) can produce zero-area slivers. Mitigation: snap output polygon vertices to a configurable epsilon before rendering.
- **Voronoi / Delaunay coverage.** flatten-js does not ship Delaunay. If this becomes required, add [d3-delaunay](https://github.com/d3/d3-delaunay) (BSD, 2 KB, Delaunator under the hood). Classified as nice-to-have so not blocking.
- **Two.js SVG text rendering** is known to be weaker than its path rendering. Scriba already owns typography via its scriba-html layer; labels should be emitted as `<text>` outside the Two.js scene, positioned from the same coordinate transform.
- **SSR jsdom cost.** Each `Plane` widget bakes N frames at compile time. For a 30-frame hull on 50 points this is <50 ms per widget; acceptable.
- **No interactivity.** This design explicitly does not support "drag a point, re-run the algorithm". Adding that later means swapping to JSXGraph or wiring the simulator to live input — a future concern, not v1.

## Recommendation

**Primary: Two.js (MIT, ~55 KB) + flatten-js (MIT, ~40 KB) + Scriba-owned algorithm simulators.** Both headless-Node friendly, both SVG-native, both actively maintained, combined bundle fits the microsite budget, and the authoring DSL stays in Scriba's voice instead of leaking a third-party geometry dialect.

**Fallback: JSXGraph.** If half-plane intersection rendering or numerical edge cases consume more than two days to stabilize, pivot to JSXGraph's native `polygon` primitives and accept the heavier bundle / imperative animation.

**Implementation effort: medium.** Roughly one engineer-week for the renderer wrapper, the six algorithm simulators (Andrew, half-plane intersection deque, line sweep status, rotating calipers, Li Chao), DSL surface extension, and SVG snapshot tests. Delaunay/Voronoi is deferred.

### References

- Two.js — https://two.js.org · https://github.com/jonobr1/two.js
- flatten-js — https://github.com/alexbol99/flatten-js
- JSXGraph — https://jsxgraph.org · https://github.com/jsxgraph/jsxgraph
- Paper.js — http://paperjs.org · https://github.com/paperjs/paper.js
- CindyJS — https://cindyjs.org · https://github.com/CindyJS/CindyJS
- Konva.js — https://konvajs.org · https://github.com/konvajs/konva
- d3-delaunay — https://github.com/d3/d3-delaunay
- Andrew's monotone chain — https://en.wikibooks.org/wiki/Algorithm_Implementation/Geometry/Convex_hull/Monotone_chain
