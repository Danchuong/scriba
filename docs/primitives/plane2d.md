# Primitive Spec: `Plane2D`

> Status: **shipped in v0.5.x** as an extended primitive. Extends the
> base primitive catalog in [`environments.md`](../spec/environments.md)
> and [`ruleset.md`](../spec/ruleset.md) §5. Error codes in range
> **E1460–E1466** — see [`error-codes.md`](../spec/error-codes.md) for
> the canonical list.
>
> Coordinate convention: **authors write math-convention coordinates
> (origin bottom-left, Y up)**. The emitted SVG uses native SVG
> coordinates internally (origin top-left, Y down); the transform that
> bridges the two is documented in §4.

---

## 1. Overview

`Plane2D` renders a 2D coordinate plane with lines, points, segments, polygons, and
shaded regions. It emits pure `<svg>` with no runtime JavaScript. It unlocks:

- **HARD-TO-DISPLAY #6** (Convex Hull Trick / Li Chao Tree): the tangent-line geometry
  showing which line achieves the minimum (or maximum) at each query point. Authors draw
  the lower envelope as a sequence of line segments and shade half-planes.
- **HARD-TO-DISPLAY #4** (FFT): the unit circle visualization with roots of unity as
  points, rotated by CSS `@keyframes`.
- All computational geometry editorials: convex hull, half-plane intersection, Minkowski
  sum, rotating calipers, Voronoi, nearest-pair.

`Plane2D` replaces the runtime Two.js proposal from research A2 with a pure Python
compile-time SVG emitter. No external dependency.

---

## 2. Shape declaration

```latex
\shape{p}{Plane2D}{
  xrange=[-5, 5],
  yrange=[-5, 5],
  grid=true,
  axes=true,
  aspect="equal",
  width=320,
  height=320
}
```

### 2.1 Parameters

| Parameter | Type                         | Default       | Description                                                  |
|-----------|------------------------------|---------------|--------------------------------------------------------------|
| `xrange`  | `[float, float]`             | `[-5, 5]`     | Minimum and maximum x values in **author (math) coordinates**. |
| `yrange`  | `[float, float]`             | `[-5, 5]`     | Minimum and maximum y values in **author (math) coordinates**. |
| `grid`    | `bool` or `"fine"`           | `true`        | Draw grid lines. `true` = integer positions; `"fine"` = also 0.2 intervals. |
| `axes`    | `bool`                       | `true`        | Draw x-axis and y-axis through the origin (or at boundary if origin not visible). |
| `aspect`  | `"equal"` \| `"auto"`        | `"equal"`     | `"equal"`: square units (geometry editorials). `"auto"`: fill viewport. |
| `width`   | integer (px)                 | 320           | ViewBox width.                                               |
| `height`  | integer (px)                 | 320           | ViewBox height. Ignored when `aspect="equal"` (height computed from width and ranges). |
| `points`  | list of `(x, y)` tuples      | `[]`          | Initial static points.                                       |
| `lines`   | list of line specs           | `[]`          | Initial static lines. Format: `(label, slope, intercept)` or `(label, {a=, b=, c=})` (ax+by=c form). |
| `segments`| list of `((x1,y1),(x2,y2))` | `[]`          | Initial static segments.                                     |
| `polygons`| list of lists of `(x, y)`   | `[]`          | Initial static polygons. Each polygon must be a closed list (last point == first, or auto-closed). |
| `regions` | list of region specs         | `[]`          | Initial static shaded half-planes or polygons. Format: `{polygon=[...], fill="rgba(...)"}`. |

**`aspect="equal"` height computation:** when `aspect="equal"` and explicit `height` is
given, the tighter constraint wins. When only `width` is given:

```
height = width * (yrange[1] - yrange[0]) / (xrange[1] - xrange[0])
```

If `xrange` or `yrange` has equal endpoints (degenerate), emit **E1460** (viewport-invalid).

**Unknown parameter:** surfaces through the generic parse/validation
path — see [`error-codes.md`](../spec/error-codes.md) for the current
mapping.

### 2.2 Line specification format

A line can be specified as:

- `(label, slope, intercept)` — slope-intercept form `y = slope * x + intercept`. `label`
  is a string for display.
- `(label, {a=A, b=B, c=C})` — general form `Ax + By = C`. Degenerate (A=0, B=0) emits
  **E1461** (line-degenerate).
- Vertical line: `(label, {a=1, b=0, c=X0})` for the line `x = X0`.

---

## 3. Addressable parts (selectors)

| Selector          | Addresses                                           |
|-------------------|-----------------------------------------------------|
| `p`               | The entire plane (whole-shape target)               |
| `p.point[i]`      | Point at 0-based index in the points list           |
| `p.line[i]`       | Line at 0-based index in the lines list             |
| `p.segment[i]`    | Segment at 0-based index                            |
| `p.polygon[i]`    | Polygon at 0-based index                            |
| `p.region[i]`     | Region at 0-based index                             |
| `p.label[i]`      | Text label at 0-based index (labels are auto-created alongside points/lines) |
| `p.all`           | Every element in the plane                          |

Index is 0-based and refers to the order in which elements were added
(initial `\shape` params fill slots 0..N-1; subsequent `add_*` operations
append). Out-of-range indices are reported through the shared selector
validation path — see [`error-codes.md`](../spec/error-codes.md).

---

## 4. SVG coordinate transform

### 4.1 Author convention

Authors specify all coordinates in **math convention**: origin at bottom-left, Y axis
pointing upward. This matches the intuition of all CP geometry problems. For example,
`point(0, 0)` is at the bottom-left of the viewport; `line(y=1)` is one unit above the
x-axis.

### 4.2 SVG native convention

SVG uses origin at top-left, Y axis pointing downward. These two conventions are
incompatible; displaying math coordinates directly in SVG would flip the Y axis.

### 4.3 The transform

The emitter places all geometric content inside a `<g class="scriba-plane-content">` group
with a single `transform` attribute that:

1. Translates the origin from SVG top-left to the math-frame bottom-left, accounting for
   padding and the scaled coordinate range.
2. Flips the Y axis.

```
transform="translate({tx}, {ty}) scale({sx}, {sy})"
```

Where:

```
pad = 32  # pixels of padding inside the viewbox for labels/axes

# Scale factors: map math units to SVG pixels
sx =  (width  - 2 * pad) / (xrange[1] - xrange[0])
sy = -(height - 2 * pad) / (yrange[1] - yrange[0])   # negative = Y-flip

# Translation: maps math origin (0,0) to SVG position
tx = pad + (-xrange[0]) * sx
ty = (height - pad) + yrange[0] * (height - 2*pad) / (yrange[1] - yrange[0])
```

This is equivalent to:

```
transform="translate({tx}, {height - pad}) scale({sx}, {-(height-2*pad)/(yrange[1]-yrange[0])})"
```

**Worked example:** suppose `xrange=[-2, 2]`, `yrange=[-2, 2]`, `width=200`, `height=200`,
`pad=32`.

```
sx =  (200 - 64) / 4 = 34
sy = -(200 - 64) / 4 = -34
tx =  32 + 2 * 34  =  100
ty =  200 - 32 + (-2) * 34 / ... 
    = (height - pad) + yrange[0] * sy_raw  where sy_raw = (height-2*pad)/(yrange[1]-yrange[0])
    = 168 + (-2) * 34 = 168 - 68 = 100
```

So `transform="translate(100, 100) scale(34, -34)"`.

Verify: math point `(0, 0)` maps to SVG `(100 + 0*34, 100 + 0*(-34)) = (100, 100)` — the
center of a 200×200 viewport, correct for a symmetric range. Math point `(2, 2)` maps to
SVG `(100 + 2*34, 100 + 2*(-34)) = (168, 32)` — upper right, correct (Y=2 is near top in
SVG because Y-flip puts large math-Y near small SVG-Y).

### 4.4 Text labels are NOT inside the transformed group

Because the transform includes `scale(1, -1)` in the Y direction, any `<text>` placed
inside the group would be mirrored (upside down). Therefore:

- All geometric shapes (line clipping, segments, polygons, circles for points) go INSIDE
  `<g class="scriba-plane-content" transform="...">`.
- All `<text>` labels (axis tick labels, point labels, line labels) go OUTSIDE this group
  in `<g class="scriba-plane-labels">` with positions computed in SVG coordinates directly.

The emitter computes label SVG positions from math coordinates using the inverse of the
transform above:

```python
def math_to_svg(x_math, y_math, tx, ty, sx, sy):
    svg_x = tx + x_math * sx
    svg_y = ty + y_math * sy
    return svg_x, svg_y
```

Labels are offset by a small constant (default 6px above or to the right) from the
corresponding anchor point in SVG space.

---

## 5. Apply commands

### 5.1 Modify an existing element

```latex
\apply{p.line[0]}{slope=1.5, intercept=0.5}
\apply{p.point[0]}{x=1.2, y=2.3}
\apply{p.segment[0]}{x1=0, y1=0, x2=3, y2=2}
```

All coordinates are in math convention. The emitter recomputes the SVG position using the
transform from §4.3.

Accepted parameters by element type:

| Element  | Mutable parameters                                                      |
|----------|-------------------------------------------------------------------------|
| point    | `x`, `y`, `label`, `radius` (px, default 4), `tooltip`                 |
| line     | `slope`, `intercept`, `a`, `b`, `c` (ax+by=c form), `label`, `tooltip` |
| segment  | `x1`, `y1`, `x2`, `y2`, `label`, `tooltip`                             |
| polygon  | `points` (full replacement list), `tooltip`                             |
| region   | `polygon` (full replacement), `fill`                                    |
| label    | `text`, `x`, `y` (anchor in math coords)                               |

### 5.2 Adding new elements dynamically

```latex
\apply{p}{add_point=(1, 2)}
\apply{p}{add_line=("new line", 2, 3)}
\apply{p}{add_segment=((0,0),(3,4))}
\apply{p}{add_polygon=[(0,0),(3,0),(3,3),(0,3)]}
\apply{p}{add_region={polygon=[(0,0),(5,0),(5,5)], fill="rgba(0,114,178,0.2)"}}
```

Each `add_*` operation appends the new element and assigns it the next available index.
For example, if the plane has 2 lines (indices 0 and 1), `add_line` creates line index 2,
which can subsequently be referenced as `p.line[2]`.

**Element cap:** a single `Plane2D` instance may hold at most **500
elements** in total (across points, lines, segments, polygons, regions)
at any one scene frame. In v0.5.x the cap is enforced as a soft
log-and-skip: when an `add_*` operation would cross the cap, the
primitive logs **E1466** and silently drops the addition rather than
aborting the render. A future Wave 4A cluster is scheduled to harden
this into a raised `RendererError`; see
[`error-codes.md`](../spec/error-codes.md) for the authoritative
severity.

### 5.3 `\apply` with `all`

```latex
\recolor{p.all}{state=dim}
\apply{p.all}{...}
```

Applies the command to every element currently in the plane.

---

## 6. Geometric helper functions (Starlark `plane2d` namespace)

The `plane2d` namespace is pre-injected into the Starlark host (see
[`ruleset.md`](../spec/ruleset.md) §5) when a `Plane2D` shape is
declared in the environment. It provides pure-Python geometry helpers
implemented in `scriba/animation/primitives/plane2d_compute.py` and exposed to `\compute`
blocks.

### 6.1 `plane2d.intersect(line1, line2) → (x, y) | None`

Compute the intersection of two lines in slope-intercept form.

**Signature:**

```
plane2d.intersect(
    line1: (slope1: float, intercept1: float),
    line2: (slope2: float, intercept2: float)
) → (x: float, y: float) | None
```

Returns `None` if lines are parallel (slopes equal within ε=1e-9). Otherwise returns
`(x, y)` in math coordinates.

**Complexity:** O(1).

**Example:**

```starlark
pt = plane2d.intersect((2, 1), (1, 3))
# y = 2x+1 and y = x+3 intersect at x=2, y=5 → (2.0, 5.0)
```

### 6.2 `plane2d.cross(a, b, c) → float`

Signed 2D cross product of vectors `(b - a)` and `(c - a)`.

**Signature:**

```
plane2d.cross(
    a: (float, float),
    b: (float, float),
    c: (float, float)
) → float
```

Returns positive if `a → b → c` is a left turn, negative if right turn, zero if collinear.

**Complexity:** O(1).

**Example:**

```starlark
sign = plane2d.cross((0,0), (1,0), (0,1))  # → 1.0 (left turn)
```

### 6.3 `plane2d.hull(points) → list of (x, y)`

Andrew's monotone chain convex hull.

**Signature:**

```
plane2d.hull(
    points: list of (float, float)
) → list of (float, float)
```

Returns the vertices of the convex hull in counter-clockwise order starting from the
lowest-leftmost point. If fewer than 3 non-collinear points are provided, returns the
input sorted. Collinear points on the hull boundary are excluded.

**Complexity:** O(N log N).

**Example:**

```starlark
pts = [(0,0),(3,0),(3,3),(0,3),(1.5,1.5),(4,1)]
h = plane2d.hull(pts)
# h = [(0,0),(4,1),(3,3),(0,3)] (CCW)
```

### 6.4 `plane2d.half_plane(line, point) → bool`

Test which side of a line a point lies on.

**Signature:**

```
plane2d.half_plane(
    line: (slope: float, intercept: float),
    point: (x: float, y: float)
) → bool
```

Returns `True` if `point.y > slope * point.x + intercept` (above the line in math
convention), `False` if below or on the line.

For vertical lines, use `plane2d.cross` instead.

**Complexity:** O(1).

**Example:**

```starlark
above = plane2d.half_plane((1, 0), (0, 2))  # → True  (2 > 0)
```

### 6.5 `plane2d.clip_line_to_viewport(slope, intercept, xrange, yrange) → ((x1,y1),(x2,y2)) | None`

Clip an infinite line to the rectangular viewport.

**Signature:**

```
plane2d.clip_line_to_viewport(
    slope: float,
    intercept: float,
    xrange: (float, float),
    yrange: (float, float)
) → ((float, float), (float, float)) | None
```

Returns the two endpoints of the visible segment, or `None` if the line does not intersect
the viewport. Used internally by the emitter for all line renderings; also exposed to
authors for custom SVG logic.

**Complexity:** O(1).

### 6.6 `plane2d.lower_envelope(lines) → list[(Line, float, float)]`

Compute the lower envelope of a set of non-vertical lines using the Convex Hull Trick
(CHT) with a monotonic deque.

**Signature:**

```
plane2d.lower_envelope(
    lines: list of (slope: float, intercept: float)
) → list of (line: (float, float), x_start: float, x_end: float)
```

Returns a list of `(line, x_start, x_end)` tuples, one per piece of the envelope, in
left-to-right order. Each tuple gives the line (as `(slope, intercept)`) and the x
interval `[x_start, x_end]` over which that line achieves the minimum y value. The
intervals partition the domain `(-∞, +∞)`, i.e., `x_start` of piece `k+1` equals
`x_end` of piece `k`.

**Complexity:** O(N log N) — standard CHT with monotone deque over lines sorted by slope.

**Implementation:** `scriba/animation/primitives/plane2d_compute.py`. No external
dependencies.

**Example:**

```starlark
lines = [(2, 1), (1, 3), (-1, 9), (-2, 11)]
# y = 2x+1, y = x+3, y = -x+9, y = -2x+11
env = plane2d.lower_envelope(lines)
# Returns the 3-piece lower envelope:
# piece 0: y=2x+1 from x=-∞ to x=2
# piece 1: y=-x+9 from x=2 to x=4
# piece 2: y=-2x+11 from x=4 to x=+∞
```

**Acceptance test requirement:** Lower envelope of 8 non-vertical lines with guaranteed
integer intersection x-coordinates. Verify that the returned pieces are contiguous, cover
`(-∞, +∞)`, and each piece correctly achieves the minimum at a test query point.

> **Audit fix (finding 7.4 / HIGH):** This helper was missing from the original spec, making
> coverage claim "Full" for HARD-TO-DISPLAY #6 overstated. With `lower_envelope` available,
> authors can directly compute and visualize the CHT envelope without hand-rolling the
> O(N log N) deque logic in Starlark.

### 6.7 Error handling in helpers

Any helper that receives invalid input (e.g. `hull` with non-numeric
coords) raises a Starlark runtime error. The `\compute` host catches
it and surfaces it through the Starlark error catalog (typically
**E1151** — Starlark runtime evaluation failure — per
[`error-codes.md`](../spec/error-codes.md)).

---

## 7. Grid and axes rendering

### 7.1 Integer grid

When `grid=true`, the emitter draws vertical and horizontal grid lines at every integer x
and y value within `xrange` and `yrange`. Grid lines use:

```css
stroke: var(--scriba-border);
stroke-width: 0.5px;
opacity: 0.6;
```

### 7.2 Fine grid

When `grid="fine"`, additionally draw lines at 0.2 intervals using:

```css
stroke: var(--scriba-border);
stroke-width: 0.25px;
opacity: 0.3;
```

### 7.3 Axes

When `axes=true`, draw the x-axis and y-axis as thicker lines through `y=0` and `x=0`
respectively (if those values fall within the viewport). If the origin is outside the
viewport, draw axes at the viewport boundary. Axes use:

```css
stroke: var(--scriba-fg);
stroke-width: 1.5px;
```

Arrowheads are rendered as `<path>` elements at the positive ends of each axis (within the
viewport). Arrowhead size: 6×4 px.

### 7.4 Tick labels

When `axes=true`, draw numeric tick labels at integer positions on both axes. Labels are
placed in `<g class="scriba-plane-labels">` (outside the transformed group, per §4.4).
Label font-size: 10px. Avoid overlap by skipping labels when tick spacing < 12px in SVG
space.

---

## 8. Element rendering details

### 8.1 Points

```html
<g data-target="p.point[0]"
   class="scriba-plane-point scriba-state-idle">
  <circle cx="{svg_x}" cy="{svg_y}" r="4"
          class="scriba-plane-point-dot"/>
  <!-- label positioned outside transformed group -->
</g>
```

Both the `<circle>` and its `<g>` wrapper are inside `<g class="scriba-plane-content">`.
The transform correctly positions the circle in math-to-SVG space. The `<g>` carries the
semantic state class and `data-target`; the corresponding label `<text>` is placed in
`<g class="scriba-plane-labels">` (outside the transformed group, in SVG space coordinates)
to avoid Y-axis flip distortion on text.

### 8.2 Lines

Lines are clipped to the viewport using `plane2d.clip_line_to_viewport` and emitted as
`<line>` elements:

```html
<g data-target="p.line[0]"
   class="scriba-plane-line scriba-state-idle">
  <line x1="{svg_x1}" y1="{svg_y1}" x2="{svg_x2}" y2="{svg_y2}"
        stroke="currentColor" stroke-width="1.5"/>
</g>
```

Degenerate lines (no intersection with viewport) emit **E1461** (line-degenerate, warning)
and are skipped.

### 8.3 Segments

```html
<g data-target="p.segment[0]"
   class="scriba-plane-segment scriba-state-idle">
  <line x1="{svg_x1}" y1="{svg_y1}" x2="{svg_x2}" y2="{svg_y2}"
        stroke="currentColor" stroke-width="2"
        stroke-linecap="round"/>
</g>
```

Segments with both endpoints outside the viewport are clipped with Liang-Barsky; if
entirely outside, **E1463** (point-outside-viewport, warning) is emitted.

### 8.4 Polygons

```html
<g data-target="p.polygon[0]"
   class="scriba-plane-polygon scriba-state-idle">
  <polygon points="{svg_point_list}"
           fill="rgba(0,114,178,0.15)"
           stroke="currentColor" stroke-width="1.5"/>
</g>
```

If the polygon is not closed (last point ≠ first), the emitter auto-closes it. **E1462**
(polygon-not-closed) is emitted as a warning (not error); rendering continues.

### 8.5 Regions

```html
<g data-target="p.region[0]"
   class="scriba-plane-region scriba-state-idle">
  <polygon points="{svg_point_list}"
           fill="{fill}"
           stroke="none"/>
</g>
```

Regions are half-plane or polygon fills with semi-transparent RGBA fill and no stroke.

### 8.6 CSS `@keyframes` for animated points/segments

The CSS `@keyframes` slot (see `extensions/keyframe-animation.md`) supports two named
presets on `Plane2D` elements:

- **`orbit`**: animates a point in a circular path around a center. Applied to
  `.scriba-plane-point` using `transform-origin` at the orbit center.
- **`rotate`**: continuously rotates a segment (useful for FFT twiddle-factor animation).

These are declared in the animation slot and respect `prefers-reduced-motion`.

---

## 9. Semantic states on Plane2D elements

Standard §9.2 state classes apply to the relevant `<g>` element:

| Element type | CSS class on `<g>`       |
|--------------|--------------------------|
| point        | `scriba-plane-point`     |
| line         | `scriba-plane-line`      |
| segment      | `scriba-plane-segment`   |
| polygon      | `scriba-plane-polygon`   |
| region       | `scriba-plane-region`    |

State classes (`scriba-state-current`, `scriba-state-done`, etc.) control the `stroke`
or `fill` via CSS variables. For lines and segments, state changes the stroke color. For
polygons, state changes the fill color while preserving opacity.

---

## 10. HTML output contract

All custom data attributes on Plane2D SVG elements use the `data-scriba-<kebab-case-name>`
convention (audit finding 4.10). No inline `<style>` is emitted in the SVG — CSS and any
`@keyframes` ship via `required_css`.

**`required_css`**: `["scriba/animation/static/scriba-plane2d.css"]`

The stylesheet provides `.scriba-plane-point`, `.scriba-plane-line`, `.scriba-plane-segment`,
`.scriba-plane-polygon`, `.scriba-plane-region` rules, `.scriba-state-*` stroke/fill
overrides, grid/axes stroke variables, and the `orbit`/`rotate` keyframe animations
(declared in `extensions/keyframe-animation.md` §2 and pulled from the shared
`scriba-keyframes.css` which is also listed as a required_css dependency of the
keyframe-animation extension).

**Supported §9.2 state classes**: `focus`, `update`, `path`, `reject`, `accept`, `hint`
(applied to `<g>` wrappers; state changes stroke color for lines/segments, fill+stroke for
polygons/regions, stroke for points).

> **Determinism.** Given identical `\shape` parameters and identical `\apply` command
> sequence, the Plane2D emitter produces byte-identical SVG output across runs.

```html
<svg class="scriba-plane2d"
     viewBox="0 0 {W} {H}"
     data-scriba-xrange="{xmin} {xmax}"
     data-scriba-yrange="{ymin} {ymax}"
     xmlns="http://www.w3.org/2000/svg"
     role="img">

  <!-- Layer 1: grid and axes (in SVG coordinates directly, no transform) -->
  <g class="scriba-plane-grid">
    <line .../>  <!-- grid lines -->
  </g>
  <g class="scriba-plane-axes">
    <line .../>  <!-- axis lines + arrowheads -->
    <path .../>  <!-- arrowhead markers -->
  </g>

  <!-- Layer 2: geometric content (math → SVG transform applied) -->
  <g class="scriba-plane-content"
     transform="translate({tx}, {ty}) scale({sx}, {sy})">
    <!-- points, lines (as clipped <line>), segments, polygons, regions -->
    <!-- each wrapped in <g data-target="p.element[i]" class="scriba-plane-... scriba-state-idle"> -->
  </g>

  <!-- Layer 3: text labels (SVG coordinates, no transform) -->
  <g class="scriba-plane-labels">
    <!-- tick labels on axes -->
    <text x="{svg_x}" y="{svg_y}" ...>{tick_value}</text>
    <!-- point labels -->
    <text ...>{point_label}</text>
    <!-- line labels (at viewport intersection) -->
    <text ...>{line_label}</text>
  </g>
</svg>
```

The three-layer structure ensures:
1. Grid/axes are always rendered in screen coordinates (no flip artifacts).
2. Geometric elements are correctly transformed from math to SVG space.
3. Text is always right-side-up.

---

## 11. Error codes

Canonical catalog in [`error-codes.md`](../spec/error-codes.md). The
Plane2D-specific range is **E1460–E1466**.

| Code  | Severity         | Condition                                              | Hint                                                        |
|-------|------------------|--------------------------------------------------------|-------------------------------------------------------------|
| E1460 | Error            | `xrange` or `yrange` has equal endpoints (degenerate viewport) | Provide non-degenerate ranges.                              |
| E1461 | Warning          | Line has no intersection with the viewport             | Extend viewport or move the line. Skipped.                  |
| E1462 | Warning          | Polygon's last point ≠ first (not closed)              | Auto-closed by emitter. No data loss.                       |
| E1463 | Warning          | Point is outside viewport bounds                       | Move the point inside the viewport or expand the range.     |
| E1465 | Error            | `aspect` is not `"equal"` or `"auto"`                  | Use one of the two supported values.                        |
| E1466 | Soft (logged)    | Plane2D element cap (500) reached                      | Reduce the number of geometric elements. v0.5.x logs and skips; future releases will raise. |

`E1464` and `E1467`–`E1469` are currently unassigned — see
[`error-codes.md`](../spec/error-codes.md) for the canonical list.

---

## 12. Acceptance tests

### 12.1 Li Chao lower envelope — 8 lines (HARD-TO-DISPLAY #6)

```latex
\begin{animation}[id=li-chao-lines]
\compute{
  lines_data = [
    ("$\ell_1: y=3x+1$",   3,  1),
    ("$\ell_2: y=2x+3$",   2,  3),
    ("$\ell_3: y=x+5$",    1,  5),
    ("$\ell_4: y=-x+9$",  -1,  9),
    ("$\ell_5: y=-2x+11$",-2, 11),
    ("$\ell_6: y=0.5x+4$", 0.5, 4),
    ("$\ell_7: y=4x-2$",   4, -2),
    ("$\ell_8: y=-0.5x+7$",-0.5,7)
  ]
}
\shape{plane}{Plane2D}{
  xrange=[0, 8], yrange=[0, 12],
  grid=true, axes=true, aspect="equal"
}

\step
\apply{plane}{add_line=${lines_data[0]}}
\narrate{Insert first line $\ell_1$.}

\step
\apply{plane}{add_line=${lines_data[1]}}
\recolor{plane.line[0]}{state=dim}
\narrate{Insert $\ell_2$. Lines not on lower envelope are dimmed.}

% ... 6 more steps ...

\step
\recolor{plane.all}{state=idle}
\recolor{plane.line[2]}{state=current}
\recolor{plane.line[3]}{state=current}
\recolor{plane.line[4]}{state=current}
\narrate{Lower envelope consists of 3 active lines.}
\end{animation}
```

Expected:
- Lines correctly clipped to `xrange=[0,8]`, `yrange=[0,12]`.
- No E146x errors for lines within viewport.
- Label text elements outside transformed group (right-side-up).
- 9 frames total (within E1180 soft limit of 30).

### 12.2 Andrew's monotone chain hull — 15 points

```latex
\begin{animation}[id=convex-hull-demo, label="Convex hull of 15 points"]
\compute{
  pts = [(0,0),(4,1),(3,4),(1,3),(2,2),(5,2),(1,1),(3,0),(4,3),(2,4),
         (0.5,2.5),(3.5,3.5),(1.5,0.5),(4.5,1.5),(2.5,3.0)]
  hull_pts = plane2d.hull(pts)
}
\shape{geo}{Plane2D}{
  xrange=[-1,6], yrange=[-1,5],
  points=${pts},
  grid=false, axes=true
}

\step
\apply{geo}{add_polygon=${hull_pts}}
\recolor{geo.polygon[0]}{state=current}
\narrate{Convex hull computed via Andrew's monotone chain.}
\end{animation}
```

Expected:
- 15 point circles rendered.
- Hull polygon with `scriba-state-current` stroke (Wong blue border).
- `plane2d.hull` returns CCW hull without collinear boundary points.

### 12.3 FFT unit circle — 8 roots of unity

```latex
\begin{animation}[id=fft-roots-of-unity, label="8th roots of unity"]
\compute{
  # 8th roots of unity: e^(2πi k/8), pre-computed (Starlark has no math module)
  # cos(k*pi/4), sin(k*pi/4) for k=0..7
  PI_OVER_4 = 0.7853981633974483
  roots8 = [
    (1.0, 0.0), (0.7071, 0.7071), (0.0, 1.0), (-0.7071, 0.7071),
    (-1.0, 0.0), (-0.7071, -0.7071), (0.0, -1.0), (0.7071, -0.7071)
  ]
  # Unit circle as 32-gon approximation (pre-computed vertices)
  unit_circle_32 = []
  for k in range(32):
      angle_k = k * 2 * 3.14159265358979 / 32
      # sin/cos approximated via the 8-point table + interpolation is not
      # practical in Starlark; in practice authors use a pre-generated list.
      # For this test the shape is symbolic; implementation pre-computes the list.
      unit_circle_32 = unit_circle_32 + [(0.0, 0.0)]  # placeholder
}
\shape{circ}{Plane2D}{
  xrange=[-1.5, 1.5], yrange=[-1.5, 1.5],
  aspect="equal", grid=false, axes=true,
  % Unit circle polygon (32 vertices computed externally and bound via \compute)
  polygons=[${unit_circle_32}]
}
% Points at roots of unity
\apply{circ}{add_point=(1.0, 0.0)}
\apply{circ}{add_point=(0.7071, 0.7071)}
\apply{circ}{add_point=(0.0, 1.0)}
\apply{circ}{add_point=(-0.7071, 0.7071)}
\apply{circ}{add_point=(-1.0, 0.0)}
\apply{circ}{add_point=(-0.7071, -0.7071)}
\apply{circ}{add_point=(0.0, -1.0)}
\apply{circ}{add_point=(0.7071, -0.7071)}

\step
\recolor{circ.point[0]}{state=current}
\narrate{First root of unity highlighted.}
\end{animation}
```

Expected:
- Unit circle approximation as polygon, state idle (light fill).
- 8 points around the circle.
- No E146x errors.

> **Audit fix (finding 9.4):** the previous draft referenced `unit_circle_64` which was
> never declared, causing E1155 at parse time. Replaced with an inline `unit_circle_32`
> binding via `\compute` and `polygons=` parameter.

---

## 13. Base-spec deltas

**§3.1** primitive type registration: add `Plane2D` (same delta as `matrix.md` §14; Agent
4 merges all five primitive registrations together).

**§4.1 BNF — IDENT accessor with subscripts** (audit finding 3.4):

`p.line[i]`, `p.segment[i]`, `p.polygon[i]`, `p.region[i]`, `p.label[i]` use
primitive-defined IDENT accessors with numeric subscripts. Base spec §4.1 BNF lists
only `cell`, `node`, `edge`, `range`, `all`, and an `IDENT` fallback, but does not
specify whether IDENT can take a subscript. Agent 4 must clarify:

> Primitive-defined IDENT accessors MAY take a single numeric or interpolation subscript:
> `IDENT "[" index "]"` where `index ::= NUMBER | INTERP`.

This same delta applies to `m.row[i]`, `m.col[j]` (Matrix) and any future primitive-defined
IDENT accessors.

**§5.2** Starlark pre-injected host API: add the `plane2d` namespace as a conditional
injection. The namespace is only injected when at least one `Plane2D` shape is declared in
the current environment. The sentence:

> The worker pre-binds exactly this set of names...

should gain a footnote:

> When a `Plane2D` shape is declared, the `plane2d` namespace is additionally pre-injected
> with the helpers documented in `primitives/plane2d.md` §6, including `intersect`, `cross`,
> `hull`, `half_plane`, `clip_line_to_viewport`, and `lower_envelope`.

**§4.2** per-primitive selector examples table: add `Plane2D` row:

| Primitive | Whole shape | Addressable parts                                                               |
|-----------|-------------|---------------------------------------------------------------------------------|
| `Plane2D` | `p`         | `p.point[0]`, `p.line[0]`, `p.segment[0]`, `p.polygon[0]`, `p.region[0]`, `p.all` |
